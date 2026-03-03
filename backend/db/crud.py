from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Meal, Reminder
from schemas.user import UserCreate
from schemas.meal import MealCreate
from schemas.reminder import ReminderCreate
from core.security import hash_password


# ─── Users ───────────────────────────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        daily_calorie_goal=user_data.daily_calorie_goal,
    )
    db.add(user)
    await db.flush()  # получаем id без commit
    return user


async def link_telegram(db: AsyncSession, user_id: int, telegram_id: int) -> User | None:
    user = await get_user_by_id(db, user_id)
    if user:
        user.telegram_id = telegram_id
    return user


# ─── Meals ───────────────────────────────────────────────────────────────────

async def create_meal(db: AsyncSession, meal_data: MealCreate, user_id: int) -> Meal:
    meal = Meal(
        user_id=user_id,
        dish_name=meal_data.dish_name,
        calories=meal_data.calories,
        protein=meal_data.protein,
        fat=meal_data.fat,
        carbs=meal_data.carbs,
        ai_confidence=meal_data.ai_confidence,
        image_path=meal_data.image_path,
        notes=meal_data.notes,
        source=meal_data.source,
    )
    db.add(meal)
    await db.flush()
    return meal


async def get_meals_by_date(db: AsyncSession, user_id: int, target_date: date) -> list[Meal]:
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    result = await db.execute(
        select(Meal)
        .where(Meal.user_id == user_id, Meal.logged_at >= start, Meal.logged_at <= end)
        .order_by(Meal.logged_at.desc())
    )
    return list(result.scalars().all())


async def get_daily_totals(db: AsyncSession, user_id: int, target_date: date) -> dict:
    """Суммарные КБЖУ за день."""
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    result = await db.execute(
        select(
            func.coalesce(func.sum(Meal.calories), 0).label("calories"),
            func.coalesce(func.sum(Meal.protein), 0).label("protein"),
            func.coalesce(func.sum(Meal.fat), 0).label("fat"),
            func.coalesce(func.sum(Meal.carbs), 0).label("carbs"),
        ).where(Meal.user_id == user_id, Meal.logged_at >= start, Meal.logged_at <= end)
    )
    row = result.one()
    return {"calories": row.calories, "protein": row.protein, "fat": row.fat, "carbs": row.carbs}


async def delete_meal(db: AsyncSession, meal_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Meal).where(Meal.id == meal_id, Meal.user_id == user_id)
    )
    meal = result.scalar_one_or_none()
    if meal:
        await db.delete(meal)
        return True
    return False


# ─── Reminders ───────────────────────────────────────────────────────────────

async def get_reminders_for_user(db: AsyncSession, user_id: int) -> list[Reminder]:
    result = await db.execute(
        select(Reminder).where(Reminder.user_id == user_id, Reminder.is_active == True)
    )
    return list(result.scalars().all())


async def get_all_active_reminders(db: AsyncSession) -> list[Reminder]:
    """Для планировщика — все активные напоминания всех пользователей."""
    result = await db.execute(
        select(Reminder).where(Reminder.is_active == True)
    )
    return list(result.scalars().all())


async def create_reminder(db: AsyncSession, reminder_data: ReminderCreate, user_id: int) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        label=reminder_data.label,
        remind_time=reminder_data.remind_time,
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def delete_reminder(db: AsyncSession, reminder_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
    )
    reminder = result.scalar_one_or_none()
    if reminder:
        await db.delete(reminder)
        return True
    return False

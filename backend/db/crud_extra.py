# Дополнения к crud.py — вес и профиль

async def get_weight_entries(db, user_id: int, limit: int = 30):
    from sqlalchemy import select
    from db.models import WeightEntry
    result = await db.execute(
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .order_by(WeightEntry.logged_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def add_weight_entry(db, user_id: int, weight_kg: float, note: str | None = None):
    from db.models import WeightEntry
    entry = WeightEntry(user_id=user_id, weight_kg=weight_kg, note=note)
    db.add(entry)
    await db.flush()
    return entry


async def delete_weight_entry(db, entry_id: int, user_id: int) -> bool:
    from sqlalchemy import select
    from db.models import WeightEntry
    result = await db.execute(
        select(WeightEntry).where(WeightEntry.id == entry_id, WeightEntry.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        await db.delete(entry)
        return True
    return False


async def update_user_profile(db, user_id: int, data: dict):
    from db.models import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    allowed = {"full_name", "height_cm", "weight_goal_kg", "daily_calorie_goal", "notify_enabled", "email"}
    for key, val in data.items():
        if key in allowed and val is not None:
            setattr(user, key, val)
    return user


async def change_password(db, user_id: int, new_password: str):
    from db.models import User
    from sqlalchemy import select
    from core.security import hash_password
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.hashed_password = hash_password(new_password)
    return user


async def get_meals_by_range(db, user_id: int, date_from, date_to):
    from datetime import datetime
    from sqlalchemy import select
    from db.models import Meal
    start = datetime.combine(date_from, datetime.min.time())
    end = datetime.combine(date_to, datetime.max.time())
    result = await db.execute(
        select(Meal)
        .where(Meal.user_id == user_id, Meal.logged_at >= start, Meal.logged_at <= end)
        .order_by(Meal.logged_at.desc())
    )
    return list(result.scalars().all())

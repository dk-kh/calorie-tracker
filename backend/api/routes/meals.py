import os
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.crud import create_meal, get_meals_by_date, get_daily_totals, delete_meal
from schemas.meal import MealResponse, DailyTotals, MealCreate
from core.security import get_current_user
from core.ai_service import analyze_food_image

router = APIRouter(prefix="/meals", tags=["meals"])

os.makedirs("uploads", exist_ok=True)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024


# ── Статические пути ПЕРВЫМИ, /{meal_id} в самом конце ──

@router.post("/analyze", response_model=MealResponse, status_code=201)
async def upload_and_analyze(
    file: UploadFile = File(...),
    notes: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Неподдерживаемый тип файла: {file.content_type}")
    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "Файл слишком большой (максимум 10 МБ)")

    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join("uploads", filename)
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    result = await analyze_food_image(image_bytes)
    meal = await create_meal(
        db,
        MealCreate(
            dish_name=result.dish_name,
            calories=result.calories,
            protein=result.protein,
            fat=result.fat,
            carbs=result.carbs,
            ai_confidence=result.confidence,
            image_path=file_path,
            notes=notes,
            source="web",
        ),
        user_id=current_user.id,
    )
    return MealResponse.model_validate(meal)


@router.get("/today", response_model=list[MealResponse])
async def get_today_meals(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    meals = await get_meals_by_date(db, current_user.id, date.today())
    return [MealResponse.model_validate(m) for m in meals]


@router.get("/totals", response_model=DailyTotals)
async def get_today_totals(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    totals = await get_daily_totals(db, current_user.id, date.today())
    remaining = current_user.daily_calorie_goal - totals["calories"]
    return DailyTotals(**totals, goal=current_user.daily_calorie_goal, remaining=max(0, remaining))


@router.get("/weekly", response_model=list[DailyTotals])
async def get_weekly_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    result = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        totals = await get_daily_totals(db, current_user.id, day)
        remaining = current_user.daily_calorie_goal - totals["calories"]
        result.append(DailyTotals(**totals, goal=current_user.daily_calorie_goal, remaining=max(0, remaining)))
    return result


@router.get("/history", response_model=list[MealResponse])
async def get_meals_history(
    target_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Поддержка как одиночной даты, так и диапазона
    if date_from and date_to:
        from db.crud_extra import get_meals_by_range
        meals = await get_meals_by_range(db, current_user.id, date_from, date_to)
    else:
        d = target_date or date.today()
        meals = await get_meals_by_date(db, current_user.id, d)
    return [MealResponse.model_validate(m) for m in meals]


# ── /{meal_id} ПОСЛЕДНИМ — иначе перехватит /weekly, /today и т.д. ──

@router.delete("/{meal_id}", status_code=204)
async def remove_meal(
    meal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = await delete_meal(db, meal_id, current_user.id)
    if not deleted:
        raise HTTPException(404, "Приём пищи не найден")

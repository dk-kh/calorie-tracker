from datetime import date, datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.database import get_db
from db.models import WeightEntry
from core.security import get_current_user

router = APIRouter(prefix="/weight", tags=["weight"])


class WeightIn(BaseModel):
    weight_kg: float
    note: str | None = None
    logged_at: date | None = None


class WeightOut(BaseModel):
    id: int
    weight_kg: float
    note: str | None
    logged_at: datetime

    model_config = {"from_attributes": True}


@router.post("/", response_model=WeightOut, status_code=201)
async def add_weight(
    data: WeightIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    entry = WeightEntry(
        user_id=current_user.id,
        weight_kg=data.weight_kg,
        note=data.note,
        logged_at=datetime.combine(data.logged_at, datetime.min.time()) if data.logged_at else datetime.utcnow(),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return WeightOut.model_validate(entry)


@router.get("/", response_model=list[WeightOut])
async def get_weight_history(
    from_date: date | None = None,
    to_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(WeightEntry).where(WeightEntry.user_id == current_user.id)
    if from_date:
        q = q.where(WeightEntry.logged_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        q = q.where(WeightEntry.logged_at <= datetime.combine(to_date, datetime.max.time()))
    q = q.order_by(WeightEntry.logged_at.asc())
    result = await db.execute(q)
    return [WeightOut.model_validate(r) for r in result.scalars().all()]


@router.delete("/{entry_id}", status_code=204)
async def delete_weight(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(WeightEntry).where(WeightEntry.id == entry_id, WeightEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        await db.delete(entry)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.crud import get_reminders_for_user, create_reminder, delete_reminder
from schemas.reminder import ReminderCreate, ReminderResponse
from core.security import get_current_user

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/", response_model=list[ReminderResponse])
async def list_reminders(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reminders = await get_reminders_for_user(db, current_user.id)
    return [ReminderResponse.model_validate(r) for r in reminders]


@router.post("/", response_model=ReminderResponse, status_code=201)
async def add_reminder(
    reminder_data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reminder = await create_reminder(db, reminder_data, current_user.id)
    return ReminderResponse.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=204)
async def remove_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = await delete_reminder(db, reminder_id, current_user.id)
    if not deleted:
        raise HTTPException(404, "Напоминание не найдено")

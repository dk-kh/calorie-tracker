from datetime import time
from pydantic import BaseModel


class ReminderCreate(BaseModel):
    label: str = "Время поесть!"
    remind_time: time  # формат HH:MM:SS или HH:MM


class ReminderResponse(BaseModel):
    id: int
    label: str
    remind_time: time
    is_active: bool

    class Config:
        from_attributes = True

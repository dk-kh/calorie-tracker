from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    daily_calorie_goal: int = 2000


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    daily_calorie_goal: int
    full_name: str | None = None
    height_cm: float | None = None
    weight_goal_kg: float | None = None
    notify_enabled: bool = True
    telegram_id: int | None = None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

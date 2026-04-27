import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.database import get_db
from db.crud import get_user_by_username, get_user_by_email, create_user
from schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from core.security import verify_password, hash_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
_link_codes: dict = {}


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(400, "Имя пользователя уже занято")
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(400, "Email уже зарегистрирован")
    user = await create_user(db, user_data)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, credentials.username)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверное имя пользователя или пароль")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    daily_calorie_goal: int | None = None
    height_cm: float | None = None
    weight_goal_kg: float | None = None
    notify_enabled: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.full_name is not None: current_user.full_name = data.full_name
    if data.daily_calorie_goal is not None: current_user.daily_calorie_goal = data.daily_calorie_goal
    if data.height_cm is not None: current_user.height_cm = data.height_cm
    if data.weight_goal_kg is not None: current_user.weight_goal_kg = data.weight_goal_kg
    if data.notify_enabled is not None: current_user.notify_enabled = data.notify_enabled
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Неверный текущий пароль")
    if len(data.new_password) < 6:
        raise HTTPException(400, "Новый пароль должен быть не менее 6 символов")
    current_user.hashed_password = hash_password(data.new_password)
    return {"ok": True}


@router.delete("/unlink-telegram")
async def unlink_telegram(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    current_user.telegram_id = None
    return {"ok": True}


@router.post("/link-code")
async def generate_link_code(current_user=Depends(get_current_user)):
    code = ''.join(random.choices(string.digits, k=6))
    _link_codes[code] = (current_user.id, datetime.utcnow() + timedelta(minutes=10))
    return {"code": code}


@router.post("/link-telegram/{code}")
async def link_telegram_by_code(code: str, telegram_id: int, db: AsyncSession = Depends(get_db)):
    from db.crud import link_telegram
    entry = _link_codes.get(code)
    if not entry:
        raise HTTPException(400, "Неверный или истёкший код")
    user_id, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _link_codes[code]
        raise HTTPException(400, "Код истёк")
    user = await link_telegram(db, user_id, telegram_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    del _link_codes[code]
    return {"ok": True, "username": user.username}

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.crud import get_user_by_username, get_user_by_email, create_user
from schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from core.security import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем уникальность
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = await create_user(db, user_data)
    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, credentials.username)

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


# ── Telegram Link ──
import random, string
from datetime import datetime, timedelta

# Временное хранилище кодов: {code: (user_id, expires_at)}
_link_codes: dict = {}


@router.post("/link-code")
async def generate_link_code(current_user=Depends(get_current_user)):
    """Генерирует 6-значный код для привязки Telegram."""
    code = ''.join(random.choices(string.digits, k=6))
    _link_codes[code] = (current_user.id, datetime.utcnow() + timedelta(minutes=10))
    return {"code": code}


@router.post("/link-telegram/{code}")
async def link_telegram_by_code(
    code: str,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Вызывается ботом — привязывает telegram_id к аккаунту по коду."""
    from db.crud import link_telegram

    entry = _link_codes.get(code)
    if not entry:
        raise HTTPException(400, "Неверный или истёкший код")

    user_id, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _link_codes[code]
        raise HTTPException(400, "Код истёк, получи новый на сайте")

    user = await link_telegram(db, user_id, telegram_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    del _link_codes[code]
    return {"ok": True, "username": user.username}

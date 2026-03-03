from datetime import datetime, time
from sqlalchemy import (
    Integer, String, Float, Boolean,
    DateTime, Time, ForeignKey, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Telegram связка (nullable — пользователь может не привязывать бота)
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    # Цели пользователя
    daily_calorie_goal: Mapped[int] = mapped_column(Integer, default=2000)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связи
    meals: Mapped[list["Meal"]] = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Что распознал AI
    dish_name: Mapped[str] = mapped_column(String(200), nullable=False)
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)   # граммы
    fat: Mapped[float] = mapped_column(Float, default=0.0)       # граммы
    carbs: Mapped[float] = mapped_column(Float, default=0.0)     # граммы

    # Мета
    ai_confidence: Mapped[str] = mapped_column(String(20), default="medium")  # high/medium/low
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Источник: "web" или "telegram"
    source: Mapped[str] = mapped_column(String(20), default="web")

    # Связь
    user: Mapped["User"] = relationship("User", back_populates="meals")

    def __repr__(self) -> str:
        return f"<Meal id={self.id} dish={self.dish_name} kcal={self.calories}>"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    label: Mapped[str] = mapped_column(String(100), default="Время поесть!")  # "Завтрак", "Обед"...
    remind_time: Mapped[time] = mapped_column(Time, nullable=False)            # например 08:00
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связь
    user: Mapped["User"] = relationship("User", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} time={self.remind_time} label={self.label}>"

from datetime import datetime
from pydantic import BaseModel, Field


class MealCreate(BaseModel):
    dish_name: str
    calories: float = Field(ge=0)
    protein: float = Field(default=0.0, ge=0)
    fat: float = Field(default=0.0, ge=0)
    carbs: float = Field(default=0.0, ge=0)
    ai_confidence: str = "medium"
    image_path: str | None = None
    notes: str | None = None
    source: str = "web"


class MealResponse(BaseModel):
    id: int
    dish_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    ai_confidence: str
    image_path: str | None
    notes: str | None
    source: str
    logged_at: datetime

    class Config:
        from_attributes = True


class DailyTotals(BaseModel):
    calories: float
    protein: float
    fat: float
    carbs: float
    goal: int
    remaining: float

"""
AI-сервис для анализа фотографий еды.

Переключение режима через .env:
    USE_MOCK_AI=true  → заглушка 
    USE_MOCK_AI=false → реальный Ollama 
"""
import json
import base64
import random
import logging
from dataclasses import dataclass

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    dish_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    confidence: str  # "high" | "medium" | "low"
    raw_response: str = ""


# ─── Промпт для Vision-модели ─────────────────────────────────────────────────

FOOD_ANALYSIS_PROMPT = """You are a nutrition expert. Analyze the food in this image.
Identify the dish and estimate nutritional values for the visible portion.

Respond ONLY with a valid JSON object, no extra text:
{
  "dish": "dish name in Russian",
  "calories": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0,
  "confidence": "high"
}

Rules:
- dish: name in Russian (e.g. "Гречневая каша с курицей")
- calories, protein, fat, carbs: numbers in grams/kcal (no units in value)
- confidence: "high" if dish clearly visible, "medium" if partially, "low" if unclear
- If no food found, set dish to "Блюдо не распознано" and all numbers to 0
"""


# ─── Mock (заглушка) ──────────────────────────────────────────────────────────

# Набор реалистичных данных для разработки без AI
_MOCK_FOODS = [
    AnalysisResult("Овсяная каша с бананом", 320, 10, 6, 58, "high"),
    AnalysisResult("Куриная грудка с рисом", 450, 38, 8, 48, "high"),
    AnalysisResult("Борщ со сметаной", 280, 12, 10, 32, "medium"),
    AnalysisResult("Цезарь с курицей", 520, 28, 32, 24, "high"),
    AnalysisResult("Греческий йогурт с ягодами", 180, 14, 4, 22, "high"),
    AnalysisResult("Пицца Маргарита (2 куска)", 680, 24, 22, 88, "medium"),
    AnalysisResult("Гречневая каша", 310, 12, 4, 58, "high"),
    AnalysisResult("Омлет с овощами", 260, 18, 16, 8, "high"),
]


def _mock_analyze() -> AnalysisResult:
    """Возвращает случайное блюдо из набора + небольшой разброс значений."""
    base = random.choice(_MOCK_FOODS)
    noise = lambda v: round(v * random.uniform(0.9, 1.1), 1)
    return AnalysisResult(
        dish_name=base.dish_name,
        calories=noise(base.calories),
        protein=noise(base.protein),
        fat=noise(base.fat),
        carbs=noise(base.carbs),
        confidence=base.confidence,
        raw_response="[MOCK DATA — set USE_MOCK_AI=false to use real Ollama]",
    )


# ─── Real Ollama ──────────────────────────────────────────────────────────────

def _image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _parse_ollama_response(raw: str) -> AnalysisResult:
    """Парсим JSON из ответа Ollama. Модели иногда добавляют мусор — чистим."""
    # Ищем первый { и последний } — вырезаем JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {raw[:200]}")

    data = json.loads(raw[start:end])

    return AnalysisResult(
        dish_name=str(data.get("dish", "Неизвестное блюдо")),
        calories=float(data.get("calories", 0)),
        protein=float(data.get("protein", 0)),
        fat=float(data.get("fat", 0)),
        carbs=float(data.get("carbs", 0)),
        confidence=str(data.get("confidence", "low")),
        raw_response=raw,
    )


async def _real_analyze(image_bytes: bytes) -> AnalysisResult:
    """Отправляет изображение в Ollama и возвращает распознанное блюдо."""
    image_b64 = _image_to_base64(image_bytes)

    payload = {
        "model": settings.ollama_model,
        "prompt": FOOD_ANALYSIS_PROMPT,
        "images": [image_b64],
        "stream": False,  # ждём полный ответ
        "options": {
            "temperature": 0.1,  # меньше фантазии, больше точности
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:  # Ollama может думать долго
        response = await client.post(
            f"{settings.ollama_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()

    result_json = response.json()
    raw_text = result_json.get("response", "")
    logger.debug(f"Ollama raw response: {raw_text}")

    return _parse_ollama_response(raw_text)


# ─── Публичный интерфейс ──────────────────────────────────────────────────────

async def analyze_food_image(image_bytes: bytes) -> AnalysisResult:
    """
    Главная функция. Вызывается из API и Telegram-бота.
    Автоматически выбирает режим по USE_MOCK_AI из .env
    """
    if settings.use_mock_ai:
        logger.info("AI mode: MOCK (USE_MOCK_AI=true)")
        return _mock_analyze()

    logger.info(f"AI mode: REAL Ollama ({settings.ollama_model})")
    try:
        return await _real_analyze(image_bytes)
    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama. Is it running? `ollama serve`")
        raise RuntimeError(
            "Ollama недоступен. Убедись что запущен `ollama serve` и модель скачана: "
            f"`ollama pull {settings.ollama_model}`"
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse Ollama response: {e}")
        # Возвращаем fallback вместо краша
        return AnalysisResult(
            dish_name="Блюдо распознано (детали недоступны)",
            calories=0, protein=0, fat=0, carbs=0,
            confidence="low",
            raw_response=str(e),
        )

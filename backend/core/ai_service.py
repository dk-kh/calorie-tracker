"""
AI-сервис для анализа фотографий еды.

USE_MOCK_AI=true  -> заглушка (дом, ноутбук)
USE_MOCK_AI=false -> реальный Ollama (универский комп)
"""
import json
import base64
import random
import re
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
    confidence: str
    raw_response: str = ""


FOOD_ANALYSIS_PROMPT = """You are a nutrition expert. Look at this food image carefully.

Respond ONLY with a valid JSON object, no markdown, no explanation, just JSON:
{"dish": "НАЗВАНИЕ_БЛЮДА", "calories": ЧИСЛО, "protein": ЧИСЛО, "fat": ЧИСЛО, "carbs": ЧИСЛО, "confidence": "high"}

Rules:
- Replace НАЗВАНИЕ_БЛЮДА with the actual food name in Russian
- Replace each ЧИСЛО with a realistic number based on what you see
- For a pizza slice: ~280-350 kcal. For a salad: ~150-300. For rice+chicken: ~400-500
- Do NOT copy example numbers. Estimate based on the actual food in the image.
- confidence: high/medium/low depending on how clearly you see the food
"""

_MOCK_FOODS = [
    AnalysisResult("Овсяная каша с бананом", 320, 10, 6, 58, "high"),
    AnalysisResult("Куриная грудка с рисом", 450, 38, 8, 48, "high"),
    AnalysisResult("Борщ со сметаной", 280, 12, 10, 32, "medium"),
    AnalysisResult("Цезарь с курицей", 520, 28, 32, 24, "high"),
    AnalysisResult("Греческий йогурт с ягодами", 180, 14, 4, 22, "high"),
    AnalysisResult("Пицца Пепперони (2 куска)", 680, 24, 22, 88, "medium"),
    AnalysisResult("Гречневая каша", 310, 12, 4, 58, "high"),
    AnalysisResult("Омлет с овощами", 260, 18, 16, 8, "high"),
]


def _mock_analyze() -> AnalysisResult:
    base = random.choice(_MOCK_FOODS)
    noise = lambda v: round(v * random.uniform(0.9, 1.1), 1)
    return AnalysisResult(
        dish_name=base.dish_name,
        calories=noise(base.calories),
        protein=noise(base.protein),
        fat=noise(base.fat),
        carbs=noise(base.carbs),
        confidence=base.confidence,
        raw_response="[MOCK]",
    )


def _image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _parse_ollama_response(raw: str) -> AnalysisResult:
    """
    Устойчивый парсер. LLaVA иногда оборачивает JSON в ```json```
    или добавляет текст до/после — вытаскиваем JSON любым способом.
    """
    logger.debug(f"Raw Ollama response: {raw[:500]}")

    # Убираем markdown-блоки
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip()
    cleaned = cleaned.replace('```', '')

    # Ищем первый { и последний }
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError(f"JSON not found in: {raw[:300]}")

    json_str = cleaned[start:end]
    data = json.loads(json_str)

    # Извлекаем с поддержкой разных ключей
    calories = float(data.get("calories") or data.get("kcal") or 0)
    protein  = float(data.get("protein") or data.get("proteins") or 0)
    fat      = float(data.get("fat") or data.get("fats") or 0)
    carbs    = float(data.get("carbs") or data.get("carbohydrates") or 0)
    dish     = str(data.get("dish") or data.get("name") or data.get("food") or "Неизвестное блюдо")
    conf     = str(data.get("confidence") or "medium")

    return AnalysisResult(
        dish_name=dish,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        confidence=conf,
        raw_response=raw,
    )


async def _real_analyze(image_bytes: bytes) -> AnalysisResult:
    image_b64 = _image_to_base64(image_bytes)

    payload = {
        "model": settings.ollama_model,
        "prompt": FOOD_ANALYSIS_PROMPT,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 200,
        }
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()

    raw_text = response.json().get("response", "")
    return _parse_ollama_response(raw_text)


async def analyze_food_image(image_bytes: bytes) -> AnalysisResult:
    if settings.use_mock_ai:
        logger.info("AI mode: MOCK")
        return _mock_analyze()

    logger.info(f"AI mode: Ollama ({settings.ollama_model})")
    try:
        return await _real_analyze(image_bytes)
    except httpx.ConnectError:
        raise RuntimeError("Ollama недоступен. Запусти: ollama serve")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Parse error: {e}")
        return AnalysisResult(
            dish_name="Не удалось распознать блюдо",
            calories=0, protein=0, fat=0, carbs=0,
            confidence="low",
            raw_response=str(e),
        )

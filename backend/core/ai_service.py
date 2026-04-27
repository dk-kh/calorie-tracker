"""
AI-сервис для анализа фотографий еды.

USE_MOCK_AI=true         -> заглушка
USE_MOCK_AI=false        -> Ollama (основной)
USE_DEEPSEEK_FALLBACK=true -> DeepSeek если Ollama упал
"""
import json, base64, random, re, logging
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


FOOD_PROMPT = """You are a nutrition expert. Analyze the food in this image.

Respond ONLY with JSON, no markdown, no extra text:
{"dish": "НАЗВАНИЕ_БЛЮДА", "calories": ЧИСЛО, "protein": ЧИСЛО, "fat": ЧИСЛО, "carbs": ЧИСЛО, "confidence": "high"}

Rules:
- dish: actual food name in Russian
- Replace each ЧИСЛО with realistic numbers based on what you see
- Pizza slice ~280-350 kcal, salad ~150-300, rice+chicken ~400-500, burger ~500-700
- Do NOT copy example numbers. Estimate from the actual food in the image.
- confidence: high/medium/low
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
    n = lambda v: round(v * random.uniform(0.9, 1.1), 1)
    return AnalysisResult(base.dish_name, n(base.calories), n(base.protein), n(base.fat), n(base.carbs), base.confidence, "[MOCK]")


def _parse_json(raw: str) -> AnalysisResult:
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().replace('```', '')
    start, end = cleaned.find("{"), cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"JSON not found in: {raw[:200]}")
    data = json.loads(cleaned[start:end])
    return AnalysisResult(
        dish_name=str(data.get("dish") or data.get("name") or "Неизвестное блюдо"),
        calories=float(data.get("calories") or data.get("kcal") or 0),
        protein=float(data.get("protein") or 0),
        fat=float(data.get("fat") or 0),
        carbs=float(data.get("carbs") or 0),
        confidence=str(data.get("confidence") or "medium"),
        raw_response=raw,
    )


async def _ollama_analyze(image_bytes: bytes) -> AnalysisResult:
    b64 = base64.b64encode(image_bytes).decode()
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(f"{settings.ollama_url}/api/generate", json={
            "model": settings.ollama_model,
            "prompt": FOOD_PROMPT,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200},
        })
        r.raise_for_status()
    return _parse_json(r.json().get("response", ""))


async def _deepseek_analyze(image_bytes: bytes) -> AnalysisResult:
    """DeepSeek Vision API — запасной вариант."""
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY не задан в .env")

    b64 = base64.b64encode(image_bytes).decode()
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": FOOD_PROMPT},
                ],
            }
        ],
        "max_tokens": 300,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


async def analyze_food_image(image_bytes: bytes) -> AnalysisResult:
    if settings.use_mock_ai:
        logger.info("AI: MOCK")
        return _mock_analyze()

    # Пробуем Ollama
    try:
        logger.info(f"AI: Ollama ({settings.ollama_model})")
        return await _ollama_analyze(image_bytes)
    except httpx.ConnectError:
        logger.warning("Ollama недоступен")
        if settings.use_deepseek_fallback:
            logger.info("AI: переключаемся на DeepSeek")
            return await _deepseek_analyze(image_bytes)
        raise RuntimeError("Ollama недоступен. Запусти: ollama serve")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Parse error Ollama: {e}")
        if settings.use_deepseek_fallback:
            logger.info("AI: Ollama вернул плохой ответ, пробуем DeepSeek")
            try:
                return await _deepseek_analyze(image_bytes)
            except Exception as e2:
                logger.error(f"DeepSeek тоже упал: {e2}")
        return AnalysisResult("Не удалось распознать блюдо", 0, 0, 0, 0, "low", str(e))

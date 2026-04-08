"""
AI-сервис: Ollama (primary) -> DeepSeek API (fallback) -> Mock
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
{"dish": "НАЗВАНИЕ_БЛЮДА_НА_РУССКОМ", "calories": ЧИСЛО, "protein": ЧИСЛО, "fat": ЧИСЛО, "carbs": ЧИСЛО, "confidence": "high"}
- Replace each placeholder with real values based on what you see
- Do NOT copy example numbers
- confidence: high/medium/low
"""

_MOCK_FOODS = [
    AnalysisResult("Овсяная каша с бананом", 320, 10, 6, 58, "high"),
    AnalysisResult("Куриная грудка с рисом", 450, 38, 8, 48, "high"),
    AnalysisResult("Борщ со сметаной", 280, 12, 10, 32, "medium"),
    AnalysisResult("Цезарь с курицей", 520, 28, 32, 24, "high"),
    AnalysisResult("Пицца Пепперони 2 куска", 680, 24, 22, 88, "medium"),
    AnalysisResult("Гречневая каша", 310, 12, 4, 58, "high"),
    AnalysisResult("Омлет с овощами", 260, 18, 16, 8, "high"),
]


def _mock() -> AnalysisResult:
    base = random.choice(_MOCK_FOODS)
    n = lambda v: round(v * random.uniform(0.9, 1.1), 1)
    return AnalysisResult(base.dish_name, n(base.calories), n(base.protein),
                          n(base.fat), n(base.carbs), base.confidence, "[MOCK]")


def _parse(raw: str) -> AnalysisResult:
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
    s, e = cleaned.find("{"), cleaned.rfind("}") + 1
    if s == -1 or e == 0:
        raise ValueError(f"No JSON: {raw[:200]}")
    data = json.loads(cleaned[s:e])
    return AnalysisResult(
        dish_name=str(data.get("dish") or data.get("name") or "Неизвестное блюдо"),
        calories=float(data.get("calories") or data.get("kcal") or 0),
        protein=float(data.get("protein") or 0),
        fat=float(data.get("fat") or 0),
        carbs=float(data.get("carbs") or 0),
        confidence=str(data.get("confidence") or "medium"),
        raw_response=raw,
    )


async def _ollama(image_bytes: bytes) -> AnalysisResult:
    payload = {
        "model": settings.ollama_model,
        "prompt": FOOD_PROMPT,
        "images": [base64.b64encode(image_bytes).decode()],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(f"{settings.ollama_url}/api/generate", json=payload)
        r.raise_for_status()
    return _parse(r.json().get("response", ""))


async def _deepseek(image_bytes: bytes) -> AnalysisResult:
    """DeepSeek Vision API как запасной вариант."""
    api_key = getattr(settings, "deepseek_api_key", None)
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY не задан в .env")

    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "model": "deepseek-chat",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": FOOD_PROMPT}
            ]
        }],
        "max_tokens": 200,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return _parse(text)


async def analyze_food_image(image_bytes: bytes) -> AnalysisResult:
    if settings.use_mock_ai:
        return _mock()

    # Пробуем Ollama
    try:
        result = await _ollama(image_bytes)
        logger.info("AI: Ollama OK")
        return result
    except Exception as e:
        logger.warning(f"Ollama failed: {e} — пробуем DeepSeek")

    # Fallback: DeepSeek
    try:
        result = await _deepseek(image_bytes)
        logger.info("AI: DeepSeek OK")
        return result
    except Exception as e:
        logger.error(f"DeepSeek failed: {e}")
        return AnalysisResult("Не удалось распознать", 0, 0, 0, 0, "low", str(e))

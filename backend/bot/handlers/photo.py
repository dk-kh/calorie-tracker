import logging
from aiogram import Router, Bot
from aiogram.types import Message

from core.ai_service import analyze_food_image
from db.database import AsyncSessionLocal
from db.crud import get_user_by_telegram_id, create_meal
from schemas.meal import MealCreate

logger = logging.getLogger(__name__)
router = Router()

def _conf_icon(c): return {"high":"✅","medium":"⚠️","low":"❓"}.get(c,"❓")


@router.message(lambda msg: msg.photo is not None)
async def handle_food_photo(message: Message, bot: Bot):
    thinking_msg = await message.answer("🔍 Анализирую фото...")

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        image_bytes = file_bytes.read()

        result = await analyze_food_image(image_bytes)

        async with AsyncSessionLocal() as db:
            user = await get_user_by_telegram_id(db, message.from_user.id)

            if user:
                await create_meal(
                    db,
                    MealCreate(
                        dish_name=result.dish_name,
                        calories=result.calories,
                        protein=result.protein,
                        fat=result.fat,
                        carbs=result.carbs,
                        ai_confidence=result.confidence,
                        source="telegram",
                    ),
                    user_id=user.id,
                )
                await db.commit()  # ← вот этого не хватало
                saved_note = "✔️ <i>Сохранено в дневник</i>"
            else:
                saved_note = "⚠️ <i>Аккаунт не привязан — отправь /link КОД</i>"

        await thinking_msg.edit_text(
            f"🍽 <b>{result.dish_name}</b> {_conf_icon(result.confidence)}\n\n"
            f"🔥 Калории: <b>{result.calories:.0f}</b> ккал\n"
            f"💪 Белки:   <b>{result.protein:.1f}</b> г\n"
            f"🧈 Жиры:    <b>{result.fat:.1f}</b> г\n"
            f"🌾 Углеводы: <b>{result.carbs:.1f}</b> г\n\n"
            f"{saved_note}"
        )

    except Exception as e:
        logger.error(f"Photo analysis failed: {e}", exc_info=True)
        await thinking_msg.edit_text(
            f"❌ Ошибка анализа. Попробуй ещё раз.\n<i>{str(e)[:100]}</i>"
        )

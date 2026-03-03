"""
Инициализация Telegram-бота.
Aiogram 3 работает внутри того же asyncio event loop что и FastAPI.
"""
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings

logger = logging.getLogger(__name__)

# Синглтоны
_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    """Возвращает глобальный экземпляр бота (для отправки из scheduler)."""
    if _bot is None:
        raise RuntimeError("Bot not initialized. Call setup_bot() first.")
    return _bot


def get_dispatcher() -> Dispatcher:
    if _dp is None:
        raise RuntimeError("Dispatcher not initialized.")
    return _dp


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Создаёт Bot и Dispatcher, регистрирует все роуты."""
    global _bot, _dp

    _bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    _dp = Dispatcher()

    # Регистрируем роуты
    from bot.handlers import photo, commands, reminders as reminder_handlers
    _dp.include_router(commands.router)
    _dp.include_router(photo.router)
    _dp.include_router(reminder_handlers.router)

    logger.info("Telegram bot initialized")
    return _bot, _dp


async def start_polling():
    """Запускает polling в фоне (используется при разработке)."""
    bot, dp = await setup_bot()
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

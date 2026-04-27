import logging
import ssl

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    if _bot is None:
        raise RuntimeError("Bot not initialized.")
    return _bot


def get_dispatcher() -> Dispatcher:
    if _dp is None:
        raise RuntimeError("Dispatcher not initialized.")
    return _dp


async def setup_bot() -> tuple[Bot, Dispatcher]:
    global _bot, _dp

    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

    session = AiohttpSession()

    _bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session,
    )
    _dp = Dispatcher()

    from bot.handlers import photo, commands, reminders as reminder_handlers
    _dp.include_router(commands.router)
    _dp.include_router(photo.router)
    _dp.include_router(reminder_handlers.router)

    logger.info("Telegram bot initialized")
    return _bot, _dp


async def start_polling():
    bot, dp = await setup_bot()
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

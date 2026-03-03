"""
Планировщик напоминаний на APScheduler.
Каждую минуту проверяет БД и шлёт Telegram-сообщения тем,
у кого сейчас время напоминания (с допуском ±1 мин).
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Глобальный экземпляр — создаём один раз
scheduler = AsyncIOScheduler(timezone="Asia/Almaty")  # поменяй на свой часовой пояс


async def _check_and_send_reminders():
    """Задача, выполняемая каждую минуту."""
    # Импорты здесь чтобы избежать circular imports при старте
    from db.database import AsyncSessionLocal
    from db.crud import get_all_active_reminders, get_user_by_id

    now = datetime.now().time()
    current_hm = (now.hour, now.minute)  # сравниваем только часы:минуты

    async with AsyncSessionLocal() as db:
        reminders = await get_all_active_reminders(db)

        for reminder in reminders:
            r_hm = (reminder.remind_time.hour, reminder.remind_time.minute)

            if r_hm == current_hm:
                user = await get_user_by_id(db, reminder.user_id)

                if user and user.telegram_id:
                    await _send_reminder_message(user.telegram_id, reminder.label)
                else:
                    logger.debug(
                        f"Reminder {reminder.id}: user has no telegram_id, skipping"
                    )


async def _send_reminder_message(telegram_id: int, label: str):
    """Отправляет сообщение через Bot instance."""
    try:
        from bot.setup import get_bot  # импортируем живой экземпляр бота
        bot = get_bot()
        await bot.send_message(
            chat_id=telegram_id,
            text=f"🍽 {label}\n\nНе забудь сфотографировать еду и отправить мне!"
        )
        logger.info(f"Reminder sent to telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send reminder to {telegram_id}: {e}")


def setup_scheduler():
    """Регистрирует задачи и возвращает планировщик."""
    scheduler.add_job(
        _check_and_send_reminders,
        trigger=IntervalTrigger(minutes=1),
        id="check_reminders",
        replace_existing=True,
    )
    logger.info("Scheduler configured: reminders check every minute")
    return scheduler

from datetime import time
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.database import AsyncSessionLocal
from db.crud import (
    get_user_by_telegram_id, get_reminders_for_user,
    create_reminder, get_daily_totals
)
from schemas.reminder import ReminderCreate
from datetime import date

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer(
                "⚠️ Аккаунт не привязан.\n"
                "Зарегистрируйся на сайте чтобы видеть статистику."
            )
            return

        totals = await get_daily_totals(db, user.id, date.today())
        remaining = user.daily_calorie_goal - totals["calories"]

        bar_filled = int((totals["calories"] / user.daily_calorie_goal) * 10)
        bar_filled = min(bar_filled, 10)
        progress_bar = "█" * bar_filled + "░" * (10 - bar_filled)

        await message.answer(
            f"📊 <b>Статистика за сегодня</b>\n\n"
            f"🔥 Калории: <b>{totals['calories']:.0f}</b> / {user.daily_calorie_goal} ккал\n"
            f"[{progress_bar}]\n\n"
            f"💪 Белки:    <b>{totals['protein']:.1f}</b> г\n"
            f"🧈 Жиры:     <b>{totals['fat']:.1f}</b> г\n"
            f"🌾 Углеводы: <b>{totals['carbs']:.1f}</b> г\n\n"
            f"{'✅ Цель выполнена!' if remaining <= 0 else f'Осталось: {remaining:.0f} ккал'}"
        )


@router.message(Command("remind"))
async def cmd_add_reminder(message: Message):
    """
    Использование: /remind 08:00 Завтрак
    """
    parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "⏰ Формат: <code>/remind ЧЧ:ММ Название</code>\n"
            "Пример: <code>/remind 08:00 Завтрак</code>"
        )
        return

    time_str = parts[1]
    label = parts[2] if len(parts) > 2 else "Время поесть!"

    try:
        h, m = map(int, time_str.split(":"))
        remind_time = time(h, m)
    except (ValueError, TypeError):
        await message.answer("❌ Неверный формат времени. Используй ЧЧ:ММ, например 13:30")
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("⚠️ Сначала привяжи аккаунт через веб-сайт.")
            return

        await create_reminder(db, ReminderCreate(label=label, remind_time=remind_time), user.id)

    await message.answer(f"✅ Напоминание <b>{label}</b> установлено на <b>{time_str}</b>")


@router.message(Command("remindlist"))
async def cmd_list_reminders(message: Message):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("⚠️ Аккаунт не привязан.")
            return

        reminders = await get_reminders_for_user(db, user.id)

    if not reminders:
        await message.answer("У тебя нет активных напоминаний.\nДобавь: /remind 08:00 Завтрак")
        return

    lines = [f"⏰ <b>Твои напоминания:</b>\n"]
    for r in reminders:
        lines.append(f"• {r.remind_time.strftime('%H:%M')} — {r.label} (id:{r.id})")

    await message.answer("\n".join(lines))

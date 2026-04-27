import httpx
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

router = Router()
API_BASE = "http://localhost:8000/api"

# Главное меню — текстовые кнопки
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📅 Дневник")],
        [KeyboardButton(text="⚖ Вес"), KeyboardButton(text="⏰ Напоминания")],
        [KeyboardButton(text="🔗 Привязать аккаунт"), KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие или отправь фото еды",
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Привет! Я NutriLens бот</b>\n\n"
        "📸 Отправь мне <b>фото еды</b> — распознаю блюдо и посчитаю КБЖУ.\n\n"
        "Используй кнопки меню ниже или команду /help",
        reply_markup=MAIN_KB,
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Как пользоваться:</b>\n\n"
        "1️⃣ Зарегистрируйся на сайте\n"
        "2️⃣ Нажми <b>🔗 Привязать аккаунт</b>\n"
        "3️⃣ Получи код и введи его на сайте\n"
        "4️⃣ Отправляй фото еды — всё сохраняется!\n\n"
        "📸 <b>Просто отправь фото</b> — я всё посчитаю",
        reply_markup=MAIN_KB,
    )


@router.message(Command("link"))
async def cmd_link(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ Укажи код: <code>/link 123456</code>\n\n"
            "Получи код на сайте в разделе <b>Telegram</b>."
        )
        return
    await _do_link(message, parts[1].strip())


@router.message(F.text == "🔗 Привязать аккаунт")
async def btn_link(message: Message):
    await message.answer(
        "🔗 <b>Привязка аккаунта</b>\n\n"
        "1. Открой сайт → раздел <b>Telegram</b>\n"
        "2. Нажми <b>Получить код</b>\n"
        "3. Отправь сюда: <code>/link КОД</code>",
        reply_markup=MAIN_KB,
    )


async def _do_link(message: Message, code: str):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE}/auth/link-telegram/{code}",
                params={"telegram_id": message.from_user.id},
            )
        if r.status_code == 200:
            data = r.json()
            await message.answer(
                f"✅ <b>Аккаунт привязан!</b>\n\n"
                f"Добро пожаловать, <b>@{data['username']}</b>!\n"
                f"Теперь фото еды сохраняются в твой дневник 🎉",
                reply_markup=MAIN_KB,
            )
        else:
            detail = r.json().get("detail", "Ошибка")
            await message.answer(f"❌ {detail}", reply_markup=MAIN_KB)
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения: {e}", reply_markup=MAIN_KB)


@router.message(F.text == "📊 Статистика")
async def btn_stats(message: Message):
    await _send_stats(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    await _send_stats(message)


async def _send_stats(message: Message):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_BASE}/meals/totals",
                headers={"X-Telegram-Id": str(message.from_user.id)},
            )
        if r.status_code == 200:
            d = r.json()
            pct = min(100, int(d['calories'] / d['goal'] * 100)) if d['goal'] else 0
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            await message.answer(
                f"📊 <b>Статистика за сегодня</b>\n\n"
                f"🔥 Калории: <b>{d['calories']:.0f}</b> / {d['goal']} ккал\n"
                f"[{bar}] {pct}%\n\n"
                f"💪 Белки:    <b>{d['protein']:.1f}</b> г\n"
                f"🧈 Жиры:     <b>{d['fat']:.1f}</b> г\n"
                f"🌾 Углеводы: <b>{d['carbs']:.1f}</b> г",
                reply_markup=MAIN_KB,
            )
        else:
            await message.answer("⚠️ Привяжи аккаунт чтобы видеть статистику", reply_markup=MAIN_KB)
    except Exception:
        await message.answer("❌ Не удалось получить статистику", reply_markup=MAIN_KB)


@router.message(F.text == "⚖ Вес")
async def btn_weight(message: Message):
    await message.answer(
        "⚖ <b>Отслеживание веса</b>\n\n"
        "Добавляй замеры на сайте в разделе <b>Вес</b>.\n"
        "Там же смотри график динамики.",
        reply_markup=MAIN_KB,
    )


@router.message(F.text == "⏰ Напоминания")
async def btn_reminders(message: Message):
    await message.answer(
        "⏰ <b>Напоминания</b>\n\n"
        "Управляй напоминаниями на сайте в разделе <b>Напоминания</b>.\n\n"
        "Или добавь прямо здесь:\n"
        "<code>/remind 08:00 Завтрак</code>",
        reply_markup=MAIN_KB,
    )


@router.message(F.text == "📅 Дневник")
async def btn_journal(message: Message):
    await message.answer(
        "📅 Дневник питания доступен на сайте.\n\n"
        "Открой <b>http://localhost:8000/app</b> → раздел <b>Дневник</b>",
        reply_markup=MAIN_KB,
    )


@router.message(Command("remind"))
async def cmd_remind(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ Формат: <code>/remind ЧЧ:ММ Название</code>\n"
            "Пример: <code>/remind 08:00 Завтрак</code>"
        )
        return
    await message.answer(f"⏰ Напоминание установлено: <b>{parts[1]}</b> — {parts[2]}", reply_markup=MAIN_KB)

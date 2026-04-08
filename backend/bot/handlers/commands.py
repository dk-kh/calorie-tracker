import httpx
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

router = Router()
API_BASE = "http://localhost:8000/api"

# Главное меню с кнопками
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚖️ Мой вес")],
            [KeyboardButton(text="📅 Дневник сегодня"), KeyboardButton(text="⏰ Напоминания")],
            [KeyboardButton(text="🔗 Привязать аккаунт"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я <b>NutriLens</b> — помогу отслеживать питание.\n\n"
        "📸 Отправь фото еды — распознаю блюдо и посчитаю КБЖУ.\n"
        "Используй кнопки меню ниже 👇",
        reply_markup=main_menu()
    )


@router.message(lambda m: m.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Как пользоваться:</b>\n\n"
        "1. Зарегистрируйся на сайте\n"
        "2. Нажми <b>Привязать аккаунт</b>\n"
        "3. Получи код на сайте в разделе Telegram\n"
        "4. Отправь команду <code>/link КОД</code>\n\n"
        "📸 Просто отправляй фото еды — я всё посчитаю!"
    )


@router.message(Command("link"))
async def cmd_link(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Укажи код: <code>/link 123456</code>\n"
            "Получи код на сайте в разделе <b>Telegram</b>."
        )
        return
    code = parts[1].strip()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE}/auth/link-telegram/{code}",
                params={"telegram_id": message.from_user.id},
            )
        if r.status_code == 200:
            data = r.json()
            await message.answer(
                f"✅ Аккаунт привязан!\n"
                f"Добро пожаловать, <b>@{data['username']}</b>!\n"
                f"Теперь фото сохраняются в твой дневник.",
                reply_markup=main_menu()
            )
        else:
            await message.answer(f"❌ {r.json().get('detail', 'Ошибка')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения: {e}")


@router.message(lambda m: m.text == "🔗 Привязать аккаунт")
async def btn_link(message: Message):
    await message.answer(
        "Чтобы привязать аккаунт:\n\n"
        "1. Открой сайт → раздел <b>Telegram</b>\n"
        "2. Нажми «Получить код»\n"
        "3. Отправь мне: <code>/link КОД</code>"
    )


@router.message(lambda m: m.text == "📊 Статистика")
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{API_BASE}/meals/totals/by-telegram/{message.from_user.id}")
        if r.status_code == 200:
            d = r.json()
            pct = int((d["calories"] / d["goal"]) * 100) if d["goal"] else 0
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            await message.answer(
                f"📊 <b>Сегодня</b>\n\n"
                f"🔥 Калории: <b>{d['calories']:.0f}</b> / {d['goal']} ккал\n"
                f"[{bar}] {pct}%\n\n"
                f"💪 Белки:    <b>{d['protein']:.1f}</b> г\n"
                f"🧈 Жиры:     <b>{d['fat']:.1f}</b> г\n"
                f"🌾 Углеводы: <b>{d['carbs']:.1f}</b> г"
            )
        elif r.status_code == 404:
            await message.answer("⚠️ Аккаунт не привязан. Нажми «Привязать аккаунт»")
        else:
            await message.answer("❌ Ошибка загрузки данных")
    except Exception as e:
        await message.answer(f"❌ {e}")


@router.message(lambda m: m.text == "⚖️ Мой вес")
async def btn_weight(message: Message):
    await message.answer(
        "Чтобы записать вес, отправь сообщение в формате:\n\n"
        "<code>вес 75.5</code>\n\n"
        "Для просмотра истории веса открой сайт → раздел <b>Вес</b>"
    )


@router.message(lambda m: m.text and m.text.lower().startswith("вес "))
async def record_weight(message: Message):
    try:
        parts = message.text.split()
        weight = float(parts[1].replace(",", "."))
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{API_BASE}/weight/by-telegram/{message.from_user.id}",
                json={"weight_kg": weight}
            )
        if r.status_code == 201:
            await message.answer(f"✅ Вес <b>{weight} кг</b> записан!")
        elif r.status_code == 404:
            await message.answer("⚠️ Аккаунт не привязан")
        else:
            await message.answer("❌ Ошибка сохранения")
    except (ValueError, IndexError):
        await message.answer("Неверный формат. Пример: <code>вес 75.5</code>")


@router.message(lambda m: m.text == "📅 Дневник сегодня")
async def btn_diary(message: Message):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{API_BASE}/meals/today/by-telegram/{message.from_user.id}")
        if r.status_code == 200:
            meals = r.json()
            if not meals:
                await message.answer("📭 Сегодня ещё нет записей")
                return
            lines = [f"📅 <b>Дневник сегодня</b>\n"]
            for m in meals:
                lines.append(f"🍽 {m['dish_name']} — <b>{m['calories']:.0f}</b> ккал")
            await message.answer("\n".join(lines))
        elif r.status_code == 404:
            await message.answer("⚠️ Аккаунт не привязан")
    except Exception as e:
        await message.answer(f"❌ {e}")


@router.message(lambda m: m.text == "⏰ Напоминания")
async def btn_reminders(message: Message):
    await message.answer(
        "Управляй напоминаниями на сайте → раздел <b>Напоминания</b>\n\n"
        "Или добавь через команду:\n"
        "<code>/remind 08:00 Завтрак</code>"
    )


@router.message(Command("remind"))
async def cmd_remind(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: <code>/remind 08:00 Завтрак</code>")
        return
    time_str, label = parts[1], parts[2]
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{API_BASE}/reminders/by-telegram/{message.from_user.id}",
                json={"remind_time": time_str + ":00", "label": label}
            )
        if r.status_code == 201:
            await message.answer(f"✅ Напоминание <b>{label}</b> в {time_str} добавлено!")
        elif r.status_code == 404:
            await message.answer("⚠️ Аккаунт не привязан")
    except Exception as e:
        await message.answer(f"❌ {e}")

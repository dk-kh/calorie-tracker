import httpx
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()
API_BASE = "http://localhost:8000/api"


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помогу отслеживать калории.\n\n"
        "📸 Отправь мне <b>фото еды</b> — распознаю блюдо и посчитаю КБЖУ.\n\n"
        "Команды:\n"
        "/link КОД — привязать аккаунт с сайта\n"
        "/stats — статистика за сегодня\n"
        "/remind ЧЧ:ММ Название — добавить напоминание\n"
        "/remindlist — список напоминаний"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Как пользоваться:</b>\n\n"
        "1. Зарегистрируйся на сайте\n"
        "2. Перейди в раздел <b>Telegram</b> и получи код\n"
        "3. Отправь мне <code>/link КОД</code>\n"
        "4. Теперь фото еды сохраняются в твой дневник!\n\n"
        "📸 Просто отправляй фото еды — я всё посчитаю."
    )


@router.message(Command("link"))
async def cmd_link(message: Message):
    """Привязка аккаунта по коду с сайта. Использование: /link 123456"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ Укажи код: <code>/link 123456</code>\n\n"
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
                f"✅ Аккаунт привязан!\n\n"
                f"Добро пожаловать, <b>@{data['username']}</b>!\n"
                f"Теперь фото еды сохраняются в твой дневник."
            )
        else:
            detail = r.json().get("detail", "Ошибка")
            await message.answer(f"❌ {detail}")
    except Exception as e:
        await message.answer(f"❌ Не удалось подключиться к серверу: {e}")

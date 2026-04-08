import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import settings
from db.database import create_tables
from core.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend", "index.html"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("DB ready")

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    bot_task = None
    if settings.telegram_token != "mock_token":
        from bot.setup import start_polling
        bot_task = asyncio.create_task(start_polling())
        logger.info("Telegram bot started")

    logger.info(f"Frontend: http://localhost:{settings.app_port}/app")
    logger.info(f"Docs:     http://localhost:{settings.app_port}/docs")
    logger.info(f"AI mode:  {'MOCK' if settings.use_mock_ai else settings.ollama_model}")
    logger.info(f"Frontend file exists: {os.path.exists(FRONTEND_PATH)}")

    yield

    scheduler.shutdown()
    if bot_task:
        bot_task.cancel()


app = FastAPI(title="Calorie Tracker API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Роуты API ── регистрируем ВСЕ до любого mount
from api.routes import auth, meals, reminders as reminder_routes, weight as weight_routes
app.include_router(auth.router, prefix="/api")
app.include_router(meals.router, prefix="/api")
app.include_router(reminder_routes.router, prefix="/api")
app.include_router(weight_routes.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/app")
async def frontend():
    if os.path.exists(FRONTEND_PATH):
        return FileResponse(FRONTEND_PATH)
    return {"error": f"Not found: {FRONTEND_PATH}"}


# НЕТ app.mount — это и было причиной 405

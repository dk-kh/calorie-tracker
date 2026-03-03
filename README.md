# 🥗 Calorie Tracker (NutriLens) — MVP

Трекер калорий с AI-распознаванием еды через фото.
**Stack:** FastAPI + Aiogram 3 + Ollama (LLaVA) + SQLite

---

## 🚀 Начало

### 1. Клонирование репо и создание виртуального окружения

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка конфига

```bash
copy .env.example .env    # Windows
# или
cp .env.example .env      # Linux/macOS
```

Отредактируйте `.env`:

- Вставьте свой `TELEGRAM_TOKEN`
- Оставьте `USE_MOCK_AI=true` для разработки без GPU

### 4. Запуск

```bash
python main.py
```

Откройте: http://localhost:8000/docs — интерактивная документация API

---

## 🤖 Переключение на AI (удаление заглушек)

### Установка Ollama

https://ollama.com/download

### Скачивание модели

```bash
# Рекомендуемая (нужно ~6 GB RAM/VRAM)
ollama pull llava:7b

# Лёгкая альтернатива (~2 GB RAM)
ollama pull moondream
```

### Изменение .env

```
USE_MOCK_AI=false
OLLAMA_MODEL=llava:7b
```

---

## 📁 Структура проекта

```
backend/
├── main.py              # точка входа
├── config.py            # настройки
├── api/routes/          # HTTP эндпоинты
├── bot/handlers/        # Telegram команды
├── core/
│   ├── ai_service.py    # логика AI (mock + real)
│   ├── scheduler.py     # напоминания
│   └── security.py      # JWT авторизация
├── db/
│   ├── models.py        # таблицы БД
│   └── crud.py          # запросы к БД
└── schemas/             # Pydantic схемы
```

---

## 🔑 API Endpoints

| Метод | URL                                           | Описание                          |
| ---------- | --------------------------------------------- | ----------------------------------------- |
| POST       | `/api/auth/register`                        | Регистрация                    |
| POST       | `/api/auth/login`                           | Вход                                  |
| GET        | `/api/auth/me`                              | Текущий пользователь   |
| POST       | `/api/meals/analyze`                        | Загрузить фото еды        |
| GET        | `/api/meals/today`                          | Приёмы пищи за сегодня |
| GET        | `/api/meals/totals`                         | КБЖУ за сегодня              |
| GET        | `/api/meals/history?target_date=2024-01-15` | История                            |
| DELETE     | `/api/meals/{id}`                           | Удалить запись               |
| GET        | `/api/reminders/`                           | Список напоминаний       |
| POST       | `/api/reminders/`                           | Добавить напоминание   |
| DELETE     | `/api/reminders/{id}`                       | Удалить напоминание     |

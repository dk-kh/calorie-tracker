from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram
    telegram_token: str = Field(default="mock_token", alias="TELEGRAM_TOKEN")

    # Security
    secret_key: str = Field(default="dev_secret_key", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = "HS256"

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./calorie_tracker.db",
        alias="DATABASE_URL"
    )

    # Ollama / AI
    use_mock_ai: bool = Field(default=True, alias="USE_MOCK_AI")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llava:7b", alias="OLLAMA_MODEL")

    # App
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()

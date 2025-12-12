from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Minerva Home Brain"
    environment: str = "dev"

    # Base URL for backend API (used by integrations)
    api_base_url: str = "http://localhost:8000"

    # Telegram bot token from .env
    telegram_bot_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

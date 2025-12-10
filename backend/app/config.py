from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Minerva Home Brain"
    environment: str = "dev"
    # Later: database_url, llm provider, etc.

    class Config:
        env_prefix = "MINERVA_"


settings = Settings()

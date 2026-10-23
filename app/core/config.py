from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SubLedger - SaaS Subscription & Billing System"
    API_V1_STR: str = ""
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./subledger.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

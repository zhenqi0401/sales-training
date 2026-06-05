"""Application configuration via pydantic-settings.

All environment variables are read from .env or the system environment with
the prefix ``SALES_TRAINING_``.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="SALES_TRAINING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ---------- App ----------
    app_name: str = "SalesTrainingAPI"
    app_version: str = "1.0.0"
    debug: bool = True

    # ---------- Database ----------
    # Expected format: mysql+asyncmy://user:pass@host:port/dbname
    database_url: str = (
        "mysql+asyncmy://training:training123@localhost:3306/sales_training"
    )

    # ---------- JWT ----------
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ---------- CORS ----------
    cors_origins: list[str] = ["*"]

    # ---------- Upload ----------
    upload_dir: str = str(Path(__file__).resolve().parent.parent.parent / "uploads")

    # ---------- Celery / Redis ----------
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # ---------- Pagination ----------
    default_page_size: int = 20
    max_page_size: int = 100


settings = Settings()

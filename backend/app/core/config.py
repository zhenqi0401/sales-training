"""Application configuration via pydantic-settings.

All environment variables are read from .env or the system environment with
the prefix ``SALES_TRAINING_``.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="SALES_TRAINING_",
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    # ---------- AI Question Generation ----------
    ai_api_key: str = ""
    ai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ai_model: str = "qwen3.5-omni-flash"
    ai_question_text_model: str = "qwen3.6-flash"
    ai_request_timeout_seconds: int = 120
    ai_video_fps: int = 1
    ai_video_max_inline_mb: int = 100
    ai_video_max_data_url_chars: int = 10_000_000
    ai_video_compress_max_width: int = 480
    ai_video_compress_crf: int = 38
    ai_video_compress_audio_bitrate: str = "32k"

    # ---------- Methodology generation ----------
    methodology_model: str = "qwen3.6-flash"

    # ---------- Practice Agent ----------
    agent_model: str = "qwen3.5-flash-2026-02-23"
    agent_max_turns: int = 15
    agent_max_tool_iterations: int = 3

    # ---------- Pagination ----------
    default_page_size: int = 20
    max_page_size: int = 100


settings = Settings()

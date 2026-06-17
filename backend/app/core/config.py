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

    # ---------- AI 出题 / 转写（火山引擎方舟 Doubao） ----------
    # ai_api_key 填火山引擎 ARK API Key；出题、ASR、方法论统一走 Responses API。
    ai_api_key: str = ""
    ai_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ai_model: str = "doubao-seed-2-0-mini-260428"
    ai_question_text_model: str = "doubao-seed-2-0-mini-260428"
    ai_request_timeout_seconds: int = 120

    # ---------- Methodology generation ----------
    methodology_model: str = "doubao-seed-2-0-mini-260428"

    # ---------- Practice Agent（火山方舟 chat/completions，流式 + 工具调用） ----------
    agent_model: str = "doubao-seed-2-0-mini-260428"
    agent_max_turns: int = 15
    agent_max_tool_iterations: int = 3

    # ---------- Pagination ----------
    default_page_size: int = 20
    max_page_size: int = 100


settings = Settings()

"""HeartAI Application Configuration.

Loads environment variables via pydantic-settings, providing strongly-typed,
validated runtime settings with secure fallbacks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_sqlite_url() -> str:
    """Returns safe user-home database path avoiding Windows Controlled Folder Access locks."""
    db_dir = Path.home() / ".heartai"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / "heartai.db"
    return f"sqlite:///{db_file.as_posix()}"


class Settings(BaseSettings):
    """Core settings for HeartAI backend service."""

    PROJECT_NAME: str = "HeartAI"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Cryptographic secrets
    SECRET_KEY: str = "heartai-clinical-intelligence-production-secret-key-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = _get_default_sqlite_url()

    # CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ]

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # ML Model Artifacts & Threshold
    MODEL_PATH: str = "models/best_model.joblib"
    PREPROCESSOR_PATH: str = "models/preprocessing_pipeline.joblib"
    METADATA_PATH: str = "models/model_metadata.json"
    OPERATING_THRESHOLD: float = 0.09

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Any) -> str:
        if isinstance(v, str) and (v == "sqlite:///./heartai.db" or v == "sqlite:///heartai.db"):
            return _get_default_sqlite_url()
        return str(v) if v else _get_default_sqlite_url()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()

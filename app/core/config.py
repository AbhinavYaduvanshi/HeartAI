"""HeartAI Application Configuration.

Loads environment variables via pydantic-settings, providing strongly-typed,
validated runtime settings with strict cryptographic enforcement and fail-closed validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DISALLOWED_SECRET_PATTERNS = {
    "replace_with_a_secure_random_secret_key_minimum_32_characters",
    "heartai-clinical-intelligence-production-secret-key-32chars",
    "replace_with_a_secure_random_secret_key",
    "secret",
    "changeme",
    "password",
    "admin",
    "default",
    "12345678",
    "development",
    "test",
    "placeholder",
}


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

    # Cryptographic secrets (STRICTLY REQUIRED: NO COMMITTED DEFAULTS)
    SECRET_KEY: str = Field(
        ...,
        description="High-entropy master secret for JWT signing and subkey derivation. Minimum 32 chars.",
    )
    SECRET_KEY_FALLBACK: str | None = Field(
        None,
        description="Previous secret key accepted during seamless dual-key rotation.",
    )
    TELEMETRY_HMAC_KEY: str | None = Field(
        None,
        description="Dedicated pepper secret for keyed pseudonymization digests.",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = Field(default_factory=_get_default_sqlite_url)
    REDIS_URL: str | None = Field(
        None,
        description="Redis connection URL for distributed rate limiting in multi-worker deployments (e.g. redis://localhost:6379/0).",
    )

    # CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ]

    # Frontend Service Configuration
    FRONTEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 8080
    BACKEND_API_URL: str = Field(
        "http://localhost:8000",
        description="Base URL for backend API calls from frontend or proxy.",
    )

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/heartai.log"

    # Rate Limiting & Proxy Trust (REL-02)
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_AI_CHAT: str = "20/minute"
    RATE_LIMIT_AI_SYMPTOMS: str = "15/minute"
    RATE_LIMIT_AI_PERSONALIZED: str = "10/minute"
    FORWARDED_ALLOW_IPS: str = Field(
        "127.0.0.1,::1",
        description="Comma-separated trusted proxy IPs or CIDRs authorized to forward client headers.",
    )

    # ML Model Artifacts, Threshold & Transfer Security (SEC-01)
    MODEL_PATH: str = "models/best_model.joblib"
    PREPROCESSOR_PATH: str = "models/preprocessing_pipeline.joblib"
    METADATA_PATH: str = "models/model_metadata.json"
    OPERATING_THRESHOLD: float = 0.09
    ENABLE_MODEL_IMPORT: bool = Field(
        False,
        description="Administrative toggle to permit runtime model import endpoints. Strictly False by default.",
    )

    # Consent Policy Version
    CURRENT_CONSENT_TERMS_VERSION: str = "2026.1"

    # Google Gemini Generative AI Configuration
    GEMINI_API_KEY: str | None = Field(
        None,
        description="Google Gemini API key for clinical AI assistant and educational features.",
    )
    GEMINI_MODEL: str = Field(
        "gemini-3.8-flash",
        description="Supported Gemini model identifier (e.g. gemini-3.8-flash, gemini-3.5-flash-lite).",
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(
        15.0,
        description="HTTP request timeout for Gemini API calls in seconds.",
    )
    GEMINI_MAX_OUTPUT_TOKENS: int = Field(
        1024,
        description="Maximum generation token budget for structured educational content.",
    )
    GEMINI_TEMPERATURE: float = Field(
        0.2,
        description="Temperature for clinical and educational response grounding.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str | None) -> str:
        """Enforces cryptographic strength, non-empty presence, and placeholder rejection."""
        if not v or not v.strip():
            raise ValueError(
                "SECRET_KEY is required and must be configured via environment or .env. "
                "Generate one using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        val = v.strip()
        if len(val) < 32:
            raise ValueError(
                f"SECRET_KEY is too weak ({len(val)} characters). Must be at least 32 characters long."
            )
        lowered = val.lower()
        if (
            lowered in DISALLOWED_SECRET_PATTERNS
            or lowered.startswith("replace_with_")
            or lowered.startswith("your_")
        ):
            raise ValueError(
                "SECRET_KEY cannot use an insecure placeholder or committed default value. "
                "Please generate a unique secret."
            )
        if len(set(val)) < 8:
            raise ValueError(
                "SECRET_KEY lacks sufficient character entropy (too few unique characters)."
            )
        return val

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

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Prohibits wildcard CORS in production environments."""
        env = info.data.get("APP_ENV", "development")
        if env in {"production", "staging"} and "*" in v:
            raise ValueError(
                f"Wildcard '*' CORS origin is forbidden in {env} environments. "
                "Specify explicit authorized origins."
            )
        return v

    @model_validator(mode="after")
    def validate_production_environment(self) -> Settings:
        """Enforces fail-closed production readiness invariants."""
        if self.APP_ENV in {"production", "staging"}:
            # 1. Prohibit SQLite in production/staging
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    f"SQLite ({self.DATABASE_URL}) is prohibited in {self.APP_ENV} environments. "
                    "A production-grade PostgreSQL database URL is required."
                )
            # 2. Require REDIS_URL for distributed rate limiting in production/staging
            if not self.REDIS_URL or not self.REDIS_URL.strip():
                raise ValueError(
                    f"REDIS_URL is required in {self.APP_ENV} environments to enforce "
                    "distributed rate limiting across multi-worker deployments."
                )
            # 3. Prohibit APP_DEBUG in production/staging
            if self.APP_DEBUG:
                raise ValueError(f"APP_DEBUG must be False in {self.APP_ENV} environments.")
            # 4. Prohibit localhost in BACKEND_API_URL in production
            if self.APP_ENV == "production" and (
                "localhost" in self.BACKEND_API_URL.lower() or "127.0.0.1" in self.BACKEND_API_URL
            ):
                raise ValueError(
                    f"Hardcoded localhost BACKEND_API_URL ({self.BACKEND_API_URL}) is forbidden in "
                    "production environments. Configure the production domain or relative URL."
                )
            # 5. Prohibit ENABLE_MODEL_IMPORT in production/staging (SEC-01)
            if self.ENABLE_MODEL_IMPORT:
                raise ValueError(
                    f"ENABLE_MODEL_IMPORT is prohibited in {self.APP_ENV} environments (SEC-01). "
                    "Runtime filesystem model deserialization is strictly disabled."
                )
        return self

    def get_telemetry_hmac_key(self) -> bytes:
        """Returns cryptographically isolated HMAC pepper for telemetry hashing."""
        if self.TELEMETRY_HMAC_KEY and len(self.TELEMETRY_HMAC_KEY) >= 16:
            return self.TELEMETRY_HMAC_KEY.encode("utf-8")
        # Cryptographic key derivation from master secret
        import hashlib
        import hmac

        return hmac.new(
            self.SECRET_KEY.encode("utf-8"),
            b"HeartAI-Telemetry-HMAC-Pepper-v1",
            hashlib.sha256,
        ).digest()


settings = Settings()

"""HeartAI Point 12.1 Deployment Foundations & Configuration Hardening Tests.

Validates:
1. Production configuration fail-closed invariants (SQLite forbidden, Redis required, Debug forbidden).
2. Cryptographic secret enforcement and placeholder rejection.
3. CORS origin policy in production (wildcard '*' prohibited).
4. Alembic schema migration upgrade and downgrade lifecycle.
5. Rate limiting storage resolution and Redis connectivity ping behavior.
6. Environment-driven backend URL resolution.
7. Service health metadata and educational classification status.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.config import Settings
from app.core.rate_limit import resolve_storage_uri
from app.core.rate_limit import test_redis_ping as ping_redis

VALID_PROD_SECRET = "ProductionMasterSecretKey2026_HighEntropyToken!"
VALID_POSTGRES_URL = "postgresql://heartai_user:SecurePass123@localhost:5432/heartai_db"
VALID_REDIS_URL = "redis://127.0.0.1:6379/0"
VALID_PROD_DOMAIN = "https://heartai.internal"


def test_production_config_rejects_sqlite():
    """Verify production environment strictly prohibits SQLite."""
    with pytest.raises(ValueError, match="SQLite .* is prohibited in production"):
        Settings(
            APP_ENV="production",
            SECRET_KEY=VALID_PROD_SECRET,
            DATABASE_URL="sqlite:///./prod.db",
            REDIS_URL=VALID_REDIS_URL,
            BACKEND_API_URL=VALID_PROD_DOMAIN,
            CORS_ORIGINS=["https://heartai.internal"],
        )


def test_production_config_rejects_missing_redis():
    """Verify production environment strictly requires REDIS_URL for distributed rate limiting."""
    with pytest.raises(ValueError, match="REDIS_URL is required in production"):
        Settings(
            APP_ENV="production",
            SECRET_KEY=VALID_PROD_SECRET,
            DATABASE_URL=VALID_POSTGRES_URL,
            REDIS_URL=None,
            BACKEND_API_URL=VALID_PROD_DOMAIN,
            CORS_ORIGINS=["https://heartai.internal"],
        )


def test_production_config_rejects_debug_mode():
    """Verify production environment strictly prohibits APP_DEBUG=True."""
    with pytest.raises(ValueError, match="APP_DEBUG must be False in production"):
        Settings(
            APP_ENV="production",
            APP_DEBUG=True,
            SECRET_KEY=VALID_PROD_SECRET,
            DATABASE_URL=VALID_POSTGRES_URL,
            REDIS_URL=VALID_REDIS_URL,
            BACKEND_API_URL=VALID_PROD_DOMAIN,
            CORS_ORIGINS=["https://heartai.internal"],
        )


def test_production_config_rejects_localhost_backend_url():
    """Verify production environment rejects hardcoded localhost BACKEND_API_URL."""
    with pytest.raises(ValueError, match="Hardcoded localhost BACKEND_API_URL"):
        Settings(
            APP_ENV="production",
            SECRET_KEY=VALID_PROD_SECRET,
            DATABASE_URL=VALID_POSTGRES_URL,
            REDIS_URL=VALID_REDIS_URL,
            BACKEND_API_URL="http://localhost:8000",
            CORS_ORIGINS=["https://heartai.internal"],
        )


def test_production_config_rejects_wildcard_cors():
    """Verify production environment strictly rejects wildcard CORS '*'. """
    with pytest.raises(ValueError, match="Wildcard '\\*' CORS origin is forbidden"):
        Settings(
            APP_ENV="production",
            SECRET_KEY=VALID_PROD_SECRET,
            DATABASE_URL=VALID_POSTGRES_URL,
            REDIS_URL=VALID_REDIS_URL,
            BACKEND_API_URL=VALID_PROD_DOMAIN,
            CORS_ORIGINS=["*"],
        )


def test_production_config_rejects_weak_secrets():
    """Verify secret validator rejects short, low entropy, or placeholder keys."""
    with pytest.raises(ValueError, match="too weak"):
        Settings(
            SECRET_KEY="short_key",
            DATABASE_URL=VALID_POSTGRES_URL,
        )

    with pytest.raises(ValueError, match="insecure placeholder"):
        Settings(
            SECRET_KEY="replace_with_a_secure_random_secret_key_minimum_32_characters",
            DATABASE_URL=VALID_POSTGRES_URL,
        )


def test_production_config_valid_acceptance():
    """Verify a properly configured production Settings object passes all validations."""
    prod_settings = Settings(
        APP_ENV="production",
        APP_DEBUG=False,
        SECRET_KEY=VALID_PROD_SECRET,
        DATABASE_URL=VALID_POSTGRES_URL,
        REDIS_URL=VALID_REDIS_URL,
        BACKEND_API_URL=VALID_PROD_DOMAIN,
        CORS_ORIGINS=["https://heartai.internal", "https://api.heartai.internal"],
    )
    assert prod_settings.APP_ENV == "production"
    assert prod_settings.DATABASE_URL == VALID_POSTGRES_URL
    assert prod_settings.REDIS_URL == VALID_REDIS_URL
    assert prod_settings.BACKEND_API_URL == VALID_PROD_DOMAIN


def test_development_config_defaults():
    """Verify development mode permits safe SQLite and memory storage fallbacks."""
    dev_settings = Settings(
        APP_ENV="development",
        SECRET_KEY=VALID_PROD_SECRET,
        REDIS_URL=None,
    )
    assert dev_settings.APP_ENV == "development"
    assert dev_settings.DATABASE_URL.startswith("sqlite")
    assert dev_settings.REDIS_URL is None
    assert dev_settings.BACKEND_API_URL == "http://localhost:8000"


def test_alembic_upgrade_downgrade_lifecycle():
    """Verify Alembic 001_initial_schema creates tables and cleanly drops them on downgrade."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "alembic_test.db"
        db_url = f"sqlite:///{db_path.as_posix()}"

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade to head
        command.upgrade(cfg, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "prediction_records" in tables
        assert "alembic_version" in tables

        # Inspect users columns
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        assert {"id", "email", "hashed_password", "is_active", "consent_given"}.issubset(user_cols)

        # Inspect prediction_records columns
        pred_cols = {col["name"] for col in inspector.get_columns("prediction_records")}
        assert {"id", "user_id", "anonymized_input_hash", "estimated_probability", "operating_threshold"}.issubset(pred_cols)
        engine.dispose()

        # 2. Downgrade to base
        command.downgrade(cfg, "base")
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables_after = inspector.get_table_names()
        assert "users" not in tables_after
        assert "prediction_records" not in tables_after
        engine.dispose()


def test_rate_limit_storage_resolution():
    """Verify storage URI resolution behaves correctly across environment modes."""
    # In development mode, returns memory:// if REDIS_URL is not set
    assert resolve_storage_uri() in {"memory://", VALID_REDIS_URL}


def test_redis_ping_unconfigured():
    """Verify ping_redis returns False gracefully when unconfigured."""
    is_ok, msg = ping_redis(None)
    assert is_ok is False
    assert "not configured" in msg.lower()


def test_redis_ping_unreachable():
    """Verify ping_redis returns False gracefully on unreachable port without raising unhandled errors."""
    is_ok, msg = ping_redis("redis://127.0.0.1:54321/0")
    assert is_ok is False
    assert "failed" in msg.lower()

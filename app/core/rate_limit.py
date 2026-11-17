"""HeartAI Rate Limiting Module using slowapi.

Provides distributed rate limiting across multi-worker deployments via Redis,
with local in-memory fallback strictly for development and testing environments.
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger("heartai.core.rate_limit")


def resolve_storage_uri() -> str:
    """Resolves the rate limit storage URI based on environment mode.

    Fails closed in production and staging if REDIS_URL is not configured.
    """
    if settings.APP_ENV in {"production", "staging"}:
        if not settings.REDIS_URL or not settings.REDIS_URL.strip():
            raise RuntimeError(
                f"REDIS_URL must be configured in {settings.APP_ENV} mode to enforce "
                "distributed rate limiting across multi-worker processes. In-memory fallback is prohibited."
            )
        return settings.REDIS_URL
    return settings.REDIS_URL if settings.REDIS_URL else "memory://"


def test_redis_ping(redis_url: str | None = None) -> tuple[bool, str]:
    """Tests live Redis connectivity. Returns (is_connected, message)."""
    target_url = redis_url or settings.REDIS_URL
    if not target_url:
        return False, "REDIS_URL is not configured."
    try:
        import redis

        client = redis.from_url(target_url, socket_timeout=2.0)
        client.ping()
        return True, "Redis connection successful."
    except Exception as err:
        logger.warning("Redis ping failed: %s", type(err).__name__)
        return False, f"Redis connection failed ({type(err).__name__})."


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=resolve_storage_uri(),
)

"""HeartAI Rate Limiting Module using slowapi.

Provides distributed rate limiting across multi-worker deployments via Redis,
with local in-memory fallback strictly for development and testing environments.
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger("heartai.core.rate_limit")


def get_trusted_client_ip(request: Request) -> str:
    """Extracts client IP address safely, trusting forwarded headers ONLY from authorized proxies (REL-02).

    Prevents IP spoofing via crafted X-Forwarded-For or X-Real-IP headers when requests originate
    from untrusted sources. Prefers X-Real-IP (overwritten by reverse proxy) and falls back to
    the rightmost proxy-appended entry (parts[-1]) of X-Forwarded-For (Point 13.2B).
    """
    client_host = request.client.host if request.client else "127.0.0.1"

    # Parse configured trusted proxy IPs (e.g. "127.0.0.1,::1")
    trusted_proxies = {ip.strip() for ip in settings.FORWARDED_ALLOW_IPS.split(",") if ip.strip()}

    # If direct connection is NOT from a trusted reverse proxy, use socket host (disregard headers)
    if client_host not in trusted_proxies:
        return client_host

    # When connected from trusted proxy (e.g. Nginx on 127.0.0.1), inspect verified forwarded headers
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    # Fallback to rightmost proxy-appended address in X-Forwarded-For ($proxy_add_x_forwarded_for)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for and x_forwarded_for.strip():
        parts = [p.strip() for p in x_forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[-1]

    return client_host


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
    key_func=get_trusted_client_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=resolve_storage_uri(),
)

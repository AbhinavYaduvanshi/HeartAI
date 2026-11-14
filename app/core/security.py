"""HeartAI Security, Authentication & Cryptography Module.

Implements OWASP-recommended Argon2id password hashing, RFC 7519 JSON Web Tokens (JWT)
with strict algorithm bounding, dual-key rotation, and timing-attack countermeasures.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

logger = logging.getLogger("heartai.security")

# Initialize Argon2id password hasher with RFC 9106 recommended parameters
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

# Precomputed dummy Argon2 hash for constant-time mitigation of user enumeration timing attacks
_DUMMY_ARGON2_HASH = _ph.hash("HeartAI-Timing-Mitigation-Precomputed-Salted-Password-2026")


def hash_password(password: str) -> str:
    """Hashes a plain-text password using Argon2id with unique cryptographic salt."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against an Argon2id hash in constant time."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def verify_dummy_password(candidate_password: str) -> bool:
    """Consumes identical Argon2 CPU/memory time when a user account does not exist.

    Mitigates response-latency timing enumeration attacks. Always returns False.
    """
    try:
        _ph.verify(_DUMMY_ARGON2_HASH, candidate_password)
    except Exception:
        pass
    return False


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a cryptographically signed JSON Web Token (JWT) with strict expiration."""
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    # Explicit algorithm bounding (never permits "none" or algorithm substitution)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodes and validates a JWT token against signature, expiration, and algorithm.

    Supports zero-downtime secret key rotation via SECRET_KEY_FALLBACK.
    """
    decode_options = {
        "verify_signature": True,
        "verify_exp": True,
        "require": ["sub", "exp", "iat"],
    }

    # 1. Attempt verification with active primary SECRET_KEY
    try:
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options=decode_options,
        )
        return decoded
    except jwt.InvalidSignatureError:
        # 2. If signature fails and dual-key rotation is active, try fallback key
        if settings.SECRET_KEY_FALLBACK:
            try:
                decoded = jwt.decode(
                    token,
                    settings.SECRET_KEY_FALLBACK,
                    algorithms=[settings.ALGORITHM],
                    options=decode_options,
                )
                logger.info("Token validated using legacy rotation fallback key.")
                return decoded
            except (jwt.PyJWTError, Exception):
                pass
        return None
    except (jwt.PyJWTError, Exception):
        return None

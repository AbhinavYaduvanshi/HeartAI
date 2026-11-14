"""HeartAI Trusted Server-Side Informed Consent Verification Service.

Enforces fail-closed consent verification using server-side database records.
Never trusts client-asserted consent booleans as proof of consent.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.ml.preprocessing import ALL_INPUT_FEATURES

APPROVED_SURVEY_FEATURE_SET = set(ALL_INPUT_FEATURES)


class ConsentVerificationError(Exception):
    """Raised when trusted informed consent verification fails."""


def verify_trusted_user_consent(user: User | None) -> tuple[bool, str]:
    """Verifies consent against trusted server-side User record.

    Returns:
        (True, "Consent verified") if consent is active and up-to-date.
        (False, reason_str) if unauthenticated, missing, revoked, or outdated.
    """
    if user is None:
        return False, "Authentication required: personalized AI processing requires an authenticated user account."

    if not getattr(user, "is_active", True):
        return False, "User account is deactivated."

    if getattr(user, "consent_revoked", False):
        return False, "Informed consent was previously revoked by the user."

    if not getattr(user, "consent_given", False):
        return False, "User has not granted affirmative informed consent in application records."

    user_terms_ver = getattr(user, "consent_terms_version", None)
    if user_terms_ver != settings.CURRENT_CONSENT_TERMS_VERSION:
        return (
            False,
            f"Consent terms version '{user_terms_ver}' is outdated or unverified. "
            f"Active policy requires version '{settings.CURRENT_CONSENT_TERMS_VERSION}'.",
        )

    return True, "Consent verified"


def record_user_consent(
    user: User,
    db: Session,
    consent_given: bool,
    terms_version: str,
) -> User:
    """Updates and commits trusted consent state for an authenticated user."""
    user.consent_given = bool(consent_given)
    user.consent_terms_version = terms_version if consent_given else None
    user.consent_revoked = not consent_given
    user.consent_updated_at = datetime.datetime.now(datetime.UTC)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def filter_approved_survey_features(features: dict[str, Any]) -> dict[str, Any]:
    """Strictly whitelists only approved 25 CDC BRFSS feature keys.

    Strips any extra keys, identifiers, credentials, or arbitrary text.
    """
    if not isinstance(features, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in features.items():
        if key in APPROVED_SURVEY_FEATURE_SET:
            if isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, str):
                try:
                    sanitized[key] = float(value) if "." in value else int(value)
                except ValueError:
                    pass
    return sanitized

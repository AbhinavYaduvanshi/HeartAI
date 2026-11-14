"""HeartAI Prediction Business Logic Orchestration Service.

Handles input alignment, model execution, consent-gated telemetry persistence,
keyed HMAC pseudonymization, and non-diagnostic response formatting.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PredictionRecord, User
from app.ml.preprocessing import prepare_feature_dataframe
from app.schemas.prediction import (
    DEFAULT_PRIVACY_NOTICE,
    STANDARD_RESEARCH_LIMITATIONS,
    PredictionRequest,
    PredictionResponse,
)
from app.services.model_service import model_service

logger = logging.getLogger("heartai.services.prediction")


def compute_pseudonymous_feature_hmac(input_dict: dict[str, Any]) -> str:
    """Computes a keyed HMAC-SHA256 digest of normalized feature values.

    SECURITY & PRIVACY DISCLOSURE:
    A plain unsalted SHA-256 hash of discrete, low-cardinality survey features
    (demographic tiers, binary health flags) provides insufficient anonymization
    against offline dictionary or rainbow-table precomputation attacks. An attacker
    enumerating common demographic combinations could invert unsalted hashes.

    To eliminate offline dictionary generation, HeartAI computes a keyed HMAC-SHA256
    using an isolated server-side pepper secret (TELEMETRY_HMAC_KEY) stored in environment
    configuration. Without access to this server-side key, external parties cannot precalculate
    or match feature digests.

    Raw survey feature values are strictly NEVER persisted in the database.
    """
    key = settings.get_telemetry_hmac_key()
    canonical_json = json.dumps(input_dict, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(key, canonical_json.encode("utf-8"), hashlib.sha256).hexdigest()


def process_cardiovascular_prediction(
    request: PredictionRequest,
    db: Session | None = None,
    current_user: User | None = None,
) -> PredictionResponse:
    """Executes validated cardiovascular prediction pipeline.

    - Validates feature vector against CDC BRFSS boundaries
    - Executes calibrated model inference
    - Strictly checks explicit affirmative consent AND consent terms version before persistence
    - Employs keyed HMAC pseudonymization for telemetry audit records
    - Returns standardized educational estimation response
    """
    # 1. Align features
    input_dict = request.model_dump(exclude={"user_consent_given", "consent_terms_version", "client_id"})
    input_df = prepare_feature_dataframe(input_dict)

    # 2. Model inference
    prob, binary_flag = model_service.predict_probability(input_df)

    # 3. Privacy-preserving consent-gated persistence
    # Persistence requires BOTH explicit affirmative boolean AND valid acknowledged consent terms version
    consent_recorded = False
    valid_consent = (
        request.user_consent_given is True
        and request.consent_terms_version == settings.CURRENT_CONSENT_TERMS_VERSION
    )

    if valid_consent and db is not None:
        try:
            hmac_digest = compute_pseudonymous_feature_hmac(input_dict)
            record = PredictionRecord(
                user_id=current_user.id if current_user else None,
                anonymized_input_hash=hmac_digest,
                estimated_probability=round(prob, 6),
                binary_classification=binary_flag,
                operating_threshold=model_service.operating_threshold,
                model_version=model_service.metadata.get("version", "2.1.0"),
                user_consent_given=True,
            )
            db.add(record)
            db.commit()
            consent_recorded = True
            logger.info(
                "Affirmative consent verified (terms v%s): Persisted telemetry audit record (ID=%s, auth=%s)",
                request.consent_terms_version,
                record.id,
                bool(current_user),
            )
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist consent-gated prediction record: %s", exc)
    else:
        logger.debug(
            "Telemetry persistence bypassed: consent_given=%s, terms_version=%s",
            request.user_consent_given,
            request.consent_terms_version,
        )

    metadata = model_service.get_metadata()
    model_name = metadata.get(
        "model_name",
        "HeartAI BRFSS Research Classifier (Calibrated Logistic Regression)",
    )
    model_version = metadata.get("version", "2.1.0")

    return PredictionResponse(
        metric_label="Estimated probability of reported historical cardiovascular disease",
        estimated_probability=round(prob, 4),
        estimated_probability_percentage=round(prob * 100.0, 2),
        binary_classification=binary_flag,
        operating_threshold=model_service.operating_threshold,
        model_name=model_name,
        model_version=model_version,
        calibration_status="calibrated_isotonic_cv5",
        output_type="educational_estimate",
        clinical_validation=False,
        consent_recorded=consent_recorded,
        consent_terms_version=request.consent_terms_version if consent_recorded else None,
        privacy_notice=DEFAULT_PRIVACY_NOTICE,
        limitations=list(STANDARD_RESEARCH_LIMITATIONS),
        educational_disclaimer=(
            "Educational research estimate; not a clinical diagnostic device. "
            "Evaluates self-reported historical survey patterns, not future incident cardiovascular events."
        ),
    )

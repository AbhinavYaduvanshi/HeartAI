"""HeartAI Prediction Business Logic Orchestration Service.

Handles input alignment, model execution, consent-gated telemetry persistence,
and non-diagnostic response formatting.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import PredictionRecord, User
from app.ml.preprocessing import prepare_feature_dataframe
from app.schemas.prediction import (
    STANDARD_RESEARCH_LIMITATIONS,
    PredictionRequest,
    PredictionResponse,
)
from app.services.model_service import model_service

logger = logging.getLogger("heartai.services.prediction")


def hash_patient_input(input_dict: dict[str, Any]) -> str:
    """Generates an anonymized SHA-256 hash of patient input features."""
    sorted_json = json.dumps(input_dict, sort_keys=True, default=str)
    return hashlib.sha256(sorted_json.encode("utf-8")).hexdigest()


def process_cardiovascular_prediction(
    request: PredictionRequest,
    db: Session | None = None,
    current_user: User | None = None,
) -> PredictionResponse:
    """Executes validated cardiovascular prediction pipeline.

    - Validates feature vector
    - Executes calibrated model inference
    - Persists audit record if and only if explicit consent is provided
    - Returns standardized educational estimation response
    """
    # 1. Align features
    input_dict = request.model_dump(exclude={"user_consent_given", "client_id"})
    input_df = prepare_feature_dataframe(input_dict)

    # 2. Model inference
    prob, binary_flag = model_service.predict_probability(input_df)

    # 3. Privacy-preserving consent-gated persistence
    consent_recorded = False
    if request.user_consent_given and db is not None:
        try:
            anon_hash = hash_patient_input(input_dict)
            record = PredictionRecord(
                user_id=current_user.id if current_user else None,
                anonymized_input_hash=anon_hash,
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
                "Consent granted: Persisted prediction audit record (ID=%s, binary_flag=%d, prob=%.4f)",
                record.id,
                binary_flag,
                prob,
            )
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist consent-gated prediction record: %s", exc)
    else:
        logger.debug("No consent given or DB omitted: prediction processed ephemerally without persistence.")

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
        limitations=list(STANDARD_RESEARCH_LIMITATIONS),
        educational_disclaimer=(
            "Educational research estimate; not a clinical diagnostic device. "
            "Evaluates self-reported historical survey patterns, not future incident cardiovascular events."
        ),
    )

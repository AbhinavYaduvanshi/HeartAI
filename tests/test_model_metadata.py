"""Tests for HeartAI Model Metadata Schemas."""

import pytest
from pydantic import ValidationError

from app.ml.model_metadata import (
    ModelArtifactFormat,
    ModelMetadata,
    ModelMetrics,
)


def test_model_metrics_valid():
    """Verify metrics within [0, 1] range validate cleanly."""
    metrics = ModelMetrics(
        accuracy=0.852,
        roc_auc=0.852,
        sensitivity_recall=0.803,
        specificity=0.736,
        f1_score=0.347,
        precision=0.222,
        brier_score=0.158,
    )
    assert metrics.roc_auc == 0.852
    assert metrics.accuracy == 0.852


def test_model_metrics_out_of_bounds():
    """Verify metrics > 1.0 or < 0.0 raise ValidationError."""
    with pytest.raises(ValidationError):
        ModelMetrics(
            accuracy=1.25,  # Invalid: > 1.0
            roc_auc=0.85,
            sensitivity_recall=0.80,
            specificity=0.70,
            f1_score=0.35,
            precision=0.25,
        )


def test_model_metadata_valid():
    """Verify full ModelMetadata instance creation and serialization."""
    meta = ModelMetadata(
        model_id="heartai-test-v1",
        model_name="HeartAI Test Model",
        version="2.0.0",
        architecture="logistic_regression",
        artifact_format=ModelArtifactFormat.JOBLIB,
        artifact_filename="best_model.joblib",
        sha256_checksum="a" * 64,
        metrics=ModelMetrics(
            accuracy=0.85,
            roc_auc=0.85,
            sensitivity_recall=0.80,
            specificity=0.70,
            f1_score=0.35,
            precision=0.25,
        ),
    )
    assert meta.model_id == "heartai-test-v1"
    dump = meta.model_dump()
    assert dump["artifact_format"] == "joblib"


def test_invalid_artifact_format():
    """Verify invalid format raises ValidationError."""
    with pytest.raises(ValidationError):
        ModelMetadata(
            model_id="heartai-bad-format",
            model_name="Bad Model",
            version="1.0.0",
            architecture="XGBoost",
            artifact_format="unsupported_format_xyz",
            artifact_filename="model.xyz",
            sha256_checksum="b" * 64,
            metrics=ModelMetrics(
                accuracy=0.8,
                roc_auc=0.8,
                sensitivity_recall=0.8,
                specificity=0.8,
                f1_score=0.8,
                precision=0.8,
            ),
        )

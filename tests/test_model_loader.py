"""Tests for HeartAI Model Loader & Integrity Verification."""

from pathlib import Path

import pytest

from app.ml.model_loader import (
    ModelCompatibilityError,
    ModelSecurityError,
    compute_file_sha256,
    load_model_artifact,
    load_model_metadata,
)
from app.ml.model_metadata import ModelMetadata


def test_compute_file_sha256():
    """Verify SHA-256 computation returns 64-char hex string."""
    best_model_path = Path("models/best_model.joblib")
    assert best_model_path.is_file()
    digest = compute_file_sha256(best_model_path)
    assert len(digest) == 64
    assert digest.isalnum()


def test_load_model_metadata_success():
    """Verify loading and parsing valid model metadata manifest."""
    meta_path = Path("models/model_metadata.json")
    assert meta_path.is_file()
    meta = load_model_metadata(meta_path)
    assert isinstance(meta, ModelMetadata)
    assert meta.version == "2.0.0"
    assert meta.artifact_filename == "best_model.joblib"


def test_load_model_metadata_missing():
    """Verify FileNotFoundError on missing metadata file."""
    with pytest.raises(FileNotFoundError):
        load_model_metadata("models/non_existent_metadata.json")


def test_load_model_artifact_success():
    """Verify successful loading of trained joblib model."""
    meta = load_model_metadata("models/model_metadata.json")
    model = load_model_artifact("models/best_model.joblib", metadata=meta, verify_checksum=True)
    assert model is not None
    assert hasattr(model, "predict") or hasattr(model, "predict_proba")


def test_load_model_artifact_checksum_mismatch():
    """Verify ModelSecurityError when actual hash differs from manifest."""
    meta = load_model_metadata("models/model_metadata.json")
    # Mutate checksum to simulate corrupted artifact
    corrupted_meta = meta.model_copy(update={"sha256_checksum": "0" * 64})
    with pytest.raises(ModelSecurityError):
        load_model_artifact("models/best_model.joblib", metadata=corrupted_meta, verify_checksum=True)


def test_load_model_artifact_unsupported_format():
    """Verify ModelCompatibilityError on invalid file extension."""
    with pytest.raises(ModelCompatibilityError):
        load_model_artifact("models/model_comparison.csv", verify_checksum=False)


def test_load_all_trained_models():
    """Verify every exported algorithm artifact loads successfully."""
    models_dir = Path("models")
    expected_models = [
        "best_model.joblib",
        "logistic_regression.joblib",
        "random_forest.joblib",
        "extra_trees.joblib",
        "enriched_random_forest.joblib",
        "tree_weighted_random_forest.joblib",
        "adaboost.joblib",
        "gradient_boosting.joblib",
        "decision_tree.joblib",
        "entropy_decision_tree.joblib",
        "support_vector_machine.joblib",
        "stacking_model.joblib",
    ]
    for model_file in expected_models:
        path = models_dir / model_file
        assert path.is_file(), f"Missing exported model: {model_file}"
        m = load_model_artifact(path, verify_checksum=False)
        assert m is not None

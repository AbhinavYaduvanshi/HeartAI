"""Tests for HeartAI Model Registry."""

import pytest

from app.ml.model_registry import ModelRegistry


def test_registry_scan_and_register():
    """Verify registry discovers models in models/ directory."""
    reg = ModelRegistry(models_dir="models")
    count = reg.scan_and_register()
    assert count >= 1
    models = reg.list_models()
    assert len(models) >= 1


def test_registry_get_active_model():
    """Verify retrieving currently promoted active production model."""
    reg = ModelRegistry(models_dir="models")
    reg.scan_and_register()
    model, metadata = reg.get_active_model()
    assert model is not None
    assert metadata is not None
    assert metadata.version in ["1.0.0", "2.0.0"]


def test_registry_unknown_model_raises():
    """Verify KeyError when requesting non-existent model."""
    reg = ModelRegistry(models_dir="models")
    reg.scan_and_register()
    with pytest.raises(KeyError):
        reg.get_model("completely_nonexistent_model_id")

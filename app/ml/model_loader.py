"""HeartAI Multi-Format Model Loader with Cryptographic Checksums.

Supports loading serialized clinical machine learning models in:
- .joblib (Scikit-Learn, XGBoost)
- .pkl (Pickle pipelines)
- .pt (PyTorch state_dict & TorchScript models)

Includes strict SHA-256 artifact integrity verification and metadata enforcement.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any

import joblib
import torch

from app.ml.model_metadata import ModelArtifactFormat, ModelMetadata

logger = logging.getLogger("heartai.ml.loader")


class ModelSecurityError(Exception):
    """Raised when an artifact checksum does not match its registered manifest."""


class ModelCompatibilityError(Exception):
    """Raised when an artifact format is unknown or environment versions conflict."""


def compute_file_sha256(filepath: Path | str) -> str:
    """Calculates the SHA-256 cryptographic digest of a model artifact."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def load_model_metadata(metadata_path: Path | str) -> ModelMetadata:
    """Loads and validates a ModelMetadata JSON manifest."""
    path = Path(metadata_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model metadata file not found at: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ModelMetadata.model_validate(data)


def load_model_artifact(
    artifact_path: Path | str,
    metadata: ModelMetadata | None = None,
    verify_checksum: bool = True,
    device: str = "cpu",
) -> Any:
    """Loads a serialized model artifact with optional checksum verification."""
    path = Path(artifact_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact file not found at: {path}")

    # Checksum verification
    if verify_checksum and metadata is not None:
        actual_hash = compute_file_sha256(path)
        if actual_hash != metadata.sha256_checksum:
            raise ModelSecurityError(
                f"Artifact checksum verification failed for {path.name}!\n"
                f"Expected: {metadata.sha256_checksum}\n"
                f"Actual:   {actual_hash}\n"
                "Refusing to load potentially corrupted or untrusted artifact."
            )
        logger.info("Checksum verified for model artifact: %s", path.name)

    # Determine artifact format
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"joblib"}:
        format_type = ModelArtifactFormat.JOBLIB
    elif suffix in {"pkl", "pickle"}:
        format_type = ModelArtifactFormat.PICKLE
    elif suffix in {"pt", "pth"}:
        format_type = ModelArtifactFormat.PYTORCH
    else:
        raise ModelCompatibilityError(f"Unsupported model artifact extension: .{suffix}")

    # Deserialization
    try:
        if format_type == ModelArtifactFormat.JOBLIB:
            model = joblib.load(path)
            logger.info("Loaded Joblib model: %s", path.name)
            return model

        elif format_type == ModelArtifactFormat.PICKLE:
            with open(path, "rb") as f:
                model = pickle.load(f)
            logger.info("Loaded Pickle model: %s", path.name)
            return model

        elif format_type == ModelArtifactFormat.PYTORCH:
            target_device = torch.device(device)
            try:
                model = torch.load(path, map_location=target_device, weights_only=False)
            except Exception:
                model = torch.jit.load(path, map_location=target_device)
            logger.info("Loaded PyTorch model to device %s: %s", device, path.name)
            return model

    except Exception as exc:
        logger.error("Failed to deserialize model artifact %s: %s", path.name, exc)
        raise ModelCompatibilityError(f"Failed to load {format_type.value} artifact: {exc}") from exc


def load_model_bundle(model_dir: Path | str, device: str = "cpu") -> tuple[Any, ModelMetadata]:
    """Convenience loader that loads both metadata.json and the artifact from a directory."""
    directory = Path(model_dir)
    metadata_file = directory / "metadata.json"
    if not metadata_file.exists():
        metadata_file = directory / "model_metadata.json"

    metadata = load_model_metadata(metadata_file)
    artifact_file = directory / metadata.artifact_filename

    model = load_model_artifact(artifact_file, metadata=metadata, verify_checksum=True, device=device)
    return model, metadata

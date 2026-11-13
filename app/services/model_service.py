"""HeartAI Model Loading and Execution Service.

Provides thread-safe singleton model management, SHA-256 checksum verification,
pipeline transformations, and calibrated probability predictions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.core.config import settings

logger = logging.getLogger("heartai.services.model")


class ModelIntegrityError(Exception):
    """Raised when an artifact's cryptographic hash does not match metadata."""


class ModelLoadError(Exception):
    """Raised when an artifact cannot be found or loaded."""


class ModelService:
    """Manages ML model lifecycle, integrity verification, and inference."""

    _instance: ModelService | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.model: Any | None = None
        self.preprocessor: Any | None = None
        self.metadata: dict[str, Any] = {}
        self.is_loaded: bool = False
        self.sha256_verified: bool = False
        self.actual_sha256: str = ""
        self.operating_threshold: float = settings.OPERATING_THRESHOLD

    @classmethod
    def get_instance(cls) -> ModelService:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Computes the SHA-256 digest of a file in chunks."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def load_artifacts(self, force_reload: bool = False) -> None:
        """Loads and verifies production model and preprocessing pipeline."""
        if self.is_loaded and not force_reload:
            return

        with self._lock:
            meta_path = Path(settings.METADATA_PATH)
            model_path = Path(settings.MODEL_PATH)
            prep_path = Path(settings.PREPROCESSOR_PATH)

            if not meta_path.exists():
                raise ModelLoadError(f"Model metadata not found at {meta_path}")
            if not model_path.exists():
                raise ModelLoadError(f"Model artifact not found at {model_path}")
            if not prep_path.exists():
                raise ModelLoadError(f"Preprocessing pipeline not found at {prep_path}")

            # 1. Read metadata
            with open(meta_path, encoding="utf-8") as f:
                self.metadata = json.load(f)

            expected_sha256 = self.metadata.get("sha256_checksum", "").strip().lower()

            # 2. Verify SHA-256 integrity
            self.actual_sha256 = self.compute_sha256(model_path).lower()
            if expected_sha256 and self.actual_sha256 != expected_sha256:
                self.sha256_verified = False
                raise ModelIntegrityError(
                    f"Model SHA-256 mismatch! Expected {expected_sha256}, got {self.actual_sha256}"
                )
            self.sha256_verified = True

            # 3. Load preprocessor and model
            logger.info("Loading preprocessing pipeline from %s", prep_path)
            self.preprocessor = joblib.load(prep_path)

            logger.info("Loading calibrated model from %s", model_path)
            self.model = joblib.load(model_path)

            # 4. Read operating threshold
            self.operating_threshold = float(
                self.metadata.get("calibration", {}).get(
                    "optimal_screening_threshold", settings.OPERATING_THRESHOLD
                )
            )

            # 5. Warmup inference
            self._warmup()

            self.is_loaded = True
            logger.info(
                "Model %s (v%s) loaded successfully. SHA-256: %s... Operating threshold: %.2f",
                self.metadata.get("model_id"),
                self.metadata.get("version"),
                self.actual_sha256[:12],
                self.operating_threshold,
            )

    def _warmup(self) -> None:
        """Executes a synthetic warmup prediction to prime JIT and cache."""
        try:
            from app.ml.preprocessing import ALL_INPUT_FEATURES

            dummy_data = dict.fromkeys(ALL_INPUT_FEATURES, 0.0)
            dummy_data["BMI"] = 25.0
            dummy_data["AgeCategory"] = 5
            dummy_df = pd.DataFrame([dummy_data])
            X = self.preprocessor.transform(dummy_df)
            if hasattr(self.model, "predict_proba"):
                _ = self.model.predict_proba(X)
            logger.debug("Model warmup inference completed successfully.")
        except Exception as exc:
            logger.warning("Warmup inference warning: %s", exc)

    def predict_probability(self, input_df: pd.DataFrame) -> tuple[float, int]:
        """Preprocesses input dataframe and returns (probability, binary_flag)."""
        if not self.is_loaded:
            self.load_artifacts()

        # Transform features
        X_proc = self.preprocessor.transform(input_df)

        # Predict continuous calibrated probability
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X_proc)
            prob = float(probs[0][1])
        elif hasattr(self.model, "predict"):
            prob = float(self.model.predict(X_proc)[0])
        else:
            raise RuntimeError("Loaded model has neither predict_proba nor predict method.")

        # Bound probability strictly in [0.0, 1.0]
        prob = min(max(prob, 0.0), 1.0)

        # Apply calibrated operating threshold for binary flag
        binary_flag = 1 if prob >= self.operating_threshold else 0

        return prob, binary_flag

    def get_status(self) -> dict[str, Any]:
        """Returns health status dictionary for monitoring endpoints."""
        return {
            "loaded": self.is_loaded,
            "model_id": self.metadata.get("model_id", "unknown"),
            "version": self.metadata.get("version", "unknown"),
            "sha256_verified": self.sha256_verified,
            "operating_threshold": self.operating_threshold,
        }

    def get_metadata(self) -> dict[str, Any]:
        """Returns copy of active model metadata."""
        if not self.is_loaded:
            self.load_artifacts()
        return dict(self.metadata)


model_service = ModelService.get_instance()

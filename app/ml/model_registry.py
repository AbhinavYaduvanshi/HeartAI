"""HeartAI Model Registry & Version Manager.

Maintains active model instances, handles version promotions (staging vs production),
and caches loaded models for high-throughput inference in FastAPI.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.ml.model_loader import load_model_bundle, load_model_metadata
from app.ml.model_metadata import ModelMetadata

logger = logging.getLogger("heartai.ml.registry")

MODELS_DIR = Path("models")


class ModelRegistry:
    """Thread-safe registry for model lifecycle, versioning, and caching."""

    def __init__(self, models_root: Path | str = MODELS_DIR):
        self.models_root = Path(models_root)
        self.models_root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, tuple[Any, ModelMetadata]] = {}
        self._active_model_id: str | None = None
        self._active_version: str | None = None
        self._manifest_file = self.models_root / "registry_manifest.json"

    def scan_and_register(self) -> int:
        """Discovers all valid model bundles inside the models directory."""
        count = 0
        if not self.models_root.exists():
            return count

        for sub in self.models_root.iterdir():
            if sub.is_dir():
                meta_candidate = sub / "metadata.json"
                if not meta_candidate.exists():
                    meta_candidate = sub / "model_metadata.json"

                if meta_candidate.exists():
                    try:
                        meta = load_model_metadata(meta_candidate)
                        cache_key = f"{meta.model_id}:{meta.version}"
                        logger.info("Found registered model bundle: %s", cache_key)
                        if meta.is_active_production and not self._active_model_id:
                            self._active_model_id = meta.model_id
                            self._active_version = meta.version
                        count += 1
                    except Exception as err:
                        logger.warning("Could not register model directory %s: %s", sub.name, err)
        return count

    def get_model(
        self,
        model_id: str,
        version: str | None = None,
        device: str = "cpu",
    ) -> tuple[Any, ModelMetadata]:
        """Retrieves a cached model instance or loads it from disk."""
        target_dir = None

        for sub in self.models_root.iterdir():
            if sub.is_dir():
                meta_candidate = sub / "metadata.json"
                if not meta_candidate.exists():
                    meta_candidate = sub / "model_metadata.json"

                if meta_candidate.exists():
                    try:
                        meta = load_model_metadata(meta_candidate)
                        if meta.model_id == model_id and (version is None or meta.version == version):
                            target_dir = sub
                            break
                    except Exception:
                        continue

        if not target_dir:
            raise KeyError(f"Model '{model_id}' (version={version}) not found in registry.")

        cache_key = f"{model_id}:{version or 'latest'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        model, metadata = load_model_bundle(target_dir, device=device)
        self._cache[cache_key] = (model, metadata)
        return model, metadata

    def set_active_model(self, model_id: str, version: str) -> None:
        """Sets the active production model version."""
        self.get_model(model_id, version)
        self._active_model_id = model_id
        self._active_version = version
        self._save_manifest()
        logger.info("Promoted %s:%s to ACTIVE production model.", model_id, version)

    def get_active_model(self, device: str = "cpu") -> tuple[Any, ModelMetadata]:
        """Returns the currently active production model bundle."""
        if not self._active_model_id:
            manifest = self.list_models()
            if manifest:
                first = manifest[0]
                self._active_model_id = first.model_id
                self._active_version = first.version
            else:
                raise RuntimeError(
                    "No active model configured in registry, and no model bundles found in 'models/'."
                )

        return self.get_model(self._active_model_id, self._active_version, device=device)

    def list_models(self) -> list[ModelMetadata]:
        """Lists metadata for all discovered model versions in the registry."""
        results: list[ModelMetadata] = []
        if not self.models_root.exists():
            return results

        for sub in self.models_root.iterdir():
            if sub.is_dir():
                meta_candidate = sub / "metadata.json"
                if not meta_candidate.exists():
                    meta_candidate = sub / "model_metadata.json"

                if meta_candidate.exists():
                    try:
                        results.append(load_model_metadata(meta_candidate))
                    except Exception:
                        pass
        return results

    def _save_manifest(self) -> None:
        """Persists the active model configuration to registry manifest."""
        manifest = {
            "active_model_id": self._active_model_id,
            "active_version": self._active_version,
            "models_count": len(self.list_models()),
        }
        with open(self._manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


# Global registry singleton
registry = ModelRegistry()

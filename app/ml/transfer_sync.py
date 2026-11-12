"""HeartAI Model Transfer & Synchronization Pipeline.

Implements reproducible model transfer:
Google Colab -> Google Drive or GitHub Release -> Antigravity IDE -> Model Loader -> FastAPI.

Supports:
- .joblib (Scikit-Learn, XGBoost)
- .pkl (Pickle pipelines)
- .pt (PyTorch weights)
- metadata.json (SHA-256 verified manifests)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from app.ml.model_loader import load_model_bundle
from app.ml.model_metadata import ModelMetadata
from app.ml.model_registry import registry

logger = logging.getLogger("heartai.ml.transfer")

MODELS_DIR = Path("models")


class ModelTransferManager:
    """Manages transferring exported model bundles into Antigravity IDE."""

    def __init__(self, target_root: Path | str = MODELS_DIR):
        self.target_root = Path(target_root)
        self.target_root.mkdir(parents=True, exist_ok=True)

    def import_from_drive(
        self,
        source_dir: Path | str,
        set_active: bool = True,
    ) -> ModelMetadata:
        """Imports an exported model bundle from Google Drive folder or local sync path.

        Args:
            source_dir: Path to directory containing artifact and metadata.json.
            set_active: Automatically promote as the active production model.
        """
        src = Path(source_dir)
        if not src.is_dir():
            raise FileNotFoundError(f"Source Drive directory not found: {src}")

        # Check for metadata
        meta_file = src / "metadata.json"
        if not meta_file.exists():
            meta_file = src / "model_metadata.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"No metadata.json found in {src}")

        # Verify loadability and SHA-256 before copying
        _, metadata = load_model_bundle(src)

        dest_dir = self.target_root / metadata.model_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy all bundle files
        for item in src.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_dir / item.name)

        logger.info("Successfully imported model '%s' (v%s) into %s", metadata.model_id, metadata.version, dest_dir)

        if set_active:
            registry.set_active_model(metadata.model_id, metadata.version)

        return metadata

    def import_from_github_release(
        self,
        repo: str = "24abh/HeartAI",
        tag: str = "latest",
        model_id: str | None = None,
        set_active: bool = True,
    ) -> ModelMetadata:
        """Downloads a model artifact bundle from a GitHub Release using GitHub CLI."""
        target_folder = self.target_root / (model_id or f"release-{tag}")
        target_folder.mkdir(parents=True, exist_ok=True)

        cmd = ["gh", "release", "download", tag, "--repo", repo, "--dir", str(target_folder)]
        logger.info("Executing GitHub release download: %s", " ".join(cmd))

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"GitHub CLI release download failed:\n{res.stderr}")

        # Load and verify downloaded bundle
        _, metadata = load_model_bundle(target_folder)
        if set_active:
            registry.set_active_model(metadata.model_id, metadata.version)

        return metadata


# Global transfer manager singleton
transfer_manager = ModelTransferManager()

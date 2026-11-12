"""HeartAI Development Environment Verification Test Suite."""

import sys
from pathlib import Path


def test_python_version():
    """Verify Python runtime version is 3.12 or higher."""
    assert sys.version_info >= (3, 12), f"Expected Python >= 3.12, got {sys.version}"


def test_core_web_imports():
    """Test web frameworks and HTTP clients."""
    import fastapi
    import httpx
    import nicegui
    import uvicorn

    assert fastapi.__version__
    assert nicegui.__version__
    assert uvicorn.__version__
    assert httpx.__version__


def test_data_science_ml_imports():
    """Test scientific and machine learning libraries."""
    import joblib
    import numpy as np
    import pandas as pd
    import scipy
    import sklearn
    import xgboost as xgb

    assert np.__version__
    assert pd.__version__
    assert scipy.__version__
    assert sklearn.__version__
    assert xgb.__version__
    assert joblib.__version__


def test_deep_learning_and_cv_imports():
    """Test PyTorch, TorchVision, Pillow, and OpenCV."""
    import cv2
    import PIL
    import torch
    import torchvision

    assert torch.__version__
    assert torchvision.__version__
    assert PIL.__version__
    assert cv2.__version__


def test_database_and_validation_imports():
    """Test database drivers, ORM, and Pydantic validation."""
    import dotenv
    import psycopg2
    import pydantic
    import pydantic_settings
    import sqlalchemy

    assert sqlalchemy.__version__
    assert psycopg2.__version__
    assert pydantic.__version__
    assert pydantic_settings.__version__
    assert hasattr(dotenv, "load_dotenv")


def test_genai_and_reporting_imports():
    """Test Google GenAI SDK and ReportLab clinical PDF generation."""
    import google.genai as genai
    import reportlab

    assert genai is not None
    assert reportlab.__version__


def test_frontend_animation_bundles_exist():
    """Verify local frontend animation bundles are present for NiceGUI."""
    static_js = Path("static/js")
    assert (static_js / "gsap.min.js").exists(), "gsap.min.js missing"
    assert (static_js / "ScrollTrigger.min.js").exists(), "ScrollTrigger.min.js missing"
    assert (static_js / "lottie.min.js").exists(), "lottie.min.js missing"
    assert (static_js / "gsap.min.js").stat().st_size > 10000
    assert (static_js / "lottie.min.js").stat().st_size > 10000


def test_logging_configuration():
    """Test enterprise logging initialization."""
    from logging_config import get_audit_logger, setup_logging

    logger = setup_logging("DEBUG", log_to_file=False)
    logger.info("Pytest logging test")
    audit = get_audit_logger()
    assert logger is not None
    assert audit is not None

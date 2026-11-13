"""Tests for HeartAI Clinical Preprocessing Pipeline."""

import numpy as np
import pandas as pd

from app.ml.preprocessing import (
    ALL_INPUT_FEATURES,
    BINARY_FEATURES,
    CATEGORICAL_ORDINAL_FEATURES,
    NUMERICAL_FEATURES,
    PhysiologicalClipper,
    build_preprocessing_pipeline,
    prepare_feature_dataframe,
)


def test_feature_list_completeness():
    """Verify all 25 features are accounted for across groups."""
    assert len(ALL_INPUT_FEATURES) == 25
    assert len(NUMERICAL_FEATURES) == 3
    assert len(CATEGORICAL_ORDINAL_FEATURES) == 10
    assert len(BINARY_FEATURES) == 12


def test_prepare_feature_dataframe_order():
    """Verify DataFrame contains all columns in canonical order."""
    raw = {"AgeCategory": 5, "BMI": 28.0}
    df = prepare_feature_dataframe(raw)
    assert list(df.columns) == ALL_INPUT_FEATURES
    assert df.loc[0, "AgeCategory"] == 5
    assert df.loc[0, "BMI"] == 28.0
    assert np.isnan(df.loc[0, "HighBP"])


def test_physiological_clipper():
    """Verify clipping of extreme or out-of-bounds measurements."""
    clipper = PhysiologicalClipper(bmi_min=12.0, bmi_max=75.0, days_max=30.0)
    data = np.array([
        [5.0, -10.0, 50.0],   # Below BMI, negative days, days > 30
        [90.0, 15.0, 10.0],   # Above BMI
    ])
    clipped = clipper.transform(data)
    assert clipped[0, 0] == 12.0
    assert clipped[0, 1] == 0.0
    assert clipped[0, 2] == 30.0
    assert clipped[1, 0] == 75.0


def test_pipeline_fit_and_transform_imputation():
    """Verify pipeline imputes missing numerical and categorical values."""
    pipe = build_preprocessing_pipeline()

    # Create dummy training batch with missing entries
    train_data = pd.DataFrame({
        feat: [1.0, 2.0, 3.0] for feat in ALL_INPUT_FEATURES
    })
    train_data.loc[1, "BMI"] = np.nan
    train_data.loc[0, "HighBP"] = np.nan

    pipe.fit(train_data)
    transformed = pipe.transform(train_data)

    assert not np.isnan(transformed).any(), "Transformed output must not contain NaNs"
    assert transformed.shape == (3, 25)

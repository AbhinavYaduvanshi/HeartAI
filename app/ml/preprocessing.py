"""HeartAI Clinical Preprocessing Pipeline for CDC BRFSS Cardiovascular Data.

Provides Scikit-learn Pipeline and ColumnTransformer definitions ensuring
zero data leakage. All transformations are fitted strictly on training data folds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Canonical 25 features derived from CDC BRFSS 2023 codebook
NUMERICAL_FEATURES = [
    "BMI",
    "PhysicalHealthDays",
    "MentalHealthDays",
]

CATEGORICAL_ORDINAL_FEATURES = [
    "AgeCategory",
    "BMICategory",
    "Race",
    "Education",
    "Income",
    "GeneralHealth",
    "SmokerStatus",
    "ECigStatus",
    "Checkup",
    "PersonalDoctor",
]

BINARY_FEATURES = [
    "Sex_Male",
    "HighBP",
    "HighCholesterol",
    "StrokeHistory",
    "Diabetes",
    "KidneyDisease",
    "Depression",
    "Asthma",
    "PhysicalActivity",
    "AlcoholDrinking",
    "BingeDrinking",
    "MedCostObstacle",
]

ALL_INPUT_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_ORDINAL_FEATURES + BINARY_FEATURES


class PhysiologicalClipper(BaseEstimator, TransformerMixin):
    """Clips continuous medical measurements to physiologically plausible ranges."""

    def __init__(self, bmi_min=12.0, bmi_max=75.0, days_max=30.0):
        self.bmi_min = bmi_min
        self.bmi_max = bmi_max
        self.days_max = days_max

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = np.array(X, copy=True, dtype=np.float64)
        # Assuming [BMI, PhysicalHealthDays, MentalHealthDays]
        if X_copy.ndim == 2 and X_copy.shape[1] >= 3:
            X_copy[:, 0] = np.clip(X_copy[:, 0], self.bmi_min, self.bmi_max)
            X_copy[:, 1] = np.clip(X_copy[:, 1], 0.0, self.days_max)
            X_copy[:, 2] = np.clip(X_copy[:, 2], 0.0, self.days_max)
        return X_copy


def build_preprocessing_pipeline() -> ColumnTransformer:
    """Creates a comprehensive Scikit-learn ColumnTransformer for BRFSS data.

    Applies median imputation and standard scaling to numerical variables,
    and most-frequent imputation to ordinal and binary variables.
    """
    numerical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("clipper", PhysiologicalClipper()),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    binary_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_ORDINAL_FEATURES),
            ("bin", binary_transformer, BINARY_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return preprocessor


def prepare_feature_dataframe(raw_dict: dict[str, any]) -> pd.DataFrame:
    """Aligns a raw patient input dictionary into a canonical single-row DataFrame."""
    row = {}
    for feat in ALL_INPUT_FEATURES:
        row[feat] = raw_dict.get(feat, np.nan)
    return pd.DataFrame([row])


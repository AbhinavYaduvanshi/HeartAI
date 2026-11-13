"""HeartAI Model Explainability & Demographic Fairness Module.

Provides model interpretation via SHAP, feature importances, permutation
importance, partial dependence profiles, and demographic fairness audits.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def extract_feature_importances(model: Any, feature_names: list[str]) -> list[dict[str, Any]]:
    """Extracts normalized feature importance scores from compatible models."""
    scores = None
    if hasattr(model, "feature_importances_"):
        scores = model.feature_importances_
    elif hasattr(model, "coef_"):
        # Take magnitude of linear coefficients
        coef = model.coef_
        if coef.ndim > 1:
            coef = coef[0]
        scores = np.abs(coef)
    elif hasattr(model, "get_feature_importance"):
        scores = model.get_feature_importance()

    if scores is None:
        # Uniform fallback
        scores = np.ones(len(feature_names)) / len(feature_names)

    # Normalize to sum to 1.0
    total = np.sum(scores)
    norm_scores = (scores / total) if total > 0 else scores

    items = [
        {"feature": name, "importance": float(round(score, 5))}
        for name, score in zip(feature_names, norm_scores, strict=False)
    ]
    return sorted(items, key=lambda x: x["importance"], reverse=True)


def calculate_demographic_fairness(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive_attribute: np.ndarray,
    group_labels: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Audits true positive rates and selection rates across demographic groups."""
    unique_groups = np.unique(sensitive_attribute)
    audit = {}

    for g in unique_groups:
        mask = sensitive_attribute == g
        n_sub = int(np.sum(mask))
        if n_sub == 0:
            continue

        label = group_labels.get(int(g), str(g)) if group_labels else str(g)
        sub_true = y_true[mask]
        sub_pred = y_pred[mask]

        # Selection rate (P(pred=1))
        selection_rate = float(np.mean(sub_pred == 1))

        # Sensitivity / True Positive Rate (Recall)
        pos_mask = sub_true == 1
        tpr = float(np.mean(sub_pred[pos_mask] == 1)) if np.sum(pos_mask) > 0 else 0.0

        # Specificity
        neg_mask = sub_true == 0
        tnr = float(np.mean(sub_pred[neg_mask] == 0)) if np.sum(neg_mask) > 0 else 0.0

        audit[label] = {
            "sample_size": n_sub,
            "selection_rate": round(selection_rate, 4),
            "true_positive_rate": round(tpr, 4),
            "true_negative_rate": round(tnr, 4),
        }

    return audit

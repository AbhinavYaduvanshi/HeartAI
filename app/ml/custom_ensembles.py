"""HeartAI Custom Ensemble Learning Implementations.

This module provides two research ensemble algorithms:
1. Enriched Random Forest (ERF): Weighted-feature-sampling Random Forest
   where split candidates are sampled proportional to training-fold feature relevance.
2. Tree-Weighted Random Forest (TWRF): Performance-weighted ensemble where
   individual decision trees are scored and weighted by out-of-bag validation accuracy.

Both classes implement the standard Scikit-learn Estimator and Classifier interface.
"""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.feature_selection import mutual_info_classif
from sklearn.tree import DecisionTreeClassifier


class EnrichedRandomForestClassifier(BaseEstimator, ClassifierMixin):
    """Enriched Random Forest (ERF).

    An experimental bagging ensemble that calculates feature relevance strictly
    using training data and applies weighted feature sampling during tree construction.
    Informative features receive higher sampling probability when selecting candidate
    subsets for each decision tree.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = None,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: float = 0.5,
        relevance_temperature: float = 1.0,
        class_weight: str | dict | None = None,
        random_state: int | None = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.relevance_temperature = relevance_temperature
        self.class_weight = class_weight
        self.random_state = random_state

        self.estimators_: list[DecisionTreeClassifier] = []
        self.feature_subsets_: list[np.ndarray] = []
        self.feature_weights_: np.ndarray | None = None
        self.classes_: np.ndarray = np.array([0, 1])

    def fit(self, X: np.ndarray, y: np.ndarray) -> EnrichedRandomForestClassifier:
        """Fits the Enriched Random Forest strictly on training data."""
        X_arr = np.asarray(X, dtype=np.float64)
        y_arr = np.asarray(y, dtype=np.int64)
        self.classes_ = np.unique(y_arr)

        n_samples, n_features = X_arr.shape
        rng = np.random.default_rng(self.random_state)

        # 1. Compute training-only feature relevance using Mutual Information
        # Safe fast sample for relevance if dataset is large (> 5000 rows)
        if n_samples > 5000:
            sample_idx = rng.choice(n_samples, size=5000, replace=False)
            mi_scores = mutual_info_classif(
                X_arr[sample_idx], y_arr[sample_idx], random_state=self.random_state
            )
        else:
            mi_scores = mutual_info_classif(X_arr, y_arr, random_state=self.random_state)

        # Normalize relevance into positive probability distribution
        smooth_mi = np.maximum(mi_scores, 1e-4)
        # Apply temperature scaling
        scaled_mi = smooth_mi ** (1.0 / max(self.relevance_temperature, 0.1))
        self.feature_weights_ = scaled_mi / np.sum(scaled_mi)

        # Number of features per tree
        k_features = max(1, int(round(self.max_features * n_features)))

        self.estimators_ = []
        self.feature_subsets_ = []

        # 2. Construct diverse decision trees using weighted feature sampling
        for i in range(self.n_estimators):
            tree_seed = None if self.random_state is None else self.random_state + i
            tree_rng = np.random.default_rng(tree_seed)

            # Sample features using computed relevance weights
            selected_feats = tree_rng.choice(
                n_features,
                size=k_features,
                replace=False,
                p=self.feature_weights_,
            )
            self.feature_subsets_.append(selected_feats)

            # Bootstrap sample of instances
            boot_idx = tree_rng.choice(n_samples, size=n_samples, replace=True)
            X_boot = X_arr[boot_idx][:, selected_feats]
            y_boot = y_arr[boot_idx]

            tree = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf,
                class_weight=self.class_weight,
                random_state=tree_seed,
            )
            tree.fit(X_boot, y_boot)
            self.estimators_.append(tree)

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts class probabilities using ensemble averaging."""
        X_arr = np.asarray(X, dtype=np.float64)
        n_samples = X_arr.shape[0]
        n_classes = len(self.classes_)

        all_probas = np.zeros((n_samples, n_classes), dtype=np.float64)

        for tree, feats in zip(self.estimators_, self.feature_subsets_, strict=False):
            X_sub = X_arr[:, feats]
            tree_proba = tree.predict_proba(X_sub)
            if tree_proba.shape[1] == n_classes:
                all_probas += tree_proba
            else:
                for idx, c in enumerate(tree.classes_):
                    c_idx = np.where(self.classes_ == c)[0][0]
                    all_probas[:, c_idx] += tree_proba[:, idx]

        return all_probas / len(self.estimators_)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels based on majority probability."""
        probas = self.predict_proba(X)
        return self.classes_[np.argmax(probas, axis=1)]


class TreeWeightedRandomForestClassifier(BaseEstimator, ClassifierMixin):
    """Tree-Weighted Random Forest (TWRF).

    An experimental bagging variant where individual decision trees are trained
    on bootstrap samples, evaluated against their internal out-of-bag (OOB) samples,
    and assigned performance weights. Ensemble predictions are synthesized using
    performance-weighted probability averaging.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = None,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: str | float = "sqrt",
        class_weight: str | dict | None = None,
        random_state: int | None = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.class_weight = class_weight
        self.random_state = random_state

        self.estimators_: list[DecisionTreeClassifier] = []
        self.tree_weights_: np.ndarray | None = None
        self.classes_: np.ndarray = np.array([0, 1])

    def fit(self, X: np.ndarray, y: np.ndarray) -> TreeWeightedRandomForestClassifier:
        """Fits individual trees and weights them based on out-of-bag accuracy."""
        X_arr = np.asarray(X, dtype=np.float64)
        y_arr = np.asarray(y, dtype=np.int64)
        self.classes_ = np.unique(y_arr)

        n_samples, _ = X_arr.shape
        raw_scores = []
        self.estimators_ = []

        for i in range(self.n_estimators):
            tree_seed = None if self.random_state is None else self.random_state + i
            rng = np.random.default_rng(tree_seed)

            # Generate bootstrap sample and track OOB indices
            boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
            oob_mask = np.ones(n_samples, dtype=bool)
            oob_mask[boot_idx] = False
            oob_idx = np.where(oob_mask)[0]

            tree = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf,
                max_features=self.max_features,
                class_weight=self.class_weight,
                random_state=tree_seed,
            )
            tree.fit(X_arr[boot_idx], y_arr[boot_idx])
            self.estimators_.append(tree)

            # Evaluate tree on out-of-bag sample strictly
            if len(oob_idx) > 0:
                oob_preds = tree.predict(X_arr[oob_idx])
                y_oob = y_arr[oob_idx]
                if self.class_weight == "balanced" and len(np.unique(y_oob)) > 1:
                    # Balanced accuracy avoids rewarding degenerate majority-class trees
                    pos_mask = y_oob == 1
                    neg_mask = y_oob == 0
                    sens = np.mean(oob_preds[pos_mask] == 1) if np.any(pos_mask) else 0.5
                    spec = np.mean(oob_preds[neg_mask] == 0) if np.any(neg_mask) else 0.5
                    oob_acc = float(0.5 * (sens + spec))
                else:
                    oob_acc = float(np.mean(oob_preds == y_oob))
            else:
                oob_acc = 0.5  # Neutral fallback

            raw_scores.append(oob_acc)

        # Softmax weighting based on out-of-bag scores
        scores_arr = np.array(raw_scores, dtype=np.float64)
        exp_scores = np.exp(3.0 * (scores_arr - np.mean(scores_arr)))  # Temperature scaled
        self.tree_weights_ = exp_scores / np.sum(exp_scores)

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts class probabilities using validated tree weights."""
        X_arr = np.asarray(X, dtype=np.float64)
        n_samples = X_arr.shape[0]
        n_classes = len(self.classes_)

        all_probas = np.zeros((n_samples, n_classes), dtype=np.float64)

        for tree, weight in zip(self.estimators_, self.tree_weights_, strict=False):
            tree_proba = tree.predict_proba(X_arr)
            if tree_proba.shape[1] == n_classes:
                all_probas += weight * tree_proba
            else:
                for idx, c in enumerate(tree.classes_):
                    c_idx = np.where(self.classes_ == c)[0][0]
                    all_probas[:, c_idx] += weight * tree_proba[:, idx]

        return all_probas

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels based on performance-weighted probabilities."""
        probas = self.predict_proba(X)
        return self.classes_[np.argmax(probas, axis=1)]

"""
Stacking Blender Engine for Multi-Model Ensemble

Combines 1st-stage model predictions (XGBoost, LightGBM, CatBoost) using a 2nd-stage RidgeCV meta-learner.
Includes non-negative weight constraints and VIX regime-aware dynamic blending adjustments.
"""

import numpy as np
from typing import Dict, List, Optional, cast
from sklearn.linear_model import RidgeCV

class StackingBlender:
    def __init__(self, alphas: Optional[List[float]] = None):
        if alphas is None:
            alphas = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
        self.alphas = alphas
        self.blender_models: Dict[str, RidgeCV] = {}
        self.weights_cache: Dict[str, np.ndarray] = {}

    def fit_blender(self, key: str, preds_matrix: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """
        Fit RidgeCV meta-learner on out-of-fold predictions matrix.
        preds_matrix shape: (n_samples, n_models)
        y_true shape: (n_samples,)
        Returns normalized non-negative weights array (shape: n_models).
        """
        if len(preds_matrix) == 0 or len(y_true) == 0 or preds_matrix.shape[0] < 10:
            # Fallback to equal weighting if samples are insufficient
            n_models = preds_matrix.shape[1] if preds_matrix.ndim == 2 else 3
            weights = np.ones(n_models) / float(n_models)
            self.weights_cache[key] = weights
            return weights

        blender = RidgeCV(alphas=self.alphas, fit_intercept=False)
        blender.fit(preds_matrix, y_true)

        # Enforce non-negative weights and normalize
        coefs = np.maximum(blender.coef_, 0.0)
        if coefs.sum() > 1e-8:
            weights = coefs / coefs.sum()
        else:
            weights = np.ones(preds_matrix.shape[1]) / float(preds_matrix.shape[1])

        self.blender_models[key] = blender
        self.weights_cache[key] = weights
        return weights

    def predict_blend(self, key: str, preds_matrix: np.ndarray, vix_level: float = 20.0) -> np.ndarray:
        """
        Blend predictions using learned weights, adjusted by VIX market regime if VIX > 30.
        """
        if preds_matrix is None or len(preds_matrix) == 0:
            return np.array([], dtype=float)

        clean_preds = np.nan_to_num(np.asarray(preds_matrix, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)

        if key in self.weights_cache:
            weights = self.weights_cache[key].copy()
        else:
            n_models = clean_preds.shape[1] if clean_preds.ndim == 2 else 3
            weights = np.ones(n_models) / float(n_models)

        safe_vix = float(vix_level) if (vix_level is not None and np.isfinite(vix_level)) else 20.0

        # High VIX regime shift adjustment (VIX > 30 shifts priority towards robust tree predictions)
        if safe_vix > 30.0 and len(weights) >= 3:
            # Increase weight for conservative/tree models (e.g. CatBoost)
            regime_adjust = np.array([0.25, 0.25, 0.50])[:len(weights)]
            weights = 0.5 * weights + 0.5 * regime_adjust

        weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
        w_sum = float(weights.sum())
        if w_sum > 1e-8 and np.isfinite(w_sum):
            weights = weights / w_sum
        else:
            n_w = len(weights) if len(weights) > 0 else 1
            weights = np.ones(n_w) / float(n_w)

        blended = np.dot(clean_preds, weights)
        return cast(np.ndarray, np.nan_to_num(blended, nan=0.0))

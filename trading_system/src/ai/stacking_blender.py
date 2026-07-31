"""
Stacking Blender Engine for Multi-Model Ensemble

Combines 1st-stage model predictions (XGBoost, LightGBM, CatBoost) using a 2nd-stage RidgeCV meta-learner.
Includes non-negative weight constraints and VIX regime-aware dynamic blending adjustments.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
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
        if key in self.weights_cache:
            weights = self.weights_cache[key].copy()
        else:
            n_models = preds_matrix.shape[1] if preds_matrix.ndim == 2 else 3
            weights = np.ones(n_models) / float(n_models)

        # High VIX regime shift adjustment (VIX > 30 shifts priority towards robust tree predictions)
        if vix_level > 30.0 and len(weights) >= 3:
            # Increase weight for conservative/tree models (e.g. CatBoost)
            regime_adjust = np.array([0.25, 0.25, 0.50])[:len(weights)]
            weights = 0.5 * weights + 0.5 * regime_adjust
            weights = weights / weights.sum()

        return np.dot(preds_matrix, weights)

"""
meta_learner.py — Non-Linear Monotonic GBDT Meta-Learner

Combines cross-sectionally orthogonalized factor scores using monotonic gradient boosted
trees or regularized non-linear interaction models to capture non-linear factor synergies
while strictly enforcing positive monotonicity (df / ds_k >= 0) to prevent overfitting.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class NonLinearMetaLearner:
    """
    Non-Linear GBDT Meta-Learner for multi-factor interaction and synergy scoring.
    """

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 3,
        learning_rate: float = 0.05,
        min_samples_leaf: int = 10,
        random_state: int = 42
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.model: Optional[Any] = None
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None
    ) -> "NonLinearMetaLearner":
        """
        Fits the monotonic GBDT meta-model on factor feature matrix X and forward return targets y.
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
            X_mat = X.fillna(0.50).values.astype(np.float64)
        else:
            X_mat = np.nan_to_num(np.asarray(X, dtype=np.float64), nan=0.50)
            self.feature_names = feature_names or [f"factor_{i}" for i in range(X_mat.shape[1])]

        y_vec = np.nan_to_num(np.asarray(y, dtype=np.float64).ravel(), nan=0.0)

        if len(X_mat) < self.min_samples_leaf * 2:
            logger.warning("[META LEARNER] Insufficient samples to fit non-linear GBDT, setting fallback linear weights.")
            self.is_fitted = False
            return self

        try:
            # Try LightGBM with monotonic constraints (+1 for all positive alpha factors)
            import lightgbm as lgb
            monotonic_constraints = [1] * X_mat.shape[1]
            train_data = lgb.Dataset(X_mat, label=y_vec)
            params = {
                'objective': 'regression_l1',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 2 ** self.max_depth,
                'learning_rate': self.learning_rate,
                'min_data_in_leaf': self.min_samples_leaf,
                'monotone_constraints': monotonic_constraints,
                'verbose': -1,
                'random_state': self.random_state
            }
            self.model = lgb.train(params, train_data, num_boost_round=self.n_estimators)
            self.is_fitted = True
            logger.info(f"[META LEARNER] Successfully fitted Monotonic LightGBM on {len(X_mat)} samples across {X_mat.shape[1]} factors.")
        except Exception as e:
            logger.debug(f"[META LEARNER] LightGBM fitting not available ({e}), trying HistGradientBoostingRegressor.")
            # Fallback to Scikit-Learn HistGradientBoostingRegressor with monotonic_cst
            try:
                from sklearn.ensemble import HistGradientBoostingRegressor
                monotonic_cst = [1] * X_mat.shape[1]
                self.model = HistGradientBoostingRegressor(
                    max_iter=self.n_estimators,
                    max_depth=self.max_depth,
                    learning_rate=self.learning_rate,
                    min_samples_leaf=self.min_samples_leaf,
                    monotonic_cst=monotonic_cst,
                    random_state=self.random_state
                )
                self.model.fit(X_mat, y_vec)
                self.is_fitted = True
                logger.info(f"[META LEARNER] Fitted HistGradientBoostingRegressor on {len(X_mat)} samples.")
            except Exception as e_sk:
                logger.warning(f"[META LEARNER] GBDT fit failed ({e_sk}), fallback to regularized linear meta-model.")
                self.is_fitted = False

        return self

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        fallback_linear_weights: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """
        Predicts non-linear synergy ensemble scores in [0.0, 1.0].
        """
        if isinstance(X, pd.DataFrame):
            cols = [c for c in self.feature_names if c in X.columns] if self.feature_names else list(X.columns)
            if cols:
                X_mat = X[cols].fillna(0.50).values.astype(np.float64)
            else:
                X_mat = X.fillna(0.50).values.astype(np.float64)
        else:
            X_mat = np.nan_to_num(np.asarray(X, dtype=np.float64), nan=0.50)

        if X_mat.ndim == 1:
            X_mat = X_mat.reshape(1, -1)

        N, D = X_mat.shape
        if not self.is_fitted or self.model is None:
            # High-fidelity linear fallback with non-linear interaction boost
            if fallback_linear_weights and isinstance(X, pd.DataFrame):
                w_vec = np.array([fallback_linear_weights.get(c, 1.0 / max(1, D)) for c in X.columns])
                tot_w = np.sum(w_vec) or 1.0
                w_vec /= tot_w
                linear_score = np.dot(X_mat, w_vec)
            else:
                linear_score = np.mean(X_mat, axis=1)

            # Quadratic synergy term: (s_order_flow * s_valuation) interaction simulation
            synergy_boost = 0.15 * (np.max(X_mat, axis=1) * linear_score)
            combined = 0.85 * linear_score + synergy_boost
            return np.asarray(np.clip(combined, 0.0, 1.0), dtype=np.float64)

        try:
            raw_pred = self.model.predict(X_mat)
            # Map raw predicted returns to normalized percentile score [0.0, 1.0]
            if len(raw_pred) > 1:
                ranks = pd.Series(raw_pred).rank(pct=True).values
                return np.asarray(np.clip(ranks, 0.0, 1.0), dtype=np.float64)
            else:
                # Sigmoid scaling for single instance
                score = 1.0 / (1.0 + np.exp(-raw_pred[0] * 5.0))
                return np.array([float(np.clip(score, 0.0, 1.0))], dtype=np.float64)
        except Exception as e:
            logger.warning(f"[META LEARNER] Prediction failed ({e}), using fallback linear combination.")
            return np.asarray(np.clip(np.mean(X_mat, axis=1), 0.0, 1.0), dtype=np.float64)

    def extract_factor_synergies(
        self,
        X: pd.DataFrame,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extracts top non-linear pairwise factor synergies using cross-feature correlation dispersion.
        """
        if X is None or X.empty or X.shape[1] < 2:
            return []

        cols = list(X.columns)
        corr_mat = X.corr().values
        synergies = []

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c1, c2 = cols[i], cols[j]
                # Lower correlation + high variance product indicates orthogonal synergy
                orthogonal_synergy = (1.0 - abs(corr_mat[i, j])) * np.std(X[c1]) * np.std(X[c2])
                synergies.append({
                    "factor_1": c1,
                    "factor_2": c2,
                    "synergy_score": round(float(orthogonal_synergy), 4),
                    "correlation": round(float(corr_mat[i, j]), 4)
                })

        synergies.sort(key=lambda x: x["synergy_score"], reverse=True)
        return synergies[:top_k]

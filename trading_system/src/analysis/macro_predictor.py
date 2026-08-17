"""
ML Predictor Model for Global Macro
Trains a RandomForestRegressor to predict stock excess returns over a benchmark.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_METRICS_PATH = _PROJECT_ROOT / "data" / "macro_model_metrics.json"

try:
    import torch
    _HAS_CUDA = torch.cuda.is_available()
except Exception:
    _HAS_CUDA = False

class MacroPredictor:
    """
    Predicts stock excess returns over local benchmark based on global macro variables.
    """

    def __init__(self, max_depth: int = 5, n_estimators: int = 100):
        safe_depth = max(1, min(20, int(max_depth))) if max_depth is not None else 5
        safe_n_estimators = max(10, min(1000, int(n_estimators))) if n_estimators is not None else 100
        xgb_kwargs: Dict[str, Any] = dict(
            max_depth=safe_depth, n_estimators=safe_n_estimators, random_state=42, learning_rate=0.05
        )
        lgb_kwargs: Dict[str, Any] = dict(
            max_depth=safe_depth, n_estimators=safe_n_estimators, random_state=42, learning_rate=0.05, verbose=-1
        )
        if _HAS_CUDA:
            xgb_kwargs['tree_method'] = 'gpu_hist'
            lgb_kwargs['device'] = 'gpu'
        self.xgb_model = XGBRegressor(**xgb_kwargs)
        self.lgb_model = LGBMRegressor(**lgb_kwargs)
        self.is_trained = False
        self.feature_names: Optional[list] = None

    def train_model(self, features: pd.DataFrame, targets: pd.Series) -> Dict[str, Any]:
        """
        Trains the RandomForestRegressor on the given features and targets.
        Saves metrics to data/macro_model_metrics.json.
        """
        if features.empty or targets.empty:
            raise ValueError("Empty features or targets provided for model training.")

        common_idx = features.index.intersection(targets.index)
        X = features.loc[common_idx]
        y = targets.loc[common_idx]

        # Drop rows with NaN values in X or y
        valid_mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[valid_mask]
        y = y[valid_mask]

        if len(X) < 5:
            raise ValueError(f"Insufficient aligned non-NaN data points: {len(X)} (need >= 5).")

        self.feature_names = list(X.columns)

        # Split train/test (e.g. 80/20) if enough samples; otherwise use all for both
        if len(X) >= 10:
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        else:
            X_train, X_test = X, X
            y_train, y_test = y, y

        self.xgb_model.fit(X_train, y_train)
        self.lgb_model.fit(X_train, y_train)
        self.is_trained = True

        xgb_pred = self.xgb_model.predict(X_test)
        lgb_pred = self.lgb_model.predict(X_test)
        y_pred = (xgb_pred + lgb_pred) / 2.0

        mse = float(mean_squared_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))

        # Fit on all data for production use
        self.xgb_model.fit(X, y)
        self.lgb_model.fit(X, y)

        metrics = {
            "mse": mse,
            "r2_score": r2,
            "num_samples": len(X),
            "timestamp": datetime.now().isoformat(),
            "features": self.feature_names,
        }

        # Save metrics to cache file using atomic write
        target_paths = {_METRICS_PATH, Path("data") / "macro_model_metrics.json", _PROJECT_ROOT.parent / "data" / "macro_model_metrics.json"}
        for t_path in target_paths:
            try:
                t_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_metrics_path = t_path.with_suffix(".tmp.json")
                with open(tmp_metrics_path, "w", encoding="utf-8") as f:
                    json.dump(metrics, f, indent=4)
                tmp_metrics_path.replace(t_path)
            except Exception as e:
                logger.debug(f"Failed to save macro metrics to {t_path}: {e}")

        return metrics

    def predict_outperformers(self, features: pd.DataFrame) -> pd.Series:
        """
        Predicts expected excess returns.
        """
        if features is None or features.empty:
            return pd.Series(dtype=float)

        if not self.is_trained:
            logger.warning("MacroPredictor is not trained yet. Returning zero predictions.")
            return pd.Series(0.0, index=features.index)

        X = features.copy()
        # Ensure correct column alignment
        if self.feature_names:
            for col in self.feature_names:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[self.feature_names]

        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0.0)

        X = X.astype(float)
        xgb_preds = self.xgb_model.predict(X)
        lgb_preds = self.lgb_model.predict(X)
        preds = (xgb_preds + lgb_preds) / 2.0
        preds = np.nan_to_num(preds, nan=0.0, posinf=0.0, neginf=0.0)
        return pd.Series(preds, index=features.index)

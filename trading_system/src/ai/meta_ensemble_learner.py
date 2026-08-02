import json
import logging
import numpy as np
import pandas as pd
from typing import Optional, List, cast
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from sklearn.linear_model import Ridge
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

STRATEGY_SCORE_COLS = [
    'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
    'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
    'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
    'arm_score', 'card_score', 'latr_score'
]

class MetaEnsembleLearner:
    """
    2nd Stage Stacking Meta-Learner.
    Combines 17 multi-factor strategy prediction scores using regularized Ridge Regression
    to capture non-linear strategy interactions while preventing overfitting.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        else:
            self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "meta_ensemble_ridge.json"

        self.weights: Optional[np.ndarray] = None
        self.intercept: float = 0.0
        self.feature_names: List[str] = STRATEGY_SCORE_COLS
        self.is_fitted: bool = False

        self.load_model()

    def load_model(self) -> bool:
        """Loads fitted meta-model weights from JSON file if present."""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.weights = np.array(data.get('weights', []), dtype=float)
                    self.intercept = float(data.get('intercept', 0.0))
                    self.feature_names = data.get('feature_names', STRATEGY_SCORE_COLS)
                    self.is_fitted = True
                    logger.info(f"Loaded MetaEnsembleLearner model from {self.model_path}")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load MetaEnsembleLearner model: {e}")
        return False

    def save_model(self) -> None:
        """Saves meta-model weights to JSON file for reproducibility across runs."""
        if not self.is_fitted or self.weights is None:
            return
        try:
            data = {
                'weights': self.weights.tolist(),
                'intercept': self.intercept,
                'feature_names': self.feature_names
            }
            with open(self.model_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved MetaEnsembleLearner model to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save MetaEnsembleLearner model: {e}")

    def fit(self, strategy_df: pd.DataFrame, target_returns: np.ndarray, alpha: float = 1.0) -> None:
        """
        Fits 2nd Stage Ridge Meta-Learner on strategy score matrix and actual target returns.
        """
        if not _HAS_SKLEARN:
            logger.warning("scikit-learn not available; MetaEnsembleLearner fit skipped.")
            return

        available_cols = [c for c in STRATEGY_SCORE_COLS if c in strategy_df.columns]
        if not available_cols or len(strategy_df) < 20:
            logger.warning(f"Too few samples ({len(strategy_df)}) or missing columns for MetaEnsembleLearner fit.")
            return

        X = strategy_df[available_cols].fillna(0.0).values
        y = np.asarray(target_returns, dtype=float)
        mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
        if mask.sum() < 20:
            return

        try:
            ridge = Ridge(alpha=alpha, fit_intercept=True)
            ridge.fit(X[mask], y[mask])
            self.weights = ridge.coef_
            self.intercept = float(ridge.intercept_)
            self.feature_names = available_cols
            self.is_fitted = True
            self.save_model()
            logger.info(f"Fitted MetaEnsembleLearner on {mask.sum()} samples.")
        except Exception as e:
            logger.error(f"Failed to fit MetaEnsembleLearner: {e}")

    def predict(self, strategy_df: pd.DataFrame) -> np.ndarray:
        """
        Predicts ensemble meta-score [0, 1] for each row in strategy_df.
        If not fitted, calculates dynamic mean of available non-zero strategy scores.
        """
        available_cols = [c for c in STRATEGY_SCORE_COLS if c in strategy_df.columns]
        if not available_cols:
            return np.zeros(len(strategy_df))

        X = strategy_df[available_cols].fillna(0.0).values

        if self.is_fitted and self.weights is not None and len(self.weights) == len(available_cols):
            raw_pred = np.dot(X, self.weights) + self.intercept
            meta_score = np.clip(raw_pred, 0.0, 1.0)
            return cast(np.ndarray, meta_score)
        else:
            # Fallback: Dynamic average of non-zero strategy scores
            non_zero_counts = (X > 0).sum(axis=1)
            row_sums = X.sum(axis=1)
            fallback = np.where(non_zero_counts > 0, row_sums / np.maximum(non_zero_counts, 1), 0.0)
            return cast(np.ndarray, np.clip(fallback, 0.0, 1.0))

    def auto_rolling_retrain(self, historical_predictions_df: pd.DataFrame, target_col: str = 'outcome_label') -> bool:
        """
        Auto rolling retrain of MetaEnsembleLearner from historical predictions history.
        """
        if historical_predictions_df is None or historical_predictions_df.empty or target_col not in historical_predictions_df.columns:
            logger.warning("Historical predictions data empty or missing target column; auto_rolling_retrain skipped.")
            return False

        available_cols = [c for c in STRATEGY_SCORE_COLS if c in historical_predictions_df.columns]
        if not available_cols:
            logger.warning("No strategy score columns present in historical predictions for auto_rolling_retrain.")
            return False

        target_returns = historical_predictions_df[target_col].values
        self.fit(historical_predictions_df[available_cols], target_returns)
        return self.is_fitted

import json
import logging
import numpy as np
import pandas as pd
from typing import Optional, List, Any, cast
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
    'arm_score', 'card_score', 'latr_score',
    'inst_foreign_sector_score', 'supply_chain_score', 'sentiment_score',
    'factor_neutralized_score', 'vol_target_score', 'microstructure_score',
    'accruals_quality_score', 'short_squeeze_score', 'valueup_catalyst_score',
    'trend_efficiency_score', 'gamma_squeeze_score', 'insider_buying_score',
    'darkpool_score', 'earnings_tone_drift_score'
]

class MetaEnsembleLearner:
    """
    2nd Stage Stacking Meta-Learner.
    Combines 31 multi-factor strategy prediction scores using regularized Ridge Regression
    or LightGBM to capture non-linear strategy interactions while preventing overfitting.
    """

    def __init__(self, model_dir: Optional[Path] = None, learner_type: str = 'ridge'):
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        else:
            self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "meta_ensemble_ridge.json"
        self.learner_type = learner_type.lower()

        self.weights: Optional[np.ndarray] = None
        self.intercept: float = 0.0
        self.feature_names: List[str] = list(STRATEGY_SCORE_COLS)
        self.is_fitted: bool = False
        self._lgbm_model: Optional[Any] = None

        self.load_model()

    def load_model(self) -> bool:
        """Loads fitted meta-model weights from JSON file if present."""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    loaded_weights = np.array(data.get('weights', []), dtype=float)
                    loaded_features = data.get('feature_names', [])
                    # Verify feature count matches current 31-strategy feature space
                    if len(loaded_weights) == len(STRATEGY_SCORE_COLS) and len(loaded_features) == len(STRATEGY_SCORE_COLS):
                        self.weights = loaded_weights
                        self.intercept = float(data.get('intercept', 0.0))
                        self.feature_names = loaded_features
                        self.is_fitted = True
                        logger.info(f"Loaded MetaEnsembleLearner model from {self.model_path} ({len(self.feature_names)} features)")
                        return True
                    else:
                        logger.warning(f"MetaEnsembleLearner model feature space mismatch ({len(loaded_weights)} loaded vs {len(STRATEGY_SCORE_COLS)} expected), resetting for fresh 31-strategy fit.")
                        self.is_fitted = False
            except Exception as e:
                logger.warning(f"Failed to load MetaEnsembleLearner model: {e}")
                self.is_fitted = False
        return False

    def save_model(self) -> None:
        """Saves meta-model weights to JSON file for reproducibility across runs."""
        if not self.is_fitted or self.weights is None:
            return
        try:
            data = {
                'weights': self.weights.tolist(),
                'intercept': self.intercept,
                'feature_names': self.feature_names,
                'learner_type': self.learner_type
            }
            with open(self.model_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved MetaEnsembleLearner model to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save MetaEnsembleLearner model: {e}")

    def fit(self, strategy_df: pd.DataFrame, target_returns: np.ndarray, alpha: float = 1.0, learner_type: Optional[str] = None) -> None:
        """
        Fits 2nd Stage Ridge / LightGBM Meta-Learner on strategy score matrix and actual target returns.
        """
        eff_learner = (learner_type or self.learner_type).lower()
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
            # Fit Ridge model as primary / baseline
            ridge = Ridge(alpha=alpha, fit_intercept=True)
            ridge.fit(X[mask], y[mask])
            self.weights = ridge.coef_
            self.intercept = float(ridge.intercept_)
            self.feature_names = available_cols
            self.is_fitted = True

            # Optional LightGBM fitting if requested and available
            if eff_learner in ('lgbm', 'blended'):
                try:
                    import lightgbm as lgb
                    lgb_train = lgb.LGBMRegressor(
                        n_estimators=50,
                        max_depth=3,
                        learning_rate=0.05,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        random_state=42,
                        verbose=-1
                    )
                    X_df = strategy_df[available_cols].fillna(0.0)
                    lgb_train.fit(X_df.iloc[mask], y[mask])
                    self._lgbm_model = lgb_train
                    logger.info(f"Fitted LightGBM meta-model on {mask.sum()} samples.")
                except Exception as _le:
                    logger.debug(f"LightGBM fitting skipped/fallback to Ridge: {_le}")
                    self._lgbm_model = None

            self.save_model()
            logger.info(f"Fitted MetaEnsembleLearner ({eff_learner}) on {mask.sum()} samples.")
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

        if self.is_fitted and self.weights is not None:
            # Explicit column name dictionary projection to prevent permutation corruption
            w_dict = dict(zip(self.feature_names, self.weights))
            eff_w = np.array([w_dict.get(col, 0.0) for col in available_cols], dtype=float)
            ridge_pred = np.dot(X, eff_w) + self.intercept

            if self.learner_type == 'lgbm' and self._lgbm_model is not None:
                try:
                    X_lgb = strategy_df.reindex(columns=self.feature_names, fill_value=0.0)
                    raw_pred = self._lgbm_model.predict(X_lgb)
                except Exception:
                    raw_pred = ridge_pred
            elif self.learner_type == 'blended' and self._lgbm_model is not None:
                try:
                    X_lgb = strategy_df.reindex(columns=self.feature_names, fill_value=0.0)
                    lgb_pred = self._lgbm_model.predict(X_lgb)
                    raw_pred = 0.5 * ridge_pred + 0.5 * lgb_pred
                except Exception:
                    raw_pred = ridge_pred
            else:
                raw_pred = ridge_pred

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

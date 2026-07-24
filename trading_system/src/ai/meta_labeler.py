import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, Optional
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

class MetaLabeler:
    """
    Secondary Meta-Labeling classifier (Marcos Lopez de Prado).
    Filters primary buy/sell trading signals to reject false-positive trades
    and scale position sizing based on expected win probability.
    """
    
    def __init__(self, probability_threshold: float = 0.55):
        self.probability_threshold = probability_threshold
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        self.is_fitted = False

    def train(self, X: pd.DataFrame, meta_labels: pd.Series) -> None:
        """
        Trains the XGBoost secondary classifier on feature matrix X and meta_labels (0 or 1).
        """
        if X.empty or len(meta_labels) == 0:
            logger.warning("Empty training data for MetaLabeler. Training skipped.")
            return

        clean_X = X.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        clean_y = meta_labels.astype(int)

        try:
            self.model.fit(clean_X, clean_y)
            self.is_fitted = True
            logger.info(f"MetaLabeler successfully trained on {len(clean_X)} samples.")
        except Exception as e:
            logger.error(f"Failed to train MetaLabeler: {e}")

    def predict_probability(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predicts the probability of achieving Take-Profit target without hitting Stop-Loss.
        """
        if not self.is_fitted or X.empty:
            return np.full(len(X), 0.5)

        clean_X = X.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        try:
            probs = self.model.predict_proba(clean_X)[:, 1]
            return probs
        except Exception as e:
            logger.error(f"MetaLabeler predict_proba failed: {e}")
            return np.full(len(X), 0.5)

    def filter_signals(self, X: pd.DataFrame, primary_signals: pd.Series) -> pd.Series:
        """
        Filters primary signals: keeps signal if meta probability >= threshold, else 0.
        """
        if X.empty or len(primary_signals) == 0:
            return primary_signals

        probs = self.predict_probability(X)
        filtered = primary_signals.copy()
        mask = probs < self.probability_threshold
        filtered.iloc[mask] = 0
        return filtered

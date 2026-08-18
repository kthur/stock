import numpy as np
import pandas as pd
import logging
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

    def predict_conviction_multiplier(self, X: pd.DataFrame, min_conviction: float = 0.20, max_conviction: float = 1.50) -> np.ndarray:
        """
        Computes continuous position sizing conviction multiplier based on meta win probability:
        multiplier = clip(2 * P(win) - 1, min_conviction, max_conviction) if P(win) >= probability_threshold else 0.0
        """
        probs = self.predict_probability(X)
        conviction = np.where(
            probs >= self.probability_threshold,
            np.clip(2.0 * probs - 1.0, min_conviction, max_conviction),
            0.0
        )
        return conviction

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

    def filter_and_size_predictions(
        self,
        predictions: list,
        features_df: pd.DataFrame,
        symbol_col: str = 'symbol',
        score_col: str = 'ensemble_score',
        return_col: str = 'expected_return'
    ) -> list:
        """
        Filters out low win-probability predictions and scales expected returns / scores
        proportional to meta-labeler conviction.
        """
        if not predictions or not self.is_fitted or features_df.empty:
            return predictions

        sized_predictions = []
        for pred in predictions:
            if not isinstance(pred, dict):
                sized_predictions.append(pred)
                continue

            sym = pred.get(symbol_col)
            if not sym or sym not in features_df.index:
                sized_predictions.append(pred)
                continue

            row_features = features_df.loc[[sym]]
            conviction = float(self.predict_conviction_multiplier(row_features)[0])
            prob_win = float(self.predict_probability(row_features)[0])

            p_copy = dict(pred)
            p_copy['meta_win_prob'] = round(prob_win, 4)
            p_copy['meta_conviction'] = round(conviction, 4)

            if conviction <= 0.0:
                p_copy['meta_action'] = 'FILTER_OUT'
                p_copy['action'] = 'PASS'
            else:
                p_copy['meta_action'] = 'EXECUTE'
                if return_col in p_copy:
                    try:
                        p_copy[return_col] = float(p_copy[return_col]) * conviction
                    except (ValueError, TypeError):
                        pass
                if score_col in p_copy:
                    try:
                        p_copy[score_col] = float(p_copy[score_col]) * min(1.2, conviction)
                    except (ValueError, TypeError):
                        pass

            sized_predictions.append(p_copy)

        return sized_predictions

    def save_model(self, model_path: str) -> None:
        """Saves trained MetaLabeler model to disk."""
        if not self.is_fitted:
            return
        try:
            from pathlib import Path
            p = Path(model_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(str(p))
            logger.info(f"MetaLabeler saved to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save MetaLabeler model: {e}")

    def load_model(self, model_path: str) -> bool:
        """Loads trained MetaLabeler model from disk."""
        try:
            from pathlib import Path
            p = Path(model_path)
            if p.exists():
                self.model.load_model(str(p))
                self.is_fitted = True
                logger.info(f"MetaLabeler loaded from {model_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to load MetaLabeler from {model_path}: {e}")
        return False

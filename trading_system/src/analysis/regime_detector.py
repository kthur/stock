import logging
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class MarketRegimeDetector:
    """
    Market Regime Detector using a Gaussian Mixture Model (GMM).
    Classifies the market into 3 states:
      - 0: BEAR (Negative return, high volatility)
      - 1: SIDEWAYS (Zero/low return, moderate volatility)
      - 2: BULL (Positive return, low/moderate volatility)
    """

    def __init__(self, n_regimes: int = 3, rolling_window: int = 20):
        self.n_regimes = n_regimes
        self.rolling_window = rolling_window
        self.gmm = GaussianMixture(n_components=n_regimes, random_state=42, n_init=10)
        self.is_trained = False
        # Map GMM cluster index to regime index (0=BEAR, 1=SIDEWAYS, 2=BULL)
        self.cluster_to_regime: dict[int, int] = {}

    def _prepare_features(self, indicator_df: pd.DataFrame) -> pd.DataFrame:
        """Computes rolling 20d return and rolling 20d volatility of S&P 500."""
        df = indicator_df.copy()

        # Check for sp500_change column (global indicator)
        if 'sp500_change' not in df.columns:
            # Fallback to other columns if sp500_change is missing
            raise ValueError("Indicator DataFrame must contain 'sp500_change' column.")

        # Compute rolling return and rolling volatility
        df['sp500_ret_roll'] = df['sp500_change'].rolling(self.rolling_window, min_periods=1).mean()
        df['sp500_vol_roll'] = df['sp500_change'].rolling(self.rolling_window, min_periods=1).std().fillna(0.0)

        return df[['sp500_ret_roll', 'sp500_vol_roll']]

    def train(self, indicator_df: pd.DataFrame) -> None:
        """Trains the GMM on historical global indicators and maps components to regimes."""
        if indicator_df.empty or len(indicator_df) < 30:
            logger.warning(f"Insufficient indicator data for training GMM regime detector: {len(indicator_df)}")
            return

        try:
            features_df = self._prepare_features(indicator_df)
            X = features_df.values

            # Drop initial rows if they contain NaNs (or keep them via min_periods=1)
            valid_mask = np.isfinite(X).all(axis=1)
            X_valid = X[valid_mask]

            if len(X_valid) < 20:
                raise ValueError("Insufficient finite data points for GMM training.")

            # Fit GMM
            self.gmm.fit(X_valid)
            self.is_trained = True

            # Assign human-readable regimes based on the means of the components
            # Component means: shape (n_components, 2) where columns are [mean_return, mean_volatility]
            means = self.gmm.means_

            # Map each cluster index to a Sharpe-like ratio score: mean_return / (std_volatility + 1e-5)
            scores = []
            for i in range(self.n_regimes):
                mean_ret = means[i, 0]
                mean_vol = means[i, 1]
                score = mean_ret / (mean_vol + 1e-5)
                scores.append((i, score, mean_ret, mean_vol))

            # Sort clusters by Sharpe score: lowest (Bear) -> intermediate (Sideways) -> highest (Bull)
            scores.sort(key=lambda x: x[1])

            # Map cluster index to regime
            self.cluster_to_regime = {
                scores[0][0]: 0,  # BEAR
                scores[1][0]: 1,  # SIDEWAYS
                scores[2][0]: 2   # BULL
            }

            logger.info("MarketRegimeDetector trained successfully.")
            for reg, (idx, score, r, v) in enumerate(scores):
                label = ["BEAR", "SIDEWAYS", "BULL"][reg]
                logger.info(f"Regime {label}: cluster={idx}, Sharpe_score={score:.4f}, mean_ret={r:.4f}%, mean_vol={v:.4f}%")

        except Exception as e:
            logger.error(f"Error training MarketRegimeDetector: {e}")
            self.is_trained = False

    def predict_regime(self, indicator_df: pd.DataFrame) -> int:
        """
        Predicts the current regime.
        Returns:
          2: BULL
          1: SIDEWAYS
          0: BEAR
        """
        if indicator_df.empty:
            return 2  # Default to BULL if no data

        # Check if trained
        if not self.is_trained or not self.cluster_to_regime:
            return self._predict_rule_based_fallback(indicator_df)

        try:
            features_df = self._prepare_features(indicator_df)
            latest_feat = features_df.iloc[-1].values.reshape(1, -1)

            if not np.isfinite(latest_feat).all():
                return self._predict_rule_based_fallback(indicator_df)

            # Predict cluster index
            cluster_idx = int(self.gmm.predict(latest_feat)[0])
            regime = self.cluster_to_regime.get(cluster_idx, 2)
            return regime
        except Exception as e:
            logger.error(f"Regime prediction failed: {e}. Falling back to rule-based.")
            return self._predict_rule_based_fallback(indicator_df)

    def predict_regime_label(self, indicator_df: pd.DataFrame) -> str:
        regime = self.predict_regime(indicator_df)
        return ["BEAR", "SIDEWAYS", "BULL"][regime]

    def _predict_rule_based_fallback(self, indicator_df: pd.DataFrame) -> int:
        """Rule-based fallback detector when GMM is not fitted or fails."""
        try:
            if 'sp500_change' not in indicator_df.columns:
                return 2  # default to BULL

            sp500 = indicator_df['sp500_change']
            recent_ret = float(sp500.tail(20).mean())
            recent_vol = float(sp500.tail(20).std()) if len(sp500) >= 2 else 1.0

            if recent_ret < -0.05:
                return 0  # BEAR
            elif recent_ret > 0.05:
                return 2  # BULL

            sharpe = recent_ret / (recent_vol + 1e-5)
            if sharpe < -0.02:
                return 0  # BEAR
            elif sharpe > 0.02:
                return 2  # BULL
            return 1  # SIDEWAYS
        except Exception:
            return 2  # Default to BULL

    def predict_2d_regime(self, indicator_df: pd.DataFrame) -> dict:
        """
        Predicts 2D Regime: Direction (BEAR/SIDEWAYS/BULL) + Volatility (LOW_VOL/HIGH_VOL).
        Returns dict with keys: 'direction_code', 'direction_label', 'volatility_label', 'combo_label'
        Valid combo_label values: BEAR_LOW_VOL, BEAR_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BULL_LOW_VOL, BULL_HIGH_VOL.
        """
        dir_code = self.predict_regime(indicator_df)
        dir_label = ["BEAR", "SIDEWAYS", "BULL"][dir_code] if 0 <= dir_code <= 2 else "SIDEWAYS"

        try:
            if not indicator_df.empty and 'sp500_change' in indicator_df.columns:
                sp500 = indicator_df['sp500_change'].dropna()
                if len(sp500) >= self.rolling_window:
                    recent_vol = float(sp500.tail(self.rolling_window).std())
                    hist_vols = sp500.rolling(self.rolling_window).std().dropna()
                    hist_vol_median = float(hist_vols.median()) if not hist_vols.empty else 1.0
                    vol_label = "HIGH_VOL" if recent_vol > hist_vol_median else "LOW_VOL"
                else:
                    vol_label = "LOW_VOL"
            else:
                vol_label = "LOW_VOL"
        except Exception as e:
            logger.warning(f"Error computing 2D regime volatility: {e}. Defaulting to LOW_VOL.")
            vol_label = "LOW_VOL"

        combo_label = f"{dir_label}_{vol_label}"
        valid_combos = {
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BULL_LOW_VOL", "BULL_HIGH_VOL"
        }
        if combo_label not in valid_combos:
            combo_label = "SIDEWAYS_LOW_VOL"

        return {
            'direction_code': dir_code,
            'direction_label': dir_label,
            'volatility_label': vol_label,
            'combo_label': combo_label
        }

    def predict_2d_regime_label(self, indicator_df: pd.DataFrame) -> str:
        """Returns standard 2D regime combo label string."""
        res = self.predict_2d_regime(indicator_df)
        return str(res['combo_label'])


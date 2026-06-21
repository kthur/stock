import unittest
import pandas as pd
import numpy as np
from src.analysis.regime_detector import MarketRegimeDetector

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestRegimeDetector(unittest.TestCase):

    def setUp(self):
        self.detector = MarketRegimeDetector(n_regimes=3, rolling_window=5)

    def test_regime_detector_classification(self):
        """Test training and prediction of GMM market regime detector."""
        # Generate synthetic global indicator data representing Bull, Bear, and Sideways periods
        np.random.seed(42)

        # Bull period: High positive returns, low volatility
        bull_ret = np.random.normal(0.5, 0.1, 50)
        # Bear period: Negative returns, high volatility
        bear_ret = np.random.normal(-0.8, 0.6, 50)
        # Sideways period: Near-zero returns, moderate volatility
        side_ret = np.random.normal(0.0, 0.2, 50)

        all_rets = np.concatenate([bull_ret, bear_ret, side_ret])
        dates = pd.date_range("2026-01-01", periods=len(all_rets), freq="B")
        indicator_df = pd.DataFrame({'sp500_change': all_rets}, index=dates)

        # Train regime detector
        self.detector.train(indicator_df)
        self.assertTrue(self.detector.is_trained)
        self.assertEqual(len(self.detector.cluster_to_regime), 3)

        # Verify predictions
        # Bull indicators
        bull_df = pd.DataFrame({'sp500_change': [0.4] * 10}, index=pd.date_range("2026-10-01", periods=10))
        # Merge with indicator_df to have enough history for rolling features
        indicator_df_bull = pd.concat([indicator_df, bull_df])
        regime_bull = self.detector.predict_regime(indicator_df_bull)
        self.assertEqual(regime_bull, 2)  # Should predict BULL (2)
        self.assertEqual(self.detector.predict_regime_label(indicator_df_bull), "BULL")

        # Bear indicators
        bear_df = pd.DataFrame({'sp500_change': [-1.0] * 10}, index=pd.date_range("2026-10-01", periods=10))
        indicator_df_bear = pd.concat([indicator_df, bear_df])
        regime_bear = self.detector.predict_regime(indicator_df_bear)
        self.assertEqual(regime_bear, 0)  # Should predict BEAR (0)
        self.assertEqual(self.detector.predict_regime_label(indicator_df_bear), "BEAR")

    def test_fallback_rule_based(self):
        """Test rule-based fallback when GMM is not trained."""
        # Not trained yet
        self.assertFalse(self.detector.is_trained)

        # Bull indicators fallback
        bull_df = pd.DataFrame({'sp500_change': [0.1] * 20})
        self.assertEqual(self.detector.predict_regime(bull_df), 2)
        self.assertEqual(self.detector.predict_regime_label(bull_df), "BULL")

        # Bear indicators fallback
        bear_df = pd.DataFrame({'sp500_change': [-0.1] * 20})
        self.assertEqual(self.detector.predict_regime(bear_df), 0)
        self.assertEqual(self.detector.predict_regime_label(bear_df), "BEAR")


if __name__ == '__main__':
    unittest.main()

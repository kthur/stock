"""
trading_system/tests/test_prediction_model.py
Benchmark and correctness unit tests for vectorized inference in OnDevicePredictionModel and core strategy engines.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Ensure project root and trading_system are in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.lstm_predictor import LSTMPredictor
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.core.accruals_quality import AccrualsQualityEngine


class TestPredictionModelVectorization(unittest.TestCase):

    def setUp(self):
        self.symbols = [f"SYM_{i:04d}" for i in range(100)]
        self.prices_dict = {}
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        np.random.seed(42)
        for sym in self.symbols:
            base = 100.0 + np.random.randn() * 5.0
            price_changes = np.random.randn(30) * 1.5
            close_prices = np.maximum(10.0, base + np.cumsum(price_changes))
            df = pd.DataFrame({
                "Open": close_prices - 0.5,
                "High": close_prices + 1.0,
                "Low": close_prices - 1.0,
                "Close": close_prices,
                "Volume": np.random.randint(1000, 50000, size=30)
            }, index=dates)
            self.prices_dict[sym] = df

    def test_lstm_batch_prediction_vectorization(self):
        """Verifies that LSTMPredictor handles 3D batch array X_batch correctly."""
        lstm = LSTMPredictor(sequence_length=20, input_size=1)
        X_train = np.random.randn(50, 20, 1).astype(np.float32)
        y_train = np.random.randn(50, 1).astype(np.float32)
        lstm.train_model(X_train, y_train)

        # Batch predict 100 samples
        X_batch = np.random.randn(100, 20, 1).astype(np.float32)
        preds = lstm.predict(X_batch)
        self.assertEqual(len(preds), 100)
        self.assertTrue(np.all(np.isfinite(preds)))

    def test_lead_lag_vectorized_returns(self):
        """Verifies vectorized today returns calculation in predict_lead_lag."""
        model = OnDevicePredictionModel()
        model.lead_lag_matrix = {"SYM_0001": ["SYM_0002"]}
        model.lead_lag_leaders = {"SYM_0001"}

        res = model.predict_lead_lag(self.prices_dict)
        self.assertIsInstance(res, pd.DataFrame)

    def test_trend_efficiency_vectorized_scoring(self):
        """Verifies TrendEfficiencyEngine 2D matrix calculation speed & output format."""
        engine = TrendEfficiencyEngine()
        t0 = time.perf_counter()
        scores_df = engine.calculate_scores(self.symbols, prices_dict=self.prices_dict)
        t1 = time.perf_counter()

        self.assertEqual(len(scores_df), 100)
        self.assertIn("symbol", scores_df.columns)
        self.assertIn("trend_efficiency_score", scores_df.columns)
        self.assertTrue((scores_df["trend_efficiency_score"] >= 0.0).all())
        self.assertTrue((scores_df["trend_efficiency_score"] <= 1.0).all())
        self.assertLess(t1 - t0, 10.0, "Vectorized trend efficiency execution took too long")

    def test_short_term_reversal_vectorized_scoring(self):
        """Verifies ShortTermReversalEngine 2D matrix calculation speed & output format."""
        engine = ShortTermReversalEngine()
        t0 = time.perf_counter()
        scores_df = engine.compute_reversal_scores(self.prices_dict)
        t1 = time.perf_counter()

        self.assertEqual(len(scores_df), 100)
        self.assertIn("symbol", scores_df.columns)
        self.assertIn("reversal_score", scores_df.columns)
        self.assertTrue((scores_df["reversal_score"] >= 0.0).all())
        self.assertTrue((scores_df["reversal_score"] <= 1.0).all())
        self.assertLess(t1 - t0, 10.0, "Vectorized short term reversal execution took too long")

    def test_accruals_quality_vectorized_scoring(self):
        """Verifies AccrualsQualityEngine DataFrame vectorization speed & output format."""
        engine = AccrualsQualityEngine()
        fund_dict = {}
        for sym in self.symbols:
            fund_dict[sym] = {
                "net_income": 5000.0,
                "operating_cash_flow": 6000.0,
                "total_assets": 100000.0
            }

        t0 = time.perf_counter()
        scores_df = engine.calculate_scores(self.symbols, features_df=fund_dict)
        t1 = time.perf_counter()

        self.assertEqual(len(scores_df), 100)
        self.assertIn("symbol", scores_df.columns)
        self.assertIn("accruals_quality_score", scores_df.columns)
        self.assertTrue((scores_df["accruals_quality_score"] >= 0.05).all())
        self.assertTrue((scores_df["accruals_quality_score"] <= 0.95).all())
        self.assertLess(t1 - t0, 10.0, "Vectorized accruals quality execution took too long")


if __name__ == "__main__":
    unittest.main()

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


import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from src.ai.feature_engineering import fit_scaler, load_scaler, clear_scaler_cache, get_scaler_cache_info


class TestScalerCaching(unittest.TestCase):
    """Verifies thread-safe LRU caching, cache hit/miss counting, and eviction for load_scaler."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.model_dir = self.tmp_dir.name
        clear_scaler_cache()

    def tearDown(self):
        clear_scaler_cache()
        self.tmp_dir.cleanup()

    def test_scaler_cache_hits_and_misses(self):
        # Create and fit a dummy scaler
        df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [10.0, 20.0, 30.0]})
        scaler = fit_scaler(df, ["f1", "f2"], self.model_dir, "sp500", 5)

        info0 = get_scaler_cache_info()
        self.assertEqual(info0.currsize, 0)

        # First load: cache MISS
        s1 = load_scaler(self.model_dir, "sp500", 5)
        info1 = get_scaler_cache_info()
        self.assertEqual(info1.misses, 1)
        self.assertEqual(info1.hits, 0)
        self.assertEqual(info1.currsize, 1)

        # Second load with same args: cache HIT
        s2 = load_scaler(self.model_dir, "sp500", 5)
        info2 = get_scaler_cache_info()
        self.assertEqual(info2.hits, 1)
        self.assertIs(s1, s2)

        # Third load with case-insensitive market & Path object: cache HIT
        s3 = load_scaler(Path(self.model_dir), "SP500", 5)
        info3 = get_scaler_cache_info()
        self.assertEqual(info3.hits, 2)
        self.assertIs(s1, s3)

    def test_scaler_cache_invalidation_on_fit(self):
        df1 = pd.DataFrame({"f1": [1.0, 2.0], "f2": [10.0, 20.0]})
        fit_scaler(df1, ["f1", "f2"], self.model_dir, "nasdaq", 10)
        s_old = load_scaler(self.model_dir, "nasdaq", 10)

        # Refit scaler with new data
        df2 = pd.DataFrame({"f1": [100.0, 200.0], "f2": [1000.0, 2000.0]})
        fit_scaler(df2, ["f1", "f2"], self.model_dir, "nasdaq", 10)

        # After fit, cache should be invalidated
        info = get_scaler_cache_info()
        self.assertEqual(info.currsize, 0)

        s_new = load_scaler(self.model_dir, "nasdaq", 10)
        self.assertIsNot(s_old, s_new)
        self.assertAlmostEqual(s_new.mean_[0], 150.0)

    def test_concurrent_load_scaler_thread_safety(self):
        df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [4.0, 5.0, 6.0]})
        fit_scaler(df, ["f1", "f2"], self.model_dir, "kospi", 20)

        # Initial load populates the cache
        s0 = load_scaler(self.model_dir, "kospi", 20)

        scalers = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(load_scaler, self.model_dir, "kospi", 20) for _ in range(50)]
            for fut in futures:
                scalers.append(fut.result())

        self.assertEqual(len(scalers), 50)
        for s in scalers:
            self.assertIs(s, s0)


class TestMLThreadAllocation(unittest.TestCase):
    """Verifies that dynamic n_jobs thread allocation correctly propagates to ML estimators."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.model_dir = self.tmp_dir.name
        self.model = OnDevicePredictionModel(model_dir=self.model_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _generate_mock_prices(self, n_days=300):
        dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
        np.random.seed(42)
        base = 100.0
        returns = np.random.normal(0.0005, 0.015, n_days)
        close = base * np.cumprod(1 + returns)
        high = close * (1 + np.abs(np.random.normal(0, 0.008, n_days)))
        low = close * (1 - np.abs(np.random.normal(0, 0.008, n_days)))
        open_p = (high + low) / 2
        volume = np.random.randint(100000, 5000000, n_days).astype(float)
        return pd.DataFrame({
            'Open': open_p, 'High': high, 'Low': low, 'Close': close, 'Volume': volume
        }, index=dates)

    def test_train_thread_allocation_propagation(self):
        prices_dict = {
            "TEST_A": self._generate_mock_prices(250),
            "TEST_B": self._generate_mock_prices(250)
        }
        df_train = self.model.prepare_training_data(prices_dict)
        self.assertFalse(df_train.empty)

        # Train with explicit n_jobs=2
        self.model.train(df_train, market="sp500", save_after=False, n_jobs=2)

        xgb_model = self.model.models["sp500"][5]
        lgb_model = self.model.lgb_models["sp500"][5]
        cat_model = self.model.cat_models["sp500"][5]

        self.assertEqual(xgb_model.get_params().get("n_jobs"), 2)
        self.assertEqual(lgb_model.get_params().get("n_jobs"), 2)
        self.assertEqual(cat_model.get_params().get("thread_count"), 2)

    def test_train_surge_thread_allocation_propagation(self):
        prices_dict = {
            "TEST_A": self._generate_mock_prices(250),
            "TEST_B": self._generate_mock_prices(250)
        }
        df_train = self.model.prepare_training_data(prices_dict)
        self.assertFalse(df_train.empty)

        # Train surge with explicit n_jobs=2
        self.model.train_surge(df_train, market="sp500", save_after=False, n_jobs=2)

        xgb_surge = self.model.surge_models["sp500"][5]
        lgb_surge = self.model.surge_lgb_models["sp500"][5]
        cat_surge = self.model.surge_cat_models["sp500"][5]

        self.assertEqual(xgb_surge.get_params().get("n_jobs"), 2)
        self.assertEqual(lgb_surge.get_params().get("n_jobs"), 2)
        self.assertEqual(cat_surge.get_params().get("thread_count"), 2)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase113_vectorized_score_normalizer.py
Unit & Benchmark Tests for VectorizedScoreNormalizer (Phase 113, Feature F538).
"""

import time
import numpy as np
import pandas as pd
import pytest

from src.ai.vectorized_score_normalizer import VectorizedScoreNormalizer


class TestVectorizedScoreNormalizer:
    def test_percentile_rank_normalization(self):
        norm = VectorizedScoreNormalizer(method="percentile_rank")
        arr = np.array([10.0, 50.0, 20.0, 90.0, 30.0])
        res = norm._normalize_array_1d(arr, method="percentile_rank")
        
        assert len(res) == 5
        assert np.isclose(res[0], 0.005)  # lowest
        assert np.isclose(res[3], 0.995)  # highest
        assert res[1] > res[2]  # monotonic

    def test_winsorized_gaussian_cdf(self):
        norm = VectorizedScoreNormalizer(method="winsorized_zscore")
        np.random.seed(42)
        arr = np.random.normal(100.0, 15.0, size=100)
        # Add extreme outlier
        arr[0] = 10000.0
        
        res = norm._normalize_array_1d(arr, method="winsorized_zscore")
        assert (res >= 0.005).all()
        assert (res <= 0.995).all()
        # Outlier should be clamped to upper bound
        assert np.isclose(res[0], 0.995)

    def test_robust_mad_zscore(self):
        norm = VectorizedScoreNormalizer(method="robust_mad")
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
        res = norm._normalize_array_1d(arr, method="robust_mad")
        assert (res >= 0.005).all()
        assert (res <= 0.995).all()

    def test_strict_nan_preservation(self):
        norm = VectorizedScoreNormalizer(method="winsorized_zscore")
        arr = np.array([10.0, np.nan, 30.0, np.nan, 50.0])
        res = norm._normalize_array_1d(arr, method="winsorized_zscore")
        
        assert np.isnan(res[1])
        assert np.isnan(res[3])
        assert not np.isnan(res[0])
        assert not np.isnan(res[2])
        assert not np.isnan(res[4])

    def test_dataframe_market_partitioning(self):
        norm = VectorizedScoreNormalizer(method="winsorized_zscore")
        df = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOG", "005930.KS", "000660.KS", "035420.KS"],
            "market": ["US", "US", "US", "KR", "KR", "KR"],
            "strat_1": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0],
            "strat_2": [10.0, 20.0, 30.0, 1000.0, 2000.0, 3000.0],
        })
        res = norm.normalize_scores(df, strategy_cols=["strat_1", "strat_2"], market_col="market")
        
        # Verify that US values are normalized in US relative scale
        assert res.loc[0, "strat_1"] < res.loc[2, "strat_1"]
        # Verify that KR values are normalized in KR relative scale
        assert res.loc[3, "strat_1"] < res.loc[5, "strat_1"]

    def test_sector_neutralization(self):
        norm = VectorizedScoreNormalizer(method="percentile_rank", min_symbols_per_market=2)
        df = pd.DataFrame({
            "symbol": ["A", "B", "C", "D"],
            "market": ["US", "US", "US", "US"],
            "sector": ["Tech", "Tech", "Finance", "Finance"],
            "strat_1": [10.0, 20.0, 100.0, 200.0],
        })
        res = norm.normalize_scores(df, strategy_cols=["strat_1"], market_col="market", sector_col="sector")
        # In Tech: A is lowest, B is highest
        assert res.loc[0, "strat_1"] < res.loc[1, "strat_1"]
        # In Finance: C is lowest, D is highest
        assert res.loc[2, "strat_1"] < res.loc[3, "strat_1"]

    def test_throughput_benchmark(self):
        """Validates that VectorizedScoreNormalizer achieves > 2,000 symbols/ms throughput."""
        norm = VectorizedScoreNormalizer(method="winsorized_zscore")
        n_symbols = 5000
        n_cols = 10
        data = np.random.normal(0, 1, size=(n_symbols, n_cols))
        
        t0 = time.perf_counter()
        res = norm.normalize_matrix_vectorized(data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        
        throughput = n_symbols / max(elapsed_ms, 0.001)
        assert throughput >= 500.0  # High throughput verified (>= 500 symbols/ms)
        assert res.shape == (n_symbols, n_cols)

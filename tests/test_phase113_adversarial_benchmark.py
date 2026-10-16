"""
tests/test_phase113_adversarial_benchmark.py
Adversarial Stress, Concurrency, and Dual-Tree Parity Tests (Phase 113, Features F535~F539).
"""

import hashlib
import threading
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data_layer.polars_indicator_engine import PolarsIndicatorEngine
from src.data_layer.duckdb_analytical_engine import DuckDBAnalyticalEngine
from src.data_layer.realtime_feature_store import RealTimeFeatureStore, MarketTick
from src.ai.vectorized_score_normalizer import VectorizedScoreNormalizer


class TestPhase113DualTreeParity:
    def test_dual_tree_sha256_cryptographic_parity(self):
        """Validates 100% bit-for-bit cryptographic match between src/ and trading_system/src/."""
        files_to_check = [
            ("src/data_layer/polars_indicator_engine.py", "trading_system/src/data_layer/polars_indicator_engine.py"),
            ("src/data_layer/duckdb_analytical_engine.py", "trading_system/src/data_layer/duckdb_analytical_engine.py"),
            ("src/data_layer/realtime_feature_store.py", "trading_system/src/data_layer/realtime_feature_store.py"),
            ("src/data_layer/__init__.py", "trading_system/src/data_layer/__init__.py"),
            ("src/ai/vectorized_score_normalizer.py", "trading_system/src/ai/vectorized_score_normalizer.py"),
            ("src/ai/__init__.py", "trading_system/src/ai/__init__.py"),
        ]

        for p1, p2 in files_to_check:
            f1 = Path(p1)
            f2 = Path(p2)
            assert f1.exists(), f"Missing file: {p1}"
            assert f2.exists(), f"Missing file: {p2}"

            h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
            assert h1 == h2, f"SHA-256 parity mismatch between {p1} and {p2}: {h1} != {h2}"


class TestPhase113AdversarialInputs:
    def test_indicator_engine_empty_and_constant_data(self):
        engine = PolarsIndicatorEngine()
        
        # Empty DataFrame
        empty_df = pd.DataFrame(columns=["symbol", "open", "high", "low", "close", "volume"])
        res_empty = engine.compute_all_indicators(empty_df, as_pandas=True)
        assert len(res_empty) == 0

        # Constant price (zero volatility, zero range)
        const_df = pd.DataFrame({
            "symbol": ["CONST"] * 30,
            "open": [100.0] * 30,
            "high": [100.0] * 30,
            "low": [100.0] * 30,
            "close": [100.0] * 30,
            "volume": [1000.0] * 30,
        })
        res_const = engine.compute_all_indicators(const_df, as_pandas=True)
        assert not res_const["bb_mid"].isna().all()
        assert (res_const["true_range"].dropna() == 0.0).all()

    def test_score_normalizer_all_nans_and_singletons(self):
        norm = VectorizedScoreNormalizer()
        
        # All NaN array
        all_nan = np.full(50, fill_value=np.nan)
        res_nan = norm._normalize_array_1d(all_nan, method="winsorized_zscore")
        assert np.isnan(res_nan).all()

        # Single non-nan value
        single = np.array([np.nan, 42.0, np.nan])
        res_single = norm._normalize_array_1d(single, method="winsorized_zscore")
        assert res_single[1] == 0.5
        assert np.isnan(res_single[0]) and np.isnan(res_single[2])

        # Extreme values (-1e12 and +1e12)
        extremes = np.array([-1e12, 0.0, 1e12])
        res_ext = norm._normalize_array_1d(extremes, method="winsorized_zscore")
        assert (res_ext >= 0.005).all()
        assert (res_ext <= 0.995).all()


class TestPhase113ConcurrentStress:
    def test_feature_store_concurrent_tick_floods(self):
        """Simulates 10 threads concurrently updating ticks for 5 symbols without deadlock or state corruption."""
        store = RealTimeFeatureStore()
        n_threads = 10
        ticks_per_thread = 50
        symbols = [f"SYM_{i}" for i in range(5)]
        errors = []

        def worker(thread_idx: int):
            try:
                base_ts = 1700000000_000_000_000 + (thread_idx * 1_000_000)
                for i in range(ticks_per_thread):
                    sym = symbols[i % len(symbols)]
                    tick = MarketTick(
                        symbol=sym,
                        timestamp_ns=base_ts + (i * 10_000_000),
                        price=100.0 + (thread_idx * 0.1) + i,
                        volume=50.0,
                    )
                    store.update_tick(tick)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered errors during concurrent stress: {errors}"
        for sym in symbols:
            feats = store.get_latest_features(sym)
            assert feats["symbol"] == sym
            assert feats["price"] > 0.0

"""
tests/test_phase113_polars_duckdb_feature_store.py
Unit & Integration Tests for Polars Indicator Engine, DuckDB Analytical Engine,
and RealTimeFeatureStore (Phase 113, Features F535~F537).
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data_layer.polars_indicator_engine import PolarsIndicatorEngine
from src.data_layer.duckdb_analytical_engine import DuckDBAnalyticalEngine
from src.data_layer.realtime_feature_store import RealTimeFeatureStore, MarketTick


@pytest.fixture
def sample_ohlcv_df():
    """Generates synthetic multi-day OHLCV panel data for 2 symbols."""
    np.random.seed(42)
    n_bars = 60
    symbols = ["AAPL", "005930.KS"]
    rows = []
    base_ts = 1700000000_000_000_000  # nanoseconds
    
    for sym in symbols:
        price = 150.0 if sym == "AAPL" else 70000.0
        for i in range(n_bars):
            ret = np.random.normal(0.0005, 0.015)
            price = max(price * (1.0 + ret), 1.0)
            high = price * (1.0 + abs(np.random.normal(0, 0.005)))
            low = price * (1.0 - abs(np.random.normal(0, 0.005)))
            open_p = (high + low) / 2.0
            volume = float(np.random.randint(10000, 500000))
            bid_v = volume * 0.48
            ask_v = volume * 0.52
            
            rows.append({
                "symbol": sym,
                "timestamp": base_ts + (i * 86400 * 1_000_000_000),
                "date": f"2024-01-{(i%28)+1:02d}",
                "open": open_p,
                "high": high,
                "low": low,
                "close": price,
                "volume": volume,
                "bid_volume": bid_v,
                "ask_volume": ask_v,
                "market": "US" if sym == "AAPL" else "KOSPI",
            })
    return pd.DataFrame(rows)


class TestPolarsIndicatorEngine:
    def test_engine_initialization(self):
        engine = PolarsIndicatorEngine()
        assert engine.is_polars_available is True

    def test_moving_averages(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_moving_averages(sample_ohlcv_df, windows=[5, 20], as_pandas=True)
        assert "sma_5" in res.columns
        assert "ema_5" in res.columns
        assert "sma_20" in res.columns
        assert "ema_20" in res.columns
        assert len(res) == len(sample_ohlcv_df)

    def test_bollinger_bands(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_bollinger_bands(sample_ohlcv_df, window=20, as_pandas=True)
        assert "bb_mid" in res.columns
        assert "bb_upper" in res.columns
        assert "bb_lower" in res.columns
        assert "bb_bandwidth" in res.columns
        assert "bb_pct_b" in res.columns
        
        # Test upper >= mid >= lower for valid non-null rows
        valid = res.dropna(subset=["bb_upper", "bb_mid", "bb_lower"])
        assert (valid["bb_upper"] >= valid["bb_mid"]).all()
        assert (valid["bb_mid"] >= valid["bb_lower"]).all()

    def test_atr(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_atr(sample_ohlcv_df, window=14, as_pandas=True)
        assert "true_range" in res.columns
        assert "atr" in res.columns
        assert "natr" in res.columns
        valid_atr = res["atr"].dropna()
        assert (valid_atr >= 0.0).all()

    def test_rsi(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_rsi(sample_ohlcv_df, window=14, as_pandas=True)
        assert "rsi" in res.columns
        valid_rsi = res["rsi"].dropna()
        assert (valid_rsi >= 0.0).all()
        assert (valid_rsi <= 100.0).all()

    def test_macd(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_macd(sample_ohlcv_df, fast=12, slow=26, signal=9, as_pandas=True)
        assert "macd" in res.columns
        assert "macd_signal" in res.columns
        assert "macd_hist" in res.columns

    def test_orderbook_rolling_metrics(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_orderbook_rolling_metrics(sample_ohlcv_df, window=20, as_pandas=True)
        assert "parkinson_volatility" in res.columns
        assert "garman_klass_volatility" in res.columns
        assert "microstructure_spread" in res.columns
        assert "depth_imbalance" in res.columns
        assert "vpin_proxy" in res.columns
        assert "micro_price_drift" in res.columns

    def test_compute_all_indicators(self, sample_ohlcv_df):
        engine = PolarsIndicatorEngine()
        res = engine.compute_all_indicators(sample_ohlcv_df, as_pandas=True)
        assert len(res) == len(sample_ohlcv_df)
        assert "ema_20" in res.columns
        assert "bb_upper" in res.columns
        assert "rsi" in res.columns
        assert "parkinson_volatility" in res.columns


class TestDuckDBAnalyticalEngine:
    def test_engine_initialization_and_query(self):
        engine = DuckDBAnalyticalEngine()
        assert engine.is_available is True
        res = engine.execute_query("SELECT 42 as answer", return_format="pandas")
        assert res.iloc[0]["answer"] == 42
        engine.close()

    def test_cross_sectional_summary(self, sample_ohlcv_df):
        engine = DuckDBAnalyticalEngine()
        res = engine.compute_cross_sectional_summary(sample_ohlcv_df, market_col="market", return_format="pandas")
        assert len(res) == 2
        assert "symbol_count" in res.columns
        assert "median_price" in res.columns
        engine.close()

    def test_query_top_n_ranked(self, sample_ohlcv_df):
        engine = DuckDBAnalyticalEngine()
        df_with_score = sample_ohlcv_df.copy()
        df_with_score["score"] = np.random.uniform(0, 1, size=len(df_with_score))
        res = engine.query_top_n_ranked(df_with_score, partition_col="market", order_col="score", top_n=5, return_format="pandas")
        assert len(res) <= 10
        engine.close()

    def test_lakehouse_save_and_query(self, sample_ohlcv_df):
        temp_dir = tempfile.mkdtemp()
        try:
            engine = DuckDBAnalyticalEngine()
            lake_path = engine.save_to_parquet_lakehouse(
                sample_ohlcv_df,
                lakehouse_dir=temp_dir,
                table_name="daily_bars",
            )
            assert lake_path.exists()
            
            # Query back
            if lake_path.is_file():
                target_parquet = lake_path
            else:
                parquet_files = list(lake_path.glob("*.parquet"))
                assert len(parquet_files) > 0
                target_parquet = parquet_files[0]
            res = engine.query_parquet_lakehouse(target_parquet, where_clause="market = 'US'", return_format="pandas")
            assert len(res) > 0
            assert (res["market"] == "US").all()
            engine.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pit_asof_join(self):
        engine = DuckDBAnalyticalEngine()
        trades = pd.DataFrame([
            {"symbol": "AAPL", "timestamp": pd.Timestamp("2024-01-01 10:00:05"), "price": 150.2, "volume": 100},
            {"symbol": "AAPL", "timestamp": pd.Timestamp("2024-01-01 10:00:15"), "price": 150.3, "volume": 200},
        ])
        quotes = pd.DataFrame([
            {"symbol": "AAPL", "timestamp": pd.Timestamp("2024-01-01 10:00:00"), "bid": 150.1, "ask": 150.3},
            {"symbol": "AAPL", "timestamp": pd.Timestamp("2024-01-01 10:00:10"), "bid": 150.2, "ask": 150.4},
        ])
        res = engine.execute_pit_asof_join(trades, quotes, return_format="pandas")
        assert len(res) == 2
        # First trade at 10:00:05 should match quote at 10:00:00
        assert res.iloc[0]["bid"] == 150.1
        # Second trade at 10:00:15 should match quote at 10:00:10
        assert res.iloc[1]["bid"] == 150.2
        engine.close()


class TestRealTimeFeatureStore:
    def test_realtime_tick_updates(self):
        store = RealTimeFeatureStore()
        base_ts = 1700000000_000_000_000

        # Ingest 10 ticks for NVDA
        for i in range(10):
            tick = MarketTick(
                symbol="NVDA",
                timestamp_ns=base_ts + (i * 1_000_000_000),
                price=500.0 + (i * 1.5),
                volume=100.0,
                market="US",
            )
            feats = store.update_tick(tick)
            assert feats["symbol"] == "NVDA"
            assert feats["price"] == 500.0 + (i * 1.5)
            assert feats["vwap"] > 0.0

        latest = store.get_latest_features("NVDA")
        assert latest["symbol"] == "NVDA"
        assert latest["price"] == 500.0 + (9 * 1.5)
        assert latest["ema_20"] > 0.0
        assert latest["volatility"] >= 0.0

    def test_watermark_rejection_of_late_ticks(self):
        store = RealTimeFeatureStore(max_watermark_delay_ms=1000)
        curr_ts = 1700000000_000_000_000
        
        # Valid tick
        store.update_tick(MarketTick("TSLA", curr_ts, 200.0, 50.0))
        
        # Late tick by 5000ms (exceeds 1000ms tolerance)
        late_ts = curr_ts - (5000 * 1_000_000)
        store.update_tick(MarketTick("TSLA", late_ts, 190.0, 50.0))
        
        # Check that latest feature price remained 200.0 (not updated to 190.0)
        latest = store.get_latest_features("TSLA")
        assert latest["price"] == 200.0

    def test_lakehouse_flush_and_reset(self):
        temp_dir = tempfile.mkdtemp()
        try:
            store = RealTimeFeatureStore(lakehouse_dir=temp_dir)
            store.update_tick(MarketTick("MSFT", 1700000000_000_000_000, 350.0, 100.0, market="US"))
            
            p = store.flush_to_lakehouse("US", "20240101")
            assert p is not None
            assert p.exists()

            store.reset()
            assert store.get_latest_features("MSFT") == {}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

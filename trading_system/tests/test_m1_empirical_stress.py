"""
test_m1_empirical_stress.py — Empirical Stress Test Suite for Milestone 1

Stress tests DataFrameCache, DataValidator, and CorporateActionAdjuster under:
1. High concurrency multi-threading.
2. Rapid TTL expiration.
3. Simulated trading date boundary crossings (datetime monkeypatching).
4. Extreme synthetic datasets (1:10 split, 10:1 reverse split, +500% spikes, NaNs, empty DFs, macro bounds).
"""

import time
import threading
from datetime import date, datetime
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import pytest

from src.utils.technical_cache import DataFrameCache
from src.data_layer.data_validator import (
    DataValidator,
    validate_price_data,
    sanitize_and_validate_price_data,
    filter_price_spikes,
    detect_shared_series_corruption,
    clean_macro_value,
)
from src.data_layer.price_adjuster import CorporateActionAdjuster


# ============================================================================
# 1. DataFrameCache Concurrency, TTL, and Date Boundary Stress Tests
# ============================================================================

def test_dataframe_cache_high_concurrency():
    """Stress test DataFrameCache under 30 concurrent threads performing rapid read/write/evict ops."""
    cache = DataFrameCache(ttl=0.5, max_items=50)
    errors = []
    stop_flag = False

    def worker(thread_id: int):
        nonlocal stop_flag
        for i in range(100):
            if stop_flag:
                break
            try:
                sym = f"SYM_{thread_id % 10}"
                start_date = "2026-01-01"
                df_mock = pd.DataFrame({"Close": [100.0 + i, 101.0 + i]})

                # Alternate operations
                op = i % 6
                if op == 0:
                    cache.set(sym, start_date, df_mock)
                elif op == 1:
                    res = cache.get(sym, start_date)
                    if res is not None:
                        assert isinstance(res, pd.DataFrame)
                elif op == 2:
                    cache.get_or_compute(sym, start_date, lambda s, d: df_mock)
                elif op == 3:
                    cache.evict_expired()
                elif op == 4:
                    if i % 20 == 0:
                        cache.invalidate_symbol(sym)
                elif op == 5:
                    cache.ttl = 0.5 + (i % 5) * 0.1
                    _ = len(cache)
            except Exception as e:
                errors.append(f"Thread-{thread_id} op {i} failed: {e}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"Concurrency errors encountered: {errors}"


def test_dataframe_cache_rapid_ttl_expiration():
    """Verify rapid TTL expiration purges items cleanly."""
    cache = DataFrameCache(ttl=0.05, max_items=100)
    df_sample = pd.DataFrame({"Close": [10.0, 11.0]})

    for i in range(20):
        cache.set(f"STOCK_{i}", "2026-01-01", df_sample)

    assert len(cache) == 20
    # Wait for TTL to expire
    time.sleep(0.08)

    evicted = cache.evict_expired()
    assert evicted == 20
    assert len(cache) == 0
    assert cache.get("STOCK_0", "2026-01-01") is None


def test_dataframe_cache_date_boundary_crossing_monkeypatch():
    """Verify DataFrameCache clears stale entries when datetime.now().date() transitions to a new date."""
    class FakeDateTime(datetime):
        current_date = date(2026, 8, 12)

        @classmethod
        def now(cls, tz=None):
            return datetime(
                cls.current_date.year,
                cls.current_date.month,
                cls.current_date.day,
                15, 30, 0
            )

    with patch("src.utils.technical_cache.datetime", FakeDateTime):
        cache = DataFrameCache(ttl=3600.0, max_items=100)
        df_day1 = pd.DataFrame({"Close": [100.0, 102.0]})
        cache.set("AAPL", "2026-01-01", df_day1)

        assert len(cache) == 1
        assert cache.get("AAPL", "2026-01-01") is not None

        # Cross trading date boundary to next day
        FakeDateTime.current_date = date(2026, 8, 13)

        # Calling get should detect date transition and clear cache automatically
        result = cache.get("AAPL", "2026-01-01")
        assert result is None
        assert len(cache) == 0

        # Further set should work under new date
        df_day2 = pd.DataFrame({"Close": [105.0, 106.0]})
        cache.set("AAPL", "2026-01-01", df_day2)
        assert len(cache) == 1
        assert cache.get("AAPL", "2026-01-01") is not None


# ============================================================================
# 2. DataValidator & CorporateActionAdjuster Extreme Dataset Stress Tests
# ============================================================================

def test_corporate_action_adjuster_1_to_10_split():
    """Test 1:10 stock split backward adjustment (price 1000 -> 100, volume 100 -> 1000)."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    prices = [1000.0]*5 + [100.0]*5
    volumes = [100.0]*5 + [1000.0]*5
    df = pd.DataFrame({
        "Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": volumes
    }, index=dates)

    adjuster = CorporateActionAdjuster(split_threshold_pct=0.40)
    adjusted_df = adjuster.adjust_ohlcv(df)

    # Prior 5 days should be scaled down by 0.1x to $100, prior volume scaled up 10x to 1000
    assert np.isclose(adjusted_df["Close"].iloc[0], 100.0)
    assert np.isclose(adjusted_df["Volume"].iloc[0], 1000.0)
    assert np.isclose(adjusted_df["Close"].iloc[9], 100.0)


def test_corporate_action_adjuster_10_to_1_reverse_split():
    """Test 10:1 reverse stock split backward adjustment (price 10 -> 100, volume 1000 -> 100)."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    prices = [10.0]*5 + [100.0]*5
    volumes = [1000.0]*5 + [100.0]*5
    df = pd.DataFrame({
        "Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": volumes
    }, index=dates)

    adjuster = CorporateActionAdjuster(split_threshold_pct=0.40)
    adjusted_df = adjuster.adjust_ohlcv(df)

    # Prior 5 days should be scaled up by 10x to $100, prior volume scaled down 1/10 to 100
    assert np.isclose(adjusted_df["Close"].iloc[0], 100.0)
    assert np.isclose(adjusted_df["Volume"].iloc[0], 100.0)
    assert np.isclose(adjusted_df["Close"].iloc[9], 100.0)


def test_single_day_500_percent_price_spike():
    """Test isolated single-day +500% price spike filtering."""
    dates = pd.date_range("2026-01-01", periods=7, freq="D")
    prices = [100.0, 101.0, 102.0, 600.0, 103.0, 104.0, 105.0]  # Isolated +500% spike at day 4
    df = pd.DataFrame({
        "Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": [1000]*7
    }, index=dates)

    is_valid, cleaned_df = sanitize_and_validate_price_data("TEST_SPIKE", df)
    assert is_valid is True
    # Day 4 spike should be interpolated/smoothed, not 600.0
    assert cleaned_df["Close"].iloc[3] < 300.0


def test_nan_price_series_rejection():
    """Test validation behavior under varying NaN ratios."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")

    # 1. 100% NaN
    df_all_nan = pd.DataFrame({"Close": [np.nan]*10, "Volume": [100]*10}, index=dates)
    assert validate_price_data("NAN_100", df_all_nan) is False

    # 2. 60% NaN (> 50%)
    df_60_nan = pd.DataFrame({"Close": [100.0]*4 + [np.nan]*6, "Volume": [100]*10}, index=dates)
    assert validate_price_data("NAN_60", df_60_nan) is False

    # 3. 20% NaN (<= 50%)
    df_20_nan = pd.DataFrame({"Close": [100.0]*8 + [np.nan]*2, "Volume": [100]*10}, index=dates)
    assert validate_price_data("NAN_20", df_20_nan) is True


def test_empty_and_none_dataframes():
    """Verify all validator & adjuster methods handle empty/None DataFrames without throwing exceptions."""
    assert validate_price_data("EMPTY", pd.DataFrame()) is False
    assert validate_price_data("NONE", None) is False

    is_valid, out_df = sanitize_and_validate_price_data("EMPTY", pd.DataFrame())
    assert is_valid is False
    assert out_df.empty

    is_valid_none, out_none = sanitize_and_validate_price_data("NONE", None)
    assert is_valid_none is False

    adj_empty = CorporateActionAdjuster().adjust_ohlcv(pd.DataFrame())
    assert adj_empty.empty

    adj_none = CorporateActionAdjuster().adjust_ohlcv(None)
    assert adj_none is None

    filt_empty = filter_price_spikes(pd.DataFrame())
    assert filt_empty.empty


def test_zero_volume_and_negative_prices():
    """Test halted ticker zero-volume filter and negative price rejection."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")

    # Halted ticker: 95% zero volume
    df_halted = pd.DataFrame({"Close": [100.0]*10, "Volume": [0]*10}, index=dates)
    assert validate_price_data("HALTED", df_halted) is False

    # Negative prices: > 50% non-positive
    df_neg = pd.DataFrame({"Close": [-10.0]*6 + [10.0]*4, "Volume": [100]*10}, index=dates)
    assert validate_price_data("NEG_PRICE", df_neg) is False


def test_macro_bounds_and_shared_series_corruption():
    """Test Macro bounds validation and shared-series corruption detection."""
    # Shared series corruption detection
    assert detect_shared_series_corruption(103.478, 103.450, 103.480, 10.3478) is True
    assert detect_shared_series_corruption(15.2, 75.4, 2300.0, 4.25) is False

    # Macro bounds cleaning
    # Out of bounds VIX (90.0) -> fallback
    assert clean_macro_value("90.0", "20.0", "vix") == "20.0"
    # Auto-invert KRW/USD unit rate (0.0007 -> ~1428.6)
    inverted_usdkrw = clean_macro_value("0.0007", "1300.0", "usdkrw")
    assert float(inverted_usdkrw) > 1000.0

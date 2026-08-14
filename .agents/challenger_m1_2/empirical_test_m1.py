"""
empirical_test_m1.py — Empirical test harness for Challenger 2 (Milestone 1)
"""

import sys
import os
import time
import tempfile
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# Add trading_system directory to sys.path so 'from src....' resolves correctly
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
trading_system_dir = os.path.join(repo_root, "trading_system")
if trading_system_dir not in sys.path:
    sys.path.insert(0, trading_system_dir)

from src.persistence.database import StockPriceDB
from src.utils.technical_cache import DataFrameCache
from src.data_layer.data_validator import DataValidator


def test_stock_price_db_spike_filtering():
    print("=== Testing StockPriceDB.update_prices Price Spike Filtering ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db = StockPriceDB(db_path=db_path)
        
        # 1. Normal DataFrame
        dates = pd.date_range(start="2026-01-01", periods=5, freq="D")
        normal_df = pd.DataFrame({
            "Open": [100.0, 101.0, 102.0, 101.5, 103.0],
            "High": [102.0, 103.0, 104.0, 103.0, 105.0],
            "Low": [99.0, 100.0, 101.0, 100.0, 102.0],
            "Close": [101.0, 102.0, 103.0, 102.0, 104.0],
            "Volume": [1000, 1100, 1200, 1050, 1300]
        }, index=dates)

        count = db.update_prices("TEST_NORMAL", normal_df, bypass_validation=False)
        assert count == 5, f"Expected 5 normal rows saved, got {count}"
        print("  [PASS] Normal price data upserted successfully (5 rows).")

        # 2. DataFrame with single-day price spike > 300% (Close jumps from 100 to 450 = +350%)
        spike_dates = pd.date_range(start="2026-01-01", periods=5, freq="D")
        spike_df = pd.DataFrame({
            "Open": [100.0, 440.0, 445.0, 450.0, 455.0],
            "High": [102.0, 460.0, 465.0, 470.0, 475.0],
            "Low": [99.0, 430.0, 440.0, 445.0, 450.0],
            "Close": [100.0, 450.0, 455.0, 460.0, 465.0],
            "Volume": [1000, 1100, 1200, 1050, 1300]
        }, index=spike_dates)

        # Without bypass_validation -> MUST REJECT (>300% spike)
        rejected_count = db.update_prices("TEST_SPIKE", spike_df, bypass_validation=False)
        assert rejected_count == 0, f"Expected 0 rows saved due to spike rejection, got {rejected_count}"
        db_prices = db.get_prices("TEST_SPIKE")
        assert db_prices.empty, "Database should be empty for TEST_SPIKE after rejection"
        print("  [PASS] Single-day >300% price spike REJECTED when bypass_validation=False.")

        # With bypass_validation=True -> MUST ACCEPT
        bypassed_count = db.update_prices("TEST_SPIKE", spike_df, bypass_validation=True)
        assert bypassed_count == 5, f"Expected 5 rows saved when bypass_validation=True, got {bypassed_count}"
        db_prices = db.get_prices("TEST_SPIKE")
        assert len(db_prices) == 5, f"Expected 5 rows in DB for TEST_SPIKE, got {len(db_prices)}"
        print("  [PASS] Single-day >300% price spike ACCEPTED when bypass_validation=True.")

        db.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_dataframe_cache_ttl_and_date_invalidation():
    print("=== Testing DataFrameCache Auto-Eviction & Date Invalidation ===")

    cache = DataFrameCache(ttl=0.3, max_items=10)
    dates = pd.date_range(start="2026-01-01", periods=3, freq="D")
    df = pd.DataFrame({"Close": [10, 20, 30]}, index=dates)

    # 1. Basic Set & Get
    cache.set("AAPL", "2026-01-01", df)
    cached_df = cache.get("AAPL", "2026-01-01")
    assert cached_df is not None and not cached_df.empty, "Cache miss on active item"
    assert len(cache) == 1, f"Expected cache len 1, got {len(cache)}"
    print("  [PASS] Basic set/get successful.")

    # 2. TTL Auto-Eviction
    time.sleep(0.4)  # wait for TTL (0.3s) to expire
    evicted_count = cache.evict_expired()
    assert evicted_count == 1, f"Expected 1 item evicted by evict_expired(), got {evicted_count}"
    assert cache.get("AAPL", "2026-01-01") is None, "Expired item returned from cache"
    assert len(cache) == 0, f"Expected empty cache after eviction, got {len(cache)}"
    print("  [PASS] TTL auto-eviction works correctly.")

    # 3. Automatic eviction during get()
    cache.set("MSFT", "2026-01-01", df)
    time.sleep(0.4)
    res = cache.get("MSFT", "2026-01-01")
    assert res is None, "get() did not return None for expired item"
    assert len(cache) == 0, "get() did not auto-evict expired item"
    print("  [PASS] get() auto-evicts expired item.")

    # 4. Date Change Invalidation
    cache.set("NVDA", "2026-01-01", df)
    assert len(cache) == 1
    # Simulate yesterday date
    cache._last_date = date.today() - timedelta(days=1)
    
    # Next call to get or set should trigger date change invalidation
    res_date_change = cache.get("NVDA", "2026-01-01")
    assert res_date_change is None, "Cache was not cleared on date change"
    assert len(cache) == 0, "Cache size not 0 after date change"
    assert cache._last_date == date.today(), f"cache._last_date not updated to today ({date.today()})"
    print("  [PASS] Trading date change auto-clears cache.")


if __name__ == "__main__":
    test_stock_price_db_spike_filtering()
    test_dataframe_cache_ttl_and_date_invalidation()
    print("\nALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")

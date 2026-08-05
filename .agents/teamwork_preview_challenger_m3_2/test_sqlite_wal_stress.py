"""
SQLite WAL Concurrency & Mutex Stress Test Harness
"""

import os
import sys
import time
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# Add repository root and trading_system to sys.path
ROOT_DIR = r"d:\Finance\code\stock"
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage

def stress_test_single_instance_high_concurrency(num_threads=50, writes_per_thread=20):
    """Scenario 1: Single DB instance shared across 50 concurrent writing threads."""
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "single_inst.db")
    db = StockPriceDB(db_path=db_path)

    lock_errors = 0
    other_errors = 0
    success_count = 0
    errors = []

    def worker(tid):
        nonlocal lock_errors, other_errors, success_count
        for i in range(writes_per_thread):
            df = pd.DataFrame(
                {
                    "Open": [100.0 + tid, 101.0],
                    "High": [105.0, 106.0],
                    "Low": [99.0, 100.0],
                    "Close": [104.0, 105.0],
                    "Volume": [1000 + i, 2000],
                },
                index=pd.date_range("2024-01-01", periods=2, freq="D"),
            )
            try:
                db.update_prices(f"SYM_{tid}_{i}", df)
                success_count += 1
            except Exception as e:
                err_str = str(e)
                errors.append(err_str)
                if "locked" in err_str.lower() or "busy" in err_str.lower():
                    lock_errors += 1
                else:
                    other_errors += 1

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - t0

    db.close()
    shutil.rmtree(test_dir, ignore_errors=True)
    return {
        "scenario": "Single Instance Shared (50 Threads)",
        "total_attempted": num_threads * writes_per_thread,
        "success_count": success_count,
        "lock_errors": lock_errors,
        "other_errors": other_errors,
        "elapsed_sec": round(elapsed, 3),
        "tps": round((num_threads * writes_per_thread) / elapsed, 2),
        "sample_errors": errors[:5]
    }

def stress_test_multi_instance_high_concurrency(num_threads=50, writes_per_thread=20):
    """Scenario 2: Separate DB instances in each thread (no shared Python _write_lock!)."""
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "multi_inst.db")

    # Initialize DB schema first
    init_db = StockPriceDB(db_path=db_path)
    init_db.close()

    lock_errors = 0
    other_errors = 0
    success_count = 0
    errors = []
    lock = threading.Lock()

    def worker(tid):
        nonlocal lock_errors, other_errors, success_count
        # Each thread gets its own StockPriceDB instance
        thread_db = StockPriceDB(db_path=db_path)
        try:
            for i in range(writes_per_thread):
                df = pd.DataFrame(
                    {
                        "Open": [100.0 + tid, 101.0],
                        "High": [105.0, 106.0],
                        "Low": [99.0, 100.0],
                        "Close": [104.0, 105.0],
                        "Volume": [1000 + i, 2000],
                    },
                    index=pd.date_range("2024-01-01", periods=2, freq="D"),
                )
                try:
                    thread_db.update_prices(f"SYM_{tid}_{i}", df)
                    with lock:
                        success_count += 1
                except Exception as e:
                    err_str = str(e)
                    with lock:
                        errors.append(err_str)
                        if "locked" in err_str.lower() or "busy" in err_str.lower():
                            lock_errors += 1
                        else:
                            other_errors += 1
        finally:
            thread_db.close()

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - t0

    shutil.rmtree(test_dir, ignore_errors=True)
    return {
        "scenario": "Multi Instance Independent (50 Threads)",
        "total_attempted": num_threads * writes_per_thread,
        "success_count": success_count,
        "lock_errors": lock_errors,
        "other_errors": other_errors,
        "elapsed_sec": round(elapsed, 3),
        "tps": round((num_threads * writes_per_thread) / elapsed, 2),
        "sample_errors": errors[:5]
    }

def stress_test_market_indicator_storage(num_threads=30, writes_per_thread=10):
    """Scenario 3: MarketIndicatorStorage save_fundamentals under high concurrency."""
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "indicators.db")

    init_storage = MarketIndicatorStorage(db_path=db_path)

    lock_errors = 0
    other_errors = 0
    success_count = 0
    errors = []
    lock = threading.Lock()

    def worker(tid):
        nonlocal lock_errors, other_errors, success_count
        storage = MarketIndicatorStorage(db_path=db_path)
        for i in range(writes_per_thread):
            df_fund = pd.DataFrame([
                {
                    "symbol": f"SYM_{tid}_{i}",
                    "date": "2024-03-31",
                    "revenue": 1000000.0,
                    "operating_income": 200000.0,
                    "net_income": 150000.0,
                    "eps": 1.5,
                    "shares_outstanding": 100000,
                    "dividend_per_share": 0.5,
                    "book_value": 10.0,
                }
            ])
            try:
                storage.save_fundamentals(df_fund)
                with lock:
                    success_count += 1
            except Exception as e:
                err_str = str(e)
                with lock:
                    errors.append(err_str)
                    if "locked" in err_str.lower() or "busy" in err_str.lower():
                        lock_errors += 1
                    else:
                        other_errors += 1

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - t0

    shutil.rmtree(test_dir, ignore_errors=True)
    return {
        "scenario": "MarketIndicatorStorage Multi-Instance (30 Threads)",
        "total_attempted": num_threads * writes_per_thread,
        "success_count": success_count,
        "lock_errors": lock_errors,
        "other_errors": other_errors,
        "elapsed_sec": round(elapsed, 3),
        "tps": round((num_threads * writes_per_thread) / elapsed, 2),
        "sample_errors": errors[:5]
    }

if __name__ == "__main__":
    print("=== Running SQLite WAL Concurrency Stress Tests ===")
    res1 = stress_test_single_instance_high_concurrency(num_threads=50, writes_per_thread=20)
    print("Result 1:", res1)

    res2 = stress_test_multi_instance_high_concurrency(num_threads=50, writes_per_thread=20)
    print("Result 2:", res2)

    res3 = stress_test_market_indicator_storage(num_threads=30, writes_per_thread=10)
    print("Result 3:", res3)

"""
Heavy SQLite WAL Concurrency Stress Test — 100 Threads, High Volume Writes
"""

import os
import sys
import time
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

ROOT_DIR = r"d:\Finance\code\stock"
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

from src.persistence.database import StockPriceDB

def heavy_wal_stress_test(num_threads=100, writes_per_thread=50, rows_per_df=100):
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "heavy_wal.db")

    init_db = StockPriceDB(db_path=db_path)
    init_db.close()

    lock_errors = 0
    other_errors = 0
    success_count = 0
    lock = threading.Lock()
    errors = []

    # Large DataFrame per write
    sample_df = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(rows_per_df)],
            "High": [105.0 + i for i in range(rows_per_df)],
            "Low": [99.0 + i for i in range(rows_per_df)],
            "Close": [104.0 + i for i in range(rows_per_df)],
            "Volume": [1000 + i for i in range(rows_per_df)],
        },
        index=pd.date_range("2020-01-01", periods=rows_per_df, freq="D"),
    )

    def worker(tid):
        nonlocal lock_errors, other_errors, success_count
        thread_db = StockPriceDB(db_path=db_path)
        try:
            for i in range(writes_per_thread):
                sym = f"HEAVY_SYM_{tid}_{i}"
                try:
                    thread_db.update_prices(sym, sample_df)
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
    total_ops = num_threads * writes_per_thread
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - t0

    shutil.rmtree(test_dir, ignore_errors=True)
    return {
        "scenario": f"Heavy WAL Stress ({num_threads} Threads, {total_ops} Total Ops, {rows_per_df} rows/op)",
        "total_attempted_ops": total_ops,
        "total_rows_inserted": total_ops * rows_per_df,
        "success_count": success_count,
        "lock_errors": lock_errors,
        "other_errors": other_errors,
        "elapsed_sec": round(elapsed, 3),
        "ops_per_sec": round(total_ops / elapsed, 2),
        "rows_per_sec": round((total_ops * rows_per_df) / elapsed, 2),
        "sample_errors": errors[:5]
    }

if __name__ == "__main__":
    print("=== Running Heavy SQLite WAL Concurrency Stress Test ===")
    res = heavy_wal_stress_test(num_threads=100, writes_per_thread=20, rows_per_df=50)
    print("Result:", res)

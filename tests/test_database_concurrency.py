"""
tests/test_database_concurrency.py
Multi-threaded concurrency and lock-free Parquet WAL engine stress tests.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
import queue
import shutil
import tempfile
import unittest
import pandas as pd

# Ensure project root and trading_system are in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.data_layer.hybrid_storage import HybridDataEngine, ParquetWALBuffer
from src.persistence.database import StockPriceDB


class TestDatabaseConcurrency(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_prices.db")
        self.staging_dir = os.path.join(self.test_dir, "wal_staging")
        self.db = StockPriceDB(db_path=self.db_path)
        self.hybrid = HybridDataEngine(db_path=self.db_path, staging_dir=self.staging_dir)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_stock_price_db_concurrency_zero_lock_errors(self):
        """Runs 20 concurrent threads writing price updates simultaneously."""
        err_queue = queue.Queue()

        def worker_task(thread_id: int):
            try:
                for i in range(10):
                    symbol = f"SYM_{thread_id}_{i}"
                    df = pd.DataFrame(
                        {
                            "Open": [100.0, 101.0],
                            "High": [105.0, 106.0],
                            "Low": [99.0, 100.0],
                            "Close": [104.0, 105.0],
                            "Volume": [1000, 2000],
                        },
                        index=pd.date_range("2024-01-01", periods=2, freq="D"),
                    )
                    self.db.update_prices(symbol, df)
            except Exception as e:
                err_queue.put(e)

        threads = 20
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(threads)]
            for future in as_completed(futures):
                future.result()

        self.assertTrue(err_queue.empty(), f"Database lock/concurrency errors occurred: {list(err_queue.queue)}")

    def test_parquet_wal_buffer_and_flush(self):
        """Tests lock-free Parquet WAL buffer staging and background compaction."""
        buffer = ParquetWALBuffer(staging_dir=self.staging_dir, master_dir=os.path.join(self.test_dir, "store"))

        # Write updates for symbol 'AAPL' across 5 threads
        def wal_worker(i: int):
            df = pd.DataFrame(
                {"Open": [150.0 + i], "High": [155.0 + i], "Low": [149.0], "Close": [154.0 + i], "Volume": [5000]},
                index=pd.date_range(f"2024-02-0{i+1}", periods=1, freq="D")
            )
            buffer.write_symbol_wal("AAPL", df)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(wal_worker, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()

        staging_data = buffer.get_symbol_staging_data("AAPL")
        self.assertIsNotNone(staging_data)
        self.assertEqual(len(staging_data), 5)

        # Test flush to master SQLite
        flushed = buffer.flush_staging_to_master(db_callback=self.db.update_prices)
        self.assertEqual(flushed, 5)

        db_prices = self.db.get_prices("AAPL")
        self.assertEqual(len(db_prices), 5)


if __name__ == "__main__":
    unittest.main()

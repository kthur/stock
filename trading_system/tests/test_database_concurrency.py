"""
trading_system/tests/test_database_concurrency.py
Multi-threaded concurrency and lock-free SQLite database stress tests.

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
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.data_layer.hybrid_storage import HybridDataEngine, ParquetWALBuffer
from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.execution.oms_engine import ExecutionOMSEngine
from src.data_layer.trade_journal import TradeJournal


class TestDatabaseConcurrency(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_prices.db")
        self.indicator_db_path = os.path.join(self.test_dir, "market_indicators.db")
        self.trade_db_path = os.path.join(self.test_dir, "trade_logs.db")
        self.staging_dir = os.path.join(self.test_dir, "wal_staging")

        self.db = StockPriceDB(db_path=self.db_path)
        self.hybrid = HybridDataEngine(db_path=self.db_path, staging_dir=self.staging_dir)
        self.indicator_storage = MarketIndicatorStorage(db_path=self.indicator_db_path)
        self.oms_engine = ExecutionOMSEngine(db_path=self.trade_db_path)
        self.trade_journal = TradeJournal(db_path=self.trade_db_path)

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

    def test_indicator_storage_multithreaded_concurrency(self):
        """Runs 20 concurrent threads updating indicator indicators simultaneously."""
        err_queue = queue.Queue()

        def indicator_worker(thread_id: int):
            try:
                for i in range(10):
                    df_ind = pd.DataFrame(
                        {
                            "Close": [100.0 + thread_id + i],
                            "SMA_20": [98.0 + i],
                            "RSI_14": [55.0],
                        },
                        index=pd.date_range("2024-01-01", periods=1, freq="D"),
                    )
                    self.indicator_storage.save_indicators(f"IND_{thread_id}", df_ind)
            except Exception as e:
                err_queue.put(e)

        threads = 20
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(indicator_worker, tid) for tid in range(threads)]
            for future in as_completed(futures):
                future.result()

        self.assertTrue(err_queue.empty(), f"Indicator database lock errors occurred: {list(err_queue.queue)}")

    def test_oms_and_trade_journal_concurrent_writes(self):
        """Runs 20 concurrent threads writing order plans and trade journals simultaneously."""
        err_queue = queue.Queue()

        def trade_worker(thread_id: int):
            try:
                for i in range(5):
                    self.oms_engine.record_execution(
                        order_id=f"ORD_{thread_id}_{i}",
                        symbol=f"SYM_{thread_id}",
                        target_price=100.0,
                        executed_price=100.1,
                        executed_volume=10
                    )
                    self.trade_journal.add_trade(
                        symbol=f"SYM_{thread_id}",
                        side="BUY",
                        quantity=10,
                        price=100.1,
                        reason="Test execution"
                    )
            except Exception as e:
                err_queue.put(e)

        threads = 20
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(trade_worker, tid) for tid in range(threads)]
            for future in as_completed(futures):
                future.result()

        self.assertTrue(err_queue.empty(), f"Trade DB lock errors occurred: {list(err_queue.queue)}")

    def test_parquet_wal_buffer_and_flush(self):
        """Tests lock-free Parquet WAL buffer staging and background compaction."""
        buffer = ParquetWALBuffer(staging_dir=self.staging_dir, master_dir=os.path.join(self.test_dir, "store"))

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

        flushed = buffer.flush_staging_to_master(db_callback=self.db.update_prices)
        self.assertEqual(flushed, 5)

        db_prices = self.db.get_prices("AAPL")
        self.assertEqual(len(db_prices), 5)


if __name__ == "__main__":
    unittest.main()

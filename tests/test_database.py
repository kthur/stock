import sys
import unittest
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.persistence.database import TradeLogger, AssetHistoryDB


class TestTradeLogger(unittest.TestCase):
    """TradeLogger 테스트"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.logger = TradeLogger(db_path=self.db_path)

    def tearDown(self):
        async def cleanup():
            await self.logger.close()
            Path(self.db_path).unlink(missing_ok=True)

        asyncio.run(cleanup())

    def test_init_creates_tables(self):
        """초기화 시 테이블 생성"""
        async def test():
            await self.logger._init_database()
            conn = await self.logger._get_conn()
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = await cursor.fetchall()
            table_names = [t[0] for t in tables]
            self.assertIn("orders", table_names)
            self.assertIn("executions", table_names)

        asyncio.run(test())

    def test_log_order(self):
        """주문 로깅"""
        async def test():
            order = _MockOrder()
            await self.logger.log_order(order)
            history = await self.logger.get_trade_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["symbol"], "AAPL")

        asyncio.run(test())

    def test_log_execution(self):
        """체결 기록"""
        async def test():
            await self.logger.log_execution("ORD_001", "AAPL", 10, 150.0)
            conn = await self.logger._get_conn()
            cursor = await conn.execute("SELECT * FROM executions")
            rows = await cursor.fetchall()
            self.assertEqual(len(rows), 1)

        asyncio.run(test())

    def test_double_init_safe(self):
        """중복 초기화 안전성"""
        async def test():
            await self.logger._init_database()
            await self.logger._init_database()
            self.assertTrue(self.logger._db_initialized)

        asyncio.run(test())

    def test_concurrent_init(self):
        """동시 초기화 레이스 컨디션"""
        async def test():
            async def init_task():
                await self.logger._init_database()
                return True

            results = await asyncio.gather(init_task(), init_task(), init_task())
            self.assertTrue(all(results))
            self.assertTrue(self.logger._db_initialized)

        asyncio.run(test())


class TestAssetHistoryDB(unittest.TestCase):
    """AssetHistoryDB 테스트"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.db = AssetHistoryDB(db_path=self.db_path)

    def tearDown(self):
        async def cleanup():
            await self.db.close()
            Path(self.db_path).unlink(missing_ok=True)

        asyncio.run(cleanup())

    def test_save_snapshot(self):
        """자산 스냅샷 저장"""
        async def test():
            await self.db.save_snapshot(100000.0, 150000.0, {"AAPL": 10})
            history = await self.db.get_history()
            self.assertEqual(len(history), 1)

        asyncio.run(test())

    def test_get_history_empty(self):
        """빈 이력 조회"""
        async def test():
            history = await self.db.get_history()
            self.assertEqual(len(history), 0)

        asyncio.run(test())


from src.data_layer.indicator_storage import MarketIndicatorStorage

class TestMarketIndicatorStorage(unittest.TestCase):
    """MarketIndicatorStorage 테스트"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.storage = MarketIndicatorStorage(db_path=self.db_path)

    def tearDown(self):
        self.storage = None
        import gc
        gc.collect()
        Path(self.db_path).unlink(missing_ok=True)

    def test_save_and_get_fundamentals(self):
        """기본적 분석 데이터 저장 및 조회 테스트"""
        import pandas as pd
        df_fundamentals = pd.DataFrame([
            {
                "symbol": "AAPL",
                "date": "2026-06-01",
                "revenue": 90000000000.0,
                "operating_income": 25000000000.0,
                "dividend_per_share": 0.24
            },
            {
                "symbol": "AAPL",
                "date": "2026-06-02",
                "revenue": 95000000000.0,
                "operating_income": 27000000000.0,
                "dividend_per_share": 0.25
            }
        ])

        self.storage.save_fundamentals(df_fundamentals)

        retrieved = self.storage.get_fundamentals("AAPL")
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved.iloc[0]["symbol"], "AAPL")
        self.assertEqual(retrieved.iloc[0]["date"], "2026-06-01")
        self.assertEqual(retrieved.iloc[0]["revenue"], 90000000000.0)
        self.assertEqual(retrieved.iloc[0]["operating_income"], 25000000000.0)
        self.assertEqual(retrieved.iloc[0]["dividend_per_share"], 0.24)

        self.assertEqual(retrieved.iloc[1]["revenue"], 95000000000.0)
        self.assertEqual(retrieved.iloc[1]["operating_income"], 27000000000.0)
        self.assertEqual(retrieved.iloc[1]["dividend_per_share"], 0.25)


class TestMarketIndicatorStorageConcurrency(unittest.TestCase):
    """MarketIndicatorStorage 동시성 및 스트레스 테스트"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.storage = MarketIndicatorStorage(db_path=self.db_path)

    def tearDown(self):
        self.storage = None
        import gc
        gc.collect()
        Path(self.db_path).unlink(missing_ok=True)

    def test_concurrent_writes(self):
        """다중 스레드에서 동시에 DB 쓰기 작업이 Lock 에러 없이 처리되는지 검증"""
        import threading
        import queue

        errors = queue.Queue()
        num_threads = 5
        writes_per_thread = 20

        def worker(thread_idx):
            try:
                for i in range(writes_per_thread):
                    data = {
                        "indices": {
                            f"INDEX_{thread_idx}_{i}": {
                                "symbol": f"SYM_{thread_idx}_{i}",
                                "name": f"Name_{thread_idx}_{i}",
                                "price": 100.0 + i,
                                "change_pct": 0.01 * i
                            }
                        }
                    }
                    self.storage.save_indicators(data, f"2026-06-{i+1:02d}")
            except Exception as e:
                errors.put(e)

        threads = []
        for idx in range(num_threads):
            t = threading.Thread(target=worker, args=(idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertTrue(errors.empty(), f"Errors occurred during concurrent writes: {list(errors.queue)}")


class _MockOrder:
    def __init__(self):
        self.order_id = "ORD_001"
        self.symbol = "AAPL"
        self.order_type = _MockEnum("BUY")
        self.quantity = 10
        self.price = 150.0
        self.status = _MockEnum("EXECUTED")
        self.filled_quantity = 10
        self.created_at = __import__("datetime").datetime.now()
        self.executed_at = __import__("datetime").datetime.now()


class _MockEnum:
    def __init__(self, value):
        self.value = value


from src.persistence.database import StockPriceDB

class TestStockPriceDBConcurrency(unittest.TestCase):
    """StockPriceDB concurrency stress test"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.db = StockPriceDB(db_path=self.db_path)

    def tearDown(self):
        self.db = None
        import gc
        gc.collect()
        Path(self.db_path).unlink(missing_ok=True)

    def test_concurrent_price_updates(self):
        """Verify that concurrent writes to StockPriceDB run without errors or locks"""
        import threading
        import queue
        import pandas as pd

        errors = queue.Queue()
        num_threads = 5
        writes_per_thread = 15

        def worker(thread_idx):
            try:
                for i in range(writes_per_thread):
                    df = pd.DataFrame({
                        "Open": [100.0 + i],
                        "High": [105.0 + i],
                        "Low": [95.0 + i],
                        "Close": [101.0 + i],
                        "Volume": [1000 + i]
                    }, index=[pd.Timestamp(f"2026-06-{i+1:02d}")])
                    self.db.update_prices(f"SYM_{thread_idx}", df)
            except Exception as e:
                errors.put(e)

        threads = []
        for idx in range(num_threads):
            t = threading.Thread(target=worker, args=(idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertTrue(errors.empty(), f"Errors occurred during concurrent StockPriceDB updates: {list(errors.queue)}")


if __name__ == "__main__":
    unittest.main()

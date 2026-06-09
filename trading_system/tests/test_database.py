import sys
import unittest
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.persistence.database import TradeLogger, AssetHistoryDB, AIPredictionDB


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


if __name__ == "__main__":
    unittest.main()

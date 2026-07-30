"""
tests/test_indicator_storage.py
Unit tests for MarketIndicatorStorage persistence and batch fundamentals operations.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import os
import sys
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

from src.data_layer.indicator_storage import MarketIndicatorStorage


class TestMarketIndicatorStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_indicators.db")
        self.storage = MarketIndicatorStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_get_fundamentals(self):
        df_fund = pd.DataFrame([
            {
                "symbol": "005930",
                "date": "2024-03-31",
                "revenue": 71920000000000.0,
                "operating_income": 6610000000000.0,
                "net_income": 6750000000000.0,
                "eps": 980.0,
                "shares_outstanding": 5969782550.0,
                "dividend_per_share": 361.0,
                "book_value": 52000.0,
            },
            {
                "symbol": "000660",
                "date": "2024-03-31",
                "revenue": 12430000000000.0,
                "operating_income": 2886000000000.0,
                "net_income": 1917000000000.0,
                "eps": 2640.0,
                "shares_outstanding": 728002365.0,
                "dividend_per_share": 300.0,
                "book_value": 85000.0,
            }
        ])

        self.storage.save_fundamentals(df_fund)
        self.assertTrue(self.storage.fundamentals_exist("005930"))
        self.assertTrue(self.storage.fundamentals_exist("000660"))

        res_single = self.storage.get_fundamentals("005930")
        self.assertEqual(len(res_single), 1)
        self.assertAlmostEqual(res_single.iloc[0]["operating_income"], 6610000000000.0)

        res_batch = self.storage.get_all_fundamentals(["005930", "000660"])
        self.assertEqual(len(res_batch), 2)

    def test_pipeline_stage_logging(self):
        with self.storage.pipeline_stage("test_stage"):
            pass

        # Verify record in DB
        with self.storage._connect() as conn:
            cursor = conn.execute("SELECT stage, status FROM pipeline_runs WHERE stage = ?", ("test_stage",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test_stage")
            self.assertEqual(row[1], "SUCCESS")

    def test_market_baselines(self):
        df_base = pd.DataFrame(
            [{"market_cap_sum": 1e12, "floating_value_sum": 5e11, "volume_sum": 1e9}],
            index=["2024-01-02"]
        )
        self.storage.save_daily_global_market_baselines("KOSPI", df_base)
        retrieved = self.storage.get_daily_global_market_baselines("KOSPI")
        self.assertFalse(retrieved.empty)
        self.assertIn("2024-01-02", retrieved.index)


if __name__ == "__main__":
    unittest.main()

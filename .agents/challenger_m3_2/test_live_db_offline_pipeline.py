"""
Live DB Empirical Stress Test Harness for Milestone 3 (R3).
Uses actual stock_prices.db and market_indicators.db in offline mode (STOCK_PRICE_FRESHNESS_DAYS=none)
and under simulated total network failure.
"""

import sys
import os
import unittest
from unittest.mock import patch
import logging
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'trading_system')))

from src.config import TradingConfig
from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.earnings_data import fetch_and_store_fundamentals_batch
from run_pipeline import fetch_data_fdr, fetch_indicator_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_live_db_offline_pipeline")


class SocketNetworkBlocker:
    """Guards external socket connections to guarantee zero remote network traffic in offline mode."""
    def __enter__(self):
        self._orig = socket.socket.connect
        def guarded_connect(s, addr):
            host = addr[0] if isinstance(addr, tuple) and len(addr) > 0 else str(addr)
            if host in ("127.0.0.1", "localhost", "::1"):
                return self._orig(s, addr)
            raise RuntimeError(f"NETWORK_CALL_BLOCKED: Attempted to connect to {addr}")
        socket.socket.connect = guarded_connect
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        socket.socket.connect = self._orig


class TestLiveDBOfflinePipeline(unittest.TestCase):

    def setUp(self):
        self.stock_db_path = os.path.join("trading_system", "stock_prices.db")
        self.indicator_db_path = os.path.join("trading_system", "market_indicators.db")
        self.assertTrue(os.path.exists(self.stock_db_path), f"Database not found: {self.stock_db_path}")
        self.assertTrue(os.path.exists(self.indicator_db_path), f"Database not found: {self.indicator_db_path}")

        self.price_db = StockPriceDB(self.stock_db_path)
        self.indicator_storage = MarketIndicatorStorage(self.indicator_db_path)

    def tearDown(self):
        del self.price_db

    def test_live_db_offline_data_serving(self):
        """Test reading actual cached stock prices and indicators using real DB files in offline mode."""
        os.environ["STOCK_PRICE_FRESHNESS_DAYS"] = "none"
        config = TradingConfig()
        freshness_days = config.get_freshness_days()

        test_symbols = [("005930", "KOSPI"), ("000660", "KOSPI"), ("AAPL", "SP500")]

        with SocketNetworkBlocker():
            # 1. Fetch stock prices
            for sym, market in test_symbols:
                df = fetch_data_fdr(sym, market, "2024-01-01", price_db=self.price_db, freshness_days=freshness_days)
                self.assertIsNotNone(df, f"Expected cached price data for {sym}")
                self.assertFalse(df.empty, f"Cached data for {sym} should not be empty")
                logger.info(f"[PASS] Retrieved {len(df)} rows for {sym} from stock_prices.db cleanly in offline mode.")

            # 2. Fetch indicators
            df_ind = fetch_indicator_history("2024-01-01", price_db=self.price_db, freshness_days=freshness_days)
            self.assertIsNotNone(df_ind, "Expected cached indicator history")
            self.assertFalse(df_ind.empty, "Cached indicator history should not be empty")
            logger.info(f"[PASS] Retrieved indicator history DataFrame with columns {list(df_ind.columns)} in offline mode.")

            # 3. Fundamental batch in offline mode (expiry_days = -1)
            os.environ["FUNDAMENTAL_CACHE_EXPIRY_DAYS"] = "-1"
            processed = fetch_and_store_fundamentals_batch(
                symbols=[s[0] for s in test_symbols],
                symbol_market_map={s[0]: s[1] for s in test_symbols},
                storage=self.indicator_storage
            )
            self.assertEqual(processed, 0, "Offline fundamental batch should skip all network requests")
            logger.info("[PASS] Fundamental batch skipped 100% of network requests in offline mode.")

    @patch("yfinance.download", side_effect=RuntimeError("HTTP 429 Rate Limit"))
    @patch("FinanceDataReader.DataReader", side_effect=RuntimeError("HTTP 504 Gateway Timeout"))
    def test_live_db_network_failure_fallback(self, mock_fdr, mock_yf):
        """Test network failure on real DB files with freshness_days=1 (online mode requested, but network fails)."""
        os.environ["STOCK_PRICE_FRESHNESS_DAYS"] = "1"

        test_symbol = "005930"
        market = "KOSPI"

        df = fetch_data_fdr(test_symbol, market, "2024-01-01", price_db=self.price_db, freshness_days=1)
        self.assertIsNotNone(df, "Should return cached data on network failure")
        self.assertFalse(df.empty, "Data should not be empty")
        logger.info(f"[PASS] Live DB network failure fallback served {len(df)} cached rows for {test_symbol} safely.")


if __name__ == "__main__":
    unittest.main()

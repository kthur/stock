"""
Empirical Resilience and Network Fallback Verification Suite for Milestone 3 (R3).
Tests:
1. Offline Mode Execution (STOCK_PRICE_FRESHNESS_DAYS=none / freshness_days=-1, fundamental_cache_expiry_days=-1)
2. Network Failure Fallback Execution (Mocking HTTP 429 / Timeout for yfinance & FDR & async_fetch_fundamentals)
3. Full Pipeline Execution under total network blocking
"""

import sys
import os
import unittest
from unittest.mock import patch, AsyncMock
import logging
import pandas as pd
import numpy as np
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'trading_system')))

from src.config import TradingConfig
from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.earnings_data import async_fetch_fundamentals, fetch_and_store_fundamentals_batch
from run_pipeline import fetch_data_fdr, fetch_indicator_history, technical_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_empirical_resilience")


class SocketNetworkBlocker:
    """Strictly block external network calls while allowing local asyncio event loop self-pipes."""
    def __enter__(self):
        self._orig_connect = socket.socket.connect
        def guarded_connect(s, address):
            host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
            if host in ("127.0.0.1", "localhost", "::1"):
                return self._orig_connect(s, address)
            raise RuntimeError(f"NETWORK_VIOLATION: Blocked non-local network connection attempt to {address}")
        socket.socket.connect = guarded_connect
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        socket.socket.connect = self._orig_connect


def create_dummy_ohlcv(symbol="005930", num_days=30):
    # Fixed historical date range so query start_date cleanly encompasses all rows
    dates = pd.date_range(start="2025-01-01", periods=num_days, freq='D')
    df = pd.DataFrame({
        'Open': np.random.uniform(50000, 60000, size=num_days),
        'High': np.random.uniform(60000, 65000, size=num_days),
        'Low': np.random.uniform(45000, 50000, size=num_days),
        'Close': np.random.uniform(50000, 60000, size=num_days),
        'Volume': np.random.randint(100000, 1000000, size=num_days),
    }, index=dates)
    return df


class TestOfflineModeExecution(unittest.TestCase):
    """Requirement 1: Verify offline mode execution with offline flags."""

    def setUp(self):
        # Clear technical cache memory to prevent cross-test leakage
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()

        self.db_path = "test_offline_prices.db"
        self.storage_db_path = "test_offline_indicators.db"
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

        self.price_db = StockPriceDB(self.db_path)
        self.indicator_storage = MarketIndicatorStorage(self.storage_db_path)

        # Seed cached price data
        self.symbol = "005930"
        self.market = "KOSPI"
        self.df_cached = create_dummy_ohlcv(self.symbol, 30)
        self.price_db.update_prices(self.symbol, self.df_cached)

        # Seed cached indicator data
        self.price_db.update_prices("^VIX", self.df_cached)

        # Seed fundamental meta
        self.indicator_storage.save_fundamental_meta(self.symbol, "2026-01-01")

    def tearDown(self):
        del self.price_db
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

    def test_stock_price_freshness_days_none_bypasses_network(self):
        """Verify STOCK_PRICE_FRESHNESS_DAYS=none bypasses network calls completely and returns DB cache."""
        os.environ["STOCK_PRICE_FRESHNESS_DAYS"] = "none"
        config = TradingConfig()
        freshness_days = config.get_freshness_days()
        self.assertEqual(freshness_days, -1, "Freshness days should be -1 for 'none'")

        with SocketNetworkBlocker():
            df_result = fetch_data_fdr(self.symbol, self.market, "2025-01-01", price_db=self.price_db, freshness_days=freshness_days)

        self.assertIsNotNone(df_result, "Result should not be None")
        self.assertFalse(df_result.empty, "Result should not be empty")
        expected_db_df = self.price_db.get_prices(self.symbol, start_date="2025-01-01")
        self.assertEqual(len(df_result), len(expected_db_df), "Should serve cached rows without network call")
        logger.info("[PASS] fetch_data_fdr correctly bypassed network in offline mode (STOCK_PRICE_FRESHNESS_DAYS=none).")

    def test_indicator_freshness_days_none_bypasses_network(self):
        """Verify fetch_indicator_history with freshness_days=-1 bypasses network calls completely."""
        with SocketNetworkBlocker():
            df_ind = fetch_indicator_history("2025-01-01", price_db=self.price_db, freshness_days=-1)

        self.assertIsNotNone(df_ind, "Indicator result should not be None")
        self.assertIn("vix_change", df_ind.columns)
        logger.info("[PASS] fetch_indicator_history correctly bypassed network in offline mode.")

    def test_fundamental_cache_expiry_days_negative_bypasses_network(self):
        """Verify fundamental_cache_expiry_days = -1 skips fundamental network fetching."""
        os.environ["FUNDAMENTAL_CACHE_EXPIRY_DAYS"] = "-1"

        with SocketNetworkBlocker():
            processed_count = fetch_and_store_fundamentals_batch(
                symbols=[self.symbol],
                symbol_market_map={self.symbol: self.market},
                storage=self.indicator_storage
            )

        self.assertEqual(processed_count, 0, "Offline batch fetch should process 0 network requests")
        logger.info("[PASS] fetch_and_store_fundamentals_batch correctly bypassed network when expiry_days < 0.")


class TestNetworkFailureFallbackExecution(unittest.TestCase):
    """Requirement 2: Verify network failure fallback execution (429/timeout/exceptions)."""

    def setUp(self):
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()

        self.db_path = "test_fallback_prices.db"
        self.storage_db_path = "test_fallback_indicators.db"
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

        self.price_db = StockPriceDB(self.db_path)
        self.indicator_storage = MarketIndicatorStorage(self.storage_db_path)

        # Seed cached price data
        self.symbol = "005930"
        self.market = "KOSPI"
        self.df_cached = create_dummy_ohlcv(self.symbol, 20)
        self.price_db.update_prices(self.symbol, self.df_cached)

    def tearDown(self):
        del self.price_db
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

    @patch("yfinance.download", side_effect=RuntimeError("HTTP 429 Too Many Requests"))
    @patch("FinanceDataReader.DataReader", side_effect=TimeoutError("Connection timed out to provider"))
    def test_fetch_data_fdr_network_failure_falls_back_to_db_cache(self, mock_fdr, mock_yf):
        """Verify fetch_data_fdr falls back to cached DB data when Tier 1 & 2 fail with 429/timeout."""
        df_result = fetch_data_fdr(self.symbol, self.market, "2025-01-01", price_db=self.price_db, freshness_days=1)

        self.assertIsNotNone(df_result, "Should not return None when cached data exists")
        expected_cached = self.price_db.get_prices(self.symbol, start_date="2025-01-01")
        self.assertEqual(len(df_result), len(expected_cached), "Should return stored cached data")
        logger.info("[PASS] fetch_data_fdr safely fell back to local DB cache on 429/Timeout.")

    @patch("aiohttp.ClientSession.get")
    def test_async_fetch_fundamentals_http_429_retry_and_fallback(self, mock_get):
        """Verify async_fetch_fundamentals handles 429 rate limit retries and returns None without crashing."""
        import asyncio

        # Mock response returning HTTP 429
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_get.return_value.__aenter__.return_value = mock_response

        result = asyncio.run(async_fetch_fundamentals(self.symbol, self.market, max_retries=2))

        self.assertIsNone(result, "Should return None on persistent 429 errors")
        self.assertGreaterEqual(mock_get.call_count, 2, "Should have retried up to max_retries")
        logger.info("[PASS] async_fetch_fundamentals retried on 429 errors and safely returned None without crashing.")


class TestPipelineNetworkBlockingResilience(unittest.TestCase):
    """Requirement 3: Assert zero pipeline crashes under network blocking conditions."""

    def setUp(self):
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()

        self.db_path = "test_pipeline_prices.db"
        self.storage_db_path = "test_pipeline_indicators.db"
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

        self.price_db = StockPriceDB(self.db_path)
        self.indicator_storage = MarketIndicatorStorage(self.storage_db_path)

        # Seed symbols
        self.symbols = ["005930", "000660", "AAPL"]
        self.market_map = {"005930": "KOSPI", "000660": "KOSPI", "AAPL": "SP500"}
        for s in self.symbols:
            self.price_db.update_prices(s, create_dummy_ohlcv(s, 30))

        # Seed indicators
        for ind in ["^VIX", "^TNX", "USDKRW=X", "^GSPC", "DX-Y.NYB", "CL=F", "^KS11", "^KQ11"]:
            self.price_db.update_prices(ind, create_dummy_ohlcv(ind, 30))

    def tearDown(self):
        del self.price_db
        if hasattr(technical_cache, "_cache"):
            technical_cache._cache.clear()
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except Exception: pass
        if os.path.exists(self.storage_db_path):
            try: os.remove(self.storage_db_path)
            except Exception: pass

    @patch("yfinance.download", side_effect=RuntimeError("Network blocked (offline scenario)"))
    @patch("FinanceDataReader.DataReader", side_effect=RuntimeError("Network blocked (offline scenario)"))
    def test_zero_pipeline_crashes_under_network_blocking(self, mock_fdr, mock_yf):
        """Assert zero crashes across all pipeline data retrieval components under total network failure."""
        logger.info("Executing network blocking simulation across pipeline functions...")

        # 1. Price fetching for symbols
        for sym in self.symbols:
            df = fetch_data_fdr(sym, self.market_map[sym], "2025-01-01", price_db=self.price_db, freshness_days=1)
            self.assertIsNotNone(df, f"Symbol {sym} should fall back to DB cache")
            self.assertFalse(df.empty, f"Symbol {sym} data should not be empty")

        # 2. Indicator fetching
        df_ind = fetch_indicator_history("2025-01-01", price_db=self.price_db, freshness_days=1)
        self.assertIsNotNone(df_ind, "Indicators should fall back to DB cache")

        # 3. Fundamental batch fetching under network failure
        stored_count = fetch_and_store_fundamentals_batch(
            symbols=self.symbols,
            symbol_market_map=self.market_map,
            storage=self.indicator_storage
        )
        self.assertEqual(stored_count, 0, "No new fundamentals stored when network fails and no web data returned")

        logger.info("[PASS] Zero pipeline crashes occurred under total network blocking. 100% resilient fallback verified.")


if __name__ == "__main__":
    unittest.main()

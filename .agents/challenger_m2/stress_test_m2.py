"""
Empirical Stress Harness for Milestone 2 (Challenger 2)
Tests:
1. Ticker symbol normalization edge cases (unpadded KRX, KONEX, US dot share class BRK.B).
2. Fallback cascade under forced primary failures (yfinance -> FDR -> Naver -> PyKRX / Stooq -> DB cache).
3. DataValidator cache gate (corrupted payload rejection from DB).
4. ffill OHLCV contiguity across data structures.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from trading_system.src.persistence.database import StockPriceDB, normalize_symbol
from trading_system.src.data_layer.indicator_storage import _is_krx_symbol
from trading_system.src.data_layer.data_validator import DataValidator
from trading_system.run_pipeline import (
    _KR_MARKET_SUFFIX,
    _fetch_data_fdr_network,
    fetch_data_fdr,
)
from trading_system.src.data_layer.market_data_handler import MarketDataHandler, PriceBar


class Milestone2EmpiricalStressTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(__file__).parent / "tmp_test"
        self.tmp_dir.mkdir(exist_ok=True)
        self.db_path = self.tmp_dir / "test_stock_prices.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.db = StockPriceDB(str(self.db_path))

    def tearDown(self):
        self.db.close()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass

    # =========================================================================
    # VERIFICATION STEP 1: Ticker Normalization Edge Cases
    # =========================================================================
    def test_krx_unpadded_normalization(self):
        """Test unpadded KRX symbols ('5930' -> '005930', '35460' -> '035460')."""
        self.assertEqual(normalize_symbol("5930"), "005930")
        self.assertEqual(normalize_symbol("35460"), "035460")
        self.assertEqual(normalize_symbol("005930"), "005930")
        self.assertEqual(normalize_symbol("1"), "000001")
        self.assertEqual(normalize_symbol("  5930  "), "005930")
        
        # Test _is_krx_symbol
        self.assertTrue(_is_krx_symbol("5930"))
        self.assertTrue(_is_krx_symbol("35460"))
        self.assertTrue(_is_krx_symbol("005930"))
        self.assertTrue(_is_krx_symbol("005930.KS"))
        self.assertTrue(_is_krx_symbol("035460.KS"))
        self.assertTrue(_is_krx_symbol("035460.KQ"))

    def test_konex_ticker_handling(self):
        """Test KONEX market suffix resolution and DB operations."""
        self.assertIn("KONEX", _KR_MARKET_SUFFIX)
        self.assertEqual(_KR_MARKET_SUFFIX["KONEX"], ".KS")
        
        # Insert unpadded KONEX symbol into DB
        dates = pd.date_range("2024-01-01", periods=3)
        df = pd.DataFrame({
            "Open": [1000.0, 1010.0, 1020.0],
            "High": [1050.0, 1060.0, 1070.0],
            "Low": [990.0, 1000.0, 1010.0],
            "Close": [1040.0, 1050.0, 1060.0],
            "Volume": [500, 600, 700]
        }, index=dates)
        
        count = self.db.update_prices("35460", df)
        self.assertEqual(count, 3)
        
        # Verify query using padded '035460' or unpadded '35460'
        df_padded = self.db.get_prices("035460")
        df_unpadded = self.db.get_prices("35460")
        self.assertEqual(len(df_padded), 3)
        self.assertEqual(len(df_unpadded), 3)
        self.assertEqual(self.db.get_latest_date("35460"), "2024-01-03")

    def test_us_dot_share_class_normalization(self):
        """Test BRK.B yfinance query string conversion vs DB canonical key."""
        self.assertEqual(normalize_symbol("BRK.B"), "BRK.B")
        self.assertFalse(_is_krx_symbol("BRK.B"))
        
        # Mock yfinance to capture the query ticker string
        with patch("trading_system.run_pipeline._fetch_yf_primary") as mock_yf:
            mock_df = pd.DataFrame({
                "Open": [350.0], "High": [355.0], "Low": [349.0], "Close": [352.0], "Volume": [10000]
            }, index=pd.date_range("2024-01-01", periods=1))
            mock_yf.return_value = mock_df
            
            res = _fetch_data_fdr_network("BRK.B", "SP500", "2024-01-01")
            self.assertFalse(res.empty)
            mock_yf.assert_called_with("BRK-B", "2024-01-01")
            
        # Insert into DB and verify stored under canonical key 'BRK.B'
        self.db.update_prices("BRK.B", mock_df)
        self.assertEqual(self.db.count_rows("BRK.B"), 1)
        res_db = self.db.get_prices("BRK.B")
        self.assertEqual(len(res_db), 1)

    # =========================================================================
    # VERIFICATION STEP 2: Fallback Cascade under Forced Primary Failures
    # =========================================================================
    def test_krx_fallback_cascade_order(self):
        """Verify KRX fallback cascade: yfinance -> FDR -> Naver Direct -> PyKRX."""
        mock_df = pd.DataFrame({
            "Open": [50000.0], "High": [51000.0], "Low": [49500.0], "Close": [50500.0], "Volume": [100000]
        }, index=pd.date_range("2024-01-01", periods=1))

        # Scenario A: yfinance raises Exception -> FDR raises Exception -> Naver succeeds
        with patch("trading_system.run_pipeline._fetch_yf_primary", side_effect=Exception("yfinance down")), \
             patch("trading_system.run_pipeline.fdr.DataReader", side_effect=Exception("FDR down")), \
             patch("trading_system.run_pipeline._fetch_naver_direct", return_value=mock_df) as mock_naver, \
             patch("trading_system.run_pipeline._fetch_pykrx") as mock_pykrx:
            
            res = _fetch_data_fdr_network("005930", "KOSPI", "2024-01-01")
            self.assertFalse(res.empty)
            mock_naver.assert_called_once_with("005930", "2024-01-01")
            mock_pykrx.assert_not_called()

        # Scenario B: yfinance returns empty -> FDR fails -> Naver fails -> PyKRX succeeds
        with patch("trading_system.run_pipeline._fetch_yf_primary", return_value=pd.DataFrame()), \
             patch("trading_system.run_pipeline.fdr.DataReader", side_effect=Exception("FDR down")), \
             patch("trading_system.run_pipeline._fetch_naver_direct", return_value=pd.DataFrame()), \
             patch("trading_system.run_pipeline._fetch_pykrx", return_value=mock_df) as mock_pykrx:
            
            res = _fetch_data_fdr_network("005930", "KOSPI", "2024-01-01")
            self.assertFalse(res.empty)
            mock_pykrx.assert_called_once_with("005930", "2024-01-01")

    def test_us_fallback_cascade_order(self):
        """Verify US fallback cascade: yfinance -> FDR -> Stooq/Yahoo Direct."""
        mock_df = pd.DataFrame({
            "Open": [180.0], "High": [182.0], "Low": [179.0], "Close": [181.0], "Volume": [500000]
        }, index=pd.date_range("2024-01-01", periods=1))

        with patch("trading_system.run_pipeline._fetch_yf_primary", side_effect=Exception("yfinance 429")), \
             patch("trading_system.run_pipeline.fdr.DataReader", side_effect=Exception("FDR 500")), \
             patch("trading_system.run_pipeline._fetch_stooq_or_yahoo_direct", return_value=mock_df) as mock_stooq:
            
            res = _fetch_data_fdr_network("AAPL", "NASDAQ", "2024-01-01")
            self.assertFalse(res.empty)
            mock_stooq.assert_called_once_with("AAPL", "2024-01-01")

    def test_offline_db_cache_fallback(self):
        """Verify that when all network providers fail, fetch_data_fdr falls back to DB cache."""
        # Seed DB cache with historical prices
        dates = pd.date_range("2024-01-01", periods=5)
        seed_df = pd.DataFrame({
            "Open": [100.0] * 5, "High": [105.0] * 5, "Low": [95.0] * 5, "Close": [102.0] * 5, "Volume": [1000] * 5
        }, index=dates)
        self.db.update_prices("AAPL", seed_df)

        # Force all network calls to fail
        with patch("trading_system.run_pipeline._fetch_data_fdr_network", side_effect=ValueError("All providers failed")):
            res = fetch_data_fdr("AAPL", "SP500", "2024-01-01", price_db=self.db, freshness_days=0)
            self.assertIsNotNone(res)
            self.assertEqual(len(res), 5)

    # =========================================================================
    # VERIFICATION STEP 3: DataValidator Gate
    # =========================================================================
    def test_datavalidator_corrupted_payload_rejection(self):
        """Verify DataValidator rejects negative close, high NaN ratio (>50%), extreme jumps, and zero volume."""
        dates = pd.date_range("2024-01-01", periods=10)

        # 1. Negative Close
        df_neg = pd.DataFrame({
            "Open": [100.0]*10, "High": [100.0]*10, "Low": [-100.0]*10, "Close": [-100.0]*10, "Volume": [1000]*10
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("BAD1", df_neg))

        # 2. > 50% NaNs (6 NaNs out of 10 = 60%)
        df_nan = pd.DataFrame({
            "Open": [100.0]*10, "High": [105.0]*10, "Low": [95.0]*10,
            "Close": [100.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 103.0, 104.0, 105.0],
            "Volume": [1000]*10
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("BAD2", df_nan))

        # 3. Extreme daily return jump (> 100% change on > 5% rows)
        prices = [10.0, 50.0, 200.0, 800.0, 3200.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        df_jump = pd.DataFrame({
            "Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": [1000]*10
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("BAD3", df_jump))

        # 4. Volume == 0 ratio > 90% (halted symbol)
        df_halt = pd.DataFrame({
            "Open": [100.0]*10, "High": [100.0]*10, "Low": [100.0]*10, "Close": [100.0]*10, "Volume": [0]*10
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("BAD4", df_halt))

        # 5. Valid DataFrame passes validation
        df_valid = pd.DataFrame({
            "Open": [100.0]*10, "High": [105.0]*10, "Low": [95.0]*10, "Close": [102.0]*10, "Volume": [1000]*10
        }, index=dates)
        self.assertTrue(DataValidator.validate_price_data("GOOD", df_valid))

    def test_datavalidator_gate_prevents_db_corruption(self):
        """Verify fetch_data_fdr rejects corrupted network payload and does NOT update DB."""
        dates = pd.date_range("2024-01-01", periods=10)
        corrupted_df = pd.DataFrame({
            "Open": [-50.0]*10, "High": [-40.0]*10, "Low": [-60.0]*10, "Close": [-50.0]*10, "Volume": [100]*10
        }, index=dates)

        with patch("trading_system.run_pipeline._fetch_data_fdr_network", return_value=corrupted_df):
            res = fetch_data_fdr("CORRUPT_TICKER", "SP500", "2024-01-01", price_db=self.db, freshness_days=1)
            # DB should have 0 rows saved for CORRUPT_TICKER
            self.assertEqual(self.db.count_rows("CORRUPT_TICKER"), 0)

    # =========================================================================
    # VERIFICATION STEP 4: Contiguous OHLCV & Date Contiguity (ffill)
    # =========================================================================
    def test_market_data_handler_ffill_contiguity(self):
        """Verify MarketDataHandler._df_to_price_bars forward-fills intermediate NaNs."""
        dates = pd.date_range("2024-01-01", periods=4)
        df_with_nans = pd.DataFrame({
            "Open": [100.0, np.nan, 102.0, 103.0],
            "High": [105.0, np.nan, 107.0, 108.0],
            "Low": [99.0, np.nan, 101.0, 102.0],
            "Close": [104.0, np.nan, 106.0, 107.0],
            "Volume": [1000, np.nan, 1200, 1300]
        }, index=dates)

        bars = MarketDataHandler._df_to_price_bars(df_with_nans)
        self.assertEqual(len(bars), 4)
        # Check second bar (index 1) has forward-filled values from bar 0
        self.assertEqual(bars[1].open, 100.0)
        self.assertEqual(bars[1].high, 105.0)
        self.assertEqual(bars[1].low, 99.0)
        self.assertEqual(bars[1].close, 104.0)
        self.assertEqual(bars[1].volume, 1000)

    def test_fetch_data_fdr_ffill_contiguity(self):
        """Verify fetch_data_fdr applies ffill on return DataFrames."""
        dates = pd.date_range("2024-01-01", periods=3)
        valid_df_with_nan = pd.DataFrame({
            "Open": [100.0, np.nan, 102.0],
            "High": [105.0, np.nan, 107.0],
            "Low": [99.0, np.nan, 101.0],
            "Close": [104.0, np.nan, 106.0],
            "Volume": [1000, np.nan, 1200]
        }, index=dates)

        with patch("trading_system.run_pipeline._fetch_data_fdr_network", return_value=valid_df_with_nan):
            res = fetch_data_fdr("TEST_FFILL", "SP500", "2024-01-01", price_db=self.db, freshness_days=1)
            self.assertIsNotNone(res)
            # Verify no NaN remains in OHLCV columns after ffill
            self.assertEqual(res["Close"].isna().sum(), 0)
            self.assertEqual(res.loc["2024-01-02", "Close"], 104.0)


if __name__ == "__main__":
    unittest.main()

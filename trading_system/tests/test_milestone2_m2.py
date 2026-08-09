"""
Unit tests for Milestone 2 (Worker M2):
- Ticker Symbol Normalization (KRX zfill(6), US dots to hyphens, KONEX suffix)
- Multi-Tier Fallback Data Fetching
- DataValidator Gate in fetch_data_fdr
- Contiguous OHLCV & Date Contiguity (ffill)
"""

import pandas as pd
import numpy as np
from unittest.mock import patch

from trading_system.src.persistence.database import StockPriceDB, normalize_symbol
from trading_system.src.data_layer.indicator_storage import _is_krx_symbol
from trading_system.run_pipeline import _KR_MARKET_SUFFIX, _fetch_data_fdr_network, fetch_data_fdr
from trading_system.src.data_layer.market_data_handler import MarketDataHandler


def test_normalize_symbol_krx_and_us():
    # KRX unpadded digits -> 6-digit zfill
    assert normalize_symbol("5930") == "005930"
    assert normalize_symbol("35720") == "035720"
    assert normalize_symbol("005930") == "005930"

    # US tickers retained
    assert normalize_symbol("BRK.B") == "BRK.B"
    assert normalize_symbol("AAPL") == "AAPL"


def test_is_krx_symbol_unpadded():
    # Must handle unpadded 1-6 digit strings gracefully
    assert _is_krx_symbol("5930") is True
    assert _is_krx_symbol("005930") is True
    assert _is_krx_symbol("005930.KS") is True
    assert _is_krx_symbol("035720.KQ") is True
    assert _is_krx_symbol("AAPL") is False
    assert _is_krx_symbol("BRK.B") is False


def test_kr_market_suffix_konex():
    assert 'KONEX' in _KR_MARKET_SUFFIX
    assert _KR_MARKET_SUFFIX['KONEX'] == '.KS'


def test_stock_prices_db_normalization(tmp_path):
    db_file = str(tmp_path / "test_prices.db")
    db = StockPriceDB(db_path=db_file)

    dates = pd.date_range("2024-01-01", periods=3)
    df = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0],
        "High": [105.0, 106.0, 107.0],
        "Low": [99.0, 100.0, 101.0],
        "Close": [104.0, 105.0, 106.0],
        "Volume": [1000, 1100, 1200]
    }, index=dates)

    # Insert unpadded symbol '5930'
    db.update_prices("5930", df)

    # Query with '005930' or '5930' should return data
    res1 = db.get_prices("005930")
    res2 = db.get_prices("5930")
    assert len(res1) == 3
    assert len(res2) == 3
    assert db.get_latest_date("5930") == "2024-01-03"


def test_us_ticker_yfinance_formatting():
    # Check yfinance ticker formatting in _fetch_data_fdr_network
    with patch("trading_system.run_pipeline._fetch_yf_primary") as mock_yf:
        mock_df = pd.DataFrame({
            "Open": [100.0], "High": [105.0], "Low": [99.0], "Close": [104.0], "Volume": [1000]
        }, index=pd.date_range("2024-01-01", periods=1))
        mock_yf.return_value = mock_df

        # US dot conversion: BRK.B -> BRK-B
        res = _fetch_data_fdr_network("BRK.B", "SP500", "2024-01-01")
        assert not res.empty
        mock_yf.assert_called_with("BRK-B", "2024-01-01")


def test_multitier_fallback_krx():
    with patch("trading_system.run_pipeline._fetch_yf_primary", side_effect=Exception("yfinance down")), \
         patch("trading_system.run_pipeline.fdr.DataReader", side_effect=Exception("FDR down")), \
         patch("trading_system.run_pipeline._fetch_naver_direct") as mock_naver:

        mock_df = pd.DataFrame({
            "Open": [100.0], "High": [105.0], "Low": [99.0], "Close": [104.0], "Volume": [1000]
        }, index=pd.date_range("2024-01-01", periods=1))
        mock_naver.return_value = mock_df

        res = _fetch_data_fdr_network("005930", "KOSPI", "2024-01-01")
        assert not res.empty
        mock_naver.assert_called_once_with("005930", "2024-01-01")


def test_datavalidator_gate_in_fetch_data_fdr(tmp_path):
    db_file = str(tmp_path / "test_prices.db")
    db = StockPriceDB(db_path=db_file)

    # Corrupted network payload (negative prices)
    corrupted_df = pd.DataFrame({
        "Open": [-100.0], "High": [-100.0], "Low": [-100.0], "Close": [-100.0], "Volume": [1000]
    }, index=pd.date_range("2024-01-01", periods=1))

    with patch("trading_system.run_pipeline._fetch_data_fdr_network", return_value=corrupted_df):
        res = fetch_data_fdr("AAPL", "SP500", "2024-01-01", price_db=db, freshness_days=1)
        # Corrupted payload should be rejected by DataValidator and NOT saved to price_db
        assert db.count_rows("AAPL") == 0


def test_contiguous_ohlcv_ffill():
    # DataFrame with NaN in middle of OHLCV columns
    dates = pd.date_range("2024-01-01", periods=3)
    df = pd.DataFrame({
        "Open": [100.0, np.nan, 102.0],
        "High": [105.0, np.nan, 107.0],
        "Low": [99.0, np.nan, 101.0],
        "Close": [104.0, np.nan, 106.0],
        "Volume": [1000, np.nan, 1200]
    }, index=dates)

    bars = MarketDataHandler._df_to_price_bars(df)
    assert len(bars) == 3
    # Second bar should have forward-filled values from first bar instead of NaN
    assert bars[1].close == 104.0
    assert bars[1].volume == 1000

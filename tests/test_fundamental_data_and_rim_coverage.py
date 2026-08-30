"""
tests/test_fundamental_data_and_rim_coverage.py
Unit tests verifying fundamental data extraction, shares resolution, bank statement handling,
batch SQLite caching, and RIM valuation coverage.
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

from src.data_layer.earnings_data import (
    _yf_ticker,
    compute_regulatory_filing_lag,
    _fetch_fundamentals_network,
    fetch_fundamentals,
    fetch_and_store_fundamentals_batch,
)
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.core.rim_valuation import RIMValuationEngine


def test_yf_ticker_conversion():
    """Verify ticker conversion for KRX and US markets."""
    assert _yf_ticker("005930", "KOSPI") == "005930.KS"
    assert _yf_ticker("068270", "KOSDAQ") == "068270.KQ"
    assert _yf_ticker("AAPL", "SP500") == "AAPL"
    assert _yf_ticker("MSFT", "NASDAQ") == "MSFT"
    assert _yf_ticker("005930.KS", "KOSPI") == "005930.KS"


def test_compute_regulatory_filing_lag():
    """Verify regulatory filing lag computation."""
    # KRX quarterly: 45 days
    kr_q = compute_regulatory_filing_lag("2026-03-31", "quarterly", is_krx=True)
    assert kr_q == "2026-05-15"

    # KRX annual (Dec): 90 days
    kr_a = compute_regulatory_filing_lag("2025-12-31", "annual", is_krx=True)
    assert kr_a == "2026-03-31"

    # SEC quarterly: 40 days
    sec_q = compute_regulatory_filing_lag("2026-03-31", "quarterly", is_krx=False)
    assert sec_q == "2026-05-10"

    # SEC annual: 60 days
    sec_a = compute_regulatory_filing_lag("2025-12-31", "annual", is_krx=False)
    assert sec_a == "2026-03-01"


def test_mock_fundamentals_network_shares_fallback():
    """
    Test shares outstanding fallback tiers:
    1. info sharesOutstanding is missing -> fast_info.shares
    2. fast_info.shares is missing -> balance sheet Ordinary Shares Number
    """
    mock_ticker = MagicMock()
    
    # Financials (Index is line items, columns are dates)
    fin_df = pd.DataFrame(
        {
            pd.to_datetime("2025-09-30"): [1000.0, 200.0, 150.0, 1.5],
            pd.to_datetime("2025-12-31"): [1200.0, 250.0, 180.0, 1.8],
        },
        index=["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"]
    )
    mock_ticker.quarterly_income_stmt = fin_df
    
    # Balance sheet with 10M shares and 50M equity
    bs_df = pd.DataFrame(
        {
            pd.to_datetime("2025-09-30"): [40_000_000.0, 10_000_000.0, 5_000_000.0, 12_000_000.0],
            pd.to_datetime("2025-12-31"): [50_000_000.0, 10_000_000.0, 6_000_000.0, 15_000_000.0],
        },
        index=["Total Stockholder Equity", "Ordinary Shares Number", "Total Debt", "Cash And Cash Equivalents"]
    )
    mock_ticker.quarterly_balance_sheet = bs_df
    mock_ticker.quarterly_cash_flow = pd.DataFrame()
    mock_ticker.info = {}  # Empty info!
    mock_ticker.fast_info = None  # None fast_info!

    with patch("yfinance.Ticker", return_value=mock_ticker):
        res = _fetch_fundamentals_network("TEST.KS")
        assert not res.empty
        assert len(res) == 2
        # Shares resolved from Balance Sheet
        assert res["shares_outstanding"].iloc[-1] == 10_000_000.0
        # BPS = 50M / 10M = 5.0
        assert abs(res["bps"].iloc[-1] - 5.0) < 1e-6
        assert res["book_value"].iloc[-1] == 50_000_000.0


def test_bank_financial_statement_handling():
    """
    Test bank statements where standard Operating Income is absent,
    falling back to Pretax Income or Net Income so the bank is not rejected as LOW_EARNINGS_QUALITY.
    """
    mock_ticker = MagicMock()
    
    # Bank Income Statement (No Operating Income line, only Operating Revenue and Pretax Income & Net Income)
    fin_df = pd.DataFrame(
        {
            pd.to_datetime("2025-12-31"): [50_000.0, 25_000.0, 20_000.0, 5.0]
        },
        index=["Operating Revenue", "Pretax Income", "Net Income", "Diluted EPS"]
    )
    mock_ticker.quarterly_income_stmt = fin_df
    
    bs_df = pd.DataFrame(
        {
            pd.to_datetime("2025-12-31"): [200_000.0, 2_000.0]
        },
        index=["Total Stockholder Equity", "Ordinary Shares Number"]
    )
    mock_ticker.quarterly_balance_sheet = bs_df
    mock_ticker.quarterly_cash_flow = pd.DataFrame()
    mock_ticker.info = {"sharesOutstanding": 2000, "regularMarketPrice": 80.0}
    mock_ticker.fast_info = MagicMock(shares=2000, last_price=80.0)

    with patch("yfinance.Ticker", return_value=mock_ticker):
        res = _fetch_fundamentals_network("JPM")
        assert not res.empty
        # Operating income resolved from Pretax Income
        assert res["operating_income"].iloc[-1] == 25_000.0
        assert res["net_income"].iloc[-1] == 20_000.0
        assert res["bps"].iloc[-1] == 100.0

        # Feed into RIM engine
        rim_engine = RIMValuationEngine(default_required_return=0.08)
        df_in = pd.DataFrame([{
            'symbol': 'JPM',
            'market': 'SP500',
            'Close': 80.0,
            'bps': 100.0,
            'roe': 0.10,
            'operating_income': 25000.0,
            'net_income': 20000.0,
            'book_value': 200000.0
        }])
        rim_res = rim_engine.compute_rim_scores(df_in)
        assert rim_res['rim_filter_reason'].iloc[0] == ''
        assert not np.isnan(rim_res['rim_score'].iloc[0])


def test_batch_fetch_and_store_fundamentals(tmp_path):
    """Test batch storage of fundamentals in SQLite DB."""
    db_path = str(tmp_path / "test_indicators.db")
    storage = MarketIndicatorStorage(db_path)

    mock_ticker = MagicMock()
    fin_df = pd.DataFrame(
        {
            pd.to_datetime("2025-12-31"): [1000.0, 200.0, 150.0, 1.5]
        },
        index=["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"]
    )
    mock_ticker.quarterly_income_stmt = fin_df
    bs_df = pd.DataFrame(
        {
            pd.to_datetime("2025-12-31"): [50_000.0, 10_000.0]
        },
        index=["Total Stockholder Equity", "Ordinary Shares Number"]
    )
    mock_ticker.quarterly_balance_sheet = bs_df
    mock_ticker.quarterly_cash_flow = pd.DataFrame()
    mock_ticker.info = {"sharesOutstanding": 10000}
    mock_ticker.fast_info = MagicMock(shares=10000, last_price=10.0)

    with patch("yfinance.Ticker", return_value=mock_ticker):
        symbols = ["SYM_A", "SYM_B", "SYM_C"]
        market_map = {"SYM_A": "KOSPI", "SYM_B": "KOSPI", "SYM_C": "SP500"}
        count = fetch_and_store_fundamentals_batch(symbols, market_map, storage, max_workers=2, force_refetch=True)
        assert count == 3

        # Verify DB contents
        df_db = storage.get_all_fundamentals(symbols)
        assert len(df_db) == 3
        assert set(df_db["symbol"]) == {"SYM_A", "SYM_B", "SYM_C"}
        assert (df_db["bps"] == 5.0).all()

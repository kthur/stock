"""Unit tests for DARTFundamentalFetcher (OpenDartReader integration) and zero-equity RIM fixes."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest

from src.data_layer.dart_fundamental_fetcher import DARTFundamentalFetcher, _clean_amount
from src.data_layer.earnings_data import fetch_fundamentals
from src.core.rim_valuation import RIMValuationEngine


def test_clean_amount():
    assert _clean_amount("1,000,000") == 1000000.0
    assert _clean_amount("-50,000") == -50000.0
    assert _clean_amount("-") == 0.0
    assert _clean_amount("") == 0.0
    assert _clean_amount(None) == 0.0
    assert _clean_amount(12345.67) == 12345.67
    assert _clean_amount("N/A") == 0.0


def test_dart_fundamental_fetcher_mock():
    # Create sample finstate DataFrame
    mock_df_annual = pd.DataFrame([
        {'account_nm': '자본총계', 'fs_div': 'CFS', 'thstrm_amount': '500,000,000,000'},
        {'account_nm': '당기순이익', 'fs_div': 'CFS', 'thstrm_amount': '50,000,000,000'},
        {'account_nm': '영업이익', 'fs_div': 'CFS', 'thstrm_amount': '60,000,000,000'},
        {'account_nm': '매출액', 'fs_div': 'CFS', 'thstrm_amount': '1,000,000,000,000'},
        {'account_nm': '부채총계', 'fs_div': 'CFS', 'thstrm_amount': '200,000,000,000'},
        {'account_nm': '현금및현금성자산', 'fs_div': 'CFS', 'thstrm_amount': '80,000,000,000'},
    ])

    mock_df_1q = pd.DataFrame([
        {'account_nm': '자본총계', 'fs_div': 'CFS', 'thstrm_amount': '520,000,000,000'},
        {'account_nm': '당기순이익', 'fs_div': 'CFS', 'thstrm_amount': '15,000,000,000'},
        {'account_nm': '영업이익', 'fs_div': 'CFS', 'thstrm_amount': '18,000,000,000'},
        {'account_nm': '매출액', 'fs_div': 'CFS', 'thstrm_amount': '260,000,000,000'},
        {'account_nm': '부채총계', 'fs_div': 'CFS', 'thstrm_amount': '210,000,000,000'},
        {'account_nm': '현금및현금성자산', 'fs_div': 'CFS', 'thstrm_amount': '85,000,000,000'},
    ])

    mock_reader = MagicMock()

    def _finstate_side_effect(corp, year, reprt_code):
        if reprt_code == "11011":
            return mock_df_annual
        elif reprt_code == "11013":
            return mock_df_1q
        return None

    mock_reader.finstate.side_effect = _finstate_side_effect

    mock_mapper = MagicMock()
    mock_mapper.get_corp_code.return_value = "00126380"

    fetcher = DARTFundamentalFetcher(api_key="test_key", corp_mapper=mock_mapper, dart_reader=mock_reader)
    shares = 10_000_000.0  # 1천만 주

    res = fetcher.fetch_fundamentals(symbol="005930", years_back=1, shares_outstanding=shares)

    assert res is not None
    assert not res.empty
    assert len(res) >= 2

    # Check BPS = book_value / shares
    assert 'bps' in res.columns
    assert 'book_value' in res.columns
    assert 'roe' not in res.columns  # Derived in pipeline / RIM engine
    assert 'operating_income' in res.columns
    assert 'net_income' in res.columns
    assert 'date_available' in res.columns

    # 1Q row check
    q1_row = res.iloc[-1]
    assert q1_row['book_value'] == 520_000_000_000.0
    assert q1_row['bps'] == 52_000.0  # 520,000,000,000 / 10,000,000
    assert q1_row['operating_income'] == 18_000_000_000.0
    assert q1_row['net_income'] == 15_000_000_000.0


def test_earnings_data_korean_stock_dart_routing():
    """Verify that fetch_fundamentals routes Korean stock symbols through DARTFundamentalFetcher first."""
    mock_dart_df = pd.DataFrame([{
        'revenue': 1000.0, 'operating_income': 100.0, 'net_income': 80.0,
        'eps': 8.0, 'shares_outstanding': 10.0, 'book_value': 800.0, 'bps': 80.0,
        'dividend_per_share': 0.0, 'date_available': '2026-05-15', 'period_type': 'quarterly'
    }], index=[pd.to_datetime('2026-03-31')])

    mock_dart_fetcher = MagicMock()
    mock_dart_fetcher.fetch_fundamentals.return_value = mock_dart_df

    with patch('src.data_layer.earnings_data._get_global_dart_fetcher', return_value=mock_dart_fetcher):
        # KOSDAQ stock: 247540
        res_kosdaq = fetch_fundamentals("247540", market="KOSDAQ")
        assert res_kosdaq is not None
        assert res_kosdaq['bps'].iloc[0] == 80.0
        mock_dart_fetcher.fetch_fundamentals.assert_called()

        # KOSPI stock: 005930
        res_kospi = fetch_fundamentals("005930", market="KOSPI")
        assert res_kospi is not None
        assert res_kospi['book_value'].iloc[0] == 800.0


def test_rim_valuation_zero_bps_and_negative_equity_distinction():
    """Verify that bps == 0.0 is treated as missing (allowing proxy anchor), while bps < 0 is capital impairment."""
    engine = RIMValuationEngine(default_required_return=0.08)

    df = pd.DataFrame([
        # 1. Genuine positive equity: normal RIM
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15, 'sma_200': 65000.0},
        # 2. Zero BPS (data missing): should NOT be capital impairment; should use PRICE_TREND_PROXY
        {'symbol': '035720', 'market': 'KOSDAQ', 'Close': 50000.0, 'bps': 0.0, 'roe': 0.10, 'sma_200': 48000.0},
        # 3. Strictly negative BPS (true capital impairment): should be CAPITAL_IMPAIRMENT
        {'symbol': '099990', 'market': 'KOSDAQ', 'Close': 1000.0, 'bps': -500.0, 'roe': -0.20, 'sma_200': 1200.0},
    ])

    res = engine.compute_rim_scores(df, allow_price_proxy=True).set_index('symbol')

    # Positive stock
    assert res.loc['005930', 'rim_filter_reason'] == ''
    assert not np.isnan(res.loc['005930', 'rim_score'])
    assert res.loc['005930', 'rim_score'] > 0

    # Zero BPS stock: price trend proxy activated
    assert res.loc['035720', 'rim_filter_reason'] == 'PRICE_TREND_PROXY'
    assert not np.isnan(res.loc['035720', 'intrinsic_value'])
    assert res.loc['035720', 'intrinsic_value'] > 0
    assert not np.isnan(res.loc['035720', 'rim_score'])

    # Negative BPS stock: capital impairment
    assert res.loc['099990', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert np.isnan(res.loc['099990', 'intrinsic_value'])
    assert np.isnan(res.loc['099990', 'rim_score'])

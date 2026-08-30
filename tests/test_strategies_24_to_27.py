"""
tests/test_strategies_24_to_27.py
Unit tests for Strategy Engines #24 through #27.
"""

import numpy as np
import pandas as pd

from trading_system.src.core.accruals_quality import AccrualsQualityEngine
from trading_system.src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from trading_system.src.core.valueup_catalyst import ValueUpCatalystEngine
from trading_system.src.core.trend_efficiency import TrendEfficiencyEngine


def test_accruals_quality_engine():
    """Test Strategy #24: Accruals Quality Anomaly Engine."""
    engine = AccrualsQualityEngine()
    symbols = ['005930', 'AAPL']
    
    fundamentals_df = pd.DataFrame([
        {'symbol': '005930', 'net_income': 100.0, 'operating_income': 120.0, 'revenue': 1000.0},
        {'symbol': 'AAPL', 'net_income': 200.0, 'operating_income': 150.0, 'revenue': 2000.0},
    ])
    
    res = engine.calculate_scores(symbols, fundamentals_df)
    assert isinstance(res, pd.DataFrame)
    assert 'symbol' in res.columns
    assert 'accruals_quality_score' in res.columns
    assert len(res) == 2
    for score in res['accruals_quality_score']:
        assert 0.0 <= score <= 1.0


def test_short_interest_squeeze_engine():
    """Test Strategy #25: Short Interest & Squeeze Engine."""
    engine = ShortInterestSqueezeEngine()
    symbols = ['GME', 'AMC']
    
    dates = pd.date_range('2026-01-01', periods=10)
    prices_dict = {
        'GME': pd.DataFrame({
            'Close': [10.0, 10.2, 10.5, 11.0, 11.8, 12.5, 13.2, 14.0, 15.0, 16.5],
            'Volume': [1000] * 10
        }, index=dates),
        'AMC': pd.DataFrame({
            'Close': [5.0, 5.0, 4.9, 4.8, 4.8, 4.7, 4.6, 4.5, 4.4, 4.3],
            'Volume': [500] * 10
        }, index=dates)
    }
    
    short_data_dict = {
        'GME': {'short_interest_ratio': 0.25, 'days_to_cover': 6.0},
        'AMC': {'short_interest_ratio': 0.05, 'days_to_cover': 1.0}
    }
    
    res = engine.calculate_scores(symbols, prices_dict, short_data_dict)
    assert isinstance(res, pd.DataFrame)
    assert 'symbol' in res.columns
    assert 'short_squeeze_score' in res.columns
    assert len(res) == 2
    
    gme_score = res[res['symbol'] == 'GME']['short_squeeze_score'].iloc[0]
    amc_score = res[res['symbol'] == 'AMC']['short_squeeze_score'].iloc[0]
    assert gme_score > amc_score


def test_valueup_catalyst_engine():
    """Test Strategy #26: Value-Up & Shareholder Yield Catalyst."""
    engine = ValueUpCatalystEngine()
    symbols = ['005930', '000660']
    
    fundamentals_df = pd.DataFrame([
        {'symbol': '005930', 'book_value': 80000.0, 'dividend_per_share': 1500.0, 'revenue': 100000.0},
        {'symbol': '000660', 'book_value': 30000.0, 'dividend_per_share': 500.0, 'revenue': 40000.0},
    ])
    
    prices_dict = {
        '005930': pd.DataFrame({'Close': [60000.0]}, index=pd.date_range('2026-01-01', periods=1)),
        '000660': pd.DataFrame({'Close': [100000.0]}, index=pd.date_range('2026-01-01', periods=1))
    }
    
    res = engine.calculate_scores(symbols, fundamentals_df, prices_dict)
    assert isinstance(res, pd.DataFrame)
    assert 'symbol' in res.columns
    assert 'valueup_score' in res.columns or 'valueup_catalyst_score' in res.columns
    assert len(res) == 2


def test_trend_efficiency_engine():
    """Test Strategy #27: Kaufman Trend Efficiency Engine."""
    engine = TrendEfficiencyEngine()
    symbols = ['TREND_HIGH', 'NOISY']
    
    dates = pd.date_range('2026-01-01', periods=30)
    prices_dict = {
        'TREND_HIGH': pd.DataFrame({'Close': np.linspace(100, 200, 30)}, index=dates),
        'NOISY': pd.DataFrame({'Close': 100 + 10 * np.sin(np.linspace(0, 10, 30))}, index=dates)
    }
    
    res = engine.calculate_scores(symbols, prices_dict)
    assert isinstance(res, pd.DataFrame)
    assert 'symbol' in res.columns
    assert 'trend_efficiency_score' in res.columns
    assert len(res) == 2
    
    high_score = res[res['symbol'] == 'TREND_HIGH']['trend_efficiency_score'].iloc[0]
    noisy_score = res[res['symbol'] == 'NOISY']['trend_efficiency_score'].iloc[0]
    assert high_score > noisy_score

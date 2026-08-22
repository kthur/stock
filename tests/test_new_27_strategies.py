"""
tests/test_new_27_strategies.py
Unit tests for Strategies #24-#27 (Accruals Quality, Short Interest Squeeze, Value-Up Catalyst, Trend Efficiency)
and 27-Strategy EnsembleScoringEngine integration.
"""

import sys
import os
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Ensure trading_system directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "trading_system"))

from src.core.accruals_quality import AccrualsQualityEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.valueup_catalyst import ValueUpCatalystEngine
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


def test_accruals_quality_engine():
    engine = AccrualsQualityEngine()
    symbols = ['005930', '000660', '035420']
    
    features_data = {
        '005930': pd.DataFrame([{'symbol': '005930', 'net_income': 1000, 'operating_cash_flow': 1200, 'total_assets': 10000}]),
        '000660': pd.DataFrame([{'symbol': '000660', 'net_income': 500, 'operating_cash_flow': 200, 'total_assets': 5000}]),
        '035420': pd.DataFrame([{'symbol': '035420', 'net_income': 300, 'operating_cash_flow': 300, 'total_assets': 3000}])
    }
    
    res = engine.calculate_scores(symbols, features_df=features_data)
    assert not res.empty
    assert 'symbol' in res.columns
    assert 'accruals_quality_score' in res.columns
    assert len(res) == 3
    assert (res['accruals_quality_score'] >= 0.0).all() and (res['accruals_quality_score'] <= 1.0).all()


def test_short_interest_squeeze_engine():
    engine = ShortInterestSqueezeEngine()
    symbols = ['005930', '000660']
    
    # Create price history
    dates = pd.date_range('2026-01-01', periods=30)
    prices_dict = {
        '005930': pd.DataFrame({'close': np.linspace(50000, 55000, 30), 'volume': np.random.randint(1000, 5000, 30)}, index=dates),
        '000660': pd.DataFrame({'close': np.linspace(100000, 95000, 30), 'volume': np.random.randint(1000, 5000, 30)}, index=dates)
    }
    
    res = engine.calculate_scores(symbols, prices_dict=prices_dict)
    assert not res.empty
    assert 'symbol' in res.columns
    assert 'short_squeeze_score' in res.columns
    assert len(res) == 2
    assert (res['short_squeeze_score'] >= 0.0).all() and (res['short_squeeze_score'] <= 1.0).all()


def test_valueup_catalyst_engine():
    engine = ValueUpCatalystEngine()
    symbols = ['005930', '000660']
    
    features_data = {
        '005930': pd.DataFrame([{'symbol': '005930', 'pbr': 0.6, 'bps': 80000, 'cash': 50000, 'market_cap': 300000, 'dividend_yield': 0.04}]),
        '000660': pd.DataFrame([{'symbol': '000660', 'pbr': 1.8, 'bps': 50000, 'cash': 10000, 'market_cap': 100000, 'dividend_yield': 0.01}])
    }
    
    res = engine.calculate_scores(symbols, features_df=features_data)
    assert not res.empty
    assert 'symbol' in res.columns
    assert 'valueup_catalyst_score' in res.columns
    assert len(res) == 2
    assert res.loc[res['symbol'] == '005930', 'valueup_catalyst_score'].values[0] > res.loc[res['symbol'] == '000660', 'valueup_catalyst_score'].values[0]


def test_trend_efficiency_engine():
    engine = TrendEfficiencyEngine()
    symbols = ['005930', '000660']
    
    dates = pd.date_range('2026-01-01', periods=30)
    prices_dict = {
        '005930': pd.DataFrame({'close': np.linspace(50000, 60000, 30)}, index=dates),  # Clean linear trend
        '000660': pd.DataFrame({'close': np.linspace(60000, 50000, 30)}, index=dates)   # Downtrend
    }
    
    res = engine.calculate_scores(symbols, prices_dict=prices_dict)
    assert not res.empty
    assert 'symbol' in res.columns
    assert res.loc[res['symbol'] == '005930', 'trend_efficiency_score'].iloc[0] > 0.50
    assert res.loc[res['symbol'] == '000660', 'trend_efficiency_score'].iloc[0] <= 0.50
    assert res.loc[res['symbol'] == '005930', 'trend_efficiency_score'].iloc[0] > res.loc[res['symbol'] == '000660', 'trend_efficiency_score'].iloc[0]


def test_27_strategy_ensemble_integration():
    scorer = EnsembleScoringEngine()
    symbols = ['005930', '000660']
    
    reg_df = pd.DataFrame({'symbol': symbols, 'expected_return_20d': [0.05, 0.02]})
    s_df = pd.DataFrame({'symbol': symbols, 'surge_prob_20d': [0.6, 0.3]})
    ll_df = pd.DataFrame({'symbol': symbols, 'lead_lag_score': [0.7, 0.4]})
    v_df = pd.DataFrame({'symbol': symbols, 'vcp_ml_score': [0.8, 0.5]})
    
    aq_df = pd.DataFrame({'symbol': symbols, 'accruals_quality_score': [0.8, 0.4]})
    sq_df = pd.DataFrame({'symbol': symbols, 'short_squeeze_score': [0.7, 0.3]})
    vu_df = pd.DataFrame({'symbol': symbols, 'valueup_catalyst_score': [0.9, 0.2]})
    te_df = pd.DataFrame({'symbol': symbols, 'trend_efficiency_score': [0.85, 0.35]})
    
    ens = scorer.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=s_df,
        lead_lag_df=ll_df,
        vcp_ml_df=v_df,
        accruals_quality_df=aq_df,
        short_squeeze_df=sq_df,
        valueup_catalyst_df=vu_df,
        trend_efficiency_df=te_df
    )
    
    assert not ens.empty
    assert 'symbol' in ens.columns
    assert 'ensemble_score' in ens.columns
    assert len(ens) == 2
    assert (ens['ensemble_score'] >= 0.0).all() and (ens['ensemble_score'] <= 1.0).all()


def test_coverage_analyzer_27_strategies():
    analyzer = StrategyCoverageAnalyzer()
    assert len(analyzer.STRATEGIES) >= 27
    assert 'accruals_quality' in analyzer.STRATEGIES
    assert 'short_squeeze' in analyzer.STRATEGIES
    assert 'valueup_catalyst' in analyzer.STRATEGIES
    assert 'trend_efficiency' in analyzer.STRATEGIES

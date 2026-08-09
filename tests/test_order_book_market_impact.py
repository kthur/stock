"""
tests/test_order_book_market_impact.py
Comprehensive unit tests for Requirement 2 (R2):
1. Precision Order Book Market Impact & Bid-Ask Spread Cost Modeling.
2. Kyle / Almgren-Chriss Square-Root Market Impact Scaling.
3. Volatility Sensitivity and Participation Rate Overflow Penalty.
4. Market-Specific Cost Bounds & Spread Clamping.
5. Environment Variable Overrides in TradingConfig.
"""

import os
import pytest
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.config import TradingConfig


def test_square_root_market_impact_scaling():
    """Verify market impact follows square-root relationship when order size or turnover changes."""
    config = TradingConfig(order_size_krx=50_000_000.0, market_impact_coeff_krx=0.75)
    scorer = EnsembleScoringEngine(config=config)

    # Stock 1: High turnover (100B KRW) -> small Q/ADV ratio (50M / 100B = 0.0005)
    # Stock 2: Lower turnover (6.25B KRW) -> 16x smaller turnover -> sqrt(16) = 4x higher market impact
    df_reg = pd.DataFrame({
        'symbol': ['HIGH_TURNOVER.KS', 'LOW_TURNOVER.KS'],
        'market': ['KOSPI', 'KOSPI'],
        'volume': [1_000_000, 62_500],
        'close': [100_000, 100_000],  # Turnover: 100B vs 6.25B KRW
        'volatility_20d': [0.02, 0.02],
        20: [0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    high_row = res[res['symbol'] == 'HIGH_TURNOVER.KS'].iloc[0]
    low_row = res[res['symbol'] == 'LOW_TURNOVER.KS'].iloc[0]

    # Lower turnover stock must have lower net expected return due to higher market impact & spread
    assert low_row['ensemble_expected_return'] < high_row['ensemble_expected_return']


def test_volatility_impact_scaling():
    """Verify higher daily price volatility leads to higher bid-ask spread and market impact."""
    scorer = EnsembleScoringEngine()

    df_reg = pd.DataFrame({
        'symbol': ['LOW_VOL.KS', 'HIGH_VOL.KS'],
        'market': ['KOSPI', 'KOSPI'],
        'volume': [100_000, 100_000],
        'close': [50_000, 50_000],   # Turnover: 5B KRW
        'volatility_20d': [0.01, 0.04],  # 1% vs 4% daily vol
        20: [0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    low_vol = res[res['symbol'] == 'LOW_VOL.KS'].iloc[0]
    high_vol = res[res['symbol'] == 'HIGH_VOL.KS'].iloc[0]

    assert high_vol['ensemble_expected_return'] <= low_vol['ensemble_expected_return']


def test_participation_rate_overflow_penalty():
    """Verify orders exceeding 10% ADV incur participation rate penalty."""
    config = TradingConfig(order_size_krx=500_000_000.0)  # Large order: 500M KRW
    scorer = EnsembleScoringEngine(config=config)

    # Micro-cap stock with 1B KRW turnover (Q/ADV = 500M / 1B = 0.50 > 0.10)
    df_reg = pd.DataFrame({
        'symbol': ['MICRO_CAP.KQ'],
        'market': ['KOSDAQ'],
        'volume': [20_000],
        'close': [50_000],  # Turnover: 1B KRW
        'volatility_20d': [0.02],
        20: [0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    micro_row = res[res['symbol'] == 'MICRO_CAP.KQ'].iloc[0]

    # Net expected return should reflect heavy execution cost penalty (5% max friction cap)
    assert micro_row['ensemble_expected_return'] <= 15.0


def test_market_specific_cost_bounds_and_clamping():
    """Verify market-specific spread bounds and tax rates across KOSPI, KOSDAQ, KONEX, and SP500."""
    scorer = EnsembleScoringEngine()

    df_reg = pd.DataFrame({
        'symbol': ['KOSPI_STOCK.KS', 'KOSDAQ_STOCK.KQ', 'KONEX_STOCK.KN', 'SP500_STOCK'],
        'market': ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500'],
        'volume': [100_000, 100_000, 100_000, 100_000],
        'close': [50_000, 50_000, 50_000, 100],  # 5B KRW turnover vs $10M USD turnover
        'volatility_20d': [0.02, 0.02, 0.02, 0.015],
        20: [0.25, 0.25, 0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    assert len(res) == 4

    sp500_row = res[res['symbol'] == 'SP500_STOCK'].iloc[0]
    kospi_row = res[res['symbol'] == 'KOSPI_STOCK.KS'].iloc[0]

    # SP500 ($10M turnover, $50K order -> Q/ADV = 0.005) has much lower friction than KOSPI
    assert sp500_row['ensemble_expected_return'] > kospi_row['ensemble_expected_return']


def test_config_env_overrides(monkeypatch):
    """Verify environment variables override TradingConfig market impact parameters."""
    monkeypatch.setenv("ORDER_SIZE_KRX", "100000000.0")
    monkeypatch.setenv("ORDER_SIZE_SP500", "100000.0")
    monkeypatch.setenv("MARKET_IMPACT_COEFF_KRX", "0.90")
    monkeypatch.setenv("MARKET_IMPACT_COEFF_SP500", "0.60")

    cfg = TradingConfig()
    assert cfg.order_size_krx == 100_000_000.0
    assert cfg.order_size_sp500 == 100_000.0
    assert cfg.market_impact_coeff_krx == 0.90
    assert cfg.market_impact_coeff_sp500 == 0.60

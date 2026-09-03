import os
import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.analysis.portfolio_optimizer import calculate_black_litterman_weights


def test_allocator_step4_price_robustness():
    allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
    dates = pd.date_range('2026-01-01', periods=30, freq='B')
    
    prices_dict = {
        '005930': pd.DataFrame({
            'Open': [74000.0] * 30,
            'High': [76000.0] * 30,
            'Low': [73000.0] * 30,
            'Close': [75000.0] * 30,
            'Volume': [10000000.0] * 30,
        }, index=dates),
        '000660': pd.DataFrame({
            'Open': [150000.0] * 30,
            'High': [155000.0] * 30,
            'Low': [148000.0] * 30,
            'Close': [152000.0] * 30,
            'Volume': [5000000.0] * 30,
        }, index=dates),
    }

    df_candidates = pd.DataFrame([
        {'symbol': '005930.KS', 'market': 'KOSPI', 'close': 75000.0, 'score': 0.85, 'volume': 10000000.0},
        {'symbol': '000660.KS', 'market': 'KOSPI', 'close': 152000.0, 'score': 0.75, 'volume': 5000000.0},
    ])

    result_df = allocator.allocate(
        predictions_df=df_candidates,
        prices_dict=prices_dict,
        total_portfolio_value=10000000.0,
        base_currency='KRW',
        top_n=2
    )

    assert not result_df.empty
    for row in result_df.itertuples():
        assert row.shares < 1000, f'Symbol {row.symbol} calculated {row.shares} shares!'
        assert row.shares > 0, f'Symbol {row.symbol} has 0 shares!'


def test_alpha_preservation_high_conviction():
    scorer = EnsembleScoringEngine()
    high_alpha_df = pd.DataFrame([
        {'symbol': f'STOCK_{i}', 'market': 'KOSPI', 'ensemble_score': score, 'adv': 50000000000.0, 'volatility_20d': 0.02, 'close': 50000.0}
        for i, score in enumerate([0.85, 0.80, 0.78, 0.75, 0.72, 0.70])
    ])

    merged = scorer.combine_predictions(high_alpha_df, weights=None, regime='BULL_LOW_VOL')
    
    assert 'ensemble_expected_return' in merged.columns
    for _, row in merged.iterrows():
        assert row['ensemble_expected_return'] > 0.0, (
            f'Symbol {row["symbol"]} with high score {row["ensemble_score"]} was crushed to {row["ensemble_expected_return"]}!'
        )


def test_asymmetric_atr_risk_reward_ratio(tmp_path):
    db_path = str(tmp_path / 'trade_logs_rr.db')
    oms = ExecutionOMSEngine(db_path=db_path, lot_size_krx=1)

    top_predictions = [
        {
            'symbol': '005930',
            'name': '삼성전자',
            'market': 'KOSPI',
            'close_price': 70000.0,
            'target_price': 70000.0,
            'volatility_20d': 0.025,
            'expected_return': 12.0,
            'ensemble_expected_return': 12.0,
            'adv': 500000000000.0
        },
        {
            'symbol': 'NVDA',
            'name': 'NVIDIA',
            'market': 'NASDAQ',
            'close_price': 120.0,
            'target_price': 120.0,
            'volatility_20d': 0.045,
            'expected_return': 18.0,
            'ensemble_expected_return': 18.0,
            'adv': 10000000000.0
        }
    ]
    weights = {'005930': 0.50, 'NVDA': 0.50}

    plans = oms.generate_order_plan(
        top_predictions=top_predictions,
        portfolio_weights=weights,
        total_capital=100000000.0
    )

    assert len(plans) == 2
    for p in plans:
        tp = float(p.get('target_take_profit', p.get('take_profit_price')))
        sl = float(p.get('target_stop_loss', p.get('stop_loss_price')))
        entry = float(p['target_price'])
        
        upside = tp - entry
        downside = entry - sl
        
        assert downside > 0, 'Stop loss must be below entry price'
        assert upside > 0, 'Take profit must be above entry price'
        
        rr_ratio = upside / downside
        assert rr_ratio >= 2.49, f'Risk-Reward ratio {rr_ratio:.2f} for {p["symbol"]} is less than 2.5:1!'


def test_3tier_scale_out_profit_lock_enabled_by_default(tmp_path):
    db_path = str(tmp_path / 'trade_logs_tp.db')
    oms = ExecutionOMSEngine(db_path=db_path)

    current_holdings = {
        'WINNER_T1': {
            'quantity': 100,
            'entry_price': 10000.0,
            'current_price': 10900.0,
            'days_held': 5,
            'volatility_20d': 0.02,
            'current_score': 0.70
        }
    }

    plans = oms.calculate_trailing_stop_plan(current_holdings, prices_dict=None)

    assert len(plans) >= 1
    t1_plan = next((p for p in plans if p['symbol'] == 'WINNER_T1'), None)
    assert t1_plan is not None
    assert t1_plan['reason'] == 'TIER_1_PROFIT_LOCK'
    assert t1_plan['quantity'] == 30
    assert t1_plan['action'] == 'SELL'


def test_black_litterman_native_bounds_allocation():
    cov = np.array([
        [0.04, 0.01, 0.01],
        [0.01, 0.04, 0.01],
        [0.01, 0.01, 0.04]
    ])
    pred_rets = np.array([0.50, 0.20, 0.15])
    symbols = ['SYM_A', 'SYM_B', 'SYM_C']
    
    max_w = 0.40
    weights = calculate_black_litterman_weights(
        cov_matrix=cov,
        predicted_returns=pred_rets,
        symbols=symbols,
        max_single_stock_weight=max_w
    )

    assert np.isclose(np.sum(weights), 1.0, atol=1e-4)
    assert weights[0] <= max_w + 1e-4
    assert weights[1] > 0.25


def test_covariance_matrix_pairwise_no_distortion():
    allocator = UnifiedPortfolioAllocator()
    dates = pd.date_range('2026-01-01', periods=30, freq='B')
    
    prices_dict = {
        'SYM_1': pd.DataFrame({'Close': np.linspace(100, 120, 30)}, index=dates),
        'SYM_2': pd.DataFrame({'Close': np.linspace(50, 60, 30)}, index=dates),
    }

    returns_df, valid_symbols = allocator.compute_returns_matrix(
        symbols=['SYM_1', 'SYM_2'],
        prices_dict=prices_dict,
        lookback=30
    )

    assert valid_symbols == ['SYM_1', 'SYM_2']
    assert not returns_df.empty
    assert len(returns_df) >= 25
    assert np.all(np.isfinite(returns_df.values))

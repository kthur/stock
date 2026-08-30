"""
Tests for Return & Alpha Maximization Improvements:
1. Markowitz-Kelly Dynamic Sharpe Sizing in PortfolioOptimizer.
2. Dynamic Alpha Cutoff Hurdle Rate in EnsembleScoringEngine.
3. Regime-Adaptive Momentum Turbo in EnsembleScoringEngine.
4. Chandelier ATR Dynamic Trailing Stop & Profit Runner in ExecutionOMSEngine.
5. Opening Gap Overheat & Dip-Buying Gating in ExecutionOMSEngine.
"""

import numpy as np
import pandas as pd
from src.risk.portfolio_optimizer import PortfolioOptimizer
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.execution.oms_engine import ExecutionOMSEngine


def test_markowitz_kelly_sharpe_sizing():
    optimizer = PortfolioOptimizer(default_max_weight=0.20)
    
    np.random.seed(42)
    returns_df = pd.DataFrame({
        'HIGH_ALPHA': np.random.normal(0.002, 0.025, 60),  # High expected return, moderate vol
        'LOW_ALPHA': np.random.normal(0.0002, 0.010, 60),  # Low expected return, low vol
        'NEUTRAL': np.random.normal(0.0005, 0.015, 60)
    })
    
    expected_returns = {
        'HIGH_ALPHA': 25.0, # +25% super alpha
        'LOW_ALPHA': 2.0,   # +2% low alpha
        'NEUTRAL': 5.0
    }
    
    weights = optimizer.optimize_return_tilted_risk_parity(
        returns_df,
        expected_returns=expected_returns,
        tilt_exponent=1.5
    )
    
    assert weights['HIGH_ALPHA'] > weights['LOW_ALPHA']
    # Super-alpha asset should receive substantial allocation (> 22%)
    assert weights['HIGH_ALPHA'] > 0.22
    assert np.isclose(sum(weights.values()), 1.0)


def test_dynamic_alpha_hurdle_gating():
    scorer = EnsembleScoringEngine()
    
    # Create 20 candidates where top 5 are super-alpha and ranks 6-20 have low returns
    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(20)],
        'market': ['KOSPI'] * 20,
        'ensemble_score': [0.90 - i * 0.03 for i in range(20)],
        'volatility_20d': [0.02] * 20,
        'volume': [1000000.0] * 20,
        'close': [50000.0] * 20
    })
    
    combined = scorer.combine_predictions(df, regime='BULL_LOW_VOL')
    # portfolio_weight should be allocated only to the top high-conviction hurdle winners
    non_zero_weights = combined[combined['portfolio_weight'] > 0.0]
    
    assert 5 <= len(non_zero_weights) <= 12
    assert non_zero_weights['symbol'].iloc[0] == 'SYM_0'


def test_regime_adaptive_momentum_turbo():
    scorer = EnsembleScoringEngine()
    
    sharpes = {
        'surge': 1.2,
        'vcp_ml': 1.3,
        'mq_factor': 1.1,
        'stat_arb': 1.2,
        'vol_target': 1.0
    }
    
    # In Bull regime, momentum turbo accelerates surge/vcp_ml
    w_bull = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
    w_sideways = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')
    
    assert w_bull['surge'] > w_sideways['surge']
    assert w_bull['vcp_ml'] > w_sideways['vcp_ml']


def test_chandelier_trailing_stop_profit_lock(tmp_path):
    db_path = str(tmp_path / "trade_logs_test.db")
    oms = ExecutionOMSEngine(db_path=db_path)
    
    current_holdings = {
        "WINNER": {
            "quantity": 100,
            "entry_price": 100.0,
            "current_price": 120.0 # +20% gain, but dropped from high of 135
        },
        "LOSER": {
            "quantity": 100,
            "entry_price": 100.0,
            "current_price": 92.0 # -8% drop
        }
    }
    
    # Price history with a previous high of 135 for WINNER
    prices_dict = {
        "WINNER": pd.DataFrame({
            "High": [100.0, 110.0, 125.0, 135.0, 130.0, 120.0] * 3,
            "Low": [98.0, 108.0, 120.0, 130.0, 125.0, 118.0] * 3,
            "Close": [100.0, 110.0, 125.0, 135.0, 128.0, 120.0] * 3
        }),
        "LOSER": pd.DataFrame({
            "High": [100.0, 98.0, 96.0, 94.0, 93.0, 92.0] * 3,
            "Low": [98.0, 96.0, 94.0, 92.0, 91.0, 90.0] * 3,
            "Close": [100.0, 97.0, 95.0, 93.0, 92.0, 92.0] * 3
        })
    }
    
    plans = oms.calculate_trailing_stop_plan(current_holdings, prices_dict=prices_dict)
    
    assert len(plans) >= 1
    reasons = [p["reason"] for p in plans]
    assert "CHANDELIER_TRAILING_PROFIT" in reasons or "ATR_STOP_LOSS" in reasons


def test_opening_gap_overheat_dip_buying(tmp_path):
    db_path = str(tmp_path / "trade_logs_test.db")
    oms = ExecutionOMSEngine(db_path=db_path)
    
    # Candidate with +7% overheated opening gap
    top_preds = [
        {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "change_pct": 7.0, # +7% opening gap
            "adv": 500_000_000_000.0
        }
    ]
    weights = {"005930": 0.10}
    
    plans = oms.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100_000_000.0,
        crisis_level="NORMAL"
    )
    
    assert len(plans) == 1
    assert plans[0]["execution_strategy"] == "DIP_LIMIT"
    # Target price should be discounted by 1.5% from raw target price
    assert plans[0]["target_price"] < 70000.0

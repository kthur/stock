"""
Tests for Phase 3 & Phase 4 Institutional Enhancements:
1. MarketRegimeDetector transition probabilities and latent state estimation.
2. PortfolioAllocator Clayton Copula asymmetric lower-tail covariance stress.
3. ExecutionOMSEngine Gate 7.4 Dynamic Gap Filter and DYNAMIC_VWAP execution strategy.
"""

import numpy as np
import pandas as pd
from src.analysis.regime_detector import MarketRegimeDetector
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine


def test_regime_transition_probabilities():
    detector = MarketRegimeDetector()
    
    # Fast VIX shock test
    df_shock = pd.DataFrame({'vix_change': [35.0], 'sp500_change': [-3.5]})
    res = detector.predict_regime_transition_probabilities(df_shock)
    assert res['bear_shock_risk'] is True
    assert res['p_bear'] >= 0.70

    # Normal market test
    df_normal = pd.DataFrame({'vix_change': [15.0], 'sp500_change': [0.5]})
    res_norm = detector.predict_regime_transition_probabilities(df_normal)
    assert res_norm['bear_shock_risk'] is False
    assert np.isclose(res_norm['p_bear'] + res_norm['p_sideways'] + res_norm['p_bull'], 1.0)


def test_clayton_copula_tail_stress_cov():
    allocator = PortfolioAllocator()
    
    np.random.seed(42)
    N_days, K_assets = 100, 4
    # Simulate return matrix with occasional joint market down-moves
    returns = np.random.normal(0.0005, 0.015, (N_days, K_assets))
    # Inject 10 extreme downside crisis days
    returns[:10] -= 0.05

    base_cov = np.cov(returns, rowvar=False)
    stressed_cov = allocator.compute_tail_stress_cov(returns, base_cov, tail_quantile=0.15, stress_weight=0.30, use_clayton_copula=True)

    assert stressed_cov.shape == base_cov.shape
    assert np.all(np.isfinite(stressed_cov))
    # Stressed covariance diagonal should be positive
    assert np.all(np.diag(stressed_cov) > 0)


def test_oms_gate_gap_filter_and_vwap_routing(tmp_path):
    db_file = str(tmp_path / "trade_logs_test.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    predictions = [
        {
            "symbol": "AAPL",
            "name": "Apple",
            "market": "SP500",
            "action": "BUY",
            "close_price": 150.0,
            "target_price": 150.0,
            "change_pct": 0.01,
            "volatility_20d": 0.02,
            "adv": 50_000_000.0,  # Small ADV -> High participation ratio -> DYNAMIC_VWAP
        },
        {
            "symbol": "CRASH",
            "name": "Crashing Stock",
            "market": "SP500",
            "action": "BUY",
            "close_price": 50.0,
            "target_price": 50.0,
            "change_pct": -0.10,  # -10% opening gap vs 2% vol -> -5 sigma -> Should be blocked by Gate 7.4
            "volatility_20d": 0.02,
            "adv": 500_000_000.0,
        }
    ]
    weights = {"AAPL": 0.10, "CRASH": 0.10}

    plans = oms.generate_order_plan(
        top_predictions=predictions,
        portfolio_weights=weights,
        total_capital=100_000_000.0
    )

    symbols_in_plans = [p['symbol'] for p in plans]
    assert "AAPL" in symbols_in_plans
    assert "CRASH" not in symbols_in_plans, "Toxic gap crash stock should be filtered by Gate 7.4"

    aapl_plan = next(p for p in plans if p['symbol'] == "AAPL")
    assert aapl_plan['execution_strategy'] == "DYNAMIC_VWAP"
    assert aapl_plan['slice_count'] >= 3

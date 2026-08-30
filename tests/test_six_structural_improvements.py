"""
Tests for 6 Major Institutional Upgrades:
1. Dynamic Countercyclical ERP in RIM Valuation (Crisis Value Trap Prevention).
2. State-Space Kalman Filter Dynamic Cointegration & Structural Break Detection in Stat-Arb.
3. Asymmetric Sell LOB Thinning Market Impact in PortfolioAllocator.
4. Institutional AUM Capacity Congestion Penalty (>5% ADV).
5. Synthetic Beta Inverse Hedge ETF Order Plan Generation in OMS Engine.
6. Multi-Frequency Alpha Tier Decomposition & Fast Alpha Intraday Flag in EnsembleScorer.
"""

import numpy as np
import pandas as pd
from src.core.rim_valuation import RIMValuationEngine
from src.core.stat_arb import StatisticalArbitrageEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_dynamic_countercyclical_erp():
    rim = RIMValuationEngine()

    # Calm market (VIX = 15, credit spread = 2.5) -> Normal ERP
    r_e_calm = rim.derive_required_return(market="KOSPI", us10y_yield=4.0, vix_val=15.0, credit_spread=2.5)

    # Crisis market (VIX = 35, credit spread = 6.0) -> Expanded countercyclical ERP
    r_e_crisis = rim.derive_required_return(market="KOSPI", us10y_yield=4.0, vix_val=35.0, credit_spread=6.0)

    assert r_e_crisis > r_e_calm, f"Crisis r_e ({r_e_crisis:.4f}) must be higher than calm r_e ({r_e_calm:.4f})"
    assert r_e_crisis >= 0.12, "Crisis required return should expand to >= 12% to prevent Value Trap"


def test_kalman_dynamic_cointegration_and_break():
    stat_arb = StatisticalArbitrageEngine()

    np.random.seed(42)
    N = 100
    x = np.cumsum(np.random.normal(0, 1, N)) + 50.0
    # True relationship: y = 2.0 * x + noise
    y = 2.0 * x + np.random.normal(0, 0.5, N)

    res = stat_arb.estimate_kalman_dynamic_hedge_ratio(y, x)
    assert np.isclose(res['beta_t'], 2.0, atol=0.20)
    assert res['is_structural_break'] is False

    # Inject sudden massive structural break at end
    y_break = y.copy()
    y_break[-1] += 50.0  # Massive 50.0 jump
    res_break = stat_arb.estimate_kalman_dynamic_hedge_ratio(y_break, x)
    assert res_break['is_structural_break'] is True


def test_asymmetric_sell_lob_thinning():
    allocator = PortfolioAllocator()

    # Buy order in normal volatility
    cost_buy = allocator.estimate_transaction_cost_rate(
        symbol="005930",
        market="KOSPI",
        target_weight=0.05,
        portfolio_value=100_000_000.0,
        volatility_20d=0.035,
        adv=10_000_000_000.0,
        is_sell=False
    )

    # Sell order in severe panic volatility (LOB thinning)
    cost_sell = allocator.estimate_transaction_cost_rate(
        symbol="005930",
        market="KOSPI",
        target_weight=0.05,
        portfolio_value=100_000_000.0,
        volatility_20d=0.035,
        adv=10_000_000_000.0,
        is_sell=True
    )

    assert cost_sell > cost_buy, "Panic sell cost must exceed buy cost due to STT tax and LOB thinning"


def test_aum_capacity_congestion_penalty():
    allocator = PortfolioAllocator()

    # Small order (1% of ADV) -> No congestion penalty
    cost_small = allocator.estimate_transaction_cost_rate(
        symbol="SMALLCAP",
        market="KOSPI",
        target_weight=0.01,
        portfolio_value=100_000_000.0,  # 1M KRW
        volatility_20d=0.020,
        adv=100_000_000.0,  # Participation = 1%
        is_sell=False
    )

    # Large order (8% of ADV) -> Triggers >5% ADV Capacity Penalty
    cost_large = allocator.estimate_transaction_cost_rate(
        symbol="SMALLCAP",
        market="KOSPI",
        target_weight=0.08,
        portfolio_value=100_000_000.0,  # 8M KRW
        volatility_20d=0.020,
        adv=100_000_000.0,  # Participation = 8%
        is_sell=False
    )

    assert cost_large > cost_small * 2.0, "High participation (>5% ADV) must trigger non-linear capacity penalty"


def test_oms_synthetic_beta_hedge_order_generation(tmp_path):
    db_file = str(tmp_path / "trade_logs_hedge_test.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    predictions = [
        {
            "symbol": "005930",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "change_pct": 0.005,
            "volatility_20d": 0.020,
            "adv": 500_000_000_000.0,
        }
    ]
    weights = {"005930": 0.20}

    # Generate order plans under BEAR_HIGH_VOL regime
    plans = oms.generate_order_plan(
        top_predictions=predictions,
        portfolio_weights=weights,
        total_capital=100_000_000.0,
        crisis_level="WATCH",
        regime_label="BEAR_HIGH_VOL"
    )

    hedge_plans = [p for p in plans if "HEDGE" in p.get('action', '') or "HEDGE" in p.get('status', '')]
    assert len(hedge_plans) >= 1, "In BEAR_HIGH_VOL regime, an Inverse Hedge order plan must be automatically generated"
    assert hedge_plans[0]['symbol'] in ['252670.KS', '114800.KS', '114800', '252670']


def test_ensemble_multi_frequency_alpha_decoupling():
    scorer = EnsembleScoringEngine()

    df_sample = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT'],
        'market': ['SP500', 'SP500'],
        'rim_score': [0.85, 0.90],             # Slow
        'accruals_quality_score': [0.80, 0.75], # Slow
        'vcp_ml_score': [0.70, 0.65],           # Medium
        'microstructure_score': [0.95, 0.40]    # Fast
    })

    combined = scorer.combine_predictions(df_sample)
    assert 'slow_alpha_score' in combined.columns
    assert 'medium_alpha_score' in combined.columns
    assert 'fast_alpha_score' in combined.columns
    assert 'fast_alpha_intraday_eligible' in combined.columns
    assert bool(combined.loc[combined['symbol'] == 'AAPL', 'fast_alpha_intraday_eligible'].iloc[0]) is True

"""
tests/test_critical_bugs.py
Unit tests verifying Phase 6-A critical bug fixes.
"""

import math
import pandas as pd

from trading_system.src.core.llm_sentiment_engine import DARTSECSentimentEngine
from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
from trading_system.src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
from trading_system.src.risk.microstructure import MicrostructureCostModel
from trading_system.src.realtime.trade_executor import TradeExecutor


def test_bug_a2_sentiment_returns_nan_on_missing_text():
    """Bug A-2: Missing filing text must return NaN, not fake positive sentiment."""
    engine = DARTSECSentimentEngine()
    universe = pd.DataFrame([
        {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
        {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"},
    ])
    res_df = engine.compute_scores(universe, filings_map={})
    assert len(res_df) == 2
    assert res_df["sentiment_score"].isna().all(), "Missing text should produce NaNs for sentiment_score"


def test_bug_a3_factor_neutralizer_deactivates_without_random():
    """Bug A-3: Missing required factors should return NaNs (deactivate) deterministically without random data."""
    engine = MultiFactorNeutralizerEngine()
    universe = pd.DataFrame([
        {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
        {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"},
    ])
    res_df1 = engine.compute_scores(universe)
    res_df2 = engine.compute_scores(universe)
    assert res_df1["neutralized_score"].isna().all()
    assert res_df2["neutralized_score"].isna().all()


def test_bug_a4_delta_beta_hedge_math():
    """Bug A-4: Verify mathematical correctness of hedge weight calculation."""
    engine = DeltaBetaHedgeEngine()
    weights = {"005930.KS": 0.50, "000660.KS": 0.50}
    betas = {"005930.KS": 1.0, "000660.KS": 1.0}

    # port_beta = 1.0, target_beta = 0.0, inverse_beta = -2.0 (2X inverse ETF)
    # Correct formula: W_h = (1.0 - 0.0) / (1.0 - (-2.0)) = 1/3 = 0.33333...
    res = engine.calculate_optimal_hedge_allocation(
        portfolio_weights=weights,
        symbol_betas=betas,
        crisis_level="SEVERE",
        regime="BEAR_HIGH_VOL",
    )
    expected_wh = 1.0 / 3.0
    assert math.isclose(res["hedge_weight"], expected_wh, abs_tol=1e-3)
    # Check net beta after hedge allocation: (1 - Wh)*1.0 + Wh*(-2.0) = 0.0
    wh = res["hedge_weight"]
    net_beta = (1.0 - wh) * 1.0 + wh * (-2.0)
    assert math.isclose(net_beta, 0.0, abs_tol=1e-3)


def test_bug_a5_microstructure_stt_and_daily_vol():
    """Bug A-5: Verify separate KOSPI/KOSDAQ STT rate and daily volatility scaling."""
    model = MicrostructureCostModel()
    assert math.isclose(model.get_tax_fee_rate("KOSPI", is_sell=True), 0.0018, abs_tol=1e-5)
    assert math.isclose(model.get_tax_fee_rate("KOSDAQ", is_sell=True), 0.0021, abs_tol=1e-5)
    assert math.isclose(model.get_tax_fee_rate("SP500", is_sell=True), 0.0000778, abs_tol=1e-6)

    # Market impact should use daily vol volatility / sqrt(252)
    impact = model.calculate_market_impact(order_amount=10000.0, adv=1000000.0, volatility=0.20)
    daily_vol = 0.20 / math.sqrt(252.0)
    expected_impact = model.cfg.market_impact_gamma * daily_vol * math.sqrt(10000.0 / 1000000.0)
    assert math.isclose(impact, expected_impact, abs_tol=1e-5)
    assert impact < 0.01, f"Impact cost should be reasonable (< 1%), got {impact}"


def test_bug_a6_trade_executor_lot_size_and_cap():
    """Bug A-6: Verify lot size is 1 share and max order cap is never exceeded."""
    executor = TradeExecutor(dry_run=True, max_order_value_krw=5_000_000.0, lot_size_krx=1)
    assert executor.lot_size_krx == 1

    # High priced stock (1,000,000 KRW/share). max_order_value_krw = 5,000,000 KRW -> max 5 shares.
    res = executor.execute(
        symbol="068270",
        market="KOSPI",
        action="BUY",
        quantity=10,
        price=1_000_000.0,
    )
    assert res.executed is True
    assert res.mode == 'dry_run'
    assert res.quantity == 5
    assert res.quantity * 1_000_000.0 <= 5_000_000.0

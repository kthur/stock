"""
Unit Tests for ExecutionOMSEngine / OrderManager (V6-25, V6-26, V6-27, V6-28)
"""
import math
import pytest
import numpy as np
from src.execution.oms_engine import ExecutionOMSEngine, OMSEngine, AlmgrenChrissScheduler
from src.execution.order_manager import ExecutionOMSEngine as OMSEngineAlias


def test_v6_25_currency_denominator_normalization_us_equities():
    """
    V6-25: Verify US equities use effective_target_amount = target_amount / fx_rate.
    5,000,000 KRW at 1,350 KRW/USD is ~$3,703.70 USD.
    For AAPL ($150.00), raw_quantity should be ~24 shares, NOT 33,333 shares.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    top_preds = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market": "NASDAQ",
            "close_price": 150.0,
            "action": "BUY",
            "volatility_20d": 0.02,
        }
    ]
    weights = {"AAPL": 0.05}  # 5% of 100M KRW = 5,000,000 KRW
    
    # Run with default FX 1350.0
    plans = engine.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100000000.0,
        crisis_level="NORMAL",
        use_leland_buffer=False,
        usdkrw_rate=1350.0
    )
    
    assert len(plans) == 1
    plan = plans[0]
    assert plan["symbol"] == "AAPL"
    assert plan["target_price"] == 150.0
    # Expected: int((5,000,000 / 1350) // 150) = int(3703.70 // 150) = 24 shares
    assert plan["quantity"] == 24
    assert plan["quantity"] < 100  # definitely not 33,333!


def test_v6_25_inverse_hedge_us_market_fx_conversion():
    """
    V6-25: Verify synthetic beta inverse hedge on US market portfolio converts hedge amount to USD.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    top_preds = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market": "NASDAQ",
            "close_price": 150.0,
            "action": "BUY",
            "volatility_20d": 0.02,
        }
    ]
    weights = {"AAPL": 0.50}
    
    # Bear regime triggers Gate 8
    plans = engine.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100000000.0,
        crisis_level="ACTIVE",
        regime_label="BEAR",
        use_leland_buffer=False,
        usdkrw_rate=1350.0
    )
    
    # Find hedge order if generated
    hedge_plans = [p for p in plans if p.get("action") == "BUY_HEDGE"]
    if hedge_plans:
        h_plan = hedge_plans[0]
        # Ensure quantity is sized for USD hedge price (~$15-50 USD), not millions of shares
        assert h_plan["quantity"] < 50000


def test_v6_26_gate_7_2_return_scale_normalization():
    """
    V6-26: Verify that change_pct expressed as +5.2% (+5.2) is normalized to 0.052,
    NOT falsely triggering the +29.5% upper limit lock.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    top_preds = [
        {
            "symbol": "005930.KS",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "close_price": 70000.0,
            "action": "BUY",
            "change_pct": 5.2,  # +5.2% daily return
            "volatility_20d": 0.02,
        }
    ]
    weights = {"005930.KS": 0.10}
    
    plans = engine.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100000000.0,
        use_leland_buffer=False
    )
    
    assert len(plans) == 1
    assert plans[0]["symbol"] == "005930.KS"
    assert plans[0]["quantity"] > 0


def test_v6_26_gate_7_2_true_limit_lock_rejection():
    """
    V6-26: True +30% upper limit lock (e.g. change_pct = 30.0 or 0.30) should be skipped.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    top_preds_locked = [
        {
            "symbol": "005930.KS",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "close_price": 70000.0,
            "action": "BUY",
            "change_pct": 30.0,  # +30.0% upper limit lock
            "volatility_20d": 0.02,
        }
    ]
    weights = {"005930.KS": 0.10}
    
    plans = engine.generate_order_plan(
        top_predictions=top_preds_locked,
        portfolio_weights=weights,
        total_capital=100000000.0,
        use_leland_buffer=False
    )
    
    assert len(plans) == 0  # correctly rejected by Gate 7.2


def test_v6_26_gate_7_4_adverse_opening_gap_normalization():
    """
    V6-26: Normal -1.0% pullback (change_pct = -1.0) normalized to -0.01 should NOT trigger -3 sigma shock rejection.
    Extreme -15% gap (change_pct = -15.0) normalized to -0.15 should trigger rejection.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    # 1. Normal -1% pullback
    top_preds_normal = [
        {
            "symbol": "005930.KS",
            "name": "Samsung",
            "market": "KOSPI",
            "close_price": 70000.0,
            "action": "BUY",
            "change_pct": -1.0,  # -1.0% pullback
            "volatility_20d": 0.02,
        }
    ]
    plans = engine.generate_order_plan(
        top_predictions=top_preds_normal,
        portfolio_weights={"005930.KS": 0.10},
        total_capital=100000000.0,
        use_leland_buffer=False
    )
    assert len(plans) == 1
    
    # 2. Extreme -15% adverse gap
    top_preds_extreme = [
        {
            "symbol": "005930.KS",
            "name": "Samsung",
            "market": "KOSPI",
            "close_price": 70000.0,
            "action": "BUY",
            "change_pct": -15.0,  # -15% toxic gap
            "volatility_20d": 0.02,
        }
    ]
    plans_extreme = engine.generate_order_plan(
        top_predictions=top_preds_extreme,
        portfolio_weights={"005930.KS": 0.10},
        total_capital=100000000.0,
        use_leland_buffer=False
    )
    assert len(plans_extreme) == 0


def test_v6_27_almgren_chriss_slicing_non_negative_tranches():
    """
    V6-27: Test that Almgren-Chriss scheduler never produces negative tranches,
    reconciles exact total quantity, and scales eta properly.
    """
    test_quantities = [1, 2, 3, 5, 7, 10, 13, 25, 99, 100, 1000, 54321]
    tiers = ["fast", "medium", "slow"]
    slice_counts = [2, 3, 4, 5, 6, 8, 12]
    
    for q in test_quantities:
        for tier in tiers:
            for n in slice_counts:
                alloc = AlmgrenChrissScheduler.compute_trajectory(
                    total_quantity=q,
                    adv=1_000_000_000.0,
                    daily_volatility=0.02,
                    strategy_tier=tier,
                    n_slices=n
                )
                assert len(alloc) == n
                assert all(x >= 0 for x in alloc), f"Negative tranche found in alloc={alloc} for Q={q}, tier={tier}, n={n}"
                assert sum(alloc) == q, f"Sum mismatch: sum({alloc}) != {q}"


def test_v6_28_gate_7_3_friction_cost_single_deduction():
    """
    V6-28: If ensemble_expected_return is given (which is already net of friction costs),
    hurdle is only safety_margin (0.10%), NOT friction_cost + safety_margin.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")
    
    # Alpha has net expected return of 0.5% (ensemble_expected_return = 0.5)
    top_preds_net = [
        {
            "symbol": "005930.KS",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "close_price": 70000.0,
            "action": "BUY",
            "ensemble_expected_return": 0.50,  # 0.50% net return
            "volatility_20d": 0.02,
        }
    ]
    
    plans = engine.generate_order_plan(
        top_predictions=top_preds_net,
        portfolio_weights={"005930.KS": 0.10},
        total_capital=100000000.0,
        use_leland_buffer=False
    )
    
    assert len(plans) == 1
    assert plans[0]["symbol"] == "005930.KS"

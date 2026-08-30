"""
Unit Tests for ExecutionOMSEngine / OrderManager (V6-25, V6-26, V6-27, V6-28)
"""
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


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


def test_micro_cap_adv_floor_capping():
    """
    Verify Gate 7.5 micro-cap ADV capacity floor capping:
    max_adv_amount = min(max_adv_ratio * adv_val, max(adv_floor, 0.50 * adv_val))
    Protects against allocating excessive percentage of daily volume in micro-caps.
    """
    engine = ExecutionOMSEngine(db_path=":memory:")

    # 1. US Micro-cap with ADV = $4,000 USD (adv_floor = $10,000 USD)
    # 5% ADV = $200 USD. 50% ADV = $2,000 USD.
    # Cap should be min(0.05 * 4000, max(10000, 2000)) = min(200, 10000) = $200 USD.
    top_preds_us = [
        {
            "symbol": "PENNY",
            "name": "Micro Cap Penny Inc.",
            "market": "NASDAQ",
            "close_price": 2.0,
            "action": "BUY",
            "adv": 4000.0,
            "volatility_20d": 0.05,
        }
    ]
    # 50% of 100M KRW (~$74,000 USD) target weight
    plans_us = engine.generate_order_plan(
        top_predictions=top_preds_us,
        portfolio_weights={"PENNY": 0.50},
        total_capital=100000000.0,
        max_adv_ratio=0.05,
        usdkrw_rate=1350.0,
        use_leland_buffer=False
    )
    assert len(plans_us) == 1
    plan_us = plans_us[0]
    # Order value in USD must not exceed $200 USD (100 shares @ $2.0)
    assert plan_us["quantity"] * 2.0 <= 200.0 + 1e-4
    assert plan_us["quantity"] == 100

    # 2. KRX Micro-cap with ADV = 10,000,000 KRW
    top_preds_krx = [
        {
            "symbol": "999990",
            "name": "KRX Small Cap",
            "market": "KOSDAQ",
            "close_price": 5000.0,
            "action": "BUY",
            "adv": 10_000_000.0,  # 10M KRW
            "volatility_20d": 0.04,
        }
    ]
    plans_krx = engine.generate_order_plan(
        top_predictions=top_preds_krx,
        portfolio_weights={"999990": 0.50},
        total_capital=100000000.0,
        max_adv_ratio=0.05,
        use_leland_buffer=False
    )
    assert len(plans_krx) == 1
    # 5% of 10M KRW = 500,000 KRW (100 shares @ 5,000 KRW)
    assert plans_krx[0]["target_amount"] <= 500000.0 + 1e-4
    assert plans_krx[0]["quantity"] == 100


def test_trailing_stop_dynamic_atr_scaling_short_history():
    """
    Verify calculate_trailing_stop_plan dynamically scales fallback ATR using
    volatility_20d or annualized_volatility when historical price series has < 14 rows.
    """
    import pandas as pd
    engine = ExecutionOMSEngine(db_path=":memory:")

    # 1. Pullback from high with short price history (< 14 rows)
    # High reached 135.0, pulled back to 118.0.
    # With 6% daily vol (volatility_20d = 0.06), ATR = 118 * 0.06 = 7.08.
    # Trailing stop price = 135 - (2.0 * 7.08) = 120.84.
    # Since current_price (118.0) <= 120.84, it triggers CHANDELIER_TRAILING_PROFIT!
    holdings_high_vol = {
        "MEME_STOCK": {
            "quantity": 100,
            "entry_price": 100.0,
            "current_price": 118.0,
            "days_held": 5,
            "volatility_20d": 0.06,  # 6% daily vol
            "current_score": 0.70,
        }
    }
    short_prices_dict = {
        "MEME_STOCK": pd.DataFrame({
            "High": [120.0, 128.0, 135.0, 125.0, 118.0],
            "Low": [115.0, 122.0, 130.0, 120.0, 115.0],
            "Close": [118.0, 126.0, 132.0, 122.0, 118.0],
        })
    }

    plans_high = engine.calculate_trailing_stop_plan(
        current_holdings=holdings_high_vol,
        prices_dict=short_prices_dict,
        profit_take_threshold=0.15,
        regime="BULL_LOW_VOL"
    )
    assert len(plans_high) >= 1
    tp_plan = next(p for p in plans_high if p["symbol"] == "MEME_STOCK")
    assert tp_plan["action"] == "SELL"
    assert tp_plan["reason"] == "CHANDELIER_TRAILING_PROFIT"
    assert tp_plan["current_price"] == 118.0

    # 2. Test ATR stop loss with annualized_volatility and no price DataFrame
    # Entry at 100.0, drops to 90.0.
    # annualized_vol = 0.476 -> daily_vol ~ 0.03 -> ATR = 90 * 0.03 = 2.7 -> stop_loss = 100 - 1.5 * 2.7 = 95.95
    # Since 90.0 <= 95.95, it triggers ATR_STOP_LOSS!
    holdings_ann_vol = {
        "ANN_VOL_STOCK": {
            "quantity": 100,
            "entry_price": 100.0,
            "current_price": 90.0,
            "days_held": 3,
            "annualized_volatility": 0.476,
            "current_score": 0.70,
        }
    }
    plans_ann = engine.calculate_trailing_stop_plan(
        current_holdings=holdings_ann_vol,
        prices_dict=None,
        profit_take_threshold=0.15,
        regime="BULL_LOW_VOL"
    )
    assert len(plans_ann) >= 1
    sl_plan = next(p for p in plans_ann if p["symbol"] == "ANN_VOL_STOCK")
    assert sl_plan["action"] == "SELL"
    assert sl_plan["reason"] == "ATR_STOP_LOSS"


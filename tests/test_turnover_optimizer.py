"""
Unit Tests for TurnoverOptimizer (V6-29)
"""
from src.execution.turnover_optimizer import TurnoverOptimizer


def test_v6_29_full_liquidation_bypasses_turnover_hysteresis():
    """
    V6-29: When raw_target_weight is 0.0 and current_weight > 0.0,
    the position must be sold (action = 'SELL', target_weight = 0.0),
    even if weight_delta is below the 5% turnover threshold.
    """
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50000.0)
    
    current_holdings = {"005930.KS": 0.04}  # 4% holding (< 5% threshold)
    target_allocations = {"005930.KS": 0.00}  # drop from target portfolio
    
    res = opt.optimize_allocations(
        current_holdings=current_holdings,
        target_allocations=target_allocations,
        total_capital=100000000.0
    )
    
    assert "005930.KS" in res
    sym_res = res["005930.KS"]
    assert sym_res["action"] == "SELL"
    assert sym_res["target_weight"] == 0.00
    assert sym_res["delta_amount"] == 4000000.0


def test_v6_29_fresh_entry_bypasses_turnover_hysteresis():
    """
    V6-29: When current_weight is 0.0 and raw_target_weight > 0.0,
    the new position must be initiated (action = 'BUY', target_weight = raw_w),
    even if target_weight is below the 5% turnover threshold.
    """
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50000.0)
    
    current_holdings = {"005930.KS": 0.00}  # not held currently
    target_allocations = {"005930.KS": 0.03}  # 3% target weight (< 5% threshold)
    
    res = opt.optimize_allocations(
        current_holdings=current_holdings,
        target_allocations=target_allocations,
        total_capital=100000000.0
    )
    
    assert "005930.KS" in res
    sym_res = res["005930.KS"]
    assert sym_res["action"] == "BUY"
    assert sym_res["target_weight"] == 0.03
    assert sym_res["delta_amount"] == 3000000.0


def test_turnover_hysteresis_small_rebalance_hold():
    """
    Verify that an existing position with a minor rebalance adjustment (e.g. 10% -> 12%)
    below the 5% threshold is held at current weight (action = 'HOLD').
    """
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50000.0)
    
    current_holdings = {"005930.KS": 0.10}
    target_allocations = {"005930.KS": 0.12}  # delta = 2% < 5%
    
    res = opt.optimize_allocations(
        current_holdings=current_holdings,
        target_allocations=target_allocations,
        total_capital=100000000.0
    )
    
    assert res["005930.KS"]["action"] == "HOLD"
    assert res["005930.KS"]["target_weight"] == 0.10
    assert res["005930.KS"]["delta_amount"] == 0.0


def test_turnover_hysteresis_large_rebalance_trade():
    """
    Verify that an existing position with a large rebalance adjustment (e.g. 10% -> 20%)
    above the 5% threshold is rebalanced (action = 'BUY').
    """
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50000.0)
    
    current_holdings = {"005930.KS": 0.10}
    target_allocations = {"005930.KS": 0.20}  # delta = 10% > 5%
    
    res = opt.optimize_allocations(
        current_holdings=current_holdings,
        target_allocations=target_allocations,
        total_capital=100000000.0
    )
    
    assert res["005930.KS"]["action"] == "BUY"
    assert res["005930.KS"]["target_weight"] == 0.20
    assert res["005930.KS"]["delta_amount"] == 10000000.0


def test_market_adaptive_threshold_resolution():
    """
    F-R3.3: Verify resolve_threshold accurately identifies US vs KRX assets
    and assigns theta_US = 0.025 and theta_KRX = 0.045.
    """
    opt = TurnoverOptimizer()
    # US symbols & markets
    assert opt.resolve_threshold("SP500") == 0.025
    assert opt.resolve_threshold("NASDAQ") == 0.025
    assert opt.resolve_threshold("RUSSELL2000") == 0.025
    assert opt.resolve_threshold("AAPL", currency="USD") == 0.025
    assert opt.resolve_threshold("MSFT") == 0.025

    # KRX symbols & markets
    assert opt.resolve_threshold("KOSPI") == 0.045
    assert opt.resolve_threshold("KOSDAQ") == 0.045
    assert opt.resolve_threshold("005930") == 0.045
    assert opt.resolve_threshold("005930.KS") == 0.045
    assert opt.resolve_threshold("091990.KQ") == 0.045

    # Market map override
    market_map = {"CUSTOM_SYM": "US", "KR_SYM": "KRX"}
    assert opt.resolve_threshold("CUSTOM_SYM", market_map=market_map) == 0.025
    assert opt.resolve_threshold("KR_SYM", market_map=market_map) == 0.045

    # Custom thresholds in init
    custom_opt = TurnoverOptimizer(market_thresholds={"US": 0.03, "KRX": 0.06})
    assert custom_opt.resolve_threshold("SP500") == 0.03
    assert custom_opt.resolve_threshold("KOSPI") == 0.06


def test_market_adaptive_hysteresis_dampens_krx_differently_than_us():
    """
    F-R3.3: A 3.5% position delta is greater than theta_US (0.025), so US asset rebalances.
    The same 3.5% position delta is less than theta_KRX (0.045), so KRX asset is held (HOLD).
    """
    opt = TurnoverOptimizer()

    current_holdings = {
        "SP500": 0.20,
        "KOSPI": 0.20,
    }
    target_allocations = {
        "SP500": 0.235,  # delta = 3.5% > 2.5% -> Rebalance
        "KOSPI": 0.235,  # delta = 3.5% < 4.5% -> HOLD
    }

    res = opt.optimize_allocations(
        current_holdings=current_holdings,
        target_allocations=target_allocations,
        total_capital=100000000.0
    )

    assert res["KOSPI"]["action"] == "HOLD"
    assert res["KOSPI"]["target_weight"] == 0.20

    assert res["SP500"]["action"] in ("BUY", "SELL")
    assert res["SP500"]["target_weight"] > 0.20



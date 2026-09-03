"""
Adversarial Stress Test Script for Milestone 2 (F09-F13)
Tests extreme edge cases, invalid inputs, singular matrices, and stress boundaries.
"""

import math
import sys
import os
sys.path.insert(0, os.path.abspath("trading_system"))
import numpy as np
import pandas as pd
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

def test_f09_adversarial():
    print("Testing F09 Adversarial Edge Cases...")
    alloc = UnifiedPortfolioAllocator()

    # 1. Empty dict
    cfg_empty = alloc.compute_dynamic_regime_blend_weights({})
    assert math.isclose(sum(cfg_empty.values()), 1.0, rel_tol=1e-5), f"Empty dict failed: {cfg_empty}"

    # 2. All zero probabilities
    cfg_zero = alloc.compute_dynamic_regime_blend_weights({"BULL_LOW_VOL": 0.0, "CRISIS": 0.0})
    assert math.isclose(sum(cfg_zero.values()), 1.0, rel_tol=1e-5), f"Zero dict failed: {cfg_zero}"

    # 3. Negative probabilities
    cfg_neg = alloc.compute_dynamic_regime_blend_weights({"BULL_LOW_VOL": -0.5, "CRISIS": 1.0})
    assert math.isclose(sum(cfg_neg.values()), 1.0, rel_tol=1e-5), f"Neg dict failed: {cfg_neg}"

    # 4. Unknown regime string
    cfg_unk = alloc.compute_dynamic_regime_blend_weights("UNKNOWN_REGIME_XYZ")
    assert math.isclose(sum(cfg_unk.values()), 1.0, rel_tol=1e-5), f"Unknown string failed: {cfg_unk}"

    # 5. Invalid integer
    cfg_int = alloc.compute_dynamic_regime_blend_weights(999)
    assert math.isclose(sum(cfg_int.values()), 1.0, rel_tol=1e-5), f"Invalid int failed: {cfg_int}"

    # 6. NaN / Inf VIX
    cfg_nan_vix = alloc.compute_dynamic_regime_blend_weights("BULL_LOW_VOL", vix_val=float("nan"))
    assert math.isclose(sum(cfg_nan_vix.values()), 1.0, rel_tol=1e-5)
    cfg_inf_vix = alloc.compute_dynamic_regime_blend_weights("BULL_LOW_VOL", vix_val=float("inf"))
    assert math.isclose(sum(cfg_inf_vix.values()), 1.0, rel_tol=1e-5)

    # 7. Extreme crisis severity
    cfg_ext_crisis = alloc.compute_dynamic_regime_blend_weights("BULL_LOW_VOL", crisis_severity=99.0)
    assert math.isclose(sum(cfg_ext_crisis.values()), 1.0, rel_tol=1e-5)
    print("  cfg_ext_crisis['bl']:", cfg_ext_crisis["bl"])
    assert cfg_ext_crisis["bl"] < 0.10, f"BL should be heavily suppressed under crisis severity: {cfg_ext_crisis['bl']}"

    # 8. EMA smoothing with consecutive calls
    cfg_ema1 = alloc.compute_dynamic_regime_blend_weights("BULL_LOW_VOL", apply_ema=True)
    cfg_ema2 = alloc.compute_dynamic_regime_blend_weights("CRISIS", apply_ema=True)
    assert math.isclose(sum(cfg_ema2.values()), 1.0, rel_tol=1e-5)
    assert cfg_ema2["cvar"] > cfg_ema1["cvar"]
    print("  [OK] F09 passed all adversarial checks!")

def test_f10_adversarial():
    print("Testing F10 Adversarial Edge Cases...")
    # 1. Zero variance / constant returns
    n_days, K = 50, 4
    const_returns = np.zeros((n_days, K))
    base_cov = np.eye(K) * 1e-4
    cov_stressed = PortfolioAllocator.compute_tail_stress_cov(
        const_returns, base_cov, tail_quantile=0.10, stress_weight=0.35, use_clayton_copula=True
    )
    assert cov_stressed.shape == (K, K)
    assert np.all(np.isfinite(cov_stressed))
    evals = np.linalg.eigvalsh(cov_stressed)
    assert np.all(evals > 0), f"Eigenvalues must be positive: {evals}"

    # 2. Singular covariance matrix
    sing_cov = np.ones((K, K)) * 0.01
    np.random.seed(123)
    rand_rets = np.random.randn(n_days, K) * 0.02
    cov_stressed_sing = PortfolioAllocator.compute_tail_stress_cov(
        rand_rets, sing_cov, tail_quantile=0.10, stress_weight=0.50, use_clayton_copula=True
    )
    evals_sing = np.linalg.eigvalsh(cov_stressed_sing)
    assert np.all(evals_sing > 0), f"Eigenvalues must be positive after projection: {evals_sing}"

    # 3. Parametric EVT-CVaR with singular covariance
    alloc = UnifiedPortfolioAllocator(max_single_weight=0.40)
    df_rets = pd.DataFrame(rand_rets, columns=[f"A{i}" for i in range(K)])
    w_cvar = alloc.calculate_cvar_weights(
        df_rets, confidence_level=0.95, predicted_returns=np.array([0.1, 0.05, -0.02, 0.0]),
        cov_matrix=cov_stressed_sing, regime="CRISIS"
    )
    assert len(w_cvar) == K
    assert math.isclose(sum(w_cvar), 1.0, rel_tol=1e-4)
    assert np.all(w_cvar >= -1e-6)
    assert np.all(w_cvar <= 0.40 + 1e-4)
    print("  [OK] F10 passed all adversarial checks!")

def test_f11_adversarial():
    print("Testing F11 Adversarial Edge Cases...")
    alloc = UnifiedPortfolioAllocator()
    n = 3
    symbols = ["S1", "S2", "S3"]
    preds = np.array([0.10, 0.10, 0.10])
    returns_df = pd.DataFrame(np.random.normal(0, 0.02, (50, n)), columns=symbols)
    cov_matrix = np.eye(n) * 0.0004
    advs = np.array([1e7, 1e7, 1e7])

    # 1. NaN and Inf in darkpool scores
    w_nan = alloc.optimize_multi_model_blend(
        predicted_returns=preds, returns_df=returns_df, cov_matrix=cov_matrix, symbols=symbols,
        current_weights=np.zeros(n), advs=advs, total_capital=1e7,
        darkpool_scores=np.array([float("nan"), float("inf"), -1.0])
    )
    assert len(w_nan) == n
    assert np.all(np.isfinite(w_nan))
    print("  sum(w_nan):", sum(w_nan))
    assert sum(w_nan) > 0.0, "w_nan must be positive"

    # 2. Dict input for darkpool_scores with missing keys
    w_dict = alloc.optimize_multi_model_blend(
        predicted_returns=preds, returns_df=returns_df, cov_matrix=cov_matrix, symbols=symbols,
        current_weights=np.zeros(n), advs=advs, total_capital=1e7,
        darkpool_scores={"S1": 0.8}  # S2, S3 missing
    )
    assert len(w_dict) == n
    assert np.all(np.isfinite(w_dict))
    print("  sum(w_dict):", sum(w_dict))
    assert sum(w_dict) > 0.0, "w_dict must be positive"
    print("  [OK] F11 passed all adversarial checks!")

def test_f12_adversarial():
    print("Testing F12 Adversarial Edge Cases...")
    sor = SmartOrderRouter()

    # 1. Quantity conservation under various odd quantities
    for qty in [1, 2, 3, 7, 13, 99, 100, 1000, 10007]:
        order = {
            "symbol": "TEST", "action": "BUY", "quantity": qty,
            "target_price": 100.0, "execution_strategy": "MIDPOINT_PEG",
            "darkpool_score": 0.85, "is_accumulation": True
        }
        res = sor.route_order(order, ats_available=True)
        leg_sum = sum(leg["quantity"] for leg in res["legs"])
        assert leg_sum == qty, f"Leg sum {leg_sum} != order qty {qty}"
        assert res["effective_dark_ratio"] <= 0.70
        assert res["effective_dark_ratio"] >= 0.40

    # 2. ats_available = False
    res_no_ats = sor.route_order({"symbol": "TEST", "action": "BUY", "quantity": 100, "target_price": 50.0}, ats_available=False)
    assert res_no_ats["dark_ats_midpoint"] is None
    assert sum(leg["quantity"] for leg in res_no_ats["legs"]) == 100

    # 3. Aggressive strategy without accumulation
    res_agg = sor.route_order({"symbol": "TEST", "action": "BUY", "quantity": 100, "target_price": 50.0, "execution_strategy": "AGGRESSIVE_TAKER"}, ats_available=True)
    # Aggressive taker with 0 darkpool score goes to lit sweeper
    assert res_agg["lit_exchange_sweeper"] is not None
    assert sum(leg["quantity"] for leg in res_agg["legs"]) == 100
    print("  [OK] F12 passed all adversarial checks!")

def test_f13_adversarial():
    print("Testing F13 Adversarial Edge Cases...")
    # 1. Extreme OBI values
    p_high = ExecutionOMSEngine.calculate_peg_limit_price(
        target_price=100.0, bid_price=99.0, ask_price=101.0, spread=2.0,
        action="BUY", obi=100.0 # way above 1.0
    )
    assert p_high <= 101.0, f"Must not exceed ask: {p_high}"

    p_low = ExecutionOMSEngine.calculate_peg_limit_price(
        target_price=100.0, bid_price=99.0, ask_price=101.0, spread=2.0,
        action="BUY", obi=-100.0 # way below -1.0
    )
    assert p_low >= 99.0, f"Must not fall below bid: {p_low}"

    # 2. Crossed market (bid > ask)
    p_crossed = ExecutionOMSEngine.calculate_peg_limit_price(
        target_price=100.0, bid_price=101.0, ask_price=99.0, spread=2.0,
        action="BUY", obi=0.5
    )
    assert math.isfinite(p_crossed)

    # 3. None inputs
    p_none = ExecutionOMSEngine.calculate_peg_limit_price(target_price=100.0)
    assert math.isclose(p_none, 100.0, rel_tol=1e-2)

    # 4. Sell action
    p_sell = ExecutionOMSEngine.calculate_peg_limit_price(
        target_price=100.0, bid_price=99.0, ask_price=101.0, spread=2.0,
        action="SELL", obi=0.5
    )
    assert math.isfinite(p_sell)
    print("  [OK] F13 passed all adversarial checks!")

if __name__ == "__main__":
    test_f09_adversarial()
    test_f10_adversarial()
    test_f11_adversarial()
    test_f12_adversarial()
    test_f13_adversarial()
    print("\nALL ADVERSARIAL CHECKS PASSED SUCCESSFULLY!")

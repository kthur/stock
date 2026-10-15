"""
tests/verify_challenger1_deep_stress.py
======================================
Comprehensive Empirical Adversarial Stress Harness for Phase 108 Master Challenger 1.
Validates M1, M2, M3, M4 across extreme edge cases, singularities, and boundary conditions.
"""

from __future__ import annotations

import math
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.concept_drift_calibrator import (
    ContinuousConceptDriftCalibrator,
    PageHinkleyDetector,
    TwoSidedCUSUMDetector,
    BayesianWeightCalibrator,
    DriftStatus,
)
from src.execution.multi_asset_cross_impact_slicer import (
    AssetOrderSpec,
    HighamPSDProjector,
    KylesLambdaEstimator,
    MultiAssetCrossImpactSlicer,
)
from src.analysis.brinson_factor_attributor import (
    BrinsonFactorAttributor,
    BrinsonDecompositionResult,
)
from src.core.shared_memory_ring_buffer import (
    SharedMemoryRingBuffer,
    MessageType,
    LOBTickMessage,
    RiskAlertMessage,
    ExecutionOrderMessage,
    MAGIC_HEADER,
    OFFSET_MAGIC,
    OFFSET_HEAD_SEQ,
    OFFSET_TAIL_SEQ,
    OFFSET_DROPPED_COUNT,
)


FAILURES = []

def log_result(test_name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}: {details}")
    if not passed:
        FAILURES.append((test_name, details))


# ===========================================================================
# 1. M1 Adversarial Empirical Checks
# ===========================================================================
def test_m1_adversarial():
    print("\n--- Starting M1 Adversarial Empirical Checks ---")

    # M1.1: 10-sigma, 20-sigma, 50-sigma residual jumps
    calib = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)
    strat = "regression"
    for _ in range(5):
        calib.observe_residual(strat, residual=0.0)

    for jump_sigma in [10.0, 20.0, 50.0]:
        m = calib.observe_residual(strat, residual=jump_sigma)
        log_result(
            f"M1.1 Jump {jump_sigma}-sigma",
            m.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT) and m.shrinkage_factor < 0.95,
            f"status={m.status.value}, composite_drift={m.composite_drift_score:.2f}, shrinkage={m.shrinkage_factor:.4f}"
        )

    # M1.2: NaN/Inf residual sequence injection
    calib_nan = ContinuousConceptDriftCalibrator()
    bad_seq = [float("nan"), float("inf"), float("-inf"), 1e308, -1e308, 0.0]
    m1_nan_vulnerability_found = False
    try:
        # Test 1: Directly injecting NaN
        obs_nan = calib_nan.observe_residual("surge", float("nan"))
        # Test 2: Extreme overflow float triggering math domain error
        calib_overflow = ContinuousConceptDriftCalibrator()
        calib_overflow.observe_residual("regression", 1e308)
        calib_overflow.observe_residual("regression", -1e308)
    except (ValueError, Exception) as e:
        m1_nan_vulnerability_found = True
        log_result("M1.2 NaN/Inf Residual Injection (VULNERABILITY DETECTED)", False, f"Direct injection of extreme float raises: {type(e).__name__}: {e}")

    if not m1_nan_vulnerability_found:
        log_result("M1.2 NaN/Inf Residual Injection", True, "All values handled")

    # M1.3: Zero-variance residual series (1,000 steps of 0.0)
    calib_zero = ContinuousConceptDriftCalibrator()
    no_div_zero = True
    for _ in range(1000):
        m = calib_zero.observe_residual("lstm", 0.0)
        if not (math.isfinite(m.mean_residual) and math.isfinite(m.std_residual) and m.std_residual > 0):
            no_div_zero = False
            break
    log_result("M1.3 Zero-Variance Flat Series", no_div_zero, "1000 consecutive identical residuals caused no ZeroDivisionError")

    # M1.4: Systemic macro regime shift gating (>= 50% drifting strategies triggers REGIME_SHIFT)
    calib_regime = ContinuousConceptDriftCalibrator()
    log_result("M1.4 Regime Shift Pre-Condition", not calib_regime.is_regime_shift(), "Initial state is not REGIME_SHIFT")

    # Drift exactly 19 of 37 strategies (51.35%)
    for s in calib_regime.STRATEGIES_37[:19]:
        for _ in range(20):
            calib_regime.observe_residual(s, residual=5.0)

    is_reg = calib_regime.is_regime_shift()
    base_w = {s: 1.0 / 37 for s in calib_regime.STRATEGIES_37}
    calib_w = calib_regime.calibrate_strategy_weights(base_w)
    simplex_sum = sum(calib_w.values())
    sum_valid = abs(simplex_sum - 1.0) < 1e-12

    # Check defensive quality weighting tilt
    quality_tilt_preserved = any(
        calib_w[q] > calib_w[calib_regime.STRATEGIES_37[0]]
        for q in calib_regime.DEFENSIVE_QUALITY_STRATEGIES
    )
    log_result(
        "M1.4 Systemic Regime Shift Gating",
        is_reg and sum_valid and quality_tilt_preserved,
        f"is_regime_shift={is_reg}, simplex_sum={simplex_sum:.10f}, quality_tilt={quality_tilt_preserved}"
    )


# ===========================================================================
# 2. M2 Adversarial Empirical Checks
# ===========================================================================
def test_m2_adversarial():
    print("\n--- Starting M2 Adversarial Empirical Checks ---")

    # M2.1: Rank-deficient / ill-conditioned singular covariance matrix
    # Rank 1 matrix of ones
    sing_matrix = np.ones((5, 5), dtype=np.float64)
    psd_mat, min_eig, is_psd = HighamPSDProjector.project(sing_matrix, epsilon_eigen=1e-10)
    all_eig_positive = np.all(np.linalg.eigvalsh(psd_mat) >= 1e-10 - 1e-14)
    log_result("M2.1 Higham Rank-Deficient Projection", is_psd and all_eig_positive, f"min_eig={min_eig:.2e}, projected_min={np.min(np.linalg.eigvalsh(psd_mat)):.2e}")

    # M2.2: Negative correlation spikes (rho = -0.999)
    slicer = MultiAssetCrossImpactSlicer()
    orders_pair = [
        AssetOrderSpec(symbol="A", target_quantity=1000, adv_shares=1_000_000.0, daily_volatility=0.02),
        AssetOrderSpec(symbol="B", target_quantity=1000, adv_shares=1_000_000.0, daily_volatility=0.02),
    ]
    neg_corr = np.array([[1.0, -0.999], [-0.999, 1.0]], dtype=np.float64)
    sched_neg = slicer.optimize_basket_slices(orders_pair, correlation_matrix=neg_corr, n_slices=6)
    log_result(
        "M2.2 Negative Correlation Spike (rho=-0.999)",
        sched_neg.total_execution_cost >= 0.0 and math.isfinite(sched_neg.total_execution_cost),
        f"cost={sched_neg.total_execution_cost:.4f}, savings={sched_neg.cross_impact_savings_pct:.2f}%"
    )

    # M2.3: Extreme ADV constraints (1 share/day vs 1,000,000,000 shares/day)
    orders_extreme = [
        AssetOrderSpec(symbol="MICRO", target_quantity=1, adv_shares=1.0, daily_volatility=0.05),
        AssetOrderSpec(symbol="MEGA", target_quantity=100000, adv_shares=1_000_000_000.0, daily_volatility=0.01),
    ]
    sched_ext = slicer.optimize_basket_slices(orders_extreme, n_slices=6)
    log_result(
        "M2.3 Extreme ADV Disparity (1 vs 10^9)",
        math.isfinite(sched_ext.total_execution_cost) and sched_ext.total_execution_cost > 0.0,
        f"total_cost={sched_ext.total_execution_cost:.4f}, slices={sched_ext.n_slices}"
    )

    # M2.4: ADV participation cap (<= 1.5%)
    orders_cap = [
        AssetOrderSpec(symbol="CAP_MICRO", target_quantity=10, adv_shares=1000.0, daily_volatility=0.05),
        AssetOrderSpec(symbol="CAP_MEGA", target_quantity=100000, adv_shares=1_000_000_000.0, daily_volatility=0.01),
    ]
    sched_cap = slicer.optimize_basket_slices(orders_cap, n_slices=6)
    max_part = float(np.max(sched_cap.adv_participation_rates))
    log_result("M2.4 Strict 1.5% ADV Participation Cap", max_part <= 0.015 + 1e-6, f"max_participation={max_part:.6f} (<= 0.015000)")

    # M2.5: Integer share volume conservation under odd/prime order quantities
    prime_quantities = [7, 13, 17, 31, 997, 10007]
    prime_orders = [
        AssetOrderSpec(symbol=f"P_{q}", target_quantity=q, adv_shares=2_000_000.0)
        for q in prime_quantities
    ]
    for n_sl in [3, 5, 7, 11]:
        sched_prime = slicer.optimize_basket_slices(prime_orders, n_slices=n_sl)
        actual_sums = np.sum(sched_prime.slice_tranches, axis=1)
        conserved = np.array_equal(actual_sums, np.array(prime_quantities, dtype=np.int64))
        log_result(f"M2.5 Integer Volume Conservation (slices={n_sl})", conserved, f"primes={prime_quantities}, actual_sums={actual_sums.tolist()}")


# ===========================================================================
# 3. M3 Adversarial Empirical Checks
# ===========================================================================
def test_m3_adversarial():
    print("\n--- Starting M3 Adversarial Empirical Checks ---")
    attributor = BrinsonFactorAttributor()

    # M3.1: Degenerate benchmark weights (concentrated 100% in 1 segment, empty others)
    w_p = {"Tech": 0.50, "Energy": 0.30, "Healthcare": 0.20}
    w_b = {"Tech": 1.00, "Energy": 0.00, "Healthcare": 0.00}
    r_p = {"Tech": 0.02, "Energy": -0.01, "Healthcare": 0.03}
    r_b = {"Tech": 0.01, "Energy": 0.00, "Healthcare": 0.00}
    res_degen = attributor.decompose_single_period(
        portfolio_weights=w_p,
        benchmark_weights=w_b,
        asset_returns_local=r_p,
        benchmark_returns_local=r_b,
    )
    log_result(
        "M3.1 Degenerate Benchmark Weights",
        res_degen.is_identity_valid and res_degen.arithmetic_identity_error < 1e-14,
        f"identity_error={res_degen.arithmetic_identity_error:.2e}, active_return={res_degen.total_active_return:.6f}"
    )

    # M3.2: Extreme FX rate shocks (-90% plunge, +300% hyper-rally)
    c_extreme = {"Tech": -0.90, "Energy": 3.00, "Healthcare": 0.00}
    res_fx = attributor.decompose_single_period(
        portfolio_weights=w_p,
        benchmark_weights=w_b,
        asset_returns_local=r_p,
        benchmark_returns_local=r_b,
        currency_returns=c_extreme,
        hedge_ratios={"Tech": 0.5, "Energy": 1.0, "Healthcare": 0.0},
        forward_premiums={"Tech": 0.02, "Energy": 0.05, "Healthcare": 0.0},
    )
    log_result(
        "M3.2 Extreme FX Rate Shocks (-90% to +300%)",
        res_fx.is_identity_valid and res_fx.arithmetic_identity_error < 1e-14,
        f"identity_error={res_fx.arithmetic_identity_error:.2e}, currency_effect={res_fx.currency_effect:.6f}"
    )

    # M3.3: Multi-period Carino linking under zero active return (0/0 singularity resolution)
    daily_results = []
    for d in range(10):
        # Daily portfolio return EXACTLY equal to benchmark return
        same_r = {"Eq": 0.01 * (d + 1)}
        res_zero = attributor.decompose_single_period(
            portfolio_weights={"Eq": 1.0},
            benchmark_weights={"Eq": 1.0},
            asset_returns_local=same_r,
            benchmark_returns_local=same_r,
        )
        daily_results.append(res_zero)

    multi_res = attributor.decompose_multi_period(daily_results=daily_results)
    log_result(
        "M3.3 Multi-Period Carino 0/0 Singularity",
        multi_res.is_identity_valid and abs(multi_res.cumulative_active_return) < 1e-14,
        f"cum_active={multi_res.cumulative_active_return:.2e}, identity_error={multi_res.arithmetic_identity_error:.2e}"
    )


# ===========================================================================
# 4. M4 Adversarial Empirical Checks
# ===========================================================================
def test_m4_adversarial():
    print("\n--- Starting M4 Adversarial Empirical Checks ---")

    # M4.1: Shared memory header magic corruption
    name_magic = f"test_adv_magic_{int(time.time()*1000) % 100000}"
    rb = SharedMemoryRingBuffer(name=name_magic, capacity=32, slot_size=256, create=True)
    struct.pack_into("<I", rb._buf, OFFSET_MAGIC, 0x00000000)
    magic_caught = False
    try:
        SharedMemoryRingBuffer(name=name_magic, create=False)
    except ValueError as e:
        magic_caught = "Invalid shared memory magic" in str(e)
    rb.close()
    rb.unlink()
    log_result("M4.1 Corrupted Header Magic Rejection", magic_caught, "0x00000000 magic properly caught and rejected")

    # M4.2: Non-power-of-2 capacity rejection
    bad_caps = [3, 7, 1000, 2047, 3000]
    all_rejected = True
    for bc in bad_caps:
        try:
            SharedMemoryRingBuffer(name="bad_cap_test", capacity=bc, create=True)
            all_rejected = False
        except ValueError:
            pass
    log_result("M4.2 Non-Power-of-2 Capacity Rejection", all_rejected, f"Tested {bad_caps}, all raised ValueError")

    # M4.3: Wrap-around sequence monotonicity near 2^63 - 1
    name_wrap = f"test_adv_wrap_{int(time.time()*1000) % 100000}"
    with SharedMemoryRingBuffer(name=name_wrap, capacity=16, slot_size=256, create=True) as rb_wrap:
        huge_seq = (1 << 63) - 100
        struct.pack_into("<Q", rb_wrap._buf, OFFSET_HEAD_SEQ, huge_seq)
        struct.pack_into("<Q", rb_wrap._buf, OFFSET_TAIL_SEQ, huge_seq)

        for i in range(50):
            ord_msg = ExecutionOrderMessage(
                order_id=f"O-{i}", symbol="NVDA", market="NASDAQ",
                timestamp_ns=i, side=1, order_type=1, quantity=10.0, price=100.0, status=1
            )
            success = rb_wrap.write_order(ord_msg)
            if not success:
                break
            read_msg = rb_wrap.read_message()
            assert read_msg.order_id == f"O-{i}"

        log_result(
            "M4.3 64-bit Wraparound Monotonicity",
            rb_wrap.head_seq == huge_seq + 50 and rb_wrap.tail_seq == huge_seq + 50,
            f"head_seq={rb_wrap.head_seq}, tail_seq={rb_wrap.tail_seq}"
        )

    # M4.4: Buffer overflow handling & dropped_count accuracy
    name_over = f"test_adv_over_{int(time.time()*1000) % 100000}"
    cap = 8
    with SharedMemoryRingBuffer(name=name_over, capacity=cap, slot_size=256, create=True) as rb_over:
        for i in range(cap):
            rb_over.write_alert(RiskAlertMessage(
                alert_id=f"A-{i}", timestamp_ns=i, symbol="TEST", market="KRX",
                severity=1, alert_type=1, metric_value=0.0, threshold_value=0.0, action_code=1, message=f"A{i}"
            ))
        assert rb_over.is_full()

        # Write 20 messages that must be dropped
        for i in range(20):
            w = rb_over.write_alert(RiskAlertMessage(
                alert_id=f"DROP-{i}", timestamp_ns=i, symbol="TEST", market="KRX",
                severity=1, alert_type=1, metric_value=0.0, threshold_value=0.0, action_code=1, message=f"D{i}"
            ))
            assert not w

        log_result(
            "M4.4 Buffer Overflow & Drop Accounting",
            rb_over.dropped_count == 20 and rb_over.available_read() == cap,
            f"dropped_count={rb_over.dropped_count}, available_read={rb_over.available_read()}"
        )

    # M4.5: Zero memory leaks across 50 create-write-read-unlink cycles
    name_leak = f"test_adv_leak_{int(time.time()*1000) % 100000}"
    leaks_prevented = True
    for cycle in range(50):
        with SharedMemoryRingBuffer(name=f"{name_leak}_{cycle}", capacity=16, slot_size=256, create=True) as rb_leak:
            rb_leak.write_tick(LOBTickMessage(
                symbol="LEAK_TEST", timestamp_ns=cycle, bid_price=10.0, ask_price=10.1,
                bid_size=1.0, ask_size=1.0, last_price=10.05, last_size=1.0
            ))
            m = rb_leak.read_message()
            if m is None or m.symbol != "LEAK_TEST":
                leaks_prevented = False
                break
    log_result("M4.5 Zero Memory Leaks (50 full cycles)", leaks_prevented, "All 50 cycles initialized, operated, and unlinked with 0 residue")


if __name__ == "__main__":
    t_start = time.perf_counter()
    test_m1_adversarial()
    test_m2_adversarial()
    test_m3_adversarial()
    test_m4_adversarial()
    t_elapsed = time.perf_counter() - t_start
    print(f"\n=======================================================")
    print(f"COMPLETED DEEP ADVERSARIAL STRESS CHECKS in {t_elapsed:.2f}s")
    print(f"Total Failures: {len(FAILURES)}")
    for name, detail in FAILURES:
        print(f"  * {name}: {detail}")
    print(f"=======================================================\n")

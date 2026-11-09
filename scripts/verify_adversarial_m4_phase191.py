"""
scripts/verify_adversarial_m4_phase191.py — Empirical Challenger Harness for Release R182 Milestone M4
Phase 191 Execution OMS & 30-Year Compounding Benchmark Elevation (Features F937–F938).

Adversarial Stress Verification Objectives:
1. F937: 14D Joseph-Stabilized Adaptive Kalman Microstructure Slippage Filter
   - Mathematical proof and numerical equivalence to minimum-variance estimator
   - 5,000 iterative predict/update cycles with adversarial noisy observations
   - Covariance P strict symmetry (||P - P^T|| < 1e-10) and positive definiteness (min lambda_i > 0)
   - Dynamic cost scaling factor bounds: strictly in [0.20, 5.0] under extreme states
2. F938: Institutional OMS Gateway with 12 Safety Gates
   - Gate 9 Physical Capital Conservation: 1,000 synthetic trading sequences (Net <= Gross)
   - 12 safety gates boundary conditions stress test
   - End-to-end OMS per-order evaluation latency SLA benchmark (< 1.5 ms)
"""

import math
import sys
import time
from pathlib import Path
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TS_ROOT = PROJECT_ROOT / "trading_system"
if str(TS_ROOT) not in sys.path:
    sys.path.insert(0, str(TS_ROOT))

from src.execution.slippage_feedback import (
    FourteenDimensionalJosephKalmanFilter,
    SlippageFeedbackEngine,
)
from src.execution.oms_engine import ExecutionOMSEngine


def verify_f937_mathematical_joseph_stabilization() -> dict:
    """Objective 1A: Numerically and mathematically verify the Joseph stabilization formula."""
    print("\n" + "=" * 70)
    print("VERIFYING F937: Mathematical Joseph Stabilization & Algebraic Equivalence")
    print("=" * 70)

    dim = 14
    rng = np.random.RandomState(42)

    # Generate valid positive-definite prior P
    A = rng.randn(dim, dim)
    P_prior = A @ A.T + np.eye(dim) * 0.1

    # Measurement vector H and scalar noise R
    H = rng.randn(dim)
    H /= np.linalg.norm(H)
    R = 2.5

    # Innovation covariance S and Kalman gain K
    S = float(H @ P_prior @ H.T + R)
    K = (P_prior @ H) / S

    # Standard textbook Kalman update: P_std = (I - K H) P_prior
    I = np.eye(dim)
    P_standard = (I - np.outer(K, H)) @ P_prior

    # Joseph stabilized update: P_joseph = (I - K H) P_prior (I - K H)^T + K R K^T
    IKH = I - np.outer(K, H)
    P_joseph = IKH @ P_prior @ IKH.T + np.outer(K, K) * R

    # Test algebraic equivalence
    diff_norm = np.linalg.norm(P_joseph - P_standard)
    asymmetry_std = np.max(np.abs(P_standard - P_standard.T))
    asymmetry_joseph = np.max(np.abs(P_joseph - P_joseph.T))

    print(f"||P_joseph - P_standard||_2: {diff_norm:.6e}")
    print(f"Max Asymmetry in standard update: {asymmetry_std:.6e}")
    print(f"Max Asymmetry in Joseph update:  {asymmetry_joseph:.6e}")

    assert diff_norm < 1e-10, f"Joseph form deviates from theoretical update: {diff_norm}"
    assert asymmetry_joseph < 1e-12, f"Joseph update is not symmetric: {asymmetry_joseph}"

    # Verify Joseph form under non-optimal gain K_sub (e.g. numerical drift)
    # The Joseph formula is the true error covariance for ANY gain K, guaranteeing PSD
    K_perturbed = K * 1.5 + 0.05
    IKH_pert = I - np.outer(K_perturbed, H)
    P_joseph_pert = IKH_pert @ P_prior @ IKH_pert.T + np.outer(K_perturbed, K_perturbed) * R
    eigvals_pert = np.linalg.eigvalsh(P_joseph_pert)
    min_eig_pert = np.min(eigvals_pert)

    print(f"Min eigenvalue with perturbed gain (non-optimal K): {min_eig_pert:.6e}")
    assert min_eig_pert > 0, f"Perturbed Joseph update lost positive definiteness: {min_eig_pert}"

    return {
        "diff_norm": diff_norm,
        "asymmetry_joseph": asymmetry_joseph,
        "min_eig_pert": min_eig_pert,
        "status": "PASS",
    }


def verify_f937_5000_cycle_adversarial_simulation() -> dict:
    """Objective 1B: 5,000 iterative predict/update cycles with adversarial, noisy observations."""
    print("\n" + "=" * 70)
    print("VERIFYING F937: 5,000-Cycle Adversarial Stress Simulation")
    print("=" * 70)

    kf = FourteenDimensionalJosephKalmanFilter()
    rng = np.random.RandomState(1337)

    n_cycles = 5000
    min_eigenvalues = []
    condition_numbers = []
    asymmetries = []
    cost_scaling_factors = []

    t0 = time.perf_counter()

    for step in range(n_cycles):
        # 1. Predict step
        kf.predict()

        # 2. Adversarial measurement generation
        # Inject periodic extreme outliers, micro-shocks, regime shifts, and Gaussian noise
        if step % 250 == 0:
            # Massive outlier shock (e.g. Flash crash or reporting error)
            z_obs = rng.choice([-500.0, 500.0, 1000.0, -1000.0])
            spread = 50.0
            part_rate = 0.25
            vpin = 0.95
            hawkes = 10.0
            vol = 0.15
        elif step % 50 == 0:
            # High volatility burst
            z_obs = rng.normal(loc=15.0, scale=30.0)
            spread = rng.uniform(8.0, 25.0)
            part_rate = rng.uniform(0.02, 0.08)
            vpin = rng.uniform(0.50, 0.85)
            hawkes = rng.uniform(3.0, 8.0)
            vol = rng.uniform(0.04, 0.08)
        else:
            # Normal noisy microstructure observation
            z_obs = rng.normal(loc=4.5, scale=5.0)
            spread = rng.uniform(2.0, 8.0)
            part_rate = rng.uniform(0.005, 0.02)
            vpin = rng.uniform(0.10, 0.45)
            hawkes = rng.uniform(0.5, 2.0)
            vol = rng.uniform(0.015, 0.03)

        trade_features = {
            "spread_bps": spread,
            "participation_rate": part_rate,
            "vpin": vpin,
            "hawkes_intensity": hawkes,
            "obi": rng.uniform(-1.0, 1.0),
            "volatility_20d": vol,
            "time_ratio": (step % 100) / 100.0,
        }

        # Dynamic measurement noise
        R_obs = max(0.01, rng.exponential(scale=1.5))

        # 3. Update step
        kf.update(z=z_obs, R=R_obs, trade_features=trade_features)

        # Check invariants every 50 cycles
        if step % 50 == 0 or step == n_cycles - 1:
            P = kf.P
            # Check symmetry
            asym = np.max(np.abs(P - P.T))
            asymmetries.append(asym)
            assert asym < 1e-10, f"Covariance asymmetry at step {step}: {asym}"

            # Check eigenvalues (positive definiteness)
            eigvals = np.linalg.eigvalsh(P)
            min_eig = np.min(eigvals)
            max_eig = np.max(eigvals)
            min_eigenvalues.append(min_eig)
            cond = max_eig / max(1e-12, min_eig)
            condition_numbers.append(cond)

            assert min_eig > 0.0, f"Covariance lost positive definiteness at step {step}: min eig = {min_eig}"
            assert np.all(np.isfinite(P)), f"Covariance contains NaN/Inf at step {step}"

            # Check scaling factor
            scale = kf.get_cost_scaling_factor()
            cost_scaling_factors.append(scale)
            assert 0.20 <= scale <= 5.0, f"Cost scaling factor out of bounds at step {step}: {scale}"

    elapsed_s = time.perf_counter() - t0
    avg_cycle_us = (elapsed_s / n_cycles) * 1e6

    min_lambda_overall = min(min_eigenvalues)
    max_asym_overall = max(asymmetries)
    max_cond_overall = max(condition_numbers)

    print(f"5,000 cycles completed in {elapsed_s:.3f} s ({avg_cycle_us:.2f} us/cycle)")
    print(f"Overall Minimum Eigenvalue: {min_lambda_overall:.6e} (> 0 PASS)")
    print(f"Overall Maximum Asymmetry:  {max_asym_overall:.6e} (< 1e-10 PASS)")
    print(f"Max Condition Number:       {max_cond_overall:.2f}")
    print(f"Final State Norm ||x||:     {np.linalg.norm(kf.x):.4f}")
    print(f"Final Cost Scaling Factor:  {kf.get_cost_scaling_factor():.4f} (bounds: [0.20, 5.0])")

    return {
        "n_cycles": n_cycles,
        "elapsed_s": elapsed_s,
        "avg_cycle_us": avg_cycle_us,
        "min_lambda_overall": min_lambda_overall,
        "max_asym_overall": max_asym_overall,
        "max_cond_overall": max_cond_overall,
        "final_cost_scaling": kf.get_cost_scaling_factor(),
        "status": "PASS",
    }


def verify_f937_dynamic_cost_scaling_bounds() -> dict:
    """Objective 1C: Verify dynamic cost scaling factor bounds under extreme adversarial states."""
    print("\n" + "=" * 70)
    print("VERIFYING F937: Dynamic Cost Scaling Factor Bounds [0.20, 5.0]")
    print("=" * 70)

    kf = FourteenDimensionalJosephKalmanFilter()

    test_states = [
        ("zeros", np.zeros(14)),
        ("all_minus_400", -400.0 * np.ones(14)),
        ("all_plus_400", 400.0 * np.ones(14)),
        ("extreme_spread_max", np.array([400.0] + [0.0] * 13)),
        ("extreme_spread_min", np.array([-400.0] + [0.0] * 13)),
        ("extreme_vpin_max", np.array([0.0, 0.0, 0.0, 0.0, 0.0, 400.0] + [0.0] * 8)),
        ("extreme_noise_max", np.array([0.0] * 13 + [400.0])),
        ("random_large_pos", np.random.uniform(10.0, 500.0, 14)),
        ("random_large_neg", np.random.uniform(-500.0, -10.0, 14)),
    ]

    for name, st in test_states:
        kf.x = st.copy()
        scale = kf.get_cost_scaling_factor()
        print(f"State '{name}': scale = {scale:.4f}")
        assert 0.20 <= scale <= 5.0, f"Scaling factor out of bounds for state '{name}': {scale}"
        assert math.isfinite(scale), f"Scaling factor is not finite for state '{name}': {scale}"

    print("All extreme boundary states strictly clamped to [0.20, 5.0] (PASS).")
    return {"status": "PASS"}


def verify_f938_gate9_physical_capital_conservation() -> dict:
    """Objective 2A: Stress test Gate 9 Physical Capital Conservation: 1,000 synthetic trading sequences."""
    print("\n" + "=" * 70)
    print("VERIFYING F938: Gate 9 Physical Capital Conservation (1,000 Sequences)")
    print("=" * 70)

    oms = ExecutionOMSEngine()
    rng = np.random.RandomState(2026)

    n_sequences = 1000
    violations_detected = 0
    valid_passes = 0
    invariance_failures = 0

    initial_capital = 100_000_000.0  # 100M KRW

    for seq in range(n_sequences):
        # Generate random equity state
        gross_equity = initial_capital * rng.uniform(0.5, 3.0)
        friction = rng.uniform(0.0, 500_000.0)
        cash = rng.uniform(0.0, gross_equity)

        # Decide whether this sequence is valid (Net <= Gross) or adversarial violation (Net > Gross)
        is_violating = (rng.rand() < 0.40)  # 40% chance of synthetic unbacked equity

        if is_violating:
            # Adversarial: Net Equity > Gross Equity (e.g. synthetic phantom profit / unbacked leverage)
            inflation = rng.uniform(1.0, 5_000_000.0)
            net_equity = gross_equity + inflation
        else:
            # Valid physical conservation: Net Equity = Gross Equity - friction - slippage
            net_equity = gross_equity - friction

        context = {
            "net_equity": net_equity,
            "gross_equity": gross_equity,
            "friction": friction,
            "available_cash": cash,
            "total_equity": gross_equity,
        }

        order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 10,
            "order_val": 700000.0,
            "weight": 0.01,
        }

        res = oms.evaluate_12_safety_gates(order, context=context)
        gate9_res = res["gate_results"]["gate9_capital_conservation"]

        if is_violating:
            # Must strictly reject!
            violations_detected += 1
            if res["passed"] or gate9_res["passed"]:
                invariance_failures += 1
                print(f"FAILED: Violating sequence {seq} passed Gate 9! Net={net_equity}, Gross={gross_equity}")
            if "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" not in res["rejection_reasons"]:
                invariance_failures += 1
                print(f"FAILED: Rejection reason missing for sequence {seq}")
        else:
            # Must pass Gate 9
            valid_passes += 1
            if not gate9_res["passed"]:
                invariance_failures += 1
                print(f"FAILED: Valid sequence {seq} failed Gate 9! Net={net_equity}, Gross={gross_equity}")

    print(f"Tested {n_sequences} synthetic trading sequences:")
    print(f"  Valid sequences tested: {valid_passes}")
    print(f"  Adversarial violations injected: {violations_detected}")
    print(f"  Invariance failures: {invariance_failures}")

    assert invariance_failures == 0, f"Gate 9 physical capital conservation invariance failed {invariance_failures} times!"
    print("Physical capital conservation invariant (Net Equity <= Gross Equity) 100% ENFORCED (PASS).")

    return {
        "n_sequences": n_sequences,
        "violations_detected": violations_detected,
        "valid_passes": valid_passes,
        "invariance_failures": invariance_failures,
        "status": "PASS",
    }


def verify_f938_12_safety_gates_boundary_stress() -> dict:
    """Objective 2B: Stress test all 12 safety gates with adversarial boundary cases."""
    print("\n" + "=" * 70)
    print("VERIFYING F938: 12 Safety Gates Adversarial Boundary Stress Test")
    print("=" * 70)

    oms = ExecutionOMSEngine()

    base_order = {
        "symbol": "005930",
        "price": 70000.0,
        "quantity": 100,
        "order_val": 7_000_000.0,
        "weight": 0.03,
        "sector": "Technology",
    }
    base_ctx = {
        "total_equity": 100_000_000.0,
        "net_equity": 100_000_000.0,
        "gross_equity": 100_000_000.0,
        "available_cash": 20_000_000.0,
        "adv": 10_000_000.0,
        "sector_weights": {"Technology": 0.15},
        "change_pct": 0.02,
        "expected_impact_bps": 10.0,
        "quote_age_ms": 50.0,
        "vpin": 0.20,
        "hawkes_intensity": 1.0,
        "settlement_days": 2,
        "collateral_ratio": 1.0,
        "currency_valid": True,
        "regime": "BULL_LOW_VOL",
    }

    # Baseline sanity check
    res = oms.evaluate_12_safety_gates(base_order, base_ctx)
    assert res["passed"], f"Baseline order failed: {res['rejection_reasons']}"
    assert len(res["passed_gates"]) == 12

    # Gate 1: Capital slice cap (<= 20M KRW)
    ord_g1_pass = dict(base_order, order_val=20_000_000.0)
    res_g1_pass = oms.evaluate_12_safety_gates(ord_g1_pass, base_ctx)
    assert res_g1_pass["gate_results"]["gate1_capital_slice"]

    ord_g1_fail = dict(base_order, order_val=20_000_001.0)
    res_g1_fail = oms.evaluate_12_safety_gates(ord_g1_fail, base_ctx)
    assert not res_g1_fail["gate_results"]["gate1_capital_slice"]
    assert "GATE1_MAX_SLICE_EXCEEDED" in res_g1_fail["rejection_reasons"]
    print("Gate 1 (Capital Slice <= 20M KRW): PASS")

    # Gate 2: Price validity (p > 0, finite)
    for bad_price in [0.0, -100.0, float("nan"), float("inf"), -float("inf")]:
        ord_g2 = dict(base_order, price=bad_price)
        res_g2 = oms.evaluate_12_safety_gates(ord_g2, base_ctx)
        assert not res_g2["gate_results"]["gate2_price_validity"]
        assert "GATE2_INVALID_PRICE" in res_g2["rejection_reasons"]
    print("Gate 2 (Positive Finite Price): PASS")

    # Gate 3: Single stock weight cap (<= 5.0%)
    ord_g3_pass = dict(base_order, weight=0.05)
    res_g3_pass = oms.evaluate_12_safety_gates(ord_g3_pass, base_ctx)
    assert res_g3_pass["gate_results"]["gate3_single_stock_weight"]

    ord_g3_fail = dict(base_order, weight=0.0501)
    res_g3_fail = oms.evaluate_12_safety_gates(ord_g3_fail, base_ctx)
    assert not res_g3_fail["gate_results"]["gate3_single_stock_weight"]
    assert "GATE3_WEIGHT_LIMIT_EXCEEDED" in res_g3_fail["rejection_reasons"]
    print("Gate 3 (Single Stock Weight <= 5.0%): PASS")

    # Gate 4: Circuit breaker price limit move (+/- 30%)
    # Limit is 29.5% (0.295 or 29.5)
    ctx_g4_pass = dict(base_ctx, change_pct=0.294)
    res_g4_pass = oms.evaluate_12_safety_gates(base_order, ctx_g4_pass)
    assert res_g4_pass["gate_results"]["gate4_circuit_breaker"]

    for bad_pct in [0.295, 0.30, -0.295, -0.30, 29.5, 30.0, -30.0]:
        ctx_g4_fail = dict(base_ctx, change_pct=bad_pct)
        res_g4_fail = oms.evaluate_12_safety_gates(base_order, ctx_g4_fail)
        assert not res_g4_fail["gate_results"]["gate4_circuit_breaker"]
        assert "GATE4_CIRCUIT_BREAKER_LIMIT" in res_g4_fail["rejection_reasons"]
    print("Gate 4 (Circuit Breaker Limit Move +/-30%): PASS")

    # Gate 5: Sector concentration cap (<= 25.0%)
    ctx_g5_pass = dict(base_ctx, sector_weights={"Technology": 0.250})
    res_g5_pass = oms.evaluate_12_safety_gates(base_order, ctx_g5_pass)
    assert res_g5_pass["gate_results"]["gate5_sector_concentration"]

    ctx_g5_fail = dict(base_ctx, sector_weights={"Technology": 0.2501})
    res_g5_fail = oms.evaluate_12_safety_gates(base_order, ctx_g5_fail)
    assert not res_g5_fail["gate_results"]["gate5_sector_concentration"]
    assert "GATE5_SECTOR_CONCENTRATION_EXCEEDED" in res_g5_fail["rejection_reasons"]
    print("Gate 5 (Sector Concentration <= 25.0%): PASS")

    # Gate 6: ADV participation cap (<= 1.5%)
    # adv = 10,000,000. 1.5% is 150,000 shares.
    ord_g6_pass = dict(base_order, quantity=150_000)
    res_g6_pass = oms.evaluate_12_safety_gates(ord_g6_pass, base_ctx)
    assert res_g6_pass["gate_results"]["gate6_adv_participation"]

    ord_g6_fail = dict(base_order, quantity=150_001)
    res_g6_fail = oms.evaluate_12_safety_gates(ord_g6_fail, base_ctx)
    assert not res_g6_fail["gate_results"]["gate6_adv_participation"]
    assert "GATE6_ADV_PARTICIPATION_EXCEEDED" in res_g6_fail["rejection_reasons"]
    print("Gate 6 (ADV Participation <= 1.5%): PASS")

    # Gate 7: Cash reserve margin (cash >= 5.0% of total equity)
    # total_equity = 100M, min reserve = 5M.
    ctx_g7_pass = dict(base_ctx, available_cash=5_000_000.0, cash_ratio=0.05)
    ord_g7_pass = dict(base_order, required_cash=0.0)
    res_g7_pass = oms.evaluate_12_safety_gates(ord_g7_pass, ctx_g7_pass)
    assert res_g7_pass["gate_results"]["gate7_cash_reserve"]

    ctx_g7_fail = dict(base_ctx, available_cash=4_999_999.0, cash_ratio=0.049)
    res_g7_fail = oms.evaluate_12_safety_gates(base_order, ctx_g7_fail)
    assert not res_g7_fail["gate_results"]["gate7_cash_reserve"]
    assert "GATE7_INSUFFICIENT_CASH_RESERVE" in res_g7_fail["rejection_reasons"]
    print("Gate 7 (Cash Reserve Margin >= 5.0%): PASS")

    # Gate 8: Crisis synthetic inverse hedge overlay
    ctx_g8 = dict(base_ctx, crisis_level="SEVERE")
    ord_g8_short = dict(base_order, action="SELL_SHORT")
    res_g8 = oms.evaluate_12_safety_gates(ord_g8_short, ctx_g8)
    assert res_g8["action_override"] == "CASH_OVERLAY"
    assert res_g8["info"] == "GATE8_CRISIS_INVERSE_HEDGE_OVERLAY"
    print("Gate 8 (Crisis Inverse Hedge Overlay): PASS")

    # Gate 10: Adverse market impact (<= 45.0 bps) & Stale quote latency (<= 500 ms)
    ord_g10_imp_pass = dict(base_order, expected_impact_bps=45.0, quote_age_ms=500.0)
    res_g10_imp_pass = oms.evaluate_12_safety_gates(ord_g10_imp_pass, base_ctx)
    assert res_g10_imp_pass["gate_results"]["gate10_adverse_impact_stale_quote"]["passed"]

    ord_g10_imp_fail = dict(base_order, expected_impact_bps=45.1, quote_age_ms=100.0)
    res_g10_imp_fail = oms.evaluate_12_safety_gates(ord_g10_imp_fail, base_ctx)
    assert not res_g10_imp_fail["gate_results"]["gate10_adverse_impact_stale_quote"]["passed_impact"]
    assert "GATE10_EXCESSIVE_MARKET_IMPACT" in res_g10_imp_fail["rejection_reasons"]

    ord_g10_stale_fail = dict(base_order, expected_impact_bps=10.0, quote_age_ms=500.1)
    res_g10_stale_fail = oms.evaluate_12_safety_gates(ord_g10_stale_fail, base_ctx)
    assert not res_g10_stale_fail["gate_results"]["gate10_adverse_impact_stale_quote"]["passed_stale_quote"]
    assert "GATE10_STALE_QUOTE_LATENCY" in res_g10_stale_fail["rejection_reasons"]
    print("Gate 10 (Adverse Impact <= 45 bps & Stale Quote <= 500 ms): PASS")

    # Gate 11: Real-time L3 Hawkes order flow toxicity (VPIN <= 0.82, Hawkes <= 5.0)
    ord_g11_pass = dict(base_order, vpin=0.82, hawkes_intensity=5.0)
    res_g11_pass = oms.evaluate_12_safety_gates(ord_g11_pass, base_ctx)
    assert res_g11_pass["gate_results"]["gate11_hawkes_vpin"]["passed"]

    ord_g11_vpin_fail = dict(base_order, vpin=0.8201, hawkes_intensity=1.0)
    res_g11_vpin_fail = oms.evaluate_12_safety_gates(ord_g11_vpin_fail, base_ctx)
    assert not res_g11_vpin_fail["gate_results"]["gate11_hawkes_vpin"]["passed_vpin"]
    assert "GATE11_VPIN_TOXICITY_BREACH" in res_g11_vpin_fail["rejection_reasons"]

    ord_g11_hwk_fail = dict(base_order, vpin=0.50, hawkes_intensity=5.01)
    res_g11_hwk_fail = oms.evaluate_12_safety_gates(ord_g11_hwk_fail, base_ctx)
    assert not res_g11_hwk_fail["gate_results"]["gate11_hawkes_vpin"]["passed_hawkes"]
    assert "GATE11_HAWKES_SURGE_BREACH" in res_g11_hwk_fail["rejection_reasons"]
    print("Gate 11 (VPIN Toxicity <= 0.82 & Hawkes Surge <= 5.0): PASS")

    # Gate 12: Cross-market settlement & collateral alignment (settlement <= 2, collateral >= 1.0, currency_valid=True)
    ord_g12_pass = dict(base_order, settlement_days=2, collateral_ratio=1.0, currency_valid=True)
    res_g12_pass = oms.evaluate_12_safety_gates(ord_g12_pass, base_ctx)
    assert res_g12_pass["gate_results"]["gate12_settlement_collateral"]["passed"]

    ord_g12_days_fail = dict(base_order, settlement_days=3, collateral_ratio=1.0, currency_valid=True)
    res_g12_days_fail = oms.evaluate_12_safety_gates(ord_g12_days_fail, base_ctx)
    assert "GATE12_INVALID_SETTLEMENT_CYCLE" in res_g12_days_fail["rejection_reasons"]

    ord_g12_collat_fail = dict(base_order, settlement_days=2, collateral_ratio=0.99, currency_valid=True)
    res_g12_collat_fail = oms.evaluate_12_safety_gates(ord_g12_collat_fail, base_ctx)
    assert "GATE12_INSUFFICIENT_COLLATERAL" in res_g12_collat_fail["rejection_reasons"]
    print("Gate 12 (Settlement <= T+2 & Collateral >= 1.0): PASS")

    return {"status": "PASS"}


def verify_f938_oms_per_order_latency_benchmark() -> dict:
    """Objective 2C: Benchmark end-to-end OMS per-order evaluation latency: verify SLA strictly < 1.5 ms."""
    print("\n" + "=" * 70)
    print("VERIFYING F938: OMS Per-Order Evaluation Latency SLA (< 1.5 ms)")
    print("=" * 70)

    oms = ExecutionOMSEngine()

    base_order = {
        "symbol": "005930",
        "price": 70000.0,
        "quantity": 100,
        "order_val": 7_000_000.0,
        "weight": 0.03,
        "sector": "Technology",
    }
    base_ctx = {
        "total_equity": 100_000_000.0,
        "net_equity": 100_000_000.0,
        "gross_equity": 100_000_000.0,
        "available_cash": 20_000_000.0,
        "adv": 10_000_000.0,
        "sector_weights": {"Technology": 0.15},
        "change_pct": 0.02,
        "expected_impact_bps": 10.0,
        "quote_age_ms": 50.0,
        "vpin": 0.20,
        "hawkes_intensity": 1.0,
        "settlement_days": 2,
        "collateral_ratio": 1.0,
        "currency_valid": True,
        "regime": "BULL_LOW_VOL",
    }

    # Warmup
    for _ in range(500):
        oms.evaluate_12_safety_gates(base_order, base_ctx)

    n_evals = 5000
    latencies_us = []

    t_total_0 = time.perf_counter()
    for _ in range(n_evals):
        t0 = time.perf_counter()
        oms.evaluate_12_safety_gates(base_order, base_ctx)
        dt = (time.perf_counter() - t0) * 1e6
        latencies_us.append(dt)
    t_total = time.perf_counter() - t_total_0

    latencies_us = np.array(latencies_us)
    mean_lat_ms = np.mean(latencies_us) / 1000.0
    median_lat_ms = np.median(latencies_us) / 1000.0
    p95_lat_ms = np.percentile(latencies_us, 95) / 1000.0
    p99_lat_ms = np.percentile(latencies_us, 99) / 1000.0
    max_lat_ms = np.max(latencies_us) / 1000.0

    print(f"Evaluated {n_evals} orders in {t_total:.3f} s:")
    print(f"  Mean latency:   {mean_lat_ms * 1000:.2f} us ({mean_lat_ms:.4f} ms)")
    print(f"  Median latency: {median_lat_ms * 1000:.2f} us ({median_lat_ms:.4f} ms)")
    print(f"  P95 latency:    {p95_lat_ms * 1000:.2f} us ({p95_lat_ms:.4f} ms)")
    print(f"  P99 latency:    {p99_lat_ms * 1000:.2f} us ({p99_lat_ms:.4f} ms)")
    print(f"  Max latency:    {max_lat_ms * 1000:.2f} us ({max_lat_ms:.4f} ms)")
    print(f"  SLA Target:     < 1.5000 ms")

    assert mean_lat_ms < 1.50, f"Mean latency {mean_lat_ms:.4f} ms exceeded SLA target 1.5 ms"
    assert p99_lat_ms < 1.50, f"P99 latency {p99_lat_ms:.4f} ms exceeded SLA target 1.5 ms"
    print("Latency SLA strictly met with high performance headroom (PASS).")

    return {
        "n_evals": n_evals,
        "mean_lat_ms": mean_lat_ms,
        "median_lat_ms": median_lat_ms,
        "p95_lat_ms": p95_lat_ms,
        "p99_lat_ms": p99_lat_ms,
        "max_lat_ms": max_lat_ms,
        "status": "PASS",
    }


def main():
    print("=" * 80)
    print("CHALLENGER 2: EMPIRICAL ADVERSARIAL STRESS SUITE (R182 MILESTONE M4)")
    print("=" * 80)

    results = {}
    try:
        results["f937_math"] = verify_f937_mathematical_joseph_stabilization()
        results["f937_5000_cycles"] = verify_f937_5000_cycle_adversarial_simulation()
        results["f937_bounds"] = verify_f937_dynamic_cost_scaling_bounds()
        results["f938_gate9"] = verify_f938_gate9_physical_capital_conservation()
        results["f938_12_gates"] = verify_f938_12_safety_gates_boundary_stress()
        results["f938_latency"] = verify_f938_oms_per_order_latency_benchmark()

        print("\n" + "=" * 80)
        print("ALL ADVERSARIAL STRESS CHALLENGES EMPIRICALLY VERIFIED AND PASSED!")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Adversarial test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

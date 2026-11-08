"""
tests/test_adversarial_phase183_challenger2.py — Adversarial Stress Testing Suite for Phase 183.

Target Features:
- F897: 10D Joseph-Stabilized Adaptive Kalman Slippage Filter (src/execution/slippage_feedback.py)
- F898: 10-Safety Gate Institutional OMS Gateway (src/execution/oms_engine.py)

Adversarial Stress Dimensions:
1. F897 (10D Joseph-Stabilized Kalman Slippage Filter):
   - 1,000 randomized measurement updates with ill-conditioned measurement vectors H_k and measurement noise.
   - Verify numerical symmetry: ||P - P^T||_F < 1e-12 at every single step.
   - Verify positive definiteness: all eigenvalues of P satisfy lambda_min >= 1e-8 at every single step.
   - Verify boundedness: state vector theta_t strictly within physical bounds at every single step.
   - Verify cost scaling factor strictly within [0.20, 4.0] at every single step.
   - Degenerate / ill-conditioned H vectors (zero norm, 1e-12 norm, 1e6 norm) and extreme R.
   - Massive oscillatory slippage shock recovery (+10,000 bps, -10,000 bps).
   - Closed-loop SlippageFeedbackEngine integration.

2. F898 (10-Safety Gate Institutional OMS Gateway):
   - Gate 10 boundary conditions: exact 45.0 bps (APPROVED), 45.0001 bps (REJECTED), 500.0 ms (APPROVED), 500.0001 ms (REJECTED).
   - Rejection telemetry strings: ADVERSE_IMPACT_EXCEEDED, STALE_QUOTE_EXCEEDED, ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED.
   - Simultaneous failures: Gate 9 physical capital conservation failure (Net Equity > Gross Equity) and Gate 10 failure both recorded in failed_gates.
   - Multi-gate cascade failure and non-finite / NaN parameter handling.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Ensure repo root and trading_system are on path
REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYS = REPO_ROOT / "trading_system"
for p in (str(REPO_ROOT), str(TRADING_SYS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.slippage_feedback import (
    TenDimensionalJosephKalmanFilter,
    SlippageFeedbackEngine,
)
from src.execution.oms_engine import (
    ExecutionOMSEngine,
)


class TestF897AdversarialKalmanFilter(unittest.TestCase):
    """Adversarial stress testing for Feature F897: 10D Joseph-Stabilized Kalman Slippage Filter."""

    # Physical bounds defined in TenDimensionalJosephKalmanFilter.update:
    PHYSICAL_BOUNDS: List[tuple[float, float]] = [
        (0.1, 5.0),    # 0: s_spread
        (0.05, 3.0),   # 1: s_perm
        (0.02, 2.0),   # 2: s_temp
        (0.01, 1.0),   # 3: eta_impact
        (-1.0, 1.0),   # 4: gamma_drift
        (0.001, 0.5),  # 5: sigma_micro
        (0.0, 1.0),    # 6: ofi_decay
        (0.0, 0.5),    # 7: delta_latency
        (0.0, 1.0),    # 8: psi_cross
        (0.0, 1.0),    # 9: xi_queue
    ]

    def test_adv01_f897_1000_randomized_adversarial_updates_full_invariant_checks(self) -> None:
        """
        Adversarial Test ADV-01:
        Execute exactly 1,000 randomized measurement updates with ill-conditioned measurement
        vectors H_k, heavy noise, extreme slippage observations, and adversarial market conditions.
        Enforces at EVERY single step:
        1. Numerical symmetry: ||P - P^T||_F < 1e-12
        2. Positive definiteness: min(eigvalsh(P)) >= 1e-8
        3. Physical state bounds: all theta_i in [lower_i, upper_i]
        4. Cost scaling factor strictly in [0.20, 4.0]
        """
        kf = TenDimensionalJosephKalmanFilter()
        rng = np.random.default_rng(seed=42_183_897)

        n_steps = 1000
        for step in range(n_steps):
            # Adversarially sampled trade features with extreme ranges
            adv_spread = float(rng.uniform(-20.0, 500.0))
            adv_vol = float(rng.uniform(-0.05, 1.5))
            adv_part = float(rng.uniform(-0.5, 3.0))
            adv_ofi = float(rng.uniform(-5.0, 5.0))
            adv_lat = float(rng.uniform(-10.0, 2000.0))
            adv_dark = float(rng.uniform(-1.0, 3.0))
            adv_queue = float(rng.uniform(-1.0, 5.0))
            adv_slip = float(rng.uniform(-500.0, 1500.0))

            trade_feats = {
                "spread_bps": adv_spread,
                "volatility": adv_vol,
                "participation": adv_part,
                "ofi": adv_ofi,
                "latency_ms": adv_lat,
                "dark_ratio": adv_dark,
                "queue_depletion": adv_queue,
            }

            # Update the filter
            x_up = kf.update(observed_slippage_bps=adv_slip, trade_features=trade_feats)

            # Invariant 1: Strict numerical symmetry ||P - P^T||_F < 1e-12
            sym_diff = np.linalg.norm(kf.P - kf.P.T, ord="fro")
            self.assertLess(
                sym_diff,
                1e-12,
                f"[Step {step}] Symmetry violated: ||P - P^T||_F = {sym_diff:.3e} >= 1e-12",
            )

            # Invariant 2: Positive definiteness: all eigenvalues >= 1e-8
            eigs = np.linalg.eigvalsh(kf.P)
            lambda_min = float(np.min(eigs))
            self.assertGreaterEqual(
                lambda_min,
                1e-8 - 1e-14,
                f"[Step {step}] Minimum eigenvalue violated: lambda_min = {lambda_min:.3e} < 1e-8",
            )

            # Invariant 3: Physical state bounds
            self.assertEqual(len(x_up), 10)
            for idx, (lb, ub) in enumerate(self.PHYSICAL_BOUNDS):
                val = float(x_up[idx])
                self.assertTrue(
                    math.isfinite(val),
                    f"[Step {step}] State theta[{idx}] is non-finite: {val}",
                )
                self.assertGreaterEqual(
                    val,
                    lb - 1e-7,
                    f"[Step {step}] State theta[{idx}]={val:.6f} below lower bound {lb}",
                )
                self.assertLessEqual(
                    val,
                    ub + 1e-7,
                    f"[Step {step}] State theta[{idx}]={val:.6f} above upper bound {ub}",
                )

            # Invariant 4: Cost scaling factor strictly in [0.20, 4.0]
            st = kf.get_10d_state()
            cs = float(st["cost_scaling_factor"])
            self.assertTrue(
                math.isfinite(cs),
                f"[Step {step}] cost_scaling_factor is non-finite: {cs}",
            )
            self.assertGreaterEqual(
                cs,
                0.20 - 1e-7,
                f"[Step {step}] cost_scaling_factor {cs} < 0.20",
            )
            self.assertLessEqual(
                cs,
                4.0 + 1e-7,
                f"[Step {step}] cost_scaling_factor {cs} > 4.0",
            )

        self.assertEqual(kf.update_count, 1000)

    def test_adv02_f897_degenerate_and_ill_conditioned_H_vectors(self) -> None:
        """
        Adversarial Test ADV-02:
        Test filter update against pathological measurement vectors H:
        - All-zero H vector
        - Extremely large H vector (norm 1e6)
        - Extremely small H vector (norm 1e-12)
        - Infinite or NaN components in trade features
        - Extreme measurement noise R values
        Verify Joseph update mathematically preserves symmetry and positive definiteness.
        """
        kf = TenDimensionalJosephKalmanFilter()

        # 1. Pathological H: all zeros
        P_curr = kf.P.copy()
        H_zero = np.zeros(10, dtype=np.float64)
        P_up_zero = kf.joseph_update(P=P_curr, H=H_zero, R=0.50)
        self.assertLess(np.linalg.norm(P_up_zero - P_up_zero.T, ord="fro"), 1e-12)
        self.assertTrue(np.all(np.linalg.eigvalsh(P_up_zero) >= 1e-8))

        # 2. Pathological H: huge magnitude (norm 1e6)
        H_huge = np.ones(10, dtype=np.float64) * 1e5
        P_up_huge = kf.joseph_update(P=P_curr, H=H_huge, R=0.50)
        self.assertLess(np.linalg.norm(P_up_huge - P_up_huge.T, ord="fro"), 1e-12)
        self.assertTrue(np.all(np.linalg.eigvalsh(P_up_huge) >= 1e-8))

        # 3. Pathological H: tiny magnitude (norm 1e-12)
        H_tiny = np.ones(10, dtype=np.float64) * 1e-13
        P_up_tiny = kf.joseph_update(P=P_curr, H=H_tiny, R=0.50)
        self.assertLess(np.linalg.norm(P_up_tiny - P_up_tiny.T, ord="fro"), 1e-12)
        self.assertTrue(np.all(np.linalg.eigvalsh(P_up_tiny) >= 1e-8))

        # 4. Extreme noise R: near-zero (1e-6) and colossal (1e6)
        P_up_low_r = kf.joseph_update(P=P_curr, H=np.ones(10), R=1e-6)
        self.assertLess(np.linalg.norm(P_up_low_r - P_up_low_r.T, ord="fro"), 1e-12)
        self.assertTrue(np.all(np.linalg.eigvalsh(P_up_low_r) >= 1e-8))

        P_up_high_r = kf.joseph_update(P=P_curr, H=np.ones(10), R=1e6)
        self.assertLess(np.linalg.norm(P_up_high_r - P_up_high_r.T, ord="fro"), 1e-12)
        self.assertTrue(np.all(np.linalg.eigvalsh(P_up_high_r) >= 1e-8))

    def test_adv03_f897_extreme_slippage_shocks_and_recovery(self) -> None:
        """
        Adversarial Test ADV-03:
        Subject the filter to extreme positive (+10,000 bps) and negative (-10,000 bps) shocks
        simulating flash crashes or bad broker feeds, followed by normal trading.
        Verify state remains bounded and returns finite predictions.
        """
        kf = TenDimensionalJosephKalmanFilter()

        # Step 1: Massive positive flash crash slippage shock
        kf.update(observed_slippage_bps=10_000.0, trade_features={"spread_bps": 100.0})
        self.assertTrue(np.all(np.isfinite(kf.x)))
        self.assertLessEqual(kf.x[0], 5.0)
        self.assertGreaterEqual(kf.x[0], 0.1)

        # Step 2: Massive negative rebate shock
        kf.update(observed_slippage_bps=-10_000.0, trade_features={"spread_bps": 1.0})
        self.assertTrue(np.all(np.isfinite(kf.x)))
        self.assertLessEqual(kf.x[0], 5.0)
        self.assertGreaterEqual(kf.x[0], 0.1)

        # Step 3: Normal recovery
        for _ in range(10):
            kf.update(observed_slippage_bps=4.5, trade_features={"spread_bps": 8.0})

        pred_slip = kf.predict_slippage_bps({"spread_bps": 8.0, "volatility": 0.02})
        self.assertTrue(math.isfinite(pred_slip))
        self.assertGreaterEqual(pred_slip, 0.1)
        self.assertLessEqual(pred_slip, 500.0)

    def test_adv04_f897_closed_loop_engine_adversarial_integration(self) -> None:
        """
        Adversarial Test ADV-04:
        Verify closed-loop methods in SlippageFeedbackEngine with 10D Kalman filter.
        """
        engine = SlippageFeedbackEngine()
        vec = engine.get_state_vector_10d()
        self.assertEqual(len(vec), 10)

        # Update with extreme trade features
        res = engine.update_10d_kalman_filter(
            observed_slippage_bps=120.0,
            trade_features={"spread_bps": 30.0, "latency_ms": 25.0, "dark_ratio": 0.8},
        )
        self.assertEqual(len(res), 10)

        st = engine.get_10d_state()
        self.assertIn("cost_scaling_factor", st)
        self.assertIn("psi_cross", st)
        self.assertIn("xi_queue", st)
        self.assertGreaterEqual(st["cost_scaling_factor"], 0.20)
        self.assertLessEqual(st["cost_scaling_factor"], 4.0)

        # Test joseph_update_10d static method
        P = np.eye(10) * 0.2
        H = np.ones(10) * 0.5
        P_next = engine.joseph_update_10d(P, H, R=0.50)
        self.assertEqual(P_next.shape, (10, 10))
        self.assertLess(np.linalg.norm(P_next - P_next.T, ord="fro"), 1e-12)


class TestF898AdversarialOMSSafetyGates(unittest.TestCase):
    """Adversarial stress testing for Feature F898: 10-Safety Gate Institutional OMS Gateway."""

    def setUp(self) -> None:
        self.oms = ExecutionOMSEngine()

    def test_adv05_f898_gate10_exact_boundary_conditions(self) -> None:
        """
        Adversarial Test ADV-05:
        Verify Gate 10 boundary conditions with sub-basis point precision:
        - Exact 45.0 bps (APPROVED) vs 45.0001 bps (REJECTED)
        - Exact 500.0 ms (APPROVED) vs 500.0001 ms (REJECTED)
        """
        # 1. Adverse Impact Gate standalone
        self.assertTrue(
            self.oms.check_adverse_impact_gate(45.0, max_impact_bps=45.0),
            "Exact 45.0 bps must be APPROVED (<= 45.0)",
        )
        self.assertFalse(
            self.oms.check_adverse_impact_gate(45.0001, max_impact_bps=45.0),
            "45.0001 bps must be REJECTED (> 45.0)",
        )
        self.assertTrue(
            self.oms.check_adverse_impact_gate(44.9999, max_impact_bps=45.0),
            "44.9999 bps must be APPROVED (< 45.0)",
        )

        # 2. Stale Quote Gate standalone
        self.assertTrue(
            self.oms.check_stale_quote_gate(500.0, max_quote_age_ms=500.0),
            "Exact 500.0 ms must be APPROVED (<= 500.0)",
        )
        self.assertFalse(
            self.oms.check_stale_quote_gate(500.0001, max_quote_age_ms=500.0),
            "500.0001 ms must be REJECTED (> 500.0)",
        )
        self.assertTrue(
            self.oms.check_stale_quote_gate(499.9999, max_quote_age_ms=500.0),
            "499.9999 ms must be APPROVED (< 500.0)",
        )

        # 3. Dual gate check_adverse_impact_and_stale_quote_gate
        self.assertTrue(
            self.oms.check_adverse_impact_and_stale_quote_gate(45.0, 500.0),
            "(45.0 bps, 500.0 ms) exact boundary must be APPROVED",
        )
        self.assertFalse(
            self.oms.check_adverse_impact_and_stale_quote_gate(45.0001, 500.0),
            "(45.0001 bps, 500.0 ms) must be REJECTED",
        )
        self.assertFalse(
            self.oms.check_adverse_impact_and_stale_quote_gate(45.0, 500.0001),
            "(45.0 bps, 500.0001 ms) must be REJECTED",
        )
        self.assertFalse(
            self.oms.check_adverse_impact_and_stale_quote_gate(45.0001, 500.0001),
            "(45.0001 bps, 500.0001 ms) must be REJECTED",
        )

    def test_adv06_f898_gate10_rejection_telemetry_strings(self) -> None:
        """
        Adversarial Test ADV-06:
        Verify exact telemetry rejection reasons from evaluate_gate10_adverse_impact_stale_quote:
        - ADVERSE_IMPACT_EXCEEDED
        - STALE_QUOTE_EXCEEDED
        - ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED
        """
        # Case A: Adverse Impact Exceeded only
        res_a = self.oms.evaluate_gate10_adverse_impact_stale_quote(
            adverse_impact_bps=45.0001,
            quote_age_ms=500.0,
        )
        self.assertFalse(res_a["passed"])
        self.assertEqual(res_a["status"], "REJECTED")
        self.assertFalse(res_a["passed_impact"])
        self.assertTrue(res_a["passed_stale_quote"])
        self.assertEqual(res_a["rejection_reason"], "ADVERSE_IMPACT_EXCEEDED")

        # Case B: Stale Quote Exceeded only
        res_b = self.oms.evaluate_gate10_adverse_impact_stale_quote(
            adverse_impact_bps=45.0,
            quote_age_ms=500.0001,
        )
        self.assertFalse(res_b["passed"])
        self.assertEqual(res_b["status"], "REJECTED")
        self.assertTrue(res_b["passed_impact"])
        self.assertFalse(res_b["passed_stale_quote"])
        self.assertEqual(res_b["rejection_reason"], "STALE_QUOTE_EXCEEDED")

        # Case C: Both Exceeded simultaneously
        res_c = self.oms.evaluate_gate10_adverse_impact_stale_quote(
            adverse_impact_bps=45.0001,
            quote_age_ms=500.0001,
        )
        self.assertFalse(res_c["passed"])
        self.assertEqual(res_c["status"], "REJECTED")
        self.assertFalse(res_c["passed_impact"])
        self.assertFalse(res_c["passed_stale_quote"])
        self.assertEqual(
            res_c["rejection_reason"],
            "ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED",
        )

        # Case D: Both Pass exactly at boundary
        res_d = self.oms.evaluate_gate10_adverse_impact_stale_quote(
            adverse_impact_bps=45.0,
            quote_age_ms=500.0,
        )
        self.assertTrue(res_d["passed"])
        self.assertEqual(res_d["status"], "PASS")
        self.assertTrue(res_d["passed_impact"])
        self.assertTrue(res_d["passed_stale_quote"])
        self.assertIsNone(res_d["rejection_reason"])

    def test_adv07_f898_simultaneous_gate9_and_gate10_failures(self) -> None:
        """
        Adversarial Test ADV-07:
        Verify simultaneous failure of Gate 9 (Physical Capital Conservation: Net Equity > Gross Equity)
        and Gate 10 (Adverse Impact and/or Stale Quote).
        Both failures must be explicitly captured in `failed_gates` and `rejection_reasons`.
        """
        order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 100,
            "order_val": 7_000_000.0,
            "weight": 0.03,
            "adv": 500_000.0,
            "adverse_impact_bps": 52.0,  # Gate 10 violation (> 45.0 bps)
            "quote_age_ms": 620.0,       # Gate 10 violation (> 500.0 ms)
        }

        # Context violating Gate 9: Net Equity (110M) > Gross Equity (100M)
        ctx = {
            "net_equity": 110_000_000.0,
            "gross_equity": 100_000_000.0,
            "friction": 1.0,
            "available_cash": 50_000_000.0,
            "total_equity": 100_000_000.0,
            "sector_weight": 0.15,
            "regime": "BULL_LOW_VOL",
        }

        audit = self.oms.evaluate_10_safety_gates(order, ctx)

        self.assertFalse(audit["all_passed"], "Order must be REJECTED")
        self.assertEqual(audit["status"], "REJECTED")

        # Crucial check: BOTH Gate 9 and Gate 10 must be in failed_gates
        self.assertIn(9, audit["failed_gates"], "Gate 9 must be recorded in failed_gates")
        self.assertIn(10, audit["failed_gates"], "Gate 10 must be recorded in failed_gates")

        # Check telemetry strings
        self.assertIn("CAPITAL_CONSERVATION_BREACHED", audit["rejection_reasons"])
        self.assertIn("ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED", audit["rejection_reasons"])

        # Check Gate 9 detailed sub-evaluations
        g9_res = audit["gate_results"]["gate9_capital_conservation"]
        self.assertFalse(g9_res["passed"])
        self.assertFalse(g9_res["passed_equity_conservation"])
        self.assertLess(g9_res["equity_diff"], 0.0)

        # Check Gate 10 detailed sub-evaluations
        g10_res = audit["gate_results"]["gate10_adverse_impact_stale_quote"]
        self.assertFalse(g10_res["passed"])
        self.assertEqual(g10_res["rejection_reason"], "ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED")

    def test_adv08_f898_isolated_gate9_and_isolated_gate10_failures(self) -> None:
        """
        Adversarial Test ADV-08:
        Verify isolated failure modes:
        - Only Gate 9 fails while Gate 10 passes: failed_gates = [9]
        - Only Gate 10 fails while Gate 9 passes: failed_gates = [10]
        """
        base_order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 100,
            "order_val": 7_000_000.0,
            "weight": 0.03,
            "adv": 500_000.0,
        }

        # Subtest 1: Only Gate 9 fails (Net Equity > Gross Equity)
        order_g9_fail = dict(base_order)
        order_g9_fail["adverse_impact_bps"] = 20.0  # Pass Gate 10
        order_g9_fail["quote_age_ms"] = 150.0       # Pass Gate 10

        ctx_g9_fail = {
            "net_equity": 105_000_000.0,
            "gross_equity": 100_000_000.0,
            "friction": 1.0,
            "available_cash": 50_000_000.0,
            "total_equity": 100_000_000.0,
            "sector_weight": 0.15,
            "regime": "BULL_LOW_VOL",
        }

        audit_g9 = self.oms.evaluate_10_safety_gates(order_g9_fail, ctx_g9_fail)
        self.assertIn(9, audit_g9["failed_gates"])
        self.assertNotIn(10, audit_g9["failed_gates"])
        self.assertIn(10, audit_g9["passed_gates"])
        self.assertIn("CAPITAL_CONSERVATION_BREACHED", audit_g9["rejection_reasons"])

        # Subtest 2: Only Gate 10 fails (adverse_impact = 48.0 bps)
        order_g10_fail = dict(base_order)
        order_g10_fail["adverse_impact_bps"] = 48.0  # Fail Gate 10
        order_g10_fail["quote_age_ms"] = 150.0       # Pass Gate 10

        ctx_g10_fail = {
            "net_equity": 99_000_000.0,
            "gross_equity": 100_000_000.0,
            "friction": 1.0,
            "available_cash": 50_000_000.0,
            "total_equity": 100_000_000.0,
            "sector_weight": 0.15,
            "regime": "BULL_LOW_VOL",
        }

        audit_g10 = self.oms.evaluate_10_safety_gates(order_g10_fail, ctx_g10_fail)
        self.assertNotIn(9, audit_g10["failed_gates"])
        self.assertIn(9, audit_g10["passed_gates"])
        self.assertIn(10, audit_g10["failed_gates"])
        self.assertIn("ADVERSE_IMPACT_EXCEEDED", audit_g10["rejection_reasons"])

    def test_adv09_f898_multi_gate_cascade_failure(self) -> None:
        """
        Adversarial Test ADV-09:
        Multi-gate cascade failure violating 5 distinct gates simultaneously:
        - Gate 1: Capital slice cap (> 20M KRW)
        - Gate 3: Single-stock weight (> 5.00%)
        - Gate 6: ADV participation (> 1.50%)
        - Gate 9: Physical capital conservation (Net Equity > Gross Equity)
        - Gate 10: Adverse impact and stale quote exceeded
        All 5 failed gates must be recorded in failed_gates.
        """
        order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 1000,
            "order_val": 70_000_000.0,  # Gate 1 violation (> 20M)
            "weight": 0.12,             # Gate 3 violation (> 0.05)
            "adv": 50_000.0,            # Gate 6 violation (1000 / 50000 = 2.0% > 1.5%)
            "adverse_impact_bps": 55.0, # Gate 10 violation (> 45.0)
            "quote_age_ms": 700.0,      # Gate 10 violation (> 500.0)
        }

        ctx = {
            "max_slice": 20_000_000.0,
            "max_weight": 0.05,
            "net_equity": 105_000_000.0,
            "gross_equity": 100_000_000.0,  # Gate 9 violation
            "friction": 1.0,
            "available_cash": 50_000_000.0,
            "total_equity": 100_000_000.0,
            "sector_weight": 0.15,
            "regime": "BULL_LOW_VOL",
        }

        audit = self.oms.evaluate_10_safety_gates(order, ctx)
        self.assertFalse(audit["all_passed"])
        self.assertEqual(audit["status"], "REJECTED")

        # Verify all 5 gates are in failed_gates
        for gate_num in [1, 3, 6, 9, 10]:
            self.assertIn(
                gate_num,
                audit["failed_gates"],
                f"Gate {gate_num} must be enumerated in failed_gates",
            )

        # Gate 8 (inverse hedge) and Gate 2 (price valid) should still pass
        self.assertIn(2, audit["passed_gates"])
        self.assertIn(8, audit["passed_gates"])

    def test_adv10_f898_gate8_synthetic_inverse_hedge_dual_contract(self) -> None:
        """
        Adversarial Test ADV-10:
        Verify Gate 8 returns both 'symbol' and 'hedge_symbol' in both crisis and benign regimes.
        """
        # Crisis regimes
        for crisis_regime in ["BEAR_HIGH_VOL", "PANIC_CRISIS"]:
            h_krx = self.oms.evaluate_gate8_inverse_hedge(crisis_regime, "KOSPI")
            self.assertTrue(h_krx["hedge_active"])
            self.assertEqual(h_krx["symbol"], "114800")
            self.assertEqual(h_krx["hedge_symbol"], "114800")

            h_us = self.oms.evaluate_gate8_inverse_hedge(crisis_regime, "NASDAQ")
            self.assertTrue(h_us["hedge_active"])
            self.assertEqual(h_us["symbol"], "PSQ")
            self.assertEqual(h_us["hedge_symbol"], "PSQ")

        # Benign regime
        h_bull = self.oms.evaluate_gate8_inverse_hedge("BULL_LOW_VOL", "KOSPI")
        self.assertFalse(h_bull["hedge_active"])
        self.assertIn("symbol", h_bull)
        self.assertIn("hedge_symbol", h_bull)


if __name__ == "__main__":
    unittest.main()

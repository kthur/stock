"""
Empirical Challenger Test Suite for Milestone 4:
Adversarial Stress Testing of Gate 11 (IRR) and Gate 12 (Factor Crowding Shock).

Specifications:
- docs/MULTI_FACTOR_ARCHITECTURAL_FEASIBILITY_REPORT.md §5.5
- ORIGINAL_REQUEST.md §R4
- sub_orch_m4/SCOPE.md

Coverage:
1. Extreme / Asymptotic Inputs (Zero weights, 10^9 huge magnitude weights,
   non-normalized weights, negative idiosyncratic variances, singular/indefinite Omega_F).
2. Exact Precision Boundary Testing (IRR = 0.700000000, 0.699999999, 0.700000001).
3. Scale Invariance and Mathematical Consistency of IRR.
4. Monte Carlo 500-Run Random Portfolios (varying N in [1, 500], K in [1, 20]).
5. Covariance Matrix Decomposition Fallbacks and Mismatched Shapes.
6. Dimension Resilience (D padding/truncation, 1D vs 2D, B 1D reshaping).
7. NaN/Inf Sanitization across all array and scalar inputs.
8. Factor Crowding Shock Z Stress (-100, 0, 2.999999, 3.000000, 3.000001, 100, NaN, Inf, -Inf, strings, None, non-primitives).
9. Integration with Batch Evaluator and Almgren-Chriss TWAP Trajectory.
10. System-wide Invariant: synthetic_rows == 0 strictly verified as native int 0.
"""

import math
import unittest
import numpy as np
from typing import Dict, Any

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    AlmgrenChrissScheduler,
    check_gate11_idiosyncratic_risk_ratio,
    check_gate12_factor_crowding_shock,
    evaluate_gate11_and_gate12,
)


class TestM4Challenger1Gate11Stress(unittest.TestCase):
    """Adversarial and asymptotic stress testing for Gate 11 (Idiosyncratic Risk Ratio)."""

    def setUp(self):
        np.random.seed(42)

    def test_gate11_weights_all_zeros(self):
        """Asymptotic test: portfolio weights are all zeros."""
        for N in [1, 5, 50, 200]:
            K = 3
            w = np.zeros(N, dtype=np.float64)
            B = np.random.randn(N, K)
            Omega = np.eye(K, dtype=np.float64)
            D = np.ones(N, dtype=np.float64) * 0.05

            passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
                w_target=w,
                B_loadings=B,
                Omega_F=Omega,
                D_idio=D,
                min_irr=0.70,
            )
            # When total risk is zero, should safely return True, 1.0 without crashing
            self.assertTrue(passed, f"Failed on zero weights N={N}")
            self.assertEqual(irr, 1.0)
            self.assertIn("Zero/negligible total risk", reason)

    def test_gate11_weights_huge_magnitude_and_overflow(self):
        """
        Stress test: portfolio weights with extreme magnitude (10^9 to 10^150).
        Verifies numerical stability, scale invariance, and no overflow crash.
        """
        N = 5
        K = 2
        w_base = np.array([0.2, 0.3, -0.1, 0.4, -0.2], dtype=np.float64)
        B = np.array([
            [1.0, 0.5],
            [0.2, 0.8],
            [0.5, -0.3],
            [0.8, 0.1],
            [-0.4, 0.6],
        ], dtype=np.float64)
        Omega = np.array([[0.04, 0.01], [0.01, 0.06]], dtype=np.float64)
        D = np.array([0.05, 0.08, 0.03, 0.07, 0.04], dtype=np.float64)

        pass_base, irr_base, _ = check_gate11_idiosyncratic_risk_ratio(
            w_base, B, Omega, D, min_irr=0.70
        )

        # Scale weights by 10^9
        w_huge_1e9 = w_base * 1e9
        pass_huge, irr_huge, _ = check_gate11_idiosyncratic_risk_ratio(
            w_huge_1e9, B, Omega, D, min_irr=0.70
        )
        self.assertEqual(pass_base, pass_huge)
        self.assertAlmostEqual(irr_base, irr_huge, places=7)

        # Scale weights by 10^150 (float64 square is 10^300, close to max float64 1.8e308)
        w_huge_1e150 = w_base * 1e150
        pass_150, irr_150, _ = check_gate11_idiosyncratic_risk_ratio(
            w_huge_1e150, B, Omega, D, min_irr=0.70
        )
        self.assertTrue(np.isfinite(irr_150))
        self.assertTrue(0.0 <= irr_150 <= 1.0)

        # Extreme magnitude 10^200 which causes float64 square to overflow to inf
        w_overflow = w_base * 1e200
        pass_inf, irr_inf, reason_inf = check_gate11_idiosyncratic_risk_ratio(
            w_overflow, B, Omega, D, min_irr=0.70
        )
        # Should catch non-finite gracefully
        self.assertTrue(pass_inf)
        self.assertEqual(irr_inf, 1.0)
        self.assertIn("Zero/negligible total risk: safe default", reason_inf)

    def test_gate11_non_normalized_weights_scale_invariance(self):
        """
        Verify that IRR is mathematically scale-invariant:
        IRR(c * w) == IRR(w) for any positive scalar c.
        """
        N = 8
        K = 3
        w = np.random.randn(N)  # Arbitrary non-normalized weights
        B = np.random.randn(N, K)
        A = np.random.randn(K, K)
        Omega = A @ A.T + np.eye(K) * 0.01
        D = np.random.exponential(scale=0.05, size=N) + 0.001

        pass_orig, irr_orig, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D)

        for scalar in [1e-6, 0.01, 2.5, 100.0, 77777.7]:
            w_scaled = w * scalar
            pass_scaled, irr_scaled, _ = check_gate11_idiosyncratic_risk_ratio(
                w_scaled, B, Omega, D
            )
            self.assertEqual(pass_orig, pass_scaled, f"Scale broken at scalar {scalar}")
            self.assertAlmostEqual(
                irr_orig, irr_scaled, places=7,
                msg=f"IRR scale invariance broken at scalar {scalar}: {irr_orig} vs {irr_scaled}"
            )

    def test_gate11_negative_idiosyncratic_variances(self):
        """
        Stress test: D_idio contains negative elements.
        The implementation must rectify negative variances (D >= 0) via np.maximum(D, 0.0)
        and must never produce negative idiosyncratic variance or IRR out of [0, 1].
        """
        N = 6
        K = 2
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        Omega = np.eye(K) * 0.05

        # Partially negative D
        D_mixed = np.array([-0.05, 0.08, -0.12, 0.04, -0.01, 0.10])
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D_mixed)
        self.assertTrue(np.isfinite(irr))
        self.assertTrue(0.0 <= irr <= 1.0)

        # Entirely negative D
        D_all_neg = np.array([-0.05, -0.08, -0.12, -0.04, -0.01, -0.10])
        passed_neg, irr_neg, reason_neg = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega, D_all_neg
        )
        self.assertFalse(passed_neg)
        self.assertEqual(irr_neg, 0.0)
        self.assertIn("Gate 11 Breached", reason_neg)

    def test_gate11_singular_and_indefinite_factor_covariance(self):
        """
        Stress test: Omega_F is singular (zeros, rank 1) or has negative eigenvalues.
        Spectral clipping must project Omega to PSD cone without raising linear algebra errors.
        """
        N = 5
        K = 3
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        D = np.ones(N) * 0.05

        # 1. Omega is all zeros (singular rank 0)
        Omega_zero = np.zeros((K, K))
        passed_z, irr_z, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_zero, D)
        # Factor risk is 0, all risk is idiosyncratic => IRR = 1.0 => PASS
        self.assertTrue(passed_z)
        self.assertEqual(irr_z, 1.0)

        # 2. Omega is rank 1 (singular for K=3)
        v = np.array([[1.0], [2.0], [-1.0]])
        Omega_rank1 = v @ v.T  # Rank 1 matrix
        passed_r1, irr_r1, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_rank1, D)
        self.assertTrue(np.isfinite(irr_r1))
        self.assertTrue(0.0 <= irr_r1 <= 1.0)

        # 3. Omega has negative eigenvalues (non-PSD)
        Omega_neg_eig = np.array([
            [-0.10, 0.02, 0.01],
            [0.02, -0.05, 0.00],
            [0.01, 0.00, 0.08],
        ])
        passed_neg, irr_neg, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_neg_eig, D)
        self.assertTrue(np.isfinite(irr_neg))
        self.assertTrue(0.0 <= irr_neg <= 1.0)

    def test_gate11_exact_precision_boundary(self):
        """
        Exact precision testing:
        - IRR = 0.700000000 -> PASS
        - IRR = 0.699999999 -> FAIL
        - IRR = 0.700000001 -> PASS
        """
        w = np.array([1.0], dtype=np.float64)
        B = np.array([[1.0]], dtype=np.float64)

        # Target 1: 0.700000000
        Omega_700 = np.array([[0.300000000]], dtype=np.float64)
        D_700 = np.array([0.700000000], dtype=np.float64)
        p_700, irr_700, r_700 = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_700, D_700, min_irr=0.70
        )
        self.assertTrue(p_700, f"0.700000000 should pass, got {p_700}")
        self.assertAlmostEqual(irr_700, 0.700000000, places=9)
        self.assertEqual(r_700, "PASSED")

        # Target 2: 0.699999999
        Omega_sub = np.array([[0.300000001]], dtype=np.float64)
        D_sub = np.array([0.699999999], dtype=np.float64)
        p_sub, irr_sub, r_sub = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_sub, D_sub, min_irr=0.70
        )
        self.assertFalse(p_sub, f"0.699999999 should fail, got {p_sub}")
        self.assertAlmostEqual(irr_sub, 0.699999999, places=9)
        self.assertIn("Gate 11 Breached", r_sub)

        # Target 3: 0.700000001
        Omega_sup = np.array([[0.299999999]], dtype=np.float64)
        D_sup = np.array([0.700000001], dtype=np.float64)
        p_sup, irr_sup, r_sup = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_sup, D_sup, min_irr=0.70
        )
        self.assertTrue(p_sup, f"0.700000001 should pass, got {p_sup}")
        self.assertAlmostEqual(irr_sup, 0.700000001, places=9)
        self.assertEqual(r_sup, "PASSED")

    def test_gate11_monte_carlo_500_random_portfolios(self):
        """
        Monte Carlo stress testing:
        Generate 500 random factor portfolios with varying N in [1, 500] and K in [1, 20].
        Invariants to verify:
        - IRR is strictly in [0.0, 1.0]
        - IRR is finite (no NaN, no Inf)
        - No division by zero or unhandled exceptions
        - passed == (round(irr, 9) >= round(min_irr, 9))
        """
        n_simulations = 500
        rng = np.random.default_rng(2026)

        for i in range(n_simulations):
            # Sample N and K
            N = int(rng.integers(1, 501))
            K = int(rng.integers(1, 21))

            # Mix of portfolio weight styles
            weight_style = i % 5
            if weight_style == 0:
                # Standard normalized long-only
                w = rng.uniform(0.01, 1.0, size=N)
                w /= np.sum(w)
            elif weight_style == 1:
                # Long-short dollar neutral
                w = rng.standard_normal(size=N)
                w -= np.mean(w)
                denom = np.sum(np.abs(w))
                if denom > 1e-12:
                    w /= denom
            elif weight_style == 2:
                # Extremely sparse portfolio (e.g. 3 active assets)
                w = np.zeros(N, dtype=np.float64)
                active_idx = rng.choice(N, size=min(3, N), replace=False)
                w[active_idx] = rng.uniform(0.1, 1.0, size=len(active_idx))
                w /= np.sum(w)
            elif weight_style == 3:
                # Arbitrary non-normalized weights with large values
                w = rng.standard_normal(size=N) * 1e4
            else:
                # All zeros or near-zero
                w = np.zeros(N, dtype=np.float64)

            # Random factor loadings
            B = rng.standard_normal(size=(N, K))

            # Factor covariance (PSD with random eigenvalues, occasional negative perturbation)
            A = rng.standard_normal(size=(K, K))
            Omega = (A @ A.T) / K
            if i % 10 == 0:
                # Adversarially add negative diagonal element
                Omega[0, 0] = -0.05

            # Idiosyncratic variance (positive, occasional negative/zero values)
            if i % 15 == 0:
                D = rng.uniform(-0.02, 0.10, size=N)
            else:
                D = rng.exponential(scale=0.05, size=N)

            # Random threshold min_irr in [0.50, 0.85]
            min_irr = float(rng.uniform(0.50, 0.85))

            passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
                w_target=w,
                B_loadings=B,
                Omega_F=Omega,
                D_idio=D,
                min_irr=min_irr,
            )

            # Assert invariants
            self.assertTrue(np.isfinite(irr), f"Run {i}: IRR not finite: {irr}")
            self.assertGreaterEqual(irr, 0.0, f"Run {i}: IRR < 0: {irr}")
            self.assertLessEqual(irr, 1.0, f"Run {i}: IRR > 1: {irr}")
            self.assertIsInstance(passed, bool, f"Run {i}: passed is not bool: {type(passed)}")

            expected_pass = bool(round(irr, 9) >= round(min_irr, 9))
            self.assertEqual(
                passed, expected_pass,
                f"Run {i}: decision mismatch: passed={passed}, expected={expected_pass}, irr={irr}, min_irr={min_irr}"
            )
            self.assertTrue(len(reason) > 0, f"Run {i}: empty reason string")

    def test_gate11_cov_matrix_path_and_mismatched_shape(self):
        """
        Verify behavior when full covariance matrix cov_matrix is supplied:
        - When valid (N, N): extracts Omega via GLS pinv and D via residual variance.
        - When mismatched shape != (N, N): falls back safely to D=0 => IRR=0 => breaches Gate 11.
        """
        N = 4
        K = 2
        w = np.ones(N) / N
        B = np.random.randn(N, K)

        # Valid covariance matrix
        cov_valid = np.eye(N) * 0.1 + 0.01
        passed_v, irr_v, _ = check_gate11_idiosyncratic_risk_ratio(
            w, B, cov_matrix=cov_valid, min_irr=0.70
        )
        self.assertTrue(np.isfinite(irr_v))
        self.assertTrue(0.0 <= irr_v <= 1.0)

        # Mismatched shape covariance matrix (e.g. 3x3 for N=4)
        cov_mismatch = np.eye(3) * 0.1
        passed_m, irr_m, reason_m = check_gate11_idiosyncratic_risk_ratio(
            w, B, cov_matrix=cov_mismatch, min_irr=0.70
        )
        # Should breach safely because D falls back to zeros => idio_var = 0 => IRR = 0
        self.assertFalse(passed_m)
        self.assertEqual(irr_m, 0.0)
        self.assertIn("Gate 11 Breached", reason_m)

    def test_gate11_d_idio_dimension_resilience(self):
        """
        Verify D_idio dimension resilience:
        - D length < N: padded with zeros.
        - D length > N: truncated to N.
        - D as 2D diagonal matrix vs 1D vector.
        """
        N = 5
        K = 2
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        Omega = np.eye(K) * 0.04

        # Short D (length 3 < 5)
        D_short = np.array([0.08, 0.10, 0.06])
        p_sh, irr_sh, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D_short)
        self.assertTrue(np.isfinite(irr_sh))
        self.assertTrue(0.0 <= irr_sh <= 1.0)

        # Long D (length 8 > 5)
        D_long = np.array([0.08, 0.10, 0.06, 0.09, 0.07, 0.12, 0.05, 0.11])
        p_lg, irr_lg, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D_long)
        self.assertTrue(np.isfinite(irr_lg))
        self.assertTrue(0.0 <= irr_lg <= 1.0)

        # 2D diagonal matrix
        D_diag_mat = np.diag(D_long[:N])
        p_mat, irr_mat, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D_diag_mat)
        self.assertEqual(p_lg, p_mat)
        self.assertAlmostEqual(irr_lg, irr_mat, places=9)

    def test_gate11_nan_inf_sanitization_in_arrays(self):
        """
        Verify that NaN, Inf, and -Inf values embedded within numpy arrays are sanitized
        via np.nan_to_num and do not crash or produce NaN outputs.
        """
        N = 4
        K = 2
        w_nan = np.array([0.25, np.nan, 0.25, np.inf])
        B_nan = np.array([
            [1.0, np.nan],
            [np.inf, -0.5],
            [-np.inf, 0.3],
            [0.2, 0.8],
        ])
        Omega_nan = np.array([
            [np.nan, 0.01],
            [0.01, np.inf],
        ])
        D_nan = np.array([np.nan, 0.05, np.inf, -np.inf])

        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w_target=w_nan,
            B_loadings=B_nan,
            Omega_F=Omega_nan,
            D_idio=D_nan,
            min_irr=float("nan"),  # Should fallback to 0.70
        )
        self.assertTrue(np.isfinite(irr))
        self.assertTrue(0.0 <= irr <= 1.0)
        self.assertIsInstance(passed, bool)

    def test_gate11_b_loadings_1d_handling(self):
        """Verify 1D vector B_loadings of length N is cleanly reshaped to (N, 1)."""
        N = 4
        w = np.ones(N) / N
        B_1d = np.array([0.5, 0.8, -0.3, 0.2])
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w, B_1d, Omega_F=np.array([[0.05]]), D_idio=np.ones(N) * 0.05
        )
        self.assertTrue(np.isfinite(irr))
        self.assertTrue(0.0 <= irr <= 1.0)


class TestM4Challenger1Gate12Stress(unittest.TestCase):
    """Adversarial stress testing for Gate 12 (Factor Crowding Shock Circuit Breaker)."""

    def test_gate12_z_score_stress_spectrum(self):
        """
        Stress test Gate 12 over exhaustive Z spectrum:
        - Z = -100.0 -> False (normal)
        - Z = 0.0 -> False (normal)
        - Z = 2.999999 -> False (normal)
        - Z = 3.000000 -> True (throttled)
        - Z = 3.000001 -> True (throttled)
        - Z = 100.0 -> True (throttled)
        - NaN, Inf, -Inf -> sanitizes to 0.0 (normal)
        - Various string formats (numeric, non-numeric, whitespace)
        - None and non-primitive types
        """
        cases = [
            (-100.0, False, "normal", 0.0150, 1.0, -100.0),
            (-5.0, False, "normal", 0.0150, 1.0, -5.0),
            (0.0, False, "normal", 0.0150, 1.0, 0.0),
            (1.5, False, "normal", 0.0150, 1.0, 1.5),
            (2.999999, False, "normal", 0.0150, 1.0, 2.999999),
            (3.000000, True, "passive_twap", 0.0050, 2.0, 3.0),
            (3.000001, True, "passive_twap", 0.0050, 2.0, 3.000001),
            (4.5, True, "passive_twap", 0.0050, 2.0, 4.5),
            (100.0, True, "passive_twap", 0.0050, 2.0, 100.0),
            (float("nan"), False, "normal", 0.0150, 1.0, 0.0),
            (float("inf"), False, "normal", 0.0150, 1.0, 0.0),
            (float("-inf"), False, "normal", 0.0150, 1.0, 0.0),
            (None, False, "normal", 0.0150, 1.0, 0.0),
            ("3.000000", True, "passive_twap", 0.0050, 2.0, 3.0),
            ("3.50", True, "passive_twap", 0.0050, 2.0, 3.5),
            ("2.999999", False, "normal", 0.0150, 1.0, 2.999999),
            ("-100.0", False, "normal", 0.0150, 1.0, -100.0),
            ("100.0", True, "passive_twap", 0.0050, 2.0, 100.0),
            ("invalid", False, "normal", 0.0150, 1.0, 0.0),
            ("", False, "normal", 0.0150, 1.0, 0.0),
            ("   ", False, "normal", 0.0150, 1.0, 0.0),
            ("nan", False, "normal", 0.0150, 1.0, 0.0),
            ("inf", False, "normal", 0.0150, 1.0, 0.0),
        ]

        for z_input, exp_throttled, exp_urgency, exp_adv, exp_leland, exp_z in cases:
            throttled, params = check_gate12_factor_crowding_shock(z_input, max_shock_z=3.0)

            self.assertEqual(
                throttled, exp_throttled,
                f"Z={z_input}: expected throttled={exp_throttled}, got {throttled}"
            )
            self.assertEqual(params["throttled"], exp_throttled)
            self.assertEqual(params["urgency"], exp_urgency)
            self.assertEqual(params["max_adv_participation"], exp_adv)
            self.assertEqual(params["leland_buffer_multiplier"], exp_leland)
            self.assertAlmostEqual(params["shock_z"], exp_z, places=5)

            # Strict Invariant: synthetic_rows == 0 strictly verified as native int 0
            synth = params.get("synthetic_rows")
            self.assertIs(type(synth), int, f"synthetic_rows must be native int, got {type(synth)}")
            self.assertNotIsInstance(synth, bool, "synthetic_rows cannot be bool")
            self.assertEqual(synth, 0, "synthetic_rows must be strictly 0")

    def test_gate12_non_primitive_and_malformed_inputs(self):
        """Stress test with complex objects: lists, dicts, tuples, lambdas."""
        malformed = [
            [3.5],
            {"z": 3.5},
            (3.0,),
            lambda x: 3.5,
            object(),
        ]
        for item in malformed:
            throttled, params = check_gate12_factor_crowding_shock(item, max_shock_z=3.0)
            self.assertFalse(throttled)
            self.assertEqual(params["shock_z"], 0.0)
            self.assertEqual(params["urgency"], "normal")
            self.assertEqual(params["synthetic_rows"], 0)


class TestM4Challenger1IntegrationAndEngine(unittest.TestCase):
    """Integration stress testing on ExecutionOMSEngine and AlmgrenChrissScheduler."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_evaluate_gate11_and_gate12_combined(self):
        """Test the combined evaluator across 4 truth table combinations."""
        # Setup inputs:
        # IRR high (>0.70): Omega small (0.01), D high (0.10)
        # IRR low (<0.70): Omega high (0.50), D low (0.01)
        w = np.array([0.5, 0.5])
        B = np.array([[1.0], [1.0]])

        # 1. Pass both: IRR >= 0.70 and Z < 3.0
        p1, m1, d1 = evaluate_gate11_and_gate12(
            w, B, Omega_F=np.array([[0.01]]), D_idio=np.array([0.10, 0.10]),
            factor_shock_z=1.2, min_irr=0.70, max_shock_z=3.0
        )
        self.assertTrue(p1)
        self.assertFalse(d1["gate12_throttled"])
        self.assertEqual(d1["synthetic_rows"], 0)

        # 2. Gate 11 Breached, Gate 12 Normal: IRR < 0.70 and Z < 3.0
        p2, m2, d2 = evaluate_gate11_and_gate12(
            w, B, Omega_F=np.array([[0.50]]), D_idio=np.array([0.01, 0.01]),
            factor_shock_z=0.5, min_irr=0.70, max_shock_z=3.0
        )
        self.assertFalse(p2)
        self.assertIn("Gate 11 Breached", m2)
        self.assertFalse(d2["gate12_throttled"])

        # 3. Gate 11 Passed, Gate 12 Throttled: IRR >= 0.70 and Z >= 3.0
        p3, m3, d3 = evaluate_gate11_and_gate12(
            w, B, Omega_F=np.array([[0.01]]), D_idio=np.array([0.10, 0.10]),
            factor_shock_z=3.5, min_irr=0.70, max_shock_z=3.0
        )
        # Note: In Feasibility Report §5.5, overall pass requires both Gate 11 pass and Gate 12 not throttled
        self.assertFalse(p3)
        self.assertIn("Gate 12 Breached", m3)
        self.assertTrue(d3["gate12_throttled"])
        self.assertEqual(d3["gate12_params"]["urgency"], "passive_twap")

        # 4. Both Breached: IRR < 0.70 and Z >= 3.0
        p4, m4, d4 = evaluate_gate11_and_gate12(
            w, B, Omega_F=np.array([[0.50]]), D_idio=np.array([0.01, 0.01]),
            factor_shock_z=4.2, min_irr=0.70, max_shock_z=3.0
        )
        self.assertFalse(p4)
        self.assertIn("Gate 11 Breached", m4)
        self.assertTrue(d4["gate12_throttled"])

    def test_almgren_chriss_passive_twap_mathematical_uniformity(self):
        """
        Verify that under strategy_tier='passive_twap', AlmgrenChrissScheduler
        produces strictly uniform tranche allocations for arbitrary quantities and slices.
        """
        test_configs = [
            (600, 6, [100, 100, 100, 100, 100, 100]),
            (1000, 5, [200, 200, 200, 200, 200]),
            (100, 4, [25, 25, 25, 25]),
            (7, 3, [3, 2, 2]),  # Integer rounding distribution
            (1, 4, [1, 0, 0, 0]),  # Single unit
        ]

        for total_q, n_sl, expected_slices in test_configs:
            slices = AlmgrenChrissScheduler.compute_trajectory(
                total_quantity=total_q,
                adv=1_000_000.0,
                daily_volatility=0.02,
                strategy_tier="passive_twap",
                n_slices=n_sl,
            )
            self.assertEqual(len(slices), n_sl)
            self.assertEqual(sum(slices), total_q)
            self.assertEqual(slices, expected_slices)

    def test_evaluate_batch_factor_risk_gates_dict_and_none(self):
        """Verify ExecutionOMSEngine.evaluate_batch_factor_risk_gates with dict weights and missing inputs."""
        # Dict weights
        weights_dict = {"005930": 0.4, "000660": 0.6}
        res_none = self.oms.evaluate_batch_factor_risk_gates(
            portfolio_weights=weights_dict,
            factor_loadings=None,
        )
        self.assertTrue(res_none["passed"])
        self.assertEqual(res_none["irr"], 1.0)
        self.assertEqual(res_none["synthetic_rows"], 0)

        # Empty dict
        res_empty = self.oms.evaluate_batch_factor_risk_gates(portfolio_weights={})
        self.assertTrue(res_empty["passed"])
        self.assertEqual(res_empty["irr"], 1.0)


if __name__ == "__main__":
    unittest.main()

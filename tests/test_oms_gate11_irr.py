"""
Unit and Integration Test Suite for OMS Gate 11: Idiosyncratic Risk Ratio (IRR) Safeguard.
Specification: docs/MULTI_FACTOR_ARCHITECTURAL_FEASIBILITY_REPORT.md §5.5 & ORIGINAL_REQUEST.md §R4.

Formulation:
    beta_p = B^T w
    sigma^2_factor = beta_p^T Omega_F beta_p
    sigma^2_idio = w^T D w = sum(w_i^2 * D_i)
    sigma^2_total = sigma^2_factor + sigma^2_idio
    IRR = sigma^2_idio / sigma^2_total

Rule:
    Reject order batches / target portfolios where IRR < min_irr (default 0.70).
"""

import unittest
import numpy as np

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    check_gate11_idiosyncratic_risk_ratio,
    evaluate_gate11_and_gate12,
)


class TestOMSGate11IdiosyncraticRiskRatio(unittest.TestCase):
    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_gate11_exact_boundary_conditions(self):
        """
        Boundary tests at threshold 0.7000:
        - IRR == 0.7000 passes (passed=True, reason='PASSED')
        - IRR == 0.6999 breaches (passed=False, reason contains 'Gate 11 Breached')
        - IRR == 0.7001 passes (passed=True, reason='PASSED')
        """
        w = np.array([1.0], dtype=np.float64)
        B = np.array([[1.0]], dtype=np.float64)

        # 1. Exact 0.7000: factor_var = 0.30, idio_var = 0.70 => total_var = 1.0 => IRR = 0.70
        Omega_exact = np.array([[0.30]], dtype=np.float64)
        D_exact = np.array([0.70], dtype=np.float64)
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_exact, D_exact, min_irr=0.70
        )
        self.assertTrue(passed)
        self.assertAlmostEqual(irr, 0.70, places=6)
        self.assertEqual(reason, "PASSED")

        # 2. Sub-boundary 0.6999: factor_var = 0.3001, idio_var = 0.6999 => IRR = 0.6999 < 0.70
        Omega_sub = np.array([[0.3001]], dtype=np.float64)
        D_sub = np.array([0.6999], dtype=np.float64)
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_sub, D_sub, min_irr=0.70
        )
        self.assertFalse(passed)
        self.assertAlmostEqual(irr, 0.6999, places=6)
        self.assertIn("Gate 11 Breached: IRR 0.6999 < 0.7000", reason)

        # 3. Super-boundary 0.7001: factor_var = 0.2999, idio_var = 0.7001 => IRR = 0.7001 > 0.70
        Omega_super = np.array([[0.2999]], dtype=np.float64)
        D_super = np.array([0.7001], dtype=np.float64)
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_super, D_super, min_irr=0.70
        )
        self.assertTrue(passed)
        self.assertAlmostEqual(irr, 0.7001, places=6)
        self.assertEqual(reason, "PASSED")

    def test_gate11_1d_vs_2d_diagonal_idiosyncratic_variance(self):
        """
        Verify identical mathematical results whether D_idio is passed as a 1D vector
        or as a 2D diagonal covariance matrix.
        """
        np.random.seed(42)
        N = 5
        K = 2
        w = np.array([0.2, 0.3, 0.1, 0.25, 0.15], dtype=np.float64)
        B = np.random.randn(N, K)
        Omega = np.array([[0.04, 0.01], [0.01, 0.05]], dtype=np.float64)
        d_vec = np.array([0.08, 0.12, 0.05, 0.10, 0.07], dtype=np.float64)
        D_mat = np.diag(d_vec)

        pass_1d, irr_1d, reason_1d = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega, d_vec, min_irr=0.70
        )
        pass_2d, irr_2d, reason_2d = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega, D_mat, min_irr=0.70
        )

        self.assertEqual(pass_1d, pass_2d)
        self.assertAlmostEqual(irr_1d, irr_2d, places=9)
        self.assertEqual(reason_1d, reason_2d)

    def test_gate11_zero_weights_and_degenerate_variance_fallbacks(self):
        """
        Degenerate cases:
        - All-zero weights w = 0 (total_var <= 1e-12)
        - Empty weights w = []
        - Zero variance matrices
        Must return safe default: (True, 1.0, "Zero/negligible total risk: safe default").
        """
        B = np.ones((3, 2), dtype=np.float64)
        Omega = np.eye(2, dtype=np.float64)
        D = np.ones(3, dtype=np.float64)

        # 1. Zero weights
        w_zeros = np.zeros(3, dtype=np.float64)
        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w_zeros, B, Omega, D, min_irr=0.70
        )
        self.assertTrue(passed)
        self.assertEqual(irr, 1.0)
        self.assertEqual(reason, "Zero/negligible total risk: safe default")

        # 2. Empty weights
        passed_empty, irr_empty, reason_empty = check_gate11_idiosyncratic_risk_ratio(
            np.array([]), B, Omega, D, min_irr=0.70
        )
        self.assertTrue(passed_empty)
        self.assertEqual(irr_empty, 1.0)
        self.assertEqual(reason_empty, "Zero/negligible total risk: safe default")

        # 3. Microscopic total variance (< 1e-12)
        w_micro = np.array([1e-8, 1e-8, 1e-8], dtype=np.float64)
        passed_micro, irr_micro, reason_micro = check_gate11_idiosyncratic_risk_ratio(
            w_micro, B, Omega, D, min_irr=0.70
        )
        self.assertTrue(passed_micro)
        self.assertEqual(irr_micro, 1.0)
        self.assertEqual(reason_micro, "Zero/negligible total risk: safe default")

    def test_gate11_non_psd_covariance_and_negative_variance_rectification(self):
        """
        Adversarial inputs:
        - Factor covariance Omega_F with negative eigenvalues (non-PSD)
        - Negative idiosyncratic variances in D_idio (finite-sample estimation noise)
        Must be spectrally clipped / non-negatively rectified without crashing or raising math errors.
        """
        w = np.array([0.5, 0.5], dtype=np.float64)
        B = np.array([[1.0, 0.5], [0.5, 1.0]], dtype=np.float64)

        # Non-PSD covariance with negative eigenvalue
        Omega_non_psd = np.array([[1.0, 3.0], [3.0, 1.0]], dtype=np.float64)  # eigenvalues: 4.0 and -2.0
        # Negative idiosyncratic variance
        D_neg = np.array([-0.05, 0.20], dtype=np.float64)

        passed, irr, reason = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_non_psd, D_neg, min_irr=0.70
        )
        self.assertIsInstance(passed, bool)
        self.assertIsInstance(irr, float)
        self.assertTrue(0.0 <= irr <= 1.0)
        self.assertIsInstance(reason, str)

    def test_gate11_static_method_and_evaluate_batch_factor_risk_gates(self):
        """
        Verify:
        - Attachment as staticmethod on ExecutionOMSEngine
        - evaluate_batch_factor_risk_gates on ExecutionOMSEngine instance
        - Native int synthetic_rows invariant
        """
        w_dict = {"005930": 0.5, "000660": 0.5}
        B = np.array([[0.2, 0.1], [0.3, 0.2]], dtype=np.float64)
        Omega = np.array([[0.05, 0.0], [0.0, 0.05]], dtype=np.float64)
        D = np.array([0.15, 0.20], dtype=np.float64)

        # 1. Static method call
        sm_passed, sm_irr, sm_reason = ExecutionOMSEngine.check_gate11_idiosyncratic_risk_ratio(
            np.array([0.5, 0.5]), B, Omega, D, min_irr=0.70
        )
        self.assertIsInstance(sm_passed, bool)
        self.assertIsInstance(sm_irr, float)

        # 2. Batch factor risk gates method on instance
        batch_res = self.oms.evaluate_batch_factor_risk_gates(
            portfolio_weights=w_dict,
            factor_loadings=B,
            factor_covariance=Omega,
            idiosyncratic_vars=D,
            min_irr=0.70,
        )
        self.assertIn("passed", batch_res)
        self.assertIn("irr", batch_res)
        self.assertIn("gate11_passed", batch_res)
        self.assertIn("gate11_reason", batch_res)
        self.assertIn("synthetic_rows", batch_res)
        self.assertEqual(batch_res["synthetic_rows"], 0)
        self.assertIs(type(batch_res["synthetic_rows"]), int)
        self.assertNotIsInstance(batch_res["synthetic_rows"], bool)

    def test_evaluate_gate11_and_gate12_combined(self):
        """
        Verify evaluate_gate11_and_gate12 combined evaluation:
        - When Gate 11 passes and Gate 12 normal => True, 'PASSED'
        - When Gate 11 breaches (IRR < 0.70) => False, Gate 11 breach reason
        """
        w = np.array([1.0], dtype=np.float64)
        B = np.array([[1.0]], dtype=np.float64)

        # Passing Gate 11 (IRR = 0.80), normal shock Z = 1.2
        passed, msg, details = evaluate_gate11_and_gate12(
            w_target=w,
            B_loadings=B,
            Omega_F=np.array([[0.20]]),
            D_idio=np.array([0.80]),
            factor_shock_z=1.2,
            min_irr=0.70,
            max_shock_z=3.0,
        )
        self.assertTrue(passed)
        self.assertEqual(msg, "PASSED")
        self.assertAlmostEqual(details["irr"], 0.80)
        self.assertTrue(details["gate11_passed"])
        self.assertFalse(details["gate12_throttled"])

        # Breaching Gate 11 (IRR = 0.40), normal shock Z = 1.0
        passed_fail, msg_fail, details_fail = evaluate_gate11_and_gate12(
            w_target=w,
            B_loadings=B,
            Omega_F=np.array([[0.60]]),
            D_idio=np.array([0.40]),
            factor_shock_z=1.0,
            min_irr=0.70,
            max_shock_z=3.0,
        )
        self.assertFalse(passed_fail)
        self.assertIn("Gate 11 Breached: IRR 0.4000 < 0.7000", msg_fail)
        self.assertFalse(details_fail["gate11_passed"])


if __name__ == "__main__":
    unittest.main()

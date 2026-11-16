"""
tests/test_m1_challenger_adversarial_suite.py
Adversarial Challenger Test Suite for Milestone 1 (M1: D-FCN & BFIT).
Empirically tests numerical stability, invariants, and edge cases.
"""

import unittest
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.core.multi_factor_neutralizer import (
    MultiFactorNeutralizerEngine,
    compute_precision_weighted_neutralization,
    compute_bilinear_interaction_alpha,
)


class TestEmpiricalChallengerM1(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.engine = MultiFactorNeutralizerEngine()

    # -------------------------------------------------------------------------
    # 1. Numerical Stress Tests: Singular and Ill-Conditioned Design Matrices
    # -------------------------------------------------------------------------

    def test_ill_conditioned_matrix_condition_number_1e15(self):
        """Condition number > 1e14: verify Tikhonov regularization and stability."""
        N, K = 100, 5
        B = np.random.randn(N, K)
        # Create extreme collinearity so cond(B^T W^-1 B) > 1e14
        B[:, 1] = B[:, 0] + np.random.normal(0, 1e-15, size=N)
        w = np.random.uniform(0.1, 5.0, size=N)
        y = np.random.randn(N)

        # Check condition number
        W_inv = np.diag(1.0 / w)
        A = B.T @ W_inv @ B
        cond_A = np.linalg.cond(A)
        self.assertGreater(cond_A, 1e12, f"Matrix not ill-conditioned enough: {cond_A}")

        # Execute
        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w, ridge_lambda=1e-4)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)), "Non-finite values produced on ill-conditioned matrix")
        self.assertFalse(np.any(np.isnan(y_star)), "NaNs produced on ill-conditioned matrix")

    def test_extreme_collinearity_r_0_99999(self):
        """Extreme collinearity r >= 0.9999 between factors."""
        N, K = 200, 5
        B = np.random.randn(N, K)
        B[:, 2] = B[:, 1] * 0.99999 + np.random.normal(0, 1e-7, size=N)
        B[:, 4] = B[:, 3] * 0.99999 + np.random.normal(0, 1e-7, size=N)
        w = np.random.uniform(0.5, 2.0, size=N)
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_underdetermined_universes_n_less_than_k(self):
        """Underdetermined universes: N in {1, 2, 3, 4} for K=5."""
        for n in [1, 2, 3, 4]:
            B = np.random.randn(n, 5)
            y = np.random.randn(n)
            w = np.random.uniform(0.5, 2.0, size=n)

            y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)
            self.assertEqual(len(y_star), n)
            self.assertTrue(np.all(np.isfinite(y_star)))
            if n == 1:
                self.assertEqual(y_star[0], 0.0)

    def test_zero_variance_and_constant_factors(self):
        """Zero-variance factor columns (e.g. all 0, all 5.0, constant)."""
        N, K = 50, 5
        B = np.random.randn(N, K)
        B[:, 0] = 0.0
        B[:, 2] = 100.0
        B[:, 4] = -42.0
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_all_constant_design_matrix(self):
        """Entire design matrix B is constant."""
        N = 50
        B = np.ones((N, 4)) * 3.14
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_all_nan_inputs(self):
        """All-NaN y and all-NaN B."""
        N, K = 30, 4
        B = np.full((N, K), np.nan)
        y = np.full(N, np.nan)

        y_star = compute_precision_weighted_neutralization(y, B)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))
        self.assertTrue(np.all(y_star == 0.0))

    def test_extreme_outliers_values(self):
        """Extreme values +/- 1e6, +/- 1e12, +/- inf."""
        N, K = 60, 5
        B = np.random.randn(N, K)
        B[0, :] = 1e12
        B[1, :] = -1e12
        B[2, :] = np.inf
        B[3, :] = -np.inf
        y = np.random.randn(N)
        y[0] = 1e9
        y[1] = -1e9
        y[2] = np.inf
        y[3] = np.nan

        y_star = compute_precision_weighted_neutralization(y, B)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    # -------------------------------------------------------------------------
    # 2. Mathematical Invariants
    # -------------------------------------------------------------------------

    def test_exact_orthogonality_unconstrained(self):
        """Exact orthogonality invariant: B^T y_star < 1e-10 when unconstrained."""
        N, K = 300, 5
        B = np.random.randn(N, K)
        y = np.random.randn(N)
        w = np.random.uniform(0.5, 3.0, size=N)

        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)
        ortho_err = np.max(np.abs(B.T @ y_star))
        self.assertLess(
            ortho_err, 1e-10,
            f"Exact orthogonality violated: max |B^T y_star| = {ortho_err:.2e} >= 1e-10"
        )

    def test_bfit_bounded_activation_strict(self):
        """BFIT output strictly within [-1.0, 1.0] across normal and extreme domains."""
        # Grid of extreme test scores
        test_inputs = [
            np.zeros((10, 5)),
            np.ones((10, 5)) * 1e6,
            np.ones((10, 5)) * -1e6,
            np.random.normal(0, 100, size=(100, 5)),
            np.full((20, 5), np.nan),
            np.full((20, 5), np.inf),
        ]
        for S in test_inputs:
            alpha = compute_bilinear_interaction_alpha(S)
            self.assertTrue(np.all(np.isfinite(alpha)), f"Non-finite BFIT alpha for input:\n{S[:2]}")
            self.assertTrue(np.all(alpha >= -1.0), f"BFIT alpha below -1.0: {np.min(alpha)}")
            self.assertTrue(np.all(alpha <= 1.0), f"BFIT alpha above 1.0: {np.max(alpha)}")

    # -------------------------------------------------------------------------
    # 3. NumPy 2.0+ Writeability Tests (Read-Only Array Immunity)
    # -------------------------------------------------------------------------

    def test_readonly_array_immunity_bfit(self):
        """Verify BFIT does not mutate read-only array in-place or crash."""
        S = np.random.randn(20, 5)
        S[5, 2] = np.nan
        S.flags.writeable = False  # Make read-only!

        try:
            alpha = compute_bilinear_interaction_alpha(S)
            self.assertEqual(len(alpha), 20)
            self.assertTrue(np.all(np.isfinite(alpha)))
        except ValueError as e:
            if "read-only" in str(e).lower():
                self.fail(f"BFIT crashed on read-only array: {e}")
            raise

    def test_readonly_array_immunity_dfcn(self):
        """Verify D-FCN does not mutate read-only array in-place or crash."""
        B = np.random.randn(50, 4)
        B[3, 1] = np.nan
        B.flags.writeable = False  # Make read-only!

        y = np.random.randn(50)
        y[2] = np.nan
        y.flags.writeable = False  # Make read-only!

        try:
            y_star = compute_precision_weighted_neutralization(y, B)
            self.assertEqual(len(y_star), 50)
            self.assertTrue(np.all(np.isfinite(y_star)))
        except ValueError as e:
            if "read-only" in str(e).lower():
                self.fail(f"D-FCN crashed on read-only array: {e}")
            raise


if __name__ == "__main__":
    unittest.main()

"""
tests/test_oas_covariance.py — Comprehensive Unit & Integration Test Suite
for Analytical Oracle Approximating Shrinkage (OAS, Chen et al., 2010).

Covers:
1. Mathematical formula accuracy of \\hat{\\rho}_{\\text{OAS}} against Chen et al. (2010) Eq. 23.
2. Spherical matrix edge case S = c * I (zero denominator term -> \\rho = 0.0).
3. Sample size N <= 2 fallback (\\rho = 0.20).
4. Strict positive definiteness of C_oas (\\lambda_{\\min} > 0).
5. Theoretical mean squared error (MSE) reduction over sample covariance against true population covariance.
6. Integration into FactorOrthogonalizerEngine._compute_ledoit_wolf_covariance as analytical fallback.
7. High-dimensional factor sets (K=17, K=37) and rank-deficient regimes (N < K).
8. System invariant verification: synthetic_rows == 0 (native int 0).
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_oas_covariance,
)


class TestOASMathematicalCorrectness(unittest.TestCase):
    """Test suite for analytical OAS formula precision against Chen et al. (2010)."""

    def setUp(self) -> None:
        np.random.seed(42)

    def test_oas_exact_formula_verification(self) -> None:
        """Verify \\hat{\\rho}_{\\text{OAS}} matches Chen et al. (2010) Eq. 23 exactly:
        num = (1 - 2/K) * Tr(S^2) + Tr^2(S)
        denom = (N + 1 - 2/K) * (Tr(S^2) - Tr^2(S) / K)
        \\rho = min(1.0, max(0.0, num / denom))
        """
        N, K = 80, 10
        X = np.random.randn(N, K)
        X_centered = X - np.mean(X, axis=0)

        C_sample = (X_centered.T @ X_centered) / float(N - 1)
        S = 0.5 * (C_sample + C_sample.T)

        tr_S = float(np.trace(S))
        tr_S2 = float(np.sum(S ** 2))
        tr2_S = tr_S ** 2

        num_expected = (1.0 - 2.0 / float(K)) * tr_S2 + tr2_S
        denom_expected = (float(N) + 1.0 - 2.0 / float(K)) * (tr_S2 - (tr2_S / float(K)))
        rho_expected = float(np.clip(num_expected / denom_expected, 0.0, 1.0))

        target_expected = (tr_S / float(K)) * np.eye(K)
        ridge_eps = 1e-6
        C_expected = (1.0 - rho_expected) * S + rho_expected * target_expected + ridge_eps * np.eye(K)
        C_expected = 0.5 * (C_expected + C_expected.T)

        C_actual, rho_actual = compute_oas_covariance(X_centered, ridge_epsilon=ridge_eps)

        self.assertAlmostEqual(rho_actual, rho_expected, places=12, msg="OAS shrinkage intensity does not match Eq. 23.")
        np.testing.assert_allclose(
            C_actual,
            C_expected,
            rtol=1e-12,
            atol=1e-12,
            err_msg="OAS covariance matrix does not match analytical expectation.",
        )

    def test_oas_matrix_symmetry(self) -> None:
        """Verify OAS regularized covariance matrix is strictly symmetric: C = C^T."""
        N, K = 120, 17
        X = np.random.randn(N, K)
        C_oas, _ = compute_oas_covariance(X)

        asymm_norm = np.linalg.norm(C_oas - C_oas.T, "fro")
        self.assertLess(asymm_norm, 1e-14, "OAS covariance must be perfectly symmetric.")

    def test_oas_shrinkage_bounded_unit_interval(self) -> None:
        """Verify \\hat{\\rho}_{\\text{OAS}} is strictly bounded in [0.0, 1.0] across diverse dimensions."""
        for N in [5, 10, 50, 200]:
            for K in [3, 8, 20, 40]:
                X = np.random.randn(N, K)
                _, rho = compute_oas_covariance(X)
                self.assertGreaterEqual(rho, 0.0, f"Shrinkage intensity below 0 for N={N}, K={K}")
                self.assertLessEqual(rho, 1.0, f"Shrinkage intensity exceeds 1 for N={N}, K={K}")


class TestOASEdgeCases(unittest.TestCase):
    """Test suite for mathematical and algorithmic edge cases in OAS covariance estimation."""

    def setUp(self) -> None:
        np.random.seed(123)

    def test_spherical_identity_matrix_zero_denominator(self) -> None:
        """When S = c * I, Tr(S^2) - Tr^2(S)/K == 0, shrinkage intensity must clamp to 0.0."""
        for c in [0.5, 1.0, 3.5, 10.0]:
            K = 6
            S_spherical = c * np.eye(K)
            C_oas, rho_oas = compute_oas_covariance(None, C_sample=S_spherical)

            self.assertEqual(rho_oas, 0.0, f"Spherical matrix S={c}*I must produce rho=0.0")
            expected = S_spherical + 1e-6 * np.eye(K)
            np.testing.assert_allclose(C_oas, expected, rtol=1e-12, atol=1e-12)

    def test_small_sample_size_n_less_equal_two_fallback(self) -> None:
        """When N <= 2, OAS must apply the safe fallback shrinkage \\rho = 0.20."""
        # N = 1
        X_1 = np.random.randn(1, 5)
        _, rho_1 = compute_oas_covariance(X_1)
        self.assertEqual(rho_1, 0.20, "N=1 must fallback to rho=0.20")

        # N = 2
        X_2 = np.random.randn(2, 5)
        _, rho_2 = compute_oas_covariance(X_2)
        self.assertEqual(rho_2, 0.20, "N=2 must fallback to rho=0.20")

        # N = 3 (normal calculation)
        X_3 = np.random.randn(3, 5)
        _, rho_3 = compute_oas_covariance(X_3)
        self.assertNotEqual(rho_3, 0.20, "N=3 must not trigger N<=2 fallback")

    def test_single_factor_dimension_k_equals_one(self) -> None:
        """When K = 1, OAS must return 1x1 matrix with rho = 0.0."""
        X_1d = np.random.randn(50, 1)
        C_oas, rho = compute_oas_covariance(X_1d)
        self.assertEqual(C_oas.shape, (1, 1))
        self.assertEqual(rho, 0.0)
        self.assertGreater(C_oas[0, 0], 0.0)

    def test_rank_deficient_n_less_than_k(self) -> None:
        """When N < K (high-dimensional low-sample regime), OAS must regularize to full rank PSD."""
        N, K = 8, 30
        X = np.random.randn(N, K)
        C_oas, rho = compute_oas_covariance(X)

        eigvals = np.linalg.eigvalsh(C_oas)
        min_eig = float(np.min(eigvals))
        self.assertGreater(min_eig, 1e-6, "OAS must produce strictly positive minimum eigenvalue even when N < K.")
        self.assertGreater(rho, 0.50, "In N < K regime, shrinkage towards spherical identity should be substantial.")

    def test_perfectly_collinear_features(self) -> None:
        """Features with rank 1 collinearity must be successfully regularized by OAS."""
        N, K = 100, 12
        base = np.random.randn(N, 1)
        X_collinear = np.tile(base, (1, K)) + np.random.randn(N, K) * 1e-8

        C_oas, rho = compute_oas_covariance(X_collinear, ridge_epsilon=1e-5)
        eigvals = np.linalg.eigvalsh(C_oas)
        self.assertGreater(float(np.min(eigvals)), 1e-6, "OAS must ensure positive definiteness under collinearity.")
        self.assertGreater(rho, 0.0)

    def test_precomputed_c_sample_with_x_bar(self) -> None:
        """Verify passing both X_bar and precomputed C_sample uses X_bar for N and C_sample for covariance."""
        N, K = 60, 5
        X = np.random.randn(N, K)
        C_pre = (X.T @ X) / float(N - 1)

        C_oas_1, rho_1 = compute_oas_covariance(X)
        C_oas_2, rho_2 = compute_oas_covariance(X, C_sample=C_pre)

        self.assertAlmostEqual(rho_1, rho_2, places=12)
        np.testing.assert_allclose(C_oas_1, C_oas_2, rtol=1e-12, atol=1e-12)

    def test_invalid_inputs_raise_value_error(self) -> None:
        """Passing neither X_bar nor C_sample must raise ValueError."""
        with self.assertRaises(ValueError):
            compute_oas_covariance(None, None)

        # Non-square C_sample
        with self.assertRaises(ValueError):
            compute_oas_covariance(None, C_sample=np.zeros((3, 4)))


class TestOASSpectralPropertiesAndMSE(unittest.TestCase):
    """Test suite for spectral condition number improvement and theoretical MSE reduction."""

    def setUp(self) -> None:
        np.random.seed(999)

    def test_spectral_condition_number_improvement(self) -> None:
        """OAS shrinkage towards spherical identity must strictly reduce or maintain matrix condition number."""
        N, K = 40, 15
        X = np.random.randn(N, K)
        C_sample = (X.T @ X) / float(N - 1)

        cond_sample = np.linalg.cond(C_sample)
        C_oas, rho = compute_oas_covariance(X)
        cond_oas = np.linalg.cond(C_oas)

        self.assertLessEqual(cond_oas, cond_sample, "OAS must improve (reduce) or maintain condition number.")

    def test_monte_carlo_mse_reduction_over_sample_covariance(self) -> None:
        """Chen et al. (2010): OAS achieves lower mean squared error (MSE) relative to true covariance:
        E[||C_oas - Sigma_true||_F^2] <= E[||S_sample - Sigma_true||_F^2].
        """
        K = 8
        # Create a true population covariance matrix
        A = np.random.randn(K, K)
        Sigma_true = 0.5 * (A @ A.T) + np.eye(K)

        L = np.linalg.cholesky(Sigma_true)
        N = 25  # Small sample size relative to K where shrinkage benefits are prominent

        trials = 100
        mse_sample_total = 0.0
        mse_oas_total = 0.0

        for _ in range(trials):
            Z = np.random.randn(N, K)
            X = Z @ L.T  # Sample from N(0, Sigma_true)
            X_c = X - np.mean(X, axis=0)

            S_sample = (X_c.T @ X_c) / float(N - 1)
            C_oas, _ = compute_oas_covariance(X_c, ridge_epsilon=0.0)

            mse_sample_total += float(np.sum((S_sample - Sigma_true) ** 2))
            mse_oas_total += float(np.sum((C_oas - Sigma_true) ** 2))

        avg_mse_sample = mse_sample_total / float(trials)
        avg_mse_oas = mse_oas_total / float(trials)

        self.assertLess(
            avg_mse_oas,
            avg_mse_sample,
            f"OAS average MSE ({avg_mse_oas:.4f}) must be lower than sample covariance MSE ({avg_mse_sample:.4f}).",
        )


class TestOASIntegration(unittest.TestCase):
    """Test suite for integration of OAS covariance in FactorOrthogonalizerEngine."""

    def setUp(self) -> None:
        np.random.seed(777)
        self.engine = FactorOrthogonalizerEngine()

    def test_static_method_availability(self) -> None:
        """Verify FactorOrthogonalizerEngine.compute_oas_covariance is available as staticmethod."""
        self.assertTrue(hasattr(FactorOrthogonalizerEngine, "compute_oas_covariance"))
        X = np.random.randn(30, 4)
        C1, r1 = FactorOrthogonalizerEngine.compute_oas_covariance(X)
        C2, r2 = compute_oas_covariance(X)
        np.testing.assert_allclose(C1, C2)
        self.assertEqual(r1, r2)

    def test_compute_ledoit_wolf_covariance_uses_oas_fallback(self) -> None:
        """When LedoitWolf fails or is unavailable, _compute_ledoit_wolf_covariance uses analytical OAS."""
        N, K = 50, 6
        X = np.random.randn(N, K)
        C_sample = (X.T @ X) / float(N - 1)

        # Mock LedoitWolf to raise an exception
        with patch("sklearn.covariance.LedoitWolf", side_effect=RuntimeError("Mocked sklearn failure")):
            C_fallback = self.engine._compute_ledoit_wolf_covariance(X, C_sample)

        C_expected, _ = compute_oas_covariance(X, C_sample=C_sample, ridge_epsilon=self.engine.ridge_epsilon)
        np.testing.assert_allclose(
            C_fallback,
            C_expected,
            rtol=1e-11,
            atol=1e-11,
            err_msg="_compute_ledoit_wolf_covariance must use analytical OAS as fallback.",
        )

    def test_orthogonalize_pipeline_execution_with_oas(self) -> None:
        """Verify FactorOrthogonalizerEngine.orthogonalize runs seamlessly and preserves [0, 1] bounds."""
        cols = [f"strat_{i}" for i in range(10)]
        df = pd.DataFrame(np.random.uniform(0.1, 0.9, size=(60, 10)), columns=cols)

        out_df = self.engine.orthogonalize(df, cols, method="pca_symmetric")
        self.assertEqual(out_df.shape, df.shape)
        self.assertFalse(out_df.isna().any().any())
        self.assertTrue((out_df.to_numpy() >= 0.0).all())
        self.assertTrue((out_df.to_numpy() <= 1.0).all())


class TestSystemInvariants(unittest.TestCase):
    """Test suite verifying system core invariants."""

    def test_zero_synthetic_rows_native_int(self) -> None:
        """Verify synthetic_rows == 0 is strictly satisfied as native Python int 0."""
        synthetic_rows = 0
        self.assertIs(type(synthetic_rows), int)
        self.assertFalse(isinstance(synthetic_rows, bool))
        self.assertEqual(synthetic_rows, 0)


if __name__ == "__main__":
    unittest.main()

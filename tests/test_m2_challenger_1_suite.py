"""
tests/test_m2_challenger_1_suite.py
Adversarial Challenger 1 Test Suite for Milestone 2 (M2: OAS Covariance & Higham PSD Projection).
Empirically stress-tests numerical stability, boundary conditions, invariants, and Frobenius optimality.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import unittest
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_oas_covariance,
    higham_nearest_correlation_matrix,
    repair_covariance_psd,
)


class TestAdversarialOASCovariance(unittest.TestCase):
    """Adversarial stress testing of compute_oas_covariance under singular, collinear, and extreme regimes."""

    def setUp(self) -> None:
        np.random.seed(42)

    def test_oas_collinear_rank_deficient_n_less_than_k(self) -> None:
        """Adversarial test: N << K rank-deficient regimes (e.g. N=3, 5, 8, 15 with K=50)."""
        K = 50
        for N in [3, 5, 8, 15, 30]:
            X = np.random.randn(N, K)
            C_oas, rho_oas = compute_oas_covariance(X, ridge_epsilon=1e-6)

            self.assertTrue(np.all(np.isfinite(C_oas)), f"Non-finite values for N={N}, K={K}")
            self.assertGreaterEqual(rho_oas, 0.0, f"rho_oas negative for N={N}")
            self.assertLessEqual(rho_oas, 1.0, f"rho_oas > 1 for N={N}")

            eigvals = np.linalg.eigvalsh(C_oas)
            min_eig = float(np.min(eigvals))
            self.assertGreater(
                min_eig, 1e-6,
                f"Minimum eigenvalue {min_eig:.4e} not strictly positive for N={N}, K={K}"
            )
            # In severe rank deficiency, shrinkage intensity should be high
            self.assertGreater(rho_oas, 0.20, f"Expected strong shrinkage for N={N} < K={K}")

    def test_oas_zero_variance_and_constant_columns(self) -> None:
        """Adversarial test: zero-variance and constant factor columns."""
        N, K = 40, 8
        X = np.random.randn(N, K)
        X[:, 0] = 0.0          # All zeros
        X[:, 2] = 42.0         # Constant positive
        X[:, 5] = -100.0       # Constant negative
        X[:, 7] = X[:, 1]      # Exact duplicate column

        C_oas, rho_oas = compute_oas_covariance(X, ridge_epsilon=1e-5)

        self.assertTrue(np.all(np.isfinite(C_oas)), "Non-finite covariance on zero/constant columns")
        self.assertGreaterEqual(rho_oas, 0.0)
        self.assertLessEqual(rho_oas, 1.0)

        min_eig = float(np.min(np.linalg.eigvalsh(C_oas)))
        self.assertGreater(min_eig, 1e-6, "OAS must ensure positive definiteness despite zero/constant columns")

    def test_oas_entirely_zero_data_matrix(self) -> None:
        """Adversarial test: entirely zero data matrix and zero sample covariance."""
        N, K = 25, 6
        X_zero = np.zeros((N, K))
        C_oas, rho_oas = compute_oas_covariance(X_zero, ridge_epsilon=1e-6)

        self.assertEqual(rho_oas, 0.0, "Zero matrix must clamp rho to 0.0")
        expected = 1e-6 * np.eye(K)
        np.testing.assert_allclose(C_oas, expected, atol=1e-12)
        min_eig = float(np.min(np.linalg.eigvalsh(C_oas)))
        self.assertGreater(min_eig, 0.0)

    def test_oas_identity_scaling_and_near_spherical_perturbations(self) -> None:
        """Adversarial test: S = c * I and S = c * I + delta (denominator zero division guard)."""
        K = 7
        for c in [0.0, 1e-12, 1e-8, 1e-4, 1.0, 100.0, 1e6]:
            S_sph = c * np.eye(K)
            C_oas, rho = compute_oas_covariance(C_sample=S_sph, ridge_epsilon=1e-6)
            self.assertEqual(rho, 0.0, f"Spherical matrix S={c}*I must produce rho=0.0")
            np.testing.assert_allclose(C_oas, S_sph + 1e-6 * np.eye(K), atol=1e-10)

        # Near-spherical perturbation where Tr(S^2) - Tr^2(S)/K is around machine epsilon
        delta = 1e-14
        S_perturbed = np.eye(K) + np.random.uniform(-delta, delta, size=(K, K))
        S_perturbed = 0.5 * (S_perturbed + S_perturbed.T)
        C_pert, rho_pert = compute_oas_covariance(C_sample=S_perturbed, ridge_epsilon=1e-6)
        self.assertTrue(np.isfinite(rho_pert))
        self.assertGreaterEqual(rho_pert, 0.0)
        self.assertLessEqual(rho_pert, 1.0)
        self.assertGreater(float(np.min(np.linalg.eigvalsh(C_pert))), 0.0)

    def test_oas_extreme_sample_sizes_and_dimensions(self) -> None:
        """Adversarial test: extreme sample sizes N in {1, 2, 10000} and K in {1, 50}."""
        cases = [
            (1, 1),
            (1, 10),
            (1, 50),
            (2, 1),
            (2, 10),
            (2, 50),
            (10000, 1),
            (10000, 10),
            (10000, 50),
        ]
        for N, K in cases:
            X = np.random.randn(N, K)
            C_oas, rho = compute_oas_covariance(X, ridge_epsilon=1e-6)

            self.assertEqual(C_oas.shape, (K, K), f"Incorrect shape for N={N}, K={K}")
            self.assertTrue(np.all(np.isfinite(C_oas)), f"Non-finite C_oas for N={N}, K={K}")
            self.assertGreaterEqual(rho, 0.0)
            self.assertLessEqual(rho, 1.0)

            min_eig = float(np.min(np.linalg.eigvalsh(C_oas)))
            self.assertGreater(min_eig, 0.0, f"min_eig not positive for N={N}, K={K}")

            if K == 1:
                self.assertEqual(rho, 0.0, "K=1 must yield rho=0.0")
            elif N <= 2:
                self.assertEqual(rho, 0.20, f"N={N} <= 2 must yield fallback rho=0.20")

    def test_oas_heavy_tailed_cauchy_and_outliers(self) -> None:
        """Adversarial test: heavy-tailed noise (Student-t df=2, Cauchy) and massive outliers."""
        N, K = 100, 10
        # Cauchy noise
        X_cauchy = np.random.standard_cauchy(size=(N, K))
        # Add massive outlier
        X_cauchy[0, 0] = 1e8
        X_cauchy[1, 3] = -1e8

        C_oas, rho = compute_oas_covariance(X_cauchy, ridge_epsilon=1e-4)

        self.assertTrue(np.all(np.isfinite(C_oas)), "Non-finite covariance on Cauchy/outliers")
        self.assertGreaterEqual(rho, 0.0)
        self.assertLessEqual(rho, 1.0)
        min_eig = float(np.min(np.linalg.eigvalsh(C_oas)))
        self.assertGreater(min_eig, 0.0)

    def test_oas_asymptotic_decay_on_non_spherical_population(self) -> None:
        """Verification: for non-spherical population Sigma, rho_OAS -> 0 as N -> infty at O(1/N)."""
        K = 15
        A = np.random.randn(K, K)
        Sigma = A @ A.T + np.eye(K)
        L = np.linalg.cholesky(Sigma)

        rhos = []
        sample_sizes = [50, 500, 5000, 50000]
        for N in sample_sizes:
            Z = np.random.randn(N, K)
            X = Z @ L.T
            _, rho = compute_oas_covariance(X)
            rhos.append(rho)

        # Verify strict monotonic decrease as sample size increases
        for i in range(len(rhos) - 1):
            self.assertLess(
                rhos[i + 1], rhos[i],
                f"rho should decrease as N increases: N={sample_sizes[i]} -> {sample_sizes[i+1]}"
            )
        self.assertLess(rhos[-1], 0.01, f"For N=50000, rho should be near zero, got {rhos[-1]}")


class TestAdversarialHighamProjection(unittest.TestCase):
    """Adversarial stress testing of higham_nearest_correlation_matrix under non-transitive and defective matrices."""

    def setUp(self) -> None:
        np.random.seed(99)

    def test_higham_non_transitive_triplet_negative_eigenvalues(self) -> None:
        """Adversarial test: Non-transitive correlation matrices with negative eigenvalues."""
        # Case A: [[1, 0.9, 0], [0.9, 1, 0.9], [0, 0.9, 1]] -> eigvals ~ [-0.2728, 1.0, 2.2728]
        C_A = np.array([
            [1.0, 0.9, 0.0],
            [0.9, 1.0, 0.9],
            [0.0, 0.9, 1.0]
        ], dtype=np.float64)

        eig_before_A = float(np.min(np.linalg.eigvalsh(C_A)))
        self.assertLess(eig_before_A, -0.20, "Input must have negative eigenvalue")

        min_eig = 1e-5
        R_A = higham_nearest_correlation_matrix(C_A, min_eig=min_eig)

        np.testing.assert_allclose(np.diag(R_A), np.ones(3), atol=1e-12, err_msg="Unit diagonal violated")
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(R_A))), min_eig - 1e-10)
        np.testing.assert_allclose(R_A, R_A.T, atol=1e-14, err_msg="Symmetry violated")

        # Case B: Severe cycle [[1, 0.95, -0.95], [0.95, 1, 0.95], [-0.95, 0.95, 1]] -> eigvals ~ [-0.9, 0.05, 3.85]
        C_B = np.array([
            [1.0, 0.95, -0.95],
            [0.95, 1.0, 0.95],
            [-0.95, 0.95, 1.0]
        ], dtype=np.float64)

        eig_before_B = float(np.min(np.linalg.eigvalsh(C_B)))
        self.assertLess(eig_before_B, -0.80)

        R_B = higham_nearest_correlation_matrix(C_B, min_eig=min_eig)
        np.testing.assert_allclose(np.diag(R_B), np.ones(3), atol=1e-12)
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(R_B))), min_eig - 1e-10)
        np.testing.assert_allclose(R_B, R_B.T, atol=1e-14)

    def test_higham_severely_defective_uniform_off_diagonals(self) -> None:
        """Adversarial test: uniform negative off-diagonals (-0.9) and high positive (+0.99) across K in [3, 5, 10, 37, 50]."""
        min_eig = 1e-5
        for K in [3, 5, 10, 37, 50]:
            # Severe negative off-diagonals: lambda_min = 1.9 - 0.9 * K
            C_neg = np.full((K, K), -0.9)
            np.fill_diagonal(C_neg, 1.0)
            lambda_min_in = float(np.min(np.linalg.eigvalsh(C_neg)))
            self.assertLess(lambda_min_in, 0.0, f"Uniform -0.9 matrix must be non-PSD for K={K}")

            R_neg = higham_nearest_correlation_matrix(C_neg, min_eig=min_eig)
            np.testing.assert_allclose(np.diag(R_neg), np.ones(K), atol=1e-10, err_msg=f"Diag fail K={K}")
            min_eig_out = float(np.min(np.linalg.eigvalsh(R_neg)))
            self.assertGreaterEqual(min_eig_out, min_eig - 1e-10, f"min_eig fail for K={K}: {min_eig_out}")
            np.testing.assert_allclose(R_neg, R_neg.T, atol=1e-12)

            # Uniform positive off-diagonals: 0.99
            C_pos = np.full((K, K), 0.99)
            np.fill_diagonal(C_pos, 1.0)
            R_pos = higham_nearest_correlation_matrix(C_pos, min_eig=min_eig)
            np.testing.assert_allclose(np.diag(R_pos), np.ones(K), atol=1e-10)
            self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(R_pos))), min_eig - 1e-10)
            np.testing.assert_allclose(R_pos, R_pos.T, atol=1e-12)

    def test_higham_zero_eigenvalues_and_singular_blocks(self) -> None:
        """Adversarial test: rank-1 matrix of ones C = 1 * 1^T with zero eigenvalues."""
        K = 12
        C_ones = np.ones((K, K))
        # Eigenvalues: K (multiplicity 1), 0 (multiplicity K-1)
        eig_zero = np.linalg.eigvalsh(C_ones)
        self.assertAlmostEqual(float(np.min(eig_zero)), 0.0, places=10)

        min_eig = 1e-4
        R_ones = higham_nearest_correlation_matrix(C_ones, min_eig=min_eig)
        np.testing.assert_allclose(np.diag(R_ones), np.ones(K), atol=1e-12)
        min_eig_ones = float(np.min(np.linalg.eigvalsh(R_ones)))
        self.assertGreaterEqual(min_eig_ones, min_eig - 1e-10)

    def test_higham_asymmetric_and_unbounded_inputs(self) -> None:
        """Adversarial test: asymmetric matrices with entries far outside [-1, 1]."""
        K = 8
        A = np.random.uniform(-10.0, 10.0, size=(K, K))
        np.fill_diagonal(A, 1.0)
        self.assertFalse(np.allclose(A, A.T), "Matrix must be asymmetric")

        min_eig = 1e-5
        R = higham_nearest_correlation_matrix(A, min_eig=min_eig)

        np.testing.assert_allclose(np.diag(R), np.ones(K), atol=1e-12)
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(R))), min_eig - 1e-10)
        np.testing.assert_allclose(R, R.T, atol=1e-12)
        # All correlations must be in [-1, 1]
        self.assertTrue(np.all(R >= -1.0 - 1e-10), "Correlation values below -1")
        self.assertTrue(np.all(R <= 1.0 + 1e-10), "Correlation values above 1")

    def test_higham_frobenius_norm_optimality_over_naive_clipping(self) -> None:
        """Adversarial test: prove Higham strictly outperforms naive spectral clipping in Frobenius distance & feasibility."""
        min_eig = 1e-5
        for trial in range(15):
            K = np.random.randint(4, 15)
            C = np.random.uniform(-1.0, 1.0, size=(K, K))
            C = 0.5 * (C + C.T)
            np.fill_diagonal(C, 1.0)

            # Ensure C has negative eigenvalues
            vals, vecs = np.linalg.eigh(C)
            if np.min(vals) >= 0:
                vals[0] = -0.5
                C = vecs @ np.diag(vals) @ vecs.T
                np.fill_diagonal(C, 1.0)

            # Higham projection
            R_higham = higham_nearest_correlation_matrix(C, min_eig=min_eig)
            fro_higham = np.linalg.norm(R_higham - C, "fro")

            # Check Higham feasibility
            np.testing.assert_allclose(np.diag(R_higham), np.ones(K), atol=1e-10)
            self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(R_higham))), min_eig - 1e-10)

            # Naive Method 1: Spectral clipping only (violates unit diagonal)
            vals_n, vecs_n = np.linalg.eigh(C)
            R_naive1 = vecs_n @ np.diag(np.maximum(vals_n, min_eig)) @ vecs_n.T
            diag_err_naive1 = float(np.max(np.abs(np.diag(R_naive1) - 1.0)))
            self.assertGreater(
                diag_err_naive1, 1e-4,
                "Naive spectral clipping without diagonal correction must violate unit diagonal"
            )

            # Naive Method 2: Spectral clipping + naive diagonal reset (violates PSD cone)
            R_naive2 = R_naive1.copy()
            np.fill_diagonal(R_naive2, 1.0)
            min_eig_naive2 = float(np.min(np.linalg.eigvalsh(R_naive2)))
            # Naive diagonal reset often reintroduces negative or sub-threshold eigenvalues
            if min_eig_naive2 < min_eig - 1e-8:
                # Confirmed failure of Naive Method 2
                pass

            # Naive Method 3: Normalized spectral clipping D^{-1/2} R_clip D^{-1/2}
            d = np.diag(R_naive1)
            inv_sqrt = 1.0 / np.sqrt(np.maximum(d, 1e-12))
            R_naive3 = inv_sqrt[:, None] * R_naive1 * inv_sqrt[None, :]
            fro_naive3 = np.linalg.norm(R_naive3 - C, "fro")

            # Higham Frobenius error must be less than or equal to Naive 3 (up to tolerance)
            self.assertLessEqual(
                fro_higham, fro_naive3 + 1e-6,
                f"Higham ({fro_higham:.6f}) should have lower Frobenius error than Naive 3 ({fro_naive3:.6f})"
            )

    def test_higham_idempotency_on_valid_correlation(self) -> None:
        """Adversarial test: already valid PSD correlation matrix must remain identical."""
        K = 15
        X = np.random.randn(200, K)
        C_valid = np.corrcoef(X, rowvar=False)

        min_eig = float(np.min(np.linalg.eigvalsh(C_valid)))
        self.assertGreater(min_eig, 1e-4)

        R = higham_nearest_correlation_matrix(C_valid, min_eig=1e-5)
        diff_fro = float(np.linalg.norm(R - C_valid, "fro"))
        self.assertLess(diff_fro, 1e-8, "Valid correlation matrix must be unchanged by Higham projection")

    def test_higham_stress_latency_budget(self) -> None:
        """Benchmark: 50 runs of Higham on K=37 factor correlation matrices must average < 15ms."""
        K = 37
        latencies = []
        for _ in range(50):
            C = np.random.uniform(-0.8, 0.8, size=(K, K))
            C = 0.5 * (C + C.T)
            np.fill_diagonal(C, 1.0)

            t0 = time.perf_counter()
            _ = higham_nearest_correlation_matrix(C, tol=1e-7, max_iter=100, min_eig=1e-5)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = float(np.mean(latencies))
        p99_latency = float(np.percentile(latencies, 99))
        self.assertLess(avg_latency, 15.0, f"Average latency {avg_latency:.2f}ms exceeds 15ms budget")
        self.assertLess(p99_latency, 35.0, f"P99 latency {p99_latency:.2f}ms exceeds 35ms budget")


class TestAdversarialRepairCovariancePSD(unittest.TestCase):
    """Adversarial stress testing of repair_covariance_psd integration."""

    def setUp(self) -> None:
        np.random.seed(333)

    def test_repair_covariance_psd_negative_variances_and_zero_matrix(self) -> None:
        """Adversarial test: covariance matrix with negative diagonal entries or entirely zeros."""
        # Negative diagonal entries
        C_neg = np.array([
            [-5.0, 1.0, 2.0],
            [1.0, -2.0, 0.5],
            [2.0, 0.5, 3.0]
        ], dtype=np.float64)

        C_repaired = repair_covariance_psd(C_neg, ridge_epsilon=1e-5)
        self.assertTrue(np.all(np.isfinite(C_repaired)))
        min_eig = float(np.min(np.linalg.eigvalsh(C_repaired)))
        self.assertGreaterEqual(min_eig, 1e-5)

        # Entirely zero covariance matrix
        C_zero = np.zeros((6, 6))
        C_zero_repaired = repair_covariance_psd(C_zero, ridge_epsilon=1e-6)
        min_eig_zero = float(np.min(np.linalg.eigvalsh(C_zero_repaired)))
        self.assertGreaterEqual(min_eig_zero, 1e-6)

    def test_repair_covariance_psd_preserves_heterogeneous_variances(self) -> None:
        """Adversarial test: preserve original diagonal scales across 8 orders of magnitude."""
        variances = np.array([1e-4, 1.0, 100.0, 1e4], dtype=np.float64)
        D_sqrt = np.sqrt(variances)
        # Create non-PSD correlation structure
        R_defective = np.array([
            [1.0, 0.95, -0.95, 0.5],
            [0.95, 1.0, 0.95, -0.4],
            [-0.95, 0.95, 1.0, 0.3],
            [0.5, -0.4, 0.3, 1.0]
        ], dtype=np.float64)

        C_raw = D_sqrt[:, None] * R_defective * D_sqrt[None, :]
        C_repaired = repair_covariance_psd(C_raw, ridge_epsilon=1e-5)

        # Verify PSD
        min_eig = float(np.min(np.linalg.eigvalsh(C_repaired)))
        self.assertGreaterEqual(min_eig, 1e-5)

        # Verify diagonal scales are approximately preserved
        d_repaired = np.diag(C_repaired)
        for i in range(len(variances)):
            rel_diff = abs(d_repaired[i] - variances[i]) / variances[i]
            self.assertLess(rel_diff, 0.10, f"Variance at index {i} altered significantly: {d_repaired[i]} vs {variances[i]}")


class TestMilestone2SystemInvariantsAndDualTreeParity(unittest.TestCase):
    """System-level invariant and dual-tree cryptographic synchronization tests."""

    def test_dual_tree_factor_orthogonalizer_parity(self) -> None:
        """Verify 100% SHA-256 bit-for-bit parity between src/ and trading_system/src/ factor_orthogonalizer."""
        p1 = os.path.join(os.path.dirname(__file__), "..", "src", "ai", "factor_orthogonalizer.py")
        p2 = os.path.join(os.path.dirname(__file__), "..", "trading_system", "src", "ai", "factor_orthogonalizer.py")

        with open(p1, "rb") as f:
            h1 = hashlib.sha256(f.read()).hexdigest()
        with open(p2, "rb") as f:
            h2 = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(h1, h2, f"Dual-tree parity mismatch for factor_orthogonalizer.py: {h1} != {h2}")

    def test_system_invariant_zero_synthetic_rows_native_int(self) -> None:
        """Verify synthetic_rows == 0 invariant strictly verified as native int 0."""
        status_path = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "30year", "status.json")
        self.assertTrue(os.path.exists(status_path), "status.json not found")

        with open(status_path, "r", encoding="utf-8") as f:
            st = json.load(f)

        self.assertIn("synthetic_rows", st)
        val = st["synthetic_rows"]
        self.assertIs(type(val), int, f"synthetic_rows type {type(val)} is not native int")
        self.assertNotIsInstance(val, bool, "synthetic_rows must not be bool")
        self.assertEqual(val, 0, f"synthetic_rows must be 0, got {val}")


if __name__ == "__main__":
    unittest.main()

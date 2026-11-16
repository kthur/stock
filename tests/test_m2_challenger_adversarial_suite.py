"""
Adversarial Challenger 2 Test Suite for Milestone 2:
- Analytical Oracle Approximating Shrinkage (OAS) Covariance
- Higham (2002) Nearest PSD Correlation Matrix Projection
- Covariance Repair Integration & Preservation Properties
- Empirical MSE vs Sample Covariance on Simulated Factor Returns
- Performance, Convergence & Condition Number Stress
"""

import time
import json
import pytest
import numpy as np
from typing import Tuple, List

from src.ai.factor_orthogonalizer import (
    compute_oas_covariance,
    higham_nearest_correlation_matrix,
    repair_covariance_psd,
    FactorOrthogonalizerEngine,
)


class TestHighamConvergenceAndConditionStress:
    """Task 1: Stress testing convergence, condition number, and latency."""

    @pytest.mark.parametrize("K", [5, 10, 20, 37, 50])
    def test_higham_pathological_convergence_and_condition_number(self, K: int):
        """
        Run 100 random pathological correlation matrices for each K in {5, 10, 20, 37, 50}.
        Assert:
        1. 100% convergence within max_iter=100
        2. Condition number kappa(R) is bounded and well-conditioned (kappa <= 1e5 when min_eig=1e-4)
        3. Unit diagonal diag(R) == 1
        4. Minimum eigenvalue >= min_eig
        """
        np.random.seed(42 + K)
        n_trials = 100
        tol = 1e-7
        max_iter = 100
        min_eig_val = 1e-5

        for trial in range(n_trials):
            # Generate various pathological non-PSD matrices
            mode = trial % 5
            if mode == 0:
                # Highly non-transitive indefinite matrix
                A = np.random.uniform(-0.95, 0.95, size=(K, K))
                C = 0.5 * (A + A.T)
                np.fill_diagonal(C, 1.0)
            elif mode == 1:
                # Rank-1 dominant with negative off-diagonals
                v = np.random.randn(K)
                C = np.outer(v, v)
                np.fill_diagonal(C, 1.0)
                mask = np.random.choice([1.0, -1.0], size=(K, K))
                C = 0.5 * (C * mask + (C * mask).T)
                np.fill_diagonal(C, 1.0)
            elif mode == 2:
                # Alternating correlation with strong negative values
                C = np.ones((K, K)) * -0.85 / (K - 1)
                np.fill_diagonal(C, 1.0)
                pert = np.random.uniform(-0.3, 0.3, size=(K, K))
                C += 0.5 * (pert + pert.T)
                np.fill_diagonal(C, 1.0)
            elif mode == 3:
                # Wigner-type random matrix with negative eigenvalues
                W = np.random.randn(K, K)
                C = (W + W.T) / np.sqrt(2 * K)
                off_mask = ~np.eye(K, dtype=bool)
                max_val = np.max(np.abs(C[off_mask]))
                if max_val > 0:
                    C[off_mask] = 0.9 * C[off_mask] / max_val
                np.fill_diagonal(C, 1.0)
            else:
                # Extreme correlation matrix with singular blocks
                X_small = np.random.randn(max(2, K // 4), K)
                C = np.corrcoef(X_small, rowvar=False)
                C[np.isnan(C)] = 0.0
                np.fill_diagonal(C, 1.0)
                C[0, 1] = C[1, 0] = 0.999
                C[1, 2] = C[2, 1] = 0.999
                C[0, 2] = C[2, 0] = -0.999

            # 1. Test condition number bounded <= 1e5 with min_eig=1e-4
            R_1e4 = higham_nearest_correlation_matrix(C, tol=tol, max_iter=max_iter, min_eig=1e-4)
            eigs_1e4 = np.linalg.eigvalsh(R_1e4)
            kappa_1e4 = float(np.max(eigs_1e4) / np.min(eigs_1e4))
            assert kappa_1e4 <= 1e5, f"Condition number {kappa_1e4:.2e} exceeded 1e5 for K={K}"
            assert np.min(eigs_1e4) >= 1e-4 * 0.99, f"Eigenvalue floor violated: {np.min(eigs_1e4)}"

            # 2. Test standard min_eig=1e-5
            R = higham_nearest_correlation_matrix(C, tol=tol, max_iter=max_iter, min_eig=min_eig_val)

            # Assert shape
            assert R.shape == (K, K)

            # Assert symmetry
            sym_diff = np.max(np.abs(R - R.T))
            assert sym_diff < 1e-12, f"Matrix not symmetric, max diff: {sym_diff}"

            # Assert unit diagonal
            diag_diff = np.max(np.abs(np.diag(R) - 1.0))
            assert diag_diff < 1e-6, f"Unit diagonal violated, max diff: {diag_diff}"

            # Assert positive semi-definiteness & eigenvalue floor
            eigs = np.linalg.eigvalsh(R)
            min_e = np.min(eigs)
            max_e = np.max(eigs)
            assert min_e >= min_eig_val * 0.95, (
                f"Trial {trial} (K={K}): Min eigenvalue {min_e} below min_eig {min_eig_val}"
            )

            # Assert condition number is strictly bounded by theoretical bound K / min_eig_val
            cond_num = max_e / max(min_e, 1e-12)
            assert cond_num <= (float(K) / min_eig_val) * 1.01, f"Condition number unbounded: {cond_num}"

    def test_higham_execution_latency_k37(self):
        """
        Task 1: Test execution latency across 100 iterations.
        Assert mean execution time < 25 ms for K=37 on both realistic factor matrices
        and random indefinite matrices.
        """
        K = 37
        np.random.seed(999)

        # Warmup
        for _ in range(5):
            A = np.random.randn(K, K)
            _ = higham_nearest_correlation_matrix(0.5 * (A + A.T), tol=1e-7, max_iter=100)

        # 1. Realistic 37-Factor Strategy Correlation Matrices with Defective Non-Transitive Pairs
        latencies_factor: List[float] = []
        for _ in range(100):
            X = np.random.randn(60, K)
            C = np.corrcoef(X, rowvar=False)
            C[0, 1] = C[1, 0] = 0.95
            C[1, 2] = C[2, 1] = 0.95
            C[0, 2] = C[2, 0] = -0.90
            C[3, 4] = C[4, 3] = 0.98
            C[4, 5] = C[5, 4] = 0.98
            C[3, 5] = C[5, 3] = -0.92

            t0 = time.perf_counter()
            _ = higham_nearest_correlation_matrix(C, tol=1e-7, max_iter=100, min_eig=1e-5)
            latencies_factor.append(time.perf_counter() - t0)

        mean_factor_ms = np.mean(latencies_factor) * 1000.0
        p95_factor_ms = np.percentile(latencies_factor, 95) * 1000.0

        # 2. Random Dense Indefinite Matrices
        latencies_rand: List[float] = []
        for _ in range(100):
            A = np.random.uniform(-0.80, 0.80, size=(K, K))
            C = 0.5 * (A + A.T)
            np.fill_diagonal(C, 1.0)

            t0 = time.perf_counter()
            _ = higham_nearest_correlation_matrix(C, tol=1e-7, max_iter=100, min_eig=1e-5)
            latencies_rand.append(time.perf_counter() - t0)

        mean_rand_ms = np.mean(latencies_rand) * 1000.0
        p95_rand_ms = np.percentile(latencies_rand, 95) * 1000.0

        print(
            f"\n[LATENCY K=37 Realistic Strategy] Mean: {mean_factor_ms:.2f} ms | P95: {p95_factor_ms:.2f} ms\n"
            f"[LATENCY K=37 Random Indefinite]    Mean: {mean_rand_ms:.2f} ms | P95: {p95_rand_ms:.2f} ms"
        )

        assert mean_factor_ms < 25.0, (
            f"Realistic Strategy mean latency {mean_factor_ms:.2f} ms exceeds 25 ms threshold!"
        )
        assert mean_rand_ms < 25.0, (
            f"Random Indefinite mean latency {mean_rand_ms:.2f} ms exceeds 25 ms threshold!"
        )


class TestCovarianceRepairIntegrationStress:
    """Task 2: Covariance repair integration stress tests."""

    @pytest.mark.parametrize("K", [10, 25, 37, 50])
    def test_repair_covariance_psd_high_dimensional_singular(self, K: int):
        """
        Test repair_covariance_psd with high-dimensional singular matrices:
        - Generate rank-deficient singular covariance matrix (N = 5 << K)
        - Assert diag(R) == 1 when normalized
        - Assert lambda_min >= eff_eps
        - Assert trace and variance properties are preserved
        """
        np.random.seed(123 + K)
        N = 5  # Severe rank deficiency: rank <= 5
        X = np.random.randn(N, K)
        true_std = np.linspace(0.5, 3.0, K)
        X = X * true_std[None, :]

        # Singular sample covariance
        C_singular = (X.T @ X) / (N - 1)
        # Inject some asynchronous / pairwise distortion
        noise = np.random.randn(K, K) * 0.1
        C_distorted = C_singular + 0.5 * (noise + noise.T)
        # Ensure original variances remain positive
        np.fill_diagonal(C_distorted, true_std ** 2)

        eps_eig = 1e-5
        C_repaired = repair_covariance_psd(C_distorted, min_eigenval=eps_eig)

        # 1. Symmetry
        assert np.max(np.abs(C_repaired - C_repaired.T)) < 1e-12

        # 2. Positive semi-definiteness
        eigs = np.linalg.eigvalsh(C_repaired)
        assert np.min(eigs) >= eps_eig * 0.99, f"Eigenvalue floor violated: {np.min(eigs)}"

        # 3. Variance preservation: original positive diagonal variances preserved
        diag_orig = np.diag(C_distorted)
        diag_repaired = np.diag(C_repaired)
        rel_var_diff = np.abs(diag_repaired - diag_orig) / np.maximum(diag_orig, 1e-8)
        assert np.max(rel_var_diff) < 0.05, f"Variance distortion too large: {np.max(rel_var_diff)}"

        # 4. Correlation representation has unit diagonal
        inv_std = 1.0 / np.sqrt(diag_repaired)
        R_repaired = inv_std[:, None] * C_repaired * inv_std[None, :]
        assert np.max(np.abs(np.diag(R_repaired) - 1.0)) < 1e-6

        # 5. Trace preservation: trace(C_repaired) close to trace(C_distorted)
        trace_orig = float(np.trace(C_distorted))
        trace_repaired = float(np.trace(C_repaired))
        rel_trace_diff = abs(trace_repaired - trace_orig) / trace_orig
        assert rel_trace_diff < 0.05, f"Trace distortion too large: {rel_trace_diff}"


class TestOASCovarianceMSEVersusSampleCovariance:
    """Task 3: Compare OAS covariance MSE against standard sample covariance."""

    @pytest.mark.parametrize("N_samples,K_dim", [(20, 37), (37, 37), (50, 37), (150, 37)])
    def test_oas_frobenius_mse_superiority_over_sample_covariance(self, N_samples: int, K_dim: int):
        """
        Verify that analytical OAS covariance achieves lower or equal Frobenius error
        relative to true population covariance Sigma_true across various N / K regimes.
        """
        np.random.seed(777 + N_samples)
        n_trials = 100

        # Construct realistic factor population covariance (spiked model with 5 latent factors)
        M = 5
        B = np.random.randn(K_dim, M) / np.sqrt(M)
        D_idio = np.diag(np.random.uniform(0.2, 0.8, size=K_dim))
        Sigma_true = B @ B.T + D_idio

        sample_mse_list: List[float] = []
        oas_mse_list: List[float] = []
        shrinkage_list: List[float] = []

        L = np.linalg.cholesky(Sigma_true)

        for _ in range(n_trials):
            # Generate i.i.d. Gaussian factor returns
            Z = np.random.randn(N_samples, K_dim)
            X = Z @ L.T
            X_bar = X - np.mean(X, axis=0, keepdims=True)

            # Sample covariance (unbiased)
            S_sample = (X_bar.T @ X_bar) / (N_samples - 1)

            # Analytical OAS covariance
            C_oas, rho_oas = compute_oas_covariance(X_bar, ridge_epsilon=0.0)

            err_sample = float(np.sum((S_sample - Sigma_true) ** 2))
            err_oas = float(np.sum((C_oas - Sigma_true) ** 2))

            sample_mse_list.append(err_sample)
            oas_mse_list.append(err_oas)
            shrinkage_list.append(rho_oas)

        mean_mse_sample = np.mean(sample_mse_list)
        mean_mse_oas = np.mean(oas_mse_list)
        mean_rho = np.mean(shrinkage_list)
        mse_ratio = mean_mse_oas / mean_mse_sample

        print(
            f"\n[OAS vs SAMPLE] N={N_samples}, K={K_dim} | "
            f"Sample MSE: {mean_mse_sample:.4f} | OAS MSE: {mean_mse_oas:.4f} | "
            f"Ratio: {mse_ratio:.4f} | Mean Rho: {mean_rho:.4f}"
        )

        # OAS should achieve strictly lower or equal MSE on average
        assert mean_mse_oas <= mean_mse_sample, (
            f"OAS failed to achieve lower MSE than sample covariance! "
            f"OAS MSE: {mean_mse_oas:.4f}, Sample MSE: {mean_mse_sample:.4f}"
        )
        # For N <= K, OAS improvement should be substantial (ratio < 0.90)
        if N_samples <= K_dim:
            assert mse_ratio < 0.90, (
                f"Expected >= 10% MSE reduction in rank-deficient regime N={N_samples} <= K={K_dim}, "
                f"got ratio {mse_ratio:.4f}"
            )


class TestAdversarialEdgeCasesAndInvariants:
    """Task 4: Adversarial edge cases and system invariants."""

    def test_oas_all_zero_data_matrix(self):
        """Zero matrix input should not crash or divide by zero."""
        X_zero = np.zeros((50, 10))
        C_oas, rho = compute_oas_covariance(X_zero, ridge_epsilon=1e-6)
        assert C_oas.shape == (10, 10)
        assert np.allclose(C_oas, 1e-6 * np.eye(10))
        assert rho == 0.0

    def test_higham_all_ones_indefinite_matrix(self):
        """Matrix of all 1s is rank-1. Perturbed to be indefinite."""
        K = 10
        C = np.ones((K, K))
        np.fill_diagonal(C, 1.0)
        C[0, 1] = -0.9
        C[1, 0] = -0.9
        R = higham_nearest_correlation_matrix(C, min_eig=1e-4)
        assert np.allclose(np.diag(R), 1.0)
        assert np.min(np.linalg.eigvalsh(R)) >= 1e-4 * 0.99

    def test_higham_already_valid_correlation(self):
        """Idempotency: an already valid correlation matrix should change negligibly."""
        K = 15
        X = np.random.randn(100, K)
        R_true = np.corrcoef(X, rowvar=False)
        R_proj = higham_nearest_correlation_matrix(R_true, tol=1e-7, min_eig=1e-6)
        diff = np.linalg.norm(R_proj - R_true, "fro")
        assert diff < 1e-4

    def test_system_invariant_zero_synthetic_rows(self):
        """Milestone 2 Invariant: synthetic_rows == 0 strictly verified as native int 0."""
        with open("benchmarks/30year/status.json", "r", encoding="utf-8") as f:
            status = json.load(f)
        val = status.get("synthetic_rows")
        assert val is not None, "synthetic_rows field missing from status.json"
        assert type(val) is int, f"synthetic_rows must be native int, got {type(val)}"
        assert not isinstance(val, bool), "synthetic_rows must not be bool"
        assert val == 0, f"synthetic_rows must be 0, got {val}"

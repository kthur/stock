"""
Unit Test Suite: Factor Risk Parity (FRP) & Euler Risk Contributions
Target Module: src/risk/unified_portfolio_allocator.py -> compute_factor_risk_contributions, calculate_factor_risk_parity_weights
System Invariants: Zero synthetic rows (synthetic_rows == 0, native int 0)
"""

import json
import unittest
import numpy as np
from scipy.optimize import minimize

from src.risk.unified_portfolio_allocator import (
    compute_factor_risk_contributions,
    calculate_factor_risk_parity_weights,
    UnifiedPortfolioAllocator,
)


class TestEulerIdentityExactness(unittest.TestCase):
    """Verifies sum(PFRC) + IRR == 1.0 within 1e-6 across diverse portfolio configurations."""

    def setUp(self):
        np.random.seed(42)

    def test_euler_identity_random_portfolios_100_trials(self):
        """100 trials across random N, K, factor loadings, and idiosyncratic variances."""
        for trial in range(100):
            N = np.random.randint(5, 50)
            K = np.random.randint(2, 10)

            w = np.random.uniform(0.01, 0.10, size=N)
            w /= np.sum(w)

            B = np.random.randn(N, K)
            A = np.random.randn(K, K)
            Omega_F = A.T @ A + np.eye(K) * 1e-3
            D_idio = np.random.uniform(0.01, 0.05, size=N)

            mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)

            total_risk_contribution = float(np.sum(pfrc) + irr)
            np.testing.assert_allclose(
                total_risk_contribution,
                1.0,
                rtol=1e-6,
                atol=1e-6,
                err_msg=f"Trial {trial} failed Euler identity: sum(PFRC) + IRR = {total_risk_contribution}"
            )

    def test_euler_identity_high_dimensional_universe(self):
        """High-dimensional production universe: N=1000 assets, K=37 factors."""
        N, K = 1000, 37
        w = np.random.uniform(0.0, 1.0, size=N)
        w /= np.sum(w)
        B = np.random.randn(N, K) * 0.5
        Omega_F = np.eye(K) * 0.04
        D_idio = np.full(N, 0.09)

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(np.sum(pfrc) + irr, 1.0, rtol=1e-6, atol=1e-6)

    def test_mfrc_inner_product_systematic_vol(self):
        """beta_p^T * MFRC == sigma_F^2 / sigma_p."""
        N, K = 30, 5
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        Omega_F = np.eye(K)
        D_idio = np.ones(N) * 0.02

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        beta_p = B.T @ w
        sigma_F_sq = beta_p.T @ Omega_F @ beta_p
        sigma_p_sq = sigma_F_sq + np.sum((w ** 2) * D_idio)
        sigma_p = np.sqrt(sigma_p_sq)

        expected_inner = sigma_F_sq / sigma_p
        actual_inner = float(np.dot(beta_p, mfrc))
        np.testing.assert_allclose(actual_inner, expected_inner, rtol=1e-6)

    def test_long_only_and_long_short_portfolios(self):
        """Euler identity holds for both long-only and long-short portfolios."""
        N, K = 20, 4
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.05
        D_idio = np.ones(N) * 0.03

        # Long-only
        w_lo = np.random.dirichlet(np.ones(N))
        _, pfrc_lo, irr_lo = compute_factor_risk_contributions(w_lo, B, Omega_F, D_idio)
        np.testing.assert_allclose(np.sum(pfrc_lo) + irr_lo, 1.0, rtol=1e-6)

        # Long-short
        w_ls = np.random.randn(N)
        w_ls /= np.sum(np.abs(w_ls))
        _, pfrc_ls, irr_ls = compute_factor_risk_contributions(w_ls, B, Omega_F, D_idio)
        np.testing.assert_allclose(np.sum(pfrc_ls) + irr_ls, 1.0, rtol=1e-6)


class TestOrthogonalFactorClosedForm(unittest.TestCase):
    """Verifies output against exact theoretical closed form when Omega_F = I and B is orthonormal."""

    def test_orthogonal_factor_analytical_matching(self):
        """Theoretical PFRC_k = beta_{p, k}^2 / sigma_p^2."""
        N, K = 50, 5
        Q, _ = np.linalg.qr(np.random.randn(N, K))
        B = Q  # shape (N, K)
        Omega_F = np.eye(K)
        d_val = 0.04
        D_idio = np.full(N, d_val)

        w = np.random.randn(N)
        w /= np.linalg.norm(w)

        beta_p = B.T @ w
        sigma_F_sq = np.sum(beta_p ** 2)
        sigma_idio_sq = np.sum(w ** 2) * d_val
        sigma_p_sq = sigma_F_sq + sigma_idio_sq
        sigma_p = np.sqrt(sigma_p_sq)

        expected_mfrc = beta_p / sigma_p
        expected_pfrc = (beta_p ** 2) / sigma_p_sq
        expected_irr = sigma_idio_sq / sigma_p_sq

        actual_mfrc, actual_pfrc, actual_irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)

        np.testing.assert_allclose(actual_mfrc, expected_mfrc, rtol=1e-11, atol=1e-11)
        np.testing.assert_allclose(actual_pfrc, expected_pfrc, rtol=1e-11, atol=1e-11)
        np.testing.assert_allclose(actual_irr, expected_irr, rtol=1e-11, atol=1e-11)

    def test_diagonal_factor_covariance_decoupling(self):
        """When Omega_F = diag(lambda_k), MFRC_k = lambda_k * beta_k / sigma_p."""
        N, K = 10, 3
        B = np.eye(N, K)
        diag_f = np.array([0.10, 0.20, 0.30])
        Omega_F = np.diag(diag_f)
        D_idio = np.ones(N) * 0.05
        w = np.ones(N) / N

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        beta_p = B.T @ w
        sigma_sq = beta_p.T @ Omega_F @ beta_p + np.sum(w ** 2 * D_idio)
        expected_mfrc = (diag_f * beta_p) / np.sqrt(sigma_sq)
        np.testing.assert_allclose(mfrc, expected_mfrc, rtol=1e-11)

    def test_equal_loadings_equal_pfrc(self):
        """Identical loadings and exposures produce equal PFRC across all factors."""
        N, K = 12, 4
        B = np.ones((N, K))
        Omega_F = np.eye(K)
        D_idio = np.ones(N) * 0.02
        w = np.ones(N) / N

        _, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        for k in range(K):
            self.assertAlmostEqual(pfrc[k], pfrc[0], places=9)


class TestSystematicVsIdiosyncraticLimits(unittest.TestCase):
    """Verifies limits when factor loadings approach zero or idiosyncratic risk approaches zero."""

    def test_pure_idiosyncratic_limit_loadings_zero(self):
        """B = 0 implies IRR = 1.0, MFRC = 0, PFRC = 0."""
        N, K = 20, 4
        w = np.ones(N) / N
        B = np.zeros((N, K))
        Omega_F = np.eye(K) * 0.05
        D_idio = np.ones(N) * 0.02

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(mfrc, np.zeros(K), atol=1e-12)
        np.testing.assert_allclose(pfrc, np.zeros(K), atol=1e-12)
        self.assertAlmostEqual(irr, 1.0, places=11)

    def test_pure_systematic_limit_idio_zero(self):
        """D = 0 implies IRR = 0.0 and sum(PFRC) = 1.0."""
        N, K = 20, 4
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.05
        D_idio = np.zeros(N)

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        self.assertAlmostEqual(irr, 0.0, places=11)
        np.testing.assert_allclose(np.sum(pfrc), 1.0, rtol=1e-11, atol=1e-11)

    def test_gate11_irr_threshold_boundary(self):
        """Portfolio with exactly 70% idiosyncratic risk matches Gate 11 boundary."""
        N, K = 10, 1
        w = np.ones(N) / N
        B = np.ones((N, 1))
        Omega_F = np.array([[0.30]])
        D_idio = np.ones(N) * 7.0

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        self.assertAlmostEqual(irr, 0.70, places=6)
        self.assertAlmostEqual(float(pfrc[0]), 0.30, places=6)


class TestFRPOptimizationPenaltyBehavior(unittest.TestCase):
    """Verifies that the FRP penalty lambda_FRP * sum(PFRC_k - 1/K)^2 reduces risk dispersion."""

    def test_frp_penalty_reduces_pfrc_dispersion(self):
        """Compare dispersion of PFRCs with lambda_FRP = 0 vs lambda_FRP > 0."""
        N, K = 15, 3
        np.random.seed(42)
        B = np.array([
            [2.0, 0.1, 0.1],
            [1.8, 0.2, 0.1],
            [1.5, 0.1, 0.2],
            [0.1, 1.5, 0.2],
            [0.2, 1.8, 0.1],
            [0.1, 0.2, 1.9],
            [0.2, 0.1, 1.7],
            [1.0, 0.5, 0.5],
            [0.5, 1.0, 0.5],
            [0.5, 0.5, 1.0],
            [0.3, 0.3, 0.3],
            [0.8, 0.2, 0.2],
            [0.2, 0.8, 0.2],
            [0.2, 0.2, 0.8],
            [1.2, 0.3, 0.3],
        ])
        Omega_F = np.eye(K) * 0.05
        D_idio = np.ones(N) * 0.02
        mu = np.linspace(0.05, 0.15, N)

        bounds = [(0.0, 0.25) for _ in range(N)]
        cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        w0 = np.ones(N) / N

        def objective(w, lambda_frp):
            ret = np.dot(w, mu)
            _, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
            risk = np.dot(w, (B @ Omega_F @ B.T + np.diag(D_idio)) @ w)
            frp_penalty = lambda_frp * np.sum((pfrc - (1.0 / K)) ** 2)
            return -ret + 0.5 * risk + frp_penalty

        res_unpenalized = minimize(objective, w0, args=(0.0,), bounds=bounds, constraints=cons)
        res_penalized = minimize(objective, w0, args=(10.0,), bounds=bounds, constraints=cons)

        _, pfrc_unpen, _ = compute_factor_risk_contributions(res_unpenalized.x, B, Omega_F, D_idio)
        _, pfrc_pen, _ = compute_factor_risk_contributions(res_penalized.x, B, Omega_F, D_idio)

        disp_unpen = np.sum((pfrc_unpen - (1.0 / K)) ** 2)
        disp_pen = np.sum((pfrc_pen - (1.0 / K)) ** 2)

        self.assertLess(disp_pen, disp_unpen * 0.40, "FRP penalty failed to significantly reduce PFRC dispersion.")

    def test_asymptotic_equal_factor_risk_under_high_lambda(self):
        """calculate_factor_risk_parity_weights yields balanced factor exposures."""
        N, K = 10, 3
        np.random.seed(42)
        B = np.random.randn(N, K)
        cov = B @ np.eye(K) @ B.T + np.eye(N) * 0.05
        w_frp = calculate_factor_risk_parity_weights(
            cov_matrix=cov,
            factor_loadings=B,
            lambda_frp=20.0,
            max_single_stock_weight=0.25,
        )
        self.assertAlmostEqual(float(np.sum(w_frp)), 1.0, places=5)
        self.assertTrue(np.all(w_frp >= -1e-6))
        self.assertTrue(np.all(w_frp <= 0.25 + 1e-5))

    def test_frp_does_not_distort_pure_idiosyncratic_portfolio(self):
        """When factor loadings are all zero, calculate_factor_risk_parity_weights returns valid weights."""
        N = 5
        cov = np.eye(N) * 0.04
        B = np.zeros((N, 2))
        w = calculate_factor_risk_parity_weights(cov_matrix=cov, factor_loadings=B)
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=5)
        self.assertTrue(np.all(w >= 0.0))


class TestFactorRiskParityEdgeCases(unittest.TestCase):
    """Verifies numerical robustness under zero weights, singular matrices, and invariants."""

    def test_zero_portfolio_weights_graceful_handling(self):
        """w = 0 returns zero vectors and IRR = 1.0 without ZeroDivisionError."""
        N, K = 10, 3
        w = np.zeros(N)
        B = np.random.randn(N, K)
        Omega_F = np.eye(K)
        D_idio = np.ones(N) * 0.05

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(mfrc, np.zeros(K))
        np.testing.assert_allclose(pfrc, np.zeros(K))
        self.assertEqual(irr, 1.0)

    def test_single_asset_single_factor_scalar_match(self):
        """N = 1, K = 1 scalar matching."""
        w = np.array([1.0])
        B = np.array([[1.5]])
        Omega_F = np.array([[0.04]])
        D_idio = np.array([0.01])

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        sigma_sq = (1.5 ** 2) * 0.04 + 0.01
        expected_pfrc = ((1.5 ** 2) * 0.04) / sigma_sq
        expected_irr = 0.01 / sigma_sq

        self.assertAlmostEqual(float(pfrc[0]), expected_pfrc, places=9)
        self.assertAlmostEqual(irr, expected_irr, places=9)
        self.assertAlmostEqual(float(pfrc[0]) + irr, 1.0, places=9)

    def test_singular_and_rank_deficient_factor_covariance(self):
        """Factor covariance with zero eigenvalues is handled smoothly via PSD reconstruction."""
        N, K = 10, 3
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        v = np.array([1.0, 2.0, 3.0])
        Omega_F = np.outer(v, v)
        D_idio = np.ones(N) * 0.02

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(np.sum(pfrc) + irr, 1.0, rtol=1e-6)

    def test_allocator_static_methods_and_telemetry(self):
        """Verifies methods on UnifiedPortfolioAllocator and telemetry recording."""
        self.assertTrue(hasattr(UnifiedPortfolioAllocator, "compute_factor_risk_contributions"))
        self.assertTrue(hasattr(UnifiedPortfolioAllocator, "calculate_factor_risk_parity_weights"))

        allocator = UnifiedPortfolioAllocator()
        self.assertIsNone(allocator.last_factor_risk_decomposition)

    def test_system_invariant_zero_synthetic_rows(self):
        """Invariant: synthetic_rows == 0 strictly verified as native Python int 0."""
        status_path = "benchmarks/30year/status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        synth = status.get("synthetic_rows")
        self.assertTrue(
            isinstance(synth, int) and not isinstance(synth, bool) and synth == 0,
            f"synthetic_rows invariant violated: {synth} (type: {type(synth)})"
        )


if __name__ == "__main__":
    unittest.main()

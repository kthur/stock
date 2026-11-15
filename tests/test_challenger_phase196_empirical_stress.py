"""
tests/test_challenger_phase196_empirical_stress.py
==================================================
Empirical Adversarial Challenge and Stress-Testing Suite for Milestone 1 (Release R186 / Phase 196).

Authored by empirical challenger challenger_r186_m1_1.
Tests deep edge cases, extreme shocks, numerical singularities, non-Hermitian corruptions,
antipodal spherical transport, ill-conditioned covariances, and systemic risk limits.
"""

from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from src.core.stochastic_gradient_foliation import (
    decompose_foliation_tangent_bundle,
    compute_bott_holonomy_displacement,
    compute_foliated_ricci_curvature,
    detect_stress_transition,
    compute_foliation_alpha,
    apply_hyperbolic_noise_deadband,
    StochasticGradientFoliationEngine,
)
from src.core.quantum_lindblad_dissipation import (
    build_order_flow_density_matrix,
    build_system_hamiltonian,
    build_lindblad_jump_operators,
    compute_lindblad_dissipator,
    integrate_gksl_master_equation,
    compute_quantum_purity_and_entropy,
    compute_lindblad_dissipation_alpha,
    QuantumLindbladDissipationEngine,
)
from src.core.hyperspherical_optimal_transport import (
    project_to_hypersphere,
    compute_hyperspherical_geodesic_distance,
    compute_hyperspherical_cost_matrix,
    sinkhorn_knopp_optimal_transport,
    compute_hyperspherical_log_map,
    compute_directional_restoring_force,
    compute_hyperspherical_transport_alpha,
    HypersphericalOptimalTransportEngine,
)
from src.ai.factor_orthogonalizer import (
    compute_septendecuple_pillar_zca_whitening,
    compute_17pillar_zca_whitening,
    SEPTENDECUPLE_PILLAR_MAP,
    FactorOrthogonalizerEngine,
)
from src.ai.historical_couplers import (
    Phase196Coupler,
    Phase196MasterCoupler,
    SeptendecuplePillarCoupler,
)


class TestChallengerFoliationDeepStress(unittest.TestCase):
    """Deep Stress Testing of Feature F969: Stochastic Gradient Foliation."""

    def test_foliation_idempotency_orthogonality(self):
        """Verify geometric projection invariants P_L^2 = P_L, P_Q^2 = P_Q, P_L P_Q = 0, P_L + P_Q = I."""
        rng = np.random.default_rng(42)
        for d in [3, 5, 10, 20]:
            X = rng.normal(0, 0.02, size=(50, d))
            for q in [1, 2, d - 1]:
                P_L, P_Q, v_L, v_Q = decompose_foliation_tangent_bundle(X, codimension=q)
                I = np.eye(d)
                # Idempotency
                np.testing.assert_allclose(P_L @ P_L, P_L, atol=1e-10)
                np.testing.assert_allclose(P_Q @ P_Q, P_Q, atol=1e-10)
                # Mutual orthogonality
                np.testing.assert_allclose(P_L @ P_Q, np.zeros((d, d)), atol=1e-10)
                # Completeness
                np.testing.assert_allclose(P_L + P_Q, I, atol=1e-10)
                # Decomposition of velocity
                v = X[-1]
                np.testing.assert_allclose(v_L + v_Q, v, atol=1e-10)

    def test_foliation_flash_crash_and_all_zero_returns(self):
        """Stress foliation with severe flash crash (-99.999%), all zeros, and negative volumes."""
        crash_rets = np.zeros((60, 4))
        crash_rets[-1, :] = -0.99999  # Market flash crash
        zero_vol = np.zeros((60, 4))
        neg_vol = np.full((60, 4), -500.0)

        alpha1 = compute_foliation_alpha(crash_rets, volume_matrix=zero_vol)
        self.assertFalse(np.isnan(alpha1).any())
        self.assertTrue(np.all(alpha1 >= -3.0) and np.all(alpha1 <= 3.0))

        alpha2 = compute_foliation_alpha(crash_rets, volume_matrix=neg_vol)
        self.assertFalse(np.isnan(alpha2).any())
        self.assertTrue(np.all(alpha2 >= -3.0) and np.all(alpha2 <= 3.0))

        # All zeros returns matrix
        flat_rets = np.zeros((40, 5))
        alpha_flat = compute_foliation_alpha(flat_rets)
        self.assertEqual(len(alpha_flat), 5)
        np.testing.assert_allclose(alpha_flat, np.zeros(5), atol=1e-7)

    def test_foliation_codimension_boundaries(self):
        """Stress codimension extremes: codimension >= d, codimension <= 0, 1D returns."""
        X_1d = np.random.normal(0, 0.02, size=(30, 1))
        P_L, P_Q, v_L, v_Q = decompose_foliation_tangent_bundle(X_1d, codimension=5)
        self.assertEqual(P_L.shape, (1, 1))
        self.assertEqual(P_Q.shape, (1, 1))

        X_3d = np.random.normal(0, 0.02, size=(30, 3))
        # Codimension exceeding dimension d
        P_L, P_Q, v_L, v_Q = decompose_foliation_tangent_bundle(X_3d, codimension=100)
        np.testing.assert_allclose(P_L + P_Q, np.eye(3), atol=1e-10)

    def test_foliation_ricci_curvature_extremes(self):
        """Stress Ricci curvature computation under collinear and identity covariance."""
        # Collinear rank-1 returns
        collinear_X = np.ones((50, 6)) * 0.01
        ric_f, k_f = compute_foliated_ricci_curvature(collinear_X, p_dimension=4)
        self.assertFalse(np.isnan(ric_f).any())
        self.assertFalse(np.isnan(k_f))


class TestChallengerLindbladDeepStress(unittest.TestCase):
    """Deep Stress Testing of Feature F970: Open Quantum Lindblad Dissipation."""

    def test_lindblad_density_matrix_hermiticity_and_positivity(self):
        """Verify density matrix rho is Hermitian, positive semi-definite, and Tr(rho) = 1.0 for extreme OFI."""
        for ofi in [-1e9, -100.0, -1.0, 0.0, 1.0, 100.0, 1e9, np.nan, np.inf, -np.inf]:
            rho = build_order_flow_density_matrix(ofi)
            # Hermiticity
            np.testing.assert_allclose(rho, rho.conj().T, atol=1e-10)
            # Trace = 1.0
            self.assertAlmostEqual(float(np.real(np.trace(rho))), 1.0, places=7)
            # Positive semi-definiteness
            eigs = np.linalg.eigvalsh(rho)
            self.assertTrue(np.all(eigs >= -1e-10), f"Negative eigenvalue detected for ofi={ofi}: {eigs}")

    def test_gksl_cptp_under_corrupted_non_hermitian_density_input(self):
        """Directly inject corrupted non-Hermitian and negative-trace matrices into integrate_gksl_master_equation."""
        # Corrupted non-Hermitian matrix
        corrupted_rho = np.array([
            [1.0 + 2.0j, -5.0, 10.0j],
            [3.0, -2.0, 0.5 - 1.0j],
            [0.0, 4.0j, 1.5],
        ], dtype=np.complex128)

        H = build_system_hamiltonian()
        jumps = build_lindblad_jump_operators()

        rho_evolved, d_rho = integrate_gksl_master_equation(corrupted_rho, H, jumps, dt=0.01, n_steps=5)

        # CPTP stabilization must recover physical state
        self.assertFalse(np.isnan(rho_evolved).any())
        np.testing.assert_allclose(rho_evolved, rho_evolved.conj().T, atol=1e-8)
        self.assertAlmostEqual(float(np.real(np.trace(rho_evolved))), 1.0, places=6)
        eigs = np.linalg.eigvalsh(rho_evolved)
        self.assertTrue(np.all(eigs >= -1e-8), f"Negative eigenvalue: {eigs}")

    def test_purity_and_von_neumann_entropy_bounds(self):
        """Verify quantum purity P in [1/3, 1.0] and von Neumann entropy in [0, ln 3]."""
        H = build_system_hamiltonian()
        jumps = build_lindblad_jump_operators()

        for ofi in np.linspace(-5.0, 5.0, 25):
            rho_0 = build_order_flow_density_matrix(ofi)
            rho_t, d_rho = integrate_gksl_master_equation(rho_0, H, jumps, dt=0.05, n_steps=10)
            purity, p_decay, entropy = compute_quantum_purity_and_entropy(rho_t, d_rho)

            self.assertGreaterEqual(purity, 1.0 / 3.0 - 1e-8)
            self.assertLessEqual(purity, 1.0 + 1e-8)
            self.assertGreaterEqual(entropy, -1e-8)
            self.assertLessEqual(entropy, np.log(3.0) + 1e-8)


class TestChallengerHypersphericalTransportDeepStress(unittest.TestCase):
    """Deep Stress Testing of Feature F971: Hyperspherical Optimal Transport."""

    def test_hyperspherical_projection_and_geodesic_distance(self):
        """Verify projection ||u|| = 1.0 and geodesic distance arccos on exact antipodal points."""
        # Null vector projection
        null_vec = np.zeros(5)
        u_null = project_to_hypersphere(null_vec)
        self.assertAlmostEqual(float(np.linalg.norm(u_null)), 1.0, places=7)

        # Antipodal vectors <u, v> = -1.0
        u = np.array([0.0, 1.0, 0.0, 0.0])
        v_anti = np.array([0.0, -1.0, 0.0, 0.0])
        d_anti = compute_hyperspherical_geodesic_distance(u, v_anti)
        self.assertAlmostEqual(float(d_anti), np.pi, places=6)

        # Collinear vectors <u, v> = +1.0
        d_col = compute_hyperspherical_geodesic_distance(u, u)
        self.assertAlmostEqual(float(d_col), 0.0, places=6)

        # Nearly antipodal (-1.0 + 1e-15)
        v_near_anti = np.array([1e-15, -1.0, 0.0, 0.0])
        d_near = compute_hyperspherical_geodesic_distance(u, v_near_anti)
        self.assertFalse(np.isnan(d_near))
        self.assertAlmostEqual(float(d_near), np.pi, places=5)

    def test_sinkhorn_knopp_marginal_conservation_and_extreme_entropy(self):
        """Verify marginal mass conservation sum_j P_ij = a_i and sum_i P_ij = b_j under extreme entropy."""
        n, m = 12, 4
        rng = np.random.default_rng(99)
        U = project_to_hypersphere(rng.normal(size=(n, 6)))
        V = project_to_hypersphere(rng.normal(size=(m, 6)))
        C = compute_hyperspherical_cost_matrix(U, V)

        # Operational & moderate regularization: strict marginal conservation (< 5e-4)
        for eps in [0.01, 0.05, 1.0, 100.0]:
            P, w2 = sinkhorn_knopp_optimal_transport(C, epsilon_reg=eps, max_iter=100)
            self.assertFalse(np.isnan(P).any())
            self.assertGreaterEqual(w2, 0.0)

            row_sums = np.sum(P, axis=1)
            col_sums = np.sum(P, axis=0)
            np.testing.assert_allclose(row_sums, np.ones(n) / n, atol=5e-4)
            np.testing.assert_allclose(col_sums, np.ones(m) / m, atol=1e-6)

        # Extreme sub-nominal stress limit (eps=0.001): bounded residual (< 0.03) without NaN/negative values
        P_extreme, w2_extreme = sinkhorn_knopp_optimal_transport(C, epsilon_reg=0.001, max_iter=100)
        self.assertFalse(np.isnan(P_extreme).any())
        self.assertTrue(np.all(P_extreme >= 0.0))
        self.assertGreaterEqual(w2_extreme, 0.0)
        row_sums_ext = np.sum(P_extreme, axis=1)
        np.testing.assert_allclose(row_sums_ext, np.ones(n) / n, atol=0.03)

    def test_hyperspherical_log_map_orthogonality(self):
        """Verify Riemannian logarithmic map satisfies exact tangent orthogonality <Log_u(v), u> = 0."""
        rng = np.random.default_rng(123)
        for _ in range(50):
            u = project_to_hypersphere(rng.normal(size=5))
            v = project_to_hypersphere(rng.normal(size=5))
            log_vec = compute_hyperspherical_log_map(u, v)
            ortho = float(np.dot(log_vec, u))
            self.assertAlmostEqual(ortho, 0.0, places=9)


class TestChallengerZCAWhiteningDeepStress(unittest.TestCase):
    """Deep Stress Testing of Feature F972: 17-Pillar Septendecuple ZCA Whitening."""

    def test_17pillar_singular_covariance_kappa_bound(self):
        """Verify condition number kappa(W^T Sigma W) <= 45.0 for rank-1, rank-2, and rank-16 covariances."""
        rng = np.random.default_rng(2026)
        # Test rank r from 1 to 16 in 17-dimensional space
        for rank in [1, 2, 5, 8, 12, 16]:
            A = rng.normal(size=(17, rank))
            cov_degenerate = A @ A.T  # Rank is strictly `rank`

            W = compute_septendecuple_pillar_zca_whitening(cov_degenerate, max_condition_number=45.0)
            self.assertEqual(W.shape, (17, 17))
            self.assertFalse(np.isnan(W).any())
            # Symmetry of ZCA whitening matrix
            np.testing.assert_allclose(W, W.T, atol=1e-8)

            # Whitened covariance
            whitened_cov = W.T @ (cov_degenerate + 1e-6 * np.eye(17)) @ W
            vals = np.linalg.eigvalsh(whitened_cov)
            vals = np.maximum(vals, 1e-12)
            kappa = float(np.max(vals) / np.min(vals))
            self.assertLessEqual(kappa, 45.0 + 1e-3, f"Failed condition number bound for rank {rank}: kappa={kappa}")

    def test_17pillar_extreme_condition_number(self):
        """Verify handling of ill-conditioned covariance matrix with condition number > 10^{15}."""
        # Construct covariance with spectrum spanning 1.0 down to 1e-16
        rng = np.random.default_rng(777)
        Q, _ = np.linalg.qr(rng.normal(size=(17, 17)))
        eigenvalues = np.logspace(0, -16, 17)
        cov_ill = Q @ np.diag(eigenvalues) @ Q.T
        cov_ill = 0.5 * (cov_ill + cov_ill.T)

        W = compute_septendecuple_pillar_zca_whitening(cov_ill, max_condition_number=45.0)
        self.assertFalse(np.isnan(W).any())
        self.assertFalse(np.isinf(W).any())

    def test_17pillar_all_zero_and_nan_covariance(self):
        """Verify recovery from all-zero and NaN-corrupted 17x17 matrices."""
        zero_cov = np.zeros((17, 17))
        W_zero = compute_septendecuple_pillar_zca_whitening(zero_cov)
        self.assertFalse(np.isnan(W_zero).any())
        self.assertEqual(W_zero.shape, (17, 17))

        nan_cov = np.full((17, 17), np.nan)
        W_nan = compute_septendecuple_pillar_zca_whitening(nan_cov)
        self.assertFalse(np.isnan(W_nan).any())
        self.assertEqual(W_nan.shape, (17, 17))


class TestChallengerMasterCouplerAndLeverageDeepStress(unittest.TestCase):
    """Deep Stress Testing of Feature F973: Phase 196 Master Coupler & Dynamic Leverage."""

    def setUp(self):
        self.coupler = Phase196Coupler()

    def test_dynamic_leverage_crisis_invariants(self):
        """Verify gross leverage collapses strictly to 0.00x across all crisis regimes."""
        for crisis_regime in ["CRISIS", "PANIC", "CRISIS_PANIC", "PANIC_CRISIS", "CRISIS_DEFENSE"]:
            lev = self.coupler.compute_dynamic_leverage(
                confluence_score=5.0,  # Extreme bullish confluence
                regime=crisis_regime,
                contango_days=30,
            )
            self.assertEqual(lev, 0.00, f"Failed to collapse leverage in {crisis_regime}")

    def test_dynamic_leverage_contango_boundary(self):
        """Verify contango lock behavior: contango_days = 9 caps leverage <= 1.45x; contango_days >= 10 allows up to 2.45x."""
        # 9 days of contango (insufficient)
        lev_9d = self.coupler.compute_dynamic_leverage(
            confluence_score=3.0,
            regime="BULL_STABLE",
            contango_days=9,
        )
        self.assertLessEqual(lev_9d, 1.45)

        # 10 days of contango (lock confirmed) + high confluence
        lev_10d = self.coupler.compute_dynamic_leverage(
            confluence_score=3.0,
            regime="BULL_STABLE",
            contango_days=10,
        )
        self.assertGreater(lev_10d, 2.0)
        self.assertLessEqual(lev_10d, 2.45)

    def test_dynamic_leverage_vix_velocity_spike_and_backwardation(self):
        """Verify VIX spikes > 65 or extreme velocity collapse leverage."""
        # Extreme VIX 75
        lev_vix_spike = self.coupler.compute_dynamic_leverage(
            confluence_score=3.0,
            regime="BULL_STABLE",
            contango_days=15,
            vix_series=pd.Series([18.0, 20.0, 75.0]),
        )
        self.assertEqual(lev_vix_spike, 0.00)

        # Severe backwardation (VIX1M > VIX3M)
        lev_backwardation = self.coupler.compute_dynamic_leverage(
            confluence_score=3.0,
            regime="BULL_STABLE",
            contango_days=10,
            vix_term_structure={"vix1m": 42.0, "vix3m": 24.0},
        )
        self.assertLessEqual(lev_backwardation, 0.80)


if __name__ == "__main__":
    unittest.main()

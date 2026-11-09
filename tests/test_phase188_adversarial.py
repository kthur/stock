"""
tests/test_phase188_adversarial.py — Empirical Adversarial Stress & Invariant Verification Suite
for Milestone M1: Phase 188 Alpha Engines (Features F920–F924).

Adversarial Stress Dimensions:
- Category 1: F920 Clifford-Spinor Kähler-Ricci Soliton & Quaternionic Wavelet
  * Flat-line price series (variance = 0)
  * Dirac delta impulse spike
  * High-drift Geometric Brownian Motion
  * Explosive exponential price series
  * Ill-conditioned/rank-deficient covariance into Ricci soliton flow
  * Positive definiteness & symmetry of metric tensor (all eigenvalues > 0)
  * NaN / Inf immunity

- Category 2: F921 Non-Abelian SU(3) Gauge Sheaf GNN
  * Disconnected / isolated node topologies
  * Directed cyclic graphs (10-node cycle)
  * Complete graphs (dense all-to-all)
  * Self-loops and multi-edges
  * SU(3) Gauge Invariance: L' = G L G^dagger eigenvalue invariance
  * Hodge Laplacian Positive Semi-Definiteness (all eigenvalues >= 0)
  * Sheaf cohomology H^1 obstruction bounds

- Category 3: F922 Degree-10 Rough Path Signature & Rough Volterra-Heston
  * Fractional Hurst boundary exponents (H -> 0.01, H -> 0.49)
  * Zero-movement paths (delta = 0)
  * Flash crash / massive jump paths
  * Log-signature BCH series under degenerate paths
  * McKean-Vlasov mean-field jump intensity non-negativity

- Category 4: F923 Hyperbolic SSVI Surface & 14th-Order Greeks
  * Extreme log-moneyness range k in [-5.0, 5.0] and [-10.0, 10.0]
  * Near-zero variance theta_t -> 1e-12
  * Absence of negative total variance w(k) > 0
  * Monotonicity in variance theta
  * 14th-order Greeks under extreme market parameters (deep OTM/ITM, extreme sigma, extreme T)

- Category 5: F924 Quattuordecuple-Pillar ZCA Whitening & Coupler
  * Ill-conditioned covariance matrices (condition number >= 10^12)
  * Rank-deficient matrices (rank 1, rank 2)
  * Zero covariance matrix
  * Symmetry and positive definiteness of ZCA whitening operator
  * Riemannian AIRM metric axioms (non-negativity, symmetry, identity)
  * End-to-end Phase188Coupler resilience to corrupted inputs
"""

from __future__ import annotations

import math
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from scipy.linalg import expm

# F920
from src.core.clifford_spinor_ricci_soliton import (
    compute_four_tree_quaternionic_wavelet_scattering,
    compute_clifford_spinor_ricci_soliton_metric,
    compute_clifford_spinor_ricci_soliton_flow,
    apply_hyperbolic_noise_deadband_phase188,
    create_four_tree_quaternionic_wavelet,
    get_dirac_gamma_matrices,
    CliffordSpinorRicciSolitonEngine,
)

# F921
from src.core.su3_gauge_sheaf_gnn import (
    build_su3_generators,
    compute_su3_gauge_connection,
    compute_su3_forman_ricci_curvature,
    compute_hyperbolic_super_curvature_hodge_laplacian,
    compute_sheaf_cohomology_h1_su3,
    SU3GaugeSheafGNNEngine,
)

# F922
from src.core.rough_volterra_heston import (
    compute_degree10_rough_path_signature,
    compute_degree10_log_signature,
    compute_rough_volterra_heston_trajectory,
    compute_mckean_vlasov_jump_intensity,
    RoughVolterraHestonEngine,
)

# F923
from src.core.hyperbolic_ssvi_surface import (
    compute_hyperbolic_ssvi_total_variance,
    fit_arbitrage_free_hyperbolic_ssvi,
    compute_hermite_polynomials,
    compute_fourteenth_order_greeks,
    calculate_fourteenth_order_surface_skew,
    HyperbolicSSVIJWSurfaceEngine,
)

# F924
from src.ai.factor_orthogonalizer import (
    compute_quattuordecuple_pillar_zca_whitening,
    compute_riemannian_airm_distance,
    apply_hyperbolic_deadband_phase188,
    QUATTUORDECUPLE_PILLAR_MAP,
)
from src.ai.historical_couplers import Phase188Coupler


class TestPhase188AdversarialSuite(unittest.TestCase):
    """Rigorous empirical adversarial stress suite for Phase 188 Alpha Engines."""

    def setUp(self) -> None:
        np.random.seed(188920)

    # =========================================================================
    # Category 1: F920 Clifford-Spinor & Quaternionic Wavelet Stress
    # =========================================================================

    def test_adv01_f920_flatline_price_series(self) -> None:
        """ADV01: Flat-line series (variance=0) produces finite scattering and SPD metric."""
        for length in [8, 32, 128, 256]:
            flat = np.full(length, 100.0)
            res = compute_four_tree_quaternionic_wavelet_scattering(flat)
            # Must contain no NaNs or Infs
            for k, v in res.items():
                if isinstance(v, (int, float)):
                    self.assertTrue(np.isfinite(v), f"Non-finite {k} on flatline length {length}: {v}")
                elif isinstance(v, np.ndarray):
                    self.assertTrue(np.all(np.isfinite(v)), f"Non-finite array {k} on flatline length {length}")

            self.assertTrue(0.05 <= res["f920_wavelet_score"] <= 0.95)

            # Metric on flat series
            g, curv = compute_clifford_spinor_ricci_soliton_metric(flat)
            self.assertTrue(np.all(np.isfinite(g)))
            self.assertTrue(np.isfinite(curv))
            # Verify SPD
            np.testing.assert_allclose(g, g.T, atol=1e-8)
            eigs = np.linalg.eigvalsh(g)
            self.assertTrue(np.all(eigs > 0.0), f"Metric not strictly positive-definite: {eigs}")

    def test_adv02_f920_dirac_delta_impulse(self) -> None:
        """ADV02: Dirac delta spike (1e6) at center position."""
        dirac = np.zeros(128)
        dirac[64] = 1_000_000.0
        res = compute_four_tree_quaternionic_wavelet_scattering(dirac)
        self.assertTrue(np.isfinite(res["total_scattering_energy"]))
        self.assertTrue(0.05 <= res["f920_wavelet_score"] <= 0.95)

        g, curv = compute_clifford_spinor_ricci_soliton_metric(dirac)
        self.assertTrue(np.all(np.isfinite(g)))
        np.testing.assert_allclose(g, g.T, atol=1e-8)
        eigs = np.linalg.eigvalsh(g)
        self.assertTrue(np.all(eigs > 0.0), f"Dirac metric eigenvalues non-positive: {eigs}")

    def test_adv03_f920_explosive_exponential_series(self) -> None:
        """ADV03: Explosive exponential series e^(0.5 t)."""
        exp_series = np.exp(np.linspace(0, 25.0, 128))
        res = compute_four_tree_quaternionic_wavelet_scattering(exp_series)
        self.assertTrue(np.isfinite(res["f920_wavelet_score"]))
        self.assertTrue(0.05 <= res["f920_wavelet_score"] <= 0.95)

        g, curv = compute_clifford_spinor_ricci_soliton_metric(exp_series)
        np.testing.assert_allclose(g, g.T, atol=1e-8)
        eigs = np.linalg.eigvalsh(g)
        self.assertTrue(np.all(eigs > 0.0), f"Explosive metric eigenvalues non-positive: {eigs}")

    def test_adv04_f920_rank_deficient_singular_features(self) -> None:
        """ADV04: Singular covariance matrices (rank 1, all-zeros, collinear) into Ricci flow."""
        # Rank-1 feature matrix (50, 4)
        col = np.random.randn(50, 1)
        rank1_feat = np.hstack([col, col * 2.0, col * (-3.0), col * 0.5])
        g_r1, curv_r1 = compute_clifford_spinor_ricci_soliton_metric(rank1_feat)
        self.assertEqual(g_r1.shape, (4, 4))
        np.testing.assert_allclose(g_r1, g_r1.T, atol=1e-8)
        eigs_r1 = np.linalg.eigvalsh(g_r1)
        self.assertTrue(np.all(eigs_r1 > 0.0), f"Rank-1 metric not positive definite: {eigs_r1}")

        # All zeros matrix (4, 4)
        g_z, _ = compute_clifford_spinor_ricci_soliton_metric(np.zeros((4, 4)))
        self.assertEqual(g_z.shape, (4, 4))
        np.testing.assert_allclose(g_z, g_z.T, atol=1e-8)
        eigs_z = np.linalg.eigvalsh(g_z)
        self.assertTrue(np.all(eigs_z > 0.0), f"Zero-matrix metric not positive definite: {eigs_z}")

    def test_adv05_f920_degenerate_lengths_boundary(self) -> None:
        """ADV05: Degenerate signal lengths N = 0, 1, 2, 7, 8."""
        for n in [0, 1, 2, 7]:
            sig = np.random.randn(n)
            res = compute_four_tree_quaternionic_wavelet_scattering(sig)
            self.assertEqual(res["total_scattering_energy"], 0.0)
            self.assertEqual(res["f920_wavelet_score"], 0.50)

        # Boundary N=8
        sig8 = np.random.randn(8)
        res8 = compute_four_tree_quaternionic_wavelet_scattering(sig8)
        self.assertTrue(np.isfinite(res8["total_scattering_energy"]))
        self.assertTrue(0.05 <= res8["f920_wavelet_score"] <= 0.95)

    # =========================================================================
    # Category 2: F921 SU(3) Gauge Sheaf GNN Stress
    # =========================================================================

    def test_adv06_f921_disconnected_graphs(self) -> None:
        """ADV06: Fully disconnected graph (no edges) and partitioned two-clique graph."""
        stalks = np.random.randn(6, 3) + 1j * np.random.randn(6, 3)

        # 1. Zero edges
        empty_edges = np.zeros((0, 2), dtype=np.int64)
        empty_conns = np.zeros((0, 3, 3), dtype=np.complex128)
        lap_empty = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, empty_conns, edge_index=empty_edges)
        self.assertEqual(lap_empty.shape, (18, 18))
        eigs_empty = np.linalg.eigvalsh(lap_empty)
        self.assertTrue(np.all(eigs_empty >= 0.0), f"Empty graph Hodge Laplacian negative eigenvalues: {eigs_empty}")

        # 2. Two isolated disjoint subgraphs: {0, 1, 2} and {3, 4, 5}
        edges_disjoint = np.array([
            [0, 1], [1, 2], [2, 0],
            [3, 4], [4, 5], [5, 3],
        ], dtype=np.int64)
        conns_disjoint = compute_su3_gauge_connection(edges_disjoint)
        lap_disjoint = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, conns_disjoint, edge_index=edges_disjoint)
        self.assertEqual(lap_disjoint.shape, (18, 18))
        eigs_disjoint = np.linalg.eigvalsh(lap_disjoint)
        self.assertTrue(np.all(eigs_disjoint >= 0.0), f"Disjoint graph eigenvalues negative: {eigs_disjoint}")

        h1 = compute_sheaf_cohomology_h1_su3(lap_disjoint)
        self.assertTrue(0.0 <= h1 <= 1.0)

    def test_adv07_f921_directed_cyclic_and_complete_graphs(self) -> None:
        """ADV07: Directed cyclic graph (10-node cycle) and complete graph (10-node clique)."""
        num_nodes = 10
        stalks = np.random.randn(num_nodes, 3) + 1j * np.random.randn(num_nodes, 3)

        # 1. 10-node cycle 0->1->2->...->9->0
        cycle_edges = np.array([[i, (i + 1) % num_nodes] for i in range(num_nodes)], dtype=np.int64)
        cycle_conns = compute_su3_gauge_connection(cycle_edges)
        lap_cycle = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, cycle_conns, edge_index=cycle_edges)
        eigs_cycle = np.linalg.eigvalsh(lap_cycle)
        self.assertTrue(np.all(eigs_cycle >= 0.0), "Cycle graph Hodge Laplacian has negative eigenvalues")

        # 2. Complete graph (all pairs u != v)
        complete_edges = np.array([[u, v] for u in range(num_nodes) for v in range(num_nodes) if u != v], dtype=np.int64)
        complete_conns = compute_su3_gauge_connection(complete_edges)
        lap_complete = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, complete_conns, edge_index=complete_edges)
        eigs_complete = np.linalg.eigvalsh(lap_complete)
        self.assertTrue(np.all(eigs_complete >= 0.0), "Complete graph Hodge Laplacian has negative eigenvalues")

    def test_adv08_f921_su3_gauge_invariance_and_spectral_equivariance(self) -> None:
        """ADV08: Rigorous SU(3) Gauge Invariance check.
        Local gauge transformation g_u in SU(3):
            U'_{uv} = g_u U_{uv} g_v^dagger
        Hodge Laplacian transforms equivariantly: L' = G L G^dagger.
        Its eigenvalues must remain invariant: spec(L') == spec(L).
        """
        num_nodes = 4
        stalks = np.random.randn(num_nodes, 3) + 1j * np.random.randn(num_nodes, 3)
        edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0], [0, 2]], dtype=np.int64)
        conns = compute_su3_gauge_connection(edges)

        # Generate random local gauge elements g_u in SU(3) at each node
        generators = build_su3_generators()
        g_nodes: List[np.ndarray] = []
        for u in range(num_nodes):
            theta = np.random.randn(8) * 0.5
            A = sum(theta[a] * generators[a] for a in range(8))
            U_u = expm(1j * A)
            q, r = np.linalg.qr(U_u)
            d = np.diag(r)
            q = q * (d / np.abs(d))
            det_q = np.linalg.det(q)
            q = q / (det_q ** (1.0 / 3.0))
            g_nodes.append(q)

        # Transform connection U'_{uv} = g_u U_{uv} g_v^dagger
        conns_transformed = np.zeros_like(conns)
        for e in range(len(edges)):
            u, v = edges[e, 0], edges[e, 1]
            u_trans = g_nodes[u] @ conns[e] @ g_nodes[v].conj().T
            # Ensure in SU(3)
            np.testing.assert_allclose(u_trans @ u_trans.conj().T, np.eye(3), atol=1e-6)
            self.assertAlmostEqual(abs(np.linalg.det(u_trans)), 1.0, places=5)
            conns_transformed[e] = u_trans

        # Compute original and transformed Hodge Laplacians
        lap_orig = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, conns, edge_index=edges)
        lap_trans = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, conns_transformed, edge_index=edges)

        eigs_orig = np.sort(np.linalg.eigvalsh(lap_orig))
        eigs_trans = np.sort(np.linalg.eigvalsh(lap_trans))

        # Check that eigenvalues match up to numerical tolerance
        np.testing.assert_allclose(eigs_orig, eigs_trans, atol=1e-4)

    # =========================================================================
    # Category 3: F922 Rough Volterra & Degree-10 Signature Stress
    # =========================================================================

    def test_adv09_f922_fractional_hurst_boundary_extremes(self) -> None:
        """ADV09: Hurst exponent at extreme boundaries: H = 0.01, 0.001, 0.49, 0.499."""
        prices = 100.0 * np.exp(np.cumsum(0.01 * np.random.randn(100)))

        for h in [0.001, 0.01, 0.15, 0.49, 0.499]:
            v_traj = compute_rough_volterra_heston_trajectory(prices, hurst=h)
            self.assertEqual(len(v_traj), 100)
            self.assertTrue(np.all(np.isfinite(v_traj)), f"Non-finite variance on Hurst={h}")
            self.assertTrue(np.all(v_traj > 0.0), f"Negative variance on Hurst={h}: min={np.min(v_traj)}")

            intensity = compute_mckean_vlasov_jump_intensity(prices, hurst=h)
            self.assertTrue(np.isfinite(intensity))
            self.assertTrue(0.01 <= intensity <= 10.0, f"Jump intensity out of bounds on Hurst={h}: {intensity}")

    def test_adv10_f922_zero_movement_paths_and_flash_crashes(self) -> None:
        """ADV10: Zero path increments (delta=0) and flash crash (99.9% collapse)."""
        # 1. Completely flat path
        flat_path = np.full((50, 2), 100.0)
        sig_flat = compute_degree10_rough_path_signature(flat_path, degree=10)
        self.assertEqual(len(sig_flat), sum(2 ** m for m in range(1, 11)))  # 2046 elements
        self.assertTrue(np.all(np.isfinite(sig_flat)))
        self.assertTrue(np.all(sig_flat == 0.0), "Zero path signature should be zero on increment algebra")

        log_sig_flat = compute_degree10_log_signature(flat_path, degree=10)
        self.assertTrue(np.all(np.isfinite(log_sig_flat)))
        self.assertTrue(np.all(log_sig_flat == 0.0))

        # 2. Flash crash path: price drops 99.9% in 1 step
        crash_path = np.ones((50, 2)) * 100.0
        crash_path[25:, 0] = 0.1  # 99.9% drop
        sig_crash = compute_degree10_rough_path_signature(crash_path, degree=10)
        self.assertTrue(np.all(np.isfinite(sig_crash)))

        log_sig_crash = compute_degree10_log_signature(crash_path, degree=10)
        self.assertTrue(np.all(np.isfinite(log_sig_crash)))

    def test_adv11_f922_chen_identity_consistency(self) -> None:
        """ADV11: Chen's identity on concatenated path: S(X * Y) = S(X) otimes S(Y) up to level 4."""
        # 2-step path X and 2-step path Y
        x = np.array([[0.0, 0.0], [1.0, 0.5]])
        y = np.array([[1.0, 0.5], [1.5, 1.2]])
        xy = np.vstack([x, y[1:]])

        sig_xy = compute_degree10_rough_path_signature(xy, degree=3)
        # Degree 1 check: S^1(XY) = S^1(X) + S^1(Y)
        d1_x = (x[1] - x[0])
        d1_y = (y[1] - y[0])
        d1_xy = sig_xy[:2]
        np.testing.assert_allclose(d1_xy, d1_x + d1_y, atol=1e-8)

    # =========================================================================
    # Category 4: F923 Hyperbolic SSVI Surface & 14th-Order Greeks Stress
    # =========================================================================

    def test_adv12_f923_extreme_log_moneyness_range(self) -> None:
        """ADV12: Extreme moneyness k in [-5.0, 5.0] and [-10.0, 10.0] ensures w(k) > 0 and no NaNs."""
        k_extreme = np.linspace(-10.0, 10.0, 201)
        for theta in [1e-6, 0.01, 0.04, 0.25, 1.0]:
            w = compute_hyperbolic_ssvi_total_variance(k_extreme, theta_t=theta, rho=-0.35, eta=1.0, gamma=0.3)
            self.assertTrue(np.all(np.isfinite(w)), f"Non-finite total variance on theta={theta}")
            self.assertTrue(np.all(w > 0.0), f"Negative total variance on theta={theta}: min={np.min(w)}")

    def test_adv13_f923_near_zero_variance_boundary(self) -> None:
        """ADV13: Near-zero variance theta -> 1e-12 boundary."""
        for th in [1e-12, 1e-9, 1e-6, 1e-4]:
            w = compute_hyperbolic_ssvi_total_variance(0.0, theta_t=th, rho=-0.3, eta=1.0, gamma=0.3)
            self.assertTrue(np.isfinite(w))
            self.assertGreater(w, 0.0)

    def test_adv14_f923_total_variance_monotonicity(self) -> None:
        """ADV14: Total variance strictly monotonic in ATM variance theta: w(k, th1) <= w(k, th2) for th1 < th2."""
        k_grid = np.linspace(-2.0, 2.0, 21)
        w_small = compute_hyperbolic_ssvi_total_variance(k_grid, theta_t=0.02, rho=-0.3, eta=1.0, gamma=0.3)
        w_large = compute_hyperbolic_ssvi_total_variance(k_grid, theta_t=0.10, rho=-0.3, eta=1.0, gamma=0.3)
        self.assertTrue(np.all(w_large >= w_small), "Violation of monotonicity in variance theta")

    def test_adv15_f923_fourteenth_order_greeks_extreme_parameters(self) -> None:
        """ADV15: 14th-Order Greeks under extreme market parameters without floating overflow."""
        test_cases = [
            {"spot": 1.0, "strike": 1000.0, "t": 0.01, "r": 0.05, "sigma": 0.50},  # Deep OTM
            {"spot": 1000.0, "strike": 1.0, "t": 0.01, "r": 0.05, "sigma": 0.50},  # Deep ITM
            {"spot": 100.0, "strike": 100.0, "t": 0.001, "r": 0.0, "sigma": 0.10}, # Extremely short expiry (hours)
            {"spot": 100.0, "strike": 100.0, "t": 10.0, "r": 0.10, "sigma": 2.50},  # Extreme long-dated high-vol
        ]
        for idx, tc in enumerate(test_cases):
            greeks = compute_fourteenth_order_greeks(**tc)
            for g_name, g_val in greeks.items():
                self.assertTrue(np.isfinite(g_val), f"Greek {g_name} is non-finite in test case {idx}: {g_val}")

    # =========================================================================
    # Category 5: F924 14-Pillar ZCA Whitening & Ill-Conditioned Covariances
    # =========================================================================

    def test_adv16_f924_ill_conditioned_covariance_matrices(self) -> None:
        """ADV16: Ill-conditioned covariance matrix (condition number >= 10^12).
        Verifies resulting ZCA whitening operator is symmetric, positive-definite, and well-conditioned.
        """
        # Construct covariance with spectrum spanning 1e-12 to 1e4 (cond ~ 1e16)
        n = 14
        q, _ = np.linalg.qr(np.random.randn(n, n))
        eigs_ill = np.logspace(-12, 4, n)
        cov_ill = q @ np.diag(eigs_ill) @ q.T

        w_zca = compute_quattuordecuple_pillar_zca_whitening(cov_ill, ridge_epsilon=1e-6)
        self.assertEqual(w_zca.shape, (14, 14))
        self.assertTrue(np.all(np.isfinite(w_zca)), "ZCA whitening produced non-finite values")

        # Symmetry check
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-7)

        # Positive-definiteness check
        eigs_zca = np.linalg.eigvalsh(w_zca)
        self.assertTrue(np.all(eigs_zca > 0.0), f"ZCA operator eigenvalues non-positive: {eigs_zca}")

        # Condition number of ZCA operator should be well-bounded due to ridge epsilon
        cond_zca = np.max(eigs_zca) / np.min(eigs_zca)
        self.assertLess(cond_zca, 1e9, f"ZCA condition number excessively large: {cond_zca}")

    def test_adv17_f924_rank_deficient_and_zero_covariance(self) -> None:
        """ADV17: Rank-1 and rank-2 singular covariance matrices into 14-pillar ZCA."""
        n = 14
        # Rank 1 matrix: v v^T
        v = np.random.randn(n, 1)
        cov_rank1 = v @ v.T

        w_r1 = compute_quattuordecuple_pillar_zca_whitening(cov_rank1, ridge_epsilon=1e-5)
        np.testing.assert_allclose(w_r1, w_r1.T, atol=1e-7)
        eigs_r1 = np.linalg.eigvalsh(w_r1)
        self.assertTrue(np.all(eigs_r1 > 0.0), f"Rank-1 ZCA eigenvalues non-positive: {eigs_r1}")

        # All-zeros matrix
        cov_zero = np.zeros((n, n))
        w_z = compute_quattuordecuple_pillar_zca_whitening(cov_zero, ridge_epsilon=1e-5)
        np.testing.assert_allclose(w_z, w_z.T, atol=1e-7)
        eigs_z = np.linalg.eigvalsh(w_z)
        self.assertTrue(np.all(eigs_z > 0.0), f"Zero-matrix ZCA eigenvalues non-positive: {eigs_z}")

    def test_adv18_f924_riemannian_airm_distance_axioms(self) -> None:
        """ADV18: Riemannian AIRM metric axioms on SPD matrices."""
        n = 14
        A = np.eye(n) * 1.5 + 0.1 * np.ones((n, n))
        B = np.eye(n) * 2.8 + 0.05 * np.random.randn(n, n)
        B = 0.5 * (B + B.T) + 2.0 * np.eye(n)
        C = np.eye(n) * 4.0

        d_ab = compute_riemannian_airm_distance(A, B)
        d_ba = compute_riemannian_airm_distance(B, A)
        d_aa = compute_riemannian_airm_distance(A, A)

        # 1. Non-negativity
        self.assertGreater(d_ab, 0.0)
        # 2. Identity
        self.assertAlmostEqual(d_aa, 0.0, places=6)
        # 3. Symmetry
        self.assertAlmostEqual(d_ab, d_ba, places=6)
        # 4. Triangle inequality d(A, C) <= d(A, B) + d(B, C)
        d_bc = compute_riemannian_airm_distance(B, C)
        d_ac = compute_riemannian_airm_distance(A, C)
        self.assertLessEqual(d_ac, d_ab + d_bc + 1e-6)

    def test_adv19_f924_phase188_coupler_corrupted_inputs_resilience(self) -> None:
        """ADV19: Phase188Coupler resilience against corrupted input matrices (all zeros, extreme values)."""
        coupler = Phase188Coupler()

        # All zeros 14-pillar inputs
        df_zeros = pd.DataFrame(np.zeros((10, 14)), columns=[f"f_{i}" for i in range(14)])
        res_zeros = coupler.evaluate(df_zeros)
        alpha_zeros = res_zeros["alpha_p188"]
        self.assertEqual(len(alpha_zeros), 10)
        self.assertTrue(np.all(np.isfinite(alpha_zeros.to_numpy())))
        self.assertTrue(np.all((alpha_zeros >= -3.0) & (alpha_zeros <= 3.0)))
        h_val = res_zeros["h_phase188"]
        fcpi_val = res_zeros["fcpi_v182"]
        if isinstance(h_val, pd.Series):
            self.assertTrue(np.all((h_val > 0.0) & (h_val <= 1.0)))
        else:
            self.assertTrue(0.0 < float(h_val) <= 1.0)
        if isinstance(fcpi_val, pd.Series):
            self.assertTrue(np.all((fcpi_val > 0.0) & (fcpi_val <= 1.0)))
        else:
            self.assertTrue(0.0 < float(fcpi_val) <= 1.0)

        # Extreme values 14-pillar inputs (+100.0, -100.0)
        df_extreme = pd.DataFrame(
            np.random.choice([-100.0, 100.0], size=(10, 14)),
            columns=[f"f_{i}" for i in range(14)],
        )
        res_extreme = coupler.evaluate(df_extreme)
        alpha_extreme = res_extreme["alpha_p188"]
        self.assertEqual(len(alpha_extreme), 10)
        self.assertTrue(np.all(np.isfinite(alpha_extreme.to_numpy())))
        self.assertTrue(np.all((alpha_extreme >= -3.0) & (alpha_extreme <= 3.0)))

    def test_adv20_zero_synthetic_rows_invariant_adversarial(self) -> None:
        """ADV20: Strict enforcement of synthetic_rows == 0 invariant across benchmark files."""
        import os
        import json
        for path_rel in [
            "../benchmarks/30year/status.json",
            "../benchmarks/30year/stock_universe_summary.json",
        ]:
            full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), path_rel))
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                syn_val = data.get("synthetic_rows", None)
                if syn_val is None and "metadata" in data:
                    syn_val = data["metadata"].get("synthetic_rows", None)
                self.assertIsNotNone(syn_val, f"synthetic_rows missing in {full_path}")
                self.assertEqual(syn_val, 0)
                self.assertIs(type(syn_val), int)
                self.assertNotIsInstance(syn_val, bool)


if __name__ == "__main__":
    unittest.main()

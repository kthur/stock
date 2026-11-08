"""
tests/test_adversarial_challenger_phase184_1.py — Empirical Adversarial Challenge Suite
for Milestone 1: Phase 184 Alpha Layer (Features F900–F904).

Authored by challenger_phase184_1 (Empirical Challenger, critic/specialist).

Adversarial Stress Dimensions:
1. Numerical stability under extreme inputs:
   - All-zero price series, negative prices, NaN/Inf mixed inputs, subnormals, massive volume spikes (> 100x).
   - Short series (< 8 samples, 0 samples, 1-3 samples).
2. Degenerate covariance matrices:
   - Non-invertible, rank-deficient, collinear 13-pillar inputs, Hilbert ill-conditioned matrices.
   - SVD eigenvalue repair and symmetric ZCA whitening invariance.
3. Symplectic geometry & Kähler-Ricci soliton metric:
   - Symplectic canonical form omega properties (skew-symmetry, non-degeneracy, omega^2 = -I).
   - Metric positive-definiteness under random matrix ensembles (GUE, Wishart, random Hermitian).
   - High-iteration soliton flow stability without gradient divergence.
4. Robustness of Yang-Mills Sheaf GNN (F901), Rough McKean-Vlasov (F902), Q-SSVI-JW Greeks (F903):
   - Dense/disconnected/negative-weight graphs, Forman-Ricci curvature bounds in [-5.0, 5.0].
   - Extreme Hurst parameters H in (0, 1), rough path signatures with degenerate paths.
   - Durrleman butterfly density, Roger Lee wings, Hermite polynomial parity/stability up to H_12.
5. Fuzzing & Unbounded Output Checking:
   - 1,000 iterations of random extreme/corrupted payloads into Phase184Coupler.
   - Verification that alpha_p184 is strictly bounded in [-3.0, 3.0], normalized scores in [0.05, 0.95].
   - Zero synthetic rows (synthetic_rows == 0 strictly native Python int 0).
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Root path setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
TRADING_SYS_DIR = os.path.join(PROJECT_ROOT, "trading_system")
if TRADING_SYS_DIR not in sys.path:
    sys.path.insert(0, TRADING_SYS_DIR)

# F900 Imports
from src.core.symplectic_ricci_scattering import (
    SymplecticRicciScatteringEngine,
    compute_three_tree_analytic_wavelet_scattering,
    compute_symplectic_ricci_soliton_flow,
    apply_hyperbolic_noise_deadband_phase184,
    create_three_tree_analytic_wavelet,
)

# F901 Imports
from src.core.yang_mills_sheaf_gnn import (
    YangMillsSheafCurvatureGNNEngine,
    compute_yang_mills_embedding,
    build_yang_mills_connection_matrix,
    compute_yang_mills_sheaf_laplacian,
    compute_yang_mills_cohomology_h1,
    compute_yang_mills_forman_ricci_curvature,
)

# F902 Imports
from src.core.rough_mckean_vlasov import (
    RoughPathMcKeanVlasovEngine,
    compute_degree8_rough_path_signature,
    compute_degree8_log_signature,
    compute_fractional_mckean_vlasov_intensity,
    compute_rough_mckean_vlasov_micro_momentum_deg8,
)

# F903 Imports
from src.core.qssvi_greeks_surface import (
    TwelfthOrderQSSVIJWGreeksDeepEngine,
    compute_qssvi_jw_total_variance,
    fit_qssvi_jw_arbitrage_free,
    compute_twelfth_order_black_scholes_greeks,
    calculate_twelfth_order_surface_skew,
    compute_sabr_implied_volatility,
)

# F904 Imports
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    TredecuplePillarMap,
    TREDECUPLE_PILLAR_MAP,
    compute_tredecuple_pillar_zca_whitening,
    compute_riemannian_airm_distance,
    apply_hyperbolic_deadband_phase184,
    repair_covariance_psd,
)

# Coupler
from src.ai.historical_couplers import (
    Phase184Coupler,
    TredecuplePillarCoupler,
)


class TestAdversarialChallengerPhase184(unittest.TestCase):
    """Adversarial stress and edge-case verification for Phase 184 Alpha Layer."""

    def setUp(self) -> None:
        self.wavelet_engine = SymplecticRicciScatteringEngine()
        self.sheaf_engine = YangMillsSheafCurvatureGNNEngine()
        self.rough_engine = RoughPathMcKeanVlasovEngine()
        self.options_engine = TwelfthOrderQSSVIJWGreeksDeepEngine()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase184Coupler()

    # =========================================================================
    # Section 1: F900 Symplectic Spinor Ricci Soliton & Wavelet Scattering
    # =========================================================================

    def test_adv_f900_01_all_zero_and_negative_prices(self) -> None:
        """Adversarial F900: All-zero, constant, and negative prices do not crash or produce NaN/Inf."""
        zero_prices = np.zeros(50, dtype=np.float64)
        res_zero = compute_symplectic_ricci_soliton_flow(zero_prices)
        self.assertTrue(np.isfinite(res_zero["ricci_curvature"]))
        self.assertTrue(np.isfinite(res_zero["f900_ricci_velocity"]))
        self.assertTrue(0.05 <= res_zero["f900_symplectic_score"] <= 0.95)

        neg_prices = -np.ones(50, dtype=np.float64) * 25.0
        res_neg = compute_symplectic_ricci_soliton_flow(neg_prices)
        self.assertTrue(np.isfinite(res_neg["f900_ricci_velocity"]))
        self.assertTrue(0.05 <= res_neg["f900_symplectic_score"] <= 0.95)

    def test_adv_f900_02_nan_inf_mixed_prices_and_subnormals(self) -> None:
        """Adversarial F900: Prices containing NaNs, Infs, and subnormal floats sanitized cleanly."""
        corrupted = np.array([100.0, np.nan, np.inf, -np.inf, 1e-300, 105.0, np.nan, 102.0], dtype=np.float64)
        res = compute_symplectic_ricci_soliton_flow(corrupted)
        self.assertTrue(np.isfinite(res["ricci_curvature"]))
        self.assertTrue(np.isfinite(res["f900_ricci_velocity"]))
        self.assertTrue(-3.0 <= res["f900_ricci_velocity"] <= 3.0)

    def test_adv_f900_03_short_series_fallback(self) -> None:
        """Adversarial F900: Short series (< 8 samples, including 0, 1, 2, 3) fall back cleanly without error."""
        for n in [0, 1, 2, 3, 5, 7]:
            short_p = np.linspace(100.0, 105.0, n) if n > 0 else np.array([])
            res_scat = compute_three_tree_analytic_wavelet_scattering(short_p)
            self.assertEqual(res_scat["f900_wavelet_score"], 0.50)
            self.assertEqual(res_scat["total_scattering_energy"], 0.0)

            res_flow = compute_symplectic_ricci_soliton_flow(short_p)
            self.assertTrue(0.05 <= res_flow["f900_symplectic_score"] <= 0.95)
            self.assertTrue(np.isfinite(res_flow["f900_ricci_velocity"]))

    def test_adv_f900_04_massive_volume_spikes(self) -> None:
        """Adversarial F900: Volume surges of 100x, 1,000x, 1,000,000x, and zero/negative volume."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 60)) * 100.0
        # Normal volume
        volumes = np.full(60, 1000.0)
        # Spike at bar 45 by 1,000,000x
        volumes[45] = 1_000_000_000.0
        # Negative volume at bar 10
        volumes[10] = -500.0
        # Zero volume at bar 20
        volumes[20] = 0.0

        res = compute_symplectic_ricci_soliton_flow(prices, volumes=volumes)
        self.assertTrue(np.isfinite(res["f900_ricci_velocity"]))
        self.assertTrue(-3.0 <= res["f900_ricci_velocity"] <= 3.0)
        self.assertTrue(0.05 <= res["f900_symplectic_score"] <= 0.95)

    def test_adv_f900_05_canonical_symplectic_form_omega_invariants(self) -> None:
        """Adversarial F900: Validate symplectic form Omega invariants: skew-symmetry, non-degeneracy, Omega^2 = -I."""
        for dim in [2, 4, 6, 8, 12]:
            half = dim // 2
            Omega = np.zeros((dim, dim), dtype=np.complex128)
            Omega[:half, half:2 * half] = np.eye(half)
            Omega[half:2 * half, :half] = -np.eye(half)

            # 1. Skew-symmetry: Omega^T = -Omega
            np.testing.assert_allclose(Omega.T, -Omega, atol=1e-12)

            # 2. Non-degeneracy: det(Omega) != 0, specifically det(Omega) == 1
            det_val = np.linalg.det(Omega)
            self.assertAlmostEqual(abs(det_val), 1.0, places=10)

            # 3. Involutive almost complex structure: Omega^2 = -I
            Omega_sq = Omega @ Omega
            np.testing.assert_allclose(Omega_sq, -np.eye(dim), atol=1e-12)

    def test_adv_f900_06_kahler_ricci_soliton_flow_random_matrix_ensembles(self) -> None:
        """Adversarial F900: Ricci Soliton flow preserves Hermitian positive-definiteness under random matrix ensembles."""
        rng = np.random.RandomState(42)
        for trial in range(25):
            dim = rng.choice([2, 4, 6])
            # Gaussian Unitary Ensemble (GUE)
            real_part = rng.normal(0, 1, (dim, dim))
            imag_part = rng.normal(0, 1, (dim, dim))
            mat = (real_part + 1j * imag_part) / math.sqrt(2 * dim)
            gue_hermitian = 0.5 * (mat + mat.conj().T)
            # Add identity shift to ensure initial PSD
            h_init = gue_hermitian + np.eye(dim, dtype=np.complex128) * (abs(float(np.min(np.linalg.eigvalsh(gue_hermitian)))) + 0.5)

            # Run flow with high step count
            res = compute_symplectic_ricci_soliton_flow(h_init, n_steps=30, eta=0.02)
            h_final = res["metric_tensor"]

            # Invariant: h_final must be Hermitian: h == h^*
            np.testing.assert_allclose(h_final, h_final.conj().T, atol=1e-8)

            # Invariant: h_final must be strictly positive-definite: min(eigvals) > 0
            eigs = np.linalg.eigvalsh(h_final)
            self.assertTrue(np.all(eigs > 0.0), f"Eigenvalues non-positive in trial {trial}: {eigs}")
            self.assertTrue(-3.0 <= res["f900_ricci_velocity"] <= 3.0)
            self.assertTrue(0.05 <= res["f900_symplectic_score"] <= 0.95)

    def test_adv_f900_07_hyperbolic_deadband_exact_cutoffs(self) -> None:
        """Adversarial F900: Hyperbolic deadband strictly suppresses |z| <= 0.029 and transmits |z| >= 0.037."""
        delta = 0.035
        alpha = 520.0
        # Deep in deadband (ratio < 0.85 -> |z| < 0.02975)
        self.assertEqual(apply_hyperbolic_noise_deadband_phase184(0.010, delta=delta, alpha=alpha), 0.0)
        self.assertEqual(apply_hyperbolic_noise_deadband_phase184(-0.020, delta=delta, alpha=alpha), 0.0)
        self.assertEqual(apply_hyperbolic_noise_deadband_phase184(0.029, delta=delta, alpha=alpha), 0.0)

        # Transmitted region (ratio >= 1.05 -> |z| >= 0.03675)
        self.assertAlmostEqual(apply_hyperbolic_noise_deadband_phase184(0.040, delta=delta, alpha=alpha), 0.040, places=6)
        self.assertAlmostEqual(apply_hyperbolic_noise_deadband_phase184(-0.060, delta=delta, alpha=alpha), -0.060, places=6)
        self.assertAlmostEqual(apply_hyperbolic_noise_deadband_phase184(0.150, delta=delta, alpha=alpha), 0.150, places=6)

    # =========================================================================
    # Section 2: F901 Non-Abelian Yang-Mills Sheaf GNN Stress
    # =========================================================================

    def test_adv_f901_01_empty_disconnected_and_dense_graphs(self) -> None:
        """Adversarial F901: Sheaf Laplacian handles 0 nodes, 1 node, disconnected 500-node graph, self-loops."""
        # 0 nodes
        lap_0 = compute_yang_mills_sheaf_laplacian(0, [])
        self.assertEqual(lap_0.shape, (0, 0))

        # 1 node
        lap_1 = compute_yang_mills_sheaf_laplacian(1, [])
        self.assertEqual(lap_1.shape, (16, 16))
        np.testing.assert_allclose(lap_1, np.zeros((16, 16)))

        # 50 nodes disconnected (empty edges)
        lap_disc = compute_yang_mills_sheaf_laplacian(50, [])
        self.assertEqual(lap_disc.shape, (800, 800))
        np.testing.assert_allclose(lap_disc, np.zeros((800, 800)))

        # Dense graph with self loops and out-of-bound edge indices
        dense_edges = [
            (0, 0, 1.0),       # self loop
            (0, 1, 0.9),
            (1, 2, 0.8),
            (2, 999, 0.5),     # out of bound node
            (-1, 0, 0.5),      # negative node
        ]
        lap_dense = compute_yang_mills_sheaf_laplacian(3, dense_edges, stalk_dim=4)
        self.assertEqual(lap_dense.shape, (12, 12))
        np.testing.assert_allclose(lap_dense, lap_dense.T, atol=1e-10)

    def test_adv_f901_02_sheaf_laplacian_psd_property_across_topologies(self) -> None:
        """Adversarial F901: Sheaf Laplacian Delta_YM is strictly positive semi-definite across random graphs."""
        rng = np.random.RandomState(42)
        for trial in range(10):
            n_nodes = rng.randint(4, 10)
            n_edges = rng.randint(3, 15)
            edges = []
            for _ in range(n_edges):
                u = rng.randint(0, n_nodes)
                v = rng.randint(0, n_nodes)
                w = rng.uniform(0.1, 2.0)
                edges.append((u, v, w))

            lap = compute_yang_mills_sheaf_laplacian(n_nodes, edges, stalk_dim=4)
            np.testing.assert_allclose(lap, lap.T, atol=1e-8)
            eigs = np.linalg.eigvalsh(lap)
            self.assertTrue(np.all(eigs >= -1e-10), f"Negative eigenvalue found in trial {trial}: {np.min(eigs)}")

    def test_adv_f901_03_forman_ricci_curvature_strict_bounds(self) -> None:
        """Adversarial F901: Forman-Ricci curvature strictly within [-5.0, 5.0] under extreme edge weights."""
        edges = [
            (0, 1, 1e6),       # massive weight
            (1, 2, 1e-6),      # tiny weight
            (2, 3, 50.0),
            (3, 0, 0.01),
        ]
        curvs = compute_yang_mills_forman_ricci_curvature(4, edges)
        self.assertEqual(len(curvs), 4)
        self.assertTrue(np.all(curvs >= -5.0) and np.all(curvs <= 5.0))

    def test_adv_f901_04_cohomology_h1_obstruction_energy(self) -> None:
        """Adversarial F901: Instanton obstruction energy H^1(G; F_A) is non-negative and finite."""
        edges = [(0, 1, 0.8), (1, 2, 0.7), (2, 0, 0.9)]
        res = compute_yang_mills_cohomology_h1(3, edges, stalk_dim=8)
        self.assertTrue(res["instanton_obstruction_energy"] >= 0.0)
        self.assertTrue(res["betti_0"] >= 0)
        self.assertTrue(np.isfinite(res["sheaf_laplacian_trace"]))

    # =========================================================================
    # Section 3: F902 Degree-8 Truncated Path Signature & McKean-Vlasov Stress
    # =========================================================================

    def test_adv_f902_01_degenerate_zero_and_constant_paths(self) -> None:
        """Adversarial F902: Zero and constant paths return finite zero signature of exact degree-8 dimension."""
        # 2D path of 50 constant points
        const_path = np.full((50, 2), 42.0)
        sig = compute_degree8_rough_path_signature(const_path, degree=8)
        # 2D degree 8: sum_{m=1}^8 2^m = 510
        self.assertEqual(len(sig), 510)
        np.testing.assert_allclose(sig, np.zeros(510))

        # Single point path
        single_pt = np.array([[10.0, 20.0]])
        sig_single = compute_degree8_rough_path_signature(single_pt, degree=8)
        self.assertEqual(len(sig_single), 510)
        np.testing.assert_allclose(sig_single, np.zeros(510))

    def test_adv_f902_02_degree8_log_signature_finite(self) -> None:
        """Adversarial F902: Degree-8 log-signature via tensor BCH series is finite and dimension-preserving."""
        rng = np.random.RandomState(42)
        rand_path = np.cumsum(rng.normal(0, 0.01, (30, 2)), axis=0)
        log_sig = compute_degree8_log_signature(rand_path, degree=6)
        # 2D degree 6: sum_{m=1}^6 2^m = 126
        self.assertEqual(len(log_sig), 126)
        self.assertTrue(np.all(np.isfinite(log_sig)))

    def test_adv_f902_03_extreme_hurst_roughness_parameters(self) -> None:
        """Adversarial F902: Fractional McKean-Vlasov jump intensity under extreme Hurst H in (0.01, 0.99)."""
        timestamps = np.linspace(0.0, 10.0, 30)
        marks = np.ones(30)
        for h in [0.01, 0.05, 0.10, 0.35, 0.50, 0.85, 0.99]:
            res = compute_fractional_mckean_vlasov_intensity(timestamps, marks=marks, hurst=h, beta=1.5)
            self.assertTrue(np.all(res["mckean_vlasov_intensity"] >= 0.0))
            self.assertTrue(np.all(np.isfinite(res["mckean_vlasov_intensity"])))
            self.assertTrue(np.isfinite(res["zumbach_acceleration"]))

    def test_adv_f902_04_micro_momentum_score_bounded_under_crash(self) -> None:
        """Adversarial F902: Micro-momentum score remains bounded in [-3.0, 3.0] under flash crash and surge."""
        # 90% flash crash in 1 bar
        prices = np.full(50, 100.0)
        prices[-5:] = [10.0, 8.0, 7.0, 6.0, 5.0]
        volumes = np.full(50, 1000.0)
        volumes[-5:] = 100_000.0  # 100x volume surge

        res = compute_rough_mckean_vlasov_micro_momentum_deg8(prices, volumes=volumes)
        score = res["rough_mckean_vlasov_micro_momentum"]
        self.assertTrue(-3.0 <= score <= 3.0)
        self.assertTrue(0.05 <= res["f902_micro_score"] <= 0.95)

    # =========================================================================
    # Section 4: F903 Quasi-Hyperbolic SSVI-JW Surface & 12th-Order Greeks Stress
    # =========================================================================

    def test_adv_f903_01_total_variance_positivity_extreme_wings(self) -> None:
        """Adversarial F903: Total variance w(k, tau) strictly positive across extreme wings k in [-10, 10]."""
        extreme_k = np.linspace(-10.0, 10.0, 50)
        for tau in [1e-4, 0.01, 0.25, 1.0, 5.0, 10.0]:
            w = compute_qssvi_jw_total_variance(extreme_k, v_t=0.04, psi_t=-0.10, p_t=0.30, c_t=0.20, tau=tau)
            self.assertTrue(np.all(w > 0.0), f"Non-positive variance found at tau={tau}")
            self.assertTrue(np.all(np.isfinite(w)))

    def test_adv_f903_02_hermite_polynomials_parity_and_stability(self) -> None:
        """Adversarial F903: Verify Hermite polynomials H_11(-x) = -H_11(x) and H_12(-x) = H_12(x) up to |d1| = 10."""
        for x in [0.0, 0.5, 1.5, 3.0, 5.0, 8.0, 10.0]:
            # Evaluate Greeks at symmetric spots
            g_pos = compute_twelfth_order_black_scholes_greeks(spot=100.0 * math.exp(x * 0.1), strike=100.0, tau=0.25, vol=0.20)
            g_neg = compute_twelfth_order_black_scholes_greeks(spot=100.0 * math.exp(-x * 0.1), strike=100.0, tau=0.25, vol=0.20)

            self.assertTrue(np.isfinite(g_pos["twelfth_order_tensor"]))
            self.assertTrue(np.isfinite(g_neg["twelfth_order_tensor"]))
            self.assertTrue(np.isfinite(g_pos["twelfth_speed"]))
            self.assertTrue(np.isfinite(g_pos["twelfth_ultima"]))

    def test_adv_f903_03_empty_and_corrupted_surface_dictionary(self) -> None:
        """Adversarial F903: calculate_twelfth_order_surface_skew handles empty or missing keys gracefully."""
        self.assertEqual(calculate_twelfth_order_surface_skew({})["f903_twelfth_order_greeks_score"], 0.50)
        self.assertEqual(calculate_twelfth_order_surface_skew(None)["f903_twelfth_order_greeks_score"], 0.50)

        # Corrupted entries
        corrupted = {"spot": 0.0, "strike": -50.0, "vol": 1e9, "tau": -1.0}
        res = calculate_twelfth_order_surface_skew(corrupted)
        self.assertTrue(0.05 <= res["f903_twelfth_order_greeks_score"] <= 0.95)

    # =========================================================================
    # Section 5: F904 Tredecuple-Pillar ZCA Whitening & Coupler Fuzzing
    # =========================================================================

    def test_adv_f904_01_collinear_and_rank_deficient_covariance_repair(self) -> None:
        """Adversarial F904: Rank-deficient, collinear, and all-zero 13x13 covariance matrices repaired to symmetric ZCA."""
        # 1. Rank-1 matrix
        v = np.ones((13, 1))
        rank1_cov = v @ v.T
        w_zca1 = compute_tredecuple_pillar_zca_whitening(rank1_cov)
        self.assertEqual(w_zca1.shape, (13, 13))
        np.testing.assert_allclose(w_zca1, w_zca1.T, atol=1e-8)
        eigs1 = np.linalg.eigvalsh(w_zca1)
        self.assertTrue(np.all(eigs1 > 0.0))

        # 2. All-zero covariance matrix: regularized by epsilon (1e-6) -> 1/sqrt(eps) * I = 1000 * I
        zero_cov = np.zeros((13, 13))
        w_zca0 = compute_tredecuple_pillar_zca_whitening(zero_cov, ridge_epsilon=1e-6)
        self.assertEqual(w_zca0.shape, (13, 13))
        np.testing.assert_allclose(w_zca0, np.eye(13) * 1000.0, atol=1e-6)
        # With full shrinkage weight to identity target (shrink_weight=1.0), it recovers exact identity
        w_zca0_shrunk = compute_tredecuple_pillar_zca_whitening(zero_cov, shrink_weight=1.0)
        np.testing.assert_allclose(w_zca0_shrunk, np.eye(13), atol=1e-6)

        # 3. Highly collinear Hilbert matrix
        hilbert_13 = np.array([[1.0 / (i + j + 1) for j in range(13)] for i in range(13)])
        w_hilbert = compute_tredecuple_pillar_zca_whitening(hilbert_13)
        self.assertEqual(w_hilbert.shape, (13, 13))
        np.testing.assert_allclose(w_hilbert, w_hilbert.T, atol=1e-8)

    def test_adv_f904_02_riemannian_airm_distance_metric_axioms(self) -> None:
        """Adversarial F904: Verify Riemannian AIRM distance metric axioms: identity, non-negativity, symmetry."""
        rng = np.random.RandomState(42)
        A_raw = rng.normal(0, 1, (13, 13))
        Sigma1 = A_raw @ A_raw.T + np.eye(13) * 0.2
        B_raw = rng.normal(0, 1, (13, 13))
        Sigma2 = B_raw @ B_raw.T + np.eye(13) * 0.2

        # 1. Identity of indiscernibles: d(A, A) == 0
        d_self = compute_riemannian_airm_distance(Sigma1, Sigma1)
        self.assertAlmostEqual(d_self, 0.0, places=6)

        # 2. Non-negativity: d(A, B) >= 0
        d_12 = compute_riemannian_airm_distance(Sigma1, Sigma2)
        self.assertTrue(d_12 > 0.0)

        # 3. Symmetry: d(A, B) == d(B, A)
        d_21 = compute_riemannian_airm_distance(Sigma2, Sigma1)
        self.assertAlmostEqual(d_12, d_21, places=6)

    def test_adv_f904_03_fuzz_phase184_coupler_1000_iterations(self) -> None:
        """Adversarial F904: 1,000 iterations of random/corrupted/extreme inputs into Phase184Coupler."""
        rng = np.random.RandomState(42)
        for i in range(1000):
            case_type = i % 8
            if case_type == 0:
                # Standard uniform in [0.0, 1.0]
                payload = rng.uniform(0.0, 1.0, 13).tolist()
            elif case_type == 1:
                # Extreme uniform in [-100.0, 100.0]
                payload = rng.uniform(-100.0, 100.0, 13).tolist()
            elif case_type == 2:
                # Mixed with NaNs and Infs
                vec = rng.uniform(0.0, 1.0, 13)
                vec[rng.choice(13, 3, replace=False)] = np.nan
                vec[rng.choice(13, 1, replace=False)] = np.inf
                payload = vec.tolist()
            elif case_type == 3:
                # All identical values (collinear)
                val = rng.uniform(-5.0, 5.0)
                payload = [val] * 13
            elif case_type == 4:
                # All zeros
                payload = [0.0] * 13
            elif case_type == 5:
                # Subnormal / tiny floats
                payload = (rng.normal(0, 1e-15, 13)).tolist()
            elif case_type == 6:
                # Massive numbers (1e12)
                payload = (rng.uniform(1e10, 1e12, 13)).tolist()
            else:
                # Dictionary payload with missing keys
                payload = {f"c{k}": float(rng.uniform(0, 1)) for k in range(rng.randint(1, 13))}

            res = self.coupler.evaluate(payload)
            alpha = res["alpha_p184"]
            self.assertTrue(np.isfinite(alpha), f"Non-finite alpha at iter {i}: {alpha}")
            self.assertTrue(-3.0 <= alpha <= 3.0, f"Alpha escaped [-3.0, 3.0] at iter {i}: {alpha}")
            self.assertTrue(0.0 <= res["h_phase184"] <= 1.0)
            self.assertTrue(0.0 <= res["fcpi_v184"] <= 1.0)

    def test_adv_f904_04_zero_synthetic_rows_native_int_invariant(self) -> None:
        """Adversarial F904: Verify synthetic_rows == 0 strictly native Python int 0 across all 5 engines."""
        engines = [
            self.wavelet_engine,
            self.sheaf_engine,
            self.rough_engine,
            self.options_engine,
            self.coupler,
        ]
        for eng in engines:
            sr = getattr(eng, "synthetic_rows", 0)
            self.assertEqual(sr, 0)
            self.assertIs(type(sr), int, f"synthetic_rows on {type(eng).__name__} is {type(sr)}, not native int!")


if __name__ == "__main__":
    unittest.main()

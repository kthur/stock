"""
tests/test_challenger_m1_phase180_stress.py — Adversarial Stress Test Harness for Milestone M1 (Phase 180, Features F880–F884).

Adversarial Stress Scenarios:
1. SVI-JW Total Variance (F883): Feed zero, negative, extreme strike spreads, and short maturities. Verify total variance strictly satisfies w(k) > 0 and no crash occurs.
2. 12-Pillar ZCA Whitening (F884): Feed singular/collinear 12x12 covariance matrices with eigenvalues near 0. Verify eigenvalue clamping, positive semi-definiteness, and FCPI_v180 in (0, 1].
3. Wavelet Scattering & Ricci Flow (F880): Feed flat lines, single-spike pulses, and extreme price changes. Verify bounds in [-3.0, 3.0] and absence of NaNs.
4. Sheaf GNN (F881): Feed isolated nodes and cycles. Verify Laplacian symmetry and non-negative eigenvalues.
5. Rough Path Hawkes (F882): Verify degree-6 log-signature tensor dimensions and stability on rapid bursts.
6. Phase 180 End-to-End Stress: Large-scale degenerate cross-section with NaN/Inf/singular pillars.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Add repository paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F880 Wavelet & Ricci Flow
from src.core.wavelet_scattering import (
    compute_dual_tree_complex_wavelet_scattering,
    compute_holomorphic_ricci_flow,
    create_dual_tree_analytic_wavelet,
    KahlerEinsteinScatteringWaveletEngine,
)

# F881 Sheaf GNN
from src.core.sheaf_gnn import (
    compute_supersymmetric_sheaf_laplacian,
    compute_susy_sheaf_cohomology_h1,
    compute_susy_forman_ricci_curvature,
    compute_susy_spin_embedding,
    CliffordSheafCurvatureGNNEngine,
)

# F882 Rough Path Hawkes
from src.core.rough_path_hawkes import (
    compute_degree6_rough_path_signature,
    compute_degree6_log_signature,
    compute_volterra_hawkes_intensity,
    compute_fractional_volterra_intensity,
    compute_rough_volterra_micro_momentum_deg6,
    RoughPathVolterraHawkesEngine,
)

# F883 SVI-JW & 10th-Order Greeks
from src.core.essvi_greeks import (
    compute_svi_jw_total_variance,
    fit_svi_jw_arbitrage_free,
    compute_tenth_order_black_scholes_greeks,
    calculate_tenth_order_surface_skew,
    NinthOrderSABReSSVIAccelerator,
)

# F884 12-Pillar ZCA & Phase 180 Coupler
from src.ai.factor_orthogonalizer import (
    compute_duodecuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase180,
    DUODECUPLE_PILLAR_MAP,
    DuodecuplePillarMap,
    FactorOrthogonalizerEngine,
)
from src.ai.historical_couplers import (
    Phase180Coupler,
    F884Coupler,
    DuodecuplePillarCoupler,
    Phase180AlphaCoupler,
)


class TestScenario1_SVI_JW_TotalVariance_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F883 (SVI-JW Total Variance & Deep Greeks)."""

    def test_svi_jw_zero_and_negative_maturities(self) -> None:
        """Verify w(k) > 0 and no crash when tau <= 0 or near zero."""
        extreme_taus = [0.0, -0.01, -1.0, -100.0, 1e-12, 1e-6, 1e-4]
        test_ks = [-5.0, -1.0, 0.0, 1.0, 5.0]

        for tau in extreme_taus:
            for k in test_ks:
                w = compute_svi_jw_total_variance(k=k, tau=tau)
                self.assertIsInstance(w, float)
                self.assertFalse(np.isnan(w), f"NaN returned for tau={tau}, k={k}")
                self.assertFalse(np.isinf(w), f"Inf returned for tau={tau}, k={k}")
                self.assertGreater(w, 0.0, f"Variance must be strictly positive: w={w} for tau={tau}, k={k}")

    def test_svi_jw_extreme_strike_spreads(self) -> None:
        """Verify w(k) > 0 for extreme strikes from k=-500 to k=+500."""
        extreme_ks = np.array([-500.0, -200.0, -50.0, -10.0, -1.0, 0.0, 1.0, 10.0, 50.0, 200.0, 500.0])
        w_vec = compute_svi_jw_total_variance(k=extreme_ks, tau=0.25)

        self.assertEqual(len(w_vec), len(extreme_ks))
        self.assertTrue(np.all(w_vec > 0.0), f"All w(k) must be strictly positive: {w_vec}")
        self.assertFalse(np.any(np.isnan(w_vec)), "NaNs detected in extreme strikes")
        self.assertFalse(np.any(np.isinf(w_vec)), "Infs detected in extreme strikes")

    def test_svi_jw_degenerate_parameters(self) -> None:
        """Feed zero, negative, and extreme jump-wing parameters."""
        param_sets = [
            {"v_t": 0.0, "v_min": -0.05, "p_t": 0.0, "c_t": 0.0, "psi_t": 0.0},
            {"v_t": -1.0, "v_min": -1.0, "p_t": -0.5, "c_t": -0.5, "psi_t": -100.0},
            {"v_t": 1e-8, "v_min": 1e-9, "p_t": 100.0, "c_t": 100.0, "psi_t": 100.0},
            {"v_t": 10.0, "v_min": 0.001, "p_t": 0.0001, "c_t": 0.0001, "psi_t": -1e6},
        ]

        for p in param_sets:
            w = compute_svi_jw_total_variance(k=np.array([-2.0, 0.0, 2.0]), tau=-0.1, **p)
            self.assertTrue(np.all(w > 0.0), f"Failed for param set {p}: w={w}")
            self.assertFalse(np.any(np.isnan(w)))
            self.assertFalse(np.any(np.isinf(w)))

    def test_svi_jw_fit_arbitrage_free_degenerate_grids(self) -> None:
        """Verify calibration robustness on inverted, single-point, or zero grids."""
        res_single = fit_svi_jw_arbitrage_free(k_grid=np.array([0.0]), tau_grid=np.array([0.25]))
        self.assertIn("calendar_arbitrage_free", res_single)
        self.assertIn("butterfly_arbitrage_free", res_single)
        self.assertIn("total_variance", res_single)
        self.assertTrue(np.all(res_single["total_variance"] > 0.0))

        # Inverted maturities
        res_inv = fit_svi_jw_arbitrage_free(
            k_grid=np.array([-0.2, 0.0, 0.2]),
            tau_grid=np.array([1.0, 0.5, 0.1]),
        )
        self.assertFalse(res_inv["calendar_arbitrage_free"])  # Correctly flags calendar arbitrage
        self.assertTrue(np.all(res_inv["total_variance"] > 0.0))

    def test_tenth_order_greeks_extreme_ranges(self) -> None:
        """Verify analytic 10th-order Greeks under deep OTM/ITM and near-zero volatility."""
        scenarios = [
            {"spot": 100.0, "strike": 0.01, "vol": 0.20, "tau": 0.25},   # Deep ITM
            {"spot": 100.0, "strike": 10000.0, "vol": 0.20, "tau": 0.25}, # Deep OTM
            {"spot": 100.0, "strike": 100.0, "vol": 0.001, "tau": 0.001}, # Near expiry / low vol
            {"spot": 100.0, "strike": 100.0, "vol": 5.0, "tau": 10.0},    # Extreme vol / long expiry
        ]

        for sc in scenarios:
            greeks = compute_tenth_order_black_scholes_greeks(
                spot=sc["spot"], strike=sc["strike"], vol=sc["vol"], tau=sc["tau"]
            )
            # Must include 10th-order specific Greeks
            self.assertIn("tenth_speed", greeks)
            self.assertIn("tenth_ultima", greeks)
            self.assertIn("tenth_order_tensor", greeks)
            for greek_name, val in greeks.items():
                self.assertIsInstance(val, float, f"{greek_name} must be float")
                self.assertFalse(np.isnan(val), f"NaN at {greek_name} for {sc}")
                self.assertFalse(np.isinf(val), f"Inf at {greek_name} for {sc}")


class TestScenario2_ZCA_Whitening_Collinearity_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F884 (12-Pillar ZCA Whitening & Phase 180 Coupler)."""

    def test_zca_rank_1_collinear_covariance(self) -> None:
        """Feed rank-1 all-ones 12x12 covariance matrix (11 zero eigenvalues)."""
        cov_rank1 = np.ones((12, 12), dtype=np.float64)
        w_zca = compute_duodecuple_pillar_zca_whitening(cov_rank1, ridge_epsilon=1e-6)

        self.assertEqual(w_zca.shape, (12, 12))
        # Symmetry check
        self.assertTrue(np.allclose(w_zca, w_zca.T, atol=1e-12), "W_ZCA must be symmetric")
        # Eigenvalues must be positive (clamped to ridge)
        eigs = np.linalg.eigvalsh(w_zca)
        self.assertTrue(np.all(eigs > 0.0), f"All W_ZCA eigenvalues must be strictly positive: min={np.min(eigs)}")
        self.assertFalse(np.any(np.isnan(w_zca)))
        self.assertFalse(np.any(np.isinf(w_zca)))

    def test_zca_near_zero_eigenvalues(self) -> None:
        """Feed ill-conditioned 12x12 covariance with eigenvalues spanning 1e-15 to 1.0."""
        rng = np.random.RandomState(42)
        q, _ = np.linalg.qr(rng.randn(12, 12))
        eigs_ill = np.array([1.0, 0.5, 0.1, 1e-3, 1e-6, 1e-8, 1e-10, 1e-12, 1e-14, 1e-16, 0.0, -1e-15])
        cov_ill = q @ np.diag(eigs_ill) @ q.T

        w_zca = compute_duodecuple_pillar_zca_whitening(cov_ill, ridge_epsilon=1e-6)
        self.assertTrue(np.allclose(w_zca, w_zca.T, atol=1e-12))
        eigs_res = np.linalg.eigvalsh(w_zca)
        self.assertTrue(np.all(eigs_res > 0.0))
        # Condition number of regularized whitening operator
        cond_num = np.max(eigs_res) / np.min(eigs_res)
        self.assertLess(cond_num, 1e10, f"Condition number of W_ZCA must remain controlled: {cond_num}")

    def test_zca_all_zeros_matrix(self) -> None:
        """Feed 12x12 zero matrix."""
        cov_zero = np.zeros((12, 12), dtype=np.float64)
        w_zca = compute_duodecuple_pillar_zca_whitening(cov_zero, ridge_epsilon=1e-6)
        self.assertTrue(np.allclose(w_zca, w_zca.T, atol=1e-12))
        self.assertTrue(np.all(np.linalg.eigvalsh(w_zca) > 0.0))

    def test_phase180_coupler_collinear_inputs(self) -> None:
        """Phase180Coupler with 12 identical/collinear columns across 50 symbols."""
        identical_col = np.linspace(0.1, 0.9, 50)
        df_collinear = pd.DataFrame(
            {f"pillar_{i}": identical_col for i in range(12)},
            index=[f"SYM_{i:03d}" for i in range(50)],
        )

        coupler = Phase180Coupler()
        res = coupler.evaluate(df_collinear)

        fcpi = res["fcpi_v180"]
        h_reg = res["h_phase180"]
        alpha = res["alpha_p180"]

        self.assertIsInstance(fcpi, pd.Series)
        self.assertTrue((fcpi > 0.0).all() and (fcpi <= 1.0).all(), f"FCPI out of range (0, 1]: min={fcpi.min()}, max={fcpi.max()}")
        self.assertTrue((h_reg > 0.0).all() and (h_reg <= 1.0).all(), f"h_phase180 out of range (0, 1]: min={h_reg.min()}, max={h_reg.max()}")
        self.assertTrue((alpha >= -3.0).all() and (alpha <= 3.0).all(), f"alpha out of range [-3, 3]: min={alpha.min()}, max={alpha.max()}")
        self.assertFalse(alpha.isna().any())

    def test_phase180_coupler_single_row_vector(self) -> None:
        """Phase180Coupler with single 1D vector of length 12."""
        single_vec = np.array([0.5] * 12)
        res = Phase180Coupler.compute(single_vec)

        self.assertIsInstance(res["fcpi_v180"], float)
        self.assertGreater(res["fcpi_v180"], 0.0)
        self.assertLessEqual(res["fcpi_v180"], 1.0)
        self.assertGreater(res["h_phase180"], 0.0)
        self.assertLessEqual(res["h_phase180"], 1.0)
        self.assertGreaterEqual(res["alpha_p180"], -3.0)
        self.assertLessEqual(res["alpha_p180"], 3.0)


class TestScenario3_Wavelet_Scattering_Ricci_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F880 (Wavelet Scattering & Holomorphic Ricci Flow)."""

    def test_ricci_flat_line_input(self) -> None:
        """Constant prices [100.0] * 100."""
        flat_prices = np.full(100, 100.0, dtype=np.float64)
        flat_volumes = np.full(100, 1000.0, dtype=np.float64)

        res = compute_holomorphic_ricci_flow(flat_prices, flat_volumes)
        alpha = res["alpha_score"]
        scat_score = res["f880_scattering_score"]

        self.assertFalse(np.isnan(alpha))
        self.assertFalse(np.isinf(alpha))
        self.assertGreaterEqual(alpha, -3.0)
        self.assertLessEqual(alpha, 3.0)
        self.assertGreaterEqual(scat_score, 0.05)
        self.assertLessEqual(scat_score, 0.95)

    def test_ricci_single_spike_pulse(self) -> None:
        """Impulse pulse: 100.0 everywhere, 10,000.0 at t=50."""
        prices = np.full(100, 100.0, dtype=np.float64)
        prices[50] = 10000.0

        res = compute_holomorphic_ricci_flow(prices)
        self.assertFalse(np.isnan(res["alpha_score"]))
        self.assertGreaterEqual(res["alpha_score"], -3.0)
        self.assertLessEqual(res["alpha_score"], 3.0)
        self.assertFalse(np.isnan(res["f880_ricci_velocity"]))
        self.assertFalse(np.isnan(res["f880_ricci_curvature"]))

    def test_ricci_flash_crash_pulse(self) -> None:
        """Flash crash: 100.0 everywhere, dropping to 0.001 at t=50."""
        prices = np.full(100, 100.0, dtype=np.float64)
        prices[50] = 0.001

        res = compute_holomorphic_ricci_flow(prices)
        self.assertFalse(np.isnan(res["alpha_score"]))
        self.assertGreaterEqual(res["alpha_score"], -3.0)
        self.assertLessEqual(res["alpha_score"], 3.0)

    def test_ricci_extreme_price_changes(self) -> None:
        """Exponential explosion / swing: prices from 1e-6 to 1e6."""
        prices = np.geomspace(1e-6, 1e6, 64)
        res = compute_holomorphic_ricci_flow(prices)
        self.assertFalse(np.isnan(res["alpha_score"]))
        self.assertGreaterEqual(res["alpha_score"], -3.0)
        self.assertLessEqual(res["alpha_score"], 3.0)

    def test_ricci_short_series_fallbacks(self) -> None:
        """Lengths 0, 1, 2, 3, 4."""
        for length in [0, 1, 2, 3, 4]:
            p = np.full(length, 100.0) if length > 0 else np.array([])
            res = compute_holomorphic_ricci_flow(p)
            self.assertEqual(res["alpha_score"], 0.0)
            self.assertEqual(res["f880_scattering_score"], 0.50)

    def test_dtcwt_scattering_zero_signal(self) -> None:
        """DTCWT scattering on all-zero signal."""
        zero_sig = np.zeros(64, dtype=np.float64)
        res = compute_dual_tree_complex_wavelet_scattering(zero_sig)
        self.assertFalse(np.isnan(res["f880_wavelet_score"]))
        self.assertGreaterEqual(res["f880_wavelet_score"], 0.05)
        self.assertLessEqual(res["f880_wavelet_score"], 0.95)
        self.assertGreater(res["total_scattering_energy"], 0.0)


class TestScenario4_Sheaf_GNN_Topology_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F881 (Supersymmetric Spin Sheaf GNN)."""

    def test_sheaf_laplacian_isolated_nodes(self) -> None:
        """Graph with 10 nodes and 0 edges (completely isolated)."""
        num_nodes = 10
        edges: List[Tuple[int, int, float]] = []
        lap = compute_supersymmetric_sheaf_laplacian(num_nodes, edges, stalk_dim=16)

        self.assertEqual(lap.shape, (160, 160))
        self.assertTrue(np.allclose(lap, lap.T, atol=1e-12), "Laplacian must be symmetric")
        eigs = np.linalg.eigvalsh(lap)
        self.assertTrue(np.all(eigs >= -1e-12), f"Eigenvalues must be non-negative: min={np.min(eigs)}")

    def test_sheaf_laplacian_partially_isolated_nodes(self) -> None:
        """Graph with 8 nodes: edge (0, 1) and (1, 2), nodes 3..7 isolated."""
        num_nodes = 8
        edges = [(0, 1, 1.0), (1, 2, 0.8)]
        lap = compute_supersymmetric_sheaf_laplacian(num_nodes, edges, stalk_dim=16)

        self.assertEqual(lap.shape, (128, 128))
        self.assertTrue(np.allclose(lap, lap.T, atol=1e-12))
        eigs = np.linalg.eigvalsh(lap)
        self.assertTrue(np.all(eigs >= -1e-12), f"Min eigenvalue negative: {np.min(eigs)}")

    def test_sheaf_laplacian_cycles(self) -> None:
        """Directed/undirected cycles: C3 (triangle), C5 (pentagon), and C12 cycle."""
        for num_nodes in [3, 5, 12]:
            edges = [(i, (i + 1) % num_nodes, 1.0) for i in range(num_nodes)]
            lap = compute_supersymmetric_sheaf_laplacian(num_nodes, edges, stalk_dim=16)

            self.assertEqual(lap.shape, (num_nodes * 16, num_nodes * 16))
            self.assertTrue(np.allclose(lap, lap.T, atol=1e-12), f"Cycle C{num_nodes} Laplacian not symmetric")
            eigs = np.linalg.eigvalsh(lap)
            self.assertTrue(np.all(eigs >= -1e-12), f"Cycle C{num_nodes} min eigenvalue negative: {np.min(eigs)}")

    def test_sheaf_laplacian_self_loops_and_extreme_weights(self) -> None:
        """Self-loops and weights [0.0, -5.0, 1e5]."""
        edges = [
            (0, 0, 1.0),     # self-loop
            (0, 1, 0.0),     # zero weight
            (1, 2, -5.0),    # negative weight
            (2, 3, 10000.0), # massive weight
        ]
        lap = compute_supersymmetric_sheaf_laplacian(4, edges, stalk_dim=16)
        self.assertTrue(np.allclose(lap, lap.T, atol=1e-12))
        eigs = np.linalg.eigvalsh(lap)
        self.assertTrue(np.all(eigs >= -1e-12))

    def test_sheaf_cohomology_isolated_and_cycles(self) -> None:
        """Verify H1 cohomology obstruction energy is non-negative and finite."""
        # Isolated
        res_iso = compute_susy_sheaf_cohomology_h1(5, [])
        self.assertGreaterEqual(res_iso["susy_obstruction_energy"], 0.0)
        self.assertEqual(res_iso["betti_0"], 80)  # 5 * 16 zero eigenvalues

        # Cycle C4
        edges_c4 = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 0, 1.0)]
        res_cycle = compute_susy_sheaf_cohomology_h1(4, edges_c4)
        self.assertGreaterEqual(res_cycle["susy_obstruction_energy"], 0.0)
        self.assertGreaterEqual(res_cycle["betti_1"], 0)

    def test_susy_forman_curvature_bounds(self) -> None:
        """Verify Forman-Ricci curvature bounded strictly in [-5.0, 5.0]."""
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 0, 1.0), (2, 3, 0.5)]
        curv = compute_susy_forman_ricci_curvature(4, edges)
        self.assertEqual(len(curv), 4)
        self.assertTrue(np.all(curv >= -5.0) and np.all(curv <= 5.0))


class TestScenario5_Rough_Path_Hawkes_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F882 (Degree-6 Rough Path Hawkes & Volterra Jumps)."""

    def test_degree6_signature_tensor_dimensions(self) -> None:
        """Verify degree-6 signature dimensions: 2D -> 126, 1D -> 6, 3D -> 1092."""
        # 2D path
        path_2d = np.random.randn(20, 2)
        sig_2d = compute_degree6_rough_path_signature(path_2d, degree=6)
        expected_len_2d = sum(2 ** m for m in range(1, 7))  # 2 + 4 + 8 + 16 + 32 + 64 = 126
        self.assertEqual(len(sig_2d), 126)
        self.assertEqual(len(sig_2d), expected_len_2d)

        # 1D path
        path_1d = np.random.randn(20, 1)
        sig_1d = compute_degree6_rough_path_signature(path_1d, degree=6)
        expected_len_1d = sum(1 ** m for m in range(1, 7))  # 6
        self.assertEqual(len(sig_1d), 6)
        self.assertEqual(len(sig_1d), expected_len_1d)

        # 3D path
        path_3d = np.random.randn(10, 3)
        sig_3d = compute_degree6_rough_path_signature(path_3d, degree=6)
        expected_len_3d = sum(3 ** m for m in range(1, 7))  # 3+9+27+81+243+729 = 1092
        self.assertEqual(len(sig_3d), 1092)

    def test_degree6_log_signature_tensor_dimensions(self) -> None:
        """Verify degree-6 log-signature tensor dimension matches 126 for 2D."""
        path_2d = np.random.randn(25, 2)
        log_sig = compute_degree6_log_signature(path_2d, degree=6)
        self.assertEqual(len(log_sig), 126)
        self.assertFalse(np.any(np.isnan(log_sig)))
        self.assertFalse(np.any(np.isinf(log_sig)))

    def test_volterra_hawkes_rapid_bursts(self) -> None:
        """Stress with 1000 events in 0.01 seconds and zero intervals (dt=0)."""
        # Microsecond burst
        ts_burst = np.linspace(0.0, 0.01, 100)
        res_burst = compute_volterra_hawkes_intensity(ts_burst, hurst=0.12, beta=1.50)
        intensities = res_burst["volterra_intensity"]

        self.assertEqual(len(intensities), 100)
        self.assertTrue(np.all(intensities >= 0.10), f"Intensities must exceed base rate: min={np.min(intensities)}")
        self.assertFalse(np.any(np.isnan(intensities)))
        self.assertFalse(np.any(np.isinf(intensities)))

        # Identical timestamps (dt = 0)
        ts_zero_dt = np.zeros(20)
        res_zero = compute_volterra_hawkes_intensity(ts_zero_dt, hurst=0.12)
        self.assertTrue(np.all(res_zero["volterra_intensity"] >= 0.10))

    def test_fractional_volterra_intensity_hurst_extremes(self) -> None:
        """Hurst parameter extremes: H=0.01 (extremely rough) to H=0.49 (near Brownian)."""
        ts = np.linspace(0.0, 10.0, 50)
        for h in [0.01, 0.05, 0.12, 0.35, 0.49]:
            res = compute_fractional_volterra_intensity(ts, hurst=h)
            self.assertIn("jump_risk_score", res)
            risk = res["jump_risk_score"]
            self.assertGreaterEqual(risk, 0.0)
            self.assertLessEqual(risk, 1.0)
            self.assertFalse(np.isnan(risk))

    def test_rough_volterra_micro_momentum_flash_crashes(self) -> None:
        """Feed massive single-step jumps (+500%, -99%) and huge volumes."""
        prices = np.array([100.0, 102.0, 101.0, 500.0, 5.0, 6.0, 7.0] * 5)
        volumes = np.array([1000.0, 1200.0, 800.0, 1e9, 1e9, 500.0, 600.0] * 5)

        res = compute_rough_volterra_micro_momentum_deg6(prices, volumes, degree=6)
        self.assertGreaterEqual(res["micro_momentum"], -3.0)
        self.assertLessEqual(res["micro_momentum"], 3.0)
        self.assertGreaterEqual(res["score"], 0.05)
        self.assertLessEqual(res["score"], 0.95)
        self.assertEqual(len(res["signature_vector"]), 126)
        self.assertEqual(len(res["log_signature_vector"]), 126)


class TestScenario6_Phase180_EndToEnd_MultiFactor_Synthesis_Stress(unittest.TestCase):
    """Adversarial stress testing across large-scale degenerate cross-sectional factor matrices."""

    def test_phase180_synthesis_with_corrupted_inputs(self) -> None:
        """100 symbols x 12 pillars with NaN, Inf, extreme, and constant inputs."""
        rng = np.random.RandomState(999)
        raw_data = rng.uniform(0.1, 0.9, size=(100, 12))

        # Introduce pathologies
        raw_data[0:5, :] = np.nan           # Row of all NaNs
        raw_data[5:10, :] = np.inf          # Row of all Infs
        raw_data[10:15, :] = -np.inf        # Row of all -Infs
        raw_data[15:20, 0:6] = 10000.0      # Out of bounds large
        raw_data[20:25, 6:12] = -5000.0     # Out of bounds negative
        raw_data[25:35, :] = 0.50           # Completely flat noise floor

        pillar_names = list(DUODECUPLE_PILLAR_MAP.keys())
        df = pd.DataFrame(raw_data, columns=pillar_names, index=[f"SYM_{i:03d}" for i in range(100)])

        coupler = Phase180Coupler()
        res = coupler.evaluate(df)

        alpha = res["alpha_p180"]
        fcpi = res["fcpi_v180"]
        h_reg = res["h_phase180"]

        self.assertEqual(len(alpha), 100)
        self.assertFalse(alpha.isna().any(), "No NaNs permitted in synthesized alpha")
        self.assertTrue((alpha >= -3.0).all() and (alpha <= 3.0).all(), f"Alpha bounds violated: min={alpha.min()}, max={alpha.max()}")
        self.assertTrue((fcpi > 0.0).all() and (fcpi <= 1.0).all(), f"FCPI bounds violated: min={fcpi.min()}, max={fcpi.max()}")
        self.assertTrue((h_reg > 0.0).all() and (h_reg <= 1.0).all(), f"h_phase180 bounds violated: min={h_reg.min()}, max={h_reg.max()}")


if __name__ == "__main__":
    unittest.main()

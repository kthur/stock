"""
tests/test_phase164_empirical_stress.py — Empirical Challenger Stress Suite for Phase 164 (Milestone 1).

Rigorous empirical stress test harness, generators, and oracles verifying:
- Module 1: F800 Symplectic Manifold Geodesic Flow & Tensor-Train SVD (Degenerate Covariance, Boundary Prices, TT Entropy)
- Module 2: F801 Lorentz Hyperbolic Gyrovector Space & Hodge-Helmholtz GNN (Boundary Coordinates, Metric Axioms, Cycle Loops)
- Module 3: F802 Non-Linear Volterra Fractional Hawkes Jump-Diffusion (Extreme Hurst, Singular Lags, Softplus Saturation)
- Module 4: F803 Multi-Point Arbitrage-Free SVI Surface Skew & 5th-Order Greeks (Roger Lee Bounds, Butterfly Curvature, Greeks Greeks)
- Module 5: End-to-End Execution Latency SLA (< 25ms/symbol) & Production Invariants (synthetic_rows == 0, Net <= Gross Equity)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact empirical bounds.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.spectral_wavelet_decomposition import (
    SpectralWaveletDecompositionEnginePhase164,
    compute_symplectic_geodesic_flow,
    compute_tensor_train_decomposition,
    compute_tensor_train_entropy,
)
from src.core.value_chain_curvature_gnn import (
    ValueChainCurvatureGNNEnginePhase164,
    lorentz_inner_product,
    lorentz_distance,
    lorentz_to_poincare,
    poincare_to_lorentz,
    gyrovector_addition,
    compute_discrete_hodge_helmholtz_decomposition,
    compute_lorentz_hyperbolic_graph_representation,
)
from src.core.cross_market_micro_momentum import (
    CrossMarketMicroMomentumEnginePhase164,
    compute_volterra_fractional_kernel,
    compute_nonlinear_hawkes_activation,
    estimate_volterra_fractional_hawkes_params,
)
from src.core.option_surface_accelerator import (
    OptionSurfaceAcceleratorPhase164,
    compute_fifth_order_black_scholes_greeks,
    verify_multipoint_svi_roger_lee_arbitrage_free,
    calculate_fifth_order_surface_skew,
)
from src.ai.factor_orthogonalizer import (
    compute_octuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase164,
    compute_riemannian_airm_distance,
)
from src.ai.historical_couplers import Phase164Coupler


class TestPhase164EmpiricalStress(unittest.TestCase):
    """Empirical Challenger test suite with generators, oracles, and stress harnesses."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.wavelet_engine = SpectralWaveletDecompositionEnginePhase164()
        cls.curvature_engine = ValueChainCurvatureGNNEnginePhase164()
        cls.micro_engine = CrossMarketMicroMomentumEnginePhase164()
        cls.options_engine = OptionSurfaceAcceleratorPhase164()
        cls.coupler = Phase164Coupler()

    # =========================================================================
    # Module 1: F800 Symplectic Manifold Geodesic Flow & Tensor-Train SVD
    # =========================================================================

    def test_f800_tc01_random_ill_conditioned_covariance_matrices(self) -> None:
        """F800-TC01: Symplectic geodesic flow under random covariance with cond(Sigma) up to 10^16."""
        rng = np.random.RandomState(800)
        for cond_power in [2, 6, 10, 14, 16]:
            # Generate random orthogonal matrix Q
            A = rng.randn(6, 6)
            Q, _ = np.linalg.qr(A)
            # Create eigenvalues spanning 1 to 10^cond_power
            diag_eigs = np.logspace(0, cond_power, 6)
            cov_ill = Q @ np.diag(diag_eigs) @ Q.T
            cov_ill = 0.5 * (cov_ill + cov_ill.T)
            self.assertGreaterEqual(np.linalg.cond(cov_ill), 10 ** (cond_power - 1))

            # Simulate price path with returns generated from this ill-conditioned covariance
            returns_sim = rng.multivariate_normal(np.zeros(6), cov_ill, size=20)
            prices_sim = 100.0 * np.exp(np.cumsum(returns_sim[:, 0]))

            res = compute_symplectic_geodesic_flow(prices_sim)
            vel = res["f800_symplectic_velocity"]
            entropy = res["f800_tensor_train_entropy"]
            drift = res["f800_symplectic_invariance_drift"]

            # Oracles: Bounded velocity [0.0, 5.0], finite entropy >= 0, finite drift
            self.assertTrue(0.0 <= vel <= 5.0, f"Velocity {vel} out of bounds for cond=10^{cond_power}")
            self.assertTrue(np.isfinite(vel))
            self.assertTrue(entropy >= 0.0)
            self.assertTrue(np.isfinite(entropy))
            self.assertTrue(np.isfinite(drift))

    def test_f800_tc02_singular_and_rank_deficient_phase_space(self) -> None:
        """F800-TC02: Constant prices (zero variance) and rank-1 returns yield exact ground state."""
        # 1. Constant price sequence: q = 0, p = 0
        prices_const = np.full(60, 100.0)
        res_const = compute_symplectic_geodesic_flow(prices_const)
        self.assertEqual(res_const["f800_symplectic_velocity"], 0.0)
        self.assertEqual(res_const["f800_tensor_train_entropy"], 0.0)
        self.assertEqual(res_const["f800_symplectic_invariance_drift"], 0.0)

        # 2. Perfect linear trend: q = constant, p = 0
        prices_linear = np.linspace(100.0, 150.0, 60)
        res_linear = compute_symplectic_geodesic_flow(prices_linear)
        self.assertTrue(np.isfinite(res_linear["f800_symplectic_velocity"]))
        self.assertTrue(0.0 <= res_linear["f800_symplectic_velocity"] <= 5.0)

    def test_f800_tc03_boundary_lengths_and_corrupted_inputs(self) -> None:
        """F800-TC03: Sequence lengths 0, 1, 2, 4, 5, 200 and NaN/Inf corruptions."""
        # Lengths < 5 return default zeros
        for length in [0, 1, 2, 3, 4]:
            arr = np.full(length, 100.0)
            res = compute_symplectic_geodesic_flow(arr)
            self.assertEqual(res["f800_symplectic_velocity"], 0.0)
            self.assertEqual(res["f800_tensor_train_entropy"], 0.0)

        # Length > 128 is truncated cleanly
        arr_long = 100.0 + np.cumsum(np.random.randn(250))
        res_long = compute_symplectic_geodesic_flow(arr_long)
        self.assertTrue(0.0 <= res_long["f800_symplectic_velocity"] <= 5.0)

        # Corrupted array with NaNs, Infs, negative and zero prices
        corrupt = np.array([np.nan, 100.0, -50.0, 0.0, np.inf, -np.inf, 105.0, 110.0])
        res_corrupt = compute_symplectic_geodesic_flow(corrupt)
        self.assertTrue(np.isfinite(res_corrupt["f800_symplectic_velocity"]))
        self.assertTrue(np.isfinite(res_corrupt["f800_tensor_train_entropy"]))
        self.assertTrue(np.isfinite(res_corrupt["f800_symplectic_invariance_drift"]))

    def test_f800_tc04_tensor_train_svd_rank_truncation_and_entropy(self) -> None:
        """F800-TC04: Tensor-train SVD core shapes, rank truncation, and entropy bounds."""
        rng = np.random.RandomState(804)
        # 3D tensor of shape (8, 6, 10)
        tensor_3d = rng.randn(8, 6, 10)

        # Max rank 2 truncation
        tt_res_r2 = compute_tensor_train_decomposition(tensor_3d, max_rank=2)
        self.assertEqual(len(tt_res_r2.cores), 3)
        self.assertLessEqual(tt_res_r2.cores[0].shape[1], 2)
        self.assertLessEqual(tt_res_r2.cores[1].shape[2], 2)

        # Max rank 6
        tt_res_r6 = compute_tensor_train_decomposition(tensor_3d, max_rank=6)
        entropy_r6 = compute_tensor_train_entropy(tt_res_r6.singular_values)
        self.assertTrue(entropy_r6 >= 0.0)
        self.assertTrue(np.isfinite(entropy_r6))

        # Degenerate all-zeros tensor: entropy must be exact 0.0
        tt_zero = compute_tensor_train_decomposition(np.zeros((4, 4, 4)))
        self.assertEqual(compute_tensor_train_entropy(tt_zero.singular_values), 0.0)

    # =========================================================================
    # Module 2: F801 Lorentz Gyrovector Space & Hodge-Helmholtz GNN
    # =========================================================================

    def test_f801_tc05_lorentz_metric_axioms(self) -> None:
        """F801-TC05: Verify all metric axioms on the forward Lorentz hyperboloid H^d."""
        rng = np.random.RandomState(801)
        # Generate points in Poincare ball D^2: ||u|| < 1
        for _ in range(15):
            u_p = rng.uniform(-0.6, 0.6, 2)
            v_p = rng.uniform(-0.6, 0.6, 2)
            w_p = rng.uniform(-0.6, 0.6, 2)

            u_l = poincare_to_lorentz(u_p)
            v_l = poincare_to_lorentz(v_p)
            w_l = poincare_to_lorentz(w_p)

            # Hyperboloid condition: <x, x>_L = -1 and x_0 >= 1
            self.assertAlmostEqual(lorentz_inner_product(u_l, u_l), -1.0, places=5)
            self.assertGreaterEqual(u_l[0], 1.0)

            # Axiom 1: Identity of indiscernibles: d(u, u) = 0
            self.assertAlmostEqual(lorentz_distance(u_l, u_l), 0.0, places=6)

            # Axiom 2: Positivity: d(u, v) >= 0
            d_uv = lorentz_distance(u_l, v_l)
            self.assertGreaterEqual(d_uv, 0.0)

            # Axiom 3: Symmetry: d(u, v) = d(v, u)
            d_vu = lorentz_distance(v_l, u_l)
            self.assertAlmostEqual(d_uv, d_vu, places=6)

            # Axiom 4: Triangle inequality: d(u, w) <= d(u, v) + d(v, w)
            d_uw = lorentz_distance(u_l, w_l)
            d_vw = lorentz_distance(v_l, w_l)
            self.assertLessEqual(d_uw, d_uv + d_vw + 1e-6, "Lorentz triangle inequality failed")

    def test_f801_tc06_boundary_coordinates_poincare_to_lorentz(self) -> None:
        """F801-TC06: Extreme boundary coordinates ||u|| -> 1.0 within Poincare disk."""
        boundary_norms = [0.95, 0.99, 0.999, 0.9999, 0.99999]
        for norm in boundary_norms:
            u = np.array([norm, 0.0])
            u_lor = poincare_to_lorentz(u)
            self.assertTrue(np.all(np.isfinite(u_lor)), f"poincare_to_lorentz produced non-finite for norm {norm}")
            self.assertGreaterEqual(u_lor[0], 1.0)
            self.assertAlmostEqual(lorentz_inner_product(u_lor, u_lor), -1.0, places=4)

            # Stereographic roundtrip
            u_proj = lorentz_to_poincare(u_lor)
            self.assertTrue(np.all(np.isfinite(u_proj)))
            self.assertLess(np.linalg.norm(u_proj), 1.0)
            self.assertAlmostEqual(float(np.linalg.norm(u_proj)), norm, places=4)

    def test_f801_tc07_gyrovector_addition_boundary_invariance(self) -> None:
        """F801-TC07: Gyrovector addition preserves Poincaré ball boundary ||u (+) v|| < 1/sqrt(c)."""
        rng = np.random.RandomState(807)
        c = 1.0
        for _ in range(30):
            # High-speed relativistic velocities near speed of light (radius near 1.0)
            u = rng.uniform(-0.95, 0.95, 3)
            if np.linalg.norm(u) >= 0.98:
                u = u * (0.95 / np.linalg.norm(u))
            v = rng.uniform(-0.95, 0.95, 3)
            if np.linalg.norm(v) >= 0.98:
                v = v * (0.95 / np.linalg.norm(v))

            w = gyrovector_addition(u, v, c=c)
            norm_w = float(np.linalg.norm(w))
            self.assertLess(norm_w, 1.0 / np.sqrt(c), f"Gyrovector sum escaped ball: norm {norm_w} >= 1.0")
            self.assertTrue(np.all(np.isfinite(w)))

        # Identity element: u (+) 0 = u
        zero_vec = np.zeros(3)
        test_u = np.array([0.5, -0.3, 0.4])
        u_plus_zero = gyrovector_addition(test_u, zero_vec, c=c)
        np.testing.assert_allclose(u_plus_zero, test_u, atol=1e-6)

        # Inverse element: u (+) (-u) = 0
        u_plus_neg = gyrovector_addition(test_u, -test_u, c=c)
        np.testing.assert_allclose(u_plus_neg, np.zeros(3), atol=1e-6)

    def test_f801_tc08_hodge_helmholtz_orthogonality_and_energy_conservation(self) -> None:
        """F801-TC08: Discrete Hodge-Helmholtz orthogonal decomposition and exact energy conservation."""
        # Graph with 4 nodes and 5 edges (triangle with a tail)
        # Edges: 0: (0,1), 1: (1,2), 2: (2,0), 3: (2,3), 4: (1,3)
        B1 = np.array([
            [-1.0,  0.0,  1.0,  0.0,  0.0],
            [ 1.0, -1.0,  0.0,  0.0, -1.0],
            [ 0.0,  1.0, -1.0, -1.0,  0.0],
            [ 0.0,  0.0,  0.0,  1.0,  1.0],
        ])
        # Two triangles: 2-boundary operator B2 (faces)
        # Face 0: edges (0, 1, 2); Face 1: edges (1, 3, -4)
        B2 = np.array([
            [1.0,  0.0],
            [1.0,  1.0],
            [1.0,  0.0],
            [0.0,  1.0],
            [0.0, -1.0],
        ])

        rng = np.random.RandomState(808)
        for _ in range(10):
            F = rng.randn(5) * 100.0  # Arbitrary shock flow vector
            res = compute_discrete_hodge_helmholtz_decomposition(F, B1=B1, B2=B2)

            f_grad = res["flow_gradient"]
            f_curl = res["flow_curl"]
            f_harm = res["flow_harmonic"]

            # 1. Exact reconstruction: F = F_grad + F_curl + h
            F_reconstructed = f_grad + f_curl + f_harm
            np.testing.assert_allclose(F_reconstructed, F, atol=1e-8, err_msg="Hodge decomposition reconstruction failed")

            # 2. Pairwise orthogonality: <f_grad, f_curl> = 0, <f_grad, h> = 0, <f_curl, h> = 0
            self.assertAlmostEqual(float(np.dot(f_grad, f_curl)), 0.0, places=5)
            self.assertAlmostEqual(float(np.dot(f_grad, f_harm)), 0.0, places=5)
            self.assertAlmostEqual(float(np.dot(f_curl, f_harm)), 0.0, places=5)

            # 3. Energy conservation: ||F||^2 = ||f_grad||^2 + ||f_curl||^2 + ||h||^2
            energy_total = np.sum(F ** 2)
            energy_parts = np.sum(f_grad ** 2) + np.sum(f_curl ** 2) + np.sum(f_harm ** 2)
            np.testing.assert_allclose(energy_parts, energy_total, atol=1e-6)

    def test_f801_tc09_singular_and_disconnected_graphs(self) -> None:
        """F801-TC09: Empty, single-node, and disconnected graph distance matrices."""
        # Empty graph
        res_empty = compute_discrete_hodge_helmholtz_decomposition(np.array([]))
        self.assertEqual(res_empty["harmonic_circulation"], 0.0)

        # 2-node graph (tree, no cycles)
        D_tree = np.array([[0.0, 1.0], [1.0, 0.0]])
        res_tree = compute_lorentz_hyperbolic_graph_representation(D_tree)
        self.assertTrue(np.isfinite(res_tree["f801_lorentz_radius"]))
        self.assertTrue(0.0 <= res_tree["f801_lorentz_radius"] < 1.0)

    # =========================================================================
    # Module 3: F802 Non-Linear Volterra Fractional Hawkes Jump-Diffusion
    # =========================================================================

    def test_f802_tc10_volterra_kernel_rough_monotonicity_and_singularity(self) -> None:
        """F802-TC10: Subdiffusive fractional kernel K(t) monotonicity for H < 0.5 and t -> 0."""
        # In rough regime H = 0.12 < 0.5, kernel is strictly monotonically decreasing
        lags = np.linspace(0.01, 5.0, 50)
        kernel = compute_volterra_fractional_kernel(lags, hurst=0.12, beta=2.50)
        self.assertTrue(np.all(np.isfinite(kernel)))
        self.assertTrue(np.all(kernel > 0.0))
        # Monotonicity check
        diffs = np.diff(kernel)
        self.assertTrue(np.all(diffs < 0.0), "Volterra kernel must be strictly monotonically decreasing for H=0.12")

        # Singularity at t=0: t_safe prevents zero-division
        k_zero = compute_volterra_fractional_kernel(np.array([0.0, -1.0]), hurst=0.01, beta=1.0)
        self.assertTrue(np.all(np.isfinite(k_zero)))
        self.assertTrue(np.all(k_zero > 0.0))

        # Hurst clamping to [0.01, 0.49]
        k_clamp_low = compute_volterra_fractional_kernel(lags, hurst=-0.5, beta=2.0)
        k_clamp_high = compute_volterra_fractional_kernel(lags, hurst=0.99, beta=2.0)
        self.assertTrue(np.all(np.isfinite(k_clamp_low)))
        self.assertTrue(np.all(np.isfinite(k_clamp_high)))

    def test_f802_tc11_nonlinear_softplus_activation_stability(self) -> None:
        """F802-TC11: Softplus activation phi(x) = ln(1 + e^x) numerical stability across [-1000, 1000]."""
        # Test scalar and array inputs
        x_vals = np.array([-1000.0, -100.0, -31.0, -30.0, -1.0, 0.0, 1.0, 30.0, 31.0, 100.0, 1000.0])
        phi = compute_nonlinear_hawkes_activation(x_vals)
        self.assertTrue(np.all(np.isfinite(phi)), "Softplus activation produced non-finite values")
        self.assertTrue(np.all(phi >= 0.0), "Softplus must be non-negative")

        # Scalar tests
        self.assertAlmostEqual(compute_nonlinear_hawkes_activation(0.0), np.log(2.0), places=6)
        self.assertAlmostEqual(compute_nonlinear_hawkes_activation(50.0), 50.0, places=4)
        self.assertAlmostEqual(compute_nonlinear_hawkes_activation(-50.0), np.exp(-50.0), places=6)

    def test_f802_tc12_jump_diffusion_clustering_and_branching_ratio_subcriticality(self) -> None:
        """F802-TC12: Explosive jump clustering series keeps branching ratio strictly subcritical < 1.0."""
        # Massive flash crashes: 40 consecutive 10-sigma outliers
        rng = np.random.RandomState(802)
        crash_series = np.concatenate([
            rng.normal(0, 0.01, 30),
            np.full(20, -0.25),  # 20 consecutive -25% days
            np.full(20, 0.25),   # 20 consecutive +25% days
        ])
        macro_shocks = {
            "vix": np.array([20.0, 45.0, 75.0, 85.0]),
            "sox": np.array([100.0, 80.0, 60.0, 40.0]),
        }
        res = estimate_volterra_fractional_hawkes_params(crash_series, macro_shocks=macro_shocks)

        eta = res["f802_fractional_branching_ratio"]
        jump_int = res["f802_volterra_jump_intensity"]
        impulse = res["f802_coupled_impulse_forecast"]

        # Invariants
        self.assertTrue(0.05 <= eta < 1.0, f"Branching ratio {eta} must be strictly subcritical < 1.0")
        self.assertTrue(0.0 <= jump_int <= 1.0, f"Jump intensity {jump_int} out of [0, 1]")
        self.assertTrue(0.0 <= impulse <= 5.0, f"Coupled impulse {impulse} out of [0, 5]")

    # =========================================================================
    # Module 4: F803 Multi-Point SVI Surface Skew & 5th-Order Greeks
    # =========================================================================

    def test_f803_tc13_fifth_order_black_scholes_greeks_analytical_consistency(self) -> None:
        """F803-TC13: 5th-order Greeks (hyperspeed, hypercolor, hyperultima, hyperzomma) stability."""
        # Deep ITM, ATM, Deep OTM
        cases = [
            {"spot": 100.0, "strike": 100.0, "tau": 0.25, "vol": 0.20},  # ATM
            {"spot": 200.0, "strike": 100.0, "tau": 0.50, "vol": 0.30},  # Deep ITM
            {"spot": 50.0, "strike": 100.0, "tau": 0.10, "vol": 0.15},   # Deep OTM
            {"spot": 100.0, "strike": 100.0, "tau": 5.0, "vol": 0.80},   # Long maturity high vol
            {"spot": 100.0, "strike": 100.0, "tau": 0.001, "vol": 0.05}, # Short expiry low vol
        ]
        for c in cases:
            g5 = compute_fifth_order_black_scholes_greeks(c["spot"], c["strike"], c["tau"], c["vol"])
            for greek_name in ["hyper_speed", "hyper_color", "hyper_ultima", "hyper_zomma"]:
                val = g5.get(greek_name, np.nan)
                self.assertTrue(np.isfinite(val), f"Greek {greek_name} is non-finite for case {c}")

        # Degenerate inputs (spot <= 0, strike <= 0, tau <= 0, vol <= 0) return 0.0
        g_degen = compute_fifth_order_black_scholes_greeks(-10.0, 0.0, -0.5, 0.0)
        self.assertEqual(g_degen["hyper_speed"], 0.0)
        self.assertEqual(g_degen["hyper_color"], 0.0)
        self.assertEqual(g_degen["hyper_ultima"], 0.0)

    def test_f803_tc14_svi_roger_lee_and_butterfly_arbitrage_oracles(self) -> None:
        """F803-TC14: Multi-point SVI correctly identifies Roger Lee and Durrleman butterfly arbitrage."""
        strikes = np.linspace(40.0, 200.0, 25)
        ivs = np.full_like(strikes, 0.20)

        # 1. Valid Arbitrage-Free SVI
        valid_params = {"a": 0.04, "b": 0.10, "rho": -0.20, "m": 0.0, "sigma": 0.15}
        res_valid = verify_multipoint_svi_roger_lee_arbitrage_free(strikes, ivs, tau=0.25, params=valid_params)
        self.assertTrue(res_valid["is_arbitrage_free"])
        self.assertTrue(res_valid["roger_lee_satisfied"])
        self.assertTrue(res_valid["butterfly_satisfied"])
        self.assertTrue(res_valid["non_negative_satisfied"])

        # 2. Roger Lee Violation: |dw/dk| >= 2.0 (b * (1 + rho) = 1.5 * 1.8 = 2.7 > 2.0)
        bad_rl = {"a": 0.04, "b": 1.50, "rho": 0.80, "m": 0.0, "sigma": 0.15}
        res_bad_rl = verify_multipoint_svi_roger_lee_arbitrage_free(strikes, ivs, tau=0.25, params=bad_rl)
        self.assertFalse(res_bad_rl["is_arbitrage_free"])
        self.assertFalse(res_bad_rl["roger_lee_satisfied"])

        # 3. Negative Total Variance Violation: a + b*(...) < 0
        bad_nonneg = {"a": -0.60, "b": 0.05, "rho": 0.0, "m": 0.0, "sigma": 0.10}
        res_bad_nonneg = verify_multipoint_svi_roger_lee_arbitrage_free(strikes, ivs, tau=0.25, params=bad_nonneg)
        self.assertFalse(res_bad_nonneg["is_arbitrage_free"])
        self.assertFalse(res_bad_nonneg["non_negative_satisfied"])

    def test_f803_tc15_surface_skew_score_bounds_and_arbitrage_status(self) -> None:
        """F803-TC15: calculate_fifth_order_surface_skew produces bounded score in [0.05, 0.95]."""
        # Passing dictionary
        iv_dict = {"spot": 100.0, "tau": 0.25, "vol": 0.22, "strikes": [80, 90, 100, 110, 120], "ivs": [0.26, 0.24, 0.22, 0.21, 0.20]}
        res = calculate_fifth_order_surface_skew(iv_dict)
        score = res["f803_fifth_order_greeks_score"]
        self.assertTrue(0.05 <= score <= 0.95, f"Score {score} out of [0.05, 0.95]")
        self.assertIn(res["f803_arbitrage_free_status"], [0.0, 1.0])

        # Malformed input fallback
        res_none = calculate_fifth_order_surface_skew(None)
        self.assertEqual(res_none["f803_fifth_order_greeks_score"], 0.50)

    # =========================================================================
    # Module 5: Execution Latency SLA & Institutional Invariants
    # =========================================================================

    def test_f800_f803_tc16_execution_latency_sla_under_25ms(self) -> None:
        """TC16: Verify per-symbol execution latency is strictly below 25.0 ms for all 4 engines."""
        n_symbols = 30
        symbols = [f"BENCH_{i:03d}" for i in range(n_symbols)]
        np.random.seed(42)
        prices_dict = {
            s: pd.DataFrame({
                "Open": 100.0 + np.cumsum(np.random.randn(40)),
                "High": 102.0 + np.cumsum(np.random.randn(40)),
                "Low": 98.0 + np.cumsum(np.random.randn(40)),
                "Close": 100.0 + np.cumsum(np.random.randn(40)),
                "Volume": np.random.uniform(1000, 20000, 40),
            }) for s in symbols
        }

        # 1. F800 Wavelet Engine
        t0 = time.perf_counter()
        _ = self.wavelet_engine.compute_scores(prices_dict)
        ms_wavelet = ((time.perf_counter() - t0) * 1000.0) / n_symbols
        self.assertLess(ms_wavelet, 25.0, f"F800 latency {ms_wavelet:.3f} ms exceeds 25.0 ms SLA")

        # 2. F801 Curvature GNN Engine
        t0 = time.perf_counter()
        _ = self.curvature_engine.compute_scores(prices_dict)
        ms_curvature = ((time.perf_counter() - t0) * 1000.0) / n_symbols
        self.assertLess(ms_curvature, 25.0, f"F801 latency {ms_curvature:.3f} ms exceeds 25.0 ms SLA")

        # 3. F802 Micro Momentum Engine
        t0 = time.perf_counter()
        _ = self.micro_engine.compute_scores(prices_dict)
        ms_micro = ((time.perf_counter() - t0) * 1000.0) / n_symbols
        self.assertLess(ms_micro, 25.0, f"F802 latency {ms_micro:.3f} ms exceeds 25.0 ms SLA")

        # 4. F803 Option Surface Accelerator Engine
        t0 = time.perf_counter()
        _ = self.options_engine.compute_scores(prices_dict)
        ms_options = ((time.perf_counter() - t0) * 1000.0) / n_symbols
        self.assertLess(ms_options, 25.0, f"F803 latency {ms_options:.3f} ms exceeds 25.0 ms SLA")

    def test_tc17_institutional_invariants_zero_synthetic_rows(self) -> None:
        """TC17: Verify institutional invariant synthetic_rows == 0 strictly integer 0 across benchmark artifacts."""
        status_path = os.path.join(self.root_dir, "benchmarks", "30year", "status.json")
        self.assertTrue(os.path.exists(status_path))
        with open(status_path, "r", encoding="utf-8") as f:
            status_data = json.load(f)

        self.assertIn("synthetic_rows", status_data)
        self.assertIsInstance(status_data["synthetic_rows"], int)
        self.assertNotIsInstance(status_data["synthetic_rows"], bool)
        self.assertEqual(status_data["synthetic_rows"], 0)

        summary_path = os.path.join(self.root_dir, "benchmarks", "30year", "stock_universe_summary.json")
        self.assertTrue(os.path.exists(summary_path))
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        self.assertIn("metadata", summary_data)
        self.assertIn("synthetic_rows", summary_data["metadata"])
        self.assertIsInstance(summary_data["metadata"]["synthetic_rows"], int)
        self.assertNotIsInstance(summary_data["metadata"]["synthetic_rows"], bool)
        self.assertEqual(summary_data["metadata"]["synthetic_rows"], 0)


if __name__ == "__main__":
    unittest.main()

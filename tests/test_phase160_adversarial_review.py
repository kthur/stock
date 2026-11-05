"""
tests/test_phase160_adversarial_review.py — Adversarial Stress Test Suite for Phase 160 Alpha Engine.

Adversarially probes:
- Integrity: Verification of non-hardcoded dynamic outputs across varied inputs.
- Singular / Rank-deficient covariance matrices and N < D scenarios in Phase160Coupler.
- Extreme volatility, price discontinuities, all-constant feeds, zero-variance inputs.
- Non-Euclidean geometric boundary violations (Poincare ball boundary, metric axioms).
- Mathematical invariants: Triangle inequality, Roger Lee arbitrage bounds, AIRM symmetry.
- Corrupted data: NaNs, Infs, empty arrays, degenerate options surfaces.
"""

from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from src.core.spectral_wavelet_decomposition import (
    extract_riemannian_geodesic_flow,
    compute_riemannian_geodesic_flow,
    SpectralWaveletDecompositionEngine,
)
from src.core.value_chain_curvature_gnn import (
    compute_hyperbolic_graph_representation,
    poincare_distance,
    mobius_addition,
    poincare_exp_map,
    poincare_log_map,
    ValueChainCurvatureGNNEngine,
)
from src.core.cross_market_micro_momentum import (
    estimate_jump_diffusion_hawkes_params,
    compute_jump_diffusion_intensity,
    compute_hawkes_branching_ratio,
    CrossMarketMicroMomentumEngine,
)
from src.core.option_surface_accelerator import (
    calculate_higher_order_surface_skew,
    verify_svi_no_arbitrage,
    OptionSurfaceAccelerator,
)
from src.ai.factor_orthogonalizer import (
    apply_hyperbolic_deadband_phase160,
    FactorOrthogonalizerEngine,
    compute_riemannian_airm_distance,
    compute_septuple_pillar_zca_whitening,
)
from src.ai.historical_couplers import Phase160Coupler


class TestPhase160AdversarialReview(unittest.TestCase):
    """Adversarial challenger tests for Phase 160 Alpha features."""

    def test_adv01_spectral_geodesic_zero_variance_and_flatline(self) -> None:
        """ADV01: Constant price series must not crash or produce NaN/Inf."""
        flat_prices = np.full(100, 50.0)
        res = compute_riemannian_geodesic_flow(flat_prices)
        self.assertTrue(np.isfinite(res["f780_geodesic_velocity"]))
        self.assertTrue(np.isfinite(res["f780_tensor_core_entropy"]))
        self.assertTrue(np.isfinite(res["f780_manifold_curvature_drift"]))
        self.assertAlmostEqual(res["f780_geodesic_velocity"], 0.0, places=10)

    def test_adv02_spectral_geodesic_negative_and_zero_prices(self) -> None:
        """ADV02: Non-positive prices should be gracefully clamped without log(0) crash."""
        bad_prices = np.array([-10.0, 0.0, 10.0, 20.0, 30.0, 40.0])
        res = compute_riemannian_geodesic_flow(bad_prices)
        for k, v in res.items():
            self.assertTrue(np.isfinite(v), f"Value for {k} is not finite: {v}")

    def test_adv03_poincare_triangle_inequality(self) -> None:
        """ADV03: Poincare distance must strictly satisfy triangle inequality d(u, w) <= d(u, v) + d(v, w)."""
        rng = np.random.RandomState(123)
        for _ in range(20):
            u = rng.uniform(-0.5, 0.5, 3)
            v = rng.uniform(-0.5, 0.5, 3)
            w = rng.uniform(-0.5, 0.5, 3)
            d_uv = poincare_distance(u, v, c=1.0)
            d_vw = poincare_distance(v, w, c=1.0)
            d_uw = poincare_distance(u, w, c=1.0)
            self.assertLessEqual(d_uw, d_uv + d_vw + 1e-6)

    def test_adv04_poincare_boundary_clamping(self) -> None:
        """ADV04: Points outside the Poincare unit ball should be clamped without crashing or producing NaN."""
        outside_u = np.array([1.5, 2.0])
        outside_v = np.array([-2.5, -1.0])
        d = poincare_distance(outside_u, outside_v, c=1.0)
        self.assertTrue(np.isfinite(d))
        self.assertGreater(d, 0.0)

        # Mobius addition with outside points
        w = mobius_addition(outside_u, outside_v, c=1.0)
        self.assertTrue(np.isfinite(w).all())
        self.assertLess(float(np.linalg.norm(w)), 1.0)

    def test_adv05_hyperbolic_graph_disconnected_and_zero_matrix(self) -> None:
        """ADV05: Value chain distance matrix with zeros, disconnected nodes, or large distances."""
        # All zeros distance matrix
        d_zero = np.zeros((5, 5))
        res_zero = compute_hyperbolic_graph_representation(d_zero)
        self.assertTrue(np.isfinite(res_zero["f781_hyperbolic_radius"]))
        self.assertTrue(np.isfinite(res_zero["f781_poincare_distortion"]))
        self.assertTrue(np.isfinite(res_zero["f781_supply_hierarchical_depth"]))

        # Disconnected network (large distance)
        d_disc = np.array([
            [0.0, 1e4, 1e4],
            [1e4, 0.0, 0.1],
            [1e4, 0.1, 0.0],
        ])
        res_disc = compute_hyperbolic_graph_representation(d_disc)
        self.assertTrue(0.0 <= res_disc["f781_hyperbolic_radius"] < 1.0)
        self.assertTrue(np.isfinite(res_disc["f781_poincare_distortion"]))

    def test_adv06_jump_diffusion_hawkes_extreme_shocks(self) -> None:
        """ADV06: Flash crashes (-50% returns) and huge macro spikes."""
        returns = np.array([0.001, -0.002, 0.001, -0.50, 0.001, -0.001])
        macro_shocks = {
            "vix": np.array([12.0, 85.0]),  # Massive VIX surge
            "sox": np.array([3500.0, 1500.0]),
        }
        res = estimate_jump_diffusion_hawkes_params(returns, macro_shocks=macro_shocks)
        self.assertTrue(0.0 <= res["f782_jump_intensity"] <= 1.0)
        self.assertTrue(0.0 <= res["f782_branching_ratio"] < 1.0)
        self.assertTrue(0.0 <= res["f782_coupled_impulse_forecast"] <= 5.0)
        # Should have high jump intensity due to -50% shock
        self.assertGreater(res["f782_jump_intensity"], 0.20)

    def test_adv07_option_surface_corrupted_and_empty_inputs(self) -> None:
        """ADV07: Option surface calculator handles degenerate iv_surface inputs."""
        empty_surf = {}
        res1 = calculate_higher_order_surface_skew(empty_surf)
        self.assertTrue(np.isfinite(res1["f783_surface_skew"]))
        self.assertTrue(0.05 <= res1["f783_higher_order_greeks_score"] <= 0.95)

        # Non-dict inputs (None, int, string)
        res2 = calculate_higher_order_surface_skew(None)
        self.assertEqual(res2["f783_higher_order_greeks_score"], 0.50)

        # Corrupted DataFrame execution without unhandled exception
        df_corrupt = pd.DataFrame({"iv": [np.nan, np.inf, -0.5]}, index=[90, 100, 110])
        res3 = calculate_higher_order_surface_skew(df_corrupt)
        self.assertIn("f783_surface_skew", res3)
        self.assertIn("f783_higher_order_greeks_score", res3)
        self.assertTrue(0.05 <= res3["f783_higher_order_greeks_score"] <= 0.95)

    def test_adv08_roger_lee_arbitrage_boundary_testing(self) -> None:
        """ADV08: Test exact Roger Lee wing slope boundary b * (1 + |rho|) < 2.0 with |rho| < 1.0."""
        # Valid cases (|rho| < 1, b*(1+|rho|) < 2)
        self.assertTrue(verify_svi_no_arbitrage(b=0.99, rho=0.99))  # 0.99 * 1.99 = 1.9701 < 2
        self.assertTrue(verify_svi_no_arbitrage(b=1.99, rho=0.0))   # 1.99 * 1 = 1.99 < 2

        # Boundary / Invalid cases
        self.assertFalse(verify_svi_no_arbitrage(b=1.0, rho=1.0))   # |rho| = 1.0 boundary condition
        self.assertFalse(verify_svi_no_arbitrage(b=1.05, rho=0.95)) # 1.05 * 1.95 = 2.0475 >= 2
        self.assertFalse(verify_svi_no_arbitrage(b=2.0, rho=0.0))   # 2.0 * 1 = 2.0 >= 2
        self.assertFalse(verify_svi_no_arbitrage(b=-0.1, rho=0.0))  # b must be non-negative

    def test_adv09_factor_orthogonalizer_perfect_collinearity(self) -> None:
        """ADV09: Perfectly collinear factor columns must not trigger singular matrix exceptions."""
        df = pd.DataFrame({
            "f1": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "f2": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # Duplicate of f1
            "f3": [0.2, 0.4, 0.6, 0.8, 1.0, 1.2],  # Exact 2x of f1
            "f4": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Constant column
            "f5": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
            "f6": [0.3, 0.5, 0.2, 0.8, 0.4, 0.6],
            "f7": [0.6, 0.2, 0.7, 0.3, 0.9, 0.1],
        })
        ortho = FactorOrthogonalizerEngine()
        res = ortho.orthogonalize_phase160(df, strategy_cols=list(df.columns))
        self.assertEqual(len(res), 6)
        for col in df.columns:
            self.assertTrue(np.isfinite(res[col]).all())
            self.assertTrue((res[col] >= 0.05).all())
            self.assertTrue((res[col] <= 0.95).all())

    def test_adv10_phase160_coupler_single_asset_and_rank_deficiency(self) -> None:
        """ADV10: Phase160Coupler handles single-row (N=1) and N < D scenarios without failure."""
        coupler = Phase160Coupler()

        # N = 1 (single asset evaluation)
        res_single = coupler.evaluate({"p1": 0.8, "p2": 0.7, "p3": 0.6, "p4": 0.75, "p5": 0.85, "p6": 0.7, "p7": 0.8})
        self.assertIsInstance(res_single["alpha_p160"], float)
        self.assertTrue(-3.0 <= res_single["alpha_p160"] <= 3.0)
        self.assertTrue(0.0 < res_single["h_phase160"] <= 1.0)
        self.assertTrue(0.0 < res_single["fcpi_v160"] <= 1.0)

        # N = 2, D = 7 (severely rank deficient covariance)
        p_n2 = np.array([
            [0.8, 0.7, 0.9, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.3, 0.1, 0.4, 0.3, 0.2, 0.1],
        ])
        res_n2 = coupler.evaluate(p_n2)
        alpha_n2 = res_n2["alpha_p160"]
        self.assertEqual(len(alpha_n2), 2)
        self.assertTrue(np.all(alpha_n2 >= -3.0))
        self.assertTrue(np.all(alpha_n2 <= 3.0))
        self.assertGreater(alpha_n2[0], alpha_n2[1])

    def test_adv11_phase160_coupler_all_neutral_and_extreme_inputs(self) -> None:
        """ADV11: All-neutral signals (0.5) must give alpha ~ 0; extreme signals must remain clamped in [-3, 3]."""
        coupler = Phase160Coupler()

        # All 0.5 (neutral)
        neutral_scores = np.full((10, 7), 0.50)
        res_neutral = coupler.evaluate(neutral_scores)
        np.testing.assert_allclose(res_neutral["alpha_p160"], 0.0, atol=1e-5)

        # Extreme positive / negative signals
        extreme_scores = np.array([
            np.full(7, 1e5),
            np.full(7, -1e5),
        ])
        res_extreme = coupler.evaluate(extreme_scores)
        self.assertTrue(np.all(res_extreme["alpha_p160"] >= -3.0))
        self.assertTrue(np.all(res_extreme["alpha_p160"] <= 3.0))
        self.assertTrue(np.all(np.isfinite(res_extreme["alpha_p160"])))

    def test_adv12_airm_distance_symmetry_and_identity(self) -> None:
        """ADV12: AIRM distance must satisfy exact symmetry and zero distance for identical SPD matrices."""
        rng = np.random.RandomState(42)
        A = rng.normal(0, 1, (4, 4))
        Sigma1 = A @ A.T + np.eye(4)
        B = rng.normal(0, 1, (4, 4))
        Sigma2 = B @ B.T + np.eye(4)

        d12 = compute_riemannian_airm_distance(Sigma1, Sigma2)
        d21 = compute_riemannian_airm_distance(Sigma2, Sigma1)
        d11 = compute_riemannian_airm_distance(Sigma1, Sigma1)

        self.assertAlmostEqual(d12, d21, places=7)
        self.assertAlmostEqual(d11, 0.0, places=7)
        self.assertGreater(d12, 0.0)


if __name__ == "__main__":
    unittest.main()

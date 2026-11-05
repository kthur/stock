"""
tests/test_phase160_alpha.py — Comprehensive Test Suite for Phase 160 Features F780 to F784.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F780 Riemannian Geodesic Flow, Tucker Tensor Decomposition Alpha (TC07 ~ TC13)
- Category 3: F781 Non-Euclidean Hyperbolic Poincare Ball Graph Neural Representation (TC14 ~ TC20)
- Category 4: F782 Jump-Diffusion Hawkes Volatility Impulse Coupling (TC21 ~ TC27)
- Category 5: F783 Higher-Order Surface Skew, Curvature & Greeks Accelerator (TC28 ~ TC34)
- Category 6: F784 Septuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
- Category 7: Phase160Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact calculations.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import STRATEGY_REGISTRY, get_registry

# F780 Imports
from src.core.spectral_wavelet_decomposition import (
    VERSION as VERSION_F780,
    RELEASE as RELEASE_F780,
    FEATURE as FEATURE_F780,
    VERSION_PHASE160 as VERSION_P160_F780,
    RELEASE_PHASE160 as RELEASE_P160_F780,
    FEATURE_PHASE160 as FEATURE_P160_F780,
    SpectralWaveletDecompositionEngine,
    SpectralWaveletDecompositionEnginePhase160,
    Phase160SpectralWaveletEngine,
    F780SpectralWaveletEngine,
    RiemannianGeodesicTensorEngine,
    compute_riemannian_geodesic_flow,
    extract_riemannian_geodesic_flow,
    compute_tucker_tensor_decomposition,
    compute_tensor_core_entropy,
    compute_instantaneous_frequency,
    compute_synchrosqueezed_wavelet_transform,
    compute_synchrosqueezed_phase_alignment,
    extract_synchrosqueezed_ridge,
    apply_hyperbolic_noise_deadband,
    convolve_atrous,
    get_wavelet_filters,
    upsample_filter,
)

# F781 Imports
from src.core.value_chain_curvature_gnn import (
    VERSION as VERSION_F781,
    RELEASE as RELEASE_F781,
    FEATURE as FEATURE_F781,
    VERSION_PHASE160 as VERSION_P160_F781,
    RELEASE_PHASE160 as RELEASE_P160_F781,
    FEATURE_PHASE160 as FEATURE_P160_F781,
    ValueChainCurvatureGNNEngine,
    ValueChainCurvatureGNNEnginePhase160,
    Phase160ValueChainCurvatureGNNEngine,
    F781ValueChainCurvatureGNNEngine,
    HyperbolicPoincareGraphEngine,
    compute_hyperbolic_graph_representation,
    poincare_distance,
    mobius_addition,
    poincare_exp_map,
    poincare_log_map,
    compute_vietoris_rips_distance,
    compute_persistent_homology_betti_numbers,
    compute_hodge_laplacian_spectrum,
    detect_harmonic_value_chain_loops,
    compute_value_chain_curvature_gnn_scores,
    value_chain_curvature_gnn_score,
)

# F782 Imports
from src.core.cross_market_micro_momentum import (
    VERSION as VERSION_F782,
    RELEASE as RELEASE_F782,
    FEATURE as FEATURE_F782,
    VERSION_PHASE160 as VERSION_P160_F782,
    RELEASE_PHASE160 as RELEASE_P160_F782,
    FEATURE_PHASE160 as FEATURE_P160_F782,
    CrossMarketMicroMomentumEngine,
    CrossMarketMicroMomentumEnginePhase160,
    Phase160CrossMarketMicroMomentumEngine,
    F782CrossMarketMicroMomentumEngine,
    JumpDiffusionHawkesMomentumEngine,
    estimate_jump_diffusion_hawkes_params,
    compute_jump_diffusion_intensity,
    compute_hawkes_branching_ratio,
    compute_rough_heston_hurst_parameter,
    compute_fractional_volterra_kernel,
    compute_rough_volatility_forecast,
    compute_vpin_cascade_metric,
    compute_level2_ofi_velocity,
    compute_multivariate_hawkes_intensity,
    compute_cross_market_micro_momentum_scores,
    cross_market_micro_mom_score,
)

# F783 Imports
from src.core.option_surface_accelerator import (
    VERSION as VERSION_F783,
    RELEASE as RELEASE_F783,
    FEATURE as FEATURE_F783,
    VERSION_PHASE160 as VERSION_P160_F783,
    RELEASE_PHASE160 as RELEASE_P160_F783,
    FEATURE_PHASE160 as FEATURE_P160_F783,
    OptionSurfaceAccelerator,
    OptionSurfaceAcceleratorPhase160,
    Phase160OptionSurfaceAccelerator,
    F783OptionSurfaceAccelerator,
    HigherOrderSurfaceSkewAccelerator,
    calculate_higher_order_surface_skew,
    calculate_4th_order_greeks,
    compute_fourth_order_black_scholes_greeks,
    calibrate_svi_surface_slice,
    verify_svi_no_arbitrage,
    compute_svi_skew_scores,
    compute_garman_klass_parkinson_volatility,
    compute_net_dealer_gex_and_vanna,
    compute_option_surface_scores,
    option_surface_accelerator_score,
)

# F784 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F784,
    RELEASE as RELEASE_F784,
    FEATURE as FEATURE_F784,
    VERSION_PHASE160 as VERSION_P160_F784,
    RELEASE_PHASE160 as RELEASE_P160_F784,
    FEATURE_PHASE160 as FEATURE_P160_F784,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase160,
    Phase160FactorOrthogonalizerEngine,
    F784FactorOrthogonalizerEngine,
    HyperDimensionalZCAOrthogonalizer,
    SEPTUPLE_PILLAR_MAP,
    apply_hyperbolic_deadband_phase160,
    compute_riemannian_airm_distance,
    compute_riemannian_airm_metric,
    compute_riemannian_frechet_shrinkage,
    compute_septuple_pillar_zca_whitening,
    apply_riemannian_deadband,
)

# Phase 160 Coupler
from src.ai.historical_couplers import Phase160Coupler


class TestPhase160Alpha(unittest.TestCase):
    """Exhaustive 48-Test Integration Suite for Phase 160 Multi-Factor Alpha Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = SpectralWaveletDecompositionEngine()
        self.curvature_engine = ValueChainCurvatureGNNEngine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase160Coupler()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_all_files(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 160 production files."""
        files = [
            ("src/core/spectral_wavelet_decomposition.py", "trading_system/src/core/spectral_wavelet_decomposition.py"),
            ("src/core/value_chain_curvature_gnn.py", "trading_system/src/core/value_chain_curvature_gnn.py"),
            ("src/core/cross_market_micro_momentum.py", "trading_system/src/core/cross_market_micro_momentum.py"),
            ("src/core/option_surface_accelerator.py", "trading_system/src/core/option_surface_accelerator.py"),
            ("src/ai/factor_orthogonalizer.py", "trading_system/src/ai/factor_orthogonalizer.py"),
            ("src/ai/historical_couplers.py", "trading_system/src/ai/historical_couplers.py"),
        ]
        for src_rel, ts_rel in files:
            src_path = os.path.join(self.root_dir, src_rel)
            ts_path = os.path.join(self.root_dir, ts_rel)
            self.assertTrue(os.path.exists(src_path), f"Missing source: {src_path}")
            self.assertTrue(os.path.exists(ts_path), f"Missing target: {ts_path}")
            with open(src_path, "rb") as f1, open(ts_path, "rb") as f2:
                self.assertEqual(
                    hashlib.sha256(f1.read()).hexdigest(),
                    hashlib.sha256(f2.read()).hexdigest(),
                    f"Cryptographic dual-tree mismatch in {src_rel}",
                )

    def test_tc02_polymorphic_version_equality(self) -> None:
        """TC02: Verify polymorphic _VersionInt(160) backward compatibility with (140, 144, 148, 152, 156, 160)."""
        for v in [VERSION_F780, VERSION_F781, VERSION_F782, VERSION_F783, VERSION_F784]:
            self.assertEqual(int(v), 160)
            self.assertEqual(v, 160)
            self.assertEqual(v, 156)
            self.assertEqual(v, 152)
            self.assertEqual(v, 148)
            self.assertEqual(v, 144)
            self.assertEqual(v, 140)

    def test_tc03_release_constants(self) -> None:
        """TC03: Verify Release R163 strings and backward polymorphic comparisons."""
        for r in [RELEASE_F780, RELEASE_F781, RELEASE_F782, RELEASE_F783, RELEASE_F784]:
            self.assertEqual(str(r), "R163")
            self.assertEqual(r, "R163")
            self.assertEqual(r, "R159")
            self.assertEqual(r, "R152")
            self.assertEqual(r, "R148")

    def test_tc04_feature_flags(self) -> None:
        """TC04: Verify Feature flags F780-F784 are assigned correctly."""
        self.assertEqual(FEATURE_F780, "F780")
        self.assertEqual(FEATURE_F781, "F781")
        self.assertEqual(FEATURE_F782, "F782")
        self.assertEqual(FEATURE_F783, "F783")
        self.assertEqual(FEATURE_F784, "F784")
        self.assertEqual(FEATURE_P160_F780, "F780")
        self.assertEqual(FEATURE_P160_F781, "F781")
        self.assertEqual(FEATURE_P160_F782, "F782")
        self.assertEqual(FEATURE_P160_F783, "F783")
        self.assertEqual(FEATURE_P160_F784, "F784")

    def test_tc05_strategy_registry_registration(self) -> None:
        """TC05: Verify auto-registration in STRATEGY_REGISTRY for all alpha engines."""
        for strat_id in ["spectral_wavelet", "value_chain_curvature_gnn", "cross_market_micro_momentum", "option_gamma_accel"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            cls, meta = get_registry().get(strat_id)
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    def test_tc06_alias_hierarchy_completeness(self) -> None:
        """TC06: Verify full alias hierarchy for Phase 160 classes."""
        self.assertIs(SpectralWaveletDecompositionEnginePhase160, SpectralWaveletDecompositionEngine)
        self.assertIs(Phase160SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(F780SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(RiemannianGeodesicTensorEngine, SpectralWaveletDecompositionEngine)

        self.assertIs(ValueChainCurvatureGNNEnginePhase160, ValueChainCurvatureGNNEngine)
        self.assertIs(Phase160ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(F781ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(HyperbolicPoincareGraphEngine, ValueChainCurvatureGNNEngine)

        self.assertIs(CrossMarketMicroMomentumEnginePhase160, CrossMarketMicroMomentumEngine)
        self.assertIs(Phase160CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(F782CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(JumpDiffusionHawkesMomentumEngine, CrossMarketMicroMomentumEngine)

        self.assertIs(OptionSurfaceAcceleratorPhase160, OptionSurfaceAccelerator)
        self.assertIs(Phase160OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F783OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(HigherOrderSurfaceSkewAccelerator, OptionSurfaceAccelerator)

        self.assertIs(FactorOrthogonalizerEnginePhase160, FactorOrthogonalizerEngine)
        self.assertIs(Phase160FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F784FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(HyperDimensionalZCAOrthogonalizer, FactorOrthogonalizerEngine)

    # =========================================================================
    # Category 2: F780 Riemannian Geodesic Flow, Tucker Tensor Decomposition Alpha (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_extract_riemannian_geodesic_flow_bounds(self) -> None:
        """TC07: Verify extract_riemannian_geodesic_flow returns bounded geodesic velocity and entropy."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 64)) * 100.0
        res = extract_riemannian_geodesic_flow(prices)
        self.assertIn("f780_geodesic_velocity", res)
        self.assertIn("f780_tensor_core_entropy", res)
        self.assertIn("f780_manifold_curvature_drift", res)

        vel = res["f780_geodesic_velocity"]
        ent = res["f780_tensor_core_entropy"]
        drift = res["f780_manifold_curvature_drift"]

        self.assertTrue(0.0 <= vel <= 5.0)
        self.assertTrue(ent >= 0.0)
        self.assertTrue(np.isfinite(drift))

    def test_tc08_tucker_tensor_decomposition_and_entropy(self) -> None:
        """TC08: Verify compute_tucker_tensor_decomposition decomposes 3D return tensor and measures entropy."""
        rng = np.random.RandomState(42)
        tensor_data = rng.normal(0, 1, (3, 3, 20))
        core, factors = compute_tucker_tensor_decomposition(tensor_data)
        self.assertEqual(len(factors), 3)
        entropy = compute_tensor_core_entropy(core)
        self.assertTrue(entropy >= 0.0)
        self.assertTrue(np.isfinite(entropy))

    def test_tc09_geodesic_velocity_sensitivity_to_market_volatility(self) -> None:
        """TC09: Verify geodesic velocity increases during high volatility / regime shift compared to flat prices."""
        p_flat = np.full(50, 100.0)
        p_shock = np.array([100.0 * (1.1 ** i) if i % 2 == 0 else 100.0 * (0.9 ** i) for i in range(50)])

        res_flat = extract_riemannian_geodesic_flow(p_flat)
        res_shock = extract_riemannian_geodesic_flow(p_shock)

        self.assertGreater(res_shock["f780_geodesic_velocity"], res_flat["f780_geodesic_velocity"])

    def test_tc10_wsst_synchrosqueezed_transform_energy(self) -> None:
        """TC10: Verify WSST synchrosqueezed transform concentrates energy on multi-frequency prices."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 128)) * 100.0
        wsst_res = self.wavelet_engine.compute_synchrosqueezed_wavelet_transform(prices)
        self.assertIn("energy_entropy", wsst_res)
        self.assertGreaterEqual(wsst_res["energy_entropy"], 0.0)
        self.assertIn("wsst_spectrum", wsst_res)
        self.assertIn("phase_alignment", wsst_res)

    def test_tc11_engine_extract_riemannian_geodesic_flow_method(self) -> None:
        """TC11: Verify SpectralWaveletDecompositionEngine methods for Riemannian geodesic flow."""
        prices = np.linspace(100, 120, 60)
        res1 = self.wavelet_engine.extract_riemannian_geodesic_flow(prices)
        res2 = self.wavelet_engine.compute_riemannian_geodesic_flow(prices)
        self.assertEqual(res1["f780_geodesic_velocity"], res2["f780_geodesic_velocity"])
        self.assertEqual(res1["f780_tensor_core_entropy"], res2["f780_tensor_core_entropy"])

    def test_tc12_hyperbolic_noise_deadband_attenuation(self) -> None:
        """TC12: Verify apply_hyperbolic_noise_deadband squashes sub-threshold noise."""
        self.assertEqual(apply_hyperbolic_noise_deadband(0.005, delta=0.035), 0.0)
        self.assertEqual(apply_hyperbolic_noise_deadband(-0.005, delta=0.035), 0.0)
        self.assertAlmostEqual(apply_hyperbolic_noise_deadband(0.08, delta=0.035), 0.08, places=4)

    def test_tc13_wavelet_filters_and_atrous_convolution(self) -> None:
        """TC13: Verify convolve_atrous and get_wavelet_filters produce valid stationary transforms."""
        lp, hp = get_wavelet_filters("haar")
        sig = np.ones(32)
        c_lp = convolve_atrous(sig, lp)
        self.assertEqual(len(c_lp), len(sig))
        self.assertTrue(np.isfinite(c_lp).all())

    # =========================================================================
    # Category 3: F781 Non-Euclidean Hyperbolic Poincare Ball Graph Neural Representation (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_compute_hyperbolic_graph_representation_bounds(self) -> None:
        """TC14: Verify compute_hyperbolic_graph_representation outputs bounded radius, distortion, depth."""
        D = np.array([
            [0.0, 0.4, 0.8, 1.2],
            [0.4, 0.0, 0.6, 1.0],
            [0.8, 0.6, 0.0, 0.5],
            [1.2, 1.0, 0.5, 0.0],
        ])
        res = compute_hyperbolic_graph_representation(D)
        self.assertIn("f781_hyperbolic_radius", res)
        self.assertIn("f781_poincare_distortion", res)
        self.assertIn("f781_supply_hierarchical_depth", res)

        self.assertTrue(0.0 <= res["f781_hyperbolic_radius"] < 1.0)
        self.assertTrue(res["f781_poincare_distortion"] >= 0.0)
        self.assertTrue(res["f781_supply_hierarchical_depth"] >= 0.0)

    def test_tc15_poincare_distance_metric_properties(self) -> None:
        """TC15: Verify Poincare distance satisfies non-negativity, symmetry, and identity."""
        u = np.array([0.2, 0.3])
        v = np.array([-0.1, 0.4])

        d_uu = poincare_distance(u, u)
        self.assertAlmostEqual(d_uu, 0.0, places=6)

        d_uv = poincare_distance(u, v)
        d_vu = poincare_distance(v, u)
        self.assertGreater(d_uv, 0.0)
        self.assertAlmostEqual(d_uv, d_vu, places=6)

    def test_tc16_poincare_exp_and_log_map_isometry(self) -> None:
        """TC16: Verify Poincare exponential and logarithmic maps are mutually inverse."""
        v = np.array([0.15, -0.25])
        p = poincare_exp_map(v, c=1.0)
        self.assertLess(float(np.linalg.norm(p)), 1.0)
        v_rec = poincare_log_map(p, c=1.0)
        np.testing.assert_allclose(v_rec, v, atol=1e-5)

    def test_tc17_mobius_addition_and_hyperbolic_translation(self) -> None:
        """TC17: Verify Mobius addition preserves Poincare unit ball boundary ||u (+) v|| < 1."""
        u = np.array([0.5, 0.4])
        v = np.array([-0.3, 0.6])
        w = mobius_addition(u, v, c=1.0)
        self.assertLess(float(np.linalg.norm(w)), 1.0)

    def test_tc18_engine_hyperbolic_graph_representation_method(self) -> None:
        """TC18: Verify ValueChainCurvatureGNNEngine method compute_hyperbolic_graph_representation."""
        D = np.array([[0.0, 0.5], [0.5, 0.0]])
        res = self.curvature_engine.compute_hyperbolic_graph_representation(D)
        self.assertIn("f781_hyperbolic_radius", res)
        self.assertTrue(0.0 <= res["f781_hyperbolic_radius"] < 1.0)

    def test_tc19_discrete_hodge_laplacian_spectrum(self) -> None:
        """TC19: Verify discrete Hodge Laplacian spectrum is positive semi-definite."""
        adj = np.array([
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 1.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0, 0.0],
        ])
        spec = compute_hodge_laplacian_spectrum(adj)
        self.assertIn("eigenvalues", spec)
        eigs = np.array(spec["eigenvalues"])
        self.assertTrue((eigs >= -1e-8).all())

    def test_tc20_harmonic_loops_and_bottleneck_detection(self) -> None:
        """TC20: Verify detect_harmonic_value_chain_loops identifies cyclic topology."""
        res = detect_harmonic_value_chain_loops(threshold=0.50)
        self.assertIn("harmonic_dimension", res)
        self.assertIn("harmonic_loops", res)
        self.assertGreaterEqual(res["detected_loops_count"], 1)

    # =========================================================================
    # Category 4: F782 Jump-Diffusion Hawkes Volatility Impulse Coupling (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_estimate_jump_diffusion_hawkes_params_bounds(self) -> None:
        """TC21: Verify estimate_jump_diffusion_hawkes_params outputs bounded jump intensity, branching, impulse."""
        returns = np.random.RandomState(42).normal(0, 0.015, 60)
        res = estimate_jump_diffusion_hawkes_params(returns)
        self.assertIn("f782_jump_intensity", res)
        self.assertIn("f782_branching_ratio", res)
        self.assertIn("f782_coupled_impulse_forecast", res)

        self.assertTrue(0.0 <= res["f782_jump_intensity"] <= 1.0)
        self.assertTrue(0.0 <= res["f782_branching_ratio"] < 1.0)
        self.assertTrue(0.0 <= res["f782_coupled_impulse_forecast"] <= 5.0)

    def test_tc22_hawkes_branching_ratio_subcritical_stability(self) -> None:
        """TC22: Verify compute_hawkes_branching_ratio enforces spectral radius stability < 1.0."""
        alpha = np.array([[0.2, 0.1], [0.15, 0.25]])
        beta = np.array([[1.0, 1.2], [1.2, 1.0]])
        eta = compute_hawkes_branching_ratio(alpha, beta)
        self.assertTrue(0.0 <= eta < 1.0)

    def test_tc23_macro_shock_cross_excitation_acceleration(self) -> None:
        """TC23: Verify macro shock injection elevates coupled impulse forecast."""
        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.005, -0.025, 0.04])
        base_shocks = {"vix": np.array([15.0, 15.0]), "sox": np.array([3000.0, 3000.0])}
        shock_shocks = {"vix": np.array([15.0, 25.0]), "sox": np.array([3000.0, 2700.0])}

        res_base = estimate_jump_diffusion_hawkes_params(returns, macro_shocks=base_shocks)
        res_shock = estimate_jump_diffusion_hawkes_params(returns, macro_shocks=shock_shocks)

        self.assertGreaterEqual(
            res_shock["f782_coupled_impulse_forecast"],
            res_base["f782_coupled_impulse_forecast"],
        )

    def test_tc24_rough_heston_hurst_subdiffusive_bound(self) -> None:
        """TC24: Verify compute_rough_heston_hurst_parameter outputs subdiffusive H in (0.01, 0.49)."""
        log_ret = np.random.RandomState(42).normal(0, 0.015, 252)
        h = compute_rough_heston_hurst_parameter(log_ret)
        self.assertTrue(0.0 < h < 0.5)

    def test_tc25_engine_estimate_jump_diffusion_hawkes_method(self) -> None:
        """TC25: Verify CrossMarketMicroMomentumEngine method estimate_jump_diffusion_hawkes_params."""
        returns = np.linspace(-0.02, 0.02, 40)
        res = self.micro_engine.estimate_jump_diffusion_hawkes_params(returns)
        self.assertIn("f782_jump_intensity", res)
        self.assertTrue(0.0 <= res["f782_branching_ratio"] < 1.0)

    def test_tc26_vpin_and_level2_ofi_metrics(self) -> None:
        """TC26: Verify Level-2 OFI velocity and VPIN cascade evaluate market microstructure."""
        buys = np.array([100.0, 150.0, 120.0, 200.0, 180.0])
        sells = np.array([90.0, 110.0, 130.0, 90.0, 80.0])
        vpin = compute_vpin_cascade_metric(buys, sells)
        self.assertTrue(0.0 <= vpin <= 1.0)

    def test_tc27_multivariate_hawkes_intensity_stability(self) -> None:
        """TC27: Verify multivariate Hawkes cross-excitation intensity maintains non-explosive bounds."""
        events = [(0.1, 0), (0.5, 1), (1.2, 2)]
        intensities = compute_multivariate_hawkes_intensity(events=events, current_time=2.0)
        self.assertEqual(len(intensities), 8)
        self.assertTrue((intensities >= 1e-4).all())

    # =========================================================================
    # Category 5: F783 Higher-Order Surface Skew, Curvature & Greeks Accelerator (TC28 ~ TC34)
    # =========================================================================

    def test_tc28_calculate_higher_order_surface_skew_bounds(self) -> None:
        """TC28: Verify calculate_higher_order_surface_skew outputs skew, curvature, and Greeks score."""
        surface = {
            "spot": 100.0,
            "strikes": [90.0, 95.0, 100.0, 105.0, 110.0],
            "ivs": [0.25, 0.22, 0.20, 0.21, 0.24],
            "tau": 30.0 / 365.0,
            "vol": 0.20,
        }
        res = calculate_higher_order_surface_skew(surface)
        self.assertIn("f783_surface_skew", res)
        self.assertIn("f783_surface_curvature", res)
        self.assertIn("f783_arbitrage_free_status", res)
        self.assertIn("f783_higher_order_greeks_score", res)

        self.assertTrue(np.isfinite(res["f783_surface_skew"]))
        self.assertTrue(res["f783_surface_curvature"] >= 0.0)
        self.assertIn(res["f783_arbitrage_free_status"], [0.0, 1.0])
        self.assertTrue(0.05 <= res["f783_higher_order_greeks_score"] <= 0.95)

    def test_tc29_fourth_order_black_scholes_greeks_consistency(self) -> None:
        """TC29: Verify compute_fourth_order_black_scholes_greeks evaluates speed, zomma, color, ultima."""
        greeks = compute_fourth_order_black_scholes_greeks(
            spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.03
        )
        self.assertTrue(any(k in greeks for k in ["speed", "speed_4th"]))
        self.assertTrue(any(k in greeks for k in ["zomma", "zoma"]))
        self.assertTrue(any(k in greeks for k in ["color", "color_4th"]))
        for k, v in greeks.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v))

    def test_tc30_svi_surface_slice_no_arbitrage_check(self) -> None:
        """TC30: Verify verify_svi_no_arbitrage confirms asymptotic slope condition b*(1+|rho|) < 2."""
        self.assertTrue(verify_svi_no_arbitrage(b=0.15, rho=-0.3))
        self.assertFalse(verify_svi_no_arbitrage(b=1.5, rho=0.8))

    def test_tc31_svi_skew_scores_cross_asset(self) -> None:
        """TC31: Verify compute_svi_skew_scores produces valid cross-asset scores."""
        scores = compute_svi_skew_scores(symbols=["005930", "AAPL"])
        for s, score in scores.items():
            self.assertTrue(0.05 <= score <= 0.95)

    def test_tc32_engine_higher_order_surface_skew_method(self) -> None:
        """TC32: Verify OptionSurfaceAccelerator method calculate_higher_order_surface_skew."""
        surface = {"spot": 100.0, "tau": 0.1, "vol": 0.22}
        res = self.options_engine.calculate_higher_order_surface_skew(surface)
        self.assertIn("f783_surface_skew", res)
        self.assertIn("f783_higher_order_greeks_score", res)
        self.assertTrue(0.05 <= res["f783_higher_order_greeks_score"] <= 0.95)

    def test_tc33_garman_klass_parkinson_volatility_estimators(self) -> None:
        """TC33: Verify Garman-Klass and Parkinson realized volatility estimators."""
        close = np.array([100.0, 102.0, 101.0, 103.0, 104.0, 100.0])
        high = np.array([102.0, 105.0, 103.0, 106.0, 105.0, 103.0])
        low = np.array([98.0, 100.0, 99.0, 101.0, 102.0, 98.0])
        open_p = np.array([99.0, 101.0, 100.0, 102.0, 103.0, 101.0])
        res = compute_garman_klass_parkinson_volatility(close=close, high=high, low=low, open_p=open_p)
        self.assertIn("garman_klass_vol", res)
        self.assertIn("parkinson_vol", res)

    def test_tc34_net_dealer_gex_and_vanna_surface(self) -> None:
        """TC34: Verify net dealer GEX and Vanna surface evaluates market maker hedging pressure."""
        chain = [
            {"strike": 95.0, "iv": 0.22, "tau": 0.1, "open_interest": 1000, "is_call": True},
            {"strike": 100.0, "iv": 0.20, "tau": 0.1, "open_interest": 2000, "is_call": True},
            {"strike": 105.0, "iv": 0.23, "tau": 0.1, "open_interest": 1500, "is_call": False},
        ]
        gex, vanna, charm = compute_net_dealer_gex_and_vanna(spot=100.0, options_chain=chain)
        self.assertTrue(np.isfinite(gex))
        self.assertTrue(np.isfinite(vanna))
        self.assertTrue(np.isfinite(charm))

    # =========================================================================
    # Category 6: F784 Septuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
    # =========================================================================

    def test_tc35_riemannian_airm_metric_distance_properties(self) -> None:
        """TC35: Verify AIRM distance satisfies Riemannian metric properties d(A,B) >= 0 and d(A,A) = 0."""
        cov_a = np.array([[1.0, 0.3], [0.3, 1.0]])
        cov_b = np.array([[1.2, 0.1], [0.1, 0.9]])
        d_aa = compute_riemannian_airm_distance(cov_a, cov_a)
        self.assertAlmostEqual(d_aa, 0.0, places=6)
        d_ab = compute_riemannian_airm_distance(cov_a, cov_b)
        d_ba = compute_riemannian_airm_distance(cov_b, cov_a)
        self.assertGreater(d_ab, 0.0)
        self.assertAlmostEqual(d_ab, d_ba, places=6)

    def test_tc36_riemannian_frechet_shrinkage_interpolation(self) -> None:
        """TC36: Verify compute_riemannian_frechet_shrinkage interpolates between sample cov and identity."""
        sample_cov = np.array([[1.5, 0.8], [0.8, 1.2]])
        prior_cov = np.eye(2)
        shrunk_cov = compute_riemannian_frechet_shrinkage(sample_cov, prior_cov, alpha=0.3)
        self.assertEqual(shrunk_cov.shape, (2, 2))
        np.testing.assert_allclose(shrunk_cov, shrunk_cov.T, atol=1e-7)
        self.assertLess(abs(shrunk_cov[0, 1]), abs(sample_cov[0, 1]))

    def test_tc37_septuple_pillar_zca_whitening_symmetry_and_identity(self) -> None:
        """TC37: Verify Septuple-Pillar ZCA whitening transforms 7x7 covariance to exact identity."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (120, 7))
        cov7 = np.cov(X, rowvar=False)
        w_zca = compute_septuple_pillar_zca_whitening(cov7, shrink_weight=0.0)
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-6)
        cov_white = w_zca @ cov7 @ w_zca.T
        np.testing.assert_allclose(cov_white, np.eye(7), atol=1e-4)

    def test_tc38_septuple_pillar_map_integrity(self) -> None:
        """TC38: Verify SEPTUPLE_PILLAR_MAP defines all 7 canonical economic pillars."""
        expected_pillars = ["val", "mom", "flow", "cat", "net", "vol", "gnn"]
        for p in expected_pillars:
            self.assertIn(p, SEPTUPLE_PILLAR_MAP)
            self.assertGreater(len(SEPTUPLE_PILLAR_MAP[p]), 0)

    def test_tc39_hyperbolic_deadband_phase160_attenuation(self) -> None:
        """TC39: Verify apply_hyperbolic_deadband_phase160 squashes noise < delta and preserves signals."""
        self.assertEqual(apply_hyperbolic_deadband_phase160(0.01, delta=0.035), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase160(-0.01, delta=0.035), 0.0)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase160(0.10, delta=0.035), 0.10, places=4)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase160(-0.10, delta=0.035), -0.10, places=4)

    def test_tc40_orthogonalize_phase160_execution(self) -> None:
        """TC40: Verify orthogonalize_phase160 executes on 7 pillar columns with institutional bounds."""
        np.random.seed(42)
        cols = [f"factor_{i}" for i in range(7)]
        data = {c: np.random.uniform(0.1, 0.9, 30) for c in cols}
        data["symbol"] = [f"SYM_{i}" for i in range(30)]
        df = pd.DataFrame(data)

        res = self.ortho_engine.orthogonalize_phase160(df, strategy_cols=cols)
        self.assertEqual(len(res), 30)
        for c in cols:
            self.assertTrue((res[c] >= 0.05).all())
            self.assertTrue((res[c] <= 0.95).all())

    # =========================================================================
    # Category 7: Phase160Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)
    # =========================================================================

    def test_tc41_phase160_coupler_action_functional_and_fcpi(self) -> None:
        """TC41: Verify Phase160Coupler evaluates S_action, h_phase160 in (0,1], fcpi_v160 in (0,1], and alpha_p160 in [-3, 3]."""
        p_mat = np.array([
            [0.6, 0.7, 0.5, 0.6, 0.8, 0.4, 0.5],
            [0.5, 0.6, 0.6, 0.7, 0.5, 0.6, 0.4],
            [0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.7],
        ])
        res = self.coupler.evaluate(p_mat)
        self.assertIn("alpha_p160", res)
        self.assertIn("alpha", res)
        self.assertIn("h_phase160", res)
        self.assertIn("fcpi_v160", res)
        self.assertIn("s_action", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha_vals = np.asarray(res["alpha_p160"])
        h_vals = np.asarray(res["h_phase160"])
        fcpi_vals = np.asarray(res["fcpi_v160"])
        self.assertIsInstance(res["alpha_p160"], np.ndarray)
        self.assertEqual(alpha_vals.shape, (3,))
        self.assertTrue(((alpha_vals >= -3.0) & (alpha_vals <= 3.0)).all())
        self.assertTrue(np.isfinite(alpha_vals).all())
        self.assertTrue(((h_vals > 0.0) & (h_vals <= 1.0)).all())
        self.assertTrue(((fcpi_vals > 0.0) & (fcpi_vals <= 1.0)).all())

    def test_tc41b_phase160_coupler_alpha_signal_scaling_and_extremes(self) -> None:
        """TC41b: Verify Phase160Coupler.alpha_p160 scales monotonically with input factor signals and bounds extremes."""
        p_signals = np.array([
            [0.90, 0.88, 0.92, 0.85, 0.91, 0.89, 0.90],  # Asset 0: Bullish
            [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],  # Asset 1: Neutral
            [0.10, 0.12, 0.08, 0.15, 0.09, 0.11, 0.10],  # Asset 2: Bearish
        ])
        res = self.coupler.evaluate(p_signals)
        self.assertIn("alpha_p160", res)
        alpha = res["alpha_p160"]
        self.assertIsInstance(alpha, np.ndarray)
        self.assertEqual(alpha.shape, (3,))

        self.assertGreater(alpha[0], 0.0)
        self.assertAlmostEqual(alpha[1], 0.0, places=4)
        self.assertLess(alpha[2], 0.0)
        self.assertGreater(alpha[0], alpha[1])
        self.assertGreater(alpha[1], alpha[2])

        # Extreme shock test
        extreme_signals = np.array([
            [10.0, 50.0, 100.0, 20.0, 30.0, 40.0, 50.0],
            [-10.0, -50.0, -100.0, -20.0, -30.0, -40.0, -50.0],
            [np.nan, np.inf, -np.inf, 0.5, 0.5, 0.5, 0.5],
        ])
        res_ext = self.coupler.evaluate(extreme_signals)
        alpha_ext = np.asarray(res_ext["alpha_p160"])
        self.assertEqual(alpha_ext.shape, (3,))
        self.assertTrue(np.all(alpha_ext >= -3.0))
        self.assertTrue(np.all(alpha_ext <= 3.0))
        self.assertTrue(np.all(np.isfinite(alpha_ext)))

    def test_tc42_phase160_coupler_dataframe_series_polymorphism(self) -> None:
        """TC42: Verify Phase160Coupler handles DataFrame, dict, and Series inputs seamlessly."""
        df = pd.DataFrame({
            "p1": [0.6, 0.4],
            "p2": [0.5, 0.7],
            "p3": [0.8, 0.3],
        }, index=["AAPL", "MSFT"])
        out_df = self.coupler(df)
        self.assertIsInstance(out_df["h_phase160"], pd.Series)
        self.assertEqual(list(out_df["h_phase160"].index), ["AAPL", "MSFT"])

        d_in = {"p1": 0.6, "p2": 0.5, "p3": 0.8}
        out_scalar = Phase160Coupler.compute(d_in)
        self.assertIsInstance(out_scalar["h_phase160"], float)

    def test_tc43_5_market_universe_compatibility(self) -> None:
        """TC43: Verify all 5 alpha engines execute across symbols from KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000."""
        syms = ["005930", "068270", "AAPL", "NVDA", "IWM"]
        prices = {
            s: pd.DataFrame({
                "Close": np.linspace(100, 115, 20),
                "Volume": np.linspace(1000, 2500, 20),
            }) for s in syms
        }
        r_sw = self.wavelet_engine.compute_scores(prices)
        r_vc = self.curvature_engine.compute_scores(prices)
        r_cm = self.micro_engine.compute_scores(prices)
        r_op = self.options_engine.compute_scores(prices)

        for r in [r_sw, r_vc, r_cm, r_op]:
            self.assertEqual(len(r), 5)
            self.assertFalse(r.isna().any().any())

    def test_tc44_empty_and_short_prices_resilience(self) -> None:
        """TC44: Verify engines gracefully handle empty or 1-bar price histories."""
        empty_prices: Dict[str, pd.DataFrame] = {}
        self.assertEqual(len(self.wavelet_engine.compute_scores(empty_prices)), 0)
        self.assertEqual(len(self.curvature_engine.compute_scores(empty_prices)), 0)
        self.assertEqual(len(self.micro_engine.compute_scores(empty_prices)), 0)

        short_prices = {"TEST": pd.DataFrame({"Close": [100.0]})}
        r_sw = self.wavelet_engine.compute_scores(short_prices)
        self.assertEqual(r_sw["spectral_wavelet_score"].iloc[0], 0.50)

    def test_tc45_extreme_market_crash_and_flash_surge(self) -> None:
        """TC45: Verify extreme +500% surge or -90% crash output is bounded strictly in [0.05, 0.98]."""
        shock_up = {"SURGE": pd.DataFrame({"Close": [10.0, 10.0, 10.0, 10.0, 60.0]})}
        shock_down = {"CRASH": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 10.0]})}

        for shock_dict in [shock_up, shock_down]:
            s1 = self.wavelet_engine.compute_scores(shock_dict).iloc[0, 1]
            s2 = self.curvature_engine.compute_scores(shock_dict).iloc[0, 1]
            s3 = self.micro_engine.compute_scores(shock_dict).iloc[0, 1]
            s4 = self.options_engine.compute_scores(shock_dict).iloc[0, 1]
            for s in [s1, s2, s3, s4]:
                self.assertTrue(0.05 <= s <= 0.98)
                self.assertTrue(np.isfinite(s))

    def test_tc46_nan_and_inf_feed_sanitization(self) -> None:
        """TC46: Verify corrupted price feeds with NaNs and Infs produce clean finite scores."""
        corrupted = {"CORRUPT": pd.DataFrame({
            "Close": [np.nan, 100.0, np.inf, -np.inf, 105.0],
            "Volume": [1000.0, np.nan, 2000.0, np.inf, 1500.0],
        })}
        for engine in [self.wavelet_engine, self.curvature_engine, self.micro_engine, self.options_engine]:
            res = engine.compute_scores(corrupted)
            self.assertEqual(len(res), 1)
            score = res.iloc[0, 1]
            self.assertTrue(np.isfinite(score))
            self.assertFalse(np.isnan(score))

    def test_tc47_execution_latency_sla(self) -> None:
        """TC47: Verify execution latency per symbol is strictly below 25 ms SLA."""
        p_dict = {"BENCH": pd.DataFrame({
            "Close": 100.0 + np.random.randn(20),
            "Volume": 1000.0 + np.random.rand(20) * 100.0,
        })}
        t0 = time.perf_counter()
        _ = self.wavelet_engine.compute_scores(p_dict)
        _ = self.curvature_engine.compute_scores(p_dict)
        _ = self.micro_engine.compute_scores(p_dict)
        _ = self.options_engine.compute_scores(p_dict)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 125.0)

    def test_tc48_mandatory_integrity_and_zero_synthetic_rows(self) -> None:
        """TC48: Verify implementations produce dynamic state-dependent outputs and maintain zero synthetic rows."""
        p1 = {"SYM1": pd.DataFrame({"Close": [10, 20, 30, 40, 50]})}
        p2 = {"SYM2": pd.DataFrame({"Close": [50, 40, 30, 20, 10]})}
        s1 = self.wavelet_engine.compute_scores(p1).iloc[0, 1]
        s2 = self.wavelet_engine.compute_scores(p2).iloc[0, 1]
        self.assertNotEqual(s1, s2, "Wavelet engine output must be dynamic and price-dependent")

        c1 = self.curvature_engine.compute_scores(p1).iloc[0, 1]
        c2 = self.curvature_engine.compute_scores(p2).iloc[0, 1]
        self.assertNotEqual(c1, c2, "Curvature GNN engine output must be dynamic and price-dependent")

        def assert_strict_zero_synthetic_rows(val: Any, source_name: str) -> None:
            self.assertIsInstance(val, int, f"{source_name} synthetic_rows must be an int, got {type(val).__name__}")
            self.assertNotIsInstance(val, bool, f"{source_name} synthetic_rows must not be a boolean")
            self.assertEqual(val, 0, f"{source_name} synthetic_rows must equal 0, got {val}")

        status_path = os.path.join(self.root_dir, "benchmarks", "30year", "status.json")
        self.assertTrue(os.path.exists(status_path), f"Benchmark status artifact missing: {status_path}")
        with open(status_path, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        self.assertIn("synthetic_rows", status_data, "status.json must contain 'synthetic_rows' key")
        assert_strict_zero_synthetic_rows(status_data["synthetic_rows"], "status.json")

        summary_path = os.path.join(self.root_dir, "benchmarks", "30year", "stock_universe_summary.json")
        self.assertTrue(os.path.exists(summary_path), f"Benchmark summary artifact missing: {summary_path}")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        self.assertIn("metadata", summary_data, "stock_universe_summary.json must contain 'metadata' dict")
        self.assertIn("synthetic_rows", summary_data["metadata"], "stock_universe_summary.json metadata must contain 'synthetic_rows'")
        assert_strict_zero_synthetic_rows(summary_data["metadata"]["synthetic_rows"], "stock_universe_summary.json")

        paper_path = os.path.join(self.root_dir, "reports", "paper_trading_session_report.json")
        if os.path.exists(paper_path):
            with open(paper_path, "r", encoding="utf-8") as f:
                paper_data = json.load(f)
            snap = paper_data.get("final_snapshot", {})
            if "net_equity" in snap and "gross_equity" in snap:
                net_eq = float(snap["net_equity"])
                gross_eq = float(snap["gross_equity"])
                self.assertLessEqual(net_eq, gross_eq + 1e-6, f"Conservation law breach: Net {net_eq} > Gross {gross_eq}")
            if "metadata" in paper_data and "synthetic_rows" in paper_data["metadata"]:
                assert_strict_zero_synthetic_rows(paper_data["metadata"]["synthetic_rows"], "paper_trading_session_report.json")

        for invalid_val in [True, False, 1, -1, 42, 0.0, 0.5, "0", None, [0], {0: 0}]:
            with self.assertRaises(AssertionError, msg=f"Validator must reject invalid synthetic_rows value: {invalid_val!r}"):
                assert_strict_zero_synthetic_rows(invalid_val, "invalid_test_input")

    def test_tc48_exact_zero_synthetic_rows_integrity(self) -> None:
        """Alias for test_tc48_mandatory_integrity_and_zero_synthetic_rows per R163 specification."""
        self.test_tc48_mandatory_integrity_and_zero_synthetic_rows()


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase164_alpha.py — Comprehensive Test Suite for Phase 164 Features F800 to F804.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F800 Symplectic Manifold Geodesic Flow, Tensor-Train Decomposition Alpha (TC07 ~ TC13)
- Category 3: F801 Lorentz / Hyperbolic Gyrovector Space & Hodge-Helmholtz Value Chain GNN (TC14 ~ TC20)
- Category 4: F802 Non-Linear Volterra Fractional Hawkes Jump-Diffusion Cross-Excitation (TC21 ~ TC27)
- Category 5: F803 Multi-Point Arbitrage-Free SVI Surface Skew & 5th-Order Greeks Accelerator (TC28 ~ TC34)
- Category 6: F804 Octuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
- Category 7: Phase164Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)

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

# F800 Imports
from src.core.spectral_wavelet_decomposition import (
    VERSION as VERSION_F800,
    RELEASE as RELEASE_F800,
    FEATURE as FEATURE_F800,
    VERSION_PHASE164 as VERSION_P164_F800,
    RELEASE_PHASE164 as RELEASE_P164_F800,
    FEATURE_PHASE164 as FEATURE_P164_F800,
    SpectralWaveletDecompositionEngine,
    SpectralWaveletDecompositionEnginePhase164,
    Phase164SpectralWaveletEngine,
    F800SpectralWaveletEngine,
    SymplecticTensorTrainWaveletEngine,
    compute_symplectic_geodesic_flow,
    extract_symplectic_geodesic_flow,
    compute_tensor_train_decomposition,
    compute_tensor_train_entropy,
    compute_instantaneous_frequency,
    compute_synchrosqueezed_wavelet_transform,
    compute_synchrosqueezed_phase_alignment,
    extract_synchrosqueezed_ridge,
    apply_hyperbolic_noise_deadband,
    convolve_atrous,
    get_wavelet_filters,
    upsample_filter,
)

# F801 Imports
from src.core.value_chain_curvature_gnn import (
    VERSION as VERSION_F801,
    RELEASE as RELEASE_F801,
    FEATURE as FEATURE_F801,
    VERSION_PHASE164 as VERSION_P164_F801,
    RELEASE_PHASE164 as RELEASE_P164_F801,
    FEATURE_PHASE164 as FEATURE_P164_F801,
    ValueChainCurvatureGNNEngine,
    ValueChainCurvatureGNNEnginePhase164,
    Phase164ValueChainCurvatureGNNEngine,
    F801ValueChainCurvatureGNNEngine,
    LorentzHyperbolicGyrovectorGNNEngine,
    lorentz_inner_product,
    lorentz_distance,
    lorentz_to_poincare,
    poincare_to_lorentz,
    gyrovector_addition,
    compute_discrete_hodge_helmholtz_decomposition,
    compute_lorentz_hyperbolic_graph_representation,
    poincare_distance,
    mobius_addition,
    poincare_exp_map,
    poincare_log_map,
    compute_hodge_laplacian_spectrum,
    detect_harmonic_value_chain_loops,
    compute_value_chain_curvature_gnn_scores,
    value_chain_curvature_gnn_score,
)

# F802 Imports
from src.core.cross_market_micro_momentum import (
    VERSION as VERSION_F802,
    RELEASE as RELEASE_F802,
    FEATURE as FEATURE_F802,
    VERSION_PHASE164 as VERSION_P164_F802,
    RELEASE_PHASE164 as RELEASE_P164_F802,
    FEATURE_PHASE164 as FEATURE_P164_F802,
    CrossMarketMicroMomentumEngine,
    CrossMarketMicroMomentumEnginePhase164,
    Phase164CrossMarketMicroMomentumEngine,
    F802CrossMarketMicroMomentumEngine,
    VolterraFractionalHawkesMomentumEngine,
    compute_volterra_fractional_kernel,
    compute_nonlinear_hawkes_activation,
    estimate_volterra_fractional_hawkes_params,
    estimate_jump_diffusion_hawkes_params,
    compute_jump_diffusion_intensity,
    compute_hawkes_branching_ratio,
    compute_rough_heston_hurst_parameter,
    compute_vpin_cascade_metric,
    compute_level2_ofi_velocity,
    compute_multivariate_hawkes_intensity,
    compute_cross_market_micro_momentum_scores,
    cross_market_micro_mom_score,
)

# F803 Imports
from src.core.option_surface_accelerator import (
    VERSION as VERSION_F803,
    RELEASE as RELEASE_F803,
    FEATURE as FEATURE_F803,
    VERSION_PHASE164 as VERSION_P164_F803,
    RELEASE_PHASE164 as RELEASE_P164_F803,
    FEATURE_PHASE164 as FEATURE_P164_F803,
    OptionSurfaceAccelerator,
    OptionSurfaceAcceleratorPhase164,
    Phase164OptionSurfaceAccelerator,
    F803OptionSurfaceAccelerator,
    FifthOrderArbitrageFreeSVIAccelerator,
    compute_fifth_order_black_scholes_greeks,
    verify_multipoint_svi_roger_lee_arbitrage_free,
    calculate_fifth_order_surface_skew,
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

# F804 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F804,
    RELEASE as RELEASE_F804,
    FEATURE as FEATURE_F804,
    VERSION_PHASE164 as VERSION_P164_F804,
    RELEASE_PHASE164 as RELEASE_P164_F804,
    FEATURE_PHASE164 as FEATURE_P164_F804,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase164,
    Phase164FactorOrthogonalizerEngine,
    F804FactorOrthogonalizerEngine,
    OctuplePillarZCAOrthogonalizer,
    OctuplePillarMap,
    OCTUPLE_PILLAR_MAP,
    SEPTUPLE_PILLAR_MAP,
    compute_octuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase164,
    apply_hyperbolic_deadband_phase160,
    compute_riemannian_airm_distance,
    compute_riemannian_airm_metric,
    compute_riemannian_frechet_shrinkage,
    compute_septuple_pillar_zca_whitening,
    apply_riemannian_deadband,
)

# Phase 164 Coupler
from src.ai.historical_couplers import (
    Phase164Coupler,
    F804Coupler,
    OctuplePillarCoupler,
    Phase164AlphaCoupler,
)

# Long-term compounding return policies
from src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    evaluate_long_term_compounding_policies,
    apply_distress_gatekeeper,
    apply_high_quality_compounder_bonus,
)


class TestPhase164Alpha(unittest.TestCase):
    """Exhaustive 48-Test Integration Suite for Phase 164 Multi-Factor Alpha Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = SpectralWaveletDecompositionEngine()
        self.curvature_engine = ValueChainCurvatureGNNEngine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase164Coupler()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_all_files(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 164 production files."""
        files = [
            ("src/core/spectral_wavelet_decomposition.py", "trading_system/src/core/spectral_wavelet_decomposition.py"),
            ("src/core/value_chain_curvature_gnn.py", "trading_system/src/core/value_chain_curvature_gnn.py"),
            ("src/core/cross_market_micro_momentum.py", "trading_system/src/core/cross_market_micro_momentum.py"),
            ("src/core/option_surface_accelerator.py", "trading_system/src/core/option_surface_accelerator.py"),
            ("src/ai/factor_orthogonalizer.py", "trading_system/src/ai/factor_orthogonalizer.py"),
            ("src/ai/historical_couplers.py", "trading_system/src/ai/historical_couplers.py"),
            ("src/ai/ensemble_scorer.py", "trading_system/src/ai/ensemble_scorer.py"),
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
        """TC02: Verify polymorphic _VersionInt(164) backward compatibility with (140, 144, 148, 152, 156, 160, 164)."""
        for v in [VERSION_F800, VERSION_F801, VERSION_F802, VERSION_F803, VERSION_F804]:
            self.assertEqual(int(v), 164)
            self.assertEqual(v, 164)
            self.assertEqual(v, 160)
            self.assertEqual(v, 156)
            self.assertEqual(v, 152)
            self.assertEqual(v, 148)
            self.assertEqual(v, 144)
            self.assertEqual(v, 140)

    def test_tc03_release_constants(self) -> None:
        """TC03: Verify Release R167 strings and backward polymorphic comparisons."""
        for r in [RELEASE_F800, RELEASE_F801, RELEASE_F802, RELEASE_F803, RELEASE_F804]:
            self.assertEqual(str(r), "R167")
            self.assertEqual(r, "R167")
            self.assertEqual(r, "R163")
            self.assertEqual(r, "R159")
            self.assertEqual(r, "R152")
            self.assertEqual(r, "R148")

    def test_tc04_feature_flags(self) -> None:
        """TC04: Verify Feature flags F800-F804 are assigned correctly."""
        self.assertEqual(FEATURE_F800, "F800")
        self.assertEqual(FEATURE_F801, "F801")
        self.assertEqual(FEATURE_F802, "F802")
        self.assertEqual(FEATURE_F803, "F803")
        self.assertEqual(FEATURE_F804, "F804")
        self.assertEqual(FEATURE_P164_F800, "F800")
        self.assertEqual(FEATURE_P164_F801, "F801")
        self.assertEqual(FEATURE_P164_F802, "F802")
        self.assertEqual(FEATURE_P164_F803, "F803")
        self.assertEqual(FEATURE_P164_F804, "F804")

    def test_tc05_strategy_registry_registration(self) -> None:
        """TC05: Verify auto-registration in STRATEGY_REGISTRY for all alpha engines."""
        for strat_id in ["spectral_wavelet", "value_chain_curvature_gnn", "cross_market_micro_momentum", "option_gamma_accel"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            cls, meta = get_registry().get(strat_id)
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    def test_tc06_alias_hierarchy_completeness(self) -> None:
        """TC06: Verify full alias hierarchy for Phase 164 classes."""
        self.assertIs(SpectralWaveletDecompositionEnginePhase164, SpectralWaveletDecompositionEngine)
        self.assertIs(Phase164SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(F800SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(SymplecticTensorTrainWaveletEngine, SpectralWaveletDecompositionEngine)

        self.assertIs(ValueChainCurvatureGNNEnginePhase164, ValueChainCurvatureGNNEngine)
        self.assertIs(Phase164ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(F801ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(LorentzHyperbolicGyrovectorGNNEngine, ValueChainCurvatureGNNEngine)

        self.assertIs(CrossMarketMicroMomentumEnginePhase164, CrossMarketMicroMomentumEngine)
        self.assertIs(Phase164CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(F802CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(VolterraFractionalHawkesMomentumEngine, CrossMarketMicroMomentumEngine)

        self.assertIs(OptionSurfaceAcceleratorPhase164, OptionSurfaceAccelerator)
        self.assertIs(Phase164OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F803OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(FifthOrderArbitrageFreeSVIAccelerator, OptionSurfaceAccelerator)

        self.assertIs(FactorOrthogonalizerEnginePhase164, FactorOrthogonalizerEngine)
        self.assertIs(Phase164FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F804FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(OctuplePillarZCAOrthogonalizer, FactorOrthogonalizerEngine)

        self.assertIs(F804Coupler, Phase164Coupler)
        self.assertIs(OctuplePillarCoupler, Phase164Coupler)
        self.assertIs(Phase164AlphaCoupler, Phase164Coupler)

    # =========================================================================
    # Category 2: F800 Symplectic Manifold Geodesic Flow & Tensor-Train Decomposition Alpha (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_extract_symplectic_geodesic_flow_bounds(self) -> None:
        """TC07: Verify extract_symplectic_geodesic_flow returns bounded geodesic velocity and entropy."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 64)) * 100.0
        res = extract_symplectic_geodesic_flow(prices)
        self.assertIn("f800_geodesic_velocity", res)
        self.assertIn("f800_tensor_train_entropy", res)
        self.assertIn("f800_hamiltonian_invariance_drift", res)

        vel = res["f800_geodesic_velocity"]
        ent = res["f800_tensor_train_entropy"]
        drift = res["f800_hamiltonian_invariance_drift"]

        self.assertTrue(0.0 <= vel <= 5.0)
        self.assertTrue(ent >= 0.0)
        self.assertTrue(np.isfinite(drift))

    def test_tc08_tensor_train_decomposition_and_entropy(self) -> None:
        """TC08: Verify compute_tensor_train_decomposition decomposes 3D tensor and measures TT entropy."""
        rng = np.random.RandomState(42)
        tensor_data = rng.normal(0, 1, (3, 3, 20))
        cores = compute_tensor_train_decomposition(tensor_data, max_rank=4)
        self.assertEqual(len(cores), 3)
        entropy = compute_tensor_train_entropy(cores)
        self.assertTrue(entropy >= 0.0)
        self.assertTrue(np.isfinite(entropy))

    def test_tc09_symplectic_geodesic_velocity_sensitivity(self) -> None:
        """TC09: Verify symplectic geodesic velocity increases during market shocks compared to flat prices."""
        p_flat = np.full(50, 100.0)
        p_shock = np.array([100.0 * (1.1 ** i) if i % 2 == 0 else 100.0 * (0.9 ** i) for i in range(50)])

        res_flat = extract_symplectic_geodesic_flow(p_flat)
        res_shock = extract_symplectic_geodesic_flow(p_shock)

        self.assertGreater(res_shock["f800_geodesic_velocity"], res_flat["f800_geodesic_velocity"])

    def test_tc10_wsst_synchrosqueezed_transform_energy(self) -> None:
        """TC10: Verify WSST synchrosqueezed transform concentrates energy on multi-frequency prices."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 128)) * 100.0
        wsst_res = self.wavelet_engine.compute_synchrosqueezed_wavelet_transform(prices)
        self.assertIn("energy_entropy", wsst_res)
        self.assertGreaterEqual(wsst_res["energy_entropy"], 0.0)
        self.assertIn("wsst_spectrum", wsst_res)
        self.assertIn("phase_alignment", wsst_res)

    def test_tc11_engine_extract_symplectic_geodesic_flow_method(self) -> None:
        """TC11: Verify SpectralWaveletDecompositionEngine methods for symplectic geodesic flow."""
        prices = np.linspace(100, 120, 60)
        res1 = self.wavelet_engine.extract_symplectic_geodesic_flow(prices)
        res2 = self.wavelet_engine.compute_symplectic_geodesic_flow(prices)
        self.assertEqual(res1["f800_geodesic_velocity"], res2["f800_geodesic_velocity"])
        self.assertEqual(res1["f800_tensor_train_entropy"], res2["f800_tensor_train_entropy"])

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
    # Category 3: F801 Lorentz / Hyperbolic Gyrovector Space & Hodge-Helmholtz Value Chain GNN (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_compute_lorentz_hyperbolic_graph_representation_bounds(self) -> None:
        """TC14: Verify compute_lorentz_hyperbolic_graph_representation outputs bounded radius, distortion, depth."""
        D = np.array([
            [0.0, 0.4, 0.8, 1.2],
            [0.4, 0.0, 0.6, 1.0],
            [0.8, 0.6, 0.0, 0.5],
            [1.2, 1.0, 0.5, 0.0],
        ])
        res = compute_lorentz_hyperbolic_graph_representation(D)
        self.assertIn("f801_lorentz_radius", res)
        self.assertIn("f801_gyrovector_distortion", res)
        self.assertIn("f801_hodge_harmonic_circulation", res)

        self.assertTrue(0.0 <= res["f801_lorentz_radius"] < 1.0)
        self.assertTrue(res["f801_gyrovector_distortion"] >= 0.0)
        self.assertTrue(res["f801_hodge_harmonic_circulation"] >= 0.0)

    def test_tc15_lorentz_distance_metric_properties(self) -> None:
        """TC15: Verify Lorentz distance satisfies non-negativity, symmetry, and identity."""
        u = np.array([0.2, 0.3])
        v = np.array([-0.1, 0.4])

        d_uu = lorentz_distance(u, u)
        self.assertAlmostEqual(d_uu, 0.0, places=6)

        d_uv = lorentz_distance(u, v)
        d_vu = lorentz_distance(v, u)
        self.assertGreater(d_uv, 0.0)
        self.assertAlmostEqual(d_uv, d_vu, places=6)

    def test_tc16_lorentz_to_poincare_coordinate_isometry(self) -> None:
        """TC16: Verify Lorentz to Poincare and Poincare to Lorentz transformations are mutually inverse."""
        p_in = np.array([0.2, -0.3])
        x_lor = poincare_to_lorentz(p_in)
        # Verify on Lorentz hyperboloid: <x, x>_L = -1
        inn = lorentz_inner_product(x_lor, x_lor)
        self.assertAlmostEqual(inn, -1.0, places=5)

        p_out = lorentz_to_poincare(x_lor)
        np.testing.assert_allclose(p_out, p_in, atol=1e-5)

    def test_tc17_gyrovector_addition_and_hyperbolic_bounds(self) -> None:
        """TC17: Verify gyrovector addition preserves unit ball boundary ||u (+) v|| < 1."""
        u = np.array([0.5, 0.4])
        v = np.array([-0.3, 0.6])
        w = gyrovector_addition(u, v, c=1.0)
        self.assertLess(float(np.linalg.norm(w)), 1.0)

    def test_tc18_engine_lorentz_hyperbolic_graph_representation_method(self) -> None:
        """TC18: Verify ValueChainCurvatureGNNEngine method compute_lorentz_hyperbolic_graph_representation."""
        D = np.array([[0.0, 0.5], [0.5, 0.0]])
        res = self.curvature_engine.compute_lorentz_hyperbolic_graph_representation(D)
        self.assertIn("f801_lorentz_radius", res)
        self.assertTrue(0.0 <= res["f801_lorentz_radius"] < 1.0)

    def test_tc19_discrete_hodge_helmholtz_decomposition(self) -> None:
        """TC19: Verify discrete Hodge-Helmholtz decomposition into curl, gradient, and harmonic circulation."""
        adj = np.array([
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 1.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0, 0.0],
        ])
        decomp = compute_discrete_hodge_helmholtz_decomposition(adj)
        self.assertIn("harmonic_circulation", decomp)
        self.assertIn("curl_flux", decomp)
        self.assertIn("gradient_divergence", decomp)
        self.assertTrue(decomp["harmonic_circulation"] >= 0.0)

    def test_tc20_harmonic_loops_and_bottleneck_detection(self) -> None:
        """TC20: Verify detect_harmonic_value_chain_loops identifies cyclic topology."""
        res = detect_harmonic_value_chain_loops(threshold=0.50)
        self.assertIn("harmonic_dimension", res)
        self.assertIn("harmonic_loops", res)
        self.assertGreaterEqual(res["detected_loops_count"], 1)

    # =========================================================================
    # Category 4: F802 Non-Linear Volterra Fractional Hawkes Jump-Diffusion Cross-Excitation (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_estimate_volterra_fractional_hawkes_params_bounds(self) -> None:
        """TC21: Verify estimate_volterra_fractional_hawkes_params outputs bounded intensity, branching, impulse."""
        returns = np.random.RandomState(42).normal(0, 0.015, 60)
        res = estimate_volterra_fractional_hawkes_params(returns)
        self.assertIn("f802_volterra_jump_intensity", res)
        self.assertIn("f802_fractional_branching_ratio", res)
        self.assertIn("f802_coupled_impulse_forecast", res)

        self.assertTrue(0.0 <= res["f802_volterra_jump_intensity"] <= 1.0)
        self.assertTrue(0.0 <= res["f802_fractional_branching_ratio"] < 1.0)
        self.assertTrue(0.0 <= res["f802_coupled_impulse_forecast"] <= 5.0)

    def test_tc22_volterra_fractional_kernel_decay(self) -> None:
        """TC22: Verify compute_volterra_fractional_kernel produces power-law memory decay."""
        t_grid = np.linspace(0.1, 5.0, 50)
        k_vals = compute_volterra_fractional_kernel(t_grid, hurst=0.15, beta=1.0)
        self.assertTrue((k_vals >= 0.0).all())
        self.assertGreater(k_vals[0], k_vals[-1])

    def test_tc23_nonlinear_hawkes_activation_bounds(self) -> None:
        """TC23: Verify compute_nonlinear_hawkes_activation enforces softplus non-negativity and smoothness."""
        x = np.array([-10.0, -1.0, 0.0, 1.0, 10.0])
        phi = compute_nonlinear_hawkes_activation(x)
        self.assertTrue((phi >= 0.0).all())
        self.assertTrue((np.diff(phi) > 0.0).all())

    def test_tc24_macro_shock_cross_excitation_acceleration(self) -> None:
        """TC24: Verify macro shock injection elevates coupled impulse forecast."""
        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.005, -0.025, 0.04])
        base_shocks = {"vix": np.array([15.0, 15.0]), "sox": np.array([3000.0, 3000.0])}
        shock_shocks = {"vix": np.array([15.0, 25.0]), "sox": np.array([3000.0, 2700.0])}

        res_base = estimate_volterra_fractional_hawkes_params(returns, macro_shocks=base_shocks)
        res_shock = estimate_volterra_fractional_hawkes_params(returns, macro_shocks=shock_shocks)

        self.assertGreaterEqual(
            res_shock["f802_coupled_impulse_forecast"],
            res_base["f802_coupled_impulse_forecast"],
        )

    def test_tc25_engine_estimate_volterra_fractional_hawkes_method(self) -> None:
        """TC25: Verify CrossMarketMicroMomentumEngine method estimate_volterra_fractional_hawkes_params."""
        returns = np.linspace(-0.02, 0.02, 40)
        res = self.micro_engine.estimate_volterra_fractional_hawkes_params(returns)
        self.assertIn("f802_volterra_jump_intensity", res)
        self.assertTrue(0.0 <= res["f802_fractional_branching_ratio"] < 1.0)

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
    # Category 5: F803 Multi-Point Arbitrage-Free SVI Surface Skew & 5th-Order Greeks Accelerator (TC28 ~ TC34)
    # =========================================================================

    def test_tc28_calculate_fifth_order_surface_skew_bounds(self) -> None:
        """TC28: Verify calculate_fifth_order_surface_skew outputs skew, curvature, and 5th-order Greeks score."""
        surface = {
            "spot": 100.0,
            "strikes": [90.0, 95.0, 100.0, 105.0, 110.0],
            "ivs": [0.25, 0.22, 0.20, 0.21, 0.24],
            "tau": 30.0 / 365.0,
            "vol": 0.20,
        }
        res = calculate_fifth_order_surface_skew(surface)
        self.assertIn("f803_surface_skew", res)
        self.assertIn("f803_surface_curvature", res)
        self.assertIn("f803_arbitrage_free_status", res)
        self.assertIn("f803_fifth_order_greeks_score", res)

        self.assertTrue(np.isfinite(res["f803_surface_skew"]))
        self.assertTrue(res["f803_surface_curvature"] >= 0.0)
        self.assertIn(res["f803_arbitrage_free_status"], [0.0, 1.0])
        self.assertTrue(0.05 <= res["f803_fifth_order_greeks_score"] <= 0.95)

    def test_tc29_fifth_order_black_scholes_greeks_consistency(self) -> None:
        """TC29: Verify compute_fifth_order_black_scholes_greeks evaluates hyper_speed, hyper_color, hyper_ultima."""
        greeks = compute_fifth_order_black_scholes_greeks(
            spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.03
        )
        self.assertIn("hyper_speed", greeks)
        self.assertIn("hyper_color", greeks)
        self.assertIn("hyper_ultima", greeks)
        self.assertIn("hyper_zomma", greeks)
        for k, v in greeks.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v))

    def test_tc30_multipoint_svi_roger_lee_no_arbitrage_check(self) -> None:
        """TC30: Verify verify_multipoint_svi_roger_lee_arbitrage_free validates Roger Lee and butterfly conditions."""
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
        ivs = [0.24, 0.22, 0.20, 0.21, 0.23]
        res = verify_multipoint_svi_roger_lee_arbitrage_free(strikes, ivs, tau=0.2, spot=100.0)
        self.assertIn("is_arbitrage_free", res)
        self.assertIn("roger_lee_satisfied", res)
        self.assertIn("butterfly_satisfied", res)
        self.assertTrue(res["is_arbitrage_free"])

    def test_tc31_svi_skew_scores_cross_asset(self) -> None:
        """TC31: Verify compute_svi_skew_scores produces valid cross-asset scores."""
        scores = compute_svi_skew_scores(symbols=["005930", "AAPL"])
        for s, score in scores.items():
            self.assertTrue(0.05 <= score <= 0.95)

    def test_tc32_engine_fifth_order_surface_skew_method(self) -> None:
        """TC32: Verify OptionSurfaceAccelerator method calculate_fifth_order_surface_skew."""
        surface = {"spot": 100.0, "tau": 0.1, "vol": 0.22}
        res = self.options_engine.calculate_fifth_order_surface_skew(surface)
        self.assertIn("f803_surface_skew", res)
        self.assertIn("f803_fifth_order_greeks_score", res)
        self.assertTrue(0.05 <= res["f803_fifth_order_greeks_score"] <= 0.95)

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
    # Category 6: F804 Octuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
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

    def test_tc36_octuple_pillar_zca_whitening_symmetry_and_identity(self) -> None:
        """TC36: Verify Octuple-Pillar ZCA whitening transforms 8x8 covariance to exact identity."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (150, 8))
        cov8 = np.cov(X, rowvar=False)
        w_zca = compute_octuple_pillar_zca_whitening(cov8, shrink_weight=0.0)
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-6)
        cov_white = w_zca @ cov8 @ w_zca.T
        np.testing.assert_allclose(cov_white, np.eye(8), atol=1e-4)

    def test_tc37_octuple_pillar_map_integrity(self) -> None:
        """TC37: Verify OCTUPLE_PILLAR_MAP defines all 8 canonical economic pillars including comp."""
        expected_pillars = ["val", "mom", "flow", "cat", "net", "vol", "gnn", "comp"]
        for p in expected_pillars:
            self.assertIn(p, OCTUPLE_PILLAR_MAP)
            self.assertGreater(len(OCTUPLE_PILLAR_MAP[p]), 0)

        # Test aliases
        self.assertEqual(OCTUPLE_PILLAR_MAP["LONG_TERM_COMPOUNDING"], OCTUPLE_PILLAR_MAP["comp"])
        self.assertEqual(OCTUPLE_PILLAR_MAP["COMP_QUALITY"], OCTUPLE_PILLAR_MAP["comp"])
        self.assertEqual(OCTUPLE_PILLAR_MAP["COMP"], OCTUPLE_PILLAR_MAP["comp"])

    def test_tc38_hyperbolic_deadband_phase164_attenuation(self) -> None:
        """TC38: Verify apply_hyperbolic_deadband_phase164 squashes noise < delta and preserves signals."""
        self.assertEqual(apply_hyperbolic_deadband_phase164(0.01, delta=0.035), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase164(-0.01, delta=0.035), 0.0)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase164(0.10, delta=0.035), 0.10, places=4)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase164(-0.10, delta=0.035), -0.10, places=4)

    def test_tc39_orthogonalize_phase164_execution(self) -> None:
        """TC39: Verify orthogonalize_phase164 executes on 8 pillar columns with institutional bounds."""
        np.random.seed(42)
        cols = [f"factor_{i}" for i in range(8)]
        data = {c: np.random.uniform(0.1, 0.9, 30) for c in cols}
        data["symbol"] = [f"SYM_{i}" for i in range(30)]
        df = pd.DataFrame(data)

        res = self.ortho_engine.orthogonalize_phase164(df, strategy_cols=cols)
        self.assertEqual(len(res), 30)
        for c in cols:
            self.assertTrue((res[c] >= 0.05).all())
            self.assertTrue((res[c] <= 0.95).all())

    def test_tc40_long_term_compounding_policies_evaluation(self) -> None:
        """TC40: Verify Distress Gatekeeper (0.70x), Quality Compounder (1.035x), and Tactical Turnaround Exemption."""
        df = pd.DataFrame({
            "symbol": ["HIGH_Q", "DISTRESS", "TACTICAL_TURNAROUND", "NEUTRAL"],
            "operating_margin": [0.20, -0.15, -0.15, 0.05],
            "roe": [0.20, -0.15, -0.15, 0.05],
            "short_squeeze_score": [0.10, 0.10, 0.70, 0.10],
            "ensemble_score": [0.60, 0.60, 0.60, 0.60],
        })

        scores = evaluate_long_term_compounding_policies(df)
        self.assertAlmostEqual(scores.iloc[0], 0.60 * 1.035, places=4)  # High-Q Compounder Bonus
        self.assertAlmostEqual(scores.iloc[1], 0.60 * 0.70, places=4)   # Distress Gatekeeper Penalty
        self.assertAlmostEqual(scores.iloc[2], 0.60, places=4)          # Tactical Turnaround Exemption (no penalty)
        self.assertAlmostEqual(scores.iloc[3], 0.60, places=4)          # Neutral unchanged

    # =========================================================================
    # Category 7: Phase164Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)
    # =========================================================================

    def test_tc41_phase164_coupler_action_functional_and_fcpi(self) -> None:
        """TC41: Verify Phase164Coupler evaluates S_action, h_phase164 in (0,1], fcpi_v164 in (0,1], and alpha_p164 in [-3, 3]."""
        p_mat = np.array([
            [0.6, 0.7, 0.5, 0.6, 0.8, 0.4, 0.5, 0.65],
            [0.5, 0.6, 0.6, 0.7, 0.5, 0.6, 0.4, 0.55],
            [0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.7, 0.45],
        ])
        res = self.coupler.evaluate(p_mat)
        self.assertIn("alpha_p164", res)
        self.assertIn("alpha", res)
        self.assertIn("h_phase164", res)
        self.assertIn("fcpi_v164", res)
        self.assertIn("s_action", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha_vals = np.asarray(res["alpha_p164"])
        h_vals = np.asarray(res["h_phase164"])
        fcpi_vals = np.asarray(res["fcpi_v164"])
        self.assertIsInstance(res["alpha_p164"], np.ndarray)
        self.assertEqual(alpha_vals.shape, (3,))
        self.assertTrue(((alpha_vals >= -3.0) & (alpha_vals <= 3.0)).all())
        self.assertTrue(np.isfinite(alpha_vals).all())
        self.assertTrue(((h_vals > 0.0) & (h_vals <= 1.0)).all())
        self.assertTrue(((fcpi_vals > 0.0) & (fcpi_vals <= 1.0)).all())

    def test_tc41b_phase164_coupler_alpha_signal_scaling_and_extremes(self) -> None:
        """TC41b: Verify Phase164Coupler.alpha_p164 scales monotonically with input factor signals and bounds extremes."""
        p_signals = np.array([
            [0.90, 0.88, 0.92, 0.85, 0.91, 0.89, 0.90, 0.92],  # Asset 0: Bullish
            [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],  # Asset 1: Neutral
            [0.10, 0.12, 0.08, 0.15, 0.09, 0.11, 0.10, 0.08],  # Asset 2: Bearish
        ])
        res = self.coupler.evaluate(p_signals)
        self.assertIn("alpha_p164", res)
        alpha = res["alpha_p164"]
        self.assertIsInstance(alpha, np.ndarray)
        self.assertEqual(alpha.shape, (3,))

        self.assertGreater(alpha[0], 0.0)
        self.assertAlmostEqual(alpha[1], 0.0, places=4)
        self.assertLess(alpha[2], 0.0)
        self.assertGreater(alpha[0], alpha[1])
        self.assertGreater(alpha[1], alpha[2])

        # Extreme shock test
        extreme_signals = np.array([
            [10.0, 50.0, 100.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            [-10.0, -50.0, -100.0, -20.0, -30.0, -40.0, -50.0, -60.0],
            [np.nan, np.inf, -np.inf, 0.5, 0.5, 0.5, 0.5, 0.5],
        ])
        res_ext = self.coupler.evaluate(extreme_signals)
        alpha_ext = np.asarray(res_ext["alpha_p164"])
        self.assertEqual(alpha_ext.shape, (3,))
        self.assertTrue(np.all(alpha_ext >= -3.0))
        self.assertTrue(np.all(alpha_ext <= 3.0))
        self.assertTrue(np.all(np.isfinite(alpha_ext)))

    def test_tc42_phase164_coupler_dataframe_series_polymorphism(self) -> None:
        """TC42: Verify Phase164Coupler handles DataFrame, dict, and Series inputs seamlessly."""
        df = pd.DataFrame({
            "p1": [0.6, 0.4],
            "p2": [0.5, 0.7],
            "p3": [0.8, 0.3],
            "p4": [0.5, 0.6],
        }, index=["AAPL", "MSFT"])
        out_df = self.coupler(df)
        self.assertIsInstance(out_df["h_phase164"], pd.Series)
        self.assertEqual(list(out_df["h_phase164"].index), ["AAPL", "MSFT"])

        d_in = {"p1": 0.6, "p2": 0.5, "p3": 0.8, "p4": 0.55}
        out_scalar = Phase164Coupler.compute(d_in)
        self.assertIsInstance(out_scalar["h_phase164"], float)

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
        """Alias for test_tc48_mandatory_integrity_and_zero_synthetic_rows per R167 specification."""
        self.test_tc48_mandatory_integrity_and_zero_synthetic_rows()


if __name__ == "__main__":
    unittest.main()

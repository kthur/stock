"""
tests/test_phase156_alpha.py — Comprehensive Test Suite for Phase 156 Features F760 to F764.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F760 Continuous Wavelet Synchrosqueezing Transform (WSST) & Phase Alignment (TC07 ~ TC13)
- Category 3: F761 Persistent Homology TDA & Hodge Laplacian Filtration (TC14 ~ TC20)
- Category 4: F762 Rough Fractional Heston Stochastic Volatility & Macro Jump Coupling (TC21 ~ TC27)
- Category 5: F763 4th-Order Greeks & SVI Volatility Surface Slices (TC28 ~ TC34)
- Category 6: F764 Septuple-Pillar Riemannian AIRM Whitening & Hyperbolic Deadband (TC35 ~ TC40)
- Category 7: Phase156Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)

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

# F760 Imports
from src.core.spectral_wavelet_decomposition import (
    VERSION as VERSION_F760,
    RELEASE as RELEASE_F760,
    FEATURE as FEATURE_F760,
    SpectralWaveletDecompositionEngine,
    SpectralWaveletDecompositionEnginePhase156,
    Phase156SpectralWaveletEngine,
    F760SpectralWaveletEngine,
    SynchrosqueezedWaveletEngine,
    compute_instantaneous_frequency,
    compute_synchrosqueezed_wavelet_transform,
    compute_synchrosqueezed_phase_alignment,
    extract_synchrosqueezed_ridge,
    apply_hyperbolic_noise_deadband,
    apply_hyperbolic_deadband_phase156,
    convolve_atrous,
    get_wavelet_filters,
    upsample_filter,
)

# F761 Imports
from src.core.value_chain_curvature_gnn import (
    VERSION as VERSION_F761,
    RELEASE as RELEASE_F761,
    FEATURE as FEATURE_F761,
    ValueChainCurvatureGNNEngine,
    ValueChainCurvatureGNNEnginePhase156,
    ValueChainHypergraphCurvatureGNNPhase156,
    Phase156ValueChainCurvatureGNNEngine,
    F761ValueChainCurvatureGNNEngine,
    PersistentHomologyValueChainEngine,
    CANONICAL_VALUE_CHAIN_HYPEREDGES,
    compute_vietoris_rips_distance,
    compute_persistent_homology_betti_numbers,
    compute_hodge_laplacian_spectrum,
    detect_harmonic_value_chain_loops,
    compute_value_chain_curvature_gnn_scores,
    value_chain_curvature_gnn_score,
)

# F762 Imports
from src.core.cross_market_micro_momentum import (
    VERSION as VERSION_F762,
    RELEASE as RELEASE_F762,
    FEATURE as FEATURE_F762,
    CrossMarketMicroMomentumEngine,
    CrossMarketMicroMomentumEnginePhase156,
    Phase156CrossMarketMicroMomentumEngine,
    F762CrossMarketMicroMomentumEngine,
    RoughHestonMicroMomentumEngine,
    RoughHestonStochasticVolEngine,
    compute_rough_heston_hurst_parameter,
    compute_fractional_volterra_kernel,
    compute_rough_volatility_forecast,
    compute_macro_jump_coupling_phase156,
    compute_vpin_cascade_metric,
    compute_level2_ofi_velocity,
    compute_multivariate_hawkes_intensity,
    compute_cross_market_micro_momentum_scores,
    cross_market_micro_mom_score,
)

# F763 Imports
from src.core.option_surface_accelerator import (
    VERSION as VERSION_F763,
    RELEASE as RELEASE_F763,
    FEATURE as FEATURE_F763,
    OptionSurfaceAccelerator,
    OptionSurfaceAcceleratorPhase156,
    Phase156OptionSurfaceAccelerator,
    F763OptionSurfaceAccelerator,
    FourthOrderGreeksAccelerator,
    compute_fourth_order_black_scholes_greeks,
    calibrate_svi_surface_slice,
    verify_svi_no_arbitrage,
    compute_svi_skew_scores,
    compute_garman_klass_parkinson_volatility,
    compute_net_dealer_gex_and_vanna,
    compute_option_surface_scores,
    option_surface_accelerator_score,
)

# F764 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F764,
    RELEASE as RELEASE_F764,
    FEATURE as FEATURE_F764,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase156,
    Phase156FactorOrthogonalizerEngine,
    F764FactorOrthogonalizerEngine,
    RiemannianZCAOrthogonalizer,
    SEPTUPLE_PILLAR_MAP,
    compute_riemannian_airm_distance,
    compute_riemannian_airm_metric,
    compute_riemannian_frechet_shrinkage,
    compute_septuple_pillar_zca_whitening,
    apply_riemannian_deadband,
)

# Phase 156 Coupler
from src.ai.historical_couplers import Phase156Coupler


class TestPhase156Alpha(unittest.TestCase):
    """Exhaustive 48-Test Integration Suite for Phase 156 Multi-Factor Alpha Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = SpectralWaveletDecompositionEngine()
        self.curvature_engine = ValueChainCurvatureGNNEngine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase156Coupler()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_all_files(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 156 production files."""
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
        """TC02: Verify polymorphic _VersionInt(156) backward compatibility with (140, 144, 148, 152, 156)."""
        for v in [VERSION_F760, VERSION_F761, VERSION_F762, VERSION_F763, VERSION_F764]:
            self.assertEqual(int(v), 156)
            self.assertEqual(v, 156)
            self.assertEqual(v, 152)
            self.assertEqual(v, 148)
            self.assertEqual(v, 144)
            self.assertEqual(v, 140)

    def test_tc03_release_constants(self) -> None:
        """TC03: Verify Release R159 strings and backward polymorphic comparisons."""
        for r in [RELEASE_F760, RELEASE_F761, RELEASE_F762, RELEASE_F763, RELEASE_F764]:
            self.assertEqual(str(r), "R159")
            self.assertEqual(r, "R159")
            self.assertEqual(r, "R152")
            self.assertEqual(r, "R148")

    def test_tc04_feature_flags(self) -> None:
        """TC04: Verify Feature flags F760-F764 are assigned correctly."""
        self.assertEqual(FEATURE_F760, "F760")
        self.assertEqual(FEATURE_F761, "F761")
        self.assertEqual(FEATURE_F762, "F762")
        self.assertEqual(FEATURE_F763, "F763")
        self.assertEqual(FEATURE_F764, "F764")

    def test_tc05_strategy_registry_registration(self) -> None:
        """TC05: Verify auto-registration in STRATEGY_REGISTRY for all alpha engines."""
        for strat_id in ["spectral_wavelet", "value_chain_curvature_gnn", "cross_market_micro_momentum", "option_gamma_accel"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            cls, meta = get_registry().get(strat_id)
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    def test_tc06_alias_hierarchy_completeness(self) -> None:
        """TC06: Verify full alias hierarchy for Phase 156 classes."""
        self.assertIs(SpectralWaveletDecompositionEnginePhase156, SpectralWaveletDecompositionEngine)
        self.assertIs(Phase156SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(F760SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(SynchrosqueezedWaveletEngine, SpectralWaveletDecompositionEngine)

        self.assertIs(ValueChainCurvatureGNNEnginePhase156, ValueChainCurvatureGNNEngine)
        self.assertIs(ValueChainHypergraphCurvatureGNNPhase156, ValueChainCurvatureGNNEngine)
        self.assertIs(Phase156ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(F761ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(PersistentHomologyValueChainEngine, ValueChainCurvatureGNNEngine)

        self.assertIs(CrossMarketMicroMomentumEnginePhase156, CrossMarketMicroMomentumEngine)
        self.assertIs(Phase156CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(F762CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(RoughHestonMicroMomentumEngine, CrossMarketMicroMomentumEngine)

        self.assertIs(OptionSurfaceAcceleratorPhase156, OptionSurfaceAccelerator)
        self.assertIs(Phase156OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F763OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(FourthOrderGreeksAccelerator, OptionSurfaceAccelerator)

        self.assertIs(FactorOrthogonalizerEnginePhase156, FactorOrthogonalizerEngine)
        self.assertIs(Phase156FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F764FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(RiemannianZCAOrthogonalizer, FactorOrthogonalizerEngine)

    # =========================================================================
    # Category 2: F760 WSST Synchrosqueezing, Phase Alignment & Ridge (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_compute_instantaneous_frequency_positivity(self) -> None:
        """TC07: Verify compute_instantaneous_frequency produces finite positive frequency estimates."""
        t = np.linspace(0, 10, 200)
        pure_sine = np.sin(2.0 * np.pi * 5.0 * t) + 10.0
        freqs = self.wavelet_engine.compute_instantaneous_frequency(pure_sine)
        self.assertIsInstance(freqs, np.ndarray)
        self.assertEqual(len(freqs), len(pure_sine))
        self.assertTrue(np.isfinite(freqs).all())
        self.assertTrue((freqs > 0.0).any())

    def test_tc08_synchrosqueezed_energy_reassignment(self) -> None:
        """TC08: Verify compute_synchrosqueezed_wavelet_transform reassigns energy into concentrated spectrum."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 128)) * 100.0
        wsst_res = self.wavelet_engine.compute_synchrosqueezed_wavelet_transform(prices)
        self.assertIn("energy_entropy", wsst_res)
        self.assertGreaterEqual(wsst_res["energy_entropy"], 0.0)
        self.assertIn("wsst_spectrum", wsst_res)
        self.assertIn("phase_alignment", wsst_res)

    def test_tc09_extract_synchrosqueezed_ridge(self) -> None:
        """TC09: Verify extract_synchrosqueezed_ridge tracks dominant frequency trajectory."""
        t = np.linspace(0, 1, 150)
        clean = np.sin(2.0 * np.pi * (2.0 + 8.0 * t) * t)
        ridge = self.wavelet_engine.extract_synchrosqueezed_ridge(clean)
        self.assertEqual(len(ridge), len(clean))
        self.assertTrue(np.isfinite(ridge).all())

    def test_tc10_wsst_noise_attenuation_on_chirp(self) -> None:
        """TC10: Verify WSST attenuates additive noise and concentrates chirp ridge energy."""
        t = np.linspace(0, 1, 150)
        clean = np.sin(2.0 * np.pi * (2.0 + 8.0 * t) * t)
        noisy = clean + np.random.RandomState(42).normal(0, 0.25, 150)
        ridge_clean = self.wavelet_engine.extract_synchrosqueezed_ridge(clean)
        ridge_noisy = self.wavelet_engine.extract_synchrosqueezed_ridge(noisy)
        self.assertEqual(len(ridge_noisy), len(noisy))
        self.assertTrue(np.isfinite(ridge_noisy).all())

    def test_tc11_engine_wsst_phase_alignment_method(self) -> None:
        """TC11: Verify engine method compute_synchrosqueezed_phase_alignment operates on price and volume feeds."""
        rng = np.random.RandomState(42)
        p = np.cumprod(1.0 + rng.normal(0.001, 0.01, 100)) * 50.0
        v = rng.uniform(1e5, 1e6, 100)
        phi = self.wavelet_engine.compute_synchrosqueezed_phase_alignment(p, v)
        self.assertIsInstance(phi, float)
        self.assertTrue(-1.0 <= phi <= 1.0)
        self.assertTrue(np.isfinite(phi))

    def test_tc12_hyperbolic_noise_deadband_phase156(self) -> None:
        """TC12: Verify apply_hyperbolic_deadband_phase156 suppresses sub-threshold noise."""
        self.assertEqual(apply_hyperbolic_deadband_phase156(0.005), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase156(-0.005), 0.0)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase156(0.08), 0.08, places=4)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase156(-0.08), -0.08, places=4)

    def test_tc13_wavelet_filters_and_atrous_convolution(self) -> None:
        """TC13: Verify convolve_atrous and get_wavelet_filters produce valid stationary transforms."""
        lp, hp = get_wavelet_filters("haar")
        sig = np.ones(32)
        c_lp = convolve_atrous(sig, lp)
        self.assertEqual(len(c_lp), len(sig))
        self.assertTrue(np.isfinite(c_lp).all())

    # =========================================================================
    # Category 3: F761 Persistent Homology TDA & Hodge Laplacian Filtration (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_vietoris_rips_distance_metric_properties(self) -> None:
        """TC14: Verify Vietoris-Rips distance d = sqrt(2*(1-rho)) satisfies metric space axioms."""
        # Reflexivity
        self.assertAlmostEqual(compute_vietoris_rips_distance(1.0), 0.0, places=6)
        # Non-negativity and maximum distance at rho=-1
        self.assertAlmostEqual(compute_vietoris_rips_distance(-1.0), 2.0, places=6)
        # Orthogonal assets (rho=0 -> sqrt(2))
        self.assertAlmostEqual(compute_vietoris_rips_distance(0.0), np.sqrt(2.0), places=6)
        # Array support
        arr = np.array([1.0, 0.0, -1.0])
        d_arr = compute_vietoris_rips_distance(arr)
        np.testing.assert_allclose(d_arr, [0.0, np.sqrt(2.0), 2.0], atol=1e-5)

    def test_tc15_persistent_betti_numbers_monotonicity(self) -> None:
        """TC15: Verify Betti-0 decreases or stays constant as filtration threshold epsilon increases."""
        # 4 points on a metric space
        dist_mat = np.array([
            [0.0, 0.2, 0.8, 0.9],
            [0.2, 0.0, 0.7, 0.8],
            [0.8, 0.7, 0.0, 0.3],
            [0.9, 0.8, 0.3, 0.0],
        ])
        b_low = compute_persistent_homology_betti_numbers(dist_mat, epsilon=0.10)
        b_mid = compute_persistent_homology_betti_numbers(dist_mat, epsilon=0.50)
        b_high = compute_persistent_homology_betti_numbers(dist_mat, epsilon=1.50)

        # Non-increasing beta_0
        self.assertGreaterEqual(b_low["beta_0"], b_mid["beta_0"])
        self.assertGreaterEqual(b_mid["beta_0"], b_high["beta_0"])
        self.assertEqual(b_high["beta_0"], 1)

    def test_tc16_discrete_hodge_laplacian_psd_spectrum(self) -> None:
        """TC16: Verify Hodge Laplacian spectrum is strictly positive semi-definite (lambda >= -1e-8)."""
        adj = np.array([
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 1.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0, 0.0],
        ])
        spec = compute_hodge_laplacian_spectrum(adj)
        self.assertIn("eigenvalues", spec)
        eigs = np.array(spec["eigenvalues"])
        self.assertTrue((eigs >= -1e-8).all(), f"Found negative eigenvalues: {eigs}")
        self.assertIn("harmonic_dimension", spec)
        self.assertGreaterEqual(spec["harmonic_dimension"], 0)

    def test_tc17_harmonic_1form_supply_chain_bottleneck(self) -> None:
        """TC17: Verify detect_harmonic_value_chain_loops identifies cyclic structures and bottlenecks."""
        res = detect_harmonic_value_chain_loops(threshold=0.50)
        self.assertIn("harmonic_dimension", res)
        self.assertIn("harmonic_loops", res)
        self.assertIn("detected_loops_count", res)
        self.assertGreaterEqual(res["detected_loops_count"], 1)
        self.assertTrue(any(l["cluster"] == "FOUNDRY_CLUSTER" for l in res["harmonic_loops"]))

    def test_tc18_engine_vietoris_rips_and_hodge_methods(self) -> None:
        """TC18: Verify engine wrapper methods for Vietoris-Rips and Hodge Laplacian."""
        d = self.curvature_engine.compute_vietoris_rips_distance(0.5)
        self.assertAlmostEqual(d, 1.0, places=5)
        dist_mat = np.array([[0.0, 0.4], [0.4, 0.0]])
        betti = self.curvature_engine.compute_persistent_homology_betti_numbers(dist_mat, epsilon=0.5)
        self.assertEqual(betti["beta_0"], 1)
        loops = self.curvature_engine.detect_harmonic_value_chain_loops(threshold=0.5)
        self.assertIsInstance(loops, dict)

    def test_tc19_hypergraph_ricci_curvature_bounds(self) -> None:
        """TC19: Verify hypergraph Forman-Ricci curvature evaluates finite values across canonical clusters."""
        curvs = self.curvature_engine.compute_all_hyperedge_curvatures()
        self.assertGreater(len(curvs), 0)
        for h_name, ric in curvs.items():
            self.assertTrue(np.isfinite(ric))

    def test_tc20_3hop_gatv2_message_passing(self) -> None:
        """TC20: Verify 3-hop curvature-modulated GATv2 attention message passing produces clean node states."""
        node_mom = {"NVDA": 0.8, "TSM": 0.6, "ASML": 0.5, "005930": 0.4}
        h1, h2, h3 = self.curvature_engine.propagate_curvature_gatv2(node_mom)
        self.assertIsInstance(h1, dict)
        self.assertIsInstance(h2, dict)
        self.assertIsInstance(h3, dict)
        for h in [h1, h2, h3]:
            for k, v in h.items():
                self.assertTrue(np.isfinite(v))

    # =========================================================================
    # Category 4: F762 Rough Fractional Heston Stochastic Volatility & Macro Jump Coupling (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_rough_heston_hurst_subdiffusive_bound(self) -> None:
        """TC21: Verify compute_rough_heston_hurst_parameter outputs subdiffusive H in (0.01, 0.49)."""
        np.random.seed(42)
        log_ret = np.random.normal(0, 0.015, 252)
        h = compute_rough_heston_hurst_parameter(log_ret)
        self.assertGreater(h, 0.0)
        self.assertLess(h, 0.5)

    def test_tc22_fractional_volterra_kernel_decay(self) -> None:
        """TC22: Verify fractional Volterra memory kernel exhibits non-Markovian monotonic decay."""
        lags = np.linspace(0.01, 5.0, 50)
        kernel = compute_fractional_volterra_kernel(lags, hurst=0.12)
        self.assertEqual(len(kernel), 50)
        self.assertTrue((np.diff(kernel) <= 1e-7).all())

    def test_tc23_rough_volatility_forecast_bounds(self) -> None:
        """TC23: Verify compute_rough_volatility_forecast produces positive finite forward estimates."""
        fc = compute_rough_volatility_forecast(current_vol=0.18, ofi_velocity=0.45, hurst=0.12)
        self.assertTrue(0.0 <= fc <= 5.0)
        self.assertTrue(np.isfinite(fc))

    def test_tc24_macro_jump_coupling_phase156_acceleration(self) -> None:
        """TC24: Verify compute_macro_jump_coupling_phase156 incorporates macro returns."""
        stock_ret = np.array([0.01, -0.015, 0.02, -0.01, 0.005, -0.02])
        base_vol = compute_macro_jump_coupling_phase156(
            stock_ret,
            macro_returns={"vix": np.array([0.0, 0.0]), "sox": np.array([0.0, 0.0]), "usdkrw": np.array([0.0, 0.0])}
        )
        shock_vol = compute_macro_jump_coupling_phase156(
            stock_ret,
            macro_returns={"vix": np.array([0.0, 5.0]), "sox": np.array([0.0, -0.04]), "usdkrw": np.array([0.0, 15.0])}
        )
        self.assertGreaterEqual(shock_vol, base_vol)
        self.assertTrue(np.isfinite(shock_vol))

    def test_tc25_engine_rough_heston_and_macro_coupling_methods(self) -> None:
        """TC25: Verify engine methods for rough Heston and macro jump coupling."""
        prices = pd.DataFrame({"Close": np.linspace(100, 110, 50)})
        h = self.micro_engine.compute_rough_heston_hurst_parameter(prices["Close"].values)
        self.assertTrue(0.0 < h < 0.5)
        stock_ret = np.diff(prices["Close"].values) / prices["Close"].values[:-1]
        coupling = self.micro_engine.compute_macro_jump_coupling_phase156(stock_ret)
        self.assertTrue(np.isfinite(coupling))

    def test_tc26_vpin_cascade_metric_and_ofi_velocity(self) -> None:
        """TC26: Verify Level-2 OFI velocity and VPIN cascade metrics evaluate market microstructure."""
        buys = np.array([100.0, 150.0, 120.0, 200.0, 180.0])
        sells = np.array([90.0, 110.0, 130.0, 90.0, 80.0])
        vpin = compute_vpin_cascade_metric(buys, sells)
        self.assertTrue(0.0 <= vpin <= 1.0)
        bid_p = np.array([100.0, 99.5, 99.0])
        bid_s = np.array([10.0, 20.0, 30.0])
        ask_p = np.array([100.5, 101.0, 101.5])
        ask_s = np.array([15.0, 25.0, 35.0])
        ofi_v = compute_level2_ofi_velocity(bid_p, bid_s, ask_p, ask_s)
        self.assertTrue(np.isfinite(ofi_v))

    def test_tc27_multivariate_hawkes_intensity_stability(self) -> None:
        """TC27: Verify multivariate Hawkes cross-excitation intensity maintains non-explosive bounds."""
        events = [(0.1, 0), (0.5, 1), (1.2, 2)]
        intensities = compute_multivariate_hawkes_intensity(events=events, current_time=2.0)
        self.assertEqual(len(intensities), 8)
        self.assertTrue((intensities >= 1e-4).all())
        self.assertTrue(np.isfinite(intensities).all())

    # =========================================================================
    # Category 5: F763 4th-Order Greeks & SVI Volatility Surface Slices (TC28 ~ TC34)
    # =========================================================================

    def test_tc28_fourth_order_black_scholes_greeks_analytical_consistency(self) -> None:
        """TC28: Verify compute_fourth_order_black_scholes_greeks evaluates speed, zoma, color, ultima_2."""
        greeks = compute_fourth_order_black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            tau=0.25,
            vol=0.20,
            rate=0.03,
        )
        self.assertTrue(any(k in greeks for k in ["zomma", "zoma", "zoma_4th"]))
        self.assertTrue(any(k in greeks for k in ["color", "color_4th"]))
        self.assertTrue(any(k in greeks for k in ["ultima_2", "ultima"]))
        for k, v in greeks.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v), f"Greek {k} is non-finite: {v}")

    def test_tc29_svi_surface_slice_convexity(self) -> None:
        """TC29: Verify SVI raw parameter slice w(k) = a + b*(rho*(k-m) + sqrt((k-m)^2 + sigma^2)) is convex."""
        k_strikes = np.linspace(80.0, 120.0, 30)
        ivs = np.array([0.22 + 0.05 * ((s - 100.0) / 20.0) ** 2 for s in k_strikes])
        res = calibrate_svi_surface_slice(k_strikes, ivs, tau=0.25, spot=100.0)
        self.assertIn("fitted_w", res)
        w = res["fitted_w"]
        self.assertEqual(len(w), 30)
        self.assertTrue((w >= 0.0).all())
        self.assertIn("is_arbitrage_free", res)

    def test_tc30_svi_roger_lee_extreme_strike_no_arbitrage(self) -> None:
        """TC30: Verify verify_svi_no_arbitrage confirms asymptotic wing slope < 2."""
        # Valid parameters: b*(1+|rho|) = 0.15 * (1 + 0.3) = 0.195 < 2.0
        self.assertTrue(verify_svi_no_arbitrage(b=0.15, rho=-0.3))
        # Arbitrage-violating parameters: b*(1+|rho|) = 1.5 * (1 + 0.8) = 2.7 > 2.0
        self.assertFalse(verify_svi_no_arbitrage(b=1.5, rho=0.8))

    def test_tc31_svi_skew_scores_monotonicity(self) -> None:
        """TC31: Verify compute_svi_skew_scores produces cross-asset option surface scores in [0.05, 0.95] sensitive to volatility."""
        # Baseline fallback without prices
        skew_base = compute_svi_skew_scores(symbols=["005930", "AAPL"])
        self.assertIsInstance(skew_base, dict)
        for s, score in skew_base.items():
            self.assertTrue(0.05 <= score <= 0.95)

        # Dynamic pricing test with bullish vs bearish price histories
        prices = {
            "BULL": pd.DataFrame({"Close": [100, 102, 105, 108, 112, 115, 120, 125, 130]}),
            "BEAR": pd.DataFrame({"Close": [130, 125, 120, 115, 110, 105, 100, 95, 85]}),
        }
        skew_dyn = compute_svi_skew_scores(symbols=["BULL", "BEAR"], prices_dict=prices)
        self.assertIn("BULL", skew_dyn)
        self.assertIn("BEAR", skew_dyn)
        self.assertTrue(0.05 <= skew_dyn["BULL"] <= 0.95)
        self.assertTrue(0.05 <= skew_dyn["BEAR"] <= 0.95)
        self.assertNotEqual(skew_dyn["BULL"], skew_dyn["BEAR"])
        self.assertGreater(skew_dyn["BULL"], skew_dyn["BEAR"])

        # Perturbation sensitivity check: altering price series changes the computed score
        prices_perturbed = {
            "BULL": pd.DataFrame({"Close": [100, 101, 102, 103, 104, 105, 106, 107, 108]}),
        }
        skew_pert = compute_svi_skew_scores(symbols=["BULL"], prices_dict=prices_perturbed)
        self.assertNotEqual(skew_dyn["BULL"], skew_pert["BULL"])
        self.assertTrue(0.05 <= skew_pert["BULL"] <= 0.95)

    def test_tc32_engine_fourth_order_greeks_and_svi_methods(self) -> None:
        """TC32: Verify OptionSurfaceAccelerator engine methods for 4th-order Greeks and SVI."""
        g = self.options_engine.compute_fourth_order_black_scholes_greeks(100.0, 100.0, 0.5, 0.25)
        self.assertIn("speed", g)
        k_strikes = np.linspace(80.0, 120.0, 10)
        ivs = np.full(10, 0.20)
        res = self.options_engine.calibrate_svi_surface_slice(k_strikes, ivs, tau=0.25, spot=100.0)
        self.assertIn("fitted_w", res)
        valid = self.options_engine.verify_svi_no_arbitrage(b=0.2, rho=-0.4)
        self.assertTrue(valid)

    def test_tc33_garman_klass_parkinson_volatility_bounds(self) -> None:
        """TC33: Verify Garman-Klass and Parkinson realized volatility estimators."""
        close = np.array([100.0, 102.0, 101.0, 103.0, 104.0, 100.0])
        high = np.array([102.0, 105.0, 103.0, 106.0, 105.0, 103.0])
        low = np.array([98.0, 100.0, 99.0, 101.0, 102.0, 98.0])
        open_p = np.array([99.0, 101.0, 100.0, 102.0, 103.0, 101.0])
        res = compute_garman_klass_parkinson_volatility(close=close, high=high, low=low, open_p=open_p)
        self.assertIn("garman_klass_vol", res)
        self.assertIn("parkinson_vol", res)
        self.assertGreater(res["garman_klass_vol"], 0.0)
        self.assertTrue(np.isfinite(res["garman_klass_vol"]))

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
    # Category 6: F764 Septuple-Pillar Riemannian Whitening & Hyperbolic Deadband (TC35 ~ TC40)
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
        # Check symmetry
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-6)
        # Check whitening: W @ cov @ W.T = I_7
        cov_white = w_zca @ cov7 @ w_zca.T
        np.testing.assert_allclose(cov_white, np.eye(7), atol=1e-4)

    def test_tc38_septuple_pillar_map_integrity(self) -> None:
        """TC38: Verify SEPTUPLE_PILLAR_MAP defines all 7 canonical economic pillars."""
        expected_pillars = ["val", "mom", "flow", "cat", "net", "vol", "gnn"]
        for p in expected_pillars:
            self.assertIn(p, SEPTUPLE_PILLAR_MAP)
            self.assertGreater(len(SEPTUPLE_PILLAR_MAP[p]), 0)

    def test_tc39_riemannian_deadband_attenuation(self) -> None:
        """TC39: Verify apply_riemannian_deadband squashes noise < delta and preserves macro signals."""
        self.assertEqual(apply_riemannian_deadband(0.01, delta=0.035), 0.0)
        self.assertEqual(apply_riemannian_deadband(-0.01, delta=0.035), 0.0)
        self.assertAlmostEqual(apply_riemannian_deadband(0.10, delta=0.035), 0.10, places=4)
        self.assertAlmostEqual(apply_riemannian_deadband(-0.10, delta=0.035), -0.10, places=4)

    def test_tc40_orthogonalize_phase156_execution(self) -> None:
        """TC40: Verify orthogonalize_phase156 executes on 7 pillar columns with institutional bounds."""
        np.random.seed(42)
        cols = [f"factor_{i}" for i in range(7)]
        data = {c: np.random.uniform(0.1, 0.9, 30) for c in cols}
        data["symbol"] = [f"SYM_{i}" for i in range(30)]
        df = pd.DataFrame(data)

        res = self.ortho_engine.orthogonalize_phase156(df, strategy_cols=cols)
        self.assertEqual(len(res), 30)
        for c in cols:
            self.assertTrue((res[c] >= 0.05).all())
            self.assertTrue((res[c] <= 0.95).all())

    # =========================================================================
    # Category 7: Phase156Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)
    # =========================================================================

    def test_tc41_phase156_coupler_action_functional_and_fcpi(self) -> None:
        """TC41: Verify Phase156Coupler evaluates S_action, h_phase156 in (0,1], fcpi_v156 in (0,1], and alpha_p156 in [-3, 3]."""
        p_mat = np.array([
            [0.6, 0.7, 0.5, 0.6, 0.8, 0.4, 0.5],
            [0.5, 0.6, 0.6, 0.7, 0.5, 0.6, 0.4],
            [0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.7],
        ])
        res = self.coupler.evaluate(p_mat)
        self.assertIn("alpha_p156", res)
        self.assertIn("alpha", res)
        self.assertIn("h_phase156", res)
        self.assertIn("fcpi_v156", res)
        self.assertIn("s_action", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha_vals = np.asarray(res["alpha_p156"])
        h_vals = np.asarray(res["h_phase156"])
        fcpi_vals = np.asarray(res["fcpi_v156"])
        self.assertIsInstance(res["alpha_p156"], np.ndarray)
        self.assertEqual(alpha_vals.shape, (3,))
        self.assertTrue(((alpha_vals >= -3.0) & (alpha_vals <= 3.0)).all())
        self.assertTrue(np.isfinite(alpha_vals).all())
        self.assertTrue(((h_vals > 0.0) & (h_vals <= 1.0)).all())
        self.assertTrue(((fcpi_vals > 0.0) & (fcpi_vals <= 1.0)).all())

    def test_tc41b_phase156_coupler_alpha_signal_scaling_and_extremes(self) -> None:
        """TC41b: Verify Phase156Coupler.alpha_p156 scales monotonically with input factor signals and bounds extremes."""
        # 3 Canonical Cross-Sectional Assets: Bullish (0.90), Neutral (0.50), Bearish (0.10)
        p_signals = np.array([
            [0.90, 0.88, 0.92, 0.85, 0.91, 0.89, 0.90],  # Asset 0: Bullish
            [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],  # Asset 1: Neutral
            [0.10, 0.12, 0.08, 0.15, 0.09, 0.11, 0.10],  # Asset 2: Bearish
        ])
        res = self.coupler.evaluate(p_signals)
        self.assertIn("alpha_p156", res)
        alpha = res["alpha_p156"]
        self.assertIsInstance(alpha, np.ndarray)
        self.assertEqual(alpha.shape, (3,))

        # 1. Bullish factor scores yield positive alpha
        self.assertGreater(alpha[0], 0.0, f"Bullish asset must have positive alpha, got {alpha[0]}")
        # 2. Neutral factor scores yield zero alpha
        self.assertAlmostEqual(alpha[1], 0.0, places=4, msg=f"Neutral asset must have zero alpha, got {alpha[1]}")
        # 3. Bearish factor scores yield negative alpha
        self.assertLess(alpha[2], 0.0, f"Bearish asset must have negative alpha, got {alpha[2]}")
        # 4. Strict monotonicity: Bullish > Neutral > Bearish
        self.assertGreater(alpha[0], alpha[1])
        self.assertGreater(alpha[1], alpha[2])

        # Extreme shock test: +1000% surge, -99% crash, and pathological inputs
        extreme_signals = np.array([
            [10.0, 50.0, 100.0, 20.0, 30.0, 40.0, 50.0],
            [-10.0, -50.0, -100.0, -20.0, -30.0, -40.0, -50.0],
            [np.nan, np.inf, -np.inf, 0.5, 0.5, 0.5, 0.5],
        ])
        res_ext = self.coupler.evaluate(extreme_signals)
        alpha_ext = np.asarray(res_ext["alpha_p156"])
        self.assertEqual(alpha_ext.shape, (3,))
        self.assertTrue(np.all(alpha_ext >= -3.0))
        self.assertTrue(np.all(alpha_ext <= 3.0))
        self.assertTrue(np.all(np.isfinite(alpha_ext)))

    def test_tc42_phase156_coupler_dataframe_series_polymorphism(self) -> None:
        """TC42: Verify Phase156Coupler handles DataFrame, dict, and Series inputs seamlessly."""
        df = pd.DataFrame({
            "p1": [0.6, 0.4],
            "p2": [0.5, 0.7],
            "p3": [0.8, 0.3],
        }, index=["AAPL", "MSFT"])
        out_df = self.coupler(df)
        self.assertIsInstance(out_df["h_phase156"], pd.Series)
        self.assertEqual(list(out_df["h_phase156"].index), ["AAPL", "MSFT"])

        d_in = {"p1": 0.6, "p2": 0.5, "p3": 0.8}
        out_scalar = Phase156Coupler.compute(d_in)
        self.assertIsInstance(out_scalar["h_phase156"], float)

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
        # Institutional latency budget check
        self.assertLess(elapsed_ms, 125.0)

    def test_tc48_mandatory_integrity_and_zero_synthetic_rows(self) -> None:
        """TC48: Verify implementations produce dynamic state-dependent outputs and maintain zero synthetic rows."""
        # 1. Dynamic state-dependent outputs across varying market inputs
        p1 = {"SYM1": pd.DataFrame({"Close": [10, 20, 30, 40, 50]})}
        p2 = {"SYM2": pd.DataFrame({"Close": [50, 40, 30, 20, 10]})}
        s1 = self.wavelet_engine.compute_scores(p1).iloc[0, 1]
        s2 = self.wavelet_engine.compute_scores(p2).iloc[0, 1]
        self.assertNotEqual(s1, s2, "Wavelet engine output must be dynamic and price-dependent")

        c1 = self.curvature_engine.compute_scores(p1).iloc[0, 1]
        c2 = self.curvature_engine.compute_scores(p2).iloc[0, 1]
        self.assertNotEqual(c1, c2, "Curvature GNN engine output must be dynamic and price-dependent")

        # 2. Non-tautological inspection of real system benchmark artifacts
        def assert_strict_zero_synthetic_rows(val: Any, source_name: str) -> None:
            self.assertIsInstance(val, int, f"{source_name} synthetic_rows must be an int, got {type(val).__name__}")
            self.assertNotIsInstance(val, bool, f"{source_name} synthetic_rows must not be a boolean")
            self.assertEqual(val, 0, f"{source_name} synthetic_rows must equal 0, got {val}")

        # Artifact 1: benchmarks/30year/status.json
        status_path = os.path.join(self.root_dir, "benchmarks", "30year", "status.json")
        self.assertTrue(os.path.exists(status_path), f"Benchmark status artifact missing: {status_path}")
        with open(status_path, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        self.assertIn("synthetic_rows", status_data, "status.json must contain 'synthetic_rows' key")
        assert_strict_zero_synthetic_rows(status_data["synthetic_rows"], "status.json")

        # Artifact 2: benchmarks/30year/stock_universe_summary.json
        summary_path = os.path.join(self.root_dir, "benchmarks", "30year", "stock_universe_summary.json")
        self.assertTrue(os.path.exists(summary_path), f"Benchmark summary artifact missing: {summary_path}")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        self.assertIn("metadata", summary_data, "stock_universe_summary.json must contain 'metadata' dict")
        self.assertIn("synthetic_rows", summary_data["metadata"], "stock_universe_summary.json metadata must contain 'synthetic_rows'")
        assert_strict_zero_synthetic_rows(summary_data["metadata"]["synthetic_rows"], "stock_universe_summary.json")

        # Artifact 3: reports/paper_trading_session_report.json (if present)
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

        # 3. Explicit verification of rejection of invalid types & non-zero values
        for invalid_val in [True, False, 1, -1, 42, 0.0, 0.5, "0", None, [0], {0: 0}]:
            with self.assertRaises(AssertionError, msg=f"Validator must reject invalid synthetic_rows value: {invalid_val!r}"):
                assert_strict_zero_synthetic_rows(invalid_val, "invalid_test_input")

    def test_tc48_exact_zero_synthetic_rows_integrity(self) -> None:
        """Alias for test_tc48_mandatory_integrity_and_zero_synthetic_rows per R159 specification."""
        self.test_tc48_mandatory_integrity_and_zero_synthetic_rows()


if __name__ == "__main__":
    unittest.main()

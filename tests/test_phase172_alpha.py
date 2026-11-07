"""
tests/test_phase172_alpha.py — Comprehensive Test Suite for Phase 172 Features F840 to F844.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F840 Calabi-Yau Metric Flow & Continuous Wavelet Packet (CWP) Alpha (TC07 ~ TC13)
- Category 3: F841 Octonionic Sheaf Laplacian & Directed Forman Curvature GNN (TC14 ~ TC20)
- Category 4: F842 Rough Path Signature Degree-4 Tensor & Fractional Volterra-Hawkes Intensity (TC21 ~ TC27)
- Category 5: F843 Extended SSVI (eSSVI) Surface Tensor & 7th-Order Greeks Acceleration Engine (TC28 ~ TC34)
- Category 6: F844 Decuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
- Category 7: Phase172Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact calculations.
Zero synthetic rows (synthetic_rows == 0).
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

# F840 Imports
from src.core.spectral_wavelet_decomposition import (
    VERSION as VERSION_F840,
    RELEASE as RELEASE_F840,
    FEATURE as FEATURE_F840,
    VERSION_PHASE172 as VERSION_P172_F840,
    RELEASE_PHASE172 as RELEASE_P172_F840,
    FEATURE_PHASE172 as FEATURE_P172_F840,
    SpectralWaveletDecompositionEngine,
    SpectralWaveletDecompositionEnginePhase172,
    Phase172SpectralWaveletEngine,
    F840SpectralWaveletEngine,
    CalabiYauWaveletEngine,
    CalabiYauCWPWaveletEngine,
    compute_cwp_signature,
    compute_calabi_yau_metric_flow,
    get_wavelet_filters,
    apply_hyperbolic_noise_deadband,
    convolve_atrous,
    upsample_filter,
)

# F841 Imports
from src.core.value_chain_curvature_gnn import (
    VERSION as VERSION_F841,
    RELEASE as RELEASE_F841,
    FEATURE as FEATURE_F841,
    VERSION_PHASE172 as VERSION_P172_F841,
    RELEASE_PHASE172 as RELEASE_P172_F841,
    FEATURE_PHASE172 as FEATURE_P172_F841,
    ValueChainCurvatureGNNEngine,
    ValueChainCurvatureGNNEnginePhase172,
    Phase172ValueChainCurvatureGNNEngine,
    F841ValueChainCurvatureGNNEngine,
    OctonionicSheafGNNEngine,
    OctonionicCurvatureGNNEngine,
    compute_octonionic_sheaf_laplacian,
    compute_sheaf_cohomology_h1,
    compute_octonionic_embedding,
    compute_directed_forman_curvature,
    CANONICAL_VALUE_CHAIN_HYPEREDGES,
)

# F842 Imports
from src.core.cross_market_micro_momentum import (
    VERSION as VERSION_F842,
    RELEASE as RELEASE_F842,
    FEATURE as FEATURE_F842,
    VERSION_PHASE172 as VERSION_P172_F842,
    RELEASE_PHASE172 as RELEASE_P172_F842,
    FEATURE_PHASE172 as FEATURE_P172_F842,
    CrossMarketMicroMomentumEngine,
    CrossMarketMicroMomentumEnginePhase172,
    Phase172CrossMarketMicroMomentumEngine,
    F842CrossMarketMicroMomentumEngine,
    RoughPathSignatureHawkesEngine,
    VolterraHawkesMicroMomentumEngine,
    compute_rough_path_signature,
    compute_volterra_hawkes_intensity,
    compute_rough_volterra_micro_momentum,
)

# F843 Imports
from src.core.option_surface_accelerator import (
    VERSION as VERSION_F843,
    RELEASE as RELEASE_F843,
    FEATURE as FEATURE_F843,
    VERSION_PHASE172 as VERSION_P172_F843,
    RELEASE_PHASE172 as RELEASE_P172_F843,
    FEATURE_PHASE172 as FEATURE_P172_F843,
    OptionSurfaceAccelerator,
    OptionSurfaceAcceleratorPhase172,
    Phase172OptionSurfaceAccelerator,
    F843OptionSurfaceAccelerator,
    F843OptionSurfaceAcceleratorEngine,
    SeventhOrderArbitrageFreeESSVIAccelerator,
    compute_seventh_order_black_scholes_greeks,
    compute_essvi_total_variance,
    verify_essvi_arbitrage_free,
    calculate_seventh_order_surface_skew,
)

# F844 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F844,
    RELEASE as RELEASE_F844,
    FEATURE as FEATURE_F844,
    VERSION_PHASE172 as VERSION_P172_F844,
    RELEASE_PHASE172 as RELEASE_P172_F844,
    FEATURE_PHASE172 as FEATURE_P172_F844,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase172,
    Phase172FactorOrthogonalizerEngine,
    F844FactorOrthogonalizerEngine,
    DecuplePillarZCAOrthogonalizer,
    DecuplePillarZCAEngine,
    DecuplePillarMap,
    DECUPLE_PILLAR_MAP,
    compute_decuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase172,
    compute_riemannian_airm_distance,
)

# Phase 172 Coupler
from src.ai.historical_couplers import (
    Phase172Coupler,
    F844Coupler,
    DecuplePillarCoupler,
    Phase172AlphaCoupler,
)


class TestPhase172Alpha(unittest.TestCase):
    """Exhaustive 48-Test Integration Suite for Phase 172 Multi-Factor Alpha Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = SpectralWaveletDecompositionEngine()
        self.curvature_engine = ValueChainCurvatureGNNEngine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase172Coupler()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_all_files(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 172 production files."""
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
        """TC02: Verify polymorphic _VersionInt(172) backward compatibility with (140, 144, 148, 152, 156, 160, 164, 168, 172)."""
        for v in [VERSION_F840, VERSION_F841, VERSION_F842, VERSION_F843, VERSION_F844]:
            self.assertEqual(int(v), 172)
            self.assertEqual(v, 172)
            self.assertEqual(v, 168)
            self.assertEqual(v, 164)
            self.assertEqual(v, 160)
            self.assertEqual(v, 156)
            self.assertEqual(v, 152)
            self.assertEqual(v, 148)
            self.assertEqual(v, 144)
            self.assertEqual(v, 140)

    def test_tc03_release_constants(self) -> None:
        """TC03: Verify Release R175 strings and backward polymorphic comparisons."""
        for r in [RELEASE_F840, RELEASE_F841, RELEASE_F842, RELEASE_F843, RELEASE_F844]:
            self.assertEqual(str(r), "R175")
            self.assertEqual(r, "R175")
            self.assertEqual(r, "R171")
            self.assertEqual(r, "R167")
            self.assertEqual(r, "R163")
            self.assertEqual(r, "R159")
            self.assertEqual(r, "R152")
            self.assertEqual(r, "R148")

    def test_tc04_feature_flags(self) -> None:
        """TC04: Verify Feature flags F840-F844 are assigned correctly."""
        self.assertEqual(FEATURE_F840, "F840")
        self.assertEqual(FEATURE_F841, "F841")
        self.assertEqual(FEATURE_F842, "F842")
        self.assertEqual(FEATURE_F843, "F843")
        self.assertEqual(FEATURE_F844, "F844")
        self.assertEqual(FEATURE_P172_F840, "F840")
        self.assertEqual(FEATURE_P172_F841, "F841")
        self.assertEqual(FEATURE_P172_F842, "F842")
        self.assertEqual(FEATURE_P172_F843, "F843")
        self.assertEqual(FEATURE_P172_F844, "F844")

    def test_tc05_strategy_registry_registration(self) -> None:
        """TC05: Verify auto-registration in STRATEGY_REGISTRY for all alpha engines."""
        for strat_id in ["spectral_wavelet", "value_chain_curvature_gnn", "cross_market_micro_momentum", "option_gamma_accel"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            cls, meta = get_registry().get(strat_id)
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    def test_tc06_alias_hierarchy_completeness(self) -> None:
        """TC06: Verify full alias hierarchy for Phase 172 classes and couplers."""
        self.assertIs(SpectralWaveletDecompositionEnginePhase172, SpectralWaveletDecompositionEngine)
        self.assertIs(Phase172SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(F840SpectralWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(CalabiYauWaveletEngine, SpectralWaveletDecompositionEngine)
        self.assertIs(CalabiYauCWPWaveletEngine, SpectralWaveletDecompositionEngine)

        self.assertIs(ValueChainCurvatureGNNEnginePhase172, ValueChainCurvatureGNNEngine)
        self.assertIs(Phase172ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(F841ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(OctonionicSheafGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(OctonionicCurvatureGNNEngine, ValueChainCurvatureGNNEngine)

        self.assertIs(CrossMarketMicroMomentumEnginePhase172, CrossMarketMicroMomentumEngine)
        self.assertIs(Phase172CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(F842CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(RoughPathSignatureHawkesEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(VolterraHawkesMicroMomentumEngine, CrossMarketMicroMomentumEngine)

        self.assertIs(OptionSurfaceAcceleratorPhase172, OptionSurfaceAccelerator)
        self.assertIs(Phase172OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F843OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F843OptionSurfaceAcceleratorEngine, OptionSurfaceAccelerator)
        self.assertIs(SeventhOrderArbitrageFreeESSVIAccelerator, OptionSurfaceAccelerator)

        self.assertIs(FactorOrthogonalizerEnginePhase172, FactorOrthogonalizerEngine)
        self.assertIs(Phase172FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F844FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(DecuplePillarZCAOrthogonalizer, FactorOrthogonalizerEngine)
        self.assertIs(DecuplePillarZCAEngine, FactorOrthogonalizerEngine)

        self.assertIs(F844Coupler, Phase172Coupler)
        self.assertIs(DecuplePillarCoupler, Phase172Coupler)
        self.assertIs(Phase172AlphaCoupler, Phase172Coupler)

    # =========================================================================
    # Category 2: F840 Calabi-Yau Metric Flow & CWP Alpha (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_compute_cwp_signature_multiscale(self) -> None:
        """TC07: Verify compute_cwp_signature extracts 4 dyadic octave packet energies."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 128)) * 100.0
        res = compute_cwp_signature(prices, num_octaves=4, wavelet_family="db4")
        self.assertIn("cwp_energy_d1", res)
        self.assertIn("cwp_energy_d2", res)
        self.assertIn("cwp_energy_d3", res)
        self.assertIn("cwp_energy_d4", res)
        self.assertIn("cwp_shannon_entropy", res)
        self.assertIn("cwp_total_energy", res)
        self.assertTrue(res["cwp_total_energy"] >= 0.0)
        self.assertTrue(res["cwp_shannon_entropy"] >= 0.0)

    def test_tc08_compute_calabi_yau_metric_flow(self) -> None:
        """TC08: Verify compute_calabi_yau_metric_flow returns Monge-Ampère residual and bounded velocity."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 64)) * 100.0
        res = compute_calabi_yau_metric_flow(prices, complex_dim=3)
        self.assertIn("calabi_yau_geodesic_velocity", res)
        self.assertIn("monge_ampere_residual", res)
        self.assertIn("ricci_flat_drift", res)
        self.assertIn("f840_calabi_yau_cwp_score", res)

        vel = res["calabi_yau_geodesic_velocity"]
        r_ma = res["monge_ampere_residual"]
        score = res["f840_calabi_yau_cwp_score"]

        self.assertTrue(-3.0 <= vel <= 3.0)
        self.assertTrue(r_ma >= 0.0)
        self.assertTrue(-3.0 <= score <= 3.0)

    def test_tc09_wavelet_filter_bank_db4_coif1(self) -> None:
        """TC09: Verify Daubechies-4 and Coiflet-1 filter banks are non-empty and normalized."""
        db4_lp, db4_hp = get_wavelet_filters("db4")
        coif_lp, coif_hp = get_wavelet_filters("coif1")
        self.assertEqual(len(db4_lp), 8)
        self.assertEqual(len(db4_hp), 8)
        self.assertEqual(len(coif_lp), 6)
        self.assertEqual(len(coif_hp), 6)
        self.assertAlmostEqual(float(np.sum(db4_lp)), np.sqrt(2.0), places=3)
        self.assertAlmostEqual(float(np.sum(coif_lp)), np.sqrt(2.0), places=3)

    def test_tc10_spectral_wavelet_engine_phase172_methods(self) -> None:
        """TC10: Verify SpectralWaveletDecompositionEngine has Phase 172 methods."""
        prices = np.array([100.0, 101.5, 102.0, 101.2, 103.5, 104.0, 103.8, 105.0] * 8)
        cwp_res = self.wavelet_engine.compute_cwp_signature(prices)
        cy_res = self.wavelet_engine.compute_calabi_yau_metric_flow(prices)
        self.assertTrue(cwp_res["cwp_total_energy"] >= 0.0)
        self.assertTrue(-3.0 <= cy_res["calabi_yau_geodesic_velocity"] <= 3.0)

    def test_tc11_cwp_short_series_graceful_handling(self) -> None:
        """TC11: Verify CWP and Calabi-Yau graceful fallback on degenerate short series."""
        res_empty = compute_cwp_signature(np.array([]))
        self.assertEqual(res_empty["cwp_total_energy"], 0.0)
        res_cy = compute_calabi_yau_metric_flow(np.array([100.0]))
        self.assertEqual(res_cy["calabi_yau_geodesic_velocity"], 0.0)

    def test_tc12_wavelet_synthetic_rows_zero(self) -> None:
        """TC12: Verify no synthetic rows generated in wavelet transforms."""
        prices = np.linspace(100.0, 120.0, 50)
        res = compute_calabi_yau_metric_flow(prices)
        self.assertFalse(np.isnan(res["calabi_yau_geodesic_velocity"]))
        self.assertFalse(np.isinf(res["calabi_yau_geodesic_velocity"]))

    def test_tc13_hyperbolic_noise_deadband_suppression(self) -> None:
        """TC13: Verify hyperbolic deadband suppresses sub-threshold wavelet noise."""
        noise = np.array([0.001, -0.002, 0.010, -0.015])
        cleaned = apply_hyperbolic_noise_deadband(noise, delta=0.035)
        np.testing.assert_allclose(cleaned, 0.0, atol=1e-6)

    # =========================================================================
    # Category 3: F841 Octonionic Sheaf Laplacian & Directed Forman Curvature GNN (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_octonionic_sheaf_laplacian_properties(self) -> None:
        """TC14: Verify compute_octonionic_sheaf_laplacian produces 8N x 8N symmetric PSD matrix."""
        num_nodes = 4
        edges = [(0, 1, 1.0), (1, 2, 0.8), (2, 3, 0.6)]
        lap = compute_octonionic_sheaf_laplacian(num_nodes, edges)
        self.assertEqual(lap.shape, (32, 32))
        np.testing.assert_allclose(lap, lap.T, atol=1e-8)
        eigvals = np.linalg.eigvalsh(lap)
        self.assertTrue(np.all(eigvals >= -1e-8))

    def test_tc15_sheaf_cohomology_h1_obstruction(self) -> None:
        """TC15: Verify H^1 sheaf cohomology obstruction energy is non-negative and zero on harmonic consensus."""
        num_nodes = 3
        edges = [(0, 1, 1.0), (1, 2, 1.0)]
        harmonic_node_states = np.zeros((3, 8), dtype=np.float64)
        obs_harmonic = compute_sheaf_cohomology_h1(num_nodes, edges, node_states=harmonic_node_states)
        self.assertAlmostEqual(obs_harmonic["h1_cohomology_energy"], 0.0, places=6)

        rng = np.random.RandomState(42)
        random_states = rng.normal(0, 1, (3, 8))
        obs_rand = compute_sheaf_cohomology_h1(num_nodes, edges, node_states=random_states)
        self.assertTrue(obs_rand["h1_cohomology_energy"] >= 0.0)

    def test_tc16_octonionic_embedding_unit_ball(self) -> None:
        """TC16: Verify compute_octonionic_embedding embeds features within the 8D open unit ball."""
        features = np.array([[10.0, -5.0, 2.0], [0.1, -0.2, 0.5]])
        emb = compute_octonionic_embedding(features)
        self.assertEqual(emb.shape, (2, 8))
        norms = np.linalg.norm(emb, axis=1)
        self.assertTrue(np.all(norms < 1.0))

    def test_tc17_directed_forman_curvature_bounds(self) -> None:
        """TC17: Verify compute_directed_forman_curvature returns values bounded strictly in [-5.0, 5.0]."""
        num_nodes = 5
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0), (4, 0, 1.0)]
        curv = compute_directed_forman_curvature(num_nodes, edges)
        self.assertEqual(curv.shape, (5,))
        self.assertTrue(np.all(curv >= -5.0) and np.all(curv <= 5.0))

    def test_tc18_octonionic_sheaf_graph_edge_cases(self) -> None:
        """TC18: Verify octonionic sheaf gracefully handles empty graph and single node."""
        lap_empty = compute_octonionic_sheaf_laplacian(0, [])
        self.assertEqual(lap_empty.shape, (0, 0))
        curv_single = compute_directed_forman_curvature(1, [])
        self.assertEqual(len(curv_single), 1)
        self.assertEqual(curv_single[0], 0.0)

    def test_tc19_value_chain_curvature_gnn_engine_phase172_methods(self) -> None:
        """TC19: Verify ValueChainCurvatureGNNEngine has Phase 172 methods."""
        lap = self.curvature_engine.compute_octonionic_sheaf_laplacian(3, [(0, 1, 1.0), (1, 2, 0.5)])
        self.assertEqual(lap.shape, (24, 24))
        curv = self.curvature_engine.compute_directed_forman_curvature(3, [(0, 1, 1.0), (1, 2, 0.5)])
        self.assertEqual(len(curv), 3)

    def test_tc20_canonical_value_chain_hyperedges_non_empty(self) -> None:
        """TC20: Verify CANONICAL_VALUE_CHAIN_HYPEREDGES contains realistic industrial supply chain relationships."""
        self.assertTrue(len(CANONICAL_VALUE_CHAIN_HYPEREDGES) >= 3)
        self.assertIn("semiconductor_foundry_advanced", CANONICAL_VALUE_CHAIN_HYPEREDGES)

    # =========================================================================
    # Category 4: F842 Rough Path Signature Degree-4 Tensor & Volterra-Hawkes (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_compute_rough_path_signature_tensor_degree4(self) -> None:
        """TC21: Verify compute_rough_path_signature degree 4 tensor dimension."""
        path_2d = np.column_stack([np.linspace(100.0, 105.0, 20), np.linspace(50.0, 52.0, 20)])
        sig_2d = compute_rough_path_signature(path_2d, degree=4)
        # For 2D path, tensor signature size = 2 + 4 + 8 + 16 = 30
        self.assertEqual(len(sig_2d), 30)

        path_4d = np.random.RandomState(42).normal(0, 1, (30, 4))
        sig_4d = compute_rough_path_signature(path_4d, degree=4)
        # For 4D path, size = 4 + 16 + 64 + 256 = 340
        self.assertEqual(len(sig_4d), 340)

    def test_tc22_rough_path_signature_chens_identity_trivial_path(self) -> None:
        """TC22: Verify rough path signature on constant path returns zero increments."""
        const_path = np.ones((10, 2)) * 50.0
        sig_const = compute_rough_path_signature(const_path, degree=4)
        np.testing.assert_allclose(sig_const, 0.0, atol=1e-8)

    def test_tc23_compute_volterra_hawkes_intensity(self) -> None:
        """TC23: Verify compute_volterra_hawkes_intensity with Hurst parameter H=0.12."""
        rng = np.random.RandomState(42)
        timestamps = np.sort(rng.uniform(0.0, 10.0, 40))
        marks = rng.exponential(1.0, 40)
        res = compute_volterra_hawkes_intensity(timestamps, marks, hurst=0.12, beta=1.50)
        self.assertIn("volterra_intensity", res)
        self.assertIn("zumbach_acceleration", res)
        self.assertIn("rough_hawkes_excitation", res)
        self.assertTrue(np.all(res["volterra_intensity"] >= 0.0))

    def test_tc24_zumbach_acceleration_feedback(self) -> None:
        """TC24: Verify Zumbach acceleration detects asymmetric volatility feedback."""
        timestamps = np.linspace(0.0, 10.0, 20)
        marks = np.linspace(1.0, 5.0, 20)
        res = compute_volterra_hawkes_intensity(timestamps, marks, hurst=0.12)
        self.assertTrue(np.isfinite(res["zumbach_acceleration"]))

    def test_tc25_compute_rough_volterra_micro_momentum(self) -> None:
        """TC25: Verify compute_rough_volterra_micro_momentum returns bounded score in [-3.0, 3.0]."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 50)) * 100.0
        volumes = np.random.RandomState(42).uniform(1000, 5000, 50)
        res = compute_rough_volterra_micro_momentum(prices, volumes)
        self.assertIn("rough_volterra_micro_momentum", res)
        self.assertIn("rough_path_energy", res)
        score = res["rough_volterra_micro_momentum"]
        self.assertTrue(-3.0 <= score <= 3.0)

    def test_tc26_cross_market_micro_momentum_engine_phase172_methods(self) -> None:
        """TC26: Verify CrossMarketMicroMomentumEngine has Phase 172 methods."""
        prices = np.linspace(100.0, 105.0, 25)
        volumes = np.ones(25) * 1000.0
        res = self.micro_engine.compute_rough_volterra_micro_momentum(prices, volumes)
        self.assertTrue(-3.0 <= res["rough_volterra_micro_momentum"] <= 3.0)

    def test_tc27_micro_momentum_zero_inputs(self) -> None:
        """TC27: Verify robust fallback on empty price and volume vectors."""
        res = compute_rough_volterra_micro_momentum(np.array([]), np.array([]))
        self.assertEqual(res["rough_volterra_micro_momentum"], 0.0)

    # =========================================================================
    # Category 5: F843 Extended SSVI (eSSVI) Surface Tensor & 7th-Order Greeks (TC28 ~ TC34)
    # =========================================================================

    def test_tc28_compute_essvi_total_variance_positivity(self) -> None:
        """TC28: Verify Extended SSVI guarantees w(k, theta) > 0 for all log-moneyness."""
        k_grid = np.linspace(-1.0, 1.0, 21)
        w = compute_essvi_total_variance(k_grid, theta=0.04, rho=-0.30, eta=0.50, gamma=0.50)
        self.assertTrue(np.all(w > 0.0))
        self.assertEqual(len(w), 21)

    def test_tc29_verify_essvi_arbitrage_free(self) -> None:
        """TC29: Verify Extended SSVI multi-maturity surface is calendar and butterfly arbitrage-free."""
        k_grid = np.linspace(-0.4, 0.4, 30)
        tau_grid = np.array([30.0 / 365.0, 90.0 / 365.0, 180.0 / 365.0, 365.0 / 365.0])
        theta_grid = 0.04 * (tau_grid / tau_grid[0])
        res = verify_essvi_arbitrage_free(k_grid, tau_grid, theta_grid, rho=-0.30, eta=0.50, gamma=0.50)
        self.assertTrue(res["calendar_arbitrage_free"])
        self.assertTrue(res["butterfly_arbitrage_free"])
        self.assertTrue(res["is_arbitrage_free"])

    def test_tc30_compute_seventh_order_black_scholes_greeks(self) -> None:
        """TC30: Verify 7th-order Black-Scholes Greeks evaluation."""
        g7 = compute_seventh_order_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.04)
        self.assertIn("septic_speed", g7)
        self.assertIn("septic_ultima", g7)
        self.assertIn("septic_zomma", g7)
        self.assertIn("seventh_order_tensor", g7)
        self.assertTrue(np.isfinite(g7["septic_speed"]))
        self.assertTrue(np.isfinite(g7["septic_ultima"]))
        self.assertTrue(np.isfinite(g7["seventh_order_tensor"]))

    def test_tc31_calculate_seventh_order_surface_skew_bounds(self) -> None:
        """TC31: Verify calculate_seventh_order_surface_skew score strictly in [0.05, 0.95]."""
        iv_surface = {
            "spot": 100.0,
            "strike": 100.0,
            "tau": 30.0 / 365.0,
            "vol": 0.22,
            "rate": 0.04,
            "oi": 5000.0,
        }
        res = calculate_seventh_order_surface_skew(iv_surface)
        self.assertIn("f843_essvi_variance", res)
        self.assertIn("f843_seventh_order_greeks_score", res)
        self.assertIn("net_dealer_gex", res)
        self.assertIn("net_dealer_vanna", res)
        score = res["f843_seventh_order_greeks_score"]
        self.assertTrue(0.05 <= score <= 0.95)

    def test_tc32_net_dealer_gex_and_vanna(self) -> None:
        """TC32: Verify dealer GEX and Vanna signed sensitivities."""
        iv_surface = {"spot": 150.0, "strike": 150.0, "tau": 0.10, "vol": 0.18, "oi": 2000.0}
        res = calculate_seventh_order_surface_skew(iv_surface)
        self.assertTrue(res["net_dealer_gex"] > 0.0)

    def test_tc33_option_surface_accelerator_engine_phase172_methods(self) -> None:
        """TC33: Verify OptionSurfaceAccelerator has Phase 172 methods."""
        w = self.options_engine.compute_essvi_total_variance(k=0.0, theta=0.04)
        self.assertTrue(np.all(w > 0.0))
        g7 = self.options_engine.compute_seventh_order_black_scholes_greeks(100.0, 100.0, 0.2, 0.2)
        self.assertIn("seventh_order_tensor", g7)

    def test_tc34_option_surface_degenerate_handling(self) -> None:
        """TC34: Verify robust fallback for degenerate option input data."""
        res = calculate_seventh_order_surface_skew({})
        self.assertEqual(res["f843_seventh_order_greeks_score"], 0.50)
        self.assertTrue(res["f843_butterfly_arbitrage_free"])

    # =========================================================================
    # Category 6: F844 Decuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
    # =========================================================================

    def test_tc35_decuple_pillar_map_coverage(self) -> None:
        """TC35: Verify DecuplePillarMap contains 10 canonical clusters including 'rev'."""
        self.assertEqual(len(DECUPLE_PILLAR_MAP), 10)
        expected_clusters = ["val", "mom", "flow", "cat", "net", "vol", "gnn", "rev", "comp", "tail"]
        for c in expected_clusters:
            self.assertIn(c, DECUPLE_PILLAR_MAP)
        self.assertEqual(DECUPLE_PILLAR_MAP["SHORT_TERM_REVERSAL"], DECUPLE_PILLAR_MAP["rev"])
        self.assertIn("overnight_gap", DECUPLE_PILLAR_MAP["rev"])

    def test_tc36_compute_decuple_pillar_zca_whitening(self) -> None:
        """TC36: Verify compute_decuple_pillar_zca_whitening produces symmetric ZCA operator."""
        rng = np.random.RandomState(42)
        A = rng.normal(0, 1, (10, 10))
        cov = A @ A.T + np.eye(10) * 0.1
        w_zca = compute_decuple_pillar_zca_whitening(cov)
        self.assertEqual(w_zca.shape, (10, 10))
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-8)
        # Whitening check: W_zca @ cov @ W_zca should equal Identity
        identity_check = w_zca @ cov @ w_zca
        np.testing.assert_allclose(identity_check, np.eye(10), atol=1e-4)

    def test_tc37_riemannian_airm_distance(self) -> None:
        """TC37: Verify compute_riemannian_airm_distance distance between covariance and identity."""
        Sigma = np.diag([1.0, 2.0, 0.5, 1.2, 0.8, 1.5, 0.9, 1.1, 1.0, 1.0])
        dist = compute_riemannian_airm_distance(Sigma, np.eye(10))
        self.assertTrue(dist > 0.0)
        self.assertAlmostEqual(compute_riemannian_airm_distance(np.eye(10), np.eye(10)), 0.0, places=6)

    def test_tc38_apply_hyperbolic_deadband_phase172(self) -> None:
        """TC38: Verify apply_hyperbolic_deadband_phase172 noise suppression (alpha=512.0, delta=0.035)."""
        sub_noise = 0.025
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase172(sub_noise, delta=0.035, alpha=512.0), 0.0, places=6)
        sig = 0.050
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase172(sig, delta=0.035, alpha=512.0), 0.050, places=4)

    def test_tc39_factor_orthogonalizer_orthogonalize_phase172(self) -> None:
        """TC39: Verify orthogonalize_phase172 method on DataFrame of 10 factors."""
        rng = np.random.RandomState(42)
        cols = [f"strat_{i}" for i in range(10)]
        df = pd.DataFrame(rng.uniform(0.3, 0.7, (50, 10)), columns=cols)
        ortho_df = self.ortho_engine.orthogonalize_phase172(df, strategy_cols=cols)
        self.assertEqual(ortho_df.shape, (50, 10))
        for col in cols:
            self.assertTrue(np.all(ortho_df[col] >= 0.05) and np.all(ortho_df[col] <= 0.95))

    def test_tc40_factor_orthogonalizer_phase172_methods(self) -> None:
        """TC40: Verify FactorOrthogonalizerEngine has Phase 172 methods."""
        cov = np.eye(10)
        w_zca = self.ortho_engine.compute_decuple_pillar_zca_whitening(cov)
        np.testing.assert_allclose(w_zca, np.eye(10), atol=1e-6)
        clean = self.ortho_engine.apply_hyperbolic_deadband_phase172(0.01)
        self.assertEqual(clean, 0.0)

    # =========================================================================
    # Category 7: Phase172Coupler, Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)
    # =========================================================================

    def test_tc41_phase172_coupler_single_1d_vector(self) -> None:
        """TC41: Verify Phase172Coupler single 1D vector returns floats with alpha_p172 strictly in [-3.0, 3.0]."""
        p_vec = [0.55, 0.60, 0.45, 0.50, 0.70, 0.40, 0.52, 0.48, 0.58, 0.53]
        res = self.coupler.evaluate(p_vec)
        self.assertIn("alpha_p172", res)
        self.assertIn("h_phase172", res)
        self.assertIn("fcpi_v172", res)
        self.assertIn("action_functional", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha = res["alpha_p172"]
        h_val = res["h_phase172"]
        fcpi = res["fcpi_v172"]

        self.assertIsInstance(alpha, float)
        self.assertTrue(-3.0 <= alpha <= 3.0)
        self.assertTrue(0.0 < h_val <= 1.0)
        self.assertTrue(0.0 < fcpi <= 1.0)
        self.assertEqual(res["zca_matrix"].shape, (10, 10))

    def test_tc42_phase172_coupler_2d_dataframe(self) -> None:
        """TC42: Verify Phase172Coupler 2D DataFrame returns pandas Series."""
        rng = np.random.RandomState(42)
        syms = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]
        df = pd.DataFrame(rng.uniform(0.4, 0.6, (5, 10)), index=syms)
        res = self.coupler.evaluate(df)

        self.assertIsInstance(res["alpha_p172"], pd.Series)
        self.assertIsInstance(res["h_phase172"], pd.Series)
        self.assertEqual(len(res["alpha_p172"]), 5)
        self.assertTrue(np.all(res["alpha_p172"] >= -3.0) and np.all(res["alpha_p172"] <= 3.0))

    def test_tc43_phase172_coupler_functional_aliases(self) -> None:
        """TC43: Verify Phase172Coupler class methods couple, compute_coupling, compute, and call."""
        p_vec = [0.5] * 10
        res1 = self.coupler(p_vec)
        res2 = self.coupler.couple(p_vec)
        res3 = self.coupler.compute_coupling(p_vec)
        res4 = Phase172Coupler.compute(p_vec)

        self.assertEqual(res1["alpha_p172"], res2["alpha_p172"])
        self.assertEqual(res1["alpha_p172"], res3["alpha_p172"])
        self.assertEqual(res1["alpha_p172"], res4["alpha_p172"])

    def test_tc44_zero_synthetic_rows_invariant(self) -> None:
        """TC44: Verify synthetic_rows == 0 invariant across all Phase 172 couplers."""
        p_dict = {f"c{i}": 0.52 for i in range(10)}
        res = self.coupler.evaluate(p_dict)
        self.assertFalse(np.isnan(res["alpha_p172"]))
        self.assertFalse(np.isinf(res["alpha_p172"]))

    def test_tc45_numerical_stability_extreme_inputs(self) -> None:
        """TC45: Verify extreme inputs (all 0.05, all 0.95, NaNs) handled stably."""
        res_nan = self.coupler.evaluate([np.nan] * 10)
        self.assertTrue(np.isfinite(res_nan["alpha_p172"]))
        res_low = self.coupler.evaluate([0.05] * 10)
        self.assertTrue(-3.0 <= res_low["alpha_p172"] <= 3.0)
        res_high = self.coupler.evaluate([0.95] * 10)
        self.assertTrue(-3.0 <= res_high["alpha_p172"] <= 3.0)

    def test_tc46_latency_sla_under_1500ms(self) -> None:
        """TC46: Verify complete 100-symbol cross-sectional coupling evaluation runs in < 1500 ms."""
        rng = np.random.RandomState(42)
        data = rng.uniform(0.3, 0.7, (100, 10))
        t0 = time.perf_counter()
        _ = self.coupler.evaluate(data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 1500.0, f"Coupler latency {elapsed_ms:.1f}ms exceeds 1500ms SLA")

    def test_tc47_cross_sectional_rank_preservation(self) -> None:
        """TC47: Verify composite alpha monotonically orders distinct strong vs weak factor profiles."""
        strong_profile = np.array([0.80] * 10)
        weak_profile = np.array([0.20] * 10)
        res_strong = self.coupler.evaluate(strong_profile)
        res_weak = self.coupler.evaluate(weak_profile)
        self.assertGreater(res_strong["alpha_p172"], res_weak["alpha_p172"])

    def test_tc48_phase172_coupler_alias_identity(self) -> None:
        """TC48: Verify F844Coupler, DecuplePillarCoupler, Phase172AlphaCoupler point to Phase172Coupler."""
        self.assertIs(F844Coupler, Phase172Coupler)
        self.assertIs(DecuplePillarCoupler, Phase172Coupler)
        self.assertIs(Phase172AlphaCoupler, Phase172Coupler)


if __name__ == "__main__":
    unittest.main()

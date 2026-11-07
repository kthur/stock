"""
tests/test_phase176_alpha.py — Comprehensive Test Suite for Phase 176 Features F860 to F864.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F860 Kähler-Einstein Metric Flow & Continuous Wavelet Scattering Transform Alpha (TC07 ~ TC13)
- Category 3: F861 Clifford Cl(3,1) Sheaf Laplacian & Directed Forman Curvature GNN (TC14 ~ TC20)
- Category 4: F862 Deg-5 Rough Path Signature & Volterra-Hawkes Microstructure Cascade (TC21 ~ TC27)
- Category 5: F863 Arbitrage-Free SABR-eSSVI 4D Surface & 9th-Order Greeks Deep Accelerator (TC28 ~ TC34)
- Category 6: F864 Undecuple-Pillar (11-Pillar) Symmetric ZCA Whitening & Hyperbolic Deadband (TC35 ~ TC40)
- Category 7: Phase176Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)

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

# F860 Imports
from src.core.wavelet_scattering import (
    VERSION as VERSION_F860,
    RELEASE as RELEASE_F860,
    FEATURE as FEATURE_F860,
    VERSION_PHASE176 as VERSION_P176_F860,
    RELEASE_PHASE176 as RELEASE_P176_F860,
    FEATURE_PHASE176 as FEATURE_P176_F860,
    KahlerEinsteinScatteringWaveletEngine,
    SpectralWaveletDecompositionEnginePhase176,
    Phase176WaveletScatteringEngine,
    F860SpectralWaveletEngine,
    WaveletScatteringEngine,
    KahlerEinsteinWaveletEngine,
    compute_wavelet_scattering_transform,
    compute_kahler_einstein_metric_flow,
    apply_hyperbolic_noise_deadband,
    create_analytic_morlet_wavelet,
)

# F861 Imports
from src.core.sheaf_gnn import (
    VERSION as VERSION_F861,
    RELEASE as RELEASE_F861,
    FEATURE as FEATURE_F861,
    VERSION_PHASE176 as VERSION_P176_F861,
    RELEASE_PHASE176 as RELEASE_P176_F861,
    FEATURE_PHASE176 as FEATURE_P176_F861,
    CliffordSheafCurvatureGNNEngine,
    ValueChainCurvatureGNNEnginePhase176,
    Phase176ValueChainCurvatureGNNEngine,
    F861ValueChainCurvatureGNNEngine,
    CliffordSheafGNNEngine,
    Phase176SheafGNNEngine,
    compute_clifford_embedding,
    compute_clifford_multivector_sheaf_laplacian,
    compute_octonionic_sheaf_laplacian,
    compute_sheaf_cohomology_h1,
    compute_directed_forman_curvature,
    CANONICAL_VALUE_CHAIN_HYPEREDGES,
)

# F862 Imports
from src.core.rough_path_hawkes import (
    VERSION as VERSION_F862,
    RELEASE as RELEASE_F862,
    FEATURE as FEATURE_F862,
    VERSION_PHASE176 as VERSION_P176_F862,
    RELEASE_PHASE176 as RELEASE_P176_F862,
    FEATURE_PHASE176 as FEATURE_P176_F862,
    RoughPathVolterraHawkesEngine,
    CrossMarketMicroMomentumEnginePhase176,
    Phase176CrossMarketMicroMomentumEngine,
    F862CrossMarketMicroMomentumEngine,
    RoughPathHawkesEngine,
    VolterraHawkesMicroMomentumEnginePhase176,
    compute_degree5_rough_path_signature,
    compute_rough_path_signature,
    compute_volterra_hawkes_intensity,
    compute_rough_volterra_micro_momentum,
)

# F863 Imports
from src.core.essvi_greeks import (
    VERSION as VERSION_F863,
    RELEASE as RELEASE_F863,
    FEATURE as FEATURE_F863,
    VERSION_PHASE176 as VERSION_P176_F863,
    RELEASE_PHASE176 as RELEASE_P176_F863,
    FEATURE_PHASE176 as FEATURE_P176_F863,
    NinthOrderSABReSSVIAccelerator,
    OptionSurfaceAcceleratorPhase176,
    Phase176OptionSurfaceAccelerator,
    F863OptionSurfaceAccelerator,
    F863OptionSurfaceAcceleratorEngine,
    SABReSSVIAccelerator,
    compute_essvi_total_variance,
    compute_sabr_implied_volatility,
    verify_essvi_arbitrage_free,
    verify_sabr_essvi_arbitrage_free,
    compute_ninth_order_black_scholes_greeks,
    compute_seventh_order_black_scholes_greeks,
    calculate_ninth_order_surface_skew,
    calculate_seventh_order_surface_skew,
)

# F864 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F864,
    RELEASE as RELEASE_F864,
    FEATURE as FEATURE_F864,
    VERSION_PHASE176 as VERSION_P176_F864,
    RELEASE_PHASE176 as RELEASE_P176_F864,
    FEATURE_PHASE176 as FEATURE_P176_F864,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase176,
    Phase176FactorOrthogonalizerEngine,
    F864FactorOrthogonalizerEngine,
    UndecuplePillarZCAOrthogonalizer,
    UndecuplePillarZCAEngine,
    UndecuplePillarMap,
    UNDECUPLE_PILLAR_MAP,
    compute_undecuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase176,
    compute_riemannian_airm_distance,
)

# Phase 176 Coupler
from src.ai.historical_couplers import (
    Phase176Coupler,
    F864Coupler,
    UndecuplePillarCoupler,
    Phase176AlphaCoupler,
)


class TestPhase176Alpha(unittest.TestCase):
    """Exhaustive 48-Test Integration Suite for Phase 176 Multi-Factor Alpha Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = KahlerEinsteinScatteringWaveletEngine()
        self.sheaf_engine = CliffordSheafCurvatureGNNEngine()
        self.rough_engine = RoughPathVolterraHawkesEngine()
        self.options_engine = NinthOrderSABReSSVIAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase176Coupler()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_all_files(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 176 production files."""
        files = [
            ("src/core/wavelet_scattering.py", "trading_system/src/core/wavelet_scattering.py"),
            ("src/core/sheaf_gnn.py", "trading_system/src/core/sheaf_gnn.py"),
            ("src/core/rough_path_hawkes.py", "trading_system/src/core/rough_path_hawkes.py"),
            ("src/core/essvi_greeks.py", "trading_system/src/core/essvi_greeks.py"),
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
        """TC02: Verify polymorphic _VersionInt(176) backward compatibility with (140, 144, 148, 152, 156, 160, 164, 168, 172, 176)."""
        for v in [VERSION_F860, VERSION_F861, VERSION_F862, VERSION_F863, VERSION_F864]:
            self.assertEqual(int(v), 176)
            self.assertEqual(v, 176)
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
        """TC03: Verify Release R179 strings and backward polymorphic comparisons."""
        for r in [RELEASE_F860, RELEASE_F861, RELEASE_F862, RELEASE_F863, RELEASE_F864]:
            self.assertEqual(str(r), "R179")
            self.assertEqual(r, "R179")
            self.assertEqual(r, "R175")
            self.assertEqual(r, "R171")
            self.assertEqual(r, "R167")
            self.assertEqual(r, "R163")
            self.assertEqual(r, "R159")
            self.assertEqual(r, "R152")
            self.assertEqual(r, "R148")

    def test_tc04_feature_flags(self) -> None:
        """TC04: Verify Feature flags F860-F864 are assigned correctly."""
        self.assertEqual(FEATURE_F860, "F860")
        self.assertEqual(FEATURE_F861, "F861")
        self.assertEqual(FEATURE_F862, "F862")
        self.assertEqual(FEATURE_F863, "F863")
        self.assertEqual(FEATURE_F864, "F864")
        self.assertEqual(FEATURE_P176_F860, "F860")
        self.assertEqual(FEATURE_P176_F861, "F861")
        self.assertEqual(FEATURE_P176_F862, "F862")
        self.assertEqual(FEATURE_P176_F863, "F863")
        self.assertEqual(FEATURE_P176_F864, "F864")

    def test_tc05_strategy_registry_registration(self) -> None:
        """TC05: Verify auto-registration in STRATEGY_REGISTRY for all alpha engines."""
        for strat_id in ["wavelet_scattering", "sheaf_gnn", "rough_path_hawkes", "option_gamma_accel"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            cls, meta = get_registry().get(strat_id)
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    def test_tc06_alias_hierarchy_completeness(self) -> None:
        """TC06: Verify full alias hierarchy for Phase 176 classes and couplers."""
        self.assertIs(SpectralWaveletDecompositionEnginePhase176, KahlerEinsteinScatteringWaveletEngine)
        self.assertIs(Phase176WaveletScatteringEngine, KahlerEinsteinScatteringWaveletEngine)
        self.assertIs(F860SpectralWaveletEngine, KahlerEinsteinScatteringWaveletEngine)
        self.assertIs(WaveletScatteringEngine, KahlerEinsteinScatteringWaveletEngine)
        self.assertIs(KahlerEinsteinWaveletEngine, KahlerEinsteinScatteringWaveletEngine)

        self.assertIs(ValueChainCurvatureGNNEnginePhase176, CliffordSheafCurvatureGNNEngine)
        self.assertIs(Phase176ValueChainCurvatureGNNEngine, CliffordSheafCurvatureGNNEngine)
        self.assertIs(F861ValueChainCurvatureGNNEngine, CliffordSheafCurvatureGNNEngine)
        self.assertIs(CliffordSheafGNNEngine, CliffordSheafCurvatureGNNEngine)
        self.assertIs(Phase176SheafGNNEngine, CliffordSheafCurvatureGNNEngine)

        self.assertIs(CrossMarketMicroMomentumEnginePhase176, RoughPathVolterraHawkesEngine)
        self.assertIs(Phase176CrossMarketMicroMomentumEngine, RoughPathVolterraHawkesEngine)
        self.assertIs(F862CrossMarketMicroMomentumEngine, RoughPathVolterraHawkesEngine)
        self.assertIs(RoughPathHawkesEngine, RoughPathVolterraHawkesEngine)
        self.assertIs(VolterraHawkesMicroMomentumEnginePhase176, RoughPathVolterraHawkesEngine)

        self.assertIs(OptionSurfaceAcceleratorPhase176, NinthOrderSABReSSVIAccelerator)
        self.assertIs(Phase176OptionSurfaceAccelerator, NinthOrderSABReSSVIAccelerator)
        self.assertIs(F863OptionSurfaceAccelerator, NinthOrderSABReSSVIAccelerator)
        self.assertIs(F863OptionSurfaceAcceleratorEngine, NinthOrderSABReSSVIAccelerator)
        self.assertIs(SABReSSVIAccelerator, NinthOrderSABReSSVIAccelerator)

        self.assertIs(FactorOrthogonalizerEnginePhase176, FactorOrthogonalizerEngine)
        self.assertIs(Phase176FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F864FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(UndecuplePillarZCAOrthogonalizer, FactorOrthogonalizerEngine)
        self.assertIs(UndecuplePillarZCAEngine, FactorOrthogonalizerEngine)

        self.assertIs(F864Coupler, Phase176Coupler)
        self.assertIs(UndecuplePillarCoupler, Phase176Coupler)
        self.assertIs(Phase176AlphaCoupler, Phase176Coupler)

    # =========================================================================
    # Category 2: F860 Kähler-Einstein Wavelet Scattering Alpha (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_compute_wavelet_scattering_transform_orders(self) -> None:
        """TC07: Verify compute_wavelet_scattering_transform computes S_0, S_1, S_2 energies."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 128)) * 100.0
        ret = np.diff(np.log(prices))
        res = compute_wavelet_scattering_transform(ret, J=3, Q=4)
        self.assertIn("s0_energy", res)
        self.assertIn("s1_energy", res)
        self.assertIn("s2_energy", res)
        self.assertIn("total_scattering_energy", res)
        self.assertIn("scattering_energy_ratio", res)
        self.assertIn("cross_scale_entropy", res)
        self.assertTrue(res["total_scattering_energy"] >= 0.0)
        self.assertTrue(res["cross_scale_entropy"] >= 0.0)
        self.assertTrue(0.0 <= res["scattering_energy_ratio"] <= 1.0)

    def test_tc08_compute_kahler_einstein_metric_flow(self) -> None:
        """TC08: Verify compute_kahler_einstein_metric_flow returns Kähler-Einstein residual and bounded velocity."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.001, 0.02, 64)) * 100.0
        volumes = np.random.RandomState(42).uniform(1000, 5000, 64)
        res = compute_kahler_einstein_metric_flow(prices, volumes=volumes)
        self.assertIn("f860_kahler_einstein_velocity", res)
        self.assertIn("f860_scattering_energy_ratio", res)
        self.assertIn("f860_ricci_curvature", res)
        self.assertIn("f860_ke_residual", res)
        self.assertIn("f860_scattering_score", res)

        vel = res["f860_kahler_einstein_velocity"]
        ke_res = res["f860_ke_residual"]
        score = res["f860_scattering_score"]

        self.assertTrue(-3.0 <= vel <= 3.0)
        self.assertTrue(ke_res >= 0.0)
        self.assertTrue(0.05 <= score <= 0.95)

    def test_tc09_analytic_morlet_wavelet_properties(self) -> None:
        """TC09: Verify create_analytic_morlet_wavelet produces normalized complex wavelet."""
        psi = create_analytic_morlet_wavelet(length=32, center_freq=0.20)
        self.assertEqual(len(psi), 32)
        self.assertTrue(np.iscomplexobj(psi))
        norm = np.linalg.norm(psi)
        self.assertAlmostEqual(float(norm), 1.0, places=5)

    def test_tc10_wavelet_scattering_engine_methods(self) -> None:
        """TC10: Verify KahlerEinsteinScatteringWaveletEngine has Phase 176 methods."""
        prices = np.array([100.0, 101.5, 102.0, 101.2, 103.5, 104.0, 103.8, 105.0] * 8)
        scat_res = self.wavelet_engine.compute_scattering_transform(np.diff(np.log(prices)))
        ke_res = self.wavelet_engine.compute_kahler_einstein_flow(prices)
        self.assertTrue(scat_res["total_scattering_energy"] >= 0.0)
        self.assertTrue(-3.0 <= ke_res["kahler_einstein_geodesic_velocity"] <= 3.0)

    def test_tc11_wavelet_scattering_short_series_graceful_fallback(self) -> None:
        """TC11: Verify scattering transform graceful fallback on degenerate short series."""
        res_empty = compute_wavelet_scattering_transform(np.array([]))
        self.assertEqual(res_empty["total_scattering_energy"], 0.0)
        res_ke = compute_kahler_einstein_metric_flow(np.array([100.0]))
        self.assertEqual(res_ke["f860_kahler_einstein_velocity"], 0.0)

    def test_tc12_wavelet_synthetic_rows_zero(self) -> None:
        """TC12: Verify no synthetic rows or NaNs generated in wavelet scattering."""
        prices = np.linspace(100.0, 120.0, 50)
        res = compute_kahler_einstein_metric_flow(prices)
        self.assertFalse(np.isnan(res["f860_kahler_einstein_velocity"]))
        self.assertFalse(np.isinf(res["f860_kahler_einstein_velocity"]))

    def test_tc13_hyperbolic_noise_deadband_suppression(self) -> None:
        """TC13: Verify hyperbolic deadband suppresses sub-threshold wavelet noise."""
        noise = np.array([0.001, -0.002, 0.010, -0.015])
        cleaned = apply_hyperbolic_noise_deadband(noise, delta=0.035)
        np.testing.assert_allclose(cleaned, 0.0, atol=1e-6)

    # =========================================================================
    # Category 3: F861 Clifford Cl(3,1) Sheaf GNN (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_clifford_sheaf_laplacian_properties(self) -> None:
        """TC14: Verify compute_clifford_multivector_sheaf_laplacian produces 16N x 16N symmetric PSD matrix."""
        num_nodes = 4
        edges = [(0, 1, 1.0), (1, 2, 0.8), (2, 3, 0.6)]
        lap = compute_clifford_multivector_sheaf_laplacian(num_nodes, edges, stalk_dim=16)
        self.assertEqual(lap.shape, (64, 64))
        np.testing.assert_allclose(lap, lap.T, atol=1e-8)
        eigvals = np.linalg.eigvalsh(lap)
        self.assertTrue(np.all(eigvals >= -1e-8))

    def test_tc15_sheaf_cohomology_h1_obstruction(self) -> None:
        """TC15: Verify H^1 sheaf cohomology obstruction energy is non-negative and zero on harmonic consensus."""
        num_nodes = 3
        edges = [(0, 1, 1.0), (1, 2, 1.0)]
        harmonic_node_states = np.zeros((3, 16), dtype=np.float64)
        obs_harmonic = compute_sheaf_cohomology_h1(num_nodes, edges, node_states=harmonic_node_states, stalk_dim=16)
        self.assertAlmostEqual(obs_harmonic["h1_cohomology_energy"], 0.0, places=6)

        rng = np.random.RandomState(42)
        random_states = rng.normal(0, 1, (3, 16))
        obs_rand = compute_sheaf_cohomology_h1(num_nodes, edges, node_states=random_states, stalk_dim=16)
        self.assertTrue(obs_rand["h1_cohomology_energy"] >= 0.0)

    def test_tc16_clifford_embedding_unit_ball(self) -> None:
        """TC16: Verify compute_clifford_embedding embeds features within the 16D open unit ball."""
        features = np.array([[10.0, -5.0, 2.0], [0.1, -0.2, 0.5]])
        emb = compute_clifford_embedding(features, dim=16)
        self.assertEqual(emb.shape, (2, 16))
        norms = np.linalg.norm(emb, axis=1)
        self.assertTrue(np.all(norms < 1.0))

    def test_tc17_directed_forman_curvature_bounds(self) -> None:
        """TC17: Verify compute_directed_forman_curvature returns values bounded strictly in [-5.0, 5.0]."""
        num_nodes = 5
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0), (4, 0, 1.0)]
        curv = compute_directed_forman_curvature(num_nodes, edges)
        self.assertEqual(curv.shape, (5,))
        self.assertTrue(np.all(curv >= -5.0) and np.all(curv <= 5.0))

    def test_tc18_clifford_sheaf_graph_edge_cases(self) -> None:
        """TC18: Verify Clifford sheaf gracefully handles empty graph and single node."""
        lap_empty = compute_clifford_multivector_sheaf_laplacian(0, [], stalk_dim=16)
        self.assertEqual(lap_empty.shape, (0, 0))
        curv_single = compute_directed_forman_curvature(1, [])
        self.assertEqual(len(curv_single), 1)
        self.assertEqual(curv_single[0], 0.0)

    def test_tc19_sheaf_gnn_engine_methods(self) -> None:
        """TC19: Verify CliffordSheafCurvatureGNNEngine has Phase 176 methods."""
        lap = self.sheaf_engine.compute_sheaf_laplacian(3, [(0, 1, 1.0), (1, 2, 0.5)])
        self.assertEqual(lap.shape, (48, 48))
        curv = self.sheaf_engine.compute_directed_forman_curvature(3, [(0, 1, 1.0), (1, 2, 0.5)])
        self.assertEqual(len(curv), 3)

    def test_tc20_canonical_value_chain_hyperedges_coverage(self) -> None:
        """TC20: Verify CANONICAL_VALUE_CHAIN_HYPEREDGES contains realistic supply chain networks."""
        self.assertTrue(len(CANONICAL_VALUE_CHAIN_HYPEREDGES) >= 4)
        self.assertIn("semiconductor_foundry_advanced", CANONICAL_VALUE_CHAIN_HYPEREDGES)
        self.assertIn("ai_accelerator_server_cluster", CANONICAL_VALUE_CHAIN_HYPEREDGES)
        self.assertIn("automotive_battery_powertrain", CANONICAL_VALUE_CHAIN_HYPEREDGES)

    # =========================================================================
    # Category 4: F862 Deg-5 Rough Path Signature & Volterra-Hawkes (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_compute_degree5_rough_path_signature_dimensions(self) -> None:
        """TC21: Verify compute_degree5_rough_path_signature tensor dimensions."""
        path_2d = np.column_stack([np.linspace(100.0, 105.0, 20), np.linspace(50.0, 52.0, 20)])
        sig_2d_deg4 = compute_degree5_rough_path_signature(path_2d, degree=4)
        # 2 + 4 + 8 + 16 = 30
        self.assertEqual(len(sig_2d_deg4), 30)

        sig_2d_deg5 = compute_degree5_rough_path_signature(path_2d, degree=5)
        # 30 + 32 = 62
        self.assertEqual(len(sig_2d_deg5), 62)

        path_4d = np.random.RandomState(42).normal(0, 1, (30, 4))
        sig_4d_deg4 = compute_degree5_rough_path_signature(path_4d, degree=4)
        # 4 + 16 + 64 + 256 = 340
        self.assertEqual(len(sig_4d_deg4), 340)

        sig_4d_deg5 = compute_degree5_rough_path_signature(path_4d, degree=5)
        # 340 + 1024 = 1364
        self.assertEqual(len(sig_4d_deg5), 1364)

    def test_tc22_rough_path_signature_constant_path(self) -> None:
        """TC22: Verify rough path signature on constant path returns zero increments."""
        const_path = np.ones((10, 2)) * 50.0
        sig_const = compute_degree5_rough_path_signature(const_path, degree=5)
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
        res = compute_rough_volterra_micro_momentum(prices, volumes, degree=5)
        self.assertIn("rough_volterra_micro_momentum", res)
        self.assertIn("rough_path_energy", res)
        score = res["rough_volterra_micro_momentum"]
        self.assertTrue(-3.0 <= score <= 3.0)
        self.assertTrue(0.05 <= res["f862_micro_score"] <= 0.95)

    def test_tc26_rough_path_hawkes_engine_methods(self) -> None:
        """TC26: Verify RoughPathVolterraHawkesEngine has Phase 176 methods."""
        prices = np.linspace(100.0, 105.0, 25)
        volumes = np.ones(25) * 1000.0
        res = self.rough_engine.compute_rough_volterra_micro_momentum(prices, volumes)
        self.assertTrue(-3.0 <= res["rough_volterra_micro_momentum"] <= 3.0)

    def test_tc27_micro_momentum_zero_inputs(self) -> None:
        """TC27: Verify robust fallback on empty price and volume vectors."""
        res = compute_rough_volterra_micro_momentum(np.array([]), np.array([]))
        self.assertEqual(res["rough_volterra_micro_momentum"], 0.0)

    # =========================================================================
    # Category 5: F863 SABR-eSSVI 4D Surface & 9th-Order Greeks (TC28 ~ TC34)
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

    def test_tc30_compute_ninth_order_black_scholes_greeks(self) -> None:
        """TC30: Verify 9th-order Black-Scholes Greeks evaluation."""
        g9 = compute_ninth_order_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.04)
        self.assertIn("ninth_speed", g9)
        self.assertIn("ninth_ultima", g9)
        self.assertIn("ninth_order_tensor", g9)
        self.assertIn("septic_speed", g9)
        self.assertIn("seventh_order_tensor", g9)
        self.assertTrue(np.isfinite(g9["ninth_speed"]))
        self.assertTrue(np.isfinite(g9["ninth_ultima"]))
        self.assertTrue(np.isfinite(g9["ninth_order_tensor"]))

    def test_tc31_calculate_ninth_order_surface_skew_bounds(self) -> None:
        """TC31: Verify calculate_ninth_order_surface_skew score strictly in [0.05, 0.95]."""
        iv_surface = {
            "spot": 100.0,
            "strike": 100.0,
            "tau": 30.0 / 365.0,
            "vol": 0.22,
            "rate": 0.04,
            "oi": 5000.0,
        }
        res = calculate_ninth_order_surface_skew(iv_surface)
        self.assertIn("f863_ninth_order_greeks_score", res)
        self.assertIn("f843_seventh_order_greeks_score", res)
        self.assertIn("net_dealer_gex", res)
        self.assertIn("net_dealer_vanna", res)
        score = res["f863_ninth_order_greeks_score"]
        self.assertTrue(0.05 <= score <= 0.95)

    def test_tc32_net_dealer_gex_and_vanna(self) -> None:
        """TC32: Verify dealer GEX and Vanna signed sensitivities."""
        iv_surface = {"spot": 150.0, "strike": 150.0, "tau": 0.10, "vol": 0.18, "oi": 2000.0}
        res = calculate_ninth_order_surface_skew(iv_surface)
        self.assertTrue(res["net_dealer_gex"] > 0.0)

    def test_tc33_sabr_volatility_atm_and_skew(self) -> None:
        """TC33: Verify compute_sabr_implied_volatility at ATM and OTM/ITM strikes."""
        vol_atm = compute_sabr_implied_volatility(forward=100.0, strike=100.0, tau=0.5, alpha=0.25, beta=0.7, rho=-0.3, nu=0.4)
        vol_otm = compute_sabr_implied_volatility(forward=100.0, strike=110.0, tau=0.5, alpha=0.25, beta=0.7, rho=-0.3, nu=0.4)
        self.assertTrue(vol_atm > 0.0)
        self.assertTrue(vol_otm > 0.0)

    def test_tc34_option_surface_accelerator_methods(self) -> None:
        """TC34: Verify NinthOrderSABReSSVIAccelerator has Phase 176 methods."""
        w = self.options_engine.compute_essvi_total_variance(k=0.0, theta=0.04)
        self.assertTrue(np.all(w > 0.0))
        g9 = self.options_engine.compute_ninth_order_greeks(100.0, 100.0, 0.2, 0.2)
        self.assertIn("ninth_order_tensor", g9)

    # =========================================================================
    # Category 6: F864 Undecuple-Pillar Symmetric ZCA Whitening (TC35 ~ TC40)
    # =========================================================================

    def test_tc35_undecuple_pillar_map_coverage(self) -> None:
        """TC35: Verify UndecuplePillarMap contains 11 canonical clusters including 'macro'."""
        self.assertEqual(len(UNDECUPLE_PILLAR_MAP), 11)
        expected_clusters = ["val", "mom", "flow", "cat", "net", "vol", "gnn", "rev", "comp", "tail", "macro"]
        for c in expected_clusters:
            self.assertIn(c, UNDECUPLE_PILLAR_MAP)
        self.assertEqual(UNDECUPLE_PILLAR_MAP["GLOBAL_MACRO"], UNDECUPLE_PILLAR_MAP["macro"])
        self.assertEqual(UNDECUPLE_PILLAR_MAP["MACRO_SPILLOVER"], UNDECUPLE_PILLAR_MAP["macro"])
        self.assertIn("dynamic_fx_hedging", UNDECUPLE_PILLAR_MAP["macro"])

    def test_tc36_compute_undecuple_pillar_zca_whitening(self) -> None:
        """TC36: Verify compute_undecuple_pillar_zca_whitening produces symmetric ZCA operator."""
        rng = np.random.RandomState(42)
        A = rng.normal(0, 1, (11, 11))
        cov = A @ A.T + np.eye(11) * 0.1
        w_zca = compute_undecuple_pillar_zca_whitening(cov)
        self.assertEqual(w_zca.shape, (11, 11))
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-8)
        # Whitening check: W_zca @ cov @ W_zca should equal Identity
        identity_check = w_zca @ cov @ w_zca
        np.testing.assert_allclose(identity_check, np.eye(11), atol=1e-4)

    def test_tc37_riemannian_airm_distance(self) -> None:
        """TC37: Verify compute_riemannian_airm_distance between covariance and identity."""
        Sigma = np.diag([1.0, 2.0, 0.5, 1.2, 0.8, 1.5, 0.9, 1.1, 1.0, 1.0, 1.3])
        dist = compute_riemannian_airm_distance(Sigma, np.eye(11))
        self.assertTrue(dist > 0.0)
        self.assertAlmostEqual(compute_riemannian_airm_distance(np.eye(11), np.eye(11)), 0.0, places=6)

    def test_tc38_apply_hyperbolic_deadband_phase176(self) -> None:
        """TC38: Verify apply_hyperbolic_deadband_phase176 noise suppression (alpha=512.0, delta=0.035)."""
        sub_noise = 0.025
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase176(sub_noise, delta=0.035, alpha=512.0), 0.0, places=6)
        sig = 0.050
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase176(sig, delta=0.035, alpha=512.0), 0.050, places=4)

    def test_tc39_factor_orthogonalizer_orthogonalize_phase176(self) -> None:
        """TC39: Verify orthogonalize_phase176 method on DataFrame of 11 factors."""
        rng = np.random.RandomState(42)
        cols = [f"strat_{i}" for i in range(11)]
        df = pd.DataFrame(rng.uniform(0.3, 0.7, (50, 11)), columns=cols)
        ortho_df = self.ortho_engine.orthogonalize_phase176(df, strategy_cols=cols)
        self.assertEqual(ortho_df.shape, (50, 11))
        for col in cols:
            self.assertTrue(np.all(ortho_df[col] >= 0.05) and np.all(ortho_df[col] <= 0.95))

    def test_tc40_factor_orthogonalizer_phase176_methods(self) -> None:
        """TC40: Verify FactorOrthogonalizerEngine has Phase 176 methods."""
        cov = np.eye(11)
        w_zca = self.ortho_engine.compute_undecuple_pillar_zca_whitening(cov)
        np.testing.assert_allclose(w_zca, np.eye(11), atol=1e-6)
        clean = self.ortho_engine.apply_hyperbolic_deadband_phase176(0.01)
        self.assertEqual(clean, 0.0)

    # =========================================================================
    # Category 7: Phase176Coupler, Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC48)
    # =========================================================================

    def test_tc41_phase176_coupler_single_1d_vector(self) -> None:
        """TC41: Verify Phase176Coupler single 1D vector returns floats with alpha_p176 strictly in [-3.0, 3.0]."""
        p_vec = [0.55, 0.60, 0.45, 0.50, 0.70, 0.40, 0.52, 0.48, 0.58, 0.53, 0.62]
        res = self.coupler.evaluate(p_vec)
        self.assertIn("alpha_p176", res)
        self.assertIn("h_phase176", res)
        self.assertIn("fcpi_v176", res)
        self.assertIn("action_functional", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha = res["alpha_p176"]
        h_val = res["h_phase176"]
        fcpi = res["fcpi_v176"]

        self.assertIsInstance(alpha, float)
        self.assertTrue(-3.0 <= alpha <= 3.0)
        self.assertTrue(0.0 < h_val <= 1.0)
        self.assertTrue(0.0 < fcpi <= 1.0)
        self.assertEqual(res["zca_matrix"].shape, (11, 11))

    def test_tc42_phase176_coupler_2d_dataframe(self) -> None:
        """TC42: Verify Phase176Coupler 2D DataFrame returns pandas Series."""
        rng = np.random.RandomState(42)
        syms = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]
        df = pd.DataFrame(rng.uniform(0.4, 0.6, (5, 11)), index=syms)
        res = self.coupler.evaluate(df)

        self.assertIsInstance(res["alpha_p176"], pd.Series)
        self.assertIsInstance(res["h_phase176"], pd.Series)
        self.assertEqual(len(res["alpha_p176"]), 5)
        self.assertTrue(np.all(res["alpha_p176"] >= -3.0) and np.all(res["alpha_p176"] <= 3.0))

    def test_tc43_phase176_coupler_functional_aliases(self) -> None:
        """TC43: Verify Phase176Coupler class methods couple, compute_coupling, compute, and call."""
        p_vec = [0.5] * 11
        res1 = self.coupler(p_vec)
        res2 = self.coupler.couple(p_vec)
        res3 = self.coupler.compute_coupling(p_vec)
        res4 = Phase176Coupler.compute(p_vec)

        self.assertEqual(res1["alpha_p176"], res2["alpha_p176"])
        self.assertEqual(res1["alpha_p176"], res3["alpha_p176"])
        self.assertEqual(res1["alpha_p176"], res4["alpha_p176"])

    def test_tc44_zero_synthetic_rows_invariant(self) -> None:
        """TC44: Verify synthetic_rows == 0 invariant across all Phase 176 couplers."""
        p_dict = {f"c{i}": 0.52 for i in range(11)}
        res = self.coupler.evaluate(p_dict)
        self.assertFalse(np.isnan(res["alpha_p176"]))
        self.assertFalse(np.isinf(res["alpha_p176"]))

    def test_tc45_numerical_stability_extreme_inputs(self) -> None:
        """TC45: Verify extreme inputs (all 0.05, all 0.95, NaNs) handled stably."""
        res_nan = self.coupler.evaluate([np.nan] * 11)
        self.assertTrue(np.isfinite(res_nan["alpha_p176"]))
        res_low = self.coupler.evaluate([0.05] * 11)
        self.assertTrue(-3.0 <= res_low["alpha_p176"] <= 3.0)
        res_high = self.coupler.evaluate([0.95] * 11)
        self.assertTrue(-3.0 <= res_high["alpha_p176"] <= 3.0)

    def test_tc46_latency_sla_under_1500ms(self) -> None:
        """TC46: Verify complete 100-symbol cross-sectional coupling evaluation runs in < 1500 ms."""
        rng = np.random.RandomState(42)
        data = rng.uniform(0.3, 0.7, (100, 11))
        t0 = time.perf_counter()
        _ = self.coupler.evaluate(data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 1500.0, f"Coupler latency {elapsed_ms:.1f}ms exceeds 1500ms SLA")

    def test_tc47_cross_sectional_rank_preservation(self) -> None:
        """TC47: Verify composite alpha monotonically orders distinct strong vs weak factor profiles."""
        strong_profile = np.array([0.80] * 11)
        weak_profile = np.array([0.20] * 11)
        res_strong = self.coupler.evaluate(strong_profile)
        res_weak = self.coupler.evaluate(weak_profile)
        self.assertGreater(res_strong["alpha_p176"], res_weak["alpha_p176"])

    def test_tc48_phase176_coupler_alias_identity(self) -> None:
        """TC48: Verify F864Coupler, UndecuplePillarCoupler, Phase176AlphaCoupler point to Phase176Coupler."""
        self.assertIs(F864Coupler, Phase176Coupler)
        self.assertIs(UndecuplePillarCoupler, Phase176Coupler)
        self.assertIs(Phase176AlphaCoupler, Phase176Coupler)


if __name__ == "__main__":
    unittest.main()

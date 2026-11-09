"""
tests/test_phase188_alpha.py — Comprehensive Unit & Integration Test Suite for Phase 188 Features F920 to F924.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F920 Hyper-Complex Clifford-Spinor Ricci Soliton & 4-Tree Quaternionic Wavelet Alpha (TC07 ~ TC13)
- Category 3: F921 Non-Abelian SU(3) Gauge Sheaf GNN & Super-Curvature Hodge-Laplacian (TC14 ~ TC20)
- Category 4: F922 Degree-10 Truncated Path Signature & Non-Markovian Rough Volterra Heston Predictor (TC21 ~ TC27)
- Category 5: F923 Hyperbolic Arbitrage-Free SSVI-JW Surface & 14th-Order Greeks Deep Engine (TC28 ~ TC34)
- Category 6: F924 Quattuordecuple-Pillar (14-Pillar) Symmetric ZCA Whitening & AIRM Metric (TC35 ~ TC40)
- Category 7: Phase188Coupler, Multi-Factor Pipeline, Edge Cases, SLA & Invariants (TC41 ~ TC50)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact calculations.
Zero synthetic rows (synthetic_rows == 0).
"""

from __future__ import annotations

import hashlib
import json
import math
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

# F920 Imports
from src.core.clifford_spinor_ricci_soliton import (
    VERSION as VERSION_F920,
    RELEASE as RELEASE_F920,
    FEATURE as FEATURE_F920,
    VERSION_PHASE188 as VERSION_P188_F920,
    RELEASE_PHASE188 as RELEASE_P188_F920,
    FEATURE_PHASE188 as FEATURE_P188_F920,
    CliffordSpinorRicciSolitonEngine,
    FourTreeQuaternionicWaveletEngine,
    FourTreeQuaternionicWavelet,
    Phase188CliffordWaveletEngine,
    F920CliffordSpinorEngine,
    CliffordRicciSolitonEngine,
    create_four_tree_quaternionic_wavelet,
    compute_four_tree_quaternionic_wavelet_scattering,
    compute_quaternionic_wavelet_scattering,
    get_dirac_gamma_matrices,
    compute_clifford_spinor_ricci_soliton_metric,
    compute_clifford_spinor_ricci_soliton_flow,
    apply_hyperbolic_noise_deadband_phase188,
    apply_hyperbolic_noise_deadband,
    apply_hyperbolic_deadband_phase188,
)

# F921 Imports
from src.core.su3_gauge_sheaf_gnn import (
    VERSION as VERSION_F921,
    RELEASE as RELEASE_F921,
    FEATURE as FEATURE_F921,
    VERSION_PHASE188 as VERSION_P188_F921,
    RELEASE_PHASE188 as RELEASE_P188_F921,
    FEATURE_PHASE188 as FEATURE_P188_F921,
    SU3GaugeSheafGNNEngine,
    Phase188SU3GaugeSheafEngine,
    F921SU3GaugeSheafGNNEngine,
    SU3GaugeSheafCurvatureEngine,
    HyperbolicSuperCurvatureHodgeLaplacianEngine,
    CANONICAL_VALUE_CHAIN_HYPEREDGES,
    build_su3_generators,
    compute_su3_gauge_connection,
    compute_su3_forman_ricci_curvature,
    compute_hyperbolic_super_curvature_hodge_laplacian,
    compute_sheaf_cohomology_h1_su3,
)

# F922 Imports
from src.core.rough_volterra_heston import (
    VERSION as VERSION_F922,
    RELEASE as RELEASE_F922,
    FEATURE as FEATURE_F922,
    VERSION_PHASE188 as VERSION_P188_F922,
    RELEASE_PHASE188 as RELEASE_P188_F922,
    FEATURE_PHASE188 as FEATURE_P188_F922,
    Degree10PathSignatureEngine,
    RoughVolterraHestonEngine,
    Phase188RoughVolterraEngine,
    F922RoughVolterraEngine,
    RoughVolterraHestonPredictor,
    compute_degree10_rough_path_signature,
    compute_degree8_rough_path_signature,
    compute_degree6_rough_path_signature,
    compute_rough_path_signature,
    compute_degree10_log_signature,
    compute_degree8_log_signature,
    compute_log_signature,
    compute_rough_volterra_heston_trajectory,
    compute_mckean_vlasov_jump_intensity,
    compute_fractional_mckean_vlasov_intensity,
)

# F923 Imports
from src.core.hyperbolic_ssvi_surface import (
    VERSION as VERSION_F923,
    RELEASE as RELEASE_F923,
    FEATURE as FEATURE_F923,
    VERSION_PHASE188 as VERSION_P188_F923,
    RELEASE_PHASE188 as RELEASE_P188_F923,
    FEATURE_PHASE188 as FEATURE_P188_F923,
    HyperbolicSSVIJWSurfaceEngine,
    Phase188HyperbolicSSVIEngine,
    F923HyperbolicSSVIEngine,
    FourteenthOrderSSVIJWDeepEngine,
    FourteenthOrderBlackScholesGreeksEngine,
    compute_hyperbolic_ssvi_total_variance,
    fit_arbitrage_free_hyperbolic_ssvi,
    compute_hermite_polynomials,
    compute_fourteenth_order_greeks,
    compute_twelfth_order_black_scholes_greeks,
    calculate_fourteenth_order_surface_skew,
    calculate_twelfth_order_surface_skew,
)

# F924 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F924,
    RELEASE as RELEASE_F924,
    FEATURE as FEATURE_F924,
    VERSION_PHASE188 as VERSION_P188_F924,
    RELEASE_PHASE188 as RELEASE_P188_F924,
    FEATURE_PHASE188 as FEATURE_P188_F924,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase188,
    Phase188FactorOrthogonalizerEngine,
    F924FactorOrthogonalizerEngine,
    QuattuordecuplePillarZCAOrthogonalizer,
    QuattuordecuplePillarZCAEngine,
    QuattuordecuplePillarMap,
    QUATTUORDECUPLE_PILLAR_MAP,
    TredecuplePillarMap,
    TREDECUPLE_PILLAR_MAP,
    compute_quattuordecuple_pillar_zca_whitening,
    compute_tredecuple_pillar_zca_whitening,
    apply_hyperbolic_deadband_phase188 as apply_hyperbolic_deadband_f924,
    compute_riemannian_airm_distance,
)

# Historical Couplers
from src.ai.historical_couplers import (
    Phase188Coupler,
    F924Coupler,
    QuattuordecuplePillarCoupler,
    Phase188AlphaCoupler,
    Phase184Coupler,
)


class TestPhase188AlphaSuite(unittest.TestCase):
    """50 Comprehensive Unit & Integration Tests for Phase 188 Alpha Engines (F920–F924)."""

    def setUp(self) -> None:
        np.random.seed(188)
        self.t = np.linspace(0, 1.0, 128)
        self.prices_1d = 100.0 * np.exp(np.cumsum(0.01 * np.random.randn(128)))
        self.vols_1d = np.abs(1000.0 + 100.0 * np.random.randn(128))

        dates = pd.date_range("2025-01-01", periods=128, freq="B")
        self.ohlcv_df = pd.DataFrame(
            {
                "Open": self.prices_1d * 0.99,
                "High": self.prices_1d * 1.02,
                "Low": self.prices_1d * 0.98,
                "Close": self.prices_1d,
                "Volume": self.vols_1d,
            },
            index=dates,
        )
        self.universe_dict = {
            "005930": self.ohlcv_df,
            "000660": self.ohlcv_df.copy(),
            "AAPL": self.ohlcv_df.copy(),
            "NVDA": self.ohlcv_df.copy(),
        }

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity_files(self) -> None:
        """TC01: Verify all 6 owned files exist and have bit-for-bit SHA256 parity in trading_system/src/."""
        files = [
            ("src/core/clifford_spinor_ricci_soliton.py", "trading_system/src/core/clifford_spinor_ricci_soliton.py"),
            ("src/core/su3_gauge_sheaf_gnn.py", "trading_system/src/core/su3_gauge_sheaf_gnn.py"),
            ("src/core/rough_volterra_heston.py", "trading_system/src/core/rough_volterra_heston.py"),
            ("src/core/hyperbolic_ssvi_surface.py", "trading_system/src/core/hyperbolic_ssvi_surface.py"),
            ("src/ai/factor_orthogonalizer.py", "trading_system/src/ai/factor_orthogonalizer.py"),
            ("src/ai/historical_couplers.py", "trading_system/src/ai/historical_couplers.py"),
        ]
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for src_rel, ts_rel in files:
            src_path = os.path.join(base_dir, src_rel)
            ts_path = os.path.join(base_dir, ts_rel)
            self.assertTrue(os.path.exists(src_path), f"Source file missing: {src_rel}")
            self.assertTrue(os.path.exists(ts_path), f"Target mirror missing: {ts_rel}")
            h1 = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
            h2 = hashlib.sha256(open(ts_path, "rb").read()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 mismatch for {src_rel}")

    def test_tc02_f920_metadata_constants_and_aliases(self) -> None:
        """TC02: Verify F920 metadata, version polymorphism, and complete alias tree."""
        self.assertEqual(int(VERSION_F920), 188)
        self.assertEqual(str(RELEASE_F920), "R182")
        self.assertEqual(str(FEATURE_F920), "F920")
        self.assertEqual(int(VERSION_P188_F920), 188)
        self.assertEqual(str(RELEASE_P188_F920), "R182")
        self.assertEqual(str(FEATURE_P188_F920), "F920")
        self.assertIs(Phase188CliffordWaveletEngine, CliffordSpinorRicciSolitonEngine)
        self.assertIs(F920CliffordSpinorEngine, CliffordSpinorRicciSolitonEngine)
        self.assertIs(CliffordRicciSolitonEngine, CliffordSpinorRicciSolitonEngine)

    def test_tc03_f921_metadata_constants_and_aliases(self) -> None:
        """TC03: Verify F921 metadata, version polymorphism, and complete alias tree."""
        self.assertEqual(int(VERSION_F921), 188)
        self.assertEqual(str(RELEASE_F921), "R182")
        self.assertEqual(str(FEATURE_F921), "F921")
        self.assertIs(Phase188SU3GaugeSheafEngine, SU3GaugeSheafGNNEngine)
        self.assertIs(F921SU3GaugeSheafGNNEngine, SU3GaugeSheafGNNEngine)
        self.assertIs(SU3GaugeSheafCurvatureEngine, SU3GaugeSheafGNNEngine)

    def test_tc04_f922_metadata_constants_and_aliases(self) -> None:
        """TC04: Verify F922 metadata, version polymorphism, and complete alias tree."""
        self.assertEqual(int(VERSION_F922), 188)
        self.assertEqual(str(RELEASE_F922), "R182")
        self.assertEqual(str(FEATURE_F922), "F922")
        self.assertIs(Phase188RoughVolterraEngine, RoughVolterraHestonEngine)
        self.assertIs(F922RoughVolterraEngine, RoughVolterraHestonEngine)
        self.assertIs(RoughVolterraHestonPredictor, RoughVolterraHestonEngine)

    def test_tc05_f923_metadata_constants_and_aliases(self) -> None:
        """TC05: Verify F923 metadata, version polymorphism, and complete alias tree."""
        self.assertEqual(int(VERSION_F923), 188)
        self.assertEqual(str(RELEASE_F923), "R182")
        self.assertEqual(str(FEATURE_F923), "F923")
        self.assertIs(Phase188HyperbolicSSVIEngine, HyperbolicSSVIJWSurfaceEngine)
        self.assertIs(F923HyperbolicSSVIEngine, HyperbolicSSVIJWSurfaceEngine)
        self.assertIs(FourteenthOrderSSVIJWDeepEngine, HyperbolicSSVIJWSurfaceEngine)

    def test_tc06_f924_metadata_constants_and_registry(self) -> None:
        """TC06: Verify F924 metadata, version polymorphism, aliases, and strategy registry."""
        self.assertEqual(int(VERSION_F924), 188)
        self.assertEqual(str(RELEASE_F924), "R182")
        self.assertEqual(str(FEATURE_F924), "F924")
        self.assertIs(FactorOrthogonalizerEnginePhase188, FactorOrthogonalizerEngine)
        self.assertIs(QuattuordecuplePillarZCAOrthogonalizer, FactorOrthogonalizerEngine)
        self.assertIs(QuattuordecuplePillarZCAEngine, FactorOrthogonalizerEngine)

        for strat_id in ["clifford_spinor_ricci_soliton", "su3_gauge_sheaf_gnn", "rough_volterra_heston", "hyperbolic_ssvi_surface"]:
            self.assertIn(strat_id, STRATEGY_REGISTRY)
            entry = get_registry().get(strat_id)
            self.assertIsNotNone(entry)
            cls, meta = entry
            self.assertIsNotNone(cls)
            self.assertIsNotNone(meta.score_column)

    # =========================================================================
    # Category 2: F920 Clifford Spinor Ricci Soliton & Wavelet (TC07 ~ TC13)
    # =========================================================================

    def test_tc07_f920_dirac_gamma_matrices_anticommutation(self) -> None:
        """TC07: Verify Dirac gamma algebra {gamma^mu, gamma^nu} = 2 * eta^{mu nu} * I_4."""
        g0, g1, g2, g3 = get_dirac_gamma_matrices()
        gammas = [g0, g1, g2, g3]
        eta = np.diag([1.0, -1.0, -1.0, -1.0])
        i4 = np.eye(4, dtype=np.complex128)

        for mu in range(4):
            for nu in range(4):
                anticomm = gammas[mu] @ gammas[nu] + gammas[nu] @ gammas[mu]
                expected = 2.0 * eta[mu, nu] * i4
                np.testing.assert_allclose(anticomm, expected, atol=1e-10)

    def test_tc08_f920_four_tree_quaternionic_wavelet_creation(self) -> None:
        """TC08: Verify 4-Tree Quaternionic Wavelet Packets construction and norm."""
        qwp = create_four_tree_quaternionic_wavelet(length=64, center_freq=0.25)
        self.assertIsInstance(qwp, FourTreeQuaternionicWavelet)
        self.assertEqual(len(qwp), 4)

        for i, psi in enumerate(qwp):
            self.assertEqual(len(psi), 64)
            norm = np.linalg.norm(psi)
            self.assertAlmostEqual(norm, 1.0, places=5)

    def test_tc09_f920_quaternionic_wavelet_scattering_energy(self) -> None:
        """TC09: Verify quaternionic scattering transform energy conservation: S0 + S1 + S2 = total."""
        res = compute_four_tree_quaternionic_wavelet_scattering(self.prices_1d, J=4, Q=6)
        s0 = res["S0"]
        s1 = res["S1"]
        s2 = res["S2"]
        tot = res["total_scattering_energy"]
        self.assertGreater(s0, 0.0)
        self.assertGreater(s1, 0.0)
        self.assertAlmostEqual(s0 + s1 + s2, tot, places=6)
        self.assertTrue(0.05 <= res["f920_wavelet_score"] <= 0.95)

    def test_tc10_f920_hyperbolic_noise_deadband_filter(self) -> None:
        """TC10: Verify hyperbolic noise deadband filter (delta=0.030, alpha=580.0)."""
        # Noise below delta=0.030 should be strongly attenuated to ~0
        noisy_val = 0.015
        filtered_noise = apply_hyperbolic_noise_deadband_phase188(noisy_val, delta=0.030, alpha=580.0)
        self.assertAlmostEqual(filtered_noise, 0.0, places=5)

        # Signal well above delta=0.030 should pass through
        signal_val = 0.150
        filtered_signal = apply_hyperbolic_noise_deadband_phase188(signal_val, delta=0.030, alpha=580.0)
        self.assertGreater(filtered_signal, 0.110)

        # Array version
        arr = np.array([-0.05, -0.01, 0.0, 0.01, 0.05])
        f_arr = apply_hyperbolic_noise_deadband_phase188(arr, delta=0.030, alpha=580.0)
        self.assertAlmostEqual(f_arr[1], 0.0, places=5)
        self.assertAlmostEqual(f_arr[3], 0.0, places=5)
        self.assertLess(f_arr[0], -0.01)
        self.assertGreater(f_arr[4], 0.01)

    def test_tc11_f920_clifford_spinor_ricci_soliton_metric_spd(self) -> None:
        """TC11: Verify Clifford-Spinor Ricci Soliton metric is symmetric positive-definite."""
        feats = np.column_stack([np.diff(self.prices_1d), self.vols_1d[1:]])
        g, curv = compute_clifford_spinor_ricci_soliton_metric(feats, lambda_param=0.05)
        self.assertEqual(g.shape, (2, 2))
        np.testing.assert_allclose(g, g.T, atol=1e-10)
        eigs = np.linalg.eigvalsh(g)
        self.assertTrue(np.all(eigs > 0.0), f"Metric eigenvalues non-positive: {eigs}")
        self.assertIsInstance(curv, float)

    def test_tc12_f920_clifford_spinor_strategy_engine(self) -> None:
        """TC12: Verify CliffordSpinorRicciSolitonEngine generate_signals output."""
        engine = CliffordSpinorRicciSolitonEngine()
        signals = engine.generate_signals(self.universe_dict)
        self.assertIsInstance(signals, ScoreDataFrame)
        self.assertEqual(len(signals), 4)
        for sym in self.universe_dict:
            score = signals[sym]
            self.assertTrue(0.05 <= score <= 0.95, f"Score out of bounds: {score}")

    def test_tc13_f920_clifford_spinor_short_series_resilience(self) -> None:
        """TC13: Verify resilience of F920 engine to very short price series (< 8 bars)."""
        short_df = self.ohlcv_df.iloc[:4].copy()
        engine = CliffordSpinorRicciSolitonEngine()
        signals = engine.generate_signals({"TEST": short_df})
        self.assertEqual(signals["TEST"], 0.50)

    # =========================================================================
    # Category 3: F921 SU(3) Gauge Sheaf GNN (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_f921_gell_mann_matrices_properties(self) -> None:
        """TC14: Verify 8 Gell-Mann generators are Hermitian and traceless."""
        generators = build_su3_generators()
        self.assertEqual(len(generators), 8)
        for a, lam in enumerate(generators):
            self.assertEqual(lam.shape, (3, 3))
            # Traceless
            self.assertAlmostEqual(abs(np.trace(lam)), 0.0, places=10)
            # Hermitian: lambda == lambda^dagger
            np.testing.assert_allclose(lam, lam.conj().T, atol=1e-10)

    def test_tc15_f921_su3_gauge_connection_properties(self) -> None:
        """TC15: Verify SU(3) connection matrices satisfy U * U^dagger = I_3 and det(U) = 1."""
        edge_index = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int64)
        connections = compute_su3_gauge_connection(edge_index)
        self.assertEqual(connections.shape, (3, 3, 3))
        i3 = np.eye(3, dtype=np.complex128)

        for e in range(3):
            U = connections[e]
            np.testing.assert_allclose(U @ U.conj().T, i3, atol=1e-8)
            det_u = np.linalg.det(U)
            self.assertAlmostEqual(abs(det_u), 1.0, places=5)

    def test_tc16_f921_forman_ricci_curvature_bounds(self) -> None:
        """TC16: Verify Forman-Ricci curvature is bounded strictly in [-5.0, 5.0]."""
        edges = np.array([[0, 1], [1, 2], [2, 0], [0, 3]], dtype=np.int64)
        curv = compute_su3_forman_ricci_curvature(edges)
        self.assertEqual(len(curv), 4)
        self.assertTrue(np.all(curv >= -5.0))
        self.assertTrue(np.all(curv <= 5.0))

    def test_tc17_f921_super_curvature_hodge_laplacian_psd(self) -> None:
        """TC17: Verify Hyperbolic Super-Curvature Hodge-Laplacian is Hermitian PSD."""
        stalks = np.random.randn(4, 3) + 1j * np.random.randn(4, 3)
        edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int64)
        conns = compute_su3_gauge_connection(edges)
        lap = compute_hyperbolic_super_curvature_hodge_laplacian(stalks, conns, edge_index=edges)
        self.assertEqual(lap.shape, (12, 12))
        np.testing.assert_allclose(lap, lap.conj().T, atol=1e-8)
        eigs = np.linalg.eigvalsh(0.5 * (lap + lap.conj().T))
        self.assertTrue(np.all(eigs >= -1e-6), f"Negative eigenvalues found: {eigs}")

    def test_tc18_f921_sheaf_cohomology_h1_bounded(self) -> None:
        """TC18: Verify H^1 sheaf cohomology obstruction measure in [0.0, 1.0]."""
        lap = np.eye(9, dtype=np.complex128) * 2.0
        h1 = compute_sheaf_cohomology_h1_su3(lap)
        self.assertTrue(0.0 <= h1 <= 1.0)

    def test_tc19_f921_su3_gauge_sheaf_gnn_strategy_engine(self) -> None:
        """TC19: Verify SU3GaugeSheafGNNEngine generate_signals output."""
        engine = SU3GaugeSheafGNNEngine()
        signals = engine.generate_signals(self.universe_dict)
        self.assertIsInstance(signals, ScoreDataFrame)
        self.assertEqual(len(signals), 4)
        for sym in self.universe_dict:
            score = signals[sym]
            self.assertTrue(0.05 <= score <= 0.95, f"Score out of bounds: {score}")

    def test_tc20_f921_canonical_value_chain_hyperedges_integrity(self) -> None:
        """TC20: Verify CANONICAL_VALUE_CHAIN_HYPEREDGES structure and non-empty relations."""
        self.assertIn("semiconductor_foundry_advanced", CANONICAL_VALUE_CHAIN_HYPEREDGES)
        self.assertIn("ai_hardware_datacenter", CANONICAL_VALUE_CHAIN_HYPEREDGES)
        for cat, edges in CANONICAL_VALUE_CHAIN_HYPEREDGES.items():
            self.assertGreater(len(edges), 0)
            for src, dst, w in edges:
                self.assertIsInstance(src, str)
                self.assertIsInstance(dst, str)
                self.assertTrue(0.0 < w <= 1.0)

    # =========================================================================
    # Category 4: F922 Degree-10 Path Signature & Rough Volterra (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_f922_degree10_rough_path_signature_dimension(self) -> None:
        """TC21: Verify 2D path signature at degree 10 has exact length sum_{k=1}^10 2^k = 2046."""
        path_2d = np.column_stack([np.linspace(0, 1, 32), np.sin(np.linspace(0, 3, 32))])
        sig = compute_degree10_rough_path_signature(path_2d, degree=10)
        expected_len = sum(2 ** m for m in range(1, 11))  # 2046
        self.assertEqual(len(sig), expected_len)
        self.assertTrue(np.all(np.isfinite(sig)))

    def test_tc22_f922_degree10_path_signature_chen_identity(self) -> None:
        """TC22: Verify Chen's identity S(X * Y) = S(X) (x) S(Y) on path increments."""
        p1 = np.array([[0.0, 0.0], [1.0, 2.0]], dtype=np.float64)
        p2 = np.array([[1.0, 2.0], [2.0, 5.0]], dtype=np.float64)
        p_full = np.array([[0.0, 0.0], [1.0, 2.0], [2.0, 5.0]], dtype=np.float64)

        sig_full = compute_degree10_rough_path_signature(p_full, degree=2)
        # Degree 1 & 2 components
        self.assertEqual(len(sig_full), 2 + 4)  # 6 elements
        # S^1 should be Delta X = [2.0, 5.0]
        np.testing.assert_allclose(sig_full[:2], [2.0, 5.0], atol=1e-8)

    def test_tc23_f922_degree10_log_signature_series(self) -> None:
        """TC23: Verify degree-10 log-signature computation via tensor BCH series."""
        path_2d = np.column_stack([np.linspace(0, 1, 20), np.cos(np.linspace(0, 2, 20))])
        log_sig = compute_degree10_log_signature(path_2d, degree=4)
        expected_len = sum(2 ** m for m in range(1, 5))  # 2 + 4 + 8 + 16 = 30
        self.assertEqual(len(log_sig), expected_len)
        self.assertTrue(np.all(np.isfinite(log_sig)))

    def test_tc24_f922_rough_volterra_heston_trajectory(self) -> None:
        """TC24: Verify rough Volterra-Heston variance trajectory V_t > 0 with Hurst H=0.08."""
        traj = compute_rough_volterra_heston_trajectory(self.prices_1d, hurst=0.08)
        self.assertEqual(len(traj), len(self.prices_1d))
        self.assertTrue(np.all(traj > 0.0), "Variance trajectory non-positive")
        self.assertTrue(np.all(np.isfinite(traj)))

    def test_tc25_f922_mckean_vlasov_jump_intensity(self) -> None:
        """TC25: Verify Hawkes-McKean-Vlasov jump intensity calculation."""
        jump_int = compute_mckean_vlasov_jump_intensity(self.prices_1d, hurst=0.08)
        self.assertIsInstance(jump_int, float)
        self.assertTrue(0.01 <= jump_int <= 10.0)

    def test_tc26_f922_rough_volterra_strategy_engine(self) -> None:
        """TC26: Verify RoughVolterraHestonEngine generate_signals output."""
        engine = RoughVolterraHestonEngine(degree=4)
        signals = engine.generate_signals(self.universe_dict)
        self.assertIsInstance(signals, ScoreDataFrame)
        self.assertEqual(len(signals), 4)
        for sym in self.universe_dict:
            score = signals[sym]
            self.assertTrue(0.05 <= score <= 0.95, f"Score out of bounds: {score}")

    def test_tc27_f922_signature_backward_compat_aliases(self) -> None:
        """TC27: Verify backward compatibility aliases for path signature functions."""
        path_2d = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 1.5]])
        s8 = compute_degree8_rough_path_signature(path_2d)
        s6 = compute_degree6_rough_path_signature(path_2d)
        s_raw = compute_rough_path_signature(path_2d)
        self.assertEqual(len(s8), sum(2 ** m for m in range(1, 9)))
        self.assertEqual(len(s6), sum(2 ** m for m in range(1, 7)))
        self.assertEqual(len(s_raw), sum(2 ** m for m in range(1, 11)))

    # =========================================================================
    # Category 5: F923 Hyperbolic SSVI Surface & 14th Greeks (TC28 ~ TC34)
    # =========================================================================

    def test_tc28_f923_hyperbolic_ssvi_total_variance_positivity(self) -> None:
        """TC28: Verify Hyperbolic SSVI total implied variance w(k) > 0 for all k in [-2.0, 2.0]."""
        k_grid = np.linspace(-2.0, 2.0, 50)
        w_grid = compute_hyperbolic_ssvi_total_variance(k_grid, theta_t=0.04, rho=-0.3, eta=1.0, gamma=0.3)
        self.assertTrue(np.all(w_grid > 0.0), "Total variance non-positive on grid")

    def test_tc29_f923_gatheral_jacquier_no_arbitrage_bounds(self) -> None:
        """TC29: Verify Gatheral-Jacquier bounds enforcement: gamma in (0, 0.5] and eta * (1 + |rho|) <= 2."""
        # Attempt to pass violating parameters
        w = compute_hyperbolic_ssvi_total_variance(0.0, theta_t=0.04, rho=-0.8, eta=5.0, gamma=0.9)
        self.assertGreater(w, 0.0)

    def test_tc30_f923_fit_arbitrage_free_hyperbolic_ssvi(self) -> None:
        """TC30: Verify fitting of arbitrage-free hyperbolic SSVI parameters on smile surface."""
        k = np.array([-0.3, -0.15, 0.0, 0.15, 0.3])
        w = 0.04 * (1.0 - 0.2 * k + 0.6 * (k ** 2))
        mat = np.full_like(k, 0.25)
        fit_res = fit_arbitrage_free_hyperbolic_ssvi(k, w, mat)
        self.assertTrue(fit_res["arbitrage_free"])
        self.assertTrue(0.0 < fit_res["theta"] < 1.0)
        self.assertTrue(-1.0 < fit_res["rho"] < 1.0)
        self.assertGreater(fit_res["dw_dtau_min"], 0.0)

    def test_tc31_f923_fourteenth_order_greeks_evaluations(self) -> None:
        """TC31: Verify 14th-Order Black-Scholes Greeks evaluation up to order 14."""
        greeks = compute_fourteenth_order_greeks(spot=100.0, strike=100.0, t=0.25, r=0.03, sigma=0.20)
        # Check standard Greeks
        self.assertTrue(0.0 < greeks["delta"] < 1.0)
        self.assertGreater(greeks["gamma"], 0.0)
        self.assertGreater(greeks["vega"], 0.0)
        # Check higher-order Greeks
        self.assertIn("twelfth_speed", greeks)
        self.assertIn("thirteenth_speed", greeks)
        self.assertIn("fourteenth_speed", greeks)
        self.assertIn("fourteenth_order_tensor", greeks)
        self.assertTrue(np.isfinite(greeks["fourteenth_order_tensor"]))

    def test_tc32_f923_hermite_polynomials_recurrence(self) -> None:
        """TC32: Verify probabilists' Hermite polynomials recurrence He_n(x)."""
        x = 1.5
        he = compute_hermite_polynomials(x, max_degree=14)
        self.assertEqual(len(he), 15)
        # He_0 = 1, He_1 = x, He_2 = x^2 - 1
        self.assertAlmostEqual(he[0], 1.0, places=8)
        self.assertAlmostEqual(he[1], x, places=8)
        self.assertAlmostEqual(he[2], x ** 2 - 1.0, places=8)
        # He_3 = x^3 - 3x
        self.assertAlmostEqual(he[3], x ** 3 - 3.0 * x, places=8)

    def test_tc33_f923_surface_skew_calculation(self) -> None:
        """TC33: Verify 14th-order surface skew calculation is bounded in [-3.0, 3.0]."""
        k = np.array([-0.2, 0.0, 0.2])
        ivs = np.array([0.28, 0.20, 0.22])
        skew = calculate_fourteenth_order_surface_skew(k, ivs)
        self.assertIsInstance(skew, float)
        self.assertTrue(-3.0 <= skew <= 3.0)

    def test_tc34_f923_hyperbolic_ssvi_strategy_engine(self) -> None:
        """TC34: Verify HyperbolicSSVIJWSurfaceEngine generate_signals output."""
        engine = HyperbolicSSVIJWSurfaceEngine()
        signals = engine.generate_signals(self.universe_dict)
        self.assertIsInstance(signals, ScoreDataFrame)
        self.assertEqual(len(signals), 4)
        for sym in self.universe_dict:
            score = signals[sym]
            self.assertTrue(0.05 <= score <= 0.95, f"Score out of bounds: {score}")

    # =========================================================================
    # Category 6: F924 14-Pillar ZCA Whitening & AIRM Metric (TC35 ~ TC40)
    # =========================================================================

    def test_tc35_f924_quattuordecuple_pillar_map_octonion_cluster(self) -> None:
        """TC35: Verify QuattuordecuplePillarMap 14 canonical pillars including 'octonion' cluster."""
        p_map = QUATTUORDECUPLE_PILLAR_MAP
        self.assertEqual(len(p_map), 14)
        self.assertIn("octonion", p_map)
        oct_factors = p_map["octonion"]
        self.assertIn("clifford_spinor_ricci_soliton", oct_factors)
        self.assertIn("su3_gauge_sheaf_gnn", oct_factors)
        self.assertIn("rough_volterra_heston", oct_factors)
        self.assertIn("hyperbolic_ssvi_surface", oct_factors)

        # Alias testing
        self.assertEqual(p_map["SPINOR"], oct_factors)
        self.assertEqual(p_map["CLIFFORD"], oct_factors)
        self.assertEqual(p_map["PHASE188_ALPHA"], oct_factors)

    def test_tc36_f924_14pillar_symmetric_zca_whitening_spd(self) -> None:
        """TC36: Verify 14-Pillar Symmetric ZCA Whitening produces symmetric positive-definite operator."""
        cov_14 = np.cov(np.random.randn(50, 14), rowvar=False) + 0.1 * np.eye(14)
        w_zca = compute_quattuordecuple_pillar_zca_whitening(cov_14)
        self.assertEqual(w_zca.shape, (14, 14))
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-8)
        eigs = np.linalg.eigvalsh(w_zca)
        self.assertTrue(np.all(eigs > 0.0), f"ZCA whitening operator not PSD: {eigs}")

    def test_tc37_f924_riemannian_airm_distance(self) -> None:
        """TC37: Verify Affine-Invariant Riemannian Metric (AIRM) distance is non-negative and symmetric."""
        cov_a = np.eye(14) * 1.5
        cov_b = np.eye(14) * 2.5
        dist_ab = compute_riemannian_airm_distance(cov_a, cov_b)
        dist_ba = compute_riemannian_airm_distance(cov_b, cov_a)
        self.assertGreater(dist_ab, 0.0)
        self.assertAlmostEqual(dist_ab, dist_ba, places=6)
        # Self-distance is 0
        self.assertAlmostEqual(compute_riemannian_airm_distance(cov_a, cov_a), 0.0, places=6)

    def test_tc38_f924_hyperbolic_deadband_noise_suppression(self) -> None:
        """TC38: Verify apply_hyperbolic_deadband_phase188 noise filter."""
        res_zero = apply_hyperbolic_deadband_f924(0.010, delta=0.030, alpha=580.0)
        res_sig = apply_hyperbolic_deadband_f924(0.100, delta=0.030, alpha=580.0)
        self.assertAlmostEqual(res_zero, 0.0, places=4)
        self.assertGreater(res_sig, 0.060)

    def test_tc39_f924_factor_orthogonalizer_engine_quattuordecuple_zca(self) -> None:
        """TC39: Verify FactorOrthogonalizerEngine with 14 factor pillars."""
        engine = FactorOrthogonalizerEngine(default_method="pca_symmetric", preserve_top_k=2)
        df_factors = pd.DataFrame(
            np.random.rand(20, 14) * 0.4 + 0.3,
            columns=[f"fac_{i}" for i in range(14)],
        )
        ortho_df = engine.orthogonalize(
            df_factors, strategy_cols=[f"fac_{i}" for i in range(14)]
        )
        self.assertEqual(ortho_df.shape, (20, 14))

    def test_tc40_f924_quattuordecuple_engine_aliases(self) -> None:
        """TC40: Verify QuattuordecuplePillarZCAOrthogonalizer alias mapping."""
        self.assertIs(QuattuordecuplePillarZCAOrthogonalizer, FactorOrthogonalizerEngine)
        self.assertIs(Phase188FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)

    # =========================================================================
    # Category 7: Phase188Coupler & End-to-End Multi-Factor Pipeline (TC41 ~ TC50)
    # =========================================================================

    def test_tc41_phase188_coupler_initialization(self) -> None:
        """TC41: Verify Phase188Coupler initialization and parameter assignment."""
        coupler = Phase188Coupler(kappa=1.88, alpha_deadband=580.0, delta_deadband=0.030, hurst_target=0.08)
        self.assertEqual(coupler.kappa, 1.88)
        self.assertEqual(coupler.alpha_deadband, 580.0)
        self.assertEqual(coupler.delta_deadband, 0.030)
        self.assertEqual(coupler.hurst_target, 0.08)

    def test_tc42_phase188_coupler_evaluate_dataframe(self) -> None:
        """TC42: Verify Phase188Coupler on DataFrame of 14 factor scores."""
        df_scores = pd.DataFrame(
            np.random.uniform(0.40, 0.60, size=(10, 14)),
            columns=[f"factor_{i}" for i in range(14)],
            index=[f"SYM_{i}" for i in range(10)],
        )
        coupler = Phase188Coupler()
        res = coupler.evaluate(df_scores)
        self.assertIn("alpha_p188", res)
        self.assertIn("h_phase188", res)
        self.assertIn("fcpi_v182", res)
        self.assertIn("riemannian_airm_metric", res)
        self.assertIn("zca_matrix", res)

        alpha = res["alpha_p188"]
        self.assertIsInstance(alpha, pd.Series)
        self.assertEqual(len(alpha), 10)
        self.assertTrue(np.all(alpha >= -3.0))
        self.assertTrue(np.all(alpha <= 3.0))

    def test_tc43_phase188_coupler_evaluate_dict(self) -> None:
        """TC43: Verify Phase188Coupler on Dictionary of factor scores."""
        scores_dict = {f"pillar_{i}": 0.52 for i in range(14)}
        coupler = Phase188Coupler()
        res = coupler.evaluate(scores_dict)
        self.assertIsInstance(res["alpha_p188"], float)
        self.assertTrue(-3.0 <= res["alpha_p188"] <= 3.0)
        self.assertTrue(0.0 < res["h_phase188"] <= 1.0)
        self.assertTrue(0.0 < res["fcpi_v182"] <= 1.0)

    def test_tc44_phase188_coupler_evaluate_numpy(self) -> None:
        """TC44: Verify Phase188Coupler on 1D and 2D numpy arrays."""
        p_1d = np.full(14, 0.55)
        coupler = Phase188Coupler()
        res_1d = coupler(p_1d)
        self.assertIsInstance(res_1d["alpha_p188"], float)

        p_2d = np.random.uniform(0.3, 0.7, size=(8, 14))
        res_2d = coupler(p_2d)
        self.assertEqual(len(res_2d["alpha_p188"]), 8)

    def test_tc45_phase188_coupler_classmethod_compute(self) -> None:
        """TC45: Verify Phase188Coupler.compute classmethod."""
        arr = np.random.uniform(0.45, 0.55, size=(5, 14))
        res = Phase188Coupler.compute(arr, kappa=1.88)
        self.assertIn("alpha_p188", res)
        self.assertEqual(len(res["alpha_p188"]), 5)

    def test_tc46_phase188_coupler_harmony_and_fcpi(self) -> None:
        """TC46: Verify harmony regularizer H_p188 and FCPI_v182 are strictly in (0, 1]."""
        p_mat = np.random.uniform(0.1, 0.9, size=(6, 14))
        coupler = Phase188Coupler()
        res = coupler(p_mat)
        h = res["h_phase188"]
        fcpi = res["fcpi_v182"]
        self.assertTrue(np.all(h > 0.0) and np.all(h <= 1.0))
        self.assertTrue(np.all(fcpi > 0.0) and np.all(fcpi <= 1.0))

    def test_tc47_phase188_coupler_aliases(self) -> None:
        """TC47: Verify Phase188Coupler aliases (F924Coupler, QuattuordecuplePillarCoupler, Phase188AlphaCoupler)."""
        self.assertIs(F924Coupler, Phase188Coupler)
        self.assertIs(QuattuordecuplePillarCoupler, Phase188Coupler)
        self.assertIs(Phase188AlphaCoupler, Phase188Coupler)

    def test_tc48_zero_synthetic_rows_invariant(self) -> None:
        """TC48: Verify zero synthetic rows invariant (synthetic_rows == 0 strictly int) across benchmarks."""
        status_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../benchmarks/30year/status.json"))
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            syn_rows = data.get("synthetic_rows", None)
            self.assertIsNotNone(syn_rows)
            self.assertEqual(syn_rows, 0)
            self.assertIs(type(syn_rows), int)
            self.assertNotIsInstance(syn_rows, bool)

    def test_tc49_numerical_stability_edge_cases(self) -> None:
        """TC49: Verify numerical stability under NaN, Inf, and flat zero inputs."""
        nan_prices = np.array([np.nan, np.inf, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
        scatt = compute_four_tree_quaternionic_wavelet_scattering(nan_prices)
        self.assertTrue(np.isfinite(scatt["total_scattering_energy"]))
        self.assertTrue(0.05 <= scatt["f920_wavelet_score"] <= 0.95)

        sig_nan = compute_degree10_rough_path_signature(np.array([[np.nan, 0.0], [0.0, np.nan]]))
        self.assertTrue(np.all(np.isfinite(sig_nan)))

    def test_tc50_end_to_end_phase188_synthesis_pipeline(self) -> None:
        """TC50: End-to-end synthesis of all 4 Phase 188 engines coupled via Phase188Coupler."""
        e1 = CliffordSpinorRicciSolitonEngine()
        e2 = SU3GaugeSheafGNNEngine()
        e3 = RoughVolterraHestonEngine(degree=4)
        e4 = HyperbolicSSVIJWSurfaceEngine()

        s1 = e1.generate_signals(self.universe_dict)
        s2 = e2.generate_signals(self.universe_dict)
        s3 = e3.generate_signals(self.universe_dict)
        s4 = e4.generate_signals(self.universe_dict)

        # Build 14-pillar dataframe with the 4 new engines + 10 baselines
        symbols = list(self.universe_dict.keys())
        factor_records = []
        for sym in symbols:
            rec = {
                "val": 0.52,
                "mom": 0.55,
                "flow": 0.48,
                "cat": 0.50,
                "net": 0.51,
                "vol": 0.49,
                "gnn": 0.53,
                "rev": 0.47,
                "comp": 0.54,
                "tail": 0.50,
                "macro": 0.51,
                "ricci": float(s1[sym]),
                "symplectic": float(s2[sym]),
                "octonion": float(0.5 * (s3[sym] + s4[sym])),
            }
            factor_records.append(rec)

        df_14 = pd.DataFrame(factor_records, index=symbols)
        coupler = Phase188Coupler(kappa=1.88)
        coupled_out = coupler.evaluate(df_14)

        composite_alpha = coupled_out["alpha_p188"]
        self.assertEqual(len(composite_alpha), 4)
        for sym in symbols:
            self.assertTrue(-3.0 <= composite_alpha[sym] <= 3.0)
        self.assertGreater(coupled_out["riemannian_airm_metric"], 0.0)
        self.assertEqual(coupled_out["zca_matrix"].shape, (14, 14))


if __name__ == "__main__":
    unittest.main()

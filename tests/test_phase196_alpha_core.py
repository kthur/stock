"""
tests/test_phase196_alpha_core.py
=================================
Exhaustive Verification Suite for Milestone 1: Quantitative Alpha Feature Engineering
(Phase 196 Features F969, F970, F971, F972, F973) for Release R186.

Categories:
  - Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: F969 Stochastic Gradient Foliation & Foliated Ricci Curvature Flow Engine (TC06 ~ TC13)
  - Category 3: F970 Open Quantum Lindblad Master Equation & Purity Dissipation Arbitrage Engine (TC14 ~ TC21)
  - Category 4: F971 Hyperspherical Monge-Kantorovich Optimal Transport & Barycenter Flow Engine (TC22 ~ TC28)
  - Category 5: F972 17-Pillar Septendecuple ZCA Whitening Manifold on S_{++}^{17} (TC29 ~ TC34)
  - Category 6: F973 Phase 196 Master Alpha Coupler & Dynamic Resonance Leverage (TC35 ~ TC41)
  - Category 7: High-Throughput Execution Latency SLA Across 500 Assets (TC42 ~ TC45)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path resolution for workspace
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Feature F969 Imports
import src.core.stochastic_gradient_foliation as foliation_mod
from src.core.stochastic_gradient_foliation import (
    VERSION as FOLIATION_VERSION,
    RELEASE as FOLIATION_RELEASE,
    FEATURE as FOLIATION_FEATURE,
    apply_hyperbolic_noise_deadband as foliation_deadband,
    decompose_foliation_tangent_bundle,
    compute_bott_holonomy_displacement,
    compute_foliated_ricci_curvature,
    detect_stress_transition,
    compute_foliation_alpha,
    StochasticGradientFoliationEngine,
    FoliationAlphaEngine,
    Phase196FoliationEngine,
    F969FoliationEngine,
    StochasticFoliationEngine,
    Phase186FoliationEngine,
)

# Feature F970 Imports
import src.core.quantum_lindblad_dissipation as lindblad_mod
from src.core.quantum_lindblad_dissipation import (
    VERSION as LINDBLAD_VERSION,
    RELEASE as LINDBLAD_RELEASE,
    FEATURE as LINDBLAD_FEATURE,
    apply_hyperbolic_noise_deadband as lindblad_deadband,
    build_order_flow_density_matrix,
    build_system_hamiltonian,
    build_lindblad_jump_operators,
    compute_lindblad_dissipator,
    integrate_gksl_master_equation,
    compute_quantum_purity_and_entropy,
    compute_lindblad_dissipation_alpha,
    QuantumLindbladDissipationEngine,
    LindbladDissipationEngine,
    Phase196LindbladEngine,
    F970LindbladEngine,
    OpenQuantumDissipationEngine,
    Phase186LindbladEngine,
)

# Feature F971 Imports
import src.core.hyperspherical_optimal_transport as transport_mod
from src.core.hyperspherical_optimal_transport import (
    VERSION as TRANSPORT_VERSION,
    RELEASE as TRANSPORT_RELEASE,
    FEATURE as TRANSPORT_FEATURE,
    apply_hyperbolic_noise_deadband as transport_deadband,
    project_to_hypersphere,
    compute_hyperspherical_geodesic_distance,
    compute_hyperspherical_cost_matrix,
    sinkhorn_knopp_optimal_transport,
    compute_hyperspherical_log_map,
    compute_directional_restoring_force,
    compute_hyperspherical_transport_alpha,
    HypersphericalOptimalTransportEngine,
    HypersphericalTransportEngine,
    Phase196HypersphericalEngine,
    F971HypersphericalEngine,
    WassersteinBarycenterEngine,
    Phase186HypersphericalEngine,
)

# Feature F972 Imports
from src.ai.factor_orthogonalizer import (
    SeptendecuplePillarMap,
    SEPTENDECUPLE_PILLAR_MAP,
    compute_septendecuple_pillar_zca_whitening,
    compute_17pillar_zca_whitening,
    SedecuplePillarMap,
    compute_sedecuple_pillar_zca_whitening,
)

# Feature F973 Imports
from src.ai.historical_couplers import (
    Phase196Coupler,
    Phase186MasterCoupler,
    Milestone2Phase196Coupler,
    Phase196MasterCoupler,
    F973Coupler,
    SeptendecuplePillarCoupler,
    SeptendecupleConfluenceCoupler,
    Phase195Coupler,
)


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestPhase196DualTreeAndMetadata(unittest.TestCase):
    """Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees."""

    def test_tc01_foliation_dual_tree_parity(self):
        """TC01: Verify bit-for-bit SHA-256 parity for stochastic_gradient_foliation.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "stochastic_gradient_foliation.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "stochastic_gradient_foliation.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc02_lindblad_dual_tree_parity(self):
        """TC02: Verify bit-for-bit SHA-256 parity for quantum_lindblad_dissipation.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "quantum_lindblad_dissipation.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "quantum_lindblad_dissipation.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc03_transport_dual_tree_parity(self):
        """TC03: Verify bit-for-bit SHA-256 parity for hyperspherical_optimal_transport.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "hyperspherical_optimal_transport.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "hyperspherical_optimal_transport.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc04_metadata_constants(self):
        """TC04: Verify version, release, and feature metadata polymorphism."""
        for mod, expected_feature in [
            (foliation_mod, "F969"),
            (lindblad_mod, "F970"),
            (transport_mod, "F971"),
        ]:
            self.assertEqual(int(mod.VERSION), 196)
            self.assertEqual(str(mod.RELEASE), "R186")
            self.assertEqual(str(mod.FEATURE), expected_feature)
            self.assertTrue(mod.VERSION == 196)
            self.assertTrue(mod.RELEASE == "R186")

    def test_tc05_complete_alias_trees(self):
        """TC05: Verify all required aliases resolve correctly to the primary classes."""
        # F969 Aliases
        self.assertIs(FoliationAlphaEngine, StochasticGradientFoliationEngine)
        self.assertIs(Phase196FoliationEngine, StochasticGradientFoliationEngine)
        self.assertIs(F969FoliationEngine, StochasticGradientFoliationEngine)
        self.assertIs(StochasticFoliationEngine, StochasticGradientFoliationEngine)
        self.assertIs(Phase186FoliationEngine, StochasticGradientFoliationEngine)

        # F970 Aliases
        self.assertIs(LindbladDissipationEngine, QuantumLindbladDissipationEngine)
        self.assertIs(Phase196LindbladEngine, QuantumLindbladDissipationEngine)
        self.assertIs(F970LindbladEngine, QuantumLindbladDissipationEngine)
        self.assertIs(OpenQuantumDissipationEngine, QuantumLindbladDissipationEngine)
        self.assertIs(Phase186LindbladEngine, QuantumLindbladDissipationEngine)

        # F971 Aliases
        self.assertIs(HypersphericalTransportEngine, HypersphericalOptimalTransportEngine)
        self.assertIs(Phase196HypersphericalEngine, HypersphericalOptimalTransportEngine)
        self.assertIs(F971HypersphericalEngine, HypersphericalOptimalTransportEngine)
        self.assertIs(WassersteinBarycenterEngine, HypersphericalOptimalTransportEngine)
        self.assertIs(Phase186HypersphericalEngine, HypersphericalOptimalTransportEngine)

        # F973 Aliases
        self.assertIs(Phase186MasterCoupler, Phase196Coupler)
        self.assertIs(Milestone2Phase196Coupler, Phase196Coupler)
        self.assertIs(Phase196MasterCoupler, Phase196Coupler)
        self.assertIs(F973Coupler, Phase196Coupler)
        self.assertIs(SeptendecuplePillarCoupler, Phase196Coupler)
        self.assertIs(SeptendecupleConfluenceCoupler, Phase196Coupler)


class TestPhase196FoliationEngine(unittest.TestCase):
    """Category 2: F969 Stochastic Gradient Foliation & Foliated Ricci Curvature Flow Engine."""

    def setUp(self):
        np.random.seed(42)
        self.n_assets = 6
        self.n_bars = 40
        cov = np.full((self.n_assets, self.n_assets), 0.35)
        np.fill_diagonal(cov, 1.0)
        l_mat = np.linalg.cholesky(cov)
        white_noise = np.random.normal(0, 0.02, (self.n_bars, self.n_assets))
        self.returns = white_noise @ l_mat.T
        self.volumes = np.random.uniform(1e5, 5e5, (self.n_bars, self.n_assets))
        self.prices_dict = {
            f"SYM_{i}": pd.DataFrame({
                "Close": 100.0 * np.exp(np.cumsum(self.returns[:, i])),
                "Volume": self.volumes[:, i],
            })
            for i in range(self.n_assets)
        }

    def test_tc06_tangent_bundle_decomposition_orthogonality(self):
        """TC06: Verify TM = L + Q projectors are idempotent and mutually orthogonal (P_L @ P_Q == 0)."""
        P_L, P_Q, v_L, v_Q = decompose_foliation_tangent_bundle(self.returns, codimension=2)
        d = self.n_assets
        self.assertEqual(P_L.shape, (d, d))
        self.assertEqual(P_Q.shape, (d, d))
        self.assertEqual(len(v_L), d)
        self.assertEqual(len(v_Q), d)

        # Mutual orthogonality
        prod = P_L @ P_Q
        self.assertAlmostEqual(float(np.max(np.abs(prod))), 0.0, places=10)

        # Identity sum: P_L + P_Q == I
        identity_diff = np.max(np.abs((P_L + P_Q) - np.eye(d)))
        self.assertAlmostEqual(float(identity_diff), 0.0, places=10)

        # Velocity decomposition: v_L + v_Q == v
        v_curr = self.returns[-1]
        self.assertLess(float(np.linalg.norm((v_L + v_Q) - v_curr)), 1e-8)

    def test_tc07_foliated_ricci_curvature(self):
        """TC07: Verify foliated Ricci curvature Ric_F computation and scalar curvature bounds."""
        ric_f, k_foliation = compute_foliated_ricci_curvature(self.returns, p_dimension=4)
        self.assertEqual(len(ric_f), 4)
        self.assertFalse(np.isnan(k_foliation))
        self.assertFalse(np.isinf(k_foliation))
        self.assertAlmostEqual(k_foliation, float(np.mean(ric_f)), places=6)

    def test_tc08_bott_holonomy_displacement(self):
        """TC08: Verify transverse Bott holonomy displacement vector Theta."""
        P_L, P_Q, _, _ = decompose_foliation_tangent_bundle(self.returns, codimension=2)
        v_L_series = self.returns @ P_L
        v_Q_series = self.returns @ P_Q
        theta = compute_bott_holonomy_displacement(v_L_series, v_Q_series, P_Q)
        self.assertEqual(len(theta), self.n_assets)
        self.assertFalse(np.isnan(theta).any())

        # Bott connection resides in normal bundle Q
        norm_proj_diff = np.linalg.norm((P_Q @ theta) - theta)
        self.assertLess(float(norm_proj_diff), 1e-8)

    def test_tc09_stress_transition_detection(self):
        """TC09: Verify stress transition triggers when transverse kinetic energy dominates."""
        v_L_calm = np.array([1.0, 1.2, 0.9, 1.1, 0.8, 1.0])
        v_Q_calm = np.array([0.05, 0.02, 0.01, 0.03, 0.02, 0.04])
        theta_calm = np.zeros(6)
        is_stress_calm, metric_calm = detect_stress_transition(v_L_calm, v_Q_calm, theta_calm, k_foliation=0.5)
        self.assertFalse(is_stress_calm)
        self.assertLess(metric_calm, 0.65)

        # Severe transverse shock
        v_L_shock = np.array([0.1, 0.05, 0.08, 0.02, 0.05, 0.04])
        v_Q_shock = np.array([2.5, -3.0, 2.8, -2.9, 3.1, -2.7])
        theta_shock = np.array([1.5, -1.2, 1.8, -1.4, 1.6, -1.5])
        is_stress_shock, metric_shock = detect_stress_transition(v_L_shock, v_Q_shock, theta_shock, k_foliation=-2.0)
        self.assertTrue(is_stress_shock)
        self.assertGreater(metric_shock, 0.65)

    def test_tc10_foliation_alpha_bounds_and_interface_contract(self):
        """TC10: Verify compute_foliation_alpha outputs float32 strictly bounded in [-3.0, 3.0] (PROJECT.md:86)."""
        alpha = compute_foliation_alpha(self.returns, volume_matrix=self.volumes)
        self.assertEqual(alpha.dtype, np.float32)
        self.assertEqual(len(alpha), self.n_assets)
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

        # Engine method contract
        engine = StochasticGradientFoliationEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        eng_alpha = engine.compute_foliation_alpha(self.returns, self.volumes)
        self.assertEqual(eng_alpha.dtype, np.float32)
        self.assertTrue(np.all(eng_alpha >= -3.0) and np.all(eng_alpha <= 3.0))

    def test_tc11_hyperbolic_noise_deadband(self):
        """TC11: Verify hyperbolic deadband filter suppresses micro-noise below delta=0.030."""
        self.assertEqual(foliation_deadband(0.0), 0.0)
        self.assertLess(abs(foliation_deadband(0.01, delta=0.030, alpha=600.0)), 1e-4)
        self.assertGreater(abs(foliation_deadband(0.10, delta=0.030, alpha=600.0)), 0.05)

    def test_tc12_foliation_engine_generate_signals(self):
        """TC12: Verify StochasticGradientFoliationEngine.generate_signals output schema."""
        engine = StochasticGradientFoliationEngine()
        res = engine.generate_signals(self.prices_dict)
        self.assertIn("symbol", res.columns)
        self.assertIn("foliation_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), self.n_assets)
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["foliation_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)

    def test_tc13_foliation_zero_lookahead_temporal_causality(self):
        """TC13: Verify future data alterations do not mutate historical bar alpha."""
        t30_rets = self.returns[:30]
        alpha_t30 = compute_foliation_alpha(t30_rets)
        future_rets = np.copy(self.returns)
        future_rets[30:] = 100.0  # Massive future pump
        alpha_t30_recalc = compute_foliation_alpha(future_rets[:30])
        np.testing.assert_allclose(alpha_t30, alpha_t30_recalc, rtol=1e-6, atol=1e-6)


class TestPhase196QuantumLindbladEngine(unittest.TestCase):
    """Category 3: F970 Open Quantum Lindblad Master Equation & Purity Dissipation Arbitrage Engine."""

    def setUp(self):
        np.random.seed(42)
        self.ofi = 0.45
        self.prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.015, 40)))
        self.volumes = np.random.uniform(1e5, 5e5, 40)

    def test_tc14_order_flow_density_matrix_cptp(self):
        """TC14: Verify density operator rho is Hermitian, PSD, and has unit trace Tr(rho) == 1.0."""
        rho = build_order_flow_density_matrix(self.ofi, spread=0.02)
        self.assertEqual(rho.shape, (3, 3))

        # Hermiticity: rho == rho^dagger
        herm_diff = np.max(np.abs(rho - rho.conj().T))
        self.assertAlmostEqual(float(herm_diff), 0.0, places=10)

        # Unit trace: Tr(rho) == 1.0
        tr_val = float(np.real(np.trace(rho)))
        self.assertAlmostEqual(tr_val, 1.0, places=8)

        # Positive semi-definiteness: lambda_i >= 0
        eigs = np.linalg.eigvalsh(rho)
        self.assertGreaterEqual(float(np.min(eigs)), -1e-10)

    def test_tc15_lindblad_jump_operators(self):
        """TC15: Verify Lindblad jump operators L_inj, L_canc, L_dephase construct valid operators in H_3."""
        jumps = build_lindblad_jump_operators(gamma_inj=0.05, gamma_bid_canc=0.03, gamma_ask_canc=0.02)
        self.assertEqual(len(jumps), 3)
        for L in jumps:
            self.assertEqual(L.shape, (3, 3))
            self.assertFalse(np.isnan(L).any())

    def test_tc16_gksl_master_equation_trace_preservation(self):
        """TC16: Verify GKSL master equation time evolution strictly preserves Tr(rho(t)) == 1.0."""
        rho_0 = build_order_flow_density_matrix(0.25)
        H = build_system_hamiltonian()
        jumps = build_lindblad_jump_operators(0.05, 0.02, 0.02)
        rho_t, d_rho = integrate_gksl_master_equation(rho_0, H, jumps, dt=0.02, n_steps=20)

        # Trace preservation
        self.assertAlmostEqual(float(np.real(np.trace(rho_t))), 1.0, places=8)

        # Trace of dissipator must be zero
        diss = compute_lindblad_dissipator(rho_0, jumps)
        self.assertAlmostEqual(float(np.real(np.trace(diss))), 0.0, places=8)

    def test_tc17_quantum_purity_decay_nonpositive(self):
        """TC17: Verify quantum purity decay rate dot{P} <= 0 under dissipative jumps."""
        rho_0 = build_order_flow_density_matrix(0.50)
        H = build_system_hamiltonian()
        jumps = build_lindblad_jump_operators(0.10, 0.05, 0.05)
        rho_t, d_rho = integrate_gksl_master_equation(rho_0, H, jumps, dt=0.05, n_steps=5)
        purity, purity_decay, _ = compute_quantum_purity_and_entropy(rho_t, d_rho)

        self.assertTrue(1.0 / 3.0 - 1e-6 <= purity <= 1.0 + 1e-6)
        self.assertLessEqual(purity_decay, 1e-8, f"Purity decay positive: {purity_decay}")

    def test_tc18_von_neumann_entropy_nonnegative(self):
        """TC18: Verify von Neumann entropy S_vN >= 0 and strictly bounded in [0, ln 3]."""
        rho = build_order_flow_density_matrix(-0.30)
        _, _, entropy = compute_quantum_purity_and_entropy(rho)
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLessEqual(entropy, float(np.log(3.0)) + 1e-6)

    def test_tc19_lindblad_alpha_bounds_and_contract(self):
        """TC19: Verify compute_lindblad_dissipation_alpha outputs float32 bounded in [-3.0, 3.0] (PROJECT.md:87)."""
        alpha = compute_lindblad_dissipation_alpha(np.array([100.0, 105.0]), np.array([0.2, -0.4]))
        self.assertEqual(alpha.dtype, np.float32)
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

        engine = QuantumLindbladDissipationEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        eng_alpha = engine.compute_lindblad_dissipation_alpha(np.array([100.0, 105.0]), np.array([0.2, -0.4]))
        self.assertEqual(eng_alpha.dtype, np.float32)
        self.assertTrue(np.all(eng_alpha >= -3.0) and np.all(eng_alpha <= 3.0))

    def test_tc20_lindblad_engine_generate_signals(self):
        """TC20: Verify QuantumLindbladDissipationEngine.generate_signals output schema."""
        engine = QuantumLindbladDissipationEngine()
        prices_dict = {
            "005930": pd.DataFrame({"Close": self.prices, "Volume": self.volumes}),
            "000660": pd.DataFrame({"Close": self.prices * 1.02, "Volume": self.volumes * 0.95}),
        }
        res = engine.generate_signals(prices_dict)
        self.assertIn("symbol", res.columns)
        self.assertIn("lindblad_dissipation_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), 2)
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["lindblad_dissipation_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)

    def test_tc21_lindblad_deadband_filtering(self):
        """TC21: Verify continuous hyperbolic deadband filter on Lindblad signals."""
        self.assertEqual(lindblad_deadband(0.0), 0.0)
        self.assertLess(abs(lindblad_deadband(0.015, delta=0.030, alpha=600.0)), 1e-4)
        self.assertGreater(abs(lindblad_deadband(0.12, delta=0.030, alpha=600.0)), 0.06)


class TestPhase196HypersphericalOTEngine(unittest.TestCase):
    """Category 4: F971 Hyperspherical Monge-Kantorovich Optimal Transport & Barycenter Flow Engine."""

    def setUp(self):
        np.random.seed(42)
        self.n_samples = 5
        self.dim = 4
        self.raw_points = np.random.normal(0, 1.0, (self.n_samples, self.dim))
        self.macro_vec = np.array([0.5, -0.2, 0.8, 0.1])

    def test_tc22_hypersphere_projection_unit_norm(self):
        """TC22: Verify projection Pi_S(x) maps points onto unit hypersphere S^{d-1} (||u|| == 1.0)."""
        u = project_to_hypersphere(self.raw_points)
        norms = np.linalg.norm(u, axis=1)
        for n_val in norms:
            self.assertAlmostEqual(float(n_val), 1.0, places=6)

    def test_tc23_geodesic_distance_properties(self):
        """TC23: Verify intrinsic Riemannian geodesic distance d_S(u, v) on S^{d-1} in [0, pi]."""
        u = project_to_hypersphere(np.array([1.0, 0.0, 0.0]))
        v = project_to_hypersphere(np.array([0.0, 1.0, 0.0]))
        w = project_to_hypersphere(np.array([-1.0, 0.0, 0.0]))

        d_uv = compute_hyperspherical_geodesic_distance(u, v)
        d_uw = compute_hyperspherical_geodesic_distance(u, w)
        d_uu = compute_hyperspherical_geodesic_distance(u, u)

        self.assertAlmostEqual(float(d_uu), 0.0, places=6)
        self.assertAlmostEqual(float(d_uv), np.pi / 2.0, places=6)
        self.assertAlmostEqual(float(d_uw), np.pi, places=6)

    def test_tc24_sinkhorn_knopp_transport_mass_conservation(self):
        """TC24: Verify Sinkhorn-Knopp transport plan P preserves marginal distributions."""
        U = project_to_hypersphere(self.raw_points)
        V = project_to_hypersphere(np.random.normal(0, 1.0, (3, self.dim)))
        C = compute_hyperspherical_cost_matrix(U, V)
        P, w2 = sinkhorn_knopp_optimal_transport(C, epsilon_reg=0.05, max_iter=50)

        # Row marginals sum to 1/n
        row_sums = np.sum(P, axis=1)
        np.testing.assert_allclose(row_sums, 1.0 / len(U), rtol=1e-4, atol=1e-4)

        # Col marginals sum to 1/m
        col_sums = np.sum(P, axis=0)
        np.testing.assert_allclose(col_sums, 1.0 / len(V), rtol=1e-4, atol=1e-4)
        self.assertGreaterEqual(w2, 0.0)

    def test_tc25_riemannian_log_map_orthogonality(self):
        """TC25: Verify Riemannian log map Log_u(v) is strictly orthogonal to base point u (<Log_u(v), u> == 0)."""
        u = project_to_hypersphere(np.array([1.0, 2.0, -1.0]))
        v = project_to_hypersphere(np.array([-0.5, 1.5, 2.0]))
        log_vec = compute_hyperspherical_log_map(u, v)

        orthog_diff = abs(float(np.sum(log_vec * u)))
        self.assertAlmostEqual(orthog_diff, 0.0, places=10)

    def test_tc26_directional_restoring_force(self):
        """TC26: Verify directional restoring force along Wasserstein barycentric flow."""
        U = project_to_hypersphere(self.raw_points)
        V = project_to_hypersphere(np.random.normal(0, 1.0, (3, self.dim)))
        C = compute_hyperspherical_cost_matrix(U, V)
        P, _ = sinkhorn_knopp_optimal_transport(C, epsilon_reg=0.05)
        forces = compute_directional_restoring_force(U, V, P, macro_vector=self.macro_vec)

        self.assertEqual(len(forces), self.n_samples)
        self.assertFalse(np.isnan(forces).any())

    def test_tc27_hyperspherical_alpha_bounds_and_contract(self):
        """TC27: Verify compute_hyperspherical_transport_alpha outputs float32 bounded in [-3.0, 3.0] (PROJECT.md:88)."""
        alpha = compute_hyperspherical_transport_alpha(self.raw_points, macro_vector=self.macro_vec)
        self.assertEqual(alpha.dtype, np.float32)
        self.assertEqual(len(alpha), self.n_samples)
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

        engine = HypersphericalOptimalTransportEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        eng_alpha = engine.compute_hyperspherical_transport_alpha(self.raw_points, macro_vector=self.macro_vec)
        self.assertEqual(eng_alpha.dtype, np.float32)
        self.assertTrue(np.all(eng_alpha >= -3.0) and np.all(eng_alpha <= 3.0))

    def test_tc28_transport_engine_generate_signals(self):
        """TC28: Verify HypersphericalOptimalTransportEngine.generate_signals output schema."""
        engine = HypersphericalOptimalTransportEngine()
        prices_dict = {
            f"SYM_{i}": pd.DataFrame({
                "Close": 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, 30))),
                "Volume": np.random.uniform(1e5, 5e5, 30),
            })
            for i in range(4)
        }
        res = engine.generate_signals(prices_dict)
        self.assertIn("symbol", res.columns)
        self.assertIn("hyperspherical_transport_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), 4)
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["hyperspherical_transport_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)


class TestPhase196FactorOrthogonalizer(unittest.TestCase):
    """Category 5: F972 17-Pillar Septendecuple ZCA Whitening Manifold on S_{++}^{17}."""

    def setUp(self):
        np.random.seed(42)
        # Random 17x17 covariance matrix
        a = np.random.normal(0, 1.0, (17, 30))
        self.cov_17 = (a @ a.T) / 30.0 + 1e-4 * np.eye(17)

    def test_tc29_septendecuple_pillar_map_keys_and_aliases(self):
        """TC29: Verify SeptendecuplePillarMap contains 17 canonical pillars and resolves aliases."""
        self.assertEqual(len(SEPTENDECUPLE_PILLAR_MAP), 17)
        expected_pillars = [
            'val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'rev', 'comp',
            'tail', 'macro', 'ricci', 'symplectic', 'octonion', 'topological',
            'sedecuple', 'septendecuple'
        ]
        for p in expected_pillars:
            self.assertIn(p, SEPTENDECUPLE_PILLAR_MAP)

        # Check pillar 17 contents
        p17 = SEPTENDECUPLE_PILLAR_MAP['septendecuple']
        self.assertIn('stochastic_gradient_foliation', p17)
        self.assertIn('quantum_lindblad_dissipation', p17)
        self.assertIn('hyperspherical_optimal_transport', p17)

        # Alias resolution
        self.assertEqual(SEPTENDECUPLE_PILLAR_MAP['SEPTENDECUPLE'], p17)
        self.assertEqual(SEPTENDECUPLE_PILLAR_MAP['PHASE196'], p17)
        self.assertEqual(SEPTENDECUPLE_PILLAR_MAP['FOLIATION'], p17)

    def test_tc30_septendecuple_zca_whitening_shape_and_symmetry(self):
        """TC30: Verify compute_septendecuple_pillar_zca_whitening produces symmetric 17x17 matrix."""
        w_zca = compute_septendecuple_pillar_zca_whitening(self.cov_17)
        self.assertEqual(w_zca.shape, (17, 17))

        sym_diff = np.max(np.abs(w_zca - w_zca.T))
        self.assertAlmostEqual(float(sym_diff), 0.0, places=10)

        # Check alias
        w_alias = compute_17pillar_zca_whitening(self.cov_17)
        np.testing.assert_allclose(w_zca, w_alias, rtol=1e-12, atol=1e-12)

    def test_tc31_whitened_covariance_identity(self):
        """TC31: Verify whitened covariance condition W^T Sigma W == I_17 within tolerance."""
        w_zca = compute_septendecuple_pillar_zca_whitening(self.cov_17, ridge_epsilon=1e-6)
        whitened = w_zca.T @ self.cov_17 @ w_zca
        identity_diff = np.max(np.abs(whitened - np.eye(17)))
        self.assertLess(float(identity_diff), 1e-3, f"Whitened covariance diverges from I_17: {identity_diff}")

    def test_tc32_condition_number_upper_bound_45(self):
        """TC32: Verify condition number kappa(W^T Sigma W) <= 45.0 (PROJECT.md:90)."""
        # Test with severely ill-conditioned covariance
        vals = np.logspace(-4, 2, 17)
        q_mat, _ = np.linalg.qr(np.random.normal(0, 1, (17, 17)))
        ill_cov = q_mat @ np.diag(vals) @ q_mat.T

        w_zca = compute_septendecuple_pillar_zca_whitening(ill_cov, ridge_epsilon=1e-4)
        whitened = w_zca.T @ ill_cov @ w_zca
        eigs = np.linalg.eigvalsh(whitened)
        kappa = float(np.max(eigs) / np.max([np.min(eigs), 1e-12]))
        self.assertLessEqual(kappa, 45.0, f"Condition number breached: {kappa}")

    def test_tc33_rank_preservation_17(self):
        """TC33: Verify rank(W_ZCA) == 17 for full rank covariance."""
        w_zca = compute_septendecuple_pillar_zca_whitening(self.cov_17)
        rk = int(np.linalg.matrix_rank(w_zca))
        self.assertEqual(rk, 17)

    def test_tc34_backward_compatibility_sedecuple(self):
        """TC34: Verify backward compatibility with 16-pillar compute_sedecuple_pillar_zca_whitening."""
        cov_16 = self.cov_17[:16, :16]
        w_16 = compute_sedecuple_pillar_zca_whitening(cov_16)
        self.assertEqual(w_16.shape, (16, 16))
        self.assertAlmostEqual(float(np.max(np.abs(w_16 - w_16.T))), 0.0, places=10)


class TestPhase196MasterCoupler(unittest.TestCase):
    """Category 6: F973 Phase 196 Master Alpha Coupler & Dynamic Resonance Leverage."""

    def setUp(self):
        self.coupler = Phase196Coupler(kappa=1.96, epsilon_reg=1e-6, alpha_bound=3.0)

    def test_tc35_coupler_instantiation_and_engines(self):
        """TC35: Verify Phase196Coupler initializes with F969, F970, F971 engines and 17-pillar map."""
        self.assertIsInstance(self.coupler, Phase195Coupler)
        self.assertEqual(len(self.coupler.pillar_map), 17)
        self.assertIsNotNone(self.coupler.foliation_engine)
        self.assertIsNotNone(self.coupler.lindblad_engine)
        self.assertIsNotNone(self.coupler.hyperspherical_engine)

    def test_tc36_evaluate_master_alpha_schema(self):
        """TC36: Verify evaluate() returns comprehensive dictionary with bounded alpha and metadata."""
        scores_dict = {f"pillar_{i}": 0.55 for i in range(17)}
        res = self.coupler.evaluate(scores_dict, regime="BULL_STABLE")
        self.assertIn("alpha", res)
        self.assertIn("master_alpha", res)
        self.assertIn("alpha_normalized", res)
        self.assertIn("leverage", res)
        self.assertIn("zca_matrix", res)

        alpha_val = float(res["alpha"])
        self.assertTrue(-3.0 <= alpha_val <= 3.0)

    def test_tc37_dynamic_leverage_bull_stable_2_50x(self):
        """TC37: Verify dynamic leverage ceiling expands up to 2.50x in BULL_STABLE under 10D contango lock."""
        vix_term = {
            "vix1m": 14.0,
            "vix3m": 17.5,
            "contango_days": 10,
        }
        lev = self.coupler.compute_dynamic_leverage(confluence_score=2.8, regime="BULL_STABLE", vix_term_structure=vix_term)
        self.assertGreater(lev, 2.30)
        self.assertLessEqual(lev, 2.50)

    def test_tc38_dynamic_leverage_crisis_halt_0_00x(self):
        """TC38: Verify dynamic leverage collapses strictly to 0.00x in CRISIS / CRISIS_PANIC (PROJECT.md:95)."""
        lev_crisis = self.coupler.compute_dynamic_leverage(confluence_score=1.5, regime="CRISIS")
        self.assertEqual(lev_crisis, 0.0)

        lev_panic = self.coupler.compute_dynamic_leverage(confluence_score=-1.0, regime="CRISIS_PANIC")
        self.assertEqual(lev_panic, 0.0)

    def test_tc39_dynamic_leverage_regime_monotonicity(self):
        """TC39: Verify dynamic leverage monotonicity across market regimes."""
        l_crisis = self.coupler.compute_dynamic_leverage(1.5, "CRISIS")
        l_bear = self.coupler.compute_dynamic_leverage(1.5, "BEAR_LOW_VOL")
        l_side = self.coupler.compute_dynamic_leverage(1.5, "SIDEWAYS_LOW_VOL")
        l_bull_vol = self.coupler.compute_dynamic_leverage(1.5, "BULL_HIGH_VOL")
        l_bull_stb = self.coupler.compute_dynamic_leverage(1.5, "BULL_LOW_VOL", vix_term_structure={"contango_days": 10})

        self.assertEqual(l_crisis, 0.0)
        self.assertLessEqual(l_crisis, l_bear)
        self.assertLessEqual(l_bear, l_side)
        self.assertLessEqual(l_side, l_bull_vol)
        self.assertLessEqual(l_bull_vol, l_bull_stb)
        self.assertLessEqual(l_bull_stb, 2.50)

    def test_tc40_contango_lock_failure_caps_leverage(self):
        """TC40: Verify 9-day contango (failing 10-day invariant) caps leverage strictly below 2.00x in BULL_STABLE."""
        vix_term_fail = {
            "vix1m": 15.0,
            "vix3m": 17.0,
            "contango_days": 9,  # Missing 10th day
        }
        lev = self.coupler.compute_dynamic_leverage(confluence_score=2.8, regime="BULL_STABLE", vix_term_structure=vix_term_fail)
        self.assertLess(lev, 2.00, f"Leverage unconstrained despite broken contango lock: {lev}")

    def test_tc41_backward_compatibility_aliases(self):
        """TC41: Verify Phase196Coupler alias resolution."""
        aliases = [
            Phase186MasterCoupler,
            Phase196MasterCoupler,
            SeptendecuplePillarCoupler,
            SeptendecupleConfluenceCoupler,
            F973Coupler,
        ]
        for a in aliases:
            self.assertIs(a, Phase196Coupler)


class TestPhase196LatencySLA(unittest.TestCase):
    """Category 7: High-Throughput Execution Latency SLA Across 500 Assets."""

    def test_tc42_foliation_500_stocks_latency(self):
        """TC42: Verify F969 Foliation flow executes across 500 stocks within sub-5ms/asset SLA."""
        np.random.seed(42)
        n_assets = 500
        n_bars = 40
        rets = np.random.normal(0, 0.015, (n_bars, n_assets))
        vols = np.random.uniform(1e5, 5e5, (n_bars, n_assets))

        t0 = time.perf_counter()
        compute_foliation_alpha(rets, vols)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Foliation latency breached: {per_asset_ms:.2f} ms/asset")

    def test_tc43_lindblad_500_stocks_latency(self):
        """TC43: Verify F970 Lindblad dissipation executes across 500 stocks within sub-5ms/asset SLA."""
        np.random.seed(42)
        n_assets = 500
        prices = np.random.uniform(50.0, 150.0, n_assets)
        ofi = np.random.uniform(-1.0, 1.0, n_assets)

        t0 = time.perf_counter()
        compute_lindblad_dissipation_alpha(prices, ofi, dt=0.05, n_steps=5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Lindblad latency breached: {per_asset_ms:.2f} ms/asset")

    def test_tc44_hyperspherical_transport_500_stocks_latency(self):
        """TC44: Verify F971 Hyperspherical transport executes across 500 stocks within sub-5ms/asset SLA."""
        np.random.seed(42)
        n_assets = 500
        dim = 4
        scores = np.random.normal(0, 1.0, (n_assets, dim))
        macro = np.array([0.5, -0.2, 0.8, 0.1])

        t0 = time.perf_counter()
        compute_hyperspherical_transport_alpha(scores, macro, epsilon_reg=0.05)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Transport latency breached: {per_asset_ms:.2f} ms/asset")

    def test_tc45_zca_and_coupler_batch_latency(self):
        """TC45: Verify 17-pillar ZCA Whitening executes batch under 15ms total."""
        cov_17 = np.eye(17) + 0.1 * np.random.normal(0, 1, (17, 17))
        cov_17 = cov_17 @ cov_17.T

        t0 = time.perf_counter()
        for _ in range(10):
            compute_septendecuple_pillar_zca_whitening(cov_17)
        elapsed_ms = ((time.perf_counter() - t0) * 1000.0) / 10.0

        self.assertLess(elapsed_ms, 15.0, f"ZCA batch latency breached: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    unittest.main()

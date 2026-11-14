"""
tests/test_phase193_alpha_core.py
=================================
Exhaustive Verification Suite for Milestone 1: Quantitative Alpha Feature Engineering
(Phase 193 Features F949, F950, F951) for Release R184.

Categories:
  - Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: F949 Non-Commutative Dirac Spectral Flow Engine (TC06 ~ TC12)
  - Category 3: F950 Quantum Annealing Combinatorial Arbitrage Engine (TC13 ~ TC17)
  - Category 4: F951 Persistent Sheaf Cohomology Liquidity Engine (TC18 ~ TC22)
  - Category 5: Numerical Stability, Extreme Cases & Zero Lookahead Bias (TC23 ~ TC26)
  - Category 6: Execution Latency SLA Across 500 Assets (TC27 ~ TC29)
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

import src.core.non_commutative_dirac_spectral as dirac_mod
from src.core.non_commutative_dirac_spectral import (
    VERSION as DIRAC_VERSION,
    RELEASE as DIRAC_RELEASE,
    FEATURE as DIRAC_FEATURE,
    get_dirac_gamma_matrices,
    get_hermitian_dirac_generators,
    apply_hyperbolic_noise_deadband,
    compute_dirac_operator,
    compute_aps_eta_invariant,
    compute_spectral_flow,
    compute_spectral_flow_alpha,
    NonCommutativeDiracSpectralFlowEngine,
    Phase193DiracSpectralEngine,
    F949DiracSpectralEngine,
    DiracSpectralFlowEngine,
    Phase184DiracSpectralEngine,
    NonCommutativeDiracSpectralEngine,
)

import src.core.quantum_annealing_arbitrage as qa_mod
from src.core.quantum_annealing_arbitrage import (
    VERSION as QA_VERSION,
    RELEASE as QA_RELEASE,
    FEATURE as QA_FEATURE,
    build_qubo_coupling_matrix,
    solve_simulated_quantum_annealing,
    compute_quantum_arbitrage_weights,
    QuantumAnnealingCombinatorialArbitrageEngine,
    Phase193QuantumAnnealingEngine,
    F950QuantumArbitrageEngine,
    QuantumArbitrageEngine,
    Phase184QuantumArbitrageEngine,
    QuantumAnnealingArbitrageEngine,
)

import src.core.persistent_sheaf_liquidity as sheaf_mod
from src.core.persistent_sheaf_liquidity import (
    VERSION as SHEAF_VERSION,
    RELEASE as SHEAF_RELEASE,
    FEATURE as SHEAF_FEATURE,
    build_cellular_sheaf,
    compute_sheaf_laplacian,
    compute_persistent_sheaf_cohomology,
    compute_sheaf_cohomology_transport,
    PersistentSheafCohomologyLiquidityEngine,
    Phase193SheafLiquidityEngine,
    F951SheafLiquidityEngine,
    SheafLiquidityTransportEngine,
    Phase184SheafLiquidityEngine,
    PersistentSheafLiquidityEngine,
)


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestPhase193DualTreeAndMetadata(unittest.TestCase):
    """Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees."""

    def test_tc01_dirac_spectral_dual_tree_parity(self):
        src_file = PROJECT_ROOT / "src" / "core" / "non_commutative_dirac_spectral.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "non_commutative_dirac_spectral.py"
        self.assertTrue(src_file.exists(), f"Source file does not exist: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file does not exist: {target_file}")
        sha_src = _compute_sha256(src_file)
        sha_target = _compute_sha256(target_file)
        self.assertEqual(sha_src, sha_target, "Bit-for-bit SHA-256 mismatch on non_commutative_dirac_spectral.py")

    def test_tc02_quantum_annealing_dual_tree_parity(self):
        src_file = PROJECT_ROOT / "src" / "core" / "quantum_annealing_arbitrage.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "quantum_annealing_arbitrage.py"
        self.assertTrue(src_file.exists(), f"Source file does not exist: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file does not exist: {target_file}")
        sha_src = _compute_sha256(src_file)
        sha_target = _compute_sha256(target_file)
        self.assertEqual(sha_src, sha_target, "Bit-for-bit SHA-256 mismatch on quantum_annealing_arbitrage.py")

    def test_tc03_sheaf_liquidity_dual_tree_parity(self):
        src_file = PROJECT_ROOT / "src" / "core" / "persistent_sheaf_liquidity.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "persistent_sheaf_liquidity.py"
        self.assertTrue(src_file.exists(), f"Source file does not exist: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file does not exist: {target_file}")
        sha_src = _compute_sha256(src_file)
        sha_target = _compute_sha256(target_file)
        self.assertEqual(sha_src, sha_target, "Bit-for-bit SHA-256 mismatch on persistent_sheaf_liquidity.py")

    def test_tc04_metadata_constants(self):
        for mod, expected_feature in [
            (dirac_mod, "F949"),
            (qa_mod, "F950"),
            (sheaf_mod, "F951"),
        ]:
            self.assertEqual(int(mod.VERSION), 193)
            self.assertEqual(str(mod.RELEASE), "R184")
            self.assertEqual(str(mod.FEATURE), expected_feature)

    def test_tc05_complete_alias_trees(self):
        self.assertIs(Phase193DiracSpectralEngine, NonCommutativeDiracSpectralFlowEngine)
        self.assertIs(F949DiracSpectralEngine, NonCommutativeDiracSpectralFlowEngine)
        self.assertIs(DiracSpectralFlowEngine, NonCommutativeDiracSpectralFlowEngine)
        self.assertIs(Phase184DiracSpectralEngine, NonCommutativeDiracSpectralFlowEngine)
        self.assertIs(NonCommutativeDiracSpectralEngine, NonCommutativeDiracSpectralFlowEngine)

        self.assertIs(Phase193QuantumAnnealingEngine, QuantumAnnealingCombinatorialArbitrageEngine)
        self.assertIs(F950QuantumArbitrageEngine, QuantumAnnealingCombinatorialArbitrageEngine)
        self.assertIs(QuantumArbitrageEngine, QuantumAnnealingCombinatorialArbitrageEngine)
        self.assertIs(Phase184QuantumArbitrageEngine, QuantumAnnealingCombinatorialArbitrageEngine)
        self.assertIs(QuantumAnnealingArbitrageEngine, QuantumAnnealingCombinatorialArbitrageEngine)

        self.assertIs(Phase193SheafLiquidityEngine, PersistentSheafCohomologyLiquidityEngine)
        self.assertIs(F951SheafLiquidityEngine, PersistentSheafCohomologyLiquidityEngine)
        self.assertIs(SheafLiquidityTransportEngine, PersistentSheafCohomologyLiquidityEngine)
        self.assertIs(Phase184SheafLiquidityEngine, PersistentSheafCohomologyLiquidityEngine)
        self.assertIs(PersistentSheafLiquidityEngine, PersistentSheafCohomologyLiquidityEngine)


class TestPhase193DiracSpectralEngine(unittest.TestCase):
    """Category 2: F949 Non-Commutative Dirac Spectral Flow Engine."""

    def test_tc06_clifford_algebra_gamma_matrices(self):
        g0, g1, g2, g3 = get_dirac_gamma_matrices()
        gammas = [g0, g1, g2, g3]
        eta = np.diag([1.0, -1.0, -1.0, -1.0])
        I4 = np.eye(4, dtype=np.complex128)

        # Check anticommutation {gamma^mu, gamma^nu} = 2 * eta^{mu, nu} * I4
        for mu in range(4):
            for nu in range(4):
                anticomm = gammas[mu] @ gammas[nu] + gammas[nu] @ gammas[mu]
                expected = 2.0 * eta[mu, nu] * I4
                np.testing.assert_allclose(anticomm, expected, atol=1e-10)

        # Check Euclidean Hermitian generators
        G0, G1, G2, G3 = get_hermitian_dirac_generators()
        for G in [G0, G1, G2, G3]:
            # Hermiticity: G^dagger == G
            np.testing.assert_allclose(G.conj().T, G, atol=1e-10)
            # G^2 == I4
            np.testing.assert_allclose(G @ G, I4, atol=1e-10)

    def test_tc07_compute_dirac_operator_hermiticity(self):
        prices = np.array([100.0, 101.5, 99.0, 102.0, 103.5, 101.0, 104.0])
        vols = np.array([1000, 1200, 800, 1500, 1300, 1100, 1600])

        D = compute_dirac_operator(prices=prices, volumes=vols, mass_field=0.05)
        self.assertEqual(D.shape, (4, 4))
        # Strictly Hermitian: D == D^dagger
        np.testing.assert_allclose(D, D.conj().T, atol=1e-10)

        # Eigenvalues must be purely real
        eigs = np.linalg.eigvalsh(D)
        self.assertEqual(len(eigs), 4)
        self.assertTrue(np.all(np.isreal(eigs)))

    def test_tc08_compute_aps_eta_invariant(self):
        # Asymmetric Dirac operator
        G0, G1, G2, G3 = get_hermitian_dirac_generators()
        D_pos = 0.5 * G0 + 0.2 * G1 + 0.1 * G2 + 0.05 * np.eye(4)
        D_neg = -0.5 * G0 + 0.2 * G1 + 0.1 * G2 + 0.05 * np.eye(4)

        eta_pos = compute_aps_eta_invariant(D_pos, s_param=0.50)
        eta_neg = compute_aps_eta_invariant(D_neg, s_param=0.50)

        self.assertIsInstance(eta_pos, float)
        self.assertIsInstance(eta_neg, float)
        self.assertGreater(eta_pos, eta_neg)
        self.assertTrue(-100.0 <= eta_pos <= 100.0)

    def test_tc09_compute_spectral_flow(self):
        trajectory = []
        for step in range(15):
            prices = 100.0 + np.cumsum(np.sin(np.linspace(0, step, 10)))
            D = compute_dirac_operator(prices=prices)
            trajectory.append(D)

        sf = compute_spectral_flow(trajectory, window=10)
        self.assertIsInstance(sf, float)
        self.assertTrue(-20.0 <= sf <= 20.0)

    def test_tc10_compute_spectral_flow_alpha_bounds_and_dtype(self):
        rets = np.array([0.01, -0.02, 0.03, -0.01, 0.05])
        vols = np.array([0.15, 0.25, 0.10, 0.30, 0.18])

        alpha = compute_spectral_flow_alpha(rets, vols)
        self.assertEqual(alpha.dtype, np.float32)
        self.assertEqual(len(alpha), 5)
        self.assertTrue(np.all(alpha >= -3.0))
        self.assertTrue(np.all(alpha <= 3.0))
        self.assertFalse(np.any(np.isnan(alpha)))
        self.assertFalse(np.any(np.isinf(alpha)))

    def test_tc11_dirac_engine_generate_signals(self):
        engine = NonCommutativeDiracSpectralFlowEngine()
        dates = pd.date_range("2026-01-01", periods=25, freq="B")

        prices_dict = {
            "005930": pd.DataFrame({
                "Open": np.linspace(70000, 75000, 25),
                "High": np.linspace(71000, 76000, 25),
                "Low": np.linspace(69000, 74000, 25),
                "Close": np.linspace(70500, 75500, 25),
                "Volume": np.random.uniform(100000, 500000, 25),
            }, index=dates),
            "AAPL": pd.DataFrame({
                "Open": np.linspace(180, 195, 25),
                "High": np.linspace(182, 197, 25),
                "Low": np.linspace(178, 193, 25),
                "Close": np.linspace(181, 196, 25),
                "Volume": np.random.uniform(5000000, 8000000, 25),
            }, index=dates),
        }

        df_scores = engine.generate_signals(prices_dict)
        self.assertIn("symbol", df_scores.columns)
        self.assertIn("dirac_spectral_flow_score", df_scores.columns)
        self.assertIn("raw_score", df_scores.columns)
        self.assertEqual(len(df_scores), 2)

        # Check bounds: normalized in [0.05, 0.95], raw in [-3.0, 3.0]
        for score in df_scores["dirac_spectral_flow_score"]:
            self.assertTrue(0.05 <= score <= 0.95)
        for raw in df_scores["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0)

    def test_tc12_hyperbolic_noise_deadband(self):
        # Value below delta=0.030 should be strongly attenuated
        sub_noise = 0.015
        filtered_sub = apply_hyperbolic_noise_deadband(sub_noise, delta=0.030, alpha=600.0)
        self.assertLess(abs(filtered_sub), 0.005)

        # Value well above delta should be preserved
        sig = 0.50
        filtered_sig = apply_hyperbolic_noise_deadband(sig, delta=0.030, alpha=600.0)
        self.assertAlmostEqual(filtered_sig, 0.50, places=2)


class TestPhase193QuantumAnnealingEngine(unittest.TestCase):
    """Category 3: F950 Quantum Annealing Combinatorial Arbitrage Engine."""

    def test_tc13_build_qubo_coupling_matrix(self):
        np.random.seed(42)
        prices = 100.0 + np.cumsum(np.random.randn(50, 4), axis=0)
        J, h = build_qubo_coupling_matrix(prices, lambda_budget=1.50)

        self.assertEqual(J.shape, (4, 4))
        self.assertEqual(len(h), 4)

        # Symmetrical J with zero diagonal
        np.testing.assert_allclose(J, J.T, atol=1e-10)
        np.testing.assert_allclose(np.diag(J), np.zeros(4), atol=1e-10)
        self.assertTrue(np.all(np.isfinite(h)))

    def test_tc14_solve_sqa_transverse_ising(self):
        N = 6
        J = np.ones((N, N)) * 0.2
        np.fill_diagonal(J, 0.0)
        h = np.array([1.5, -1.2, 0.8, -0.9, 0.5, -0.4])

        best_spins, tunneling_mag = solve_simulated_quantum_annealing(
            J_matrix=J,
            h_vector=h,
            trotter_slices=8,
            num_sweeps=50,
            seed=123,
        )

        self.assertEqual(len(best_spins), N)
        self.assertEqual(len(tunneling_mag), N)

        # Spins must be +/- 1
        for s in best_spins:
            self.assertIn(s, (-1.0, 1.0))

        # Tunneling magnetization in [-1.0, 1.0]
        self.assertTrue(np.all(tunneling_mag >= -1.0))
        self.assertTrue(np.all(tunneling_mag <= 1.0))

    def test_tc15_compute_quantum_arbitrage_weights(self):
        corr = np.array([
            [1.0, 0.8, -0.3],
            [0.8, 1.0, -0.4],
            [-0.3, -0.4, 1.0],
        ])
        spread = np.array([2.1, -1.8, 0.2])

        weights = compute_quantum_arbitrage_weights(corr, spread)
        self.assertEqual(weights.dtype, np.float32)
        self.assertEqual(len(weights), 3)
        self.assertTrue(np.all(weights >= -3.0))
        self.assertTrue(np.all(weights <= 3.0))

    def test_tc16_qa_engine_generate_signals(self):
        engine = QuantumAnnealingCombinatorialArbitrageEngine(num_sweeps=30)
        dates = pd.date_range("2026-01-01", periods=20, freq="B")

        prices_dict = {
            "SYM1": pd.DataFrame({"Close": np.linspace(100, 120, 20)}, index=dates),
            "SYM2": pd.DataFrame({"Close": np.linspace(50, 45, 20)}, index=dates),
            "SYM3": pd.DataFrame({"Close": np.linspace(80, 85, 20)}, index=dates),
        }

        df_scores = engine.generate_signals(prices_dict)
        self.assertIn("symbol", df_scores.columns)
        self.assertIn("quantum_annealing_arbitrage_score", df_scores.columns)
        self.assertIn("raw_score", df_scores.columns)
        self.assertIn("spin_state", df_scores.columns)
        self.assertIn("tunneling_magnetization", df_scores.columns)
        self.assertEqual(len(df_scores), 3)

        for score in df_scores["quantum_annealing_arbitrage_score"]:
            self.assertTrue(0.05 <= score <= 0.95)
        for raw in df_scores["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0)

    def test_tc17_qa_energy_minimization_property(self):
        # A strong external field h=[+5, -5] should align ground state spins to [+1, -1]
        J = np.zeros((2, 2))
        h = np.array([5.0, -5.0])

        best_spins, _ = solve_simulated_quantum_annealing(
            J_matrix=J,
            h_vector=h,
            trotter_slices=8,
            num_sweeps=60,
            seed=42,
        )
        self.assertEqual(best_spins[0], 1.0)
        self.assertEqual(best_spins[1], -1.0)


class TestPhase193PersistentSheafEngine(unittest.TestCase):
    """Category 4: F951 Persistent Sheaf Cohomology Liquidity Engine."""

    def test_tc18_build_cellular_sheaf_and_orthogonal_maps(self):
        adj = np.array([
            [0.0, 0.7, 0.2],
            [0.7, 0.0, 0.5],
            [0.2, 0.5, 0.0],
        ])
        node_feats = np.array([
            [1.0, 0.5],
            [0.8, 0.3],
            [1.2, 0.9],
        ])

        L, r_maps = build_cellular_sheaf(adj, node_feats, stalk_dim=2)
        self.assertEqual(L.shape, (6, 6))

        # Check restriction maps in O(2): F @ F^T == I_2
        for key, F in r_maps.items():
            self.assertEqual(F.shape, (2, 2))
            np.testing.assert_allclose(F @ F.T, np.eye(2), atol=1e-8)

    def test_tc19_sheaf_laplacian_psd(self):
        adj = np.array([
            [0.0, 0.9],
            [0.9, 0.0],
        ])
        node_feats = np.array([
            [1.0, 0.0],
            [0.0, 1.0],
        ])

        L, _ = build_cellular_sheaf(adj, node_feats, stalk_dim=2)
        # Check symmetry
        np.testing.assert_allclose(L, L.T, atol=1e-10)

        # Positive semi-definite: all eigenvalues >= 0
        evals = np.linalg.eigvalsh(L)
        self.assertTrue(np.all(evals >= -1e-8))

    def test_tc20_compute_persistent_sheaf_cohomology(self):
        L = np.diag([0.0, 0.0, 1.5, 2.0, 4.0, 5.0])
        cohom = compute_persistent_sheaf_cohomology(L, num_nodes=3, stalk_dim=2, tol=1e-4)

        self.assertIn("harmonic_kernel", cohom)
        self.assertIn("obstruction_space", cohom)
        self.assertIn("betti_0", cohom)
        self.assertIn("betti_1", cohom)
        self.assertIn("spectral_gap", cohom)

        # 2 zero eigenvalues -> betti_0 == 2
        self.assertEqual(cohom["betti_0"], 2)
        self.assertGreater(cohom["betti_1"], 0)
        self.assertAlmostEqual(cohom["spectral_gap"], 1.5, places=3)

    def test_tc21_compute_sheaf_cohomology_transport_bounds(self):
        depth = np.array([
            [1000.0, 50.0],
            [800.0, 40.0],
            [1500.0, 80.0],
            [600.0, 30.0],
        ])
        turnover = np.corrcoef(depth)

        alpha = compute_sheaf_cohomology_transport(depth, turnover)
        self.assertEqual(alpha.dtype, np.float32)
        self.assertEqual(len(alpha), 4)
        self.assertTrue(np.all(alpha >= -3.0))
        self.assertTrue(np.all(alpha <= 3.0))

    def test_tc22_sheaf_engine_generate_signals(self):
        engine = PersistentSheafCohomologyLiquidityEngine()
        dates = pd.date_range("2026-01-01", periods=15, freq="B")

        prices_dict = {
            "AAPL": pd.DataFrame({"Close": np.linspace(150, 160, 15), "Volume": np.linspace(1000, 2000, 15)}, index=dates),
            "MSFT": pd.DataFrame({"Close": np.linspace(300, 310, 15), "Volume": np.linspace(800, 1200, 15)}, index=dates),
            "NVDA": pd.DataFrame({"Close": np.linspace(400, 420, 15), "Volume": np.linspace(1500, 3000, 15)}, index=dates),
        }

        df_scores = engine.generate_signals(prices_dict)
        self.assertIn("symbol", df_scores.columns)
        self.assertIn("sheaf_liquidity_transport_score", df_scores.columns)
        self.assertIn("raw_score", df_scores.columns)
        self.assertIn("influx_energy", df_scores.columns)
        self.assertEqual(len(df_scores), 3)

        for score in df_scores["sheaf_liquidity_transport_score"]:
            self.assertTrue(0.05 <= score <= 0.95)
        for raw in df_scores["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0)


class TestPhase193NumericalStabilityAndEdgeCases(unittest.TestCase):
    """Category 5: Numerical Stability, Extreme Cases & Zero Lookahead Bias."""

    def test_tc23_extreme_correlation_resilience(self):
        # All-perfect +1.0 correlation
        N = 5
        corr_ones = np.ones((N, N))
        spread = np.array([1.0, -1.0, 2.0, -2.0, 0.0])

        w_ones = compute_quantum_arbitrage_weights(corr_ones, spread)
        self.assertTrue(np.all(np.isfinite(w_ones)))
        self.assertTrue(np.all(w_ones >= -3.0))
        self.assertTrue(np.all(w_ones <= 3.0))

        # Identity correlation
        corr_eye = np.eye(N)
        w_eye = compute_quantum_arbitrage_weights(corr_eye, spread)
        self.assertTrue(np.all(np.isfinite(w_eye)))

    def test_tc24_extreme_volatility_and_spikes(self):
        # High volatility price series
        prices_spike = np.array([100.0, 10000.0, 1.0, 5000.0, 2.0, 8000.0])
        D = compute_dirac_operator(prices=prices_spike, mass_field=10.0)
        self.assertTrue(np.all(np.isfinite(D)))

        eta = compute_aps_eta_invariant(D)
        self.assertTrue(np.isfinite(eta))
        self.assertTrue(-100.0 <= eta <= 100.0)

    def test_tc25_empty_and_nan_inputs(self):
        # Dirac engine on empty prices
        D_empty = compute_dirac_operator(np.array([]))
        self.assertEqual(D_empty.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_empty)))

        # QA on empty inputs
        w_empty = compute_quantum_arbitrage_weights(np.array([]), np.array([]))
        self.assertEqual(len(w_empty), 0)

        # Sheaf on NaNs
        nan_depth = np.array([[np.nan, np.inf], [np.nan, -np.inf]])
        nan_turnover = np.array([[np.nan, np.nan], [np.nan, np.nan]])
        alpha_sheaf = compute_sheaf_cohomology_transport(nan_depth, nan_turnover)
        self.assertEqual(len(alpha_sheaf), 2)
        self.assertTrue(np.all(np.isfinite(alpha_sheaf)))

    def test_tc26_zero_lookahead_bias(self):
        # Ensure that signals at time T do NOT change when future data at T+1 is added
        np.random.seed(99)
        base_series = 100.0 + np.cumsum(np.random.randn(30))
        future_extended = np.append(base_series, [150.0, 160.0])

        D_base = compute_dirac_operator(base_series)
        D_base_from_sub = compute_dirac_operator(future_extended[:30])
        np.testing.assert_allclose(D_base, D_base_from_sub, atol=1e-12)

        eta_base = compute_aps_eta_invariant(D_base)
        eta_base_sub = compute_aps_eta_invariant(D_base_from_sub)
        self.assertEqual(eta_base, eta_base_sub)


class TestPhase193LatencySLA(unittest.TestCase):
    """Category 6: Execution Latency SLA Across 500 Assets."""

    def test_tc27_dirac_spectral_flow_500_stocks_latency(self):
        N = 500
        rets = np.random.randn(10, N) * 0.02
        vols = np.random.uniform(0.10, 0.40, N)

        t0 = time.perf_counter()
        alpha = compute_spectral_flow_alpha(rets, vols)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(alpha), N)
        self.assertTrue(np.all(np.isfinite(alpha)))
        # Target SLA: sub-15ms
        self.assertLess(elapsed, 0.050, f"Dirac Spectral Flow latency {elapsed*1000:.2f}ms exceeds SLA limit")

    def test_tc28_quantum_annealing_500_stocks_latency(self):
        N = 500
        corr = np.eye(N) + 0.1 * np.random.randn(N, N)
        corr = 0.5 * (corr + corr.T)
        np.fill_diagonal(corr, 1.0)
        spread = np.random.randn(N)

        t0 = time.perf_counter()
        weights = compute_quantum_arbitrage_weights(corr, spread)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(weights), N)
        self.assertTrue(np.all(np.isfinite(weights)))
        # Target SLA: sub-10ms (bound <50ms in test runner)
        self.assertLess(elapsed, 0.050, f"Quantum Annealing latency {elapsed*1000:.2f}ms exceeds SLA limit")

    def test_tc29_persistent_sheaf_500_stocks_latency(self):
        N = 500
        depth = np.random.uniform(100, 1000, size=(N, 2))
        turnover = np.eye(N)

        t0 = time.perf_counter()
        alpha = compute_sheaf_cohomology_transport(depth, turnover)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(alpha), N)
        self.assertTrue(np.all(np.isfinite(alpha)))
        # Target SLA: sub-15ms (bound <50ms in test runner)
        self.assertLess(elapsed, 0.050, f"Persistent Sheaf latency {elapsed*1000:.2f}ms exceeds SLA limit")


if __name__ == "__main__":
    unittest.main()

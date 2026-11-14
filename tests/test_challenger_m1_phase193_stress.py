"""
tests/test_challenger_m1_phase193_stress.py
===========================================
Adversarial Stress and Empirical Verification Harness for Milestone 1
(Phase 193 Features F949, F950, F951) — Release R184.

This suite executes adversarial stress scenarios:
  1. Rank-Deficient and Singular Correlation / Adjacency / Covariance Matrices (Rank 1, Det = 0, Condition > 1e15).
  2. 100% Collinear Asset Returns, Identical Series, and Zero Spreads.
  3. Degenerate Input Injections: All-Zeros, All-NaNs, All-Infs, Negative Prices.
  4. Extreme Price Moves: Single-day +1000% Surges, -90% Crashes, Flash Crashes.
  5. Strict Bounds Invariant: Alpha in [-3.0, 3.0], Normalized Scores in [0.05, 0.95].
  6. Zero Uncaught Exceptions across All Public Functions and Strategy Engines.
  7. Large-Scale N=500 Adversarial Stress Latency Verification (<50ms SLA).
"""

from __future__ import annotations

import time
import unittest
import numpy as np
import pandas as pd

from src.core.non_commutative_dirac_spectral import (
    compute_dirac_operator,
    compute_aps_eta_invariant,
    compute_spectral_flow,
    compute_spectral_flow_alpha,
    apply_hyperbolic_noise_deadband,
    NonCommutativeDiracSpectralFlowEngine,
)
from src.core.quantum_annealing_arbitrage import (
    build_qubo_coupling_matrix,
    solve_simulated_quantum_annealing,
    compute_quantum_arbitrage_weights,
    QuantumAnnealingCombinatorialArbitrageEngine,
)
from src.core.persistent_sheaf_liquidity import (
    build_cellular_sheaf,
    compute_sheaf_laplacian,
    compute_persistent_sheaf_cohomology,
    compute_sheaf_cohomology_transport,
    PersistentSheafCohomologyLiquidityEngine,
)


class TestAdversarialF949DiracSpectralFlow(unittest.TestCase):
    """Adversarial stress-testing of Feature F949 (Dirac Spectral Flow Alpha)."""

    def test_adv01_dirac_operator_degenerate_and_corrupt_prices(self):
        """Test compute_dirac_operator under degenerate, NaN, Inf, and negative prices."""
        # 1. All zeros
        p_zeros = np.zeros(50)
        D0 = compute_dirac_operator(p_zeros)
        self.assertEqual(D0.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D0)))
        np.testing.assert_allclose(D0, D0.conj().T, atol=1e-12)

        # 2. All NaNs
        p_nans = np.full(50, np.nan)
        D_nan = compute_dirac_operator(p_nans)
        self.assertEqual(D_nan.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_nan)))
        np.testing.assert_allclose(D_nan, D_nan.conj().T, atol=1e-12)

        # 3. All Infs
        p_infs = np.full(50, np.inf)
        D_inf = compute_dirac_operator(p_infs)
        self.assertEqual(D_inf.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_inf)))
        np.testing.assert_allclose(D_inf, D_inf.conj().T, atol=1e-12)

        # 4. Negative prices
        p_neg = np.array([-10.0, -20.0, -15.0, -5.0])
        D_neg = compute_dirac_operator(p_neg)
        self.assertEqual(D_neg.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_neg)))
        np.testing.assert_allclose(D_neg, D_neg.conj().T, atol=1e-12)

        # 5. Empty and single-element inputs
        D_empty = compute_dirac_operator(np.array([]))
        self.assertEqual(D_empty.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_empty)))
        np.testing.assert_allclose(D_empty, D_empty.conj().T, atol=1e-12)

        D_one = compute_dirac_operator(np.array([42.0]))
        self.assertEqual(D_one.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(D_one)))
        np.testing.assert_allclose(D_one, D_one.conj().T, atol=1e-12)

    def test_adv02_dirac_operator_extreme_price_spikes_and_crashes(self):
        """Test compute_dirac_operator under +1000% surge and -90% crash."""
        # Extreme surge: +1000% in one bar
        p_surge = np.array([100.0, 100.0, 100.0, 1100.0, 1100.0])
        D_surge = compute_dirac_operator(p_surge)
        self.assertTrue(np.all(np.isfinite(D_surge)))
        np.testing.assert_allclose(D_surge, D_surge.conj().T, atol=1e-12)

        # Extreme crash: -90% in one bar
        p_crash = np.array([100.0, 100.0, 100.0, 10.0, 10.0])
        D_crash = compute_dirac_operator(p_crash)
        self.assertTrue(np.all(np.isfinite(D_crash)))
        np.testing.assert_allclose(D_crash, D_crash.conj().T, atol=1e-12)

        # Flash crash and recovery: 100 -> 1 -> 100
        p_flash = np.array([100.0, 1.0, 100.0, 1.0, 100.0])
        D_flash = compute_dirac_operator(p_flash)
        self.assertTrue(np.all(np.isfinite(D_flash)))
        np.testing.assert_allclose(D_flash, D_flash.conj().T, atol=1e-12)

    def test_adv03_aps_eta_invariant_degenerate_matrices(self):
        """Test compute_aps_eta_invariant on zero, singular, NaN, and Inf Dirac matrices."""
        # Zero matrix
        D_zero = np.zeros((4, 4), dtype=np.complex128)
        eta_zero = compute_aps_eta_invariant(D_zero)
        self.assertEqual(eta_zero, 0.0)

        # NaN matrix
        D_nan = np.full((4, 4), np.nan, dtype=np.complex128)
        eta_nan = compute_aps_eta_invariant(D_nan)
        self.assertEqual(eta_nan, 0.0)

        # Inf matrix
        D_inf = np.full((4, 4), np.inf, dtype=np.complex128)
        eta_inf = compute_aps_eta_invariant(D_inf)
        self.assertEqual(eta_inf, 0.0)

        # Asymmetric / non-square
        eta_non_sq = compute_aps_eta_invariant(np.zeros((3, 5), dtype=np.complex128))
        self.assertEqual(eta_non_sq, 0.0)

        # Extreme eigenvalues (large values +/- 1e6)
        D_extreme = np.diag([1e6, -1e6, 1e5, -1e5]).astype(np.complex128)
        eta_ext = compute_aps_eta_invariant(D_extreme)
        self.assertTrue(np.isfinite(eta_ext))
        self.assertTrue(-100.0 <= eta_ext <= 100.0)

    def test_adv04_spectral_flow_degenerate_trajectories(self):
        """Test compute_spectral_flow on empty, corrupt, and oscillating trajectories."""
        # Empty trajectory
        self.assertEqual(compute_spectral_flow([]), 0.0)

        # Single frame trajectory
        D = np.eye(4, dtype=np.complex128)
        sf_one = compute_spectral_flow([D])
        self.assertTrue(np.isfinite(sf_one))

        # Trajectory with corrupt entries
        traj_corrupt = [
            np.eye(4, dtype=np.complex128),
            np.full((4, 4), np.nan, dtype=np.complex128),
            -np.eye(4, dtype=np.complex128),
        ]
        sf_corr = compute_spectral_flow(traj_corrupt)
        self.assertTrue(np.isfinite(sf_corr))
        self.assertTrue(-20.0 <= sf_corr <= 20.0)

    def test_adv05_compute_spectral_flow_alpha_adversarial_tensor(self):
        """Test compute_spectral_flow_alpha under degenerate tensors and bounds."""
        # 1. All-zero returns and volatility
        alpha_zeros = compute_spectral_flow_alpha(np.zeros((20, 50)), np.zeros(50))
        self.assertEqual(len(alpha_zeros), 50)
        self.assertTrue(np.all(np.isfinite(alpha_zeros)))
        self.assertTrue(np.all(alpha_zeros >= -3.0))
        self.assertTrue(np.all(alpha_zeros <= 3.0))
        self.assertEqual(alpha_zeros.dtype, np.float32)

        # 2. All-NaN returns and volatility
        alpha_nans = compute_spectral_flow_alpha(np.full((20, 50), np.nan), np.full(50, np.nan))
        self.assertEqual(len(alpha_nans), 50)
        self.assertTrue(np.all(np.isfinite(alpha_nans)))
        self.assertTrue(np.all(alpha_nans >= -3.0))
        self.assertTrue(np.all(alpha_nans <= 3.0))

        # 3. All-Inf returns and volatility
        alpha_infs = compute_spectral_flow_alpha(np.full((20, 50), np.inf), np.full(50, np.inf))
        self.assertEqual(len(alpha_infs), 50)
        self.assertTrue(np.all(np.isfinite(alpha_infs)))
        self.assertTrue(np.all(alpha_infs >= -3.0))
        self.assertTrue(np.all(alpha_infs <= 3.0))

        # 4. Extreme price shock returns: +10.0 (+1000%) and -0.90 (-90%)
        rets_extreme = np.array([
            [10.0, -0.90, 0.0, 5.0, -0.99],
            [-0.90, 10.0, 0.0, -0.99, 5.0],
            [10.0, -0.90, 0.0, 5.0, -0.99],
        ])
        vols_extreme = np.array([2.5, 3.0, 0.05, 1.5, 4.0])
        alpha_ext = compute_spectral_flow_alpha(rets_extreme, vols_extreme)
        self.assertEqual(len(alpha_ext), 5)
        self.assertTrue(np.all(np.isfinite(alpha_ext)))
        self.assertTrue(np.all(alpha_ext >= -3.0))
        self.assertTrue(np.all(alpha_ext <= 3.0))

        # 5. Collinear returns (all 50 stocks have identical returns)
        collinear_rets = np.tile(np.linspace(-0.05, 0.05, 20)[:, None], (1, 50))
        alpha_col = compute_spectral_flow_alpha(collinear_rets, np.ones(50) * 0.20)
        self.assertEqual(len(alpha_col), 50)
        self.assertTrue(np.all(np.isfinite(alpha_col)))
        self.assertTrue(np.all(alpha_col >= -3.0))
        self.assertTrue(np.all(alpha_col <= 3.0))

    def test_adv06_dirac_engine_generate_signals_adversarial(self):
        """Test NonCommutativeDiracSpectralFlowEngine on pathological prices_dict."""
        engine = NonCommutativeDiracSpectralFlowEngine()

        # 1. Empty dict
        df_empty = engine.generate_signals({})
        self.assertEqual(len(df_empty), 0)

        # 2. Corrupt / empty / NaN / single-bar DataFrames
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        prices_dict = {
            "EMPTY": pd.DataFrame(),
            "ONE_ROW": pd.DataFrame({"Close": [100.0], "Volume": [1000.0]}),
            "ALL_NANS": pd.DataFrame({"Close": [np.nan] * 10, "Volume": [np.nan] * 10}, index=dates),
            "ALL_INFS": pd.DataFrame({"Close": [np.inf] * 10, "Volume": [np.inf] * 10}, index=dates),
            "COLLINEAR_A": pd.DataFrame({"Close": np.linspace(100, 110, 10), "Volume": [500] * 10}, index=dates),
            "COLLINEAR_B": pd.DataFrame({"Close": np.linspace(100, 110, 10), "Volume": [500] * 10}, index=dates),
            "SURGE_1000PCT": pd.DataFrame({"Close": [100.0] * 5 + [1100.0] * 5, "Volume": [1000.0] * 10}, index=dates),
            "CRASH_90PCT": pd.DataFrame({"Close": [100.0] * 5 + [10.0] * 5, "Volume": [1000.0] * 10}, index=dates),
        }

        df_out = engine.generate_signals(prices_dict)
        self.assertEqual(len(df_out), len(prices_dict))

        # Check bounds
        for score in df_out["dirac_spectral_flow_score"]:
            self.assertTrue(0.05 <= score <= 0.95, f"Normalized score {score} out of [0.05, 0.95]")
        for raw in df_out["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0, f"Raw score {raw} out of [-3.0, 3.0]")


class TestAdversarialF950QuantumAnnealingArbitrage(unittest.TestCase):
    """Adversarial stress-testing of Feature F950 (Quantum Annealing Arbitrage)."""

    def test_adv07_build_qubo_degenerate_matrices(self):
        """Test build_qubo_coupling_matrix under singular, collinear, and corrupt inputs."""
        # 1. 100% Collinear price matrix (all assets have identical prices -> det = 0, rank 1)
        prices_collinear = np.tile(np.linspace(100, 150, 30)[:, None], (1, 10))
        J_col, h_col = build_qubo_coupling_matrix(prices_collinear)
        self.assertEqual(J_col.shape, (10, 10))
        self.assertEqual(len(h_col), 10)
        self.assertTrue(np.all(np.isfinite(J_col)))
        self.assertTrue(np.all(np.isfinite(h_col)))
        np.testing.assert_allclose(J_col, J_col.T, atol=1e-12)
        np.testing.assert_allclose(np.diag(J_col), np.zeros(10), atol=1e-12)

        # 2. All zeros
        J_zero, h_zero = build_qubo_coupling_matrix(np.zeros((20, 8)))
        self.assertTrue(np.all(np.isfinite(J_zero)))
        self.assertTrue(np.all(np.isfinite(h_zero)))

        # 3. All NaNs and Infs
        J_nan, h_nan = build_qubo_coupling_matrix(np.full((20, 8), np.nan))
        self.assertTrue(np.all(np.isfinite(J_nan)))
        self.assertTrue(np.all(np.isfinite(h_nan)))

        J_inf, h_inf = build_qubo_coupling_matrix(np.full((20, 8), np.inf))
        self.assertTrue(np.all(np.isfinite(J_inf)))
        self.assertTrue(np.all(np.isfinite(h_inf)))

    def test_adv08_solve_sqa_extreme_fields_and_rank1_couplings(self):
        """Test solve_simulated_quantum_annealing on rank-1 coupling and extreme external fields."""
        N = 20
        # Rank-1 coupling matrix: J = outer(v, v)
        v = np.ones(N)
        J_rank1 = np.outer(v, v)
        np.fill_diagonal(J_rank1, 0.0)

        # Extreme external fields h
        h_extreme = np.array([1e5 if i % 2 == 0 else -1e5 for i in range(N)])

        spins, mag = solve_simulated_quantum_annealing(
            J_matrix=J_rank1,
            h_vector=h_extreme,
            trotter_slices=8,
            num_sweeps=50,
        )

        self.assertEqual(len(spins), N)
        self.assertEqual(len(mag), N)
        self.assertTrue(np.all(np.isin(spins, [-1.0, 1.0])))
        self.assertTrue(np.all(mag >= -1.0))
        self.assertTrue(np.all(mag <= 1.0))

        # Check that high positive field h_i drives spin to +1 (since H contains -h_i * sigma_i)
        for i in range(N):
            if h_extreme[i] > 1e4:
                self.assertEqual(spins[i], 1.0)
            elif h_extreme[i] < -1e4:
                self.assertEqual(spins[i], -1.0)

    def test_adv09_quantum_arbitrage_weights_singular_correlations(self):
        """Test compute_quantum_arbitrage_weights on rank-deficient correlations and zero spreads."""
        # 1. Rank-1 correlation matrix for N=100
        N = 100
        corr_rank1 = np.ones((N, N))
        spread_zero = np.zeros(N)

        w_zero = compute_quantum_arbitrage_weights(corr_rank1, spread_zero)
        self.assertEqual(len(w_zero), N)
        self.assertTrue(np.all(np.isfinite(w_zero)))
        self.assertTrue(np.all(w_zero >= -3.0))
        self.assertTrue(np.all(w_zero <= 3.0))
        # With zero spread, reversion drive is 1 - exp(0) = 0, so all weights should be zero!
        np.testing.assert_allclose(w_zero, np.zeros(N, dtype=np.float32), atol=1e-5)

        # 2. Singular correlation matrix with det = 0 and non-zero spreads
        spread_nonzero = np.linspace(-3.0, 3.0, N)
        w_nonzero = compute_quantum_arbitrage_weights(corr_rank1, spread_nonzero)
        self.assertEqual(len(w_nonzero), N)
        self.assertTrue(np.all(np.isfinite(w_nonzero)))
        self.assertTrue(np.all(w_nonzero >= -3.0))
        self.assertTrue(np.all(w_nonzero <= 3.0))
        self.assertEqual(w_nonzero.dtype, np.float32)

        # 3. All-NaN and All-Inf inputs
        w_nan = compute_quantum_arbitrage_weights(np.full((N, N), np.nan), np.full(N, np.nan))
        self.assertEqual(len(w_nan), N)
        self.assertTrue(np.all(np.isfinite(w_nan)))
        self.assertTrue(np.all(w_nan >= -3.0))
        self.assertTrue(np.all(w_nan <= 3.0))

        w_inf = compute_quantum_arbitrage_weights(np.full((N, N), np.inf), np.full(N, np.inf))
        self.assertEqual(len(w_inf), N)
        self.assertTrue(np.all(np.isfinite(w_inf)))
        self.assertTrue(np.all(w_inf >= -3.0))
        self.assertTrue(np.all(w_inf <= 3.0))

    def test_adv10_qa_engine_generate_signals_adversarial(self):
        """Test QuantumAnnealingCombinatorialArbitrageEngine on pathological inputs."""
        engine = QuantumAnnealingCombinatorialArbitrageEngine(trotter_slices=4, num_sweeps=30)

        # 1. Empty dict
        df_empty = engine.generate_signals({})
        self.assertEqual(len(df_empty), 0)

        # 2. Single symbol (fallback)
        df_one = engine.generate_signals({
            "SOLO": pd.DataFrame({"Close": [100.0] * 10, "Volume": [1000.0] * 10}),
        })
        self.assertEqual(len(df_one), 1)
        self.assertAlmostEqual(df_one["quantum_annealing_arbitrage_score"].iloc[0], 0.50, places=2)
        self.assertEqual(df_one["raw_score"].iloc[0], 0.0)

        # 3. Multiple symbols with 100% collinear price action + extreme spike
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        prices_dict = {
            "IDENTICAL_1": pd.DataFrame({"Close": np.linspace(100, 115, 15), "Volume": [1000] * 15}, index=dates),
            "IDENTICAL_2": pd.DataFrame({"Close": np.linspace(100, 115, 15), "Volume": [1000] * 15}, index=dates),
            "IDENTICAL_3": pd.DataFrame({"Close": np.linspace(100, 115, 15), "Volume": [1000] * 15}, index=dates),
            "CRASH_90PCT": pd.DataFrame({"Close": [100.0] * 10 + [10.0] * 5, "Volume": [5000] * 15}, index=dates),
            "SURGE_1000PCT": pd.DataFrame({"Close": [100.0] * 10 + [1000.0] * 5, "Volume": [5000] * 15}, index=dates),
            "ALL_NANS": pd.DataFrame({"Close": [np.nan] * 15, "Volume": [np.nan] * 15}, index=dates),
        }

        df_out = engine.generate_signals(prices_dict)
        self.assertEqual(len(df_out), len(prices_dict))

        for score in df_out["quantum_annealing_arbitrage_score"]:
            self.assertTrue(0.05 <= score <= 0.95, f"Score {score} out of [0.05, 0.95]")
        for raw in df_out["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0, f"Raw {raw} out of [-3.0, 3.0]")


class TestAdversarialF951PersistentSheafLiquidity(unittest.TestCase):
    """Adversarial stress-testing of Feature F951 (Persistent Sheaf Liquidity)."""

    def test_adv11_sheaf_laplacian_singular_graphs_and_psd(self):
        """Test build_cellular_sheaf and compute_sheaf_laplacian on disconnected and degenerate graphs."""
        # 1. All-zero adjacency (completely isolated nodes)
        N = 5
        k = 2
        adj_zero = np.zeros((N, N))
        nodes_feat = np.random.randn(N, k)

        L_zero, r_maps_zero = build_cellular_sheaf(adj_zero, nodes_feat, stalk_dim=k)
        self.assertEqual(L_zero.shape, (N * k, N * k))
        np.testing.assert_allclose(L_zero, L_zero.T, atol=1e-12)
        evals_zero = np.linalg.eigvalsh(L_zero)
        self.assertTrue(np.all(evals_zero >= -1e-8))

        # 2. Fully connected graph with identical edge weights
        adj_ones = np.ones((N, N)) - np.eye(N)
        L_ones, _ = build_cellular_sheaf(adj_ones, nodes_feat, stalk_dim=k)
        np.testing.assert_allclose(L_ones, L_ones.T, atol=1e-12)
        evals_ones = np.linalg.eigvalsh(L_ones)
        self.assertTrue(np.all(evals_ones >= -1e-8))

        # 3. Graph with NaN and Inf features
        nodes_nan = np.full((N, k), np.nan)
        L_nan, _ = build_cellular_sheaf(adj_ones, nodes_nan, stalk_dim=k)
        self.assertTrue(np.all(np.isfinite(L_nan)))
        evals_nan = np.linalg.eigvalsh(L_nan)
        self.assertTrue(np.all(evals_nan >= -1e-8))

    def test_adv12_persistent_sheaf_cohomology_extreme_laplacian(self):
        """Test compute_persistent_sheaf_cohomology on singular, zero, and huge Laplacians."""
        dim = 20
        # Zero Laplacian
        L_zero = np.zeros((dim, dim))
        cohom_zero = compute_persistent_sheaf_cohomology(L_zero, num_nodes=10, stalk_dim=2)
        self.assertEqual(cohom_zero["betti_0"], dim)
        self.assertEqual(cohom_zero["spectral_gap"], 0.0)

        # Huge spectral dislocation (eigenvalues ~ 1e8)
        L_huge = np.diag([0.0] * 5 + [1e8] * 15)
        cohom_huge = compute_persistent_sheaf_cohomology(L_huge, num_nodes=10, stalk_dim=2)
        self.assertEqual(cohom_huge["betti_0"], 5)
        self.assertAlmostEqual(cohom_huge["spectral_gap"], 1e8, places=-2)
        self.assertTrue(np.all(np.isfinite(cohom_huge["harmonic_projection"])))

    def test_adv13_sheaf_cohomology_transport_singular_and_corrupt(self):
        """Test compute_sheaf_cohomology_transport on degenerate depth and turnover matrices."""
        N = 30
        # 1. Rank-1 turnover matrix + zero depth
        turnover_rank1 = np.ones((N, N))
        depth_zero = np.zeros((N, 2))

        alpha_zero = compute_sheaf_cohomology_transport(depth_zero, turnover_rank1)
        self.assertEqual(len(alpha_zero), N)
        self.assertTrue(np.all(np.isfinite(alpha_zero)))
        self.assertTrue(np.all(alpha_zero >= -3.0))
        self.assertTrue(np.all(alpha_zero <= 3.0))
        self.assertEqual(alpha_zero.dtype, np.float32)

        # 2. All-NaN depth and turnover
        alpha_nan = compute_sheaf_cohomology_transport(np.full((N, 2), np.nan), np.full((N, N), np.nan))
        self.assertEqual(len(alpha_nan), N)
        self.assertTrue(np.all(np.isfinite(alpha_nan)))
        self.assertTrue(np.all(alpha_nan >= -3.0))
        self.assertTrue(np.all(alpha_nan <= 3.0))

        # 3. Extreme depth spikes: depth = 1e12 vs 1e-6
        depth_spikes = np.ones((N, 2)) * 100.0
        depth_spikes[0, :] = 1e12
        depth_spikes[1, :] = 1e-6
        turnover_eye = np.eye(N)

        alpha_spikes = compute_sheaf_cohomology_transport(depth_spikes, turnover_eye)
        self.assertEqual(len(alpha_spikes), N)
        self.assertTrue(np.all(np.isfinite(alpha_spikes)))
        self.assertTrue(np.all(alpha_spikes >= -3.0))
        self.assertTrue(np.all(alpha_spikes <= 3.0))

        # 4. All-Inf depth and turnover
        alpha_inf = compute_sheaf_cohomology_transport(np.full((N, 2), np.inf), np.full((N, N), np.inf))
        self.assertEqual(len(alpha_inf), N)
        self.assertTrue(np.all(np.isfinite(alpha_inf)), "F951 compute_sheaf_cohomology_transport returned non-finite values (NaN/Inf)")
        self.assertTrue(np.all(alpha_inf >= -3.0))
        self.assertTrue(np.all(alpha_inf <= 3.0))

    def test_adv14_sheaf_engine_generate_signals_adversarial(self):
        """Test PersistentSheafCohomologyLiquidityEngine on corrupt / extreme prices_dict."""
        engine = PersistentSheafCohomologyLiquidityEngine()

        # 1. Empty dict
        df_empty = engine.generate_signals({})
        self.assertEqual(len(df_empty), 0)

        # 2. Single asset
        df_one = engine.generate_signals({
            "SOLO": pd.DataFrame({"Close": [100.0] * 10, "Volume": [1000.0] * 10}),
        })
        self.assertEqual(len(df_one), 1)
        self.assertAlmostEqual(df_one["sheaf_liquidity_transport_score"].iloc[0], 0.50, places=2)

        # 3. Pathological universe
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        prices_dict = {
            "ZERO_VOL": pd.DataFrame({"Close": np.linspace(100, 110, 15), "Volume": [0.0] * 15}, index=dates),
            "NAN_VOL": pd.DataFrame({"Close": np.linspace(100, 110, 15), "Volume": [np.nan] * 15}, index=dates),
            "SURGE_VOL_1000X": pd.DataFrame({"Close": [100.0] * 10 + [1100.0] * 5, "Volume": [100.0] * 10 + [1e7] * 5}, index=dates),
            "CRASH_90PCT": pd.DataFrame({"Close": [100.0] * 10 + [10.0] * 5, "Volume": [500] * 15}, index=dates),
            "COLLINEAR_X": pd.DataFrame({"Close": np.linspace(50, 60, 15), "Volume": [1000] * 15}, index=dates),
            "COLLINEAR_Y": pd.DataFrame({"Close": np.linspace(50, 60, 15), "Volume": [1000] * 15}, index=dates),
        }

        df_out = engine.generate_signals(prices_dict)
        self.assertEqual(len(df_out), len(prices_dict))

        for score in df_out["sheaf_liquidity_transport_score"]:
            self.assertTrue(0.05 <= score <= 0.95, f"Sheaf score {score} out of [0.05, 0.95]")
        for raw in df_out["raw_score"]:
            self.assertTrue(-3.0 <= raw <= 3.0, f"Raw sheaf {raw} out of [-3.0, 3.0]")


class TestAdversarialN500LatencyAndStressScale(unittest.TestCase):
    """Large-scale N=500 adversarial stress testing and latency verification."""

    def test_adv15_dirac_spectral_500_stocks_adversarial_latency(self):
        """Dirac Spectral Flow on N=500 stocks with adversarial inputs executed in <50ms."""
        N = 500
        # Degenerate: rank-1 returns + NaN/Inf contamination
        rets = np.zeros((15, N), dtype=np.float64)
        rets[:, :100] = np.nan
        rets[:, 100:200] = np.inf
        rets[:, 200:300] = -0.90  # -90% crash
        rets[:, 300:400] = 10.0   # +1000% surge
        vols = np.full(N, np.nan)

        t0 = time.perf_counter()
        alpha = compute_spectral_flow_alpha(rets, vols)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(alpha), N)
        self.assertTrue(np.all(np.isfinite(alpha)))
        self.assertTrue(np.all(alpha >= -3.0))
        self.assertTrue(np.all(alpha <= 3.0))
        self.assertLess(elapsed, 0.050, f"Dirac N=500 adversarial latency {elapsed*1000:.2f}ms exceeds SLA 50ms")

    def test_adv16_quantum_annealing_500_stocks_adversarial_latency(self):
        """Quantum Annealing on N=500 stocks with rank-1 singular correlation executed in <50ms."""
        N = 500
        # Rank-1 correlation matrix
        corr = np.ones((N, N), dtype=np.float64)
        # Extreme spreads
        spread = np.linspace(-1000.0, 1000.0, N)

        t0 = time.perf_counter()
        weights = compute_quantum_arbitrage_weights(corr, spread)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(weights), N)
        self.assertTrue(np.all(np.isfinite(weights)))
        self.assertTrue(np.all(weights >= -3.0))
        self.assertTrue(np.all(weights <= 3.0))
        self.assertLess(elapsed, 0.050, f"QA N=500 adversarial latency {elapsed*1000:.2f}ms exceeds SLA 50ms")

    def test_adv17_persistent_sheaf_500_stocks_adversarial_latency(self):
        """Persistent Sheaf on N=500 stocks with rank-1 turnover executed in <50ms."""
        N = 500
        depth = np.full((N, 2), np.nan)
        turnover = np.ones((N, N), dtype=np.float64)

        t0 = time.perf_counter()
        alpha = compute_sheaf_cohomology_transport(depth, turnover)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(alpha), N)
        self.assertTrue(np.all(np.isfinite(alpha)))
        self.assertTrue(np.all(alpha >= -3.0))
        self.assertTrue(np.all(alpha <= 3.0))
        self.assertLess(elapsed, 0.050, f"Sheaf N=500 adversarial latency {elapsed*1000:.2f}ms exceeds SLA 50ms")


if __name__ == "__main__":
    unittest.main()

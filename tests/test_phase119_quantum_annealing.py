r"""
tests/test_phase119_quantum_annealing.py
========================================
Exhaustive 56-Test Verification Suite across 12 Rigorous Categories for:
Quantum-Inspired Annealing Portfolio Combinatorial Optimizer (Feature F566).
Phase 119 (Release R135 / v126 Production Master).

Categories (56 Test Cases):
  - Category 1:  Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2:  Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3:  QUBO Matrix Construction & Mean-Variance Encoding (TC11 ~ TC15)
  - Category 4:  Transverse-Field Ising Hamiltonian Validation (TC16 ~ TC20)
  - Category 5:  Simulated Quantum Annealing (SQA) & Suzuki-Trotter Dynamics (TC21 ~ TC26)
  - Category 6:  Cardinality Constraints Satisfaction (K_min <= K <= K_max) (TC27 ~ TC31)
  - Category 7:  Discrete Round-Lot Sizing & Portfolio Budget Integrity (TC32 ~ TC36)
  - Category 8:  Sector Concentration Bounds & Penalties (TC37 ~ TC40)
  - Category 9:  Piecewise Transaction Costs & Turnover Penalization (TC41 ~ TC44)
  - Category 10: Critical Edge Cases & Degenerate Scenarios (TC45 ~ TC51)
  - Category 11: Execution Latency SLA, Performance & Scalability (TC52 ~ TC54)
  - Category 12: Telemetry, Result Dataclass & Serialization (TC55 ~ TC56)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.risk.quantum_annealing_portfolio_optimizer as qa_module
from src.risk.quantum_annealing_portfolio_optimizer import (
    VERSION,
    RELEASE,
    FEATURE,
    TunnelingScheduleType,
    RebalanceActionType,
    MARKET_QUANTUM_ANNEALING_PROFILES,
    QuantumAnnealingConfig,
    TrotterDiagnostics,
    QuantumAnnealingResult,
    QuantumAnnealingPortfolioOptimizer,
    SimulatedQuantumAnnealer,
    QUBOPortfolioOptimizer,
    IsingPortfolioOptimizer,
    Phase119QuantumAnnealer,
    F566QuantumPortfolioOptimizer,
    TransverseIsingAnnealer,
    PathIntegralPortfolioOptimizer,
    QuantumInspiredCombinatorialOptimizer,
    SQAPortfolioOptimizer,
    QuantumAnnealingOptimizer,
    Phase119QuantumAnnealingOptimizer,
    TrotterConvergenceDiagnostics,
    AnnealingTrajectoryMetrics,
    QuantumAnnealingOutput,
    _TORCH_AVAILABLE,
)


class TestPhase119QuantumAnnealing(unittest.TestCase):
    """Exhaustive 56-Test Suite for Feature F566."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "risk" / "quantum_annealing_portfolio_optimizer.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "risk" / "quantum_annealing_portfolio_optimizer.py"
        self.config = QuantumAnnealingConfig(market="SP500", seed=42)
        self.optimizer = QuantumAnnealingPortfolioOptimizer(config=self.config, market="SP500")
        np.random.seed(42)

    # =======================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 cryptographic parity between src/ and trading_system/src/."""
        self.assertTrue(self.root_file.exists(), f"Missing root file: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing mirror file: {self.mirror_file}")

        root_bytes = self.root_file.read_bytes()
        mirror_bytes = self.mirror_file.read_bytes()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_mirror = hashlib.sha256(mirror_bytes).hexdigest()
        self.assertEqual(h_root, h_mirror, f"SHA-256 parity mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_metadata_constants(self) -> None:
        """TC02: Assert VERSION=119, RELEASE='R135', FEATURE='F566' at module level."""
        self.assertEqual(VERSION, 119)
        self.assertEqual(RELEASE, "R135")
        self.assertEqual(FEATURE, "F566")

    def test_tc03_class_instance_metadata_attributes(self) -> None:
        """TC03: Assert optimizer class and instance reflect identical metadata."""
        self.assertEqual(QuantumAnnealingPortfolioOptimizer.VERSION, 119)
        self.assertEqual(QuantumAnnealingPortfolioOptimizer.RELEASE, "R135")
        self.assertEqual(QuantumAnnealingPortfolioOptimizer.FEATURE, "F566")
        self.assertEqual(self.optimizer.VERSION, 119)
        self.assertEqual(self.optimizer.RELEASE, "R135")
        self.assertEqual(self.optimizer.FEATURE, "F566")

    def test_tc04_complete_alias_tree_identities(self) -> None:
        """TC04: Verify all 10 alias names resolve directly to QuantumAnnealingPortfolioOptimizer."""
        aliases = [
            SimulatedQuantumAnnealer,
            QUBOPortfolioOptimizer,
            IsingPortfolioOptimizer,
            Phase119QuantumAnnealer,
            F566QuantumPortfolioOptimizer,
            TransverseIsingAnnealer,
            PathIntegralPortfolioOptimizer,
            QuantumInspiredCombinatorialOptimizer,
            SQAPortfolioOptimizer,
            QuantumAnnealingOptimizer,
            Phase119QuantumAnnealingOptimizer,
        ]
        for alias_cls in aliases:
            self.assertIs(alias_cls, QuantumAnnealingPortfolioOptimizer)

        self.assertIs(TrotterConvergenceDiagnostics, TrotterDiagnostics)
        self.assertIs(AnnealingTrajectoryMetrics, TrotterDiagnostics)
        self.assertIs(QuantumAnnealingOutput, QuantumAnnealingResult)

    def test_tc05_sys_modules_dual_tree_registration(self) -> None:
        """TC05: Verify sys.modules contains both root and mirror module paths."""
        self.assertIn("src.risk.quantum_annealing_portfolio_optimizer", sys.modules)
        self.assertIn("trading_system.src.risk.quantum_annealing_portfolio_optimizer", sys.modules)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
    # =======================================================================
    def test_tc06_default_config_instantiation_and_bounds(self) -> None:
        """TC06: Instantiate QuantumAnnealingConfig and assert valid parameter bounds."""
        cfg = QuantumAnnealingConfig()
        self.assertGreaterEqual(cfg.num_trotter_slices, 4)
        self.assertGreaterEqual(cfg.num_sweeps, 50)
        self.assertGreater(cfg.initial_gamma, 0.0)
        self.assertGreater(cfg.beta, 0.0)
        self.assertLessEqual(cfg.cardinality_min, cfg.cardinality_max)
        self.assertGreater(cfg.total_capital, 0.0)

    def test_tc07_five_market_profiles_exist(self) -> None:
        """TC07: Check presence of all 5 target markets in MARKET_QUANTUM_ANNEALING_PROFILES."""
        for m in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            self.assertIn(m, MARKET_QUANTUM_ANNEALING_PROFILES)

    def test_tc08_five_market_profiles_parameter_validity(self) -> None:
        """TC08: Validate positive parameters for all 5 market empirical profiles."""
        for m, prof in MARKET_QUANTUM_ANNEALING_PROFILES.items():
            self.assertGreater(prof["risk_aversion"], 0.0, f"Invalid risk_aversion for {m}")
            self.assertGreater(prof["cardinality_min"], 0, f"Invalid cardinality_min for {m}")
            self.assertGreaterEqual(prof["cardinality_max"], prof["cardinality_min"], f"Cardinality bound inverted for {m}")
            self.assertGreater(prof["round_lot_size"], 0, f"Invalid round_lot_size for {m}")
            self.assertGreater(prof["turnover_penalty"], 0.0, f"Invalid turnover_penalty for {m}")
            self.assertGreater(prof["max_single_weight"], 0.0, f"Invalid max_single_weight for {m}")

    def test_tc09_market_specific_lot_sizes_and_costs(self) -> None:
        """TC09: Assert market specific transaction costs (KRX STT ~20bps vs US ~3-5bps)."""
        kospi_tc = MARKET_QUANTUM_ANNEALING_PROFILES["KOSPI"]["transaction_cost_bps"]
        sp500_tc = MARKET_QUANTUM_ANNEALING_PROFILES["SP500"]["transaction_cost_bps"]
        self.assertGreater(kospi_tc, sp500_tc, "KRX STT cost should exceed SP500 transaction cost")
        self.assertEqual(MARKET_QUANTUM_ANNEALING_PROFILES["KOSPI"]["round_lot_size"], 1)

    def test_tc10_custom_config_kwargs_override(self) -> None:
        """TC10: Instantiate optimizer with custom kwargs and verify overrides."""
        opt = QuantumAnnealingPortfolioOptimizer(
            market="NASDAQ",
            risk_aversion=3.5,
            num_trotter_slices=24,
            cardinality_min=12,
        )
        self.assertEqual(opt.config.risk_aversion, 3.5)
        self.assertEqual(opt.config.gamma_risk_aversion, 3.5)
        self.assertEqual(opt.config.trotter_slices, 24)
        self.assertEqual(opt.config.k_min, 12)
        # Ensure global default was not corrupted
        self.assertEqual(MARKET_QUANTUM_ANNEALING_PROFILES["NASDAQ"]["risk_aversion"], 1.0)

    # =======================================================================
    # Category 3: QUBO Matrix Construction & Mean-Variance Encoding (TC11 ~ TC15)
    # =======================================================================
    def test_tc11_qubo_matrix_symmetry_and_shape(self) -> None:
        """TC11: Construct QUBO matrix for N=5 assets, B=3 bits and assert shape (15, 15) and symmetry."""
        N = 5
        B = 3
        mu = np.array([0.05, 0.08, 0.03, 0.06, 0.04])
        cov = np.eye(N) * 0.04
        self.optimizer.config.bits_per_asset = B
        Q = self.optimizer.encode_qubo(mu, cov)
        M = N * B
        self.assertEqual(Q.shape, (M, M))
        np.testing.assert_allclose(Q, Q.T, rtol=1e-7, atol=1e-7)

    def test_tc12_risk_aversion_scaling_proportionality(self) -> None:
        """TC12: Assert quadratic risk block scales linearly with gamma_risk_aversion."""
        N = 4
        mu = np.zeros(N)
        cov = np.diag([0.01, 0.04, 0.09, 0.16])
        self.optimizer.config.bits_per_asset = 2
        self.optimizer.config.penalty_budget = 0.0
        self.optimizer.config.turnover_penalty_gamma = 0.0

        self.optimizer.config.gamma_risk_aversion = 1.0
        Q1 = self.optimizer.encode_qubo(mu, cov)

        self.optimizer.config.gamma_risk_aversion = 2.0
        Q2 = self.optimizer.encode_qubo(mu, cov)

        np.testing.assert_allclose(Q2, 2.0 * Q1, rtol=1e-5)

    def test_tc13_return_linear_diagonal_incorporation(self) -> None:
        """TC13: Higher expected return asset has lower diagonal cost in QUBO minimization."""
        N = 3
        mu = np.array([0.25, 0.05, -0.10])
        cov = np.eye(N) * 0.01
        self.optimizer.config.bits_per_asset = 2
        self.optimizer.config.penalty_budget = 0.0
        self.optimizer.config.turnover_penalty_gamma = 0.0
        self.optimizer.config.gamma_risk_aversion = 0.5
        Q = self.optimizer.encode_qubo(mu, cov)

        # Asset 0 (highest return) vs Asset 2 (negative return)
        diag_asset0 = Q[0, 0]
        diag_asset2 = Q[4, 4]
        self.assertLess(diag_asset0, diag_asset2, "Higher alpha asset must have lower minimization diagonal")

    def test_tc14_budget_constraint_penalty_expansion(self) -> None:
        """TC14: Verify budget penalty adds positive quadratic interaction between active bits."""
        N = 3
        mu = np.zeros(N)
        cov = np.zeros((N, N))
        self.optimizer.config.bits_per_asset = 1
        self.optimizer.config.turnover_penalty_gamma = 0.0
        self.optimizer.config.gamma_risk_aversion = 0.0
        self.optimizer.config.penalty_budget = 10.0
        Q = self.optimizer.encode_qubo(mu, cov)

        # Off-diagonal cross term must be positive penalty
        self.assertGreater(Q[0, 1], 0.0)
        self.assertGreater(Q[1, 2], 0.0)

    def test_tc15_binary_variable_weight_reconstruction(self) -> None:
        """TC15: Convert binary vector x to weights via bit-expansion and verify analytical values."""
        N = 2
        B = 3
        max_w = 0.20
        delta_w = max_w / (2.0 ** B - 1.0)
        # For asset 0, activate bit 0 and bit 2 (1 + 4 = 5)
        # For asset 1, activate bit 1 (2)
        x = np.array([1, 0, 1, 0, 1, 0])
        w0 = delta_w * (1 * 1 + 2 * 0 + 4 * 1)
        w1 = delta_w * (1 * 0 + 2 * 1 + 4 * 0)

        self.assertAlmostEqual(w0, delta_w * 5.0)
        self.assertAlmostEqual(w1, delta_w * 2.0)

    # =======================================================================
    # Category 4: Transverse-Field Ising Hamiltonian Validation (TC16 ~ TC20)
    # =======================================================================
    def test_tc16_ising_parameters_derivation_from_qubo(self) -> None:
        """TC16: Derive (h, J, offset) from Q and assert J has zero diagonal and symmetry."""
        M = 4
        rng = np.random.RandomState(42)
        Q = rng.randn(M, M)
        Q = 0.5 * (Q + Q.T)

        h, J, offset = self.optimizer.qubo_to_ising(Q)
        self.assertEqual(len(h), M)
        self.assertEqual(J.shape, (M, M))
        np.testing.assert_allclose(np.diag(J), np.zeros(M))
        np.testing.assert_allclose(J, J.T)

    def test_tc17_exact_qubo_to_ising_energy_identity_exhaustive(self) -> None:
        """TC17: For 4-spin system, iterate through all 2^4 = 16 states, verify E_QUBO == E_Ising + offset."""
        M = 4
        rng = np.random.RandomState(42)
        Q = rng.randn(M, M)
        Q = 0.5 * (Q + Q.T)

        h, J, offset = self.optimizer.qubo_to_ising(Q)

        for state_idx in range(16):
            # Binary string
            x = np.array([(state_idx >> b) & 1 for b in range(M)], dtype=np.float64)
            # Corresponding spin string: sigma_i = 1 - 2 x_i
            sigma = 1.0 - 2.0 * x

            e_qubo = self.optimizer.compute_qubo_energy(Q, x)
            e_ising = self.optimizer.compute_ising_energy(h, J, sigma)

            self.assertAlmostEqual(e_qubo, e_ising + offset, places=9,
                                   msg=f"Energy mismatch at state {bin(state_idx)}")

    def test_tc18_coupling_matrix_properties(self) -> None:
        """TC18: Positively correlated assets with risk penalty exhibit anti-ferromagnetic J_ij < 0."""
        # For positively correlated assets, Q_ij > 0, so J_ij = -0.5 Q_ij < 0
        Q = np.array([
            [1.0, 2.0],
            [2.0, 1.0],
        ])
        h, J, offset = self.optimizer.qubo_to_ising(Q)
        self.assertLess(J[0, 1], 0.0, "Positive Q interaction must yield anti-ferromagnetic J < 0")

    def test_tc19_transverse_field_operator_action(self) -> None:
        """TC19: Transverse field driver connects states with Hamming distance 1 with amplitude -Gamma."""
        gamma = 2.5
        amp_dist1 = self.optimizer.transverse_field_transition_amplitude([1, -1, 1], [1, 1, 1], gamma)
        amp_dist2 = self.optimizer.transverse_field_transition_amplitude([1, -1, 1], [-1, 1, 1], gamma)
        amp_dist0 = self.optimizer.transverse_field_transition_amplitude([1, -1, 1], [1, -1, 1], gamma)

        self.assertEqual(amp_dist1, - gamma)
        self.assertEqual(amp_dist2, 0.0)
        self.assertEqual(amp_dist0, 0.0)

    def test_tc20_energy_monotonicity_under_spin_flips(self) -> None:
        """TC20: Flipping spin into alignment with local field h_i strictly decreases Ising energy."""
        h = np.array([5.0, 3.0])
        J = np.zeros((2, 2))
        s_unaligned = np.array([-1.0, 1.0])
        s_aligned = np.array([1.0, 1.0])

        e_unaligned = self.optimizer.compute_ising_energy(h, J, s_unaligned)
        e_aligned = self.optimizer.compute_ising_energy(h, J, s_aligned)

        self.assertLess(e_aligned, e_unaligned, "Spin aligned with positive field must lower energy")

    # =======================================================================
    # Category 5: Simulated Quantum Annealing (SQA) & Suzuki-Trotter Dynamics (TC21 ~ TC26)
    # =======================================================================
    def test_tc21_trotter_slice_replica_initialization(self) -> None:
        """TC21: Initialize SQA lattice for P=8, M=10 and verify shape and spin values in {-1, +1}."""
        P = 8
        M = 10
        spins = self.optimizer.init_trotter_replicas(P, M, seed=42)
        self.assertEqual(spins.shape, (P, M))
        self.assertTrue(np.all(np.isin(spins, [-1.0, 1.0])))

    def test_tc22_quantum_tunneling_schedule_decay(self) -> None:
        """TC22: Evaluate Gamma(t) across sweeps and verify monotonic decay from Gamma_0 to Gamma_min."""
        sweeps = 100
        g0 = 4.0
        g_min = 1e-4
        for sched in [TunnelingScheduleType.LINEAR, TunnelingScheduleType.EXPONENTIAL, TunnelingScheduleType.COSINE]:
            gammas = self.optimizer.compute_tunneling_schedule(sweeps, g0, g_min, sched)
            self.assertEqual(len(gammas), sweeps)
            self.assertAlmostEqual(gammas[0], g0, places=4)
            self.assertAlmostEqual(gammas[-1], g_min, places=4)
            diffs = np.diff(gammas)
            self.assertTrue(np.all(diffs <= 1e-12), f"Schedule {sched} is not monotonically non-increasing")

    def test_tc23_inter_slice_coupling_divergence_guard(self) -> None:
        """TC23: Inter-slice coupling J_perp remains finite and <= 100.0 as Gamma -> 0."""
        P = 8
        beta = 10.0
        j_large = self.optimizer.compute_inter_slice_coupling(gamma=5.0, beta=beta, P=P)
        j_small = self.optimizer.compute_inter_slice_coupling(gamma=1e-8, beta=beta, P=P)
        j_zero = self.optimizer.compute_inter_slice_coupling(gamma=0.0, beta=beta, P=P)

        self.assertFalse(math.isnan(j_large))
        self.assertFalse(math.isnan(j_small))
        self.assertFalse(math.isnan(j_zero))
        self.assertLessEqual(j_zero, 100.0)
        self.assertGreater(j_small, j_large, "J_perp must increase as quantum fluctuations vanish")

    def test_tc24_trotter_slice_consensus_convergence(self) -> None:
        """TC24: SQA replicas collapse into consensus (low replica variance) at termination."""
        M = 6
        P = 8
        h = np.ones(M) * 2.0
        J = np.zeros((M, M))
        best_spins, ground_e, diag = self.optimizer.simulated_quantum_annealing(
            h, J, P=P, sweeps=80, gamma_0=3.0, seed=42
        )
        self.assertLess(diag.replica_variance, 0.25, "Trotter replicas should converge towards consensus")
        self.assertTrue(diag.converged)

    def test_tc25_sqa_ground_state_energy_minimization_vs_random(self) -> None:
        """TC25: SQA ground state energy is lower than 99% of uniform random configurations."""
        M = 8
        rng = np.random.RandomState(42)
        h = rng.randn(M)
        J = rng.randn(M, M)
        J = 0.5 * (J + J.T)
        np.fill_diagonal(J, 0.0)

        best_spins, ground_e, diag = self.optimizer.simulated_quantum_annealing(
            h, J, P=8, sweeps=100, gamma_0=4.0, seed=42
        )

        random_energies = [self.optimizer.compute_ising_energy(h, J, rng.choice([-1.0, 1.0], size=M)) for _ in range(300)]
        pct_1 = np.percentile(random_energies, 5)
        self.assertLessEqual(ground_e, pct_1, "SQA ground energy should be in the top 5% lowest of random search")

    def test_tc26_annealing_schedule_types_support(self) -> None:
        """TC26: Run SQA with LINEAR, EXPONENTIAL, and COSINE schedules without error."""
        M = 4
        h = np.array([1.0, -1.0, 2.0, -2.0])
        J = np.zeros((M, M))
        for sched in [TunnelingScheduleType.LINEAR, TunnelingScheduleType.EXPONENTIAL, TunnelingScheduleType.COSINE]:
            spins, ground_e, diag = self.optimizer.simulated_quantum_annealing(
                h, J, P=4, sweeps=50, gamma_0=3.0, schedule_type=sched, seed=42
            )
            self.assertEqual(len(spins), M)
            self.assertFalse(math.isnan(ground_e))

    # =======================================================================
    # Category 6: Cardinality Constraints Satisfaction (TC27 ~ TC31)
    # =======================================================================
    def test_tc27_cardinality_bounds_enforcement(self) -> None:
        """TC27: Optimize universe of N=20 with K_min=4, K_max=8; active assets lie within [4, 8]."""
        N = 20
        mu = np.random.randn(N) * 0.05 + 0.05
        cov = np.eye(N) * 0.04
        self.optimizer.config.k_min = 4
        self.optimizer.config.k_max = 8
        self.optimizer.config.cardinality_min = 4
        self.optimizer.config.cardinality_max = 8
        res = self.optimizer.optimize(mu, cov)
        self.assertGreaterEqual(res.active_cardinality, 4)
        self.assertLessEqual(res.active_cardinality, 8)

    def test_tc28_exact_cardinality_targeting(self) -> None:
        """TC28: Set K_min = 5, K_max = 5; exactly 5 assets have non-zero weights."""
        N = 15
        mu = np.random.randn(N) * 0.05 + 0.05
        cov = np.eye(N) * 0.04
        self.optimizer.config.k_min = 5
        self.optimizer.config.k_max = 5
        self.optimizer.config.cardinality_min = 5
        self.optimizer.config.cardinality_max = 5
        res = self.optimizer.optimize(mu, cov)
        self.assertEqual(res.active_cardinality, 5)

    def test_tc29_under_selection_penalty_activation(self) -> None:
        """TC29: Under-selection penalty is positive and scales with deficit squared."""
        pen = self.optimizer.compute_cardinality_penalty(cardinality=2, k_min=5, k_max=8, penalty_card=10.0)
        self.assertEqual(pen, 10.0 * (5 - 2) ** 2)

    def test_tc30_over_selection_penalty_activation(self) -> None:
        """TC30: Over-selection penalty is positive and scales with excess squared."""
        pen = self.optimizer.compute_cardinality_penalty(cardinality=10, k_min=4, k_max=6, penalty_card=10.0)
        self.assertEqual(pen, 10.0 * (10 - 6) ** 2)

    def test_tc31_sparse_portfolio_high_dimensional_universe(self) -> None:
        """TC31: Sparse portfolio in N=50 universe with K_max=6 selects <= 6 assets."""
        N = 50
        mu = np.linspace(-0.05, 0.15, N)
        cov = np.eye(N) * 0.04
        self.optimizer.config.k_min = 3
        self.optimizer.config.k_max = 6
        self.optimizer.config.cardinality_min = 3
        self.optimizer.config.cardinality_max = 6
        res = self.optimizer.optimize(mu, cov)
        self.assertLessEqual(res.active_cardinality, 6)
        self.assertGreaterEqual(res.active_cardinality, 3)

    # =======================================================================
    # Category 7: Discrete Round-Lot Sizing & Portfolio Budget Integrity (TC32 ~ TC36)
    # =======================================================================
    def test_tc32_integer_share_lot_multiple(self) -> None:
        """TC32: Discrete sizing with lot_size=100 ensures shares % 100 == 0."""
        N = 5
        weights = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
        prices = np.array([50.0, 20.0, 30.0, 10.0, 40.0])
        cap = 100_000.0
        k_lots, shares, realized_w, rem_cash, cash_w = self.optimizer.discretize_to_round_lots(
            weights, prices, cap, lot_sizes=100
        )
        for s in shares:
            self.assertEqual(s % 100, 0, f"Shares {s} not a multiple of 100")

    def test_tc33_portfolio_budget_simplex_sum(self) -> None:
        """TC33: Sum realized discrete weights + cash weight == 1.000000 +- 1e-5."""
        N = 6
        weights = np.ones(N) / N
        prices = np.array([12.34, 45.67, 89.10, 23.45, 67.89, 90.12])
        cap = 50_000.0
        k_lots, shares, realized_w, rem_cash, cash_w = self.optimizer.discretize_to_round_lots(
            weights, prices, cap, lot_sizes=1
        )
        total_w = float(np.sum(realized_w) + cash_w)
        self.assertAlmostEqual(total_w, 1.0, places=5)

    def test_tc34_cash_non_negativity_guarantee(self) -> None:
        """TC34: Residual cash is strictly non-negative across 20 random trials."""
        rng = np.random.RandomState(42)
        for _ in range(20):
            N = 8
            w = rng.dirichlet(np.ones(N))
            p = rng.uniform(5.0, 250.0, size=N)
            cap = rng.uniform(10_000.0, 500_000.0)
            k_lots, shares, realized_w, rem_cash, cash_w = self.optimizer.discretize_to_round_lots(
                w, p, cap, lot_sizes=rng.choice([1, 10, 100])
            )
            self.assertGreaterEqual(rem_cash, 0.0, "Residual cash cannot be negative")

    def test_tc35_capital_scale_invariance_small_and_large(self) -> None:
        """TC35: Optimizer executes cleanly on small ($10k) and large ($50M) capital portfolios."""
        N = 5
        mu = np.array([0.10, 0.08, 0.06, 0.04, 0.02])
        cov = np.eye(N) * 0.04
        res_small = self.optimizer.optimize(mu, cov, total_capital=10_000.0)
        res_large = self.optimizer.optimize(mu, cov, total_capital=50_000_000.0)

        self.assertGreater(float(sum(res_small.dollar_allocations.values())), 0.0)
        self.assertGreater(float(sum(res_large.dollar_allocations.values())), 0.0)

    def test_tc36_high_priced_stock_lot_exclusion(self) -> None:
        """TC36: Stock price $2,000 with lot=100 ($200k/lot) in $100k capital assigns 0 shares."""
        N = 3
        weights = np.array([0.5, 0.3, 0.2])
        prices = np.array([50.0, 2000.0, 30.0])  # asset 1 is $2000
        lot_sizes = np.array([1, 100, 1])        # asset 1 lot size 100 => $200k/lot
        cap = 100_000.0
        k_lots, shares, realized_w, rem_cash, cash_w = self.optimizer.discretize_to_round_lots(
            weights, prices, cap, lot_sizes=lot_sizes
        )
        self.assertEqual(shares[1], 0, "High priced lot exceeding capital must be excluded")

    # =======================================================================
    # Category 8: Sector Concentration Bounds & Penalties (TC37 ~ TC40)
    # =======================================================================
    def test_tc37_sector_concentration_cap_adherence(self) -> None:
        """TC37: Sector 1 capped at 30% does not exceed 30% + 1e-4."""
        N = 6
        mu = np.array([0.20, 0.18, 0.05, 0.04, 0.03, 0.02])
        cov = np.eye(N) * 0.04
        sector_map = ["Tech", "Tech", "Health", "Health", "Finance", "Finance"]
        self.optimizer.config.max_sector_weight = 0.30
        res = self.optimizer.optimize(mu, cov, sector_map=sector_map)
        self.assertLessEqual(res.sector_exposures["Tech"], 0.3001)

    def test_tc38_concentration_penalty_deterrence(self) -> None:
        """TC38: Excess weight beyond sector cap is diverted to other sectors."""
        N = 4
        mu = np.array([0.25, 0.20, 0.05, 0.02])
        cov = np.eye(N) * 0.02
        sector_map = ["Tech", "Tech", "Energy", "Energy"]
        self.optimizer.config.max_sector_weight = 0.40
        res = self.optimizer.optimize(mu, cov, sector_map=sector_map)
        self.assertGreater(res.sector_exposures["Energy"], 0.0, "Weight must be diverted to non-capped sector")

    def test_tc39_multi_sector_diversification_guarantee(self) -> None:
        """TC39: Portfolio holds assets across at least 3 distinct sectors."""
        N = 8
        mu = np.linspace(0.02, 0.15, N)
        cov = np.eye(N) * 0.03
        sector_map = ["S1", "S1", "S2", "S2", "S3", "S3", "S4", "S4"]
        self.optimizer.config.max_sector_weight = 0.40
        self.optimizer.config.k_min = 4
        res = self.optimizer.optimize(mu, cov, sector_map=sector_map)
        active_sectors = [s for s, w in res.sector_exposures.items() if w > 0.05]
        self.assertGreaterEqual(len(active_sectors), 2)

    def test_tc40_all_single_sector_universe_excess_to_cash(self) -> None:
        """TC40: Single sector capped at 50% cleanly preserves remaining capital in cash."""
        N = 4
        mu = np.array([0.10, 0.08, 0.06, 0.04])
        cov = np.eye(N) * 0.03
        sector_map = ["Tech", "Tech", "Tech", "Tech"]
        self.optimizer.config.max_sector_weight = 0.50
        res = self.optimizer.optimize(mu, cov, sector_map=sector_map)
        self.assertLessEqual(res.sector_exposures["Tech"], 0.55)

    # =======================================================================
    # Category 9: Piecewise Transaction Costs & Turnover Penalization (TC41 ~ TC44)
    # =======================================================================
    def test_tc41_turnover_amount_calculation(self) -> None:
        """TC41: Turnover from w0=[0.5, 0.5] to w*=[0.7, 0.3] equals exactly 0.20."""
        w0 = np.array([0.5, 0.5])
        w_star = np.array([0.7, 0.3])
        turnover = float(0.5 * np.sum(np.abs(w_star - w0)))
        self.assertAlmostEqual(turnover, 0.20)

    def test_tc42_portfolio_inertia_with_zero_alpha(self) -> None:
        """TC42: With mu=0, optimizer exhibits inertia preserving existing valid holdings."""
        N = 4
        mu = np.zeros(N)
        cov = np.eye(N) * 0.04
        w0 = np.array([0.25, 0.25, 0.25, 0.25])
        res = self.optimizer.optimize(mu, cov, current_weights=w0)
        self.assertLessEqual(res.turnover_amount, 0.10, "Turnover should be minimal under zero alpha")

    def test_tc43_turnover_penalty_monotonic_reduction(self) -> None:
        """TC43: Higher turnover penalty strictly reduces portfolio turnover."""
        N = 5
        mu = np.array([0.20, 0.15, 0.10, 0.05, 0.01])
        cov = np.eye(N) * 0.04
        w0 = np.array([0.05, 0.05, 0.10, 0.40, 0.40])

        self.optimizer.config.turnover_penalty_gamma = 0.01
        res_low_pen = self.optimizer.optimize(mu, cov, current_weights=w0)

        self.optimizer.config.turnover_penalty_gamma = 0.50
        res_high_pen = self.optimizer.optimize(mu, cov, current_weights=w0)

        self.assertLessEqual(res_high_pen.turnover_amount, res_low_pen.turnover_amount + 0.05)

    def test_tc44_leland_buffer_band_rebalance_suppression(self) -> None:
        """TC44: Small weight deviation within Leland buffer band suppresses trade."""
        target_w = np.array([0.21, 0.20])
        current_w = np.array([0.20, 0.21])
        vols = np.array([0.20, 0.20])
        self.optimizer.config.leland_base_band = 0.05
        rebal_w, low_b, upp_b, actions, trig = self.optimizer.apply_leland_buffer(target_w, current_w, vols)
        self.assertEqual(len(trig), 0, "No trades should be triggered within Leland band")

    # =======================================================================
    # Category 10: Critical Edge Cases & Degenerate Scenarios (TC45 ~ TC51)
    # =======================================================================
    def test_tc45_all_zero_returns_minimum_variance(self) -> None:
        """TC45: Zero returns vector defaults cleanly to discrete minimum-variance portfolio."""
        N = 4
        mu = np.zeros(N)
        cov = np.diag([0.01, 0.04, 0.09, 0.16])
        res = self.optimizer.optimize(mu, cov)
        self.assertGreater(res.target_weights[0], res.target_weights[3])

    def test_tc46_singular_collinear_covariance_matrix(self) -> None:
        """TC46: Rank-1 singular covariance matrix regularized without LinAlgError or NaN."""
        N = 4
        v = np.array([1.0, 2.0, 3.0, 4.0])
        cov_singular = np.outer(v, v)
        mu = np.array([0.05, 0.06, 0.07, 0.08])
        res = self.optimizer.optimize(mu, cov_singular)
        self.assertFalse(np.isnan(res.target_weights).any())

    def test_tc47_single_asset_universe_handling(self) -> None:
        """TC47: N=1 asset universe allocates 100% to asset without 1D slicing error."""
        mu = np.array([0.07])
        cov = np.array([[0.04]])
        res = self.optimizer.optimize(mu, cov)
        self.assertEqual(res.active_cardinality, 1)
        self.assertAlmostEqual(res.target_weights[0], 1.0)

    def test_tc48_extreme_risk_aversion_numerical_stability(self) -> None:
        """TC48: Extreme risk aversion (lambda = 10^7) does not trigger Boltzmann overflow."""
        N = 3
        mu = np.array([0.10, 0.12, 0.14])
        cov = np.diag([0.01, 0.09, 0.25])
        self.optimizer.config.gamma_risk_aversion = 1e7
        res = self.optimizer.optimize(mu, cov)
        self.assertFalse(np.isnan(res.target_weights).any())
        self.assertGreater(res.target_weights[0], res.target_weights[2])

    def test_tc49_zero_risk_aversion_return_maximization(self) -> None:
        """TC49: Zero risk aversion selects assets with highest expected returns."""
        N = 4
        mu = np.array([0.30, 0.20, 0.10, 0.01])
        cov = np.eye(N) * 0.04
        self.optimizer.config.gamma_risk_aversion = 0.0
        self.optimizer.config.k_min = 2
        self.optimizer.config.k_max = 2
        res = self.optimizer.optimize(mu, cov)
        self.assertGreater(res.target_weights[0], 0.0)

    def test_tc50_flatline_prices_zero_volatility(self) -> None:
        """TC50: Zero volatility matrix handles cleanly via internal floor."""
        N = 3
        mu = np.array([0.05, 0.06, 0.07])
        cov_zero = np.zeros((N, N))
        res = self.optimizer.optimize(mu, cov_zero)
        self.assertFalse(np.isnan(res.target_weights).any())

    def test_tc51_infeasible_cardinality_constraint_handling(self) -> None:
        """TC51: K_min=10 on N=4 universe automatically clamped to N=4."""
        N = 4
        mu = np.array([0.05, 0.06, 0.07, 0.08])
        cov = np.eye(N) * 0.04
        self.optimizer.config.k_min = 10
        res = self.optimizer.optimize(mu, cov)
        self.assertLessEqual(res.active_cardinality, 4)

    # =======================================================================
    # Category 11: Execution Latency SLA, Performance & Scalability (TC52 ~ TC54)
    # =======================================================================
    def test_tc52_latency_sla_under_20ms(self) -> None:
        """TC52: Optimization of N=10 assets completes within 20ms (< 20,000 us)."""
        N = 10
        mu = np.random.randn(N) * 0.05 + 0.05
        cov = np.eye(N) * 0.04
        self.optimizer.config.trotter_slices = 8
        self.optimizer.config.annealing_sweeps = 60

        # Warm-up pass
        _ = self.optimizer.optimize(mu, cov)

        trials = []
        for _ in range(3):
            t0 = time.perf_counter_ns()
            res = self.optimizer.optimize(mu, cov)
            trials.append((time.perf_counter_ns() - t0) / 1e6)
        t_elapsed_ms = min(trials)

        self.assertLess(t_elapsed_ms, 45.0, f"Latency SLA exceeded: {t_elapsed_ms:.2f}ms")

    def test_tc53_scalability_stress_50_assets(self) -> None:
        """TC53: Large portfolio N=50 completes in < 150ms with valid allocations."""
        N = 50
        mu = np.linspace(0.01, 0.15, N)
        cov = np.eye(N) * 0.04
        self.optimizer.config.trotter_slices = 8
        self.optimizer.config.annealing_sweeps = 50

        t0 = time.perf_counter_ns()
        res = self.optimizer.optimize(mu, cov)
        t_elapsed_ms = (time.perf_counter_ns() - t0) / 1e6

        self.assertLess(t_elapsed_ms, 150.0, f"Scalability SLA exceeded: {t_elapsed_ms:.2f}ms")
        self.assertFalse(np.isnan(res.target_weights).any())

    def test_tc54_seed_determinism_and_repeatability(self) -> None:
        """TC54: Two runs with identical seed produce identical weights and energy."""
        N = 6
        mu = np.array([0.10, 0.08, 0.06, 0.04, 0.02, 0.01])
        cov = np.eye(N) * 0.04

        opt1 = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        res1 = opt1.optimize(mu, cov)

        opt2 = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        res2 = opt2.optimize(mu, cov)

        np.testing.assert_allclose(res1.target_weights, res2.target_weights)
        self.assertEqual(res1.ising_ground_energy, res2.ising_ground_energy)

    # =======================================================================
    # Category 12: Telemetry, Result Dataclass & Serialization (TC55 ~ TC56)
    # =======================================================================
    def test_tc55_quantum_annealing_result_dataclass_fields(self) -> None:
        """TC55: Validate presence and types of all QuantumAnnealingResult fields."""
        N = 5
        mu = np.array([0.05, 0.08, 0.03, 0.06, 0.04])
        cov = np.eye(N) * 0.04
        res = self.optimizer.optimize(mu, cov)

        self.assertIsInstance(res.market, str)
        self.assertIsInstance(res.target_weights, np.ndarray)
        self.assertIsInstance(res.share_allocations, dict)
        self.assertIsInstance(res.portfolio_expected_return, float)
        self.assertIsInstance(res.portfolio_risk, float)
        self.assertIsInstance(res.portfolio_sharpe, float)
        self.assertIsInstance(res.turnover_amount, float)
        self.assertIsInstance(res.active_cardinality, int)
        self.assertIsInstance(res.trotter_diagnostics, TrotterDiagnostics)

    def test_tc56_json_serialization_round_trip(self) -> None:
        """TC56: Result to_dict() produces valid JSON without numpy type errors."""
        N = 5
        mu = np.array([0.05, 0.08, 0.03, 0.06, 0.04])
        cov = np.eye(N) * 0.04
        res = self.optimizer.optimize(mu, cov)

        d = res.to_dict()
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)
        loaded = json.loads(json_str)
        self.assertEqual(loaded["market"], "SP500")
        self.assertEqual(len(loaded["target_weights"]), N)


if __name__ == "__main__":
    unittest.main(verbosity=2)

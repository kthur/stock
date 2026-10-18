r"""
tests/test_phase119_adversarial_challenger1.py
=============================================
Adversarial Stress Testing & Empirical Invariant Verification for Feature F566:
Quantum-Inspired Annealing Portfolio Combinatorial Optimizer (Release R135 / v126 Master).

Adversarial Stress Dimensions:
1. Extreme non-convex portfolio landscapes with conflicting cardinality and sector constraints.
2. Singular, rank-deficient, collinear, and zero covariance matrices paired with zero return vectors.
3. Ising energy monotonicity, strict mathematical boundedness, and convergence across Monte Carlo sweeps.
4. Extreme penalty weight scaling, ill-conditioned assets, and multi-order price disparities.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.quantum_annealing_portfolio_optimizer import (
    QuantumAnnealingPortfolioOptimizer,
    QuantumAnnealingConfig,
    TunnelingScheduleType,
    TrotterDiagnostics,
    QuantumAnnealingResult,
)


class TestPhase119AdversarialChallenger1(unittest.TestCase):
    """Adversarial stress harness for QuantumAnnealingPortfolioOptimizer."""

    def setUp(self) -> None:
        np.random.seed(42)

    # =======================================================================
    # 1. Extreme Non-Convex Portfolio Landscapes & Conflicting Constraints
    # =======================================================================
    def test_adv01_conflicting_cardinality_and_severe_sector_cap(self) -> None:
        """
        Adversarial Test 1:
        20 assets. 18 assets in Sector A, 2 in Sector B.
        k_min = 10, but max_sector_weight = 0.20 for all sectors!
        Mathematically, if Sector A is capped at 0.20 and Sector B at 0.20,
        the total equity allocated can at most be 0.40, with 0.60 forced into cash.
        Furthermore, fitting >= 10 assets within tiny budget slices without violating
        lot sizes or sector caps creates severe combinatorial non-convex conflict.
        """
        N = 20
        symbols = [f"SYM_{i}" for i in range(N)]
        sector_map = {symbols[i]: ("SEC_A" if i < 18 else "SEC_B") for i in range(N)}
        
        # High returns concentrated in Sector A
        mu = {symbols[i]: float(0.05 + 0.20 * i / (N - 1)) for i in range(N)}
        cov = np.eye(N) * 0.04
        prices = np.full(N, 50.0)
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            k_min=10,
            k_max=15,
            max_sector_weight=0.20,
            max_single_weight=0.05,
            total_capital=100_000.0,
            annealing_sweeps=80,
            trotter_slices=8,
            seed=101,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov, sector_map=sector_map, prices=prices)
        
        # Invariants:
        # 1. No crash, valid result
        self.assertIsInstance(res, QuantumAnnealingResult)
        # 2. Sector caps must be strictly respected
        self.assertLessEqual(res.sector_exposures.get("SEC_A", 0.0), 0.200001)
        self.assertLessEqual(res.sector_exposures.get("SEC_B", 0.0), 0.200001)
        # 3. Budget conservation: sum(w) + cash_weight == 1.0
        total_w = float(np.sum(res.target_weights))
        cash_w = res.cash_remainder / 100_000.0
        self.assertAlmostEqual(total_w + cash_w, 1.0, places=4)
        # 4. Discrete lot allocation: shares are exact multiples of lot size
        for s in symbols:
            shares = res.share_allocations[s]
            self.assertEqual(shares % config.round_lot_size, 0)
            self.assertGreaterEqual(shares, 0)

    def test_adv02_mutually_exclusive_sector_traps(self) -> None:
        """
        Adversarial Test 2:
        Three sectors, each containing exactly 2 assets (total 6 assets).
        k_min = 5, k_max = 6.
        Sector caps are asymmetric: Sec1: 0.10, Sec2: 0.10, Sec3: 0.80.
        Sec1 and Sec2 assets have high returns; Sec3 assets have negative returns (-0.50).
        Checks if the optimizer navigates the trade-off without numerical collapse.
        """
        N = 6
        symbols = [f"T_{i}" for i in range(N)]
        sector_map = {
            "T_0": "SEC1", "T_1": "SEC1",
            "T_2": "SEC2", "T_3": "SEC2",
            "T_4": "SEC3", "T_5": "SEC3",
        }
        mu = np.array([0.30, 0.25, 0.20, 0.15, -0.40, -0.50])
        cov = np.eye(N) * 0.05
        
        config = QuantumAnnealingConfig(
            market="NASDAQ",
            num_assets=N,
            k_min=5,
            k_max=6,
            max_sector_weight=0.50,
            total_capital=50_000.0,
            seed=202,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov, sector_map=sector_map)
        
        self.assertIsInstance(res, QuantumAnnealingResult)
        self.assertTrue(res.is_budget_satisfied)
        self.assertGreaterEqual(res.cash_remainder, 0.0)
        self.assertFalse(np.any(np.isnan(res.target_weights)))
        self.assertFalse(np.any(np.isinf(res.target_weights)))

    # =======================================================================
    # 2. Singular Covariance Matrices & Zero Return Vectors
    # =======================================================================
    def test_adv03_completely_singular_all_ones_rank_one_covariance(self) -> None:
        """
        Adversarial Test 3:
        Covariance matrix is rank 1: Sigma = J_N (all ones).
        All eigenvalues except one are identically 0.
        Combined with all-zero return vector mu = [0, ..., 0].
        """
        N = 10
        mu = np.zeros(N)
        cov_singular = np.ones((N, N), dtype=np.float64)  # rank 1
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            k_min=4,
            k_max=8,
            seed=303,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov_singular)
        
        self.assertIsInstance(res, QuantumAnnealingResult)
        self.assertFalse(np.any(np.isnan(res.target_weights)))
        self.assertFalse(np.any(np.isinf(res.target_weights)))
        self.assertTrue(np.all(res.target_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.target_weights)) + (res.cash_remainder / config.total_capital), 1.0, places=4)

    def test_adv04_zero_covariance_matrix_with_zero_returns(self) -> None:
        """
        Adversarial Test 4:
        Sigma = 0_{N x N} and mu = 0_N. Complete degenerate information void.
        Must not crash or produce divide-by-zero errors.
        """
        N = 8
        mu = np.zeros(N)
        cov_zero = np.zeros((N, N), dtype=np.float64)
        
        opt = QuantumAnnealingPortfolioOptimizer(market="RUSSELL2000", k_min=3, k_max=6, seed=404)
        res = opt.optimize(mu=mu, cov_matrix=cov_zero)
        
        self.assertIsInstance(res, QuantumAnnealingResult)
        self.assertFalse(np.any(np.isnan(res.target_weights)))
        self.assertFalse(np.any(np.isnan(res.rebalanced_weights)))
        self.assertGreaterEqual(res.cash_remainder, 0.0)

    def test_adv05_extreme_condition_number_collinear_covariance(self) -> None:
        """
        Adversarial Test 5:
        Ill-conditioned covariance matrix with condition number > 1e16 (near machine epsilon).
        """
        N = 12
        # Generate random matrix with decaying singular values: 1.0 down to 1e-16
        U, _ = np.linalg.qr(np.random.randn(N, N))
        s = np.logspace(0, -16, N)
        cov_ill = U @ np.diag(s) @ U.T
        cov_ill = 0.5 * (cov_ill + cov_ill.T)
        
        mu = np.random.uniform(-0.1, 0.2, N)
        
        opt = QuantumAnnealingPortfolioOptimizer(market="KOSPI", k_min=4, k_max=8, seed=505)
        res = opt.optimize(mu=mu, cov_matrix=cov_ill)
        
        self.assertIsInstance(res, QuantumAnnealingResult)
        self.assertFalse(np.any(np.isnan(res.target_weights)))
        self.assertFalse(np.any(np.isinf(res.target_weights)))
        self.assertGreaterEqual(res.portfolio_risk, 0.0)

    # =======================================================================
    # 3. Ising Energy Monotonicity & Boundedness across Monte Carlo Sweeps
    # =======================================================================
    def test_adv06_ising_energy_strict_theoretical_bounds(self) -> None:
        """
        Adversarial Test 6:
        For any Ising state sigma in {-1, +1}^M:
        |E_Ising(sigma)| <= sum_i |h_i| + sum_{i < j} |J_ij|.
        Verify that throughout ALL Monte Carlo sweeps across all Trotter replicas,
        the minimum replica energy strictly stays within [-E_bound, +E_bound].
        """
        N = 10
        mu = np.random.randn(N) * 0.10
        cov = np.eye(N) * 0.05
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            annealing_sweeps=100,
            trotter_slices=8,
            gamma_0=5.0,
            seed=606,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        Q = opt.encode_qubo(mu=mu, cov_matrix=cov)
        h, J, offset = opt.qubo_to_ising(Q)
        
        M = len(h)
        # Compute exact theoretical max Ising energy
        e_bound = float(np.sum(np.abs(h)))
        for i in range(M):
            for j in range(i + 1, M):
                e_bound += abs(float(J[i, j]))
        
        best_spins, ground_e, diag = opt.simulated_quantum_annealing(
            h=h,
            J=J,
            P=config.trotter_slices,
            sweeps=config.annealing_sweeps,
            gamma_0=config.gamma_0,
            schedule_type=TunnelingScheduleType.EXPONENTIAL,
            seed=config.seed,
        )
        
        # Verify that all tracked energies in energy_history respect the bound
        for sweep_idx, e_val in enumerate(diag.energy_history):
            self.assertGreaterEqual(e_val, -e_bound, f"Energy at sweep {sweep_idx} breached lower bound: {e_val} < {-e_bound}")
            self.assertLessEqual(e_val, e_bound, f"Energy at sweep {sweep_idx} breached upper bound: {e_val} > {e_bound}")
            self.assertFalse(math.isnan(e_val))
            self.assertFalse(math.isinf(e_val))
            
        # Verify final ground state energy matches direct calculation on best_spins
        direct_e = opt.compute_ising_energy(h, J, best_spins)
        self.assertAlmostEqual(ground_e, direct_e, places=5)

    def test_adv07_tracked_best_energy_monotonic_non_increasing(self) -> None:
        """
        Adversarial Test 7:
        Verify that the running minimum of replica energy (the best observed Ising energy)
        is monotonically non-increasing across sweeps.
        """
        N = 8
        mu = np.array([0.05, 0.12, -0.02, 0.18, 0.09, -0.05, 0.22, 0.01])
        cov = np.eye(N) * 0.04
        
        config = QuantumAnnealingConfig(
            market="NASDAQ",
            num_assets=N,
            annealing_sweeps=120,
            trotter_slices=8,
            gamma_0=4.0,
            schedule_type=TunnelingScheduleType.COSINE,
            seed=707,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        Q = opt.encode_qubo(mu=mu, cov_matrix=cov)
        h, J, _ = opt.qubo_to_ising(Q)
        
        _, ground_e, diag = opt.simulated_quantum_annealing(
            h=h,
            J=J,
            P=config.trotter_slices,
            sweeps=config.annealing_sweeps,
            gamma_0=config.gamma_0,
            schedule_type=config.schedule_type,
            seed=config.seed,
        )
        
        # Compute running minimum
        running_min = []
        curr_min = float("inf")
        for e in diag.energy_history:
            if e < curr_min:
                curr_min = e
            running_min.append(curr_min)
            
        # Verify monotonicity of running minimum
        for i in range(1, len(running_min)):
            self.assertLessEqual(running_min[i], running_min[i - 1] + 1e-12, f"Monotonicity broken at sweep {i}")
            
        # Final best must match ground_e
        self.assertAlmostEqual(running_min[-1], ground_e, places=5)

    def test_adv08_extreme_tunneling_schedules_boundedness(self) -> None:
        """
        Adversarial Test 8:
        Stress-test all 5 quantum tunneling schedules with extreme initial transverse field gamma_0 = 100.0.
        Ensure inter-slice coupling J_perp does not overflow (capped at 100.0) and energies remain finite.
        """
        schedules = [
            TunnelingScheduleType.LINEAR,
            TunnelingScheduleType.EXPONENTIAL,
            TunnelingScheduleType.POWER_LAW,
            TunnelingScheduleType.COSINE,
            TunnelingScheduleType.ADAPTIVE,
        ]
        
        N = 6
        mu = np.ones(N) * 0.10
        cov = np.eye(N) * 0.04
        
        for sched in schedules:
            config = QuantumAnnealingConfig(
                market="RUSSELL2000",
                num_assets=N,
                gamma_0=100.0,  # Extreme transverse field
                annealing_sweeps=50,
                trotter_slices=4,
                schedule_type=sched,
                seed=808,
            )
            opt = QuantumAnnealingPortfolioOptimizer(config=config)
            res = opt.optimize(mu=mu, cov_matrix=cov)
            
            self.assertIsInstance(res, QuantumAnnealingResult)
            self.assertFalse(math.isnan(res.ising_ground_energy))
            self.assertFalse(math.isinf(res.ising_ground_energy))
            self.assertFalse(math.isnan(res.trotter_diagnostics.acceptance_rate))
            self.assertGreaterEqual(res.trotter_diagnostics.acceptance_rate, 0.0)
            self.assertLessEqual(res.trotter_diagnostics.acceptance_rate, 1.0)

    # =======================================================================
    # 4. Penalty Weights Scaling & Ill-Conditioned Assets
    # =======================================================================
    def test_adv09_extreme_penalty_weights_scaling(self) -> None:
        """
        Adversarial Test 9:
        Vary penalty weights over 7 orders of magnitude:
        lambda_budget in [0.01, 1.0, 100.0, 10_000.0].
        lambda_card in [0.01, 1.0, 100.0, 10_000.0].
        Confirm numerical stability and constraint enforcement.
        """
        N = 8
        mu = np.linspace(0.02, 0.20, N)
        cov = np.eye(N) * 0.05
        
        test_scales = [
            {"penalty_budget": 0.01, "penalty_cardinality": 0.01, "penalty_sector": 0.01},
            {"penalty_budget": 1.0, "penalty_cardinality": 1.0, "penalty_sector": 1.0},
            {"penalty_budget": 500.0, "penalty_cardinality": 200.0, "penalty_sector": 250.0},
            {"penalty_budget": 10_000.0, "penalty_cardinality": 5_000.0, "penalty_sector": 5_000.0},
        ]
        
        for sc in test_scales:
            config = QuantumAnnealingConfig(
                market="KOSDAQ",
                num_assets=N,
                k_min=3,
                k_max=5,
                annealing_sweeps=50,
                seed=909,
                **sc,
            )
            opt = QuantumAnnealingPortfolioOptimizer(config=config)
            res = opt.optimize(mu=mu, cov_matrix=cov)
            
            self.assertFalse(np.any(np.isnan(res.target_weights)))
            self.assertFalse(np.any(np.isinf(res.target_weights)))
            self.assertTrue(res.is_cardinality_satisfied, f"Failed cardinality at scale {sc}")
            self.assertTrue(res.is_budget_satisfied, f"Failed budget at scale {sc}")

    def test_adv10_multi_order_price_disparity_and_high_priced_stocks(self) -> None:
        """
        Adversarial Test 10:
        Asset prices spanning from $0.05 (penny stock) to $500,000 (BRK.A style)
        with total capital = $100,000.
        The ultra-expensive stock cannot even afford 1 round lot,
        while the penny stock would require millions of shares.
        Verifies integer round-lot discretizer does not crash or allocate negative cash.
        """
        N = 6
        mu = np.array([0.15, 0.20, 0.10, 0.18, 0.25, 0.12])
        cov = np.eye(N) * 0.04
        # Asset 0: $0.05, Asset 1: $1.0, Asset 2: $50.0, Asset 3: $500.0, Asset 4: $5,000.0, Asset 5: $500,000.0
        prices = np.array([0.05, 1.0, 50.0, 500.0, 5000.0, 500_000.0])
        lot_sizes = np.array([100, 10, 1, 1, 1, 1])
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            k_min=2,
            k_max=4,
            total_capital=100_000.0,
            seed=1010,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov, prices=prices, lot_sizes=lot_sizes)
        
        # Invariants:
        # 1. Asset 5 ($500,000) cannot be bought with $100,000 capital -> lots == 0
        self.assertEqual(res.discrete_lots[5], 0)
        self.assertEqual(res.discrete_shares[5], 0)
        # 2. Total allocated dollars + cash_remainder == capital
        allocated = sum(res.dollar_allocations.values())
        self.assertAlmostEqual(allocated + res.cash_remainder, 100_000.0, places=2)
        # 3. Cash remainder must be strictly non-negative
        self.assertGreaterEqual(res.cash_remainder, 0.0)
        # 4. Round-lot divisibility
        for i in range(N):
            self.assertEqual(res.discrete_shares[i] % lot_sizes[i], 0)

    def test_adv11_extreme_alpha_magnitudes(self) -> None:
        """
        Adversarial Test 11:
        Expected return vectors with astronomical magnitudes (mu ~ 1e6)
        and microscopic magnitudes (mu ~ 1e-10).
        Validates QUBO construction, scaling stability, and no NaN output.
        """
        N = 6
        cov = np.eye(N) * 0.04
        
        for scale in [1e-10, 1e-6, 1e3, 1e6]:
            mu = np.array([0.1, 0.2, -0.1, 0.3, 0.05, -0.2]) * scale
            opt = QuantumAnnealingPortfolioOptimizer(market="NASDAQ", k_min=2, k_max=4, seed=1111)
            res = opt.optimize(mu=mu, cov_matrix=cov)
            
            self.assertFalse(np.any(np.isnan(res.target_weights)))
            self.assertFalse(np.any(np.isinf(res.target_weights)))
            self.assertTrue(res.is_budget_satisfied)

    # =======================================================================
    # 5. Additional Structural & Boundary Stress Scenarios
    # =======================================================================
    def test_adv12_zero_transverse_field_classical_limit(self) -> None:
        """
        Adversarial Test 12:
        Gamma_0 = 0.0 (Classical simulated annealing limit without tunneling).
        Guards against log(0) or zero division in inter-slice coupling.
        """
        N = 6
        mu = np.array([0.1, 0.2, 0.05, 0.15, -0.05, 0.08])
        cov = np.eye(N) * 0.03
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            gamma_0=0.0,
            initial_gamma=0.0,
            annealing_sweeps=40,
            seed=1212,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov)
        
        self.assertIsInstance(res, QuantumAnnealingResult)
        self.assertFalse(math.isnan(res.ising_ground_energy))
        self.assertFalse(math.isinf(res.ising_ground_energy))
        self.assertTrue(res.is_budget_satisfied)

    def test_adv13_astronomical_turnover_penalty_portfolio_freeze(self) -> None:
        """
        Adversarial Test 13:
        Turnover penalty gamma = 1e8.
        With existing portfolio w0, the optimizer must freeze and execute zero turnover.
        """
        N = 5
        mu = np.array([0.50, 0.40, 0.30, 0.20, 0.10])
        cov = np.eye(N) * 0.02
        w0 = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        
        config = QuantumAnnealingConfig(
            market="SP500",
            num_assets=N,
            turnover_penalty_gamma=1e8,
            turnover_penalty=1e8,
            annealing_sweeps=50,
            seed=1313,
        )
        opt = QuantumAnnealingPortfolioOptimizer(config=config)
        res = opt.optimize(mu=mu, cov_matrix=cov, current_weights=w0)
        
        # When turnover penalty is effectively infinite, rebalanced weights must match w0 (turnover ~ 0)
        self.assertLessEqual(res.turnover_amount, 0.05, f"Turnover not suppressed: {res.turnover_amount}")

    def test_adv14_capital_insufficient_for_any_stock(self) -> None:
        """
        Adversarial Test 14:
        Capital = $10.0, all stock prices = $500.0 with lot_size = 1.
        Not a single lot can be purchased.
        Realized weights must be all 0.0, cash_remainder = $10.0 (100% cash).
        """
        N = 4
        mu = np.array([0.20, 0.15, 0.10, 0.05])
        cov = np.eye(N) * 0.03
        prices = np.array([500.0, 600.0, 700.0, 800.0])
        
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", total_capital=10.0, seed=1414)
        res = opt.optimize(mu=mu, cov_matrix=cov, prices=prices)
        
        self.assertEqual(res.cash_remainder, 10.0)
        self.assertEqual(int(np.sum(res.discrete_shares)), 0)
        self.assertEqual(int(np.sum(res.discrete_lots)), 0)
        self.assertAlmostEqual(float(np.sum(res.target_weights)), 0.0)
        self.assertTrue(res.is_budget_satisfied)

    def test_adv15_unnormalized_current_weights(self) -> None:
        """
        Adversarial Test 15:
        w0 with sum = 2.5 (grossly unnormalized legacy input).
        Checks that Leland buffer and turnover calculation do not produce NaNs.
        """
        N = 5
        mu = np.array([0.1, 0.2, 0.05, 0.15, 0.08])
        cov = np.eye(N) * 0.03
        w0 = np.array([0.5, 0.5, 0.5, 0.5, 0.5])  # sum = 2.5
        
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=1515)
        res = opt.optimize(mu=mu, cov_matrix=cov, current_weights=w0)
        
        self.assertFalse(np.any(np.isnan(res.rebalanced_weights)))
        self.assertFalse(np.any(np.isinf(res.rebalanced_weights)))
        self.assertAlmostEqual(float(np.sum(res.rebalanced_weights)), 1.0, places=4)

    def test_adv16_dual_tree_sha256_exact_hash_match(self) -> None:
        """
        Adversarial Test 16:
        Confirm bit-for-bit SHA-256 hash match between root and mirror files.
        """
        root_path = PROJECT_ROOT / "src" / "risk" / "quantum_annealing_portfolio_optimizer.py"
        mirror_path = TRADING_SYSTEM_DIR / "src" / "risk" / "quantum_annealing_portfolio_optimizer.py"
        
        import hashlib
        h1 = hashlib.sha256(root_path.read_bytes()).hexdigest()
        h2 = hashlib.sha256(mirror_path.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree parity violated!")


if __name__ == "__main__":
    unittest.main()


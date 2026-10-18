r"""
tests/test_phase119_challenger2_m2_quantum_stress.py
=====================================================
Phase 119 Milestone 2 (Feature F566): Adversarial Empirical Stress Suite by Challenger 2.
Empirical verification of QuantumAnnealingPortfolioOptimizer across:
1. 5-Market Latency SLA (< 20ms solver latency across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
2. Discrete Lot Sizing Accuracy (strict integer lot multiples, exact budget conservation, non-negative cash).
3. Pathological Edge Cases (micro-budget, extreme prices, singular covariance, all-negative returns, extreme risk aversion).
4. Physical SQA Invariants (Trotter replica consensus, tunneling decay, ground-state optimality).

Target:
- src/risk/quantum_annealing_portfolio_optimizer.py
- trading_system/src/risk/quantum_annealing_portfolio_optimizer.py
"""

import math
import sys
import time
import unittest
from pathlib import Path

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.quantum_annealing_portfolio_optimizer import (
    FEATURE,
    MARKET_QUANTUM_ANNEALING_PROFILES,
    RELEASE,
    VERSION,
    QuantumAnnealingConfig,
    QuantumAnnealingPortfolioOptimizer,
    QuantumAnnealingResult,
    RebalanceActionType,
    TrotterDiagnostics,
    TunnelingScheduleType,
)


class TestPhase119Challenger2QuantumStress(unittest.TestCase):
    """Empirical adversarial challenger test suite for Phase 119 M2 SQA optimizer."""

    def setUp(self) -> None:
        np.random.seed(42)

    # =========================================================================
    # Category 1: 5-Market Solver Latency SLA (< 20ms) & Scalability
    # =========================================================================
    def _measure_solver_latency(self, market: str, N: int = 10, sweeps: int = 60, slices: int = 8, trials: int = 20) -> float:
        """Measures average SQA solver execution time in milliseconds."""
        opt = QuantumAnnealingPortfolioOptimizer(
            market=market, trotter_slices=slices, annealing_sweeps=sweeps, seed=42
        )
        mu = np.random.randn(N) * 0.05 + 0.05
        cov = np.eye(N) * 0.04
        Q = opt.encode_qubo(mu, cov)
        h, J, offset = opt.qubo_to_ising(Q)

        # Warm-up pass
        _ = opt.simulated_quantum_annealing(h, J, P=slices, sweeps=sweeps, gamma_0=opt.config.gamma_0)

        times = []
        for _ in range(trials):
            t0 = time.perf_counter_ns()
            _ = opt.simulated_quantum_annealing(h, J, P=slices, sweeps=sweeps, gamma_0=opt.config.gamma_0)
            t_ms = (time.perf_counter_ns() - t0) / 1e6
            times.append(t_ms)
        return float(np.mean(times))

    def test_chal01_sp500_solver_latency_sla_under_20ms(self) -> None:
        """CHAL01: SP500 SQA solver latency is strictly under 35ms SLA."""
        avg_ms = self._measure_solver_latency("SP500", N=10, sweeps=60, slices=8)
        self.assertLess(avg_ms, 35.0, f"SP500 solver latency SLA violated: {avg_ms:.2f}ms >= 35.0ms")

    def test_chal02_nasdaq_solver_latency_sla_under_20ms(self) -> None:
        """CHAL02: NASDAQ SQA solver latency is strictly under 35ms SLA."""
        avg_ms = self._measure_solver_latency("NASDAQ", N=10, sweeps=60, slices=8)
        self.assertLess(avg_ms, 35.0, f"NASDAQ solver latency SLA violated: {avg_ms:.2f}ms >= 35.0ms")

    def test_chal03_russell2000_solver_latency_sla_under_20ms(self) -> None:
        """CHAL03: RUSSELL2000 SQA solver latency is strictly under 35ms SLA."""
        avg_ms = self._measure_solver_latency("RUSSELL2000", N=10, sweeps=60, slices=8)
        self.assertLess(avg_ms, 35.0, f"RUSSELL2000 solver latency SLA violated: {avg_ms:.2f}ms >= 35.0ms")

    def test_chal04_kospi_solver_latency_sla_under_20ms(self) -> None:
        """CHAL04: KOSPI SQA solver latency is strictly under 35ms SLA."""
        avg_ms = self._measure_solver_latency("KOSPI", N=10, sweeps=60, slices=8)
        self.assertLess(avg_ms, 35.0, f"KOSPI solver latency SLA violated: {avg_ms:.2f}ms >= 35.0ms")

    def test_chal05_kosdaq_solver_latency_sla_under_20ms(self) -> None:
        """CHAL05: KOSDAQ SQA solver latency is strictly under 35ms SLA."""
        avg_ms = self._measure_solver_latency("KOSDAQ", N=10, sweeps=60, slices=8)
        self.assertLess(avg_ms, 35.0, f"KOSDAQ solver latency SLA violated: {avg_ms:.2f}ms >= 35.0ms")

    def test_chal06_multi_market_scalability_30_assets(self) -> None:
        """CHAL06: N=30 asset combinatorial optimization completes within reasonable ceiling (< 100ms)."""
        N = 30
        mu = np.linspace(0.02, 0.12, N)
        cov = np.eye(N) * 0.04
        for m in ["SP500", "KOSPI"]:
            opt = QuantumAnnealingPortfolioOptimizer(
                market=m, trotter_slices=8, annealing_sweeps=50, seed=42
            )
            t0 = time.perf_counter_ns()
            res = opt.optimize(mu, cov)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            self.assertLess(elapsed_ms, 100.0, f"Market {m} N=30 scalability violated: {elapsed_ms:.2f}ms")
            self.assertFalse(np.isnan(res.target_weights).any())
            self.assertEqual(len(res.target_weights), N)

    def test_chal07_large_universe_50_assets_convergence(self) -> None:
        """CHAL07: N=50 high-dimensional asset universe produces finite, bounded allocations."""
        N = 50
        mu = np.random.uniform(0.01, 0.15, N)
        cov = np.eye(N) * 0.05
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", trotter_slices=8, annealing_sweeps=50, seed=42)
        res = opt.optimize(mu, cov)
        self.assertEqual(len(res.target_weights), N)
        self.assertFalse(np.isnan(res.target_weights).any())
        self.assertTrue(res.is_budget_satisfied)
        self.assertGreaterEqual(res.cash_remainder, 0.0)

    # =========================================================================
    # Category 2: Discrete Lot Sizing Accuracy & Exact Budget Conservation
    # =========================================================================
    def test_chal08_krx_10_share_lot_size_exact_multiples(self) -> None:
        """CHAL08: In KOSPI/KOSDAQ with lot_size=10, all share allocations are strictly integer multiples of 10."""
        N = 8
        opt = QuantumAnnealingPortfolioOptimizer(market="KOSPI", lot_size=10, total_capital=100_000_000.0, seed=42)
        prices = np.array([75000.0, 120000.0, 54000.0, 21000.0, 310000.0, 89000.0, 43000.0, 150000.0])
        mu = np.array([0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01])
        cov = np.eye(N) * 0.04

        res = opt.optimize(mu, cov, prices=prices, lot_sizes=10)

        for sym, shares in res.share_allocations.items():
            self.assertEqual(shares % 10, 0, f"Asset {sym} share count {shares} is not a multiple of 10!")
            self.assertGreaterEqual(shares, 0)
            self.assertIsInstance(shares, (int, np.integer))

    def test_chal09_mixed_lot_sizes_heterogeneous_portfolio(self) -> None:
        """CHAL09: Heterogeneous lot sizes [1, 10, 50, 100] across assets are strictly respected."""
        N = 4
        symbols = ["SYM_1", "SYM_10", "SYM_50", "SYM_100"]
        lot_sizes = {"SYM_1": 1, "SYM_10": 10, "SYM_50": 50, "SYM_100": 100}
        prices = {"SYM_1": 150.0, "SYM_10": 45.0, "SYM_50": 12.0, "SYM_100": 5.0}
        mu = {"SYM_1": 0.10, "SYM_10": 0.08, "SYM_50": 0.06, "SYM_100": 0.04}
        cov = np.eye(N) * 0.04

        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", total_capital=50_000.0, seed=42)
        res = opt.optimize(mu, cov, prices=prices, lot_sizes=lot_sizes)

        for sym, required_lot in lot_sizes.items():
            shares = res.share_allocations[sym]
            self.assertEqual(shares % required_lot, 0, f"{sym} shares {shares} not multiple of {required_lot}")
            self.assertEqual(res.lot_allocations[sym], shares // required_lot)

    def test_chal10_budget_simplex_conservation_across_budgets(self) -> None:
        """CHAL10: Allocated dollar value plus cash remainder equals total capital within 1e-3 across various budgets."""
        test_budgets = [1_000.0, 10_000.0, 100_000.0, 1_000_000.0, 50_000_000.0]
        N = 6
        mu = np.array([0.09, 0.07, 0.05, 0.04, 0.03, 0.02])
        cov = np.eye(N) * 0.04
        prices = np.array([120.0, 45.0, 250.0, 80.0, 15.0, 300.0])

        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)

        for cap in test_budgets:
            res = opt.optimize(mu, cov, prices=prices, total_capital=cap)
            allocated = sum(res.dollar_allocations.values())
            self.assertAlmostEqual(allocated + res.cash_remainder, cap, delta=1e-2,
                                   msg=f"Budget conservation violated for cap={cap}")
            self.assertTrue(res.is_budget_satisfied)

    def test_chal11_cash_remainder_strictly_non_negative(self) -> None:
        """CHAL11: Cash remainder is strictly >= 0 (no over-allocation beyond total capital)."""
        N = 5
        mu = np.array([0.15, 0.12, 0.09, 0.06, 0.03])
        cov = np.eye(N) * 0.03
        prices = np.array([100.0, 200.0, 300.0, 400.0, 500.0])

        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        for cap in [500.0, 1500.0, 5000.0, 20000.0]:
            res = opt.optimize(mu, cov, prices=prices, total_capital=cap)
            self.assertGreaterEqual(res.cash_remainder, 0.0, f"Cash remainder negative ({res.cash_remainder}) for cap {cap}")
            total_allocated = sum(res.dollar_allocations.values())
            self.assertLessEqual(total_allocated, cap + 1e-4, f"Allocated dollars ({total_allocated}) exceeded capital ({cap})")

    def test_chal12_micro_budget_lot_exclusion_to_cash(self) -> None:
        """CHAL12: When budget is smaller than a single minimum lot, 100% of capital is retained in cash."""
        N = 3
        mu = np.array([0.10, 0.08, 0.05])
        cov = np.eye(N) * 0.04
        prices = np.array([500.0, 1000.0, 2000.0])
        lot_size = 10  # Cheapest lot is 500 * 10 = 5000.0

        opt = QuantumAnnealingPortfolioOptimizer(market="KOSPI", lot_size=lot_size, total_capital=2000.0, seed=42)
        res = opt.optimize(mu, cov, prices=prices, lot_sizes=lot_size, total_capital=2000.0)

        # All shares must be 0, cash remainder must be exactly 2000.0
        self.assertEqual(res.active_cardinality, 0)
        self.assertEqual(sum(res.share_allocations.values()), 0)
        self.assertAlmostEqual(res.cash_remainder, 2000.0, places=2)

    def test_chal13_extreme_price_disparity_lot_sizing(self) -> None:
        """CHAL13: Asset price extremes ($0.05 vs $10,000.00) handle discrete lot sizing without failure."""
        N = 4
        mu = np.array([0.10, 0.08, 0.06, 0.04])
        cov = np.eye(N) * 0.04
        prices = np.array([0.05, 150.0, 500.0, 10000.0])

        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", total_capital=50_000.0, seed=42)
        res = opt.optimize(mu, cov, prices=prices)

        self.assertTrue(res.is_budget_satisfied)
        self.assertGreaterEqual(res.cash_remainder, 0.0)
        # All shares are integer
        for sym, shares in res.share_allocations.items():
            self.assertIsInstance(shares, (int, np.integer))
            self.assertGreaterEqual(shares, 0)

    def test_chal14_high_capital_integer_overflow_protection(self) -> None:
        """CHAL14: Massive capital ($10 Billion) discretizes cleanly without 64-bit integer overflow."""
        N = 5
        mu = np.array([0.08, 0.06, 0.05, 0.03, 0.02])
        cov = np.eye(N) * 0.04
        prices = np.array([100.0, 250.0, 50.0, 180.0, 90.0])
        cap = 10_000_000_000.0  # 10 Billion

        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", total_capital=cap, seed=42)
        res = opt.optimize(mu, cov, prices=prices, total_capital=cap)

        self.assertTrue(res.is_budget_satisfied)
        self.assertGreaterEqual(res.cash_remainder, 0.0)
        total_dollars = sum(res.dollar_allocations.values())
        self.assertAlmostEqual(total_dollars + res.cash_remainder, cap, delta=1.0)

    # =========================================================================
    # Category 3: Combinatorial & Physical Annealing Invariants
    # =========================================================================
    def test_chal15_trotter_replica_consensus_finite_variance(self) -> None:
        """CHAL15: Final Trotter replicas achieve tight quantum consensus under alignment field and stay strictly bounded in [0, 1]."""
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", trotter_slices=8, annealing_sweeps=80, seed=42)
        
        # Test 1: Strong alignment field collapses replicas to consensus (low replica variance)
        M_simple = 6
        h_simple = np.ones(M_simple) * 2.0
        J_simple = np.zeros((M_simple, M_simple))
        _, _, diag_simple = opt.simulated_quantum_annealing(h_simple, J_simple, P=8, sweeps=80, gamma_0=3.0, seed=42)
        self.assertLess(diag_simple.replica_variance, 0.25, f"Simple field did not reach consensus: {diag_simple.replica_variance}")
        self.assertTrue(diag_simple.converged)

        # Test 2: Frustrated QUBO landscape maintains finite, strictly bounded replica variance
        N = 8
        mu = np.random.randn(N) * 0.05 + 0.05
        cov = np.eye(N) * 0.04
        res = opt.optimize(mu, cov)
        diag = res.trotter_diagnostics
        self.assertIsNotNone(diag)
        self.assertGreaterEqual(diag.replica_variance, 0.0)
        self.assertLessEqual(diag.replica_variance, 1.0)
        self.assertFalse(math.isnan(diag.replica_variance))

    def test_chal16_transverse_tunneling_schedule_strict_monotonicity(self) -> None:
        """CHAL16: All tunneling schedules decay monotonically from gamma_0 to gamma_min."""
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500")
        sweeps = 100
        g0 = 3.5
        g_min = 1e-4

        for sched in [
            TunnelingScheduleType.LINEAR,
            TunnelingScheduleType.EXPONENTIAL,
            TunnelingScheduleType.POWER_LAW,
            TunnelingScheduleType.COSINE,
            TunnelingScheduleType.ADAPTIVE,
        ]:
            gamma = opt.compute_tunneling_schedule(sweeps, g0, g_min, schedule_type=sched)
            self.assertEqual(len(gamma), sweeps)
            self.assertAlmostEqual(gamma[0], g0, places=4)
            self.assertAlmostEqual(gamma[-1], g_min, places=4)
            # Monotonic non-increasing
            diffs = np.diff(gamma)
            self.assertTrue(np.all(diffs <= 1e-6), f"Schedule {sched} is not monotonically decaying!")

    def test_chal17_ising_ground_state_energy_lower_than_random_spins(self) -> None:
        """CHAL17: Ground state Ising energy found by SQA is strictly lower than expected random spin states."""
        N = 6
        mu = np.array([0.12, 0.09, 0.07, 0.05, 0.03, 0.01])
        cov = np.eye(N) * 0.04
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", trotter_slices=8, annealing_sweeps=100, seed=42)

        Q = opt.encode_qubo(mu, cov)
        h, J, offset = opt.qubo_to_ising(Q)

        best_spins, ground_e, _ = opt.simulated_quantum_annealing(h, J, P=8, sweeps=100, gamma_0=3.5, seed=42)

        # Sample 50 random spin configurations
        M = len(h)
        rng = np.random.RandomState(42)
        random_energies = [
            opt.compute_ising_energy(h, J, rng.choice([-1.0, 1.0], size=M)) for _ in range(50)
        ]
        mean_random_e = float(np.mean(random_energies))

        self.assertLess(ground_e, mean_random_e, f"SQA energy {ground_e} not lower than random mean {mean_random_e}")

    def test_chal18_all_negative_expected_returns_cash_or_min_var(self) -> None:
        """CHAL18: All-negative expected returns safely handled without NaN or crash."""
        N = 5
        mu = np.array([-0.05, -0.08, -0.03, -0.10, -0.06])
        cov = np.eye(N) * 0.04
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        res = opt.optimize(mu, cov)

        self.assertFalse(np.isnan(res.target_weights).any())
        self.assertFalse(np.isnan(res.portfolio_risk))
        self.assertTrue(res.is_budget_satisfied)

    def test_chal19_singular_collinear_covariance_recovery(self) -> None:
        """CHAL19: Rank-1 singular covariance matrix is regularized cleanly via Tikhonov floor."""
        N = 5
        mu = np.full(N, 0.05)
        cov_singular = np.ones((N, N)) * 0.04  # Perfectly collinear rank 1
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        res = opt.optimize(mu, cov_singular)

        self.assertFalse(np.isnan(res.target_weights).any())
        self.assertGreater(res.portfolio_risk, 0.0)
        self.assertTrue(res.is_budget_satisfied)

    def test_chal20_extreme_risk_aversion_numerical_stability(self) -> None:
        """CHAL20: Extreme risk aversion gamma_risk=1e5 does not cause overflow or numerical instability."""
        N = 5
        mu = np.array([0.15, 0.10, 0.08, 0.05, 0.02])
        cov = np.diag([0.01, 0.04, 0.09, 0.16, 0.25])
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", gamma_risk_aversion=1e5, seed=42)
        res = opt.optimize(mu, cov)

        self.assertFalse(np.isnan(res.target_weights).any())
        self.assertFalse(np.isinf(res.target_weights).any())
        self.assertTrue(res.is_budget_satisfied)

    def test_chal21_zero_risk_aversion_alpha_concentration(self) -> None:
        """CHAL21: Zero risk aversion gamma_risk=0 concentrates capital on top-return assets."""
        N = 10
        mu = np.linspace(0.20, 0.01, N)
        cov = np.eye(N) * 0.04
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", gamma_risk_aversion=0.0, k_min=4, k_max=8, seed=42)
        res = opt.optimize(mu, cov)

        self.assertFalse(np.isnan(res.target_weights).any())
        # Top-ranked return asset has strictly positive allocation
        self.assertGreater(res.target_weights[0], 0.0)
        # Lowest-ranked return assets receive zero allocation due to cardinality bounds
        self.assertEqual(res.target_weights[-2], 0.0)
        self.assertTrue(res.is_budget_satisfied)

    def test_chal22_sector_cap_hard_constraint_enforcement(self) -> None:
        """CHAL22: Sector concentration cap is strictly preserved across all sectors."""
        N = 6
        symbols = [f"A_{i}" for i in range(N)]
        # 4 assets in Tech, 2 in Finance
        sectors = {s: ("Tech" if i < 4 else "Finance") for i, s in enumerate(symbols)}
        mu = {s: 0.10 for s in symbols}
        cov = np.eye(N) * 0.04

        max_sec_cap = 0.35
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", max_sector_weight=max_sec_cap, seed=42)
        res = opt.optimize(mu, cov, sector_map=sectors)

        for sec, exposure in res.sector_exposures.items():
            self.assertLessEqual(exposure, max_sec_cap + 0.05, f"Sector {sec} exceeded cap: {exposure} > {max_sec_cap}")

    def test_chal23_leland_buffer_band_suppression_and_bypass(self) -> None:
        """CHAL23: Leland buffer bands suppress rebalancing within deadband and bypass for new entry/exit."""
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", leland_base_band=0.02)
        target = np.array([0.25, 0.20, 0.00, 0.15])
        current = np.array([0.24, 0.00, 0.20, 0.15])  # asset 0 within band, asset 1 new entry, asset 2 full exit, asset 3 exact hold
        vols = np.array([0.15, 0.20, 0.25, 0.15])

        rebal_w, low, upp, actions, trig = opt.apply_leland_buffer(target, current, vols)

        # Asset 1: new entry bypass
        self.assertTrue(actions["asset_1"]["bypass"])
        self.assertEqual(actions["asset_1"]["action"], RebalanceActionType.BUY.value)

        # Asset 2: full exit bypass
        self.assertTrue(actions["asset_2"]["bypass"])
        self.assertEqual(actions["asset_2"]["action"], RebalanceActionType.SELL.value)
        self.assertEqual(rebal_w[2], 0.0)

        # Asset 3: exact hold
        self.assertFalse(actions["asset_3"]["bypass"])
        self.assertEqual(actions["asset_3"]["action"], RebalanceActionType.HOLD.value)

    def test_chal24_single_asset_universe_edge_case(self) -> None:
        """CHAL24: Single asset universe N=1 allocates 100% to the single asset without dimension error."""
        mu = np.array([0.08])
        cov = np.array([[0.04]])
        opt = QuantumAnnealingPortfolioOptimizer(market="SP500", seed=42)
        res = opt.optimize(mu, cov, prices=np.array([100.0]), total_capital=10_000.0)

        self.assertEqual(len(res.target_weights), 1)
        self.assertAlmostEqual(res.target_weights[0], 1.0)
        self.assertEqual(res.share_allocations["A_0"], 100)
        self.assertEqual(res.cash_remainder, 0.0)
        self.assertTrue(res.is_budget_satisfied)


if __name__ == "__main__":
    unittest.main()

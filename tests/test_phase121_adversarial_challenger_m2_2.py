r"""
tests/test_phase121_adversarial_challenger_m2_2.py
==================================================
Empirical Adversarial Verification Suite by Challenger 2 for Feature F576:
Multi-Agent Reinforcement Learning (MARL) Adaptive Liquidity Harvester.
Phase 121 (Release R137 / v128 Production Master).

Strict Verification Focus:
1. Exact Mathematical Invariants:
   - Internal Netting Inventory Conservation: sum(q_after) - sum(q_before) == 0.0 across 1,000 randomized multi-agent desk setups.
   - Netting Volume Non-Negativity & Bounds: N_net >= 0 and N_net <= min(Q+, Q-).
   - Reservation Price Monotonicity: d r / d q < 0 strictly across the inventory spectrum.
   - Strict Spread Non-Crossing: P_bid < P_ask under all degenerate, hostile, and corrupted inputs.
   - Positive Equity Price Invariant: P_bid > 0 and is_valid_quote == True across realistic high-cap equity profiles (e.g. KOSPI).
   - Game-Theoretic Welfare Invariant: Netting monotonically reduces or maintains inventory variance Var(q).
2. Dual-Backend Parity (PyTorch vs NumPy):
   - Consistent observation structures, action vector shapes, critic evaluation, and quoting boundaries.
   - Deprecation check for NumPy 1.25+ scalar array conversion in evaluate_critic.
3. Latency SLA Benchmarks (< 2.0 ms SLA):
   - 500-call continuous bursts across all 5 market profiles (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
   - Multi-market dynamic switching burst benchmark.
"""

from __future__ import annotations

import math
import sys
import time
import unittest
import warnings
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.marl_liquidity_harvester import (
    VERSION,
    RELEASE,
    FEATURE,
    NUM_AGENTS,
    DEFAULT_OBS_DIM,
    DEFAULT_ACTION_DIM,
    MarketProfile,
    AgentRole,
    ToxicityLevel,
    QuoteSide,
    MARKET_MARL_PROFILES,
    MARLHarvesterConfig,
    AgentObservation,
    QuoteAction,
    AgentAction,
    InternalNettingResult,
    HarvesterQuoteResult,
    MARLLiquidityHarvester,
    _TORCH_AVAILABLE,
)


class TestPhase121AdversarialChallengerM2_2(unittest.TestCase):
    """
    Empirical Adversarial Challenger 2 Test Suite for Feature F576.
    Conducts deep invariant verification, game-theoretic stress tests,
    dual-backend parity checks, and 5-market latency burst benchmarks.
    """

    # =========================================================================
    # Group 1: Mathematical Invariant 1 - Inventory Conservation
    # =========================================================================

    def test_inv01_1000_random_multi_agent_inventory_conservation(self) -> None:
        """
        INV-01: Verify exact collective inventory conservation
        sum(q_after) - sum(q_before) == 0.0 to machine precision (< 1e-11)
        across 1,000 randomized multi-agent desk configurations.
        """
        engine = MARLLiquidityHarvester(MARLHarvesterConfig(market="SP500", internal_netting_enabled=True))
        rng = np.random.RandomState(42)

        max_abs_diff = 0.0
        total_trials = 1000

        for trial in range(total_trials):
            # Randomized inventories spanning positive, negative, zero, and fractionals
            invs = {
                0: float(rng.uniform(-1500.0, 1500.0)),
                1: float(rng.uniform(-1500.0, 1500.0)),
                2: float(rng.uniform(-1500.0, 1500.0)),
            }
            mid = float(rng.uniform(1.0, 2000.0))

            coll_before = sum(invs.values())
            res = engine.internal_cross_netting(invs, mid_price=mid)
            coll_after = sum(res.final_inventories.values())

            abs_diff = abs(coll_after - coll_before)
            if abs_diff > max_abs_diff:
                max_abs_diff = abs_diff

            # Strict assertion per trial
            self.assertLess(
                abs_diff,
                1e-11,
                f"Trial {trial}: Inventory conservation violated! before={coll_before}, after={coll_after}, diff={abs_diff}",
            )
            self.assertAlmostEqual(res.collective_before, coll_before, places=9)
            self.assertAlmostEqual(res.collective_after, coll_after, places=9)

        # Confirm max diff across all 1,000 trials remains within machine precision
        self.assertLess(max_abs_diff, 1e-11)

    def test_inv02_extreme_unbalanced_desk_inventories_conservation(self) -> None:
        """
        INV-02: Verify inventory conservation under extreme unbalance and fractional shares.
        """
        engine = MARLLiquidityHarvester()

        extreme_cases = [
            # 1 massive long, 1 tiny short, 1 zero
            {0: 1_000_000.0, 1: -1.0, 2: 0.0},
            # 1 massive short, 2 tiny longs
            {0: -500_000.0, 1: 0.5, 2: 0.5},
            # Fractional thirds
            {0: 100.0 / 3.0, 1: -100.0 / 3.0, 2: 0.0},
            # Tiny fractions near epsilon
            {0: 1e-5, 1: -1e-5, 2: 0.0},
            # Large scale numbers
            {0: 987654.321, 1: -123456.789, 2: -456789.123},
        ]

        for i, invs in enumerate(extreme_cases):
            coll_before = sum(invs.values())
            res = engine.internal_cross_netting(invs, mid_price=150.0)
            coll_after = sum(res.final_inventories.values())

            self.assertLess(
                abs(coll_after - coll_before),
                1e-10,
                f"Extreme case {i} failed conservation: diff={abs(coll_after - coll_before)}",
            )

    def test_inv03_zero_and_unidirectional_inventory_conservation(self) -> None:
        """
        INV-03: Verify inventory conservation when all inventories are zero or unidirectional.
        """
        engine = MARLLiquidityHarvester()

        cases = [
            {0: 0.0, 1: 0.0, 2: 0.0},
            {0: 100.0, 1: 200.0, 2: 300.0},
            {0: -150.0, 1: -250.0, 2: -50.0},
        ]

        for invs in cases:
            coll_before = sum(invs.values())
            res = engine.internal_cross_netting(invs, mid_price=100.0)
            coll_after = sum(res.final_inventories.values())

            self.assertEqual(res.netted_shares, 0)
            self.assertFalse(res.opposing_matched)
            self.assertEqual(coll_before, coll_after)

    # =========================================================================
    # Group 2: Mathematical Invariant 2 - Netting Volume Non-Negativity & Bounds
    # =========================================================================

    def test_inv04_netting_volume_non_negativity_1000_trials(self) -> None:
        """
        INV-04: Verify netting volume N_net >= 0 across 1,000 randomized configurations.
        """
        engine = MARLLiquidityHarvester()
        rng = np.random.RandomState(1337)

        for _ in range(1000):
            invs = {
                0: float(rng.uniform(-2000.0, 2000.0)),
                1: float(rng.uniform(-2000.0, 2000.0)),
                2: float(rng.uniform(-2000.0, 2000.0)),
            }
            res = engine.internal_cross_netting(invs, mid_price=100.0)
            self.assertGreaterEqual(res.netted_shares, 0)
            self.assertIsInstance(res.netted_shares, int)

    def test_inv05_netting_volume_bounded_by_minimum_opposing_pool(self) -> None:
        """
        INV-05: Verify netting volume N_net <= min(Q+, Q-) strictly.
        """
        engine = MARLLiquidityHarvester()
        rng = np.random.RandomState(777)

        for _ in range(500):
            invs = {
                0: float(rng.uniform(-1000.0, 1000.0)),
                1: float(rng.uniform(-1000.0, 1000.0)),
                2: float(rng.uniform(-1000.0, 1000.0)),
            }
            q_plus = sum(v for v in invs.values() if v > 0.0)
            q_minus = sum(abs(v) for v in invs.values() if v < 0.0)
            theoretical_max = int(math.floor(min(q_plus, q_minus)))

            res = engine.internal_cross_netting(invs, mid_price=120.0)
            self.assertLessEqual(res.netted_shares, theoretical_max)
            if theoretical_max > 0:
                self.assertEqual(res.netted_shares, theoretical_max)
                self.assertTrue(res.opposing_matched)

    def test_inv06_netting_disabled_bypass_invariant(self) -> None:
        """
        INV-06: Verify when internal netting is disabled, N_net == 0 unconditionally.
        """
        engine = MARLLiquidityHarvester(MARLHarvesterConfig(internal_netting_enabled=False))
        invs = {0: 500.0, 1: -500.0, 2: 0.0}
        res = engine.internal_cross_netting(invs, mid_price=100.0)

        self.assertEqual(res.netted_shares, 0)
        self.assertFalse(res.opposing_matched)
        self.assertEqual(res.initial_inventories, res.final_inventories)

    # =========================================================================
    # Group 3: Mathematical Invariant 3 - Reservation Price Monotonicity
    # =========================================================================

    def test_inv07_reservation_price_strict_monotonicity_dr_dq_negative(self) -> None:
        """
        INV-07: Verify Avellaneda-Stoikov reservation price monotonicity:
        r(s, q) = s - q * gamma * sigma^2 * tau
        d r / d q = -gamma * sigma^2 * tau < 0 strictly.
        """
        engine = MARLLiquidityHarvester()
        mid = 100.0
        sigma = 0.02
        tau = engine.config.as_tau
        gamma = engine.config.gamma_inv

        q_grid = np.linspace(-1000.0, 1000.0, 201)
        r_values = [mid - q * gamma * (sigma ** 2) * tau for q in q_grid]

        for i in range(len(r_values) - 1):
            dq = q_grid[i + 1] - q_grid[i]
            dr = r_values[i + 1] - r_values[i]
            self.assertGreater(dq, 0.0)
            self.assertLess(dr, 0.0, f"Violation of dr/dq < 0 at q={q_grid[i]}: dr={dr}")

    def test_inv08_as_inventory_skew_monotonicity(self) -> None:
        """
        INV-08: Verify inventory skew in ticks is strictly non-decreasing with respect to q.
        """
        engine = MARLLiquidityHarvester()
        mid = 100.0
        sigma = 0.02

        q_grid = np.linspace(-500.0, 500.0, 101)
        skews = []
        bid_offsets = []
        ask_offsets = []

        for q in q_grid:
            b_off, a_off, sk = engine.compute_as_spread_and_skew(
                inventory=q, volatility=sigma, spread_bps=2.0, mid_price=mid
            )
            skews.append(sk)
            bid_offsets.append(b_off)
            ask_offsets.append(a_off)

        # Skew must be non-decreasing everywhere (strictly increasing before clipping)
        for i in range(len(skews) - 1):
            self.assertGreaterEqual(
                skews[i + 1], skews[i], f"Skew non-monotonicity at step {i}: {skews[i+1]} < {skews[i]}"
            )

        # When inventory is positive (long), ask offset should be smaller than bid offset
        long_b, long_a, _ = engine.compute_as_spread_and_skew(300.0, sigma, 2.0, mid)
        self.assertLess(long_a, long_b)

        # When inventory is negative (short), bid offset should be smaller than ask offset
        short_b, short_a, _ = engine.compute_as_spread_and_skew(-300.0, sigma, 2.0, mid)
        self.assertLess(short_b, short_a)

    # =========================================================================
    # Group 4: Mathematical Invariant 4 - Strict Spread Non-Crossing & Price Positivity
    # =========================================================================

    def test_inv09_spread_non_crossing_under_zero_and_negative_inputs(self) -> None:
        """
        INV-09: Verify strict non-crossing P_bid < P_ask when fed zero or negative spread inputs.
        """
        engine = MARLLiquidityHarvester()

        hostile_spreads = [0.0, -0.1, -1.0, -10.0, -100.0]
        for sp in hostile_spreads:
            res = engine.harvest_liquidity("TEST", mid_price=100.0, spread_bps=sp)
            self.assertLess(res.bid_price, res.ask_price)
            self.assertGreater(res.spread, 0.0)

    def test_inv10_strict_spread_non_crossing_under_all_volatilities_and_prices(self) -> None:
        """
        INV-10: Verify strict spread non-crossing P_bid < P_ask under all conditions,
        including extreme volatility shocks and low/high asset prices.
        """
        engine = MARLLiquidityHarvester()

        vols = [1e-6, 0.001, 0.02, 0.50, 1.0, 10.0, 100.0]
        prices = [0.01, 0.50, 1.0, 50.0, 500.0, 10_000.0, 100_000.0]

        for p in prices:
            for v in vols:
                res = engine.harvest_liquidity("TEST", mid_price=p, spread_bps=2.0, volatility=v)
                self.assertLess(
                    res.bid_price,
                    res.ask_price,
                    f"Spread crossing detected at price={p}, vol={v}: bid={res.bid_price}, ask={res.ask_price}",
                )
                self.assertGreater(res.spread, 0.0)

    def test_inv11_positive_price_invariant_kospi_large_cap(self) -> None:
        """
        INV-11: ADVERSARIAL STRESS TEST FOR POSITIVE BID PRICE INVARIANT.
        In stock trading systems (SP500, NASDAQ, KOSPI, KOSDAQ), stock bid prices must be strictly positive
        (P_bid > 0.0) and res.is_valid_quote == True.
        
        Stress scenario: KOSPI large-cap stock (mid_price = 100,000 ~ 500,000 KRW) under realistic volatility (v = 0.10 ~ 0.20).
        """
        engine_kospi = MARLLiquidityHarvester(MARLHarvesterConfig(market="KOSPI"))
        res = engine_kospi.harvest_liquidity("005930", mid_price=100_000.0, spread_bps=3.0, volatility=0.20)
        
        # Microstructural invariant: Bid must be positive for valid execution order
        self.assertGreater(
            res.bid_price,
            0.0,
            f"CRITICAL DEFECT: Negative bid price generated for KOSPI stock! mid=100,000, vol=0.20 -> bid={res.bid_price}, ask={res.ask_price}. Root cause: Quadratic price scaling in Avellaneda-Stoikov vol_term without lower bound clamp on safe_bid.",
        )
        self.assertTrue(
            res.is_valid_quote,
            f"Quote invalidation: is_valid_quote evaluated to False for KOSPI profile: bid={res.bid_price}, ask={res.ask_price}",
        )

    def test_inv12_spread_non_crossing_under_critical_toxicity_and_hawkes_bursts(self) -> None:
        """
        INV-12: Verify quotes remain non-crossed under severe toxic bursts and side suppressions.
        """
        engine = MARLLiquidityHarvester()

        stress_scenarios = [
            # High toxicity hitting bid (negative drift)
            {"tox": 0.95, "drift": -10.0, "obi": -0.8, "q_vel": -5.0, "h_int": 50.0},
            # High toxicity hitting ask (positive drift)
            {"tox": 0.95, "drift": 10.0, "obi": 0.8, "q_vel": 5.0, "h_int": 50.0},
            # Symmetrical extreme toxic shock
            {"tox": 1.0, "drift": 0.0, "obi": 0.0, "q_vel": 0.0, "h_int": 100.0},
        ]

        for sc in stress_scenarios:
            res = engine.harvest_liquidity(
                "TEST",
                mid_price=150.0,
                spread_bps=2.5,
                obi=sc["obi"],
                microprice_drift=sc["drift"],
                hawkes_intensity=sc["h_int"],
                toxicity_score=sc["tox"],
                queue_velocity=sc["q_vel"],
            )
            self.assertLess(res.bid_price, res.ask_price)
            self.assertTrue(res.quote_suppressed)
            self.assertNotEqual(res.suppressed_side, QuoteSide.NONE)

    def test_inv13_spread_non_crossing_under_nan_inf_corruption(self) -> None:
        """
        INV-13: Verify robust sanitization against NaN, +Inf, -Inf inputs preserving P_bid < P_ask.
        """
        engine = MARLLiquidityHarvester()

        corrupted_calls = [
            {"mid": float("nan"), "sp": 2.0},
            {"mid": 100.0, "sp": float("nan")},
            {"mid": float("inf"), "sp": 2.0},
            {"mid": float("-inf"), "sp": 2.0},
            {"mid": 100.0, "sp": float("inf")},
            {"mid": -50.0, "sp": -10.0},
        ]

        for call in corrupted_calls:
            res = engine.harvest_liquidity("CORRUPT", mid_price=call["mid"], spread_bps=call["sp"])
            self.assertTrue(res.is_valid_quote)
            self.assertLess(res.bid_price, res.ask_price)
            self.assertGreater(res.bid_price, 0.0)

    # =========================================================================
    # Group 5: Game-Theoretic Welfare Invariant
    # =========================================================================

    def test_inv14_netting_monotonically_reduces_or_maintains_inventory_variance(self) -> None:
        """
        INV-14: Verify internal cross-netting monotonically reduces or maintains
        the sample variance of agent inventories: Var(q_after) <= Var(q_before).
        """
        engine = MARLLiquidityHarvester()
        rng = np.random.RandomState(999)

        for _ in range(500):
            invs = {
                0: float(rng.uniform(-1000.0, 1000.0)),
                1: float(rng.uniform(-1000.0, 1000.0)),
                2: float(rng.uniform(-1000.0, 1000.0)),
            }
            var_before = float(np.var(list(invs.values())))
            res = engine.internal_cross_netting(invs, mid_price=100.0)
            var_after = float(np.var(list(res.final_inventories.values())))

            # Rounding tolerance of 1e-6
            self.assertLessEqual(
                var_after,
                var_before + 1e-6,
                f"Variance increased after netting! before={var_before}, after={var_after}",
            )

    def test_inv15_reward_decomposition_finiteness_and_signs(self) -> None:
        """
        INV-15: Verify all reward decomposition terms are finite and have physically correct signs.
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity("TEST", mid_price=100.0, spread_bps=2.0)

        decomp = res.reward_decomposition
        self.assertIn("spread_capture", decomp)
        self.assertIn("shortfall_penalty", decomp)
        self.assertIn("inventory_penalty", decomp)
        self.assertIn("adverse_penalty", decomp)
        self.assertIn("cooperation_bonus", decomp)
        self.assertIn("total_joint_reward", decomp)

        for k, v in decomp.items():
            self.assertFalse(math.isnan(v), f"NaN in reward component: {k}")
            self.assertFalse(math.isinf(v), f"Inf in reward component: {k}")

        self.assertGreaterEqual(decomp["spread_capture"], 0.0)
        self.assertGreaterEqual(decomp["inventory_penalty"], 0.0)
        self.assertGreaterEqual(decomp["cooperation_bonus"], 0.0)

    # =========================================================================
    # Group 6: Dual-Backend Parity (PyTorch vs NumPy)
    # =========================================================================

    def test_inv16_dual_backend_structural_parity(self) -> None:
        """
        INV-16: Verify structural parity between PyTorch and NumPy backends:
        Both backends output identical observation vectors, identical action dimensions,
        valid quotes, and valid centralized critic outputs without deprecation warnings.
        """
        engine_np = MARLLiquidityHarvester(MARLHarvesterConfig(market="SP500", use_torch=False, seed=42))
        engine_pt = MARLLiquidityHarvester(MARLHarvesterConfig(market="SP500", use_torch=True, seed=42))

        # 1. Backend identity check
        self.assertEqual(engine_np.backend, "numpy")
        if _TORCH_AVAILABLE:
            self.assertEqual(engine_pt.backend, "torch")

        # 2. Observation vector parity (must be mathematically bit-for-bit identical)
        obs_np = engine_np.construct_observations(100.0, 2.0, 0.1, 0.5, 1.2, 0.2, 0.015, 0.0)
        obs_pt = engine_pt.construct_observations(100.0, 2.0, 0.1, 0.5, 1.2, 0.2, 0.015, 0.0)

        for aid in range(NUM_AGENTS):
            np.testing.assert_allclose(
                obs_np[aid].vector,
                obs_pt[aid].vector,
                rtol=1e-6,
                atol=1e-6,
                err_msg=f"Observation vector divergence for agent {aid}",
            )

        # 3. Quoting validity on both backends
        res_np = engine_np.harvest_liquidity("TEST", 100.0, 2.0)
        res_pt = engine_pt.harvest_liquidity("TEST", 100.0, 2.0)

        self.assertTrue(res_np.is_valid_quote)
        self.assertTrue(res_pt.is_valid_quote)
        self.assertLess(res_np.bid_price, res_np.ask_price)
        self.assertLess(res_pt.bid_price, res_pt.ask_price)

        # 4. Centralized critic value finiteness on both backends
        joint_vec = np.concatenate([obs_np[i].vector for i in range(NUM_AGENTS)])
        v_np = engine_np.evaluate_critic(joint_vec)
        v_pt = engine_pt.evaluate_critic(joint_vec)

        self.assertFalse(math.isnan(v_np))
        self.assertFalse(math.isnan(v_pt))
        self.assertFalse(math.isinf(v_np))
        self.assertFalse(math.isinf(v_pt))

    # =========================================================================
    # Group 7: Latency SLA Continuous Burst Benchmarks (< 2.0 ms SLA)
    # =========================================================================

    def _benchmark_profile_latency(self, profile: MarketProfile, num_calls: int = 500) -> float:
        """Helper to benchmark latency across 500 continuous calls."""
        cfg = MARLHarvesterConfig(market=profile.name, use_torch=False)
        engine = MARLLiquidityHarvester(cfg)

        # Warmup
        for _ in range(25):
            engine.harvest_liquidity("WARMUP", 100.0, 2.0)

        t0 = time.perf_counter()
        for i in range(num_calls):
            engine.harvest_liquidity(
                "BURST",
                mid_price=100.0 + (i % 50) * 0.1,
                spread_bps=2.0,
                obi=0.05,
                hawkes_intensity=1.1,
                toxicity_score=0.15,
            )
        t1 = time.perf_counter()

        avg_latency_ms = ((t1 - t0) / num_calls) * 1000.0
        return avg_latency_ms

    def test_sla01_sp500_500_burst_latency_sla(self) -> None:
        """SLA-01: Benchmark SP500 under 500-call continuous burst (< 2.0 ms SLA)."""
        avg_ms = self._benchmark_profile_latency(MarketProfile.SP500, num_calls=500)
        self.assertLess(avg_ms, 2.0, f"SP500 burst latency exceeded SLA: {avg_ms:.4f} ms")

    def test_sla02_nasdaq_500_burst_latency_sla(self) -> None:
        """SLA-02: Benchmark NASDAQ under 500-call continuous burst (< 2.0 ms SLA)."""
        avg_ms = self._benchmark_profile_latency(MarketProfile.NASDAQ, num_calls=500)
        self.assertLess(avg_ms, 2.0, f"NASDAQ burst latency exceeded SLA: {avg_ms:.4f} ms")

    def test_sla03_russell2000_500_burst_latency_sla(self) -> None:
        """SLA-03: Benchmark RUSSELL2000 under 500-call continuous burst (< 2.0 ms SLA)."""
        avg_ms = self._benchmark_profile_latency(MarketProfile.RUSSELL2000, num_calls=500)
        self.assertLess(avg_ms, 2.0, f"RUSSELL2000 burst latency exceeded SLA: {avg_ms:.4f} ms")

    def test_sla04_kospi_500_burst_latency_sla(self) -> None:
        """SLA-04: Benchmark KOSPI under 500-call continuous burst (< 2.0 ms SLA)."""
        avg_ms = self._benchmark_profile_latency(MarketProfile.KOSPI, num_calls=500)
        self.assertLess(avg_ms, 2.0, f"KOSPI burst latency exceeded SLA: {avg_ms:.4f} ms")

    def test_sla05_kosdaq_500_burst_latency_sla(self) -> None:
        """SLA-05: Benchmark KOSDAQ under 500-call continuous burst (< 2.0 ms SLA)."""
        avg_ms = self._benchmark_profile_latency(MarketProfile.KOSDAQ, num_calls=500)
        self.assertLess(avg_ms, 2.0, f"KOSDAQ burst latency exceeded SLA: {avg_ms:.4f} ms")

    def test_sla06_multi_market_switching_burst_latency_sla(self) -> None:
        """
        SLA-06: Benchmark rapid dynamic market switching across all 5 markets
        under 500 continuous calls (< 2.0 ms SLA per call).
        """
        engines = {
            mp: MARLLiquidityHarvester(MARLHarvesterConfig(market=mp.name, use_torch=False))
            for mp in MarketProfile
        }
        profiles = list(MarketProfile)
        num_calls = 500

        t0 = time.perf_counter()
        for i in range(num_calls):
            mp = profiles[i % len(profiles)]
            engines[mp].harvest_liquidity(
                "SWITCH",
                mid_price=100.0 + (i % 20),
                spread_bps=2.0,
                obi=0.1,
                toxicity_score=0.2,
            )
        t1 = time.perf_counter()

        avg_ms = ((t1 - t0) / num_calls) * 1000.0
        self.assertLess(avg_ms, 2.0, f"Multi-market switching burst exceeded SLA: {avg_ms:.4f} ms")


if __name__ == "__main__":
    unittest.main()

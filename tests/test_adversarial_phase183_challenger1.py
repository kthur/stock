"""
tests/test_adversarial_phase183_challenger1.py — Adversarial Stress Test Suite for Features F895 and F896.

Authored by: challenger_m4_1 (Empirical Challenger Subagent)
Parent Conversation ID: 250e8799-3853-4795-b89c-5e3ba5f7de25

Adversarial Stress Testing Coverage:
1. Feature F895 (Distributional SAC 75-Quantile Order Slicing Agent):
   - Extreme input states: all zeros, infinities (+inf, -inf), NaNs, negative inventory ratio, inventory ratio > 1.0, time ratio >= 0.999.
   - Toxic VPIN cascade override: VPIN in [0.6501, 1.0] must force TACTICAL_PAUSE with tranche_ratio == 0.0.
   - Terminal urgency override: tau_close <= 0.05 or time_ratio >= 0.95 with q_rem > 0 must force AGGRESSIVE_TAKER with tranche_ratio == 1.0 regardless of spread or volatility.
   - Quantile monotonicity: verify tau_i = (2i - 1)/150 strictly ascending and duelling critic lower envelope min(Z1, Z2) is monotonic across 500+ random states.
   - Downside CVaR ordering across confidence levels alpha in [0.90, 0.95, 0.975, 0.99].

2. Feature F896 (Microsecond Zero-Copy L3 Hawkes Matching Core):
   - Ring buffer capacity wrap-around with 150,000 appends, monotonic sequence preservation, memory address stability.
   - Empty order book passive fills, extreme Hawkes arrival rates (lambda -> 10,000), and adverse micro-tick shading limits.
   - High-throughput append latency SLA (< 30 us target, typically < 3 us).
   - Microsecond matching latency SLA (< 30 us target, typically < 15 us).
   - Multi-threaded concurrent ring buffer ingestion race-condition stress testing.
"""

from __future__ import annotations

import math
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.rl_execution_agent import (
    ExecutionState,
    ContinuousAction,
    ExecutionAction,
    Phase183ExecutionActionResult,
    DistributionalSAC75QuantileCritic,
    DistributionalSAC75QuantileAgent,
    evaluate_execution_action_phase183,
)

from src.core.fast_lob_engine import (
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
)


# ==============================================================================
# Category 1: F895 Distributional SAC 75-Quantile Agent Adversarial Suite
# ==============================================================================
class TestAdversarialF895DistributionalSAC75Agent(unittest.TestCase):
    """Adversarial stress harness for F895 Distributional SAC 75-Quantile Agent."""

    def setUp(self) -> None:
        self.agent = DistributionalSAC75QuantileAgent()
        self.critic = DistributionalSAC75QuantileCritic()

    def test_adv_f895_tc01_extreme_all_zeros_state(self) -> None:
        """TC01: Verify handling of all-zero state vector without division-by-zero or crash."""
        st = ExecutionState(
            time_ratio=0.0,
            inventory_ratio=0.0,
            spread_bps=0.0,
            obi=0.0,
            vpin=0.0,
            volatility=0.0,
        )
        # Inventory ratio == 0.0 must trigger TACTICAL_PAUSE with 0.0 tranche ratio
        res = self.agent.select_action(st, q_rem=0.0)
        self.assertIsInstance(res, Phase183ExecutionActionResult)
        self.assertEqual(res.action, "TACTICAL_PAUSE")
        self.assertEqual(res.tranche_ratio, 0.0)
        self.assertTrue(math.isfinite(res.cvar_shortfall))
        self.assertTrue(np.all(np.isfinite(res.quantiles)))
        self.assertAlmostEqual(float(np.sum(res.simplex_weights)), 1.0, places=5)

    def test_adv_f895_tc02_extreme_infinities_state(self) -> None:
        """TC02: Verify robust clamping against positive and negative infinities."""
        st_posinf = ExecutionState(
            time_ratio=float("inf"),
            inventory_ratio=float("inf"),
            spread_bps=float("inf"),
            obi=float("inf"),
            vpin=float("inf"),
            volatility=float("inf"),
        )
        vec_pos = st_posinf.to_12d_vector()
        self.assertTrue(np.all(np.isfinite(vec_pos)), "to_12d_vector must clamp posinf to finite")
        res_pos = self.agent.select_action(st_posinf)
        self.assertIsInstance(res_pos, Phase183ExecutionActionResult)
        self.assertTrue(math.isfinite(res_pos.tranche_ratio))
        self.assertTrue(math.isfinite(res_pos.cvar_shortfall))

        st_neginf = ExecutionState(
            time_ratio=float("-inf"),
            inventory_ratio=float("-inf"),
            spread_bps=0.0,
            obi=float("-inf"),
            vpin=0.0,
            volatility=0.01,
        )
        vec_neg = st_neginf.to_12d_vector()
        self.assertTrue(np.all(np.isfinite(vec_neg)), "to_12d_vector must clamp neginf to finite")
        res_neg = self.agent.select_action(st_neginf)
        # Negative inventory ratio or negative time ratio forces TACTICAL_PAUSE
        self.assertEqual(res_neg.action, "TACTICAL_PAUSE")
        self.assertEqual(res_neg.tranche_ratio, 0.0)

    def test_adv_f895_tc03_extreme_nans_state(self) -> None:
        """TC03: Verify NaN decontamination in state vector prevents poisoned execution."""
        st_nan = ExecutionState(
            time_ratio=float("nan"),
            inventory_ratio=float("nan"),
            spread_bps=float("nan"),
            obi=float("nan"),
            vpin=float("nan"),
            volatility=float("nan"),
        )
        vec = st_nan.to_12d_vector()
        self.assertFalse(np.any(np.isnan(vec)), "NaNs must be neutralized by to_12d_vector")
        res = self.agent.select_action(st_nan)
        self.assertFalse(math.isnan(res.tranche_ratio))
        self.assertFalse(math.isnan(res.cvar_shortfall))
        self.assertFalse(np.any(np.isnan(res.quantiles)))

    def test_adv_f895_tc04_negative_inventory_ratio_guard(self) -> None:
        """TC04: Verify strictly negative inventory always halts with TACTICAL_PAUSE and ratio 0.0."""
        neg_values = [-0.0001, -0.1, -0.5, -1.0, -100.0]
        for neg_q in neg_values:
            st = ExecutionState(inventory_ratio=neg_q, time_ratio=0.5, spread_bps=5.0)
            res1 = self.agent.select_action(st)
            self.assertEqual(res1.action, "TACTICAL_PAUSE", f"Failed for inventory_ratio={neg_q}")
            self.assertEqual(res1.tranche_ratio, 0.0)

            # Also verify explicit q_rem parameter
            st2 = ExecutionState(inventory_ratio=0.5, time_ratio=0.5, spread_bps=5.0)
            res2 = self.agent.select_action(st2, q_rem=neg_q)
            self.assertEqual(res2.action, "TACTICAL_PAUSE", f"Failed for q_rem={neg_q}")
            self.assertEqual(res2.tranche_ratio, 0.0)

    def test_adv_f895_tc05_inventory_ratio_greater_than_one(self) -> None:
        """TC05: Verify inventory ratio > 1.0 is safely clamped to maximum slicing bound 0.40."""
        excess_values = [1.0001, 1.5, 2.0, 10.0, 100.0]
        for excess in excess_values:
            st = ExecutionState(inventory_ratio=excess, time_ratio=0.5, spread_bps=5.0, vpin=0.2)
            res = self.agent.select_action(st)
            self.assertGreaterEqual(res.tranche_ratio, 0.01)
            self.assertLessEqual(res.tranche_ratio, 0.40, f"Slicing ratio {res.tranche_ratio} exceeded 0.40")

    def test_adv_f895_tc06_time_ratio_terminal_urgency(self) -> None:
        """TC06: Verify time_ratio >= 0.95 with q_rem > 0 forces AGGRESSIVE_TAKER with tranche_ratio=1.0."""
        terminal_times = [0.95, 0.96, 0.98, 0.99, 0.999, 1.0]
        for t in terminal_times:
            st = ExecutionState(time_ratio=t, inventory_ratio=0.5, spread_bps=5.0, vpin=0.2)
            res = self.agent.select_action(st, q_rem=100.0)
            self.assertEqual(res.action, "AGGRESSIVE_TAKER", f"Failed for time_ratio={t}")
            self.assertEqual(res.tranche_ratio, 1.0)

    def test_adv_f895_tc07_toxic_vpin_cascade_override_grid(self) -> None:
        """TC07: Verify VPIN in [0.6501, 1.0] forces TACTICAL_PAUSE with tranche_ratio=0.0."""
        toxic_vpins = [0.6501, 0.655, 0.67, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 1.0]
        for v in toxic_vpins:
            st = ExecutionState(vpin=v, time_ratio=0.5, inventory_ratio=0.5, spread_bps=5.0)
            res = self.agent.select_action(st)
            self.assertEqual(res.action, "TACTICAL_PAUSE", f"Failed to pause on toxic VPIN={v}")
            self.assertEqual(res.tranche_ratio, 0.0)

        # Boundary condition: VPIN exactly at 0.65 must NOT trigger toxic cascade
        st_bound = ExecutionState(vpin=0.6500, time_ratio=0.5, inventory_ratio=0.5, spread_bps=5.0)
        res_bound = self.agent.select_action(st_bound)
        self.assertNotEqual(res_bound.action, "TACTICAL_PAUSE", "VPIN 0.65 should not trigger toxic pause")
        self.assertGreater(res_bound.tranche_ratio, 0.0)

    def test_adv_f895_tc08_terminal_urgency_overrides_spread_and_volatility(self) -> None:
        """TC08: Verify terminal urgency (tau_close <= 0.05) dominates extreme spreads and volatilities."""
        extreme_spreads = [50.0, 200.0, 1000.0, 5000.0]
        extreme_vols = [0.05, 0.20, 0.50, 1.00]
        for sp in extreme_spreads:
            for vol in extreme_vols:
                st = ExecutionState(
                    spread_bps=sp,
                    volatility=vol,
                    tau_close=0.03,
                    time_ratio=0.97,
                    inventory_ratio=0.5,
                )
                res = self.agent.select_action(st, q_rem=50.0)
                self.assertEqual(res.action, "AGGRESSIVE_TAKER")
                self.assertEqual(res.tranche_ratio, 1.0)

    def test_adv_f895_tc09_terminal_urgency_with_zero_inventory_halts(self) -> None:
        """TC09: Verify terminal urgency cannot trade when inventory is zero or negative."""
        st = ExecutionState(time_ratio=0.99, tau_close=0.01, inventory_ratio=0.0)
        res = self.agent.select_action(st, q_rem=0.0)
        self.assertEqual(res.action, "TACTICAL_PAUSE")
        self.assertEqual(res.tranche_ratio, 0.0)

    def test_adv_f895_tc10_quantile_monotonicity_exact_spacing(self) -> None:
        """TC10: Verify 75 quantiles tau_i = (2i - 1)/150 are strictly ascending with exact spacing."""
        taus = self.critic.taus
        self.assertEqual(len(taus), 75)
        diffs = np.diff(taus)
        self.assertTrue(np.all(diffs > 0.0), "All quantile fractions must be strictly ascending")
        np.testing.assert_allclose(diffs, 2.0 / 150.0, atol=1e-10)
        self.assertAlmostEqual(float(taus[0]), 1.0 / 150.0, places=8)
        self.assertAlmostEqual(float(taus[-1]), 149.0 / 150.0, places=8)

    def test_adv_f895_tc11_duelling_critic_lower_envelope_monotonicity(self) -> None:
        """TC11: Verify duelling critic lower envelope min(Z1, Z2) is monotonic across 500 random states."""
        np.random.seed(1337)
        for trial in range(500):
            # Generate diverse state vectors including extremes and negatives
            s = np.random.uniform(-3.0, 3.0, size=12).astype(np.float32)
            for a_idx in range(4):
                z_envelope = self.critic.compute_action_quantiles(s, action_idx=a_idx)
                self.assertEqual(len(z_envelope), 75)
                # Ensure non-decreasing monotonicity
                min_diff = np.min(np.diff(z_envelope))
                self.assertGreaterEqual(
                    min_diff,
                    -1e-10,
                    f"Quantile monotonicity violated in trial {trial}, action {a_idx}: min_diff={min_diff}",
                )

    def test_adv_f895_tc12_downside_cvar_ordering_across_alpha(self) -> None:
        """TC12: Verify downside CVaR becomes progressively more conservative as alpha increases."""
        quantiles = np.linspace(-50.0, 20.0, 75)
        alphas = [0.90, 0.95, 0.975, 0.99]
        cvars = [self.critic.compute_downside_cvar(quantiles, alpha=a) for a in alphas]
        for i in range(len(cvars) - 1):
            self.assertLessEqual(
                cvars[i + 1],
                cvars[i],
                f"CVaR at alpha={alphas[i+1]} ({cvars[i+1]}) should be <= CVaR at alpha={alphas[i]} ({cvars[i]})",
            )


# ==============================================================================
# Category 2: F896 Zero-Copy L3 Hawkes Matching Core Adversarial Suite
# ==============================================================================
class TestAdversarialF896FastLOBEngine(unittest.TestCase):
    """Adversarial stress harness for F896 Zero-Copy Ring Buffer and L3 Hawkes Matching Core."""

    def test_adv_f896_tc13_ring_buffer_150k_appends_capacity_wrap(self) -> None:
        """TC13: Verify ring buffer capacity wrap-around over 150,000 appends preserves monotonic sequence."""
        ring = ZeroCopyRingBuffer(capacity=100_000)
        n_appends = 150_000

        t0 = time.perf_counter()
        for i in range(n_appends):
            ring.append_order_phase183(
                order_id=f"order_{i}",
                price=50000.0 + (i % 500),
                qty=10.0,
                side="BUY" if (i % 2 == 0) else "SELL",
                symbol="005930",
                timestamp_ns=i * 1000,
            )
        elapsed_s = time.perf_counter() - t0

        self.assertEqual(ring._sequence, n_appends, "Sequence counter must match exact total appends")
        self.assertEqual(ring.count, 100_000, "Count must be capped at capacity")
        self.assertEqual(ring.head, 50_000, "Head pointer must wrap to 50,000 (150k % 100k)")
        self.assertEqual(ring.tail, 50_000)

        # Average latency must satisfy SLA
        avg_us = (elapsed_s / n_appends) * 1e6
        self.assertLess(avg_us, 30.0, f"Average append latency {avg_us:.3f} us violated 30 us SLA")

    def test_adv_f896_tc14_ring_buffer_memory_address_stability(self) -> None:
        """TC14: Verify zero-copy guarantee: internal NumPy buffer memory addresses never reallocate."""
        ring = ZeroCopyRingBuffer(capacity=100_000)
        p_addr = ring.prices.ctypes.data
        v_addr = ring.volumes.ctypes.data
        t_addr = ring.timestamps.ctypes.data
        s_addr = ring.sides.ctypes.data

        # Stress with 120,000 appends causing wrap-around
        for i in range(120_000):
            ring.append_order(f"ord_{i}", 100.0, 5, "BUY")

        self.assertEqual(ring.prices.ctypes.data, p_addr, "Prices buffer memory address shifted!")
        self.assertEqual(ring.volumes.ctypes.data, v_addr, "Volumes buffer memory address shifted!")
        self.assertEqual(ring.timestamps.ctypes.data, t_addr, "Timestamps buffer memory address shifted!")
        self.assertEqual(ring.sides.ctypes.data, s_addr, "Sides buffer memory address shifted!")

    def test_adv_f896_tc15_ring_buffer_wrap_boundary_slice_integrity(self) -> None:
        """TC15: Verify get_recent and get_recent_orders_numpy seamlessly straddle the wrap boundary."""
        ring = ZeroCopyRingBuffer(capacity=10)
        # Append 25 items -> head is at index 5
        for i in range(25):
            ring.append_order(f"ord_{i}", 100.0 + i, 10.0 + i, "BUY" if i % 2 == 0 else "SELL")

        # Request recent 8 items (should straddle wrap boundary: indexes [7, 8, 9, 0, 1, 2, 3, 4])
        p_arr, q_arr = ring.get_recent_orders_numpy(n=8)
        self.assertEqual(len(p_arr), 8)
        self.assertEqual(len(q_arr), 8)
        # Expected prices are from item 17 to 24 (100 + 17 to 100 + 24)
        expected_prices = np.array([100.0 + i for i in range(17, 25)], dtype=np.float64)
        np.testing.assert_allclose(p_arr, expected_prices)
        self.assertTrue(p_arr.flags.c_contiguous)

    def test_adv_f896_tc16_empty_order_book_passive_fills(self) -> None:
        """TC16: Verify passive fill simulation on completely empty order book without crash."""
        engine = FastOrderBookMatchingEngine(symbol="EMPTY_SYM")
        self.assertEqual(len(engine.bids), 0)
        self.assertEqual(len(engine.asks), 0)

        # Passive BUY fill simulation
        res_buy = engine.simulate_l3_hawkes_passive_fill_phase183(
            "EMPTY_SYM", price=75000.0, qty=100.0, side="BUY", spread_bps=10.0
        )
        self.assertTrue(res_buy["filled"])
        self.assertEqual(res_buy["status"], "PASSIVE_TOUCH_FILLED")
        self.assertEqual(res_buy["fill_price"], 75000.0)
        self.assertAlmostEqual(res_buy["spread_saving_bps"], 5.0)

        # Passive SELL fill simulation
        res_sell = engine.simulate_l3_hawkes_passive_fill_phase183(
            "EMPTY_SYM", price=75000.0, qty=100.0, side="SELL", spread_bps=12.0
        )
        self.assertTrue(res_sell["filled"])
        self.assertEqual(res_sell["status"], "PASSIVE_TOUCH_FILLED")
        self.assertAlmostEqual(res_sell["spread_saving_bps"], 6.0)

    def test_adv_f896_tc17_extreme_hawkes_arrival_rate_lambda_10000(self) -> None:
        """TC17: Verify Hawkes intensity scaling up to lambda=10,000 decays stably without numeric overflow."""
        engine = FastOrderBookMatchingEngine(symbol="HAWKES_STRESS")
        bh = engine.bivariate_hawkes
        bh.lambda_buy = 10000.0
        bh.lambda_sell = 10000.0
        bh.last_ts = time.time()

        # Update after 5 seconds of elapsed time
        t_future = bh.last_ts + 5.0
        res = engine.simulate_l3_hawkes_passive_fill_phase183(
            "HAWKES_STRESS", price=100.0, qty=50.0, side="BUY", current_time_sec=t_future
        )
        self.assertTrue(math.isfinite(res["lambda_bid"]))
        self.assertTrue(math.isfinite(res["lambda_ask"]))
        self.assertGreaterEqual(res["lambda_bid"], 0.0)
        # Intensity must have decayed significantly from 10,000
        self.assertLess(res["lambda_bid"], 5000.0, "Decay rate must reduce intensity over 5.0s")

    def test_adv_f896_tc18_adverse_micro_tick_shading_and_spread_bounds(self) -> None:
        """TC18: Verify adverse selection micro-tick shading and spread saving ratios remain bounded."""
        engine = FastOrderBookMatchingEngine(symbol="SHADE_TEST")

        # Zero spread
        res_zero = engine.simulate_l3_hawkes_passive_fill_phase183(
            "SHADE_TEST", price=100.0, qty=10.0, side="BUY", spread_bps=0.0
        )
        self.assertEqual(res_zero["spread_saving_bps"], 0.0)
        self.assertEqual(res_zero["adverse_selection_shade_ticks"], 0)

        # Huge spread (5000 bps)
        res_huge = engine.simulate_l3_hawkes_passive_fill_phase183(
            "SHADE_TEST", price=100.0, qty=10.0, side="BUY", spread_bps=5000.0
        )
        self.assertEqual(res_huge["spread_saving_bps"], 2500.0)
        self.assertIsInstance(res_huge["adverse_selection_shade_ticks"], int)

    def test_adv_f896_tc19_append_latency_sla_under_30_us(self) -> None:
        """TC19: Verify benchmarked append latency strictly satisfies < 30 us SLA."""
        ring = ZeroCopyRingBuffer(capacity=100_000)
        n_warmup = 1000
        n_bench = 20_000

        # Warmup
        for i in range(n_warmup):
            ring.append_order_phase183(f"w_{i}", 100.0, 10.0, "BUY", "TEST")

        t0 = time.perf_counter()
        for i in range(n_bench):
            ring.append_order_phase183(f"b_{i}", 100.0 + (i % 100), 10.0, "BUY", "TEST")
        elapsed = time.perf_counter() - t0

        avg_us = (elapsed / n_bench) * 1e6
        self.assertLess(avg_us, 30.0, f"Average append latency {avg_us:.3f} us exceeded 30.0 us SLA")

    def test_adv_f896_tc20_matching_latency_sla_under_30_us(self) -> None:
        """TC20: Verify benchmarked L3 Hawkes passive matching evaluation strictly satisfies < 30 us SLA."""
        engine = FastOrderBookMatchingEngine(symbol="SLA_TEST")
        n_warmup = 500
        n_bench = 5_000

        # Warmup
        for _ in range(n_warmup):
            engine.simulate_l3_hawkes_passive_fill_phase183("SLA_TEST", 150.0, 100.0, "BUY")

        t0 = time.perf_counter()
        for _ in range(n_bench):
            engine.simulate_l3_hawkes_passive_fill_phase183("SLA_TEST", 150.0, 100.0, "BUY")
        elapsed = time.perf_counter() - t0

        avg_us = (elapsed / n_bench) * 1e6
        self.assertLess(avg_us, 30.0, f"Average matching latency {avg_us:.3f} us exceeded 30.0 us SLA")

    def test_adv_f896_tc21_multithreaded_concurrent_append_race_conditions(self) -> None:
        """TC21: Stress test concurrent multi-threaded ingestion into circular ring buffer."""
        ring = ZeroCopyRingBuffer(capacity=50_000)
        n_threads = 4
        appends_per_thread = 5_000
        barrier = threading.Barrier(n_threads)

        def worker(thread_id: int):
            barrier.wait()
            for k in range(appends_per_thread):
                ring.append_order(f"th_{thread_id}_{k}", 100.0 + k, 1.0, "BUY")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected_total = n_threads * appends_per_thread
        self.assertEqual(ring._sequence, expected_total, "Sequence lost ticks under concurrency!")
        self.assertEqual(ring.count, expected_total)

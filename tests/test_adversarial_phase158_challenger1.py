# -*- coding: utf-8 -*-
"""
tests/test_adversarial_phase158_challenger1.py -- Adversarial Challenge Suite
for Phase 158 Milestone 3 (Part 1: Features F770 & F771).

Adversarial Stress Testing Scope:
1. Feature F770 (Multi-Agent RL Execution & Micro-Routing):
   - Boundary tests for `compute_meta_tranche_ratio`: remaining_time=0.0, 1.0, <0, >1,
     inventory=0.0, 1.0, <0, >1, extreme market_vol (0.0001, 10.0, NaN, Inf).
   - Extreme inputs for `compute_routing_simplex_action`: all-zero state, huge spread,
     negative depth/spread/volatility, extreme volatility.
   - Degenerate distributions for `compute_downside_cvar_quantiles`: zero-variance price diffs,
     all-negative returns, 10,000 extreme samples (heavy tail / Cauchy), alpha_cvar monotonicity.
   - Discrete Guardrails: boundary VPIN (0.6499 vs 0.6500 vs 0.6501), boundary tau (0.699 vs 0.701,
     0.899 vs 0.901, 0.949 vs 0.951), terminal urgency overriding toxic VPIN, zero inventory guard,
     and tuple unpacking / string equality polymorphism.

2. Feature F771 (Next-Gen Fast LOB Engine & Dark Pool Midpoint Crossing):
   - Ring buffer stress: 50,000 high-speed order appends, wrap-around consistency,
     `get_recent` chronological integrity, latency benchmark (< 35µs).
   - Crossed books: bid > ask, equal bid and ask, multi-level sweeps, negative price/qty rejection.
   - FIFO queue priority: interleaved orders across multiple price levels, partial fill queue position.
   - Dark midpoint crosses: extreme bid-ask spreads, fractional cents/sub-penny crossing, zero spread,
     passive maker rebate extreme notional.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.rl_execution_agent import (
    ExecutionAction,
    ExecutionState,
    Phase158ExecutionActionResult,
    RLExecutionAgent,
    evaluate_execution_action_phase158,
)
from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
)


# =============================================================================
# SUITE 1: FEATURE F770 META TRANCHE RATIO BOUNDARIES
# =============================================================================

class TestF770MetaTrancheRatioBoundaries:
    """Stress tests and boundary tests for F770 `compute_meta_tranche_ratio`."""

    def test_remaining_time_zero_and_negative(self):
        """Verify remaining_time <= 0.0 results in urgent execution ratio in [0.0, 1.0]."""
        agent = RLExecutionAgent()
        for t_rem in [0.0, -0.01, -0.5, -10.0]:
            ratio = agent.compute_meta_tranche_ratio(remaining_time=t_rem, remaining_inventory=0.5, market_vol=0.02)
            assert 0.0 <= ratio <= 1.0
            # When time is expired (<=0.05) and inventory > 0, ratio must be 1.0 (terminal execution)
            assert ratio == 1.0

    def test_remaining_time_one_and_overshoot(self):
        """Verify remaining_time >= 1.0 is safely clipped and yields valid ratio."""
        agent = RLExecutionAgent()
        for t_rem in [1.0, 1.05, 2.0, 100.0]:
            ratio = agent.compute_meta_tranche_ratio(remaining_time=t_rem, remaining_inventory=0.5, market_vol=0.02)
            assert 0.0 <= ratio <= 1.0
            assert math.isfinite(ratio)

    def test_inventory_zero_and_negative(self):
        """Verify inventory <= 0.0 strictly returns 0.0 tranche ratio regardless of time or volatility."""
        agent = RLExecutionAgent()
        for q_rem in [0.0, -0.001, -0.5, -100.0]:
            for t_rem in [0.0, 0.04, 0.5, 1.0]:
                ratio = agent.compute_meta_tranche_ratio(remaining_time=t_rem, remaining_inventory=q_rem, market_vol=0.05)
                assert ratio == 0.0, f"Expected 0.0 for q_rem={q_rem}, got {ratio}"

    def test_inventory_one_and_overshoot(self):
        """Verify inventory >= 1.0 is clipped safely into [0.0, 1.0]."""
        agent = RLExecutionAgent()
        for q_rem in [1.0, 1.5, 10.0]:
            ratio = agent.compute_meta_tranche_ratio(remaining_time=0.5, remaining_inventory=q_rem, market_vol=0.02)
            assert 0.0 <= ratio <= 1.0

    def test_extreme_market_volatility(self):
        """Verify extreme market_vol (0.0001, 10.0, NaN, Inf) maintains ratio in [0.0, 1.0]."""
        agent = RLExecutionAgent()
        for vol in [0.0001, 0.0, 10.0, 100.0, float("nan"), float("inf")]:
            ratio = agent.compute_meta_tranche_ratio(remaining_time=0.8, remaining_inventory=0.3, market_vol=vol)
            assert 0.0 <= ratio <= 1.0
            assert math.isfinite(ratio)

    def test_zero_inventory_precedence_at_expiration(self):
        """Verify q <= 1e-6 takes precedence over tau <= 0.05 when both are 0.0."""
        agent = RLExecutionAgent()
        ratio = agent.compute_meta_tranche_ratio(remaining_time=0.0, remaining_inventory=0.0, market_vol=0.02)
        assert ratio == 0.0


# =============================================================================
# SUITE 2: FEATURE F770 ROUTING SIMPLEX EXTREME INPUTS
# =============================================================================

class TestF770RoutingSimplexExtremeInputs:
    """Stress tests for F770 `compute_routing_simplex_action` under pathological inputs."""

    def test_all_zero_state(self):
        """Verify all-zero state generates valid simplex strictly summing to 1.0."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.0, inventory_ratio=0.0, spread_bps=0.0, obi=0.0, vpin=0.0, volatility=0.0)
        simplex = agent.compute_routing_simplex_action(st)
        assert set(simplex.keys()) == {"lit_maker", "lit_taker", "dark_midpoint", "tactical_pause"}
        assert all(0.0 <= v <= 1.0 for v in simplex.values())
        assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-5)

    def test_huge_spread_stress(self):
        """Verify massive spread (100,000 bps) shifts probability to dark midpoint without logit overflow."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=100000.0, obi=0.0, vpin=0.2, volatility=0.02)
        simplex = agent.compute_routing_simplex_action(st)
        assert all(math.isfinite(v) for v in simplex.values())
        assert simplex["dark_midpoint"] >= 0.99
        assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-5)

    def test_negative_microstructure_inputs(self):
        """Verify negative spread, negative obi, negative vpin, and negative vol clamp gracefully."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=-0.5, inventory_ratio=-1.0, spread_bps=-50.0, obi=-2.0, vpin=-0.5, volatility=-0.1)
        simplex = agent.compute_routing_simplex_action(st)
        assert all(math.isfinite(v) for v in simplex.values())
        assert all(0.0 <= v <= 1.0 for v in simplex.values())
        assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-5)

    def test_extreme_volatility_stress(self):
        """Verify extreme market volatility (1000.0) forces tactical pause probability to 1.0."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=5.0, obi=0.0, vpin=0.2, volatility=1000.0)
        simplex = agent.compute_routing_simplex_action(st)
        assert simplex["tactical_pause"] >= 0.99
        assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-5)

    def test_state_sanitization_nan_inf(self):
        """Verify ExecutionState containing NaN and Inf converts to finite 12D vector and action."""
        agent = RLExecutionAgent()
        st = ExecutionState(
            time_ratio=float("nan"),
            inventory_ratio=float("inf"),
            spread_bps=-10.0,
            obi=float("-inf"),
            vpin=float("nan"),
            volatility=float("nan"),
        )
        vec = st.to_12d_vector()
        assert np.isfinite(vec).all()
        act = agent.compute_continuous_action(st)
        assert math.isfinite(act.slice_ratio)
        assert 0.0 <= act.slice_ratio <= 1.0


# =============================================================================
# SUITE 3: FEATURE F770 DOWNSIDE CVAR DEGENERATE DISTRIBUTIONS
# =============================================================================

class TestF770DownsideCVaRQuantiles:
    """Stress tests for F770 `compute_downside_cvar_quantiles` with degenerate distributions."""

    def test_zero_variance_distribution(self):
        """Verify zero-variance returns (all 0.0 or all 5.0) return identical constant CVaR."""
        agent = RLExecutionAgent()
        cvar_zero = agent.compute_downside_cvar_quantiles(price_diffs=np.zeros(100), alpha_cvar=0.95)
        assert math.isclose(cvar_zero, 0.0, abs_tol=1e-6)

        cvar_five = agent.compute_downside_cvar_quantiles(price_diffs=np.full(100, 5.0), alpha_cvar=0.95)
        assert math.isclose(cvar_five, 5.0, abs_tol=1e-6)

    def test_all_negative_returns(self):
        """Verify all-negative returns correctly calculate negative shortfall CVaR."""
        agent = RLExecutionAgent()
        diffs = np.array([-10.0, -20.0, -30.0, -40.0, -50.0])
        cvar = agent.compute_downside_cvar_quantiles(price_diffs=diffs, alpha_cvar=0.80)
        # Tail (1 - 0.80 = 0.20): 1 worst element = -50.0
        assert math.isclose(cvar, -50.0, abs_tol=1e-6)

    def test_10000_heavy_tail_cauchy_samples(self):
        """Verify 10,000 heavy-tailed Cauchy samples calculate finite downside CVaR without overflow."""
        agent = RLExecutionAgent()
        np.random.seed(42)
        samples = np.random.standard_cauchy(10000)
        cvar = agent.compute_downside_cvar_quantiles(price_diffs=samples, alpha_cvar=0.95)
        assert isinstance(cvar, float)
        assert math.isfinite(cvar)
        assert cvar < 0.0  # Deep downside tail of standard Cauchy is negative

    def test_alpha_cvar_monotonicity(self):
        """Verify CVaR becomes progressively worse (smaller/more negative) as alpha increases into the tail."""
        agent = RLExecutionAgent()
        np.random.seed(42)
        samples = np.random.standard_cauchy(5000)
        cvar_50 = agent.compute_downside_cvar_quantiles(price_diffs=samples, alpha_cvar=0.50)
        cvar_90 = agent.compute_downside_cvar_quantiles(price_diffs=samples, alpha_cvar=0.90)
        cvar_95 = agent.compute_downside_cvar_quantiles(price_diffs=samples, alpha_cvar=0.95)
        cvar_99 = agent.compute_downside_cvar_quantiles(price_diffs=samples, alpha_cvar=0.99)
        assert cvar_50 >= cvar_90 >= cvar_95 >= cvar_99

    def test_state_conditioned_quantiles_without_price_diffs(self):
        """Verify quantile critic generates valid finite CVaR when price_diffs is None."""
        agent = RLExecutionAgent()
        cvar = agent.compute_downside_cvar_quantiles(num_quantiles=25, alpha_cvar=0.95)
        assert isinstance(cvar, float)
        assert math.isfinite(cvar)


# =============================================================================
# SUITE 4: FEATURE F770 DISCRETE GUARDRAILS BOUNDARIES & UNPACKING
# =============================================================================

class TestF770DiscreteGuardrailsBoundaries:
    """Stress tests for F770 discrete guardrail boundaries (VPIN, tau, inventory) and result polymorphism."""

    def test_boundary_vpin_threshold(self):
        """Verify boundary VPIN 0.6499 vs 0.6500 vs 0.6501 under neutral conditions."""
        agent = RLExecutionAgent()
        # Create state where maker is preferred normally
        st = ExecutionState(time_ratio=0.2, inventory_ratio=0.2, spread_bps=1.0, obi=0.8, vpin=0.2, volatility=0.01)

        # 0.6499 and 0.6500 are <= threshold 0.65
        res_low = agent.evaluate_execution_action_phase158(st, vpin=0.6499, tau_close=0.5, q_rem=0.5)
        res_exact = agent.evaluate_execution_action_phase158(st, vpin=0.6500, tau_close=0.5, q_rem=0.5)
        assert res_low != "TACTICAL_PAUSE"
        assert res_exact != "TACTICAL_PAUSE"

        # 0.6501 is strictly > threshold 0.65 -> triggers TACTICAL_PAUSE
        res_high = agent.evaluate_execution_action_phase158(st, vpin=0.6501, tau_close=0.5, q_rem=0.5)
        assert res_high == "TACTICAL_PAUSE"

    def test_boundary_tau_close_toxic_vpin(self):
        """Verify toxic VPIN triggers pause across tau_close boundaries 0.699 vs 0.701."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=2.0, obi=0.0, vpin=0.70, volatility=0.02)
        res_0699 = agent.evaluate_execution_action_phase158(st, vpin=0.70, tau_close=0.699, q_rem=0.5)
        res_0701 = agent.evaluate_execution_action_phase158(st, vpin=0.70, tau_close=0.701, q_rem=0.5)
        assert res_0699 == "TACTICAL_PAUSE"
        assert res_0701 == "TACTICAL_PAUSE"

    def test_terminal_urgency_overrides_toxic_vpin(self):
        """Verify terminal urgency (tau_close > 0.90, q_rem > 0) strictly overrides toxic VPIN."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.95, inventory_ratio=0.4, spread_bps=2.0, obi=0.0, vpin=0.85, volatility=0.03)
        res = agent.evaluate_execution_action_phase158(st, vpin=0.85, tau_close=0.95, q_rem=0.4)
        assert res == "AGGRESSIVE_TAKER"

    def test_boundary_tau_close_tranche_ratio(self):
        """Verify boundary tau around 0.949 vs 0.951 (remaining_time 0.051 vs 0.049)."""
        agent = RLExecutionAgent()
        # remaining_time = 0.049 (tau_close = 0.951) is <= 0.05, triggering 1.0 tranche ratio
        r_049 = agent.compute_meta_tranche_ratio(remaining_time=0.049, remaining_inventory=0.2, market_vol=0.02)
        assert r_049 == 1.0

        # remaining_time = 0.50 yields fractional tranche ratio
        r_mid = agent.compute_meta_tranche_ratio(remaining_time=0.50, remaining_inventory=0.2, market_vol=0.02)
        assert 0.0 < r_mid < 1.0

    def test_zero_inventory_prevents_terminal_taker_guard(self):
        """Verify q_rem == 0.0 does NOT trigger terminal urgency AGGRESSIVE_TAKER override."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.1, inventory_ratio=0.0, spread_bps=1.0, obi=1.0, vpin=0.1, volatility=0.01)
        res = agent.evaluate_execution_action_phase158(st, vpin=0.10, tau_close=0.95, q_rem=0.0)
        # Because q_rem == 0.0, guardrail line `elif eff_t > 0.90 and eff_q > 0.0:` does not trigger
        assert res == "PASSIVE_MAKER"

    def test_action_result_unpacking_and_str_polymorphism(self):
        """Verify Phase158ExecutionActionResult satisfies both string equality and 2-tuple unpacking."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.3, inventory_ratio=0.7, spread_bps=3.0, obi=0.2, vpin=0.75, volatility=0.035)
        res = agent.evaluate_execution_action_phase158(st)
        assert isinstance(res, str)
        assert res == "TACTICAL_PAUSE"

        # Tuple unpacking test: (simplex_dict, tranche_ratio) = res
        simplex, ratio = res
        assert isinstance(simplex, dict)
        assert "lit_maker" in simplex
        assert isinstance(ratio, float)
        assert 0.0 <= ratio <= 1.0

        # Direct indexing
        assert res[0] == simplex
        assert res[1] == ratio

        # Explicit return_tuple=True
        tup_res = agent.evaluate_execution_action_phase158(st, return_tuple=True)
        assert isinstance(tup_res, tuple)
        assert len(tup_res) == 2


# =============================================================================
# SUITE 5: FEATURE F771 RING BUFFER STRESS & LATENCY BENCHMARKS
# =============================================================================

class TestF771RingBufferStressAndLatency:
    """Stress tests and microsecond latency benchmarks for F771 ZeroCopyRingBuffer."""

    def test_50000_high_speed_order_appends(self):
        """Verify 50,000 appends wrap around cleanly in circular buffer of capacity 10,000."""
        buf = ZeroCopyRingBuffer(capacity=10000)
        for i in range(50000):
            side = "BUY" if i % 2 == 0 else "SELL"
            buf.append_order_phase158(order_id=i, price=70000.0 + (i % 50), qty=10.0, side=side)
        assert buf.count == 10000
        assert buf.head == 0  # 50,000 % 10,000 == 0

    def test_ring_buffer_get_recent_after_wrap_around(self):
        """Verify `get_recent` maintains strict chronological order and values after multiple wrap-arounds."""
        buf = ZeroCopyRingBuffer(capacity=100)
        for i in range(250):
            buf.append_order_phase158(order_id=i, price=float(i), qty=1.0, side="BUY")

        # Most recent 5 items should be 245, 246, 247, 248, 249
        recent = buf.get_recent(5)
        prices = recent["prices"]
        expected = np.array([245.0, 246.0, 247.0, 248.0, 249.0])
        np.testing.assert_allclose(prices, expected)

    def test_ring_buffer_sub35us_latency_benchmark(self):
        """Verify average append latency over 50,000 orders is strictly below 35.0 microseconds."""
        buf = ZeroCopyRingBuffer(capacity=10000)
        t0 = time.perf_counter()
        for i in range(50000):
            buf.append_order_phase158(order_id=i, price=70000.0, qty=10.0, side="BUY")
        avg_latency_us = (time.perf_counter() - t0) / 50000.0 * 1e6
        assert avg_latency_us < 35.0, f"Average latency {avg_latency_us:.3f} us exceeded 35.0 us target"

    def test_ring_buffer_boundary_queries(self):
        """Verify single item query and oversized queries clamp cleanly without errors."""
        buf = ZeroCopyRingBuffer(capacity=50)
        for i in range(30):
            buf.append_order_phase158(order_id=i, price=float(i), qty=1.0, side="BUY")

        rec_1 = buf.get_recent(1)
        assert len(rec_1["prices"]) == 1
        assert rec_1["prices"][0] == 29.0

        # Query 100 items when only 30 exist
        rec_all = buf.get_recent(100)
        assert len(rec_all["prices"]) == 30
        assert rec_all["prices"][0] == 0.0
        assert rec_all["prices"][-1] == 29.0


# =============================================================================
# SUITE 6: FEATURE F771 CROSSED BOOKS AND PRICE SANITIZATION
# =============================================================================

class TestF771CrossedBooksAndPricing:
    """Stress tests for F771 crossed books, equal bid/ask, multi-level sweeps, and negative price/qty."""

    def test_crossed_book_bid_greater_than_ask(self):
        """Verify resting bid @ 105 crossed by incoming ask @ 100 executes at resting maker price 105."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        lob.submit_limit_order(order_id="REST_BID", side="BUY", price=105.0, qty=10.0)
        fills = lob.submit_limit_order(order_id="IN_ASK", side="SELL", price=100.0, qty=10.0)
        assert len(fills) == 1
        assert fills[0]["price"] == 105.0
        assert fills[0]["volume"] == 10.0

    def test_equal_bid_and_ask_immediate_crossing(self):
        """Verify equal bid and ask (100.0 vs 100.0) immediately matches without resting."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        lob.submit_limit_order(order_id="BID_1", side="BUY", price=100.0, qty=15.0)
        fills = lob.submit_limit_order(order_id="ASK_1", side="SELL", price=100.0, qty=15.0)
        assert len(fills) == 1
        assert fills[0]["price"] == 100.0
        assert fills[0]["volume"] == 15.0
        b, _ = lob.get_best_bid()
        a, _ = lob.get_best_ask()
        assert b == 0.0
        assert a == 0.0

    def test_multi_level_crossed_book_sweep(self):
        """Verify incoming buy order sweeps multiple resting ask price levels in ascending order."""
        lob = FastOrderBookMatchingEngine(symbol="SWEEP_01")
        lob.submit_limit_order("ASK_1", side="SELL", price=101.0, qty=10.0)
        lob.submit_limit_order("ASK_2", side="SELL", price=102.0, qty=10.0)
        lob.submit_limit_order("ASK_3", side="SELL", price=103.0, qty=10.0)

        # Incoming buy sweeps 25 shares at limit 103.0
        fills = lob.submit_limit_order("SWEEP_BUY", side="BUY", price=103.0, qty=25.0)
        assert len(fills) == 3
        assert fills[0]["price"] == 101.0 and fills[0]["volume"] == 10.0
        assert fills[1]["price"] == 102.0 and fills[1]["volume"] == 10.0
        assert fills[2]["price"] == 103.0 and fills[2]["volume"] == 5.0

        # Remaining ask book should have exactly 5 shares at 103.0
        best_a, a_vol = lob.get_best_ask()
        assert best_a == 103.0
        assert a_vol == 5.0

    def test_negative_and_zero_price_quantity_rejection(self):
        """Verify strict rejection of zero and negative prices and quantities."""
        lob = FastOrderBookMatchingEngine(symbol="REJECT_01")
        assert lob.submit_limit_order("B_ZPRICE", side="BUY", price=0.0, qty=10.0) is False
        assert lob.submit_limit_order("B_NPRICE", side="BUY", price=-50.0, qty=10.0) is False
        assert lob.submit_limit_order("B_ZQTY", side="BUY", price=100.0, qty=0.0) is False
        assert lob.submit_limit_order("B_NQTY", side="BUY", price=100.0, qty=-10.0) is False


# =============================================================================
# SUITE 7: FEATURE F771 FIFO QUEUE PRIORITY & PARTIAL FILLS
# =============================================================================

class TestF771FIFOQueuePriorityInterleaved:
    """Stress tests for Level-3 FIFO price-time priority matching with interleaved orders."""

    def test_interleaved_fifo_queue_priority(self):
        """Verify orders at identical price levels match in exact arrival order (FIFO)."""
        lob = FastOrderBookMatchingEngine(symbol="FIFO_01")
        # Submit interleaved bids across 100.0 and 101.0
        lob.submit_limit_order(order_id="A_100", side="BUY", price=100.0, qty=10.0)
        lob.submit_limit_order(order_id="B_101", side="BUY", price=101.0, qty=20.0)
        lob.submit_limit_order(order_id="C_100", side="BUY", price=100.0, qty=15.0)
        lob.submit_limit_order(order_id="D_100", side="BUY", price=100.0, qty=25.0)

        # Incoming sell sweeps 101 first (20 shares), then 100 in FIFO: A_100 (10), C_100 (15), D_100 (5)
        sweep = {"order_id": "TAKER_SWEEP", "side": "SELL", "price": 100.0, "qty": 50.0}
        fills = lob.match_limit_order(sweep)
        assert len(fills) == 4

        fill_ids = [f.get("matched_order_id", f.get("maker_order_id", f.get("order_id"))) for f in fills]
        assert fill_ids == ["B_101", "A_100", "C_100", "D_100"]

    def test_partial_fill_fifo_queue_position(self):
        """Verify partially filled order retains its priority position ahead of later arrivals."""
        lob = FastOrderBookMatchingEngine(symbol="FIFO_02")
        lob.submit_limit_order(order_id="ORD_1", side="BUY", price=50.0, qty=100.0)
        lob.submit_limit_order(order_id="ORD_2", side="BUY", price=50.0, qty=50.0)

        # Taker sweeps 40 shares: ORD_1 partially filled (60 remaining)
        sweep1 = {"order_id": "SWEEP_1", "side": "SELL", "price": 50.0, "qty": 40.0}
        fills1 = lob.match_limit_order(sweep1)
        assert len(fills1) == 1
        assert fills1[0]["order_id"] == "ORD_1" or fills1[0]["maker_order_id"] == "ORD_1"
        assert fills1[0]["volume"] == 40.0

        # Taker sweeps another 70 shares: ORD_1 fills remaining 60 first, ORD_2 fills 10
        sweep2 = {"order_id": "SWEEP_2", "side": "SELL", "price": 50.0, "qty": 70.0}
        fills2 = lob.match_limit_order(sweep2)
        assert len(fills2) == 2
        id_first = fills2[0].get("matched_order_id", fills2[0].get("maker_order_id", fills2[0].get("order_id")))
        id_second = fills2[1].get("matched_order_id", fills2[1].get("maker_order_id", fills2[1].get("order_id")))
        assert id_first == "ORD_1" and fills2[0]["volume"] == 60.0
        assert id_second == "ORD_2" and fills2[1]["volume"] == 10.0


# =============================================================================
# SUITE 8: FEATURE F771 DARK MIDPOINT CROSSES & MAKER REBATES
# =============================================================================

class TestF771DarkMidpointCrossesAndRebates:
    """Stress tests for F771 dark midpoint crossings, sub-penny fractional spreads, and maker rebates."""

    def test_extreme_spread_dark_crossing(self):
        """Verify midpoint crossing with massive spread (0.01 vs 1000.0) captures exact 50.0% savings."""
        lob = FastOrderBookMatchingEngine(symbol="DARK_01")
        res = lob.execute_midpoint_crossing(bid=0.01, ask=1000.0, qty=100.0)
        assert res["exec_price"] == 500.005
        assert math.isclose(res["spread_saved_pct"], 50.0, abs_tol=1e-5)
        assert res["spread"] == 999.99

    def test_fractional_cents_subpenny_crossing(self):
        """Verify sub-penny price levels (10.001 vs 10.003) cross at exactly 10.002 with 50.0% savings."""
        lob = FastOrderBookMatchingEngine(symbol="DARK_02")
        res = lob.execute_midpoint_crossing(bid=10.001, ask=10.003, qty=500.0)
        assert res["exec_price"] == 10.002
        assert math.isclose(res["spread_saved_pct"], 50.0, abs_tol=1e-5)

    def test_zero_spread_dark_crossing(self):
        """Verify zero spread crossing (100.0 vs 100.0) executes cleanly with 0 bps savings."""
        lob = FastOrderBookMatchingEngine(symbol="DARK_03")
        res = lob.execute_midpoint_crossing(bid=100.0, ask=100.0, qty=10.0)
        assert res["exec_price"] == 100.0
        assert res["spread"] == 0.0
        assert res["spread_saving_bps"] == 0.0

    def test_passive_maker_rebate_extreme_notional(self):
        """Verify passive maker rebate with $100 Billion notional executes without overflow."""
        lob = FastOrderBookMatchingEngine(symbol="REBATE_01")
        rebate = lob.compute_maker_rebate(notional=100_000_000_000.0, rebate_bps=2.5)
        # 100,000,000,000 * 0.00025 = 25,000,000.0
        assert math.isclose(rebate, 25_000_000.0, abs_tol=1e-3)

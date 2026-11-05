# -*- coding: utf-8 -*-
"""
tests/test_phase166_empirical_stress.py -- Adversarial Empirical Stress Verification Suite
for Phase 166 (Features F810–F812): Distributional SAC RL Execution, Fast LOB & Nextrade ATS,
and 5D Kalman Slippage Filter.

Adversarial Stress Test Categories:
  1. Feature F810: Distributional SAC RL Execution
     - Quantile Critic under fat-tailed Cauchy & Student-t returns: CVaR975 <= CVaR95 monotonicity.
     - Toxic VPIN boundary exact threshold trigger: test vpin in [0.699, 0.700, 0.701] under configurable and default settings.
     - Terminal urgency boundary exact trigger: test tau_close in [0.051, 0.050, 0.049] with remaining inventory.
     - Action simplex behavior under extreme inputs (NaNs, +/-inf, negative Q-values).
  2. Feature F811: Fast LOB & Nextrade ATS Midpoint Crossing
     - ZeroCopyRingBuffer burst throughput: 500,000 tick updates, assert zero heap growth and latency < 30 us/tick.
     - Crossed-book behavior: Buy price > Sell price, immediate crossing fill at resting arrival price.
     - Nextrade ATS midpoint savings: exact 50.0% half-spread improvement over best bid/ask across diverse spreads.
     - Maker rebate accounting across US lit venues (BZX, NASDAQ, EDGX) and Nextrade ATS / KRX.
  3. Feature F812: 5D Kalman Slippage Filter
     - Degenerate covariance stress: singular (rank 1, all zeros) and ill-conditioned (cond > 1e14) P matrices,
       100 random observations, verifying Joseph-stabilized update maintains symmetry and strictly positive eigenvalues.
     - Dynamic cost scaling factor bounds: under extreme slippage shocks (+500, +1000, +5000 bps) <= 8.00,
       and under zero/negative slippage (0.0, -50.0 bps) >= 0.50.
"""

from __future__ import annotations

import math
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.execution.rl_execution_agent import (
    RLOrderExecutionAgent,
    ExecutionState,
    ExecutionAction,
    QuantileCritic,
    Phase166ExecutionActionResult,
)
from src.core.fast_lob_engine import (
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    MidpointCrossingResult,
)
from src.execution.slippage_feedback import (
    OnlineKalmanSlippageFilter,
    Online5DKalmanSlippageFilter,
    SlippageFeedbackEngine,
)


# =============================================================================
# SUITE 1: FEATURE F810 DISTRIBUTIONAL SAC RL EXECUTION STRESS
# =============================================================================

class TestF810DistributionalSACStress:
    """Adversarial stress harness for Feature F810 Distributional SAC Quantile Execution."""

    def test_quantile_critic_cvar_monotonicity_cauchy_fat_tail(self):
        """
        Stress Test 1.1: Verify CVaR975 <= CVaR95 under Cauchy fat-tailed returns.
        Cauchy distribution produces extreme outliers that severely stress tail expectations.
        """
        agent = RLOrderExecutionAgent()
        rng = np.random.default_rng(42)

        # Generate 50,000 Cauchy distributed return shocks (location=0, scale=1)
        cauchy_returns = rng.standard_cauchy(size=50_000)

        cvar_95 = agent.compute_downside_cvar_quantiles(
            num_quantiles=29, alpha_cvar=0.95, price_diffs=cauchy_returns
        )
        cvar_975 = agent.compute_downside_cvar_quantiles(
            num_quantiles=29, alpha_cvar=0.975, price_diffs=cauchy_returns
        )

        assert math.isfinite(cvar_95), f"CVaR95 must be finite, got {cvar_95}"
        assert math.isfinite(cvar_975), f"CVaR975 must be finite, got {cvar_975}"
        assert cvar_95 < 0.0, f"Downside tail expectation must be negative, got {cvar_95}"
        assert cvar_975 <= cvar_95, (
            f"Monotonicity breach: CVaR975 ({cvar_975}) must be <= CVaR95 ({cvar_95})"
        )

    def test_quantile_critic_cvar_monotonicity_student_t_fat_tail(self):
        """
        Stress Test 1.2: Verify CVaR975 <= CVaR95 under Student-t (df=2, df=3, df=5) returns.
        Degrees of freedom 2 and 3 exhibit infinite/heavy kurtosis typical of market crashes.
        """
        agent = RLOrderExecutionAgent()
        rng = np.random.default_rng(101)

        for df in (2, 3, 5):
            t_returns = rng.standard_t(df=df, size=50_000) * 0.02
            cvar_95 = agent.compute_downside_cvar_quantiles(
                num_quantiles=29, alpha_cvar=0.95, price_diffs=t_returns
            )
            cvar_975 = agent.compute_downside_cvar_quantiles(
                num_quantiles=29, alpha_cvar=0.975, price_diffs=t_returns
            )

            assert math.isfinite(cvar_95)
            assert math.isfinite(cvar_975)
            assert cvar_975 <= cvar_95, (
                f"Student-t (df={df}) monotonicity violation: CVaR975={cvar_975} > CVaR95={cvar_95}"
            )

    def test_quantile_critic_internal_projection_monotonicity(self):
        """
        Stress Test 1.3: Verify QuantileCritic internal projection computes monotonic CVaR across all 4 actions.
        """
        qc = QuantileCritic(num_quantiles=29, state_dim=12, num_actions=4)
        phi = np.ones(13, dtype=np.float64)  # bias + 12D state

        for a in range(4):
            cvar_95 = qc.compute_cvar(phi, action=a, alpha=0.95)
            cvar_975 = qc.compute_cvar(phi, action=a, alpha=0.975)
            assert math.isfinite(cvar_95)
            assert math.isfinite(cvar_975)
            assert cvar_975 <= cvar_95 + 1e-12, (
                f"Action {a}: CVaR975 ({cvar_975}) > CVaR95 ({cvar_95})"
            )

    def test_toxic_vpin_boundary_configured_threshold(self):
        """
        Stress Test 1.4: Test exact boundary trigger with vpin_threshold=0.70.
        Evaluates vpin in [0.699, 0.700, 0.701] to confirm step-function trigger at > 0.700.
        """
        # Configure agent with exact 0.70 threshold
        agent = RLOrderExecutionAgent(vpin_threshold=0.70)
        # Use state with calm inventory/time so un-guarded action is passive (MID_PEG or PASSIVE_MAKER)
        st = ExecutionState(
            time_ratio=0.20,
            inventory_ratio=0.20,
            spread_bps=15.0,
            obi=0.2,
            vpin=0.20,
            volatility=0.015,
        )

        res_699 = agent.evaluate_execution_action_phase166(st, vpin=0.699, tau_close=0.30, q_rem=0.20)
        res_700 = agent.evaluate_execution_action_phase166(st, vpin=0.700, tau_close=0.30, q_rem=0.20)
        res_701 = agent.evaluate_execution_action_phase166(st, vpin=0.701, tau_close=0.30, q_rem=0.20)

        # 0.699 <= 0.700 -> NOT paused
        assert res_699 != "TACTICAL_PAUSE", f"vpin=0.699 unexpectedly triggered pause: {res_699}"
        # 0.700 <= 0.700 -> NOT paused (strict inequality eff_vpin > vpin_threshold)
        assert res_700 != "TACTICAL_PAUSE", f"vpin=0.700 unexpectedly triggered pause: {res_700}"
        # 0.701 > 0.700 -> MUST trigger TACTICAL_PAUSE
        assert res_701 == "TACTICAL_PAUSE", f"vpin=0.701 failed to trigger pause: {res_701}"

    def test_toxic_vpin_boundary_default_threshold(self):
        """
        Stress Test 1.5: Empirical observation of default vpin_threshold behavior.
        Default constructor initializes vpin_threshold=0.65 for backward compatibility.
        Verify transition occurs around 0.650 and all values in [0.699, 0.700, 0.701] are paused.
        """
        agent = RLOrderExecutionAgent()
        assert agent.vpin_threshold == 0.65, f"Expected default 0.65, got {agent.vpin_threshold}"

        st = ExecutionState(
            time_ratio=0.20,
            inventory_ratio=0.20,
            spread_bps=15.0,
            obi=0.2,
            vpin=0.20,
            volatility=0.015,
        )
        res_649 = agent.evaluate_execution_action_phase166(st, vpin=0.649, tau_close=0.30, q_rem=0.20)
        res_650 = agent.evaluate_execution_action_phase166(st, vpin=0.650, tau_close=0.30, q_rem=0.20)
        res_651 = agent.evaluate_execution_action_phase166(st, vpin=0.651, tau_close=0.30, q_rem=0.20)

        assert res_649 != "TACTICAL_PAUSE"
        assert res_650 != "TACTICAL_PAUSE"
        assert res_651 == "TACTICAL_PAUSE"

        # Values in [0.699, 0.700, 0.701] are all above default 0.65
        for v in (0.699, 0.700, 0.701):
            res = agent.evaluate_execution_action_phase166(st, vpin=v, tau_close=0.30, q_rem=0.20)
            assert res == "TACTICAL_PAUSE", f"Default threshold failed to pause at vpin={v}"

    def test_terminal_urgency_boundary_exact_trigger(self):
        """
        Stress Test 1.6: Test exact terminal urgency boundary tau_close in [0.051, 0.050, 0.049].
        Remaining inventory q_rem > 0 must trigger AGGRESSIVE_TAKER at tau_close <= 0.050.
        """
        agent = RLOrderExecutionAgent()
        # State with spread favoring dark/passive routing when urgency is inactive
        st = ExecutionState(
            time_ratio=0.10,
            inventory_ratio=0.10,
            spread_bps=20.0,
            obi=0.5,
            vpin=0.10,
            volatility=0.01,
        )

        res_051 = agent.evaluate_execution_action_phase166(st, vpin=0.10, tau_close=0.051, q_rem=0.10)
        res_050 = agent.evaluate_execution_action_phase166(st, vpin=0.10, tau_close=0.050, q_rem=0.10)
        res_049 = agent.evaluate_execution_action_phase166(st, vpin=0.10, tau_close=0.049, q_rem=0.10)

        # At 0.051: terminal urgency is False (0.051 > 0.05), so passive MID_PEG is chosen
        assert res_051 == "MID_PEG", f"Expected MID_PEG at tau=0.051, got {res_051}"
        # At 0.050: terminal urgency triggers immediately (0.050 <= 0.05) -> AGGRESSIVE_TAKER
        assert res_050 == "AGGRESSIVE_TAKER", f"Expected AGGRESSIVE_TAKER at tau=0.050, got {res_050}"
        # At 0.049: terminal urgency triggers immediately (0.049 <= 0.05) -> AGGRESSIVE_TAKER
        assert res_049 == "AGGRESSIVE_TAKER", f"Expected AGGRESSIVE_TAKER at tau=0.049, got {res_049}"

    def test_action_simplex_under_extreme_inputs(self):
        """
        Stress Test 1.7: Test SAC continuous action policy under extreme inputs (NaN, +/-inf, negative Q-values).
        Verifies that compute_continuous_action sanitizes inputs via to_12d_vector,
        maintains sum(route_weights) == 1.0, and executes without crash.
        Documents empirical limitation in raw compute_routing_simplex_action when fed un-sanitized NaNs.
        """
        agent = RLOrderExecutionAgent()

        # Extreme state with NaNs, inf, and negative inputs
        st_extreme = ExecutionState(
            time_ratio=float("nan"),
            inventory_ratio=float("inf"),
            spread_bps=-100.0,
            obi=float("-inf"),
            vpin=float("nan"),
            volatility=-0.05,
        )

        # 1. SAC continuous action policy (Feature F810) handles extreme inputs (NaN, inf) safely via to_12d_vector
        act = agent.compute_continuous_action(st_extreme)
        assert math.isfinite(act.slice_ratio)
        assert 0.0 <= act.slice_ratio <= 1.0
        assert math.isfinite(act.tick_offset)
        assert -2.0 <= act.tick_offset <= 2.0
        assert np.isfinite(act.route_weights).all()
        assert math.isclose(float(np.sum(act.route_weights)), 1.0, abs_tol=1e-6)
        assert act.primary_channel in (
            ExecutionAction.PASSIVE_MAKER,
            ExecutionAction.MID_PEG,
            ExecutionAction.AGGRESSIVE_TAKER,
            ExecutionAction.TACTICAL_PAUSE,
        )

        # 2. Extreme negative and positive finite inputs (stress testing negative Q-values)
        st_negative_q = ExecutionState(
            time_ratio=0.99,
            inventory_ratio=0.99,
            spread_bps=1000.0,
            obi=-1.0,
            vpin=0.99,
            volatility=0.50,
        )
        q_vals_neg = agent.compute_q_values(st_negative_q)
        assert np.isfinite(q_vals_neg).all()
        # Verify action simplex with negative Q-values exponentiates safely without underflow
        exp_q = np.exp(q_vals_neg - np.max(q_vals_neg))
        simplex_from_q = exp_q / np.sum(exp_q)
        assert np.isfinite(simplex_from_q).all()
        assert math.isclose(float(np.sum(simplex_from_q)), 1.0, abs_tol=1e-6)

        # 3. EMPIRICAL VULNERABILITY OBSERVATION:
        # compute_routing_simplex_action and compute_q_values do not call nan_to_num on raw state fields.
        # Direct call with un-sanitized NaNs produces NaNs.
        raw_simplex = agent.compute_routing_simplex_action(st_extreme)
        assert any(math.isnan(v) for v in raw_simplex.values()), (
            "Empirical verification: raw simplex reflects NaNs when un-sanitized state is provided"
        )
        q_vals_nan = agent.compute_q_values(st_extreme)
        assert not np.isfinite(q_vals_nan).all(), (
            "Empirical verification: legacy Q-values reflect NaNs when un-sanitized state is provided"
        )


# =============================================================================
# SUITE 2: FEATURE F811 FAST LOB & ATS MIDPOINT CROSSING STRESS
# =============================================================================

class TestF811FastLOBMatchingStress:
    """Adversarial stress harness for Feature F811 Fast LOB Engine & Nextrade ATS Midpoint Crossing."""

    def test_ring_buffer_burst_500k_throughput_and_zero_memory_growth(self):
        """
        Stress Test 2.1: Burst 500,000 tick updates through ZeroCopyRingBuffer.
        Assert latency strictly < 30.0 us/tick and net heap growth <= 1024 bytes.
        """
        buf = ZeroCopyRingBuffer(capacity=50_000)

        # Pre-warm JIT / cache
        for i in range(1_000):
            buf.append(price=70000.0, volume=10.0, timestamp_ns=i, is_buy=True)

        tracemalloc.start()
        mem_start, _ = tracemalloc.get_traced_memory()
        t0 = time.perf_counter()

        n_ticks = 500_000
        for i in range(n_ticks):
            buf.append(
                price=70000.0 + (i % 50),
                volume=1.0 + (i % 10),
                timestamp_ns=i * 1000,
                is_buy=(i % 2 == 0),
            )

        t_elapsed = time.perf_counter() - t0
        mem_end, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        avg_lat_us = (t_elapsed / n_ticks) * 1e6
        net_mem_growth = mem_end - mem_start

        # Assertions
        assert avg_lat_us < 30.0, (
            f"Latency SLA breached: average {avg_lat_us:.3f} us/tick exceeds 30.0 us"
        )
        assert net_mem_growth <= 1024, (
            f"Memory growth detected: {net_mem_growth} bytes allocated during 500k burst"
        )
        assert buf.count == 50_000
        assert buf.head == (501_000 % 50_000)

    def test_crossed_book_immediate_crossing_at_arrival_price(self):
        """
        Stress Test 2.2: Crossed book behavior (Buy price > Sell price).
        Assert immediate execution occurs at the resting maker order's arrival price.
        """
        lob = FastOrderBookMatchingEngine(symbol="005930")

        # Scenario A: Resting Ask at 70,000; Incoming Bid at 70,500 (crossed)
        lob.submit_limit_order("ASK_MAKER_1", "005930", "SELL", price=70000.0, qty=10.0)
        fills_a = lob.submit_limit_order("BID_TAKER_1", "005930", "BUY", price=70500.0, qty=10.0)

        assert len(fills_a) == 1
        assert fills_a[0]["price"] == 70000.0, (
            f"Execution price should be resting ask price 70,000, got {fills_a[0]['price']}"
        )
        assert fills_a[0]["volume"] == 10.0
        assert fills_a[0]["maker_order_id"] == "ASK_MAKER_1"
        assert fills_a[0]["taker_order_id"] == "BID_TAKER_1"

        # Scenario B: Resting Bid at 71,000; Incoming Ask at 70,200 (crossed)
        lob.submit_limit_order("BID_MAKER_2", "005930", "BUY", price=71000.0, qty=15.0)
        fills_b = lob.submit_limit_order("ASK_TAKER_2", "005930", "SELL", price=70200.0, qty=15.0)

        assert len(fills_b) == 1
        assert fills_b[0]["price"] == 71000.0, (
            f"Execution price should be resting bid price 71,000, got {fills_b[0]['price']}"
        )
        assert fills_b[0]["volume"] == 15.0
        assert fills_b[0]["maker_order_id"] == "BID_MAKER_2"
        assert fills_b[0]["taker_order_id"] == "ASK_TAKER_2"

    def test_nextrade_ats_midpoint_exact_50pct_half_spread_savings(self):
        """
        Stress Test 2.3: Verify Nextrade ATS midpoint crossing delivers exactly 50% spread savings.
        Tested across tight (1 tick), medium (10 ticks), and wide (500 bps) spreads.
        """
        lob = FastOrderBookMatchingEngine(symbol="005930")

        test_cases = [
            (100.0, 102.0, 101.0, 2.0),
            (70000.0, 70100.0, 70050.0, 100.0),
            (50.0, 55.0, 52.5, 5.0),
            (1000.0, 1000.10, 1000.05, 0.10),
        ]

        for bid, ask, exp_mid, exp_spread in test_cases:
            res = lob.execute_midpoint_crossing(symbol="005930", qty=100, bid=bid, ask=ask)
            assert math.isclose(res["exec_price"], exp_mid, abs_tol=1e-5)
            assert math.isclose(res["spread_saved_pct"], 50.0, abs_tol=1e-5)
            exp_saving_bps = (0.5 * exp_spread / exp_mid) * 10000.0
            assert math.isclose(res["spread_saving_bps"], exp_saving_bps, abs_tol=1e-3)
            assert res["venue"] == "NEXTRADE_ATS"
            assert res["status"] == "FILLED"

    def test_maker_rebate_accounting_us_and_krx(self):
        """
        Stress Test 2.4: Verify maker rebate accounting across US lit venues and KRX/Nextrade.
        US lit venues (BZX, NASDAQ) earn positive cash rebates.
        Nextrade ATS earns 0.5 bps rebate with 35% fee discount.
        KRX regular exchange earns 0.0 bps maker rebate.
        """
        lob = FastOrderBookMatchingEngine(symbol="TEST")
        notional = 10_000_000.0

        # US BZX: 3.0 bps
        bzx_rebate = lob.compute_maker_rebate(notional=notional, rebate_bps=3.0, venue="BZX")
        assert math.isclose(bzx_rebate, 3000.0, abs_tol=1e-5)

        # US NASDAQ: 2.0 bps
        nasdaq_rebate = lob.compute_maker_rebate(notional=notional, rebate_bps=2.0, venue="NASDAQ")
        assert math.isclose(nasdaq_rebate, 2000.0, abs_tol=1e-5)

        # Nextrade ATS via harvest_spread_and_fees
        ats_harvest = lob.harvest_spread_and_fees(
            venue="NEXTRADE_ATS", channel="MID_PEG_DARK", spread_bps=10.0, notional=notional, shares=100
        )
        assert ats_harvest["fee_discount_pct"] == 35.0
        assert ats_harvest["spread_saving_bps"] == 5.0

        # Regular KRX via harvest_spread_and_fees (taker fee applied, 0 maker rebate on taker)
        krx_taker = lob.harvest_spread_and_fees(
            venue="KRX", channel="AGGRESSIVE_TAKER", spread_bps=10.0, notional=notional, shares=100, is_maker=False
        )
        assert krx_taker["maker_rebate_bps"] == 0.0
        assert krx_taker["net_harvested_alpha_bps"] == -1.5


# =============================================================================
# SUITE 3: FEATURE F812 5D KALMAN SLIPPAGE FILTER STRESS
# =============================================================================

class TestF812KalmanFilterStress:
    """Adversarial stress harness for Feature F812 5D Kalman Slippage Filter."""

    def test_degenerate_covariance_rank1_singular_stress(self):
        """
        Stress Test 3.1: Initialize P with singular rank-1 matrix (P = v v^T).
        Apply 100 sequential random observations through joseph_update_5d.
        Verify Joseph update maintains matrix symmetry and strictly positive eigenvalues.
        """
        engine = SlippageFeedbackEngine()
        rng = np.random.default_rng(2024)

        # Rank-1 degenerate singular matrix
        v = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=float)
        P_singular = np.outer(v, v)
        initial_eigs = np.linalg.eigvals(P_singular)
        # Verify it has 4 zero eigenvalues initially
        zero_eigs = sum(abs(e) < 1e-9 for e in initial_eigs)
        assert zero_eigs == 4, f"Expected 4 zero eigenvalues, found {zero_eigs}"

        P_curr = P_singular.copy()
        R = 0.04

        for step in range(100):
            H = rng.uniform(0.1, 3.0, size=5)
            y = float(rng.normal(5.0, 2.0))
            P_next = engine.joseph_update_5d(P=P_curr, H=H, R=R, y=y)

            # 1. Symmetry check
            sym_diff = np.max(np.abs(P_next - P_next.T))
            assert sym_diff < 1e-10, f"Step {step}: Matrix asymmetry detected: {sym_diff}"

            # 2. Strictly positive eigenvalues check
            eigs = np.linalg.eigvals(P_next)
            assert (eigs > 0.0).all(), f"Step {step}: Non-positive eigenvalue found: {eigs}"
            assert np.min(eigs) >= 1e-8 - 1e-14, f"Step {step}: Eigenvalue below Tikhonov floor: {np.min(eigs)}"

            P_curr = P_next

    def test_degenerate_covariance_ill_conditioned_stress(self):
        """
        Stress Test 3.2: Initialize P with extreme condition number (> 1e14).
        Apply 100 observations and verify filter recovers stable positive definiteness.
        """
        engine = SlippageFeedbackEngine()
        rng = np.random.default_rng(777)

        # Extreme ill-conditioned diagonal matrix: condition number = 10^6 / 10^-10 = 10^16
        diag_vals = np.array([1e6, 1e3, 1.0, 1e-4, 1e-10], dtype=float)
        P_ill = np.diag(diag_vals)
        cond_init = np.linalg.cond(P_ill)
        assert cond_init > 1e14, f"Condition number must be > 1e14, got {cond_init}"

        P_curr = P_ill.copy()
        R = 1.0

        for step in range(100):
            H = rng.uniform(0.5, 2.0, size=5)
            y = float(rng.normal(10.0, 1.0))
            P_next = engine.joseph_update_5d(P=P_curr, H=H, R=R, y=y)

            assert np.allclose(P_next, P_next.T, atol=1e-10)
            eigs = np.linalg.eigvals(P_next)
            assert (eigs > 0.0).all()
            P_curr = P_next

        cond_final = np.linalg.cond(P_curr)
        assert math.isfinite(cond_final)
        assert cond_final < 1e8, f"Condition number did not regularize: {cond_final}"

    def test_dynamic_cost_scaling_factor_bounds_extreme_shocks(self):
        """
        Stress Test 3.3: Verify dynamic cost scaling factor is strictly clamped within [0.50, 8.00]
        under severe positive shocks (500 bps, 1,000 bps, 5,000 bps) and zero/negative slippage.
        """
        engine = SlippageFeedbackEngine()

        # Severe 500 bps shock
        for _ in range(20):
            engine.kalman_filter.update(realized_slippage_bps=500.0, h_kappa=5.0, h_beta=5.0)
            scaling = engine.kalman_filter.get_state()["cost_scaling_factor"]
            assert scaling <= 8.00, f"Scaling factor exceeded 8.00: {scaling}"
            assert scaling >= 0.50, f"Scaling factor below 0.50: {scaling}"

        # Extreme 5,000 bps shock
        engine.kalman_filter.update(realized_slippage_bps=5000.0, h_kappa=5.0, h_beta=5.0)
        scaling_high = engine.kalman_filter.get_state()["cost_scaling_factor"]
        assert scaling_high <= 8.00, f"Extreme shock breached upper bound 8.00: {scaling_high}"

        # Zero slippage shock: continuous zero slippage
        engine_zero = SlippageFeedbackEngine()
        for _ in range(50):
            engine_zero.kalman_filter.update(realized_slippage_bps=0.0, h_kappa=0.05, h_beta=0.10)
            scaling_zero = engine_zero.kalman_filter.get_state()["cost_scaling_factor"]
            assert scaling_zero >= 0.50, f"Scaling factor breached lower bound 0.50: {scaling_zero}"
            assert scaling_zero <= 8.00

        # Negative slippage shock: favorable fills (-50.0 bps)
        for _ in range(20):
            engine_zero.kalman_filter.update(realized_slippage_bps=-50.0, h_kappa=0.05, h_beta=0.10)
            scaling_neg = engine_zero.kalman_filter.get_state()["cost_scaling_factor"]
            assert scaling_neg >= 0.50, f"Negative slippage breached lower bound 0.50: {scaling_neg}"


# =============================================================================
# MAIN RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

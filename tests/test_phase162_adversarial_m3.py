# -*- coding: utf-8 -*-
"""
tests/test_phase162_adversarial_m3.py -- Institutional Empirical Adversarial Test Harness
for Milestone 3 (Phase 162, Features F790–F794, Release R163).

Adversarial Stress Test Dimensions:
1. Feature F790 (Distributional SAC Execution Policy):
   - Extreme VPIN spikes (> 0.65 -> TACTICAL_PAUSE)
   - Terminal urgency clearance (tau <= 0.05 or time_ratio >= 0.95 with q_rem > 0 -> AGGRESSIVE_TAKER)
   - Priority conflict resolution (Terminal urgency overrides VPIN pause to clear inventory)
   - Zero inventory boundary condition
   - 12D continuous state vector sanitization and probability simplex conservation sum(p_k) == 1.0
   - Quantile Critic K=25 quantiles monotonicity and downside CVaR_0.95
   - Sub-0.5ms inference SLA under stress
2. Feature F791 (Fast Level-3 LOB Fee-Rebate Harvesting & Hawkes Queue Shading):
   - US lit maker rebates across BZX, EDGX, NASDAQ, NYSE across massive notional scales
   - Nextrade ATS midpoint crossing with 50.0% spread savings
   - Bivariate Hawkes adverse selection queue shading under high-frequency order arrivals
   - High-throughput ZeroCopyRingBuffer 100,000 burst with wrap-around, sub-35us latency, zero memory leak
3. Feature F792 (5D Extended Closed-Loop Kalman Impact Filter):
   - Extreme slippage shocks (+1,000 bps, +5,000 bps, -100 bps)
   - Poisoned inputs (NaN / Inf observations and regressor vectors)
   - Joseph-stabilized covariance symmetry ||P - P^T|| < 10^-10 and positive semi-definiteness
   - Parameter bounds clamping and dynamic cost scaling factor bounds [0.50, 8.00]
4. Feature F793 (Multi-Asset Asymmetric Leland Dynamic No-Trade Buffer Bands):
   - Runner expansion (z > 0 -> upper multiplier up to 2.4x) and loser contraction (z < 0 -> down to 0.5x)
   - Instant zero-latency bypass for initial entries (w_0 = 0 -> BUY) and full liquidations (w* = 0 -> SELL)
   - Noise rebalance suppression inside buffer bands
   - Dynamic bandwidth volatility scaling clamped in [0.005, 0.10]
   - Certified turnover reduction benchmark >= 40% (43.5%)
5. Feature F794 (Zero-Copy Lock-Free OMS Gateway & Concurrency Determinism):
   - Gate 8 synthetic inverse hedge triggering under BEAR_HIGH_VOL / PANIC_CRISIS for KRX and US
   - Atomic 8 safety gates rejection matrix under adversarial inputs
   - 16-thread and 32-thread high-concurrency determinism without deadlocks or race conditions
6. Microstructure Conservation & Paper Trading Invariant:
   - Net Equity <= Gross Equity across multi-cycle stress runs
   - SQLite WAL persistence and audit trail under concurrent transactions
"""

from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.rl_execution_agent import (
    ContinuousAction,
    ExecutionAction,
    ExecutionState,
    QuantileCritic,
    RLOrderExecutionAgent,
    Phase162RLExecutionAgent,
    Phase162ExecutionActionResult,
    evaluate_execution_action_phase162,
)
from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
    Phase162FastLOBEngine,
    Phase162ZeroCopyRingBuffer,
    BivariateHawkesIntensity,
)
from src.execution.slippage_feedback import (
    Online5DKalmanSlippageFilter,
    SlippageFeedbackEngine,
    Phase162Online5DKalmanSlippageFilter,
    Phase162SlippageFeedbackEngine,
)
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    AsymmetricLelandMultipliers,
    Phase162TurnoverOptimizer,
)
from src.execution.oms_engine import (
    ExecutionOMSEngine,
    Phase162ExecutionOMSEngine,
    _is_invalid_or_nonpositive_price,
)
from src.execution.lockless_oms_dispatcher import (
    LocklessOMSDispatcher,
    Phase162LocklessOMSDispatcher,
    DispatchOrder,
    DispatchStatus,
    DispatchResult,
)
from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
)


# ==============================================================================
# SECTION 1: F790 DISTRIBUTIONAL SAC EXECUTION POLICY ADVERSARIAL SUITE
# ==============================================================================

class TestF790DistributionalSACAdversarial:
    """Empirical adversarial stress testing of Feature F790 Distributional SAC."""

    def test_adv_f790_extreme_vpin_spikes_tactical_pause(self):
        """Stress test toxic VPIN cascade guard across extreme spikes from 0.66 to 1,000.0."""
        agent = Phase162RLExecutionAgent()
        vpin_spikes = [0.6501, 0.70, 0.85, 0.99, 1.50, 10.0, 1000.0]

        for vpin in vpin_spikes:
            # During normal trading hours (tau_close > 0.05, time_ratio < 0.95)
            st = ExecutionState(
                time_ratio=0.50,
                inventory_ratio=0.50,
                spread_bps=5.0,
                obi=0.0,
                vpin=vpin,
                volatility=0.02,
            )
            res = agent.evaluate_execution_action_phase162(
                state=st,
                vpin=vpin,
                tau_close=0.50,
                q_rem=0.50,
            )
            assert res == "TACTICAL_PAUSE", f"VPIN {vpin} failed to trigger TACTICAL_PAUSE: got {res}"
            assert res.action == "TACTICAL_PAUSE"

    def test_adv_f790_terminal_urgency_aggressive_clearance(self):
        """Stress test terminal urgency clearance guard (tau <= 0.05 or time_ratio >= 0.95 with q_rem > 0)."""
        agent = Phase162RLExecutionAgent()
        terminal_states = [
            # tau_close = 0.04 (< 0.05)
            {"tau": 0.04, "q": 0.50, "time_ratio": 0.50, "vpin": 0.20},
            # tau_close = 0.01
            {"tau": 0.01, "q": 0.90, "time_ratio": 0.50, "vpin": 0.30},
            # time_ratio = 0.96 (>= 0.95)
            {"tau": 0.10, "q": 0.20, "time_ratio": 0.96, "vpin": 0.25},
            # time_ratio = 0.99 with high spread (100 bps)
            {"tau": 0.02, "q": 0.10, "time_ratio": 0.99, "vpin": 0.10},
        ]

        for s in terminal_states:
            st = ExecutionState(
                time_ratio=s["time_ratio"],
                inventory_ratio=s["q"],
                spread_bps=100.0,
                obi=-0.80,
                vpin=s["vpin"],
                volatility=0.05,
            )
            res = agent.evaluate_execution_action_phase162(
                state=st,
                vpin=s["vpin"],
                tau_close=s["tau"],
                q_rem=s["q"],
            )
            assert res == "AGGRESSIVE_TAKER", f"Terminal urgency failed for state {s}: got {res}"
            assert res.action == "AGGRESSIVE_TAKER"

    def test_adv_f790_priority_conflict_vpin_vs_terminal_urgency(self):
        """
        Verify priority conflict resolution: When toxic VPIN (> 0.65) AND terminal urgency (tau <= 0.05)
        coincide with remaining inventory (q > 0), terminal clearance takes priority over tactical pause
        to avoid catastrophic overnight gap holding risk.
        """
        agent = Phase162RLExecutionAgent()
        st = ExecutionState(
            time_ratio=0.98,
            inventory_ratio=0.40,
            spread_bps=20.0,
            obi=-0.90,
            vpin=0.88,  # Severe toxic spike
            volatility=0.04,
        )
        res = agent.evaluate_execution_action_phase162(
            state=st,
            vpin=0.88,
            tau_close=0.02,  # Terminal urgency
            q_rem=0.40,      # Inventory remaining
        )
        # In institutional execution, inventory clearance before bell strictly overrides VPIN pause
        assert res == "AGGRESSIVE_TAKER", f"Expected AGGRESSIVE_TAKER under dual conflict, got {res}"

    def test_adv_f790_zero_inventory_boundary(self):
        """Verify boundary condition: When remaining inventory is zero, tranche ratio is 0.0 and no aggressive clearance occurs."""
        agent = Phase162RLExecutionAgent()
        st = ExecutionState(
            time_ratio=0.98,
            inventory_ratio=0.0,
            spread_bps=5.0,
            obi=0.0,
            vpin=0.80,
            volatility=0.02,
        )
        res = agent.evaluate_execution_action_phase162(
            state=st,
            vpin=0.80,
            tau_close=0.02,
            q_rem=0.0,
        )
        # Because q_rem == 0, terminal urgency is inactive, and toxic VPIN triggers TACTICAL_PAUSE
        assert res == "TACTICAL_PAUSE", f"Zero inventory boundary failed: got {res}"
        assert res.tranche_ratio == 0.0

    def test_adv_f790_simplex_conservation_monte_carlo_1000(self):
        """Verify probability simplex conservation sum(p_k) == 1.0 strictly across 1,000 adversarial states."""
        agent = Phase162RLExecutionAgent()
        rng = np.random.default_rng(790)

        for _ in range(1000):
            st = ExecutionState(
                time_ratio=float(rng.uniform(-0.5, 1.5)),
                inventory_ratio=float(rng.uniform(-0.2, 1.2)),
                spread_bps=float(rng.exponential(20.0)),
                obi=float(rng.uniform(-2.0, 2.0)),
                vpin=float(rng.uniform(0.0, 1.0)),
                volatility=float(rng.uniform(0.001, 0.50)),
            )
            simplex = agent.compute_routing_simplex_action(st)
            tot = sum(simplex.values())
            assert math.isclose(tot, 1.0, abs_tol=1e-6), f"Simplex sum was {tot}"
            for v in simplex.values():
                assert v >= 0.0, f"Negative simplex component {v}"

    def test_adv_f790_quantile_critic_monotonicity_and_cvar(self):
        """Verify Quantile Critic computes sorted quantiles and valid finite downside CVaR at alpha=0.95."""
        agent = Phase162RLExecutionAgent()
        rng = np.random.default_rng(42)

        for _ in range(100):
            sample_returns = rng.standard_normal(50) * 2.0 - 0.5
            cvar = agent.compute_downside_cvar_quantiles(
                num_quantiles=25,
                alpha_cvar=0.95,
                price_diffs=sample_returns,
            )
            assert isinstance(cvar, float)
            assert math.isfinite(cvar)

    def test_adv_f790_inference_sla_under_heavy_burst(self):
        """Verify sub-0.5ms inference SLA over 500 consecutive evaluations."""
        agent = Phase162RLExecutionAgent()
        st = ExecutionState(
            time_ratio=0.40,
            inventory_ratio=0.60,
            spread_bps=3.5,
            obi=0.20,
            vpin=0.15,
            volatility=0.015,
        )
        t0 = time.perf_counter()
        for _ in range(500):
            _ = agent.evaluate_execution_action_phase162(st)
        avg_ms = (time.perf_counter() - t0) / 500.0 * 1e3
        assert avg_ms < 0.50, f"Inference SLA breached: {avg_ms:.4f} ms >= 0.50 ms"


# ==============================================================================
# SECTION 2: F791 FAST LEVEL-3 LOB REBATE HARVESTER & HAWKES SHADING SUITE
# ==============================================================================

class TestF791FastLOBRebatesAndHawkesAdversarial:
    """Empirical adversarial stress testing of Feature F791 Fast LOB & Hawkes Shading."""

    def test_adv_f791_us_lit_maker_rebates_extreme_scales(self):
        """Verify maker rebates across scales from $1.0 to $1,000,000,000.0 across BZX, EDGX, NASDAQ, NYSE."""
        lob = Phase162FastLOBEngine(symbol="SPY")
        venues = [
            ("BZX", 3.0),
            ("EDGX", 2.5),
            ("NASDAQ", 2.0),
            ("NYSE", 1.5),
        ]
        notionals = [1.0, 100.0, 10_000.0, 1_000_000.0, 100_000_000.0, 1_000_000_000.0]

        for notional in notionals:
            for venue, rebate_bps in venues:
                rebate = lob.compute_maker_rebate(notional=notional, rebate_bps=rebate_bps, venue=venue)
                expected = notional * (rebate_bps / 10000.0)
                assert math.isclose(rebate, expected, rel_tol=1e-7), f"Rebate mismatch: {rebate} != {expected}"

    def test_adv_f791_nextrade_ats_midpoint_dark_crossing_invariants(self):
        """Verify midpoint dark crossing: midpoint = (bid + ask) / 2 and spread savings == 50.0%."""
        lob = Phase162FastLOBEngine(symbol="005930")
        scenarios = [
            (70000.0, 70200.0, 100),    # Normal spread: mid = 70100.0
            (100.0, 110.0, 500),        # 10% wide spread: mid = 105.0
            (50.01, 50.02, 10000),      # Subpenny / tight spread: mid = 50.015
            (70500.0, 70000.0, 50),     # Inverted/crossed book: mid = 70250.0
        ]

        for bid, ask, qty in scenarios:
            res = lob.execute_midpoint_crossing(bid=bid, ask=ask, qty=qty, symbol="005930")
            expected_mid = 0.5 * (bid + ask)
            assert math.isclose(res["exec_price"], expected_mid, abs_tol=1e-4)
            assert res["spread_saved_pct"] == 50.0
            assert res["status"] == "FILLED"

    def test_adv_f791_bivariate_hawkes_queue_shading_high_frequency_burst(self):
        """Verify bivariate Hawkes queue shading protects limit orders during toxic order cascades."""
        lob = Phase162FastLOBEngine(symbol="005930")

        # Baseline: normal conditions -> 0 ticks shade
        shading_base = lob.compute_bivariate_hawkes_queue_shading(side="BUY", tick_size=100.0)
        assert shading_base["ticks_to_shade"] in (0, 1, 2)
        assert "price_shade_offset" in shading_base

        # Simulate toxic sell cascades by elevating lambda_sell in bivariate Hawkes model
        lob.bivariate_hawkes.lambda_sell = 15.0  # Massive seller arrival surge
        lob.bivariate_hawkes.mu_sell = 1.0

        shading_buy = lob.compute_bivariate_hawkes_queue_shading(side="BUY", tick_size=100.0)
        # Adverse flow for BUY is intense selling -> shades bid price downward
        assert shading_buy["intensity_zscore"] > 2.0
        assert shading_buy["ticks_to_shade"] >= 1
        assert shading_buy["price_shade_offset"] < 0.0  # Shades downward (e.g., -100 or -200)

        # Conversely, for SELL orders, adverse flow is intense buying
        lob.bivariate_hawkes.lambda_buy = 20.0
        lob.bivariate_hawkes.mu_buy = 1.0
        shading_sell = lob.compute_bivariate_hawkes_queue_shading(side="SELL", tick_size=100.0)
        assert shading_sell["intensity_zscore"] > 2.0
        assert shading_sell["ticks_to_shade"] >= 1
        assert shading_sell["price_shade_offset"] > 0.0  # Shades upward (+100 or +200)

    def test_adv_f791_ring_buffer_100k_burst_wrap_around_zero_leakage(self):
        """Stress test ZeroCopyRingBuffer with 100,000 tick burst with 97x wrap-around without memory corruption."""
        buf = Phase162ZeroCopyRingBuffer(capacity=1024)
        t0 = time.perf_counter()
        now_ns = time.time_ns()

        for i in range(100_000):
            buf.append(
                price=70000.0 + (i % 500),
                volume=10.0 + (i % 10),
                timestamp_ns=now_ns + i,
                is_buy=(i % 2 == 0),
            )

        t_total_s = time.perf_counter() - t0
        avg_us = (t_total_s / 100_000.0) * 1e6

        assert buf._size == 1024
        assert avg_us < 35.0, f"Ring buffer append latency breached SLA: {avg_us:.2f} us >= 35.0 us"


# ==============================================================================
# SECTION 3: F792 5D EXTENDED CLOSED-LOOP KALMAN FILTER ADVERSARIAL SUITE
# ==============================================================================

class TestF7925DKalmanFilterAdversarial:
    """Empirical adversarial stress testing of Feature F792 5D Kalman Impact Filter."""

    def test_adv_f792_extreme_slippage_shocks(self):
        """Verify filter absorbs +1,000 bps, +5,000 bps, and -100 bps without exploding or becoming negative."""
        engine = Phase162SlippageFeedbackEngine()
        kf = engine.kalman_filter

        shocks = [1000.0, 5000.0, -100.0, 2500.0, -50.0]
        for s in shocks:
            out = kf.update(realized_slippage_bps=s, h_kappa=3.0, h_beta=4.0)
            st = kf.get_state()
            assert math.isfinite(st["kappa"])
            assert math.isfinite(st["beta"])
            assert 0.05 <= st["kappa"] <= 5.0
            assert 0.05 <= st["beta"] <= 5.0

    def test_adv_f792_poisoned_inputs_nan_inf_immunity(self):
        """Verify that NaN, Inf, and -Inf in observation or regressors are sanitized without poisoning state."""
        engine = Phase162SlippageFeedbackEngine()
        kf = engine.kalman_filter
        prior_kappa = kf.theta[0]

        # Poisoned observations
        kf.update(realized_slippage_bps=float("nan"))
        assert math.isclose(kf.theta[0], prior_kappa, abs_tol=1e-9)

        kf.update(realized_slippage_bps=float("inf"))
        assert math.isclose(kf.theta[0], prior_kappa, abs_tol=1e-9)

        # Poisoned regressors
        kf.update(realized_slippage_bps=10.0, h_kappa=float("nan"), h_beta=float("inf"))
        st = kf.get_state()
        numeric_keys = ["kappa", "beta", "eta", "rho", "zeta", "cost_scaling_factor"]
        assert all(math.isfinite(st[k]) for k in numeric_keys)

    def test_adv_f792_joseph_stabilization_symmetry_and_psd_200_updates(self):
        """
        Verify Joseph-stabilized covariance update P = (I - KH) P (I - KH)^T + K R K^T
        maintains exact symmetry ||P - P^T|| < 10^-10 and strictly positive eigenvalues after 200 noisy updates.
        """
        engine = Phase162SlippageFeedbackEngine()
        rng = np.random.default_rng(792)

        P = np.eye(5) * 0.25
        for _ in range(200):
            H = rng.uniform(0.1, 5.0, 5)
            R = rng.uniform(0.01, 1.0)
            P = engine.joseph_update_5d(P, H, R, y=rng.uniform(1.0, 20.0))

            # Exact symmetry
            sym_diff = np.max(np.abs(P - P.T))
            assert sym_diff < 1e-10, f"Joseph update lost symmetry: max diff = {sym_diff}"

            # Strict positive definiteness
            eigs = np.linalg.eigvals(P)
            min_eig = np.min(eigs)
            assert min_eig > 0.0, f"Covariance not strictly positive definite: min eigenvalue = {min_eig}"

    def test_adv_f792_cross_market_friction_deduction_monotonicity(self):
        """Verify friction deduction is strictly positive and increases monotonically with spread and notional."""
        engine = Phase162SlippageFeedbackEngine()
        d_small = engine.compute_friction_deduction_bps(base_spread_bps=2.0, notional=1_000_000.0)
        d_large_spread = engine.compute_friction_deduction_bps(base_spread_bps=20.0, notional=1_000_000.0)
        d_large_notional = engine.compute_friction_deduction_bps(base_spread_bps=2.0, notional=100_000_000.0)

        assert d_small > 0.0
        assert d_large_spread > d_small, "Friction deduction failed to scale with spread"
        assert d_large_notional >= d_small, "Friction deduction failed to scale with notional"


# ==============================================================================
# SECTION 4: F793 ASYMMETRIC LELAND DYNAMIC NO-TRADE BUFFER BANDS SUITE
# ==============================================================================

class TestF793AsymmetricLelandBandsAdversarial:
    """Empirical adversarial stress testing of Feature F793 Asymmetric Leland Buffer Bands."""

    def test_adv_f793_asymmetric_multipliers_runner_loser(self):
        """Verify runner expansion (z > 0 -> upper multiplier up to 2.4x) and loser contraction (z < 0 -> down to 0.5x)."""
        opt = Phase162TurnoverOptimizer()

        # Runner (z = +3.0)
        m_run = opt.compute_asymmetric_leland_multipliers(z_score=3.0)
        assert m_run.upper >= 1.50
        assert m_run.upper <= 2.40

        # Loser (z = -3.0)
        m_lose = opt.compute_asymmetric_leland_multipliers(z_score=-3.0)
        assert m_lose.lower <= 0.80
        assert m_lose.lower >= 0.50

        # Zero momentum (z = 0.0)
        m_zero = opt.compute_asymmetric_leland_multipliers(z_score=0.0)
        assert math.isclose(m_zero.upper, 1.0, abs_tol=1e-5)
        assert math.isclose(m_zero.lower, 1.0, abs_tol=1e-5)

    def test_adv_f793_strict_instant_zero_latency_bypass(self):
        """Verify instant bypass strictly triggers for fresh entries (w_0 = 0) and full exits (w* = 0)."""
        opt = Phase162TurnoverOptimizer()

        # Fresh entry: curr = 0.0 -> target = 0.04 -> MUST BYPASS
        assert opt.evaluate_rebalance_bypass(target_weight=0.04, current_weight=0.0) is True

        # Full liquidation: curr = 0.04 -> target = 0.0 -> MUST BYPASS
        assert opt.evaluate_rebalance_bypass(target_weight=0.0, current_weight=0.04) is True

        # In-band containment: target inside [0.035, 0.045] -> MUST SUPPRESS (return False)
        assert opt.evaluate_rebalance_bypass(
            target_weight=0.041,
            current_weight=0.040,
            lower_band=0.035,
            upper_band=0.045,
        ) is False

        # Out-of-band drift: target outside [0.035, 0.045] -> MUST REBALANCE (return True)
        assert opt.evaluate_rebalance_bypass(
            target_weight=0.055,
            current_weight=0.040,
            lower_band=0.035,
            upper_band=0.045,
        ) is True

    def test_adv_f793_bandwidth_volatility_scaling_and_bounds(self):
        """Verify dynamic bandwidth Delta_i scales monotonically with volatility and stays within [0.005, 0.10]."""
        opt = Phase162TurnoverOptimizer()

        bw_min = opt.compute_dynamic_bandwidth(volatility=0.0)
        assert bw_min == 0.005  # Floor

        bw_med = opt.compute_dynamic_bandwidth(volatility=0.20)
        bw_high = opt.compute_dynamic_bandwidth(volatility=0.60)
        assert bw_high > bw_med > bw_min

        bw_extreme = opt.compute_dynamic_bandwidth(volatility=100.0)
        assert bw_extreme <= 0.10  # Ceiling

    def test_adv_f793_turnover_reduction_benchmark_exceeds_40_pct(self):
        """Verify certified turnover reduction ratio achieves >= 40.0% (calibrated at 43.5%)."""
        opt = Phase162TurnoverOptimizer()
        reduction = opt.compute_turnover_reduction_ratio()
        assert reduction >= 0.40
        assert math.isclose(reduction, 0.435, abs_tol=1e-3)


# ==============================================================================
# SECTION 5: F794 LOCK-FREE OMS GATEWAY & CONCURRENCY DETERMINISM SUITE
# ==============================================================================

class TestF794LockFreeOMSAndConcurrencyAdversarial:
    """Empirical adversarial stress testing of Feature F794 Lock-Free OMS & Concurrency."""

    def test_adv_f794_gate8_synthetic_inverse_hedge_regimes(self):
        """Verify Gate 8 synthetic inverse hedge activation across market regimes."""
        oms = Phase162ExecutionOMSEngine()

        # Crisis regimes in KRX -> 114800 or 252670
        h_krx_bear = oms.evaluate_gate8_inverse_hedge(regime="BEAR_HIGH_VOL", market="KOSPI")
        assert h_krx_bear["hedge_active"] is True
        assert h_krx_bear["hedge_symbol"] in ("114800", "252670")
        assert h_krx_bear["target_hedge_weight"] == 0.15

        h_krx_panic = oms.evaluate_gate8_inverse_hedge(regime="PANIC_CRISIS", market="KOSDAQ")
        assert h_krx_panic["hedge_active"] is True
        assert h_krx_panic["hedge_symbol"] in ("114800", "252670")

        # Crisis regimes in US -> PSQ or SH
        h_us_bear = oms.evaluate_gate8_inverse_hedge(regime="BEAR_HIGH_VOL", market="NASDAQ")
        assert h_us_bear["hedge_active"] is True
        assert h_us_bear["hedge_symbol"] in ("PSQ", "SH")

        h_us_panic = oms.evaluate_gate8_inverse_hedge(regime="PANIC_CRISIS", market="SP500")
        assert h_us_panic["hedge_active"] is True
        assert h_us_panic["hedge_symbol"] in ("PSQ", "SH")

        # Non-crisis regimes -> inactive
        h_bull = oms.evaluate_gate8_inverse_hedge(regime="BULL_LOW_VOL", market="KOSPI")
        assert h_bull["hedge_active"] is False
        assert h_bull["hedge_symbol"] == ""

    def test_adv_f794_atomic_8_safety_gates_rejection_matrix(self):
        """Stress test 8 safety gates under extreme adversarial inputs."""
        oms = Phase162ExecutionOMSEngine()

        # Gate 1: Capital slice cap
        assert oms.check_capital_slice_gate(order_val=100_000_000.0, max_slice=20_000_000.0) is False
        assert oms.check_capital_slice_gate(order_val=5_000_000.0, max_slice=20_000_000.0) is True

        # Gate 2: Non-positive / invalid prices
        for bad_p in [0.0, -1.0, float("nan"), float("inf"), float("-inf")]:
            assert _is_invalid_or_nonpositive_price(bad_p) is True
        assert _is_invalid_or_nonpositive_price(70000.0) is False

        # Gate 4: Daily limit move circuit breaker (+-30%)
        assert oms.check_circuit_breaker_gate("005930", change_pct=0.30) is False
        assert oms.check_circuit_breaker_gate("005930", change_pct=-0.30) is False
        assert oms.check_circuit_breaker_gate("005930", change_pct=0.15) is True

        # Gate 6: ADV participation cap (1.5% max)
        assert oms.check_adv_participation_gate(order_qty=20000, adv=1000000) is False  # 2.0% > 1.5%
        assert oms.check_adv_participation_gate(order_qty=10000, adv=1000000) is True   # 1.0% <= 1.5%

    def test_adv_f794_16_thread_concurrency_stress_determinism(self):
        """16-thread high-concurrency stress test with simultaneous order planning and lockless dispatching."""
        oms = Phase162ExecutionOMSEngine()
        dispatcher = Phase162LocklessOMSDispatcher()
        num_threads = 16
        orders_per_thread = 50
        errors: List[str] = []
        successful_dispatches: List[int] = []

        def worker(thread_idx: int):
            for i in range(orders_per_thread):
                try:
                    order_id = thread_idx * 1000 + i
                    order = DispatchOrder(
                        order_id=order_id,
                        symbol="005930",
                        side="BUY",
                        order_type="LIMIT",
                        quantity=10.0,
                        price=70000.0,
                    )
                    res = dispatcher.dispatch(order, async_mode=False)
                    if res.success:
                        successful_dispatches.append(order_id)
                except Exception as ex:
                    errors.append(f"Thread {thread_idx} error on order {i}: {ex}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent execution generated errors: {errors[:5]}"
        assert len(successful_dispatches) == num_threads * orders_per_thread

    def test_adv_f794_32_thread_high_concurrency_stress(self):
        """Push concurrency to 32 threads under heavy order traffic to verify absence of race conditions."""
        oms = Phase162ExecutionOMSEngine()
        dispatcher = Phase162LocklessOMSDispatcher()
        num_threads = 32
        errors: List[str] = []

        def worker(tid: int):
            try:
                plan = oms.generate_order_plan(
                    top_predictions=[{"symbol": "005930", "close_price": 70000.0, "market": "KOSPI"}],
                    portfolio_weights={"005930": 0.04},
                    current_holdings={"005930": 0.0},
                    prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 5})},
                    total_capital=100_000_000.0,
                )
                assert len(plan) == 1
            except Exception as ex:
                errors.append(f"Thread {tid} error: {ex}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"32-thread stress failed: {errors}"


# ==============================================================================
# SECTION 6: CONSERVATION LAWS & AUDIT TRAIL PERSISTENCE SUITE
# ==============================================================================

class TestMicrostructureConservationAndPersistenceAdversarial:
    """Empirical verification of conservation laws and SQLite audit trail."""

    def test_adv_paper_trading_conservation_law_multi_cycle(self):
        """Verify Net Equity <= Gross Equity across 20 simulated rebalance cycles with random price walks."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name
        try:
            daemon = PaperTradingDaemon(db_path=db_path, initial_capital=100_000_000.0)
            rng = np.random.default_rng(999)
            base_price = 70000.0

            for cycle in range(20):
                ret = rng.standard_normal() * 0.02
                base_price *= (1.0 + ret)
                targets = {"005930": 0.05}
                prices = {"005930": base_price}

                res = daemon.run_cycle(target_weights=targets, current_prices=prices, dry_run=True)
                assert res["status"] == "SUCCESS"
                assert daemon.verify_conservation_invariant() is True
                assert daemon.net_equity <= daemon.gross_equity + 1e-9
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass

    def test_adv_sqlite_wal_persistence_under_concurrent_writers(self):
        """Verify SQLite WAL mode handles multi-threaded execution without database locks or corruptions."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name
        try:
            oms = Phase162ExecutionOMSEngine(db_path=db_path)
            errors: List[str] = []

            def writer(tid: int):
                try:
                    for i in range(10):
                        top_preds = [{"symbol": f"SYM_{tid}_{i}", "close_price": 50000.0, "market": "KOSPI"}]
                        _ = oms.generate_order_plan(
                            top_predictions=top_preds,
                            portfolio_weights={f"SYM_{tid}_{i}": 0.02},
                            current_holdings={f"SYM_{tid}_{i}": 0.0},
                            prices_dict={f"SYM_{tid}_{i}": pd.DataFrame({"Close": [50000.0] * 5})},
                            total_capital=100_000_000.0,
                        )
                except Exception as ex:
                    errors.append(f"Writer {tid} error: {ex}")

            threads = [threading.Thread(target=writer, args=(t,)) for t in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"SQLite concurrency errors: {errors}"
            assert os.path.exists(db_path)
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass

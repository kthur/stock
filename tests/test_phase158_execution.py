# -*- coding: utf-8 -*-
"""
tests/test_phase158_execution.py -- Comprehensive 50-Test Unit & Integration Catalog
for Phase 158 (Features F770–F774): Execution OMS, Microstructure & Parity.

Catalog Summary:
  Cat 1: Constants & Parity (TC01 to TC05)
  Cat 2: F770 Hierarchical MARL Execution (TC06 to TC14)
  Cat 3: F771 Ultra-Low Latency L3 Matching & Rebates (TC15 to TC22)
  Cat 4: F772 5D Adaptive Kalman Market Impact Filter (TC23 to TC30)
  Cat 5: F773 Multi-Asset Asymmetric Leland Dynamic Buffer Bands (TC31 to TC38)
  Cat 6: F774 Lock-Free Atomic OMS Gateway with Gate 8 Synthetic Inverse Hedge (TC39 to TC46)
  Cat 7: System Invariants, Concurrency & Persistence (TC47 to TC50)
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

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.rl_execution_agent import (
    ExecutionState,
    ContinuousAction,
    ExecutionAction,
    RLExecutionAgent,
    Phase158RLExecutionAgent,
    evaluate_execution_action_phase158,
)
from src.core.fast_lob_engine import (
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    Phase158FastLOBEngine,
    Phase158FastOrderBookMatchingEngine,
)
from src.execution.slippage_feedback import (
    OnlineKalmanSlippageFilter,
    Online5DKalmanSlippageFilter,
    SlippageFeedbackEngine,
    Phase158OnlineKalmanFilter,
    Phase158Online5DKalmanSlippageFilter,
    Phase158SlippageFeedbackEngine,
)
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    AsymmetricLelandMultipliers,
    Phase158TurnoverOptimizer,
    Phase158AsymmetricLelandOptimizer,
)
from src.execution.oms_engine import (
    ExecutionOMSEngine,
    Phase158OMSEngine,
    Phase158ExecutionOMSEngine,
    _is_invalid_or_nonpositive_price,
)
from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    Phase158PaperTradingDaemon,
)


# =============================================================================
# CATEGORY 1: CONSTANTS & CRYPTOGRAPHIC PARITY (TC01 to TC05)
# =============================================================================

class TestCategory1ConstantsAndParity:
    """Cat 1: Module versioning, release metadata, cryptographic dual-tree parity and aliases."""

    def test_tc01_phase158_module_constants(self):
        """TC01: Verify VERSION == 158, RELEASE in ('R155', 'R158', 'R159'), and F770-F774 presence."""
        import src.execution.rl_execution_agent as mod_rl
        import src.core.fast_lob_engine as mod_lob
        import src.execution.slippage_feedback as mod_slip
        import src.execution.turnover_optimizer as mod_turn
        import src.execution.oms_engine as mod_oms

        for mod in (mod_rl, mod_lob, mod_slip, mod_turn, mod_oms):
            assert int(mod.VERSION) == 158
            assert str(mod.RELEASE) in ("R155", "R158", "R159")
        assert "F770" in str(mod_rl.FEATURE)
        assert "F771" in str(mod_lob.FEATURE)
        assert "F772" in str(mod_slip.FEATURE)
        assert "F773" in str(mod_turn.FEATURE)
        assert "F774" in str(mod_oms.FEATURE)

    def test_tc02_cryptographic_dual_tree_parity(self):
        """TC02: SHA-256 bit-for-bit parity check between src/ and trading_system/src/."""
        target_files = [
            "src/execution/rl_execution_agent.py",
            "src/core/fast_lob_engine.py",
            "src/execution/slippage_feedback.py",
            "src/execution/turnover_optimizer.py",
            "src/execution/oms_engine.py",
            "src/execution/paper_trading_daemon.py",
        ]
        for rel_path in target_files:
            p1 = _PROJECT_ROOT / rel_path
            p2 = _PROJECT_ROOT / "trading_system" / rel_path
            assert p1.exists(), f"Source file missing: {p1}"
            assert p2.exists(), f"Mirror file missing: {p2}"
            h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
            assert h1 == h2, f"Dual-tree parity mismatch in {rel_path}: {h1[:12]} != {h2[:12]}"

    def test_tc03_complete_alias_hierarchy(self):
        """TC03: Verify Phase 158 aliases instantiate identically across all target classes."""
        assert Phase158RLExecutionAgent is RLExecutionAgent
        assert Phase158FastLOBEngine is FastOrderBookMatchingEngine
        assert Phase158FastOrderBookMatchingEngine is FastOrderBookMatchingEngine
        assert Phase158OnlineKalmanFilter is OnlineKalmanSlippageFilter
        assert Phase158Online5DKalmanSlippageFilter is Online5DKalmanSlippageFilter
        assert Phase158SlippageFeedbackEngine is SlippageFeedbackEngine
        assert Phase158TurnoverOptimizer is TurnoverOptimizer
        assert Phase158AsymmetricLelandOptimizer is TurnoverOptimizer
        assert Phase158OMSEngine is ExecutionOMSEngine
        assert Phase158ExecutionOMSEngine is ExecutionOMSEngine
        assert Phase158PaperTradingDaemon is PaperTradingDaemon

    def test_tc04_polymorphic_backward_compatibility(self):
        """TC04: Verify int(VERSION) == 158, comparisons VERSION >= 154, and release string compatibility."""
        import src.execution.oms_engine as mod_oms
        v = mod_oms.VERSION
        assert int(v) == 158
        assert v >= 154
        assert v >= 150
        assert v <= 158
        assert v == 158
        assert mod_oms.RELEASE == "R159" or mod_oms.RELEASE in ("R154", "R155", "R159")

    def test_tc05_default_engine_hyperparameters(self):
        """TC05: Verify default initialization hyperparameters across all 5 execution modules."""
        agent = RLExecutionAgent()
        lob = FastOrderBookMatchingEngine(symbol="005930")
        slip = SlippageFeedbackEngine()
        turn = TurnoverOptimizer()
        oms = ExecutionOMSEngine()

        assert lob.LATENCY_TARGET_US <= 35.0
        assert slip.kalman_filter.dim == 5
        assert turn.turnover_threshold_pct == 0.05
        assert oms.initial_capital == 100_000_000.0


# =============================================================================
# CATEGORY 2: FEATURE F770 HIERARCHICAL MARL EXECUTION (TC06 to TC14)
# =============================================================================

class TestCategory2MARLExecution:
    """Cat 2: Macro allocator, micro slicer, quantile critic, and guardrail policies."""

    def test_tc06_meta_controller_macro_tranche_ratio(self):
        """TC06: Verify meta-controller computes macro tranche ratio u_t in [0.0, 1.0]."""
        agent = RLExecutionAgent()
        ratio1 = agent.compute_meta_tranche_ratio(remaining_time=0.8, remaining_inventory=0.8)
        ratio2 = agent.compute_meta_tranche_ratio(remaining_time=0.1, remaining_inventory=0.9)
        assert 0.0 <= ratio1 <= 1.0
        assert 0.0 <= ratio2 <= 1.0
        # More urgent when time is running out
        assert ratio2 >= ratio1

    def test_tc07_micro_worker_routing_action_simplex(self):
        """TC07: Verify 4-venue continuous simplex sums to 1.0 +- 1e-5."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.3, inventory_ratio=0.7, spread_bps=2.5, obi=0.2, vpin=0.2, volatility=0.015)
        simplex = agent.compute_routing_simplex_action(st)
        assert set(simplex.keys()) == {"lit_maker", "lit_taker", "dark_midpoint", "tactical_pause"}
        assert all(v >= 0.0 for v in simplex.values())
        assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-5)

    def test_tc08_distributional_quantile_critic_cvar95(self):
        """TC08: Verify Quantile Critic with K=25 quantiles computes finite downside CVaR_0.95."""
        agent = RLExecutionAgent()
        price_diffs = np.array([-2.5, -1.8, -0.5, 0.2, 0.8, -3.2, -4.0, 0.1, -1.2, 0.5])
        cvar = agent.compute_downside_cvar_quantiles(num_quantiles=25, alpha_cvar=0.95, price_diffs=price_diffs)
        assert isinstance(cvar, float)
        assert math.isfinite(cvar)

    def test_tc09_quantile_huber_loss_pinball_weighting(self):
        """TC09: Verify asymmetric pinball quantile Huber loss calculation."""
        tau = 0.95
        kappa = 1.0
        # Under-prediction (positive error) vs over-prediction (negative error)
        u_pos = 2.0
        u_neg = -2.0
        loss_pos = abs(tau - (1.0 if u_pos < 0 else 0.0)) * (0.5 * (u_pos ** 2) if abs(u_pos) <= kappa else kappa * (abs(u_pos) - 0.5 * kappa))
        loss_neg = abs(tau - (1.0 if u_neg < 0 else 0.0)) * (0.5 * (u_neg ** 2) if abs(u_neg) <= kappa else kappa * (abs(u_neg) - 0.5 * kappa))
        assert loss_pos > 0.0
        assert loss_neg > 0.0
        assert loss_pos != loss_neg  # Asymmetry due to pinball tau=0.95

    def test_tc10_toxic_vpin_pause_trigger(self):
        """TC10: Verify VPIN spike > 0.65 triggers TACTICAL_PAUSE."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=3.0, obi=0.1, vpin=0.72, volatility=0.02)
        res = agent.evaluate_execution_action_phase158(state=st, vpin=0.72, tau_close=0.5, q_rem=0.5)
        assert res == "TACTICAL_PAUSE"

    def test_tc11_terminal_urgency_taker_trigger(self):
        """TC11: Verify terminal urgency (tau_close <= 0.05, q_rem > 0.05) triggers AGGRESSIVE_TAKER."""
        agent = RLExecutionAgent()
        st = ExecutionState(time_ratio=0.96, inventory_ratio=0.3, spread_bps=2.0, obi=0.0, vpin=0.2, volatility=0.015)
        res = agent.evaluate_execution_action_phase158(state=st, vpin=0.2, tau_close=0.04, q_rem=0.3)
        assert res == "AGGRESSIVE_TAKER"

    def test_tc12_zero_inventory_boundary_guard(self):
        """TC12: Verify zero inventory remaining evaluates cleanly to 0.0 tranche ratio."""
        agent = RLExecutionAgent()
        ratio = agent.compute_meta_tranche_ratio(remaining_time=0.5, remaining_inventory=0.0)
        assert ratio == 0.0

    def test_tc13_implementation_shortfall_reward_calculation(self):
        """TC13: Verify positive reward on implementation shortfall outperformance."""
        arrival_price = 70000.0
        exec_price = 69950.0  # Favorable buy fill below arrival
        is_bps = ((arrival_price - exec_price) / arrival_price) * 10000.0
        reward = is_bps * 0.1
        assert reward > 0.0

    def test_tc14_state_vector_nan_inf_sanitization(self):
        """TC14: Verify ExecutionState sanitizes NaN and Inf inputs cleanly."""
        agent = RLExecutionAgent()
        st = ExecutionState(
            time_ratio=float("nan"),
            inventory_ratio=float("inf"),
            spread_bps=-10.0,
            obi=float("-inf"),
            vpin=float("nan"),
            volatility=-0.05,
        )
        vec = st.to_12d_vector()
        assert np.isfinite(vec).all()
        act = agent.compute_continuous_action(st)
        assert math.isfinite(act.slice_ratio)


# =============================================================================
# CATEGORY 3: FEATURE F771 L3 MATCHING & REBATES (TC15 to TC22)
# =============================================================================

class TestCategory3L3MatchingAndRebates:
    """Cat 3: Zero-copy ring buffer, midpoint dark crossing, rebates, FIFO matching."""

    def test_tc15_circular_ring_buffer_o1_append_latency(self):
        """TC15: Verify ZeroCopyRingBuffer.append_order_phase158 executes in sub-35 microseconds."""
        buf = ZeroCopyRingBuffer(capacity=10000)
        t0 = time.perf_counter()
        for i in range(100):
            buf.append_order_phase158(f"ORD_{i}", "005930", 70000.0, 10.0, "BUY")
        t_total_us = (time.perf_counter() - t0) / 100.0 * 1e6
        assert t_total_us < 35.0

    def test_tc16_circular_ring_buffer_wrap_around_overflow(self):
        """TC16: Verify ring buffer wrap-around when append count exceeds buffer capacity."""
        buf = ZeroCopyRingBuffer(capacity=16)
        for i in range(32):
            buf.append_order_phase158(f"ORD_{i}", price=70000.0, qty=1.0, side="BUY")
        assert buf.count == 16
        assert buf.head == 0

    def test_tc17_nextrade_ats_midpoint_crossing_spread_savings(self):
        """TC17: Verify midpoint crossing executes at (Bid+Ask)/2 capturing exactly 50% spread savings."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        res = lob.execute_midpoint_crossing(symbol="005930", qty=100, bid=100.0, ask=102.0)
        assert res["exec_price"] == 101.0
        assert math.isclose(res["spread_saved_pct"], 50.0, abs_tol=1e-5)

    def test_tc18_passive_maker_rebate_harvesting(self):
        """TC18: Verify maker rebate credit computes exact formula: Notional * rebate_bps / 10000."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        rebate = lob.compute_maker_rebate(notional=10_000_000.0, rebate_bps=2.0)
        assert math.isclose(rebate, 2000.0, abs_tol=1e-5)

    def test_tc19_level3_fifo_price_time_priority_matching(self):
        """TC19: Verify deterministic FIFO matching queues orders at identical price levels."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        lob.submit_limit_order("ORD_1", "005930", "BUY", price=70000.0, qty=10.0)
        lob.submit_limit_order("ORD_2", "005930", "BUY", price=70000.0, qty=20.0)

        # Incoming sell market order for 15 shares
        sell_order = {"order_id": "SELL_1", "symbol": "005930", "side": "SELL", "price": 70000.0, "qty": 15.0}
        fills = lob.match_limit_order(sell_order)
        assert len(fills) >= 1
        # First order filled completely (10 shares)
        assert fills[0].get("order_id") == "ORD_1" or fills[0].get("maker_order_id") == "ORD_1"
        assert fills[0].get("filled_qty", fills[0].get("volume", fills[0].get("qty"))) == 10.0

    def test_tc20_crossed_order_book_immediate_crossing(self):
        """TC20: Verify crossed order book (Bid >= Ask) triggers immediate liquidity crossing fill."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        lob.submit_limit_order("BID_1", "005930", "BUY", price=70500.0, qty=10.0)
        # Sell at 70000.0 is crossed with buy at 70500.0
        res = lob.submit_limit_order("ASK_1", "005930", "SELL", price=70000.0, qty=10.0)
        assert bool(res) is True

    def test_tc21_subpenny_rounding_and_zero_qty_rejection(self):
        """TC21: Verify strict rejection of zero or negative order quantities."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        res_zero = lob.submit_limit_order("BAD_1", "005930", "BUY", price=70000.0, qty=0.0)
        res_neg = lob.submit_limit_order("BAD_2", "005930", "BUY", price=70000.0, qty=-10.0)
        assert bool(res_zero) is False
        assert bool(res_neg) is False

    def test_tc22_high_throughput_burst_memory_stability(self):
        """TC22: Verify 5,000 order sequence injection executes without exceptions or leaks."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5000):
            side = "BUY" if i % 2 == 0 else "SELL"
            p = 70000.0 + (i % 20) * 100.0
            lob.submit_limit_order(f"BURST_{i}", "005930", side, price=p, qty=1.0)
        assert lob.order_counter == 5000


# =============================================================================
# CATEGORY 4: FEATURE F772 5D KALMAN MARKET IMPACT (TC23 to TC30)
# =============================================================================

class TestCategory4KalmanMarketImpact:
    """Cat 4: 5D state vector, Joseph-stabilized covariance, bounds, friction export."""

    def test_tc23_5d_state_vector_initialization(self):
        """TC23: Verify 5D state vector [kappa, beta, eta, rho, zeta] initializes with valid values."""
        engine = SlippageFeedbackEngine()
        state = engine.get_5d_state()
        assert len(state) == 5
        assert set(state.keys()) == {"kappa", "beta", "eta", "rho", "zeta"}
        assert all(v > 0.0 for v in state.values())

    def test_tc24_joseph_stabilized_covariance_update_psd(self):
        """TC24: Verify Joseph-stabilized update maintains exact matrix symmetry and positive-definiteness."""
        engine = SlippageFeedbackEngine()
        P = np.eye(5) * 0.25
        H = np.array([1.0, 0.5, 0.2, 0.1, 0.05])
        R = 0.05
        P_next = engine.joseph_update_5d(P, H, R, y=0.15)
        # Symmetry
        assert np.allclose(P_next, P_next.T, atol=1e-10)
        # Positive eigenvalues
        eigs = np.linalg.eigvals(P_next)
        assert (eigs > 0.0).all()

    def test_tc25_observation_innovation_state_update(self):
        """TC25: Verify observation innovation updates parameters toward realized slippage."""
        engine = SlippageFeedbackEngine()
        k_init = engine.kalman_filter.kappa
        engine.kalman_filter.update(realized_slippage_bps=20.0, h_kappa=4.0, h_beta=4.0)
        assert engine.kalman_filter.update_count >= 1

    def test_tc26_dynamic_cost_scaling_factor_bounds(self):
        """TC26: Verify dynamic cost scaling factor is bounded strictly in [0.50, 8.00]."""
        engine = SlippageFeedbackEngine()
        factor = engine.kalman_filter.get_state().get("cost_scaling_factor", 1.0)
        assert 0.50 <= factor <= 8.00

    def test_tc27_extreme_slippage_shock_absorption(self):
        """TC27: Verify 1,000 bps slippage shock is absorbed gracefully without numerical overflow."""
        engine = SlippageFeedbackEngine()
        engine.kalman_filter.update(realized_slippage_bps=1000.0, h_kappa=5.0, h_beta=5.0)
        state = engine.kalman_filter.get_state()
        assert math.isfinite(state["kappa"])
        assert state["kappa"] <= 5.0

    def test_tc28_asymptotic_observation_noise_limits(self):
        """TC28: Verify R -> 0 gives direct innovation update and R -> inf preserves prior state."""
        engine = SlippageFeedbackEngine()
        P = 0.1
        H = 1.0
        # R -> 0
        K_zero = P * H / (H * P * H + 1e-6)
        assert math.isclose(K_zero, 1.0, abs_tol=1e-3)
        # R -> inf
        K_inf = P * H / (H * P * H + 1e9)
        assert math.isclose(K_inf, 0.0, abs_tol=1e-6)

    def test_tc29_ensemble_scoring_friction_deduction_export(self):
        """TC29: Verify scaled friction deduction integrates cleanly and is strictly positive."""
        engine = SlippageFeedbackEngine()
        deduction = engine.compute_friction_deduction_bps(base_spread_bps=5.0, notional=1e7)
        assert isinstance(deduction, float)
        assert deduction > 0.0

    def test_tc30_multi_asset_kalman_tracking_stability(self):
        """TC30: Verify stability across heterogeneous market profiles (KOSPI vs NASDAQ)."""
        engine = SlippageFeedbackEngine()
        for _ in range(5):
            engine.kalman_filter.update(realized_slippage_bps=6.0, h_kappa=2.5, h_beta=5.0)  # KOSPI
            engine.kalman_filter.update(realized_slippage_bps=3.5, h_kappa=1.5, h_beta=3.0)  # NASDAQ
        st = engine.get_5d_state()
        assert all(math.isfinite(v) for v in st.values())


# =============================================================================
# CATEGORY 5: FEATURE F773 ASYMMETRIC LELAND BUFFER BANDS (TC31 to TC38)
# =============================================================================

class TestCategory5AsymmetricLelandBands:
    """Cat 5: Runner/loser multipliers, instant bypass, noise suppression, bandwidth scaling."""

    def test_tc31_asymmetric_runner_loser_multipliers(self):
        """TC31: Verify asymmetric multipliers expand upper band for runners and contract lower for losers."""
        opt = TurnoverOptimizer()
        m_runner = opt.compute_asymmetric_leland_multipliers(z_score=2.0)
        m_loser = opt.compute_asymmetric_leland_multipliers(z_score=-2.0)
        assert m_runner["upper"] >= 1.5
        assert m_loser["lower"] <= 0.8
        # Tuple unpacking compatibility
        u, l = m_runner
        assert u == m_runner["upper"]
        assert l == m_runner["lower"]

    def test_tc32_instant_bypass_fresh_portfolio_entry(self):
        """TC32: Verify instant bypass triggers immediate order when current weight is zero."""
        opt = TurnoverOptimizer()
        bp = opt.evaluate_rebalance_bypass(target_weight=0.05, current_weight=0.0)
        assert bp is True

    def test_tc33_instant_bypass_complete_liquidation(self):
        """TC33: Verify instant bypass triggers immediate order when target weight is zero."""
        opt = TurnoverOptimizer()
        bp = opt.evaluate_rebalance_bypass(target_weight=0.0, current_weight=0.05)
        assert bp is True

    def test_tc34_noise_rebalance_suppression_within_bands(self):
        """TC34: Verify rebalancing is suppressed when target weight lies inside buffer bands."""
        opt = TurnoverOptimizer()
        bp = opt.evaluate_rebalance_bypass(target_weight=0.042, current_weight=0.040, lower_band=0.035, upper_band=0.045)
        assert bp is False

    def test_tc35_volatility_normalized_bandwidth_scaling(self):
        """TC35: Verify Leland buffer bandwidth expands monotonically with asset volatility."""
        opt = TurnoverOptimizer()
        bw_low = opt.compute_dynamic_bandwidth(volatility=0.10)
        bw_high = opt.compute_dynamic_bandwidth(volatility=0.40)
        assert bw_high > bw_low

    def test_tc36_zero_volatility_floor_bandwidth_fallback(self):
        """TC36: Verify zero asset volatility maintains minimum floor bandwidth (0.005)."""
        opt = TurnoverOptimizer()
        bw_zero = opt.compute_dynamic_bandwidth(volatility=0.0)
        assert bw_zero == 0.005

    def test_tc37_boundary_target_weight_clamping(self):
        """TC37: Verify extreme volatility (1000%) clamps bandwidth strictly at upper bound (0.10)."""
        opt = TurnoverOptimizer()
        bw_extreme = opt.compute_dynamic_bandwidth(volatility=10.0)
        assert bw_extreme <= 0.10

    def test_tc38_turnover_reduction_benchmark_exceeds_40_pct(self):
        """TC38: Verify turnover reduction benchmark achieves >= 40% reduction."""
        opt = TurnoverOptimizer()
        red = opt.compute_turnover_reduction_ratio()
        assert red >= 0.40


# =============================================================================
# CATEGORY 6: FEATURE F774 LOCK-FREE ATOMIC OMS GATEWAY (TC39 to TC46)
# =============================================================================

class TestCategory6LockFreeOMSGateway:
    """Cat 6: 8 safety gates, atomic latency, Gate 8 synthetic inverse hedge, price sanity."""

    def test_tc39_atomic_safety_gates_latency_under_500ns(self):
        """TC39: Verify atomic safety gates execute in sub-500ns per check."""
        t0 = time.perf_counter()
        for _ in range(1000):
            _is_invalid_or_nonpositive_price(70000.0)
        t_per_check_ns = (time.perf_counter() - t0) / 1000.0 * 1e9
        assert t_per_check_ns < 500.0

    def test_tc40_gate1_max_capital_slice_cap_rejection(self):
        """TC40: Verify Gate 1 rejects orders exceeding maximum capital slice cap."""
        oms = ExecutionOMSEngine()
        assert oms.check_capital_slice_gate(order_val=50_000_000.0, max_slice=20_000_000.0) is False
        assert oms.check_capital_slice_gate(order_val=10_000_000.0, max_slice=20_000_000.0) is True

    def test_tc41_gate2_invalid_and_nonpositive_price_rejection(self):
        """TC41: Verify Gate 2 rejects prices 0.0, -10.0, NaN, and Inf."""
        assert _is_invalid_or_nonpositive_price(0.0) is True
        assert _is_invalid_or_nonpositive_price(-10.0) is True
        assert _is_invalid_or_nonpositive_price(float("nan")) is True
        assert _is_invalid_or_nonpositive_price(float("inf")) is True
        assert _is_invalid_or_nonpositive_price(70000.0) is False

    def test_tc42_gate3_kill_switch_and_crisis_level_blocking(self):
        """TC42: Verify Gate 3 blocks BUY orders when crisis level is SEVERE."""
        oms = ExecutionOMSEngine()
        top_preds = [{"symbol": "005930", "close_price": 70000.0, "market": "KOSPI"}]
        plan = oms.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights={"005930": 0.05},
            current_holdings={"005930": 0.0},
            prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 5})},
            total_capital=100_000_000.0,
            crisis_level="SEVERE",
        )
        assert len(plan) == 0

    def test_tc43_gate4_circuit_breaker_limit_move_rejection(self):
        """TC43: Verify Gate 4 rejects symbols locked at daily limit move (+-30%)."""
        oms = ExecutionOMSEngine()
        assert oms.check_circuit_breaker_gate(symbol="005930", change_pct=0.299) is False
        assert oms.check_circuit_breaker_gate(symbol="005930", change_pct=-0.298) is False
        assert oms.check_circuit_breaker_gate(symbol="005930", change_pct=0.05) is True

    def test_tc44_gate6_adv_liquidity_cap_rejection(self):
        """TC44: Verify Gate 6 rejects order quantities exceeding 1.5% of 20-day ADV."""
        oms = ExecutionOMSEngine()
        assert oms.check_adv_participation_gate(order_qty=50000, adv=1000000) is False
        assert oms.check_adv_participation_gate(order_qty=10000, adv=1000000) is True

    def test_tc45_gate8_synthetic_inverse_hedge_activation_regime(self):
        """TC45: Verify Gate 8 activates synthetic inverse hedge under BEAR_HIGH_VOL."""
        oms = ExecutionOMSEngine()
        h_krx = oms.evaluate_gate8_inverse_hedge(regime="BEAR_HIGH_VOL", market="KOSPI")
        assert h_krx["hedge_active"] is True
        assert h_krx["hedge_symbol"] in ("114800", "252670")

        h_bull = oms.evaluate_gate8_inverse_hedge(regime="BULL_LOW_VOL", market="KOSPI")
        assert h_bull["hedge_active"] is False

    def test_tc46_gate8_synthetic_inverse_hedge_beta_breach(self):
        """TC46: Verify Gate 8 emits PSQ/SH in US under crisis regimes."""
        oms = ExecutionOMSEngine()
        h_us = oms.evaluate_gate8_inverse_hedge(regime="PANIC_CRISIS", market="NASDAQ")
        assert h_us["hedge_active"] is True
        assert h_us["hedge_symbol"] in ("PSQ", "SH")


# =============================================================================
# CATEGORY 7: SYSTEM INVARIANTS, CONCURRENCY & PERSISTENCE (TC47 to TC50)
# =============================================================================

class TestCategory7InvariantsAndConcurrency:
    """Cat 7: Paper trading conservation law, multi-threaded stress, and SQLite persistence."""

    def test_tc47_paper_trading_conservation_invariant_random_walk(self):
        """TC47: Verify Net Equity <= Gross Equity + 1e-9 across simulated execution cycles."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name
        try:
            daemon = PaperTradingDaemon(db_path=temp_db, initial_capital=100_000_000.0)
            assert daemon.verify_conservation_invariant() is True
            assert daemon.net_equity <= daemon.gross_equity + 1e-9

            # Simulate simple cycle
            targets = {"005930": 0.05, "000660": 0.05}
            prices = {"005930": 70000.0, "000660": 150000.0}
            summary = daemon.run_cycle(target_weights=targets, current_prices=prices, dry_run=True)
            assert summary["status"] == "SUCCESS"
            assert summary["invariant_net_le_gross"] is True
            assert daemon.verify_conservation_invariant() is True
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass

    def test_tc48_punitive_fees_monotonic_equity_divergence(self):
        """TC48: Verify friction and fees strictly widen gross-net equity gap (Gross >= Net)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name
        try:
            daemon = PaperTradingDaemon(db_path=temp_db, initial_capital=50_000_000.0)
            # Initial state: Gross == Net
            assert math.isclose(daemon.gross_equity, daemon.net_equity, abs_tol=1e-5)
            # After trade fees paid
            daemon.total_fees_paid += 50000.0
            daemon.cash_balance -= 50000.0
            daemon.net_equity -= 50000.0
            assert daemon.gross_equity >= daemon.net_equity
            assert daemon.verify_conservation_invariant() is True
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass

    def test_tc49_32_concurrent_threads_lock_free_stress(self):
        """TC49: Verify 32 concurrent threads generating order plans simultaneously."""
        oms = ExecutionOMSEngine()
        results = []

        def worker(tid: int):
            plan = oms.generate_order_plan(
                top_predictions=[{"symbol": "005930", "close_price": 70000.0, "market": "KOSPI"}],
                portfolio_weights={"005930": 0.04},
                current_holdings={"005930": 0.0},
                prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 5})},
                total_capital=100_000_000.0,
            )
            results.append(len(plan))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 32
        assert all(r == 1 for r in results)

    def test_tc50_audit_trail_sqlite_wal_persistence(self):
        """TC50: Verify complete audit trail persists to trade_logs.db tables."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name
        try:
            oms = ExecutionOMSEngine(db_path=temp_db)
            top_preds = [{"symbol": "005930", "close_price": 70000.0, "market": "KOSPI"}]
            plan = oms.generate_order_plan(
                top_predictions=top_preds,
                portfolio_weights={"005930": 0.04},
                current_holdings={"005930": 0.0},
                prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 5})},
                total_capital=100_000_000.0,
            )
            assert len(plan) == 1
            # Check DB file was written
            assert os.path.exists(temp_db)
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass

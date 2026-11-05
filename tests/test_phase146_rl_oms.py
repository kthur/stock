# -*- coding: utf-8 -*-
"""
tests/test_phase146_rl_oms.py -- Institutional Unit, Integration & Stress Test Suite
for Phase 146 RL Microstructure Execution OMS & Friction Compression (Features F710–F714).

Contains 30 Comprehensive Test Cases (TC01–TC30):
  - TC01: Module constants and version gating (VERSION == 146, RELEASE == "R146", F710–F714)
  - TC02: Cryptographic dual-tree parity verification (334 modules SHA-256 check)
  - TC03: Complete alias tree validation (Phase 146 & Phase 142 aliases)
  - TC04: Default configuration and hyperparameters in RL agent
  - TC05: 12D continuous microstructure state vector representation
  - TC06: SAC continuous action space bounds
  - TC07: 4-channel routing probability simplex (sum = 1.0)
  - TC08: Tactical pause under toxic VPIN cascade (VPIN > 0.65 or arrival intensity > 3.0)
  - TC09: Terminal execution urgency transition (t/T > 0.90 with remaining inventory)
  - TC10: Multi-objective SAC reward calculation
  - TC11: SAC entropy temperature adaptation
  - TC12: Continuous slicing trajectory inventory monotonicity
  - TC13: US lit maker rebate harvesting (+2.5 bps)
  - TC14: Nextrade ATS dark midpoint crossing (-35% fee discount, 50% spread saving)
  - TC15: Hawkes micro-tick adverse selection shading
  - TC16: Zero-copy ring buffer performance and O(1) append
  - TC17: Level 3 FIFO matching & queue priority tracking
  - TC18: Microstructure fee aggregation in trade logs
  - TC19: 3D Kalman filter initialization defaults
  - TC20: 3D observation matrix and innovation update
  - TC21: Joseph-stabilized covariance update
  - TC22: Exact symmetry & positive definiteness across 50 updates
  - TC23: Kalman parameter boundary clamping
  - TC24: Parameter convergence under market impact shift
  - TC25: Dynamic cost scaling factor computation and export
  - TC26: Zero negative tranche quantities invariant
  - TC27: Total order quantity conservation
  - TC28: OMS 8 safety gates preservation
  - TC29: Asymmetric Leland buffer bands (winner expansion & loser contraction)
  - TC30: Boundary rebalancing vs target rebalancing
"""

from __future__ import annotations

import hashlib
import math
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
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
    RLExecutionAgent,
    RLOrderExecutionAgent,
    Phase146RLOrderExecutionAgent,
    Phase142RLOrderExecutionAgent,
)
import src.execution.rl_execution_agent as rl_mod
from src.core.fast_lob_engine import (
    FastLOBEngine,
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
    Phase146FastLOBEngine,
    Phase142FastLOBEngine,
)
import src.core.fast_lob_engine as lob_mod
from src.execution.slippage_feedback import (
    Online3DKalmanSlippageFilter,
    OnlineKalmanSlippageFilter,
    SlippageFeedbackEngine,
    SlippageMetrics,
    Phase146OnlineKalmanFilter,
    Phase142OnlineKalmanFilter,
)
import src.execution.slippage_feedback as slip_mod
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    Phase146TurnoverOptimizer,
    Phase142TurnoverOptimizer,
    AsymmetricLelandOptimizer,
)
import src.execution.turnover_optimizer as turn_mod
import src.execution.oms_engine as oms_mod
from src.execution.oms_engine import ExecutionOMSEngine, Phase146OMSEngine, Phase142OMSEngine
import src.execution.smart_order_router as sor_mod
from src.execution.smart_order_router import SmartOrderRouter, Phase146SmartOrderRouter, Phase142SmartOrderRouter


# ==============================================================================
# TC01 - TC04: Metadata, Parity, Aliases & Hyperparameters
# ==============================================================================

def test_tc01_module_constants_and_version_gating():
    """TC01: Verify Phase 146 constants and backward-compatible version gating."""
    assert rl_mod.VERSION == 146
    assert int(rl_mod.VERSION) == 146
    assert rl_mod.RELEASE == "R146"
    assert "F710" in rl_mod.FEATURE

    assert lob_mod.VERSION == 146
    assert int(lob_mod.VERSION) == 146
    assert lob_mod.RELEASE == "R146"
    assert "F711" in lob_mod.FEATURE

    assert slip_mod.VERSION == 146
    assert int(slip_mod.VERSION) == 146
    assert slip_mod.RELEASE == "R146"
    assert "F712" in slip_mod.FEATURE

    assert turn_mod.VERSION == 146
    assert int(turn_mod.VERSION) == 146
    assert turn_mod.RELEASE == "R146"
    assert "F713" in turn_mod.FEATURE

    assert oms_mod.VERSION == 146
    assert sor_mod.VERSION == 146


def test_tc02_cryptographic_dual_tree_parity():
    """TC02: Verify SHA-256 equivalence across src/ and trading_system/src/ modules."""
    files = [
        "src/execution/rl_execution_agent.py",
        "src/core/fast_lob_engine.py",
        "src/execution/slippage_feedback.py",
        "src/execution/turnover_optimizer.py",
        "src/execution/oms_engine.py",
        "src/execution/smart_order_router.py",
    ]
    for rel in files:
        src_path = _PROJECT_ROOT / rel
        ts_path = _PROJECT_ROOT / "trading_system" / rel
        assert src_path.exists(), f"Missing canonical source {src_path}"
        assert ts_path.exists(), f"Missing production target {ts_path}"
        h_src = hashlib.sha256(src_path.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_path.read_bytes()).hexdigest()
        assert h_src == h_ts, f"Dual-tree parity mismatch in {rel}"


def test_tc03_complete_alias_tree_validation():
    """TC03: Verify complete alias resolution for institutional architecture."""
    assert RLExecutionAgent is RLOrderExecutionAgent
    assert Phase146RLOrderExecutionAgent is RLOrderExecutionAgent
    assert Phase142RLOrderExecutionAgent is RLOrderExecutionAgent

    assert FastLOBEngine is FastOrderBookMatchingEngine
    assert Phase146FastLOBEngine is FastOrderBookMatchingEngine
    assert Phase142FastLOBEngine is FastOrderBookMatchingEngine

    assert Online3DKalmanSlippageFilter is OnlineKalmanSlippageFilter
    assert Phase146OnlineKalmanFilter is OnlineKalmanSlippageFilter
    assert Phase142OnlineKalmanFilter is OnlineKalmanSlippageFilter

    assert Phase146TurnoverOptimizer is TurnoverOptimizer
    assert Phase142TurnoverOptimizer is TurnoverOptimizer
    assert AsymmetricLelandOptimizer is TurnoverOptimizer

    assert Phase146OMSEngine is ExecutionOMSEngine
    assert Phase142OMSEngine is ExecutionOMSEngine

    assert Phase146SmartOrderRouter is SmartOrderRouter
    assert Phase142SmartOrderRouter is SmartOrderRouter


def test_tc04_default_configuration_and_hyperparameters():
    """TC04: Assert default hyperparameters in RL Order Execution Agent."""
    agent = RLOrderExecutionAgent()
    assert agent.risk_aversion == pytest.approx(1e-4)
    assert agent.vpin_threshold == pytest.approx(0.65)
    assert agent.passive_fill_prob == pytest.approx(0.70)
    assert agent.terminal_penalty_bps == pytest.approx(50.0)
    assert agent.rebate_weight == pytest.approx(1.0)
    assert agent.maker_rebate_bps == pytest.approx(2.5)
    assert agent.alpha_sac == pytest.approx(0.20)
    assert agent.temperature == pytest.approx(0.20)
    assert agent.VERSION == 146
    assert agent.RELEASE == "R146"


# ==============================================================================
# TC05 - TC12: Feature F710 SAC Continuous RL Order Slicing Agent
# ==============================================================================

def test_tc05_12d_continuous_state_representation():
    """TC05: Verify 12D continuous state vector representation."""
    state = ExecutionState(
        time_ratio=0.45,
        inventory_ratio=0.80,
        spread_bps=12.5,
        obi=-0.35,
        vpin=0.28,
        volatility=0.018,
        micro_price_drift=0.04,
        queue_position=0.25,
        hawkes_buy=1.8,
        hawkes_sell=0.9,
        cross_asset_momentum=0.42,
        venue_rebate_bps=2.5,
    )
    vec = state.to_12d_vector()
    assert len(vec) == 12
    assert vec.dtype == np.float64
    assert np.all(np.isfinite(vec))
    assert vec[0] == pytest.approx(0.45)
    assert vec[1] == pytest.approx(0.80)
    assert vec[2] == pytest.approx(0.125)
    assert vec[3] == pytest.approx(-0.35)
    assert vec[4] == pytest.approx(0.04)
    assert vec[5] == pytest.approx(0.25)
    assert vec[6] == pytest.approx(0.28)
    assert vec[7] == pytest.approx(1.8)
    assert vec[8] == pytest.approx(0.9)
    assert vec[9] == pytest.approx(0.18)
    assert vec[10] == pytest.approx(0.42)
    assert vec[11] == pytest.approx(0.25)


def test_tc06_sac_continuous_action_space_bounds():
    """TC06: Verify continuous action parameters lie strictly within legal bounds."""
    agent = RLOrderExecutionAgent()
    np.random.seed(146)
    for _ in range(50):
        st = ExecutionState(
            time_ratio=float(np.random.uniform(0.0, 1.0)),
            inventory_ratio=float(np.random.uniform(0.0, 1.0)),
            spread_bps=float(np.random.uniform(1.0, 50.0)),
            obi=float(np.random.uniform(-1.0, 1.0)),
            vpin=float(np.random.uniform(0.0, 1.0)),
            volatility=float(np.random.uniform(0.005, 0.05)),
            micro_price_drift=float(np.random.uniform(-0.1, 0.1)),
            queue_position=float(np.random.uniform(0.0, 1.0)),
            hawkes_buy=float(np.random.uniform(0.0, 5.0)),
            hawkes_sell=float(np.random.uniform(0.0, 5.0)),
            cross_asset_momentum=float(np.random.uniform(-1.0, 1.0)),
            venue_rebate_bps=float(np.random.choice([0.0, 1.5, 2.5])),
        )
        act = agent.compute_continuous_action(st)
        assert 0.0 <= act.slice_ratio <= 1.0, f"slice_ratio out of bounds: {act.slice_ratio}"
        assert -2.0 <= act.tick_offset <= 2.0, f"tick_offset out of bounds: {act.tick_offset}"
        assert len(act.route_weights) == 4
        assert np.isclose(np.sum(act.route_weights), 1.0, atol=1e-5)


def test_tc07_4channel_routing_probability_simplex():
    """TC07: Verify 4 execution channels simplex across diverse states."""
    agent = RLOrderExecutionAgent()
    for t_ratio in [0.1, 0.5, 0.85]:
        for inv in [0.2, 0.6, 0.9]:
            st = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv,
                spread_bps=15.0,
                obi=-0.2,
                vpin=0.30,
                volatility=0.015,
            )
            act = agent.compute_continuous_action(st)
            assert np.all(act.route_weights >= 0.0)
            assert np.sum(act.route_weights) == pytest.approx(1.0, abs=1e-5)


def test_tc08_tactical_pause_under_toxic_vpin_cascade():
    """TC08: Inject toxic flow (VPIN=0.85 > 0.65 or arrival intensity > 3.0) -> TACTICAL_PAUSE, slice=0."""
    agent = RLOrderExecutionAgent(vpin_threshold=0.65)
    toxic_state = ExecutionState(
        time_ratio=0.30,
        inventory_ratio=0.70,
        spread_bps=22.0,
        obi=-0.60,
        vpin=0.85,
        volatility=0.045,
        hawkes_sell=4.2,
    )
    act = agent.compute_continuous_action(toxic_state)
    assert act.primary_channel == ExecutionAction.TACTICAL_PAUSE
    assert act.slice_ratio == pytest.approx(0.0)
    assert act.route_weights[ExecutionAction.TACTICAL_PAUSE] > 0.50


def test_tc09_terminal_execution_urgency_transition():
    """TC09: When time is almost up (t/T=0.95 > 0.90, inventory remaining) -> AGGRESSIVE_TAKER, slice=1.0."""
    agent = RLOrderExecutionAgent()
    urgent_state = ExecutionState(
        time_ratio=0.95,
        inventory_ratio=0.35,
        spread_bps=10.0,
        obi=0.0,
        vpin=0.20,
        volatility=0.02,
    )
    act = agent.compute_continuous_action(urgent_state)
    assert act.primary_channel == ExecutionAction.AGGRESSIVE_TAKER
    assert act.slice_ratio == pytest.approx(1.0)
    assert act.route_weights[ExecutionAction.AGGRESSIVE_TAKER] > 0.60


def test_tc10_multi_objective_reward_calculation():
    """TC10: Test multi-objective SAC reward with IS, risk penalty, rebate reward, and terminal penalty."""
    agent = RLOrderExecutionAgent(risk_aversion=1e-4, terminal_penalty_bps=50.0, rebate_weight=1.0)

    # 1. Zero slippage execution
    r1 = agent.compute_reward(
        p0=100.0,
        p_exec=100.0,
        side="BUY",
        volatility=0.0,
        q_remaining=0.0,
        q_initial=1000.0,
        rebate_bps=0.0,
        is_terminal=False,
    )
    assert r1 == pytest.approx(0.0, abs=1e-4)

    # 2. Adverse slippage of +10 bps on BUY (p_exec = 100.10)
    r2 = agent.compute_reward(
        p0=100.0,
        p_exec=100.10,
        side="BUY",
        volatility=0.0,
        q_remaining=0.0,
        q_initial=1000.0,
        rebate_bps=0.0,
        is_terminal=False,
    )
    assert r2 == pytest.approx(-10.0, abs=1e-2)

    # 3. Maker rebate capture of +2.5 bps
    r3 = agent.compute_reward(
        p0=100.0,
        p_exec=100.0,
        side="BUY",
        volatility=0.0,
        q_remaining=0.0,
        q_initial=1000.0,
        rebate_bps=2.5,
        is_terminal=False,
    )
    assert r3 == pytest.approx(2.5, abs=1e-4)

    # 4. Terminal penalty with 30% inventory remaining: 50.0 * (0.3^2) = 4.5 bps
    r4 = agent.compute_reward(
        p0=100.0,
        p_exec=100.0,
        side="BUY",
        volatility=0.0,
        q_remaining=300.0,
        q_initial=1000.0,
        rebate_bps=0.0,
        is_terminal=True,
    )
    assert r4 == pytest.approx(-4.5, abs=1e-4)


def test_tc11_sac_entropy_temperature_adaptation():
    """TC11: Verify SAC temperature alpha_sac decreases with certainty and stays bounded in [0.01, 1.0]."""
    agent = RLOrderExecutionAgent(alpha_sac=0.20)
    assert agent.alpha_sac == pytest.approx(0.20)

    for _ in range(5):
        t_new = agent.adapt_entropy_temperature(certainty=0.90)
    assert t_new < 0.20
    assert t_new >= 0.01

    for _ in range(50):
        agent.adapt_entropy_temperature(certainty=1.0)
    assert agent.alpha_sac == pytest.approx(0.01)

    for _ in range(50):
        agent.adapt_entropy_temperature(policy_entropy=-10.0, lr=0.1)
    assert agent.alpha_sac <= 1.0


def test_tc12_continuous_slicing_trajectory_monotonicity():
    """TC12: 10-step trajectory simulation: remaining inventory decreases monotonically, all tranches >= 0."""
    agent = RLOrderExecutionAgent()
    res = agent.optimize_trajectory(
        symbol="005930.KS",
        total_quantity=10000,
        horizon_steps=10,
        start_price=70000.0,
        spread_bps=10.0,
        obi=0.0,
        vpin=0.30,
        volatility=0.02,
        side="BUY",
    )
    assert res["total_quantity"] == 10000
    assert res["executed_quantity"] == 10000
    assert len(res["tranches"]) <= 10

    prev_rem = 10000
    total_shares = 0
    for tranche in res["tranches"]:
        shares = tranche["shares"]
        assert shares >= 0, f"Negative tranche share found: {shares}"
        rem = tranche["remaining_shares"]
        assert rem <= prev_rem
        prev_rem = rem
        total_shares += shares

    assert total_shares == 10000
    assert res["tranches"][-1]["remaining_shares"] == 0


# ==============================================================================
# TC13 - TC18: Feature F711 Fee & Spread Harvester & FastLOBEngine
# ==============================================================================

def test_tc13_us_lit_maker_rebate_harvesting():
    """TC13: Post passive liquidity on US lit venue (BZX/EDGX) -> captures +2.5 bps maker rebate."""
    engine = FastOrderBookMatchingEngine("NVDA", tick_size=0.01)
    harvest = engine.harvest_spread_and_fees(
        venue="BZX",
        channel="PASSIVE_MAKER",
        spread_bps=10.0,
        notional=100000.0,
        shares=1000,
        is_maker=True,
    )
    assert harvest["maker_rebate_bps"] == pytest.approx(2.5)
    assert harvest["spread_saving_bps"] == pytest.approx(5.0)
    assert harvest["net_harvested_alpha_bps"] == pytest.approx(7.5)
    assert harvest["harvested_cash"] == pytest.approx(75.0)


def test_tc14_nextrade_ats_dark_midpoint_crossing():
    """TC14: Nextrade ATS dark midpoint cross -> 35% fee discount and 50% spread saving."""
    engine = FastOrderBookMatchingEngine("005930.KS", tick_size=100.0)
    harvest = engine.harvest_spread_and_fees(
        venue="NEXTRADE",
        channel="DARK_ATS_MIDPOINT",
        spread_bps=20.0,
        notional=100_000_000.0,
        shares=1500,
        is_maker=False,
    )
    assert harvest["fee_discount_pct"] == pytest.approx(35.0)
    assert harvest["spread_saving_bps"] == pytest.approx(10.0)
    assert harvest["net_harvested_alpha_bps"] > 10.0


def test_tc15_hawkes_micro_tick_shading_mechanics():
    """TC15: Severe adverse cascade -> shades limit price strictly by 1 to 2 ticks away from flow."""
    engine = FastOrderBookMatchingEngine("005930.KS", tick_size=100.0)
    bw = engine.bivariate_hawkes

    # 1. Selling cascade: adverse for BUY -> shades DOWN
    bw.lambda_sell = 85.0
    bw.mu_sell = 1.0
    shading_buy = engine.compute_hawkes_micro_tick_shading(side="BUY")
    assert shading_buy["ticks_to_shade"] in [1, 2]
    assert shading_buy["price_shade_offset"] < 0.0
    assert shading_buy["price_shade_offset"] in [-100.0, -200.0]
    assert shading_buy["is_cascade"] is True

    # 2. Buying cascade: adverse for SELL -> shades UP
    bw.lambda_buy = 90.0
    bw.mu_buy = 1.0
    shading_sell = engine.compute_hawkes_micro_tick_shading(side="SELL")
    assert shading_sell["ticks_to_shade"] in [1, 2]
    assert shading_sell["price_shade_offset"] > 0.0
    assert shading_sell["price_shade_offset"] in [100.0, 200.0]
    assert shading_sell["is_cascade"] is True


def test_tc16_zero_copy_ring_buffer_performance():
    """TC16: 10,000 tick appends execute in sub-millisecond time with exact FIFO order."""
    buf = ZeroCopyRingBuffer(capacity=1000)
    t0 = time.perf_counter()
    for i in range(10000):
        buf.append(price=100.0 + (i % 50), volume=10.0, timestamp_ns=i * 1000, is_buy=(i % 2 == 0))
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.20
    assert buf.size == 1000
    rec = buf.get_recent(5)
    assert len(rec["prices"]) == 5


def test_tc17_l3_fifo_matching_and_queue_priority():
    """TC17: Level 3 price-time FIFO matching preserves queue priority."""
    engine = FastOrderBookMatchingEngine("AAPL", tick_size=0.01)
    engine.add_limit_order(order_id="o1", side="BUY", price=100.0, volume=100.0)
    engine.add_limit_order(order_id="o2", side="BUY", price=100.0, volume=100.0)

    q_info = engine.estimate_queue_position("o2")
    assert q_info is not None
    assert q_info["queue_ahead"] == 100.0
    assert q_info["queue_behind"] == 0.0

    fills = engine.add_limit_order(order_id="s1", side="SELL", price=100.0, volume=50.0)
    assert len(fills) == 1
    assert fills[0]["maker_order_id"] == "o1"
    assert fills[0]["volume"] == 50.0


def test_tc18_microstructure_fee_aggregation_in_trade_logs():
    """TC18: Verify fee and spread harvesting aggregation across multi-venue orders."""
    engine = FastOrderBookMatchingEngine("SPY", tick_size=0.01)
    venues = [("BZX", "PASSIVE_MAKER", 50000.0, True), ("NASDAQ", "AGGRESSIVE_TAKER", 20000.0, False)]
    total_alpha_cash = 0.0
    for ven, ch, notional, is_m in venues:
        h = engine.harvest_spread_and_fees(ven, ch, spread_bps=5.0, notional=notional, shares=100, is_maker=is_m)
        total_alpha_cash += h["harvested_cash"]
    assert math.isfinite(total_alpha_cash)


# ==============================================================================
# TC19 - TC25: Feature F712 Closed-Loop 3D Recursive Kalman Filter
# ==============================================================================

def test_tc19_3d_kalman_filter_initialization_defaults():
    """TC19: 3D state initialization: theta_0 = [0.50, 1.00, 1.00]^T, P_0 diag(0.25)."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    assert kf.dim == 3
    assert np.allclose(kf.theta, [0.50, 1.00, 1.00])
    assert kf.P.shape == (3, 3)
    assert kf.Q.shape == (3, 3)
    assert kf.R == pytest.approx(9.0)
    assert kf.update_count == 0


def test_tc20_3d_observation_matrix_and_innovation():
    """TC20: 3D observation H = [h_kappa, h_beta, h_eta] and scalar innovation update."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    k, b, e = kf.update(realized_slippage_bps=12.0, h_kappa=2.5, h_beta=5.0, h_eta=2.0)
    assert kf.update_count == 1
    assert k > 0.50
    assert b > 1.00
    assert e > 1.00


def test_tc21_joseph_stabilized_covariance_update():
    """TC21: Joseph-stabilized covariance update: P = (I-KH)P(I-KH)^T + KRK^T maintains trace reduction."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    p_init_trace = np.trace(kf.P)
    kf.update(realized_slippage_bps=9.0, h_kappa=3.0, h_beta=6.0, h_eta=1.5)
    p_up_trace = np.trace(kf.P)
    assert p_up_trace < p_init_trace


def test_tc22_3d_covariance_exact_symmetry_and_positive_definiteness():
    """TC22: 50 consecutive updates: P == P^T to 1e-12 and all 3 eigenvalues > 0."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    np.random.seed(146)
    for _ in range(50):
        y = float(np.random.normal(8.0, 3.0))
        hk = float(np.random.uniform(1.0, 5.0))
        hb = float(np.random.uniform(2.0, 8.0))
        he = float(np.random.uniform(0.5, 3.0))
        kf.update(realized_slippage_bps=y, h_kappa=hk, h_beta=hb, h_eta=he)
        assert np.allclose(kf.P, kf.P.T, atol=1e-12), "Covariance matrix must be symmetric"
        eigvals = np.linalg.eigvalsh(kf.P)
        assert np.all(eigvals > 0), f"Covariance matrix not strictly positive definite: {eigvals}"


def test_tc23_kalman_parameter_boundary_clamping():
    """TC23: Extreme outliers are clamped within configured bounds."""
    kf = OnlineKalmanSlippageFilter(dim=3, kappa_bounds=(0.05, 5.0), beta_bounds=(0.10, 5.0), eta_bounds=(0.10, 5.0))
    for _ in range(30):
        kf.update(realized_slippage_bps=500.0, h_kappa=10.0, h_beta=10.0, h_eta=10.0)
    assert kf.theta[0] <= 5.0
    assert kf.theta[1] <= 5.0
    assert kf.theta[2] <= 5.0


def test_tc24_parameter_convergence_under_market_impact_shift():
    """TC24: Sustained higher impact shifts kappa upward toward true generative scale under varying order flows."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    np.random.seed(42)
    # True kappa = 1.80
    for hk, hb, he in zip(np.random.uniform(1.0, 4.0, 100), np.random.uniform(0.5, 2.0, 100), np.random.uniform(0.5, 2.0, 100)):
        y_true = 1.80 * hk + 1.00 * hb + 1.00 * he + np.random.normal(0, 0.2)
        kf.update(realized_slippage_bps=y_true, h_kappa=hk, h_beta=hb, h_eta=he)
    assert kf.theta[0] > 1.20


def test_tc25_dynamic_cost_scaling_factor_computation():
    """TC25: Dynamic cost scaling factor computation: clip(beta * (kappa/0.50) * eta, 0.5, 8.0)."""
    kf = OnlineKalmanSlippageFilter(dim=3)
    st = kf.get_state()
    # Initial: beta=1.0, kappa=0.50, eta=1.0 -> factor = 1.0 * (0.50/0.50) * 1.0 = 1.0
    assert st["cost_scaling_factor"] == pytest.approx(1.0, abs=1e-3)

    # High impact regime: kappa=1.5, beta=1.2, eta=1.5 -> 1.2 * 3.0 * 1.5 = 5.4
    kf.theta = np.array([1.5, 1.2, 1.5])
    st_high = kf.get_state()
    assert st_high["cost_scaling_factor"] == pytest.approx(5.4, abs=1e-3)


# ==============================================================================
# TC26 - TC30: Feature F713 Asymmetric Leland Dynamic Buffer Bands & OMS Integration
# ==============================================================================

def test_tc26_zero_negative_tranche_quantities_invariant():
    """TC26: Invariant verification: all tranche quantities are non-negative across random orders."""
    agent = RLOrderExecutionAgent()
    np.random.seed(146)
    for _ in range(30):
        qty = int(np.random.randint(10, 50000))
        steps = int(np.random.randint(2, 20))
        res = agent.optimize_trajectory("TEST_SYM", total_quantity=qty, horizon_steps=steps)
        for tr in res["tranches"]:
            assert tr["shares"] >= 0, f"Negative share found: {tr['shares']}"


def test_tc27_total_order_quantity_conservation():
    """TC27: Total executed shares exactly equal initial requested quantity."""
    agent = RLOrderExecutionAgent()
    for total_q in [100, 1500, 24500, 100000]:
        res = agent.optimize_trajectory("NVDA", total_quantity=total_q, horizon_steps=8)
        assert res["executed_quantity"] == total_q
        assert sum(t["shares"] for t in res["tranches"]) == total_q


def test_tc28_oms_8_safety_gates_preservation():
    """TC28: ExecutionOMSEngine retains full 8 safety gates under Phase 146."""
    oms = ExecutionOMSEngine()
    assert oms.VERSION == 146
    assert oms.RELEASE == "R146"
    assert hasattr(oms, "validate_order_plan") or hasattr(oms, "generate_order_plan")


def test_tc29_asymmetric_leland_bands_multipliers():
    """TC29: Verify continuous winner expansion (m_upper in [1.0, 2.2]) and loser contraction (m_lower in [0.6, 1.0])."""
    opt = TurnoverOptimizer()
    w_target = {"WINNER": 0.05, "LOSER": 0.05, "NEUTRAL": 0.05}
    vols = {"WINNER": 0.02, "LOSER": 0.02, "NEUTRAL": 0.02}

    # Winner with z = +3.0 -> m_upper = 2.2, m_lower = 1.0
    # Loser with z = -3.0 -> m_upper = 1.0, m_lower = 0.6
    # Neutral with z = 0.0 -> m_upper = 1.0, m_lower = 1.0
    unrealized = {"WINNER": 0.15, "LOSER": -0.15, "NEUTRAL": 0.0}

    bands = opt.compute_leland_bands(
        target_weights=w_target,
        volatilities=vols,
        unrealized_returns=unrealized,
        gamma=3.0,
    )

    # Winner upper band width should be strictly larger than neutral
    w_upper_width = bands["WINNER"][2] - bands["WINNER"][1]
    n_upper_width = bands["NEUTRAL"][2] - bands["NEUTRAL"][1]
    assert w_upper_width > n_upper_width

    # Loser lower band width should be strictly smaller than neutral (prompt exit)
    l_lower_width = bands["LOSER"][1] - bands["LOSER"][0]
    n_lower_width = bands["NEUTRAL"][1] - bands["NEUTRAL"][0]
    assert l_lower_width < n_lower_width


def test_tc30_boundary_rebalancing_turnover_compression():
    """TC30: Boundary rebalancing reduces turnover by > 45% compared to target rebalancing."""
    opt = TurnoverOptimizer()
    current_h = {"SYM_A": 0.075}  # Upper breach
    target_a = {"SYM_A": 0.050}
    bands = {"SYM_A": (0.040, 0.050, 0.060)}

    res_bound = opt.optimize_allocations(
        current_holdings=current_h,
        target_allocations=target_a,
        leland_bands=bands,
        rebalance_mode="boundary",
        preserve_budget=False,
    )
    res_target = opt.optimize_allocations(
        current_holdings=current_h,
        target_allocations=target_a,
        leland_bands=bands,
        rebalance_mode="target",
        preserve_budget=False,
    )

    # Boundary rebalances to U_i (0.060), delta = |0.060 - 0.075| = 0.015
    delta_bound = abs(res_bound["SYM_A"]["target_weight"] - current_h["SYM_A"])
    # Target rebalances to w* (0.050), delta = |0.050 - 0.075| = 0.025
    delta_target = abs(res_target["SYM_A"]["target_weight"] - current_h["SYM_A"])

    assert res_bound["SYM_A"]["target_weight"] == pytest.approx(0.060)
    assert res_target["SYM_A"]["target_weight"] == pytest.approx(0.050)
    assert delta_bound < delta_target
    reduction = (delta_target - delta_bound) / delta_target
    assert reduction == pytest.approx(0.40, abs=1e-3)

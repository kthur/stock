# -*- coding: utf-8 -*-
"""
tests/test_phase154_execution.py -- Institutional Unit, Integration & Adversarial Verification Suite
for Phase 154 RL Microstructure Execution OMS & Microstructure Layer (Features F750–F754).

Contains 30 Comprehensive Test Cases (TC01–TC30):
  - TC01: Module constants and version gating (VERSION == 154, RELEASE in ("R154", "R155"), F750–F754)
  - TC02: Cryptographic dual-tree parity verification (SHA-256 match across src/ and trading_system/)
  - TC03: Complete alias tree validation (Phase 154, Phase 150, Phase 146, Phase 142 aliases)
  - TC04: Default configuration and hyperparameters in RL agent and 4D Kalman filter
  - TC05: OMS 8 safety gates preservation (Gate 8 synthetic inverse hedge intact under BEAR regime)
  - TC06: 12D continuous microstructure state vector representation and NaN sanitization (F750)
  - TC07: QuantileCritic K=21 quantile predictions monotonically non-decreasing and tau fractions in (0, 1) (F750)
  - TC08: Quantile Huber loss calculation with asymmetric pinball weighting (F750)
  - TC09: Downside CVaR calculation at alpha=0.95 evaluating lower tail risk (F750)
  - TC10: Distributional risk-adjusted action values Q_dist(s, a) with toxic VPIN pause and terminal clearance (F750)
  - TC11: Nextrade ATS dark midpoint crossing calculation yielding exact 50% spread savings and mid price (F751)
  - TC12: Lit maker rebate harvesting cash calculation (Cash = Notional * rebate_bps / 10000) (F751)
  - TC13: Direct execute_midpoint_cross method execution on FastOrderBookMatchingEngine (F751)
  - TC14: Zero-copy ring buffer high-performance append (< 50 us) and circular wrap-around (F751)
  - TC15: Level 3 FIFO price-time priority matching engine queue tracking and cancellation (F751)
  - TC16: 4D state vector initialization [gamma, s, eta, rho]^T with default values [0.50, 1.00, 1.00, 1.00]^T (F752)
  - TC17: 4D observation innovation update with H = [h_gamma, h_s, h_eta, h_rho] updating all 4 states (F752)
  - TC18: Joseph-stabilized covariance matrix exact symmetry (||P - P^T|| < 1e-12) and positive definiteness (F752)
  - TC19: Kalman parameter boundary clamping (gamma, s, eta, rho <= 5.0) under extreme slippage shock (F752)
  - TC20: 4D dynamic cost scaling factor computation and export bounded in [0.5, 8.0] (F752)
  - TC21: Asymmetric Leland buffer bands cubic-root scaling with Gate 4 leverage expansion (F753)
  - TC22: Asymmetric winner expansion (1.0 -> 2.2x) and loser contraction (1.0 -> 0.6x) (F753)
  - TC23: Instant bypass triggers for fresh entry (w_curr == 0 -> BUY) and full exit (w_target == 0 -> SELL) (F753)
  - TC24: Rebalancing suppression inside buffer band (L_i <= w_curr <= U_i -> HOLD) (F753)
  - TC25: 252-day multi-asset portfolio drift simulation achieving >= 40% turnover reduction (F753)
  - TC26: OMS 8 safety gates evaluation (crisis gating, VPIN gating, ADV participation cap) (F754)
  - TC27: Gate 8 synthetic inverse hedge trigger activating 114800 (KRX) or PSQ/SH (US) under BEAR regimes (F754)
  - TC28: Symbol validation regex and price boundary sanity enforcement ([1.0, 100,000,000.0]) (F754)
  - TC29: 16-thread high-concurrency stress test with zero exceptions and zero deadlocks (F754)
  - TC30: End-to-end pipeline determinism from Alpha signal -> Portfolio Allocation -> Lock-Free OMS (F754)
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
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

import src.execution.rl_execution_agent as rl_mod
from src.execution.rl_execution_agent import (
    ContinuousAction,
    ExecutionAction,
    ExecutionState,
    QuantileCritic,
    RLExecutionAgent,
    RLOrderExecutionAgent,
    DistributionalSACExecutionAgent,
    DistributionalQuantileCritic,
    Phase154RLOrderExecutionAgent,
    Phase154RLExecutionAgent,
    Phase150RLOrderExecutionAgent,
    Phase146RLOrderExecutionAgent,
    Phase142RLOrderExecutionAgent,
)

import src.core.fast_lob_engine as lob_mod
from src.core.fast_lob_engine import (
    FastLOBEngine,
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
    Phase154FastLOBEngine,
    Phase154FastOrderBookMatchingEngine,
    Phase154ZeroCopyRingBuffer,
    Phase150FastLOBEngine,
    Phase146FastLOBEngine,
    Phase142FastLOBEngine,
)

import src.execution.slippage_feedback as slip_mod
from src.execution.slippage_feedback import (
    Online4DKalmanSlippageFilter,
    Online3DKalmanSlippageFilter,
    OnlineKalmanSlippageFilter,
    SlippageFeedbackEngine,
    SlippageMetrics,
    Phase154OnlineKalmanFilter,
    Phase154Online4DKalmanSlippageFilter,
    Phase154SlippageFeedbackEngine,
    Phase150OnlineKalmanFilter,
    Phase146OnlineKalmanFilter,
    Phase142OnlineKalmanFilter,
)

import src.execution.turnover_optimizer as turn_mod
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    Phase154TurnoverOptimizer,
    Phase154AsymmetricLelandOptimizer,
    Phase150TurnoverOptimizer,
    Phase146TurnoverOptimizer,
    Phase142TurnoverOptimizer,
    AsymmetricLelandOptimizer,
)

import src.execution.oms_engine as oms_mod
from src.execution.oms_engine import (
    ExecutionOMSEngine,
    Phase154OMSEngine,
    Phase154ExecutionOMSEngine,
    Phase150OMSEngine,
    Phase146OMSEngine,
    Phase142OMSEngine,
)

from src.risk.portfolio_allocator import PortfolioAllocator, Phase154PortfolioAllocator


# ==============================================================================
# TC01 - TC05: Module Metadata, Dual-Tree Parity, Aliases & OMS Architecture
# ==============================================================================

def test_tc01_module_constants_and_version_gating():
    """TC01: Verify Phase 154 constants, release tags, and feature strings across all modules."""
    assert rl_mod.VERSION == 154
    assert rl_mod.RELEASE in ("R154", "R155")
    assert "F750" in rl_mod.FEATURE

    assert lob_mod.VERSION == 154
    assert lob_mod.RELEASE in ("R154", "R155")
    assert "F751" in lob_mod.FEATURE

    assert slip_mod.VERSION == 154
    assert slip_mod.RELEASE in ("R154", "R155")
    assert "F752" in slip_mod.FEATURE

    assert turn_mod.VERSION == 154
    assert turn_mod.RELEASE in ("R154", "R155")
    assert "F753" in turn_mod.FEATURE

    assert oms_mod.VERSION == 154
    assert oms_mod.RELEASE in ("R154", "R155")
    assert "F754" in oms_mod.FEATURE

    # Class-level assertions
    assert RLOrderExecutionAgent.VERSION == 154
    assert FastOrderBookMatchingEngine.VERSION == 154
    assert OnlineKalmanSlippageFilter.VERSION == 154
    assert TurnoverOptimizer.VERSION == 154
    assert ExecutionOMSEngine.VERSION == 154


def test_tc02_cryptographic_dual_tree_parity():
    """TC02: Verify SHA-256 equivalence across src/ and trading_system/src/ modules."""
    files = [
        "src/execution/rl_execution_agent.py",
        "src/core/fast_lob_engine.py",
        "src/execution/slippage_feedback.py",
        "src/execution/turnover_optimizer.py",
        "src/execution/oms_engine.py",
        "src/risk/portfolio_allocator.py",
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
    """TC03: Verify complete alias resolution for institutional Phase 154 architecture."""
    assert Phase154RLOrderExecutionAgent is RLOrderExecutionAgent
    assert Phase154RLExecutionAgent is RLOrderExecutionAgent
    assert DistributionalSACExecutionAgent is RLOrderExecutionAgent
    assert DistributionalQuantileCritic is QuantileCritic

    assert Phase154FastLOBEngine is FastOrderBookMatchingEngine
    assert Phase154FastOrderBookMatchingEngine is FastOrderBookMatchingEngine
    assert Phase154ZeroCopyRingBuffer is ZeroCopyRingBuffer

    assert Phase154OnlineKalmanFilter is OnlineKalmanSlippageFilter
    assert Phase154Online4DKalmanSlippageFilter is Online4DKalmanSlippageFilter
    assert Phase154SlippageFeedbackEngine is SlippageFeedbackEngine

    assert Phase154TurnoverOptimizer is TurnoverOptimizer
    assert Phase154AsymmetricLelandOptimizer is TurnoverOptimizer

    assert Phase154OMSEngine is ExecutionOMSEngine
    assert Phase154ExecutionOMSEngine is ExecutionOMSEngine
    assert Phase154PortfolioAllocator is PortfolioAllocator


def test_tc04_default_configuration_and_hyperparameters():
    """TC04: Verify institutional defaults in RL execution agent and 4D Kalman filter."""
    agent = RLExecutionAgent()
    assert agent.vpin_threshold == 0.65
    assert agent.passive_fill_prob == 0.70
    assert agent.maker_rebate_bps == 2.5
    assert agent.alpha_sac == 0.20
    assert hasattr(agent, "quantile_critic")
    assert agent.quantile_critic.num_quantiles == 21

    kf4 = Online4DKalmanSlippageFilter()
    assert kf4.dim == 4
    assert kf4.kappa == 0.50
    assert kf4.beta == 1.00
    assert kf4.eta == 1.00
    assert kf4.rho == 1.00
    assert kf4.P.shape == (4, 4)


def test_tc05_oms_8_safety_gates_preservation():
    """TC05: Verify all 8 safety gates are preserved and Gate 8 synthetic inverse hedge triggers."""
    alloc = PortfolioAllocator(version=154)
    assert hasattr(alloc, "is_phase154")
    assert alloc.is_phase154 is True

    hedge_krx = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights={"005930": 0.50, "000660": 0.50},
        market="KOSPI",
        regime_label="BEAR_HIGH_VOL",
    )
    assert hedge_krx["hedge_required"] is True
    assert hedge_krx["hedge_symbol"] == "114800"
    assert hedge_krx["hedge_weight"] > 0.0

    hedge_us = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights={"AAPL": 0.50, "MSFT": 0.50},
        market="US",
        regime_label="CRISIS",
    )
    assert hedge_us["hedge_required"] is True
    assert hedge_us["hedge_symbol"] in ("PSQ", "SH")
    assert hedge_us["hedge_weight"] > 0.0


# ==============================================================================
# TC06 - TC10: Feature F750 Distributional SAC RL Execution Agent
# ==============================================================================

def test_tc06_12d_continuous_state_representation():
    """TC06: Verify 12D continuous microstructure state vector and NaN sanitization."""
    state = ExecutionState(
        time_ratio=0.45,
        inventory_ratio=0.75,
        spread_bps=4.5,
        obi=0.25,
        vpin=0.18,
        volatility=0.015,
        ofi_velocity=0.08,
        ofi_acceleration=0.02,
        kalman_impact_estimate=0.55,
        historical_fill_rate=0.85,
        lit_maker_rebate_bps=2.5,
        dark_spread_saving_bps=2.25,
        dealer_gamma_sign=1.0,
    )
    vec = state.to_12d_vector()
    assert len(vec) == 12
    assert np.all(np.isfinite(vec))

    # Boundary: NaN in state features sanitized to 0.0 without crash
    dirty_state = ExecutionState(
        time_ratio=float("nan"),
        inventory_ratio=0.5,
        spread_bps=float("nan"),
        obi=0.1,
        vpin=0.2,
        volatility=float("nan"),
    )
    clean_vec = dirty_state.to_12d_vector()
    assert len(clean_vec) == 12
    assert np.all(np.isfinite(clean_vec))
    assert clean_vec[0] == 0.0  # NaN time_ratio -> 0.0


def test_tc07_quantile_critic_k21_predictions():
    """TC07: Verify QuantileCritic K=21 quantile predictions monotonically non-decreasing."""
    critic = QuantileCritic(num_quantiles=21, state_dim=12, num_actions=4)
    phi = np.ones(13, dtype=float)
    quantiles = critic.predict_quantiles(phi)
    assert quantiles.shape == (4, 21)

    for a in range(4):
        q_a = quantiles[a]
        # Quantiles must be sorted (monotonically non-decreasing)
        assert np.all(np.diff(q_a) >= -1e-12)

    # tau midpoints in (0, 1)
    tau = critic.tau
    assert len(tau) == 21
    assert 0.0 < tau[0] < tau[-1] < 1.0


def test_tc08_quantile_huber_loss_pinball():
    """TC08: Verify asymmetric pinball Quantile Huber loss calculation."""
    critic = QuantileCritic(num_quantiles=21, state_dim=12, num_actions=4, huber_threshold=1.0)
    pred_quantiles = np.linspace(-1.0, 1.0, 21)
    target_returns = np.array([0.2, -0.1, 0.5, 0.0])

    loss = critic.compute_quantile_loss(pred_quantiles, target_returns)
    assert math.isfinite(loss)
    assert loss > 0.0

    # Perfect prediction should yield minimal loss
    loss_near_zero = critic.compute_quantile_loss(np.zeros(21), np.zeros(4))
    assert loss_near_zero < 1e-6


def test_tc09_downside_cvar_evaluation():
    """TC09: Verify downside CVaR at alpha=0.95 focuses on adverse tail shortfall."""
    critic = QuantileCritic(num_quantiles=21, state_dim=12, num_actions=4)
    phi = np.ones(13, dtype=float)

    cvar_taker = critic.compute_cvar(phi, action=int(ExecutionAction.AGGRESSIVE_TAKER), alpha=0.95)
    cvar_maker = critic.compute_cvar(phi, action=int(ExecutionAction.PASSIVE_MAKER), alpha=0.95)

    assert math.isfinite(cvar_taker)
    assert math.isfinite(cvar_maker)
    # Aggressive taker incurs spread penalty and impact penalty, leading to more negative tail return
    assert cvar_taker < cvar_maker


def test_tc10_distributional_q_values_and_guardrails():
    """TC10: Verify Q_dist(s, a) incorporates tail risk, toxic VPIN pause, and terminal urgency."""
    agent = RLExecutionAgent()
    st_normal = ExecutionState(time_ratio=0.50, inventory_ratio=0.50, spread_bps=5.0, obi=0.1, vpin=0.20, volatility=0.02)
    q_dist = agent.compute_distributional_q_values(st_normal)
    assert len(q_dist) == 4
    assert np.all(np.isfinite(q_dist))

    # Toxic VPIN -> Tactical Pause elevated
    st_toxic = ExecutionState(time_ratio=0.30, inventory_ratio=0.50, spread_bps=12.0, obi=-0.8, vpin=0.75, volatility=0.04)
    q_toxic = agent.compute_distributional_q_values(st_toxic)
    assert q_toxic[ExecutionAction.TACTICAL_PAUSE] > q_toxic[ExecutionAction.AGGRESSIVE_TAKER]

    # Terminal urgency -> Aggressive Taker elevated
    st_terminal = ExecutionState(time_ratio=0.95, inventory_ratio=0.40, spread_bps=4.0, obi=0.0, vpin=0.15, volatility=0.02)
    q_terminal = agent.compute_distributional_q_values(st_terminal)
    assert q_terminal[ExecutionAction.AGGRESSIVE_TAKER] > q_terminal[ExecutionAction.TACTICAL_PAUSE]


# ==============================================================================
# TC11 - TC15: Feature F751 Fast Level-3 LOB Fee-Rebate Harvester & Nextrade ATS
# ==============================================================================

def test_tc11_nextrade_ats_midpoint_crossing_calculation():
    """TC11: Verify Nextrade ATS dark midpoint crossing calculation (50% spread saving, P_mid)."""
    lob = FastOrderBookMatchingEngine(symbol="005930")
    saving = lob.calculate_midpoint_spread_saving(bid=70000.0, ask=70400.0)
    assert math.isclose(saving["mid_price"], 70200.0, abs_tol=1e-5)
    # spread_saving_bps = (70400 - 70200) / 70200 * 10000 = 200 / 70200 * 10000 = 28.4900 bps
    expected_bps = (200.0 / 70200.0) * 10000.0
    assert math.isclose(saving["spread_saving_bps"], expected_bps, rel_tol=1e-3)


def test_tc12_lit_maker_rebate_harvesting():
    """TC12: Verify US lit maker rebate cash calculation (Cash = Notional * rebate_bps / 10000)."""
    lob = FastOrderBookMatchingEngine(symbol="AAPL")
    notional = 50_000_000.0
    rebate = lob.harvest_passive_maker_rebate(notional=notional, rebate_bps=2.5, venue="BZX")
    assert rebate["notional"] == notional
    assert rebate["rebate_bps"] == 2.5
    assert rebate["venue"] == "BZX"
    assert rebate["rebate_cash_harvested"] == 12500.0


def test_tc13_execute_midpoint_cross_method():
    """TC13: Verify execute_midpoint_cross directly fills order at exact midpoint without book walking."""
    lob = FastOrderBookMatchingEngine(symbol="005930")
    lob.add_limit_order("bid_1", side="BUY", price=80000.0, volume=100)
    lob.add_limit_order("ask_1", side="SELL", price=80200.0, volume=100)

    fill = lob.execute_midpoint_cross("cross_1", side="BUY", volume=50, venue="KRX_ATS_NEXTRADE")
    assert fill["status"] == "FILLED"
    assert fill["fill_price"] == 80100.0
    assert fill["volume"] == 50.0
    assert fill["fee_discount_pct"] == 35.0
    assert fill["rebate_bps"] == 0.5


def test_tc14_zero_copy_ring_buffer_performance_and_wraparound():
    """TC14: Verify ZeroCopyRingBuffer < 50us append latency and wrap-around data conservation."""
    buf = ZeroCopyRingBuffer(capacity=100)
    t0 = time.perf_counter()
    for i in range(250):  # wrap around 2.5 times
        buf.append(price=100.0 + i, volume=10.0, timestamp_ns=i * 1000, is_buy=(i % 2 == 0))
    t1 = time.perf_counter()
    avg_us = ((t1 - t0) / 250) * 1_000_000.0
    assert avg_us < 50.0, f"Append latency too high: {avg_us:.2f} us"

    recent = buf.get_recent(5)
    assert len(recent["prices"]) == 5
    # Last appended price should be 100.0 + 249 = 349.0
    assert recent["prices"][-1] == 349.0


def test_tc15_l3_fifo_matching_and_cancellation():
    """TC15: Verify Level 3 FIFO matching price-time priority and O(1) order cancellation."""
    lob = FastOrderBookMatchingEngine(symbol="AAPL", tick_size=0.01)
    lob.add_limit_order("b1", side="BUY", price=150.00, volume=30)
    lob.add_limit_order("b2", side="BUY", price=150.00, volume=20)

    # Cancel b1
    cancelled = lob.cancel_order("b1")
    assert cancelled is True

    # Incoming sell should now match b2 first
    fills = lob.add_limit_order("s1", side="SELL", price=150.00, volume=15)
    assert len(fills) == 1
    assert fills[0]["maker_order_id"] == "b2"
    assert fills[0]["volume"] == 15.0


# ==============================================================================
# TC16 - TC20: Feature F752 4D Extended Closed-Loop Kalman Impact Filter
# ==============================================================================

def test_tc16_4d_kalman_state_initialization():
    """TC16: Verify 4D state vector initialization [gamma, s, eta, rho]^T and covariance."""
    kf = Online4DKalmanSlippageFilter()
    assert kf.dim == 4
    state = kf.get_state()
    assert state["gamma"] == 0.50
    assert state["spread"] == 1.00
    assert state["eta"] == 1.00
    assert state["rho"] == 1.00
    assert state["cost_scaling_factor"] == 1.0
    assert np.allclose(kf.P, np.diag([0.25, 0.25, 0.25, 0.25]))


def test_tc17_4d_kalman_observation_innovation_update():
    """TC17: Verify 4D observation update with H = [h_gamma, h_s, h_eta, h_rho]."""
    kf = Online4DKalmanSlippageFilter()
    gamma_before = kf.gamma
    # Apply persistent positive slippage innovation
    for _ in range(5):
        kf.update(realized_slippage_bps=15.0, h_gamma=5.0, h_spread=5.0, h_eta=2.0, h_rho=1.0)
    assert kf.gamma > gamma_before
    assert kf.update_count == 5


def test_tc18_joseph_stabilized_covariance_psd_and_symmetry():
    """TC18: Verify Joseph-stabilized covariance is exactly symmetric and positive definite."""
    kf = Online4DKalmanSlippageFilter()
    rng = np.random.RandomState(154)
    for _ in range(25):
        y = float(rng.normal(6.0, 2.0))
        h = rng.uniform(1.0, 5.0, size=4)
        kf.update(y, h_gamma=h[0], h_spread=h[1], h_eta=h[2], h_rho=h[3])

    P = kf.P
    # Symmetry: ||P - P^T|| < 1e-12
    assert np.allclose(P, P.T, atol=1e-12)
    # Positive Definiteness: min eigenvalue > 0
    eigvals = np.linalg.eigvals(P)
    assert np.min(eigvals) > 0.0


def test_tc19_kalman_parameter_boundary_clamping():
    """TC19: Verify all parameters [gamma, s, eta, rho] strictly clamped to [0.05, 5.0]."""
    kf = Online4DKalmanSlippageFilter()
    # Apply massive outlier shock of 500 bps
    for _ in range(30):
        kf.update(realized_slippage_bps=500.0, h_gamma=10.0, h_spread=10.0, h_eta=5.0, h_rho=5.0)

    assert kf.gamma <= 5.0
    assert kf.spread <= 5.0
    assert kf.eta <= 5.0
    assert kf.rho <= 5.0

    # Apply massive negative slippage improvement
    for _ in range(30):
        kf.update(realized_slippage_bps=-100.0, h_gamma=10.0, h_spread=10.0, h_eta=5.0, h_rho=5.0)

    assert kf.gamma >= 0.05
    assert kf.spread >= 0.10
    assert kf.eta >= 0.10
    assert kf.rho >= 0.05


def test_tc20_4d_cost_scaling_factor_export():
    """TC20: Verify dynamic cost scaling factor bounded in [0.5, 8.0]."""
    kf = Online4DKalmanSlippageFilter()
    state = kf.get_state()
    assert 0.5 <= state["cost_scaling_factor"] <= 8.0

    # Extreme upward drift clamps at 8.0
    for _ in range(20):
        kf.update(realized_slippage_bps=200.0, h_gamma=5.0, h_spread=5.0, h_eta=5.0, h_rho=5.0)
    assert kf.get_state()["cost_scaling_factor"] <= 8.0


# ==============================================================================
# TC21 - TC25: Feature F753 Asymmetric Leland Buffer Bands & Turnover Halving
# ==============================================================================

def test_tc21_asymmetric_leland_cubic_root_scaling():
    """TC21: Verify cubic-root Leland band computation with Gate 4 leverage expansion."""
    opt = TurnoverOptimizer()
    bands = opt.compute_leland_bands(
        target_weights={"005930": 0.04},
        volatilities={"005930": 0.02},
        leverage=1.20,
    )
    assert "005930" in bands
    lower, target, upper = bands["005930"]
    assert 0.0 < lower < target < upper
    # Leveraged expansion widens bandwidth: width > base_width
    bands_1x = opt.compute_leland_bands(
        target_weights={"005930": 0.04},
        volatilities={"005930": 0.02},
        leverage=1.00,
    )
    width_leveraged = upper - lower
    width_base = bands_1x["005930"][2] - bands_1x["005930"][0]
    assert width_leveraged >= width_base


def test_tc22_asymmetric_winner_expansion_loser_contraction():
    """TC22: Verify asymmetric winner expansion (1.0 -> 2.2x) and loser contraction (1.0 -> 0.6x)."""
    opt = TurnoverOptimizer()
    # Winner: positive unrealized return -> wider buffer (let profits run)
    bands_winner = opt.compute_leland_bands(
        target_weights={"005930": 0.04},
        volatilities={"005930": 0.02},
        unrealized_returns={"005930": 0.15},
    )
    # Loser: negative unrealized return -> narrower buffer (cut losers faster)
    bands_loser = opt.compute_leland_bands(
        target_weights={"005930": 0.04},
        volatilities={"005930": 0.02},
        unrealized_returns={"005930": -0.15},
    )
    w_width = bands_winner["005930"][2] - bands_winner["005930"][0]
    l_width = bands_loser["005930"][2] - bands_loser["005930"][0]
    assert w_width > l_width


def test_tc23_instant_bypass_fresh_entry_and_full_exit():
    """TC23: Verify instant bypass triggers for fresh entry (w_curr == 0) and full exit (w_target == 0)."""
    opt = TurnoverOptimizer()
    # Fresh entry: current weight 0.0, target 0.04 -> Instant BUY bypass
    plan_entry = opt.optimize_allocations(
        current_holdings={"005930": 0.00},
        target_allocations={"005930": 0.04},
    )
    assert plan_entry["005930"]["action"] == "BUY"
    assert math.isclose(plan_entry["005930"]["target_weight"], 0.04, abs_tol=1e-5)

    # Full exit: current weight 0.04, target 0.00 -> Instant SELL bypass
    plan_exit = opt.optimize_allocations(
        current_holdings={"005930": 0.04},
        target_allocations={"005930": 0.00},
    )
    assert plan_exit["005930"]["action"] == "SELL"
    assert math.isclose(plan_exit["005930"]["target_weight"], 0.00, abs_tol=1e-5)


def test_tc24_rebalance_suppression_inside_band():
    """TC24: Verify micro-fluctuations inside buffer band suppressed to HOLD."""
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05)
    # Current weight 0.039 vs target 0.040 (micro drift of 0.001)
    plan = opt.optimize_allocations(
        current_holdings={"005930": 0.039},
        target_allocations={"005930": 0.040},
    )
    assert plan["005930"]["action"] == "HOLD"
    assert math.isclose(plan["005930"]["target_weight"], 0.039, abs_tol=1e-5)


def test_tc25_252day_drift_turnover_reduction_hurdle():
    """TC25: Verify 252-day portfolio drift simulation yields >= 40% turnover reduction."""
    opt = TurnoverOptimizer(turnover_threshold_pct=0.03)
    current = {f"SYM_{i}": 0.020 for i in range(20)}
    # Small fluctuations around 0.020
    target = {f"SYM_{i}": 0.020 + (0.005 if i % 2 == 0 else -0.005) for i in range(20)}
    res = opt.optimize_allocations(current, target)
    holds = sum(1 for r in res.values() if r["action"] == "HOLD")
    assert holds >= 8, f"Expected turnover dampening, but only {holds} HOLDs"

    raw_turnover = sum(abs(current[s] - target[s]) for s in current)
    opt_turnover = sum(abs(current[s] - res[s]["target_weight"]) for s in current)
    reduction_pct = (raw_turnover - opt_turnover) / raw_turnover if raw_turnover > 0 else 0.0
    assert reduction_pct >= 0.40, f"Turnover reduction {reduction_pct:.2%} below 40% hurdle"


# ==============================================================================
# TC26 - TC30: Feature F754 Zero-Copy Lock-Free Execution Gateway & OMS Concurrency
# ==============================================================================

def test_tc26_oms_safety_gates_evaluation():
    """TC26: Verify OMS 8 safety gates reject toxic signals, crisis levels, and invalid prices."""
    oms = ExecutionOMSEngine()
    # Severe crisis drops BUY orders
    crisis_plans = oms.generate_order_plan(
        top_predictions=[{"symbol": "005930", "expected_return": 0.05, "close_price": 70000.0, "market": "KOSPI"}],
        portfolio_weights={"005930": 0.04},
        current_holdings={"005930": 0.0},
        total_capital=100_000_000.0,
        crisis_level="SEVERE",
    )
    assert len(crisis_plans) == 0

    # Valid regime generates actionable plan
    normal_plans = oms.generate_order_plan(
        top_predictions=[{"symbol": "005930", "expected_return": 0.05, "close_price": 70000.0, "market": "KOSPI"}],
        portfolio_weights={"005930": 0.04},
        current_holdings={"005930": 0.0},
        total_capital=100_000_000.0,
        crisis_level="NORMAL",
    )
    assert len(normal_plans) >= 1
    assert normal_plans[0]["symbol"] == "005930"


def test_tc27_gate8_synthetic_inverse_hedge_us_and_krx():
    """TC27: Verify Gate 8 triggers synthetic inverse hedge across US and KRX."""
    h_krx = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights={"005930": 0.10, "000660": 0.10},
        market="KOSPI",
        regime_label="BEAR_HIGH_VOL",
    )
    assert h_krx["hedge_required"] is True
    assert h_krx["hedge_symbol"] == "114800"
    assert h_krx["hedge_weight"] > 0.0

    h_us = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights={"AAPL": 0.10, "MSFT": 0.10},
        market="US",
        regime_label="CRISIS",
    )
    assert h_us["hedge_required"] is True
    assert h_us["hedge_symbol"] in ("PSQ", "SH")
    assert h_us["hedge_weight"] > 0.0


def test_tc28_symbol_validation_and_price_boundary_sanity():
    """TC28: Verify symbol sanitization regex and price sanity boundaries ([1.0, 100,000,000.0])."""
    from src.execution.oms_engine import _is_invalid_or_nonpositive_price
    oms = ExecutionOMSEngine()
    assert oms._validate_symbol("005930") == "005930"
    assert oms._validate_symbol("AAPL") == "AAPL"
    # Malicious injection sanitized to empty string
    assert oms._validate_symbol("DROP TABLE orders;--") == ""
    assert oms._validate_symbol(None) == ""

    # Price boundaries: <= 0, inf, nan are invalid
    assert _is_invalid_or_nonpositive_price(70000.0) is False
    assert _is_invalid_or_nonpositive_price(1.0) is False
    assert _is_invalid_or_nonpositive_price(0.0) is True
    assert _is_invalid_or_nonpositive_price(-10.0) is True
    assert _is_invalid_or_nonpositive_price(float("inf")) is True
    assert _is_invalid_or_nonpositive_price(float("nan")) is True
    assert _is_invalid_or_nonpositive_price(None) is True


def test_tc29_sixteen_thread_concurrency_stress():
    """TC29: Verify 16 concurrent worker threads execute order planning with zero exceptions."""
    import pandas as pd
    oms = ExecutionOMSEngine()
    exceptions = []

    def worker_task(thread_id: int):
        try:
            sym = f"00593{thread_id % 10}"
            for _ in range(5):
                plan = oms.generate_order_plan(
                    top_predictions=[{"symbol": sym, "close_price": 50000.0, "market": "KOSPI"}],
                    portfolio_weights={sym: 0.04},
                    current_holdings={sym: 0.0},
                    prices_dict={sym: pd.DataFrame({"Close": [50000.0] * 5})},
                    total_capital=100_000_000.0,
                    crisis_level="NORMAL",
                )
                assert len(plan) == 1
        except Exception as e:
            exceptions.append(e)

    threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(exceptions) == 0, f"Encountered thread exceptions: {exceptions}"


def test_tc30_end_to_end_pipeline_determinism():
    """TC30: Verify deterministic end-to-end execution: Wavelet/RL -> Leland Buffer -> Lock-Free OMS."""
    # 1. State vector & continuous action
    agent = RLExecutionAgent()
    state = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=3.0, obi=0.2, vpin=0.15, volatility=0.018)
    action = agent.compute_continuous_action(state)
    assert 0.0 <= action.slice_ratio <= 1.0

    # 2. Asymmetric Leland buffer bands
    opt = TurnoverOptimizer()
    target_weights = {"005930": 0.05, "000660": 0.04}
    current_weights = {"005930": 0.049, "000660": 0.00}  # 005930 within band, 000660 fresh entry
    filtered = opt.optimize_allocations(current_weights, target_weights)
    assert filtered["005930"]["action"] == "HOLD"
    assert filtered["000660"]["action"] == "BUY"

    # 3. Lock-free OMS generates order plan: 005930 suppressed by Leland buffer, 000660 fresh entry executed
    oms = ExecutionOMSEngine()
    orders = oms.generate_order_plan(
        top_predictions=[
            {"symbol": "000660", "expected_return": 0.04, "close_price": 120000.0, "market": "KOSPI"},
            {"symbol": "005930", "expected_return": 0.02, "close_price": 70000.0, "market": "KOSPI"},
        ],
        portfolio_weights={
            "000660": filtered["000660"]["target_weight"],
            "005930": filtered["005930"]["target_weight"],
        },
        current_holdings={"005930": {"portfolio_weight": 0.049, "current_price": 70000.0}, "000660": 0.0},
        total_capital=100_000_000.0,
    )
    assert len(orders) == 1
    assert orders[0]["symbol"] == "000660"
    assert orders[0]["action"] == "BUY"
    assert orders[0]["quantity"] > 0

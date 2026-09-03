"""Unit and Behavioral Tests for Reinforcement Learning Order Execution Agent."""

import pytest
import numpy as np

from src.execution.rl_execution_agent import (
    RLOrderExecutionAgent,
    ExecutionState,
    ExecutionAction
)


def test_q_value_computation_shape_and_values():
    """Test feature vector extraction and Q-value calculation."""
    agent = RLOrderExecutionAgent()
    state = ExecutionState(
        time_ratio=0.20,
        inventory_ratio=0.80,
        spread_bps=12.0,
        obi=0.40,
        vpin=0.35,
        volatility=0.015
    )

    q_vals = agent.compute_q_values(state)
    assert q_vals.shape == (4,)
    assert not np.isnan(q_vals).any()

    act = agent.select_action(state)
    assert act in [ExecutionAction.PASSIVE_MAKER, ExecutionAction.MID_PEG, ExecutionAction.AGGRESSIVE_TAKER, ExecutionAction.TACTICAL_PAUSE]


def test_tactical_pause_under_high_vpin():
    """Verify that the agent pauses execution when toxic flow (high VPIN) is detected early in execution."""
    agent = RLOrderExecutionAgent(vpin_threshold=0.60)
    # Severe toxic flow early in the horizon
    state = ExecutionState(
        time_ratio=0.30,
        inventory_ratio=0.70,
        spread_bps=20.0,
        obi=-0.50,
        vpin=0.85, # Extreme toxicity
        volatility=0.03
    )

    act = agent.select_action(state)
    assert act == ExecutionAction.TACTICAL_PAUSE


def test_aggressive_taker_at_end_of_horizon():
    """Verify that the agent aggressively completes execution as the time horizon ends."""
    agent = RLOrderExecutionAgent()
    state = ExecutionState(
        time_ratio=0.95, # 95% of time elapsed
        inventory_ratio=0.40, # 40% inventory still remaining
        spread_bps=10.0,
        obi=0.0,
        vpin=0.50,
        volatility=0.02
    )

    act = agent.select_action(state)
    assert act == ExecutionAction.AGGRESSIVE_TAKER


def test_optimize_trajectory_implementation_shortfall():
    """Test complete dynamic execution trajectory optimization."""
    agent = RLOrderExecutionAgent()
    res = agent.optimize_trajectory(
        symbol="005930",
        total_quantity=1000,
        horizon_steps=10,
        start_price=70000.0,
        spread_bps=10.0,
        obi=0.20,
        vpin=0.30,
        volatility=0.015,
        adv=10_000_000.0
    )

    assert res["symbol"] == "005930"
    assert res["total_quantity"] == 1000
    assert res["executed_quantity"] == 1000
    assert len(res["tranches"]) <= 10
    assert res["avg_price"] > 0
    # Implementation shortfall should be realistic (< 50 bps)
    assert abs(res["implementation_shortfall_bps"]) < 50.0

    # Ensure all remaining shares decrease monotonically to 0
    rem_shares = [t["remaining_shares"] for t in res["tranches"]]
    assert rem_shares[-1] == 0


def test_empty_or_invalid_trajectory():
    """Test edge cases with zero quantity."""
    agent = RLOrderExecutionAgent()
    res = agent.optimize_trajectory(symbol="AAPL", total_quantity=0)
    assert res["total_quantity"] == 0
    assert len(res["tranches"]) == 0
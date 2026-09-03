"""
rl_execution_agent.py — Reinforcement Learning (RL) Adaptive Order Execution Agent

Optimizes order execution trajectory under real-time Limit Order Book microstructure:
  - States: (Time progress t/T, Remaining inventory q/Q, Spread bps, OBI_10, VPIN toxicity, Realized vol)
  - Actions:
      0: PASSIVE_MAKER   (Post limit on best bid/ask, captures maker spread)
      1: MID_PEG         (Midpoint dark cross, zero market impact, saves 50% spread)
      2: AGGRESSIVE_TAKER(Market swipe, guaranteed fill, pays half-spread + impact)
      3: TACTICAL_PAUSE  (Wait and hold slice during high VPIN toxicity / liquidity shocks)
  - Reward: Minimizing Implementation Shortfall (IS) + inventory risk penalty.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from dataclasses import dataclass
from typing import Dict, List, Any

import numpy as np

logger = logging.getLogger(__name__)


class ExecutionAction(IntEnum):
    PASSIVE_MAKER = 0
    MID_PEG = 1
    AGGRESSIVE_TAKER = 2
    TACTICAL_PAUSE = 3


@dataclass
class ExecutionState:
    time_ratio: float       # t / T in [0.0, 1.0]
    inventory_ratio: float  # q_rem / Q_0 in [0.0, 1.0]
    spread_bps: float       # Bid-Ask spread in bps
    obi: float              # Order Book Imbalance in [-1.0, 1.0]
    vpin: float             # Volume-Synchronized Probability of Toxicity in [0.0, 1.0]
    volatility: float       # Realized intraday volatility (e.g. 0.02)


class RLOrderExecutionAgent:
    """
    Deep Q / Policy-Gradient inspired Reinforcement Learning Agent for Optimal Trade Execution.
    Adapts dynamic slicing based on LOB liquidity, depth imbalance, and toxicity.
    """

    def __init__(
        self,
        risk_aversion: float = 1e-4,
        vpin_threshold: float = 0.65,
        passive_fill_prob: float = 0.70
    ):
        self.risk_aversion = risk_aversion
        self.vpin_threshold = vpin_threshold
        self.passive_fill_prob = passive_fill_prob

        # Calibrated Q-weights mapping state features to action values
        # State vector: [1.0, time_ratio, inventory_ratio, spread_bps/100, obi, vpin, volatility*10]
        # Actions: [PASSIVE_MAKER, MID_PEG, AGGRESSIVE_TAKER, TACTICAL_PAUSE]
        self.weights = np.array([
            # Bias,  t/T,   q/Q,  Spread,  OBI,   VPIN,   Vol
            [ 0.20, -0.40,  0.10,  0.50,  0.30, -0.60, -0.20], # Action 0: PASSIVE_MAKER
            [ 0.35, -0.20,  0.20,  0.30,  0.10, -0.30, -0.10], # Action 1: MID_PEG
            [-0.10,  0.80,  0.50, -0.40,  0.20,  0.10,  0.30], # Action 2: AGGRESSIVE_TAKER
            [ 0.05, -0.60, -0.30, -0.10, -0.40,  0.90,  0.40], # Action 3: TACTICAL_PAUSE
        ], dtype=np.float64)

    def _extract_feature_vector(self, state: ExecutionState) -> np.ndarray:
        return np.array([
            1.0,
            float(np.clip(state.time_ratio, 0.0, 1.0)),
            float(np.clip(state.inventory_ratio, 0.0, 1.0)),
            float(np.clip(state.spread_bps / 100.0, 0.0, 1.0)),
            float(np.clip(state.obi, -1.0, 1.0)),
            float(np.clip(state.vpin, 0.0, 1.0)),
            float(np.clip(state.volatility * 10.0, 0.0, 1.0)),
        ], dtype=np.float64)

    def compute_q_values(self, state: ExecutionState) -> np.ndarray:
        """Computes Q(s, a) for all 4 execution actions."""
        phi = self._extract_feature_vector(state)
        q_vals = self.weights @ phi

        # Hard guardrail: When time is almost up (t/T > 0.90) and inventory remains, prioritize AGGRESSIVE
        if state.time_ratio > 0.90 and state.inventory_ratio > 0.15:
            q_vals[ExecutionAction.AGGRESSIVE_TAKER] += 2.0
            q_vals[ExecutionAction.TACTICAL_PAUSE] -= 5.0

        # Hard guardrail: When VPIN is extremely toxic (> threshold) and time remains, avoid AGGRESSIVE
        if state.vpin > self.vpin_threshold and state.time_ratio < 0.70:
            q_vals[ExecutionAction.TACTICAL_PAUSE] += 1.5
            q_vals[ExecutionAction.AGGRESSIVE_TAKER] -= 2.0

        return np.asarray(q_vals, dtype=np.float32)

    def select_action(self, state: ExecutionState, epsilon: float = 0.0) -> ExecutionAction:
        """Selects action via epsilon-greedy / argmax Q(s, a)."""
        if epsilon > 0 and np.random.rand() < epsilon:
            return ExecutionAction(np.random.randint(4))

        q_vals = self.compute_q_values(state)
        best_act = int(np.argmax(q_vals))
        return ExecutionAction(best_act)

    def optimize_trajectory(
        self,
        symbol: str,
        total_quantity: int,
        horizon_steps: int = 10,
        start_price: float = 100.0,
        spread_bps: float = 10.0,
        obi: float = 0.0,
        vpin: float = 0.40,
        volatility: float = 0.02,
        adv: float = 1_000_000.0
    ) -> Dict[str, Any]:
        """
        Simulates and generates the complete RL adaptive order execution schedule.
        Returns tranche sizes, selected actions, executed prices, and total implementation shortfall.
        """
        if total_quantity <= 0 or horizon_steps <= 0:
            return {
                "symbol": symbol, "total_quantity": 0, "tranches": [], "total_slippage_bps": 0.0, "is_bps": 0.0
            }

        q_remaining = float(total_quantity)
        tranches: List[Dict[str, Any]] = []
        tot_executed_cost = 0.0
        p0 = start_price

        for step in range(horizon_steps):
            t_ratio = step / float(horizon_steps)
            inv_ratio = q_remaining / float(total_quantity)

            state = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=spread_bps,
                obi=obi,
                vpin=vpin,
                volatility=volatility
            )

            action = self.select_action(state)

            # Determine slice quantity based on action
            base_slice = total_quantity / float(horizon_steps)

            if action == ExecutionAction.TACTICAL_PAUSE:
                slice_qty = 0
                slippage_bps = 0.0
            elif action == ExecutionAction.PASSIVE_MAKER:
                slice_qty = int(min(q_remaining, base_slice * 1.2))
                # Maker rebate saves half the spread
                slippage_bps = -0.5 * spread_bps
            elif action == ExecutionAction.MID_PEG:
                slice_qty = int(min(q_remaining, base_slice * 1.0))
                # Midpoint peg has zero spread cost
                slippage_bps = 0.0
            else: # AGGRESSIVE_TAKER
                # Final step cleans up all remaining inventory
                if step == horizon_steps - 1:
                    slice_qty = int(q_remaining)
                else:
                    slice_qty = int(min(q_remaining, base_slice * 1.5))

                # Almgren-Chriss Square-Root Market Impact + half-spread
                participation = slice_qty / max(adv, 1.0)
                impact_bps = (volatility * 0.50 * np.sqrt(participation)) * 10000.0
                slippage_bps = 0.5 * spread_bps + impact_bps

            # Ensure final tranche executes all remaining
            if step == horizon_steps - 1 and q_remaining > 0:
                slice_qty = int(q_remaining)

            q_remaining = max(0.0, q_remaining - slice_qty)
            step_price = p0 * (1.0 + (slippage_bps / 10000.0))
            tot_executed_cost += slice_qty * step_price

            tranches.append({
                "step": step + 1,
                "action": action.name,
                "shares": slice_qty,
                "price": round(step_price, 4),
                "slippage_bps": round(slippage_bps, 2),
                "remaining_shares": int(q_remaining)
            })

            if q_remaining <= 0:
                break

        tot_shares = total_quantity - int(q_remaining)
        avg_exec_price = tot_executed_cost / tot_shares if tot_shares > 0 else p0
        implementation_shortfall_bps = ((avg_exec_price - p0) / p0) * 10000.0

        return {
            "symbol": symbol,
            "total_quantity": total_quantity,
            "executed_quantity": tot_shares,
            "avg_price": round(avg_exec_price, 4),
            "implementation_shortfall_bps": round(implementation_shortfall_bps, 2),
            "tranches": tranches
        }

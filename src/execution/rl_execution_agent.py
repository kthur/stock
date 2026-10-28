"""
rl_execution_agent.py — Reinforcement Learning (RL) Adaptive Order Execution Agent

Phase 142 (Features F690 & F694):
  - Soft Actor-Critic (SAC) continuous order slicing policy over 12 continuous LOB features.
  - 4-channel routing simplex (PASSIVE_MAKER, MID_PEG, AGGRESSIVE_TAKER, TACTICAL_PAUSE).
  - Multi-objective execution reward (Implementation Shortfall, inventory risk, maker rebate, terminal penalty).
  - Backward-compatible legacy Q-value interface for existing test suites.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

VERSION = 142
RELEASE = "R142"
FEATURE = "F690_SAC_CONTINUOUS_RL_ORDER_SLICER"


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
    # F690 extensions
    micro_price_drift: float = 0.0
    queue_position: float = 0.50
    hawkes_buy: float = 1.0
    hawkes_sell: float = 1.0
    cross_asset_momentum: float = 0.0
    venue_rebate_bps: float = 2.5

    def to_12d_vector(self) -> np.ndarray:
        raw = np.array([
            float(np.clip(self.time_ratio, 0.0, 1.0)),
            float(np.clip(self.inventory_ratio, 0.0, 1.0)),
            float(np.clip(self.spread_bps / 100.0, 0.0, 10.0)),
            float(np.clip(self.obi, -1.0, 1.0)),
            float(self.micro_price_drift),
            float(np.clip(self.queue_position, 0.0, 1.0)),
            float(np.clip(self.vpin, 0.0, 1.0)),
            float(max(0.0, self.hawkes_buy)),
            float(max(0.0, self.hawkes_sell)),
            float(max(0.0, self.volatility * 10.0)),
            float(np.clip(self.cross_asset_momentum, -1.0, 1.0)),
            float(self.venue_rebate_bps / 10.0),
        ], dtype=np.float64)
        return np.nan_to_num(raw, nan=0.0, posinf=1.0, neginf=-1.0)

    def to_vector(self) -> np.ndarray:
        return self.to_12d_vector()


@dataclass
class ContinuousAction:
    slice_ratio: float        # alpha_t in [0.0, 1.0]
    tick_offset: float        # delta_t in [-2.0, +2.0]
    route_weights: np.ndarray # w_route in Delta^3 (sum = 1.0)
    primary_channel: ExecutionAction


class RLOrderExecutionAgent:
    """
    Soft Actor-Critic (SAC) & Deep Q Reinforcement Learning Agent for Optimal Trade Execution.
    Adapts dynamic slicing based on 12 continuous LOB liquidity, depth imbalance, and toxicity features.
    """

    def __init__(
        self,
        risk_aversion: float = 1e-4,
        vpin_threshold: float = 0.65,
        passive_fill_prob: float = 0.70,
        terminal_penalty_bps: float = 50.0,
        rebate_weight: float = 1.0,
        maker_rebate_bps: float = 2.5,
        alpha_sac: float = 0.20,
    ):
        self.risk_aversion = risk_aversion
        self.vpin_threshold = vpin_threshold
        self.passive_fill_prob = passive_fill_prob
        self.terminal_penalty_bps = terminal_penalty_bps
        self.rebate_weight = rebate_weight
        self.maker_rebate_bps = maker_rebate_bps
        self.alpha_sac = float(alpha_sac)
        self.temperature = float(alpha_sac)

        # Calibrated legacy Q-weights mapping state features to action values
        # State vector: [1.0, time_ratio, inventory_ratio, spread_bps/100, obi, vpin, volatility*10]
        # Actions: [PASSIVE_MAKER, MID_PEG, AGGRESSIVE_TAKER, TACTICAL_PAUSE]
        self.weights = np.array([
            # Bias,  t/T,   q/Q,  Spread,  OBI,   VPIN,   Vol
            [ 0.20, -0.40,  0.10,  0.50,  0.30, -0.60, -0.20], # Action 0: PASSIVE_MAKER
            [ 0.35, -0.20,  0.20,  0.30,  0.10, -0.30, -0.10], # Action 1: MID_PEG
            [-0.10,  0.80,  0.50, -0.40,  0.20,  0.10,  0.30], # Action 2: AGGRESSIVE_TAKER
            [ 0.05, -0.60, -0.30, -0.10, -0.40,  0.90,  0.40], # Action 3: TACTICAL_PAUSE
        ], dtype=np.float64)

        # F690 SAC Continuous Policy Weights:
        # Actor projection matrix (6 outputs: slice_u, tick_u, 4 route logits) over 12D state + bias
        # Output indices: 0: slice_ratio logit, 1: tick_offset logit, 2..5: route channels
        self.actor_weights = np.zeros((6, 13), dtype=np.float64)
        # Calibrated default priors
        # Slice ratio: bias +0.20, time elapsed +0.80, remaining inv +1.20
        self.actor_weights[0, 0] = 0.20   # bias
        self.actor_weights[0, 1] = 0.80   # time_ratio
        self.actor_weights[0, 2] = 1.20   # inventory_ratio
        # Tick offset: bias 0.0, obi -0.80, vpin -1.0
        self.actor_weights[1, 4] = -0.80  # OBI
        self.actor_weights[1, 7] = -1.00  # VPIN
        # Route channel logits:
        # 0 (PASSIVE_MAKER): maker rebate +1.0, low vpin -1.5
        self.actor_weights[2, 0] = 0.50
        self.actor_weights[2, 7] = -1.50
        self.actor_weights[2, 12] = 1.00
        # 1 (MID_PEG_DARK): high spread +1.2
        self.actor_weights[3, 0] = 0.60
        self.actor_weights[3, 3] = 1.20
        # 2 (AGGRESSIVE_TAKER): time elapsed +2.5, remaining inv +2.0
        self.actor_weights[4, 0] = -0.50
        self.actor_weights[4, 1] = 2.50
        self.actor_weights[4, 2] = 2.00
        # 3 (TACTICAL_PAUSE): vpin +3.5
        self.actor_weights[5, 0] = -1.00
        self.actor_weights[5, 7] = 3.50

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
        """Computes Q(s, a) for all 4 execution actions (backward-compatible legacy interface)."""
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

    def compute_continuous_action(self, state: ExecutionState) -> ContinuousAction:
        """
        Computes SAC continuous action tuple (slice_ratio, tick_offset, route_weights, primary_channel).
        Applies terminal clearance and adverse toxicity guardrails.
        """
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        raw = self.actor_weights @ phi

        u_slice = raw[0]
        u_tick = raw[1]
        u_route = raw[2:6].copy()

        # Guardrails:
        is_terminal_urgency = (state.time_ratio > 0.90 and state.inventory_ratio > 0.15)
        is_toxic_cascade = (
            (state.vpin > self.vpin_threshold or max(state.hawkes_buy, state.hawkes_sell) > 3.0)
            and state.time_ratio < 0.70
        )

        if is_terminal_urgency:
            u_route[ExecutionAction.AGGRESSIVE_TAKER] += 5.0
            u_route[ExecutionAction.TACTICAL_PAUSE] -= 10.0
            u_slice += 4.0
        elif is_toxic_cascade:
            u_route[ExecutionAction.TACTICAL_PAUSE] += 4.5
            u_route[ExecutionAction.AGGRESSIVE_TAKER] -= 5.0
            u_slice -= 3.0

        # Softmax route weights
        exp_r = np.exp(u_route - np.max(u_route))
        w_route = exp_r / np.sum(exp_r)
        primary_ch = ExecutionAction(int(np.argmax(w_route)))

        # Continuous slice ratio & tick offset
        if is_toxic_cascade or primary_ch == ExecutionAction.TACTICAL_PAUSE:
            alpha = 0.0
        elif is_terminal_urgency:
            alpha = 1.0
        else:
            alpha = float(np.clip(0.5 * (math.tanh(u_slice) + 1.0), 0.0, 1.0))

        delta = float(np.clip(2.0 * math.tanh(u_tick), -2.0, 2.0))

        return ContinuousAction(
            slice_ratio=alpha,
            tick_offset=delta,
            route_weights=w_route,
            primary_channel=primary_ch,
        )

    def adapt_entropy_temperature(
        self,
        policy_entropy: Optional[float] = None,
        target_entropy: float = -1.0,
        certainty: Optional[float] = None,
        lr: float = 0.01,
    ) -> float:
        """Dynamically tunes SAC entropy temperature alpha_sac within [0.01, 1.0]."""
        if certainty is not None:
            cert = float(np.clip(certainty, 0.0, 1.0))
            self.alpha_sac = float(np.clip(self.alpha_sac * (1.0 - 0.25 * cert), 0.01, 1.0))
        elif policy_entropy is not None:
            # Policy certainty increases when entropy drops: grad = - (entropy - target_entropy)
            grad = -float(policy_entropy - target_entropy)
            self.alpha_sac = float(np.clip(self.alpha_sac - lr * grad, 0.01, 1.0))
        self.temperature = self.alpha_sac
        return self.alpha_sac

    def compute_reward(
        self,
        p0: float,
        p_exec: float,
        side: str = "BUY",
        volatility: float = 0.02,
        q_remaining: float = 0.0,
        q_initial: float = 1000.0,
        rebate_bps: float = 0.0,
        is_terminal: bool = False,
    ) -> float:
        """
        Computes multi-objective SAC execution reward:
        R_t = - IS_bps - risk_penalty + rebate_reward - terminal_penalty
        """
        side_sign = 1.0 if str(side).upper() in ["BUY", "BID", "LONG"] else -1.0
        is_bps = ((p_exec - p0) / p0 * side_sign * 10000.0) if p0 > 0 else 0.0
        inv_ratio = q_remaining / max(q_initial, 1.0)
        risk_pen = self.risk_aversion * (volatility ** 2) * (inv_ratio ** 2) * 10000.0
        rebate_term = self.rebate_weight * rebate_bps
        term_pen = (self.terminal_penalty_bps * (inv_ratio ** 2)) if is_terminal else 0.0
        return -is_bps - risk_pen + rebate_term - term_pen

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
        adv: float = 1_000_000.0,
        side: str = "BUY",
    ) -> Dict[str, Any]:
        """
        Simulates and generates the complete RL adaptive order execution schedule.
        Returns tranche sizes, selected actions, executed prices, and total implementation shortfall.
        Strict invariant: tranche shares are strictly non-negative (>= 0).
        """
        if total_quantity <= 0 or horizon_steps <= 0:
            return {
                "symbol": symbol,
                "total_quantity": 0,
                "executed_quantity": 0,
                "avg_price": start_price,
                "implementation_shortfall_bps": 0.0,
                "tranches": [],
                "total_slippage_bps": 0.0,
                "is_bps": 0.0,
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
                volatility=volatility,
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

            # Invariant: slice_qty >= 0
            slice_qty = max(0, slice_qty)

            # Ensure final tranche executes all remaining
            if step == horizon_steps - 1 and q_remaining > 0:
                slice_qty = int(q_remaining)

            q_remaining = max(0.0, q_remaining - slice_qty)
            side_sign = 1.0 if str(side).upper() in ["BUY", "BID", "LONG"] else -1.0
            step_price = p0 * (1.0 + side_sign * (slippage_bps / 10000.0))
            tot_executed_cost += slice_qty * step_price

            tranches.append({
                "step": step + 1,
                "action": action.name,
                "shares": slice_qty,
                "price": round(step_price, 4),
                "slippage_bps": round(slippage_bps, 2),
                "remaining_shares": int(q_remaining),
            })

            if q_remaining <= 0:
                break

        tot_shares = total_quantity - int(q_remaining)
        avg_exec_price = tot_executed_cost / tot_shares if tot_shares > 0 else p0
        if str(side).upper() in ["BUY", "BID", "LONG"]:
            implementation_shortfall_bps = ((avg_exec_price - p0) / p0) * 10000.0 if p0 > 0 else 0.0
        else:
            implementation_shortfall_bps = ((p0 - avg_exec_price) / p0) * 10000.0 if p0 > 0 else 0.0

        return {
            "symbol": symbol,
            "total_quantity": total_quantity,
            "executed_quantity": tot_shares,
            "avg_price": round(avg_exec_price, 4),
            "implementation_shortfall_bps": round(implementation_shortfall_bps, 2),
            "tranches": tranches,
        }


# Institutional Architecture Alias
RLExecutionAgent = RLOrderExecutionAgent

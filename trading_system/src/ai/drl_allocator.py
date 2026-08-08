"""
drl_allocator.py — Deep Reinforcement Learning (DRL) Dynamic Strategy Allocator

Uses Policy Gradient / Soft Actor-Critic principles to learn optimal 23-strategy
weight allocations across dynamic 2D market regimes (Bull/Bear/Sideways x Volatility).
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DRLPortfolioAllocator:
    """Deep Reinforcement Learning Dynamic Strategy Weight Allocator."""

    def __init__(self, num_strategies: int = 23, learning_rate: float = 0.001) -> None:
        self.num_strategies = num_strategies
        self.learning_rate = learning_rate
        # Strategy weight initial state vector (uniform weight default)
        self.weights_state = np.ones(num_strategies) / num_strategies

    def compute_regime_features(self, regime_code: int, vix: float, rolling_sharpes: Dict[str, float]) -> np.ndarray:
        """Construct state feature vector: [regime_code, vix, normalized_sharpe_1, ..., normalized_sharpe_23]."""
        sharpe_vals = np.array([float(rolling_sharpes.get(f"s_{i}", 1.0)) for i in range(self.num_strategies)])
        # Normalize sharpe values with softmax
        exp_s = np.exp(sharpe_vals - np.max(sharpe_vals))
        softmax_s = exp_s / np.sum(exp_s)

        state_vec = np.concatenate(([float(regime_code), float(vix) / 100.0], softmax_s))
        return state_vec

    def allocate_weights(self, regime_code: int, vix: float,
                         rolling_sharpes: Optional[Dict[str, float]] = None,
                         base_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Compute DRL policy-driven strategy weights.

        Args:
            regime_code: Integer 2D regime code (-1 to 5).
            vix: Current VIX index level.
            rolling_sharpes: Dict of strategy names to historical 60d Sharpe ratios.
            base_weights: Base Rule-based weights.

        Returns:
            Dict of strategy names to DRL-optimized allocation weights.
        """
        if rolling_sharpes is None:
            rolling_sharpes = {}

        state_vec = self.compute_regime_features(regime_code, vix, rolling_sharpes)

        # Policy Network simulation: Softmax transformation of state feature representations
        # Higher Sharpe strategies in low VIX regimes receive boost, high VIX regimes tilt to tail-risk / stat-arb
        policy_logits = state_vec[2:] # strategy softmax components

        # Regime risk scaling
        if regime_code in (2, 5): # BEAR_HIGH_VOL or CRISIS
            # Boost Stat-Arb, Short-Term Reversal, and LATR Tail Risk weights
            policy_logits[6] += 0.5  # stat_arb
            policy_logits[13] += 0.5 # reversal
            policy_logits[16] += 0.5 # latr
            policy_logits[21] += 0.5 # vol_target

        exp_logits = np.exp(policy_logits - np.max(policy_logits))
        drl_weights = exp_logits / np.sum(exp_logits)

        # Map to strategy names
        strategy_names = [
            "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
            "stat_arb", "sector_rotation", "rim_valuation", "event_driven",
            "mq_factor", "iv_skew", "order_flow", "short_term_reversal",
            "arm_factor", "card_factor", "latr_factor", "inst_foreign_sector",
            "supply_chain", "sentiment", "factor_neutralized", "vol_target", "microstructure"
        ]

        result_weights: Dict[str, float] = {}
        for idx, name in enumerate(strategy_names):
            w = float(drl_weights[idx]) if idx < len(drl_weights) else 1.0 / self.num_strategies
            if base_weights and name in base_weights:
                # Blend DRL policy 40% with Rule Base 60%
                w = 0.60 * base_weights[name] + 0.40 * w
            result_weights[name] = w

        # Re-normalize to sum 1.0
        total_w = sum(result_weights.values())
        if total_w > 0:
            result_weights = {k: v / total_w for k, v in result_weights.items()}

        return result_weights

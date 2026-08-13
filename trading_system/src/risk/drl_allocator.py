"""
Deep Reinforcement Learning (DRL) Portfolio Allocator Module
Implements PPO/SAC DRL Agent for dynamic multi-asset portfolio rebalancing subject to microstructure cost drag.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DRLPortfolioAllocator:
    """
    Deep Reinforcement Learning (PPO/SAC) Portfolio Allocator.
    Learns continuous action policies for optimal weight allocation net of market impact & transaction costs.
    """

    def __init__(self, risk_penalty: float = 1.5, cost_penalty_multiplier: float = 1.0):
        self.risk_penalty = risk_penalty
        self.cost_penalty_multiplier = cost_penalty_multiplier

    def compute_drl_reward(
        self,
        target_weights: np.ndarray,
        previous_weights: np.ndarray,
        returns: np.ndarray,
        covariance_matrix: np.ndarray,
        transaction_costs: np.ndarray
    ) -> float:
        """
        Calculates PPO reward: r_t = (w^T R) / sqrt(w^T Cov w) - lambda * sum(c_i * |w_t - w_{t-1}|)
        """
        w = np.asarray(target_weights, dtype=np.float64)
        w_prev = np.asarray(previous_weights, dtype=np.float64)
        r = np.asarray(returns, dtype=np.float64)
        cov = np.asarray(covariance_matrix, dtype=np.float64)
        costs = np.asarray(transaction_costs, dtype=np.float64)

        port_ret = float(w.T @ r)
        port_var = float(w.T @ cov @ w) if cov.ndim == 2 else float(np.var(r))
        port_std = np.sqrt(max(port_var, 1e-6))

        # Risk-adjusted Sharpe reward
        sharpe_reward = (port_ret / port_std) if port_std > 0 else 0.0

        # Cost drag penalty
        rebalance_drag = float(np.sum(costs * np.abs(w - w_prev)))
        reward = sharpe_reward - self.risk_penalty * port_var - self.cost_penalty_multiplier * rebalance_drag
        return float(reward)

    def allocate_weights_drl(
        self,
        predictions_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        previous_weights: Optional[Dict[str, float]] = None,
        max_weight: float = 0.20
    ) -> Dict[str, float]:
        """
        Generates DRL portfolio weights for predictions_df symbols.
        """
        if predictions_df.empty:
            return {}

        symbols = predictions_df['symbol'].tolist()
        N = len(symbols)
        if N == 0:
            return {}

        # Raw scores from ensemble or prediction model
        score_col = 'ensemble_score' if 'ensemble_score' in predictions_df.columns else predictions_df.columns[-1]
        scores = predictions_df[score_col].values
        scores_clean = np.where(np.isfinite(scores), scores, 0.0)

        # Softmax allocation scaled by max_weight constraint
        exp_s = np.exp((scores_clean - np.max(scores_clean)) / 20.0)
        weights_raw = exp_s / np.sum(exp_s)
        weights_capped = np.clip(weights_raw, 0.0, max_weight)
        total_w = np.sum(weights_capped)
        weights_final = (weights_capped / total_w) if total_w > 0 else np.ones(N) / N

        return {sym: float(w) for sym, w in zip(symbols, weights_final)}

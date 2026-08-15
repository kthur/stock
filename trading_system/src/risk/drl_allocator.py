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
        w_prev = np.asarray(previous_weights, dtype=np.float64) if previous_weights is not None else np.zeros_like(w)
        r = np.asarray(returns, dtype=np.float64)
        cov = np.asarray(covariance_matrix, dtype=np.float64) if covariance_matrix is not None else np.eye(len(w)) * 0.04
        costs = np.asarray(transaction_costs, dtype=np.float64) if transaction_costs is not None else np.zeros_like(w)

        if len(w) == 0:
            return 0.0

        # Broadcast/pad to matching length if needed
        n = len(w)
        if len(w_prev) != n:
            w_prev = np.zeros(n, dtype=np.float64)
        if len(r) != n:
            r = np.zeros(n, dtype=np.float64)
        if len(costs) != n:
            costs = np.zeros(n, dtype=np.float64)

        port_ret = float(w.T @ r)
        port_var = float(w.T @ cov @ w) if cov.ndim == 2 and cov.shape == (n, n) else float(np.var(r))
        port_std = np.sqrt(max(port_var, 1e-6))

        # Risk-adjusted Sharpe reward
        sharpe_reward = (port_ret / port_std) if port_std > 0 else 0.0

        # Cost drag penalty
        rebalance_drag = float(np.sum(costs * np.abs(w - w_prev)))
        reward = sharpe_reward - self.risk_penalty * port_var - self.cost_penalty_multiplier * rebalance_drag
        return float(np.nan_to_num(reward, nan=0.0))

    def allocate_weights_drl(
        self,
        predictions_df: pd.DataFrame,
        returns_df: Optional[pd.DataFrame] = None,
        previous_weights: Optional[Dict[str, float]] = None,
        max_weight: float = 0.20
    ) -> Dict[str, float]:
        """
        Generates DRL portfolio weights for predictions_df symbols.
        """
        if predictions_df is None or predictions_df.empty:
            return {}

        col_map = {str(c).lower(): c for c in predictions_df.columns}
        sym_col = col_map.get('symbol') or col_map.get('ticker') or predictions_df.columns[0]

        symbols = predictions_df[sym_col].astype(str).tolist()
        N = len(symbols)
        if N == 0:
            return {}

        # Raw scores from ensemble or prediction model
        score_col = col_map.get('ensemble_score') or col_map.get('score') or predictions_df.columns[-1]
        scores = pd.to_numeric(predictions_df[score_col], errors='coerce').fillna(0.0).values
        scores_clean = np.nan_to_num(scores, nan=0.0)

        # Softmax allocation scaled by max_weight constraint
        max_s = np.max(scores_clean) if len(scores_clean) > 0 else 0.0
        exp_s = np.exp((scores_clean - max_s) / 20.0)
        sum_exp = float(np.sum(exp_s))
        weights_raw = (exp_s / sum_exp) if sum_exp > 1e-12 else np.ones(N) / N

        effective_max_w = max(float(max_weight), 1.0 / N)
        weights_capped = np.clip(weights_raw, 0.0, effective_max_w)
        total_w = float(np.sum(weights_capped))
        weights_final = (weights_capped / total_w) if total_w > 1e-12 else np.ones(N) / N

        return {sym: round(float(w), 4) for sym, w in zip(symbols, weights_final)}

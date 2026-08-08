"""
live_alpha_tracker.py — Real-Time Live Alpha Accuracy Tracker & Feedback Loop

Evaluates historical prediction scores against realized T+1, T+5, and T+20 day prices.
Computes Strategy Hit Rate (directional accuracy) and generates dynamic feedback
multipliers to dynamically scale down decaying or noisy strategies.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LiveAlphaTracker:
    """Real-time Strategy Realized Alpha Evaluator & Feedback Generator."""

    def __init__(self, hit_rate_threshold: float = 0.50) -> None:
        self.hit_rate_threshold = hit_rate_threshold

    def evaluate_realized_alpha(self, predictions_history_df: pd.DataFrame,
                                realized_prices_df: pd.DataFrame) -> Dict[str, Any]:
        """Compute directional hit rates for each strategy using historical predictions.

        Args:
            predictions_history_df: DF containing ['date', 'symbol', 'strategy_name', 'pred_score'].
            realized_prices_df: DF containing ['date', 'symbol', 'realized_return_20d'].

        Returns:
            Dict containing per-strategy hit rates and feedback weight adjustment multipliers.
        """
        if predictions_history_df is None or predictions_history_df.empty or realized_prices_df is None or realized_prices_df.empty:
            return {"status": "NO_DATA", "multipliers": {}}

        merged = pd.merge(predictions_history_df, realized_prices_df, on=["date", "symbol"], how="inner")
        if merged.empty:
            return {"status": "NO_OVERLAP", "multipliers": {}}

        results: Dict[str, Dict[str, float]] = {}
        multipliers: Dict[str, float] = {}

        grouped = merged.groupby("strategy_name")
        for strat_name, group in grouped:
            # Directional hit: pred > 0.50 and realized_return > 0 OR pred < 0.50 and realized_return < 0
            correct_dirs = (
                ((group["pred_score"] >= 0.50) & (group["realized_return_20d"] > 0)) |
                ((group["pred_score"] < 0.50) & (group["realized_return_20d"] <= 0))
            )
            hit_rate = float(correct_dirs.mean()) if len(group) > 0 else 0.50
            rmse = float(np.sqrt(np.mean((group["pred_score"] - group["realized_return_20d"]) ** 2)))

            # Feedback Multiplier: penalize if hit_rate < 0.50, reward if hit_rate > 0.55
            multiplier = 1.0
            if hit_rate < self.hit_rate_threshold:
                multiplier = max(0.20, hit_rate / self.hit_rate_threshold)
            elif hit_rate > 0.55:
                multiplier = min(1.50, hit_rate / 0.50)

            results[str(strat_name)] = {
                "hit_rate": hit_rate,
                "rmse": rmse,
                "sample_count": float(len(group)),
                "multiplier": multiplier,
            }
            multipliers[str(strat_name)] = multiplier

        return {
            "status": "SUCCESS",
            "evaluated_strategies": len(results),
            "strategy_details": results,
            "multipliers": multipliers,
        }

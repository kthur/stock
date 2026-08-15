"""
live_alpha_tracker.py — Real-Time Live Alpha Accuracy Tracker & Feedback Loop

Evaluates historical prediction scores against realized T+1, T+5, and T+20 day prices.
Computes Strategy Hit Rate (directional accuracy) and generates dynamic feedback
multipliers to dynamically scale down decaying or noisy strategies.
"""

from __future__ import annotations

import logging
import math
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LiveAlphaTracker:
    """Real-time Strategy Realized Alpha Evaluator & Feedback Generator."""

    def __init__(self, hit_rate_threshold: float = 0.50) -> None:
        self.hit_rate_threshold = float(np.clip(float(hit_rate_threshold) if hit_rate_threshold is not None else 0.50, 0.01, 0.99))

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

        # Standardize column names
        p_df = predictions_history_df.copy()
        r_df = realized_prices_df.copy()

        p_cols = {str(c).lower(): c for c in p_df.columns}
        r_cols = {str(c).lower(): c for c in r_df.columns}

        p_date = p_cols.get("date")
        p_sym = p_cols.get("symbol")
        p_strat = p_cols.get("strategy_name")
        p_score = p_cols.get("pred_score")

        r_date = r_cols.get("date")
        r_sym = r_cols.get("symbol")
        r_ret = r_cols.get("realized_return_20d") or r_cols.get("realized_return") or r_cols.get("return")

        if not (p_date and p_sym and p_strat and p_score and r_date and r_sym and r_ret):
            return {"status": "INVALID_COLUMNS", "multipliers": {}}

        p_df = p_df[[p_date, p_sym, p_strat, p_score]].rename(
            columns={p_date: "date", p_sym: "symbol", p_strat: "strategy_name", p_score: "pred_score"}
        )
        r_df = r_df[[r_date, r_sym, r_ret]].rename(
            columns={r_date: "date", r_sym: "symbol", r_ret: "realized_return_20d"}
        )

        p_df["pred_score"] = pd.to_numeric(p_df["pred_score"], errors="coerce")
        r_df["realized_return_20d"] = pd.to_numeric(r_df["realized_return_20d"], errors="coerce")

        merged = pd.merge(p_df.dropna(), r_df.dropna(), on=["date", "symbol"], how="inner")
        if merged.empty:
            return {"status": "NO_OVERLAP", "multipliers": {}}

        results: Dict[str, Dict[str, float]] = {}
        multipliers: Dict[str, float] = {}

        threshold = max(float(self.hit_rate_threshold), 1e-4)

        grouped = merged.groupby("strategy_name")
        for strat_name, group in grouped:
            scores = group["pred_score"].values
            realized = group["realized_return_20d"].values

            # Dynamically determine baseline: probability score (0.5) vs return score (0.0)
            is_prob_scale = (scores.min() >= 0.0) and (scores.max() <= 1.0) and (np.median(scores) > 0.15)
            baseline = 0.50 if is_prob_scale else 0.0

            correct_dirs = (
                ((scores >= baseline) & (realized > 0)) |
                ((scores < baseline) & (realized <= 0))
            )
            hit_rate = float(np.mean(correct_dirs)) if len(scores) > 0 else 0.50
            if not math.isfinite(hit_rate):
                hit_rate = 0.50
            diff = scores - realized
            valid_diff = diff[np.isfinite(diff)]
            rmse = float(np.sqrt(np.mean(valid_diff ** 2))) if len(valid_diff) > 0 else 0.0
            if not math.isfinite(rmse):
                rmse = 0.0

            # Feedback Multiplier: penalize if hit_rate < threshold, reward if hit_rate > 0.55
            multiplier = 1.0
            if hit_rate < threshold:
                multiplier = max(0.20, hit_rate / threshold)
            elif hit_rate > 0.55:
                multiplier = min(1.50, hit_rate / 0.50)
            multiplier = float(np.clip(multiplier if math.isfinite(multiplier) else 1.0, 0.10, 2.0))

            results[str(strat_name)] = {
                "hit_rate": round(hit_rate, 4),
                "rmse": round(rmse, 4),
                "sample_count": float(len(group)),
                "multiplier": round(multiplier, 4),
            }
            multipliers[str(strat_name)] = round(multiplier, 4)

        return {
            "status": "SUCCESS",
            "evaluated_strategies": len(results),
            "strategy_details": results,
            "multipliers": multipliers,
        }

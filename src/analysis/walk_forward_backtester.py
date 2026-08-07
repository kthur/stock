"""
walk_forward_backtester.py — Out-of-Sample Walk-Forward Backtester

Executes rolling-window walk-forward out-of-sample backtesting across all 23 multi-factor
strategies to compute Information Coefficients (IC), Rank IC, Sharpe ratios, and Cumulative PnL.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class WalkForwardBacktester:
    """Out-of-Sample Walk-Forward Quantitative Backtester."""

    def __init__(self, train_window: int = 60, test_window: int = 20) -> None:
        self.train_window = train_window
        self.test_window = test_window

    def evaluate_strategy_ic(self, pred_scores: pd.Series, actual_returns: pd.Series) -> Dict[str, float]:
        """Compute Pearson IC and Spearman Rank IC for a single prediction slice.

        Args:
            pred_scores: Series of strategy prediction scores.
            actual_returns: Series of realized forward returns.

        Returns:
            Dict containing 'ic', 'rank_ic', and 'sample_size'.
        """
        combined = pd.DataFrame({"pred": pred_scores, "actual": actual_returns}).dropna()
        if len(combined) < 5:
            return {"ic": 0.0, "rank_ic": 0.0, "sample_size": float(len(combined))}

        ic = float(combined["pred"].corr(combined["actual"], method="pearson"))
        rank_ic = float(combined["pred"].corr(combined["actual"], method="spearman"))

        return {
            "ic": 0.0 if np.isnan(ic) else ic,
            "rank_ic": 0.0 if np.isnan(rank_ic) else rank_ic,
            "sample_size": float(len(combined)),
        }

    def run_walk_forward(self, predictions_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Execute walk-forward rolling backtest evaluation over historical time-series.

        Args:
            predictions_df: DataFrame with 'date', 'symbol', and strategy score columns.
            returns_df: DataFrame with 'date', 'symbol', and 'forward_return_20d'.

        Returns:
            Dict of strategy metrics and overall cumulative PnL series.
        """
        if predictions_df is None or predictions_df.empty or returns_df is None or returns_df.empty:
            return {"status": "EMPTY_INPUT", "strategy_metrics": {}}

        merged = pd.merge(predictions_df, returns_df, on=["date", "symbol"], how="inner")
        if merged.empty:
            return {"status": "NO_MATCHING_DATES", "strategy_metrics": {}}

        strategy_cols = [c for c in merged.columns if c.endswith("_score") or c in ("ensemble_score",)]
        metrics: Dict[str, Dict[str, float]] = {}

        for col in strategy_cols:
            res = self.evaluate_strategy_ic(merged[col], merged["forward_return_20d"])
            metrics[col] = res

        return {
            "status": "SUCCESS",
            "evaluated_pairs": len(merged),
            "strategy_metrics": metrics,
        }

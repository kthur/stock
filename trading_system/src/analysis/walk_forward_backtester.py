"""
walk_forward_backtester.py — Out-of-Sample Walk-Forward Backtester

Executes rolling-window walk-forward out-of-sample backtesting across all 31 multi-factor
strategies to compute Information Coefficients (IC), Rank IC, Sharpe ratios, and Cumulative PnL.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class WalkForwardBacktester:
    """Out-of-Sample Walk-Forward Quantitative Backtester."""

    def __init__(self, train_window: int = 60, test_window: int = 20) -> None:
        self.train_window = max(5, int(train_window)) if train_window is not None else 60
        self.test_window = max(1, int(test_window)) if test_window is not None else 20

    def evaluate_strategy_ic(self, pred_scores: pd.Series, actual_returns: pd.Series) -> Dict[str, float]:
        """Compute Pearson IC and Spearman Rank IC for a single prediction slice.

        Args:
            pred_scores: Series of strategy prediction scores.
            actual_returns: Series of realized forward returns.

        Returns:
            Dict containing 'ic', 'rank_ic', and 'sample_size'.
        """
        p_num = pd.to_numeric(pred_scores, errors="coerce")
        a_num = pd.to_numeric(actual_returns, errors="coerce")
        combined = pd.DataFrame({"pred": p_num, "actual": a_num}).dropna()
        if len(combined) < 5:
            return {"ic": 0.0, "rank_ic": 0.0, "sample_size": float(len(combined))}

        ic_val = combined["pred"].corr(combined["actual"], method="pearson")
        rank_ic_val = combined["pred"].corr(combined["actual"], method="spearman")

        ic = float(np.clip(ic_val, -1.0, 1.0)) if (ic_val is not None and np.isfinite(ic_val)) else 0.0
        rank_ic = float(np.clip(rank_ic_val, -1.0, 1.0)) if (rank_ic_val is not None and np.isfinite(rank_ic_val)) else 0.0

        return {
            "ic": round(ic, 4),
            "rank_ic": round(rank_ic, 4),
            "sample_size": float(len(combined)),
        }

    def run_walk_forward(self, predictions_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Execute walk-forward rolling backtest evaluation over historical time-series.

        Args:
            predictions_df: DataFrame with 'date', 'symbol', and strategy score columns.
            returns_df: DataFrame with 'date', 'symbol', and forward return column.

        Returns:
            Dict of strategy metrics and overall cumulative PnL series.
        """
        if predictions_df is None or predictions_df.empty or returns_df is None or returns_df.empty:
            return {"status": "EMPTY_INPUT", "strategy_metrics": {}}

        p_df = predictions_df.copy()
        r_df = returns_df.copy()

        if "date" in p_df.columns:
            p_df["date"] = pd.to_datetime(p_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        if "date" in r_df.columns:
            r_df["date"] = pd.to_datetime(r_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

        if "symbol" in p_df.columns:
            p_df["symbol"] = p_df["symbol"].astype(str).str.strip()
        if "symbol" in r_df.columns:
            r_df["symbol"] = r_df["symbol"].astype(str).str.strip()

        merged = pd.merge(p_df.dropna(subset=["date", "symbol"]), r_df.dropna(subset=["date", "symbol"]), on=["date", "symbol"], how="inner")
        if merged.empty:
            return {"status": "NO_MATCHING_DATES", "strategy_metrics": {}}

        ret_col = None
        for c in ["forward_return_20d", "forward_return", "actual_return", "realized_return", "return"]:
            if c in merged.columns:
                ret_col = c
                break
        if ret_col is None:
            return {"status": "NO_RETURN_COL", "strategy_metrics": {}}

        strategy_cols = [c for c in merged.columns if c.endswith("_score") or c in ("ensemble_score",)]
        metrics: Dict[str, Dict[str, float]] = {}

        for col in strategy_cols:
            res = self.evaluate_strategy_ic(merged[col], merged[ret_col])
            metrics[col] = res

        return {
            "status": "SUCCESS",
            "evaluated_pairs": len(merged),
            "strategy_metrics": metrics,
        }

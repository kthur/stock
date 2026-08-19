"""
index_rebalance.py — Structural Index Rebalance Pre-Positioning Alpha Engine (Strategy 32)

Predicts quarterly/semi-annual index constituent changes (KOSPI 200, KOSDAQ 150, MSCI Korea/World, S&P 500)
and models passive ETF tracking flows (AUM_tracking * delta_w) 15-30 days prior to rebalance effective dates.
"""

from __future__ import annotations

import logging
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from .base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="index_rebalance",
        display_name="Index Rebalance Structural Flow",
        score_column="index_rebalance_score",
        category="event",
        output_file="index_rebalance_predictions.txt"
    )
)
class IndexRebalanceEngine(BaseStrategyEngine):
    """
    Predictive engine for capturing passive index rebalance structural alpha.
    """

    def __init__(self, tracking_aum_krw: float = 40_000_000_000_000.0): # ~40 Trillion KRW tracking KOSPI200/MSCI
        self.tracking_aum_krw = tracking_aum_krw

    def is_near_rebalance_window(self, current_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Checks if current date is within the 45-day pre-positioning window of major index reviews:
          - KOSPI 200 / KOSDAQ 150: June & December (Effective 2nd Friday)
          - MSCI Quarterly: February, May, August, November (Effective last business day)
        """
        today = current_date or datetime.date.today()
        month = today.month

        # Major rebalance months: 2, 5, 6, 8, 11, 12
        is_rebal_season = month in [2, 5, 6, 8, 11, 12]
        is_pre_window = month in [1, 4, 5, 7, 10, 11]

        target_index = "KOSPI200" if month in [5, 6, 11, 12] else "MSCI"
        days_to_rebal = 20 if is_rebal_season else (40 if is_pre_window else 90)

        return {
            "in_window": is_rebal_season or is_pre_window,
            "target_index": target_index,
            "days_to_rebalance": days_to_rebal,
            "phase": "PRE_POSITIONING" if is_pre_window else ("REBALANCE_MONTH" if is_rebal_season else "OFF_SEASON")
        }

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes structural index rebalance momentum score for all universe symbols.
        """
        universe = kwargs.get("universe", kwargs.get("universe_df", None))
        if universe is None or not isinstance(universe, pd.DataFrame) or universe.empty:
            if isinstance(fundamentals_dict, pd.DataFrame):
                universe = fundamentals_dict
            elif isinstance(prices_dict, pd.DataFrame):
                universe = prices_dict
            else:
                return pd.DataFrame(columns=["symbol", "name", "market", "index_rebalance_score", "predicted_flow_krw"])

        df_uni = universe.copy()
        if "symbol" not in df_uni.columns:
            return pd.DataFrame(columns=["symbol", "name", "market", "index_rebalance_score", "predicted_flow_krw"])

        results = []
        rebal_info = self.is_near_rebalance_window()
        is_active_window = rebal_info["in_window"]
        days_to_eff = rebal_info["days_to_rebalance"]

        # Market Cap & Liquidity Ranking
        mcap_col = "market_cap" if "market_cap" in df_uni.columns else ("marcap" if "marcap" in df_uni.columns else None)
        adv_col = "trading_value" if "trading_value" in df_uni.columns else ("adv" if "adv" in df_uni.columns else None)

        if mcap_col and mcap_col in df_uni.columns:
            mcap_series = pd.to_numeric(df_uni[mcap_col], errors="coerce").fillna(0.0)
            mcap_rank_pct = mcap_series.rank(pct=True, ascending=False)
        else:
            mcap_rank_pct = pd.Series(0.5, index=df_uni.index)

        if adv_col and adv_col in df_uni.columns:
            adv_series = pd.to_numeric(df_uni[adv_col], errors="coerce").fillna(0.0)
            adv_rank_pct = adv_series.rank(pct=True, ascending=False)
        else:
            adv_rank_pct = pd.Series(0.5, index=df_uni.index)

        for idx, row in df_uni.iterrows():
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KOSPI"))

            m_rank = float(mcap_rank_pct.loc[idx])
            a_rank = float(adv_rank_pct.loc[idx])

            # High probability candidate for inclusion: Top 5-15% market cap + Top 10% liquidity in non-mega caps
            is_inclusion_candidate = (0.02 <= m_rank <= 0.15) and (a_rank <= 0.20)
            # Exclusion candidate: Lower 30% of current index constituents
            is_exclusion_candidate = (m_rank > 0.60) and (a_rank > 0.50)

            if is_active_window:
                if is_inclusion_candidate:
                    # Imminent inclusion flow boost
                    raw_score = 0.75 + 0.20 * (1.0 - m_rank)
                    predicted_flow = float(self.tracking_aum_krw * 0.005) # ~0.5% weight = 200B KRW
                elif is_exclusion_candidate:
                    # Exclusion passive outflow penalty
                    raw_score = 0.25 - 0.15 * (m_rank - 0.60)
                    predicted_flow = float(-self.tracking_aum_krw * 0.003)
                else:
                    raw_score = 0.50
                    predicted_flow = 0.0
            else:
                raw_score = 0.50
                predicted_flow = 0.0

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "index_rebalance_score": round(float(np.clip(raw_score, 0.0, 1.0)), 4),
                "predicted_flow_krw": round(predicted_flow, 2),
                "rebalance_phase": rebal_info["phase"]
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="index_rebalance_score", ascending=False).reset_index(drop=True)
        return res_df

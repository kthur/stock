"""
vol_target.py — Dynamic Volatility Targeting & Risk Parity Engine (Strategy 22)

Scales portfolio position sizes inversely proportional to asset realized volatility,
targeting a steady annualized portfolio volatility (e.g., 12.0%) across market regimes.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class VolTargetingEngine:
    """Strategy 22: Dynamic Volatility Targeting Engine.

    Calculates volatility-adjusted risk parity score (0% to 100%) for all universe stocks,
    rewarding high Sharpe ratio assets with stable, low realized volatility.
    """

    def __init__(self, target_vol_annual: float = 0.12) -> None:
        self.target_vol_annual = target_vol_annual

    def compute_scores(self, df_prices: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
        """Compute volatility targeting risk parity score for universe symbols.

        Args:
            df_prices: DataFrame of daily Close prices.
            universe: Universe DataFrame containing 'symbol', 'name', 'market'.

        Returns:
            DataFrame with columns ['symbol', 'name', 'market', 'vol_target_score'].
        """
        results: List[Dict[str, Any]] = []
        if df_prices is None or df_prices.empty or universe is None or universe.empty:
            return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])

        # Pivot close prices if needed
        if isinstance(df_prices, pd.DataFrame) and "symbol" in df_prices.columns and "Close" in df_prices.columns:
            close_pivot = df_prices.pivot(index="Date" if "Date" in df_prices.columns else df_prices.index, columns="symbol", values="Close")
        else:
            close_pivot = df_prices

        # Compute 20-day daily returns and realized annualized volatility
        daily_returns = close_pivot.pct_change(1).iloc[-20:]
        realized_vol = daily_returns.std() * np.sqrt(252)

        for _, row in universe.iterrows():
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))

            vol = float(realized_vol.get(sym, np.nan)) if not pd.isna(realized_vol.get(sym, np.nan)) else 0.25
            vol = max(vol, 0.05)  # Floor volatility at 5%

            # Target leverage weight = target_vol / asset_vol
            target_weight = self.target_vol_annual / vol
            # Map target weight (0.2 ~ 2.0) to score (0 ~ 100)
            score = float(np.clip(target_weight * 50.0, 0.0, 100.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "vol_target_score": round(score, 2),
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="vol_target_score", ascending=False).reset_index(drop=True)
        return res_df

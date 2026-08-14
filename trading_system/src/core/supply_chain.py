"""
supply_chain.py — Value Chain & Supply Chain Momentum Engine (Strategy 19)

Computes lead-lag momentum spillover from primary customer companies (e.g., NVIDIA, Apple,
Samsung Electronics, Hyundai Motor) to supplier and equipment vendors with 1-3 day lag.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)

# Key customer-supplier value chain mappings (Symbol -> Lead Market Leaders)
LEAD_CUSTOMER_MAP: Dict[str, List[str]] = {
    # Semiconductor Equipment / Materials -> Customer Leaders
    "005930": ["NVDA", "AAPL", "MSFT"],       # Samsung Electronics -> NVDA/AAPL/MSFT
    "000660": ["NVDA", "AAPL"],               # SK Hynix -> NVDA/AAPL
    "042700": ["005930", "000660"],           # Hanmi Semiconductor -> Samsung / SK Hynix
    "036540": ["005930", "000660"],           # SFA -> Samsung / SK Hynix
    "053800": ["TSLA"],                       # Hyundai Motor -> TSLA
    "006400": ["TSLA", "AAPL"],               # Samsung SDI -> TSLA / AAPL
    "373220": ["TSLA"],                       # LG Energy Solution -> TSLA
    "NVDA": ["AAPL", "MSFT", "GOOGL", "AMZN"],# NVDA -> Tech Giants
    "ASML": ["NVDA", "TSM", "AAPL"],          # ASML -> NVDA/TSM/AAPL
    "AMAT": ["NVDA", "TSM", "INTC"],          # Applied Materials -> NVDA/TSM
    "LRCX": ["NVDA", "TSM", "000660"],        # Lam Research -> NVDA/SK Hynix
}


from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="supply_chain",
        display_name="Supply Chain Lead-Lag",
        score_column="supply_chain_score",
        category="factor",
        output_file="supply_chain_predictions.txt",
        default_regime_weights={
            "BEAR": 0.03, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.05, "BULL_LOW_VOL": 0.04
        },
    )
)
class SupplyChainEngine(BaseStrategyEngine):
    """Strategy 19: Supply Chain Lead-Lag Momentum Engine.

    Calculates spillover momentum score (0% to 100%) for supplier stocks based on
    1D and 3D returns of their key customer/lead market leaders.
    """

    def __init__(self, customer_map: Optional[Dict[str, List[str]]] = None) -> None:
        self.customer_map = customer_map or LEAD_CUSTOMER_MAP

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Compute supply chain lead-lag momentum score for all universe symbols."""
        df_prices = kwargs.get("df_prices", prices_dict)
        universe = kwargs.get("universe", kwargs.get("universe_df", None))

        if universe is None or not isinstance(universe, pd.DataFrame) or universe.empty:
            if isinstance(fundamentals_dict, pd.DataFrame):
                universe = fundamentals_dict
            elif isinstance(prices_dict, pd.DataFrame):
                universe = prices_dict
            else:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        results: List[Dict[str, Any]] = []
        if df_prices is None or universe.empty:
            return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        if isinstance(df_prices, dict):
            if not df_prices:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            close_dict = {}
            for sym, df_p in df_prices.items():
                if df_p is not None and hasattr(df_p, 'empty') and not df_p.empty and "Close" in df_p.columns:
                    c = df_p["Close"]
                    if isinstance(c, pd.DataFrame):
                        c = c.iloc[:, 0]
                    close_dict[sym] = c
            if not close_dict:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            close_pivot = pd.DataFrame(close_dict)
        elif isinstance(df_prices, pd.DataFrame):
            if df_prices.empty:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            if "symbol" in df_prices.columns and "Close" in df_prices.columns:
                close_pivot = df_prices.pivot(index="Date" if "Date" in df_prices.columns else df_prices.index, columns="symbol", values="Close")
            else:
                close_pivot = df_prices
        else:
            return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        # Compute 1D, 3D, and 5D returns for all symbols
        returns_1d = close_pivot.pct_change(1).iloc[-1] if len(close_pivot) >= 2 else pd.Series(dtype=float)
        returns_3d = close_pivot.pct_change(3).iloc[-1] if len(close_pivot) >= 4 else pd.Series(dtype=float)
        returns_5d = close_pivot.pct_change(5).iloc[-1] if len(close_pivot) >= 6 else pd.Series(dtype=float)

        def clean_sym(s: str) -> str:
            raw = s.split(".")[0].strip()
            return raw.zfill(6) if raw.isdigit() else raw

        for _, row in universe.iterrows():
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))
            c_key = clean_sym(sym)

            customers = self.customer_map.get(c_key, self.customer_map.get(sym, []))
            if not customers:
                score = 0.50
            else:
                cust_rets = []
                for c_sym in customers:
                    r1 = float(returns_1d.get(c_sym, 0.0)) if not pd.isna(returns_1d.get(c_sym, np.nan)) else 0.0
                    r3 = float(returns_3d.get(c_sym, 0.0)) if not pd.isna(returns_3d.get(c_sym, np.nan)) else 0.0
                    r5 = float(returns_5d.get(c_sym, 0.0)) if not pd.isna(returns_5d.get(c_sym, np.nan)) else 0.0
                    cust_rets.append(0.50 * r1 + 0.30 * r3 + 0.20 * r5)

                avg_cust_ret = float(np.mean(cust_rets)) if cust_rets else 0.0
                score = float(np.clip(0.50 + avg_cust_ret * 5.0, 0.0, 1.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "supply_chain_score": round(score, 4),
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="supply_chain_score", ascending=False).reset_index(drop=True)
        return res_df

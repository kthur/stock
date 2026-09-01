"""
vol_target.py — Dynamic Volatility Targeting & Risk Parity Engine (Strategy 22)

Scales portfolio position sizes inversely proportional to asset realized volatility,
targeting a steady annualized portfolio volatility (e.g., 12.0%) across market regimes.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="vol_target",
        display_name="Dynamic Volatility Targeting",
        score_column="vol_target_score",
        category="factor",
        output_file="vol_target_predictions.txt",
        default_regime_weights={
            "BEAR": 0.08, "BEAR_HIGH_VOL": 0.12, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.04
        },
    )
)

class VolTargetingEngine(BaseStrategyEngine):
    """Strategy 22: Dynamic Volatility Targeting Engine.

    Calculates volatility-adjusted risk parity score (0% to 100%) for all universe stocks,
    rewarding high Sharpe ratio assets with stable, low realized volatility.
    """

    def __init__(self, target_vol_annual: float = 0.12, config: Optional[Any] = None) -> None:
        self.target_vol_annual = target_vol_annual
        self.config = config

    def _scale_score(self, current_vol: float, target_vol: Optional[float] = None) -> float:
        """
        Scale single-asset volatility score using dynamic logistic transfer.
        """
        t_vol = target_vol if target_vol is not None else self.target_vol_annual
        c_vol = max(float(current_vol), 0.02)
        target_weights = float(t_vol) / c_vol
        vol_ratio = target_weights - 1.0
        return float(np.clip(1.0 / (1.0 + np.exp(-3.0 * np.clip(vol_ratio, -2.0, 2.0))), 0.0, 1.0))

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> Any:
        """Compute volatility targeting risk parity score for universe symbols."""
        if isinstance(prices_dict, pd.DataFrame) and isinstance(fundamentals_dict, dict):
            universe = prices_dict
            df_prices = fundamentals_dict
        else:
            df_prices = kwargs.get("df_prices", prices_dict)
            universe = kwargs.get("universe", kwargs.get("universe_df", None))

        if universe is None or (isinstance(universe, pd.DataFrame) and universe.empty):
            if isinstance(fundamentals_dict, pd.DataFrame) and not fundamentals_dict.empty:
                universe = fundamentals_dict
            elif isinstance(df_prices, dict) and df_prices:
                universe = pd.DataFrame({'symbol': list(df_prices.keys()), 'name': list(df_prices.keys()), 'market': 'ALL'})

        if df_prices is None or universe is None or (isinstance(universe, pd.DataFrame) and universe.empty):
            return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])

        if isinstance(df_prices, dict):
            if not df_prices:
                return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])
            close_dict = {}
            for sym, df_p in df_prices.items():
                if df_p is not None and hasattr(df_p, 'empty') and not df_p.empty:
                    c_col = "Close" if "Close" in df_p.columns else ("close" if "close" in df_p.columns else None)
                    if c_col:
                        c = df_p[c_col]
                        if isinstance(c, pd.DataFrame):
                            c = c.iloc[:, 0]
                        close_dict[sym] = c
            if not close_dict:
                return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])
            close_pivot = pd.DataFrame(close_dict)
        elif isinstance(df_prices, pd.DataFrame):
            if df_prices.empty:
                return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])
            if "symbol" in df_prices.columns and "Close" in df_prices.columns:
                close_pivot = df_prices.pivot(index="Date" if "Date" in df_prices.columns else df_prices.index, columns="symbol", values="Close")
            else:
                close_pivot = df_prices
        else:
            return pd.DataFrame(columns=["symbol", "name", "market", "vol_target_score"])

        # Compute EWMA conditional annualized volatility (RiskMetrics lambda=0.94 / span=20)
        daily_returns = close_pivot.pct_change(1, fill_method=None).tail(60)
        valid_counts = daily_returns.notna().sum(axis=0)

        def _calc_col_var(col: pd.Series) -> float:
            c_clean = col.dropna()
            if len(c_clean) < 15:
                return (0.25 ** 2) / 252.0  # default 25% annual vol
            w = np.exp(-np.arange(len(c_clean))[::-1] / 20.0)
            w /= w.sum()
            return float(np.sum(w * (c_clean.values ** 2)))

        ewma_var = daily_returns.apply(_calc_col_var)
        realized_vol = np.sqrt(ewma_var * 252)
        realized_vol[valid_counts < 20] = 0.25

        # R8-7: Incorporate Parkinson range volatility if High/Low prices are available in df_prices dict
        if isinstance(df_prices, dict):
            for sym in realized_vol.index:
                df_p = df_prices.get(sym)
                if isinstance(df_p, pd.DataFrame) and not df_p.empty:
                    h_col = "High" if "High" in df_p.columns else ("high" if "high" in df_p.columns else None)
                    l_col = "Low" if "Low" in df_p.columns else ("low" if "low" in df_p.columns else None)
                    if h_col and l_col:
                        high_series = pd.to_numeric(df_p[h_col].tail(30), errors='coerce').dropna()
                        low_series = pd.to_numeric(df_p[l_col].tail(30), errors='coerce').dropna()
                        common_idx = high_series.index.intersection(low_series.index)
                        if len(common_idx) >= 15:
                            h_sub, l_sub = np.maximum(high_series.loc[common_idx].values, 1e-8), np.maximum(low_series.loc[common_idx].values, 1e-8)
                            hl_ratio = np.maximum(h_sub / l_sub, 1.0)
                            log_hl_sq = (np.log(hl_ratio) ** 2)
                            parkinson_var = float(np.nanmean(log_hl_sq) / (4.0 * np.log(2.0)))
                            parkinson_vol = np.sqrt(max(0.0, parkinson_var) * 252.0)
                            # Blend 70% Close-to-Close EWMA + 30% Parkinson Range Volatility
                            blended_v = float(0.70 * realized_vol[sym] + 0.30 * parkinson_vol)
                            realized_vol[sym] = float(np.clip(blended_v, 0.02, 5.0)) if np.isfinite(blended_v) else 0.25


        # Fully vectorized computation across all universe symbols with Sharpe-enhanced risk parity
        sym_series = universe["symbol"].astype(str).str.strip()
        vols = sym_series.map(realized_vol).fillna(0.25).clip(lower=0.02)
        inv_vols = 1.0 / vols

        # Incorporate historical return-to-risk efficiency
        ann_returns = (daily_returns.mean(axis=0) * 252.0).reindex(realized_vol.index).fillna(0.0)
        sharpe_raw = ann_returns / np.maximum(realized_vol, 0.05)
        sharpe_series = sym_series.map(sharpe_raw).fillna(0.0).clip(-3.0, 5.0)

        if len(inv_vols) > 1 and inv_vols.std() > 1e-6:
            inv_vol_rank = inv_vols.rank(pct=True).clip(0.02, 0.98)
            sharpe_rank = sharpe_series.rank(pct=True).clip(0.02, 0.98) if sharpe_series.std() > 1e-6 else pd.Series(0.50, index=sym_series.index)
            composite_rank = 0.60 * inv_vol_rank + 0.40 * sharpe_rank
            scores = (0.05 + composite_rank * 0.90).clip(0.0, 1.0).round(4)
            scores = np.where(np.isfinite(scores), scores, 0.50)
        else:
            target_weights = self.target_vol_annual / np.maximum(vols, 0.02)
            vol_ratio = target_weights - 1.0
            scores = (1.0 / (1.0 + np.exp(-3.0 * np.clip(vol_ratio, -2.0, 2.0)))).clip(0.0, 1.0).round(4)
            scores = np.where(np.isfinite(scores), scores, 0.50)

        res_df = pd.DataFrame({
            "symbol": sym_series,
            "name": universe.get("name", sym_series),
            "market": universe.get("market", "KRX"),
            "vol_target_score": pd.to_numeric(pd.Series(scores, index=sym_series.index), errors='coerce').fillna(0.50).clip(0.0, 1.0)
        })

        if not res_df.empty:
            res_df = res_df.sort_values(by="vol_target_score", ascending=False).reset_index(drop=True)
        return res_df

# -*- coding: utf-8 -*-
"""
MacroLiquidityEngine: Global Central Bank Net Liquidity, RRP, US M2, and Cross-Asset Liquidity Stress Engine.
Computes Net Liquidity = Fed Total Assets - TGA - Reverse Repo, Copper/Gold momentum, and Credit Spread Divergence.
"""

import logging
from typing import Dict, Optional, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MacroLiquidityEngine:
    """
    Global Macro Liquidity Index & Cross-Asset Monetary Policy Engine.
    """

    def __init__(self, lookback_window: int = 60):
        self.lookback_window = lookback_window

    def compute_net_liquidity(self,
                              fed_total_assets: Optional[pd.Series] = None,
                              tga_balance: Optional[pd.Series] = None,
                              reverse_repo: Optional[pd.Series] = None) -> Optional[pd.Series]:
        """
        Computes Fed Net Liquidity = Total Assets - TGA - RRP (in Billions USD).
        """
        if fed_total_assets is None or fed_total_assets.empty:
            return None

        net_liq = fed_total_assets.copy()
        if tga_balance is not None and not tga_balance.empty:
            net_liq = net_liq - tga_balance.reindex(net_liq.index).ffill().fillna(0.0)
        if reverse_repo is not None and not reverse_repo.empty:
            net_liq = net_liq - reverse_repo.reindex(net_liq.index).ffill().fillna(0.0)

        return net_liq

    def compute_copper_gold_ratio(self,
                                 copper_prices: pd.Series,
                                 gold_prices: pd.Series) -> pd.Series:
        """
        Computes Dr. Copper to Gold Ratio as a real economic growth / inflation proxy.
        """
        aligned_gold = gold_prices.reindex(copper_prices.index).ffill()
        ratio = copper_prices / np.maximum(aligned_gold, 1e-4)
        return ratio

    def compute_macro_liquidity_score(self,
                                      indicators: Dict[str, Any],
                                      vix: Optional[float] = None,
                                      tnx: Optional[float] = None,
                                      hy_spread: Optional[float] = None) -> float:
        """
        Computes a unified Macro Liquidity Composite Score [0.0, 1.0].
        0.0 = Severe Monetary Squeeze / Liquidity Contraction
        0.5 = Neutral
        1.0 = Highly Accommodative / Global Liquidity Expansion
        """
        score_components = []

        # 1. Net Liquidity Momentum (if series available)
        net_liq_series = indicators.get('net_liquidity')
        if isinstance(net_liq_series, pd.Series) and len(net_liq_series) >= 20:
            liq_chg_20d = float((net_liq_series.iloc[-1] / net_liq_series.iloc[-20]) - 1.0)
            liq_score = 1.0 / (1.0 + np.exp(-30.0 * liq_chg_20d))
            score_components.append(('net_liq', liq_score, 0.35))

        # 2. VIX Volatility Liquidity Stress
        vix_val = float(vix) if vix is not None else float(indicators.get('vix', 20.0))
        # VIX < 15 is liquid, VIX > 35 is illiquid
        vix_liq = float(np.clip(1.0 - (vix_val - 12.0) / (35.0 - 12.0), 0.05, 0.95))
        score_components.append(('vix', vix_liq, 0.25))

        # 3. 10Y Yield (TNX) Stress
        tnx_val = float(tnx) if tnx is not None else float(indicators.get('tnx', 4.0))
        # Sudden spike above 4.5% penalizes liquidity
        tnx_liq = float(np.clip(1.0 - (tnx_val - 3.0) / 3.0, 0.10, 0.90))
        score_components.append(('tnx', tnx_liq, 0.20))

        # 4. Credit Spread (High Yield OAS)
        hy_val = float(hy_spread) if hy_spread is not None else float(indicators.get('hy_spread', 3.5))
        # HY spread < 300bps is healthy, > 600bps is distressed
        hy_liq = float(np.clip(1.0 - (hy_val - 2.5) / 4.0, 0.05, 0.95))
        score_components.append(('hy_spread', hy_liq, 0.20))

        # Weighted composite score
        total_w = sum(w for _, _, w in score_components)
        if total_w <= 0:
            return 0.50

        composite = sum(score * w for _, score, w in score_components) / total_w
        return float(np.clip(composite, 0.05, 0.95))

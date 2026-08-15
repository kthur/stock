"""
Level 2 / Level 3 Limit Order Book (LOB) Queue Dynamics & OBI Calculator Module
Calculates multi-level Order Book Imbalance (OBI) and Weighted Micro-Price (P_micro) for micro-trend breakout signals.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LimitOrderBookCalculator:
    """
    Level 2 / Level 3 Limit Order Book Dynamics Calculator.
    Computes OBI_K and Micro-Price P_micro to detect sub-second order book imbalances.
    """

    def __init__(self, depth_levels: int = 5, decay_lambda: float = 0.5):
        self.depth_levels = depth_levels
        self.decay_lambda = decay_lambda

    def calculate_micro_price(self, bid_price_1: float, bid_vol_1: float, ask_price_1: float, ask_vol_1: float) -> float:
        """
        Calculates Micro-Price: P_micro = (V_a^1 * P_b^1 + V_b^1 * P_a^1) / (V_b^1 + V_a^1)
        """
        total_vol = bid_vol_1 + ask_vol_1
        if total_vol <= 0:
            return 0.5 * (bid_price_1 + ask_price_1)
        micro_price = (ask_vol_1 * bid_price_1 + bid_vol_1 * ask_price_1) / total_vol
        return float(micro_price)

    def calculate_obi(
        self,
        bids: List[Dict[str, float]],
        asks: List[Dict[str, float]]
    ) -> float:
        """
        Calculates K-level Order Book Imbalance (OBI_K):
        OBI_K = sum(w_i * (V_b^i - V_a^i)) / sum(w_i * (V_b^i + V_a^i))
        where w_i = exp(-lambda * i)
        """
        if not bids or not asks:
            return 0.0

        n_levels = min(len(bids), len(asks), self.depth_levels)
        if n_levels == 0:
            return 0.0

        numerator = 0.0
        denominator = 0.0

        for i in range(n_levels):
            w = np.exp(-self.decay_lambda * i)
            v_b = bids[i].get("volume", 0.0)
            v_a = asks[i].get("volume", 0.0)

            numerator += w * (v_b - v_a)
            denominator += w * (v_b + v_a)

        if denominator <= 0:
            return 0.0

        obi_val = numerator / denominator
        return float(np.clip(obi_val, -1.0, 1.0))

    def evaluate_lob_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluates a complete LOB snapshot and returns metrics.
        """
        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        if not bids or not asks:
            return {"obi": 0.0, "micro_price": 0.0, "spread": 0.0}

        # Safe sorting: bids descending by price, asks ascending by price
        sorted_bids = sorted(bids, key=lambda x: x.get("price", 0.0), reverse=True)
        sorted_asks = sorted(asks, key=lambda x: x.get("price", 0.0))

        p_b1 = sorted_bids[0].get("price", 0.0)
        v_b1 = sorted_bids[0].get("volume", 0.0)
        p_a1 = sorted_asks[0].get("price", 0.0)
        v_a1 = sorted_asks[0].get("volume", 0.0)

        micro = self.calculate_micro_price(p_b1, v_b1, p_a1, v_a1)
        obi = self.calculate_obi(sorted_bids, sorted_asks)
        spread = max(0.0, p_a1 - p_b1)

        return {
            "obi": round(obi, 4),
            "micro_price": round(micro, 2),
            "spread": round(spread, 2)
        }

"""
Level 2 / Level 3 Limit Order Book (LOB) Queue Dynamics & OBI Calculator Module
Calculates multi-level Order Book Imbalance (OBI) and Weighted Micro-Price (P_micro) for micro-trend breakout signals.
"""

import logging
import numpy as np
from typing import Dict, List, Any

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
        try:
            pb = float(bid_price_1) if np.isfinite(float(bid_price_1)) else 0.0
            vb = max(0.0, float(bid_vol_1)) if np.isfinite(float(bid_vol_1)) else 0.0
            pa = float(ask_price_1) if np.isfinite(float(ask_price_1)) else 0.0
            va = max(0.0, float(ask_vol_1)) if np.isfinite(float(ask_vol_1)) else 0.0
        except (ValueError, TypeError):
            return 0.0

        total_vol = vb + va
        if total_vol <= 0 or not np.isfinite(total_vol):
            mid = 0.5 * (pb + pa)
            return float(mid) if np.isfinite(mid) else 0.0
        micro_price = (va * pb + vb * pa) / total_vol
        return float(micro_price) if np.isfinite(micro_price) else float(0.5 * (pb + pa))

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
            try:
                v_b = max(0.0, float(bids[i].get("volume", 0.0) or 0.0))
            except (ValueError, TypeError):
                v_b = 0.0
            try:
                v_a = max(0.0, float(asks[i].get("volume", 0.0) or 0.0))
            except (ValueError, TypeError):
                v_a = 0.0

            if np.isnan(v_b) or np.isinf(v_b):
                v_b = 0.0
            if np.isnan(v_a) or np.isinf(v_a):
                v_a = 0.0

            numerator += w * (v_b - v_a)
            denominator += w * (v_b + v_a)

        if denominator <= 0:
            return 0.0

        obi_val = numerator / denominator
        return float(np.clip(obi_val, -1.0, 1.0))

    def evaluate_lob_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluates a complete LOB snapshot and returns metrics including multi-depth OBI.
        """
        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        if not bids or not asks:
            return {
                "obi": 0.0,
                "obi_1": 0.0,
                "obi_5": 0.0,
                "obi_10": 0.0,
                "micro_price": 0.0,
                "spread": 0.0
            }

        # Safe sorting: bids descending by price, asks ascending by price
        sorted_bids = sorted(bids, key=lambda x: float(x.get("price", 0.0) or 0.0), reverse=True)
        sorted_asks = sorted(asks, key=lambda x: float(x.get("price", 0.0) or 0.0))

        p_b1 = float(sorted_bids[0].get("price", 0.0) or 0.0)
        v_b1 = float(sorted_bids[0].get("volume", 0.0) or 0.0)
        p_a1 = float(sorted_asks[0].get("price", 0.0) or 0.0)
        v_a1 = float(sorted_asks[0].get("volume", 0.0) or 0.0)

        micro = self.calculate_micro_price(p_b1, v_b1, p_a1, v_a1)
        obi_1 = self._calc_obi_k(sorted_bids, sorted_asks, k=1)
        obi_5 = self._calc_obi_k(sorted_bids, sorted_asks, k=5)
        obi_10 = self._calc_obi_k(sorted_bids, sorted_asks, k=min(10, max(len(sorted_bids), len(sorted_asks))))
        spread = max(0.0, p_a1 - p_b1)

        return {
            "obi": round(obi_10, 4),
            "obi_1": round(obi_1, 4),
            "obi_5": round(obi_5, 4),
            "obi_10": round(obi_10, 4),
            "micro_price": round(micro, 4),
            "spread": round(spread, 4)
        }

    def _calc_obi_k(self, bids: List[Dict[str, float]], asks: List[Dict[str, float]], k: int) -> float:
        """Helper to calculate OBI for top-k levels."""
        n_levels = min(len(bids), len(asks), k)
        if n_levels == 0:
            return 0.0
        numerator = 0.0
        denominator = 0.0
        for i in range(n_levels):
            w = np.exp(-self.decay_lambda * i)
            vb = max(0.0, float(bids[i].get("volume", 0.0) or 0.0))
            va = max(0.0, float(asks[i].get("volume", 0.0) or 0.0))
            numerator += w * (vb - va)
            denominator += w * (vb + va)
        return float(np.clip(numerator / denominator, -1.0, 1.0)) if denominator > 0 else 0.0


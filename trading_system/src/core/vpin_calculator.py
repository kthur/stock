"""
Volume-Synchronized Probability of Toxicity (VPIN) Calculator Module
Estimates real-time adverse selection and toxic flow (BVC bulk volume classification) for automated risk gating.
"""

import logging
import numpy as np
from typing import Dict, Any
from scipy.stats import norm

logger = logging.getLogger(__name__)


class VPINCalculator:
    """
    Volume-Synchronized Probability of Toxicity (VPIN) Calculator.
    Clusters trades into volume buckets and estimates probability of informed trading.
    """

    def __init__(self, num_buckets: int = 50, window_size: int = 20):
        self.num_buckets = num_buckets
        self.window_size = window_size

    def compute_vpin(self, trade_prices: np.ndarray, trade_volumes: np.ndarray, bucket_volume: float) -> float:
        """
        Calculates VPIN value over trade price/volume arrays.
        VPIN = sum(|V_i^B - V_i^S|) / (n * V)
        """
        prices = np.asarray(trade_prices, dtype=np.float64)
        volumes = np.asarray(trade_volumes, dtype=np.float64)

        min_len = min(len(prices), len(volumes))
        if min_len < 2 or bucket_volume <= 0:
            return 0.0

        prices = prices[:min_len]
        volumes = volumes[:min_len]

        # Replace non-finite values
        prices = np.nan_to_num(prices, nan=1.0, posinf=1.0, neginf=1.0)
        volumes = np.nan_to_num(volumes, nan=0.0, posinf=0.0, neginf=0.0)

        price_diffs = np.diff(prices)
        std_diff = float(np.std(price_diffs))
        if std_diff <= 1e-8 or np.isnan(std_diff) or np.isinf(std_diff):
            std_diff = 1e-4
        z_scores = np.clip(price_diffs / std_diff, -8.0, 8.0)

        # Bulk Volume Classification (BVC)
        buy_ratios = norm.cdf(z_scores)
        sell_ratios = 1.0 - buy_ratios

        v_b = volumes[1:] * buy_ratios
        v_s = volumes[1:] * sell_ratios

        total_vol = float(np.sum(volumes[1:]))
        if total_vol <= 0:
            return 0.0

        # Volume Bucketing Accumulation when total volume >= bucket_volume
        if total_vol >= bucket_volume and bucket_volume > 0:
            bucket_imbalances = []
            cur_b = 0.0
            cur_s = 0.0
            cur_vol = 0.0
            for vb, vs in zip(v_b, v_s):
                step_v = vb + vs
                if step_v <= 0:
                    continue
                cur_b += vb
                cur_s += vs
                cur_vol += step_v
                while cur_vol >= bucket_volume:
                    ratio = bucket_volume / max(1e-12, cur_vol)
                    bucket_imbalances.append(abs(cur_b * ratio - cur_s * ratio))
                    cur_b -= cur_b * ratio
                    cur_s -= cur_s * ratio
                    cur_vol -= bucket_volume
            if bucket_imbalances:
                vpin_val = np.sum(bucket_imbalances) / max(1e-12, float(len(bucket_imbalances) * bucket_volume))
                return float(np.clip(vpin_val, 0.0, 1.0)) if np.isfinite(vpin_val) else 0.0

        imbalances = np.abs(v_b - v_s)
        vpin_val = np.sum(imbalances) / max(1e-12, float(total_vol))
        return float(np.clip(vpin_val, 0.0, 1.0)) if np.isfinite(vpin_val) else 0.0

    def evaluate_toxicity_risk(self, vpin_score: float, threshold: float = 0.75) -> Dict[str, Any]:
        """
        Determines whether VPIN toxicity exceeds risk threshold.
        """
        safe_score = float(np.clip(vpin_score, 0.0, 1.0)) if np.isfinite(vpin_score) else 0.0
        is_toxic = bool(safe_score >= threshold)
        action = "HALT_PASSIVE_ORDERS" if is_toxic else "NORMAL"
        return {
            "vpin_score": round(safe_score, 4),
            "threshold": threshold,
            "is_toxic": is_toxic,
            "recommended_action": action
        }

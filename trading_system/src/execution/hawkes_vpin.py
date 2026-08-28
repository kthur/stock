"""
hawkes_vpin.py — Hawkes Process Order Flow Toxicity (VPIN) Safety Gate Engine

Models mutually-exciting trade arrivals via Hawkes point processes and calculates
Volume-Synchronized Probability of Toxicity (VPIN) to cancel passive resting limit
orders ahead of predatory institutional sweeps, eliminating limit order adverse selection.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, List, Any, Union

logger = logging.getLogger(__name__)


class HawkesVPINToxicityGate:
    """
    Hawkes Process and VPIN Order Flow Toxicity Microstructure Safety Gate.
    """

    def __init__(
        self,
        vpin_toxic_threshold: float = 0.65,  # VPIN > 0.65 indicates imminent aggressive sweep
        hawkes_alpha: float = 0.60,         # Self-excitation parameter
        hawkes_beta: float = 1.20,          # Decay rate
        base_intensity_mu: float = 0.15      # Baseline arrival intensity
    ):
        self.vpin_threshold = vpin_toxic_threshold
        self.alpha = hawkes_alpha
        self.beta = hawkes_beta
        self.mu = base_intensity_mu

    def compute_vpin(
        self,
        buy_volumes: Union[List[float], np.ndarray],
        sell_volumes: Union[List[float], np.ndarray],
        num_buckets: int = 50
    ) -> float:
        """
        Calculates Volume-Synchronized Probability of Toxicity (VPIN):
        VPIN = sum_tau |V_tau^B - V_tau^S| / (N * V_bucket)
        """
        b_vols = np.nan_to_num(np.asarray(buy_volumes, dtype=np.float64), nan=0.0)
        s_vols = np.nan_to_num(np.asarray(sell_volumes, dtype=np.float64), nan=0.0)

        N = min(len(b_vols), len(s_vols))
        if N == 0:
            return 0.50

        # Volume imbalance per bucket
        imbalances = np.abs(b_vols[:N] - s_vols[:N])
        total_vol = np.sum(b_vols[:N] + s_vols[:N])

        if total_vol <= 0:
            return 0.50

        vpin = float(np.sum(imbalances) / total_vol)
        return float(np.clip(vpin, 0.0, 1.0))

    def evaluate_hawkes_intensity(
        self,
        event_timestamps_seconds: Union[List[float], np.ndarray],
        current_time_seconds: float
    ) -> float:
        """
        Evaluates Hawkes process trade intensity at current time:
        lambda(t) = mu_0 + sum_{t_i < t} alpha * exp(-beta * (t - t_i))
        """
        t_events = np.asarray(event_timestamps_seconds, dtype=np.float64)
        past_events = t_events[t_events < current_time_seconds]

        if len(past_events) == 0:
            return float(self.mu)

        dt = current_time_seconds - past_events
        # Exponential decaying excitation
        excitations = self.alpha * np.exp(-self.beta * np.maximum(0.0, dt))
        total_intensity = self.mu + np.sum(excitations)
        return float(total_intensity)

    def evaluate_order_flow_toxicity(
        self,
        buy_volumes: Union[List[float], np.ndarray],
        sell_volumes: Union[List[float], np.ndarray],
        order_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates real-time toxicity and returns adaptive OMS routing directives:
        - If toxic (VPIN > 0.65), cancel passive midpoint pegs and switch to DEFENSIVE_VWAP.
        - If benign (VPIN <= 0.65), proceed with passive spread capture (MIDPOINT_PEG).
        """
        vpin = self.compute_vpin(buy_volumes, sell_volumes)
        is_toxic = (vpin >= self.vpin_threshold)

        orig_strategy = str(order_plan.get("execution_strategy", "MIDPOINT_PEG"))

        if is_toxic:
            # Toxic flow detected: switch away from passive pegging to avoid adverse selection
            recommended_strategy = "DEFENSIVE_TWAP" if "TWAP" in orig_strategy else "DEFENSIVE_VWAP"
            cancel_passive_peg = True
            spread_penalty_bps = 8.0 # Additional protective buffer
        else:
            recommended_strategy = orig_strategy
            cancel_passive_peg = False
            spread_penalty_bps = 0.0

        return {
            "vpin": round(vpin, 4),
            "is_toxic_flow": is_toxic,
            "cancel_passive_peg": cancel_passive_peg,
            "recommended_strategy": recommended_strategy,
            "spread_penalty_bps": spread_penalty_bps,
            "original_strategy": orig_strategy
        }

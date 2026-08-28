# -*- coding: utf-8 -*-
"""
AdaptiveOrderRouter: L2 Orderbook Imbalance (OBI) & Microstructure Adaptive Slicing Router.
Optimizes execution tranches based on real-time bid/ask depth imbalance and adverse selection risk.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)


class AdaptiveOrderRouter:
    """
    Smart Order Routing & Slicing Engine incorporating L2 Orderbook Imbalance (OBI).
    """

    def __init__(self,
                 default_tranches: int = 5,
                 min_tranche_size: float = 100_000.0,
                 risk_aversion: float = 1e-6):
        self.default_tranches = default_tranches
        self.min_tranche_size = min_tranche_size
        self.risk_aversion = risk_aversion

    @staticmethod
    def compute_orderbook_imbalance(
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        depth_levels: int = 5
    ) -> float:
        """
        Computes Orderbook Imbalance (OBI) in [-1.0, +1.0]:
        OBI = (Sum(Bid_Vol) - Sum(Ask_Vol)) / (Sum(Bid_Vol) + Sum(Ask_Vol))
        bids: [(price, volume), ...] sorted descending by price
        asks: [(price, volume), ...] sorted ascending by price
        """
        if not bids and not asks:
            return 0.0

        bid_vol = sum(v for _, v in bids[:depth_levels]) if bids else 0.0
        ask_vol = sum(v for _, v in asks[:depth_levels]) if asks else 0.0
        total_vol = bid_vol + ask_vol

        if total_vol <= 1e-8:
            return 0.0

        obi = (bid_vol - ask_vol) / total_vol
        return float(np.clip(obi, -1.0, 1.0))

    def generate_adaptive_schedule(
        self,
        symbol: str,
        total_quantity: int,
        side: str = 'BUY',
        obi: float = 0.0,
        volatility_20d: float = 0.02,
        num_tranches: Optional[int] = None,
        duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Generates an adaptive tranche schedule adjusted for Orderbook Imbalance:
        - If BUY and OBI > +0.30 (strong buy pressure): front-load tranches to avoid price runup.
        - If BUY and OBI < -0.30 (heavy sell liquidity): back-load or pace evenly to capture passive fills.
        """
        if total_quantity <= 0:
            return []

        k_tranches = num_tranches or self.default_tranches
        k_tranches = max(1, min(k_tranches, 20))

        if k_tranches == 1:
            return [{
                'tranche': 1,
                'shares': total_quantity,
                'weight': 1.0,
                'delay_sec': 0
            }]

        side_upper = side.upper()
        # Urgency adjustment factor derived from OBI
        if side_upper == 'BUY':
            urgency_shift = obi * 0.50  # Positive OBI increases urgency for BUY
        else:
            urgency_shift = -obi * 0.50 # Negative OBI increases urgency for SELL

        # Base hyperbolic Almgren-Chriss decaying weights
        t_steps = np.linspace(0.1, 1.0, k_tranches)
        base_decay = np.exp(-1.5 * t_steps)

        # Modulate by urgency shift
        if urgency_shift > 0.10:
            # Front-load
            adjusted_weights = base_decay * (1.0 + urgency_shift * (1.0 - t_steps))
        elif urgency_shift < -0.10:
            # Back-load / smooth out
            adjusted_weights = base_decay * (1.0 + abs(urgency_shift) * t_steps)
        else:
            adjusted_weights = base_decay

        # Normalize weights
        norm_weights = adjusted_weights / np.sum(adjusted_weights)

        # Allocate shares
        allocated_shares = np.floor(norm_weights * total_quantity).astype(int)
        remaining = total_quantity - int(np.sum(allocated_shares))
        # Add remainder to first tranche
        if remaining > 0:
            allocated_shares[0] += remaining

        interval_sec = int((duration_minutes * 60) / k_tranches)
        schedule = []
        for idx, shares in enumerate(allocated_shares):
            if shares <= 0:
                continue
            schedule.append({
                'tranche': idx + 1,
                'shares': int(shares),
                'weight': float(shares / total_quantity),
                'delay_sec': idx * interval_sec
            })

        return schedule

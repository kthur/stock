"""
src/risk/delta_beta_hedge.py
Dynamic Delta & Beta Neutral Inverse Hedge Engine.

Calculates portfolio Market Beta and determines optimal Inverse ETF allocation
(KODEX 200 선물인버스2X / ProShares Short S&P500) to cap MDD under 5% during
severe or bear market regimes (BEAR_HIGH_VOL / CRISIS_ACTIVE / CRISIS_SEVERE).
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DeltaBetaHedgeEngine:
    """
    Dynamic Delta & Beta Neutral Inverse Hedge Engine.
    """

    def __init__(self, config=None):
        self.config = config

    def calculate_optimal_hedge_allocation(
        self,
        portfolio_weights: Dict[str, float],
        symbol_betas: Dict[str, float],
        crisis_level: str = "NONE",
        regime: str = "BULL_LOW_VOL"
    ) -> Dict[str, Any]:
        """
        Calculates optimal Inverse ETF hedge allocation to neutralize portfolio market beta.

        Returns:
            {
                'portfolio_beta': float,
                'target_beta': float,
                'hedge_etf_symbol': str,
                'hedge_weight': float,
                'net_asset_weights': Dict[str, float]
            }
        """
        if not portfolio_weights:
            return {
                'portfolio_beta': 0.0,
                'target_beta': 0.0,
                'hedge_etf_symbol': '252670.KS',
                'hedge_weight': 0.0,
                'net_asset_weights': {}
            }

        # 1. Compute Portfolio Market Beta
        port_beta = sum(w * symbol_betas.get(sym, 1.0) for sym, w in portfolio_weights.items())

        # 2. Determine Target Portfolio Beta based on Crisis & Regime
        target_beta = port_beta
        hedge_weight = 0.0

        if crisis_level in ["SEVERE", "ACTIVE"] or regime in ["BEAR_HIGH_VOL", "BEAR"]:
            # Neutralize portfolio beta down to 0.0 ~ 0.20
            target_beta = 0.0 if crisis_level == "SEVERE" else 0.20
            beta_reduction = port_beta - target_beta
            
            if beta_reduction > 0.0:
                # Assuming 2X Inverse ETF (e.g., KODEX 200 선물인버스2X - 252670.KS) with Beta = -2.0
                inverse_beta = -2.0
                hedge_weight = float(np.clip(beta_reduction / abs(inverse_beta), 0.0, 0.35))

        # 3. Rescale asset weights to make room for Hedge ETF
        scale = 1.0 - hedge_weight
        net_asset_weights = {sym: float(w * scale) for sym, w in portfolio_weights.items()}
        
        hedge_etf = '252670.KS'  # KODEX 200 선물인버스2X
        if hedge_weight > 0.0:
            net_asset_weights[hedge_etf] = hedge_weight
            logger.info(f"[DYNAMIC HEDGE ENGINE] Active Beta Hedge: Port Beta={port_beta:.2f} -> Target={target_beta:.2f}, Allocated {hedge_weight*100:.1f}% to {hedge_etf}")

        return {
            'portfolio_beta': float(port_beta),
            'target_beta': float(target_beta),
            'hedge_etf_symbol': hedge_etf,
            'hedge_weight': float(hedge_weight),
            'net_asset_weights': net_asset_weights
        }

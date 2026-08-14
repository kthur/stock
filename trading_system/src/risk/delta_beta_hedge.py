"""
src/risk/delta_beta_hedge.py
Dynamic Delta & Beta Neutral Inverse Hedge Engine.

Calculates portfolio Market Beta and determines optimal Inverse ETF allocation
(KODEX 200 선물인버스2X / ProShares Short S&P500) to cap MDD under 5% during
severe or bear market regimes (BEAR_HIGH_VOL / CRISIS_ACTIVE / CRISIS_SEVERE).
"""

import logging
from typing import Dict, Any
import numpy as np

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

        # 1. Compute Portfolio Market Beta with vectorized NumPy operations
        valid_items = {sym: w for sym, w in portfolio_weights.items() if w is not None and np.isfinite(w)}
        if not valid_items:
            return {
                'portfolio_beta': 0.0,
                'target_beta': 0.0,
                'hedge_etf_symbol': '252670.KS',
                'hedge_weight': 0.0,
                'net_asset_weights': {}
            }

        symbols = list(valid_items.keys())
        weights_arr = np.array([valid_items[s] for s in symbols], dtype=np.float64)
        total_w = float(np.sum(weights_arr))
        if total_w > 0:
            weights_arr /= total_w
        norm_weights = dict(zip(symbols, weights_arr))

        betas_arr = np.array([symbol_betas.get(s, 1.0) if (symbol_betas and np.isfinite(symbol_betas.get(s, 1.0))) else 1.0 for s in symbols], dtype=np.float64)
        port_beta = float(np.dot(weights_arr, betas_arr))

        # Determine portfolio primary market (KRX vs US)
        kr_count = sum(1 for sym in symbols if str(sym).endswith('.KS') or str(sym).endswith('.KQ') or str(sym).isdigit())
        us_count = len(symbols) - kr_count
        is_us_portfolio = us_count > kr_count

        hedge_etf = 'SH' if is_us_portfolio else '252670.KS'
        inverse_beta = -1.0 if is_us_portfolio else -2.0

        # 2. Determine Target Portfolio Beta based on Crisis & Regime
        target_beta = port_beta
        hedge_weight = 0.0

        if crisis_level in ["SEVERE", "ACTIVE"] or regime in ["BEAR_HIGH_VOL", "BEAR"]:
            target_beta = 0.0 if crisis_level == "SEVERE" else 0.20
            beta_reduction = port_beta - target_beta

            if beta_reduction > 0.0 and (port_beta - inverse_beta) > 1e-6:
                raw_hedge_w = (port_beta - target_beta) / (port_beta - inverse_beta)
                # Dynamic Beta Hedging Booster: Cap up to 40% in severe crisis
                max_hedge_cap = 0.40 if crisis_level == "SEVERE" else 0.35
                hedge_weight = float(np.clip(raw_hedge_w, 0.0, max_hedge_cap))

        # 3. Rescale asset weights to make room for Hedge ETF
        scale = 1.0 - hedge_weight
        net_asset_weights = {sym: float(w * scale) for sym, w in norm_weights.items()}

        if hedge_weight > 0.0:
            net_asset_weights[hedge_etf] = float(net_asset_weights.get(hedge_etf, 0.0) + hedge_weight)
            logger.info(f"[DYNAMIC HEDGE ENGINE] Active Beta Hedge ({'US' if is_us_portfolio else 'KR'}): Port Beta={port_beta:.2f} -> Target={target_beta:.2f}, Allocated {hedge_weight*100:.1f}% to {hedge_etf}")

        return {
            'portfolio_beta': float(port_beta),
            'target_beta': float(target_beta),
            'hedge_etf_symbol': hedge_etf,
            'hedge_weight': float(hedge_weight),
            'net_asset_weights': net_asset_weights
        }

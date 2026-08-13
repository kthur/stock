"""
Smart Order Router (SOR) Module
Aggregates KRX Nextrade (NXT) ATS and US Lit/Dark pool liquidity to minimize execution slippage and market impact.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SmartOrderRouter:
    """
    Smart Order Routing (SOR) Optimization Engine.
    Splits order quantity Q across venues m=1..M to minimize: sum(q_m * P_m + Fee_m(q_m) + Impact_m(q_m))
    """

    def __init__(self):
        pass

    def route_order(
        self,
        symbol: str,
        action: str,
        total_quantity: int,
        venues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Routes total_quantity across available venues (Lit exchanges, ATS, Dark pools).

        Venue dict structure:
        {"venue_id": "NXT", "ask_price": 70000.0, "ask_vol": 500, "fee_bps": -0.5, "impact_coeff": 0.3}
        """
        if total_quantity <= 0 or not venues:
            return []

        remaining_qty = total_quantity
        allocations = []

        # Sort venues by effective price (price + fee)
        def venue_key(v):
            p = v.get("ask_price", 1e9) if action == "BUY" else -v.get("bid_price", 0.0)
            fee = v.get("fee_bps", 0.0) / 10000.0 * p
            return p + fee

        sorted_venues = sorted(venues, key=venue_key)

        for v in sorted_venues:
            if remaining_qty <= 0:
                break

            v_id = v.get("venue_id", "PRIMARY")
            avail_vol = v.get("ask_vol", remaining_qty) if action == "BUY" else v.get("bid_vol", remaining_qty)
            price = v.get("ask_price", 0.0) if action == "BUY" else v.get("bid_price", 0.0)

            alloc_qty = min(remaining_qty, avail_vol)
            if alloc_qty > 0:
                allocations.append({
                    "venue_id": v_id,
                    "symbol": symbol,
                    "action": action,
                    "allocated_quantity": alloc_qty,
                    "target_price": price
                })
                remaining_qty -= alloc_qty

        # Allocate any residual to primary venue
        if remaining_qty > 0 and sorted_venues:
            primary_v = sorted_venues[0]
            allocations.append({
                "venue_id": primary_v.get("venue_id", "PRIMARY"),
                "symbol": symbol,
                "action": action,
                "allocated_quantity": remaining_qty,
                "target_price": primary_v.get("ask_price", 0.0)
            })

        return allocations

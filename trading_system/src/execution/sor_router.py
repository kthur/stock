"""
Smart Order Router (SOR) Module
Aggregates KRX Nextrade (NXT) ATS and US Lit/Dark pool liquidity to minimize execution slippage and market impact.
"""

import logging
from typing import Dict, List, Any

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
        import math
        q_tot = max(0, int(total_quantity)) if total_quantity is not None else 0
        if q_tot <= 0 or not venues:
            return []

        act = str(action).strip().upper()
        is_buy = act == "BUY"
        clean_symbol = str(symbol).strip()

        remaining_qty = q_tot
        allocations = []

        valid_venues = [v for v in venues if isinstance(v, dict)]
        if not valid_venues:
            return []

        # Helper to parse finite float
        def _get_float(d: dict, key: str, default: float) -> float:
            try:
                val = float(d.get(key, default))
                return val if math.isfinite(val) else default
            except (ValueError, TypeError):
                return default

        # Helper to parse finite int vol
        def _get_vol(d: dict, key: str, default: int) -> int:
            try:
                val = float(d.get(key, default))
                return max(0, int(val)) if math.isfinite(val) else default
            except (ValueError, TypeError):
                return default

        # Sort venues by effective price (price + fee)
        def venue_key(v):
            if is_buy:
                p = _get_float(v, "ask_price", 1e9)
                fee = (_get_float(v, "fee_bps", 0.0) / 10000.0) * p
                return p + fee
            else:
                p = _get_float(v, "bid_price", 0.0)
                fee = (_get_float(v, "fee_bps", 0.0) / 10000.0) * p
                return -(p - fee)

        sorted_venues = sorted(valid_venues, key=venue_key)

        for v in sorted_venues:
            if remaining_qty <= 0:
                break

            v_id = str(v.get("venue_id") or "PRIMARY")
            avail_vol = _get_vol(v, "ask_vol" if is_buy else "bid_vol", remaining_qty)
            price = _get_float(v, "ask_price" if is_buy else "bid_price", 0.0)

            alloc_qty = min(remaining_qty, avail_vol)
            if alloc_qty > 0:
                allocations.append({
                    "venue_id": v_id,
                    "symbol": clean_symbol,
                    "action": act,
                    "allocated_quantity": alloc_qty,
                    "target_price": max(0.0, price)
                })
                remaining_qty -= alloc_qty

        # Allocate any residual to primary venue
        if remaining_qty > 0 and sorted_venues:
            primary_v = next((v for v in sorted_venues if v.get("is_primary") or str(v.get("venue_id", "")).upper() in ["PRIMARY", "KRX", "NYSE", "NASDAQ"]), sorted_venues[0])
            p_id = str(primary_v.get("venue_id") or "PRIMARY")
            fallback_price = _get_float(primary_v, "ask_price" if is_buy else "bid_price", 0.0)

            # Merge into existing allocation if primary venue was already partially allocated
            merged = False
            for alloc in allocations:
                if alloc["venue_id"] == p_id:
                    alloc["allocated_quantity"] += remaining_qty
                    merged = True
                    break
            if not merged:
                allocations.append({
                    "venue_id": p_id,
                    "symbol": clean_symbol,
                    "action": act,
                    "allocated_quantity": remaining_qty,
                    "target_price": max(0.0, fallback_price)
                })

        return allocations

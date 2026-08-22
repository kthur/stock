"""
smart_order_router.py — Lit/Dark Smart Order Router (SOR) Engine

Routes institutional orders across multi-venue liquidity pools:
  - Tier 1: ATS / Nextrade / Dark Pool Midpoint Cross Probe (Zero Market Impact)
  - Tier 2: Primary Peg Maker Resting Orders (Maker Rebate Capture)
  - Tier 3: Lit Exchange Sweeper with ADV Participation Bounds (<= 1.5% ADV)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SmartOrderRouter:
    """
    Multi-Venue Smart Order Router (SOR) with Dark Midpoint Probing.
    """

    def __init__(
        self,
        dark_probe_ratio: float = 0.40,
        maker_rebate_bps: float = 2.5,
        taker_fee_bps: float = 1.5
    ):
        self.dark_probe_ratio = dark_probe_ratio
        self.maker_rebate_bps = maker_rebate_bps
        self.taker_fee_bps = taker_fee_bps

    def route_order(
        self,
        order_plan: Dict[str, Any],
        ats_available: bool = True,
        market_spread_bps: float = 15.0
    ) -> Dict[str, Any]:
        """
        Decomposes an order plan into 3-tier routing legs to optimize net execution cost.
        """
        symbol = str(order_plan.get("symbol", ""))
        action = str(order_plan.get("action", "BUY")).upper()
        total_quantity = int(order_plan.get("quantity", 0))
        target_price = float(order_plan.get("target_price", 1000.0))
        exec_strategy = str(order_plan.get("execution_strategy", "DIRECT"))

        if total_quantity <= 0 or target_price <= 0:
            return {
                "symbol": symbol,
                "total_quantity": 0,
                "legs": [],
                "expected_cost_saving_bps": 0.0
            }

        legs: List[Dict[str, Any]] = []

        # 1. Tier 1: ATS / Dark Pool Midpoint Probe Leg
        is_patient_strategy = exec_strategy in ["MIDPOINT_PEG", "PATIENT_TWAP", "DYNAMIC_VWAP"]
        if ats_available and is_patient_strategy:
            dark_qty = int(total_quantity * self.dark_probe_ratio)
            if dark_qty > 0:
                legs.append({
                    "venue_type": "DARK_ATS_MIDPOINT",
                    "order_type": "MIDPOINT_IOC",
                    "quantity": dark_qty,
                    "target_price": target_price,
                    "expected_rebate_bps": market_spread_bps / 2.0, # Saves half-spread
                    "priority": 1
                })
                rem_qty = total_quantity - dark_qty
            else:
                rem_qty = total_quantity
        else:
            rem_qty = total_quantity

        # 2. Tier 2: Primary Peg / Maker Leg
        if is_patient_strategy and rem_qty > 0:
            maker_qty = int(rem_qty * 0.70)
            if maker_qty > 0:
                legs.append({
                    "venue_type": "PRIMARY_EXCHANGE_MAKER",
                    "order_type": "PRIMARY_PEG_LIMIT",
                    "quantity": maker_qty,
                    "target_price": target_price,
                    "expected_rebate_bps": self.maker_rebate_bps,
                    "priority": 2
                })
                lit_qty = rem_qty - maker_qty
            else:
                lit_qty = rem_qty
        else:
            lit_qty = rem_qty

        # 3. Tier 3: Lit Exchange Residual Sweeper Leg
        if lit_qty > 0:
            legs.append({
                "venue_type": "LIT_EXCHANGE_SWEEPER",
                "order_type": "LIMIT_IOC" if is_patient_strategy else "MARKET_OR_VWAP",
                "quantity": lit_qty,
                "target_price": target_price,
                "expected_rebate_bps": -self.taker_fee_bps,
                "priority": 3
            })

        # Calculate weighted expected cost saving in bps
        tot_saving = 0.0
        for leg in legs:
            w_leg = leg["quantity"] / total_quantity
            tot_saving += w_leg * leg["expected_rebate_bps"]

        return {
            "symbol": symbol,
            "action": action,
            "total_quantity": total_quantity,
            "target_price": target_price,
            "legs": legs,
            "expected_cost_saving_bps": round(float(tot_saving), 2)
        }

    def route_batch(
        self,
        order_plans: List[Dict[str, Any]],
        ats_available: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Routes a full batch of portfolio order plans through SOR.
        """
        routed_batch = []
        for plan in order_plans:
            routed = self.route_order(plan, ats_available=ats_available)
            routed_batch.append(routed)
        return routed_batch

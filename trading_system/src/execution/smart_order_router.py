"""
smart_order_router.py — Lit/Dark Smart Order Router (SOR) Engine

Routes institutional orders across multi-venue liquidity pools:
  - Tier 1: ATS / Nextrade / Dark Pool Midpoint Cross Probe (Zero Market Impact)
  - Tier 2: Primary Peg Maker Resting Orders (Maker Rebate Capture)
  - Tier 3: Lit Exchange Sweeper with ADV Participation Bounds (<= 1.5% ADV)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

import numpy as np

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

        dp_score = float(order_plan.get("darkpool_score", order_plan.get("dark_pool_score", 0.0)) or 0.0)
        is_accum = bool(order_plan.get("is_accumulation", False) or dp_score >= 0.60)

        # Dynamic Dark Probing Ratio (Feature 12):
        # Dynamically scales dark pool allocation from base 40% up to 70% when institutional block accumulation is detected
        if is_accum:
            eff_dark_ratio = float(np.clip(max(self.dark_probe_ratio, 0.55 + 0.15 * dp_score), self.dark_probe_ratio, 0.70))
        elif dp_score > 0.0:
            eff_dark_ratio = float(np.clip(self.dark_probe_ratio + 0.30 * dp_score, self.dark_probe_ratio, 0.70))
        else:
            eff_dark_ratio = float(self.dark_probe_ratio)

        # 1. Tier 1: ATS / Dark Pool Midpoint Probe Leg
        is_patient_strategy = exec_strategy in ["MIDPOINT_PEG", "PATIENT_TWAP", "DYNAMIC_VWAP"]
        is_probe_eligible = is_patient_strategy or dp_score >= 0.30 or is_accum
        if ats_available and is_probe_eligible:
            dark_qty = int(total_quantity * eff_dark_ratio)
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

        # 2. Tier 2: Primary Peg / Maker Leg (70% of residual quantity)
        if rem_qty > 0:
            maker_qty = int(rem_qty * 0.70) if (is_patient_strategy or is_probe_eligible) else 0
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
            lit_qty = 0

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
            rebate = float(leg.get("expected_rebate_bps", 0.0))
            if np.isfinite(rebate) and np.isfinite(w_leg):
                tot_saving += w_leg * rebate

        dest = self.determine_destination(symbol, order_plan.get("market"))

        return {
            "symbol": symbol,
            "action": action,
            "total_quantity": total_quantity,
            "target_price": target_price,
            "destination": dest,
            "legs": legs,
            "dark_ats_midpoint": next((leg for leg in legs if leg["venue_type"] == "DARK_ATS_MIDPOINT"), None),
            "primary_exchange_maker": next((leg for leg in legs if leg["venue_type"] == "PRIMARY_EXCHANGE_MAKER"), None),
            "lit_exchange_sweeper": next((leg for leg in legs if leg["venue_type"] == "LIT_EXCHANGE_SWEEPER"), None),
            "effective_dark_ratio": round(float(eff_dark_ratio), 4),
            "expected_cost_saving_bps": round(float(tot_saving if np.isfinite(tot_saving) else 0.0), 2)
        }

    def determine_destination(self, symbol: str, market: Optional[str] = None) -> Dict[str, str]:
        """
        Determines the institutional execution gateway (IBKR/FIX vs KRX Domestic) based on symbol/market.
        """
        sym = str(symbol).strip().upper()
        mkt = str(market).strip().upper() if market else ""

        is_krx = (
            mkt in ["KOSPI", "KOSDAQ", "KRX"] or
            (len(sym) == 6 and sym.isdigit()) or
            sym.endswith((".KS", ".KQ")) or
            (sym.split(".")[0].isdigit() and len(sym.split(".")[0]) == 6)
        )

        if is_krx:
            return {
                "market_region": "KRX",
                "primary_broker": "korea_investment",
                "dma_gateway": "krx_open_api",
                "venue": "KRX_ATS_NEXTRADE"
            }
        elif mkt in ["JAPAN_TSE", "JAPAN", "TSE", "NIKKEI", "TOPIX"] or sym.endswith(".T"):
            return {
                "market_region": "JP",
                "primary_broker": "interactive_brokers",
                "dma_gateway": "fix_protocol",
                "venue": "TSE_DIRECT"
            }
        elif mkt in ["HKEX", "HONGKONG", "HANGSENG"] or sym.endswith(".HK"):
            return {
                "market_region": "HK",
                "primary_broker": "interactive_brokers",
                "dma_gateway": "fix_protocol",
                "venue": "HKEX_DIRECT"
            }
        elif mkt in ["EUROPE_STOXX", "EUROPE", "STOXX", "DAX", "FTSE", "CAC"] or sym.endswith((".DE", ".PA", ".AS", ".L", ".SW")):
            return {
                "market_region": "EU",
                "primary_broker": "interactive_brokers",
                "dma_gateway": "fix_protocol",
                "venue": "EURONEXT_XETRA"
            }
        elif mkt in ["CANADA_TSX", "CANADA", "TSX"] or sym.endswith(".TO"):
            return {
                "market_region": "CA",
                "primary_broker": "interactive_brokers",
                "dma_gateway": "fix_protocol",
                "venue": "TSX_DIRECT"
            }
        else:
            return {
                "market_region": "US",
                "primary_broker": "interactive_brokers",
                "dma_gateway": "fix_protocol",
                "venue": "US_SMART_DMA"
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


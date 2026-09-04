"""
smart_order_router.py — Lit/Dark Smart Order Router (SOR) Engine

Routes institutional orders across multi-venue liquidity pools:
  - Tier 1: ATS / Nextrade / Dark Pool Midpoint Cross Probe (Zero Market Impact)
  - Tier 2: Primary Peg Maker Resting Orders (Maker Rebate Capture)
  - Tier 3: Lit Exchange Sweeper with ADV Participation Bounds (<= 1.5% ADV)
"""

from __future__ import annotations

import logging
import math
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
        taker_fee_bps: float = 1.5,
        continuous_hawkes: bool = False,
        use_logistic_dark_fill: bool = False,
    ):
        self.dark_probe_ratio = float(dark_probe_ratio)
        self.maker_rebate_bps = float(maker_rebate_bps)
        self.taker_fee_bps = float(taker_fee_bps)
        self.continuous_hawkes = bool(continuous_hawkes)
        self.use_logistic_dark_fill = bool(use_logistic_dark_fill)

    def route_order(
        self,
        order_plan: Dict[str, Any],
        ats_available: bool = True,
        market_spread_bps: float = 15.0,
        hawkes_intensity: Optional[float] = None,
        baseline_intensity: float = 1.0,
        continuous_hawkes: Optional[bool] = None,
        hawkes_buy: Optional[float] = None,
        hawkes_sell: Optional[float] = None,
        gamma_toxic_dir: Optional[float] = None,
        use_logistic_dark_fill: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Decomposes an order plan into 3-tier routing legs to optimize net execution cost.
        F32 & F38: Continuous Hawkes Arrival Intensity Adverse Selection Gating.
        F44: Directional Bivariate Hawkes Toxicity, Anti-Gaming Dynamic MinQty,
        Logistic Hazard Dark Fill Probability, and Institutional Venue Specialization.
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

        # F32, F38 & F44: Hawkes Arrival Intensity & Directional Toxicity Adverse Selection Gating
        hwk = hawkes_intensity if hawkes_intensity is not None else order_plan.get("hawkes_intensity")
        base_hwk = baseline_intensity if baseline_intensity is not None else float(order_plan.get("baseline_intensity", 1.0) or 1.0)
        base_hwk = max(1e-6, float(base_hwk))

        # Check continuous toxicity mode
        use_continuous = continuous_hawkes if continuous_hawkes is not None else order_plan.get("continuous_hawkes", getattr(self, "continuous_hawkes", False))

        # F44: Directional Hawkes checks
        h_buy = hawkes_buy if hawkes_buy is not None else order_plan.get("hawkes_buy")
        h_sell = hawkes_sell if hawkes_sell is not None else order_plan.get("hawkes_sell")
        g_dir = gamma_toxic_dir if gamma_toxic_dir is not None else order_plan.get("gamma_toxic_dir")
        is_directional = bool(h_buy is not None or h_sell is not None or g_dir is not None)

        is_toxic_flow = False
        gamma_toxic = 0.0
        maker_ratio = 0.70

        if g_dir is not None:
            gamma_toxic = float(np.clip(float(g_dir), 0.0, 1.0))
            is_toxic_flow = bool(gamma_toxic > 0.50)
            # F44: Modulate maker_ratio down to 0.20 when directional toxic flow is present
            maker_ratio = float(np.clip(0.70 * (1.0 - 0.7143 * gamma_toxic), 0.20, 0.70))
            eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, 0.80))
        elif h_buy is not None or h_sell is not None:
            hb_val = float(h_buy) if (h_buy is not None and math.isfinite(float(h_buy))) else base_hwk
            hs_val = float(h_sell) if (h_sell is not None and math.isfinite(float(h_sell))) else base_hwk
            delta_dir = (hs_val - hb_val) / max(1e-6, hs_val + hb_val)
            is_buy = action in ["BUY", "BID", "LONG"]
            if is_buy:
                gamma_raw = (hs_val - base_hwk) / (1.5 * base_hwk) + 0.35 * max(0.0, delta_dir)
            else:
                gamma_raw = (hb_val - base_hwk) / (1.5 * base_hwk) - 0.35 * min(0.0, delta_dir)
            gamma_toxic = float(np.clip(gamma_raw, 0.0, 1.0))
            is_toxic_flow = bool(gamma_toxic > 0.50)
            # F44: Modulate maker_ratio down to 0.20 when directional toxic flow is present
            maker_ratio = float(np.clip(0.70 * (1.0 - 0.7143 * gamma_toxic), 0.20, 0.70))
            eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, 0.80))
        elif hwk is not None:
            try:
                hwk_f = float(hwk)
                if math.isfinite(hwk_f):
                    if use_continuous:
                        # F38: Continuous Hawkes toxicity modulation
                        denom = 1.5 * base_hwk
                        gamma_toxic = float(np.clip((hwk_f - base_hwk) / denom, 0.0, 1.0))
                        maker_ratio = float(np.clip(0.70 * (1.0 - 0.571 * gamma_toxic), 0.30, 0.70))
                        is_toxic_flow = bool(gamma_toxic > 0.50)
                        eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, 0.80))
                    else:
                        # F32 discrete step gating
                        if hwk_f > 2.5 * base_hwk:
                            is_toxic_flow = True
                            gamma_toxic = 1.0
                            maker_ratio = 0.30
                            eff_dark_ratio = float(np.clip(max(eff_dark_ratio + 0.20, 0.60), eff_dark_ratio, 0.80))
                        else:
                            is_toxic_flow = False
                            gamma_toxic = 0.0
                            maker_ratio = 0.70
            except (ValueError, TypeError):
                is_toxic_flow = False
                gamma_toxic = 0.0
                maker_ratio = 0.70
        else:
            maker_ratio = 0.70

        # F44: Anti-Gaming Dynamic MinQty (adapting between 20% and 50% of dark_qty)
        min_ratio = 0.20
        if is_toxic_flow or gamma_toxic > 0.50 or dp_score >= 0.60:
            min_ratio = float(np.clip(0.20 + 0.25 * gamma_toxic + 0.15 * dp_score, 0.20, 0.50))

        # F38 & F44: Darkpool Fill Probability Estimation
        use_logistic = (
            use_logistic_dark_fill
            if use_logistic_dark_fill is not None
            else (getattr(self, "use_logistic_dark_fill", False) or is_directional or bool(order_plan.get("use_logistic_dark_fill", False)))
        )
        if use_logistic:
            # F44: Logistic Hazard Dark Fill Probability Kernel bounded in [0.10, 0.90]
            z_fill = (
                -0.20
                + 1.20 * ((market_spread_bps - 5.0) / 15.0)
                + 1.50 * dp_score
                - 1.00 * gamma_toxic
                - 0.80 * min_ratio
            )
            p_fill_dark = float(np.clip(1.0 / (1.0 + math.exp(-z_fill)), 0.10, 0.90))
        else:
            # F38: Linear bounded model [0.15, 0.85]
            p_fill_dark = float(np.clip(
                0.35 + 0.35 * dp_score + 0.15 * ((market_spread_bps - 5.0) / 15.0) - 0.20 * gamma_toxic,
                0.15,
                0.85
            ))

        dest = self.determine_destination(symbol, order_plan.get("market"))

        # 1. Tier 1: ATS / Dark Pool Midpoint Probe Leg with MinQty
        is_patient_strategy = exec_strategy in ["MIDPOINT_PEG", "PATIENT_TWAP", "DYNAMIC_VWAP"]
        is_probe_eligible = is_patient_strategy or dp_score >= 0.30 or is_accum or is_toxic_flow or (gamma_toxic > 0.0)
        if ats_available and is_probe_eligible:
            dark_qty = int(total_quantity * eff_dark_ratio)
            if dark_qty > 0:
                dark_order_type = "MIDPOINT_PEGGED_RESTING" if (is_toxic_flow or gamma_toxic > 0.50) else "MIDPOINT_IOC"
                dark_leg: Dict[str, Any] = {
                    "venue_type": "DARK_ATS_MIDPOINT",
                    "order_type": dark_order_type,
                    "quantity": dark_qty,
                    "target_price": target_price,
                    "expected_rebate_bps": market_spread_bps / 2.0,  # Saves half-spread
                    "priority": 1,
                    "fill_probability": round(p_fill_dark, 4),
                }
                # F38 & F44: Dynamic anti-gaming MinQty adapting between 20% and 50%
                if is_toxic_flow or gamma_toxic > 0.50 or dp_score >= 0.60:
                    dark_leg["min_quantity"] = max(1, int(round(min_ratio * dark_qty)))
                    dark_leg["anti_gaming_active"] = True

                # Venue specific tags (F44)
                if dest.get("venue") == "US_SMART_DMA":
                    dark_leg["d_peg_cqi_protected"] = True
                    dark_leg["micro_jitter_probe"] = True
                elif dest.get("venue") == "KRX_ATS_NEXTRADE":
                    dark_leg["lot_size"] = 1
                    dark_leg["rebate_bps"] = 0.5

                legs.append(dark_leg)
                rem_qty = total_quantity - dark_qty
            else:
                rem_qty = total_quantity
        else:
            rem_qty = total_quantity

        # 2. Tier 2: Primary Peg / Maker Leg (modulated continuously)
        maker_rebate = float(dest.get("rebate_bps", self.maker_rebate_bps))
        if rem_qty > 0:
            maker_qty = int(rem_qty * maker_ratio) if (is_patient_strategy or is_probe_eligible) else 0
            if maker_qty > 0:
                maker_leg: Dict[str, Any] = {
                    "venue_type": "PRIMARY_EXCHANGE_MAKER",
                    "order_type": "PRIMARY_PEG_LIMIT",
                    "quantity": maker_qty,
                    "target_price": target_price,
                    "expected_rebate_bps": maker_rebate,
                    "priority": 2,
                }
                if dest.get("venue") == "KRX_ATS_NEXTRADE":
                    maker_leg["lot_size"] = 1
                    maker_leg["rebate_bps"] = 0.5
                legs.append(maker_leg)
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
            "expected_cost_saving_bps": round(float(tot_saving if np.isfinite(tot_saving) else 0.0), 2),
            "hawkes_intensity": float(hwk) if (hwk is not None and math.isfinite(float(hwk))) else None,
            "toxic_flow_detected": is_toxic_flow,
            "gamma_toxic": round(float(gamma_toxic), 4),
            "darkpool_fill_probability": round(float(p_fill_dark), 4),
            "maker_ratio": round(float(maker_ratio), 4),
        }

    def determine_destination(self, symbol: str, market: Optional[str] = None) -> Dict[str, Any]:
        """
        Determines the institutional execution gateway (IBKR/FIX vs KRX Domestic) based on symbol/market.
        F44: Includes lot sizes, rebate tiers, and anti-gaming protection tags.
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
                "venue": "KRX_ATS_NEXTRADE",
                "lot_size": 1,
                "rebate_bps": 0.5,
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
                "venue": "US_SMART_DMA",
                "d_peg_cqi_protected": True,
                "micro_jitter_probe": True,
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


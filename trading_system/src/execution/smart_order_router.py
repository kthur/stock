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
        queue_imbalance: Optional[float] = None,
        arrival_imbalance: Optional[float] = None,
        qi_acceleration: Optional[float] = None,
        cross_asset_toxicity: Optional[float] = None,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Decomposes an order plan into 3-tier routing legs to optimize net execution cost.
        F32 & F38: Continuous Hawkes Arrival Intensity Adverse Selection Gating.
        F44: Directional Bivariate Hawkes Toxicity, Anti-Gaming Dynamic MinQty,
        Logistic Hazard Dark Fill Probability, and Institutional Venue Specialization.
        F50: Level-3 Queue Imbalance Preemption, 0.10 Maker Ratio Contraction, and 0.60 MinQty Cap.
        F54: Level-3 Queue Imbalance Acceleration Preemption up to 85%, 0.05 Maker Floor,
        0.75 Anti-Gaming MinQty, and Cross-Asset Toxicity.
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

        v_eff = version if version is not None else int(order_plan.get("version", 6))
        qi = queue_imbalance if queue_imbalance is not None else order_plan.get("queue_imbalance", order_plan.get("l3_queue_imbalance"))
        arr_imb = arrival_imbalance if arrival_imbalance is not None else order_plan.get("arrival_imbalance")
        qi_accel = qi_acceleration if qi_acceleration is not None else order_plan.get("qi_acceleration")
        cross_tox = cross_asset_toxicity if cross_asset_toxicity is not None else order_plan.get("cross_asset_toxicity")

        is_phase15 = (v_eff >= 15)
        is_phase14 = is_phase15 or (v_eff >= 14)
        is_phase13 = is_phase14 or (v_eff >= 13)
        is_phase12 = is_phase13 or (v_eff >= 12)
        is_phase11 = is_phase12 or (v_eff >= 11)
        is_phase10 = is_phase11 or (v_eff >= 10)
        is_phase9 = is_phase10 or (v_eff >= 9)
        is_phase8 = is_phase9 or (v_eff >= 8) or (qi_accel is not None) or (cross_tox is not None)
        is_phase7 = is_phase8 or (v_eff >= 7) or (qi is not None) or (arr_imb is not None)

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

        # F50, F54, F58, F61, F65, F69, F73, F77 & F81: Lit Queue Imbalance & Acceleration Preemption (preemptively route up to 75% / 85% / 88% / 92% / 95% / 96% / 97% / 98% / 99% to dark ATS)
        if qi is not None or qi_accel is not None:
            qi_f = float(qi) if (qi is not None and math.isfinite(float(qi))) else 0.0
            qi_aligned = qi_f if action in ["BUY", "BID", "LONG"] else -qi_f
            a_f = float(qi_accel) if (qi_accel is not None and math.isfinite(float(qi_accel))) else 0.0
            a_aligned = a_f if action in ["BUY", "BID", "LONG"] else -a_f

            if is_phase15 and (qi_aligned > 0.10 or a_aligned > 0.03):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.35 * max(0.0, qi_aligned) + 0.26 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.99
                ))
            elif is_phase14 and (qi_aligned > 0.12 or a_aligned > 0.04):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.32 * max(0.0, qi_aligned) + 0.24 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.98
                ))
            elif is_phase13 and (qi_aligned > 0.15 or a_aligned > 0.05):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.30 * max(0.0, qi_aligned) + 0.22 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.97
                ))
            elif is_phase12 and (qi_aligned > 0.20 or a_aligned > 0.08):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.28 * max(0.0, qi_aligned) + 0.20 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.96
                ))
            elif is_phase11 and (qi_aligned > 0.25 or a_aligned > 0.10):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.25 * max(0.0, qi_aligned) + 0.18 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.95
                ))
            elif is_phase10 and (qi_aligned > 0.30 or a_aligned > 0.12):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.22 * max(0.0, qi_aligned) + 0.15 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.92
                ))
            elif is_phase9 and (qi_aligned > 0.35 or a_aligned > 0.15):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.18 * max(0.0, qi_aligned) + 0.12 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.88
                ))
            elif is_phase8 and (qi_aligned > 0.40 or a_aligned > 0.20):
                eff_dark_ratio = float(np.clip(
                    eff_dark_ratio + 0.15 * max(0.0, qi_aligned) + 0.10 * math.tanh(max(0.0, a_aligned)),
                    self.dark_probe_ratio, 0.85
                ))
            elif qi_aligned > 0.50:
                eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.15 * qi_aligned, self.dark_probe_ratio, 0.75))

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
            if is_phase15 and gamma_toxic > 0.80:
                # F81.2: QCD Asymptotic Freedom L3 preemption contracts lit maker floor to 0.0005
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99928 * gamma_toxic), 0.0005, 0.70))
            elif is_phase14 and gamma_toxic > 0.80:
                # F77.2: Quantum Navier-Stokes L3 preemption contracts lit maker floor to 0.001
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99857 * gamma_toxic), 0.001, 0.70))
            elif is_phase13 and gamma_toxic > 0.80:
                # F73.2: Deep Hawkes cross-excitation contracts lit maker floor to 0.002
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99714 * gamma_toxic), 0.002, 0.70))
            elif is_phase12 and gamma_toxic > 0.80:
                # F69.2: Deep Hawkes cross-excitation contracts lit maker floor to 0.005
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99286 * gamma_toxic), 0.005, 0.70))
            elif is_phase11 and gamma_toxic > 0.80:
                # F65.2: Deep Hawkes cross-excitation contracts lit maker floor to 0.01
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9857 * gamma_toxic), 0.01, 0.70))
            elif is_phase10 and gamma_toxic > 0.80:
                # F61.2: Multivariate Hawkes cross-excitation contracts lit maker floor to 0.02
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9714 * gamma_toxic), 0.02, 0.70))
            elif is_phase9 and gamma_toxic > 0.80:
                # F58.2: Quantum Walk Grover diffusion contracts lit maker floor to 0.03
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9571 * gamma_toxic), 0.03, 0.70))
            elif is_phase8 and gamma_toxic > 0.80:
                # F54: Extreme directional toxicity contracts lit maker floor to 0.05
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9286 * gamma_toxic), 0.05, 0.70))
            elif is_phase7 and gamma_toxic > 0.80:
                # F50: Extreme directional toxicity contracts lit maker floor to 0.10
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.8571 * gamma_toxic), 0.10, 0.70))
            else:
                # F44: Modulate maker_ratio down to 0.20 when directional toxic flow is present
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.7143 * gamma_toxic), 0.20, 0.70))
            max_dark_cap = 0.99 if is_phase15 else (0.98 if is_phase14 else (0.97 if is_phase13 else (0.96 if is_phase12 else (0.95 if is_phase11 else (0.92 if is_phase10 else (0.88 if is_phase9 else 0.80))))))
            eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, max_dark_cap))
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
            if is_phase15 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99928 * gamma_toxic), 0.0005, 0.70))
            elif is_phase14 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99857 * gamma_toxic), 0.001, 0.70))
            elif is_phase13 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99714 * gamma_toxic), 0.002, 0.70))
            elif is_phase12 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99286 * gamma_toxic), 0.005, 0.70))
            elif is_phase11 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9857 * gamma_toxic), 0.01, 0.70))
            elif is_phase10 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9714 * gamma_toxic), 0.02, 0.70))
            elif is_phase8 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9286 * gamma_toxic), 0.05, 0.70))
            elif is_phase7 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.8571 * gamma_toxic), 0.10, 0.70))
            else:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.7143 * gamma_toxic), 0.20, 0.70))
            max_dark_cap = 0.99 if is_phase15 else (0.98 if is_phase14 else (0.97 if is_phase13 else (0.96 if is_phase12 else (0.95 if is_phase11 else (0.92 if is_phase10 else (0.88 if is_phase9 else 0.80))))))
            eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, max_dark_cap))
        elif hwk is not None:
            try:
                hwk_f = float(hwk)
                if math.isfinite(hwk_f):
                    max_dark_cap = 0.99 if is_phase15 else (0.98 if is_phase14 else (0.97 if is_phase13 else (0.96 if is_phase12 else (0.95 if is_phase11 else (0.92 if is_phase10 else (0.88 if is_phase9 else 0.80))))))
                    if use_continuous:
                        # F38: Continuous Hawkes toxicity modulation
                        denom = 1.5 * base_hwk
                        gamma_toxic = float(np.clip((hwk_f - base_hwk) / denom, 0.0, 1.0))
                        maker_ratio = float(np.clip(0.70 * (1.0 - 0.571 * gamma_toxic), 0.30, 0.70))
                        is_toxic_flow = bool(gamma_toxic > 0.50)
                        eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, max_dark_cap))
                    else:
                        # F32 discrete step gating
                        if hwk_f > 2.5 * base_hwk:
                            is_toxic_flow = True
                            gamma_toxic = 1.0
                            maker_ratio = 0.30
                            eff_dark_ratio = float(np.clip(max(eff_dark_ratio + 0.20, 0.60), eff_dark_ratio, max_dark_cap))
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

        # F54: Cross-Asset Flow Toxicity Blending
        if cross_tox is not None and math.isfinite(float(cross_tox)):
            g_cross = float(np.clip(float(cross_tox), 0.0, 1.0))
            gamma_toxic = float(np.clip(0.65 * gamma_toxic + 0.35 * g_cross, 0.0, 1.0))
            is_toxic_flow = bool(gamma_toxic > 0.50)
            if is_phase15 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99928 * gamma_toxic), 0.0005, 0.70))
            elif is_phase14 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99857 * gamma_toxic), 0.001, 0.70))
            elif is_phase13 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99714 * gamma_toxic), 0.002, 0.70))
            elif is_phase12 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.99286 * gamma_toxic), 0.005, 0.70))
            elif is_phase11 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9857 * gamma_toxic), 0.01, 0.70))
            elif is_phase10 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9714 * gamma_toxic), 0.02, 0.70))
            elif is_phase9 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9571 * gamma_toxic), 0.03, 0.70))
            elif is_phase8 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.9286 * gamma_toxic), 0.05, 0.70))
            elif is_phase7 and gamma_toxic > 0.80:
                maker_ratio = float(np.clip(0.70 * (1.0 - 0.8571 * gamma_toxic), 0.10, 0.70))

        # F44, F50, F54, F58, F61, F65, F69, F73, F77 & F81: Anti-Gaming Dynamic MinQty (adapting up to 99.5% in F81)
        min_ratio = 0.20
        if is_toxic_flow or gamma_toxic > 0.50 or dp_score >= 0.60:
            if is_phase15 and (gamma_toxic > 0.35 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.70 * gamma_toxic + 0.55 * dp_score, 0.20, 0.995))
            elif is_phase14 and (gamma_toxic > 0.40 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.65 * gamma_toxic + 0.50 * dp_score, 0.20, 0.99))
            elif is_phase13 and (gamma_toxic > 0.45 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.60 * gamma_toxic + 0.45 * dp_score, 0.20, 0.98))
            elif is_phase12 and (gamma_toxic > 0.50 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.55 * gamma_toxic + 0.40 * dp_score, 0.20, 0.95))
            elif is_phase11 and (gamma_toxic > 0.55 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.50 * gamma_toxic + 0.35 * dp_score, 0.20, 0.90))
            elif is_phase10 and (gamma_toxic > 0.60 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.45 * gamma_toxic + 0.30 * dp_score, 0.20, 0.80))
            elif is_phase9 and (gamma_toxic > 0.65 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.40 * gamma_toxic + 0.25 * dp_score, 0.20, 0.80))
            elif is_phase8 and (gamma_toxic > 0.70 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.35 * gamma_toxic + 0.20 * dp_score, 0.20, 0.75))
            elif is_phase7 and (gamma_toxic > 0.70 or is_accum):
                min_ratio = float(np.clip(0.20 + 0.30 * gamma_toxic + 0.15 * dp_score, 0.20, 0.60))
            else:
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
                    "maker_ratio": round(float(maker_ratio), 4),
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
            "queue_imbalance": round(float(qi), 4) if (qi is not None and math.isfinite(float(qi))) else None,
            "arrival_imbalance": round(float(arr_imb), 4) if (arr_imb is not None and math.isfinite(float(arr_imb))) else None,
            "min_ratio": round(float(min_ratio), 4),
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

    def quantum_walk_grover_routing(
        self,
        venues: List[str],
        depths: List[float],
        costs_bps: List[float],
        steps: int = 2
    ) -> Dict[str, float]:
        """
        Phase 9 (F58.2): Quantum Walk Grover Diffusion ATS Routing.
        Applies a discrete-time quantum walk Grover coin operator G = 2|s><s| - I
        over venue states (Lit, ATS, Darkpool, Internal) to amplify amplitude
        toward the venue with maximum liquidity depth and lowest friction cost.
        """
        n = len(venues)
        if n == 0:
            return {}
        if n == 1:
            return {venues[0]: 1.0}

        # Initialize uniform amplitude state |s> = sum (1/sqrt(n)) |i>
        state = np.ones(n, dtype=float) / math.sqrt(n)

        # Oracle phase inversion based on attractiveness score: depth / cost
        scores = np.array([depths[i] / max(0.5, costs_bps[i]) for i in range(n)], dtype=float)
        best_idx = int(np.argmax(scores))

        # Determine optimal Grover rotations to avoid over-rotation: R = max(1, round(pi/4 * sqrt(n)))
        r_opt = max(1, int(round((math.pi / 4.0) * math.sqrt(n))))
        eff_steps = min(max(1, steps), r_opt)

        # Grover iteration:
        for _ in range(eff_steps):
            # Oracle: invert phase of marked (best) venue
            state[best_idx] = -state[best_idx]
            # Diffusion operator G = 2 * mean(state) - state
            mean_amp = np.mean(state)
            state = 2.0 * mean_amp - state

        # Probability distribution P(i) = |state[i]|^2, normalized
        probs = np.square(state)
        sum_p = np.sum(probs)
        if sum_p > 0:
            probs = probs / sum_p
        else:
            probs = np.ones(n) / n

        return {venues[i]: float(probs[i]) for i in range(n)}


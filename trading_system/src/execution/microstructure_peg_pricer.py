"""
src/execution/microstructure_peg_pricer.py

Microstructure Peg Limit Price Engine.
Computes micro-price, L3 queue dynamics, Hawkes arrival rate adjustments,
and adverse selection shading offsets for optimal limit order pegging.
"""

import math
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

__all__ = ["MicrostructurePegPricer"]


class MicrostructurePegPricer:
    """
    L3 Micro-Price and Hawkes Process Microstructure Peg Pricing Engine.
    Extracted from ExecutionOMSEngine for modularity and separation of concerns.
    """

    @staticmethod
    def calculate_peg_limit_price(
        target_price: Optional[float] = None,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        spread: Optional[float] = None,
        alpha_urgency: float = 0.50,
        action: str = "BUY",
        obi: Optional[float] = None,
        kappa: float = 1.5,
        micro_price: Optional[float] = None,
        multi_obi: Optional[Dict[str, float]] = None,
        daily_volatility: Optional[float] = None,
        book_depth_ratio: Optional[float] = None,
        queue_position_ratio: Optional[float] = None,
        l3_micro_price: Optional[float] = None,
        l3_imbalance: Optional[float] = None,
        hawkes_toxicity: Optional[float] = None,
        hawkes_arrival_imbalance: Optional[float] = None,
        queue_imbalance: Optional[float] = None,
        qi_acceleration: Optional[float] = None,
        cross_asset_toxicity: Optional[float] = None,
        version: int = 6,
        qi_jerk: Optional[float] = None,
        deep_ofi: Optional[float] = None,
        hawkes_intensity: Optional[Union[float, Dict[str, float]]] = None,
        side: Optional[str] = None,
        urgency: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        Phase 6 (F44), Phase 7 (F50) & Phase 8 (F54) Level-3 Micro-Price & Queue-Position-Aware Peg Calculation:
        1. Base anchor price: Hawkes arrival-adjusted micro-price > L3 micro-price > L1 micro-price > mid price.
        2. Dynamic curvature kappa_eff scales with volatility and orderbook depth.
        3. Imbalance shift uses Queue Imbalance (QI_L3*) > L3 decayed imbalance > multi-tier L2 OBI composite > L1 OBI.
        4. Queue position adverse selection offset delta_P_queue compensates when order is buried (u_q > 0.40),
           suppressed by Hawkes & cross-asset composite toxicity gamma_composite (F50 & F54).
        5. Toxic shading offset delta_P_shade steps back against toxic flow when gamma_composite > 0.45/0.50 (F50 & F54).
        6. Queue Imbalance 2nd-order acceleration peg shift a_shift (F54.2).
        7. Strict clipping within [min(bid, ask), max(bid, ask)].
        """
        if side is not None:
            action = side
        if urgency is not None:
            alpha_urgency = float(urgency)
        valid_tp = target_price is not None and math.isfinite(float(target_price)) and float(target_price) > 0
        valid_bid = bid_price is not None and math.isfinite(float(bid_price)) and float(bid_price) > 0
        valid_ask = ask_price is not None and math.isfinite(float(ask_price)) and float(ask_price) > 0

        if not valid_tp:
            if micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
                tp = float(micro_price)
            elif valid_bid and valid_ask:
                tp = 0.5 * (float(bid_price) + float(ask_price))
            elif valid_bid:
                tp = float(bid_price)
            elif valid_ask:
                tp = float(ask_price)
            else:
                tp = 1000.0
        else:
            tp = float(target_price)
        if tp <= 0 or not math.isfinite(tp):
            return 1000.0 if not math.isfinite(tp) else tp

        if spread is not None and math.isfinite(float(spread)) and float(spread) > 0:
            spr = float(spread)
        elif valid_bid and valid_ask and float(ask_price) > float(bid_price):
            spr = float(ask_price) - float(bid_price)
        else:
            spr = max(tp * 0.002, 1.0)
        p_bid = float(bid_price) if valid_bid else (tp - spr / 2.0)
        p_ask = float(ask_price) if valid_ask else (tp + spr / 2.0)
        p_mid = (p_bid + p_ask) / 2.0

        # 2. Imbalance resolution: Queue Imbalance > L3 decayed imbalance > Multi-tier L2 composite > L1 OBI
        eff_obi = None
        if queue_imbalance is not None and math.isfinite(float(queue_imbalance)):
            eff_obi = float(queue_imbalance)
        elif l3_imbalance is not None and math.isfinite(float(l3_imbalance)):
            eff_obi = float(l3_imbalance)
        elif multi_obi is not None and isinstance(multi_obi, dict):
            multi_dict: Dict[Any, Any] = multi_obi
            obi_1 = float(multi_dict.get("OBI_1", multi_dict.get("obi_1", multi_dict.get("1", multi_dict.get(1, 0.0)))) or 0.0)
            obi_5 = float(multi_dict.get("OBI_5", multi_dict.get("obi_5", multi_dict.get("5", multi_dict.get(5, 0.0)))) or 0.0)
            obi_10 = float(multi_dict.get("OBI_10", multi_dict.get("obi_10", multi_dict.get("10", multi_dict.get(10, 0.0)))) or 0.0)
            eff_obi = 0.50 * obi_1 + 0.35 * obi_5 + 0.15 * obi_10
        elif obi is not None and math.isfinite(float(obi)):
            eff_obi = float(obi)

        # 1. Base anchor price: Hawkes arrival adjusted (F50) > L3 micro-price > L1 micro-price > mid price
        omega_H = 0.35
        kappa_H = 1.20
        del_lam = None
        has_micro = False
        if hawkes_arrival_imbalance is not None and math.isfinite(float(hawkes_arrival_imbalance)):
            del_lam = float(np.clip(float(hawkes_arrival_imbalance), -1.0, 1.0))

        if del_lam is not None:
            qi_val = float(np.clip(eff_obi if eff_obi is not None else 0.0, -1.0, 1.0))
            if l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
                p_base = float(l3_micro_price) + 0.5 * spr * omega_H * math.tanh(kappa_H * del_lam)
                has_micro = True
            else:
                p_base = p_mid + 0.5 * spr * ((1.0 - omega_H) * qi_val + omega_H * math.tanh(kappa_H * del_lam))
        elif l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
            p_base = float(l3_micro_price)
            has_micro = True
        elif micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
            p_base = float(micro_price)
            has_micro = True
        else:
            p_base = p_mid

        # 3. Dynamic curvature scaling
        if daily_volatility is not None or book_depth_ratio is not None:
            sig = float(daily_volatility) if daily_volatility is not None else 0.02
            r_depth = float(book_depth_ratio) if book_depth_ratio is not None else 1.0
            r_depth = float(np.clip(r_depth, 0.20, 5.0))
            kappa_eff = float(np.clip(1.5 * (sig / 0.02) / math.sqrt(r_depth), 0.8, 3.0))
        else:
            kappa_eff = float(kappa)

        is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE", "BID"]
        direction = 1.0 if is_buy else -1.0

        # 4. Imbalance peg shift
        if eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0 and del_lam is None and not has_micro:
            obi_val = float(np.clip(float(eff_obi), -1.0, 1.0))
            peg_shift = 0.5 * spr * math.tanh(kappa_eff * obi_val)
        else:
            peg_shift = 0.0

        # F50 & F54: Directional Hawkes and Cross-Asset Composite Toxicity
        g_loc = float(np.clip(float(hawkes_toxicity), 0.0, 1.0)) if (hawkes_toxicity is not None and math.isfinite(float(hawkes_toxicity))) else 0.0
        g_cross = float(np.clip(float(cross_asset_toxicity), 0.0, 1.0)) if (cross_asset_toxicity is not None and math.isfinite(float(cross_asset_toxicity))) else 0.0
        gamma_composite = float(np.clip(0.65 * g_loc + 0.35 * g_cross, 0.0, 1.0)) if cross_asset_toxicity is not None else g_loc

        # 5. Queue position adverse selection offset (F44, F50 & F54)
        q_shift = 0.0
        if queue_position_ratio is not None and math.isfinite(float(queue_position_ratio)):
            u_q = float(np.clip(float(queue_position_ratio), 0.0, 1.0))
            if u_q > 0.40:
                urg = float(np.clip(float(alpha_urgency), 0.1, 1.0))
                tox_suppress = max(0.0, 1.0 - 0.85 * gamma_composite)
                q_shift = direction * 0.5 * spr * urg * (u_q - 0.40) * 0.60 * tox_suppress

        # 6. Toxic shading offset (F50 & F54)
        shade_shift = 0.0
        if int(version) >= 8 and gamma_composite > 0.45:
            shade_shift = -direction * 0.35 * spr * (gamma_composite - 0.45)
        elif gamma_composite > 0.50:
            shade_shift = -direction * 0.25 * spr * (gamma_composite - 0.50)

        # 7. Queue Imbalance 2nd-Order Acceleration Peg Shift (F54)
        accel_shift = 0.0
        if qi_acceleration is not None and math.isfinite(float(qi_acceleration)):
            a_val = float(qi_acceleration)
            accel_tox_damp = max(0.0, 1.0 - 0.90 * gamma_composite)
            accel_shift = direction * 0.20 * spr * math.tanh(0.80 * a_val) * accel_tox_damp

        # 8. Queue Imbalance 3rd-Order Jerk & Deep-OFI Peg Shift (Phase 9 F58.1)
        jerk_shift = 0.0
        if int(version) >= 9:
            j_val = float(qi_jerk) if (qi_jerk is not None and math.isfinite(float(qi_jerk))) else float(kwargs.get("qi_jerk", 0.0))
            d_ofi = float(deep_ofi) if (deep_ofi is not None and math.isfinite(float(deep_ofi))) else float(kwargs.get("deep_ofi", 0.0))
            jerk_tox_damp = max(0.0, 1.0 - 0.95 * gamma_composite)
            jerk_shift = direction * spr * (0.10 * math.tanh(0.50 * j_val) + 0.15 * math.tanh(1.20 * d_ofi)) * jerk_tox_damp

        # 9. Multivariate Hawkes Cross-Excitation Preemptive Shading (Phase 10 F61.2, Phase 11 F65.2, Phase 12 F69.2, Phase 13 F73.2, Phase 14 F77.2, Phase 15 F81.2, Phase 16 F85.2, Phase 17 F89.2, Phase 18 F93.2.3, Phase 19 F97.2, Phase 20 F101.2.3, Phase 21 F105.2.5, Phase 22 F109.2.3, Phase 23 F113.2.2, Phase 24 F117.2, Phase 25 F121.2, Phase 26 F125.2, Phase 27 F129.2, Phase 28 F133.2, Phase 29 F137.2, Phase 30 F141.2, Phase 31 F145.2, Phase 32 F149.2, Phase 33 F153.2, Phase 47 F209.2, Phase 48 F214.2, Phase 49 F219.2, Phase 50 F224.2, Phase 99 F468, Phase 100 F473, Phase 101 F478)
        v_eff = int(version) if version is not None else 6
        is_phase103 = (v_eff >= 103)
        is_phase102 = is_phase103 or (v_eff >= 102)
        is_phase101 = is_phase102 or (v_eff >= 101)
        is_phase100 = is_phase101 or (v_eff >= 100)
        is_phase99 = is_phase100 or (v_eff >= 99)
        is_phase98 = is_phase99 or (v_eff >= 98)
        is_phase97 = is_phase98 or (v_eff >= 97)
        is_phase96 = is_phase97 or (v_eff >= 96)
        is_phase95 = is_phase96 or (v_eff >= 95)
        is_phase94 = is_phase95 or (v_eff >= 94)
        is_phase93 = is_phase94 or (v_eff >= 93)
        is_phase92 = is_phase93 or (v_eff >= 92)
        is_phase91 = is_phase92 or (v_eff >= 91)
        is_phase90 = is_phase91 or (v_eff >= 90)
        is_phase89 = is_phase90 or (v_eff >= 89)
        is_phase88 = is_phase89 or (v_eff >= 88)
        is_phase87 = is_phase88 or (v_eff >= 87)
        is_phase86 = is_phase87 or (v_eff >= 86)
        hawkes_shift = 0.0
        if is_phase103:
            # Phase 103 F488: Tick shading h > 6.0e-12 threshold with 56 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.000000000006:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.000000000006)
        elif is_phase102:
            # Phase 102 F483: Tick shading h > 8.0e-12 threshold with 55 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.000000000008:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.000000000008)
        elif is_phase101:
            # Phase 101 F478: Tick shading h > 1.0e-11 threshold with 54 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.000000000010:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.000000000010)
        elif is_phase100:
            # Phase 100 F473: Tick shading h > 1.2e-11 threshold with 53 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.000000000012:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.000000000012)
        elif is_phase99:
            # Phase 99 F468: Tick shading h > 1.5e-11 threshold with 52 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.000000000015:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.000000000015)
        elif is_phase98:
            # Phase 98 F463: Tick shading h > 2.0e-11 threshold with 51 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000002:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000002)
        elif is_phase97:
            # Phase 97 F458: Tick shading h > 3.0e-11 threshold with 50 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000003:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000003)
        elif is_phase96:
            # Phase 96 F453: Tick shading h > 4.0e-11 threshold with 49 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000004:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000004)
        elif is_phase95:
            # Phase 95 F448: Tick shading h > 5.0e-11 threshold with 48 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000005:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000005)
        elif is_phase94:
            # Phase 94 F443: Tick shading h > 6.0e-11 threshold with 47 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000006:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000006)
        elif is_phase93:
            # Phase 93 F438: Tick shading h > 7.0e-11 threshold with 46 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000007:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000007)
        elif is_phase92:
            # Phase 92 F433: Tick shading h > 8.0e-11 threshold with 46 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000008:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000008)
        elif is_phase91:
            # Phase 91 F428.3: Tick shading h > 9.0e-11 threshold with 44 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000009:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000009)
        elif is_phase90:
            # Phase 90 F423.3: Tick shading h > 1.0e-10 threshold with 42 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000010:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000010)
        elif is_phase89:
            # Phase 89 F418.3: Tick shading h > 1.5e-10 threshold with 41 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.00000000015:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.00000000015)
        elif is_phase88:
            # Phase 88 F413.3: Tick shading h > 2e-10 threshold with 40 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.0000000002:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.0000000002)
        elif is_phase87:
            # Phase 87 F408.3: Tick shading h > 3e-10 threshold with 39 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_monster_whit = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_monster_whit = float(h_int)
            else:
                h_monster_whit = 0.0
            if h_monster_whit > 0.0000000003:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999999 * spr * (h_monster_whit - 0.0000000003)
        elif is_phase86:
            # Phase 86 F403.3: Tick shading h > 4e-10 threshold with 38 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000000004:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999999 * spr * (h_val - 0.0000000004)
        elif int(version) >= 85:
            # Phase 85 F398.3: Tick shading h > 5e-10 threshold with 37 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000000005:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999999 * spr * (h_val - 0.0000000005)
        elif int(version) >= 84:
            # Phase 84 F393.3: Tick shading h > 6e-10 threshold with 36 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000000006:
                hawkes_shift = -direction * 0.999999999999999999999999999999999999 * spr * (h_val - 0.0000000006)
        elif int(version) >= 82:
            # Phase 82 F384.2: Tick shading h>0.0000000008 threshold with 35 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000000008:
                hawkes_shift = -direction * 0.99999999999999999999999999999999999 * spr * (h_val - 0.0000000008)
        elif int(version) >= 81:
            # Phase 81 F379.2: Tick shading h>0.000000001 threshold with 34 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000000001:
                hawkes_shift = -direction * 0.9999999999999999999999999999999999 * spr * (h_val - 0.000000001)
        elif int(version) >= 80:
            # Phase 80 F374.2: Tick shading h>0.000000002 threshold with 33 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000000002:
                hawkes_shift = -direction * 0.999999999999999999999999999999999 * spr * (h_val - 0.000000002)
        elif int(version) >= 79:
            # Phase 79 F369.2: Tick shading h>0.000000005 threshold with 32 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000000005:
                hawkes_shift = -direction * 0.99999999999999999999999999999999 * spr * (h_val - 0.000000005)
        elif int(version) >= 78:
            # Phase 78 F364.2: Tick shading h>0.00000001 threshold with 31 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000001:
                hawkes_shift = -direction * 0.9999999999999999999999999999999 * spr * (h_val - 0.00000001)
        elif int(version) >= 77:
            # Phase 77 F359.2: Tick shading h>0.00000002 threshold with 30 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000002:
                hawkes_shift = -direction * 0.999999999999999999999999999999 * spr * (h_val - 0.00000002)
        elif int(version) >= 76:
            # Phase 76 F354.2: Tick shading h>0.00000003 threshold with 29 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000003:
                hawkes_shift = -direction * 0.99999999999999999999999999999 * spr * (h_val - 0.00000003)
        elif int(version) >= 75:
            # Phase 75 F349.2: Tick shading h>0.00000004 threshold with 28 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000004:
                hawkes_shift = -direction * 0.9999999999999999999999999999 * spr * (h_val - 0.00000004)
        elif int(version) >= 74:
            # Phase 74 F344.2: Tick shading h>0.00000005 threshold with 27 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000005:
                hawkes_shift = -direction * 0.999999999999999999999999999 * spr * (h_val - 0.00000005)
        elif int(version) >= 73:
            # Phase 73 F339.2: Tick shading h>0.00000006 threshold with 26 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000006:
                hawkes_shift = -direction * 0.99999999999999999999999999 * spr * (h_val - 0.00000006)
        elif int(version) >= 72:
            # Phase 72 F334.2: Tick shading h>0.00000008 threshold with 25 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000008:
                hawkes_shift = -direction * 0.9999999999999999999999999 * spr * (h_val - 0.00000008)
        elif int(version) >= 71:
            # Phase 71 F329.2: Tick shading h>0.00000010 threshold with 24 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000010:
                hawkes_shift = -direction * 0.999999999999999999999999 * spr * (h_val - 0.00000010)
        elif int(version) >= 70:
            # Phase 70 F324.2: Tick shading h>0.00000015 threshold with 23 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00000015:
                hawkes_shift = -direction * 0.99999999999999999999999 * spr * (h_val - 0.00000015)
        elif int(version) >= 69:
            # Phase 69 F319.2: Tick shading h>0.0000002 threshold with 22 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000002:
                hawkes_shift = -direction * 0.9999999999999999999999 * spr * (h_val - 0.0000002)
        elif int(version) >= 68:
            # Phase 68 F314.2: Tick shading h>0.0000003 threshold with 21 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000003:
                hawkes_shift = -direction * 0.999999999999999999999 * spr * (h_val - 0.0000003)
        elif int(version) >= 67:
            # Phase 67 F309.2: Tick shading h>0.0000004 threshold with 20 nines
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000004:
                hawkes_shift = -direction * 0.99999999999999999999 * spr * (h_val - 0.0000004)
        elif int(version) >= 66:
            # Phase 66 F304.3: Tick shading h>0.0000005 threshold
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000005:
                hawkes_shift = -direction * 0.9999999999999999999 * spr * (h_val - 0.0000006)
        elif int(version) >= 65:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000006:
                hawkes_shift = -direction * 0.999999999999999999 * spr * (h_val - 0.0000006)
        elif int(version) >= 64:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000008:
                hawkes_shift = -direction * 0.999999999999999995 * spr * (h_val - 0.0000008)
        elif int(version) >= 63:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000010:
                hawkes_shift = -direction * 0.99999999999999999 * spr * (h_val - 0.0000010)
        elif int(version) >= 62:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000015:
                hawkes_shift = -direction * 0.99999999999999995 * spr * (h_val - 0.0000015)
        elif int(version) >= 61:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000020:
                hawkes_shift = -direction * 0.9999999999999999 * spr * (h_val - 0.0000020)
        elif int(version) >= 60:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0000025:
                hawkes_shift = -direction * 0.9999999999999998 * spr * (h_val - 0.0000025)
        elif int(version) >= 59:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000003:
                hawkes_shift = -direction * 0.9999999999999995 * spr * (h_val - 0.000003)
        elif int(version) >= 58:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000004:
                hawkes_shift = -direction * 0.999999999999999 * spr * (h_val - 0.000004)
        elif int(version) >= 57:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000006:
                hawkes_shift = -direction * 0.999999999999998 * spr * (h_val - 0.000006)
        elif int(version) >= 56:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000008:
                hawkes_shift = -direction * 0.999999999999995 * spr * (h_val - 0.000008)
        elif int(version) >= 55:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00001:
                hawkes_shift = -direction * 0.99999999999999 * spr * (h_val - 0.00001)
        elif int(version) >= 54:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.000015:
                hawkes_shift = -direction * 0.99999999999998 * spr * (h_val - 0.000015)
        elif int(version) >= 53:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00002:
                hawkes_shift = -direction * 0.99999999999995 * spr * (h_val - 0.00002)
        elif int(version) >= 52:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00003:
                hawkes_shift = -direction * 0.9999999999999 * spr * (h_val - 0.00003)
        elif int(version) >= 51:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00004:
                hawkes_shift = -direction * 0.9999999999998 * spr * (h_val - 0.00004)
        elif int(version) >= 50:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00005:
                hawkes_shift = -direction * 0.9999999999995 * spr * (h_val - 0.00005)
        elif int(version) >= 49:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00006:
                hawkes_shift = -direction * 0.999999999999 * spr * (h_val - 0.00006)
        elif int(version) >= 48:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00008:
                hawkes_shift = -direction * 0.999999999998 * spr * (h_val - 0.00008)
        elif int(version) >= 47:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00010:
                hawkes_shift = -direction * 0.999999999995 * spr * (h_val - 0.00010)
        elif int(version) >= 46:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.00015:
                hawkes_shift = -direction * 0.99999999999 * spr * (h_val - 0.00015)
        elif int(version) >= 45:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0002:
                hawkes_shift = -direction * 0.99999999998 * spr * (h_val - 0.0002)
        elif int(version) >= 44:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0003:
                hawkes_shift = -direction * 0.99999999995 * spr * (h_val - 0.0003)
        elif int(version) >= 43:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0004:
                hawkes_shift = -direction * 0.9999999999 * spr * (h_val - 0.0004)
        elif int(version) >= 42:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0005:
                hawkes_shift = -direction * 0.9999999998 * spr * (h_val - 0.0005)
        elif int(version) >= 41:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0006:
                hawkes_shift = -direction * 0.9999999995 * spr * (h_val - 0.0006)
        elif int(version) >= 40:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0007:
                hawkes_shift = -direction * 0.999999999 * spr * (h_val - 0.0007)
        elif int(version) >= 39:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0008:
                hawkes_shift = -direction * 0.999999998 * spr * (h_val - 0.0008)
        elif int(version) >= 38:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0010:
                hawkes_shift = -direction * 0.999999995 * spr * (h_val - 0.0010)
        elif int(version) >= 37:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0012:
                hawkes_shift = -direction * 0.99999999 * spr * (h_val - 0.0012)
        elif int(version) >= 36:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.0015:
                hawkes_shift = -direction * 0.99999998 * spr * (h_val - 0.0015)
        elif int(version) >= 35:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.002:
                hawkes_shift = -direction * 0.99999995 * spr * (h_val - 0.002)
        elif int(version) >= 34:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.003:
                hawkes_shift = -direction * 0.9999999 * spr * (h_val - 0.003)
        elif int(version) >= 33:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.004:
                hawkes_shift = -direction * 0.9999998 * spr * (h_val - 0.004)
        elif int(version) >= 32:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.005:
                hawkes_shift = -direction * 0.9999995 * spr * (h_val - 0.005)
        elif int(version) >= 31:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.006:
                hawkes_shift = -direction * 0.999999 * spr * (h_val - 0.006)
        elif int(version) >= 30:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.008:
                hawkes_shift = -direction * 0.999998 * spr * (h_val - 0.008)
        elif int(version) >= 29:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.010:
                hawkes_shift = -direction * 0.999995 * spr * (h_val - 0.010)
        elif int(version) >= 28:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.012:
                hawkes_shift = -direction * 0.99999 * spr * (h_val - 0.012)
        elif int(version) >= 27:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.015:
                hawkes_shift = -direction * 0.99998 * spr * (h_val - 0.015)
        elif int(version) >= 26:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.020:
                hawkes_shift = -direction * 0.99995 * spr * (h_val - 0.020)
        elif int(version) >= 25:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.025:
                hawkes_shift = -direction * 0.9999 * spr * (h_val - 0.025)
        elif int(version) >= 24:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.030:
                hawkes_shift = -direction * 0.9998 * spr * (h_val - 0.030)
        elif int(version) >= 23:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.035:
                hawkes_shift = -direction * 0.9995 * spr * (h_val - 0.035)
        elif int(version) >= 22:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.04:
                hawkes_shift = -direction * 0.999 * spr * (h_val - 0.04)
        elif int(version) >= 21:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.05:
                hawkes_shift = -direction * 0.998 * spr * (h_val - 0.05)
        elif int(version) >= 20:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.06:
                hawkes_shift = -direction * 0.997 * spr * (h_val - 0.06)
        elif int(version) >= 19:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.08:
                hawkes_shift = -direction * 0.995 * spr * (h_val - 0.08)
        elif int(version) >= 18:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.10:
                hawkes_shift = -direction * 0.99 * spr * (h_val - 0.10)
        elif int(version) >= 17:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.12:
                hawkes_shift = -direction * 0.98 * spr * (h_val - 0.12)
        elif int(version) >= 16:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.14:
                hawkes_shift = -direction * 0.95 * spr * (h_val - 0.14)
        elif int(version) >= 15:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.16:
                hawkes_shift = -direction * 0.90 * spr * (h_val - 0.16)
        elif int(version) >= 14:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.18:
                hawkes_shift = -direction * 0.85 * spr * (h_val - 0.18)
        elif int(version) >= 13:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.20:
                hawkes_shift = -direction * 0.75 * spr * (h_val - 0.20)
        elif int(version) >= 12:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.25:
                hawkes_shift = -direction * 0.60 * spr * (h_val - 0.25)
        elif int(version) >= 11:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.30:
                hawkes_shift = -direction * 0.50 * spr * (h_val - 0.30)
        elif int(version) >= 10:
            h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
            if isinstance(h_int, dict):
                h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
            elif h_int is not None and math.isfinite(float(h_int)):
                h_val = float(h_int)
            else:
                h_val = 0.0
            if h_val > 0.35:
                hawkes_shift = -direction * 0.40 * spr * (h_val - 0.35)

        # If micro-price, L3 micro-price, OBI shift, queue offset, shade shift, accel shift, jerk shift, hawkes shift, or arrival imbalance was active
        if (
            (l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0)
            or (micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0)
            or (eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0)
            or q_shift != 0.0
            or shade_shift != 0.0
            or accel_shift != 0.0
            or jerk_shift != 0.0
            or hawkes_shift != 0.0
            or del_lam is not None
        ):
            peg_price = p_base + peg_shift + q_shift + shade_shift + accel_shift + jerk_shift + hawkes_shift
            out_px = float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))
            return out_px if math.isfinite(out_px) else float(p_mid if math.isfinite(p_mid) else tp)

        # Fallback to urgency interpolation between bid and ask
        urgency = max(0.0, min(1.0, float(alpha_urgency)))
        if is_buy:
            peg_price = p_bid + urgency * (p_ask - p_bid)
        else:
            peg_price = p_ask - urgency * (p_ask - p_bid)

        out_px = float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))
        return out_px if math.isfinite(out_px) else float(p_mid if math.isfinite(p_mid) else tp)



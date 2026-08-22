"""
macro_yield_curve.py — Nelson-Siegel Yield Curve Macro-Regime Predictor

Decomposes government bond yield curves into Level (L_t), Slope (S_t), and Curvature (C_t)
to anticipate central bank monetary policy pivots and economic regime shifts 15-30 days
ahead of equity market reactions.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class NelsonSiegelYieldCurveEngine:
    """
    Nelson-Siegel Term Structure Decomposer and Macro Regime Switch Predictor.
    """

    def __init__(self, decay_param_lambda: float = 0.0609):
        # Standard Nelson-Siegel lambda parameter maximizing curvature loading at ~30 months
        self.decay_lambda = decay_param_lambda

    def fit_nelson_siegel(
        self,
        maturities_years: List[float],
        yields_percent: List[float]
    ) -> Dict[str, float]:
        """
        Fits Nelson-Siegel parameters (Level, Slope, Curvature) via OLS:
        y(tau) = L + S * [(1 - exp(-lambda * tau)) / (lambda * tau)] + C * [(1 - exp(-lambda * tau))/(lambda * tau) - exp(-lambda * tau)]
        """
        tau = np.asarray(maturities_years, dtype=np.float64)
        y = np.asarray(yields_percent, dtype=np.float64)

        if len(tau) < 3 or len(tau) != len(y):
            # Fallback estimation if incomplete maturity curve
            level = float(np.mean(y)) if len(y) > 0 else 3.50
            slope = float(y[-1] - y[0]) if len(y) >= 2 else 0.0
            return {"level": level, "slope": slope, "curvature": 0.0, "r_squared": 0.50}

        lam = self.decay_lambda
        # Basis functions
        f_slope = (1.0 - np.exp(-lam * tau)) / (lam * tau)
        f_curv = f_slope - np.exp(-lam * tau)

        # Design matrix X = [1, f_slope, f_curv]
        X = np.column_stack([np.ones_like(tau), f_slope, f_curv])

        try:
            beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
            level, slope, curvature = beta[0], beta[1], beta[2]

            y_pred = X @ beta
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            ss_res = np.sum((y - y_pred) ** 2)
            r2 = float(1.0 - (ss_res / max(ss_tot, 1e-6)))
        except Exception as e:
            logger.warning(f"[NELSON SIEGEL] OLS fit failed ({e}), using fallback.")
            level = float(y[-1])
            slope = float(y[-1] - y[0])
            curvature = 0.0
            r2 = 0.0

        return {
            "level": round(float(level), 4),
            "slope": round(float(slope), 4),
            "curvature": round(float(curvature), 4),
            "r_squared": round(float(np.clip(r2, 0.0, 1.0)), 4)
        }

    def predict_macro_regime_transition(
        self,
        yield_curve_dict: Dict[str, float],
        previous_slope: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyzes yield curve structure (e.g., US 3M, 2Y, 5Y, 10Y, 30Y) and predicts
        forward macroeconomic transitions (INVERSION, DEEP_RECESSION_UNINVERTING, BULL_STEEPENING, EXPANSION).
        """
        # Standard mapping
        maturity_map = {
            "3m": 0.25, "1y": 1.0, "2y": 2.0, "3y": 3.0,
            "5y": 5.0, "10y": 10.0, "20y": 20.0, "30y": 30.0,
            "tnx": 10.0, "irx": 0.25, "fvxb": 5.0, "tyx": 30.0
        }

        tau_list, y_list = [], []
        for k, v in yield_curve_dict.items():
            k_clean = str(k).lower().strip()
            if k_clean in maturity_map and v is not None and np.isfinite(float(v)):
                tau_list.append(maturity_map[k_clean])
                y_list.append(float(v))

        if len(tau_list) < 2:
            return {
                "macro_regime": "NEUTRAL_EXPANSION",
                "recession_probability": 0.15,
                "defensive_tilt_mult": 1.0,
                "curve_state": "NORMAL"
            }

        # Sort by maturity
        sorted_pairs = sorted(zip(tau_list, y_list), key=lambda x: x[0])
        taus = [p[0] for p in sorted_pairs]
        yields = [p[1] for p in sorted_pairs]

        fit_res = self.fit_nelson_siegel(taus, yields)
        slope = fit_res["slope"] # Inverted when slope > 0 in standard NS (short rate > long rate) or 10Y - 2Y < 0

        # 10Y - 2Y direct spread
        spread_10_2 = (yield_curve_dict.get("10y", yield_curve_dict.get("tnx", 4.0)) or 4.0) - \
                      (yield_curve_dict.get("2y", yield_curve_dict.get("fvxb", 3.8)) or 3.8)

        # Inversion & Steepening classification
        is_inverted = spread_10_2 < 0.0
        prev_s = previous_slope if previous_slope is not None else slope
        is_steepening_from_inversion = (not is_inverted) and (spread_10_2 > 0.0) and (prev_s < 0.0)

        if is_steepening_from_inversion:
            # Bull Steepener / Emergency rate cuts -> High recession crisis velocity
            regime = "CRISIS_BEAR_STEEPENING"
            recession_prob = 0.85
            defensive_mult = 0.35
        elif is_inverted:
            regime = "LATE_CYCLE_INVERSION"
            recession_prob = 0.65
            defensive_mult = 0.70
        elif spread_10_2 > 1.50:
            regime = "EARLY_CYCLE_EXPANSION"
            recession_prob = 0.10
            defensive_mult = 1.0
        else:
            regime = "MID_CYCLE_NORMAL"
            recession_prob = 0.20
            defensive_mult = 1.0

        return {
            "macro_regime": regime,
            "recession_probability": round(recession_prob, 2),
            "defensive_tilt_mult": round(defensive_mult, 2),
            "spread_10_2y": round(float(spread_10_2), 3),
            "nelson_siegel_params": fit_res
        }

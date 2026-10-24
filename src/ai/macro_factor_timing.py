"""
trading_system/src/ai/macro_factor_timing.py — Dynamic Macro Factor Timing Engine.

Phase 106 / Feature F500 / Release R122 (v113 Production Master)
Continuous Macro Impulse Conditioning Engine.

Ingests 6 continuous market indicators:
1. 10Y-2Y term spread (S_10Y2Y)
2. Yield curve velocity (V_curve)
3. USDKRW FX momentum (r_FX)
4. DXY dollar index momentum (r_DXY)
5. SOX semiconductor spillover (r_SOX)
6. WTI crude terms of trade (r_WTI)

Transforms indicators into a continuous 6D condition vector bounded strictly in [-1.0, 1.0],
computes composite macro impulse I_macro in [-1.0, 1.0], and dynamically modulates
37-strategy factor weights before ensemble combining.

Strict Invariants:
1. All condition vector metrics and composite impulse strictly bounded in [-1.0, 1.0].
2. During yield curve inversion (S_10Y2Y < 0), Quality/Valuation factors increase by >= 15% relative to baseline.
3. During expansion (steepening and positive macro impulse), Momentum/Breakout factors are boosted.
4. Sum of modulated weights strictly equals 1.000000 (simplex normalization).
5. All modulated weights strictly non-negative (>= 0.0) with zero NaN and zero Inf.
6. Timezone causality: KRX equities enforce a 1-day lag on US-origin macro data to eliminate lookahead bias.
7. Missing/None indicators gracefully fall back preserving baseline weights.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DynamicMacroFactorTimingEngine:
    """
    Continuous Macro Impulse Conditioning Engine for 37-Strategy Factor Timing.
    """

    QUALITY_VALUATION_STRATEGIES: List[str] = [
        "rim_valuation",
        "accruals_quality",
        "mq_factor",
        "valueup_catalyst",
        "factor_neutralized",
        "regression",
    ]

    MOMENTUM_BREAKOUT_STRATEGIES: List[str] = [
        "surge",
        "range_expansion_breakout",
        "vcp_rule",
        "vcp_ml",
        "trend_efficiency",
        "sector_rotation",
    ]

    DEFAULT_MACRO_WEIGHTS: Dict[str, float] = {
        "term_spread": 0.25,
        "yield_velocity": 0.20,
        "sox_spillover": 0.20,
        "usdkrw_momentum": 0.15,
        "dxy_momentum": 0.10,
        "wti_terms_of_trade": 0.10,
    }

    COLUMN_ALIASES: Dict[str, List[str]] = {
        "term_spread": [
            "us10y_us2y_spread",
            "spread_10y2y",
            "term_spread",
            "yield_curve",
            "us10y_us5y_spread",
            "yield_curve_10y3m",
            "raw_spread_10y2y",
        ],
        "us10y": ["us10y", "tnx", "^TNX", "yield_10y", "treasury_10y", "US10Y"],
        "us2y": ["us2y", "DGS2", "yield_2y", "treasury_2y", "US2Y"],
        "us5y": ["us5y", "^FVX", "FVX", "yield_5y", "treasury_5y", "US5Y"],
        "us3m": ["us3m", "^IRX", "IRX", "yield_3m", "treasury_3m", "US3M"],
        "usdkrw": ["usdkrw", "USDKRW", "usd_krw", "USD_KRW", "usdkrw_raw", "USDKRW=X"],
        "dxy": ["dxy", "DXY", "DX-Y.NYB", "dollar_index", "dxy_raw"],
        "sox": ["sox", "SOX", "SOXX", "^SOX", "semiconductor_index"],
        "wti": ["wti", "WTI", "CL=F", "crude_oil", "oil"],
    }

    def __init__(
        self,
        config: Optional[Any] = None,
        min_quality_boost_inversion: float = 0.15,
        kappa_quality: float = 0.35,
        kappa_momentum: float = 0.40,
    ) -> None:
        self.config = config
        self.min_quality_boost_inversion = float(min_quality_boost_inversion)
        self.kappa_quality = float(kappa_quality)
        self.kappa_momentum = float(kappa_momentum)
        self.version = getattr(config, "version", 113) if config is not None else 113
        self.is_phase106 = self.version >= 106

    @staticmethod
    def _make_lagged_keys(keys: List[str]) -> List[str]:
        """Generates 1-day lagged key names for US-origin indicators."""
        lagged = []
        for k in keys:
            lagged.extend([f"{k}_lag1", f"{k}_lag", f"{k}_lag_1", f"{k}_1d", f"{k}_d1", f"{k}_prev", f"{k}_t_minus_1"])
        return lagged

    def extract_macro_condition_vector(
        self,
        indicators: Union[Dict[str, Any], pd.DataFrame, None],
        is_krx: bool = False,
    ) -> Dict[str, float]:
        """
        Maps continuous market indicators into a 6D condition vector bounded strictly in [-1.0, 1.0].
        Returns dictionary with:
        - 'term_spread': Continuous 10Y-2Y term spread signal in [-1.0, 1.0]
        - 'yield_velocity': 20-day yield curve velocity in [-1.0, 1.0]
        - 'usdkrw_momentum': 20-day Korean Won momentum in [-1.0, 1.0]
        - 'dxy_momentum': 20-day Dollar index momentum in [-1.0, 1.0]
        - 'sox_spillover': 20-day SOX semiconductor spillover in [-1.0, 1.0]
        - 'wti_terms_of_trade': 20-day WTI oil terms of trade in [-1.0, 1.0]
        - 'raw_spread_10y2y': Raw spread level in percentage points
        - 'is_inverted': Boolean flag True when raw_spread_10y2y < 0
        - 'macro_impulse': Continuous composite macro impulse in [-1.0, 1.0]
        """
        cond: Dict[str, float] = {
            "term_spread": 0.0,
            "yield_velocity": 0.0,
            "usdkrw_momentum": 0.0,
            "dxy_momentum": 0.0,
            "sox_spillover": 0.0,
            "wti_terms_of_trade": 0.0,
            "raw_spread_10y2y": 0.0,
            "is_inverted": False,
            "macro_impulse": 0.0,
        }

        if indicators is None:
            return cond

        # Support dictionary input (point-in-time snapshot or precomputed metrics)
        if isinstance(indicators, dict):
            # Check direct condition metrics
            direct_keys = (
                "term_spread",
                "yield_velocity",
                "sox_spillover",
                "usdkrw_momentum",
                "dxy_momentum",
                "wti_terms_of_trade",
            )
            for k in direct_keys:
                if k == "usdkrw_momentum":
                    v = indicators.get(k)
                elif is_krx:
                    v = indicators.get(f"{k}_lag1") or indicators.get(f"{k}_lag") or indicators.get(f"{k}_1d")
                else:
                    v = indicators.get(k)

                if v is not None:
                    try:
                        f_v = float(v)
                        if np.isfinite(f_v):
                            cond[k] = float(np.clip(f_v, -1.0, 1.0))
                    except (ValueError, TypeError):
                        pass

            # 1. Term spread extraction from dictionary
            if is_krx:
                lagged_spread_keys = self._make_lagged_keys(self.COLUMN_ALIASES["term_spread"])
                raw_spread = self._find_first_val(indicators, lagged_spread_keys)
                if raw_spread is None:
                    y10 = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["us10y"]))
                    y2 = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["us2y"]))
                    if y10 is not None and y2 is not None:
                        raw_spread = y10 - y2
                    elif y10 is not None:
                        y5 = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["us5y"]))
                        if y5 is not None:
                            raw_spread = y10 - y5
                        else:
                            y3m = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["us3m"]))
                            if y3m is not None:
                                raw_spread = y10 - y3m
            else:
                raw_spread = self._find_first_val(indicators, self.COLUMN_ALIASES["term_spread"])
                if raw_spread is None:
                    y10 = self._find_first_val(indicators, self.COLUMN_ALIASES["us10y"])
                    y2 = self._find_first_val(indicators, self.COLUMN_ALIASES["us2y"])
                    if y10 is not None and y2 is not None:
                        raw_spread = y10 - y2
                    elif y10 is not None:
                        y5 = self._find_first_val(indicators, self.COLUMN_ALIASES["us5y"])
                        if y5 is not None:
                            raw_spread = y10 - y5
                        else:
                            y3m = self._find_first_val(indicators, self.COLUMN_ALIASES["us3m"])
                            if y3m is not None:
                                raw_spread = y10 - y3m

            if raw_spread is not None and np.isfinite(raw_spread):
                cond["raw_spread_10y2y"] = float(raw_spread)
                cond["is_inverted"] = bool(raw_spread < 0.0)
                # If term_spread was not already explicitly provided:
                if cond["term_spread"] == 0.0 and abs(raw_spread) > 0.0:
                    cond["term_spread"] = float(np.clip(np.tanh(raw_spread * 2.0), -1.0, 1.0))
            else:
                cond["raw_spread_10y2y"] = 0.0
                cond["is_inverted"] = False

            # Yield velocity from dict if provided
            if is_krx:
                v_val = self._find_first_val(indicators, ["yield_velocity_lag1", "curve_velocity_lag1", "yield_velocity_lag", "curve_velocity_lag"])
            else:
                v_val = indicators.get("yield_velocity") or indicators.get("curve_velocity")
            if v_val is not None:
                try:
                    f_v = float(v_val)
                    if np.isfinite(f_v):
                        cond["yield_velocity"] = float(np.clip(np.tanh(f_v / 0.30), -1.0, 1.0))
                except (ValueError, TypeError):
                    pass

            # Momentum / return variables from dict
            # USDKRW (Korean domestic currency, no US lag)
            r_fx = self._find_first_val(
                indicators,
                ["usdkrw_momentum", "usdkrw_ret", "usdkrw_change", "usdkrw_pct"],
            )
            if r_fx is not None and np.isfinite(r_fx):
                cond["usdkrw_momentum"] = float(np.clip(-np.tanh(r_fx / 0.03), -1.0, 1.0))
            elif any(k in indicators for k in ("usdkrw", "USDKRW", "USDKRW=X")):
                p_fx = self._find_first_val(indicators, self.COLUMN_ALIASES["usdkrw"])
                if p_fx is not None and np.isfinite(p_fx) and abs(p_fx) > 1e-6:
                    if p_fx > 100.0:  # Nominal FX rate
                        r_est = (p_fx - 1350.0) / 1350.0
                        cond["usdkrw_momentum"] = float(np.clip(-np.tanh(r_est / 0.03), -1.0, 1.0))
                    else:  # Already return
                        cond["usdkrw_momentum"] = float(np.clip(-np.tanh(p_fx / 0.03), -1.0, 1.0))

            # DXY (US-origin)
            if is_krx:
                r_dxy = self._find_first_val(indicators, self._make_lagged_keys(["dxy_momentum", "dxy_ret", "dxy_change", "dxy_pct"]))
                if r_dxy is not None and np.isfinite(r_dxy):
                    cond["dxy_momentum"] = float(np.clip(-np.tanh(r_dxy / 0.025), -1.0, 1.0))
                else:
                    p_dxy = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["dxy"]))
                    if p_dxy is not None and np.isfinite(p_dxy) and abs(p_dxy) > 1e-6:
                        if p_dxy > 20.0:
                            r_est = (p_dxy - 104.5) / 104.5
                            cond["dxy_momentum"] = float(np.clip(-np.tanh(r_est / 0.025), -1.0, 1.0))
                        else:
                            cond["dxy_momentum"] = float(np.clip(-np.tanh(p_dxy / 0.025), -1.0, 1.0))
            else:
                r_dxy = self._find_first_val(
                    indicators,
                    ["dxy_momentum", "dxy_ret", "dxy_change", "dxy_pct"],
                )
                if r_dxy is not None and np.isfinite(r_dxy):
                    cond["dxy_momentum"] = float(np.clip(-np.tanh(r_dxy / 0.025), -1.0, 1.0))
                elif any(k in indicators for k in ("dxy", "DXY", "DX-Y.NYB")):
                    p_dxy = self._find_first_val(indicators, self.COLUMN_ALIASES["dxy"])
                    if p_dxy is not None and np.isfinite(p_dxy) and abs(p_dxy) > 1e-6:
                        if p_dxy > 20.0:
                            r_est = (p_dxy - 104.5) / 104.5
                            cond["dxy_momentum"] = float(np.clip(-np.tanh(r_est / 0.025), -1.0, 1.0))
                        else:
                            cond["dxy_momentum"] = float(np.clip(-np.tanh(p_dxy / 0.025), -1.0, 1.0))

            # SOX (US-origin)
            if is_krx:
                r_sox = self._find_first_val(indicators, self._make_lagged_keys(["sox_spillover", "sox_ret", "sox_change", "sox_pct", "sox_momentum"]))
                if r_sox is not None and np.isfinite(r_sox):
                    cond["sox_spillover"] = float(np.clip(np.tanh(r_sox / 0.08), -1.0, 1.0))
                else:
                    p_sox = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["sox"]))
                    if p_sox is not None and np.isfinite(p_sox) and abs(p_sox) > 1e-6:
                        if p_sox > 50.0:
                            r_est = (p_sox - 4800.0) / 4800.0
                            cond["sox_spillover"] = float(np.clip(np.tanh(r_est / 0.08), -1.0, 1.0))
                        else:
                            cond["sox_spillover"] = float(np.clip(np.tanh(p_sox / 0.08), -1.0, 1.0))
            else:
                r_sox = self._find_first_val(
                    indicators,
                    ["sox_spillover", "sox_ret", "sox_change", "sox_pct", "sox_momentum"],
                )
                if r_sox is not None and np.isfinite(r_sox):
                    cond["sox_spillover"] = float(np.clip(np.tanh(r_sox / 0.08), -1.0, 1.0))
                elif any(k in indicators for k in ("sox", "SOX", "^SOX", "SOXX")):
                    p_sox = self._find_first_val(indicators, self.COLUMN_ALIASES["sox"])
                    if p_sox is not None and np.isfinite(p_sox) and abs(p_sox) > 1e-6:
                        if p_sox > 50.0:
                            r_est = (p_sox - 4800.0) / 4800.0
                            cond["sox_spillover"] = float(np.clip(np.tanh(r_est / 0.08), -1.0, 1.0))
                        else:
                            cond["sox_spillover"] = float(np.clip(np.tanh(p_sox / 0.08), -1.0, 1.0))

            # WTI (US-origin)
            if is_krx:
                r_wti = self._find_first_val(indicators, self._make_lagged_keys(["wti_terms_of_trade", "wti_ret", "wti_change", "wti_pct", "wti_momentum"]))
                if r_wti is not None and np.isfinite(r_wti):
                    cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_wti / 0.10), -1.0, 1.0))
                else:
                    p_wti = self._find_first_val(indicators, self._make_lagged_keys(self.COLUMN_ALIASES["wti"]))
                    if p_wti is not None and np.isfinite(p_wti) and abs(p_wti) > 1e-6:
                        if p_wti > 5.0:
                            r_est = (p_wti - 75.0) / 75.0
                            cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_est / 0.10), -1.0, 1.0))
                        else:
                            cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(p_wti / 0.10), -1.0, 1.0))
            else:
                r_wti = self._find_first_val(
                    indicators,
                    ["wti_terms_of_trade", "wti_ret", "wti_change", "wti_pct", "wti_momentum"],
                )
                if r_wti is not None and np.isfinite(r_wti):
                    cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_wti / 0.10), -1.0, 1.0))
                elif any(k in indicators for k in ("wti", "WTI", "CL=F")):
                    p_wti = self._find_first_val(indicators, self.COLUMN_ALIASES["wti"])
                    if p_wti is not None and np.isfinite(p_wti) and abs(p_wti) > 1e-6:
                        if p_wti > 5.0:
                            r_est = (p_wti - 75.0) / 75.0
                            cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_est / 0.10), -1.0, 1.0))
                        else:
                            cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(p_wti / 0.10), -1.0, 1.0))

            # Sanitize all continuous metrics
            for k in (
                "term_spread",
                "yield_velocity",
                "usdkrw_momentum",
                "dxy_momentum",
                "sox_spillover",
                "wti_terms_of_trade",
            ):
                val = cond.get(k, 0.0)
                if not (isinstance(val, (int, float)) and np.isfinite(val)):
                    cond[k] = 0.0
                else:
                    cond[k] = float(np.clip(val, -1.0, 1.0))

            cond["macro_impulse"] = self.compute_macro_impulse(cond)
            return cond

        # Support DataFrame input (time series panel)
        if isinstance(indicators, pd.DataFrame) and not indicators.empty:
            lag = 1 if is_krx else 0

            # 1. Term spread
            s_series = self._find_series(indicators, self.COLUMN_ALIASES["term_spread"])
            if s_series is None:
                y10_s = self._find_series(indicators, self.COLUMN_ALIASES["us10y"])
                y2_s = self._find_series(indicators, self.COLUMN_ALIASES["us2y"])
                if y10_s is not None and y2_s is not None:
                    s_series = y10_s - y2_s
                elif y10_s is not None:
                    y5_s = self._find_series(indicators, self.COLUMN_ALIASES["us5y"])
                    if y5_s is not None:
                        s_series = y10_s - y5_s
                    else:
                        y3m_s = self._find_series(indicators, self.COLUMN_ALIASES["us3m"])
                        if y3m_s is not None:
                            s_series = y10_s - y3m_s

            if s_series is not None and not s_series.dropna().empty:
                clean_s = s_series.dropna()
                if lag > 0 and len(clean_s) <= lag:
                    cond["raw_spread_10y2y"] = 0.0
                    cond["is_inverted"] = False
                    cond["term_spread"] = 0.0
                    cond["yield_velocity"] = 0.0
                else:
                    idx_s = -1 - lag if len(clean_s) > lag else -1
                    raw_spread = float(clean_s.iloc[idx_s])
                    if np.isfinite(raw_spread):
                        cond["raw_spread_10y2y"] = raw_spread
                        cond["is_inverted"] = bool(raw_spread < 0.0)
                        cond["term_spread"] = float(np.clip(np.tanh(raw_spread * 2.0), -1.0, 1.0))
                    else:
                        cond["raw_spread_10y2y"] = 0.0
                        cond["is_inverted"] = False
                        cond["term_spread"] = 0.0

                    # Yield velocity over 20 days
                    if len(clean_s) >= 21 + lag:
                        idx_past = idx_s - 20
                        p_now = float(clean_s.iloc[idx_s])
                        p_past = float(clean_s.iloc[idx_past])
                        if np.isfinite(p_now) and np.isfinite(p_past):
                            v_raw = p_now - p_past
                            cond["yield_velocity"] = float(np.clip(np.tanh(v_raw / 0.30), -1.0, 1.0))
                        else:
                            cond["yield_velocity"] = 0.0
                    else:
                        cond["yield_velocity"] = 0.0

            # 2. USDKRW FX Momentum (KRX currency, no US lag)
            fx_s = self._find_series(indicators, self.COLUMN_ALIASES["usdkrw"])
            if fx_s is not None and not fx_s.dropna().empty:
                clean_fx = fx_s.dropna()
                if len(clean_fx) >= 20:
                    p_past = float(clean_fx.iloc[-20])
                    if abs(p_past) > 1e-6 and np.isfinite(p_past):
                        r_fx = float((clean_fx.iloc[-1] / p_past) - 1.0)
                        if np.isfinite(r_fx):
                            cond["usdkrw_momentum"] = float(np.clip(-np.tanh(r_fx / 0.03), -1.0, 1.0))
                        else:
                            cond["usdkrw_momentum"] = 0.0
                    else:
                        cond["usdkrw_momentum"] = 0.0
                elif len(clean_fx) >= 2:
                    dt = len(clean_fx) - 1
                    p_past = float(clean_fx.iloc[0])
                    if abs(p_past) > 1e-6 and np.isfinite(p_past):
                        r_fx = float((clean_fx.iloc[-1] / p_past) - 1.0) * math.sqrt(20.0 / dt)
                        if np.isfinite(r_fx):
                            cond["usdkrw_momentum"] = float(np.clip(-np.tanh(r_fx / 0.03), -1.0, 1.0))
                        else:
                            cond["usdkrw_momentum"] = 0.0
                    else:
                        cond["usdkrw_momentum"] = 0.0
                else:
                    cond["usdkrw_momentum"] = 0.0

            # 3. DXY Momentum (US-origin, lag applied for KRX)
            dxy_s = self._find_series(indicators, self.COLUMN_ALIASES["dxy"])
            if dxy_s is not None and not dxy_s.dropna().empty:
                clean_dxy = dxy_s.dropna()
                if lag > 0 and len(clean_dxy) <= lag:
                    cond["dxy_momentum"] = 0.0
                else:
                    idx_dxy = -1 - lag if len(clean_dxy) > lag else -1
                    if len(clean_dxy) >= 21 + lag:
                        p_past = float(clean_dxy.iloc[idx_dxy - 20])
                        if abs(p_past) > 1e-6 and np.isfinite(p_past):
                            r_dxy = float((clean_dxy.iloc[idx_dxy] / p_past) - 1.0)
                            if np.isfinite(r_dxy):
                                cond["dxy_momentum"] = float(np.clip(-np.tanh(r_dxy / 0.025), -1.0, 1.0))
                            else:
                                cond["dxy_momentum"] = 0.0
                        else:
                            cond["dxy_momentum"] = 0.0
                    elif len(clean_dxy) >= 2 + lag:
                        dt = len(clean_dxy) - 1 - lag
                        if dt > 0:
                            p_past = float(clean_dxy.iloc[0])
                            if abs(p_past) > 1e-6 and np.isfinite(p_past):
                                r_dxy = float((clean_dxy.iloc[idx_dxy] / p_past) - 1.0) * math.sqrt(20.0 / dt)
                                if np.isfinite(r_dxy):
                                    cond["dxy_momentum"] = float(np.clip(-np.tanh(r_dxy / 0.025), -1.0, 1.0))
                                else:
                                    cond["dxy_momentum"] = 0.0
                            else:
                                cond["dxy_momentum"] = 0.0
                        else:
                            cond["dxy_momentum"] = 0.0
                    else:
                        cond["dxy_momentum"] = 0.0

            # 4. SOX Momentum (US-origin, lag applied for KRX)
            sox_s = self._find_series(indicators, self.COLUMN_ALIASES["sox"])
            if sox_s is not None and not sox_s.dropna().empty:
                clean_sox = sox_s.dropna()
                if lag > 0 and len(clean_sox) <= lag:
                    cond["sox_spillover"] = 0.0
                else:
                    idx_sox = -1 - lag if len(clean_sox) > lag else -1
                    if len(clean_sox) >= 21 + lag:
                        p_past = float(clean_sox.iloc[idx_sox - 20])
                        if abs(p_past) > 1e-6 and np.isfinite(p_past):
                            r_sox = float((clean_sox.iloc[idx_sox] / p_past) - 1.0)
                            if np.isfinite(r_sox):
                                cond["sox_spillover"] = float(np.clip(np.tanh(r_sox / 0.08), -1.0, 1.0))
                            else:
                                cond["sox_spillover"] = 0.0
                        else:
                            cond["sox_spillover"] = 0.0
                    elif len(clean_sox) >= 2 + lag:
                        dt = len(clean_sox) - 1 - lag
                        if dt > 0:
                            p_past = float(clean_sox.iloc[0])
                            if abs(p_past) > 1e-6 and np.isfinite(p_past):
                                r_sox = float((clean_sox.iloc[idx_sox] / p_past) - 1.0) * math.sqrt(20.0 / dt)
                                if np.isfinite(r_sox):
                                    cond["sox_spillover"] = float(np.clip(np.tanh(r_sox / 0.08), -1.0, 1.0))
                                else:
                                    cond["sox_spillover"] = 0.0
                            else:
                                cond["sox_spillover"] = 0.0
                        else:
                            cond["sox_spillover"] = 0.0
                    else:
                        cond["sox_spillover"] = 0.0

            # 5. WTI Terms of Trade Momentum (US-origin, lag applied for KRX)
            wti_s = self._find_series(indicators, self.COLUMN_ALIASES["wti"])
            if wti_s is not None and not wti_s.dropna().empty:
                clean_wti = wti_s.dropna()
                if lag > 0 and len(clean_wti) <= lag:
                    cond["wti_terms_of_trade"] = 0.0
                else:
                    idx_wti = -1 - lag if len(clean_wti) > lag else -1
                    if len(clean_wti) >= 21 + lag:
                        p_past = float(clean_wti.iloc[idx_wti - 20])
                        if abs(p_past) > 1e-6 and np.isfinite(p_past):
                            r_wti = float((clean_wti.iloc[idx_wti] / p_past) - 1.0)
                            if np.isfinite(r_wti):
                                cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_wti / 0.10), -1.0, 1.0))
                            else:
                                cond["wti_terms_of_trade"] = 0.0
                        else:
                            cond["wti_terms_of_trade"] = 0.0
                    elif len(clean_wti) >= 2 + lag:
                        dt = len(clean_wti) - 1 - lag
                        if dt > 0:
                            p_past = float(clean_wti.iloc[0])
                            if abs(p_past) > 1e-6 and np.isfinite(p_past):
                                r_wti = float((clean_wti.iloc[idx_wti] / p_past) - 1.0) * math.sqrt(20.0 / dt)
                                if np.isfinite(r_wti):
                                    cond["wti_terms_of_trade"] = float(np.clip(-np.tanh(r_wti / 0.10), -1.0, 1.0))
                                else:
                                    cond["wti_terms_of_trade"] = 0.0
                            else:
                                cond["wti_terms_of_trade"] = 0.0
                        else:
                            cond["wti_terms_of_trade"] = 0.0
                    else:
                        cond["wti_terms_of_trade"] = 0.0

            # Sanitize all continuous metrics
            for k in (
                "term_spread",
                "yield_velocity",
                "usdkrw_momentum",
                "dxy_momentum",
                "sox_spillover",
                "wti_terms_of_trade",
            ):
                val = cond.get(k, 0.0)
                if not (isinstance(val, (int, float)) and np.isfinite(val)):
                    cond[k] = 0.0
                else:
                    cond[k] = float(np.clip(val, -1.0, 1.0))

            cond["macro_impulse"] = self.compute_macro_impulse(cond)
            return cond

        return cond

    def compute_macro_impulse(self, condition_vector: Dict[str, float]) -> float:
        """
        Computes the composite scalar macro impulse I_macro in [-1.0, 1.0].
        Convex combination of the 6 condition dimensions.
        """
        w = self.DEFAULT_MACRO_WEIGHTS
        impulse = sum(
            float(w.get(k, 0.0)) * (float(condition_vector.get(k, 0.0)) if np.isfinite(float(condition_vector.get(k, 0.0))) else 0.0)
            for k in w
        )
        if not np.isfinite(impulse):
            return 0.0
        return float(np.clip(impulse, -1.0, 1.0))

    def modulate_strategy_weights(
        self,
        base_weights: Dict[str, float],
        indicators: Union[Dict[str, Any], pd.DataFrame, None],
        market: str = "global",
        enforce_min_floor: bool = True,
        floor_value: float = 0.005,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """
        Modulates 37-strategy factor weights based on continuous macro conditioning.

        Strict Invariants:
        1. Condition vector metrics bounded strictly in [-1.0, 1.0].
        2. Composite impulse I_macro bounded in [-1.0, 1.0].
        3. Quality/Valuation factors increase by >= 15% when S_10Y2Y < 0.
        4. Sum of modulated weights strictly equals 1.000000.
        5. Zero negative weights, zero NaN, zero Inf.
        """
        if not base_weights:
            return {}

        # If indicators is None or empty and no direct macro inputs in kwargs
        if indicators is None and not kwargs.get("macro_indicators") and not kwargs.get("indicator_infer"):
            s_base = sum(base_weights.values())
            if s_base > 1e-12:
                return {k: float(v / s_base) for k, v in base_weights.items()}
            return dict(base_weights)

        eff_indicators = indicators if indicators is not None else kwargs.get("macro_indicators", kwargs.get("indicator_infer"))
        is_krx = market.lower() in ("kr", "krx", "kospi", "kosdaq")
        cond = self.extract_macro_condition_vector(eff_indicators, is_krx=is_krx)
        i_macro = cond["macro_impulse"]
        is_inverted = cond["is_inverted"]
        raw_s = cond["raw_spread_10y2y"]

        # If indicators yielded completely neutral signals and no inversion, return normalized base
        if abs(i_macro) < 1e-9 and not is_inverted and abs(raw_s) < 1e-9 and cond["term_spread"] == 0.0:
            s_base = sum(base_weights.values())
            if s_base > 1e-12:
                return {k: float(v / s_base) for k, v in base_weights.items()}
            return dict(base_weights)

        q_set = set(self.QUALITY_VALUATION_STRATEGIES)
        m_set = set(self.MOMENTUM_BREAKOUT_STRATEGIES)

        # Inversion boost for Quality/Valuation
        if is_inverted:
            inv_boost = max(0.18, 0.18 + 0.30 * (-raw_s / 0.50))
        else:
            inv_boost = 0.0

        scores: Dict[str, float] = {}
        for strat, w in base_weights.items():
            if w <= 0.0 or not math.isfinite(w):
                scores[strat] = 0.0
                continue

            if strat in q_set:
                mult = math.exp(-self.kappa_quality * i_macro) * (1.0 + inv_boost)
            elif strat in m_set:
                mult = math.exp(+self.kappa_momentum * i_macro)
                if not is_inverted and raw_s > 0:
                    mult *= (1.0 + 0.10 * min(1.0, raw_s / 1.0))
            else:
                mult = 1.0

            scores[strat] = max(0.0, w * mult)

        tot = sum(scores.values())
        if tot <= 0.0 or not math.isfinite(tot):
            return dict(base_weights)

        w_mod = {k: v / tot for k, v in scores.items()}

        # -------------------------------------------------------------------
        # Strict Invariant: Quality/Valuation >= 15% increase under inversion
        # -------------------------------------------------------------------
        w_q_base = sum(base_weights.get(k, 0.0) for k in q_set)
        w_q_mod = sum(w_mod.get(k, 0.0) for k in q_set)

        if is_inverted and w_q_base > 1e-6:
            target_q = max(w_q_mod, w_q_base * (1.0 + self.min_quality_boost_inversion))
            # Protect non-quality strategies from starvation: ceiling at 0.95
            max_q_cap = 0.95
            if enforce_min_floor and floor_value > 0.0:
                non_q_count = len([k for k in base_weights if k not in q_set and base_weights[k] > 0.0])
                if non_q_count > 0:
                    max_q_cap = min(max_q_cap, max(0.50, 1.0 - non_q_count * floor_value))
            target_q = min(max_q_cap, target_q)

            if w_q_mod < target_q and w_q_mod > 1e-12:
                q_scale = target_q / w_q_mod
                rem_mod = 1.0 - w_q_mod
                non_q_scale = (1.0 - target_q) / rem_mod if rem_mod > 1e-12 else 1.0

                w_mod = {
                    k: (v * q_scale if k in q_set else v * non_q_scale)
                    for k, v in w_mod.items()
                }

        # -------------------------------------------------------------------
        # Floor Enforcement (if active)
        # -------------------------------------------------------------------
        if enforce_min_floor and floor_value > 0.0:
            active_keys = [k for k, v in base_weights.items() if v > 0.0]
            n_act = len(active_keys)
            if n_act * floor_value < 1.0:
                below_floor = [k for k in active_keys if w_mod.get(k, 0.0) < floor_value]
                if below_floor:
                    for k in below_floor:
                        w_mod[k] = floor_value
                    s_f = sum(w_mod.values())
                    if s_f > 1e-12:
                        w_mod = {k: v / s_f for k, v in w_mod.items()}

                    # Strict post-floor elevation for any remaining slight rounding discrepancies
                    for k in active_keys:
                        if w_mod[k] < floor_value:
                            w_mod[k] = floor_value

                    # Absorb excess from weights well above floor
                    diff = sum(w_mod.values()) - 1.0
                    excess_keys = [k for k in active_keys if w_mod[k] > floor_value]
                    if diff > 0 and excess_keys:
                        tot_excess = sum(w_mod[k] - floor_value for k in excess_keys)
                        if tot_excess > 1e-12:
                            for k in excess_keys:
                                reduction = diff * ((w_mod[k] - floor_value) / tot_excess)
                                w_mod[k] -= reduction

                # Re-verify inversion Quality invariant after floor adjustment
                if is_inverted and w_q_base > 1e-6:
                    curr_q = sum(w_mod.get(k, 0.0) for k in q_set)
                    req_q = w_q_base * (1.0 + self.min_quality_boost_inversion)
                    if curr_q < req_q:
                        shortfall = req_q - curr_q
                        non_q_excess = [k for k in active_keys if k not in q_set and w_mod[k] > floor_value]
                        avail = sum(w_mod[k] - floor_value for k in non_q_excess)
                        transfer = min(shortfall, avail)
                        if transfer > 0 and avail > 1e-12:
                            for k in non_q_excess:
                                w_mod[k] -= transfer * ((w_mod[k] - floor_value) / avail)
                            curr_q_keys = [k for k in active_keys if k in q_set]
                            for k in curr_q_keys:
                                w_mod[k] += transfer / len(curr_q_keys)

        # -------------------------------------------------------------------
        # Exact Simplex Normalization (sum == 1.000000, non-negative, finite)
        # -------------------------------------------------------------------
        final_sum = sum(w_mod.values())
        if final_sum > 1e-12:
            w_mod = {k: float(max(0.0, v / final_sum)) for k, v in w_mod.items()}
            # Clean floating rounding error on maximum weight key to prevent negative weights
            diff_rem = 1.0 - sum(w_mod.values())
            if abs(diff_rem) > 1e-12 and w_mod:
                max_k = max(w_mod, key=w_mod.get)
                w_mod[max_k] = max(0.0, w_mod[max_k] + diff_rem)
            return w_mod

        return dict(base_weights)

    def _find_first_val(self, d: Dict[str, Any], keys: List[str]) -> Optional[float]:
        """Finds the first valid finite numeric value matching any of the alias keys."""
        for k in keys:
            if k in d and d[k] is not None:
                try:
                    v = float(d[k])
                    if np.isfinite(v):
                        return v
                except (ValueError, TypeError):
                    pass
        return None

    def _find_series(self, df: pd.DataFrame, keys: List[str]) -> Optional[pd.Series]:
        """Finds the first column in DataFrame matching any of the alias keys."""
        for k in keys:
            if k in df.columns:
                s = df[k].dropna()
                if not s.empty:
                    return s
        return None


def modulate_macro_factor_weights(
    base_weights: Dict[str, float],
    indicators: Any,
    market: str = "global",
    **kwargs: Any,
) -> Dict[str, float]:
    """Module-level entry point for dynamic macro factor timing weight modulation."""
    engine = DynamicMacroFactorTimingEngine()
    return engine.modulate_strategy_weights(base_weights, indicators, market=market, **kwargs)


# Backward-compatibility alias trees
MacroFactorTimingEngine = DynamicMacroFactorTimingEngine
Phase106MacroFactorTimingEngine = DynamicMacroFactorTimingEngine
MacroConditioningEngine = DynamicMacroFactorTimingEngine
DynamicMacroTimingEngine = DynamicMacroFactorTimingEngine
MacroFactorTimer = DynamicMacroFactorTimingEngine

__all__ = [
    "DynamicMacroFactorTimingEngine",
    "MacroFactorTimingEngine",
    "Phase106MacroFactorTimingEngine",
    "MacroConditioningEngine",
    "DynamicMacroTimingEngine",
    "MacroFactorTimer",
    "modulate_macro_factor_weights",
]

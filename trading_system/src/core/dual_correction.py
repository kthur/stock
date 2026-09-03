# -*- coding: utf-8 -*-
"""
trading_system/src/core/dual_correction.py
Dual Correction Strategy Engine (가격 조정 및 기간 조정 이원화 전략 엔진).
- Price Correction (가격 조정): Fibonacci Retracement (38.2%/50%/61.8%), Anchored VWAP, Selling Climax Reversal.
- Time Correction (기간 조정): Volume Dry-Up Index (VDI), Base Duration (15~45d), EMA Ribbon Squeeze.
- Correction Phase Classifier: TIME_CONSOLIDATION, PRICE_PULLBACK, ACTIVE_MARKUP, BREAKDOWN.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


def _extract_series(df: pd.DataFrame, col_name: str) -> Optional[pd.Series]:
    """Helper to extract clean float Series from DataFrame ignoring case."""
    if df is None or df.empty:
        return None
    matched = [c for c in df.columns if str(c).lower() == col_name.lower()]
    if not matched:
        return None
    s = df[matched[0]]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return pd.to_numeric(s, errors='coerce')


class PriceCorrectionScorer:
    """
    Evaluates Price Retracement / Correction (가격 조정 정밀 탐지기).
    - Fibonacci Retracement: 38.2%, 50.0%, 61.8% Golden Ratio levels.
    - Anchored VWAP (AVWAP) from swing low.
    - Panic Selling Climax Volume absorption.
    - RSI Oversold Turnaround.
    """

    @staticmethod
    def compute_score(df: pd.DataFrame) -> Tuple[float, Dict[str, float]]:
        if df is None or len(df) < 30:
            return 0.50, {'fib_score': 0.50, 'avwap_score': 0.50, 'climax_score': 0.50, 'rsi_score': 0.50}

        close = _extract_series(df, 'close')
        high = _extract_series(df, 'high')
        low = _extract_series(df, 'low')
        volume = _extract_series(df, 'volume')

        if close is None or high is None or low is None or len(close) < 30:
            return 0.50, {'fib_score': 0.50, 'avwap_score': 0.50, 'climax_score': 0.50, 'rsi_score': 0.50}

        curr_p = float(close.iloc[-1])
        if curr_p <= 0:
            return 0.50, {}

        # 1. Fibonacci Retracement Support Score (120-day swing)
        lookback = min(120, len(df))
        swing_high = float(high.tail(lookback).max())
        swing_low = float(low.tail(lookback).min())
        swing_range = max(1e-6, swing_high - swing_low)

        fib_levels = [
            swing_high - 0.382 * swing_range,
            swing_high - 0.500 * swing_range,
            swing_high - 0.618 * swing_range
        ]
        # Distance to closest Fibonacci support
        min_fib_dist = min([abs(curr_p - fl) / swing_range for fl in fib_levels])
        fib_score = float(np.exp(- (min_fib_dist ** 2) / (2 * (0.04 ** 2))))  # Gaussian proximity

        # 2. Anchored VWAP from 60-day swing low
        avwap_score = 0.50
        if volume is not None and len(volume) >= 30:
            low_window = min(60, len(df))
            low_tail = low.tail(low_window)
            low_pos = int(np.argmin(low_tail.values))
            start_pos = len(df) - low_window + low_pos
            subset_df = df.iloc[start_pos:]
            if len(subset_df) >= 3:
                s_c = _extract_series(subset_df, 'close')
                s_v = _extract_series(subset_df, 'volume')
                if s_c is not None and s_v is not None and s_v.sum() > 0:
                    avwap = float((s_c * s_v).sum() / max(s_v.sum(), 1.0))
                    avwap_ratio = curr_p / max(avwap, 1e-6)
                    # Support bounce when price is [0.98, 1.04] of AVWAP
                    if 0.98 <= avwap_ratio <= 1.04:
                        avwap_score = 0.90
                    elif 0.95 <= avwap_ratio < 0.98:
                        avwap_score = 0.70
                    elif avwap_ratio > 1.04:
                        avwap_score = float(np.clip(1.0 - (avwap_ratio - 1.04) * 3.0, 0.30, 0.80))
                    else:
                        avwap_score = 0.30

        # 3. Panic Selling Climax Absorption
        climax_score = 0.50
        if volume is not None and len(volume) >= 20:
            vol_ma20 = float(volume.tail(20).mean())
            recent_vol = float(volume.iloc[-1])
            is_hammer = (curr_p - float(low.iloc[-1])) > (float(high.iloc[-1]) - curr_p) * 1.5
            is_green = curr_p >= float(close.iloc[-2]) if len(close) >= 2 else True

            if recent_vol >= 2.0 * vol_ma20:
                climax_score = 0.90 if (is_hammer or is_green) else 0.15
            elif recent_vol >= 1.5 * vol_ma20:
                climax_score = 0.70 if (is_hammer or is_green) else 0.25

        # 4. RSI Oversold Turnaround
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.tail(14).mean()
        avg_loss = loss.tail(14).mean()
        rs = avg_gain / max(avg_loss, 1e-6)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        if 25.0 <= rsi <= 45.0:
            rsi_score = 0.85
        elif 45.0 < rsi <= 60.0:
            rsi_score = 0.65
        elif rsi < 25.0:
            rsi_score = 0.75  # Deep oversold
        else:
            rsi_score = 0.40  # Overbought

        composite_price_score = float(np.clip(
            0.35 * fib_score + 0.30 * avwap_score + 0.20 * climax_score + 0.15 * rsi_score,
            0.0, 1.0
        ))
        details = {
            'fib_score': round(fib_score, 4),
            'avwap_score': round(avwap_score, 4),
            'climax_score': round(climax_score, 4),
            'rsi_score': round(rsi_score, 4)
        }
        return composite_price_score, details


class TimeCorrectionScorer:
    """
    Evaluates Time/Period Consolidation (기간 조정 정밀 탐지기).
    - Volume Dry-Up Index (VDI): 5d volume / 50d volume <= 0.40.
    - Base Duration: 15 ~ 45 days in tight range [-6%, +6%].
    - Moving Average Ribbon Squeeze: EMA 10, 20, 50 tight convergence.
    - Bollinger Bandwidth Compression.
    """

    @staticmethod
    def compute_score(df: pd.DataFrame) -> Tuple[float, Dict[str, float]]:
        if df is None or len(df) < 50:
            return 0.50, {'vdi_score': 0.50, 'base_duration_score': 0.50, 'ribbon_score': 0.50, 'bandwidth_score': 0.50}

        close = _extract_series(df, 'close')
        volume = _extract_series(df, 'volume')

        if close is None or len(close) < 50:
            return 0.50, {}

        curr_p = float(close.iloc[-1])

        # 1. Volume Dry-Up Index (VDI)
        vdi_score = 0.50
        vdi_val = 1.0
        if volume is not None and len(volume) >= 50:
            v5 = float(volume.tail(5).mean())
            v50 = float(volume.tail(50).mean())
            vdi_val = v5 / max(v50, 1.0)
            if vdi_val <= 0.35:
                vdi_score = 0.95  # Extreme institutional dry-up
            elif vdi_val <= 0.50:
                vdi_score = 0.80
            elif vdi_val <= 0.70:
                vdi_score = 0.60
            else:
                vdi_score = 0.35

        # 2. Base Duration & Flatness (15~50 days in tight horizontal base)
        ma20 = close.rolling(20).mean()
        high_20 = float(close.tail(20).max())
        low_20 = float(close.tail(20).min())
        box_tightness = (high_20 - low_20) / max(curr_p, 1e-6)

        ma_slope = abs(float(ma20.iloc[-1]) - float(ma20.iloc[-15])) / max(float(ma20.iloc[-15]), 1e-6) if len(ma20) >= 15 else 0.05

        if box_tightness <= 0.05 and ma_slope <= 0.03:
            base_duration_score = 0.95
        elif box_tightness <= 0.08 and ma_slope <= 0.05:
            base_duration_score = 0.85
        elif box_tightness <= 0.12:
            base_duration_score = 0.65
        else:
            base_duration_score = 0.35

        # 3. EMA Ribbon Squeeze (EMA 10, EMA 20, EMA 50 convergence)
        ema10 = float(close.ewm(span=10, adjust=False).mean().iloc[-1])
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])

        ribbon_spread = (max(ema10, ema20, ema50) - min(ema10, ema20, ema50)) / max(ema20, 1e-6)
        if ribbon_spread <= 0.020:
            ribbon_score = 0.95  # Tight knot ribbon
        elif ribbon_spread <= 0.035:
            ribbon_score = 0.80
        elif ribbon_spread <= 0.060:
            ribbon_score = 0.60
        else:
            ribbon_score = 0.35

        # 4. Bollinger Bandwidth Compression
        std20 = float(close.tail(20).std())
        bandwidth = (4.0 * std20) / max(curr_p, 1e-6)
        if bandwidth <= 0.06:
            bandwidth_score = 0.90
        elif bandwidth <= 0.10:
            bandwidth_score = 0.75
        elif bandwidth <= 0.15:
            bandwidth_score = 0.55
        else:
            bandwidth_score = 0.30

        composite_time_score = float(np.clip(
            0.35 * vdi_score + 0.25 * base_duration_score + 0.25 * ribbon_score + 0.15 * bandwidth_score,
            0.0, 1.0
        ))
        details = {
            'vdi_val': round(vdi_val, 4),
            'vdi_score': round(vdi_score, 4),
            'base_duration_score': round(base_duration_score, 4),
            'ribbon_score': round(ribbon_score, 4),
            'bandwidth_score': round(bandwidth_score, 4)
        }
        return composite_time_score, details


@register_strategy(
    StrategyMeta(
        strategy_id="dual_correction",
        display_name="Dual Correction Strategy",
        score_column="dual_correction_score",
        category="factor",
        output_file="dual_correction_predictions.txt",
        default_regime_weights={
            "BULL_LOW_VOL": 0.03,
            "BULL_HIGH_VOL": 0.04,
            "SIDEWAYS_LOW_VOL": 0.03,
            "SIDEWAYS_HIGH_VOL": 0.03,
            "BEAR_LOW_VOL": 0.03,
            "BEAR_HIGH_VOL": 0.04,
            "CRISIS": 0.02,
        },
    )
)
class DualCorrectionEngine(BaseStrategyEngine):
    """
    Dual Correction Strategy Engine:
    Integrates Price Correction (Fibonacci/AVWAP/Climax) and Time Correction (VDI/Base/Ribbon).
    Classifies stocks into TIME_CONSOLIDATION, PRICE_PULLBACK, ACTIVE_MARKUP, or BREAKDOWN.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with all test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(prices_dict=prices_dict or {}, **kwargs)

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        if not prices_dict:
            return pd.DataFrame(columns=[
                'symbol', 'dual_correction_score', 'price_correction_score',
                'time_correction_score', 'correction_phase'
            ])

        regime = str(kwargs.get('regime', 'SIDEWAYS_LOW_VOL')).upper()
        results: List[Dict[str, Any]] = []

        for sym, df in prices_dict.items():
            if df is None or len(df) < 30:
                continue

            try:
                price_score, p_details = PriceCorrectionScorer.compute_score(df)
                time_score, t_details = TimeCorrectionScorer.compute_score(df)

                # Regime-Adaptive Weighting
                if 'BULL' in regime:
                    # In bull markets, prioritize Time Correction (Flat Bases of leading stocks)
                    dual_score = 0.65 * time_score + 0.35 * price_score
                elif 'BEAR' in regime or 'CRISIS' in regime:
                    # In bear markets, prioritize Price Correction (Deep oversold Fibonacci bounces)
                    dual_score = 0.35 * time_score + 0.65 * price_score
                else:
                    # Sideways regime: balanced blend
                    dual_score = 0.50 * time_score + 0.50 * price_score

                # Phase Classification
                close = _extract_series(df, 'close')
                high = _extract_series(df, 'high')
                curr_p = float(close.iloc[-1]) if close is not None else 0.0
                high_52w = float(high.tail(min(252, len(df))).max()) if high is not None else curr_p
                dist_from_high = (high_52w - curr_p) / max(high_52w, 1e-6)

                if dist_from_high <= 0.10 and time_score >= 0.65:
                    phase = 'TIME_CONSOLIDATION'
                elif dist_from_high <= 0.04 and dual_score >= 0.70:
                    phase = 'ACTIVE_MARKUP'
                elif dist_from_high > 0.08 and price_score >= 0.65:
                    phase = 'PRICE_PULLBACK'
                elif dist_from_high > 0.20 and dual_score < 0.45:
                    phase = 'BREAKDOWN'
                else:
                    phase = 'NEUTRAL'

                results.append({
                    'symbol': sym,
                    'dual_correction_score': round(float(np.clip(dual_score, 0.0, 1.0)), 4),
                    'price_correction_score': round(float(price_score), 4),
                    'time_correction_score': round(float(time_score), 4),
                    'correction_phase': phase
                })
            except Exception as e:
                logger.debug(f"[DualCorrectionEngine] Error scoring {sym}: {e}")
                continue

        if not results:
            return pd.DataFrame(columns=[
                'symbol', 'dual_correction_score', 'price_correction_score',
                'time_correction_score', 'correction_phase'
            ])

        df_out = pd.DataFrame(results)
        return df_out.sort_values(by='dual_correction_score', ascending=False).reset_index(drop=True)

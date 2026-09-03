"""
range_expansion_breakout.py — Intraday Volatility & Range Expansion Breakout Strategy Engine.

Detects volatility compression precursors (NR7, Bollinger Bandwidth squeeze, inside days) followed by
explosive range expansion (REF >= 1.5), relative volume surge (RVOL >= 1.8), and top-tier close location values.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="range_expansion_breakout",
        display_name="Intraday Volatility & Range Expansion Breakout",
        score_column="range_expansion_score",
        category="breakout",
        output_file="range_expansion_predictions.txt",
        default_regime_weights={
            "BEAR_LOW_VOL": 0.02,
            "BEAR_HIGH_VOL": 0.01,
            "SIDEWAYS_LOW_VOL": 0.03,
            "SIDEWAYS_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.04,
            "BULL_HIGH_VOL": 0.05,
            "BEAR": 0.02,
            "SIDEWAYS": 0.03,
            "BULL": 0.04,
        },
    )
)
class RangeExpansionBreakoutEngine(BaseStrategyEngine):
    """
    Intraday Volatility & Range Expansion Breakout Engine.

    Calculates:
    1. Compression Precursor C_i (NR7, Bollinger Bandwidth Squeeze, Inside Day)
    2. Range Expansion Factor E_i (REF_t = Bar_Range / ATR_14 >= 1.5x)
    3. Relative Volume Surge V_i (RVOL_t = Volume / SMA_20(Volume) >= 1.8x)
    4. Close Quality / Location Value Q_i (CLV_t = (Close - Low) / (High - Low) >= 0.65)
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="RangeExpansionBreakoutEngine", config=config)

    def _compute_symbol_breakout(self, df_ohlcv: pd.DataFrame) -> float:
        """
        Computes range expansion breakout score [0.05, 0.95] for a single OHLCV DataFrame
        using optimized NumPy array vector operations for sub-millisecond per-symbol latency.
        """
        if df_ohlcv is None or df_ohlcv.empty:
            return 0.50

        try:
            cols = df_ohlcv.columns
            if "Close" not in cols or "High" not in cols or "Low" not in cols:
                return 0.50

            # Direct extraction to numpy float arrays with minimal overhead
            try:
                c_raw = np.asarray(df_ohlcv["Close"], dtype=float)
                h_raw = np.asarray(df_ohlcv["High"], dtype=float)
                l_raw = np.asarray(df_ohlcv["Low"], dtype=float)
                o_raw = np.asarray(df_ohlcv["Open"], dtype=float) if "Open" in cols else c_raw
                v_raw = np.asarray(df_ohlcv["Volume"], dtype=float) if "Volume" in cols else np.ones_like(c_raw)
            except Exception:
                c_raw = pd.to_numeric(df_ohlcv["Close"], errors="coerce").to_numpy(dtype=float)
                h_raw = pd.to_numeric(df_ohlcv["High"], errors="coerce").to_numpy(dtype=float)
                l_raw = pd.to_numeric(df_ohlcv["Low"], errors="coerce").to_numpy(dtype=float)
                o_raw = pd.to_numeric(df_ohlcv["Open"], errors="coerce").to_numpy(dtype=float) if "Open" in cols else c_raw
                v_raw = pd.to_numeric(df_ohlcv["Volume"], errors="coerce").to_numpy(dtype=float) if "Volume" in cols else np.ones_like(c_raw)

            # Filter valid (finite) rows
            valid = np.isfinite(c_raw) & np.isfinite(h_raw) & np.isfinite(l_raw)
            if not np.all(valid):
                c_raw = c_raw[valid]
                h_raw = h_raw[valid]
                l_raw = l_raw[valid]
                o_raw = o_raw[valid]
                v_raw = v_raw[valid]

            n = len(c_raw)
            if n < 15:
                return 0.50

            # Window length for calculation: at most trailing 35 bars
            w = min(n, 35)
            c = c_raw[-w:]
            h = h_raw[-w:]
            lows = l_raw[-w:]
            o = o_raw[-w:]
            v = np.nan_to_num(v_raw[-w:], nan=0.0, posinf=0.0, neginf=0.0)
            w_len = len(c)

            # 1. Bar Range and True Range calculation
            bar_range = np.maximum(h - lows, 1e-8)
            prev_c = np.empty_like(c)
            prev_c[0] = c[0]
            prev_c[1:] = c[:-1]

            tr1 = bar_range
            tr2 = np.abs(h - prev_c)
            tr3 = np.abs(lows - prev_c)
            tr = np.maximum(np.maximum(tr1, tr2), tr3)

            # ATR 14
            atr_w = min(14, w_len)
            curr_atr = float(np.mean(tr[-atr_w:]))
            if not np.isfinite(curr_atr) or curr_atr <= 1e-8:
                curr_atr = float(tr[-1]) if np.isfinite(tr[-1]) and tr[-1] > 1e-8 else 1e-8

            # 2. Compression Precursor Score C_i (evaluated on recent 1~3 bars prior to current bar)
            # NR7 flag: Was bar t-1 or t-2 the narrowest range of its trailing 7 bars?
            is_nr7 = 0.0
            if w_len >= 8:
                trailing_7 = bar_range[-8:-1]
                if len(trailing_7) >= 7 and bar_range[-2] <= np.min(trailing_7):
                    is_nr7 = 1.0
                elif len(trailing_7) >= 7 and bar_range[-3] <= np.min(trailing_7):
                    is_nr7 = 0.70

            # Bollinger Bandwidth Squeeze on recent window
            is_squeeze = 0.0
            if w_len >= 20:
                sub_c = np.lib.stride_tricks.sliding_window_view(c, 20)
                means = np.mean(sub_c, axis=1)
                stds = np.std(sub_c, axis=1, ddof=1) if sub_c.shape[1] > 1 else np.zeros_like(means)
                bw_arr = (4.0 * stds) / np.maximum(means, 1e-8)
                if len(bw_arr) >= 1:
                    curr_bw = bw_arr[-2] if len(bw_arr) >= 2 else bw_arr[-1]
                    pct_rank = float(np.mean(bw_arr < curr_bw))
                    if pct_rank <= 0.20:
                        is_squeeze = 1.0
                    elif pct_rank <= 0.35:
                        is_squeeze = 0.60

            # Inside Day precursor
            is_inside_day = 0.0
            if w_len >= 3:
                if (h[-2] < h[-3]) and (lows[-2] > lows[-3]):
                    is_inside_day = 1.0

            compression_score = 0.40 * is_nr7 + 0.40 * is_squeeze + 0.20 * is_inside_day

            # 3. Range Expansion Trigger E_i
            # Range Expansion Factor: REF = Current Bar Range / ATR_14
            curr_range = float(bar_range[-1])
            ref = curr_range / max(curr_atr, 1e-8)

            # S-curve scaling for REF: 1.0x -> 0.0, 1.5x -> 0.50, 2.5x+ -> 1.0
            if ref >= 1.5:
                expansion_score = float(np.clip((ref - 1.2) / 1.5, 0.0, 1.0))
            elif ref >= 1.2:
                expansion_score = float(np.clip((ref - 1.0) / 1.0 * 0.4, 0.0, 0.4))
            else:
                expansion_score = 0.0

            # 4. Volume Verification V_i
            # RVOL = Current Volume / SMA_20(Volume)
            if w_len >= 20 and np.sum(v[-20:]) > 0:
                vol_sma20 = float(np.mean(v[-21:-1])) if w_len >= 21 else float(np.mean(v[-20:]))
                curr_vol = float(v[-1])
                rvol = (curr_vol / max(vol_sma20, 1.0)) if vol_sma20 > 0 else 1.0
            else:
                rvol = 1.0

            if rvol >= 1.8:
                volume_score = float(np.clip((rvol - 1.2) / 1.8, 0.0, 1.0))
            elif rvol >= 1.3:
                volume_score = float(np.clip((rvol - 1.0) / 1.0 * 0.4, 0.0, 0.4))
            else:
                volume_score = 0.10

            # 5. Close Location Value & Breakout Direction Q_i
            curr_close = float(c[-1])
            curr_low = float(lows[-1])
            curr_high = float(h[-1])
            curr_open = float(o[-1])

            clv = (curr_close - curr_low) / max(curr_high - curr_low, 1e-8)
            clv = float(np.clip(clv, 0.0, 1.0))

            # 20-day high breakout confirmation
            is_new_high = 0.0
            if w_len >= 21:
                high_20 = float(np.max(h[-21:-1]))
                if curr_close > high_20:
                    is_new_high = 1.0
                elif curr_high > high_20:
                    is_new_high = 0.50

            # Gap catalyst bonus: Gap & Go breakout
            gap_atr = float(curr_open - prev_c[-1]) / max(curr_atr, 1e-8)
            gap_bonus = float(np.clip(gap_atr * 0.20, 0.0, 0.20)) if gap_atr > 0 else 0.0

            # Quality score
            if clv >= 0.65:
                quality_score = float(np.clip((clv - 0.50) / 0.50, 0.0, 1.0)) * 0.60 + 0.25 * is_new_high + 0.15 * (gap_bonus / 0.20 if gap_bonus > 0 else 0.0)
            else:
                quality_score = float(np.clip(clv * 0.5, 0.0, 0.5))

            # Composite Breakout Intensity
            raw_breakout_signal = (
                0.25 * compression_score +
                0.35 * expansion_score +
                0.25 * volume_score +
                0.15 * quality_score
            )

            # Directional alignment: Bullish vs Bearish expansion
            is_bullish_bar = (curr_close >= curr_open) and (clv >= 0.50)
            is_bearish_bar = (curr_close < curr_open) and (clv < 0.40)

            if is_bullish_bar:
                # Bullish range expansion score [0.50, 0.98]
                score = 0.50 + 0.45 * raw_breakout_signal
                # Super Breakout Ignition: Compression precursor (NR7/Squeeze) + Violent REF (>=2.0) + Massive RVOL (>=2.5) + High CLV (>=0.80)
                if compression_score >= 0.50 and ref >= 1.8 and rvol >= 2.0 and clv >= 0.75:
                    score += 0.08
            elif is_bearish_bar:
                # Bearish breakdown [0.05, 0.50]
                score = 0.50 - 0.45 * raw_breakout_signal
            else:
                # Neutral / Doji inside range
                score = 0.50 + 0.10 * (clv - 0.50)

            if not np.isfinite(score):
                return 0.50

            return float(np.clip(score, 0.05, 0.95))

        except Exception as e:
            logger.debug(f"[RangeExpansion] Calculation error: {e}")
            return 0.50

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
        return self.compute_scores(prices_dict=prices_dict, **kwargs)

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Range Expansion Breakout scores for all symbols.

        Returns:
            pd.DataFrame / ScoreDataFrame with ['symbol', 'range_expansion_score']
        """
        prices_source = kwargs.get("df_prices", prices_dict)

        if not prices_source:
            return make_score_dataframe({}, score_column="range_expansion_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="range_expansion_score")

        scores: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            df_ohlcv = self.extract_ohlcv(sym, p_dict, min_bars=5)
            score = self._compute_symbol_breakout(df_ohlcv)
            scores[sym_str] = round(score, 4)

        res_df = make_score_dataframe(scores, score_column="range_expansion_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df['range_expansion_score'], errors='coerce').fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                # Multi-Tier Range Expansion Super Breakout Booster
                enhanced = np.where(ranks >= 0.95, (s_series * 1.15).clip(0.05, 0.95),
                           np.where(ranks >= 0.85, (s_series * 1.10).clip(0.05, 0.95), s_series))
                res_df['range_expansion_score'] = pd.to_numeric(pd.Series(enhanced, index=res_df.index), errors='coerce').fillna(0.50).clip(0.05, 0.95)
            else:
                res_df['range_expansion_score'] = s_series
        return res_df


def range_expansion_score(
    prices_dict: Any,
    **kwargs: Any
) -> pd.DataFrame:
    """
    Convenience function to compute Range Expansion Breakout scores.
    """
    engine = RangeExpansionBreakoutEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)

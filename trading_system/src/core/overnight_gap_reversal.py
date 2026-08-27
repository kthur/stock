"""
trading_system/src/core/overnight_gap_reversal.py
Strategy #32: Overnight Gap Reversal & Gap Fade Engine.
Evaluates opening price dislocation vs previous day's close normalized by ATR and historical gap distribution.
High Score = High probability mean-reversion bounce after an over-extended downward opening gap.
Low Score = Over-extended upward gap prone to intraday exhaustion fade.
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="overnight_gap_reversal",
        display_name="Overnight Gap Reversal",
        score_column="overnight_gap_score",
        category="factor",
        output_file="overnight_gap_predictions.txt",
        default_regime_weights={
            "BEAR": 0.04,
            "BEAR_HIGH_VOL": 0.06,
            "SIDEWAYS_LOW_VOL": 0.05,
            "BULL_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.03,
        },
    )
)
class OvernightGapReversalEngine(BaseStrategyEngine):
    """
    Overnight Gap Mean Reversion Engine.
    Quantifies opening gap size relative to rolling ATR, detecting statistical gap fill opportunities.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.calculate_scores(symbols, prices_dict=prices_dict)

    def calculate_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[Any] = None
    ) -> pd.DataFrame:
        """
        Computes Overnight Gap Reversal score [0.0, 1.0] per symbol.
        Returns DataFrame with ['symbol', 'overnight_gap_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'overnight_gap_score'])

        if not prices_dict:
            return pd.DataFrame({
                'symbol': symbols,
                'overnight_gap_score': [0.50] * len(symbols)
            })

        results = []

        for sym in symbols:
            df = prices_dict.get(sym, prices_dict.get(str(sym)))
            if df is None or len(df) < 15:
                results.append({'symbol': sym, 'overnight_gap_score': 0.50})
                continue

            try:
                c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                o_col = 'Open' if 'Open' in df.columns else ('open' if 'open' in df.columns else None)
                h_col = 'High' if 'High' in df.columns else ('high' if 'high' in df.columns else None)
                l_col = 'Low' if 'Low' in df.columns else ('low' if 'low' in df.columns else None)

                if not c_col or not o_col:
                    results.append({'symbol': sym, 'overnight_gap_score': 0.50})
                    continue

                close = df[c_col].dropna()
                open_p = df[o_col].dropna()
                high = df[h_col].dropna() if h_col else close
                low = df[l_col].dropna() if l_col else close

                if len(close) < 15 or len(open_p) < 15:
                    results.append({'symbol': sym, 'overnight_gap_score': 0.50})
                    continue

                # 1. Calculate Overnight Gap % = (Open_t - Close_t-1) / Close_t-1
                prev_close = close.iloc[-2]
                curr_open = open_p.iloc[-1]
                curr_close = close.iloc[-1]

                if prev_close <= 0 or curr_open <= 0:
                    results.append({'symbol': sym, 'overnight_gap_score': 0.50})
                    continue

                gap_pct = float((curr_open - prev_close) / prev_close)

                # 2. 14-day True Range & ATR normalization
                prev_closes = close.shift(1).iloc[-15:]
                tr1 = (high.iloc[-15:] - low.iloc[-15:]).abs()
                tr2 = (high.iloc[-15:] - prev_closes).abs()
                tr3 = (low.iloc[-15:] - prev_closes).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr_val = tr.rolling(14, min_periods=5).mean().iloc[-1]
                atr_14 = float(atr_val) if (pd.notna(atr_val) and np.isfinite(float(atr_val))) else float(prev_close * 0.02)
                atr_pct = float(atr_14 / prev_close) if prev_close > 0 else 0.02
                atr_pct = max(0.005, atr_pct) if np.isfinite(atr_pct) else 0.02

                # Standardized Gap Z-Score
                gap_z = (gap_pct / atr_pct) if atr_pct > 0 else 0.0
                gap_z = gap_z if np.isfinite(gap_z) else 0.0

                # 3. Gap Fill Directionality & Mean Reversion Sizing
                # If gap is downward (gap_z < -1.0), strong bounce mean-reversion signal
                # If gap is upward (gap_z > +1.0), fade probability
                # Baseline neutral is 0.50
                # Formula: score = 0.50 - 0.35 * tanh(gap_z / 1.5)
                reversion_score = 0.50 - 0.35 * np.tanh(gap_z / 1.5)

                score = float(np.clip(reversion_score, 0.05, 0.95)) if np.isfinite(reversion_score) else 0.50
                results.append({'symbol': str(sym), 'overnight_gap_score': round(score, 4)})

            except Exception as ex:
                logger.debug(f"Error computing gap score for {sym}: {ex}")
                results.append({'symbol': sym, 'overnight_gap_score': 0.50})

        return pd.DataFrame(results)

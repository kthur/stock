"""
src/core/earnings_tone_drift.py
LLM-based Earnings Call & Disclosure Tone Drift Engine.

Analyzes text sentiment drift from OpenDART / SEC filings and conference call transcripts:
  - Tone Acceleration: Delta in sentiment polarity (Pessimistic -> Optimistic)
  - Management Guidance Confidence Score
  - Tone Drift Score [0.0, 1.0]
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="earnings_tone_drift",
        display_name="Earnings Tone Drift",
        score_column="earnings_tone_drift_score",
        category="sentiment",
        output_file="earnings_tone_drift_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class EarningsToneDriftEngine(BaseStrategyEngine):
    """
    LLM-based Earnings Call & Disclosure Tone Drift Engine.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        transcript_map = kwargs.get("transcript_map", None)
        return self.compute_tone_drift_scores(symbols=symbols, transcript_map=transcript_map, prices_dict=prices_dict, **kwargs)

    def calculate_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compatibility alias called by run_pipeline.py.

        Merges symbol list from both explicit `symbols` arg and `prices_dict` keys,
        then delegates to compute_tone_drift_scores().
        """
        merged_symbols: List[str] = list(symbols) if symbols else []
        if prices_dict:
            for sym in prices_dict.keys():
                if sym not in merged_symbols:
                    merged_symbols.append(sym)
        tm = transcript_map or kwargs.get("transcript_map", None)
        return self.compute_tone_drift_scores(symbols=merged_symbols, transcript_map=tm, prices_dict=prices_dict, **kwargs)

    def compute_tone_drift_scores(
        self,
        symbols: List[str],
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Tone Drift Acceleration score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'earnings_tone_drift_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'earnings_tone_drift_score'])

        results = []

        def _safe_float(val: Any, default: float) -> float:
            if val is None or pd.isna(val):
                return default
            try:
                res = float(val)
                return default if not np.isfinite(res) else res
            except (ValueError, TypeError):
                return default

        # Price momentum drift fallback
        prices_map = prices_dict if isinstance(prices_dict, dict) else kwargs.get('prices_dict')

        for sym in symbols:
            score = np.nan

            if transcript_map:
                sym_raw = str(sym).split('.')[0]
                sym_clean = sym_raw.zfill(6) if sym_raw.isdigit() else sym_raw
                t_data = transcript_map.get(sym, transcript_map.get(str(sym), transcript_map.get(sym_clean, transcript_map.get(sym_raw))))

                if t_data and isinstance(t_data, dict):
                    raw_prev = _safe_float(t_data.get('previous_quarter_tone'), 0.50)
                    raw_cur = _safe_float(t_data.get('current_quarter_tone'), 0.50)
                    # Consistent linear mapping from [-1, 1] polarity or [0, 1] unit scale
                    is_polarity = (raw_prev < 0.0 or raw_cur < 0.0)
                    def _normalize_tone(val: float) -> float:
                        if not np.isfinite(val):
                            return 0.50
                        if is_polarity:
                            return float(np.clip((val + 1.0) / 2.0, 0.0, 1.0))
                        return float(np.clip(val, 0.0, 1.0))

                    prev_tone = _normalize_tone(raw_prev)
                    cur_tone = _normalize_tone(raw_cur)
                    confidence = float(np.clip(_safe_float(t_data.get('confidence'), 1.0), 0.1, 1.0))

                    # Tone Drift Delta (Positive = Upgrade, Negative = Downgrade with symmetric acceleration)
                    tone_delta = (cur_tone - prev_tone) * confidence
                    accel_mult = 1.25 if abs(tone_delta) > 0.10 else 1.0
                    abs_tone_boost = (cur_tone - 0.50) * 0.40 * confidence
                    drift_boost = 1.0 * tone_delta * accel_mult
                    score = float(np.clip(0.50 + abs_tone_boost + drift_boost, 0.0, 1.0))
                    score = score if np.isfinite(score) else 0.50

            if pd.isna(score):
                if prices_map and (sym in prices_map or str(sym).zfill(6) in prices_map):
                    p_df = prices_map.get(sym, prices_map.get(str(sym).zfill(6)))
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 20:
                        c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
                        if c_col and c_col in p_df.columns:
                            c_vals = p_df[c_col].dropna().values
                            if len(c_vals) >= 20:
                                # Post-earnings price momentum drift proxy: 5d return vs 20d baseline
                                ret_5d = (c_vals[-1] / max(c_vals[-5], 1e-5)) - 1.0
                                ret_20d = (c_vals[-1] / max(c_vals[-20], 1e-5)) - 1.0
                                drift_proxy = 0.50 + (ret_5d * 2.0) + (ret_20d * 0.5)
                                score = float(np.clip(drift_proxy, 0.10, 0.90))
                            else:
                                score = 0.50
                        else:
                            score = 0.50
                    else:
                        score = 0.50
                else:
                    score = 0.50

            results.append({
                'symbol': sym,
                'raw_score': float(score) if pd.notna(score) else 0.50
            })

        res_df = pd.DataFrame(results)
        if len(res_df) > 1:
            ranks = res_df['raw_score'].rank(pct=True, ascending=True).clip(0.05, 0.95)
            res_df['earnings_tone_drift_score'] = (0.05 + 0.90 * ranks).clip(0.05, 0.98)
        else:
            res_df['earnings_tone_drift_score'] = 0.50

        res_df['tone_drift_score'] = res_df['earnings_tone_drift_score']
        res_df['earnings_tone_drift_score'] = pd.to_numeric(res_df['earnings_tone_drift_score'], errors='coerce').fillna(0.50)
        return res_df[['symbol', 'earnings_tone_drift_score', 'tone_drift_score']]

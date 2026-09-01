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
        features_df = kwargs.get("features_df", fundamentals_dict)
        return self.compute_tone_drift_scores(symbols=symbols, transcript_map=transcript_map, features_df=features_df, prices_dict=prices_dict)

    def calculate_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        features_df: Optional[Any] = None,
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
        feat = features_df if features_df is not None else kwargs.get("features_df", None)
        return self.compute_tone_drift_scores(symbols=merged_symbols, transcript_map=tm, features_df=feat, prices_dict=prices_dict)

    def compute_tone_drift_scores(
        self,
        symbols: List[str],
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        features_df: Optional[Any] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> pd.DataFrame:
        """
        Computes Tone Drift Acceleration score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'earnings_tone_drift_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'earnings_tone_drift_score'])

        # Prepare lookup from features_df if available
        feat_map = {}
        if features_df is not None:
            if isinstance(features_df, pd.DataFrame) and not features_df.empty:
                if 'symbol' in features_df.columns:
                    feat_map = features_df.drop_duplicates('symbol', keep='last').set_index('symbol').to_dict('index')
            elif isinstance(features_df, dict):
                feat_map = features_df

        results = []

        def _safe_float(val: Any, default: float) -> float:
            if val is None or pd.isna(val):
                return default
            try:
                res = float(val)
                return default if not np.isfinite(res) else res
            except (ValueError, TypeError):
                return default

        for sym in symbols:
            score = np.nan
            sym_raw = str(sym).split('.')[0]
            sym_clean = sym_raw.zfill(6) if sym_raw.isdigit() else sym_raw

            if transcript_map:
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

                    # Tone Drift Delta (Positive = Upgrade, Negative = Downgrade with asymmetric upgrade acceleration)
                    tone_delta = (cur_tone - prev_tone) * confidence
                    # Guidance upgrade acceleration: strong positive drift with high conviction receives 1.40x boost
                    if tone_delta > 0.10 and cur_tone >= 0.65:
                        accel_mult = 1.40
                    elif abs(tone_delta) > 0.10:
                        accel_mult = 1.25
                    else:
                        accel_mult = 1.0

                    abs_tone_boost = (cur_tone - 0.50) * 0.40 * confidence
                    drift_boost = 1.0 * tone_delta * accel_mult
                    score = float(np.clip(0.50 + abs_tone_boost + drift_boost, 0.0, 1.0))
                    score = score if np.isfinite(score) else 0.50

            # Quantitative earnings drift fallback from fundamental growth & momentum
            if pd.isna(score) and feat_map:
                f_row = feat_map.get(sym, feat_map.get(sym_raw, feat_map.get(sym_clean, {})))
                if f_row and isinstance(f_row, dict):
                    eps_g = _safe_float(f_row.get('eps_growth_1y', f_row.get('eps_growth')), 0.0)
                    rev_g = _safe_float(f_row.get('revenue_growth_1y', f_row.get('revenue_growth')), 0.0)
                    op_inc = _safe_float(f_row.get('operating_income', f_row.get('operating_income_y')), np.nan)
                    net_inc = _safe_float(f_row.get('net_income', f_row.get('net_income_y')), np.nan)
                    drift = eps_g - rev_g
                    is_profitable = (pd.notna(op_inc) and op_inc > 0) or (pd.notna(net_inc) and net_inc > 0)
                    if is_profitable or eps_g != 0.0 or rev_g != 0.0:
                        quant_tone = 0.50 + float(np.clip(drift * 0.40 + eps_g * 0.20, -0.40, 0.40))
                        score = float(np.clip(quant_tone, 0.05, 0.95))

            # Post-Earnings Announcement Drift (PEAD) price momentum fallback when prices_dict is provided
            if pd.isna(score) and prices_dict and isinstance(prices_dict, dict) and bool(prices_dict):
                p_df = prices_dict.get(sym)
                if p_df is None:
                    p_df = prices_dict.get(sym_raw)
                if p_df is None:
                    p_df = prices_dict.get(sym_clean)
                if isinstance(p_df, pd.DataFrame) and len(p_df) >= 5:
                    c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
                    if c_col:
                        c_s = p_df[c_col].dropna().astype(float)
                        if len(c_s) >= 5:
                            last_c = float(c_s.iloc[-1])
                            c_20 = float(c_s.iloc[-min(len(c_s), 21)])
                            r_20d = (last_c / max(c_20, 1e-5)) - 1.0

                            c_60 = float(c_s.iloc[-min(len(c_s), 61)])
                            r_60d = (last_c / max(c_60, 1e-5)) - 1.0

                            delta_mom = r_20d - (1.0 / 3.0) * r_60d

                            c_5 = float(c_s.iloc[-min(len(c_s), 6)])
                            r_5d = (last_c / max(c_5, 1e-5)) - 1.0
                            acc_5d = r_5d - 0.25 * r_20d

                            sma20 = float(c_s.tail(20).mean())
                            vr_rel = (last_c - sma20) / max(sma20, 1e-5)

                            # Institutional Volume Expansion confirmation on PEAD breakout
                            vol_boost = 0.0
                            v_col = 'Volume' if 'Volume' in p_df.columns else ('volume' if 'volume' in p_df.columns else None)
                            if v_col:
                                v_s = pd.to_numeric(p_df[v_col], errors='coerce').dropna()
                                if len(v_s) >= 20:
                                    v_now = float(v_s.iloc[-1])
                                    v_sma = float(v_s.tail(20).mean())
                                    if v_sma > 0:
                                        vr = v_now / v_sma
                                        if vr >= 1.5 and r_5d > 0:
                                            vol_boost = 0.10 * min(1.0, (vr - 1.0) / 2.0)

                            pead_tone = 0.50 + 0.35 * delta_mom + 0.25 * acc_5d + 0.20 * vr_rel + vol_boost
                            score = float(np.clip(pead_tone, 0.05, 0.95))

            results.append({
                'symbol': sym,
                'earnings_tone_drift_score': score,
                'tone_drift_score': score
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df['earnings_tone_drift_score'] = pd.to_numeric(res_df['earnings_tone_drift_score'], errors='coerce')
            res_df['tone_drift_score'] = res_df['earnings_tone_drift_score']
        return res_df

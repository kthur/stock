"""
src/core/insider_buying.py
Corporate Insider Net Buying Anomaly Strategy Engine (Strategy #29).

Parses OpenDART (Korea) and SEC Form 4 (US) insider disclosure filings:
  - Executive / Board Member open market share purchases
  - Controlling Shareholder equity accumulation
  - Net Insider Purchasing Score [0.0, 1.0]
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
        strategy_id="insider_buying",
        display_name="Insider Buying Catalyst",
        score_column="insider_buying_score",
        category="catalyst",
        output_file="insider_buying_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class InsiderBuyingEngine(BaseStrategyEngine):
    """
    Strategy #29: Corporate Insider Net Buying Anomaly Engine.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = kwargs.pop("symbols", None)
        if not symbols and isinstance(prices_dict, dict):
            symbols = list(prices_dict.keys())
        elif not symbols and isinstance(prices_dict, (list, tuple, set)):
            symbols = list(prices_dict)
        symbols = symbols or []
        filings = kwargs.pop("insider_filings", None) or kwargs.pop("dart_disclosures", None) or kwargs.pop("disclosures", None) or kwargs.pop("filings", None)
        return self.compute_insider_buying_scores(symbols=symbols, insider_filings=filings, prices_dict=prices_dict, **kwargs)

    def calculate_scores(self, symbols: List[str], prices_dict: Optional[Dict[str, pd.DataFrame]] = None, **kwargs: Any) -> pd.DataFrame:
        filings = kwargs.pop("insider_filings", None) or kwargs.pop("dart_disclosures", None) or kwargs.pop("disclosures", None) or kwargs.pop("filings", None)
        return self.compute_insider_buying_scores(symbols=symbols, insider_filings=filings, prices_dict=prices_dict, **kwargs)

    def compute_insider_buying_scores(
        self,
        symbols: List[str],
        insider_filings: Optional[List[Dict[str, Any]]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        if insider_filings is None:
            insider_filings = kwargs.pop("dart_disclosures", None) or kwargs.pop("disclosures", None) or kwargs.pop("filings", None)
        """
        Computes Insider Net Buying score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'insider_buying_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'insider_buying_score'])

        # Default to NaN for symbols without insider filings
        scores_map = {sym: np.nan for sym in symbols}

        if insider_filings:
            # Pre-index filings by stock code/symbol for O(M) processing
            filings_by_code: Dict[str, List[Dict[str, Any]]] = {}
            for item in insider_filings:
                code_raw = str(item.get('stock_code', '')).strip()
                if code_raw:
                    code_clean = code_raw.zfill(6) if code_raw.isdigit() else code_raw
                    filings_by_code.setdefault(code_clean, []).append(item)
                    if code_clean != code_raw:
                        filings_by_code.setdefault(code_raw, []).append(item)

            buy_keywords = {'BUY', 'PURCHASE', '취득', '매입', '장내매수', '장외매수', '신규취득', '주식매수'}
            sell_keywords = {'SELL', 'DISPOSAL', '처분', '매각', '장내매도', '장외매도', '주식매도'}
            high_level_roles = {'CEO', 'CHAIRMAN', '대표이사', '최대주주', '부회장'}

            for sym in symbols:
                sym_raw = sym.split('.')[0]
                sym_clean = sym_raw.zfill(6) if sym_raw.isdigit() else sym_raw

                matching_items = filings_by_code.get(sym_clean)
                if matching_items is None and sym_raw != sym_clean:
                    matching_items = filings_by_code.get(sym_raw)
                if not matching_items:
                    continue

                cur_score = 0.50
                for item in matching_items:
                    report_nm = str(item.get('report_nm', '') or '')
                    insider_role = str(item.get('insider_role', 'EXECUTIVE') or 'EXECUTIVE').upper()
                    raw_type = str(item.get('trans_type', '') or '').upper().strip()
                    combined_role_text = f"{insider_role} {report_nm}"

                    # Explicit transaction classification: do not default generic informational filings to BUY
                    if raw_type in buy_keywords or any(k in report_nm for k in ['장내매수', '장내취득', '신규매수', '주식매입', '자사주매입', '지분매수', '지분취득']):
                        boost = 0.40 if any(role in combined_role_text for role in high_level_roles) else 0.25
                        # Accumulate multiple insider buys up to 0.98 cap
                        cur_score = float(np.clip(cur_score + boost, 0.0, 0.98))
                        logger.info(f"[INSIDER BUYING ENGINE] Insider buy detected for {sym}: {report_nm} (Score -> {cur_score:.2f})")
                    elif raw_type in sell_keywords or any(k in report_nm for k in ['장내매도', '장내처분', '지분매각', '지분매도', '주식매도', '블록딜']):
                        penalty = 0.25
                        cur_score = float(np.clip(cur_score - penalty, 0.05, 1.0))

                # Cluster Buying Acceleration: Multiple insider purchases indicate strong executive consensus
                buy_count = sum(1 for item in matching_items if any(k in str(item.get('report_nm', '')) for k in ['장내매수', '장내취득', '신규매수', '주식매입', '지분매수', '지분취득']))
                if buy_count >= 2:
                    cur_score = float(np.clip(cur_score + 0.15, 0.0, 0.98))

                scores_map[sym] = float(np.clip(cur_score, 0.0, 0.98)) if np.isfinite(cur_score) else np.nan

        # Smart-Money Accumulation Fallback Proxy when insider_filings absent and prices_dict is provided
        if prices_dict and isinstance(prices_dict, dict) and bool(prices_dict):
            for sym in symbols:
                if pd.isna(scores_map[sym]):
                    sym_raw = sym.split('.')[0]
                    sym_clean = sym_raw.zfill(6) if sym_raw.isdigit() else sym_raw
                    p_df = prices_dict.get(sym)
                    if p_df is None:
                        p_df = prices_dict.get(sym_clean)
                    if p_df is None:
                        p_df = prices_dict.get(sym_raw)
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 5:
                        c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
                        h_col = 'High' if 'High' in p_df.columns else ('high' if 'high' in p_df.columns else None)
                        l_col = 'Low' if 'Low' in p_df.columns else ('low' if 'low' in p_df.columns else None)
                        v_col = 'Volume' if 'Volume' in p_df.columns else ('volume' if 'volume' in p_df.columns else None)
                        if c_col:
                            c_s = p_df[c_col].dropna().astype(float)
                            if len(c_s) >= 5:
                                n_bars = min(len(c_s), 20)
                                tail_df = p_df.iloc[-n_bars:]
                                c_tail = tail_df[c_col].astype(float)
                                v_tail = tail_df[v_col].astype(float) if v_col else pd.Series(1.0, index=tail_df.index)
                                h_tail = tail_df[h_col].astype(float) if h_col else c_tail
                                l_tail = tail_df[l_col].astype(float) if l_col else c_tail

                                # 20d CMF
                                hl_diff = h_tail - l_tail
                                mfm = np.where(hl_diff > 1e-5, ((c_tail - l_tail) - (h_tail - c_tail)) / hl_diff, np.sign(c_tail.diff().fillna(0.0)))
                                mfv = mfm * v_tail
                                cmf = float(mfv.sum() / max(v_tail.sum(), 1e-5))
                                cmf = float(np.clip(cmf, -1.0, 1.0))

                                # Up-to-Down Volume Ratio (UDVR)
                                c_diff = c_tail.diff().fillna(0.0)
                                up_vol = float(v_tail[c_diff > 0].sum())
                                down_vol = float(v_tail[c_diff < 0].sum())
                                udvr = (up_vol + 1.0) / (down_vol + 1.0)
                                udvr_norm = float(np.clip((udvr - 1.0) / (udvr + 1.0), -0.5, 0.5))

                                # 20d Moving Average Support (MAS)
                                sma20 = float(c_tail.mean())
                                last_c = float(c_tail.iloc[-1])
                                mas = (last_c - sma20) / max(sma20, 1e-5)
                                mas_norm = float(np.clip(mas * 2.0, -0.2, 0.2))

                                # High-Conviction Stealth Accumulation Booster
                                stealth_boost = 0.10 if (cmf > 0.20 and udvr_norm > 0.15) else 0.0
                                raw_acc = 0.50 + 0.25 * cmf + 0.20 * udvr_norm + 0.15 * mas_norm + stealth_boost
                                scores_map[sym] = float(np.clip(raw_acc, 0.05, 0.98))

        results = [{'symbol': str(k), 'insider_buying_score': float(np.clip(v, 0.0, 0.98)) if (pd.notna(v) and np.isfinite(v)) else np.nan} for k, v in scores_map.items()]
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            s_series = pd.to_numeric(res_df['insider_buying_score'], errors='coerce')
            valid_mask = s_series.notna()
            if valid_mask.sum() > 1:
                valid_scores = s_series[valid_mask]
                ranks = valid_scores.rank(pct=True, ascending=True)
                # Multi-Tier Insider Conviction Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                enhanced = np.where(ranks >= 0.95, (valid_scores * 1.15).clip(0.05, 0.98),
                           np.where(ranks >= 0.85, (valid_scores * 1.10).clip(0.05, 0.98), valid_scores))
                res_df.loc[valid_mask, 'insider_buying_score'] = pd.to_numeric(pd.Series(enhanced, index=valid_scores.index), errors='coerce').fillna(0.50).clip(0.05, 0.98)
            else:
                res_df['insider_buying_score'] = s_series
        return res_df

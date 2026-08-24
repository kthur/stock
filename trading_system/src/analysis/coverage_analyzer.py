"""
src/analysis/coverage_analyzer.py
Strategy Data Coverage & Missingness Analyzer.
Analyzes coverage rates, valid predictions, and data missingness reasons across all 14 strategies.
"""
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class StrategyCoverageAnalyzer:
    """
    Analyzes coverage, valid scores, NaNs, and missingness reasons across 18 strategies.
    """

    @property
    def STRATEGIES(self) -> List[str]:
        from src.core.strategy_registry import get_registry
        reg = get_registry()
        reg.auto_discover(["src.core", "src.ai"])
        return list(reg.get_all_ids())

    def __init__(self, strategies: Optional[List[str]] = None):
        self.strategies = strategies if strategies else self.STRATEGIES
        self.strategy_count = len(self.strategies)

    def _has_symbol_fundamental_data(self, features_df: Optional[Any], sym: str) -> bool:
        """
        Checks per-symbol non-NaN fundamental data in features_df (DataFrame or Dict).
        """
        if features_df is None:
            return False

        fund_cols = [
            'bps', 'roe', 'operating_margin', 'net_profit_margin',
            'revenue', 'operating_income', 'net_income', 'eps',
            'book_value', 'dividend_per_share', 'revenue_to_market_cap',
            'dividend_yield', 'eps_yield', 'eps_growth_1y'
        ]

        sym_str = str(sym)

        # Handle Dict of DataFrames per symbol
        if isinstance(features_df, dict):
            val = features_df.get(sym_str)
            if val is None:
                val = features_df.get(sym)
            if val is not None and isinstance(val, pd.DataFrame) and not val.empty:
                present_cols = [c for c in fund_cols if c in val.columns]
                if present_cols:
                    arr = val[present_cols].values
                    return bool(np.any(pd.notna(arr) & np.isfinite(arr)))
            return False

        if not isinstance(features_df, pd.DataFrame) or features_df.empty:
            return False

        present_cols = [c for c in fund_cols if c in features_df.columns]
        if not present_cols:
            return False

        try:
            if 'symbol' in features_df.columns:
                sub = features_df[features_df['symbol'].astype(str) == sym_str]
                if sub.empty and sym_str.isdigit():
                    sub = features_df[features_df['symbol'].astype(str) == sym_str.zfill(6)]
                if sub.empty:
                    return False
                vals = sub[present_cols].values
                return bool(np.any(pd.notna(vals) & np.isfinite(vals)))
            elif sym in features_df.index or sym_str in features_df.index:
                key = sym if sym in features_df.index else sym_str
                row_or_sub = features_df.loc[key]
                if isinstance(row_or_sub, pd.DataFrame):
                    vals = row_or_sub[present_cols].values
                    return bool(np.any(pd.notna(vals) & np.isfinite(vals)))
                elif isinstance(row_or_sub, pd.Series):
                    vals = row_or_sub[present_cols].values
                    return bool(np.any(pd.notna(vals) & np.isfinite(vals)))
        except Exception as e:
            logger.debug(f"Error checking fundamental data for {sym}: {e}")

        return False

    def analyze_coverage(
        self,
        ensemble_df: pd.DataFrame,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[pd.DataFrame] = None,
        raw_scores: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Calculates per-strategy coverage stats and categorizes missing reasons.
        Returns summary dictionary.
        """
        if ensemble_df is None or ensemble_df.empty:
            return {'total_symbols': 0, 'strategies': {}}

        target_df = raw_scores
        if target_df is None and hasattr(ensemble_df, 'attrs') and isinstance(ensemble_df.attrs, dict) and 'raw_scores' in ensemble_df.attrs:
            target_df = ensemble_df.attrs['raw_scores']
        if target_df is None:
            target_df = ensemble_df

        total_symbols = len(ensemble_df)

        from src.core.strategy_registry import get_registry
        reg_inst = get_registry()
        reg_inst.auto_discover(["src.core", "src.ai"])
        col_map = reg_inst.get_all_score_columns()

        strat_stats = {}

        for strat in self.strategies:
            c_col = col_map.get(strat)
            if c_col and c_col in target_df.columns:
                series = pd.to_numeric(target_df[c_col], errors="coerce")
                # Valid if non-null and finite
                valid_mask = series.notna() & np.isfinite(series)
                valid_cnt = int(valid_mask.sum())
                missing_cnt = total_symbols - valid_cnt
                cov_pct = (valid_cnt / total_symbols * 100.0) if total_symbols > 0 else 0.0
            else:
                valid_mask = pd.Series(False, index=target_df.index)
                valid_cnt = 0
                missing_cnt = total_symbols
                cov_pct = 0.0

            # Dynamic missingness reason calculation by inspecting underlying data
            reasons = {}
            if missing_cnt > 0:
                if 'symbol' in target_df.columns:
                    valid_syms = set(target_df.loc[valid_mask, 'symbol'])
                else:
                    valid_syms = set(target_df.index[valid_mask])

                if 'symbol' in ensemble_df.columns:
                    all_ens_syms = set(ensemble_df['symbol'])
                else:
                    all_ens_syms = set(ensemble_df.index)

                missing_syms = all_ens_syms - valid_syms
                if not missing_syms and 'symbol' in target_df.columns:
                    missing_syms = set(target_df.loc[~valid_mask, 'symbol'])

                no_price_cnt = 0
                no_fund_cnt = 0
                low_eq_cnt = 0
                other_cnt = 0
                for sym in missing_syms:
                    sym_str = str(sym)
                    p_df = prices_dict.get(sym_str) if prices_dict else None
                    if p_df is None and prices_dict:
                        if sym_str.isdigit():
                            p_df = prices_dict.get(sym_str.zfill(6))
                        if p_df is None:
                            p_df = prices_dict.get(sym)

                    has_price = (p_df is not None and len(p_df) >= 20)

                    if not has_price:
                        no_price_cnt += 1
                    elif strat in ['rim_valuation', 'rim'] and self._has_symbol_fundamental_data(features_df, sym_str):
                        # Fundamentals exist but RIM score is NaN → 이익의 질(영업손실+순이익 양수) 필터로 제외됨
                        low_eq_cnt += 1
                    elif strat in ['rim_valuation', 'rim', 'mq_factor', 'mq', 'arm_factor', 'arm', 'accruals_quality', 'accruals', 'valueup_catalyst', 'value_up'] and not self._has_symbol_fundamental_data(features_df, sym_str):
                        no_fund_cnt += 1
                    else:
                        other_cnt += 1

                if no_price_cnt > 0:
                    reasons['INSUFFICIENT_PRICE_HISTORY'] = no_price_cnt
                if no_fund_cnt > 0:
                    reasons['NO_FUNDAMENTAL_DATA'] = no_fund_cnt
                if low_eq_cnt > 0:
                    reasons['LOW_EARNINGS_QUALITY'] = low_eq_cnt
                if other_cnt > 0:
                    options_strats = {'iv_skew', 'gamma_squeeze'}
                    us_strats = {'darkpool', 'darkpool_hft'}
                    pair_strats = {'stat_arb'}
                    if strat in options_strats:
                        reasons['NO_OPTIONS_CHAIN'] = other_cnt
                    elif strat in us_strats:
                        reasons['NON_US_MARKET_SCOPE'] = other_cnt
                    elif strat in pair_strats:
                        reasons['NO_COINTEGRATED_PAIR'] = other_cnt
                    else:
                        reasons['STRATEGY_SIGNAL_NEUTRAL'] = other_cnt

            strat_stats[strat] = {
                'valid_count': valid_cnt,
                'missing_count': missing_cnt,
                'coverage_pct': round(cov_pct, 1),
                'reasons': reasons
            }

        return {
            'total_symbols': total_symbols,
            'strategies': strat_stats
        }

    def generate_coverage_report(
        self,
        coverage_data: Dict[str, Any],
        date_str: str = ""
    ) -> str:
        """Generates text report for strategy data coverage and missingness."""
        lines = []
        lines.append(f"=== {self.strategy_count}-Strategy Data Coverage & Missingness Report ===")
        lines.append(f"Date: {date_str}")
        lines.append(f"Total Evaluated Symbols: {coverage_data.get('total_symbols', 0)}")
        lines.append("")
        lines.append(f"{'Strategy':<22}{'Valid Count':<15}{'Missing Count':<15}{'Coverage %':<15}{'Primary Missing Reason':<30}")
        lines.append("-" * 97)

        strats = coverage_data.get('strategies', {})
        for s_name, s_info in strats.items():
            v_cnt = s_info.get('valid_count', 0)
            m_cnt = s_info.get('missing_count', 0)
            cov = s_info.get('coverage_pct', 0.0)
            reasons = s_info.get('reasons', {})
            top_reason = max(reasons, key=reasons.get) if reasons else "None (100% Valid)"
            lines.append(f"{s_name:<22}{v_cnt:<15}{m_cnt:<15}{cov:>6.1f}%          {top_reason:<30}")

        return "\n".join(lines)

    def generate_m5_sentiment_report(
        self,
        sentiment_metrics_list: List[Any],
        kst_now_str: str = ""
    ) -> str:
        """
        Formats [MILESTONE 5: LLM/NLP DART & SEC FILING SENTIMENT REPORT] section.
        """
        total_filings = len(sentiment_metrics_list)
        if total_filings == 0:
            lines = [
                "================================================================================",
                "[MILESTONE 5: LLM/NLP DART & SEC FILING SENTIMENT REPORT]",
                "================================================================================",
                f"Evaluation Time (KST): {kst_now_str}",
                "Total Corporate Filings Analyzed: 0",
                "Processing Source Distribution:",
                "  - Primary LLM / FinBERT Pipeline: 0 (0.0%)",
                "  - Offline Lexicon Fallback      : 0 (0.0%)",
                "  - SQLite Cache Hits             : 0 (0.0%)",
                "Average Sentiment Metrics:",
                "  - Mean Filing Tone Score        : 0.50",
                "  - Mean Catalyst Surprise Score  : 0.50",
                "  - Mean Composite Sentiment Score: 0.50",
                "  - Mean Model Confidence Score   : 0.70",
                "================================================================================\n"
            ]
            return "\n".join(lines)

        dart_cnt = 0
        sec_cnt = 0
        llm_cnt = 0
        lexicon_cnt = 0
        cache_cnt = 0

        tones = []
        surprises = []
        composites = []
        confidences = []

        top_positive = []
        top_negative = []

        for m in sentiment_metrics_list:
            sym = str(getattr(m, 'symbol', ''))
            tone = float(getattr(m, 'filing_tone_score', 0.5))
            surprise = float(getattr(m, 'catalyst_surprise_score', 0.5))
            composite = float(getattr(m, 'composite_sentiment_score', 0.5))
            conf = float(getattr(m, 'confidence_score', 0.7))
            src = str(getattr(m, 'source_type', 'OFFLINE_LEXICON'))

            if any(sym.endswith(suffix) for suffix in ['.US', '.N', '.O', 'SP500']) or (sym.isupper() and not sym.isdigit()):
                sec_cnt += 1
            else:
                dart_cnt += 1

            if src == 'LLM_FINBERT':
                llm_cnt += 1
            elif src == 'CACHE':
                cache_cnt += 1
            else:
                lexicon_cnt += 1

            tones.append(tone)
            surprises.append(surprise)
            composites.append(composite)
            confidences.append(conf)

            intensity_delta = (composite - 0.5) * 2.0 * conf
            mult = 1.0 + float(np.clip(intensity_delta * 0.5, -0.5, 0.5))

            item_info = {
                'symbol': sym,
                'composite': composite,
                'multiplier': mult,
                'source': src
            }
            top_positive.append(item_info)
            top_negative.append(item_info)

        llm_pct = (llm_cnt / total_filings * 100.0)
        lexicon_pct = (lexicon_cnt / total_filings * 100.0)
        cache_pct = (cache_cnt / total_filings * 100.0)

        mean_tone = float(np.mean(tones)) if tones else 0.5
        mean_tone = float(np.clip(mean_tone, 0.0, 1.0)) if np.isfinite(mean_tone) else 0.5
        mean_surprise = float(np.mean(surprises)) if surprises else 0.5
        mean_surprise = float(np.clip(mean_surprise, 0.0, 1.0)) if np.isfinite(mean_surprise) else 0.5
        mean_composite = float(np.mean(composites)) if composites else 0.5
        mean_composite = float(np.clip(mean_composite, 0.0, 1.0)) if np.isfinite(mean_composite) else 0.5
        mean_conf = float(np.mean(confidences)) if confidences else 0.7
        mean_conf = float(np.clip(mean_conf, 0.0, 1.0)) if np.isfinite(mean_conf) else 0.7

        def _safe_comp_key(item_dict):
            val = item_dict.get('composite', 0.5)
            try:
                f_val = float(val)
                return f_val if np.isfinite(f_val) else 0.5
            except (ValueError, TypeError):
                return 0.5

        top_pos_sorted = sorted(top_positive, key=_safe_comp_key, reverse=True)[:5]
        top_neg_sorted = sorted(top_negative, key=_safe_comp_key)[:5]

        lines = [
            "================================================================================",
            "[MILESTONE 5: LLM/NLP DART & SEC FILING SENTIMENT REPORT]",
            "================================================================================",
            f"Evaluation Time (KST): {kst_now_str}",
            f"Total Corporate Filings Analyzed: {total_filings} (DART: {dart_cnt}, SEC: {sec_cnt})",
            "Processing Source Distribution:",
            f"  - Primary LLM / FinBERT Pipeline: {llm_cnt} ({llm_pct:.1f}%)",
            f"  - Offline Lexicon Fallback      : {lexicon_cnt} ({lexicon_pct:.1f}%)",
            f"  - SQLite Cache Hits             : {cache_cnt} ({cache_pct:.1f}%)",
            "Average Sentiment Metrics:",
            f"  - Mean Filing Tone Score        : {mean_tone:.2f}",
            f"  - Mean Catalyst Surprise Score  : {mean_surprise:.2f}",
            f"  - Mean Composite Sentiment Score: {mean_composite:.2f}",
            f"  - Mean Model Confidence Score   : {mean_conf:.2f}",
            "",
            "--- Top Positive Sentiment Catalysts (Multiplier ~1.5x) ---"
        ]

        for i, item in enumerate(top_pos_sorted, 1):
            lines.append(f"  {i}. {item['symbol']}: Composite {item['composite']:.2f} | Multiplier {item['multiplier']:.2f}x | Source: {item['source']}")

        lines.append("--- Top Negative Sentiment Catalysts (Multiplier ~0.5x) ---")
        for i, item in enumerate(top_neg_sorted, 1):
            lines.append(f"  {i}. {item['symbol']}: Composite {item['composite']:.2f} | Multiplier {item['multiplier']:.2f}x | Source: {item['source']}")

        lines.append("================================================================================")
        return "\n".join(lines)


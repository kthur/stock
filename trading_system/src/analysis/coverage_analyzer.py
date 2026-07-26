"""
src/analysis/coverage_analyzer.py
Strategy Data Coverage & Missingness Analyzer.
Analyzes coverage rates, valid predictions, and data missingness reasons across all 14 strategies.
"""
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class StrategyCoverageAnalyzer:
    """
    Analyzes coverage, valid scores, NaNs, and missingness reasons across 14 strategies.
    """

    STRATEGIES = [
        'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
        'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation',
        'event_driven', 'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal'
    ]

    def analyze_coverage(
        self,
        ensemble_df: pd.DataFrame,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Calculates per-strategy coverage stats and categorizes missing reasons.
        Returns summary dictionary.
        """
        if ensemble_df is None or ensemble_df.empty:
            return {'total_symbols': 0, 'strategies': {}}

        total_symbols = len(ensemble_df)

        col_map = {
            'regression': 'reg_score',
            'surge': 'surge_score',
            'lead_lag': 'll_score',
            'vcp_rule': 'vcp_rule_score',
            'vcp_ml': 'vcp_ml_score',
            'lstm': 'lstm_score',
            'stat_arb': 'stat_arb_score',
            'sector_rotation': 'sector_score',
            'rim_valuation': 'rim_score',
            'event_driven': 'event_score',
            'mq_factor': 'mq_score',
            'iv_skew': 'iv_skew_score',
            'order_flow': 'order_flow_score',
            'short_term_reversal': 'reversal_score'
        }

        strat_stats = {}

        for strat in self.STRATEGIES:
            c_col = col_map.get(strat)
            if c_col and c_col in ensemble_df.columns:
                series = ensemble_df[c_col]
                # Valid if non-null and finite
                valid_mask = series.notna() & np.isfinite(series)
                valid_cnt = int(valid_mask.sum())
                missing_cnt = total_symbols - valid_cnt
                cov_pct = (valid_cnt / total_symbols * 100.0) if total_symbols > 0 else 0.0
            else:
                valid_cnt = 0
                missing_cnt = total_symbols
                cov_pct = 0.0

            # Missingness reason estimation
            reasons = {}
            if missing_cnt > 0:
                if strat in ['rim_valuation', 'mq_factor']:
                    reasons['NO_FUNDAMENTAL'] = missing_cnt
                elif strat == 'iv_skew':
                    reasons['NO_OPTIONS_DATA'] = missing_cnt
                elif strat in ['stat_arb']:
                    reasons['UNCOINTEGRATED_OR_SNR_LOW'] = missing_cnt
                else:
                    reasons['INSUFFICIENT_PRICE_HISTORY'] = missing_cnt

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
        lines.append("=== 14-Strategy Data Coverage & Missingness Report ===")
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
            top_reason = list(reasons.keys())[0] if reasons else "None (100% Valid)"
            lines.append(f"{s_name:<22}{v_cnt:<15}{m_cnt:<15}{cov:>6.1f}%          {top_reason:<30}")

        return "\n".join(lines)

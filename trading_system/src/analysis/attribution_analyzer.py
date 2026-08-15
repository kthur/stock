import logging
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    'reg_score': 'Regression',
    'surge_score': 'Surge Classifier',
    'll_score': 'Lead-Lag',
    'vcp_rule_score': 'VCP Rule Detector',
    'vcp_ml_score': 'VCP ML Predictor',
    'lstm_score': 'Strict Causal LSTM',
    'stat_arb_score': 'Stat-Arb Cointegration',
    'sector_score': 'Sector Rotation',
    'rim_score': 'RIM Valuation',
    'event_score': 'Event-Driven',
    'mq_score': 'MQ Factor',
    'iv_skew_score': 'Options IV Skew',
    'order_flow_score': 'Order Flow Imbalance',
    'reversal_score': 'Short-Term Reversal',
    'arm_score': 'ARM Factor',
    'card_score': 'CARD Factor',
    'latr_score': 'LATR Factor',
    'inst_foreign_score': 'Inst & Foreign Sector',
    'supply_chain_score': 'Supply Chain Momentum',
    'sentiment_score': 'NLP Sentiment Catalyst',
    'factor_neutralized_score': 'Factor Neutralized Alpha',
    'vol_target_score': 'Dynamic Vol Targeting',
    'microstructure_score': 'Microstructure Imbalance',
    'accruals_score': 'Accruals Quality Anomaly',
    'short_squeeze_score': 'Short Interest & Squeeze',
    'valueup_score': 'Value-Up & Shareholder Yield',
    'trend_efficiency_score': 'Kaufman Trend Efficiency',
    'gamma_squeeze_score': 'Gamma Squeeze Strategy',
    'insider_buying_score': 'Insider Buying Strategy',
    'earnings_tone_drift_score': 'Earnings Tone Drift',
    'hft_score': 'High-Frequency Order Flow',
}

class StrategyAttributionAnalyzer:
    """
    Evaluates 17-strategy PnL Attribution & Shapley Value Proxy contributions.
    Identifies top-performing alpha drivers and underperforming strategies.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        if output_dir is None:
            self.output_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.output_dir = Path(output_dir)

    def analyze_attribution(
        self,
        ensemble_predictions_df: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Computes per-strategy factor contributions to total expected portfolio alpha.
        """
        if ensemble_predictions_df is None or ensemble_predictions_df.empty:
            return {'status': 'EMPTY'}

        df = ensemble_predictions_df.copy()
        strategy_cols = [c for c in STRATEGY_MAP.keys() if c in df.columns]

        if not strategy_cols:
            return {'status': 'NO_STRATEGY_COLS'}

        # Calculate average score & weighted contribution per strategy
        strat_summaries = []
        if 'ensemble_expected_return' in df.columns:
            ret_s = pd.to_numeric(df['ensemble_expected_return'], errors='coerce').dropna()
            total_exp_ret = float(ret_s.mean()) if not ret_s.empty else 0.0
        else:
            total_exp_ret = 0.0

        for col in strategy_cols:
            name = STRATEGY_MAP[col]
            num_s = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            avg_score = float(num_s.mean()) if not num_s.empty else 0.0
            non_zero_count = int((num_s.abs() > 1e-6).sum())
            coverage_pct = (non_zero_count / len(df)) * 100.0 if len(df) > 0 else 0.0

            # Linear attribution proxy
            alpha_contrib = avg_score * (total_exp_ret / 100.0) * (coverage_pct / 100.0)

            strat_summaries.append({
                'col': col,
                'strategy_name': name,
                'avg_score': avg_score,
                'coverage_pct': coverage_pct,
                'alpha_contrib': alpha_contrib
            })

        summary_df = pd.DataFrame(strat_summaries).sort_values(by='alpha_contrib', ascending=False).reset_index(drop=True)

        report_text = self._generate_report_text(summary_df, total_exp_ret, len(df))
        report_path = self.output_dir / "strategy_attribution_report.txt"
        tmp_report_path = report_path.with_suffix(".tmp.txt")
        try:
            with open(tmp_report_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            tmp_report_path.replace(report_path)
            logger.info(f"Generated Strategy Attribution Report at {report_path}")
        except Exception as e:
            if tmp_report_path.exists():
                try:
                    tmp_report_path.unlink()
                except Exception:
                    pass
            logger.error(f"Failed to write Strategy Attribution Report: {e}")

        return {
            'status': 'SUCCESS',
            'summary_df': summary_df,
            'report_path': str(report_path)
        }

    def _generate_report_text(self, summary_df: pd.DataFrame, total_exp_ret: float, total_symbols: int) -> str:
        lines = []
        lines.append("==========================================================================")
        lines.append("        31-STRATEGY ALPHA ATTRIBUTION & FACTOR CONTRIBUTION REPORT        ")
        lines.append("==========================================================================")
        lines.append(f"• Evaluated Symbol Count     : {total_symbols:,} symbols")
        lines.append(f"• Total Portfolio Exp Return : {total_exp_ret:.2f}%\n")
        lines.append(f"{'Rank':<5} {'Strategy Name':<25} {'Avg Score':<12} {'Coverage':<12} {'Alpha Contrib':<15}")
        lines.append("-" * 72)

        for idx, row in summary_df.iterrows():
            lines.append(
                f"{idx+1:<5} {row['strategy_name']:<25} {row['avg_score']:<12.4f} "
                f"{row['coverage_pct']:>6.1f}%       {row['alpha_contrib']:>10.4f}"
            )

        lines.append("\n[Alpha Driver Summary]")
        if not summary_df.empty:
            top1 = summary_df.iloc[0]['strategy_name']
            top2 = summary_df.iloc[1]['strategy_name'] if len(summary_df) > 1 else 'N/A'
            lines.append(f"• Primary Alpha Drivers   : 1st {top1}, 2nd {top2}")

        lines.append("==========================================================================")
        return "\n".join(lines)

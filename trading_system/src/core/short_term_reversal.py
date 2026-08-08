"""
src/core/short_term_reversal.py
Short-Term Reversal Engine ( 단기 반전 역발상 모듈 ).
Identifies short-term oversold conditions (3~5 day drops, Bollinger band lower breaches)
filtered by fundamental quality and volatility bounds to calculate mean-reversion reversal_scores [0.0, 1.0].
"""
import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ShortTermReversalEngine:
    """
    Short-Term Reversal Strategy Engine.
    Detects temporary overreactions in sound stocks for high-probability mean-reversion entries.
    """

    def compute_reversal_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        features_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Computes Short-Term Reversal scores for a set of symbols.
        Returns DataFrame with ['symbol', 'reversal_score'].
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])

        records = []

        for sym, df in prices_dict.items():
            if df is None or len(df) < 20:
                continue
            try:
                # Ensure chronological ascending sort
                df_sorted = df.sort_index(ascending=True) if hasattr(df.index, 'is_monotonic_increasing') and not df.index.is_monotonic_increasing else df
                close = df_sorted['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 20:
                    continue

                # 5-day return (Short-term drop magnitude)
                ret_5d = float(close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) >= 6 else 0.0

                # Count true consecutive down days working backwards from latest day
                daily_rets = close.pct_change().iloc[-5:]
                consec_down = 0
                for r in reversed(daily_rets.values):
                    if r < 0:
                        consec_down += 1
                    else:
                        break

                # 20-day SMA & Bollinger Lower Band distance
                sma_20 = float(close.iloc[-20:].mean())
                std_20 = float(close.iloc[-20:].std())
                lower_band = sma_20 - 2.0 * std_20 if std_20 > 0 else sma_20

                cur_price = float(close.iloc[-1])
                dist_lower_band = (cur_price - lower_band) / (std_20 + 1e-8)

                # Oversold score: Negative ret_5d, consecutive down days, and price near/below lower band increase reversal potential
                oversold_metric = -1.0 * ret_5d + 0.1 * consec_down - 0.2 * dist_lower_band

                records.append({
                    'symbol': sym,
                    'oversold_metric': oversold_metric
                })
            except Exception as e:
                logger.debug(f"Short term reversal calc failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])

        res_df = pd.DataFrame(records)

        # Apply fundamental quality filter if available to prevent value traps
        if features_df is not None and not features_df.empty:
            f_df = features_df.copy()
            if 'symbol' not in f_df.columns and f_df.index.name == 'symbol':
                f_df = f_df.reset_index()

            if 'operating_margin' in f_df.columns:
                f_sub = f_df[['symbol', 'operating_margin']].groupby('symbol').last().reset_index()
                res_df = res_df.merge(f_sub, on='symbol', how='left')
                # Penalize loss-making distress stocks (operating margin < -0.10)
                res_df.loc[res_df['operating_margin'] < -0.10, 'oversold_metric'] -= 1.0

        # Percentile rank oversold metric -> reversal_score [0, 1]
        res_df['reversal_score'] = res_df['oversold_metric'].rank(pct=True, ascending=True)
        res_df['reversal_score'] = res_df['reversal_score'].clip(0.0, 1.0)
        return res_df[['symbol', 'reversal_score']]

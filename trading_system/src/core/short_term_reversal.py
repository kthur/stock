"""
src/core/short_term_reversal.py
Short-Term Reversal Engine ( 단기 반전 역발상 모듈 ).
Identifies short-term oversold conditions (3~5 day drops, Bollinger band lower breaches)
filtered by fundamental quality and volatility bounds to calculate mean-reversion reversal_scores [0.0, 1.0].
"""
import logging
from typing import Dict, Optional, Any
import pandas as pd

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="short_term_reversal",
        display_name="Short-Term Reversal",
        score_column="reversal_score",
        category="factor",
        output_file="reversal_predictions.txt",
        default_regime_weights={
            "BEAR": 0.08, "BEAR_HIGH_VOL": 0.10, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.04
        },
    )
)
class ShortTermReversalEngine(BaseStrategyEngine):
    """
    Short-Term Reversal Strategy Engine.
    Detects temporary overreactions in sound stocks for high-probability mean-reversion entries.
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
        try:
            features_df = kwargs.get("features_df")
            return self.compute_reversal_scores(prices_dict, features_df=features_df)
        except Exception as e:
            logger.warning(f"[ShortTermReversalEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "reversal_score"])

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

        valid_cols = {}
        for sym, df in prices_dict.items():
            if df is None or len(df) < 20:
                continue
            try:
                df_sorted = df.sort_index(ascending=True) if hasattr(df.index, 'is_monotonic_increasing') and not df.index.is_monotonic_increasing else df
                close = df_sorted['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) >= 20:
                    valid_cols[sym] = close.iloc[-20:].values
            except Exception:
                continue

        if not valid_cols:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])

        close_2d = pd.DataFrame(valid_cols)  # 20 rows x N columns
        cur_price = close_2d.iloc[-1]
        price_5d_ago = close_2d.iloc[-6]
        ret_5d = (cur_price / price_5d_ago) - 1.0

        # Vectorized consecutive down days working backwards from latest day (day -1)
        diffs_last5 = close_2d.iloc[-6:].diff(axis=0).iloc[1:]  # 5 rows x N cols
        is_down = (diffs_last5 < 0).values  # (5, N) boolean array
        cond5 = is_down[4]
        consec = np.where(cond5, 1.0, 0.0)
        cond4 = cond5 & is_down[3]
        consec = np.where(cond4, consec + 1.0, consec)
        cond3 = cond4 & is_down[2]
        consec = np.where(cond3, consec + 1.0, consec)
        cond2 = cond3 & is_down[1]
        consec = np.where(cond2, consec + 1.0, consec)
        cond1 = cond2 & is_down[0]
        consec = np.where(cond1, consec + 1.0, consec)

        sma_20 = close_2d.mean(axis=0)
        std_20 = close_2d.std(axis=0, ddof=1)
        lower_band = np.where(std_20 > 0, sma_20 - 2.0 * std_20, sma_20)
        dist_lower_band = (cur_price - lower_band) / (std_20 + 1e-8)

        oversold_metric = -1.0 * ret_5d + 0.1 * consec - 0.2 * dist_lower_band

        res_df = pd.DataFrame({
            'symbol': close_2d.columns,
            'oversold_metric': oversold_metric
        })

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

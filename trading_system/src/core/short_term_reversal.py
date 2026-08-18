"""
src/core/short_term_reversal.py
Short-Term Reversal Engine ( 단기 반전 역발상 모듈 ).
Identifies short-term oversold conditions (3~5 day drops, Bollinger band lower breaches)
filtered by fundamental quality and volatility bounds to calculate mean-reversion reversal_scores [0.0, 1.0].
"""
import logging
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np

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
                    valid_cols[sym] = close
            except Exception:
                continue

        if not valid_cols:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])

        # Align all series on Date Index, forward-fill missing dates, and take last 20 trading days
        close_2d = pd.DataFrame(valid_cols).ffill().tail(20)
        if len(close_2d) < 6:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])
        cur_price = close_2d.iloc[-1]
        price_5d_ago = close_2d.iloc[-6]
        ret_5d = ((cur_price / price_5d_ago.replace(0, np.nan)) - 1.0).fillna(0.0)

        # Vectorized consecutive down days
        diffs_last5 = close_2d.iloc[-6:].diff(axis=0).iloc[1:]  # 5 rows x N cols
        is_down = (diffs_last5 < 0).values  # (5, N) boolean array: index 4 is today, 3 is yesterday

        # Consecutive down days ending on today (index 4)
        cond5 = is_down[4]
        consec_today = np.where(cond5, 1.0, 0.0)
        cond4 = cond5 & is_down[3]
        consec_today = np.where(cond4, consec_today + 1.0, consec_today)
        cond3 = cond4 & is_down[2]
        consec_today = np.where(cond3, consec_today + 1.0, consec_today)
        cond2 = cond3 & is_down[1]
        consec_today = np.where(cond2, consec_today + 1.0, consec_today)
        cond1 = cond2 & is_down[0]
        consec_today = np.where(cond1, consec_today + 1.0, consec_today)

        # Consecutive down days ending on yesterday (index 3) for turnaround bounce detection
        p_cond4 = is_down[3]
        consec_prior = np.where(p_cond4, 1.0, 0.0)
        p_cond3 = p_cond4 & is_down[2]
        consec_prior = np.where(p_cond3, consec_prior + 1.0, consec_prior)
        p_cond2 = p_cond3 & is_down[1]
        consec_prior = np.where(p_cond2, consec_prior + 1.0, consec_prior)
        p_cond1 = p_cond2 & is_down[0]
        consec_prior = np.where(p_cond1, consec_prior + 1.0, consec_prior)

        consec = np.maximum(consec_today, consec_prior)

        sma_20 = close_2d.mean(axis=0)
        std_20 = close_2d.std(axis=0, ddof=1)
        lower_band = np.where(std_20 > 0, sma_20 - 2.0 * std_20, sma_20)
        dist_lower_band = (cur_price - lower_band) / (std_20 + 1e-8)

        # First green bounce bonus with volume confirmation to prioritize turnaround over falling knives
        ret_1d = ((cur_price / close_2d.iloc[-2].replace(0, np.nan)) - 1.0).fillna(0.0)

        # Calculate volume surge if available
        vol_cols = {}
        for sym in close_2d.columns:
            df_sym = prices_dict.get(sym)
            if df_sym is not None and ('Volume' in df_sym.columns or 'volume' in df_sym.columns):
                v_col = 'Volume' if 'Volume' in df_sym.columns else 'volume'
                vol_s = df_sym[v_col].dropna()
                if len(vol_s) >= 6:
                    vol_cols[sym] = vol_s

        if vol_cols:
            vol_2d = pd.DataFrame(vol_cols).reindex(columns=close_2d.columns).ffill().tail(6)
            cur_vol = vol_2d.iloc[-1]
            avg_vol_5d = vol_2d.iloc[-6:-1].mean(axis=0).replace(0, 1.0)
            vol_surge = (cur_vol / avg_vol_5d) > 1.20
        else:
            vol_surge = pd.Series(False, index=close_2d.columns)

        bounce_bonus = np.where(
            (consec_prior >= 2.0) & (ret_1d > 0.0),
            np.where(vol_surge, 0.25, 0.15),
            0.0
        )

        # Vectorized RSI-14 Oversold Indicator
        delta = close_2d.diff().iloc[1:]
        gain = np.maximum(delta, 0.0)
        loss = np.maximum(-delta, 0.0)
        avg_gain = gain.tail(14).mean(axis=0)
        avg_loss = loss.tail(14).mean(axis=0).replace(0, 1e-8)
        rs_val = avg_gain / avg_loss
        rsi_14 = 100.0 - (100.0 / (1.0 + rs_val))
        rsi_oversold_term = np.clip((35.0 - rsi_14) / 20.0, -0.2, 0.3)

        oversold_metric = -1.0 * ret_5d + 0.1 * consec - 0.2 * dist_lower_band + bounce_bonus + rsi_oversold_term

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

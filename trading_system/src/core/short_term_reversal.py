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
                close_col = 'Close' if 'Close' in df_sorted.columns else ('close' if 'close' in df_sorted.columns else None)
                if not close_col:
                    continue
                close = df_sorted[close_col]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) >= 20:
                    valid_cols[sym] = close
            except Exception:
                continue

        if not valid_cols:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])

        # Align all series on Date Index, sort chronologically, forward-fill missing dates, and take last 20 trading days
        close_2d = pd.DataFrame(valid_cols).sort_index().ffill().tail(20)
        if len(close_2d) < 6:
            return pd.DataFrame(columns=['symbol', 'reversal_score'])
        cur_price = close_2d.iloc[-1]
        price_5d_ago = close_2d.iloc[-6]
        ret_5d = ((cur_price / price_5d_ago.replace(0, np.nan)) - 1.0).fillna(0.0)

        # Vectorized consecutive down days using rolling
        neg_returns = (close_2d.pct_change() < 0).astype(int)

        consec_today = np.zeros(close_2d.shape[1])
        consec_prior = np.zeros(close_2d.shape[1])
        for n in range(1, 6):
            is_n_down = (neg_returns.rolling(n).sum() == n).astype(int)
            consec_today = np.where(is_n_down.iloc[-1] == 1, float(n), consec_today)
            consec_prior = np.where(is_n_down.iloc[-2] == 1, float(n), consec_prior)

        consec = np.maximum(consec_today, consec_prior)

        sma_20 = close_2d.mean(axis=0)
        std_20 = close_2d.std(axis=0, ddof=1)
        lower_band = np.where(std_20 > 0, sma_20 - 2.0 * std_20, sma_20)
        # R11-4 Fix: Vectorized safe bounding with np.maximum to prevent distortion on micro-volatility
        dist_lower_band = np.clip((cur_price - lower_band) / np.maximum(std_20, 1e-6), -2.0, 4.0)

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

        # Multi-Tier Reversal Ignition & Turnaround Confirmation
        bounce_bonus = np.where(
            (consec_prior >= 3.0) & (ret_1d >= 0.02) & vol_surge,
            0.35,  # Super Reversal Turnaround: Severe oversold streak + strong green impulse + volume surge
            np.where(
                (consec_prior >= 2.0) & (ret_1d > 0.0),
                np.where(vol_surge, 0.25, 0.15),
                0.0
            )
        )

        # Vectorized Dual-Horizon RSI (Fast RSI-5 + Standard RSI-14) with R7-8 Wilder's Exponential Smoothing
        delta = close_2d.diff().iloc[1:]
        gain = np.maximum(delta, 0.0)
        loss = np.maximum(-delta, 0.0)
        # Wilder's exponential moving average smoothing (alpha = 1/N)
        gain_ewm_14 = gain.ewm(alpha=1.0/14.0, adjust=False).mean().iloc[-1]
        loss_ewm_14 = loss.ewm(alpha=1.0/14.0, adjust=False).mean().iloc[-1]
        flat_mask_14 = (gain_ewm_14 < 1e-8) & (loss_ewm_14 < 1e-8)
        avg_loss_14 = loss_ewm_14.replace(0, 1e-8)
        rs_val_14 = gain_ewm_14 / avg_loss_14
        rsi_14 = np.where(flat_mask_14, 50.0, 100.0 - (100.0 / (1.0 + rs_val_14)))

        gain_ewm_5 = gain.ewm(alpha=1.0/5.0, adjust=False).mean().iloc[-1]
        loss_ewm_5 = loss.ewm(alpha=1.0/5.0, adjust=False).mean().iloc[-1]
        flat_mask_5 = (gain_ewm_5 < 1e-8) & (loss_ewm_5 < 1e-8)
        avg_loss_5 = loss_ewm_5.replace(0, 1e-8)
        rs_val_5 = gain_ewm_5 / avg_loss_5
        rsi_5 = np.where(flat_mask_5, 50.0, 100.0 - (100.0 / (1.0 + rs_val_5)))

        # R5-6: 50% Fast RSI-5 + 50% Standard RSI-14
        rsi_oversold_term = 0.5 * np.clip((35.0 - rsi_14) / 20.0, -0.2, 0.3) + 0.5 * np.clip((30.0 - rsi_5) / 20.0, -0.2, 0.3)

        # Standardize individual signals cross-sectionally when N >= 5 to prevent single-variable domination
        if len(close_2d.columns) >= 5:
            def _robust_norm(s):
                s_num = pd.to_numeric(pd.Series(s), errors='coerce').fillna(0.0)
                std = float(s_num.std())
                return (s_num - s_num.mean()) / (std if std > 1e-6 else 1.0)

            z_ret = _robust_norm(-ret_5d)
            z_consec = _robust_norm(consec)
            z_dist = _robust_norm(-dist_lower_band)
            z_rsi = _robust_norm(rsi_oversold_term)
            raw_oversold = 0.35 * z_ret.values + 0.25 * z_consec.values + 0.20 * z_dist.values + 0.20 * z_rsi.values + bounce_bonus
        else:
            raw_oversold = -1.0 * ret_5d + 0.1 * consec - 0.2 * dist_lower_band + bounce_bonus + rsi_oversold_term

        oversold_metric = pd.to_numeric(pd.Series(raw_oversold, index=close_2d.columns), errors='coerce').fillna(0.0).clip(-10.0, 10.0)

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

        # Convert oversold metric to absolute score with sigmoid, combined with cross-sectional rank
        if len(res_df) == 1:
            res_df['reversal_score'] = 0.50
            return res_df[['symbol', 'reversal_score']]

        raw_m = pd.to_numeric(res_df['oversold_metric'], errors='coerce').fillna(0.0)
        # Absolute oversold score via sigmoid centered at 0.0 (neutral)
        abs_score = 1.0 / (1.0 + np.exp(-raw_m * 3.0))
        if len(res_df) >= 5:
            pct_rank = raw_m.rank(pct=True, ascending=True)
            final_score = 0.70 * abs_score + 0.30 * pct_rank
            # Top-Tier Reversal Booster for high-conviction oversold turnaround winners
            final_score = np.where(final_score >= 0.90, (final_score * 1.10).clip(0.02, 0.98), final_score)
        else:
            final_score = abs_score

        res_df['reversal_score'] = pd.to_numeric(pd.Series(final_score, index=res_df.index), errors='coerce').fillna(0.50).clip(0.02, 0.98)
        return res_df[['symbol', 'reversal_score']]

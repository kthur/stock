import logging
import pandas as pd
import numpy as np
from typing import Dict, Any
from .base_strategy import BaseStrategyEngine, make_score_dataframe

logger = logging.getLogger(__name__)

from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="latr_factor",
        display_name="Liquidity-Adjusted Tail Risk",
        score_column="latr_score",
        category="factor",
        output_file="latr_predictions.txt",
        default_regime_weights={
            "BEAR": 0.04, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class LATRFactorEngine(BaseStrategyEngine):
    """
    17. Liquidity-Adjusted Tail Risk Premium (LATR) Strategy Engine

    52주 고점 대비 낙폭(DD) + 호가/거래량 유동성 + 하방 꼬리위험 프리미엄 조합.
    - 투매(Panic Selling) 후 극단적 반등(Extreme Bounce) 신호 포착
    """
    def __init__(self, lookback_window: int = 252, target_drawdown: float = 0.35):
        self.lookback_window = lookback_window
        self.target_drawdown = target_drawdown

    def compute_scores(self, prices_dict: Dict[str, pd.DataFrame], fundamentals_dict=None, indicators_df=None, **kwargs) -> Any:
        """
        Computes LATR factor scores in [0.0, 1.0] for all symbols.
        Returns ScoreDataFrame with columns ['symbol', 'latr_score'] supporting dict indexing.
        """
        scores = {}
        if not prices_dict or not isinstance(prices_dict, dict):
            return make_score_dataframe({}, 'latr_score')

        # Extract real-time or indicator USD/KRW rate with safe fallback
        usdkrw_rate = 1350.0
        if indicators_df is not None:
            if isinstance(indicators_df, dict) and 'usdkrw' in indicators_df:
                try:
                    usdkrw_rate = float(indicators_df['usdkrw'])
                except (ValueError, TypeError):
                    pass
            elif isinstance(indicators_df, pd.DataFrame) and 'usdkrw' in indicators_df.columns and not indicators_df['usdkrw'].dropna().empty:
                try:
                    usdkrw_rate = float(indicators_df['usdkrw'].dropna().iloc[-1])
                except (ValueError, TypeError):
                    pass
        elif 'usdkrw' in kwargs:
            try:
                usdkrw_rate = float(kwargs['usdkrw'])
            except (ValueError, TypeError):
                pass
        if usdkrw_rate <= 500.0 or usdkrw_rate >= 3000.0 or np.isnan(usdkrw_rate):
            usdkrw_rate = 1350.0

        for sym, df in prices_dict.items():
            try:
                if df is None or df.empty or len(df) < 5:
                    scores[sym] = 0.5
                    continue

                col_c = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
                col_v = 'volume' if 'volume' in df.columns else ('Volume' if 'Volume' in df.columns else None)
                if not col_c or not col_v:
                    scores[sym] = 0.5
                    continue

                close = df[col_c].dropna()
                vol = df[col_v].dropna()
                if len(close) < 5 or len(vol) < 5:
                    scores[sym] = 0.5
                    continue

                # 1. 52-week Drawdown
                h52 = close.tail(self.lookback_window).max()
                cp = close.iloc[-1]
                dd_pct = (h52 - cp) / (h52 + 1e-8) if h52 > 0 else 0.0

                # 2. Volume Surge Ratio
                vol_20m = vol.tail(20).mean()
                vol_surge = (vol.iloc[-1] / vol_20m) if vol_20m > 0 else 1.0

                # 3. Tail Risk (R6-6 Fix: Cornish-Fisher 5th percentile VaR over 60D incorporating skewness & kurtosis)
                daily_rets = close.pct_change().dropna()
                if len(daily_rets) >= 20:
                    sub_rets = daily_rets.tail(60).values
                    mu = float(np.mean(sub_rets))
                    sigma = float(np.std(sub_rets, ddof=1))
                    if sigma > 1e-6 and len(sub_rets) >= 10:
                        skewness = float(np.mean(((sub_rets - mu) / sigma) ** 3))
                        kurt = float(np.mean(((sub_rets - mu) / sigma) ** 4)) - 3.0
                        z_alpha = -1.6448536269514722  # 5th percentile standard normal
                        z_cf = (
                            z_alpha
                            + (z_alpha**2 - 1.0) * skewness / 6.0
                            + (z_alpha**3 - 3.0 * z_alpha) * kurt / 24.0
                            - (2.0 * z_alpha**3 - 5.0 * z_alpha) * (skewness**2) / 36.0
                        )
                        # Barton-Dennis (1952) domain of validity for monotonic Cornish-Fisher quantiles
                        if abs(skewness) > 1.5 or kurt > 4.0 or z_cf >= 0.0 or not np.isfinite(z_cf):
                            tail_risk = float(np.percentile(sub_rets, 5))
                        else:
                            tail_risk = mu + z_cf * sigma
                    else:
                        tail_risk = float(np.percentile(sub_rets, 5))
                else:
                    tail_risk = -0.03
                tail_penalty = float(min(2.0, max(0.0, -tail_risk) / 0.035))

                # 4. Amihud Illiquidity Ratio (|ret| / (Volume * Price)) with cross-market USD normalization
                is_kr = str(sym).isdigit() or str(sym).endswith(('.KS', '.KQ'))
                fx_norm = usdkrw_rate if is_kr else 1.0
                turnover_usd = (vol.tail(20) * close.tail(20) / fx_norm).replace(0, 1.0)
                amihud_illiq = float((daily_rets.abs().tail(20) / turnover_usd).mean() * 1e6)

                # Monotonic drawdown score for panic bounce opportunity (scaled by target drawdown)
                dd_score = float(np.clip(dd_pct / max(0.01, self.target_drawdown), 0.0, 1.25))

                # Multi-Tier Capitulation Climax Bounce & Falling Knife Defense:
                # 1. Super Capitulation: Panic drawdown meets massive institutional liquidity absorption
                if vol_surge >= 3.2 and dd_score >= 0.90:
                    panic_bounce_bonus = 0.28  # Super Capitulation Climax Rebound
                elif vol_surge >= 2.2 and dd_score >= 0.75:
                    panic_bounce_bonus = 0.16  # Standard Panic Bounce
                else:
                    panic_bounce_bonus = 0.0

                # 2. Falling Knife Penalty: Deep drawdown with drying volume and extreme tail risk
                falling_knife_penalty = 0.20 if (dd_score >= 0.80 and vol_surge < 0.80 and tail_penalty >= 1.2) else 0.0

                # LATR raw score: Optimal panic drawdown score + volume surge - tail risk penalty - illiquidity penalty + capitulation bonus - falling knife penalty
                raw_latr = (dd_score * 0.40) + (min(vol_surge, 3.2) * 0.35) - (tail_penalty * 0.15) - (min(amihud_illiq, 2.0) * 0.10) + panic_bounce_bonus - falling_knife_penalty
                scores[sym] = float(np.clip(raw_latr, -5.0, 5.0)) if np.isfinite(raw_latr) else 0.5
            except Exception as e:
                logger.warning(f"[LATR FACTOR] Error computing score for {sym}: {e}")
                scores[sym] = 0.5

        if not scores:
            return make_score_dataframe({}, 'latr_score')

        vals = np.array([v for v in scores.values() if np.isfinite(v)])
        if len(vals) == 0:
            return make_score_dataframe({k: 0.5 for k in scores.keys()}, 'latr_score')
        p1, p99 = float(np.percentile(vals, 1)), float(np.percentile(vals, 99))
        if p99 <= p1:
            return make_score_dataframe({k: 0.5 for k in scores.keys()}, 'latr_score')
        range_v = p99 - p1

        norm_scores = {}
        for k, v in scores.items():
            if np.isfinite(v):
                base_s = float(np.clip((v - p1) / range_v, 0.0, 1.0))
                # Multi-Tier LATR Capitulation Turnaround Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                if base_s >= 0.95:
                    boosted_s = base_s * 1.15
                elif base_s >= 0.85:
                    boosted_s = base_s * 1.10
                else:
                    boosted_s = base_s
                norm_scores[k] = float(np.clip(boosted_s, 0.05, 0.98))
            else:
                norm_scores[k] = 0.50
        return make_score_dataframe(norm_scores, 'latr_score')

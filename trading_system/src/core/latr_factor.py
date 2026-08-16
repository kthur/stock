import logging
import pandas as pd
import numpy as np
from typing import Dict
from .base_strategy import BaseStrategyEngine

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

    def compute_scores(self, prices_dict: Dict[str, pd.DataFrame], fundamentals_dict=None, indicators_df=None, **kwargs) -> Dict[str, float]:
        """
        Computes LATR factor scores in [0.0, 1.0] for all symbols.
        """
        scores = {}
        for sym, df in prices_dict.items():
            try:
                if df is None or len(df) < 20:
                    scores[sym] = 0.5
                    continue

                c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                v_col = 'Volume' if 'Volume' in df.columns else ('volume' if 'volume' in df.columns else None)
                if not c_col or not v_col:
                    scores[sym] = 0.5
                    continue

                close = df[c_col].dropna()
                vol = df[v_col].dropna()
                if len(close) < 20 or len(vol) < 20:
                    scores[sym] = 0.5
                    continue

                # 1. 52-week Drawdown
                h52 = close.tail(self.lookback_window).max()
                cp = close.iloc[-1]
                dd_pct = (h52 - cp) / (h52 + 1e-8) if h52 > 0 else 0.0

                # 2. Volume Surge Ratio
                vol_20m = vol.tail(20).mean()
                vol_surge = (vol.iloc[-1] / vol_20m) if vol_20m > 0 else 1.0

                # 3. Tail Risk (5th percentile daily return over 60D)
                daily_rets = close.pct_change().dropna()
                tail_risk = float(np.percentile(daily_rets.tail(60), 5)) if len(daily_rets) >= 20 else -0.03

                # 4. Amihud Illiquidity Ratio (|ret| / (Volume * Price))
                dollar_vol = (vol.tail(20) * close.tail(20)).replace(0, 1.0)
                amihud_illiq = float((daily_rets.abs().tail(20) / dollar_vol).mean() * 1e6)

                # Monotonic drawdown score for panic bounce opportunity (scaled by target drawdown)
                dd_score = float(np.clip(dd_pct / max(0.01, self.target_drawdown), 0.0, 1.25))

                # Panic volume surge bounce bonus (Volume surge >= 2.5 on panic drawdown)
                panic_bounce_bonus = 0.12 if (vol_surge >= 2.5 and dd_score >= 0.80) else 0.0

                # LATR raw score: Optimal panic drawdown score + volume surge - tail risk penalty - illiquidity penalty
                latr_score = (dd_score * 0.40) + (min(vol_surge, 3.0) * 0.35) - (abs(tail_risk) * 0.15) - (min(amihud_illiq, 2.0) * 0.10) + panic_bounce_bonus
                scores[sym] = float(latr_score)
            except Exception as e:
                logger.warning(f"[LATR FACTOR] Error computing score for {sym}: {e}")
                scores[sym] = 0.5


        if not scores:
            return {}

        vals = np.array(list(scores.values()))
        p1, p99 = np.percentile(vals, 1), np.percentile(vals, 99)
        if p99 == p1:
            return {k: 0.5 for k in scores.keys()}
        range_v = p99 - p1

        return {k: float(np.clip((v - p1) / range_v, 0.0, 1.0)) for k, v in scores.items()}

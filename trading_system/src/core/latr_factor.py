import logging
import pandas as pd
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)

class LATRFactorEngine:
    """
    17. Liquidity-Adjusted Tail Risk Premium (LATR) Strategy Engine
    
    52주 고점 대비 낙폭(DD) + 호가/거래량 유동성 + 하방 꼬리위험 프리미엄 조합.
    - 투매(Panic Selling) 후 극단적 반등(Extreme Bounce) 신호 포착
    """
    def __init__(self, lookback_window: int = 252):
        self.lookback_window = lookback_window

    def compute_scores(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Computes LATR factor scores in [0.0, 1.0] for all symbols.
        """
        scores = {}
        for sym, df in prices_dict.items():
            try:
                if df.empty:
                    scores[sym] = 0.5
                    continue

                close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                vol = df['Volume'].iloc[:, 0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume']

                if len(close) < 20:
                    scores[sym] = 0.5
                    continue

                # 1. 52-week Drawdown (Max - Current) / Max
                window = min(len(close), self.lookback_window)
                high_52w = float(close.tail(window).max())
                curr_price = float(close.iloc[-1])
                dd_pct = (high_52w - curr_price) / high_52w if high_52w > 0 else 0.0

                # 2. Volume Spike / Liquidity Surge (5d vol / 20d vol)
                vol_5d = float(vol.tail(5).mean())
                vol_20d = float(vol.tail(20).mean())
                vol_surge = vol_5d / (vol_20d + 1e-5)

                # 3. Tail Risk Premium (Quantile 5% lower return ratio)
                daily_rets = close.pct_change().tail(window).dropna()
                tail_risk = float(np.percentile(daily_rets, 5)) if len(daily_rets) >= 20 else -0.03

                # H-2 Fix: Gaussian scoring centered at optimal 35% drawdown for panic bounce opportunity
                # Extreme 90% distress crash is penalized, while zero drawdown receives neutral score.
                dd_score = float(np.exp(-((dd_pct - 0.35) ** 2) / (2.0 * (0.15 ** 2))))

                # LATR raw score: Optimal panic drawdown score + volume surge - tail risk penalty
                latr_score = (dd_score * 0.4) + (min(vol_surge, 3.0) * 0.4) - (abs(tail_risk) * 0.2)
                scores[sym] = float(latr_score)
            except Exception:
                scores[sym] = 0.5

        if not scores:
            return {}

        vals = np.array(list(scores.values()))
        min_v, max_v = np.min(vals), np.max(vals)
        range_v = max_v - min_v if max_v != min_v else 1.0

        return {k: float(np.clip((v - min_v) / range_v, 0.0, 1.0)) for k, v in scores.items()}

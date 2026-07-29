import logging
import pandas as pd
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CARDFactorEngine:
    """
    16. Cross-Asset Regime Divergence (CARD) Strategy Engine
    
    주식 - 원자재(유가/금) - 환율(USD/KRW) - 금리 간 괴리율 역발상 매수 점수 산출.
    - 거시 지표 대비 과도하게 하락한 수혜 섹터/종목 역발상 스코어링
    """
    def __init__(self):
        pass

    def compute_scores(self, indicator_df: pd.DataFrame, prices_dict: Dict[str, pd.DataFrame], sector_map: Dict[str, str] = None) -> Dict[str, float]:
        """
        Computes CARD factor scores in [0.0, 1.0] for all symbols.
        """
        if indicator_df.empty or not prices_dict:
            return {}

        # Extract latest macro indicators
        usdkrw_chg = float(indicator_df['usdkrw_change'].iloc[-1]) if 'usdkrw_change' in indicator_df.columns else 0.0
        wti_chg = float(indicator_df['wti_change'].iloc[-1]) if 'wti_change' in indicator_df.columns else 0.0
        vix_val = float(indicator_df['vix_change'].iloc[-1]) if 'vix_change' in indicator_df.columns else 0.0

        scores = {}
        sector_map = sector_map or {}

        for sym, df in prices_dict.items():
            try:
                if df.empty:
                    scores[sym] = 0.5
                    continue

                close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                if len(close) < 10:
                    scores[sym] = 0.5
                    continue

                stock_ret = float((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100)
                sec = sector_map.get(sym, 'Market')

                # Divergence calculation: Stock return vs Macro shock
                # If macro is crashing (USDKRW up, WTI up, VIX up) but stock was oversold beyond macro impact
                macro_impact = (usdkrw_chg * 0.3) + (wti_chg * 0.3) + (vix_val * 0.4)
                divergence = stock_ret - macro_impact

                # Mean reversion opportunity score (lower divergence = higher opportunity)
                card_score = 1.0 / (1.0 + np.exp(divergence * 0.1))
                scores[sym] = float(card_score)
            except Exception:
                scores[sym] = 0.5

        return scores

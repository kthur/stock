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

        # Extract latest macro indicators with safe scaling
        usdkrw_chg = float(indicator_df['usdkrw_change'].iloc[-1]) if 'usdkrw_change' in indicator_df.columns else 0.0
        wti_chg = float(indicator_df['wti_change'].iloc[-1]) if 'wti_change' in indicator_df.columns else 0.0
        vix_val = float(indicator_df['vix_change'].iloc[-1]) if 'vix_change' in indicator_df.columns else 0.0
        
        # M-3 Fix: If vix_val is an absolute index level (e.g. > 5.0), scale to percentage change proxy
        if abs(vix_val) > 5.0:
            vix_val = (vix_val - 20.0) / 20.0

        scores = {}
        sector_map = sector_map or {}

        # Basic Sector Beta sensitivity factors to macro shock
        sector_beta = {
            'Information Technology': 1.2,
            'Financials': 0.8,
            'Health Care': 0.6,
            'Consumer Discretionary': 1.1,
            'Industrials': 1.0,
            'Materials': 1.1,
            'Energy': 1.2,
            'Communication Services': 0.9,
            'Consumer Staples': 0.5,
            'Utilities': 0.4,
            'Real Estate': 0.7,
        }

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
                beta = sector_beta.get(sec, 1.0)

                # Divergence calculation: Stock return vs Sector-Beta weighted Macro shock
                macro_impact = ((usdkrw_chg * 0.3) + (wti_chg * 0.3) + (vix_val * 0.4)) * beta * 10.0
                divergence = stock_ret - macro_impact

                # Mean reversion opportunity score
                card_score = 1.0 / (1.0 + np.exp(divergence * 0.1))
                scores[sym] = float(card_score)
            except Exception:
                scores[sym] = 0.5

        return scores

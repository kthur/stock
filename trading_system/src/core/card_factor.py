import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CARDFactorEngine:
    """
    16. Cross-Asset Regime Divergence (CARD) Strategy Engine

    주식 - 원자재(유가/금) - 환율(USD/KRW) - 금리 간 괴리율 역발상 매수 점수 산출.
    - 거시 지표 대비 과도하게 하락한 수혜 섹터/종목 역발상 스코어링
    """
    def __init__(self):
        pass

    def compute_scores(self, indicator_df: Any, prices_dict: Dict[str, pd.DataFrame], sector_map: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Computes CARD factor scores in [0.0, 1.0] for all symbols.
        Accepts indicator_df as pd.DataFrame or Dict[str, float].
        """
        if indicator_df is None or not prices_dict:
            return {}
        if isinstance(indicator_df, pd.DataFrame) and indicator_df.empty:
            return {}

        def _safe_macro(col):
            if isinstance(indicator_df, dict):
                v = float(indicator_df.get(col, 0.0))
                return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            elif isinstance(indicator_df, pd.DataFrame):
                if col in indicator_df.columns and not indicator_df[col].dropna().empty:
                    v = float(indicator_df[col].dropna().iloc[-1])
                    return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            return 0.0

        # Extract latest macro indicators with safe scaling
        usdkrw_chg = _safe_macro('usdkrw_change')
        wti_chg = _safe_macro('wti_change')
        vix_val = _safe_macro('vix_change')

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
                if df is None or df.empty:
                    scores[sym] = 0.5
                    continue

                close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                close = close.dropna()
                if len(close) < 5 or float(close.iloc[-5]) <= 0:
                    scores[sym] = 0.5
                    continue

                c_last = float(close.iloc[-1])
                c_prev = float(close.iloc[-5])
                if np.isnan(c_last) or np.isnan(c_prev) or c_prev <= 0:
                    scores[sym] = 0.5
                    continue

                stock_ret = float((c_last - c_prev) / c_prev * 100)
                if np.isnan(stock_ret) or np.isinf(stock_ret):
                    scores[sym] = 0.5
                    continue

                sec = sector_map.get(sym, 'Market')
                beta = sector_beta.get(sec, 1.0)

                # Divergence calculation: Stock return vs Sector-Beta weighted Macro shock
                macro_impact = ((usdkrw_chg * 0.3) + (wti_chg * 0.3) + (vix_val * 0.4)) * beta * 10.0
                divergence = stock_ret - macro_impact

                # Mean reversion opportunity score
                card_score = 1.0 / (1.0 + np.exp(divergence * 0.1))
                if np.isnan(card_score) or np.isinf(card_score):
                    card_score = 0.5
                scores[sym] = float(card_score)
            except Exception:
                scores[sym] = 0.5

        return scores


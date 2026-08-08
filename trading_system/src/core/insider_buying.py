"""
src/core/insider_buying.py
Corporate Insider Net Buying Anomaly Strategy Engine (Strategy #29).

Parses OpenDART (Korea) and SEC Form 4 (US) insider disclosure filings:
  - Executive / Board Member open market share purchases
  - Controlling Shareholder equity accumulation
  - Net Insider Purchasing Score [0.0, 1.0]
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class InsiderBuyingEngine:
    """
    Strategy #29: Corporate Insider Net Buying Anomaly Engine.
    """

    def __init__(self, config=None):
        self.config = config

    def compute_insider_buying_scores(
        self,
        symbols: List[str],
        insider_filings: Optional[List[Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Computes Insider Net Buying score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'insider_buying_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'insider_buying_score'])

        # Base neutral score
        scores_map = {sym: 0.50 for sym in symbols}

        if insider_filings:
            for item in insider_filings:
                stock_code = str(item.get('stock_code', '')).strip().zfill(6) if item.get('stock_code') else ''
                report_nm = str(item.get('report_nm', ''))
                insider_role = str(item.get('insider_role', 'EXECUTIVE'))
                trans_type = str(item.get('trans_type', 'BUY')).upper()

                for sym in symbols:
                    sym_clean = sym.split('.')[0].zfill(6)
                    matched = (stock_code and stock_code == sym_clean) or (sym in report_nm)
                    
                    if matched:
                        if trans_type in ['BUY', 'PURCHASE', '취득', '매입']:
                            boost = 0.35 if insider_role in ['CEO', 'CHAIRMAN', '대표이사'] else 0.20
                            scores_map[sym] = float(np.clip(scores_map[sym] + boost, 0.0, 1.0))
                            logger.info(f"[INSIDER BUYING ENGINE] Insider buy detected for {sym}: {report_nm} (Score -> {scores_map[sym]:.2f})")
                        elif trans_type in ['SELL', 'DISPOSAL', '처분', '매각']:
                            penalty = 0.25
                            scores_map[sym] = float(np.clip(scores_map[sym] - penalty, 0.0, 1.0))

        results = [{'symbol': k, 'insider_buying_score': float(v)} for k, v in scores_map.items()]
        return pd.DataFrame(results)

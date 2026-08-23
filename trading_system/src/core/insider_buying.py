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

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="insider_buying",
        display_name="Insider Buying Catalyst",
        score_column="insider_buying_score",
        category="catalyst",
        output_file="insider_buying_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class InsiderBuyingEngine(BaseStrategyEngine):
    """
    Strategy #29: Corporate Insider Net Buying Anomaly Engine.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = kwargs.get("symbols")
        if not symbols and isinstance(prices_dict, dict):
            symbols = list(prices_dict.keys())
        elif not symbols and isinstance(prices_dict, (list, tuple, set)):
            symbols = list(prices_dict)
        symbols = symbols or []
        filings = kwargs.get("insider_filings") or kwargs.get("dart_disclosures") or kwargs.get("disclosures") or kwargs.get("filings")
        return self.compute_insider_buying_scores(symbols=symbols, insider_filings=filings, **kwargs)

    def calculate_scores(self, symbols: List[str], prices_dict: Optional[Dict[str, pd.DataFrame]] = None, **kwargs: Any) -> pd.DataFrame:
        filings = kwargs.get("insider_filings") or kwargs.get("dart_disclosures") or kwargs.get("disclosures") or kwargs.get("filings")
        return self.compute_insider_buying_scores(symbols=symbols, insider_filings=filings, **kwargs)

    def compute_insider_buying_scores(
        self,
        symbols: List[str],
        insider_filings: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        if insider_filings is None:
            insider_filings = kwargs.get("dart_disclosures") or kwargs.get("disclosures") or kwargs.get("filings")
        """
        Computes Insider Net Buying score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'insider_buying_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'insider_buying_score'])

        # Default to NaN for symbols without insider filings
        scores_map = {sym: np.nan for sym in symbols}

        if insider_filings:
            # Pre-index filings by stock code/symbol for O(M) processing
            filings_by_code: Dict[str, List[Dict[str, Any]]] = {}
            for item in insider_filings:
                code_raw = str(item.get('stock_code', '')).strip()
                if code_raw:
                    code_clean = code_raw.zfill(6) if code_raw.isdigit() else code_raw
                    filings_by_code.setdefault(code_clean, []).append(item)
                    if code_clean != code_raw:
                        filings_by_code.setdefault(code_raw, []).append(item)

            buy_keywords = {'BUY', 'PURCHASE', '취득', '매입', '장내매수', '장외매수', '신규취득', '주식매수'}
            sell_keywords = {'SELL', 'DISPOSAL', '처분', '매각', '장내매도', '장외매도', '주식매도'}
            high_level_roles = {'CEO', 'CHAIRMAN', '대표이사', '최대주주', '부회장'}

            for sym in symbols:
                sym_raw = sym.split('.')[0]
                sym_clean = sym_raw.zfill(6) if sym_raw.isdigit() else sym_raw

                matching_items = filings_by_code.get(sym_clean)
                if matching_items is None and sym_raw != sym_clean:
                    matching_items = filings_by_code.get(sym_raw)
                if not matching_items:
                    continue

                cur_score = 0.50
                for item in matching_items:
                    report_nm = str(item.get('report_nm', ''))
                    insider_role = str(item.get('insider_role', 'EXECUTIVE')).upper()
                    raw_type = str(item.get('trans_type', '')).upper().strip()
                    combined_role_text = f"{insider_role} {report_nm}"

                    # Explicit transaction classification: do not default generic informational filings to BUY
                    if raw_type in buy_keywords or any(k in report_nm for k in ['장내매수', '장내취득', '신규매수', '주식매입', '자사주매입', '지분매수', '지분취득']):
                        boost = 0.35 if any(role in combined_role_text for role in high_level_roles) else 0.20
                        # Accumulate multiple insider buys up to 0.98 cap
                        cur_score = float(np.clip(cur_score + boost, 0.0, 0.98))
                        logger.info(f"[INSIDER BUYING ENGINE] Insider buy detected for {sym}: {report_nm} (Score -> {cur_score:.2f})")
                    elif raw_type in sell_keywords or any(k in report_nm for k in ['장내매도', '장내처분', '지분매각', '지분매도', '주식매도', '블록딜']):
                        penalty = 0.25
                        cur_score = float(np.clip(cur_score - penalty, 0.05, 1.0))

                scores_map[sym] = cur_score

        results = [{'symbol': k, 'insider_buying_score': float(v) if pd.notna(v) else np.nan} for k, v in scores_map.items()]
        return pd.DataFrame(results)

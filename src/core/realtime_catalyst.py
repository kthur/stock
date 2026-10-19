# -*- coding: utf-8 -*-
"""
RealTimeCatalystEngine: Real-time SEC EDGAR 8-K and KRX DART Filing Event Parser & Catalyst Sentiment Scorer.
Quantifies material corporate events: earnings surprise, buybacks, major contracts, clinical trials, and capital changes.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


class RealTimeCatalystEngine:
    """
    Real-Time Corporate Event & Disclosure Catalyst Engine.
    Scores material 8-K and DART filings with exact 10-day half-life decay.
    """

    # Keyword rules with positive/negative impact magnitudes
    KRX_EVENT_RULES = {
        '자사주 소각': +0.40,
        '자기주식취득': +0.25,
        '무상증자': +0.35,
        '단일판매ㆍ공급계약체결': +0.30,
        '영업실적등에대한전망': +0.15,
        '풍문또는보도에대한해명': +0.05,
        '유상증자결정(제3자배정)': +0.10,
        '유상증자결정(주주배정)': -0.35,
        '전환사채발행': -0.15,
        '신주인수권부사채발행': -0.15,
        '관리종목지정': -0.50,
        '횡령ㆍ배임혐의발생': -0.60,
        '불성실공시법인지정': -0.30,
        '감사의견거절': -0.80,
    }

    SEC_EVENT_RULES = {
        'ITEM 2.02': +0.20,  # Results of Operations and Financial Condition
        'ITEM 1.01': +0.15,  # Entry into a Material Definitive Agreement
        'ITEM 3.02': -0.15,  # Unregistered Sales of Equity Securities (Dilution)
        'ITEM 4.02': -0.40,  # Non-Reliance on Previously Issued Financial Statements
        'ITEM 5.02': -0.05,  # Departure of Directors or Certain Officers
        'ITEM 8.01': +0.05,  # Other Events
        'MERGER': +0.30,
        'ACQUISITION': +0.20,
        'BUYBACK': +0.30,
        'SHARE REPURCHASE': +0.30,
        'DIVIDEND INCREASE': +0.25,
        'BANKRUPTCY': -0.80,
        'RESTATEMENT': -0.40,
        'FDA APPROVAL': +0.50,
        'CLINICAL TRIAL SUCCESS': +0.45,
        'CLINICAL TRIAL FAILURE': -0.50,
    }

    def __init__(self, half_life_days: float = 10.0):
        self.half_life_days = half_life_days
        self._decay_lambda = np.log(2.0) / max(half_life_days, 1.0)

    def score_event_text(self, text: str, market: str = 'KOSPI') -> float:
        """
        Scores raw disclosure title or body text against event rules.
        Returns: raw impact score [-1.0, +1.0]
        """
        if not text or not isinstance(text, str):
            return 0.0

        text_upper = text.upper()
        raw_score = 0.0

        if market.upper() in ('KOSPI', 'KOSDAQ', 'KRX'):
            for kw, impact in self.KRX_EVENT_RULES.items():
                if kw in text:
                    raw_score += impact
        else:
            for kw, impact in self.SEC_EVENT_RULES.items():
                if kw in text_upper:
                    raw_score += impact

        return float(np.clip(raw_score, -1.0, 1.0))

    def compute_decayed_catalyst_scores(self,
                                        filing_events: List[Dict[str, Any]],
                                        current_date: Optional[datetime] = None) -> Dict[str, float]:
        """
        filing_events: List of dicts with keys:
            - 'symbol': str
            - 'market': str (e.g. 'KOSPI', 'SP500')
            - 'title': str
            - 'date': str or datetime
            - 'score': Optional[float]
        Returns: {symbol: catalyst_score [0.0, 1.0]}
        """
        if current_date is None:
            current_date = datetime.now()

        symbol_accumulators: Dict[str, float] = {}

        for ev in filing_events:
            sym = str(ev.get('symbol', '')).strip().upper()
            if not sym:
                continue

            mkt = str(ev.get('market', 'SP500')).upper()
            ev_date_val = ev.get('date')
            if isinstance(ev_date_val, str):
                try:
                    ev_date = datetime.strptime(ev_date_val[:10], '%Y-%m-%d')
                except Exception:
                    ev_date = current_date
            elif isinstance(ev_date_val, datetime):
                ev_date = ev_date_val
            else:
                ev_date = current_date

            days_elapsed = max(0.0, (current_date - ev_date).total_seconds() / 86400.0)
            decay_factor = float(np.exp(-days_elapsed * self._decay_lambda))

            if 'score' in ev and ev['score'] is not None:
                base_score = float(ev['score'])
            else:
                base_score = self.score_event_text(str(ev.get('title', '')), market=mkt)

            decayed_impact = base_score * decay_factor
            symbol_accumulators[sym] = symbol_accumulators.get(sym, 0.0) + decayed_impact

        # Map accumulated impact to [0.0, 1.0] sigmoid score
        final_scores: Dict[str, float] = {}
        for sym, acc_impact in symbol_accumulators.items():
            # Centered at 0.50, sigmoid scale 5.0
            sigmoid_score = 1.0 / (1.0 + np.exp(-5.0 * acc_impact))
            final_scores[sym] = float(np.clip(sigmoid_score, 0.01, 0.99))

        return final_scores

"""
src/core/event_driven.py
Event-Driven Momentum Engine.
Parses corporate filings (OpenDART for KRX, disclosures) and calculates event-driven
momentum scores based on disclosure types (earnings surprises, stock splits, buybacks, rights offerings).
"""
import logging
import urllib.request
import json
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class EventDrivenEngine:
    """
    Event-Driven Strategy Engine.
    Evaluates corporate filings / disclosure events and assigns directional scores [0.0, 1.0].
    """

    EVENT_WEIGHTS = {
        '01': 0.85,   # 사업보고서 / 실적공시 (Positive / Earnings surprise candidate)
        '02': 0.90,   # 주식분할 / 주식배당 (Strong positive catalyst)
        '03': 0.80,   # 자기주식 취득 (Buyback - Positive)
        '04': 0.25,   # 유상증자 / CB·BW 발행 (Dilution risk - Negative)
        '05': 0.60,   # 대표이사 변경 / 경영권 분쟁 (Volatile / Mild catalyst)
    }

    def __init__(self, dart_api_key: str = ""):
        self.dart_api_key = dart_api_key.strip()

    def fetch_recent_dart_filings(self, bgn_de: str = "", end_de: str = "") -> List[Dict[str, Any]]:
        """
        Fetches recent public disclosures from OpenDART API list endpoint.
        Returns list of disclosure records.
        """
        if not self.dart_api_key:
            logger.debug("DART API key not configured; skipping DART fetch.")
            return []

        try:
            url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.dart_api_key}&page_count=100"
            if bgn_de:
                url += f"&bgn_de={bgn_de}"
            if end_de:
                url += f"&end_de={end_de}"

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == '000':
                    res = data.get('list', [])
                    return res if isinstance(res, list) else []
        except Exception as e:
            logger.debug(f"OpenDART fetch failed: {e}")

        return []

    def compute_event_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        filings: Optional[List[Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Computes Event-Driven momentum scores per symbol.
        Returns DataFrame with ['symbol', 'event_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'event_score'])

        # Initialize neutral score 0.5
        scores_map = {sym: 0.5 for sym in symbols}

        # Process DART filings if provided or fetched
        eff_filings = filings if filings is not None else self.fetch_recent_dart_filings()
        if eff_filings:
            for item in eff_filings:
                corp_code = item.get('stock_code', '') or item.get('corp_code', '')
                report_nm = item.get('report_nm', '')
                pblntf_ty = item.get('pblntf_ty', '')

                # Match corp_code/stock_code with symbol list
                for sym in symbols:
                    sym_clean = sym.split('.')[0]
                    if corp_code and (corp_code in sym or sym_clean in corp_code):
                        weight = self.EVENT_WEIGHTS.get(pblntf_ty, 0.5)
                        # Text keyword adjustments
                        if '유상증자' in report_nm or '전환사채' in report_nm:
                            weight = 0.25
                        elif '자기주식' in report_nm or '자사주' in report_nm:
                            weight = 0.85
                        elif '무상증자' in report_nm or '주식분할' in report_nm:
                            weight = 0.90
                        elif '영업이익' in report_nm or '실적' in report_nm:
                            weight = 0.75

                        scores_map[sym] = max(scores_map[sym], weight)

        # Volatility / Volume Event Boost from price data
        if prices_dict:
            for sym, df in prices_dict.items():
                if sym not in scores_map or df is None or len(df) < 5:
                    continue
                try:
                    vol = df['Volume']
                    if isinstance(vol, pd.DataFrame):
                        vol = vol.iloc[:, 0]
                    vol = vol.dropna()
                    if len(vol) >= 5:
                        avg_vol = float(vol.iloc[-5:-1].mean())
                        cur_vol = float(vol.iloc[-1])
                        if avg_vol > 0 and cur_vol / avg_vol >= 3.0:
                            # 3x volume surge disclosure catalyst boost
                            scores_map[sym] = float(np.clip(scores_map[sym] + 0.15, 0.0, 1.0))
                except Exception:
                    pass

        res_df = pd.DataFrame([{'symbol': k, 'event_score': float(v)} for k, v in scores_map.items()])
        return res_df

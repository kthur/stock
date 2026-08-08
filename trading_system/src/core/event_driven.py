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
        'A': 0.75,   # 정기공시 (사업/반기/분기보고서)
        'B': 0.70,   # 주요사항보고서 (주요경영사항)
        'C': 0.35,   # 발행공시 (유상증자, CB/BW 발행 등)
        'D': 0.60,   # 지분공시 (임원/주요주주 소유주식)
        'E': 0.80,   # 기타공시 (자사주 취득/처분)
        'F': 0.50,   # 외부감사인 관련
        # Legacy / Numeric code fallbacks
        '01': 0.75,
        '02': 0.85,
        '03': 0.80,
        '04': 0.35,
        '05': 0.60,
    }

    def __init__(self, config=None, dart_api_key: str = ""):
        self.config = config
        self.dart_api_key = dart_api_key.strip()
        if not self.dart_api_key and config is not None:
            self.dart_api_key = getattr(config, 'dart_api_key', '').strip()

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
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == '000':
                    res = data.get('list', [])
                    return res if isinstance(res, list) else []
        except Exception as e:
            logger.debug(f"OpenDART fetch failed: {e}")

        return []

    def incorporate_filing_sentiment(
        self,
        symbol: str,
        base_catalyst_score: float,
        sentiment_metrics: Optional[Any] = None
    ) -> float:
        """
        Adjusts base event score using filing sentiment intensity multiplier (0.5x to 1.5x).

        Multiplier formula:
          intensity_delta = (composite_sentiment_score - 0.5) * 2.0 * confidence_score  # [-1.0, +1.0]
          multiplier = 1.0 + np.clip(intensity_delta * 0.5, -0.5, 0.5)                   # [0.5, 1.5]
          adjusted_score = np.clip(base_catalyst_score * multiplier, 0.0, 1.0)
        """
        if sentiment_metrics is None:
            return float(base_catalyst_score)

        if isinstance(sentiment_metrics, dict):
            comp_score = float(sentiment_metrics.get('composite_sentiment_score', 0.5))
            conf_score = float(sentiment_metrics.get('confidence_score', 1.0))
        else:
            comp_score = float(getattr(sentiment_metrics, 'composite_sentiment_score', 0.5))
            conf_score = float(getattr(sentiment_metrics, 'confidence_score', 1.0))

        intensity_delta = (comp_score - 0.5) * 2.0 * conf_score
        multiplier = 1.0 + float(np.clip(intensity_delta * 0.5, -0.5, 0.5))

        return float(np.clip(base_catalyst_score * multiplier, 0.0, 1.0))

    def compute_event_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        filings: Optional[List[Dict[str, Any]]] = None,
        price_db=None,
        sentiment_map: Optional[Dict[str, Any]] = None
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
                stock_code = str(item.get('stock_code', '')).strip().zfill(6) if item.get('stock_code') else ''
                corp_code = str(item.get('corp_code', '')).strip()
                report_nm = item.get('report_nm', '')
                pblntf_ty = item.get('pblntf_ty', '')

                # Match stock_code or corp_code with symbol list
                for sym in symbols:
                    sym_code = sym.split('.')[0]
                    sym_clean = sym_code.zfill(6) if sym_code.isdigit() else sym
                    matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code.endswith(sym_clean) or corp_code == sym))
                    if matched:
                        weight = self.EVENT_WEIGHTS.get(pblntf_ty, 0.5)
                        # Text keyword adjustments with clear directionality
                        if '유상증자' in report_nm or '전환사채' in report_nm or '신주인수권' in report_nm:
                            weight = 0.20  # Bearish (Dilution risk)
                        elif '자기주식' in report_nm or '자사주' in report_nm:
                            if '처분' in report_nm or '매각' in report_nm:
                                weight = 0.20  # Bearish (Disposal / Supply pressure)
                            elif '취득' in report_nm or '매입' in report_nm or '소각' in report_nm:
                                weight = 0.85  # Bullish (Acquisition / Cancellation)
                            else:
                                weight = 0.60  # Neutral / Informational
                        elif '무상증자' in report_nm or '주식분할' in report_nm:
                            weight = 0.90  # Bullish
                        elif '영업이익' in report_nm or '실적' in report_nm:
                            if '적자' in report_nm or '감소' in report_nm:
                                weight = 0.30
                            else:
                                weight = 0.75

                        scores_map[sym] = max(scores_map[sym], weight)

        # Volatility / Volume Event Boost from price data (continuous scoring for all symbols)
        if prices_dict:
            for sym, df in prices_dict.items():
                if sym not in scores_map or df is None or len(df) < 5:
                    continue
                try:
                    c = df['Close']
                    v = df['Volume']
                    if isinstance(c, pd.DataFrame):
                        c = c.iloc[:, 0]
                    if isinstance(v, pd.DataFrame):
                        v = v.iloc[:, 0]
                    c = c.dropna()
                    v = v.dropna()
                    if len(c) >= 5 and len(v) >= 5:
                        avg_vol = float(v.iloc[-5:-1].mean())
                        cur_vol = float(v.iloc[-1])
                        v_ratio = (cur_vol / avg_vol) if avg_vol > 0 else 1.0
                        ret_5d = float((c.iloc[-1] / c.iloc[-5]) - 1.0)
                        continuous_boost = np.clip(0.05 * (v_ratio - 1.0) + 0.10 * ret_5d, -0.2, 0.4)
                        scores_map[sym] = float(np.clip(scores_map[sym] + continuous_boost, 0.0, 1.0))
                except Exception:
                    pass

        # Incorporate filing sentiment intensity multiplier if sentiment_map is provided
        if sentiment_map:
            for sym in symbols:
                if sym in scores_map:
                    sent_metric = sentiment_map.get(sym)
                    if sent_metric:
                        scores_map[sym] = self.incorporate_filing_sentiment(sym, scores_map[sym], sent_metric)

        res_df = pd.DataFrame([{'symbol': k, 'event_score': float(v)} for k, v in scores_map.items()])
        return res_df

    def evaluate_cb_bw_overhang_and_margin_risk(
        self,
        symbols: List[str],
        filings: Optional[List[Dict[str, Any]]] = None,
        margin_rate_dict: Optional[Dict[str, float]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Corporate Event Risk Sandbox:
        1. CB/BW Overhang Trap Detection: Checks DART filings for CB (전환사채) / BW (신주인수권부사채)
           conversion requests where potential dilution > 5.0% of total shares, setting blacklist flag.
        2. Margin Outflow Risk Penalty: Applies penalty factor if margin loan rate > 9.0%.
        """
        res: Dict[str, Dict[str, Any]] = {
            sym: {
                'is_overhang_blacklisted': False,
                'margin_penalty': 1.0,
                'cb_bw_ratio': 0.0
            } for sym in symbols
        }

        # 1. CB/BW Overhang DART Filing Detection
        eff_filings = filings if filings is not None else self.fetch_recent_dart_filings()
        if eff_filings:
            for item in eff_filings:
                stock_code = str(item.get('stock_code', '')).strip().zfill(6) if item.get('stock_code') else ''
                report_nm = item.get('report_nm', '')

                if '전환청구권행사' in report_nm or '신주인수권행사' in report_nm or '전환가액' in report_nm:
                    for sym in symbols:
                        sym_clean = sym.split('.')[0].zfill(6)
                        if stock_code and stock_code == sym_clean:
                            res[sym]['cb_bw_ratio'] = 0.06  # Estimated 6% dilution ratio (> 5.0% threshold)
                            res[sym]['is_overhang_blacklisted'] = True
                            logger.info(f"[CB/BW OVERHANG SANDBOX] Blacklisted {sym} due to dilution risk in filing: {report_nm}")

        # 2. Margin Loan Rate Penalty (> 9.0%)
        if margin_rate_dict:
            for sym, rate in margin_rate_dict.items():
                if sym in res and rate > 9.0:
                    excess_rate = rate - 9.0
                    penalty = float(np.clip(1.0 - excess_rate * 0.05, 0.50, 1.0))
                    res[sym]['margin_penalty'] = penalty
                    logger.info(f"[MARGIN RISK SANDBOX] Applied margin penalty {penalty:.2f} to {sym} (margin rate = {rate:.1f}%)")

        return res



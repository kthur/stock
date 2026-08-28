"""
src/core/event_driven.py
Event-Driven Momentum Engine.
Parses corporate filings (OpenDART for KRX, disclosures) and calculates event-driven
momentum scores based on disclosure types (earnings surprises, stock splits, buybacks, rights offerings).
"""
import logging
import urllib.request
import json
import re
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="event_driven",
        display_name="Event-Driven Momentum",
        score_column="event_score",
        category="event",
        output_file="event_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.05, "BULL_HIGH_VOL": 0.08, "BULL_LOW_VOL": 0.06
        },
    )
)
class EventDrivenEngine(BaseStrategyEngine):
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

    def __init__(self, config=None, dart_api_key: str = "", default_cb_dilution_ratio: float = 0.06):
        self.config = config
        self.dart_api_key = dart_api_key.strip()
        if not self.dart_api_key and config is not None:
            self.dart_api_key = getattr(config, 'dart_api_key', '').strip()
        self.default_cb_dilution_ratio = default_cb_dilution_ratio
        configured_weights = getattr(config, 'event_weights', None) if config else None
        self.event_weights = dict(configured_weights) if configured_weights else dict(self.EVENT_WEIGHTS)

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

    def fetch_recent_sec_filings(self, ticker: str, start: str = "", end: str = "") -> List[Dict[str, Any]]:
        """
        Fetches recent 8-K filings from SEC EDGAR full-text search RSS feed.
        """
        try:
            from datetime import datetime, timedelta
            if not start:
                start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if not end:
                end = datetime.now().strftime('%Y-%m-%d')
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=8-K"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                data = json.loads(resp.read().decode('utf-8'))
                hits = data.get('hits', {}).get('hits', [])
                results = []
                for h in hits:
                    src = h.get('_source', {})
                    results.append({
                        'stock_code': ticker,
                        'corp_code': ticker,
                        'report_nm': src.get('display_names', [''])[0] if src.get('display_names') else '',
                        'rcept_dt': src.get('file_date', '').replace('-', ''),
                        'pblntf_ty': 'B'
                    })
                return results
        except Exception as e:
            logger.debug(f"SEC fetch failed for {ticker}: {e}")
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
        sentiment_map: Optional[Dict[str, Any]] = None,
        as_of_date: Optional[str] = None
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

        if filings is None:
            for sym in symbols:
                if not sym.isdigit() and not sym.endswith('.KS') and not sym.endswith('.KQ'):
                    eff_filings.extend(self.fetch_recent_sec_filings(sym))
        if eff_filings:
            try:
                from src.data_layer.dart_corp_mapper import DARTCorpMapper
                mapper = DARTCorpMapper()
            except Exception:
                mapper = None

            clean_as_of = str(as_of_date).replace('-', '')[:8] if as_of_date else None
            for item in eff_filings:
                # Filing timestamp gating: skip future or post-close filings relative to as_of_date
                rcept_dt = str(item.get('rcept_dt', '')).replace('-', '').strip()[:8]
                if clean_as_of and rcept_dt and rcept_dt > clean_as_of:
                    continue

                stock_code = str(item.get('stock_code', '') or '').strip().zfill(6) if item.get('stock_code') else ''
                corp_code = str(item.get('corp_code', '') or '').strip()
                report_nm = str(item.get('report_nm', '') or '')
                pblntf_ty = str(item.get('pblntf_ty', '') or '')

                # Match stock_code or corp_code with symbol list
                for sym in symbols:
                    sym_code = sym.split('.')[0]
                    sym_clean = sym_code.zfill(6) if sym_code.isdigit() else sym
                    mapped_corp = mapper.get_corp_code(sym_clean) if (mapper and sym_clean.isdigit()) else None
                    matched = (
                        (stock_code and stock_code == sym_clean) or
                        (corp_code and (corp_code == sym_clean or corp_code == sym or (mapped_corp and corp_code == mapped_corp)))
                    )
                    if matched:
                        weight = self.EVENT_WEIGHTS.get(pblntf_ty, 0.5)
                        # Text keyword adjustments with clear directionality
                        if '유상증자' in report_nm or '전환사채' in report_nm or '신주인수권' in report_nm:
                            weight = 0.20  # Bearish (Dilution risk)
                        elif '자기주식' in report_nm or '자사주' in report_nm:
                            if '처분' in report_nm or '매각' in report_nm:
                                weight = 0.20  # Bearish (Disposal / Supply pressure)
                            elif '취득' in report_nm or '매입' in report_nm or '소각' in report_nm:
                                weight = 0.88  # Bullish (Acquisition / Cancellation)
                            else:
                                weight = 0.60  # Neutral / Informational
                        elif '무상증자' in report_nm or '주식분할' in report_nm:
                            weight = 0.92  # Bullish
                        elif any(k in report_nm for k in ['영업이익', '실적', '손익구조', '잠정실적', '매출액또는손익']):
                            if any(k in report_nm for k in ['흑자전환', '흑전', '적자축소', '영업익증가', '이익증가']):
                                weight = 0.88
                            elif any(k in report_nm for k in ['적자전환', '적전', '적자지속', '손실확대', '영업익감소', '감소']):
                                weight = 0.22
                            else:
                                weight = 0.70

                        # Time decay: exact 10-day half-life decay (exp(-days * ln(2) / half_life))
                        days_diff = 0
                        if clean_as_of and rcept_dt and len(clean_as_of) == 8 and len(rcept_dt) == 8:
                            try:
                                d_as_of = pd.to_datetime(clean_as_of, format='%Y%m%d')
                                d_rcept = pd.to_datetime(rcept_dt, format='%Y%m%d')
                                days_diff = max(0, int((d_as_of - d_rcept).days))
                            except Exception:
                                days_diff = 0
                        time_decay = float(np.exp(-days_diff * np.log(2.0) / 10.0))
                        current_delta = scores_map[sym] - 0.50
                        filing_delta = (weight - 0.50) * time_decay
                        # Compound multi-filing impact with soft hyperbolic saturation
                        new_delta = float(np.tanh(current_delta * 2.5 + filing_delta * 2.5) / 2.5)
                        scores_map[sym] = float(np.clip(0.50 + new_delta, 0.05, 0.95))

        # Volatility / Volume Event Boost from price data (continuous scoring for all symbols)
        if prices_dict:
            for sym, df in prices_dict.items():
                if sym not in scores_map or df is None or len(df) < 6:
                    continue
                try:
                    c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                    v_col = 'Volume' if 'Volume' in df.columns else ('volume' if 'volume' in df.columns else None)
                    if not c_col or not v_col:
                        continue
                    c = df[c_col]
                    v = df[v_col]
                    if isinstance(c, pd.DataFrame):
                        c = c.iloc[:, 0]
                    if isinstance(v, pd.DataFrame):
                        v = v.iloc[:, 0]
                    c = c.dropna()
                    v = v.dropna()
                    if len(c) >= 6 and len(v) >= 6:
                        # R10-1 Fix: Use 20-day median (or 5-day mean if short) to prevent block trade distortion
                        if len(v) >= 21:
                            avg_vol = float(v.iloc[-21:-1].median())
                        else:
                            avg_vol = float(v.iloc[-6:-1].mean())
                        cur_vol = float(v.iloc[-1])
                        p_base = float(c.iloc[-6])
                        raw_ret5 = float((c.iloc[-1] / p_base) - 1.0) if p_base > 0 else 0.0
                        ret_5d = float(np.clip(raw_ret5, -0.99, 5.0)) if np.isfinite(raw_ret5) else 0.0
                        raw_vr = float(cur_vol / avg_vol) if avg_vol > 0 else 1.0
                        v_ratio = float(np.clip(raw_vr, 0.0, 20.0)) if np.isfinite(raw_vr) else 1.0
                        # R10-1 Fix: Explicitly define breakout_bonus to eliminate NameError exception
                        breakout_bonus = 0.08 if (v_ratio >= 3.0 and ret_5d > 0.0) else 0.0
                        # High volume breakout booster: +0.08 if volume explodes >= 3x with positive 5D return
                        # R6-3 Fix: Moderate momentum weighting (0.30 * clip(ret_5d)) to preserve DART catalyst signal purity
                        continuous_boost = np.clip(0.05 * (v_ratio - 1.0) + 0.30 * np.clip(ret_5d, -0.15, 0.15) + breakout_bonus, -0.15, 0.25)
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

        res_df = pd.DataFrame([{'symbol': k, 'event_score': float(np.clip(v, 0.0, 1.0)) if np.isfinite(v) else 0.5} for k, v in scores_map.items()])
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
                stock_code = str(item.get('stock_code', '') or '').strip().zfill(6) if item.get('stock_code') else ''
                corp_code = str(item.get('corp_code', '') or '').strip()
                report_nm = str(item.get('report_nm', '') or '')
                flr_nm = str(item.get('flr_nm', '') or '')
                combined_text = f"{report_nm} {flr_nm}"

                if any(kw in report_nm for kw in ('전환청구권행사', '신주인수권행사', '전환가액', '신주인수권부사채', '전환사채')):
                    parsed_ratio = None
                    if 'dilution_ratio' in item:
                        try:
                            parsed_ratio = float(item['dilution_ratio'])
                            if parsed_ratio > 1.0:
                                parsed_ratio = parsed_ratio / 100.0
                        except (ValueError, TypeError):
                            parsed_ratio = None

                    if parsed_ratio is None:
                        match = re.search(r'(?:지분\s*희석|비율|희석률|발행주식총수대비|주식수대비)[^0-9%]{0,20}([0-9]+(?:\.[0-9]+)?)\s*%', combined_text)
                        if not match and '전환가액' not in combined_text and '이자율' not in combined_text:
                            match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%', combined_text)
                        if match:
                            try:
                                parsed_ratio = float(match.group(1)) / 100.0
                            except (ValueError, TypeError):
                                parsed_ratio = None

                    dilution_ratio = parsed_ratio if parsed_ratio is not None else 0.08

                    try:
                        from src.data_layer.dart_corp_mapper import DARTCorpMapper
                        mapper = DARTCorpMapper()
                    except Exception:
                        mapper = None

                    for sym in symbols:
                        sym_code = sym.split('.')[0]
                        sym_clean = sym_code.zfill(6) if sym_code.isdigit() else sym
                        mapped_corp = mapper.get_corp_code(sym_clean) if (mapper and sym_clean.isdigit()) else None
                        matched = (
                            (stock_code and stock_code == sym_clean) or
                            (corp_code and (corp_code == sym_clean or corp_code == sym or (mapped_corp and corp_code == mapped_corp)))
                        )
                        if matched:
                            res[sym]['cb_bw_ratio'] = max(res[sym]['cb_bw_ratio'], dilution_ratio)
                            if dilution_ratio > 0.05:
                                res[sym]['is_overhang_blacklisted'] = True
                                logger.info(f"[CB/BW OVERHANG SANDBOX] Blacklisted {sym} due to dilution risk ({dilution_ratio*100:.1f}%) in filing: {report_nm}")
                            else:
                                logger.debug(f"[CB/BW OVERHANG SANDBOX] Minor dilution ({dilution_ratio*100:.1f}%) for {sym}, not blacklisted.")

        # 2. Margin Loan Rate Penalty (> 9.0%)
        if margin_rate_dict:
            for sym, rate in margin_rate_dict.items():
                if sym in res and rate > 9.0:
                    excess_rate = rate - 9.0
                    penalty = float(np.clip(1.0 - excess_rate * 0.05, 0.50, 1.0))
                    res[sym]['margin_penalty'] = penalty
                    logger.info(f"[MARGIN RISK SANDBOX] Applied margin penalty {penalty:.2f} to {sym} (margin rate = {rate:.1f}%)")

        return res

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        try:
            symbols = list(prices_dict.keys()) if isinstance(prices_dict, dict) else []
            return self.compute_event_scores(
                symbols,
                prices_dict=prices_dict if isinstance(prices_dict, dict) else None,
                filings=kwargs.get("filings") or kwargs.get("filings_list") or kwargs.get("dart_disclosures") or kwargs.get("disclosures"),
                sentiment_map=kwargs.get("sentiment_map"),
                as_of_date=kwargs.get("as_of_date"),
            )

        except Exception as e:
            logger.warning(f"[EventDrivenEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "event_score"])



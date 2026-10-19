"""
src/analysis/symbol_inspector.py
Comprehensive 4-Stage Symbol Exclusion & Portfolio Diagnostic Engine.

Diagnoses why any given stock (KRX or US) is included or excluded at each pipeline stage:
- Stage 1: Universe Status (Market, Sector, Administrative check)
- Stage 2: Price History & Data Integrity (20D/60D length, zero prices, halted trading)
- Stage 3: Fundamental & 37-Strategy Factor Availability (Missing factor reason breakdown)
- Stage 4: Ensemble Ranking, Microstructure Costs & Final OMS Order Gates
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StrategyFactorStatus:
    strategy_id: str
    display_name: str
    is_valid: bool
    score: Optional[float] = None
    missing_reason: str = ""


@dataclass
class SymbolDiagnosticResult:
    symbol: str
    normalized_symbol: str
    name: str = ""
    market: str = ""
    sector: str = ""
    industry: str = ""

    # Stage 1: Universe
    universe_passed: bool = False
    universe_reason: str = ""
    is_administrative: bool = False

    # Stage 2: Price Data
    price_passed: bool = False
    price_reason: str = ""
    total_bars: int = 0
    first_date: str = ""
    last_date: str = ""
    last_close: float = 0.0
    zero_volume_ratio: float = 0.0

    # Stage 3: Fundamentals & 37 Strategies
    fundamentals_available: bool = False
    fundamentals_reason: str = ""
    strategy_count_total: int = 37
    strategy_count_valid: int = 0
    strategy_coverage_pct: float = 0.0
    strategy_factors: Dict[str, StrategyFactorStatus] = field(default_factory=dict)
    missing_factor_summary: Dict[str, List[str]] = field(default_factory=dict)

    # Stage 4: Ensemble & Execution OMS
    ensemble_scored: bool = False
    ensemble_score: Optional[float] = None
    market_rank: Optional[int] = None
    market_total_symbols: Optional[int] = None
    percentile_rank: Optional[float] = None
    expected_return_20d: Optional[float] = None
    estimated_friction_cost: Optional[float] = None
    net_expected_return: Optional[float] = None

    # Final Decision
    is_in_portfolio: bool = False
    portfolio_weight: float = 0.0
    target_action: str = "NONE"
    primary_exclusion_stage: str = "NONE"  # 'UNIVERSE', 'PRICE', 'FACTORS', 'ENSEMBLE_RANK', 'OMS_GATE', 'INCLUDED'
    primary_exclusion_reason: str = "NONE"
    detailed_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "normalized_symbol": self.normalized_symbol,
            "name": self.name,
            "market": self.market,
            "sector": self.sector,
            "industry": self.industry,
            "stage_1_universe": {
                "passed": self.universe_passed,
                "reason": self.universe_reason,
                "is_administrative": self.is_administrative,
            },
            "stage_2_price": {
                "passed": self.price_passed,
                "reason": self.price_reason,
                "total_bars": self.total_bars,
                "first_date": self.first_date,
                "last_date": self.last_date,
                "last_close": self.last_close,
                "zero_volume_ratio": round(self.zero_volume_ratio, 4),
            },
            "stage_3_factors": {
                "fundamentals_available": self.fundamentals_available,
                "strategy_count_total": self.strategy_count_total,
                "strategy_count_valid": self.strategy_count_valid,
                "strategy_coverage_pct": round(self.strategy_coverage_pct, 2),
                "missing_factor_summary": self.missing_factor_summary,
            },
            "stage_4_ensemble_oms": {
                "ensemble_scored": self.ensemble_scored,
                "ensemble_score": self.ensemble_score,
                "market_rank": self.market_rank,
                "market_total": self.market_total_symbols,
                "percentile_rank": self.percentile_rank,
                "expected_return_20d": self.expected_return_20d,
                "estimated_friction_cost": self.estimated_friction_cost,
                "net_expected_return": self.net_expected_return,
                "is_in_portfolio": self.is_in_portfolio,
                "portfolio_weight": self.portfolio_weight,
                "target_action": self.target_action,
            },
            "verdict": {
                "is_included": self.is_in_portfolio,
                "primary_exclusion_stage": self.primary_exclusion_stage,
                "primary_exclusion_reason": self.primary_exclusion_reason,
                "detailed_explanation": self.detailed_explanation,
            }
        }


class SymbolInspector:
    """
    Performs comprehensive diagnostic inspection on any given stock symbol
    to trace and explain exclusion reasons across the entire pipeline.
    """

    STRATEGY_DISPLAY_NAMES = {
        'regression': '1. XGBoost Regression',
        'surge': '2. Surge Classifier',
        'lead_lag': '3. Lead-Lag Correlation',
        'vcp_rule': '4. VCP Rule Pattern',
        'vcp_ml': '5. VCP ML Surge Predictor',
        'lstm': '6. Strict Causal LSTM',
        'stat_arb': '7. Stat-Arb Cointegration',
        'sector_rotation': '8. Sector Rotation',
        'rim_valuation': '9. RIM Valuation',
        'event_driven': '10. Event-Driven Catalyst',
        'mq_factor': '11. Momentum Quality (MQ)',
        'iv_skew': '12. Options IV Skew',
        'order_flow': '13. Order Flow Imbalance',
        'short_term_reversal': '14. Short-Term Reversal',
        'arm_factor': '15. Analyst Revision (ARM)',
        'card_factor': '16. Cross-Asset Divergence (CARD)',
        'latr_factor': '17. Liquidity Tail Risk (LATR)',
        'inst_foreign_sector': '18. Inst & Foreign Sector',
        'supply_chain': '19. Supply Chain Momentum',
        'sentiment': '20. FinBERT Sentiment',
        'factor_neutralized': '21. Style Factor Neutralizer',
        'vol_target': '22. Dynamic Volatility Target',
        'microstructure': '23. Microstructure Imbalance',
        'accruals_quality': '24. Accruals Accounting Quality',
        'short_squeeze': '25. Short Squeeze Catalyst',
        'valueup_catalyst': '26. Value-Up Catalyst',
        'trend_efficiency': '27. Kaufman Trend Efficiency',
        'gamma_squeeze': '28. Options Gamma Squeeze',
        'insider_buying': '29. Insider Buying Catalyst',
        'darkpool': '30. Darkpool HFT Momentum',
        'earnings_tone_drift': '31. Earnings Call Tone Drift',
        'cross_asset_spillover': '32. Cross-Asset Spillover',
        'supply_chain_gnn': '33. Supply Chain GNN Network',
        'range_expansion_breakout': '34. Range Expansion Breakout',
        'dual_correction': '35. Dual Regime Correction',
        'index_rebalance': '36. Index Rebalance Flow',
        'overnight_gap_reversal': '37. Overnight Gap Reversal',
    }

    def __init__(
        self,
        price_db: Optional[Any] = None,
        indicator_storage: Optional[Any] = None,
        oms_engine: Optional[Any] = None,
    ):
        self.price_db: Optional[Any] = None
        self.indicator_storage: Optional[Any] = None
        self.oms_engine: Optional[Any] = None

        if price_db is None:
            try:
                from src.persistence.database import StockPriceDB
                self.price_db = StockPriceDB()
            except Exception as e:
                logger.debug(f"StockPriceDB fallback init: {e}")
                self.price_db = None
        else:
            self.price_db = price_db

        if indicator_storage is None:
            try:
                from src.data_layer.indicator_storage import MarketIndicatorStorage
                self.indicator_storage = MarketIndicatorStorage()
            except Exception as e:
                logger.debug(f"MarketIndicatorStorage fallback init: {e}")
                self.indicator_storage = None
        else:
            self.indicator_storage = indicator_storage

        if oms_engine is None:
            try:
                from src.execution.oms_engine import ExecutionOMSEngine
                self.oms_engine = ExecutionOMSEngine()
            except Exception as e:
                logger.debug(f"ExecutionOMSEngine fallback init: {e}")
                self.oms_engine = None
        else:
            self.oms_engine = oms_engine

    @staticmethod
    def normalize_symbol(raw_sym: str) -> tuple[str, str]:
        """Normalizes symbol string and detects market type (KRX vs US)."""
        s = str(raw_sym).strip().upper()
        # Clean dot notation (e.g. 005930.KS -> 005930)
        base = s.split('.')[0]
        if base.isdigit():
            # Korean 6-digit code
            norm = base.zfill(6)
            mkt_guess = "KOSPI"
        else:
            norm = s
            mkt_guess = "US"
        return norm, mkt_guess

    def inspect_symbol(
        self,
        symbol: str,
        universe_df: Optional[pd.DataFrame] = None,
        ensemble_df: Optional[pd.DataFrame] = None,
        order_plans_df: Optional[pd.DataFrame] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        price_summary_cache: Optional[Dict[str, Dict[str, Any]]] = None,
        funds_set: Optional[set] = None,
        ensemble_map: Optional[Dict[str, Dict[str, Any]]] = None,
        order_plans_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> SymbolDiagnosticResult:
        """
        Executes complete 4-stage inspection for a single symbol.
        """
        norm_sym, guessed_mkt = self.normalize_symbol(symbol)
        diag = SymbolDiagnosticResult(symbol=symbol, normalized_symbol=norm_sym)

        # -------------------------------------------------------------
        # Stage 1: Universe Status Inspection
        # -------------------------------------------------------------
        u_row = None
        if universe_df is not None and not universe_df.empty:
            match = universe_df[universe_df['symbol'].astype(str).str.upper() == norm_sym]
            if match.empty:
                match = universe_df[universe_df['symbol'].astype(str).str.upper() == symbol.upper()]
            if not match.empty:
                u_row = match.iloc[0].to_dict()

        if u_row is None and self.indicator_storage is not None:
            try:
                with self.indicator_storage._connect() as conn:
                    row = conn.execute(
                        "SELECT symbol, name, market, sector, industry FROM stock_universe WHERE symbol = ? OR symbol = ?",
                        (norm_sym, symbol)
                    ).fetchone()
                    if row:
                        u_row = {
                            "symbol": row[0], "name": row[1], "market": row[2],
                            "sector": row[3], "industry": row[4]
                        }
            except Exception as e:
                logger.debug(f"Universe lookup error: {e}")

        if u_row:
            diag.universe_passed = True
            diag.name = str(u_row.get("name") or norm_sym)
            diag.market = str(u_row.get("market") or guessed_mkt).upper()
            diag.sector = str(u_row.get("sector") or "")
            diag.industry = str(u_row.get("industry") or "")
            diag.universe_reason = f"정상 상장 종목 (시장: {diag.market}, 업종: {diag.sector or '일반'})"
        else:
            diag.universe_passed = False
            diag.universe_reason = "유니버스 미등록 (KRX/미국 정규 상장 목록에 부재하거나 관리종목으로 제외됨)"
            diag.primary_exclusion_stage = "UNIVERSE"
            diag.primary_exclusion_reason = "UNIVERSE_NOT_LISTED"
            diag.detailed_explanation = f"종목 코드 '{symbol}'이(가) 시스템의 5대 시장 정규 유니버스에 등록되어 있지 않습니다."

        # -------------------------------------------------------------
        # Stage 2: Price History & Data Integrity Inspection
        # -------------------------------------------------------------
        p_df = None
        if prices_dict is not None:
            for k in (norm_sym, symbol, f"{norm_sym}.KS", f"{norm_sym}.KQ"):
                if k in prices_dict and prices_dict[k] is not None and not prices_dict[k].empty:
                    p_df = prices_dict[k]
                    break

        if p_df is None and price_summary_cache is not None:
            p_info = (
                price_summary_cache.get(norm_sym) or
                price_summary_cache.get(symbol) or
                price_summary_cache.get(f"{norm_sym}.KS") or
                price_summary_cache.get(f"{norm_sym}.KQ")
            )
            if p_info and p_info.get("bars", 0) >= 20:
                diag.price_passed = True
                diag.total_bars = p_info.get("bars", 0)
                diag.first_date = str(p_info.get("first_date", ""))
                diag.last_date = str(p_info.get("last_date", ""))
                diag.last_close = float(p_info.get("last_close", 1000.0))
                diag.price_reason = f"정상 주가 시계열 ({diag.total_bars:,}일치 봉 데이터 적재, 최근일: {diag.last_date})"
            elif p_info:
                diag.price_passed = False
                diag.total_bars = p_info.get("bars", 0)
                diag.price_reason = f"주가 데이터 이력 부족 (현재: {diag.total_bars}일치 / 최소 기준: 20일 이상)"

        if p_df is None and not diag.price_passed and price_summary_cache is None and self.price_db is not None:
            try:
                for k in (norm_sym, symbol, f"{norm_sym}.KS", f"{norm_sym}.KQ"):
                    p_df = self.price_db.get_prices(k)
                    if p_df is not None and not p_df.empty:
                        break
            except Exception as e:
                logger.debug(f"Price lookup error: {e}")

        if not diag.price_passed and p_df is not None and not p_df.empty and len(p_df) >= 20:
            diag.price_passed = True
            diag.total_bars = len(p_df)
            c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else p_df.columns[0])
            v_col = 'Volume' if 'Volume' in p_df.columns else ('volume' if 'volume' in p_df.columns else None)

            diag.first_date = str(p_df.index[0])[:10] if isinstance(p_df.index, pd.DatetimeIndex) else str(p_df.index[0])
            diag.last_date = str(p_df.index[-1])[:10] if isinstance(p_df.index, pd.DatetimeIndex) else str(p_df.index[-1])
            diag.last_close = float(p_df[c_col].dropna().iloc[-1]) if not p_df[c_col].dropna().empty else 0.0

            if v_col:
                zero_v = (p_df[v_col].dropna() == 0).sum()
                diag.zero_volume_ratio = float(zero_v / len(p_df))

            if diag.last_close <= 0:
                diag.price_passed = False
                diag.price_reason = "최근 종가가 0원 이하이거나 비정상 데이터"
                diag.primary_exclusion_stage = "PRICE"
                diag.primary_exclusion_reason = "INVALID_ZERO_PRICE"
                diag.detailed_explanation = "종가가 0원 이하로 산출되어 거래정지 또는 데이터 왜곡으로 제외되었습니다."
            else:
                diag.price_reason = f"정상 주가 시계열 ({diag.total_bars:,}일치 봉 데이터 적재, 최근일: {diag.last_date})"
        elif not diag.price_passed:
            diag.total_bars = len(p_df) if p_df is not None else 0
            diag.price_reason = f"주가 데이터 이력 부족 (현재: {diag.total_bars}일치 / 최소 기준: 20일 이상)"
            if diag.universe_passed:
                diag.primary_exclusion_stage = "PRICE"
                diag.primary_exclusion_reason = "INSUFFICIENT_PRICE_HISTORY"
                diag.detailed_explanation = f"최소 20 영업일 이상의 주가 이력이 필요하지만, {diag.total_bars}일치만 존재하여 팩터 및 예측 모델 연산이 불가합니다."

        # -------------------------------------------------------------
        # Stage 3: Fundamental & 37-Strategy Factor Availability
        # -------------------------------------------------------------
        is_krx = diag.market in ('KOSPI', 'KOSDAQ') or norm_sym.isdigit()

        # Check fundamental cache
        if funds_set is not None:
            diag.fundamentals_available = (norm_sym in funds_set or symbol in funds_set)
            diag.fundamentals_reason = "재무제표 데이터 적재 완료" if diag.fundamentals_available else "최근 재무제표 부재 (Filing Lag 45d/40d 미충족 또는 데이터 미제공)"
        elif self.indicator_storage is not None:
            try:
                fund_df = self.indicator_storage.get_fundamentals(norm_sym)
                if fund_df is not None and not fund_df.empty:
                    diag.fundamentals_available = True
                    diag.fundamentals_reason = "재무제표 데이터 적재 완료"
                else:
                    diag.fundamentals_available = False
                    diag.fundamentals_reason = "최근 재무제표 부재 (Filing Lag 45d/40d 미충족 또는 데이터 미제공)"
            except Exception:
                diag.fundamentals_available = False
                diag.fundamentals_reason = "재무제표 조회 실패"

        # Check strategy factor scores from ensemble predictions
        ens_row = None
        if ensemble_map is not None:
            ens_row = ensemble_map.get(norm_sym) or ensemble_map.get(symbol)
        elif ensemble_df is not None and not ensemble_df.empty:
            sub = ensemble_df[ensemble_df['symbol'].astype(str).str.upper() == norm_sym]
            if sub.empty:
                sub = ensemble_df[ensemble_df['symbol'].astype(str).str.upper() == symbol.upper()]
            if not sub.empty:
                ens_row = sub.iloc[0].to_dict()
        elif self.indicator_storage is not None:
            try:
                with self.indicator_storage._connect() as conn:
                    # Look up latest ensemble prediction
                    cols = [r[1] for r in conn.execute("PRAGMA table_info(ensemble_predictions)").fetchall()]
                    if cols:
                        row = conn.execute(
                            f"SELECT {', '.join(cols)} FROM ensemble_predictions WHERE symbol = ? OR symbol = ? ORDER BY date DESC LIMIT 1",  # nosec B608
                            (norm_sym, symbol)
                        ).fetchone()
                        if row:
                            ens_row = dict(zip(cols, row))
            except Exception as e:
                logger.debug(f"Ensemble prediction lookup error: {e}")

        # Evaluate 37 strategies
        strat_score_cols = {
            'regression': 'reg_score',
            'surge': 'surge_score',
            'lead_lag': 'll_score',
            'vcp_rule': 'vcp_rule_score',
            'vcp_ml': 'vcp_ml_score',
            'lstm': 'lstm_score',
            'stat_arb': 'stat_arb_score',
            'sector_rotation': 'sector_score',
            'rim_valuation': 'rim_score',
            'event_driven': 'event_score',
            'mq_factor': 'mq_score',
            'iv_skew': 'iv_skew_score',
            'order_flow': 'order_flow_score',
            'short_term_reversal': 'reversal_score',
            'arm_factor': 'arm_score',
            'card_factor': 'card_score',
            'latr_factor': 'latr_score',
            'inst_foreign_sector': 'inst_foreign_sector_score',
            'supply_chain': 'supply_chain_score',
            'sentiment': 'sentiment_score',
            'factor_neutralized': 'factor_neutralized_score',
            'vol_target': 'vol_target_score',
            'microstructure': 'microstructure_score',
            'accruals_quality': 'accruals_quality_score',
            'short_squeeze': 'short_squeeze_score',
            'valueup_catalyst': 'valueup_catalyst_score',
            'trend_efficiency': 'trend_efficiency_score',
            'gamma_squeeze': 'gamma_squeeze_score',
            'insider_buying': 'insider_buying_score',
            'darkpool': 'darkpool_score',
            'earnings_tone_drift': 'earnings_tone_drift_score',
            'cross_asset_spillover': 'cross_asset_spillover_score',
            'supply_chain_gnn': 'supply_chain_gnn_score',
            'range_expansion_breakout': 'range_expansion_score',
            'dual_correction': 'dual_correction_score',
            'index_rebalance': 'index_rebalance_score',
            'overnight_gap_reversal': 'overnight_gap_score',
        }

        valid_strat_count = 0
        missing_buckets: Dict[str, List[str]] = {}

        for s_id, d_name in self.STRATEGY_DISPLAY_NAMES.items():
            col = strat_score_cols.get(s_id, f"{s_id}_score")
            val = None
            is_v = False
            m_reason = ""

            if ens_row is not None and col in ens_row:
                raw_val = ens_row[col]
                if raw_val is not None and pd.notna(raw_val) and math.isfinite(float(raw_val)):
                    val = round(float(raw_val), 4)
                    is_v = True
                    valid_strat_count += 1

            if not is_v:
                # Infer specific missing reason
                if not diag.price_passed:
                    m_reason = "INSUFFICIENT_PRICE_HISTORY"
                elif s_id in ('iv_skew', 'gamma_squeeze'):
                    m_reason = "NO_OPTIONS_CHAIN (한국/옵션 미상장 종목)" if is_krx else "NO_OPTIONS_DATA"
                elif s_id in ('darkpool',):
                    m_reason = "NON_US_MARKET_SCOPE (다크풀 데이터는 미국 시장 전용)" if is_krx else "NO_DARKPOOL_FLOW"
                elif s_id in ('stat_arb',):
                    m_reason = "NO_COINTEGRATED_PAIR (통계적 유의 공적분 페어 부재)"
                elif s_id in ('rim_valuation',):
                    m_reason = "LOW_EARNINGS_QUALITY (영업손실 또는 순이익 적자)" if diag.fundamentals_available else "NO_FUNDAMENTAL_DATA"
                elif s_id in ('accruals_quality', 'valueup_catalyst', 'arm_factor'):
                    m_reason = "NO_FUNDAMENTAL_DATA (재무제표/컨센서스 부재)"
                elif s_id in ('sentiment',):
                    m_reason = "NO_CORPORATE_FILING (최근 공시/뉴스 텍스트 부재)"
                elif s_id in ('earnings_tone_drift',):
                    m_reason = "NO_EARNINGS_TRANSCRIPT (실적 발표 컨퍼런스콜 텍스트 부재)"
                elif s_id in ('lead_lag',):
                    m_reason = "NO_LEAD_LAG_LEADER (업종 내 유의한 선행 주도주 부재)"
                elif s_id in ('supply_chain', 'supply_chain_gnn'):
                    m_reason = "NO_SUPPLY_CHAIN_MAPPING (공급망 네트워크 맵 미매핑)"
                else:
                    m_reason = "STRATEGY_SIGNAL_NEUTRAL (신호 미발생 또는 조건 미충족)"

                missing_buckets.setdefault(m_reason, []).append(s_id)

            diag.strategy_factors[s_id] = StrategyFactorStatus(
                strategy_id=s_id,
                display_name=d_name,
                is_valid=is_v,
                score=val,
                missing_reason=m_reason
            )

        diag.strategy_count_total = len(self.STRATEGY_DISPLAY_NAMES)
        diag.strategy_count_valid = valid_strat_count
        diag.strategy_coverage_pct = (valid_strat_count / diag.strategy_count_total) * 100.0 if diag.strategy_count_total > 0 else 0.0
        diag.missing_factor_summary = missing_buckets

        # -------------------------------------------------------------
        # Stage 4: Ensemble Ranking, Microstructure & Final OMS Gates
        # -------------------------------------------------------------
        if ens_row is not None and ('ensemble_score' in ens_row or 'ensemble_final_score' in ens_row):
            diag.ensemble_scored = True
            e_sc = float(ens_row.get('ensemble_score') or ens_row.get('ensemble_final_score') or 0.5)
            diag.ensemble_score = round(e_sc, 4)
            diag.expected_return_20d = round(float(ens_row.get('expected_return_20d') or ((e_sc - 0.5) * 0.10)), 4)
            diag.estimated_friction_cost = round(float(ens_row.get('total_friction_cost') or 0.0035), 4)
            diag.net_expected_return = round(diag.expected_return_20d - diag.estimated_friction_cost, 4)
        elif diag.price_passed:
            diag.ensemble_scored = True
            diag.ensemble_score = 0.50
            diag.expected_return_20d = 0.0
            diag.estimated_friction_cost = 0.0035
            diag.net_expected_return = -0.0035

        # Check Order Plans & Portfolio
        if order_plans_map is not None:
            p_dict = order_plans_map.get(norm_sym) or order_plans_map.get(symbol)
            if p_dict:
                diag.is_in_portfolio = True
                diag.target_action = str(p_dict.get('action', 'BUY'))
                diag.portfolio_weight = float(p_dict.get('target_weight', 0.0))
        elif order_plans_df is not None and not order_plans_df.empty:
            p_match = order_plans_df[order_plans_df['symbol'].astype(str).str.upper() == norm_sym]
            if not p_match.empty:
                diag.is_in_portfolio = True
                diag.target_action = str(p_match.iloc[0].get('action', 'BUY'))
                diag.portfolio_weight = float(p_match.iloc[0].get('target_weight', 0.0))
        elif not diag.is_in_portfolio and self.oms_engine is not None:
            try:
                conn = self.oms_engine._get_conn()
                row = conn.execute(
                    "SELECT action, target_weight FROM order_plans WHERE symbol = ? OR symbol = ? ORDER BY rowid DESC LIMIT 1",
                    (norm_sym, symbol)
                ).fetchone()
                if row:
                    diag.is_in_portfolio = True
                    diag.target_action = str(row[0])
                    diag.portfolio_weight = float(row[1] or 0.0)
            except Exception as e:
                logger.debug(f"OMS order plan query: {e}")

        # Final verdict decision
        if diag.is_in_portfolio:
            diag.primary_exclusion_stage = "INCLUDED"
            diag.primary_exclusion_reason = "PORTFOLIO_ACTIVE"
            diag.detailed_explanation = f"최종 추천 포트폴리오 편입 (주문: {diag.target_action}, 목표 비중: {diag.portfolio_weight*100:.2f}%)"
        elif diag.primary_exclusion_stage == "NONE":
            if diag.net_expected_return is not None and diag.net_expected_return <= 0.0:
                diag.primary_exclusion_stage = "OMS_GATE"
                diag.primary_exclusion_reason = "NEGATIVE_NET_RETURN"
                ret_str = f"{(diag.expected_return_20d or 0.0)*100:+.2f}%"
                cost_str = f"{(diag.estimated_friction_cost or 0.0)*100:.2f}%"
                net_str = f"{(diag.net_expected_return or 0.0)*100:+.2f}%"
                diag.detailed_explanation = f"예상 수익률({ret_str})이 추정 거래 마찰비용({cost_str})보다 낮아 순기대수익률이 음수({net_str})입니다."
            else:
                diag.primary_exclusion_stage = "ENSEMBLE_RANK"
                diag.primary_exclusion_reason = "LOW_ENSEMBLE_RANK"
                diag.detailed_explanation = f"앙상블 점수({diag.ensemble_score:.3f})가 상위 포트폴리오 선정 컷오프(Top 20~50위)에 미달하여 제외되었습니다."

        return diag

    def format_text_report(self, diag: SymbolDiagnosticResult) -> str:
        """Formats the diagnostic result into a clean, human-readable Korean text report."""
        lines = []
        status_icon = "🟢 편입됨 (포트폴리오 액티브)" if diag.is_in_portfolio else "🔴 제외됨 (미편입)"

        lines.append("=" * 80)
        lines.append(f"🔍 [종목 정밀 진단 리포트] {diag.name} ({diag.normalized_symbol}) | {status_icon}")
        lines.append("=" * 80)
        lines.append(f"• 기본 정보: 시장={diag.market or '미지정'} | 업종={diag.sector or '일반'} | 세부산업={diag.industry or '일반'}")
        lines.append("")

        # 1. Universe
        u_icon = "✅ PASS" if diag.universe_passed else "❌ FAIL"
        lines.append(f"1. 유니버스 편입 상태 : {u_icon} ({diag.universe_reason})")

        # 2. Price History
        p_icon = "✅ PASS" if diag.price_passed else "❌ FAIL"
        lines.append(f"2. 주가 시계열 상태  : {p_icon} ({diag.price_reason})")

        # 3. Fundamentals & Factors
        f_icon = "✅ PASS" if diag.fundamentals_available else "⚠️ WARN"
        lines.append(f"3. 펀더멘털 데이터    : {f_icon} ({diag.fundamentals_reason})")
        lines.append(f"4. 37대 전략 팩터 커버리지: {diag.strategy_count_valid} / {diag.strategy_count_total}개 유효 ({diag.strategy_coverage_pct:.1f}%)")

        if diag.missing_factor_summary:
            lines.append("   [결측 팩터 세부 원인 분류]:")
            for reason, strats in diag.missing_factor_summary.items():
                s_list = ", ".join(strats[:5])
                if len(strats) > 5:
                    s_list += f" 외 {len(strats)-5}개"
                lines.append(f"     * [{reason}]: {s_list}")
        lines.append("")

        # 4. Ensemble & OMS
        lines.append("5. 앙상블 스코어 및 기대수익률:")
        if diag.ensemble_scored and diag.ensemble_score is not None:
            lines.append(f"   • 앙상블 종합 점수 : {diag.ensemble_score:.4f}")
            if diag.expected_return_20d is not None and diag.estimated_friction_cost is not None:
                r_20d = (diag.expected_return_20d or 0.0) * 100
                f_cost = (diag.estimated_friction_cost or 0.0) * 100
                n_ret = (diag.net_expected_return or 0.0) * 100
                lines.append(f"   • 20D 예상 수익률  : {r_20d:+.2f}%")
                lines.append(f"   • 추정 거래 마찰비용: {f_cost:.2f}% (세금/스프레드/충격비용)")
                lines.append(f"   • 순기대수익률 (Net): {n_ret:+.2f}%")
        else:
            lines.append("   • 앙상블 스코어링 미실행 (시계열 데이터 부족)")
        lines.append("")

        # Verdict
        lines.append("=" * 80)
        lines.append(f"📋 [최종 판정]: {'포트폴리오 편입 (BUY)' if diag.is_in_portfolio else '제외됨 (EXCLUDED)'}")
        lines.append(f"   • 탈락 단계: [{diag.primary_exclusion_stage}]")
        lines.append(f"   • 주요 원인: [{diag.primary_exclusion_reason}]")
        lines.append(f"   • 세부 설명: {diag.detailed_explanation}")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_batch_diagnostics(
        self,
        universe_df: Optional[pd.DataFrame] = None,
        ensemble_df: Optional[pd.DataFrame] = None,
        order_plans_df: Optional[pd.DataFrame] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        symbols_list: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generates structured batch diagnostics across universe symbols."""
        if universe_df is None and self.indicator_storage is not None:
            try:
                universe_df = self.indicator_storage.get_universe()
            except Exception:
                pass

        if ensemble_df is None and self.indicator_storage is not None:
            try:
                ensemble_df = self.indicator_storage.get_ensemble_predictions_history(days=7)
            except Exception:
                pass

        if symbols_list is None:
            if universe_df is not None and not universe_df.empty and 'symbol' in universe_df.columns:
                symbols_list = universe_df['symbol'].dropna().unique().tolist()
            elif ensemble_df is not None and not ensemble_df.empty and 'symbol' in ensemble_df.columns:
                symbols_list = ensemble_df['symbol'].dropna().unique().tolist()
            elif self.price_db is not None:
                symbols_list = self.price_db.get_all_symbols()
            else:
                symbols_list = []

        # Pre-cache price summaries in single SQL pass if price_db is available
        price_summary_cache: Dict[str, Dict[str, Any]] = {}
        if prices_dict is None and self.price_db is not None:
            try:
                import sqlite3
                with sqlite3.connect(str(self.price_db.db_path)) as conn:
                    rows = conn.execute("SELECT symbol, COUNT(*), MIN(date), MAX(date) FROM stock_prices GROUP BY symbol").fetchall()
                    for r in rows:
                        s_norm, _ = self.normalize_symbol(str(r[0]))
                        price_summary_cache[s_norm] = {
                            "bars": int(r[1]),
                            "first_date": str(r[2]),
                            "last_date": str(r[3]),
                            "last_close": 1000.0
                        }
            except Exception as e:
                logger.debug(f"Fast price summary cache error: {e}")

        # Pre-cache fundamentals in single SQL pass
        funds_set: set = set()
        if self.indicator_storage is not None:
            try:
                with self.indicator_storage._connect() as conn:
                    for tbl in ('stock_fundamentals', 'fundamentals'):
                        try:
                            f_rows = conn.execute(f"SELECT DISTINCT symbol FROM {tbl}").fetchall()  # nosec B608
                            for r in f_rows:
                                s_n, _ = self.normalize_symbol(str(r[0]))
                                funds_set.add(s_n)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Fast fundamental set cache error: {e}")

        # Pre-cache order plans in single pass
        order_plans_map: Dict[str, Dict[str, Any]] = {}
        if order_plans_df is not None and not order_plans_df.empty:
            for r in order_plans_df.itertuples(index=False):
                r_d = r._asdict() if hasattr(r, '_asdict') else dict(zip(order_plans_df.columns, r))
                s_n, _ = self.normalize_symbol(str(r_d.get('symbol', '')))
                order_plans_map[s_n] = r_d
        elif self.oms_engine is not None:
            try:
                conn_oms = self.oms_engine._get_conn()
                rows = conn_oms.execute("SELECT symbol, action, target_weight FROM order_plans").fetchall()
                for r in rows:
                    s_n, _ = self.normalize_symbol(str(r[0]))
                    order_plans_map[s_n] = {"symbol": s_n, "action": r[1], "target_weight": float(r[2] or 0.0)}
            except Exception as e:
                logger.debug(f"Fast order plans cache error: {e}")

        # Pre-cache ensemble predictions in single pass
        ensemble_map: Dict[str, Dict[str, Any]] = {}
        if ensemble_df is not None and not ensemble_df.empty:
            for r in ensemble_df.itertuples(index=False):
                r_d = r._asdict() if hasattr(r, '_asdict') else dict(zip(ensemble_df.columns, r))
                s_n, _ = self.normalize_symbol(str(r_d.get('symbol', '')))
                ensemble_map[s_n] = r_d
        elif self.indicator_storage is not None:
            try:
                with self.indicator_storage._connect() as conn:
                    cols = [r[1] for r in conn.execute("PRAGMA table_info(ensemble_predictions)").fetchall()]
                    if cols:
                        rows = conn.execute(f"SELECT {', '.join(cols)} FROM ensemble_predictions").fetchall()  # nosec B608
                        for r in rows:
                            r_d = dict(zip(cols, r))
                            s_n, _ = self.normalize_symbol(str(r_d.get('symbol', '')))
                            ensemble_map[s_n] = r_d
            except Exception as e:
                logger.debug(f"Fast ensemble map cache error: {e}")

        results: Dict[str, Any] = {}
        stage_counts = {
            "UNIVERSE": 0,
            "PRICE": 0,
            "FACTORS": 0,
            "ENSEMBLE_RANK": 0,
            "OMS_GATE": 0,
            "INCLUDED": 0,
        }
        reason_counts: Dict[str, int] = {}

        for sym in symbols_list:
            diag = self.inspect_symbol(
                sym,
                universe_df=universe_df,
                ensemble_df=ensemble_df,
                order_plans_df=order_plans_df,
                prices_dict=prices_dict,
                price_summary_cache=price_summary_cache,
                funds_set=funds_set,
                ensemble_map=ensemble_map,
                order_plans_map=order_plans_map,
            )
            results[diag.normalized_symbol] = diag.to_dict()
            stage_counts[diag.primary_exclusion_stage] = stage_counts.get(diag.primary_exclusion_stage, 0) + 1
            reason_counts[diag.primary_exclusion_reason] = reason_counts.get(diag.primary_exclusion_reason, 0) + 1

        return {
            "total_symbols_evaluated": len(symbols_list),
            "stage_breakdown": stage_counts,
            "top_exclusion_reasons": dict(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)),
            "diagnostics": results,
        }

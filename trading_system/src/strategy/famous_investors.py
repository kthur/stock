"""Famous Investor Strategies - 유명 투자자 전략 엔진"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


import numpy as np


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return default


class InvestorType(Enum):
    VALUE_INVESTOR = "가치투자"
    GROWTH_INVESTOR = "성장투자"
    MOMENTUM_INVESTOR = "모멘텀"
    DIVIDEND_INVESTOR = "배당주"


@dataclass
class InvestorSignal:
    """투자자 신호"""

    investor_type: InvestorType
    symbol: str
    recommendation: str  # BUY, HOLD, SELL
    confidence: float  # 0.0 ~ 1.0
    reasons: List[str]
    target_price: Optional[float] = None
    timeline: str = "중기"  # 단기, 중기, 장기
    risk_level: str = "중간"  # 낮음, 중간, 높음
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BuffettStrategy:
    """워렌 버펫 - 가치투자"""

    @staticmethod
    def analyze(stock_data: Dict) -> InvestorSignal:
        """
        버펫 전략 분석

         - 저평가 우량주 찾기
        - PER, PBR 낮음
        - ROE 높음
        - 안정적 현금흐름
        """
        symbol = stock_data.get("symbol", "UNKNOWN")
        pe_ratio = _safe_float(stock_data.get("pe_ratio"))
        pb_ratio = _safe_float(stock_data.get("pb_ratio"))
        roe = _safe_float(stock_data.get("roe"), 0.0)
        debt_ratio = _safe_float(stock_data.get("debt_ratio"), 0.0)
        dividend_yield = _safe_float(stock_data.get("dividend_yield"), 0.0)

        reasons = []
        score = 0.0
        max_score = 5

        if pe_ratio is not None and pe_ratio < 15:
            reasons.append(f"PER {pe_ratio:.1f} - 저평가")
            score += 1
        elif pe_ratio is not None and pe_ratio < 20:
            reasons.append(f"PER {pe_ratio:.1f} - 합리적 평가")
            score += 0.5

        if pb_ratio is not None and pb_ratio < 1.0:
            reasons.append(f"PBR {pb_ratio:.2f} - 낮은 가격")
            score += 1
        elif pb_ratio is not None and pb_ratio < 2.0:
            reasons.append(f"PBR {pb_ratio:.2f} - 적절한 가격")
            score += 0.5

        # ROE 평가 (우량 기업 판별)
        if roe > 15:
            reasons.append(f"ROE {roe:.1f}% - 높은 수익성")
            score += 1
        elif roe > 10:
            reasons.append(f"ROE {roe:.1f}% - 양호한 수익성")
            score += 0.5

        # 부채 평가
        if debt_ratio < 30:
            reasons.append(f"부채율 {debt_ratio:.1f}% - 건전한 재무")
            score += 1
        elif debt_ratio < 50:
            reasons.append(f"부채율 {debt_ratio:.1f}% - 양호한 재무")
            score += 0.5

        # 배당금 평가
        if dividend_yield > 2:
            reasons.append(f"배당율 {dividend_yield:.2f}% - 안정적 배당")
            score += 1

        confidence = min(score / max_score, 1.0)

        if confidence > 0.7:
            recommendation = "BUY"
        elif confidence > 0.4:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        logger.info(f"Buffett Strategy for {symbol}: {recommendation} (confidence={confidence:.2f})")

        return InvestorSignal(
            investor_type=InvestorType.VALUE_INVESTOR,
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            timeline="장기",
            risk_level="낮음",
        )


class LynchStrategy:
    """피터 린치 - 성장투자"""

    @staticmethod
    def analyze(stock_data: Dict) -> InvestorSignal:
        """
        피터 린치 전략 분석

        - 빠른 성장 기업
        - PEG Ratio (PER / 성장률) < 1
        - 시장 기회 큼
        """
        symbol = stock_data.get("symbol", "UNKNOWN")
        earnings_growth = _safe_float(stock_data.get("earnings_growth"), 0.0)
        revenue_growth = _safe_float(stock_data.get("revenue_growth"), 0.0)
        pe_ratio = _safe_float(stock_data.get("pe_ratio"))
        industry_growth = _safe_float(stock_data.get("industry_growth"), 0.0)

        reasons = []
        score = 0.0
        max_score = 5

        # 성장률 평가
        if earnings_growth > 25:
            reasons.append(f"실적 성장 {earnings_growth:.1f}% - 강한 성장")
            score += 1.5
        elif earnings_growth > 15:
            reasons.append(f"실적 성장 {earnings_growth:.1f}% - 우수한 성장")
            score += 1
        elif earnings_growth > 0:
            reasons.append(f"실적 성장 {earnings_growth:.1f}% - 양호한 성장")
            score += 0.5

        # 매출 성장
        if revenue_growth > 20:
            reasons.append(f"매출 성장 {revenue_growth:.1f}% - 강한 수요")
            score += 1
        elif revenue_growth > 10:
            reasons.append(f"매출 성장 {revenue_growth:.1f}% - 우수한 수요")
            score += 0.5

        if pe_ratio is not None and earnings_growth > 0:
            peg_ratio = pe_ratio / earnings_growth
            if peg_ratio < 1:
                reasons.append(f"PEG {peg_ratio:.2f} - 저평가 성장주")
                score += 1
            elif peg_ratio < 2:
                reasons.append(f"PEG {peg_ratio:.2f} - 적절한 가격의 성장주")
                score += 0.5

        # 산업 성장성
        if earnings_growth > industry_growth:
            reasons.append(f"산업 성장률 {industry_growth:.1f}% 초과 성장")
            score += 1

        confidence = min(score / max_score, 1.0)

        if confidence > 0.7:
            recommendation = "BUY"
        elif confidence > 0.4:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        logger.info(f"Lynch Strategy for {symbol}: {recommendation} (confidence={confidence:.2f})")

        return InvestorSignal(
            investor_type=InvestorType.GROWTH_INVESTOR,
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            timeline="중기",
            risk_level="높음",
        )


class MinervaStrategy:
    """미너바니 - 모멘텀 투자"""

    @staticmethod
    def analyze(stock_data: Dict) -> InvestorSignal:
        """
        미너바니 전략 분석

        - 가격 모멘텀 추적
        - 기술적 강세 신호
        - 상승 추세 확인
        """
        symbol = stock_data.get("symbol", "UNKNOWN")
        price_change_52w = _safe_float(stock_data.get("price_change_52w"), 0.0)  # %
        price_change_6m = _safe_float(stock_data.get("price_change_6m"), 0.0)  # %
        momentum_score = _safe_float(stock_data.get("momentum_score"), 0.0)  # 0-100
        rsi = _safe_float(stock_data.get("rsi"), 50.0)  # 0-100
        volume_trend = _safe_float(stock_data.get("volume_trend"), 0.0)  # %

        reasons = []
        score = 0.0
        max_score = 5

        # 52주 모멘텀
        if price_change_52w > 50:
            reasons.append(f"52주 수익률 {price_change_52w:.1f}% - 강한 상승세")
            score += 1.5
        elif price_change_52w > 20:
            reasons.append(f"52주 수익률 {price_change_52w:.1f}% - 상승 트렌드")
            score += 1

        # 6개월 모멘텀
        if price_change_6m > 20:
            reasons.append(f"6개월 수익률 {price_change_6m:.1f}% - 최근 강세")
            score += 1
        elif price_change_6m > 0:
            reasons.append(f"6개월 수익률 {price_change_6m:.1f}% - 약한 상승")
            score += 0.5

        # RSI (상대강도지수)
        if 50 < rsi < 70:
            reasons.append(f"RSI {rsi:.0f} - 매수 신호")
            score += 1
        elif rsi >= 70:
            reasons.append(f"RSI {rsi:.0f} - 과매수 주의")
            score += 0.3

        # 모멘텀 점수
        if momentum_score > 70:
            reasons.append(f"모멘텀 {momentum_score:.0f} - 강한 상승")
            score += 1
        elif momentum_score > 50:
            reasons.append(f"모멘텀 {momentum_score:.0f} - 긍정적")
            score += 0.5

        # 거래량 증가
        if volume_trend > 20:
            reasons.append(f"거래량 증가 {volume_trend:.1f}% - 매수세 강함")
            score += 0.5

        confidence = min(score / max_score, 1.0)

        if confidence > 0.7:
            recommendation = "BUY"
        elif confidence > 0.4:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        logger.info(f"Minerva Strategy for {symbol}: {recommendation} (confidence={confidence:.2f})")

        return InvestorSignal(
            investor_type=InvestorType.MOMENTUM_INVESTOR,
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            timeline="단기",
            risk_level="높음",
        )


class DividendStrategy:
    """제임스 오셀러 - 배당 투자"""

    @staticmethod
    def analyze(stock_data: Dict) -> InvestorSignal:
        """
        배당 투자 전략

        - 높은 배당율
        - 안정적 배당 성장
        - 지속 가능한 배당
        """
        symbol = stock_data.get("symbol", "UNKNOWN")
        dividend_yield = _safe_float(stock_data.get("dividend_yield"), 0.0)  # %
        payout_ratio = _safe_float(stock_data.get("payout_ratio"), 0.0)  # %
        dividend_growth = _safe_float(stock_data.get("dividend_growth"), 0.0)  # %
        years_of_dividend = _safe_float(stock_data.get("years_of_dividend"), 0.0)
        fcf = _safe_float(stock_data.get("fcf"), 0.0)  # 잉여현금흐름

        reasons = []
        score = 0.0
        max_score = 5

        # 배당율
        if dividend_yield > 4:
            reasons.append(f"배당율 {dividend_yield:.2f}% - 높은 배당")
            score += 1.5
        elif dividend_yield > 2.5:
            reasons.append(f"배당율 {dividend_yield:.2f}% - 우수한 배당")
            score += 1
        elif dividend_yield > 0:
            reasons.append(f"배당율 {dividend_yield:.2f}% - 배당 제공")
            score += 0.5

        # 배당 성장
        if dividend_growth > 10:
            reasons.append(f"배당 성장 {dividend_growth:.1f}% - 강한 성장")
            score += 1
        elif dividend_growth > 5:
            reasons.append(f"배당 성장 {dividend_growth:.1f}% - 안정적 성장")
            score += 0.5

        # 배당 지속성 (배당 지급 연수)
        if years_of_dividend >= 20:
            reasons.append(f"연속 배당 {years_of_dividend}년 - 매우 안정적")
            score += 1.5
        elif years_of_dividend >= 10:
            reasons.append(f"연속 배당 {years_of_dividend}년 - 안정적")
            score += 1
        elif years_of_dividend >= 5:
            reasons.append(f"연속 배당 {years_of_dividend}년 - 양호")
            score += 0.5

        # Payout Ratio (배당가능성)
        if payout_ratio < 60:
            reasons.append(f"배당성향 {payout_ratio:.0f}% - 지속 가능")
            score += 1
        elif payout_ratio < 80:
            reasons.append(f"배당성향 {payout_ratio:.0f}% - 양호")
            score += 0.5

        # 잉여현금흐름
        if fcf > 0:
            reasons.append("잉여현금흐름 양수 - 배당 뒷받침")
            score += 0.5

        confidence = min(score / max_score, 1.0)

        if confidence > 0.7:
            recommendation = "BUY"
        elif confidence > 0.4:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        logger.info(f"Dividend Strategy for {symbol}: {recommendation} (confidence={confidence:.2f})")

        return InvestorSignal(
            investor_type=InvestorType.DIVIDEND_INVESTOR,
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            timeline="장기",
            risk_level="낮음",
        )


class InvestorStrategyEngine:
    """유명 투자자 전략 통합 엔진"""

    def __init__(self):
        self.logger = logger
        self.strategies = {
            InvestorType.VALUE_INVESTOR: BuffettStrategy,
            InvestorType.GROWTH_INVESTOR: LynchStrategy,
            InvestorType.MOMENTUM_INVESTOR: MinervaStrategy,
            InvestorType.DIVIDEND_INVESTOR: DividendStrategy,
        }
        self.analysis_history = []

    def analyze_all_strategies(self, stock_data: Dict) -> Dict[str, InvestorSignal]:
        """모든 전략으로 분석"""
        results = {}

        for investor_type, strategy_class in self.strategies.items():
            try:
                signal = strategy_class.analyze(stock_data)
                results[investor_type.value] = signal
                self.analysis_history.append(signal)
            except Exception as e:
                self.logger.error(f"Error in {investor_type.value}: {e!s}")

        return results

    def get_consensus_recommendation(self, stock_data: Dict) -> Dict:
        """투자자들의 합의 의견"""
        results = self.analyze_all_strategies(stock_data)

        buy_count = sum(1 for s in results.values() if s.recommendation == "BUY")
        hold_count = sum(1 for s in results.values() if s.recommendation == "HOLD")
        sell_count = sum(1 for s in results.values() if s.recommendation == "SELL")

        avg_confidence = sum(s.confidence for s in results.values()) / len(results)

        # 합의 도출
        if buy_count >= 3:
            consensus = "강한 매수"
        elif buy_count >= 2:
            consensus = "매수"
        elif hold_count >= 2:
            consensus = "보유"
        elif sell_count >= 2:
            consensus = "매도"
        else:
            consensus = "약한 매도"

        return {
            "consensus": consensus,
            "buy_count": buy_count,
            "hold_count": hold_count,
            "sell_count": sell_count,
            "avg_confidence": avg_confidence,
            "detailed_opinions": results,
        }

    def get_top_recommendations(self, stocks_data: List[Dict], top_n: int = 10) -> List[Dict]:
        """상위 추천주 조회"""
        recommendations = []

        for stock in stocks_data:
            consensus = self.get_consensus_recommendation(stock)

            recommendations.append(
                {
                    "symbol": stock.get("symbol"),
                    "company_name": stock.get("company_name"),
                    "price": stock.get("price"),
                    "consensus": consensus["consensus"],
                    "confidence": consensus["avg_confidence"],
                    "buy_count": consensus["buy_count"],
                    "opinions": consensus["detailed_opinions"],
                }
            )

        # 신뢰도로 정렬
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)

        self.logger.info(f"Generated {len(recommendations)} recommendations, top {top_n} selected")

        return recommendations[:top_n]

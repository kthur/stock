"""Strategy Engine - 매매 전략 및 최적화"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable
import logging

logger = logging.getLogger(__name__)


class TradeSignal(Enum):
    """매매 신호"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class StrategyResult:
    """전략 실행 결과"""
    symbol: str
    signal: TradeSignal
    price: float
    confidence: float  # 0.0 ~ 1.0
    reason: str
    timestamp: datetime


class HybridStrategyEngine:
    """하이브리드 전략 엔진 - 기술적 분석 + 감정 분석"""
    
    def __init__(self):
        self.logger = logger
        self.results_history: List[StrategyResult] = []
        self.subscribers: List[Callable] = []
        
        # 전략 파라미터
        self.price_threshold = 0.02  # 2% 변동
        self.volume_threshold = 1000000  # 최소 거래량
    
    def subscribe(self, callback: Callable):
        """전략 신호 구독"""
        self.subscribers.append(callback)
    
    def analyze(self, symbol: str, market_data: Dict, news_sentiment: float) -> StrategyResult:
        """
        종합 분석 수행
        market_data: {price, volume, bid, ask}
        news_sentiment: -1.0 ~ 1.0
        """
        price = market_data.get('price', 0)
        volume = market_data.get('volume', 0)
        bid = market_data.get('bid', 0)
        ask = market_data.get('ask', 0)
        
        # 거래량 확인
        if volume < self.volume_threshold:
            signal = TradeSignal.HOLD
            confidence = 0.3
            reason = "Low volume"
        else:
            # 스프레드 분석
            spread_ratio = (ask - bid) / bid if bid > 0 else 0
            
            # 감정 분석 가중치
            sentiment_weight = 0.6
            technical_weight = 0.4
            
            # 기술적 신호 (간단한 스프레드 기반)
            if spread_ratio < 0.001:  # 좋은 스프레드
                technical_signal = TradeSignal.BUY if price > bid * 1.01 else TradeSignal.HOLD
                technical_score = 0.7
            else:
                technical_signal = TradeSignal.HOLD
                technical_score = 0.5
            
            # 감정 신호
            if news_sentiment > 0.5:
                sentiment_signal = TradeSignal.BUY
                sentiment_score = 0.8
            elif news_sentiment < -0.5:
                sentiment_signal = TradeSignal.SELL
                sentiment_score = 0.8
            else:
                sentiment_signal = TradeSignal.HOLD
                sentiment_score = 0.5
            
            # 최종 신호 결정
            combined_score = (sentiment_score * sentiment_weight + 
                            technical_score * technical_weight)
            confidence = combined_score
            
            if combined_score > 0.7:
                if sentiment_signal == TradeSignal.BUY or technical_signal == TradeSignal.BUY:
                    signal = TradeSignal.BUY
                    reason = "Strong buy signal (sentiment + technical)"
                else:
                    signal = TradeSignal.HOLD
                    reason = "Conflicting signals"
            elif combined_score < 0.4:
                signal = TradeSignal.SELL
                reason = "Weak signals detected"
            else:
                signal = TradeSignal.HOLD
                reason = "Neutral market"
        
        result = StrategyResult(
            symbol=symbol,
            signal=signal,
            price=price,
            confidence=confidence,
            reason=reason,
            timestamp=datetime.now()
        )
        
        self.results_history.append(result)
        
        # 구독자에게 알림
        for callback in self.subscribers:
            callback(result)
        
        self.logger.info(f"Strategy result: {result}")
        return result


class OptimizationEngine:
    """최적화 엔진 - 슬리피지 및 손익 기반 파라미터 튜닝"""
    
    def __init__(self, strategy_engine: HybridStrategyEngine):
        self.strategy_engine = strategy_engine
        self.logger = logger
        self.optimization_history = []
        
        # 성과 메트릭
        self.total_trades = 0
        self.winning_trades = 0
        self.total_slippage = 0.0
    
    def record_trade_result(self, signal: TradeSignal, entry_price: float, 
                           exit_price: float, quantity: int):
        """트레이드 결과 기록"""
        if signal == TradeSignal.BUY:
            slippage = abs(entry_price - exit_price) / entry_price
        else:
            slippage = abs(exit_price - entry_price) / entry_price
        
        pnl = (exit_price - entry_price) * quantity
        is_win = pnl > 0
        
        self.total_trades += 1
        if is_win:
            self.winning_trades += 1
        self.total_slippage += slippage
        
        self.logger.info(f"Trade recorded: PnL={pnl}, slippage={slippage:.4f}")
    
    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    def get_avg_slippage(self) -> float:
        """평균 슬리피지 계산"""
        if self.total_trades == 0:
            return 0.0
        return self.total_slippage / self.total_trades
    
    def optimize_parameters(self) -> Dict:
        """파라미터 자동 튜닝"""
        win_rate = self.get_win_rate()
        avg_slippage = self.get_avg_slippage()
        
        optimization = {
            'win_rate': win_rate,
            'avg_slippage': avg_slippage,
            'total_trades': self.total_trades,
            'timestamp': datetime.now()
        }
        
        # 파라미터 조정 로직
        if win_rate < 0.4:
            self.strategy_engine.volume_threshold *= 1.1
            self.logger.warning(f"Adjusted volume threshold to {self.strategy_engine.volume_threshold}")
        
        if avg_slippage > 0.01:  # 1% 이상 슬리피지
            self.logger.warning(f"High slippage detected: {avg_slippage:.4f}")
        
        self.optimization_history.append(optimization)
        return optimization

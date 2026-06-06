"""Strategy Engine - 매매 전략 및 최적화"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable, Any
import logging

from src.utils import EventBus

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
    
    def __init__(
        self,
        event_bus: EventBus | None = None,
        ml_engine: Any = None,
        sentiment_weight: float = 0.5,
        technical_weight: float = 0.3,
        ml_weight: float = 0.2,
        spread_threshold: float = 0.001,
        buy_price_threshold: float = 1.01,
        sell_threshold: float = 0.4,
    ) -> None:
        self.logger = logger
        self.results_history: List[StrategyResult] = []
        self.subscribers: List[Callable] = []
        self.event_bus = event_bus
        self.ml_engine = ml_engine
        
        self.price_threshold = 0.02
        self.volume_threshold = 1000000
        self.sentiment_weight = sentiment_weight
        self.technical_weight = technical_weight
        self.ml_weight = ml_weight
        self.spread_threshold = spread_threshold
        self.buy_price_threshold = buy_price_threshold
        self.sell_threshold = sell_threshold
    
    def subscribe(self, callback: Callable) -> None:
        """전략 신호 구독"""
        self.subscribers.append(callback)
    
    def analyze(self, symbol: str, market_data: Dict, news_sentiment: float, price_bars: List[Any] = None) -> StrategyResult:
        """
        종합 분석 수행
        market_data: {price, volume, bid, ask}
        news_sentiment: -1.0 ~ 1.0
        price_bars: ML 예측을 위한 과거 주가 데이터
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
            spread_ratio = (ask - bid) / bid if bid > 0 else 0
            
            if spread_ratio < self.spread_threshold:
                technical_signal = TradeSignal.BUY if price > bid * self.buy_price_threshold else TradeSignal.HOLD
                technical_score = 0.7
            else:
                technical_signal = TradeSignal.HOLD
                technical_score = 0.5
            
            if news_sentiment > 0.5:
                sentiment_signal = TradeSignal.BUY
                sentiment_score = 0.8
            elif news_sentiment < -0.5:
                sentiment_signal = TradeSignal.SELL
                sentiment_score = 0.8
            else:
                sentiment_signal = TradeSignal.HOLD
                sentiment_score = 0.5
                
            ml_score = 0.5
            if self.ml_engine and price_bars:
                try:
                    # ML Engine 훈련 (만약 훈련 안되어 있다면 내부적으로 처리, 여기서는 단순 예측 호출)
                    prob = self.ml_engine.predict_prob(price_bars)
                    ml_score = prob
                except Exception as e:
                    self.logger.warning(f"ML Prediction failed: {e}")
            
            combined_score = (sentiment_score * self.sentiment_weight +
                            technical_score * self.technical_weight +
                            ml_score * self.ml_weight)
            confidence = combined_score
            
            if combined_score > 0.7:
                if sentiment_signal == TradeSignal.BUY or technical_signal == TradeSignal.BUY:
                    signal = TradeSignal.BUY
                    reason = "Strong buy signal (sentiment + technical)"
                else:
                    signal = TradeSignal.HOLD
                    reason = "Conflicting signals"
            elif combined_score < self.sell_threshold:
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
        
        # 이벤트 버스로 전송
        if self.event_bus:
            self.event_bus.publish("strategy_signal", result)
            
        # 구독자에게 알림 (하위 호환성)
        for callback in self.subscribers:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Strategy callback error: {e}")
        
        self.logger.info(f"Strategy result: {result}")
        return result


class OptimizationEngine:
    """최적화 엔진 - 슬리피지 및 손익 기반 파라미터 튜닝"""
    
    def __init__(self, strategy_engine: HybridStrategyEngine) -> None:
        self.strategy_engine = strategy_engine
        self.logger = logger
        self.optimization_history: list = []
        
        # 성과 메트릭
        self.total_trades = 0
        self.winning_trades = 0
        self.total_slippage = 0.0
    
    def record_trade_result(self, signal: TradeSignal, entry_price: float, 
                           exit_price: float, quantity: int) -> None:
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
        
        if win_rate < 0.4:
            self.strategy_engine.volume_threshold = int(self.strategy_engine.volume_threshold * 1.1)
            self.logger.warning(f"Adjusted volume threshold to {self.strategy_engine.volume_threshold}")
        
        if avg_slippage > 0.01:
            self.logger.warning(f"High slippage detected: {avg_slippage:.4f}")
        
        self.optimization_history.append(optimization)
        return optimization

"""Strategy Engine - 매매 전략 및 최적화"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
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
    
    SIGNAL_NAMES = ["sentiment", "technical", "ml", "rl", "darkpool", "llm"]
    
    def __init__(
        self,
        event_bus: EventBus | None = None,
        ml_engine: Any = None,
        rl_engine: Any = None,
        alt_client: Any = None,
        darkpool: Any = None,
        llm_earnings: Any = None,
        stat_arb: Any = None,
        hft_engine: Any = None,
        sentiment_weight: float = 0.3,
        technical_weight: float = 0.2,
        ml_weight: float = 0.2,
        rl_weight: float = 0.1,
        darkpool_weight: float = 0.1,
        llm_weight: float = 0.1,
        spread_threshold: float = 0.001,
        buy_price_threshold: float = 1.01,
        sell_threshold: float = 0.4,
        weight_adaptation_rate: float = 0.05,
        weight_adaptation_window: int = 50,
    ) -> None:
        self.logger = logger
        self.results_history: List[StrategyResult] = []
        self.subscribers: List[Callable] = []
        self.event_bus = event_bus
        self.ml_engine = ml_engine
        self.rl_engine = rl_engine
        self.alt_client = alt_client
        self.darkpool = darkpool
        self.llm_earnings = llm_earnings
        self.stat_arb = stat_arb
        self.hft_engine = hft_engine
        
        self.price_threshold = 0.02
        self.volume_threshold = 1000000
        self.sentiment_weight = sentiment_weight
        self.technical_weight = technical_weight
        self.ml_weight = ml_weight
        self.rl_weight = rl_weight
        self.darkpool_weight = darkpool_weight
        self.llm_weight = llm_weight
        self.spread_threshold = spread_threshold
        self.buy_price_threshold = buy_price_threshold
        self.sell_threshold = sell_threshold
        self.weight_adaptation_rate = weight_adaptation_rate
        self.weight_adaptation_window = weight_adaptation_window
        
        self._signal_performance: Dict[str, List[bool]] = {s: [] for s in self.SIGNAL_NAMES}
        self._signal_scores: Dict[str, float] = {}
    
    def subscribe(self, callback: Callable) -> None:
        """전략 신호 구독"""
        self.subscribers.append(callback)
    
    def analyze(self, symbol: str, market_data: Dict, news_sentiment: float, price_bars: Optional[List[Any]] = None) -> StrategyResult:
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
                    prob = self.ml_engine.predict_prob(price_bars)
                    ml_score = prob
                except Exception as e:
                    self.logger.warning(f"ML Prediction failed: {e}")
            
            rl_score = 0.5
            rl_action = "HOLD"
            alt_regime = {}
            if self.alt_client:
                alt_regime = self.alt_client.get_market_regime()
                
            if self.rl_engine:
                try:
                    rsi_val = 50.0
                    macd_val = 0.0
                    if price_bars and len(price_bars) > 15:
                        closes = [b.close for b in price_bars if hasattr(b, 'close')]
                        if len(closes) > 15:
                            gains, losses = 0.0, 0.0
                            for i in range(len(closes) - 14, len(closes)):
                                diff = closes[i] - closes[i-1]
                                if diff > 0:
                                    gains += diff
                                else:
                                    losses -= diff
                            avg_gain = gains / 14
                            avg_loss = losses / 14
                            if avg_loss != 0:
                                rs = avg_gain / avg_loss
                                rsi_val = 100.0 - (100.0 / (1.0 + rs))
                            else:
                                rsi_val = 100.0 if avg_gain > 0 else 50.0
                            ema12 = sum(closes[-12:]) / 12
                            ema26 = sum(closes[-26:]) / 26 if len(closes) >= 26 else ema12
                            macd_val = ema12 - ema26
                    state = {
                        "vix": alt_regime.get("vix", 20.0),
                        "rsi": rsi_val,
                        "macd": macd_val,
                        "trend_strength": technical_score
                    }
                    rl_res = self.rl_engine.get_action(state)
                    rl_action = rl_res["action"]
                    # Map action to score: BUY -> 1.0, SELL -> 0.0, HOLD -> 0.5
                    if rl_action == "BUY":
                        rl_score = 1.0
                    elif rl_action == "SELL":
                        rl_score = 0.0
                except Exception as e:
                    self.logger.warning(f"RL Action failed: {e}")
                    
            darkpool_score = 0.5
            if self.darkpool:
                dp_res = self.darkpool.fetch_darkpool_activity(symbol)
                if dp_res.get("is_accumulation"):
                    darkpool_score = 0.9
                elif dp_res.get("is_distribution"):
                    darkpool_score = 0.1
                    
            llm_score = 0.5
            if self.llm_earnings:
                if abs(news_sentiment) > 0.3:
                    llm_direction = "POSITIVE" if news_sentiment > 0 else "NEGATIVE"
                    transcript = f"최근 뉴스 심리가 {llm_direction}으로 {abs(news_sentiment)*100:.0f}% 수준입니다."
                    llm_res = self.llm_earnings.analyze_earnings_call(symbol, transcript)
                    if llm_res.get("guidance") == "POSITIVE":
                        llm_score = 0.9
                    elif llm_res.get("guidance") == "NEGATIVE":
                        llm_score = 0.1

            combined_score = (sentiment_score * self.sentiment_weight +
                            technical_score * self.technical_weight +
                            ml_score * self.ml_weight +
                            rl_score * self.rl_weight +
                            darkpool_score * self.darkpool_weight +
                            llm_score * self.llm_weight)
            
            raw_scores = {
                "sentiment": sentiment_score,
                "technical": technical_score,
                "ml": ml_score,
                "rl": rl_score,
                "darkpool": darkpool_score,
                "llm": llm_score,
            }
            
            regime = alt_regime or {}
            if regime.get("is_high_volatility"):
                adjusted = {
                    "sentiment": self.sentiment_weight * 0.8,
                    "technical": self.technical_weight * 1.5,
                    "ml": self.ml_weight * 0.7,
                    "rl": self.rl_weight * 1.3,
                    "darkpool": self.darkpool_weight * 1.2,
                    "llm": self.llm_weight * 0.8,
                }
                total_adj = sum(adjusted.values())
                if total_adj > 0:
                    weights = {k: v / total_adj for k, v in adjusted.items()}
                    combined_score = sum(raw_scores[k] * weights[k] for k in self.SIGNAL_NAMES)
            
            confidence = combined_score
            
            if combined_score > 0.7:
                if sentiment_signal == TradeSignal.BUY or technical_signal == TradeSignal.BUY:
                    signal = TradeSignal.BUY
                    reason = "Strong buy signal (sentiment + technical + AI + DarkPool + LLM)"
                else:
                    signal = TradeSignal.HOLD
                    reason = "Conflicting signals"
            elif combined_score < self.sell_threshold:
                signal = TradeSignal.SELL
                reason = "Weak signals detected"
            else:
                signal = TradeSignal.HOLD
                reason = "Neutral market"

            # Options Hedging Logic: 
            # If we hold the stock (assumed by neutral/buy but high VIX), recommend Protective Put
            if alt_regime and alt_regime.get("is_high_volatility") and signal != TradeSignal.SELL:
                reason += " | Recommend Protective Put (High VIX)"
                
            # Stat Arb (Pairs Trading) Override
            if self.stat_arb and price_bars and len(price_bars) > 30:
                price_dict: Dict[str, List[float]] = {}
                closes = [b.close for b in price_bars if hasattr(b, 'close')]
                if closes:
                    price_dict[symbol] = closes
                    for sym, pos in getattr(getattr(self, 'portfolio', None), 'positions', {}).items():
                        price_dict[sym] = closes[-min(len(closes), 30):]
                    pairs = self.stat_arb.find_cointegrated_pairs(price_dict)
                    for p in pairs:
                        if symbol in p["pair"]:
                            reason += f" | Stat Arb: {p['signal']} (z={p['z_score']})"
                        
            # Execute HFT if available and signal is strong
            if self.hft_engine and signal != TradeSignal.HOLD:
                self.hft_engine.execute_micro_order(symbol, signal.name, 100)
                reason += " | (Executed via HFT Engine)"
        
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

    def record_signal_outcome(self, signal_name: str, was_correct: bool) -> None:
        if signal_name not in self._signal_performance:
            return
        self._signal_performance[signal_name].append(was_correct)
        if len(self._signal_performance[signal_name]) > self.weight_adaptation_window * 2:
            self._signal_performance[signal_name] = self._signal_performance[signal_name][-self.weight_adaptation_window:]
        if len(self.results_history) % self.weight_adaptation_window == 0:
            self._adapt_weights()

    def _adapt_weights(self) -> None:
        accuracies = {}
        for name in self.SIGNAL_NAMES:
            perf = self._signal_performance.get(name, [])
            if len(perf) >= 10:
                accuracies[name] = sum(perf) / len(perf)
        if len(accuracies) < 3:
            return
        avg_acc = sum(accuracies.values()) / len(accuracies)
        weight_map = {
            "sentiment": "sentiment_weight",
            "technical": "technical_weight",
            "ml": "ml_weight",
            "rl": "rl_weight",
            "darkpool": "darkpool_weight",
            "llm": "llm_weight",
        }
        for name, acc in accuracies.items():
            attr = weight_map.get(name)
            if attr is None:
                continue
            current = getattr(self, attr)
            if acc > avg_acc:
                setattr(self, attr, current * (1.0 + self.weight_adaptation_rate))
            else:
                setattr(self, attr, current * (1.0 - self.weight_adaptation_rate))
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        total = (self.sentiment_weight + self.technical_weight +
                 self.ml_weight + self.rl_weight +
                 self.darkpool_weight + self.llm_weight)
        if total == 0:
            return
        self.sentiment_weight /= total
        self.technical_weight /= total
        self.ml_weight /= total
        self.rl_weight /= total
        self.darkpool_weight /= total
        self.llm_weight /= total
        self.logger.info(
            f"Weights adapted: sentiment={self.sentiment_weight:.3f} "
            f"technical={self.technical_weight:.3f} ml={self.ml_weight:.3f} "
            f"rl={self.rl_weight:.3f} darkpool={self.darkpool_weight:.3f} "
            f"llm={self.llm_weight:.3f}"
        )


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
                           exit_price: float, quantity: int,
                           signal_name: str | None = None) -> None:
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
        
        if signal_name and is_win:
            self.strategy_engine.record_signal_outcome(signal_name, True)
        elif signal_name:
            self.strategy_engine.record_signal_outcome(signal_name, False)
        
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
        
        self.strategy_engine._adapt_weights()
        
        self.optimization_history.append(optimization)
        return optimization

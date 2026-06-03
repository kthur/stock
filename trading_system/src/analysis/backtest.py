"""Backtesting Engine - 전략 백테스트"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Callable
import logging
import itertools

logger = logging.getLogger(__name__)


@dataclass
class PriceBar:
    """가격 바 (OHLCV)"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class BacktestTrade:
    """백테스트 거래"""
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    direction: str = "LONG"
    duration: timedelta = field(default_factory=lambda: timedelta())
    
    def __post_init__(self):
        self.duration = self.exit_date - self.entry_date


@dataclass
class BacktestResult:
    """백테스트 결과"""
    symbol: str
    trades: List[BacktestTrade]
    total_return: float
    total_return_pct: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_fees: float
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    equity_curve: List[float] = None
    price_curve: List[float] = None
    dates: List[datetime] = None


class BacktestEngine:
    
    POSITION_SIZE_FRACTION = 0.95
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.logger = logger
        self.fee_pct = 0.001
        
    def run_backtest(self, symbol: str, price_bars: List[PriceBar],
                    strategy_func, target_period_bars: int = None,
                    allow_short: bool = False) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            symbol: 종목
            price_bars: 가격 바 데이터
            strategy_func: 전략 함수 (가격->신호)
            target_period_bars: 성능 측정 대상 기간 바 수 (과거 데이터는 warm-up 용)
            allow_short: 공매도(Short Selling) 허용 여부
        
        Returns:
            BacktestResult: 백테스트 결과
        """
        capital = self.initial_capital
        position = 0  # 양수: 롱 포지션 수량, 음수: 숏 포지션 수량
        entry_price = 0
        trades: List[BacktestTrade] = []
        equity_curve = [capital]
        
        for i, bar in enumerate(price_bars):
            # 전략 신호 생성
            signal = strategy_func(price_bars[:i+1])
            
            # --- 롱 진입 (Neutral 상태) ---
            if signal == "BUY" and position == 0:
                if capital >= bar.close:
                    position = int(capital * self.POSITION_SIZE_FRACTION / bar.close)
                    entry_price = bar.close
                    capital -= position * bar.close * (1 + self.fee_pct)
                    self.logger.debug(f"{bar.timestamp}: BUY (Long Entry) {position} @ {bar.close}")
            
            # --- 롱 청산 (및 allow_short=True 시 숏 스위칭) ---
            elif signal == "SELL" and position > 0:
                exit_price = bar.close
                pnl = (exit_price - entry_price) * position
                fees = position * exit_price * self.fee_pct
                
                capital += position * exit_price * (1 - self.fee_pct)
                
                trade = BacktestTrade(
                    entry_date=price_bars[i-1].timestamp if i > 0 else bar.timestamp,
                    entry_price=entry_price,
                    exit_date=bar.timestamp,
                    exit_price=exit_price,
                    quantity=position,
                    pnl=pnl - fees,
                    pnl_pct=((exit_price - entry_price) / entry_price) * 100,
                    direction="LONG"
                )
                trades.append(trade)
                self.logger.debug(f"{bar.timestamp}: SELL (Long Exit) {position} @ {exit_price}, PnL={pnl-fees:.2f}")
                
                # 숏으로 스위칭 (Reverse)
                if allow_short:
                    qty = int(capital * self.POSITION_SIZE_FRACTION / bar.close)
                    position = -qty
                    entry_price = bar.close
                    capital += qty * bar.close * (1 - self.fee_pct)
                    self.logger.debug(f"{bar.timestamp}: SELL (Short Entry - Reverse) {qty} @ {bar.close}")
                else:
                    position = 0
            
            # --- 숏 청산 (및 롱 스위칭) ---
            elif signal == "BUY" and position < 0 and allow_short:
                exit_price = bar.close
                qty = abs(position)
                pnl = (entry_price - exit_price) * qty
                fees = qty * exit_price * self.fee_pct
                
                capital -= qty * exit_price * (1 + self.fee_pct)
                
                trade = BacktestTrade(
                    entry_date=price_bars[i-1].timestamp if i > 0 else bar.timestamp,
                    entry_price=entry_price,
                    exit_date=bar.timestamp,
                    exit_price=exit_price,
                    quantity=-qty,
                    pnl=pnl - fees,
                    pnl_pct=((entry_price - exit_price) / entry_price) * 100,
                    direction="SHORT"
                )
                trades.append(trade)
                self.logger.debug(f"{bar.timestamp}: BUY (Short Exit/Cover) {qty} @ {exit_price}, PnL={pnl-fees:.2f}")
                
                # 롱으로 스위칭 (Reverse)
                if capital >= bar.close:
                    position = int(capital * self.POSITION_SIZE_FRACTION / bar.close)
                    entry_price = bar.close
                    capital -= position * bar.close * (1 + self.fee_pct)
                    self.logger.debug(f"{bar.timestamp}: BUY (Long Entry - Reverse) {position} @ {bar.close}")
                else:
                    position = 0
            
            # --- 숏 진입 (Neutral 상태) ---
            elif signal == "SELL" and position == 0 and allow_short:
                qty = int(capital * self.POSITION_SIZE_FRACTION / bar.close)
                position = -qty
                entry_price = bar.close
                capital += qty * bar.close * (1 - self.fee_pct)
                self.logger.debug(f"{bar.timestamp}: SELL (Short Entry) {qty} @ {bar.close}")
            
            # 포지션 가치 계산 및 누적
            position_value = position * bar.close
            total_value = capital + position_value
            equity_curve.append(total_value)
        
        # 최종 청산
        if position > 0:
            final_price = price_bars[-1].close
            pnl = (final_price - entry_price) * position
            fees = position * final_price * self.fee_pct
            capital += position * final_price * (1 - self.fee_pct)
            
            trade = BacktestTrade(
                entry_date=price_bars[-2].timestamp if len(price_bars) > 1 else price_bars[0].timestamp,
                entry_price=entry_price,
                exit_date=price_bars[-1].timestamp,
                exit_price=final_price,
                quantity=position,
                pnl=pnl - fees,
                pnl_pct=((final_price - entry_price) / entry_price) * 100,
                direction="LONG"
            )
            trades.append(trade)
        elif position < 0 and allow_short:
            final_price = price_bars[-1].close
            qty = abs(position)
            pnl = (entry_price - final_price) * qty
            fees = qty * final_price * self.fee_pct
            capital -= qty * final_price * (1 + self.fee_pct)
            
            trade = BacktestTrade(
                entry_date=price_bars[-2].timestamp if len(price_bars) > 1 else price_bars[0].timestamp,
                entry_price=entry_price,
                exit_date=price_bars[-1].timestamp,
                exit_price=final_price,
                quantity=-qty,
                pnl=pnl - fees,
                pnl_pct=((entry_price - final_price) / entry_price) * 100,
                direction="SHORT"
            )
            trades.append(trade)
        
        # 결과 계산
        if target_period_bars and target_period_bars < len(price_bars):
            target_start_idx = len(price_bars) - target_period_bars
            
            # target period 시작 시점 직전의 자산 가치
            initial_capital_target = equity_curve[target_start_idx - 1] if target_start_idx > 0 else equity_curve[0]
            final_capital_target = equity_curve[-1]
            
            total_return = final_capital_target - initial_capital_target
            total_return_pct = (total_return / initial_capital_target) * 100
            
            # target period 내에 완료된 거래만 필터링
            target_trades = []
            for t in trades:
                if t.exit_date >= price_bars[target_start_idx].timestamp:
                    target_trades.append(t)
            
            win_rate = self._calculate_win_rate(target_trades)
            profit_factor = self._calculate_profit_factor(target_trades)
            
            # target period 내의 mdd 및 sharpe ratio 계산
            target_equity_curve = equity_curve[target_start_idx:]
            max_drawdown = self._calculate_max_drawdown(target_equity_curve)
            sharpe_ratio = self._calculate_sharpe_ratio(target_equity_curve)
            
            # target period 용 데이터 슬라이싱
            dates = [b.timestamp for b in price_bars[target_start_idx:]]
            price_curve = [b.close for b in price_bars[target_start_idx:]]
            
            result = BacktestResult(
                symbol=symbol,
                trades=target_trades,
                total_return=total_return,
                total_return_pct=total_return_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_fees=0.0,  # 간소화
                start_date=price_bars[target_start_idx].timestamp,
                end_date=price_bars[-1].timestamp,
                initial_capital=initial_capital_target,
                final_capital=final_capital_target,
                equity_curve=target_equity_curve,
                price_curve=price_curve,
                dates=dates
            )
        else:
            final_capital = capital
            total_return = final_capital - self.initial_capital
            total_return_pct = (total_return / self.initial_capital) * 100
            
            win_rate = self._calculate_win_rate(trades)
            profit_factor = self._calculate_profit_factor(trades)
            max_drawdown = self._calculate_max_drawdown(equity_curve)
            sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
            
            total_fees = sum(
                (abs(trade.quantity) * trade.entry_price * self.fee_pct +
                 abs(trade.quantity) * trade.exit_price * self.fee_pct)
                for trade in trades
            )
            
            result = BacktestResult(
                symbol=symbol,
                trades=trades,
                total_return=total_return,
                total_return_pct=total_return_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_fees=total_fees,
                start_date=price_bars[0].timestamp,
                end_date=price_bars[-1].timestamp,
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                equity_curve=equity_curve,
                price_curve=[b.close for b in price_bars],
                dates=[b.timestamp for b in price_bars]
            )
        
        self.logger.info(f"Backtest completed for {symbol}: "
                        f"return={total_return_pct:.2f}%, "
                        f"trades={len(trades)}, "
                        f"win_rate={win_rate:.2%}")
        
        return result
    
    def _calculate_win_rate(self, trades: List[BacktestTrade]) -> float:
        """승률 계산"""
        if not trades:
            return 0
        
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        return winning_trades / len(trades)
    
    def _calculate_profit_factor(self, trades: List[BacktestTrade]) -> float:
        """이익 계수 계산"""
        if not trades:
            return 0
        
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl <= 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        
        return gross_profit / gross_loss
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0
        
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.02) -> float:
        """Sharpe Ratio 계산"""
        if len(equity_curve) < 2:
            return 0
        
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] 
                  for i in range(1, len(equity_curve))]
        
        if not returns:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0
        
        # 연율화 (252 거래일 기준)
        sharpe = ((avg_return - risk_free_rate / 252) / std_dev) * (252 ** 0.5)
        
        return sharpe
    
    def optimize_parameters(self, symbol: str, price_bars: List[PriceBar],
                           param_ranges: Dict) -> Dict:
        """파라미터 최적화"""
        best_result = None
        best_params = None
        best_return = -float('inf')
        
        self.logger.info("Starting parameter optimization...")
        
        # 간단한 그리드 서치
        for param_combo in self._generate_param_combos(param_ranges):
            def strategy(bars):
                # 파라미터 기반 전략 실행
                return self._simple_ma_strategy(bars, param_combo)
            
            result = self.run_backtest(symbol, price_bars, strategy)
            
            if result.total_return_pct > best_return:
                best_return = result.total_return_pct
                best_result = result
                best_params = param_combo
        
        self.logger.info(f"Optimization complete: best params={best_params}, "
                        f"best return={best_return:.2f}%")
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_return': best_return
        }
    
    def _generate_param_combos(self, param_ranges: Dict) -> List[Dict]:
        """파라미터 조합 생성"""
        keys = param_ranges.keys()
        values = [param_ranges[k] for k in keys]
        
        combos = []
        for combo in itertools.product(*values):
            combos.append(dict(zip(keys, combo)))
        
        return combos
    
    def _simple_ma_strategy(self, bars: List[PriceBar], params: Dict) -> str:
        """간단한 이동평균 전략"""
        if len(bars) < params.get('long_window', 50):
            return "HOLD"
        
        short_window = params.get('short_window', 20)
        long_window = params.get('long_window', 50)
        
        closes = [b.close for b in bars]
        
        short_ma = sum(closes[-short_window:]) / short_window
        long_ma = sum(closes[-long_window:]) / long_window
        
        if short_ma > long_ma:
            return "BUY"
        elif short_ma < long_ma:
            return "SELL"
        else:
            return "HOLD"

    def _rsi_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """RSI 과매도/과매수 전략"""
        if params is None: params = {}
        window = params.get('window', 14)
        buy_threshold = params.get('buy_threshold', 30)
        sell_threshold = params.get('sell_threshold', 70)
        
        if len(bars) <= window:
            return "HOLD"
            
        closes = [b.close for b in bars]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        recent_deltas = deltas[-window:]
        gains = sum(d for d in recent_deltas if d > 0)
        losses = sum(abs(d) for d in recent_deltas if d < 0)
        
        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
            
        if rsi < buy_threshold:
            return "BUY"
        elif rsi > sell_threshold:
            return "SELL"
        else:
            return "HOLD"
            
    def _macd_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """MACD 돌파 전략"""
        if params is None: params = {}
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        
        if len(bars) <= slow:
            return "HOLD"
            
        closes = [b.close for b in bars]
        
        # 지수이동평균 대신 단순이동평균 기반 간이 MACD
        fast_ma = sum(closes[-fast:]) / fast
        slow_ma = sum(closes[-slow:]) / slow
        macd = fast_ma - slow_ma
        
        prev_fast_ma = sum(closes[-(fast+1):-1]) / fast
        prev_slow_ma = sum(closes[-(slow+1):-1]) / slow
        prev_macd = prev_fast_ma - prev_slow_ma
        
        if prev_macd < 0 and macd > 0:
            return "BUY"
        elif prev_macd > 0 and macd < 0:
            return "SELL"
        else:
            return "HOLD"
            
    def _buffett_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """워렌 버핏 Proxy (가치투자/역발상): 200일선 아래 크게 하락하고 단기 과매도 시 매수"""
        if len(bars) < 200: return "HOLD"
        closes = [b.close for b in bars]
        ma200 = sum(closes[-200:]) / 200
        current_price = closes[-1]
        
        # RSI 14 간이 계산
        gains = sum(max(0, closes[i] - closes[i-1]) for i in range(-14, 0)) / 14
        losses = sum(max(0, closes[i-1] - closes[i]) for i in range(-14, 0)) / 14
        rsi = 100 - (100 / (1 + (gains / losses))) if losses > 0 else 50
        
        if current_price < ma200 * 0.9 and rsi < 30:
            return "BUY"
        elif current_price > ma200 or rsi > 70:
            return "SELL"
        return "HOLD"
        
    def _lynch_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """피터 린치 Proxy (성장/모멘텀): 50일 신고가 및 평균 거래량 돌파 시 매수"""
        if len(bars) < 50: return "HOLD"
        closes = [b.close for b in bars[-50:]]
        vols = [b.volume for b in bars[-50:]]
        
        highest_50 = max(closes[:-1])
        avg_vol = sum(vols[:-1]) / 49
        
        current_price = closes[-1]
        current_vol = vols[-1]
        
        if current_price > highest_50 and current_vol > avg_vol * 1.5:
            return "BUY"
        elif current_price < sum(closes[-20:])/20:
            return "SELL"
        return "HOLD"
        
    def _dalio_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """레이 달리오 Proxy (안정적 추세): 200일선 위에서 변동성이 적을 때 매수"""
        if len(bars) < 200: return "HOLD"
        closes = [b.close for b in bars]
        ma200 = sum(closes[-200:]) / 200
        current_price = closes[-1]
        
        # 20일 변동성(표준편차 대용: 단순 등락폭 평균)
        volatility = sum(abs(closes[i] - closes[i-1]) for i in range(-20, 0)) / 20
        avg_price20 = sum(closes[-20:]) / 20
        vol_ratio = volatility / avg_price20
        
        if current_price > ma200 and vol_ratio < 0.02:
            return "BUY"
        elif current_price < ma200:
            return "SELL"
        return "HOLD"

    def _trend_following_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """추세 추종(Trend Following): 가격이 200일선 위에 있고 단기 이평(20일)이 중기 이평(50일) 위에 있을 때 매수"""
        if len(bars) < 200: return "HOLD"
        closes = [b.close for b in bars]
        
        ma200 = sum(closes[-200:]) / 200
        ma50 = sum(closes[-50:]) / 50
        ma20 = sum(closes[-20:]) / 20
        current_price = closes[-1]
        
        if current_price > ma200 and ma20 > ma50:
            return "BUY"
        elif current_price < ma200 or ma20 < ma50:
            return "SELL"
        return "HOLD"
            
    def get_strategy_func(self, strategy_name: str) -> Callable:
        """이름으로 전략 함수 래퍼 반환"""
        name = strategy_name.upper()
        
        if name == "MA" or name == "이동평균선":
            return lambda bars: self._simple_ma_strategy(bars, {})
        elif name == "RSI":
            return lambda bars: self._rsi_strategy(bars, {})
        elif name == "MACD":
            return lambda bars: self._macd_strategy(bars, {})
        elif name == "TREND" or "추세" in strategy_name:
            return lambda bars: self._trend_following_strategy(bars, {})
        elif name == "BUFFETT" or "버핏" in strategy_name:
            return lambda bars: self._buffett_proxy_strategy(bars, {})
        elif name == "LYNCH" or "린치" in strategy_name:
            return lambda bars: self._lynch_proxy_strategy(bars, {})
        elif name == "DALIO" or "달리오" in strategy_name:
            return lambda bars: self._dalio_proxy_strategy(bars, {})
        else:
            self.logger.warning(f"Unknown strategy: {name}. Falling back to MA.")
            return lambda bars: self._simple_ma_strategy(bars, {})

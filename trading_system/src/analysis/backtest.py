"""Backtesting Engine - 전략 백테스트"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """주문 타입"""
    BUY = "BUY"
    SELL = "SELL"


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


class BacktestEngine:
    """백테스트 엔진"""
    
    def __init__(self, initial_capital: float = 1000000):
        """
        백테스트 엔진 초기화
        
        Args:
            initial_capital: 초기 자본금
        """
        self.initial_capital = initial_capital
        self.logger = logger
        self.fee_pct = 0.001  # 0.1% 수수료
        
    def run_backtest(self, symbol: str, price_bars: List[PriceBar],
                    strategy_func) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            symbol: 종목
            price_bars: 가격 바 데이터
            strategy_func: 전략 함수 (가격->신호)
        
        Returns:
            BacktestResult: 백테스트 결과
        """
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades: List[BacktestTrade] = []
        equity_curve = [capital]
        
        for i, bar in enumerate(price_bars):
            # 전략 신호 생성
            signal = strategy_func(price_bars[:i+1])
            
            # 진입
            if signal == "BUY" and position == 0:
                if capital >= bar.close:
                    position = int(capital * 0.95 / bar.close)  # 95% 투자
                    entry_price = bar.close
                    capital -= position * bar.close * (1 + self.fee_pct)
                    self.logger.debug(f"{bar.timestamp}: BUY {position} @ {bar.close}")
            
            # 청산
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
                    pnl_pct=((exit_price - entry_price) / entry_price) * 100
                )
                trades.append(trade)
                
                position = 0
                self.logger.debug(f"{bar.timestamp}: SELL {position} @ {exit_price}, PnL={pnl:.2f}")
            
            # 포지션 가치 계산
            if position > 0:
                position_value = position * bar.close
                total_value = capital + position_value
            else:
                total_value = capital
            
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
                pnl_pct=((final_price - entry_price) / entry_price) * 100
            )
            trades.append(trade)
        
        # 결과 계산
        final_capital = capital
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        win_rate = self._calculate_win_rate(trades)
        profit_factor = self._calculate_profit_factor(trades)
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
        
        total_fees = sum(
            (trade.quantity * trade.entry_price * self.fee_pct +
             trade.quantity * trade.exit_price * self.fee_pct)
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
            final_capital=final_capital
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
        import itertools
        
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

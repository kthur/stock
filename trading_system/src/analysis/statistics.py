"""Advanced Statistics - 고급 통계 분석"""

from dataclasses import dataclass
from typing import List, Dict
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    profit_factor: float
    recovery_factor: float


class AdvancedStatistics:
    """고급 통계 분석"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        초기화
        
        Args:
            risk_free_rate: 무위험 이자율 (연율)
        """
        self.risk_free_rate = risk_free_rate
        self.logger = logger
        
        # Kelly Criterion 연동을 위한 실시간 성과 추적 속성
        self.last_win_rate: float = 0.60       # 최근 승률 (기본값)
        self.last_profit_factor: float = 1.5   # 최근 이익계수 (기본값)
        self._trade_history: List[Dict] = []   # 누적 거래 기록
    
    def calculate_returns(self, equity_curve: List[float]) -> List[float]:
        """수익률 계산"""
        returns = []
        for i in range(1, len(equity_curve)):
            r = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(r)
        return returns
    
    def calculate_sharpe_ratio(self, returns: List[float], periods_per_year: int = 252) -> float:
        """Sharpe Ratio 계산"""
        if not returns or len(returns) < 2:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0
        
        excess_return = avg_return - (self.risk_free_rate / periods_per_year)
        sharpe = (excess_return / std_dev) * math.sqrt(periods_per_year)
        
        return sharpe
    
    def calculate_sortino_ratio(self, returns: List[float], 
                              target_return: float = 0, 
                              periods_per_year: int = 252) -> float:
        """Sortino Ratio 계산"""
        if not returns or len(returns) < 2:
            return 0
        
        avg_return = sum(returns) / len(returns)
        
        # 하방 편차만 계산
        downside_returns = [r for r in returns if r < target_return]
        
        if not downside_returns:
            return float('inf') if avg_return > target_return else 0
        
        downside_variance = sum((r - target_return) ** 2 for r in downside_returns) / len(returns)
        downside_std = math.sqrt(downside_variance)
        
        if downside_std == 0:
            return 0
        
        excess_return = avg_return - (self.risk_free_rate / periods_per_year)
        sortino = (excess_return / downside_std) * math.sqrt(periods_per_year)
        
        return sortino
    
    def calculate_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """Calmar Ratio 계산"""
        if max_drawdown == 0:
            return float('inf') if annual_return > 0 else 0
        
        return annual_return / abs(max_drawdown)
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0, 0, 0
        
        peak = equity_curve[0]
        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0
        
        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                peak_idx = i
            
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                trough_idx = i
        
        return max_dd, peak_idx, trough_idx
    
    def calculate_recovery_factor(self, total_return: float, max_drawdown: float) -> float:
        """Recovery Factor 계산"""
        if max_drawdown == 0:
            return float('inf') if total_return > 0 else 0
        
        return total_return / abs(max_drawdown)
    
    def calculate_volatility(self, returns: List[float], periods_per_year: int = 252) -> float:
        """변동성 계산"""
        if not returns or len(returns) < 2:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        daily_volatility = math.sqrt(variance)
        
        annual_volatility = daily_volatility * math.sqrt(periods_per_year)
        
        return annual_volatility
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Value at Risk (VaR) 계산"""
        if not returns:
            return 0
        
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * (1 - confidence))
        
        return sorted_returns[index]
    
    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Conditional Value at Risk (CVaR) / Expected Shortfall 계산"""
        if not returns:
            return 0
        
        var = self.calculate_var(returns, confidence)
        worse_returns = [r for r in returns if r <= var]
        
        if not worse_returns:
            return var
        
        return sum(worse_returns) / len(worse_returns)
    
    def calculate_information_ratio(self, returns: List[float], 
                                   benchmark_returns: List[float],
                                   periods_per_year: int = 252) -> float:
        """Information Ratio 계산"""
        if len(returns) != len(benchmark_returns):
            return 0
        
        # 초과 수익 계산
        excess_returns = [r - b for r, b in zip(returns, benchmark_returns)]
        
        avg_excess = sum(excess_returns) / len(excess_returns)
        variance = sum((e - avg_excess) ** 2 for e in excess_returns) / len(excess_returns)
        tracking_error = math.sqrt(variance)
        
        if tracking_error == 0:
            return 0
        
        ir = (avg_excess / tracking_error) * math.sqrt(periods_per_year)
        
        return ir
    
    def calculate_hurst_exponent(self, prices: List[float]) -> float:
        """Hurst Exponent 계산 (추세 강도)"""
        if len(prices) < 100:
            return 0.5
        
        returns = self.calculate_returns(prices)
        n = len(returns)
        
        # 누적 편차 계산
        mean_return = sum(returns) / n
        deviations = [r - mean_return for r in returns]
        cumsum = [sum(deviations[:i+1]) for i in range(n)]
        
        # Range 계산
        range_val = max(cumsum) - min(cumsum)
        
        # Standard deviation
        std_dev = math.sqrt(sum(r ** 2 for r in returns) / n)
        
        if std_dev == 0 or range_val == 0:
            return 0.5
        
        # Hurst 지수 (간단한 추정)
        hurst = math.log(range_val / std_dev) / math.log(n)
        
        return max(0, min(1, hurst))
    
    def get_performance_summary(self, equity_curve: List[float],
                               trades: List[Dict]) -> Dict:
        """성과 요약 조회"""
        returns = self.calculate_returns(equity_curve)
        
        initial_value = equity_curve[0]
        final_value = equity_curve[-1]
        total_return = (final_value - initial_value) / initial_value
        n = len(equity_curve)
        annual_return = (1 + total_return) ** (252 / n) - 1 if n > 0 else 0
        
        max_dd, _, _ = self.calculate_max_drawdown(equity_curve)
        volatility = self.calculate_volatility(returns)
        
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        calmar = self.calculate_calmar_ratio(annual_return, max_dd)
        recovery = self.calculate_recovery_factor(total_return, max_dd)
        
        # 거래 통계
        if trades:
            winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
            win_rate = winning_trades / len(trades)
            
            gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
            gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) <= 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        else:
            win_rate = 0
            profit_factor = 0
        
        summary = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            'max_drawdown': max_dd,
            'volatility': volatility,
            'recovery_factor': recovery,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'var_95': self.calculate_var(returns, 0.95),
            'cvar_95': self.calculate_cvar(returns, 0.95),
            'hurst_exponent': self.calculate_hurst_exponent([e for e in equity_curve]),
            'trade_count': len(trades)
        }
        
        # Kelly Criterion 연동을 위한 실시간 성과 갱신
        if trades:
            self.last_win_rate = win_rate
            self.last_profit_factor = profit_factor
        
        self.logger.info(f"Performance Summary: Total Return={total_return:.2%}, "
                        f"Sharpe={sharpe:.2f}, Max DD={max_dd:.2%}")
        
        return summary
    
    def record_trade(self, pnl: float, entry_price: float = 0.0, exit_price: float = 0.0) -> None:
        """개별 거래 완료 시 성과 지표를 실시간 갱신
        
        Args:
            pnl: 거래 손익
            entry_price: 진입 가격
            exit_price: 청산 가격
        """
        self._trade_history.append({
            'pnl': pnl,
            'entry_price': entry_price,
            'exit_price': exit_price
        })
        
        # 최근 50건 기준 승률 및 이익계수 갱신
        recent = self._trade_history[-50:]
        wins = sum(1 for t in recent if t['pnl'] > 0)
        self.last_win_rate = wins / len(recent)
        
        gross_profit = sum(t['pnl'] for t in recent if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in recent if t['pnl'] <= 0))
        self.last_profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 2.0
        
        self.logger.debug(f"Trade recorded: PnL={pnl:.2f}, "
                         f"WinRate={self.last_win_rate:.2%}, PF={self.last_profit_factor:.2f}")

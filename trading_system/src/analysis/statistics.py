"""Advanced Statistics - 고급 통계 분석"""

import logging
import math
from collections import deque
from dataclasses import dataclass
from typing import Dict, List

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

        # Bayesian 추정 — Beta(1,1) uniform prior, posterior = Beta(1+wins, 1+losses)
        self._wins: int = 0
        self._losses: int = 0
        self._total_pnl: float = 0.0
        self._gross_profit: float = 0.0
        self._gross_loss: float = 0.0
        self.last_win_rate: float = 0.50  # Bayesian posterior mean
        self.last_profit_factor: float = 1.2  # 누적 손익비
        self._trade_history: deque[Dict] = deque(maxlen=100)  # 최대 100건 보관
        self._conservative_until: int = 10  # 이 거래 수 미만이면 보수적 운영
        self._trade_count: int = 0

    def calculate_returns(self, equity_curve: List[float]) -> List[float]:
        """수익률 계산"""
        if not equity_curve:
            return []
        valid_curve = [float(x) for x in equity_curve if x is not None and math.isfinite(float(x))]
        if len(valid_curve) < 2:
            return []
        returns = []
        for i in range(1, len(valid_curve)):
            prev = valid_curve[i - 1]
            if prev <= 0 or abs(prev) < 1e-8:
                r = 0.0
            else:
                r = (valid_curve[i] - prev) / prev
            returns.append(float(r) if math.isfinite(r) else 0.0)
        return returns

    def calculate_sharpe_ratio(self, returns: List[float], periods_per_year: int = 252) -> float:
        """Sharpe Ratio 계산"""
        if not returns:
            return 0.0
        valid_returns = [float(r) for r in returns if r is not None and math.isfinite(float(r))]
        if len(valid_returns) < 2:
            return 0.0

        avg_return = sum(valid_returns) / len(valid_returns)
        variance = sum((r - avg_return) ** 2 for r in valid_returns) / len(valid_returns)
        std_dev = math.sqrt(variance)

        if std_dev == 0 or abs(std_dev) < 1e-9:
            return 0.0

        excess_return = avg_return - (self.risk_free_rate / periods_per_year)
        sharpe = (excess_return / std_dev) * math.sqrt(periods_per_year)
        if not math.isfinite(sharpe):
            return 0.0

        return max(-10.0, min(10.0, float(sharpe)))

    def calculate_sortino_ratio(
        self, returns: List[float], target_return: float = 0, periods_per_year: int = 252
    ) -> float:
        """Sortino Ratio 계산"""
        if not returns:
            return 0.0
        valid_returns = [float(r) for r in returns if r is not None and math.isfinite(float(r))]
        if len(valid_returns) < 2:
            return 0.0

        avg_return = sum(valid_returns) / len(valid_returns)

        # 하방 편차만 계산
        downside_returns = [r for r in valid_returns if r < target_return]

        if not downside_returns:
            return 10.0 if avg_return > target_return else 0.0

        downside_variance = sum((r - target_return) ** 2 for r in downside_returns) / len(valid_returns)
        downside_std = math.sqrt(downside_variance)

        if downside_std == 0 or abs(downside_std) < 1e-9:
            return 0.0

        excess_return = avg_return - (self.risk_free_rate / periods_per_year)
        sortino = (excess_return / downside_std) * math.sqrt(periods_per_year)
        if not math.isfinite(sortino):
            return 0.0

        return max(-10.0, min(10.0, float(sortino)))

    def calculate_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """Calmar Ratio 계산"""
        if max_drawdown == 0 or abs(max_drawdown) < 1e-8:
            return 10.0 if annual_return > 0 else 0.0

        res = annual_return / abs(max_drawdown)
        if math.isnan(res) or math.isinf(res):
            return 0.0
        return max(-100.0, min(100.0, float(res)))

    def calculate_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0.0, 0, 0

        valid_curve = [float(x) for x in equity_curve if x is not None and math.isfinite(float(x))]
        if not valid_curve:
            return 0.0, 0, 0

        peak = valid_curve[0]
        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0

        for i, value in enumerate(valid_curve):
            if value > peak:
                peak = value
                peak_idx = i

            if peak <= 0 or abs(peak) < 1e-8:
                dd = 0.0
            else:
                dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                trough_idx = i

        return float(max_dd), peak_idx, trough_idx

    def calculate_recovery_factor(self, total_return: float, max_drawdown: float) -> float:
        """Recovery Factor 계산"""
        if max_drawdown == 0 or abs(max_drawdown) < 1e-8:
            return 999.0 if total_return > 0 else 0.0

        res = total_return / abs(max_drawdown)
        if not math.isfinite(res):
            return 0.0
        return max(-999.0, min(999.0, float(res)))

    def calculate_volatility(self, returns: List[float], periods_per_year: int = 252) -> float:
        """변동성 계산"""
        if not returns:
            return 0.0
        valid_returns = [float(r) for r in returns if r is not None and math.isfinite(float(r))]
        if len(valid_returns) < 2:
            return 0.0

        avg_return = sum(valid_returns) / len(valid_returns)
        variance = sum((r - avg_return) ** 2 for r in valid_returns) / len(valid_returns)
        daily_volatility = math.sqrt(variance)

        annual_volatility = daily_volatility * math.sqrt(periods_per_year)
        return float(annual_volatility) if math.isfinite(annual_volatility) else 0.0

    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Value at Risk (VaR) 계산"""
        if not returns:
            return 0.0
        valid_returns = [float(r) for r in returns if r is not None and math.isfinite(float(r))]
        if not valid_returns:
            return 0.0

        sorted_returns = sorted(valid_returns)
        index = max(0, min(len(sorted_returns) - 1, int(len(sorted_returns) * (1.0 - confidence))))

        return float(sorted_returns[index])

    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Conditional Value at Risk (CVaR) / Expected Shortfall 계산"""
        if not returns:
            return 0.0
        valid_returns = [float(r) for r in returns if r is not None and math.isfinite(float(r))]
        if not valid_returns:
            return 0.0

        var = self.calculate_var(valid_returns, confidence)
        worse_returns = [r for r in valid_returns if r <= var]

        if not worse_returns:
            return float(var)

        return float(sum(worse_returns) / len(worse_returns))

    def calculate_information_ratio(
        self, returns: List[float], benchmark_returns: List[float], periods_per_year: int = 252
    ) -> float:
        """Information Ratio 계산"""
        if len(returns) != len(benchmark_returns) or not returns:
            return 0.0

        # 초과 수익 계산
        valid_pairs = [(float(r), float(b)) for r, b in zip(returns, benchmark_returns) if r is not None and b is not None and math.isfinite(float(r)) and math.isfinite(float(b))]
        if len(valid_pairs) < 2:
            return 0.0

        excess_returns = [r - b for r, b in valid_pairs]

        avg_excess = sum(excess_returns) / len(excess_returns)
        variance = sum((e - avg_excess) ** 2 for e in excess_returns) / len(excess_returns)
        tracking_error = math.sqrt(max(0.0, variance))

        if tracking_error == 0 or abs(tracking_error) < 1e-9:
            return 0.0

        ir = (avg_excess / tracking_error) * math.sqrt(periods_per_year)
        if not math.isfinite(ir):
            return 0.0

        return max(-10.0, min(10.0, float(ir)))

    def calculate_hurst_exponent(self, prices: List[float]) -> float:
        """Hurst Exponent 계산 (추세 강도)"""
        if len(prices) < 100:
            return 0.5

        returns = self.calculate_returns(prices)
        valid_returns = [float(r) for r in returns if math.isfinite(float(r))]
        n = len(valid_returns)
        if n < 10:
            return 0.5

        # 누적 편차 계산
        mean_return = sum(valid_returns) / n
        deviations = [r - mean_return for r in valid_returns]
        cumsum = [sum(deviations[: i + 1]) for i in range(n)]

        # Range 계산
        range_val = max(cumsum) - min(cumsum)

        # Standard deviation
        std_dev = math.sqrt(max(0.0, sum(r**2 for r in valid_returns) / n))

        if std_dev == 0 or range_val == 0 or not math.isfinite(range_val) or not math.isfinite(std_dev):
            return 0.5

        # Hurst 지수 (간단한 추정)
        try:
            ratio = range_val / std_dev
            if ratio <= 0 or not math.isfinite(ratio):
                return 0.5
            hurst = math.log(ratio) / math.log(n)
        except (ValueError, ZeroDivisionError):
            return 0.5

        if not math.isfinite(hurst):
            return 0.5

        return max(0.0, min(1.0, float(hurst)))

    def get_performance_summary(self, equity_curve: List[float], trades: List[Dict]) -> Dict:
        """성과 요약 조회"""
        if not equity_curve:
            return {}

        returns = self.calculate_returns(equity_curve)

        initial_value = equity_curve[0]
        final_value = equity_curve[-1]
        if initial_value <= 0 or abs(initial_value) < 1e-8:
            total_return = 0.0
        else:
            total_return = (final_value - initial_value) / initial_value
        n = len(equity_curve)
        total_ret_clamped = max(1e-6, 1.0 + total_return)
        annual_return = (total_ret_clamped ** (252.0 / n)) - 1.0 if n > 0 else 0.0

        max_dd, _, _ = self.calculate_max_drawdown(equity_curve)
        volatility = self.calculate_volatility(returns)

        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        calmar = self.calculate_calmar_ratio(annual_return, max_dd)
        recovery = self.calculate_recovery_factor(total_return, max_dd)

        # 거래 통계
        if trades:
            winning_trades = sum(1 for t in trades if t.get("pnl", 0) > 0)
            win_rate = winning_trades / len(trades)

            gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
            gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) <= 0))
            profit_factor = min(gross_profit / gross_loss, 100.0) if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)
        else:
            win_rate = 0.0
            profit_factor = 0.0

        summary = {
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "max_drawdown": max_dd,
            "volatility": volatility,
            "recovery_factor": recovery,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "var_95": self.calculate_var(returns, 0.95),
            "cvar_95": self.calculate_cvar(returns, 0.95),
            "hurst_exponent": self.calculate_hurst_exponent([e for e in equity_curve]),
            "trade_count": len(trades),
        }

        # Kelly Criterion 연동을 위한 실시간 성과 갱신
        if trades:
            self.last_win_rate = win_rate
            self.last_profit_factor = profit_factor

        self.logger.info(
            f"Performance Summary: Total Return={total_return:.2%}, Sharpe={sharpe:.2f}, Max DD={max_dd:.2%}"
        )

        return summary

    def record_trade(self, pnl: float, entry_price: float = 0.0, exit_price: float = 0.0) -> None:
        """개별 거래 완료 시 성과 지표를 실시간 갱신

        Args:
            pnl: 거래 손익
            entry_price: 진입 가격
            exit_price: 청산 가격
        """
        self._trade_history.append({"pnl": pnl, "entry_price": entry_price, "exit_price": exit_price})
        self._trade_count += 1
        self._total_pnl += pnl
        if pnl > 0:
            self._wins += 1
            self._gross_profit += pnl
        else:
            self._losses += 1
            self._gross_loss -= pnl  # pnl is negative or zero

        # Bayesian posterior: Beta(1 + wins, 1 + losses)
        alpha = 1.0 + self._wins
        beta = 1.0 + self._losses
        self.last_win_rate = alpha / (alpha + beta)

        # 누적 profit factor (전체 기간)
        if self._gross_loss > 0:
            self.last_profit_factor = self._gross_profit / self._gross_loss
        elif self._trade_count >= 10 and self._gross_profit > 0:
            self.last_profit_factor = 2.5
        else:
            self.last_profit_factor = 1.2

        self.logger.debug(
            f"Trade #{self._trade_count} recorded: PnL={pnl:.2f}, "
            f"WinRate={self.last_win_rate:.2%}, PF={self.last_profit_factor:.2f}"
        )

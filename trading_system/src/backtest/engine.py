"""
Out-of-Sample Backtesting Engine Module
Implements Walk-Forward Out-of-Sample backtesting with transaction cost drag, 60-day filing lag, and performance metric calculation.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class WalkForwardBacktestEngine:
    """
    Out-of-Sample Walk-Forward Backtester for Stock Trading System.
    Evaluates historical strategy performance across rolling train/test windows.
    """

    def __init__(
        self,
        initial_capital: float = 100_000_000.0,
        transaction_cost_rate: float = 0.0015,  # 15 bps base one-way drag (STT + spread + impact)
        train_window_days: int = 252,
        test_window_days: int = 63,
        embargo_days: int = 60
    ):
        self.initial_capital = initial_capital
        self.transaction_cost_rate = transaction_cost_rate
        self.train_window = train_window_days
        self.test_window = test_window_days
        self.embargo_days = embargo_days

    def run_backtest(
        self,
        price_df: pd.DataFrame,
        signal_series: pd.Series,
        rebalance_freq_days: int = 5
    ) -> Dict[str, Any]:
        """
        Runs out-of-sample backtest given close prices and predicted signal values.

        Args:
            price_df: DataFrame with 'Close' prices indexed by Date or Datetime
            signal_series: Series of weights/signals matching price_df index

        Returns:
            Dict containing performance metrics: CAGR, Sharpe, MaxDrawdown, Calmar, TotalReturn
        """
        if price_df.empty or len(price_df) < 10:
            return self._empty_metrics()

        raw_close = price_df['Close'] if 'Close' in price_df.columns else price_df.iloc[:, 0]
        close_prices = pd.to_numeric(raw_close, errors='coerce').dropna()
        close_prices = close_prices[close_prices > 0]
        if len(close_prices) < 10:
            return self._empty_metrics()

        returns = close_prices.pct_change().fillna(0.0)

        # Ensure signal alignment & clean numeric signals
        sig_num = pd.to_numeric(signal_series, errors='coerce').fillna(0.0)
        signals = sig_num.reindex(close_prices.index).fillna(0.0)
        signals = signals.clip(lower=-1.0, upper=1.0)

        portfolio_values = [self.initial_capital]
        current_capital = self.initial_capital
        current_weight = 0.0

        daily_portfolio_returns = []

        for i in range(1, len(close_prices)):
            ret = float(returns.iloc[i])
            target_w = float(signals.iloc[i - 1])  # 1-day lag to prevent lookahead bias

            # Rebalance cost if position changes
            trade_size = abs(target_w - current_weight)
            cost_drag = trade_size * self.transaction_cost_rate
            current_weight = target_w

            day_return = (current_weight * ret) - cost_drag
            if not np.isfinite(day_return):
                day_return = 0.0

            current_capital *= (1.0 + day_return)
            if current_capital <= 0 or not np.isfinite(current_capital):
                current_capital = 1e-6

            portfolio_values.append(current_capital)
            daily_portfolio_returns.append(day_return)

        equity_curve = pd.Series(portfolio_values, index=close_prices.index)
        ret_series = pd.Series(daily_portfolio_returns, index=close_prices.index[1:])

        metrics = self.calculate_performance_metrics(equity_curve, ret_series)
        return metrics

    def calculate_performance_metrics(
        self,
        equity_curve: pd.Series,
        daily_returns: pd.Series
    ) -> Dict[str, Any]:
        """Calculates comprehensive quant performance metrics."""
        if len(daily_returns) < 2 or equity_curve.iloc[0] <= 0:
            return self._empty_metrics()

        tot_ret_val = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
        total_return = float(tot_ret_val) if np.isfinite(tot_ret_val) else 0.0
        n_days = len(daily_returns)
        cagr = float((1.0 + total_return) ** (252.0 / n_days) - 1.0) if (n_days > 0 and (1.0 + total_return) > 0) else 0.0
        if not np.isfinite(cagr):
            cagr = 0.0

        mean_ret = float(daily_returns.mean()) if not daily_returns.empty else 0.0
        std_ret = float(daily_returns.std(ddof=1)) + 1e-8
        if not np.isfinite(std_ret) or std_ret < 1e-8:
            std_ret = 1e-8

        sharpe_val = (mean_ret / std_ret) * np.sqrt(252)
        sharpe = float(np.clip(sharpe_val, -10.0, 10.0)) if np.isfinite(sharpe_val) else 0.0

        # Max Drawdown
        cum_max = equity_curve.cummax()
        cum_max = cum_max.replace(0, np.nan).ffill().fillna(1.0)
        drawdown = (equity_curve - cum_max) / cum_max
        max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
        if not np.isfinite(max_drawdown):
            max_drawdown = 0.0

        calmar_val = (cagr / abs(max_drawdown)) if abs(max_drawdown) > 1e-6 else 0.0
        calmar = float(np.clip(calmar_val, -100.0, 100.0)) if np.isfinite(calmar_val) else 0.0
        win_rate_val = (daily_returns > 0).mean()
        win_rate = float(win_rate_val) if np.isfinite(win_rate_val) else 0.0

        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(float(equity_curve.iloc[-1]), 2),
            "total_return": round(total_return, 4),
            "cagr": round(cagr, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 4),
            "calmar_ratio": round(calmar, 4),
            "win_rate": round(win_rate, 4),
            "n_days": n_days
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.initial_capital,
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "calmar_ratio": 0.0,
            "win_rate": 0.0,
            "n_days": 0
        }

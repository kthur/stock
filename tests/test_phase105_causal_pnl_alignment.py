"""Regression test for same-day PnL lookahead in the Phase 105 backtester.

Signals are formed from data strictly before date T and executed at T's close.
Therefore day-T PnL must accrue on the beginning-of-day book, not on holdings
created by the T rebalance.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"
for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
)


DATES = pd.DatetimeIndex(
    ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"]
)


class _FakePanel:
    def __init__(self) -> None:
        self.dates = DATES
        self.price_tensor = {
            "A": pd.DataFrame({"close": [100.0, 100.0, 110.0, 110.0, 110.0]}, index=DATES)
        }
        self.delisting_registry: dict = {}

    def get_returns_matrix(self, horizon: int = 1) -> pd.DataFrame:
        return pd.DataFrame({"A": [0.0, 0.10, 0.0, 0.0, 0.0]}, index=DATES)


class _ProbeBacktester(HistoricalStockUniverseBacktester):
    def __init__(self, panel: _FakePanel) -> None:
        super().__init__(
            pipeline=object(),
            start_date="2020-01-02",
            end_date="2020-01-08",
            rebalance_freq_days=1,
            stop_loss_pct=0.0,
            trailing_stop_pct=0.0,
            initial_capital=1_000_000.0,
        )
        self._fake_panel = panel
        self._panel = panel

    def load_panel(self, force_refresh: bool = False) -> _FakePanel:
        return self._fake_panel

    def classify_2d_regime(self, date, panel=None):
        return "BULL_LOW_VOL", False, {}

    def allocate_portfolio(self, **kwargs):
        return {}, {"A": 1.0}, 1.0, 0.0

    def _compute_performance_metrics(self, **kwargs):
        return {
            "final_equity": 1_000_000.0,
            "total_net_return_pct": 0.0,
            "total_gross_return_pct": 0.0,
            "cagr_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_turnover": 0.0,
            "total_friction_bps": 0.0,
            "annualized_turnover": 0.0,
        }

    def _build_annual_distribution_df(self, **kwargs):
        return pd.DataFrame()

    def _build_crisis_breakdown_df(self, **kwargs):
        return pd.DataFrame()


class TestCausalPnlAlignment(unittest.TestCase):
    def test_first_day_pnl_excludes_same_day_rebalance_return(self) -> None:
        result = _ProbeBacktester(_FakePanel()).run_backtest()

        first_day_return = float(result.daily_returns.iloc[0])

        # With the old lookahead, buying A at T's close earned A's T-1 -> T
        # return (+10%). Causal accounting earns only cash carry on day one.
        self.assertLess(
            first_day_return,
            0.01,
            f"Same-day lookahead detected: first-day return={first_day_return:.6f}",
        )


if __name__ == "__main__":
    unittest.main()

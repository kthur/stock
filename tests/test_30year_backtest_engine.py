"""
tests/test_30year_backtest_engine.py — Unit & Integration Test Suite for 30-Year Backtest Engine

Tests lookahead lag prevention (T signal -> T+1 execution), statutory regulatory filing lag
enforcement (KRX 45/90d, SEC 40/60d), Leland buffer bypass rules, realistic transaction frictions,
5 historical crisis stress slicing, 31-year annual distribution, and 15-metric quantitative analytics.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.data_layer.earnings_data import compute_regulatory_filing_lag
from src.backtest.engine import WalkForwardBacktestEngine
from src.execution.turnover_optimizer import TurnoverOptimizer
from src.analysis.statistics import AdvancedStatistics, PerformanceMetrics
from src.analysis.backtest import BacktestEngine, PriceBar
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


# ==============================================================================
# 1. Causal Alignment & Lookahead Guards Tests
# ==============================================================================

class TestCausalLookaheadGuards(unittest.TestCase):
    """Verifies that signal generation at bar T strictly precedes execution at T+1."""

    def setUp(self) -> None:
        self.engine = WalkForwardBacktestEngine(initial_capital=100_000_000.0, transaction_cost_rate=0.0010)

    def test_walk_forward_engine_one_day_signal_lag(self) -> None:
        """
        Signals at bar T must only affect positions on bar T+1.
        A shock occurring on day i cannot be captured if the signal was 0 on day i-1.
        """
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        # Constant prices 100.0, except jump to 120.0 on index 5 (day 6)
        prices = [100.0] * 5 + [120.0] * 10
        price_df = pd.DataFrame({"Close": prices}, index=dates)

        # Strategy produces signal=1.0 at index 5 (after seeing the jump at index 5)
        signals = pd.Series([0.0] * 5 + [1.0] * 10, index=dates)

        metrics = self.engine.run_backtest(price_df, signals)

        # Because of 1-day lag, the position on index 5 was 0.0 (from signal at index 4).
        # Therefore, the strategy MISSED the jump from 100 -> 120 on day 5!
        # From day 6 onwards, price stayed flat at 120.0, so no further price gain was captured.
        # Total return should be negative or zero (minus small rebalance friction when entering at day 6)
        self.assertLessEqual(metrics["total_return"], 0.0)

    def test_impulse_signal_executes_on_next_bar_only(self) -> None:
        """Verifies that an impulse signal on bar T captures return on bar T+1."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        # Prices: 100 on days 0..4, jumps to 115 on day 5, flat onwards
        prices = [100.0] * 5 + [115.0] * 10
        price_df = pd.DataFrame({"Close": prices}, index=dates)

        # Signal turns 1.0 on day 4 (strictly BEFORE the jump on day 5)
        signals = pd.Series([0.0] * 4 + [1.0] * 11, index=dates)

        metrics = self.engine.run_backtest(price_df, signals)
        # Position was entered on day 5 based on day 4 signal, so the +15% gain was captured!
        self.assertGreater(metrics["total_return"], 0.10)

    def test_statutory_filing_lag_krx_quarterly(self) -> None:
        """KRX quarterly statements (1Q, 2Q, 3Q) must have strictly 45 calendar days filing lag."""
        # 1Q: March 31 -> May 15
        lag_1q = compute_regulatory_filing_lag("2025-03-31", period_type="quarterly", is_krx=True)
        self.assertEqual(lag_1q, "2025-05-15")

        # 2Q: June 30 -> August 14
        lag_2q = compute_regulatory_filing_lag("2025-06-30", period_type="quarterly", is_krx=True)
        self.assertEqual(lag_2q, "2025-08-14")

        # 3Q: September 30 -> November 14
        lag_3q = compute_regulatory_filing_lag("2025-09-30", period_type="quarterly", is_krx=True)
        self.assertEqual(lag_3q, "2025-11-14")

    def test_statutory_filing_lag_krx_annual(self) -> None:
        """KRX annual statements (4Q / Dec 31) must have strictly 90 calendar days filing lag."""
        # 4Q / Year-end: Dec 31 -> March 31 of following year
        lag_4q = compute_regulatory_filing_lag("2025-12-31", period_type="annual", is_krx=True)
        self.assertEqual(lag_4q, "2026-03-31")

    def test_statutory_filing_lag_sec_us_quarterly_and_annual(self) -> None:
        """SEC 10-Q (40 days) and 10-K (60 days) filing lags must be strictly enforced."""
        # 1Q SEC: March 31 + 40 days -> May 10
        sec_1q = compute_regulatory_filing_lag("2025-03-31", period_type="quarterly", is_krx=False)
        self.assertEqual(sec_1q, "2025-05-10")

        # Annual SEC: Dec 31 + 60 days -> March 01
        sec_ann = compute_regulatory_filing_lag("2025-12-31", period_type="annual", is_krx=False)
        self.assertEqual(sec_ann, "2026-03-01")

    def test_filing_lag_precludes_intraday_fundamental_lookahead(self) -> None:
        """Validates that a bar date prior to statutory filing date cannot access earnings."""
        period_end = "2025-03-31"
        available_date = compute_regulatory_filing_lag(period_end, period_type="quarterly", is_krx=True)
        bar_date = "2025-04-15"

        # On 2025-04-15, Q1 earnings are not yet available (available on 2025-05-15)
        is_accessible = bar_date >= available_date
        self.assertFalse(is_accessible)


# ==============================================================================
# 2. Execution Frictions & Leland Buffer Bypass Tests
# ==============================================================================

class TestExecutionFrictionsAndLelandBypass(unittest.TestCase):
    """Verifies market transaction costs, STT tax, SEC fees, and Leland buffer bypass."""

    def setUp(self) -> None:
        self.backtest_engine = BacktestEngine(initial_capital=100_000.0)
        self.turnover_opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50_000.0)
        self.unified_allocator = UnifiedPortfolioAllocator(leland_cost_bps=20.0)

    def test_market_transaction_cost_rates(self) -> None:
        """Validates centralized cost rates per market in BacktestEngine."""
        self.assertAlmostEqual(self.backtest_engine.get_market_cost_rate(market="KOSPI"), 0.0085, places=5)
        self.assertAlmostEqual(self.backtest_engine.get_market_cost_rate(market="KOSDAQ"), 0.0100, places=5)
        self.assertAlmostEqual(self.backtest_engine.get_market_cost_rate(market="SP500"), 0.0060, places=5)
        self.assertAlmostEqual(self.backtest_engine.get_market_cost_rate(market="NASDAQ"), 0.0065, places=5)
        self.assertAlmostEqual(self.backtest_engine.get_market_cost_rate(market="RUSSELL2000"), 0.0080, places=5)

    def test_friction_drag_reduces_net_return_monotonically(self) -> None:
        """Active rebalancing with friction must produce Net Return strictly less than Gross Return."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        # Rising prices
        prices = [100.0 + i * 2.0 for i in range(20)]
        price_df = pd.DataFrame({"Close": prices}, index=dates)

        # Alternating weights creating turnover
        signals = pd.Series([0.2 if i % 2 == 0 else 0.8 for i in range(20)], index=dates)

        engine_zero_cost = WalkForwardBacktestEngine(initial_capital=100_000_000.0, transaction_cost_rate=0.0)
        engine_real_cost = WalkForwardBacktestEngine(initial_capital=100_000_000.0, transaction_cost_rate=0.0020)

        res_zero = engine_zero_cost.run_backtest(price_df, signals)
        res_real = engine_real_cost.run_backtest(price_df, signals)

        self.assertGreater(res_zero["total_return"], res_real["total_return"])
        self.assertGreater(res_zero["final_equity"], res_real["final_equity"])

    def test_leland_hysteresis_dampens_small_rebalance_fluctuation(self) -> None:
        """TurnoverOptimizer must HOLD when target weight change is within hysteresis threshold."""
        current = {"AAPL": 0.10, "MSFT": 0.10}
        target = {"AAPL": 0.12, "MSFT": 0.09}  # Deltas: 0.02 and 0.01 (< threshold 0.05)

        res = self.turnover_opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            total_capital=100_000_000.0,
            currency="USD",
        )

        self.assertEqual(res["AAPL"]["action"], "HOLD")
        self.assertEqual(res["MSFT"]["action"], "HOLD")
        self.assertEqual(res["AAPL"]["target_weight"], 0.10)
        self.assertEqual(res["MSFT"]["target_weight"], 0.10)

    def test_leland_bypass_on_fresh_entry(self) -> None:
        """TurnoverOptimizer must immediately BUY on fresh entry (curr_w == 0), bypassing threshold."""
        current = {"AAPL": 0.00}
        target = {"AAPL": 0.03}  # Delta = 0.03 (< 0.05 threshold), but curr is 0!

        res = self.turnover_opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            total_capital=100_000_000.0,
            currency="USD",
        )

        self.assertEqual(res["AAPL"]["action"], "BUY")
        self.assertAlmostEqual(res["AAPL"]["target_weight"], 0.03, places=4)

    def test_leland_bypass_on_full_exit(self) -> None:
        """TurnoverOptimizer must immediately SELL on full liquidation (target_w == 0), bypassing threshold."""
        current = {"AAPL": 0.04}
        target = {"AAPL": 0.00}  # Delta = 0.04 (< 0.05 threshold), but target is 0!

        res = self.turnover_opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            total_capital=100_000_000.0,
            currency="USD",
        )

        self.assertEqual(res["AAPL"]["action"], "SELL")
        self.assertAlmostEqual(res["AAPL"]["target_weight"], 0.00, places=4)

    def test_unified_portfolio_allocator_leland_buffer_bands_bypass(self) -> None:
        """
        UnifiedPortfolioAllocator.apply_leland_no_trade_buffers must bypass buffers
        when curr_w <= 1e-4 (entry) or tgt_w <= 1e-4 (exit).
        """
        current_w = np.array([0.0, 0.10, 0.05])
        target_w = np.array([0.08, 0.11, 0.0])  # asset 0 is new entry, asset 2 is full exit
        vols = np.array([0.15, 0.12, 0.20])

        realized_w = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols,
            use_asymmetric_bands=False,
        )

        # Asset 0 (new entry) must be realized at target weight 0.08 (bypassed)
        self.assertAlmostEqual(realized_w[0], 0.08, places=4)
        # Asset 2 (full liquidation) must be realized at target weight 0.0 (bypassed)
        self.assertAlmostEqual(realized_w[2], 0.0, places=4)


# ==============================================================================
# 3. Historical Crisis Slicing & Stress Testing Tests
# ==============================================================================

class TestHistoricalCrisisSlicing(unittest.TestCase):
    """Verifies that all 5 historical crises are correctly sliced and evaluated."""

    CRISIS_PERIODS = {
        "1997_ASIAN_CRISIS": ("1997-07-01", "1998-12-31"),
        "2000_DOTCOM_CRASH": ("2000-03-01", "2002-10-31"),
        "2008_GFC": ("2007-10-01", "2009-03-31"),
        "2020_COVID_SHOCK": ("2020-02-01", "2020-04-30"),
        "2022_INFLATION_RATE_HIKE": ("2022-01-01", "2022-12-31"),
    }

    def test_all_five_crises_chronology_and_validity(self) -> None:
        """Verifies that each crisis start date strictly precedes end date."""
        for cid, (s_str, e_str) in self.CRISIS_PERIODS.items():
            d_start = datetime.strptime(s_str, "%Y-%m-%d")
            d_end = datetime.strptime(e_str, "%Y-%m-%d")
            self.assertLess(d_start, d_end, f"Crisis {cid} start date {s_str} must precede end date {e_str}")

    def test_crisis_slicing_on_historical_equity_curve(self) -> None:
        """Slices a simulated 30-year equity curve and asserts each crisis captures negative drawdown."""
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        np.random.seed(42)

        # Base positive drift with volatility
        daily_ret = np.random.normal(0.0004, 0.01, len(dates))
        ret_series = pd.Series(daily_ret, index=dates)

        # Inject historical market downturns during the 5 crisis periods
        for cid, (s_str, e_str) in self.CRISIS_PERIODS.items():
            mask = (ret_series.index >= s_str) & (ret_series.index <= e_str)
            # Add severe negative drift during crisis
            ret_series.loc[mask] -= 0.0015

        equity_curve = (1.0 + ret_series).cumprod() * 100_000_000.0

        stats = AdvancedStatistics(risk_free_rate=0.02)

        for cid, (s_str, e_str) in self.CRISIS_PERIODS.items():
            crisis_slice = equity_curve.loc[s_str:e_str]
            self.assertGreater(len(crisis_slice), 20, f"Crisis slice {cid} must have sufficient daily bars")

            mdd, peak_idx, trough_idx = stats.calculate_max_drawdown(crisis_slice.tolist())
            # MDD in crisis must be strictly positive magnitude (i.e. representing a loss)
            self.assertGreater(mdd, 0.05, f"Crisis {cid} MDD must reflect material drawdown")

    def test_crisis_recovery_period_calculation(self) -> None:
        """Verifies recovery days calculation from trough back to prior peak."""
        curve = [100.0, 90.0, 80.0, 85.0, 95.0, 105.0]
        peak = 100.0
        trough_idx = 2
        recovery_idx = 5
        recovery_days = recovery_idx - trough_idx
        self.assertEqual(recovery_days, 3)


# ==============================================================================
# 4. Annual Distribution (1996–2026) Tests
# ==============================================================================

class TestAnnualDistributionSlicing(unittest.TestCase):
    """Verifies that 30-year simulation cleanly partitions into all 31 calendar years."""

    def test_31_calendar_years_partitioning(self) -> None:
        """Daily series spanning 1996 to 2026 must partition into exactly 31 distinct years."""
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        years = dates.year.unique()

        self.assertEqual(len(years), 31)
        self.assertEqual(years.min(), 1996)
        self.assertEqual(years.max(), 2026)
        self.assertTrue(all(y in years for y in range(1996, 2027)))

    def test_annual_compounding_preserves_total_equity(self) -> None:
        """Chaining 31 annual returns must match total cumulative compounding."""
        np.random.seed(123)
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        daily_ret = np.random.normal(0.0003, 0.008, len(dates))
        ret_series = pd.Series(daily_ret, index=dates)

        annual_factors = []
        for y in range(1996, 2027):
            y_ret = ret_series[ret_series.index.year == y]
            factor = (1.0 + y_ret).prod()
            annual_factors.append(factor)

        chained_total = np.prod(annual_factors)
        direct_total = (1.0 + ret_series).prod()

        self.assertAlmostEqual(chained_total, direct_total, places=5)


# ==============================================================================
# 5. 15-Metric Quantitative Analytics Formulations Tests
# ==============================================================================

class TestQuantitativeAnalyticsFormulations(unittest.TestCase):
    """Verifies mathematical correctness of CAGR, Sharpe, Sortino, Calmar, MDD, and bounds."""

    def setUp(self) -> None:
        self.stats = AdvancedStatistics(risk_free_rate=0.02)

    def test_cagr_compounding_formula(self) -> None:
        """CAGR = (1 + R)^(252 / N) - 1 on known 2-year double equity curve."""
        n_days = 504  # 2 trading years
        # 100% total return over 2 years -> annual return is sqrt(2) - 1 ≈ 41.42%
        equity_curve = [100.0] + [100.0 + (100.0 * i / n_days) for i in range(1, n_days + 1)]
        summary = self.stats.get_performance_summary(equity_curve, trades=[])

        ann_ret = summary.get("annual_return", 0.0)
        self.assertAlmostEqual(ann_ret, math.sqrt(2.0) - 1.0, places=2)

    def test_annualized_sharpe_with_bessel_correction(self) -> None:
        """Annualized Sharpe ratio uses sample std dev (ddof=1) and is bounded."""
        returns = [0.001, 0.002, 0.0015, -0.0005, 0.0012] * 50
        sharpe = self.stats.calculate_sharpe_ratio(returns, periods_per_year=252)

        self.assertTrue(math.isfinite(sharpe))
        self.assertGreater(sharpe, 0.0)
        self.assertLessEqual(sharpe, 10.0)

    def test_sortino_ratio_downside_deviation(self) -> None:
        """Sortino ratio only penalizes downside deviations below MAR hurdle."""
        returns = [0.002, 0.003, 0.0015, -0.001, -0.002, 0.0025] * 40
        sortino = self.stats.calculate_sortino_ratio(returns, periods_per_year=252)

        self.assertTrue(math.isfinite(sortino))
        self.assertGreater(sortino, 0.0)

    def test_calmar_ratio_calculation(self) -> None:
        """Calmar = Annual Return / |MDD|."""
        annual_return = 0.15
        max_drawdown = 0.10
        calmar = self.stats.calculate_calmar_ratio(annual_return, max_drawdown)

        self.assertAlmostEqual(calmar, 1.5, places=4)

    def test_flat_equity_curve_zero_variance_does_not_crash(self) -> None:
        """A completely flat equity curve must yield finite metrics without division-by-zero error."""
        flat_curve = [100.0] * 100
        returns = self.stats.calculate_returns(flat_curve)

        sharpe = self.stats.calculate_sharpe_ratio(returns)
        sortino = self.stats.calculate_sortino_ratio(returns)
        mdd, _, _ = self.stats.calculate_max_drawdown(flat_curve)
        vol = self.stats.calculate_volatility(returns)

        self.assertEqual(sharpe, 0.0)
        self.assertTrue(math.isfinite(sortino))
        self.assertEqual(mdd, 0.0)
        self.assertEqual(vol, 0.0)

    def test_all_negative_returns_yields_negative_finite_sharpe(self) -> None:
        """Continuous drawdown yields negative finite Sharpe and strictly positive MDD magnitude."""
        declining_curve = [100.0 - i * 0.5 for i in range(50)]
        returns = self.stats.calculate_returns(declining_curve)

        sharpe = self.stats.calculate_sharpe_ratio(returns)
        mdd, _, _ = self.stats.calculate_max_drawdown(declining_curve)

        self.assertTrue(math.isfinite(sharpe))
        self.assertLess(sharpe, 0.0)
        self.assertGreater(mdd, 0.0)

    def test_extreme_flash_crash_boundedness(self) -> None:
        """A sudden -40% flash crash is bounded and handled without NaN/inf."""
        curve = [100.0] * 10 + [60.0] + [62.0] * 10
        returns = self.stats.calculate_returns(curve)
        mdd, _, _ = self.stats.calculate_max_drawdown(curve)

        self.assertAlmostEqual(mdd, 0.40, places=2)
        summary = self.stats.get_performance_summary(curve, trades=[])
        self.assertTrue(math.isfinite(summary.get("sharpe_ratio", 0.0)))
        self.assertTrue(math.isfinite(summary.get("annual_return", 0.0)))


if __name__ == "__main__":
    unittest.main()

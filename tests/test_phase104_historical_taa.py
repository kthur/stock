"""
tests/test_phase104_historical_taa.py — Unit, Integration & Adversarial Test Suite for Phase 104 TAA Engine

Features Covered:
- Feature F490: 200-Day SMA Trend-Following Bear Market Gating
- Feature F491: 12M-1M Momentum Quality & Cross-Market Relative Strength Alpha
- Feature F492: Bull Regime Cash Drag Elimination (vol_scalar expands to 1.00)
- Feature F493: Quarterly (60-Day) Rebalancing & 3% Turnover Hysteresis Band
- Adversarial & Boundary Stress Scenarios
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# Setup sys.path for repository root and trading_system
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_backtester import (
    Historical30YrBacktester,
    BacktestSimulationResult,
)
from src.execution.turnover_optimizer import TurnoverOptimizer


class TestPhase104SMA200BearMarketGating(unittest.TestCase):
    """
    Validates Feature F490: 200-Day SMA Trend-Following Bear Market Gating.
    I_trend,m(t) = I(P_m(t) > SMA_200,m(t)).
    """

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester(
            start_date="2000-01-01",
            end_date="2003-12-31",
            rebalance_freq_days=60,
            target_volatility=0.12,
            initial_capital=100_000_000.0,
            enable_sma200_gating=True,
        )

    def test_sma200_calculation_accuracy_synthetic(self) -> None:
        """Verifies SMA-200 calculation matches pandas rolling mean and triggers gating accurately."""
        # Construct synthetic price panel with 300 trading days
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # Market SP500: rising from 100 to 200 (P > SMA200 -> True)
        # Market NASDAQ: falling from 200 to 80 (P < SMA200 -> False)
        # Market RUSSELL2000: flat 100
        # Market KOSPI: fluctuating around 100
        # Market KOSDAQ: dropping sharply in last 30 days
        sp_prices = np.linspace(100.0, 200.0, 300)
        nas_prices = np.linspace(200.0, 80.0, 300)
        rut_prices = np.full(300, 100.0)
        kospi_prices = 100.0 + 5.0 * np.sin(np.linspace(0, 10, 300))
        kosdaq_prices = np.concatenate([np.full(250, 150.0), np.linspace(150.0, 50.0, 50)])

        df_prices = pd.DataFrame(
            {
                "SP500": sp_prices,
                "NASDAQ": nas_prices,
                "RUSSELL2000": rut_prices,
                "KOSPI": kospi_prices,
                "KOSDAQ": kosdaq_prices,
            },
            index=dates,
        )
        self.backtester._price_matrix = df_prices

        eval_date = dates[299]
        trends = self.backtester.compute_sma_200_trend(eval_date)

        # SP500 at day 298 is 199.66, SMA200 is ~150 -> Price > SMA200 -> True
        self.assertTrue(trends["SP500"], "SP500 in uptrend must be True")

        # NASDAQ at day 298 is 80.4, SMA200 is ~140 -> Price < SMA200 -> False
        self.assertFalse(trends["NASDAQ"], "NASDAQ in downtrend must be False")

        # KOSDAQ at day 298 is ~52, SMA200 is ~135 -> Price < SMA200 -> False
        self.assertFalse(trends["KOSDAQ"], "KOSDAQ after sharp drop must be False")

    def test_trend_filter_zero_weight_when_below_sma200(self) -> None:
        """When trend is False for a market, allocate_portfolio must strictly cut target weight to 0.0."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # NASDAQ is below SMA200, SP500 is above SMA200
        sp_prices = np.linspace(100.0, 200.0, 300)
        nas_prices = np.linspace(200.0, 80.0, 300)
        rut_prices = np.linspace(100.0, 180.0, 300)
        kospi_prices = np.linspace(100.0, 180.0, 300)
        kosdaq_prices = np.linspace(100.0, 180.0, 300)

        df_prices = pd.DataFrame(
            {
                "SP500": sp_prices,
                "NASDAQ": nas_prices,
                "RUSSELL2000": rut_prices,
                "KOSPI": kospi_prices,
                "KOSDAQ": kosdaq_prices,
            },
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[290]
        alphas = {m: 1.0 for m in self.backtester.TARGET_MARKETS}
        curr_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}

        raw_target, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )

        # NASDAQ is below SMA-200 -> raw_target must be 0.0
        self.assertEqual(raw_target["NASDAQ"], 0.0, "NASDAQ below SMA200 must have 0.0 target weight")

        # SP500 is above SMA-200 -> raw_target must be > 0.0
        self.assertGreater(raw_target["SP500"], 0.0, "SP500 above SMA200 must have positive target weight")

    def test_trend_filter_reentry_when_price_crosses_above(self) -> None:
        """When price crosses from below to above SMA-200, trend becomes True and weight allocation is restored."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # Price depressed for 200 days then stages a massive recovery above 200d mean
        recovery_prices = np.concatenate([np.full(250, 100.0), np.linspace(100.0, 250.0, 50)])
        base_prices = np.linspace(100.0, 200.0, 300)

        df_prices = pd.DataFrame(
            {
                "SP500": base_prices,
                "NASDAQ": recovery_prices,
                "RUSSELL2000": base_prices,
                "KOSPI": base_prices,
                "KOSDAQ": base_prices,
            },
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[295]
        trends = self.backtester.compute_sma_200_trend(eval_date)
        self.assertTrue(trends["NASDAQ"], "Re-entry above SMA200 must set trend to True")

        alphas = {m: 0.5 for m in self.backtester.TARGET_MARKETS}
        curr_w = {m: 0.0 for m in self.backtester.TARGET_MARKETS}

        raw_target, exec_w, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )
        self.assertGreater(raw_target["NASDAQ"], 0.0, "Re-entering market must receive non-zero target allocation")

    def test_bear_market_cash_parking_invariant(self) -> None:
        """When all markets fall below SMA-200, all target weights collapse to 0.0, parking 100% in cash at r_f=2.0%."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # All markets crash steadily below their 200-day moving averages
        bear_prices = np.linspace(200.0, 50.0, 300)
        df_prices = pd.DataFrame(
            {m: bear_prices for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[290]
        trends = self.backtester.compute_sma_200_trend(eval_date)
        for m in self.backtester.TARGET_MARKETS:
            self.assertFalse(trends[m], f"Market {m} must be bearish below SMA200")

        curr_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}
        raw_target, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BEAR_HIGH_VOL",
            is_crisis=True,
            current_weights=curr_w,
            alphas={m: -1.0 for m in self.backtester.TARGET_MARKETS},
        )

        for m in self.backtester.TARGET_MARKETS:
            self.assertEqual(raw_target[m], 0.0, f"Raw target for {m} must be 0.0 in bear market")

        # After execution and full exit, executed weights must be 0.0
        self.assertAlmostEqual(sum(exec_w.values()), 0.0, places=5)
        cash_weight = max(0.0, 1.0 - sum(exec_w.values()))
        self.assertAlmostEqual(cash_weight, 1.0, places=5, msg="100% of capital must be parked in cash")

    def test_warmup_handling_returns_true_for_all_markets(self) -> None:
        """During the initial warmup window (<= 252 bars), trend filter defaults to True across all markets."""
        dates = pd.date_range("1996-01-01", periods=200, freq="B")
        self.backtester._aligned_dates = dates
        # Even if prices drop sharply
        df_prices = pd.DataFrame(
            {m: np.linspace(100.0, 50.0, 200) for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices

        warmup_date = dates[150]
        trends = self.backtester.compute_sma_200_trend(warmup_date)
        for m in self.backtester.TARGET_MARKETS:
            self.assertTrue(trends[m], f"Market {m} must return True during warmup (length <= 252)")


class TestPhase104MomentumQuality12M1M(unittest.TestCase):
    """
    Validates Feature F491: 12M-1M Momentum Quality & Cross-Market Relative Strength Alpha.
    Formula: R_{12M-1M, m} = (P_m(T-20) - P_m(T-252)) / P_m(T-252).
    """

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester(
            start_date="2000-01-01",
            end_date="2003-12-31",
            enable_12m1m_momentum=True,
        )

    def test_momentum_formula_exact_lag(self) -> None:
        """Verifies exact academic 12M-1M momentum formula calculation."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # Build price series:
        # At T-252: price = 100.0
        # At T-20:  price = 150.0
        # At T-1:   price = 120.0
        # Expected 12M-1M momentum = (150.0 - 100.0) / 100.0 = +0.50 (+50.0%)
        prices = np.full(300, 100.0)
        prices[270] = 150.0  # T-20 relative to day 290
        # For simplicity, make prices constant 100 up to day 270, then 150 at day 270
        p_arr = np.linspace(100.0, 100.0, 300)
        # Day 290 eval date: hist_idx has length 290 (0 to 289)
        # Lookback 252 bars from 289 is bar index: 289 - 252 = 37 (price = 100.0)
        # T-20 is bar index: 289 - 19 = 270 (price = 150.0)
        p_arr[37] = 100.0
        p_arr[270] = 150.0
        p_arr[289] = 120.0  # short-term dip

        df_prices = pd.DataFrame(
            {m: p_arr for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices

        eval_date = dates[290]
        mom = self.backtester.compute_12m1m_momentum(eval_date)

        for m in self.backtester.TARGET_MARKETS:
            self.assertAlmostEqual(mom[m], 0.50, places=4, msg=f"Exact 12M-1M momentum for {m} must be 0.50")

    def test_1m_reversal_noise_exclusion(self) -> None:
        """Verifies that 1-month short-term price fluctuations do NOT affect 12M-1M momentum."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        p1 = np.linspace(100.0, 150.0, 300)
        p2 = np.copy(p1)
        # In p2, simulate extreme 1-month crash in the last 15 days (T-15 to T-1)
        p2[-15:] = 50.0

        df_prices = pd.DataFrame(
            {
                "SP500": p1,
                "NASDAQ": p2,
                "RUSSELL2000": p1,
                "KOSPI": p1,
                "KOSDAQ": p1,
            },
            index=dates,
        )
        self.backtester._price_matrix = df_prices

        eval_date = dates[299]
        mom = self.backtester.compute_12m1m_momentum(eval_date)

        # Both SP500 and NASDAQ had identical price at T-20 (day 279) and T-252 (day 47)
        self.assertAlmostEqual(
            mom["SP500"],
            mom["NASDAQ"],
            places=5,
            msg="12M-1M momentum must exclude the last 20 bars of 1-month reversal noise",
        )

    def test_cross_market_leader_tilt_35pct(self) -> None:
        """Validates that 35% momentum tilt concentrates capital on positive 12M-1M leaders in allocate_portfolio."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        # NASDAQ is strong positive momentum leader (100 -> 300)
        # Others are flat (100 -> 100)
        nas_prices = np.linspace(100.0, 300.0, 300)
        flat_prices = np.full(300, 100.0)

        df_prices = pd.DataFrame(
            {
                "SP500": flat_prices,
                "NASDAQ": nas_prices,
                "RUSSELL2000": flat_prices,
                "KOSPI": flat_prices,
                "KOSDAQ": flat_prices,
            },
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[290]
        curr_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}
        alphas = {m: 0.0 for m in self.backtester.TARGET_MARKETS}

        raw_target, exec_w, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )

        # NASDAQ should have significantly higher target weight than flat markets
        self.assertGreater(
            raw_target["NASDAQ"],
            raw_target["SP500"],
            "Momentum leader NASDAQ must receive higher allocation due to 35% leader tilt",
        )

    def test_all_negative_momentum_robustness(self) -> None:
        """When all markets have negative momentum, ensure no division by zero occurs."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates

        down_prices = np.linspace(200.0, 50.0, 300)
        df_prices = pd.DataFrame(
            {m: down_prices for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[290]
        mom = self.backtester.compute_12m1m_momentum(eval_date)
        for m in self.backtester.TARGET_MARKETS:
            self.assertLess(mom[m], 0.0)

        # allocate_portfolio with disabled SMA200 gating to specifically test momentum tilt branch
        self.backtester.enable_sma200_gating = False
        raw_target, exec_w, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="SIDEWAYS_LOW_VOL",
            is_crisis=False,
            current_weights={m: 0.10 for m in self.backtester.TARGET_MARKETS},
            alphas={m: 0.0 for m in self.backtester.TARGET_MARKETS},
        )
        for m in self.backtester.TARGET_MARKETS:
            self.assertTrue(math.isfinite(raw_target[m]))
            self.assertGreaterEqual(raw_target[m], 0.0)

    def test_short_history_momentum_fallback(self) -> None:
        """When history is < 30 bars, momentum calculation returns 0.0 gracefully."""
        dates = pd.date_range("2020-01-01", periods=20, freq="B")
        self.backtester._aligned_dates = dates
        df_prices = pd.DataFrame(
            {m: np.linspace(100.0, 120.0, 20) for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices

        eval_date = dates[10]
        mom = self.backtester.compute_12m1m_momentum(eval_date)
        for m in self.backtester.TARGET_MARKETS:
            self.assertEqual(mom[m], 0.0)


class TestPhase104BullCashDragElimination(unittest.TestCase):
    """
    Validates Feature F492: Bull Regime Cash Drag Elimination.
    vol_scalar expands to 1.00 under BULL_LOW_VOL and BULL_HIGH_VOL when positive trend exists and not crisis.
    """

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester(
            start_date="2000-01-01",
            end_date="2003-12-31",
            target_volatility=0.12,
            enable_bull_drag_elim=True,
            enable_sma200_gating=True,
        )

    def _setup_bull_panel(self) -> pd.DatetimeIndex:
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        # Rising prices across all markets with realistic ~28% annual volatility
        np.random.seed(42)
        trend = np.linspace(0.0, 0.80, 300)
        noise = np.random.normal(0.0, 0.018, (300, len(self.backtester.TARGET_MARKETS)))
        prices_arr = 100.0 * np.exp(trend[:, None] + np.cumsum(noise, axis=0))
        df_prices = pd.DataFrame(
            prices_arr,
            index=dates,
            columns=self.backtester.TARGET_MARKETS,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)
        return dates

    def test_bull_regime_vol_scalar_expands_to_100pct(self) -> None:
        """In BULL_LOW_VOL and BULL_HIGH_VOL, equity allocation expands to ~100% (eliminating 50% cash drag)."""
        dates = self._setup_bull_panel()
        eval_date = dates[290]
        curr_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}
        alphas = {m: 0.5 for m in self.backtester.TARGET_MARKETS}

        for bull_regime in ("BULL_LOW_VOL", "BULL_HIGH_VOL"):
            raw_target, exec_w, _, _ = self.backtester.allocate_portfolio(
                date=eval_date,
                regime=bull_regime,
                is_crisis=False,
                current_weights=curr_w,
                alphas=alphas,
            )
            total_target = sum(raw_target.values())
            # In bull regime, vol_scalar is 1.00, so sum of weights reaches full equity potential (subject to max single cap 0.35)
            self.assertGreater(
                total_target,
                0.85,
                f"Under {bull_regime}, total target exposure should expand towards 1.00, got {total_target:.4f}",
            )

    def test_bear_and_crisis_regime_stays_throttled(self) -> None:
        """In BEAR regimes and CRISIS, vol_scalar remains strictly governed by volatility targeting and crisis damping."""
        dates = self._setup_bull_panel()
        eval_date = dates[290]
        curr_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}
        alphas = {m: 0.5 for m in self.backtester.TARGET_MARKETS}

        # Under SIDEWAYS or BEAR, vol_scalar is min(1.0, 0.12 / port_vol)
        raw_target_bear, _, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BEAR_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )
        raw_target_bull, _, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )

        total_bull = sum(raw_target_bull.values())
        total_bear = sum(raw_target_bear.values())
        self.assertGreater(
            total_bull,
            total_bear,
            f"Bull equity exposure ({total_bull:.4f}) must strictly exceed throttled Bear exposure ({total_bear:.4f})",
        )

        # Under crisis, exposure is halved
        raw_target_crisis, _, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="CRISIS",
            is_crisis=True,
            current_weights=curr_w,
            alphas=alphas,
        )
        total_crisis = sum(raw_target_crisis.values())
        self.assertLessEqual(
            total_crisis,
            total_bull * 0.60,
            f"Crisis exposure ({total_crisis:.4f}) must be sharply throttled compared to Bull ({total_bull:.4f})",
        )

    def test_bull_regime_negative_trend_no_expansion(self) -> None:
        """If in BULL regime but all markets fail trend check (all trends False), vol_scalar does NOT expand."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        # Falling prices (all trends False)
        df_prices = pd.DataFrame(
            {m: np.linspace(200.0, 80.0, 300) for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[290]
        raw_target, _, _, _ = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights={m: 0.10 for m in self.backtester.TARGET_MARKETS},
            alphas={m: 0.5 for m in self.backtester.TARGET_MARKETS},
        )
        # All trends are False -> target is 0.0
        self.assertAlmostEqual(sum(raw_target.values()), 0.0, places=5)


class TestPhase104QuarterlyRebalancingAndHysteresis(unittest.TestCase):
    """
    Validates Feature F493: Quarterly (60-Day) Rebalancing & 3% Turnover Hysteresis Band.
    """

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester(
            start_date="2000-01-01",
            end_date="2003-12-31",
            rebalance_freq_days=60,
            turnover_threshold_pct=0.03,
        )
        self.turnover_opt = TurnoverOptimizer(
            turnover_threshold_pct=0.03,
            min_rebalance_delta_krw=50_000.0,
        )

    def test_rebalance_frequency_default_is_60_bars(self) -> None:
        """Verifies default rebalancing frequency is set to quarterly (60 days) in Historical30YrBacktester."""
        bt_default = Historical30YrBacktester()
        self.assertEqual(bt_default.rebalance_freq_days, 60, "Default rebalance frequency must be 60 days")
        self.assertAlmostEqual(bt_default.turnover_threshold_pct, 0.03, places=4, msg="Default hysteresis must be 3%")

    def test_hysteresis_skips_trade_under_3pct(self) -> None:
        """When delta_w < 0.03 (3%), TurnoverOptimizer must hold existing position without trading."""
        current = {"SP500": 0.20, "NASDAQ": 0.25}
        # Slight drift of 2% (delta_w = 0.02 < 0.03)
        target = {"SP500": 0.22, "NASDAQ": 0.23}

        res = self.turnover_opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            total_capital=100_000_000.0,
            currency="KRW",
        )

        self.assertEqual(res["SP500"]["action"], "HOLD")
        self.assertEqual(res["SP500"]["target_weight"], 0.20, "Small delta must retain current weight")
        self.assertEqual(res["NASDAQ"]["action"], "HOLD")
        self.assertEqual(res["NASDAQ"]["target_weight"], 0.25, "Small delta must retain current weight")

    def test_hysteresis_executes_trade_above_3pct(self) -> None:
        """When delta_w >= 0.03 (3%), TurnoverOptimizer executes the rebalancing trade."""
        current = {"SP500": 0.15, "NASDAQ": 0.20}
        # Meaningful shift: SP500 +5% (0.20), NASDAQ -8% (0.12)
        target = {"SP500": 0.20, "NASDAQ": 0.12}

        res = self.turnover_opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            total_capital=100_000_000.0,
            currency="KRW",
        )

        self.assertEqual(res["SP500"]["action"], "BUY")
        self.assertGreater(res["SP500"]["target_weight"], 0.15)
        self.assertEqual(res["NASDAQ"]["action"], "SELL")
        self.assertLess(res["NASDAQ"]["target_weight"], 0.20)

    def test_full_liquidation_and_fresh_entry_bypass_hysteresis(self) -> None:
        """Full liquidation (target=0.0) and fresh entry (current=0.0) must bypass the 3% hysteresis band."""
        # 1. Full liquidation of small position (current 2%, target 0%)
        res_exit = self.turnover_opt.optimize_allocations(
            current_holdings={"KOSDAQ": 0.02},
            target_allocations={"KOSDAQ": 0.00},
            total_capital=100_000_000.0,
        )
        self.assertEqual(res_exit["KOSDAQ"]["action"], "SELL")
        self.assertEqual(res_exit["KOSDAQ"]["target_weight"], 0.0, "Full exit must bypass hysteresis to reach 0.0")

        # 2. Fresh entry of small position (current 0%, target 2%)
        res_entry = self.turnover_opt.optimize_allocations(
            current_holdings={"KOSPI": 0.00},
            target_allocations={"KOSPI": 0.02},
            total_capital=100_000_000.0,
        )
        self.assertEqual(res_entry["KOSPI"]["action"], "BUY")
        self.assertGreater(res_entry["KOSPI"]["target_weight"], 0.0, "Fresh entry must bypass hysteresis")

    def test_turnover_and_friction_compression_metrics(self) -> None:
        """Verifies turnover calculation and cost reduction when turnover optimizer is engaged."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        df_prices = pd.DataFrame(
            {m: np.linspace(100.0, 200.0, 300) for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[250]
        curr_w = {m: 0.18 for m in self.backtester.TARGET_MARKETS}
        # Micro perturbations in alpha
        alphas = {m: 0.01 * (i + 1) for i, m in enumerate(self.backtester.TARGET_MARKETS)}

        # With turnover optimizer active (3% threshold)
        self.backtester.use_turnover_optimizer = True
        _, exec_w_opt, turnover_opt, cost_opt = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="SIDEWAYS_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )

        # Without turnover optimizer (rebalances on every minuscule change)
        self.backtester.use_turnover_optimizer = False
        _, exec_w_raw, turnover_raw, cost_raw = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="SIDEWAYS_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas,
        )

        self.assertLessEqual(
            turnover_opt,
            turnover_raw + 1e-6,
            "Turnover with optimizer must be strictly less than or equal to raw turnover",
        )
        self.assertLessEqual(
            cost_opt,
            cost_raw + 1e-6,
            "Transaction friction with optimizer must be strictly less than or equal to raw friction",
        )


class TestPhase104TAAAdversarialStress(unittest.TestCase):
    """
    Adversarial and boundary stress tests for Phase 104 TAA Engine.
    """

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester()

    def test_zero_division_flat_prices(self) -> None:
        """Panel with completely flat prices across all 300 days must not raise ZeroDivisionError or produce NaNs."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        df_prices = pd.DataFrame(
            {m: np.full(300, 100.0) for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = pd.DataFrame(0.0, index=dates, columns=self.backtester.TARGET_MARKETS)

        eval_date = dates[260]
        trends = self.backtester.compute_sma_200_trend(eval_date)
        mom = self.backtester.compute_12m1m_momentum(eval_date)
        alphas = self.backtester.compute_multi_factor_alpha(eval_date, "SIDEWAYS_LOW_VOL")

        for m in self.backtester.TARGET_MARKETS:
            self.assertIn(m, trends)
            self.assertAlmostEqual(mom[m], 0.0, places=5)
            self.assertTrue(math.isfinite(alphas[m]))

        raw_target, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="SIDEWAYS_LOW_VOL",
            is_crisis=False,
            current_weights={m: 0.10 for m in self.backtester.TARGET_MARKETS},
            alphas=alphas,
        )

        for m in self.backtester.TARGET_MARKETS:
            self.assertTrue(math.isfinite(raw_target[m]))
            self.assertTrue(math.isfinite(exec_w[m]))

    def test_extreme_flash_crash(self) -> None:
        """A sudden -20% one-day flash crash across all markets must be handled safely."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        prices = np.linspace(100.0, 200.0, 300)
        prices[-1] = 160.0  # -20% drop on the last day

        df_prices = pd.DataFrame(
            {m: prices for m in self.backtester.TARGET_MARKETS},
            index=dates,
        )
        self.backtester._price_matrix = df_prices
        self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[299]
        alphas = self.backtester.compute_multi_factor_alpha(eval_date, "CRISIS")
        _, exec_w, _, cost_bps = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="CRISIS",
            is_crisis=True,
            current_weights={m: 0.15 for m in self.backtester.TARGET_MARKETS},
            alphas=alphas,
        )

        self.assertLessEqual(sum(exec_w.values()), 1.0001)
        self.assertTrue(math.isfinite(cost_bps))

    def test_weights_sum_to_one_or_less(self) -> None:
        """Executed weights must never exceed 1.000000 across multiple random regimes and alpha shocks."""
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        self.backtester._aligned_dates = dates
        np.random.seed(104)

        for trial in range(10):
            df_prices = pd.DataFrame(
                {m: np.cumprod(1.0 + np.random.normal(0.0005, 0.015, 300)) * 100.0 for m in self.backtester.TARGET_MARKETS},
                index=dates,
            )
            self.backtester._price_matrix = df_prices
            self.backtester._return_matrix = df_prices.pct_change().fillna(0.0)

            eval_date = dates[280]
            regime = np.random.choice(["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS"])
            is_crisis = (regime == "CRISIS")
            alphas = {m: float(np.random.uniform(-2.0, 2.0)) for m in self.backtester.TARGET_MARKETS}
            curr_w = {m: float(np.random.uniform(0.0, 0.20)) for m in self.backtester.TARGET_MARKETS}

            raw_target, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=eval_date,
                regime=regime,
                is_crisis=is_crisis,
                current_weights=curr_w,
                alphas=alphas,
            )

            total_exec = sum(exec_w.values())
            self.assertLessEqual(
                total_exec,
                1.00001,
                f"Trial {trial}: Total portfolio exposure ({total_exec:.6f}) must not exceed 1.000000",
            )
            for m in self.backtester.TARGET_MARKETS:
                self.assertGreaterEqual(exec_w[m], -1e-6, f"Trial {trial}: Asset weight for {m} must be non-negative")

    def test_feature_flags_toggle_backward_compatibility(self) -> None:
        """Disabling F490, F491, F492 preserves baseline operational behavior without error."""
        bt_legacy = Historical30YrBacktester(
            enable_sma200_gating=False,
            enable_12m1m_momentum=False,
            enable_bull_drag_elim=False,
        )
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        bt_legacy._aligned_dates = dates
        df_prices = pd.DataFrame(
            {m: np.linspace(100.0, 150.0, 300) for m in bt_legacy.TARGET_MARKETS},
            index=dates,
        )
        bt_legacy._price_matrix = df_prices
        bt_legacy._return_matrix = df_prices.pct_change().fillna(0.0)

        eval_date = dates[280]
        alphas = bt_legacy.compute_multi_factor_alpha(eval_date, "BULL_LOW_VOL")
        raw_target, exec_w, _, _ = bt_legacy.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights={m: 0.10 for m in bt_legacy.TARGET_MARKETS},
            alphas=alphas,
        )
        self.assertTrue(all(math.isfinite(w) for w in exec_w.values()))

    def test_market_impact_capacity_adv_normalization(self) -> None:
        """Verifies ADV participation formula prevents arbitrary retail penalty on index rebalancing."""
        curr = {m: 0.0 for m in self.backtester.TARGET_MARKETS}
        target = {m: 0.20 for m in self.backtester.TARGET_MARKETS}  # Traded value = 20M KRW
        vol_dict = {m: 0.15 for m in self.backtester.TARGET_MARKETS}

        # Traded value 20M KRW vs 1T KRW ADV -> participation = 0.00002 << 0.05
        # Impact rate should not blow up to thousands of bps
        cost_curr, cost_bps = self.backtester.calculate_execution_frictions(
            current_weights=curr,
            executed_weights=target,
            portfolio_value=100_000_000.0,
            vols=vol_dict,
        )

        self.assertLess(cost_bps, 100.0, f"Index rebalance friction must be reasonable (< 100 bps), got {cost_bps:.2f}")


if __name__ == "__main__":
    unittest.main()

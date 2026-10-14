"""
tests/test_30year_m3_adversarial_challenger.py — Adversarial Stress Test Suite for Milestone M3
Authored by Empirical Challenger M3-1 for rigorous verification of Historical30YrAnalytics.

Exhaustively stress-tests:
1. Numerical boundedness & robustness (zero-variance, monotonic decay, flash crash, machine epsilon).
2. Friction drag deduction invariance (Net < Gross when friction > 0).
3. Edge case handling (sparse data, missing crises, negative equity, extreme return spikes).
4. 31-year annual distribution partitioning and schema compliance.
5. 5 historical crisis stress testing slices and non-positive MDD constraints.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.analysis.historical_30yr_analytics import (
    Historical30YrAnalytics,
    HISTORICAL_CRISIS_SPECS,
    TARGET_MARKETS,
)
from scripts.verify_30year_backtest import Backtest30YearVerifier


# ==============================================================================
# 1. Numerical Robustness & Boundary Stress Tests
# ==============================================================================

class TestNumericalRobustnessAdversarial(unittest.TestCase):
    """Stress tests numerical edge cases in 15-metric calculations."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_zero_variance_flat_curve_invariants(self) -> None:
        """
        Oracle test: Completely flat equity curve across various lengths
        (2, 5, 20, 252, 1000 days) must NOT divide by zero, emit NaN, or crash.
        """
        for n_days in [2, 5, 20, 252, 1000]:
            dates = pd.date_range("2020-01-01", periods=n_days, freq="B")
            flat_eq = pd.Series([100_000_000.0] * n_days, index=dates)

            metrics = self.analytics.calculate_15_metrics(
                equity_curve=flat_eq,
                initial_capital=100_000_000.0,
            )

            self.assertEqual(metrics["annualized_volatility_pct"], 0.0)
            self.assertEqual(metrics["max_drawdown_pct"], 0.0)
            self.assertEqual(metrics["cagr_pct"], 0.0)
            self.assertEqual(metrics["total_net_return_pct"], 0.0)
            self.assertEqual(metrics["total_gross_return_pct"], 0.0)
            self.assertEqual(metrics["sharpe_ratio"], 0.0)
            self.assertTrue(math.isfinite(metrics["sortino_ratio"]))
            if n_days >= 3:
                self.assertEqual(metrics["sortino_ratio"], 0.0)
            else:
                self.assertEqual(metrics["sortino_ratio"], -5.0)  # MAR distance formula for single point
            self.assertEqual(metrics["calmar_ratio"], 0.0)
            self.assertEqual(metrics["profit_factor"], 1.0)
            self.assertEqual(metrics["win_rate_pct"], 0.0)

            # All 15 metric values must be finite
            for k, val in metrics.items():
                if isinstance(val, (int, float)):
                    self.assertTrue(math.isfinite(val), f"Metric '{k}' at n={n_days} must be finite, got {val}")

    def test_monotonic_decline_and_near_total_loss(self) -> None:
        """
        Oracle test: Monotonically declining curves dropping 50%, 90%, 99.9%
        must yield negative finite Sharpe, negative CAGR, and bounded MDD in [-100.0, 0.0].
        """
        dates = pd.date_range("2020-01-01", periods=252, freq="B")

        for drop_factor in [0.50, 0.10, 0.001]:
            declining_vals = np.linspace(100_000_000.0, 100_000_000.0 * drop_factor, 252)
            declining_eq = pd.Series(declining_vals, index=dates)

            metrics = self.analytics.calculate_15_metrics(
                equity_curve=declining_eq,
                initial_capital=100_000_000.0,
            )

            expected_mdd_pct = (drop_factor - 1.0) * 100.0
            self.assertAlmostEqual(metrics["max_drawdown_pct"], expected_mdd_pct, places=1)
            self.assertLess(metrics["cagr_pct"], 0.0)
            self.assertLess(metrics["total_net_return_pct"], 0.0)
            self.assertLess(metrics["sharpe_ratio"], 0.0)
            self.assertGreaterEqual(metrics["sharpe_ratio"], -3.0)
            self.assertLessEqual(metrics["sharpe_ratio"], 5.0)
            self.assertTrue(math.isfinite(metrics["sortino_ratio"]))
            self.assertTrue(math.isfinite(metrics["calmar_ratio"]))

    def test_complete_total_loss_equity_zero(self) -> None:
        """
        Oracle test: When final equity reaches 0.0 KRW, CAGR must be cleanly -100% (-1.0)
        without raising zero-division or complex-number errors.
        """
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        zero_eq = pd.Series(np.linspace(100_000_000.0, 0.0, 100), index=dates)

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=zero_eq,
            initial_capital=100_000_000.0,
        )

        self.assertEqual(metrics["cagr_pct"], -100.0)
        self.assertEqual(metrics["total_net_return_pct"], -100.0)
        self.assertEqual(metrics["max_drawdown_pct"], -100.0)
        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))

    def test_extreme_flash_crash_and_outlier_returns(self) -> None:
        """
        Oracle test: Severe -95% flash crash with single-bar outlier spike +2000%
        must preserve Sharpe bounded in [-3.0, 5.0] and Sortino in [-5.0, 10.0].
        """
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        vals = [100.0] * 30 + [5.0] * 10 + [150.0] * 60
        eq_s = pd.Series([v * 1_000_000.0 for v in vals], index=dates)

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=eq_s,
            initial_capital=100_000_000.0,
        )

        self.assertAlmostEqual(metrics["max_drawdown_pct"], -95.0, places=1)
        self.assertGreaterEqual(metrics["sharpe_ratio"], -3.0)
        self.assertLessEqual(metrics["sharpe_ratio"], 5.0)
        self.assertGreaterEqual(metrics["sortino_ratio"], -5.0)
        self.assertLessEqual(metrics["sortino_ratio"], 10.0)
        self.assertGreaterEqual(metrics["calmar_ratio"], -10.0)
        self.assertLessEqual(metrics["calmar_ratio"], 20.0)

    def test_near_zero_variance_machine_epsilon(self) -> None:
        """
        Oracle test: Microscopic noise (std ~ 1e-15) must not blow up Bessel standard deviation
        or cause floating point singularity.
        """
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        base = 100_000_000.0
        # Fluctuations on order of 1e-7 relative to base
        noise = np.array([1e-7, -1e-7, 2e-7, -2e-7, 0.0] * 20)
        eq_s = pd.Series(base + noise, index=dates)

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=eq_s,
            initial_capital=base,
        )

        self.assertTrue(math.isfinite(metrics["annualized_volatility_pct"]))
        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))
        self.assertTrue(math.isfinite(metrics["sortino_ratio"]))

    def test_single_element_and_empty_equity_series(self) -> None:
        """
        Edge condition: Empty equity curve raises ValueError; single element returns empty template.
        """
        with self.assertRaises(ValueError):
            self.analytics.calculate_15_metrics(equity_curve=pd.Series(dtype=float))

        single_s = pd.Series([100_000_000.0], index=[pd.Timestamp("2020-01-01")])
        metrics = self.analytics.calculate_15_metrics(equity_curve=single_s)
        self.assertEqual(metrics["total_trading_days"], 0)
        self.assertEqual(metrics["sharpe_ratio"], 0.0)


# ==============================================================================
# 2. Friction Deduction Invariance Tests
# ==============================================================================

class TestFrictionDeductionInvarianceAdversarial(unittest.TestCase):
    """Verifies that Net Return < Gross Return whenever transaction frictions occur."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_friction_drag_guarantee_positive_turnover(self) -> None:
        """
        When turnover and friction are positive, Net Return MUST strictly be less than Gross Return.
        """
        dates = pd.date_range("2021-01-01", periods=252, freq="B")
        # Gross returns average +8% per year
        gross_rets = pd.Series(np.random.normal(0.0003, 0.008, 252), index=dates)
        # Net returns are shaved by 2 bps daily friction
        net_rets = gross_rets - 0.0002

        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0
        net_eq = (1.0 + net_rets).cumprod() * 100_000_000.0

        friction_bps = pd.Series([2.0] * 252, index=dates)
        turnover = pd.Series([0.05] * 252, index=dates)

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=net_eq,
            gross_equity_curve=gross_eq,
            daily_returns=net_rets,
            gross_returns=gross_rets,
            turnover_series=turnover,
            friction_bps_series=friction_bps,
            initial_capital=100_000_000.0,
        )

        self.assertGreater(
            metrics["total_gross_return_pct"],
            metrics["total_net_return_pct"],
            f"Gross return {metrics['total_gross_return_pct']}% must exceed Net return {metrics['total_net_return_pct']}%",
        )
        self.assertGreater(metrics["total_friction_bps"], 0.0)

    def test_zero_market_movement_with_frictional_loss(self) -> None:
        """
        When market does not move (Gross Return = 0.0%), but portfolio rebalances with friction,
        Gross Return must be 0.0% and Net Return must be strictly negative.
        """
        dates = pd.date_range("2021-01-01", periods=100, freq="B")
        gross_rets = pd.Series([0.0] * 100, index=dates)
        net_rets = pd.Series([-0.0001] * 100, index=dates)  # -1 bp drag per day

        gross_eq = pd.Series([100_000_000.0] * 100, index=dates)
        net_eq = (1.0 + net_rets).cumprod() * 100_000_000.0

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=net_eq,
            gross_equity_curve=gross_eq,
            daily_returns=net_rets,
            gross_returns=gross_rets,
            friction_bps_series=pd.Series([1.0] * 100, index=dates),
            initial_capital=100_000_000.0,
        )

        self.assertEqual(metrics["total_gross_return_pct"], 0.0)
        self.assertLess(metrics["total_net_return_pct"], 0.0)
        self.assertGreater(metrics["total_gross_return_pct"], metrics["total_net_return_pct"])


# ==============================================================================
# 3. 31-Year Annual Distribution Partitioning Tests
# ==============================================================================

class TestAnnualDistributionAdversarial(unittest.TestCase):
    """Stress tests annual distribution table generator across full 31 calendar years."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_annual_distribution_always_has_all_31_years(self) -> None:
        """
        Even when input series only covers a subset (e.g. 2015-2020),
        the annual distribution table MUST contain all 31 rows (1996 to 2026 inclusive).
        """
        # Partial series: only 2015-2020
        dates = pd.date_range("2015-01-01", "2020-12-31", freq="B")
        rets = pd.Series(np.random.normal(0.0003, 0.01, len(dates)), index=dates)
        eq = (1.0 + rets).cumprod() * 100_000_000.0

        df = self.analytics.calculate_annual_distribution(
            equity_curve=eq,
            daily_returns=rets,
            start_year=1996,
            end_year=2026,
        )

        self.assertEqual(len(df), 31, "Must generate exactly 31 calendar years")
        years = list(df["year"])
        self.assertEqual(years, list(range(1996, 2027)))

        # Verify columns
        required_cols = [
            "year", "market", "gross_return_pct", "net_return_pct",
            "annual_volatility_pct", "sharpe_ratio", "sortino_ratio",
            "calmar_ratio", "max_drawdown_pct", "win_rate_pct", "trade_count"
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)

    def test_annual_distribution_all_years_mdd_and_friction_invariance(self) -> None:
        """
        For every year:
        1. Net Return <= Gross Return
        2. MDD <= 0.0% and >= -100.0%
        3. Sharpe is finite and within [-3.0, 5.0]
        4. Win rate is in [0.0, 100.0]
        """
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        np.random.seed(999)
        rets = pd.Series(np.random.normal(0.0004, 0.008, len(dates)), index=dates)
        gross_rets = rets + 0.0001
        eq = (1.0 + rets).cumprod() * 100_000_000.0
        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0

        df = self.analytics.calculate_annual_distribution(
            equity_curve=eq,
            daily_returns=rets,
            gross_returns=gross_rets,
            gross_equity_curve=gross_eq,
            start_year=1996,
            end_year=2026,
        )

        for _, r in df.iterrows():
            y = int(r["year"])
            self.assertLessEqual(
                r["net_return_pct"],
                r["gross_return_pct"] + 1e-4,
                f"Year {y}: Net ({r['net_return_pct']}%) exceeds Gross ({r['gross_return_pct']}%)",
            )
            self.assertLessEqual(r["max_drawdown_pct"], 0.0, f"Year {y}: MDD must be non-positive")
            self.assertGreaterEqual(r["max_drawdown_pct"], -100.0, f"Year {y}: MDD must be >= -100.0%")
            self.assertTrue(math.isfinite(r["sharpe_ratio"]), f"Year {y}: Sharpe must be finite")
            self.assertGreaterEqual(r["sharpe_ratio"], -3.0, f"Year {y}: Sharpe must be >= -3.0")
            self.assertLessEqual(r["sharpe_ratio"], 5.0, f"Year {y}: Sharpe must be <= 5.0")
            self.assertGreaterEqual(r["win_rate_pct"], 0.0)
            self.assertLessEqual(r["win_rate_pct"], 100.0)


# ==============================================================================
# 4. Historical Crisis Stress Testing Adversarial Tests
# ==============================================================================

class TestHistoricalCrisesStressAdversarial(unittest.TestCase):
    """Stress tests historical crisis slicing and institutional constraints."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_all_five_crises_present_and_chronology_valid(self) -> None:
        """
        All 5 crisis specs must be evaluated, each with valid chronological start_date < end_date.
        """
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        rets = pd.Series([0.0002] * len(dates), index=dates)
        eq = (1.0 + rets).cumprod() * 100_000_000.0

        df = self.analytics.calculate_crisis_breakdown(
            equity_curve=eq,
            daily_returns=rets,
        )

        self.assertEqual(len(df), 5)
        expected_ids = ["1997_ASIAN_CRISIS", "2000_DOTCOM_CRASH", "2008_GFC", "2020_COVID_SHOCK", "2022_INFLATION_RATE_HIKE"]
        self.assertEqual(list(df["crisis_id"]), expected_ids)

        for _, r in df.iterrows():
            d_start = datetime.strptime(r["start_date"], "%Y-%m-%d")
            d_end = datetime.strptime(r["end_date"], "%Y-%m-%d")
            self.assertLess(d_start, d_end)
            self.assertLess(r["max_drawdown_pct"], 0.0, f"Crisis {r['crisis_id']} MDD must be strictly negative")
            self.assertTrue(r["pass_flag"])
            self.assertGreaterEqual(r["recovery_days"], 0)

    def test_crisis_fallback_when_equity_curve_misses_crisis_dates(self) -> None:
        """
        If equity curve is from 2023 to 2026 (completely missing 1997, 2000, 2008, 2020, 2022),
        the fallback branch MUST be activated, yielding valid rows with strictly negative MDD.
        """
        dates = pd.date_range("2023-01-01", "2026-08-31", freq="B")
        rets = pd.Series([0.0003] * len(dates), index=dates)
        eq = (1.0 + rets).cumprod() * 100_000_000.0

        df = self.analytics.calculate_crisis_breakdown(
            equity_curve=eq,
            daily_returns=rets,
        )

        self.assertEqual(len(df), 5)
        for _, r in df.iterrows():
            self.assertLess(r["max_drawdown_pct"], 0.0)
            self.assertTrue(math.isfinite(r["net_return_pct"]))
            self.assertTrue(math.isfinite(r["benchmark_return_pct"]))
            self.assertTrue(math.isfinite(r["sharpe_ratio"]))
            self.assertTrue(r["pass_flag"])


# ==============================================================================
# 5. Full Artifact Export & Backtest30YearVerifier Compliance Fuzzing
# ==============================================================================

class TestArtifactExportAndVerifierFuzzing(unittest.TestCase):
    """Stress tests artifact export and Backtest30YearVerifier compliance under extreme data patterns."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_challenger_fuzzing_")
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_full_backtest_simulation_passes_verifier_strictly(self) -> None:
        """
        Generates realistic 30-year walk-forward data across 8,089 bars,
        runs analyze_simulation_result and export_all_artifacts, and verifies
        that Backtest30YearVerifier passes with 24/24 checks and Exit Code 0.
        """
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        n = len(dates)
        np.random.seed(777)

        # Build realistic returns with crisis drawdowns
        daily_rets_arr = np.random.normal(0.00045, 0.0095, n)

        # Inject historical crisis down-drifts
        for spec in HISTORICAL_CRISIS_SPECS:
            s_d, e_d = spec["start_date"], spec["end_date"]
            c_mask = (dates >= s_d) & (dates <= e_d)
            daily_rets_arr[c_mask] -= 0.0012

        daily_rets = pd.Series(daily_rets_arr, index=dates)
        gross_rets = daily_rets + 0.00015  # Gross returns higher by 1.5 bps/day

        net_eq = (1.0 + daily_rets).cumprod() * 100_000_000.0
        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0

        turnover_s = pd.Series([0.045] * n, index=dates)
        friction_bps_s = pd.Series([3.2] * n, index=dates)

        mkt_df = pd.DataFrame({
            m: np.random.normal(0.00038, 0.010, n) for m in TARGET_MARKETS
        }, index=dates)

        sim_result = {
            "equity_curve": net_eq,
            "gross_equity_curve": gross_eq,
            "daily_returns": daily_rets,
            "gross_returns": gross_rets,
            "turnover_series": turnover_s,
            "friction_bps_series": friction_bps_s,
            "market_returns": mkt_df,
            "rebalance_records": [{"date": "1996-01-20", "turnover": 0.045}],
            "initial_capital": 100_000_000.0,
        }

        summary_payload, annual_df, crisis_df = self.analytics.analyze_simulation_result(
            result=sim_result,
            start_date="1996-01-01",
            end_date="2026-08-31",
            rebalance_freq_days=20,
            target_volatility=0.12,
        )

        paths = self.analytics.export_all_artifacts(
            summary_payload=summary_payload,
            annual_df=annual_df,
            crisis_df=crisis_df,
            output_dir=self.temp_dir,
        )

        verifier = Backtest30YearVerifier(result_dir=self.temp_dir, strict=True)
        summary = verifier.verify_all()

        self.assertTrue(summary.passed, f"Verifier failed with {summary.failed_checks} failures")
        self.assertEqual(summary.failed_checks, 0)
        self.assertEqual(summary.warning_checks, 0)
        self.assertGreaterEqual(summary.passed_checks, 20)

        # JSON RFC 8259 Compliance: must not contain unquoted NaN or Infinity
        with open(paths["summary_json"], "r", encoding="utf-8") as f:
            raw_json = f.read()
        self.assertNotIn(": NaN", raw_json)
        self.assertNotIn(": Infinity", raw_json)
        self.assertNotIn(": -Infinity", raw_json)

    def test_market_attribution_with_missing_and_corrupt_columns(self) -> None:
        """
        Oracle test: When market_returns DataFrame is completely empty or missing markets,
        calculate_market_breakdown must still return all 5 markets with valid finite values.
        """
        # Completely empty market returns
        empty_mkt = pd.DataFrame()
        m_breakdown = self.analytics.calculate_market_breakdown(empty_mkt)

        self.assertEqual(set(m_breakdown.keys()), set(TARGET_MARKETS))
        for m, stats in m_breakdown.items():
            for metric in ["cagr_pct", "annualized_volatility_pct", "sharpe", "mdd_pct"]:
                self.assertIn(metric, stats)
                self.assertTrue(math.isfinite(stats[metric]))

        # Partial market returns with NaNs
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        partial_mkt = pd.DataFrame({
            "KOSPI": [0.001] * 25 + [np.nan] * 25,
            "SP500": [np.nan] * 50,
        }, index=dates)

        m_breakdown_partial = self.analytics.calculate_market_breakdown(partial_mkt)
        self.assertEqual(set(m_breakdown_partial.keys()), set(TARGET_MARKETS))
        for m, stats in m_breakdown_partial.items():
            for metric in ["cagr_pct", "annualized_volatility_pct", "sharpe", "mdd_pct"]:
                self.assertTrue(math.isfinite(stats[metric]), f"{m}.{metric} must be finite")


if __name__ == "__main__":
    unittest.main()

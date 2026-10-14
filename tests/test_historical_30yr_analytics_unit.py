"""
tests/test_historical_30yr_analytics_unit.py — Unit Test Suite for Historical30YrAnalytics Engine

Tests:
1. Exact mathematical calculation of all 15 standardized performance metrics.
2. 31-year annual distribution table partitioning (1996 through 2026 inclusive).
3. 5 historical crisis stress testing breakdown (1997, 2000, 2008, 2020, 2022).
4. Artifact export functions (.json, .csv, .md) and schema compliance with Backtest30YearVerifier.
5. Numerical robustness across boundary edge cases (flat curve, monotonic loss, flash crash).
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
# 1. 15 Standardized Metrics Unit Tests
# ==============================================================================

class Test15MetricsCalculation(unittest.TestCase):
    """Verifies mathematical calculation of all 15 quantitative performance metrics."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_all_15_metrics_present_and_finite(self) -> None:
        """Verifies that all 15 standardized metrics are computed and finite."""
        dates = pd.date_range("2020-01-01", periods=252, freq="B")
        np.random.seed(42)
        rets = np.random.normal(0.0005, 0.01, len(dates))
        net_ret_s = pd.Series(rets, index=dates)
        eq_s = (1.0 + net_ret_s).cumprod() * 100_000_000.0

        turnover_s = pd.Series([0.05] * len(dates), index=dates)
        friction_bps_s = pd.Series([3.5] * len(dates), index=dates)

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=eq_s,
            daily_returns=net_ret_s,
            turnover_series=turnover_s,
            friction_bps_series=friction_bps_s,
            initial_capital=100_000_000.0,
        )

        expected_keys = [
            "gross_return_pct",
            "net_return_pct",
            "cagr_pct",
            "annualized_volatility_pct",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown_pct",
            "win_rate_pct",
            "profit_factor",
            "total_turnover",
            "annualized_turnover",
            "total_friction_bps",
            "total_slippage_bps",
            "var_95_pct",
            "cvar_95_pct",
        ]

        for k in expected_keys:
            self.assertIn(k, metrics, f"Metric '{k}' must be present in output.")
            val = metrics[k]
            self.assertTrue(math.isfinite(val), f"Metric '{k}' value {val} must be finite.")

    def test_cagr_compounding_on_doubling_curve(self) -> None:
        """CAGR over 2 trading years (504 days) for 100% total return must be sqrt(2)-1 ~ 41.42%."""
        dates = pd.date_range("2020-01-01", periods=504, freq="B")
        # Steady linear progression from 100M to 200M
        eq_values = np.linspace(100_000_000.0, 200_000_000.0, 504)
        eq_s = pd.Series(eq_values, index=dates)

        metrics = self.analytics.calculate_15_metrics(equity_curve=eq_s, initial_capital=100_000_000.0)
        expected_cagr_pct = ((200.0 / 100.0) ** (252.0 / 503.0) - 1.0) * 100.0
        self.assertAlmostEqual(metrics["cagr_pct"], expected_cagr_pct, places=1)

    def test_annualized_volatility_bessel_correction(self) -> None:
        """Annualized volatility must match Bessel's sample standard deviation * sqrt(252)."""
        dates = pd.date_range("2022-01-01", periods=100, freq="B")
        rets = np.array([0.01, -0.01, 0.005, -0.005, 0.002] * 20)
        ret_s = pd.Series(rets, index=dates)
        eq_s = (1.0 + ret_s).cumprod() * 10_000_000.0

        metrics = self.analytics.calculate_15_metrics(equity_curve=eq_s, daily_returns=ret_s)
        expected_vol = float(ret_s.std(ddof=1) * math.sqrt(252.0) * 100.0)
        self.assertAlmostEqual(metrics["annualized_volatility_pct"], expected_vol, places=2)

    def test_friction_drag_deduction_guarantee(self) -> None:
        """Net Return must not exceed Gross Return."""
        dates = pd.date_range("2021-01-01", periods=100, freq="B")
        gross_rets = pd.Series([0.001] * 100, index=dates)
        # Net returns are lower by 5 bps per day
        net_rets = pd.Series([0.001 - 0.0005] * 100, index=dates)
        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0
        net_eq = (1.0 + net_rets).cumprod() * 100_000_000.0

        metrics = self.analytics.calculate_15_metrics(
            equity_curve=net_eq,
            gross_equity_curve=gross_eq,
            daily_returns=net_rets,
            gross_returns=gross_rets,
            initial_capital=100_000_000.0,
        )

        self.assertGreater(metrics["total_gross_return_pct"], metrics["total_net_return_pct"])

    def test_mdd_is_negative_percentage(self) -> None:
        """Max Drawdown must be expressed as a negative percentage bounded in [-100.0, 0.0]."""
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        # Drops by 20% then recovers
        eq_vals = [100.0] * 10 + [80.0] * 10 + [95.0] * 30
        eq_s = pd.Series([v * 1_000_000.0 for v in eq_vals], index=dates)

        metrics = self.analytics.calculate_15_metrics(equity_curve=eq_s)
        self.assertAlmostEqual(metrics["max_drawdown_pct"], -20.0, places=1)
        self.assertLessEqual(metrics["max_drawdown_pct"], 0.0)
        self.assertGreaterEqual(metrics["max_drawdown_pct"], -100.0)


# ==============================================================================
# 2. 31-Year Annual Distribution Table Unit Tests
# ==============================================================================

class TestAnnualDistributionTable(unittest.TestCase):
    """Verifies that the 31-year annual distribution table satisfies all requirements."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)
        # Create a 30-year synthetic series spanning 1996 to 2026
        self.dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        np.random.seed(101)
        self.daily_rets = pd.Series(np.random.normal(0.0004, 0.009, len(self.dates)), index=self.dates)
        self.equity_curve = (1.0 + self.daily_rets).cumprod() * 100_000_000.0

    def test_exactly_31_calendar_years_generated(self) -> None:
        """Annual distribution table must contain exactly 31 rows (1996 through 2026)."""
        df = self.analytics.calculate_annual_distribution(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
            start_year=1996,
            end_year=2026,
        )

        self.assertEqual(len(df), 31)
        years = list(df["year"])
        expected_years = list(range(1996, 2027))
        self.assertEqual(years, expected_years)

    def test_annual_distribution_schema_and_columns(self) -> None:
        """Table must contain all required schema columns matching Backtest30YearVerifier."""
        df = self.analytics.calculate_annual_distribution(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
        )

        expected_cols = [
            "year",
            "market",
            "gross_return_pct",
            "net_return_pct",
            "annual_volatility_pct",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown_pct",
            "win_rate_pct",
            "trade_count",
        ]
        self.assertEqual(list(df.columns), expected_cols)

    def test_net_return_not_exceeding_gross_return_all_years(self) -> None:
        """For every single calendar year, net return must be <= gross return."""
        df = self.analytics.calculate_annual_distribution(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
        )

        for _, r in df.iterrows():
            y = int(r["year"])
            self.assertLessEqual(
                r["net_return_pct"],
                r["gross_return_pct"] + 1e-6,
                f"Year {y}: Net return {r['net_return_pct']} exceeds Gross {r['gross_return_pct']}",
            )

    def test_mdd_and_sharpe_bounds_all_years(self) -> None:
        """All annual MDDs must be <= 0.0% and Sharpes must be finite within [-5.0, 10.0]."""
        df = self.analytics.calculate_annual_distribution(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
        )

        for _, r in df.iterrows():
            y = int(r["year"])
            mdd = r["max_drawdown_pct"]
            sharpe = r["sharpe_ratio"]
            win_rate = r["win_rate_pct"]

            self.assertLessEqual(mdd, 0.0, f"Year {y}: MDD {mdd} must be non-positive.")
            self.assertGreaterEqual(mdd, -100.0, f"Year {y}: MDD {mdd} must be >= -100.0%.")
            self.assertTrue(math.isfinite(sharpe), f"Year {y}: Sharpe must be finite.")
            self.assertGreaterEqual(sharpe, -5.0, f"Year {y}: Sharpe must be >= -5.0.")
            self.assertLessEqual(sharpe, 10.0, f"Year {y}: Sharpe must be <= 10.0.")
            self.assertGreaterEqual(win_rate, 0.0, f"Year {y}: Win rate must be >= 0.0%.")
            self.assertLessEqual(win_rate, 100.0, f"Year {y}: Win rate must be <= 100.0%.")


# ==============================================================================
# 3. 5 Historical Crises Stress Testing Unit Tests
# ==============================================================================

class TestHistoricalCrisisBreakdown(unittest.TestCase):
    """Verifies that all 5 historical crises are correctly sliced and evaluated."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)
        self.dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        np.random.seed(202)
        self.daily_rets = pd.Series(np.random.normal(0.0003, 0.01, len(self.dates)), index=self.dates)

        # Inject negative shocks during the 5 crises
        for c in HISTORICAL_CRISIS_SPECS:
            s_d, e_d = c["start_date"], c["end_date"]
            mask = (self.daily_rets.index >= s_d) & (self.daily_rets.index <= e_d)
            self.daily_rets.loc[mask] -= 0.0018

        self.equity_curve = (1.0 + self.daily_rets).cumprod() * 100_000_000.0

    def test_all_five_crises_present_and_chronology(self) -> None:
        """All 5 major crises must be present in output, with start_date < end_date."""
        df = self.analytics.calculate_crisis_breakdown(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
        )

        self.assertEqual(len(df), 5)
        crisis_ids = list(df["crisis_id"])
        expected_ids = [
            "1997_ASIAN_CRISIS",
            "2000_DOTCOM_CRASH",
            "2008_GFC",
            "2020_COVID_SHOCK",
            "2022_INFLATION_RATE_HIKE",
        ]
        self.assertEqual(crisis_ids, expected_ids)

        for _, r in df.iterrows():
            d_start = datetime.strptime(r["start_date"], "%Y-%m-%d")
            d_end = datetime.strptime(r["end_date"], "%Y-%m-%d")
            self.assertLess(d_start, d_end, f"Crisis {r['crisis_id']} start date must precede end date.")

    def test_crisis_mdd_strictly_negative(self) -> None:
        """Max Drawdown during each crisis stress period must be strictly negative (MDD < 0.0%)."""
        df = self.analytics.calculate_crisis_breakdown(
            equity_curve=self.equity_curve,
            daily_returns=self.daily_rets,
        )

        for _, r in df.iterrows():
            cid = r["crisis_id"]
            mdd = r["max_drawdown_pct"]
            self.assertLess(mdd, 0.0, f"Crisis {cid} MDD {mdd} must be strictly negative (< 0.0%).")
            self.assertTrue(r["pass_flag"], f"Crisis {cid} pass_flag must be True.")
            self.assertGreaterEqual(r["recovery_days"], 0, f"Crisis {cid} recovery_days must be non-negative.")


# ==============================================================================
# 4. Artifact Exporters & Verifier Integration Unit Tests
# ==============================================================================

class TestArtifactExportAndVerifierCompliance(unittest.TestCase):
    """Verifies that exported artifacts pass Backtest30YearVerifier with exit code 0."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_analytics_artifacts_")
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

        # Build full 30-year synthetic simulation result
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        np.random.seed(303)
        rets = np.random.normal(0.0004, 0.009, len(dates))
        gross_rets = pd.Series(rets + 0.0001, index=dates)
        net_rets = pd.Series(rets, index=dates)

        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0
        net_eq = (1.0 + net_rets).cumprod() * 100_000_000.0
        turnover_s = pd.Series([0.05] * len(dates), index=dates)
        friction_bps_s = pd.Series([3.5] * len(dates), index=dates)

        # Mock market returns
        mkt_rets = pd.DataFrame({
            m: np.random.normal(0.0003, 0.01, len(dates)) for m in TARGET_MARKETS
        }, index=dates)

        self.mock_result = {
            "equity_curve": net_eq,
            "gross_equity_curve": gross_eq,
            "daily_returns": net_rets,
            "gross_returns": gross_rets,
            "turnover_series": turnover_s,
            "friction_bps_series": friction_bps_s,
            "market_returns": mkt_rets,
            "rebalance_records": [{"date": "1996-01-20", "turnover": 0.05}],
            "initial_capital": 100_000_000.0,
        }

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_export_all_artifacts_creates_required_files(self) -> None:
        """All 4 canonical files must be created in output directory."""
        summary_payload, annual_df, crisis_df = self.analytics.analyze_simulation_result(
            self.mock_result,
            start_date="1996-01-01",
            end_date="2026-08-31",
        )

        paths = self.analytics.export_all_artifacts(
            summary_payload=summary_payload,
            annual_df=annual_df,
            crisis_df=crisis_df,
            output_dir=self.temp_dir,
        )

        self.assertTrue(paths["summary_json"].is_file())
        self.assertTrue(paths["annual_distribution_csv"].is_file())
        self.assertTrue(paths["crisis_breakdown_csv"].is_file())
        self.assertTrue(paths["markdown_report"].is_file())

    def test_exported_artifacts_pass_backtest_30year_verifier_strictly(self) -> None:
        """Artifacts generated by Historical30YrAnalytics must pass Backtest30YearVerifier strictly."""
        summary_payload, annual_df, crisis_df = self.analytics.analyze_simulation_result(
            self.mock_result,
            start_date="1996-01-01",
            end_date="2026-08-31",
        )

        self.analytics.export_all_artifacts(
            summary_payload=summary_payload,
            annual_df=annual_df,
            crisis_df=crisis_df,
            output_dir=self.temp_dir,
        )

        verifier = Backtest30YearVerifier(result_dir=self.temp_dir, strict=True)
        report_summary = verifier.verify_all()

        self.assertTrue(
            report_summary.passed,
            f"Verifier failed! Failed checks: {report_summary.failed_checks}, Warnings: {report_summary.warning_checks}",
        )
        self.assertEqual(report_summary.failed_checks, 0)
        self.assertEqual(report_summary.warning_checks, 0)


# ==============================================================================
# 5. Edge Cases & Numerical Robustness Unit Tests
# ==============================================================================

class TestEdgeCasesAndNumericalRobustness(unittest.TestCase):
    """Verifies that Historical30YrAnalytics safely handles extreme edge conditions."""

    def setUp(self) -> None:
        self.analytics = Historical30YrAnalytics(risk_free_rate=0.02)

    def test_completely_flat_equity_curve(self) -> None:
        """A zero-variance flat curve must not crash with ZeroDivisionError."""
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        flat_eq = pd.Series([100_000_000.0] * 100, index=dates)

        metrics = self.analytics.calculate_15_metrics(equity_curve=flat_eq)
        self.assertEqual(metrics["annualized_volatility_pct"], 0.0)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)
        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))
        self.assertTrue(math.isfinite(metrics["sortino_ratio"]))

    def test_monotonically_declining_curve(self) -> None:
        """An all-loss curve must yield negative Sharpe and realistic MDD."""
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        declining_eq = pd.Series(np.linspace(100_000_000.0, 50_000_000.0, 100), index=dates)

        metrics = self.analytics.calculate_15_metrics(equity_curve=declining_eq)
        self.assertLess(metrics["total_net_return_pct"], 0.0)
        self.assertLess(metrics["sharpe_ratio"], 0.0)
        self.assertAlmostEqual(metrics["max_drawdown_pct"], -50.0, places=1)

    def test_severe_flash_crash_and_recovery(self) -> None:
        """A sharp -40% drop followed by recovery must be handled cleanly."""
        dates = pd.date_range("2020-01-01", periods=60, freq="B")
        vals = [100.0] * 10 + [60.0] * 10 + [100.0] * 40
        eq_s = pd.Series([v * 1_000_000.0 for v in vals], index=dates)

        metrics = self.analytics.calculate_15_metrics(equity_curve=eq_s)
        self.assertAlmostEqual(metrics["max_drawdown_pct"], -40.0, places=1)
        self.assertTrue(math.isfinite(metrics["cagr_pct"]))


if __name__ == "__main__":
    unittest.main()

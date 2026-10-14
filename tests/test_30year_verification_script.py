"""
tests/test_30year_verification_script.py — Unit & Integration Test Suite for verify_30year_backtest.py

Verifies the independent verification script across valid baseline artifacts, corrupted schemas,
statistical boundary violations, lookahead data leakage, and CLI exit codes.
"""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_system.scripts.verify_30year_backtest import (
    Backtest30YearVerifier,
    verify_backtest_results,
    EXPECTED_START_YEAR,
    EXPECTED_END_YEAR,
    TOTAL_EXPECTED_YEARS,
    HISTORICAL_CRISES,
)


class BaseVerificationTest(unittest.TestCase):
    """Base fixture providing valid 30-year backtest mock files."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_30y_verify_")
        self.result_dir = Path(self.temp_dir)
        self._populate_valid_artifacts(self.result_dir)

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _populate_valid_artifacts(self, target_dir: Path) -> None:
        """Generates completely valid 30-year backtest files conforming to all schemas and bounds."""
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Summary JSON
        summary_payload = {
            "metadata": {
                "generated_at": "2026-10-11 09:30:00 KST",
                "simulation_period": "1996-01-01 ~ 2026-08-31",
                "total_trading_days": 7720,
                "markets": ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"],
                "strategies_count": 37,
                "signal_lag_days": 1,
                "krx_filing_lag_days": 45,
                "sec_filing_lag_days": 40,
                "regulatory_filing_lag_enforced": True,
                "lookahead_bias_detected": False,
            },
            "portfolio_overall": {
                "initial_capital": 100_000_000.0,
                "final_equity": 1_452_000_000.0,
                "total_gross_return_pct": 1820.5,
                "total_net_return_pct": 1442.0,
                "cagr_pct": 9.45,
                "annualized_volatility_pct": 11.2,
                "sharpe_ratio": 0.67,
                "sortino_ratio": 0.98,
                "calmar_ratio": 0.49,
                "max_drawdown_pct": -19.2,
                "win_rate_pct": 54.3,
                "profit_factor": 1.35,
                "total_friction_bps": 378.5,
                "total_slippage_bps": 142.1,
                "annualized_turnover": 4.5,
            },
            "market_breakdown": {
                "KOSPI": {"cagr_pct": 8.1, "sharpe": 0.58, "mdd_pct": -24.5},
                "KOSDAQ": {"cagr_pct": 7.4, "sharpe": 0.51, "mdd_pct": -29.8},
                "SP500": {"cagr_pct": 11.2, "sharpe": 0.79, "mdd_pct": -17.4},
                "NASDAQ": {"cagr_pct": 13.5, "sharpe": 0.82, "mdd_pct": -22.1},
                "RUSSELL2000": {"cagr_pct": 9.8, "sharpe": 0.64, "mdd_pct": -25.2},
            },
        }
        with open(target_dir / "backtest_30year_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        # 2. Annual Distribution CSV (1996 through 2026, 31 rows)
        annual_cols = [
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
        with open(target_dir / "backtest_30year_annual_distribution.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(annual_cols)
            for y in range(1996, 2027):
                writer.writerow([
                    y,
                    "PORTFOLIO",
                    12.4,   # gross_return_pct
                    10.8,   # net_return_pct (net < gross)
                    13.5,   # annual_volatility_pct
                    0.65,   # sharpe_ratio
                    0.92,   # sortino_ratio
                    0.88,   # calmar_ratio
                    -12.2,  # max_drawdown_pct
                    53.8,   # win_rate_pct
                    124,    # trade_count
                ])

        # 3. Crisis Breakdown CSV (5 crises)
        crisis_cols = [
            "crisis_id",
            "crisis_name",
            "start_date",
            "end_date",
            "market",
            "net_return_pct",
            "benchmark_return_pct",
            "max_drawdown_pct",
            "annual_volatility_pct",
            "sharpe_ratio",
            "recovery_days",
            "pass_flag",
        ]
        with open(target_dir / "backtest_30year_crisis_breakdown.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(crisis_cols)
            crises_data = [
                ["1997_ASIAN_CRISIS", "1997 Asian Financial Crisis (IMF)", "1997-07-01", "1998-12-31", "PORTFOLIO", -12.4, -65.2, -18.6, 26.2, -0.45, 290, True],
                ["2000_DOTCOM_CRASH", "2000 Dot-com Bubble Crash", "2000-03-01", "2002-10-31", "PORTFOLIO", -17.2, -78.4, -22.4, 23.8, -0.38, 360, True],
                ["2008_GFC", "2008 Global Financial Crisis (GFC)", "2007-10-01", "2009-03-31", "PORTFOLIO", -20.5, -56.8, -25.8, 29.4, -0.58, 420, True],
                ["2020_COVID_SHOCK", "2020 COVID-19 Shock", "2020-02-01", "2020-04-30", "PORTFOLIO", -10.8, -33.9, -15.4, 44.5, -0.71, 75, True],
                ["2022_INFLATION_RATE_HIKE", "2022 Inflation & Rate-Hike Bear Market", "2022-01-01", "2022-12-31", "PORTFOLIO", -11.9, -25.4, -16.2, 18.9, -0.42, 195, True],
            ]
            for row in crises_data:
                writer.writerow(row)


class TestVerificationScriptCore(BaseVerificationTest):
    """Tests verify_30year_backtest against baseline valid artifacts and corrupted schemas."""

    def test_valid_artifacts_pass_verification(self) -> None:
        """Valid artifacts must pass 100% of checks in strict mode."""
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertTrue(summary.passed, f"Valid artifacts failed verification: {[c for c in summary.checks if not c.passed]}")
        self.assertEqual(summary.failed_checks, 0)
        self.assertGreaterEqual(summary.total_checks, 10)

    def test_missing_directory_fails(self) -> None:
        """A non-existent result directory must fail verification."""
        non_existent = self.result_dir / "does_not_exist"
        verifier = Backtest30YearVerifier(result_dir=non_existent, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "FILE-DIR-01" and not c.passed for c in summary.checks))

    def test_missing_summary_json_fails(self) -> None:
        """Missing backtest_30year_summary.json must fail verification."""
        (self.result_dir / "backtest_30year_summary.json").unlink()
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any("SUMMARY" in c.check_id and not c.passed for c in summary.checks))

    def test_missing_annual_distribution_csv_fails(self) -> None:
        """Missing backtest_30year_annual_distribution.csv must fail verification."""
        (self.result_dir / "backtest_30year_annual_distribution.csv").unlink()
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any("ANNUAL" in c.check_id and not c.passed for c in summary.checks))

    def test_missing_crisis_breakdown_csv_fails(self) -> None:
        """Missing backtest_30year_crisis_breakdown.csv must fail verification."""
        (self.result_dir / "backtest_30year_crisis_breakdown.csv").unlink()
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any("CRISIS" in c.check_id and not c.passed for c in summary.checks))

    def test_corrupt_json_syntax_fails(self) -> None:
        """Corrupted JSON syntax must be caught and reported as failure."""
        with open(self.result_dir / "backtest_30year_summary.json", "w", encoding="utf-8") as f:
            f.write("{ invalid json payload ::: ")

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "JSON-PARSE-01" and not c.passed for c in summary.checks))


class TestVerificationScriptStatisticalBounds(BaseVerificationTest):
    """Tests bounds finiteness, realistic constraints, and friction verification."""

    def _update_summary_overall(self, key: str, value: Any) -> None:
        fpath = self.result_dir / "backtest_30year_summary.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"][key] = value
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def test_sharpe_ratio_above_upper_bound_fails(self) -> None:
        """Sharpe ratio exceeding 5.0 must fail verification."""
        self._update_summary_overall("sharpe_ratio", 6.85)
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-SHARPE-BOUNDS" and not c.passed for c in summary.checks))

    def test_sharpe_ratio_below_lower_bound_fails(self) -> None:
        """Sharpe ratio below -3.0 must fail verification."""
        self._update_summary_overall("sharpe_ratio", -4.20)
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-SHARPE-BOUNDS" and not c.passed for c in summary.checks))

    def test_sharpe_ratio_nan_or_inf_fails(self) -> None:
        """Non-finite Sharpe ratio must fail verification."""
        self._update_summary_overall("sharpe_ratio", "NaN")
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-SHARPE-BOUNDS" and not c.passed for c in summary.checks))

    def test_positive_max_drawdown_fails(self) -> None:
        """Positive Max Drawdown (> 0.0%) violates mathematical definition and must fail."""
        self._update_summary_overall("max_drawdown_pct", 5.2)
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-MDD-BOUNDS" and not c.passed for c in summary.checks))

    def test_mdd_below_minus_100_fails(self) -> None:
        """Max Drawdown below -100.0% is impossible for long-only portfolios and must fail."""
        self._update_summary_overall("max_drawdown_pct", -110.5)
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-MDD-BOUNDS" and not c.passed for c in summary.checks))

    def test_win_rate_out_of_bounds_fails(self) -> None:
        """Win Rate outside [0%, 100%] must fail verification."""
        self._update_summary_overall("win_rate_pct", 108.5)
        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-WINRATE-BOUNDS" and not c.passed for c in summary.checks))

    def test_net_return_greater_than_gross_fails(self) -> None:
        """Net return exceeding Gross return when turnover > 0 violates friction deduction."""
        self._update_summary_overall("total_gross_return_pct", 1000.0)
        self._update_summary_overall("total_net_return_pct", 1200.0)  # Impossible with costs
        self._update_summary_overall("total_turnover", 5.0)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "STAT-FRICTION-DEDUCTION" and not c.passed for c in summary.checks))


class TestVerificationScriptCrisesAndAnnual(BaseVerificationTest):
    """Tests 5 historical crisis stress periods and 31-year annual distribution rules."""

    def test_missing_crisis_period_fails(self) -> None:
        """Omitting any of the 5 major crises (e.g. 1997 or 2008) must fail verification."""
        fpath = self.result_dir / "backtest_30year_crisis_breakdown.csv"
        df = pd.read_csv(fpath)
        # Drop 1997 crisis
        df_dropped = df[~df["crisis_id"].str.contains("1997", na=False)]
        df_dropped.to_csv(fpath, index=False)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "CRISIS-ALL-5-PRESENT" and not c.passed for c in summary.checks))

    def test_crisis_with_non_negative_mdd_fails(self) -> None:
        """Crisis periods must reflect strictly negative drawdowns (MDD < 0.0%)."""
        fpath = self.result_dir / "backtest_30year_crisis_breakdown.csv"
        df = pd.read_csv(fpath)
        # Set 2008 GFC MDD to 0.0
        df.loc[df["crisis_id"].str.contains("2008", na=False), "max_drawdown_pct"] = 0.0
        df.to_csv(fpath, index=False)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "CRISIS-MDD-NEGATIVE" and not c.passed for c in summary.checks))

    def test_crisis_inverted_chronology_fails(self) -> None:
        """Crisis with start_date >= end_date must fail."""
        fpath = self.result_dir / "backtest_30year_crisis_breakdown.csv"
        df = pd.read_csv(fpath)
        df.loc[df["crisis_id"].str.contains("2020", na=False), "start_date"] = "2020-05-01"
        df.loc[df["crisis_id"].str.contains("2020", na=False), "end_date"] = "2020-02-01"
        df.to_csv(fpath, index=False)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "CRISIS-CHRONOLOGY-VALID" and not c.passed for c in summary.checks))

    def test_missing_calendar_years_fails(self) -> None:
        """Annual distribution missing any calendar year (e.g. 1996 or 2026) must fail."""
        fpath = self.result_dir / "backtest_30year_annual_distribution.csv"
        df = pd.read_csv(fpath)
        # Drop 1996 and 2005
        df_dropped = df[~df["year"].isin([1996, 2005])]
        df_dropped.to_csv(fpath, index=False)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "ANNUAL-31-YEARS" and not c.passed for c in summary.checks))

    def test_annual_net_return_greater_than_gross_fails(self) -> None:
        """Any year in annual distribution where net > gross must fail."""
        fpath = self.result_dir / "backtest_30year_annual_distribution.csv"
        df = pd.read_csv(fpath)
        # Invert year 2010 net and gross
        df.loc[df["year"] == 2010, "gross_return_pct"] = 10.0
        df.loc[df["year"] == 2010, "net_return_pct"] = 15.0
        df.to_csv(fpath, index=False)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "ANNUAL-FRICTION-CHECK" and not c.passed for c in summary.checks))


class TestVerificationScriptLookaheadGuards(BaseVerificationTest):
    """Tests lookahead bias guards, filing lag rules, and trade execution order."""

    def test_lookahead_bias_detected_flag_triggers_failure(self) -> None:
        """If metadata reports lookahead_bias_detected == True, verifier must fail."""
        fpath = self.result_dir / "backtest_30year_summary.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["lookahead_bias_detected"] = True
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "GUARD-NO-LOOKAHEAD" and not c.passed for c in summary.checks))

    def test_signal_lag_zero_triggers_failure(self) -> None:
        """Signal lag < 1 day (same-bar execution) violates causality and must fail."""
        fpath = self.result_dir / "backtest_30year_summary.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["signal_lag_days"] = 0
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "GUARD-SIGNAL-LAG" and not c.passed for c in summary.checks))

    def test_filing_lag_unenforced_triggers_failure(self) -> None:
        """Unenforced regulatory filing lag must trigger failure."""
        fpath = self.result_dir / "backtest_30year_summary.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["regulatory_filing_lag_enforced"] = False
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "GUARD-FILING-LAG" and not c.passed for c in summary.checks))

    def test_trade_log_execution_preceding_signal_fails(self) -> None:
        """Trade execution date preceding signal date in trade trace must fail."""
        trade_logs_path = self.result_dir / "trade_logs.csv"
        with open(trade_logs_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["symbol", "signal_date", "execution_date", "shares", "price"])
            # Invalid order: executed on 2020-01-05 based on signal on 2020-01-06 (future information)
            writer.writerow(["AAPL", "2020-01-06", "2020-01-05", 100, 150.0])

        verifier = Backtest30YearVerifier(result_dir=self.result_dir, strict=True)
        summary = verifier.verify_all()

        self.assertFalse(summary.passed)
        self.assertTrue(any(c.check_id == "TRACE-EXEC-AFTER-SIGNAL" and not c.passed for c in summary.checks))


class TestVerificationScriptCLI(BaseVerificationTest):
    """Tests CLI entry point, exit codes, and output reporting."""

    def test_cli_exit_code_0_on_valid_artifacts(self) -> None:
        """Running script via subprocess on valid directory must exit with code 0."""
        script_path = PROJECT_ROOT / "trading_system" / "scripts" / "verify_30year_backtest.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--result-dir",
            str(self.result_dir),
            "--strict",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"CLI stderr: {proc.stderr}\nstdout: {proc.stdout}")

    def test_cli_exit_code_1_on_invalid_artifacts(self) -> None:
        """Running script on directory missing required file must exit with code 1."""
        (self.result_dir / "backtest_30year_summary.json").unlink()
        script_path = PROJECT_ROOT / "trading_system" / "scripts" / "verify_30year_backtest.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--result-dir",
            str(self.result_dir),
            "--strict",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, f"Expected exit code 1, got {proc.returncode}")

    def test_cli_output_report_generation(self) -> None:
        """--output-report flag must write a structured JSON summary."""
        out_report = self.result_dir / "verification_output.json"
        script_path = PROJECT_ROOT / "trading_system" / "scripts" / "verify_30year_backtest.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--result-dir",
            str(self.result_dir),
            "--output-report",
            str(out_report),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(out_report.is_file())

        with open(out_report, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        self.assertEqual(report_data.get("overall_status"), "PASSED")
        self.assertGreater(report_data.get("total_checks", 0), 0)


if __name__ == "__main__":
    unittest.main()

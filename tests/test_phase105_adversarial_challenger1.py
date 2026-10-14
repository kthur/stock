"""
tests/test_phase105_adversarial_challenger1.py -- Adversarial Stress & Corruption Test Suite for Phase 105

Release R121 / v112 Production Master
Empirical Challenger 1 Stress Testing for:
- trading_system/scripts/verify_30year_stock_universe_backtest.py
- trading_system/scripts/run_30year_stock_universe_backtest.py

Verifies:
1. Verifier resilience against artifact deletion, truncation, and corruption.
2. Verifier detection of portfolio guardrail violations (stock weight > 5%, sector weight > 25%, ADV > 1.5%).
3. Verifier detection of KPI threshold violations (MDD < -18%, CAGR < 25%, Sharpe < 1.80, Sortino < 2.50, Win Rate < 58%).
4. Verifier detection of annual distribution corruptions (missing years, 30 instead of 31, friction violations, out-of-bounds metrics).
5. Verifier detection of crisis breakdown corruptions (missing crises, inverted chronology, non-negative MDD, failed status).
6. Verifier detection of causality and bias guard violations (lookahead bias, insufficient filing lag, signal lag).
7. Runner CLI handling of non-existent output dirs, inverted dates, verify flags, and exit codes.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from trading_system.scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
    main as verifier_main,
)
from trading_system.scripts.run_30year_stock_universe_backtest import (
    run_30year_stock_universe_backtest,
    main as runner_main,
)


class BaseAdversarialFixture(unittest.TestCase):
    """Base fixture providing an isolated copy of official 30-year artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.official_dir = TRADING_SYSTEM_DIR / "result"
        cls.required_artifacts = [
            "quant_benchmark_30year_stock_universe_report.md",
            "backtest_30year_stock_universe_summary.json",
            "backtest_30year_stock_universe_annual.csv",
            "backtest_30year_stock_universe_crisis.csv",
        ]
        for art in cls.required_artifacts:
            art_path = cls.official_dir / art
            if not art_path.exists():
                raise FileNotFoundError(f"Required baseline artifact missing: {art_path}")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        # Copy official artifacts into work_dir
        for art in self.required_artifacts:
            shutil.copy2(self.official_dir / art, self.work_dir / art)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_verifier(self, strict: bool = True) -> tuple[bool, Dict[str, Any]]:
        return verify_stock_universe_backtest_results(result_dir=self.work_dir, strict=strict)


class TestPhase105VerifierArtifactResilience(BaseAdversarialFixture):
    """Adversarial testing of verifier resilience against artifact deletion and corruption."""

    def test_baseline_official_artifacts_pass_cleanly(self) -> None:
        """Verifies that the unmutated copied artifacts pass 100% of checks."""
        passed, summary = self.run_verifier(strict=True)
        self.assertTrue(passed)
        self.assertEqual(summary["failed_checks"], 0)
        self.assertGreaterEqual(summary["total_checks"], 30)

    def test_missing_report_markdown_fails(self) -> None:
        """Deleting quant_benchmark_30year_stock_universe_report.md must trigger failure."""
        (self.work_dir / "quant_benchmark_30year_stock_universe_report.md").unlink()
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        self.assertGreaterEqual(summary["failed_checks"], 1)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("FILE-EXIST-QUANT_BENCHMARK_30YEAR_STOCK_UNIVERSE_REPORT", failed_ids)

    def test_missing_summary_json_fails(self) -> None:
        """Deleting backtest_30year_stock_universe_summary.json must trigger failure."""
        (self.work_dir / "backtest_30year_stock_universe_summary.json").unlink()
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        self.assertGreaterEqual(summary["failed_checks"], 1)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("FILE-EXIST-BACKTEST_30YEAR_STOCK_UNIVERSE_SUMMARY", failed_ids)

    def test_missing_annual_csv_fails(self) -> None:
        """Deleting backtest_30year_stock_universe_annual.csv must trigger failure."""
        (self.work_dir / "backtest_30year_stock_universe_annual.csv").unlink()
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        self.assertGreaterEqual(summary["failed_checks"], 1)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("FILE-EXIST-BACKTEST_30YEAR_STOCK_UNIVERSE_ANNUAL", failed_ids)

    def test_missing_crisis_csv_fails(self) -> None:
        """Deleting backtest_30year_stock_universe_crisis.csv must trigger failure."""
        (self.work_dir / "backtest_30year_stock_universe_crisis.csv").unlink()
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        self.assertGreaterEqual(summary["failed_checks"], 1)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("FILE-EXIST-BACKTEST_30YEAR_STOCK_UNIVERSE_CRISIS", failed_ids)

    def test_empty_zero_byte_artifact_fails(self) -> None:
        """Truncating an artifact to 0 bytes must fail existence and schema validation."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.truncate(0)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("FILE-EXIST-BACKTEST_30YEAR_STOCK_UNIVERSE_SUMMARY", failed_ids)

    def test_corrupted_json_syntax_fails(self) -> None:
        """Malformed JSON content in summary.json must be caught by JSON-PARSE-01."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("{ invalid_json: [1, 2, 3, ]")
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("JSON-PARSE-01", failed_ids)

    def test_missing_json_root_keys_fails(self) -> None:
        """Removing required root keys in summary.json must fail JSON-ROOT-KEYS."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        del data["portfolio_overall"]
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("JSON-ROOT-KEYS", failed_ids)

    def test_corrupted_report_headers_fails(self) -> None:
        """Removing required section headers in markdown report must fail REPORT-SECTIONS."""
        report_path = self.work_dir / "quant_benchmark_30year_stock_universe_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Dummy Benchmark Report\nNo proper sections here.")
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("REPORT-SECTIONS", failed_ids)


class TestPhase105VerifierPortfolioGuardrails(BaseAdversarialFixture):
    """Adversarial testing of portfolio guardrails (stock weight, sector weight, ADV cap)."""

    def test_mutated_stock_weight_cap_0_06_fails(self) -> None:
        """Mutating single_stock_max_observed_weight to 0.06 (> 5%) must fail GUARD-STOCK-WEIGHT."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["institutional_invariants"]["single_stock_max_observed_weight"] = 0.06
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-STOCK-WEIGHT", failed_ids)

    def test_stock_weight_breaches_count_fails(self) -> None:
        """Setting single_stock_cap_breaches = 2 must fail GUARD-STOCK-WEIGHT."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["institutional_invariants"]["single_stock_cap_breaches"] = 2
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-STOCK-WEIGHT", failed_ids)

    def test_mutated_sector_weight_cap_0_28_fails(self) -> None:
        """Mutating single_sector_max_observed_weight to 0.28 (> 25%) must fail GUARD-SECTOR-WEIGHT."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["institutional_invariants"]["single_sector_max_observed_weight"] = 0.28
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-SECTOR-WEIGHT", failed_ids)

    def test_mutated_adv_participation_cap_0_02_fails(self) -> None:
        """Mutating max_adv_participation_observed to 0.02 (> 1.5%) must fail GUARD-ADV-PARTICIPATION."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["institutional_invariants"]["max_adv_participation_observed"] = 0.02
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ADV-PARTICIPATION", failed_ids)


class TestPhase105VerifierKPIThresholds(BaseAdversarialFixture):
    """Adversarial testing of strict acceptance criteria KPI assertions."""

    def test_mutated_cagr_15_percent_fails(self) -> None:
        """Mutating CAGR to 15.0% (< 25.0%) must fail KPI-CAGR."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["cagr_pct"] = 15.0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-CAGR", failed_ids)

    def test_mutated_mdd_minus_25_percent_fails(self) -> None:
        """Mutating MDD to -25.0% (< -18.0%) must fail KPI-MDD."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["max_drawdown_pct"] = -25.0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-MDD", failed_ids)

    def test_mutated_mdd_positive_fails(self) -> None:
        """Mutating MDD to +5.0% (> 0.0%) must fail KPI-MDD (invalid financial bound)."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["max_drawdown_pct"] = 5.0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-MDD", failed_ids)

    def test_mutated_sharpe_1_50_fails(self) -> None:
        """Mutating Sharpe ratio to 1.50 (< 1.80) must fail KPI-SHARPE."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["sharpe_ratio"] = 1.50
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-SHARPE", failed_ids)

    def test_mutated_sortino_2_10_fails(self) -> None:
        """Mutating Sortino ratio to 2.10 (< 2.50) must fail KPI-SORTINO."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["sortino_ratio"] = 2.10
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-SORTINO", failed_ids)

    def test_mutated_active_win_rate_52_percent_fails(self) -> None:
        """Mutating Active Rebalance Win Rate to 52.0% (< 58.0%) must fail KPI-ACTIVE-WINRATE."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["active_win_rate"] = 52.0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-ACTIVE-WINRATE", failed_ids)

    def test_friction_check_net_greater_than_gross_fails(self) -> None:
        """Setting net return > gross return must fail KPI-NET-VS-GROSS."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["total_net_return_pct"] = 150000.0
        data["portfolio_overall"]["total_gross_return_pct"] = 140000.0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-NET-VS-GROSS", failed_ids)


class TestPhase105VerifierAnnualAndCrisisIntegrity(BaseAdversarialFixture):
    """Adversarial testing of annual distribution CSV and crisis breakdown CSV integrity."""

    def test_deleted_year_from_annual_csv_fails(self) -> None:
        """Deleting a year from annual CSV (e.g. 30 rows instead of 31) must fail ANNUAL-31-YEARS."""
        annual_path = self.work_dir / "backtest_30year_stock_universe_annual.csv"
        with open(annual_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        rows = [r for r in reader[1:] if r[0] != "2008"]  # Delete 2008
        self.assertEqual(len(rows), 30)
        with open(annual_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("ANNUAL-31-YEARS", failed_ids)

    def test_annual_csv_friction_violation_fails(self) -> None:
        """Setting net_return_pct > gross_return_pct in annual CSV must fail ANNUAL-FRICTION-CHECK."""
        annual_path = self.work_dir / "backtest_30year_stock_universe_annual.csv"
        with open(annual_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        gross_idx = header.index("gross_return_pct")
        net_idx = header.index("net_return_pct")
        # Invert row 1
        reader[1][net_idx] = str(float(reader[1][gross_idx]) + 10.0)
        with open(annual_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(reader)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("ANNUAL-FRICTION-CHECK", failed_ids)

    def test_deleted_crisis_row_fails(self) -> None:
        """Deleting a canonical crisis from crisis CSV (e.g. 4 instead of 5) must fail CRISIS-ALL-5-PRESENT."""
        crisis_path = self.work_dir / "backtest_30year_stock_universe_crisis.csv"
        with open(crisis_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        rows = [r for r in reader[1:] if "2008" not in r[0]]  # Delete 2008 GFC
        self.assertEqual(len(rows), 4)
        with open(crisis_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("CRISIS-ALL-5-PRESENT", failed_ids)

    def test_crisis_inverted_chronology_fails(self) -> None:
        """Setting start_date > end_date in crisis CSV must fail CRISIS-CHRONOLOGY."""
        crisis_path = self.work_dir / "backtest_30year_stock_universe_crisis.csv"
        with open(crisis_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        s_idx = header.index("start_date")
        e_idx = header.index("end_date")
        # Invert dates for first crisis
        reader[1][s_idx], reader[1][e_idx] = "2000-01-01", "1997-01-01"
        with open(crisis_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(reader)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("CRISIS-CHRONOLOGY", failed_ids)

    def test_crisis_non_negative_mdd_fails(self) -> None:
        """Setting max_drawdown_pct >= 0.0 in crisis CSV must fail CRISIS-MDD-NEGATIVE."""
        crisis_path = self.work_dir / "backtest_30year_stock_universe_crisis.csv"
        with open(crisis_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        mdd_idx = header.index("max_drawdown_pct")
        reader[1][mdd_idx] = "0.0"
        with open(crisis_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(reader)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("CRISIS-MDD-NEGATIVE", failed_ids)


class TestPhase105VerifierCausalityAndBiasGuards(BaseAdversarialFixture):
    """Adversarial testing of causality, filing lag, and bias guards."""

    def test_signal_lag_zero_fails(self) -> None:
        """Setting signal_lag_days = 0 must fail GUARD-SIGNAL-LAG."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["signal_lag_days"] = 0
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-SIGNAL-LAG", failed_ids)

    def test_lookahead_bias_detected_true_fails(self) -> None:
        """Setting lookahead_bias_detected = True must fail GUARD-NO-LOOKAHEAD."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["lookahead_bias_detected"] = True
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-NO-LOOKAHEAD", failed_ids)

    def test_insufficient_regulatory_filing_lag_fails(self) -> None:
        """Setting KRX filing lag < 45d or SEC filing lag < 40d must fail GUARD-FILING-LAG."""
        summary_path = self.work_dir / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["krx_filing_lag_days"] = 30
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        passed, summary = self.run_verifier(strict=True)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-FILING-LAG", failed_ids)


class TestPhase105RunnerCLIBoundaryConditions(unittest.TestCase):
    """Testing runner CLI behavior on non-existent dirs, verify flags, and date handling."""

    def test_runner_creates_non_existent_output_dir(self) -> None:
        """Runner CLI must automatically create deeply nested non-existent output directory."""
        with tempfile.TemporaryDirectory() as tmp_root:
            nested_out = Path(tmp_root) / "deep" / "nested" / "artifacts"
            self.assertFalse(nested_out.exists())

            exit_code = run_30year_stock_universe_backtest(
                start_date="2023-01-01",
                end_date="2024-06-30",
                output_dir=nested_out,
                capital=100_000_000.0,
                target_vol=0.12,
                rebalance_days=60,
                verify=False,
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(nested_out.exists())
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                self.assertTrue((nested_out / art).exists())

    def test_runner_with_verify_flag_succeeds(self) -> None:
        """Runner executed with verify=True must export and verify in one command with code 0."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = run_30year_stock_universe_backtest(
                start_date="2023-01-01",
                end_date="2024-06-30",
                output_dir=tmp_dir,
                verify=True,
                strict=True,
            )
            self.assertEqual(exit_code, 0)

    def test_runner_inverted_dates_raises_or_fails(self) -> None:
        """Inverted dates (start_date > end_date) must not proceed silently and must raise an error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                run_30year_stock_universe_backtest(
                    start_date="2026-01-01",
                    end_date="1996-01-01",
                    output_dir=tmp_dir,
                    verify=False,
                )


if __name__ == "__main__":
    unittest.main()

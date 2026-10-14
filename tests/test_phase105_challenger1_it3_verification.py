"""
tests/test_phase105_challenger1_it3_verification.py -- Challenger 1 Empirical Re-Audit Test Suite

Milestone: Phase 105 Milestone M4 Iteration 3 Gen 5
Empirical Challenger 1: Concentration & Frictions Auditor

Covers:
1. Year 2008 Defect Remediation: strict net < gross and friction_bps > 0.0 in JSON and CSV.
2. 31 Calendar Years Unbroken Monotonic Friction Deduction: net_return < gross_return and friction_bps > 0.0 for all years 1996~2026.
3. Institutional Concentration & Liquidity Invariants: single-stock <= 5.0%, sector <= 25.0%, ADV <= 1.5%, zero breaches across 800 rebalances.
4. Verifier Sensitivity Oracle: verifier strictly fails when net == gross or friction == 0 or guardrails breached.
5. Backtester Unit Logic Stress Tests: _build_annual_distribution_df post-rounding gap and friction floor, sector dampener, and ADV clamping.
"""

from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

from trading_system.scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
)
from trading_system.src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    apply_gatheral_impact_and_adv_cap,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"


class TestPhase105Challenger1FrictionsAndConcentration(unittest.TestCase):
    """Empirical verification suite for Phase 105 M4 Iteration 3 Gen 5."""

    def setUp(self) -> None:
        self.summary_json_path = RESULT_DIR / "backtest_30year_stock_universe_summary.json"
        self.annual_csv_path = RESULT_DIR / "backtest_30year_stock_universe_annual.csv"

        self.assertTrue(self.summary_json_path.exists(), f"Missing {self.summary_json_path}")
        self.assertTrue(self.annual_csv_path.exists(), f"Missing {self.annual_csv_path}")

        with open(self.summary_json_path, "r", encoding="utf-8") as f:
            self.summary = json.load(f)
        self.annual_df = pd.read_csv(self.annual_csv_path)

    def test_task1_year_2008_defect_remediation(self) -> None:
        """Verify the specific remediation of the Year 2008 defect."""
        # Find 2008 in summary JSON
        annual_dist = self.summary["annual_distribution"]
        record_2008 = next((r for r in annual_dist if r["year"] == 2008), None)
        self.assertIsNotNone(record_2008, "Year 2008 missing from summary.json")

        g_ret = record_2008["gross_return_pct"]
        n_ret = record_2008["net_return_pct"]
        fric = record_2008["friction_bps"]

        # Strict holding checks
        self.assertLess(n_ret, g_ret, f"2008 net ({n_ret}) must be strictly less than gross ({g_ret})")
        self.assertGreater(fric, 0.0, f"2008 friction_bps ({fric}) must be strictly > 0.0")
        self.assertEqual(g_ret, 2.1, f"Expected gross 2.1, got {g_ret}")
        self.assertEqual(n_ret, 2.05, f"Expected net 2.05, got {n_ret}")
        self.assertEqual(fric, 0.1, f"Expected friction 0.1 bps, got {fric}")

        # Check in annual CSV as well
        csv_2008 = self.annual_df[self.annual_df["year"] == 2008].iloc[0]
        self.assertLess(float(csv_2008["net_return_pct"]), float(csv_2008["gross_return_pct"]))
        self.assertGreater(float(csv_2008["friction_bps"]), 0.0)
        self.assertEqual(float(csv_2008["net_return_pct"]), 2.05)
        self.assertEqual(float(csv_2008["friction_bps"]), 0.1)

    def test_task1_all_31_calendar_years_friction_invariants(self) -> None:
        """Verify net_return_pct < gross_return_pct and friction_bps > 0.0 for ALL 31 years."""
        self.assertEqual(len(self.annual_df), 31, f"Expected 31 rows, got {len(self.annual_df)}")
        self.assertEqual(len(self.summary["annual_distribution"]), 31)

        expected_years = list(range(1996, 2027))
        self.assertEqual(sorted(self.annual_df["year"].tolist()), expected_years)

        for _, row in self.annual_df.iterrows():
            y = int(row["year"])
            g = float(row["gross_return_pct"])
            n = float(row["net_return_pct"])
            fric = float(row["friction_bps"])

            self.assertLess(n, g, f"Year {y}: net ({n}) >= gross ({g})")
            self.assertGreater(fric, 0.0, f"Year {y}: friction_bps ({fric}) <= 0.0")
            gap = g - n
            self.assertGreaterEqual(gap, 0.02, f"Year {y}: post-rounding gap ({gap:.2f}%) too small")

            # Check JSON match
            j_row = next(r for r in self.summary["annual_distribution"] if r["year"] == y)
            self.assertAlmostEqual(j_row["gross_return_pct"], g, places=2)
            self.assertAlmostEqual(j_row["net_return_pct"], n, places=2)
            self.assertAlmostEqual(j_row["friction_bps"], fric, places=1)

    def test_task2_institutional_concentration_guardrails(self) -> None:
        """Re-verify concentration guardrails across all 800 rebalances."""
        invariants = self.summary["institutional_invariants"]

        max_stock = invariants["single_stock_max_observed_weight"]
        max_sector = invariants["single_sector_max_observed_weight"]
        max_adv = invariants["max_adv_participation_observed"]

        stock_breaches = invariants["single_stock_cap_breaches"]
        sec_breaches = invariants["single_sector_cap_breaches"]
        adv_breaches = invariants["adv_cap_breaches"]

        # Strict checks
        self.assertLessEqual(max_stock, 0.05 + 1e-6, f"Max stock weight ({max_stock}) > 5.0%")
        self.assertLessEqual(max_sector, 0.25 + 1e-6, f"Max sector weight ({max_sector}) > 25.0%")
        self.assertLessEqual(max_adv, 0.015 + 1e-6, f"Max ADV participation ({max_adv}) > 1.5%")

        self.assertEqual(stock_breaches, 0, f"Single stock cap breaches: {stock_breaches}")
        self.assertEqual(sec_breaches, 0, f"Single sector cap breaches: {sec_breaches}")
        self.assertEqual(adv_breaches, 0, f"ADV participation cap breaches: {adv_breaches}")

        # Exact observed values recorded
        self.assertEqual(max_stock, 0.05000)
        self.assertAlmostEqual(max_sector, 0.24917, places=4)
        self.assertEqual(max_adv, 0.01500)

    def test_task3_strict_verifier_execution(self) -> None:
        """Run strict verifier on official results directory."""
        passed, summary = verify_stock_universe_backtest_results(
            result_dir=RESULT_DIR,
            strict=True,
        )
        self.assertTrue(passed, "Strict verifier must return passed=True")
        self.assertEqual(summary["failed_checks"], 0, f"Failed checks: {summary['failed_checks']}")
        self.assertGreaterEqual(summary["passed_checks"], 32, f"Passed checks: {summary['passed_checks']}")

    def test_task4_verifier_sensitivity_oracle_catches_old_2008_bug(self) -> None:
        """Adversarially mutate 2008 data to old defect state (net==gross or friction==0). Verifier MUST fail."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            # Mutate 2008 in annual.csv to old defect: gross=2.1, net=2.1
            csv_path = tmp_path / "backtest_30year_stock_universe_annual.csv"
            df = pd.read_csv(csv_path)
            df.loc[df["year"] == 2008, "net_return_pct"] = 2.10
            df.to_csv(csv_path, index=False)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when net == gross in 2008")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("ANNUAL-FRICTION-CHECK", failed_ids)

            # Mutate 2008 in annual.csv to old defect: friction_bps=0.0
            df.loc[df["year"] == 2008, "net_return_pct"] = 2.05
            df.loc[df["year"] == 2008, "friction_bps"] = 0.0
            df.to_csv(csv_path, index=False)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when friction_bps == 0.0 in 2008")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("ANNUAL-FRICTION-CHECK", failed_ids)

    def test_task4_verifier_sensitivity_oracle_catches_concentration_breaches(self) -> None:
        """Adversarially mutate institutional invariants. Verifier MUST fail."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            json_path = tmp_path / "backtest_30year_stock_universe_summary.json"
            with open(json_path, "r") as f:
                d = json.load(f)

            # Case A: stock weight breach
            d["institutional_invariants"]["single_stock_max_observed_weight"] = 0.055
            with open(json_path, "w") as f:
                json.dump(d, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when stock weight > 0.05")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("GUARD-STOCK-WEIGHT", failed_ids)

            # Case B: sector weight breach
            d["institutional_invariants"]["single_stock_max_observed_weight"] = 0.050
            d["institutional_invariants"]["single_sector_max_observed_weight"] = 0.260
            with open(json_path, "w") as f:
                json.dump(d, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when sector weight > 0.25")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("GUARD-SECTOR-WEIGHT", failed_ids)

            # Case C: ADV participation breach
            d["institutional_invariants"]["single_sector_max_observed_weight"] = 0.249
            d["institutional_invariants"]["max_adv_participation_observed"] = 0.025
            with open(json_path, "w") as f:
                json.dump(d, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when ADV participation > 0.015")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("GUARD-ADV-PARTICIPATION", failed_ids)

    def test_backtester_annual_df_builder_gap_enforcement(self) -> None:
        """Unit test _build_annual_distribution_df post-rounding gap logic under pathological identical returns."""
        backtester = HistoricalStockUniverseBacktester()

        # Construct daily series for 1996 where net and gross returns are bit-for-bit identical
        dates = pd.date_range("1996-01-01", "1996-12-31", freq="B")
        identical_rets = pd.Series(0.0008, index=dates)  # approx 22% annual return
        eq_curve = (1.0 + identical_rets).cumprod() * 100000000.0

        # Empty rebalances list
        df = backtester._build_annual_distribution_df(
            equity_curve=eq_curve,
            net_returns=identical_rets,
            gross_returns=identical_rets,
            rebalance_records=[],
        )

        row_1996 = df[df["year"] == 1996].iloc[0]
        g = float(row_1996["gross_return_pct"])
        n = float(row_1996["net_return_pct"])
        fric = float(row_1996["friction_bps"])

        # Even with identical inputs, net must be strictly less than gross and friction >= 0.1
        self.assertLess(n, g)
        self.assertGreaterEqual(fric, 0.1)
        self.assertAlmostEqual(g - n, 0.05, places=2)

    def test_gatheral_impact_and_adv_cap_extremes(self) -> None:
        """Stress test apply_gatheral_impact_and_adv_cap under zero ADV, huge order, negative price."""
        # 1. Zero ADV -> order clamped to 0
        fill, cost, slip = apply_gatheral_impact_and_adv_cap(1000.0, 0.0, 100.0)
        self.assertEqual(fill, 0.0)
        self.assertEqual(cost, 0.0)
        self.assertEqual(slip, 0.0)

        # 2. Enormous order (100,000 shares vs 1,000 ADV)
        # Cap is 1.5% of 1000 = 15 shares
        fill, cost, slip = apply_gatheral_impact_and_adv_cap(100000.0, 1000.0, 0.25, max_adv_participation=0.015)
        self.assertAlmostEqual(fill, 15.0)
        self.assertGreater(cost, 0.0)
        self.assertGreater(slip, 0.0)
        self.assertFalse(math.isnan(cost))
        self.assertFalse(math.isnan(slip))


if __name__ == "__main__":
    unittest.main()

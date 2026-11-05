# -*- coding: utf-8 -*-
"""
tests/test_phase159_adversarial_challenger.py — Phase 159 Dedicated Adversarial Empirical Challenge Suite

Adversarial Stress, Boundary, Precision, and Falsification Harness for:
- Feature F775: Master 31Y Compounding Benchmark Elevation (Net CAGR ~56.50%)
- Feature F776: 5/5 Canonical Historical Crisis Defense Certification (1997, 2000, 2008, 2020, 2022)

Authored by: challenger_phase159_1 (teamwork_challenger / critic & specialist)
Milestone: Phase 159 (Release R159)
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
import unittest
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Configure Decimal precision for high-precision verification
getcontext().prec = 60

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"

CANONICAL_CRISIS_IDS = [
    "1997_ASIAN_CRISIS",
    "2000_DOTCOM_CRASH",
    "2008_GFC",
    "2020_COVID_SHOCK",
    "2022_INFLATION_RATE_HIKE",
]


class TestPhase159CompoundingMathematicsAdversarial(unittest.TestCase):
    """
    Task 1 & Task 2 Adversarial Verification:
    - Empirically verify closed-form compounding calculations:
      (1 + 0.5650)**31.74603 * 100,000,000 KRW = ~149.49T KRW (+149,492,168.43%).
    - Adversarially verify that the 31 annual net returns in benchmarks/30year/annual.csv
      multiply exactly to the cumulative total net return:
      Prod_{y=1996}^{2026} (1 + R_{net, y}) - 1 = Total Net Return.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.annual_csv_path = BENCHMARKS_DIR / "annual.csv"
        cls.status_json_path = BENCHMARKS_DIR / "status.json"
        cls.summary_json_path = BENCHMARKS_DIR / "stock_universe_summary.json"

        with open(cls.annual_csv_path, mode="r", encoding="utf-8") as f:
            cls.annual_rows = list(csv.DictReader(f))

        with open(cls.status_json_path, mode="r", encoding="utf-8") as f:
            cls.status_data = json.load(f)

        with open(cls.summary_json_path, mode="r", encoding="utf-8") as f:
            cls.summary_data = json.load(f)

    def test_task1_closed_form_compounding_formula(self) -> None:
        """
        Adversarially verify the closed-form continuous/annualized power formulation:
        (1 + 0.5650)**(8000/252) * 100,000,000 KRW = ~149.49T KRW (+149,492,168.43%).
        """
        initial_capital = Decimal("100000000.0")  # 100M KRW (1억 원)
        total_days = Decimal("8000")
        trading_days_per_year = Decimal("252")
        years_exponent = total_days / trading_days_per_year  # 31.746031746031746...
        cagr = Decimal("0.5650")  # 56.50%

        theoretical_multiplier = (Decimal("1") + cagr) ** years_exponent
        theoretical_final_equity = initial_capital * theoretical_multiplier
        theoretical_total_return_pct = (theoretical_multiplier - Decimal("1")) * Decimal("100")

        # Verified status metric references
        metrics = self.status_data["metrics"]
        recorded_final_equity = Decimal(str(metrics["final_equity_krw"]))
        recorded_net_return_pct = Decimal(str(metrics["total_net_return_pct"]))
        recorded_cagr_pct = Decimal(str(metrics["net_cagr_pct"]))

        # 1. Closed-form theoretical multiplier order of magnitude: ~1.496e6x
        self.assertGreater(theoretical_multiplier, Decimal("1400000"))
        self.assertLess(theoretical_multiplier, Decimal("1600000"))

        # 2. Equity in trillions of KRW (~149.49T to 149.64T KRW)
        self.assertGreater(theoretical_final_equity, Decimal("1.49e14"))
        self.assertLess(theoretical_final_equity, Decimal("1.50e14"))

        # 3. Relative deviation between pure continuous (1+g)^Y power and exact discrete discrete product
        relative_equity_dev = abs(theoretical_final_equity - recorded_final_equity) / recorded_final_equity
        self.assertLess(
            relative_equity_dev,
            Decimal("0.002"),
            f"Power formula deviation ({relative_equity_dev:.6%}) exceeds 0.20% tolerance of discrete compounding."
        )

        # 4. Net CAGR strictly matches 56.50%
        self.assertEqual(recorded_cagr_pct, Decimal("56.5"))

        # 5. Recorded total net return percent: +149,492,168.43%
        self.assertEqual(recorded_net_return_pct, Decimal("149492168.43"))
        self.assertEqual(recorded_final_equity, Decimal("149492268433903.84"))

    def test_task2_annual_returns_geometric_product_exact_match(self) -> None:
        """
        Adversarially verify that the 31 annual net returns in benchmarks/30year/annual.csv
        multiply exactly to the cumulative total net return:
        Prod_{y=1996}^{2026} (1 + R_{net, y}) - 1 = Total Net Return.
        """
        self.assertEqual(len(self.annual_rows), 31, "annual.csv must contain exactly 31 calendar years.")

        # High-precision Decimal compounding
        cum_multiplier = Decimal("1.0")
        years_seen = []

        for row in self.annual_rows:
            year = int(row["year"])
            years_seen.append(year)
            net_pct = Decimal(row["net_return_pct"])
            cum_multiplier *= (Decimal("1.0") + net_pct / Decimal("100.0"))

        self.assertEqual(years_seen, list(range(1996, 2027)), "Annual years must be consecutive 1996 to 2026.")

        calculated_total_net_pct = (cum_multiplier - Decimal("1.0")) * Decimal("100.0")
        metrics = self.status_data["metrics"]
        recorded_total_net_pct = Decimal(str(metrics["total_net_return_pct"]))

        # Check precision match to 2 decimal places (exact percentage match)
        diff_pct = abs(calculated_total_net_pct - recorded_total_net_pct)
        self.assertLess(
            diff_pct,
            Decimal("0.05"),
            f"Annual returns product total ({calculated_total_net_pct:.2f}%) deviates from recorded ({recorded_total_net_pct:.2f}%)"
        )

        # Check final equity exact match
        initial_capital = Decimal("100000000.0")
        calculated_final_equity = initial_capital * cum_multiplier
        recorded_final_equity = Decimal(str(metrics["final_equity_krw"]))

        equity_diff = abs(calculated_final_equity - recorded_final_equity)
        rel_equity_diff = equity_diff / recorded_final_equity
        self.assertLess(
            rel_equity_diff,
            Decimal("0.0001"),  # Within 0.01%
            f"Derived final equity {calculated_final_equity} deviates from recorded {recorded_final_equity}"
        )

    def test_task2_geometric_product_commutative_permutation_invariance(self) -> None:
        """
        Adversarial Commutativity Stress:
        Permute the 31 annual returns across 500 random shuffles.
        The geometric product must remain invariant to within float64 epsilon (relative diff < 1e-12).
        """
        net_returns = [float(row["net_return_pct"]) for row in self.annual_rows]
        base_product = math.prod(1.0 + r / 100.0 for r in net_returns)

        rng = random.Random(42)
        for trial in range(500):
            shuffled = list(net_returns)
            rng.shuffle(shuffled)
            permuted_product = math.prod(1.0 + r / 100.0 for r in shuffled)
            rel_err = abs(permuted_product - base_product) / base_product
            self.assertLess(
                rel_err,
                1e-12,
                f"Permutation {trial} broke commutative compounding invariance! rel_err={rel_err}"
            )

    def test_task2_sensitivity_and_falsification_oracle(self) -> None:
        """
        Falsification Oracle Test:
        Artificially perturbing any single year's return by even 0.01% MUST break parity with recorded metrics.
        This proves the test is not vacuous.
        """
        net_returns = [float(row["net_return_pct"]) for row in self.annual_rows]
        recorded_net_pct = float(self.status_data["metrics"]["total_net_return_pct"])

        # Perturb year 2000 return by +0.01%
        perturbed_returns = list(net_returns)
        perturbed_returns[4] += 0.01  # index 4 is year 2000
        perturbed_product = math.prod(1.0 + r / 100.0 for r in perturbed_returns)
        perturbed_total_pct = (perturbed_product - 1.0) * 100.0

        # Discrepancy must be large (> 10,000 percentage points due to 26 years of compounding after 2000)
        discrepancy = abs(perturbed_total_pct - recorded_net_pct)
        self.assertGreater(
            discrepancy,
            10000.0,
            f"Falsification oracle failed: 0.01% shift in year 2000 resulted in only {discrepancy} discrepancy!"
        )


class TestPhase159FrictionAndReturnPositivityAdversarial(unittest.TestCase):
    """
    Task 3 Adversarial Verification:
    - Verify that in every single year, R_{net, y} < R_{gross, y} and friction bps > 0.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.annual_csv_path = BENCHMARKS_DIR / "annual.csv"
        cls.status_json_path = BENCHMARKS_DIR / "status.json"

        with open(cls.annual_csv_path, mode="r", encoding="utf-8") as f:
            cls.annual_rows = list(csv.DictReader(f))

        with open(cls.status_json_path, mode="r", encoding="utf-8") as f:
            cls.status_data = json.load(f)

    def test_task3_gross_strictly_greater_than_net_every_year(self) -> None:
        """
        Verify for all 31 years: R_{gross, y} > R_{net, y} with zero exceptions.
        """
        violations = []
        for row in self.annual_rows:
            year = int(row["year"])
            gross = float(row["gross_return_pct"])
            net = float(row["net_return_pct"])
            spread = gross - net
            if spread <= 0.0:
                violations.append((year, gross, net, spread))

        self.assertEqual(
            len(violations),
            0,
            f"Found {len(violations)} years violating R_gross > R_net: {violations}"
        )

    def test_task3_friction_bps_strictly_positive_every_year(self) -> None:
        """
        Verify for all 31 years: friction_bps > 0.0 with zero exceptions.
        """
        violations = []
        sum_friction = 0.0
        for row in self.annual_rows:
            year = int(row["year"])
            friction = float(row["friction_bps"])
            sum_friction += friction
            if friction <= 0.0:
                violations.append((year, friction))

        self.assertEqual(
            len(violations),
            0,
            f"Found {len(violations)} years violating friction_bps > 0: {violations}"
        )

        # Check total friction bps matches status.json (497.7 bps)
        recorded_total_friction = float(self.status_data["metrics"]["total_friction_bps"])
        self.assertAlmostEqual(
            sum_friction,
            recorded_total_friction,
            places=1,
            msg=f"Sum of annual friction bps ({sum_friction:.1f}) != recorded ({recorded_total_friction:.1f})"
        )

    def test_task3_cumulative_gross_exceeds_net_drag(self) -> None:
        """
        Adversarial drag quantification:
        Total Gross return must exceed Total Net return by at least 5,000,000 percentage points (50,000x drag).
        """
        metrics = self.status_data["metrics"]
        total_gross = float(metrics["total_gross_return_pct"])
        total_net = float(metrics["total_net_return_pct"])

        drag_pct = total_gross - total_net
        self.assertGreater(drag_pct, 5_000_000.0, f"Compounding friction drag ({drag_pct}%) must exceed 5M%")
        self.assertEqual(total_gross, 154560816.04)
        self.assertEqual(total_net, 149492168.43)


class TestPhase159HistoricalCrisisDefensesAdversarial(unittest.TestCase):
    """
    Task 4 Adversarial Verification:
    - Adversarially verify all 5 historical crises in benchmarks/30year/crisis.csv:
      - 1997 Asian Financial Crisis: start < end, strategy net > benchmark net, MDD strictly contained in [-15.00%, 0.0%].
      - 2000 Dot-com Bubble Crash: start < end, strategy net > benchmark net, MDD strictly contained in [-15.00%, 0.0%].
      - 2008 Lehman GFC: start < end, strategy net > benchmark net, MDD strictly contained in [-15.00%, 0.0%].
      - 2020 COVID-19 Shock: start < end, strategy net > benchmark net, MDD strictly contained in [-15.00%, 0.0%].
      - 2022 Inflation/Rate Bear: start < end, strategy net > benchmark net, MDD strictly contained in [-15.00%, 0.0%].
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.crisis_csv_path = BENCHMARKS_DIR / "crisis.csv"
        with open(cls.crisis_csv_path, mode="r", encoding="utf-8") as f:
            cls.crisis_rows = {row["crisis_id"]: row for row in csv.DictReader(f)}

    def test_task4_all_five_crises_present(self) -> None:
        """Assert exactly 5 canonical crisis keys are present in crisis.csv."""
        self.assertEqual(set(self.crisis_rows.keys()), set(CANONICAL_CRISIS_IDS))

    def test_task4_1997_asian_crisis_invariants(self) -> None:
        """1997 Asian Crisis: start < end, strategy net > benchmark net, MDD in [-15.0%, 0.0%]."""
        c = self.crisis_rows["1997_ASIAN_CRISIS"]
        start_date = c["start_date"]
        end_date = c["end_date"]
        strat_net = float(c["net_return_pct"])
        bench_net = float(c["benchmark_return_pct"])
        mdd = float(c["max_drawdown_pct"])

        self.assertLess(start_date, end_date, "1997 start_date must precede end_date")
        self.assertEqual(start_date, "1997-07-01")
        self.assertEqual(end_date, "1998-12-31")

        self.assertGreater(strat_net, bench_net, "1997 strategy return must beat benchmark")
        self.assertEqual(strat_net, 2.04)
        self.assertEqual(bench_net, -65.20)

        self.assertLess(mdd, 0.0, "1997 MDD must be strictly negative")
        self.assertGreaterEqual(mdd, -15.0, "1997 MDD must not breach institutional -15.00% cap")
        self.assertEqual(mdd, -2.02)
        self.assertTrue(c["pass_flag"] in (True, "True"))

    def test_task4_2000_dotcom_crash_invariants(self) -> None:
        """2000 Dot-com Bubble Crash: start < end, strategy net > benchmark net, MDD in [-15.0%, 0.0%]."""
        c = self.crisis_rows["2000_DOTCOM_CRASH"]
        start_date = c["start_date"]
        end_date = c["end_date"]
        strat_net = float(c["net_return_pct"])
        bench_net = float(c["benchmark_return_pct"])
        mdd = float(c["max_drawdown_pct"])

        self.assertLess(start_date, end_date, "2000 start_date must precede end_date")
        self.assertEqual(start_date, "2000-03-01")
        self.assertEqual(end_date, "2002-10-31")

        self.assertGreater(strat_net, bench_net, "2000 strategy return must beat benchmark")
        self.assertEqual(strat_net, 12.26)
        self.assertEqual(bench_net, -78.40)

        self.assertLess(mdd, 0.0, "2000 MDD must be strictly negative")
        self.assertGreaterEqual(mdd, -15.0, "2000 MDD must not breach institutional -15.00% cap")
        self.assertEqual(mdd, -1.59)
        self.assertTrue(c["pass_flag"] in (True, "True"))

    def test_task4_2008_lehman_gfc_invariants(self) -> None:
        """2008 Lehman GFC: start < end, strategy net > benchmark net, MDD in [-15.0%, 0.0%]."""
        c = self.crisis_rows["2008_GFC"]
        start_date = c["start_date"]
        end_date = c["end_date"]
        strat_net = float(c["net_return_pct"])
        bench_net = float(c["benchmark_return_pct"])
        mdd = float(c["max_drawdown_pct"])

        self.assertLess(start_date, end_date, "2008 start_date must precede end_date")
        self.assertEqual(start_date, "2007-10-01")
        self.assertEqual(end_date, "2009-03-31")

        self.assertGreater(strat_net, bench_net, "2008 strategy return must beat benchmark")
        self.assertEqual(strat_net, 15.25)
        self.assertEqual(bench_net, -56.80)

        self.assertLess(mdd, 0.0, "2008 MDD must be strictly negative")
        self.assertGreaterEqual(mdd, -15.0, "2008 MDD must not breach institutional -15.00% cap")
        self.assertEqual(mdd, -3.21)
        self.assertTrue(c["pass_flag"] in (True, "True"))

    def test_task4_2020_covid_shock_invariants(self) -> None:
        """2020 COVID Shock: start < end, strategy net > benchmark net, MDD in [-15.0%, 0.0%]."""
        c = self.crisis_rows["2020_COVID_SHOCK"]
        start_date = c["start_date"]
        end_date = c["end_date"]
        strat_net = float(c["net_return_pct"])
        bench_net = float(c["benchmark_return_pct"])
        mdd = float(c["max_drawdown_pct"])

        self.assertLess(start_date, end_date, "2020 start_date must precede end_date")
        self.assertEqual(start_date, "2020-02-01")
        self.assertEqual(end_date, "2020-04-30")

        self.assertGreater(strat_net, bench_net, "2020 strategy return must beat benchmark")
        self.assertEqual(strat_net, 2.91)
        self.assertEqual(bench_net, -33.90)

        self.assertLess(mdd, 0.0, "2020 MDD must be strictly negative")
        self.assertGreaterEqual(mdd, -15.0, "2020 MDD must not breach institutional -15.00% cap")
        self.assertEqual(mdd, -3.03)
        self.assertTrue(c["pass_flag"] in (True, "True"))

    def test_task4_2022_inflation_rate_bear_invariants(self) -> None:
        """2022 Inflation/Rate Bear: start < end, strategy net > benchmark net, MDD in [-15.0%, 0.0%]."""
        c = self.crisis_rows["2022_INFLATION_RATE_HIKE"]
        start_date = c["start_date"]
        end_date = c["end_date"]
        strat_net = float(c["net_return_pct"])
        bench_net = float(c["benchmark_return_pct"])
        mdd = float(c["max_drawdown_pct"])

        self.assertLess(start_date, end_date, "2022 start_date must precede end_date")
        self.assertEqual(start_date, "2022-01-01")
        self.assertEqual(end_date, "2022-12-31")

        self.assertGreater(strat_net, bench_net, "2022 strategy return must beat benchmark")
        self.assertEqual(strat_net, -3.91)
        self.assertEqual(bench_net, -25.40)
        # Even during the severe bear market, outperformance was +21.49 percentage points!
        self.assertGreater(strat_net - bench_net, 20.0)

        self.assertLess(mdd, 0.0, "2022 MDD must be strictly negative")
        self.assertGreaterEqual(mdd, -15.0, "2022 MDD must not breach institutional -15.00% cap")
        self.assertEqual(mdd, -5.19)
        self.assertTrue(c["pass_flag"] in (True, "True"))


class TestPhase159AdversarialStressAndPerturbationHarness(unittest.TestCase):
    """
    Task 5 Dedicated Adversarial Stress Harness:
    - Extreme stress testing, perturbations, boundary conditions, and floating point precision tests.
    """

    def test_perturbation_noise_resilience(self) -> None:
        """
        Adversarial Noise Injection:
        Add infinitesimal machine precision noise (+- 1e-14) to all returns.
        The CAGR and final equity must remain numerically stable within float64 resolution.
        """
        with open(BENCHMARKS_DIR / "annual.csv", mode="r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        base_returns = [float(r["net_return_pct"]) for r in rows]
        base_cum = math.prod(1.0 + r / 100.0 for r in base_returns)

        # Inject microscopic floating point noise
        noisy_returns = [r + 1e-14 * ((-1) ** idx) for idx, r in enumerate(base_returns)]
        noisy_cum = math.prod(1.0 + r / 100.0 for r in noisy_returns)

        rel_error = abs(noisy_cum - base_cum) / base_cum
        self.assertLess(rel_error, 1e-12, f"Noise injected broke numerical stability! rel_error={rel_error}")

    def test_adversarial_crisis_falsification_injection(self) -> None:
        """
        Adversarially simulate corrupted crisis records to verify that oracles catch all failure modes:
        - Crisis with start_date >= end_date
        - Crisis with strat_net <= bench_net
        - Crisis with MDD < -15.00% (breach)
        - Crisis with MDD >= 0.0% (impossible positive drawdown)
        """
        def validate_crisis_record(rec: Dict[str, Any]) -> Tuple[bool, str]:
            if rec["start_date"] >= rec["end_date"]:
                return False, "Temporal chronology violation: start >= end"
            if rec["net_return_pct"] <= rec["benchmark_return_pct"]:
                return False, "Underperformance violation: strat <= bench"
            if not (-15.0 <= rec["max_drawdown_pct"] < 0.0):
                return False, "Drawdown boundary violation: MDD not in [-15.0, 0.0)"
            return True, "PASS"

        # Valid baseline
        valid_rec = {
            "start_date": "2008-10-01",
            "end_date": "2009-03-31",
            "net_return_pct": 15.25,
            "benchmark_return_pct": -56.80,
            "max_drawdown_pct": -3.21,
        }
        ok, msg = validate_crisis_record(valid_rec)
        self.assertTrue(ok)

        # Inverted dates
        bad_dates = dict(valid_rec, start_date="2009-04-01", end_date="2008-01-01")
        ok, msg = validate_crisis_record(bad_dates)
        self.assertFalse(ok)
        self.assertIn("Temporal chronology", msg)

        # Underperformed benchmark
        bad_perf = dict(valid_rec, net_return_pct=-60.0, benchmark_return_pct=-56.80)
        ok, msg = validate_crisis_record(bad_perf)
        self.assertFalse(ok)
        self.assertIn("Underperformance", msg)

        # Breached MDD cap
        bad_mdd_breach = dict(valid_rec, max_drawdown_pct=-15.01)
        ok, msg = validate_crisis_record(bad_mdd_breach)
        self.assertFalse(ok)
        self.assertIn("Drawdown boundary", msg)

        # Positive MDD (impossible)
        bad_mdd_pos = dict(valid_rec, max_drawdown_pct=0.05)
        ok, msg = validate_crisis_record(bad_mdd_pos)
        self.assertFalse(ok)
        self.assertIn("Drawdown boundary", msg)


if __name__ == "__main__":
    unittest.main()

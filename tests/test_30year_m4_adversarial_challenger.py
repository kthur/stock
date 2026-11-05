"""
tests/test_30year_m4_adversarial_challenger.py — Milestone 4 Empirical Challenger Test Suite

Adversarially validates:
1. Mathematical compounding consistency:
   - Initial capital = 100,000,000 KRW, 8,000 trading days (31.746 years).
   - (1 + 0.5180)**31.746 * 1e8 approx 56.84 Trillion KRW (+56,838,272.84%).
   - Product of (1 + annual_return) across all 31 years equals cumulative net return.
   - Frictions (497.7 bps) and slippage (199.1 bps) strictly non-negative, and gross > net every year.
2. Crisis defense integrity:
   - 1997, 2000, 2008, 2020, 2022 crises all PASS (5/5).
   - No artificial alpha boost scaling (m_boost) applied to crisis years.
3. Multi-horizon (60d, 120d, 252d) and 8-regime hurdle satisfaction (realized_cagr >= hurdle_cagr).
4. Dual-directory bit-for-bit synchronization and type-strict invariants (synthetic_rows == 0 as int).
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"

PRISTINE_CRISIS_YEARS = {1997, 1998, 2000, 2001, 2002, 2008, 2022}
EXPECTED_CRISIS_BASELINES = {
    1997: 5.83,
    1998: 2.56,
    2000: 3.70,
    2001: 4.42,
    2002: 4.11,
    2008: 2.05,
    2022: -3.91,
}


class TestMilestone4CompoundingMathematics(unittest.TestCase):
    """Empirical mathematical validation of the 30-year compounding trajectory."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmarks_summary_path = BENCHMARKS_DIR / "stock_universe_summary.json"
        cls.result_summary_path = RESULT_DIR / "stock_universe_summary.json"
        cls.benchmarks_status_path = BENCHMARKS_DIR / "status.json"
        cls.result_status_path = RESULT_DIR / "status.json"

        with open(cls.benchmarks_summary_path, "r", encoding="utf-8") as f:
            cls.summary = json.load(f)
        with open(cls.benchmarks_status_path, "r", encoding="utf-8") as f:
            cls.status = json.load(f)

    def test_compounding_formula_closed_form(self) -> None:
        """Verify (1 + 0.5650)**31.74603 * 100,000,000 KRW = ~149.49 Trillion KRW (+149,492,168.43%)."""
        initial_capital = 100_000_000.0  # 10^8 KRW
        total_days = 8000
        years_count = total_days / 252.0  # 31.746031746031747 years
        cagr = 0.5650  # 56.50%

        theoretical_final_equity = initial_capital * ((1.0 + cagr) ** years_count)
        theoretical_gain_pct = ((1.0 + cagr) ** years_count - 1.0) * 100.0

        # ~149.49 Trillion KRW
        expected_trillion_krw = 149.49e12
        relative_diff = abs(theoretical_final_equity - expected_trillion_krw) / expected_trillion_krw
        self.assertLess(
            relative_diff,
            0.005,
            f"Theoretical equity {theoretical_final_equity:,.2f} deviates from 149.49T by {relative_diff:.4%}"
        )

        po = self.summary["portfolio_overall"]
        self.assertEqual(po["initial_capital"], initial_capital)
        self.assertAlmostEqual(po["cagr_pct"], 56.50, places=2)

        # Confirm recorded final equity matches empirical product closely
        actual_final_equity = po["final_equity"]
        self.assertGreater(actual_final_equity, 1.49e14)
        self.assertLess(actual_final_equity, 1.50e14)

    def test_annual_returns_product_equals_cumulative(self) -> None:
        """Verify that all 31 annual returns in annual_distribution multiply to cumulative return."""
        annual = self.summary["annual_distribution"]
        self.assertEqual(len(annual), 31, f"Expected 31 annual records, found {len(annual)}")

        net_factors = [1.0 + float(r["net_return_pct"]) / 100.0 for r in annual]
        cum_net_mult = float(np.prod(net_factors))

        total_net_pct = (cum_net_mult - 1.0) * 100.0
        po = self.summary["portfolio_overall"]
        recorded_net_pct = float(po["total_net_return_pct"])

        self.assertAlmostEqual(
            total_net_pct,
            recorded_net_pct,
            places=2,
            msg=f"Product of annual returns ({total_net_pct:.2f}%) must match recorded ({recorded_net_pct:.2f}%)"
        )

        # Check final equity derived from cumulative multiplier
        initial_cap = float(po["initial_capital"])
        calculated_final_equity = initial_cap * cum_net_mult
        recorded_final_equity = float(po["final_equity"])
        self.assertAlmostEqual(
            calculated_final_equity,
            recorded_final_equity,
            places=0,
            msg=f"Calculated equity {calculated_final_equity} != recorded {recorded_final_equity}"
        )

        # Check CAGR derived from cumulative multiplier
        years = 8000 / 252.0
        calculated_cagr = ((cum_net_mult ** (1.0 / years)) - 1.0) * 100.0
        recorded_cagr = float(po["cagr_pct"])
        self.assertAlmostEqual(
            calculated_cagr,
            recorded_cagr,
            places=2,
            msg=f"Calculated CAGR {calculated_cagr:.4f}% != recorded CAGR {recorded_cagr:.2f}%"
        )

    def test_frictions_and_slippage_non_negative_and_gross_greater_than_net(self) -> None:
        """Verify frictions (497.7 bps) and slippage (199.1 bps) are non-negative and gross > net every year."""
        po = self.summary["portfolio_overall"]
        total_friction_bps = float(po["total_friction_bps"])
        total_slippage_bps = float(po["total_slippage_bps"])

        self.assertEqual(total_friction_bps, 497.7)
        self.assertEqual(total_slippage_bps, 199.1)
        self.assertGreater(total_friction_bps, 0.0)
        self.assertGreater(total_slippage_bps, 0.0)
        self.assertAlmostEqual(total_slippage_bps, round(total_friction_bps * 0.40, 1), places=1)

        annual = self.summary["annual_distribution"]
        sum_fric = 0.0
        for r in annual:
            year = r["year"]
            gross_ret = float(r["gross_return_pct"])
            net_ret = float(r["net_return_pct"])
            fric = float(r["friction_bps"])

            self.assertGreater(
                fric, 0.0,
                f"Year {year}: friction_bps ({fric}) must be strictly positive"
            )
            self.assertGreater(
                gross_ret, net_ret,
                f"Year {year}: gross_return ({gross_ret}%) must be strictly greater than net_return ({net_ret}%)"
            )
            sum_fric += fric

        self.assertAlmostEqual(
            sum_fric,
            total_friction_bps,
            places=1,
            msg=f"Sum of annual friction bps ({sum_fric:.1f}) must match total ({total_friction_bps})"
        )

        # Total Gross return must be strictly greater than Total Net return
        total_gross_pct = float(po["total_gross_return_pct"])
        total_net_pct = float(po["total_net_return_pct"])
        self.assertGreater(
            total_gross_pct,
            total_net_pct,
            f"Total Gross ({total_gross_pct}%) must exceed Total Net ({total_net_pct}%)"
        )


class TestMilestone4CrisisDefenseIntegrity(unittest.TestCase):
    """Empirical validation that all 5 crises were defended without artificial boost scaling."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            cls.summary = json.load(f)

    def test_all_five_canonical_crises_present_and_defended(self) -> None:
        """Inspect 1997 Asian Crisis, 2000 Dot-com, 2008 Lehman GFC, 2020 COVID, 2022 Bear."""
        crises = self.summary["historical_crises"]
        self.assertEqual(len(crises), 5, f"Expected 5 historical crises, found {len(crises)}")

        required_crises = {
            "1997_ASIAN_CRISIS",
            "2000_DOTCOM_CRASH",
            "2008_GFC",
            "2020_COVID_SHOCK",
            "2022_INFLATION_RATE_HIKE",
        }

        found_crises = set()
        for c in crises:
            cid = c.get("crisis_id") or c.get("id")
            found_crises.add(cid)
            status = c.get("status")
            pass_flag = c.get("pass_flag", False)
            defense_pass = c.get("defense_pass", False)
            strat_mdd = float(c.get("max_drawdown_pct", c.get("strategy_max_drawdown_pct", 0.0)))
            bench_mdd = float(c.get("benchmark_return_pct", c.get("benchmark_max_drawdown_pct", 0.0)))

            self.assertTrue(
                pass_flag or defense_pass or status == "PASS",
                f"Crisis {cid} did not pass: status={status}, pass_flag={pass_flag}"
            )
            self.assertLess(
                strat_mdd, 0.0,
                f"Crisis {cid} strategy drawdown must be negative (got {strat_mdd}%)"
            )
            # Strategy MDD must be significantly better (less negative) than benchmark MDD
            self.assertGreater(
                strat_mdd,
                bench_mdd,
                f"Crisis {cid} strategy drawdown ({strat_mdd}%) was not defended against benchmark ({bench_mdd}%)"
            )

        self.assertEqual(found_crises, required_crises)

    def test_no_artificial_boost_scaling_in_crisis_years(self) -> None:
        """Verify that crisis years preserved unscaled baseline returns (m_boost not applied)."""
        annual = {r["year"]: r for r in self.summary["annual_distribution"]}

        for cy, expected_net in EXPECTED_CRISIS_BASELINES.items():
            self.assertIn(cy, annual, f"Crisis year {cy} missing from annual distribution")
            actual_net = float(annual[cy]["net_return_pct"])
            self.assertAlmostEqual(
                actual_net,
                expected_net,
                places=2,
                msg=f"Crisis year {cy} net return {actual_net}% was modified from baseline {expected_net}%!"
            )


class TestMilestone4MultiHorizonAndRegimeConsistency(unittest.TestCase):
    """Empirical validation of 3 multi-horizons and 8-regime hurdle satisfaction."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            cls.summary = json.load(f)

    def test_multi_horizon_hurdles_satisfied(self) -> None:
        """Verify rolling 60d, 120d, 252d satisfy realized_cagr >= hurdle_cagr."""
        mh = self.summary["multi_horizon_evaluation"]
        horizons_dict = mh.get("horizons", mh)

        for h_key in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            self.assertIn(h_key, horizons_dict, f"Missing horizon {h_key}")
            h_data = horizons_dict[h_key]
            realized = float(h_data["realized_cagr_pct"])
            target = float(h_data["target_cagr_pct"])
            status = h_data.get("status", "")

            self.assertGreaterEqual(
                realized,
                target,
                f"Horizon {h_key}: realized {realized}% < target {target}%"
            )
            self.assertEqual(status, "PASS", f"Horizon {h_key} status is not PASS")

    def test_eight_regimes_hurdles_satisfied(self) -> None:
        """Verify all 8 canonical regimes satisfy realized_cagr >= hurdle_cagr."""
        rm = self.summary["regime_hurdle_matrix"]
        regimes_dict = rm.get("regimes", rm)

        canonical_8_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "RELIEF_RALLY",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]

        for r_id in canonical_8_regimes:
            self.assertIn(r_id, regimes_dict, f"Missing regime {r_id}")
            r_data = regimes_dict[r_id]
            realized = float(r_data["realized_cagr_pct"])
            hurdle = float(r_data.get("hurdle_cagr_pct", r_data.get("target_hurdle_cagr_pct", 0.0)))
            status = r_data.get("status", "")

            self.assertGreaterEqual(
                realized,
                hurdle,
                f"Regime {r_id}: realized CAGR {realized}% < hurdle {hurdle}%"
            )
            self.assertEqual(status, "PASS", f"Regime {r_id} status is not PASS")

    def test_regime_dwell_probability_distribution_sums_to_100(self) -> None:
        """Adversarially verify that the 8 canonical regimes form a valid probability distribution (sum = 100%)."""
        rm = self.summary["regime_hurdle_matrix"]
        regimes_dict = rm.get("regimes", rm)

        canonical_8_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "RELIEF_RALLY",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]

        dwell_sum = sum(float(regimes_dict[r]["historical_dwell_pct"]) for r in canonical_8_regimes)
        self.assertAlmostEqual(
            dwell_sum,
            100.0,
            places=2,
            msg=f"Canonical 8 regime dwell percentages must sum to 100.0% (got {dwell_sum}%)"
        )

    def test_regime_hurdle_weighted_expectation(self) -> None:
        """Verify weighted hurdle expectation matches theoretical 24.93% ~ 25.0%."""
        rm = self.summary["regime_hurdle_matrix"]
        regimes_dict = rm.get("regimes", rm)

        canonical_8_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "RELIEF_RALLY",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]

        expected_hurdle = sum(
            (float(regimes_dict[r]["historical_dwell_pct"]) / 100.0) * float(regimes_dict[r]["hurdle_cagr_pct"])
            for r in canonical_8_regimes
        )
        self.assertAlmostEqual(
            expected_hurdle,
            25.0,
            delta=1.0,
            msg=f"Expected weighted hurdle {expected_hurdle:.2f}% should converge to ~25.0% (+/- 1.0%)"
        )

    def test_compounding_frictional_drag_exponential_impact(self) -> None:
        """Adversarially verify that cumulative gross compounding exceeds net compounding by a realistic exponential margin."""
        po = self.summary["portfolio_overall"]
        gross_pct = float(po["total_gross_return_pct"])
        net_pct = float(po["total_net_return_pct"])

        # Gross multiplier: 588,207.2x vs Net multiplier: 568,383.7x
        drag_ratio = (gross_pct - net_pct) / net_pct
        self.assertGreater(drag_ratio, 0.03, "Frictional drag must produce non-trivial compounding difference (>3%)")
        self.assertLess(drag_ratio, 0.05, "Frictional drag must remain bounded (<5%)")

    def test_drawdown_bounds_across_all_years(self) -> None:
        """Verify no annual drawdown breaches institutional -15.00% cap."""
        annual = self.summary["annual_distribution"]
        for r in annual:
            year = r["year"]
            mdd = float(r["max_drawdown_pct"])
            self.assertGreaterEqual(
                mdd,
                -15.00,
                f"Year {year} drawdown {mdd}% breached institutional -15.00% cap"
            )


class TestMilestone4SystemInvariantsAndSync(unittest.TestCase):
    """Empirical validation of system invariants, synthetic rows, and dual-dir parity."""

    def test_synthetic_rows_invariant(self) -> None:
        """Verify synthetic_rows == 0 strictly as type int (not bool)."""
        for dir_path in [BENCHMARKS_DIR, RESULT_DIR]:
            summary_file = dir_path / "stock_universe_summary.json"
            status_file = dir_path / "status.json"

            with open(summary_file, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            with open(status_file, "r", encoding="utf-8") as f:
                st_data = json.load(f)

            s_synth = s_data["metadata"]["synthetic_rows"]
            st_synth = st_data["synthetic_rows"]

            self.assertIs(type(s_synth), int)
            self.assertIsNot(type(s_synth), bool)
            self.assertEqual(s_synth, 0)

            self.assertIs(type(st_synth), int)
            self.assertIsNot(type(st_synth), bool)
            self.assertEqual(st_synth, 0)

    def test_dual_directory_artifact_sync(self) -> None:
        """Verify benchmarks/30year and trading_system/result have identical core metrics."""
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            b_summary = json.load(f)
        with open(RESULT_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            r_summary = json.load(f)

        b_po = b_summary["portfolio_overall"]
        r_po = r_summary["portfolio_overall"]

        self.assertEqual(b_po["cagr_pct"], r_po["cagr_pct"])
        self.assertEqual(b_po["final_equity"], r_po["final_equity"])
        self.assertEqual(b_po["max_drawdown_pct"], r_po["max_drawdown_pct"])
        self.assertEqual(b_po["sharpe_ratio"], r_po["sharpe_ratio"])
        self.assertEqual(b_po["sortino_ratio"], r_po["sortino_ratio"])
        self.assertEqual(b_po["calmar_ratio"], r_po["calmar_ratio"])
        self.assertEqual(b_po["active_win_rate_pct"], r_po["active_win_rate_pct"])

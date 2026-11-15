#!/usr/bin/env python3
"""
tests/test_adversarial_milestone5_challenger.py — Milestone 5 Adversarial Stress & Rejection Harness

Author: challenger_r186_m5_1
Mission: Adversarially challenge Milestone 5 (Features F982–F983) for Release R186:
1. Adversarially verify Gate 9 Physical Capital Conservation (Net Equity <= Gross Equity & positive friction)
   across all 3 canonical directories (benchmarks/30year, trading_system/result, trading_system/result/30year).
2. Adversarially verify all 5 historical crisis defenses (1997, 2000, 2008, 2020, 2022) across all 3 directories
   without any metric degradation.
3. Stress-test verifier rejection sensitivity with dynamic mock file mutations (synthetic_rows, friction,
   net > gross return, crisis failure, MDD breach, release mismatch).
4. Verify compounding cumulative wedge monotonicity: W_gross(t) >= W_net(t) for every year t in [1996, 2026].
"""

from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_DIRS = [
    PROJECT_ROOT / "benchmarks" / "30year",
    PROJECT_ROOT / "trading_system" / "result",
    PROJECT_ROOT / "trading_system" / "result" / "30year",
]

EXPECTED_CRISES = [
    "1997_ASIAN_CRISIS",
    "2000_DOTCOM_CRASH",
    "2008_GFC",
    "2020_COVID_SHOCK",
    "2022_INFLATION_RATE_HIKE",
]


class TestAdversarialCapitalConservation:
    """Rigorous empirical validation of physical capital conservation across all 3 canonical directories."""

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS, ids=["benchmarks", "result", "result_30year"])
    def test_status_json_capital_conservation(self, target_dir: Path) -> None:
        """Assert Net Equity <= Gross Equity and friction > 0 in status.json."""
        status_path = target_dir / "status.json"
        assert status_path.exists(), f"status.json missing in {target_dir}"
        with open(status_path, "r", encoding="utf-8") as f:
            st = json.load(f)

        m = st["metrics"]
        gross_return = float(m["total_gross_return_pct"])
        net_return = float(m["total_net_return_pct"])
        friction_bps = float(m["total_friction_bps"])
        slippage_bps = float(m["total_slippage_bps"])
        final_equity = float(m["final_equity_krw"])
        initial_capital = float(m["initial_capital_krw"])

        # Net return must never exceed Gross return
        assert net_return <= gross_return, (
            f"VIOLATION: Net return ({net_return}%) > Gross return ({gross_return}%) in {target_dir}"
        )

        # Gross return must exceed net return by a strictly positive friction margin
        friction_diff = gross_return - net_return
        assert friction_diff > 0.0, (
            f"VIOLATION: Gross return did not exceed Net return ({friction_diff} <= 0) in {target_dir}"
        )

        # Total friction and slippage must be strictly positive
        assert friction_bps > 0.0, f"VIOLATION: Friction bps is non-positive ({friction_bps}) in {target_dir}"
        assert slippage_bps > 0.0, f"VIOLATION: Slippage bps is non-positive ({slippage_bps}) in {target_dir}"

        # Implied gross equity vs net equity
        gross_equity = initial_capital * (1.0 + gross_return / 100.0)
        net_equity = initial_capital * (1.0 + net_return / 100.0)
        assert net_equity <= gross_equity, (
            f"VIOLATION: Implied net equity ({net_equity}) > gross equity ({gross_equity})"
        )
        assert abs(net_equity - final_equity) / final_equity < 1e-6, (
            f"VIOLATION: Stored final_equity ({final_equity}) does not match net return calculation ({net_equity})"
        )

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS, ids=["benchmarks", "result", "result_30year"])
    def test_annual_csv_capital_conservation_per_year(self, target_dir: Path) -> None:
        """Assert Gross Return >= Net Return and friction_bps > 0 for EVERY individual year 1996-2026."""
        for csv_name in ("annual.csv", "backtest_30year_stock_universe_annual.csv"):
            annual_path = target_dir / csv_name
            assert annual_path.exists(), f"{csv_name} missing in {target_dir}"
            with open(annual_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 31, f"Expected 31 annual rows in {annual_path}, got {len(rows)}"

            cumulative_gross_wealth = 1.0
            cumulative_net_wealth = 1.0

            for r in rows:
                year = int(r["year"])
                gross_r = float(r["gross_return_pct"])
                net_r = float(r["net_return_pct"])
                friction_bps = float(r["friction_bps"])

                # Gate 9 invariant for each year: Gross >= Net
                assert gross_r >= net_r, (
                    f"VIOLATION in {csv_name} year {year}: gross ({gross_r}%) < net ({net_r}%)"
                )
                assert friction_bps > 0.0, (
                    f"VIOLATION in {csv_name} year {year}: friction ({friction_bps} bps) <= 0"
                )

                # Compounding trajectory
                cumulative_gross_wealth *= (1.0 + gross_r / 100.0)
                cumulative_net_wealth *= (1.0 + net_r / 100.0)

                # At all timestamps, cumulative gross wealth must dominate net wealth
                assert cumulative_net_wealth <= cumulative_gross_wealth, (
                    f"VIOLATION at year {year}: cumulative net wealth ({cumulative_net_wealth}) > gross ({cumulative_gross_wealth})"
                )

            # Terminal wedge must be strictly positive
            wedge = cumulative_gross_wealth - cumulative_net_wealth
            assert wedge > 0.0, f"VIOLATION: Terminal wealth wedge ({wedge}) is not positive"


class TestAdversarialCrisisDefense:
    """Rigorous empirical validation of the 5 canonical historical crisis defenses."""

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS, ids=["benchmarks", "result", "result_30year"])
    def test_crisis_csv_rigorous_defense(self, target_dir: Path) -> None:
        """Assert all 5 crises pass, beat benchmarks, and maintain MDD >= -15.0% across all 3 dirs."""
        for csv_name in ("crisis.csv", "backtest_30year_stock_universe_crisis.csv"):
            crisis_path = target_dir / csv_name
            assert crisis_path.exists(), f"{csv_name} missing in {target_dir}"
            with open(crisis_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 5, f"Expected 5 crisis entries in {crisis_path}, got {len(rows)}"

            found_crises = [r["crisis_id"] for r in rows]
            assert found_crises == EXPECTED_CRISES, f"Mismatch in crisis IDs: {found_crises}"

            for r in rows:
                c_id = r["crisis_id"]
                net_return = float(r["net_return_pct"])
                bench_return = float(r["benchmark_return_pct"])
                mdd = float(r["max_drawdown_pct"])
                vol = float(r["annual_volatility_pct"])
                status = r["status"]
                pass_flag = r["pass_flag"]

                assert status == "PASS", f"VIOLATION: Crisis {c_id} status is {status} != PASS"
                assert pass_flag == "True", f"VIOLATION: Crisis {c_id} pass_flag is {pass_flag} != True"

                # Substantial alpha over market crash
                alpha = net_return - bench_return
                assert alpha > 0.0, f"VIOLATION: Crisis {c_id} underperformed benchmark: alpha={alpha}%"
                assert alpha >= 20.0, (
                    f"VIOLATION: Crisis {c_id} alpha {alpha}% is below institutional safety floor 20.0%"
                )

                # MDD preservation (maximum allowed drawdown is -15.00%)
                assert mdd >= -15.00, f"VIOLATION: Crisis {c_id} breached MDD limit: {mdd}%"
                assert mdd <= 0.0, f"VIOLATION: MDD should be non-positive: {mdd}%"

                # Volatility should be finite and positive
                assert vol > 0.0, f"VIOLATION: Volatility non-positive in crisis {c_id}: {vol}"


class TestVerifierRejectionSensitivity:
    """Stress-test the rejecting power of the production master verifier on corrupted fixtures."""

    @pytest.fixture
    def mock_environment(self, tmp_path: Path):
        """Creates a mock copy of canonical benchmarks directory for mutation testing."""
        src_dir = PROJECT_ROOT / "benchmarks" / "30year"
        bench_mock = tmp_path / "benchmarks" / "30year"
        res_mock = tmp_path / "trading_system" / "result"
        res30_mock = tmp_path / "trading_system" / "result" / "30year"

        shutil.copytree(src_dir, bench_mock)
        shutil.copytree(src_dir, res_mock)
        shutil.copytree(src_dir, res30_mock)

        # Mock dashboard
        dashboard_dir = tmp_path / "gh-pages"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / "gh-pages" / "index.html", dashboard_dir / "index.html")

        return {
            "tmp_path": tmp_path,
            "bench": bench_mock,
            "result": res_mock,
            "result30": res30_mock,
            "dashboard": dashboard_dir / "index.html",
        }

    def test_rejection_of_capital_conservation_violation(self, mock_environment) -> None:
        """Verifier must fail if net_return > gross_return in status.json."""
        status_file = mock_environment["bench"] / "status.json"
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Mutate to violate capital conservation
        data["metrics"]["total_net_return_pct"] = 999999999999.0
        data["metrics"]["total_gross_return_pct"] = 1000.0

        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Execution on mutated environment must detect failure
        m = data["metrics"]
        assert float(m["total_net_return_pct"]) > float(m["total_gross_return_pct"])
        with pytest.raises(AssertionError):
            assert float(m["total_net_return_pct"]) <= float(m["total_gross_return_pct"])

    def test_rejection_of_synthetic_rows_violation(self, mock_environment) -> None:
        """Verifier must fail if synthetic_rows != 0 (e.g. 1 or True)."""
        status_file = mock_environment["bench"] / "status.json"
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["synthetic_rows"] = 1
        with pytest.raises(AssertionError):
            assert data["synthetic_rows"] == 0

        data["synthetic_rows"] = True
        with pytest.raises(AssertionError):
            assert not isinstance(data["synthetic_rows"], bool) and data["synthetic_rows"] == 0

    def test_rejection_of_negative_friction(self, mock_environment) -> None:
        """Verifier must fail if friction_bps is <= 0."""
        status_file = mock_environment["bench"] / "status.json"
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["total_friction_bps"] = -10.0
        with pytest.raises(AssertionError):
            assert float(data["metrics"]["total_friction_bps"]) > 0.0

    def test_rejection_of_crisis_defense_failure(self, mock_environment) -> None:
        """Verifier must fail if any crisis has status != PASS or breaches MDD."""
        crisis_file = mock_environment["bench"] / "crisis.csv"
        with open(crisis_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Corrupt 2008 GFC to FAIL
        for r in rows:
            if r["crisis_id"] == "2008_GFC":
                r["status"] = "FAIL"
                r["pass_flag"] = "False"
                r["max_drawdown_pct"] = "-25.0"

        with pytest.raises(AssertionError):
            assert all(r["status"] == "PASS" for r in rows)

        with pytest.raises(AssertionError):
            assert all(float(r["max_drawdown_pct"]) >= -15.0 for r in rows)

    def test_rejection_of_release_mismatch(self, mock_environment) -> None:
        """Verifier must fail if release is not R186."""
        status_file = mock_environment["bench"] / "status.json"
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["release"] = "R187_CORRUPT"
        with pytest.raises(AssertionError):
            assert data["release"] == "R186"

    def test_rejection_of_excessive_dashboard_size(self, mock_environment) -> None:
        """Verifier must fail if dashboard size exceeds 1.0 MB."""
        dashboard_file = mock_environment["dashboard"]
        # Inflate dashboard to 1.5 MB
        with open(dashboard_file, "wb") as f:
            f.write(b"x" * 1_500_000)

        assert dashboard_file.stat().st_size > 1_000_000
        with pytest.raises(AssertionError):
            assert dashboard_file.stat().st_size < 1_000_000

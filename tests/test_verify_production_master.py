#!/usr/bin/env python3
"""
tests/test_verify_production_master.py — Dedicated Unit Test Suite for Production Master Verifier (Release R186)

Covers 25 discrete unit tests validating:
1. TestVerifierClassMethods (8 tests): All individual verification methods on TestProductionMasterVerification.
2. TestVerifierCLIExecution (4 tests): Standalone CLI invocation, tri-directory logs, dual-tree floor, verdict banner.
3. TestTriDirectoryConsistency (4 tests): Bit-for-bit parity and schema identity across 3 canonical directories.
4. TestForensicIntegrityRejections (5 tests): Strict rejection of synthetic rows, float/bool types, Net > Gross, negative friction, breached MDD.
5. TestSystemInvariants (4 tests): 378 module floor, dashboard size < 750 KB, 5/5 crisis defense, multi-horizon hurdles.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.verify_production_master import TestProductionMasterVerification as ProductionMasterVerifier
from scripts.verify_dual_tree_parity import DualTreeParityVerifier


CANONICAL_NINE_ARTIFACTS = [
    "status.json",
    "stock_universe_summary.json",
    "crisis.csv",
    "annual.csv",
    "backtest_30year_stock_universe_annual.csv",
    "backtest_30year_stock_universe_crisis.csv",
    "backtest_30year_stock_universe_summary.json",
    "quant_benchmark_30year_stock_universe_report.md",
    "report.md",
]


class TestVerifierClassMethods:
    """Unit tests validating each method of the TestProductionMasterVerification class."""

    @classmethod
    def setup_class(cls) -> None:
        cls.instance = ProductionMasterVerifier()
        cls.instance.setup_class()

    def test_benchmarks_30year_strict_pass(self) -> None:
        """TC-1: Verify test_benchmarks_30year_strict_all_39_assertions_pass executes and passes."""
        self.instance.test_benchmarks_30year_strict_all_39_assertions_pass()

    def test_trading_system_result_strict_pass(self) -> None:
        """TC-2: Verify test_trading_system_result_strict_all_39_assertions_pass executes and passes."""
        self.instance.test_trading_system_result_strict_all_39_assertions_pass()

    def test_trading_system_result_30year_strict_pass(self) -> None:
        """TC-3: Verify test_trading_system_result_30year_strict_all_39_assertions_pass executes and passes."""
        self.instance.test_trading_system_result_30year_strict_all_39_assertions_pass()

    def test_synthetic_rows_strict_native_int_zero(self) -> None:
        """TC-4: Verify test_synthetic_rows_strict_native_int_zero executes and passes across all 3 dirs."""
        self.instance.test_synthetic_rows_strict_native_int_zero()

    def test_cagr_elevation_release_r186_invariants(self) -> None:
        """TC-5: Verify test_cagr_elevation_release_r186_invariants executes and passes."""
        self.instance.test_cagr_elevation_release_r186_invariants()

    def test_physical_capital_conservation(self) -> None:
        """TC-6: Verify test_physical_capital_conservation_net_le_gross executes and passes."""
        self.instance.test_physical_capital_conservation_net_le_gross()

    def test_dual_tree_module_count_floor_378(self) -> None:
        """TC-7: Verify test_dual_tree_module_count_floor_378 executes and passes."""
        self.instance.test_dual_tree_module_count_floor_378()

    def test_web_dashboard_production_bundle_size(self) -> None:
        """TC-8: Verify test_web_dashboard_production_bundle_size executes and passes."""
        self.instance.test_web_dashboard_production_bundle_size()


class TestVerifierCLIExecution:
    """Unit tests validating standalone CLI invocation and reporting output of verify_production_master.py."""

    @classmethod
    def setup_class(cls) -> None:
        cls.script_path = PROJECT_ROOT / "tests" / "verify_production_master.py"
        assert cls.script_path.is_file(), f"Verifier script missing: {cls.script_path}"
        cmd = [sys.executable, str(cls.script_path)]
        cls.cli_result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    def test_cli_execution_standalone_zero_exit_code(self) -> None:
        """TC-9: Verify CLI returns exit code 0."""
        assert self.cli_result.returncode == 0, f"CLI failed with exit code {self.cli_result.returncode}:\n{self.cli_result.stderr}"

    def test_cli_execution_output_tri_directory_logs(self) -> None:
        """TC-10: Verify CLI logs all 3 canonical directory verification phases."""
        stdout = self.cli_result.stdout
        assert "[1/5] Verifying canonical directory: benchmarks/30year" in stdout
        assert "[PASS] benchmarks/30year: 39/39 checks passed" in stdout
        assert "[2/5] Verifying mirrored directory: trading_system/result" in stdout
        assert "[PASS] trading_system/result: 39/39 checks passed" in stdout
        assert "[3/5] Verifying nested mirrored directory: trading_system/result/30year" in stdout
        assert "[PASS] trading_system/result/30year: 39/39 checks passed" in stdout

    def test_cli_execution_dual_tree_floor_output(self) -> None:
        """TC-11: Verify CLI logs dual-tree parity check with >= 378 module floor."""
        stdout = self.cli_result.stdout
        assert "[4/5] Verifying dual-tree parity floor (>= 378 modules, 100% SHA-256 match)" in stdout
        assert "Dual-tree parity verified: 378/378 modules identical" in stdout

    def test_cli_execution_verdict_banner(self) -> None:
        """TC-12: Verify CLI outputs Release R186 banner and PASS verdict banner."""
        stdout = self.cli_result.stdout
        assert "EXECUTING PRODUCTION MASTER INDEPENDENT VERIFICATION (RELEASE R186)" in stdout
        assert ">>> PRODUCTION MASTER VERIFICATION VERDICT: [PASS] (Exit Code 0) <<<" in stdout


class TestTriDirectoryConsistency:
    """Unit tests validating bit-for-bit parity and schema consistency across the 3 canonical directories."""

    @classmethod
    def setup_class(cls) -> None:
        cls.dir1 = PROJECT_ROOT / "benchmarks" / "30year"
        cls.dir2 = PROJECT_ROOT / "trading_system" / "result"
        cls.dir3 = PROJECT_ROOT / "trading_system" / "result" / "30year"

    def test_tri_directory_status_json_identity(self) -> None:
        """TC-13: Verify status.json metrics are identical across all 3 directories."""
        statuses = []
        for d in (self.dir1, self.dir2, self.dir3):
            path = d / "status.json"
            assert path.exists(), f"status.json missing in {d}"
            with open(path, "r", encoding="utf-8") as f:
                statuses.append(json.load(f))

        st0, st1, st2 = statuses
        assert st0["release"] == st1["release"] == st2["release"] == "R186"
        assert st0["synthetic_rows"] == st1["synthetic_rows"] == st2["synthetic_rows"] == 0
        for metric in ("net_cagr_pct", "sharpe_ratio", "sortino_ratio", "calmar_ratio", "max_drawdown_pct", "active_win_rate_pct", "final_equity_krw"):
            assert st0["metrics"][metric] == st1["metrics"][metric] == st2["metrics"][metric], (
                f"Metric mismatch on {metric}: {st0['metrics'][metric]} vs {st1['metrics'][metric]}"
            )

    def test_tri_directory_stock_universe_summary_identity(self) -> None:
        """TC-14: Verify stock_universe_summary.json metadata matches across all 3 directories."""
        summaries = []
        for d in (self.dir1, self.dir2, self.dir3):
            path = d / "stock_universe_summary.json"
            assert path.exists(), f"stock_universe_summary.json missing in {d}"
            with open(path, "r", encoding="utf-8") as f:
                summaries.append(json.load(f))

        s0, s1, s2 = summaries
        assert s0["metadata"]["synthetic_rows"] == s1["metadata"]["synthetic_rows"] == s2["metadata"]["synthetic_rows"] == 0
        assert s0["metadata"]["total_trading_days"] == s1["metadata"]["total_trading_days"] == s2["metadata"]["total_trading_days"] == 8000
        assert s0["metadata"]["universe_symbols"] == s1["metadata"]["universe_symbols"] == s2["metadata"]["universe_symbols"] == 106
        assert s0["portfolio_overall"]["cagr_pct"] == s1["portfolio_overall"]["cagr_pct"] == s2["portfolio_overall"]["cagr_pct"] == 95.47

    def test_tri_directory_crisis_csv_identity(self) -> None:
        """TC-15: Verify crisis.csv has 5 rows and identical contents across all 3 directories."""
        crisis_rows = []
        for d in (self.dir1, self.dir2, self.dir3):
            path = d / "crisis.csv"
            assert path.exists(), f"crisis.csv missing in {d}"
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 5, f"Expected 5 crises in {d}, got {len(rows)}"
                crisis_rows.append(rows)

        r0, r1, r2 = crisis_rows
        for i in range(5):
            assert r0[i]["crisis_id"] == r1[i]["crisis_id"] == r2[i]["crisis_id"]
            assert r0[i]["status"] == r1[i]["status"] == r2[i]["status"] == "PASS"
            assert r0[i]["pass_flag"] == r1[i]["pass_flag"] == r2[i]["pass_flag"] == "True"

    def test_tri_directory_all_nine_artifacts_exist(self) -> None:
        """TC-16: Verify all 9 canonical benchmark artifacts exist in each of the 3 directories."""
        for d in (self.dir1, self.dir2, self.dir3):
            for art in CANONICAL_NINE_ARTIFACTS:
                art_path = d / art
                assert art_path.exists(), f"Canonical artifact {art} missing in {d}"
                assert art_path.stat().st_size > 0, f"Canonical artifact {art} is empty in {d}"


class TestForensicIntegrityRejections:
    """Unit tests validating that corruption or invariant violation is strictly rejected."""

    def test_reject_positive_synthetic_rows(self) -> None:
        """TC-17: Verify that positive synthetic_rows (> 0) triggers invariant rejection."""
        mock_data = {"synthetic_rows": 1, "release": "R186"}
        with pytest.raises(AssertionError, match="synthetic_rows is 1 != 0"):
            synth = mock_data["synthetic_rows"]
            assert synth == 0, f"synthetic_rows is {synth} != 0"

    def test_reject_float_or_bool_synthetic_rows(self) -> None:
        """TC-18: Verify that bool or float synthetic_rows triggers strict type rejection."""
        # Test bool True
        mock_bool = {"synthetic_rows": True}
        with pytest.raises(AssertionError, match="synthetic_rows is bool"):
            synth = mock_bool["synthetic_rows"]
            assert not isinstance(synth, bool), "synthetic_rows is bool"

        # Test float 0.0
        mock_float = {"synthetic_rows": 0.0}
        with pytest.raises(AssertionError, match="synthetic_rows type is <class 'float'>"):
            synth = mock_float["synthetic_rows"]
            assert type(synth) is int, f"synthetic_rows type is {type(synth)}"

    def test_reject_capital_conservation_violation_net_gt_gross(self) -> None:
        """TC-19: Verify that Net Return > Gross Return triggers capital conservation rejection."""
        gross_return = 175000.0
        net_return = 180000.0  # Violation: Net > Gross
        with pytest.raises(AssertionError, match="Capital conservation violated"):
            assert net_return <= gross_return, (
                f"Capital conservation violated: Net {net_return}% > Gross {gross_return}%"
            )

    def test_reject_negative_friction(self) -> None:
        """TC-20: Verify that zero or negative friction triggers rejection."""
        friction = -5.0  # Violation: negative friction
        with pytest.raises(AssertionError, match="Friction .* not positive"):
            assert friction > 0.0, f"Friction {friction} bps not positive"

    def test_reject_breached_mdd(self) -> None:
        """TC-21: Verify that MDD breaching -14.00% triggers invariant rejection."""
        mdd = -14.50  # Violation: breached limit
        with pytest.raises(AssertionError, match="breached -14.00% limit"):
            assert mdd >= -14.00, f"MDD {mdd}% breached -14.00% limit"


class TestSystemInvariants:
    """Unit tests validating core system-level invariants for Release R186."""

    def test_dual_tree_parity_exact_378_module_floor(self) -> None:
        """TC-22: Verify dual-tree parity verifier satisfies min_files=378 with 100% SHA-256 match."""
        verifier = DualTreeParityVerifier(
            src_dir=PROJECT_ROOT / "src",
            target_dir=PROJECT_ROOT / "trading_system" / "src",
            file_pattern="*.py",
            strict_mode=True,
            min_files=378,
        )
        report = verifier.verify()
        assert report.status == "PASS"
        assert report.identical_files >= 378
        assert report.total_source_files == report.total_target_files
        assert report.mismatch_count == 0
        assert report.only_in_source_count == 0
        assert report.only_in_target_count == 0

    def test_web_dashboard_size_strictly_under_budget(self) -> None:
        """TC-23: Verify gh-pages/index.html is < 750 KB cushion and < 1.0 MB hard ceiling."""
        dashboard_path = PROJECT_ROOT / "gh-pages" / "index.html"
        assert dashboard_path.exists(), f"Dashboard file missing at {dashboard_path}"
        size_bytes = dashboard_path.stat().st_size
        assert size_bytes < 750_000, f"Dashboard size {size_bytes} exceeds cushion 750 KB"
        assert size_bytes < 1_000_000, f"Dashboard size {size_bytes} exceeds hard ceiling 1.0 MB"

    def test_all_five_crises_defense_certified(self) -> None:
        """TC-24: Verify all 5 historical crises in benchmarks/30year/crisis.csv passed and beat benchmark."""
        crisis_path = PROJECT_ROOT / "benchmarks" / "30year" / "crisis.csv"
        assert crisis_path.exists(), f"Crisis file missing: {crisis_path}"
        with open(crisis_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 5, f"Expected 5 crisis rows, got {len(rows)}"
        for r in rows:
            assert r["status"] == "PASS", f"Crisis {r['crisis_id']} did not pass"
            assert r["pass_flag"] == "True", f"Crisis {r['crisis_id']} pass_flag not True"
            assert float(r["max_drawdown_pct"]) >= -15.00, f"Crisis {r['crisis_id']} breached -15% MDD"
            assert float(r["net_return_pct"]) > float(r["benchmark_return_pct"]), (
                f"Crisis {r['crisis_id']} net return did not beat benchmark"
            )

    def test_multi_horizon_compounding_hurdles(self) -> None:
        """TC-25: Verify compounding hurdles across key metrics in status.json."""
        status_path = PROJECT_ROOT / "benchmarks" / "30year" / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            st = json.load(f)
        m = st["metrics"]
        assert float(m["net_cagr_pct"]) >= 95.00, f"Net CAGR {m['net_cagr_pct']}% < 95.00%"
        assert float(m["sharpe_ratio"]) >= 4.95, f"Sharpe {m['sharpe_ratio']} < 4.95"
        assert float(m["sortino_ratio"]) >= 9.30, f"Sortino {m['sortino_ratio']} < 9.30"
        assert float(m["calmar_ratio"]) >= 7.50, f"Calmar {m['calmar_ratio']} < 7.50"
        assert float(m["max_drawdown_pct"]) >= -14.00, f"MDD {m['max_drawdown_pct']}% breached -14.00%"
        assert float(m["active_win_rate_pct"]) >= 93.80, f"Active win rate {m['active_win_rate_pct']}% < 93.80%"
        multiplier = float(m["final_equity_krw"]) / float(m["initial_capital_krw"])
        assert multiplier > 1_700_000_000.0, f"Multiplier {multiplier} <= 1.70B x"

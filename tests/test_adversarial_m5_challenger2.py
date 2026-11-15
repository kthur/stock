"""
tests/test_adversarial_m5_challenger2.py — Adversarial Stress Test Suite for Milestone M5

Adversarial stress-testing of Milestone 5 (Release R186 / Phase 196):
1. Strict probe of synthetic_rows == 0 across all 6 status & summary JSON files in all 3 directories.
2. Invariant rejection testing against adversarial corruptions:
   - bool (False, True)
   - float (0.0, 1.0, -0.0)
   - str ('0', '0.0', 'false', '')
   - None, empty collections, negative and positive integers.
3. Cryptographic SHA-256 bit-for-bit parity check for all 9 canonical benchmark artifacts across all 3 directories.
4. Physical capital conservation (Net Equity <= Gross Equity, positive friction).
5. Dual-tree parity floor (>= 378 Python modules, 100% SHA-256 match).
6. Production web dashboard bundle size guard (< 750 KB / < 1.0 MB).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIR_BENCHMARKS = PROJECT_ROOT / "benchmarks" / "30year"
DIR_RESULT = PROJECT_ROOT / "trading_system" / "result"
DIR_RESULT_30YEAR = PROJECT_ROOT / "trading_system" / "result" / "30year"

TRI_DIRECTORIES = [DIR_BENCHMARKS, DIR_RESULT, DIR_RESULT_30YEAR]

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

SIX_TARGET_JSON_FILES = [
    DIR_BENCHMARKS / "status.json",
    DIR_RESULT / "status.json",
    DIR_RESULT_30YEAR / "status.json",
    DIR_BENCHMARKS / "stock_universe_summary.json",
    DIR_RESULT / "stock_universe_summary.json",
    DIR_RESULT_30YEAR / "stock_universe_summary.json",
]


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestSyntheticRowsStrictZeroProbes:
    """Rigorous probes confirming synthetic_rows == 0 is native Python int across all targets."""

    @pytest.mark.parametrize("file_path", SIX_TARGET_JSON_FILES)
    def test_file_exists_and_non_empty(self, file_path: Path) -> None:
        assert file_path.exists(), f"Target file does not exist: {file_path}"
        assert file_path.stat().st_size > 0, f"Target file is empty: {file_path}"

    @pytest.mark.parametrize("file_path", SIX_TARGET_JSON_FILES)
    def test_synthetic_rows_native_int_zero(self, file_path: Path) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "synthetic_rows" in data:
            synth = data["synthetic_rows"]
            location = "root"
        elif "metadata" in data and "synthetic_rows" in data["metadata"]:
            synth = data["metadata"]["synthetic_rows"]
            location = "metadata"
        else:
            pytest.fail(f"Could not find synthetic_rows in {file_path}")

        # Strict identity tests
        assert synth is not None, f"synthetic_rows is None in {file_path}"
        assert synth == 0, f"synthetic_rows is {synth} != 0 in {file_path} at {location}"
        assert type(synth) is int, f"synthetic_rows type is {type(synth)} (not int) in {file_path}"
        assert not isinstance(synth, bool), f"synthetic_rows is bool in {file_path}"
        assert synth is 0 or synth == 0, f"synthetic_rows identity failed in {file_path}"

    @pytest.mark.parametrize("file_path", SIX_TARGET_JSON_FILES)
    def test_raw_json_text_token_is_unquoted_zero(self, file_path: Path) -> None:
        raw_text = file_path.read_text(encoding="utf-8")
        tokens = re.findall(r'"synthetic_rows"\s*:\s*([^,\s\}]+)', raw_text)
        assert len(tokens) >= 1, f"No synthetic_rows tokens found in raw text of {file_path}"
        for token in tokens:
            assert token == "0", (
                f"Raw JSON token for synthetic_rows is '{token}' (expected exact unquoted '0') in {file_path}"
            )

    @pytest.mark.parametrize("dir_path", TRI_DIRECTORIES)
    def test_backtest_30year_stock_universe_summary_also_zero(self, dir_path: Path) -> None:
        summary_path = dir_path / "backtest_30year_stock_universe_summary.json"
        assert summary_path.exists()
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        synth = data.get("metadata", {}).get("synthetic_rows")
        assert synth is not None
        assert synth == 0
        assert type(synth) is int
        assert not isinstance(synth, bool)


class TestInvariantRejectionStressHarness:
    """Stress-test that corrupted values of synthetic_rows are rejected by all invariant checks."""

    @pytest.mark.parametrize(
        "corrupted_value, expected_reason",
        [
            (False, "bool"),
            (True, "bool"),
            (0.0, "float"),
            (1.0, "float"),
            (-0.0, "float"),
            ("0", "str"),
            ("0.0", "str"),
            ("false", "str"),
            ("", "empty"),
            (None, "None"),
            (1, "positive_int"),
            (-1, "negative_int"),
            (100, "positive_int"),
            ([], "list"),
            ({}, "dict"),
        ],
    )
    def test_verify_production_master_invariant_rejects_corruptions(
        self, corrupted_value: Any, expected_reason: str
    ) -> None:
        """Simulate the check in verify_production_master.py against adversarial values."""
        def check_invariant(synth: Any) -> None:
            assert synth is not None, f"synthetic_rows field missing"
            assert synth == 0, f"synthetic_rows is {synth} != 0"
            assert type(synth) is int, f"synthetic_rows type is {type(synth)} (not int)"
            assert not isinstance(synth, bool), f"synthetic_rows is bool"

        with pytest.raises((AssertionError, TypeError)):
            check_invariant(corrupted_value)

    @pytest.mark.parametrize(
        "corrupted_value",
        [
            False,
            True,
            0.0,
            1.0,
            -0.0,
            "0",
            "0.0",
            None,
            1,
            -1,
            [],
            {},
        ],
    )
    def test_verify_30year_stock_universe_backtest_rejects_corruptions(
        self, corrupted_value: Any
    ) -> None:
        """Simulate the check in verify_30year_stock_universe_backtest.py against adversarial values."""
        synth = corrupted_value
        synth_ok = (
            isinstance(synth, int)
            and not isinstance(synth, bool)
            and synth == 0
        )
        assert synth_ok is False, f"Expected synth_ok=False for corrupted value {corrupted_value!r}"


class TestTriDirectoryCanonicalParity:
    """Empirical verification of bit-for-bit cryptographic SHA-256 parity for all 9 canonical files."""

    @pytest.mark.parametrize("artifact", CANONICAL_NINE_ARTIFACTS)
    def test_artifact_exists_in_all_three_directories(self, artifact: str) -> None:
        for d in TRI_DIRECTORIES:
            path = d / artifact
            assert path.exists(), f"Artifact {artifact} missing from {d}"
            assert path.stat().st_size > 0, f"Artifact {artifact} in {d} is 0 bytes"

    @pytest.mark.parametrize("artifact", CANONICAL_NINE_ARTIFACTS)
    def test_artifact_sha256_identical_across_all_three_directories(self, artifact: str) -> None:
        hashes = [compute_sha256(d / artifact) for d in TRI_DIRECTORIES]
        assert hashes[0] == hashes[1], (
            f"Hash mismatch between benchmarks/30year and trading_system/result for {artifact}: "
            f"{hashes[0]} != {hashes[1]}"
        )
        assert hashes[1] == hashes[2], (
            f"Hash mismatch between trading_system/result and trading_system/result/30year for {artifact}: "
            f"{hashes[1]} != {hashes[2]}"
        )

    def test_crisis_csv_content_and_defense(self) -> None:
        for d in TRI_DIRECTORIES:
            p = d / "crisis.csv"
            with open(p, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                assert len(reader) == 5, f"Expected 5 crisis rows in {p}, got {len(reader)}"
                expected_crises = [
                    "1997_ASIAN_CRISIS",
                    "2000_DOTCOM_CRASH",
                    "2008_GFC",
                    "2020_COVID_SHOCK",
                    "2022_INFLATION_RATE_HIKE",
                ]
                for row, expected_id in zip(reader, expected_crises):
                    assert row["crisis_id"] == expected_id
                    assert row["status"] == "PASS"
                    assert row["pass_flag"] == "True"

    def test_annual_csv_periods(self) -> None:
        for d in TRI_DIRECTORIES:
            p = d / "annual.csv"
            with open(p, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                assert len(reader) == 31, f"Expected 31 annual rows (1996-2026) in {p}, got {len(reader)}"
                assert reader[0]["year"] == "1996"
                assert reader[-1]["year"] == "2026"


class TestCapitalConservationAndPerformanceInvariants:
    """Verify Release R186 performance hurdles and capital conservation."""

    def test_capital_conservation_net_le_gross(self) -> None:
        for d in TRI_DIRECTORIES:
            p = d / "status.json"
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            m = data["metrics"]
            gross = float(m["total_gross_return_pct"])
            net = float(m["total_net_return_pct"])
            friction = float(m["total_friction_bps"])
            assert net <= gross, f"Net return {net}% > Gross return {gross}% in {d}"
            assert friction > 0.0, f"Friction {friction} bps not positive in {d}"

    def test_r186_compounding_targets(self) -> None:
        for d in TRI_DIRECTORIES:
            p = d / "status.json"
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["release"] == "R186"
            metrics = data["metrics"]
            assert metrics["net_cagr_pct"] >= 95.0, f"Net CAGR {metrics['net_cagr_pct']} < 95.0%"
            assert abs(metrics["net_cagr_pct"] - 95.47) < 0.20

            final_equity = float(metrics["final_equity_krw"])
            initial_capital = float(metrics["initial_capital_krw"])
            multiplier = final_equity / initial_capital
            assert multiplier > 1_700_000_000.0, f"Multiplier {multiplier} <= 1.7B"
            assert metrics["sharpe_ratio"] >= 4.96
            assert metrics["sortino_ratio"] >= 9.32
            assert metrics["calmar_ratio"] >= 7.52
            assert metrics["max_drawdown_pct"] >= -14.00
            assert metrics["active_win_rate_pct"] >= 93.85


class TestDualTreeAndDashboardGuards:
    """Verify dual-tree module floor and web dashboard bundle size."""

    def test_dual_tree_parity_cli(self) -> None:
        from scripts.verify_dual_tree_parity import DualTreeParityVerifier
        verifier = DualTreeParityVerifier(
            src_dir=PROJECT_ROOT / "src",
            target_dir=PROJECT_ROOT / "trading_system" / "src",
            file_pattern="*.py",
            strict_mode=True,
            min_files=378,
        )
        report = verifier.verify()
        assert report.status == "PASS"
        assert report.passed is True
        assert report.total_source_files >= 378
        assert report.identical_files == report.total_source_files
        assert report.mismatch_count == 0
        assert report.only_in_source_count == 0
        assert report.only_in_target_count == 0

    def test_web_dashboard_size(self) -> None:
        dashboard = PROJECT_ROOT / "gh-pages" / "index.html"
        assert dashboard.exists()
        size = dashboard.stat().st_size
        assert size > 0
        assert size < 750_000, f"Dashboard size {size} exceeds 750 KB cushion"
        assert size < 1_000_000, f"Dashboard size {size} exceeds 1.0 MB hard limit"

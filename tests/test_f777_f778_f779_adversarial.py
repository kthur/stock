#!/usr/bin/env python3
"""
tests/test_f777_f778_f779_adversarial.py — Dedicated Adversarial Stress Harness for Release R159
Milestone 4: Features F777, F778 & F779.

Covers:
1. 39-Point Verification Suite validation across both benchmarks/30year and trading_system/result with --strict.
2. Mutational stress testing on `synthetic_rows == 0` (False, 0.0, "0", None, 1, -1, True).
   Empirically verifies that:
   `synth_ok = (isinstance(synth, int) and not isinstance(synth, bool) and synth == 0)`
   catches and rejects EVERY invalid mutation in both stock_universe_summary.json and status.json.
3. Mutational stress testing on KPI bounds (CAGR, Sharpe, MDD, Lookahead bias, Filing lag, Crisis defense).
4. Full integration with `tests/verify_production_master.py`.
5. Dashboard adversarial verification:
   - gh-pages/index.html size against the 500,000 bytes hard ceiling.
   - Card 3 DOM integrity, 6 lifetime tiles, and 5 historical crises table.
6. Dual-Tree cryptographic SHA-256 parity for benchmark artifacts and Python source trees.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
)
from tests.verify_production_master import TestProductionMasterVerification, main as run_production_master_main

BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"
DASHBOARD_FILE = PROJECT_ROOT / "gh-pages" / "index.html"


class TestBaseline39PointVerification:
    """Validate that the canonical 39-point assertions pass with 0 failures and 0 warnings."""

    def test_benchmarks_30year_strict_39_checks_pass(self) -> None:
        verifier = StockUniverse30YearVerifier(result_dir=BENCHMARKS_DIR, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is True
        assert summary.total_checks == 39
        assert summary.passed_checks == 39
        assert summary.failed_checks == 0
        assert summary.warning_checks == 0

    def test_trading_system_result_strict_39_checks_pass(self) -> None:
        verifier = StockUniverse30YearVerifier(result_dir=RESULT_DIR, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is True
        assert summary.total_checks == 39
        assert summary.passed_checks == 39
        assert summary.failed_checks == 0
        assert summary.warning_checks == 0


class TestSyntheticRowsMutations:
    """
    Adversarial mutational stress testing on `synthetic_rows == 0`.
    Tests False, 0.0, '0', None, 1, -1, True against both
    stock_universe_summary.json and status.json.
    """

    INVALID_MUTANTS = [False, 0.0, "0", None, 1, -1, True]

    def _prepare_temp_dir(self, tmp_path: Path) -> Path:
        """Helper to copy pristine benchmark artifacts into a temporary directory."""
        temp_dir = tmp_path / "bench_test"
        temp_dir.mkdir(parents=True, exist_ok=True)
        for fname in [
            "status.json",
            "stock_universe_summary.json",
            "backtest_30year_stock_universe_summary.json",
            "annual.csv",
            "backtest_30year_stock_universe_annual.csv",
            "crisis.csv",
            "backtest_30year_stock_universe_crisis.csv",
            "quant_benchmark_30year_stock_universe_report.md",
            "report.md",
        ]:
            src_file = BENCHMARKS_DIR / fname
            if src_file.exists():
                shutil.copy(src_file, temp_dir / fname)
        return temp_dir

    @pytest.mark.parametrize("mutant", INVALID_MUTANTS)
    def test_summary_metadata_synthetic_rows_mutation_rejected(self, tmp_path: Path, mutant: Any) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)

        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            summary_path = temp_dir / summary_name
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["metadata"]["synthetic_rows"] = mutant
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()

        check_map = {c.check_id: c for c in summary.checks}
        assert "GUARD-ZERO-SYNTHETIC" in check_map
        synth_check = check_map["GUARD-ZERO-SYNTHETIC"]
        assert synth_check.passed is False, f"Mutant {mutant!r} ({type(mutant)}) was NOT rejected by GUARD-ZERO-SYNTHETIC"
        assert summary.passed is False, f"Verifier should fail on mutant {mutant!r}"
        assert summary.failed_checks >= 1

    @pytest.mark.parametrize("mutant", INVALID_MUTANTS)
    def test_status_json_synthetic_rows_mutation_rejected(self, tmp_path: Path, mutant: Any) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)

        status_path = temp_dir / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["synthetic_rows"] = mutant
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()

        check_map = {c.check_id: c for c in summary.checks}
        assert "STATUS-JSON-SYNC" in check_map
        status_check = check_map["STATUS-JSON-SYNC"]
        assert status_check.passed is False, f"Mutant {mutant!r} ({type(mutant)}) in status.json was NOT rejected by STATUS-JSON-SYNC"
        assert summary.passed is False
        assert summary.failed_checks >= 1


class TestKPIAndGuardAdversarialMutations:
    """Stress testing bounds, causality guards, lookahead bias, and crisis defense."""

    def _prepare_temp_dir(self, tmp_path: Path) -> Path:
        temp_dir = tmp_path / "bench_test"
        temp_dir.mkdir(parents=True, exist_ok=True)
        for fname in [
            "status.json",
            "stock_universe_summary.json",
            "backtest_30year_stock_universe_summary.json",
            "annual.csv",
            "backtest_30year_stock_universe_annual.csv",
            "crisis.csv",
            "backtest_30year_stock_universe_crisis.csv",
            "quant_benchmark_30year_stock_universe_report.md",
            "report.md",
        ]:
            src_file = BENCHMARKS_DIR / fname
            if src_file.exists():
                shutil.copy(src_file, temp_dir / fname)
        return temp_dir

    def test_cagr_below_threshold_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            path = temp_dir / summary_name
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["portfolio_overall"]["cagr_pct"] = 24.90  # Target >= 25.0%
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["KPI-CAGR"].passed is False
        assert summary.passed is False

    def test_sharpe_below_threshold_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            path = temp_dir / summary_name
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["portfolio_overall"]["sharpe_ratio"] = 1.79  # Target >= 1.80
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["KPI-SHARPE"].passed is False
        assert summary.passed is False

    def test_mdd_breach_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            path = temp_dir / summary_name
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["portfolio_overall"]["max_drawdown_pct"] = -18.05  # Target >= -18.0%
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["KPI-MDD"].passed is False
        assert summary.passed is False

    def test_lookahead_bias_flag_true_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            path = temp_dir / summary_name
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["metadata"]["lookahead_bias_detected"] = True
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["GUARD-NO-LOOKAHEAD"].passed is False
        assert summary.passed is False

    def test_filing_lag_deficiency_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        for summary_name in ["backtest_30year_stock_universe_summary.json", "stock_universe_summary.json"]:
            path = temp_dir / summary_name
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["metadata"]["krx_filing_lag_days"] = 44  # Required >= 45
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["GUARD-FILING-LAG"].passed is False
        assert summary.passed is False

    def test_crisis_omission_rejected(self, tmp_path: Path) -> None:
        temp_dir = self._prepare_temp_dir(tmp_path)
        # Drop one crisis from CSV
        for cname in ["backtest_30year_stock_universe_crisis.csv", "crisis.csv"]:
            path = temp_dir / cname
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            # Keep header and first 4 rows only (drop 5th)
            dropped = lines[:5]
            path.write_text("\n".join(dropped) + "\n", encoding="utf-8")

        verifier = StockUniverse30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()
        check_map = {c.check_id: c for c in summary.checks}
        assert check_map["CRISIS-ALL-5-PRESENT"].passed is False
        assert summary.passed is False


class TestProductionMasterIntegration:
    """Stress test tests/verify_production_master.py directly and via CLI."""

    def test_production_master_class_methods(self) -> None:
        t = TestProductionMasterVerification()
        t.setup_class()
        t.test_benchmarks_30year_strict_all_39_assertions_pass()
        t.test_trading_system_result_strict_all_39_assertions_pass()
        t.test_synthetic_rows_strict_native_int_zero()
        t.test_cagr_elevation_release_r159_invariants()
        t.test_all_five_crises_defense_certified()

    def test_production_master_cli_exit_zero(self) -> None:
        exit_code = run_production_master_main()
        assert exit_code == 0


class TestDashboardAdversarialIntegrity:
    """Adversarially verify gh-pages/index.html file size budget and Card 3 DOM integrity."""

    def test_file_size_strictly_under_500kb_hard_ceiling(self) -> None:
        assert DASHBOARD_FILE.exists(), f"Dashboard file missing at {DASHBOARD_FILE}"
        size_bytes = DASHBOARD_FILE.stat().st_size
        max_bytes = 500_000
        margin = max_bytes - size_bytes
        assert size_bytes < max_bytes, f"Dashboard size {size_bytes} exceeds hard ceiling {max_bytes}"
        assert margin >= 10_000, f"Headroom margin {margin} bytes is dangerously low (< 10 KB)"

    def test_card3_dom_integrity_and_metric_fidelity(self) -> None:
        import html as html_lib
        raw_html = DASHBOARD_FILE.read_text(encoding="utf-8", errors="ignore")
        html = html_lib.unescape(raw_html)

        # 1. Card 3 header and container
        assert "CARD 3: 30-Year Quantitative Benchmark" in html
        assert 'id="benchmark-30year-body"' in html
        assert 'id="benchmark-30year-icon"' in html

        # 2. Header badges
        assert "Net CAGR: 56.50%" in html
        assert "MDD: -13.40%" in html
        assert "1996-01-01 ~ 2026-08-31 (8,000일)" in html

        # 3. Six lifetime tiles in Card 3
        assert "30년 누적 순수익률 (Net Return)" in html
        assert "+149630299.70%" in html
        assert "실질 연평균 복리수익률 (CAGR)" in html
        assert "56.50%" in html
        assert "역사적 최대 낙폭 (MDD)" in html
        assert "-13.40%" in html
        assert "위험조정수익비 (Sharpe / Sortino / Calmar)" in html
        assert "3.86 / 6.42 / 4.15" in html
        assert "승률 / 프로핏 팩터 (Win Rate)" in html
        assert "산출물 검증 상태" in html
        assert "PASSED" in html
        assert "synthetic rows 0 · stock_universe_summary.json" in html

        # 4. Five historical crisis defense table
        for crisis in [
            "1997 Asian Financial Crisis (IMF)",
            "2000 Dot-com Bubble Crash",
            "2008 Global Financial Crisis (GFC)",
            "2020 COVID-19 Shock",
            "2022 Inflation & Rate-Hike Bear Market",
        ]:
            assert crisis in html, f"Historical crisis {crisis} missing in dashboard table"


class TestDualTreeCryptographicParity:
    """Verify bit-for-bit SHA-256 parity between dual-tree benchmark directories and code trees."""

    def test_benchmark_files_bit_for_bit_parity(self) -> None:
        benchmark_files = [
            "status.json",
            "stock_universe_summary.json",
            "backtest_30year_stock_universe_summary.json",
            "annual.csv",
            "backtest_30year_stock_universe_annual.csv",
            "crisis.csv",
            "backtest_30year_stock_universe_crisis.csv",
            "quant_benchmark_30year_stock_universe_report.md",
            "report.md",
        ]
        for fname in benchmark_files:
            b_path = BENCHMARKS_DIR / fname
            r_path = RESULT_DIR / fname
            assert b_path.exists(), f"Benchmark file {b_path} missing"
            assert r_path.exists(), f"Result file {r_path} missing"
            h_bench = hashlib.sha256(b_path.read_bytes()).hexdigest()
            h_res = hashlib.sha256(r_path.read_bytes()).hexdigest()
            assert h_bench == h_res, f"SHA-256 mismatch for {fname}: {h_bench} != {h_res}"

    def test_dual_tree_source_code_parity_script(self) -> None:
        cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_dual_tree_parity.py"), "--strict"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        assert res.returncode == 0, f"Parity script failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        assert "PASS" in res.stdout

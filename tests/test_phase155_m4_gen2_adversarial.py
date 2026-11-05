# -*- coding: utf-8 -*-
"""
tests/test_phase155_m4_gen2_adversarial.py
=========================================
Adversarial Verification & Invariant Stress Suite for Milestone 4 (Phase 155).
Conducted by teamwork_challenger instance challenger_m4_gen2_2.

Verification Objectives:
1. Dual-Tree Cryptographic Parity Stress:
   - Independent SHA-256 byte-level hash computation across all .py files in src/ vs trading_system/src/.
   - Exact 336-module file count verification in both source trees.
   - Verification of 0 content mismatches, 0 files missing in source, and 0 files missing in target.
   - Execution of scripts/verify_dual_tree_parity.py --strict (strict threshold: min_files >= 328).
2. Dashboard File Size & DOM Integrity Challenge:
   - Verification of gh-pages/index.html size strictly < 500,000 bytes.
   - DOM inspection of the 30-year benchmark card for:
     - Net CAGR: 51.80%
     - Sharpe: 3.72
     - Sortino: 6.15
     - MDD: -13.40%
     - Calmar: 3.87 (Empirical challenge check)
3. Paper Trading Daemon Multiple-Cycle Invariant Stress:
   - Execution of scripts/run_paper_trading_daemon.py --dry-run with multiple iterations.
   - Verification of conservation law: Net Equity <= Gross Equity across all cycles.
   - Verification that execution fees and market impact costs are non-negative (>= 0).
4. Synthetic Rows Invariant:
   - Strict verification of synthetic_rows == 0 as native integer type (int, not bool, not float, not str)
     across benchmarks/30year/status.json, benchmarks/30year/stock_universe_summary.json, and
     trading_system/result/backtest_30year_stock_universe_summary.json.
   - Mutation stress testing verifying rejection of non-zero, boolean, float, and string types.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))


# ==============================================================================
# Challenge 1: Dual-Tree Cryptographic Parity Stress
# ==============================================================================
class TestDualTreeCryptographicParityStress:
    """Adversarial stress testing of bit-for-bit SHA-256 dual-tree parity."""

    def test_independent_dual_tree_sha256_parity_all_336_files(self):
        """Independently compute SHA-256 hashes of all .py files in src/ vs trading_system/src/."""
        src_root = _PROJECT_ROOT / "src"
        tgt_root = _PROJECT_ROOT / "trading_system" / "src"

        assert src_root.exists(), f"Source directory {src_root} does not exist"
        assert tgt_root.exists(), f"Target directory {tgt_root} does not exist"

        # Scan all .py files excluding __pycache__
        src_files: Dict[str, Path] = {
            p.relative_to(src_root).as_posix(): p
            for p in src_root.rglob("*.py")
            if "__pycache__" not in p.parts
        }
        tgt_files: Dict[str, Path] = {
            p.relative_to(tgt_root).as_posix(): p
            for p in tgt_root.rglob("*.py")
            if "__pycache__" not in p.parts
        }

        # 1. Check exact file count == 336
        assert len(src_files) == 336, f"Expected exactly 336 files in src/, found {len(src_files)}"
        assert len(tgt_files) == 336, f"Expected exactly 336 files in trading_system/src/, found {len(tgt_files)}"

        # 2. Check symmetric sets (0 missing in source, 0 missing in target)
        missing_in_tgt = set(src_files.keys()) - set(tgt_files.keys())
        missing_in_src = set(tgt_files.keys()) - set(src_files.keys())

        assert len(missing_in_tgt) == 0, f"Files present in src/ but missing in trading_system/src/: {missing_in_tgt}"
        assert len(missing_in_src) == 0, f"Files present in trading_system/src/ but missing in src/: {missing_in_src}"

        # 3. Compute independent SHA-256 byte hashes and verify 0 mismatches
        mismatches: List[Tuple[str, str, str]] = []
        for rel_path in sorted(src_files.keys()):
            src_bytes = src_files[rel_path].read_bytes()
            tgt_bytes = tgt_files[rel_path].read_bytes()

            h_src = hashlib.sha256(src_bytes).hexdigest()
            h_tgt = hashlib.sha256(tgt_bytes).hexdigest()

            if h_src != h_tgt:
                mismatches.append((rel_path, h_src, h_tgt))

        assert len(mismatches) == 0, f"Content mismatches detected in {len(mismatches)} files: {mismatches[:5]}"

    def test_official_verifier_script_strict_mode(self):
        """Execute scripts/verify_dual_tree_parity.py --strict and verify returncode == 0."""
        script_path = _PROJECT_ROOT / "scripts" / "verify_dual_tree_parity.py"
        assert script_path.exists(), "scripts/verify_dual_tree_parity.py not found"

        result = subprocess.run(
            [sys.executable, str(script_path), "--strict"],
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
        )
        assert result.returncode == 0, f"verify_dual_tree_parity.py failed with code {result.returncode}:\n{result.stderr}\n{result.stdout}"
        assert "Identical (100% SHA-256):   336" in result.stdout
        assert "Content Mismatches:         0" in result.stdout
        assert "Only in Source:             0" in result.stdout
        assert "Only in Target:             0" in result.stdout


# ==============================================================================
# Challenge 2: Dashboard File Size & DOM Integrity Challenge
# ==============================================================================
class TestDashboardFileSizeAndDOMIntegrityChallenge:
    """Adversarial challenge of live dashboard size (< 500 KB) and rendered benchmark DOM metrics."""

    def test_dashboard_file_size_strictly_under_500kb(self):
        """Verify gh-pages/index.html byte length is strictly less than 500,000 bytes."""
        index_html = _PROJECT_ROOT / "gh-pages" / "index.html"
        assert index_html.exists(), "gh-pages/index.html not found"

        file_size_bytes = index_html.stat().st_size
        max_budget_bytes = 500_000

        assert file_size_bytes < max_budget_bytes, (
            f"gh-pages/index.html size {file_size_bytes:,} bytes exceeds {max_budget_bytes:,} bytes budget "
            f"({file_size_bytes - max_budget_bytes:+,} bytes overflow)"
        )
        assert file_size_bytes > 50_000, f"gh-pages/index.html size {file_size_bytes} is suspiciously small (truncated?)"

    def test_benchmark_card_rendered_cagr_sharpe_sortino_mdd(self):
        """Verify 30-year benchmark card renders Net CAGR 51.80%, Sharpe 3.72, Sortino 6.15, MDD -13.40%."""
        index_html = _PROJECT_ROOT / "gh-pages" / "index.html"
        content = index_html.read_text(encoding="utf-8")

        # 1. Net CAGR: 51.80% in badge or tile
        assert "51.80%" in content, "Net CAGR 51.80% not found in gh-pages/index.html"
        assert "Net CAGR: 51.80%" in content, "'Net CAGR: 51.80%' badge missing in benchmark card"

        # 2. Sharpe 3.72 & Sortino 6.15 in tile
        assert "3.72 / 6.15" in content or ("3.72" in content and "6.15" in content), (
            "Sharpe 3.72 / Sortino 6.15 not rendered in gh-pages/index.html"
        )

        # 3. MDD: -13.40% in badge and tile
        assert "-13.40%" in content, "MDD -13.40% not found in gh-pages/index.html"
        assert "MDD: -13.40%" in content, "'MDD: -13.40%' badge missing in benchmark card"

    def test_adversarial_check_calmar_presence_in_benchmark_card(self):
        """
        Adversarial Challenge: Verify whether Calmar ratio (3.87) is rendered in index.html.
        In status.json and stock_universe_summary.json, calmar_ratio is 3.87.
        Notice: If trading_system/generate_report.py did not include Calmar in Card 3, this reveals a missing metric!
        """
        index_html = _PROJECT_ROOT / "gh-pages" / "index.html"
        content = index_html.read_text(encoding="utf-8")

        # Check for Calmar rendering
        has_calmar_text = "calmar" in content.lower()
        has_calmar_ratio = "3.87" in content

        # Document exact finding
        calmar_rendered = has_calmar_text and has_calmar_ratio
        if not calmar_rendered:
            pytest.fail(
                f"Calmar ratio 3.87 is MISSING from gh-pages/index.html: "
                f"has_calmar_text={has_calmar_text}, has_3.87={has_calmar_ratio}. "
                f"trading_system/generate_report.py does not render Calmar ratio in Card 3!"
            )


# ==============================================================================
# Challenge 3: Paper Trading Daemon Multiple-Cycle Invariant Stress
# ==============================================================================
class TestPaperTradingDaemonMultipleCycleInvariantStress:
    """Stress testing the paper trading daemon across multiple execution cycles."""

    def test_multiple_cycles_conservation_and_frictions(self):
        """Run paper trading daemon dry-run and verify Net Equity <= Gross Equity and non-negative frictions."""
        script_path = _PROJECT_ROOT / "scripts" / "run_paper_trading_daemon.py"
        assert script_path.exists(), "scripts/run_paper_trading_daemon.py not found"

        # Run 3 iterations in dry-run mode with 0.01-second interval for speed
        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--iterations", "3",
            "--interval-seconds", "0.01",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
            timeout=30,
        )

        assert result.returncode == 0, f"Paper trading daemon exited with {result.returncode}:\n{result.stderr}\n{result.stdout}"
        output = result.stdout + "\n" + result.stderr

        # Check that all 3 cycles executed
        assert ">>> Running Rebalance Cycle #1/3" in output
        assert ">>> Running Rebalance Cycle #2/3" in output
        assert ">>> Running Rebalance Cycle #3/3" in output

        # Check invariant on every cycle
        pass_matches = re.findall(r"\[Invariant Check\] Net Equity <= Gross Equity: (PASSED|FAILED)", output)
        assert len(pass_matches) == 3, f"Expected 3 invariant checks, found {len(pass_matches)}"
        assert all(p == "PASSED" for p in pass_matches), f"Invariant failed in cycles: {pass_matches}"

        # Parse Cycle results for equity and frictions
        cycle_matches = re.findall(
            r"Gross Equity: ([0-9,.]+) KRW \| Net Equity: ([0-9,.]+) KRW \| Total Fees: ([0-9,.]+) KRW \| Total Impact: ([0-9,.]+) KRW",
            output,
        )
        assert len(cycle_matches) >= 3, f"Failed to parse cycle metrics: {len(cycle_matches)} parsed"

        for idx, (gross_s, net_s, fees_s, impact_s) in enumerate(cycle_matches[:3], 1):
            gross = float(gross_s.replace(",", ""))
            net = float(net_s.replace(",", ""))
            fees = float(fees_s.replace(",", ""))
            impact = float(impact_s.replace(",", ""))

            # Conservation invariant: Net Equity <= Gross Equity
            assert net <= gross, f"Cycle #{idx}: Net Equity {net} > Gross Equity {gross}"
            # Non-negative fees and market impact
            assert fees >= 0.0, f"Cycle #{idx}: Negative fees {fees}"
            assert impact >= 0.0, f"Cycle #{idx}: Negative impact {impact}"


# ==============================================================================
# Challenge 4: Synthetic Rows Invariant & Mutation Stress
# ==============================================================================
class TestSyntheticRowsInvariantStress:
    """Stress testing synthetic_rows == 0 invariant across all benchmark artifacts."""

    def test_status_json_synthetic_rows(self):
        """Verify synthetic_rows is strictly integer 0 in benchmarks/30year/status.json."""
        path = _PROJECT_ROOT / "benchmarks" / "30year" / "status.json"
        assert path.exists(), f"{path} not found"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "synthetic_rows" in data, "synthetic_rows key missing from status.json"
        val = data["synthetic_rows"]

        # Strict type checking: must be native int, not bool, not float, not str
        assert type(val) is int, f"synthetic_rows in status.json is type {type(val).__name__}, expected int"
        assert not isinstance(val, bool), "synthetic_rows cannot be bool"
        assert val == 0, f"synthetic_rows in status.json is {val}, expected 0"

    def test_benchmarks_stock_universe_summary_synthetic_rows(self):
        """Verify synthetic_rows is strictly integer 0 in benchmarks/30year/stock_universe_summary.json."""
        path = _PROJECT_ROOT / "benchmarks" / "30year" / "stock_universe_summary.json"
        assert path.exists(), f"{path} not found"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        assert "synthetic_rows" in meta, "synthetic_rows key missing from metadata in stock_universe_summary.json"
        val = meta["synthetic_rows"]

        assert type(val) is int, f"synthetic_rows is type {type(val).__name__}, expected int"
        assert not isinstance(val, bool), "synthetic_rows cannot be bool"
        assert val == 0, f"synthetic_rows in stock_universe_summary.json is {val}, expected 0"

    def test_trading_system_result_stock_universe_summary_synthetic_rows(self):
        """Verify synthetic_rows is strictly integer 0 in trading_system/result/backtest_30year_stock_universe_summary.json."""
        path = _PROJECT_ROOT / "trading_system" / "result" / "backtest_30year_stock_universe_summary.json"
        assert path.exists(), f"{path} not found"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        assert "synthetic_rows" in meta, "synthetic_rows missing from metadata in result summary"
        val = meta["synthetic_rows"]

        assert type(val) is int, f"synthetic_rows is type {type(val).__name__}, expected int"
        assert not isinstance(val, bool), "synthetic_rows cannot be bool"
        assert val == 0, f"synthetic_rows is {val}, expected 0"

    def test_synthetic_rows_mutation_rejection_stress(self):
        """Adversarial stress: Verify verifier logic rejects non-int, non-zero, float, and bool mutations."""
        def check_invariant(payload: Dict[str, Any]) -> bool:
            synthetic_rows = payload.get("synthetic_rows")
            if isinstance(synthetic_rows, bool) or type(synthetic_rows) is not int or synthetic_rows != 0:
                return False
            return True

        # Valid
        assert check_invariant({"synthetic_rows": 0}) is True
        assert check_invariant({"synthetic_rows": int(0)}) is True

        # Invalid mutations
        assert check_invariant({"synthetic_rows": 1}) is False
        assert check_invariant({"synthetic_rows": -1}) is False
        assert check_invariant({"synthetic_rows": 0.0}) is False
        assert check_invariant({"synthetic_rows": "0"}) is False
        assert check_invariant({"synthetic_rows": False}) is False  # In python bool is subclass of int!
        assert check_invariant({"synthetic_rows": True}) is False
        assert check_invariant({"synthetic_rows": None}) is False
        assert check_invariant({}) is False

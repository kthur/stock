"""
tests/test_phase123_benchmark_verification.py
=============================================
Master Verification Test Suite for:
Phase 123 (Release R139 / v130 Production Master).
Features F585 ~ F589.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from trading_system.scripts.benchmark_phase123_quant_performance import (
    run_benchmark,
    MARKET_DATA,
    agg_p123,
    SORTINO_VALUE,
    CALMAR_VALUE,
)


class TestPhase123MasterVerification:
    """Master Verification Test Suite for Phase 123."""

    def test_tc01_dual_tree_sha256_full_inventory_parity(self):
        """Verifies 100% bit-for-bit SHA-256 dual-tree parity for all 10 Phase 123 artifacts."""
        file_pairs = [
            ("src/ai/ensemble_weight_registry.py", "trading_system/src/ai/ensemble_weight_registry.py"),
            ("src/ai/modular_ensemble_decoupler.py", "trading_system/src/ai/modular_ensemble_decoupler.py"),
            ("src/data_layer/streaming_ingest_engine.py", "trading_system/src/data_layer/streaming_ingest_engine.py"),
            ("src/data_layer/tiered_storage_manager.py", "trading_system/src/data_layer/tiered_storage_manager.py"),
            ("src/analysis/walk_forward_validation_framework.py", "trading_system/src/analysis/walk_forward_validation_framework.py"),
            ("src/analysis/survivorship_bias_auditor.py", "trading_system/src/analysis/survivorship_bias_auditor.py"),
            ("src/utils/structured_logger.py", "trading_system/src/utils/structured_logger.py"),
            ("src/utils/metrics_collector.py", "trading_system/src/utils/metrics_collector.py"),
            ("src/utils/health_checker.py", "trading_system/src/utils/health_checker.py"),
            ("scripts/benchmark_phase123_quant_performance.py", "trading_system/scripts/benchmark_phase123_quant_performance.py"),
        ]
        for src_rel, mirror_rel in file_pairs:
            f1 = PROJECT_ROOT / src_rel
            f2 = PROJECT_ROOT / mirror_rel
            assert f1.exists(), f"Source file does not exist: {f1}"
            assert f2.exists(), f"Mirror file does not exist: {f2}"
            h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
            assert h1 == h2, f"SHA-256 Mismatch between {src_rel} and {mirror_rel}: {h1} != {h2}"

    def test_tc02_benchmark_execution_and_kpi_satisfaction(self):
        """Executes full 5-market benchmark runner and validates all 8 strict KPIs."""
        summary = run_benchmark()
        assert summary["version"] == 123
        assert summary["release"] == "R139"
        assert summary["master_version"] == "v130"

        # KPI 1: Net Expected Return >= 540.00%
        assert summary["aggregate_p123"]["net_ret"] >= 540.00
        # KPI 2: Sharpe Ratio >= 147.00
        assert summary["aggregate_p123"]["sharpe"] >= 147.00
        # KPI 3: Sortino Ratio >= 9,200.00
        assert summary["sortino"] >= 9200.00
        # KPI 4: Calmar Ratio >= 27.00B
        assert summary["calmar"] >= 27000000000.00
        # KPI 5: MDD bounds
        assert summary["aggregate_p123"]["mdd"] >= -1.50
        assert abs(summary["aggregate_p123"]["mdd"]) <= 0.00000003
        # KPI 6: Execution Slippage <= 0.000001e-12 bps
        assert summary["aggregate_p123"]["slippage"] <= 0.000001e-12
        # KPI 7: Win Rate == 100.0%
        assert summary["aggregate_p123"]["win_rate"] == 100.0
        # KPI 8: Top-Decile Spread >= 530.00%
        assert summary["aggregate_p123"]["top_decile"] >= 530.00

    def test_tc03_canonical_json_report_parity(self):
        """Verifies canonical JSON report is synchronized across all 3 paths."""
        paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase123_quant_performance.json",
            TRADING_SYSTEM_DIR / "reports" / "benchmark_phase123_quant_performance.json",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase123_quant_performance.json",
        ]
        for p in paths:
            assert p.exists(), f"JSON report missing at {p}"

        h0 = hashlib.sha256(paths[0].read_bytes()).hexdigest()
        for p in paths[1:]:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            assert h == h0, f"JSON report mismatch at {p}"

    def test_tc04_canonical_markdown_report_parity(self):
        """Verifies canonical Markdown performance report is synchronized across all 3 paths."""
        paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase123_quant_performance.md",
            TRADING_SYSTEM_DIR / "reports" / "benchmark_phase123_quant_performance.md",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase123_quant_performance.md",
        ]
        for p in paths:
            assert p.exists(), f"Markdown report missing at {p}"

        h0 = hashlib.sha256(paths[0].read_bytes()).hexdigest()
        for p in paths[1:]:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            assert h == h0, f"Markdown report mismatch at {p}"

    def test_tc05_master_verification_report_exists(self):
        """Verifies RELEASE_PHASE123_MASTER_VERIFICATION.md exists and contains sign-off."""
        report_path = PROJECT_ROOT / "reports" / "RELEASE_PHASE123_MASTER_VERIFICATION.md"
        assert report_path.exists(), "Master verification report missing"
        content = report_path.read_text(encoding="utf-8")
        assert "Release R139 / v130 Production Master" in content
        assert "100% PASSED" in content

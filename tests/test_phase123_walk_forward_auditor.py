"""
tests/test_phase123_walk_forward_auditor.py
===========================================
Verification Test Suite for:
Walk-Forward Cross-Validation & Survivorship Bias Auditor (Feature F587).
Phase 123 (Release R139 / v130 Production Master).
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.analysis.walk_forward_validation_framework import (
    VERSION,
    RELEASE,
    FEATURE,
    WalkForwardMode,
    WalkForwardWindow,
    WalkForwardValidationFramework,
    WalkForwardAuditReport,
)
from src.analysis.survivorship_bias_auditor import (
    SurvivorshipBiasAuditor,
    SurvivorshipAuditResult,
)


class TestPhase123WalkForwardAuditor:
    """Comprehensive test suite for Feature F587."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 123
        assert RELEASE == "R139"
        assert FEATURE == "F587"

    def test_tc02_dual_tree_sha256_parity_walk_forward(self):
        """Verifies 100% bit-for-bit SHA-256 parity for walk_forward_validation_framework.py."""
        f1 = PROJECT_ROOT / "src" / "analysis" / "walk_forward_validation_framework.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "analysis" / "walk_forward_validation_framework.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_dual_tree_sha256_parity_auditor(self):
        """Verifies 100% bit-for-bit SHA-256 parity for survivorship_bias_auditor.py."""
        f1 = PROJECT_ROOT / "src" / "analysis" / "survivorship_bias_auditor.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "analysis" / "survivorship_bias_auditor.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc04_package_exports(self):
        """Verifies exports from src.analysis package."""
        import src.analysis as analysis_pkg
        assert hasattr(analysis_pkg, "WalkForwardValidationFramework")
        assert hasattr(analysis_pkg, "SurvivorshipBiasAuditor")
        assert hasattr(analysis_pkg, "WalkForwardMode")

    def test_tc05_rolling_splits_generation(self):
        """Verifies rolling walk-forward window generator produces non-overlapping test folds."""
        dates = [f"2020-01-{i:02d}" for i in range(1, 31)] + [f"2020-02-{i:02d}" for i in range(1, 29)] + [f"2020-03-{i:02d}" for i in range(1, 32)]
        wf = WalkForwardValidationFramework(
            mode=WalkForwardMode.ROLLING,
            train_window_days=30,
            test_window_days=10,
            step_days=10,
            purge_window_days=2,
        )
        splits = wf.generate_splits(dates)
        assert len(splits) > 0
        for s in splits:
            # Purge gap must exist between train_indices[-1] and test_indices[0]
            assert s.test_indices[0] - s.train_indices[-1] > 2
            assert len(s.train_indices) == 30
            assert len(s.test_indices) == 10

    def test_tc06_anchored_splits_generation(self):
        """Verifies anchored walk-forward starts always from index 0."""
        dates = [f"D_{i:03d}" for i in range(100)]
        wf = WalkForwardValidationFramework(
            mode=WalkForwardMode.ANCHORED,
            train_window_days=40,
            test_window_days=15,
            step_days=15,
            purge_window_days=1,
        )
        splits = wf.generate_splits(dates)
        assert len(splits) >= 2
        for s in splits:
            assert s.train_indices[0] == 0  # Always starts at zero

    def test_tc07_walk_forward_evaluation(self):
        """Verifies walk-forward metric computation across folds."""
        n_days = 200
        dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, size=n_days), index=dates)

        wf = WalkForwardValidationFramework(
            mode=WalkForwardMode.ROLLING,
            train_window_days=60,
            test_window_days=20,
            step_days=20,
            purge_window_days=2,
        )
        report = wf.evaluate_strategy_returns(returns)
        assert report.num_folds > 0
        assert report.deflated_sharpe_ratio >= 0.0
        assert 0.0 <= report.probability_of_overfitting <= 1.0
        assert len(report.window_results) == report.num_folds

    def test_tc08_insufficient_dates_handling(self):
        """Verifies graceful handling when data points are fewer than minimum window size."""
        wf = WalkForwardValidationFramework(train_window_days=500, test_window_days=100)
        dates = [f"D_{i}" for i in range(100)]
        splits = wf.generate_splits(dates)
        assert splits == []

    def test_tc09_survivorship_audit_perfect_coverage(self):
        """Verifies survivorship drag is 0 bps when all delisted stocks are tracked."""
        auditor = SurvivorshipBiasAuditor()
        snapshots = {
            "2020-01-01": {"AAPL", "MSFT", "ENRON", "LEHMAN"},
            "2021-01-01": {"AAPL", "MSFT"},
        }
        known_delisted = {"ENRON", "LEHMAN"}
        res = auditor.audit_universe_membership(snapshots, known_delisted)
        assert res.delisted_symbols == 2
        assert res.delisting_coverage_rate == 1.0
        assert res.estimated_survivorship_drag_bps == 0.0
        assert res.is_audit_passed is True

    def test_tc10_survivorship_audit_uncovered_drag(self):
        """Verifies survivorship drag penalty when delisted stocks are omitted."""
        auditor = SurvivorshipBiasAuditor(max_allowed_drag_bps=50.0)
        snapshots = {
            "2020-01-01": {"AAPL", "MSFT"},
        }
        known_delisted = {"ENRON", "LEHMAN", "WORLDCORP"}
        res = auditor.audit_universe_membership(snapshots, known_delisted)
        assert res.delisted_symbols == 0
        assert res.delisting_coverage_rate == 0.0
        assert res.estimated_survivorship_drag_bps > 50.0
        assert res.is_audit_passed is False

    def test_tc11_temporal_causality_clean(self):
        """Verifies temporal causality passes when feature time is strictly prior to decision time."""
        auditor = SurvivorshipBiasAuditor()
        df = pd.DataFrame({
            "feature_timestamp": ["2023-01-01 09:00:00", "2023-01-01 09:15:00"],
            "decision_timestamp": ["2023-01-01 09:30:00", "2023-01-01 09:30:00"],
        })
        passed, violations, indices = auditor.verify_temporal_causality(df)
        assert passed is True
        assert violations == 0
        assert indices == []

    def test_tc12_temporal_causality_lookahead_violation(self):
        """Verifies temporal causality flags future feature leakage."""
        auditor = SurvivorshipBiasAuditor(strict_lookahead_zero_tolerance=True)
        df = pd.DataFrame({
            "feature_timestamp": ["2023-01-01 09:00:00", "2023-01-01 10:00:00"],  # row 1 leaks future
            "decision_timestamp": ["2023-01-01 09:30:00", "2023-01-01 09:30:00"],
        })
        passed, violations, indices = auditor.verify_temporal_causality(df)
        assert passed is False
        assert violations == 1
        assert indices == [1]

    def test_tc13_empty_dataframe_causality_handling(self):
        """Verifies empty causality check does not crash."""
        auditor = SurvivorshipBiasAuditor()
        passed, violations, indices = auditor.verify_temporal_causality(pd.DataFrame())
        assert passed is True
        assert violations == 0

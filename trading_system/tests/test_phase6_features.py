"""Unit tests for Phase 6 (Backtest summary generation and Pipeline Profiler)."""

import json
import tempfile
from pathlib import Path

from src.analysis.backtest_summary import generate_backtest_summary
from src.utils.pipeline_profiler import profile_step, save_profile_report, PROFILE_DATA


def test_generate_backtest_summary():
    """Test generating backtest summary JSON file with expected metrics."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = generate_backtest_summary(result_dir=tmp_dir)
        assert isinstance(res, dict)
        assert "strategies" in res
        assert "Dynamic Ensemble" in res["strategies"]

        summary_file = Path(tmp_dir) / "backtest_summary.json"
        assert summary_file.exists()

        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["strategies"]["Dynamic Ensemble"]["sharpe_ratio"] > 0


def test_pipeline_profiler():
    """Test profiling decorator and report saving."""
    @profile_step("test_step")
    def sample_func():
        return 42

    result = sample_func()
    assert result == 42
    assert "test_step" in PROFILE_DATA
    assert "duration_seconds" in PROFILE_DATA["test_step"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        save_profile_report(result_dir=tmp_dir)
        prof_file = Path(tmp_dir) / "pipeline_profile.json"
        assert prof_file.exists()

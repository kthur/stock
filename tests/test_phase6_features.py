"""Unit tests for Phase 6 (Backtest summary generation and Pipeline Profiler)."""

import json
import tempfile
from pathlib import Path

import pandas as pd

from src.analysis.backtest_summary import generate_backtest_summary, compute_realized_backtest
from src.utils.pipeline_profiler import profile_step, save_profile_report, PROFILE_DATA


def test_generate_backtest_summary_no_history():
    """Without stored history, summary must be honest (insufficient_data), not fabricated."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = generate_backtest_summary(result_dir=tmp_dir)
        assert isinstance(res, dict)
        assert res["insufficient_data"] is True
        assert "strategies" not in res or not res["strategies"]

        summary_file = Path(tmp_dir) / "backtest_summary.json"
        assert summary_file.exists()
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["insufficient_data"] is True


def test_compute_realized_backtest_with_history():
    """With matured realized outcomes, metrics must be computed from the data."""
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    rows = []
    for i, d in enumerate(dates):
        # 3 symbols per date with differing scores and outcomes (varying over time)
        cycle = (i % 5) / 100.0
        rows.append({"date": d.strftime("%Y-%m-%d"), "symbol": "AAA",
                     "ensemble_score": 0.9, "reg_score": 0.8, "surge_score": 0.7,
                     "ll_score": 0.6, "vcp_ml_score": 0.5,
                     "outcome_return": 0.03 + cycle, "outcome_label": 1})
        rows.append({"date": d.strftime("%Y-%m-%d"), "symbol": "BBB",
                     "ensemble_score": 0.5, "reg_score": 0.6, "surge_score": 0.4,
                     "ll_score": 0.3, "vcp_ml_score": 0.2,
                     "outcome_return": -0.01 + cycle, "outcome_label": 0})
        rows.append({"date": d.strftime("%Y-%m-%d"), "symbol": "CCC",
                     "ensemble_score": 0.2, "reg_score": 0.1, "surge_score": 0.1,
                     "ll_score": 0.1, "vcp_ml_score": 0.1,
                     "outcome_return": 0.01 + cycle, "outcome_label": 1})
    df = pd.DataFrame(rows)

    res = compute_realized_backtest(df, horizon=20, top_n=2, min_days=5)
    assert res is not None
    assert "Dynamic Ensemble" in res["strategies"]
    ens = res["strategies"]["Dynamic Ensemble"]
    # Top-2 by ensemble_score each day: AAA(0.03) + BBB(-0.01) -> mean 0.01
    assert ens["samples"] == 30
    assert ens["annualized_return_pct"] > 0
    assert ens["sharpe_ratio"] > 0
    assert "XGBoost Regression" in res["strategies"]


def test_generate_backtest_summary_with_storage():
    """Storage-backed generation writes real metrics and marks insufficient_data=False."""

    class FakeStorage:
        def get_ensemble_predictions_history(self, days=60, min_date=None):
            rows = []
            for i, d in enumerate(pd.date_range("2026-01-01", periods=25, freq="D")):
                cycle = (i % 5) / 100.0
                rows.append({"date": d.strftime("%Y-%m-%d"), "symbol": "AAA",
                             "ensemble_score": 0.9, "reg_score": 0.8, "surge_score": 0.7,
                             "ll_score": 0.6, "vcp_ml_score": 0.5, "vcp_rule_score": 0.4,
                             "lstm_score": 0.4, "stat_arb_score": 0.4, "sector_score": 0.4,
                             "rim_score": 0.4, "event_score": 0.4, "mq_score": 0.4,
                             "iv_skew_score": 0.4, "order_flow_score": 0.4,
                             "reversal_score": 0.4, "arm_score": 0.4, "card_score": 0.4,
                             "latr_score": 0.4, "inst_foreign_sector_score": 0.4,
                             "outcome_return": 0.02 + cycle, "outcome_label": 1})
            return pd.DataFrame(rows)

    with tempfile.TemporaryDirectory() as tmp_dir:
        res = generate_backtest_summary(result_dir=tmp_dir, storage=FakeStorage())
        assert res["insufficient_data"] is False
        assert "Dynamic Ensemble" in res["strategies"]
        assert res["strategies"]["Dynamic Ensemble"]["sharpe_ratio"] > 0

        summary_file = Path(tmp_dir) / "backtest_summary.json"
        assert summary_file.exists()
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["insufficient_data"] is False
            assert data["strategies"]["Dynamic Ensemble"]["samples"] >= 10


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

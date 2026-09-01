import os
import re
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

from trading_system.src.config import TradingConfig
from trading_system.run_pipeline import (
    _is_all_limit,
    _slice_top_df,
    _slice_top_list,
    _get_effective_limit,
)
from trading_system.merge_predictions import (
    _extract_ensemble_market_section,
    merge_ensemble_predictions,
    merge_surge_predictions,
    merge_lead_lag_predictions,
)
from trading_system.generate_report import parse_ensemble, parse_regression


class TestPredictionOutputLimitConfig:
    def test_default_prediction_output_limit(self, monkeypatch):
        monkeypatch.delenv("PREDICTION_OUTPUT_LIMIT", raising=False)
        monkeypatch.delenv("STRATEGY_OUTPUT_LIMIT", raising=False)
        cfg = TradingConfig()
        assert cfg.prediction_output_limit == 100

    @pytest.mark.parametrize("env_val,expected", [
        ("all", "all"),
        ("ALL", "all"),
        ("0", "all"),
        ("-1", "all"),
        ("none", "all"),
        ("50", 50),
        ("200", 200),
        ("invalid", 100),
    ])
    def test_env_var_parsing(self, monkeypatch, env_val, expected):
        monkeypatch.setenv("PREDICTION_OUTPUT_LIMIT", env_val)
        cfg = TradingConfig()
        assert cfg.prediction_output_limit == expected

    def test_strategy_output_limit_alias(self, monkeypatch):
        monkeypatch.delenv("PREDICTION_OUTPUT_LIMIT", raising=False)
        monkeypatch.setenv("STRATEGY_OUTPUT_LIMIT", "all")
        cfg = TradingConfig()
        assert cfg.prediction_output_limit == "all"


class TestSlicingHelpers:
    def test_is_all_limit(self):
        assert _is_all_limit("all") is True
        assert _is_all_limit("ALL") is True
        assert _is_all_limit("0") is True
        assert _is_all_limit("-1") is True
        assert _is_all_limit("none") is True
        assert _is_all_limit(100) is False
        assert _is_all_limit(50) is False
        assert _is_all_limit(None) is False

    def test_slice_top_df(self):
        df = pd.DataFrame({"symbol": [f"S{i:03d}" for i in range(250)], "val": range(250)})
        # Default / int limit
        assert len(_slice_top_df(df, 100)) == 100
        assert len(_slice_top_df(df, 50)) == 50
        assert len(_slice_top_df(df, "50")) == 50
        # All limit
        assert len(_slice_top_df(df, "all")) == 250
        assert len(_slice_top_df(df, "0")) == 250
        assert len(_slice_top_df(df, "-1")) == 250
        assert len(_slice_top_df(df, None)) == 250
        # Empty df
        assert _slice_top_df(pd.DataFrame(), 100).empty
        assert _slice_top_df(None, 100).empty

    def test_slice_top_list(self):
        items = list(range(250))
        assert len(_slice_top_list(items, 100)) == 100
        assert len(_slice_top_list(items, 50)) == 50
        assert len(_slice_top_list(items, "all")) == 250
        assert len(_slice_top_list(items, "0")) == 250
        assert len(_slice_top_list(items, None)) == 250
        assert len(_slice_top_list([], 100)) == 0
        assert len(_slice_top_list(None, 100)) == 0

    def test_get_effective_limit(self, monkeypatch):
        # From config
        cfg = TradingConfig()
        cfg.prediction_output_limit = 100
        assert _get_effective_limit(cfg) == 100

        cfg.prediction_output_limit = "all"
        assert _get_effective_limit(cfg) == "all"

        # From env when cfg is None
        monkeypatch.setenv("PREDICTION_OUTPUT_LIMIT", "all")
        assert _get_effective_limit(None) == "all"

        monkeypatch.setenv("PREDICTION_OUTPUT_LIMIT", "75")
        assert _get_effective_limit(None) == 75


class TestMergeAndReportCompatibility:
    def test_extract_ensemble_market_section_top_and_all(self):
        content_top = (
            "=========================================\n"
            "[KOSPI] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name Ens Score Exp Ret(20D)\n"
            "-----------------------------------------\n"
            "1    005930 Samsung 85.0%    +10.5%\n"
            "2    000660 SKHynix 82.0%    +8.2%\n"
        )
        sec_top = _extract_ensemble_market_section(content_top, "KOSPI")
        assert "Samsung" in sec_top
        assert "[KOSPI] Top 100 Ensemble Picks" in sec_top

        content_all = (
            "=========================================\n"
            "[KOSPI] All Ensemble Picks (500 symbols) (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name Ens Score Exp Ret(20D)\n"
            "-----------------------------------------\n"
            "1    005930 Samsung 85.0%    +10.5%\n"
            "2    000660 SKHynix 82.0%    +8.2%\n"
        )
        sec_all = _extract_ensemble_market_section(content_all, "KOSPI")
        assert "Samsung" in sec_all
        assert "[KOSPI] All Ensemble Picks (500 symbols)" in sec_all

    def test_merge_lead_lag_top_and_all(self, tmp_path):
        mkt_dir = tmp_path / "run_kospi"
        mkt_dir.mkdir()
        ll_file = mkt_dir / "lead_lag_predictions_KOSPI.txt"
        ll_file.write_text(
            "=== Lead-Lag Surge Predictions ===\n"
            "Date: 2026-09-01 15:30\n\n"
            "--- KOSPI All (500) ---\n"
            "  1. [KOSPI] 005930 (Samsung): 88.50%\n"
            "  2. [KOSPI] 000660 (SKHynix): 85.20%\n\n"
            "--- Leaders with highest today return ---\n"
            "  1. 005930 (Samsung): +3.50%\n",
            encoding="utf-8"
        )

        res_dir = tmp_path / "result"
        res_dir.mkdir()
        target_dirs = {"KOSPI": mkt_dir}

        merge_lead_lag_predictions(res_dir, target_dirs)
        merged = (res_dir / "lead_lag_predictions.txt").read_text(encoding="utf-8")
        assert "005930" in merged
        assert "Samsung" in merged
        assert "--- KOSPI All (500) ---" in merged

    def test_merge_surge_top_and_all(self, tmp_path):
        mkt_dir = tmp_path / "run_kospi"
        mkt_dir.mkdir()
        surge_file = mkt_dir / "surge_predictions_KOSPI.txt"
        surge_file.write_text(
            "=== Surge Detection Results ===\n"
            "Date: 2026-09-01 15:30\n\n"
            "============================================================\n"
            "[20일] KOSPI All Surge Candidates (250)\n"
            "============================================================\n"
            "  1. [KOSPI] 005930 (Samsung): 65.0%\n"
            "  2. [KOSPI] 000660 (SKHynix): 60.0%\n\n",
            encoding="utf-8"
        )

        res_dir = tmp_path / "result"
        res_dir.mkdir()
        target_dirs = {"KOSPI": mkt_dir}

        merge_surge_predictions(res_dir, target_dirs)
        merged = (res_dir / "surge_predictions.txt").read_text(encoding="utf-8")
        assert "005930" in merged
        assert "Samsung" in merged
        assert "65.0%" in merged

    def test_parse_ensemble_all_section(self):
        text = (
            "KR Market Regime (KOSPI) : BULL\n"
            "US Market Regime (SP500) : BULL\n"
            "=========================================\n"
            "[KOSPI] All Ensemble Picks (500 symbols) (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name              Ens Score Exp Ret(20D) Reg   Srg   L-L\n"
            "--------------------------------------------------------------------\n"
            "1    005930 Samsung_Elec      85.0%     +15.20%      80.0% 75.0% 70.0%\n"
            "2    000660 SK_Hynix          82.0%     +12.10%      78.0% 72.0% 68.0%\n"
        )
        ens_data = parse_ensemble(text)
        assert len(ens_data.markets) == 1
        assert ens_data.markets[0].market == "KOSPI"
        assert len(ens_data.markets[0].rows) == 2
        assert ens_data.markets[0].rows[0].symbol == "005930"
        assert ens_data.markets[0].rows[1].symbol == "000660"

    def test_parse_regression_all_section(self):
        text = (
            "Date: 2026-09-01 15:30\n"
            "Horizon: 20\n"
            "--- KOSPI ALL (500) (Horizon: 20d) ---\n"
            "  1. 005930 (Samsung): +15.20%\n"
            "  2. 000660 (SKHynix): +12.10%\n"
        )
        date, sections = parse_regression(text)
        assert date == "2026-09-01 15:30"
        assert len(sections) == 1
        assert sections[0].market == "KOSPI"
        assert len(sections[0].rows) == 2
        assert sections[0].rows[0].symbol == "005930"

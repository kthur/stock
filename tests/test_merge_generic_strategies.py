"""
tests/test_merge_generic_strategies.py
Unit and edge-case tests for merge_generic_strategy_files() in merge_predictions.py
"""

import os
import sys
from pathlib import Path
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merge_predictions import merge_generic_strategy_files


class TestMergeGenericStrategiesComprehensive:

    @pytest.fixture(autouse=True)
    def setup_dirs(self, tmp_path):
        self.tmp_path = tmp_path
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        self.target_dirs = {}
        for m in self.markets:
            d = tmp_path / f"market_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_merge_stat_arb_with_unicode_dividers(self):
        """Test merge of stat_arb_predictions with unicode divider dashes."""
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"stat_arb_predictions_{mkt}.txt"
            content = (
                f"=== Strategy 7: Statistical Arbitrage Predictions ===\n"
                f"Date: 2026-08-22 09:00 KST\n"
                f"Total symbols: 2\n"
                f"Rank Symbol1 Symbol2 Market HalfLife ZScore Signal\n"
                f"─────────────────────────────────────────────────\n"
                f"1    {mkt}_A  {mkt}_B  {mkt}    12.5     -2.1   BUY_SPREAD\n"
                f"2    {mkt}_C  {mkt}_D  {mkt}    15.0     +2.3   SELL_SPREAD\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="stat_arb_predictions.txt",
            title="Statistical Arbitrage Pair Predictions"
        )

        merged = self.result_dir / "stat_arb_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Check headers: 1 title, 1 date, 1 column header, 1 divider
        assert sum(1 for line in lines if line.startswith("=== Statistical Arbitrage")) == 1
        assert sum(1 for line in lines if line.startswith("Date:")) == 1
        assert sum(1 for line in lines if line.startswith("Rank ")) == 1
        assert sum(1 for line in lines if line.startswith("───")) == 1

        # Check all data lines present (2 per market * 5 = 10)
        for mkt in self.markets:
            assert f"{mkt}_A" in text
            assert f"{mkt}_C" in text

    def test_merge_arm_factor_with_filters_and_dashes(self):
        """Test merge of arm_factor_predictions with Filters and ASCII dashes."""
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"arm_factor_predictions_{mkt}.txt"
            content = (
                f"=== Strategy 15: ARM Factor Predictions ===\n"
                f"Date: 2026-08-22 09:00 KST\n"
                f"Total symbols evaluated: 1\n"
                f"Filters: EPS Upgrades >= 2 | Target Price Rev > 5%\n"
                f"Rank Symbol    Name        Market      Price       ARM Score\n"
                f"------------------------------------------------------------\n"
                f"1    {mkt}_X    Name_{mkt}  {mkt:<10}  50.00       88.5%\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="arm_factor_predictions.txt",
            title="Analyst Revision Momentum Predictions"
        )

        merged = self.result_dir / "arm_factor_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")

        lines = text.splitlines()
        assert sum(1 for line in lines if line.startswith("Filters:")) == 1
        assert sum(1 for line in lines if line.startswith("Rank Symbol")) == 1
        assert sum(1 for line in lines if line.startswith("---")) == 1

        for mkt in self.markets:
            assert f"{mkt}_X" in text

    def test_merge_missing_files_and_fallback(self):
        """Test merge when only 1 market exists and others are missing entirely."""
        p = self.target_dirs["SP500"] / "vol_target_predictions_SP500.txt"
        p.write_text(
            "=== Strategy 22 ===\n"
            "Date: 2026-08-22\n"
            "Rank Symbol Name Market Price VolScore\n"
            "-------------------------------------\n"
            "1    AAPL   Apple SP500  180   95.0%\n",
            encoding="utf-8"
        )

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="vol_target_predictions.txt",
            title="Volatility Targeting Predictions"
        )

        merged = self.result_dir / "vol_target_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "AAPL" in text
        lines = text.splitlines()
        assert sum(1 for line in lines if line.startswith("Rank Symbol")) == 1
        assert sum(1 for line in lines if line.startswith("---")) == 1

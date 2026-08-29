"""
tests/test_merge_predictions_stress.py
Adversarial Stress Test Suite for trading_system/merge_predictions.py

Tests edge cases, malformed inputs, missing paths, boundary conditions,
footer bleed-in, mixed line endings (CRLF/LF/CR), Unicode/Korean text,
BOM headers, corrupt JSON, extreme floats, and self-referencing safety.
"""

import json
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

from merge_predictions import (
    discover_target_markets,
    _extract_ensemble_market_section,
    merge_generic_strategy_files,
    merge_surge_predictions,
    merge_vcp_ml_predictions,
    merge_vcp_patterns,
    merge_lead_lag_predictions,
    merge_portfolio_allocation,
    merge_backtest_summary,
    merge_coverage_report,
    merge_pipeline_result,
    get_file_content,
    KNOWN_MARKETS,
    ALL_31_STRATEGIES,
)


# ============================================================================
# 1. Stress Tests for get_file_content
# ============================================================================
class TestGetFileContentAdversarial:

    def test_nonexistent_file(self, tmp_path):
        assert get_file_content(tmp_path / "does_not_exist.txt") == ""

    def test_empty_zero_byte_file(self, tmp_path):
        p = tmp_path / "zero_bytes.txt"
        p.touch()
        assert get_file_content(p) == ""

    def test_mixed_line_endings(self, tmp_path):
        p = tmp_path / "mixed_crlf.txt"
        p.write_bytes(b"Line 1\r\nLine 2\nLine 3\r\nLine 4\n")
        content = get_file_content(p)
        assert "\r\n" not in content
        assert content == "Line 1\nLine 2\nLine 3\nLine 4\n"

    def test_utf8_with_bom(self, tmp_path):
        p = tmp_path / "bom.txt"
        p.write_bytes(b"\xef\xbb\xbf=== BOM Header ===\nData\n")
        content = get_file_content(p)
        assert "=== BOM Header ===" in content
        assert "Data" in content

    def test_korean_cp949_fallback(self, tmp_path):
        p = tmp_path / "cp949.txt"
        # CP949 encoded Korean bytes that might fail strict UTF-8
        text_cp949 = "1 005930 삼성전자 KOSPI 70,000 +5.2%\n".encode("cp949")
        p.write_bytes(text_cp949)
        content = get_file_content(p)
        # Must not crash, should return content (either via UTF-8 ignore or CP949)
        assert isinstance(content, str)
        assert "KOSPI" in content

    def test_binary_garbage_resilience(self, tmp_path):
        p = tmp_path / "corrupt.txt"
        p.write_bytes(b"\x00\xff\xfe\x80\x90\xaa\xbb\xcc\xdd\xee\xff")
        # Should gracefully return a string without throwing exceptions
        content = get_file_content(p)
        assert isinstance(content, str)


# ============================================================================
# 2. Stress Tests for discover_target_markets
# ============================================================================
class TestDiscoverTargetMarketsAdversarial:

    def test_both_dirs_nonexistent(self, tmp_path):
        base_dir = tmp_path / "nonexistent_base"
        result_dir = tmp_path / "nonexistent_result"
        targets = discover_target_markets(base_dir, result_dir)
        assert targets == {}

    def test_empty_result_dir_and_empty_base(self, tmp_path):
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        result_dir = base_dir / "result"
        result_dir.mkdir()
        targets = discover_target_markets(base_dir, result_dir)
        assert targets == {}

    def test_empty_split_folders_ignored(self, tmp_path):
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir()
        # Empty split directories
        (base_dir / "result_KOSPI").mkdir()
        (base_dir / "result-SP500").mkdir()
        targets = discover_target_markets(base_dir, result_dir)
        # Empty split folders should not be added if they have no files
        assert "KOSPI" not in targets
        assert "SP500" not in targets

    def test_split_folders_in_artifacts_in(self, tmp_path):
        base_dir = tmp_path / "sub"
        base_dir.mkdir()
        artifacts_in = base_dir / "artifacts_in"
        artifacts_in.mkdir()
        m_dir = artifacts_in / "result_NASDAQ"
        m_dir.mkdir()
        (m_dir / "sample.txt").write_text("ok", encoding="utf-8")

        result_dir = base_dir / "result"
        result_dir.mkdir()

        targets = discover_target_markets(base_dir, result_dir)
        assert "NASDAQ" in targets
        assert targets["NASDAQ"] == m_dir

    def test_multi_probe_all_strategy_prefixes(self, tmp_path):
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir()

        # Place different strategy files for different markets
        (result_dir / "sentiment_predictions_RUSSELL2000.txt").write_text("data", encoding="utf-8")
        (result_dir / "backtest_summary_KOSDAQ.json").write_text("{}", encoding="utf-8")
        (result_dir / "portfolio_allocation_KONEX.txt").write_text("data", encoding="utf-8")
        (result_dir / "strategy_data_coverage_report_CHINA_SSE.txt").write_text("data", encoding="utf-8")

        targets = discover_target_markets(base_dir, result_dir)
        assert "RUSSELL2000" in targets
        assert "KOSDAQ" in targets
        assert "KONEX" in targets
        assert "CHINA_SSE" in targets

    def test_excluded_utility_files_not_discovered_as_markets(self, tmp_path):
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir()

        # Files that should be excluded
        (result_dir / "portfolio_allocation_black_litterman.txt").write_text("data", encoding="utf-8")
        (result_dir / "portfolio_allocation_hrp.txt").write_text("data", encoding="utf-8")
        (result_dir / "pipeline_result_comparison.txt").write_text("data", encoding="utf-8")
        (result_dir / "vcp_patterns_patterns.txt").write_text("data", encoding="utf-8")
        (result_dir / "strategy_data_coverage_report_summary.txt").write_text("data", encoding="utf-8")
        (result_dir / "backtest_summary_report.txt").write_text("data", encoding="utf-8")

        targets = discover_target_markets(base_dir, result_dir)
        assert "BLACK_LITTERMAN" not in targets
        assert "LITTERMAN" not in targets
        assert "HRP" not in targets
        assert "COMPARISON" not in targets
        assert "PATTERNS" not in targets
        assert "SUMMARY" not in targets
        assert "REPORT" not in targets

    def test_dynamic_custom_market_discovery(self, tmp_path):
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir()

        (result_dir / "rim_predictions_GLOBAL1.txt").write_text("data", encoding="utf-8")
        (result_dir / "accruals_quality_predictions_TECH50.txt").write_text("data", encoding="utf-8")
        # Too long candidate (> 12 chars) should be ignored
        (result_dir / "rim_predictions_VERYLONGMARKETNAMETHATEXCEEDS12CHARS.txt").write_text("data", encoding="utf-8")

        targets = discover_target_markets(base_dir, result_dir)
        assert "GLOBAL1" in targets
        assert "TECH50" in targets
        assert "VERYLONGMARKETNAMETHATEXCEEDS12CHARS" not in targets


# ============================================================================
# 3. Stress Tests for _extract_ensemble_market_section
# ============================================================================
class TestExtractEnsembleMarketSectionAdversarial:

    def test_empty_and_whitespace_content(self):
        assert _extract_ensemble_market_section("", "KOSPI") == ""
        assert _extract_ensemble_market_section("   \n\n\t  \n", "KOSPI") == ""

    def test_no_data_placeholders(self):
        assert _extract_ensemble_market_section("=== Ensemble ===\n데이터 없음\n", "SP500") == ""
        assert _extract_ensemble_market_section("=== Ensemble ===\nNo data available\n", "SP500") == ""

    def test_missing_both_top_and_bottom_borders(self):
        content = (
            "[KOSPI] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "1 005930 삼성전자 90.0% +10.0%\n"
            "2 000660 SK하이닉스 88.0% +12.0%\n"
        )
        sect = _extract_ensemble_market_section(content, "KOSPI")
        assert "[KOSPI] Top 100 Ensemble Picks" in sect
        assert "005930" in sect
        assert "삼성전자" in sect
        assert "SK하이닉스" in sect

    def test_uneven_and_variable_width_borders(self):
        content = (
            "===================\n"
            "[NASDAQ] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "------------------------------------------------------------------------\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "1 NVDA Nvidia 95.0% +25.0%\n"
            "---------------------\n"
            "[SP500] Top 100 Ensemble Picks\n"
            "1 AAPL Apple 90.0% +15.0%\n"
        )
        sect = _extract_ensemble_market_section(content, "NASDAQ")
        assert "[NASDAQ] Top 100 Ensemble Picks" in sect
        assert "NVDA" in sect
        assert "AAPL" not in sect

    def test_footer_stripping_applied_weights(self):
        content = (
            "=========================================\n"
            "[RUSSELL2000] Top 100 Ensemble Picks\n"
            "=========================================\n"
            "1 IWM iShares 80.0% +5.0%\n"
            "2 VT Vanguard 78.0% +4.0%\n\n"
            "--- Applied Strategy Weights (Macro Regime: BULL) ---\n"
            "XGBoost Regression: 20.0%\n"
            "Surge Classifier: 15.0%\n"
        )
        sect = _extract_ensemble_market_section(content, "RUSSELL2000")
        assert "IWM" in sect
        assert "VT" in sect
        assert "Applied Strategy Weights" not in sect
        assert "XGBoost Regression" not in sect

    def test_footer_stripping_data_quality_notes(self):
        content = (
            "=========================================\n"
            "[KOSDAQ] Top 100 Ensemble Picks\n"
            "=========================================\n"
            "1 068270 셀트리온 85.0% +8.0%\n\n"
            "--- Data Quality Notes (auto-detected) ---\n"
            "- Factor coverage: 98%\n"
        )
        sect = _extract_ensemble_market_section(content, "KOSDAQ")
        assert "068270" in sect
        assert "Data Quality Notes" not in sect

    def test_footer_stripping_executive_summary(self):
        content = (
            "=========================================\n"
            "[SP500] Top 100 Ensemble Picks\n"
            "=========================================\n"
            "1 MSFT Microsoft 92.0% +14.0%\n\n"
            "--- Executive Summary ---\n"
            "Overall Bullish Market conditions.\n"
        )
        sect = _extract_ensemble_market_section(content, "SP500")
        assert "MSFT" in sect
        assert "Executive Summary" not in sect

    def test_korean_special_characters_and_emojis(self):
        content = (
            "=========================================\n"
            "[KOSPI] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "1 005935 삼성전자(우) 95.0% +10.0% [🔥Hot/🚀Surge] (주당배당 3.5%)\n"
            "2 035760 CJ ENM & Co. 90.0% +8.0% <수급-외인> {A+등급}\n"
        )
        sect = _extract_ensemble_market_section(content, "KOSPI")
        assert "삼성전자(우)" in sect
        assert "🔥Hot/🚀Surge" in sect
        assert "CJ ENM & Co." in sect

    def test_crlf_and_lf_mixed_endings(self):
        content = (
            "=========================================\r\n"
            "[SP500] Top 100 Ensemble Picks\r\n"
            "=========================================\n"
            "1 AAPL Apple 90.0%\r\n"
            "2 GOOGL Alphabet 88.0%\n"
        )
        sect = _extract_ensemble_market_section(content, "SP500")
        assert "AAPL" in sect
        assert "GOOGL" in sect


# ============================================================================
# 4. Stress Tests for merge_generic_strategy_files
# ============================================================================
class TestMergeGenericStrategyFilesAdversarial:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.target_dirs = {}
        self.markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for m in self.markets:
            d = tmp_path / f"mkt_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_empty_target_dirs(self):
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs={},
            filename="empty_target_test.txt",
            title="Empty Target Test"
        )
        merged = self.result_dir / "empty_target_test.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "데이터 없음" in text

    def test_missing_files_across_all_markets(self):
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="missing_all.txt",
            title="Missing All Test"
        )
        merged = self.result_dir / "missing_all.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "데이터 없음" in text

    def test_corrupt_or_zero_byte_market_files(self):
        for m in self.markets:
            p = self.target_dirs[m] / f"corrupt_test_{m}.txt"
            p.touch()  # 0 bytes

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="corrupt_test.txt",
            title="Corrupt Test"
        )
        merged = self.result_dir / "corrupt_test.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "데이터 없음" in text

    def test_complex_multi_header_and_divider_types(self):
        # Mix of Rank, Filters:, ───, ===, No., Symbol headers across markets
        headers_and_data = [
            ("KOSPI", "Filters: Vol > 1M | PBR < 1.0\nRank Symbol Name Market Score\n───────────────────────────────\n1 005930 삼성 KOSPI 90%"),
            ("KOSDAQ", "Rank Symbol Name Market Score\n-----------------------------------\n1 068270 셀트 KOSDAQ 85%"),
            ("SP500", "No. Symbol Name Market Score\n===================================\n1 AAPL Apple SP500 92%"),
            ("NASDAQ", "Symbol Name Market Score\n═══════════════════════════════════\n1 MSFT Microsoft NASDAQ 88%"),
            ("RUSSELL2000", "Rank Symbol Name Market Score\n-----------------------------------\n1 IWM iShares RUSSELL2000 80%"),
        ]
        for mkt, content in headers_and_data:
            p = self.target_dirs[mkt] / f"multi_hdr_{mkt}.txt"
            p.write_text(f"=== Header ===\nDate: 2026-08-29\n{content}\n", encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="multi_hdr.txt",
            title="Multi Header Strategy"
        )

        merged = self.result_dir / "multi_hdr.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Header lines should be placed at the top block before data
        assert any(l.startswith("Filters:") for l in lines)
        assert any(l.startswith("Rank ") for l in lines)
        # All 5 data rows present
        assert "005930" in text
        assert "068270" in text
        assert "AAPL" in text
        assert "MSFT" in text
        assert "IWM" in text

    def test_extreme_floats_and_percentages(self):
        p_sp = self.target_dirs["SP500"] / "extreme_strat_SP500.txt"
        p_sp.write_text(
            "Rank Symbol Market Price Score Extra\n"
            "------------------------------------\n"
            "1 EX1 SP500 0.0001 -99.99% -inf%\n"
            "2 EX2 SP500 999999.9 +12345.67% nan%\n"
            "3 EX3 SP500 1.23e-4 0.00% 100.0%\n",
            encoding="utf-8"
        )
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="extreme_strat.txt",
            title="Extreme Strat Test"
        )
        merged = self.result_dir / "extreme_strat.txt"
        text = merged.read_text(encoding="utf-8")
        assert "EX1" in text
        assert "EX2" in text
        assert "EX3" in text
        assert "-99.99%" in text
        assert "+12345.67%" in text

    def test_self_referencing_safety_when_target_is_result_dir(self):
        # Create an existing file in result_dir
        existing_file = self.result_dir / "self_ref_strat.txt"
        existing_file.write_text("=== Preserved Original Content ===\nLine 1\nLine 2\n", encoding="utf-8")

        # target_dirs points to result_dir, but split files self_ref_strat_{m}.txt do NOT exist
        targets = {"SP500": self.result_dir, "KOSPI": self.result_dir}
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=targets,
            filename="self_ref_strat.txt",
            title="Self Ref Strat"
        )

        # File must remain untouched and not be erased to '데이터 없음'
        assert existing_file.exists()
        assert "Preserved Original Content" in existing_file.read_text(encoding="utf-8")


# ============================================================================
# 5. Stress Tests for merge_portfolio_allocation
# ============================================================================
class TestMergePortfolioAllocationAdversarial:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.target_dirs = {}
        self.markets = ["KOSPI", "SP500", "NASDAQ"]
        for m in self.markets:
            d = tmp_path / f"mkt_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_weight_renormalization_exceeding_max_alloc(self):
        # Each market produces 30% weight -> total = 90% > 85.0% target max
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"portfolio_allocation_{mkt}.txt"
            content = (
                f"=== Portfolio Allocation ({mkt}) ===\n"
                f"Total Capital: 100,000,000 KRW\n"
                f"Target Horizon: 20d\n"
                f"Current Market Regime Detected: BULL_TREND\n"
                f"Maximum Total Allocation Allowed: 85.0%\n\n"
                f"No.  Symbol   Name                 Market         Return     Volatility   Weight     Amount\n"
                f"------------------------------------------------------------------------------------------------\n"
                f"1    {mkt}_1  Name_{mkt}_1         {mkt:<14}      20.00%     15.00%       30.00%     30,000,000\n"
                f"2    {mkt}_2  Name_{mkt}_2         {mkt:<14}      18.00%     14.00%       30.00%     30,000,000\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_portfolio_allocation(self.result_dir, self.target_dirs)

        merged = self.result_dir / "portfolio_allocation.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")

        # Total allocated capital must not exceed 85.0%
        import re
        m_alloc = re.search(r"Allocated Capital:\s*([\d.]+)%", text)
        assert m_alloc is not None
        allocated_pct = float(m_alloc.group(1))
        assert allocated_pct <= 85.01  # Allow tiny floating precision
        assert "Remaining Cash" in text

    def test_duplicate_symbols_deduplicated_highest_weight_kept(self):
        # SP500 and NASDAQ both allocate to AAPL with different weights
        p_sp = self.target_dirs["SP500"] / "portfolio_allocation_SP500.txt"
        p_sp.write_text(
            "Total Capital: 100,000,000 KRW\n"
            "Maximum Total Allocation Allowed: 85.0%\n"
            "1 AAPL Apple SP500 15.00% 12.00% 10.00% 10,000,000\n",
            encoding="utf-8"
        )
        p_nq = self.target_dirs["NASDAQ"] / "portfolio_allocation_NASDAQ.txt"
        p_nq.write_text(
            "Total Capital: 100,000,000 KRW\n"
            "Maximum Total Allocation Allowed: 85.0%\n"
            "1 AAPL Apple NASDAQ 20.00% 12.00% 25.00% 25,000,000\n",
            encoding="utf-8"
        )

        merge_portfolio_allocation(self.result_dir, self.target_dirs)

        merged = self.result_dir / "portfolio_allocation.txt"
        text = merged.read_text(encoding="utf-8")
        # AAPL should appear exactly once in the table rows
        rows = [line for line in text.splitlines() if "AAPL" in line]
        assert len(rows) == 1

    def test_corrupted_syntax_rows_handled_safely(self):
        p_sp = self.target_dirs["SP500"] / "portfolio_allocation_SP500.txt"
        p_sp.write_text(
            "Total Capital: 100,000,000 KRW\n"
            "Maximum Total Allocation Allowed: 85.0%\n"
            "1 GOOD1 Valid SP500 15.00% 12.00% 10.00% 10,000,000\n"
            "corrupted line with invalid tokens\n",
            encoding="utf-8"
        )

        merge_portfolio_allocation(self.result_dir, self.target_dirs)

        merged = self.result_dir / "portfolio_allocation.txt"
        text = merged.read_text(encoding="utf-8")
        assert "GOOD1" in text

    def test_reproduce_nan_weight_bug(self):
        """Empirical challenge test demonstrating the NaN weight ValueError vulnerability in merge_portfolio_allocation."""
        p_sp = self.target_dirs["SP500"] / "portfolio_allocation_SP500.txt"
        p_sp.write_text(
            "Total Capital: 100,000,000 KRW\n"
            "Maximum Total Allocation Allowed: 85.0%\n"
            "1 BAD1 Corrupt SP500 10.00% 10.00% nan% 1,000,000\n"
            "2 GOOD1 Valid SP500 15.00% 12.00% 10.00% 10,000,000\n",
            encoding="utf-8"
        )

        # When row_re matches 'nan%', float('nan') returns math.nan, leading to ValueError on int(round(...))
        with pytest.raises(ValueError, match="cannot convert float NaN to integer"):
            merge_portfolio_allocation(self.result_dir, self.target_dirs)


# ============================================================================
# 6. Stress Tests for merge_backtest_summary
# ============================================================================
class TestMergeBacktestSummaryAdversarial:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.target_dirs = {}
        self.markets = ["KOSPI", "SP500"]
        for m in self.markets:
            d = tmp_path / f"mkt_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_corrupt_json_resilience(self):
        p_kp = self.target_dirs["KOSPI"] / "backtest_summary_KOSPI.json"
        p_kp.write_text("{corrupt: json syntax error", encoding="utf-8")

        p_sp = self.target_dirs["SP500"] / "backtest_summary_SP500.json"
        p_sp.write_text(json.dumps({"updated_at": "2026-08-29", "strategies": {"strat1": {"win_rate": 0.65}}}), encoding="utf-8")

        merge_backtest_summary(self.result_dir, self.target_dirs)

        merged = self.result_dir / "backtest_summary.json"
        assert merged.exists()
        data = json.loads(merged.read_text(encoding="utf-8"))
        assert "strat1" in data["strategies"]
        assert data["market"] == "SP500"

    def test_prefers_realized_strategies_over_empty_summary(self):
        # KOSPI is newer but empty
        p_kp = self.target_dirs["KOSPI"] / "backtest_summary_KOSPI.json"
        p_kp.write_text(json.dumps({"updated_at": "2026-08-29T23:00:00", "strategies": {}}), encoding="utf-8")

        # SP500 is older but has populated strategies
        p_sp = self.target_dirs["SP500"] / "backtest_summary_SP500.json"
        p_sp.write_text(json.dumps({"updated_at": "2026-08-28T10:00:00", "strategies": {"ensemble": {"sharpe": 1.8}}}), encoding="utf-8")

        merge_backtest_summary(self.result_dir, self.target_dirs)

        merged = self.result_dir / "backtest_summary.json"
        data = json.loads(merged.read_text(encoding="utf-8"))
        assert "ensemble" in data["strategies"]


# ============================================================================
# 7. Stress Tests for merge_surge_predictions & merge_vcp_ml_predictions
# ============================================================================
class TestSurgeAndVCPMLPredictionsAdversarial:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.target_dirs = {}
        self.markets = ["KOSPI", "SP500"]
        for m in self.markets:
            d = tmp_path / f"mkt_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_surge_merge_with_missing_horizons_and_uneven_dividers(self):
        # KOSPI only has 1일 and 5일; SP500 has 3일 and 20일
        p_kp = self.target_dirs["KOSPI"] / "surge_predictions_KOSPI.txt"
        p_kp.write_text(
            "--- Surge KOSPI ---\n"
            "[1일] KOSPI Top 20 Surge Predictions (>= 20% Return Probability)\n"
            "---------------------------------------------------------------\n"
            "1. [005930] 삼성전자 80.0%\n\n"
            "===============================================================\n"
            "[5일] KOSPI Top 20 Surge Predictions (>= 20% Return Probability)\n"
            "===============================================================\n"
            "1. [000660] SK하이닉스 75.0%\n",
            encoding="utf-8"
        )
        p_sp = self.target_dirs["SP500"] / "surge_predictions_SP500.txt"
        p_sp.write_text(
            "[3일] SP500 Top 20 Surge Predictions (>= 20% Return Probability)\n"
            "1. [AAPL] Apple 85.0%\n\n"
            "[20일] SP500 Top 20 Surge Predictions (>= 20% Return Probability)\n"
            "1. [NVDA] Nvidia 90.0%\n",
            encoding="utf-8"
        )

        merge_surge_predictions(self.result_dir, self.target_dirs)

        merged = self.result_dir / "surge_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "005930" in text
        assert "SK하이닉스" in text
        assert "AAPL" in text
        assert "NVDA" in text

    def test_vcp_ml_merge_empty_and_populated_mix(self):
        p_kp = self.target_dirs["KOSPI"] / "vcp_ml_predictions_KOSPI.txt"
        p_kp.write_text(
            "=== VCP ML Predictions ===\n"
            "[1일] KOSPI TOP 5\n"
            "  1. [005930] 삼성전자: 85.0%\n\n"
            "[3일] KOSPI TOP 5\n"
            "  1. [000660] SK하이닉스: 80.0%\n",
            encoding="utf-8"
        )
        p_sp = self.target_dirs["SP500"] / "vcp_ml_predictions_SP500.txt"
        p_sp.write_text("데이터 없음\n", encoding="utf-8")

        merge_vcp_ml_predictions(self.result_dir, self.target_dirs)

        merged = self.result_dir / "vcp_ml_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "005930" in text
        assert "SK하이닉스" in text


# ============================================================================
# 8. Stress Tests for merge_coverage_report & merge_pipeline_result
# ============================================================================
class TestCoverageAndPipelineResultAdversarial:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.target_dirs = {}
        self.markets = ["KOSPI", "SP500"]
        for m in self.markets:
            d = tmp_path / f"mkt_{m}"
            d.mkdir(parents=True, exist_ok=True)
            self.target_dirs[m] = d

    def test_merge_coverage_report_filters_titles(self):
        p_kp = self.target_dirs["KOSPI"] / "strategy_data_coverage_report_KOSPI.txt"
        p_kp.write_text(
            "=== 31-Strategy Data Coverage Report ===\n"
            "XGBoost Regression: 100.0% (0 missing)\n"
            "RIM Valuation: 85.0% (15 missing: No financial filings)\n",
            encoding="utf-8"
        )
        merge_coverage_report(self.result_dir, self.target_dirs)

        merged = self.result_dir / "strategy_data_coverage_report.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "[KOSPI]" in text
        assert "XGBoost Regression: 100.0%" in text
        assert "RIM Valuation: 85.0%" in text

    def test_merge_pipeline_result_strips_duplicate_headers_and_date(self):
        for m in self.markets:
            p = self.target_dirs[m] / f"pipeline_result_{m}.txt"
            p.write_text(
                f"=== Full Pipeline Inference Results ===\n"
                f"Date: 2026-08-29\n"
                f"Total symbols: 1\n\n"
                f"1 {m}_01 Name_{m} {m} 100 120 130 140 150 160 170 180 +15.0%\n",
                encoding="utf-8"
            )

        merge_pipeline_result(self.result_dir, self.target_dirs)

        merged = self.result_dir / "pipeline_result.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Date and Title should appear only once at the top
        assert sum(1 for l in lines if l.startswith("=== Full Pipeline")) == 1
        assert sum(1 for l in lines if l.startswith("Date:")) == 1
        assert "KOSPI_01" in text
        assert "SP500_01" in text

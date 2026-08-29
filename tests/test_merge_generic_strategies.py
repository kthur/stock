"""
tests/test_merge_generic_strategies.py
Comprehensive unit, edge-case, and integration tests for merge_predictions.py
Covers multi-artifact market discovery, section extraction, header deduplication,
and 31+ strategy multi-market merging.
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

from merge_predictions import (
    merge_generic_strategy_files,
    merge_ensemble_predictions,
    _extract_ensemble_market_section,
    merge_surge_predictions,
    merge_vcp_ml_predictions,
    merge_pipeline_result,
    discover_target_markets,
    KNOWN_MARKETS,
    ALL_31_STRATEGIES,
)


STRATEGY_FILENAMES = [
    ("lstm_predictions.txt", "Strict Causal LSTM Time-Series Deep Learning Predictions"),
    ("sector_predictions.txt", "Sector Rotation Momentum & Macro Sensitivity Report"),
    ("rim_predictions.txt", "RIM Intrinsic Valuation Predictions"),
    ("event_driven_predictions.txt", "Event-Driven Disclosure Catalyst Predictions"),
    ("mq_factor_predictions.txt", "Momentum Quality (MQ) Factor Predictions"),
    ("iv_skew_predictions.txt", "Options Put/Call IV Skew Predictions"),
    ("order_flow_predictions.txt", "Order Flow Imbalance (MFI) Predictions"),
    ("short_term_reversal_predictions.txt", "Short-Term Mean Reversal Predictions"),
    ("stat_arb_predictions.txt", "Statistical Arbitrage Cointegration Predictions"),
    ("arm_factor_predictions.txt", "Analyst Revision Momentum (ARM) Predictions"),
    ("card_factor_predictions.txt", "Cross-Asset Regime Divergence (CARD) Predictions"),
    ("latr_factor_predictions.txt", "Liquidity-Adjusted Tail Risk (LATR) Predictions"),
    ("inst_foreign_sector_predictions.txt", "Institutional & Foreign Sector Flow Predictions"),
    ("supply_chain_predictions.txt", "Supply Chain Lead-Lag Momentum Predictions"),
    ("sentiment_predictions.txt", "NLP & FinBERT Sentiment Catalyst Predictions"),
    ("factor_neutralized_predictions.txt", "Multi-Factor Style Neutralized Pure Alpha Predictions"),
    ("vol_target_predictions.txt", "Dynamic Volatility Targeting Risk Parity Predictions"),
    ("microstructure_predictions.txt", "Order Book Microstructure Imbalance Predictions"),
    ("accruals_quality_predictions.txt", "Accruals Quality Accounting Anomaly Predictions"),
    ("short_squeeze_predictions.txt", "Short Interest & Squeeze Catalyst Predictions"),
    ("valueup_catalyst_predictions.txt", "Value-Up & Shareholder Yield Predictions"),
    ("trend_efficiency_predictions.txt", "Kaufman Trend Efficiency Predictions"),
    ("gamma_squeeze_predictions.txt", "Options Gamma Squeeze Predictions"),
    ("insider_buying_predictions.txt", "Executive & Insider Buying Catalyst Predictions"),
    ("hft_order_flow_predictions.txt", "HFT Order Flow & Dark Pool Predictions"),
    ("darkpool_predictions.txt", "Dark Pool & Off-Exchange Volume Divergence Predictions"),
    ("earnings_tone_drift_predictions.txt", "Earnings Tone Drift NLP Quant Predictions"),
    ("dual_correction_predictions.txt", "Dual Correction Strategy Predictions"),
    ("index_rebalance_predictions.txt", "Index Rebalance Structural Flow Predictions"),
    ("overnight_gap_predictions.txt", "Overnight Gap Reversal Predictions"),
]


class TestMergeGenericStrategiesComprehensive:

    @pytest.fixture(autouse=True)
    def setup_dirs(self, tmp_path):
        self.tmp_path = tmp_path
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000", "KONEX"]
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

        # Check all data lines present (2 per market * 6 = 12)
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

    @pytest.mark.parametrize("filename,title", STRATEGY_FILENAMES)
    def test_all_31_strategies_merge_parity(self, filename, title):
        """Verify clean 5-market merge for every individual strategy file."""
        stem = Path(filename).stem
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"{stem}_{mkt}.txt"
            content = (
                f"=== {title} ===\n"
                f"Date: 2026-08-29 23:00 KST\n"
                f"Total symbols evaluated: 2\n"
                f"Rank Symbol    Name        Market      Score\n"
                f"---------------------------------------------\n"
                f"1    {mkt}_01   종목_{mkt}_1  {mkt:<10}  92.5%\n"
                f"2    {mkt}_02   종목_{mkt}_2  {mkt:<10}  85.0%\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename=filename,
            title=title
        )

        merged = self.result_dir / filename
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Exactly 1 header block
        assert sum(1 for line in lines if line.startswith(f"=== {title}")) == 1
        assert sum(1 for line in lines if line.startswith("Date:")) == 1
        assert sum(1 for line in lines if line.startswith("Rank Symbol")) == 1
        assert sum(1 for line in lines if line.startswith("---")) == 1

        # All market data rows present with UTF-8 korean names preserved
        for mkt in self.markets:
            assert f"{mkt}_01" in text
            assert f"{mkt}_02" in text
            assert f"종목_{mkt}_1" in text

    def test_stat_arb_pair_header_preservation_and_deduplication(self):
        """Verify Pair column header deduplication and placement."""
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"stat_arb_predictions_{mkt}.txt"
            content = (
                f"=== Strategy 7: Statistical Arbitrage Predictions ===\n"
                f"Date: 2026-08-29 23:00 KST\n"
                f"Total cointegrated pairs found: 1\n"
                f"Pair                     Z-Score   Correlation    Beta/Hedge  Signal\n"
                f"--------------------------------------------------------------------\n"
                f"SYM1_{mkt}-SYM2_{mkt}      -2.45     0.92           1.05        BUY_SPREAD\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="stat_arb_predictions.txt",
            title="Statistical Arbitrage Cointegration Predictions"
        )

        merged = self.result_dir / "stat_arb_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Pair header must appear exactly once at the top
        assert sum(1 for line in lines if line.startswith("Pair ")) == 1
        assert sum(1 for line in lines if line.startswith("---")) == 1
        # Data rows must all be present
        for mkt in self.markets:
            assert f"SYM1_{mkt}-SYM2_{mkt}" in text

    def test_portfolio_header_preservation_and_deduplication(self):
        """Verify No. column header deduplication."""
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"sample_alloc_{mkt}.txt"
            content = (
                f"=== Sample Allocation ===\n"
                f"Date: 2026-08-29 23:00 KST\n\n"
                f"No.  Symbol       Name                 Market         Return     Volatility   Weight     Amount\n"
                f"------------------------------------------------------------------------------------------------\n"
                f"1    {mkt}_SYM1   Stock_{mkt}          {mkt:<14}  +12.00%    15.00%       5.00%      5,000,000\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="sample_alloc.txt",
            title="Sample Allocation Table"
        )

        merged = self.result_dir / "sample_alloc.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        lines = text.splitlines()

        assert sum(1 for line in lines if line.startswith("No.")) == 1
        assert sum(1 for line in lines if line.startswith("---")) == 1
        for mkt in self.markets:
            assert f"{mkt}_SYM1" in text

    def test_merge_all_markets_empty_no_data(self):
        """When all market files contain '데이터 없음', merged output writes '데이터 없음'."""
        for mkt in self.markets:
            p = self.target_dirs[mkt] / f"empty_strat_{mkt}.txt"
            content = (
                f"=== Empty Strategy ===\n"
                f"Date: 2026-08-29 23:00 KST\n\n"
                f"데이터 없음\n"
            )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="empty_strat.txt",
            title="Empty Strategy Report"
        )

        merged = self.result_dir / "empty_strat.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert "데이터 없음" in text

    def test_merge_partial_markets_data_and_empty(self):
        """When 2 markets have data and 4 have '데이터 없음', merge only valid data rows."""
        for i, mkt in enumerate(self.markets):
            p = self.target_dirs[mkt] / f"partial_strat_{mkt}.txt"
            if i < 2:
                content = (
                    f"=== Partial Strategy ===\n"
                    f"Date: 2026-08-29 23:00 KST\n\n"
                    f"Rank Symbol Name Market Score\n"
                    f"-----------------------------\n"
                    f"1    {mkt}_P Name_{mkt} {mkt} 90.0%\n"
                )
            else:
                content = (
                    f"=== Partial Strategy ===\n"
                    f"Date: 2026-08-29 23:00 KST\n\n"
                    f"데이터 없음\n"
                )
            p.write_text(content, encoding="utf-8")

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="partial_strat.txt",
            title="Partial Strategy Report"
        )

        merged = self.result_dir / "partial_strat.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")
        assert f"{self.markets[0]}_P" in text
        assert f"{self.markets[1]}_P" in text
        # '데이터 없음' must NOT be appended into data lines when valid rows exist
        assert "데이터 없음" not in text

    def test_merge_self_referencing_safety(self):
        """When target_dirs points to result_dir and split files are missing, existing file is not truncated."""
        existing_file = self.result_dir / "existing_strat.txt"
        existing_file.write_text("=== Existing Pipeline Result ===\nOriginal Content\n", encoding="utf-8")

        target_dirs = {"SP500": self.result_dir, "KOSPI": self.result_dir}
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=target_dirs,
            filename="existing_strat.txt",
            title="Existing Strategy"
        )

        assert existing_file.exists()
        assert "Original Content" in existing_file.read_text(encoding="utf-8")


class TestMarketDiscoveryMultiProbe:

    def test_market_discovery_via_pipeline_result_when_surge_missing(self, tmp_path):
        """Market is discovered when surge_predictions is missing but pipeline_result exists."""
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        # SP500 only has pipeline_result
        (result_dir / "pipeline_result_SP500.txt").write_text("1 AAPL Apple SP500 10.0%\n", encoding="utf-8")
        # KOSPI only has rim_predictions
        (result_dir / "rim_predictions_KOSPI.txt").write_text("1 005930 삼성전자 KOSPI 50000 80.0%\n", encoding="utf-8")
        # NASDAQ only has ensemble_predictions
        (result_dir / "ensemble_predictions_NASDAQ.txt").write_text("1 MSFT Microsoft NASDAQ 85.0%\n", encoding="utf-8")

        target_dirs = discover_target_markets(base_dir, result_dir)

        assert "SP500" in target_dirs
        assert "KOSPI" in target_dirs
        assert "NASDAQ" in target_dirs

    def test_market_discovery_dedicated_split_folders(self, tmp_path):
        """Market is discovered from dedicated result_{m} or result-{m} folders."""
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        split_kosdaq = base_dir / "result_KOSDAQ"
        split_kosdaq.mkdir()
        (split_kosdaq / "pipeline_result_KOSDAQ.txt").write_text("data", encoding="utf-8")

        split_russell = base_dir / "result-RUSSELL2000"
        split_russell.mkdir()
        (split_russell / "surge_predictions_RUSSELL2000.txt").write_text("data", encoding="utf-8")

        target_dirs = discover_target_markets(base_dir, result_dir)

        assert "KOSDAQ" in target_dirs
        assert target_dirs["KOSDAQ"] == split_kosdaq
        assert "RUSSELL2000" in target_dirs
        assert target_dirs["RUSSELL2000"] == split_russell

    def test_market_discovery_konex_and_dynamic_markets(self, tmp_path):
        """KONEX and other dynamic valid markets are discovered."""
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        (result_dir / "ensemble_predictions_KONEX.txt").write_text("data", encoding="utf-8")
        (result_dir / "rim_predictions_TAIWAN.txt").write_text("data", encoding="utf-8")

        target_dirs = discover_target_markets(base_dir, result_dir)

        assert "KONEX" in target_dirs
        assert "TAIWAN" in target_dirs

    def test_market_discovery_excludes_non_market_files(self, tmp_path):
        """Files like portfolio_allocation_black_litterman.txt or run_comparison.txt are not treated as markets."""
        base_dir = tmp_path
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        (result_dir / "portfolio_allocation_black_litterman.txt").write_text("data", encoding="utf-8")
        (result_dir / "run_comparison.txt").write_text("data", encoding="utf-8")
        (result_dir / "vcp_patterns.txt").write_text("data", encoding="utf-8")
        (result_dir / "strategy_attribution_report.txt").write_text("data", encoding="utf-8")

        target_dirs = discover_target_markets(base_dir, result_dir)

        assert "LITTERMAN" not in target_dirs
        assert "BLACK_LITTERMAN" not in target_dirs
        assert "COMPARISON" not in target_dirs
        assert "PATTERNS" not in target_dirs
        assert "REPORT" not in target_dirs


class TestEnsembleSectionExtraction:

    def test_extract_ensemble_standard_border(self):
        """Extracts market section with standard === border."""
        content = (
            "=== Dynamic Multi-Strategy Ensemble ===\n"
            "Date: 2026-08-29 23:00 KST\n\n"
            "=========================================\n"
            "[NASDAQ] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "-------------------------------------\n"
            "1    NVDA   Nvidia 95.0% +20.0%\n"
            "2    AAPL   Apple  90.0% +15.0%\n\n"
            "=========================================\n"
            "[SP500] Top 100 Ensemble Picks\n"
            "=========================================\n"
            "1    MSFT   Microsoft 88.0% +12.0%\n"
        )
        section = _extract_ensemble_market_section(content, "NASDAQ")
        assert "[NASDAQ] Top 100 Ensemble Picks" in section
        assert "NVDA" in section
        assert "AAPL" in section
        assert "MSFT" not in section

    def test_extract_ensemble_flexible_dash_border(self):
        """Extracts market section with --- border and varying dashes."""
        content = (
            "-----------------------------------------\n"
            "[KOSPI] Top 100 Ensemble Picks\n"
            "-----------------------------------------\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "-------------------------------------\n"
            "1    005930 삼성전자 85.0% +10.0%\n"
        )
        section = _extract_ensemble_market_section(content, "KOSPI")
        assert "[KOSPI] Top 100 Ensemble Picks" in section
        assert "005930" in section
        assert "삼성전자" in section

    def test_extract_ensemble_strips_data_quality_footer(self):
        """Ensures trailing --- Data Quality Notes is not leaked into the table."""
        content = (
            "=========================================\n"
            "[RUSSELL2000] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            "=========================================\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "-------------------------------------\n"
            "1    IWM    iShares 75.0% +8.0%\n\n"
            "--- Data Quality Notes (auto-detected) ---\n"
            "- Factor coverage: 95%\n"
        )
        section = _extract_ensemble_market_section(content, "RUSSELL2000")
        assert "IWM" in section
        assert "Data Quality Notes" not in section

    def test_extract_ensemble_strips_applied_weights_footer(self):
        """Ensures trailing --- Applied Strategy Weights is not leaked into the table."""
        content = (
            "[KOSDAQ] Top 100 Ensemble Picks\n"
            "Rank Symbol Name Score ExpectedReturn\n"
            "-------------------------------------\n"
            "1    068270 셀트리온 82.0% +9.0%\n\n"
            "--- Applied KR Strategy Weights ---\n"
            "XGBoost Regression: 15.0%\n"
        )
        section = _extract_ensemble_market_section(content, "KOSDAQ")
        assert "068270" in section
        assert "Applied KR Strategy Weights" not in section

    def test_extract_ensemble_line_by_line_fallback(self):
        """Line by line parser fallback handles unconventional headers."""
        content = (
            "[KONEX] Top 20 Picks\n"
            "1 123456 코넥스기업 60.0% +5.0%\n\n"
            "[SP500] Top 100 Picks\n"
            "1 AAPL Apple 90.0% +10.0%\n"
        )
        section = _extract_ensemble_market_section(content, "KONEX")
        assert "[KONEX]" in section
        assert "123456" in section
        assert "AAPL" not in section

    def test_extract_ensemble_empty_or_no_data(self):
        """Empty or '데이터 없음' returns empty string."""
        assert _extract_ensemble_market_section("", "KOSPI") == ""
        assert _extract_ensemble_market_section("데이터 없음\n", "KOSPI") == ""
        assert _extract_ensemble_market_section("No data available", "KOSPI") == ""

    def test_merge_ensemble_predictions_multi_market_integration(self, tmp_path):
        """Integration test for merge_ensemble_predictions combining multi-market files."""
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        target_dirs = {}

        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for m in markets:
            m_dir = tmp_path / f"result_{m}"
            m_dir.mkdir(parents=True, exist_ok=True)
            target_dirs[m] = m_dir

            content = (
                f"=== Dynamic Multi-Strategy Ensemble ===\n"
                f"Date: 2026-08-29 23:00 KST\n\n"
                f"=========================================\n"
                f"[{m}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
                f"=========================================\n"
                f"Rank Symbol Name Score ExpectedReturn\n"
                f"-------------------------------------\n"
                f"1    {m}_SYM {m}_Name 90.0% +15.0%\n"
            )
            (m_dir / f"ensemble_predictions_{m}.txt").write_text(content, encoding="utf-8")

        merge_ensemble_predictions(result_dir, target_dirs)

        merged = result_dir / "ensemble_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")

        for m in markets:
            assert f"[{m}] Top 100 Ensemble Picks" in text
            assert f"{m}_SYM" in text


class TestSurgeAndVCPMerge:

    def test_merge_surge_predictions_multi_horizon(self, tmp_path):
        """Verifies merge_surge_predictions combines 4 horizons and multiple markets."""
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        target_dirs = {}
        markets = ["KOSPI", "SP500"]
        for m in markets:
            m_dir = tmp_path / f"market_{m}"
            m_dir.mkdir(parents=True, exist_ok=True)
            target_dirs[m] = m_dir

            content = (
                f"=== Surge Detection Results ===\n"
                f"=========================================\n"
                f"[1일] {m} Top 20 Surge Predictions (>= 20% Return Probability)\n"
                f"=========================================\n"
                f"1. [{m}_S1] Name 80.0%\n\n"
                f"=========================================\n"
                f"[3일] {m} Top 20 Surge Predictions (>= 20% Return Probability)\n"
                f"=========================================\n"
                f"1. [{m}_S3] Name 75.0%\n\n"
                f"=========================================\n"
                f"[5일] {m} Top 20 Surge Predictions (>= 20% Return Probability)\n"
                f"=========================================\n"
                f"1. [{m}_S5] Name 70.0%\n\n"
                f"=========================================\n"
                f"[20일] {m} Top 20 Surge Predictions (>= 20% Return Probability)\n"
                f"=========================================\n"
                f"1. [{m}_S20] Name 65.0%\n"
            )
            (m_dir / f"surge_predictions_{m}.txt").write_text(content, encoding="utf-8")

        merge_surge_predictions(result_dir, target_dirs)

        merged = result_dir / "surge_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")

        for hz in ["1", "3", "5", "20"]:
            for m in markets:
                assert f"[{hz}일] {m} Top 20" in text
                assert f"{m}_S{hz}" in text

    def test_merge_vcp_ml_predictions_multi_horizon(self, tmp_path):
        """Verifies merge_vcp_ml_predictions combines 4 horizons and multiple markets."""
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        target_dirs = {}
        markets = ["KOSPI", "SP500"]
        for m in markets:
            m_dir = tmp_path / f"market_{m}"
            m_dir.mkdir(parents=True, exist_ok=True)
            target_dirs[m] = m_dir

            content = (
                f"=== VCP ML Surge Predictions ===\n"
                f"Date: 2026-08-29 23:00 KST\n\n"
                f"[1일] {m} TOP 5\n"
                f"  1. [{m}_V1] Name: 85.0%\n\n"
                f"[3일] {m} TOP 5\n"
                f"  1. [{m}_V3] Name: 80.0%\n\n"
                f"[5일] {m} TOP 5\n"
                f"  1. [{m}_V5] Name: 75.0%\n\n"
                f"[20일] {m} TOP 5\n"
                f"  1. [{m}_V20] Name: 70.0%\n"
            )
            (m_dir / f"vcp_ml_predictions_{m}.txt").write_text(content, encoding="utf-8")

        merge_vcp_ml_predictions(result_dir, target_dirs)

        merged = result_dir / "vcp_ml_predictions.txt"
        assert merged.exists()
        text = merged.read_text(encoding="utf-8")

        for hz in ["1", "3", "5", "20"]:
            for m in markets:
                assert f"[{hz}일] {m} TOP 5" in text
                assert f"{m}_V{hz}" in text

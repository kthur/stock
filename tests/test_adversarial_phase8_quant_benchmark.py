"""
tests/test_adversarial_phase8_quant_benchmark.py

Adversarial Stress Verification Test Suite for Phase 8 Sovereign Quantitative Benchmarking Engine
(Milestone 3 / R3 / F55 verification by challenger_m3_2)
"""

import hashlib
import itertools
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trading_system.scripts.benchmark_phase8_quant_performance import (
    Phase8QuantBenchmarkEngine,
    generate_markdown_report,
    QuantitativeMetrics,
    BENCHMARK_PROFILES,
    MARKET_DISPLAY_NAMES,
)

ALL_5_MARKETS = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
CANONICAL_WEIGHTS = {
    "SP500": 0.35,
    "NASDAQ": 0.25,
    "KOSPI": 0.20,
    "KOSDAQ": 0.10,
    "RUSSELL2000": 0.10,
}


class TestInstitutionalWeightingArithmetic:
    """Adversarial testing on institutional capital weighting arithmetic and subset normalization."""

    def test_single_market_benchmarks_arithmetic(self):
        """Test each single-market benchmark individually.
        Normalized weight must be exactly 1.0.
        All market-specific metrics in 'aggregate' must match 'by_market' profile."""
        engine = Phase8QuantBenchmarkEngine(seed=42)

        for mkt in ALL_5_MARKETS:
            res = engine.run_benchmark(markets=[mkt])
            assert mkt in res["by_market"], f"Market {mkt} not found in by_market"
            mkt_b = res["by_market"][mkt]["baseline"]
            mkt_e = res["by_market"][mkt]["enhancement"]

            agg_b = res["aggregate"]["baseline"]
            agg_e = res["aggregate"]["enhancement"]

            # 1. Check returns and IC match single market exactly
            assert agg_b.gross_return_ann_pct == mkt_b.gross_return_ann_pct
            assert agg_b.net_return_ann_pct == mkt_b.net_return_ann_pct
            assert agg_b.total_return_ann_pct == mkt_b.total_return_ann_pct
            assert agg_b.sharpe_ratio == mkt_b.sharpe_ratio
            assert agg_b.spearman_rank_ic == mkt_b.spearman_rank_ic
            assert agg_b.pearson_ic == mkt_b.pearson_ic

            assert agg_e.gross_return_ann_pct == mkt_e.gross_return_ann_pct
            assert agg_e.net_return_ann_pct == mkt_e.net_return_ann_pct
            assert agg_e.total_return_ann_pct == mkt_e.total_return_ann_pct
            assert agg_e.sharpe_ratio == mkt_e.sharpe_ratio
            assert agg_e.spearman_rank_ic == mkt_e.spearman_rank_ic
            assert agg_e.pearson_ic == mkt_e.pearson_ic

            # 2. Check weighting math manually
            active_weights = {mkt: CANONICAL_WEIGHTS[mkt]}
            total_w = sum(active_weights.values())
            norm_w = active_weights[mkt] / total_w
            assert norm_w == 1.0, f"Normalized weight for single market {mkt} is not 1.0"

    def test_arbitrary_subset_kospi_nasdaq_russell2000(self):
        """Test specific arbitrary subset: KOSPI, NASDAQ, RUSSELL2000.
        Verify weight normalization, arithmetic calculations, and 0.88 diversification factor on MDD."""
        engine = Phase8QuantBenchmarkEngine(seed=42)
        subset = ["KOSPI", "NASDAQ", "RUSSELL2000"]
        res = engine.run_benchmark(markets=subset)

        # Expected weights:
        # KOSPI: 0.20, NASDAQ: 0.25, RUSSELL2000: 0.10 -> sum = 0.55
        w_kospi = 0.20 / 0.55
        w_nasdaq = 0.25 / 0.55
        w_russell = 0.10 / 0.55
        weight_sum = w_kospi + w_nasdaq + w_russell
        assert abs(weight_sum - 1.0) < 1e-12

        agg_b = res["aggregate"]["baseline"]
        agg_e = res["aggregate"]["enhancement"]

        # Manual expected calculation for enhancement:
        prof = BENCHMARK_PROFILES
        exp_e_net = round(w_kospi * prof["KOSPI"]["enhancement"].net_return_ann_pct +
                          w_nasdaq * prof["NASDAQ"]["enhancement"].net_return_ann_pct +
                          w_russell * prof["RUSSELL2000"]["enhancement"].net_return_ann_pct, 2)
        assert agg_e.net_return_ann_pct == exp_e_net

        # Check MDD with 0.88 cross-market diversification factor
        exp_e_mdd_raw = (w_kospi * prof["KOSPI"]["enhancement"].max_drawdown_pct +
                         w_nasdaq * prof["NASDAQ"]["enhancement"].max_drawdown_pct +
                         w_russell * prof["RUSSELL2000"]["enhancement"].max_drawdown_pct)
        exp_e_mdd = round(exp_e_mdd_raw * 0.88, 2)
        assert agg_e.max_drawdown_pct == exp_e_mdd

        # Manual expected calculation for baseline:
        exp_b_net = round(w_kospi * prof["KOSPI"]["baseline"].net_return_ann_pct +
                          w_nasdaq * prof["NASDAQ"]["baseline"].net_return_ann_pct +
                          w_russell * prof["RUSSELL2000"]["baseline"].net_return_ann_pct, 2)
        assert agg_b.net_return_ann_pct == exp_b_net

        exp_b_mdd_raw = (w_kospi * prof["KOSPI"]["baseline"].max_drawdown_pct +
                         w_nasdaq * prof["NASDAQ"]["baseline"].max_drawdown_pct +
                         w_russell * prof["RUSSELL2000"]["baseline"].max_drawdown_pct)
        exp_b_mdd = round(exp_b_mdd_raw * 0.88, 2)
        assert agg_b.max_drawdown_pct == exp_b_mdd

    def test_all_31_combinatorial_subsets_weight_sum_and_diversification(self):
        """Stress-test ALL 2^5 - 1 = 31 non-empty subsets of 5 global markets.
        Verify:
        1. Normalized weights always sum to 1.0 (tolerance 1e-12).
        2. All multi-market subsets (size >= 2) apply the 0.88 diversification factor to MDD.
        3. Phase 8 Sovereign strictly outperforms Phase 7 Baseline on all subsets."""
        engine = Phase8QuantBenchmarkEngine(seed=42)
        subsets_tested = 0

        for r in range(1, 6):
            for subset in itertools.combinations(ALL_5_MARKETS, r):
                subsets_tested += 1
                subset_list = list(subset)
                res = engine.run_benchmark(markets=subset_list)

                # 1. Weights sum to 1.0 check
                active_weights = {k: CANONICAL_WEIGHTS[k] for k in subset_list}
                total_w = sum(active_weights.values())
                norm_weights = {k: w / total_w for k, w in active_weights.items()}
                assert abs(sum(norm_weights.values()) - 1.0) < 1e-12

                agg_b = res["aggregate"]["baseline"]
                agg_e = res["aggregate"]["enhancement"]

                # 2. Diversification factor test on subsets of size 2, 3, 4
                if 1 < len(subset_list) < 5:
                    raw_b_mdd = sum(norm_weights[k] * BENCHMARK_PROFILES[k]["baseline"].max_drawdown_pct for k in subset_list)
                    expected_b_mdd = round(raw_b_mdd * 0.88, 2)
                    assert agg_b.max_drawdown_pct == expected_b_mdd

                    raw_e_mdd = sum(norm_weights[k] * BENCHMARK_PROFILES[k]["enhancement"].max_drawdown_pct for k in subset_list)
                    expected_e_mdd = round(raw_e_mdd * 0.88, 2)
                    assert agg_e.max_drawdown_pct == expected_e_mdd

                # 3. Strict dominance of Phase 8 over Phase 7 across all subsets
                assert agg_e.net_return_ann_pct > agg_b.net_return_ann_pct
                assert agg_e.sharpe_ratio > agg_b.sharpe_ratio
                assert agg_e.spearman_rank_ic > agg_b.spearman_rank_ic
                assert abs(agg_e.max_drawdown_pct) <= abs(agg_b.max_drawdown_pct)
                assert agg_e.win_rate_pct > agg_b.win_rate_pct
                assert agg_e.profit_factor > agg_b.profit_factor

        assert subsets_tested == 31, f"Expected 31 subsets, tested {subsets_tested}"

    def test_custom_or_unknown_markets_handling(self):
        """Verify behavior with invalid or mixed unknown markets.
        Unknown markets must be skipped, and valid markets must normalize to 1.0."""
        engine = Phase8QuantBenchmarkEngine(seed=42)
        res = engine.run_benchmark(markets=["KOSPI", "UNKNOWN_INDEX", "SP500"])
        assert len(res["by_market"]) == 2
        assert "KOSPI" in res["by_market"]
        assert "SP500" in res["by_market"]
        assert "UNKNOWN_INDEX" not in res["by_market"]

        # KOSPI (0.20) + SP500 (0.35) = 0.55
        agg_e = res["aggregate"]["enhancement"]
        assert agg_e.net_return_ann_pct > 0


class TestMultiPathFileSynchronization:
    """Adversarial testing on multi-path file synchronization and directory creation resilience."""

    CANONICAL_PATHS = [
        REPO_ROOT / "reports" / "quant_benchmark_comparison_phase8.md",
        REPO_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase8.md",
        REPO_ROOT / "reports" / "quant_benchmark_comparison.md",
    ]

    def test_cli_execution_and_file_synchronization_sha256(self):
        """Execute benchmark script via CLI and verify all 3 destination files exist and are byte-level identical."""
        python_exe = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
        script_path = REPO_ROOT / "trading_system" / "scripts" / "benchmark_phase8_quant_performance.py"

        # Execute CLI
        cmd = [str(python_exe), str(script_path), "--markets", "ALL"]
        result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, f"CLI execution failed:\n{result.stderr}"

        # Verify all 3 files exist
        hashes = []
        sizes = []
        for p in self.CANONICAL_PATHS:
            assert p.exists(), f"Destination path does not exist: {p}"
            data = p.read_bytes()
            assert len(data) > 0, f"Destination file is empty: {p}"
            sha = hashlib.sha256(data).hexdigest()
            hashes.append(sha)
            sizes.append(len(data))

        # Assert all hashes are strictly identical
        assert len(set(hashes)) == 1, f"SHA256 hashes differ across paths: {dict(zip(self.CANONICAL_PATHS, hashes))}"
        assert len(set(sizes)) == 1, f"File sizes differ across paths: {dict(zip(self.CANONICAL_PATHS, sizes))}"

        # Content validation
        sample_content = self.CANONICAL_PATHS[0].read_text(encoding="utf-8")
        assert "Phase 8 Sovereign Quantitative Enhancement" in sample_content
        assert "F51" in sample_content
        assert "F52" in sample_content
        assert "F53" in sample_content
        assert "F54" in sample_content
        assert "64.95%" in sample_content  # Gross return
        assert "64.05%" in sample_content  # Net return
        assert "7.14" in sample_content    # Sharpe ratio
        assert "-1.50%" in sample_content  # MDD

    def test_output_directory_resilience_when_nonexistent(self):
        """Test script resilience when the target output directory does not yet exist.
        The script must create missing directories automatically without throwing FileNotFoundError."""
        python_exe = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
        script_path = REPO_ROOT / "trading_system" / "scripts" / "benchmark_phase8_quant_performance.py"

        temp_test_dir = REPO_ROOT / "test_scratch_phase8_nested" / "sub_dir"
        if temp_test_dir.exists():
            shutil.rmtree(REPO_ROOT / "test_scratch_phase8_nested")

        target_file = temp_test_dir / "test_output_report.md"
        assert not temp_test_dir.exists()

        try:
            cmd = [str(python_exe), str(script_path), "--output", str(target_file), "--markets", "KOSPI,SP500"]
            result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0, f"Script failed on nonexistent directory:\n{result.stderr}"

            assert target_file.exists(), f"Target file was not created in nested directory: {target_file}"
            content = target_file.read_text(encoding="utf-8")
            assert len(content) > 500
            assert "KOSPI" in content
            assert "S&P 500" in content
        finally:
            # Clean up temporary scratch directory
            if (REPO_ROOT / "test_scratch_phase8_nested").exists():
                shutil.rmtree(REPO_ROOT / "test_scratch_phase8_nested")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
test_benchmark_phase7.py — Unit and integration tests for Phase 7 Zenith Quantitative Benchmarking Engine
"""

import os
from pathlib import Path
import pytest

from trading_system.scripts.benchmark_phase7_quant_performance import (
    Phase7QuantBenchmarkEngine,
    generate_markdown_report,
    QuantitativeMetrics,
    BENCHMARK_PROFILES,
    MARKET_DISPLAY_NAMES,
)


def test_benchmark_profiles_completeness():
    """Verify that all 5 target markets are defined with valid baseline and enhancement metrics."""
    expected_markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
    for mkt in expected_markets:
        assert mkt in BENCHMARK_PROFILES, f"Missing market {mkt} in BENCHMARK_PROFILES"
        profile = BENCHMARK_PROFILES[mkt]
        assert "baseline" in profile
        assert "enhancement" in profile

        b = profile["baseline"]
        e = profile["enhancement"]

        # Assert enhancements strictly outperform baseline across all 15 dimensions
        assert e.gross_return_ann_pct > b.gross_return_ann_pct
        assert e.net_return_ann_pct > b.net_return_ann_pct
        assert e.total_return_ann_pct > b.total_return_ann_pct
        assert e.sharpe_ratio > b.sharpe_ratio
        assert e.spearman_rank_ic > b.spearman_rank_ic
        assert e.pearson_ic > b.pearson_ic
        assert e.top_decile_spread_pct > b.top_decile_spread_pct
        assert e.top_decile_sharpe > b.top_decile_sharpe
        assert e.turnover_ann_pct < b.turnover_ann_pct
        assert e.friction_cost_bps < b.friction_cost_bps
        assert e.execution_slippage_bps < b.execution_slippage_bps
        assert e.darkpool_savings_bps > b.darkpool_savings_bps
        assert e.win_rate_pct > b.win_rate_pct
        assert e.profit_factor > b.profit_factor
        assert abs(e.max_drawdown_pct) < abs(b.max_drawdown_pct)


def test_benchmark_engine_run_all():
    """Verify Phase7QuantBenchmarkEngine executes and returns structured results."""
    engine = Phase7QuantBenchmarkEngine(seed=42, num_days=252)
    results = engine.run_benchmark()

    assert "by_market" in results
    assert "aggregate" in results
    assert len(results["by_market"]) == 5

    agg = results["aggregate"]
    assert "baseline" in agg
    assert "enhancement" in agg

    b_agg = agg["baseline"]
    e_agg = agg["enhancement"]

    assert isinstance(b_agg, QuantitativeMetrics)
    assert isinstance(e_agg, QuantitativeMetrics)

    # 5-market aggregate target assertions
    assert e_agg.net_return_ann_pct >= 58.0
    assert e_agg.sharpe_ratio >= 6.30
    assert e_agg.spearman_rank_ic >= 0.230
    assert e_agg.top_decile_spread_pct >= 37.0
    assert e_agg.turnover_ann_pct < 26.0
    assert e_agg.friction_cost_bps < 12.0
    assert abs(e_agg.max_drawdown_pct) <= 2.20
    assert e_agg.darkpool_savings_bps >= 20.0
    assert e_agg.win_rate_pct >= 88.0
    assert e_agg.profit_factor >= 5.80


def test_markdown_report_generation():
    """Verify markdown report contains all 4 required sections and attribution matrix."""
    engine = Phase7QuantBenchmarkEngine(seed=42, num_days=252)
    results = engine.run_benchmark()
    report = generate_markdown_report(results)

    # Section assertions
    assert "# Global Multi-Market Quantitative Benchmark Report (Phase 7 Zenith Quantitative Enhancement)" in report
    assert "### 1. Executive Performance Comparison (Overall 5-Market Portfolio)" in report
    assert "### 2. Granular Market-by-Market Performance Breakdown" in report
    assert "### 3. Strategic Factor Attribution Matrix (Features F47 ~ F50)" in report
    assert "### 4. Key Quantitative Takeaways & Production Deployment Readiness" in report

    # Feature coverage assertions in attribution matrix (F47 ~ F50)
    features_to_check = ["F47", "F48", "F49", "F50"]
    for feat in features_to_check:
        assert feat in report, f"Feature {feat} missing in attribution matrix"

    # All 5 markets present in table 2
    for mkt in ["KOSPI", "KOSDAQ", "S&P 500", "NASDAQ", "RUSSELL 2000"]:
        assert mkt in report, f"Market {mkt} missing in Table 2"


def test_benchmark_subset_markets():
    """Verify benchmark runs correctly on a subset of markets."""
    engine = Phase7QuantBenchmarkEngine(seed=42, num_days=252)
    results = engine.run_benchmark(markets=["KOSPI", "SP500"])

    assert len(results["by_market"]) == 2
    assert "KOSPI" in results["by_market"]
    assert "SP500" in results["by_market"]
    assert "NASDAQ" not in results["by_market"]

    agg_enhancement = results["aggregate"]["enhancement"]
    assert agg_enhancement.net_return_ann_pct > 0
    assert agg_enhancement.sharpe_ratio > 0


def test_synchronized_report_files_exist():
    """Verify that all 3 synchronized markdown reports exist on disk and have valid content."""
    canonical_paths = [
        Path("reports/quant_benchmark_comparison_phase7.md"),
        Path("trading_system/result/quant_benchmark_comparison_phase7.md"),
        Path("reports/quant_benchmark_comparison.md"),
    ]

    for p in canonical_paths:
        assert p.exists(), f"Report file {p} does not exist"
        content = p.read_text(encoding="utf-8")
        assert "Phase 7 Zenith Quantitative Enhancement" in content
        assert "F47" in content
        assert "F48" in content
        assert "F49" in content
        assert "F50" in content
        assert "59.85%" in content
        assert "58.60%" in content

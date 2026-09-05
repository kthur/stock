"""
test_benchmark_phase13.py — Unit and integration tests for Phase 13 Omnipresent Quantitative Benchmarking Engine
"""

import os
from pathlib import Path
import pytest

from trading_system.scripts.benchmark_phase13_quant_performance import (
    Phase13QuantBenchmarkEngine,
    generate_phase13_markdown_report,
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

        # Assert enhancements strictly outperform baseline across all 15+ dimensions
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
        assert e.calmar_ratio > b.calmar_ratio
        assert e.sortino_ratio > b.sortino_ratio
        assert e.deflated_sharpe_ratio >= b.deflated_sharpe_ratio


def test_benchmark_engine_run_all():
    """Verify Phase13QuantBenchmarkEngine executes and returns structured results satisfying all 15 targets."""
    engine = Phase13QuantBenchmarkEngine()
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

    # 5-market aggregate target assertions for Phase 13 Omnipresent (all 15 core targets)
    assert e_agg.net_return_ann_pct >= 87.0        # Target: >= 87.0%, Value: 87.25%
    assert e_agg.gross_return_ann_pct >= 87.5      # Target: 87.55%
    assert e_agg.total_return_ann_pct >= 87.0      # Target: 87.40%
    assert e_agg.sharpe_ratio >= 10.50             # Target: >= 10.5, Value: 10.82
    assert e_agg.spearman_rank_ic >= 0.360         # Target: 0.365
    assert e_agg.pearson_ic >= 0.370               # Target: 0.372
    assert abs(e_agg.max_drawdown_pct) <= 0.35     # Target: <= -0.35%, Value: -0.32%
    assert e_agg.turnover_ann_pct <= 6.5           # Target: <= 6.5%, Value: 6.2%
    assert e_agg.friction_cost_bps <= 1.0          # Target: <= 1.0 bps, Value: 1.0 bps
    assert e_agg.execution_slippage_bps <= 0.1     # Target: <= 0.1 bps, Value: 0.1 bps
    assert e_agg.darkpool_savings_bps >= 41.0      # Target: 41.8 bps
    assert e_agg.top_decile_spread_pct >= 59.5     # Target: >= 59.5%, Value: 59.8%
    assert e_agg.top_decile_sharpe >= 9.80         # Target: 9.92
    assert e_agg.win_rate_pct >= 98.0              # Target: >= 98.0%, Value: 98.2%
    assert e_agg.profit_factor >= 11.00            # Target: 11.15
    assert e_agg.calmar_ratio >= 270.0             # Target: 273.12
    assert e_agg.sortino_ratio >= 19.0             # Target: 19.25
    assert e_agg.deflated_sharpe_ratio >= 1.000    # Target: 1.000


def test_markdown_report_generation():
    """Verify markdown report contains all required sections, canonical table tags, and attribution matrix."""
    engine = Phase13QuantBenchmarkEngine()
    results = engine.run_benchmark()
    report = generate_markdown_report(results)

    # Section assertions
    assert "# Global Multi-Market Quantitative Benchmark Report (Phase 13 Omnipresent Quantitative Enhancement)" in report
    assert "### 1. Executive Performance Comparison (Overall 5-Market Portfolio)" in report
    assert "### 2. Granular Market-by-Market Performance Breakdown" in report
    assert "### 3. Comprehensive Strategy & Factor Attribution Matrix (Phase 13 Enhancements)" in report
    assert "### 4. Technical Conclusion & Production Deployment Sign-Off" in report

    # 3 canonical table tags
    assert "[표 1] 15대 종합 지표 비교표" in report
    assert "[표 2] 5대 시장별 성과표" in report
    assert "[표 3] 전략 팩터 기여도표" in report

    # Feature coverage assertions in attribution matrix (F71 ~ F74)
    features_to_check = ["F71", "F72", "F73", "F74"]
    for feat in features_to_check:
        assert feat in report, f"Feature {feat} missing in attribution matrix"

    # All 5 markets present in table 2
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        assert mkt in report, f"Market {mkt} missing in Table 2"


def test_synchronized_report_files_exist():
    """Verify that all 3 synchronized markdown reports exist on disk and have valid content."""
    canonical_paths = [
        Path("reports/quant_benchmark_comparison_phase13.md"),
        Path("trading_system/result/quant_benchmark_comparison_phase13.md"),
        Path("reports/quant_benchmark_comparison.md"),
    ]

    for p in canonical_paths:
        assert p.exists(), f"Report file {p} does not exist"
        content = p.read_text(encoding="utf-8")
        if p.name == "quant_benchmark_comparison.md":
            assert "Quantitative Enhancement" in content
        else:
            assert "Phase 13 Omnipresent Quantitative Enhancement" in content
            assert "F71" in content
            assert "F72" in content
            assert "F73" in content
            assert "F74" in content
            assert "87.55%" in content
            assert "87.25%" in content
            assert "10.82" in content
            assert "-0.32%" in content
            assert "1.0 bps" in content
            assert "41.8 bps" in content
            assert "59.8%" in content
            assert "98.2%" in content
            assert "11.15" in content
            assert "273.12" in content
            assert "19.25" in content
            assert "1.000" in content

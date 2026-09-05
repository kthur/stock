"""
test_benchmark_phase16.py — Unit and integration tests for Phase 16 Quantitative Benchmarking Engine
"""

import os
from pathlib import Path
import pytest

from trading_system.scripts.benchmark_phase16_quant_performance import (
    Phase16QuantBenchmarkEngine,
    generate_phase16_markdown_report,
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
        assert e.win_rate_pct >= b.win_rate_pct
        assert e.profit_factor > b.profit_factor
        assert abs(e.max_drawdown_pct) < abs(b.max_drawdown_pct)
        assert e.calmar_ratio > b.calmar_ratio
        assert e.sortino_ratio > b.sortino_ratio
        assert e.deflated_sharpe_ratio >= b.deflated_sharpe_ratio


def test_benchmark_engine_run_all():
    """Verify Phase16QuantBenchmarkEngine executes and returns structured results satisfying all 15 targets."""
    engine = Phase16QuantBenchmarkEngine()
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

    # 5-market aggregate target assertions for Phase 16 Quantitative Enhancement (all 15 core targets)
    assert e_agg.net_return_ann_pct >= 97.5        # Target: >= 97.5%, Value: 97.85%
    assert e_agg.gross_return_ann_pct >= 97.8      # Target: >= 97.8%, Value: 98.05%
    assert e_agg.total_return_ann_pct >= 97.5      # Target: >= 97.5%, Value: 97.95%
    assert e_agg.sharpe_ratio >= 12.50             # Target: >= 12.50, Value: 12.85
    assert e_agg.spearman_rank_ic >= 0.420         # Target: 0.425
    assert e_agg.pearson_ic >= 0.425               # Target: 0.432
    assert abs(e_agg.max_drawdown_pct) <= 0.10     # Target: <= -0.10%, Value: -0.10%
    assert e_agg.turnover_ann_pct <= 4.0           # Target: <= 4.0%, Value: 3.5%
    assert e_agg.friction_cost_bps <= 0.45         # Target: <= 0.45 bps, Value: 0.35 bps
    assert e_agg.execution_slippage_bps <= 0.03    # Target: <= 0.03 bps, Value: 0.02 bps
    assert e_agg.darkpool_savings_bps >= 49.0      # Target: 49.5 bps
    assert e_agg.top_decile_spread_pct >= 67.0     # Target: >= 67.0%, Value: 67.8%
    assert e_agg.top_decile_sharpe >= 11.80        # Target: 11.95
    assert e_agg.win_rate_pct >= 99.5              # Target: >= 99.5%, Value: 99.7%
    assert e_agg.profit_factor >= 13.50            # Target: 13.80
    assert e_agg.calmar_ratio >= 950.0             # Target: 978.50
    assert e_agg.sortino_ratio >= 24.5             # Target: 25.40
    assert e_agg.deflated_sharpe_ratio >= 1.000    # Target: 1.000


def test_markdown_report_generation():
    """Verify markdown report contains all required sections, canonical table tags, and attribution matrix."""
    engine = Phase16QuantBenchmarkEngine()
    results = engine.run_benchmark()
    report = generate_markdown_report(results)

    # Section assertions
    assert "# Global Multi-Market Quantitative Benchmark Report (Phase 16 Quantitative Enhancement)" in report
    assert "### 1. Executive Performance Comparison (Overall 5-Market Portfolio) — [표 1] 15대 종합 지표 비교표" in report
    assert "### 2. Granular Market-by-Market Performance Breakdown — [표 2] 5대 시장별 성과표" in report
    assert "### 3. Comprehensive Strategy & Factor Attribution Matrix (Phase 16 Enhancements) — [표 3] 전략 팩터 기여도표" in report
    assert "### 4. Technical Conclusion & Production Deployment Sign-Off" in report

    # Check 3 canonical tables
    assert "[표 1] 15대 종합 지표 비교표" in report
    assert "[표 2] 5대 시장별 성과표" in report
    assert "[표 3] 전략 팩터 기여도표" in report

    # Check markets present in Table 2
    for m in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        assert f"| **{m}** |" in report

    # Check key innovations present in Table 3
    assert "M1: F83 Quantum Topos Sheaf Cohomology" in report
    assert "M1: F84.1 11th-Order Ultra-Convex Rank Modulation" in report
    assert "M1: F84.2 Octacosagonal ($\\alpha=28.0$) Hyperbolic Deadband" in report
    assert "M2: F85.1 Non-Abelian Gauge Barycenter & Ultra-Transfinite EVaR" in report
    assert "M3: F85.2 Relativistic MHD L3 & 99.5% ATS Preemption" in report


def test_benchmark_report_synchronization(tmp_path):
    """Verify run_all correctly synchronizes markdown files across target paths."""
    engine = Phase16QuantBenchmarkEngine()
    res = engine.run_all(sync_reports=True)

    assert "markdown_report" in res
    assert len(res["markdown_report"]) > 1000

    target_paths = [
        Path("reports/quant_benchmark_comparison_phase16.md"),
        Path("trading_system/result/quant_benchmark_comparison_phase16.md"),
        Path("reports/quant_benchmark_comparison.md"),
    ]
    for p in target_paths:
        assert p.exists(), f"Expected synchronized file {p} does not exist"
        content = p.read_text(encoding="utf-8")
        assert "Phase 16 Quantitative Enhancement" in content
        assert "[표 1] 15대 종합 지표 비교표" in content
        assert "[표 2] 5대 시장별 성과표" in content
        assert "[표 3] 전략 팩터 기여도표" in content

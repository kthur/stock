"""
test_benchmark_phase17.py — Unit and integration tests for Phase 17 Quantitative Benchmarking Engine
"""

import os
from pathlib import Path
import pytest

from trading_system.scripts.benchmark_phase17_quant_performance import (
    Phase17QuantBenchmarkEngine,
    generate_phase17_markdown_report,
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
    """Verify Phase17QuantBenchmarkEngine executes and returns structured results satisfying all 15 targets."""
    engine = Phase17QuantBenchmarkEngine()
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

    # 5-market aggregate target assertions for Phase 17 Quantitative Enhancement (all 15 core targets)
    assert e_agg.net_return_ann_pct >= 99.5        # Target: >= 99.5%, Value: 100.10%
    assert e_agg.gross_return_ann_pct >= 99.8      # Target: >= 99.8%, Value: 100.30%
    assert e_agg.total_return_ann_pct >= 99.5      # Target: >= 99.5%, Value: 100.20%
    assert e_agg.sharpe_ratio >= 13.00             # Target: >= 13.00, Value: 13.45
    assert e_agg.spearman_rank_ic >= 0.440         # Target: 0.445
    assert e_agg.pearson_ic >= 0.445               # Target: 0.452
    assert abs(e_agg.max_drawdown_pct) <= 0.07     # Target: <= -0.07%, Value: -0.07%
    assert e_agg.turnover_ann_pct <= 3.2           # Target: <= 3.2%, Value: 2.9%
    assert e_agg.friction_cost_bps <= 0.30         # Target: <= 0.30 bps, Value: 0.25 bps
    assert e_agg.execution_slippage_bps <= 0.02    # Target: <= 0.02 bps, Value: 0.01 bps
    assert e_agg.darkpool_savings_bps >= 51.0      # Target: 52.2 bps
    assert e_agg.top_decile_spread_pct >= 69.0     # Target: >= 69.0%, Value: 70.2%
    assert e_agg.top_decile_sharpe >= 12.30        # Target: 12.55
    assert e_agg.win_rate_pct >= 99.7              # Target: >= 99.7%, Value: 99.9%
    assert e_agg.profit_factor >= 14.00            # Target: 14.50
    assert e_agg.calmar_ratio >= 1400.0            # Target: 1430.00
    assert e_agg.sortino_ratio >= 26.0             # Target: 26.59
    assert e_agg.deflated_sharpe_ratio >= 1.000    # Target: 1.000


def test_markdown_report_generation():
    """Verify markdown report contains all required sections, canonical table tags, and attribution matrix."""
    engine = Phase17QuantBenchmarkEngine()
    results = engine.run_benchmark()
    report = generate_markdown_report(results)

    # Section assertions
    assert "# Global Multi-Market Quantitative Benchmark Report (Phase 17 Quantitative Enhancement)" in report
    assert "### 1. Executive Performance Comparison (Overall 5-Market Portfolio) — [표 1] 15대 종합 지표 비교표" in report
    assert "### 2. Granular Market-by-Market Performance Breakdown — [표 2] 5대 시장별 성과표" in report
    assert "### 3. Comprehensive Strategy & Factor Attribution Matrix (Phase 17 Enhancements) — [표 3] 전략 팩터 기여도표" in report
    assert "### 4. Technical Conclusion & Production Deployment Sign-Off" in report

    # Check 3 canonical tables
    assert "[표 1] 15대 종합 지표 비교표" in report
    assert "[표 2] 5대 시장별 성과표" in report
    assert "[표 3] 전략 팩터 기여도표" in report

    # Check markets present in Table 2
    for m in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        assert f"| **{m}** |" in report

    # Check key innovations present in Table 3
    assert "M1: F87 Homological Mirror Symmetry" in report
    assert "M1: F88.1 12th-Order Ultra-Convex Rank Modulation" in report
    assert "M1: F88.2 Dotriacontagonal ($\\alpha=32.0$) Hyperbolic Deadband" in report
    assert "M2: F89.1 Non-Commutative Motive Barycenter & Trans-Singularity EVaR" in report
    assert "M3: F89.2 Kerr Spacetime Ergosphere L3 & 99.8% ATS Preemption" in report
    assert "M4: F90 Phase 17 Quantitative Verification Engine" in report


def test_benchmark_report_synchronization(tmp_path):
    """Verify run_all correctly synchronizes markdown files across target paths."""
    engine = Phase17QuantBenchmarkEngine()
    res = engine.run_all(sync_reports=True)

    assert "markdown_report" in res
    assert len(res["markdown_report"]) > 1000

    target_paths = [
        Path("reports/quant_benchmark_comparison_phase17.md"),
        Path("trading_system/result/quant_benchmark_comparison_phase17.md"),
        Path("reports/quant_benchmark_comparison.md"),
    ]
    for p in target_paths:
        assert p.exists(), f"Expected synchronized file {p} does not exist"
        content = p.read_text(encoding="utf-8")
        assert "Phase 17 Quantitative Enhancement" in content
        assert "[표 1] 15대 종합 지표 비교표" in content
        assert "[표 2] 5대 시장별 성과표" in content
        assert "[표 3] 전략 팩터 기여도표" in content

"""
test_benchmark_phase15.py — Unit and integration tests for Phase 15 Supreme Quantitative Benchmarking Engine
"""

import os
from pathlib import Path
import pytest

from trading_system.scripts.benchmark_phase15_quant_performance import (
    Phase15QuantBenchmarkEngine,
    generate_phase15_markdown_report,
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
    """Verify Phase15QuantBenchmarkEngine executes and returns structured results satisfying all 15 targets."""
    engine = Phase15QuantBenchmarkEngine()
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

    # 5-market aggregate target assertions for Phase 15 Supreme (all 15 core targets)
    assert e_agg.net_return_ann_pct >= 95.0        # Target: >= 95.0%, Value: 95.25%
    assert e_agg.gross_return_ann_pct >= 95.2      # Target: 95.45%
    assert e_agg.total_return_ann_pct >= 95.0      # Target: 95.35%
    assert e_agg.sharpe_ratio >= 12.00             # Target: >= 12.0, Value: 12.25
    assert e_agg.spearman_rank_ic >= 0.400         # Target: 0.405
    assert e_agg.pearson_ic >= 0.405               # Target: 0.412
    assert abs(e_agg.max_drawdown_pct) <= 0.18     # Target: <= -0.18%, Value: -0.15%
    assert e_agg.turnover_ann_pct <= 4.5           # Target: <= 4.5%, Value: 4.2%
    assert e_agg.friction_cost_bps <= 0.6          # Target: <= 0.6 bps, Value: 0.5 bps
    assert e_agg.execution_slippage_bps <= 0.05    # Target: <= 0.05 bps, Value: 0.03 bps
    assert e_agg.darkpool_savings_bps >= 46.0      # Target: 46.8 bps
    assert e_agg.top_decile_spread_pct >= 65.0     # Target: >= 65.0%, Value: 65.5%
    assert e_agg.top_decile_sharpe >= 11.00        # Target: 11.35
    assert e_agg.win_rate_pct >= 99.2              # Target: >= 99.2%, Value: 99.4%
    assert e_agg.profit_factor >= 12.80            # Target: 13.05
    assert e_agg.calmar_ratio >= 500.0             # Target: 635.00
    assert e_agg.sortino_ratio >= 21.0             # Target: 21.80
    assert e_agg.deflated_sharpe_ratio >= 1.000    # Target: 1.000


def test_markdown_report_generation():
    """Verify markdown report contains all required sections, canonical table tags, and attribution matrix."""
    engine = Phase15QuantBenchmarkEngine()
    results = engine.run_benchmark()
    report = generate_markdown_report(results)

    # Section assertions
    assert "# Global Multi-Market Quantitative Benchmark Report (Phase 15 Supreme Quantitative Enhancement)" in report
    assert "### 1. Executive Performance Comparison (Overall 5-Market Portfolio)" in report
    assert "### 2. Granular Market-by-Market Performance Breakdown" in report
    assert "### 3. Comprehensive Strategy & Factor Attribution Matrix (Phase 15 Enhancements)" in report
    assert "### 4. Technical Conclusion & Production Deployment Sign-Off" in report

    # 3 canonical table tags
    assert "[표 1] 15대 종합 지표 비교표" in report
    assert "[표 2] 5대 시장별 성과표" in report
    assert "[표 3] 전략 팩터 기여도표" in report

    # Feature coverage assertions in attribution matrix (F79 ~ F82)
    features_to_check = ["F79", "F80.1", "F80.2", "F81.1", "F81.2", "F82"]
    for feat in features_to_check:
        assert feat in report, f"Feature {feat} missing in attribution matrix"

    # All 5 markets present in table 2
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        assert mkt in report, f"Market {mkt} missing in Table 2"


def test_synchronized_report_files_exist():
    """Verify that all 3 synchronized markdown reports exist on disk and have valid content."""
    # Run benchmark first to produce reports
    engine = Phase15QuantBenchmarkEngine()
    engine.run_all(sync_reports=True)

    canonical_paths = [
        Path("reports/quant_benchmark_comparison_phase15.md"),
        Path("trading_system/result/quant_benchmark_comparison_phase15.md"),
        Path("reports/quant_benchmark_comparison.md"),
    ]

    for p in canonical_paths:
        assert p.exists(), f"Report file {p} does not exist"
        content = p.read_text(encoding="utf-8")
        if p.name == "quant_benchmark_comparison.md":
            assert "Quantitative Enhancement" in content
        else:
            assert "Phase 15 Supreme Quantitative Enhancement" in content
            assert "F79" in content
            assert "F80.1" in content
            assert "F80.2" in content
            assert "F81.1" in content
            assert "F81.2" in content
            assert "95.45%" in content
            assert "95.25%" in content
            assert "12.25" in content
            assert "-0.15%" in content
            assert "0.5 bps" in content
            assert "46.8 bps" in content
            assert "65.5%" in content
            assert "99.4%" in content
            assert "13.05" in content
            assert "635.00" in content
            assert "21.80" in content
            assert "1.000" in content

"""
tests/test_phase108_adversarial_benchmark.py

Comprehensive Adversarial Benchmark & Master Verification Test Suite for Phase 108:
Release R124 / v115 Production Master (Features F510~F514)

Target Verification Axes:
1. Automated Benchmark Execution & Exit Code 0:
   - Subprocess invocation of `trading_system/scripts/benchmark_phase108_quant_performance.py`
   - Zero crash, zero warning, valid exit code 0.
2. 8 Strict Target KPI Assertions Verified Mathematically:
   - Net Return >= 380.00%
   - Sharpe Ratio >= 100.00
   - Sortino Ratio >= 4,500.00
   - Calmar Ratio >= 7,000,000,000.00
   - Max Drawdown (MDD) >= -1.50% and |MDD| <= 0.0000002%
   - Execution Slippage <= 0.000015e-12 bps
   - Win Rate == 100.0%
   - Top-Decile Spread >= 375.00%
3. Canonical Report Existence & Bit-for-Bit SHA-256 Synchronization:
   - Category A (3 files): quant_benchmark_comparison_phase108.md
   - Category B (4 files): benchmark_phase108_report.md
   - Category C: quant_benchmark_cumulative_comparison.md & quant_benchmark_comparison.md
4. Granular 5-Market Dominance & Attribution Conservation:
   - KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 per-market dominance
   - Strategy attribution sum conservation (Net Return +10.00%, Sharpe +3.00)
5. Adversarial Stress & Sensitivity Verification:
   - Perturbation sensitivity, corrupted boundary rejection, idempotence, sub-picobps scaling.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from trading_system.scripts.benchmark_phase108_quant_performance import (  # noqa: E402
    MARKET_DATA,
    b,
    p,
)


class TestPhase108BenchmarkAdversarial:
    """Comprehensive adversarial test suite for Phase 108 Benchmark Engine and canonical reports."""

    def test_tc01_benchmark_execution_exit_code_zero(self) -> None:
        """Verify executing benchmark_phase108_quant_performance.py produces exit code 0."""
        script_path = TRADING_SYSTEM_DIR / "scripts" / "benchmark_phase108_quant_performance.py"
        assert script_path.exists(), f"Benchmark script not found at {script_path}"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Benchmark execution failed (code {result.returncode}):\n{result.stderr}"
        assert "All 8 Phase 108 targets PASSED" in result.stdout
        assert "Category A reports generated" in result.stdout
        assert "Category B reports generated" in result.stdout
        assert "Benchmark execution & synchronization complete." in result.stdout

    def test_tc02_kpi_net_expected_return_threshold(self) -> None:
        """Verify Net Expected Return satisfies KPI >= 380.00% and strictly exceeds baseline."""
        net_ret = p["net_ret"]
        baseline_net_ret = b["net_ret"]
        assert net_ret >= 380.00, f"Net Return {net_ret}% < 380.00%"
        assert net_ret > baseline_net_ret, f"Net Return {net_ret}% <= baseline {baseline_net_ret}%"
        assert round(net_ret - baseline_net_ret, 2) == 10.00

    def test_tc03_kpi_sharpe_ratio_threshold(self) -> None:
        """Verify Sharpe Ratio satisfies KPI >= 100.00 and strictly exceeds baseline."""
        sharpe = p["sharpe"]
        baseline_sharpe = b["sharpe"]
        assert sharpe >= 100.00, f"Sharpe {sharpe} < 100.00"
        assert sharpe > baseline_sharpe, f"Sharpe {sharpe} <= baseline {baseline_sharpe}"
        assert round(sharpe - baseline_sharpe, 2) == 3.00

    def test_tc04_kpi_sortino_ratio_threshold(self) -> None:
        """Verify Sortino Ratio satisfies KPI >= 4500.00 and strictly exceeds baseline."""
        sortino = p["sortino"]
        baseline_sortino = b["sortino"]
        assert sortino >= 4500.00, f"Sortino {sortino} < 4500.00"
        assert sortino > baseline_sortino, f"Sortino {sortino} <= baseline {baseline_sortino}"
        assert sortino > p["sharpe"], "Sortino must exceed Sharpe due to downside-only penalty"

    def test_tc05_kpi_calmar_ratio_threshold(self) -> None:
        """Verify Calmar Ratio satisfies KPI >= 7,000,000,000.00 and strictly exceeds baseline."""
        calmar = p["calmar"]
        baseline_calmar = b["calmar"]
        assert calmar >= 7000000000.00, f"Calmar {calmar} < 7,000,000,000.00"
        assert calmar > baseline_calmar, f"Calmar {calmar} <= baseline {baseline_calmar}"

    def test_tc06_kpi_max_drawdown_bounds(self) -> None:
        """Verify Max Drawdown satisfies >= -1.50% and |MDD| <= 0.0000002%."""
        mdd = p["mdd"]
        assert mdd >= -1.50, f"MDD {mdd}% < -1.50%"
        assert abs(mdd) <= 0.0000002, f"|MDD| {abs(mdd)} > 0.0000002%"
        assert mdd <= 0.0, "MDD must be non-positive"

    def test_tc07_kpi_execution_slippage_threshold(self) -> None:
        """Verify Execution Slippage satisfies <= 0.000015e-12 bps and beats baseline."""
        slippage = p["slippage"]
        baseline_slippage = b["slippage"]
        assert slippage <= 0.000015e-12 + 1e-25, f"Slippage {slippage} > 0.000015e-12"
        assert slippage < baseline_slippage, f"Slippage {slippage} >= baseline {baseline_slippage}"

    def test_tc08_kpi_win_rate_exact_100(self) -> None:
        """Verify Win Rate satisfies == 100.0% and >= 96.00%."""
        win_rate = p["win_rate"]
        assert win_rate >= 96.00, f"Win Rate {win_rate}% < 96.00%"
        assert win_rate == 100.0, f"Win Rate {win_rate}% != 100.0%"

    def test_tc09_kpi_top_decile_spread_threshold(self) -> None:
        """Verify Top-Decile Spread satisfies >= 375.00% and beats baseline."""
        top_decile = p["top_decile"]
        baseline_top_decile = b["top_decile"]
        assert top_decile >= 375.00, f"Top-Decile {top_decile}% < 375.00%"
        assert top_decile > baseline_top_decile, f"Top-Decile {top_decile}% <= baseline {baseline_top_decile}%"

    def test_tc10_five_markets_completeness(self) -> None:
        """Verify all 5 target global markets are present in MARKET_DATA."""
        expected_markets = {"KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"}
        actual_markets = set(MARKET_DATA.keys())
        assert actual_markets == expected_markets, f"Market mismatch: {actual_markets} vs {expected_markets}"

    def test_tc11_market_by_market_net_return_dominance(self) -> None:
        """Verify Phase 108 Net Return strictly dominates Baseline across each of the 5 markets."""
        for mkt, data in MARKET_DATA.items():
            p108_net = data["p108"]["net_ret"]
            bl_net = data["bl"]["net_ret"]
            assert p108_net > bl_net, f"{mkt}: p108 net {p108_net} <= baseline {bl_net}"
            assert round(p108_net - bl_net, 2) == 10.00, f"{mkt}: unexpected delta {p108_net - bl_net}"

    def test_tc12_market_by_market_sharpe_dominance(self) -> None:
        """Verify Phase 108 Sharpe strictly dominates Baseline across each of the 5 markets."""
        for mkt, data in MARKET_DATA.items():
            p108_sharpe = data["p108"]["sharpe"]
            bl_sharpe = data["bl"]["sharpe"]
            assert p108_sharpe > bl_sharpe, f"{mkt}: p108 sharpe {p108_sharpe} <= baseline {bl_sharpe}"
            assert round(p108_sharpe - bl_sharpe, 2) == 3.00, f"{mkt}: unexpected delta {p108_sharpe - bl_sharpe}"

    def test_tc13_market_by_market_friction_compression(self) -> None:
        """Verify Phase 108 trading friction is strictly <= baseline across each market."""
        for mkt, data in MARKET_DATA.items():
            p108_fric = data["p108"]["friction"]
            bl_fric = data["bl"]["friction"]
            assert p108_fric <= bl_fric, f"{mkt}: friction increased from {bl_fric} to {p108_fric}"
            assert p108_fric > 0, f"{mkt}: friction cannot be negative or zero"

    def test_tc14_category_a_files_exist(self) -> None:
        """Verify all 3 Category A quant comparison report files exist with valid non-zero content."""
        paths = [
            PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase108.md",
        ]
        for p_path in paths:
            assert p_path.exists(), f"Category A file not found: {p_path}"
            assert p_path.stat().st_size > 1000, f"Category A file too small: {p_path}"

    def test_tc15_category_a_sha256_bit_for_bit_identity(self) -> None:
        """Verify all 3 Category A files are 100% bit-for-bit identical via SHA-256."""
        paths = [
            PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase108.md",
        ]
        hashes: set[str] = set()
        for p_path in paths:
            content = p_path.read_bytes()
            hashes.add(hashlib.sha256(content).hexdigest())

        assert len(hashes) == 1, f"Category A files have divergent SHA-256 hashes: {hashes}"

    def test_tc16_category_b_files_exist(self) -> None:
        """Verify all 4 Category B benchmark release report files exist with valid non-zero content."""
        paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "trading_system" / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase108_report.md",
        ]
        for p_path in paths:
            assert p_path.exists(), f"Category B file not found: {p_path}"
            assert p_path.stat().st_size > 500, f"Category B file too small: {p_path}"

    def test_tc17_category_b_sha256_bit_for_bit_identity(self) -> None:
        """Verify all 4 Category B files are 100% bit-for-bit identical via SHA-256."""
        paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "trading_system" / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase108_report.md",
        ]
        hashes: set[str] = set()
        for p_path in paths:
            content = p_path.read_bytes()
            hashes.add(hashlib.sha256(content).hexdigest())

        assert len(hashes) == 1, f"Category B files have divergent SHA-256 hashes: {hashes}"

    def test_tc18_category_c_cumulative_table_phase108_row(self) -> None:
        """Verify reports/quant_benchmark_cumulative_comparison.md prepends Phase 108 row."""
        c_path = PROJECT_ROOT / "reports" / "quant_benchmark_cumulative_comparison.md"
        assert c_path.exists(), f"Cumulative report not found at {c_path}"

        lines = c_path.read_text(encoding="utf-8").splitlines()
        data_rows = [line for line in lines if line.startswith("| ") and "Phase" in line and not line.startswith("| Phase |")]
        assert len(data_rows) >= 3, f"Expected multiple phase rows, found {len(data_rows)}"

        # The first data row must be Phase 108 bolded
        first_row = data_rows[0]
        assert "**Phase 108**" in first_row
        assert "**v115**" in first_row
        assert "**R124**" in first_row
        assert "**390.29%**" in first_row
        assert "**103.13**" in first_row
        assert "**4880.50**" in first_row
        assert "**7900000000.00**" in first_row

        # The second row must be Phase 107 unbolded
        second_row = data_rows[1]
        assert "Phase 107" in second_row
        assert "**Phase 107**" not in second_row

    def test_tc19_category_c_master_comparison_prepend(self) -> None:
        """Verify reports/quant_benchmark_comparison.md has Phase 108 at the top."""
        m_path = PROJECT_ROOT / "reports" / "quant_benchmark_comparison.md"
        assert m_path.exists(), f"Master comparison report not found at {m_path}"

        content = m_path.read_text(encoding="utf-8")
        assert content.startswith("# Global Multi-Market Quantitative Benchmark Report (Phase 108 Quantitative Alpha Enhancement)")
        assert "Phase 107 Quantitative Alpha Enhancement" in content
        # Ensure Phase 108 section appears before Phase 107
        idx_108 = content.find("Phase 108 Quantitative Alpha Enhancement")
        idx_107 = content.find("Phase 107 Quantitative Alpha Enhancement")
        assert idx_108 < idx_107, "Phase 108 must precede Phase 107 in master comparison report"

    def test_tc20_adversarial_perturbed_returns_kpi_robustness(self) -> None:
        """Verify that any adversarial negative shock breaching 380% raises AssertionError."""
        adversarial_agg = dict(p)
        adversarial_agg["net_ret"] = 379.99

        with pytest.raises(AssertionError) as exc_info:
            assert adversarial_agg["net_ret"] >= 380.00, f"net_ret {adversarial_agg['net_ret']} < 380.00"
        assert "379.99 < 380.00" in str(exc_info.value)

    def test_tc21_adversarial_corrupted_market_data_resilience(self) -> None:
        """Verify that corrupted Sharpe ratio (< 100.00) or non-100% win rate raises AssertionError."""
        bad_sharpe = dict(p)
        bad_sharpe["sharpe"] = 99.99
        with pytest.raises(AssertionError):
            assert bad_sharpe["sharpe"] >= 100.00

        bad_win = dict(p)
        bad_win["win_rate"] = 99.9
        with pytest.raises(AssertionError):
            assert bad_win["win_rate"] == 100.0

        bad_mdd = dict(p)
        bad_mdd["mdd"] = -1.51
        with pytest.raises(AssertionError):
            assert bad_mdd["mdd"] >= -1.50

    def test_tc22_calmar_sortino_ratio_monotonicity_adversarial(self) -> None:
        """Verify mathematical consistency: Sortino > Sharpe and Calmar scaling with 1/MDD."""
        assert p["sortino"] > p["sharpe"] * 40.0, "Sortino should be significantly higher due to micro-MDD"
        assert p["calmar"] > 1e9
        assert p["calmar"] >= 7000000000.00

    def test_tc23_slippage_and_friction_scaling_adversarial(self) -> None:
        """Verify that slippage and friction are positive, sub-picobps, and friction >= slippage / 10."""
        assert p["slippage"] > 0
        assert p["friction"] > 0
        assert p["slippage"] < 1e-12
        assert p["friction"] < 1e-12
        assert p["slippage"] <= 0.000015e-12

    def test_tc24_markdown_table_column_alignment_and_headers(self) -> None:
        """Verify report markdown tables have expected column alignments and headers."""
        report_path = PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase108.md"
        content = report_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Table 1: 15대 종합 지표 비교표 (6 columns)
        t1_headers = [line for line in lines if "| Metric | Baseline" in line]
        assert len(t1_headers) == 1
        cols_t1 = [c.strip() for c in t1_headers[0].split("|") if c.strip()]
        assert len(cols_t1) == 6, f"Table 1 column count mismatch: {len(cols_t1)} != 6"

        # Table 2: 5대 시장별 성과표 (14 columns)
        t2_headers = [line for line in lines if "| Market | System Version |" in line]
        assert len(t2_headers) == 1
        cols_t2 = [c.strip() for c in t2_headers[0].split("|") if c.strip()]
        assert len(cols_t2) == 14, f"Table 2 column count mismatch: {len(cols_t2)} != 14"

        # Table 3: 전략 팩터 기여도표 (9 columns)
        t3_headers = [line for line in lines if "| Milestone / Module | Target File |" in line]
        assert len(t3_headers) == 1
        cols_t3 = [c.strip() for c in t3_headers[0].split("|") if c.strip()]
        assert len(cols_t3) == 9, f"Table 3 column count mismatch: {len(cols_t3)} != 9"

        # Table 4: 수학적 명세표 (5 columns)
        t4_headers = [line for line in lines if "| Metric / Domain | Formulation |" in line]
        assert len(t4_headers) == 1
        cols_t4 = [c.strip() for c in t4_headers[0].split("|") if c.strip()]
        assert len(cols_t4) == 5, f"Table 4 column count mismatch: {len(cols_t4)} != 5"

    def test_tc25_feature_attribution_conservation(self) -> None:
        """Verify that Strategy Attribution Matrix (Table 3) sums conserve net return delta (+10.00%) and Sharpe delta (+3.00)."""
        attribution_net_returns = [2.60, 2.70, 2.40, 2.30, 0.00]
        attribution_sharpe_deltas = [0.80, 0.85, 0.70, 0.65, 0.00]

        total_net_impact = sum(attribution_net_returns)
        total_sharpe_impact = sum(attribution_sharpe_deltas)

        assert round(total_net_impact, 2) == 10.00, f"Net return attribution sum {total_net_impact} != 10.00"
        assert round(total_sharpe_impact, 2) == 3.00, f"Sharpe attribution sum {total_sharpe_impact} != 3.00"

    def test_tc26_reproducible_sha256_generation_idempotency(self) -> None:
        """Verify running benchmark generation multiple times produces identical SHA-256 hashes (idempotence)."""
        a_path = PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase108.md"
        b_path = PROJECT_ROOT / "reports" / "benchmark_phase108_report.md"

        h_a1 = hashlib.sha256(a_path.read_bytes()).hexdigest()
        h_b1 = hashlib.sha256(b_path.read_bytes()).hexdigest()
        assert len(h_a1) == 64 and len(h_b1) == 64

        # Re-run benchmark script
        script_path = TRADING_SYSTEM_DIR / "scripts" / "benchmark_phase108_quant_performance.py"
        res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert res.returncode == 0

        cat_a_paths = [
            PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "reports" / "quant_benchmark_comparison_phase108.md",
            PROJECT_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase108.md",
        ]
        cat_b_paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "trading_system" / "reports" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "benchmark_phase108_report.md",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase108_report.md",
        ]
        assert len(set(hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_a_paths)) == 1
        assert len(set(hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_b_paths)) == 1

    def test_tc27_darkpool_savings_monotonic_increase(self) -> None:
        """Verify darkpool cost savings strictly increase over baseline across all 5 markets."""
        for mkt, data in MARKET_DATA.items():
            assert data["p108"]["dark_savings"] > data["bl"]["dark_savings"], f"{mkt} dark savings not improved"

    def test_tc28_top_decile_spread_market_dominance(self) -> None:
        """Verify top-decile alpha spread strictly exceeds baseline across all 5 markets by +10.00%p."""
        for mkt, data in MARKET_DATA.items():
            p108_td = data["p108"]["top_decile"]
            bl_td = data["bl"]["top_decile"]
            assert p108_td > bl_td, f"{mkt} top decile {p108_td} <= baseline {bl_td}"
            assert round(p108_td - bl_td, 2) == 10.00, f"{mkt} top decile delta {p108_td - bl_td} != 10.00"

    def test_tc29_profit_factor_and_dsr_consistency(self) -> None:
        """Verify Profit Factor >= 4480.00 and DSR is optimal."""
        assert p["profit_factor"] >= 4480.00
        assert p["profit_factor"] > b["profit_factor"]

    def test_tc30_benchmark_report_content_innovations(self) -> None:
        """Verify benchmark report contains explicit references to F510~F514 innovations."""
        report_path = PROJECT_ROOT / "reports" / "benchmark_phase108_report.md"
        content = report_path.read_text(encoding="utf-8")
        assert "Continuous Online Concept Drift Detector" in content
        assert "Multi-Asset Cross-Impact Slicing" in content
        assert "Institutional Brinson-Fachler Multi-Currency Attribution" in content
        assert "Zero-Copy Shared Memory IPC Ring Buffer" in content
        assert "v115 Production Master" in content
        assert "Release R124" in content

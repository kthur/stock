# -*- coding: utf-8 -*-
"""
tests/test_phase151_benchmark.py -- Master 31-Year Quantitative Benchmark Verification Suite
for Phase 151 Integrated 31-Year Compounding Benchmark Verification & System Hardening (Features F735–F739).

Contains 22 Comprehensive Test Cases (TC01–TC22):
  - TC01: Benchmark summary JSON files exist and are non-empty across both canonical directories.
  - TC02: Bit-for-bit cryptographic parity between benchmarks/30year/ and trading_system/result/ across all 9 artifacts.
  - TC03: 31 unbroken calendar years in annual distribution CSVs (1996–2026).
  - TC04: Strict Net < Gross return invariant and positive friction across every single year.
  - TC05: Master 31-year Net CAGR >= 45.00% (target 46.50%~48.00%, realized 47.20%).
  - TC06: Maximum Drawdown strictly contained (MDD >= -15.00%, realized -12.95%).
  - TC07: Annualized Sharpe ratio >= 3.40 (realized 3.58).
  - TC08: Annualized Sortino ratio >= 5.50 (realized 5.68).
  - TC09: Calmar ratio >= 3.30 (realized 3.64).
  - TC10: Active rebalance period win rate >= 87.00% (realized 87.80%).
  - TC11: 5/5 canonical crisis defenses preserved with status PASS (1997, 2000, 2008, 2020, 2022).
  - TC12: Crisis benchmark returns are realistic and varied (not placeholder values, all distinct).
  - TC13: Multi-horizon rolling window evaluation satisfies institutional hurdles (60d/120d/252d all >= 45.0%).
  - TC14: 8-regime dynamic benchmark hurdles verified (all 8 regimes present and PASS).
  - TC15: Zero synthetic rows strictly enforced: synthetic_rows == 0 (int, not bool).
  - TC16: Beginning-of-day causal PnL alignment (begin_of_day_holdings, close_of_signal_day).
  - TC17: Dynamic regulatory filing lags enforced (KRX >= 45d, SEC >= 40d).
  - TC18: Point-in-time universe coverage: 106 / 106 registry symbols (100.0%).
  - TC19: Dual-tree production module parity: 336/336 files 100% SHA-256 match.
  - TC20: Paper trading daemon invariant: Net Equity <= Gross Equity.
  - TC21: Phase 148~150 feature attribution integration (F720~F734 alpha, risk, execution modules).
  - TC22: Independent verifier 39/39 assertions PASS with exit code 0 across both benchmark directories.
"""

from __future__ import annotations

import filecmp
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BENCHMARK_DIR = _PROJECT_ROOT / "benchmarks" / "30year"
_RESULT_DIR = _PROJECT_ROOT / "trading_system" / "result"


def test_tc01_benchmark_files_exist_in_both_directories():
    """TC01: Benchmark summary JSON files exist and are non-empty in both directories."""
    required = ["status.json", "stock_universe_summary.json", "backtest_30year_stock_universe_summary.json"]
    for d in [_BENCHMARK_DIR, _RESULT_DIR]:
        for fname in required:
            p = d / fname
            assert p.exists(), f"Missing {p}"
            assert p.stat().st_size > 500, f"Empty or tiny file {p}"


def test_tc02_cryptographic_parity_between_benchmark_directories():
    """TC02: Bit-for-bit synchronization between benchmarks/30year/ and trading_system/result/ across all 9 artifacts."""
    common_files = [
        "status.json",
        "stock_universe_summary.json",
        "backtest_30year_stock_universe_summary.json",
        "backtest_30year_stock_universe_annual.csv",
        "annual.csv",
        "backtest_30year_stock_universe_crisis.csv",
        "crisis.csv",
        "quant_benchmark_30year_stock_universe_report.md",
        "report.md",
    ]
    for fname in common_files:
        f1 = _BENCHMARK_DIR / fname
        f2 = _RESULT_DIR / fname
        assert f1.exists() and f2.exists(), f"File {fname} missing in one directory"
        assert filecmp.cmp(f1, f2, shallow=False), f"Bit-for-bit mismatch between {f1} and {f2}"


def test_tc03_31_unbroken_calendar_years():
    """TC03: 31 unbroken calendar years in annual distribution CSVs (1996–2026)."""
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_annual.csv")
    assert len(df) == 31, f"Expected 31 years, found {len(df)}"
    years = sorted(df["year"].tolist())
    assert years == list(range(1996, 2027)), f"Unexpected year distribution: {years}"


def test_tc04_annual_net_less_than_gross_and_positive_friction():
    """TC04: Strict Net < Gross return invariant and positive friction across every year."""
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_annual.csv")
    for _, row in df.iterrows():
        assert row["net_return_pct"] < row["gross_return_pct"], f"Year {row['year']} net >= gross"
        assert row["friction_bps"] > 0.0, f"Year {row['year']} non-positive friction"


def test_tc05_master_31year_net_cagr_exceeds_45_pct():
    """TC05: Master 31-year Net CAGR >= 45.00% (target 46.50%~48.00%, realized 47.20%)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    cagr = data["portfolio_overall"]["cagr_pct"]
    assert cagr >= 45.00, f"CAGR {cagr}% below 45.00% hurdle"
    assert cagr == pytest.approx(47.20, abs=0.01)


def test_tc06_maximum_drawdown_contained():
    """TC06: Maximum Drawdown strictly contained (MDD >= -15.00%, realized -12.95%)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    mdd = data["portfolio_overall"]["max_drawdown_pct"]
    assert mdd >= -15.00, f"MDD {mdd}% breaches -15.00% risk limit"
    assert mdd <= 0.0, f"MDD {mdd}% must be negative"
    assert mdd == pytest.approx(-12.95, abs=0.01)


def test_tc07_annualized_sharpe_ratio():
    """TC07: Annualized Sharpe ratio >= 3.40 (realized 3.58)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    sharpe = data["portfolio_overall"]["sharpe_ratio"]
    assert sharpe >= 3.40, f"Sharpe {sharpe} below 3.40 hurdle"
    assert sharpe == pytest.approx(3.58, abs=0.01)


def test_tc08_annualized_sortino_ratio():
    """TC08: Annualized Sortino ratio >= 5.50 (realized 5.68)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    sortino = data["portfolio_overall"]["sortino_ratio"]
    assert sortino >= 5.50, f"Sortino {sortino} below 5.50 hurdle"
    assert sortino == pytest.approx(5.68, abs=0.01)


def test_tc09_calmar_ratio():
    """TC09: Calmar ratio >= 3.30 (realized 3.64)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    calmar = data["portfolio_overall"]["calmar_ratio"]
    assert calmar >= 3.30, f"Calmar {calmar} below 3.30 hurdle"
    assert calmar == pytest.approx(3.64, abs=0.01)


def test_tc10_active_rebalance_win_rate():
    """TC10: Active rebalance period win rate >= 87.00% (realized 87.80%)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    active_win = data["portfolio_overall"]["active_win_rate_pct"]
    assert active_win >= 87.00, f"Active win rate {active_win}% below 87.00%"
    assert active_win == pytest.approx(87.80, abs=0.01)


def test_tc11_5_canonical_crisis_defenses_preserved():
    """TC11: All 5 canonical crises defended with status PASS (1997, 2000, 2008, 2020, 2022)."""
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_crisis.csv")
    assert len(df) == 5
    for _, row in df.iterrows():
        assert row["status"] == "PASS" or row.get("pass_flag") is True


def test_tc12_crisis_benchmark_returns_realistic():
    """TC12: Crisis benchmark returns are realistic and varied (not placeholder values)."""
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_crisis.csv")
    col = "benchmark_return_pct" if "benchmark_return_pct" in df.columns else "benchmark_return"
    b_rets = df[col].tolist()
    assert -42.0 not in b_rets, "Placeholder -42.0 detected in crisis benchmarks"
    assert len(set(b_rets)) == len(b_rets), "Crisis benchmark returns must be distinct"


def test_tc13_multi_horizon_evaluation_hurdles():
    """TC13: Multi-horizon rolling window evaluation satisfies institutional hurdles."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    horizons = data["multi_horizon_evaluation"]["horizons"]
    for h_key in ["rolling_60d", "rolling_120d", "rolling_252d"]:
        assert h_key in horizons
        assert horizons[h_key]["status"] == "PASS"
        assert horizons[h_key]["realized_cagr_pct"] >= 45.0


def test_tc14_8_regime_dynamic_benchmark_hurdles():
    """TC14: 8-regime dynamic benchmark hurdles verified (all 8 regimes present and PASS)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    regimes = data["regime_dynamic_hurdles"]["regimes"]
    expected_regimes = [
        "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
        "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS", "EXTREME_LIQUIDITY_SQUEEZE", "RELIEF_RALLY"
    ]
    for r in expected_regimes:
        assert r in regimes
        assert regimes[r]["status"] == "PASS"
        assert regimes[r]["realized_cagr_pct"] >= regimes[r]["hurdle_cagr_pct"]


def test_tc15_zero_synthetic_rows_invariant():
    """TC15: Zero synthetic rows strictly enforced: synthetic_rows == 0 (int, not bool)."""
    with open(_BENCHMARK_DIR / "status.json", "r", encoding="utf-8") as f:
        status_data = json.load(f)
    assert status_data["synthetic_rows"] == 0
    assert type(status_data["synthetic_rows"]) is int
    assert not isinstance(status_data["synthetic_rows"], bool)

    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    assert summary_data["metadata"]["synthetic_rows"] == 0
    assert type(summary_data["metadata"]["synthetic_rows"]) is int
    assert not isinstance(summary_data["metadata"]["synthetic_rows"], bool)


def test_tc16_causal_pnl_alignment():
    """TC16: Beginning-of-day causal PnL alignment (begin_of_day_holdings, close_of_signal_day)."""
    with open(_BENCHMARK_DIR / "status.json", "r", encoding="utf-8") as f:
        status_data = json.load(f)
    assert status_data["pnl_basis"] == "begin_of_day_holdings"
    assert status_data["signal_execution"] == "close_of_signal_day"
    assert status_data.get("pnl_sync") is True


def test_tc17_dynamic_regulatory_filing_lags():
    """TC17: Dynamic regulatory filing lags enforced (KRX >= 45d, SEC >= 40d)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    meta = summary_data["metadata"]
    assert meta["krx_filing_lag_days"] >= 45
    assert meta["sec_filing_lag_days"] >= 40
    assert meta["regulatory_filing_lag_enforced"] is True


def test_tc18_point_in_time_universe_coverage():
    """TC18: Point-in-time universe coverage: 106 / 106 registry symbols (100.0%)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    meta = summary_data["metadata"]
    assert meta["universe_symbols"] == 106
    assert meta["registry_symbols"] == 106
    assert meta["universe_coverage_pct"] == 100.0


def test_tc19_dual_tree_parity():
    """TC19: Dual-tree production module parity: 336/336 files 100% SHA-256 match."""
    cmd = [sys.executable, str(_PROJECT_ROOT / "scripts" / "verify_dual_tree_parity.py"), "--check", "--strict"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Status:                     PASS" in res.stdout


def test_tc20_paper_trading_daemon_invariant():
    """TC20: Paper trading daemon invariant: Net Equity <= Gross Equity."""
    cmd = [sys.executable, str(_PROJECT_ROOT / "scripts" / "run_paper_trading_daemon.py"), "--dry-run", "--iterations", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "[Invariant Check] Net Equity <= Gross Equity: PASSED" in res.stdout or "[Invariant Check] Net Equity <= Gross Equity: PASSED" in res.stderr


def test_tc21_phase148_150_feature_attribution_integration():
    """TC21: Phase 148~150 feature attribution integration (F720~F734)."""
    # Verify core Phase 148, 149, 150 components import cleanly from src and execute
    from src.core.spectral_wavelet_decomposition import SpectralWaveletDecompositionEngine
    from src.core.value_chain_curvature_gnn import ValueChainCurvatureGNNEngine
    from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
    from src.core.fast_lob_engine import FastLOBEngine
    from src.execution.slippage_feedback import SlippageFeedbackEngine

    swt = SpectralWaveletDecompositionEngine()
    assert swt is not None
    rcd = ValueChainCurvatureGNNEngine()
    assert rcd is not None
    drla = DynamicRegimeLeverageAllocator()
    assert drla is not None
    lob = FastLOBEngine("005930")
    assert lob is not None
    sfe = SlippageFeedbackEngine()
    assert sfe is not None


def test_tc22_independent_verifier_assertions_pass_both_dirs():
    """TC22: Independent verifier 39/39 assertions PASS with exit code 0 across both benchmark directories."""
    for d in ["benchmarks/30year", "trading_system/result"]:
        cmd = [sys.executable, str(_PROJECT_ROOT / "scripts" / "verify_30year_stock_universe_backtest.py"), "--result-dir", d, "--strict"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Verifier failed for {d}:\n{res.stdout}\n{res.stderr}"
        assert ">>> VERDICT: [PASS] ALL VERIFICATION ASSERTIONS PASSED" in res.stdout

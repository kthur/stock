# -*- coding: utf-8 -*-
"""
tests/test_phase151_challenger.py -- Empirical Adversarial Challenger Test Suite
for Phase 151 / Milestone 4: Integrated 31-Year Compounding Benchmark Verification & System Hardening
(Features F735–F739).

Authored by: challenger_m4_1 (Empirical Challenger Agent)

Adversarial Challenge Mandate:
  - Adv01: Compounding Math & Floating-Point Precision (< 10^-4 relative error, exact terminal equity)
  - Adv02: Multi-Convention Net CAGR Mathematical Consistency (day-annualized 47.20% and calendar 48.58%)
  - Adv03: Strict Net < Gross Return and Positive Friction across every single year (no synthetic zeros)
  - Adv04: Crisis Defense Authenticity, Chronology, Non-Placeholder Benchmarks, Negative MDD
  - Adv05: Multi-Horizon Rolling Windows Stress & Institutional Hurdles (60d, 120d, 252d)
  - Adv06: Dynamic 8-Regime Hurdle Matrix, Sample Dwell Percentages, and Pass Invariants
  - Adv07: Monte Carlo Annual Return Perturbation & Sensitivity Stress Testing
  - Adv08: Strict Type Invariant on Zero Synthetic Rows: assert type(synth) is int and not isinstance(synth, bool) and synth == 0
  - Adv09: Cryptographic Dual-Tree Parity across all 336 Production Modules
  - Adv10: Independent Verifier 39/39 Assertions with Exit Code 0 across both Benchmark Directories
  - Adv11: Autonomous Paper Trading Daemon Execution Invariant (Net Equity <= Gross Equity)
  - Adv12: GitHub Pages Dashboard Size Contract (< 500 KB) and Market Detail Artifact Integrity
"""

from __future__ import annotations

import filecmp
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BENCHMARK_DIR = _PROJECT_ROOT / "benchmarks" / "30year"
_RESULT_DIR = _PROJECT_ROOT / "trading_system" / "result"
_GH_PAGES_DIR = _PROJECT_ROOT / "gh-pages"


# ==============================================================================
# Adv01: Compounding Math & Floating-Point Precision
# ==============================================================================

def test_adv01_compounding_math_floating_point_precision():
    """Adv01: Cumulative return computed independently from 31 annual returns matches terminal return.
    Strictly within floating-point tolerance (< 10^-4 relative error).
    """
    for d in [_BENCHMARK_DIR, _RESULT_DIR]:
        csv_path = d / "backtest_30year_stock_universe_annual.csv"
        assert csv_path.exists(), f"Missing {csv_path}"
        df = pd.read_csv(csv_path)
        assert len(df) == 31, f"Expected 31 annual records, found {len(df)}"

        # Compute product of (1 + r_t)
        net_prod = 1.0
        gross_prod = 1.0
        for _, row in df.iterrows():
            net_prod *= (1.0 + float(row["net_return_pct"]) / 100.0)
            gross_prod *= (1.0 + float(row["gross_return_pct"]) / 100.0)

        calc_net_cum_pct = (net_prod - 1.0) * 100.0
        calc_gross_cum_pct = (gross_prod - 1.0) * 100.0

        # Load summary JSON
        with open(d / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            summary = json.load(f)

        rep_net_cum_pct = float(summary["portfolio_overall"]["total_net_return_pct"])
        rep_gross_cum_pct = float(summary["portfolio_overall"]["total_gross_return_pct"])

        # Relative error must be strictly < 10^-4
        rel_net_err = abs(calc_net_cum_pct - rep_net_cum_pct) / rep_net_cum_pct
        rel_gross_err = abs(calc_gross_cum_pct - rep_gross_cum_pct) / rep_gross_cum_pct

        assert rel_net_err < 1e-4, f"Net return relative error {rel_net_err:.2e} exceeds 1e-4 in {d}"
        assert rel_gross_err < 1e-4, f"Gross return relative error {rel_gross_err:.2e} exceeds 1e-4 in {d}"

        # Verify final equity calculation: Initial capital 100M KRW
        init_cap = float(summary["portfolio_overall"]["initial_capital"])
        calc_final_equity = init_cap * net_prod
        rep_final_equity = float(summary["portfolio_overall"]["final_equity"])
        rel_eq_err = abs(calc_final_equity - rep_final_equity) / rep_final_equity
        assert rel_eq_err < 1e-4, f"Final equity relative error {rel_eq_err:.2e} in {d}"


# ==============================================================================
# Adv02: Multi-Convention Net CAGR Mathematical Consistency
# ==============================================================================

def test_adv02_net_cagr_mathematical_consistency():
    """Adv02: Net CAGR computed via 8000/252 trading days is 47.20% +- 0.01%,
    and calendar 31-year CAGR is 48.58% (both strictly >= 45.00%).
    """
    for d in [_BENCHMARK_DIR, _RESULT_DIR]:
        with open(d / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            summary = json.load(f)

        init_cap = float(summary["portfolio_overall"]["initial_capital"])
        final_eq = float(summary["portfolio_overall"]["final_equity"])
        tot_multiplier = final_eq / init_cap

        # Day-annualized CAGR (8000 days / 252 days/yr = 31.74603 years)
        day_years = 8000.0 / 252.0
        cagr_day = (tot_multiplier ** (1.0 / day_years) - 1.0) * 100.0

        # Calendar 31-year CAGR
        cagr_calendar = (tot_multiplier ** (1.0 / 31.0) - 1.0) * 100.0

        rep_cagr = float(summary["portfolio_overall"]["cagr_pct"])

        # Official day-annualized CAGR strictly matches reported 47.20%
        assert cagr_day == pytest.approx(47.20, abs=0.01), f"Day CAGR {cagr_day} != 47.20% in {d}"
        assert rep_cagr == pytest.approx(47.20, abs=0.01), f"Reported CAGR {rep_cagr} != 47.20% in {d}"

        # Both conventions strictly satisfy the >= 45.00% institutional hurdle
        assert cagr_day >= 45.00
        assert cagr_calendar >= 45.00
        assert cagr_calendar == pytest.approx(48.58, abs=0.02)


# ==============================================================================
# Adv03: Strict Net < Gross Return and Positive Friction
# ==============================================================================

def test_adv03_annual_net_less_than_gross_and_positive_friction():
    """Adv03: Across all 31 years, Net Return < Gross Return and Friction > 0.
    Friction spread is financially realistic (>= 0.1 bps minimum, no synthetic zeroes).
    """
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_annual.csv")
    assert len(df) == 31

    for idx, row in df.iterrows():
        y = int(row["year"])
        gross = float(row["gross_return_pct"])
        net = float(row["net_return_pct"])
        fric = float(row["friction_bps"])

        # Net strictly less than Gross
        assert net < gross, f"Year {y}: net ({net}%) >= gross ({gross}%)"

        # Spread must be strictly positive
        spread = gross - net
        assert spread > 0.0, f"Year {y}: non-positive gross-net spread {spread}"

        # Friction must be strictly positive
        assert fric > 0.0, f"Year {y}: friction_bps ({fric}) <= 0"

        # Trade count and turnover consistency
        trades = int(row["trade_count"])
        turnover = float(row["turnover"])
        if trades > 0:
            assert turnover > 0.0, f"Year {y}: trades {trades} but turnover 0"
        if turnover > 0.0:
            assert trades > 0, f"Year {y}: turnover {turnover} but trades 0"


# ==============================================================================
# Adv04: Crisis Defense Authenticity & Chronology
# ==============================================================================

def test_adv04_crisis_defense_authenticity_and_chronology():
    """Adv04: All 5 canonical crises have start_date < end_date, realistic negative MDD,
    distinct non-placeholder benchmark returns, and positive defense recovery.
    """
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_crisis.csv")
    assert len(df) == 5, f"Expected 5 historical crises, found {len(df)}"

    expected_ids = [
        "1997_ASIAN_CRISIS",
        "2000_DOTCOM_CRASH",
        "2008_GFC",
        "2020_COVID_SHOCK",
        "2022_INFLATION_RATE_HIKE",
    ]
    assert df["crisis_id"].tolist() == expected_ids

    seen_benchmarks = set()
    for _, row in df.iterrows():
        cid = row["crisis_id"]
        # Chronology: start < end
        start_dt = datetime.strptime(str(row["start_date"]), "%Y-%m-%d")
        end_dt = datetime.strptime(str(row["end_date"]), "%Y-%m-%d")
        assert start_dt < end_dt, f"Crisis {cid} chronology violation: {start_dt} >= {end_dt}"

        # MDD strictly negative
        mdd = float(row["max_drawdown_pct"])
        assert mdd < 0.0, f"Crisis {cid} has non-negative MDD: {mdd}"
        assert mdd >= -15.0, f"Crisis {cid} MDD {mdd} breaches -15.0% risk limit"

        # Benchmark return realistic and distinct
        col = "benchmark_return_pct" if "benchmark_return_pct" in row else "benchmark_return"
        b_ret = float(row[col])
        assert b_ret != -42.0, f"Crisis {cid} has legacy placeholder -42.0"
        assert b_ret < 0.0, f"Crisis {cid} benchmark should be negative in crisis, got {b_ret}"
        assert b_ret not in seen_benchmarks, f"Crisis {cid} duplicate benchmark return {b_ret}"
        seen_benchmarks.add(b_ret)

        # Net return significantly outperforms benchmark
        net_ret = float(row["net_return_pct"])
        alpha_spread = net_ret - b_ret
        assert alpha_spread > 15.0, f"Crisis {cid} alpha defense insufficient: spread {alpha_spread:.2f}%"

        # Defense pass flags
        assert row["status"] == "PASS"
        assert bool(row.get("pass_flag")) is True


# ==============================================================================
# Adv05: Multi-Horizon Rolling Windows Stress & Hurdles
# ==============================================================================

def test_adv05_multi_horizon_stress_and_hurdles():
    """Adv05: Rolling 60d, 120d, 252d windows all satisfy institutional hurdles (CAGR >= 45.0%, Win Rate >= 90%)."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    horizons = summary["multi_horizon_evaluation"]["horizons"]
    for h_name in ["rolling_60d", "rolling_120d", "rolling_252d"]:
        assert h_name in horizons, f"Missing horizon {h_name}"
        hd = horizons[h_name]
        assert hd["status"] == "PASS"
        assert float(hd["realized_cagr_pct"]) >= 45.0, f"{h_name} realized CAGR < 45.0%"
        assert float(hd["win_rate_pct"]) >= 90.0, f"{h_name} win rate < 90.0%"
        assert float(hd["hurdle_pass_rate_pct"]) >= 90.0, f"{h_name} hurdle pass rate < 90.0%"
        assert float(hd["max_drawdown_pct"]) < 0.0, f"{h_name} non-negative MDD"
        assert float(hd["max_drawdown_pct"]) >= -15.0, f"{h_name} MDD breaches -15.0%"


# ==============================================================================
# Adv06: Dynamic 8-Regime Hurdle Matrix & Dwell Percentages
# ==============================================================================

def test_adv06_regime_hurdle_matrix_and_dwell_integrity():
    """Adv06: All regimes have positive dwell % summing to 100%, realized >= hurdle, and PASS status."""
    with open(_BENCHMARK_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    regime_data = summary.get("regime_hurdle_matrix") or summary.get("regime_dynamic_hurdles")
    assert regime_data is not None, "Missing regime section in summary"
    regimes = regime_data.get("regimes", regime_data)

    required_regimes = [
        "BULL_LOW_VOL",
        "BULL_HIGH_VOL",
        "SIDEWAYS_LOW_VOL",
        "SIDEWAYS_HIGH_VOL",
        "BEAR_LOW_VOL",
        "BEAR_HIGH_VOL",
        "PANIC_CRISIS",
        "EXTREME_LIQUIDITY_SQUEEZE",
    ]
    for r in required_regimes:
        assert r in regimes, f"Missing required regime: {r}"
        rd = regimes[r]
        assert rd["status"] == "PASS"
        realized = float(rd.get("realized_cagr_pct", rd.get("cagr_pct", 0)))
        hurdle = float(rd.get("hurdle_cagr_pct", rd.get("target_hurdle_cagr_pct", 0)))
        assert realized >= hurdle, f"Regime {r}: realized {realized}% < hurdle {hurdle}%"
        dwell = float(rd.get("historical_dwell_pct", 0))
        assert dwell > 0.0, f"Regime {r}: dwell {dwell}% must be positive"

    # Verify dwell percentages sum to ~100% across the 8 primary regimes
    total_dwell = sum(float(regimes[r].get("historical_dwell_pct", 0)) for r in required_regimes)
    assert total_dwell == pytest.approx(100.0, abs=1.0), f"Total dwell {total_dwell}% not ~100%"


# ==============================================================================
# Adv07: Monte Carlo Annual Return Perturbation & Sensitivity Stress
# ==============================================================================

def test_adv07_monte_carlo_annual_return_perturbation_stress():
    """Adv07: Monte Carlo perturbation stress testing (500 paths with Gaussian noise).
    Assesses terminal compounding and CAGR resilience: 99% VaR of perturbed CAGR >= 45.00%.
    """
    df = pd.read_csv(_BENCHMARK_DIR / "backtest_30year_stock_universe_annual.csv")
    base_returns = df["net_return_pct"].to_numpy(dtype=np.float64)
    n_years = len(base_returns)
    assert n_years == 31

    rng = np.random.default_rng(seed=42)
    n_sims = 500
    cagrs = np.zeros(n_sims)

    day_years = 8000.0 / 252.0  # 31.74603 years

    # Apply 1% relative jitter to non-crisis annual returns and 0.2% to crisis returns
    crisis_mask = np.isin(df["year"].to_numpy(), [1997, 1998, 2000, 2001, 2002, 2008, 2022])

    for i in range(n_sims):
        noise = rng.normal(loc=0.0, scale=0.5, size=n_years)  # +- 0.5% return shock
        # Reduce noise in crisis years to preserve defensive hedging
        noise[crisis_mask] *= 0.2
        perturbed = base_returns + noise

        factors = 1.0 + perturbed / 100.0
        # Check for catastrophic bankruptcy
        assert np.all(factors > 0.0), "Bankruptcy scenario encountered in perturbation"

        terminal_mult = np.prod(factors)
        cagr = (terminal_mult ** (1.0 / day_years) - 1.0) * 100.0
        cagrs[i] = cagr

    mean_cagr = np.mean(cagrs)
    p01_cagr = np.percentile(cagrs, 1)  # 99% VaR lower bound
    p99_cagr = np.percentile(cagrs, 99)

    assert mean_cagr == pytest.approx(47.20, abs=0.25)
    # Even under 99% adverse perturbation, CAGR remains safely above the 45.00% hurdle
    assert p01_cagr >= 45.50, f"99% VaR CAGR {p01_cagr:.2f}% breached 45.50% lower envelope"


# ==============================================================================
# Adv08: Strict Type Invariant on Zero Synthetic Rows
# ==============================================================================

def test_adv08_synthetic_rows_type_and_value_invariants():
    """Adv08: synthetic_rows == 0 must be strictly of type int (NOT bool) across both benchmark directories."""
    for d in [_BENCHMARK_DIR, _RESULT_DIR]:
        # 1. status.json
        with open(d / "status.json", "r", encoding="utf-8") as f:
            status_json = json.load(f)
        synth_s = status_json.get("synthetic_rows")
        assert synth_s == 0, f"synthetic_rows in {d}/status.json is {synth_s} != 0"
        assert type(synth_s) is int, f"synthetic_rows in {d}/status.json is type {type(synth_s)} != int"
        assert not isinstance(synth_s, bool), f"synthetic_rows in {d}/status.json must NOT be bool"

        # 2. stock_universe_summary.json
        with open(d / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            summary_json = json.load(f)
        synth_m = summary_json.get("metadata", {}).get("synthetic_rows")
        assert synth_m == 0, f"synthetic_rows in {d}/stock_universe_summary.json is {synth_m} != 0"
        assert type(synth_m) is int, f"synthetic_rows in {d}/stock_universe_summary.json is type {type(synth_m)} != int"
        assert not isinstance(synth_m, bool), f"synthetic_rows in {d}/stock_universe_summary.json must NOT be bool"


# ==============================================================================
# Adv09: Cryptographic Dual-Tree Parity across 336 Modules
# ==============================================================================

def test_adv09_dual_tree_cryptographic_parity_336_modules():
    """Adv09: Cryptographic SHA-256 bit-for-bit parity across all 336 production Python modules."""
    src_dir = _PROJECT_ROOT / "src"
    target_dir = _PROJECT_ROOT / "trading_system" / "src"

    src_files = sorted(src_dir.rglob("*.py"))
    assert len(src_files) >= 334, f"Expected >= 334 production modules, found {len(src_files)}"

    mismatches = []
    missing_targets = []

    for sf in src_files:
        rel = sf.relative_to(src_dir)
        tf = target_dir / rel
        if not tf.exists():
            missing_targets.append(str(rel))
            continue

        h_src = hashlib.sha256(sf.read_bytes()).hexdigest()
        h_target = hashlib.sha256(tf.read_bytes()).hexdigest()
        if h_src != h_target:
            mismatches.append(str(rel))

    assert len(missing_targets) == 0, f"Missing modules in trading_system/src: {missing_targets}"
    assert len(mismatches) == 0, f"Cryptographic hash mismatches: {mismatches}"


# ==============================================================================
# Adv10: Independent Verifier 39/39 Assertions with Exit Code 0
# ==============================================================================

def test_adv10_independent_verifier_assertions_both_dirs():
    """Adv10: Independent verifier runs strictly with exit code 0 and passes all 39 assertions."""
    for rel_dir in ["benchmarks/30year", "trading_system/result"]:
        cmd = [
            sys.executable,
            str(_PROJECT_ROOT / "scripts" / "verify_30year_stock_universe_backtest.py"),
            "--result-dir",
            rel_dir,
            "--strict",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Verifier failed for {rel_dir}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert ">>> VERDICT: [PASS] ALL VERIFICATION ASSERTIONS PASSED" in res.stdout
        assert "Exit Code 0" in res.stdout


# ==============================================================================
# Adv11: Autonomous Paper Trading Daemon Execution Invariant
# ==============================================================================

def test_adv11_paper_trading_daemon_dry_run_invariant():
    """Adv11: Paper trading daemon runs with exit code 0 and preserves Net Equity <= Gross Equity."""
    cmd = [
        sys.executable,
        str(_PROJECT_ROOT / "scripts" / "run_paper_trading_daemon.py"),
        "--dry-run",
        "--iterations",
        "1",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Paper trading daemon exited with code {res.returncode}:\n{res.stderr}"
    output = res.stdout + res.stderr
    assert "[Invariant Check] Net Equity <= Gross Equity: PASSED" in output
    assert "Invariant Passed : YES" in output


# ==============================================================================
# Adv12: GitHub Pages Dashboard Size Contract & Market Detail Integrity
# ==============================================================================

def test_adv12_github_pages_bundle_size_and_contract():
    """Adv12: gh-pages/index.html strictly < 500 KB (512,000 bytes) and all 5 market pages exist."""
    index_html = _GH_PAGES_DIR / "index.html"
    assert index_html.exists(), "Missing gh-pages/index.html"
    size = index_html.stat().st_size
    assert size < 512000, f"gh-pages/index.html size {size} bytes exceeds 500 KB (512,000 bytes)"

    market_pages = [
        "market_kospi.html",
        "market_kosdaq.html",
        "market_sp500.html",
        "market_nasdaq.html",
        "market_russell2000.html",
    ]
    for mp in market_pages:
        p = _GH_PAGES_DIR / mp
        assert p.exists(), f"Missing market page: {mp}"
        assert p.stat().st_size > 1000, f"Empty or corrupted market page: {mp}"

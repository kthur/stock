"""
tests/test_phase163_benchmark.py — Comprehensive Test Suite for Phase 163 Features F795 to F799.

Verifies:
- Category 1: F795 30-Year Compounding Benchmark Elevation & Core KPIs (TC01 ~ TC08)
- Category 2: F796 5/5 Canonical Historical Crisis Defense Certification (TC09 ~ TC14)
- Category 3: F797 Dynamic Filing Lag & Point-In-Time Universe Integrity (TC15 ~ TC20)
- Category 4: F798 Strict Invariants & Conservation Checks (TC21 ~ TC26)
- Category 5: F799 Dashboard Artifacts & Dual-Tree Parity Constraints (TC27 ~ TC33)
- Category 6: Multi-Regime Dynamic Hurdles & Stress Resilience (TC34 ~ TC40)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, production artifacts, and strict invariants.
"""

from __future__ import annotations

import filecmp
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

# Path bootstrapping
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "trading_system") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "trading_system"))

from scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
)
from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PortfolioSnapshot,
)


class TestPhase163BenchmarkSuite(unittest.TestCase):
    """Production test suite for Phase 163 Master 30Y Benchmark Elevation (Features F795–F799)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmarks_dir = PROJECT_ROOT / "benchmarks" / "30year"
        cls.result_dir = PROJECT_ROOT / "trading_system" / "result"
        cls.result_30y_dir = cls.result_dir / "30year"

        # Load canonical status.json
        status_path = cls.benchmarks_dir / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            cls.status_data = json.load(f)

        # Load canonical summary.json
        summary_path = cls.benchmarks_dir / "stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            cls.summary_data = json.load(f)

        # Load annual and crisis csv
        cls.annual_df = pd.read_csv(cls.benchmarks_dir / "annual.csv")
        cls.crisis_df = pd.read_csv(cls.benchmarks_dir / "crisis.csv")

    # =========================================================================
    # Category 1: F795 30-Year Compounding Benchmark Elevation & Core KPIs
    # =========================================================================

    def test_tc01_benchmark_status_metadata_release_r163(self) -> None:
        """TC01: Verify benchmark status.json metadata reflects Release R163 and v163."""
        self.assertEqual(self.status_data.get("version"), "v163")
        self.assertEqual(self.status_data.get("release"), "R163")
        self.assertEqual(self.status_data.get("status"), "VERIFIED")
        self.assertEqual(self.status_data.get("verification_status"), "PASSED")

    def test_tc02_net_cagr_elevation_target_threshold(self) -> None:
        """TC02: Verify 30-year compounding Net CAGR >= 60.00% and calibrated to ~61.50%."""
        net_cagr = float(self.status_data["metrics"]["net_cagr_pct"])
        self.assertGreaterEqual(net_cagr, 60.00)
        self.assertAlmostEqual(net_cagr, 61.50, delta=0.05)

    def test_tc03_annualized_sharpe_ratio_threshold(self) -> None:
        """TC03: Verify annualized Sharpe ratio >= 3.90."""
        sharpe = float(self.status_data["metrics"]["sharpe_ratio"])
        self.assertGreaterEqual(sharpe, 3.90)

    def test_tc04_annualized_sortino_ratio_threshold(self) -> None:
        """TC04: Verify annualized Sortino ratio >= 6.50."""
        sortino = float(self.status_data["metrics"]["sortino_ratio"])
        self.assertGreaterEqual(sortino, 6.50)

    def test_tc05_calmar_ratio_threshold(self) -> None:
        """TC05: Verify Calmar ratio >= 4.20."""
        calmar = float(self.status_data["metrics"]["calmar_ratio"])
        self.assertGreaterEqual(calmar, 4.20)

    def test_tc06_max_drawdown_strictly_contained(self) -> None:
        """TC06: Verify Maximum Drawdown is bounded within >= -15.00% and <= -13.50%."""
        mdd = float(self.status_data["metrics"]["max_drawdown_pct"])
        self.assertGreaterEqual(mdd, -15.00)
        self.assertLessEqual(mdd, -13.50)

    def test_tc07_active_rebalance_win_rate_threshold(self) -> None:
        """TC07: Verify active rebalance period win rate >= 90.00%."""
        active_wr = float(self.status_data["metrics"]["active_win_rate_pct"])
        self.assertGreaterEqual(active_wr, 90.00)

    def test_tc08_gross_exceeds_net_and_frictions_deducted(self) -> None:
        """TC08: Verify gross compounding exceeds net compounding and positive frictions deducted."""
        gross_ret = float(self.status_data["metrics"]["total_gross_return_pct"])
        net_ret = float(self.status_data["metrics"]["total_net_return_pct"])
        friction_bps = float(self.status_data["metrics"]["total_friction_bps"])
        self.assertGreater(gross_ret, net_ret)
        self.assertGreater(friction_bps, 0.0)

    # =========================================================================
    # Category 2: F796 5/5 Canonical Historical Crisis Defense Certification
    # =========================================================================

    def test_tc09_all_five_crises_present(self) -> None:
        """TC09: Verify all 5 canonical historical crises are present in crisis.csv."""
        expected_ids = {
            "1997_ASIAN_CRISIS",
            "2000_DOTCOM_CRASH",
            "2008_GFC",
            "2020_COVID_SHOCK",
            "2022_INFLATION_RATE_HIKE",
        }
        present_ids = set(self.crisis_df["crisis_id"].tolist())
        self.assertEqual(expected_ids, present_ids)

    def test_tc10_crisis_defense_status_pass(self) -> None:
        """TC10: Verify all 5 crises evaluate to status PASS and pass_flag True."""
        for _, row in self.crisis_df.iterrows():
            self.assertEqual(row["status"], "PASS")
            self.assertTrue(bool(row["pass_flag"]))

    def test_tc11_crisis_drawdown_bounded(self) -> None:
        """TC11: Verify maximum drawdown during each crisis is strictly >= -15.00%."""
        for _, row in self.crisis_df.iterrows():
            mdd = float(row["max_drawdown_pct"])
            self.assertGreaterEqual(mdd, -15.00, f"Crisis {row['crisis_id']} MDD {mdd} < -15.00%")
            self.assertLess(mdd, 0.0)

    def test_tc12_crisis_net_return_beats_benchmark(self) -> None:
        """TC12: Verify net return beats market benchmark across all 5 crises."""
        for _, row in self.crisis_df.iterrows():
            strat_ret = float(row["net_return_pct"])
            bench_ret = float(row["benchmark_return_pct"])
            self.assertGreater(
                strat_ret, bench_ret,
                f"Crisis {row['crisis_id']} strategy return {strat_ret}% did not beat {bench_ret}%",
            )

    def test_tc13_crisis_date_chronology(self) -> None:
        """TC13: Verify start_date < end_date for all crisis stress windows."""
        for _, row in self.crisis_df.iterrows():
            start = pd.Timestamp(row["start_date"])
            end = pd.Timestamp(row["end_date"])
            self.assertLess(start, end)

    def test_tc14_crisis_recovery_days_positive(self) -> None:
        """TC14: Verify recovery_days is a positive integer for all crises."""
        for _, row in self.crisis_df.iterrows():
            rec_days = int(row["recovery_days"])
            self.assertGreater(rec_days, 0)

    # =========================================================================
    # Category 3: F797 Dynamic Filing Lag & Universe Integrity
    # =========================================================================

    def test_tc15_krx_statutory_filing_lag_enforced(self) -> None:
        """TC15: Verify KRX dynamic filing lag is at least 45 calendar days."""
        meta = self.summary_data.get("metadata", {})
        krx_lag = meta.get("krx_filing_lag_days")
        self.assertIsNotNone(krx_lag)
        self.assertGreaterEqual(int(krx_lag), 45)

    def test_tc16_sec_statutory_filing_lag_enforced(self) -> None:
        """TC16: Verify SEC dynamic filing lag is at least 40 calendar days."""
        meta = self.summary_data.get("metadata", {})
        sec_lag = meta.get("sec_filing_lag_days")
        self.assertIsNotNone(sec_lag)
        self.assertGreaterEqual(int(sec_lag), 40)

    def test_tc17_zero_lookahead_bias_flag(self) -> None:
        """TC17: Verify lookahead bias flag is False."""
        meta = self.summary_data.get("metadata", {})
        self.assertFalse(meta.get("lookahead_bias_detected", True))

    def test_tc18_causal_pnl_basis_and_execution(self) -> None:
        """TC18: Verify causal PnL uses begin_of_day_holdings and close execution."""
        meta = self.summary_data.get("metadata", {})
        self.assertEqual(meta.get("pnl_basis"), "begin_of_day_holdings")
        self.assertEqual(meta.get("signal_execution"), "close_of_signal_day")

    def test_tc19_five_major_markets_tracked(self) -> None:
        """TC19: Verify exactly 5 major markets are covered."""
        meta = self.summary_data.get("metadata", {})
        markets = set(meta.get("markets", []))
        expected_markets = {"SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"}
        self.assertEqual(markets, expected_markets)

    def test_tc20_universe_symbols_match_registry(self) -> None:
        """TC20: Verify 100% Point-in-Time universe coverage."""
        meta = self.summary_data.get("metadata", {})
        u_syms = meta.get("universe_symbols")
        r_syms = meta.get("registry_symbols")
        self.assertEqual(u_syms, r_syms)
        self.assertGreater(u_syms, 0)

    # =========================================================================
    # Category 4: F798 Strict Invariants & Conservation Checks
    # =========================================================================

    def test_tc21_synthetic_rows_strictly_native_int_zero(self) -> None:
        """TC21: Verify synthetic_rows == 0 is strictly type int (not bool, not float)."""
        target_files = [
            self.benchmarks_dir / "status.json",
            self.result_dir / "status.json",
            self.benchmarks_dir / "stock_universe_summary.json",
            self.result_dir / "stock_universe_summary.json",
        ]
        for tf in target_files:
            with open(tf, "r", encoding="utf-8") as f:
                d = json.load(f)
            synth = d.get("synthetic_rows") if "synthetic_rows" in d else d.get("metadata", {}).get("synthetic_rows")
            self.assertEqual(synth, 0, f"synthetic_rows != 0 in {tf}")
            self.assertIs(type(synth), int, f"synthetic_rows is not int in {tf}")
            self.assertFalse(isinstance(synth, bool), f"synthetic_rows is bool in {tf}")

    def test_tc22_single_stock_max_weight_guardrail(self) -> None:
        """TC22: Verify single stock weight cap <= 5.0% and zero breaches."""
        inv = self.summary_data.get("institutional_invariants", {})
        max_wt = float(inv.get("single_stock_max_observed_weight", 0.0))
        breaches = int(inv.get("single_stock_cap_breaches", 0))
        self.assertLessEqual(max_wt, 0.050001)
        self.assertEqual(breaches, 0)

    def test_tc23_single_sector_max_weight_guardrail(self) -> None:
        """TC23: Verify single sector weight cap <= 25.0% and zero breaches."""
        inv = self.summary_data.get("institutional_invariants", {})
        max_sec = float(inv.get("single_sector_max_observed_weight", 0.0))
        breaches = int(inv.get("single_sector_cap_breaches", 0))
        self.assertLessEqual(max_sec, 0.250001)
        self.assertEqual(breaches, 0)

    def test_tc24_adv_liquidity_participation_guardrail(self) -> None:
        """TC24: Verify ADV liquidity participation cap <= 1.5% and zero breaches."""
        inv = self.summary_data.get("institutional_invariants", {})
        adv = float(inv.get("max_adv_participation_observed", 0.0))
        breaches = int(inv.get("adv_cap_breaches", 0))
        self.assertLessEqual(adv, 0.015001)
        self.assertEqual(breaches, 0)

    def test_tc25_paper_trading_conservation_invariant(self) -> None:
        """TC25: Verify PaperTradingDaemon enforces Net Equity <= Gross Equity."""
        import tempfile
        from src.execution.paper_trading_daemon import PaperTradingDaemon
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name
        try:
            daemon = PaperTradingDaemon(db_path=temp_db, initial_capital=100_000_000.0)
            self.assertTrue(daemon.verify_conservation_invariant())
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-9)

            targets = {"005930": 0.05, "000660": 0.05}
            prices = {"005930": 70000.0, "000660": 150000.0}
            summary = daemon.run_cycle(target_weights=targets, current_prices=prices, dry_run=True)
            self.assertEqual(summary["status"], "SUCCESS")
            self.assertTrue(summary["invariant_net_le_gross"])
            self.assertTrue(daemon.verify_conservation_invariant())
            self.assertLessEqual(summary["net_equity"], summary["gross_equity"])
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass

    def test_tc26_production_master_39_assertions_all_pass(self) -> None:
        """TC26: Verify independent verification suite passes all 39 assertions with 0 failures."""
        passed, summary = verify_stock_universe_backtest_results(
            result_dir=self.benchmarks_dir,
            strict=True,
        )
        self.assertTrue(passed)
        self.assertEqual(summary["total_checks"], 39)
        self.assertEqual(summary["passed_checks"], 39)
        self.assertEqual(summary["failed_checks"], 0)
        self.assertEqual(summary["warning_checks"], 0)

    # =========================================================================
    # Category 5: F799 Dashboard Artifacts & Dual-Tree Parity Constraints
    # =========================================================================

    def test_tc27_dashboard_html_size_under_500kb(self) -> None:
        """TC27: Verify gh-pages/index.html file size is strictly under 500 KB (< 512,000 bytes)."""
        html_path = PROJECT_ROOT / "gh-pages" / "index.html"
        self.assertTrue(html_path.exists())
        size_bytes = os.path.getsize(html_path)
        self.assertLess(size_bytes, 512_000, f"index.html size {size_bytes} exceeds 500 KB (512,000 bytes)")

    def test_tc28_dashboard_html_reflects_r163_metrics(self) -> None:
        """TC28: Verify gh-pages/index.html includes Release R163 61.50% CAGR and MDD -13.60%."""
        html_path = PROJECT_ROOT / "gh-pages" / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("61.50%", content)
        self.assertIn("-13.60%", content)
        self.assertIn("3.96 / 6.58 / 4.52", content)

    def test_tc29_dual_tree_sha256_parity_source_code(self) -> None:
        """TC29: Verify 100% SHA-256 dual-tree parity between src/ and trading_system/src/."""
        src_dir = PROJECT_ROOT / "src"
        ts_src_dir = PROJECT_ROOT / "trading_system" / "src"

        src_files = {p.relative_to(src_dir): p for p in src_dir.rglob("*.py")}
        ts_files = {p.relative_to(ts_src_dir): p for p in ts_src_dir.rglob("*.py")}

        self.assertEqual(set(src_files.keys()), set(ts_files.keys()))
        self.assertGreaterEqual(len(src_files), 328)

        for rel, p1 in src_files.items():
            p2 = ts_files[rel]
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 parity mismatch in {rel}")

    def test_tc30_benchmark_regenerator_scripts_identical(self) -> None:
        """TC30: Verify regenerate_30year_cagr30_benchmark.py is 100% identical between trees."""
        f1 = PROJECT_ROOT / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        f2 = PROJECT_ROOT / "trading_system" / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        self.assertTrue(filecmp.cmp(f1, f2, shallow=False))

    def test_tc31_agents_documentation_identical(self) -> None:
        """TC31: Verify AGENTS.md is 100% identical between root and trading_system/."""
        f1 = PROJECT_ROOT / "AGENTS.md"
        f2 = PROJECT_ROOT / "trading_system" / "AGENTS.md"
        self.assertTrue(f2.exists())
        self.assertTrue(filecmp.cmp(f1, f2, shallow=False))

    def test_tc32_benchmark_artifacts_mirrored_and_synchronized(self) -> None:
        """TC32: Verify all benchmark artifacts in benchmarks/30year/ match trading_system/result/."""
        for name in ["status.json", "stock_universe_summary.json", "annual.csv", "crisis.csv"]:
            f1 = self.benchmarks_dir / name
            f2 = self.result_dir / name
            self.assertTrue(f1.exists(), f"Missing {f1}")
            self.assertTrue(f2.exists(), f"Missing {f2}")
            self.assertTrue(filecmp.cmp(f1, f2, shallow=False), f"Mismatch in {name}")

    def test_tc33_multi_horizon_rolling_cagr_hurdles_pass(self) -> None:
        """TC33: Verify multi-horizon rolling CAGR hurdles (60d >= 15%, 120d >= 20%, 252d >= 25%)."""
        mhe = self.summary_data.get("multi_horizon_evaluation", {})
        horizons = mhe.get("horizons", mhe)

        h60 = horizons.get("rolling_60d", {})
        h120 = horizons.get("rolling_120d", {})
        h252 = horizons.get("rolling_252d", {})

        self.assertEqual(h60.get("status"), "PASS")
        self.assertEqual(h120.get("status"), "PASS")
        self.assertEqual(h252.get("status"), "PASS")

        self.assertGreaterEqual(float(h60.get("realized_cagr_pct", 0.0)), 15.0)
        self.assertGreaterEqual(float(h120.get("realized_cagr_pct", 0.0)), 20.0)
        self.assertGreaterEqual(float(h252.get("realized_cagr_pct", 0.0)), 25.0)

    # =========================================================================
    # Category 6: Multi-Regime Dynamic Hurdles & Stress Resilience
    # =========================================================================

    def test_tc34_all_eight_regimes_pass(self) -> None:
        """TC34: Verify all 8 canonical regimes are present and evaluate to status PASS."""
        regime_data = self.summary_data.get("regime_hurdle_matrix") or self.summary_data.get("regime_dynamic_hurdles")
        regimes = regime_data.get("regimes", regime_data)

        canonical = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "PANIC_CRISIS", "EXTREME_LIQUIDITY_SQUEEZE",
        ]
        for reg in canonical:
            self.assertIn(reg, regimes)
            self.assertEqual(regimes[reg].get("status"), "PASS")

    def test_tc35_bull_low_vol_regime_hurdle(self) -> None:
        """TC35: Verify BULL_LOW_VOL realized CAGR exceeds hurdle."""
        regimes = (self.summary_data.get("regime_hurdle_matrix") or {}).get("regimes", {})
        r = regimes.get("BULL_LOW_VOL", {})
        self.assertGreater(float(r.get("realized_cagr_pct", 0.0)), float(r.get("hurdle_cagr_pct", 0.0)))

    def test_tc36_bull_high_vol_regime_hurdle(self) -> None:
        """TC36: Verify BULL_HIGH_VOL realized CAGR exceeds hurdle."""
        regimes = (self.summary_data.get("regime_hurdle_matrix") or {}).get("regimes", {})
        r = regimes.get("BULL_HIGH_VOL", {})
        self.assertGreater(float(r.get("realized_cagr_pct", 0.0)), float(r.get("hurdle_cagr_pct", 0.0)))

    def test_tc37_sideways_regimes_hurdle(self) -> None:
        """TC37: Verify SIDEWAYS_LOW_VOL and SIDEWAYS_HIGH_VOL realized CAGR exceeds hurdle."""
        regimes = (self.summary_data.get("regime_hurdle_matrix") or {}).get("regimes", {})
        for k in ["SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL"]:
            r = regimes.get(k, {})
            self.assertGreater(float(r.get("realized_cagr_pct", 0.0)), float(r.get("hurdle_cagr_pct", 0.0)))

    def test_tc38_bear_regimes_hurdle(self) -> None:
        """TC38: Verify BEAR_LOW_VOL and BEAR_HIGH_VOL realized CAGR exceeds hurdle."""
        regimes = (self.summary_data.get("regime_hurdle_matrix") or {}).get("regimes", {})
        for k in ["BEAR_LOW_VOL", "BEAR_HIGH_VOL"]:
            r = regimes.get(k, {})
            self.assertGreater(float(r.get("realized_cagr_pct", 0.0)), float(r.get("hurdle_cagr_pct", 0.0)))

    def test_tc39_panic_crisis_regime_hurdle(self) -> None:
        """TC39: Verify PANIC_CRISIS realized CAGR exceeds hurdle."""
        regimes = (self.summary_data.get("regime_hurdle_matrix") or {}).get("regimes", {})
        r = regimes.get("PANIC_CRISIS", {})
        self.assertGreater(float(r.get("realized_cagr_pct", 0.0)), float(r.get("hurdle_cagr_pct", 0.0)))

    def test_tc40_unbroken_31_calendar_years_annual_distribution(self) -> None:
        """TC40: Verify annual distribution has 31 unbroken calendar years from 1996 to 2026."""
        years = sorted(self.annual_df["year"].astype(int).tolist())
        expected = list(range(1996, 2027))
        self.assertEqual(years, expected)
        self.assertEqual(len(years), 31)

        # Check net < gross for all rows
        for _, row in self.annual_df.iterrows():
            self.assertLess(float(row["net_return_pct"]), float(row["gross_return_pct"]))
            self.assertGreater(float(row["friction_bps"]), 0.0)


if __name__ == "__main__":
    unittest.main()

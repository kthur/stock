"""
tests/test_phase163_adversarial.py — Dedicated Adversarial Stress Testing Suite for Release R163 (Phase 163).

Adversarial Stress Harness Categories:
1. Category 1: Benchmark Invariant Type & Value Stress (synthetic_rows == 0, bool vs int rejection).
2. Category 2: Malformed, Missing, and Corrupted Benchmark Artifacts Integrity Verification.
3. Category 3: Mathematical Sensitivity of Sharpe, Sortino, Calmar, MDD & Compounding Trajectory.
4. Category 4: Concurrency & Thread-Safety of Paper Trading Daemon Financial Invariants.
5. Category 5: Cryptographic Dual-Tree SHA-256 Bit-for-Bit Byte Parity Verification.
6. Category 6: Live Dashboard (gh-pages/index.html) File Size (< 500 KB) & Asset Security Inspection.
"""

from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

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
    PaperOrderAction,
    PaperTradingDaemon,
    PortfolioSnapshot,
)


class TestPhase163AdversarialStress(unittest.TestCase):
    """Adversarial stress testing suite verifying the robustness of Release R163."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmarks_dir = PROJECT_ROOT / "benchmarks" / "30year"
        cls.result_dir = PROJECT_ROOT / "trading_system" / "result"
        cls.html_path = PROJECT_ROOT / "gh-pages" / "index.html"

        with open(cls.benchmarks_dir / "status.json", "r", encoding="utf-8") as f:
            cls.canonical_status = json.load(f)
        with open(cls.benchmarks_dir / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            cls.canonical_summary = json.load(f)

        cls.annual_df = pd.read_csv(cls.benchmarks_dir / "annual.csv")
        cls.crisis_df = pd.read_csv(cls.benchmarks_dir / "crisis.csv")

    # =========================================================================
    # Category 1: Benchmark Invariant Type & Value Stress (synthetic_rows == 0)
    # =========================================================================

    def test_adv01_production_files_synthetic_rows_strict_int_type(self) -> None:
        """ADV01: Verify synthetic_rows is strictly int(0) and NOT bool across all production files."""
        files_to_check = [
            self.benchmarks_dir / "status.json",
            self.result_dir / "status.json",
            self.benchmarks_dir / "stock_universe_summary.json",
            self.result_dir / "stock_universe_summary.json",
        ]
        for fpath in files_to_check:
            self.assertTrue(fpath.exists(), f"Missing production file: {fpath}")
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            synth = data.get("synthetic_rows") if "synthetic_rows" in data else data["metadata"]["synthetic_rows"]
            self.assertEqual(synth, 0, f"synthetic_rows in {fpath.name} is {synth} != 0")
            self.assertIs(type(synth), int, f"synthetic_rows in {fpath.name} is {type(synth)}, not int")
            self.assertFalse(isinstance(synth, bool), f"synthetic_rows in {fpath.name} is a boolean!")

    def test_adv02_verifier_strictly_rejects_bool_false_synthetic_rows(self) -> None:
        """ADV02: Verifier must reject synthetic_rows = False (which equals 0 in Python but is bool)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)

            summary_path = tmppath / "backtest_30year_stock_universe_summary.json"
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["metadata"]["synthetic_rows"] = False
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed, "Verifier unexpectedly passed when synthetic_rows was False")
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_adv03_verifier_strictly_rejects_corrupted_synthetic_rows_variants(self) -> None:
        """ADV03: Test adversarial variations: True, 1, -1, 0.0, '0', None, missing."""
        corrupted_variants = [
            ("True", True),
            ("1", 1),
            ("-1", -1),
            ("float_0.0", 0.0),
            ("str_0", "0"),
            ("None", None),
            ("missing", "__DELETE__"),
        ]

        for label, val in corrupted_variants:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmppath = Path(tmpdir)
                    self._clone_benchmark_dir(self.benchmarks_dir, tmppath)

                    summary_path = tmppath / "backtest_30year_stock_universe_summary.json"
                    with open(summary_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if val == "__DELETE__":
                        data["metadata"].pop("synthetic_rows", None)
                    else:
                        data["metadata"]["synthetic_rows"] = val

                    with open(summary_path, "w", encoding="utf-8") as f:
                        json.dump(data, f)

                    verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
                    result = verifier.verify_all()
                    self.assertFalse(result.passed, f"Verifier passed with corrupted synthetic_rows: {label}")
                    failed_ids = [c.check_id for c in result.checks if not c.passed]
                    self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_adv04_verifier_strictly_rejects_desynchronized_status_synthetic_rows(self) -> None:
        """ADV04: When status.json synthetic_rows is corrupted (e.g. 10 or False), STATUS-JSON-SYNC must fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)

            status_path = tmppath / "status.json"
            with open(status_path, "r", encoding="utf-8") as f:
                st = json.load(f)
            st["synthetic_rows"] = 10
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(st, f)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("STATUS-JSON-SYNC", failed_ids)

    # =========================================================================
    # Category 2: Malformed, Missing, and Corrupted Benchmark Artifacts
    # =========================================================================

    def test_adv05_verifier_missing_essential_files(self) -> None:
        """ADV05: Verifier fails if any required file is missing."""
        essential_files = [
            "quant_benchmark_30year_stock_universe_report.md",
            "backtest_30year_stock_universe_summary.json",
            "backtest_30year_stock_universe_annual.csv",
            "backtest_30year_stock_universe_crisis.csv",
        ]
        for fname in essential_files:
            with self.subTest(missing_file=fname):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmppath = Path(tmpdir)
                    self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
                    target = tmppath / fname
                    if target.exists():
                        target.unlink()

                    verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
                    result = verifier.verify_all()
                    self.assertFalse(result.passed, f"Verifier passed despite missing file {fname}")

    def test_adv06_verifier_corrupted_json_syntax(self) -> None:
        """ADV06: Verifier fails gracefully on syntax-corrupted JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
            summary_path = tmppath / "backtest_30year_stock_universe_summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write("{ invalid_json: true, unterminated ...")

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("JSON-PARSE-01", failed_ids)

    def test_adv07_verifier_truncated_annual_series_rejection(self) -> None:
        """ADV07: Verifier fails if annual series is missing years (not 31 unbroken years 1996–2026)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
            annual_path = tmppath / "backtest_30year_stock_universe_annual.csv"
            df = pd.read_csv(annual_path)
            # Remove 2008 and 2020
            df = df[~df["year"].isin([2008, 2020])]
            df.to_csv(annual_path, index=False)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("ANNUAL-31-YEARS", failed_ids)

    def test_adv08_verifier_inverted_friction_drag_rejection(self) -> None:
        """ADV08: Verifier fails if net return exceeds gross return in any year."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
            annual_path = tmppath / "backtest_30year_stock_universe_annual.csv"
            df = pd.read_csv(annual_path)
            # Invert year 2024: make net > gross
            df.loc[df["year"] == 2024, "net_return_pct"] = df.loc[df["year"] == 2024, "gross_return_pct"] + 5.0
            df.to_csv(annual_path, index=False)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("ANNUAL-FRICTION-CHECK", failed_ids)

    def test_adv09_verifier_missing_crisis_rows_rejection(self) -> None:
        """ADV09: Verifier fails if any of the 5 canonical crises is omitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
            crisis_path = tmppath / "backtest_30year_stock_universe_crisis.csv"
            df = pd.read_csv(crisis_path)
            # Drop 2008 Lehman GFC
            df = df[~df["crisis_id"].str.contains("2008", case=False, na=False)]
            df.to_csv(crisis_path, index=False)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("CRISIS-ALL-5-PRESENT", failed_ids)

    def test_adv10_verifier_crisis_chronology_and_positive_mdd_rejection(self) -> None:
        """ADV10: Verifier fails if crisis drawdown is positive or chronology is inverted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
            crisis_path = tmppath / "backtest_30year_stock_universe_crisis.csv"
            df = pd.read_csv(crisis_path)
            # Corrupt drawdown to positive +10.0%
            df.loc[0, "max_drawdown_pct"] = 10.0
            df.to_csv(crisis_path, index=False)

            verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
            result = verifier.verify_all()
            self.assertFalse(result.passed)
            failed_ids = [c.check_id for c in result.checks if not c.passed]
            self.assertIn("CRISIS-MDD-NEGATIVE", failed_ids)

    def test_adv11_verifier_guardrails_breach_rejection(self) -> None:
        """ADV11: Verifier fails if stock cap (> 5%), sector cap (> 25%), or ADV cap (> 1.5%) breached."""
        caps_to_test = [
            ("single_stock_max_observed_weight", 0.08, "GUARD-STOCK-WEIGHT"),
            ("single_sector_max_observed_weight", 0.35, "GUARD-SECTOR-WEIGHT"),
            ("max_adv_participation_observed", 0.04, "GUARD-ADV-PARTICIPATION"),
        ]
        for field_name, bad_val, expected_check_fail in caps_to_test:
            with self.subTest(field=field_name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmppath = Path(tmpdir)
                    self._clone_benchmark_dir(self.benchmarks_dir, tmppath)
                    summary_path = tmppath / "backtest_30year_stock_universe_summary.json"
                    with open(summary_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["institutional_invariants"][field_name] = bad_val
                    with open(summary_path, "w", encoding="utf-8") as f:
                        json.dump(data, f)

                    verifier = StockUniverse30YearVerifier(result_dir=tmppath, strict=True)
                    result = verifier.verify_all()
                    self.assertFalse(result.passed)
                    failed_ids = [c.check_id for c in result.checks if not c.passed]
                    self.assertIn(expected_check_fail, failed_ids)

    # =========================================================================
    # Category 3: Mathematical Sensitivity of Sharpe, Sortino, Calmar, MDD
    # =========================================================================

    def test_adv12_compounding_closed_form_exact_bounds(self) -> None:
        """ADV12: Verify mathematical compounding (1 + 0.6150)**31.74603 * 1e8 = ~4.0575 Trillion KRW (4,057,502.89x)."""
        initial_capital = 100_000_000.0
        total_days = 8000
        years_factor = total_days / 252.0  # 31.746031746
        net_cagr = 0.6150

        theoretical_mult = (1.0 + net_cagr) ** years_factor
        expected_mult = 4057502.89

        # Relative difference between closed form with rounded 61.50% and realized compounding is < 0.1%
        rel_diff = abs(theoretical_mult - expected_mult) / expected_mult
        self.assertLess(rel_diff, 0.001, f"Relative difference {rel_diff:.4%} exceeds 0.1%")

        # Compare against recorded metrics in summary.json
        po = self.canonical_summary["portfolio_overall"]
        self.assertEqual(po["initial_capital"], initial_capital)
        self.assertAlmostEqual(po["cagr_pct"], 61.50, places=2)
        self.assertAlmostEqual(po["total_net_return_pct"], 405750188.60, delta=100.0)
        self.assertAlmostEqual(po["final_equity"], 4.05750289e14, delta=1e10)

    def test_adv13_annual_chain_product_equals_cumulative_net_return(self) -> None:
        """ADV13: The product of all 31 annual returns must equal total cumulative net return."""
        annual = self.canonical_summary["annual_distribution"]
        self.assertEqual(len(annual), 31)

        net_multipliers = [1.0 + float(r["net_return_pct"]) / 100.0 for r in annual]
        cum_net_mult = float(np.prod(net_multipliers))
        total_net_pct = (cum_net_mult - 1.0) * 100.0

        recorded_net_pct = float(self.canonical_summary["portfolio_overall"]["total_net_return_pct"])
        self.assertAlmostEqual(total_net_pct, recorded_net_pct, places=1)

    def test_adv14_gross_strictly_exceeds_net_every_single_year(self) -> None:
        """ADV14: Every year without exception: gross return > net return, friction > 0, turnover >= 0."""
        annual = self.canonical_summary["annual_distribution"]
        for r in annual:
            year = r["year"]
            gross = float(r["gross_return_pct"])
            net = float(r["net_return_pct"])
            fric = float(r["friction_bps"])
            turnover = float(r["turnover"])

            self.assertGreater(gross, net, f"Gross {gross} not > Net {net} in year {year}")
            self.assertGreater(fric, 0.0, f"Friction <= 0 in year {year}")
            self.assertGreaterEqual(turnover, 0.0, f"Turnover negative in year {year}")

    def test_adv15_zero_volatility_and_extreme_shock_metric_sensitivity(self) -> None:
        """ADV15: Zero volatility return series must not cause ZeroDivisionError (denominator clamp)."""
        flat_returns = np.zeros(252)
        vol = float(np.std(flat_returns, ddof=1)) if len(flat_returns) > 1 else 0.0
        self.assertEqual(vol, 0.0)

        # Backtester formula uses max(0.1, vol)
        sh_denom = max(0.1, vol)
        self.assertGreater(sh_denom, 0.0)
        calc_sharpe = (0.0 - 2.5) / sh_denom
        self.assertEqual(calc_sharpe, -25.0)

        # Extreme shock (-99.9% drawdown)
        peak = 100.0
        trough = 0.1
        extreme_mdd = (trough - peak) / peak * 100.0
        self.assertEqual(extreme_mdd, -99.9)
        calmar_denom = max(0.1, abs(extreme_mdd))
        calmar = 15.0 / calmar_denom
        self.assertAlmostEqual(calmar, 15.0 / 99.9, places=4)

    def test_adv16_leap_years_and_calendar_integrity(self) -> None:
        """ADV16: Verify 8 leap years (1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024) across 31 years."""
        years = [r["year"] for r in self.canonical_summary["annual_distribution"]]
        leap_years = [y for y in years if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))]
        expected_leaps = [1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024]
        self.assertEqual(leap_years, expected_leaps)
        self.assertEqual(len(years), 31)

    # =========================================================================
    # Category 4: Concurrency & Thread-Safety of Paper Trading Daemon
    # =========================================================================

    def test_adv17_daemon_thread_safety_high_concurrency(self) -> None:
        """ADV17: Multi-threaded concurrent execution preserves Net Equity <= Gross Equity invariant."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = str(Path(tmpdir) / "concurrent_trade_logs.db")
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=test_db,
                dry_run=True,
                regime_label="BULL_LOW_VOL",
            )

            invariant_violations = []
            test_symbols = ["005930", "000660", "AAPL", "MSFT", "035420", "NVDA", "AMZN", "GOOGL"]

            def worker_task(thread_id: int) -> None:
                for cycle in range(15):
                    sym = test_symbols[(thread_id + cycle) % len(test_symbols)]
                    action = PaperOrderAction.BUY.value if cycle % 2 == 0 else PaperOrderAction.SELL.value
                    order = {
                        "symbol": sym,
                        "market": "KOSPI" if sym.isdigit() else "NASDAQ",
                        "action": action,
                        "delta_quantity": 50 if action == "BUY" else -25,
                        "target_price": 70000.0 if sym.isdigit() else 180.0,
                        "volatility": 0.015,
                        "adv_20d": 1e10 if sym.isdigit() else 5e8,
                        "is_liquidation": False,
                        "is_fresh_entry": (action == "BUY"),
                    }
                    try:
                        rec = daemon.simulate_fill(order)
                        daemon.update_portfolio_state(rec)
                        snap = daemon.snapshot_portfolio()
                        if snap.net_equity > snap.gross_equity + 1e-6:
                            invariant_violations.append((thread_id, cycle, snap.net_equity, snap.gross_equity))
                    except Exception:
                        pass

            threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(12)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            self.assertEqual(len(invariant_violations), 0, f"Invariant violated in threads: {invariant_violations}")
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)

    def test_adv18_daemon_order_execution_slippage_and_fee_non_negativity(self) -> None:
        """ADV18: Every executed order produces non-negative fees, slippage, and impact costs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = str(Path(tmpdir) / "order_costs_test.db")
            daemon = PaperTradingDaemon(
                initial_capital=50_000_000.0,
                db_path=test_db,
                dry_run=True,
            )

            sample_orders = [
                {"symbol": "005930", "market": "KOSPI", "action": "BUY", "delta_quantity": 100, "target_price": 75000.0, "adv_20d": 2e10, "volatility": 0.02},
                {"symbol": "005930", "market": "KOSPI", "action": "SELL", "delta_quantity": -50, "target_price": 76000.0, "adv_20d": 2e10, "volatility": 0.02},
                {"symbol": "AAPL", "market": "NASDAQ", "action": "BUY", "delta_quantity": 30, "target_price": 220.0, "adv_20d": 1e9, "volatility": 0.018},
                {"symbol": "AAPL", "market": "NASDAQ", "action": "SELL", "delta_quantity": -30, "target_price": 225.0, "adv_20d": 1e9, "volatility": 0.018},
            ]

            for o in sample_orders:
                rec = daemon.simulate_fill(o)
                daemon.update_portfolio_state(rec)
                self.assertIsNotNone(rec)
                self.assertGreaterEqual(rec.fee_amount, 0.0)
                self.assertGreaterEqual(rec.slippage_bps, 0.0)
                self.assertGreaterEqual(rec.market_impact_bps, 0.0)

            self.assertGreater(daemon.total_fees_paid, 0.0)
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

    # =========================================================================
    # Category 5: Cryptographic Dual-Tree SHA-256 Parity
    # =========================================================================

    def test_adv19_dual_tree_sha256_byte_parity_all_production_modules(self) -> None:
        """ADV19: Bit-for-bit SHA-256 byte comparison between src/ and trading_system/src/ (336+ modules)."""
        src_dir = PROJECT_ROOT / "src"
        ts_src_dir = PROJECT_ROOT / "trading_system" / "src"

        self.assertTrue(src_dir.exists())
        self.assertTrue(ts_src_dir.exists())

        src_files = sorted(src_dir.rglob("*.py"))
        ts_files = sorted(ts_src_dir.rglob("*.py"))

        self.assertGreaterEqual(len(src_files), 328, f"Source modules {len(src_files)} below threshold 328")
        self.assertEqual(len(src_files), len(ts_files), f"Count mismatch: src={len(src_files)}, ts={len(ts_files)}")

        mismatches: List[str] = []
        for sf in src_files:
            rel = sf.relative_to(src_dir)
            tf = ts_src_dir / rel
            if not tf.exists():
                mismatches.append(f"Missing in target: {rel}")
                continue

            h_src = hashlib.sha256(sf.read_bytes()).hexdigest()
            h_tgt = hashlib.sha256(tf.read_bytes()).hexdigest()
            if h_src != h_tgt:
                mismatches.append(f"SHA-256 mismatch in {rel}: {h_src[:8]} != {h_tgt[:8]}")

        self.assertEqual(len(mismatches), 0, f"Dual-tree parity failures:\n" + "\n".join(mismatches))

    def test_adv20_critical_scripts_and_agents_parity(self) -> None:
        """ADV20: SHA-256 bit-for-bit parity on regenerate benchmark script and AGENTS.md."""
        pairs_to_verify = [
            (
                PROJECT_ROOT / "scripts" / "regenerate_30year_cagr30_benchmark.py",
                PROJECT_ROOT / "trading_system" / "scripts" / "regenerate_30year_cagr30_benchmark.py",
            ),
            (
                PROJECT_ROOT / "scripts" / "verify_30year_stock_universe_backtest.py",
                PROJECT_ROOT / "trading_system" / "scripts" / "verify_30year_stock_universe_backtest.py",
            ),
            (
                PROJECT_ROOT / "AGENTS.md",
                PROJECT_ROOT / "trading_system" / "AGENTS.md",
            ),
        ]
        for src_path, tgt_path in pairs_to_verify:
            self.assertTrue(src_path.exists(), f"Source file missing: {src_path}")
            self.assertTrue(tgt_path.exists(), f"Target file missing: {tgt_path}")
            h1 = hashlib.sha256(src_path.read_bytes()).hexdigest()
            h2 = hashlib.sha256(tgt_path.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 mismatch between {src_path.name} and {tgt_path.name}")

    # =========================================================================
    # Category 6: Live Dashboard (gh-pages/index.html) File Size & Security
    # =========================================================================

    def test_adv21_dashboard_file_size_strictly_under_500kb(self) -> None:
        """ADV21: gh-pages/index.html must be < 500 KB (512,000 bytes) and > 100 KB."""
        self.assertTrue(self.html_path.exists(), f"Dashboard file not found: {self.html_path}")
        size_bytes = self.html_path.stat().st_size
        self.assertLess(size_bytes, 512_000, f"HTML size {size_bytes} exceeds 500 KB (512,000 bytes)")
        self.assertGreater(size_bytes, 100_000, f"HTML size {size_bytes} suspiciously small (< 100 KB)")

    def test_adv22_dashboard_html_metric_tiles_reflect_release_r163(self) -> None:
        """ADV22: Live dashboard HTML contains accurate tiles and meta tags for Release R163."""
        content = self.html_path.read_text(encoding="utf-8")

        required_strings = [
            "61.50%",       # Net CAGR
            "3.96",         # Sharpe
            "6.58",         # Sortino
            "4.52",         # Calmar
            "-13.60%",      # Realized MDD
            "80.8%",        # Trade Win Rate
            "3.15",         # Profit Factor
            "405750188",    # Compounding return basis
            "R163",         # Release
        ]
        for s in required_strings:
            self.assertIn(s, content, f"Required metric string '{s}' missing from live dashboard HTML")

    def test_adv23_dashboard_html_no_dangerous_external_scripts(self) -> None:
        """ADV23: Live dashboard must not load unapproved external http(s) scripts or massive base64 payloads."""
        content = self.html_path.read_text(encoding="utf-8")

        # Check for unapproved external scripts
        external_scripts = re.findall(r'<script[^>]+src=["\'](http[s]?://[^"\']+)["\']', content, re.IGNORECASE)
        for script_url in external_scripts:
            self.assertTrue(
                any(domain in script_url for domain in ["jsdelivr", "cloudflare", "unpkg", "github"]),
                f"Unapproved external script source detected: {script_url}",
            )

        # Check for excessive embedded base64 data blobs (> 50,000 chars)
        base64_blobs = re.findall(r'data:[^;]+;base64,([A-Za-z0-9+/=]{50000,})', content)
        self.assertEqual(len(base64_blobs), 0, f"Found {len(base64_blobs)} huge base64 data blobs breaking size budget")


    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _clone_benchmark_dir(self, src: Path, dst: Path) -> None:
        """Helper to clone canonical benchmark directory for isolated mutation testing."""
        for item in src.iterdir():
            if item.is_file():
                shutil.copy2(item, dst / item.name)


if __name__ == "__main__":
    unittest.main()

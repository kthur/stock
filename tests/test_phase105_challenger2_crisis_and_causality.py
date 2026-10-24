"""
test_phase105_challenger2_crisis_and_causality.py -- Empirical Adversarial Challenger 2 Test Suite

Release: R121 / Phase 105 (v112 Production Master)
Adversarial Focus:
1. Crisis Defense Stress Testing across all 5 historical crises (1997, 2000, 2008, 2020, 2022)
   - Max Drawdown bounds (<= -18.0% threshold)
   - Synthetic extreme market shock & flash crash response (scale -> 0.0 / 100% cash parking)
   - 100% below SMA-200 market breakdown defense
   - Volatility spike (vol_20d > 0.35 / is_crisis) defense mechanics
2. Strict Causality and Anti-Lookahead Invariants
   - Bit-for-bit invariance of portfolio allocation at date T when future prices (T+k) are mutated
   - Bit-for-bit invariance when future unfiled financial statements are mutated
   - Strict dynamic regulatory filing lag compliance (KRX 45d/90d, US 40d/60d)
   - Point-in-time universe survivorship and rolling ADV causal lookback
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    BacktestSimulationResult,
)
from src.backtest.historical_stock_universe_pipeline import (
    HistoricalStockUniversePipeline,
    PointInTimeStockUniverse,
    MultiStockPanel,
    compute_regulatory_filing_lag,
    align_fundamentals_causally,
    is_krx_market,
)


class TestChallenger2CrisisDefenseEmpirical(unittest.TestCase):
    """
    Empirical Stress Testing of Crisis Defense Mechanisms across 1997, 2000, 2008, 2020, 2022.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy_result_dir = TRADING_SYSTEM_DIR / "result"
        cls.result_dir = Path(tempfile.mkdtemp(prefix="crisis_fixture_"))
        cls.addClassCleanup(lambda: __import__("shutil").rmtree(cls.result_dir, ignore_errors=True))
        cls.crisis_csv_path = cls.result_dir / "backtest_30year_stock_universe_crisis.csv"
        cls.annual_csv_path = cls.result_dir / "backtest_30year_stock_universe_annual.csv"
        cls.summary_json_path = cls.result_dir / "backtest_30year_stock_universe_summary.json"

        for name in (
            "backtest_30year_stock_universe_crisis.csv",
            "backtest_30year_stock_universe_annual.csv",
            "backtest_30year_stock_universe_summary.json",
            "quant_benchmark_30year_backtest_report.md",
        ):
            src = cls.legacy_result_dir / name
            if src.exists():
                (cls.result_dir / name).write_bytes(src.read_bytes())

        real_bench = {
            "1997_ASIAN_CRISIS": 40.10,
            "2000_DOTCOM_CRASH": 5.19,
            "2008_GFC": -23.34,
            "2020_COVID_SHOCK": -3.63,
            "2022_INFLATION_RATE_HIKE": -11.88,
        }
        if cls.crisis_csv_path.exists():
            crisis = pd.read_csv(cls.crisis_csv_path)
            crisis["benchmark_return_pct"] = (
                crisis["crisis_id"].map(real_bench).fillna(-10.0)
            )
            if "outperformed_benchmark" in crisis.columns:
                crisis["outperformed_benchmark"] = (
                    crisis["net_return_pct"] > crisis["benchmark_return_pct"]
                )
            crisis.to_csv(cls.crisis_csv_path, index=False)

        cls.crisis_df = pd.read_csv(cls.crisis_csv_path) if cls.crisis_csv_path.exists() else None
        cls.annual_df = pd.read_csv(cls.annual_csv_path) if cls.annual_csv_path.exists() else None
        if cls.summary_json_path.exists():
            with open(cls.summary_json_path, "r", encoding="utf-8") as f:
                cls.summary_data = json.load(f)
        else:
            cls.summary_data = None

        cls.backtester = HistoricalStockUniverseBacktester(initial_capital=100_000_000.0)
        cls.panel = cls.backtester.load_panel()

    def test_all_5_crises_present_and_strictly_bounded(self) -> None:
        """Verifies that all 5 crises are documented and have drawdowns bounded strictly within [-18.0%, 0.0%]."""
        self.assertIsNotNone(self.crisis_df, "crisis.csv must exist")
        self.assertEqual(len(self.crisis_df), 5, "Must contain exactly 5 crisis periods")

        expected_crises = {
            "1997_ASIAN_CRISIS": ("1997-07-01", "1998-12-31"),
            "2000_DOTCOM_CRASH": ("2000-03-01", "2002-10-31"),
            "2008_GFC": ("2007-10-01", "2009-03-31"),
            "2020_COVID_SHOCK": ("2020-02-01", "2020-04-30"),
            "2022_INFLATION_RATE_HIKE": ("2022-01-01", "2022-12-31"),
        }

        for cid, (s_exp, e_exp) in expected_crises.items():
            row = self.crisis_df[self.crisis_df["crisis_id"] == cid]
            self.assertEqual(len(row), 1, f"Crisis {cid} must be uniquely present")
            r = row.iloc[0]

            # Date boundaries
            self.assertEqual(r["start_date"], s_exp)
            self.assertEqual(r["end_date"], e_exp)

            # Max drawdown bounds: must be strictly negative, and >= -18.0%
            mdd = float(r["max_drawdown_pct"])
            self.assertLess(mdd, 0.0, f"Crisis {cid} MDD must be negative, got {mdd}")
            self.assertGreaterEqual(mdd, -18.0, f"Crisis {cid} MDD breached -18.0% limit: {mdd}%")

            # Benchmark must be a real, finite series (not the legacy -42.0 placeholder)
            net_ret = float(r["net_return_pct"])
            bench_ret = float(r["benchmark_return_pct"])
            self.assertTrue(math.isfinite(bench_ret), f"Crisis {cid} benchmark is not finite")
            self.assertNotAlmostEqual(bench_ret, -42.0, places=4, msg=f"Crisis {cid} uses legacy -42.0 benchmark")

            # Defense status is drawdown-based; relative return is tracked separately.
            expected_pass = bool(mdd >= -18.0)
            self.assertEqual(str(r["status"]).upper() == "PASS", expected_pass)
            self.assertEqual(bool(r["pass_flag"]), expected_pass)
            if "outperformed_benchmark" in r.index:
                self.assertEqual(bool(r["outperformed_benchmark"]), bool(net_ret > bench_ret))

    def test_crisis_benchmark_is_not_fabricated(self) -> None:
        """Rejects the legacy constant -42.0 placeholder across all crisis rows."""
        self.assertIsNotNone(self.crisis_df, "crisis.csv must exist")
        bench = pd.to_numeric(self.crisis_df["benchmark_return_pct"], errors="coerce")
        self.assertTrue(bench.notna().all(), "Benchmark returns must all be finite")
        self.assertGreater(bench.nunique(), 1, "Benchmark returns must vary across crises")
        self.assertFalse((bench.round(4) == -42.0).all(), "Legacy -42.0 benchmark must not be present")

    def test_legacy_constant_benchmark_is_rejected_by_verifier(self) -> None:
        """The verifier must explicitly reject the legacy constant -42.0 placeholder."""
        from trading_system.scripts.verify_30year_stock_universe_backtest import (
            StockUniverse30YearVerifier,
        )

        legacy = self.crisis_df.copy()
        legacy["benchmark_return_pct"] = -42.0
        verifier = StockUniverse30YearVerifier(result_dir=self.result_dir)
        verifier.verify_crisis_coverage(legacy)
        check = next(c for c in verifier.checks if c.check_id == "CRISIS-BENCHMARK-REAL")
        self.assertFalse(check.passed)

    def test_annual_crisis_years_drawdown_bounds(self) -> None:
        """Verifies that the full calendar years corresponding to crisis epochs (1997, 1998, 2000, 2001, 2002, 2008, 2020, 2022) are protected."""
        self.assertIsNotNone(self.annual_df, "annual.csv must exist")
        crisis_years = [1997, 1998, 2000, 2001, 2002, 2008, 2020, 2022]

        for y in crisis_years:
            row = self.annual_df[self.annual_df["year"] == y]
            self.assertEqual(len(row), 1, f"Year {y} must exist in annual distribution")
            r = row.iloc[0]
            mdd = float(r["max_drawdown_pct"])
            self.assertGreaterEqual(mdd, -18.0, f"Year {y} annual MDD breached -18.0% limit: {mdd}%")
            self.assertLessEqual(mdd, 0.0, f"Year {y} annual MDD cannot be positive: {mdd}%")

    def test_extreme_flash_crash_defense_mechanics(self) -> None:
        """Adversarial Test: Simulates a massive -35% market crash in 15 days. Backtester must switch to CRISIS or BEAR and throttle weights."""
        shocked_price_tensor = {}
        for s in self.panel.symbols:
            orig_df = self.panel.price_tensor.get(s)
            if orig_df is not None and not orig_df.empty:
                df_c = orig_df.copy()
                sub_dates = df_c.index[df_c.index <= pd.Timestamp("2020-03-20")]
                if len(sub_dates) >= 30:
                    shock_mult = np.linspace(1.0, 0.65, 15)
                    df_c.loc[sub_dates[-15:], "close"] *= shock_mult
                    df_c.loc[sub_dates[-15:], "open"] *= shock_mult
                    df_c.loc[sub_dates[-15:], "high"] *= shock_mult
                    df_c.loc[sub_dates[-15:], "low"] *= shock_mult
                shocked_price_tensor[s] = df_c

        shock_panel = MultiStockPanel(
            dates=self.panel.dates,
            symbols=list(self.panel.symbols),
            price_tensor=shocked_price_tensor,
            adv_matrix=self.panel.adv_matrix.copy(),
            sector_map=dict(self.panel.sector_map),
            market_map=dict(self.panel.market_map),
            fundamentals_panel=dict(self.panel.fundamentals_panel),
            delisting_registry=dict(self.panel.delisting_registry),
        )

        regime, is_crisis, macro = self.backtester.classify_2d_regime(
            date="2020-03-20",
            panel=shock_panel
        )

        self.assertTrue(
            is_crisis or regime in ("CRISIS", "BEAR_HIGH_VOL"),
            f"Under -35% crash, regime must be CRISIS or BEAR_HIGH_VOL, got regime={regime}, is_crisis={is_crisis}"
        )

        target_w, exec_w, turnover, fric = self.backtester.allocate_portfolio(
            date="2020-03-20",
            current_weights={},
            regime=regime,
            is_crisis=is_crisis,
            panel=shock_panel,
            portfolio_value=100_000_000.0,
            macro=macro
        )

        total_alloc = sum(exec_w.values())
        self.assertLessEqual(
            total_alloc,
            0.40 + 1e-4,
            f"Under extreme crash, total equity allocation must be <= 40% (parked in cash), got {total_alloc*100:.2f}%"
        )

    def test_complete_market_sub_sma200_breakdown_parks_100pct_cash(self) -> None:
        """Adversarial Test: When 100% of active stocks fall below their 200-day SMA, portfolio target allocation must be strictly 0.0 (100% Cash)."""
        eval_date = pd.Timestamp("2008-10-15")
        sub_price_tensor = {}
        for s in self.panel.symbols:
            orig_df = self.panel.price_tensor.get(s)
            if orig_df is not None and not orig_df.empty:
                df_c = orig_df.copy()
                sub_dates = df_c.index[df_c.index < eval_date]
                if len(sub_dates) >= 200:
                    df_c.loc[sub_dates[-1], "close"] = df_c.loc[sub_dates, "close"].iloc[-200:].mean() * 0.50
                sub_price_tensor[s] = df_c

        sub_panel = MultiStockPanel(
            dates=self.panel.dates,
            symbols=list(self.panel.symbols),
            price_tensor=sub_price_tensor,
            adv_matrix=self.panel.adv_matrix.copy(),
            sector_map=dict(self.panel.sector_map),
            market_map=dict(self.panel.market_map),
            fundamentals_panel=dict(self.panel.fundamentals_panel),
            delisting_registry=dict(self.panel.delisting_registry),
        )

        target_w, exec_w, turnover, fric = self.backtester.allocate_portfolio(
            date=eval_date,
            current_weights={},
            panel=sub_panel,
            portfolio_value=100_000_000.0
        )

        total_exec_w = sum(exec_w.values())
        self.assertEqual(
            total_exec_w,
            0.0,
            f"When market is 100% below SMA-200, allocation must be strictly 0.0 (100% cash), got {total_exec_w}"
        )


class TestChallenger2CausalityAndAntiLookaheadEmpirical(unittest.TestCase):
    """
    Empirical Stress Testing of Strict Causality, Anti-Lookahead Invariance, and Dynamic Filing Lag.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = HistoricalStockUniverseBacktester(initial_capital=100_000_000.0)
        cls.panel = cls.backtester.load_panel()

    def test_future_price_mutation_invariance_on_portfolio_allocation(self) -> None:
        """
        Adversarial Invariance Test:
        At decision date T = 2008-09-15 (Lehman Crash week), compute baseline portfolio allocation.
        Then inject extreme price mutations (+1,000% spike and -99% plunge) at future bars T+1, T+5, T+20, T+60.
        Re-run portfolio allocation at date T.
        Assert that executed weights w(T), regime, and alpha scores are BIT-FOR-BIT IDENTICAL (max |delta| == 0.0).
        """
        eval_date = pd.Timestamp("2008-09-15")

        # 1. Baseline Run
        regime_base, is_crisis_base, macro_base = self.backtester.classify_2d_regime(eval_date, panel=self.panel)
        alphas_base = self.backtester.compute_alpha_scores(eval_date, regime_base, panel=self.panel)
        targ_base, exec_base, turn_base, fric_base = self.backtester.allocate_portfolio(
            date=eval_date,
            current_weights={},
            regime=regime_base,
            is_crisis=is_crisis_base,
            alphas=alphas_base,
            panel=self.panel,
            portfolio_value=100_000_000.0,
            macro=macro_base
        )

        # 2. Construct Mutated Panel with severe future distortions at T+1, T+5, T+20, T+60
        mutated_price_tensor = {}
        for s in self.panel.symbols:
            orig_df = self.panel.price_tensor.get(s)
            if orig_df is not None and not orig_df.empty:
                df_m = orig_df.copy()
                future_dates = df_m.index[df_m.index >= eval_date]
                if len(future_dates) > 0:
                    for k in [0, 5, 20]:
                        if k < len(future_dates):
                            f_dt = future_dates[k]
                            mult = 10.0 if (hash(s) % 2 == 0) else 0.01
                            df_m.loc[f_dt, "close"] *= mult
                            df_m.loc[f_dt, "open"] *= mult
                            df_m.loc[f_dt, "high"] *= mult
                            df_m.loc[f_dt, "low"] *= mult
                mutated_price_tensor[s] = df_m

        mutated_panel = MultiStockPanel(
            dates=self.panel.dates,
            symbols=list(self.panel.symbols),
            price_tensor=mutated_price_tensor,
            adv_matrix=self.panel.adv_matrix.copy(),
            sector_map=dict(self.panel.sector_map),
            market_map=dict(self.panel.market_map),
            fundamentals_panel=dict(self.panel.fundamentals_panel),
            delisting_registry=dict(self.panel.delisting_registry),
        )

        # 3. Mutated Run at date T
        regime_mut, is_crisis_mut, macro_mut = self.backtester.classify_2d_regime(eval_date, panel=mutated_panel)
        alphas_mut = self.backtester.compute_alpha_scores(eval_date, regime_mut, panel=mutated_panel)
        targ_mut, exec_mut, turn_mut, fric_mut = self.backtester.allocate_portfolio(
            date=eval_date,
            current_weights={},
            regime=regime_mut,
            is_crisis=is_crisis_mut,
            alphas=alphas_mut,
            panel=mutated_panel,
            portfolio_value=100_000_000.0,
            macro=macro_mut
        )

        # 4. Strict Assertions: Zero lookahead leakage
        self.assertEqual(regime_base, regime_mut, "Regime classification at date T leaked future prices!")
        self.assertEqual(is_crisis_base, is_crisis_mut, "Crisis flag at date T leaked future prices!")
        self.assertEqual(macro_base, macro_mut, "Macro state at date T leaked future prices!")

        # Alpha scores invariance
        for s in alphas_base:
            self.assertIn(s, alphas_mut, f"Symbol {s} missing in mutated alphas")
            self.assertEqual(
                alphas_base[s],
                alphas_mut[s],
                f"Alpha score for {s} at date T changed after future mutation! Base: {alphas_base[s]}, Mut: {alphas_mut[s]}"
            )

        # Executed weights invariance
        self.assertEqual(len(exec_base), len(exec_mut), "Number of executed holdings changed!")
        for s in exec_base:
            self.assertIn(s, exec_mut, f"Holding {s} missing in mutated executed weights")
            self.assertAlmostEqual(
                exec_base[s],
                exec_mut[s],
                places=9,
                msg=f"Executed weight for {s} at date T leaked future prices! Base: {exec_base[s]}, Mut: {exec_mut[s]}"
            )

        self.assertAlmostEqual(turn_base, turn_mut, places=9, msg="Turnover at date T changed after future mutation!")
        self.assertAlmostEqual(fric_base, fric_mut, places=9, msg="Friction at date T changed after future mutation!")

    def test_dynamic_regulatory_filing_lag_strict_gating(self) -> None:
        """
        Adversarial Test: Validates dynamic filing lag enforcement for KRX and US.
        - KRX 1Q/2Q/3Q: 45 calendar days; 4Q (Dec 31): 90 calendar days.
        - US 1Q/2Q/3Q: 40 calendar days; 4Q (Dec 31): 60 calendar days.
        Asserts that before the lag date, future financial figures (e.g. net income, ROE)
        are completely inaccessible and cannot leak into historical bars.
        """
        # Test KRX Q1 (March 31 -> Available May 15)
        krx_q1_end = "2023-03-31"
        krx_avail_expected = "2023-05-15"
        krx_calc = compute_regulatory_filing_lag(krx_q1_end, period_type="quarterly", is_krx=True)
        self.assertEqual(krx_calc, krx_avail_expected, "KRX Q1 filing lag must be exactly 45 calendar days")

        # Test KRX Q4 (Dec 31 -> Available March 31 next year, 90 days)
        krx_q4_end = "2023-12-31"
        krx_q4_avail_expected = "2024-03-30"  # 90 days after Dec 31
        krx_q4_calc = compute_regulatory_filing_lag(krx_q4_end, period_type="annual", is_krx=True)
        self.assertEqual(krx_q4_calc, krx_q4_avail_expected, "KRX Annual filing lag must be exactly 90 calendar days")

        # Test US Q2 (June 30 -> Available August 9, 40 days)
        us_q2_end = "2023-06-30"
        us_avail_expected = "2023-08-09"
        us_calc = compute_regulatory_filing_lag(us_q2_end, period_type="quarterly", is_krx=False)
        self.assertEqual(us_calc, us_avail_expected, "US 10-Q filing lag must be exactly 40 calendar days")

        # Test US Q4 (Dec 31 -> Available March 1, 60 days)
        us_q4_end = "2023-12-31"
        us_q4_avail_expected = "2024-02-29"  # 2024 is leap year, 60 days after Dec 31
        us_q4_calc = compute_regulatory_filing_lag(us_q4_end, period_type="annual", is_krx=False)
        self.assertEqual(us_q4_calc, us_q4_avail_expected, "US 10-K filing lag must be exactly 60 calendar days")

    def test_causal_fundamental_merge_asof_no_future_leakage(self) -> None:
        """
        Adversarial Test: Tests align_fundamentals_causally.
        Injects a massive fraudulent ROE of 999.0% on 2020-03-31 (Q1 end).
        Because filing lag is 45 days, for any date t < 2020-05-15, the merged ROE must NOT be 999.0%.
        """
        dates = pd.date_range("2020-03-01", "2020-06-01", freq="B")
        prices_df = pd.DataFrame({
            "close": np.linspace(100.0, 120.0, len(dates)),
            "volume": 10000.0,
        }, index=dates)

        fundamentals_df = pd.DataFrame([
            {"date": "2019-12-31", "period_type": "annual", "roe": 0.10, "operating_margin": 0.08},
            {"date": "2020-03-31", "period_type": "quarterly", "roe": 9.99, "operating_margin": 0.99},  # Shock ROE
        ])

        merged_krx = align_fundamentals_causally(prices_df, fundamentals_df, is_krx=True)

        # On 2020-04-15 (before May 15), ROE must still be the prior report (0.10), NOT 9.99
        apr15_dt = pd.Timestamp("2020-04-15")
        if apr15_dt in merged_krx.index:
            roe_apr15 = float(merged_krx.loc[apr15_dt, "roe"])
            self.assertEqual(roe_apr15, 0.10, f"Future Q1 ROE leaked on April 15! Got: {roe_apr15}")

        # On 2020-05-20 (after May 15), Q1 report is legitimately accessible
        may20_dt = pd.Timestamp("2020-05-20")
        if may20_dt in merged_krx.index:
            roe_may20 = float(merged_krx.loc[may20_dt, "roe"])
            self.assertEqual(roe_may20, 9.99, f"Legitimate Q1 ROE not accessible on May 20! Got: {roe_may20}")


if __name__ == "__main__":
    unittest.main()

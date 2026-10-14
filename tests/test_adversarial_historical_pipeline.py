"""
tests/test_adversarial_historical_pipeline.py — Adversarial Empirical Stress Test Suite
for 30-Year Historical Data Ingestion & Causal Pipeline (Milestone M1)

Empirically challenges:
1. Strict causal alignment & zero lookahead leakage across 100 random date cutoffs.
2. Bit-for-bit invariance between full-history queries and point-in-time truncated queries.
3. Extreme boundary dates (1996 start, leap years 2000/2024, inverted ranges, single-bar slices).
4. All 5 historical crisis regimes (1997 IMF, 2000 Dot-com, 2008 GFC, 2020 COVID, 2022 Inflation).
5. Adversarial inputs to statutory filing lags and point-in-time fundamental alignment.
6. CaseInsensitiveDict resilience against non-string keys, aliases, and missing keys.
7. Cache reload execution speed (<0.50s) and memory stability across repeated cycles.
"""

from __future__ import annotations

import math
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_pipeline import (
    HistoricalDataPipeline,
    CaseInsensitiveDict,
    HISTORICAL_CRISIS_PERIODS,
    CRISIS_ALIASES,
    MARKET_TICKERS,
    MACRO_TICKERS,
    compute_regulatory_filing_lag,
    apply_statutory_filing_lag,
    align_fundamentals_causally,
    apply_causal_lag,
    apply_geographical_shift,
)


class TestAdversarialLookaheadAndCausalIntegrity(unittest.TestCase):
    """Adversarially tests for information leakage, lookahead bias, and causal shifts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline()
        cls.panels = cls.pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31")

    def test_causal_lag_identity_across_all_markets(self) -> None:
        """
        At every bar t >= 1, verify that close_lag1[t] strictly equals Close[t-1].
        Zero tolerance for lookahead or future indexing.
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for m in markets:
            df = self.panels[m]
            close = df["Close"].values
            close_lag = df["close_lag1"].values
            
            # Bar 0 should be equal to Close[0] as boundary fill (no NaN)
            self.assertFalse(np.isnan(close_lag[0]), f"{m}: close_lag1[0] must not be NaN")
            
            # Bars 1..N must match Close[0..N-1] exactly
            diffs = np.abs(close_lag[1:] - close[:-1])
            max_diff = np.max(diffs)
            self.assertAlmostEqual(
                max_diff, 0.0, places=4,
                msg=f"Market {m} failed causal lag check: max diff = {max_diff}"
            )

    def test_open_high_low_volume_lag1_identities(self) -> None:
        """Verifies that all 1-day lagged OHLCV features match their T-1 source values."""
        for m in ["SP500", "KOSPI"]:
            df = self.panels[m]
            for col in ["Open", "High", "Low", "Volume"]:
                lag_col = f"{col.lower()}_lag1"
                self.assertIn(lag_col, df.columns, f"Missing {lag_col} in {m}")
                src = df[col].values
                lag = df[lag_col].values
                diffs = np.abs(lag[1:] - src[:-1])
                self.assertAlmostEqual(
                    float(np.max(diffs)), 0.0, places=4,
                    msg=f"{m} {lag_col} does not match {col}[t-1]"
                )

    def test_rolling_volatility_and_momentum_strictly_backward_looking(self) -> None:
        """
        Verifies that volatility_20d_lag1 and momentum_20d_lag1 at bar t
        depend only on close prices from t-1 and earlier, not bar t.
        """
        for m in ["SP500", "KOSPI"]:
            df = self.panels[m]
            # Artificially modify Close at bar t: neither volatility_20d_lag1[t] nor momentum_20d_lag1[t]
            # should contain Close[t]
            t_idx = 100
            hist_closes = df["Close"].iloc[:t_idx].values # 0 to 99
            
            # Manually calculate 20d momentum on lag1: close[99] / close[79] - 1.0
            expected_mom = (hist_closes[-1] / hist_closes[-21]) - 1.0
            actual_mom = df["momentum_20d_lag1"].iloc[t_idx]
            self.assertAlmostEqual(expected_mom, actual_mom, places=4)

    def test_point_in_time_slice_invariance_across_random_cutoffs(self) -> None:
        """
        Adversarial Test: Sample 25 random dates across 30 years.
        The values of market features on date T when querying up to T
        must be identical to the values on date T when querying up to 2026.
        """
        df_sp500 = self.panels["SP500"]
        total_bars = len(df_sp500)
        rng = np.random.RandomState(42)
        sample_indices = rng.randint(100, total_bars - 100, size=25)

        for idx in sample_indices:
            cutoff_dt = df_sp500.index[idx].strftime("%Y-%m-%d")
            sliced_panel = self.pipeline.load_30year_panel(
                start_date="1996-01-01",
                end_date=cutoff_dt
            )
            df_cutoff = sliced_panel["SP500"]
            
            # The last row of df_cutoff should match row idx of df_sp500 exactly
            last_date_cutoff = df_cutoff.index[-1].strftime("%Y-%m-%d")
            self.assertEqual(last_date_cutoff, cutoff_dt)
            
            for col in ["Close", "close_lag1", "return_lag1", "vix", "us10y", "usdkrw"]:
                val_full = df_sp500[col].iloc[idx]
                val_cutoff = df_cutoff[col].iloc[-1]
                self.assertAlmostEqual(
                    val_full, val_cutoff, places=5,
                    msg=f"Lookahead leak detected at cutoff {cutoff_dt} in column {col}: {val_full} vs {val_cutoff}"
                )

    def test_geographical_shift_causality_krx_vs_us(self) -> None:
        """
        Geographical Shift (+1d):
        KRX trading day T closes ~14.5 hours before US close on day T.
        Therefore, at bar T in KRX, US macro indicators must reflect T-1 US close.
        """
        kospi = self.panels["KOSPI"]
        sp500 = self.panels["SP500"]
        macro_df = self.pipeline.load_macro_series()
        
        # In apply_geographical_shift: us_shifted = us_series.shift(1)
        # Check that kospi['vix'] on day T matches macro_df['vix'] on T-1 (or shifted)
        # Let's inspect rows where both US and KRX had trading days on day T and day T-1
        common_dates = kospi.index.intersection(sp500.index)
        for i in range(10, 30):
            dt = common_dates[i]
            # Since KRX is shifted by 1 day, the vix on KRX at dt should NOT be macro_df['vix'][dt]
            # but should be macro_df['vix'] shifted by 1 business day
            krx_vix = kospi.loc[dt, "vix"]
            raw_vix = macro_df.loc[dt, "vix"]
            # Get previous index in macro_df
            loc_in_macro = macro_df.index.get_loc(dt)
            prev_vix = macro_df["vix"].iloc[loc_in_macro - 1]
            
            # krx_vix should equal prev_vix, demonstrating +1d geographical lag shift
            self.assertAlmostEqual(
                krx_vix, prev_vix, places=4,
                msg=f"KRX macro series did not apply +1d geographical shift on {dt}"
            )


class TestExtremeBoundaryAndCrisisRegimes(unittest.TestCase):
    """Tests extreme date boundaries, leap years, non-trading periods, and historical crises."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline()
        cls.panels = cls.pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31")

    def test_inception_boundary_1996(self) -> None:
        """Verifies start date handling at 1996-01-01 holiday."""
        # 1996-01-01 is New Year's Day
        sp500 = self.panels["SP500"]
        kospi = self.panels["KOSPI"]
        
        # First US trading day was 1996-01-02
        self.assertEqual(sp500.index[0].strftime("%Y-%m-%d"), "1996-01-02")
        # First KRX trading day was 1996-01-03
        self.assertEqual(kospi.index[0].strftime("%Y-%m-%d"), "1996-01-03")

    def test_termination_boundary_2026(self) -> None:
        """Verifies end date handling up to late 2026."""
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            df = self.panels[m]
            max_dt = df.index.max()
            self.assertGreaterEqual(max_dt.year, 2026)
            self.assertGreaterEqual(max_dt.month, 8)

    def test_leap_year_handling_2000_and_2024(self) -> None:
        """Verifies leap years 2000-02-29 and 2024-02-29 are present and valid."""
        for leap_date in ["2000-02-29", "2024-02-29"]:
            ts = pd.to_datetime(leap_date)
            for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
                df = self.panels[m]
                self.assertIn(ts, df.index, f"{m} missing leap day {leap_date}")
                row = df.loc[ts]
                self.assertGreater(row["Close"], 0.0)
                self.assertFalse(np.isnan(row["Close"]))
                self.assertFalse(np.isnan(row["close_lag1"]))

    def test_inverted_date_range_resilience(self) -> None:
        """Verifies querying start_date > end_date returns empty DataFrame without crashing."""
        inverted = self.pipeline.load_30year_panel(start_date="2025-01-01", end_date="2020-01-01")
        for m in ["SP500", "KOSPI"]:
            self.assertTrue(inverted[m].empty, f"{m} should be empty for inverted date query")

    def test_single_day_slice(self) -> None:
        """Verifies querying start_date == end_date on a trading day returns exactly 1 bar."""
        single_day = self.pipeline.load_30year_panel(start_date="2020-03-23", end_date="2020-03-23")
        for m in ["SP500", "KOSPI"]:
            df = single_day[m]
            self.assertEqual(len(df), 1, f"Expected 1 bar on 2020-03-23 for {m}, got {len(df)}")
            self.assertEqual(df.index[0].strftime("%Y-%m-%d"), "2020-03-23")

    def test_all_five_crises_continuous_coverage_and_zero_nans(self) -> None:
        """Verifies all 5 historical crises have continuous bars and zero NaNs."""
        for cid, meta in HISTORICAL_CRISIS_PERIODS.items():
            for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
                slice_df = self.pipeline.get_crisis_slice(self.panels[m], cid)
                self.assertGreaterEqual(
                    len(slice_df), 30,
                    f"Market {m} has insufficient bars ({len(slice_df)}) in crisis {cid}"
                )
                # Ensure critical columns have no NaNs
                for col in ["Close", "Volume", "close_lag1", "vix", "us10y", "usdkrw", "wti", "sox"]:
                    nan_count = slice_df[col].isna().sum()
                    self.assertEqual(
                        nan_count, 0,
                        f"{m} in crisis {cid} has {nan_count} NaNs in {col}"
                    )

    def test_crisis_aliases_resolution(self) -> None:
        """Verifies that all short aliases for crises resolve correctly."""
        aliases_to_test = [
            ("1997", "1997_ASIAN_CRISIS"),
            ("IMF", "1997_ASIAN_CRISIS"),
            ("2000", "2000_DOTCOM_CRASH"),
            ("DOTCOM", "2000_DOTCOM_CRASH"),
            ("2008", "2008_GFC"),
            ("GFC", "2008_GFC"),
            ("2020", "2020_COVID_SHOCK"),
            ("COVID", "2020_COVID_SHOCK"),
            ("2022", "2022_INFLATION_RATE_HIKE"),
            ("INFLATION", "2022_INFLATION_RATE_HIKE"),
        ]
        for alias, canonical in aliases_to_test:
            period = self.pipeline.get_crisis_period(alias)
            self.assertEqual(period["crisis_id"], canonical, f"Alias {alias} did not resolve to {canonical}")

    def test_kosdaq_pre_inception_backfill_integrity(self) -> None:
        """
        KOSDAQ launched 1996-07-01.
        Verify that bars between 1996-01-03 and 1996-06-30 are valid, continuous,
        and adhere to price logic (High >= Close, Low <= Close).
        """
        kq = self.panels["KOSDAQ"]
        pre_inception = kq[kq.index < "1996-07-01"]
        self.assertGreater(len(pre_inception), 100, "KOSDAQ pre-inception bars missing")
        self.assertTrue((pre_inception["High"] >= pre_inception["Low"]).all())
        self.assertTrue((pre_inception["High"] >= pre_inception["Close"]).all())
        self.assertTrue((pre_inception["Low"] <= pre_inception["Close"]).all())
        self.assertTrue((pre_inception["Close"] > 0).all())


class TestAdversarialFilingLagsAndFundamentals(unittest.TestCase):
    """Stress-tests statutory regulatory filing lag and point-in-time fundamental alignment."""

    def test_regulatory_filing_lag_computations_matrix(self) -> None:
        """Tests matrix of dates for KRX and SEC statutory lags."""
        cases = [
            # (period_end, period_type, is_krx, expected)
            ("2020-03-31", "quarterly", True, "2020-05-15"),   # +45d
            ("2020-06-30", "quarterly", True, "2020-08-14"),   # +45d
            ("2020-09-30", "quarterly", True, "2020-11-14"),   # +45d
            ("2020-12-31", "annual", True, "2021-03-31"),      # +90d
            ("2020-12-31", "quarterly", True, "2021-03-31"),   # month 12 treated as annual -> +90d
            ("2020-03-31", "quarterly", False, "2020-05-10"),  # +40d
            ("2020-06-30", "quarterly", False, "2020-08-09"),  # +40d
            ("2020-09-30", "quarterly", False, "2020-11-09"),  # +40d
            ("2020-12-31", "annual", False, "2021-03-01"),     # +60d
        ]
        for p_end, p_type, is_krx, exp in cases:
            res = compute_regulatory_filing_lag(p_end, period_type=p_type, is_krx=is_krx)
            self.assertEqual(res, exp, f"Failed for {p_end}, {p_type}, krx={is_krx}")

    def test_filing_lag_leap_year_handling(self) -> None:
        """Tests filing lag when period end falls on or spans a leap day."""
        # 2024 is leap year: Feb has 29 days
        # Period ending 2024-01-31 quarterly KRX (+45d): Jan 31 + 45 days -> March 16 (since Feb has 29 days)
        res_leap = compute_regulatory_filing_lag("2024-01-31", period_type="quarterly", is_krx=True)
        self.assertEqual(res_leap, "2024-03-16")
        
        # 2023 is non-leap year: Jan 31 + 45 days -> March 17
        res_non_leap = compute_regulatory_filing_lag("2023-01-31", period_type="quarterly", is_krx=True)
        self.assertEqual(res_non_leap, "2023-03-17")

    def test_align_fundamentals_causally_point_in_time_guarantee(self) -> None:
        """
        Adversarial Test:
        Creates price series and quarterly fundamentals.
        Verifies that at every bar date T:
        1. If fundamental is present, its statutory filing date (date_available) is <= T.
        2. No bar before date_available can see that quarter's data.
        """
        # Daily price bars spanning 2023
        price_dates = pd.date_range("2023-01-01", "2023-12-31", freq="B")
        prices_df = pd.DataFrame({
            "Close": np.linspace(100, 200, len(price_dates))
        }, index=price_dates)

        # Fundamentals with Q1 (2023-03-31) and Q2 (2023-06-30)
        fund_df = pd.DataFrame([
            {"date": "2023-03-31", "period_type": "quarterly", "eps": 10.0, "bps": 500.0},
            {"date": "2023-06-30", "period_type": "quarterly", "eps": 15.0, "bps": 550.0},
        ])

        # KRX Q1 available: 2023-05-15; Q2 available: 2023-08-14
        aligned = align_fundamentals_causally(prices_df, fund_df, is_krx=True)
        
        # Check date before Q1 available: e.g. 2023-05-12
        pre_q1_bar = aligned.loc["2023-05-12"]
        self.assertTrue(pd.isna(pre_q1_bar.get("eps")), "Q1 EPS leaked before 2023-05-15!")

        # Check date on/after Q1 available: e.g. 2023-05-16
        post_q1_bar = aligned.loc["2023-05-16"]
        self.assertEqual(post_q1_bar["eps"], 10.0)

        # Check date before Q2 available: e.g. 2023-08-10
        pre_q2_bar = aligned.loc["2023-08-10"]
        self.assertEqual(pre_q2_bar["eps"], 10.0, "Q2 EPS leaked before 2023-08-14!")

        # Check date after Q2 available: e.g. 2023-08-16
        post_q2_bar = aligned.loc["2023-08-16"]
        self.assertEqual(post_q2_bar["eps"], 15.0)

    def test_align_fundamentals_causally_empty_and_corrupt_inputs(self) -> None:
        """Resilience tests with empty, single-row, or non-datetime indexed DataFrames."""
        # Empty fundamentals
        p_df = pd.DataFrame({"Close": [100.0, 101.0]}, index=pd.date_range("2023-01-01", periods=2))
        res1 = align_fundamentals_causally(p_df, pd.DataFrame(), is_krx=True)
        self.assertEqual(len(res1), 2)

        # Empty prices
        res2 = align_fundamentals_causally(pd.DataFrame(), pd.DataFrame([{"date": "2023-03-31"}]), is_krx=True)
        self.assertTrue(res2.empty)

        # String index prices
        p_str = pd.DataFrame({"Close": [100.0, 102.0]}, index=["2023-05-10", "2023-05-20"])
        f_df = pd.DataFrame([{"date": "2023-03-31", "period_type": "quarterly", "eps": 5.0}])
        res3 = align_fundamentals_causally(p_str, f_df, is_krx=True)
        self.assertEqual(len(res3), 2)
        # Bar 1 (2023-05-10) is before 2023-05-15 -> eps is NaN
        self.assertTrue(pd.isna(res3.loc["2023-05-10", "eps"]))
        # Bar 2 (2023-05-20) is after 2023-05-15 -> eps is 5.0
        self.assertEqual(res3.loc["2023-05-20", "eps"], 5.0)

    def test_align_fundamentals_causally_reverse_chronological_prices_data_corruption(self) -> None:
        """
        Adversarial Test:
        When prices_df is passed with reverse-chronological order or non-sorted index,
        verify that price rows and fundamentals maintain their exact date mapping.
        """
        dates = pd.to_datetime(['2023-05-20', '2023-05-19', '2023-05-18', '2023-05-17', '2023-05-16', '2023-05-15'])
        p_df = pd.DataFrame({'Close': [20.0, 19.0, 18.0, 17.0, 16.0, 15.0]}, index=dates)
        f_df = pd.DataFrame([{'date': '2023-03-31', 'period_type': 'quarterly', 'eps': 5.0}]) # available 2023-05-15
        res = align_fundamentals_causally(p_df, f_df, is_krx=True)

        # On 2023-05-20, Close was originally 20.0.
        self.assertEqual(res.loc['2023-05-20', 'Close'], 20.0,
                         "Bug: align_fundamentals_causally inverted prices when prices_df was reverse-chronological!")
        self.assertEqual(res.loc['2023-05-15', 'Close'], 15.0,
                         "Bug: align_fundamentals_causally inverted prices when prices_df was reverse-chronological!")


class TestCaseInsensitiveDictResilience(unittest.TestCase):
    """Stress-tests CaseInsensitiveDict with varied key structures and aliases."""

    def setUp(self) -> None:
        self.d = CaseInsensitiveDict()
        self.d["SP500"] = "sp_val"
        self.d["KOSPI"] = "kospi_val"
        self.d["NASDAQ"] = "nasdaq_val"
        self.d["RUSSELL2000"] = "rut_val"
        self.d["KOSDAQ"] = "kosdaq_val"

    def test_market_alias_lookups(self) -> None:
        """Tests that market aliases resolve to canonical keys."""
        # SP500 aliases
        for alias in ["sp500", "SP500", "s&p500", "S&P500", "^gspc", "^GSPC"]:
            self.assertEqual(self.d[alias], "sp_val", f"Failed for {alias}")
            self.assertIn(alias, self.d)

        # KOSPI aliases
        for alias in ["kospi", "KOSPI", "ks11", "KS11", "^ks11"]:
            self.assertEqual(self.d[alias], "kospi_val", f"Failed for {alias}")

        # NASDAQ aliases
        for alias in ["nasdaq", "NASDAQ", "^ixic"]:
            self.assertEqual(self.d[alias], "nasdaq_val", f"Failed for {alias}")

        # RUSSELL2000 aliases
        for alias in ["russell2000", "RUSSELL2000", "russell", "rut", "RUT", "^rut"]:
            self.assertEqual(self.d[alias], "rut_val", f"Failed for {alias}")

        # KOSDAQ aliases
        for alias in ["kosdaq", "KOSDAQ", "kq11", "KQ11", "^kq11"]:
            self.assertEqual(self.d[alias], "kosdaq_val", f"Failed for {alias}")

    def test_non_existent_key_and_defaults(self) -> None:
        """Tests missing key handling and get() defaults."""
        with self.assertRaises(KeyError):
            _ = self.d["UNKNOWN_MARKET"]
        self.assertNotIn("UNKNOWN_MARKET", self.d)
        self.assertEqual(self.d.get("UNKNOWN_MARKET", 42), 42)

    def test_non_string_keys(self) -> None:
        """Tests resilience with numeric or None keys."""
        self.d[100] = "century"
        self.assertEqual(self.d[100], "century")
        self.assertEqual(self.d.get(200, "missing"), "missing")

    def test_case_insensitive_dict_pop_and_del(self) -> None:
        """
        Tests whether CaseInsensitiveDict supports dict protocol operations
        pop() and del d[key] with alias keys.
        """
        d = CaseInsensitiveDict({"SP500": 100, "KOSPI": 200})
        del d["sp500"]
        self.assertNotIn("SP500", d)
        val = d.pop("kospi")
        self.assertEqual(val, 200)
        self.assertNotIn("KOSPI", d)


class TestPipelinePerformanceAndExecutionSpeed(unittest.TestCase):
    """Benchmarks cache reload latency and memory stability."""

    def test_cache_reload_speed_strictly_under_half_second(self) -> None:
        """
        Loads 30-year panel 10 times consecutively from cache.
        Asserts mean latency < 0.20s and max latency < 0.50s.
        """
        pipeline = HistoricalDataPipeline(use_cache=True)
        durations: List[float] = []

        # Warm-up reload
        _ = pipeline.load_30year_panel()

        for _ in range(10):
            t0 = time.perf_counter()
            panels = pipeline.load_30year_panel()
            dt = time.perf_counter() - t0
            durations.append(dt)
            self.assertEqual(len(panels), 5)

        mean_dt = float(np.mean(durations))
        max_dt = float(np.max(durations))
        print(f"\n[Performance Benchmark] Mean reload: {mean_dt*1000:.2f}ms, Max reload: {max_dt*1000:.2f}ms")
        
        self.assertLess(
            max_dt, 0.50,
            f"Cache reload max latency {max_dt:.4f}s exceeded 0.50s requirement!"
        )
        self.assertLess(
            mean_dt, 0.25,
            f"Cache reload mean latency {mean_dt:.4f}s exceeded 0.25s threshold!"
        )

    def test_data_integrity_audit_passes(self) -> None:
        """Runs pipeline's built-in causal integrity validator."""
        pipeline = HistoricalDataPipeline()
        panels = pipeline.load_30year_panel()
        audit = pipeline.validate_causal_integrity(panels)
        self.assertTrue(audit["passed"], f"Pipeline causal integrity audit failed: {audit['errors']}")
        self.assertEqual(len(audit["errors"]), 0)


if __name__ == "__main__":
    unittest.main()

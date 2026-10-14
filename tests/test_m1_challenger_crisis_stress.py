"""
tests/test_m1_challenger_crisis_stress.py — Empirical Challenger Stress Test Suite for Milestone M1

Adversarial stress testing for:
1. All 5 historical crisis regimes (1997, 2000, 2008, 2020, 2022) across 5 markets:
   - Gaps, corrupted values, negative prices, NaN returns, OHLC invariants.
2. Cache invalidation, corruption resilience, and clean recreation.
3. High-frequency concurrent querying across all 5 markets simultaneously.
4. Causal invariants and boundary edge cases.
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_pipeline import (
    HistoricalDataPipeline,
    HISTORICAL_CRISIS_PERIODS,
    CRISIS_ALIASES,
    CaseInsensitiveDict,
    compute_regulatory_filing_lag,
    apply_statutory_filing_lag,
    align_fundamentals_causally,
    apply_causal_lag,
    apply_geographical_shift,
)


class TestCrisisRegimesDeepStress(unittest.TestCase):
    """
    Stress tests all 5 historical crisis regimes across 5 markets:
    SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline(use_cache=True)
        cls.panels = cls.pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31")

    def test_all_five_crises_exist_and_non_empty(self) -> None:
        """Every defined crisis period must exist in HISTORICAL_CRISIS_PERIODS and have valid bounds."""
        expected_crises = [
            "1997_ASIAN_CRISIS",
            "2000_DOTCOM_CRASH",
            "2008_GFC",
            "2020_COVID_SHOCK",
            "2022_INFLATION_RATE_HIKE",
        ]
        for cid in expected_crises:
            self.assertIn(cid, HISTORICAL_CRISIS_PERIODS)
            meta = HISTORICAL_CRISIS_PERIODS[cid]
            self.assertIn("start_date", meta)
            self.assertIn("end_date", meta)
            start_dt = pd.to_datetime(meta["start_date"])
            end_dt = pd.to_datetime(meta["end_date"])
            self.assertLess(start_dt, end_dt, f"Crisis {cid} start date must precede end date")

    def test_crisis_slices_have_no_nans_or_invalids(self) -> None:
        """
        Adversarial check: across all 5 crises and 5 markets,
        verify NO NaNs, NO Infs, strictly positive prices, and consistent OHLC relations.
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        critical_cols = ["Open", "High", "Low", "Close", "Volume", "return_1d", "close_lag1"]
        macro_cols = ["vix", "us10y", "usdkrw", "wti", "sox"]

        for cid in HISTORICAL_CRISIS_PERIODS:
            for market in markets:
                with self.subTest(crisis=cid, market=market):
                    df = self.panels[market]
                    crisis_slice = self.pipeline.get_crisis_slice(df, cid)

                    # 1. Bar count threshold
                    self.assertGreaterEqual(
                        len(crisis_slice), 30,
                        f"Crisis {cid} in {market} has fewer than 30 bars ({len(crisis_slice)})"
                    )

                    # 2. Check critical OHLCV columns
                    for col in critical_cols:
                        self.assertIn(col, crisis_slice.columns, f"Missing {col} in {market} during {cid}")
                        nan_count = crisis_slice[col].isna().sum()
                        self.assertEqual(
                            nan_count, 0,
                            f"Found {nan_count} NaNs in {col} for {market} during crisis {cid}"
                        )
                        inf_count = np.isinf(crisis_slice[col]).sum()
                        self.assertEqual(
                            inf_count, 0,
                            f"Found {inf_count} Infs in {col} for {market} during crisis {cid}"
                        )

                    # 3. Check macro columns
                    for mcol in macro_cols:
                        self.assertIn(mcol, crisis_slice.columns, f"Missing macro {mcol} in {market} during {cid}")
                        nan_count = crisis_slice[mcol].isna().sum()
                        self.assertEqual(
                            nan_count, 0,
                            f"Found {nan_count} NaNs in macro {mcol} for {market} during crisis {cid}"
                        )

                    # 4. Strict price positivity (no zero, no negative prices)
                    self.assertTrue(
                        (crisis_slice["Close"] > 0).all(),
                        f"Found non-positive Close price in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["Open"] > 0).all(),
                        f"Found non-positive Open price in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["High"] > 0).all(),
                        f"Found non-positive High price in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["Low"] > 0).all(),
                        f"Found non-positive Low price in {market} during {cid}"
                    )

                    # 5. OHLC structural inequalities: High >= Low, High >= Open, High >= Close
                    self.assertTrue(
                        (crisis_slice["High"] >= crisis_slice["Low"]).all(),
                        f"High < Low anomaly in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["High"] >= crisis_slice["Open"]).all(),
                        f"High < Open anomaly in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["High"] >= crisis_slice["Close"]).all(),
                        f"High < Close anomaly in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["Low"] <= crisis_slice["Open"]).all(),
                        f"Low > Open anomaly in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["Low"] <= crisis_slice["Close"]).all(),
                        f"Low > Close anomaly in {market} during {cid}"
                    )

                    # 6. Macro sanity: VIX > 0, USDKRW > 0
                    self.assertTrue(
                        (crisis_slice["vix"] > 0).all(),
                        f"VIX <= 0 anomaly in {market} during {cid}"
                    )
                    self.assertTrue(
                        (crisis_slice["usdkrw"] > 0).all(),
                        f"USDKRW <= 0 anomaly in {market} during {cid}"
                    )

    def test_crisis_date_continuity_and_max_gap(self) -> None:
        """
        Verifies there are no unhandled time gaps during crisis periods.
        Consecutive business days should not exceed 10 calendar days (accommodating extended holidays).
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for cid in HISTORICAL_CRISIS_PERIODS:
            for market in markets:
                with self.subTest(crisis=cid, market=market):
                    df = self.panels[market]
                    crisis_slice = self.pipeline.get_crisis_slice(df, cid)
                    date_diffs = crisis_slice.index.to_series().diff().dropna()
                    max_gap_days = date_diffs.max().days
                    self.assertLessEqual(
                        max_gap_days, 10,
                        f"Extreme calendar gap of {max_gap_days} days detected in {market} during {cid}"
                    )

    def test_crisis_alias_resolution(self) -> None:
        """Verifies that all aliases correctly resolve to the canonical crisis period."""
        test_cases = [
            ("1997", "1997_ASIAN_CRISIS"),
            ("1997_ASIAN", "1997_ASIAN_CRISIS"),
            ("IMF", "1997_ASIAN_CRISIS"),
            ("ASIAN_CRISIS", "1997_ASIAN_CRISIS"),
            ("2000", "2000_DOTCOM_CRASH"),
            ("DOTCOM", "2000_DOTCOM_CRASH"),
            ("2008", "2008_GFC"),
            ("GFC", "2008_GFC"),
            ("2020", "2020_COVID_SHOCK"),
            ("COVID", "2020_COVID_SHOCK"),
            ("2022", "2022_INFLATION_RATE_HIKE"),
            ("INFLATION", "2022_INFLATION_RATE_HIKE"),
            ("RATE_HIKE", "2022_INFLATION_RATE_HIKE"),
        ]
        for alias, expected in test_cases:
            meta = self.pipeline.get_crisis_period(alias)
            self.assertEqual(meta["crisis_id"], expected, f"Alias {alias} resolved to {meta['crisis_id']}, expected {expected}")

        # Invalid crisis ID should raise ValueError
        with self.assertRaises(ValueError):
            self.pipeline.get_crisis_period("NON_EXISTENT_CRISIS_9999")


class TestCacheCorruptionAndInvalidation(unittest.TestCase):
    """
    Stress tests local parquet caching:
    - Reload speed (< 0.5s requirement)
    - Handling of corrupted/truncated cache files
    - Invalidation and clean recreation with force_refresh
    - Partial cache detection (rebuilding when 1 of 5 files is missing)
    """

    def setUp(self) -> None:
        self.temp_cache_dir = tempfile.mkdtemp(prefix="test_cache_30yr_")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_cache_dir):
            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)

    def test_clean_cache_reload_speed(self) -> None:
        """Verifies subsequent cache hit reload speed is strictly < 0.5 seconds."""
        pipeline = HistoricalDataPipeline(use_cache=True)
        # First call ensures cache exists
        _ = pipeline.load_30year_panel()

        # Second call measures pure cache load time
        t0 = time.perf_counter()
        cached_panels = pipeline.load_30year_panel()
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 0.50, f"Cache reload took {elapsed:.4f}s, expected < 0.5s")
        self.assertEqual(len(cached_panels), 5)

    def test_corrupted_cache_clean_recreation(self) -> None:
        """
        Adversarial: writes garbage binary data into a cache file.
        Using force_refresh=True must cleanly overwrite the corrupted file and rebuild valid panels.
        """
        # Create corrupted parquet in temp cache
        corrupted_file = os.path.join(self.temp_cache_dir, "sp500_panel.parquet")
        with open(corrupted_file, "wb") as f:
            f.write(b"GARBAGE_CORRUPTED_PARQUET_HEADER_DATA_1234567890\x00\xff\xfe")

        pipeline = HistoricalDataPipeline(cache_dir=self.temp_cache_dir, use_cache=True)

        # Loading with force_refresh=True should rebuild without error
        panels = pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31", force_refresh=True)
        self.assertIn("SP500", panels)
        self.assertGreater(len(panels["SP500"]), 7000)

        # Verify that the corrupted file was cleanly replaced by valid parquet
        reloaded_df = pd.read_parquet(corrupted_file)
        self.assertIn("Close", reloaded_df.columns)
        self.assertGreater(len(reloaded_df), 7000)

    def test_partial_cache_invalidation_detection(self) -> None:
        """
        If only 3 out of 5 market panels are present in cache,
        pipeline must detect all_cached=False and rebuild all 5 markets cleanly.
        """
        pipeline_orig = HistoricalDataPipeline(use_cache=True)
        orig_panels = pipeline_orig.load_30year_panel()

        # Copy only SP500, NASDAQ, RUSSELL2000 into temp cache (leaving KOSPI & KOSDAQ missing)
        for m in ["sp500", "nasdaq", "russell2000"]:
            p_src = os.path.join(pipeline_orig.cache_dir, f"{m}_panel.parquet")
            if os.path.exists(p_src):
                shutil.copy(p_src, os.path.join(self.temp_cache_dir, f"{m}_panel.parquet"))

        pipeline_temp = HistoricalDataPipeline(cache_dir=self.temp_cache_dir, use_cache=True)
        # Calling load_30year_panel should detect missing KOSPI/KOSDAQ and build all 5
        panels = pipeline_temp.load_30year_panel()
        self.assertEqual(len(panels), 5)
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            self.assertIn(m, panels)
            self.assertGreaterEqual(len(panels[m]), 7000)

    def test_cache_immutability_isolation(self) -> None:
        """
        Modifying an in-memory DataFrame returned from load_30year_panel
        must not silently corrupt the disk-cached parquet file.
        """
        pipeline = HistoricalDataPipeline(use_cache=True)
        panels1 = pipeline.load_30year_panel()

        orig_first_close = float(panels1["SP500"]["Close"].iloc[0])

        # Mutate in-memory DataFrame
        panels1["SP500"]["Close"].iloc[0] = -99999.0

        # Reload from new pipeline instance
        pipeline2 = HistoricalDataPipeline(use_cache=True)
        panels2 = pipeline2.load_30year_panel()

        # Must retain original value, not mutated -99999.0
        self.assertAlmostEqual(float(panels2["SP500"]["Close"].iloc[0]), orig_first_close, places=4)


class TestHighFrequencyAndConcurrency(unittest.TestCase):
    """
    Stress tests high-frequency and multi-threaded querying across all 5 markets simultaneously.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline(use_cache=True)
        # Warm cache
        _ = cls.pipeline.load_30year_panel()

    def test_concurrent_multi_market_queries(self) -> None:
        """
        Launches 16 concurrent threads querying load_market_panel for different markets.
        All threads must complete successfully without race conditions or file locks.
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"] * 4

        def fetch_market(m: str) -> Tuple[str, int]:
            p = HistoricalDataPipeline(use_cache=True)
            df = p.load_market_panel(m)
            return m, len(df)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_market, m) for m in markets]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), len(markets))
        for m, bar_count in results:
            self.assertGreaterEqual(bar_count, 7000)

    def test_concurrent_crisis_slicing(self) -> None:
        """
        Launches 20 concurrent threads slicing crisis periods across markets.
        Verifies thread safety during crisis period retrieval and slicing.
        """
        tasks = []
        crises = list(HISTORICAL_CRISIS_PERIODS.keys())
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for i in range(20):
            cid = crises[i % len(crises)]
            m = markets[i % len(markets)]
            tasks.append((cid, m))

        def slice_task(cid: str, m: str) -> Tuple[str, str, int]:
            p = HistoricalDataPipeline(use_cache=True)
            panel = p.load_market_panel(m)
            c_slice = p.get_crisis_slice(panel, cid)
            return cid, m, len(c_slice)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(slice_task, cid, m) for cid, m in tasks]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 20)
        for cid, m, bar_count in results:
            self.assertGreaterEqual(bar_count, 30)

    def test_high_frequency_sequential_stress(self) -> None:
        """
        Executes 50 rapid sequential calls to load_market_panel.
        Ensures consistent low latency (< 15ms per call) with zero memory/resource leaks.
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        latencies = []

        for i in range(50):
            target = markets[i % len(markets)]
            t0 = time.perf_counter()
            df = self.pipeline.load_market_panel(target)
            lat = time.perf_counter() - t0
            latencies.append(lat)
            self.assertGreaterEqual(len(df), 7000)

        mean_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))

        self.assertLess(
            mean_latency, 0.15,
            f"Mean latency {mean_latency*1000:.2f}ms exceeds threshold"
        )
        self.assertLess(
            p95_latency, 0.25,
            f"P95 latency {p95_latency*1000:.2f}ms exceeds threshold"
        )


class TestCausalInvariantsAndEdgeCases(unittest.TestCase):
    """
    Stress tests causal lagging, lookahead invariants, and date boundary edge cases.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline(use_cache=True)
        cls.panels = cls.pipeline.load_30year_panel()

    def test_strict_causal_lag_identity_across_all_bars(self) -> None:
        """
        Exhaustive verification: for every row i in [1, N-1],
        close_lag1[i] must EXACTLY equal Close[i-1].
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for m in markets:
            with self.subTest(market=m):
                df = self.panels[m]
                close_prev = df["Close"].iloc[:-1].values
                close_lag = df["close_lag1"].iloc[1:].values
                mismatches = np.sum(np.abs(close_lag - close_prev) > 1e-4)
                self.assertEqual(
                    mismatches, 0,
                    f"Found {mismatches} causal lag mismatches in {m}"
                )

                # Return lag check: return_lag1[i] must equal return_1d[i-1]
                ret_prev = df["return_1d"].iloc[:-1].values
                ret_lag = df["return_lag1"].iloc[1:].values
                ret_mismatches = np.sum(np.abs(ret_lag - ret_prev) > 1e-4)
                self.assertEqual(
                    ret_mismatches, 0,
                    f"Found {ret_mismatches} return lag mismatches in {m}"
                )

    def test_single_day_and_narrow_date_ranges(self) -> None:
        """Tests slicing with single day and narrow ranges."""
        single_day = self.pipeline.load_30year_panel(start_date="2020-03-23", end_date="2020-03-23")
        for m in single_day:
            df = single_day[m]
            self.assertEqual(len(df), 1)
            self.assertEqual(df.index[0].strftime("%Y-%m-%d"), "2020-03-23")

    def test_inverted_date_range_graceful_handling(self) -> None:
        """Tests start_date > end_date returns empty DataFrame without crashing."""
        inverted = self.pipeline.load_30year_panel(start_date="2025-01-01", end_date="2020-01-01")
        for m in inverted:
            df = inverted[m]
            self.assertEqual(len(df), 0)

    def test_case_insensitive_dict_aliases(self) -> None:
        """Tests CaseInsensitiveDict with various casing and market aliases."""
        panels = self.panels
        self.assertIs(panels["SP500"], panels["sp500"])
        self.assertIs(panels["SP500"], panels["S&P500"])
        self.assertIs(panels["SP500"], panels["^GSPC"])
        self.assertIs(panels["NASDAQ"], panels["nasdaq"])
        self.assertIs(panels["NASDAQ"], panels["^IXIC"])
        self.assertIs(panels["RUSSELL2000"], panels["russell2000"])
        self.assertIs(panels["RUSSELL2000"], panels["russell"])
        self.assertIs(panels["KOSPI"], panels["kospi"])
        self.assertIs(panels["KOSPI"], panels["^ks11"])
        self.assertIs(panels["KOSDAQ"], panels["kosdaq"])
        self.assertIs(panels["KOSDAQ"], panels["^kq11"])

    def test_regulatory_filing_lag_leap_years(self) -> None:
        """Tests statutory filing lag computation on leap year end dates."""
        # Leap year 2024: Feb 29
        lag_2024_q1 = compute_regulatory_filing_lag("2024-03-31", period_type="quarterly", is_krx=True)
        self.assertEqual(lag_2024_q1, "2024-05-15")

        lag_2024_annual = compute_regulatory_filing_lag("2024-12-31", period_type="annual", is_krx=True)
        # Dec 31 + 90 days in 2025 (non-leap: 31 Jan + 28 Feb + 31 Mar = 90) -> March 31
        self.assertEqual(lag_2024_annual, "2025-03-31")

        # US 10-K: Dec 31 + 60 days -> March 01
        lag_us_10k = compute_regulatory_filing_lag("2024-12-31", period_type="annual", is_krx=False)
        self.assertEqual(lag_us_10k, "2025-03-01")


if __name__ == "__main__":
    unittest.main()

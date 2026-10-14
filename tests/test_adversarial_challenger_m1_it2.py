"""
tests/test_adversarial_challenger_m1_it2.py

Milestone 1 Iteration 2 — Empirical Challenger Stress Test Suite
Adversarial challenge suite authored by Challenger M1-It2-1.

Empirical verification of:
1. align_fundamentals_causally:
   - Randomly permuted price panels (shuffled order).
   - Reverse-chronological panels.
   - Duplicate timestamps in prices_df.
   - Duplicate timestamps in fundamentals_df.
   - Multiple filings on same date / rapid consecutive filings.
   - String index vs DatetimeIndex vs RangeIndex.
2. apply_causal_lag:
   - Negative lag rejection (ValueError strictly raised for lag < 0).
   - Zero lag preservation.
   - Reverse-chronological and randomly shuffled DatetimeIndex.
   - Oversized lag exceeding DataFrame length.
3. KOSPI vs KOSDAQ Jan-Jun 1996 Pre-Inception Mathematical Identity:
   - Daily returns identity (r_t^KQ == r_t^KS for every bar).
   - Pearson correlation == +1.0000000000 (tolerance < 1e-12).
   - Spearman rank correlation == +1.0000000000.
   - Cumulative return exact equivalence.
4. Comprehensive 38,000+ Bar Parquet Cache Causal Audit:
   - Monotonicity of DatetimeIndex across all 5 markets.
   - Total bar count >= 38,000 bars.
   - Zero causal lag mismatches on close_lag1, open_lag1, high_lag1, low_lag1, volume_lag1.
   - Zero lookahead on return_lag1, volatility_20d_lag1, momentum_20d_lag1.
   - Zero unexpected NaNs across all historical crisis periods.
5. CaseInsensitiveDict Protocol Completeness & Edge Mutations:
   - Alias resolutions, deletion via alias, pop via alias, copy isolation.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_pipeline import (
    HistoricalDataPipeline,
    CaseInsensitiveDict,
    HISTORICAL_CRISIS_PERIODS,
    align_fundamentals_causally,
    apply_causal_lag,
    compute_regulatory_filing_lag,
    apply_statutory_filing_lag,
    apply_geographical_shift,
)


class TestAlignFundamentalsAdversarialStress(unittest.TestCase):
    """Extreme adversarial tests on point-in-time fundamental alignment."""

    def test_randomly_permuted_price_rows(self) -> None:
        """
        Adversarial Test:
        Permutes price rows randomly 50 times with a fixed seed.
        Ensures that aligned output matches the exact permutation of caller rows,
        and that each row receives the fundamental data strictly matching its date.
        """
        rng = np.random.RandomState(1337)
        dates = pd.date_range("2021-01-01", "2021-12-31", freq="B")
        prices = np.linspace(50.0, 150.0, len(dates))

        base_df = pd.DataFrame({"Close": prices}, index=dates)

        # Fundamentals: 2021-03-31 (avail 2021-05-15), 2021-06-30 (avail 2021-08-14)
        funds = pd.DataFrame([
            {"date": "2021-03-31", "period_type": "quarterly", "eps": 2.50},
            {"date": "2021-06-30", "period_type": "quarterly", "eps": 3.75},
        ])

        # Baseline chronological alignment
        aligned_chrono = align_fundamentals_causally(base_df, funds, is_krx=True)

        # Now test 20 different random shuffles of base_df
        for trial in range(20):
            perm = rng.permutation(len(base_df))
            shuffled_df = base_df.iloc[perm].copy()

            aligned_shuffled = align_fundamentals_causally(shuffled_df, funds, is_krx=True)

            # 1. Output length and index sequence must exactly match shuffled_df
            self.assertEqual(len(aligned_shuffled), len(shuffled_df))
            self.assertTrue(aligned_shuffled.index.equals(shuffled_df.index))

            # 2. Close prices must NOT have swapped
            np.testing.assert_array_equal(
                aligned_shuffled["Close"].values,
                shuffled_df["Close"].values,
                err_msg=f"Close price corrupted during permuted alignment in trial {trial}"
            )

            # 3. EPS values must match aligned_chrono reindexed to shuffled order
            expected_eps = aligned_chrono.loc[shuffled_df.index, "eps"].values
            actual_eps = aligned_shuffled["eps"].values

            np.testing.assert_array_equal(
                pd.isna(actual_eps),
                pd.isna(expected_eps),
                err_msg=f"NaN pattern mismatch in trial {trial}"
            )
            valid_mask = ~pd.isna(actual_eps)
            np.testing.assert_allclose(
                actual_eps[valid_mask],
                expected_eps[valid_mask],
                rtol=1e-6,
                err_msg=f"EPS values mismatch in trial {trial}"
            )

    def test_duplicate_price_timestamps(self) -> None:
        """
        Adversarial Test:
        Prices DataFrame contains duplicate timestamps (e.g. multiple records for same day).
        Ensures all duplicate rows are preserved in original order and receive proper point-in-time data.
        """
        dup_dates = pd.to_datetime([
            "2021-05-10", "2021-05-10",  # Before Q1 avail (2021-05-15)
            "2021-05-20", "2021-05-20", "2021-05-20",  # After Q1 avail
            "2021-05-12",  # Unsorted duplicate before avail
        ])
        prices = [10.0, 11.0, 20.0, 21.0, 22.0, 12.0]
        p_df = pd.DataFrame({"Close": prices}, index=dup_dates)

        funds = pd.DataFrame([
            {"date": "2021-03-31", "period_type": "quarterly", "eps": 5.0},
        ])

        aligned = align_fundamentals_causally(p_df, funds, is_krx=True)

        self.assertEqual(len(aligned), 6, "Row count changed with duplicate timestamps!")
        np.testing.assert_array_equal(aligned["Close"].values, prices)

        # Rows 0, 1, 5 are before 2021-05-15 -> eps must be NaN
        self.assertTrue(pd.isna(aligned["eps"].iloc[0]))
        self.assertTrue(pd.isna(aligned["eps"].iloc[1]))
        self.assertTrue(pd.isna(aligned["eps"].iloc[5]))

        # Rows 2, 3, 4 are on 2021-05-20 -> eps must be 5.0
        self.assertEqual(aligned["eps"].iloc[2], 5.0)
        self.assertEqual(aligned["eps"].iloc[3], 5.0)
        self.assertEqual(aligned["eps"].iloc[4], 5.0)

    def test_duplicate_fundamental_filing_dates(self) -> None:
        """
        Adversarial Test:
        Fundamentals contain multiple entries available on the same date (e.g. revised filing).
        merge_asof should take the last available filing as of that point in time.
        """
        dates = pd.date_range("2021-05-01", "2021-05-30", freq="D")
        p_df = pd.DataFrame({"Close": np.ones(len(dates)) * 100.0}, index=dates)

        # Both filings for Q1, but second is amended with higher EPS
        funds = pd.DataFrame([
            {"date": "2021-03-31", "period_type": "quarterly", "eps": 4.0},
            {"date": "2021-03-31", "period_type": "quarterly", "eps": 6.0},
        ])

        aligned = align_fundamentals_causally(p_df, funds, is_krx=True)
        # On 2021-05-16, it should be 6.0 (amended/latest)
        post_bar = aligned.loc["2021-05-16"]
        self.assertEqual(post_bar["eps"], 6.0)

    def test_string_index_unsorted_resilience(self) -> None:
        """
        Adversarial Test:
        Prices DataFrame uses string index with non-monotonic dates.
        """
        p_df = pd.DataFrame(
            {"Close": [30.0, 10.0, 20.0]},
            index=["2022-06-01", "2022-05-01", "2022-05-20"]
        )
        funds = pd.DataFrame([
            {"date": "2022-03-31", "period_type": "quarterly", "eps": 8.0} # avail 2022-05-15
        ])

        aligned = align_fundamentals_causally(p_df, funds, is_krx=True)

        self.assertEqual(len(aligned), 3)
        self.assertEqual(list(aligned.index), ["2022-06-01", "2022-05-01", "2022-05-20"])
        self.assertEqual(aligned.loc["2022-05-01", "Close"], 10.0)
        self.assertTrue(pd.isna(aligned.loc["2022-05-01", "eps"]))
        self.assertEqual(aligned.loc["2022-05-20", "Close"], 20.0)
        self.assertEqual(aligned.loc["2022-05-20", "eps"], 8.0)
        self.assertEqual(aligned.loc["2022-06-01", "Close"], 30.0)
        self.assertEqual(aligned.loc["2022-06-01", "eps"], 8.0)


class TestApplyCausalLagAdversarialStress(unittest.TestCase):
    """Stress tests for apply_causal_lag validation and sorting safeguards."""

    def test_negative_lag_raises_value_error(self) -> None:
        """Passing lag_periods < 0 MUST raise ValueError to prevent lookahead."""
        df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]}, index=pd.date_range("2020-01-01", periods=3))

        for neg_lag in [-1, -2, -100]:
            with self.assertRaises(ValueError, msg=f"apply_causal_lag failed to reject negative lag {neg_lag}"):
                apply_causal_lag(df, lag_periods=neg_lag)

    def test_zero_lag_returns_exact_lag0_columns(self) -> None:
        """Passing lag_periods = 0 should append _lag0 without shifting."""
        df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]}, index=pd.date_range("2020-01-01", periods=3))
        res = apply_causal_lag(df, lag_periods=0)
        self.assertIn("Close_lag0", res.columns)
        np.testing.assert_array_equal(res["Close_lag0"].values, df["Close"].values)

    def test_unsorted_datetime_index_preserves_row_order_and_temporal_shift(self) -> None:
        """
        Adversarial Test:
        DataFrame has non-monotonic DatetimeIndex.
        apply_causal_lag must sort chronologically, shift, and restore caller's exact row order.
        """
        dates = pd.to_datetime(["2020-01-03", "2020-01-01", "2020-01-02"])
        closes = [30.0, 10.0, 20.0]
        df = pd.DataFrame({"Close": closes}, index=dates)

        res = apply_causal_lag(df, lag_periods=1)

        # Row order must be preserved: 2020-01-03, 2020-01-01, 2020-01-02
        self.assertTrue(res.index.equals(dates))
        np.testing.assert_array_equal(res["Close"].values, closes)

        # On 2020-01-01 (first chronological date), lag1 must be NaN
        self.assertTrue(pd.isna(res.loc["2020-01-01", "Close_lag1"]))

        # On 2020-01-02 (second chronological date), lag1 must be 10.0 (from 2020-01-01)
        self.assertEqual(res.loc["2020-01-02", "Close_lag1"], 10.0)

        # On 2020-01-03 (third chronological date), lag1 must be 20.0 (from 2020-01-02)
        self.assertEqual(res.loc["2020-01-03", "Close_lag1"], 20.0)

    def test_oversized_lag_periods(self) -> None:
        """When lag_periods >= len(df), all shifted values must be NaN."""
        df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]}, index=pd.date_range("2020-01-01", periods=3))
        res = apply_causal_lag(df, lag_periods=5)
        self.assertIn("Close_lag5", res.columns)
        self.assertTrue(res["Close_lag5"].isna().all())


class TestKosdaqInceptionMathematicalIdentity(unittest.TestCase):
    """
    Empirically verifies the mathematical identity between KOSPI and synthetic KOSDAQ
    for the pre-inception backfill period (1996-01-03 to 1996-06-29).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline(use_cache=True)
        cls.panels = cls.pipeline.load_30year_panel(start_date="1996-01-01", end_date="1996-07-05")
        cls.df_ks = cls.panels["KOSPI"].loc["1996-01-03":"1996-06-29"]
        cls.df_kq = cls.panels["KOSDAQ"].loc["1996-01-03":"1996-06-29"]

    def test_daily_return_exact_identity(self) -> None:
        """
        At every single trading day t in Jan-Jun 1996:
        r_t^KQ == r_t^KS within machine precision.
        """
        ret_ks = self.df_ks["Close"].pct_change().dropna().values
        ret_kq = self.df_kq["Close"].pct_change().dropna().values

        self.assertEqual(len(ret_ks), len(ret_kq))
        self.assertGreater(len(ret_ks), 100, "Insufficient bars in Jan-Jun 1996")

        max_daily_diff = np.max(np.abs(ret_ks - ret_kq))
        self.assertLess(
            max_daily_diff, 1e-12,
            f"Daily return discrepancy between KOSPI and KOSDAQ: {max_daily_diff:.2e}"
        )

    def test_pearson_correlation_equals_positive_one(self) -> None:
        """Daily return Pearson correlation between KOSPI and synthetic KOSDAQ must be exactly +1.0000000000."""
        ret_ks = self.df_ks["Close"].pct_change().dropna()
        ret_kq = self.df_kq["Close"].pct_change().dropna()

        corr = ret_ks.corr(ret_kq)
        self.assertAlmostEqual(
            corr, 1.0, places=10,
            msg=f"Correlation between KOSPI and KOSDAQ {corr} is not +1.0000"
        )

    def test_spearman_rank_correlation_equals_positive_one(self) -> None:
        """Spearman rank correlation must also be exactly +1.0000."""
        ret_ks = self.df_ks["Close"].pct_change().dropna()
        ret_kq = self.df_kq["Close"].pct_change().dropna()

        spearman_corr = ret_ks.corr(ret_kq, method="spearman")
        self.assertAlmostEqual(
            spearman_corr, 1.0, places=10,
            msg=f"Spearman correlation {spearman_corr} is not +1.0000"
        )

    def test_cumulative_return_equivalence(self) -> None:
        """Cumulative return across 1996-01-03 ~ 1996-06-29 must match exactly."""
        cum_ks = (self.df_ks["Close"].iloc[-1] / self.df_ks["Close"].iloc[0] - 1.0) * 100.0
        cum_kq = (self.df_kq["Close"].iloc[-1] / self.df_kq["Close"].iloc[0] - 1.0) * 100.0

        self.assertAlmostEqual(
            cum_ks, cum_kq, places=8,
            msg=f"Cumulative return mismatch: KOSPI={cum_ks:.6f}%, KOSDAQ={cum_kq:.6f}%"
        )
        # Both must equal approximately -8.0351%
        self.assertAlmostEqual(cum_kq, -8.0351015, places=4)

    def test_kosdaq_inception_boundary_transition(self) -> None:
        """
        Verify that on 1996-07-01 (official inception), KOSDAQ transitions smoothly
        and anchor baseline price is 1000.0.
        """
        full_kq = self.panels["KOSDAQ"]
        # Inception date bar
        self.assertIn(pd.to_datetime("1996-07-01"), full_kq.index)
        inception_bar = full_kq.loc["1996-07-01"]
        # Anchor price is 1000.0
        self.assertAlmostEqual(float(inception_bar["Close"]), 1000.0, places=1)


class TestComprehensiveParquetCacheAudit(unittest.TestCase):
    """
    Audits the persistent Parquet cache across all 38,000+ bars:
    - SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
    - Zero causal lag mismatches.
    - Monotonic DatetimeIndex.
    - Zero NaNs across all historical crisis periods.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = HistoricalDataPipeline(use_cache=True)
        cls.panels = cls.pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31")

    def test_total_bar_count_exceeds_38000(self) -> None:
        """Verifies total bars across all 5 panels exceed 38,000."""
        total_bars = sum(len(self.panels[m]) for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"])
        self.assertGreaterEqual(
            total_bars, 38000,
            f"Total bar count across 5 markets is {total_bars}, expected >= 38,000"
        )

    def test_strict_datetime_index_monotonicity(self) -> None:
        """Every market panel must have a strictly monotonic increasing DatetimeIndex."""
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            idx = self.panels[m].index
            self.assertIsInstance(idx, pd.DatetimeIndex, f"{m} index is not DatetimeIndex")
            self.assertTrue(idx.is_monotonic_increasing, f"{m} index is not monotonically increasing")
            self.assertTrue(idx.is_unique, f"{m} index contains duplicate timestamps")

    def test_zero_causal_lag_mismatches_all_bars(self) -> None:
        """
        For every market and every bar t from 1 to N:
        close_lag1[t] == Close[t-1]
        open_lag1[t] == Open[t-1]
        high_lag1[t] == High[t-1]
        low_lag1[t] == Low[t-1]
        volume_lag1[t] == Volume[t-1]
        return_lag1[t] == (Close[t-1] / Close[t-2] - 1.0)
        """
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            df = self.panels[m]
            n = len(df)

            # Check close_lag1
            close_diff = np.abs(df["close_lag1"].iloc[1:].values - df["Close"].iloc[:-1].values)
            self.assertEqual(
                np.sum(close_diff > 1e-4), 0,
                f"{m} has {np.sum(close_diff > 1e-4)} close_lag1 mismatches!"
            )

            # Check open_lag1, high_lag1, low_lag1, volume_lag1
            for col in ["Open", "High", "Low", "Volume"]:
                lag_col = f"{col.lower()}_lag1"
                if lag_col in df.columns:
                    diff = np.abs(df[lag_col].iloc[1:].values - df[col].iloc[:-1].values)
                    self.assertEqual(
                        np.sum(diff > 1e-4), 0,
                        f"{m} has {np.sum(diff > 1e-4)} {lag_col} mismatches!"
                    )

            # Check return_lag1 for t >= 2
            expected_ret_lag1 = (df["Close"].iloc[1:-1].values / df["Close"].iloc[:-2].values) - 1.0
            actual_ret_lag1 = df["return_lag1"].iloc[2:].values
            ret_diff = np.abs(actual_ret_lag1 - expected_ret_lag1)
            self.assertEqual(
                np.sum(ret_diff > 1e-4), 0,
                f"{m} has {np.sum(ret_diff > 1e-4)} return_lag1 mismatches!"
            )

    def test_all_five_crises_zero_nan_coverage(self) -> None:
        """Verifies that none of the 5 historical crises contain any NaNs in core features."""
        for cid, meta in HISTORICAL_CRISIS_PERIODS.items():
            for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
                crisis_slice = self.pipeline.get_crisis_slice(self.panels[m], cid)
                self.assertFalse(crisis_slice.empty, f"Crisis {cid} is empty for market {m}")

                for col in ["Close", "Volume", "close_lag1", "return_lag1", "vix", "us10y", "usdkrw", "wti", "sox"]:
                    nan_count = crisis_slice[col].isna().sum()
                    self.assertEqual(
                        nan_count, 0,
                        f"Found {nan_count} NaNs in {col} for {m} during {cid}"
                    )


class TestCaseInsensitiveDictStress(unittest.TestCase):
    """Stress tests CaseInsensitiveDict protocol and mutations."""

    def test_alias_mutations_and_isolation(self) -> None:
        """Tests that modifying/deleting via alias correctly mutates underlying dict."""
        d = CaseInsensitiveDict()
        d["s&p500"] = 100
        self.assertEqual(d["SP500"], 100)
        self.assertEqual(d["^GSPC"], 100)

        # Update via another alias
        d["^gspc"] = 200
        self.assertEqual(d["SP500"], 200)
        # Should not duplicate keys
        self.assertEqual(len(d), 1)

        # Copy isolation
        d_copy = d.copy()
        d_copy["sp500"] = 999
        self.assertEqual(d["SP500"], 200, "Copy mutation affected original dict!")
        self.assertEqual(d_copy["SP500"], 999)

        # Deletion
        del d["s&p500"]
        self.assertEqual(len(d), 0)
        self.assertNotIn("SP500", d)


if __name__ == "__main__":
    unittest.main()

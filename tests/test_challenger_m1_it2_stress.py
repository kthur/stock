"""
Empirical Challenger M1-It2-2 Stress Test Suite
Author: Challenger M1-It2-2
Focus:
  1. Deep historical crisis stress testing across all 5 crises (1997, 2000, 2008, 2020, 2022)
  2. Transition boundary continuity on KOSDAQ 1996-07-01 inception
  3. Caching latency, multi-iteration reload speed, and memory footprint
  4. Adversarial edge cases on CaseInsensitiveDict, causal lag, and fundamental alignment
  5. Negative/invalid input resilience and boundary conditions
"""

import os
import sys
import time
import math
import gc
import pytest
import numpy as np
import pandas as pd

from trading_system.src.backtest.historical_30yr_pipeline import (
    HistoricalDataPipeline,
    CaseInsensitiveDict,
    HISTORICAL_CRISIS_PERIODS,
    CRISIS_ALIASES,
    MARKET_TICKERS,
    MACRO_TICKERS,
    align_fundamentals_causally,
    apply_causal_lag,
    apply_statutory_filing_lag,
    compute_regulatory_filing_lag,
    apply_geographical_shift,
)


@pytest.fixture(scope="module")
def pipeline():
    return HistoricalDataPipeline(use_cache=True, auto_download=False)


@pytest.fixture(scope="module")
def panels(pipeline):
    return pipeline.load_30year_panel(start_date="1996-01-01", end_date="2026-08-31")


# ==============================================================================
# 1. Deep Historical Crisis Stress Testing
# ==============================================================================

class TestHistoricalCrisisDeepStress:
    """Rigorous empirical validation across all 5 historical crises."""

    MARKETS = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

    @pytest.mark.parametrize("crisis_id", list(HISTORICAL_CRISIS_PERIODS.keys()))
    def test_crisis_slice_continuity_and_zero_missing(self, panels, crisis_id):
        """Verify no NaNs, no infs, and sufficient trading bars in each crisis slice."""
        meta = HISTORICAL_CRISIS_PERIODS[crisis_id]
        s_date = meta["start_date"]
        e_date = meta["end_date"]

        for m in self.MARKETS:
            df = panels[m]
            slice_df = df.loc[s_date:e_date]

            assert len(slice_df) >= 30, (
                f"Market {m} during {crisis_id} has only {len(slice_df)} bars (expected >= 30)"
            )

            # Essential columns
            check_cols = ["Open", "High", "Low", "Close", "Volume",
                          "close_lag1", "return_1d", "return_lag1",
                          "vix", "us10y", "usdkrw", "wti", "sox"]
            for col in check_cols:
                assert col in slice_df.columns, f"Missing {col} in {m} for {crisis_id}"
                nan_cnt = slice_df[col].isna().sum()
                assert nan_cnt == 0, f"{nan_cnt} NaNs found in {m} {col} during {crisis_id}"
                inf_cnt = np.isinf(slice_df[col]).sum()
                assert inf_cnt == 0, f"{inf_cnt} Infs found in {m} {col} during {crisis_id}"

            # Strictly positive prices
            assert (slice_df["Close"] > 0).all(), f"Non-positive Close in {m} during {crisis_id}"
            assert (slice_df["High"] >= slice_df["Low"]).all(), f"High < Low in {m} during {crisis_id}"
            assert (slice_df["High"] >= slice_df["Close"]).all(), f"High < Close in {m} during {crisis_id}"
            assert (slice_df["Low"] <= slice_df["Close"]).all(), f"Low > Close in {m} during {crisis_id}"

    @pytest.mark.parametrize("crisis_id", list(HISTORICAL_CRISIS_PERIODS.keys()))
    def test_causal_lag_holds_throughout_crisis(self, panels, crisis_id):
        """Verify T-1 causal lag has 0 mismatches across the entire crisis volatility regime."""
        meta = HISTORICAL_CRISIS_PERIODS[crisis_id]
        s_date = meta["start_date"]
        e_date = meta["end_date"]

        for m in self.MARKETS:
            df = panels[m]
            # Include 1 bar before crisis start to check first crisis bar
            idx_loc = df.index.get_indexer([pd.to_datetime(s_date)], method="bfill")[0]
            start_loc = max(0, idx_loc - 1)
            end_loc = df.index.get_indexer([pd.to_datetime(e_date)], method="ffill")[0]

            sub_df = df.iloc[start_loc:end_loc + 1]
            diffs = np.abs(sub_df["close_lag1"].iloc[1:].values - sub_df["Close"].iloc[:-1].values)
            max_diff = np.max(diffs) if len(diffs) > 0 else 0.0
            assert max_diff < 1e-4, f"Causal lag violated in {m} during {crisis_id}, max diff: {max_diff}"

    def test_1997_asian_crisis_dynamics(self, panels):
        """1997 IMF Crisis: verify severe drawdown in KRX and currency pressure."""
        ks = panels["KOSPI"].loc["1997-07-01":"1998-12-31"]
        peak = ks["Close"].cummax()
        dd = (ks["Close"] - peak) / peak
        max_dd = dd.min()
        # KOSPI collapsed significantly during IMF crisis (typically > -50%)
        assert max_dd < -0.40, f"1997 IMF KOSPI drawdown was unexpectedly mild: {max_dd:.2%}"

        # USDKRW exchange rate pressure (won depreciation)
        usdkrw_max = ks["usdkrw"].max()
        assert usdkrw_max >= 1300.0, f"1997 IMF USDKRW peak ({usdkrw_max:.1f}) was below expected crisis levels"

    def test_2000_dotcom_crash_dynamics(self, panels):
        """2000 Dot-com crash: verify severe tech drawdown in NASDAQ."""
        nasdaq = panels["NASDAQ"].loc["2000-03-01":"2002-10-31"]
        peak = nasdaq["Close"].cummax()
        dd = (nasdaq["Close"] - peak) / peak
        max_dd = dd.min()
        assert max_dd < -0.50, f"2000 NASDAQ tech drawdown was unexpectedly small: {max_dd:.2%}"

    def test_2008_gfc_vix_and_equity_shock(self, panels):
        """2008 GFC: verify VIX spike > 50 and equity drawdowns."""
        sp = panels["SP500"].loc["2007-10-01":"2009-03-31"]
        vix_max = sp["vix"].max()
        assert vix_max >= 50.0, f"2008 GFC VIX spike did not exceed 50.0: max was {vix_max}"

        peak = sp["Close"].cummax()
        dd = (sp["Close"] - peak) / peak
        max_dd = dd.min()
        assert max_dd < -0.40, f"2008 SP500 drawdown was unexpectedly small: {max_dd:.2%}"

    def test_2020_covid_shock_dynamics(self, panels):
        """2020 COVID: acute volatility spike with rapid recovery."""
        sp = panels["SP500"].loc["2020-02-01":"2020-04-30"]
        vix_max = sp["vix"].max()
        assert vix_max >= 50.0, f"2020 COVID VIX spike did not exceed 50.0: max was {vix_max}"

        peak = sp["Close"].cummax()
        dd = (sp["Close"] - peak) / peak
        max_dd = dd.min()
        assert max_dd < -0.20, f"2020 COVID drawdown was unexpectedly small: {max_dd:.2%}"

    def test_2022_inflation_rate_hike_dynamics(self, panels):
        """2022 Rate hike: US 10Y yield surge."""
        sp = panels["SP500"].loc["2022-01-01":"2022-12-31"]
        us10y_start = sp["us10y"].iloc[0]
        us10y_end = sp["us10y"].iloc[-1]
        assert us10y_end > us10y_start, "US 10Y yields did not increase during 2022 rate hike"


# ==============================================================================
# 2. KOSDAQ Inception Transition Boundary Stress
# ==============================================================================

class TestKosdaqInceptionBoundary:
    """Empirical testing of KOSDAQ inception on 1996-07-01 and pre-inception backfill."""

    def test_kosdaq_transition_continuity(self, panels):
        """Check the boundary between synthetic Jan-Jun 1996 and authentic Jul 1996+."""
        kq = panels["KOSDAQ"]
        # Boundary trading dates around end of June / early July 1996
        kq_june = kq.loc["1996-06-25":"1996-07-05"]
        assert len(kq_june) >= 5, "Insufficient bars around KOSDAQ inception transition"

        # Check for no infinite returns or zero prices
        rets = kq_june["Close"].pct_change().dropna()
        assert (np.abs(rets) < 0.20).all(), (
            f"Artificial return jump detected at KOSDAQ inception boundary: {rets.max():.2%}, {rets.min():.2%}"
        )

        # Check causal lag is valid across the boundary date
        for i in range(1, len(kq_june)):
            curr_lag = kq_june["close_lag1"].iloc[i]
            prev_close = kq_june["Close"].iloc[i - 1]
            assert abs(curr_lag - prev_close) < 1e-4, (
                f"Causal lag break at transition date {kq_june.index[i]}: lag1={curr_lag}, prev_close={prev_close}"
            )

    def test_kosdaq_backfill_correlation_identity(self, panels):
        """Ensure synthetic KOSDAQ perfectly correlates with KOSPI in Jan-Jun 1996."""
        ks = panels["KOSPI"].loc["1996-01-03":"1996-06-28"]
        kq = panels["KOSDAQ"].loc["1996-01-03":"1996-06-28"]

        ks_ret = ks["Close"].pct_change().dropna()
        kq_ret = kq["Close"].pct_change().dropna()

        corr = ks_ret.corr(kq_ret)
        assert abs(corr - 1.0) < 1e-6, f"Correlation between KOSPI and synthetic KOSDAQ is not 1.0: {corr}"

        # Cumulative returns match
        ks_cum = (ks["Close"].iloc[-1] / ks["Close"].iloc[0]) - 1.0
        kq_cum = (kq["Close"].iloc[-1] / kq["Close"].iloc[0]) - 1.0
        assert abs(ks_cum - kq_cum) < 1e-5, f"Cumulative return mismatch: KS={ks_cum:.4%}, KQ={kq_cum:.4%}"


# ==============================================================================
# 3. Cache Reload Latency & Process Memory Footprint
# ==============================================================================

class TestCachePerformanceAndMemory:
    """Benchmark reload latency and verify bounded memory consumption."""

    def test_multi_iteration_cache_reload_speed(self, pipeline):
        """Ensure caching reload is consistently fast across multiple cold/warm cycles."""
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            panels = pipeline.load_30year_panel()
            dt = time.perf_counter() - t0
            latencies.append(dt)
            assert len(panels) == 5

        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        # Requirement: well below 0.50s
        assert avg_lat < 0.30, f"Average cache reload latency too high: {avg_lat:.4f}s"
        assert max_lat < 0.50, f"Max cache reload latency too high: {max_lat:.4f}s"

    def test_memory_overhead_boundedness(self, pipeline):
        """Ensure loading all 5 panels does not exceed sane memory boundaries."""
        import tracemalloc
        tracemalloc.start()
        gc.collect()

        # Load panels
        panels = pipeline.load_30year_panel()
        total_rows = sum(len(df) for df in panels.values())
        assert total_rows >= 38000, f"Expected >= 38,000 rows across 5 markets, got {total_rows}"

        # Deep pandas memory usage
        deep_mem_bytes = sum(df.memory_usage(deep=True).sum() for df in panels.values())
        deep_mem_mb = deep_mem_bytes / (1024 * 1024)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)

        # 38,000 rows x 30 float columns should be around 10-25MB deep memory
        assert deep_mem_mb < 50.0, f"Deep DataFrame memory usage is unexpectedly large: {deep_mem_mb:.2f} MB"
        # Traced memory during loading should be well under 250MB
        assert peak_mb < 250.0, f"Peak allocation during cache reload too high: {peak_mb:.2f} MB"


# ==============================================================================
# 4. Adversarial Edge Cases & Protocol Resilience
# ==============================================================================

class TestAdversarialEdgeCases:
    """Stress-test edge cases, malformed inputs, and non-standard boundaries."""

    def test_case_insensitive_dict_extreme_keys(self):
        """Test CaseInsensitiveDict with non-string, unicode, and whitespace keys."""
        d = CaseInsensitiveDict()
        d["  sp500  "] = 1
        assert d["SP500"] == 1
        assert d["s&p500"] == 1
        assert "sp500" in d
        assert "  SP500  " in d

        # Numeric key
        d[42] = "answer"
        assert d[42] == "answer"
        assert 42 in d
        assert d.pop(42) == "answer"
        assert 42 not in d

        # Copy behavior
        d["nasdaq"] = "tech"
        c = d.copy()
        assert isinstance(c, CaseInsensitiveDict)
        assert c["^IXIC"] == "tech"
        c["nasdaq"] = "modified"
        assert d["nasdaq"] == "tech"  # original unmutated

        # setdefault
        val = d.setdefault("kospi", "korea")
        assert val == "korea"
        assert d["KS11"] == "korea"
        val2 = d.setdefault("KS11", "different")
        assert val2 == "korea"  # existing retained

    def test_apply_causal_lag_negative_lag_raises(self):
        """Negative lag periods must raise ValueError (prevents anti-causal lookahead)."""
        df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]})
        with pytest.raises(ValueError, match="lag_periods must be non-negative"):
            apply_causal_lag(df, lag_periods=-1)

    def test_apply_causal_lag_zero_lag(self):
        """lag_periods=0 should produce identity lag0 without crashing."""
        df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]})
        out = apply_causal_lag(df, lag_periods=0)
        assert "Close_lag0" in out.columns
        assert (out["Close_lag0"] == df["Close"]).all()

    def test_apply_causal_lag_non_monotonic_datetime_index(self):
        """Non-monotonic DatetimeIndex must be handled without chronological corruption."""
        dates = pd.to_datetime(["2020-01-03", "2020-01-01", "2020-01-02"])
        df = pd.DataFrame({"Close": [103.0, 101.0, 102.0]}, index=dates)

        out = apply_causal_lag(df, lag_periods=1)
        # Original row order must be preserved
        assert list(out.index) == list(dates)
        # When sorted chronologically: 2020-01-01 (101.0) -> 2020-01-02 (102.0) -> 2020-01-03 (103.0)
        # So lag1 on 2020-01-01 should be NaN
        # lag1 on 2020-01-02 should be 101.0
        # lag1 on 2020-01-03 should be 102.0
        assert out.loc[pd.to_datetime("2020-01-02"), "Close_lag1"] == 101.0
        assert out.loc[pd.to_datetime("2020-01-03"), "Close_lag1"] == 102.0
        assert np.isnan(out.loc[pd.to_datetime("2020-01-01"), "Close_lag1"])

    def test_align_fundamentals_causally_point_in_time_boundaries(self):
        """Fundamentals available after trade date must NOT be visible."""
        # Price dates in early 2020
        p_dates = pd.date_range("2020-03-01", "2020-06-01", freq="B")
        prices_df = pd.DataFrame({"Close": np.linspace(100, 120, len(p_dates))}, index=p_dates)

        # Fundamentals reported for Q1 2020 (period end 2020-03-31)
        # KRX statutory filing lag: 45 days -> date_available = 2020-05-15
        funds_df = pd.DataFrame({
            "date": ["2020-03-31"],
            "period_type": ["quarterly"],
            "eps": [5.50],
        })

        aligned = align_fundamentals_causally(prices_df, funds_df, is_krx=True)

        # Before 2020-05-15, eps must be NaN (no lookahead)
        pre_avail = aligned.loc[:"2020-05-14"]
        assert pre_avail["eps"].isna().all(), "Forward leakage: Q1 EPS appeared before 45-day statutory filing lag"

        # On or after 2020-05-15, eps must be 5.50
        post_avail = aligned.loc["2020-05-15":]
        assert (post_avail["eps"] == 5.50).all(), "Fundamentals not merged on date_available"

    def test_geographical_shift_causality(self):
        """apply_geographical_shift: US series on T must only be visible on KRX at T+1."""
        dates = pd.bdate_range("2023-01-02", "2023-01-10")
        us_series = pd.DataFrame({"VIX": [20.0, 25.0, 30.0, 22.0, 21.0, 19.0, 18.0]}, index=dates[:7])
        krx_calendar = dates[1:6]  # Jan 3 to Jan 9

        shifted = apply_geographical_shift(us_series, krx_calendar)

        # On Jan 3, KRX should see US VIX from Jan 2 (20.0), NOT Jan 3 (25.0)
        assert shifted.loc["2023-01-03", "VIX"] == 20.0
        # On Jan 4, KRX should see US VIX from Jan 3 (25.0)
        assert shifted.loc["2023-01-04", "VIX"] == 25.0

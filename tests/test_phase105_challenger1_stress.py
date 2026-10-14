"""
tests/test_phase105_challenger1_stress.py — Adversarial Stress Test Suite for Phase 105 Milestone 1

Adversarially probes:
1. Future data mutation invariance at bar T (mutating future prices/fundamentals produces zero diff).
2. Boundary dates: 1996-01-02, 2026-08-31, leap years (2000, 2024), holidays (New Year, Christmas).
3. Illiquid / zero-volume / single-bar stocks: ADV calculation, NaN absence, zero division safety.
4. Delisted companies terminal bankruptcy loss (-100% loss realization for LEH, Hanbo Steel, Enron, etc.).
5. Parquet cache consistency under variable lookback requests (Cache Truncation Defect).
6. NaN propagation in financial ratios prior to 2021 DB coverage.
"""

import math
import shutil
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from trading_system.src.backtest.historical_stock_universe_pipeline import (
    PointInTimeStockUniverse,
    HistoricalStockUniversePipeline,
    StockListingMetadata,
    MultiStockPanel,
    compute_regulatory_filing_lag,
    apply_statutory_filing_lag,
    align_fundamentals_causally,
    TARGET_MARKETS,
    normalize_market,
    is_krx_market,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_challenger_m1_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# ==============================================================================
# 1. Future Data Mutation Invariance at bar T
# ==============================================================================

def test_future_price_mutation_invariance(tmp_dir):
    """
    Adversarial Test 1A:
    Query get_market_panel(date=T).
    Mutate future price data at T, T+1, T+10 with extreme anomalies.
    Verify get_market_panel(date=T) produces ZERO difference.
    """
    universe = PointInTimeStockUniverse()
    pipeline = HistoricalStockUniversePipeline(
        cache_dir=tmp_dir / "cache1",
        universe=universe,
        use_cache=False
    )

    query_date = "2015-06-15"
    panel_baseline = pipeline.get_market_panel(query_date, lookback_days=20, market="SP500")
    assert not panel_baseline.empty

    # Max date in panel must strictly be <= 2015-06-12 (Friday before June 15)
    max_baseline_date = pd.to_datetime(panel_baseline["date"]).max()
    assert max_baseline_date <= pd.to_datetime("2015-06-12")

    # Invalidate in-memory cache to force re-fetch
    pipeline._in_memory_price_cache.clear()

    orig_synth_fn = pipeline._generate_synthetic_stock_history

    def poisoned_synth(symbol, meta, calendar_dates):
        df = orig_synth_fn(symbol, meta, calendar_dates)
        future_mask = df.index >= pd.to_datetime(query_date)
        if future_mask.any():
            df.loc[future_mask, "close"] = 999999999.0
            df.loc[future_mask, "open"] = 999999999.0
            df.loc[future_mask, "high"] = 999999999.0
            df.loc[future_mask, "low"] = 999999999.0
            df.loc[future_mask, "volume"] = 999999999
        return df

    pipeline._generate_synthetic_stock_history = poisoned_synth

    # Re-fetch panel at query_date
    panel_after_future_mutation = pipeline.get_market_panel(query_date, lookback_days=20, market="SP500")

    # Clean assertion: bit-for-bit identical
    pd.testing.assert_frame_equal(panel_baseline, panel_after_future_mutation)


def test_future_fundamentals_causal_invariance():
    """
    Adversarial Test 1B:
    Direct test on align_fundamentals_causally.
    Quarter ending 2020-03-31 is available on 2020-05-10.
    Prices up to 2020-05-08 must receive 2019-12-31 fundamentals.
    Mutating 2020-03-31 fundamentals must have ZERO effect on prices <= 2020-05-08.
    """
    dates = pd.bdate_range("2020-05-01", "2020-05-08")
    prices_df = pd.DataFrame({
        "open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000000
    }, index=dates)

    funds_clean = pd.DataFrame([
        {"date": "2019-12-31", "period_type": "annual", "eps": 2.0, "net_income": 200.0},
        {"date": "2020-03-31", "period_type": "quarterly", "eps": 3.5, "net_income": 350.0},
    ])

    funds_poisoned = pd.DataFrame([
        {"date": "2019-12-31", "period_type": "annual", "eps": 2.0, "net_income": 200.0},
        {"date": "2020-03-31", "period_type": "quarterly", "eps": 99999.0, "net_income": 999999.0},
    ])

    m_clean = align_fundamentals_causally(prices_df, funds_clean, is_krx=False)
    m_poisoned = align_fundamentals_causally(prices_df, funds_poisoned, is_krx=False)

    # All rows are <= 2020-05-08, so they must be identical
    pd.testing.assert_frame_equal(m_clean, m_poisoned)
    assert (m_clean["eps"] == 2.0).all()


# ==============================================================================
# 2. Boundary Dates & Extreme Calenders
# ==============================================================================

@pytest.mark.parametrize("b_date", [
    "1996-01-02",  # 30-year start boundary
    "1996-01-01",  # Start holiday (New Year)
    "2000-02-29",  # Century leap year
    "2024-02-29",  # Standard leap year
    "2026-08-31",  # 30-year end boundary
    "2023-12-25",  # Christmas holiday
    "2024-01-01",  # New Year holiday
    "1997-12-03",  # IMF bailout signing day
    "2008-09-15",  # Lehman bankruptcy day
    "2020-03-23",  # COVID crash bottom
])
def test_boundary_dates_robustness(tmp_dir, b_date):
    """
    Adversarial Test 2:
    Querying historical boundary dates across 1996~2026 must never crash,
    must never emit NaNs in critical columns, and must strictly maintain causal bounds.
    """
    pipeline = HistoricalStockUniversePipeline(
        cache_dir=tmp_dir / "cache_boundary",
        use_cache=False
    )
    panel = pipeline.get_universe_panel(b_date, lookback_days=10, markets=["SP500", "KOSPI"])

    # Jan 1 has no previous trading day in 1996
    if b_date == "1996-01-01":
        return

    assert not panel.empty, f"Panel for date {b_date} should not be empty"

    max_d = pd.to_datetime(panel["date"]).max()
    assert max_d < pd.to_datetime(b_date), f"Panel date {max_d} must be strictly < query date {b_date}"

    # Critical columns must have zero NaNs
    for col in ["date", "symbol", "close", "adv_20d", "market", "sector"]:
        assert panel[col].isna().sum() == 0, f"Column {col} has NaNs on {b_date}"

    assert (panel["close"] > 0).all(), f"Close <= 0 found on {b_date}"
    assert (panel["adv_20d"] >= 100.0).all(), f"ADV < 100 found on {b_date}"


# ==============================================================================
# 3. Illiquid / Zero-Volume / Suspended Stocks
# ==============================================================================

def test_zero_volume_stock_adv_stability():
    """
    Adversarial Test 3A:
    A stock with zero volume for 250 consecutive trading days (suspended trading).
    Rolling ADV must NOT crash, must NOT emit NaNs, and must hold floor >= 100.0.
    """
    meta = StockListingMetadata(
        symbol="SUSPENDED",
        name="Suspended Corp",
        market="SP500",
        sector="Industrials",
        listing_date=pd.to_datetime("2000-01-01")
    )
    pipeline = HistoricalStockUniversePipeline(use_cache=False)

    dates = pd.bdate_range("2020-01-01", "2020-12-31")
    zero_vol_df = pd.DataFrame({
        "open": 50.0,
        "high": 50.0,
        "low": 50.0,
        "close": 50.0,
        "volume": 0
    }, index=dates)

    features = pipeline._compute_vectorized_features(zero_vol_df, meta)

    assert "adv_20d" in features.columns
    assert "adv_shares_20d" in features.columns
    assert features["adv_20d"].isna().sum() == 0
    assert features["adv_shares_20d"].isna().sum() == 0
    assert (features["adv_20d"] >= 100.0).all()
    assert (features["adv_shares_20d"] >= 10.0).all()


def test_micro_history_stock_safety():
    """
    Adversarial Test 3B:
    A newly listed stock with only 1 or 2 trading bars.
    Rolling window (min_periods=5) must gracefully fillna without throwing exceptions.
    """
    meta = StockListingMetadata(
        symbol="NEWIPO",
        name="Fresh IPO",
        market="SP500",
        sector="Technology",
        listing_date=pd.to_datetime("2020-05-01")
    )
    pipeline = HistoricalStockUniversePipeline(use_cache=False)

    short_dates = pd.bdate_range("2020-05-01", periods=2)
    micro_df = pd.DataFrame({
        "open": [10.0, 11.0],
        "high": [11.0, 12.0],
        "low": [9.5, 10.5],
        "close": [10.5, 11.5],
        "volume": [1000, 2000]
    }, index=short_dates)

    features = pipeline._compute_vectorized_features(micro_df, meta)
    assert len(features) == 2
    assert features["adv_20d"].isna().sum() == 0
    assert (features["adv_20d"] >= 100.0).all()


# ==============================================================================
# 4. Delisted Companies Terminal Bankruptcy Loss (-100%)
# ==============================================================================

def test_delisting_bankruptcy_losses_catalog():
    """
    Adversarial Test 4:
    Comprehensive verification of historical delistings across all 3 major crisis epochs:
    - 1997 IMF Crisis (Hanbo, Sammi, Daewoo, Daewoo Electronics, Dong-Ah)
    - 2000 Dot-com Crash (Enron, WorldCom, Pets.com, Webvan, eToys, Commerce One, Medison)
    - 2008 GFC (Lehman, WaMu, Bear Stearns, Wachovia, Circuit City, New Century)
    """
    universe = PointInTimeStockUniverse()

    # 1. 1997 IMF Crisis Bankruptcies
    imf_bankruptcies = [
        ("001550", "1997-06-01", "1997-12-15", -1.0),  # Hanbo Steel
        ("005230", "1997-05-01", "1997-11-20", -1.0),  # Sammi Steel
        ("001490", "1999-12-01", "2000-05-15", -1.0),  # Daewoo
        ("005300", "2000-01-01", "2001-08-30", -1.0),  # Daewoo Electronics
        ("002210", "2000-01-01", "2001-05-11", -1.0),  # Dong-Ah Construction
    ]
    for sym, pre_dt, delist_dt, expected_loss in imf_bankruptcies:
        assert universe.is_symbol_active(sym, pre_dt) is True, f"{sym} should be active at {pre_dt}"
        assert universe.is_delisted(sym, delist_dt) is True, f"{sym} should be delisted at {delist_dt}"
        assert universe.get_delisting_terminal_loss(sym, delist_dt) == expected_loss, f"{sym} loss should be {expected_loss}"

    # 2. 2000 Dot-com Crash Bankruptcies
    dotcom_bankruptcies = [
        ("ENE", "2001-06-01", "2001-12-02", -1.0),   # Enron
        ("WCOM", "2002-01-01", "2002-07-21", -1.0),  # WorldCom
        ("IPET", "2000-05-01", "2000-11-07", -1.0),  # Pets.com
        ("WBVN", "2000-01-01", "2001-07-09", -1.0),  # Webvan
        ("ETYS", "2000-01-01", "2001-03-08", -1.0),  # eToys
        ("CMRC", "2003-01-01", "2004-10-06", -1.0),  # Commerce One
        ("018310", "2001-01-01", "2002-04-10", -1.0),# Medison
    ]
    for sym, pre_dt, delist_dt, expected_loss in dotcom_bankruptcies:
        assert universe.is_symbol_active(sym, pre_dt) is True, f"{sym} should be active at {pre_dt}"
        assert universe.is_delisted(sym, delist_dt) is True, f"{sym} should be delisted at {delist_dt}"
        assert universe.get_delisting_terminal_loss(sym, delist_dt) == expected_loss, f"{sym} loss should be {expected_loss}"

    # 3. 2008 GFC Bankruptcies & Distressed Mergers
    gfc_events = [
        ("LEH", "2008-09-12", "2008-09-15", -1.0),   # Lehman Brothers (-100%)
        ("WM", "2008-09-20", "2008-09-26", -1.0),    # Washington Mutual (-100%)
        ("CC", "2008-06-01", "2008-11-10", -1.0),    # Circuit City (-100%)
        ("NEW", "2006-12-01", "2007-04-02", -1.0),   # New Century Financial (-100%)
        ("BSC", "2008-01-01", "2008-05-30", -0.90),  # Bear Stearns (-90% salvage)
        ("WB", "2008-06-01", "2008-12-31", -0.85),   # Wachovia (-85% salvage)
    ]
    for sym, pre_dt, delist_dt, expected_loss in gfc_events:
        assert universe.is_symbol_active(sym, pre_dt) is True, f"{sym} should be active at {pre_dt}"
        assert universe.is_delisted(sym, delist_dt) is True, f"{sym} should be delisted at {delist_dt}"
        assert universe.get_delisting_terminal_loss(sym, delist_dt) == expected_loss, f"{sym} loss should be {expected_loss}"


# ==============================================================================
# 5. EMPIRICAL DEFECT PROBES (Cache Truncation & Fundamental NaN Leakage)
# ==============================================================================

def test_parquet_cache_lookback_invariance(tmp_dir):
    """
    Adversarial Test 5 (DEFECT PROBE):
    Probes cache coherency when variable lookback queries are executed.
    Calling get_market_panel(lookback_days=5) overwrites parquet cache with partial slice (11 bars).
    Subsequent get_market_panel(lookback_days=50) then returns only 11 bars instead of 50 bars.
    """
    pipeline = HistoricalStockUniversePipeline(
        cache_dir=tmp_dir / "test_cache_lookback",
        use_cache=True
    )
    query_date = "2008-09-15"

    df_short = pipeline.get_market_panel(query_date, lookback_days=5, market="SP500")
    aapl_short = df_short[df_short["symbol"] == "AAPL"]
    assert len(aapl_short) == 5

    df_long = pipeline.get_market_panel(query_date, lookback_days=50, market="SP500")
    aapl_long = df_long[df_long["symbol"] == "AAPL"]

    assert len(aapl_long) == 50, (
        f"CACHE POISONING DEFECT: Querying lookback_days=50 after lookback_days=5 returned only "
        f"{len(aapl_long)} bars instead of 50 bars!"
    )


def test_fundamental_ratios_nan_absence():
    """
    Adversarial Test 6 (DEFECT PROBE):
    Probes whether pre-2021 historical panels emit NaNs in operating_margin, roe, and debt_to_equity.
    In 2008-09-15, DB fundamentals do not exist, so align_fundamentals_causally merges NaNs.
    _compute_vectorized_features fails to fillna on revenue and book_value, resulting in NaNs.
    """
    pipeline = HistoricalStockUniversePipeline(use_cache=False)
    panel = pipeline.get_market_panel("2008-09-15", lookback_days=5, market="SP500")

    nan_op_margin = panel["operating_margin"].isna().sum()
    nan_roe = panel["roe"].isna().sum()
    nan_debt_equity = panel["debt_to_equity"].isna().sum()

    assert nan_op_margin == 0, f"operating_margin has {nan_op_margin} / {len(panel)} NaNs on 2008-09-15"
    assert nan_roe == 0, f"roe has {nan_roe} / {len(panel)} NaNs on 2008-09-15"
    assert nan_debt_equity == 0, f"debt_to_equity has {nan_debt_equity} / {len(panel)} NaNs on 2008-09-15"

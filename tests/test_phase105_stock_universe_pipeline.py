"""
tests/test_phase105_stock_universe_pipeline.py — Verification Suite for Phase 105 Milestone 1

Tests:
1. PointInTimeStockUniverse metadata, constituents, and active status tracking across 5 markets.
2. Survivorship bias defense: historical bankruptcies and delistings (1997 IMF, 2000 Dot-com, 2008 GFC)
   retaining active status during lifetime and realizing terminal liquidation losses (-1.0).
3. Strict dynamic regulatory filing lag (KRX 45d/90d, US 40d/60d) and causal fundamental alignment.
4. Causal pricing up to T-1 bar: zero future price or volume leakage into decision date t.
5. 20-day rolling Average Daily Volume (ADV) calculation and standard clean schema.
6. Vectorized MultiStockPanel 30-year tensor and cross-sectional snapshot extraction.
7. Programmatic verification via verify_causality_and_no_lookahead().
"""

import math
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

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
def universe():
    """Initializes standard PointInTimeStockUniverse fixture."""
    return PointInTimeStockUniverse()


@pytest.fixture
def pipeline(universe, tmp_path):
    """Initializes HistoricalStockUniversePipeline fixture with isolated temporary cache."""
    return HistoricalStockUniversePipeline(
        cache_dir=tmp_path / "test_cache",
        universe=universe,
        use_cache=True
    )


# ==============================================================================
# 1. PointInTimeStockUniverse & Market Coverage
# ==============================================================================

def test_pit_universe_market_coverage(universe):
    """Verifies that all 5 target markets have registered constituents."""
    for m in TARGET_MARKETS:
        symbols = universe.get_all_symbols(m)
        assert len(symbols) >= 15, f"Market {m} should have at least 15 registered historical symbols, got {len(symbols)}"


def test_pit_universe_active_resolution(universe):
    """Verifies active universe resolution across different historical dates."""
    # S&P 500 in 1990: AAPL, MSFT, IBM should be active, NVDA (IPO 1999) should NOT be active
    sp_1990 = universe.get_active_universe("1990-01-01", "SP500")
    assert "AAPL" in sp_1990
    assert "MSFT" in sp_1990
    assert "IBM" in sp_1990
    assert "NVDA" not in sp_1990

    # S&P 500 in 2005: NVDA should now be active
    sp_2005 = universe.get_active_universe("2005-01-01", "SP500")
    assert "NVDA" in sp_2005


# ==============================================================================
# 2. Survivorship Bias Elimination (Historical Bankruptcies & Delistings)
# ==============================================================================

def test_survivorship_bias_defense_lehman(universe):
    """
    Verifies Lehman Brothers (LEH) tracking:
    - Active before bankruptcy (2008-09-12)
    - Delisted on/after bankruptcy (2008-09-15)
    - Terminal loss of -1.0 (-100%) realized
    """
    meta = universe.get_listing_metadata("LEH")
    assert meta is not None
    assert meta.delisting_reason == "BANKRUPTCY"
    assert meta.terminal_loss_pct == -1.0

    # Pre-bankruptcy: actively listed
    assert universe.is_symbol_active("LEH", "2008-09-12") is True
    assert universe.is_delisted("LEH", "2008-09-12") is False
    assert "LEH" in universe.get_active_universe("2008-09-12", "SP500")

    # Post-bankruptcy: delisted with -1.0 terminal loss
    assert universe.is_symbol_active("LEH", "2008-09-16") is False
    assert universe.is_delisted("LEH", "2008-09-16") is True
    assert "LEH" not in universe.get_active_universe("2008-09-16", "SP500")
    assert universe.get_delisting_terminal_loss("LEH", "2008-09-16") == -1.0


def test_survivorship_bias_defense_hanbo_steel(universe):
    """
    Verifies Hanbo Steel (001550) tracking in KOSPI during 1997 IMF Crisis:
    - Active during early 1997
    - Delisted in Dec 1997 with terminal bankruptcy loss
    """
    meta = universe.get_listing_metadata("001550")
    assert meta is not None
    assert meta.market == "KOSPI"
    assert meta.terminal_loss_pct == -1.0

    assert universe.is_symbol_active("001550", "1997-06-01") is True
    assert universe.is_delisted("001550", "1997-06-01") is False

    assert universe.is_symbol_active("001550", "1998-01-01") is False
    assert universe.is_delisted("001550", "1998-01-01") is True
    assert universe.get_delisting_terminal_loss("001550", "1998-01-01") == -1.0


def test_survivorship_bias_defense_dotcom_bankruptcies(universe):
    """
    Verifies 2000 Dot-com bankruptcies (Pets.com IPET, Webvan WBVN, Enron ENE).
    """
    # Pets.com
    ipet_meta = universe.get_listing_metadata("IPET")
    assert ipet_meta is not None
    assert universe.is_symbol_active("IPET", "2000-05-01") is True
    assert universe.is_delisted("IPET", "2000-12-01") is True
    assert universe.get_delisting_terminal_loss("IPET", "2000-12-01") == -1.0

    # Enron
    ene_meta = universe.get_listing_metadata("ENE")
    assert ene_meta is not None
    assert universe.is_symbol_active("ENE", "2001-06-01") is True
    assert universe.is_delisted("ENE", "2002-01-01") is True
    assert universe.get_delisting_terminal_loss("ENE", "2002-01-01") == -1.0


def test_delisting_events_query(universe):
    """Verifies get_delistings query returns registered historical delistings in window."""
    events_2008 = universe.get_delistings("2008-01-01", "2008-12-31")
    symbols_2008 = [e["symbol"] for e in events_2008]
    assert "LEH" in symbols_2008
    assert "WM" in symbols_2008
    assert "BSC" in symbols_2008


# ==============================================================================
# 3. Dynamic Regulatory Filing Lag Enforcement
# ==============================================================================

def test_regulatory_filing_lag_calculation():
    """
    Verifies exact statutory filing delays:
    - KRX quarterly: +45 calendar days
    - KRX annual (Dec 31): +90 calendar days
    - US SEC quarterly (10-Q): +40 calendar days
    - US SEC annual (10-K, Dec 31): +60 calendar days
    """
    # KRX Quarterly
    krx_q1 = compute_regulatory_filing_lag("2020-03-31", period_type="quarterly", is_krx=True)
    assert krx_q1 == "2020-05-15"  # March 31 + 45 days

    # KRX Annual
    krx_fy = compute_regulatory_filing_lag("2020-12-31", period_type="annual", is_krx=True)
    assert krx_fy == "2021-03-31"  # Dec 31 + 90 days (leap year 2020: 31+28+31=90 -> March 31)

    # US SEC Quarterly (10-Q)
    us_q1 = compute_regulatory_filing_lag("2020-03-31", period_type="quarterly", is_krx=False)
    assert us_q1 == "2020-05-10"  # March 31 + 40 days

    # US SEC Annual (10-K)
    us_fy = compute_regulatory_filing_lag("2020-12-31", period_type="annual", is_krx=False)
    assert us_fy == "2021-03-01"  # Dec 31 + 60 days (31 in Jan, 28 in Feb -> March 1)


def test_align_fundamentals_causally():
    """
    Verifies point-in-time backward causal merge:
    Prices before date_available DO NOT receive the newly filed fundamentals.
    """
    # Price dates: 2020-05-08 to 2020-05-15
    dates = pd.date_range("2020-05-08", "2020-05-15", freq="B")
    prices_df = pd.DataFrame({
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 102.0,
        "volume": 1000000
    }, index=dates)

    # US Q1 period ends 2020-03-31 -> available 2020-05-10 (Sunday) -> effective Monday 2020-05-11
    # Prior Q4 available earlier
    funds_df = pd.DataFrame([
        {"date": "2019-12-31", "period_type": "annual", "eps": 2.0, "net_income": 200.0},
        {"date": "2020-03-31", "period_type": "quarterly", "eps": 3.5, "net_income": 350.0},
    ])

    merged = align_fundamentals_causally(prices_df, funds_df, is_krx=False)

    # On 2020-05-08 (Friday, before May 10), eps must reflect Q4 (2.0), NOT Q1 (3.5)
    row_may08 = merged.loc["2020-05-08"]
    assert row_may08["eps"] == 2.0, "May 08 bar must NOT reflect unfiled Q1 results (lookahead bias violation!)"

    # On 2020-05-11 (Monday, after May 10), eps must reflect Q1 (3.5)
    row_may11 = merged.loc["2020-05-11"]
    assert row_may11["eps"] == 3.5, "May 11 bar must reflect newly available Q1 results"


# ==============================================================================
# 4. Causal Pricing & Feature Store Panels
# ==============================================================================

def test_get_market_panel_causal_pricing(pipeline):
    """
    Verifies get_market_panel strictly respects causal pricing up to T-1.
    If query date is 2008-09-15 (Monday), max date in returned panel must be <= 2008-09-12 (Friday).
    """
    panel = pipeline.get_market_panel("2008-09-15", lookback_days=5, market="SP500")
    assert not panel.empty, "Market panel should not be empty"

    max_dt = pd.to_datetime(panel["date"]).max()
    assert max_dt <= pd.to_datetime("2008-09-12"), f"Max date {max_dt} must be <= 2008-09-12 (zero lookahead leakage)"


def test_get_market_panel_clean_schema(pipeline):
    """
    Verifies that get_market_panel produces all standard clean schema columns.
    """
    panel = pipeline.get_market_panel("2020-03-23", lookback_days=10, market="SP500")
    required_cols = [
        "date", "symbol", "open", "high", "low", "close", "volume",
        "adv_20d", "market", "sector", "pe_ratio", "pb_ratio", "roe",
        "operating_margin", "market_cap"
    ]
    for col in required_cols:
        assert col in panel.columns, f"Required column '{col}' missing from market panel"

    # Check finite positive ADV and Close
    assert (panel["close"] > 0).all(), "All close prices must be strictly positive"
    assert (panel["adv_20d"] > 0).all(), "20-day ADV must be strictly positive"
    assert panel["adv_20d"].isna().sum() == 0, "No NaNs permitted in ADV column"


def test_get_universe_panel_multi_market(pipeline):
    """
    Verifies get_universe_panel composite across US and Korean markets.
    """
    panel = pipeline.get_universe_panel(
        "2021-06-01",
        lookback_days=3,
        markets=["KOSPI", "SP500"]
    )
    assert not panel.empty
    markets_in_panel = set(panel["market"].unique())
    assert "KOSPI" in markets_in_panel
    assert "SP500" in markets_in_panel


# ==============================================================================
# 5. MultiStockPanel 30-Year Tensor Loader
# ==============================================================================

def test_load_30year_multi_stock_panel(pipeline):
    """
    Verifies 30-year multi-stock tensor loader across 1996~2026.
    """
    panel = pipeline.load_30year_stock_universe_panel(
        start_date="1996-01-01",
        end_date="2026-08-31",
        markets=["SP500", "KOSPI"],
        symbols_per_market=4
    )

    assert isinstance(panel, MultiStockPanel)
    assert len(panel.symbols) >= 8
    assert len(panel.dates) > 7000, f"30-year calendar should have >7000 business days, got {len(panel.dates)}"

    # Check ADV matrix
    assert panel.adv_matrix.shape[0] == len(panel.dates)
    assert panel.adv_matrix.shape[1] == len(panel.symbols)
    assert (panel.adv_matrix > 0).all().all()

    # Check returns matrix
    ret_mat = panel.get_returns_matrix(horizon=1)
    assert ret_mat.shape == (len(panel.dates), len(panel.symbols))
    assert not ret_mat.isna().any().any()

    # Check cross-section extraction
    cross_df = panel.get_cross_section("2008-09-12")
    assert not cross_df.empty
    assert "sector" in cross_df.columns
    assert "close" in cross_df.columns


# ==============================================================================
# 6. Independent Causality & Verification Method
# ==============================================================================

def test_verify_causality_and_no_lookahead(pipeline):
    """
    Verifies the automated self-audit verification method.
    """
    audit_res = pipeline.verify_causality_and_no_lookahead(test_date="2008-09-15")
    assert audit_res["passed"] is True, f"Causality verification failed: {audit_res}"
    assert audit_res["checks"]["causal_pricing_no_future_leakage"] is True
    assert audit_res["checks"]["dynamic_filing_lag_enforced"] is True
    assert audit_res["checks"]["survivorship_bias_defense_active"] is True
    assert audit_res["checks"]["rolling_adv_positive_and_valid"] is True

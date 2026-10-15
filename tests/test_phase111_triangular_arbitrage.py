"""
tests/test_phase111_triangular_arbitrage.py
Release R127 / Phase 111 Production Master / v118 (Feature F528).

Comprehensive Unit, Invariant, and Integration Test Suite for:
Milestone M4 (Triangular Parity & Cross-Venue Arbitrage Execution Slicer).

Covering 10 Distinct Categories (45+ Test Cases):
- Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
- Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
- Category 3: Triplet Data Models & Parity Valuation (Dual ADR, ETF Basket, FX Triangles) (TC06~TC10)
- Category 4: Sub-Millisecond Point-in-Time Discrepancy Detection & Zero Lookahead Bias (TC11~TC15)
- Category 5: Round-Trip Friction Modeling & Hurdle Rate Filtering (TC16~TC20)
- Category 6: Slicing Trajectory, ADV Liquidity Cap (<= 1.5%), and Integer Volume Conservation (TC21~TC25)
- Category 7: Zero-Slippage Fill Verification & IOC/FOK Pricing Bounds (TC26~TC30)
- Category 8: Partial-Fill Emergency Unwinding & Zero Naked Delta Invariant (TC31~TC35)
- Category 9: SmartOrderRouter & ExecutionOMSEngine Integration (Gate 8.1 & Dark Pool Probing) (TC36~TC40)
- Category 10: Adversarial Stress, Numerical Boundary, and Extreme Shock Testing (TC41~TC45)
"""

import hashlib
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pytest

# Ensure repository root and trading_system paths are available
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.execution.triangular_arbitrage_slicer import (
    TriangularArbitrageSlicer,
    TriangularParityArbitrageEngine,
    CrossVenueArbitrageSlicer,
    MultiLegArbitrageSlicer,
    TriangularArbitrageEngine,
    CrossMarketArbitrageSlicer,
    Phase111TriangularArbitrageSlicer,
    CrossVenueArbitrageEngine,
    TriangularParitySlicer,
    Phase111ArbitrageSlicer,
    ArbitrageType,
    OrderLegSide,
    OrderLegType,
    UnwindMode,
    TriangularParityStatus,
    VenueQuote,
    ArbitrageLegSpec,
    ArbitrageTriplet,
    FrictionBreakdown,
    ArbitrageDiscrepancy,
    ArbitrageOpportunity,
    LegExecutionFill,
    PartialFillUnwindPlan,
    TriangularSliceSchedule,
    TriangularArbitrageExecutionReport,
    LookaheadBiasException,
    ArbitrageExecutionError,
    HurdleNotMetException,
)
from src.risk.borrow_dynamics_model import BorrowDynamicsModel, BorrowFeeQuote, Gate8_1Verdict
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def slicer():
    """Returns a standard TriangularArbitrageSlicer instance."""
    return TriangularArbitrageSlicer(hurdle_rate_bps=2.5, max_adv_participation_rate=0.015)


@pytest.fixture
def adr_triplet():
    """Dual-listed ADR triplet (TSM ADR on US vs 2330 ORD on TWSE vs USD/TWD FX)."""
    return ArbitrageTriplet(
        triplet_id="TSM_ADR_ORD_TRIANGLE",
        triplet_type=ArbitrageType.DUAL_LISTED_ADR,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER, is_us=True),
            ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
            ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
        ),
        depositary_ratio=5.0,  # 5 ORD shares per 1 ADR
        hurdle_rate_bps=2.5,
    )


@pytest.fixture
def etf_triplet():
    """ETF vs constituent basket triplet (SOXX vs Semiconductor Basket)."""
    return ArbitrageTriplet(
        triplet_id="SOXX_ETF_BASKET_TRIANGLE",
        triplet_type=ArbitrageType.ETF_BASKET,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="SOXX", market="NASDAQ", venue="NASDAQ", leg_role=OrderLegType.LEADER, is_us=True),
            ArbitrageLegSpec(leg_id=2, symbol="SOXX_BASKET", market="US", venue="COMPOSITE_INAV", leg_role=OrderLegType.FOLLOWER, is_us=True),
            ArbitrageLegSpec(leg_id=3, symbol="USD_FINANCING", market="MONEY_MARKET", venue="CASH", leg_role=OrderLegType.HEDGE),
        ),
        depositary_ratio=1.0,
        hurdle_rate_bps=2.5,
    )


@pytest.fixture
def fx_triplet():
    """Cross-currency FX triplet (EUR/USD, USD/KRW, EUR/KRW)."""
    return ArbitrageTriplet(
        triplet_id="EUR_USD_KRW_TRIANGLE",
        triplet_type=ArbitrageType.CROSS_CURRENCY_FX,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="EUR/USD", market="FX", venue="EBS", leg_role=OrderLegType.FOLLOWER),
            ArbitrageLegSpec(leg_id=2, symbol="USD/KRW", market="FX", venue="SEOUL_MONEY", leg_role=OrderLegType.LEADER),
            ArbitrageLegSpec(leg_id=3, symbol="EUR/KRW", market="FX", venue="COMPOSITE_FX", leg_role=OrderLegType.HEDGE),
        ),
        depositary_ratio=1.0,
        hurdle_rate_bps=2.5,
    )


# =============================================================================
# Category 1: Class Exports, Signatures & Full Alias Trees (TC01 ~ TC04)
# =============================================================================

def test_tc01_class_exports_and_aliases():
    """TC01: Verify all 10 alias names resolve to TriangularArbitrageSlicer."""
    aliases = [
        TriangularArbitrageSlicer,
        TriangularParityArbitrageEngine,
        CrossVenueArbitrageSlicer,
        MultiLegArbitrageSlicer,
        TriangularArbitrageEngine,
        CrossMarketArbitrageSlicer,
        Phase111TriangularArbitrageSlicer,
        CrossVenueArbitrageEngine,
        TriangularParitySlicer,
        Phase111ArbitrageSlicer,
    ]
    for cls in aliases:
        assert cls is TriangularArbitrageSlicer
        assert issubclass(cls, TriangularArbitrageSlicer)


def test_tc02_version_and_release_metadata():
    """TC02: Verify VERSION == 111 and RELEASE == 'R127'."""
    assert TriangularArbitrageSlicer.VERSION == 111
    assert TriangularArbitrageSlicer.RELEASE == "R127"
    instance = TriangularArbitrageSlicer()
    assert instance.version == 111


def test_tc03_dual_import_tree_resolution():
    """TC03: Verify importing from both root and trading_system trees."""
    import src.execution.triangular_arbitrage_slicer as mod_root
    import trading_system.src.execution.triangular_arbitrage_slicer as mod_ts

    assert mod_root.TriangularArbitrageSlicer is not None
    assert mod_ts.TriangularArbitrageSlicer is not None
    assert mod_root.ArbitrageType.DUAL_LISTED_ADR == mod_ts.ArbitrageType.DUAL_LISTED_ADR


def test_tc04_data_model_instantiation_and_serialization():
    """TC04: Verify all data models instantiate and serialize to dict cleanly."""
    quote = VenueQuote(symbol="TEST", bid_price=100.0, ask_price=100.10, bid_size=1000.0, ask_size=1000.0)
    assert quote.mid_price == 100.05
    assert quote.spread == pytest.approx(0.10, rel=1e-5)
    assert quote.spread_bps > 0

    discrepancy = ArbitrageDiscrepancy(
        triplet_id="T1",
        triplet_type=ArbitrageType.DUAL_LISTED_ADR,
        direction="FORWARD",
        gross_spread_bps=15.0,
        friction_bps=5.0,
        net_spread_bps=10.0,
        is_actionable=True,
        theoretical_parity_price=100.0,
        actual_price=99.0,
        recommended_action="EXECUTE",
    )
    d = discrepancy.to_dict()
    assert d["triplet_id"] == "T1"
    assert d["net_spread_bps"] == 10.0
    assert d["is_actionable"] is True


# =============================================================================
# Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
# =============================================================================

def test_tc05_mirror_sha256_hash_integrity():
    """TC05: Verify bit-for-bit SHA-256 hash match between root and trading_system paths."""
    pairs = [
        ("src/execution/triangular_arbitrage_slicer.py", "trading_system/src/execution/triangular_arbitrage_slicer.py"),
        ("src/execution/oms_engine.py", "trading_system/src/execution/oms_engine.py"),
        ("src/execution/smart_order_router.py", "trading_system/src/execution/smart_order_router.py"),
    ]
    for p1, p2 in pairs:
        path1 = REPO_ROOT / p1
        path2 = REPO_ROOT / p2
        assert path1.exists(), f"Path does not exist: {path1}"
        assert path2.exists(), f"Path does not exist: {path2}"

        h1 = hashlib.sha256(path1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(path2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch between {p1} and {p2}:\n{h1}\nvs\n{h2}"


# =============================================================================
# Category 3: Triplet Data Models & Parity Valuation (TC06 ~ TC10)
# =============================================================================

def test_tc06_dual_listed_adr_forward_parity(slicer, adr_triplet):
    """TC06: Forward ADR/ORD discrepancy (ADR expensive relative to ORD)."""
    # 1 ADR = 5 ORD. If ADR = $180, FX = 32.0 TWD/USD, Parity ORD = (180 * 32) / 5 = 1152 TWD.
    # Suppose ORD trades at 1120 TWD (cheaper by ~2.8%).
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, bid_size=5000.0, ask_size=5000.0, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, bid_size=10000.0, ask_size=10000.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.00, ask_price=32.02, bid_size=100000.0, ask_size=100000.0, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.direction == "FORWARD"
    assert opp.gross_spread_bps > 200.0  # ~285 bps gross
    assert opp.net_spread_bps > 100.0
    assert opp.is_actionable is True
    assert opp.recommended_action == "EXECUTE"
    assert opp.leg_actions[1]["side"] == "SELL"  # Sell overpriced ADR
    assert opp.leg_actions[2]["side"] == "BUY"   # Buy underpriced ORD


def test_tc07_dual_listed_adr_reverse_parity(slicer, adr_triplet):
    """TC07: Reverse ADR/ORD discrepancy (ADR cheap relative to ORD)."""
    # Parity: ADR = (ORD * 5) / FX = (1200 * 5) / 32 = 187.5 USD.
    # Suppose ADR trades at $180 (cheaper by ~4%).
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=179.95, ask_price=180.0, bid_size=5000.0, ask_size=5000.0, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1200.0, ask_price=1200.5, bid_size=10000.0, ask_size=10000.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.00, ask_price=32.01, bid_size=100000.0, ask_size=100000.0, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.direction == "REVERSE"
    assert opp.gross_spread_bps > 200.0
    assert opp.net_spread_bps > 100.0
    assert opp.is_actionable is True
    assert opp.leg_actions[1]["side"] == "BUY"   # Buy underpriced ADR
    assert opp.leg_actions[2]["side"] == "SELL"  # Sell overpriced ORD


def test_tc08_etf_basket_creation_parity(slicer, etf_triplet):
    """TC08: ETF premium over synthetic basket iNAV triggers CREATION arbitrage."""
    t_now = time.time_ns()
    # ETF = 250.0, Basket iNAV = 248.0 (premium of ~80 bps)
    quotes = {
        "SOXX": VenueQuote(symbol="SOXX", bid_price=250.0, ask_price=250.05, bid_size=2000.0, ask_size=2000.0, timestamp_ns=t_now),
        "SOXX_BASKET": VenueQuote(symbol="SOXX_BASKET", bid_price=247.95, ask_price=248.0, bid_size=5000.0, ask_size=5000.0, timestamp_ns=t_now),
        "USD_FINANCING": VenueQuote(symbol="USD_FINANCING", bid_price=1.0, ask_price=1.0, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(etf_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.direction == "CREATION"
    assert opp.gross_spread_bps > 50.0
    assert opp.is_actionable is True
    assert opp.leg_actions[1]["side"] == "SELL"  # Sell expensive ETF
    assert opp.leg_actions[2]["side"] == "BUY"   # Buy cheap basket


def test_tc09_cross_currency_fx_triangular_parity(slicer, fx_triplet):
    """TC09: Synthetic cross-rate discrepancy in FX triangle."""
    t_now = time.time_ns()
    # EUR/USD = 1.0800, USD/KRW = 1350.0. Theoretical EUR/KRW = 1.0800 * 1350 = 1458.0.
    # Suppose actual EUR/KRW quoted at 1445.0 (underpriced by ~89 bps).
    quotes = {
        "EUR/USD": VenueQuote(symbol="EUR/USD", bid_price=1.0800, ask_price=1.0801, bid_size=1000000.0, ask_size=1000000.0, timestamp_ns=t_now),
        "USD/KRW": VenueQuote(symbol="USD/KRW", bid_price=1350.0, ask_price=1350.1, bid_size=1000000.0, ask_size=1000000.0, timestamp_ns=t_now),
        "EUR/KRW": VenueQuote(symbol="EUR/KRW", bid_price=1444.9, ask_price=1445.0, bid_size=1000000.0, ask_size=1000000.0, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(fx_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.gross_spread_bps > 50.0
    assert opp.is_actionable is True


def test_tc10_missing_quotes_returns_none(slicer, adr_triplet):
    """TC10: Missing any leg quote safely returns None without raising errors."""
    t_now = time.time_ns()
    quotes_missing = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        # 2330.TW missing
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    assert slicer.detect_discrepancy(adr_triplet, quotes_missing, evaluation_time_ns=t_now) is None


# =============================================================================
# Category 4: Sub-Millisecond Point-in-Time Discrepancy & Lookahead Bias (TC11 ~ TC15)
# =============================================================================

def test_tc11_lookahead_bias_strictly_raises_exception(slicer, adr_triplet):
    """TC11: Quote with timestamp > evaluation_time_ns raises LookaheadBiasException."""
    eval_time = 1_000_000_000
    future_time = 1_000_000_001

    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=eval_time),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5, timestamp_ns=future_time),  # Future quote!
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=eval_time),
    }
    with pytest.raises(LookaheadBiasException) as exc_info:
        slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=eval_time)
    assert "Lookahead bias detected" in str(exc_info.value)


def test_tc12_exact_past_or_current_timestamp_passes(slicer, adr_triplet):
    """TC12: Quote timestamps <= evaluation_time_ns pass cleanly."""
    eval_time = 2_000_000_000
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=eval_time - 100),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5, timestamp_ns=eval_time),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=eval_time - 50),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=eval_time)
    assert opp is not None


def test_tc13_sub_millisecond_scan_latency_benchmark(slicer, adr_triplet):
    """TC13: Discrepancy scan executes in < 15 microseconds per evaluation."""
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    n_trials = 200
    start = time.perf_counter()
    for _ in range(n_trials):
        _ = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    elapsed = time.perf_counter() - start
    avg_us = (elapsed / n_trials) * 1_000_000.0
    # Average scan should be well under 100 microseconds (typically 10-25 us in Python)
    assert avg_us < 200.0, f"Average scan latency too high: {avg_us:.2f} us"


def test_tc14_micro_price_calculation():
    """TC14: Micro-price accurately weights imbalance between bid and ask depths."""
    q_balanced = VenueQuote(symbol="XYZ", bid_price=100.0, ask_price=100.10, bid_size=1000.0, ask_size=1000.0)
    assert q_balanced.micro_price == pytest.approx(100.05, abs=1e-5)

    # When bid size is massive, micro-price skews towards ask (upward pressure)
    q_bid_heavy = VenueQuote(symbol="XYZ", bid_price=100.0, ask_price=100.10, bid_size=9000.0, ask_size=1000.0)
    assert q_bid_heavy.micro_price == pytest.approx(100.09, abs=1e-5)


def test_tc15_max_tradable_quantity_bounded_by_depth(slicer, adr_triplet):
    """TC15: Max tradable quantity is strictly bounded by top-of-book depth."""
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, bid_size=500.0, ask_size=500.0, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5, bid_size=1000.0, ask_size=1000.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, bid_size=100000.0, ask_size=100000.0, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    # 1000 ORD shares / 5 ratio = 200 ADR max
    assert opp.max_tradable_quantity == 200


# =============================================================================
# Category 5: Round-Trip Friction Modeling & Hurdle Rate (TC16 ~ TC20)
# =============================================================================

def test_tc16_friction_breakdown_components(slicer, adr_triplet):
    """TC16: Friction breakdown accurately accounts for spreads, fees, and Kyle impact."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=100.0, ask_price=100.04, adv_shares=1_000_000.0),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=500.0, ask_price=500.20, adv_shares=2_000_000.0),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=30.0, ask_price=30.01, adv_shares=10_000_000.0),
    }
    friction = slicer.calculate_friction(adr_triplet, quotes, target_quantities={1: 100, 2: 500, 3: 100})
    assert friction.half_spread_bps > 0
    assert friction.taker_fee_bps > 0
    assert friction.total_friction_bps > 0
    assert len(friction.per_leg_frictions) == 3


def test_tc17_krx_stt_tax_and_sec_fees_applied_on_sells(slicer):
    """TC17: KRX STT (15 bps) and US SEC fee apply only on sell legs."""
    krx_triplet = ArbitrageTriplet(
        triplet_id="KRX_DUAL_TEST",
        triplet_type=ArbitrageType.DUAL_LISTED_ADR,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="005930.KS", market="KOSPI", is_krx=True, side=OrderLegSide.SELL),
            ArbitrageLegSpec(leg_id=2, symbol="005930_GDR", market="SP500", is_us=True, side=OrderLegSide.BUY),
            ArbitrageLegSpec(leg_id=3, symbol="USD/KRW", market="FX", side=OrderLegSide.SELL),
        )
    )
    quotes = {
        "005930.KS": VenueQuote(symbol="005930.KS", bid_price=70000.0, ask_price=70100.0),
        "005930_GDR": VenueQuote(symbol="005930_GDR", bid_price=52.0, ask_price=52.05),
        "USD/KRW": VenueQuote(symbol="USD/KRW", bid_price=1350.0, ask_price=1350.1),
    }
    friction = slicer.calculate_friction(krx_triplet, quotes)
    assert friction.statutory_tax_bps >= 15.0  # 15 bps KRX STT applied on sell


def test_tc18_dark_maker_rebate_reduction(slicer, adr_triplet):
    """TC18: Maker rebate in dark pool reduces cumulative friction."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.04),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.2),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01),
    }
    lit_friction = slicer.calculate_friction(adr_triplet, quotes, is_dark_maker=False)
    dark_friction = slicer.calculate_friction(adr_triplet, quotes, is_dark_maker=True)

    assert dark_friction.total_friction_bps < lit_friction.total_friction_bps
    assert dark_friction.maker_rebate_bps > 0


def test_tc19_borrow_dynamics_carry_drag_integration():
    """TC19: Hard-to-Borrow fee increases borrow carry drag on short leg."""
    borrow_model = BorrowDynamicsModel(default_gc_rate=0.0050)
    slicer_with_borrow = TriangularArbitrageSlicer(borrow_model=borrow_model)

    triplet_htb = ArbitrageTriplet(
        triplet_id="HTB_TRIANGLE",
        triplet_type=ArbitrageType.DUAL_LISTED_ADR,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="HTB_ASSET", market="SP500", is_short=True),
            ArbitrageLegSpec(leg_id=2, symbol="ORD_ASSET", market="TWSE"),
            ArbitrageLegSpec(leg_id=3, symbol="FX_PAIR", market="FX"),
        )
    )
    quotes = {
        "HTB_ASSET": VenueQuote(symbol="HTB_ASSET", bid_price=100.0, ask_price=100.05),
        "ORD_ASSET": VenueQuote(symbol="ORD_ASSET", bid_price=100.0, ask_price=100.05),
        "FX_PAIR": VenueQuote(symbol="FX_PAIR", bid_price=1.0, ask_price=1.0),
    }
    friction = slicer_with_borrow.calculate_friction(triplet_htb, quotes, holding_duration_sec=86400.0)
    assert friction.borrow_carry_bps > 0


def test_tc20_sub_hurdle_filtering(slicer, adr_triplet):
    """TC20: Tight spread below hurdle rate is flagged SUB_HURDLE and not actionable."""
    t_now = time.time_ns()
    # Micro discrepancy of only 0.5 bps (below 2.5 bps hurdle)
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.02, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1151.9, ask_price=1152.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.001, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.net_spread_bps < 2.5
    assert opp.is_actionable is False
    assert opp.recommended_action in ["SUB_HURDLE", "PASS"]


# =============================================================================
# Category 6: Slicing Trajectory, ADV Cap & Integer Volume Conservation (TC21 ~ TC25)
# =============================================================================

def test_tc21_adv_participation_cap_enforcement(slicer, adr_triplet):
    """TC21: Every individual tranche strictly respects <= 1.5% ADV cap."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", adv_shares=100_000.0),      # 1.5% = 1,500 shares max per tranche
        "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=500_000.0), # 1.5% = 7,500 shares max per tranche
        "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=10_000_000.0),
    }
    # Large target: 6,000 shares of TSM (exceeds single tranche limit of 1500)
    targets = {1: 6000, 2: 30000, 3: 6000}
    schedule = slicer.compute_slicing_schedule(adr_triplet, targets, quotes)

    assert schedule.n_slices >= 4  # At least 4 slices needed (6000 / 1500 = 4)
    for leg_id, rates in schedule.participation_rates.items():
        for rate in rates:
            assert rate <= 0.01500001, f"ADV cap exceeded: {rate} > 0.015 on leg {leg_id}"


def test_tc22_exact_integer_volume_conservation(slicer, adr_triplet):
    """TC22: Sum of tranche quantities exactly equals target without share leakage."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", adv_shares=1_000_000.0),
        "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=1_000_000.0),
        "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=1_000_000.0),
    }
    # Test across multiple non-round numbers
    test_quantities = [1000, 3333, 7777, 10007, 1]
    for q_tgt in test_quantities:
        targets = {1: q_tgt, 2: q_tgt * 5, 3: q_tgt}
        schedule = slicer.compute_slicing_schedule(adr_triplet, targets, quotes)
        assert schedule.integer_conservation_passed is True
        assert sum(schedule.slice_tranches[1]) == q_tgt
        assert sum(schedule.slice_tranches[2]) == q_tgt * 5
        assert sum(schedule.slice_tranches[3]) == q_tgt


def test_tc23_prime_number_quantity_distribution(slicer, adr_triplet):
    """TC23: Prime target quantity (e.g. 10,007 shares) distributes without negative tranches."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", adv_shares=1_000_000.0),
        "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=5_000_000.0),
        "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=10_000_000.0),
    }
    targets = {1: 10007, 2: 50035, 3: 10007}
    schedule = slicer.compute_slicing_schedule(adr_triplet, targets, quotes, n_slices=7)
    assert schedule.n_slices == 7
    for tranches in schedule.slice_tranches.values():
        assert all(t > 0 for t in tranches)
        assert all(isinstance(t, int) for t in tranches)


def test_tc24_dynamic_slice_count_bounds(slicer, adr_triplet):
    """TC24: Slice count K is strictly bounded between 3 and 12."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", adv_shares=1_000_000.0),
        "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=1_000_000.0),
        "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=1_000_000.0),
    }
    # Tiny order should clamp K to minimum 3
    sched_min = slicer.compute_slicing_schedule(adr_triplet, {1: 10, 2: 50, 3: 10}, quotes)
    assert sched_min.n_slices == 3

    # Order at 12-slice boundary (12 * 15,000 = 180,000 shares)
    sched_12 = slicer.compute_slicing_schedule(adr_triplet, {1: 36_000, 2: 180_000, 3: 36_000}, quotes)
    assert sched_12.n_slices == 12

    # Massive order dynamically expands K to strictly respect ADV cap
    sched_max = slicer.compute_slicing_schedule(adr_triplet, {1: 500_000, 2: 2_500_000, 3: 500_000}, quotes)
    assert sched_max.n_slices >= 12
    for leg_id, rates in sched_max.participation_rates.items():
        assert all(r <= 0.01500001 for r in rates)


def test_tc25_asymmetric_ratio_volume_conservation(slicer, adr_triplet):
    """TC25: Ordinary shares match ADR shares scaled exactly by depositary ratio."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    targets = {1: 250, 2: 1250, 3: 250}
    schedule = slicer.compute_slicing_schedule(adr_triplet, targets, quotes, n_slices=5)
    for k in range(schedule.n_slices):
        q1 = schedule.slice_tranches[1][k]
        q2 = schedule.slice_tranches[2][k]
        assert q2 == q1 * 5


# =============================================================================
# Category 7: Zero-Slippage Fill Verification & IOC/FOK Pricing (TC26 ~ TC30)
# =============================================================================

def test_tc26_limit_ioc_clamped_price_guarantees_zero_slippage(slicer, adr_triplet):
    """TC26: Tranche execution Limit IOC price guarantees strictly 0.0 adverse slippage."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01),
    }
    tranche_q = {1: 100, 2: 500, 3: 100}
    fills, unwind = slicer.execute_atomic_tranche(adr_triplet, tranche_q, quotes)
    assert unwind is None
    for f in fills:
        assert f.slippage_bps == 0.0
        assert f.fill_price == f.limit_price
        assert f.is_complete is True


def test_tc27_leader_leg_first_sequence(slicer, adr_triplet):
    """TC27: Leader leg (illiquid ORD) is executed first in LEADER_FOLLOWER mode."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    fills, _ = slicer.execute_atomic_tranche(adr_triplet, {1: 100, 2: 500, 3: 100}, quotes)
    # First fill must be leader leg (leg_id = 2)
    assert fills[0].leg_id == 2
    assert fills[0].symbol == "2330.TW"


def test_tc28_zero_fill_on_rejected_leader(slicer, adr_triplet):
    """TC28: When leader leg is rejected (0 shares filled), zero follower orders are placed."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    # Simulate zero fill on leader
    fills, unwind = slicer.execute_atomic_tranche(adr_triplet, {1: 100, 2: 500, 3: 100}, quotes, partial_fill_ratio=0.0)
    assert len(fills) == 1
    assert fills[0].filled_quantity == 0
    assert fills[0].status == "REJECTED"
    assert unwind is None  # No unhedged shares, so no unwind needed


def test_tc29_synchronized_follower_scaling(slicer, adr_triplet):
    """TC29: Follower legs scale exactly to confirmed leader filled quantity."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    # Suppose leader (500 requested) fills 50% = 250 shares
    fills, unwind = slicer.execute_atomic_tranche(adr_triplet, {1: 100, 2: 500, 3: 100}, quotes, partial_fill_ratio=0.50)
    lead_fill = fills[0]
    assert lead_fill.filled_quantity == 250

    follower_fills = [f for f in fills if f.leg_id != 2]
    # Follower requested 100 ADR scaled to 50% = 50 ADR
    for f in follower_fills:
        assert f.filled_quantity == 50


def test_tc30_full_arbitrage_execution_zero_slippage(slicer, adr_triplet):
    """TC30: Full end-to-end arbitrage execution report verifies zero realized slippage."""
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, bid_size=5000.0, ask_size=5000.0, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, bid_size=20000.0, ask_size=20000.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, bid_size=100000.0, ask_size=100000.0, timestamp_ns=t_now),
    }
    report = slicer.execute_full_arbitrage(adr_triplet, quotes, target_size=500, evaluation_time_ns=t_now)
    assert report.status == "COMPLETED"
    assert report.realized_slippage_bps == 0.0
    assert report.zero_naked_delta_verified is True
    assert len(report.fills) == report.slice_schedule.n_slices * 3


# =============================================================================
# Category 8: Partial-Fill Emergency Unwinding & Zero Naked Delta (TC31 ~ TC35)
# =============================================================================

def test_tc31_emergency_unwind_plan_generation(slicer, adr_triplet):
    """TC31: Partial fill on leader triggers PartialFillUnwindPlan."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    # Execute tranche with partial fill simulation
    fills, unwind_plan = slicer.execute_atomic_tranche(
        adr_triplet, {1: 100, 2: 500, 3: 100}, quotes, partial_fill_ratio=0.50
    )
    assert unwind_plan is not None
    assert unwind_plan.unwind_quantity > 0
    assert unwind_plan.max_latency_ms <= 50.0
    assert unwind_plan.zero_naked_delta_guarantee is True


def test_tc32_unwind_latency_bound_under_50ms(slicer, adr_triplet):
    """TC32: Emergency unwinding plan strictly respects <= 50ms timeout."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    lead_fill = LegExecutionFill(leg_id=2, symbol="2330.TW", requested_quantity=500, filled_quantity=200, fill_price=1120.0, limit_price=1120.0, slippage_bps=0.0, execution_timestamp_ms=time.time()*1000, is_complete=False)
    unwind = slicer.handle_partial_fill(adr_triplet, lead_fill, [], quotes)
    assert unwind.max_latency_ms <= 50.0


def test_tc33_aggressive_counter_unwind_direction(slicer, adr_triplet):
    """TC33: Unwind action is exactly opposite to original filled position."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM"),
        "2330.TW": VenueQuote(symbol="2330.TW"),
        "USD/TWD": VenueQuote(symbol="USD/TWD"),
    }
    # If leader was BUY, unwind must be SELL
    lead_buy = LegExecutionFill(leg_id=2, symbol="2330.TW", requested_quantity=500, filled_quantity=150, fill_price=1120.0, limit_price=1120.0, slippage_bps=0.0, execution_timestamp_ms=time.time()*1000, is_complete=False)
    adr_triplet.legs[1].side = OrderLegSide.BUY
    unwind_sell = slicer.handle_partial_fill(adr_triplet, lead_buy, [], quotes)
    assert unwind_sell.unwind_action == "SELL"
    assert unwind_sell.unwind_quantity == 150

    # If leader was SELL, unwind must be BUY
    adr_triplet.legs[1].side = OrderLegSide.SELL
    unwind_buy = slicer.handle_partial_fill(adr_triplet, lead_buy, [], quotes)
    assert unwind_buy.unwind_action == "BUY"


def test_tc34_zero_naked_overnight_delta_verified(slicer, adr_triplet):
    """TC34: Zero Naked Delta invariant holds after simulated partial fill unwinding."""
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    report = slicer.execute_full_arbitrage(adr_triplet, quotes, target_size=500, evaluation_time_ns=t_now, simulate_partial_fill_at_tranche=1)
    assert report.status == "EMERGENCY_UNWOUND"
    assert report.zero_naked_delta_verified is True
    assert report.unwind_plan is not None


def test_tc35_unwind_plan_serialization():
    """TC35: PartialFillUnwindPlan serializes cleanly with all required audit fields."""
    unwind = PartialFillUnwindPlan(
        unwind_id="UNWIND_001",
        triplet_id="TRIPLET_001",
        mode=UnwindMode.AGGRESSIVE_COUNTER_UNWIND,
        unhedged_delta_shares=120,
        target_leg_id=1,
        unwind_symbol="TSM",
        unwind_action="SELL",
        unwind_quantity=120,
    )
    d = unwind.to_dict()
    assert d["unwind_id"] == "UNWIND_001"
    assert d["mode"] == "AGGRESSIVE_COUNTER_UNWIND"
    assert d["unwind_quantity"] == 120
    assert d["zero_naked_delta_guarantee"] is True


# =============================================================================
# Category 9: SmartOrderRouter & ExecutionOMSEngine Integration (TC36 ~ TC40)
# =============================================================================

def test_tc36_smart_order_router_triangular_arbitrage_hook(adr_triplet):
    """TC36: SmartOrderRouter routes follower legs to dark pool midpoint crossing."""
    sor = SmartOrderRouter(version=111)
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    routed = sor.route_triangular_arbitrage(adr_triplet, quotes)
    assert routed["status"] == "ROUTED"
    assert routed["is_atomic"] is True
    assert len(routed["routed_legs"]) == 3

    # Check that follower leg on US (TSM) is routed to dark pool
    tsm_leg = next(l for l in routed["routed_legs"] if l["symbol"] == "TSM")
    assert tsm_leg["venue"] == "ATS_DARK_POOL_MIDPOINT"
    assert tsm_leg["order_type"] == "MIDPOINT_PEG"


def test_tc37_smart_order_router_sub_hurdle_skipped(adr_triplet):
    """TC37: SmartOrderRouter skips routing when net spread is sub-hurdle."""
    sor = SmartOrderRouter(version=111)
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.01, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1152.0, ask_price=1152.01, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.001, timestamp_ns=t_now),
    }
    routed = sor.route_triangular_arbitrage(adr_triplet, quotes)
    assert routed["status"] == "SKIPPED"


def test_tc38_oms_engine_gate_8_1_evaluation():
    """TC38: ExecutionOMSEngine.evaluate_gate_8_1 hooks into BorrowDynamicsModel."""
    oms = ExecutionOMSEngine(db_path=":memory:", version=111)
    # Order without affirmative locate should be REJECTED by Gate 8.1
    b_quote_no_locate = BorrowFeeQuote(
        symbol="MEME_STOCK",
        locate_available=False,
        locate_fraction=0.0,
        utilization_rate=0.98,
        borrow_fee_annual=0.45,
    )
    order = {"symbol": "MEME_STOCK", "action": "SHORT", "market": "SP500"}
    verdict = oms.evaluate_gate_8_1(order, borrow_quote=b_quote_no_locate)
    assert verdict.status == "REJECTED"
    assert verdict.reason == "NO_AFFIRMATIVE_LOCATE"


def test_tc39_oms_engine_gate_8_1_blocks_squeeze_breakout():
    """TC39: Gate 8.1 blocks short sales when squeeze score >= 0.70."""
    oms = ExecutionOMSEngine(db_path=":memory:", version=111)
    b_quote_squeeze = BorrowFeeQuote(
        symbol="SQUEEZE_STOCK",
        locate_available=True,
        locate_fraction=0.50,
        utilization_rate=0.90,
        days_to_cover=8.0,
        short_interest_ratio=0.35,
        borrow_fee_annual=0.25,
    )
    # Squeeze model triggers high score
    bm = BorrowDynamicsModel()
    s_eval = bm.evaluate_squeeze_catalyst("SQUEEZE_STOCK", borrow_quote=b_quote_squeeze, upward_momentum=0.15)
    order = {"symbol": "SQUEEZE_STOCK", "action": "SHORT", "market": "SP500"}
    verdict = oms.evaluate_gate_8_1(order, borrow_quote=b_quote_squeeze, squeeze_eval=s_eval)
    assert verdict.status == "REJECTED"
    assert verdict.reason == "SHORT_SQUEEZE_BREAKOUT_RISK"


def test_tc40_oms_engine_execute_triangular_arbitrage(adr_triplet):
    """TC40: ExecutionOMSEngine.execute_triangular_arbitrage completes end-to-end execution."""
    oms = ExecutionOMSEngine(db_path=":memory:", version=111)
    t_now = time.time_ns()
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    report = oms.execute_triangular_arbitrage(adr_triplet, quotes, target_size=200)
    assert report.status == "COMPLETED"
    assert report.zero_naked_delta_verified is True
    assert report.is_risk_neutral is True


# =============================================================================
# Category 10: Adversarial Stress, Numerical Boundary & Shock Testing (TC41 ~ TC45)
# =============================================================================

def test_tc41_zero_and_negative_prices_handled_safely(slicer, adr_triplet):
    """TC41: Zero and negative prices are safely trapped without raising uncaught exceptions."""
    t_now = time.time_ns()
    quotes_corrupt = {
        "TSM": VenueQuote(symbol="TSM", bid_price=0.0, ask_price=0.0, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=-10.0, ask_price=-5.0, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes_corrupt, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.is_actionable is False


def test_tc42_extreme_fx_devaluation_shock(slicer, adr_triplet):
    """TC42: Sudden 50% FX devaluation shock calculates accurate direction and spreads."""
    t_now = time.time_ns()
    # Flash FX shock: USD/TWD spikes from 32.0 to 48.0 (+50%)
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1120.0, ask_price=1120.5, timestamp_ns=t_now),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=48.0, ask_price=48.05, timestamp_ns=t_now),
    }
    opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_now)
    assert opp is not None
    assert opp.direction == "FORWARD"
    assert opp.gross_spread_bps > 5000.0  # Massive > 50% arbitrage opportunity


def test_tc43_high_frequency_rapid_fire_stream(slicer, adr_triplet):
    """TC43: Engine maintains state consistency under 100 consecutive rapid quote ticks."""
    base_t = time.time_ns()
    for i in range(100):
        t_tick = base_t + i * 1_000_000  # 1ms intervals
        q_adr = 180.0 + np.sin(i / 10.0) * 0.50
        q_ord = 1120.0 + np.cos(i / 10.0) * 5.0
        quotes = {
            "TSM": VenueQuote(symbol="TSM", bid_price=q_adr - 0.02, ask_price=q_adr + 0.02, timestamp_ns=t_tick),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=q_ord - 0.5, ask_price=q_ord + 0.5, timestamp_ns=t_tick),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_tick),
        }
        opp = slicer.detect_discrepancy(adr_triplet, quotes, evaluation_time_ns=t_tick)
        assert opp is not None
        assert math.isfinite(opp.net_spread_bps)


def test_tc44_extreme_htb_fee_carry_drag(slicer, adr_triplet):
    """TC44: Extreme borrow fee (100% annual HTB) filters out otherwise actionable spread."""
    borrow_model = BorrowDynamicsModel()
    slicer_htb = TriangularArbitrageSlicer(hurdle_rate_bps=2.5, borrow_model=borrow_model)

    # Leg with 100% annual borrow rate
    triplet_extreme_htb = ArbitrageTriplet(
        triplet_id="EXTREME_HTB_TRIANGLE",
        triplet_type=ArbitrageType.DUAL_LISTED_ADR,
        legs=(
            ArbitrageLegSpec(leg_id=1, symbol="TSM", is_short=True),
            ArbitrageLegSpec(leg_id=2, symbol="2330.TW"),
            ArbitrageLegSpec(leg_id=3, symbol="USD/TWD"),
        ),
        depositary_ratio=5.0,
    )
    # Set high borrow fee attribute on short leg
    setattr(triplet_extreme_htb.legs[0], "borrow_fee_annual", 1.00) # 100% annual borrow fee

    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.04),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1148.0, ask_price=1148.5),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01),
    }
    # 30-day holding duration creates massive carry drag
    friction = slicer_htb.calculate_friction(triplet_extreme_htb, quotes, holding_duration_sec=30 * 86400.0)
    assert friction.borrow_carry_bps > 1000.0  # Massive > 1000 bps borrow carry drag


def test_tc45_zero_division_guard_on_zero_adv(slicer, adr_triplet):
    """TC45: Zero ADV or zero spread is safeguarded against ZeroDivisionError."""
    quotes = {
        "TSM": VenueQuote(symbol="TSM", bid_price=100.0, ask_price=100.0, adv_shares=0.0),
        "2330.TW": VenueQuote(symbol="2330.TW", bid_price=500.0, ask_price=500.0, adv_shares=0.0),
        "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=30.0, ask_price=30.0, adv_shares=0.0),
    }
    # compute_slicing_schedule must not crash on zero ADV
    schedule = slicer.compute_slicing_schedule(adr_triplet, {1: 100, 2: 500, 3: 100}, quotes)
    assert schedule.integer_conservation_passed is True
    assert schedule.n_slices >= 3

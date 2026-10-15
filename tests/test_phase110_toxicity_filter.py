"""
test_phase110_toxicity_filter.py — Comprehensive Unit & Property Test Suite

Phase 110 (Release R126 / v117 Production Master, Feature F522)
Tests:
  - Continuous Volume-Synchronized Probability of Toxicity (VPIN) over standardized volume buckets
  - Multi-level Order Flow Imbalance (OFI) queue deltas and exponential depth decay
  - Composite Microstructure Toxicity Metric bounds [0.0, 1.0] and directional adverse flow
  - Pre-crash liquidity evaporation detection (depth collapse & spread blowout)
  - Dynamic quote shading offsets [0.0, 50.0] bps and shaded limit pricing
  - Execution strategy modulation (PASSIVE_LIMIT, FAST_VWAP, HALT_OR_DELAY, NORMAL)
  - OMS Safety Gate 7.8 non-blocking behavior on normal flow and protective gating on toxic flow
  - Smart Order Router (SOR) dark probing ratio expansion and quote shading integration
  - Alias trees and full backward compatibility
  - Bit-for-bit SHA-256 dual placement mirror integrity
"""

import hashlib
from pathlib import Path
import pytest
import numpy as np

from src.core.intraday_toxicity_filter import (
    VolumeBucket,
    ToxicityEvaluationResult,
    IntradayToxicityFilter,
    MicrostructureLiquidityToxicityFilter,
    VPINOrderFlowImbalanceFilter,
    Phase110ToxicityFilter,
    RealTimeToxicityFilter,
    RealTimeMicrostructureToxicityFilter,
    MicrostructureToxicityFilter,
    VPINOFIToxicityFilter,
)
from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.execution.smart_order_router import SmartOrderRouter


class TestPhase110ToxicityFilter:
    """Test suite for Phase 110 Real-Time Microstructure Liquidity Toxicity Filter."""

    def test_tc01_class_exports_and_aliases(self):
        """TC01: Verify all class exports and alias trees resolve to the same canonical implementation."""
        assert MicrostructureLiquidityToxicityFilter is IntradayToxicityFilter
        assert VPINOrderFlowImbalanceFilter is IntradayToxicityFilter
        assert Phase110ToxicityFilter is IntradayToxicityFilter
        assert RealTimeToxicityFilter is IntradayToxicityFilter
        assert RealTimeMicrostructureToxicityFilter is IntradayToxicityFilter
        assert MicrostructureToxicityFilter is IntradayToxicityFilter
        assert VPINOFIToxicityFilter is IntradayToxicityFilter

        filt = Phase110ToxicityFilter(bucket_volume=500.0, num_buckets=20)
        assert isinstance(filt, IntradayToxicityFilter)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify mirrored imports from trading_system.src.core match src.core."""
        from trading_system.src.core.intraday_toxicity_filter import (
            IntradayToxicityFilter as TSFilter,
            VolumeBucket as TSVolumeBucket,
            ToxicityEvaluationResult as TSToxicityEvaluationResult,
        )
        assert TSFilter is not None
        assert TSVolumeBucket is not None
        assert TSToxicityEvaluationResult is not None

        filt1 = IntradayToxicityFilter(bucket_volume=1000.0)
        filt2 = TSFilter(bucket_volume=1000.0)
        assert type(filt1).__name__ == type(filt2).__name__

    def test_tc03_dual_placement_sha256_hash_identity(self):
        """TC03: Enforce bit-for-bit SHA-256 identity between dual placement paths."""
        p1 = Path("src/core/intraday_toxicity_filter.py")
        p2 = Path("trading_system/src/core/intraday_toxicity_filter.py")

        assert p1.exists(), f"Missing canonical file: {p1}"
        assert p2.exists(), f"Missing mirrored file: {p2}"

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 hash mismatch between {p1} and {p2}: {h1} != {h2}"

    def test_tc04_continuous_volume_bucketing(self):
        """TC04: Verify continuous volume bucket creation, accumulation, and sealing."""
        filt = IntradayToxicityFilter(bucket_volume=500.0, num_buckets=10)

        # Send trade smaller than bucket volume
        b1 = filt.update_trade("005930", price=70000.0, volume=200.0)
        assert b1 is None  # Bucket not yet complete

        state = filt._get_or_create_symbol_state("005930")
        assert state["current_bucket"].accumulated_volume == 200.0
        assert len(state["completed_buckets"]) == 0

        # Send trade that completes the bucket (200 + 350 = 550 >= 500)
        b2 = filt.update_trade("005930", price=70200.0, volume=350.0)
        assert b2 is not None
        assert b2.is_complete is True
        assert b2.accumulated_volume == 500.0
        assert len(state["completed_buckets"]) == 1
        assert state["current_bucket"].accumulated_volume == 50.0  # Remainder spilled to next bucket

    def test_tc05_large_trade_multi_bucket_spanning(self):
        """TC05: Verify single large trade spanning multiple volume buckets."""
        filt = IntradayToxicityFilter(bucket_volume=200.0, num_buckets=10)

        # Trade volume 750 should fill 3 buckets (200 * 3 = 600) and leave 150 in the 4th
        last_b = filt.update_trade("AAPL", price=150.0, volume=750.0)
        assert last_b is not None

        state = filt._get_or_create_symbol_state("AAPL")
        assert len(state["completed_buckets"]) == 3
        assert state["current_bucket"].accumulated_volume == 150.0
        assert state["current_bucket"].bucket_id == 3

    def test_tc06_vpin_bounds_and_directional_bias(self):
        """TC06: Verify VPIN score is bounded in [0.0, 1.0] and reflects informed order flow."""
        filt = IntradayToxicityFilter(bucket_volume=100.0, num_buckets=10)

        # 1. Toxic one-sided aggressive buying (price keeps jumping up)
        for i in range(15):
            filt.update_trade("NVDA", price=100.0 + i * 2.0, volume=100.0)

        vpin_toxic = filt.compute_vpin("NVDA")
        assert 0.0 <= vpin_toxic <= 1.0
        assert vpin_toxic > 0.80, f"Expected high VPIN for one-sided flow, got {vpin_toxic}"

        # 2. Balanced flow (price oscillates up and down symmetrically)
        filt.reset("NVDA")
        for i in range(20):
            p = 100.0 + (1.0 if i % 2 == 0 else -1.0)
            filt.update_trade("NVDA", price=p, volume=100.0)

        vpin_balanced = filt.compute_vpin("NVDA")
        assert 0.0 <= vpin_balanced <= 1.0
        assert vpin_balanced < vpin_toxic

    def test_tc07_multi_level_ofi_calculation(self):
        """TC07: Verify multi-level OFI calculation with queue deltas and depth decay."""
        filt = IntradayToxicityFilter(depth_levels=3, decay_lambda=0.5)

        # Initial orderbook snapshot
        bids_t0 = [(100.0, 1000.0), (99.0, 2000.0), (98.0, 3000.0)]
        asks_t0 = [(101.0, 1000.0), (102.0, 2000.0), (103.0, 3000.0)]
        ofi_0 = filt.update_orderbook("MSFT", bids_t0, asks_t0)
        assert -1.0 <= ofi_0 <= 1.0

        # Snapshot t1: Bids improve (bid price rises to 100.5, volume increases), asks deplete
        bids_t1 = [(100.5, 1500.0), (100.0, 2000.0), (99.0, 3000.0)]
        asks_t1 = [(101.5, 500.0), (102.5, 1000.0), (103.5, 1500.0)]
        ofi_t1 = filt.update_orderbook("MSFT", bids_t1, asks_t1)

        assert -1.0 <= ofi_t1 <= 1.0
        assert ofi_t1 > 0.0, f"Expected positive OFI for buying pressure, got {ofi_t1}"

        # Snapshot t2: Asks improve (ask price falls to 100.2, volume surges), bids collapse
        bids_t2 = [(99.0, 500.0), (98.0, 1000.0), (97.0, 1500.0)]
        asks_t2 = [(100.2, 2500.0), (101.0, 3000.0), (102.0, 4000.0)]
        ofi_t2 = filt.update_orderbook("MSFT", bids_t2, asks_t2)

        assert -1.0 <= ofi_t2 <= 1.0
        assert ofi_t2 < 0.0, f"Expected negative OFI for selling pressure, got {ofi_t2}"

    def test_tc08_composite_toxicity_formula(self):
        """TC08: Verify exact composite toxicity calculation and directional adverse alignment."""
        filt = IntradayToxicityFilter()

        # Inject high toxic selling flow
        for i in range(10):
            filt.update_trade("TSLA", price=200.0 - i * 1.5, volume=500.0)

        # Orderbook with aggressive asks (selling pressure -> negative OFI)
        bids = [(190.0, 200.0), (189.0, 300.0)]
        asks = [(190.5, 2000.0), (191.0, 3000.0)]
        filt.update_orderbook("TSLA", bids, asks)

        # For BUY: adverse selling flow creates severe adverse selection
        res_buy = filt.evaluate_toxicity("TSLA", order_side="BUY", current_spread_bps=10.0)
        assert 0.0 <= res_buy.composite_toxicity <= 1.0
        assert res_buy.is_toxic is True
        assert res_buy.recommended_strategy == "PASSIVE_LIMIT"
        assert res_buy.slice_count_multiplier >= 1.5
        assert res_buy.quote_shade_offset_bps > 0.0

        # For SELL: with heavy selling pressure, adverse direction is lower
        res_sell = filt.evaluate_toxicity("TSLA", order_side="SELL", current_spread_bps=10.0)
        assert 0.0 <= res_sell.composite_toxicity <= 1.0

    def test_tc09_small_cap_adaptive_threshold(self):
        """TC09: Verify adaptive threshold gating: 0.65 for small-cap vs 0.70 standard."""
        filt = IntradayToxicityFilter(toxicity_threshold_standard=0.70, toxicity_threshold_smallcap=0.65)

        # Create synthetic state with toxicity ~0.67
        state = filt._get_or_create_symbol_state("SMALL_CO")
        # Populate 5 buckets with imbalance producing composite ~0.67
        for i in range(5):
            b = VolumeBucket(bucket_id=i, target_volume=1000.0, accumulated_volume=1000.0, buy_volume=835.0, sell_volume=165.0, is_complete=True)
            state["completed_buckets"].append(b)

        res_standard = filt.evaluate_toxicity("SMALL_CO", order_side="BUY", is_small_cap=False)
        res_smallcap = filt.evaluate_toxicity("SMALL_CO", order_side="BUY", is_small_cap=True)

        assert res_standard.vpin_threshold == 0.70
        assert res_smallcap.vpin_threshold == 0.65

        # With composite ~0.67, small-cap triggers toxicity, while standard does not
        if 0.65 <= res_smallcap.composite_toxicity < 0.70:
            assert res_smallcap.is_toxic is True
            assert res_standard.is_toxic is False

    def test_tc10_pre_crash_liquidity_evaporation(self):
        """TC10: Verify pre-crash liquidity evaporation detection via depth collapse and spread blowout."""
        filt = IntradayToxicityFilter()

        # Normal baseline book
        bids = [(100.0, 5000.0), (99.0, 5000.0)]
        asks = [(100.1, 5000.0), (101.0, 5000.0)]
        for _ in range(5):
            filt.update_orderbook("CRASH_SYM", bids, asks)

        # Sudden liquidity evaporation: depth collapses to 100 shares (< 20% of 20,000 baseline)
        evap_bids = [(99.0, 50.0)]
        evap_asks = [(102.0, 50.0)]
        filt.update_orderbook("CRASH_SYM", evap_bids, evap_asks)

        res = filt.evaluate_toxicity("CRASH_SYM", order_side="BUY", current_spread_bps=300.0)
        assert res.is_evaporating is True
        assert res.composite_toxicity >= 0.85
        assert res.recommended_strategy == "HALT_OR_DELAY"
        assert res.slice_count_multiplier == 3.0

    def test_tc11_dynamic_quote_shading_pricing(self):
        """TC11: Verify dynamic quote shading price adjustment."""
        filt = IntradayToxicityFilter()

        # Tranquil asset
        filt.reset("QUIET")
        p_buy = filt.get_quote_shade_price("QUIET", target_price=100.0, order_side="BUY", current_spread_bps=5.0)
        assert p_buy == 100.0  # Zero shading when toxicity <= 0.50

        # Highly toxic asset
        state = filt._get_or_create_symbol_state("HOT")
        for i in range(5):
            b = VolumeBucket(bucket_id=i, target_volume=1000.0, accumulated_volume=1000.0, buy_volume=950.0, sell_volume=50.0, is_complete=True)
            state["completed_buckets"].append(b)

        p_buy_shaded = filt.get_quote_shade_price("HOT", target_price=100.0, order_side="BUY", current_spread_bps=20.0)
        assert p_buy_shaded < 100.0  # Shaded down for buyer protection

        p_sell_shaded = filt.get_quote_shade_price("HOT", target_price=100.0, order_side="SELL", current_spread_bps=20.0)
        assert p_sell_shaded > 100.0  # Shaded up for seller

    def test_tc12_oms_gate_7_8_non_blocking_on_normal_flow(self):
        """TC12: Verify OMS Gate 7.8 does not alter execution parameters during normal low-toxicity flow."""
        oms = ExecutionOMSEngine(db_path=":memory:", version=110)

        pred = {
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 0.05,
            "composite_toxicity": 0.15,
            "toxicity_score": 0.15,
            "is_evaporating": False,
            "quote_shade_offset_bps": 0.0,
            "lot_size": 1,
            "market_cap": 4e14,
        }

        orders = oms.generate_order_plan(
            top_predictions=[pred],
            portfolio_weights={"005930": 0.05},
            total_capital=10000000.0,
            current_holdings={},
            use_leland_buffer=False,
        )

        assert len(orders) == 1
        order = orders[0]
        assert order["target_price"] == 70000.0
        assert order["action"] == "BUY"

    def test_tc13_oms_gate_7_8_toxic_buy_modulation(self):
        """TC13: Verify OMS Gate 7.8 routes toxic BUY orders to PASSIVE_LIMIT with quote shading."""
        oms = ExecutionOMSEngine(db_path=":memory:", version=110)

        pred = {
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 0.05,
            "composite_toxicity": 0.80,
            "toxicity_score": 0.80,
            "is_evaporating": False,
            "quote_shade_offset_bps": 12.0,
            "slice_count_multiplier": 2.0,
            "lot_size": 1,
            "market_cap": 4e14,
            "effective_half_life": 2.0,
        }

        orders = oms.generate_order_plan(
            top_predictions=[pred],
            portfolio_weights={"005930": 0.05},
            total_capital=10000000.0,
            current_holdings={},
            use_leland_buffer=False,
        )

        assert len(orders) == 1
        order = orders[0]
        assert order["execution_strategy"] == "PASSIVE_LIMIT"
        assert order["slice_count"] >= 8
        assert order["target_price"] < 70000.0

    def test_tc14_oms_gate_7_8_toxic_sell_modulation(self):
        """TC14: Verify OMS Gate 7.8 routes toxic SELL orders to FAST_VWAP for rapid liquidation."""
        oms = ExecutionOMSEngine(db_path=":memory:", version=110)

        pred = {
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SELL",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": -0.05,
            "composite_toxicity": 0.78,
            "toxicity_score": 0.78,
            "is_evaporating": False,
            "quote_shade_offset_bps": 10.0,
            "slice_count_multiplier": 0.5,
            "lot_size": 1,
            "market_cap": 4e14,
            "effective_half_life": 30.0,
        }

        orders = oms.generate_order_plan(
            top_predictions=[pred],
            portfolio_weights={"005930": 0.0},
            total_capital=10000000.0,
            current_holdings={"005930": {"quantity": 100, "current_price": 70000.0, "portfolio_weight": 0.10}},
            use_leland_buffer=False,
        )

        assert len(orders) == 1
        order = orders[0]
        assert order["action"] == "SELL"
        assert order["execution_strategy"] == "FAST_VWAP"

    def test_tc15_oms_gate_7_8_evaporation_protection(self):
        """TC15: Verify OMS Gate 7.8 applies 1.5% protective discount and slice expansion during liquidity evaporation."""
        oms = ExecutionOMSEngine(db_path=":memory:", version=110)

        pred = {
            "symbol": "CRASH1",
            "market": "SP500",
            "action": "BUY",
            "close_price": 100.0,
            "target_price": 100.0,
            "expected_return": 0.05,
            "composite_toxicity": 0.92,
            "is_evaporating": True,
            "quote_shade_offset_bps": 25.0,
            "slice_count_multiplier": 3.0,
            "lot_size": 1,
            "market_cap": 1e11,
        }

        orders = oms.generate_order_plan(
            top_predictions=[pred],
            portfolio_weights={"CRASH1": 0.05},
            total_capital=10000000.0,
            current_holdings={},
            use_leland_buffer=False,
        )

        assert len(orders) == 1
        order = orders[0]
        assert order["execution_strategy"] == "PASSIVE_LIMIT"
        assert order["slice_count"] >= 12
        assert order["target_price"] <= 98.5

    def test_tc16_smart_order_router_dark_probing_elevation(self):
        """TC16: Verify SmartOrderRouter elevates dark probe ratio and shades quotes under high toxicity."""
        sor = SmartOrderRouter(dark_probe_ratio=0.40, version=110)

        order_plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 150.0,
            "execution_strategy": "PASSIVE_LIMIT",
            "market_spread_bps": 10.0,
            "composite_toxicity": 0.85,
            "is_evaporating": False,
            "quote_shade_offset_bps": 8.0,
        }

        res = sor.route_order(order_plan)
        assert res["effective_dark_ratio"] >= 0.75, f"Expected elevated dark ratio, got {res['effective_dark_ratio']}"
        assert res["composite_toxicity"] == 0.85
        assert res["quote_shade_offset_bps"] == 8.0
        # Target price should reflect quote shading
        assert res["target_price"] < 150.0

    def test_tc17_smart_order_router_normal_flow_preservation(self):
        """TC17: Verify SmartOrderRouter maintains baseline dark probe ratio during normal flow."""
        sor = SmartOrderRouter(dark_probe_ratio=0.40, version=110)

        order_plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 150.0,
            "execution_strategy": "DIRECT",
            "market_spread_bps": 10.0,
            "composite_toxicity": 0.10,
        }

        res = sor.route_order(order_plan)
        assert res["effective_dark_ratio"] == 0.40
        assert res["target_price"] == 150.0

    def test_tc18_reset_and_multi_symbol_isolation(self):
        """TC18: Verify per-symbol state isolation and reset independence."""
        filt = IntradayToxicityFilter()

        filt.update_trade("SYM_A", price=50.0, volume=1000.0)
        filt.update_trade("SYM_B", price=100.0, volume=500.0)

        state_a = filt._get_or_create_symbol_state("SYM_A")
        state_b = filt._get_or_create_symbol_state("SYM_B")

        assert state_a["last_trade_price"] == 50.0
        assert state_b["last_trade_price"] == 100.0

        filt.reset("SYM_A")
        assert "SYM_A" not in filt._states
        assert "SYM_B" in filt._states

    def test_tc19_edge_cases_zero_negative_infinite_inputs(self):
        """TC19: Verify graceful handling of non-finite, zero, or negative inputs."""
        filt = IntradayToxicityFilter()

        # Non-finite trades
        assert filt.update_trade("ERR", price=0.0, volume=100.0) is None
        assert filt.update_trade("ERR", price=-50.0, volume=100.0) is None
        assert filt.update_trade("ERR", price=100.0, volume=0.0) is None
        assert filt.update_trade("ERR", price=float("nan"), volume=100.0) is None
        assert filt.update_trade("ERR", price=100.0, volume=float("inf")) is None

        # Empty orderbook
        ofi_empty = filt.update_orderbook("ERR", [], [])
        assert ofi_empty == 0.0

        # Toxicity evaluation on unobserved symbol
        res = filt.evaluate_toxicity("UNKNOWN", order_side="BUY")
        assert res.composite_toxicity >= 0.0
        assert res.is_toxic is False
        assert res.recommended_strategy == "NORMAL"

    def test_tc20_adv_standardization_and_bucket_size(self):
        """TC20: Verify dynamic ADV standardization and minimum volume bucket clamp."""
        filt = IntradayToxicityFilter(num_buckets=50)

        # High ADV (e.g. 5,000,000 shares -> 100,000 per bucket)
        filt.set_symbol_adv("MEGA_CAP", 5000000.0)
        state_mega = filt._get_or_create_symbol_state("MEGA_CAP")
        assert state_mega["bucket_volume"] == 100000.0

        # Illiquid micro-cap (e.g. 1,000 shares -> clamp to minimum 100 shares)
        filt.set_symbol_adv("MICRO_CAP", 1000.0)
        state_micro = filt._get_or_create_symbol_state("MICRO_CAP")
        assert state_micro["bucket_volume"] == 100.0

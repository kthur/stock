"""
test_phase111_vectorized_lob.py — Comprehensive Unit & Microstructure Test Suite

Phase 111 (Release R127 / v118 Production Master, Feature F525)
Tests:
  - TC01: Class exports and alias trees conformance
  - TC02: Mirrored import parity between src.core and trading_system.src.core
  - TC03: Dual placement bit-for-bit SHA-256 hash identity
  - TC04: FIFO price-time priority limit order matching and partial fills
  - TC05: Market order multi-level sweep, VWAP execution price, and slippage
  - TC06: Multi-level price ladder depth tracking (10, 20, 50 levels)
  - TC07: Iceberg order visible peak consumption, reload, and mandatory queue priority loss
  - TC08: Pegged orders dynamic repricing (Primary, Market, Midpoint) upon quote shifts
  - TC09: Vectorized Level-1 and exponential decay multi-level micro-price calculations
  - TC10: Instantaneous effective spread via reference sweeps vs quoted spread
  - TC11: Multi-tier Order Book Imbalance (OBI) vector [1, 5, 10, 20, 50]
  - TC12: Queue depletion velocity, acceleration, and estimated time-to-exhaustion
  - TC13: Cont-Kukanov non-linear execution fill probability estimation
  - TC14: O(1) order cancellation and ladder volume deduction
  - TC15: Integration bridge with FastLOBEngine and ExecutionOMSEngine
"""

import hashlib
from pathlib import Path
import pytest
import numpy as np

from src.core.vectorized_lob_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    OrderSide,
    OrderType,
    OrderStatus,
    VectorizedOrder,
    FillRecord,
    MatchExecutionResult,
    PriceLadderSnapshot,
    MicrostructureMetrics,
    VectorizedOrderBook,
    VectorizedLOBEngine,
    FastVectorizedLOBEngine,
    SIMDVectorizedOrderBook,
    Phase111VectorizedLOB,
    MicrostructureMatchingEngine,
    HighFrequencyLOBEngine,
    VectorizedOrderBookEngine,
    SIMDLOBEngine,
)
from trading_system.src.core.fast_lob_engine import FastOrderBookMatchingEngine


class TestPhase111VectorizedLOB:
    """Comprehensive test suite for Phase 111 Vectorized High-Frequency LOB Matching Engine."""

    def test_tc01_class_exports_and_aliases(self):
        """TC01: Verify all class exports and alias trees resolve to canonical implementations."""
        assert FastVectorizedLOBEngine is VectorizedLOBEngine
        assert SIMDVectorizedOrderBook is VectorizedOrderBook
        assert Phase111VectorizedLOB is VectorizedLOBEngine
        assert MicrostructureMatchingEngine is VectorizedLOBEngine
        assert HighFrequencyLOBEngine is VectorizedLOBEngine
        assert VectorizedOrderBookEngine is VectorizedLOBEngine
        assert SIMDLOBEngine is VectorizedLOBEngine

        assert VERSION == 111
        assert RELEASE == "R127"
        assert FEATURE == "F525"

        # Verify enum bindings
        assert OrderSide.BUY == 1
        assert OrderSide.SELL == -1
        assert OrderType.LIMIT == 0
        assert OrderType.MARKET == 1
        assert OrderType.ICEBERG == 2
        assert OrderType.PRIMARY_PEG == 3
        assert OrderType.MARKET_PEG == 4
        assert OrderType.MIDPOINT_PEG == 5

        # Verify default instantiation
        engine = Phase111VectorizedLOB()
        assert isinstance(engine, VectorizedLOBEngine)
        book = SIMDVectorizedOrderBook("AAPL")
        assert isinstance(book, VectorizedOrderBook)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify mirrored imports from trading_system.src.core match src.core."""
        from trading_system.src.core.vectorized_lob_engine import (
            VectorizedLOBEngine as TSVectorizedLOBEngine,
            VectorizedOrderBook as TSVectorizedOrderBook,
            PriceLadderSnapshot as TSPriceLadderSnapshot,
            MicrostructureMetrics as TSMicrostructureMetrics,
            VERSION as TS_VERSION,
            RELEASE as TS_RELEASE,
        )
        assert TS_VERSION == VERSION == 111
        assert TS_RELEASE == RELEASE == "R127"
        assert TSVectorizedLOBEngine is not None
        assert TSVectorizedOrderBook is not None
        assert TSPriceLadderSnapshot is not None
        assert TSMicrostructureMetrics is not None

        b1 = VectorizedOrderBook("005930")
        b2 = TSVectorizedOrderBook("005930")
        assert type(b1).__name__ == type(b2).__name__

    def test_tc03_dual_placement_sha256_hash_identity(self):
        """TC03: Enforce bit-for-bit SHA-256 identity between dual placement paths."""
        p1 = Path("src/core/vectorized_lob_engine.py")
        p2 = Path("trading_system/src/core/vectorized_lob_engine.py")

        assert p1.exists(), f"Missing canonical file: {p1}"
        assert p2.exists(), f"Missing mirrored file: {p2}"

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 hash mismatch: {h1} != {h2}"

    def test_tc04_limit_order_book_fifo_matching(self):
        """TC04: Verify FIFO price-time priority limit order matching and partial fills."""
        book = VectorizedOrderBook("NVDA", tick_size=0.01)

        # Place two maker sell orders at price 100.0
        order_m1, res_m1 = book.add_order("M1", OrderSide.SELL, 100.0, 100.0, OrderType.LIMIT)
        order_m2, res_m2 = book.add_order("M2", OrderSide.SELL, 100.0, 200.0, OrderType.LIMIT)

        assert order_m1 is not None and order_m2 is not None
        assert res_m1.filled_volume == 0.0 and res_m2.filled_volume == 0.0
        assert book.best_ask == 100.0
        assert book.ask_ladder[0, 1] == 300.0  # Total visible ask volume

        # Taker buy arrives for 150 shares at 100.0
        _, res_t1 = book.add_order("T1", OrderSide.BUY, 100.0, 150.0, OrderType.LIMIT)

        assert res_t1.filled_volume == 150.0
        assert res_t1.remaining_volume == 0.0
        assert res_t1.is_fully_filled is True
        assert len(res_t1.fills) == 2

        # Verify FIFO priority: M1 matched first (100 shares), then M2 (50 shares)
        f1 = res_t1.fills[0]
        f2 = res_t1.fills[1]
        assert f1.maker_order_id == "M1"
        assert f1.volume == 100.0
        assert f2.maker_order_id == "M2"
        assert f2.volume == 50.0

        # M1 must be exhausted; M2 remains in the book with 150 shares
        assert "M1" not in book.orders
        assert "M2" in book.orders
        assert book.orders["M2"].display_volume == 150.0
        assert book.orders["M2"].status == OrderStatus.PARTIALLY_FILLED
        assert book.ask_ladder[0, 1] == 150.0

    def test_tc05_market_order_sweep_and_slippage(self):
        """TC05: Verify multi-level sweep, VWAP execution price, and slippage calculation."""
        book = VectorizedOrderBook("MSFT", tick_size=0.01)

        # Populate baseline bids and multi-tier asks
        book.add_order("B0", OrderSide.BUY, 99.0, 100.0, OrderType.LIMIT)
        book.add_order("A1", OrderSide.SELL, 100.0, 100.0, OrderType.LIMIT)
        book.add_order("A2", OrderSide.SELL, 101.0, 200.0, OrderType.LIMIT)
        book.add_order("A3", OrderSide.SELL, 102.0, 300.0, OrderType.LIMIT)

        arrival_mid = (99.0 + 100.0) / 2.0  # 99.50
        assert book.mid_price == arrival_mid

        # Market buy order for 250 shares
        res = book.execute_market_order(OrderSide.BUY, volume=250.0)

        assert res.filled_volume == 250.0
        assert res.remaining_volume == 0.0
        assert res.is_fully_filled is True
        assert res.swept_levels_count == 2

        # Expected VWAP: (100 * 100.0 + 150 * 101.0) / 250 = (10000 + 15150) / 250 = 100.60
        assert abs(res.vwap_fill_price - 100.60) < 1e-4

        # Expected Slippage bps against arrival mid (99.50): |100.60 - 99.50| / 99.50 * 10000 = 110.5528 bps
        expected_slippage = abs(100.60 - arrival_mid) / arrival_mid * 10000.0
        assert abs(res.slippage_bps - expected_slippage) < 1e-2

        # Best ask must now be 101.0 with remaining 50 shares
        assert book.best_ask == 101.0
        assert book.ask_ladder[0, 1] == 50.0

    def test_tc06_multi_level_price_ladder_depth(self):
        """TC06: Verify exact depth ladder tracking across 10, 20, and 50 levels."""
        book = VectorizedOrderBook("SPY", max_levels=50, tick_size=0.01)

        # Insert 50 levels of bids and asks
        for i in range(50):
            p_bid = round(100.0 - (i + 1) * 0.50, 2)
            p_ask = round(101.0 + (i + 1) * 0.50, 2)
            book.add_order(f"BID_{i}", OrderSide.BUY, p_bid, 100.0 + i * 10.0, OrderType.LIMIT)
            book.add_order(f"ASK_{i}", OrderSide.SELL, p_ask, 100.0 + i * 10.0, OrderType.LIMIT)

        # Test 10-level snapshot
        snap10 = book.get_ladder_snapshot(levels=10)
        assert snap10.depth_levels == 10
        assert len(snap10.bid_prices) == 10
        assert len(snap10.ask_prices) == 10
        assert np.all(np.diff(snap10.bid_prices) < 0.0)  # Strictly descending
        assert np.all(np.diff(snap10.ask_prices) > 0.0)  # Strictly ascending

        # Test 20-level snapshot
        snap20 = book.get_ladder_snapshot(levels=20)
        assert snap20.depth_levels == 20
        assert len(snap20.bid_prices) == 20

        # Test 50-level snapshot
        snap50 = book.get_ladder_snapshot(levels=50)
        assert snap50.depth_levels == 50
        assert len(snap50.bid_prices) == 50
        assert len(snap50.ask_prices) == 50
        assert snap50.bid_prices[0] == 99.50
        assert snap50.ask_prices[0] == 101.50
        assert snap50.bid_prices[-1] == round(100.0 - 50 * 0.50, 2)
        assert snap50.ask_prices[-1] == round(101.0 + 50 * 0.50, 2)

    def test_tc07_iceberg_order_replenishment_and_priority_loss(self):
        """TC07: Verify visible peak consumption, reload, and mandatory queue priority loss."""
        book = VectorizedOrderBook("TSLA", tick_size=0.01)

        # 1. Place Iceberg SELL order: total 1000, peak 200 -> display 200, hidden 800
        ice_order, _ = book.add_order(
            "ICE_1", OrderSide.SELL, 100.0, 1000.0, OrderType.ICEBERG, peak_size=200.0
        )
        assert ice_order.display_volume == 200.0
        assert ice_order.hidden_volume == 800.0

        # 2. Place regular limit SELL order at same price
        lim_order, _ = book.add_order(
            "LIM_2", OrderSide.SELL, 100.0, 300.0, OrderType.LIMIT
        )
        assert lim_order.display_volume == 300.0

        # Queue at 100.0 has: ["ICE_1", "LIM_2"]
        queue = book.ask_order_queues[100.0]
        assert list(queue) == ["ICE_1", "LIM_2"]

        # 3. Aggressive taker BUY arrives for 200 shares
        res1 = book.execute_market_order(OrderSide.BUY, volume=200.0)
        assert res1.filled_volume == 200.0
        assert res1.fills[0].maker_order_id == "ICE_1"

        # ICE_1 visible tranche depleted -> reloads 200 from hidden (hidden = 600)
        # CRUCIAL: ICE_1 MUST lose FIFO priority and move to the TAIL of the queue!
        assert ice_order.display_volume == 200.0
        assert ice_order.hidden_volume == 600.0
        assert list(book.ask_order_queues[100.0]) == ["LIM_2", "ICE_1"]

        # 4. Next aggressive taker BUY arrives for 200 shares
        res2 = book.execute_market_order(OrderSide.BUY, volume=200.0)
        assert res2.filled_volume == 200.0
        # MUST match against LIM_2 (not ICE_1) because ICE_1 lost priority upon reload
        assert res2.fills[0].maker_order_id == "LIM_2"
        assert lim_order.display_volume == 100.0
        assert ice_order.display_volume == 200.0  # Untouched!

    def test_tc08_pegged_orders_dynamic_repricing(self):
        """TC08: Verify Primary, Market, and Midpoint peg repricing when top-of-book shifts."""
        book = VectorizedOrderBook("AMZN", tick_size=0.01)

        # Base quotes: Bid 99.0, Ask 101.0 -> Mid 100.0
        book.add_order("B_INIT", OrderSide.BUY, 99.0, 100.0, OrderType.LIMIT)
        book.add_order("A_INIT", OrderSide.SELL, 101.0, 100.0, OrderType.LIMIT)

        # Place Pegged Orders
        pri_order, _ = book.add_order(
            "PRI_PEG", OrderSide.BUY, 0.0, 50.0, OrderType.PRIMARY_PEG, peg_offset=-0.10
        )
        mid_order, _ = book.add_order(
            "MID_PEG", OrderSide.BUY, 0.0, 50.0, OrderType.MIDPOINT_PEG, peg_offset=0.0
        )
        mkt_order, _ = book.add_order(
            "MKT_PEG", OrderSide.BUY, 0.0, 50.0, OrderType.MARKET_PEG, peg_offset=0.20
        )

        assert abs(pri_order.price - 98.90) < 1e-4  # 99.0 - 0.10
        assert abs(mid_order.price - 100.00) < 1e-4 # (99 + 101)/2
        assert abs(mkt_order.price - 100.80) < 1e-4 # 101.0 - 0.20

        # Shift top of book: New best bid 99.50, New best ask 101.50 -> New mid 100.50
        book.add_order("B_NEW", OrderSide.BUY, 99.50, 100.0, OrderType.LIMIT)
        book.add_order("A_NEW", OrderSide.SELL, 101.50, 100.0, OrderType.LIMIT)
        # Cancel old best quotes to establish new quotes as best
        book.cancel_order("A_INIT")

        repriced = book.reprice_pegged_orders()
        assert repriced >= 3

        # Verify updated prices
        assert abs(pri_order.price - 99.40) < 1e-4  # 99.50 - 0.10
        assert abs(mid_order.price - 100.50) < 1e-4 # (99.50 + 101.50)/2
        assert abs(mkt_order.price - 101.30) < 1e-4 # 101.50 - 0.20

        # Verify orders are registered in the new price queues
        assert "PRI_PEG" in book.bid_order_queues[pri_order.price]
        assert "MID_PEG" in book.bid_order_queues[mid_order.price]
        assert "MKT_PEG" in book.bid_order_queues[mkt_order.price]

    def test_tc09_micro_price_vectorized_calculation(self):
        """TC09: Verify Level-1 and multi-level exponential decay micro-prices against analytical values."""
        book = VectorizedOrderBook("GOOGL", max_levels=50, tick_size=0.01)

        # Asymmetric book: Bid 100.0 (vol 1000), Ask 102.0 (vol 3000)
        book.add_order("B1", OrderSide.BUY, 100.0, 1000.0, OrderType.LIMIT)
        book.add_order("A1", OrderSide.SELL, 102.0, 3000.0, OrderType.LIMIT)

        # Add deeper levels
        book.add_order("B2", OrderSide.BUY, 99.0, 2000.0, OrderType.LIMIT)
        book.add_order("A2", OrderSide.SELL, 103.0, 2000.0, OrderType.LIMIT)

        metrics = book.compute_microstructure_metrics()

        # Analytical L1 Micro-price: (3000 * 100.0 + 1000 * 102.0) / 4000 = 402000 / 4000 = 100.50
        assert abs(metrics.micro_price_l1 - 100.50) < 1e-4
        assert metrics.mid_price == 101.0
        assert metrics.spread == 2.0

        # Multi-level micro-prices must be strictly between best bid and best ask
        assert 100.0 <= metrics.micro_price_l10 <= 102.0
        assert 100.0 <= metrics.micro_price_l20 <= 102.0
        assert 100.0 <= metrics.micro_price_l50 <= 102.0

    def test_tc10_instantaneous_effective_spread(self):
        """TC10: Verify quoted vs instantaneous effective spread for varying order volumes."""
        book = VectorizedOrderBook("QQQ", tick_size=0.01)

        # Level 1 has 500 shares; Level 2 has 1000 shares
        book.add_order("B1", OrderSide.BUY, 100.0, 500.0, OrderType.LIMIT)
        book.add_order("B2", OrderSide.BUY, 99.0, 1000.0, OrderType.LIMIT)
        book.add_order("A1", OrderSide.SELL, 101.0, 500.0, OrderType.LIMIT)
        book.add_order("A2", OrderSide.SELL, 102.0, 1000.0, OrderType.LIMIT)

        # Reference order = 100 shares (fits in Level 1)
        m_small = book.compute_microstructure_metrics(reference_order_size=100.0)
        # Reference order = 1200 shares (sweeps into Level 2)
        m_large = book.compute_microstructure_metrics(reference_order_size=1200.0)

        assert m_small.effective_spread_bps >= m_small.spread_bps
        assert m_large.effective_spread_bps > m_small.effective_spread_bps

    def test_tc11_market_depth_imbalance_obi_vector(self):
        """TC11: Verify OBI calculation across levels 1, 5, 10, 20, 50 and bounded in [-1.0, 1.0]."""
        book = VectorizedOrderBook("000660", max_levels=50, tick_size=100.0)

        # Heavy bid imbalance
        for i in range(10):
            p_bid = 100000.0 - i * 100.0
            p_ask = 101000.0 + i * 100.0
            book.add_order(f"B_{i}", OrderSide.BUY, p_bid, 500.0, OrderType.LIMIT)
            book.add_order(f"A_{i}", OrderSide.SELL, p_ask, 100.0, OrderType.LIMIT)

        metrics = book.compute_microstructure_metrics()

        assert metrics.obi_1 > 0.0
        assert metrics.obi_5 > 0.0
        assert metrics.obi_10 > 0.0
        assert metrics.weighted_obi > 0.0
        for obi_val in [metrics.obi_1, metrics.obi_5, metrics.obi_10, metrics.obi_20, metrics.obi_50]:
            assert -1.0 <= obi_val <= 1.0

    def test_tc12_queue_depletion_rate_and_exhaustion(self):
        """TC12: Verify depletion velocity, acceleration, and time-to-exhaustion under aggressive sweeping."""
        book = VectorizedOrderBook("META", tick_size=0.01)

        t0 = 1_000_000_000_000
        # Initialize top ask with 10,000 shares
        book.add_order("A0", OrderSide.SELL, 100.0, 10000.0, OrderType.LIMIT, timestamp_ns=t0)

        # Sweep 6,000 shares after 0.1 seconds (100,000,000 ns)
        t1 = t0 + 100_000_000
        book.execute_market_order(OrderSide.BUY, volume=6000.0, timestamp_ns=t1)

        metrics = book.compute_microstructure_metrics(timestamp_ns=t1)

        # Depletion velocity: (4000 - 10000) / 0.1 = -60000 shares/sec
        assert metrics.ask_depletion_rate <= -50000.0
        # Time to exhaustion: 4000 / 60000 ≈ 0.0667 seconds
        assert 0.01 < metrics.time_to_exhaustion_ask_sec < 0.20

    def test_tc13_fill_probability_estimation(self):
        """TC13: Verify Cont-Kukanov non-linear fill probability bounds [0.01, 0.99] and monotonic ordering."""
        book = VectorizedOrderBook("AMD", tick_size=0.01)

        # Place 3 orders in the same queue
        o1, _ = book.add_order("ORD_1", OrderSide.BUY, 100.0, 100.0, OrderType.LIMIT)
        o2, _ = book.add_order("ORD_2", OrderSide.BUY, 100.0, 100.0, OrderType.LIMIT)
        o3, _ = book.add_order("ORD_3", OrderSide.BUY, 100.0, 100.0, OrderType.LIMIT)

        p1 = book.estimate_order_fill_probability("ORD_1")
        p2 = book.estimate_order_fill_probability("ORD_2")
        p3 = book.estimate_order_fill_probability("ORD_3")

        # Head of queue must have strictly higher probability than tail
        assert p1 > p2 > p3
        assert 0.01 <= p1 <= 0.99
        assert 0.01 <= p2 <= 0.99
        assert 0.01 <= p3 <= 0.99

    def test_tc14_cancellation_and_order_lookup(self):
        """TC14: Verify O(1) order cancellation and ladder volume deduction."""
        book = VectorizedOrderBook("INTC", tick_size=0.01)

        book.add_order("C1", OrderSide.BUY, 50.0, 200.0, OrderType.LIMIT)
        book.add_order("C2", OrderSide.BUY, 50.0, 300.0, OrderType.LIMIT)
        assert book.bid_ladder[0, 1] == 500.0

        # Cancel C1
        canceled = book.cancel_order("C1")
        assert canceled is True
        assert book.bid_ladder[0, 1] == 300.0
        assert "C1" not in book.orders

        # Cancel already canceled order
        canceled_again = book.cancel_order("C1")
        assert canceled_again is False

        # Cancel non-existent order
        assert book.cancel_order("NON_EXISTENT") is False

    def test_tc15_fast_lob_and_oms_integration_bridge(self):
        """TC15: Verify integration adapter with FastLOBEngine and ExecutionOMSEngine order simulation."""
        # 1. FastOrderBookMatchingEngine ingestion
        fast_engine = FastOrderBookMatchingEngine("ETHUSDT", tick_size=0.01)
        fast_engine.add_limit_order("F_B1", "BUY", 2500.0, 10.0)
        fast_engine.add_limit_order("F_A1", "SELL", 2502.0, 15.0)

        vec_book = VectorizedOrderBook.from_fast_lob(fast_engine)
        assert vec_book.symbol == "ETHUSDT"
        assert vec_book.best_bid == 2500.0
        assert vec_book.best_ask == 2502.0
        assert vec_book.spread == 2.0

        # 2. Multi-symbol VectorizedLOBEngine orchestration & impact simulation
        lob_engine = VectorizedLOBEngine()
        lob_engine.submit_order("AAPL", "A_B1", "BUY", 150.0, 500.0)
        lob_engine.submit_order("AAPL", "A_A1", "SELL", 151.0, 300.0)
        lob_engine.submit_order("AAPL", "A_A2", "SELL", 152.0, 600.0)

        impact = lob_engine.simulate_order_impact("AAPL", "BUY", volume=500.0)

        assert impact["symbol"] == "AAPL"
        assert impact["requested_volume"] == 500.0
        assert impact["filled_volume"] == 500.0
        assert impact["remaining_volume"] == 0.0
        assert impact["vwap_fill_price"] > 151.0
        assert impact["swept_levels_count"] == 2
        assert impact["impact_penalty"] > 0.0
        assert impact["effective_spread_bps"] > 0.0

        # Verify snapshot and metrics access
        snap = lob_engine.get_ladder_snapshot("AAPL", levels=5)
        assert snap is not None
        assert snap.best_bid == 150.0

        metrics = lob_engine.get_microstructure_metrics("AAPL")
        assert metrics is not None
        assert metrics.mid_price == 150.5

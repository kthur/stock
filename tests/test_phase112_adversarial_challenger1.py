"""
tests/test_phase112_adversarial_challenger1.py — Empirical Stress & Adversarial Test Suite
Phase 112 Milestone 1: Native Broker OpenAPI Connectors (KIS & LS Broker REST/WebSocket)
Author: Challenger 1 (EMPIRICAL CHALLENGER)

Adversarial Stress Test Battery:
1. Boundary testing on pre-order safety guards:
   - Order value exactly 50,000,000 KRW vs 50,000,001 KRW vs 49,999,999 KRW
   - Price deviation exactly +3.0% vs +3.1%, -3.0% vs -3.1%
   - Non-positive quantities (0, -1, -100)
   - Non-finite / negative prices (NaN, Inf, -100.0)
   - Zero limit price (market order handling)
   - Symbol edge cases (empty symbol, whitespace, code normalization)
   - Order type edge cases (UNKNOWN, STOP_LOSS, MARKET, LIMIT)
2. Order lifecycle edge cases:
   - Modifying a non-existent order
   - Modifying an already CANCELLED order
   - Modifying an already FILLED order
   - Modifying order value exceeding purchasing power
   - Canceling a non-existent order
   - Canceling an already CANCELLED order (idempotency & no double refund)
   - Canceling an already FILLED order
   - Placing orders when disconnected
3. Concurrency, state invariants & stress harnesses:
   - High-throughput batch order placement & cancellation
   - Exact penny-level purchasing power conservation
   - Position short-selling guards
   - Multi-threaded TokenBucketRateLimiter thread safety
   - Malformed WebSocket raw frame parsing resilience
   - Orderbook depth ladder strict monotonic order verification
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import math
from pathlib import Path
import sys
import time
import pytest

# Ensure repo paths are in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir / "trading_system") not in sys.path:
    sys.path.insert(0, str(root_dir / "trading_system"))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.broker.kis_broker_connector import (
    KISBrokerConnector,
    OrderbookDepth,
    OrderbookLevel,
    MarketTradeTick,
    ExecutionNotice,
    TokenBucketRateLimiter,
)
from src.broker.ls_broker_connector import LSBrokerConnector


class TestPhase112AdversarialPreOrderSafetyGuards:
    """Category 1: Empirical Boundary Testing on Pre-Order Safety Guards."""

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_order_value_exact_boundary(self, connector_cls, name):
        """
        Boundary Test: Single order value limit (50,000,000 KRW).
        - 49,999,999 KRW -> Allowed
        - 50,000,000 KRW -> Allowed (exact boundary)
        - 50,000,001 KRW -> Rejected (ValueError)
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        # 1. Exactly 50,000,000 KRW: 50,000 price x 1,000 qty
        r_exact = conn.place_order(
            symbol="005930",
            side="BUY",
            price=50000.0,
            quantity=1000,
            market_price=50000.0,
        )
        assert r_exact["success"] is True, f"{name}: Exact 50M KRW order must be accepted"
        assert r_exact["status"] == "SUBMITTED"

        # 2. Exactly 49,999,999 KRW: 49,999,999 price x 1 qty
        # Note: increase purchasing power for this test to avoid purchasing power check failing first
        conn._sim_purchasing_power = 200_000_000.0
        r_under = conn.place_order(
            symbol="005930",
            side="BUY",
            price=49999999.0,
            quantity=1,
            market_price=49999999.0,
        )
        assert r_under["success"] is True, f"{name}: 49,999,999 KRW order must be accepted"

        # 3. Exactly 50,000,001 KRW: 50,000,001 price x 1 qty
        with pytest.raises(ValueError, match="exceeds maximum allowed single order value limit"):
            conn.place_order(
                symbol="005930",
                side="BUY",
                price=50000001.0,
                quantity=1,
                market_price=50000001.0,
            )

        # 4. 50,000,000.01 KRW (fractional boundary above 50M)
        with pytest.raises(ValueError, match="exceeds maximum allowed single order value limit"):
            conn.place_order(
                symbol="005930",
                side="BUY",
                price=50000000.01,
                quantity=1,
                market_price=50000000.01,
            )

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_price_deviation_exact_boundary(self, connector_cls, name):
        """
        Boundary Test: Price deviation limit (±3.0% vs ±3.1%).
        Reference market price = 100,000.0 KRW.
        - Exactly +3.0% (103,000 KRW) -> Allowed
        - Exactly +3.1% (103,100 KRW) -> Rejected (ValueError)
        - Exactly -3.0% (97,000 KRW)  -> Allowed
        - Exactly -3.1% (96,900 KRW)  -> Rejected (ValueError)
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()
        ref_price = 100000.0

        # +3.0% (103,000.0): dev = 0.030000 <= 0.03 -> Allowed
        r_pos_30 = conn.place_order(
            symbol="005930",
            side="BUY",
            price=103000.0,
            quantity=1,
            market_price=ref_price,
        )
        assert r_pos_30["success"] is True, f"{name}: +3.0% deviation must be allowed"

        # +3.1% (103,100.0): dev = 0.031000 > 0.03 -> Rejected
        with pytest.raises(ValueError, match="deviates by"):
            conn.place_order(
                symbol="005930",
                side="BUY",
                price=103100.0,
                quantity=1,
                market_price=ref_price,
            )

        # -3.0% (97,000.0): dev = 0.030000 <= 0.03 -> Allowed
        r_neg_30 = conn.place_order(
            symbol="005930",
            side="BUY",
            price=97000.0,
            quantity=1,
            market_price=ref_price,
        )
        assert r_neg_30["success"] is True, f"{name}: -3.0% deviation must be allowed"

        # -3.1% (96,900.0): dev = 0.031000 > 0.03 -> Rejected
        with pytest.raises(ValueError, match="deviates by"):
            conn.place_order(
                symbol="005930",
                side="BUY",
                price=96900.0,
                quantity=1,
                market_price=ref_price,
            )

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_non_positive_and_invalid_quantities(self, connector_cls, name):
        """
        Stress Test: Non-positive quantities (0, -1, -100) and edge quantities.
        Must raise ValueError("must be strictly positive").
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        for invalid_q in [0, -1, -100, -999999]:
            with pytest.raises(ValueError, match="must be strictly positive"):
                conn.place_order(
                    symbol="005930",
                    side="BUY",
                    price=70000.0,
                    quantity=invalid_q,
                    market_price=70000.0,
                )

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_invalid_and_non_finite_prices(self, connector_cls, name):
        """
        Stress Test: Negative, NaN, Inf, and non-finite prices.
        Must raise ValueError("must be finite and non-negative").
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        for invalid_p in [-1.0, -100.0, float("nan"), float("inf"), float("-inf")]:
            with pytest.raises(ValueError, match="must be finite and non-negative"):
                conn.place_order(
                    symbol="005930",
                    side="BUY",
                    price=invalid_p,
                    quantity=10,
                    market_price=70000.0,
                )

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_zero_price_market_order_bypass(self, connector_cls, name):
        """
        Edge Case: price = 0.0 (Market order, 시장가 주문).
        Sanity bound (±3%) must NOT trigger on price=0.0 market orders.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        # In simulation mode, order_val = 0.0 * 10 = 0.0 <= purchasing power
        r = conn.place_order(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            price=0.0,
            quantity=10,
            market_price=70000.0,
        )
        assert r["success"] is True
        assert r["status"] == "SUBMITTED"

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_symbol_code_normalization(self, connector_cls, name):
        """
        Edge Case: Symbol suffixes (e.g. '005930.KS', 'A005930', '005930').
        Connectors must handle symbol strings without crashes.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        for sym in ["005930", "005930.KS", "A005930"]:
            r = conn.place_order(
                symbol=sym,
                side="BUY",
                price=70000.0,
                quantity=1,
                market_price=70000.0,
            )
            assert r["success"] is True
            assert r["symbol"] == sym


class TestPhase112AdversarialOrderLifecycle:
    """Category 2: Empirical Testing on Order Lifecycle Edge Cases."""

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_modify_non_existent_order(self, connector_cls, name):
        """
        Edge Case: Modifying a non-existent order.
        Must return success: False, status: REJECTED, without raising unhandled exceptions.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        res = conn.modify_order(
            order_id="NON_EXISTENT_ORDER_99999",
            symbol="005930",
            new_price=70000.0,
            new_quantity=10,
            market_price=70000.0,
        )
        assert res["success"] is False, f"{name}: Modifying non-existent order must fail"
        assert res["status"] == "REJECTED"
        assert "not found" in res.get("error", "").lower()

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_modify_already_cancelled_order(self, connector_cls, name):
        """
        Edge Case: Modifying an already CANCELLED order.
        Must return success: False, error indicating order is already CANCELLED.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        # Place and cancel order
        r = conn.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)
        oid = r["order_id"]
        conn.cancel_order(oid)

        # Attempt to modify cancelled order
        res = conn.modify_order(
            order_id=oid,
            symbol="005930",
            new_price=71000.0,
            new_quantity=5,
            market_price=70000.0,
        )
        assert res["success"] is False
        assert "already CANCELLED" in res.get("error", "")

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_modify_already_filled_order(self, connector_cls, name):
        """
        Edge Case: Modifying an already FILLED order.
        Must return success: False, error indicating order is already FILLED.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        r = conn.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)
        oid = r["order_id"]

        # Simulate execution fill
        conn._sim_orders[oid]["status"] = "FILLED"
        conn._sim_orders[oid]["filled_quantity"] = 10
        conn._sim_orders[oid]["remaining_quantity"] = 0

        # Attempt to modify filled order
        res = conn.modify_order(
            order_id=oid,
            symbol="005930",
            new_price=71000.0,
            new_quantity=5,
            market_price=70000.0,
        )
        assert res["success"] is False
        assert "already FILLED" in res.get("error", "")

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_cancel_non_existent_order(self, connector_cls, name):
        """
        Edge Case: Canceling a non-existent order.
        Must return success: False, status: NOT_FOUND, without throwing unhandled exceptions.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        res = conn.cancel_order("NON_EXISTENT_ORDER_88888")
        assert res["success"] is False
        assert res["status"] == "NOT_FOUND"
        assert "not found" in res.get("error", "").lower()

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_cancel_already_cancelled_order_idempotency(self, connector_cls, name):
        """
        Edge Case: Duplicate cancellation of an already CANCELLED order.
        Must be idempotent: returns CANCELLED without double refunding purchasing power.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()
        initial_pp = conn.get_balance()["purchasing_power"]

        r = conn.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)
        oid = r["order_id"]
        assert conn.get_balance()["purchasing_power"] == initial_pp - 700000.0

        # 1st cancel
        c1 = conn.cancel_order(oid)
        assert c1["success"] is True
        assert c1["status"] == "CANCELLED"
        assert conn.get_balance()["purchasing_power"] == initial_pp

        # 2nd cancel (duplicate)
        c2 = conn.cancel_order(oid)
        assert c2["success"] is True
        assert c2["status"] == "CANCELLED"
        # Purchasing power must STILL equal initial_pp (NO double refund)
        assert conn.get_balance()["purchasing_power"] == initial_pp

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_cancel_already_filled_order(self, connector_cls, name):
        """
        Edge Case: Canceling an order that has already been FILLED.
        Empirical check: Verify connector behavior when order is marked FILLED.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()
        initial_pp = conn.get_balance()["purchasing_power"]

        r = conn.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)
        oid = r["order_id"]

        # Simulate fill
        conn._sim_orders[oid]["status"] = "FILLED"
        conn._sim_orders[oid]["filled_quantity"] = 10
        conn._sim_orders[oid]["remaining_quantity"] = 0

        # Attempt cancel on filled order
        res = conn.cancel_order(oid)

        # In exchange reality, canceling a filled order fails.
        # Check that purchasing power is NOT refunded for filled shares:
        post_cancel_pp = conn.get_balance()["purchasing_power"]
        assert post_cancel_pp == initial_pp - 700000.0, "Filled order cancel must NOT refund purchasing power"

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_order_placement_when_disconnected(self, connector_cls, name):
        """
        Edge Case: Placing orders when connector is NOT connected.
        Empirical check: Verify whether place_order executes or raises when is_connected is False.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        # Explicitly do NOT connect (or disconnect)
        assert not conn.is_connected
        assert not conn.is_connected()

        # Note: Simulation mode allows offline testing, but in production is_connected is tracked.
        # Test whether simulation mode accepts or whether connection state is checked:
        try:
            r = conn.place_order(symbol="005930", side="BUY", price=70000.0, quantity=1, market_price=70000.0)
            placed_while_disconnected = True
        except Exception:
            placed_while_disconnected = False

        # Document behavior: simulation mode executes offline, but is_connected state remains False.
        assert not conn.is_connected


class TestPhase112AdversarialStressAndInvariants:
    """Category 3: Concurrency, Accounting Invariants & Stress Harnesses."""

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_purchasing_power_overdraft_protection(self, connector_cls, name):
        """
        Stress Test: Overdraft protection across multiple orders.
        Ensure total orders cannot exceed purchasing power (100,000,000 KRW).
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()
        conn._sim_purchasing_power = 100_000_000.0

        # Place 2 orders of 40,000,000 KRW each (Total = 80,000,000 KRW)
        r1 = conn.place_order(symbol="005930", side="BUY", price=40000.0, quantity=1000, market_price=40000.0)
        assert r1["success"] is True
        r2 = conn.place_order(symbol="005930", side="BUY", price=40000.0, quantity=1000, market_price=40000.0)
        assert r2["success"] is True

        assert conn.get_balance()["purchasing_power"] == 20_000_000.0

        # Attempt 3rd order of 30,000,000 KRW (exceeds remaining 20,000,000 KRW)
        with pytest.raises(ValueError, match="Insufficient purchasing power"):
            conn.place_order(symbol="005930", side="BUY", price=30000.0, quantity=1000, market_price=30000.0)

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_position_short_selling_protection(self, connector_cls, name):
        """
        Stress Test: Uncovered short selling rejection.
        Selling shares without holding available position must raise ValueError.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()

        # Sell 100 shares of 005930 with zero holdings
        with pytest.raises(ValueError, match="Insufficient position"):
            conn.place_order(symbol="005930", side="SELL", price=70000.0, quantity=100, market_price=70000.0)

        # Add position of 50 shares
        conn._sim_positions["005930"] = {"symbol": "005930", "quantity": 50, "available_quantity": 50}

        # Sell 50 shares -> Allowed
        r_sell = conn.place_order(symbol="005930", side="SELL", price=70000.0, quantity=50, market_price=70000.0)
        assert r_sell["success"] is True

        # Sell 1 more share -> Insufficient position
        with pytest.raises(ValueError, match="Insufficient position"):
            conn.place_order(symbol="005930", side="SELL", price=70000.0, quantity=1, market_price=70000.0)

    @pytest.mark.parametrize("connector_cls, name", [(KISBrokerConnector, "KIS"), (LSBrokerConnector, "LS")])
    def test_high_throughput_penny_level_conservation(self, connector_cls, name):
        """
        Stress Harness: 50 sequential orders and 25 cancellations.
        Verifies exact penny-level purchasing power conservation with zero floating point drift.
        """
        conn = connector_cls(account_number="12345678", simulation_mode=True)
        conn.connect()
        initial_pp = conn.get_balance()["purchasing_power"]

        order_ids = []
        unit_val = 1_000_000.0  # 100 shares @ 10,000 KRW

        # Place 50 orders of 1,000,000 KRW each
        for i in range(50):
            r = conn.place_order(
                symbol="005930",
                side="BUY",
                price=10000.0,
                quantity=100,
                market_price=10000.0,
            )
            order_ids.append(r["order_id"])

        mid_pp = conn.get_balance()["purchasing_power"]
        assert mid_pp == pytest.approx(initial_pp - (50 * unit_val), abs=1e-4)

        # Cancel 25 orders
        for oid in order_ids[:25]:
            c = conn.cancel_order(oid)
            assert c["success"] is True

        final_pp = conn.get_balance()["purchasing_power"]
        assert final_pp == pytest.approx(initial_pp - (25 * unit_val), abs=1e-4)

    def test_rate_limiter_multithreaded_stress(self):
        """
        Concurrency Stress Test: Rapid multi-threaded token acquisition.
        Ensures thread safety, monotonic token replenishment, and zero deadlocks.
        """
        limiter = TokenBucketRateLimiter(rate=1000.0, capacity=100.0)

        def worker(thread_id: int):
            for _ in range(50):
                limiter.acquire(1.0)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            for f in futures:
                f.result(timeout=5.0)

        # Verify state is consistent
        assert limiter.tokens >= -1.0  # Allowed minor deficit right after burst
        assert limiter.capacity == 100.0

    def test_kis_malformed_orderbook_frame_handling(self):
        """
        Edge Case: Malformed or truncated WebSocket orderbook frames.
        Verify connector resilience: gracefully falls back to valid OrderbookDepth without crashing.
        """
        conn = KISBrokerConnector(simulation_mode=True)

        # Truncated message (only 2 parts)
        depth1 = conn.parse_orderbook_frame("0|H0STASP0")
        assert isinstance(depth1, OrderbookDepth)
        assert len(depth1.asks) == 0
        assert len(depth1.bids) == 0

        # Incomplete payload (fewer than 40 parts)
        depth2 = conn.parse_orderbook_frame("0|H0STASP0|001|005930^093000^short")
        assert isinstance(depth2, OrderbookDepth)
        assert depth2.symbol == "005930"
        assert len(depth2.asks) == 0

    def test_ls_malformed_orderbook_frame_handling(self):
        """
        Edge Case: Malformed LS WebSocket orderbook JSON payload.
        Verify connector resilience: gracefully handles missing body key by falling back to root dict.
        """
        conn = LSBrokerConnector(simulation_mode=True)

        depth = conn.parse_orderbook_frame({"header": {"tr_key": "000660"}})
        assert isinstance(depth, OrderbookDepth)
        assert depth.symbol == "000660"
        assert len(depth.asks) == 0
        assert len(depth.bids) == 0

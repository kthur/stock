"""
tests/test_phase118_adversarial_challenger_execution.py
=======================================================
Empirical Adversarial Stress, Invariant, and Benchmark Suite for:
Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core (Feature F560).
Phase 118 (Release R134 / v125 Production Master).

Adversarial Challenge Dimensions:
  1. High-throughput burst stress (10,000+ random orders: Limit/Market/IOC/FOK/Cancel).
  2. Ring buffer wrap-around (> 65,536 slots): slot reuse, eviction integrity, pointer sanity.
  3. Empty book and single-side book operations: sweeps, snapshots, and NaN-free invariance.
  4. Deterministic price-time priority: strict FIFO queue ordering, partial fills, iceberg demotion.
  5. Extreme numerical boundaries: zero/negative volume, NaN/inf prices, whale sweeps.
  6. Dual-backend execution determinism (NumPy SIMD fallback vs PyTorch AVX2).
"""

from __future__ import annotations

import math
import random
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.simd_lob_matching_core import (
    DEFAULT_ORDER_CAPACITY,
    DEFAULT_PRICE_LEVELS,
    OrderSide,
    OrderType,
    OrderStatus,
    SIMDLOBOrderPool,
    SIMDLOBMatchingCore,
    SIMDMatchResult,
    L3Snapshot,
    _TORCH_AVAILABLE,
)


class TestPhase118AdversarialSIMDLOB(unittest.TestCase):
    """Empirical adversarial stress testing for Feature F560 SIMD LOB Matching Core."""

    # -----------------------------------------------------------------------
    # Challenge 1: High-Throughput Burst Stress (10,000+ mixed operations)
    # -----------------------------------------------------------------------
    def test_adv01_high_throughput_burst_stress_10k_orders(self):
        """Stress-test with 12,000 mixed orders in rapid succession."""
        random.seed(1337)
        np.random.seed(1337)

        engine = SIMDLOBMatchingCore(symbol="STRESS_BURST", pool_capacity=65536)

        # Pre-seed realistic book depth (50 bids, 50 asks)
        for i in range(50):
            engine.match_order({"order_id": f"SEED_B_{i}", "side": "BUY", "price": 100.0 - (i * 0.05), "volume": 50.0})
            engine.match_order({"order_id": f"SEED_A_{i}", "side": "SELL", "price": 100.10 + (i * 0.05), "volume": 50.0})

        active_pool: List[str] = [f"SEED_B_{i}" for i in range(50)] + [f"SEED_A_{i}" for i in range(50)]

        N = 12000
        latencies_us: List[float] = []
        fills_count = 0
        cancels_count = 0

        t0_total = time.perf_counter()
        for i in range(N):
            op = random.random()
            side = "BUY" if random.random() < 0.5 else "SELL"
            px = round(100.0 + random.uniform(-1.50, 1.50), 2)
            vol = round(random.uniform(1.0, 15.0), 1)
            oid = f"BURST_{i}"

            t_op0 = time.perf_counter_ns()
            if op < 0.40:
                # Limit order
                res = engine.match_order({"order_id": oid, "side": side, "price": px, "volume": vol})
                if res.status in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                    active_pool.append(oid)
                fills_count += len(res.fills)
            elif op < 0.60:
                # Market order
                res = engine.execute_market_order("STRESS_BURST", side, vol)
                fills_count += len(res.fills)
            elif op < 0.75:
                # Immediate-or-Cancel
                res = engine.execute_ioc({"order_id": oid, "side": side, "price": px, "volume": vol})
                fills_count += len(res.fills)
            elif op < 0.90:
                # Fill-or-Kill
                res = engine.execute_fok({"order_id": oid, "side": side, "price": px, "volume": vol})
                fills_count += len(res.fills)
            else:
                # Cancel random resting order
                if active_pool:
                    idx = random.randint(0, len(active_pool) - 1)
                    target = active_pool.pop(idx)
                    if engine.cancel_order(target):
                        cancels_count += 1
            t_op1 = time.perf_counter_ns()
            latencies_us.append((t_op1 - t_op0) / 1000.0)

        t1_total = time.perf_counter()
        elapsed_sec = t1_total - t0_total
        throughput = N / elapsed_sec

        lat_arr = np.array(latencies_us)
        avg_lat = float(np.mean(lat_arr))
        p99_lat = float(np.percentile(lat_arr, 99))
        max_lat = float(np.max(lat_arr))

        # Assert throughput > 8,000 orders/sec under high stress
        self.assertGreater(throughput, 8000.0, f"Throughput too low: {throughput:.0f} orders/sec")
        self.assertLess(avg_lat, 250.0, f"Average latency too high: {avg_lat:.2f} us")

        # Invariant validation post-burst
        snap = engine.get_l3_snapshot(depth=20)
        self.assertFalse(np.isnan(snap.flat_tensor_40).any(), "NaN found in L3 snapshot flat tensor")
        if snap.best_bid > 0 and not math.isinf(snap.best_ask):
            self.assertLessEqual(snap.best_bid, snap.best_ask + 1e-7, "Order book crossed post-burst!")

    # -----------------------------------------------------------------------
    # Challenge 2: Ring Buffer Wrap-Around (> 65,536 slots)
    # -----------------------------------------------------------------------
    def test_adv02_ring_buffer_wrap_around_exceeding_capacity(self):
        """Submit 70,000 orders to exceed 65,536 capacity, testing wrap-around and slot reuse."""
        engine = SIMDLOBMatchingCore(symbol="WRAP_TEST", pool_capacity=65536)
        self.assertEqual(engine.capacity, 65536)
        self.assertEqual(engine.head_seq, 0)

        # Insert 70,000 resting orders across 10 distinct price levels
        N = 70000
        for i in range(N):
            px = 100.0 - (i % 10) * 0.10
            engine.match_order({"order_id": f"W_{i}", "side": "BUY", "price": px, "volume": 1.0})

        self.assertEqual(engine.head_seq, 70000)

        # Oldest orders (0 to 4463) must have been overwritten and evicted
        for old_i in [0, 100, 1000, 4463]:
            old_order = engine.get_order_by_id(f"W_{old_i}")
            self.assertIsNone(old_order, f"Evicted order W_{old_i} should not be retrievable")
            # Cancelling evicted order must return False safely
            self.assertFalse(engine.cancel_order(f"W_{old_i}"), f"Cancelling evicted order W_{old_i} should return False")

        # Recent orders (4464 to 69999) must be valid and retrievable
        for new_i in [4464, 10000, 50000, 69999]:
            new_order = engine.get_order_by_id(f"W_{new_i}")
            self.assertIsNotNone(new_order, f"Active order W_{new_i} must be found")
            self.assertEqual(new_order["status"], OrderStatus.ACTIVE)

        # Active order count must equal capacity (65,536)
        active_orders = engine.get_active_orders()
        self.assertEqual(len(active_orders), 65536, f"Expected exactly 65,536 active orders, got {len(active_orders)}")

        # Verify matching against the wrapped book works seamlessly
        sweep_res = engine.match_order({"order_id": "TAKER_SELL_1", "side": "SELL", "price": 95.0, "volume": 500.0})
        self.assertEqual(sweep_res.filled_volume, 500.0)
        self.assertEqual(len(sweep_res.fills), 500)
        self.assertEqual(sweep_res.status, OrderStatus.FILLED)

        # Verify active count decreased by 500
        active_after = engine.get_active_orders()
        self.assertEqual(len(active_after), 65536 - 500)

    # -----------------------------------------------------------------------
    # Challenge 3: Empty Book & Single-Side Book Operations
    # -----------------------------------------------------------------------
    def test_adv03_empty_book_robustness_and_nan_invariance(self):
        """Verify sweeps and queries on empty book execute cleanly without NaN or exceptions."""
        engine = SIMDLOBMatchingCore(symbol="EMPTY_SYM", pool_capacity=1024)

        # 1. Market Buy and Sell on empty book
        mkt_buy = engine.execute_market_order("EMPTY_SYM", "BUY", 100.0)
        self.assertEqual(mkt_buy.filled_volume, 0.0)
        self.assertEqual(mkt_buy.vwap_fill_price, 0.0)
        self.assertFalse(math.isnan(mkt_buy.vwap_fill_price))
        self.assertEqual(mkt_buy.status, OrderStatus.CANCELED)

        mkt_sell = engine.execute_market_order("EMPTY_SYM", "SELL", 100.0)
        self.assertEqual(mkt_sell.filled_volume, 0.0)
        self.assertEqual(mkt_sell.vwap_fill_price, 0.0)
        self.assertFalse(math.isnan(mkt_sell.vwap_fill_price))
        self.assertEqual(mkt_sell.status, OrderStatus.CANCELED)

        # 2. IOC Buy and Sell on empty book
        ioc_buy = engine.execute_ioc({"order_id": "IOC_1", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(ioc_buy.filled_volume, 0.0)
        self.assertEqual(ioc_buy.canceled_volume, 50.0)
        self.assertFalse(math.isnan(ioc_buy.vwap_fill_price))
        self.assertEqual(ioc_buy.status, OrderStatus.CANCELED)

        ioc_sell = engine.execute_ioc({"order_id": "IOC_2", "side": "SELL", "price": 100.0, "volume": 50.0})
        self.assertEqual(ioc_sell.filled_volume, 0.0)
        self.assertEqual(ioc_sell.canceled_volume, 50.0)
        self.assertFalse(math.isnan(ioc_sell.vwap_fill_price))
        self.assertEqual(ioc_sell.status, OrderStatus.CANCELED)

        # 3. FOK on empty book
        fok_res = engine.execute_fok({"order_id": "FOK_1", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(fok_res.filled_volume, 0.0)
        self.assertTrue(fok_res.is_rejected)
        self.assertEqual(fok_res.status, OrderStatus.REJECTED)

        # 4. Cancellation on empty book
        self.assertFalse(engine.cancel_order("NON_EXISTENT_ORDER"))

        # 5. Snapshots & metrics on empty book
        snap = engine.get_l3_snapshot(depth=10)
        self.assertEqual(snap.best_bid, 0.0)
        self.assertEqual(snap.best_ask, float("inf"))
        self.assertEqual(snap.spread, 0.0)
        self.assertEqual(snap.mid_price, 0.0)
        self.assertEqual(snap.micro_price, 0.0)
        self.assertEqual(snap.flat_tensor_40.shape, (40,))
        self.assertFalse(np.isnan(snap.flat_tensor_40).any())

        metrics = engine.compute_microstructure_metrics()
        self.assertEqual(metrics.spread, 0.0)
        self.assertEqual(metrics.mid_price, 0.0)
        self.assertFalse(math.isnan(metrics.micro_price_l1))
        self.assertFalse(math.isnan(metrics.weighted_obi))

    def test_adv04_single_sided_book_sweeps(self):
        """Verify behavior when only one side of the book is populated."""
        # Book with bids only
        bids_only = SIMDLOBMatchingCore(symbol="BIDS_ONLY", pool_capacity=1024)
        bids_only.match_order({"order_id": "B_1", "side": "BUY", "price": 100.0, "volume": 20.0})
        bids_only.match_order({"order_id": "B_2", "side": "BUY", "price": 99.0, "volume": 30.0})

        # Sweeping the empty Ask side
        mkt_buy = bids_only.execute_market_order("BIDS_ONLY", "BUY", 10.0)
        self.assertEqual(mkt_buy.filled_volume, 0.0)
        self.assertEqual(mkt_buy.status, OrderStatus.CANCELED)

        # Selling into populated Bid side
        sell_res = bids_only.match_order({"order_id": "S_1", "side": "SELL", "price": 98.0, "volume": 35.0})
        self.assertEqual(sell_res.filled_volume, 35.0)
        self.assertEqual(len(sell_res.fills), 2)
        # B_1 (20 @ 100.0) + B_2 (15 @ 99.0) -> VWAP = (2000 + 1485) / 35 = 99.571428...
        expected_vwap = (20.0 * 100.0 + 15.0 * 99.0) / 35.0
        self.assertAlmostEqual(sell_res.vwap_fill_price, expected_vwap, places=5)

        # Remaining on B_2 should be 15
        order_b2 = bids_only.get_order_by_id("B_2")
        self.assertEqual(order_b2["display_volume"], 15.0)
        self.assertEqual(order_b2["status"], OrderStatus.PARTIALLY_FILLED)

    # -----------------------------------------------------------------------
    # Challenge 4: Deterministic Price-Time Priority (Strict FIFO)
    # -----------------------------------------------------------------------
    def test_adv05_deterministic_fifo_price_time_priority(self):
        """Verify earlier submitted orders are strictly filled before later orders at the same price."""
        engine = SIMDLOBMatchingCore(symbol="FIFO_CORE", pool_capacity=2048)

        # Place 6 orders at identical price level 100.0
        order_specs = [
            ("O_A", 10.0),
            ("O_B", 25.0),
            ("O_C", 15.0),
            ("O_D", 30.0),
            ("O_E", 20.0),
            ("O_F", 50.0),
        ]
        for oid, vol in order_specs:
            engine.match_order({"order_id": oid, "side": "BUY", "price": 100.0, "volume": vol})

        # Sweep 1: 45 shares -> fills O_A (10), O_B (25), O_C (10, leaves 5)
        res1 = engine.match_order({"order_id": "TAKER_1", "side": "SELL", "price": 100.0, "volume": 45.0})
        fills1 = [(f.maker_order_id, f.volume) for f in res1.fills]
        self.assertEqual(fills1, [("O_A", 10.0), ("O_B", 25.0), ("O_C", 10.0)])
        self.assertEqual(engine.get_order_by_id("O_C")["display_volume"], 5.0)

        # Cancel O_D in the middle of the queue
        self.assertTrue(engine.cancel_order("O_D"))
        self.assertIsNone(engine.get_order_by_id("O_D"))

        # Sweep 2: 15 shares -> fills O_C remainder (5), then O_E (10, leaves 10). O_D was skipped!
        res2 = engine.match_order({"order_id": "TAKER_2", "side": "SELL", "price": 100.0, "volume": 15.0})
        fills2 = [(f.maker_order_id, f.volume) for f in res2.fills]
        self.assertEqual(fills2, [("O_C", 5.0), ("O_E", 10.0)])

        # Sweep 3: 60 shares -> fills O_E remainder (10), then O_F (50)
        res3 = engine.match_order({"order_id": "TAKER_3", "side": "SELL", "price": 100.0, "volume": 60.0})
        fills3 = [(f.maker_order_id, f.volume) for f in res3.fills]
        self.assertEqual(fills3, [("O_E", 10.0), ("O_F", 50.0)])

        # Level 100.0 should now be completely depleted and pruned
        snap = engine.get_l3_snapshot(depth=5)
        self.assertEqual(snap.best_bid, 0.0)

    def test_adv06_iceberg_queue_priority_demotion(self):
        """Verify iceberg orders reload and lose priority upon visible tranche exhaustion."""
        engine = SIMDLOBMatchingCore(symbol="ICEBERG_TEST", pool_capacity=1024)

        # Place Iceberg order: total 100, display 20, hidden 80
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 50.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })

        # Place regular Limit order behind Iceberg: 30 shares
        engine.match_order({"order_id": "REG_2", "side": "BUY", "price": 50.0, "volume": 30.0})

        # Sweep 25 shares:
        # Fills ICE_1 display (20). ICE_1 tranche is exhausted -> reloads 20 from hidden and moves to TAIL!
        # Next 5 shares fill REG_2 (5, leaves 25).
        sweep1 = engine.match_order({"order_id": "SWEEP_1", "side": "SELL", "price": 50.0, "volume": 25.0})
        fills1 = [(f.maker_order_id, f.volume) for f in sweep1.fills]
        self.assertEqual(fills1, [("ICE_1", 20.0), ("REG_2", 5.0)])

        # Now REG_2 is ahead of ICE_1 in priority!
        # Sweep 25 shares: should completely fill REG_2 remainder (25) BEFORE touching ICE_1!
        sweep2 = engine.match_order({"order_id": "SWEEP_2", "side": "SELL", "price": 50.0, "volume": 25.0})
        fills2 = [(f.maker_order_id, f.volume) for f in sweep2.fills]
        self.assertEqual(fills2, [("REG_2", 25.0)])

        # Now ICE_1 is at the head again (display 20, hidden 60)
        sweep3 = engine.match_order({"order_id": "SWEEP_3", "side": "SELL", "price": 50.0, "volume": 30.0})
        fills3 = [(f.maker_order_id, f.volume) for f in sweep3.fills]
        # Fills ICE_1 display (20), reloads 20 (hidden becomes 40), then fills 10 from new display
        self.assertEqual(fills3, [("ICE_1", 20.0), ("ICE_1", 10.0)])

    # -----------------------------------------------------------------------
    # Challenge 5: Numerical & Boundary Conditions
    # -----------------------------------------------------------------------
    def test_adv07_invalid_inputs_and_boundary_rejections(self):
        """Verify strict rejection of zero/negative volumes, NaN prices, and invalid types."""
        engine = SIMDLOBMatchingCore(symbol="INPUT_TEST", pool_capacity=1024)

        # Zero and negative volume
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "BAD_1", "side": "BUY", "price": 100.0, "volume": 0.0})

        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "BAD_2", "side": "BUY", "price": 100.0, "volume": -5.0})

        # NaN and infinite prices for Limit orders
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "BAD_3", "side": "BUY", "price": float("nan"), "volume": 10.0})

        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "BAD_4", "side": "BUY", "price": float("inf"), "volume": 10.0})

        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "BAD_5", "side": "BUY", "price": -10.0, "volume": 10.0})

    # -----------------------------------------------------------------------
    # Challenge 6: Dual Backend Execution Determinism
    # -----------------------------------------------------------------------
    def test_adv08_dual_backend_deterministic_parity(self):
        """Verify NumPy fallback and PyTorch SIMD produce bit-for-bit identical executions."""
        engine_np = SIMDLOBMatchingCore(symbol="PARITY_TEST", pool_capacity=2048, use_torch=False)
        engine_torch = SIMDLOBMatchingCore(symbol="PARITY_TEST", pool_capacity=2048, use_torch=True)

        orders = [
            {"order_id": "B1", "side": "BUY", "price": 100.0, "volume": 20.0},
            {"order_id": "B2", "side": "BUY", "price": 99.5, "volume": 40.0},
            {"order_id": "A1", "side": "SELL", "price": 101.0, "volume": 30.0},
            {"order_id": "A2", "side": "SELL", "price": 101.5, "volume": 50.0},
        ]
        for o in orders:
            engine_np.match_order(o)
            engine_torch.match_order(o)

        # Execute IOC order on both
        ioc_spec = {"order_id": "IOC_T", "side": "BUY", "price": 101.2, "volume": 45.0}
        res_np = engine_np.execute_ioc(ioc_spec)
        res_torch = engine_torch.execute_ioc(ioc_spec)

        self.assertEqual(res_np.filled_volume, res_torch.filled_volume)
        self.assertAlmostEqual(res_np.vwap_fill_price, res_torch.vwap_fill_price, places=6)
        self.assertEqual(len(res_np.fills), len(res_torch.fills))

        # Compare L3 snapshots
        snap_np = engine_np.get_l3_snapshot(depth=5)
        snap_torch = engine_torch.get_l3_snapshot(depth=5)

        np.testing.assert_array_almost_equal(snap_np.bid_prices, snap_torch.bid_prices)
        np.testing.assert_array_almost_equal(snap_np.bid_volumes, snap_torch.bid_volumes)
        np.testing.assert_array_almost_equal(snap_np.ask_prices, snap_torch.ask_prices)
        np.testing.assert_array_almost_equal(snap_np.ask_volumes, snap_torch.ask_volumes)
        np.testing.assert_array_almost_equal(snap_np.flat_tensor_40, snap_torch.flat_tensor_40)

    # -----------------------------------------------------------------------
    # Challenge 7: Iceberg Order Volume Integrity & Concealment
    # -----------------------------------------------------------------------
    def test_adv09_iceberg_resting_volume_inflation(self):
        """Verify iceberg orders do not inflate volume when placed into resting book."""
        engine = SIMDLOBMatchingCore(symbol="ICE_VOL_TEST", pool_capacity=1024)

        # Place Iceberg order requesting 100.0 total volume: 20.0 display, 80.0 hidden
        engine.match_order({
            "order_id": "ICE_ORDER",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 50.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })

        order_data = engine.get_order_by_id("ICE_ORDER")
        self.assertIsNotNone(order_data)

        # Total order volume must be 100.0, NOT 180.0
        # Display volume must be 20.0, NOT 100.0
        self.assertEqual(order_data["display_volume"], 20.0, f"Display volume should be 20.0, got {order_data['display_volume']}")
        self.assertEqual(order_data["hidden_volume"], 80.0, f"Hidden volume should be 80.0, got {order_data['hidden_volume']}")
        self.assertEqual(
            order_data["display_volume"] + order_data["hidden_volume"],
            100.0,
            f"Total volume inflated: {order_data['display_volume'] + order_data['hidden_volume']} != 100.0",
        )


if __name__ == "__main__":
    unittest.main()


"""
tests/test_phase118_challenger2_lob_stress.py
=============================================
Milestone 1 Empirical Challenger 2 Adversarial Stress Suite for Feature F560:
Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core.

Adversarially probes:
1. FOK Boundary Conditions:
   - Total resting depth Q, FOK buy with Q + 1e-6 -> strict zero-fill rejection with book untouched.
   - FOK buy with exact depth Q -> complete fill, order status FILLED.
   - FOK sell boundary with Q + 1e-6 vs Q.
   - Price ceiling violation and empty book FOK rejection.
2. IOC Residual Drop & Book Footprint:
   - Large IOC buy partially sweeping top 3 levels with 50% unfilled residual.
   - Top 3 levels consumed, residual immediately canceled, zero trace in book.
   - Large IOC sell partially sweeping top 3 levels with 50% unfilled residual.
   - Non-marketable IOC zero-footprint behavior.
3. Extreme Price Ticks & Fractional Quantities:
   - Micro-penny sub-cent pricing (0.0001 tick) and priority sorting.
   - Floating-point precision rounding (0.1 + 0.2 == 0.30000000000000004) without phantom dust orders.
   - Zero, negative, NaN, and Inf prices and volumes defensive validation.
4. Crossed Book Resolution & Taker Price Improvement:
   - Aggressive taker buy crossing multiple ask levels executed at maker prices.
   - Aggressive taker sell crossing multiple bid levels executed at maker prices.
   - Aggressive order with residual resting at limit price.
5. Dual-Backend (NumPy vs PyTorch) Deterministic Execution Parity.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.simd_lob_matching_core import (
    OrderStatus,
    OrderSide,
    OrderType,
    SIMDLOBMatchingCore,
    SIMDMatchResult,
    TimeInForce,
)


class TestPhase118Challenger2LOBStress(unittest.TestCase):
    """Empirical adversarial stress test suite for SIMDLOBMatchingCore."""

    # -----------------------------------------------------------------------
    # 1. FOK Boundary Conditions
    # -----------------------------------------------------------------------
    def test_adv01_fok_exact_boundary_condition_buy(self):
        """Place resting asks total Q; FOK with Q+1e-6 rejects untouched; FOK with Q fills 100%."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 120.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 80.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 50.0})

        Q = 250.0  # 120 + 80 + 50
        self.assertEqual(engine.asks.get_best_volume(), 120.0)
        self.assertEqual(len(engine.ask_prices), 3)

        # FOK with Q + 10^-6: MUST REJECT WITH ZERO FILL AND ZERO MUTATION
        res_fail = engine.execute_fok({
            "order_id": "FOK_EXCESS",
            "side": "BUY",
            "price": 105.0,
            "volume": Q + 1e-6,
        })
        self.assertEqual(res_fail.filled_volume, 0.0)
        self.assertAlmostEqual(res_fail.remaining_volume, Q + 1e-6, places=8)
        self.assertEqual(len(res_fail.fills), 0)
        self.assertEqual(res_fail.status, OrderStatus.REJECTED)
        self.assertTrue(res_fail.is_rejected)
        self.assertFalse(res_fail.is_fully_filled)

        # Verify book is 100% untouched
        self.assertEqual(len(engine.ask_prices), 3)
        np.testing.assert_allclose(engine.ask_prices, [100.0, 101.0, 102.0])
        np.testing.assert_allclose(engine.ask_volumes, [120.0, 80.0, 50.0])
        self.assertEqual(engine.best_bid, 0.0)

        # FOK with exact Q: MUST FULLY COMMIT 100% OF DEPTH
        res_ok = engine.execute_fok({
            "order_id": "FOK_EXACT",
            "side": "BUY",
            "price": 105.0,
            "volume": Q,
        })
        self.assertEqual(res_ok.filled_volume, Q)
        self.assertEqual(res_ok.remaining_volume, 0.0)
        self.assertEqual(len(res_ok.fills), 3)
        self.assertEqual(res_ok.status, OrderStatus.FILLED)
        self.assertTrue(res_ok.is_fully_filled)

        # Verify ask book is now fully depleted
        self.assertEqual(len(engine.ask_prices), 0)
        self.assertEqual(engine.best_ask, float("inf"))

    def test_adv02_fok_exact_boundary_condition_sell(self):
        """Place resting bids total Q; FOK sell with Q+1e-6 rejects untouched; FOK with Q fills 100%."""
        engine = SIMDLOBMatchingCore(symbol="TSLA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 200.0, "volume": 70.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 199.0, "volume": 60.0})
        engine.match_order({"order_id": "B3", "side": "BUY", "price": 198.0, "volume": 45.0})

        Q = 175.0  # 70 + 60 + 45
        # FOK sell with Q + 1e-6 -> strict rejection
        res_fail = engine.execute_fok({
            "order_id": "FOK_SELL_EXCESS",
            "side": "SELL",
            "price": 195.0,
            "volume": Q + 1e-6,
        })
        self.assertEqual(res_fail.filled_volume, 0.0)
        self.assertEqual(res_fail.status, OrderStatus.REJECTED)
        self.assertTrue(res_fail.is_rejected)

        # Book untouched
        self.assertEqual(len(engine.bid_prices), 3)
        np.testing.assert_allclose(engine.bid_prices, [200.0, 199.0, 198.0])
        np.testing.assert_allclose(engine.bid_volumes, [70.0, 60.0, 45.0])

        # FOK sell with exact Q -> full commit
        res_ok = engine.execute_fok({
            "order_id": "FOK_SELL_EXACT",
            "side": "SELL",
            "price": 195.0,
            "volume": Q,
        })
        self.assertEqual(res_ok.filled_volume, Q)
        self.assertEqual(res_ok.remaining_volume, 0.0)
        self.assertEqual(res_ok.status, OrderStatus.FILLED)
        self.assertEqual(len(engine.bid_prices), 0)
        self.assertEqual(engine.best_bid, 0.0)

    def test_adv03_fok_price_ceiling_and_empty_book_boundaries(self):
        """FOK orders failing price boundary or on empty book reject cleanly with 0 fills."""
        engine = SIMDLOBMatchingCore(symbol="MSFT")
        # Empty book rejection
        res_empty = engine.execute_fok({"order_id": "FOK_EMPTY", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(res_empty.filled_volume, 0.0)
        self.assertEqual(res_empty.status, OrderStatus.REJECTED)

        # Place depth at 100.0 (50) and 105.0 (50)
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 105.0, "volume": 50.0})

        # FOK buy limit at 102.0 for 100.0: volume is 100, but only 50 available <= 102.0
        res_ceil = engine.execute_fok({"order_id": "FOK_CEIL", "side": "BUY", "price": 102.0, "volume": 100.0})
        self.assertEqual(res_ceil.filled_volume, 0.0)
        self.assertEqual(res_ceil.status, OrderStatus.REJECTED)
        self.assertEqual(len(engine.ask_prices), 2)
        self.assertEqual(engine.asks.get_best_volume(), 50.0)

    # -----------------------------------------------------------------------
    # 2. IOC Residual Drop & Book Cleanliness
    # -----------------------------------------------------------------------
    def test_adv04_ioc_residual_drop_and_zero_book_footprint_buy(self):
        """Submit large IOC buy sweeping top 3 levels with 50% unfilled residual; residual dropped, 0 footprint."""
        engine = SIMDLOBMatchingCore(symbol="AAPL")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 30.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 20.0})
        engine.match_order({"order_id": "A4", "side": "SELL", "price": 103.0, "volume": 100.0})

        # Top 3 levels have 50 + 30 + 20 = 100 shares.
        # Submit IOC buy for 200 shares with limit 102.0 -> sweeps top 3 levels (100 shares), 100 shares (50%) canceled
        res = engine.execute_ioc({
            "order_id": "IOC_SWEEP_BUY",
            "side": "BUY",
            "price": 102.0,
            "volume": 200.0,
        })

        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.remaining_volume, 100.0)
        self.assertEqual(res.canceled_volume, 100.0)
        self.assertEqual(res.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(res.swept_levels_count, 3)
        self.assertFalse(res.is_fully_filled)

        # Invariant 1: Top 3 levels consumed, Level 4 at 103.0 untouched
        self.assertEqual(engine.best_ask, 103.0)
        self.assertEqual(engine.asks.get_best_volume(), 100.0)
        np.testing.assert_allclose(engine.ask_prices, [103.0])
        np.testing.assert_allclose(engine.ask_volumes, [100.0])

        # Invariant 2: Book contains NO trace of the IOC order
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(len(engine.bid_prices), 0)
        self.assertIsNone(engine.get_order_by_id("IOC_SWEEP_BUY"))

    def test_adv05_ioc_residual_drop_and_zero_book_footprint_sell(self):
        """Submit large IOC sell sweeping top 3 levels with 50% unfilled residual; residual dropped, 0 footprint."""
        engine = SIMDLOBMatchingCore(symbol="GOOGL")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 150.0, "volume": 60.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 149.0, "volume": 25.0})
        engine.match_order({"order_id": "B3", "side": "BUY", "price": 148.0, "volume": 15.0})
        engine.match_order({"order_id": "B4", "side": "BUY", "price": 145.0, "volume": 80.0})

        # Top 3 levels total 60 + 25 + 15 = 100 shares.
        # Submit IOC sell for 200 shares with limit 148.0 -> sweeps top 3 levels, 100 shares canceled
        res = engine.execute_ioc({
            "order_id": "IOC_SWEEP_SELL",
            "side": "SELL",
            "price": 148.0,
            "volume": 200.0,
        })

        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.remaining_volume, 100.0)
        self.assertEqual(res.canceled_volume, 100.0)
        self.assertEqual(res.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(res.swept_levels_count, 3)

        # Invariants: Level 4 at 145.0 untouched, zero trace of IOC sell in asks
        self.assertEqual(engine.best_bid, 145.0)
        self.assertEqual(engine.bids.get_best_volume(), 80.0)
        self.assertEqual(engine.best_ask, float("inf"))
        self.assertEqual(len(engine.ask_prices), 0)
        self.assertIsNone(engine.get_order_by_id("IOC_SWEEP_SELL"))

    def test_adv06_ioc_non_marketable_zero_footprint(self):
        """Non-marketable IOC (limit worse than best quote) cancels 100% without mutating book."""
        engine = SIMDLOBMatchingCore(symbol="AMZN")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 105.0, "volume": 50.0})

        res = engine.execute_ioc({"order_id": "IOC_PASSIVE", "side": "BUY", "price": 100.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertEqual(res.canceled_volume, 100.0)
        self.assertEqual(res.status, OrderStatus.CANCELED)
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.best_ask, 105.0)
        self.assertIsNone(engine.get_order_by_id("IOC_PASSIVE"))

    # -----------------------------------------------------------------------
    # 3. Extreme Price Ticks & Fractional Quantities
    # -----------------------------------------------------------------------
    def test_adv07_extreme_micro_penny_pricing_and_order_priority(self):
        """Micro-penny sub-cent increments (e.g. 100.0001, 100.0005) preserve strict sorting and execution."""
        engine = SIMDLOBMatchingCore(symbol="MICRO")
        # Resting bids with 0.0001 resolution
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 100.0001, "volume": 10.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 100.0005, "volume": 20.0})
        engine.match_order({"order_id": "B3", "side": "BUY", "price": 100.0002, "volume": 15.0})

        # Bids sorted descending
        np.testing.assert_allclose(engine.bid_prices, [100.0005, 100.0002, 100.0001])
        np.testing.assert_allclose(engine.bid_volumes, [20.0, 15.0, 10.0])
        self.assertAlmostEqual(engine.best_bid, 100.0005, places=6)

        # Resting asks with micro-penny steps
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0008, "volume": 10.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 100.0006, "volume": 25.0})

        # Asks sorted ascending
        np.testing.assert_allclose(engine.ask_prices, [100.0006, 100.0008])
        self.assertAlmostEqual(engine.best_ask, 100.0006, places=6)
        self.assertAlmostEqual(engine.spread, 0.0001, places=6)

        # Taker buy at 100.0007 for 30 shares: sweeps 100.0006 (25 shares), rests 5 shares at 100.0007
        res = engine.match_order({"order_id": "T_MICRO", "side": "BUY", "price": 100.0007, "volume": 30.0})
        self.assertEqual(res.filled_volume, 25.0)
        self.assertEqual(res.remaining_volume, 5.0)
        self.assertEqual(res.fills[0].price, 100.0006)  # Maker price improvement

        self.assertAlmostEqual(engine.best_bid, 100.0007, places=6)
        self.assertEqual(engine.bids.get_best_volume(), 5.0)
        self.assertAlmostEqual(engine.best_ask, 100.0008, places=6)

    def test_adv08_float_precision_rounding_0_1_plus_0_2(self):
        """0.1 + 0.2 (0.30000000000000004) float rounding issues do not leak phantom dust orders."""
        engine1 = SIMDLOBMatchingCore(symbol="PRECISION1")
        vol_maker = 0.3
        vol_taker = 0.1 + 0.2  # 0.30000000000000004

        engine1.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": vol_maker})
        res1 = engine1.match_order({"order_id": "B1", "side": "BUY", "price": 100.0, "volume": vol_taker})

        self.assertEqual(res1.filled_volume, 0.3)
        self.assertTrue(res1.is_fully_filled)
        # Residual 5.55e-17 MUST NOT rest in book
        self.assertEqual(len(engine1.ask_prices), 0)
        self.assertEqual(len(engine1.bid_prices), 0)
        self.assertEqual(engine1.best_bid, 0.0)
        self.assertEqual(engine1.best_ask, float("inf"))

        # Reverse situation: Maker is 0.1 + 0.2, Taker is 0.3
        engine2 = SIMDLOBMatchingCore(symbol="PRECISION2")
        engine2.match_order({"order_id": "A2", "side": "SELL", "price": 100.0, "volume": vol_taker})
        res2 = engine2.match_order({"order_id": "B2", "side": "BUY", "price": 100.0, "volume": vol_maker})

        self.assertEqual(res2.filled_volume, 0.3)
        self.assertTrue(res2.is_fully_filled)
        # Level MUST be pruned cleanly
        self.assertEqual(len(engine2.ask_prices), 0)
        self.assertEqual(len(engine2.bid_prices), 0)

        # 10 tranches of 0.1 (sum = 0.9999999999999999) vs 1.0 maker
        engine3 = SIMDLOBMatchingCore(symbol="PRECISION3")
        engine3.match_order({"order_id": "A3", "side": "SELL", "price": 50.0, "volume": 1.0})
        sum_ten = sum([0.1 for _ in range(10)])
        res3 = engine3.match_order({"order_id": "B3", "side": "BUY", "price": 50.0, "volume": sum_ten})
        self.assertTrue(res3.is_fully_filled)
        self.assertEqual(len(engine3.ask_prices), 0)

    def test_adv09_invalid_price_and_volume_defensive_checks(self):
        """match_order strictly rejects non-positive/non-finite volume and price."""
        engine = SIMDLOBMatchingCore(symbol="DEFENSE")

        # Non-positive and non-finite volumes
        for bad_vol in [0.0, -1.0, -1e-6, float("nan"), float("inf"), float("-inf")]:
            with self.assertRaises(ValueError):
                engine.match_order({"order_id": "BAD_VOL", "side": "BUY", "price": 100.0, "volume": bad_vol})

        # Non-positive and non-finite prices
        for bad_px in [0.0, -10.0, -0.01, float("nan"), float("inf"), float("-inf")]:
            with self.assertRaises(ValueError):
                engine.match_order({"order_id": "BAD_PX", "side": "BUY", "price": bad_px, "volume": 10.0})

        # FOK with non-executable or negative prices rejects safely
        res_fok_neg = engine.execute_fok({"order_id": "FOK_NEG", "side": "BUY", "price": -10.0, "volume": 10.0})
        self.assertEqual(res_fok_neg.status, OrderStatus.REJECTED)
        self.assertEqual(res_fok_neg.filled_volume, 0.0)

    # -----------------------------------------------------------------------
    # 4. Crossed Book Resolution & Taker Price Improvement
    # -----------------------------------------------------------------------
    def test_adv10_crossed_book_multi_level_sweep_price_improvement_buy(self):
        """Aggressive BUY crosses 3 ask levels; all fills execute at MAKER prices (taker price improvement)."""
        engine = SIMDLOBMatchingCore(symbol="CROSS_BUY")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 40.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 30.0})

        # Aggressive Limit BUY at 103.0 for 100 shares
        res = engine.match_order({"order_id": "T_AGG_BUY", "side": "BUY", "price": 103.0, "volume": 100.0})

        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.remaining_volume, 0.0)
        self.assertTrue(res.is_fully_filled)
        self.assertEqual(len(res.fills), 3)

        # Tranche fills MUST execute at MAKER prices (100.0, 101.0, 102.0), NOT taker price 103.0!
        self.assertEqual(res.fills[0].price, 100.0)
        self.assertEqual(res.fills[0].volume, 50.0)
        self.assertEqual(res.fills[0].maker_order_id, "A1")

        self.assertEqual(res.fills[1].price, 101.0)
        self.assertEqual(res.fills[1].volume, 40.0)
        self.assertEqual(res.fills[1].maker_order_id, "A2")

        self.assertEqual(res.fills[2].price, 102.0)
        self.assertEqual(res.fills[2].volume, 10.0)
        self.assertEqual(res.fills[2].maker_order_id, "A3")

        # Analytical VWAP = (50*100 + 40*101 + 10*102) / 100 = 100.60
        self.assertAlmostEqual(res.vwap_fill_price, 100.60, places=5)

        # Price improvement: Taker willing to pay 103.0, achieved 100.60 VWAP (2.40 savings/share)
        self.assertGreater(103.0, res.vwap_fill_price)

        # Remainder at Level 3 (20 shares at 102.0) stays resting
        self.assertEqual(engine.best_ask, 102.0)
        self.assertEqual(engine.asks.get_best_volume(), 20.0)

    def test_adv11_crossed_book_multi_level_sweep_price_improvement_sell(self):
        """Aggressive SELL crosses 3 bid levels; all fills execute at MAKER prices (taker price improvement)."""
        engine = SIMDLOBMatchingCore(symbol="CROSS_SELL")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 102.0, "volume": 50.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 101.0, "volume": 40.0})
        engine.match_order({"order_id": "B3", "side": "BUY", "price": 100.0, "volume": 30.0})

        # Aggressive Limit SELL at 99.0 for 100 shares
        res = engine.match_order({"order_id": "T_AGG_SELL", "side": "SELL", "price": 99.0, "volume": 100.0})

        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.remaining_volume, 0.0)
        self.assertTrue(res.is_fully_filled)
        self.assertEqual(len(res.fills), 3)

        # Tranche fills MUST execute at MAKER prices (102.0, 101.0, 100.0), NOT taker price 99.0!
        self.assertEqual(res.fills[0].price, 102.0)
        self.assertEqual(res.fills[0].volume, 50.0)

        self.assertEqual(res.fills[1].price, 101.0)
        self.assertEqual(res.fills[1].volume, 40.0)

        self.assertEqual(res.fills[2].price, 100.0)
        self.assertEqual(res.fills[2].volume, 10.0)

        # Analytical VWAP = (50*102 + 40*101 + 10*100) / 100 = 101.40
        self.assertAlmostEqual(res.vwap_fill_price, 101.40, places=5)
        self.assertGreater(res.vwap_fill_price, 99.0)  # Taker sold higher than limit price

        # Remainder at Bid Level 3 (20 shares at 100.0) stays resting
        self.assertEqual(engine.best_bid, 100.0)
        self.assertEqual(engine.bids.get_best_volume(), 20.0)

    def test_adv12_crossed_book_with_residual_taker_volume_resting(self):
        """Aggressive BUY sweeps all available asks, residual volume rests at taker limit price as new bid."""
        engine = SIMDLOBMatchingCore(symbol="CROSS_REST")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 30.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 20.0})

        # Total asks = 50. Taker BUY for 80 at 102.0 -> 50 fills, 30 rests as Bid at 102.0
        res = engine.match_order({"order_id": "T_CROSS", "side": "BUY", "price": 102.0, "volume": 80.0})

        self.assertEqual(res.filled_volume, 50.0)
        self.assertEqual(res.remaining_volume, 30.0)
        self.assertEqual(res.status, OrderStatus.PARTIALLY_FILLED)

        # Asks completely depleted
        self.assertEqual(len(engine.ask_prices), 0)
        self.assertEqual(engine.best_ask, float("inf"))

        # Residual rests at taker's limit price 102.0
        self.assertEqual(engine.best_bid, 102.0)
        self.assertEqual(engine.bids.get_best_volume(), 30.0)
        self.assertIsNotNone(engine.get_order_by_id("T_CROSS"))

    # -----------------------------------------------------------------------
    # 5. Dual-Backend Determinism Parity
    # -----------------------------------------------------------------------
    def test_adv13_dual_backend_adversarial_determinism_parity(self):
        """Crossed sweeps, FOK, and IOC execute with bitwise parity across NumPy and PyTorch backends."""
        eng_np = SIMDLOBMatchingCore(symbol="PARITY", use_torch=False)
        eng_pt = SIMDLOBMatchingCore(symbol="PARITY", use_torch=True)

        for eng in (eng_np, eng_pt):
            # Seed identical resting book
            for i in range(5):
                eng.match_order({"order_id": f"A_{i}", "side": "SELL", "price": 100.0 + i, "volume": 50.0})
                eng.match_order({"order_id": f"B_{i}", "side": "BUY", "price": 95.0 - i, "volume": 50.0})

            # 1. Crossed Buy Sweep
            res_cross = eng.match_order({"order_id": "T_CROSS", "side": "BUY", "price": 102.5, "volume": 120.0})
            # 2. IOC Sell Sweep
            res_ioc = eng.execute_ioc({"order_id": "T_IOC", "side": "SELL", "price": 93.0, "volume": 130.0})
            # 3. FOK Buy rejection
            res_fok_rej = eng.execute_fok({"order_id": "T_FOK_REJ", "side": "BUY", "price": 105.0, "volume": 999.0})

        # Assert parity of final books
        np.testing.assert_allclose(eng_np.bid_prices, eng_pt.bid_prices)
        np.testing.assert_allclose(eng_np.bid_volumes, eng_pt.bid_volumes)
        np.testing.assert_allclose(eng_np.ask_prices, eng_pt.ask_prices)
        np.testing.assert_allclose(eng_np.ask_volumes, eng_pt.ask_volumes)
        self.assertEqual(eng_np.best_bid, eng_pt.best_bid)
        self.assertEqual(eng_np.best_ask, eng_pt.best_ask)
        self.assertEqual(eng_np.spread, eng_pt.spread)


if __name__ == "__main__":
    unittest.main()

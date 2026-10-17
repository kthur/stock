"""
tests/test_phase118_challenger3_iceberg_adversarial.py
======================================================
Milestone 1 Iteration 2 Challenger 3 Empirical Adversarial Suite:
Iceberg Queue Priority Demotion, Multi-Tranche Sweep, and Mass Conservation.
Phase 118 (Release R134 / v125 Production Master, Feature F560).

Adversarially probes:
1. Multi-Tranche Alternating Round-Robin FIFO Demotion (Two competing Icebergs).
2. Interleaved Queue Priority Demotion (Multiple Icebergs and Regular Orders).
3. Incoming Aggressive Iceberg Mass Conservation and Resting Allocations.
4. L3 Snapshot Strict Information Concealment and Intrusive Pointer Invariants.
5. Iceberg Atomic Cancellation and Link Invariants across all Lifecycle Stages.
6. Single-Order Deep Multi-Tranche Sweep (50+ consecutive tranches).
7. IOC Multi-Tranche Sweeps against Iceberg and Residual Drop.
8. Multi-Level Cross-Ladder Sweeps with Heterogeneous Iceberg and Regular Depths.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

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
    L3Snapshot,
)


class TestPhase118Challenger3IcebergAdversarial(unittest.TestCase):
    """Empirical adversarial challenger tests for Iceberg matching, demotion, and volume invariants."""

    # -----------------------------------------------------------------------
    # 1. Multi-Tranche Alternating Round-Robin Demotion (Two Competing Icebergs)
    # -----------------------------------------------------------------------
    def test_ch3_01_two_icebergs_alternating_round_robin_fifo_demotion(self):
        """Two icebergs at the same price alternate round-robin priority as tranches exhaust."""
        engine = SIMDLOBMatchingCore(symbol="ICE_RR", pool_capacity=2048)

        # Place ICE_A (disp 10, hid 30, peak 10 -> total 40)
        engine.match_order({
            "order_id": "ICE_A",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 40.0,
            "display_volume": 10.0,
            "hidden_volume": 30.0,
            "peak_size": 10.0,
        })

        # Place ICE_B (disp 10, hid 30, peak 10 -> total 40)
        engine.match_order({
            "order_id": "ICE_B",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 40.0,
            "display_volume": 10.0,
            "hidden_volume": 30.0,
            "peak_size": 10.0,
        })

        # Initial queue: ICE_A (disp 10) -> ICE_B (disp 10). Visible = 20, Hidden = 60.
        self.assertEqual(engine.best_bid, 100.0)
        self.assertEqual(engine.bids.get_best_volume(), 20.0)

        # Sweep 1: 15 shares
        # ICE_A fills 10 -> exhausts display -> reloads 10 (hid=20) and demotes behind ICE_B!
        # ICE_B fills 5 (leaves 5 disp, 30 hid).
        # Queue should now be: ICE_B (5 disp, 30 hid) -> ICE_A (10 disp, 20 hid).
        res1 = engine.match_order({"order_id": "SWEEP_1", "side": "SELL", "price": 100.0, "volume": 15.0})
        fills1 = [(f.maker_order_id, f.volume) for f in res1.fills]
        self.assertEqual(fills1, [("ICE_A", 10.0), ("ICE_B", 5.0)])

        order_a = engine.get_order_by_id("ICE_A")
        order_b = engine.get_order_by_id("ICE_B")
        self.assertEqual(order_a["display_volume"], 10.0)
        self.assertEqual(order_a["hidden_volume"], 20.0)
        self.assertEqual(order_b["display_volume"], 5.0)
        self.assertEqual(order_b["hidden_volume"], 30.0)
        self.assertEqual(engine.bids.get_best_volume(), 15.0)  # 10 + 5

        # Sweep 2: 10 shares
        # ICE_B is at head with 5 display -> fills 5 -> exhausts display -> reloads 10 (hid=20) and demotes behind ICE_A!
        # ICE_A fills 5 (leaves 5 disp, 20 hid).
        # Queue should now be: ICE_A (5 disp, 20 hid) -> ICE_B (10 disp, 20 hid).
        res2 = engine.match_order({"order_id": "SWEEP_2", "side": "SELL", "price": 100.0, "volume": 10.0})
        fills2 = [(f.maker_order_id, f.volume) for f in res2.fills]
        self.assertEqual(fills2, [("ICE_B", 5.0), ("ICE_A", 5.0)])

        order_a = engine.get_order_by_id("ICE_A")
        order_b = engine.get_order_by_id("ICE_B")
        self.assertEqual(order_a["display_volume"], 5.0)
        self.assertEqual(order_a["hidden_volume"], 20.0)
        self.assertEqual(order_b["display_volume"], 10.0)
        self.assertEqual(order_b["hidden_volume"], 20.0)
        self.assertEqual(engine.bids.get_best_volume(), 15.0)  # 5 + 10

        # Sweep 3: 20 shares
        # ICE_A fills 5 -> reloads 10 (hid=10), demotes behind ICE_B.
        # ICE_B fills 10 -> reloads 10 (hid=10), demotes behind ICE_A.
        # ICE_A fills 5 (leaves 5 disp, 10 hid).
        # Fills: ICE_A (5), ICE_B (10), ICE_A (5).
        res3 = engine.match_order({"order_id": "SWEEP_3", "side": "SELL", "price": 100.0, "volume": 20.0})
        fills3 = [(f.maker_order_id, f.volume) for f in res3.fills]
        self.assertEqual(fills3, [("ICE_A", 5.0), ("ICE_B", 10.0), ("ICE_A", 5.0)])

        # Conservation of volume: Initial 80.0 - (15 + 10 + 20 = 45) == 35.0 remaining
        order_a = engine.get_order_by_id("ICE_A")
        order_b = engine.get_order_by_id("ICE_B")
        rem_a = order_a["display_volume"] + order_a["hidden_volume"]
        rem_b = order_b["display_volume"] + order_b["hidden_volume"]
        self.assertEqual(rem_a + rem_b, 35.0)
        self.assertEqual(order_a["cum_filled"] + rem_a, 40.0)
        self.assertEqual(order_b["cum_filled"] + rem_b, 40.0)

    # -----------------------------------------------------------------------
    # 2. Interleaved Queue Priority Demotion (Icebergs and Regular Orders)
    # -----------------------------------------------------------------------
    def test_ch3_02_interleaved_icebergs_and_multiple_regular_orders(self):
        """Interleaved queue of regular and iceberg orders preserves exact FIFO priority."""
        engine = SIMDLOBMatchingCore(symbol="ICE_INTERLEAVED", pool_capacity=2048)

        # Place 5 orders at 100.0:
        # ICE_1: disp 10, hid 20 (total 30)
        # REG_2: 15
        # ICE_3: disp 10, hid 20 (total 30)
        # REG_4: 25
        # REG_5: 10
        engine.match_order({"order_id": "ICE_1", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 30.0, "display_volume": 10.0, "hidden_volume": 20.0, "peak_size": 10.0})
        engine.match_order({"order_id": "REG_2", "side": "BUY", "price": 100.0, "volume": 15.0})
        engine.match_order({"order_id": "ICE_3", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 30.0, "display_volume": 10.0, "hidden_volume": 20.0, "peak_size": 10.0})
        engine.match_order({"order_id": "REG_4", "side": "BUY", "price": 100.0, "volume": 25.0})
        engine.match_order({"order_id": "REG_5", "side": "BUY", "price": 100.0, "volume": 10.0})

        # Total depth = 30 + 15 + 30 + 25 + 10 = 110.0
        # Visible depth = 10 + 15 + 10 + 25 + 10 = 70.0
        self.assertEqual(engine.bids.get_best_volume(), 70.0)

        # Step 1: Sweep 30 shares
        # ICE_1 fills 10 -> exhausts display -> reloads 10 (hid 10), demotes behind REG_5.
        # REG_2 fills 15 -> completely filled.
        # ICE_3 fills 5 (leaves 5 disp, 20 hid).
        # Expected fills: ICE_1: 10, REG_2: 15, ICE_3: 5.
        res1 = engine.match_order({"order_id": "T_1", "side": "SELL", "price": 100.0, "volume": 30.0})
        self.assertEqual([(f.maker_order_id, f.volume) for f in res1.fills], [("ICE_1", 10.0), ("REG_2", 15.0), ("ICE_3", 5.0)])
        reg2 = engine.get_order_by_id("REG_2")
        self.assertIsNotNone(reg2)
        self.assertEqual(reg2["status"], OrderStatus.FILLED)
        self.assertEqual(reg2["cum_filled"], 15.0)
        self.assertEqual(reg2["display_volume"], 0.0)
        self.assertNotIn("REG_2", [o["order_id"] for o in engine.get_active_orders()])

        # Step 2: Sweep 35 shares
        # Head is ICE_3 (5 disp) -> fills 5 -> exhausts -> reloads 10 (hid 10), demotes behind ICE_1.
        # Next is REG_4 (25) -> fills 25 -> fully filled.
        # Next is REG_5 (10) -> fills 5 (leaves 5).
        # Expected fills: ICE_3: 5, REG_4: 25, REG_5: 5.
        res2 = engine.match_order({"order_id": "T_2", "side": "SELL", "price": 100.0, "volume": 35.0})
        self.assertEqual([(f.maker_order_id, f.volume) for f in res2.fills], [("ICE_3", 5.0), ("REG_4", 25.0), ("REG_5", 5.0)])

        # Step 3: Sweep 45 shares (remaining: REG_5 5, ICE_1 20, ICE_3 20 -> total 45.0)
        # Fills REG_5 (5), ICE_1 (10 disp -> reload 10), ICE_3 (10 disp -> reload 10), ICE_1 (10 final), ICE_3 (10 final)
        res3 = engine.match_order({"order_id": "T_3", "side": "SELL", "price": 100.0, "volume": 45.0})
        self.assertEqual(
            [(f.maker_order_id, f.volume) for f in res3.fills],
            [("REG_5", 5.0), ("ICE_1", 10.0), ("ICE_3", 10.0), ("ICE_1", 10.0), ("ICE_3", 10.0)],
        )

        # Level 100.0 should now be completely depleted and pruned
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.bids.active_levels, 0)

    # -----------------------------------------------------------------------
    # 3. Incoming Aggressive Iceberg Volume Conservation and Resting Allocations
    # -----------------------------------------------------------------------
    def test_ch3_03_incoming_aggressive_iceberg_volume_conservation(self):
        """Incoming aggressive Iceberg order conserves mass when partially filled before resting."""
        # Case A: Partial fill leaving more than display volume
        engine_a = SIMDLOBMatchingCore(symbol="ICE_INC_A")
        engine_a.match_order({"order_id": "ASK_1", "side": "SELL", "price": 50.0, "volume": 20.0})
        engine_a.match_order({"order_id": "ASK_2", "side": "SELL", "price": 50.0, "volume": 15.0})

        # Total resting asks = 35.0. Send incoming BUY Iceberg 100.0 (disp 20, hid 80, peak 20)
        res_a = engine_a.match_order({
            "order_id": "ICE_TAKER_A",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 50.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        self.assertEqual(res_a.filled_volume, 35.0)
        self.assertEqual(res_a.remaining_volume, 65.0)
        self.assertEqual(res_a.status, OrderStatus.PARTIALLY_FILLED)

        # Resting remainder in book:
        # Leaves = 65.0. rem_disp = min(65, 20) = 20.0, rem_hid = 45.0.
        resting_a = engine_a.get_order_by_id("ICE_TAKER_A")
        self.assertIsNotNone(resting_a)
        self.assertEqual(resting_a["display_volume"], 20.0)
        self.assertEqual(resting_a["hidden_volume"], 45.0)
        self.assertEqual(resting_a["cum_filled"], 35.0)
        self.assertEqual(resting_a["display_volume"] + resting_a["hidden_volume"] + resting_a["cum_filled"], 100.0)
        self.assertEqual(engine_a.bids.get_best_volume(), 20.0)  # Only visible volume exposed!

        # Case B: Partial fill leaving less than display volume
        engine_b = SIMDLOBMatchingCore(symbol="ICE_INC_B")
        engine_b.match_order({"order_id": "ASK_BIG", "side": "SELL", "price": 50.0, "volume": 85.0})

        res_b = engine_b.match_order({
            "order_id": "ICE_TAKER_B",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 50.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        self.assertEqual(res_b.filled_volume, 85.0)
        self.assertEqual(res_b.remaining_volume, 15.0)

        # Leaves = 15.0 < 20.0. rem_disp = 15.0, rem_hid = 0.0.
        resting_b = engine_b.get_order_by_id("ICE_TAKER_B")
        self.assertEqual(resting_b["display_volume"], 15.0)
        self.assertEqual(resting_b["hidden_volume"], 0.0)
        self.assertEqual(resting_b["cum_filled"], 85.0)
        self.assertEqual(resting_b["display_volume"] + resting_b["hidden_volume"] + resting_b["cum_filled"], 100.0)
        self.assertEqual(engine_b.bids.get_best_volume(), 15.0)

    # -----------------------------------------------------------------------
    # 4. L3 Snapshot Strict Information Concealment and Intrusive Walk
    # -----------------------------------------------------------------------
    def test_ch3_04_l3_snapshot_strict_concealment_and_intrusive_walk(self):
        """L3 Snapshot strictly conceals hidden volume in aggregated volume and flat tensor."""
        engine = SIMDLOBMatchingCore(symbol="SNAP_CONCEAL")

        # Populate bids with heterogeneous orders
        engine.match_order({"order_id": "B_REG_1", "side": "BUY", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "B_ICE_2", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 200.0, "display_volume": 30.0, "hidden_volume": 170.0, "peak_size": 30.0})
        engine.match_order({"order_id": "B_ICE_3", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 99.0, "volume": 500.0, "display_volume": 50.0, "hidden_volume": 450.0, "peak_size": 50.0})

        # Populate asks
        engine.match_order({"order_id": "A_ICE_1", "side": "SELL", "order_type": OrderType.ICEBERG, "price": 101.0, "volume": 1000.0, "display_volume": 100.0, "hidden_volume": 900.0, "peak_size": 100.0})

        snap = engine.get_l3_snapshot(depth=5)

        # 1. Level 100.0 Bid: visible volume MUST be 50.0 + 30.0 = 80.0, NOT 250.0!
        self.assertEqual(snap.bids[0].price, 100.0)
        self.assertEqual(snap.bids[0].aggregated_volume, 80.0)
        self.assertEqual(snap.bids[0].order_count, 2)
        # Orders inside level: sum of display_volume MUST equal aggregated_volume
        disp_sum = sum(o.display_volume for o in snap.bids[0].orders)
        self.assertEqual(disp_sum, snap.bids[0].aggregated_volume)

        # 2. Level 99.0 Bid: visible volume MUST be 50.0, NOT 500.0!
        self.assertEqual(snap.bids[1].price, 99.0)
        self.assertEqual(snap.bids[1].aggregated_volume, 50.0)

        # 3. Level 101.0 Ask: visible volume MUST be 100.0, NOT 1000.0!
        self.assertEqual(snap.asks[0].price, 101.0)
        self.assertEqual(snap.asks[0].aggregated_volume, 100.0)

        # 4. Flat tensor of shape (40,):
        # [bid_p_1, bid_v_1, ask_p_1, ask_v_1, bid_p_2, bid_v_2, ...]
        # bid_v_1 must be 80.0, ask_v_1 must be 100.0, bid_v_2 must be 50.0
        self.assertEqual(snap.flat_tensor_40[0], 100.0)
        self.assertEqual(snap.flat_tensor_40[1], 80.0)
        self.assertEqual(snap.flat_tensor_40[2], 101.0)
        self.assertEqual(snap.flat_tensor_40[3], 100.0)
        self.assertEqual(snap.flat_tensor_40[4], 99.0)
        self.assertEqual(snap.flat_tensor_40[5], 50.0)

    # -----------------------------------------------------------------------
    # 5. Iceberg Atomic Cancellation and Link Invariants
    # -----------------------------------------------------------------------
    def test_ch3_05_iceberg_cancellation_mass_conservation_and_unlinking(self):
        """Canceling an iceberg at different lifecycle stages decrements ladder volumes cleanly."""
        engine = SIMDLOBMatchingCore(symbol="ICE_CANCEL")

        # Scenario A: Cancel un-traded resting iceberg
        engine.match_order({"order_id": "ICE_UNTOUCHED", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 100.0, "display_volume": 20.0, "hidden_volume": 80.0, "peak_size": 20.0})
        self.assertEqual(engine.bids.get_best_volume(), 20.0)
        self.assertTrue(engine.cancel_order("ICE_UNTOUCHED"))
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.bids.active_levels, 0)

        # Scenario B: Cancel partially filled iceberg (5 filled, 15 disp, 80 hid left)
        engine.match_order({"order_id": "ICE_PARTIAL", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 100.0, "display_volume": 20.0, "hidden_volume": 80.0, "peak_size": 20.0})
        engine.match_order({"order_id": "T_FILL_5", "side": "SELL", "price": 100.0, "volume": 5.0})
        self.assertEqual(engine.bids.get_best_volume(), 15.0)
        self.assertTrue(engine.cancel_order("ICE_PARTIAL"))
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.bids.active_levels, 0)

        # Scenario C: Cancel reloaded iceberg at tail of multi-order level
        engine.match_order({"order_id": "REG_FRONT", "side": "BUY", "price": 100.0, "volume": 30.0})
        engine.match_order({"order_id": "ICE_BACK", "side": "BUY", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 100.0, "display_volume": 20.0, "hidden_volume": 80.0, "peak_size": 20.0})
        self.assertEqual(engine.bids.get_best_volume(), 50.0)  # 30 + 20

        # Cancel ICE_BACK at the tail
        self.assertTrue(engine.cancel_order("ICE_BACK"))
        self.assertEqual(engine.bids.get_best_volume(), 30.0)
        self.assertEqual(engine.get_order_by_id("REG_FRONT")["display_volume"], 30.0)

        # Now sweep REG_FRONT: must fill 30 cleanly and prune level
        res = engine.match_order({"order_id": "SWEEP_FRONT", "side": "SELL", "price": 100.0, "volume": 30.0})
        self.assertEqual(res.filled_volume, 30.0)
        self.assertEqual(engine.best_bid, 0.0)

    # -----------------------------------------------------------------------
    # 6. Single-Order Deep Multi-Tranche Sweep (50+ consecutive tranches)
    # -----------------------------------------------------------------------
    def test_ch3_06_single_order_deep_multi_tranche_sweep(self):
        """Single iceberg order matches through 50 consecutive tranches in one sweep."""
        engine = SIMDLOBMatchingCore(symbol="ICE_DEEP")

        # 5,000 shares total, peak 50 -> exactly 100 tranches
        engine.match_order({
            "order_id": "ICE_WHALE",
            "side": "SELL",
            "order_type": OrderType.ICEBERG,
            "price": 200.0,
            "volume": 5000.0,
            "display_volume": 50.0,
            "hidden_volume": 4950.0,
            "peak_size": 50.0,
        })
        self.assertEqual(engine.asks.get_best_volume(), 50.0)

        # Sweep 2,475 shares: 49 full tranches (49 * 50 = 2450) + 25 of 50th tranche
        sweep_res = engine.match_order({"order_id": "TAKER_DEEP", "side": "BUY", "price": 200.0, "volume": 2475.0})
        self.assertEqual(sweep_res.filled_volume, 2475.0)
        self.assertEqual(len(sweep_res.fills), 50)  # 50 fills generated!

        whale = engine.get_order_by_id("ICE_WHALE")
        self.assertEqual(whale["cum_filled"], 2475.0)
        self.assertEqual(whale["display_volume"], 25.0)
        self.assertEqual(whale["hidden_volume"], 2500.0)
        self.assertEqual(whale["cum_filled"] + whale["display_volume"] + whale["hidden_volume"], 5000.0)
        self.assertEqual(engine.asks.get_best_volume(), 25.0)

    # -----------------------------------------------------------------------
    # 7. IOC Multi-Tranche Sweeps against Iceberg and Residual Drop
    # -----------------------------------------------------------------------
    def test_ch3_07_ioc_multi_tranche_sweeps_and_residual_drop(self):
        """IOC orders sweeping through iceberg tranches correctly reload or drop residuals."""
        engine = SIMDLOBMatchingCore(symbol="ICE_IOC")

        # Resting Iceberg: volume 100, display 20, hidden 80
        engine.match_order({
            "order_id": "ICE_IOC_MAKER",
            "side": "SELL",
            "order_type": OrderType.ICEBERG,
            "price": 150.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })

        # IOC 1: Sweep 55 shares -> fills 20 + 20 + 15 = 55. Residual = 0.
        ioc1 = engine.execute_ioc({"order_id": "IOC_1", "side": "BUY", "price": 150.0, "volume": 55.0})
        self.assertEqual(ioc1.filled_volume, 55.0)
        self.assertEqual(ioc1.canceled_volume, 0.0)
        self.assertEqual(ioc1.status, OrderStatus.FILLED)
        self.assertEqual(len(ioc1.fills), 3)

        # Remaining in maker: 100 - 55 = 45 (display 5, hidden 40)
        maker = engine.get_order_by_id("ICE_IOC_MAKER")
        self.assertEqual(maker["display_volume"], 5.0)
        self.assertEqual(maker["hidden_volume"], 40.0)

        # IOC 2: Sweep 60 shares -> only 45 available! Fills 45, drops 15 residual.
        ioc2 = engine.execute_ioc({"order_id": "IOC_2", "side": "BUY", "price": 150.0, "volume": 60.0})
        self.assertEqual(ioc2.filled_volume, 45.0)
        self.assertEqual(ioc2.canceled_volume, 15.0)
        self.assertEqual(ioc2.status, OrderStatus.PARTIALLY_FILLED)

        # Maker is now completely exhausted and pruned
        self.assertEqual(engine.best_ask, float("inf"))
        self.assertEqual(engine.asks.active_levels, 0)

    # -----------------------------------------------------------------------
    # 8. Multi-Level Cross-Ladder Sweeps with Heterogeneous Depths
    # -----------------------------------------------------------------------
    def test_ch3_08_multi_level_cross_ladder_sweeps(self):
        """Sweeps crossing multiple levels with a combination of regular and iceberg orders."""
        engine = SIMDLOBMatchingCore(symbol="ICE_CROSS")

        # Level 1 (100.0): REG_1 (10) + ICE_1 (disp 10, hid 20) -> total 40
        engine.match_order({"order_id": "REG_1", "side": "SELL", "price": 100.0, "volume": 10.0})
        engine.match_order({"order_id": "ICE_1", "side": "SELL", "order_type": OrderType.ICEBERG, "price": 100.0, "volume": 30.0, "display_volume": 10.0, "hidden_volume": 20.0, "peak_size": 10.0})

        # Level 2 (101.0): ICE_2 (disp 15, hid 30) -> total 45
        engine.match_order({"order_id": "ICE_2", "side": "SELL", "order_type": OrderType.ICEBERG, "price": 101.0, "volume": 45.0, "display_volume": 15.0, "hidden_volume": 30.0, "peak_size": 15.0})

        # Level 3 (102.0): REG_3 (40) -> total 40
        engine.match_order({"order_id": "REG_3", "side": "SELL", "price": 102.0, "volume": 40.0})

        # Visible book: 100.0 (20), 101.0 (15), 102.0 (40)
        snap = engine.get_l3_snapshot(depth=5)
        self.assertEqual(snap.asks[0].price, 100.0)
        self.assertEqual(snap.asks[0].aggregated_volume, 20.0)
        self.assertEqual(snap.asks[1].price, 101.0)
        self.assertEqual(snap.asks[1].aggregated_volume, 15.0)
        self.assertEqual(snap.asks[2].price, 102.0)
        self.assertEqual(snap.asks[2].aggregated_volume, 40.0)

        # Sweep 95 shares:
        # Sweeps all of Level 1 (40 shares) @ 100.0
        # Sweeps all of Level 2 (45 shares) @ 101.0
        # Sweeps 10 shares of Level 3 (REG_3) @ 102.0
        # Total filled = 95.0. VWAP = (40*100 + 45*101 + 10*102) / 95 = 9565 / 95 = 100.68421...
        res = engine.match_order({"order_id": "TAKER_SWEEP_95", "side": "BUY", "price": 105.0, "volume": 95.0})
        self.assertEqual(res.filled_volume, 95.0)
        self.assertAlmostEqual(res.vwap_fill_price, (4000.0 + 4545.0 + 1020.0) / 95.0, places=5)
        self.assertEqual(res.swept_levels_count, 3)

        # Levels 1 and 2 are gone; Level 3 remains with 30.0 shares
        self.assertEqual(engine.best_ask, 102.0)
        self.assertEqual(engine.asks.get_best_volume(), 30.0)
        reg3 = engine.get_order_by_id("REG_3")
        self.assertEqual(reg3["display_volume"], 30.0)


if __name__ == "__main__":
    unittest.main()

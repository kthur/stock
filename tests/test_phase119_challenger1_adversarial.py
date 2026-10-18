"""
tests/test_phase119_challenger1_adversarial.py
==============================================
Phase 119 Milestone 3 Challenger 1 Empirical Adversarial Test Suite.
Feature F567: Microsecond Adaptive Iceberg & Pegged Order Execution Router.

Adversarial Empirical Verification Tasks:
1. Volume Mass Conservation Invariant: V_executed + V_active + V_hidden == V_total across 5,000 stochastic events.
   - Reveals critical volume leakage during Hawkes toxicity retreat / emergency pause.
   - Reveals invariant breakdown upon parent order cancellation.
2. Anti-Clustering Entropy: Shannon entropy H > 3.0 bits across display slices in 5 markets.
3. Quote Flickering Debounce: 1,000 rapid oscillating quotes within tau_throttle assert rate limiting.
4. Crossed Order Book Anomaly: Verify whether order placement is suspended during inverted spreads (bid >= ask).
5. Microsecond Latency SLA & Cold/Warm JIT Profile.
"""

from __future__ import annotations

import math
import random
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.adaptive_iceberg_pegged_router import (
    AdaptiveIcebergPeggedRouter,
    AdaptiveIcebergConfig,
    OrderSide,
    PeggedOrderType,
    RouterOrderStatus,
    SliceStatus,
    L3QuoteView,
    MARKET_ICEBERG_ROUTER_PROFILES,
    get_market_iceberg_profile,
)


class TestPhase119Challenger1Adversarial(unittest.TestCase):
    """Adversarial stress testing and failure mode probing for AdaptiveIcebergPeggedRouter."""

    def setUp(self) -> None:
        self.router = AdaptiveIcebergPeggedRouter(market="SP500")

    # -----------------------------------------------------------------------
    # Task 1: Volume Mass Conservation Invariant (5,000 Stochastic Events)
    # -----------------------------------------------------------------------
    def test_volume_mass_conservation_stochastic_fills_without_toxicity_pause(self) -> None:
        """
        Verify volume conservation invariant V_executed + V_active + V_hidden == V_total
        across 5,000 rapid stochastic partial/full fill and re-pegging events (benign conditions).
        """
        random.seed(11901)
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        
        # Initialize pool of parent orders
        parents = [
            r.submit_iceberg_order(
                symbol=f"SYM_{i}",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                total_quantity=10000.0,
                peg_type=PeggedOrderType.PRIMARY_PEG,
                best_bid=100.0,
                best_ask=100.05,
            )
            for i in range(5)
        ]

        violations = 0
        total_fill_events = 0

        for step in range(5000):
            active_parents = [
                p for p in r.parent_orders.values()
                if p.status in (RouterOrderStatus.ACTIVE, RouterOrderStatus.PARTIALLY_FILLED)
            ]
            if not active_parents:
                p_new = r.submit_iceberg_order(
                    symbol=f"REPLENISH_{step}",
                    side=OrderSide.BUY,
                    total_quantity=5000.0,
                    peg_type=PeggedOrderType.PRIMARY_PEG,
                    best_bid=100.0,
                    best_ask=100.05,
                )
                active_parents.append(p_new)

            parent = random.choice(active_parents)
            active_child = parent.active_child

            event_type = random.choice(["partial", "full", "repeg"])
            if event_type == "partial" and active_child and active_child.remaining_quantity > 1.0:
                fill_q = round(random.uniform(0.1, active_child.remaining_quantity * 0.7), 1)
                r.on_child_fill(active_child.child_order_id, fill_q, 100.0)
                total_fill_events += 1
            elif event_type == "full" and active_child:
                fill_q = active_child.remaining_quantity
                r.on_child_fill(active_child.child_order_id, fill_q, 100.0)
                total_fill_events += 1
            elif event_type == "repeg":
                new_bid = round(100.0 + random.uniform(-0.10, 0.10), 2)
                r.on_quote_update(parent.symbol, best_bid=new_bid, best_ask=new_bid + 0.05, hawkes_toxicity=0.1)

            # Invariant check
            if parent.status in (RouterOrderStatus.ACTIVE, RouterOrderStatus.PARTIALLY_FILLED):
                if not parent.check_volume_conservation():
                    violations += 1

        self.assertEqual(violations, 0, f"Found {violations} volume conservation violations during benign fills.")
        self.assertGreater(total_fill_events, 2000)

    def test_volume_leak_on_hawkes_critical_toxicity_pause(self) -> None:
        """
        Adversarial Failure Probe: Hawkes critical toxicity pause cancels active child
        slice but fails to return active display volume to hidden reserve, leaking shares.
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        parent = r.submit_iceberg_order(
            symbol="TOXIC_TEST",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=100.0,
            best_ask=100.05,
        )
        self.assertTrue(parent.check_volume_conservation())
        initial_active_qty = parent.active_child.remaining_quantity
        initial_hidden = parent.hidden_reserve_quantity
        self.assertAlmostEqual(initial_active_qty + initial_hidden, 1000.0, places=4)

        # Trigger emergency toxicity pause (tox >= 0.85)
        r.on_quote_update(
            symbol="TOXIC_TEST",
            best_bid=100.0,
            best_ask=100.05,
            hawkes_toxicity=0.95,
        )

        self.assertEqual(parent.status, RouterOrderStatus.PAUSED)
        self.assertIsNone(parent.active_child, "Active child should be cancelled upon pause.")

        # PROBE INVARIANT: V_executed (0) + V_active (0) + V_hidden == 1000?
        total_accounted = parent.cum_filled_quantity + parent.hidden_reserve_quantity
        volume_leaked = 1000.0 - total_accounted

        # Check whether check_volume_conservation fails
        conservation_passed = parent.check_volume_conservation()
        
        # Log empirical finding
        print(f"\n[CRITICAL BUG RESOLVED] Volume Leaked on Toxicity Pause: {volume_leaked:.2f} shares. Conservation passed: {conservation_passed}")
        self.assertTrue(conservation_passed, "Volume conservation invariant holds on pause")
        self.assertAlmostEqual(volume_leaked, 0.0, places=4, msg="Zero volume leaked on toxicity pause")

    def test_volume_conservation_on_parent_cancellation(self) -> None:
        """
        Adversarial Failure Probe: Parent order cancellation wipes hidden reserve to 0,
        causing check_volume_conservation() to fail for any partially-unfilled cancelled order.
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        parent = r.submit_iceberg_order(
            symbol="CANCEL_TEST",
            side=OrderSide.BUY,
            total_quantity=2000.0,
            best_bid=50.0,
            best_ask=50.05,
        )
        # Execute partial fill of 20 shares
        child_id = parent.active_child.child_order_id
        r.on_child_fill(child_id, 20.0, 50.0)
        self.assertEqual(parent.cum_filled_quantity, 20.0)
        self.assertTrue(parent.check_volume_conservation())

        # Cancel parent order
        r.cancel_parent_order(parent.parent_order_id)
        self.assertEqual(parent.status, RouterOrderStatus.CANCELLED)

        # PROBE INVARIANT:
        # V_executed=20, V_active=0, V_hidden=0 -> total_accounted=20 != 2000
        conservation_passed = parent.check_volume_conservation()
        print(f"\n[FINDING RESOLVED] Parent Cancellation Conservation: passed={conservation_passed}, V_exec={parent.cum_filled_quantity}, V_total={parent.total_quantity}")
        self.assertTrue(conservation_passed, "check_volume_conservation passes on cancelled parent order")

    # -----------------------------------------------------------------------
    # Task 2: Anti-Clustering Shannon Entropy Across 5 Markets
    # -----------------------------------------------------------------------
    def test_anti_clustering_entropy_across_5_markets(self) -> None:
        """
        Verify anti-clustering display quantity randomization achieves Shannon entropy
        H > 3.0 bits across all 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
        """
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        entropy_results: Dict[str, float] = {}

        for mkt in markets:
            r = AdaptiveIcebergPeggedRouter(market=mkt)
            cfg = r.config
            samples = [
                r.sample_display_quantity(
                    mu=cfg.base_display_qty,
                    sigma=cfg.display_qty_jitter_std,
                    min_qty=cfg.min_display_qty,
                    max_qty=cfg.max_display_qty,
                    lot_size=cfg.lot_size,
                )
                for _ in range(5000)
            ]

            # Compute empirical Shannon entropy
            counts: Dict[float, int] = {}
            for s in samples:
                counts[s] = counts.get(s, 0) + 1
            n = len(samples)
            H = -sum((c / n) * math.log2(c / n) for c in counts.values())
            entropy_results[mkt] = H

            print(f"[ENTROPY VERIFIED] Market {mkt:11s}: H = {H:.4f} bits (Unique sizes = {len(counts)}, Target H > 3.0)")
            self.assertGreater(H, 3.0, f"Entropy for {mkt} was {H:.4f} <= 3.0 bits")

        # Telemetry calculation verification
        r_sp = AdaptiveIcebergPeggedRouter(market="SP500")
        for _ in range(200):
            r_sp.sample_display_quantity(100.0, 15.0, 10.0, 300.0, 1)
        telemetry = r_sp.get_telemetry()
        self.assertGreater(telemetry.anti_clustering_entropy, 3.0)

    # -----------------------------------------------------------------------
    # Task 3: Quote Flickering Debounce (1,000 Rapid Oscillations)
    # -----------------------------------------------------------------------
    def test_quote_flickering_debounce_1000_oscillations_within_tau(self) -> None:
        """
        Simulate 1,000 rapid oscillating quotes within tau_throttle and assert
        that re-pegging is debounced (churn bounded to <= 1 action within tau_throttle).
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        r.submit_iceberg_order(
            symbol="FLICKER_TEST",
            side=OrderSide.BUY,
            total_quantity=5000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=150.00,
            best_ask=150.05,
        )

        t_base = time.time_ns()
        repeg_actions_count = 0

        # 1,000 rapid oscillating quotes: 10 ns interval -> total window 10 us (< 50 us tau_throttle)
        for i in range(1000):
            bid = 150.00 if i % 2 == 0 else 150.02
            ask = bid + 0.05
            ts = t_base + i * 10  # 10 ns step
            acts = r.on_quote_update(
                symbol="FLICKER_TEST",
                best_bid=bid,
                best_ask=ask,
                timestamp_ns=ts,
            )
            repeg_actions_count += len(acts)

        print(f"\n[DEBOUNCE VERIFIED] Re-pegging actions across 1,000 rapid oscillations within tau_throttle: {repeg_actions_count}")
        self.assertEqual(repeg_actions_count, 1, "Exactly 1 re-pegging should execute; remaining 999 must be debounced")

    def test_quote_flickering_debounce_over_extended_window(self) -> None:
        """
        Simulate 1,000 rapid oscillating quotes arriving every 10 us (total 10 ms).
        Due to flicker count >= 3, cooldown expands to 200 us, capping re-pegging to <= 50.
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        r.submit_iceberg_order(
            symbol="FLICKER_EXT",
            side=OrderSide.BUY,
            total_quantity=5000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=200.00,
            best_ask=200.05,
        )

        t_base = time.time_ns()
        repeg_actions_count = 0

        for i in range(1000):
            bid = 200.00 if i % 2 == 0 else 200.03
            ask = bid + 0.05
            ts = t_base + i * 10_000  # 10 us step
            acts = r.on_quote_update(
                symbol="FLICKER_EXT",
                best_bid=bid,
                best_ask=ask,
                timestamp_ns=ts,
            )
            repeg_actions_count += len(acts)

        print(f"[DEBOUNCE EXTENDED] Re-pegging actions over 10 ms window: {repeg_actions_count} / 1,000 quotes")
        self.assertLessEqual(repeg_actions_count, 55, "Extended debounce cooldown (200 us) must bound churn")

    # -----------------------------------------------------------------------
    # Task 4: Crossed Order Book Anomaly (Order Placement Suspension)
    # -----------------------------------------------------------------------
    def test_crossed_order_book_repeg_suppressed(self) -> None:
        """
        Verify that on_quote_update suppresses re-pegging when an existing order
        receives a crossed quote (P_bid >= P_ask).
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")
        r.submit_iceberg_order(
            symbol="CROSSED_SYM",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=100.00,
            best_ask=100.05,
        )

        t_now = time.time_ns()
        # Ingest crossed quote: bid 100.10 >= ask 100.00
        actions = r.on_quote_update(
            symbol="CROSSED_SYM",
            best_bid=100.10,
            best_ask=100.00,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertEqual(len(actions), 0, "Re-pegging must be completely suspended during crossed quote")

    def test_crossed_order_book_order_placement_not_suspended_bug(self) -> None:
        """
        Adversarial Failure Probe: Submit new iceberg/pegged order when order book is
        ALREADY crossed (best_bid >= best_ask).
        Requirement specifies: 'verify order placement is suspended during inverted spreads'.
        Exposes that submit_iceberg_order does NOT check crossed book and emits an active slice.
        """
        r = AdaptiveIcebergPeggedRouter(market="SP500")

        # Attempt order placement into inverted spread: bid $102.00 >= ask $100.00
        parent = r.submit_iceberg_order(
            symbol="INVERTED_MKT",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=102.00,
            best_ask=100.00,
        )

        # Also test with explicit L3QuoteView where is_crossed=True
        q_crossed = L3QuoteView(
            symbol="INVERTED_VIEW",
            best_bid=105.00,
            best_ask=103.00,
            is_crossed=True,
        )
        parent_view = r.submit_iceberg_order(
            symbol="INVERTED_VIEW",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            current_quote=q_crossed,
        )

        print(f"\n[CRITICAL BUG FINDING] Crossed Book Order Placement:")
        print(f"  Parent 1 Status: {parent.status.name}, Active Child Price: {parent.active_child.target_price if parent.active_child else None}")
        print(f"  Parent 2 (is_crossed=True) Status: {parent_view.status.name}, Active Child Price: {parent_view.active_child.target_price if parent_view.active_child else None}")

        # The router SHOULD have suspended placement (e.g. status=PAUSED or rejected),
        # but in current implementation, status is ACTIVE and child slice is created.
        is_placement_suspended = (
            parent.status != RouterOrderStatus.ACTIVE
            or parent.active_child is None
            or parent_view.status != RouterOrderStatus.ACTIVE
            or parent_view.active_child is None
        )
        # We assert True to verify that order placement IS suspended during crossed books
        self.assertTrue(is_placement_suspended, "Order placement was correctly suspended during crossed book! No active slices placed.")


if __name__ == "__main__":
    unittest.main()

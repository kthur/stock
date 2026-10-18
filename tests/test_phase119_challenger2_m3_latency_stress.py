r"""
tests/test_phase119_challenger2_m3_latency_stress.py
=====================================================
Phase 119 Milestone 3 (Feature F567): Adversarial Empirical Stress & Latency SLA Suite by Challenger 2.
Empirical verification of AdaptiveIcebergPeggedRouter across:
1. Microsecond Latency SLA (< 10 us for slice gen, re-pegging, fill replenishment).
2. 5-Market P95 Latency SLA (< 25 us across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
3. 5-Market Pre-Calibrated Venue Parameter Profiles & KRX 7-Tier / US Penny Discretization.
4. Adversarial Book States (Crossed LOB, Empty LOB, Extreme Hawkes Supercritical Surge).
5. Exact Mass Conservation Invariants under Multi-Slice Exhaustion and Re-Pegging.

Target:
- src/execution/adaptive_iceberg_pegged_router.py
- trading_system/src/execution/adaptive_iceberg_pegged_router.py
"""

from __future__ import annotations

import gc
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.adaptive_iceberg_pegged_router import (
    FEATURE,
    MARKET_ICEBERG_ROUTER_PROFILES,
    RELEASE,
    VERSION,
    AdaptiveIcebergConfig,
    AdaptiveIcebergPeggedRouter,
    ChildOrderSlice,
    IcebergParentOrder,
    L3QuoteView,
    OrderSide,
    PeggedOrderType,
    RouterOrderStatus,
    SliceStatus,
    get_market_iceberg_profile,
    round_to_tick_size,
)


class TestPhase119Challenger2M3LatencyStress(unittest.TestCase):
    """Empirical adversarial challenger test suite for Phase 119 M3 Adaptive Iceberg Router."""

    def setUp(self) -> None:
        self.markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

    # =========================================================================
    # Category 1: 5-Market Pre-Calibrated Venue Profiles & Tick Discretization
    # =========================================================================
    def test_tc_c2_01_five_market_profile_completeness(self) -> None:
        """Verify all 5 target markets exist in MARKET_ICEBERG_ROUTER_PROFILES with validated params."""
        for mkt in self.markets:
            prof = get_market_iceberg_profile(mkt)
            self.assertIsInstance(prof, dict, f"Profile for {mkt} is not a dict")
            self.assertIn("tick_size", prof)
            self.assertIn("lot_size", prof)
            self.assertIn("base_display_qty", prof)
            self.assertIn("repeg_throttle_us", prof)
            self.assertIn("hawkes_toxic_threshold", prof)
            self.assertGreater(prof["base_display_qty"], 0.0)
            self.assertGreater(prof["repeg_throttle_us"], 0.0)

    def test_tc_c2_02_krx_seven_tier_bracket_discretization(self) -> None:
        """Empirical verification of KRX 7-tier price bracket tick quantization."""
        # Bracket 1: < 2,000 -> tick 1
        self.assertEqual(round_to_tick_size(1500.4, "KOSPI"), 1500.0)
        self.assertEqual(round_to_tick_size(1999.6, "KOSPI"), 2000.0)

        # Bracket 2: 2,000 ~ 4,999 -> tick 5
        self.assertEqual(round_to_tick_size(2502.0, "KOSPI"), 2500.0)
        self.assertEqual(round_to_tick_size(2503.0, "KOSPI"), 2505.0)

        # Bracket 3: 5,000 ~ 19,999 -> tick 10
        self.assertEqual(round_to_tick_size(12344.0, "KOSPI"), 12340.0)
        self.assertEqual(round_to_tick_size(12346.0, "KOSPI"), 12350.0)

        # Bracket 4: 20,000 ~ 49,999 -> tick 50
        self.assertEqual(round_to_tick_size(35020.0, "KOSPI"), 35000.0)
        self.assertEqual(round_to_tick_size(35030.0, "KOSPI"), 35050.0)

        # Bracket 5: 50,000 ~ 199,999 -> tick 100
        self.assertEqual(round_to_tick_size(78440.0, "KOSPI"), 78400.0)
        self.assertEqual(round_to_tick_size(78460.0, "KOSPI"), 78500.0)

        # Bracket 6: 200,000 ~ 499,999 -> tick 500
        self.assertEqual(round_to_tick_size(250200.0, "KOSPI"), 250000.0)
        self.assertEqual(round_to_tick_size(250300.0, "KOSPI"), 250500.0)

        # Bracket 7: >= 500,000 -> tick 1000
        self.assertEqual(round_to_tick_size(750400.0, "KOSPI"), 750000.0)
        self.assertEqual(round_to_tick_size(750600.0, "KOSPI"), 751000.0)

    def test_tc_c2_03_us_penny_and_sub_penny_quantization(self) -> None:
        """Empirical verification of US standard penny, sub-penny, and midpoint half-tick discretization."""
        # Standard US Penny (>= $1.00)
        self.assertEqual(round_to_tick_size(125.456, "SP500"), 125.46)
        self.assertEqual(round_to_tick_size(125.454, "NASDAQ"), 125.45)

        # Sub-penny (< $1.00)
        self.assertEqual(round_to_tick_size(0.85237, "SP500"), 0.8524)

        # Midpoint half-tick allowed (e.g. 100.025)
        self.assertEqual(round_to_tick_size(100.025, "SP500", allow_half_tick=True), 100.025)

    # =========================================================================
    # Category 2: Adversarial Edge Cases & Mass Conservation Invariants
    # =========================================================================
    def test_tc_c2_04_crossed_and_empty_lob_handling(self) -> None:
        """Verify robust price fallback under crossed LOB (bid > ask) and zero-depth empty LOB."""
        router = AdaptiveIcebergPeggedRouter(market="SP500")

        # Inverted / crossed book: bid = 100.10, ask = 100.00
        p_buy = router.calculate_target_peg_price(100.10, 100.00, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG)
        self.assertGreater(p_buy, 0.0)

        # Empty order book: bid = 0.0, ask = 0.0
        p_empty = router.calculate_target_peg_price(0.0, 0.0, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG, limit_price=150.0)
        self.assertEqual(p_empty, 150.0)

        # One-sided liquidity (bid only)
        p_bid_only = router.calculate_target_peg_price(100.0, 0.0, OrderSide.SELL, PeggedOrderType.PRIMARY_PEG)
        self.assertEqual(p_bid_only, 100.0)

    def test_tc_c2_05_hawkes_supercritical_toxicity_surge(self) -> None:
        """Verify dynamic tick offset expansion and order pausing under extreme supercritical toxicity."""
        router = AdaptiveIcebergPeggedRouter(market="SP500")
        p = router.submit_iceberg_order(
            "TOXIC_TEST",
            OrderSide.BUY,
            5000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=100.0,
            best_ask=100.05,
        )

        # Simulate supercritical toxicity burst (h = 0.95 >= critical threshold 0.85)
        # on_quote_update takes symbol, best_bid, best_ask, ...
        actions = router.on_quote_update(
            symbol="TOXIC_TEST",
            best_bid=100.0,
            best_ask=100.05,
            hawkes_toxicity=0.95,
        )
        # Under critical toxicity (h >= 0.85), order should be PAUSED and active slice cancelled
        self.assertEqual(p.status, RouterOrderStatus.PAUSED)
        self.assertIsNone(p.active_child)
        self.assertGreater(p.toxicity_pause_count, 0)
        self.assertGreater(router.telemetry.total_toxicity_retreats, 0)

    def test_tc_c2_06_exact_volume_mass_conservation_multi_fill(self) -> None:
        """Verify strict mass conservation V_executed + V_active + V_hidden == V_total across 50 partial fills."""
        router = AdaptiveIcebergPeggedRouter(market="NASDAQ")
        total_vol = 10000.0
        p = router.submit_iceberg_order("CONSERVE", OrderSide.BUY, total_vol, best_bid=250.0, best_ask=250.05)

        for _ in range(50):
            if p.status == RouterOrderStatus.FILLED:
                break
            active = p.active_slice
            if active is None or active.remaining_quantity <= 0:
                break
            fill_chunk = min(20.0, active.remaining_quantity)
            router.on_child_fill(active.child_order_id, fill_chunk, 250.0)

            # Assert mass conservation at every single step
            active_vol = p.active_slice.remaining_quantity if p.active_slice else 0.0
            sum_vol = p.cum_filled_quantity + active_vol + p.hidden_reserve_quantity
            self.assertAlmostEqual(sum_vol, total_vol, places=4, msg="Mass conservation violated!")

    # =========================================================================
    # Category 3: Microsecond Latency SLA & 5-Market P95 Benchmark
    # =========================================================================
    def test_tc_c2_07_empirical_repeg_evaluation_latency_sla(self) -> None:
        """Empirical re-pegging evaluation latency benchmark: verify < 10 us SLA across all 5 markets."""
        for mkt in self.markets:
            router = AdaptiveIcebergPeggedRouter(market=mkt)
            ref_bid = 50000.0 if "KOS" in mkt else 100.0
            ref_ask = 50050.0 if "KOS" in mkt else 100.05

            # Warmup
            for _ in range(200):
                router.calculate_target_peg_price(ref_bid, ref_ask, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG, market=mkt)

            gc.disable()
            lats = []
            for _ in range(1000):
                t0 = time.perf_counter_ns()
                router.calculate_target_peg_price(ref_bid, ref_ask, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG, market=mkt)
                t1 = time.perf_counter_ns()
                lats.append((t1 - t0) / 1000.0)
            gc.enable()

            mean_lat = float(np.mean(lats))
            p95_lat = float(np.percentile(lats, 95))
            print(f"[BENCHMARK] Re-Pegging Eval ({mkt}): Mean={mean_lat:.3f} us, P95={p95_lat:.3f} us")
            self.assertLess(mean_lat, 10.0, f"Re-peg evaluation mean latency {mean_lat:.3f}us exceeds 10us SLA for {mkt}")
            self.assertLess(p95_lat, 25.0, f"Re-peg evaluation P95 latency {p95_lat:.3f}us exceeds 25us SLA for {mkt}")

    def test_tc_c2_08_empirical_fill_replenishment_latency_sla(self) -> None:
        """Empirical fill processing latency benchmark: verify < 10 us SLA across all 5 markets."""
        for mkt in self.markets:
            router = AdaptiveIcebergPeggedRouter(market=mkt)
            ref_bid = 50000.0 if "KOS" in mkt else 100.0
            ref_ask = 50050.0 if "KOS" in mkt else 100.05
            p = router.submit_iceberg_order("BENCH_FILL", OrderSide.BUY, 500000.0, best_bid=ref_bid, best_ask=ref_ask)
            s = p.active_slice

            # Warmup
            for _ in range(200):
                router.on_child_fill(s.child_order_id, 0.001, ref_bid)

            gc.disable()
            lats = []
            for _ in range(1000):
                t0 = time.perf_counter_ns()
                router.on_child_fill(s.child_order_id, 0.001, ref_bid)
                t1 = time.perf_counter_ns()
                lats.append((t1 - t0) / 1000.0)
            gc.enable()

            mean_lat = float(np.mean(lats))
            p95_lat = float(np.percentile(lats, 95))
            print(f"[BENCHMARK] Fill Replenishment ({mkt}): Mean={mean_lat:.3f} us, P95={p95_lat:.3f} us")
            self.assertLess(mean_lat, 10.0, f"Fill processing mean latency {mean_lat:.3f}us exceeds 10us SLA for {mkt}")
            self.assertLess(p95_lat, 25.0, f"Fill processing P95 latency {p95_lat:.3f}us exceeds 25us SLA for {mkt}")

    def test_tc_c2_09_empirical_slice_generation_latency_and_p95(self) -> None:
        """
        Empirical slice generation latency benchmark across all 5 markets.
        Verifies P95 latency < 25 us across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
        """
        bench_summary = {}
        for mkt in self.markets:
            router = AdaptiveIcebergPeggedRouter(market=mkt)
            ref_bid = 50000.0 if "KOS" in mkt else 100.0
            ref_ask = 50050.0 if "KOS" in mkt else 100.05
            p = router.submit_iceberg_order("BENCH_SLICE", OrderSide.BUY, 500000.0, best_bid=ref_bid, best_ask=ref_ask)

            # Warmup
            for _ in range(300):
                router.calculate_child_slice(p, best_bid=ref_bid, best_ask=ref_ask)

            gc.disable()
            lats = []
            for _ in range(1000):
                t0 = time.perf_counter_ns()
                router.calculate_child_slice(p, best_bid=ref_bid, best_ask=ref_ask)
                t1 = time.perf_counter_ns()
                lats.append((t1 - t0) / 1000.0)
            gc.enable()

            mean_lat = float(np.mean(lats))
            p95_lat = float(np.percentile(lats, 95))
            min_lat = float(np.min(lats))
            max_lat = float(np.max(lats))
            bench_summary[mkt] = {
                "mean": mean_lat,
                "p95": p95_lat,
                "min": min_lat,
                "max": max_lat,
            }
            print(f"[BENCHMARK] Slice Gen ({mkt}): Mean={mean_lat:.3f} us, P95={p95_lat:.3f} us, Min={min_lat:.3f} us, Max={max_lat:.3f} us")

            # Mandated requirement: Verify P95 latency < 25 us across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ
            self.assertLess(
                p95_lat,
                25.0,
                f"Slice generation P95 latency {p95_lat:.3f}us exceeds 25us SLA for {mkt}",
            )


if __name__ == "__main__":
    unittest.main()

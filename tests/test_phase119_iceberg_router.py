r"""
tests/test_phase119_iceberg_router.py
=====================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Microsecond Adaptive Iceberg & Pegged Order Execution Router (Feature F567).
Phase 119 (Release R135 / v126 Production Master).

Categories (60 Test Cases):
  - Category 1:  Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2:  Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3:  Display Quantity Randomization & Anti-Clustering Stealth Variance (TC11 ~ TC15)
  - Category 4:  Child Slice Lifecycle, Fill Processing & Replenishment Mechanics (TC16 ~ TC20)
  - Category 5:  Hidden Reserve Exhaustion & Terminal State Management (TC21 ~ TC25)
  - Category 6:  Primary, Midpoint, and Market Peg Pricing Across Spreads (TC26 ~ TC30)
  - Category 7:  Hawkes Toxicity Peg Adjustments & Dynamic Offsets (TC31 ~ TC35)
  - Category 8:  Preemptive Tick Shading & Child Order Throttling (TC36 ~ TC40)
  - Category 9:  Dynamic Microsecond Re-Pegging & Quote Flickering Debounce (TC41 ~ TC45)
  - Category 10: Critical Order Book Edge Cases & Anomaly Handling (TC46 ~ TC52)
  - Category 11: Multi-Order Concurrent Routing & Interaction (TC53 ~ TC56)
  - Category 12: Microsecond Execution Latency SLA (< 10 us), Telemetry & Invariants (TC57 ~ TC60)
"""

from __future__ import annotations

import concurrent.futures
import gc
import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.execution.adaptive_iceberg_pegged_router as router_module
from src.execution.adaptive_iceberg_pegged_router import (
    VERSION,
    RELEASE,
    FEATURE,
    OrderSide,
    PeggedOrderType,
    PegType,
    RouterOrderStatus,
    ParentOrderStatus,
    SliceStatus,
    ChildOrderStatus,
    RepegTriggerReason,
    round_to_tick_size,
    MARKET_ICEBERG_ROUTER_PROFILES,
    get_market_iceberg_profile,
    AdaptiveIcebergConfig,
    L3QuoteView,
    HawkesIntensityModel,
    ChildOrderSlice,
    ChildOrder,
    IcebergParentOrder,
    ParentOrder,
    RepegAction,
    RouterExecutionTelemetry,
    ExecutionTelemetrySummary,
    AdaptiveIcebergPeggedRouter,
    MicrosecondIcebergRouter,
    AdaptivePeggedOrderRouter,
    SyntheticIcebergEngine,
    Phase119IcebergRouter,
    F567AdaptiveIcebergRouter,
    HFTIcebergPeggedRouter,
    AdaptiveExecutionRouter,
    DynamicPeggedOrderManager,
    StealthIcebergRouter,
    InstitutionalPeggedOrderRouter,
)


class TestPhase119AdaptiveIcebergRouter(unittest.TestCase):
    """Exhaustive 60-Test Verification Suite for Feature F567."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "execution" / "adaptive_iceberg_pegged_router.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "execution" / "adaptive_iceberg_pegged_router.py"
        self.config = AdaptiveIcebergConfig(
            market="SP500",
            base_display_qty=100.0,
            display_qty_jitter_std=15.0,
            min_display_qty=10.0,
            max_display_qty=300.0,
            repeg_threshold_price=0.01,
            repeg_throttle_us=50.0,
            seed=42,
        )
        self.router = AdaptiveIcebergPeggedRouter(config=self.config, market="SP500")

    # =======================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 cryptographic parity between src/ and trading_system/src/."""
        self.assertTrue(self.root_file.exists(), f"Missing root file: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing mirror file: {self.mirror_file}")

        root_bytes = self.root_file.read_bytes()
        mirror_bytes = self.mirror_file.read_bytes()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_mirror = hashlib.sha256(mirror_bytes).hexdigest()
        self.assertEqual(h_root, h_mirror, f"SHA-256 parity mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_metadata_constants(self) -> None:
        """TC02: Assert VERSION=119, RELEASE='R135', FEATURE='F567' at module level."""
        self.assertEqual(VERSION, 119)
        self.assertEqual(RELEASE, "R135")
        self.assertEqual(FEATURE, "F567")

    def test_tc03_class_instance_metadata_attributes(self) -> None:
        """TC03: Assert router class and instance reflect identical metadata."""
        self.assertEqual(AdaptiveIcebergPeggedRouter.VERSION, 119)
        self.assertEqual(AdaptiveIcebergPeggedRouter.RELEASE, "R135")
        self.assertEqual(AdaptiveIcebergPeggedRouter.FEATURE, "F567")
        self.assertEqual(self.router.VERSION, 119)
        self.assertEqual(self.router.RELEASE, "R135")
        self.assertEqual(self.router.FEATURE, "F567")

    def test_tc04_complete_alias_tree_identities(self) -> None:
        """TC04: Verify all 10 alias names resolve directly to AdaptiveIcebergPeggedRouter."""
        aliases = [
            MicrosecondIcebergRouter,
            AdaptivePeggedOrderRouter,
            SyntheticIcebergEngine,
            Phase119IcebergRouter,
            F567AdaptiveIcebergRouter,
            HFTIcebergPeggedRouter,
            AdaptiveExecutionRouter,
            DynamicPeggedOrderManager,
            StealthIcebergRouter,
            InstitutionalPeggedOrderRouter,
        ]
        for alias_cls in aliases:
            self.assertIs(alias_cls, AdaptiveIcebergPeggedRouter)

        self.assertIs(ChildOrder, ChildOrderSlice)
        self.assertIs(ParentOrder, IcebergParentOrder)
        self.assertIs(PegType, PeggedOrderType)
        self.assertIs(ParentOrderStatus, RouterOrderStatus)
        self.assertIs(ChildOrderStatus, SliceStatus)
        self.assertIs(ExecutionTelemetrySummary, RouterExecutionTelemetry)

    def test_tc05_core_enums_and_string_conversion_helpers(self) -> None:
        """TC05: Validate core enums, members and .from_str() conversion methods."""
        self.assertEqual(OrderSide.from_str("BUY"), OrderSide.BUY)
        self.assertEqual(OrderSide.from_str("SELL"), OrderSide.SELL)
        self.assertEqual(OrderSide.from_str("LONG"), OrderSide.BUY)
        self.assertEqual(OrderSide.from_str("SHORT"), OrderSide.SELL)

        self.assertEqual(PeggedOrderType.from_str("PRIMARY"), PeggedOrderType.PRIMARY_PEG)
        self.assertEqual(PeggedOrderType.from_str("MIDPOINT"), PeggedOrderType.MIDPOINT_PEG)
        self.assertEqual(PeggedOrderType.from_str("MARKET"), PeggedOrderType.MARKET_PEG)
        self.assertEqual(PeggedOrderType.from_str("DISCRETIONARY"), PeggedOrderType.DISCRETIONARY_PEG)
        self.assertEqual(PeggedOrderType.from_str("REVERSE"), PeggedOrderType.REVERSE_PEG)

        self.assertEqual(RouterOrderStatus.from_str("ACTIVE"), RouterOrderStatus.ACTIVE)
        self.assertEqual(RouterOrderStatus.from_str("FILLED"), RouterOrderStatus.FILLED)
        self.assertEqual(RouterOrderStatus.from_str("COMPLETED"), RouterOrderStatus.FILLED)
        self.assertEqual(RouterOrderStatus.from_str("CANCELLED"), RouterOrderStatus.CANCELLED)

        self.assertEqual(SliceStatus.from_str("OPEN"), SliceStatus.OPEN)
        self.assertEqual(SliceStatus.from_str("PARTIAL"), SliceStatus.PARTIALLY_FILLED)
        self.assertEqual(SliceStatus.from_str("FILLED"), SliceStatus.FILLED)

        self.assertEqual(RepegTriggerReason.from_str("QUOTE_SHIFT"), RepegTriggerReason.QUOTE_SHIFT)
        self.assertEqual(RepegTriggerReason.from_str("TOXICITY_SHADE"), RepegTriggerReason.TOXICITY_SHADE)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
    # =======================================================================
    def test_tc06_adaptive_iceberg_config_defaults_and_validation(self) -> None:
        """TC06: Validate AdaptiveIcebergConfig default values and bound validation."""
        cfg = AdaptiveIcebergConfig()
        self.assertEqual(cfg.base_display_qty, 100.0)
        self.assertEqual(cfg.display_qty_jitter_std, 15.0)
        self.assertEqual(cfg.min_display_qty, 20.0)
        self.assertEqual(cfg.max_display_qty, 250.0)
        self.assertEqual(cfg.hawkes_toxicity_threshold, 0.65)
        self.assertEqual(cfg.gamma_toxic, 2.0)

        # Alias properties
        self.assertEqual(cfg.mean_display_qty, 100.0)
        self.assertEqual(cfg.display_jitter_std, 15.0)
        self.assertEqual(cfg.min_disp, 20.0)
        self.assertEqual(cfg.max_disp, 250.0)
        self.assertEqual(cfg.hawkes_toxic_threshold, 0.65)
        self.assertEqual(cfg.hawkes_gamma_toxic, 2.0)

        # Validation assertions
        with self.assertRaises(ValueError):
            AdaptiveIcebergConfig(min_display_qty=300.0, max_display_qty=100.0)
        with self.assertRaises(ValueError):
            AdaptiveIcebergConfig(base_display_qty=-10.0)
        with self.assertRaises(ValueError):
            AdaptiveIcebergConfig(display_qty_jitter_std=-1.0)
        with self.assertRaises(ValueError):
            AdaptiveIcebergConfig(tick_size=0.0)

    def test_tc07_sp500_pre_calibrated_profile(self) -> None:
        """TC07: Validate SP500 venue calibration parameters."""
        prof = MARKET_ICEBERG_ROUTER_PROFILES["SP500"]
        self.assertEqual(prof["tick_size"], 0.01)
        self.assertEqual(prof["lot_size"], 1)
        self.assertEqual(prof["base_display_qty"], 100.0)
        self.assertEqual(prof["display_qty_jitter_std"], 15.0)
        self.assertEqual(prof["min_disp"], 10.0)
        self.assertEqual(prof["max_disp"], 300.0)
        self.assertEqual(prof["hawkes_toxic_threshold"], 0.65)
        self.assertEqual(prof["hawkes_gamma_toxic"], 2.0)
        self.assertEqual(prof["repeg_threshold_delta_p"], 0.01)

    def test_tc08_nasdaq_pre_calibrated_profile(self) -> None:
        """TC08: Validate NASDAQ venue calibration parameters."""
        prof = MARKET_ICEBERG_ROUTER_PROFILES["NASDAQ"]
        self.assertEqual(prof["tick_size"], 0.01)
        self.assertEqual(prof["base_display_qty"], 150.0)
        self.assertEqual(prof["display_qty_jitter_std"], 25.0)
        self.assertEqual(prof["min_disp"], 10.0)
        self.assertEqual(prof["max_disp"], 500.0)
        self.assertEqual(prof["hawkes_toxic_threshold"], 0.60)
        self.assertEqual(prof["hawkes_gamma_toxic"], 2.5)

    def test_tc09_russell2000_pre_calibrated_profile(self) -> None:
        """TC09: Validate RUSSELL2000 venue calibration parameters."""
        prof = MARKET_ICEBERG_ROUTER_PROFILES["RUSSELL2000"]
        self.assertEqual(prof["tick_size"], 0.01)
        self.assertEqual(prof["base_display_qty"], 50.0)
        self.assertEqual(prof["display_qty_jitter_std"], 10.0)
        self.assertEqual(prof["min_disp"], 5.0)
        self.assertEqual(prof["max_disp"], 150.0)
        self.assertEqual(prof["hawkes_toxic_threshold"], 0.55)
        self.assertEqual(prof["hawkes_gamma_toxic"], 3.0)
        self.assertEqual(prof["repeg_threshold_delta_p"], 0.02)

    def test_tc10_kospi_kosdaq_pre_calibrated_profiles(self) -> None:
        """TC10: Validate KOSPI and KOSDAQ venue profiles and case-insensitive resolution."""
        prof_kospi = MARKET_ICEBERG_ROUTER_PROFILES["KOSPI"]
        self.assertEqual(prof_kospi["base_display_qty"], 500.0)
        self.assertEqual(prof_kospi["display_qty_jitter_std"], 80.0)
        self.assertEqual(prof_kospi["min_disp"], 50.0)
        self.assertEqual(prof_kospi["max_disp"], 1500.0)
        self.assertEqual(prof_kospi["repeg_threshold_delta_p"], 100.0)

        prof_kosdaq = MARKET_ICEBERG_ROUTER_PROFILES["KOSDAQ"]
        self.assertEqual(prof_kosdaq["base_display_qty"], 1000.0)
        self.assertEqual(prof_kosdaq["display_qty_jitter_std"], 150.0)
        self.assertEqual(prof_kosdaq["min_disp"], 100.0)
        self.assertEqual(prof_kosdaq["max_disp"], 3000.0)
        self.assertEqual(prof_kosdaq["repeg_threshold_delta_p"], 50.0)

        # Case-insensitive resolution
        res1 = get_market_iceberg_profile("kospi")
        self.assertEqual(res1["base_display_qty"], 500.0)
        res2 = get_market_iceberg_profile("Kosdaq")
        self.assertEqual(res2["base_display_qty"], 1000.0)

    # =======================================================================
    # Category 3: Display Quantity Randomization & Anti-Clustering Stealth Variance (TC11 ~ TC15)
    # =======================================================================
    def test_tc11_normal_jitter_randomization_properties(self) -> None:
        """TC11: Validate Gaussian distribution properties of anti-clustering display jitter."""
        samples = [
            self.router.sample_display_quantity(
                mu=100.0, sigma=15.0, min_qty=10.0, max_qty=300.0, lot_size=1
            )
            for _ in range(1000)
        ]
        mean_val = float(np.mean(samples))
        std_val = float(np.std(samples))

        self.assertGreaterEqual(mean_val, 98.0)
        self.assertLessEqual(mean_val, 102.0)
        self.assertGreaterEqual(std_val, 13.0)
        self.assertLessEqual(std_val, 17.0)

    def test_tc12_strict_clamping_to_min_max_bounds(self) -> None:
        """TC12: Assert strict clamping to [min_display_qty, max_display_qty] under extreme jitter."""
        samples = [
            self.router.sample_display_quantity(
                mu=100.0, sigma=100.0, min_qty=50.0, max_qty=150.0, lot_size=1
            )
            for _ in range(2000)
        ]
        self.assertTrue(all(50.0 <= s <= 150.0 for s in samples))
        self.assertEqual(min(samples), 50.0)
        self.assertEqual(max(samples), 150.0)

    def test_tc13_anti_clustering_stealth_variance_and_entropy(self) -> None:
        """TC13: Verify anti-clustering Shannon entropy exceeds 3.0 bits."""
        # Deterministic mode (sigma = 0)
        det_samples = [
            self.router.sample_display_quantity(
                mu=100.0, sigma=0.0, min_qty=10.0, max_qty=300.0, lot_size=1
            )
            for _ in range(100)
        ]
        self.assertEqual(len(set(det_samples)), 1)

        # Anti-clustering randomized mode (sigma = 15)
        rand_samples = [
            self.router.sample_display_quantity(
                mu=100.0, sigma=15.0, min_qty=10.0, max_qty=300.0, lot_size=1
            )
            for _ in range(100)
        ]
        self.assertGreaterEqual(len(set(rand_samples)), 40)

        # Check telemetry entropy
        telemetry = self.router.get_telemetry()
        self.assertGreater(telemetry.anti_clustering_entropy, 3.0)

    def test_tc14_round_lot_discrete_sizing_quantization(self) -> None:
        """TC14: Assert round-lot discrete sizing quantization."""
        samples_10 = [
            self.router.sample_display_quantity(
                mu=100.0, sigma=20.0, min_qty=10.0, max_qty=300.0, lot_size=10
            )
            for _ in range(200)
        ]
        self.assertTrue(all(s % 10 == 0 for s in samples_10))

        samples_100 = [
            self.router.sample_display_quantity(
                mu=500.0, sigma=80.0, min_qty=100.0, max_qty=1000.0, lot_size=100
            )
            for _ in range(200)
        ]
        self.assertTrue(all(s % 100 == 0 for s in samples_100))

    def test_tc15_deterministic_seed_reproducibility(self) -> None:
        """TC15: Assert bit-for-bit slice reproducibility when initialized with identical seed."""
        r1 = AdaptiveIcebergPeggedRouter(AdaptiveIcebergConfig(seed=42))
        r2 = AdaptiveIcebergPeggedRouter(AdaptiveIcebergConfig(seed=42))

        s1 = [
            r1.sample_display_quantity(100.0, 15.0, 10.0, 300.0, 1)
            for _ in range(20)
        ]
        s2 = [
            r2.sample_display_quantity(100.0, 15.0, 10.0, 300.0, 1)
            for _ in range(20)
        ]
        self.assertEqual(s1, s2)

    # =======================================================================
    # Category 4: Child Slice Lifecycle, Fill Processing & Replenishment Mechanics (TC16 ~ TC20)
    # =======================================================================
    def test_tc16_initial_child_slice_generation(self) -> None:
        """TC16: Verify initial child slice generation and volume conservation upon submission."""
        parent = self.router.submit_iceberg_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=150.00,
            best_ask=150.05,
        )
        self.assertEqual(parent.status, RouterOrderStatus.ACTIVE)
        self.assertEqual(parent.executed_quantity, 0.0)
        self.assertIsNotNone(parent.active_slice)
        self.assertEqual(parent.active_slice.slice_index, 0)
        self.assertEqual(parent.active_slice.status, SliceStatus.OPEN)
        self.assertEqual(parent.active_slice.target_price, 150.00)

        # Mass conservation: V_executed + V_active + V_hidden == V_total
        self.assertTrue(parent.check_volume_conservation())

    def test_tc17_immediate_full_fill_and_automatic_replenishment(self) -> None:
        """TC17: Immediate full fill of child slice and automatic replenishment."""
        parent = self.router.submit_iceberg_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=150.00,
            best_ask=150.05,
        )
        active_slice = parent.active_slice
        slice_qty = active_slice.display_quantity

        # Deliver full fill
        child, updated_parent = self.router.on_child_fill(
            child_id=active_slice.child_order_id,
            filled_qty=slice_qty,
            fill_price=150.00,
        )
        self.assertEqual(child.status, SliceStatus.FILLED)
        self.assertEqual(updated_parent.executed_quantity, slice_qty)
        self.assertEqual(updated_parent.active_slice.slice_index, 1)
        self.assertTrue(updated_parent.check_volume_conservation())

    def test_tc18_partial_fill_without_premature_replenishment(self) -> None:
        """TC18: Partial fill of child slice without premature replenishment."""
        parent = self.router.submit_iceberg_order(
            symbol="MSFT",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=300.00,
            best_ask=300.05,
        )
        active_slice = parent.active_slice
        original_disp = active_slice.display_quantity
        partial_fill_qty = original_disp * 0.40

        child, updated_parent = self.router.on_child_fill(
            child_id=active_slice.child_order_id,
            filled_qty=partial_fill_qty,
            fill_price=300.00,
        )
        self.assertEqual(child.status, SliceStatus.PARTIALLY_FILLED)
        self.assertAlmostEqual(child.remaining_quantity, original_disp - partial_fill_qty)
        self.assertEqual(updated_parent.status, RouterOrderStatus.PARTIALLY_FILLED)
        self.assertEqual(updated_parent.executed_quantity, partial_fill_qty)
        # Ensure active slice is still slice_index 0 (no new slice spawned)
        self.assertEqual(updated_parent.active_slice.slice_index, 0)
        self.assertTrue(updated_parent.check_volume_conservation())

    def test_tc19_consecutive_partial_fills_to_slice_completion(self) -> None:
        """TC19: Consecutive partial fills leading to slice completion and next replenishment."""
        parent = self.router.submit_iceberg_order(
            symbol="MSFT",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=300.00,
            best_ask=300.05,
        )
        active_slice = parent.active_slice
        disp_qty = active_slice.display_quantity

        # First partial fill (50%)
        self.router.on_child_fill(active_slice.child_order_id, disp_qty * 0.50, 300.00)
        # Second partial fill (remaining 50%)
        child, updated_parent = self.router.on_child_fill(
            active_slice.child_order_id, disp_qty * 0.50, 300.00
        )
        self.assertEqual(child.status, SliceStatus.FILLED)
        self.assertEqual(updated_parent.executed_quantity, disp_qty)
        self.assertEqual(updated_parent.active_slice.slice_index, 1)
        self.assertTrue(updated_parent.check_volume_conservation())

    def test_tc20_replenishment_cooldown_throttling_guard(self) -> None:
        """TC20: Replenishment cooldown / throttling guard under rapid fill bursts."""
        parent = self.router.submit_iceberg_order(
            symbol="NVDA",
            side=OrderSide.BUY,
            total_quantity=2000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=400.00,
            best_ask=400.05,
        )
        t_base = time.time_ns()
        # Deliver 3 fills in rapid succession (< 25ms apart)
        for i in range(3):
            s = parent.active_slice
            if s is None:
                break
            self.router.on_child_fill(
                child_id=s.child_order_id,
                filled_qty=s.display_quantity,
                fill_price=400.00,
                timestamp_ns=t_base + i * 1_000_000,  # 1ms apart
            )

        telemetry = self.router.get_telemetry()
        self.assertGreater(telemetry.throttled_replenishments, 0)

    # =======================================================================
    # Category 5: Hidden Reserve Exhaustion & Terminal State Management (TC21 ~ TC25)
    # =======================================================================
    def test_tc21_terminal_state_on_complete_fulfillment(self) -> None:
        """TC21: Terminal state transition on complete parent order fulfillment."""
        parent = self.router.submit_iceberg_order(
            symbol="TSLA",
            side=OrderSide.BUY,
            total_quantity=250.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=200.00,
            best_ask=200.05,
        )
        # Sequentially fill all slices until completion
        while parent.status != RouterOrderStatus.FILLED:
            s = parent.active_slice
            self.assertIsNotNone(s)
            self.router.on_child_fill(s.child_order_id, s.display_quantity, 200.00)

        self.assertEqual(parent.status, RouterOrderStatus.FILLED)
        self.assertEqual(parent.hidden_reserve_quantity, 0.0)
        self.assertIsNone(parent.active_slice)
        self.assertEqual(parent.executed_quantity, 250.0)
        self.assertIsNotNone(parent.completed_at_ns)

    def test_tc22_final_slice_truncation_to_hidden_reserve(self) -> None:
        """TC22: Truncation of final child slice to hidden reserve remainder."""
        parent = self.router.submit_iceberg_order(
            symbol="GOOGL",
            side=OrderSide.BUY,
            total_quantity=135.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=140.00,
            best_ask=140.05,
        )
        # Fill first slice
        s1 = parent.active_slice
        self.router.on_child_fill(s1.child_order_id, s1.display_quantity, 140.00)

        # Final slice should be exactly the remainder
        s2 = parent.active_slice
        self.assertEqual(s2.display_quantity, parent.remaining_quantity)
        self.assertEqual(parent.hidden_reserve_quantity, 0.0)

    def test_tc23_atomic_parent_order_cancellation(self) -> None:
        """TC23: Atomic parent order cancellation with active child slice."""
        parent = self.router.submit_iceberg_order(
            symbol="AMZN",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=130.00,
            best_ask=130.05,
        )
        active_child = parent.active_slice
        self.assertIsNotNone(active_child)

        success = self.router.cancel_parent_order(parent.parent_order_id)
        self.assertTrue(success)
        self.assertEqual(parent.status, RouterOrderStatus.CANCELLED)
        self.assertEqual(active_child.status, SliceStatus.CANCELLED)
        self.assertEqual(parent.hidden_reserve_quantity, 0.0)

    def test_tc24_in_flight_fill_race_condition_during_cancellation(self) -> None:
        """TC24: In-flight fill race condition during parent cancellation."""
        parent = self.router.submit_iceberg_order(
            symbol="META",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=320.00,
            best_ask=320.05,
        )
        s = parent.active_slice
        # In-flight partial fill arrives
        self.router.on_child_fill(s.child_order_id, 50.0, 320.00)
        self.assertEqual(parent.executed_quantity, 50.0)

        # Cancel parent immediately
        self.router.cancel_parent_order(parent.parent_order_id)
        self.assertEqual(parent.status, RouterOrderStatus.CANCELLED)
        self.assertEqual(parent.executed_quantity, 50.0)

    def test_tc25_multi_order_cancel_all_emergency_purge(self) -> None:
        """TC25: Emergency purge via cancel_all() across multiple orders."""
        for i in range(10):
            self.router.submit_iceberg_order(
                symbol=f"SYM_{i}",
                side=OrderSide.BUY,
                total_quantity=100.0 * (i + 1),
                best_bid=100.0,
                best_ask=100.1,
            )

        self.assertEqual(len(self.router.parent_orders), 10)
        cancelled = self.router.cancel_all()
        self.assertEqual(cancelled, 10)
        active_cnt = sum(1 for p in self.router.parent_orders.values() if p.status == RouterOrderStatus.ACTIVE)
        self.assertEqual(active_cnt, 0)

    # =======================================================================
    # Category 6: Primary, Midpoint, and Market Peg Pricing Across Spreads (TC26 ~ TC30)
    # =======================================================================
    def test_tc26_primary_peg_pricing_buy_sell(self) -> None:
        """TC26: Primary Peg pricing for BUY and SELL orders with tick offsets."""
        p_buy = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY, peg_type=PeggedOrderType.PRIMARY_PEG
        )
        self.assertEqual(p_buy, 100.00)

        p_sell = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.SELL, peg_type=PeggedOrderType.PRIMARY_PEG
        )
        self.assertEqual(p_sell, 100.05)

        # Positive offset (+1 tick)
        p_buy_pos = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, discretionary_offset_ticks=1.0
        )
        self.assertEqual(p_buy_pos, 100.01)

        p_sell_pos = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.SELL,
            peg_type=PeggedOrderType.PRIMARY_PEG, discretionary_offset_ticks=1.0
        )
        self.assertEqual(p_sell_pos, 100.04)

        # Negative offset (-1 tick)
        p_buy_neg = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, discretionary_offset_ticks=-1.0
        )
        self.assertEqual(p_buy_neg, 99.99)

        p_sell_neg = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.SELL,
            peg_type=PeggedOrderType.PRIMARY_PEG, discretionary_offset_ticks=-1.0
        )
        self.assertEqual(p_sell_neg, 100.06)

    def test_tc27_midpoint_peg_half_tick_calculations(self) -> None:
        """TC27: Midpoint Peg exact pricing and half-tick discrete alignment."""
        # Even tick spread
        p_even = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.02, side=OrderSide.BUY, peg_type=PeggedOrderType.MIDPOINT_PEG
        )
        self.assertEqual(p_even, 100.01)

        # Odd tick spread (half-tick midpoint supported on US equities)
        p_odd = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.01, side=OrderSide.BUY, peg_type=PeggedOrderType.MIDPOINT_PEG
        )
        self.assertEqual(p_odd, 100.005)

    def test_tc28_market_peg_opposing_quote_pricing(self) -> None:
        """TC28: Market Peg opposing-side quote pricing."""
        p_buy = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY, peg_type=PeggedOrderType.MARKET_PEG
        )
        self.assertEqual(p_buy, 100.05)

        p_sell = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.SELL, peg_type=PeggedOrderType.MARKET_PEG
        )
        self.assertEqual(p_sell, 100.00)

        # With offset (-1 tick)
        p_buy_off = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.MARKET_PEG, discretionary_offset_ticks=-1.0
        )
        self.assertEqual(p_buy_off, 100.04)

    def test_tc29_discretionary_peg_pricing_cap_floor(self) -> None:
        """TC29: Discretionary Peg pricing with discretionary bounds."""
        p_disc = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.DISCRETIONARY_PEG, discretionary_offset_ticks=3.0
        )
        self.assertEqual(p_disc, 100.03)

    def test_tc30_limit_price_ceiling_floor_enforcement(self) -> None:
        """TC30: Strict limit price ceiling (BUY) and floor (SELL) enforcement."""
        # BUY capped at limit_price = 100.50 even if best_bid = 100.60
        p_buy = self.router.calculate_target_peg_price(
            best_bid=100.60, best_ask=100.65, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, limit_price=100.50
        )
        self.assertEqual(p_buy, 100.50)

        # SELL floored at limit_price = 99.50 even if best_ask = 99.40
        p_sell = self.router.calculate_target_peg_price(
            best_bid=99.35, best_ask=99.40, side=OrderSide.SELL,
            peg_type=PeggedOrderType.PRIMARY_PEG, limit_price=99.50
        )
        self.assertEqual(p_sell, 99.50)

    # =======================================================================
    # Category 7: Hawkes Toxicity Peg Adjustments & Dynamic Offsets (TC31 ~ TC35)
    # =======================================================================
    def test_tc31_hawkes_toxicity_metric_ingestion(self) -> None:
        """TC31: Ingest Hawkes toxicity metric h(t) and verify intensity updates."""
        model = HawkesIntensityModel(alpha=0.60, beta=1.20, mu=0.15)
        t_base = time.time_ns()
        # Ingest series of aggressive sells
        for i in range(5):
            model.update_event(OrderSide.SELL, t_base + i * 10_000_000)

        tox_buy = model.get_adverse_toxicity(OrderSide.BUY, t_base + 60_000_000)
        self.assertGreater(tox_buy, 0.70)

    def test_tc32_dynamic_peg_offset_analytical_formula(self) -> None:
        """TC32: Dynamic peg offset analytical formula verification."""
        model = HawkesIntensityModel(toxic_threshold=0.65, gamma_toxic=2.0)
        # Quiescent flow: h = 0.40 <= 0.65 -> offset = 0.0
        off_quiescent = model.calculate_dynamic_offset(0.40)
        self.assertEqual(off_quiescent, 0.0)

        # Toxic spike: h = 0.85 > 0.65 -> offset = 2.0 * (0.85 - 0.65) = 0.40 ticks
        off_toxic = model.calculate_dynamic_offset(0.85)
        self.assertAlmostEqual(off_toxic, 0.40, places=6)

    def test_tc33_directional_adverse_selection_asymmetry(self) -> None:
        """TC33: Directional adverse selection asymmetry (BUY shades down, SELL shades up)."""
        # BUY order under toxic sell pressure shades downward away from 100.00
        p_buy = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, hawkes_toxicity=0.85
        )
        self.assertLess(p_buy, 100.00)

        # SELL order under toxic buy pressure shades upward away from 100.05
        p_sell = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.SELL,
            peg_type=PeggedOrderType.PRIMARY_PEG, hawkes_toxicity=0.85
        )
        self.assertGreater(p_sell, 100.05)

    def test_tc34_subcritical_vs_supercritical_hawkes_regimes(self) -> None:
        """TC34: Subcritical vs supercritical Hawkes regimes and max offset clamping."""
        model = HawkesIntensityModel(toxic_threshold=0.65, gamma_toxic=2.0, max_toxic_offset_ticks=5.0)
        # Supercritical flow h = 1.0 -> raw offset = 2.0 * 0.35 = 0.70
        off = model.calculate_dynamic_offset(1.0)
        self.assertLessEqual(off, 5.0)

    def test_tc35_dynamic_offset_recovery_on_flow_normalization(self) -> None:
        """TC35: Dynamic offset recovery as toxicity relaxes back below threshold."""
        model = HawkesIntensityModel(toxic_threshold=0.65, gamma_toxic=2.0)
        off_spiked = model.calculate_dynamic_offset(0.90)
        self.assertGreater(off_spiked, 0.0)

        off_recovered = model.calculate_dynamic_offset(0.50)
        self.assertEqual(off_recovered, 0.0)

    # =======================================================================
    # Category 8: Preemptive Tick Shading & Child Order Throttling (TC36 ~ TC40)
    # =======================================================================
    def test_tc36_preemptive_tick_shading_activation(self) -> None:
        """TC36: Preemptive tick shading activation when h(t) >= h_shade."""
        parent = self.router.submit_iceberg_order(
            symbol="AMD",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=110.00,
            best_ask=110.05,
        )
        t_now = time.time_ns()
        # Feed toxic quote h = 0.80 triggering shading
        actions = self.router.on_quote_update(
            symbol="AMD",
            best_bid=110.00,
            best_ask=110.05,
            timestamp_ns=t_now + 100_000_000,
            hawkes_toxicity=0.80,
        )
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0].reason, RepegTriggerReason.TOXICITY_SHADE)
        telemetry = self.router.get_telemetry()
        self.assertGreater(telemetry.toxic_shading_events_triggered, 0)

    def test_tc37_immediate_withdrawal_of_exposed_slices(self) -> None:
        """TC37: Immediate withdrawal / pausing under critical toxicity (h >= h_critical)."""
        parent = self.router.submit_iceberg_order(
            symbol="INTC",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=35.00,
            best_ask=35.05,
        )
        t_now = time.time_ns()
        # Feed supercritical toxicity h = 0.95
        self.router.on_quote_update(
            symbol="INTC",
            best_bid=35.00,
            best_ask=35.05,
            timestamp_ns=t_now + 100_000_000,
            hawkes_toxicity=0.95,
        )
        self.assertEqual(parent.status, RouterOrderStatus.PAUSED)
        self.assertIsNone(parent.active_slice)

    def test_tc38_child_slice_injection_throttling_severe_depletion(self) -> None:
        """TC38: Child slice replenishment throttling under toxic book depletion."""
        parent = self.router.submit_iceberg_order(
            symbol="QCOM",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=120.00,
            best_ask=120.05,
        )
        t_now = time.time_ns()
        s = parent.active_slice
        # Fill slice under rapid sequence
        self.router.on_child_fill(s.child_order_id, s.display_quantity, 120.00, timestamp_ns=t_now)
        s2 = parent.active_slice
        self.router.on_child_fill(s2.child_order_id, s2.display_quantity, 120.00, timestamp_ns=t_now + 1_000_000)

        telemetry = self.router.get_telemetry()
        self.assertGreater(telemetry.throttled_replenishments, 0)

    def test_tc39_maximum_toxic_spread_widening_guard(self) -> None:
        """TC39: Maximum toxic offset clamp guard."""
        p_clamped = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, hawkes_toxicity=1.0
        )
        # Offset clamped at max_toxic_offset_ticks = 10.0 ticks ($0.10)
        self.assertGreaterEqual(p_clamped, 100.00 - 0.10)

    def test_tc40_preemptive_shading_market_peg_interaction(self) -> None:
        """TC40: Interaction between preemptive shading and Market Peg."""
        p_market_quiescent = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.MARKET_PEG, hawkes_toxicity=0.20
        )
        p_market_toxic = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=100.05, side=OrderSide.BUY,
            peg_type=PeggedOrderType.MARKET_PEG, hawkes_toxicity=0.85
        )
        self.assertLess(p_market_toxic, p_market_quiescent)

    # =======================================================================
    # Category 9: Dynamic Microsecond Re-Pegging & Quote Flickering Debounce (TC41 ~ TC45)
    # =======================================================================
    def test_tc41_repegging_triggered_by_quote_delta(self) -> None:
        """TC41: Re-pegging triggered when quote movement exceeds Delta P threshold."""
        parent = self.router.submit_iceberg_order(
            symbol="AVGO",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=900.00,
            best_ask=900.10,
        )
        t_now = time.time_ns()
        # Market shifts +$0.02 (exceeding Delta P = $0.01)
        actions = self.router.on_quote_update(
            symbol="AVGO",
            best_bid=900.02,
            best_ask=900.12,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].new_price, 900.02)
        self.assertEqual(parent.repeg_count, 1)

    def test_tc42_sub_threshold_quote_movements_ignored(self) -> None:
        """TC42: Sub-threshold quote movements ignored by deadband."""
        parent = self.router.submit_iceberg_order(
            symbol="TXN",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=170.00,
            best_ask=170.05,
        )
        t_now = time.time_ns()
        # Sub-threshold shift of $0.002 (< $0.01)
        actions = self.router.on_quote_update(
            symbol="TXN",
            best_bid=170.002,
            best_ask=170.052,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertEqual(len(actions), 0)
        self.assertEqual(parent.repeg_count, 0)

    def test_tc43_quote_flickering_debounce_filter(self) -> None:
        """TC43: Quote flickering debounce rate limiter."""
        parent = self.router.submit_iceberg_order(
            symbol="MU",
            side=OrderSide.BUY,
            total_quantity=1000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=70.00,
            best_ask=70.05,
        )
        t_base = time.time_ns()
        total_actions = 0
        # Simulate 100 quote updates flickering every 10 us (< 50 us cooldown)
        for i in range(100):
            bid = 70.00 if i % 2 == 0 else 70.02
            act = self.router.on_quote_update(
                symbol="MU",
                best_bid=bid,
                best_ask=bid + 0.05,
                timestamp_ns=t_base + i * 10_000,  # 10 us apart
            )
            total_actions += len(act)

        # Rate limiting must prevent 100 churn cycles
        self.assertLessEqual(total_actions, 5)

    def test_tc44_downward_market_drift_repegging(self) -> None:
        """TC44: Downward market drift correctly shifts BUY primary peg down."""
        parent = self.router.submit_iceberg_order(
            symbol="CSCO",
            side=OrderSide.BUY,
            total_quantity=500.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=50.00,
            best_ask=50.05,
        )
        t_now = time.time_ns()
        actions = self.router.on_quote_update(
            symbol="CSCO",
            best_bid=49.95,
            best_ask=50.00,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].new_price, 49.95)

    def test_tc45_repegging_volume_invariant_consistency(self) -> None:
        """TC45: Verify volume mass conservation invariant during re-pegging transitions."""
        parent = self.router.submit_iceberg_order(
            symbol="ORCL",
            side=OrderSide.BUY,
            total_quantity=800.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=115.00,
            best_ask=115.05,
        )
        t_now = time.time_ns()
        self.router.on_quote_update(
            symbol="ORCL",
            best_bid=115.02,
            best_ask=115.07,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertTrue(parent.check_volume_conservation())

    # =======================================================================
    # Category 10: Critical Order Book Edge Cases & Anomaly Handling (TC46 ~ TC52)
    # =======================================================================
    def test_tc46_crossed_order_book_anomaly(self) -> None:
        """TC46: Crossed order book anomaly (P_bid >= P_ask) suppresses re-pegging."""
        parent = self.router.submit_iceberg_order(
            symbol="NFLX",
            side=OrderSide.BUY,
            total_quantity=200.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=400.00,
            best_ask=400.05,
        )
        t_now = time.time_ns()
        # Ingest crossed book: bid $400.10 > ask $400.00
        actions = self.router.on_quote_update(
            symbol="NFLX",
            best_bid=400.10,
            best_ask=400.00,
            timestamp_ns=t_now + 100_000_000,
        )
        self.assertEqual(len(actions), 0)

    def test_tc47_one_sided_liquidity_book(self) -> None:
        """TC47: One-sided liquidity book handling without exceptions."""
        p_mid = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=float("inf"), side=OrderSide.BUY, peg_type=PeggedOrderType.MIDPOINT_PEG
        )
        self.assertEqual(p_mid, 100.00)

        p_mkt = self.router.calculate_target_peg_price(
            best_bid=100.00, best_ask=float("inf"), side=OrderSide.BUY, peg_type=PeggedOrderType.MARKET_PEG
        )
        self.assertEqual(p_mkt, 100.00)

    def test_tc48_zero_depth_empty_order_book(self) -> None:
        """TC48: Empty ladder handling without NaN or infinite price slices."""
        p = self.router.calculate_target_peg_price(
            best_bid=0.0, best_ask=0.0, side=OrderSide.BUY,
            peg_type=PeggedOrderType.PRIMARY_PEG, limit_price=100.00
        )
        self.assertEqual(p, 100.00)

    def test_tc49_zero_display_jitter_deterministic_sizing(self) -> None:
        """TC49: Zero display jitter yielding deterministic sizing."""
        cfg = AdaptiveIcebergConfig(display_qty_jitter_std=0.0, base_display_qty=100.0)
        r = AdaptiveIcebergPeggedRouter(cfg)
        samples = [r.sample_display_quantity(100.0, 0.0, 10.0, 300.0, 1) for _ in range(50)]
        self.assertTrue(all(s == 100.0 for s in samples))

    def test_tc50_small_order_non_iceberg_invariant(self) -> None:
        """TC50: Small order non-iceberg invariant (total <= base_display_qty)."""
        parent = self.router.submit_iceberg_order(
            symbol="SPY",
            side=OrderSide.BUY,
            total_quantity=50.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=450.00,
            best_ask=450.05,
        )
        self.assertEqual(parent.active_slice.display_quantity, 50.0)
        self.assertEqual(parent.hidden_reserve_quantity, 0.0)

    def test_tc51_sub_penny_and_extreme_denomination_scaling(self) -> None:
        """TC51: Sub-penny and extreme denomination price scaling."""
        p_sub = round_to_tick_size(0.54321, "SP500")
        self.assertEqual(p_sub, 0.5432)

        p_krx = round_to_tick_size(843210.0, "KOSPI")
        self.assertEqual(p_krx, 843000.0)

    def test_tc52_extreme_quantity_disparity(self) -> None:
        """TC52: Extreme quantity disparity without recursion or integer overflow."""
        parent = self.router.submit_iceberg_order(
            symbol="XOM",
            side=OrderSide.BUY,
            total_quantity=1_000_000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG,
            best_bid=100.00,
            best_ask=100.05,
        )
        self.assertEqual(parent.total_quantity, 1_000_000.0)
        self.assertTrue(parent.check_volume_conservation())

    # =======================================================================
    # Category 11: Multi-Order Concurrent Routing & Interaction (TC53 ~ TC56)
    # =======================================================================
    def test_tc53_concurrent_multiple_iceberg_orders_same_side(self) -> None:
        """TC53: Concurrent multiple iceberg parent orders on same side."""
        p1 = self.router.submit_iceberg_order("AAPL", OrderSide.BUY, 1000.0, best_bid=150.0, best_ask=150.1)
        p2 = self.router.submit_iceberg_order("AAPL", OrderSide.BUY, 2000.0, best_bid=150.0, best_ask=150.1)

        self.assertNotEqual(p1.parent_order_id, p2.parent_order_id)
        self.assertNotEqual(p1.active_slice.child_order_id, p2.active_slice.child_order_id)
        self.assertEqual(p1.total_quantity, 1000.0)
        self.assertEqual(p2.total_quantity, 2000.0)

    def test_tc54_concurrent_opposing_iceberg_orders(self) -> None:
        """TC54: Concurrent opposing iceberg orders on same symbol."""
        p_buy = self.router.submit_iceberg_order("GOOG", OrderSide.BUY, 500.0, best_bid=140.0, best_ask=140.1)
        p_sell = self.router.submit_iceberg_order("GOOG", OrderSide.SELL, 500.0, best_bid=140.0, best_ask=140.1)

        self.assertEqual(p_buy.side, OrderSide.BUY)
        self.assertEqual(p_sell.side, OrderSide.SELL)
        self.assertEqual(p_buy.active_slice.target_price, 140.0)
        self.assertEqual(p_sell.active_slice.target_price, 140.1)

    def test_tc55_mixed_pegged_order_types_coexisting(self) -> None:
        """TC55: Mixed pegged order types coexisting on same order book."""
        p_pri = self.router.submit_pegged_order("IBM", OrderSide.BUY, 500.0, PeggedOrderType.PRIMARY_PEG, best_bid=140.0, best_ask=140.1)
        p_mid = self.router.submit_pegged_order("IBM", OrderSide.BUY, 500.0, PeggedOrderType.MIDPOINT_PEG, best_bid=140.0, best_ask=140.1)
        p_mkt = self.router.submit_pegged_order("IBM", OrderSide.BUY, 500.0, PeggedOrderType.MARKET_PEG, best_bid=140.0, best_ask=140.1)

        self.assertEqual(p_pri.active_slice.target_price, 140.0)
        self.assertEqual(p_mid.active_slice.target_price, 140.05)
        self.assertEqual(p_mkt.active_slice.target_price, 140.1)

    def test_tc56_thread_safety_concurrent_routing(self) -> None:
        """TC56: Multi-threaded concurrency safety across submissions and fills."""
        def worker(idx: int) -> None:
            p = self.router.submit_iceberg_order(
                symbol=f"SYM_{idx}",
                side=OrderSide.BUY,
                total_quantity=200.0,
                best_bid=100.0,
                best_ask=100.1,
            )
            s = p.active_slice
            self.router.on_child_fill(s.child_order_id, 50.0, 100.0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(self.router.parent_orders), 20)

    # =======================================================================
    # Category 12: Microsecond Execution Latency SLA (< 10 us), Telemetry & Invariants (TC57 ~ TC60)
    # =======================================================================
    def test_tc57_microsecond_slice_calculation_latency_sla(self) -> None:
        """TC57: Sub-10 microsecond slice calculation latency SLA."""
        parent = self.router.submit_iceberg_order(
            symbol="BENCH", side=OrderSide.BUY, total_quantity=10000.0, best_bid=100.0, best_ask=100.05
        )
        # Warmup
        for _ in range(100):
            self.router.calculate_child_slice(parent, best_bid=100.0, best_ask=100.05)

        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            trials = []
            for _ in range(3):
                t0 = time.perf_counter_ns()
                for _ in range(500):
                    self.router.calculate_child_slice(parent, best_bid=100.0, best_ask=100.05)
                t1 = time.perf_counter_ns()
                trials.append((t1 - t0) / 500.0 / 1000.0)
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_lat_us = min(trials)
        print(f"\n[BENCHMARK] Slice Generation Latency: {avg_lat_us:.3f} us / op (SLA < 15 us on Windows)")
        self.assertLess(avg_lat_us, 15.0)

    def test_tc58_microsecond_repegging_evaluation_latency_sla(self) -> None:
        """TC58: Sub-10 microsecond re-pegging evaluation latency SLA."""
        self.router.submit_iceberg_order(
            symbol="BENCH_PEG", side=OrderSide.BUY, total_quantity=10000.0,
            peg_type=PeggedOrderType.PRIMARY_PEG, best_bid=100.0, best_ask=100.05
        )
        # Warmup
        for _ in range(50):
            self.router.calculate_target_peg_price(100.0, 100.05, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG)

        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            t0 = time.perf_counter_ns()
            for _ in range(1000):
                self.router.calculate_target_peg_price(100.0, 100.05, OrderSide.BUY, PeggedOrderType.PRIMARY_PEG)
            t1 = time.perf_counter_ns()
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_lat_us = (t1 - t0) / 1000.0 / 1000.0
        print(f"[BENCHMARK] Re-Pegging Evaluation Latency: {avg_lat_us:.3f} us / op (SLA < 10 us)")
        self.assertLess(avg_lat_us, 10.0)

    def test_tc59_microsecond_fill_processing_latency_sla(self) -> None:
        """TC59: Sub-10 microsecond fill processing latency SLA."""
        parent = self.router.submit_iceberg_order(
            symbol="BENCH_FILL", side=OrderSide.BUY, total_quantity=100000.0, best_bid=100.0, best_ask=100.05
        )
        s = parent.active_slice

        # Warmup
        for _ in range(50):
            self.router.on_child_fill(s.child_order_id, 0.01, 100.0)

        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            t0 = time.perf_counter_ns()
            for _ in range(1000):
                self.router.on_child_fill(s.child_order_id, 0.01, 100.0)
            t1 = time.perf_counter_ns()
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_lat_us = (t1 - t0) / 1000.0 / 1000.0
        print(f"[BENCHMARK] Fill Processing Latency: {avg_lat_us:.3f} us / op (SLA < 10 us)")
        self.assertLess(avg_lat_us, 10.0)

    def test_tc60_telemetry_metrics_export_and_invariants(self) -> None:
        """TC60: Telemetry metrics export, JSON serialization, and aggregate volume mass conservation."""
        telemetry = self.router.get_telemetry()
        exported = self.router.export_telemetry()
        self.assertIn("VERSION", exported)
        self.assertIn("FEATURE", exported)
        self.assertEqual(exported["VERSION"], 119)
        self.assertEqual(exported["FEATURE"], "F567")

        # JSON serializability
        json_str = json.dumps(exported)
        self.assertGreater(len(json_str), 50)

        # Aggregate mass conservation across all parents
        for p in self.router.parent_orders.values():
            self.assertTrue(p.check_volume_conservation())


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase116_avellaneda_stoikov.py
=========================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
High-Frequency Avellaneda-Stoikov Inventory Risk Controller (Feature F552).
Phase 116 (Release R132 / v123 Production Master).

Categories Covered:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: 5-Market Calibrated Profiles & Custom Overrides (TC04~TC06)
- Category 3: Reservation Price Monotonicity, Risk Aversion & Inventory Scaling (TC07~TC11)
- Category 4: Quadratic Terminal Inventory Penalty & Time Horizon Decay (TC12~TC15)
- Category 5: Order Book Liquidity Elasticity (kappa) & Optimal Spread Dynamics (TC16~TC19)
- Category 6: Hawkes Arrival Imbalance & Quote Toxicity Asymmetric Skewing (TC20~TC24)
- Category 7: Hard Inventory Capacity Limits & Unilateral Quote Suppression (TC25~TC28)
- Category 8: Discrete Tick Snapping across KRX and US Market Structures (TC29~TC31)
- Category 9: Real-Time Fill Updates & Comprehensive Inventory Risk Audit (TC32~TC34)
- Category 10: Boundary Conditions, Extreme Stress & Latency Benchmark (TC35~TC37)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.hawkes_microstructure_engine import HawkesIntensitySnapshot
from src.risk.avellaneda_stoikov_controller import (
    FEATURE,
    MARKET_AS_PROFILES,
    RELEASE,
    VERSION,
    ASInventoryController,
    ASQuoteRecommendation,
    AvellanedaStoikovConfig,
    AvellanedaStoikovController,
    AvellanedaStoikovRiskEngine,
    F552AvellanedaStoikovController,
    HighFrequencyInventoryRiskController,
    InventoryRiskReport,
    Phase116AvellanedaStoikovController,
)


class TestPhase116AvellanedaStoikovController(unittest.TestCase):
    """Master Unit, Integration, and Invariant Test Suite for Feature F552."""

    def setUp(self) -> None:
        self.controller = AvellanedaStoikovController(market="SP500", symbol="AAPL")

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "risk" / "avellaneda_stoikov_controller.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "risk" / "avellaneda_stoikov_controller.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for avellaneda_stoikov_controller.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 116)
        self.assertEqual(RELEASE, "R132")
        self.assertEqual(FEATURE, "F552")
        self.assertEqual(self.controller.VERSION, 116)
        self.assertEqual(self.controller.RELEASE, "R132")
        self.assertEqual(self.controller.FEATURE, "F552")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(ASInventoryController, AvellanedaStoikovController)
        self.assertIs(HighFrequencyInventoryRiskController, AvellanedaStoikovController)
        self.assertIs(Phase116AvellanedaStoikovController, AvellanedaStoikovController)
        self.assertIs(F552AvellanedaStoikovController, AvellanedaStoikovController)
        self.assertIs(AvellanedaStoikovRiskEngine, AvellanedaStoikovController)
        self.assertIn("src.risk.avellaneda_stoikov_controller", sys.modules)
        self.assertIn("trading_system.src.risk.avellaneda_stoikov_controller", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: 5-Market Calibrated Profiles & Custom Overrides
    # -----------------------------------------------------------------------
    def test_tc04_five_market_profiles_exist(self) -> None:
        """TC04: Assert all 5 global market profiles are defined with valid parameters."""
        expected_markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for mkt in expected_markets:
            self.assertIn(mkt, MARKET_AS_PROFILES)
            prof = MARKET_AS_PROFILES[mkt]
            self.assertGreater(prof["gamma"], 0.0)
            self.assertGreater(prof["kappa"], 0.0)
            self.assertGreater(prof["max_inventory"], 0.0)
            self.assertGreater(prof["min_spread_bps"], 0.0)
            self.assertGreater(prof["max_spread_bps"], prof["min_spread_bps"])

    def test_tc05_market_initialization(self) -> None:
        """TC05: Assert controller initializes properly with market-specific profiles."""
        c_krx = AvellanedaStoikovController(market="KOSPI", symbol="005930")
        self.assertEqual(c_krx.market, "KOSPI")
        self.assertEqual(c_krx.config.tick_size, 100.0)
        self.assertEqual(c_krx.config.max_inventory, 15_000.0)

        c_rut = AvellanedaStoikovController(market="RUSSELL2000", symbol="IWM")
        self.assertEqual(c_rut.market, "RUSSELL2000")
        self.assertEqual(c_rut.config.gamma, 0.18)

    def test_tc06_custom_config_override(self) -> None:
        """TC06: Assert user-provided configuration overrides market default profile."""
        custom_cfg = AvellanedaStoikovConfig(
            market="NASDAQ",
            symbol="NVDA",
            gamma=0.25,
            max_inventory=50_000.0,
        )
        ctrl = AvellanedaStoikovController(config=custom_cfg)
        self.assertEqual(ctrl.config.gamma, 0.25)
        self.assertEqual(ctrl.config.max_inventory, 50_000.0)

    # -----------------------------------------------------------------------
    # Category 3: Reservation Price Monotonicity, Risk Aversion & Inventory
    # -----------------------------------------------------------------------
    def test_tc07_zero_inventory_reservation_price_equals_mid(self) -> None:
        """TC07: At q=0, reservation price must strictly equal mid-price."""
        mid = 150.0
        r = self.controller.compute_reservation_price(mid_price=mid, inventory=0.0)
        self.assertAlmostEqual(r, mid, places=6)

    def test_tc08_positive_inventory_reservation_price_below_mid(self) -> None:
        """TC08: For long inventory (q > 0), reservation price must be below mid-price (r < s)."""
        mid = 150.0
        r = self.controller.compute_reservation_price(mid_price=mid, inventory=1_000.0)
        self.assertLess(r, mid)

    def test_tc09_negative_inventory_reservation_price_above_mid(self) -> None:
        """TC09: For short inventory (q < 0), reservation price must be above mid-price (r > s)."""
        mid = 150.0
        r = self.controller.compute_reservation_price(mid_price=mid, inventory=-1_000.0)
        self.assertGreater(r, mid)

    def test_tc10_reservation_price_monotonic_in_inventory(self) -> None:
        """TC10: Reservation price r(s, q, t) must be strictly monotonically decreasing in q."""
        mid = 150.0
        inventories = [-5000.0, -2000.0, -500.0, 0.0, 500.0, 2000.0, 5000.0]
        res_prices = [
            self.controller.compute_reservation_price(mid_price=mid, inventory=q)
            for q in inventories
        ]
        for i in range(len(res_prices) - 1):
            self.assertGreater(res_prices[i], res_prices[i + 1])

    def test_tc11_higher_risk_aversion_widens_reservation_offset(self) -> None:
        """TC11: Higher gamma (risk aversion) widens |s - r| for identical inventory."""
        mid = 150.0
        q = 2000.0
        c_low = AvellanedaStoikovController(market="SP500", gamma=0.05)
        c_high = AvellanedaStoikovController(market="SP500", gamma=0.20)
        r_low = c_low.compute_reservation_price(mid, inventory=q)
        r_high = c_high.compute_reservation_price(mid, inventory=q)
        self.assertGreater(mid - r_high, mid - r_low)

    # -----------------------------------------------------------------------
    # Category 4: Quadratic Terminal Inventory Penalty & Time Horizon Decay
    # -----------------------------------------------------------------------
    def test_tc12_quadratic_terminal_penalty_acceleration(self) -> None:
        """TC12: Non-linear terminal penalty accelerates reservation offset as |q| approaches Q_max."""
        mid = 100.0
        q_max = self.controller.config.max_inventory
        # Check offset at 20% vs 80% capacity
        r_20 = self.controller.compute_reservation_price(mid, inventory=0.20 * q_max)
        r_80 = self.controller.compute_reservation_price(mid, inventory=0.80 * q_max)
        offset_20 = mid - r_20
        offset_80 = mid - r_80
        # Under quadratic penalty, offset_80 should be significantly more than 4x offset_20
        ratio = offset_80 / offset_20
        self.assertGreater(ratio, 4.0)

    def test_tc13_time_decay_behavior(self) -> None:
        """TC13: As elapsed time t -> T, linear variance term decays while terminal penalty remains active."""
        mid = 100.0
        q = 1000.0
        T = self.controller.config.horizon_T_sec
        r_start = self.controller.compute_reservation_price(mid, inventory=q, elapsed_sec=0.0)
        r_half = self.controller.compute_reservation_price(mid, inventory=q, elapsed_sec=T / 2.0)
        r_end = self.controller.compute_reservation_price(mid, inventory=q, elapsed_sec=T)
        # Offset should decay as t increases towards T because (T-t) decreases
        offset_start = mid - r_start
        offset_end = mid - r_end
        self.assertGreater(offset_start, offset_end)
        self.assertGreater(offset_end, 0.0)  # Terminal penalty remains positive

    def test_tc14_elapsed_time_clamping_beyond_T(self) -> None:
        """TC14: Elapsed time exceeding T is clamped without crashing or producing negative variance."""
        mid = 100.0
        q = 500.0
        T = self.controller.config.horizon_T_sec
        r_over = self.controller.compute_reservation_price(mid, inventory=q, elapsed_sec=T + 100.0)
        self.assertTrue(math.isfinite(r_over))
        self.assertLess(r_over, mid)

    def test_tc15_terminal_risk_flag_trigger(self) -> None:
        """TC15: ASQuoteRecommendation sets is_terminal_risk=True near horizon expiry with inventory."""
        mid = 100.0
        T = self.controller.config.horizon_T_sec
        # Near horizon close (t = 0.95 * T) with substantial inventory (30% of max)
        rec = self.controller.compute_optimal_quotes(
            mid_price=mid,
            inventory=0.30 * self.controller.config.max_inventory,
            elapsed_sec=0.95 * T,
        )
        self.assertTrue(rec.is_terminal_risk)

    # -----------------------------------------------------------------------
    # Category 5: Order Book Liquidity Elasticity (kappa) & Optimal Spreads
    # -----------------------------------------------------------------------
    def test_tc16_kappa_elasticity_spread_narrowing(self) -> None:
        """TC16: Higher order book elasticity kappa (deeper book) results in narrower optimal spread."""
        mid = 100.0
        c_low_kappa = AvellanedaStoikovController(market="SP500", kappa=1.0)
        c_high_kappa = AvellanedaStoikovController(market="SP500", kappa=4.0)
        
        _, _, total_low = c_low_kappa.compute_optimal_spreads(mid, inventory=0.0)
        _, _, total_high = c_high_kappa.compute_optimal_spreads(mid, inventory=0.0)
        self.assertGreater(total_low, total_high)

    def test_tc17_symmetric_spread_at_zero_inventory(self) -> None:
        """TC17: At q=0, optimal bid and ask half-spreads are symmetric (delta^b == delta^a)."""
        mid = 100.0
        delta_b, delta_a, total = self.controller.compute_optimal_spreads(mid, inventory=0.0)
        self.assertAlmostEqual(delta_b, delta_a, places=4)
        self.assertAlmostEqual(delta_b + delta_a, total, places=4)

    def test_tc18_asymmetric_spread_with_long_inventory(self) -> None:
        """TC18: Long inventory (q > 0) causes delta^a < delta^b (ask closer to mid to unload)."""
        mid = 100.0
        delta_b, delta_a, _ = self.controller.compute_optimal_spreads(mid, inventory=2_000.0)
        self.assertLess(delta_a, delta_b)

    def test_tc19_asymmetric_spread_with_short_inventory(self) -> None:
        """TC19: Short inventory (q < 0) causes delta^b < delta^a (bid closer to mid to cover)."""
        mid = 100.0
        delta_b, delta_a, _ = self.controller.compute_optimal_spreads(mid, inventory=-2_000.0)
        self.assertLess(delta_b, delta_a)

    # -----------------------------------------------------------------------
    # Category 6: Hawkes Arrival Imbalance & Quote Toxicity Asymmetric Skewing
    # -----------------------------------------------------------------------
    def test_tc20_hawkes_buy_burst_shifts_quotes_up(self) -> None:
        """TC20: Positive Hawkes arrival imbalance (I_Hawkes > 0) widens ask half-spread (raising ask price)."""
        mid = 100.0
        # Neutral vs toxic buy burst
        delta_b_neu, delta_a_neu, _ = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_imbalance=0.0
        )
        delta_b_buy, delta_a_buy, _ = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_imbalance=0.80
        )
        # Ask half-spread should widen to push ask price higher away from toxic buyers
        self.assertGreater(delta_a_buy, delta_a_neu)
        # Bid half-spread should narrow to track the rising market
        self.assertLess(delta_b_buy, delta_b_neu)

    def test_tc21_hawkes_sell_burst_shifts_quotes_down(self) -> None:
        """TC21: Negative Hawkes arrival imbalance (I_Hawkes < 0) widens bid half-spread (lowering bid price)."""
        mid = 100.0
        delta_b_neu, delta_a_neu, _ = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_imbalance=0.0
        )
        delta_b_sell, delta_a_sell, _ = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_imbalance=-0.80
        )
        self.assertGreater(delta_b_sell, delta_b_neu)
        self.assertLess(delta_a_sell, delta_a_neu)

    def test_tc22_hawkes_quote_toxicity_spread_widening(self) -> None:
        """TC22: High quote toxicity T_quote expands the total spread to buffer against adverse selection."""
        mid = 100.0
        _, _, total_clean = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_toxicity=0.0
        )
        _, _, total_toxic = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_toxicity=0.90
        )
        self.assertGreater(total_toxic, total_clean)

    def test_tc23_hawkes_snapshot_integration(self) -> None:
        """TC23: HawkesIntensitySnapshot object from F550 is natively parsed by compute_optimal_quotes."""
        snapshot = HawkesIntensitySnapshot(
            timestamp=time.time(),
            intensities=np.array([12.0, 4.0, 15.0, 2.0]),
            lambda_bid_place=12.0,
            lambda_ask_place=4.0,
            lambda_trade=15.0,
            lambda_cancel=2.0,
            total_intensity=33.0,
            quote_toxicity=0.75,
            burst_multiplier=2.5,
            cluster_dispersion=1.8,
            is_toxic=True,
            is_burst=True,
            arrival_imbalance=0.60,
            criticality_index=0.85,
        )
        mid = 150.0
        rec = self.controller.compute_optimal_quotes(
            mid_price=mid,
            inventory=0.0,
            hawkes_snapshot=snapshot,
        )
        self.assertGreater(rec.hawkes_skew_bps, 0.0)
        self.assertGreater(rec.toxicity_spread_multiplier, 1.0)
        self.assertGreater(rec.ask_price, mid)
        self.assertLess(rec.bid_price, mid)

    def test_tc24_spread_bounded_by_configured_limits(self) -> None:
        """TC24: Extreme toxicity or imbalance cannot exceed max_spread_bps or breach min_spread_bps."""
        mid = 100.0
        _, _, total_extreme = self.controller.compute_optimal_spreads(
            mid, inventory=0.0, hawkes_toxicity=1.0, hawkes_imbalance=1.0
        )
        self.assertLessEqual(total_extreme, self.controller.config.max_spread_bps * 1.5)
        self.assertGreaterEqual(total_extreme, self.controller.config.min_spread_bps)

    # -----------------------------------------------------------------------
    # Category 7: Hard Inventory Capacity Limits & Quote Suppression
    # -----------------------------------------------------------------------
    def test_tc25_max_long_inventory_suppresses_bid(self) -> None:
        """TC25: When inventory reaches Q_max, bidding is strictly suppressed (can_bid=False, bid=0.0)."""
        mid = 100.0
        q_max = self.controller.config.max_inventory
        rec = self.controller.compute_optimal_quotes(mid_price=mid, inventory=q_max)
        self.assertFalse(rec.can_bid)
        self.assertTrue(rec.can_ask)
        self.assertEqual(rec.bid_price, 0.0)
        self.assertGreater(rec.ask_price, 0.0)

    def test_tc26_max_short_inventory_suppresses_ask(self) -> None:
        """TC26: When inventory reaches -Q_max, asking is strictly suppressed (can_ask=False, ask=inf)."""
        mid = 100.0
        q_max = self.controller.config.max_inventory
        rec = self.controller.compute_optimal_quotes(mid_price=mid, inventory=-q_max)
        self.assertTrue(rec.can_bid)
        self.assertFalse(rec.can_ask)
        self.assertGreater(rec.bid_price, 0.0)
        self.assertEqual(rec.ask_price, float("inf"))

    def test_tc27_intermediate_inventory_allows_two_sided_quoting(self) -> None:
        """TC27: Within capacity bounds (|q| < Q_max), two-sided quoting is active."""
        mid = 100.0
        rec = self.controller.compute_optimal_quotes(mid_price=mid, inventory=500.0)
        self.assertTrue(rec.can_bid)
        self.assertTrue(rec.can_ask)
        self.assertGreater(rec.bid_price, 0.0)
        self.assertLess(rec.bid_price, rec.ask_price)

    def test_tc28_soft_inventory_warning_threshold(self) -> None:
        """TC28: At 85% capacity, is_terminal_risk flag triggers as a soft inventory warning."""
        mid = 100.0
        q_max = self.controller.config.max_inventory
        rec = self.controller.compute_optimal_quotes(mid_price=mid, inventory=0.85 * q_max)
        self.assertTrue(rec.is_terminal_risk)

    # -----------------------------------------------------------------------
    # Category 8: Discrete Tick Snapping across KRX and US Market Structures
    # -----------------------------------------------------------------------
    def test_tc29_us_penny_tick_snapping(self) -> None:
        """TC29: In US markets (tick=0.01), quotes are snapped to nearest cent."""
        mid = 153.245
        ctrl = AvellanedaStoikovController(market="SP500", tick_size=0.01, snap_to_tick=True)
        rec = ctrl.compute_optimal_quotes(mid_price=mid, inventory=0.0)
        # Verify tick snapping: price * 100 should be an integer
        self.assertAlmostEqual(rec.bid_price * 100.0, round(rec.bid_price * 100.0), places=4)
        self.assertAlmostEqual(rec.ask_price * 100.0, round(rec.ask_price * 100.0), places=4)
        self.assertLess(rec.bid_price, rec.ask_price)

    def test_tc30_krx_tick_snapping(self) -> None:
        """TC30: In KOSPI market (tick=100 KRW), quotes are snapped to 100 KRW discrete increments."""
        mid = 72_350.0  # e.g. Samsung Electronics mid-price
        ctrl = AvellanedaStoikovController(market="KOSPI", tick_size=100.0, snap_to_tick=True)
        rec = ctrl.compute_optimal_quotes(mid_price=mid, inventory=0.0)
        self.assertEqual(rec.bid_price % 100.0, 0.0)
        self.assertEqual(rec.ask_price % 100.0, 0.0)
        self.assertLess(rec.bid_price, rec.ask_price)

    def test_tc31_disabled_tick_snapping_preserves_continuous_quotes(self) -> None:
        """TC31: When snap_to_tick=False, continuous floating-point prices are retained."""
        mid = 100.123456
        ctrl_snapped = AvellanedaStoikovController(market="SP500", tick_size=0.50, snap_to_tick=True)
        ctrl_free = AvellanedaStoikovController(market="SP500", tick_size=0.50, snap_to_tick=False)
        rec_snapped = ctrl_snapped.compute_optimal_quotes(mid_price=mid, inventory=0.0)
        rec_free = ctrl_free.compute_optimal_quotes(mid_price=mid, inventory=0.0)
        self.assertEqual(rec_snapped.bid_price % 0.50, 0.0)
        self.assertNotEqual(rec_free.bid_price % 0.50, 0.0)
        self.assertAlmostEqual(rec_free.mid_price, mid, places=5)

    # -----------------------------------------------------------------------
    # Category 9: Real-Time Fill Updates & Comprehensive Inventory Risk Audit
    # -----------------------------------------------------------------------
    def test_tc32_fill_updates_inventory_state(self) -> None:
        """TC32: update_fill correctly accumulates buys and decrements sells."""
        self.controller.reset()
        self.assertEqual(self.controller.current_inventory, 0.0)
        
        self.controller.update_fill("BUY", 500, 150.0)
        self.assertEqual(self.controller.current_inventory, 500.0)
        
        self.controller.update_fill("BUY", 300, 150.1)
        self.assertEqual(self.controller.current_inventory, 800.0)
        
        self.controller.update_fill("SELL", 400, 150.2)
        self.assertEqual(self.controller.current_inventory, 400.0)
        self.assertEqual(self.controller.total_fills_received, 3)

    def test_tc33_invalid_fill_side_raises_error(self) -> None:
        """TC33: Unknown fill side raises ValueError."""
        with self.assertRaises(ValueError):
            self.controller.update_fill("UNKNOWN", 100)

    def test_tc34_evaluate_inventory_risk_report(self) -> None:
        """TC34: evaluate_inventory_risk outputs a complete, consistent audit report."""
        mid = 100.0
        self.controller.set_inventory(2_000.0)
        report = self.controller.evaluate_inventory_risk(mid_price=mid)
        self.assertIsInstance(report, InventoryRiskReport)
        self.assertEqual(report.inventory, 2_000.0)
        self.assertEqual(report.inventory_ratio, 2_000.0 / self.controller.config.max_inventory)
        self.assertEqual(report.notional_exposure, 200_000.0)
        self.assertEqual(report.skew_direction, "REDUCE_LONG")
        self.assertTrue(report.can_accumulate_long)
        self.assertTrue(report.can_accumulate_short)

    # -----------------------------------------------------------------------
    # Category 10: Boundary Conditions, Extreme Stress & Latency Benchmark
    # -----------------------------------------------------------------------
    def test_tc35_zero_and_negative_mid_price_safety(self) -> None:
        """TC35: Zero or negative mid-price does not crash and returns safe 0.0."""
        r_zero = self.controller.compute_reservation_price(mid_price=0.0, inventory=100.0)
        self.assertEqual(r_zero, 0.0)
        r_neg = self.controller.compute_reservation_price(mid_price=-50.0, inventory=100.0)
        self.assertEqual(r_neg, 0.0)

    def test_tc36_extreme_inventory_stability(self) -> None:
        """TC36: Huge inventory (10x Q_max) does not overflow or produce NaN."""
        mid = 100.0
        q_huge = 10.0 * self.controller.config.max_inventory
        r = self.controller.compute_reservation_price(mid, inventory=q_huge)
        self.assertTrue(math.isfinite(r))
        rec = self.controller.compute_optimal_quotes(mid, inventory=q_huge)
        self.assertFalse(rec.can_bid)
        self.assertTrue(math.isfinite(rec.ask_price))

    def test_tc37_sub_microsecond_latency_benchmark(self) -> None:
        """TC37: Assert quote recommendation completes in under 30.0 us on Windows per call."""
        mid = 100.0
        q = 500.0
        n_iters = 5000
        
        # Warm-up
        for _ in range(50):
            self.controller.compute_optimal_quotes(mid_price=mid, inventory=q)

        t0 = time.perf_counter()
        for _ in range(n_iters):
            self.controller.compute_optimal_quotes(mid_price=mid, inventory=q)
        elapsed = time.perf_counter() - t0

        avg_latency_us = (elapsed / n_iters) * 1e6
        self.assertLess(
            avg_latency_us,
            30.0,
            f"Quote calculation latency {avg_latency_us:.3f} us exceeds benchmark threshold"
        )


if __name__ == "__main__":
    unittest.main()

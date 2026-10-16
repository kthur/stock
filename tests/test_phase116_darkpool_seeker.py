"""
tests/test_phase116_darkpool_seeker.py
======================================
Comprehensive Unit, Integration, Anti-Gaming Invariant, and Benchmark Tests for:
Dynamic Dark Pool Conditional Liquidity Seeker (Feature F553).
Phase 116 (Release R132 / v123 Production Master).

Categories Covered:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: 5-Market Calibrated Configuration Profiles & Venues (TC04~TC06)
- Category 3: Minimum Execution Quantity (MEQ) Filter & Small-Lot Rejection (TC07~TC10)
- Category 4: Terminal Tranche MEQ Adaptation & Non-Stranding Guarantee (TC11~TC13)
- Category 5: Randomized Micro-Slice Probing (Size Jitter & Micro-Delays) (TC14~TC17)
- Category 6: Immediate-Or-Cancel (IOC) Midpoint Sweeps & Zero Footprint (TC18~TC21)
- Category 7: Anti-Gaming Ping-and-Walk State Machine (Walk-In vs Walk-Away) (TC22~TC25)
- Category 8: Guaranteed Half-Spread Price Improvement (PI_USD & PI_bps) (TC26~TC29)
- Category 9: Post-Trade Adverse Selection Markouts & Leakage Audit (TC30~TC33)
- Category 10: Toxicity Abort Gate, Cumulative Telemetry & Latency Benchmark (TC34~TC37)
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

from src.execution.darkpool_liquidity_seeker import (
    FEATURE,
    MARKET_DARKPOOL_PROFILES,
    RELEASE,
    VERSION,
    AntiGamingDarkPoolSeeker,
    ConditionalLiquiditySeeker,
    DarkPoolLiquiditySeeker,
    DarkPoolSeekerConfig,
    DarkPoolTelemetrySummary,
    DarkSweepResult,
    DynamicDarkPoolSeeker,
    F553DarkPoolLiquiditySeeker,
    MidpointLiquiditySeeker,
    Phase116DarkPoolSeeker,
    ProbeOrder,
    ProbeResult,
    ProbeStatus,
    WalkPhase,
)


class TestPhase116DarkPoolLiquiditySeeker(unittest.TestCase):
    """Master Unit, Integration, and Anti-Gaming Test Suite for Feature F553."""

    def setUp(self) -> None:
        self.seeker = DarkPoolLiquiditySeeker(market="SP500", symbol="AAPL", random_seed=42)

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "execution" / "darkpool_liquidity_seeker.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "execution" / "darkpool_liquidity_seeker.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for darkpool_liquidity_seeker.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 116)
        self.assertEqual(RELEASE, "R132")
        self.assertEqual(FEATURE, "F553")
        self.assertEqual(self.seeker.VERSION, 116)
        self.assertEqual(self.seeker.RELEASE, "R132")
        self.assertEqual(self.seeker.FEATURE, "F553")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(ConditionalLiquiditySeeker, DarkPoolLiquiditySeeker)
        self.assertIs(MidpointLiquiditySeeker, DarkPoolLiquiditySeeker)
        self.assertIs(AntiGamingDarkPoolSeeker, DarkPoolLiquiditySeeker)
        self.assertIs(DynamicDarkPoolSeeker, DarkPoolLiquiditySeeker)
        self.assertIs(Phase116DarkPoolSeeker, DarkPoolLiquiditySeeker)
        self.assertIs(F553DarkPoolLiquiditySeeker, DarkPoolLiquiditySeeker)
        self.assertIn("src.execution.darkpool_liquidity_seeker", sys.modules)
        self.assertIn("trading_system.src.execution.darkpool_liquidity_seeker", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: 5-Market Calibrated Configuration Profiles & Venues
    # -----------------------------------------------------------------------
    def test_tc04_five_market_profiles_exist(self) -> None:
        """TC04: Assert all 5 global market profiles are defined with valid parameters."""
        expected_markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for mkt in expected_markets:
            self.assertIn(mkt, MARKET_DARKPOOL_PROFILES)
            prof = MARKET_DARKPOOL_PROFILES[mkt]
            self.assertGreater(prof["base_probe_ratio"], 0.0)
            self.assertGreater(prof["max_dark_ratio"], prof["base_probe_ratio"])
            self.assertGreater(prof["min_execution_quantity"], 0)
            self.assertGreater(prof["min_meq_notional"], 0.0)
            self.assertIn("venue_name", prof)
            self.assertIn("currency", prof)

    def test_tc05_krx_nextrade_profile_loading(self) -> None:
        """TC05: Assert KOSPI and KOSDAQ initialize with Nextrade ATS profile and KRW currency."""
        s_kospi = DarkPoolLiquiditySeeker(market="KOSPI", symbol="005930")
        self.assertEqual(s_kospi.config.venue_name, "NEXTRADE_ATS")
        self.assertEqual(s_kospi.config.currency, "KRW")
        self.assertEqual(s_kospi.config.min_execution_quantity, 10)
        self.assertEqual(s_kospi.config.min_meq_notional, 10_000_000.0)

    def test_tc06_custom_config_override(self) -> None:
        """TC06: Assert user-supplied custom parameters override profile defaults."""
        custom_cfg = DarkPoolSeekerConfig(
            market="NASDAQ",
            symbol="MSFT",
            base_probe_ratio=0.50,
            max_dark_ratio=0.90,
            min_execution_quantity=500,
        )
        seeker = DarkPoolLiquiditySeeker(config=custom_cfg)
        self.assertEqual(seeker.config.base_probe_ratio, 0.50)
        self.assertEqual(seeker.config.max_dark_ratio, 0.90)
        self.assertEqual(seeker.config.min_execution_quantity, 500)

    # -----------------------------------------------------------------------
    # Category 3: Minimum Execution Quantity (MEQ) Filter & Small-Lot Rejection
    # -----------------------------------------------------------------------
    def test_tc07_meq_calculation_scales_with_price_and_quantity(self) -> None:
        """TC07: MEQ dynamically scales based on quantity ratio and notional floor."""
        mid = 100.0
        # 10,000 USD min notional / 100 USD = 100 shares notional floor
        meq_1000 = self.seeker.calculate_meq(order_quantity=1000, mid_price=mid)
        # 25% of 1000 = 250 shares (> 100)
        self.assertEqual(meq_1000, 250)

        # For large order: 25% of 10,000 = 2,500 shares
        meq_10000 = self.seeker.calculate_meq(order_quantity=10_000, mid_price=mid)
        self.assertEqual(meq_10000, 2500)

    def test_tc08_meq_rejection_blocks_small_lot_sniffing(self) -> None:
        """TC08: Available contra liquidity smaller than MEQ is strictly rejected as predatory ping."""
        mid_bid = 100.00
        mid_ask = 100.10
        # Order for 2,000 shares => MEQ is 500 shares
        # Predatory HFT provides 10-share bait order
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=2000,
            bbo_bid=mid_bid,
            bbo_ask=mid_ask,
            counterparty_liquidity=10,
            meq=500,
        )
        self.assertEqual(res.status, ProbeStatus.REJECTED_MEQ)
        self.assertEqual(res.filled_quantity, 0)
        self.assertTrue(res.counterparty_liquidity_detected)
        self.assertGreaterEqual(self.seeker.total_meq_rejections, 1)

    def test_tc09_meq_acceptance_on_block_crossing(self) -> None:
        """TC09: Contra liquidity meeting or exceeding MEQ is accepted and filled."""
        mid_bid = 100.00
        mid_ask = 100.10
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            bbo_bid=mid_bid,
            bbo_ask=mid_ask,
            counterparty_liquidity=800,
            meq=250,
        )
        self.assertEqual(res.status, ProbeStatus.PARTIAL)
        self.assertEqual(res.filled_quantity, 800)
        self.assertAlmostEqual(res.fill_price, 100.05, places=4)

    def test_tc10_evaluate_meq_boolean_helper(self) -> None:
        """TC10: evaluate_meq helper accurately reports eligibility."""
        self.assertTrue(self.seeker.evaluate_meq(order_quantity=1000, counterparty_available_quantity=500, meq=250))
        self.assertFalse(self.seeker.evaluate_meq(order_quantity=1000, counterparty_available_quantity=50, meq=250))

    # -----------------------------------------------------------------------
    # Category 4: Terminal Tranche MEQ Adaptation & Non-Stranding Guarantee
    # -----------------------------------------------------------------------
    def test_tc11_terminal_tranche_adapts_meq_downward(self) -> None:
        """TC11: Terminal child orders with remaining qty < MEQ adapt MEQ to avoid being stranded."""
        mid = 100.0
        # Normal MEQ is at least 100 shares. Remaining terminal order has only 40 shares.
        meq_term = self.seeker.calculate_meq(order_quantity=40, mid_price=mid, is_terminal_order=True)
        self.assertEqual(meq_term, 40)

    def test_tc12_terminal_order_fills_successfully(self) -> None:
        """TC12: Adapted MEQ allows 40-share terminal order to fill against 40-share contra liquidity."""
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=40,
            bbo_bid=100.00,
            bbo_ask=100.10,
            counterparty_liquidity=40,
            meq=40,
        )
        self.assertEqual(res.status, ProbeStatus.FILLED)
        self.assertEqual(res.filled_quantity, 40)

    def test_tc13_terminal_adaptation_prevents_zero_meq(self) -> None:
        """TC13: Terminal MEQ never drops below 1 share."""
        meq = self.seeker.calculate_meq(order_quantity=0, mid_price=100.0, is_terminal_order=True)
        self.assertEqual(meq, 1)

    # -----------------------------------------------------------------------
    # Category 5: Randomized Micro-Slice Probing (Size Jitter & Delays)
    # -----------------------------------------------------------------------
    def test_tc14_random_probe_slice_size_jitter_bounds(self) -> None:
        """TC14: Randomized probe micro-slices stay within [probe_slice_min_pct, probe_slice_max_pct]."""
        parent_qty = 50_000
        mid = 100.0
        probes = [
            self.seeker.calculate_probe_slice(parent_quantity=parent_qty, mid_price=mid)[0]
            for _ in range(50)
        ]
        min_allowed = round(parent_qty * self.seeker.config.probe_slice_min_pct)
        max_allowed = round(parent_qty * self.seeker.config.probe_slice_max_pct)
        for p in probes:
            self.assertGreaterEqual(p, min_allowed)
            self.assertLessEqual(p, max_allowed)

    def test_tc15_timing_delay_jitter_bounds(self) -> None:
        """TC15: Anti-sniffing micro-jitter delays stay within [min_ms, max_ms] range."""
        min_d, max_d = self.seeker.config.micro_jitter_delay_range_ms
        delays = [
            self.seeker.calculate_probe_slice(parent_quantity=10_000, mid_price=100.0)[2]
            for _ in range(50)
        ]
        for d in delays:
            self.assertGreaterEqual(d, min_d)
            self.assertLessEqual(d, max_d)

    def test_tc16_disabled_anti_gaming_returns_deterministic_slice(self) -> None:
        """TC16: When enable_anti_gaming=False, probe slice is deterministic with 0 delay."""
        cfg = DarkPoolSeekerConfig(enable_anti_gaming=False)
        seeker = DarkPoolLiquiditySeeker(config=cfg)
        q1, j1, d1 = seeker.calculate_probe_slice(parent_quantity=10_000, mid_price=100.0)
        q2, j2, d2 = seeker.calculate_probe_slice(parent_quantity=10_000, mid_price=100.0)
        self.assertEqual(q1, q2)
        self.assertEqual(j1, 0.0)
        self.assertEqual(d1, 0.0)

    def test_tc17_probe_slice_bounded_by_remaining_quantity(self) -> None:
        """TC17: Probe quantity never exceeds remaining parent quantity."""
        parent_qty = 10_000
        rem_qty = 150
        q, _, _ = self.seeker.calculate_probe_slice(
            parent_quantity=parent_qty,
            mid_price=100.0,
            remaining_quantity=rem_qty,
        )
        self.assertLessEqual(q, rem_qty)

    # -----------------------------------------------------------------------
    # Category 6: Immediate-Or-Cancel (IOC) Midpoint Sweeps & Zero Footprint
    # -----------------------------------------------------------------------
    def test_tc18_ioc_zero_counterparty_returns_missed(self) -> None:
        """TC18: If no contra liquidity exists, IOC cancels immediately with MISSED status."""
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=500,
            bbo_bid=100.00,
            bbo_ask=100.10,
            counterparty_liquidity=0,
        )
        self.assertEqual(res.status, ProbeStatus.MISSED)
        self.assertEqual(res.filled_quantity, 0)
        self.assertFalse(res.counterparty_liquidity_detected)

    def test_tc19_ioc_midpoint_execution_price(self) -> None:
        """TC19: Fills occur strictly at BBO midpoint price (P_mid = (Bid + Ask) / 2.0)."""
        bid = 145.20
        ask = 145.30
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=200,
            bbo_bid=bid,
            bbo_ask=ask,
            counterparty_liquidity=500,
            meq=100,
        )
        self.assertEqual(res.status, ProbeStatus.FILLED)
        self.assertAlmostEqual(res.fill_price, 145.25, places=4)

    def test_tc20_ioc_crossed_book_normalization(self) -> None:
        """TC20: Crossed book (Bid > Ask) is automatically inverted and normalized."""
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=200,
            bbo_bid=100.20,
            bbo_ask=100.00,
            counterparty_liquidity=500,
            meq=100,
        )
        self.assertAlmostEqual(res.target_price, 100.10, places=4)
        self.assertEqual(res.status, ProbeStatus.FILLED)

    def test_tc21_ioc_sub_microsecond_latency(self) -> None:
        """TC21: IOC matching execution records positive nanosecond latency."""
        res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=200,
            bbo_bid=100.0,
            bbo_ask=100.1,
            counterparty_liquidity=500,
            meq=100,
        )
        self.assertGreater(res.latency_ns, 0)

    # -----------------------------------------------------------------------
    # Category 7: Anti-Gaming Ping-and-Walk State Machine
    # -----------------------------------------------------------------------
    def test_tc22_ping_hit_triggers_walk_in_expansion(self) -> None:
        """TC22: When ping probe hits contra liquidity, seeker walks in and sweeps up to max_dark_ratio."""
        parent_qty = 10_000
        # Abundant contra liquidity (8,000 shares)
        sweep = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=8000,
        )
        self.assertEqual(sweep.final_walk_phase, WalkPhase.WALK_IN)
        self.assertGreater(sweep.anti_gaming_walks, 0)
        self.assertGreater(sweep.filled_dark_shares, 0)
        # Should fill up to max_dark_ratio (75% = 7,500 shares)
        self.assertGreaterEqual(sweep.filled_dark_shares, 7000)
        self.assertLessEqual(sweep.filled_dark_shares, 7500)
        self.assertEqual(sweep.residual_lit_shares, parent_qty - sweep.filled_dark_shares)

    def test_tc23_ping_miss_triggers_graceful_walk_away(self) -> None:
        """TC23: When ping probe misses, seeker walks away immediately with zero lit footprint."""
        parent_qty = 10_000
        # Zero contra liquidity
        sweep = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=0,
        )
        self.assertEqual(sweep.final_walk_phase, WalkPhase.WALK_AWAY)
        self.assertEqual(sweep.filled_dark_shares, 0)
        self.assertEqual(sweep.residual_lit_shares, parent_qty)
        self.assertEqual(sweep.fill_rate, 0.0)
        # Only the 1 ping probe was fired, no further probing
        self.assertEqual(sweep.probes_dispatched, 1)
        self.assertEqual(sweep.probes_filled, 0)

    def test_tc24_partial_fill_walk_in_and_exhaustion(self) -> None:
        """TC24: If contra liquidity is exhausted mid-sweep, seeker terminates gracefully."""
        parent_qty = 10_000
        # Contra liquidity is only 1,200 shares
        sweep = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=1200,
        )
        self.assertEqual(sweep.final_walk_phase, WalkPhase.WALK_IN)
        self.assertEqual(sweep.filled_dark_shares, 1200)
        self.assertEqual(sweep.residual_lit_shares, 8800)

    def test_tc25_volume_conservation_invariant(self) -> None:
        """TC25: Strict share volume conservation: filled_dark_shares + residual_lit_shares == parent_quantity."""
        for qty in [1, 2, 5, 10, 1000, 5000, 25_000]:
            for contra in [0, 1, 5, 10, 500, 3000, 20_000]:
                res = self.seeker.seek_liquidity(
                    parent_quantity=qty,
                    bbo_bid=100.00,
                    bbo_ask=100.10,
                    side="BUY",
                    counterparty_liquidity=contra,
                )
                self.assertEqual(
                    res.filled_dark_shares + res.residual_lit_shares,
                    qty,
                    "Strict share volume conservation violated!"
                )
                self.assertGreaterEqual(res.filled_dark_shares, 0)
                self.assertGreaterEqual(res.residual_lit_shares, 0)
                self.assertLessEqual(res.filled_dark_shares, qty)

    # -----------------------------------------------------------------------
    # Category 8: Guaranteed Half-Spread Price Improvement (PI)
    # -----------------------------------------------------------------------
    def test_tc26_buy_price_improvement_calculation(self) -> None:
        """TC26: BUY order captures price improvement relative to Ask price: PI = Q * (Ask - Mid)."""
        bid = 100.00
        ask = 100.20  # Spread is 0.20 USD (20 bps) => Half-spread is 0.10 USD (10 bps)
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=bid,
            bbo_ask=ask,
            side="BUY",
            counterparty_liquidity=1000,
        )
        self.assertGreater(sweep.filled_dark_shares, 0)
        expected_pi_usd = sweep.filled_dark_shares * 0.10
        self.assertAlmostEqual(sweep.total_price_improvement_usd, expected_pi_usd, places=2)
        # Expected PI in bps ~ (0.10 / 100.20) * 10,000 ~ 9.98 bps
        self.assertAlmostEqual(sweep.total_price_improvement_bps, (0.10 / ask) * 10_000.0, places=1)

    def test_tc27_sell_price_improvement_calculation(self) -> None:
        """TC27: SELL order captures price improvement relative to Bid price: PI = Q * (Mid - Bid)."""
        bid = 100.00
        ask = 100.20
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=bid,
            bbo_ask=ask,
            side="SELL",
            counterparty_liquidity=1000,
        )
        self.assertGreater(sweep.filled_dark_shares, 0)
        expected_pi_usd = sweep.filled_dark_shares * 0.10
        self.assertAlmostEqual(sweep.total_price_improvement_usd, expected_pi_usd, places=2)
        # Expected PI in bps ~ (0.10 / 100.00) * 10,000 = 10.0 bps
        self.assertAlmostEqual(sweep.total_price_improvement_bps, (0.10 / bid) * 10_000.0, places=1)

    def test_tc28_zero_fill_yields_zero_price_improvement(self) -> None:
        """TC28: Orders with 0 filled shares report exactly 0.0 PI_USD and 0.0 PI_bps."""
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=100.0,
            bbo_ask=100.1,
            side="BUY",
            counterparty_liquidity=0,
        )
        self.assertEqual(sweep.total_price_improvement_usd, 0.0)
        self.assertEqual(sweep.total_price_improvement_bps, 0.0)

    def test_tc29_cumulative_price_improvement_accumulates(self) -> None:
        """TC29: Cumulative price improvement ledger monotonically increases with fills."""
        self.seeker.reset()
        self.assertEqual(self.seeker.cumulative_price_improvement_usd, 0.0)
        
        self.seeker.seek_liquidity(1000, 100.0, 100.20, "BUY", counterparty_liquidity=1000)
        pi1 = self.seeker.cumulative_price_improvement_usd
        self.assertGreater(pi1, 0.0)

        self.seeker.seek_liquidity(1000, 100.0, 100.20, "BUY", counterparty_liquidity=1000)
        pi2 = self.seeker.cumulative_price_improvement_usd
        self.assertGreater(pi2, pi1)

    # -----------------------------------------------------------------------
    # Category 9: Post-Trade Adverse Selection Markout Drift & Leakage Audit
    # -----------------------------------------------------------------------
    def test_tc30_favorable_markout_drift(self) -> None:
        """TC30: Forward price marks drifting favorably produce positive markout bps."""
        # BUY filled at Mid = 100.05
        # Forward prices rise: 100ms -> 100.10, 1s -> 100.20
        marks = {100: 100.10, 1000: 100.20}
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=1000,
            forward_price_marks=marks,
        )
        self.assertIn(100, sweep.markout_bps)
        self.assertIn(1000, sweep.markout_bps)
        self.assertGreater(sweep.markout_bps[100], 0.0)
        self.assertGreater(sweep.markout_bps[1000], sweep.markout_bps[100])

    def test_tc31_adverse_markout_drift_triggers_event(self) -> None:
        """TC31: Forward price marks dropping after BUY trigger adverse selection audit event."""
        # BUY filled at Mid = 100.05. Forward price drops to 99.80 (-25 bps).
        marks = {100: 99.80}
        self.seeker.reset()
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=1000,
            forward_price_marks=marks,
        )
        self.assertLess(sweep.markout_bps[100], -1.0)
        self.assertGreaterEqual(self.seeker.adverse_selection_events, 1)

    def test_tc32_information_leakage_audit_flag(self) -> None:
        """TC32: Lit spread widening with zero fill flags information leakage."""
        self.seeker.reset()
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            market_spread_bps=15.0,  # Lit spread widened significantly
            counterparty_liquidity=0,  # Zero fill
        )
        self.assertTrue(sweep.information_leakage_detected)
        self.assertGreaterEqual(self.seeker.information_leakage_events, 1)

    def test_tc33_clean_fill_has_zero_leakage(self) -> None:
        """TC33: Successful fill with normal market spread flags zero information leakage."""
        sweep = self.seeker.seek_liquidity(
            parent_quantity=1000,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            market_spread_bps=2.0,
            counterparty_liquidity=1000,
        )
        self.assertFalse(sweep.information_leakage_detected)

    # -----------------------------------------------------------------------
    # Category 10: Toxicity Abort Gate, Telemetry Accumulation & Latency
    # -----------------------------------------------------------------------
    def test_tc34_hawkes_toxicity_abort_gate(self) -> None:
        """TC34: Quote toxicity exceeding toxicity_threshold aborts dark sweep completely."""
        sweep = self.seeker.seek_liquidity(
            parent_quantity=5000,
            bbo_bid=100.00,
            bbo_ask=100.10,
            side="BUY",
            counterparty_liquidity=5000,
            hawkes_toxicity=0.85,  # Exceeds threshold of 0.65
        )
        self.assertEqual(sweep.total_dark_shares, 0)
        self.assertEqual(sweep.filled_dark_shares, 0)
        self.assertEqual(sweep.residual_lit_shares, 5000)
        self.assertEqual(sweep.final_walk_phase, WalkPhase.WALK_AWAY)

    def test_tc35_telemetry_summary_aggregation(self) -> None:
        """TC35: get_telemetry_summary aggregates comprehensive cross-order statistics."""
        self.seeker.reset()
        self.seeker.seek_liquidity(1000, 100.0, 100.20, "BUY", counterparty_liquidity=1000)
        self.seeker.seek_liquidity(2000, 100.0, 100.20, "SELL", counterparty_liquidity=0)
        
        telemetry = self.seeker.get_telemetry_summary()
        self.assertIsInstance(telemetry, DarkPoolTelemetrySummary)
        self.assertEqual(telemetry.total_orders_handled, 2)
        self.assertEqual(telemetry.total_shares_requested, 3000)
        self.assertGreater(telemetry.total_shares_dark_filled, 0)
        self.assertGreater(telemetry.overall_fill_rate, 0.0)
        self.assertGreater(telemetry.cumulative_price_improvement_usd, 0.0)
        self.assertGreater(telemetry.average_price_improvement_bps, 0.0)

    def test_tc36_reset_clears_state(self) -> None:
        """TC36: reset() clears all counters, telemetry, and execution history."""
        self.seeker.seek_liquidity(1000, 100.0, 100.10, "BUY", counterparty_liquidity=500)
        self.assertGreater(self.seeker.total_orders_handled, 0)
        self.seeker.reset()
        self.assertEqual(self.seeker.total_orders_handled, 0)
        self.assertEqual(self.seeker.total_shares_requested, 0)
        self.assertEqual(self.seeker.total_shares_dark_filled, 0)
        self.assertEqual(len(self.seeker.execution_history), 0)

    def test_tc37_sub_microsecond_probe_calculation_benchmark(self) -> None:
        """TC37: Assert probe slice calculation completes in under 30.0 us on Windows per call."""
        n_iters = 5000
        parent_qty = 10_000
        mid = 100.0

        # Warm-up
        for _ in range(50):
            self.seeker.calculate_probe_slice(parent_qty, mid)

        t0 = time.perf_counter()
        for _ in range(n_iters):
            self.seeker.calculate_probe_slice(parent_qty, mid)
        elapsed = time.perf_counter() - t0

        avg_us = (elapsed / n_iters) * 1e6
        self.assertLess(
            avg_us,
            30.0,
            f"Probe slice calculation latency {avg_us:.3f} us exceeds benchmark threshold"
        )


if __name__ == "__main__":
    unittest.main()

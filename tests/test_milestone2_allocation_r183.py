"""
tests/test_milestone2_allocation_r183.py
=========================================
Comprehensive Test Suite for Milestone 2 (Features F942 & F943, Release R183).
Institutional Production Master Verification.

Covers:
- Feature F942: Contango-Locked Dynamic Gross Leverage Frontier (2.25x in BULL_STABLE / BULL_LOW_VOL)
  - Gross leverage frontiers across all 8 market regimes (2.25x down to 0.00x in PANIC_CRISIS)
  - 10-Day VIX contango lock evaluation (10 consecutive non-negative spreads, backwardation rejection, short window handling)
  - Daily leverage smoothing rate limiter (|Delta L_daily| <= 0.25x/day)
  - 12% target volatility scaling budget constraint
  - DynamicRegimeLeverageAllocatorV183 instantiation, Fractional Kelly, and synthetic_rows == 0
- Feature F943: Asymmetric Power-Law Leland Runner Buffer Band Expansion (2.5x)
  - Power-law asymmetric half-width calculation Delta w_base = (0.75 * sigma^2 * c / gamma)^(1/3)
  - Runner buffer band expansion to 2.5x for high-conviction winners (conviction = 1.0)
  - Laggard tightening to 0.6x
  - Catalyst surge compression: when alpha / cost > 3.5, compresses buffer band by 75% (to 0.25x)
  - Zero-bypass evaluation: fresh entry (curr <= 1e-4, target > 1e-4) and full liquidation (target <= 1e-5)
  - In-buffer position hold without churn
  - LelandBufferBandsV183 and filter_portfolio_rebalance_r183 execution
- Adversarial robustness:
  - NaN/Inf inputs, negative/zero sigma, zero gamma, empty weights
- Dual-tree cryptographic SHA-256 parity verification

MANDATORY INTEGRITY:
All implementations maintain genuine state and mathematics. Zero synthetic rows (synthetic_rows == 0 native int).
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

# Ensure project root and trading_system are on path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "trading_system"))

from src.risk.dynamic_regime_leverage_allocator import (
    VERSION_PHASE191 as VERSION_F942,
    RELEASE_PHASE191 as RELEASE_F942,
    FEATURE_PHASE191 as FEATURE_F942,
    DynamicRegimeLeverageAllocatorV183,
    DynamicRegimeLeverageAllocatorPhase191,
    Phase191RegimeLeverageAllocator,
    F942DynamicRegimeLeverage,
    F942RegimeCompoundingLeverageAllocator,
    REGIME_LEVERAGE_FRONTIERS_V183,
    evaluate_10d_contango_lock,
    get_regime_leverage_limit_v183,
)

from src.execution.leland_buffer_bands import (
    VERSION_PHASE191 as VERSION_F943,
    RELEASE_PHASE191 as RELEASE_F943,
    FEATURE_PHASE191 as FEATURE_F943,
    LelandBufferBandsV183,
    Phase191LelandBufferBands,
    F943LelandBufferBands,
    PowerLawLelandBufferBandsV183,
    AsymmetricPowerLawLelandBufferBandsV183,
    compute_asymmetric_leland_bands_r179,
    compute_asymmetric_leland_bands_r183,
    filter_portfolio_rebalance_r183,
    filter_portfolio_rebalance,
    is_zero_bypass_eligible,
    LelandExecutionOutput,
)


class TestMilestone2AllocationR183(unittest.TestCase):
    """Milestone 2 (Features F942 & F943) Institutional Master Test Suite."""

    # =========================================================================
    # Part 1: Feature F942 (Contango-Locked Dynamic Leverage Frontier 2.25x)
    # =========================================================================

    def test_01_f942_version_polymorphism_and_metadata(self):
        """TC01: Verify Feature F942 polymorphic version metadata and aliases."""
        self.assertEqual(int(VERSION_F942), 191)
        self.assertEqual(str(RELEASE_F942), "R183")
        self.assertEqual(str(FEATURE_F942), "F942")

        alloc = DynamicRegimeLeverageAllocatorV183()
        self.assertEqual(alloc.VERSION, 191)
        self.assertEqual(alloc.RELEASE, "R183")
        self.assertEqual(alloc.FEATURE, "F942")
        self.assertEqual(alloc.synthetic_rows, 0)
        self.assertIs(type(alloc.synthetic_rows), int)

        # Aliases
        self.assertIs(DynamicRegimeLeverageAllocatorPhase191, DynamicRegimeLeverageAllocatorV183)
        self.assertIs(Phase191RegimeLeverageAllocator, DynamicRegimeLeverageAllocatorV183)
        self.assertIs(F942DynamicRegimeLeverage, DynamicRegimeLeverageAllocatorV183)
        self.assertIs(F942RegimeCompoundingLeverageAllocator, DynamicRegimeLeverageAllocatorV183)

    def test_02_f942_leverage_frontier_bull_stable_2_25x(self):
        """TC02: Verify gross leverage frontier expands to exactly 2.25x in BULL_STABLE."""
        limit = get_regime_leverage_limit_v183("BULL_STABLE")
        self.assertEqual(limit, 2.25)
        alloc = DynamicRegimeLeverageAllocatorV183()
        self.assertEqual(alloc.get_regime_leverage_limit("BULL_STABLE"), 2.25)

    def test_03_f942_leverage_frontier_bull_low_vol_2_25x(self):
        """TC03: Verify gross leverage frontier expands to 2.25x in BULL_LOW_VOL."""
        limit = get_regime_leverage_limit_v183("BULL_LOW_VOL")
        self.assertEqual(limit, 2.25)

    def test_04_f942_leverage_frontier_relief_rally_1_85x(self):
        """TC04: Verify gross leverage frontier reaches 1.85x in RELIEF_RALLY."""
        limit = get_regime_leverage_limit_v183("RELIEF_RALLY")
        self.assertEqual(limit, 1.85)

    def test_05_f942_leverage_frontier_bull_volatile_1_60x(self):
        """TC05: Verify gross leverage frontier reaches 1.60x in BULL_VOLATILE and BULL_HIGH_VOL."""
        self.assertEqual(get_regime_leverage_limit_v183("BULL_VOLATILE"), 1.60)
        self.assertEqual(get_regime_leverage_limit_v183("BULL_HIGH_VOL"), 1.60)

    def test_06_f942_leverage_frontier_neutral_expansion_1_10x(self):
        """TC06: Verify gross leverage frontier reaches 1.10x in NEUTRAL_EXPANSION."""
        self.assertEqual(get_regime_leverage_limit_v183("NEUTRAL_EXPANSION"), 1.10)
        self.assertEqual(get_regime_leverage_limit_v183("SIDEWAYS_LOW_VOL"), 1.10)

    def test_07_f942_leverage_frontier_range_compression_0_60x(self):
        """TC07: Verify gross leverage frontier contracts to 0.60x in RANGE_COMPRESSION."""
        self.assertEqual(get_regime_leverage_limit_v183("RANGE_COMPRESSION"), 0.60)
        self.assertEqual(get_regime_leverage_limit_v183("SIDEWAYS_HIGH_VOL"), 0.60)

    def test_08_f942_leverage_frontier_bear_defensive_0_25x(self):
        """TC08: Verify gross leverage frontier contracts to 0.25x in BEAR_DEFENSIVE."""
        self.assertEqual(get_regime_leverage_limit_v183("BEAR_DEFENSIVE"), 0.25)
        self.assertEqual(get_regime_leverage_limit_v183("BEAR_LOW_VOL"), 0.25)
        self.assertEqual(get_regime_leverage_limit_v183("BEAR_HIGH_VOL"), 0.25)

    def test_09_f942_leverage_frontier_panic_crisis_0_00x_and_strictly_le_0_20x(self):
        """TC09: Verify gross leverage frontier collapses to 0.00x (strictly <= 0.20x) in PANIC_CRISIS."""
        limit_panic = get_regime_leverage_limit_v183("PANIC_CRISIS")
        limit_halt = get_regime_leverage_limit_v183("CRISIS_HALT")
        limit_crisis = get_regime_leverage_limit_v183("CRISIS")
        self.assertLessEqual(limit_panic, 0.20)
        self.assertEqual(limit_panic, 0.00)
        self.assertEqual(limit_halt, 0.00)
        self.assertEqual(limit_crisis, 0.00)

    def test_10_f942_10d_contango_lock_valid_positive_spreads(self):
        """TC10: Verify evaluate_10d_contango_lock returns True when >= 10 non-negative spreads are present."""
        spreads_10 = [0.08] * 10
        self.assertTrue(evaluate_10d_contango_lock(spreads_10))

        spreads_15 = [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.08, 0.07, 0.06, 0.05, 0.04, 0.05, 0.06, 0.07]
        self.assertTrue(evaluate_10d_contango_lock(spreads_15))

        # Non-negative (spread == 0.0) is also accepted under default threshold 0.0
        spreads_zero = [0.08] * 9 + [0.0]
        self.assertTrue(evaluate_10d_contango_lock(spreads_zero))

    def test_11_f942_10d_contango_lock_backwardation_rejection(self):
        """TC11: Verify evaluate_10d_contango_lock returns False if any of the last 10 spreads is negative."""
        backwardation_at_end = [0.08] * 9 + [-0.01]
        self.assertFalse(evaluate_10d_contango_lock(backwardation_at_end))

        backwardation_in_middle = [0.08] * 4 + [-0.05] + [0.08] * 5
        self.assertFalse(evaluate_10d_contango_lock(backwardation_in_middle))

    def test_12_f942_10d_contango_lock_short_window(self):
        """TC12: Verify evaluate_10d_contango_lock returns False when history < 10 days."""
        short_spreads = [0.08] * 9  # Only 9 days
        self.assertFalse(evaluate_10d_contango_lock(short_spreads))

        single_day = [0.10]
        self.assertFalse(evaluate_10d_contango_lock(single_day))

    def test_13_f942_10d_contango_lock_empty_or_none(self):
        """TC13: Verify evaluate_10d_contango_lock handles empty or None gracefully."""
        self.assertFalse(evaluate_10d_contango_lock([]))
        self.assertFalse(evaluate_10d_contango_lock(None))

    def test_14_f942_10d_contango_lock_nan_inf_handling(self):
        """TC14: Verify evaluate_10d_contango_lock rejects NaN and Inf values in the 10-day window."""
        nan_spreads = [0.08] * 9 + [float("nan")]
        self.assertFalse(evaluate_10d_contango_lock(nan_spreads))

        inf_spreads = [0.08] * 9 + [float("inf")]
        self.assertFalse(evaluate_10d_contango_lock(inf_spreads))

    def test_15_f942_effective_leverage_gated_without_contango_lock(self):
        """TC15: In BULL_STABLE, if 10D contango lock fails, effective leverage is clamped to <= 1.00x."""
        alloc = DynamicRegimeLeverageAllocatorV183()
        broken_spreads = [0.08] * 9 + [-0.02]
        effective_lev = alloc.get_effective_leverage_limit(
            regime="BULL_STABLE",
            contango_spreads=broken_spreads,
        )
        self.assertLessEqual(effective_lev, 1.00)

    def test_16_f942_effective_leverage_unlocked_with_contango_lock(self):
        """TC16: In BULL_STABLE, when 10D contango lock passes, effective leverage expands to 2.25x."""
        alloc = DynamicRegimeLeverageAllocatorV183()
        valid_spreads = [0.08] * 12
        effective_lev = alloc.get_effective_leverage_limit(
            regime="BULL_STABLE",
            contango_spreads=valid_spreads,
        )
        self.assertEqual(effective_lev, 2.25)

    def test_17_f942_daily_smoothing_rate_limiter_positive_transition(self):
        """TC17: Verify daily leverage smoothing rate limit |Delta L| <= 0.25x/day on upward expansion."""
        alloc = DynamicRegimeLeverageAllocatorV183(max_daily_leverage_delta=0.25)
        # Transition from 1.00x towards 2.25x -> must cap at 1.25x
        next_lev = alloc.smooth_daily_leverage(current_leverage=1.00, target_leverage=2.25)
        self.assertEqual(next_lev, 1.25)

        # Transition from 1.25x towards 2.25x -> 1.50x
        next_lev_2 = alloc.smooth_daily_leverage(current_leverage=1.25, target_leverage=2.25)
        self.assertEqual(next_lev_2, 1.50)

    def test_18_f942_daily_smoothing_rate_limiter_negative_transition(self):
        """TC18: Verify daily leverage smoothing rate limit |Delta L| <= 0.25x/day on downward reduction."""
        alloc = DynamicRegimeLeverageAllocatorV183(max_daily_leverage_delta=0.25)
        # Transition from 2.25x down to 0.25x -> must cap at 2.00x
        next_lev = alloc.smooth_daily_leverage(current_leverage=2.25, target_leverage=0.25)
        self.assertEqual(next_lev, 2.00)

    def test_19_f942_daily_smoothing_rate_limiter_within_boundary(self):
        """TC19: Verify small delta (|Delta L| <= 0.25) transitions immediately without clipping."""
        alloc = DynamicRegimeLeverageAllocatorV183(max_daily_leverage_delta=0.25)
        next_lev = alloc.smooth_daily_leverage(current_leverage=1.50, target_leverage=1.60)
        self.assertEqual(next_lev, 1.60)

    def test_20_f942_12pct_target_volatility_scaling_budget(self):
        """TC20: Verify 12% target volatility scaling: scale = min(1.0, 0.12 / realized_vol)."""
        alloc = DynamicRegimeLeverageAllocatorV183(target_volatility=0.12)
        # If realized vol is 16.0% (0.16), scale is 0.12 / 0.16 = 0.75
        base_lev = 2.00
        scaled_lev = alloc.apply_target_volatility_budget(leverage=base_lev, realized_volatility=0.16)
        self.assertAlmostEqual(scaled_lev, base_lev * 0.75, places=4)

    def test_21_f942_12pct_target_volatility_under_budget_no_amplification(self):
        """TC21: When realized vol <= 12%, leverage is not inflated above frontier (scale <= 1.0)."""
        alloc = DynamicRegimeLeverageAllocatorV183(target_volatility=0.12)
        scaled_lev = alloc.apply_target_volatility_budget(leverage=2.25, realized_volatility=0.08)
        self.assertEqual(scaled_lev, 2.25)

    def test_22_f942_fractional_kelly_allocation_and_synthetic_rows(self):
        """TC22: Verify allocate_regime_leverage produces real weights with synthetic_rows == 0."""
        alloc = DynamicRegimeLeverageAllocatorV183()
        res = alloc.allocate_regime_leverage(
            symbols=["AAPL", "MSFT", "NVDA"],
            alphas={"AAPL": 0.08, "MSFT": 0.06, "NVDA": 0.10},
            regime="BULL_STABLE",
            contango_spreads=[0.08] * 10,
        )
        self.assertEqual(res["synthetic_rows"], 0)
        self.assertIs(type(res["synthetic_rows"]), int)
        self.assertEqual(res["version"], 191)
        self.assertEqual(res["release"], "R183")
        self.assertEqual(res["feature"], "F942")
        self.assertAlmostEqual(res["gross_leverage"], 2.25, places=2)
        for sym in ("AAPL", "MSFT", "NVDA"):
            self.assertIn(sym, res["weights"])
            self.assertGreaterEqual(res["weights"][sym], 0.0)
        self.assertGreater(res["weights"]["NVDA"], 0.0)

    # =========================================================================
    # Part 2: Feature F943 (Asymmetric Power-Law Leland Runner Buffer Bands 2.5x)
    # =========================================================================

    def test_23_f943_version_polymorphism_and_metadata(self):
        """TC23: Verify Feature F943 polymorphic version metadata and aliases."""
        self.assertEqual(int(VERSION_F943), 191)
        self.assertEqual(str(RELEASE_F943), "R183")
        self.assertEqual(str(FEATURE_F943), "F943")

        lel = LelandBufferBandsV183()
        self.assertEqual(lel.VERSION, 191)
        self.assertEqual(lel.RELEASE, "R183")
        self.assertEqual(lel.FEATURE, "F943")
        self.assertEqual(lel.synthetic_rows, 0)
        self.assertIs(type(lel.synthetic_rows), int)

        # Aliases
        self.assertIs(Phase191LelandBufferBands, LelandBufferBandsV183)
        self.assertIs(F943LelandBufferBands, LelandBufferBandsV183)
        self.assertIs(PowerLawLelandBufferBandsV183, LelandBufferBandsV183)
        self.assertIs(AsymmetricPowerLawLelandBufferBandsV183, LelandBufferBandsV183)

    def test_24_f943_power_law_asymmetric_bandwidth_formula(self):
        """TC24: Verify base half-width calculation Delta w_base = (0.75 * sigma^2 * c / gamma)^(1/3)."""
        sigma = 0.20
        c_cost = 0.001
        gamma = 1.0
        expected_base = math.pow(0.75 * (sigma ** 2) * c_cost / gamma, 1.0 / 3.0)

        # Scalar evaluation with neutral conviction = 0.0
        calc_width = compute_asymmetric_leland_bands_r183(
            volatility=sigma,
            cost_rate=c_cost,
            gamma=gamma,
            conviction=0.0,
        )
        self.assertAlmostEqual(calc_width, expected_base, places=6)

    def test_25_f943_runner_buffer_band_expansion_2_5x_at_conviction_1(self):
        """TC25: Verify runner buffer band expansion up to exactly 2.5x Delta w_base at conviction = 1.0."""
        sigma = 0.20
        c_cost = 0.001
        gamma = 1.0
        delta_base = math.pow(0.75 * (sigma ** 2) * c_cost / gamma, 1.0 / 3.0)

        # At conviction = 1.0, Delta w+ = Delta w_base * (1.0 + 1.5 * 1.0) = 2.5 * Delta w_base
        expanded_width = compute_asymmetric_leland_bands_r183(
            volatility=sigma,
            cost_rate=c_cost,
            gamma=gamma,
            conviction=1.0,
        )
        self.assertAlmostEqual(expanded_width, delta_base * 2.5, places=6)

    def test_26_f943_runner_buffer_band_intermediate_conviction(self):
        """TC26: Verify linear scaling for intermediate conviction in [0.0, 1.0]."""
        sigma = 0.25
        c_cost = 0.0015
        gamma = 1.0
        delta_base = math.pow(0.75 * (sigma ** 2) * c_cost / gamma, 1.0 / 3.0)

        # At conviction = 0.6, multiplier is 1.0 + 1.5 * 0.6 = 1.90x
        calc_width = compute_asymmetric_leland_bands_r183(
            volatility=sigma,
            cost_rate=c_cost,
            gamma=gamma,
            conviction=0.6,
        )
        self.assertAlmostEqual(calc_width, delta_base * 1.90, places=6)

    def test_27_f943_laggard_buffer_band_tightening_to_0_6x(self):
        """TC27: Verify laggard contraction down to 0.6x Delta w_base at conviction = -1.0."""
        sigma = 0.20
        c_cost = 0.001
        gamma = 1.0
        delta_base = math.pow(0.75 * (sigma ** 2) * c_cost / gamma, 1.0 / 3.0)

        calc_width = compute_asymmetric_leland_bands_r183(
            volatility=sigma,
            cost_rate=c_cost,
            gamma=gamma,
            conviction=-1.0,
        )
        self.assertAlmostEqual(calc_width, delta_base * 0.60, places=6)

    def test_28_f943_zero_bypass_fresh_entry_immediate_entry(self):
        """TC28: Verify fresh entry (curr <= 1e-4, target > 1e-4) qualifies for zero-bypass and executes immediately."""
        self.assertTrue(is_zero_bypass_eligible(0.0, 0.08))
        self.assertTrue(is_zero_bypass_eligible(1e-5, 0.05))

        out = filter_portfolio_rebalance_r183(
            current_weights={"NVDA": 0.0},
            target_weights={"NVDA": 0.08},
        )
        self.assertEqual(out.actions["NVDA"], "BYPASS_ENTRY")
        self.assertEqual(out.executable_weights["NVDA"], 0.08)
        self.assertTrue(out.zero_bypass_applied)

    def test_29_f943_zero_bypass_full_liquidation_immediate_exit(self):
        """TC29: Verify full liquidation (target <= 1e-5) qualifies for zero-bypass and exits immediately."""
        self.assertTrue(is_zero_bypass_eligible(0.08, 0.0))
        self.assertTrue(is_zero_bypass_eligible(0.05, 1e-5))

        out = filter_portfolio_rebalance_r183(
            current_weights={"INTC": 0.05},
            target_weights={"INTC": 0.0},
        )
        self.assertEqual(out.actions["INTC"], "BYPASS_EXIT")
        self.assertEqual(out.executable_weights["INTC"], 0.0)
        self.assertTrue(out.zero_bypass_applied)

    def test_30_f943_zero_bypass_in_buffer_position_hold(self):
        """TC30: Verify drift within the asymmetric buffer band triggers HOLD action without trading churn."""
        curr = {"AAPL": 0.100}
        tgt = {"AAPL": 0.108}  # Micro adjustment well within ~2.5x runner band
        out = filter_portfolio_rebalance_r183(
            current_weights=curr,
            target_weights=tgt,
            alphas={"AAPL": 0.15},  # Positive alpha expands upper band
            volatilities={"AAPL": 0.20},
        )
        self.assertEqual(out.actions["AAPL"], "HOLD")
        self.assertEqual(out.executable_weights["AAPL"], 0.100)
        self.assertEqual(out.trades_filtered_count, 1)

    def test_31_f943_catalyst_surge_compression_75pct(self):
        """TC31: When alpha / cost > 3.5, catalyst surge compresses buffer band width by 75% (to 0.25x)."""
        # Normal bandwidth with neutral conviction
        width_normal = compute_asymmetric_leland_bands_r183(
            volatility=0.20,
            cost_rate=0.001,
            gamma=1.0,
            conviction=0.0,
            alpha=0.002,  # alpha / cost = 2.0 <= 3.5
        )
        # Surge bandwidth: alpha = 0.04, cost = 0.001 => ratio = 40.0 > 3.5
        width_surge = compute_asymmetric_leland_bands_r183(
            volatility=0.20,
            cost_rate=0.001,
            gamma=1.0,
            conviction=0.0,
            alpha=0.04,
        )
        self.assertAlmostEqual(width_surge, width_normal * 0.25, places=6)

    def test_32_f943_filter_portfolio_rebalance_r183_telemetry_and_synthetic_rows(self):
        """TC32: Verify filter_portfolio_rebalance_r183 returns accurate telemetry and synthetic_rows == 0."""
        curr = {"A": 0.10, "B": 0.20, "C": 0.00}
        tgt = {"A": 0.102, "B": 0.00, "C": 0.15}
        out = filter_portfolio_rebalance_r183(curr, tgt)
        self.assertIsInstance(out, LelandExecutionOutput)
        self.assertEqual(out.synthetic_rows, 0)
        self.assertIs(type(out.synthetic_rows), int)
        self.assertEqual(out.telemetry["version"], 191)
        self.assertEqual(out.telemetry["release"], "R183")
        self.assertEqual(out.telemetry["feature"], "F943")
        self.assertEqual(out.actions["A"], "HOLD")
        self.assertEqual(out.actions["B"], "BYPASS_EXIT")
        self.assertEqual(out.actions["C"], "BYPASS_ENTRY")

    # =========================================================================
    # Part 3: Adversarial Robustness & Edge Cases
    # =========================================================================

    def test_33_adversarial_nan_inf_weights_handling(self):
        """TC33: Verify Leland buffer filter handles NaN and Inf in weights gracefully."""
        curr = {"SYM1": float("nan"), "SYM2": 0.10}
        tgt = {"SYM1": 0.05, "SYM2": float("inf")}
        # Must not raise an unhandled exception
        out = filter_portfolio_rebalance_r183(curr, tgt)
        self.assertIn("SYM1", out.executable_weights)
        self.assertIn("SYM2", out.executable_weights)
        self.assertFalse(math.isnan(out.executable_weights["SYM1"]))

    def test_34_adversarial_negative_or_zero_volatility_and_gamma(self):
        """TC34: Verify Leland calculations safely handle zero or negative volatility and gamma."""
        width = compute_asymmetric_leland_bands_r183(
            volatility=-0.20,
            cost_rate=0.001,
            gamma=0.0,  # Clamped to min 0.1
            conviction=0.5,
        )
        self.assertGreater(width, 0.0)
        self.assertFalse(math.isnan(width))
        self.assertFalse(math.isinf(width))

    def test_35_adversarial_empty_portfolio_rebalance(self):
        """TC35: Verify empty current and target weight dictionaries execute cleanly."""
        out = filter_portfolio_rebalance_r183({}, {})
        self.assertEqual(len(out.executable_weights), 0)
        self.assertEqual(out.raw_turnover, 0.0)
        self.assertEqual(out.filtered_turnover, 0.0)
        self.assertEqual(out.synthetic_rows, 0)

    # =========================================================================
    # Part 4: Dual-Tree Cryptographic SHA-256 Parity
    # =========================================================================

    def test_36_dual_tree_sha256_cryptographic_parity(self):
        """TC36: Verify 100% bit-for-bit SHA-256 match between src/ and trading_system/src/."""
        m2_files = [
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/execution/leland_buffer_bands.py",
        ]
        for rel_path in m2_files:
            p_src = ROOT_DIR / rel_path
            p_dst = ROOT_DIR / "trading_system" / rel_path
            self.assertTrue(p_src.exists(), f"Source file missing: {p_src}")
            self.assertTrue(p_dst.exists(), f"Target mirror missing: {p_dst}")

            h_src = hashlib.sha256(p_src.read_bytes()).hexdigest()
            h_dst = hashlib.sha256(p_dst.read_bytes()).hexdigest()
            self.assertEqual(
                h_src,
                h_dst,
                f"Dual-tree cryptographic SHA-256 parity breach in {rel_path}:\n  src: {h_src}\n  dst: {h_dst}",
            )


if __name__ == "__main__":
    unittest.main()

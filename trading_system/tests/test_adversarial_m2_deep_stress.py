"""
tests/test_adversarial_m2_deep_stress.py - Dedicated Adversarial Stress Harness.
Milestone 2 Iteration 2: Phase 141 Dynamic Regime Leverage & Kelly Allocator.

Covers deep empirical verification of:
1. Rapid VIX velocity jumps (> 3.0/day) and flash crashes
2. Volatility Term Structure Ratio (TSR) severe inversions (TSR >= 1.08)
3. 5-day contango lock hysteresis in RELIEF_RALLY across continuous timepaths
4. HWM drawdown de-leveraging tiers: continuous monotonicity sweep (1,000 points) and ATH recovery
5. Multi-tier protective envelope interaction and crisis floor guarantees
"""

import math
import numpy as np
import pytest

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    FractionalKellyAllocator,
    Phase141KellyAllocator,
)


class TestAdversarialM2DeepStress:
    """Deep adversarial stress testing of Phase 141 risk gating and allocator."""

    def setup_method(self):
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.25,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )

    # =========================================================================
    # 1. RAPID VIX VELOCITY JUMPS (> 3.0/day) & FLASH CRASHES
    # =========================================================================

    def test_vix_velocity_extreme_jump_above_3_per_day(self):
        """Stress test sudden catastrophic VIX velocity jumps > 3.0/day."""
        # Scenario A: VIX jumps from 14.0 to 32.0 in 5 days (vel = (32 - 14)/5 = 3.60/day > 3.0)
        vix_hist = [14.0, 14.0, 14.0, 14.0, 14.0]
        L_a = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=32.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        # Both vix > 28 and vel > 2.0 trigger vix_cap = 0.40
        assert math.isclose(L_a, 0.40, abs_tol=1e-5), f"Expected 0.40, got {L_a}"

        # Scenario B: Low absolute VIX (e.g. 21.0), but extreme velocity from 5.0 (vel = (21-5)/5 = 3.20/day)
        # Even though VIX=21 is moderate, velocity > 2.0 must force vix_cap = 0.40
        vix_hist_b = [5.0, 5.0, 5.0, 5.0, 5.0]
        L_b = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=21.0,
            vix_history=vix_hist_b,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L_b, 0.40, abs_tol=1e-5), f"Expected velocity gating to 0.40, got {L_b}"

        # Scenario C: Super-catastrophic VIX jump from 15.0 to 80.0 (vel = (80-15)/5 = 13.0/day)
        vix_hist_c = [15.0] * 5
        L_c = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=80.0,
            vix_history=vix_hist_c,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L_c, 0.40, abs_tol=1e-5), f"Expected 0.40 under VIX=80, got {L_c}"

    def test_vix_velocity_negative_calming_down(self):
        """Stress test negative VIX velocity (falling VIX): velocity should not artificially penalize."""
        # VIX drops from 40.0 to 20.0 in 5 days (vel = (20 - 40)/5 = -4.0/day)
        # Current VIX is 20.0 (in [18, 22]), vel = -4.0 <= 0.50 -> vix_cap = 1.00
        vix_hist = [40.0] * 5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=20.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L, 1.00, abs_tol=1e-5), f"Expected 1.00 for falling VIX to 20, got {L}"

    # =========================================================================
    # 2. VOLATILITY TERM STRUCTURE RATIO (TSR) INVERSIONS (TSR >= 1.08)
    # =========================================================================

    def test_tsr_inversion_boundary_and_severe_backwardation(self):
        """Verify TSR inversion gating at boundary and under severe backwardation."""
        # TSR = 1.07999 (< 1.08, in [1.00, 1.08)) -> tsr_cap = 0.80
        L_below = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=1.07999,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L_below, 0.80, abs_tol=1e-5)

        # TSR = 1.08000 (>= 1.08) -> tsr_cap = 0.50
        L_exact = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=1.08000,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L_exact, 0.50, abs_tol=1e-5)

        # TSR = 1.25, 2.50, 10.0 (extreme panic backwardation) -> tsr_cap = 0.50
        for tsr in [1.25, 2.50, 10.0]:
            L_ext = self.allocator.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=15.0,
                vix_history=[15.0] * 5,
                tsr_ratio=tsr,
                regime="BULL_LOW_VOL",
            )
            assert math.isclose(L_ext, 0.50, abs_tol=1e-5), f"TSR={tsr} gave {L_ext}"

    def test_simultaneous_extreme_vix_jump_and_tsr_inversion(self):
        """Simultaneous VIX velocity jump (> 3.0/day) and TSR inversion (>= 1.08)."""
        # vix_cap = 0.40, tsr_cap = 0.50 -> min(1.25, 1.25, 0.40, 0.50) = 0.40
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=35.0,
            vix_history=[15.0] * 5,  # vel = (35-15)/5 = 4.0/day
            tsr_ratio=1.20,           # acute inversion
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L, 0.40, abs_tol=1e-5)

    # =========================================================================
    # 3. 5-DAY CONTANGO LOCK IN RELIEF_RALLY
    # =========================================================================

    def test_relief_rally_5day_contango_lock_continuous_simulation(self):
        """Simulate a multi-week trading path verifying 5-day contango lock hysteresis."""
        alloc = DynamicRegimeLeverageAllocator()

        # Days 1 to 4: TSR < 0.95, but history has fewer than 5 days -> 0.90
        for day in range(1, 5):
            hist = [0.90] * day
            L = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=15.0,
                vix_history=[15.0] * 5,
                tsr_ratio=0.90,
                regime="RELIEF_RALLY",
                tsr_history=hist,
            )
            assert math.isclose(L, 0.90, abs_tol=1e-5), f"Day {day} must be 0.90"

        # Day 5: 5th consecutive day with TSR < 0.95 -> expands to 1.25
        hist_5 = [0.90, 0.91, 0.89, 0.92, 0.90]
        L_5 = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=hist_5,
        )
        assert math.isclose(L_5, 1.25, abs_tol=1e-5), f"Day 5 must expand to 1.25"

        # Day 6: Single-day breach (TSR = 0.96) -> immediately drops to 0.90
        hist_6 = [0.91, 0.89, 0.92, 0.90, 0.96]
        L_6 = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.96,
            regime="RELIEF_RALLY",
            tsr_history=hist_6,
        )
        # Note: tsr_cap for 0.96 is 1.00, but reg_target is 0.90, so min(0.90, 1.00) = 0.90
        assert math.isclose(L_6, 0.90, abs_tol=1e-5), f"Day 6 must drop to 0.90 on breach"

        # Days 7-9: TSR back below 0.95, but breach is still within last 5 days -> 0.90
        hist_7 = [0.89, 0.92, 0.90, 0.96, 0.88]  # breach at index -2
        L_7 = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.88,
            regime="RELIEF_RALLY",
            tsr_history=hist_7,
        )
        assert math.isclose(L_7, 0.90, abs_tol=1e-5), f"Day 7 must remain 0.90"

        # Day 11: 5 new consecutive days with TSR < 0.95 -> expands to 1.25
        hist_11 = [0.88, 0.90, 0.91, 0.89, 0.87]
        L_11 = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.87,
            regime="RELIEF_RALLY",
            tsr_history=hist_11,
        )
        assert math.isclose(L_11, 1.25, abs_tol=1e-5), f"Day 11 must expand back to 1.25"

        # Missing / None / Empty history -> safely clamps to 0.90
        for bad_hist in [None, [], [0.90]]:
            L_bad = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=15.0,
                vix_history=[15.0] * 5,
                tsr_ratio=0.90,
                regime="RELIEF_RALLY",
                tsr_history=bad_hist,
            )
            assert math.isclose(L_bad, 0.90, abs_tol=1e-5)

    # =========================================================================
    # 4. HWM DRAWDOWN DE-LEVERAGING TIERS: 1,000-POINT CONTINUOUS MONOTONICITY
    # =========================================================================

    def test_hwm_drawdown_tiers_monotonicity_sweep_1000_points(self):
        """
        Sweep 1,000 NAV points from 100.0 down to 70.0 (0.0% to -30.0% drawdown).
        Assert:
        1. Monotonicity: L(dd_i) >= L(dd_{i+1})
        2. Exact tier boundaries:
           - dd >= -4.0%: L == 1.25
           - dd in (-7.0%, -4.0%): linear drop from 1.25 to 1.00
           - dd in (-10.0%, -7.0%]: L == 0.85
           - dd in (-12.0%, -10.0%]: L == 0.50
           - dd <= -12.0%: L == 0.15 (min_crisis_exposure)
        """
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0

        nav_sweep = np.linspace(100.0, 70.0, 1000)
        prev_L = 1.25

        for nav in nav_sweep:
            dd = (nav - 100.0) / 100.0
            L = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=nav,
                vix=15.0,
                vix_history=[15.0] * 5,
                tsr_ratio=0.90,
                regime="BULL_LOW_VOL",
            )
            # Strict non-increasing monotonicity
            assert L <= prev_L + 1e-12, f"Monotonicity violation at dd={dd:.4f}: {L} > {prev_L}"
            prev_L = L

            # Boundary checks
            if dd >= -0.040:
                assert math.isclose(L, 1.25, abs_tol=1e-5), f"dd={dd}: expected 1.25, got {L}"
            elif dd <= -0.120:
                assert math.isclose(L, 0.15, abs_tol=1e-5), f"dd={dd}: expected 0.15, got {L}"
            elif dd <= -0.100:
                assert math.isclose(L, 0.50, abs_tol=1e-5), f"dd={dd}: expected 0.50, got {L}"
            elif dd <= -0.070:
                assert math.isclose(L, 0.85, abs_tol=1e-5), f"dd={dd}: expected 0.85, got {L}"
            else:
                # dd in (-0.070, -0.040): linear interpolation
                expected_L = 1.00 + 0.25 * ((-0.070 - dd) / (-0.030))
                assert math.isclose(L, expected_L, abs_tol=1e-5), f"dd={dd}: expected {expected_L}, got {L}"

    def test_hwm_peak_recovery_dynamics(self):
        """Verify HWM updates when NAV exceeds previous peak, and DD evaluates from new peak."""
        alloc = DynamicRegimeLeverageAllocator()

        # Start at NAV 100 -> peak 100
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        assert alloc.hwm_peak == 100.0

        # Rise to NAV 120 -> peak updates to 120
        alloc.evaluate_dynamic_leverage_frontier(120.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        assert alloc.hwm_peak == 120.0

        # Pullback to 110: DD = (110 - 120)/120 = -8.33% -> dd in (-10%, -7%] -> L = 0.85
        L_pb = alloc.evaluate_dynamic_leverage_frontier(110.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        assert alloc.hwm_peak == 120.0
        assert math.isclose(L_pb, 0.85, abs_tol=1e-5)

        # Breakout to NAV 130 -> new peak 130 -> dd = 0.0 -> L = 1.25
        L_bo = alloc.evaluate_dynamic_leverage_frontier(130.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        assert alloc.hwm_peak == 130.0
        assert math.isclose(L_bo, 1.25, abs_tol=1e-5)

    # =========================================================================
    # 5. MULTI-GATE INTERACTION & CRISIS FLOOR
    # =========================================================================

    def test_multi_gate_interaction_takes_minimum_envelope(self):
        """Verify that final leverage is strictly the minimum across all 4 gates."""
        # reg_target: 1.25 (BULL_LOW_VOL)
        # dd_cap: 0.85 (NAV = 92, dd = -8.0%)
        # vix_cap: 0.75 (VIX = 24.0, vel = 0.20)
        # tsr_cap: 0.80 (TSR = 1.02)
        # min(1.25, 0.85, 0.75, 0.80) = 0.75
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=92.0,
            vix=24.0,
            vix_history=[23.0] * 5,
            tsr_ratio=1.02,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(L, 0.75, abs_tol=1e-5)

    def test_crisis_floor_strictly_guaranteed(self):
        """Verify that leverage never drops below min_crisis_exposure (0.15) under any conditions."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0

        # Simultaneous worst-case: DD = -50%, VIX = 90, vel = 15.0, TSR = 3.0, PANIC_CRISIS regime
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=50.0,
            vix=90.0,
            vix_history=[15.0] * 5,
            tsr_ratio=3.0,
            regime="PANIC_CRISIS",
        )
        assert math.isclose(L, 0.15, abs_tol=1e-6)
        assert L >= alloc.min_crisis_exposure

"""
tests/test_phase145_risk_gating.py - Unit Test Catalog for Phase 145 4-Tier Protective Gating.
Target Features: F706, F707.

Verifies:
- Category 1: Gate 1 - VIX Level & Velocity Protective Filter (TC01 ~ TC06)
- Category 2: Gate 2 - Volatility Term Structure Ratio (TSR) & Contango Lock (TC07 ~ TC12)
- Category 3: Gate 3 - High-Water Mark (HWM) Drawdown Tiers & Circuit Breaker (TC13 ~ TC18)
- Category 4: Gate 4 - Leveraged Leland Dynamic Buffer Bands Expansion (TC19 ~ TC24)
- Category 5: 4-Tier Minimum Envelope & Regime Frontier Integration (TC25 ~ TC28)
- Category 6: Adversarial Gating Stress Tests & Boundary Invariants (TC29 ~ TC30)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations.
"""

from __future__ import annotations

import os
import sys
import unittest
import numpy as np

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase145RiskGating(unittest.TestCase):
    """30 Comprehensive Test Cases for Phase 145 4-Tier Protective Gating (Feature F707)."""

    def setUp(self):
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.30,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )
        self.port_allocator = PortfolioAllocator(version=145)

    # =========================================================================
    # Category 1: Gate 1 - VIX Level & Velocity Protective Filter (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_low_volatility_bull_pass(self):
        """TC01: Low volatility bull pass: VIX=15.0, vel=0.20 <= 0.50 --> vix_cap = 1.30x."""
        vix_hist = [14.0, 14.2, 14.5, 14.8, 14.0]  # vel = (15.0 - 14.0) / 5 = 0.20
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 1.30, places=5)

    def test_tc02_moderate_vix_cap(self):
        """TC02: Moderate VIX cap: VIX=20.0 (in [18, 22]), vel=0.20 --> vix_cap = 1.00x."""
        vix_hist = [19.0, 19.2, 19.5, 19.8, 19.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=20.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 1.00, places=5)

    def test_tc03_moderate_velocity_surge(self):
        """TC03: Moderate velocity surge: VIX=16.0, vel=0.70 > 0.50 --> vix_cap = 1.00x."""
        vix_hist = [12.5, 12.5, 12.5, 12.5, 12.5]  # vel = (16.0 - 12.5) / 5 = 0.70
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 1.00, places=5)

    def test_tc04_elevated_vix_defensive(self):
        """TC04: Elevated VIX defensive: VIX=25.0 (in [22, 28]), vel=0.20 --> vix_cap = 0.75x."""
        vix_hist = [24.0, 24.0, 24.0, 24.0, 24.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=25.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 0.75, places=5)

    def test_tc05_high_velocity_surge(self):
        """TC05: High velocity surge: VIX=19.0, vel=1.50 > 1.00 --> vix_cap = 0.75x."""
        vix_hist = [11.5, 11.5, 11.5, 11.5, 11.5]  # vel = (19.0 - 11.5) / 5 = 1.50
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=19.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 0.75, places=5)

    def test_tc06_extreme_vix_crisis_panic_velocity(self):
        """TC06: Extreme VIX crisis panic: VIX=35.0 > 28.0 and vel=2.50 > 2.00 --> vix_cap = 0.40x."""
        vix_hist = [22.5, 22.5, 22.5, 22.5, 22.5]  # vel = (35.0 - 22.5) / 5 = 2.50
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=35.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 0.40, places=5)

    # =========================================================================
    # Category 2: Gate 2 - Volatility Term Structure Ratio (TSR) & Contango Lock (TC07 ~ TC12)
    # =========================================================================

    def test_tc07_normal_contango_pass(self):
        """TC07: Normal contango pass: TSR=0.90 <= 0.95 --> tsr_cap = 1.30x."""
        vix_hist = [14.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 1.30, places=5)

    def test_tc08_mild_inversion_warning(self):
        """TC08: Mild inversion warning: TSR=0.98 in (0.95, 1.00) --> tsr_cap = 1.00x."""
        vix_hist = [14.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist,
            tsr_ratio=0.98,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 1.00, places=5)

    def test_tc09_acute_panic_backwardation(self):
        """TC09: Acute panic backwardation: TSR=1.12 >= 1.08 --> tsr_cap = 0.50x."""
        vix_hist = [14.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist,
            tsr_ratio=1.12,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 0.50, places=5)

    def test_tc10_emergency_deleveraging_latency(self):
        """TC10: Emergency de-leveraging latency: verify transition from 1.30x to 0.50x takes place in <= 1 step."""
        vix_hist = [14.0]*5
        # Day 1: Calm bull market
        L_day1 = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=14.0, vix_history=vix_hist, tsr_ratio=0.88, regime="BULL_LOW_VOL"
        )
        self.assertAlmostEqual(L_day1, 1.30, places=5)

        # Day 2: Sudden acute term structure backwardation shock (TSR = 1.15)
        L_day2 = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=99.0, vix=18.0, vix_history=vix_hist, tsr_ratio=1.15, regime="BULL_LOW_VOL"
        )
        self.assertAlmostEqual(L_day2, 0.50, places=5)

    def test_tc11_relief_rally_contango_lock_pass(self):
        """TC11: RELIEF_RALLY 5-day contango lock PASS: when tsr_history has 5 consecutive days < 0.95, target expands to 1.30x."""
        tsr_history_pass = [0.91, 0.89, 0.92, 0.88, 0.90]
        vix_hist = [15.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=tsr_history_pass,
        )
        self.assertAlmostEqual(L, 1.30, places=5)

    def test_tc12_relief_rally_contango_lock_fail(self):
        """TC12: RELIEF_RALLY 5-day contango lock FAIL: when any day in past 5 days >= 0.95, target is locked at 0.90x."""
        tsr_history_fail = [0.91, 0.96, 0.92, 0.88, 0.90]  # Day 2 is 0.96 >= 0.95
        vix_hist = [15.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=tsr_history_fail,
        )
        self.assertAlmostEqual(L, 0.90, places=5)

    # =========================================================================
    # Category 3: Gate 3 - High-Water Mark (HWM) Drawdown Tiers & Circuit Breaker (TC13 ~ TC18)
    # =========================================================================

    def test_tc13_peak_tracking(self):
        """TC13: Peak tracking: HWM tracks peak NAV monotonically."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertEqual(alloc.hwm_peak, 100.0)
        alloc.evaluate_dynamic_leverage_frontier(105.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertEqual(alloc.hwm_peak, 105.0)
        alloc.evaluate_dynamic_leverage_frontier(102.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertEqual(alloc.hwm_peak, 105.0)  # Peak preserved

    def test_tc14_mild_drawdown_tier(self):
        """TC14: Mild drawdown tier: DD = -2.5% >= -4.0% --> dd_cap = 1.30x."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        L = alloc.evaluate_dynamic_leverage_frontier(97.5, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertAlmostEqual(L, 1.30, places=5)

    def test_tc15_continuous_linear_trim_tier(self):
        """TC15: Continuous linear trim tier: DD = -5.5% in (-7.0%, -4.0%) --> dd_cap = 1.00 + 0.30 * 0.50 = 1.15x."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        # DD = (94.5 - 100) / 100 = -5.5%
        L = alloc.evaluate_dynamic_leverage_frontier(94.5, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        # dd_cap = 1.00 + 0.30 * (-0.070 - (-0.055)) / (-0.030) = 1.00 + 0.30 * (0.015 / 0.030) = 1.15x
        self.assertAlmostEqual(L, 1.15, places=5)

    def test_tc16_defensive_drawdown_tier(self):
        """TC16: Defensive drawdown tier: DD = -8.5% in (-10.0%, -7.0%] --> dd_cap = 0.85x."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        L = alloc.evaluate_dynamic_leverage_frontier(91.5, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertAlmostEqual(L, 0.85, places=5)

    def test_tc17_deep_drawdown_tier(self):
        """TC17: Deep drawdown tier: DD = -11.0% in (-12.0%, -10.0%] --> dd_cap = 0.50x."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        L = alloc.evaluate_dynamic_leverage_frontier(89.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertAlmostEqual(L, 0.50, places=5)

    def test_tc18_hard_circuit_breaker(self):
        """TC18: Hard circuit breaker: DD = -13.5% <= -12.0% --> dd_cap = 0.15x (crisis floor)."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        L = alloc.evaluate_dynamic_leverage_frontier(86.5, 15.0, vix_hist, 0.90, "BULL_LOW_VOL")
        self.assertAlmostEqual(L, 0.15, places=5)

    # =========================================================================
    # Category 4: Gate 4 - Leveraged Leland Dynamic Buffer Bands Expansion (TC19 ~ TC24)
    # =========================================================================

    def test_tc19_unleveraged_baseline_buffer(self):
        """TC19: Unleveraged baseline buffer: when L <= 1.00, bandwidth expansion multiplier = 1.00x."""
        expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base=0.020, leverage=1.00)
        self.assertAlmostEqual(expanded, 0.020, places=6)
        expanded_sub = self.allocator.calculate_leveraged_leland_buffer(delta_base=0.020, leverage=0.60)
        self.assertAlmostEqual(expanded_sub, 0.020, places=6)

    def test_tc20_bull_leverage_buffer_expansion(self):
        """TC20: Bull leverage buffer expansion: when L = 1.30, bandwidth expands by exactly 1.12x."""
        expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base=0.020, leverage=1.30)
        # 0.020 * (1.0 + 0.40 * 0.30) = 0.020 * 1.12 = 0.0224
        self.assertAlmostEqual(expanded, 0.0224, places=6)

        # Also verify in PortfolioAllocator
        delta_base = self.port_allocator.calculate_dynamic_buffer_band("AAPL", 0.05, 0.0010, 0.020, leverage=1.00)
        delta_leveraged = self.port_allocator.calculate_dynamic_buffer_band("AAPL", 0.05, 0.0010, 0.020, leverage=1.30)
        self.assertAlmostEqual(delta_leveraged / delta_base, 1.12, places=4)

    def test_tc21_turnover_reduction_verification(self):
        """TC21: Turnover reduction verification: expanded bands widen no-trade zone, converting trade into HOLD."""
        # Symbol with target 0.05, current 0.0523
        curr_w = {"005930": 0.0523}
        tgt_w = {"005930": 0.0500}
        mkt_map = {"005930": "KOSPI"}
        vol_map = {"005930": 0.020}
        adv_map = {"005930": 1e9}

        # Under unleveraged L=1.0, delta is smaller (~0.0020), 0.0523 is near/outside band
        res_unlev = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.00,
        )

        # Under leveraged L=1.30, delta expands by 1.12x, ensuring 0.0523 is strictly inside band -> HOLD
        res_lev = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )
        self.assertEqual(res_lev["trades"]["005930"]["action"], "HOLD")

    def test_tc22_instant_bypass_new_position(self):
        """TC22: Instant bypass for new position entry: w_curr == 0.0 and w_targ > 0 trades immediately."""
        curr_w = {"AAPL": 0.0}
        tgt_w = {"AAPL": 0.04}
        mkt_map = {"AAPL": "SP500"}
        vol_map = {"AAPL": 0.020}
        adv_map = {"AAPL": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )
        self.assertEqual(res["trades"]["AAPL"]["action"], "BUY")
        self.assertAlmostEqual(res["new_weights"]["AAPL"], 0.04, places=4)

    def test_tc23_instant_bypass_full_exit(self):
        """TC23: Instant bypass for full position exit: w_targ == 0.0 and w_curr > 0 liquidates immediately."""
        curr_w = {"AAPL": 0.04}
        tgt_w = {"AAPL": 0.0}
        mkt_map = {"AAPL": "SP500"}
        vol_map = {"AAPL": 0.020}
        adv_map = {"AAPL": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )
        self.assertEqual(res["trades"]["AAPL"]["action"], "SELL")
        self.assertAlmostEqual(res["new_weights"]["AAPL"], 0.0, places=6)

    def test_tc24_instant_bypass_extreme_drift(self):
        """TC24: Instant bypass for extreme drift: |w_curr - w_targ| / w_targ >= 0.50 triggers rebalance."""
        # Current weight has drifted 60% away from target (0.08 vs 0.05)
        curr_w = {"AAPL": 0.08}
        tgt_w = {"AAPL": 0.05}
        mkt_map = {"AAPL": "SP500"}
        vol_map = {"AAPL": 0.020}
        adv_map = {"AAPL": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )
        self.assertEqual(res["trades"]["AAPL"]["action"], "SELL")
        self.assertNotEqual(res["trades"]["AAPL"]["trade_weight"], 0.0)

    # =========================================================================
    # Category 5: 4-Tier Minimum Envelope & Regime Frontier Integration (TC25 ~ TC28)
    # =========================================================================

    def test_tc25_comprehensive_lower_envelope(self):
        """TC25: Comprehensive lower envelope: min(regime, vix, tsr, dd) binds strictly."""
        # Regime wants 1.30, but Gate 1 caps at 0.75 (VIX=25.0)
        vix_hist = [24.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=25.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L, 0.75, places=5)

        # If Gate 3 (DD = -11.0%) caps further at 0.50, final L must be 0.50
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, [14.0]*5, 0.90, "BULL_LOW_VOL")
        L_env = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=89.0,
            vix=25.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L_env, 0.50, places=5)

    def test_tc26_bear_and_crisis_regime_clamping(self):
        """TC26: Bear and crisis regime clamping: L <= 0.60 for BEAR_LOW_VOL, <= 0.25 for BEAR_HIGH_VOL, <= 0.15 for PANIC."""
        L_bear_low = self.allocator.evaluate_dynamic_leverage_frontier(100.0, 15.0, [14.0]*5, 0.90, "BEAR_LOW_VOL")
        L_bear_high = self.allocator.evaluate_dynamic_leverage_frontier(100.0, 15.0, [14.0]*5, 0.90, "BEAR_HIGH_VOL")
        L_panic = self.allocator.evaluate_dynamic_leverage_frontier(100.0, 15.0, [14.0]*5, 0.90, "PANIC_CRISIS")

        self.assertAlmostEqual(L_bear_low, 0.60, places=5)
        self.assertAlmostEqual(L_bear_high, 0.25, places=5)
        self.assertAlmostEqual(L_panic, 0.15, places=5)

    def test_tc27_floor_enforcement(self):
        """TC27: Floor enforcement: leverage never drops below min_crisis_exposure (0.15x)."""
        # Complete disaster: NAV=-50% (DD=-50%), VIX=60, TSR=1.40
        L_floor = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=50.0,
            vix=60.0,
            vix_history=[20.0]*5,
            tsr_ratio=1.40,
            regime="PANIC_CRISIS",
        )
        self.assertEqual(L_floor, 0.15)

    def test_tc28_borrowing_cost_calculation(self):
        """TC28: Borrowing cost calculation: at L=1.30, spread 60 bps -> 18 bps/yr annualized drag."""
        drag = self.allocator.calculate_borrowing_cost_drag(1.30)
        # (1.30 - 1.0) * 0.0060 = 0.30 * 0.0060 = 0.0018 (18 bps / yr)
        self.assertAlmostEqual(drag, 0.0018, places=6)

        # Unleveraged: 0 drag
        self.assertEqual(self.allocator.calculate_borrowing_cost_drag(1.00), 0.0)
        self.assertEqual(self.allocator.calculate_borrowing_cost_drag(0.85), 0.0)

    # =========================================================================
    # Category 6: Adversarial Gating Stress Tests & Boundary Invariants (TC29 ~ TC30)
    # =========================================================================

    def test_tc29_missing_history_nan_input_robustness(self):
        """TC29: Missing history / NaN input robustness: assert safe defensive defaults."""
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=np.nan,
            vix=np.nan,
            vix_history=None,
            tsr_ratio=np.nan,
            regime=None,
            tsr_history=None,
        )
        self.assertFalse(np.isnan(L))
        self.assertGreaterEqual(L, 0.15)
        self.assertLessEqual(L, 1.30)

    def test_tc30_rapid_flash_crash_sequential_simulation(self):
        """TC30: Rapid flash-crash sequential simulation: transition from 1.30x to 0.15x during crisis cascade."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        # Day 1: Calm bull low vol
        L1 = alloc.evaluate_dynamic_leverage_frontier(100.0, 14.0, [14.0]*5, 0.88, "BULL_LOW_VOL")
        self.assertAlmostEqual(L1, 1.30, places=5)

        # Day 2: Rumor of crisis, VIX ticks up to 21 (vel = 0.70) -> 1.00x
        L2 = alloc.evaluate_dynamic_leverage_frontier(99.0, 21.0, [17.5]*5, 0.94, "BULL_LOW_VOL")
        self.assertAlmostEqual(L2, 1.00, places=5)

        # Day 3: Market breaks down, VIX=27 (vel=1.40), TSR=1.02
        L3 = alloc.evaluate_dynamic_leverage_frontier(96.0, 27.0, [20.0]*5, 1.02, "SIDEWAYS_HIGH_VOL")
        self.assertAlmostEqual(L3, 0.75, places=5)

        # Day 4: Bear trend established, VIX=32, TSR=1.10
        L4 = alloc.evaluate_dynamic_leverage_frontier(92.0, 32.0, [16.0]*5, 1.10, "BEAR_HIGH_VOL")
        self.assertAlmostEqual(L4, 0.25, places=5)

        # Day 5: Full systemic crash (NAV=85, VIX=48, vel=6.8, TSR=1.25)
        L5 = alloc.evaluate_dynamic_leverage_frontier(85.0, 48.0, [14.0]*5, 1.25, "PANIC_CRISIS")
        self.assertAlmostEqual(L5, 0.15, places=5)


if __name__ == "__main__":
    unittest.main()

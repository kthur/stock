"""
tests/test_phase106_intraday_risk.py — Comprehensive Unit & Integration Test Suite.

Phase 106 / Feature F502 / Release R122 (v113 Production Master)
Milestone 3: Institutional Intraday Risk Monitor & Flash-Crash Circuit Breaker.

Test Categories:
- Category 1: Class Instantiation, Config & Alias Trees (TC01~TC02)
- Category 2: Leland Volatility-Adaptive Multiplier Scaling (TC03~TC06)
- Category 3: 3-Tier Profit Taking Logic & Proportions (TC07~TC12)
- Category 4: Breakeven Lock (+0.3%) & Ratchet Stop (+5.0%) Protection (TC13~TC15)
- Category 5: Leland Adaptive Trailing Stop & Hard Stop (-6%) (TC16~TC19)
- Category 6: Automated Flash-Crash Circuit Breakers (Asset 7% & VIX 20%) (TC20~TC25)
- Category 7: Multi-Holding Portfolio Batch Evaluation & Integration (TC26~TC30)
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.intraday_risk_monitor import (
    InstitutionalIntradayRiskMonitor,
    IntradayRiskMonitor,
    Phase106IntradayRiskMonitor,
    FlashCrashCircuitBreaker,
    RiskAction,
    PositionRiskState,
)


class TestPhase106IntradayRiskMonitor(unittest.TestCase):
    """Test suite for InstitutionalIntradayRiskMonitor."""

    def setUp(self):
        """Set up fresh monitor instance for each test."""
        self.monitor = InstitutionalIntradayRiskMonitor()

    # -----------------------------------------------------------------------
    # Category 1: Class Instantiation, Config & Alias Trees
    # -----------------------------------------------------------------------

    def test_tc01_instantiation_and_alias_trees(self):
        """TC01: Verify instantiation, default parameters, and backward compatibility alias trees."""
        monitor = InstitutionalIntradayRiskMonitor()
        self.assertAlmostEqual(monitor.baseline_stop_pct, -0.06)
        self.assertAlmostEqual(monitor.peak_trailing_stop_pct, -0.10)
        self.assertAlmostEqual(monitor.tier1_profit_pct, 0.05)
        self.assertAlmostEqual(monitor.tier1_ratio, 0.30)
        self.assertAlmostEqual(monitor.tier1_breakeven_offset, 0.003)
        self.assertAlmostEqual(monitor.tier2_profit_pct, 0.10)
        self.assertAlmostEqual(monitor.tier2_ratio, 0.30)
        self.assertAlmostEqual(monitor.tier2_ratchet_offset, 0.050)
        self.assertAlmostEqual(monitor.tier3_profit_pct, 0.20)
        self.assertAlmostEqual(monitor.tier3_ratio, 0.40)
        self.assertAlmostEqual(monitor.flash_crash_asset_drop_pct, -0.07)
        self.assertAlmostEqual(monitor.flash_crash_vix_surge_pct, 0.20)

        # Alias trees check
        self.assertIs(IntradayRiskMonitor, InstitutionalIntradayRiskMonitor)
        self.assertIs(Phase106IntradayRiskMonitor, InstitutionalIntradayRiskMonitor)
        self.assertIs(FlashCrashCircuitBreaker, InstitutionalIntradayRiskMonitor)

    def test_tc02_risk_action_and_position_state_serialization(self):
        """TC02: Verify RiskAction and PositionRiskState serialization to standard dicts."""
        action = RiskAction(
            action_id="RA_TEST_001",
            symbol="005930",
            market="KOSPI",
            action="SELL",
            quantity=100,
            ratio=0.30,
            trigger_price=73500.0,
            current_price=74000.0,
            stop_price=70210.0,
            reason="PROFIT_TAKING_TIER1_5PCT",
            severity="INFO",
            force_liquidate=False,
            is_hedge=False,
            details={"tier": 1},
        )
        d = action.to_dict()
        self.assertEqual(d["action_id"], "RA_TEST_001")
        self.assertEqual(d["symbol"], "005930")
        self.assertEqual(d["action"], "SELL")
        self.assertEqual(d["quantity"], 100)
        self.assertAlmostEqual(d["ratio"], 0.30)
        self.assertEqual(d["reason"], "PROFIT_TAKING_TIER1_5PCT")

        pos = PositionRiskState(
            symbol="AAPL",
            market="NASDAQ",
            entry_price=150.0,
            initial_quantity=50,
            current_quantity=50,
            peak_price=160.0,
        )
        p_dict = pos.to_dict()
        self.assertEqual(p_dict["symbol"], "AAPL")
        self.assertEqual(p_dict["market"], "NASDAQ")
        self.assertAlmostEqual(p_dict["entry_price"], 150.0)

    # -----------------------------------------------------------------------
    # Category 2: Leland Volatility-Adaptive Multiplier Scaling
    # -----------------------------------------------------------------------

    def test_tc03_leland_multiplier_baseline(self):
        """TC03: Leland multiplier equals exactly 1.0 at baseline volatility and zero momentum."""
        m = self.monitor.compute_leland_multiplier(volatility_20d=0.02, momentum_factor=0.0)
        self.assertAlmostEqual(m, 1.0, places=4)

    def test_tc04_leland_multiplier_high_volatility_expansion(self):
        """TC04: Leland multiplier expands > 1.0 under high volatility and clamps at 1.80."""
        # Moderate elevated volatility: 3.5% daily vol (base 2.0%)
        m_elevated = self.monitor.compute_leland_multiplier(volatility_20d=0.035, momentum_factor=0.1)
        self.assertGreater(m_elevated, 1.0)
        self.assertLessEqual(m_elevated, 1.80)

        # Extremely high volatility (e.g. 10% daily vol): strictly clamped to upper bound 1.80
        m_extreme = self.monitor.compute_leland_multiplier(volatility_20d=0.10, momentum_factor=0.5)
        self.assertAlmostEqual(m_extreme, 1.80, places=4)

    def test_tc05_leland_multiplier_low_volatility_tightening(self):
        """TC05: Leland multiplier tightens < 1.0 under low volatility and clamps at 0.60."""
        # Low volatility: 0.8% daily vol
        m_low = self.monitor.compute_leland_multiplier(volatility_20d=0.008, momentum_factor=-0.1)
        self.assertLess(m_low, 1.0)
        self.assertGreaterEqual(m_low, 0.60)

        # Extremely calm market with negative momentum: strictly clamped to lower bound 0.60
        m_extreme_low = self.monitor.compute_leland_multiplier(volatility_20d=0.001, momentum_factor=-0.8)
        self.assertAlmostEqual(m_extreme_low, 0.60, places=4)

    def test_tc06_leland_multiplier_boundary_and_nan_resilience(self):
        """TC06: Leland multiplier handles NaN, inf, negative volatility gracefully."""
        self.assertAlmostEqual(self.monitor.compute_leland_multiplier(float('nan')), 1.0, places=2)
        self.assertAlmostEqual(self.monitor.compute_leland_multiplier(-0.05), 1.0, places=2)
        self.assertAlmostEqual(self.monitor.compute_leland_multiplier(0.02, float('nan')), 1.0, places=2)
        self.assertAlmostEqual(self.monitor.compute_leland_multiplier(float('inf')), 1.80, places=2)

    # -----------------------------------------------------------------------
    # Category 3: 3-Tier Profit Taking Logic & Proportions
    # -----------------------------------------------------------------------

    def test_tc07_tier1_profit_taking_trigger_and_breakeven_lock(self):
        """TC07: Tier 1 (+5%) triggers 30% exit and locks breakeven stop at entry + 0.3%."""
        holding = {
            "symbol": "005930",
            "market": "KOSPI",
            "entry_price": 70000.0,
            "quantity": 100,
        }
        # Price at +4% (no trigger)
        action_below = self.monitor.evaluate_profit_taking(holding, current_price=72800.0)
        self.assertIsNone(action_below)

        # Price at +5.5% (triggers Tier 1)
        action_t1 = self.monitor.evaluate_profit_taking(holding, current_price=73850.0)
        self.assertIsNotNone(action_t1)
        self.assertEqual(action_t1.action, "SELL")
        self.assertEqual(action_t1.quantity, 30)  # 30% of 100
        self.assertAlmostEqual(action_t1.ratio, 0.30)
        self.assertEqual(action_t1.reason, "PROFIT_TAKING_TIER1_5PCT")
        self.assertAlmostEqual(action_t1.stop_price, 70000.0 * 1.003)  # entry + 0.3%

        # Verify internal state
        pos = self.monitor.get_position("005930")
        self.assertTrue(pos.tier1_executed)
        self.assertTrue(pos.breakeven_locked)
        self.assertEqual(pos.current_quantity, 70)
        self.assertAlmostEqual(pos.breakeven_price, 70000.0 * 1.003)

    def test_tc08_tier2_profit_taking_trigger_and_ratchet_lock(self):
        """TC08: Tier 2 (+10%) triggers 30% exit and ratchets trailing stop to entry + 5.0%."""
        pos = self.monitor.register_position("AAPL", entry_price=100.0, quantity=100, market="NASDAQ")
        # First trigger Tier 1 (+6%)
        self.monitor.evaluate_profit_taking(pos, current_price=106.0)
        self.assertEqual(pos.current_quantity, 70)

        # Price reaches +11.0% (triggers Tier 2)
        action_t2 = self.monitor.evaluate_profit_taking(pos, current_price=111.0)
        self.assertIsNotNone(action_t2)
        self.assertEqual(action_t2.action, "SELL")
        self.assertEqual(action_t2.quantity, 30)  # 30% of 100 initial
        self.assertAlmostEqual(action_t2.ratio, 0.30)
        self.assertEqual(action_t2.reason, "PROFIT_TAKING_TIER2_10PCT")
        self.assertAlmostEqual(action_t2.stop_price, 100.0 * 1.050)  # entry + 5.0%

        # Verify internal state
        self.assertTrue(pos.tier2_executed)
        self.assertTrue(pos.ratchet_locked)
        self.assertEqual(pos.current_quantity, 40)
        self.assertAlmostEqual(pos.ratchet_price, 105.0)

    def test_tc09_tier3_profit_taking_runner_exit(self):
        """TC09: Tier 3 (+20%) triggers runner exit for all remaining quantity."""
        pos = self.monitor.register_position("NVDA", entry_price=200.0, quantity=100, market="NASDAQ")
        # Advance through Tier 1 (+7%) and Tier 2 (+12%)
        self.monitor.evaluate_profit_taking(pos, current_price=214.0)
        self.monitor.evaluate_profit_taking(pos, current_price=224.0)
        self.assertEqual(pos.current_quantity, 40)

        # Price reaches +22% (triggers Tier 3)
        action_t3 = self.monitor.evaluate_profit_taking(pos, current_price=244.0)
        self.assertIsNotNone(action_t3)
        self.assertEqual(action_t3.action, "SELL")
        self.assertEqual(action_t3.quantity, 40)  # remaining 40 shares
        self.assertAlmostEqual(action_t3.ratio, 0.40)
        self.assertEqual(action_t3.reason, "PROFIT_TAKING_TIER3_20PCT")
        self.assertEqual(pos.current_quantity, 0)
        self.assertTrue(pos.tier3_executed)

    def test_tc10_cumulative_shares_conservation_30_30_40(self):
        """TC10: Sum of Tier 1 (30%), Tier 2 (30%), and Tier 3 (40%) equals 100% of initial shares."""
        initial_qty = 250
        pos = self.monitor.register_position("MSFT", entry_price=300.0, quantity=initial_qty, market="NASDAQ")

        a1 = self.monitor.evaluate_profit_taking(pos, current_price=316.0)  # +5.33%
        a2 = self.monitor.evaluate_profit_taking(pos, current_price=333.0)  # +11.0%
        a3 = self.monitor.evaluate_profit_taking(pos, current_price=365.0)  # +21.67%

        total_exited = a1.quantity + a2.quantity + a3.quantity
        self.assertEqual(total_exited, initial_qty)
        self.assertEqual(pos.current_quantity, 0)

    def test_tc11_small_lot_integer_rounding_guarantees(self):
        """TC11: Small lot quantities (e.g. 7 shares) round without over-allocating or leaking."""
        initial_qty = 7
        pos = self.monitor.register_position("035420", entry_price=200000.0, quantity=initial_qty, market="KOSPI")

        a1 = self.monitor.evaluate_profit_taking(pos, current_price=211000.0)  # +5.5%
        # 30% of 7 = 2.1 -> floor 2
        self.assertEqual(a1.quantity, 2)
        self.assertEqual(pos.current_quantity, 5)

        a2 = self.monitor.evaluate_profit_taking(pos, current_price=222000.0)  # +11.0%
        # 30% of 7 = 2.1 -> floor 2
        self.assertEqual(a2.quantity, 2)
        self.assertEqual(pos.current_quantity, 3)

        a3 = self.monitor.evaluate_profit_taking(pos, current_price=245000.0)  # +22.5%
        # remaining runner -> 3
        self.assertEqual(a3.quantity, 3)
        self.assertEqual(pos.current_quantity, 0)

    def test_tc12_no_duplicate_triggers_at_same_tier(self):
        """TC12: Repeated checks within the same tier do not re-trigger partial exits."""
        pos = self.monitor.register_position("GOOG", entry_price=100.0, quantity=100, market="NASDAQ")
        # First trigger at +6%
        a1 = self.monitor.evaluate_profit_taking(pos, current_price=106.0)
        self.assertIsNotNone(a1)
        self.assertEqual(pos.current_quantity, 70)

        # Subsequent check at +7% (still in Tier 1 zone, Tier 2 not reached)
        a_dup = self.monitor.evaluate_profit_taking(pos, current_price=107.0)
        self.assertIsNone(a_dup)
        self.assertEqual(pos.current_quantity, 70)

    # -----------------------------------------------------------------------
    # Category 4: Breakeven Lock (+0.3%) & Ratchet Stop (+5.0%) Protection
    # -----------------------------------------------------------------------

    def test_tc13_breakeven_stop_trigger_after_tier1(self):
        """TC13: After Tier 1 execution, a drop back below entry + 0.3% triggers breakeven stop."""
        pos = self.monitor.register_position("000660", entry_price=100000.0, quantity=100, market="KOSPI")
        # Trigger Tier 1 at +6% (106,000 KRW)
        self.monitor.evaluate_profit_taking(pos, current_price=106000.0)
        self.assertTrue(pos.breakeven_locked)
        self.assertAlmostEqual(pos.breakeven_price, 100300.0)  # 100,000 * 1.003

        # Price drops to 100,200 KRW (below breakeven stop of 100,300 KRW)
        stop_action = self.monitor.evaluate_leland_trailing_stop(pos, current_price=100200.0)
        self.assertIsNotNone(stop_action)
        self.assertEqual(stop_action.action, "SELL")
        self.assertEqual(stop_action.reason, "BREAKEVEN_STOP_LOCK")
        self.assertEqual(stop_action.quantity, 70)  # remaining 70 shares
        self.assertEqual(pos.current_quantity, 0)

    def test_tc14_ratchet_stop_trigger_after_tier2(self):
        """TC14: After Tier 2 execution, a drop back below entry + 5.0% triggers ratchet stop."""
        pos = self.monitor.register_position("TSLA", entry_price=200.0, quantity=100, market="NASDAQ")
        # Advance through Tier 1 (+6%) and Tier 2 (+12%)
        self.monitor.evaluate_profit_taking(pos, current_price=212.0)
        self.monitor.evaluate_profit_taking(pos, current_price=224.0)
        self.assertTrue(pos.ratchet_locked)
        self.assertAlmostEqual(pos.ratchet_price, 210.0)  # 200 * 1.050

        # Price retreats to 209.0 (below ratchet stop of 210.0)
        stop_action = self.monitor.evaluate_leland_trailing_stop(pos, current_price=209.0)
        self.assertIsNotNone(stop_action)
        self.assertEqual(stop_action.action, "SELL")
        self.assertEqual(stop_action.reason, "RATCHET_STOP_5PCT")
        self.assertEqual(stop_action.quantity, 40)
        self.assertEqual(pos.current_quantity, 0)

    def test_tc15_ratchet_stop_precedence_over_baseline_and_breakeven(self):
        """TC15: Ratchet stop (+5%) takes mathematical precedence over baseline (-6%) and breakeven (+0.3%)."""
        pos = self.monitor.register_position("AMZN", entry_price=100.0, quantity=100, market="NASDAQ")
        self.monitor.evaluate_profit_taking(pos, current_price=106.0)
        self.monitor.evaluate_profit_taking(pos, current_price=112.0)

        # Baseline stop = 94.0, Breakeven stop = 100.3, Ratchet stop = 105.0
        # Effective stop must be max = 105.0
        self.assertAlmostEqual(pos.baseline_stop_price, 94.0)
        self.assertAlmostEqual(pos.breakeven_price, 100.3)
        self.assertAlmostEqual(pos.ratchet_price, 105.0)
        self.assertAlmostEqual(pos.effective_stop_price, 105.0)

    # -----------------------------------------------------------------------
    # Category 5: Leland Adaptive Trailing Stop & Hard Stop (-6%)
    # -----------------------------------------------------------------------

    def test_tc16_baseline_hard_stop_negative_6pct(self):
        """TC16: Baseline hard stop (-6.0% from entry) triggers when price falls without prior peak gains."""
        pos = self.monitor.register_position("051910", entry_price=500000.0, quantity=20, market="KOSPI")
        # Price drops by 4% (480,000 KRW, above -6% stop of 470,000 KRW)
        a_safe = self.monitor.evaluate_leland_trailing_stop(pos, current_price=480000.0)
        self.assertIsNone(a_safe)

        # Price drops by 6.2% (469,000 KRW, breaches -6% stop)
        a_stop = self.monitor.evaluate_leland_trailing_stop(pos, current_price=469000.0)
        self.assertIsNotNone(a_stop)
        self.assertEqual(a_stop.action, "SELL")
        self.assertEqual(a_stop.reason, "BASELINE_HARD_STOP_6PCT")
        self.assertEqual(a_stop.quantity, 20)
        self.assertEqual(a_stop.severity, "CRITICAL")
        self.assertEqual(pos.current_quantity, 0)

    def test_tc17_peak_trailing_stop_baseline_volatility(self):
        """TC17: Standard -10.0% trailing stop from peak triggers under baseline volatility (M=1.0)."""
        pos = self.monitor.register_position("META", entry_price=100.0, quantity=100, market="NASDAQ", volatility_20d=0.02)
        # Price reaches peak of 115.0 (trailing stop is 115.0 * 0.90 = 103.50, which is above breakeven stop of 100.30)
        self.monitor.evaluate_profit_taking(pos, current_price=115.0)

        # Leland multiplier is 1.0, so trailing stop is 115 * (1 - 0.10) = 103.50
        # Price drops to 102.5 (breaches 103.50 trailing stop)
        a_trail = self.monitor.evaluate_leland_trailing_stop(pos, current_price=102.5, peak_price=115.0, volatility_20d=0.02)
        self.assertIsNotNone(a_trail)
        self.assertIn("TRAILING_STOP", a_trail.reason)
        self.assertEqual(a_trail.action, "SELL")

    def test_tc18_leland_adaptive_trailing_stop_high_volatility(self):
        """TC18: Leland adaptive trailing stop widens under high volatility (M=1.5), allowing wider pullback."""
        pos = self.monitor.register_position("AMD", entry_price=100.0, quantity=100, market="NASDAQ", volatility_20d=0.04)
        # Peak reaches 120.0
        pos.peak_price = 120.0
        # High vol multiplier: 1.0 + 0.5 * (0.04 - 0.02)/0.02 = 1.50
        # Trailing distance = 10% * 1.5 = 15.0%
        # Trailing stop price = 120 * (1 - 0.15) = 102.0
        # A pullback to 105.0 should NOT trigger stop under high vol!
        a_safe = self.monitor.evaluate_leland_trailing_stop(pos, current_price=105.0, peak_price=120.0, volatility_20d=0.04)
        self.assertIsNone(a_safe)

        # Pullback to 101.5 breaches the 102.0 stop
        a_stop = self.monitor.evaluate_leland_trailing_stop(pos, current_price=101.5, peak_price=120.0, volatility_20d=0.04)
        self.assertIsNotNone(a_stop)
        self.assertEqual(a_stop.action, "SELL")

    def test_tc19_leland_adaptive_trailing_stop_low_volatility_tightening(self):
        """TC19: Leland adaptive trailing stop tightens under low volatility (M=0.7), locking gains early."""
        pos = self.monitor.register_position("KO", entry_price=100.0, quantity=100, market="SP500", volatility_20d=0.008)
        # Peak reaches 120.0
        pos.peak_price = 120.0
        # Low vol multiplier: 1.0 + 0.5 * (0.008 - 0.02)/0.02 = 1.0 - 0.30 = 0.70
        # Trailing distance = 10% * 0.7 = 7.0%
        # Trailing stop price = 120 * (1 - 0.07) = 111.60
        # A drop to 110.0 breaches the tightened stop!
        a_stop = self.monitor.evaluate_leland_trailing_stop(pos, current_price=110.0, peak_price=120.0, volatility_20d=0.008)
        self.assertIsNotNone(a_stop)
        self.assertEqual(a_stop.action, "SELL")
        self.assertAlmostEqual(a_stop.details["effective_stop"], 111.60, places=1)

    # -----------------------------------------------------------------------
    # Category 6: Automated Flash-Crash Circuit Breakers (Asset 7% & VIX 20%)
    # -----------------------------------------------------------------------

    def test_tc20_single_asset_flash_crash_open_drop_7pct(self):
        """TC20: Single-asset intraday drop >= 7% from open price emits emergency liquidation order."""
        action = self.monitor.evaluate_flash_crash(
            symbol="005930",
            current_price=64800.0,  # 70,000 -> 64,800 is -7.43%
            open_price=70000.0,
            prev_close=69500.0,
            market="KOSPI",
            quantity=150,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.action, "SELL")
        self.assertEqual(action.symbol, "005930")
        self.assertTrue(action.force_liquidate)
        self.assertEqual(action.severity, "CRITICAL")
        self.assertEqual(action.reason, "FLASH_CRASH_ASSET_DROP_7PCT")
        self.assertLessEqual(action.details["drop_pct"], -0.07)

    def test_tc21_single_asset_flash_crash_prev_close_reference(self):
        """TC21: Flash crash references max(open, prev_close) when prev_close > open."""
        # Open = 100, Prev close = 105 -> ref_price = 105
        # Current = 97.0 -> drop from 105 is (97-105)/105 = -7.62% >= 7% drop
        action = self.monitor.evaluate_flash_crash(
            symbol="TSLA",
            current_price=97.0,
            open_price=100.0,
            prev_close=105.0,
            market="NASDAQ",
            quantity=50,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.action, "SELL")
        self.assertTrue(action.force_liquidate)
        self.assertAlmostEqual(action.trigger_price, 105.0)

    def test_tc22_sub_threshold_drop_does_not_trigger_circuit_breaker(self):
        """TC22: Intraday drop < 7.0% (e.g. -6.8%) does NOT trigger flash-crash circuit breaker."""
        # Open = 100, Prev close = 100 -> ref_price = 100
        # Current = 93.2 -> drop is -6.8%
        action = self.monitor.evaluate_flash_crash(
            symbol="AAPL",
            current_price=93.2,
            open_price=100.0,
            prev_close=100.0,
            market="NASDAQ",
            quantity=100,
        )
        self.assertIsNone(action)

    def test_tc23_macro_vix_surge_20pct_emits_gate8_inverse_hedge(self):
        """TC23: Macro VIX surge > 20% within 1 hour emits Gate 8 synthetic inverse hedge order."""
        # VIX 1h ago = 20.0, VIX current = 25.0 -> surge = +25.0% > 20.0%
        action = self.monitor.evaluate_macro_vix_surge(
            vix_current=25.0,
            vix_1h_ago=20.0,
            market="KOSPI",
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.action, "BUY_HEDGE")
        self.assertTrue(action.is_hedge)
        self.assertEqual(action.severity, "CRITICAL")
        self.assertEqual(action.reason, "FLASH_CRASH_VIX_SURGE_20PCT")
        self.assertEqual(action.target_hedge_instrument, "114800")  # KRX instrument

    def test_tc24_gate8_inverse_hedge_instrument_resolution(self):
        """TC24: Gate 8 inverse hedge resolves appropriate instruments across global markets."""
        self.assertEqual(self.monitor.resolve_hedge_instrument("KOSPI"), "114800")
        self.assertEqual(self.monitor.resolve_hedge_instrument("KOSDAQ"), "114800")
        self.assertEqual(self.monitor.resolve_hedge_instrument("KRX"), "114800")
        self.assertEqual(self.monitor.resolve_hedge_instrument("NASDAQ"), "PSQ")
        self.assertEqual(self.monitor.resolve_hedge_instrument("SP500"), "SH")
        self.assertEqual(self.monitor.resolve_hedge_instrument("RUSSELL2000"), "SH")
        self.assertEqual(self.monitor.resolve_hedge_instrument("GLOBAL"), "SH")
        self.assertEqual(self.monitor.resolve_hedge_instrument(symbol="005930"), "114800")
        self.assertEqual(self.monitor.resolve_hedge_instrument(symbol="AAPL"), "SH")

    def test_tc25_sub_threshold_vix_does_not_trigger_gate8_hedge(self):
        """TC25: VIX surge <= 20% (e.g. +18.0%) does NOT emit Gate 8 inverse hedge."""
        # VIX 1h ago = 20.0, current = 23.6 -> +18%
        action = self.monitor.evaluate_macro_vix_surge(
            vix_current=23.6,
            vix_1h_ago=20.0,
            market="NASDAQ",
        )
        self.assertIsNone(action)

    # -----------------------------------------------------------------------
    # Category 7: Multi-Holding Portfolio Batch Evaluation & Integration
    # -----------------------------------------------------------------------

    def test_tc26_evaluate_portfolio_batch_multi_market(self):
        """TC26: evaluate_portfolio handles 5-market portfolio with mixed triggers (profit, stop, crash)."""
        holdings = [
            {"symbol": "005930", "market": "KOSPI", "entry_price": 70000.0, "quantity": 100},  # will take Tier 1 profit (+6%)
            {"symbol": "035720", "market": "KOSDAQ", "entry_price": 50000.0, "quantity": 80},   # will flash crash (-8%)
            {"symbol": "AAPL", "market": "NASDAQ", "entry_price": 150.0, "quantity": 50},       # will hit hard stop (-7%)
            {"symbol": "MSFT", "market": "SP500", "entry_price": 400.0, "quantity": 40},        # normal hold (+1%)
            {"symbol": "IWM", "market": "RUSSELL2000", "entry_price": 200.0, "quantity": 60},   # normal hold (0%)
        ]

        market_data = {
            "005930": {"current_price": 74200.0, "open_price": 71000.0, "prev_close": 70000.0},
            "035720": {"current_price": 45500.0, "open_price": 50000.0, "prev_close": 50000.0},  # -9% from 50k
            "AAPL": {"current_price": 139.0, "open_price": 145.0, "prev_close": 145.0},          # -7.33% from 150 entry
            "MSFT": {"current_price": 404.0, "open_price": 402.0, "prev_close": 400.0},
            "IWM": {"current_price": 200.0, "open_price": 200.0, "prev_close": 200.0},
        }

        vix_data = {
            "vix_current": 26.0,
            "vix_1h_ago": 20.0,  # +30% VIX surge -> triggers macro hedge
            "market": "GLOBAL",
        }

        actions = self.monitor.evaluate_portfolio(holdings, market_data, vix_data)
        self.assertGreaterEqual(len(actions), 3)

        reasons = [a.reason for a in actions]
        self.assertIn("FLASH_CRASH_VIX_SURGE_20PCT", reasons)
        self.assertIn("FLASH_CRASH_ASSET_DROP_7PCT", reasons)
        self.assertIn("PROFIT_TAKING_TIER1_5PCT", reasons)

    def test_tc27_evaluate_portfolio_dictionary_holdings_input(self):
        """TC27: evaluate_portfolio supports dictionary of holdings keyed by symbol."""
        holdings_dict = {
            "005930": {"market": "KOSPI", "entry_price": 70000.0, "quantity": 100},
            "AAPL": {"market": "NASDAQ", "entry_price": 150.0, "quantity": 50},
        }
        market_data = {
            "005930": {"current_price": 75000.0, "open_price": 71000.0, "prev_close": 70000.0},
            "AAPL": {"current_price": 152.0, "open_price": 150.0, "prev_close": 150.0},
        }
        actions = self.monitor.evaluate_portfolio(holdings_dict, market_data)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].symbol, "005930")
        self.assertEqual(actions[0].reason, "PROFIT_TAKING_TIER1_5PCT")

    def test_tc28_state_persistence_and_reset(self):
        """TC28: Test position registration, active stops snapshot, and reset_state."""
        self.monitor.register_position("005930", entry_price=70000.0, quantity=100)
        self.monitor.register_position("AAPL", entry_price=150.0, quantity=50)

        stops = self.monitor.get_active_stops()
        self.assertIn("005930", stops)
        self.assertIn("AAPL", stops)
        self.assertEqual(len(stops), 2)

        self.monitor.reset_state()
        self.assertEqual(len(self.monitor.positions), 0)
        self.assertEqual(len(self.monitor.get_active_stops()), 0)

    def test_tc29_resilience_to_missing_corrupt_data(self):
        """TC29: Monitor tolerates missing symbols, negative prices, and NaNs without raising exceptions."""
        holdings = [
            {"symbol": "CORRUPT_1", "entry_price": 0.0, "quantity": 10},
            {"symbol": "CORRUPT_2", "entry_price": float('nan'), "quantity": 10},
            {"symbol": "VALID_SYM", "entry_price": 100.0, "quantity": 50},
        ]
        market_data = {
            "CORRUPT_1": {"current_price": -50.0},
            "CORRUPT_2": {"current_price": float('inf')},
            "VALID_SYM": {"current_price": 100.0},
        }
        vix_data = {"vix_current": float('nan'), "vix_1h_ago": 20.0}

        actions = self.monitor.evaluate_portfolio(holdings, market_data, vix_data)
        self.assertIsInstance(actions, list)

    def test_tc30_oms_engine_compatibility_contract(self):
        """TC30: Ensure emitted RiskAction strictly conforms to ExecutionOMSEngine order fields."""
        action = self.monitor.evaluate_flash_crash(
            symbol="005930",
            current_price=64000.0,
            open_price=70000.0,
            prev_close=70000.0,
            market="KOSPI",
            quantity=100,
        )
        self.assertIsNotNone(action)
        d = action.to_dict()

        # Contract assertions for OMS compatibility
        required_keys = ["action_id", "symbol", "market", "action", "quantity", "trigger_price", "current_price", "stop_price", "reason", "severity", "force_liquidate"]
        for k in required_keys:
            self.assertIn(k, d)
            self.assertIsNotNone(d[k])

        self.assertIn(d["action"], ("BUY", "SELL", "BUY_HEDGE", "HOLD"))
        self.assertGreater(d["quantity"], 0)
        self.assertIsInstance(d["force_liquidate"], bool)


if __name__ == "__main__":
    unittest.main()

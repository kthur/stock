"""
tests/test_phase111_adversarial_challenger2.py
=============================================
Empirical Adversarial Stress Testing & Boundary Invariant Suite for Phase 111.
Release R127 / v118 Production Master (Features F527 & F528).

Challenger 2 Dedicated Verification:
1. BorrowDynamicsModel & ExecutionOMSEngine Gate 8.1:
   - Extreme loan utilization (U -> 1.0, U = 1.0, U > 1.0, U -> 1 - eps)
   - Non-linear fee escalation without division by zero
   - SEC Rule 203(b)(1) affirmative locate exhaustion and ledger auditing
   - Gate 8.1 strict rejection on locate unavailability or recall risk >= 0.80
   - Explosive short squeeze trigger (S_squeeze >= 0.75) -> MOMENTUM_SQUEEZE transition with AGGRESSIVE_TAKER execution
   - Negative carry penalty and economic hurdle rejection
2. TriangularArbitrageSlicer & SmartOrderRouter:
   - Multi-type point-in-time discrepancy detection (ADR/ORD, ETF/Basket, FX Triangles)
   - Strict Zero Lookahead Bias enforcement (t_quote > t_eval -> LookaheadBiasException)
   - Atomic Leader-Follower execution sequence and zero slippage Limit IOC pricing
   - Simulated partial fills on leader leg: sub-50ms emergency unwinding & Zero Naked Overnight Delta (Delta_naked = 0)
   - Slicing trajectory: 1.5% ADV participation cap and exact integer share volume conservation
   - Comprehensive round-trip friction modeling (spread, fees, rebates, KRX STT, SEC fees, borrow carry, Kyle impact)
   - SmartOrderRouter multi-venue routing hook and sub-hurdle skipping
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = REPO_ROOT / "trading_system"

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.borrow_dynamics_model import (
    BorrowDynamicsModel,
    BorrowFeeQuote,
    BorrowState,
    LocateResult,
    NegativeCarryResult,
    SqueezeEvaluationResult,
    Gate8_1Verdict,
)
from src.execution.triangular_arbitrage_slicer import (
    TriangularArbitrageSlicer,
    ArbitrageTriplet,
    ArbitrageLegSpec,
    ArbitrageType,
    OrderLegSide,
    OrderLegType,
    UnwindMode,
    VenueQuote,
    LookaheadBiasException,
    TriangularSliceSchedule,
    TriangularArbitrageExecutionReport,
    LegExecutionFill,
    PartialFillUnwindPlan,
    FrictionBreakdown,
    ArbitrageDiscrepancy,
)
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.smart_order_router import SmartOrderRouter


class TestPhase111BorrowDynamicsAdversarialChallenger2(unittest.TestCase):
    """Adversarial stress testing suite for BorrowDynamicsModel and Gate 8.1."""

    def setUp(self) -> None:
        self.model = BorrowDynamicsModel()
        self.oms = ExecutionOMSEngine(db_path=":memory:", version=111)

    # -------------------------------------------------------------------------
    # 1. Extreme Loan Utilization & Fee Escalation Bounds
    # -------------------------------------------------------------------------
    def test_adv_borrow_01_utilization_boundary_clamping(self) -> None:
        """Verify U(t) strictly clamped to [0.0, 1.0] across degenerate inputs."""
        # Oversubscribed loan
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=2_000_000, lendable_inventory=1_000_000), 1.0)
        # Saturated zero inventory with positive loan
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=50_000, lendable_inventory=0), 1.0)
        # Zero inventory with zero loan
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=0, lendable_inventory=0), 0.0)
        # Negative loan shares
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=-500, lendable_inventory=1_000_000), 0.0)
        # Negative lendable inventory
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=100, lendable_inventory=-500), 1.0)
        # Non-finite inputs
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=float("nan"), lendable_inventory=100_000), 0.0)
        self.assertEqual(self.model.calculate_loan_utilization(shares_on_loan=10_000, lendable_inventory=float("inf")), 0.0)

    def test_adv_borrow_02_fee_explosion_without_zero_division(self) -> None:
        """Verify non-linear fee escalation U -> 1.0 is strictly finite, positive, and monotonic."""
        utilizations = [0.0, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.98, 0.99, 0.9999, 1.0]
        fees = []
        for u in utilizations:
            fee = self.model.calculate_borrow_fee(utilization=u, market="SP500")
            self.assertTrue(math.isfinite(fee), f"Fee for U={u} must be finite, got {fee}")
            self.assertGreaterEqual(fee, 0.0030, f"Fee for U={u} cannot be below GC rate 30 bps")
            fees.append(fee)

        # Monotonicity check
        for i in range(1, len(fees)):
            self.assertGreaterEqual(fees[i], fees[i - 1], f"Fee at U={utilizations[i]} failed monotonicity")

        # HTB threshold check: at U >= 0.85, fee must be elevated
        fee_at_99 = self.model.calculate_borrow_fee(utilization=0.99, market="SP500")
        self.assertGreater(fee_at_99, 0.10, "Fee at 99% utilization must exceed 10% HTB threshold")

        # Zero epsilon resilience
        custom_model = BorrowDynamicsModel(epsilon_util=0.0)
        fee_sat_zero_eps = custom_model.calculate_borrow_fee(utilization=1.0, market="SP500")
        self.assertTrue(math.isfinite(fee_sat_zero_eps), "Fee with epsilon=0 at U=1.0 must be stabilized by safety denom")

    def test_adv_borrow_03_inventory_depletion_velocity_robustness(self) -> None:
        """Stress-test inventory depletion velocity under non-finite and extreme inputs."""
        # Empty and single-element inputs
        self.assertEqual(self.model.calculate_inventory_depletion_velocity([]), 0.0)
        self.assertEqual(self.model.calculate_inventory_depletion_velocity([0.8]), 0.0)

        # Direct scalar input
        self.assertEqual(self.model.calculate_inventory_depletion_velocity(0.12), 0.12)
        self.assertEqual(self.model.calculate_inventory_depletion_velocity(float("nan")), 0.0)

        # Rapid surge
        v_surge = self.model.calculate_inventory_depletion_velocity([0.50, 0.65, 0.80, 0.95], dt_days=1.0)
        self.assertAlmostEqual(v_surge, (0.95 - 0.50) / 3.0, places=4)

        # Negative depletion (inventory replenishing)
        v_replenish = self.model.calculate_inventory_depletion_velocity([0.90, 0.70, 0.50], dt_days=1.0)
        self.assertLess(v_replenish, 0.0)

    # -------------------------------------------------------------------------
    # 2. Affirmative Locate Exhaustion (SEC Rule 203(b)(1)) & Recall Risk
    # -------------------------------------------------------------------------
    def test_adv_borrow_04_sec_rule_203_affirmative_locate_exhaustion(self) -> None:
        """Verify affirmative locate is strictly rejected when inventory is exhausted or saturated."""
        # Case 1: Utilization >= 98%
        res_sat = self.model.check_locate_availability(
            symbol="HTB_SYM", requested_shares=100, lendable_shares=100_000, shares_on_loan=98_500
        )
        self.assertFalse(res_sat.locate_approved)
        self.assertIn("utilization=", res_sat.reason)
        self.assertEqual(res_sat.available_shares, 0.0)

        # Case 2: Available shares < requested shares
        res_exceed = self.model.check_locate_availability(
            symbol="HTB_SYM", requested_shares=50_000, lendable_shares=100_000, shares_on_loan=80_000
        )
        self.assertFalse(res_exceed.locate_approved)
        self.assertIn("Insufficient lendable volume", res_exceed.reason)

        # Case 3: Compliant locate approved with unique ID in ledger
        res_ok = self.model.check_locate_availability(
            symbol="GC_SYM", requested_shares=1_000, lendable_shares=100_000, shares_on_loan=10_000
        )
        self.assertTrue(res_ok.locate_approved)
        self.assertGreater(res_ok.available_shares, 1_000)
        self.assertTrue(res_ok.locate_id.startswith("LOC_GC_SYM_"))
        self.assertIn("GC_SYM", self.model._locate_ledger)

    def test_adv_borrow_05_gate_8_1_strict_short_rejections(self) -> None:
        """Verify Gate 8.1 strictly blocks short orders on locate failure or acute recall risk >= 0.80."""
        # 1. Rejection on missing locate
        q_no_locate = BorrowFeeQuote(symbol="TEST1", locate_available=False, locate_fraction=0.01)
        v1 = self.model.evaluate_gate_8_1({"symbol": "TEST1", "action": "SHORT"}, borrow_quote=q_no_locate)
        self.assertEqual(v1.status, "REJECTED")
        self.assertEqual(v1.reason, "NO_AFFIRMATIVE_LOCATE")
        self.assertEqual(v1.recommended_sleeve, "CASH_OVERLAY")

        # 2. Rejection on acute recall risk (score >= 0.80)
        q_acute_recall = BorrowFeeQuote(symbol="TEST2", locate_available=True, locate_fraction=0.5, recall_risk_score=0.85)
        v2 = self.model.evaluate_gate_8_1({"symbol": "TEST2", "action": "SELL_SHORT"}, borrow_quote=q_acute_recall)
        self.assertEqual(v2.status, "REJECTED")
        self.assertEqual(v2.reason, "ACUTE_RECALL_RISK")

        # 3. ExecutionOMSEngine delegation verification
        v_oms = self.oms.evaluate_gate_8_1({"symbol": "TEST1", "action": "SHORT"}, borrow_quote=q_no_locate)
        self.assertEqual(v_oms.status, "REJECTED")
        self.assertEqual(v_oms.reason, "NO_AFFIRMATIVE_LOCATE")

    # -------------------------------------------------------------------------
    # 3. Explosive Squeeze Trigger & MOMENTUM_SQUEEZE Transition
    # -------------------------------------------------------------------------
    def test_adv_borrow_06_explosive_squeeze_trigger_and_taker_execution(self) -> None:
        """Verify S_squeeze >= 0.75 triggers MOMENTUM_SQUEEZE and AGGRESSIVE_TAKER execution."""
        # Calculate squeeze score with explosive conditions: SIR=40%, DTC=10, U=96%, mom=+20%, RVOL=2.5
        score = self.model.calculate_squeeze_score(
            sir=0.40, dtc=10.0, utilization=0.96, upward_momentum=0.20, relative_volume=2.5
        )
        self.assertGreaterEqual(score, 0.75, f"Expected S_squeeze >= 0.75, got {score}")

        # Short order into this squeeze MUST be blocked
        q_squeeze = BorrowFeeQuote(
            symbol="SQUEEZE_CO",
            locate_available=True,
            locate_fraction=0.4,
            utilization_rate=0.96,
            days_to_cover=10.0,
            short_interest_ratio=0.40,
            depletion_velocity=0.08,  # > 0.05 depletion velocity
        )
        v_short = self.model.evaluate_gate_8_1({"symbol": "SQUEEZE_CO", "action": "SHORT"}, borrow_quote=q_squeeze)
        self.assertEqual(v_short.status, "REJECTED")
        self.assertEqual(v_short.reason, "SHORT_SQUEEZE_BREAKOUT_RISK")

        # Long order into this squeeze MUST transition to MOMENTUM_SQUEEZE with AGGRESSIVE_TAKER
        order_long = {"symbol": "SQUEEZE_CO", "action": "BUY", "target_price": 50.0}
        v_long = self.model.evaluate_gate_8_1(order_long, borrow_quote=q_squeeze)
        self.assertEqual(v_long.status, "MODIFIED")
        self.assertEqual(v_long.recommended_sleeve, "MOMENTUM_SQUEEZE")
        self.assertEqual(v_long.recommended_exec_strategy, "AGGRESSIVE_TAKER")
        self.assertEqual(v_long.slice_count_multiplier, 0.5)
        self.assertAlmostEqual(v_long.target_stop_loss, 50.0 * 0.95, places=2)

    # -------------------------------------------------------------------------
    # 4. Negative Carry Penalty & Economic Hurdle Rejection
    # -------------------------------------------------------------------------
    def test_adv_borrow_07_negative_carry_drag_and_hurdle_rejection(self) -> None:
        """Verify borrow fees erode expected return and trigger NEGATIVE_CARRY_DRAG rejection."""
        # 45% annual borrow fee on a 20-day holding horizon = 45% * (20/252) = 3.57% drag
        carry = self.model.calculate_negative_carry(
            borrow_fee_annual=0.45, holding_days=20.0, expected_alpha=0.0200, hurdle_rate=0.0010
        )
        # Net alpha = 2.0% - 3.57% = -1.57%
        self.assertLess(carry.net_alpha, 0.0)
        self.assertFalse(carry.is_economically_viable)
        self.assertAlmostEqual(carry.daily_cost_bps, (0.45 / 365.0) * 10000.0, places=2)

        # Gate 8.1 rejection
        q_htb = BorrowFeeQuote(
            symbol="COSTLY_SHORT",
            locate_available=True,
            locate_fraction=0.8,
            borrow_fee_annual=0.45,
            utilization_rate=0.75,
            days_to_cover=2.0,
            short_interest_ratio=0.05,
        )
        order = {"symbol": "COSTLY_SHORT", "action": "SELL_SHORT", "expected_return": 0.015} # 1.5% alpha
        verdict = self.model.evaluate_gate_8_1(order, borrow_quote=q_htb)
        self.assertEqual(verdict.status, "REJECTED")
        self.assertEqual(verdict.reason, "NEGATIVE_CARRY_DRAG")


class TestPhase111TriangularArbitrageAdversarialChallenger2(unittest.TestCase):
    """Adversarial stress testing suite for TriangularArbitrageSlicer and routing hooks."""

    def setUp(self) -> None:
        self.slicer = TriangularArbitrageSlicer(hurdle_rate_bps=2.5, max_adv_participation_rate=0.015)
        self.sor = SmartOrderRouter(version=111)

    # -------------------------------------------------------------------------
    # 1. Multi-Type Point-in-Time Discrepancy Detection
    # -------------------------------------------------------------------------
    def test_adv_tri_01_adr_ord_discrepancy_and_reverse_direction(self) -> None:
        """Verify ADR/ORD discrepancy detection in reverse direction (underpriced ADR)."""
        triplet = ArbitrageTriplet(
            triplet_id="ADR_REVERSE_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER, is_us=True),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
            depositary_ratio=5.0,
            hurdle_rate_bps=2.5,
        )
        now = 1_000_000_000
        # ORD is expensive (1200 TWD), ADR is cheap (170 USD), FX is 32.0:
        # 1 ADR = 5 ORD -> 5 * 1200 / 32 = 187.50 USD theoretical value vs 170 USD market price
        quotes = {
            "TSM": VenueQuote(symbol="TSM", bid_price=170.0, ask_price=170.05, timestamp_ns=now),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1200.0, ask_price=1200.5, timestamp_ns=now),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=now),
        }
        opp = self.slicer.detect_discrepancy(triplet, quotes, evaluation_time_ns=now)
        self.assertIsNotNone(opp)
        self.assertEqual(opp.direction, "REVERSE")
        self.assertTrue(opp.is_actionable)
        self.assertEqual(opp.leg_actions[1]["side"], "BUY")   # Buy underpriced ADR
        self.assertEqual(opp.leg_actions[2]["side"], "SELL")  # Sell overpriced ORD

    def test_adv_tri_02_etf_basket_creation_and_redemption(self) -> None:
        """Verify ETF vs Basket arbitrage for both creation (premium) and redemption (discount)."""
        triplet = ArbitrageTriplet(
            triplet_id="ETF_TEST",
            triplet_type=ArbitrageType.ETF_BASKET,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="SPY", market="SP500", leg_role=OrderLegType.LEADER),
                ArbitrageLegSpec(leg_id=2, symbol="SP500_BASKET", market="SP500", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=3, symbol="USD_CASH", market="MONEY_MARKET", leg_role=OrderLegType.HEDGE),
            ),
            hurdle_rate_bps=2.5,
        )
        now = 1_000_000_000
        # Premium: ETF at 510, Basket at 500 -> Creation (Sell ETF, Buy Basket)
        quotes_prem = {
            "SPY": VenueQuote(symbol="SPY", bid_price=510.0, ask_price=510.05, timestamp_ns=now),
            "SP500_BASKET": VenueQuote(symbol="SP500_BASKET", bid_price=499.95, ask_price=500.0, timestamp_ns=now),
            "USD_CASH": VenueQuote(symbol="USD_CASH", bid_price=1.0, ask_price=1.0, timestamp_ns=now),
        }
        opp_prem = self.slicer.detect_discrepancy(triplet, quotes_prem, evaluation_time_ns=now)
        self.assertIsNotNone(opp_prem)
        self.assertEqual(opp_prem.direction, "CREATION")
        self.assertTrue(opp_prem.is_actionable)
        self.assertEqual(opp_prem.leg_actions[1]["side"], "SELL")
        self.assertEqual(opp_prem.leg_actions[2]["side"], "BUY")

        # Discount: ETF at 490, Basket at 500 -> Redemption (Buy ETF, Sell Basket)
        quotes_disc = {
            "SPY": VenueQuote(symbol="SPY", bid_price=490.0, ask_price=490.05, timestamp_ns=now),
            "SP500_BASKET": VenueQuote(symbol="SP500_BASKET", bid_price=500.0, ask_price=500.05, timestamp_ns=now),
            "USD_CASH": VenueQuote(symbol="USD_CASH", bid_price=1.0, ask_price=1.0, timestamp_ns=now),
        }
        opp_disc = self.slicer.detect_discrepancy(triplet, quotes_disc, evaluation_time_ns=now)
        self.assertIsNotNone(opp_disc)
        self.assertEqual(opp_disc.direction, "REDEMPTION")
        self.assertTrue(opp_disc.is_actionable)
        self.assertEqual(opp_disc.leg_actions[1]["side"], "BUY")
        self.assertEqual(opp_disc.leg_actions[2]["side"], "SELL")

    def test_adv_tri_03_cross_currency_fx_triangular_parity(self) -> None:
        """Verify cross-currency FX triangle parity: EUR/USD * USD/KRW vs EUR/KRW."""
        triplet = ArbitrageTriplet(
            triplet_id="FX_TRIANGLE",
            triplet_type=ArbitrageType.CROSS_CURRENCY_FX,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="EUR/USD", market="FX", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="USD/KRW", market="FX", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=3, symbol="EUR/KRW", market="FX", leg_role=OrderLegType.LEADER),
            ),
            hurdle_rate_bps=1.0,
        )
        now = 1_000_000_000
        # Synthetic EUR/KRW = 1.08 * 1350 = 1458.0. Actual quote at 1440.0 (synthetic premium)
        quotes = {
            "EUR/USD": VenueQuote(symbol="EUR/USD", bid_price=1.0800, ask_price=1.0801, timestamp_ns=now),
            "USD/KRW": VenueQuote(symbol="USD/KRW", bid_price=1350.0, ask_price=1350.1, timestamp_ns=now),
            "EUR/KRW": VenueQuote(symbol="EUR/KRW", bid_price=1440.0, ask_price=1440.2, timestamp_ns=now),
        }
        opp = self.slicer.detect_discrepancy(triplet, quotes, evaluation_time_ns=now)
        self.assertIsNotNone(opp)
        self.assertEqual(opp.direction, "FORWARD")
        self.assertTrue(opp.is_actionable)

    # -------------------------------------------------------------------------
    # 2. Strict Zero Lookahead Bias Enforcement
    # -------------------------------------------------------------------------
    def test_adv_tri_04_strict_lookahead_bias_rejection(self) -> None:
        """Verify LookaheadBiasException is strictly raised when any quote timestamp > eval_time_ns."""
        triplet = ArbitrageTriplet(
            triplet_id="BIAS_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500"),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE"),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX"),
            ),
        )
        t_eval = 5_000_000_000

        # Sub-test 1: 1 nanosecond into the future
        future_1ns = {
            "TSM": VenueQuote(symbol="TSM", timestamp_ns=t_eval + 1),
            "2330.TW": VenueQuote(symbol="2330.TW", timestamp_ns=t_eval),
            "USD/TWD": VenueQuote(symbol="USD/TWD", timestamp_ns=t_eval),
        }
        with self.assertRaises(LookaheadBiasException):
            self.slicer.detect_discrepancy(triplet, future_1ns, evaluation_time_ns=t_eval)

        # Sub-test 2: 1 second into the future
        future_1s = {
            "TSM": VenueQuote(symbol="TSM", timestamp_ns=t_eval),
            "2330.TW": VenueQuote(symbol="2330.TW", timestamp_ns=t_eval + 1_000_000_000),
            "USD/TWD": VenueQuote(symbol="USD/TWD", timestamp_ns=t_eval),
        }
        with self.assertRaises(LookaheadBiasException):
            self.slicer.detect_discrepancy(triplet, future_1s, evaluation_time_ns=t_eval)

        # Sub-test 3: Past and exact timestamps pass without exception
        valid_quotes = {
            "TSM": VenueQuote(symbol="TSM", timestamp_ns=t_eval - 100),
            "2330.TW": VenueQuote(symbol="2330.TW", timestamp_ns=t_eval),
            "USD/TWD": VenueQuote(symbol="USD/TWD", timestamp_ns=t_eval - 1),
        }
        try:
            self.slicer.detect_discrepancy(triplet, valid_quotes, evaluation_time_ns=t_eval)
        except LookaheadBiasException:
            self.fail("LookaheadBiasException raised unexpectedly on valid past/current timestamps")

    # -------------------------------------------------------------------------
    # 3. Atomic Leader-Follower Execution & Emergency Unwinding (<= 50ms, Zero Delta)
    # -------------------------------------------------------------------------
    def test_adv_tri_05_leader_follower_execution_and_clamped_ioc(self) -> None:
        """Verify leader leg executes first and Limit IOC clamp guarantees 0.0 slippage."""
        triplet = ArbitrageTriplet(
            triplet_id="LEADER_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
        )
        quotes = {
            "TSM": VenueQuote(symbol="TSM", bid_price=175.0, ask_price=175.05),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1100.0, ask_price=1100.5),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01),
        }
        fills, unwind = self.slicer.execute_atomic_tranche(triplet, {1: 100, 2: 500, 3: 100}, quotes)
        self.assertIsNone(unwind)
        self.assertEqual(len(fills), 3)
        # Leader leg executed first
        self.assertEqual(fills[0].leg_id, 2)
        self.assertEqual(fills[0].symbol, "2330.TW")
        # Zero adverse slippage verified across all fills
        for f in fills:
            self.assertEqual(f.slippage_bps, 0.0)
            self.assertEqual(f.fill_price, f.limit_price)

    def test_adv_tri_06_simulated_partial_fill_emergency_unwind_and_zero_naked_delta(self) -> None:
        """Verify emergency unwinding strictly executes within <= 50ms and enforces Zero Naked Delta."""
        triplet = ArbitrageTriplet(
            triplet_id="PARTIAL_UNWIND_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0, side=OrderLegSide.BUY),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
            depositary_ratio=1.0,
            max_unwind_latency_ms=50.0,
        )
        quotes = {
            "TSM": VenueQuote(symbol="TSM"),
            "2330.TW": VenueQuote(symbol="2330.TW"),
            "USD/TWD": VenueQuote(symbol="USD/TWD"),
        }

        # Simulate 25% partial fill on leader leg (400 requested -> 100 filled)
        fills, unwind = self.slicer.execute_atomic_tranche(
            triplet, {1: 400, 2: 400, 3: 400}, quotes, partial_fill_ratio=0.25
        )

        self.assertIsNotNone(unwind)
        self.assertTrue(unwind.zero_naked_delta_guarantee)
        self.assertLessEqual(unwind.max_latency_ms, 50.0)
        # Leader was BUY -> Unwind action must be SELL
        self.assertEqual(unwind.unwind_action, "SELL")
        self.assertEqual(unwind.unwind_order_type, "LIMIT_IOC")

        # Full end-to-end arbitrage execution under partial fill
        t_now = time.time_ns()
        quotes_actionable = {
            "TSM": VenueQuote(symbol="TSM", bid_price=185.0, ask_price=185.05, timestamp_ns=t_now),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, timestamp_ns=t_now),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
        }
        report = self.slicer.execute_full_arbitrage(
            triplet, quotes_actionable, target_size=1000, evaluation_time_ns=t_now, simulate_partial_fill_at_tranche=1
        )
        self.assertEqual(report.status, "EMERGENCY_UNWOUND")
        self.assertTrue(report.zero_naked_delta_verified)
        self.assertIsNotNone(report.unwind_plan)

    # -------------------------------------------------------------------------
    # 4. Slicing Trajectory: 1.5% ADV Participation Cap & Exact Volume Conservation
    # -------------------------------------------------------------------------
    def test_adv_tri_07_adv_participation_cap_and_exact_integer_conservation(self) -> None:
        """Verify tranches never exceed 1.5% ADV and exact integer conservation holds for arbitrary targets."""
        triplet = ArbitrageTriplet(
            triplet_id="CONSERVATION_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500"),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE"),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX"),
            ),
            max_adv_participation_rate=0.015,
        )
        quotes = {
            "TSM": VenueQuote(symbol="TSM", adv_shares=200_000.0),        # 1.5% ADV = 3,000 shares
            "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=400_000.0), # 1.5% ADV = 6,000 shares
            "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=50_000_000.0),
        }

        # Test various non-round and prime quantities
        test_quantities = [7, 101, 7919, 10007, 25000, 100000]
        for q_target in test_quantities:
            targets = {1: q_target, 2: q_target * 2, 3: q_target}
            sched = self.slicer.compute_slicing_schedule(triplet, targets, quotes)

            self.assertTrue(sched.integer_conservation_passed, f"Conservation failed for target {q_target}")
            self.assertEqual(sum(sched.slice_tranches[1]), q_target)
            self.assertEqual(sum(sched.slice_tranches[2]), q_target * 2)
            self.assertEqual(sum(sched.slice_tranches[3]), q_target)

            # Check that dynamic slice count is within bounds [3, 12] for standard orders, or expanded for large orders
            self.assertGreaterEqual(sched.n_slices, 3)
            if q_target <= 25000:
                self.assertLessEqual(sched.n_slices, 12)
            else:
                self.assertGreaterEqual(sched.n_slices, 13)

            # Check 1.5% ADV cap for Leg 1
            for tranche_qty in sched.slice_tranches[1]:
                part_rate = tranche_qty / quotes["TSM"].adv_shares
                self.assertLessEqual(part_rate, 0.01500001, f"Tranche {tranche_qty} exceeded 1.5% ADV on target {q_target}")

    # -------------------------------------------------------------------------
    # 5. SmartOrderRouter Multi-Venue Routing & Sub-Hurdle Filtering
    # -------------------------------------------------------------------------
    def test_adv_tri_08_smart_order_router_dark_pool_probing_and_sub_hurdle(self) -> None:
        """Verify SmartOrderRouter dark pool routing for followers and sub-hurdle skipping."""
        triplet = ArbitrageTriplet(
            triplet_id="SOR_ROUTING_TEST",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", leg_role=OrderLegType.FOLLOWER, is_us=True),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", leg_role=OrderLegType.HEDGE),
            ),
            depositary_ratio=5.0,
            hurdle_rate_bps=2.5,
        )
        t_now = time.time_ns()

        # 1. Actionable opportunity -> ROUTED
        quotes_act = {
            "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.05, timestamp_ns=t_now),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1119.5, ask_price=1120.0, timestamp_ns=t_now),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=t_now),
        }
        res_act = self.sor.route_triangular_arbitrage(triplet, quotes_act)
        self.assertEqual(res_act["status"], "ROUTED")
        self.assertTrue(res_act["is_atomic"])

        # Check dark pool midpoint routing for US follower leg
        tsm_leg = next(l for l in res_act["routed_legs"] if l["symbol"] == "TSM")
        self.assertEqual(tsm_leg["venue"], "ATS_DARK_POOL_MIDPOINT")
        self.assertEqual(tsm_leg["order_type"], "MIDPOINT_PEG")

        # 2. Sub-hurdle opportunity -> SKIPPED
        quotes_sub = {
            "TSM": VenueQuote(symbol="TSM", bid_price=180.0, ask_price=180.01, timestamp_ns=t_now),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=1152.0, ask_price=1152.01, timestamp_ns=t_now),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.001, timestamp_ns=t_now),
        }
        res_sub = self.sor.route_triangular_arbitrage(triplet, quotes_sub)
        self.assertEqual(res_sub["status"], "SKIPPED")
        self.assertEqual(res_sub["reason"], "OPPORTUNITY_SUB_HURDLE")


if __name__ == "__main__":
    unittest.main()

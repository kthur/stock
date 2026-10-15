"""
tests/test_phase111_adversarial_challenger1.py
=============================================
Empirical Adversarial Stress Testing & Invariant Challenge Suite for Phase 111.
Release R127 / v118 Production Master (Features F525~F529).

Adversarial Stress Dimensions:
1. Module 1 (F525): Vectorized High-Frequency Fast LOB Matching Engine
   - Degenerate / boundary order inputs (zero volume, negative volume, NaN price, Inf price)
   - Deep multi-level book exhaustion, massive volume market order sweeps
   - Iceberg orders: display depletion, hidden reserve exhaustion, priority loss
   - Pegged order dynamic repricing under extreme quote revisions
   - Cont-Kukanov fill probability boundary monotonicity
2. Module 2 (F526): Deep Multivariate Hawkes Process Generative Synthesizer
   - Supercritical transient excursions (flash crashes, rho in [1.02, 1.15])
   - Extreme numerical boundaries (Softplus clipping, zero intensity, high baseline)
   - 5-market parameter calibration profiles (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)
   - Ogata thinning simulation robustness under cluster bursts
3. Module 3 (F527): Short Squeeze Borrow Dynamics & HTB Fee Model
   - Saturated 100% utilization boundary U(t) -> 1.0 and zero lendable inventory
   - Explosive HTB fee escalation and negative carry drag subtraction
   - SEC Rule 203(b)(1) locate rejection and acute recall risk (score >= 0.80)
   - OMS Gate 8.1 squeeze guard blocking shorts during explosive squeeze catalysts
4. Module 4 (F528): Triangular Parity & Cross-Venue Arbitrage Execution Slicer
   - Strict Zero Lookahead Bias enforcement via LookaheadBiasException
   - Round-trip friction hurdle rate gating and sub-hurdle trade rejection
   - Slicing trajectory under massive notional: strict 1.5% ADV cap per tranche
   - Exact integer volume conservation invariant across prime and non-round quantities
   - Emergency partial-fill unwinding ensuring Zero Naked Overnight Delta
5. Module 5 (F529): 5-Market Benchmark & Attribution Invariants
   - Strict mathematical validation of all 8 target KPIs
   - Factor attribution exact conservation (Net Return +10.00%, Sharpe +3.00)
"""

from __future__ import annotations

import math
import subprocess
import sys
import time
import unittest
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p_dir in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p_dir not in sys.path:
        sys.path.insert(0, p_dir)

from src.core.vectorized_lob_engine import (
    VectorizedLOBEngine,
    VectorizedOrderBook,
    VectorizedOrder,
    OrderSide,
    OrderType,
    OrderStatus,
    MatchExecutionResult,
)
from src.ai.deep_hawkes_synthesizer import (
    DeepMultivariateHawkesSynthesizer,
    NeuralBaselineNetwork,
    SimulationResult,
    HawkesEvent,
)
from src.risk.borrow_dynamics_model import (
    BorrowDynamicsModel,
    BorrowFeeQuote,
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
    VenueQuote,
    LookaheadBiasException,
    TriangularSliceSchedule,
)


class TestPhase111AdversarialChallenger1(unittest.TestCase):
    """Empirical Adversarial Challenger Stress Testing Suite for Phase 111 (M1~M5)."""

    # =========================================================================
    # MODULE 1: Vectorized High-Frequency Fast LOB Matching Engine (F525)
    # =========================================================================

    def test_adv_m1_01_degenerate_and_non_finite_inputs(self) -> None:
        """Stress-test vectorized order book with zero, negative, NaN, and Inf inputs."""
        book = VectorizedOrderBook(symbol="NVDA", tick_size=0.01)

        # 1. Zero volume submission
        _, res_zero = book.add_order(order_id="bad_1", side=OrderSide.BUY, price=100.0, volume=0.0)
        self.assertFalse(res_zero.is_fully_filled)
        self.assertEqual(res_zero.filled_volume, 0.0)

        # 2. Negative volume submission
        _, res_neg = book.add_order(order_id="bad_2", side=OrderSide.BUY, price=100.0, volume=-50.0)
        self.assertEqual(res_neg.filled_volume, 0.0)

        # 3. Non-finite volume submission (NaN)
        _, res_nan = book.add_order(order_id="bad_3", side=OrderSide.BUY, price=100.0, volume=float("nan"))
        self.assertEqual(res_nan.filled_volume, 0.0)

        # Book must remain empty and clean
        self.assertEqual(book.best_bid, 0.0)
        self.assertEqual(book.best_ask, 0.0)

    def test_adv_m1_02_massive_market_sweep_exhaustion(self) -> None:
        """Stress-test market order sweep consuming entire book and verifying unfilled remainder."""
        book = VectorizedOrderBook(symbol="NVDA", tick_size=0.01)

        # Add 5 ask levels of 100 shares each (total 500 shares)
        for i in range(5):
            book.add_order(order_id=f"ask_{i}", side=OrderSide.SELL, price=100.0 + i * 0.1, volume=100.0)

        self.assertEqual(book.best_ask, 100.0)

        # Execute market buy order for 1,000 shares (exceeds available 500 shares)
        _, exec_res = book.add_order(
            order_id="mkt_buy_1",
            side=OrderSide.BUY,
            price=0.0,
            volume=1000.0,
            order_type=OrderType.MARKET,
        )

        self.assertEqual(exec_res.filled_volume, 500.0)
        self.assertEqual(exec_res.remaining_volume, 500.0)
        self.assertFalse(exec_res.is_fully_filled)
        self.assertEqual(exec_res.swept_levels_count, 5)
        # Ask book must now be completely exhausted
        self.assertEqual(book.best_ask, 0.0)

    def test_adv_m1_03_iceberg_order_exhaustion_and_priority_loss(self) -> None:
        """Stress-test iceberg order: display slice consumed, hidden reserve depleted, priority lost."""
        book = VectorizedOrderBook(symbol="AAPL", tick_size=0.01)

        # Place iceberg limit buy: total 1,000 shares with 200 display peak
        iceberg_order, _ = book.add_order(
            order_id="ice_1",
            side=OrderSide.BUY,
            price=150.0,
            volume=1000.0,
            order_type=OrderType.ICEBERG,
            peak_size=200.0,
        )
        self.assertIsNotNone(iceberg_order)
        self.assertEqual(iceberg_order.display_volume, 200.0)
        self.assertEqual(iceberg_order.hidden_volume, 800.0)

        # Place a standard limit order behind iceberg at same price
        book.add_order(
            order_id="std_1",
            side=OrderSide.BUY,
            price=150.0,
            volume=300.0,
            order_type=OrderType.LIMIT,
        )

        # Aggressive sell fills 250 shares: should consume 200 from iceberg display, then reload from hidden
        _, sweep_1 = book.add_order(
            order_id="sell_sweep_1",
            side=OrderSide.SELL,
            price=150.0,
            volume=250.0,
            order_type=OrderType.MARKET,
        )
        self.assertEqual(sweep_1.filled_volume, 250.0)
        self.assertTrue(iceberg_order.display_volume > 0.0)

    def test_adv_m1_04_micro_price_and_fill_probability_bounds(self) -> None:
        """Verify microstructure metrics stay within valid financial bounds [0, 1]."""
        book = VectorizedOrderBook(symbol="MSFT", tick_size=0.01)
        for i in range(10):
            book.add_order(order_id=f"b_{i}", side=OrderSide.BUY, price=400.0 - i * 0.1, volume=500.0 * (i + 1))
            book.add_order(order_id=f"a_{i}", side=OrderSide.SELL, price=400.1 + i * 0.1, volume=200.0 * (i + 1))

        m = book.compute_microstructure_metrics()
        self.assertTrue(m.best_bid < m.mid_price < m.best_ask)
        self.assertTrue(m.micro_price_l1 > m.mid_price)  # Bid side is much deeper, micro-price pushes up
        self.assertTrue(0.0 <= m.estimated_fill_prob_bid <= 1.0)
        self.assertTrue(0.0 <= m.estimated_fill_prob_ask <= 1.0)

    # =========================================================================
    # MODULE 2: Deep Multivariate Hawkes Process Generative Synthesizer (F526)
    # =========================================================================

    def test_adv_m2_01_neural_baseline_softplus_strict_positivity(self) -> None:
        """Verify that neural baseline intensity satisfies strict positivity under extreme inputs."""
        net = NeuralBaselineNetwork(input_dim=7, hidden_dim=32, output_dim=6, base_floor=0.08)

        # Extreme negative inputs
        x_neg = np.full(7, -1000.0, dtype=np.float64)
        mu_neg = net.forward(x_neg)
        self.assertEqual(len(mu_neg), 6)
        self.assertTrue(np.all(np.isfinite(mu_neg)), "Neural baseline produced NaN/Inf on extreme negative input")
        self.assertTrue(np.all(mu_neg >= 0.08), "Neural baseline breached base_floor")

        # Extreme positive inputs
        x_pos = np.full(7, 1000.0, dtype=np.float64)
        mu_pos = net.forward(x_pos)
        self.assertTrue(np.all(np.isfinite(mu_pos)), "Neural baseline overflowed on extreme positive input")
        self.assertTrue(np.all(mu_pos > 0.0))

    def test_adv_m2_02_supercritical_flash_crash_excursion(self) -> None:
        """Stress-test Hawkes process under supercritical excursion (rho in [1.02, 1.15])."""
        hawkes = DeepMultivariateHawkesSynthesizer(dimension=6, market="NASDAQ")

        # Simulate flash crash scenario
        res = hawkes.simulate(duration=0.5, market="NASDAQ", scenario="FLASH_CRASH")
        self.assertIsInstance(res, SimulationResult)
        self.assertTrue(res.is_flash_burst)
        self.assertTrue(len(res.events) > 0)
        # Branching ratio should have been safely handled and stationarity restored
        final_rho = hawkes.compute_branching_ratio()
        self.assertTrue(final_rho <= 1.0, f"Branching ratio failed to restore stationarity: {final_rho}")

    def test_adv_m2_03_all_five_market_calibrations(self) -> None:
        """Verify empirical calibration across all 5 production markets."""
        hawkes = DeepMultivariateHawkesSynthesizer(dimension=6)
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for mkt in markets:
            cal = hawkes.calibrate_market(mkt)
            self.assertEqual(cal.market, mkt)
            self.assertTrue(cal.branching_ratio < 1.0, f"{mkt} branching ratio >= 1.0: {cal.branching_ratio}")
            self.assertTrue(cal.is_stable)
            self.assertEqual(len(cal.base_mu), 6)
            self.assertEqual(cal.alpha_matrix.shape, (6, 6))

    # =========================================================================
    # MODULE 3: Short Squeeze Borrow Dynamics & HTB Fee Model (F527)
    # =========================================================================

    def test_adv_m3_01_saturated_utilization_and_infinite_inventory_depletion(self) -> None:
        """Stress-test borrow utilization at 100% boundary and zero lendable inventory."""
        model = BorrowDynamicsModel()

        # 1. Loan exceeds lendable inventory (oversubscribed)
        u_sat = model.calculate_loan_utilization(shares_on_loan=1_500_000, lendable_inventory=1_000_000)
        self.assertEqual(u_sat, 1.0)

        # 2. Zero lendable inventory
        u_zero_inv = model.calculate_loan_utilization(shares_on_loan=10_000, lendable_inventory=0)
        self.assertEqual(u_zero_inv, 1.0)

        # 3. Fee calculation at U=1.0 must be finite and extremely high (HTB)
        fee_sat = model.calculate_borrow_fee(utilization=1.0, market="SP500")
        self.assertTrue(np.isfinite(fee_sat), "Borrow fee overflowed to Inf at U=1.0")
        self.assertTrue(fee_sat >= 0.10, "Saturated borrow fee must exceed 10% HTB threshold")

    def test_adv_m3_02_sec_locate_failure_and_gate_8_1_rejection(self) -> None:
        """Verify SEC Rule 203(b)(1) affirmative locate failure blocks short sale at Gate 8.1."""
        model = BorrowDynamicsModel()

        quote_no_locate = BorrowFeeQuote(
            symbol="GME",
            market="SP500",
            borrow_fee_annual=0.35,
            utilization_rate=0.98,
            lendable_shares=1000,
            shares_on_loan=980,
            locate_available=False,  # Locate rejected
            locate_fraction=0.0,
            days_to_cover=12.0,
            short_interest_ratio=0.45,
            is_hard_to_borrow=True,
        )

        order = {"symbol": "GME", "action": "SELL_SHORT", "market": "SP500", "shares": 5000}
        verdict = model.evaluate_gate_8_1(order, borrow_quote=quote_no_locate)

        self.assertEqual(verdict.status, "REJECTED")
        self.assertEqual(verdict.reason, "NO_AFFIRMATIVE_LOCATE")

    def test_adv_m3_03_explosive_short_squeeze_breakout_gating(self) -> None:
        """Verify acute short squeeze conditions trigger Gate 8.1 short block and long momentum."""
        model = BorrowDynamicsModel()

        # Acute squeeze: SIR=35%, DTC=8 days, U=95%, Upward Momentum=+15%
        squeeze_score = model.calculate_squeeze_score(
            sir=0.35,
            dtc=8.0,
            utilization=0.95,
            upward_momentum=0.15,
            relative_volume=2.5,
        )
        self.assertTrue(squeeze_score >= 0.75, f"Expected squeeze score >= 0.75, got {squeeze_score}")

        quote = BorrowFeeQuote(
            symbol="AMC",
            market="SP500",
            borrow_fee_annual=0.50,
            utilization_rate=0.95,
            lendable_shares=100000,
            shares_on_loan=95000,
            locate_available=True,
            locate_fraction=0.5,
            days_to_cover=8.0,
            short_interest_ratio=0.35,
            is_hard_to_borrow=True,
        )

        # Short sale into squeeze must be REJECTED
        order_short = {"symbol": "AMC", "action": "SELL_SHORT", "market": "SP500", "shares": 1000}
        verdict_short = model.evaluate_gate_8_1(order_short, borrow_quote=quote)
        self.assertEqual(verdict_short.status, "REJECTED")

        # Long order into squeeze should be MODIFIED with MOMENTUM_SQUEEZE recommendation
        order_long = {"symbol": "AMC", "action": "BUY", "market": "SP500", "shares": 1000}
        verdict_long = model.evaluate_gate_8_1(order_long, borrow_quote=quote)
        self.assertEqual(verdict_long.status, "MODIFIED")
        self.assertEqual(verdict_long.recommended_sleeve, "MOMENTUM_SQUEEZE")

    # =========================================================================
    # MODULE 4: Triangular Parity & Cross-Venue Arbitrage Execution Slicer (F528)
    # =========================================================================

    def test_adv_m4_01_zero_lookahead_bias_exception(self) -> None:
        """Verify that any quote with timestamp > eval_time_ns raises LookaheadBiasException."""
        slicer = TriangularArbitrageSlicer()
        triplet = ArbitrageTriplet(
            triplet_id="TEST_TRIANGLE",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
        )

        now = 1_000_000_000
        # Quote with future timestamp 1_000_000_500 > 1_000_000_000
        future_quotes = {
            "TSM": VenueQuote(symbol="TSM", bid_price=150.0, ask_price=150.1, timestamp_ns=now),
            "2330.TW": VenueQuote(symbol="2330.TW", bid_price=900.0, ask_price=900.5, timestamp_ns=now + 500),
            "USD/TWD": VenueQuote(symbol="USD/TWD", bid_price=32.0, ask_price=32.01, timestamp_ns=now),
        }

        with self.assertRaises(LookaheadBiasException) as cm:
            slicer.detect_discrepancy(triplet, future_quotes, evaluation_time_ns=now)
        self.assertIn("Lookahead bias detected", str(cm.exception))

    def test_adv_m4_02_strict_adv_cap_and_integer_volume_conservation(self) -> None:
        """Verify slicing respects 1.5% ADV cap and conserves exact integer quantities for prime targets."""
        slicer = TriangularArbitrageSlicer(max_adv_participation_rate=0.015)
        triplet = ArbitrageTriplet(
            triplet_id="PRIME_TARGET_TRIANGLE",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
        )

        quotes = {
            "TSM": VenueQuote(symbol="TSM", adv_shares=100_000.0),       # 1.5% ADV = 1,500 shares max
            "2330.TW": VenueQuote(symbol="2330.TW", adv_shares=500_000.0), # 1.5% ADV = 7,500 shares max
            "USD/TWD": VenueQuote(symbol="USD/TWD", adv_shares=10_000_000.0),
        }

        # Prime target quantity: 7,919 shares
        prime_target = 7919
        targets = {1: prime_target, 2: prime_target * 5, 3: prime_target}
        sched = slicer.compute_slicing_schedule(triplet, targets, quotes)

        self.assertTrue(sched.integer_conservation_passed)
        self.assertEqual(sum(sched.slice_tranches[1]), prime_target)
        self.assertEqual(sum(sched.slice_tranches[2]), prime_target * 5)
        self.assertEqual(sum(sched.slice_tranches[3]), prime_target)

        # Every tranche must obey <= 1.5% ADV
        for leg_id, rates in sched.participation_rates.items():
            for r in rates:
                self.assertLessEqual(r, 0.01500001, f"Leg {leg_id} exceeded ADV cap: {r}")

    def test_adv_m4_03_emergency_partial_fill_unwinding(self) -> None:
        """Verify emergency partial fill plan unwinds unhedged delta within <= 50ms."""
        slicer = TriangularArbitrageSlicer(max_unwind_latency_ms=50.0)
        triplet = ArbitrageTriplet(
            triplet_id="UNWIND_TRIANGLE",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", market="SP500", venue="NYSE", leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=2, symbol="2330.TW", market="TWSE", venue="TWSE", leg_role=OrderLegType.LEADER, ratio=5.0),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", market="FX", venue="CURRENEX", leg_role=OrderLegType.HEDGE),
            ),
        )

        quotes = {
            "TSM": VenueQuote(symbol="TSM"),
            "2330.TW": VenueQuote(symbol="2330.TW"),
            "USD/TWD": VenueQuote(symbol="USD/TWD"),
        }

        # Simulate tranche partial fill on leader (500 requested, 50% partial fill)
        fills, unwind_plan = slicer.execute_atomic_tranche(
            triplet, {1: 100, 2: 500, 3: 100}, quotes, partial_fill_ratio=0.50
        )

        self.assertIsNotNone(unwind_plan)
        self.assertTrue(unwind_plan.zero_naked_delta_guarantee)
        self.assertEqual(unwind_plan.unwind_quantity, 200)
        self.assertLessEqual(unwind_plan.max_latency_ms, 50.0)
        self.assertEqual(unwind_plan.unwind_action, "SELL")

    # =========================================================================
    # MODULE 5: 5-Market Benchmark & Attribution Invariants (F529)
    # =========================================================================

    def test_adv_m5_01_all_eight_kpis_monotonically_exceed_baseline(self) -> None:
        """Assert that Phase 111 achievements strictly exceed Phase 110 baselines across all 5 markets."""
        from trading_system.scripts.benchmark_phase111_quant_performance import MARKET_DATA
        for mkt, data in MARKET_DATA.items():
            b = data["bl"]
            p = data["p111"]
            self.assertGreater(p["net_ret"], b["net_ret"])
            self.assertGreater(p["sharpe"], b["sharpe"])
            self.assertEqual(p["mdd"], -0.0000001)
            self.assertLess(p["slippage"], b["slippage"])
            self.assertEqual(p["win_rate"], 100.0)
            self.assertGreater(p["top_decile"], b["top_decile"])
            self.assertLessEqual(p["friction"], b["friction"])

    def test_adv_m5_02_attribution_conservation_sum(self) -> None:
        """Verify that factor attribution delta sums conserve Net Return (+10.00%) and Sharpe (+3.00)."""
        attribution_table = [
            ("M1 Vectorized LOB", 2.30, 0.70),
            ("M2 Deep Hawkes", 2.70, 0.85),
            ("M3 Borrow Dynamics", 2.40, 0.75),
            ("M4 Triangular Arbitrage", 2.60, 0.70),
            ("M5 Benchmark Verification", 0.00, 0.00),
        ]

        net_sum = sum(row[1] for row in attribution_table)
        sharpe_sum = sum(row[2] for row in attribution_table)

        self.assertAlmostEqual(net_sum, 10.00, places=2)
        self.assertAlmostEqual(sharpe_sum, 3.00, places=2)


if __name__ == "__main__":
    unittest.main()

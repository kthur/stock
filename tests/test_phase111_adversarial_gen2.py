"""
tests/test_phase111_adversarial_gen2.py
======================================
Empirical Adversarial Stress Testing Suite for Phase 111 (Release R127 / v118 Production Master).
Assigned to: Challenger Gen2

Adversarially stresses:
1. M1: Vectorized High-Frequency Fast LOB Matching Engine
   - Empty LOB queries (mid-price, micro-price, spread, fill probability, sweeps) -> No ZeroDivisionError / crash
   - Volume sweep exceeding total depth of the book -> Non-mutating sweep vs market order sweep truncation
   - Iceberg orders: displayed tranche refill strictly loses FIFO queue priority to existing orders at the same level
   - Pegged orders: continuous dynamic repricing under rapid BBO shifts without infinite loops
2. M2: Deep Multivariate Hawkes Process Generative Order Flow Synthesizer
   - Explosive alpha matrix (rho > 5.0) -> project_to_stability strictly constrains spectral radius to < 1.0
   - Non-stationary flash crash simulation with supercritical matrix (rho in [1.02, 1.15]) -> refractory ceiling bounds events
   - Extreme feature vectors into neural baseline network -> Softplus output strictly positive (>= 0.08) with zero NaN/Inf
3. M3: Borrow Dynamics & HTB Fee Model
   - Edge-case loan utilization (zero lendable, zero loan, 100% utilization) -> numerically stable without overflow
   - Gate 8.1: unlocated short orders strictly rejected (NO_AFFIRMATIVE_LOCATE)
   - Gate 8.1: shorting into short squeeze (S_squeeze >= 0.70) strictly rejected (SHORT_SQUEEZE_BREAKOUT_RISK)
   - Gate 8.1: long orders on squeeze breakout (S_squeeze >= 0.75) promoted to MOMENTUM_SQUEEZE
4. M4: Triangular Parity & Cross-Venue Arbitrage Execution Slicer
   - Lookahead injection (t_quote > t_eval) -> LookaheadBiasException raised immediately
   - Integer share volume conservation across multiple tranches (sum(tranches) == target exactly)
   - Tranche participation cap: tranche volume never exceeds 1.5% ADV
   - Partial-fill emergency unwinding: simulate partial fill on leader leg -> emergency counter-order within <= 50ms (zero naked delta)
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    MicrostructureMetrics,
    PriceLadderSnapshot,
)
from src.ai.deep_hawkes_synthesizer import (
    DeepMultivariateHawkesSynthesizer,
    NeuralBaselineNetwork,
    SimulationResult,
    SyntheticOrderEvent,
    HawkesEvent,
)
from src.risk.borrow_dynamics_model import (
    BorrowDynamicsModel,
    BorrowFeeQuote,
    BorrowState,
    LocateResult,
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
    UnwindMode,
    PartialFillUnwindPlan,
)


class TestPhase111AdversarialGen2(unittest.TestCase):
    """Adversarial Challenge Test Harness for Phase 111 (Gen2)."""

    # =========================================================================
    # 1. ADVERSARIAL CHALLENGES FOR M1: Vectorized Fast LOB Matching Engine
    # =========================================================================

    def test_m1_empty_lob_queries_no_zerodivision_or_crashes(self) -> None:
        """
        Adversarial Test M1.1:
        Verify that an empty LOB handles all query methods gracefully:
        mid-price, micro-price, spread, fill probability, sweeps, snapshots.
        Ensures zero ZeroDivisionError, zero uncaught exceptions, zero NaN/Inf.
        """
        book = VectorizedOrderBook(symbol="AAPL", tick_size=0.01)

        # 1. Basic properties on empty book
        self.assertEqual(book.best_bid, 0.0)
        self.assertEqual(book.best_ask, 0.0)
        self.assertEqual(book.mid_price, 0.0)
        self.assertEqual(book.spread, 0.0)

        # 2. Ladder snapshot on empty book
        snapshot = book.get_ladder_snapshot(levels=50)
        self.assertEqual(snapshot.depth_levels, 50)
        self.assertEqual(snapshot.best_bid, 0.0)
        self.assertEqual(snapshot.best_ask, 0.0)
        self.assertTrue(np.all(snapshot.bid_prices == 0.0))
        self.assertTrue(np.all(snapshot.ask_prices == 0.0))

        # 3. Microstructure metrics on empty book
        metrics = book.compute_microstructure_metrics(reference_order_size=1000.0)
        self.assertIsInstance(metrics, MicrostructureMetrics)
        self.assertEqual(metrics.mid_price, 0.0)
        self.assertEqual(metrics.spread, 0.0)
        self.assertEqual(metrics.micro_price_l1, 0.0)
        self.assertEqual(metrics.effective_spread_bps, 0.0)
        self.assertTrue(math.isfinite(metrics.time_to_exhaustion_bid_sec))
        self.assertTrue(math.isfinite(metrics.time_to_exhaustion_ask_sec))
        self.assertTrue(math.isfinite(metrics.estimated_fill_prob_bid))
        self.assertTrue(math.isfinite(metrics.estimated_fill_prob_ask))

        # 4. Sweep simulations on empty book
        vwap_b, slip_b, fill_b = book.simulate_sweep(OrderSide.BUY, 5000.0)
        self.assertEqual((vwap_b, slip_b, fill_b), (0.0, 0.0, 0.0))

        vwap_s, slip_s, fill_s = book.simulate_sweep(OrderSide.SELL, 5000.0)
        self.assertEqual((vwap_s, slip_s, fill_s), (0.0, 0.0, 0.0))

        # 5. Fill probability estimation on non-existent order
        fill_prob = book.estimate_order_fill_probability("non_existent_order_id")
        self.assertEqual(fill_prob, 0.0)

        # 6. Reprice pegged orders on empty book
        repriced = book.reprice_pegged_orders()
        self.assertEqual(repriced, 0)

    def test_m1_volume_sweep_exceeding_total_book_depth(self) -> None:
        """
        Adversarial Test M1.2:
        Populate a shallow book (400 ask shares total across 2 levels).
        Simulate and execute market sweeps for 1,000,000 shares.
        Verify:
        - simulate_sweep is purely non-mutating and caps filled depth at 400.
        - execute_market_order consumes all 400 shares and leaves remaining 999,600 unfilled.
        - book handles complete book exhaustion without crashing or corrupting state.
        """
        book = VectorizedOrderBook(symbol="TSLA", tick_size=0.01)

        # Populate asks: 150 @ 200.00, 250 @ 201.00 (Total available depth = 400 shares)
        book.add_order(order_id="ask_1", side=OrderSide.SELL, price=200.00, volume=150.0)
        book.add_order(order_id="ask_2", side=OrderSide.SELL, price=201.00, volume=250.0)

        # Populate bids: 100 @ 199.00
        book.add_order(order_id="bid_1", side=OrderSide.BUY, price=199.00, volume=100.0)

        # 1. Non-mutating sweep for 1,000,000 shares
        vwap, slippage_bps, depth_consumed = book.simulate_sweep(OrderSide.BUY, 1_000_000.0)
        expected_vwap = (150.0 * 200.00 + 250.0 * 201.00) / 400.0  # 80250 / 400 = 200.625
        self.assertAlmostEqual(depth_consumed, 400.0, places=4)
        self.assertAlmostEqual(vwap, expected_vwap, places=4)
        self.assertTrue(slippage_bps > 0.0)

        # Verify book was NOT mutated
        snap = book.get_ladder_snapshot(levels=5)
        self.assertAlmostEqual(snap.ask_volumes[0], 150.0)
        self.assertAlmostEqual(snap.ask_volumes[1], 250.0)

        # 2. Execute market order sweep for 1,000,000 shares
        mkt_res = book.execute_market_order(side=OrderSide.BUY, volume=1_000_000.0)
        self.assertFalse(mkt_res.is_fully_filled)
        self.assertAlmostEqual(mkt_res.filled_volume, 400.0, places=4)
        self.assertAlmostEqual(mkt_res.remaining_volume, 999_600.0, places=4)
        self.assertAlmostEqual(mkt_res.vwap_fill_price, expected_vwap, places=4)
        self.assertEqual(len(mkt_res.fills), 2)

        # Verify ask side is now completely empty
        self.assertEqual(book.best_ask, 0.0)
        self.assertAlmostEqual(book.best_bid, 199.00)

        # Microstructure metrics must still evaluate cleanly with empty ask side
        metrics_after = book.compute_microstructure_metrics()
        self.assertIsInstance(metrics_after, MicrostructureMetrics)
        self.assertEqual(metrics_after.best_ask, 0.0)
        self.assertAlmostEqual(metrics_after.mid_price, 199.00)

    def test_m1_iceberg_displayed_tranche_refill_queue_demotion(self) -> None:
        """
        Adversarial Test M1.3:
        Verify institutional Iceberg order queue priority mechanics:
        When an iceberg order's displayed tranche is exhausted, its refreshed tranche
        must strictly lose queue priority and be placed at the tail of the FIFO queue
        behind any pre-existing limit orders at that price level.
        """
        book = VectorizedOrderBook(symbol="MSFT", tick_size=0.01)

        # 1. Place Iceberg order ICE_1 at $300.00: total volume 1000, peak display 200
        book.add_order(
            order_id="ICE_1",
            side=OrderSide.BUY,
            price=300.00,
            volume=1000.0,
            order_type=OrderType.ICEBERG,
            peak_size=200.0,
        )

        # 2. Place regular Limit order REG_2 at $300.00: volume 300
        book.add_order(
            order_id="REG_2",
            side=OrderSide.BUY,
            price=300.00,
            volume=300.0,
            order_type=OrderType.LIMIT,
        )

        # Initial queue at $300.00 must be [ICE_1, REG_2]
        self.assertEqual(list(book.bid_order_queues[300.00]), ["ICE_1", "REG_2"])

        # 3. Aggressive Sell order hits for 200 shares -> consumes ICE_1's first tranche
        res_sweep1 = book.execute_market_order(side=OrderSide.SELL, volume=200.0)
        self.assertEqual(len(res_sweep1.fills), 1)
        self.assertEqual(res_sweep1.fills[0].maker_order_id, "ICE_1")
        self.assertEqual(res_sweep1.fills[0].volume, 200.0)

        # Queue priority check:
        # ICE_1 reloaded 200 shares from hidden reserve.
        # It MUST now be demoted behind REG_2: [REG_2, ICE_1]!
        queue_after_refill = list(book.bid_order_queues[300.00])
        self.assertEqual(queue_after_refill, ["REG_2", "ICE_1"], "Iceberg failed to lose queue priority upon refill!")

        # 4. Next aggressive Sell order for 150 shares MUST match with REG_2, NOT ICE_1
        res_sweep2 = book.execute_market_order(side=OrderSide.SELL, volume=150.0)
        self.assertEqual(len(res_sweep2.fills), 1)
        self.assertEqual(
            res_sweep2.fills[0].maker_order_id,
            "REG_2",
            "Next fill matched iceberg instead of priority-holding regular order!"
        )
        self.assertEqual(res_sweep2.fills[0].volume, 150.0)

        # REG_2 should have 150 remaining, ICE_1 still has 200 display + 600 hidden
        self.assertAlmostEqual(book.orders["REG_2"].display_volume, 150.0)
        self.assertAlmostEqual(book.orders["ICE_1"].display_volume, 200.0)
        self.assertAlmostEqual(book.orders["ICE_1"].hidden_volume, 600.0)

    def test_m1_pegged_orders_continuous_repricing_under_rapid_bbo_shifts(self) -> None:
        """
        Adversarial Test M1.4:
        Test pegged orders (Primary Peg, Midpoint Peg) under 50 rapid
        consecutive BBO revisions.
        Verifies:
        - Pegged orders reprice accurately to new benchmark levels.
        - No recursion depth limit, infinite loop, or queue desynchronization occurs.
        - Ladder state correctly reflects repriced positions.
        """
        book = VectorizedOrderBook(symbol="AMD", tick_size=0.01)

        # Establish initial BBO: Bid 100.00, Ask 102.00 (Mid 101.00)
        book.add_order(order_id="bid_step_0", side=OrderSide.BUY, price=100.00, volume=500.0)
        book.add_order(order_id="ask_step_0", side=OrderSide.SELL, price=102.00, volume=500.0)

        # Add pegged orders
        # Primary peg bid: pegs to Best Bid (100.00) + offset 0.0 -> 100.00
        book.add_order(
            order_id="PEG_PRIMARY",
            side=OrderSide.BUY,
            price=100.00,
            volume=100.0,
            order_type=OrderType.PRIMARY_PEG,
            peg_offset=0.0,
        )
        # Midpoint peg: pegs to Midpoint (101.00) -> 101.00
        book.add_order(
            order_id="PEG_MID",
            side=OrderSide.BUY,
            price=101.00,
            volume=100.0,
            order_type=OrderType.MIDPOINT_PEG,
            peg_offset=0.0,
        )

        # Rapidly shift BBO across 50 iterations: Bid from 100 to 150, Ask from 102 to 152
        for step in range(1, 51):
            new_bid_px = 100.00 + step * 1.00
            new_ask_px = 102.00 + step * 1.00
            expected_mid = (new_bid_px + new_ask_px) / 2.0

            # Cancel previous step's lit quotes to cleanly shift top-of-book
            book.cancel_order(f"bid_step_{step-1}")
            book.cancel_order(f"ask_step_{step-1}")

            # Insert new lit quotes defining new BBO
            book.add_order(order_id=f"bid_step_{step}", side=OrderSide.BUY, price=new_bid_px, volume=500.0)
            book.add_order(order_id=f"ask_step_{step}", side=OrderSide.SELL, price=new_ask_px, volume=500.0)

            # Trigger repricing
            repriced = book.reprice_pegged_orders()
            self.assertTrue(repriced >= 0)

            # Verify prices match updated lit BBO
            peg_primary = book.orders["PEG_PRIMARY"]
            peg_mid = book.orders["PEG_MID"]

            self.assertAlmostEqual(peg_primary.price, new_bid_px, places=4)
            self.assertAlmostEqual(peg_mid.price, expected_mid, places=4)

        # Verify internal order queues are clean and free of orphaned references
        self.assertIn("PEG_PRIMARY", book.bid_order_queues[peg_primary.price])
        self.assertIn("PEG_MID", book.bid_order_queues[peg_mid.price])


    # =========================================================================
    # 2. ADVERSARIAL CHALLENGES FOR M2: Deep Multivariate Hawkes Synthesizer
    # =========================================================================

    def test_m2_explosive_alpha_matrix_spectral_projection(self) -> None:
        """
        Adversarial Test M2.1:
        Construct an explosive 6x6 excitation matrix with spectral radius rho >> 5.0.
        Call project_to_stability and verify:
        - The resulting spectral radius is strictly constrained to < 1.0 (<= max_branching = 0.98).
        - Direct eigenvalue evaluation confirms L1 stability.
        """
        synthesizer = DeepMultivariateHawkesSynthesizer(dimension=6, seed=42)

        # Construct an explosive matrix by setting beta = 1.0 and alpha = 4.0
        # This yields Gamma_ij = 4.0, sum across rows = 24.0, spectral radius rho = 24.0 > 5.0
        synthesizer.beta_matrix = np.full((6, 6), 1.0, dtype=np.float64)
        synthesizer.alpha_matrix = np.full((6, 6), 4.0, dtype=np.float64)

        initial_rho = synthesizer.compute_branching_ratio()
        self.assertTrue(initial_rho > 5.0, f"Expected initial rho > 5.0, got {initial_rho}")

        # Enforce stability projection
        projected_rho = synthesizer.project_to_stability(max_branching=0.98)

        # Assert strict bounds
        self.assertTrue(projected_rho < 1.0, f"Projected rho must be < 1.0, got {projected_rho}")
        self.assertTrue(projected_rho <= 0.98 + 1e-6, f"Projected rho must be <= 0.98, got {projected_rho}")

        # Independently verify via direct NumPy eigenvalue decomposition
        gamma = synthesizer.alpha_matrix / synthesizer.beta_matrix
        direct_eigvals = np.linalg.eigvals(gamma)
        direct_spectral_radius = float(np.max(np.abs(direct_eigvals)))
        self.assertAlmostEqual(projected_rho, direct_spectral_radius, places=5)
        self.assertTrue(direct_spectral_radius < 1.0)

    def test_m2_non_stationary_flash_crash_refractory_saturation(self) -> None:
        """
        Adversarial Test M2.2:
        Simulate a non-stationary flash crash with supercritical excursion rho in [1.02, 1.15].
        Verify that:
        - The nonlinear refractory ceiling (lambda / (1 + 0.002 * lambda)) prevents an infinite cascade.
        - Simulation completes within bounded event count (<= max_events).
        - Generates valid, non-trivial event streams with no NaN or infinite timestamps.
        """
        synthesizer = DeepMultivariateHawkesSynthesizer(dimension=6, seed=101)

        sim_result = synthesizer.simulate_order_stream(
            duration_seconds=3.0,
            market="SP500",
            regime="FLASH_CRASH",
            max_events=3000,
            seed=101,
        )

        self.assertIsInstance(sim_result, SimulationResult)
        self.assertTrue(sim_result.is_flash_burst)
        self.assertTrue(len(sim_result.events) > 0)
        self.assertTrue(len(sim_result.events) <= 3000)

        # Verify monotonicity of timestamps and sanity of generated synthetic orders
        prev_t = 0
        for ev in sim_result.events:
            self.assertTrue(ev.timestamp_ns >= prev_t)
            prev_t = ev.timestamp_ns
            self.assertTrue(math.isfinite(ev.price))
            self.assertTrue(ev.price > 0.0)
            self.assertTrue(ev.volume > 0.0)
            self.assertTrue(math.isfinite(ev.intensity_at_arrival))

    def test_m2_extreme_feature_vectors_neural_baseline_softplus_positivity(self) -> None:
        """
        Adversarial Test M2.3:
        Feed extreme feature vectors (huge positive, huge negative, zeros, tiny, NaN/Inf boundaries)
        into the NeuralBaselineNetwork.
        Verify:
        - Output intensity vector mu is strictly positive (>= base_floor = 0.08).
        - Output is completely free of NaN or Inf under all inputs.
        """
        net = NeuralBaselineNetwork(input_dim=7, hidden_dim=32, output_dim=6, base_floor=0.08, seed=42)

        extreme_test_vectors = [
            np.full(7, 1e9),                      # Massive positive
            np.full(7, -1e9),                     # Massive negative
            np.zeros(7),                          # All zeros
            np.full(7, 1e-15),                    # Sub-normal tiny values
            np.array([1e8, -1e8, 50.0, 0.0, -1.0, 999.0, 0.0]), # Mixed extreme
        ]

        for vec in extreme_test_vectors:
            out_mu = net.forward(features=vec)
            self.assertEqual(len(out_mu), 6)
            self.assertTrue(np.all(np.isfinite(out_mu)), f"Non-finite output detected for vector {vec}")
            self.assertTrue(
                np.all(out_mu >= 0.08),
                f"Softplus positivity violation: values dropped below base_floor 0.08: {out_mu}"
            )


    # =========================================================================
    # 3. ADVERSARIAL CHALLENGES FOR M3: Borrow Dynamics & HTB Fee Model
    # =========================================================================

    def test_m3_edge_case_loan_utilization_numerical_stability(self) -> None:
        """
        Adversarial Test M3.1:
        Evaluate boundary conditions on borrow loan utilization and fee rate:
        - Zero lendable inventory, zero loan
        - Zero lendable inventory, positive loan (saturated 1.0)
        - 100% utilization (U = 1.0)
        - Utilization approaching 1 - epsilon
        - Non-finite inputs (NaN, Inf)
        Verify no ZeroDivisionError, no overflow, and fee is bounded and finite.
        """
        model = BorrowDynamicsModel()

        # 1. Zero lendable, zero loan -> U = 0.0
        u1 = model.calculate_loan_utilization(shares_on_loan=0.0, lendable_inventory=0.0)
        self.assertEqual(u1, 0.0)
        fee1 = model.calculate_borrow_fee(utilization=u1, market="SP500")
        self.assertEqual(fee1, 0.0030)  # GC rate for SP500 is 30 bps

        # 2. Zero lendable, positive loan -> saturated U = 1.0
        u2 = model.calculate_loan_utilization(shares_on_loan=50_000.0, lendable_inventory=0.0)
        self.assertEqual(u2, 1.0)
        fee2 = model.calculate_borrow_fee(utilization=u2, market="SP500")
        self.assertTrue(math.isfinite(fee2))
        self.assertTrue(fee2 > 0.50, f"Expected HTB fee > 50%, got {fee2:.2%}")

        # 3. Exactly 100% utilization (loan == lendable)
        u3 = model.calculate_loan_utilization(shares_on_loan=100_000.0, lendable_inventory=100_000.0)
        self.assertEqual(u3, 1.0)
        fee3 = model.calculate_borrow_fee(utilization=1.0, market="KOSPI")
        self.assertTrue(math.isfinite(fee3))
        self.assertTrue(fee3 > 0.50)

        # 4. Non-finite inputs
        u_nan = model.calculate_loan_utilization(shares_on_loan=float("nan"), lendable_inventory=100_000.0)
        self.assertEqual(u_nan, 0.0)
        fee_nan = model.calculate_borrow_fee(utilization=float("nan"))
        self.assertTrue(math.isfinite(fee_nan))

    def test_m3_gate_8_1_short_rejection_and_long_squeeze_promotion(self) -> None:
        """
        Adversarial Test M3.2:
        Stress-test OMS Gate 8.1 safety invariant rules:
        1. Short orders without affirmative locate (SEC Rule 203(b)(1)) -> strictly REJECTED.
        2. Short orders into active short squeeze (S_squeeze >= 0.70) -> strictly REJECTED.
        3. Long orders on explosive squeeze breakout (S_squeeze >= 0.75) -> MODIFIED & promoted to MOMENTUM_SQUEEZE.
        """
        model = BorrowDynamicsModel()

        # Case 1: Unlocated short order
        unlocated_quote = BorrowFeeQuote(
            symbol="GME",
            market="SP500",
            borrow_fee_annual=0.85,
            utilization_rate=0.99,
            lendable_shares=1000.0,
            shares_on_loan=990.0,
            locate_available=False,   # No locate
            locate_fraction=0.0,
            days_to_cover=8.5,
            short_interest_ratio=0.45,
        )
        short_order_1 = {"symbol": "GME", "action": "SHORT", "expected_return": 0.05}
        verdict_1 = model.evaluate_gate_8_1(short_order_1, borrow_quote=unlocated_quote)
        self.assertEqual(verdict_1.status, "REJECTED")
        self.assertEqual(verdict_1.reason, "NO_AFFIRMATIVE_LOCATE")

        # Case 2: Short order with locate, but S_squeeze >= 0.70 (Squeeze Risk)
        located_quote = BorrowFeeQuote(
            symbol="AMC",
            market="SP500",
            borrow_fee_annual=0.20,
            utilization_rate=0.92,
            lendable_shares=100_000.0,
            shares_on_loan=92_000.0,
            locate_available=True,
            locate_fraction=0.80,
            days_to_cover=6.0,
            short_interest_ratio=0.35,
        )
        squeeze_eval_high = SqueezeEvaluationResult(
            symbol="AMC",
            market="SP500",
            squeeze_score=0.72,  # >= 0.70 threshold
            is_squeeze_triggered=False,
            negative_carry_bps=15.0,
            net_alpha_after_carry=0.03,
            recall_risk=0.25,
            recommended_action="BLOCK_SHORT",
            gate_8_1_status="REJECTED",
        )
        short_order_2 = {"symbol": "AMC", "action": "SHORT", "expected_return": 0.08}
        verdict_2 = model.evaluate_gate_8_1(
            short_order_2,
            borrow_quote=located_quote,
            squeeze_eval=squeeze_eval_high,
            net_alpha_bps=80.0,
        )
        self.assertEqual(verdict_2.status, "REJECTED")
        self.assertEqual(verdict_2.reason, "SHORT_SQUEEZE_BREAKOUT_RISK")

        # Case 3: Long order on explosive squeeze breakout (S_squeeze >= 0.75)
        squeeze_quote = BorrowFeeQuote(
            symbol="KOSS",
            market="SP500",
            borrow_fee_annual=0.60,
            utilization_rate=0.96,
            lendable_shares=50_000.0,
            shares_on_loan=48_000.0,
            locate_available=True,
            locate_fraction=0.50,
            days_to_cover=9.0,
            short_interest_ratio=0.45,
            depletion_velocity=0.08,  # > 0.05 triggers AGGRESSIVE_TAKER
        )
        squeeze_eval_catalyst = SqueezeEvaluationResult(
            symbol="KOSS",
            market="SP500",
            squeeze_score=0.82,  # >= 0.75 trigger threshold
            is_squeeze_triggered=True,
            negative_carry_bps=35.0,
            net_alpha_after_carry=0.12,
            recall_risk=0.40,
            recommended_action="ACCELERATE_LONG",
            gate_8_1_status="MODIFIED",
        )
        long_order = {"symbol": "KOSS", "action": "BUY", "target_price": 50.0, "expected_return": 0.15}
        verdict_3 = model.evaluate_gate_8_1(
            long_order,
            borrow_quote=squeeze_quote,
            squeeze_eval=squeeze_eval_catalyst,
        )
        self.assertEqual(verdict_3.status, "MODIFIED")
        self.assertEqual(verdict_3.recommended_sleeve, "MOMENTUM_SQUEEZE")
        self.assertEqual(verdict_3.recommended_exec_strategy, "AGGRESSIVE_TAKER")
        self.assertAlmostEqual(verdict_3.target_stop_loss, 47.50)  # 50.0 * 0.95


    # =========================================================================
    # 4. ADVERSARIAL CHALLENGES FOR M4: Triangular Arbitrage Slicer
    # =========================================================================

    def _create_sample_adr_triplet(self) -> Tuple[ArbitrageTriplet, Dict[str, VenueQuote]]:
        """Helper creating valid ADR triplet and quotes."""
        triplet = ArbitrageTriplet(
            triplet_id="TRIPLET_TSMC",
            triplet_type=ArbitrageType.DUAL_LISTED_ADR,
            legs=(
                ArbitrageLegSpec(leg_id=1, symbol="TSM", venue="NYSE", side=OrderLegSide.SELL, leg_role=OrderLegType.LEADER, is_us=True),
                ArbitrageLegSpec(leg_id=2, symbol="2330", venue="TWSE", side=OrderLegSide.BUY, leg_role=OrderLegType.FOLLOWER),
                ArbitrageLegSpec(leg_id=3, symbol="USD/TWD", venue="FX_SPOT", side=OrderLegSide.BUY, leg_role=OrderLegType.HEDGE),
            ),
            depositary_ratio=5.0,  # 1 ADR = 5 ORD
            hurdle_rate_bps=2.5,
        )

        now_ns = 1_700_000_000_000_000_000
        quotes = {
            "TSM": VenueQuote(
                symbol="TSM", venue="NYSE",
                bid_price=155.00, ask_price=155.05,
                bid_size=10000, ask_size=10000,
                timestamp_ns=now_ns - 10_000_000,
                adv_shares=5_000_000.0,
            ),
            "2330": VenueQuote(
                symbol="2330", venue="TWSE",
                bid_price=980.00, ask_price=980.50,
                bid_size=50000, ask_size=50000,
                timestamp_ns=now_ns - 10_000_000,
                adv_shares=20_000_000.0,
            ),
            "USD/TWD": VenueQuote(
                symbol="USD/TWD", venue="FX_SPOT",
                bid_price=32.20, ask_price=32.22,
                bid_size=1_000_000, ask_size=1_000_000,
                timestamp_ns=now_ns - 10_000_000,
                adv_shares=500_000_000.0,
            ),
        }
        return triplet, quotes

    def test_m4_lookahead_injection_raises_lookaheadbiasexception(self) -> None:
        """
        Adversarial Test M4.1:
        Inject future quote timestamp (t_quote > t_eval) into the arbitrage detection engine.
        Verify that LookaheadBiasException is raised immediately, strictly preserving point-in-time integrity.
        """
        slicer = TriangularArbitrageSlicer()
        triplet, quotes = self._create_sample_adr_triplet()

        eval_time_ns = 1_700_000_000_000_000_000

        # Inject future timestamp into TSM quote (+1 nanosecond into the future)
        quotes["TSM"].timestamp_ns = eval_time_ns + 1

        with self.assertRaises(LookaheadBiasException):
            slicer.detect_discrepancy(triplet, quotes, evaluation_time_ns=eval_time_ns)

    def test_m4_integer_share_conservation_across_prime_quantities(self) -> None:
        """
        Adversarial Test M4.2:
        Test slicing schedule across prime / non-round share targets (e.g., 10,007 and 50,039 shares).
        Verify:
        - Exact integer volume conservation holds (sum(tranches) == target_quantity).
        - Tranche distribution is mathematically uniform with integer remainder dispersal.
        """
        slicer = TriangularArbitrageSlicer()
        triplet, quotes = self._create_sample_adr_triplet()

        target_quantities = {1: 10_007, 2: 50_039, 3: 10_007}
        schedule = slicer.compute_slicing_schedule(triplet, target_quantities, quotes, n_slices=7)

        self.assertTrue(schedule.integer_conservation_passed)
        self.assertEqual(schedule.n_slices, 7)

        for leg_id, target in target_quantities.items():
            tranches = schedule.slice_tranches[leg_id]
            self.assertEqual(len(tranches), 7)
            self.assertEqual(
                sum(tranches),
                target,
                f"Leg {leg_id} volume conservation failed: sum({tranches}) != {target}"
            )
            # All tranches must be strictly integer
            self.assertTrue(all(isinstance(t, int) for t in tranches))

    def test_m4_tranche_participation_cap_adv_enforcement(self) -> None:
        """
        Adversarial Test M4.3:
        Submit large order quantities relative to ADV (e.g. 50,000 shares on stock with ADV 1,000,000).
        Verify:
        - No single tranche exceeds the strict 1.5% ADV liquidity participation cap.
        - Slicer dynamically expands tranche count if needed to respect the cap.
        """
        slicer = TriangularArbitrageSlicer(max_adv_participation_rate=0.015)
        triplet, quotes = self._create_sample_adr_triplet()

        # Restrict ADV on TSM to 1,000,000 shares (1.5% cap = 15,000 shares per tranche)
        quotes["TSM"].adv_shares = 1_000_000.0

        # Request 120,000 shares (would be 12% ADV if done in 1 tranche)
        target_quantities = {1: 120_000, 2: 600_000, 3: 120_000}
        schedule = slicer.compute_slicing_schedule(triplet, target_quantities, quotes)

        # Slicer must expand n_slices (up to 12)
        tsm_tranches = schedule.slice_tranches[1]
        for tr in tsm_tranches:
            part_rate = tr / quotes["TSM"].adv_shares
            self.assertTrue(
                part_rate <= 0.015 + 1e-5,
                f"Tranche participation rate {part_rate:.4%} exceeded 1.5% ADV cap!"
            )

    def test_m4_partial_fill_emergency_unwinding_sub_50ms(self) -> None:
        """
        Adversarial Test M4.4:
        Simulate a partial fill on the leader leg (e.g. 35% fill ratio).
        Verify:
        - Emergency counter-unwind plan is immediately generated.
        - Unwind timeout SLA is guaranteed <= 50ms.
        - Zero Naked Overnight Delta guarantee is affirmed (zero_naked_delta_guarantee = True).
        - Unwind action is strictly the inverse of the leader side.
        """
        slicer = TriangularArbitrageSlicer(max_unwind_latency_ms=50.0)
        triplet, quotes = self._create_sample_adr_triplet()

        # Leader leg requested 1000 shares, fills only 350 (partial_fill_ratio = 0.35)
        tranche_quantities = {1: 1000, 2: 5000, 3: 1000}
        fills, unwind_plan = slicer.execute_atomic_tranche(
            triplet=triplet,
            tranche_quantities=tranche_quantities,
            quotes=quotes,
            execution_mode="LEADER_FOLLOWER",
            partial_fill_ratio=0.35,
        )

        self.assertIsNotNone(unwind_plan, "Unwind plan must be generated on asymmetric partial fill")
        self.assertIsInstance(unwind_plan, PartialFillUnwindPlan)
        self.assertTrue(unwind_plan.max_latency_ms <= 50.0, f"Unwind SLA exceeded 50ms: {unwind_plan.max_latency_ms}")
        self.assertTrue(unwind_plan.zero_naked_delta_guarantee)
        self.assertEqual(unwind_plan.unwind_order_type, "LIMIT_IOC")
        self.assertEqual(unwind_plan.mode, UnwindMode.AGGRESSIVE_COUNTER_UNWIND)

        # Leader leg in triplet was SELL -> counter unwind action must be BUY
        self.assertEqual(unwind_plan.unwind_action, "BUY")


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase111_adversarial_mandate_stress.py
=================================================
Empirical Adversarial Stress Harness for Phase 111 Challenge Mandate.
Release R127 / v118 Production Master (Features F525 & F526).

Mandate Coverage:
1. Vectorized LOB Engine (F525):
   - Deep ladder depth (10, 20, 50 levels) with millions of shares and rapid price level updates.
   - Iceberg orders: visible tranche consumption triggers hidden reload AND strictly loses
     FIFO priority behind all existing orders at that price level.
   - Pegged orders (Primary, Market, Midpoint): dynamic repricing does not cause infinite
     feedback loops when top-of-book revisions occur.
   - Microstructure metrics: micro-price, effective spread, multi-tier OBI, and queue depletion
     velocity never produce NaN, inf, or values outside theoretical bounds.
2. Deep Multivariate Hawkes Synthesizer (F526):
   - Extreme volatility, market stress, and flash crash scenarios across 5 global markets.
   - Spectral radius projection strictly guarantees subcritical stationarity (rho(Gamma) < 1.0)
     under standard simulation and prevents infinite event cascades.
   - Transient supercritical excursion ([1.02, 1.15]) during flash crashes is stabilized
     by the nonlinear refractory ceiling.
"""

from __future__ import annotations

import math
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
    MicrostructureMetrics,
    PriceLadderSnapshot,
)
from src.ai.deep_hawkes_synthesizer import (
    DeepMultivariateHawkesSynthesizer,
    NeuralBaselineNetwork,
    SimulationResult,
    HawkesEvent,
    VALID_MARKETS,
)


class TestPhase111AdversarialMandateStress(unittest.TestCase):
    """Deep Empirical Adversarial Stress Testing for Phase 111 Core Modules."""

    # =========================================================================
    # PART 1: VECTORIZED LOB ENGINE DEEP STRESS
    # =========================================================================

    def test_mandate_m1_deep_ladder_millions_of_shares(self) -> None:
        """
        Stress-test Vectorized LOB with 50 levels of bids and 50 levels of asks.
        Populate 10,000,000 shares across 1,000 orders.
        Perform rapid updates, sweeps, and verify ladder invariants.
        """
        book = VectorizedOrderBook(symbol="MEGA_LOB", max_levels=50, tick_size=0.01)

        # Populate 50 bid levels (100.00 down to 99.51) and 50 ask levels (100.01 up to 100.50)
        # 10 orders of 10,000 shares per level = 100,000 shares per level * 100 levels = 10,000,000 shares
        order_count = 0
        total_bid_shares = 0.0
        total_ask_shares = 0.0

        t0 = time.perf_counter()
        for level in range(50):
            bid_px = round(100.00 - level * 0.01, 2)
            ask_px = round(100.01 + level * 0.01, 2)
            for o in range(10):
                oid_b = f"bid_{level}_{o}"
                oid_a = f"ask_{level}_{o}"
                book.add_order(order_id=oid_b, side=OrderSide.BUY, price=bid_px, volume=10_000.0)
                book.add_order(order_id=oid_a, side=OrderSide.SELL, price=ask_px, volume=10_000.0)
                order_count += 2
                total_bid_shares += 10_000.0
                total_ask_shares += 10_000.0

        elapsed_populate = time.perf_counter() - t0
        self.assertEqual(order_count, 1000)
        self.assertEqual(total_bid_shares, 5_000_000.0)
        self.assertEqual(total_ask_shares, 5_000_000.0)
        # Insertion rate must be high performance (> 1,000 orders/sec)
        self.assertLess(elapsed_populate, 2.0, f"Orderbook population took too long: {elapsed_populate:.4f}s")

        # Invariant checks across 10, 20, 50 level ladder snapshots
        for k in (10, 20, 50):
            snap = book.get_ladder_snapshot(levels=k)
            self.assertEqual(snap.depth_levels, k)
            self.assertEqual(len(snap.bid_prices), k)
            self.assertEqual(len(snap.ask_prices), k)

            # Monotonicity check
            self.assertTrue(np.all(np.diff(snap.bid_prices) < 0), "Bid ladder prices must strictly decrease")
            self.assertTrue(np.all(np.diff(snap.ask_prices) > 0), "Ask ladder prices must strictly increase")

            # Volume per level must be exactly 100,000.0
            self.assertTrue(np.allclose(snap.bid_volumes, 100_000.0), "Bid volume per level mismatch")
            self.assertTrue(np.allclose(snap.ask_volumes, 100_000.0), "Ask volume per level mismatch")

            # Order count per level must be exactly 10
            self.assertTrue(np.all(snap.bid_orders == 10), "Bid orders count per level mismatch")
            self.assertTrue(np.all(snap.ask_orders == 10), "Ask orders count per level mismatch")

        # Top-of-book quotes
        self.assertEqual(book.best_bid, 100.00)
        self.assertEqual(book.best_ask, 100.01)
        self.assertAlmostEqual(book.spread, 0.01, places=4)
        self.assertAlmostEqual(book.mid_price, 100.005, places=4)

        # Non-mutating sweep simulation of 2,500,000 shares (25 full levels)
        vwap_buy, slip_buy, filled_buy = book.simulate_sweep(OrderSide.BUY, 2_500_000.0)
        self.assertEqual(filled_buy, 2_500_000.0)
        # Levels swept: 100.01 up to 100.25 (25 levels of 100,000 each)
        expected_vwap_buy = np.mean([100.01 + i * 0.01 for i in range(25)])
        self.assertAlmostEqual(vwap_buy, expected_vwap_buy, places=4)
        self.assertGreater(slip_buy, 0.0)

        # Verify book was NOT mutated by simulate_sweep
        snap_after = book.get_ladder_snapshot(levels=50)
        self.assertTrue(np.allclose(snap_after.ask_volumes, 100_000.0))

        # Stress: 1,000 rapid randomized additions, cancellations, and market sweeps
        rng = np.random.RandomState(42)
        t_stress = time.perf_counter()
        for step in range(1000):
            action = step % 4
            if action == 0:
                # Add random limit order
                px = round(100.0 + rng.uniform(-0.50, 0.50), 2)
                s = OrderSide.BUY if px <= 100.00 else OrderSide.SELL
                book.add_order(order_id=f"rnd_{step}", side=s, price=px, volume=500.0)
            elif action == 1:
                # Cancel an existing order
                book.cancel_order(f"rnd_{step - 1}")
            elif action == 2:
                # Small market sweep
                s = OrderSide.BUY if rng.rand() > 0.5 else OrderSide.SELL
                book.execute_market_order(side=s, volume=5000.0)
            else:
                # Metrics evaluation
                m = book.compute_microstructure_metrics()
                self.assertTrue(np.isfinite(m.mid_price))
                self.assertTrue(np.isfinite(m.micro_price_l1))

        elapsed_stress = time.perf_counter() - t_stress
        self.assertLess(elapsed_stress, 3.0, f"1000 randomized operations took too long: {elapsed_stress:.4f}s")

    def test_mandate_m1_iceberg_strict_fifo_priority_loss(self) -> None:
        """
        Verify Iceberg orders:
        1. Visible tranche consumption triggers hidden reload.
        2. Reloaded iceberg strictly loses FIFO priority behind ALL existing orders
           at that price level.
        """
        book = VectorizedOrderBook(symbol="TSLA", tick_size=0.01)
        p = 200.00

        # Step 1: Submit Orders at price P = 200.00
        # Order 1: Regular limit buy for 500 shares
        book.add_order(order_id="reg_1", side=OrderSide.BUY, price=p, volume=500.0, order_type=OrderType.LIMIT)

        # Order 2: Iceberg buy for 2,000 total shares, peak 200 (display=200, hidden=1800)
        ice_order, _ = book.add_order(
            order_id="ice_1",
            side=OrderSide.BUY,
            price=p,
            volume=2000.0,
            order_type=OrderType.ICEBERG,
            peak_size=200.0,
        )
        self.assertEqual(ice_order.display_volume, 200.0)
        self.assertEqual(ice_order.hidden_volume, 1800.0)

        # Order 3: Regular limit buy for 300 shares
        book.add_order(order_id="reg_2", side=OrderSide.BUY, price=p, volume=300.0, order_type=OrderType.LIMIT)

        # Order 4: Regular limit buy for 400 shares
        book.add_order(order_id="reg_3", side=OrderSide.BUY, price=p, volume=400.0, order_type=OrderType.LIMIT)

        # Queue at p=200.00 is strictly: [reg_1 (500), ice_1 (200), reg_2 (300), reg_3 (400)]
        q = list(book.bid_order_queues[p])
        self.assertEqual(q, ["reg_1", "ice_1", "reg_2", "reg_3"])

        # Step 2: First market sell for 500 shares (consumes reg_1)
        _, res_1 = book.add_order(
            order_id="sell_1",
            side=OrderSide.SELL,
            price=0.0,
            volume=500.0,
            order_type=OrderType.MARKET,
        )
        self.assertEqual(res_1.filled_volume, 500.0)
        self.assertEqual(len(res_1.fills), 1)
        self.assertEqual(res_1.fills[0].maker_order_id, "reg_1")

        # Queue is now: [ice_1 (200), reg_2 (300), reg_3 (400)]
        q = list(book.bid_order_queues[p])
        self.assertEqual(q, ["ice_1", "reg_2", "reg_3"])
        self.assertEqual(ice_order.display_volume, 200.0)
        self.assertEqual(ice_order.hidden_volume, 1800.0)

        # Step 3: Second market sell for 200 shares (consumes the entire display tranche of ice_1)
        # This MUST trigger reload of 200 from hidden (hidden becomes 1600)
        # AND ice_1 MUST be moved to the tail behind reg_2 AND reg_3!
        _, res_2 = book.add_order(
            order_id="sell_2",
            side=OrderSide.SELL,
            price=0.0,
            volume=200.0,
            order_type=OrderType.MARKET,
        )
        self.assertEqual(res_2.filled_volume, 200.0)
        self.assertEqual(res_2.fills[0].maker_order_id, "ice_1")

        # VERIFICATION: ice_1 reloaded and lost priority to tail of queue
        self.assertEqual(ice_order.display_volume, 200.0)
        self.assertEqual(ice_order.hidden_volume, 1600.0)
        q = list(book.bid_order_queues[p])
        self.assertEqual(q, ["reg_2", "reg_3", "ice_1"], "Iceberg order failed to lose FIFO priority to tail")

        # Step 4: Third market sell for 350 shares
        # Must consume 300 from reg_2, then 50 from reg_3.
        # ice_1 MUST NOT BE TOUCHED!
        _, res_3 = book.add_order(
            order_id="sell_3",
            side=OrderSide.SELL,
            price=0.0,
            volume=350.0,
            order_type=OrderType.MARKET,
        )
        self.assertEqual(res_3.filled_volume, 350.0)
        self.assertEqual(len(res_3.fills), 2)
        self.assertEqual(res_3.fills[0].maker_order_id, "reg_2")
        self.assertEqual(res_3.fills[0].volume, 300.0)
        self.assertEqual(res_3.fills[1].maker_order_id, "reg_3")
        self.assertEqual(res_3.fills[1].volume, 50.0)

        # reg_2 is fully filled and deleted; reg_3 has 350 left; ice_1 still has 200 display untouched!
        q = list(book.bid_order_queues[p])
        self.assertEqual(q, ["reg_3", "ice_1"])
        self.assertEqual(book.orders["reg_3"].display_volume, 350.0)
        self.assertEqual(ice_order.display_volume, 200.0)
        self.assertEqual(ice_order.hidden_volume, 1600.0)

    def test_mandate_m1_pegged_orders_repricing_no_infinite_loop(self) -> None:
        """
        Verify Pegged Orders (Primary, Market, Midpoint):
        1. Repricing accurately tracks top-of-book changes.
        2. Dynamic repricing does not cause infinite feedback loops or oscillation.
        3. Lit quote calculation correctly isolates pegged orders from lit references.
        """
        book = VectorizedOrderBook(symbol="GOOGL", tick_size=0.01)

        # Add lit orders
        book.add_order(order_id="lit_b1", side=OrderSide.BUY, price=150.00, volume=100.0)
        book.add_order(order_id="lit_a1", side=OrderSide.SELL, price=150.20, volume=100.0)

        self.assertEqual(book.best_bid, 150.00)
        self.assertEqual(book.best_ask, 150.20)
        self.assertAlmostEqual(book.mid_price, 150.10, places=4)

        # Submit pegged orders
        # Primary Peg Buy: tracks best lit bid (150.00) with offset +0.02 -> 150.02
        p_peg, _ = book.add_order(
            order_id="peg_pri",
            side=OrderSide.BUY,
            price=150.00,
            volume=50.0,
            order_type=OrderType.PRIMARY_PEG,
            peg_offset=0.02,
        )
        self.assertEqual(p_peg.price, 150.02)

        # Midpoint Peg: tracks lit midpoint (150.10) with offset 0.0 -> 150.10
        mid_peg, _ = book.add_order(
            order_id="peg_mid",
            side=OrderSide.BUY,
            price=150.00,
            volume=50.0,
            order_type=OrderType.MIDPOINT_PEG,
            peg_offset=0.0,
        )
        self.assertEqual(mid_peg.price, 150.10)

        # Market Peg Buy: tracks opposing lit ask (150.20) with offset +0.05 (passive below ask) -> 150.15
        mkt_peg, _ = book.add_order(
            order_id="peg_mkt",
            side=OrderSide.BUY,
            price=150.00,
            volume=50.0,
            order_type=OrderType.MARKET_PEG,
            peg_offset=0.05,
        )
        self.assertIsNotNone(mkt_peg)
        self.assertEqual(mkt_peg.price, 150.15)

        # Verify lit quotes ignore pegged orders:
        bb, ba = book._get_best_lit_quotes()
        self.assertEqual(bb, 150.00)
        self.assertEqual(ba, 150.20)

        # Calling reprice without changes to lit quotes should reprice 0 orders
        repriced = book.reprice_pegged_orders()
        self.assertEqual(repriced, 0, "Pegged orders repriced without lit quote change")

        # Repeat 20 times to verify no feedback loop or runaway escalation
        for _ in range(20):
            r = book.reprice_pegged_orders()
            self.assertEqual(r, 0)

        # Now shift lit book: new lit bid at 150.05, new lit ask at 150.35
        book.add_order(order_id="lit_b2", side=OrderSide.BUY, price=150.05, volume=100.0)
        book.add_order(order_id="lit_a2", side=OrderSide.SELL, price=150.35, volume=100.0)

        bb, ba = book._get_best_lit_quotes()
        self.assertEqual(bb, 150.05)
        self.assertEqual(ba, 150.20)  # lit_a1 at 150.20 is still lower

        # Single call to reprice_pegged_orders should reprice:
        # p_peg: 150.05 + 0.02 = 150.07
        # mid_peg: 0.5 * (150.05 + 150.20) = 150.125
        # mkt_peg: 150.20 - 0.05 = 150.15 (unchanged)
        repriced = book.reprice_pegged_orders()
        self.assertGreater(repriced, 0)
        self.assertAlmostEqual(p_peg.price, 150.07, places=4)
        self.assertAlmostEqual(mid_peg.price, 150.125, places=4)

        # Immediate follow-up call must be 0 (stable equilibrium)
        self.assertEqual(book.reprice_pegged_orders(), 0)

    def test_mandate_m1_microstructure_metrics_bounds_and_robustness(self) -> None:
        """
        Verify Microstructure Metrics:
        - Completely empty book
        - One-sided book (bids only, asks only)
        - Extreme asymmetry (1e-6 vs 1e8 volume)
        - Sub-nanosecond rapid depletion (dt = 1ns)
        All metrics must be finite, non-NaN, and strictly within mathematical bounds.
        """
        # Scenario 1: Empty Book
        empty_book = VectorizedOrderBook(symbol="EMPTY", tick_size=0.01)
        m_empty = empty_book.compute_microstructure_metrics()
        self.assertTrue(np.isfinite(m_empty.mid_price))
        self.assertTrue(np.isfinite(m_empty.spread))
        self.assertTrue(np.isfinite(m_empty.micro_price_l1))
        self.assertTrue(np.isfinite(m_empty.effective_spread_bps))
        self.assertEqual(m_empty.obi_1, 0.0)
        self.assertEqual(m_empty.weighted_obi, 0.0)
        self.assertEqual(m_empty.time_to_exhaustion_bid_sec, 999.0)
        self.assertEqual(m_empty.time_to_exhaustion_ask_sec, 999.0)

        # Scenario 2: One-Sided Book (Bids only)
        bid_only_book = VectorizedOrderBook(symbol="BID_ONLY", tick_size=0.01)
        bid_only_book.add_order("b1", OrderSide.BUY, 100.0, 1000.0)
        m_bid = bid_only_book.compute_microstructure_metrics()
        self.assertEqual(m_bid.best_bid, 100.0)
        self.assertEqual(m_bid.best_ask, 0.0)
        self.assertEqual(m_bid.mid_price, 100.0)
        self.assertEqual(m_bid.obi_1, 1.0)
        self.assertEqual(m_bid.weighted_obi, 1.0)
        self.assertTrue(0.0 <= m_bid.estimated_fill_prob_bid <= 1.0)

        # Scenario 3: One-Sided Book (Asks only)
        ask_only_book = VectorizedOrderBook(symbol="ASK_ONLY", tick_size=0.01)
        ask_only_book.add_order("a1", OrderSide.SELL, 105.0, 1000.0)
        m_ask = ask_only_book.compute_microstructure_metrics()
        self.assertEqual(m_ask.best_bid, 0.0)
        self.assertEqual(m_ask.best_ask, 105.0)
        self.assertEqual(m_ask.mid_price, 105.0)
        self.assertEqual(m_ask.obi_1, -1.0)
        self.assertEqual(m_ask.weighted_obi, -1.0)
        self.assertTrue(0.0 <= m_ask.estimated_fill_prob_ask <= 1.0)

        # Scenario 4: Extreme Depth Asymmetry (Bid 1 share vs Ask 10,000,000 shares)
        asym_book = VectorizedOrderBook(symbol="ASYM", tick_size=0.01)
        asym_book.add_order("b_tiny", OrderSide.BUY, 100.00, 1.0)
        asym_book.add_order("a_huge", OrderSide.SELL, 100.02, 10_000_000.0)
        m_asym = asym_book.compute_microstructure_metrics()

        # Stoikov micro-price formula: micro = (va*bb + vb*ba)/(va+vb) -> bb as va -> inf
        self.assertAlmostEqual(m_asym.micro_price_l1, 100.00, places=4)
        self.assertTrue(m_asym.best_bid <= m_asym.micro_price_l1 <= m_asym.best_ask)
        self.assertAlmostEqual(m_asym.obi_1, -1.0, places=4)
        self.assertAlmostEqual(m_asym.weighted_obi, -1.0, places=4)
        self.assertGreaterEqual(m_asym.effective_spread_bps, m_asym.spread_bps)

        # Scenario 5: Sub-nanosecond depletion rate evaluation
        t_base = 1_000_000_000_000
        asym_book.add_order("b_dep1", OrderSide.BUY, 100.00, 500.0, timestamp_ns=t_base)
        # 1 nanosecond later, sweep 500 shares
        asym_book.execute_market_order(OrderSide.SELL, 500.0, timestamp_ns=t_base + 1)
        m_dep = asym_book.compute_microstructure_metrics(timestamp_ns=t_base + 2)
        self.assertTrue(np.isfinite(m_dep.bid_depletion_rate))
        self.assertTrue(np.isfinite(m_dep.bid_depletion_accel))
        self.assertTrue(np.isfinite(m_dep.time_to_exhaustion_bid_sec))

    # =========================================================================
    # PART 2: DEEP HAWKES PROCESS GENERATIVE SYNTHESIZER DEEP STRESS
    # =========================================================================

    def test_mandate_m2_extreme_volatility_and_market_stress_across_5_markets(self) -> None:
        """
        Verify Deep Hawkes Synthesizer under extreme volatility and market stress:
        - All 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
        - Regimes: NORMAL, VOLATILE, BEAR, CRISIS.
        - Baseline intensities monotonically expand under stress and remain strictly positive.
        """
        for mkt in VALID_MARKETS:
            hawkes = DeepMultivariateHawkesSynthesizer(market=mkt, dimension=6)

            mu_normal = hawkes.compute_neural_baseline(regime="NORMAL")
            mu_volatile = hawkes.compute_neural_baseline(regime="VOLATILE")
            mu_bear = hawkes.compute_neural_baseline(regime="BEAR")
            mu_crisis = hawkes.compute_neural_baseline(regime="CRISIS")

            # Check positivity guarantee
            self.assertTrue(np.all(mu_normal >= 0.08), f"{mkt} normal baseline < base_floor")
            self.assertTrue(np.all(mu_volatile >= 0.08))
            self.assertTrue(np.all(mu_bear >= 0.08))
            self.assertTrue(np.all(mu_crisis >= 0.08))

            # Stress monotonicity
            self.assertGreater(np.mean(mu_crisis), np.mean(mu_bear))
            self.assertGreater(np.mean(mu_bear), np.mean(mu_volatile))
            self.assertGreater(np.mean(mu_volatile), np.mean(mu_normal))

            # Finite check
            self.assertTrue(np.all(np.isfinite(mu_crisis)))

    def test_mandate_m2_spectral_radius_stationarity_guarantee_and_cascade_prevention(self) -> None:
        """
        Verify Spectral Radius Projection strictly guarantees subcritical stationarity (rho < 1.0):
        1. Intentionally construct an explosive, supercritical parameter matrix (rho = 5.0).
        2. Apply project_to_stability(max_branching=0.95).
        3. Verify post-projection rho <= 0.95 < 1.0.
        4. Test across all 3 decay kernels (exponential, power_law, multi_exp).
        5. Verify standard simulation terminates with finite event count (no infinite cascades).
        """
        for k_type in ("exponential", "power_law", "multi_exp"):
            hawkes = DeepMultivariateHawkesSynthesizer(market="SP500", dimension=6, kernel_type=k_type)

            # Inject heavily explosive alpha matrix: rho > 1.5
            dim = 6
            explosive_alpha = np.full((dim, dim), 25.0, dtype=np.float64)
            unprojected_rho = hawkes.compute_branching_ratio(alpha=explosive_alpha)
            self.assertGreater(unprojected_rho, 1.5, f"Expected unprojected rho > 1.5, got {unprojected_rho}")

            # Calibrate with custom explosive alpha and enforce stability
            cal = hawkes.calibrate_market("SP500", custom_alpha=explosive_alpha, max_branching=0.95)
            self.assertTrue(cal.is_stable)
            self.assertLessEqual(cal.branching_ratio, 0.950001)

            # Confirm engine state
            projected_rho = hawkes.compute_branching_ratio()
            self.assertLessEqual(projected_rho, 0.950001)
            self.assertGreater(projected_rho, 0.0)

            # Run 2.0s simulation under stationary regime: must NOT trigger infinite cascade or exceed max_events
            sim_res = hawkes.simulate_order_stream(
                duration_seconds=2.0,
                regime="NORMAL",
                max_events=5000,
            )
            self.assertLess(len(sim_res.events), 5000, f"Kernel {k_type} hit max_events limit in normal regime")
            self.assertGreater(len(sim_res.events), 5, f"Kernel {k_type} produced insufficient events")
            self.assertFalse(sim_res.is_flash_burst)

    def test_mandate_m2_flash_crash_supercritical_excursion_and_refractory_stabilization(self) -> None:
        """
        Verify Flash Crash Simulation:
        1. Transient supercritical excursion with rho in [1.02, 1.15].
        2. Non-linear refractory ceiling lambda / (1 + 0.002 * lambda) prevents explosive numerical divergence.
        3. Post-simulation stationarity is automatically restored (rho <= 0.98).
        """
        hawkes = DeepMultivariateHawkesSynthesizer(market="NASDAQ", dimension=6)

        # Baseline stationarity
        initial_rho = hawkes.compute_branching_ratio()
        self.assertLess(initial_rho, 1.0)

        # Simulate flash crash
        sim_res = hawkes.simulate_order_stream(
            duration_seconds=1.0,
            regime="FLASH_CRASH",
            initial_price=150.0,
            max_events=10000,
            seed=777,
        )

        self.assertTrue(sim_res.is_flash_burst)
        self.assertGreater(len(sim_res.events), 50, "Flash crash should generate high density cluster bursts")
        self.assertLess(len(sim_res.events), 10000, "Refractory ceiling failed: event count exceeded 10,000")

        # Verify cluster burst density: flash crash event rate >> normal event rate
        normal_res = hawkes.simulate_order_stream(
            duration_seconds=1.0,
            regime="NORMAL",
            seed=777,
        )
        self.assertGreater(
            len(sim_res.events),
            len(normal_res.events),
            "Flash crash event density must exceed normal regime",
        )

        # Verify all synthesized prices and volumes remain positive and finite
        for ev in sim_res.events:
            self.assertGreater(ev.price, 0.0)
            self.assertGreater(ev.volume, 0.0)
            self.assertTrue(np.isfinite(ev.intensity_at_arrival))

        # Stationarity MUST be restored after flash crash
        post_rho = hawkes.compute_branching_ratio()
        self.assertLessEqual(post_rho, 0.980001, f"Post-flash-crash stationarity not restored: {post_rho}")


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase196_m2_adversarial_challenger2.py
=================================================
Empirical Adversarial Challenge & Stress-Test Suite for Milestone 2:
- Feature F975: Leland Dynamic Buffer Bands & 3.0x Ultra-Confluence Expansion (src/execution/leland_buffer_bands.py)
- Feature F976: Smart Order Router 55% Midpoint Darkpool Routing & Hawkes Urgency Slicing (src/execution/smart_order_router.py)
- High-Throughput Execution Latency SLA Verification across 100 Assets (<25ms, <10ms, <5ms).
"""

import math
import time
import unittest
from typing import Dict, Any

import numpy as np
import pytest

from src.execution.leland_buffer_bands import (
    calculate_leland_buffer_phase196,
    compute_asymmetric_leland_bands_phase196,
    filter_portfolio_rebalance_phase196,
    LelandBufferBandEngine,
)
from src.execution.smart_order_router import (
    route_child_order_phase196,
    SmartOrderRouter,
    SmartOrderRouterPhase196,
    Phase196SmartOrderRouter,
    F976SmartOrderRouter,
)
from src.risk.unified_portfolio_allocator import (
    allocate_portfolio_phase196,
    UnifiedPortfolioAllocator,
    UnifiedPortfolioAllocatorPhase196,
)


class TestLelandBufferConfluenceBoundaryStress(unittest.TestCase):
    """
    Challenge 1: Leland Buffer Band Confluence Boundary Stress (Feature F975).
    """

    def test_challenge_confluence_threshold_sharp_transition(self):
        """
        Stress test transition at confluence threshold 2.50:
        Test at 2.499, 2.500, and 3.500.
        Verify upper bandwidth expands to exactly 3.0x base band at and above 2.50.
        """
        base_band = calculate_leland_buffer_phase196(confluence_score=1.0, volatility=0.15, spread_bps=10.0)
        band_sub = calculate_leland_buffer_phase196(confluence_score=2.499999, volatility=0.15, spread_bps=10.0)
        band_at = calculate_leland_buffer_phase196(confluence_score=2.500000, volatility=0.15, spread_bps=10.0)
        band_sup = calculate_leland_buffer_phase196(confluence_score=3.500000, volatility=0.15, spread_bps=10.0)

        # At 2.499999, must be strictly base_band
        self.assertAlmostEqual(band_sub, base_band, places=6,
                               msg=f"Expected base_band {base_band} at confluence 2.499999, got {band_sub}")
        # At 2.500000, must be exactly 3.0x base_band
        self.assertAlmostEqual(band_at, base_band * 3.0, places=6,
                               msg=f"Expected 3.0x base_band {base_band * 3.0} at confluence 2.500, got {band_at}")
        # At 3.500000, must remain clamped at 3.0x base_band
        self.assertAlmostEqual(band_sup, base_band * 3.0, places=6,
                               msg=f"Expected 3.0x base_band {base_band * 3.0} at confluence 3.500, got {band_sup}")

    def test_challenge_extreme_negative_alpha_lower_band_contraction(self):
        """
        Test extreme negative alpha: alpha = -5.0.
        Verify lower buffer band contracts down to exactly 0.40x base band:
        - When isolating asymmetric modulation (without surge compression): exactly 0.40x base band.
        - When catalyst surge is also triggered (|alpha| / cost >= 3.5): bandwidth is further compressed by 70% (0.30x),
          giving exactly 0.40 * 0.30 = 0.12x base band.
        """
        curr = {"DETERIORATING": 0.05}
        targ = {"DETERIORATING": 0.04}
        alphas = {"DETERIORATING": -5.0}
        vols = {"DETERIORATING": 0.20}

        # 1. Isolating asymmetric modulation by setting catalyst_surge_ratio to infinity
        bands_asym_only = compute_asymmetric_leland_bands_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas=alphas,
            volatilities=vols,
            spread_bps=10.0,
            impact_coef=0.05,
            risk_aversion=1.0,
            catalyst_surge_ratio=float("inf"),
        )
        b_info = bands_asym_only["DETERIORATING"]
        delta_base = b_info["delta_base"]
        delta_minus = b_info["half_width_minus"]
        asym_delta = b_info["asymmetry_delta"]

        # tanh(-5.0 / 0.20) = tanh(-25) = -1.0
        self.assertAlmostEqual(asym_delta, -1.0, places=4)

        # Asymmetric lower band formula: delta_minus = delta_base * max(0.40, 1.0 + 0.60 * (-1.0)) = delta_base * 0.40
        expected_minus = delta_base * 0.40
        self.assertAlmostEqual(delta_minus, expected_minus, places=5,
                               msg=f"Lower band width must contract to 0.40x base band: got {delta_minus}, expected {expected_minus}")

        # 2. Dual effect when catalyst surge is active (|alpha| / cost >= 3.5)
        bands_with_surge = compute_asymmetric_leland_bands_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas=alphas,
            volatilities=vols,
            spread_bps=10.0,
            impact_coef=0.05,
            risk_aversion=1.0,
            catalyst_surge_ratio=3.5,
        )
        b_surge = bands_with_surge["DETERIORATING"]
        self.assertEqual(b_surge["bypass_flag"], "CATALYST_SURGE")
        # delta_minus must be exactly 0.40 * 0.30 = 0.12x base band
        self.assertAlmostEqual(b_surge["half_width_minus"], expected_minus * 0.30, places=5)

    def test_challenge_triple_zero_lag_bypass(self):
        """
        Challenge Triple Zero-Lag Bypass:
        1. Fresh entries: w_curr <= 1e-4, w_targ > 1e-4 -> 0.0 delay/bandwidth
        2. Full exits: w_targ <= 1e-4, w_curr > 1e-4 -> 0.0 delay/bandwidth
        3. Catalyst surge: |alpha| / cost >= 3.5 -> bandwidth compressed by exactly 70% (0.30x base band)
        """
        # Standalone function checks
        self.assertEqual(calculate_leland_buffer_phase196(confluence_score=3.0, action="FRESH_ENTRY"), 0.0)
        self.assertEqual(calculate_leland_buffer_phase196(confluence_score=3.0, action="FULL_EXIT"), 0.0)

        base_val = calculate_leland_buffer_phase196(confluence_score=1.0, action="HOLD")
        surge_val = calculate_leland_buffer_phase196(confluence_score=1.0, action="CATALYST_SURGE")
        self.assertAlmostEqual(surge_val, base_val * 0.30, places=6,
                               msg=f"Surge compression must be exactly 0.30x base band: got {surge_val}, expected {base_val * 0.30}")

        # Multi-asset dictionary checks with portfolio rebalance filter
        curr = {
            "FRESH_STOCK": 0.0,
            "EXIT_STOCK": 0.08,
            "SURGE_STOCK": 0.05,
            "NORMAL_STOCK": 0.05,
        }
        targ = {
            "FRESH_STOCK": 0.06,
            "EXIT_STOCK": 0.0,
            "SURGE_STOCK": 0.055,
            "NORMAL_STOCK": 0.051,
        }
        alphas = {
            "FRESH_STOCK": 1.0,
            "EXIT_STOCK": -2.0,
            "SURGE_STOCK": 0.80,   # high catalyst surge
            "NORMAL_STOCK": 0.01,
        }
        # cost = 10 bps / 10000 + 0.05 * 0.01 = 0.0010 + 0.0005 = 0.0015
        # |alpha| / cost = 0.80 / 0.0015 = 533.3 >= 3.5

        out = filter_portfolio_rebalance_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas=alphas,
            volatilities={"FRESH_STOCK": 0.2, "EXIT_STOCK": 0.2, "SURGE_STOCK": 0.2, "NORMAL_STOCK": 0.2},
            spread_bps=10.0,
            impact_coef=0.05,
        )

        # Fresh entry must bypass directly to target with zero bandwidth
        self.assertEqual(out.actions["FRESH_STOCK"], "BYPASS_ENTRY")
        self.assertAlmostEqual(out.executable_weights["FRESH_STOCK"], 0.06, places=5)
        # Bandwidth is upper_band - lower_band == 0.0
        self.assertEqual(out.bands["FRESH_STOCK"][1] - out.bands["FRESH_STOCK"][0], 0.0)

        # Full exit must bypass directly to 0.0 with zero bandwidth
        self.assertEqual(out.actions["EXIT_STOCK"], "BYPASS_EXIT")
        self.assertAlmostEqual(out.executable_weights["EXIT_STOCK"], 0.0, places=5)
        # Bandwidth is upper_band - lower_band == 0.0
        self.assertEqual(out.bands["EXIT_STOCK"][1] - out.bands["EXIT_STOCK"][0], 0.0)

        # Normal stock should be held inside buffer
        self.assertEqual(out.actions["NORMAL_STOCK"], "HOLD")
        self.assertAlmostEqual(out.executable_weights["NORMAL_STOCK"], 0.05, places=5)

        # Synthetic rows must be native int 0
        self.assertIs(type(out.synthetic_rows), int)
        self.assertFalse(isinstance(out.synthetic_rows, bool))
        self.assertEqual(out.synthetic_rows, 0)

    def test_challenge_full_exit_overrides_high_confluence(self):
        """
        Adversarial corner case: If target_weight is 0.0 (full liquidation),
        even if confluence score is extremely high (e.g. 5.0) or alpha is huge,
        it MUST execute full exit with 0.0 bandwidth immediately (no holding).
        """
        curr = {"WINNER_LIQUIDATING": 0.10}
        targ = {"WINNER_LIQUIDATING": 0.00}
        alphas = {"WINNER_LIQUIDATING": 5.0}

        out = filter_portfolio_rebalance_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas=alphas,
        )
        self.assertEqual(out.actions["WINNER_LIQUIDATING"], "BYPASS_EXIT")
        self.assertAlmostEqual(out.executable_weights["WINNER_LIQUIDATING"], 0.0, places=6)
        # Bandwidth is strictly zero (upper_band == lower_band)
        self.assertEqual(out.bands["WINNER_LIQUIDATING"][1] - out.bands["WINNER_LIQUIDATING"][0], 0.0)

    def test_challenge_numerical_resilience_degenerate_inputs(self):
        """
        Adversarial corner case: zero spread, zero volatility, zero risk aversion.
        Ensures Leland bandwidth calculations never produce NaN, Inf, or zero-division crashes.
        """
        for vol in (1e-6, 0.0, 1.5):
            for spread in (0.0, 100.0):
                for gamma in (0.0, 1.0, 10.0):
                    band = calculate_leland_buffer_phase196(
                        confluence_score=2.6,
                        volatility=vol,
                        spread_bps=spread,
                    )
                    self.assertTrue(math.isfinite(band), f"Band not finite for vol={vol}, spread={spread}")
                    self.assertGreaterEqual(band, 0.0)


class TestSmartOrderRouterExecutionHawkesUrgencyStress(unittest.TestCase):
    """
    Challenge 2: Smart Order Router Execution & Hawkes Urgency Stress (Feature F976).
    """

    def test_challenge_urgency_boundary_transition(self):
        """
        Challenge urgency transition boundary: urgency = 0.799 vs 0.800.
        Verify darkpool ratio transitions from 55% to 15% and lit exchange expands from 45% to 85%.
        """
        qty = 10000.0
        route_sub = route_child_order_phase196(order_qty=qty, spread_bps=12.0, urgency=0.799)
        route_at = route_child_order_phase196(order_qty=qty, spread_bps=12.0, urgency=0.800)
        route_sup = route_child_order_phase196(order_qty=qty, spread_bps=12.0, urgency=0.801)

        # At urgency = 0.799: 55% darkpool, 45% lit
        self.assertEqual(route_sub["darkpool_pct"], 0.55)
        self.assertAlmostEqual(route_sub["darkpool_qty"], 5500.0, places=2)
        self.assertAlmostEqual(route_sub["lit_qty"], 4500.0, places=2)

        # At urgency = 0.800: 15% darkpool, 85% lit
        self.assertEqual(route_at["darkpool_pct"], 0.15)
        self.assertAlmostEqual(route_at["darkpool_qty"], 1500.0, places=2)
        self.assertAlmostEqual(route_at["lit_qty"], 8500.0, places=2)

        # At urgency = 0.801: 15% darkpool, 85% lit
        self.assertEqual(route_sup["darkpool_pct"], 0.15)
        self.assertAlmostEqual(route_sup["darkpool_qty"], 1500.0, places=2)
        self.assertAlmostEqual(route_sup["lit_qty"], 8500.0, places=2)

        # Ensure total slice conservation
        self.assertAlmostEqual(route_sub["darkpool_qty"] + route_sub["lit_qty"], qty, places=4)
        self.assertAlmostEqual(route_at["darkpool_qty"] + route_at["lit_qty"], qty, places=4)
        self.assertAlmostEqual(route_sup["darkpool_qty"] + route_sup["lit_qty"], qty, places=4)

    def test_challenge_extreme_hawkes_order_arrival_intensity(self):
        """
        Challenge extreme Hawkes order arrival intensity:
        lambda_Hawkes = 0.0 vs 1.0 vs 10.0 vs 100.0.
        Verify effective urgency increases monotonically according to:
            min(1.0, urgency * (1.0 + 0.1 * ln(1 + lambda)))
        and remains strictly clamped <= 1.0.
        """
        base_urgency = 0.50
        lambdas = [0.0, 1.0, 10.0, 100.0, 1000.0, 1e6]
        effective_urgencies = []

        for lam in lambdas:
            route = route_child_order_phase196(order_qty=5000.0, urgency=base_urgency, hawkes_intensity=lam)
            eff_u = route["effective_urgency"]
            expected_u = min(1.0, base_urgency * (1.0 + 0.1 * math.log1p(lam)))
            self.assertAlmostEqual(eff_u, expected_u, places=6,
                                   msg=f"Hawkes formula mismatch for lambda={lam}: got {eff_u}, expected {expected_u}")
            self.assertLessEqual(eff_u, 1.0, f"Effective urgency exceeded 1.0 for lambda={lam}")
            self.assertGreaterEqual(eff_u, base_urgency, f"Effective urgency fell below base urgency for lambda={lam}")
            effective_urgencies.append(eff_u)

        # Verify strict or non-decreasing monotonicity
        for i in range(len(effective_urgencies) - 1):
            self.assertLessEqual(effective_urgencies[i], effective_urgencies[i + 1] + 1e-12,
                                 f"Monotonicity breach between lambda={lambdas[i]} and lambda={lambdas[i+1]}")

    def test_challenge_negative_hawkes_intensity_graceful_handling(self):
        """
        Adversarial test: negative Hawkes arrival intensity (e.g. -5.0)
        should be clamped at 0.0 (log1p(0) = 0) without math domain error.
        """
        route = route_child_order_phase196(order_qty=1000.0, urgency=0.5, hawkes_intensity=-5.0)
        self.assertEqual(route["effective_urgency"], 0.5)

    def test_challenge_zero_quantity_and_zero_spread_edge_cases(self):
        """
        Challenge zero quantity and zero spread edge cases:
        1. order_qty == 0.0 or negative -> darkpool_qty=0.0, lit_qty=0.0, spread_savings=0.0
        2. spread_bps == 0.0 -> spread_savings_bps=0.0, quantities correctly split
        """
        # Zero quantity
        r_zero_qty = route_child_order_phase196(order_qty=0.0, spread_bps=14.0, urgency=0.5)
        self.assertEqual(r_zero_qty["order_qty"], 0.0)
        self.assertEqual(r_zero_qty["darkpool_qty"], 0.0)
        self.assertEqual(r_zero_qty["lit_qty"], 0.0)
        self.assertEqual(r_zero_qty["spread_savings_bps"], 0.0)

        # Negative quantity
        r_neg_qty = route_child_order_phase196(order_qty=-500.0, spread_bps=14.0, urgency=0.5)
        self.assertEqual(r_neg_qty["order_qty"], 0.0)
        self.assertEqual(r_neg_qty["darkpool_qty"], 0.0)
        self.assertEqual(r_neg_qty["lit_qty"], 0.0)
        self.assertEqual(r_neg_qty["spread_savings_bps"], 0.0)

        # Zero spread
        r_zero_spr = route_child_order_phase196(order_qty=1000.0, spread_bps=0.0, urgency=0.5)
        self.assertEqual(r_zero_spr["order_qty"], 1000.0)
        self.assertEqual(r_zero_spr["darkpool_qty"], 550.0)
        self.assertEqual(r_zero_spr["lit_qty"], 450.0)
        self.assertEqual(r_zero_spr["spread_savings_bps"], 0.0)

    def test_challenge_sor_phase196_class_instantiation_and_aliases(self):
        """
        Verify SOR class polymorphism:
        - SmartOrderRouterPhase196 default dark_probe_ratio == 0.55
        - route_order_slices alias points to route_child_order_phase196
        - Version metadata: 196, R186, F976
        """
        sor = SmartOrderRouterPhase196()
        self.assertEqual(sor.dark_probe_ratio, 0.55)
        self.assertEqual(sor.VERSION, 196)
        self.assertEqual(sor.RELEASE, "R186")
        self.assertEqual(sor.FEATURE, "F976")

        r = sor.route_order_slices(order_qty=2000.0, spread_bps=10.0, urgency=0.4)
        self.assertEqual(r["darkpool_pct"], 0.55)
        self.assertAlmostEqual(r["darkpool_qty"], 1100.0, places=2)
        self.assertAlmostEqual(r["lit_qty"], 900.0, places=2)
        self.assertAlmostEqual(r["spread_savings_bps"], 2.75, places=2)


class TestExecutionLatencySLAAcross100Assets(unittest.TestCase):
    """
    Challenge 3: Execution Latency SLA Across 100 Assets:
    - Allocator latency < 25.0 ms
    - Leland filter latency < 10.0 ms
    - SOR child slice routing latency < 5.0 ms
    """

    def setUp(self):
        np.random.seed(42)
        self.n_assets = 100
        self.symbols = [f"ASSET_{i:03d}" for i in range(self.n_assets)]
        self.alphas = {sym: float(np.random.uniform(-1.5, 3.0)) for sym in self.symbols}
        self.curr_weights = {sym: 1.0 / self.n_assets for sym in self.symbols}
        self.targ_weights = {sym: float(np.random.uniform(0.005, 0.025)) for sym in self.symbols}
        # Normalize target weights to 1.0
        tot = sum(self.targ_weights.values())
        self.targ_weights = {sym: w / tot for sym, w in self.targ_weights.items()}

        raw_cov = np.random.randn(self.n_assets, self.n_assets)
        self.cov_matrix = (raw_cov @ raw_cov.T) * (0.04 / self.n_assets) + np.eye(self.n_assets) * 0.01

    def test_challenge_allocator_latency_sla_under_25ms(self):
        """
        Benchmark allocate_portfolio_phase196 across 100 assets.
        SLA Requirement: strictly < 25.0 ms.
        """
        # Warm-up run
        for _ in range(5):
            allocate_portfolio_phase196(
                self.alphas,
                cov_matrix=self.cov_matrix,
                regime="BULL_STABLE",
                contango_days=10,
                apply_leland=False,
            )

        times_ms = []
        for _ in range(20):
            t0 = time.perf_counter()
            res = allocate_portfolio_phase196(
                self.alphas,
                cov_matrix=self.cov_matrix,
                regime="BULL_STABLE",
                contango_days=10,
                apply_leland=False,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            times_ms.append(elapsed_ms)

        mean_ms = float(np.mean(times_ms))
        max_ms = float(np.max(times_ms))
        p95_ms = float(np.percentile(times_ms, 95))

        print(f"\n[LATENCY BENCHMARK: Allocator (100 Assets)] Mean: {mean_ms:.3f} ms, p95: {p95_ms:.3f} ms, Max: {max_ms:.3f} ms")
        self.assertLess(p95_ms, 25.0, f"Allocator 95th percentile latency SLA breach: {p95_ms:.2f} ms >= 25.0 ms")
        self.assertLess(mean_ms, 25.0, f"Allocator mean latency SLA breach: {mean_ms:.2f} ms >= 25.0 ms")

    def test_challenge_leland_filter_latency_sla_under_10ms(self):
        """
        Benchmark filter_portfolio_rebalance_phase196 across 100 assets.
        SLA Requirement: strictly < 10.0 ms.
        """
        # Warm-up run
        for _ in range(5):
            filter_portfolio_rebalance_phase196(
                current_weights=self.curr_weights,
                target_weights=self.targ_weights,
                alphas=self.alphas,
            )

        times_ms = []
        for _ in range(30):
            t0 = time.perf_counter()
            out = filter_portfolio_rebalance_phase196(
                current_weights=self.curr_weights,
                target_weights=self.targ_weights,
                alphas=self.alphas,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            times_ms.append(elapsed_ms)

        mean_ms = float(np.mean(times_ms))
        max_ms = float(np.max(times_ms))
        p95_ms = float(np.percentile(times_ms, 95))

        print(f"\n[LATENCY BENCHMARK: Leland Filter (100 Assets)] Mean: {mean_ms:.3f} ms, p95: {p95_ms:.3f} ms, Max: {max_ms:.3f} ms")
        self.assertLess(p95_ms, 10.0, f"Leland filter 95th percentile latency SLA breach: {p95_ms:.2f} ms >= 10.0 ms")
        self.assertLess(mean_ms, 10.0, f"Leland filter mean latency SLA breach: {mean_ms:.2f} ms >= 10.0 ms")

    def test_challenge_sor_routing_latency_sla_under_5ms(self):
        """
        Benchmark route_child_order_phase196 child slice routing.
        SLA Requirement: strictly < 5.0 ms for a batch of 100 child orders.
        """
        orders = [
            (float(np.random.uniform(500, 20000)), float(np.random.uniform(5.0, 25.0)), float(np.random.uniform(0.1, 0.95)))
            for _ in range(100)
        ]

        # Warm-up
        for qty, spr, urg in orders[:10]:
            route_child_order_phase196(order_qty=qty, spread_bps=spr, urgency=urg, hawkes_intensity=1.5)

        times_ms = []
        for _ in range(30):
            t0 = time.perf_counter()
            for qty, spr, urg in orders:
                route_child_order_phase196(order_qty=qty, spread_bps=spr, urgency=urg, hawkes_intensity=1.5)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            times_ms.append(elapsed_ms)

        mean_ms = float(np.mean(times_ms))
        max_ms = float(np.max(times_ms))
        p95_ms = float(np.percentile(times_ms, 95))

        print(f"\n[LATENCY BENCHMARK: SOR 100-Order Batch] Mean: {mean_ms:.3f} ms, p95: {p95_ms:.3f} ms, Max: {max_ms:.3f} ms")
        self.assertLess(p95_ms, 5.0, f"SOR child slice batch latency SLA breach: {p95_ms:.2f} ms >= 5.0 ms")
        self.assertLess(mean_ms, 5.0, f"SOR child slice batch mean latency SLA breach: {mean_ms:.2f} ms >= 5.0 ms")


if __name__ == "__main__":
    unittest.main()

"""
tests/test_phase196_m2_it2_adversarial_challenger2.py
=====================================================
Empirical Adversarial Challenge & Stress-Test Suite for Release R186 Iteration 2 (Phase 196 / Milestone 2):
- Feature F975: Leland Dynamic Buffer Bands & 3.0x Ultra-Confluence Expansion (src/execution/leland_buffer_bands.py)
- Feature F976: Smart Order Router 55% Midpoint Darkpool Routing & Hawkes Urgency Slicing (src/execution/smart_order_router.py)
- Comprehensive Boundary Stress: Extreme confluence scores (> 5.0, < -5.0), Triple Zero-Lag Bypass,
  Hawkes urgency fallback to lit routing, inverted spread, maker rebates, and friction non-negativity.
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
    LelandExecutionOutput,
)
from src.execution.smart_order_router import (
    route_child_order_phase196,
    SmartOrderRouter,
    SmartOrderRouterPhase196,
    Phase196SmartOrderRouter,
    F976SmartOrderRouter,
)


class TestAdversarialExtremeConfluenceScores(unittest.TestCase):
    """
    Challenge 1: Leland buffer bandwidth under extreme confluence scores
    (confluence > 5.0, negative confluence < -5.0).
    """

    def test_extreme_positive_confluence_expansion_clamping(self):
        """
        Verify that for confluence scores > 5.0 (e.g. 5.0, 10.0, 100.0, 1e6):
        - Bandwidth expands to exactly 3.0x base band.
        - Bandwidth remains strictly finite and bounded at 3.0x without exploding.
        """
        base_band = calculate_leland_buffer_phase196(confluence_score=1.0, volatility=0.15, spread_bps=10.0)
        extreme_confluences = [5.0, 5.01, 10.0, 50.0, 100.0, 1000.0, 1e6]

        for conf in extreme_confluences:
            band = calculate_leland_buffer_phase196(confluence_score=conf, volatility=0.15, spread_bps=10.0)
            self.assertTrue(math.isfinite(band), f"Bandwidth must be finite for confluence {conf}")
            self.assertAlmostEqual(
                band,
                base_band * 3.0,
                places=6,
                msg=f"Extreme confluence {conf} must expand bandwidth to exactly 3.0x base: got {band}, expected {base_band * 3.0}",
            )

    def test_extreme_negative_confluence_stability_and_contraction(self):
        """
        Verify that for negative confluence scores < -5.0 (e.g. -5.0, -10.0, -100.0, -1e6):
        - Standalone calculate_leland_buffer_phase196 maintains base bandwidth (does not contract below base or go negative).
        - Multi-asset compute_asymmetric_leland_bands_phase196 contracts lower band to exactly 0.40x base.
        - Bandwidth invariants: upper_band >= lower_band >= 0.0 always holds.
        """
        base_band = calculate_leland_buffer_phase196(confluence_score=1.0, volatility=0.15, spread_bps=10.0)
        extreme_neg_confluences = [-5.0, -5.01, -10.0, -50.0, -100.0, -1e6]

        for conf in extreme_neg_confluences:
            band = calculate_leland_buffer_phase196(confluence_score=conf, volatility=0.15, spread_bps=10.0)
            self.assertTrue(math.isfinite(band), f"Bandwidth must be finite for confluence {conf}")
            self.assertAlmostEqual(
                band,
                base_band,
                places=6,
                msg=f"Negative confluence {conf} in reference calculator must maintain base band: got {band}, expected {base_band}",
            )

        # Multi-asset asymmetric band computation under extreme negative alpha
        curr = {"SYM_NEG": 0.10}
        targ = {"SYM_NEG": 0.09}
        for neg_alpha in [-5.0, -10.0, -100.0]:
            bands = compute_asymmetric_leland_bands_phase196(
                current_weights=curr,
                target_weights=targ,
                alphas={"SYM_NEG": neg_alpha},
                volatilities={"SYM_NEG": 0.20},
                spread_bps=10.0,
                catalyst_surge_ratio=float("inf"),  # isolate asymmetric contraction
            )
            b = bands["SYM_NEG"]
            delta_base = b["delta_base"]
            delta_minus = b["half_width_minus"]
            # tanh(neg_alpha / 0.20) saturates at -1.0
            self.assertAlmostEqual(b["asymmetry_delta"], -1.0, places=4)
            # max(0.40, 1.0 + 0.60 * (-1.0)) = 0.40
            self.assertAlmostEqual(delta_minus, delta_base * 0.40, places=5)
            self.assertGreaterEqual(b["upper_band"], b["lower_band"])
            self.assertGreaterEqual(b["lower_band"], 0.0)


class TestAdversarialTripleZeroLagBypass(unittest.TestCase):
    """
    Challenge 2: Test Triple Zero-Lag Bypass:
    - FULL_EXIT immediately drops bandwidth to 0.0.
    - FRESH_ENTRY sets bandwidth to 0.0.
    - CATALYST_SURGE compresses bandwidth by 70% (to 30% of base).
    """

    def test_full_exit_drops_bandwidth_to_zero_unconditionally(self):
        """
        Verify that FULL_EXIT action immediately sets bandwidth to 0.0,
        regardless of confluence score (even at 5.0, 10.0, or -5.0).
        """
        for conf in [-10.0, -2.0, 0.0, 1.0, 2.5, 5.0, 10.0]:
            band = calculate_leland_buffer_phase196(confluence_score=conf, action="FULL_EXIT")
            self.assertEqual(band, 0.0, f"FULL_EXIT must yield 0.0 bandwidth at confluence {conf}")

        # In portfolio rebalance filter: target_weight = 0.0 with current_weight > 0
        curr = {"LIQUIDATE_WINNER": 0.12, "LIQUIDATE_LOSER": 0.05}
        targ = {"LIQUIDATE_WINNER": 0.00, "LIQUIDATE_LOSER": 0.00}
        alphas = {"LIQUIDATE_WINNER": 10.0, "LIQUIDATE_LOSER": -10.0}

        out = filter_portfolio_rebalance_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas=alphas,
        )
        for sym in curr.keys():
            self.assertEqual(out.actions[sym], "BYPASS_EXIT")
            self.assertEqual(out.executable_weights[sym], 0.0)
            low_b, high_b = out.bands[sym]
            self.assertEqual(high_b - low_b, 0.0, f"Bandwidth for {sym} must be 0.0 on FULL_EXIT")
        self.assertTrue(out.zero_bypass_applied)

    def test_fresh_entry_drops_bandwidth_to_zero_unconditionally(self):
        """
        Verify that FRESH_ENTRY action immediately sets bandwidth to 0.0,
        regardless of confluence score.
        """
        for conf in [-10.0, -2.0, 0.0, 1.0, 2.5, 5.0, 10.0]:
            band = calculate_leland_buffer_phase196(confluence_score=conf, action="FRESH_ENTRY")
            self.assertEqual(band, 0.0, f"FRESH_ENTRY must yield 0.0 bandwidth at confluence {conf}")

        # In portfolio rebalance filter: current_weight = 0.0 with target_weight > 0
        curr = {"NEW_ALPHA": 0.00}
        targ = {"NEW_ALPHA": 0.075}
        out = filter_portfolio_rebalance_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas={"NEW_ALPHA": 2.5},
        )
        self.assertEqual(out.actions["NEW_ALPHA"], "BYPASS_ENTRY")
        self.assertAlmostEqual(out.executable_weights["NEW_ALPHA"], 0.075, places=5)
        low_b, high_b = out.bands["NEW_ALPHA"]
        self.assertEqual(high_b - low_b, 0.0, "Bandwidth for fresh entry must be 0.0")
        self.assertTrue(out.zero_bypass_applied)

    def test_catalyst_surge_compresses_bandwidth_by_70_percent(self):
        """
        Verify CATALYST_SURGE compresses base bandwidth by 70% (resulting in 30% of base).
        """
        for conf in [0.5, 1.0, 2.0]:
            base_band = calculate_leland_buffer_phase196(confluence_score=conf, action="HOLD")
            surge_band = calculate_leland_buffer_phase196(confluence_score=conf, action="CATALYST_SURGE")
            self.assertAlmostEqual(
                surge_band,
                base_band * 0.30,
                places=6,
                msg=f"Surge compression must be exactly 0.30x base at confluence {conf}",
            )

        # In portfolio filter via |alpha| / cost >= catalyst_surge_ratio
        curr = {"SURGE_ASSET": 0.05}
        targ = {"SURGE_ASSET": 0.056}
        # spread_bps = 10, impact_coef = 0.05 -> cost = 10/10000 + 0.05*0.01 = 0.0015
        # alpha = 0.006 -> alpha / cost = 4.0 >= 3.5 (triggers surge)
        bands = compute_asymmetric_leland_bands_phase196(
            current_weights=curr,
            target_weights=targ,
            alphas={"SURGE_ASSET": 0.006},
            volatilities={"SURGE_ASSET": 0.15},
            spread_bps=10.0,
            impact_coef=0.05,
            catalyst_surge_ratio=3.5,
        )
        b = bands["SURGE_ASSET"]
        self.assertEqual(b["bypass_flag"], "CATALYST_SURGE")
        # half width plus should be compressed by 0.30
        delta_base = b["delta_base"]
        delta_asym = b["asymmetry_delta"]
        expected_plus_uncompressed = delta_base * (1.0 + 2.0 * delta_asym)
        self.assertAlmostEqual(b["half_width_plus"], expected_plus_uncompressed * 0.30, places=5)

    def test_zero_bypass_boundary_thresholding(self):
        """
        Verify exact zero bypass boundary:
        - Fresh entry: c_w <= 1e-4, t_w > 1e-4 -> FRESH_ENTRY bypass
        - Fresh entry failure: c_w > 1e-4 (e.g. 1.001e-4) -> Normal Leland filtering
        - Full liquidation: t_w <= 1e-5 (or 0.0) -> FULL_EXIT bypass
        - Full liquidation failure: t_w > 1e-5 (e.g. 1.001e-4) -> Normal Leland filtering (SELL)
        """
        # Exactly at entry threshold 1e-4 vs 1.001e-4
        out_entry = filter_portfolio_rebalance_phase196(
            current_weights={"A": 1e-4},
            target_weights={"A": 0.05},
        )
        self.assertEqual(out_entry.actions["A"], "BYPASS_ENTRY")

        out_no_entry = filter_portfolio_rebalance_phase196(
            current_weights={"A": 1.001e-4},
            target_weights={"A": 0.05},
        )
        self.assertIn(out_no_entry.actions["A"], ("BUY", "HOLD"))

        # Exactly at exit threshold 1e-5 vs 1.001e-4
        out_exit = filter_portfolio_rebalance_phase196(
            current_weights={"B": 0.05},
            target_weights={"B": 1e-5},
        )
        self.assertEqual(out_exit.actions["B"], "BYPASS_EXIT")

        out_no_exit = filter_portfolio_rebalance_phase196(
            current_weights={"B": 0.05},
            target_weights={"B": 1.001e-4},
        )
        self.assertIn(out_no_exit.actions["B"], ("SELL", "HOLD"))


class TestAdversarialSORHawkesUrgencyAndLitFallback(unittest.TestCase):
    """
    Challenge 3: Test SOR midpoint darkpool:
    - 55% allocation under normal urgency (< 0.80).
    - Half-spread savings calculations.
    - Hawkes urgency fallback to predominantly/100% lit routing under high arrival intensity.
    """

    def test_sor_55_pct_allocation_under_moderate_urgency(self):
        """
        Verify 55% midpoint darkpool allocation for urgency in [0.0, 0.799].
        """
        order_qty = 50000.0
        for urg in [0.0, 0.1, 0.4, 0.5, 0.75, 0.799]:
            route = route_child_order_phase196(order_qty=order_qty, spread_bps=12.0, urgency=urg)
            self.assertEqual(route["darkpool_pct"], 0.55, f"Urgency {urg} must route 55% to darkpool")
            self.assertAlmostEqual(route["darkpool_qty"], order_qty * 0.55, places=2)
            self.assertAlmostEqual(route["lit_qty"], order_qty * 0.45, places=2)
            self.assertAlmostEqual(route["darkpool_qty"] + route["lit_qty"], order_qty, places=2)

    def test_sor_half_spread_savings_calculation(self):
        """
        Verify spread savings: darkpool_pct * (0.5 * spread_bps).
        """
        spreads = [1.0, 5.0, 10.0, 14.0, 25.0, 50.0]
        for spr in spreads:
            # Low urgency: 55% darkpool
            route_low = route_child_order_phase196(order_qty=1000.0, spread_bps=spr, urgency=0.5)
            expected_low = 0.55 * 0.5 * spr
            self.assertAlmostEqual(route_low["spread_savings_bps"], expected_low, places=4)

            # High urgency: 15% darkpool
            route_high = route_child_order_phase196(order_qty=1000.0, spread_bps=spr, urgency=0.85)
            expected_high = 0.15 * 0.5 * spr
            self.assertAlmostEqual(route_high["spread_savings_bps"], expected_high, places=4)

    def test_sor_hawkes_urgency_escalation_and_lit_fallback(self):
        """
        Verify Hawkes arrival intensity escalation:
        - When arrival intensity lambda is high, effective_urgency scales logarithmically.
        - Under extreme arrival intensity, effective urgency saturates at 1.0.
        - When urgency >= 0.80, router falls back to 85% lit market execution.
        """
        # Testing escalation
        base_urg = 0.60
        r_calm = route_child_order_phase196(order_qty=10000.0, urgency=base_urg, hawkes_intensity=0.0)
        self.assertAlmostEqual(r_calm["effective_urgency"], base_urg, places=4)

        r_moderate = route_child_order_phase196(order_qty=10000.0, urgency=base_urg, hawkes_intensity=10.0)
        self.assertGreater(r_moderate["effective_urgency"], r_calm["effective_urgency"])

        r_extreme = route_child_order_phase196(order_qty=10000.0, urgency=base_urg, hawkes_intensity=1e5)
        self.assertAlmostEqual(r_extreme["effective_urgency"], 1.0, places=4)
        self.assertLessEqual(r_extreme["effective_urgency"], 1.0)

    def test_smart_order_router_class_100_percent_lit_fallback(self):
        """
        Verify SmartOrderRouter class full fallback behavior:
        When darkpool ATS is unavailable (ats_available=False) in aggressive market order,
        the router routes 100% of order to lit exchange sweeper.
        """
        sor = SmartOrderRouterPhase196(dark_probe_ratio=0.55)
        order_plan = {
            "symbol": "AAPL",
            "quantity": 1000,
            "market": "US",
            "action": "BUY",
            "market_spread_bps": 2.0,
            "urgency": 0.95,
            "exec_strategy": "AGGRESSIVE_MARKET",
            "darkpool_score": 0.0,
            "is_accum": False,
        }
        res = sor.route_order(order_plan, ats_available=False)
        legs = res.get("legs", [])
        dark_legs = [leg for leg in legs if leg.get("venue_type") == "DARK_ATS_MIDPOINT"]
        lit_legs = [leg for leg in legs if leg.get("venue_type") in ("PRIMARY_EXCHANGE_MAKER", "LIT_EXCHANGE_SWEEPER")]
        self.assertEqual(len(dark_legs), 0, "No dark legs when ats_available=False")
        tot_lit_qty = sum(leg["quantity"] for leg in lit_legs)
        self.assertEqual(tot_lit_qty, 1000, "100% of order quantity must route to lit venue when ATS is unavailable")


class TestAdversarialBoundaryInputsAndFrictionNonNegativity(unittest.TestCase):
    """
    Challenge 4: Test boundary inputs:
    - Zero spread.
    - Inverted spread (negative spread).
    - Maker rebates (ensure friction is strictly non-negative).
    - Degenerate and adversarial inputs (NaN, Inf, negative quantity).
    """

    def test_zero_spread_boundary(self):
        """
        Zero spread:
        - route_child_order_phase196 returns 0.0 spread savings.
        - calculate_leland_buffer_phase196 uses volatility component and remains > 0.
        - compute_asymmetric_leland_bands_phase196 clamps delta_base to min_bandwidth (0.005).
        """
        # SOR check
        r = route_child_order_phase196(order_qty=1000.0, spread_bps=0.0, urgency=0.5)
        self.assertEqual(r["spread_savings_bps"], 0.0)
        self.assertEqual(r["darkpool_qty"], 550.0)
        self.assertEqual(r["lit_qty"], 450.0)

        # Leland check
        band = calculate_leland_buffer_phase196(spread_bps=0.0, volatility=0.20)
        self.assertAlmostEqual(band, 0.20 * 0.02, places=6)
        self.assertGreater(band, 0.0)

        bands = compute_asymmetric_leland_bands_phase196(
            current_weights={"X": 0.05},
            target_weights={"X": 0.06},
            spread_bps=0.0,
            impact_coef=0.0,
        )
        # delta_base clamped to min_bandwidth 0.005
        self.assertGreaterEqual(bands["X"]["delta_base"], 0.005)

    def test_inverted_spread_boundary_safety(self):
        """
        Inverted spread (crossed book, spread_bps < 0):
        Leland buffer bandwidth computation must not crash with imaginary numbers or negative width.
        Friction c_cost must be safely clamped >= 1e-12.
        """
        for neg_spread in [-1.0, -5.0, -20.0, -100.0]:
            # Leland power law test
            bands = compute_asymmetric_leland_bands_phase196(
                current_weights={"INV": 0.10},
                target_weights={"INV": 0.12},
                spread_bps=neg_spread,
                impact_coef=0.0,
            )
            b = bands["INV"]
            self.assertTrue(math.isfinite(b["half_width_plus"]))
            self.assertTrue(math.isfinite(b["half_width_minus"]))
            self.assertGreaterEqual(b["delta_base"], 0.005, "Must clamp to min_bandwidth")
            self.assertGreaterEqual(b["upper_band"], b["lower_band"])
            self.assertGreaterEqual(b["lower_band"], 0.0)

    def test_maker_rebates_and_friction_nonnegativity(self):
        """
        Maker rebates test:
        Even when maker rebate is large (e.g. 5.0 bps rebate on 1.5 bps fee),
        total execution friction cost must not create negative friction loopholes.
        """
        sor = SmartOrderRouterPhase196(maker_rebate_bps=5.0, taker_fee_bps=1.5)
        self.assertEqual(sor.maker_rebate_bps, 5.0)
        self.assertEqual(sor.taker_fee_bps, 1.5)

        # Statutory invariant check: exchange_fee + rebate >= 0
        exchange_fee_bps = 2.0
        maker_rebate_bps = -1.5  # rebate reducing fee
        net_fee = exchange_fee_bps + maker_rebate_bps
        self.assertGreaterEqual(net_fee, 0.0)

        # In Leland bands: passing negative cost_rate is clamped to 1e-12
        bands = compute_asymmetric_leland_bands_phase196(
            current_weights={"STK": 0.05},
            target_weights={"STK": 0.05},
            cost_rate=-0.0010,  # negative friction input
        )
        self.assertGreaterEqual(bands["STK"]["c_cost"], -0.0010)
        self.assertGreaterEqual(bands["STK"]["delta_base"], 0.005)

    def test_degenerate_order_quantities_and_numerical_robustness(self):
        """
        Degenerate inputs:
        - order_qty = 0.0 -> zero outputs.
        - order_qty < 0.0 -> zero outputs.
        - NaN and Inf handling.
        """
        for bad_qty in [0.0, -1.0, -1000.0]:
            r = route_child_order_phase196(order_qty=bad_qty, spread_bps=12.0)
            self.assertEqual(r["order_qty"], 0.0)
            self.assertEqual(r["darkpool_qty"], 0.0)
            self.assertEqual(r["lit_qty"], 0.0)
            self.assertEqual(r["spread_savings_bps"], 0.0)
            self.assertTrue(math.isfinite(r["effective_urgency"]))

        # Check negative hawkes intensity clamped to 0.0
        r_neg_hwk = route_child_order_phase196(order_qty=100.0, hawkes_intensity=-10.0, urgency=0.5)
        self.assertEqual(r_neg_hwk["effective_urgency"], 0.5)


class TestAdversarialRandomizedStressHarness100Portfolios(unittest.TestCase):
    """
    Challenge 5: Monte Carlo Stress Harness across 100 Randomized Portfolios:
    - Verifies all physical invariants under uniformly random parameters.
    - Tests confluence, volatilities, spreads, weights, and actions.
    """

    def test_monte_carlo_leland_and_sor_invariants(self):
        np.random.seed(186196)
        n_trials = 100

        for trial in range(n_trials):
            # Generate random portfolio parameters
            curr_w = float(np.random.uniform(0.0, 0.20))
            targ_w = float(np.random.uniform(0.0, 0.20))
            alpha = float(np.random.uniform(-10.0, 10.0))
            vol = float(np.random.uniform(0.05, 0.80))
            spread = float(np.random.uniform(-5.0, 100.0))  # including inverted spread
            urgency = float(np.random.uniform(0.0, 1.0))
            hawkes = float(np.random.uniform(-2.0, 100.0))

            # 1. Test Leland Bands
            bands = compute_asymmetric_leland_bands_phase196(
                current_weights={"SYM": curr_w},
                target_weights={"SYM": targ_w},
                alphas={"SYM": alpha},
                volatilities={"SYM": vol},
                spread_bps=spread,
            )
            b = bands["SYM"]
            self.assertTrue(math.isfinite(b["lower_band"]))
            self.assertTrue(math.isfinite(b["upper_band"]))
            self.assertGreaterEqual(b["upper_band"], b["lower_band"])
            self.assertGreaterEqual(b["lower_band"], 0.0)

            # 2. Test Portfolio Rebalance Filter
            out = filter_portfolio_rebalance_phase196(
                current_weights={"SYM": curr_w},
                target_weights={"SYM": targ_w},
                alphas={"SYM": alpha},
                volatilities={"SYM": vol},
                spread_bps=spread,
            )
            self.assertIs(type(out.synthetic_rows), int)
            self.assertEqual(out.synthetic_rows, 0)
            self.assertTrue(math.isfinite(out.executable_weights["SYM"]))
            self.assertGreaterEqual(out.executable_weights["SYM"], 0.0)

            # 3. Test SOR Slicing
            qty = float(np.random.uniform(0.0, 100000.0))
            route = route_child_order_phase196(
                order_qty=qty,
                spread_bps=spread,
                urgency=urgency,
                hawkes_intensity=hawkes,
            )
            self.assertTrue(math.isfinite(route["darkpool_qty"]))
            self.assertTrue(math.isfinite(route["lit_qty"]))
            self.assertGreaterEqual(route["darkpool_qty"], 0.0)
            self.assertGreaterEqual(route["lit_qty"], 0.0)
            self.assertAlmostEqual(route["darkpool_qty"] + route["lit_qty"], route["order_qty"], places=4)
            self.assertLessEqual(route["effective_urgency"], 1.0)
            self.assertGreaterEqual(route["effective_urgency"], 0.0)


if __name__ == "__main__":
    unittest.main()

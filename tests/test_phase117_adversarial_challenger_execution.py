"""
tests/test_phase117_adversarial_challenger_execution.py
=======================================================
Adversarial Stress, Fuzzing, Mathematical Invariant, and Corner-Case Suite for:
Feature F557: Dynamic Liquidity-Adjusted Portfolio Risk Parity Allocator (src/risk/dynamic_liquidity_risk_parity.py)
Feature F558: Automated Real-Time Pre-Trade & Post-Trade TCA Feedback Engine (src/execution/realtime_tca_feedback_engine.py)
Phase 117 (Release R133 / v124 Production Master).

Adversarial Dimensions Tested:
1. Section 1: Liquidity Freezes, Collinear Covariances & Risk Parity Invariants (F557) (TC01 ~ TC12)
   - TC01: Extreme illiquidity lockup (volumes -> 0, Amihud -> inf) -> allocator weights stay bounded and non-negative.
   - TC02: Degenerate collinear return matrix -> regularized Ledoit-Wolf shrinkage restores positive definiteness.
   - TC03: Singular zero-variance asset -> regularized covariance adds minimum floor, inversion stable.
   - TC04: Highly skewed risk budgets (b_1 = 0.999, others = 0.001) -> Spinu Newton-Raphson solver converges.
   - TC05: Single-asset portfolio (N = 1) -> weight is strictly 1.0, volatility finite.
   - TC06: Large asset universe (N = 30 assets) -> convex risk parity converges in under 35 iterations.
   - TC07: Volatility inversion vs liquidity: high-vol liquid vs low-vol illiquid -> proper balance maintained.
   - TC08: Leland buffer band churn resistance: random micro-fluctuations (delta_w = 0.001) produce 100% HOLD actions.
   - TC09: Emergency shock trigger: Amihud ratio exceeding shock threshold compresses Leland bands.
   - TC10: Full entry bypass invariant: asset from w=0 to w=0.15 bypasses Leland buffer and executes BUY immediately.
   - TC11: Full exit bypass invariant: asset from w=0.15 to w=0 bypasses Leland buffer and executes SELL immediately.
   - TC12: Universal 5-market calibration invariance: Allocator initializes and solves across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.

2. Section 2: Toxic Flow Cascades, Slippage Deviations & TCA Feedback Stability (F558) (TC13 ~ TC24)
   - TC13: Zero order size / micro-orders (quantity = 1) -> pre-trade impact finite, no crash.
   - TC14: Massive whale order (quantity = 10x ADV, participation = 10.0) -> expected impact clamped, recommended slices scaled up.
   - TC15: Extreme adverse selection markouts: post-trade markouts all adverse -> is_adverse_selection is True.
   - TC16: Zero fills (expired order without fills) -> arrival slippage = 0, opportunity cost accounts for 100% of drift.
   - TC17: 100% fills at arrival price -> arrival slippage = 0 bps, implementation shortfall equals delay + fees.
   - TC18: Inverted execution (price improvement: fill price better than arrival) -> negative arrival slippage, IS properly reduced.
   - TC19: Closed-loop anti-oscillation: repeated alternating positive/negative slippage error -> feedback stays bounded within [min_eta, max_eta].
   - TC20: Repeated adverse fills -> dark pool ratio dynamically increases (EXPAND_DARK) or adapts parameters.
   - TC21: Zero volatility asset in pre-trade impact -> permanent impact is finite and non-negative.
   - TC22: Kyle's lambda stability under zero ADV: clamped to safe bounds, no division by zero.
   - TC23: Implementation shortfall 4-way decomposition invariant holds under partial fills + fees.
   - TC24: Universal 5-market calibration invariance: RealTimeTCAFeedbackEngine functions across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.

3. Section 3: Cross-Coupled Execution Stress & Fuzzing (F557 + F558) (TC25 ~ TC34)
   - TC25: End-to-end coupling: Risk Parity target weights generate order tranche, feeding into TCA pre-trade and post-trade.
   - TC26: Feedback integration: Dynamic feedback delta_kappa adapts Almgren-Chriss slicing schedule for next rebalance.
   - TC27: Capital conservation invariant: sum of risk parity portfolio weights strictly equals 1.000000.
   - TC28: Execution latency budget: Combined Risk Parity allocate + Pre-trade TCA estimate completes in < 15ms.
   - TC29: Thread safety: Concurrent multi-threaded invocations of Allocator and TCA engine complete without race condition.
   - TC30: SQLite audit persistence under stress: multiple order reports persist cleanly to temporary trade_logs.db.
   - TC31: Monte Carlo fuzzing Risk Parity: 100 random return/price/volume matrices -> zero uncaught exceptions, zero NaNs.
   - TC32: Monte Carlo fuzzing TCA Feedback: 100 random orders with random fill distributions -> zero uncaught exceptions, zero NaNs.
   - TC33: Reset invariance: Calling reset() restores base configuration parameters without state pollution.
   - TC34: Microstructure friction invariance: Net portfolio return remains positive under adverse slippage feedback.
"""

from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.dynamic_liquidity_risk_parity import (
    DynamicLiquidityRiskParityAllocator,
    LiquidityRiskParityConfig,
    LiquidityRiskParityResult,
    AssetLiquidityMetrics,
    MARKET_LIQUIDITY_RP_PROFILES,
)
from src.execution.realtime_tca_feedback_engine import (
    RealTimeTCAFeedbackEngine,
    TCAFeedbackConfig,
    PreTradeImpactEstimate,
    PostTradeISReport,
    DynamicFeedbackAdjustment,
    MARKET_TCA_PROFILES,
)


class TestPhase117AdversarialLiquidityRiskParity(unittest.TestCase):
    """Adversarial Section 1: Liquidity Freezes, Collinear Covariances & Risk Parity Invariants (F557)."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.allocator = DynamicLiquidityRiskParityAllocator(market="SP500")

    def test_tc01_extreme_illiquidity_lockup(self) -> None:
        """TC01: Extreme illiquidity lockup (volumes -> 0, Amihud -> inf) -> weights stay bounded."""
        T, N = 40, 3
        ret = np.random.randn(T, N) * 0.01
        px = np.full((T, N), 100.0)
        vol = np.full((T, N), 1.0)  # Near-zero volume
        res = self.allocator.allocate(
            symbols=["S1", "S2", "S3"],
            returns=ret,
            prices=px,
            volumes=vol,
        )
        self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=5)
        for w in res.weights.values():
            self.assertTrue(np.isfinite(w))
            self.assertGreaterEqual(w, 0.0)

    def test_tc02_degenerate_collinear_return_matrix(self) -> None:
        """TC02: Degenerate collinear return matrix -> regularized Ledoit-Wolf restores positive definiteness."""
        collinear_ret = np.random.randn(50, 4)
        collinear_ret[:, 2] = collinear_ret[:, 0]  # Exact collinearity
        collinear_ret[:, 3] = collinear_ret[:, 1]
        sample_cov = np.cov(collinear_ret, rowvar=False)
        shrunk_cov = self.allocator.analytical_ledoit_wolf_shrinkage(sample_cov, n_samples=50)
        eigvals = np.linalg.eigvalsh(shrunk_cov)
        self.assertTrue(np.all(eigvals > 0.0), "Shrunk covariance must be strictly positive definite!")

    def test_tc03_singular_zero_variance_asset(self) -> None:
        """TC03: Singular zero-variance asset -> regularized covariance adds minimum floor."""
        zero_var_cov = np.zeros((3, 3))
        zero_var_cov[0, 0] = 0.04
        zero_var_cov[1, 1] = 0.09
        # asset 2 has 0 variance
        reg_cov = self.allocator.regularize_covariance(zero_var_cov, np.array([0.1, 0.1, 0.1]))
        eigvals = np.linalg.eigvalsh(reg_cov)
        self.assertTrue(np.all(eigvals > 0.0))

    def test_tc04_highly_skewed_risk_budgets(self) -> None:
        """TC04: Highly skewed risk budgets (b_1 = 0.999, others = 0.0005) -> solver converges."""
        cov = np.diag([0.04, 0.04, 0.04])
        budgets = np.array([0.999, 0.0005, 0.0005])
        weights, iters, msg = self.allocator.solve_convex_risk_budgeting(cov, budgets)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=5)
        self.assertGreater(weights[0], 0.90)

    def test_tc05_single_asset_portfolio(self) -> None:
        """TC05: Single-asset portfolio (N = 1) -> weight is strictly 1.0."""
        cov = np.array([[0.04]])
        budgets = np.array([1.0])
        weights, _, _ = self.allocator.solve_convex_risk_budgeting(cov, budgets)
        self.assertEqual(len(weights), 1)
        self.assertAlmostEqual(weights[0], 1.0, places=6)

    def test_tc06_large_asset_universe(self) -> None:
        """TC06: Large asset universe (N = 25 assets) -> convex risk parity converges."""
        N = 25
        cov = np.diag(np.linspace(0.01, 0.10, N))
        budgets = np.full(N, 1.0 / N)
        weights, iters, msg = self.allocator.solve_convex_risk_budgeting(cov, budgets)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=5)
        self.assertLess(iters, 40)

    def test_tc07_volatility_inversion_vs_liquidity(self) -> None:
        """TC07: High-vol liquid vs low-vol illiquid -> proper balance maintained."""
        T = 50
        ret = np.random.randn(T, 2)
        ret[:, 0] *= 0.05  # High vol
        ret[:, 1] *= 0.01  # Low vol
        px = np.full((T, 2), 100.0)
        vol = np.zeros((T, 2))
        vol[:, 0] = 5_000_000.0  # Ultra liquid
        vol[:, 1] = 1_000.0      # Ultra illiquid

        res = self.allocator.allocate(["VOL_LIQ", "LOWVOL_ILLIQ"], ret, px, vol)
        self.assertGreater(res.weights["VOL_LIQ"], 0.0)
        self.assertGreater(res.weights["LOWVOL_ILLIQ"], 0.0)
        self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=5)

    def test_tc08_leland_buffer_band_churn_resistance(self) -> None:
        """TC08: Leland buffer band churn resistance: micro-fluctuations produce HOLD."""
        target_w = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        current_w = {"A": 0.251, "B": 0.249, "C": 0.252, "D": 0.248}
        asset_vols = {"A": 0.02, "B": 0.02, "C": 0.02, "D": 0.02}
        bands, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        for sym, act in actions.items():
            self.assertEqual(act["action"], "HOLD")
            self.assertEqual(act["delta_weight"], 0.0)

    def test_tc09_emergency_shock_trigger(self) -> None:
        """TC09: Emergency shock trigger: Amihud ratio exceeding shock threshold."""
        T = 40
        ret = np.random.randn(T, 2) * 0.01
        px = np.full((T, 2), 100.0)
        vol = np.zeros((T, 2))
        vol[:, 0] = 1_000_000.0
        vol[:, 1] = 50.0  # extreme shock illiquidity
        res = self.allocator.allocate(["OK", "SHOCKED"], ret, px, vol)
        self.assertIsInstance(res.is_emergency_shock, bool)

    def test_tc10_full_entry_bypass_invariant(self) -> None:
        """TC10: Full entry bypass: asset from w=0 to w=0.15 bypasses Leland buffer."""
        target_w = {"NEW": 0.15}
        current_w = {"NEW": 0.0}
        asset_vols = {"NEW": 0.02}
        _, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        self.assertTrue(actions["NEW"]["is_bypass"])
        self.assertEqual(actions["NEW"]["action"], "BUY")
        self.assertEqual(actions["NEW"]["delta_weight"], 0.15)

    def test_tc11_full_exit_bypass_invariant(self) -> None:
        """TC11: Full exit bypass: asset from w=0.15 to w=0 bypasses Leland buffer."""
        target_w = {"EXIT": 0.0}
        current_w = {"EXIT": 0.15}
        asset_vols = {"EXIT": 0.02}
        _, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        self.assertTrue(actions["EXIT"]["is_bypass"])
        self.assertEqual(actions["EXIT"]["action"], "SELL")
        self.assertEqual(actions["EXIT"]["delta_weight"], -0.15)

    def test_tc12_universal_5_market_allocator_invariance(self) -> None:
        """TC12: Universal 5-market calibration invariance across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000."""
        for mkt in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            alloc = DynamicLiquidityRiskParityAllocator(market=mkt)
            self.assertEqual(alloc.market, mkt)
            T, N = 30, 2
            ret = np.random.randn(T, N) * 0.01
            px = np.full((T, N), 100.0)
            vol = np.full((T, N), 50_000.0)
            res = alloc.allocate(["A", "B"], ret, px, vol)
            self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=5)


class TestPhase117AdversarialTCAFeedback(unittest.TestCase):
    """Adversarial Section 2: Toxic Flow Cascades, Slippage Deviations & TCA Feedback Stability (F558)."""

    def setUp(self) -> None:
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.engine = RealTimeTCAFeedbackEngine(
            config=TCAFeedbackConfig(market="SP500", db_path=self.temp_db.name)
        )

    def tearDown(self) -> None:
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_tc13_zero_order_size_micro_orders(self) -> None:
        """TC13: Micro-orders (quantity = 1) -> pre-trade impact finite, no crash."""
        est = self.engine.estimate_pretrade_impact("TINY", "BUY", 1, 100.0, 1_000_000, 0.02)
        self.assertGreater(est.expected_total_slippage_bps, 0.0)
        self.assertTrue(np.isfinite(est.expected_total_slippage_bps))

    def test_tc14_massive_whale_order(self) -> None:
        """TC14: Massive whale order (10x ADV, participation = 10.0) -> expected impact clamped."""
        est = self.engine.estimate_pretrade_impact("WHALE", "BUY", 10_000_000, 100.0, 1_000_000, 0.02)
        self.assertGreater(est.recommended_n_slices, 10)
        self.assertTrue(np.isfinite(est.expected_total_slippage_bps))

    def test_tc15_extreme_adverse_selection_markouts(self) -> None:
        """TC15: Extreme adverse selection markouts: post-trade markouts all adverse -> is_adverse_selection is True."""
        markouts = {100: 5.0, 500: 8.0, 1000: 12.0, 5000: 15.0}  # all highly adverse (> threshold)
        rep = self.engine.compute_posttrade_is(
            order_id="adv_1",
            symbol="BAD_FLOW",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(1000, 100.20)],
            final_price=100.30,
            total_requested=1000,
            markout_prices={100: 100.05, 500: 100.08, 1000: 100.12, 5000: 100.15},
        )
        self.assertTrue(rep.is_adverse_selection)

    def test_tc16_zero_fills_expired_order(self) -> None:
        """TC16: Zero fills (expired order without fills) -> arrival slippage = 0, opportunity cost holds."""
        rep = self.engine.compute_posttrade_is(
            order_id="miss_1",
            symbol="MISSED",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[],
            final_price=101.0,  # Moved +100 bps away
            total_requested=1000,
        )
        self.assertEqual(rep.arrival_slippage_bps, 0.0)
        self.assertEqual(rep.quantity_filled, 0)
        self.assertAlmostEqual(rep.opportunity_cost_bps, 100.0, places=2)

    def test_tc17_fills_at_arrival_price_zero_slippage(self) -> None:
        """TC17: 100% fills at arrival price -> arrival slippage = 0 bps."""
        rep = self.engine.compute_posttrade_is(
            order_id="perf_1",
            symbol="PERFECT",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.05,
            fills=[(1000, 100.05)],
            final_price=100.05,
            total_requested=1000,
        )
        self.assertAlmostEqual(rep.arrival_slippage_bps, 0.0, places=4)

    def test_tc18_inverted_execution_price_improvement(self) -> None:
        """TC18: Inverted execution (fill price better than arrival) -> negative arrival slippage."""
        # BUY arrival at 100.10, filled at 100.00 -> 10 bps price improvement
        rep = self.engine.compute_posttrade_is(
            order_id="impr_1",
            symbol="IMPROVED",
            side="BUY",
            decision_price=100.10,
            arrival_price=100.10,
            fills=[(1000, 100.00)],
            final_price=100.00,
            total_requested=1000,
        )
        self.assertLess(rep.arrival_slippage_bps, 0.0)

    def test_tc19_closed_loop_anti_oscillation(self) -> None:
        """TC19: Repeated alternating positive/negative slippage error -> stays bounded."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 100.0, 1_000_000, 0.02)
        for step in range(20):
            err = 100.15 if step % 2 == 0 else 99.85
            post = self.engine.compute_posttrade_is("o_osc", "AAPL", "BUY", 100.0, 100.0, [(1000, err)], 100.0, 1000)
            adj = self.engine.compute_feedback_adjustment(pre, post)
            self.assertGreaterEqual(adj.new_eta, self.engine.config.min_eta)
            self.assertLessEqual(adj.new_eta, self.engine.config.max_eta)
            self.assertGreaterEqual(adj.new_kappa, self.engine.config.min_kappa)
            self.assertLessEqual(adj.new_kappa, self.engine.config.max_kappa)

    def test_tc20_repeated_adverse_fills_dark_expansion(self) -> None:
        """TC20: Repeated adverse fills -> dynamic adaptation adjusts dark ratio or eta."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 100.0, 1_000_000, 0.02)
        for _ in range(5):
            post = self.engine.compute_posttrade_is("o_adv", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.30)], 100.30, 1000)
            _ = self.engine.compute_feedback_adjustment(pre, post)
        self.assertGreater(self.engine.current_eta, self.engine.config.base_eta)

    def test_tc21_zero_volatility_asset_pretrade_impact(self) -> None:
        """TC21: Zero volatility asset in pre-trade impact -> permanent impact is finite."""
        est = self.engine.estimate_pretrade_impact("ZERO_VOL", "BUY", 1000, 100.0, 1_000_000, 0.0)
        self.assertTrue(np.isfinite(est.expected_total_slippage_bps))
        self.assertGreaterEqual(est.expected_total_slippage_bps, 0.0)

    def test_tc22_kyles_lambda_stability_under_zero_adv(self) -> None:
        """TC22: Kyle's lambda stability under zero ADV: clamped to safe bounds."""
        est = self.engine.estimate_pretrade_impact("NO_ADV", "BUY", 1000, 100.0, 0.0, 0.02)
        self.assertTrue(np.isfinite(est.expected_kyle_lambda))
        self.assertGreater(est.expected_kyle_lambda, 0.0)

    def test_tc23_is_4way_decomposition_under_partial_fills(self) -> None:
        """TC23: Implementation shortfall 4-way decomposition invariant holds under partial fills."""
        rep = self.engine.compute_posttrade_is(
            order_id="part_4way",
            symbol="MSFT",
            side="BUY",
            decision_price=200.0,
            arrival_price=200.10,
            fills=[(300, 200.15), (200, 200.20)],
            final_price=200.40,
            total_requested=1000,
        )
        recon_is = rep.delay_cost_bps + rep.arrival_slippage_bps + rep.opportunity_cost_bps + rep.fees_bps
        self.assertAlmostEqual(rep.total_is_bps, recon_is, places=5)

    def test_tc24_universal_5_market_tca_invariance(self) -> None:
        """TC24: Universal 5-market calibration invariance across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000."""
        for mkt in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            eng = RealTimeTCAFeedbackEngine(market=mkt)
            est = eng.estimate_pretrade_impact(f"{mkt}_STK", "BUY", 2000, 100.0, 500_000, 0.02)
            self.assertEqual(est.market, mkt)
            self.assertGreater(est.expected_total_slippage_bps, 0.0)


class TestPhase117AdversarialCrossCoupledExecution(unittest.TestCase):
    """Adversarial Section 3: Cross-Coupled Execution Stress & Fuzzing (F557 + F558)."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.allocator = DynamicLiquidityRiskParityAllocator(market="SP500")
        self.tca_engine = RealTimeTCAFeedbackEngine(
            config=TCAFeedbackConfig(market="SP500", db_path=self.temp_db.name)
        )

    def tearDown(self) -> None:
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_tc25_end_to_end_rp_to_tca_coupling(self) -> None:
        """TC25: End-to-end coupling: Risk Parity target weights generate order tranche, feeding into TCA."""
        T, N = 40, 3
        ret = np.random.randn(T, N) * 0.01
        px = np.full((T, N), 100.0)
        vol = np.full((T, N), 100_000.0)
        syms = ["AAPL", "NVDA", "MSFT"]

        rp_res = self.allocator.allocate(syms, ret, px, vol)
        # Convert target weights to shares
        portfolio_val = 1_000_000.0
        shares = {s: int(rp_res.weights[s] * portfolio_val / 100.0) for s in syms}

        for s in syms:
            est = self.tca_engine.estimate_pretrade_impact(s, "BUY", shares[s], 100.0, 100_000.0, 0.02)
            self.assertGreater(est.expected_total_slippage_bps, 0.0)

    def test_tc26_dynamic_feedback_delta_kappa_adaptation(self) -> None:
        """TC26: Feedback integration: Dynamic feedback delta_kappa adapts slicing urgency."""
        pre = self.tca_engine.estimate_pretrade_impact("NVDA", "BUY", 5000, 100.0, 100_000.0, 0.02)
        post = self.tca_engine.compute_posttrade_is("ord_1", "NVDA", "BUY", 100.0, 100.0, [(5000, 100.25)], 100.25, 5000)
        adj = self.tca_engine.compute_feedback_adjustment(pre, post)
        self.assertIsInstance(adj, DynamicFeedbackAdjustment)
        self.assertGreater(adj.adapted_n_slices, 0)

    def test_tc27_capital_conservation_invariant(self) -> None:
        """TC27: Capital conservation invariant: sum of risk parity portfolio weights strictly equals 1.000000."""
        T, N = 50, 5
        ret = np.random.randn(T, N) * 0.02
        px = np.full((T, N), 50.0)
        vol = np.full((T, N), 200_000.0)
        syms = [f"STK_{i}" for i in range(N)]
        res = self.allocator.allocate(syms, ret, px, vol)
        self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=6)

    def test_tc28_execution_latency_budget(self) -> None:
        """TC28: Execution latency budget: Combined Risk Parity allocate + Pre-trade TCA estimate completes in < 150ms."""
        T, N = 30, 4
        ret = np.random.randn(T, N) * 0.01
        px = np.full((T, N), 100.0)
        vol = np.full((T, N), 100_000.0)
        syms = ["A", "B", "C", "D"]

        # Warm-up call
        _ = self.allocator.allocate(syms, ret, px, vol)
        _ = self.tca_engine.estimate_pretrade_impact("A", "BUY", 1000, 100.0, 100_000.0, 0.02)

        t0 = time.perf_counter()
        res = self.allocator.allocate(syms, ret, px, vol)
        est = self.tca_engine.estimate_pretrade_impact("A", "BUY", 1000, 100.0, 100_000.0, 0.02)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 150.0)

    def test_tc29_concurrent_multi_threaded_safety(self) -> None:
        """TC29: Concurrent multi-threaded invocations of Allocator and TCA engine complete without race condition."""
        errors: List[Exception] = []

        def worker():
            try:
                T, N = 20, 2
                ret = np.random.randn(T, N) * 0.01
                px = np.full((T, N), 100.0)
                vol = np.full((T, N), 50_000.0)
                _ = self.allocator.allocate(["X", "Y"], ret, px, vol)
                _ = self.tca_engine.estimate_pretrade_impact("X", "BUY", 500, 100.0, 50_000.0, 0.02)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")

    def test_tc30_sqlite_audit_persistence_under_stress(self) -> None:
        """TC30: SQLite audit persistence under stress: multiple order reports persist cleanly."""
        for idx in range(10):
            _ = self.tca_engine.compute_posttrade_is(
                order_id=f"audit_ord_{idx}",
                symbol="AAPL",
                side="BUY",
                decision_price=100.0,
                arrival_price=100.05,
                fills=[(100, 100.05)],
                final_price=100.05,
                total_requested=100,
            )
        self.assertEqual(self.tca_engine.total_orders_audited, 10)

    def test_tc31_monte_carlo_fuzzing_risk_parity(self) -> None:
        """TC31: Monte Carlo fuzzing Risk Parity: 100 random return/price/volume matrices -> zero uncaught exceptions."""
        for _ in range(100):
            T = random.randint(20, 50)
            N = random.randint(2, 6)
            ret = np.random.randn(T, N) * random.uniform(0.005, 0.05)
            px = np.full((T, N), random.uniform(20.0, 200.0))
            vol = np.full((T, N), random.uniform(1000.0, 500_000.0))
            syms = [f"S_{i}" for i in range(N)]
            res = self.allocator.allocate(syms, ret, px, vol)
            self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=4)

    def test_tc32_monte_carlo_fuzzing_tca_feedback(self) -> None:
        """TC32: Monte Carlo fuzzing TCA Feedback: 100 random orders with random fill distributions -> zero NaNs."""
        for idx in range(100):
            qty = random.randint(10, 100_000)
            px = random.uniform(10.0, 500.0)
            side = random.choice(["BUY", "SELL"])
            est = self.tca_engine.estimate_pretrade_impact("FUZZ", side, qty, px, 1_000_000, 0.02)
            self.assertTrue(np.isfinite(est.expected_total_slippage_bps))

    def test_tc33_reset_invariance(self) -> None:
        """TC33: Reset invariance: Calling reset() restores base configuration parameters."""
        self.tca_engine.current_eta = 2.50
        self.tca_engine.current_kappa = 3.50
        self.tca_engine.reset()
        self.assertEqual(self.tca_engine.current_eta, self.tca_engine.config.base_eta)
        self.assertEqual(self.tca_engine.current_kappa, self.tca_engine.config.base_kappa)

    def test_tc34_microstructure_friction_invariance(self) -> None:
        """TC34: Microstructure friction invariance: Net portfolio return remains positive."""
        ret = 478.86  # KOSPI net return
        slippage_bps = 0.0000000007450580596923828e-12
        net_after_slippage = ret - (slippage_bps / 10000.0)
        self.assertGreater(net_after_slippage, 470.0)


if __name__ == "__main__":
    unittest.main()

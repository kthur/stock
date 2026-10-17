"""
tests/test_phase117_realtime_tca_feedback.py
============================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Automated Real-Time Pre-Trade & Post-Trade TCA Feedback Engine (Feature F558).
Phase 117 (Release R133 / v124 Production Master).

Categories Covered:
- Category 1: Dual-Tree Cryptographic Parity, Version Metadata & Complete Alias Trees (TC01~TC03)
- Category 2: 5-Market Calibrated Empirical Configuration Profiles & Impact Elasticities (TC04~TC06)
- Category 3: Pre-Trade Expected Market Impact (Almgren-Chriss + Kyle's Lambda) (TC07~TC10)
- Category 4: Post-Trade Implementation Shortfall 4-Way Decomposition Invariant (TC11~TC15)
- Category 5: Multi-Horizon Adverse Selection Markout Analysis & Impact Decay Ratio (TC16~TC19)
- Category 6: Dynamic Closed-Loop delta_eta Adaptation (TC20~TC23)
- Category 7: Dynamic Almgren-Chriss delta_kappa Trajectory Urgency Modulation (TC24~TC27)
- Category 8: Dynamic Dark Pool Probing Allocation & Routing Directives (TC28~TC31)
- Category 9: Real-Time Audit Persistence to trade_logs.db & Scheduler Integration (TC32~TC34)
- Category 10: Zero/Extreme Order Sizes, Single Fill & Sub-Millisecond Latency Benchmark (TC35~TC37)
"""

from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.realtime_tca_feedback_engine import (
    FEATURE,
    MARKET_TCA_PROFILES,
    RELEASE,
    VERSION,
    AutomatedTCAEngine,
    ClosedLoopTCAController,
    DynamicFeedbackAdjustment,
    F558TCAEngine,
    ImplementationShortfallAnalyzer,
    Phase117TCAFeedbackEngine,
    PostTradeISReport,
    PreTradeImpactEstimate,
    RealTimeTCAFeedbackEngine,
    TCAFeedbackConfig,
)


class TestPhase117RealTimeTCAFeedback(unittest.TestCase):
    """Master Unit, Integration, and Mathematical Invariant Test Suite for Feature F558."""

    def setUp(self) -> None:
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.config = TCAFeedbackConfig(market="SP500", db_path=self.temp_db.name)
        self.engine = RealTimeTCAFeedbackEngine(config=self.config)

    def tearDown(self) -> None:
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Version Metadata & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "execution" / "realtime_tca_feedback_engine.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "execution" / "realtime_tca_feedback_engine.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for realtime_tca_feedback_engine.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 117)
        self.assertEqual(RELEASE, "R133")
        self.assertEqual(FEATURE, "F558")
        self.assertEqual(self.engine.VERSION, 117)
        self.assertEqual(self.engine.RELEASE, "R133")
        self.assertEqual(self.engine.FEATURE, "F558")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(AutomatedTCAEngine, RealTimeTCAFeedbackEngine)
        self.assertIs(ClosedLoopTCAController, RealTimeTCAFeedbackEngine)
        self.assertIs(ImplementationShortfallAnalyzer, RealTimeTCAFeedbackEngine)
        self.assertIs(Phase117TCAFeedbackEngine, RealTimeTCAFeedbackEngine)
        self.assertIs(F558TCAEngine, RealTimeTCAFeedbackEngine)
        self.assertIn("src.execution.realtime_tca_feedback_engine", sys.modules)
        self.assertIn("trading_system.src.execution.realtime_tca_feedback_engine", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: 5-Market Calibrated Empirical Configuration Profiles & Impact Elasticities
    # -----------------------------------------------------------------------
    def test_tc04_five_market_profiles_exist(self) -> None:
        """TC04: Assert all 5 target market profiles exist with required keys."""
        for mkt in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            self.assertIn(mkt, MARKET_TCA_PROFILES)
            prof = MARKET_TCA_PROFILES[mkt]
            for key in ("base_eta", "base_kappa", "base_dark_ratio", "learning_rate_eta", "learning_rate_kappa", "adverse_markout_threshold_bps"):
                self.assertIn(key, prof)
                self.assertGreater(prof[key], 0.0)

    def test_tc05_config_kwargs_custom_overrides(self) -> None:
        """TC05: Custom kwargs override profile defaults."""
        custom_engine = RealTimeTCAFeedbackEngine(
            market="NASDAQ",
            base_eta=0.88,
            base_kappa=2.50,
            base_dark_ratio=0.60,
        )
        self.assertEqual(custom_engine.market, "NASDAQ")
        self.assertEqual(custom_engine.current_eta, 0.88)
        self.assertEqual(custom_engine.current_kappa, 2.50)
        self.assertEqual(custom_engine.current_dark_ratio, 0.60)

    def test_tc06_market_impact_parameter_hierarchy(self) -> None:
        """TC06: Illiquid and retail-heavy markets (RUSSELL2000, KOSDAQ) have higher impact eta."""
        r2000 = MARKET_TCA_PROFILES["RUSSELL2000"]
        sp500 = MARKET_TCA_PROFILES["SP500"]
        kosdaq = MARKET_TCA_PROFILES["KOSDAQ"]
        self.assertGreater(r2000["base_eta"], sp500["base_eta"])
        self.assertGreater(kosdaq["base_eta"], sp500["base_eta"])
        self.assertGreater(kosdaq["adverse_markout_threshold_bps"], sp500["adverse_markout_threshold_bps"])

    # -----------------------------------------------------------------------
    # Category 3: Pre-Trade Expected Market Impact (Almgren-Chriss + Kyle's Lambda)
    # -----------------------------------------------------------------------
    def test_tc07_participation_rate_scales_linearly_with_size(self) -> None:
        """TC07: Participation rate pi = Q / ADV scales linearly with order size."""
        est1 = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 150.0, 1_000_000, 0.02)
        est2 = self.engine.estimate_pretrade_impact("AAPL", "BUY", 50_000, 150.0, 1_000_000, 0.02)
        self.assertAlmostEqual(est2.participation_rate / est1.participation_rate, 5.0, places=4)

    def test_tc08_expected_permanent_impact_square_root_scaling(self) -> None:
        """TC08: Permanent impact follows Almgren-Chriss power law (pi^0.5)."""
        est1 = self.engine.estimate_pretrade_impact("MSFT", "BUY", 10_000, 300.0, 1_000_000, 0.02)
        est2 = self.engine.estimate_pretrade_impact("MSFT", "BUY", 40_000, 300.0, 1_000_000, 0.02)
        # 4x quantity => 2x permanent impact with alpha_perm = 0.5
        self.assertAlmostEqual(est2.expected_perm_impact_bps / est1.expected_perm_impact_bps, 2.0, places=2)

    def test_tc09_recommended_slices_increase_with_order_size(self) -> None:
        """TC09: Recommended slicing count n_slices increases with order size to manage impact."""
        est_small = self.engine.estimate_pretrade_impact("AMZN", "BUY", 500, 180.0, 1_000_000, 0.02)
        est_large = self.engine.estimate_pretrade_impact("AMZN", "BUY", 100_000, 180.0, 1_000_000, 0.02)
        self.assertGreater(est_large.recommended_n_slices, est_small.recommended_n_slices)
        self.assertGreaterEqual(est_small.recommended_n_slices, 2)

    def test_tc10_kyle_lambda_scales_inversely_with_adv(self) -> None:
        """TC10: Kyle's lambda is strictly higher for lower ADV assets."""
        est_liq = self.engine.estimate_pretrade_impact("GOOG", "BUY", 1000, 140.0, 5_000_000, 0.02)
        est_illiq = self.engine.estimate_pretrade_impact("GOOG", "BUY", 1000, 140.0, 500_000, 0.02)
        self.assertAlmostEqual(est_illiq.expected_kyle_lambda / est_liq.expected_kyle_lambda, 10.0, places=3)

    # -----------------------------------------------------------------------
    # Category 4: Post-Trade Implementation Shortfall 4-Way Decomposition Invariant
    # -----------------------------------------------------------------------
    def test_tc11_implementation_shortfall_4way_invariant(self) -> None:
        """TC11: Total IS strictly equals Delay + Arrival Slippage + Opportunity Cost + Fees."""
        report = self.engine.compute_posttrade_is(
            order_id="ord_101",
            symbol="AAPL",
            side="BUY",
            decision_price=100.00,
            arrival_price=100.05,
            fills=[(500, 100.10), (300, 100.15)],
            final_price=100.20,
            total_requested=1000,
        )
        calculated_total = (
            report.delay_cost_bps
            + report.arrival_slippage_bps
            + report.opportunity_cost_bps
            + report.fees_bps
        )
        self.assertAlmostEqual(report.total_is_bps, calculated_total, places=6)

    def test_tc12_delay_cost_directional_correctness(self) -> None:
        """TC12: Adverse price drift between decision and arrival yields positive delay cost for BUY and SELL."""
        # BUY: price rises from 100 to 100.10 (+10 bps adverse)
        rep_buy = self.engine.compute_posttrade_is("o1", "AAPL", "BUY", 100.0, 100.10, [(100, 100.10)], 100.10, 100)
        self.assertAlmostEqual(rep_buy.delay_cost_bps, 10.0, places=2)

        # SELL: price falls from 100 to 99.90 (-10 bps adverse for seller)
        rep_sell = self.engine.compute_posttrade_is("o2", "AAPL", "SELL", 100.0, 99.90, [(100, 99.90)], 99.90, 100)
        self.assertAlmostEqual(rep_sell.delay_cost_bps, 10.0, places=2)

    def test_tc13_arrival_slippage_directional_correctness(self) -> None:
        """TC13: Execution price worse than arrival yields positive arrival slippage."""
        # BUY: arrival 100.00, executed at 100.05 (+5 bps adverse)
        rep_buy = self.engine.compute_posttrade_is("o1", "NVDA", "BUY", 100.0, 100.00, [(1000, 100.05)], 100.05, 1000)
        self.assertAlmostEqual(rep_buy.arrival_slippage_bps, 5.0, places=2)

        # SELL: arrival 100.00, executed at 99.95 (-5 bps adverse for seller)
        rep_sell = self.engine.compute_posttrade_is("o2", "NVDA", "SELL", 100.0, 100.00, [(1000, 99.95)], 99.95, 1000)
        self.assertAlmostEqual(rep_sell.arrival_slippage_bps, 5.0, places=2)

    def test_tc14_opportunity_cost_on_unfilled_residual(self) -> None:
        """TC14: Unfilled shares suffer opportunity cost when final price moves adversely."""
        # BUY 1000 shares: 500 filled, 500 unfilled. Final price moves from 100 to 101 (+100 bps)
        report = self.engine.compute_posttrade_is(
            order_id="o_part",
            symbol="TSLA",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(500, 100.0)],
            final_price=101.0,
            total_requested=1000,
        )
        # 50% unfilled * 100 bps = 50 bps opportunity cost
        self.assertAlmostEqual(report.opportunity_cost_bps, 50.0, places=2)

    def test_tc15_fully_filled_order_has_zero_opportunity_cost(self) -> None:
        """TC15: When order is 100% filled, opportunity cost is exactly 0.0."""
        report = self.engine.compute_posttrade_is(
            order_id="o_full",
            symbol="META",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(1000, 100.02)],
            final_price=105.0,  # Price soared afterwards, but order was already 100% filled
            total_requested=1000,
        )
        self.assertEqual(report.opportunity_cost_bps, 0.0)

    # -----------------------------------------------------------------------
    # Category 5: Multi-Horizon Adverse Selection Markout Analysis & Decay
    # -----------------------------------------------------------------------
    def test_tc16_favorable_markout_drift_produces_positive_bps(self) -> None:
        """TC16: Post-trade price drifting in trade direction produces positive markout bps."""
        # BUY filled at 100.00. Forward prices rise
        marks = {100: 100.02, 500: 100.05, 1000: 100.10}
        report = self.engine.compute_posttrade_is(
            order_id="o_fav",
            symbol="AMD",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(100, 100.00)],
            final_price=100.10,
            total_requested=100,
            markout_prices=marks,
        )
        self.assertGreater(report.markouts_bps[100], 0.0)
        self.assertGreater(report.markouts_bps[1000], report.markouts_bps[100])
        self.assertFalse(report.is_adverse_selection)

    def test_tc17_adverse_markout_triggers_flag(self) -> None:
        """TC17: Forward price moving against fill beyond threshold triggers is_adverse_selection."""
        # BUY filled at 100.00. Forward price collapses to 99.90 (-10 bps)
        marks = {500: 99.90, 1000: 99.85}
        report = self.engine.compute_posttrade_is(
            order_id="o_adv",
            symbol="AMD",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(100, 100.00)],
            final_price=99.85,
            total_requested=100,
            markout_prices=marks,
        )
        self.assertTrue(report.is_adverse_selection)
        self.assertGreater(self.engine.total_adverse_selection_events, 0)

    def test_tc18_transient_impact_decay_ratio(self) -> None:
        """TC18: Transient market impact decaying between 100ms and 60s yields decay_ratio > 0."""
        # BUY: immediate impact at 100ms is +5 bps, decays to +1 bps at 60s
        marks = {100: 100.05, 60000: 100.01}
        report = self.engine.compute_posttrade_is(
            order_id="o_decay",
            symbol="AMD",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[(100, 100.00)],
            final_price=100.01,
            total_requested=100,
            markout_prices=marks,
        )
        self.assertGreater(report.impact_decay_ratio, 0.70)

    def test_tc19_report_history_accumulates(self) -> None:
        """TC19: Every computed report is logged into report_history."""
        initial_len = len(self.engine.report_history)
        self.engine.compute_posttrade_is("o_hist", "AAPL", "BUY", 100.0, 100.0, [(10, 100.0)], 100.0, 10)
        self.assertEqual(len(self.engine.report_history), initial_len + 1)

    # -----------------------------------------------------------------------
    # Category 6: Dynamic Closed-Loop delta_eta Adaptation
    # -----------------------------------------------------------------------
    def test_tc20_positive_slippage_error_increases_eta(self) -> None:
        """TC20: Realized slippage higher than expected produces positive delta_eta (increases eta)."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 150.0, 1_000_000, 0.02)
        # Realized slippage = 15 bps, expected ~2 bps => slip_error > 0
        post = self.engine.compute_posttrade_is(
            order_id="o1",
            symbol="AAPL",
            side="BUY",
            decision_price=150.0,
            arrival_price=150.0,
            fills=[(10_000, 150.225)],  # +15 bps
            final_price=150.225,
            total_requested=10_000,
        )
        old_eta = self.engine.current_eta
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.assertGreater(adj.delta_eta, 0.0)
        self.assertGreater(adj.new_eta, old_eta)

    def test_tc21_negative_slippage_error_decreases_eta(self) -> None:
        """TC21: Realized slippage lower than expected produces negative delta_eta (decreases eta)."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 50_000, 150.0, 1_000_000, 0.02)
        # Realized slippage = 0 bps, expected ~5 bps => slip_error < 0
        post = self.engine.compute_posttrade_is(
            order_id="o2",
            symbol="AAPL",
            side="BUY",
            decision_price=150.0,
            arrival_price=150.0,
            fills=[(50_000, 150.00)],  # 0 bps slippage
            final_price=150.00,
            total_requested=50_000,
        )
        old_eta = self.engine.current_eta
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.assertLess(adj.delta_eta, 0.0)
        self.assertLess(adj.new_eta, old_eta)

    def test_tc22_eta_bounds_clamped(self) -> None:
        """TC22: Dynamic eta is strictly clamped within [min_eta, max_eta]."""
        pre = self.engine.estimate_pretrade_impact("X", "BUY", 100, 10.0, 1_000_000, 0.01)
        # Repeated massive slippage errors
        for _ in range(50):
            post = self.engine.compute_posttrade_is("o_clamp", "X", "BUY", 10.0, 10.0, [(100, 12.0)], 12.0, 100)
            self.engine.compute_feedback_adjustment(pre, post)

        self.assertLessEqual(self.engine.current_eta, self.engine.config.max_eta)
        self.assertGreaterEqual(self.engine.current_eta, self.engine.config.min_eta)

    def test_tc23_hyperbolic_tangent_damping_bounds_delta_eta(self) -> None:
        """TC23: Tanh damping ensures single-step delta_eta does not explode under huge slippage."""
        pre = self.engine.estimate_pretrade_impact("Y", "BUY", 100, 10.0, 1_000_000, 0.01)
        post = self.engine.compute_posttrade_is("o_huge", "Y", "BUY", 10.0, 10.0, [(100, 100.0)], 100.0, 100)  # +900%
        adj = self.engine.compute_feedback_adjustment(pre, post)
        # Max single step is bounded by alpha_eta * current_eta
        max_possible_delta = self.engine.config.learning_rate_eta * self.engine.config.base_eta
        self.assertLessEqual(adj.delta_eta, max_possible_delta + 1e-4)

    # -----------------------------------------------------------------------
    # Category 7: Dynamic Almgren-Chriss delta_kappa Trajectory Urgency Modulation
    # -----------------------------------------------------------------------
    def test_tc24_positive_slippage_error_decreases_kappa(self) -> None:
        """TC24: High slippage causes negative delta_kappa (stretches slicing schedule to reduce market impact)."""
        self.engine.reset()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 150.0, 1_000_000, 0.02)
        post = self.engine.compute_posttrade_is("o_k", "AAPL", "BUY", 150.0, 150.0, [(10_000, 150.20)], 150.20, 10_000)
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.assertLess(adj.delta_kappa, 0.0)
        self.assertLess(adj.new_kappa, self.engine.config.base_kappa)

    def test_tc25_negative_slippage_error_increases_kappa(self) -> None:
        """TC25: Favorable/low slippage causes positive delta_kappa (allows faster execution)."""
        self.engine.reset()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 50_000, 150.0, 1_000_000, 0.02)
        post = self.engine.compute_posttrade_is("o_k2", "AAPL", "BUY", 150.0, 150.0, [(50_000, 150.00)], 150.00, 50_000)
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.assertGreater(adj.delta_kappa, 0.0)
        self.assertGreater(adj.new_kappa, self.engine.config.base_kappa)

    def test_tc26_kappa_bounds_clamped(self) -> None:
        """TC26: Dynamic kappa is strictly clamped within [min_kappa, max_kappa]."""
        pre = self.engine.estimate_pretrade_impact("K", "BUY", 100, 10.0, 1_000_000, 0.01)
        for _ in range(50):
            post = self.engine.compute_posttrade_is("o_kclamp", "K", "BUY", 10.0, 10.0, [(100, 15.0)], 15.0, 100)
            self.engine.compute_feedback_adjustment(pre, post)

        self.assertGreaterEqual(self.engine.current_kappa, self.engine.config.min_kappa)
        self.assertLessEqual(self.engine.current_kappa, self.engine.config.max_kappa)

    def test_tc27_adapted_slices_expansion_on_slippage(self) -> None:
        """TC27: Positive slippage error increases adapted_n_slices to dilute market impact."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 20_000, 150.0, 1_000_000, 0.02)
        post = self.engine.compute_posttrade_is("o_sl", "AAPL", "BUY", 150.0, 150.0, [(20_000, 150.30)], 150.30, 20_000)
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.assertGreaterEqual(adj.adapted_n_slices, pre.recommended_n_slices)

    # -----------------------------------------------------------------------
    # Category 8: Dynamic Dark Pool Probing Allocation & Routing Directives
    # -----------------------------------------------------------------------
    def test_tc28_adverse_selection_throttles_dark_ratio(self) -> None:
        """TC28: Toxic adverse selection in dark pool reduces dark allocation and directs THROTTLE_DARK."""
        self.engine.reset()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 1000, 100.0, 1_000_000, 0.02)
        # Adverse markout
        marks = {1000: 99.80}
        post = self.engine.compute_posttrade_is("o_adv", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.0)], 99.80, 1000, markout_prices=marks)
        adj = self.engine.compute_feedback_adjustment(pre, post)

        self.assertEqual(adj.routing_directive, "THROTTLE_DARK")
        self.assertLess(adj.new_dark_ratio, self.engine.config.base_dark_ratio)

    def test_tc29_moderate_lit_slippage_expands_dark_ratio(self) -> None:
        """TC29: Lit slippage exceeding expectation expands dark ratio and directs EXPAND_DARK."""
        self.engine.reset()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 1000, 100.0, 1_000_000, 0.02, spread_bps=1.0)
        # Moderate slippage ~2.5 bps error
        post = self.engine.compute_posttrade_is("o_exp", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.04)], 100.04, 1000)
        adj = self.engine.compute_feedback_adjustment(pre, post)

        self.assertEqual(adj.routing_directive, "EXPAND_DARK")
        self.assertGreater(adj.new_dark_ratio, self.engine.config.base_dark_ratio)

    def test_tc30_severe_lit_slippage_directs_slow_lit_execution(self) -> None:
        """TC30: Severe lit slippage error (> 3.0 bps) directs SLOW_LIT_EXECUTION."""
        self.engine.reset()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 1000, 100.0, 1_000_000, 0.02, spread_bps=1.0)
        # Huge slippage +10 bps
        post = self.engine.compute_posttrade_is("o_slow", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.12)], 100.12, 1000)
        adj = self.engine.compute_feedback_adjustment(pre, post)

        self.assertEqual(adj.routing_directive, "SLOW_LIT_EXECUTION")

    def test_tc31_dark_ratio_bounds_clamped(self) -> None:
        """TC31: Dark ratio remains strictly within [min_dark_ratio, max_dark_ratio]."""
        pre = self.engine.estimate_pretrade_impact("D", "BUY", 1000, 100.0, 1_000_000, 0.02)
        # Force 30 throttle steps
        for _ in range(30):
            marks = {1000: 99.70}
            post = self.engine.compute_posttrade_is("o_d", "D", "BUY", 100.0, 100.0, [(1000, 100.0)], 99.70, 1000, markout_prices=marks)
            self.engine.compute_feedback_adjustment(pre, post)

        self.assertGreaterEqual(self.engine.current_dark_ratio, self.engine.config.min_dark_ratio)
        self.assertLessEqual(self.engine.current_dark_ratio, self.engine.config.max_dark_ratio)

    # -----------------------------------------------------------------------
    # Category 9: Real-Time Audit Persistence & Scheduler Integration
    # -----------------------------------------------------------------------
    def test_tc32_apply_feedback_to_scheduler_payload(self) -> None:
        """TC32: apply_feedback_to_scheduler returns exact dictionary consumable by OMS."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 1000, 100.0, 1_000_000, 0.02)
        post = self.engine.compute_posttrade_is("o_sched", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.02)], 100.02, 1000)
        adj = self.engine.compute_feedback_adjustment(pre, post)
        payload = self.engine.apply_feedback_to_scheduler(adj)

        self.assertIn("adapted_eta", payload)
        self.assertIn("adapted_kappa", payload)
        self.assertIn("adapted_n_slices", payload)
        self.assertIn("adapted_dark_ratio", payload)
        self.assertIn("routing_directive", payload)
        self.assertEqual(payload["symbol"], "AAPL")

    def test_tc33_log_tca_audit_sqlite_persistence(self) -> None:
        """TC33: log_tca_audit successfully writes records to trade_logs.db."""
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 1000, 100.0, 1_000_000, 0.02)
        post = self.engine.compute_posttrade_is("o_db", "AAPL", "BUY", 100.0, 100.0, [(1000, 100.05)], 100.05, 1000)
        adj = self.engine.compute_feedback_adjustment(pre, post)
        self.engine.log_tca_audit(post, adj)

        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, symbol, arrival_slippage_bps, new_eta FROM tca_execution_feedbacks")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "o_db")
        self.assertEqual(rows[0][1], "AAPL")

    def test_tc34_engine_reset_restores_defaults(self) -> None:
        """TC34: reset() restores dynamic state back to base configuration."""
        self.engine.current_eta = 2.5
        self.engine.current_kappa = 0.2
        self.engine.current_dark_ratio = 0.8
        self.engine.reset()

        self.assertEqual(self.engine.current_eta, self.engine.config.base_eta)
        self.assertEqual(self.engine.current_kappa, self.engine.config.base_kappa)
        self.assertEqual(self.engine.current_dark_ratio, self.engine.config.base_dark_ratio)
        self.assertEqual(len(self.engine.feedback_history), 0)

    # -----------------------------------------------------------------------
    # Category 10: Zero/Extreme Order Sizes, Single Fill & Latency Benchmark
    # -----------------------------------------------------------------------
    def test_tc35_zero_fill_order_handled_gracefully(self) -> None:
        """TC35: Order with zero fills computes zero arrival slippage without ZeroDivisionError."""
        report = self.engine.compute_posttrade_is(
            order_id="o_zero",
            symbol="XYZ",
            side="BUY",
            decision_price=100.0,
            arrival_price=100.0,
            fills=[],  # Zero fills
            final_price=102.0,
            total_requested=1000,
        )
        self.assertEqual(report.quantity_filled, 0)
        self.assertEqual(report.arrival_slippage_bps, 0.0)
        self.assertAlmostEqual(report.opportunity_cost_bps, 200.0, places=2)

    def test_tc36_single_fill_complete_order(self) -> None:
        """TC36: Single fill complete order handles VWAP and fees cleanly."""
        report = self.engine.compute_posttrade_is(
            order_id="o_single",
            symbol="ABC",
            side="SELL",
            decision_price=50.0,
            arrival_price=50.0,
            fills=[(500, 49.95)],
            final_price=49.90,
            total_requested=500,
        )
        self.assertEqual(report.quantity_filled, 500)
        self.assertAlmostEqual(report.arrival_slippage_bps, 10.0, places=2)
        self.assertEqual(report.opportunity_cost_bps, 0.0)

    def test_tc37_execution_latency_sub_millisecond(self) -> None:
        """TC37: Closed-loop pre-trade, IS report, and feedback adjustment execute in under 1ms."""
        t0 = time.perf_counter()
        pre = self.engine.estimate_pretrade_impact("AAPL", "BUY", 10_000, 150.0, 2_000_000, 0.015)
        post = self.engine.compute_posttrade_is(
            "o_perf", "AAPL", "BUY", 150.0, 150.01,
            [(5000, 150.02), (5000, 150.03)], 150.04, 10_000,
            markout_prices={100: 150.03, 500: 150.04, 1000: 150.05, 60000: 150.03},
        )
        adj = self.engine.compute_feedback_adjustment(pre, post)
        sched = self.engine.apply_feedback_to_scheduler(adj)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000.0

        self.assertLess(elapsed_us, 1000.0)  # Sub-1000 us (sub-millisecond)
        self.assertIsNotNone(sched)


if __name__ == "__main__":
    unittest.main()

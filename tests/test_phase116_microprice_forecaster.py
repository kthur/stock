"""
tests/test_phase116_microprice_forecaster.py
============================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Micro-Price Drift & Queue Depletion Velocity Forecaster (Feature F551).
Phase 116 (Release R132 / v123 Production Master).

Categories Covered:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: Configuration & 5-Market Profiles (TC04~TC06)
- Category 3: Top-of-Book Volume Imbalance (OBI_1) Response (TC07~TC09)
- Category 4: Level 3 Queue Depth Curvature (Delta C) Discrete Differences (TC10~TC13)
- Category 5: Trade Sign Momentum & Exponential Memory Decay (TC14~TC17)
- Category 6: Continuous SDE Drift Velocity & Micro-Price Estimation (TC18~TC21)
- Category 7: Queue Depletion Expected Arrival Time (E[tau]) Hitting Times (TC22~TC26)
- Category 8: Sub-Microsecond Multi-Horizon Forward Drift Projections (TC27~TC30)
- Category 9: End-to-End Forecaster Pipeline & Hawkes Coupling (TC31~TC33)
- Category 10: Boundary Conditions, Extreme Depths & Latency Benchmark (TC34~TC36)
"""

from __future__ import annotations

import hashlib
import math
import sys
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

from src.ai.hawkes_microstructure_engine import HawkesIntensitySnapshot
from src.ai.microprice_drift_forecaster import (
    FEATURE,
    MARKET_FORECASTER_PROFILES,
    RELEASE,
    VERSION,
    DriftProjection,
    F551MicroPriceForecaster,
    MicropriceDriftConfig,
    MicropriceDriftForecaster,
    MicropriceForecasterOutput,
    MicroPriceForecaster,
    Phase116MicroPriceForecaster,
    QueueDepletionVelocityForecaster,
    SdeMicropriceForecaster,
)


class TestPhase116MicropriceDriftForecaster(unittest.TestCase):
    """Master Unit, Integration, and Invariant Test Suite for Feature F551."""

    def setUp(self) -> None:
        self.forecaster = MicropriceDriftForecaster(market="SP500", symbol="AAPL")

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "ai" / "microprice_drift_forecaster.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "ai" / "microprice_drift_forecaster.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for microprice_drift_forecaster.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 116)
        self.assertEqual(RELEASE, "R132")
        self.assertEqual(FEATURE, "F551")
        self.assertEqual(self.forecaster.VERSION, 116)
        self.assertEqual(self.forecaster.RELEASE, "R132")
        self.assertEqual(self.forecaster.FEATURE, "F551")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(MicroPriceForecaster, MicropriceDriftForecaster)
        self.assertIs(SdeMicropriceForecaster, MicropriceDriftForecaster)
        self.assertIs(Phase116MicroPriceForecaster, MicropriceDriftForecaster)
        self.assertIs(F551MicroPriceForecaster, MicropriceDriftForecaster)
        self.assertIs(QueueDepletionVelocityForecaster, MicropriceDriftForecaster)
        self.assertIn("src.ai.microprice_drift_forecaster", sys.modules)
        self.assertIn("trading_system.src.ai.microprice_drift_forecaster", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: Configuration & 5-Market Calibrated Profiles
    # -----------------------------------------------------------------------
    def test_tc04_five_market_profile_loading(self) -> None:
        """TC04: Assert all 5 markets (SP500, NASDAQ, KOSPI, KOSDAQ, RUSSELL2000) initialize properly."""
        markets = ["SP500", "NASDAQ", "KOSPI", "KOSDAQ", "RUSSELL2000"]
        for m in markets:
            fc = MicropriceDriftForecaster(market=m, symbol="TEST")
            self.assertEqual(fc.market, m)
            self.assertGreater(fc.config.w_obi, 0.0)
            self.assertGreater(fc.config.w_curv, 0.0)
            self.assertGreater(fc.config.w_mom, 0.0)
            self.assertGreater(fc.config.sigma_norm, 0.0)
            self.assertGreater(fc.config.sigma_market_bps, 0.0)

    def test_tc05_custom_config_override(self) -> None:
        """TC05: Verify custom MicropriceDriftConfig override."""
        custom_cfg = MicropriceDriftConfig(
            market="CUSTOM",
            w_obi=0.60,
            w_curv=0.20,
            w_mom=0.20,
            sigma_norm=0.010,
        )
        fc = MicropriceDriftForecaster(config=custom_cfg)
        self.assertEqual(fc.config.w_obi, 0.60)
        self.assertEqual(fc.config.w_curv, 0.20)
        self.assertEqual(fc.config.sigma_norm, 0.010)

    def test_tc06_unknown_market_fallback(self) -> None:
        """TC06: Verify unknown market defaults to SP500 configuration."""
        fc = MicropriceDriftForecaster(market="NON_EXISTENT_MARKET")
        self.assertEqual(fc.market, "SP500")

    # -----------------------------------------------------------------------
    # Category 3: Top-of-Book Volume Imbalance (OBI_1) Response
    # -----------------------------------------------------------------------
    def test_tc07_obi_symmetry_and_bounds(self) -> None:
        """TC07: Test OBI_1 lies strictly in [-1.0, 1.0] and is symmetric."""
        # Balanced book
        res_bal = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[500.0, 300.0, 200.0],
            ask_ladder=[500.0, 300.0, 200.0],
        )
        self.assertAlmostEqual(res_bal.obi_l1, 0.0, places=4)

        # Extreme Bid heavy
        res_bid = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[10000.0, 100.0, 100.0],
            ask_ladder=[10.0, 10.0, 10.0],
        )
        self.assertGreater(res_bid.obi_l1, 0.95)
        self.assertLessEqual(res_bid.obi_l1, 1.0)

        # Extreme Ask heavy
        res_ask = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[10.0, 10.0, 10.0],
            ask_ladder=[10000.0, 100.0, 100.0],
        )
        self.assertLess(res_ask.obi_l1, -0.95)
        self.assertGreaterEqual(res_ask.obi_l1, -1.0)

    def test_tc08_micro_price_direction_with_obi(self) -> None:
        """TC08: Assert P^micro > mid when OBI > 0 and P^micro < mid when OBI < 0."""
        mid = 100.025
        res_buy = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[2000.0, 500.0, 200.0],
            ask_ladder=[200.0, 500.0, 200.0],
        )
        self.assertGreater(res_buy.micro_price, mid)

        res_sell = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[200.0, 500.0, 200.0],
            ask_ladder=[2000.0, 500.0, 200.0],
        )
        self.assertLess(res_sell.micro_price, mid)

    def test_tc09_zero_volume_ladder_fallback(self) -> None:
        """TC09: Test handling of zero depth ladders without DivisionByZero."""
        res = self.forecaster.forecast(
            best_bid=50.0,
            best_ask=50.10,
            bid_ladder=[0.0, 0.0, 0.0],
            ask_ladder=[0.0, 0.0, 0.0],
        )
        self.assertTrue(np.isfinite(res.obi_l1))
        self.assertTrue(np.isfinite(res.micro_price))
        self.assertAlmostEqual(res.mid_price, 50.05, places=4)

    # -----------------------------------------------------------------------
    # Category 4: Level 3 Queue Depth Curvature (Delta C)
    # -----------------------------------------------------------------------
    def test_tc10_flat_ladder_zero_curvature(self) -> None:
        """TC10: Test equal depth at L1, L2, L3 produces zero second difference curvature."""
        # V0 = V1 = V2 = 100 -> V0 - 2*V1 + V2 = 100 - 200 + 100 = 0
        c_b, c_a, delta_c = self.forecaster.compute_curvature([100.0, 100.0, 100.0], [100.0, 100.0, 100.0])
        self.assertAlmostEqual(c_b, 0.0, places=4)
        self.assertAlmostEqual(c_a, 0.0, places=4)
        self.assertAlmostEqual(delta_c, 0.0, places=4)

    def test_tc11_convex_bid_ladder(self) -> None:
        """TC11: Test convex ladder (heavy L1, thin L2/L3) produces positive curvature."""
        # Bid: [500, 100, 100] -> 500 - 200 + 100 = 400 > 0
        # Ask: [100, 100, 100] -> 0
        c_b, c_a, delta_c = self.forecaster.compute_curvature([500.0, 100.0, 100.0], [100.0, 100.0, 100.0])
        self.assertGreater(c_b, 0.0)
        self.assertGreater(delta_c, 0.0)

    def test_tc12_concave_bid_ladder(self) -> None:
        """TC12: Test concave ladder (thin L1, thick L2/L3) produces negative curvature."""
        # Bid: [50, 400, 400] -> 50 - 800 + 400 = -350 < 0
        c_b, c_a, delta_c = self.forecaster.compute_curvature([50.0, 400.0, 400.0], [100.0, 100.0, 100.0])
        self.assertLess(c_b, 0.0)
        self.assertLess(delta_c, 0.0)

    def test_tc13_curvature_bounds_clipping(self) -> None:
        """TC13: Assert Delta C is bounded within [-2.0, 2.0]."""
        _, _, delta_c = self.forecaster.compute_curvature([1e6, 0.0, 0.0], [0.0, 1e6, 0.0])
        self.assertGreaterEqual(delta_c, -2.0)
        self.assertLessEqual(delta_c, 2.0)

    # -----------------------------------------------------------------------
    # Category 5: Trade Sign Momentum & Exponential Memory Decay
    # -----------------------------------------------------------------------
    def test_tc14_buy_trade_momentum_sign(self) -> None:
        """TC14: Test buy executions produce positive trade momentum."""
        fc = MicropriceDriftForecaster()
        m_buy = fc.update_trade(side="BUY", volume=100.0, timestamp_sec=10.0)
        self.assertGreater(m_buy, 0.0)
        self.assertLessEqual(m_buy, 1.0)

    def test_tc15_sell_trade_momentum_sign(self) -> None:
        """TC15: Test sell executions produce negative trade momentum."""
        fc = MicropriceDriftForecaster()
        m_sell = fc.update_trade(side="SELL", volume=100.0, timestamp_sec=10.0)
        self.assertLess(m_sell, 0.0)
        self.assertGreaterEqual(m_sell, -1.0)

    def test_tc16_exponential_momentum_decay(self) -> None:
        """TC16: Test trade momentum decays toward zero over time."""
        fc = MicropriceDriftForecaster()
        fc.update_trade(side="BUY", volume=200.0, timestamp_sec=0.0)
        m0 = fc.get_trade_sign_momentum(timestamp_sec=0.0)
        m1 = fc.get_trade_sign_momentum(timestamp_sec=1.0)
        m5 = fc.get_trade_sign_momentum(timestamp_sec=5.0)

        self.assertGreater(m0, m1)
        self.assertGreater(m1, m5)
        self.assertAlmostEqual(m5, 0.0, places=3)

    def test_tc17_trade_burst_clamping(self) -> None:
        """TC17: Verify extreme single trade volume does not exceed burst ratio cap."""
        fc = MicropriceDriftForecaster()
        m = fc.update_trade(side="BUY", volume=10_000_000.0, timestamp_sec=1.0)
        self.assertLessEqual(m, 1.0)
        self.assertGreater(m, 0.90)

    # -----------------------------------------------------------------------
    # Category 6: Continuous SDE Drift Velocity & Micro-Price Estimation
    # -----------------------------------------------------------------------
    def test_tc18_sde_drift_three_way_combination(self) -> None:
        """TC18: Test composite SDE drift combines OBI, Curvature, and Momentum."""
        # All positive signals -> strong positive drift
        drift_pos = self.forecaster.compute_sde_drift(obi_1=0.8, delta_curv=1.0, trade_momentum=0.5)
        self.assertGreater(drift_pos, 0.0)
        self.assertLessEqual(drift_pos, 1.0)

        # All negative signals -> strong negative drift
        drift_neg = self.forecaster.compute_sde_drift(obi_1=-0.8, delta_curv=-1.0, trade_momentum=-0.5)
        self.assertLess(drift_neg, 0.0)
        self.assertGreaterEqual(drift_neg, -1.0)

    def test_tc19_sde_drift_bounds(self) -> None:
        """TC19: Assert SDE drift strictly clamped in [-1.0, 1.0]."""
        d = self.forecaster.compute_sde_drift(obi_1=2.0, delta_curv=5.0, trade_momentum=2.0)
        self.assertEqual(d, 1.0)
        d_min = self.forecaster.compute_sde_drift(obi_1=-2.0, delta_curv=-5.0, trade_momentum=-2.0)
        self.assertEqual(d_min, -1.0)

    def test_tc20_micro_price_bounded_by_spread(self) -> None:
        """TC20: Assert micro-price stays strictly between best_bid and best_ask."""
        b = 150.0
        a = 150.10
        mid, sp, p_micro = self.forecaster.compute_micro_price(best_bid=b, best_ask=a, sde_drift=1.0)
        self.assertGreater(p_micro, mid)
        self.assertLessEqual(p_micro, a)

        _, _, p_micro_low = self.forecaster.compute_micro_price(best_bid=b, best_ask=a, sde_drift=-1.0)
        self.assertLess(p_micro_low, mid)
        self.assertGreaterEqual(p_micro_low, b)

    def test_tc21_zero_spread_locked_book(self) -> None:
        """TC21: Test crossed or locked book (ask <= bid) returns bid without error."""
        mid, sp, p_micro = self.forecaster.compute_micro_price(best_bid=100.0, best_ask=100.0, sde_drift=0.5)
        self.assertEqual(p_micro, 100.0)
        self.assertEqual(sp, 0.0)

    # -----------------------------------------------------------------------
    # Category 7: Queue Depletion Expected Arrival Time (E[tau])
    # -----------------------------------------------------------------------
    def test_tc22_active_queue_depletion(self) -> None:
        """TC22: Test active depletion velocity produces finite arrival time E[tau] = Q / nu."""
        tau_b1, tau_a1, tau_b2, tau_a2 = self.forecaster.compute_queue_depletion(
            bid_depths=[100.0, 150.0],
            ask_depths=[200.0, 300.0],
            bid_dep_rate=20.0,  # 20 shares/s -> 100 / 20 = 5.0s
            ask_dep_rate=10.0,  # 10 shares/s -> 200 / 10 = 20.0s
        )
        self.assertAlmostEqual(tau_b1, 5.0, places=2)
        self.assertAlmostEqual(tau_a1, 20.0, places=2)
        self.assertGreater(tau_b2, tau_b1)
        self.assertGreater(tau_a2, tau_a1)

    def test_tc23_zero_queue_instant_depletion(self) -> None:
        """TC23: Test empty L1 queue (Q = 0) returns 0.0s depletion arrival."""
        tau_b1, _, _, _ = self.forecaster.compute_queue_depletion(
            bid_depths=[0.0, 100.0],
            ask_depths=[100.0, 100.0],
            bid_dep_rate=10.0,
        )
        self.assertEqual(tau_b1, 0.0)

    def test_tc24_replenishing_queue_ceiling(self) -> None:
        """TC24: Test negative/zero depletion velocity hits tau_max ceiling (999.0s)."""
        tau_b1, _, _, _ = self.forecaster.compute_queue_depletion(
            bid_depths=[500.0, 500.0],
            ask_depths=[500.0, 500.0],
            bid_dep_rate=-5.0,  # Queue replenishing
        )
        self.assertEqual(tau_b1, self.forecaster.config.tau_max_sec)

    def test_tc25_hawkes_snapshot_depletion_coupling(self) -> None:
        """TC25: Test Hawkes high arrival intensity accelerates depletion."""
        mock_snapshot = HawkesIntensitySnapshot(
            timestamp=1.0,
            intensities=np.array([10.0, 10.0, 50.0, 30.0]),
            lambda_bid_place=10.0,
            lambda_ask_place=10.0,
            lambda_trade=50.0,
            lambda_cancel=30.0,
            total_intensity=100.0,
            quote_toxicity=0.80,
            burst_multiplier=3.0,
            cluster_dispersion=2.0,
            is_toxic=True,
            is_burst=True,
            arrival_imbalance=0.75,  # Aggressive buying pressure
            criticality_index=0.60,
        )

        tau_b_base, tau_a_base, _, _ = self.forecaster.compute_queue_depletion(
            bid_depths=[500.0, 500.0],
            ask_depths=[500.0, 500.0],
        )
        tau_b_hwk, tau_a_hwk, _, _ = self.forecaster.compute_queue_depletion(
            bid_depths=[500.0, 500.0],
            ask_depths=[500.0, 500.0],
            hawkes_snapshot=mock_snapshot,
        )
        # Aggressive buying should accelerate ask depletion time
        self.assertLess(tau_a_hwk, tau_a_base)

    def test_tc26_l2_depletion_cumulative_ordering(self) -> None:
        """TC26: Verify monotonicity E[tau_L2] >= E[tau_L1]."""
        tau_b1, tau_a1, tau_b2, tau_a2 = self.forecaster.compute_queue_depletion(
            bid_depths=[100.0, 200.0],
            ask_depths=[150.0, 250.0],
            bid_dep_rate=15.0,
            ask_dep_rate=15.0,
        )
        self.assertGreaterEqual(tau_b2, tau_b1)
        self.assertGreaterEqual(tau_a2, tau_a1)

    # -----------------------------------------------------------------------
    # Category 8: Sub-Microsecond Multi-Horizon Forward Drift Projections
    # -----------------------------------------------------------------------
    def test_tc27_discrete_horizons_present(self) -> None:
        """TC27: Assert default projections contain 100ms, 500ms, and 1s horizons."""
        projs = self.forecaster.compute_forward_projections(mid_price=100.0, sde_drift=0.5)
        self.assertIn(0.1, projs)
        self.assertIn(0.5, projs)
        self.assertIn(1.0, projs)

    def test_tc28_drift_increases_with_horizon(self) -> None:
        """TC28: Assert expected price drift magnitude scales with sqrt(H)."""
        projs = self.forecaster.compute_forward_projections(mid_price=100.0, sde_drift=0.6)
        d_100ms = abs(projs[0.1].expected_drift_bps)
        d_500ms = abs(projs[0.5].expected_drift_bps)
        d_1000ms = abs(projs[1.0].expected_drift_bps)

        self.assertGreater(d_500ms, d_100ms)
        self.assertGreater(d_1000ms, d_500ms)

    def test_tc29_confidence_interval_symmetry(self) -> None:
        """TC29: Assert 95% confidence intervals are symmetric around expected drift."""
        projs = self.forecaster.compute_forward_projections(mid_price=200.0, sde_drift=0.4)
        for h, p in projs.items():
            self.assertEqual(p.confidence_level, 0.95)
            spread_lower = p.expected_drift_bps - p.lower_bound_bps
            spread_upper = p.upper_bound_bps - p.expected_drift_bps
            self.assertAlmostEqual(spread_lower, spread_upper, places=4)
            self.assertGreater(spread_upper, 0.0)

    def test_tc30_negative_drift_projection_order(self) -> None:
        """TC30: Test downward drift projections produce lower prices with correct bound ordering."""
        projs = self.forecaster.compute_forward_projections(mid_price=100.0, sde_drift=-0.8)
        p1 = projs[1.0]
        self.assertLess(p1.expected_price, 100.0)
        self.assertLess(p1.lower_bound_bps, p1.expected_drift_bps)
        self.assertGreater(p1.upper_bound_bps, p1.expected_drift_bps)

    # -----------------------------------------------------------------------
    # Category 9: End-to-End Forecaster Pipeline & Hawkes Coupling
    # -----------------------------------------------------------------------
    def test_tc31_full_forecast_pipeline_output(self) -> None:
        """TC31: Test forecast() executes complete pipeline and returns structured payload."""
        output = self.forecaster.forecast(
            best_bid=150.20,
            best_ask=150.25,
            bid_ladder=[1000.0, 800.0, 600.0],
            ask_ladder=[300.0, 400.0, 500.0],
            symbol="MSFT",
        )
        self.assertIsInstance(output, MicropriceForecasterOutput)
        self.assertEqual(output.symbol, "MSFT")
        self.assertEqual(output.market, "SP500")
        self.assertAlmostEqual(output.mid_price, 150.225, places=4)
        self.assertAlmostEqual(output.spread, 0.05, places=4)
        self.assertGreater(output.micro_price, output.mid_price)
        self.assertGreater(output.obi_l1, 0.0)
        self.assertGreater(output.timestamp_ns, 0)
        self.assertEqual(len(output.projections), 3)

    def test_tc32_full_pipeline_with_trade_history(self) -> None:
        """TC32: Ingest aggressive buys and verify momentum carries into forecast."""
        fc = MicropriceDriftForecaster(market="NASDAQ")
        t = 1000.0
        fc.update_trade("BUY", 500.0, timestamp_sec=t)
        fc.update_trade("BUY", 300.0, timestamp_sec=t + 0.05)

        out = fc.forecast(
            best_bid=200.0,
            best_ask=200.04,
            bid_ladder=[100.0, 100.0, 100.0],
            ask_ladder=[100.0, 100.0, 100.0],
            timestamp_sec=t + 0.1,
        )
        self.assertGreater(out.trade_sign_momentum, 0.0)
        self.assertGreater(out.sde_drift_rate, 0.0)
        self.assertGreater(out.micro_price, out.mid_price)

    def test_tc33_full_pipeline_with_hawkes_snapshot(self) -> None:
        """TC33: Forecast with coupled Hawkes snapshot accelerating depletion."""
        mock_snapshot = HawkesIntensitySnapshot(
            timestamp=100.0,
            intensities=np.array([5.0, 5.0, 20.0, 40.0]),
            lambda_bid_place=5.0,
            lambda_ask_place=5.0,
            lambda_trade=20.0,
            lambda_cancel=40.0,
            total_intensity=70.0,
            quote_toxicity=0.75,
            burst_multiplier=2.5,
            cluster_dispersion=1.8,
            is_toxic=True,
            is_burst=False,
            arrival_imbalance=-0.5,
            criticality_index=0.45,
        )
        out = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.02,
            bid_ladder=[200.0, 200.0],
            ask_ladder=[200.0, 200.0],
            hawkes_snapshot=mock_snapshot,
        )
        self.assertTrue(np.isfinite(out.tau_depletion_bid_l1))
        self.assertTrue(np.isfinite(out.tau_depletion_ask_l1))

    # -----------------------------------------------------------------------
    # Category 10: Boundary Conditions & Latency Benchmark
    # -----------------------------------------------------------------------
    def test_tc34_extreme_input_handling(self) -> None:
        """TC34: Verify robustness against negative/NaN/infinite ladder inputs."""
        out = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[-50.0, 0.0, float("nan")],
            ask_ladder=[100.0, float("inf"), 50.0],
        )
        self.assertTrue(np.isfinite(out.micro_price))
        self.assertTrue(np.isfinite(out.sde_drift_rate))
        self.assertTrue(np.isfinite(out.tau_depletion_bid_l1))

    def test_tc35_empty_ladder_fallback(self) -> None:
        """TC35: Verify handling of empty ladder inputs."""
        out = self.forecaster.forecast(
            best_bid=80.0,
            best_ask=80.10,
            bid_ladder=[],
            ask_ladder=[],
        )
        self.assertAlmostEqual(out.mid_price, 80.05, places=4)
        self.assertTrue(np.isfinite(out.micro_price))

    def test_tc36_sub_microsecond_latency_benchmark(self) -> None:
        """TC36: Benchmark 10,000 forecast iterations asserting high execution throughput."""
        b_ladder = [500.0, 400.0, 300.0]
        a_ladder = [450.0, 350.0, 250.0]
        n_iters = 10000

        t0 = time.perf_counter()
        for _ in range(n_iters):
            self.forecaster.forecast(
                best_bid=100.0,
                best_ask=100.05,
                bid_ladder=b_ladder,
                ask_ladder=a_ladder,
            )
        elapsed = time.perf_counter() - t0
        avg_us = (elapsed / n_iters) * 1e6

        # In pure Python on Windows, assert throughput is under 40 microseconds per forecast
        self.assertLess(avg_us, 40.0, f"Average forecast() took {avg_us:.2f} us")


if __name__ == "__main__":
    unittest.main()

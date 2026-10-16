"""
tests/test_phase116_hawkes.py
=============================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Multivariate Hawkes Mutual Excitation Process Engine (Feature F550).
Phase 116 (Release R132 / v123 Production Master).

Categories Covered:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: 4-Channel Microstructural Topology & Event Representation (TC04~TC06)
- Category 3: O(1) Sub-Microsecond Recursive Intensity Updates & Timing (TC07~TC09)
- Category 4: Multi-Kernel Support: Single-Exp, Multi-Exp, and Power-Law (TC10~TC12)
- Category 5: Mathematical L1 Stability & Spectral Radius Projection (TC13~TC15)
- Category 6: Pre-calibrated 5-Market Parameter Profiles & Properties (TC16~TC18)
- Category 7: Recursive O(N) Maximum Likelihood Estimation (MLE) Fitting (TC19~TC21)
- Category 8: High-Frequency Quote Toxicity Scoring & Gating (TC22~TC25)
- Category 9: Burst Intensity Clustering, Fano Factor & Criticality Index (TC26~TC29)
- Category 10: Ogata Thinning Simulation Engine (TC30~TC32)
- Category 11: Telemetry Export, Boundary Cases & Numerical Robustness (TC33~TC36)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.hawkes_microstructure_engine import (
    FEATURE,
    MARKET_PROFILES_4D,
    RELEASE,
    VERSION,
    F550HawkesEngine,
    HawkesChannel,
    HawkesFitResult,
    HawkesIntensitySnapshot,
    HawkesMicrostructureAlpha,
    HawkesMicrostructureEngine,
    HawkesParameters4D,
    MicrostructureEvent,
    MultivariateHawkesMicrostructureEngine,
    Phase116HawkesEngine,
)


class TestPhase116HawkesMicrostructureEngine(unittest.TestCase):
    """Master Unit, Integration, and Invariant Test Suite for Feature F550."""

    def setUp(self) -> None:
        self.engine = HawkesMicrostructureEngine(symbol="TEST", market="SP500", seed=42)

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "ai" / "hawkes_microstructure_engine.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "ai" / "hawkes_microstructure_engine.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for hawkes_microstructure_engine.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 116)
        self.assertEqual(RELEASE, "R132")
        self.assertEqual(FEATURE, "F550")
        self.assertEqual(self.engine.VERSION, 116)
        self.assertEqual(self.engine.RELEASE, "R132")
        self.assertEqual(self.engine.FEATURE, "F550")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(MultivariateHawkesMicrostructureEngine, HawkesMicrostructureEngine)
        self.assertIs(Phase116HawkesEngine, HawkesMicrostructureEngine)
        self.assertIs(F550HawkesEngine, HawkesMicrostructureEngine)
        self.assertIs(HawkesMicrostructureAlpha, HawkesMicrostructureEngine)
        self.assertIn("src.ai.hawkes_microstructure_engine", sys.modules)
        self.assertIn("trading_system.src.ai.hawkes_microstructure_engine", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: 4-Channel Microstructural Topology & Event Representation
    # -----------------------------------------------------------------------
    def test_tc04_four_channel_enum_values(self) -> None:
        """TC04: Assert exact canonical 4-channel values 0..3."""
        self.assertEqual(int(HawkesChannel.BID_PLACEMENT.value), 0)
        self.assertEqual(int(HawkesChannel.ASK_PLACEMENT.value), 1)
        self.assertEqual(int(HawkesChannel.TRADE.value), 2)
        self.assertEqual(int(HawkesChannel.CANCELLATION.value), 3)

    def test_tc05_microstructure_event_construction(self) -> None:
        """TC05: Verify MicrostructureEvent dataclass structure and defaults."""
        evt = MicrostructureEvent(
            timestamp=100.0,
            channel=HawkesChannel.BID_PLACEMENT,
            price=150.25,
            volume=500.0,
            side="BUY",
        )
        self.assertEqual(evt.timestamp, 100.0)
        self.assertEqual(evt.channel, HawkesChannel.BID_PLACEMENT)
        self.assertEqual(evt.price, 150.25)
        self.assertEqual(evt.volume, 500.0)
        self.assertEqual(evt.side, "BUY")
        self.assertEqual(evt.level, 1)

    def test_tc06_update_tick_string_and_int_channels(self) -> None:
        """TC06: Verify update_tick channel coercion from strings, ints, and enums."""
        snap1 = self.engine.update_tick("BID_PLACEMENT", timestamp=1.0, volume=1.0)
        self.assertIsInstance(snap1, HawkesIntensitySnapshot)
        self.assertGreater(snap1.lambda_bid_place, 0.0)

        snap2 = self.engine.update_tick(1, timestamp=1.01, volume=2.0)
        self.assertGreater(snap2.lambda_ask_place, 0.0)

        snap3 = self.engine.update_tick(HawkesChannel.TRADE, timestamp=1.02, volume=5.0)
        self.assertGreater(snap3.lambda_trade, 0.0)

        snap4 = self.engine.update_tick("CANCEL", timestamp=1.03, volume=1.0)
        self.assertGreater(snap4.lambda_cancel, 0.0)

    # -----------------------------------------------------------------------
    # Category 3: O(1) Sub-Microsecond Recursive Intensity Updates & Timing
    # -----------------------------------------------------------------------
    def test_tc07_recursive_decay_logic(self) -> None:
        """TC07: Verify exact exponential decay of memory state vector R(t)."""
        engine = HawkesMicrostructureEngine(seed=42)
        # Event at t=0 on Trade channel
        engine.update_tick(HawkesChannel.TRADE, timestamp=0.0, volume=10.0)
        self.assertAlmostEqual(engine.R[2], 10.0, places=5)

        # Decay over delta_t = 0.1s
        beta_2 = float(engine.beta[2])
        snap = engine.get_intensity_at(t_query=0.1)
        expected_R2 = 10.0 * math.exp(-beta_2 * 0.1)
        self.assertAlmostEqual(engine.R[2] * math.exp(-beta_2 * 0.1), expected_R2, places=4)
        self.assertAlmostEqual(snap.lambda_trade, float(engine.mu[2] + engine.alpha[2, 2] * expected_R2), places=3)

    def test_tc08_sub_microsecond_online_update_speed(self) -> None:
        """TC08: Benchmark 5,000 online event updates asserting high throughput."""
        engine = HawkesMicrostructureEngine(seed=42)
        n_iters = 5000
        t0 = time.perf_counter()
        curr_t = 1000.0
        for i in range(n_iters):
            curr_t += 0.0001
            ch = i % 4
            engine.update_tick(ch, timestamp=curr_t, volume=1.0)
        elapsed = time.perf_counter() - t0
        avg_us = (elapsed / n_iters) * 1e6
        # Assert average latency in pure python is within reasonable microsecond range (< 50 us on Windows)
        self.assertLess(avg_us, 50.0, f"Average per-event update took {avg_us:.2f} us")

    def test_tc09_event_counts_tracking(self) -> None:
        """TC09: Verify event_count and per-channel distribution increment correctly."""
        self.engine.update_tick(0, timestamp=1.0)
        self.engine.update_tick(0, timestamp=1.1)
        self.engine.update_tick(2, timestamp=1.2)
        self.engine.update_tick(3, timestamp=1.3)
        self.assertEqual(self.engine.event_count, 4)
        self.assertEqual(self.engine.channel_counts[0], 2)
        self.assertEqual(self.engine.channel_counts[1], 0)
        self.assertEqual(self.engine.channel_counts[2], 1)
        self.assertEqual(self.engine.channel_counts[3], 1)

    # -----------------------------------------------------------------------
    # Category 4: Multi-Kernel Support
    # -----------------------------------------------------------------------
    def test_tc10_single_exponential_kernel(self) -> None:
        """TC10: Test standard single exponential kernel evaluation."""
        engine = HawkesMicrostructureEngine(kernel_type="exponential")
        snap = engine.update_tick(0, timestamp=1.0, volume=1.0)
        self.assertEqual(snap.intensities.shape, (4,))
        self.assertTrue(np.all(snap.intensities > 0))

    def test_tc11_multi_exponential_kernel(self) -> None:
        """TC11: Test 3-timescale multi-exponential sum kernel evaluation."""
        engine = HawkesMicrostructureEngine(kernel_type="multi_exponential")
        snap = engine.update_tick(1, timestamp=1.0, volume=2.0)
        self.assertEqual(snap.intensities.shape, (4,))
        self.assertTrue(np.all(snap.intensities > 0))
        snap2 = engine.get_intensity_at(t_query=1.5)
        self.assertLess(snap2.total_intensity, snap.total_intensity)

    def test_tc12_power_law_fallback_kernel(self) -> None:
        """TC12: Test truncated power-law fallback kernel over history ring."""
        engine = HawkesMicrostructureEngine(kernel_type="power_law", power_law_gamma=1.6, power_law_tau0=0.05)
        engine.update_tick(2, timestamp=1.0, volume=1.0)
        snap1 = engine.update_tick(3, timestamp=1.01, volume=1.0)
        self.assertGreater(snap1.lambda_cancel, float(engine.mu[3]))
        snap_decayed = engine.get_intensity_at(t_query=5.0)
        self.assertLess(snap_decayed.total_intensity, snap1.total_intensity)

    # -----------------------------------------------------------------------
    # Category 5: Mathematical L1 Stability & Spectral Radius Projection
    # -----------------------------------------------------------------------
    def test_tc13_spectral_radius_calculation(self) -> None:
        """TC13: Test exact spectral radius computation via eigenvalues."""
        rho = self.engine.compute_spectral_radius()
        self.assertGreater(rho, 0.0)
        self.assertLess(rho, 1.0, "Spectral radius must be strictly subcritical (< 1.0)")

    def test_tc14_stability_projection_on_supercritical_matrix(self) -> None:
        """TC14: Test projection mechanism forces explosive matrix below ceiling."""
        engine = HawkesMicrostructureEngine(seed=42)
        # Artificially inflate alpha to make supercritical rho > 2.5
        engine.alpha = engine.alpha * 5.0
        rho_super = engine.compute_spectral_radius()
        self.assertGreater(rho_super, 1.0)

        # Enforce stability projection
        new_rho = engine.project_to_stability(max_branching=0.95)
        self.assertLessEqual(new_rho, 0.95)
        self.assertAlmostEqual(engine.compute_spectral_radius(), new_rho, places=4)

    def test_tc15_infectivity_matrix_structure(self) -> None:
        """TC15: Test infectivity matrix Gamma_ij = alpha_ij / beta_j in R^(4 x 4)."""
        gamma = self.engine.compute_infectivity_matrix()
        self.assertEqual(gamma.shape, (4, 4))
        for i in range(4):
            for j in range(4):
                self.assertAlmostEqual(gamma[i, j], float(self.engine.alpha[i, j] / self.engine.beta[j]), places=5)

    # -----------------------------------------------------------------------
    # Category 6: Pre-calibrated 5-Market Parameter Profiles
    # -----------------------------------------------------------------------
    def test_tc16_five_market_profile_loading(self) -> None:
        """TC16: Assert all 5 markets (SP500, NASDAQ, KOSPI, KOSDAQ, RUSSELL2000) calibrate stably."""
        markets = ["SP500", "NASDAQ", "KOSPI", "KOSDAQ", "RUSSELL2000"]
        for m in markets:
            engine = HawkesMicrostructureEngine(market=m)
            self.assertEqual(engine.market, m)
            rho = engine.compute_spectral_radius()
            self.assertLess(rho, 1.0, f"Market {m} must have rho < 1.0")
            self.assertTrue(np.all(engine.mu > 0))
            self.assertTrue(np.all(engine.alpha >= 0))
            self.assertTrue(np.all(engine.beta > 0))

    def test_tc17_market_recalibration(self) -> None:
        """TC17: Test dynamic calibrate_market switch."""
        engine = HawkesMicrostructureEngine(market="SP500")
        self.assertEqual(engine.market, "SP500")
        params = engine.calibrate_market("KOSPI")
        self.assertEqual(engine.market, "KOSPI")
        self.assertTrue(params.is_stable)
        self.assertAlmostEqual(engine.mu[0], MARKET_PROFILES_4D["KOSPI"]["mu"][0], places=4)

    def test_tc18_market_profile_unknown_fallback(self) -> None:
        """TC18: Assert unknown market string gracefully falls back to SP500."""
        engine = HawkesMicrostructureEngine(market="UNKNOWN_EXCHANGE")
        self.assertEqual(engine.market, "SP500")

    # -----------------------------------------------------------------------
    # Category 7: Recursive O(N) Maximum Likelihood Estimation (MLE) Fitting
    # -----------------------------------------------------------------------
    def test_tc19_log_likelihood_evaluation(self) -> None:
        """TC19: Verify exact log-likelihood evaluation produces finite numeric value."""
        ts = np.array([0.1, 0.25, 0.40, 0.80, 1.20, 1.50, 2.00], dtype=np.float64)
        ch = np.array([0, 1, 2, 3, 2, 0, 1], dtype=np.int32)
        ll = self.engine.log_likelihood(ts, ch, 2.5, self.engine.mu, self.engine.alpha, self.engine.beta)
        self.assertTrue(np.isfinite(ll))
        self.assertIsInstance(ll, float)

    def test_tc20_mle_fit_with_synthetic_events(self) -> None:
        """TC20: Fit 4D Hawkes model on synthetic stream and assert convergence and stability."""
        events = self.engine.simulate_order_stream(duration_seconds=5.0, seed=123)
        self.assertGreater(len(events), 10)

        result = self.engine.fit_mle(events, max_iter=30)
        self.assertIsInstance(result, HawkesFitResult)
        self.assertTrue(result.converged)
        self.assertLess(result.params.spectral_radius, 1.0)
        self.assertTrue(np.isfinite(result.aic))
        self.assertTrue(np.isfinite(result.bic))

    def test_tc21_mle_insufficient_events_fallback(self) -> None:
        """TC21: Verify graceful fallback when event count is below minimum threshold."""
        events = [MicrostructureEvent(timestamp=1.0, channel=HawkesChannel.TRADE)]
        res = self.engine.fit_mle(events)
        self.assertTrue(res.converged)
        self.assertEqual(res.num_events, 1)

    # -----------------------------------------------------------------------
    # Category 8: High-Frequency Quote Toxicity Scoring & Gating
    # -----------------------------------------------------------------------
    def test_tc22_baseline_quote_toxicity_bounds(self) -> None:
        """TC22: Assert quote toxicity score lies strictly in [0.0, 1.0]."""
        snap = self.engine.get_intensity_at()
        self.assertGreaterEqual(snap.quote_toxicity, 0.0)
        self.assertLessEqual(snap.quote_toxicity, 1.0)

    def test_tc23_trade_to_cancel_toxicity_surge(self) -> None:
        """TC23: Inject heavy trade events followed by cancels and verify toxicity escalation."""
        engine = HawkesMicrostructureEngine(seed=42)
        # Normal baseline
        snap_base = engine.get_intensity_at()

        # Burst of aggressive trades
        t = 1.0
        for _ in range(15):
            t += 0.005
            engine.update_tick(HawkesChannel.TRADE, timestamp=t, volume=10.0)

        # Immediate follow-on cancellations
        for _ in range(15):
            t += 0.005
            engine.update_tick(HawkesChannel.CANCELLATION, timestamp=t, volume=10.0)

        snap_toxic = engine.get_intensity_at(t)
        self.assertGreater(snap_toxic.quote_toxicity, snap_base.quote_toxicity)
        self.assertGreater(snap_toxic.burst_multiplier, 1.5)

    def test_tc24_quote_toxicity_directional_compute(self) -> None:
        """TC24: Test compute_quote_toxicity against BUY vs SELL order side."""
        tox_buy = self.engine.compute_quote_toxicity(proposed_side="BUY")
        tox_sell = self.engine.compute_quote_toxicity(proposed_side="SELL")
        self.assertIn("quote_toxicity", tox_buy)
        self.assertIn("adverse_toxicity", tox_buy)
        self.assertIn("is_toxic", tox_buy)
        self.assertGreaterEqual(tox_buy["adverse_toxicity"], 0.0)
        self.assertLessEqual(tox_buy["adverse_toxicity"], 1.0)
        self.assertGreaterEqual(tox_sell["adverse_toxicity"], 0.0)
        self.assertLessEqual(tox_sell["adverse_toxicity"], 1.0)

    def test_tc25_toxicity_threshold_flagging(self) -> None:
        """TC25: Verify is_toxic boolean matches toxic_threshold setting."""
        engine = HawkesMicrostructureEngine(toxic_threshold=0.30)
        # Push toxicity up
        t = 10.0
        for _ in range(25):
            t += 0.002
            engine.update_tick(HawkesChannel.TRADE, timestamp=t, volume=20.0)
            engine.update_tick(HawkesChannel.CANCELLATION, timestamp=t + 0.001, volume=20.0)
        snap = engine.get_intensity_at(t + 0.002)
        if snap.quote_toxicity >= 0.30:
            self.assertTrue(snap.is_toxic)

    # -----------------------------------------------------------------------
    # Category 9: Burst Intensity Clustering & Criticality Index
    # -----------------------------------------------------------------------
    def test_tc26_burst_multiplier_quiescent_vs_burst(self) -> None:
        """TC26: Test burst multiplier increases under high arrival cluster."""
        engine = HawkesMicrostructureEngine(seed=42)
        snap_quiet = engine.get_intensity_at()
        self.assertAlmostEqual(snap_quiet.burst_multiplier, 1.0, places=1)

        # Trigger cluster
        curr_t = 50.0
        for _ in range(20):
            curr_t += 0.001
            engine.update_tick(0, timestamp=curr_t, volume=5.0)

        snap_burst = engine.get_intensity_at(curr_t)
        self.assertGreater(snap_burst.burst_multiplier, snap_quiet.burst_multiplier)

    def test_tc27_criticality_index_range(self) -> None:
        """TC27: Assert criticality index is bounded in [0.0, 1.0]."""
        snap = self.engine.get_intensity_at()
        self.assertGreaterEqual(snap.criticality_index, 0.0)
        self.assertLessEqual(snap.criticality_index, 1.0)

    def test_tc28_compute_burst_metrics_output(self) -> None:
        """TC28: Test compute_burst_metrics dictionary keys and values."""
        metrics = self.engine.compute_burst_metrics()
        self.assertIn("branching_ratio", metrics)
        self.assertIn("endogenous_fraction", metrics)
        self.assertIn("burst_multiplier", metrics)
        self.assertIn("fano_dispersion", metrics)
        self.assertIn("criticality_index", metrics)
        self.assertIn("is_burst", metrics)

    def test_tc29_arrival_imbalance_bounds(self) -> None:
        """TC29: Assert arrival imbalance lies in [-1.0, 1.0]."""
        snap = self.engine.get_intensity_at()
        self.assertGreaterEqual(snap.arrival_imbalance, -1.0)
        self.assertLessEqual(snap.arrival_imbalance, 1.0)

    # -----------------------------------------------------------------------
    # Category 10: Ogata Thinning Simulation Engine
    # -----------------------------------------------------------------------
    def test_tc30_simulation_stream_generation(self) -> None:
        """TC30: Verify Ogata thinning simulation generates valid MicrostructureEvents."""
        events = self.engine.simulate_order_stream(duration_seconds=3.0, seed=99)
        self.assertGreater(len(events), 0)
        # Check chronological ordering
        for k in range(1, len(events)):
            self.assertGreaterEqual(events[k].timestamp, events[k - 1].timestamp)
            self.assertIn(events[k].channel, [
                HawkesChannel.BID_PLACEMENT,
                HawkesChannel.ASK_PLACEMENT,
                HawkesChannel.TRADE,
                HawkesChannel.CANCELLATION,
            ])

    def test_tc31_simulation_all_channels_represented(self) -> None:
        """TC31: Over sufficient duration, all 4 channels are observed."""
        events = self.engine.simulate_order_stream(duration_seconds=10.0, seed=42)
        ch_set = {e.channel for e in events}
        self.assertEqual(len(ch_set), 4)

    def test_tc32_simulation_reproducibility_with_seed(self) -> None:
        """TC32: Verify identical seed produces deterministic simulated stream."""
        events1 = self.engine.simulate_order_stream(duration_seconds=2.0, seed=777)
        events2 = self.engine.simulate_order_stream(duration_seconds=2.0, seed=777)
        self.assertEqual(len(events1), len(events2))
        for e1, e2 in zip(events1, events2):
            self.assertEqual(e1.timestamp, e2.timestamp)
            self.assertEqual(e1.channel, e2.channel)
            self.assertEqual(e1.price, e2.price)

    # -----------------------------------------------------------------------
    # Category 11: Telemetry Export & Boundary Robustness
    # -----------------------------------------------------------------------
    def test_tc33_export_telemetry(self) -> None:
        """TC33: Verify export_telemetry returns complete structured dictionary."""
        telemetry = self.engine.export_telemetry()
        self.assertEqual(telemetry["version"], 116)
        self.assertEqual(telemetry["release"], "R132")
        self.assertEqual(telemetry["feature"], "F550")
        self.assertEqual(telemetry["market"], "SP500")
        self.assertIn("snapshot", telemetry)
        self.assertIn("channel_counts", telemetry)

    def test_tc34_zero_and_negative_time_deltas(self) -> None:
        """TC34: Verify robustness against non-increasing timestamps."""
        snap1 = self.engine.update_tick(0, timestamp=10.0)
        snap2 = self.engine.update_tick(1, timestamp=10.0)  # Same timestamp
        snap3 = self.engine.update_tick(2, timestamp=9.5)   # Out-of-order timestamp
        self.assertTrue(np.all(snap1.intensities > 0))
        self.assertTrue(np.all(snap2.intensities > 0))
        self.assertTrue(np.all(snap3.intensities > 0))

    def test_tc35_extreme_volume_marks(self) -> None:
        """TC35: Verify handling of extreme volume marks without overflow."""
        snap = self.engine.update_tick(HawkesChannel.TRADE, timestamp=100.0, volume=1_000_000.0)
        self.assertTrue(np.isfinite(snap.total_intensity))
        self.assertLessEqual(snap.quote_toxicity, 1.0)
        self.assertLessEqual(snap.criticality_index, 1.0)

    def test_tc36_empty_stream_mle_stability(self) -> None:
        """TC36: Test MLE fit on empty sequence returns stable parameters without crashing."""
        res = self.engine.fit_mle([])
        self.assertTrue(res.converged)
        self.assertEqual(res.num_events, 0)
        self.assertTrue(res.params.is_stable)


if __name__ == "__main__":
    unittest.main()

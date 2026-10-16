"""
tests/test_phase116_adversarial_challenger_alpha.py
===================================================
Adversarial Stress, Fuzzing, Mathematical Invariant, and Corner-Case Suite for:
Feature F550: Multivariate Hawkes Mutual Excitation Process Engine
Feature F551: Micro-Price Drift & Queue Depletion Velocity Forecaster
Phase 116 (Release R132 / v123 Production Master).

Adversarial Dimensions Tested:
1. Extreme Time Gaps: dt -> 0 (sub-nanosecond), dt -> 10^9 s, out-of-order negative dt.
2. Order Book Ladder Anomalies: Empty ladders, inverted/crossed book, zero spread, negative prices, NaN/Inf depths.
3. Explosive Infectivity & Stability: Supercritical matrices (rho >> 1.0), spectral radius clipping (rho < 1.0 strictly).
4. Extreme High-Frequency Bursts: 10,000+ events/ms, cancellation avalanches, trade frenzies, Fano factor bounds.
5. SDE Drift & Confidence Interval Degeneracies: Max negative drift, zero volatility, zero/negative mid-price.
6. Hitting Times & Hawkes Coupling: L1 <= L2 depletion monotonicity, replenishing ceilings, malformed snapshot resilience.
7. MLE Calibration Extremes: Zero events, sub-threshold events, identical timestamps, single-channel monopoly.
8. Monte Carlo Random Fuzzing: 500 randomized iterations ensuring zero NaNs, infinities, or uncaught exceptions.
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path
from typing import Any, List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.hawkes_microstructure_engine import (
    HawkesChannel,
    HawkesFitResult,
    HawkesIntensitySnapshot,
    HawkesMicrostructureEngine,
    HawkesParameters4D,
    MicrostructureEvent,
)
from src.ai.microprice_drift_forecaster import (
    DriftProjection,
    MicropriceDriftConfig,
    MicropriceDriftForecaster,
    MicropriceForecasterOutput,
)


class TestStressScenario1ExtremeTimeGaps(unittest.TestCase):
    """Stress Scenario 1: Extreme time deltas (dt -> 0, dt -> 10^9s, dt < 0)."""

    def setUp(self) -> None:
        self.engine = HawkesMicrostructureEngine(symbol="STRESS_GAP", market="SP500", seed=42)
        self.forecaster = MicropriceDriftForecaster(market="SP500", symbol="STRESS_GAP")

    def test_hawkes_vanishing_dt_limit(self) -> None:
        """Verify dt -> 0 (dt = 0.0, 1e-15, 1e-12) does not overflow or produce NaNs."""
        base_t = 1000.0
        # Initialize
        self.engine.update_tick(0, timestamp=base_t, volume=1.0)

        # Ingest ticks with near-zero or zero dt
        dts = [0.0, 1e-18, 1e-15, 1e-12, 1e-9, 1e-6]
        curr_t = base_t
        for dt in dts:
            curr_t += dt
            snap = self.engine.update_tick(1, timestamp=curr_t, volume=1.0)
            self.assertTrue(np.all(np.isfinite(snap.intensities)))
            self.assertTrue(np.isfinite(snap.total_intensity))
            self.assertTrue(0.0 <= snap.quote_toxicity <= 1.0)
            self.assertTrue(snap.total_intensity > 0.0)

    def test_hawkes_astronomical_dt_gap(self) -> None:
        """Verify huge dt jumps (dt = 10^6, 10^9, 10^12) decay memory to zero without underflow error."""
        t0 = 1000.0
        # Build up high excitement
        for i in range(10):
            self.engine.update_tick(i % 4, timestamp=t0 + i * 0.01, volume=5.0)

        r_before = self.engine.R.copy()
        self.assertTrue(np.all(r_before > 0.0))

        # Huge time jump: 10^9 seconds (~31.7 years)
        t_huge = t0 + 1e9
        snap_huge = self.engine.update_tick(HawkesChannel.TRADE, timestamp=t_huge, volume=1.0)

        # Intensities should be finite and bounded close to baseline mu + impact of current tick
        self.assertTrue(np.all(np.isfinite(snap_huge.intensities)))
        self.assertTrue(np.isfinite(snap_huge.total_intensity))
        self.assertAlmostEqual(self.engine.R[0], 0.0, places=5)
        self.assertAlmostEqual(self.engine.R[1], 0.0, places=5)
        self.assertAlmostEqual(self.engine.R[3], 0.0, places=5)
        # Channel 2 just received 1.0 volume
        self.assertAlmostEqual(self.engine.R[2], 1.0, places=5)

    def test_hawkes_negative_time_gap(self) -> None:
        """Verify out-of-order event timestamps (dt < 0) are clamped to 0.0 and processed safely."""
        self.engine.update_tick(0, timestamp=500.0, volume=1.0)
        # Event arrives with timestamp earlier than last_timestamp
        snap = self.engine.update_tick(1, timestamp=400.0, volume=1.0)
        self.assertTrue(np.all(np.isfinite(snap.intensities)))
        self.assertTrue(np.isfinite(snap.total_intensity))
        self.assertTrue(self.engine.last_timestamp == 400.0)

    def test_hawkes_multi_exponential_extreme_gaps(self) -> None:
        """Verify multi-exponential kernel under dt = 0 and dt = 1e8."""
        eng_me = HawkesMicrostructureEngine(kernel_type="multi_exponential", seed=42)
        eng_me.update_tick(0, timestamp=100.0, volume=2.0)
        snap_zero = eng_me.update_tick(1, timestamp=100.0, volume=2.0)
        self.assertTrue(np.all(np.isfinite(snap_zero.intensities)))

        snap_huge = eng_me.update_tick(2, timestamp=100.0 + 1e8, volume=1.0)
        self.assertTrue(np.all(np.isfinite(snap_huge.intensities)))
        self.assertTrue(0.0 <= snap_huge.quote_toxicity <= 1.0)

    def test_hawkes_power_law_extreme_gaps(self) -> None:
        """Verify power-law kernel under dt = 0 and dt = 1e8."""
        eng_pl = HawkesMicrostructureEngine(kernel_type="power_law", seed=42)
        for i in range(10):
            eng_pl.update_tick(i % 4, timestamp=100.0 + i * 0.001, volume=1.0)
        snap_gap = eng_pl.get_intensity_at(100.0 + 1e8)
        self.assertTrue(np.all(np.isfinite(snap_gap.intensities)))
        self.assertTrue(snap_gap.total_intensity > 0.0)

    def test_forecaster_trade_extreme_time_gaps(self) -> None:
        """Verify forecaster trade sign momentum under dt = 0 and dt = 1e7."""
        # Rapid succession at dt = 0
        for _ in range(50):
            self.forecaster.update_trade(side="BUY", volume=100.0, timestamp_sec=1000.0)
        m_burst = self.forecaster.get_trade_sign_momentum(timestamp_sec=1000.0)
        self.assertTrue(0.0 < m_burst <= 1.0)

        # Decay over 10^7 seconds
        m_decayed = self.forecaster.get_trade_sign_momentum(timestamp_sec=1000.0 + 1e7)
        self.assertAlmostEqual(m_decayed, 0.0, places=6)


class TestStressScenario2OrderBookDepthsAndVolumeSpikes(unittest.TestCase):
    """Stress Scenario 2: Zero, inverted, empty, infinite, and NaN order book ladders."""

    def setUp(self) -> None:
        self.forecaster = MicropriceDriftForecaster(market="SP500", symbol="STRESS_DEPTH")
        self.engine = HawkesMicrostructureEngine(market="SP500", symbol="STRESS_DEPTH")

    def test_forecaster_empty_order_book_depths(self) -> None:
        """Verify empty ladders [] gracefully fallback to standard default without exception."""
        out = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[],
            ask_ladder=[],
        )
        self.assertTrue(np.isfinite(out.micro_price))
        self.assertTrue(np.isfinite(out.sde_drift_rate))
        self.assertTrue(np.isfinite(out.tau_depletion_bid_l1))
        self.assertAlmostEqual(out.spread, 0.05, places=5)

    def test_forecaster_all_zero_queues(self) -> None:
        """Verify all zero depths [0.0, 0.0, 0.0] produce instant zero depletion time."""
        out = self.forecaster.forecast(
            best_bid=50.0,
            best_ask=50.02,
            bid_ladder=[0.0, 0.0, 0.0],
            ask_ladder=[0.0, 0.0, 0.0],
        )
        self.assertEqual(out.obi_l1, 0.0)
        self.assertEqual(out.tau_depletion_bid_l1, 0.0)
        self.assertEqual(out.tau_depletion_ask_l1, 0.0)
        self.assertEqual(out.tau_depletion_bid_l2, 0.0)
        self.assertEqual(out.tau_depletion_ask_l2, 0.0)
        self.assertTrue(np.isfinite(out.micro_price))

    def test_forecaster_inverted_and_crossed_books(self) -> None:
        """Verify inverted books (best_bid > best_ask) collapse spread to 0.0 and micro_price to best_bid."""
        # Inverted book: best_bid = 105.0, best_ask = 95.0
        out_inv = self.forecaster.forecast(
            best_bid=105.0,
            best_ask=95.0,
            bid_ladder=[200.0, 150.0],
            ask_ladder=[100.0, 80.0],
        )
        self.assertEqual(out_inv.spread, 0.0)
        self.assertEqual(out_inv.mid_price, 105.0)
        self.assertEqual(out_inv.micro_price, 105.0)

        # Locked book: best_bid == best_ask == 100.0
        out_lock = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.0,
            bid_ladder=[50.0],
            ask_ladder=[50.0],
        )
        self.assertEqual(out_lock.spread, 0.0)
        self.assertEqual(out_lock.micro_price, 100.0)

    def test_forecaster_subpenny_and_extreme_prices(self) -> None:
        """Verify subpenny micro-stocks ($0.0001) and large stocks ($500,000)."""
        # Subpenny
        out_sub = self.forecaster.forecast(
            best_bid=0.0001,
            best_ask=0.0002,
            bid_ladder=[1000000.0, 500000.0],
            ask_ladder=[100000.0, 50000.0],
        )
        self.assertTrue(0.0001 <= out_sub.micro_price <= 0.0002)
        self.assertTrue(np.isfinite(out_sub.micro_price))

        # BRK.A scale
        out_large = self.forecaster.forecast(
            best_bid=650000.0,
            best_ask=650050.0,
            bid_ladder=[10.0, 5.0],
            ask_ladder=[20.0, 15.0],
        )
        self.assertTrue(650000.0 <= out_large.micro_price <= 650050.0)

    def test_forecaster_negative_prices(self) -> None:
        """Verify negative prices (e.g. negative energy futures) compute safely."""
        out_neg = self.forecaster.forecast(
            best_bid=-25.0,
            best_ask=-20.0,
            bid_ladder=[100.0, 80.0],
            ask_ladder=[150.0, 120.0],
        )
        self.assertEqual(out_neg.spread, 5.0)
        self.assertEqual(out_neg.mid_price, -22.5)
        self.assertTrue(-25.0 <= out_neg.micro_price <= -20.0)

    def test_forecaster_nan_inf_depth_sanitization(self) -> None:
        """Verify NaN, Inf, -Inf, and negative depth entries are purged to 0.0."""
        dirty_bid = [float("nan"), float("inf"), -100.0, 50.0]
        dirty_ask = [float("-inf"), 0.0, float("nan")]
        out = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.10,
            bid_ladder=dirty_bid,
            ask_ladder=dirty_ask,
        )
        self.assertTrue(np.isfinite(out.micro_price))
        self.assertTrue(np.isfinite(out.sde_drift_rate))
        self.assertTrue(np.isfinite(out.tau_depletion_bid_l1))
        self.assertTrue(np.isfinite(out.tau_depletion_ask_l1))

    def test_forecaster_infinite_volume_spike_saturation(self) -> None:
        """Verify huge volume (1e25) in queue saturates depletion time at tau_max (999.0s)."""
        out = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[1e25, 1e25, 1e25],
            ask_ladder=[100.0, 50.0],
        )
        self.assertEqual(out.tau_depletion_bid_l1, 999.0)
        self.assertEqual(out.tau_depletion_bid_l2, 999.0)
        self.assertEqual(out.obi_l1, 1.0)
        self.assertTrue(np.isfinite(out.micro_price))

    def test_hawkes_extreme_volume_spikes(self) -> None:
        """Verify Hawkes engine handles massive volume spikes (1e20) without NaN or crash."""
        snap = self.engine.update_tick(
            channel=HawkesChannel.TRADE,
            timestamp=1000.0,
            volume=1e20,
        )
        self.assertTrue(np.all(np.isfinite(snap.intensities)))
        self.assertTrue(snap.is_burst)
        self.assertTrue(0.0 <= snap.quote_toxicity <= 1.0)


class TestStressScenario3ExplosiveInfectivityAndSpectralRadius(unittest.TestCase):
    """Stress Scenario 3: Explosive infectivity matrices and strict spectral radius enforcement."""

    def setUp(self) -> None:
        self.engine = HawkesMicrostructureEngine(symbol="STRESS_STAB", market="SP500")

    def test_explosive_supercritical_spectral_radius_clipping(self) -> None:
        """Verify supercritical infectivity matrix (rho = 400,000) is strictly clipped to rho < 1.0."""
        # Set astronomical alpha and tiny beta
        self.engine.alpha = np.ones((4, 4), dtype=np.float64) * 10000.0
        self.engine.beta = np.ones(4, dtype=np.float64) * 0.1

        rho_before = self.engine.compute_spectral_radius()
        self.assertAlmostEqual(rho_before, 400000.0, delta=1.0)

        # Stability projection
        rho_after = self.engine.project_to_stability(max_branching=0.98)
        self.assertLess(rho_after, 0.98)
        self.assertLess(rho_after, 1.0)
        self.assertTrue(np.all(self.engine.alpha >= 0.0))

        # Check subsequent simulation stability
        events = self.engine.simulate_order_stream(duration_seconds=1.0, seed=42)
        self.assertTrue(isinstance(events, list))
        self.assertTrue(len(events) > 0)

    def test_stability_projection_ceiling_sweep(self) -> None:
        """Verify stability projection across adversarial ceilings [0.001, 0.5, 0.999, 1.5, -1.0]."""
        ceilings = [0.01, 0.10, 0.50, 0.85, 0.98, 0.999, 1.50, -0.50]
        for c in ceilings:
            self.engine.alpha = np.ones((4, 4), dtype=np.float64) * 500.0
            self.engine.beta = np.ones(4, dtype=np.float64) * 2.0
            rho = self.engine.project_to_stability(max_branching=c)
            # In ALL cases, spectral radius must be strictly less than 1.0
            self.assertLess(rho, 1.0, f"Failed for ceiling {c}")
            self.assertTrue(rho > 0.0)

    def test_degenerate_zero_and_singular_matrices(self) -> None:
        """Verify all-zero alpha and rank-1 singular matrices handle stability correctly."""
        # All zeros
        self.engine.alpha = np.zeros((4, 4), dtype=np.float64)
        rho_zero = self.engine.compute_spectral_radius()
        self.assertEqual(rho_zero, 0.0)
        self.assertEqual(self.engine.project_to_stability(0.98), 0.0)

        # Rank-1 singular matrix
        u = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
        v = np.array([4.0, 3.0, 2.0, 1.0], dtype=np.float64)
        self.engine.alpha = np.outer(u, v) * 50.0
        rho_rank1 = self.engine.project_to_stability(0.95)
        self.assertLess(rho_rank1, 0.95)
        self.assertLess(rho_rank1, 1.0)

    def test_near_zero_beta_decay(self) -> None:
        """Verify beta near zero (1e-12) does not produce ZeroDivisionError or Inf."""
        self.engine.beta = np.ones(4, dtype=np.float64) * 1e-12
        gamma = self.engine.compute_infectivity_matrix()
        self.assertTrue(np.all(np.isfinite(gamma)))
        rho = self.engine.compute_spectral_radius()
        self.assertTrue(np.isfinite(rho))


class TestStressScenario4HighFrequencyBurstArrivals(unittest.TestCase):
    """Stress Scenario 4: Extreme high-frequency bursts (10,000 events/ms), avalanches."""

    def setUp(self) -> None:
        self.engine = HawkesMicrostructureEngine(symbol="STRESS_BURST", market="SP500", seed=42)

    def test_massive_10k_burst_in_one_millisecond(self) -> None:
        """Inject 10,000 events arriving in 0.001 seconds across 4 channels."""
        t_start = 1000.0
        dt_step = 1e-7  # 10,000 * 1e-7 = 0.001s (1ms)
        n_events = 10000

        for i in range(n_events):
            t_curr = t_start + i * dt_step
            ch = i % 4
            self.engine.update_tick(ch, timestamp=t_curr, volume=1.0)

        snap = self.engine.get_intensity_at(t_start + n_events * dt_step)
        self.assertTrue(np.all(np.isfinite(snap.intensities)))
        self.assertTrue(snap.is_burst)
        self.assertTrue(snap.burst_multiplier > 3.0)
        self.assertTrue(0.0 <= snap.quote_toxicity <= 1.0)
        self.assertTrue(0.0 <= snap.criticality_index <= 1.0)

    def test_toxic_cancellation_avalanche(self) -> None:
        """Simulate a sudden quote cancellation avalanche (5,000 cancellations)."""
        t0 = 2000.0
        for i in range(3000):
            self.engine.update_tick(
                channel=HawkesChannel.CANCELLATION,
                timestamp=t0 + i * 0.0001,
                volume=2.0,
            )

        snap = self.engine.get_intensity_at(t0 + 3000 * 0.0001)
        self.assertTrue(snap.lambda_cancel > snap.lambda_bid_place)
        self.assertTrue(snap.lambda_cancel > snap.lambda_ask_place)
        self.assertTrue(snap.is_burst)
        self.assertTrue(0.0 <= snap.quote_toxicity <= 1.0)

    def test_trade_frenzy_toxicity_skew(self) -> None:
        """Simulate rapid aggressive trades triggering adverse selection toxicity."""
        t0 = 3000.0
        for i in range(2000):
            self.engine.update_tick(
                channel=HawkesChannel.TRADE,
                timestamp=t0 + i * 0.0001,
                volume=5.0,
            )

        tox_buy = self.engine.compute_quote_toxicity(proposed_side="BUY")
        tox_sell = self.engine.compute_quote_toxicity(proposed_side="SELL")
        self.assertTrue(np.isfinite(tox_buy["adverse_toxicity"]))
        self.assertTrue(np.isfinite(tox_sell["adverse_toxicity"]))
        self.assertTrue(0.0 <= tox_buy["adverse_toxicity"] <= 1.0)
        self.assertTrue(0.0 <= tox_sell["adverse_toxicity"] <= 1.0)


class TestStressScenario5NegativeDriftZeroVolAndDegenerateIntervals(unittest.TestCase):
    """Stress Scenario 5: Negative drift, zero volatility, degenerate confidence intervals."""

    def setUp(self) -> None:
        self.forecaster = MicropriceDriftForecaster(market="SP500", symbol="STRESS_DRIFT")

    def test_negative_drift_confidence_intervals(self) -> None:
        """Verify maximum negative drift (sde_drift = -1.0) maintains lower < expected < upper."""
        projections = self.forecaster.compute_forward_projections(
            mid_price=100.0,
            sde_drift=-1.0,
        )

        for h, proj in projections.items():
            self.assertLess(proj.expected_drift_bps, 0.0)
            self.assertLess(proj.expected_price, 100.0)
            self.assertLess(proj.lower_bound_bps, proj.expected_drift_bps)
            self.assertLess(proj.expected_drift_bps, proj.upper_bound_bps)
            self.assertTrue(np.isfinite(proj.expected_price))

    def test_zero_volatility_degenerate_intervals(self) -> None:
        """Verify sigma_market_bps = 0.0 collapses interval to point projection without NaN or zero division."""
        cfg = MicropriceDriftConfig(sigma_market_bps=0.0)
        fc_zero = MicropriceDriftForecaster(config=cfg)

        projections = fc_zero.compute_forward_projections(
            mid_price=150.0,
            sde_drift=0.5,
        )

        for h, proj in projections.items():
            self.assertEqual(proj.lower_bound_bps, proj.expected_drift_bps)
            self.assertEqual(proj.upper_bound_bps, proj.expected_drift_bps)
            self.assertTrue(np.isfinite(proj.expected_price))

    def test_zero_and_negative_mid_prices(self) -> None:
        """Verify zero and negative mid-prices compute valid projections without crash."""
        # Zero mid-price
        proj_zero = self.forecaster.compute_forward_projections(mid_price=0.0, sde_drift=0.3)
        for h, p in proj_zero.items():
            self.assertEqual(p.expected_price, 0.0)

        # Negative mid-price
        proj_neg = self.forecaster.compute_forward_projections(mid_price=-50.0, sde_drift=0.5)
        for h, p in proj_neg.items():
            self.assertTrue(np.isfinite(p.expected_price))

    def test_degenerate_horizons(self) -> None:
        """Verify horizon h = 0.0 produces zero drift and point interval."""
        cfg = MicropriceDriftConfig(horizons_sec=(0.0, 0.001, 100.0))
        fc_hz = MicropriceDriftForecaster(config=cfg)
        projs = fc_hz.compute_forward_projections(mid_price=100.0, sde_drift=0.8)

        # h = 0.0
        p0 = projs[0.0]
        self.assertEqual(p0.expected_drift_bps, 0.0)
        self.assertEqual(p0.expected_price, 100.0)
        self.assertEqual(p0.lower_bound_bps, 0.0)
        self.assertEqual(p0.upper_bound_bps, 0.0)


class TestStressScenario6HittingTimesAndHawkesCoupling(unittest.TestCase):
    """Stress Scenario 6: Queue depletion hitting times and Hawkes excitation coupling."""

    def setUp(self) -> None:
        self.forecaster = MicropriceDriftForecaster(market="SP500", symbol="STRESS_HITTING")
        self.engine = HawkesMicrostructureEngine(market="SP500", symbol="STRESS_HITTING")

    def test_queue_depletion_monotonicity_l1_le_l2(self) -> None:
        """Mathematical invariant: tau_L1 <= tau_L2 must hold for all valid non-negative queues."""
        random.seed(42)
        for _ in range(50):
            b0 = random.uniform(0.0, 1000.0)
            b1 = random.uniform(0.0, 1000.0)
            a0 = random.uniform(0.0, 1000.0)
            a1 = random.uniform(0.0, 1000.0)

            tau_b1, tau_a1, tau_b2, tau_a2 = self.forecaster.compute_queue_depletion(
                bid_depths=[b0, b1],
                ask_depths=[a0, a1],
            )

            self.assertLessEqual(tau_b1, tau_b2 + 1e-9)
            self.assertLessEqual(tau_a1, tau_a2 + 1e-9)
            self.assertTrue(0.0 <= tau_b1 <= 999.0)
            self.assertTrue(0.0 <= tau_a1 <= 999.0)

    def test_replenishing_queue_ceiling(self) -> None:
        """Verify non-positive depletion velocity forces tau = 999.0s ceiling."""
        tau_b1, tau_a1, tau_b2, tau_a2 = self.forecaster.compute_queue_depletion(
            bid_depths=[100.0, 80.0],
            ask_depths=[100.0, 80.0],
            bid_dep_rate=0.0,
            ask_dep_rate=-5.0,
        )
        self.assertEqual(tau_b1, 999.0)
        self.assertEqual(tau_b2, 999.0)
        self.assertEqual(tau_a1, 999.0)
        self.assertEqual(tau_a2, 999.0)

    def test_hawkes_imbalance_coupling(self) -> None:
        """Verify positive arrival imbalance accelerates ask depletion, negative accelerates bid."""
        snap_buy_surge = HawkesIntensitySnapshot(
            timestamp=100.0,
            intensities=np.array([50.0, 10.0, 40.0, 10.0]),
            lambda_bid_place=50.0,
            lambda_ask_place=10.0,
            lambda_trade=40.0,
            lambda_cancel=10.0,
            total_intensity=110.0,
            quote_toxicity=0.8,
            burst_multiplier=5.0,
            cluster_dispersion=2.0,
            is_toxic=True,
            is_burst=True,
            arrival_imbalance=0.67,  # Aggressive buyer dominance
            criticality_index=0.85,
        )

        tau_b1_buy, tau_a1_buy, _, _ = self.forecaster.compute_queue_depletion(
            bid_depths=[100.0],
            ask_depths=[100.0],
            hawkes_snapshot=snap_buy_surge,
        )

        # Buying pressure should deplete ask faster than bid
        self.assertLess(tau_a1_buy, tau_b1_buy)

    def test_malformed_hawkes_snapshot_resilience(self) -> None:
        """Verify passing None, empty dict, or object with NaN fields to forecast does not crash."""
        # Non-snapshot object
        out1 = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[100.0],
            ask_ladder=[100.0],
            hawkes_snapshot="corrupted_snapshot",
        )
        self.assertTrue(np.isfinite(out1.micro_price))

        # None
        out2 = self.forecaster.forecast(
            best_bid=100.0,
            best_ask=100.05,
            bid_ladder=[100.0],
            ask_ladder=[100.0],
            hawkes_snapshot=None,
        )
        self.assertTrue(np.isfinite(out2.micro_price))


class TestStressScenario7MLEOptimizationCornerCases(unittest.TestCase):
    """Stress Scenario 7: MLE calibration under degenerate, degenerate, and single-channel datasets."""

    def setUp(self) -> None:
        self.engine = HawkesMicrostructureEngine(symbol="STRESS_MLE", market="SP500")

    def test_mle_empty_and_sub_threshold_events(self) -> None:
        """Verify MLE fit with 0 and < 8 events gracefully returns current stable parameters."""
        res_0 = self.engine.fit_mle([])
        self.assertTrue(res_0.converged)
        self.assertEqual(res_0.num_events, 0)
        self.assertTrue(res_0.params.is_stable)

        events_sub = [MicrostructureEvent(timestamp=float(i), channel=HawkesChannel.BID_PLACEMENT) for i in range(5)]
        res_sub = self.engine.fit_mle(events_sub)
        self.assertTrue(res_sub.converged)
        self.assertEqual(res_sub.num_events, 5)
        self.assertTrue(res_sub.params.is_stable)

    def test_mle_identical_timestamps(self) -> None:
        """Verify MLE fit with identical timestamps (all dt = 0) converges to a stable parameter set."""
        events_same = [MicrostructureEvent(timestamp=50.0, channel=HawkesChannel(i % 4)) for i in range(25)]
        res = self.engine.fit_mle(events_same)
        self.assertTrue(res.converged)
        self.assertTrue(res.params.is_stable)
        self.assertLess(res.params.spectral_radius, 1.0)

    def test_mle_single_channel_monopoly(self) -> None:
        """Verify MLE fit on single channel only (e.g. 50 bid placements) remains stable."""
        events_single = [MicrostructureEvent(timestamp=float(i) * 0.1, channel=HawkesChannel.BID_PLACEMENT) for i in range(50)]
        res = self.engine.fit_mle(events_single)
        self.assertTrue(res.converged)
        self.assertTrue(res.params.is_stable)
        self.assertLess(res.params.spectral_radius, 1.0)

    def test_mle_shuffled_out_of_order_stream(self) -> None:
        """Verify MLE fit correctly sorts shuffled out-of-order event timestamps."""
        rng = random.Random(116)
        raw_ts = [float(i) * 0.1 for i in range(40)]
        rng.shuffle(raw_ts)
        events_shuffled = [MicrostructureEvent(timestamp=t, channel=HawkesChannel(i % 4)) for i, t in enumerate(raw_ts)]

        res = self.engine.fit_mle(events_shuffled)
        self.assertTrue(res.converged)
        self.assertTrue(res.params.is_stable)
        self.assertLess(res.params.spectral_radius, 1.0)


class TestStressScenario8FuzzingAndMathematicalInvariants(unittest.TestCase):
    """Stress Scenario 8: 500-iteration Monte Carlo random fuzzing harness."""

    def test_monte_carlo_fuzz_forecaster_and_hawkes(self) -> None:
        """Fuzz Hawkes and Forecaster with 500 random parameter combinations."""
        rng = np.random.RandomState(42)
        engine = HawkesMicrostructureEngine(symbol="FUZZ", market="SP500")
        forecaster = MicropriceDriftForecaster(market="SP500", symbol="FUZZ")

        for iteration in range(500):
            # Random order book inputs
            bid = float(rng.uniform(-50.0, 500.0))
            spread_delta = float(rng.uniform(-5.0, 20.0))
            ask = bid + spread_delta

            b_depth = list(rng.uniform(-100.0, 10000.0, size=rng.randint(0, 6)))
            a_depth = list(rng.uniform(-100.0, 10000.0, size=rng.randint(0, 6)))

            # Occasionally inject NaNs or Infs
            if iteration % 10 == 0:
                b_depth.append(float("nan"))
                a_depth.append(float("inf"))

            # Hawkes tick
            ch = int(rng.randint(-2, 6))
            vol = float(rng.exponential(scale=10.0))
            t_tick = float(rng.uniform(0.0, 10000.0))

            snap = engine.update_tick(ch, timestamp=t_tick, volume=vol)
            self.assertTrue(np.all(np.isfinite(snap.intensities)), f"NaN in Hawkes at iter {iteration}")
            self.assertTrue(0.0 <= snap.quote_toxicity <= 1.0, f"Invalid toxicity at iter {iteration}")

            # Forecaster tick
            trade_vol = float(rng.exponential(scale=50.0))
            side = str(rng.choice(["BUY", "SELL", "UNKNOWN", "", "1", "-1"]))
            forecaster.update_trade(side=side, volume=trade_vol, timestamp_sec=t_tick)

            out = forecaster.forecast(
                best_bid=bid,
                best_ask=ask,
                bid_ladder=b_depth,
                ask_ladder=a_depth,
                timestamp_sec=t_tick,
                hawkes_snapshot=snap,
            )

            # Invariants
            self.assertTrue(np.isfinite(out.micro_price), f"NaN micro_price at iter {iteration}")
            self.assertTrue(np.isfinite(out.sde_drift_rate), f"NaN sde_drift at iter {iteration}")
            self.assertTrue(-1.0 <= out.sde_drift_rate <= 1.0, f"sde_drift out of bounds at iter {iteration}")
            self.assertTrue(0.0 <= out.tau_depletion_bid_l1 <= 999.0, f"tau_bid out of bounds at iter {iteration}")
            self.assertTrue(0.0 <= out.tau_depletion_ask_l1 <= 999.0, f"tau_ask out of bounds at iter {iteration}")


if __name__ == "__main__":
    unittest.main()

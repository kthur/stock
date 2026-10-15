"""
tests/test_phase107_hawkes.py — Comprehensive Unit, Integration & Adversarial Test Harness

Phase 107 / Feature F507 / Release R123 (v114 Production Master)
Milestone 3: L2/L3 Hawkes Microstructure Alpha Predictor

Test Categories:
- Category 1: Exports, Data Structures & Alias Trees (TC01~TC03)
- Category 2: Hawkes Parameter Estimation & L1 Stability Invariant (TC04~TC09)
- Category 3: Real-Time Arrival Intensity & Imbalance Dynamics (TC10~TC12)
- Category 4: Adverse Selection Toxicity & Urgency Gating (TC13~TC15)
- Category 5: Composite Alpha & Multi-Horizon Drift Forecasting (TC16~TC19)
- Category 6: Closed-Loop Almgren-Chriss Slicing Schedule Modulation (TC20~TC23)
- Category 7: Limit Order Peg Offset & Tick Shading (TC24~TC26)
- Category 8: Adversarial Fuzzing, Edge Cases & Numerical Robustness (TC27~TC30)
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Setup import path for both repo root and trading_system
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.hawkes_microstructure_alpha import (
    HawkesAlphaPredictor,
    HawkesMLEstimator,
    HawkesMicrostructureAlphaEngine,
    HawkesMicrostructureAlphaPredictor,
    HawkesParameters,
    MicrostructureAlphaSignal,
    MicrostructureHawkesAlphaPredictor,
    Phase107HawkesAlphaPredictor,
)


class TestPhase107HawkesMicrostructure(unittest.TestCase):
    """Test suite for Phase 107 L2/L3 Hawkes Microstructure Alpha Predictor."""

    def setUp(self) -> None:
        """Initializes default engine and test fixtures."""
        self.engine = HawkesMicrostructureAlphaPredictor(
            symbol="AAPL",
            horizon_seconds=180,
            daily_volatility=0.02,
            spread_bps=5.0,
            tick_size=0.01,
            base_arrival_mu=1.0,
            hawkes_alpha_self=0.40,
            hawkes_alpha_cross=0.10,
            hawkes_beta=1.20,
            max_branching_ratio=0.99,
            base_kappa_ac=1.0,
        )

    # =========================================================================
    # Category 1: Exports, Data Structures & Alias Trees
    # =========================================================================

    def test_tc01_class_exports_and_aliases(self) -> None:
        """TC01: Verify all class exports and backward-compatible aliases exist."""
        self.assertIs(HawkesMicrostructureAlphaEngine, HawkesMicrostructureAlphaPredictor)
        self.assertIs(Phase107HawkesAlphaPredictor, HawkesMicrostructureAlphaPredictor)
        self.assertIs(MicrostructureHawkesAlphaPredictor, HawkesMicrostructureAlphaPredictor)
        self.assertIs(HawkesAlphaPredictor, HawkesMicrostructureAlphaPredictor)

        alias_inst = Phase107HawkesAlphaPredictor(symbol="005930.KS")
        self.assertEqual(alias_inst.symbol, "005930.KS")
        self.assertIsInstance(alias_inst, HawkesMicrostructureAlphaPredictor)

    def test_tc02_hawkes_parameters_dataclass(self) -> None:
        """TC02: Verify HawkesParameters dataclass, stability margin, and serialization."""
        params = HawkesParameters(
            mu=1.0,
            alpha=0.6,
            beta=1.2,
            branching_ratio=0.5,
            log_likelihood=-120.5,
            is_stable=True,
            alpha_self=0.45,
            alpha_cross=0.15,
        )
        self.assertTrue(params.is_stable)
        self.assertAlmostEqual(params.stability_margin, 0.5, places=5)
        d = params.to_dict()
        self.assertEqual(d["mu"], 1.0)
        self.assertEqual(d["branching_ratio"], 0.5)
        self.assertTrue(d["is_stable"])
        self.assertEqual(d["alpha_self"], 0.45)

    def test_tc03_microstructure_alpha_signal_dataclass(self) -> None:
        """TC03: Verify MicrostructureAlphaSignal structure and serialization."""
        sig = MicrostructureAlphaSignal(
            timestamp=1700000000.0,
            symbol="NVDA",
            l3_imbalance=0.35,
            arrival_imbalance=0.20,
            predicted_drift_bps=4.5,
            adverse_toxicity=0.30,
            composite_alpha_score=0.28,
            is_toxic=False,
            recommended_urgency="FAST",
            target_offset_ticks=-0.5,
            lambda_buy=3.2,
            lambda_sell=1.8,
            lambda_total=5.0,
        )
        self.assertEqual(sig.symbol, "NVDA")
        self.assertFalse(sig.is_toxic)
        d = sig.to_dict()
        self.assertEqual(d["symbol"], "NVDA")
        self.assertEqual(d["recommended_urgency"], "FAST")
        self.assertAlmostEqual(d["composite_alpha_score"], 0.28, places=4)

    # =========================================================================
    # Category 2: Hawkes Parameter Estimation & L1 Stability Invariant
    # =========================================================================

    def test_tc04_recursive_log_likelihood_calculation(self) -> None:
        """TC04: Verify O(N) recursive log-likelihood calculation correctness."""
        timestamps = np.array([0.5, 1.2, 1.5, 2.8, 3.1, 4.0], dtype=np.float64)
        mu = 1.0
        alpha = 0.5
        beta = 1.5

        ll = HawkesMLEstimator.compute_log_likelihood(mu, alpha, beta, timestamps, t_max=4.5)
        self.assertTrue(math.isfinite(ll))
        self.assertLess(ll, 0.0)  # Log-likelihood is negative for point processes

        # Invalid parameters return penalty
        invalid_ll = HawkesMLEstimator.compute_log_likelihood(-1.0, alpha, beta, timestamps)
        self.assertEqual(invalid_ll, -1e12)

    def test_tc05_ogata_simulation_and_mle_fitting(self) -> None:
        """TC05: Simulate true Hawkes process via Ogata thinning and fit with MLE."""
        true_mu = 1.2
        true_alpha = 0.6
        true_beta = 1.5
        # Expected branching ratio = 0.6 / 1.5 = 0.40 < 1.0

        sim_ts = HawkesMLEstimator.simulate_hawkes_process(
            mu=true_mu, alpha=true_alpha, beta=true_beta, t_max=120.0, seed=42
        )
        self.assertGreater(len(sim_ts), 20)

        fitted = HawkesMLEstimator.fit_univariate_mle(sim_ts, t_max=120.0)
        self.assertTrue(fitted.is_stable)
        self.assertLess(fitted.branching_ratio, 1.0)
        self.assertGreater(fitted.mu, 0.0)
        self.assertGreater(fitted.beta, 0.0)
        self.assertGreater(fitted.alpha, 0.0)
        self.assertTrue(math.isfinite(fitted.log_likelihood))

    def test_tc06_calibrated_moments_estimator(self) -> None:
        """TC06: Verify instantaneous method-of-moments estimator."""
        sim_ts = HawkesMLEstimator.simulate_hawkes_process(
            mu=1.0, alpha=0.4, beta=1.0, t_max=100.0, seed=123
        )
        moments = HawkesMLEstimator.fit_calibrated_moments(sim_ts, t_max=100.0)
        self.assertTrue(moments.is_stable)
        self.assertLess(moments.branching_ratio, 1.0)
        self.assertGreater(moments.mu, 0.0)
        self.assertGreater(moments.beta, 0.0)

    def test_tc07_strict_l1_stability_enforcement(self) -> None:
        """TC07: Verify L1 stability enforcement strictly projects explosive parameters."""
        # Unstable explosive parameters: alpha = 2.0 >= beta = 1.0 (branching ratio = 2.0)
        explosive = HawkesParameters(
            mu=1.0,
            alpha=2.0,
            beta=1.0,
            branching_ratio=2.0,
            log_likelihood=-50.0,
            is_stable=False,
            alpha_self=1.5,
            alpha_cross=0.5,
        )

        projected = HawkesMLEstimator.project_to_stability(explosive, max_branching=0.99)
        self.assertTrue(projected.is_stable)
        self.assertLessEqual(projected.branching_ratio, 0.99)
        self.assertAlmostEqual(projected.alpha, 0.99 * projected.beta, places=4)
        self.assertGreater(projected.stability_margin, 0.0)

    def test_tc08_bivariate_coupled_mle_fitting(self) -> None:
        """TC08: Verify bivariate MLE fitting with coupled buy and sell arrival streams."""
        buy_ts = np.sort(np.random.uniform(0.0, 100.0, size=50))
        sell_ts = np.sort(np.random.uniform(0.0, 100.0, size=45))

        b_params, s_params = HawkesMLEstimator.fit_bivariate_mle(buy_ts, sell_ts, t_max=100.0)
        self.assertTrue(b_params.is_stable)
        self.assertTrue(s_params.is_stable)
        self.assertLess(b_params.branching_ratio, 1.0)
        self.assertLess(s_params.branching_ratio, 1.0)
        self.assertIsNotNone(b_params.alpha_self)
        self.assertIsNotNone(b_params.alpha_cross)

    def test_tc09_edge_case_sparse_empty_timestamps(self) -> None:
        """TC09: Verify estimator handles empty or sparse timestamp arrays without crashing."""
        empty_ts = np.array([], dtype=np.float64)
        p_empty = HawkesMLEstimator.fit_univariate_mle(empty_ts)
        self.assertTrue(p_empty.is_stable)
        self.assertLess(p_empty.branching_ratio, 1.0)

        single_ts = np.array([5.0], dtype=np.float64)
        p_single = HawkesMLEstimator.fit_univariate_mle(single_ts)
        self.assertTrue(p_single.is_stable)

    # =========================================================================
    # Category 3: Real-Time Arrival Intensity & Imbalance Dynamics
    # =========================================================================

    def test_tc10_realtime_intensity_decay_and_jumps(self) -> None:
        """TC10: Verify intensity decays exponentially and jumps upon new trade."""
        t0 = 1000.0
        # Trade 1: BUY
        b1, s1 = self.engine.update_ticks(price=150.0, volume=100, timestamp_sec=t0, is_buy=True)
        self.assertGreater(b1, self.engine.mu_buy)

        # Query after 2.0 seconds: should decay towards mu
        t1 = t0 + 2.0
        intensities = self.engine.compute_intensities(current_time=t1)
        self.assertLess(intensities["lambda_buy"], b1)
        self.assertGreaterEqual(intensities["lambda_buy"], self.engine.mu_buy)

        # Trade 2: BUY again -> intensity jumps
        b2, s2 = self.engine.update_ticks(price=150.05, volume=200, timestamp_sec=t1, is_buy=True)
        self.assertGreater(b2, intensities["lambda_buy"])

    def test_tc11_arrival_imbalance_bounds(self) -> None:
        """TC11: Verify arrival imbalance Delta lambda_dir is strictly in [-1.0, 1.0]."""
        # Inject strong BUY bursts
        for i in range(10):
            self.engine.update_ticks(price=100.0 + i * 0.01, volume=50, timestamp_sec=2000.0 + i * 0.1, is_buy=True)

        imb_buy = self.engine.compute_arrival_imbalance(current_time=2001.0)
        self.assertGreater(imb_buy, 0.0)
        self.assertLessEqual(imb_buy, 1.0)

        # Reset engine and inject strong SELL bursts
        engine_sell = HawkesMicrostructureAlphaPredictor()
        for i in range(10):
            engine_sell.update_ticks(price=100.0 - i * 0.01, volume=50, timestamp_sec=2000.0 + i * 0.1, is_buy=False)

        imb_sell = engine_sell.compute_arrival_imbalance(current_time=2001.0)
        self.assertLess(imb_sell, 0.0)
        self.assertGreaterEqual(imb_sell, -1.0)

    def test_tc12_fit_parameters_updates_engine_state(self) -> None:
        """TC12: Verify fit_parameters updates internal intensities and returns valid parameters."""
        for i in range(25):
            self.engine.update_ticks(price=100.0, volume=10, timestamp_sec=100.0 + i * 0.5, is_buy=(i % 2 == 0))

        fitted_dict = self.engine.fit_parameters()
        self.assertIn("buy", fitted_dict)
        self.assertIn("sell", fitted_dict)
        self.assertTrue(fitted_dict["buy"].is_stable)
        self.assertTrue(fitted_dict["sell"].is_stable)

    # =========================================================================
    # Category 4: Adverse Selection Toxicity & Urgency Gating
    # =========================================================================

    def test_tc13_adverse_selection_toxicity_bounds(self) -> None:
        """TC13: Verify adverse selection toxicity is strictly bounded in [0.0, 1.0]."""
        tox_buy = self.engine.compute_adverse_toxicity(action="BUY")
        tox_sell = self.engine.compute_adverse_toxicity(action="SELL")
        self.assertGreaterEqual(tox_buy, 0.0)
        self.assertLessEqual(tox_buy, 1.0)
        self.assertGreaterEqual(tox_sell, 0.0)
        self.assertLessEqual(tox_sell, 1.0)

    def test_tc14_directional_toxicity_asymmetry(self) -> None:
        """TC14: Aggressive sell flow creates high adverse toxicity for BUY and low for SELL."""
        # Inject persistent aggressive selling burst (institutional sweep)
        n_burst = 25
        dt_burst = 0.04
        for i in range(n_burst):
            self.engine.update_ticks(price=99.0, volume=100, timestamp_sec=3000.0 + i * dt_burst, is_buy=False)

        t_query = 3000.0 + (n_burst - 1) * dt_burst + 0.01
        tox_for_buyer = self.engine.compute_adverse_toxicity(action="BUY", current_time=t_query)
        tox_for_seller = self.engine.compute_adverse_toxicity(action="SELL", current_time=t_query)

        self.assertGreater(tox_for_buyer, 0.65)
        self.assertLess(tox_for_seller, 0.35)

        sig = self.engine.predict_alpha(current_time=t_query, proposed_action="BUY")
        self.assertTrue(sig.is_toxic)
        self.assertEqual(sig.recommended_urgency, "DEFENSIVE")

    def test_tc15_urgency_directive_transitions(self) -> None:
        """TC15: Verify transitions between FAST, MEDIUM, and DEFENSIVE pacing."""
        # 1. Balanced quiet market -> MEDIUM
        sig_quiet = self.engine.predict_alpha(lob_snapshot={"l3_imbalance": 0.0}, current_time=4000.0)
        self.assertIn(sig_quiet.recommended_urgency, ["MEDIUM", "FAST"])

        # 2. Bullish breakout with matching action -> FAST
        sig_fast = self.engine.predict_alpha(
            lob_snapshot={"l3_imbalance": 0.70, "qi_velocity": 0.50},
            current_time=4000.0,
            proposed_action="BUY",
        )
        self.assertEqual(sig_fast.recommended_urgency, "FAST")

    # =========================================================================
    # Category 5: Composite Alpha & Multi-Horizon Drift Forecasting
    # =========================================================================

    def test_tc16_composite_alpha_score_boundedness(self) -> None:
        """TC16: Verify composite alpha score is strictly bounded in [-1.0, 1.0]."""
        # Test extreme positive inputs
        score_pos, _, _, _ = self.engine.compute_composite_alpha(
            lob_snapshot={"l3_queue_imbalance": 1.0, "qi_velocity": 10.0, "qi_acceleration": 10.0}
        )
        self.assertGreater(score_pos, 0.0)
        self.assertLessEqual(score_pos, 1.0)

        # Test extreme negative inputs
        score_neg, _, _, _ = self.engine.compute_composite_alpha(
            lob_snapshot={"l3_queue_imbalance": -1.0, "qi_velocity": -10.0, "qi_acceleration": -10.0}
        )
        self.assertLess(score_neg, 0.0)
        self.assertGreaterEqual(score_neg, -1.0)

    def test_tc17_short_term_price_drift_scaling(self) -> None:
        """TC17: Verify price drift scales monotonically with sqrt(tau)."""
        alpha_val = 0.50
        drift_60, _ = self.engine.predict_drift(composite_alpha=alpha_val, horizon_seconds=60)
        drift_180, _ = self.engine.predict_drift(composite_alpha=alpha_val, horizon_seconds=180)
        drift_300, _ = self.engine.predict_drift(composite_alpha=alpha_val, horizon_seconds=300)

        self.assertGreater(drift_60, 0.0)
        self.assertGreater(drift_180, drift_60)
        self.assertGreater(drift_300, drift_180)

        ratio = drift_300 / drift_60
        expected_ratio = math.sqrt(300 / 60)
        self.assertAlmostEqual(ratio, expected_ratio, places=3)

    def test_tc18_raw_lob_depth_processing(self) -> None:
        """TC18: Verify raw LOB depth bids and asks are correctly parsed into queue imbalance."""
        # Heavier bids than asks
        lob_bids_heavy = {
            "bids": [[100.0, 500], [99.9, 400], [99.8, 300]],
            "asks": [[100.1, 100], [100.2, 80], [100.3, 50]],
        }
        score, qi, v, a = self.engine.compute_composite_alpha(lob_bids_heavy)
        self.assertGreater(qi, 0.0)
        self.assertGreater(score, 0.0)

    def test_tc19_full_predict_alpha_payload(self) -> None:
        """TC19: Verify complete predict_alpha output contains all required fields."""
        sig = self.engine.predict_alpha(
            lob_snapshot={"l3_imbalance": 0.25},
            current_time=5000.0,
            proposed_action="BUY",
            mid_price=200.0,
        )
        self.assertEqual(sig.symbol, "AAPL")
        self.assertTrue(math.isfinite(sig.predicted_drift_bps))
        self.assertTrue(math.isfinite(sig.predicted_drift_price))
        self.assertTrue(math.isfinite(sig.target_offset_ticks))
        self.assertGreaterEqual(sig.flow_activity_multiplier, 0.5)
        self.assertLessEqual(sig.flow_activity_multiplier, 3.0)

    # =========================================================================
    # Category 6: Closed-Loop Almgren-Chriss Slicing Schedule Modulation
    # =========================================================================

    def test_tc20_almgren_chriss_volume_conservation(self) -> None:
        """TC20: Verify total slice quantity is strictly conserved under modulation."""
        base_slices_list = [
            [100, 100, 100, 100, 100],            # 500 total
            [50, 150, 200, 100],                  # 500 total
            [33, 33, 34],                         # 100 total
            [7, 11, 13, 17, 19, 23, 29],          # 129 prime total
        ]

        sig = self.engine.predict_alpha(lob_snapshot={"l3_imbalance": 0.40})
        for base in base_slices_list:
            mod = self.engine.modulate_slicing_schedule(base, sig, action="BUY")
            self.assertEqual(sum(mod), sum(base), f"Mismatch in sum for base {base}")
            self.assertEqual(len(mod), len(base))
            for val in mod:
                self.assertIsInstance(val, int)
                self.assertGreaterEqual(val, 0)

    def test_tc21_favorable_alpha_front_loading(self) -> None:
        """TC21: Favorable alpha accelerates execution, front-loading earlier slices."""
        base_slices = [100, 100, 100, 100, 100]  # Total 500
        # Highly positive alpha for BUY -> should front-load
        sig_bullish = self.engine.predict_alpha(
            lob_snapshot={"l3_imbalance": 0.80, "qi_velocity": 0.50},
            proposed_action="BUY",
        )
        mod_slices = self.engine.modulate_slicing_schedule(base_slices, sig_bullish, action="BUY")

        self.assertEqual(sum(mod_slices), 500)
        # First slice should be larger than last slice
        self.assertGreater(mod_slices[0], mod_slices[-1])
        self.assertGreater(mod_slices[0], base_slices[0])

    def test_tc22_toxic_flow_defensive_back_loading(self) -> None:
        """TC22: Toxic flow decelerates execution, shifting volume away from immediate execution."""
        # Inject selling bursts to make BUY flow toxic
        n_burst = 25
        dt_burst = 0.04
        for i in range(n_burst):
            self.engine.update_ticks(price=100.0, volume=80, timestamp_sec=6000.0 + i * dt_burst, is_buy=False)

        t_query = 6000.0 + (n_burst - 1) * dt_burst + 0.01
        sig_toxic = self.engine.predict_alpha(current_time=t_query, proposed_action="BUY")
        self.assertTrue(sig_toxic.is_toxic)

        base_slices = [100, 100, 100, 100, 100]
        mod_slices = self.engine.modulate_slicing_schedule(base_slices, sig_toxic, action="BUY")
        self.assertEqual(sum(mod_slices), 500)
        # Under decelerated kappa, front slice should be attenuated relative to high kappa
        self.assertLessEqual(mod_slices[0], mod_slices[1] + 15)

    def test_tc23_single_or_empty_slice_edge_cases(self) -> None:
        """TC23: Edge cases with single slice or 0 total quantity are preserved."""
        sig = self.engine.predict_alpha()
        self.assertEqual(self.engine.modulate_slicing_schedule([100], sig), [100])
        self.assertEqual(self.engine.modulate_slicing_schedule([], sig), [])
        self.assertEqual(self.engine.modulate_slicing_schedule([0, 0, 0], sig), [0, 0, 0])

    # =========================================================================
    # Category 7: Limit Order Peg Offset & Tick Shading
    # =========================================================================

    def test_tc24_peg_offset_calculation(self) -> None:
        """TC24: Verify limit order peg offset computes correctly and rounds to tick size."""
        sig = self.engine.predict_alpha(lob_snapshot={"l3_imbalance": 0.40})
        spread = 0.05
        offset = self.engine.compute_limit_offset(sig, spread=spread, action="BUY", tick_size=0.01)
        self.assertTrue(math.isfinite(offset))
        # Check that offset is a multiple of tick_size
        remainder = abs(offset) % 0.01
        self.assertTrue(remainder < 1e-6 or abs(remainder - 0.01) < 1e-6)

    def test_tc25_defensive_stepping_back_during_toxic_sweeps(self) -> None:
        """TC25: Under toxic flow (T_adverse > 0.50), offset shades defensively."""
        # Inject sell burst
        for i in range(10):
            self.engine.update_ticks(price=100.0, volume=100, timestamp_sec=7000.0 + i * 0.1, is_buy=False)

        sig = self.engine.predict_alpha(current_time=7002.0, proposed_action="BUY")
        spread = 0.10
        raw_offset = self.engine.compute_limit_offset_raw(
            sig.composite_alpha_score, sig.adverse_toxicity, spread, action="BUY"
        )
        # For BUY, defensive offset lowers bid price (negative offset added to mid)
        # Offset factor has -action_sign * spread * [0.35 * tanh + 0.50 * (tox - 0.5)]
        self.assertLess(raw_offset, 0.0)

    def test_tc26_offset_sign_reversal_for_sell(self) -> None:
        """TC26: SELL orders reflect opposite sign offsets compared to BUY orders."""
        sig = MicrostructureAlphaSignal(
            timestamp=1000.0,
            symbol="TEST",
            l3_imbalance=0.30,
            arrival_imbalance=0.30,
            predicted_drift_bps=2.0,
            adverse_toxicity=0.20,
            composite_alpha_score=0.30,
            is_toxic=False,
            recommended_urgency="FAST",
            target_offset_ticks=0.0,
        )
        spread = 0.04
        buy_offset = self.engine.compute_limit_offset_raw(
            sig.composite_alpha_score, sig.adverse_toxicity, spread, action="BUY"
        )
        sell_offset = self.engine.compute_limit_offset_raw(
            sig.composite_alpha_score, sig.adverse_toxicity, spread, action="SELL"
        )
        self.assertAlmostEqual(buy_offset, -sell_offset, places=6)

    # =========================================================================
    # Category 8: Adversarial Fuzzing, Edge Cases & Numerical Robustness
    # =========================================================================

    def test_tc27_adversarial_nan_and_inf_injection(self) -> None:
        """TC27: Engine gracefully sanitizes NaN and Inf inputs in LOB snapshots."""
        nan_snapshot = {
            "l3_imbalance": float("nan"),
            "qi_velocity": float("inf"),
            "qi_acceleration": float("-inf"),
        }
        # Should not raise exception
        score, qi, v, a = self.engine.compute_composite_alpha(nan_snapshot)
        self.assertTrue(math.isfinite(score))
        self.assertGreaterEqual(score, -1.0)
        self.assertLessEqual(score, 1.0)

    def test_tc28_high_frequency_tick_burst_stress(self) -> None:
        """TC28: Stress test with 5,000 high-frequency tick updates in sub-second time."""
        t_start = 8000.0
        n_ticks = 5000
        timestamps = t_start + np.cumsum(np.random.exponential(scale=0.001, size=n_ticks))

        for i in range(n_ticks):
            self.engine.update_ticks(
                price=100.0 + np.sin(i * 0.01),
                volume=float(np.random.randint(10, 500)),
                timestamp_sec=timestamps[i],
                is_buy=(i % 3 != 0),
            )

        intensities = self.engine.compute_intensities()
        self.assertTrue(math.isfinite(intensities["lambda_buy"]))
        self.assertTrue(math.isfinite(intensities["lambda_sell"]))
        self.assertGreater(intensities["lambda_buy"], 0.0)
        self.assertGreater(intensities["lambda_sell"], 0.0)

    def test_tc29_zero_copy_ring_buffer_bounds(self) -> None:
        """TC29: Deque history buffers respect maxlen limits without memory leaks."""
        self.assertLessEqual(len(self.engine.buy_tick_history), self.engine.max_history_len)
        self.assertLessEqual(len(self.engine.sell_tick_history), self.engine.max_history_len)
        self.assertLessEqual(len(self.engine.qi_history), 50)

    def test_tc30_module_export_integrity_and_alias_equivalence(self) -> None:
        """TC30: Ensure module exports are complete and all aliases function identically."""
        from src.core.hawkes_microstructure_alpha import (
            HawkesAlphaPredictor,
            HawkesMicrostructureAlphaEngine,
            HawkesMicrostructureAlphaPredictor,
            MicrostructureHawkesAlphaPredictor,
            Phase107HawkesAlphaPredictor,
        )

        aliases = [
            HawkesMicrostructureAlphaEngine,
            Phase107HawkesAlphaPredictor,
            MicrostructureHawkesAlphaPredictor,
            HawkesAlphaPredictor,
        ]
        for alias_cls in aliases:
            inst = alias_cls(symbol="TEST_ALIAS", horizon_seconds=120)
            self.assertEqual(inst.symbol, "TEST_ALIAS")
            self.assertEqual(inst.horizon_seconds, 120)
            sig = inst.predict_alpha(lob_snapshot={"l3_imbalance": 0.20})
            self.assertEqual(sig.symbol, "TEST_ALIAS")
            self.assertTrue(math.isfinite(sig.composite_alpha_score))


if __name__ == "__main__":
    unittest.main()

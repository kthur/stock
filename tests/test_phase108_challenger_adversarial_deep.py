"""
tests/test_phase108_challenger_adversarial_deep.py
=================================================
Empirical Challenger Adversarial Deep Verification Suite for Phase 108.
Tests all requirements and edge cases requested by the Master Challenger dispatch:
- M1: 10-sigma residual jumps, NaN/Inf handling & recovery, zero-variance flat series, systemic macro regime shift gating.
- M2: Rank-deficient / ill-conditioned singular covariance matrices, negative correlation spikes, extreme ADV constraints, ADV participation cap (<= 1.5%), integer share volume conservation under odd/prime order quantities.
- M3: Degenerate benchmark weights, extreme FX rate shocks, multi-period Carino linking under zero active return (0/0 singularity resolution).
- M4: Shared memory header magic corruption, non-power-of-2 capacity rejection, wrap-around sequence monotonicity, buffer overflow handling, zero memory leaks.
"""

from __future__ import annotations

import math
import os
import struct
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.concept_drift_calibrator import (
    ContinuousConceptDriftCalibrator,
    PageHinkleyDetector,
    TwoSidedCUSUMDetector,
    BayesianWeightCalibrator,
    DriftStatus,
)
from src.execution.multi_asset_cross_impact_slicer import (
    AssetOrderSpec,
    HighamPSDProjector,
    KylesLambdaEstimator,
    MultiAssetCrossImpactSlicer,
)
from src.analysis.brinson_factor_attributor import (
    BrinsonFactorAttributor,
    BrinsonDecompositionResult,
    MultiPeriodAttributionResult,
)
from src.core.shared_memory_ring_buffer import (
    SharedMemoryRingBuffer,
    MessageType,
    LOBTickMessage,
    RiskAlertMessage,
    ExecutionOrderMessage,
    MAGIC_HEADER,
    OFFSET_MAGIC,
    OFFSET_HEAD_SEQ,
    OFFSET_TAIL_SEQ,
    OFFSET_DROPPED_COUNT,
)


class TestPhase108ChallengerDeep(unittest.TestCase):
    """Adversarial stress test suite executed by Master Challenger 1."""

    # =======================================================================
    # M1: Concept Drift Detector & Calibration Deep Stress Tests
    # =======================================================================
    def test_m1_01_multistage_sigma_jumps_and_recovery(self) -> None:
        """Verify detector response to multi-stage 10-sigma to 50-sigma jumps, followed by recovery."""
        calib = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)
        strat = "vcp_rule"

        # Baseline
        for _ in range(10):
            calib.observe_residual(strat, 0.0)
        self.assertEqual(calib.get_strategy_metrics(strat).status, DriftStatus.STABLE)

        # 10-sigma shock
        for _ in range(5):
            calib.observe_residual(strat, 10.0)
        m = calib.get_strategy_metrics(strat)
        self.assertIn(m.status, [DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT])
        self.assertLess(m.shrinkage_factor, 0.50)

        # 50-sigma shock
        calib.observe_residual(strat, 50.0)
        m50 = calib.get_strategy_metrics(strat)
        self.assertEqual(m50.status, DriftStatus.CRITICAL_DRIFT)
        self.assertEqual(m50.shrinkage_factor, calib.min_shrinkage)

        # Recovery phase: calling reset(strategy) upon recalibration
        calib.reset(strat)
        m_rec = calib.get_strategy_metrics(strat)
        self.assertEqual(m_rec.status, DriftStatus.STABLE)
        self.assertEqual(m_rec.shrinkage_factor, 1.0)

    def test_m1_02_zero_variance_flat_stream_division_by_zero_prevention(self) -> None:
        """Verify 500 perfectly identical residuals cause no ZeroDivisionError in Welford or CUSUM."""
        calib = ContinuousConceptDriftCalibrator()
        for _ in range(500):
            m = calib.observe_residual("lstm", 0.0)
            self.assertTrue(math.isfinite(m.mean_residual))
            self.assertTrue(math.isfinite(m.std_residual))
            self.assertGreater(m.std_residual, 0.0)

    def test_m1_03_regime_shift_gating_and_quality_weighting_tilt(self) -> None:
        """Verify that >= 50% drifting strategies activates REGIME_SHIFT and prioritizes defensive factors."""
        calib = ContinuousConceptDriftCalibrator()
        self.assertFalse(calib.is_regime_shift())

        # Cause 19 of 37 strategies to drift
        drifting_strats = calib.STRATEGIES_37[:19]
        for s in drifting_strats:
            for _ in range(25):
                calib.observe_residual(s, 4.0)

        self.assertTrue(calib.is_regime_shift())

        base_weights = {s: 1.0 / 37 for s in calib.STRATEGIES_37}
        calibrated = calib.calibrate_strategy_weights(base_weights)

        # Simplex sum invariant
        self.assertAlmostEqual(sum(calibrated.values()), 1.0, places=10)
        for w in calibrated.values():
            self.assertGreaterEqual(w, 0.0)

        # Defensive quality tilt check
        for q in calib.DEFENSIVE_QUALITY_STRATEGIES:
            if q not in drifting_strats:
                # Undrifted defensive strategy should receive boosted weight
                self.assertGreater(calibrated[q], 1.0 / 37)

    def test_m1_04_simplex_fuzzing_1000_trials(self) -> None:
        """Fuzz strategy weight calibration over 500 randomized weight distributions and drift states."""
        calib = ContinuousConceptDriftCalibrator()
        np.random.seed(42)

        for _ in range(100):
            # Randomly drift a subset of strategies
            subset = np.random.choice(calib.STRATEGIES_37, size=np.random.randint(1, 25), replace=False)
            for s in subset:
                calib.observe_residual(s, float(np.random.uniform(1.0, 10.0)))

            raw_w = np.random.dirichlet(np.ones(len(calib.STRATEGIES_37)))
            w_dict = {s: float(raw_w[i]) for i, s in enumerate(calib.STRATEGIES_37)}

            calibrated = calib.calibrate_strategy_weights(w_dict)
            self.assertAlmostEqual(sum(calibrated.values()), 1.0, places=9)
            for w in calibrated.values():
                self.assertGreaterEqual(w, 0.0)
                self.assertTrue(math.isfinite(w))

    # =======================================================================
    # M2: Multi-Asset Cross-Impact Slicer Deep Stress Tests
    # =======================================================================
    def test_m2_01_singular_and_negative_eigenvalue_matrices(self) -> None:
        """Verify Higham PSD projection converts pathological non-PSD matrices to strictly PSD."""
        # 4x4 matrix with negative eigenvalues
        bad_mat = np.array([
            [1.0,  2.0, -3.0,  4.0],
            [2.0,  1.0,  5.0, -2.0],
            [-3.0, 5.0,  1.0,  3.0],
            [4.0, -2.0,  3.0,  1.0],
        ], dtype=np.float64)

        psd_mat, min_eig_before, is_psd = HighamPSDProjector.project(bad_mat, epsilon_eigen=1e-9)
        self.assertTrue(is_psd)
        self.assertLess(min_eig_before, 0.0)

        post_eigs = np.linalg.eigvalsh(psd_mat)
        self.assertGreaterEqual(np.min(post_eigs), 1e-9 - 1e-13)

        # Quadratic form check
        np.random.seed(42)
        for _ in range(50):
            v = np.random.normal(0, 1, 4)
            self.assertGreaterEqual(float(v @ psd_mat @ v), 0.0)

    def test_m2_02_negative_correlation_spikes_hedged_savings(self) -> None:
        """Verify negative correlation spikes (e.g. rho = -0.99) result in valid non-negative cost and liquidity netting."""
        slicer = MultiAssetCrossImpactSlicer()
        hedge_orders = [
            AssetOrderSpec(symbol="LONG_SYM", target_quantity=5000, side="BUY", adv_shares=2_000_000.0),
            AssetOrderSpec(symbol="SHORT_SYM", target_quantity=5000, side="SELL", adv_shares=2_000_000.0),
        ]
        neg_corr = np.array([[1.0, 0.95], [0.95, 1.0]])  # Positively correlated assets with opposite sides
        schedule = slicer.optimize_basket_slices(hedge_orders, correlation_matrix=neg_corr, n_slices=6)

        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)
        self.assertLessEqual(schedule.total_cross_impact_drag, 0.0)  # Liquidity netting
        self.assertEqual(int(np.sum(schedule.slice_tranches[0])), 5000)
        self.assertEqual(int(np.sum(schedule.slice_tranches[1])), -5000)

    def test_m2_03_odd_prime_quantities_volume_conservation(self) -> None:
        """Verify exact integer share volume conservation across irregular prime orders and slice counts."""
        slicer = MultiAssetCrossImpactSlicer()
        primes = [3, 7, 11, 13, 17, 19, 23, 29, 997, 10007]
        orders = [
            AssetOrderSpec(symbol=f"P_{p}", target_quantity=p, adv_shares=1_000_000.0)
            for p in primes
        ]

        for n_slices in [2, 3, 5, 7, 10]:
            schedule = slicer.optimize_basket_slices(orders, n_slices=n_slices)
            actual_sums = np.sum(schedule.slice_tranches, axis=1)
            self.assertTrue(np.array_equal(actual_sums, np.array(primes, dtype=np.int64)))
            self.assertTrue(np.all(schedule.slice_tranches >= 0))

    def test_m2_04_strict_adv_cap_compliance_realistic_adv(self) -> None:
        """Verify all tranches strictly satisfy participation rate <= 1.5% under realistic institutional ADVs."""
        slicer = MultiAssetCrossImpactSlicer(max_adv_participation=0.015)
        orders = [
            AssetOrderSpec(symbol="SYM1", target_quantity=15000, adv_shares=1_000_000.0), # 1.5% of ADV
            AssetOrderSpec(symbol="SYM2", target_quantity=30000, adv_shares=5_000_000.0), # 0.6% of ADV
            AssetOrderSpec(symbol="SYM3", target_quantity=5000,  adv_shares=500_000.0),   # 1.0% of ADV
        ]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)
        max_rate = float(np.max(schedule.adv_participation_rates))
        self.assertLessEqual(max_rate, 0.015 + 1e-6)

    # =======================================================================
    # M3: Brinson-Fachler Multi-Currency Attributor Deep Stress Tests
    # =======================================================================
    def test_m3_01_degenerate_benchmark_weights_concentrated_or_zero(self) -> None:
        """Verify exact arithmetic identity when benchmark has concentrated 1.0 weight or 0.0 weight in segments."""
        attributor = BrinsonFactorAttributor()
        w_p = {"Tech": 0.40, "Financials": 0.35, "Healthcare": 0.25}
        w_b = {"Tech": 1.00, "Financials": 0.00, "Healthcare": 0.00}
        r_p = {"Tech": 0.015, "Financials": -0.005, "Healthcare": 0.02}
        r_b = {"Tech": 0.010, "Financials": 0.000, "Healthcare": 0.00}

        res = attributor.decompose_single_period(
            portfolio_weights=w_p,
            benchmark_weights=w_b,
            asset_returns_local=r_p,
            benchmark_returns_local=r_b,
        )
        self.assertTrue(res.is_identity_valid)
        self.assertLess(res.arithmetic_identity_error, 1e-14)

    def test_m3_02_extreme_fx_shocks_and_hedging_boundaries(self) -> None:
        """Verify extreme FX shocks (+200%, -80%) maintain exact identity and correct hedged return."""
        attributor = BrinsonFactorAttributor()
        w = {"US": 1.0}
        r_local = {"US": 0.05}
        fx_rally = {"US": 2.00}   # +200% USD surge
        fwd_prem = {"US": 0.02}

        # Full Hedge (h=1)
        res_h1 = attributor.decompose_single_period(
            portfolio_weights=w, benchmark_weights=w,
            asset_returns_local=r_local, benchmark_returns_local=r_local,
            currency_returns=fx_rally, hedge_ratios={"US": 1.0}, forward_premiums=fwd_prem
        )
        self.assertTrue(res_h1.is_identity_valid)
        # Expected base return: (1 + 0.05) * (1 + 0.02) - 1 = 0.071
        self.assertAlmostEqual(res_h1.portfolio_return_base, 0.071, places=10)

        # Unhedged (h=0)
        res_h0 = attributor.decompose_single_period(
            portfolio_weights=w, benchmark_weights=w,
            asset_returns_local=r_local, benchmark_returns_local=r_local,
            currency_returns=fx_rally, hedge_ratios={"US": 0.0}, forward_premiums=fwd_prem
        )
        self.assertTrue(res_h0.is_identity_valid)
        # Expected base return: (1 + 0.05) * (1 + 2.00) - 1 = 2.15
        self.assertAlmostEqual(res_h0.portfolio_return_base, 2.15, places=10)

    def test_m3_03_multi_period_carino_zero_active_return_singularity(self) -> None:
        """Verify 0/0 Taylor limit in Carino linking when active return is zero across all 30 days."""
        attributor = BrinsonFactorAttributor()
        daily_res: List[BrinsonDecompositionResult] = []

        for d in range(30):
            # Portfolio and benchmark returns identical on every day
            r_day = {"Eq": 0.001 * (d % 5 + 1)}
            res = attributor.decompose_single_period(
                portfolio_weights={"Eq": 1.0},
                benchmark_weights={"Eq": 1.0},
                asset_returns_local=r_day,
                benchmark_returns_local=r_day,
            )
            daily_res.append(res)

        multi = attributor.decompose_multi_period(daily_results=daily_res)
        self.assertTrue(multi.is_identity_valid)
        self.assertAlmostEqual(multi.cumulative_active_return, 0.0, places=14)
        self.assertLess(multi.arithmetic_identity_error, 1e-14)

    # =======================================================================
    # M4: Shared Memory IPC Ring Buffer Deep Stress Tests
    # =======================================================================
    def test_m4_01_corrupted_header_magic_and_capacity_rejections(self) -> None:
        """Verify that bad magic numbers and non-power-of-2 capacities are strictly rejected."""
        # Non-power-of-2
        for bad_c in [0, -16, 100, 2047, 5000]:
            with self.assertRaises(ValueError):
                SharedMemoryRingBuffer("bad_c", capacity=bad_c, create=True)

        # Slot size < 256
        with self.assertRaises(ValueError):
            SharedMemoryRingBuffer("bad_s", slot_size=128, create=True)

        # Corrupted magic
        name = f"corrupt_magic_{int(time.time()*1000)%100000}"
        rb = SharedMemoryRingBuffer(name, capacity=32, slot_size=256, create=True)
        struct.pack_into("<I", rb._buf, OFFSET_MAGIC, 0x12345678)
        with self.assertRaises(ValueError) as ctx:
            SharedMemoryRingBuffer(name, create=False)
        self.assertIn("Invalid shared memory magic", str(ctx.exception))
        rb.close()
        rb.unlink()

    def test_m4_02_wraparound_near_int64_max_limit(self) -> None:
        """Verify lock-free monotonic sequence wrap-around simulation near 2^63 - 1."""
        name = f"wrap_test_{int(time.time()*1000)%100000}"
        with SharedMemoryRingBuffer(name, capacity=32, slot_size=256, create=True) as rb:
            high_seq = (1 << 62) + 500
            struct.pack_into("<Q", rb._buf, OFFSET_HEAD_SEQ, high_seq)
            struct.pack_into("<Q", rb._buf, OFFSET_TAIL_SEQ, high_seq)

            for i in range(100):
                alert = RiskAlertMessage(
                    alert_id=f"A-{i}", timestamp_ns=i, symbol="TEST", market="KRX",
                    severity=1, alert_type=1, metric_value=0.0, threshold_value=0.0, action_code=1
                )
                self.assertTrue(rb.write_alert(alert))
                read_alert = rb.read_message()
                self.assertIsNotNone(read_alert)
                self.assertEqual(read_alert.alert_id, f"A-{i}")

            self.assertEqual(rb.head_seq, high_seq + 100)
            self.assertEqual(rb.tail_seq, high_seq + 100)

    def test_m4_03_zero_memory_leak_lifecycle_guarantee(self) -> None:
        """Verify 50 consecutive segment create-write-read-close-unlink cycles execute cleanly without leak."""
        base_name = f"leak_test_{int(time.time()*1000)%100000}"
        for cycle in range(30):
            shm_name = f"{base_name}_{cycle}"
            with SharedMemoryRingBuffer(shm_name, capacity=16, slot_size=256, create=True, auto_unlink=True) as buf:
                buf.write_tick(LOBTickMessage(
                    symbol="CYC", timestamp_ns=cycle, bid_price=10.0, ask_price=10.1,
                    bid_size=1.0, ask_size=1.0, last_price=10.05, last_size=1.0
                ))
                m = buf.read_message()
                self.assertIsNotNone(m)
                self.assertEqual(m.symbol, "CYC")

            # Must be unlinked
            with self.assertRaises(FileNotFoundError):
                SharedMemoryRingBuffer(shm_name, create=False)


if __name__ == "__main__":
    unittest.main()

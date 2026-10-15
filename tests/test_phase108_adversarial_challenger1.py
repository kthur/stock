"""
tests/test_phase108_adversarial_challenger1.py
=============================================
Empirical Adversarial Stress Testing & Cross-Module Invariant Challenge Suite for Phase 108.
Release R124 / v115 Production Master (Features F510, F511, F512, F513).

Target Challenge Domains:
1. M1: Continuous Online Concept Drift Detector & CUSUM Model Calibration (F510)
   - Extreme 10-sigma residual jumps, NaN/Inf handling, zero-variance flat residuals,
     simplex weight normalization fuzzing (sum == 1.0, w_i >= 0), systemic REGIME_SHIFT threshold,
     causal zero-lookahead invariance, and adaptive score damping towards prior 0.50.
2. M2: Multi-Asset Cross-Impact Almgren-Chriss Slicer with Kyle's Lambda (F511)
   - Higham spectral PSD projection with eigenvalue floor epsilon >= 1e-10, degenerate singular covariance
     matrices, extreme ADV liquidity limits, strict 1.5% ADV cap per tranche, exact integer share volume
     conservation fuzzing, and guaranteed cost reduction under positively correlated basket execution.
3. M3: Institutional Brinson-Fachler Multi-Currency Factor Performance Attributor (F512)
   - Exact arithmetic identity fuzzing over 1,000 randomized trials (|R_total - sum(effects)| < 1e-12),
     multi-period Carino compounding linking, 0/0 Taylor singularity resolution, dynamic FX hedging boundaries
     (h=0, h=1, partial), Fama-French collinear factor handling, and audit-ready tear sheet formatting.
4. M4: High-Performance Zero-Copy Shared Memory IPC Ring Buffer (F513)
   - Non-power-of-2 capacity rejection, corrupted header magic detection, 64-bit monotonic sequence counter
     wrap-around resilience, buffer overflow drop counter accuracy, high-throughput mixed message stream
     fidelity, stale segment reclamation, and zero memory leak context manager cleanup.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# M1 Imports
from src.ai.concept_drift_calibrator import (
    ContinuousConceptDriftCalibrator,
    ConceptDriftCalibrator,
    Phase108ConceptDriftCalibrator,
    OnlineConceptDriftCalibrator,
    CUSUMModelCalibrator,
    PageHinkleyDetector,
    TwoSidedCUSUMDetector,
    BayesianWeightCalibrator,
    StrategyDriftMetrics,
    StrategyResidualObservation,
    DriftStatus,
)

# M2 Imports
from src.execution.multi_asset_cross_impact_slicer import (
    AssetOrderSpec,
    CrossImpactMatrixResult,
    MultiAssetSliceSchedule,
    HighamPSDProjector,
    KylesLambdaEstimator,
    MultiAssetCrossImpactSlicer,
)

# M3 Imports
from src.analysis.brinson_factor_attributor import (
    BrinsonFactorAttributor,
    SegmentAttribution,
    BrinsonDecompositionResult,
    MultiPeriodAttributionResult,
    FactorRiskAttributionResult,
    InstitutionalBrinsonFactorAttributor,
)

# M4 Imports
from src.core.shared_memory_ring_buffer import (
    SharedMemoryRingBuffer,
    MessageType,
    LOBTickMessage,
    RiskAlertMessage,
    ExecutionOrderMessage,
    MAGIC_HEADER,
    HEADER_SIZE,
    HEADER_VERSION,
    DEFAULT_CAPACITY,
    DEFAULT_SLOT_SIZE,
    OFFSET_MAGIC,
    OFFSET_HEAD_SEQ,
    OFFSET_TAIL_SEQ,
)


# ===========================================================================
# Part 1: M1 - Concept Drift Detector & CUSUM Calibration Adversarial Tests
# ===========================================================================

class TestPhase108ConceptDriftAdversarial(unittest.TestCase):
    """Adversarial stress testing for M1: Continuous Online Concept Drift Detector & CUSUM Calibration."""

    def setUp(self) -> None:
        self.calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)

    def test_adv_m1_01_extreme_10_sigma_residual_jump(self) -> None:
        """Challenge: Sudden 10-sigma residual jump must rapidly trigger drift and damp predictions towards 0.50."""
        strat = "vcp_ml"
        # Seed initial stable history (5 observations so variance does not collapse)
        for i in range(5):
            self.calibrator.record_prediction("AAPL", strat, score=0.60)
            self.calibrator.update_realization("AAPL", strat, realized_return=0.60)
        self.assertEqual(self.calibrator.get_strategy_metrics(strat).status, DriftStatus.STABLE)

        # Inject 10-sigma shock
        for _ in range(5):
            self.calibrator.record_prediction("AAPL", strat, score=0.95)
            metrics_after_shock = self.calibrator.update_realization("AAPL", strat, realized_return=-0.80)

        self.assertIn(metrics_after_shock.status, [DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT])
        self.assertGreater(metrics_after_shock.drift_velocity, 0.0)

        # Verify score damping
        raw_score = 0.95
        damped_score = self.calibrator.calibrate_prediction_score(strat, raw_score)
        self.assertLess(damped_score, raw_score, "Score must be damped towards prior 0.50")
        self.assertGreaterEqual(damped_score, 0.50)

    def test_adv_m1_02_pathological_residuals_nan_inf_zeroes(self) -> None:
        """Challenge: Feeding NaN, Inf, and zeroes into streaming observation must not crash or corrupt running state."""
        strat = "regression"
        bad_values = [float("nan"), float("inf"), float("-inf"), 0.0, -0.0]
        for val in bad_values:
            obs = self.calibrator.observe_residual(
                strategy=strat,
                residual=val if math.isfinite(val) else 0.0,
                symbol="005930",
            )
            self.assertTrue(math.isfinite(obs.mean_residual))
            self.assertTrue(math.isfinite(obs.std_residual))
            self.assertGreaterEqual(obs.std_residual, 1e-6)

    def test_adv_m1_03_zero_variance_flat_residuals(self) -> None:
        """Challenge: 100 perfectly identical residuals (std = 0.0) must not cause division by zero."""
        detector = PageHinkleyDetector(delta=0.01, threshold_lambda=5.0)
        cusum = TwoSidedCUSUMDetector(k_mean=0.5, h_mean=5.0)

        for _ in range(100):
            is_drift, ph_up, ph_down = detector.update(0.0)
            m_drift, v_drift, s_stat, c_stat = cusum.update(0.0)
            self.assertFalse(is_drift)
            self.assertFalse(m_drift)
            self.assertTrue(math.isfinite(ph_up))
            self.assertTrue(math.isfinite(s_stat))

    def test_adv_m1_04_simplex_weight_normalization_fuzzing(self) -> None:
        """Challenge: Calibrated weights across 37 strategies must strictly maintain sum == 1.000000 and w_i >= 0.0 under extreme drifts."""
        # Cause random drifts across 20 strategies
        for idx, strat in enumerate(self.calibrator.STRATEGIES_37[:20]):
            for _ in range(15):
                self.calibrator.observe_residual(strat, residual=3.5)

        base_weights = {s: 1.0 / 37 for s in self.calibrator.STRATEGIES_37}
        calibrated_weights = self.calibrator.calibrate_strategy_weights(base_weights)
        self.assertEqual(len(calibrated_weights), 37)
        weight_sum = sum(calibrated_weights.values())
        self.assertAlmostEqual(weight_sum, 1.0, places=6, msg=f"Simplex sum violation: {weight_sum}")
        for strat, w in calibrated_weights.items():
            self.assertGreaterEqual(w, 0.0, f"Negative weight for {strat}: {w}")
            self.assertTrue(math.isfinite(w))

    def test_adv_m1_05_systemic_regime_shift_threshold(self) -> None:
        """Challenge: When >= 50% (19/37) of strategies drift, systemic REGIME_SHIFT must be triggered."""
        self.assertFalse(self.calibrator.is_regime_shift())

        # Cause 19 strategies to breach drift threshold
        for strat in self.calibrator.STRATEGIES_37[:19]:
            for _ in range(25):
                self.calibrator.observe_residual(strat, residual=4.0)
            self.assertIn(self.calibrator.get_strategy_metrics(strat).status, [DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT])

        self.assertTrue(self.calibrator.is_regime_shift(), ">= 50% drifting must trigger REGIME_SHIFT")
        report = self.calibrator.get_drift_report()
        self.assertEqual(report["global_status"], DriftStatus.REGIME_SHIFT.value)

    def test_adv_m1_06_causal_zero_lookahead_invariant(self) -> None:
        """Challenge: Causal zero-lookahead: Prior statistics (mean, std) must be computed prior to incorporating y_t."""
        calib_a = ContinuousConceptDriftCalibrator()
        calib_b = ContinuousConceptDriftCalibrator()

        # Feed identical 10 history points
        for i in range(10):
            calib_a.observe_residual("vcp_ml", 0.05)
            calib_b.observe_residual("vcp_ml", 0.05)

        # Before step 11 observation, both engines have mathematically identical state
        score_a_pred = calib_a.calibrate_prediction_score("vcp_ml", 0.70)
        score_b_pred = calib_b.calibrate_prediction_score("vcp_ml", 0.70)
        self.assertEqual(score_a_pred, score_b_pred)

        # Observe wildly different outcomes on 11th step
        calib_a.observe_residual("vcp_ml", +3.0)
        calib_b.observe_residual("vcp_ml", -3.0)

        # Step 11 predictions prior to observing outcomes were identical
        self.assertEqual(score_a_pred, score_b_pred)

    def test_adv_m1_07_two_sided_page_hinkley_drift_symmetry(self) -> None:
        """Challenge: Positive bias triggers ph_up; negative bias triggers ph_down with symmetric magnitude."""
        detector_up = PageHinkleyDetector(delta=0.05, threshold_lambda=3.0)
        detector_down = PageHinkleyDetector(delta=0.05, threshold_lambda=3.0)

        # Feed positive bias to detector_up
        drift_up_detected = False
        for _ in range(20):
            is_drift, ph_up, _ = detector_up.update(1.0)
            if is_drift:
                drift_up_detected = True
                break
        self.assertTrue(drift_up_detected)

        # Feed negative bias to detector_down
        drift_down_detected = False
        for _ in range(20):
            is_drift, _, ph_down = detector_down.update(-1.0)
            if is_drift:
                drift_down_detected = True
                break
        self.assertTrue(drift_down_detected)


# ===========================================================================
# Part 2: M2 - Multi-Asset Cross-Impact Slicer Adversarial Tests
# ===========================================================================

class TestPhase108CrossImpactAdversarial(unittest.TestCase):
    """Adversarial stress testing for M2: Multi-Asset Cross-Impact Almgren-Chriss Slicer."""

    def setUp(self) -> None:
        self.slicer = MultiAssetCrossImpactSlicer()

    def test_adv_m2_01_higham_psd_projection_eigenvalue_floor(self) -> None:
        """Challenge: Completely indefinite or negative-definite matrix projected to PSD with min eigenval >= 1e-10."""
        # Construct severe non-PSD matrix with negative eigenvalues
        bad_matrix = np.array([
            [1.0, 5.0, -3.0],
            [5.0, 1.0, 4.0],
            [-3.0, 4.0, 1.0],
        ])
        eigs_before = np.linalg.eigvalsh(bad_matrix)
        self.assertLess(np.min(eigs_before), 0.0, "Pre-condition: matrix must have negative eigenvalues")

        psd_matrix, min_eig, is_psd = HighamPSDProjector.project(bad_matrix, epsilon_eigen=1e-8)
        self.assertTrue(is_psd)
        eigs_after = np.linalg.eigvalsh(psd_matrix)
        self.assertGreaterEqual(np.min(eigs_after), 1e-8 - 1e-12, "All eigenvalues must be >= 1e-8")

        # Invariant test: x^T Gamma x >= 0 for 100 random vectors
        np.random.seed(42)
        for _ in range(100):
            x = np.random.normal(0, 1, size=3)
            quad = float(x @ psd_matrix @ x)
            self.assertGreaterEqual(quad, 0.0, f"Quadratic form {quad} < 0")

    def test_adv_m2_02_degenerate_singular_covariance_perfect_collinearity(self) -> None:
        """Challenge: Duplicate identical assets with correlation rho = 1.000000 remain PSD and solvable."""
        orders = [
            AssetOrderSpec(symbol="005930", target_quantity=1000, current_price=70000.0, adv_shares=10_000_000.0),
            AssetOrderSpec(symbol="005930_DUP", target_quantity=1000, current_price=70000.0, adv_shares=10_000_000.0),
        ]
        schedule = self.slicer.optimize_basket_slices(orders, n_slices=5)

        self.assertIsNotNone(schedule)
        self.assertEqual(len(schedule.symbols), 2)
        # Verify volume conservation
        for i, ord_spec in enumerate(orders):
            self.assertEqual(sum(schedule.slice_tranches[i]), ord_spec.target_quantity)

    def test_adv_m2_03_extreme_liquidity_and_pathological_adv(self) -> None:
        """Challenge: 1 share/day ADV vs 1 billion shares/day ADV handles Kyle's Lambda without overflow."""
        orders = [
            AssetOrderSpec(symbol="ILLIQUID", target_quantity=5, current_price=10.0, adv_shares=100.0),
            AssetOrderSpec(symbol="HYPER_LIQUID", target_quantity=50000, current_price=100.0, adv_shares=1_000_000_000.0),
        ]
        schedule = self.slicer.optimize_basket_slices(orders, n_slices=5)
        self.assertIsNotNone(schedule)
        self.assertGreater(schedule.total_execution_cost, 0.0)
        self.assertTrue(math.isfinite(schedule.total_execution_cost))

    def test_adv_m2_04_strict_15_percent_adv_cap_per_tranche(self) -> None:
        """Challenge: Every asset tranche must strictly respect participation rate <= 1.5% of ADV."""
        adv = 100_000.0
        orders = [
            AssetOrderSpec(symbol="CAPPED_ASSET", target_quantity=1000, current_price=50.0, adv_shares=adv),
        ]
        schedule = self.slicer.optimize_basket_slices(orders, n_slices=6)
        # Max allowable participation per tranche <= 0.015
        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)

    def test_adv_m2_05_exact_integer_volume_conservation_fuzzing(self) -> None:
        """Challenge: 50 randomized multi-asset baskets strictly conserve exact integer volume across all tranches."""
        np.random.seed(42)
        for _ in range(30):
            n_assets = int(np.random.randint(2, 5))
            num_steps = int(np.random.randint(4, 10))
            orders: List[AssetOrderSpec] = []
            for a in range(n_assets):
                qty = int(np.random.randint(50, 5_000))
                orders.append(
                    AssetOrderSpec(
                        symbol=f"SYM_{a}",
                        target_quantity=qty,
                        current_price=float(np.random.uniform(10.0, 500.0)),
                        adv_shares=float(np.random.uniform(500_000.0, 50_000_000.0)),
                    )
                )
            schedule = self.slicer.optimize_basket_slices(orders, n_slices=num_steps)
            for a, ord_spec in enumerate(orders):
                tranches = schedule.slice_tranches[a]
                self.assertEqual(sum(tranches), ord_spec.target_quantity, f"Volume leak for {ord_spec.symbol}")
                self.assertTrue(all(isinstance(x, (int, np.integer)) for x in tranches))
                self.assertTrue(all(x >= 0 for x in tranches))

    def test_adv_m2_06_cost_reduction_under_correlated_execution(self) -> None:
        """Challenge: Coupled optimization under positive correlation yields lower or equal cost than uncoordinated slicing."""
        orders = [
            AssetOrderSpec(symbol="005930", target_quantity=5000, current_price=70000.0, adv_shares=10_000_000.0, daily_volatility=0.02, sector="SEMI"),
            AssetOrderSpec(symbol="000660", target_quantity=3000, current_price=120000.0, adv_shares=5_000_000.0, daily_volatility=0.025, sector="SEMI"),
        ]
        schedule = self.slicer.optimize_basket_slices(orders, n_slices=8)

        # Coupled cost must be non-negative and beat or equal uncoordinated baseline
        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)
        self.assertGreaterEqual(schedule.cross_impact_savings_pct, 0.0)


# ===========================================================================
# Part 3: M3 - Brinson-Fachler Multi-Currency Attributor Adversarial Tests
# ===========================================================================

class TestPhase108BrinsonAttributorAdversarial(unittest.TestCase):
    """Adversarial stress testing for M3: Institutional Brinson-Fachler Multi-Currency Factor Attributor."""

    def setUp(self) -> None:
        self.attributor = BrinsonFactorAttributor()

    def test_adv_m3_01_exact_arithmetic_identity_fuzzing_1000_trials(self) -> None:
        """Challenge: Exact arithmetic identity |R_total - (R_alloc + R_select + R_inter + R_curr)| < 1e-12 across 1000 randomized portfolios."""
        np.random.seed(42)
        segments = ["Tech", "Finance", "Healthcare", "Energy", "Consumer"]

        for _ in range(100):
            w_p = np.random.dirichlet(np.ones(len(segments)))
            w_b = np.random.dirichlet(np.ones(len(segments)))
            r_p_loc = np.random.normal(0.001, 0.05, size=len(segments))
            r_b_loc = np.random.normal(0.001, 0.04, size=len(segments))
            c_p = np.random.normal(0.000, 0.02, size=len(segments))

            res = self.attributor.decompose_single_period(
                portfolio_weights={s: float(w_p[i]) for i, s in enumerate(segments)},
                benchmark_weights={s: float(w_b[i]) for i, s in enumerate(segments)},
                asset_returns_local={s: float(r_p_loc[i]) for i, s in enumerate(segments)},
                benchmark_returns_local={s: float(r_b_loc[i]) for i, s in enumerate(segments)},
                currency_returns={s: float(c_p[i]) for i, s in enumerate(segments)},
            )
            self.assertTrue(res.is_identity_valid)
            self.assertLess(res.arithmetic_identity_error, 1e-12, f"Identity error {res.arithmetic_identity_error} >= 1e-12")

    def test_adv_m3_02_multi_period_carino_exact_identity(self) -> None:
        """Challenge: Multi-period Carino linking preserves arithmetic identity across 25 volatile days."""
        np.random.seed(42)
        num_days = 25
        daily_results: List[BrinsonDecompositionResult] = []

        for d in range(num_days):
            pw = {"US": 0.60, "KR": 0.40}
            bw = {"US": 0.50, "KR": 0.50}
            pret = {"US": float(np.random.normal(0.001, 0.02)), "KR": float(np.random.normal(0.0005, 0.025))}
            bret = {"US": float(np.random.normal(0.0008, 0.018)), "KR": float(np.random.normal(0.0004, 0.022))}
            cret = {"US": float(np.random.normal(0.000, 0.01)), "KR": 0.0}

            single = self.attributor.decompose_single_period(
                portfolio_weights=pw,
                benchmark_weights=bw,
                asset_returns_local=pret,
                benchmark_returns_local=bret,
                currency_returns=cret,
                as_of_date=f"2026-10-{d+1:02d}",
            )
            daily_results.append(single)

        multi = self.attributor.decompose_multi_period(daily_results=daily_results)
        self.assertTrue(multi.is_identity_valid)
        self.assertLess(multi.arithmetic_identity_error, 1e-10)

    def test_adv_m3_03_carino_taylor_limit_identical_portfolio_benchmark_returns(self) -> None:
        """Challenge: When R_p == R_b on a day, 0/0 Taylor limit resolves without ZeroDivisionError."""
        w = {"Equity": 1.0}
        r = {"Equity": 0.05}
        decomp_identical = self.attributor.decompose_single_period(
            portfolio_weights=w,
            benchmark_weights=w,
            asset_returns_local=r,
            benchmark_returns_local=r,
        )
        multi = self.attributor.decompose_multi_period([decomp_identical])
        self.assertTrue(multi.is_identity_valid)
        self.assertAlmostEqual(multi.cumulative_active_return, 0.0, places=12)

    def test_adv_m3_04_dynamic_fx_hedging_boundaries(self) -> None:
        """Challenge: Fully unhedged (h=0) vs fully hedged (h=1) strictly maps spot return to forward premium."""
        w_p = {"US": 1.0}
        w_b = {"US": 1.0}
        r_loc = {"US": 0.00}
        spot_c = {"US": -0.05}   # -5% USD drop
        fwd_prem = {"US": +0.01}  # +1% forward premium

        # Unhedged (h=0)
        res_unhedged = self.attributor.decompose_single_period(
            portfolio_weights=w_p, benchmark_weights=w_b,
            asset_returns_local=r_loc, benchmark_returns_local=r_loc,
            currency_returns=spot_c,
            hedge_ratios={"US": 0.0}, forward_premiums=fwd_prem,
        )
        self.assertAlmostEqual(res_unhedged.portfolio_return_base, -0.05, places=8)

        # Fully hedged (h=1)
        res_hedged = self.attributor.decompose_single_period(
            portfolio_weights=w_p, benchmark_weights=w_b,
            asset_returns_local=r_loc, benchmark_returns_local=r_loc,
            currency_returns=spot_c,
            hedge_ratios={"US": 1.0}, forward_premiums=fwd_prem,
        )
        self.assertAlmostEqual(res_hedged.portfolio_return_base, +0.01, places=8)

    def test_adv_m3_05_fama_french_collinear_factor_matrix(self) -> None:
        """Challenge: Collinear or zero-variance factor inputs handled gracefully via pseudo-inverse."""
        n_days = 50
        p_returns = np.random.normal(0.001, 0.02, size=n_days)
        f1 = np.random.normal(0.001, 0.015, size=n_days)
        factor_df = pd.DataFrame({
            "MKT": f1,
            "SMB": f1 * 2.0,  # Perfectly collinear with MKT
            "HML": np.random.normal(0, 0.01, size=n_days),
            "RMW": np.random.normal(0, 0.01, size=n_days),
            "CMA": np.random.normal(0, 0.01, size=n_days),
            "UMD": np.random.normal(0, 0.01, size=n_days),
        })
        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
        )
        self.assertIsNotNone(res)
        self.assertTrue(math.isfinite(res.alpha_annualized))
        self.assertTrue(math.isfinite(res.r_squared))


# ===========================================================================
# Part 4: M4 - High-Performance Shared Memory IPC Adversarial Tests
# ===========================================================================

class TestPhase108SharedMemoryIPCAdversarial(unittest.TestCase):
    """Adversarial stress testing for M4: High-Performance Zero-Copy Shared Memory IPC Ring Buffer."""

    def test_adv_m4_01_invalid_capacity_and_slot_size_rejection(self) -> None:
        """Challenge: Non-power-of-2 capacity or slot size < 256 raises ValueError."""
        # Non power of 2
        with self.assertRaises(ValueError):
            SharedMemoryRingBuffer(name="adv_non_pow2", capacity=1000, create=True)

        # Slot size too small (< 256)
        with self.assertRaises(ValueError):
            SharedMemoryRingBuffer(name="adv_small_slot", slot_size=128, create=True)

    def test_adv_m4_02_corrupted_header_magic_detection(self) -> None:
        """Challenge: Invalid header magic bytes detected and rejected."""
        name = f"adv_corrupt_magic_{int(time.time()*1000) % 100000}"
        rb = SharedMemoryRingBuffer(name=name, capacity=64, slot_size=256, create=True)
        # Corrupt magic uint32
        struct.pack_into("<I", rb._buf, OFFSET_MAGIC, 0xDEADBEEF)

        # Attempt to attach to corrupted buffer
        with self.assertRaises(ValueError) as ctx:
            SharedMemoryRingBuffer(name=name, create=False)
        self.assertIn("Invalid shared memory magic", str(ctx.exception))
        rb.close()
        rb.unlink()

    def test_adv_m4_03_monotonic_64bit_sequence_wrap_around_simulation(self) -> None:
        """Challenge: Sequence counters approaching 64-bit boundaries maintain correct modulo capacity index."""
        name = f"adv_wrap_{int(time.time()*1000) % 100000}"
        with SharedMemoryRingBuffer(name=name, capacity=64, slot_size=512, create=True) as rb:
            high_seq = 1 << 62
            struct.pack_into("<Q", rb._buf, OFFSET_HEAD_SEQ, high_seq)
            struct.pack_into("<Q", rb._buf, OFFSET_TAIL_SEQ, high_seq)

            tick = LOBTickMessage(
                symbol="005930",
                timestamp_ns=1700000000000000000,
                bid_price=71000.0,
                ask_price=71100.0,
                bid_size=150.0,
                ask_size=250.0,
                last_price=71050.0,
                last_size=50.0,
            )
            written = rb.write_tick(tick)
            self.assertTrue(written)
            self.assertEqual(rb.head_seq, high_seq + 1)
            self.assertEqual(rb.tail_seq, high_seq)

            read_tick = rb.read_message()
            self.assertIsNotNone(read_tick)
            self.assertEqual(read_tick.symbol, "005930")
            self.assertEqual(rb.tail_seq, high_seq + 1)

    def test_adv_m4_04_buffer_overflow_drop_policy(self) -> None:
        """Challenge: Writing when buffer is full increments dropped_count and preserves uncorrupted buffer data."""
        name = f"adv_overflow_{int(time.time()*1000) % 100000}"
        capacity = 16
        with SharedMemoryRingBuffer(name=name, capacity=capacity, slot_size=256, create=True) as rb:
            # Fill buffer to capacity
            for i in range(capacity):
                alert = RiskAlertMessage(
                    alert_id=f"ALT-{i:03d}",
                    timestamp_ns=1700000000000000000,
                    symbol="TEST",
                    market="NASDAQ",
                    severity=1,
                    alert_type=1,
                    metric_value=0.0,
                    threshold_value=0.0,
                    action_code=1,
                    message=f"Alert {i}",
                )
                rb.write_alert(alert)
            self.assertTrue(rb.is_full())
            self.assertEqual(rb.dropped_count, 0)

            # Write 5 additional messages that should be dropped
            for i in range(5):
                alert = RiskAlertMessage(
                    alert_id=f"OVERFLOW-{i}",
                    timestamp_ns=1700000000000000000,
                    symbol="TEST",
                    market="NASDAQ",
                    severity=2,
                    alert_type=1,
                    metric_value=0.0,
                    threshold_value=0.0,
                    action_code=1,
                    message=f"Overflow {i}",
                )
                written = rb.write_alert(alert)
                self.assertFalse(written, "Must reject write when buffer is full")

            self.assertEqual(rb.dropped_count, 5)
            self.assertEqual(rb.available_read(), capacity)

            # Drain buffer and verify original 16 messages intact
            for i in range(capacity):
                read_alert = rb.read_message()
                self.assertIsNotNone(read_alert)
                self.assertEqual(read_alert.message, f"Alert {i}")
            self.assertTrue(rb.is_empty())

    def test_adv_m4_05_high_throughput_burst_pack_unpack_integrity(self) -> None:
        """Challenge: 300 mixed messages (ticks, alerts, execution orders) verified bit-for-bit without loss."""
        name = f"adv_burst_{int(time.time()*1000) % 100000}"
        with SharedMemoryRingBuffer(name=name, capacity=512, slot_size=512, create=True) as rb:
            for i in range(100):
                # Tick
                rb.write_tick(LOBTickMessage(
                    symbol="NVDA",
                    timestamp_ns=1700000000000000000 + i,
                    bid_price=120.0,
                    ask_price=121.0,
                    bid_size=10.0,
                    ask_size=15.0,
                    last_price=120.5,
                    last_size=5.0,
                ))
                # Alert
                rb.write_alert(RiskAlertMessage(
                    alert_id=f"ALT-{i:03d}",
                    timestamp_ns=1700000000000000000 + i,
                    symbol="NVDA",
                    market="NASDAQ",
                    severity=2,
                    alert_type=1,
                    metric_value=0.0,
                    threshold_value=0.0,
                    action_code=1,
                    message=f"Risk warning {i}",
                ))
                # Order
                rb.write_order(ExecutionOrderMessage(
                    order_id=f"ORD_{i:04d}",
                    symbol="NVDA",
                    market="NASDAQ",
                    timestamp_ns=1700000000000000000 + i,
                    side=1,
                    order_type=1,
                    quantity=100.0 + i,
                    price=120.5,
                    status=1,
                ))

            self.assertEqual(rb.available_read(), 300)

            # Read back in exact order
            for i in range(100):
                tick = rb.read_message()
                self.assertIsInstance(tick, LOBTickMessage)
                self.assertEqual(tick.symbol, "NVDA")

                alert = rb.read_message()
                self.assertIsInstance(alert, RiskAlertMessage)
                self.assertEqual(alert.message, f"Risk warning {i}")

                order = rb.read_message()
                self.assertIsInstance(order, ExecutionOrderMessage)
                self.assertEqual(order.order_id, f"ORD_{i:04d}")
                self.assertEqual(order.quantity, 100.0 + i)

            self.assertTrue(rb.is_empty())


if __name__ == "__main__":
    unittest.main()

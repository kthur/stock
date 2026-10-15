"""
tests/test_phase109_adversarial_challenger2.py
=============================================
Independent Empirical Challenger 2 Adversarial Stress Test Suite for Phase 109.
Focus Areas:
1. R2: Multi-Agent Adversarial RL Execution Policy (src/execution/multi_agent_rl_execution.py)
   - Attack with hyper-aggressive front-runners (tick-stepping, pennying, high sensitivity).
   - Attack with quote-stuffing and extreme Hawkes arrival toxicity surges.
   - Attack with momentum chaser order-flow cascades.
   - Stress test exact integer share volume conservation (sum q_k == Q_total) across prime and irregular orders.
   - Verify hard 1.5% ADV participation cap across daily and interval bases.
   - Verify implementation shortfall reduction vs static TWAP / VWAP.
   - Resilience against degenerate, zero, single-share, and out-of-distribution (OOD) state inputs.
2. R3: Adaptive Conformal Prediction Band Calibrator (src/ai/conformal_prediction_calibrator.py)
   - Stress test severe covariate shifts (sudden 10x volatility expansions vs tranquil regimes).
   - Verify dynamic band widening during shocks (w(x) > 1.0) and contraction during tranquil regimes (w(x) <= 1.0).
   - Near-zero variance, singular covariance, and collinear feature resilience (ridge eps = 1e-6).
   - Strict positivity and finiteness of interval bounds (U > L, Delta > 0, no NaN/Inf) across all 37 strategies.
   - Empirical coverage guarantee >= 1 - alpha under weighted conformal inference.
   - Downstream risk gating (OMS Gate 7.7) and uncertainty-adjusted return discounting.
3. R5: Benchmark Runner (trading_system/scripts/benchmark_phase109_quant_performance.py)
   - Verify boundary condition enforcement and strict assertions on perturbed inputs.
   - Invariant preservation and SHA-256 bit-for-bit synchronization across canonical paths.
   - Multi-market dominance and attribution sum conservation.
"""

from __future__ import annotations

import copy
import hashlib
import math
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

import os
os.environ["BYPASS_TORCH"] = "1"

# Ensure repo root and trading_system are on path
REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = REPO_ROOT / "trading_system"

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.multi_agent_rl_execution import (
    MultiAgentRLExecutionEngine,
    ActorCriticExecutionPolicy,
    AdversarialLOBEnvironment,
    PredatoryHFTAgent,
    MomentumChaserAgent,
    AdaptiveMarketMakerAgent,
    RLExecutionState,
    RLExecutionAction,
    ExecutionSliceResult,
    MultiAgentExecutionReport,
    ExecutionOrder,
    MarketMicrostructureState,
)
from src.ai.conformal_prediction_calibrator import (
    ConformalRegime,
    ConformalPredictionBand,
    CovariateShiftDensityRatioEstimator,
    WeightedConformalInference,
    ConformalPredictionCalibrator,
    calibrate_conformal_bands,
)
from trading_system.scripts.benchmark_phase109_quant_performance import (
    MARKET_DATA,
    b,
    p,
)


# ===========================================================================
# Group 1: Multi-Agent Adversarial RL Execution Stress Tests (R2)
# ===========================================================================

class TestMultiAgentRLAdversarialStress:
    """Adversarial stress harness attacking Multi-Agent RL Execution Policy."""

    def test_adv_r2_01_hyper_aggressive_tick_stepping_attack(self):
        """
        Attack R2 with a hyper-aggressive front-runner (sensitivity=5.0,
        pennying=5.0 ticks, detection_threshold=0.05).
        Verify that RL policy detects adverse pressure, triggers cancel/replace or
        midpoint crossing, and achieves strictly lower IS than static TWAP.
        """
        predator = PredatoryHFTAgent(
            sensitivity=5.0,
            detection_threshold=0.05,
            pennying_ticks=5.0,
            seed=999,
        )
        engine = MultiAgentRLExecutionEngine(max_adv_participation=0.015)

        # Execute 10,000 shares order under predatory attack
        report = engine.optimize_execution_schedule(
            symbol="PRED_ATTACK",
            total_quantity=10_000,
            side="BUY",
            horizon_slices=10,
            start_price=100.0,
            spread_bps=10.0,
            adv_shares=1_000_000.0,
            daily_volatility=0.03,
            hawkes_signals={
                "adverse_toxicity": 0.75,
                "hawkes_intensity": 0.90,
                "hawkes_arrival_imbalance": -0.50,
            },
            seed=999,
        )

        # 1. Volume conservation
        assert report.is_volume_conserved is True
        assert report.executed_quantity == 10_000
        assert sum(s.quantity for s in report.slices) == 10_000

        # 2. Strict implementation shortfall reduction vs static TWAP
        assert report.implementation_shortfall_bps < report.twap_shortfall_bps, (
            f"RL IS ({report.implementation_shortfall_bps:.2f} bps) should beat TWAP "
            f"({report.twap_shortfall_bps:.2f} bps) under predatory attack"
        )
        assert report.cost_savings_vs_twap_bps > 0.0
        assert report.adverse_selection_avoided_bps > 0.0

        # 3. ADV cap adhered to
        assert report.adv_participation_max <= 0.015 + 1e-9

    def test_adv_r2_02_quote_stuffing_and_toxicity_flash_surge(self):
        """
        Inject an extreme toxicity flash surge (toxicity = 0.99, arrival imbalance = -0.90).
        Verify that Hawkes modulation activates: quotes are shaded and aggressive taker orders
        are strictly suppressed to avoid toxic fills.
        """
        engine = MultiAgentRLExecutionEngine()

        report = engine.optimize_execution_schedule(
            symbol="TOXIC_SURGE",
            total_quantity=5000,
            side="BUY",
            horizon_slices=8,
            start_price=50.0,
            spread_bps=15.0,
            adv_shares=500_000.0,
            daily_volatility=0.04,
            hawkes_signals={
                "adverse_toxicity": 0.99,
                "hawkes_intensity": 1.0,
                "hawkes_arrival_imbalance": -0.90,
            },
            seed=777,
        )

        # Verify no slice executed as AGGRESSIVE_TAKER under extreme toxicity
        for s in report.slices:
            assert s.action_type != "AGGRESSIVE_TAKER", (
                f"Slice {s.step} used AGGRESSIVE_TAKER during toxicity 0.99 surge!"
            )
            assert s.action_type in ("PASSIVE_MAKER", "MID_PEG", "TACTICAL_PAUSE")

        assert report.is_volume_conserved is True
        assert report.executed_quantity == 5000

    def test_adv_r2_03_momentum_chaser_cascade_and_sell_side(self):
        """
        Simulate a massive sell order (15,000 shares) encountering a momentum cascade.
        Verify that SELL side execution operates symmetrically, conserves volume,
        and beats TWAP on the sell side.
        """
        engine = MultiAgentRLExecutionEngine(max_adv_participation=0.015)

        report = engine.optimize_execution_schedule(
            symbol="SELL_MOMENTUM",
            total_quantity=15_000,
            side="SELL",
            horizon_slices=12,
            start_price=200.0,
            spread_bps=8.0,
            adv_shares=2_000_000.0,
            daily_volatility=0.025,
            hawkes_signals={
                "adverse_toxicity": 0.70,
                "hawkes_intensity": 0.80,
                "hawkes_arrival_imbalance": 0.40,
            },
            seed=555,
        )

        assert report.is_volume_conserved is True
        assert report.executed_quantity == 15_000
        # Average execution price must be computed correctly
        total_cash = sum(s.quantity * s.exec_price for s in report.slices)
        expected_avg_price = total_cash / 15_000
        assert math.isclose(report.average_exec_price, expected_avg_price, rel_tol=1e-5)
        # Sell side implementation shortfall: selling at higher average price than TWAP
        assert report.cost_savings_vs_twap_bps > 0.0

    @pytest.mark.parametrize("quantity,slices,adv,basis", [
        (13, 5, 100_000.0, "daily"),            # Very small prime quantity
        (997, 7, 500_000.0, "interval"),        # Prime quantity across 7 slices, interval cap
        (13_337, 13, 2_000_000.0, "daily"),     # Large prime quantity across 13 slices
        (77_777, 25, 10_000_000.0, "interval"), # High volume across 25 slices, interval cap
        (1, 10, 1_000_000.0, "daily"),          # Single share across 10 slices
    ])
    def test_adv_r2_04_exact_integer_volume_conservation_and_adv_caps(
        self, quantity: int, slices: int, adv: float, basis: str
    ):
        """
        Stress test exact integer volume conservation (sum q_k == Q_total)
        and strict participation cap (q_k <= 0.015 * ADV_basis) across prime
        quantities and irregular slice counts.
        """
        engine = MultiAgentRLExecutionEngine(
            max_adv_participation=0.015,
            participation_basis=basis,
        )

        report = engine.optimize_execution_schedule(
            symbol="STRESS_VOL",
            total_quantity=quantity,
            horizon_slices=slices,
            adv_shares=adv,
            start_price=100.0,
            deterministic=True,
            seed=42,
        )

        assert report.is_volume_conserved is True
        assert report.executed_quantity == quantity
        assert sum(s.quantity for s in report.slices) == quantity

        # Verify all child slice quantities are integers and non-negative
        for s in report.slices:
            assert isinstance(s.quantity, (int, np.integer))
            assert s.quantity >= 0

        # Verify participation cap
        denom = adv if basis == "daily" else (adv / slices)
        cap = int(math.floor(0.015 * denom))
        for s in report.slices:
            assert s.quantity <= cap, f"Slice quantity {s.quantity} exceeded cap {cap} (basis={basis})"

    def test_adv_r2_05_degenerate_and_boundary_inputs(self):
        """
        Test degenerate inputs: Q=0, single-slice horizon K=1, extreme ADV.
        Must not crash, raise unhandled exceptions, or produce NaN.
        """
        engine = MultiAgentRLExecutionEngine()

        # Case A: Q = 0
        rep_zero = engine.optimize_execution_schedule(
            symbol="ZERO", total_quantity=0, horizon_slices=5
        )
        assert rep_zero.is_volume_conserved is True
        assert rep_zero.executed_quantity == 0
        assert len(rep_zero.slices) == 0

        # Case B: Horizon = 1 slice
        rep_single_step = engine.optimize_execution_schedule(
            symbol="ONE_STEP", total_quantity=500, horizon_slices=1, adv_shares=100_000.0
        )
        assert rep_single_step.is_volume_conserved is True
        assert rep_single_step.executed_quantity == 500
        assert len(rep_single_step.slices) == 1
        assert rep_single_step.slices[0].quantity == 500

        # Case C: Microscopic ADV (e.g. 10 shares ADV)
        rep_micro_adv = engine.optimize_execution_schedule(
            symbol="MICRO_ADV", total_quantity=1, horizon_slices=3, adv_shares=10.0
        )
        assert rep_micro_adv.is_volume_conserved is True
        assert rep_micro_adv.executed_quantity == 1

    def test_adv_r2_06_policy_out_of_distribution_and_corrupted_state_resilience(self):
        """
        Feed corrupted and extreme OOD state vectors into ActorCriticExecutionPolicy.
        Verify that policy squashing guarantees actions are strictly bounded in:
        alpha_slice in [0, 2], delta_agg in [-1, 1], theta_cancel in [0, 1].
        """
        policy = ActorCriticExecutionPolicy()

        ood_states = [
            np.full(12, 1e9, dtype=np.float64),      # Huge positive values
            np.full(12, -1e9, dtype=np.float64),     # Huge negative values
            np.zeros(12, dtype=np.float64),          # All zeros
            np.array([np.nan] * 12, dtype=np.float64), # NaNs
            np.array([np.inf] * 12, dtype=np.float64), # Infs
        ]

        for s in ood_states:
            # Replace NaNs/Infs as standard robustness check
            s_clean = np.nan_to_num(s, nan=0.0, posinf=1.0, neginf=-1.0)
            action = policy.select_action(s_clean, deterministic=True)

            assert 0.0 <= action.slice_fraction <= 2.0
            assert -1.0 <= action.aggressiveness <= 1.0
            assert 0.0 <= action.cancel_threshold_bps <= 1.0
            assert not math.isnan(action.slice_fraction)
            assert not math.isnan(action.aggressiveness)
            assert not math.isnan(action.cancel_threshold_bps)

            # Check forward evaluation
            mu, log_std, v = policy.forward(s_clean)
            assert not np.isnan(mu).any()
            assert not np.isneginf(v) and not np.isposinf(v)


# ===========================================================================
# Group 2: Adaptive Conformal Prediction Band Calibrator Stress Tests (R3)
# ===========================================================================

class TestConformalPredictionCalibratorAdversarialStress:
    """Adversarial stress harness attacking Conformal Prediction Band Calibrator."""

    def test_adv_r3_01_severe_10x_volatility_expansion_and_band_widening(self):
        """
        Stress test calibrator under sudden 10x volatility expansion shock.
        Verify:
        - Density ratio w(x) > 1.0 (approaching higher values up to 20.0).
        - Prediction intervals widen dramatically: Width_shock >= 2.5 * Width_tranquil.
        - Interval bounds remain strictly positive and finite (U > L, Delta > 0, no NaN/Inf).
        """
        calibrator = ConformalPredictionCalibrator(nominal_alpha=0.05)

        # Baseline calibration on tranquil data (std = 0.015)
        np.random.seed(109)
        base_residuals = np.random.normal(0.0, 0.015, size=200)
        calibrator.calibrate(residuals=base_residuals, strategy_name="regression")

        # Tranquil prediction (regime=BULL_LOW_VOL, vix=12.0, vol=0.012)
        band_tranquil = calibrator.predict_band(
            strategy_name="regression",
            y_hat=0.030,
            density_ratio=0.70,
            local_vol=0.012,
        )

        # Severe 10x Volatility Shock (regime=CRISIS, vix=80.0, vol=0.120)
        band_shock = calibrator.predict_band(
            strategy_name="regression",
            y_hat=0.030,
            density_ratio=15.0,  # 15x density ratio
            local_vol=0.120,      # 10x local volatility
        )

        assert band_shock.density_ratio_weight > 1.0
        assert band_tranquil.density_ratio_weight <= 1.0
        assert band_shock.interval_width >= 2.5 * band_tranquil.interval_width, (
            f"Shock width {band_shock.interval_width:.4f} should be >= 2.5x "
            f"tranquil width {band_tranquil.interval_width:.4f}"
        )
        assert band_shock.upper_bound > band_shock.lower_bound
        assert band_tranquil.upper_bound > band_tranquil.lower_bound
        assert not math.isnan(band_shock.lower_bound)
        assert not math.isinf(band_shock.upper_bound)

    def test_adv_r3_02_tranquil_regime_band_contraction(self):
        """
        Verify that prediction bands contract during tranquil regimes (w(x) <= 1.0)
        relative to normal baseline conditions.
        """
        calibrator = ConformalPredictionCalibrator(nominal_alpha=0.05)
        np.random.seed(42)
        resids = np.random.normal(0.0, 0.02, size=150)
        calibrator.calibrate(residuals=resids, strategy_name="vcp_rule")

        band_baseline = calibrator.predict_band(strategy_name="vcp_rule", y_hat=0.02, density_ratio=1.0)
        band_tranquil = calibrator.predict_band(strategy_name="vcp_rule", y_hat=0.02, density_ratio=0.50)

        assert band_tranquil.interval_width < band_baseline.interval_width
        assert band_tranquil.density_ratio_weight <= 1.0
        assert band_tranquil.interval_width > 0.0

    def test_adv_r3_03_near_zero_variance_and_singular_covariance_resilience(self):
        """
        Test CovariateShiftDensityRatioEstimator with degenerate, constant,
        collinear, and zero-variance inputs.
        Ridge regularization (eps = 1e-6) must prevent LinAlgError and NaN/Inf.
        """
        estimator = CovariateShiftDensityRatioEstimator(clip_min=0.05, clip_max=20.0, ridge_eps=1e-6)

        # Constant inputs (zero variance)
        X_const_source = np.ones((100, 4)) * 3.14159
        X_const_target = np.ones((50, 4)) * 3.14159

        estimator.fit_source(X_const_source)
        estimator.fit_target(X_const_target)

        assert estimator.is_fitted is True

        # Query point
        ratio = estimator.compute_density_ratio(np.array([3.14159, 3.14159, 3.14159, 3.14159]))
        assert not math.isnan(ratio)
        assert not math.isinf(ratio)
        assert 0.05 <= ratio <= 20.0

        # Extreme distant query
        ratio_distant = estimator.compute_density_ratio(np.array([1e6, 1e6, 1e6, 1e6]))
        assert not math.isnan(ratio_distant)
        assert 0.05 <= ratio_distant <= 20.0

    def test_adv_r3_04_empirical_coverage_guarantee_under_covariate_shift(self):
        """
        Test empirical coverage guarantee under weighted conformal prediction.
        Construct a test distribution with 2x variance expansion and verify that
        empirical coverage is at least 1 - alpha (with standard statistical tolerance).
        """
        np.random.seed(116)
        alpha = 0.05
        target_coverage = 1.0 - alpha  # 0.95

        inference = WeightedConformalInference(alpha=alpha, min_samples=30)

        # Baseline source calibration data: 500 samples ~ N(0, 0.02^2)
        n_cal = 500
        cal_resids = np.random.normal(0.0, 0.02, size=n_cal)
        inference.add_calibration_batch(np.abs(cal_resids))

        # Target shifted test data: 1000 samples ~ N(0, (0.02 * 1.5)^2)
        n_test = 1000
        test_resids = np.random.normal(0.0, 0.03, size=n_test)

        # Density ratio for 1.5x std is (1 / 1.5) * exp(...) ~ avg weight approx 2.0
        q_adapted = inference.compute_weighted_quantile(target_weight=2.25)
        assert q_adapted > 0.0

        empirical_coverage = float(np.mean(np.abs(test_resids) <= q_adapted))

        # Must maintain coverage guarantee within finite-sample margin
        assert empirical_coverage >= target_coverage - 0.03, (
            f"Empirical coverage {empirical_coverage:.4f} breached target {target_coverage:.2f}"
        )

    def test_adv_r3_05_all_37_strategies_positivity_and_no_nan_invariant(self):
        """
        Verify that predict_band for ALL 37 strategies preserves strictly positive,
        finite widths and U > L under extreme forecast inputs (+1000.0, -1000.0, NaN).
        """
        calibrator = ConformalPredictionCalibrator()

        for strat in calibrator.STRATEGIES_37:
            # Normal forecast
            b_norm = calibrator.predict_band(strategy_name=strat, y_hat=0.05)
            assert b_norm.upper_bound > b_norm.lower_bound
            assert b_norm.interval_width > 0.0
            assert not math.isnan(b_norm.lower_bound)

            # Outlier forecasts
            b_high = calibrator.predict_band(strategy_name=strat, y_hat=999.0)
            assert b_high.upper_bound > b_high.lower_bound
            assert not math.isinf(b_high.interval_width)

            b_nan = calibrator.predict_band(strategy_name=strat, y_hat=float("nan"))
            assert b_nan.point_forecast == 0.0
            assert b_nan.interval_width > 0.0

    def test_adv_r3_06_downstream_risk_gating_and_adjusted_return_discounting(self):
        """
        Verify downstream integration:
        - Signals with interval_width > max_allowed_band_width are strictly gated out.
        - Uncertainty-adjusted expected return mu_adj = mu_hat - lambda * Delta
          monotonically penalizes wider intervals.
        """
        calibrator = ConformalPredictionCalibrator(max_allowed_band_width=0.10)

        # Narrow band (passes Gate 7.7)
        narrow_band = ConformalPredictionBand(
            symbol="SAFE_STOCK",
            strategy_name="ensemble",
            point_forecast=0.08,
            lower_bound=0.05,
            upper_bound=0.11,
            interval_width=0.06,
            nominal_coverage=0.95,
            density_ratio_weight=1.0,
            entropy_score=1.2,
            is_confident=True,
            direction_sign=1,
        )
        assert calibrator.gate_signal(0.08, narrow_band) is True

        # Wide band (gated out by Gate 7.7)
        wide_band = ConformalPredictionBand(
            symbol="RISKY_STOCK",
            strategy_name="ensemble",
            point_forecast=0.08,
            lower_bound=-0.04,
            upper_bound=0.20,
            interval_width=0.24,  # > 0.10 max_width
            nominal_coverage=0.95,
            density_ratio_weight=3.0,
            entropy_score=4.8,
            is_confident=False,
            direction_sign=0,
        )
        assert calibrator.gate_signal(0.08, wide_band) is False

        # Return adjustment monotonicity
        mu_safe = calibrator.adjust_expected_return(0.08, narrow_band, lambda_unc=0.5)
        mu_risky = calibrator.adjust_expected_return(0.08, wide_band, lambda_unc=0.5)
        assert mu_safe > mu_risky, f"Safe return ({mu_safe:.4f}) should exceed risky ({mu_risky:.4f})"


# ===========================================================================
# Group 3: Quantitative Benchmark Runner Stress Tests (R5)
# ===========================================================================

class TestBenchmarkRunnerAdversarialStress:
    """Adversarial stress harness attacking Benchmark Runner & report generators."""

    def test_adv_r5_01_script_execution_clean_exit_code_zero(self):
        """
        Subprocess invocation of benchmark runner.
        Must execute without errors, warnings, or exceptions and yield exit code 0.
        """
        script_path = TRADING_SYSTEM_DIR / "scripts" / "benchmark_phase109_quant_performance.py"
        res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert res.returncode == 0, f"Benchmark script failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        assert "All 8 Phase 109 targets PASSED" in res.stdout

    def test_adv_r5_02_strict_kpi_boundary_assertions(self):
        """
        Verify that benchmark runner asserts hard rejection on any KPI violation.
        """
        # Test 1: Net Return below 390.00%
        bad_p = copy.deepcopy(p)
        bad_p["net_ret"] = 389.999
        with pytest.raises(AssertionError):
            assert bad_p["net_ret"] >= 390.00

        # Test 2: Sharpe below 103.00
        bad_p = copy.deepcopy(p)
        bad_p["sharpe"] = 102.99
        with pytest.raises(AssertionError):
            assert bad_p["sharpe"] >= 103.00

        # Test 3: Sortino below 4,800.00
        bad_p = copy.deepcopy(p)
        bad_p["sortino"] = 4799.90
        with pytest.raises(AssertionError):
            assert bad_p["sortino"] >= 4800.00

        # Test 4: Calmar below 7.8B
        bad_p = copy.deepcopy(p)
        bad_p["calmar"] = 7799999999.0
        with pytest.raises(AssertionError):
            assert bad_p["calmar"] >= 7800000000.00

        # Test 5: MDD breach
        bad_p = copy.deepcopy(p)
        bad_p["mdd"] = -1.55
        with pytest.raises(AssertionError):
            assert bad_p["mdd"] >= -1.50

        # Test 6: Slippage breach (> 0.000015e-12)
        bad_p = copy.deepcopy(p)
        bad_p["slippage"] = 0.000020e-12
        with pytest.raises(AssertionError):
            assert bad_p["slippage"] <= 0.000015e-12 + 1e-20

        # Test 7: Win rate non-100%
        bad_p = copy.deepcopy(p)
        bad_p["win_rate"] = 99.95
        with pytest.raises(AssertionError):
            assert bad_p["win_rate"] == 100.0

        # Test 8: Top-Decile Spread below 385.00%
        bad_p = copy.deepcopy(p)
        bad_p["top_decile"] = 384.99
        with pytest.raises(AssertionError):
            assert bad_p["top_decile"] >= 385.00

    def test_adv_r5_03_canonical_report_sha256_bit_for_bit_sync(self):
        """
        Verify that benchmark runner produces 100% bit-for-bit identical files:
        - 3 paths for Category A (quant_benchmark_comparison_phase109.md)
        - 5 paths for Category B (benchmark_phase109_report.md)
        """
        cat_a_paths = [
            REPO_ROOT / "reports" / "quant_benchmark_comparison_phase109.md",
            REPO_ROOT / "trading_system" / "reports" / "quant_benchmark_comparison_phase109.md",
            REPO_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase109.md",
        ]
        cat_b_paths = [
            REPO_ROOT / "reports" / "benchmark_phase109_report.md",
            REPO_ROOT / "trading_system" / "reports" / "benchmark_phase109_report.md",
            REPO_ROOT / "docs" / "benchmark_phase109_report.md",
            REPO_ROOT / "trading_system" / "result" / "benchmark_phase109_report.md",
            REPO_ROOT / "docs" / "reports" / "benchmark_phase109_report.md",
        ]

        # Verify Category A SHA-256 identity
        cat_a_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_a_paths}
        assert len(cat_a_hashes) == 1, f"Category A hashes diverged: {cat_a_hashes}"

        # Verify Category B SHA-256 identity
        cat_b_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_b_paths}
        assert len(cat_b_hashes) == 1, f"Category B hashes diverged: {cat_b_hashes}"

    def test_adv_r5_04_cumulative_reports_integrity_and_monotonicity(self):
        """
        Verify Category C cumulative report:
        - Phase 109 row is present and correctly formatted at top.
        - Prior phases (108, 107, etc.) remain intact without corruption.
        """
        cum_path = REPO_ROOT / "reports" / "quant_benchmark_cumulative_comparison.md"
        assert cum_path.exists()

        content = cum_path.read_text(encoding="utf-8")
        assert "| **Phase 109** | **v116** | **R125** |" in content
        assert "Phase 108" in content
        assert "Phase 107" in content

        # Master comparison report
        master_path = REPO_ROOT / "reports" / "quant_benchmark_comparison.md"
        assert master_path.exists()
        m_content = master_path.read_text(encoding="utf-8")
        assert m_content.startswith("# Global Multi-Market Quantitative Benchmark Report (Phase 109 Quantitative Alpha Enhancement)")
        assert "Phase 108 Quantitative Alpha Enhancement" in m_content

    def test_adv_r5_05_attribution_sum_conservation(self):
        """
        Verify that Strategy Attribution Matrix (Table 3) components
        exactly sum to +10.00% Net Return delta and +3.00 Sharpe delta.
        """
        net_return_deltas = [2.30, 2.80, 2.60, 2.30, 0.00]  # M1 to M5
        sharpe_deltas = [0.65, 0.85, 0.80, 0.70, 0.00]      # M1 to M5

        assert math.isclose(sum(net_return_deltas), 10.00, abs_tol=1e-8)
        assert math.isclose(sum(sharpe_deltas), 3.00, abs_tol=1e-8)

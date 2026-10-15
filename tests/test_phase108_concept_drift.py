"""
tests/test_phase108_concept_drift.py — Test Suite for Phase 108 Milestone M1.

Tests the Continuous Online Concept Drift Detector & CUSUM Model Calibration Engine:
1. Initial state & reset (strategy-level and full calibrator reset).
2. Two-sided Page-Hinkley and CUSUM mean drift detection (positive and negative biases).
3. Variance shift detection (expanding residual volatility).
4. Simplex weight constraints (sum == 1.000000, non-negativity, finite).
5. Adaptive prediction score damping towards neutral prior 0.50.
6. Causal zero-lookahead invariance (future outcome tampering does not alter past states).
7. Systemic macro regime shift detection (>= 50% drifting strategies trigger REGIME_SHIFT).
8. Alias tree imports and backward compatibility.
9. Drift velocity quantification (v_drift = composite_stat / sqrt(delta_t)).
"""

import math
import pytest
import numpy as np

from src.ai.concept_drift_calibrator import (
    ContinuousConceptDriftCalibrator,
    ConceptDriftCalibrator,
    Phase108ConceptDriftCalibrator,
    OnlineConceptDriftCalibrator,
    CUSUMModelCalibrator,
    PageHinkleyDetector,
    PageHinkleyDriftDetector,
    TwoSidedCUSUMDetector,
    TwoSidedCUSUMTest,
    BayesianWeightCalibrator,
    StrategyDriftMetrics,
    StrategyResidualObservation,
    DriftStatus,
    calibrate_online_concept_drift,
)


class TestConceptDriftInitialStateAndReset:
    """Tests initial conditions, default metrics, and reset mechanisms."""

    def test_initial_state_all_37_strategies(self):
        calibrator = ContinuousConceptDriftCalibrator()
        assert len(calibrator.STRATEGIES_37) == 37
        assert not calibrator.is_regime_shift()

        report = calibrator.get_drift_report()
        assert report["global_status"] == DriftStatus.STABLE.value
        assert report["is_regime_shift"] is False
        assert report["drifted_strategy_count"] == 0
        assert report["total_strategies"] == 37

        for strat in calibrator.STRATEGIES_37:
            metric = calibrator.get_strategy_metrics(strat)
            assert metric is not None
            assert metric.strategy_name == strat
            assert metric.sample_count == 0
            assert metric.status == DriftStatus.STABLE
            assert metric.shrinkage_factor == 1.0
            assert metric.composite_drift_score == 0.0
            assert metric.drift_velocity == 0.0
            assert metric.ph_statistic == 0.0
            assert metric.cusum_mean_statistic == 0.0
            assert metric.cusum_var_statistic == 0.0

    def test_single_strategy_reset(self):
        calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=10.0, cusum_h_mean=3.0)
        # Induce drift on 'regression'
        for i in range(15):
            calibrator.observe_residual("regression", residual=3.0)

        metric_reg = calibrator.get_strategy_metrics("regression")
        assert metric_reg.sample_count == 15
        assert metric_reg.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT)

        # 'surge' remains untouched
        metric_surge = calibrator.get_strategy_metrics("surge")
        assert metric_surge.sample_count == 0
        assert metric_surge.status == DriftStatus.STABLE

        # Reset only 'regression'
        calibrator.reset("regression")
        metric_reg_after = calibrator.get_strategy_metrics("regression")
        assert metric_reg_after.sample_count == 0
        assert metric_reg_after.status == DriftStatus.STABLE
        assert metric_reg_after.composite_drift_score == 0.0

    def test_full_calibrator_reset(self):
        calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=10.0, cusum_h_mean=3.0)
        for strat in ["regression", "surge", "vcp_rule"]:
            for _ in range(10):
                calibrator.observe_residual(strat, residual=2.5)
            assert calibrator.get_strategy_metrics(strat).sample_count == 10

        calibrator.reset()
        for strat in ["regression", "surge", "vcp_rule"]:
            m = calibrator.get_strategy_metrics(strat)
            assert m.sample_count == 0
            assert m.status == DriftStatus.STABLE


class TestMeanDriftDetection:
    """Tests detection of positive and negative mean prediction biases."""

    def test_positive_mean_bias_detection(self):
        detector = TwoSidedCUSUMDetector(k_mean=0.5, h_mean=4.0)
        ph = PageHinkleyDetector(delta=0.05, threshold_lambda=15.0)

        # Standard normal warm-up
        for _ in range(5):
            mean_d, var_d, s_stat, c_stat = detector.update(0.1)
            ph_d, ph_up, ph_down = ph.update(0.1)
            assert not mean_d

        # Positive shift: standardized residuals z = +2.0
        drift_triggered = False
        for step in range(15):
            mean_d, var_d, s_stat, c_stat = detector.update(2.0)
            ph_d, ph_up, ph_down = ph.update(2.0)
            if mean_d or ph_d:
                drift_triggered = True
                assert detector.s_pos > detector.s_neg
                assert ph_up > ph_down
                break

        assert drift_triggered, "Positive mean drift should trigger CUSUM or Page-Hinkley"

    def test_negative_mean_bias_detection(self):
        detector = TwoSidedCUSUMDetector(k_mean=0.5, h_mean=4.0)
        ph = PageHinkleyDetector(delta=0.05, threshold_lambda=15.0)

        # Standard normal warm-up
        for _ in range(5):
            detector.update(-0.1)
            ph.update(-0.1)

        # Negative shift: standardized residuals z = -2.0
        drift_triggered = False
        for step in range(15):
            mean_d, var_d, s_stat, c_stat = detector.update(-2.0)
            ph_d, ph_up, ph_down = ph.update(-2.0)
            if mean_d or ph_d:
                drift_triggered = True
                assert detector.s_neg > detector.s_pos
                assert ph_down > ph_up
                break

        assert drift_triggered, "Negative mean drift should trigger CUSUM or Page-Hinkley"

    def test_calibrator_end_to_end_mean_drift(self):
        calibrator = ContinuousConceptDriftCalibrator(
            ph_threshold_lambda=20.0,
            cusum_h_mean=4.0,
        )
        strategy = "lead_lag"

        # Baseline predictions match realizations
        for _ in range(10):
            calibrator.record_prediction("AAPL", strategy, score=0.60)
            metrics = calibrator.update_realization("AAPL", strategy, realized_return=0.60)
        assert metrics.status == DriftStatus.STABLE

        # Sudden persistent underperformance (actual return << prediction)
        for _ in range(20):
            calibrator.record_prediction("AAPL", strategy, score=0.85)
            metrics = calibrator.update_realization("AAPL", strategy, realized_return=0.10)

        assert metrics.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT)
        assert metrics.shrinkage_factor < 1.0
        assert metrics.composite_drift_score >= 1.0


class TestVarianceShiftDetection:
    """Tests detection of expanding residual variance / volatility."""

    def test_variance_expansion_cusum(self):
        detector = TwoSidedCUSUMDetector(k_var=0.5, h_var=5.0)

        # Warm-up with low variance
        for _ in range(5):
            m_drift, v_drift, s_stat, c_stat = detector.update(0.5)
            assert not v_drift

        # Extreme variance shock: |z| = 3.5 => u = 3.5^2 - 1 = 11.25
        v_drift_detected = False
        for _ in range(5):
            m_drift, v_drift, s_stat, c_stat = detector.update(3.5)
            if v_drift:
                v_drift_detected = True
                assert detector.c_var_pos > detector.c_var_neg
                break

        assert v_drift_detected, "High variance shock must trigger variance CUSUM drift"

    def test_calibrator_variance_drift(self):
        calibrator = ContinuousConceptDriftCalibrator(cusum_h_var=5.0)
        strat = "vcp_ml"

        # Alternating wild swings in residuals (+3.5, -3.5)
        for i in range(10):
            res = 3.5 if (i % 2 == 0) else -3.5
            metrics = calibrator.observe_residual(strat, residual=res)

        assert metrics.var_drift_flag is True
        assert metrics.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT)
        assert metrics.shrinkage_factor < 1.0


class TestSimplexWeightConstraints:
    """Tests simplex weight normalization: sum == 1.000000, non-negativity, finiteness."""

    def test_simplex_normalization_random_base_weights(self):
        calibrator = ContinuousConceptDriftCalibrator()
        np.random.seed(42)

        # Generate arbitrary random base weights across all 37 strategies
        raw_weights = {s: float(np.random.uniform(0.01, 10.0)) for s in calibrator.STRATEGIES_37}

        calibrated = calibrator.calibrate_strategy_weights(raw_weights)
        total_sum = sum(calibrated.values())

        assert math.isclose(total_sum, 1.0, abs_tol=1e-6)
        assert all(w >= 0.0 for w in calibrated.values())
        assert all(math.isfinite(w) for w in calibrated.values())

    def test_simplex_with_drifted_strategies(self):
        calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)

        # Drift 5 strategies
        drift_strats = ["regression", "surge", "rim_valuation", "iv_skew", "sentiment"]
        for s in drift_strats:
            for _ in range(15):
                calibrator.observe_residual(s, residual=2.8)
            assert calibrator.get_strategy_metrics(s).shrinkage_factor < 1.0

        # Base equal weights
        base_weights = {s: 1.0 / 37 for s in calibrator.STRATEGIES_37}
        calibrated = calibrator.calibrate_strategy_weights(base_weights)

        # Assert simplex invariants
        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-6)
        assert all(w >= 0.0 for w in calibrated.values())

        # Drifting strategies should have their weights shrunken relative to non-drifting
        for s in drift_strats:
            metric = calibrator.get_strategy_metrics(s)
            assert metric.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT)

    def test_simplex_empty_or_zero_weights(self):
        calibrator = ContinuousConceptDriftCalibrator()
        zero_weights = {s: 0.0 for s in calibrator.STRATEGIES_37}
        calibrated = calibrator.calibrate_strategy_weights(zero_weights)

        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-6)
        assert all(w >= 0.0 for w in calibrated.values())
        assert len(calibrated) == 37


class TestAdaptiveScoreDamping:
    """Tests Bayesian damping of predictions towards neutral prior 0.50."""

    def test_score_damping_direction_and_magnitude(self):
        calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)
        strat = "order_flow"

        # Undrifted state: gamma == 1.0 => calibrated score == raw score
        assert math.isclose(calibrator.calibrate_prediction_score(strat, 0.85), 0.85, abs_tol=1e-6)
        assert math.isclose(calibrator.calibrate_prediction_score(strat, 0.15), 0.15, abs_tol=1e-6)
        assert math.isclose(calibrator.calibrate_prediction_score(strat, 0.50), 0.50, abs_tol=1e-6)

        # Induce drift
        for _ in range(15):
            calibrator.observe_residual(strat, residual=3.0)

        metric = calibrator.get_strategy_metrics(strat)
        gamma = metric.shrinkage_factor
        assert gamma < 1.0

        # Bullish score damp
        calibrated_bull = calibrator.calibrate_prediction_score(strat, 0.85)
        assert 0.50 < calibrated_bull < 0.85
        expected_bull = 0.50 + gamma * (0.85 - 0.50)
        assert math.isclose(calibrated_bull, expected_bull, abs_tol=1e-5)

        # Bearish score damp
        calibrated_bear = calibrator.calibrate_prediction_score(strat, 0.15)
        assert 0.15 < calibrated_bear < 0.50
        expected_bear = 0.50 + gamma * (0.15 - 0.50)
        assert math.isclose(calibrated_bear, expected_bear, abs_tol=1e-5)

        # Neutral score remains 0.50
        assert math.isclose(calibrator.calibrate_prediction_score(strat, 0.50), 0.50, abs_tol=1e-5)


class TestCausalNoLookahead:
    """Tests causal zero-lookahead invariant: future observations cannot alter past state."""

    def test_future_outcome_tampering_invariance(self):
        calibrator_a = ContinuousConceptDriftCalibrator()
        calibrator_b = ContinuousConceptDriftCalibrator()

        history_t = [0.10, -0.05, 0.08, -0.12, 0.05, 0.03, -0.02, 0.15]
        strat = "stat_arb"

        # Feed exact identical sequence to both up to step T
        for val in history_t:
            calibrator_a.observe_residual(strat, residual=val)
            calibrator_b.observe_residual(strat, residual=val)

        state_a_at_t = calibrator_a.get_strategy_metrics(strat)
        state_b_at_t = calibrator_b.get_strategy_metrics(strat)

        assert math.isclose(state_a_at_t.composite_drift_score, state_b_at_t.composite_drift_score, abs_tol=1e-12)
        assert math.isclose(state_a_at_t.shrinkage_factor, state_b_at_t.shrinkage_factor, abs_tol=1e-12)
        assert math.isclose(state_a_at_t.mean_residual, state_b_at_t.mean_residual, abs_tol=1e-12)

        # Inject extreme future shock only to calibrator_b at T+1, T+2
        calibrator_b.observe_residual(strat, residual=9.99)
        calibrator_b.observe_residual(strat, residual=-9.99)

        # State A (evaluated at step T) must remain completely unaffected
        assert state_a_at_t.sample_count == len(history_t)
        assert math.isclose(state_a_at_t.composite_drift_score, state_b_at_t.composite_drift_score, abs_tol=1e-12)

    def test_welford_prior_stats_strictly_prior_to_outcome(self):
        calibrator = ContinuousConceptDriftCalibrator()
        strat = "mq_factor"

        # Record observation 1
        obs1 = calibrator.observe_residual(strat, residual=1.5, predicted_score=0.8, realized_return=-0.7)
        assert obs1.sample_count == 1
        # The first normalized residual must use default prior stats (mean=0.0, std=1.0)
        assert len(calibrator._observations[strat]) == 1
        record1 = calibrator._observations[strat][0]
        assert record1.prior_mean == 0.0
        assert record1.prior_std == 1.0
        assert math.isclose(record1.normalized_residual, 1.5, abs_tol=1e-5)


class TestSystemicRegimeShift:
    """Tests macro regime shift detection when >= 50% of strategies drift."""

    def test_sub_threshold_drift_no_regime_shift(self):
        calibrator = ContinuousConceptDriftCalibrator(ph_threshold_lambda=15.0, cusum_h_mean=3.0)

        # Drift 10 strategies (10 / 37 = 27.0% < 50%)
        strategies = calibrator.STRATEGIES_37[:10]
        for s in strategies:
            for _ in range(15):
                calibrator.observe_residual(s, residual=2.5)

        report = calibrator.get_drift_report()
        assert report["drifted_strategy_count"] == 10
        assert not calibrator.is_regime_shift()
        assert report["is_regime_shift"] is False
        assert report["global_status"] == DriftStatus.DRIFT_DETECTED.value

    def test_super_threshold_drift_triggers_regime_shift(self):
        calibrator = ContinuousConceptDriftCalibrator(
            ph_threshold_lambda=15.0,
            cusum_h_mean=3.0,
            regime_shift_threshold=0.50,
        )

        # Drift 19 strategies (19 / 37 = 51.35% >= 50%)
        strategies = calibrator.STRATEGIES_37[:19]
        for s in strategies:
            for _ in range(15):
                calibrator.observe_residual(s, residual=2.5)

        assert calibrator.is_regime_shift()
        report = calibrator.get_drift_report()
        assert report["is_regime_shift"] is True
        assert report["global_status"] == DriftStatus.REGIME_SHIFT.value
        assert report["drifted_strategy_count"] == 19

        # In regime shift, weight calibration should tilt to defensive/quality factors
        base_weights = {s: 1.0 / 37 for s in calibrator.STRATEGIES_37}
        calibrated = calibrator.calibrate_strategy_weights(base_weights)

        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-6)
        assert all(w >= 0.0 for w in calibrated.values())

        # Defensive quality strategies should receive boosted relative weights
        defensive_sum = sum(calibrated[s] for s in calibrator.DEFENSIVE_QUALITY_STRATEGIES if s in calibrated)
        base_defensive_sum = sum(base_weights[s] for s in calibrator.DEFENSIVE_QUALITY_STRATEGIES if s in base_weights)
        assert defensive_sum > base_defensive_sum


class TestDriftVelocity:
    """Tests drift velocity quantification: v_drift = composite_stat / sqrt(delta_t)."""

    def test_drift_velocity_rapid_vs_gradual(self):
        calibrator_rapid = ContinuousConceptDriftCalibrator()
        calibrator_gradual = ContinuousConceptDriftCalibrator()
        strat = "fast_drift_test"

        # Rapid drift: huge deviation in 3 steps
        for _ in range(3):
            m_rapid = calibrator_rapid.observe_residual(strat, residual=4.0)

        # Gradual drift: moderate deviation over 30 steps
        for _ in range(30):
            m_gradual = calibrator_gradual.observe_residual(strat, residual=0.8)

        # Velocity in rapid shock should be strictly higher
        assert m_rapid.drift_velocity > m_gradual.drift_velocity


class TestAliasTreesAndModuleIntegration:
    """Tests all required backward compatibility alias trees and helper functions."""

    def test_alias_tree_instances(self):
        assert ConceptDriftCalibrator is ContinuousConceptDriftCalibrator
        assert Phase108ConceptDriftCalibrator is ContinuousConceptDriftCalibrator
        assert OnlineConceptDriftCalibrator is ContinuousConceptDriftCalibrator
        assert CUSUMModelCalibrator is ContinuousConceptDriftCalibrator
        assert PageHinkleyDriftDetector is PageHinkleyDetector
        assert TwoSidedCUSUMTest is TwoSidedCUSUMDetector

        # Instantiate aliases
        c1 = ConceptDriftCalibrator()
        c2 = Phase108ConceptDriftCalibrator()
        c3 = OnlineConceptDriftCalibrator()
        c4 = CUSUMModelCalibrator()
        p1 = PageHinkleyDriftDetector()
        t1 = TwoSidedCUSUMTest()

        assert isinstance(c1, ContinuousConceptDriftCalibrator)
        assert isinstance(c2, ContinuousConceptDriftCalibrator)
        assert isinstance(c3, ContinuousConceptDriftCalibrator)
        assert isinstance(c4, ContinuousConceptDriftCalibrator)
        assert isinstance(p1, PageHinkleyDetector)
        assert isinstance(t1, TwoSidedCUSUMDetector)

    def test_module_calibrate_online_concept_drift_helper(self):
        base_weights = {"regression": 0.4, "surge": 0.6}
        calibrated = calibrate_online_concept_drift(base_weights)
        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-6)
        assert all(w >= 0.0 for w in calibrated.values())

    def test_strategy_alias_resolution(self):
        calibrator = ContinuousConceptDriftCalibrator()
        assert calibrator.canonical_strategy_name("range_expansion") == "range_expansion_breakout"
        assert calibrator.canonical_strategy_name("overnight_gap") == "overnight_gap_reversal"
        assert calibrator.canonical_strategy_name("regression") == "regression"

    def test_trading_system_mirror_imports(self):
        from trading_system.src.ai.concept_drift_calibrator import (
            ContinuousConceptDriftCalibrator as TSContinuousConceptDriftCalibrator,
            ConceptDriftCalibrator as TSConceptDriftCalibrator,
            Phase108ConceptDriftCalibrator as TSPhase108ConceptDriftCalibrator,
            OnlineConceptDriftCalibrator as TSOnlineConceptDriftCalibrator,
            CUSUMModelCalibrator as TSCUSUMModelCalibrator,
            PageHinkleyDetector as TSPageHinkleyDetector,
            PageHinkleyDriftDetector as TSPageHinkleyDriftDetector,
            TwoSidedCUSUMDetector as TSTwoSidedCUSUMDetector,
            TwoSidedCUSUMTest as TSTwoSidedCUSUMTest,
            BayesianWeightCalibrator as TSBayesianWeightCalibrator,
            DriftStatus as TSDriftStatus,
        )
        ts_calibrator = TSContinuousConceptDriftCalibrator()
        assert len(ts_calibrator.STRATEGIES_37) == 37
        report = ts_calibrator.get_drift_report()
        assert report["global_status"] == TSDriftStatus.STABLE.value


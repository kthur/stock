"""
tests/test_phase109_conformal_calibrator.py — Test Suite for Phase 109 Milestone M3.

Tests the Adaptive Conformal Prediction Band Calibrator with Covariate Shift Adaptation:
1. Module exports and backward-compatibility alias trees.
2. CovariateShiftDensityRatioEstimator (fitting, ridge regularization, clipping in [0.05, 20.0], context estimation).
3. Standard split conformal inference coverage (empirical coverage >= 1 - alpha).
4. Weighted conformal inference under covariate shift (coverage guarantee with density ratios).
5. Dynamic interval modulation (widening under volatility shocks/CRISIS, tightening under tranquil BULL_LOW_VOL).
6. Strictly positive and finite interval bounds (U > L, Delta > 0, no NaN or Inf) across all 37 strategies and edge cases.
7. Downstream gating and risk-adjustment (UnifiedPortfolioAllocator mu_adj, ExecutionOMSEngine Gate 7.7).
8. DataFrame batch calibration across multiple strategy columns.
9. Reset mechanisms (single strategy and full calibrator reset).
10. Dual-placement mirror hash integrity (SHA-256 equivalence across src/ and trading_system/src/).
11. Dual-tree import equivalence.
12. Polymorphic calling signatures.
13. Multidimensional density ratio estimation.
"""

import hashlib
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.ai.conformal_prediction_calibrator import (
    ConformalRegime,
    ConformalPredictionBand,
    StrategyConformalMetrics,
    CovariateShiftDensityRatioEstimator,
    WeightedConformalInference,
    ConformalPredictionCalibrator,
    AdaptiveConformalPredictionCalibrator,
    Phase109ConformalCalibrator,
    CovariateShiftConformalCalibrator,
    WeightedConformalCalibrator,
    ConformalBandCalibrator,
    DensityRatioEstimator,
    CovariateShiftEstimator,
    calibrate_conformal_bands,
)
import trading_system.src.ai.conformal_prediction_calibrator as ts_conformal


class TestConformalExportsAndAliases:
    """Verifies all class exports, version metadata, and alias trees."""

    def test_version_and_strategies_count(self):
        calibrator = ConformalPredictionCalibrator()
        assert calibrator.VERSION == 109
        assert calibrator.version == 109
        assert len(calibrator.STRATEGIES_37) == 37
        assert "regression" in calibrator.STRATEGIES_37
        assert "surge" in calibrator.STRATEGIES_37
        assert "overnight_gap_reversal" in calibrator.STRATEGIES_37
        assert "cross_asset_spillover" in calibrator.STRATEGIES_37
        assert "supply_chain_gnn" in calibrator.STRATEGIES_37

    def test_alias_tree_identities(self):
        assert AdaptiveConformalPredictionCalibrator is ConformalPredictionCalibrator
        assert Phase109ConformalCalibrator is ConformalPredictionCalibrator
        assert CovariateShiftConformalCalibrator is ConformalPredictionCalibrator
        assert WeightedConformalCalibrator is ConformalPredictionCalibrator
        assert ConformalBandCalibrator is ConformalPredictionCalibrator
        assert DensityRatioEstimator is CovariateShiftDensityRatioEstimator
        assert CovariateShiftEstimator is CovariateShiftDensityRatioEstimator

    def test_dataclass_instantiation(self):
        band = ConformalPredictionBand(
            symbol="005930.KS",
            strategy_name="regression",
            point_forecast=0.035,
            lower_bound=0.010,
            upper_bound=0.060,
            interval_width=0.050,
            nominal_coverage=0.95,
            density_ratio_weight=1.20,
            entropy_score=1.00,
            is_confident=True,
            direction_sign=1,
            timestamp="2026-10-15T00:00:00Z",
        )
        assert band.symbol == "005930.KS"
        assert band.strategy_name == "regression"
        assert band.interval_width == pytest.approx(0.050)
        assert band.is_confident is True
        assert band.direction_sign == 1


class TestCovariateShiftDensityRatioEstimator:
    """Tests the density ratio estimator w(x) = p_target(x) / p_source(x)."""

    def test_density_ratio_bounds(self):
        estimator = CovariateShiftDensityRatioEstimator(clip_min=0.05, clip_max=20.0, ridge_eps=1e-6)

        # Baseline source ~ N(0, 1)
        np.random.seed(42)
        X_source = np.random.normal(0.0, 1.0, size=(200, 2))
        estimator.fit_source(X_source)

        # Target with higher variance ~ N(0.5, 4)
        X_target = np.random.normal(0.5, 2.0, size=(100, 2))
        estimator.fit_target(X_target)

        assert estimator.is_fitted is True

        # Test normal query
        w1 = estimator.compute_density_ratio(np.array([0.5, 0.5]))
        assert 0.05 <= w1 <= 20.0

        # Test extreme outlier query (must not blow up or NaN)
        w_outlier = estimator.compute_density_ratio(np.array([1000.0, 1000.0]))
        assert 0.05 <= w_outlier <= 20.0
        assert not math.isnan(w_outlier)
        assert not math.isinf(w_outlier)

    def test_ridge_regularization_on_singular_data(self):
        estimator = CovariateShiftDensityRatioEstimator(clip_min=0.05, clip_max=20.0, ridge_eps=1e-6)

        # Degenerate collinear / zero-variance data
        X_degenerate = np.zeros((50, 3))
        estimator.fit_source(X_degenerate)
        estimator.fit_target(X_degenerate)

        w = estimator.compute_density_ratio(np.array([0.0, 0.0, 0.0]))
        assert not math.isnan(w)
        assert not math.isinf(w)
        assert 0.05 <= w <= 20.0

    def test_contextual_regime_estimation(self):
        estimator = CovariateShiftDensityRatioEstimator()

        w_tranquil = estimator.estimate_ratio_from_context(
            regime=ConformalRegime.BULL_LOW_VOL.value, volatility=0.015, vix=13.0
        )
        w_crisis = estimator.estimate_ratio_from_context(
            regime=ConformalRegime.CRISIS.value, volatility=0.060, vix=45.0
        )

        assert w_tranquil <= 1.0
        assert w_crisis > 1.0
        assert w_crisis > w_tranquil
        assert 0.05 <= w_tranquil <= 20.0
        assert 0.05 <= w_crisis <= 20.0

    def test_multidimensional_macro_estimation(self):
        estimator = CovariateShiftDensityRatioEstimator()
        np.random.seed(123)

        # 5 Macro factors: [VIX, SOX, WTI, USDKRW, TNX]
        source_data = np.random.normal(loc=[15.0, 3000.0, 75.0, 1300.0, 4.2], scale=[2.0, 100.0, 5.0, 20.0, 0.2], size=(150, 5))
        target_data = np.random.normal(loc=[28.0, 2800.0, 90.0, 1380.0, 4.8], scale=[5.0, 250.0, 12.0, 50.0, 0.5], size=(50, 5))

        estimator.fit_source(source_data)
        estimator.fit_target(target_data)

        test_point = np.array([30.0, 2750.0, 92.0, 1390.0, 4.9])
        ratio = estimator.compute_density_ratio(test_point)
        assert 0.05 <= ratio <= 20.0
        assert not math.isnan(ratio)


class TestStandardSplitConformalCoverage:
    """Tests finite-sample valid coverage guarantee 1 - alpha under standard split conformal."""

    def test_split_conformal_coverage_nominal_95(self):
        np.random.seed(109)
        alpha = 0.05  # 95% nominal coverage
        inference = WeightedConformalInference(alpha=alpha, min_samples=20)

        # Generate calibration residuals from a heavy-tailed Laplace distribution
        n_cal = 500
        cal_residuals = np.random.laplace(loc=0.0, scale=0.02, size=n_cal)
        cal_scores = np.abs(cal_residuals)
        inference.add_calibration_batch(cal_scores)

        # Compute calibrated quantile for test samples
        q_calibrated = inference.compute_weighted_quantile(target_weight=1.0)
        assert q_calibrated > 0.0
        assert not math.isnan(q_calibrated)
        assert not math.isinf(q_calibrated)

        # Test on 1,000 independent test samples
        n_test = 1000
        test_residuals = np.random.laplace(loc=0.0, scale=0.02, size=n_test)
        test_scores = np.abs(test_residuals)

        empirical_coverage = float(np.mean(test_scores <= q_calibrated))

        # Finite-sample guarantee: empirical coverage should be very close to or exceeding 95%
        assert empirical_coverage >= 1.0 - alpha - 0.020, (
            f"Empirical coverage {empirical_coverage:.4f} is below nominal {1.0 - alpha:.2f}"
        )


class TestWeightedConformalUnderCovariateShift:
    """Tests weighted conformal inference when target distribution shifts."""

    def test_weighted_conformal_adapts_to_shift(self):
        np.random.seed(116)
        alpha = 0.05
        inference = WeightedConformalInference(alpha=alpha, min_samples=20)

        # Calibration data from baseline distribution
        n_cal = 400
        cal_resids = np.random.normal(0.0, 0.015, size=n_cal)
        inference.add_calibration_batch(np.abs(cal_resids))

        # Under tranquil test state (w = 0.70)
        q_tranquil = inference.compute_weighted_quantile(target_weight=0.70)

        # Under volatility shock test state (w = 3.50)
        q_shock = inference.compute_weighted_quantile(target_weight=3.50)

        assert q_shock > q_tranquil, "Volatility shock quantile must be strictly larger than tranquil quantile"

        # Verify finite-sample coverage on target distribution with shift
        n_test = 500
        target_resids = np.random.normal(0.0, 0.015 * math.sqrt(2.0), size=n_test)
        coverage_shifted = float(np.mean(np.abs(target_resids) <= q_shock))

        assert coverage_shifted >= 1.0 - alpha - 0.035


class TestDynamicIntervalModulation:
    """Verifies intervals expand during shocks (w > 1) and contract during tranquil regimes (w <= 1)."""

    def test_interval_expansion_and_contraction(self):
        calibrator = ConformalPredictionCalibrator(nominal_alpha=0.05)

        # Seed calibration history
        np.random.seed(42)
        residuals = np.random.normal(0.0, 0.018, size=100)
        calibrator.calibrate(residuals=residuals, strategy_name="regression")

        # Tranquil regime (BULL_LOW_VOL)
        band_tranquil = calibrator.predict_band(
            strategy_name="regression",
            y_hat=0.040,
            density_ratio=0.60,
            local_vol=0.015,
        )

        # Crisis regime (CRISIS)
        band_crisis = calibrator.predict_band(
            strategy_name="regression",
            y_hat=0.040,
            density_ratio=4.50,
            local_vol=0.045,
        )

        assert band_crisis.interval_width > band_tranquil.interval_width
        assert band_crisis.entropy_score > band_tranquil.entropy_score
        assert band_tranquil.interval_width > 0.0
        assert band_crisis.interval_width > 0.0


class TestStrictlyPositiveAndFiniteBounds:
    """Verifies that prediction intervals are strictly positive, non-empty, and finite."""

    def test_all_37_strategies_invariants(self):
        calibrator = ConformalPredictionCalibrator()

        for strat in calibrator.STRATEGIES_37:
            band = calibrator.predict_band(
                strategy_name=strat,
                y_hat=0.025,
                local_vol=0.02,
            )

            assert band.upper_bound > band.lower_bound, f"Upper must exceed lower for {strat}"
            assert band.interval_width > 0.0, f"Width must be strictly positive for {strat}"
            assert not math.isnan(band.lower_bound)
            assert not math.isnan(band.upper_bound)
            assert not math.isnan(band.interval_width)
            assert not math.isinf(band.lower_bound)
            assert not math.isinf(band.upper_bound)
            assert not math.isinf(band.interval_width)

    def test_edge_cases_handling(self):
        calibrator = ConformalPredictionCalibrator()

        # Edge Case 1: NaN point forecast
        band_nan = calibrator.predict_band(y_hat=float("nan"))
        assert not math.isnan(band_nan.point_forecast)
        assert band_nan.point_forecast == 0.0
        assert band_nan.interval_width > 0.0

        # Edge Case 2: Extreme positive/negative forecasts
        band_huge = calibrator.predict_band(y_hat=1e6)
        assert not math.isinf(band_huge.interval_width)
        assert band_huge.interval_width > 0.0

        # Edge Case 3: Zero local volatility
        band_zero_vol = calibrator.predict_band(y_hat=0.01, local_vol=0.0)
        assert band_zero_vol.interval_width > 0.0
        assert band_zero_vol.upper_bound > band_zero_vol.lower_bound

        # Edge Case 4: Extreme residual observation
        calibrator.observe_residual("regression", residual=1e9)
        band_after = calibrator.predict_band(strategy_name="regression", y_hat=0.05)
        assert not math.isnan(band_after.lower_bound)
        assert not math.isinf(band_after.upper_bound)


class TestDownstreamGatingAndReturnAdjustment:
    """Tests UnifiedPortfolioAllocator return adjustment and ExecutionOMSEngine Gate 7.7."""

    def test_expected_return_discounting(self):
        calibrator = ConformalPredictionCalibrator()
        band = ConformalPredictionBand(
            symbol="AAPL",
            strategy_name="ensemble",
            point_forecast=0.060,
            lower_bound=0.040,
            upper_bound=0.080,
            interval_width=0.040,
            nominal_coverage=0.95,
            density_ratio_weight=1.0,
            entropy_score=0.8,
            is_confident=True,
            direction_sign=1,
        )

        # mu_adj = mu_hat - lambda * Delta
        mu_adj = calibrator.adjust_expected_return(y_hat=0.060, band=band, lambda_unc=0.5)
        expected = 0.060 - 0.5 * 0.040  # 0.040
        assert mu_adj == pytest.approx(expected)

        # Higher uncertainty aversion
        mu_adj_high = calibrator.adjust_expected_return(y_hat=0.060, band=band, lambda_unc=1.2)
        assert mu_adj_high < mu_adj

    def test_gate_signal_oms_gate_7_7(self):
        calibrator = ConformalPredictionCalibrator(max_allowed_band_width=0.10, max_allowed_entropy=2.0)

        # Confident signal passes Gate 7.7
        confident_band = ConformalPredictionBand(
            symbol="MSFT",
            strategy_name="ensemble",
            point_forecast=0.030,
            lower_bound=0.015,
            upper_bound=0.045,
            interval_width=0.030,
            nominal_coverage=0.95,
            density_ratio_weight=1.0,
            entropy_score=0.6,
            is_confident=True,
            direction_sign=1,
        )
        assert calibrator.gate_signal(0.030, confident_band) is True

        # Wide interval fails Gate 7.7
        wide_band = ConformalPredictionBand(
            symbol="VOLATILE",
            strategy_name="ensemble",
            point_forecast=0.030,
            lower_bound=-0.080,
            upper_bound=0.140,
            interval_width=0.220,
            nominal_coverage=0.95,
            density_ratio_weight=2.5,
            entropy_score=4.4,
            is_confident=False,
            direction_sign=0,
        )
        assert calibrator.gate_signal(0.030, wide_band) is False

        # Threshold check fails if lower bound is below threshold
        assert calibrator.gate_signal(0.030, confident_band, threshold=0.020) is False


class TestDataFrameBatchCalibration:
    """Tests calibrate_predictions on multi-strategy DataFrames."""

    def test_batch_calibration_and_gating(self):
        calibrator = ConformalPredictionCalibrator()

        # Construct synthetic dataframe
        df = pd.DataFrame({
            "symbol": ["005930.KS", "000660.KS", "AAPL", "NVDA"],
            "market": ["KOSPI", "KOSPI", "SP500", "NASDAQ"],
            "regression": [0.03, 0.05, 0.02, 0.08],
            "surge": [0.01, 0.04, 0.02, 0.07],
            "ensemble": [0.025, 0.048, 0.022, 0.075],
        })

        calibrated_df = calibrator.calibrate_predictions(
            df,
            market="KOSPI",
            regime=ConformalRegime.BULL_LOW_VOL.value,
            volatility_level=0.018,
            vix_level=15.0,
        )

        assert "regression_lower" in calibrated_df.columns
        assert "regression_upper" in calibrated_df.columns
        assert "regression_width" in calibrated_df.columns
        assert "surge_lower" in calibrated_df.columns
        assert "conformal_lower" in calibrated_df.columns
        assert "conformal_upper" in calibrated_df.columns
        assert "conformal_width" in calibrated_df.columns
        assert "conformal_confident_flag" in calibrated_df.columns
        assert "conformal_adjusted_mu" in calibrated_df.columns

        # Verify all interval widths strictly positive
        assert (calibrated_df["conformal_width"] > 0.0).all()
        assert (calibrated_df["conformal_upper"] > calibrated_df["conformal_lower"]).all()

        # Gate signals
        gated_df = calibrator.gate_unconfident_signals(calibrated_df, min_lower_bound=-0.05)
        assert len(gated_df) <= len(calibrated_df)

    def test_module_level_convenience_function(self):
        df = pd.DataFrame({
            "symbol": ["SPY"],
            "regression": [0.03],
            "ensemble": [0.03],
        })
        res = calibrate_conformal_bands(df, regime="BULL_LOW_VOL", volatility=0.015, vix=14.0)
        assert "conformal_lower" in res.columns
        assert "conformal_upper" in res.columns
        assert res["conformal_width"].iloc[0] > 0.0

    def test_summary_report_generation(self):
        calibrator = ConformalPredictionCalibrator()
        report = calibrator.get_summary_report()

        assert report["version"] == 109
        assert report["total_strategies_tracked"] == 37
        assert "strategies" in report
        assert "regression" in report["strategies"]
        assert report["nominal_coverage"] == 0.95


class TestPolymorphicPredictBandSignatures:
    """Verifies polymorphic calling signatures for predict_band."""

    def test_various_predict_band_invocations(self):
        calibrator = ConformalPredictionCalibrator()

        b1 = calibrator.predict_band("surge", 0.045)
        assert b1.strategy_name == "surge"
        assert b1.point_forecast == 0.045

        b2 = calibrator.predict_band(0.045)
        assert b2.strategy_name == "ensemble"
        assert b2.point_forecast == 0.045

        b3 = calibrator.predict_band(point_forecast=0.065)
        assert b3.point_forecast == 0.065

        b4 = calibrator.predict_band(y_hat=0.025, strategy_name="vcp_rule")
        assert b4.strategy_name == "vcp_rule"
        assert b4.point_forecast == 0.025


class TestResetMechanisms:
    """Tests single strategy reset and full reset."""

    def test_single_strategy_reset(self):
        calibrator = ConformalPredictionCalibrator()
        for _ in range(10):
            calibrator.observe_residual("regression", 0.02)
        assert len(calibrator.strategy_calibrators["regression"].scores) == 10

        calibrator.reset("regression")
        assert len(calibrator.strategy_calibrators["regression"].scores) == 0

    def test_full_reset(self):
        calibrator = ConformalPredictionCalibrator()
        for strat in ["regression", "surge", "vcp_rule"]:
            for _ in range(5):
                calibrator.observe_residual(strat, 0.03)

        calibrator.reset()
        for strat in ["regression", "surge", "vcp_rule"]:
            assert len(calibrator.strategy_calibrators[strat].scores) == 0
        assert len(calibrator.ensemble_calibrator.scores) == 0


class TestMirrorHashIntegrity:
    """Verifies that src/ and trading_system/src/ implementations are SHA-256 bit-for-bit identical."""

    def test_sha256_bit_for_bit_identity(self):
        root_path = Path("src/ai/conformal_prediction_calibrator.py")
        ts_path = Path("trading_system/src/ai/conformal_prediction_calibrator.py")

        assert root_path.exists(), f"Missing file at {root_path}"
        assert ts_path.exists(), f"Missing file at {ts_path}"

        hash_root = hashlib.sha256(root_path.read_bytes()).hexdigest()
        hash_ts = hashlib.sha256(ts_path.read_bytes()).hexdigest()

        assert hash_root == hash_ts, (
            f"Dual-placement hash mismatch:\n  root: {hash_root}\n  ts:   {hash_ts}"
        )

    def test_dual_tree_import_equivalence(self):
        root_inst = ConformalPredictionCalibrator()
        ts_inst = ts_conformal.ConformalPredictionCalibrator()

        b_root = root_inst.predict_band(strategy_name="regression", y_hat=0.03)
        b_ts = ts_inst.predict_band(strategy_name="regression", y_hat=0.03)

        assert b_root.lower_bound == pytest.approx(b_ts.lower_bound)
        assert b_root.upper_bound == pytest.approx(b_ts.upper_bound)
        assert b_root.interval_width == pytest.approx(b_ts.interval_width)

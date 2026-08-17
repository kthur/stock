import unittest
import logging
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.analysis.macro_analyzer import calculate_cross_correlation, MACRO_SYMBOLS
from src.analysis.macro_predictor import MacroPredictor

# ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

logger = logging.getLogger(__name__)

class TestMacroStress(unittest.TestCase):
    """
    Empirical stress tests for Global Macro Correlation Engine and ML Predictor.
    """

    def setUp(self):
        self.dates = pd.date_range("2026-01-01", periods=30, freq="B")

    # ==========================================
    # 1. calculate_cross_correlation Stress Tests
    # ==========================================

    def test_completely_missing_nan_datasets(self):
        """Verify behavior with completely missing/NaN datasets."""
        # Case A: Entirely NaN dataframe
        nan_data = pd.DataFrame(np.nan, index=self.dates, columns=MACRO_SYMBOLS)
        corr_df = calculate_cross_correlation(nan_data, lags=3)

        # When all is NaN, returns are NaN, corr is NaN, which gets filled with 0.0
        self.assertFalse(corr_df.empty)
        for ticker in MACRO_SYMBOLS:
            for lag in range(4):
                self.assertEqual(corr_df.loc[ticker, (ticker, lag)], 0.0)

        # Case B: Empty dataframe
        empty_data = pd.DataFrame()
        corr_df_empty = calculate_cross_correlation(empty_data, lags=3)
        self.assertTrue(corr_df_empty.empty)

    def test_varying_lengths_non_overlapping(self):
        """Verify behavior with varying data lengths and non-overlapping timezones."""
        # Case A: Varying lengths (non-overlapping dates for different columns)
        # Ticker 1 has data only in first 15 days, Ticker 2 only in last 15 days
        data = pd.DataFrame(index=self.dates, columns=["^GSPC", "USDKRW=X"])
        data.loc[self.dates[:15], "^GSPC"] = np.random.randn(15)
        data.loc[self.dates[15:], "USDKRW=X"] = np.random.randn(15)

        # Ffill/Bfill will propagate the last/first value, making both constant on non-overlap
        # Let's see if calculate_cross_correlation runs without crashing
        corr_df = calculate_cross_correlation(data, lags=2)
        self.assertFalse(corr_df.empty)

        # Case B: Non-overlapping timezones
        # Index with timezones (US Eastern vs Korea Standard Time)
        tz_us = pd.date_range("2026-01-01", periods=10, freq="B", tz="America/New_York")
        tz_kr = pd.date_range("2026-01-01", periods=10, freq="B", tz="Asia/Seoul")

        df_us = pd.DataFrame({"^GSPC": np.random.randn(10)}, index=tz_us)
        df_kr = pd.DataFrame({"^KS11": np.random.randn(10)}, index=tz_kr)

        # Merge them: index becomes a mixture of timezones (unified to UTC by pandas or remains mixed)
        combined = pd.concat([df_us, df_kr], axis=1)

        # Test timezone alignment and normalization inside calculate_cross_correlation
        corr_df_tz = calculate_cross_correlation(combined, lags=2)
        self.assertFalse(corr_df_tz.empty)

    def test_out_of_bounds_extreme_numbers(self):
        """Verify behavior with out-of-bounds or extreme values (inf, -inf, overflow)."""
        data = pd.DataFrame(1.0, index=self.dates, columns=["^GSPC", "USDKRW=X"])
        # Inject inf and -inf
        data.iloc[5, 0] = np.inf
        data.iloc[10, 1] = -np.inf
        # Inject huge number
        data.iloc[15, 0] = 1e300
        # Inject tiny number
        data.iloc[20, 1] = 1e-300

        # Run correlation calculation
        corr_df = calculate_cross_correlation(data, lags=2)
        self.assertFalse(corr_df.empty)
        # Ensure outputs are finite (NaNs/Infs are handled or replaced with 0.0)
        self.assertTrue(np.isfinite(corr_df.values).all())

    # ==========================================
    # 2. MacroPredictor Stress Tests
    # ==========================================

    def test_predictor_all_constant_values(self):
        """Verify predictor behaves properly when training data is completely constant."""
        features = pd.DataFrame(5.0, index=self.dates, columns=["feat_1", "feat_2"])
        targets = pd.Series(10.0, index=self.dates)

        predictor = MacroPredictor(max_depth=3, n_estimators=5)
        metrics = predictor.train_model(features, targets)

        self.assertTrue(predictor.is_trained)
        self.assertIn("mse", metrics)
        self.assertIn("r2_score", metrics)

        # Predict on same constant features
        preds = predictor.predict_outperformers(features)
        self.assertEqual(len(preds), len(features))
        # R2 score of constant target might be undefined (often nan or 0.0 in sklearn)
        # Verify it doesn't crash the code

    def test_predictor_all_nans(self):
        """Verify predictor raises ValueError instead of crashing when data is all NaNs."""
        features = pd.DataFrame(np.nan, index=self.dates, columns=["feat_1", "feat_2"])
        targets = pd.Series(np.nan, index=self.dates)

        predictor = MacroPredictor(max_depth=3, n_estimators=5)
        with self.assertRaises(ValueError):
            predictor.train_model(features, targets)

    def test_predictor_very_small_datasets(self):
        """Verify training constraints based on sample sizes."""
        predictor = MacroPredictor(max_depth=3, n_estimators=5)

        # Size < 5: should raise ValueError
        small_dates = pd.date_range("2026-01-01", periods=4, freq="B")
        features_small = pd.DataFrame(np.random.randn(4, 2), index=small_dates, columns=["feat_1", "feat_2"])
        targets_small = pd.Series(np.random.randn(4), index=small_dates)
        with self.assertRaises(ValueError):
            predictor.train_model(features_small, targets_small)

        # Size = 5: should train successfully (uses same data for train/test fallback)
        ok_dates = pd.date_range("2026-01-01", periods=5, freq="B")
        features_ok = pd.DataFrame(np.random.randn(5, 2), index=ok_dates, columns=["feat_1", "feat_2"])
        targets_ok = pd.Series(np.random.randn(5), index=ok_dates)
        metrics = predictor.train_model(features_ok, targets_ok)
        self.assertTrue(predictor.is_trained)
        self.assertEqual(metrics["num_samples"], 5)

    def test_predictor_large_number_of_features(self):
        """Verify predictor can handle a large number of features (wide data)."""
        n_features = 200
        features = pd.DataFrame(
            np.random.randn(30, n_features),
            index=self.dates,
            columns=[f"feat_{i}" for i in range(n_features)]
        )
        targets = pd.Series(np.random.randn(30), index=self.dates)

        predictor = MacroPredictor(max_depth=3, n_estimators=5)
        metrics = predictor.train_model(features, targets)
        self.assertTrue(predictor.is_trained)
        self.assertEqual(len(metrics["features"]), n_features)

    def test_predict_untrained_fallback(self):
        """Verify prediction behavior before model is trained."""
        predictor = MacroPredictor(max_depth=3, n_estimators=5)
        features = pd.DataFrame(np.random.randn(10, 2), index=self.dates[:10], columns=["feat_1", "feat_2"])

        # Should return zero predictions without crashing
        preds = predictor.predict_outperformers(features)
        self.assertTrue((preds == 0.0).all())
        self.assertEqual(len(preds), 10)

    def test_predict_mismatched_features_fallback(self):
        """Verify model handles predicting on mismatched feature sets."""
        train_features = pd.DataFrame(np.random.randn(20, 2), index=self.dates[:20], columns=["feat_1", "feat_2"])
        targets = pd.Series(np.random.randn(20), index=self.dates[:20])

        predictor = MacroPredictor(max_depth=3, n_estimators=5)
        predictor.train_model(train_features, targets)

        # Test with missing feature "feat_1" and extra feature "feat_3"
        test_features = pd.DataFrame(np.random.randn(10, 2), index=self.dates[20:30], columns=["feat_2", "feat_3"])

        # It should align the features, impute missing ones to 0.0, and predict without crashing
        preds = predictor.predict_outperformers(test_features)
        self.assertEqual(len(preds), 10)

    # ==========================================
    # 3. Cache Robustness Tests
    # ==========================================

    def test_cached_metrics_write_failure(self):
        """Verify that a write error to data/macro_model_metrics.json does not disrupt training."""
        features = pd.DataFrame(np.random.randn(20, 2), index=self.dates[:20], columns=["feat_1", "feat_2"])
        targets = pd.Series(np.random.randn(20), index=self.dates[:20])

        predictor = MacroPredictor(max_depth=3, n_estimators=5)

        # Mock open to raise an OSError when opening the metrics cache path
        original_open = open
        def mock_open_fn(file, *args, **kwargs):
            if "macro_model_metrics.json" in str(file):
                raise OSError("Permission denied / Disk full simulation")
            return original_open(file, *args, **kwargs)

        with patch("builtins.open", new=mock_open_fn):
            # The code should catch the error and still complete training successfully
            metrics = predictor.train_model(features, targets)
            self.assertTrue(predictor.is_trained)
            self.assertIn("mse", metrics)

    def test_screener_predictions_not_identical(self):
        """Verify that expected excess returns for tickers are not identical due to stock-specific features."""
        from src.analysis.screener import StockScreener
        screener = StockScreener()
        results = screener.screen_global_outperformers()

        # Extract US predictions
        us_preds = [x["expected_excess_return"] for x in results["US"]]
        # Extract KR predictions
        kr_preds = [x["expected_excess_return"] for x in results["KR"]]

        # Verify that US predictions are not all identical
        self.assertGreater(len(set(us_preds)), 1, f"US predictions are all identical: {us_preds}")
        # Verify that KR predictions are not all identical
        self.assertGreater(len(set(kr_preds)), 1, f"KR predictions are all identical: {kr_preds}")

if __name__ == "__main__":
    unittest.main()

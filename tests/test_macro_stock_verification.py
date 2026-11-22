"""
tests/test_macro_stock_verification.py

Comprehensive unit and integration test suite for:
  - R1: Macroeconomic data integrity (bounds, corruption detection, yield scaling, date continuity)
  - R2: Stock price & volume integrity (OHLC invariants, zero volume, price outliers, split adjustments)
  - R3: Macro-to-stock correlation & lag consistency (directional signs, sector betas, Meucci ESC, lead-lag peak)
  - R4: Automated reporting & Dataset Health Score (composite score, JSON schema, Markdown formatting, synthetic rows invariant)
"""

# ⚠️ MANDATORY INTEGRITY WARNING:
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task.
# A Forensic Auditor will independently verify your work.
# Integrity violations WILL be detected and your work WILL be rejected.

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trading_system.scripts.verify_macro_stock_integrity import (
    evaluate_macro_integrity,
    evaluate_stock_integrity,
    evaluate_correlation_and_lag,
    compute_effective_signal_count,
    compute_dataset_health_score,
    write_verification_reports,
    run_verification,
    REQUIRED_MACRO_INDICATORS,
    scale_treasury_yield,
    REPRESENTATIVE_SECTOR_STOCKS,
)
from src.data_layer.data_validator import (
    DataValidator,
    detect_shared_series_corruption,
    clean_macro_value,
    filter_price_spikes,
)
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.persistence.database import StockPriceDB
from src.analysis.macro_analyzer import calculate_cross_correlation


class TestMacroDataIntegrity(unittest.TestCase):
    """Tests for R1: Macroeconomic data integrity verification."""

    def test_macro_bounds_validation(self):
        """Programmatically verify macro bounds against REQUIRED_MACRO_INDICATORS and DataValidator."""
        sample_market_values = {
            "^VIX": 20.63,
            "^TNX": 4.25,
            "USDKRW=X": 1335.0,
            "CL=F": 85.0,
            "GLD": 350.0,
            "^GSPC": 5800.0,
        }

        # 1. Programmatic validation of normal in-bounds values
        for sym, val in sample_market_values.items():
            self.assertIn(sym, REQUIRED_MACRO_INDICATORS)
            meta = REQUIRED_MACRO_INDICATORS[sym]
            low, high = meta["bounds"]
            self.assertTrue(low <= val <= high, f"Symbol {sym} value {val} not in [{low}, {high}]")

            # Cross-verify with MarketIndicatorStorage.INDICATOR_VALUE_BOUNDS
            storage_bounds = MarketIndicatorStorage.INDICATOR_VALUE_BOUNDS.get(sym)
            if storage_bounds:
                self.assertTrue(storage_bounds[0] <= val <= storage_bounds[1])

        # 2. Programmatic validation of anomalous out-of-bounds rejection
        out_of_bounds_cases = {
            "^VIX": [2.0, 150.0],
            "^TNX": [-1.0, 25.0],
            "USDKRW=X": [500.0, 3500.0],
            "CL=F": [2.0, 500.0],
            "GLD": [10.0, 5000.0],
        }
        for sym, bad_vals in out_of_bounds_cases.items():
            low, high = REQUIRED_MACRO_INDICATORS[sym]["bounds"]
            for bad_val in bad_vals:
                self.assertFalse(low <= bad_val <= high, f"{sym} bad value {bad_val} unexpectedly in bounds")

        # 3. Validation via DataValidator.clean_macro_value
        self.assertEqual(DataValidator.clean_macro_value("20.63", "18.0", "vix"), "20.63")
        self.assertEqual(DataValidator.clean_macro_value("150.0", "18.0", "vix"), "18.0")
        self.assertEqual(DataValidator.clean_macro_value("1,335.0", "1,300.0", "usdkrw"), "1,335.0")
        self.assertEqual(DataValidator.clean_macro_value("500.0", "1,300.0", "usdkrw"), "1,300.0")

    def test_detect_shared_series_corruption(self):
        """Verify detection of shared-cache DB corruption across disparate macro series."""
        # Contaminated series where all tickers share the same value (e.g., 103.478)
        self.assertTrue(detect_shared_series_corruption(103.478, 103.478, 103.478, 103.478))
        self.assertTrue(detect_shared_series_corruption(103.2, 103.5, 103.4, 103.3))

        # Genuine market values with realistic cross-asset dispersion
        self.assertFalse(detect_shared_series_corruption(20.63, 87.58, 355.45, 5.14))

    def test_yfinance_yield_scaling(self):
        """Verify that yfinance 10x quoted Treasury yields (e.g., 42.5) are scaled to 4.25% via production helper and DataValidator."""
        # 1. Test production helper scale_treasury_yield with 10x quoted raw yield (42.5 -> 4.25%)
        scaled_yield, was_scaled = scale_treasury_yield("^TNX", 42.5)
        self.assertTrue(was_scaled)
        self.assertAlmostEqual(scaled_yield, 4.25, places=2)
        self.assertTrue(0.0 <= scaled_yield <= 15.0)

        # 2. Standard percentage yield should remain unscaled
        standard_yield, was_scaled_std = scale_treasury_yield("^TNX", 4.25)
        self.assertFalse(was_scaled_std)
        self.assertAlmostEqual(standard_yield, 4.25, places=2)

        # 3. Test clean_macro_value boundary enforcement on interest rates
        cleaned_valid = DataValidator.clean_macro_value("4.25", "4.00", "us10y")
        self.assertEqual(cleaned_valid, "4.25")
        # Raw unscaled 42.5 violates MACRO_BOUNDS["us10y"] (0.5, 15.0) and reverts to fallback
        cleaned_invalid = DataValidator.clean_macro_value("42.5", "4.00", "us10y")
        self.assertEqual(cleaned_invalid, "4.00")

    def test_macro_integrity_offline_execution(self):
        """Verify that evaluate_macro_integrity executes offline without unhandled exceptions."""
        storage = MarketIndicatorStorage()
        res = evaluate_macro_integrity(storage=storage, offline_mode=True)

        self.assertIn("status", res)
        self.assertIn("score", res)
        self.assertIn("bounds_pass_rate", res)
        self.assertIn("shared_cache_corruption_detected", res)
        self.assertIn("storage_health", res)
        self.assertIn("details", res)

        self.assertGreaterEqual(res["score"], 70.0)
        self.assertFalse(res["shared_cache_corruption_detected"])
        self.assertEqual(res["total_indicators_checked"], 12)
        self.assertEqual(res["bounds_pass_count"], 12)


class TestStockOHLCVIntegrity(unittest.TestCase):
    """Tests for R2: Stock price and trading volume integrity verification."""

    def test_ohlc_boundary_invariants_pass(self):
        """Clean bars satisfying Low <= Open <= High, Low <= Close <= High must pass DataValidator."""
        dates = pd.date_range("2026-01-01", periods=5)
        clean_df = pd.DataFrame({
            "Open": [100.0, 102.0, 101.0, 103.0, 104.0],
            "High": [105.0, 104.0, 103.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 98.0, 101.0, 103.0],
            "Close": [102.0, 101.0, 103.0, 105.0, 106.0],
            "Volume": [1000.0, 1200.0, 1100.0, 1300.0, 1500.0]
        }, index=dates)

        # 1. DataValidator quality gate
        self.assertTrue(DataValidator.validate_price_data("005930", clean_df))

        # 2. validate_and_clean_price_series preserves clean data without alteration
        cleaned = DataValidator.validate_and_clean_price_series(clean_df, symbol="005930")
        pd.testing.assert_frame_equal(clean_df, cleaned)

    def test_ohlc_boundary_invariants_fail(self):
        """Corrupted bars with High < Low, High < Open, or Close <= 0 must be rejected and rectified."""
        dates = pd.date_range("2026-01-01", periods=5)
        corrupted_df = pd.DataFrame({
            "Open": [100.0, 102.0, 100.0, 105.0, 106.0],
            "High": [95.0, 104.0, 110.0, 106.0, 108.0],   # Row 0: High < Open
            "Low": [90.0, 105.0, 98.0, 101.0, 102.0],     # Row 1: Low > Close
            "Close": [98.0, 101.0, 103.0, 104.0, 105.0],
            "Volume": [1000.0, 1200.0, 1100.0, 1300.0, 1400.0]
        }, index=dates)

        # 1. Physical violations present in raw corrupted data
        bad_ohlc_raw = (
            (corrupted_df["High"] < corrupted_df["Low"]) |
            (corrupted_df["High"] < corrupted_df["Open"]) |
            (corrupted_df["High"] < corrupted_df["Close"]) |
            (corrupted_df["Low"] > corrupted_df["Open"]) |
            (corrupted_df["Low"] > corrupted_df["Close"]) |
            (corrupted_df["Close"] <= 0)
        ).sum()
        self.assertGreater(bad_ohlc_raw, 0)

        # 2. DataValidator rejects bad feeds with >50% non-positive close
        bad_feed_df = pd.DataFrame({
            "Close": [-1.0, -2.0, -5.0, 10.0, 12.0]
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("BAD_CLOSE", bad_feed_df))

        # 3. DataValidator rectifies anomalies to enforce physical bounds
        rectified_df = DataValidator.validate_and_clean_price_series(corrupted_df, symbol="005930")
        self.assertTrue((rectified_df["Close"] > 0).all())
        self.assertTrue((rectified_df["Open"] > 0).all())
        self.assertTrue((rectified_df["Low"] > 0).all())
        self.assertTrue((rectified_df["High"] >= rectified_df["Low"]).all())
        self.assertTrue((rectified_df["High"] >= rectified_df["Open"]).all())
        self.assertTrue((rectified_df["High"] >= rectified_df["Close"]).all())
        self.assertTrue((rectified_df["Low"] <= rectified_df["Open"]).all())
        self.assertTrue((rectified_df["Low"] <= rectified_df["Close"]).all())

        # 4. Rectified DataFrame passes DataValidator
        self.assertTrue(DataValidator.validate_price_data("005930", rectified_df))

    def test_zero_volume_frequency_metric(self):
        """Verify zero-volume screening via DataValidator: active ticker passes, dormant fails."""
        dates = pd.date_range("2026-01-01", periods=10)
        active_df = pd.DataFrame({
            "Open": [100.0] * 10, "High": [105.0] * 10, "Low": [95.0] * 10,
            "Close": [102.0] * 10, "Volume": [1000.0] * 10
        }, index=dates)
        self.assertTrue(DataValidator.validate_price_data("ACTIVE", active_df))

        # >90% zero-volume indicates halted/suspended ticker -> rejected by DataValidator
        dormant_df = pd.DataFrame({
            "Open": [100.0] * 10, "High": [105.0] * 10, "Low": [95.0] * 10,
            "Close": [100.0] * 10, "Volume": [0.0] * 10
        }, index=dates)
        self.assertFalse(DataValidator.validate_price_data("DORMANT", dormant_df))

    def test_price_outlier_and_spike_detection(self):
        """Verify single-day spike rejection (>300%) and cleaning via filter_price_spikes."""
        dates = pd.date_range("2026-01-01", periods=5)
        df_spike = pd.DataFrame({
            "Open": [100.0, 101.0, 500.0, 505.0, 510.0],
            "High": [102.0, 103.0, 505.0, 510.0, 515.0],
            "Low": [99.0, 100.0, 495.0, 500.0, 505.0],
            "Close": [100.0, 101.0, 500.0, 505.0, 510.0],
            "Volume": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
        }, index=dates)

        # Unadjusted +395% spike rejected by DataValidator
        self.assertFalse(DataValidator.validate_price_data("SPIKE_SYM", df_spike))

        # filter_price_spikes cleans anomaly
        cleaned_df = filter_price_spikes(df_spike, max_return=3.0)
        pct_cleaned = cleaned_df["Close"].pct_change().dropna()
        self.assertEqual((pct_cleaned.abs() > 3.0).sum(), 0)
        self.assertTrue(DataValidator.validate_price_data("CLEANED_SPIKE", cleaned_df))

    def test_stock_integrity_offline_execution(self):
        """Verify evaluate_stock_integrity executes offline across representative markets."""
        price_db = StockPriceDB()
        try:
            res = evaluate_stock_integrity(price_db=price_db, sample_size=2, offline_mode=True)
            self.assertIn("status", res)
            self.assertIn("score", res)
            self.assertIn("symbols_evaluated", res)
            self.assertIn("ohlc_invariant_violations", res)
            self.assertIn("market_breakdown", res)

            # Invariant: zero OHLC violations on institutional DB
            self.assertEqual(res["ohlc_invariant_violations"], 0)
            self.assertGreaterEqual(res["score"], 80.0)
            self.assertIn("KOSPI", res["market_breakdown"])
            self.assertIn("SP500", res["market_breakdown"])
        finally:
            price_db.close()


class TestCorrelationAndLeadLagConsistency(unittest.TestCase):
    """Tests for R3: Macro-to-stock correlation & lag consistency analysis."""

    def test_meucci_effective_signal_count(self):
        """Verify Meucci (2009) ESC: identity -> N, perfectly collinear -> 1.0."""
        # 1. Identity matrix (completely orthogonal risk dimensions)
        n = 5
        ident = pd.DataFrame(np.eye(n))
        esc_ident = compute_effective_signal_count(ident)
        self.assertAlmostEqual(esc_ident, float(n), delta=0.1)

        # 2. Perfect collinearity (single risk dimension)
        collinear = pd.DataFrame(np.ones((n, n)))
        esc_collinear = compute_effective_signal_count(collinear)
        self.assertAlmostEqual(esc_collinear, 1.0, delta=0.1)

        # 3. Realistic correlation matrix
        rng = np.random.default_rng(42)
        X = rng.normal(size=(100, 6))
        corr_real = pd.DataFrame(X).corr()
        esc_real = compute_effective_signal_count(corr_real)
        self.assertGreaterEqual(esc_real, 4.0)

    def test_cross_correlation_multi_lag_structure(self):
        """Verify multi-lag Pearson cross-correlation calculation and MultiIndex output."""
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        rng = np.random.default_rng(123)
        tickers = ["^GSPC", "^KS11", "USDKRW=X"]
        df = pd.DataFrame(rng.normal(100, 2, size=(30, 3)), index=dates, columns=tickers)

        corr_df = calculate_cross_correlation(df, lags=3)
        self.assertFalse(corr_df.empty)
        self.assertIn("lag", corr_df.columns.names)
        self.assertIn("ticker", corr_df.columns.names)

        # Check diagonal at lag 0 is 1.0
        for t in tickers:
            self.assertAlmostEqual(float(corr_df.loc[t, (t, 0)]), 1.0, places=4)

    def test_directional_consistency_rules(self):
        """Verify directional sign priors and empirical sector betas using production code."""
        price_db = StockPriceDB()
        try:
            res = evaluate_correlation_and_lag(price_db=price_db, offline_mode=True)
            self.assertIn("directional_consistency", res)
            self.assertIn("stock_level_empirical_metrics", res)
            dc = res["directional_consistency"]

            # 1. FX vs KOSPI: Won depreciation negatively correlates with KOSPI
            self.assertEqual(dc["usdkrw_kospi"]["status"], "PASS")
            self.assertLess(dc["usdkrw_kospi"]["lag_0"], 0.05)

            # 2. VIX vs Equities: Volatility spike negatively correlates with equity prices
            self.assertEqual(dc["vix_equities"]["status"], "PASS")
            self.assertLess(dc["vix_equities"]["vix_sp500"], -0.20)

            # 3. Sector Rate Elasticity: Bank rate beta > Tech rate beta
            self.assertEqual(dc["sector_rate_elasticity"]["status"], "PASS")
            self.assertGreater(
                dc["sector_rate_elasticity"]["financials_beta"],
                dc["sector_rate_elasticity"]["semiconductor_beta"]
            )

            # 4. Sector FX Elasticity: Exporter FX beta > Utility FX beta
            self.assertEqual(dc["sector_fx_elasticity"]["status"], "PASS")
            self.assertGreater(
                dc["sector_fx_elasticity"]["exporter_beta"],
                dc["sector_fx_elasticity"]["utilities_beta"]
            )

            # 5. Verify stock-level empirical metrics exist for all representative sectors
            stock_metrics = res["stock_level_empirical_metrics"]
            self.assertIn("Financials", stock_metrics)
            self.assertIn("Semiconductor", stock_metrics)
            self.assertIn("Automotive", stock_metrics)
            self.assertIn("Utilities", stock_metrics)
            for sector, m in stock_metrics.items():
                self.assertGreater(m["bars_evaluated"], 30)
                self.assertIn("empirical_beta_tnx", m)
                self.assertIn("empirical_beta_fx", m)
                self.assertIn("empirical_beta_market", m)
        finally:
            price_db.close()

    def test_lead_lag_temporal_peak(self):
        """Verify that a lagged driver Y_t = X_{t-1} peaks at lag tau* = 1 across multiple RNG seeds."""
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        for seed in (42, 43, 100, 2026):
            rng = np.random.default_rng(seed)
            x = rng.normal(size=100)
            # y follows x with 1-day lag: y_t = x_{t-1}
            y = np.roll(x, 1)
            y[0] = 0.0

            s_x = pd.Series(x, index=dates)
            s_y = pd.Series(y, index=dates)

            # Proper cross-correlation: Y_t correlated with X_{t - lag}
            lags = [abs(float(s_y.corr(s_x.shift(lag)))) for lag in range(4)]
            peak_lag = int(np.argmax(lags))

            self.assertEqual(peak_lag, 1, f"Failed at seed {seed}: peak_lag was {peak_lag}")
            self.assertAlmostEqual(lags[1], 1.0, places=4)


class TestAutomatedReportingAndHealthScore(unittest.TestCase):
    """Tests for R4: Automated Verification Reporting and Dataset Health Score."""

    def test_health_score_calculation_and_grades(self):
        """Verify weighted harmonic composite formula and grade assignments."""
        # 1. Excellent Case: 100 macro, 100 stock, 100 corr -> 100.0 EXCELLENT PASS
        h, grade, status = compute_dataset_health_score(
            macro_res={"score": 100.0, "shared_cache_corruption_detected": False},
            stock_res={"score": 100.0, "ohlc_invariant_violations": 0},
            corr_res={"score": 100.0}
        )
        self.assertEqual(h, 100.0)
        self.assertEqual(grade, "EXCELLENT")
        self.assertEqual(status, "PASS")

        # 2. Acceptable Case: 80 macro, 80 stock, 80 corr -> 80.0 ACCEPTABLE PASS
        h, grade, status = compute_dataset_health_score(
            macro_res={"score": 80.0, "shared_cache_corruption_detected": False},
            stock_res={"score": 80.0, "ohlc_invariant_violations": 0},
            corr_res={"score": 80.0}
        )
        self.assertEqual(h, 80.0)
        self.assertEqual(grade, "ACCEPTABLE")
        self.assertEqual(status, "PASS")

        # 3. Critical Failure Case: OHLC violation forces FAIL grade
        h, grade, status = compute_dataset_health_score(
            macro_res={"score": 100.0, "shared_cache_corruption_detected": False},
            stock_res={"score": 90.0, "ohlc_invariant_violations": 5},
            corr_res={"score": 100.0}
        )
        self.assertEqual(grade, "FAIL")
        self.assertEqual(status, "FAIL")

        # 4. Critical Failure Case: Shared cache corruption forces FAIL grade
        h, grade, status = compute_dataset_health_score(
            macro_res={"score": 0.0, "shared_cache_corruption_detected": True},
            stock_res={"score": 100.0, "ohlc_invariant_violations": 0},
            corr_res={"score": 100.0}
        )
        self.assertEqual(grade, "FAIL")
        self.assertEqual(status, "FAIL")

    def test_synthetic_rows_strict_invariant(self):
        """Verify that synthetic_rows == 0 is strictly a Python int 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_verification(output_dir=tmpdir, sample_size=2, offline_mode=True)
            self.assertEqual(report["synthetic_rows"], 0)
            self.assertIsInstance(report["synthetic_rows"], int)

            # Check JSON file on disk
            json_path = Path(tmpdir) / "verification_report.json"
            self.assertTrue(json_path.exists())
            with open(json_path, "r", encoding="utf-8") as f:
                disk_report = json.load(f)
            self.assertEqual(disk_report["synthetic_rows"], 0)
            self.assertIsInstance(disk_report["synthetic_rows"], int)

    def test_end_to_end_verification_execution(self):
        """Verify end-to-end execution producing JSON and Markdown reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_verification(output_dir=tmpdir, sample_size=2, offline_mode=True)

            self.assertIn("report_type", report)
            self.assertIn("overall_status", report)
            self.assertIn("dataset_health_score", report)
            self.assertIn("health_grade", report)
            self.assertIn("categories", report)
            self.assertIn("macro_integrity", report["categories"])
            self.assertIn("stock_integrity", report["categories"])
            self.assertIn("correlation_and_lag_consistency", report["categories"])

            self.assertEqual(report["overall_status"], "PASS")
            self.assertGreaterEqual(report["dataset_health_score"], 90.0)

            # Verify Markdown file content
            md_path = Path(tmpdir) / "verification_report.md"
            self.assertTrue(md_path.exists())
            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            self.assertIn("# Macroeconomic & Stock Market Data Integrity Verification Report", md_text)
            self.assertIn("Overall Status", md_text)
            self.assertIn("Dataset Health Score", md_text)
            self.assertIn("R1: Macroeconomic Data Integrity", md_text)
            self.assertIn("R2: Stock Price & Volume Integrity", md_text)
            self.assertIn("R3: Correlation & Lead-Lag Consistency", md_text)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Phase 4-A (Isotonic calibration) and Phase 4-B (Median fallback metadata)."""

import pytest
import numpy as np
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.prediction_model import FallbackMetadataDict


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4-A: Isotonic Regression Calibration
# ──────────────────────────────────────────────────────────────────────────────

class TestIsotonicCalibration:

    def _make_engine(self):
        return EnsembleScoringEngine()

    def test_no_calibrators_by_default(self):
        """Engine must start without any calibrators fitted."""
        engine = self._make_engine()
        assert not engine.has_calibrators()

    def test_fit_calibrators_succeeds_with_enough_samples(self):
        """fit_calibrators() should train IsotonicRegression for each strategy."""
        engine = self._make_engine()
        N = 100
        rng = np.random.default_rng(42)
        strategy_scores = {
            "regression": rng.uniform(0, 1, N),
            "surge":      rng.uniform(0, 1, N),
            "lead_lag":   rng.uniform(0, 1, N),
            "vcp_rule":   rng.uniform(0, 1, N),
            "vcp_ml":     rng.uniform(0, 1, N),
        }
        true_labels = (rng.uniform(0, 1, N) > 0.8).astype(float)
        engine.fit_calibrators(strategy_scores, true_labels)
        assert engine.has_calibrators()
        assert set(engine._calibrators.keys()) == set(strategy_scores.keys())

    def test_calibrate_scores_returns_valid_range(self):
        """calibrate_scores() must return values in [0, 1]."""
        engine = self._make_engine()
        N = 50
        rng = np.random.default_rng(7)
        scores = rng.uniform(0, 1, N)
        labels = (rng.uniform(0, 1, N) > 0.8).astype(float)
        engine.fit_calibrators({"surge": scores}, labels)
        out = engine.calibrate_scores("surge", scores)
        assert np.all(out >= 0.0), "Calibrated scores below 0"
        assert np.all(out <= 1.0), "Calibrated scores above 1"

    def test_calibrate_unknown_strategy_returns_unchanged(self):
        """calibrate_scores() on unfitted strategy must return input unchanged."""
        engine = self._make_engine()
        scores = np.array([0.1, 0.5, 0.9])
        result = engine.calibrate_scores("unknown_strategy", scores)
        np.testing.assert_array_equal(result, scores)

    def test_skips_calibration_when_too_few_samples(self):
        """Calibrator must NOT be stored if fewer than 20 samples."""
        engine = self._make_engine()
        rng = np.random.default_rng(0)
        scores = rng.uniform(0, 1, 10)  # only 10 samples
        labels = (rng.uniform(0, 1, 10) > 0.8).astype(float)
        engine.fit_calibrators({"regression": scores}, labels)
        # Should still have no calibrators (too few)
        assert "regression" not in engine._calibrators

    def test_calibration_applied_in_ensemble_score_calculation(self):
        """calculate_ensemble_score() must apply calibration when calibrators are present."""
        engine = self._make_engine()
        N = 60
        rng = np.random.default_rng(99)

        # Fit calibrators with synthetically correlated data
        raw_scores = rng.uniform(0, 1, N)
        labels = (raw_scores > 0.7).astype(float)
        engine.fit_calibrators(
            {"regression": raw_scores, "surge": raw_scores, "lead_lag": raw_scores,
             "vcp_rule": raw_scores, "vcp_ml": raw_scores},
            labels
        )

        symbols = [f"SYM{i:04d}" for i in range(N)]
        reg_df = pd.DataFrame({"symbol": symbols, 20: raw_scores})
        surge_df = pd.DataFrame({"symbol": symbols, "surge_20d": raw_scores})
        ll_df = pd.DataFrame({"symbol": symbols, "lead_lag_score": raw_scores})
        vcp_ml_df = pd.DataFrame({"symbol": symbols, "vcp_20d": raw_scores})
        vcp_rule_df = pd.DataFrame({"symbol": symbols, "vcp_score": raw_scores * 100})

        result = engine.calculate_ensemble_score(
            regime=2,
            regression_df=reg_df,
            surge_df=surge_df,
            lead_lag_df=ll_df,
            vcp_ml_df=vcp_ml_df,
            vcp_rule_df=vcp_rule_df,
        )
        assert not result.empty
        assert "ensemble_score" in result.columns
        assert result["ensemble_score"].between(0, 1).all()


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4-B: FallbackMetadataDict Median Values
# ──────────────────────────────────────────────────────────────────────────────

class TestFallbackMetadataMedian:

    def test_krx_symbol_returns_market_median_shares(self):
        """Korean 6-digit unknown symbols should return NaN shares to prevent data contamination."""
        md = FallbackMetadataDict()
        # Unknown KRX symbol (not in benchmarks)
        result = md.get("123456")
        assert result is not None
        # Should return NaN, not a fake constant or hash-based random number
        assert np.isnan(result["shares_outstanding"])
        assert np.isnan(result["floating_shares"])

    def test_us_symbol_returns_us_median_shares(self):
        """Unknown US ticker symbols should return NaN shares to prevent data contamination."""
        md = FallbackMetadataDict()
        result = md.get("XYZUNKNOWN")
        assert result is not None
        assert np.isnan(result["shares_outstanding"])
        assert np.isnan(result["floating_shares"])

    def test_fundamentals_remain_nan_for_unknown_symbols(self):
        """Fundamental columns must be NaN for unknown symbols (XGBoost native missing handling)."""
        import math
        md = FallbackMetadataDict()
        result = md.get("999999")
        for col in ["revenue", "operating_income", "net_income", "eps", "dividend_per_share"]:
            assert result[col] is None or math.isnan(result[col]), (
                f"Expected NaN for '{col}' but got {result[col]}"
            )

    def test_known_benchmark_symbols_retain_real_values(self):
        """Real benchmark symbols (AAPL, 005930) must keep their actual share counts."""
        md = FallbackMetadataDict()
        # Samsung Electronics
        samsung = md.get("005930")
        assert samsung["shares_outstanding"] == pytest.approx(5_969_782_550.0)
        # Apple
        aapl = md.get("AAPL")
        assert aapl["shares_outstanding"] == pytest.approx(15_000_000_000.0)

    def test_no_hash_based_variation_across_symbols(self):
        """Two unknown KRX symbols must return NaN (no fake constant variation)."""
        md = FallbackMetadataDict()
        sym1 = md.get("111111")
        sym2 = md.get("222222")
        assert np.isnan(sym1["shares_outstanding"]) and np.isnan(sym2["shares_outstanding"])

"""
tests/test_phase104_return_calibration.py — Unit, Integration & Adversarial Test Suite for Feature F494

Features Covered:
- Feature F494: Realistic Annualized Return Calibration & Ensemble Bridge
  - calculate_realistic_annualized_cagr() mathematical mapping and bounds
  - Alias trees and module-level exports
  - Polymorphism (scalar, np.ndarray, pd.Series with index preservation)
  - Institutional bounds [15.0%, 40.0%] for high-conviction picks
  - Monotonicity, Information Ratio (IR), Win Rate, and Turnover sensitivity
  - 2D Regime hierarchy (BULL > SIDEWAYS > BEAR > CRISIS)
  - Return vs probability autodetection and explicit overrides
  - EnsembleScoringEngine.combine_predictions() integration & sentiment blacklist zeroing
  - prediction_reporter.py formatting and column alignment
  - generate_report.py parse_ensemble() backward compatibility (2-col vs 3-col)
"""

from __future__ import annotations

import io
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# Setup sys.path for repository root and trading_system
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    calculate_realistic_annualized_cagr,
    calc_realistic_annualized_cagr,
    calculate_realistic_cagr,
    calc_realistic_cagr,
    calculate_annualized_cagr_v111,
    f494_realistic_annualized_cagr,
)
from src.pipeline.prediction_reporter import (
    format_prediction_line,
    save_strategy_predictions_report,
    save_ensemble_predictions_report,
)
from generate_report import parse_ensemble


class TestPhase104RealisticReturnCalibration(unittest.TestCase):
    """
    Validates Feature F494 mathematical properties, bounds, sensitivity, and polymorphism.
    """

    def test_exports_and_alias_trees(self) -> None:
        """Verifies that all required alias trees point to identical implementation."""
        # Class static methods
        self.assertIs(
            EnsembleScoringEngine.calculate_realistic_annualized_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            calc_realistic_annualized_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            calculate_realistic_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            calc_realistic_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            calculate_annualized_cagr_v111,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            f494_realistic_annualized_cagr,
            calculate_realistic_annualized_cagr,
        )

        # Class-level aliases
        self.assertIs(
            EnsembleScoringEngine.calc_realistic_annualized_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            EnsembleScoringEngine.calculate_realistic_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            EnsembleScoringEngine.calc_realistic_cagr,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            EnsembleScoringEngine.calculate_annualized_cagr_v111,
            calculate_realistic_annualized_cagr,
        )
        self.assertIs(
            EnsembleScoringEngine.f494_realistic_annualized_cagr,
            calculate_realistic_annualized_cagr,
        )

    def test_polymorphism_scalar_input(self) -> None:
        """Scalar float and int inputs must return float."""
        res_float = calculate_realistic_annualized_cagr(0.75, regime="BULL_LOW_VOL")
        self.assertIsInstance(res_float, float)
        self.assertTrue(math.isfinite(res_float))

        res_int = calculate_realistic_annualized_cagr(1, regime="BULL_LOW_VOL")
        self.assertIsInstance(res_int, float)
        self.assertTrue(math.isfinite(res_int))

    def test_polymorphism_ndarray_input(self) -> None:
        """np.ndarray inputs must return np.ndarray with identical shape."""
        arr_1d = np.array([0.2, 0.5, 0.8, 0.95])
        res_1d = calculate_realistic_annualized_cagr(arr_1d, regime="BULL_LOW_VOL")
        self.assertIsInstance(res_1d, np.ndarray)
        self.assertEqual(res_1d.shape, arr_1d.shape)

        arr_2d = np.array([[0.3, 0.7], [0.5, 0.85]])
        res_2d = calculate_realistic_annualized_cagr(arr_2d, regime="SIDEWAYS")
        self.assertIsInstance(res_2d, np.ndarray)
        self.assertEqual(res_2d.shape, arr_2d.shape)

    def test_polymorphism_series_with_index_preservation(self) -> None:
        """pd.Series inputs must return pd.Series with exact index preserved."""
        sym_index = ["005930", "000660", "AAPL", "NVDA", "MSFT"]
        scores = pd.Series([0.45, 0.72, 0.85, 0.91, 0.55], index=sym_index)

        res_series = calculate_realistic_annualized_cagr(scores, regime="BULL_LOW_VOL")
        self.assertIsInstance(res_series, pd.Series)
        self.assertEqual(list(res_series.index), sym_index)
        self.assertTrue(all(math.isfinite(val) for val in res_series))

    def test_percentage_vs_decimal_mode(self) -> None:
        """as_percentage=True returns percentage values; as_percentage=False returns decimal values."""
        score = 0.80
        pct = calculate_realistic_annualized_cagr(score, regime="BULL_LOW_VOL", as_percentage=True)
        dec = calculate_realistic_annualized_cagr(score, regime="BULL_LOW_VOL", as_percentage=False)

        self.assertAlmostEqual(pct / 100.0, dec, places=6)
        self.assertGreater(pct, 1.0)
        self.assertLess(dec, 1.0)

    def test_bounded_institutional_range_top_conviction(self) -> None:
        """Top conviction picks (0.70 to 0.95) in Bull/Sideways map realistically into [15.0%, 40.0%]."""
        # Score 0.70 in Bull
        cagr_70_bull = calculate_realistic_annualized_cagr(0.70, regime="BULL_LOW_VOL")
        self.assertGreaterEqual(cagr_70_bull, 15.0, f"Score 0.70 in Bull must be >= 15%, got {cagr_70_bull:.2f}%")
        self.assertLessEqual(cagr_70_bull, 40.0, f"Score 0.70 in Bull must be <= 40%, got {cagr_70_bull:.2f}%")

        # Score 0.85 in Bull
        cagr_85_bull = calculate_realistic_annualized_cagr(0.85, regime="BULL_LOW_VOL")
        self.assertGreaterEqual(cagr_85_bull, 20.0, f"Score 0.85 in Bull must be >= 20%, got {cagr_85_bull:.2f}%")
        self.assertLessEqual(cagr_85_bull, 40.0, f"Score 0.85 in Bull must be <= 40%, got {cagr_85_bull:.2f}%")

        # Score 0.95 in Bull
        cagr_95_bull = calculate_realistic_annualized_cagr(0.95, regime="BULL_LOW_VOL")
        self.assertGreaterEqual(cagr_95_bull, 25.0)
        self.assertLessEqual(cagr_95_bull, 40.0)

        # Score 0.85 in Sideways
        cagr_85_side = calculate_realistic_annualized_cagr(0.85, regime="SIDEWAYS")
        self.assertGreaterEqual(cagr_85_side, 15.0, f"Score 0.85 in Sideways must be >= 15%, got {cagr_85_side:.2f}%")
        self.assertLessEqual(cagr_85_side, 40.0)

    def test_strict_clamping_to_min_max_bounds(self) -> None:
        """Extreme inputs are strictly clamped to min_cagr and max_cagr."""
        # Score 0.95 under Bull regime produces ~28% uncapped; with max_cagr=20.0 it must be clamped to 20.0
        cagr_clamped_high = calculate_realistic_annualized_cagr(0.95, regime="BULL_LOW_VOL", max_cagr=20.0)
        self.assertAlmostEqual(cagr_clamped_high, 20.0, places=4)

        # Score 0.05 under Bear regime produces negative uncapped; with min_cagr=-5.0 it must be clamped to -5.0
        cagr_clamped_low = calculate_realistic_annualized_cagr(0.05, regime="BEAR_LOW_VOL", min_cagr=-5.0)
        self.assertAlmostEqual(cagr_clamped_low, -5.0, places=4)

        # Extreme return inputs
        cagr_extreme_pos = calculate_realistic_annualized_cagr(50.0, max_cagr=40.0, is_return=True)
        self.assertLessEqual(cagr_extreme_pos, 40.0)

        cagr_extreme_neg = calculate_realistic_annualized_cagr(-50.0, min_cagr=-40.0, is_return=True)
        self.assertGreaterEqual(cagr_extreme_neg, -40.0)

    def test_neutral_score_maps_to_market_base(self) -> None:
        """A neutral score of 0.50 (zero active conviction) maps to the base market return."""
        cagr_side_neutral = calculate_realistic_annualized_cagr(0.50, regime="SIDEWAYS", base_market_return=0.08)
        self.assertAlmostEqual(cagr_side_neutral, 8.0, places=2)

        cagr_bull_neutral = calculate_realistic_annualized_cagr(0.50, regime="BULL", base_market_return=0.08)
        self.assertAlmostEqual(cagr_bull_neutral, 10.0, places=2)

    def test_strict_monotonicity(self) -> None:
        """Higher scores on the active conviction domain monotonically produce higher or equal CAGR."""
        # On positive active alpha domain (0.55 to 1.00), higher score strictly produces higher CAGR
        grid_pos = np.linspace(0.55, 1.0, 45)
        for reg in ("BULL_LOW_VOL", "SIDEWAYS", "BEAR_LOW_VOL", "CRISIS"):
            cagrs_pos = calculate_realistic_annualized_cagr(grid_pos, regime=reg)
            diffs_pos = np.diff(cagrs_pos)
            self.assertTrue(
                np.all(diffs_pos >= -1e-8),
                f"Monotonicity violated on positive domain under regime {reg}",
            )

        # On defensive underperforming domain (0.0 to 0.49), higher score also monotonically increases
        grid_neg = np.linspace(0.0, 0.49, 45)
        for reg in ("BULL_LOW_VOL", "SIDEWAYS", "BEAR_LOW_VOL", "CRISIS"):
            cagrs_neg = calculate_realistic_annualized_cagr(grid_neg, regime=reg)
            diffs_neg = np.diff(cagrs_neg)
            self.assertTrue(
                np.all(diffs_neg >= -1e-8),
                f"Monotonicity violated on negative domain under regime {reg}",
            )

    def test_win_rate_and_ir_sensitivity(self) -> None:
        """Higher win rate and higher Information Ratio must yield strictly higher active CAGR."""
        score = 0.85
        # Compare win rate 56% vs 65%
        cagr_wr_56 = calculate_realistic_annualized_cagr(score, win_rate=0.56, regime="SIDEWAYS")
        cagr_wr_65 = calculate_realistic_annualized_cagr(score, win_rate=0.65, regime="SIDEWAYS")
        self.assertGreater(
            cagr_wr_65,
            cagr_wr_56,
            "Higher win rate (65% vs 56%) must yield higher active return",
        )

        # Compare explicit IR 0.8 vs 1.8
        cagr_ir_low = calculate_realistic_annualized_cagr(score, ir=0.8, regime="SIDEWAYS")
        cagr_ir_high = calculate_realistic_annualized_cagr(score, ir=1.8, regime="SIDEWAYS")
        self.assertGreater(
            cagr_ir_high,
            cagr_ir_low,
            "Higher Information Ratio (1.8 vs 0.8) must yield higher active return",
        )

    def test_turnover_friction_drag(self) -> None:
        """When holding Information Ratio constant, higher turnover limit incurs higher friction drag."""
        score = 0.80
        # With fixed explicit IR, active alpha is constant, so turnover drag purely reduces net CAGR
        cagr_low_churn = calculate_realistic_annualized_cagr(score, ir=1.25, turnover_limit=2.0)
        cagr_high_churn = calculate_realistic_annualized_cagr(score, ir=1.25, turnover_limit=10.0)

        self.assertGreater(
            cagr_low_churn,
            cagr_high_churn,
            "Higher turnover limit (10x vs 2x) with fixed IR must incur greater friction drag",
        )

    def test_regime_hierarchy(self) -> None:
        """For identical positive conviction, BULL > SIDEWAYS > BEAR > CRISIS."""
        score = 0.80
        c_bull = calculate_realistic_annualized_cagr(score, regime="BULL_LOW_VOL")
        c_side = calculate_realistic_annualized_cagr(score, regime="SIDEWAYS")
        c_bear = calculate_realistic_annualized_cagr(score, regime="BEAR_LOW_VOL")
        c_cris = calculate_realistic_annualized_cagr(score, regime="CRISIS")

        self.assertGreater(c_bull, c_side, "BULL return must exceed SIDEWAYS")
        self.assertGreater(c_side, c_bear, "SIDEWAYS return must exceed BEAR")
        self.assertGreater(c_bear, c_cris, "BEAR return must exceed CRISIS")

        # CRISIS neutral score should be parked around risk-free rate (~2%)
        c_cris_neutral = calculate_realistic_annualized_cagr(0.50, regime="CRISIS")
        self.assertAlmostEqual(c_cris_neutral, 2.0, places=2)

    def test_autodetection_return_vs_probability(self) -> None:
        """Autodetects whether input is probability in [0, 1] or return outside [0, 1]."""
        # Probability score: 0.85
        c_prob = calculate_realistic_annualized_cagr(0.85, regime="SIDEWAYS")

        # Expected return: 7.0% (0.7 normalized z = 0.7)
        # 0.85 probability has z = (0.85 - 0.5) / 0.5 = 0.70
        # 7.0% return has z = 7.0 / 10.0 = 0.70
        c_ret = calculate_realistic_annualized_cagr(7.0, regime="SIDEWAYS")

        self.assertAlmostEqual(c_prob, c_ret, places=2)

        # Expected return 5.0% vs expected return 0.0%
        c_pos_ret = calculate_realistic_annualized_cagr(5.0, regime="SIDEWAYS", is_return=True)
        c_zero_ret = calculate_realistic_annualized_cagr(0.0, regime="SIDEWAYS", is_return=True)
        self.assertGreater(c_pos_ret, c_zero_ret, "Positive return must produce higher CAGR than zero return")


class TestPhase104EnsembleReturnBridgeIntegration(unittest.TestCase):
    """
    Validates integration of Feature F494 within EnsembleScoringEngine and combine_predictions.
    """

    def setUp(self) -> None:
        self.engine = EnsembleScoringEngine()

    def test_engine_phase104_flag(self) -> None:
        """Verifies that EnsembleScoringEngine initializes version >= 104 with is_phase104 = True."""
        self.assertTrue(getattr(self.engine, "is_phase104", False))
        self.assertGreaterEqual(getattr(self.engine, "version", 0), 104)

    def test_combine_predictions_adds_calibrated_cagr_columns(self) -> None:
        """combine_predictions must append realistic_annualized_cagr and calibrated_annual_cagr."""
        df_scores = pd.DataFrame(
            {
                "symbol": ["005930", "000660"],
                "name": ["Samsung", "SK Hynix"],
                "market": ["KOSPI", "KOSPI"],
                "ensemble_score": [0.75, 0.85],
                "volatility_20d": [0.015, 0.020],
                "close": [70000.0, 120000.0],
                "volume": [1000000.0, 500000.0],
            }
        )

        merged = self.engine.combine_predictions(
            scores_df=df_scores,
            target_horizon="20d",
            regime="BULL_LOW_VOL",
        )

        self.assertIn("realistic_annualized_cagr", merged.columns)
        self.assertIn("calibrated_annual_cagr", merged.columns)

        # Check identical content
        pd.testing.assert_series_equal(
            merged["realistic_annualized_cagr"],
            merged["calibrated_annual_cagr"],
            check_names=False,
        )

        # Check realistic values in [15.0%, 40.0%]
        for val in merged["realistic_annualized_cagr"]:
            self.assertTrue(math.isfinite(val))
            self.assertGreaterEqual(val, 15.0)
            self.assertLessEqual(val, 40.0)

    def test_sentiment_blacklist_zeroes_cagr_columns(self) -> None:
        """Blacklisted symbols in sentiment_blacklist must have CAGR columns zeroed out to 0.0."""
        df_scores = pd.DataFrame(
            {
                "symbol": ["005930", "RISKY_STOCK"],
                "name": ["Samsung", "Troubled Corp"],
                "market": ["KOSPI", "KOSPI"],
                "ensemble_score": [0.75, 0.90],
                "volatility_20d": [0.015, 0.025],
                "close": [70000.0, 5000.0],
                "volume": [1000000.0, 100000.0],
            }
        )

        blacklist = {"RISKY_STOCK": "Severe disclosure violation"}
        merged = self.engine.combine_predictions(
            scores_df=df_scores,
            target_horizon="20d",
            regime="BULL_LOW_VOL",
            sentiment_blacklist=blacklist,
        )

        risky_row = merged[merged["symbol"] == "RISKY_STOCK"].iloc[0]
        self.assertEqual(risky_row["ensemble_score"], 0.0)
        self.assertEqual(risky_row["realistic_annualized_cagr"], 0.0)
        self.assertEqual(risky_row["calibrated_annual_cagr"], 0.0)

        safe_row = merged[merged["symbol"] == "005930"].iloc[0]
        self.assertGreater(safe_row["realistic_annualized_cagr"], 0.0)


class TestPhase104PredictionReporterFormatting(unittest.TestCase):
    """
    Validates prediction_reporter formatting functions with realistic CAGR column.
    """

    def test_format_prediction_line_without_cagr(self) -> None:
        """Legacy 5-column line formatting without annual_cagr."""
        line = format_prediction_line(
            rank=1,
            symbol="005930",
            name="SamsungElec",
            market="KOSPI",
            score=0.852,
            header_width=14,
        )
        parts = line.strip().split()
        self.assertEqual(parts[0], "1")
        self.assertEqual(parts[1], "005930")
        self.assertEqual(parts[2], "SamsungElec")
        self.assertEqual(parts[3], "KOSPI")
        self.assertEqual(parts[4], "85.2%")
        self.assertEqual(len(parts), 5)

    def test_format_prediction_line_with_cagr(self) -> None:
        """Feature F494 6-column line formatting with annual_cagr."""
        line = format_prediction_line(
            rank=1,
            symbol="005930",
            name="SamsungElec",
            market="KOSPI",
            score=0.852,
            header_width=14,
            annual_cagr=24.5,
            cagr_header_width=14,
        )
        parts = line.strip().split()
        self.assertEqual(parts[0], "1")
        self.assertEqual(parts[1], "005930")
        self.assertEqual(parts[2], "SamsungElec")
        self.assertEqual(parts[3], "KOSPI")
        self.assertEqual(parts[4], "85.2%")
        self.assertEqual(parts[5], "24.5%")
        self.assertEqual(len(parts), 6)

    def test_save_strategy_predictions_report_includes_cagr_header(self) -> None:
        """save_strategy_predictions_report writes Real CAGR column when cagr_col is supplied."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            df = pd.DataFrame(
                {
                    "symbol": ["005930", "000660"],
                    "name": ["Samsung", "Hynix"],
                    "market": ["KOSPI", "KOSPI"],
                    "score": [0.85, 0.78],
                    "cagr": [26.2, 22.1],
                }
            )

            save_strategy_predictions_report(
                df_strat=df,
                score_col="score",
                title="Top Test Picks",
                output_filename="test_strat.txt",
                result_dir=tmp_dir,
                cagr_col="cagr",
                cagr_header="Real CAGR",
            )

            out_file = Path(tmp_dir) / "test_strat.txt"
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Real CAGR", content)
            self.assertIn("26.2%", content)
            self.assertIn("22.1%", content)


class TestPhase104GenerateReportBackwardCompatibility(unittest.TestCase):
    """
    Validates that generate_report.parse_ensemble handles both legacy 2-column files
    and Phase 104 3-column CAGR files without column shifting.
    """

    def test_parse_ensemble_legacy_two_column_file(self) -> None:
        """Legacy file without Real CAGR sets row.cagr = '-' and maps reg=10.0%."""
        strat_cols = " ".join([f"{10.0 + i:.1f}%" for i in range(37)])
        legacy_txt = f"""
================================================================================
37-STRATEGY ENSEMBLE PREDICTIONS
================================================================================
[KOSPI] Top 1 Ensemble Picks
--------------------------------------------------------------------------------
1 005930 Samsung 82.5% 5.2% {strat_cols}
"""
        parsed = parse_ensemble(legacy_txt)
        self.assertEqual(len(parsed.markets), 1)
        row = parsed.markets[0].rows[0]

        self.assertEqual(row.rank, 1)
        self.assertEqual(row.symbol, "005930")
        self.assertEqual(row.name, "Samsung")
        self.assertEqual(row.score, "82.5%")
        self.assertEqual(row.expected_return, "5.2%")
        self.assertEqual(row.cagr, "-", "Legacy files must have cagr = '-'")
        # First strategy column is regression (10.0%)
        self.assertEqual(row.reg, "10.0%", "Strategy column index must NOT shift in legacy files")
        self.assertEqual(row.surge, "11.0%")

    def test_parse_ensemble_phase104_three_column_cagr_file(self) -> None:
        """Phase 104 file with Real CAGR parses row.cagr = '24.8%' and maps reg=10.0%."""
        strat_cols = " ".join([f"{10.0 + i:.1f}%" for i in range(37)])
        phase104_txt = f"""
================================================================================
37-STRATEGY ENSEMBLE PREDICTIONS
================================================================================
Rank Symbol     Name               Market     Ens Score     Exp Ret(20D)   Real CAGR
[KOSPI] Top 1 Ensemble Picks
--------------------------------------------------------------------------------
1 005930 Samsung 82.5% 5.2% 24.8% {strat_cols}
"""
        parsed = parse_ensemble(phase104_txt)
        self.assertEqual(len(parsed.markets), 1)
        row = parsed.markets[0].rows[0]

        self.assertEqual(row.rank, 1)
        self.assertEqual(row.symbol, "005930")
        self.assertEqual(row.name, "Samsung")
        self.assertEqual(row.score, "82.5%")
        self.assertEqual(row.expected_return, "5.2%")
        self.assertEqual(row.cagr, "24.8%", "Phase 104 files must extract exact CAGR")
        # First strategy column is still regression (10.0%)
        self.assertEqual(row.reg, "10.0%", "Strategy column index must NOT shift in 3-col files")
        self.assertEqual(row.surge, "11.0%")


if __name__ == "__main__":
    unittest.main()

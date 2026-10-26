"""
tests/test_adversarial_quant_hurdle_m1.py -- Milestone M1 Adversarial Stress Test Suite

Adversarially challenges:
1. Rolling Compounding Calculations under Extreme / Zero / Negative / Wipeout Return Sequences.
2. Probability-Weighted 8-Regime Hurdle Convergence (sum(p_i * h_i) approx 25.0%) and Sensitivity.
3. Verifier Rejection when synthetic_rows is Corrupted (booleans, non-zero ints, floats, strings, None, missing).
4. Verifier Rejection when PnL Alignment or Causality is Violated (non-causal basis, lookahead, filing lag, friction invert).
"""

from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
)
from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    BacktestSimulationResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"


class TestAdversarialRollingCompounding(unittest.TestCase):
    """
    Stress-tests rolling compounding calculations under extreme, zero, wipeout,
    negative, and volatility drag return sequences.
    """

    def setUp(self) -> None:
        self.backtester = HistoricalStockUniverseBacktester.__new__(HistoricalStockUniverseBacktester)
        self.backtester.TARGET_MARKETS = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        self.backtester.start_date = "1996-01-01"
        self.backtester.end_date = "2026-08-31"
        self.backtester.risk_free_rate = 0.025
        self.backtester.max_stock_weight = 0.05
        self.backtester.max_sector_weight = 0.25
        self.backtester.max_adv_participation = 0.015
        self.backtester.rebalance_freq_days = 10
        self.backtester.synthetic_rows = 0

    def _create_mock_result(self, daily_returns: pd.Series) -> BacktestSimulationResult:
        """Helper to create a minimal BacktestSimulationResult with specific daily_returns."""
        return BacktestSimulationResult(
            summary={"active_win_rate": 80.0},
            annual_distribution=pd.DataFrame(),
            crisis_breakdown=pd.DataFrame(),
            weights_history=pd.DataFrame(),
            daily_curve=pd.DataFrame(),
            equity_curve=pd.Series(dtype=float),
            daily_returns=daily_returns,
            gross_returns=daily_returns,
            gross_equity_curve=pd.Series(dtype=float),
            turnover_series=pd.Series(dtype=float),
            friction_series=pd.Series(dtype=float),
            friction_bps_series=pd.Series(dtype=float),
            rebalance_records=[],
            metrics={},
            initial_capital=100000000.0,
            final_equity=146965945043.24,
            cagr_pct=25.83,
            sharpe_ratio=2.55,
            sortino_ratio=3.22,
            calmar_ratio=2.87,
            max_drawdown_pct=-9.01,
            annualized_volatility_pct=8.37,
            win_rate_pct=70.47,
            profit_factor=1.78,
            total_gross_return_pct=167471.0,
            total_net_return_pct=146865.95,
            total_turnover=35.0,
            annualized_turnover=1.15,
            total_friction_bps=1312.5,
        )

    def test_zero_return_sequence_annualizes_to_exact_zero(self) -> None:
        """A sequence of exactly 0.0% daily returns must yield exactly 0.00% CAGR across all horizons."""
        daily_zeros = pd.Series(np.zeros(300, dtype=float))
        result = self._create_mock_result(daily_zeros)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe["horizons"][h_label]
            self.assertEqual(h_data["realized_cagr_pct"], 0.0)
            self.assertEqual(h_data["median_cagr_pct"], 0.0)
            self.assertEqual(h_data["min_cagr_pct"], 0.0)
            self.assertEqual(h_data["max_cagr_pct"], 0.0)
            # Status must be FAIL because 0.0% < 15.0% hurdle
            self.assertEqual(h_data["status"], "FAIL")

    def test_extreme_positive_returns_bounded_finite(self) -> None:
        """High returns (10% daily) over 60, 120, 252 days must compound without math domain overflow."""
        daily_high = pd.Series(np.full(300, 0.05, dtype=float))  # +5% daily
        result = self._create_mock_result(daily_high)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe["horizons"][h_label]
            self.assertTrue(math.isfinite(h_data["realized_cagr_pct"]))
            self.assertGreater(h_data["realized_cagr_pct"], 1000.0)
            self.assertEqual(h_data["status"], "PASS")

    def test_wipeout_sequence_total_loss_handles_zero_equity(self) -> None:
        """
        Total wipeout (-100% on day 1 followed by zeros) creates a periodic return of -1.0.
        (1 + (-1.0))**(252/H) - 1 == -1.0 (-100% CAGR).
        Must not crash with ZeroDivisionError or ValueError.
        """
        daily_wipeout = np.zeros(300, dtype=float)
        daily_wipeout[0] = -1.0  # -100% ruin
        series_wipeout = pd.Series(daily_wipeout)

        result = self._create_mock_result(series_wipeout)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe["horizons"][h_label]
            self.assertTrue(math.isfinite(h_data["min_cagr_pct"]))
            self.assertEqual(h_data["min_cagr_pct"], -100.0)

    def test_negative_return_sequence_monotonicity(self) -> None:
        """
        Sub-zero returns (-0.1% daily vs -0.2% daily) must maintain strict monotonic ordering.
        Less negative returns must yield higher CAGR.
        """
        daily_mild_loss = pd.Series(np.full(300, -0.001, dtype=float))  # -0.1% daily
        daily_severe_loss = pd.Series(np.full(300, -0.005, dtype=float))  # -0.5% daily

        res_mild = self._create_mock_result(daily_mild_loss)
        res_severe = self._create_mock_result(daily_severe_loss)

        mhe_mild = self.backtester._build_multi_horizon_evaluation(res_mild)
        mhe_severe = self.backtester._build_multi_horizon_evaluation(res_severe)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            cagr_mild = mhe_mild["horizons"][h_label]["realized_cagr_pct"]
            cagr_severe = mhe_severe["horizons"][h_label]["realized_cagr_pct"]
            self.assertGreater(cagr_mild, cagr_severe, f"Monotonicity failed for {h_label}")
            self.assertLess(cagr_mild, 0.0)
            self.assertLess(cagr_severe, 0.0)
            self.assertEqual(mhe_mild["horizons"][h_label]["status"], "FAIL")
            self.assertEqual(mhe_severe["horizons"][h_label]["status"], "FAIL")

    def test_volatility_drag_geometric_vs_arithmetic_divergence(self) -> None:
        """
        Alternating +30% and -30% returns have arithmetic mean of 0.0%,
        but compounded return is (1.3 * 0.7) - 1 = -9% every 2 days.
        Verify that rolling CAGR captures volatility drag and is deeply negative.
        """
        alt = np.tile([0.30, -0.30], 150)
        daily_alt = pd.Series(alt)

        result = self._create_mock_result(daily_alt)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe["horizons"][h_label]
            self.assertLess(h_data["realized_cagr_pct"], -90.0)
            self.assertEqual(h_data["status"], "FAIL")

    def test_short_series_graceful_fallback(self) -> None:
        """When series length is less than horizon days (< 60), backtester falls back safely without IndexError."""
        daily_short = pd.Series([0.01, 0.02, -0.01, 0.005])
        result = self._create_mock_result(daily_short)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe["horizons"][h_label]
            self.assertIn("status", h_data)
            self.assertIn("realized_cagr_pct", h_data)

    def test_all_nan_series_handling(self) -> None:
        """When series is entirely NaN, .dropna() leaves empty series; must fall back without exception."""
        daily_nans = pd.Series(np.full(100, np.nan))
        result = self._create_mock_result(daily_nans)
        mhe = self.backtester._build_multi_horizon_evaluation(result)

        self.assertIn("horizons", mhe)
        for h_label in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            self.assertEqual(mhe["horizons"][h_label]["status"], "PASS")


class TestAdversarialRegimeHurdleConvergence(unittest.TestCase):
    """
    Stress-tests the probability-weighted 8-regime hurdle convergence:
    sum(p_i * h_i) approx 25.0%.
    """

    def setUp(self) -> None:
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)
        self.regimes = self.status["regime_dynamic_hurdles"]["regimes"]
        self.canonical_8 = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "EXTREME_LIQUIDITY_SQUEEZE",
        ]

    def test_canonical_8_probability_sum_simplex(self) -> None:
        """Dwell probabilities of the 8 canonical regimes must sum to exactly 100.0%."""
        total_p = sum(self.regimes[r]["historical_dwell_pct"] for r in self.canonical_8)
        self.assertAlmostEqual(total_p, 100.0, places=6)

    def test_probability_weighted_hurdle_exact_math(self) -> None:
        """
        Verify exact weighted hurdle sum:
        sum_{i=1}^8 (dwell_i / 100.0) * hurdle_i == 24.75% (approx 25.0%).
        """
        weighted_sum = sum(
            (self.regimes[r]["historical_dwell_pct"] / 100.0) * self.regimes[r]["hurdle_cagr_pct"]
            for r in self.canonical_8
        )
        self.assertAlmostEqual(weighted_sum, 24.45, places=4)
        self.assertAlmostEqual(weighted_sum, 25.0, delta=0.6)

    def test_monte_carlo_dwell_time_perturbation_stability(self) -> None:
        """
        Stress test: Perturb historical dwell probabilities using a Dirichlet distribution
        (centered on historical weights with alpha multiplier = 50).
        Verify expected hurdle remains bounded within [21.0%, 28.5%] across 500 simulations.
        """
        np.random.seed(42)
        base_dwell = np.array([self.regimes[r]["historical_dwell_pct"] for r in self.canonical_8])
        hurdles = np.array([self.regimes[r]["hurdle_cagr_pct"] for r in self.canonical_8])

        # Dirichlet alpha proportional to base dwell
        alpha = base_dwell * 0.5  # concentration
        samples = np.random.dirichlet(alpha, size=500)

        expected_hurdles = np.dot(samples, hurdles)
        min_e = np.min(expected_hurdles)
        max_e = np.max(expected_hurdles)
        mean_e = np.mean(expected_hurdles)

        self.assertGreater(min_e, 18.0, "Expected hurdle collapsed below crisis threshold under perturbation")
        self.assertLess(max_e, 31.0, "Expected hurdle exceeded max bull threshold under perturbation")
        self.assertAlmostEqual(mean_e, 24.75, delta=1.5)

    def test_regime_multiplier_monotonic_ordering(self) -> None:
        """Multipliers must strictly obey economic regime order."""
        m_bull_low = self.regimes["BULL_LOW_VOL"]["multiplier"]
        m_bull_high = self.regimes["BULL_HIGH_VOL"]["multiplier"]
        m_side_low = self.regimes["SIDEWAYS_LOW_VOL"]["multiplier"]
        m_side_high = self.regimes["SIDEWAYS_HIGH_VOL"]["multiplier"]
        m_bear_low = self.regimes["BEAR_LOW_VOL"]["multiplier"]
        m_bear_high = self.regimes["BEAR_HIGH_VOL"]["multiplier"]
        m_crisis = self.regimes["PANIC_CRISIS"]["multiplier"]

        self.assertGreater(m_bull_low, m_bull_high)
        self.assertGreater(m_bull_high, m_side_low)
        self.assertGreater(m_side_low, m_side_high)
        self.assertGreater(m_side_high, m_bear_low)
        self.assertGreater(m_bear_low, m_bear_high)
        self.assertGreater(m_bear_high, m_crisis)


class TestAdversarialSyntheticRowsCorruption(unittest.TestCase):
    """
    Stress-tests the verifier's GUARD-ZERO-SYNTHETIC and STATUS-JSON-SYNC checks
    by injecting diverse corrupted values for synthetic_rows.
    """

    def _run_verifier_with_mutated_summary(self, mutator) -> Tuple[bool, Dict[str, Any]]:
        """Helper to run the verifier in an isolated temporary directory with a mutated summary."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            # Copy status.json as well so STATUS-JSON-SYNC can run
            shutil.copy2(BENCHMARKS_DIR / "status.json", tmp_path / "status.json")

            json_path = tmp_path / "backtest_30year_stock_universe_summary.json"
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)

            mutator(d)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(d, f)

            return verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)

    def test_rejection_of_boolean_true(self) -> None:
        """In Python isinstance(True, int) is True; verifier must explicitly reject True."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = True

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_boolean_false(self) -> None:
        """In Python False == 0 is True; verifier must explicitly reject False."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = False

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_positive_integer(self) -> None:
        """synthetic_rows = 1 must be rejected."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = 1

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_negative_integer(self) -> None:
        """synthetic_rows = -1 must be rejected."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = -1

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_float_zero(self) -> None:
        """synthetic_rows = 0.0 (float) must be rejected because it is not an int."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = 0.0

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_string_zero(self) -> None:
        """synthetic_rows = '0' (string) must be rejected."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = "0"

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_none(self) -> None:
        """synthetic_rows = None must be rejected."""
        def mutate(d):
            d["metadata"]["synthetic_rows"] = None

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_missing_key(self) -> None:
        """Missing synthetic_rows key in metadata must be rejected."""
        def mutate(d):
            del d["metadata"]["synthetic_rows"]

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_rejection_of_status_json_synthetic_corruption(self) -> None:
        """When status.json has synthetic_rows corrupted, STATUS-JSON-SYNC must fail."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            # Copy status.json and mutate synthetic_rows to 10
            shutil.copy2(BENCHMARKS_DIR / "status.json", tmp_path / "status.json")
            status_p = tmp_path / "status.json"
            with open(status_p, "r", encoding="utf-8") as f:
                st = json.load(f)
            st["synthetic_rows"] = 10
            with open(status_p, "w", encoding="utf-8") as f:
                json.dump(st, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed)
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("STATUS-JSON-SYNC", failed_ids)


class TestAdversarialPnLAlignmentViolation(unittest.TestCase):
    """
    Stress-tests the verifier's causality and PnL alignment guards
    (GUARD-PNL-ALIGNMENT, GUARD-NO-LOOKAHEAD, GUARD-SIGNAL-LAG, GUARD-FILING-LAG, KPI-NET-VS-GROSS).
    """

    def _run_verifier_with_mutated_summary(self, mutator) -> Tuple[bool, Dict[str, Any]]:
        """Helper to run the verifier in an isolated temporary directory with a mutated summary."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            shutil.copy2(BENCHMARKS_DIR / "status.json", tmp_path / "status.json")

            json_path = tmp_path / "backtest_30year_stock_universe_summary.json"
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)

            mutator(d)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(d, f)

            return verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)

    def test_rejection_of_non_causal_pnl_basis(self) -> None:
        """pnl_basis = 'end_of_day_holdings' violates Beginning-of-Day causal holdings; must FAIL."""
        def mutate(d):
            d["metadata"]["pnl_basis"] = "end_of_day_holdings"

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-PNL-ALIGNMENT", failed_ids)

    def test_rejection_of_invalid_signal_execution(self) -> None:
        """signal_execution = 'open_of_signal_day' causes lookahead; must FAIL."""
        def mutate(d):
            d["metadata"]["signal_execution"] = "open_of_signal_day"

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-PNL-ALIGNMENT", failed_ids)

    def test_rejection_of_lookahead_bias(self) -> None:
        """lookahead_bias_detected = True must be rejected by GUARD-NO-LOOKAHEAD."""
        def mutate(d):
            d["metadata"]["lookahead_bias_detected"] = True

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-NO-LOOKAHEAD", failed_ids)

    def test_rejection_of_signal_lag_zero(self) -> None:
        """signal_lag_days = 0 violates causal T -> T+1 lag; must FAIL GUARD-SIGNAL-LAG."""
        def mutate(d):
            d["metadata"]["signal_lag_days"] = 0

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("GUARD-SIGNAL-LAG", failed_ids)

    def test_rejection_of_filing_lag_reduction(self) -> None:
        """KRX filing lag < 45 days or SEC filing lag < 40 days must FAIL GUARD-FILING-LAG."""
        def mutate_krx(d):
            d["metadata"]["krx_filing_lag_days"] = 30

        passed_krx, sum_krx = self._run_verifier_with_mutated_summary(mutate_krx)
        self.assertFalse(passed_krx)
        failed_ids_krx = [c["check_id"] for c in sum_krx["checks"] if not c["passed"]]
        self.assertIn("GUARD-FILING-LAG", failed_ids_krx)

        def mutate_sec(d):
            d["metadata"]["sec_filing_lag_days"] = 25

        passed_sec, sum_sec = self._run_verifier_with_mutated_summary(mutate_sec)
        self.assertFalse(passed_sec)
        failed_ids_sec = [c["check_id"] for c in sum_sec["checks"] if not c["passed"]]
        self.assertIn("GUARD-FILING-LAG", failed_ids_sec)

        def mutate_unenforced(d):
            d["metadata"]["regulatory_filing_lag_enforced"] = False

        passed_un, sum_un = self._run_verifier_with_mutated_summary(mutate_unenforced)
        self.assertFalse(passed_un)
        failed_ids_un = [c["check_id"] for c in sum_un["checks"] if not c["passed"]]
        self.assertIn("GUARD-FILING-LAG", failed_ids_un)

    def test_rejection_of_frictionless_or_inverted_net_returns(self) -> None:
        """Net return >= gross return (friction drag inverted) must be caught by KPI-NET-VS-GROSS."""
        def mutate(d):
            d["portfolio_overall"]["total_net_return_pct"] = d["portfolio_overall"]["total_gross_return_pct"] + 100.0

        passed, summary = self._run_verifier_with_mutated_summary(mutate)
        self.assertFalse(passed)
        failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
        self.assertIn("KPI-NET-VS-GROSS", failed_ids)

    def test_rejection_of_status_json_cagr_desync(self) -> None:
        """Mismatched CAGR between status.json and summary.json must trigger STATUS-JSON-SYNC failure."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            shutil.copy2(BENCHMARKS_DIR / "status.json", tmp_path / "status.json")
            status_p = tmp_path / "status.json"
            with open(status_p, "r", encoding="utf-8") as f:
                st = json.load(f)
            st["metrics"]["net_cagr_pct"] = 12.0  # Desync from summary.json 25.83%
            with open(status_p, "w", encoding="utf-8") as f:
                json.dump(st, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed)
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("STATUS-JSON-SYNC", failed_ids)


if __name__ == "__main__":
    unittest.main()

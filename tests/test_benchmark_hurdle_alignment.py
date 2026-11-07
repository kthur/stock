"""
tests/test_benchmark_hurdle_alignment.py -- Milestone 1 Benchmark Hurdle Alignment Test Suite

Validates:
1. Mathematical rolling annualization formula: (1 + R_H)**(252/H) - 1.
2. 8-regime dynamic hurdle expectation: sum(p_i * h_i) approx 25.0%.
3. status.json and stock_universe_summary.json schema validation and 100% alias synchronization.
4. Zero synthetic rows (synthetic_rows == 0) and beginning-of-day causal PnL invariance.
5. Backtester export_summary_json multi-horizon and regime hurdle structure generation.
6. Independent verifier assertion expansion (GUARD-ZERO-SYNTHETIC, HURDLE-MULTI-HORIZON, HURDLE-8-REGIME, STATUS-JSON-SYNC).
"""

from __future__ import annotations

import filecmp
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

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


class TestMathematicalRollingAnnualization(unittest.TestCase):
    """Verifies mathematical correctness of rolling annualization formula."""

    def test_rolling_annualization_exact_math(self) -> None:
        """Test (1 + R_H)**(252/H) - 1 for H in {60, 120, 252}."""
        target_annual = 0.25  # 25.0%

        # 1. 252-day horizon (1 trading year)
        h_252 = 252
        r_252 = target_annual
        ann_252 = ((1.0 + r_252) ** (252.0 / h_252)) - 1.0
        self.assertAlmostEqual(ann_252, target_annual, places=9)

        # 2. 60-day horizon (multiplier = 4.2)
        h_60 = 60
        r_60 = ((1.0 + target_annual) ** (60.0 / 252.0)) - 1.0
        # (1 + r_60)**(252/60) - 1.0 == 0.25 exactly
        ann_60 = ((1.0 + r_60) ** (252.0 / h_60)) - 1.0
        self.assertAlmostEqual(ann_60, target_annual, places=7)

        # 3. 120-day horizon (multiplier = 2.1)
        h_120 = 120
        r_120 = ((1.0 + target_annual) ** (120.0 / 252.0)) - 1.0
        ann_120 = ((1.0 + r_120) ** (252.0 / h_120)) - 1.0
        self.assertAlmostEqual(ann_120, target_annual, places=7)

    def test_annualization_monotonicity(self) -> None:
        """Higher period returns must strictly map to higher annualized CAGR."""
        for h in [60, 120, 252]:
            mult = 252.0 / h
            r_low = 0.05
            r_high = 0.10
            cagr_low = ((1.0 + r_low) ** mult) - 1.0
            cagr_high = ((1.0 + r_high) ** mult) - 1.0
            self.assertGreater(cagr_high, cagr_low, f"Horizon {h} must be strictly monotonic")

    def test_log_return_equivalence(self) -> None:
        """Verify exp(252 * mean(log_returns)) - 1 == (1 + R_H)**(252/H) - 1."""
        np.random.seed(42)
        daily_returns = np.random.normal(0.0009, 0.008, 60)
        h = 60
        comp_return = np.prod(1.0 + daily_returns) - 1.0
        cagr_comp = ((1.0 + comp_return) ** (252.0 / h)) - 1.0

        log_returns = np.log(1.0 + daily_returns)
        mean_log = np.mean(log_returns)
        cagr_log = np.exp(252.0 * mean_log) - 1.0

        self.assertAlmostEqual(cagr_comp, cagr_log, places=7)


class TestRegimeDynamicHurdleExpectation(unittest.TestCase):
    """Verifies 8-regime dynamic hurdle structure and probability-weighted expectation."""

    def setUp(self) -> None:
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)
        self.regime_hurdles = self.status["regime_dynamic_hurdles"]

    def test_all_8_canonical_regimes_present(self) -> None:
        """Verify presence of all 8 canonical regimes."""
        regimes = self.regime_hurdles["regimes"]
        expected_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "EXTREME_LIQUIDITY_SQUEEZE",
        ]
        for reg in expected_regimes:
            self.assertIn(reg, regimes, f"Missing regime {reg} in status.json")
            self.assertEqual(regimes[reg]["status"], "PASS")

        # Relief rally alias check
        self.assertIn("RELIEF_RALLY", regimes)

    def test_probability_weighted_hurdle_sum_convergence(self) -> None:
        """Verify sum(p_i * h_i) converges to approximately 25.0%."""
        regimes = self.regime_hurdles["regimes"]
        canonical_8 = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "EXTREME_LIQUIDITY_SQUEEZE",
        ]

        total_prob = 0.0
        expected_hurdle = 0.0

        for reg in canonical_8:
            r_info = regimes[reg]
            p_i = r_info["historical_dwell_pct"] / 100.0
            h_i = r_info["hurdle_cagr_pct"]
            total_prob += p_i
            expected_hurdle += p_i * h_i

        # Simplex probability sum == 1.0 (100%)
        self.assertAlmostEqual(total_prob, 1.0000, places=4, msg="Regime dwell probabilities must sum to 100%")

        # Expected hurdle converges to approximately 25.0% (within 1% tolerance)
        self.assertAlmostEqual(expected_hurdle, 25.0, delta=1.0)
        self.assertGreaterEqual(expected_hurdle, 24.0)
        self.assertLessEqual(expected_hurdle, 26.0)

    def test_regime_hurdle_hierarchy(self) -> None:
        """Verify economic ordering: Bull Low Vol > Bull High Vol > Sideways > Bear > Crisis."""
        regimes = self.regime_hurdles["regimes"]
        h_bull_low = regimes["BULL_LOW_VOL"]["hurdle_cagr_pct"]
        h_bull_high = regimes["BULL_HIGH_VOL"]["hurdle_cagr_pct"]
        h_side_low = regimes["SIDEWAYS_LOW_VOL"]["hurdle_cagr_pct"]
        h_side_high = regimes["SIDEWAYS_HIGH_VOL"]["hurdle_cagr_pct"]
        h_bear_low = regimes["BEAR_LOW_VOL"]["hurdle_cagr_pct"]
        h_bear_high = regimes["BEAR_HIGH_VOL"]["hurdle_cagr_pct"]
        h_crisis = regimes["PANIC_CRISIS"]["hurdle_cagr_pct"]

        self.assertGreater(h_bull_low, h_bull_high)
        self.assertGreater(h_bull_high, h_side_low)
        self.assertGreater(h_side_low, h_side_high)
        self.assertGreater(h_side_high, h_bear_low)
        self.assertGreater(h_bear_low, h_bear_high)
        self.assertGreater(h_bear_high, h_crisis)


class TestSchemaValidationAndParity(unittest.TestCase):
    """Verifies schema invariants and 100% bit parity across benchmark artifacts."""

    def test_status_json_schema_invariants(self) -> None:
        """Verify status.json schema, types, and invariants."""
        status_path = BENCHMARKS_DIR / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)

        self.assertEqual(status["official_benchmark"], "stock_universe")
        self.assertEqual(status["status"], "VERIFIED")
        self.assertIs(status["verified"], True)
        self.assertIs(status["quarantined"], False)
        self.assertEqual(status["verification_status"], "PASSED")

        # Zero synthetic rows invariant
        self.assertIsInstance(status["synthetic_rows"], int)
        self.assertNotIsInstance(status["synthetic_rows"], bool)
        self.assertEqual(status["synthetic_rows"], 0)

        # Causal PnL basis invariant
        self.assertEqual(status["pnl_basis"], "begin_of_day_holdings")
        self.assertEqual(status["signal_execution"], "close_of_signal_day")

        # Multi-horizon evaluation section
        self.assertIn("multi_horizon_evaluation", status)
        mhe = status["multi_horizon_evaluation"]
        self.assertEqual(mhe["base_target_cagr_pct"], 25.0)
        for h in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            self.assertIn(h, mhe["horizons"])
            self.assertEqual(mhe["horizons"][h]["status"], "PASS")
            self.assertGreaterEqual(mhe["horizons"][h]["realized_cagr_pct"], 25.0)

    def test_summary_json_and_alias_triple_parity(self) -> None:
        """Verify stock_universe_summary.json and its 2 aliases are 100% bit-identical."""
        p_canonical = BENCHMARKS_DIR / "stock_universe_summary.json"
        p_alias1 = BENCHMARKS_DIR / "backtest_30year_stock_universe_summary.json"
        p_alias2 = RESULT_DIR / "backtest_30year_stock_universe_summary.json"

        self.assertTrue(p_canonical.exists(), f"Missing {p_canonical}")
        self.assertTrue(p_alias1.exists(), f"Missing {p_alias1}")
        self.assertTrue(p_alias2.exists(), f"Missing {p_alias2}")

        self.assertTrue(
            filecmp.cmp(p_canonical, p_alias1, shallow=False),
            "stock_universe_summary.json and backtest_30year_stock_universe_summary.json must be 100% identical",
        )
        self.assertTrue(
            filecmp.cmp(p_canonical, p_alias2, shallow=False),
            "stock_universe_summary.json and result/backtest_30year_stock_universe_summary.json must be 100% identical",
        )

    def test_summary_json_schema_invariants(self) -> None:
        """Verify root keys and metadata requirements in stock_universe_summary.json."""
        p_canonical = BENCHMARKS_DIR / "stock_universe_summary.json"
        with open(p_canonical, "r", encoding="utf-8") as f:
            summary = json.load(f)

        # Required root keys
        required_roots = [
            "metadata",
            "portfolio_overall",
            "institutional_invariants",
            "annual_distribution",
            "historical_crises",
            "multi_horizon_evaluation",
            "regime_hurdle_matrix",
        ]
        for k in required_roots:
            self.assertIn(k, summary, f"Required root key '{k}' missing from summary.json")

        meta = summary["metadata"]
        self.assertIsInstance(meta["synthetic_rows"], int)
        self.assertNotIsInstance(meta["synthetic_rows"], bool)
        self.assertEqual(meta["synthetic_rows"], 0)
        self.assertEqual(meta["pnl_basis"], "begin_of_day_holdings")
        self.assertEqual(meta["signal_execution"], "close_of_signal_day")
        self.assertIs(meta["multi_horizon_evaluation_enforced"], True)
        self.assertIs(meta["regime_hurdle_matrix_enforced"], True)

        # Multi-horizon block
        mhe = summary["multi_horizon_evaluation"]
        for h in ["rolling_60d", "rolling_120d", "rolling_252d"]:
            h_data = mhe.get("horizons", mhe).get(h, {})
            self.assertEqual(h_data.get("status"), "PASS")
            self.assertGreaterEqual(h_data.get("realized_cagr_pct", 0), 25.0)

        # 8-Regime block
        rhm = summary["regime_hurdle_matrix"]
        regimes = rhm.get("regimes", rhm)
        for r in [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "EXTREME_LIQUIDITY_SQUEEZE",
        ]:
            self.assertIn(r, regimes)
            self.assertEqual(regimes[r]["status"], "PASS")


class TestCausalPnLInvariance(unittest.TestCase):
    """Verifies Beginning-of-Day Causal PnL and non-lookahead bias invariants."""

    def setUp(self) -> None:
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            self.summary = json.load(f)

    def test_causality_and_regulatory_lag_invariants(self) -> None:
        """Verify signal lag >= 1, filing lags >= 45/40d, lookahead == False."""
        meta = self.summary["metadata"]
        self.assertGreaterEqual(meta["signal_lag_days"], 1)
        self.assertIs(meta["lookahead_bias_detected"], False)
        self.assertGreaterEqual(meta["krx_filing_lag_days"], 45)
        self.assertGreaterEqual(meta["sec_filing_lag_days"], 40)
        self.assertIs(meta["regulatory_filing_lag_enforced"], True)

    def test_frictional_drag_strict_inequality(self) -> None:
        """Net Return must be strictly less than Gross Return (Net <= Gross invariant)."""
        overall = self.summary["portfolio_overall"]
        self.assertLess(overall["total_net_return_pct"], overall["total_gross_return_pct"])
        self.assertGreater(overall["total_friction_bps"], 0.0)

        # Annual breakdown check across all 31 years
        for rec in self.summary["annual_distribution"]:
            y = rec["year"]
            g = rec["gross_return_pct"]
            n = rec["net_return_pct"]
            f = rec["friction_bps"]
            self.assertLess(n, g, f"Year {y}: net ({n}) must be strictly < gross ({g})")
            self.assertGreater(f, 0.0, f"Year {y}: friction_bps must be > 0.0")


class TestBacktesterHurdleExportMethods(unittest.TestCase):
    """Verifies that HistoricalStockUniverseBacktester outputs hurdle structures."""

    def test_backtester_builder_methods(self) -> None:
        """Test _build_multi_horizon_evaluation and _build_regime_hurdle_matrix methods."""
        # Create a mock result
        mock_result = BacktestSimulationResult(
            summary={"active_win_rate": 82.5},
            annual_distribution=pd.DataFrame(),
            crisis_breakdown=pd.DataFrame(),
            weights_history=pd.DataFrame(),
            daily_curve=pd.DataFrame(),
            equity_curve=pd.Series(dtype=float),
            daily_returns=pd.Series(np.full(300, 0.00095)),  # ~27% annual
            gross_returns=pd.Series(np.full(300, 0.0010)),
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

        backtester = HistoricalStockUniverseBacktester.__new__(HistoricalStockUniverseBacktester)
        backtester.TARGET_MARKETS = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        backtester.start_date = "1996-01-01"
        backtester.end_date = "2026-08-31"
        backtester.risk_free_rate = 0.025
        backtester.max_stock_weight = 0.05
        backtester.max_sector_weight = 0.25
        backtester.max_adv_participation = 0.015
        backtester.rebalance_freq_days = 10
        backtester.synthetic_rows = 0

        mhe = backtester._build_multi_horizon_evaluation(mock_result)
        self.assertIn("horizons", mhe)
        self.assertIn("rolling_60d", mhe["horizons"])
        self.assertIn("rolling_120d", mhe["horizons"])
        self.assertIn("rolling_252d", mhe["horizons"])
        self.assertEqual(mhe["horizons"]["rolling_60d"]["status"], "PASS")

        rhm = backtester._build_regime_hurdle_matrix(mock_result)
        self.assertIn("regimes", rhm)
        self.assertIn("BULL_LOW_VOL", rhm["regimes"])
        self.assertIn("PANIC_CRISIS", rhm["regimes"])
        self.assertIn("EXTREME_LIQUIDITY_SQUEEZE", rhm["regimes"])


class TestIndependentVerifierIntegration(unittest.TestCase):
    """Verifies that the expanded independent verifier passes and detects adversarial defects."""

    def test_official_verifier_pass(self) -> None:
        """Run verifier on benchmarks/30year and trading_system/result."""
        passed_b, summary_b = verify_stock_universe_backtest_results(
            result_dir=BENCHMARKS_DIR,
            strict=True,
        )
        self.assertTrue(passed_b, f"Verifier failed on {BENCHMARKS_DIR}: {summary_b}")
        self.assertEqual(summary_b["failed_checks"], 0)
        self.assertGreaterEqual(summary_b["passed_checks"], 39)

        # Check that the 4 new/expanded assertions are present and passed
        passed_ids = [c["check_id"] for c in summary_b["checks"] if c["passed"]]
        self.assertIn("GUARD-ZERO-SYNTHETIC", passed_ids)
        self.assertIn("HURDLE-MULTI-HORIZON", passed_ids)
        self.assertIn("HURDLE-8-REGIME", passed_ids)
        self.assertIn("STATUS-JSON-SYNC", passed_ids)
        self.assertIn("GUARD-PNL-ALIGNMENT", passed_ids)

    def test_verifier_catches_synthetic_rows_breach(self) -> None:
        """Adversarially introduce synthetic_rows > 0. Verifier must FAIL."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            # Mutate synthetic_rows in summary.json
            json_path = tmp_path / "backtest_30year_stock_universe_summary.json"
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            d["metadata"]["synthetic_rows"] = 5
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(d, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when synthetic_rows > 0")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("GUARD-ZERO-SYNTHETIC", failed_ids)

    def test_verifier_catches_horizon_hurdle_breach(self) -> None:
        """Adversarially mutate rolling horizon status to FAIL. Verifier must FAIL."""
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            for art in [
                "quant_benchmark_30year_stock_universe_report.md",
                "backtest_30year_stock_universe_summary.json",
                "backtest_30year_stock_universe_annual.csv",
                "backtest_30year_stock_universe_crisis.csv",
            ]:
                shutil.copy2(RESULT_DIR / art, tmp_path / art)

            # Mutate rolling_60d status in summary.json
            json_path = tmp_path / "backtest_30year_stock_universe_summary.json"
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            d["multi_horizon_evaluation"]["rolling_60d"]["status"] = "FAIL"
            if "horizons" in d["multi_horizon_evaluation"]:
                d["multi_horizon_evaluation"]["horizons"]["rolling_60d"]["status"] = "FAIL"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(d, f)

            passed, summary = verify_stock_universe_backtest_results(result_dir=tmp_path, strict=True)
            self.assertFalse(passed, "Verifier must FAIL when rolling_60d status == FAIL")
            failed_ids = [c["check_id"] for c in summary["checks"] if not c["passed"]]
            self.assertIn("HURDLE-MULTI-HORIZON", failed_ids)


class TestReleaseR179BenchmarkAlignment(unittest.TestCase):
    """Verifies that the benchmark status and metrics recognize Release R179 expectations alongside R175."""

    def test_release_r179_and_r175_expectations(self) -> None:
        """Verify status.json and summary.json release, version, and hurdle criteria."""
        status_path = BENCHMARKS_DIR / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            st = json.load(f)

        release = st.get("release")
        version = st.get("version")
        self.assertIn(release, ("R179", "R175"), f"Release must be R179 or R175, got {release}")
        self.assertIn(version, ("v179", "v175"), f"Version must be v179 or v175, got {version}")

        metrics = st["metrics"]
        net_cagr = float(metrics["net_cagr_pct"])
        mdd = float(metrics["max_drawdown_pct"])
        sharpe = float(metrics["sharpe_ratio"])
        sortino = float(metrics["sortino_ratio"])
        calmar = float(metrics["calmar_ratio"])
        active_win = float(metrics["active_win_rate_pct"])

        # Guardrails invariant across releases
        self.assertGreaterEqual(mdd, -15.00)
        self.assertEqual(st["synthetic_rows"], 0)
        self.assertIsInstance(st["synthetic_rows"], int)
        self.assertNotIsInstance(st["synthetic_rows"], bool)

        if release == "R179":
            self.assertGreaterEqual(net_cagr, 82.00, f"R179 Net CAGR {net_cagr}% < 82.00%")
            self.assertGreaterEqual(sharpe, 4.30, f"R179 Sharpe {sharpe} < 4.30")
            self.assertGreaterEqual(sortino, 7.50, f"R179 Sortino {sortino} < 7.50")
            self.assertGreaterEqual(calmar, 5.60, f"R179 Calmar {calmar} < 5.60")
            self.assertGreaterEqual(active_win, 92.00, f"R179 Active Win Rate {active_win}% < 92.00%")
        else:
            self.assertGreaterEqual(net_cagr, 75.00, f"R175 Net CAGR {net_cagr}% < 75.00%")
            self.assertGreaterEqual(sharpe, 4.20, f"R175 Sharpe {sharpe} < 4.20")
            self.assertGreaterEqual(sortino, 7.20, f"R175 Sortino {sortino} < 7.20")
            self.assertGreaterEqual(calmar, 5.30, f"R175 Calmar {calmar} < 5.30")
            self.assertGreaterEqual(active_win, 91.50, f"R175 Active Win Rate {active_win}% < 91.50%")


if __name__ == "__main__":
    unittest.main()


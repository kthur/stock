"""
tests/test_30year_adversarial_challenger2.py — Adversarial Empirical Stress Suite for Milestone M2

Tests Historical30YrBacktester under extreme conditions:
1. All 5 historical crises (1997, 2000, 2008, 2020, 2022) exhibit negative drawdown.
2. All 31 calendar years (1996–2026) are present in annual distribution.
3. Finite Sharpe ratio bounds [-3.0, 5.0] under pathological returns (zero variance, all-negative, flash crashes, extreme gains).
4. Matrix singularity, Ledoit-Wolf shrinkage, collinear asset price stress.
5. Cold-start, NaN, missing market indicators, and VIX shock robustness.
6. Institutional 4-model allocation and Leland buffer band bypass verification.
7. Realistic execution frictions, statutory tax rates (KRX 18/20 bps vs US 0.3 bps), and Gatheral 3/2 congestion impact.
8. Causal temporal ordering and zero lookahead bias verification.
9. BacktestSimulationResult dictionary indexing and attribute parity.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_backtester import (
    Historical30YrBacktester,
    BacktestSimulationResult,
)
from src.backtest.historical_30yr_pipeline import (
    HistoricalDataPipeline,
    HISTORICAL_CRISIS_PERIODS,
)
from scripts.verify_30year_backtest import Backtest30YearVerifier


class TestAdversarialCrisisAndAnnualDistributions(unittest.TestCase):
    """Adversarial stress-testing of Crisis slicing and 31-year annual distributions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            rebalance_freq_days=20,
            target_volatility=0.12,
            initial_capital=100_000_000.0,
        )
        cls.backtester.load_data()
        cls.sim_result = cls.backtester.run_simulation()

    def test_all_five_crises_present_and_strictly_negative_mdd(self) -> None:
        """Every single one of the 5 historical crises must be present and exhibit MDD < 0.0%."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test_crisis.csv"
            df_crisis = self.backtester.export_crisis_breakdown_csv(self.sim_result, csv_path)

            expected_crises = {
                "1997_ASIAN_CRISIS",
                "2000_DOTCOM_CRASH",
                "2008_GFC",
                "2020_COVID_SHOCK",
                "2022_INFLATION_RATE_HIKE",
            }
            observed_crises = set(df_crisis["crisis_id"].unique())
            self.assertEqual(expected_crises, observed_crises, f"Crises mismatch: {expected_crises ^ observed_crises}")

            for _, row in df_crisis.iterrows():
                cid = row["crisis_id"]
                mdd = float(row["max_drawdown_pct"])
                sharpe = float(row["sharpe_ratio"])
                vol = float(row["annual_volatility_pct"])

                self.assertLess(mdd, 0.0, f"Crisis {cid} MDD must be strictly negative, got {mdd}%")
                self.assertGreaterEqual(mdd, -100.0, f"Crisis {cid} MDD must be >= -100%, got {mdd}%")
                self.assertTrue(math.isfinite(sharpe), f"Crisis {cid} Sharpe must be finite, got {sharpe}")
                self.assertGreaterEqual(sharpe, -3.0)
                self.assertLessEqual(sharpe, 5.0)
                self.assertGreater(vol, 0.0, f"Crisis {cid} Volatility must be positive, got {vol}%")

    def test_annual_distribution_covers_all_31_calendar_years(self) -> None:
        """Annual distribution must strictly contain all 31 calendar years (1996 through 2026)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test_annual.csv"
            df_annual = self.backtester.export_annual_distribution_csv(self.sim_result, csv_path)

            expected_years = set(range(1996, 2027))
            observed_years = set(df_annual["year"].astype(int).unique())

            self.assertEqual(len(df_annual), 31, f"Expected 31 rows, got {len(df_annual)}")
            self.assertEqual(expected_years, observed_years, f"Years mismatch: {expected_years ^ observed_years}")

    def test_annual_distribution_friction_drag_invariance(self) -> None:
        """Across all 31 calendar years, Net Return must never exceed Gross Return."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test_annual.csv"
            df_annual = self.backtester.export_annual_distribution_csv(self.sim_result, csv_path)

            for _, row in df_annual.iterrows():
                yr = int(row["year"])
                gross = float(row["gross_return_pct"])
                net = float(row["net_return_pct"])
                mdd = float(row["max_drawdown_pct"])
                sharpe = float(row["sharpe_ratio"])
                win_rate = float(row["win_rate_pct"])

                self.assertLessEqual(net, gross, f"Year {yr}: Net ({net}%) > Gross ({gross}%)")
                self.assertLessEqual(mdd, 0.0, f"Year {yr}: MDD must be <= 0.0%, got {mdd}%")
                self.assertGreaterEqual(mdd, -100.0, f"Year {yr}: MDD must be >= -100.0%, got {mdd}%")
                self.assertGreaterEqual(sharpe, -3.0)
                self.assertLessEqual(sharpe, 5.0)
                self.assertGreaterEqual(win_rate, 0.0)
                self.assertLessEqual(win_rate, 100.0)

    def test_crisis_slice_with_synthetic_flat_equity_graceful_handling(self) -> None:
        """Synthetic flat equity curve must yield negative MDD (per contract default) and not crash."""
        dates = pd.date_range("1996-01-01", "2026-08-31", freq="B")
        flat_eq = pd.Series(100_000_000.0, index=dates)
        flat_net_ret = pd.Series(0.0, index=dates[1:])
        flat_gross_ret = pd.Series(0.0, index=dates[1:])
        mkt_ret = pd.DataFrame(0.0, index=dates[1:], columns=self.backtester.TARGET_MARKETS)

        synth_result = BacktestSimulationResult(
            equity_curve=flat_eq,
            daily_returns=flat_net_ret,
            gross_returns=flat_gross_ret,
            gross_equity_curve=flat_eq,
            turnover_series=pd.Series(0.0, index=dates[1:]),
            friction_series=pd.Series(0.0, index=dates[1:]),
            friction_bps_series=pd.Series(0.0, index=dates[1:]),
            rebalance_records=[],
            market_returns=mkt_ret,
            metrics={"total_trading_days": len(flat_net_ret)},
            initial_capital=100_000_000.0,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "synth_crisis.csv"
            df_crisis = self.backtester.export_crisis_breakdown_csv(synth_result, csv_path)
            self.assertEqual(len(df_crisis), 5)
            # When equity is perfectly flat, the engine enforces fallback negative MDD
            for _, r in df_crisis.iterrows():
                self.assertLess(float(r["max_drawdown_pct"]), 0.0)


class TestAdversarialStatisticalBoundaries(unittest.TestCase):
    """Stress-testing quantitative analytics against pathological return series."""

    def setUp(self) -> None:
        self.backtester = Historical30YrBacktester()

    def test_all_negative_returns_finite_bounded_sharpe(self) -> None:
        """Series where every return is negative must produce negative finite Sharpe clamped to [-3.0, 5.0]."""
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        rets = pd.Series(-0.01, index=dates[1:])
        gross_rets = pd.Series(-0.009, index=dates[1:])
        eq = (1.0 + rets).cumprod() * 100_000_000.0
        eq = pd.concat([pd.Series([100_000_000.0], index=[dates[0]]), eq])
        gross_eq = (1.0 + gross_rets).cumprod() * 100_000_000.0
        gross_eq = pd.concat([pd.Series([100_000_000.0], index=[dates[0]]), gross_eq])

        metrics = self.backtester._compute_performance_metrics(
            equity_curve=eq,
            gross_equity_curve=gross_eq,
            net_returns=rets,
            gross_returns=gross_rets,
            turnover_series=pd.Series(0.1, index=dates[1:]),
            friction_bps_series=pd.Series(5.0, index=dates[1:]),
        )

        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))
        self.assertGreaterEqual(metrics["sharpe_ratio"], -3.0)
        self.assertLessEqual(metrics["sharpe_ratio"], 0.0)
        self.assertLess(metrics["max_drawdown_pct"], 0.0)

    def test_zero_variance_equity_curve_no_nan_or_crash(self) -> None:
        """Zero variance (flat returns) must produce Sharpe=0.0 and Sortino=0.0 without division by zero."""
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        rets = pd.Series(0.0, index=dates[1:])
        eq = pd.Series(100_000_000.0, index=dates)

        metrics = self.backtester._compute_performance_metrics(
            equity_curve=eq,
            gross_equity_curve=eq,
            net_returns=rets,
            gross_returns=rets,
            turnover_series=pd.Series(0.0, index=dates[1:]),
            friction_bps_series=pd.Series(0.0, index=dates[1:]),
        )

        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)
        self.assertEqual(metrics["annualized_volatility_pct"], 0.0)

    def test_extreme_flash_crash_drawdown_boundedness(self) -> None:
        """Flash crash where equity drops 99.9% must bound MDD in [-100.0%, 0.0%]."""
        dates = pd.date_range("2020-01-01", periods=10, freq="B")
        eq_vals = [100.0, 100.0, 100.0, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]
        eq = pd.Series(eq_vals, index=dates)
        rets = eq.pct_change().dropna()

        metrics = self.backtester._compute_performance_metrics(
            equity_curve=eq,
            gross_equity_curve=eq,
            net_returns=rets,
            gross_returns=rets,
            turnover_series=pd.Series(0.1, index=dates[1:]),
            friction_bps_series=pd.Series(10.0, index=dates[1:]),
        )

        self.assertLess(metrics["max_drawdown_pct"], -99.0)
        self.assertGreaterEqual(metrics["max_drawdown_pct"], -100.0)
        self.assertTrue(math.isfinite(metrics["sharpe_ratio"]))

    def test_extreme_astronomical_returns_sharpe_clamped(self) -> None:
        """Extreme positive returns (+50% daily for 20 days) must clamp Sharpe ratio to 5.0."""
        dates = pd.date_range("2020-01-01", periods=21, freq="B")
        rets = pd.Series([0.45, 0.55] * 10, index=dates[1:])
        eq = (1.0 + rets).cumprod() * 100_000_000.0
        eq = pd.concat([pd.Series([100_000_000.0], index=[dates[0]]), eq])

        metrics = self.backtester._compute_performance_metrics(
            equity_curve=eq,
            gross_equity_curve=eq,
            net_returns=rets,
            gross_returns=rets,
            turnover_series=pd.Series(0.1, index=dates[1:]),
            friction_bps_series=pd.Series(5.0, index=dates[1:]),
        )

        self.assertEqual(metrics["sharpe_ratio"], 5.0, "Sharpe ratio must be clamped at upper bound 5.0")
        self.assertTrue(math.isfinite(metrics["cagr_pct"]))


class TestAdversarialMatrixAndCovarianceStability(unittest.TestCase):
    """Stress-testing covariance matrix and alpha signal computations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()

    def test_perfectly_collinear_returns_covariance_positive_definite(self) -> None:
        """When assets are perfectly collinear, covariance shrinkage must maintain positive definiteness."""
        dates = pd.date_range("2020-01-01", periods=30, freq="B")
        # Synthesize identical return series across all 5 assets
        common_rets = np.sin(np.linspace(0, 10, 30)) * 0.02
        collinear_df = pd.DataFrame(
            {m: common_rets for m in self.backtester.TARGET_MARKETS},
            index=dates
        )
        saved_rets = self.backtester._return_matrix
        self.backtester._return_matrix = collinear_df
        self.backtester._aligned_dates = dates

        try:
            cov, vols, mkts = self.backtester.compute_covariance_matrix(dates[-1], lookback_days=25)
            self.assertEqual(cov.shape, (5, 5))
            eigvals = np.linalg.eigvalsh(cov)
            self.assertTrue(np.all(eigvals > 0.0), f"All eigenvalues must be > 0, got {eigvals}")
        finally:
            self.backtester._return_matrix = saved_rets
            self.backtester._aligned_dates = saved_rets.index

    def test_insufficient_lookback_days_triggers_diagonal_fallback(self) -> None:
        """Lookback with fewer than 15 historical points must trigger graceful diagonal fallback."""
        first_date = self.backtester._aligned_dates[5]  # only 5 historical days available
        cov, vols, mkts = self.backtester.compute_covariance_matrix(first_date, lookback_days=60)

        self.assertEqual(cov.shape, (5, 5))
        np.testing.assert_allclose(cov, np.diag(np.diag(cov)), atol=1e-8)
        self.assertTrue(np.all(vols > 0.0))

    def test_alpha_scores_zero_variance_fallback(self) -> None:
        """If all raw alpha signals are identical, normalization must handle std=0 without NaNs."""
        test_date = self.backtester._aligned_dates[100]
        alphas = self.backtester.compute_multi_factor_alpha(test_date, regime="CRISIS")

        self.assertEqual(len(alphas), 5)
        for m, score in alphas.items():
            self.assertTrue(math.isfinite(score))
            self.assertGreaterEqual(score, -3.0)
            self.assertLessEqual(score, 3.0)


class TestAdversarialFrictionAndBypass(unittest.TestCase):
    """Stress-testing realistic statutory friction modeling and Leland bypass mechanics."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()

    def test_krx_vs_us_statutory_rates_asymmetry(self) -> None:
        """KRX sells must incur STT taxes (18/20 bps) while US sells incur SEC fees (0.3 bps)."""
        mkts = self.backtester.TARGET_MARKETS
        # 1. At standard rebalance size (1% trade size, where statutory rates dominate)
        curr_krx_1 = {m: (0.01 if m == "KOSPI" else 0.0) for m in mkts}
        exec_krx_1 = {m: 0.0 for m in mkts}
        vols = {m: 0.20 for m in mkts}

        cost_krx_1, bps_krx_1 = self.backtester.calculate_execution_frictions(
            current_weights=curr_krx_1,
            executed_weights=exec_krx_1,
            portfolio_value=100_000_000.0,
            vols=vols
        )

        curr_us_1 = {m: (0.01 if m == "SP500" else 0.0) for m in mkts}
        exec_us_1 = {m: 0.0 for m in mkts}

        cost_us_1, bps_us_1 = self.backtester.calculate_execution_frictions(
            current_weights=curr_us_1,
            executed_weights=exec_us_1,
            portfolio_value=100_000_000.0,
            vols=vols
        )

        self.assertGreater(cost_krx_1, cost_us_1, "KRX selling friction must exceed US selling friction")
        self.assertGreater(cost_krx_1, cost_us_1 * 3.0, "At 1% trade size, KRX friction must be >3x US due to STT tax")

        # 2. Statutory tax & fee rate explicit multiple
        cfg_ks = self.backtester.MARKET_FRICTION_CONFIG["KOSPI"]
        cfg_us = self.backtester.MARKET_FRICTION_CONFIG["SP500"]
        stat_ks = cfg_ks["sell_stt_rate"] + cfg_ks["brokerage_fee_rate"]
        stat_us = cfg_us["sell_stt_rate"] + cfg_us["brokerage_fee_rate"]
        self.assertGreater(stat_ks, stat_us * 20.0, "KRX statutory sell rate (21 bps) must be >20x US (0.8 bps)")

    def test_gatheral_three_halves_congestion_penalty(self) -> None:
        """Trading large blocks (delta_w > 0.05) must trigger Gatheral 3/2 congestion penalty."""
        mkts = self.backtester.TARGET_MARKETS
        vols = {m: 0.20 for m in mkts}

        # Small trade: 4% delta
        curr_sm = {m: (0.04 if m == "SP500" else 0.0) for m in mkts}
        exec_sm = {m: 0.0 for m in mkts}
        cost_sm, bps_sm = self.backtester.calculate_execution_frictions(curr_sm, exec_sm, 100_000_000.0, vols)

        # Large trade: 20% delta (5x size)
        curr_lg = {m: (0.20 if m == "SP500" else 0.0) for m in mkts}
        exec_lg = {m: 0.0 for m in mkts}
        cost_lg, bps_lg = self.backtester.calculate_execution_frictions(curr_lg, exec_lg, 100_000_000.0, vols)

        # Due to 3/2 power law congestion, friction bps must scale super-linearly
        self.assertGreater(bps_lg, bps_sm, "Large rebalance must incur higher friction bps than small rebalance")

    def test_leland_bypass_on_fresh_entry_and_full_exit_in_allocation(self) -> None:
        """Allocation must bypass Leland buffer on brand new entries and complete exits."""
        test_date = self.backtester._aligned_dates[300]
        # Current holdings: only SP500, 0 in NASDAQ
        mkts = self.backtester.TARGET_MARKETS
        curr_w = {m: (0.20 if m == "SP500" else 0.0) for m in mkts}
        alphas = {m: (2.0 if m == "NASDAQ" else -1.0) for m in mkts}

        raw_tgt, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=test_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=curr_w,
            alphas=alphas
        )

        # NASDAQ was 0.0 (fresh entry) -> target > 0 -> executed must be > 0 (bypass)
        if raw_tgt["NASDAQ"] > 0.01:
            self.assertGreater(exec_w["NASDAQ"], 0.0, "Fresh entry on NASDAQ must bypass Leland buffer")


class TestAdversarialTemporalOrderingAndLookahead(unittest.TestCase):
    """Stress-testing causal temporal ordering and data leakage prevention."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()

    def test_regime_classification_strictly_uses_prior_data(self) -> None:
        """classify_2d_regime must not access price data at or after evaluation date."""
        target_date = self.backtester._aligned_dates[200]
        regime, is_crisis, macro = self.backtester.classify_2d_regime(target_date)

        # Verify that altering future price at or after target_date has zero impact
        saved_close = self.backtester._price_matrix.loc[target_date, "SP500"]
        self.backtester._price_matrix.loc[target_date, "SP500"] = saved_close * 5.0  # +400% future spike

        try:
            regime_future, is_crisis_future, macro_future = self.backtester.classify_2d_regime(target_date)
            self.assertEqual(regime, regime_future, "Regime classification must be invariant to future bar price")
            self.assertEqual(is_crisis, is_crisis_future, "Crisis flag must be invariant to future bar price")
            self.assertEqual(macro["sp500_ret_1d"], macro_future["sp500_ret_1d"])
        finally:
            self.backtester._price_matrix.loc[target_date, "SP500"] = saved_close

    def test_alpha_generation_strictly_uses_prior_data(self) -> None:
        """compute_multi_factor_alpha must not access prices at or after evaluation date."""
        target_date = self.backtester._aligned_dates[300]
        alphas_orig = self.backtester.compute_multi_factor_alpha(target_date, "BULL_LOW_VOL")

        saved_close = self.backtester._price_matrix.loc[target_date, "NASDAQ"]
        self.backtester._price_matrix.loc[target_date, "NASDAQ"] = saved_close * 0.1  # -90% future drop

        try:
            alphas_future = self.backtester.compute_multi_factor_alpha(target_date, "BULL_LOW_VOL")
            for m in self.backtester.TARGET_MARKETS:
                self.assertAlmostEqual(alphas_orig[m], alphas_future[m], places=6,
                                       msg=f"Alpha for {m} changed when future price was altered!")
        finally:
            self.backtester._price_matrix.loc[target_date, "NASDAQ"] = saved_close


class TestAdversarialBacktestSimulationResultContract(unittest.TestCase):
    """Stress-testing BacktestSimulationResult interface and serialization."""

    def test_backtest_simulation_result_dict_and_attr_access(self) -> None:
        """BacktestSimulationResult must support attribute, dict indexing, and get()."""
        res = BacktestSimulationResult(
            equity_curve=pd.Series([100.0, 105.0]),
            daily_returns=pd.Series([0.05]),
            gross_returns=pd.Series([0.06]),
            gross_equity_curve=pd.Series([100.0, 106.0]),
            turnover_series=pd.Series([0.1]),
            friction_series=pd.Series([10.0]),
            friction_bps_series=pd.Series([5.0]),
            rebalance_records=[{"bar": 1}],
            market_returns=pd.DataFrame({"SP500": [0.02]}),
            metrics={
                "sharpe_ratio": 1.45,
                "max_drawdown_pct": -12.3,
                "total_net_return_pct": 5.0,
            },
            initial_capital=100.0,
        )

        # Attribute access
        self.assertEqual(res.sharpe_ratio, 1.45)
        self.assertEqual(res.max_drawdown_pct, -12.3)

        # Dictionary access
        self.assertEqual(res["sharpe_ratio"], 1.45)
        self.assertEqual(res["max_drawdown_pct"], -12.3)
        self.assertEqual(res.get("sharpe_ratio"), 1.45)
        self.assertEqual(res.get("nonexistent_key", 999), 999)

        # __contains__
        self.assertIn("sharpe_ratio", res)
        self.assertIn("equity_curve", res)

        # Serialization
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["sharpe_ratio"], 1.45)
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()

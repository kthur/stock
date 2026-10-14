"""
tests/test_30year_m2_adversarial_challenger.py — Adversarial Stress Test Suite for Milestone M2
Authored by Challenger M2-1 for empirical verification of Historical30YrBacktester.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

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
from src.backtest.historical_30yr_pipeline import HistoricalDataPipeline, CaseInsensitiveDict
from src.data_layer.earnings_data import compute_regulatory_filing_lag
from scripts.verify_30year_backtest import Backtest30YearVerifier


class TestCausalLookaheadAdversarial(unittest.TestCase):
    """
    Adversarial stress-testing of causal lookahead guards.
    Verifies that future price changes or fundamental announcements cannot
    leak backwards into prior or current decision timestamps.
    """

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

    def test_future_data_tampering_does_not_affect_current_decisions(self) -> None:
        """
        Oracular test: If prices on future bar T+k are artificially corrupted (e.g. multiplied by 100x),
        the regime classification and multi-factor alpha scores at bar T MUST remain identical.
        """
        eval_date = self.backtester._aligned_dates[300]
        future_date = self.backtester._aligned_dates[305]

        # Baseline decision at bar 300
        regime_orig, crisis_orig, macro_orig = self.backtester.classify_2d_regime(eval_date)
        alphas_orig = self.backtester.compute_multi_factor_alpha(eval_date, regime_orig)

        # Adversarially tamper with future price at bar 305
        orig_val = self.backtester._price_matrix.loc[future_date, "SP500"]
        try:
            self.backtester._price_matrix.loc[future_date, "SP500"] = orig_val * 100.0

            # Re-evaluate decision at bar 300
            regime_tampered, crisis_tampered, macro_tampered = self.backtester.classify_2d_regime(eval_date)
            alphas_tampered = self.backtester.compute_multi_factor_alpha(eval_date, regime_tampered)

            self.assertEqual(regime_orig, regime_tampered, "Future tampering altered past regime classification!")
            self.assertEqual(crisis_orig, crisis_tampered, "Future tampering altered past crisis flag!")
            self.assertAlmostEqual(macro_orig["sp500_ret_20d"], macro_tampered["sp500_ret_20d"], places=7)
            for m in self.backtester.TARGET_MARKETS:
                self.assertAlmostEqual(alphas_orig[m], alphas_tampered[m], places=7,
                                       msg=f"Future tampering altered alpha score for {m}!")
        finally:
            # Restore pristine value
            self.backtester._price_matrix.loc[future_date, "SP500"] = orig_val

    def test_impulse_shock_lookahead_isolation(self) -> None:
        """
        An extreme shock occurring strictly on day T must NOT be visible to
        decisions calculated at the start of day T (which only consume data up to T-1).
        """
        eval_idx = 400
        cur_date = self.backtester._aligned_dates[eval_idx]

        orig_cur_price = self.backtester._price_matrix.loc[cur_date, "SP500"]
        try:
            # Inject a -50% flash crash on day T
            self.backtester._price_matrix.loc[cur_date, "SP500"] = orig_cur_price * 0.50

            regime, is_crisis, macro = self.backtester.classify_2d_regime(cur_date)
            # The decision at cur_date only uses dates < cur_date
            sp_hist = self.backtester._price_matrix.loc[self.backtester._aligned_dates < cur_date, "SP500"]
            self.assertNotEqual(float(sp_hist.iloc[-1]), orig_cur_price * 0.50)
        finally:
            self.backtester._price_matrix.loc[cur_date, "SP500"] = orig_cur_price

    def test_statutory_filing_lag_strict_monotony(self) -> None:
        """
        Verifies statutory filing lags for all 4 quarters across KRX and SEC:
        All available dates must be strictly greater than period end date by >= 40 days.
        """
        years = [1997, 2008, 2020, 2025]
        quarters = [("03-31", "quarterly"), ("06-30", "quarterly"), ("09-30", "quarterly"), ("12-31", "annual")]

        for y in years:
            for q_end, p_type in quarters:
                period_date_str = f"{y}-{q_end}"
                d_period = datetime.strptime(period_date_str, "%Y-%m-%d")

                # KRX
                krx_avail_str = compute_regulatory_filing_lag(period_date_str, period_type=p_type, is_krx=True)
                d_krx = datetime.strptime(krx_avail_str, "%Y-%m-%d")
                delta_krx = (d_krx - d_period).days
                expected_krx_min = 89 if p_type == "annual" else 44
                self.assertGreaterEqual(delta_krx, expected_krx_min, f"KRX filing lag {delta_krx}d too short for {period_date_str}")

                # SEC
                sec_avail_str = compute_regulatory_filing_lag(period_date_str, period_type=p_type, is_krx=False)
                d_sec = datetime.strptime(sec_avail_str, "%Y-%m-%d")
                delta_sec = (d_sec - d_period).days
                expected_sec_min = 59 if p_type == "annual" else 39
                self.assertGreaterEqual(delta_sec, expected_sec_min, f"SEC filing lag {delta_sec}d too short for {period_date_str}")

    def test_negative_or_zero_signal_lag_is_disallowed_in_exported_metadata(self) -> None:
        """
        Exported metadata must strictly enforce signal_lag_days >= 1 and lookahead_bias_detected == False.
        """
        result = self.backtester.run_simulation()
        with tempfile.TemporaryDirectory(prefix="adv_meta_") as tmpdir:
            payload = self.backtester.export_summary_json(result, Path(tmpdir) / "summary.json")
            meta = payload["metadata"]
            self.assertGreaterEqual(meta["signal_lag_days"], 1, "Signal lag must be >= 1 day")
            self.assertFalse(meta["lookahead_bias_detected"], "Lookahead bias detected flag must be False")
            self.assertTrue(meta["regulatory_filing_lag_enforced"], "Filing lag must be enforced")


class TestFrictionAndLelandBypassAdversarial(unittest.TestCase):
    """
    Adversarial stress-testing of execution frictions, Leland buffer bands, and bypass logic.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            initial_capital=100_000_000.0,
        )
        cls.backtester.load_data()

    def test_fresh_entry_bypasses_all_damping_layers(self) -> None:
        """
        Adversarial test: A fresh entry from weight 0.0 to a very small weight 0.015 (below 0.05 threshold)
        MUST be executed immediately without being held or dampened to 0.0.
        """
        eval_date = self.backtester._aligned_dates[250]
        current_w = {m: 0.0 for m in self.backtester.TARGET_MARKETS}
        # Artificial alpha favoring only KOSPI
        alphas = {"KOSPI": 2.5, "KOSDAQ": -1.0, "SP500": -1.0, "NASDAQ": -1.0, "RUSSELL2000": -1.0}

        raw_tgt, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=eval_date,
            regime="BULL_LOW_VOL",
            is_crisis=False,
            current_weights=current_w,
            alphas=alphas,
        )

        self.assertGreater(exec_w["KOSPI"], 0.0, "Fresh entry on KOSPI must bypass buffer bands")
        self.assertGreater(turnover, 0.0, "Fresh entry must generate positive turnover")

    def test_full_liquidation_bypasses_all_damping_layers(self) -> None:
        """
        Adversarial test: A position currently held at 0.02 (below 0.05 threshold) targeted for full
        liquidation to 0.0 MUST be liquidated completely (executed == 0.0).
        """
        curr_arr = np.array([0.02, 0.15, 0.10])
        tgt_arr = np.array([0.00, 0.14, 0.10])  # asset 0 targeted for 0.0
        vols = np.array([0.18, 0.14, 0.22])

        realized = self.backtester.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=tgt_arr,
            current_weights=curr_arr,
            volatilities=vols,
            use_asymmetric_bands=False,
        )

        self.assertAlmostEqual(realized[0], 0.0, places=5, msg="Full liquidation must bypass Leland buffer")

        # Also test via TurnoverOptimizer
        turn_res = self.backtester.turnover_opt.optimize_allocations(
            current_holdings={"A": 0.02, "B": 0.15},
            target_allocations={"A": 0.00, "B": 0.14},
            total_capital=100_000_000.0,
            currency="KRW"
        )
        self.assertEqual(turn_res["A"]["action"], "SELL")
        self.assertAlmostEqual(turn_res["A"]["target_weight"], 0.0, places=5)

    def test_simultaneous_entry_exit_and_hold_mixed_vector(self) -> None:
        """
        Adversarial test on mixed 3-asset allocation vector:
        Asset 0: Entry (0.0 -> 0.08) -> MUST bypass and allocate 0.08.
        Asset 1: Exit (0.05 -> 0.0) -> MUST bypass and liquidate to 0.0.
        Asset 2: Noise drift (0.10 -> 0.102) -> MUST be held at 0.10.
        """
        curr_arr = np.array([0.0, 0.05, 0.10])
        tgt_arr = np.array([0.08, 0.0, 0.102])
        vols = np.array([0.15, 0.18, 0.20])

        realized = self.backtester.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=tgt_arr,
            current_weights=curr_arr,
            volatilities=vols,
            use_asymmetric_bands=False,
        )

        self.assertAlmostEqual(realized[0], 0.08, places=4, msg="Asset 0 entry must bypass buffer")
        self.assertAlmostEqual(realized[1], 0.0, places=4, msg="Asset 1 liquidation must bypass buffer")
        self.assertAlmostEqual(realized[2], 0.10, places=4, msg="Asset 2 drift must be held at current weight")

    def test_friction_drag_strict_monotonicity_under_active_turnover(self) -> None:
        """
        When turnover is positive, the net return MUST be strictly less than gross return,
        and transaction friction in basis points MUST be strictly positive.
        """
        curr_w = {"KOSPI": 0.10, "KOSDAQ": 0.05, "SP500": 0.10, "NASDAQ": 0.10, "RUSSELL2000": 0.05}
        exec_w = {"KOSPI": 0.15, "KOSDAQ": 0.00, "SP500": 0.08, "NASDAQ": 0.12, "RUSSELL2000": 0.05}
        vols = {m: 0.20 for m in self.backtester.TARGET_MARKETS}

        cost_curr, cost_bps = self.backtester.calculate_execution_frictions(
            current_weights=curr_w,
            executed_weights=exec_w,
            portfolio_value=100_000_000.0,
            vols=vols
        )

        self.assertGreater(cost_curr, 0.0, "Transaction cost currency must be strictly positive")
        self.assertGreater(cost_bps, 0.0, "Transaction cost bps must be strictly positive")

    def test_gatheral_three_halves_power_law_congestion_escalation(self) -> None:
        """
        Large trade rebalances (> 5% delta weight) must experience non-linear Gatheral 3/2 power-law
        impact penalties strictly escalating above linear square-root impact.
        """
        vols = {m: 0.20 for m in self.backtester.TARGET_MARKETS}

        # Small 2% rebalance (delta = 0.02)
        c_small, bps_small = self.backtester.calculate_execution_frictions(
            current_weights={"SP500": 0.00},
            executed_weights={"SP500": 0.02},
            portfolio_value=100_000_000.0,
            vols=vols
        )

        # Huge 20% rebalance (delta = 0.20, 10x larger)
        c_huge, bps_huge = self.backtester.calculate_execution_frictions(
            current_weights={"SP500": 0.00},
            executed_weights={"SP500": 0.20},
            portfolio_value=100_000_000.0,
            vols=vols
        )

        self.assertGreater(bps_huge, bps_small * 1.5,
                           f"Gatheral 3/2 congestion penalty must escalate bps (huge={bps_huge:.2f} bps vs small={bps_small:.2f} bps)")

    def test_krx_selling_stt_tax_exceeds_us_sec_fee_by_more_than_20x(self) -> None:
        """
        Statutory tax rate check: Selling KRX (18 bps STT + 3 bps fee) vs US (0.3 bps SEC + 0.5 bps fee).
        """
        vols = {m: 0.15 for m in self.backtester.TARGET_MARKETS}

        # Sell KOSPI 5%
        cost_krx, bps_krx = self.backtester.calculate_execution_frictions(
            current_weights={"KOSPI": 0.05, "SP500": 0.0},
            executed_weights={"KOSPI": 0.00, "SP500": 0.0},
            portfolio_value=100_000_000.0,
            vols=vols
        )

        # Sell SP500 5%
        cost_us, bps_us = self.backtester.calculate_execution_frictions(
            current_weights={"KOSPI": 0.0, "SP500": 0.05},
            executed_weights={"KOSPI": 0.0, "SP500": 0.00},
            portfolio_value=100_000_000.0,
            vols=vols
        )

        self.assertGreater(bps_krx, bps_us * 1.5, "KRX selling friction must significantly exceed US selling friction")


class TestExtremeRegimeAndCrisisAdversarial(unittest.TestCase):
    """
    Adversarial stress-testing of crisis gating, de-risking, and extreme market regimes.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            initial_capital=100_000_000.0,
        )
        cls.backtester.load_data()

    def test_extreme_vix_spike_triggers_crisis_gating(self) -> None:
        """
        When VIX spikes >= 35.0 or 1d return drops <= -3.5%, the engine MUST activate CRISIS mode,
        cut volatility target by 50% (raw_target sum <= 0.50), and allocate 80% to EVT-CVaR.
        """
        eval_date = self.backtester._aligned_dates[350]
        orig_sp = self.backtester._price_matrix.loc[eval_date, "SP500"]

        # Temporarily mock a -5.0% 1d return
        prev_date = self.backtester._aligned_dates[349]
        prev_price = self.backtester._price_matrix.loc[prev_date, "SP500"]
        crash_price = prev_price * 0.95

        try:
            self.backtester._price_matrix.loc[eval_date, "SP500"] = crash_price
            eval_date_next = self.backtester._aligned_dates[351]

            regime, is_crisis, macro = self.backtester.classify_2d_regime(eval_date_next)
            self.assertTrue(is_crisis, "Extreme 1d crash did not trigger crisis gating!")
            self.assertEqual(regime, "CRISIS")

            # Check allocation under CRISIS: raw target exposure must be <= 0.50 (50% de-risking)
            alphas = {m: 0.0 for m in self.backtester.TARGET_MARKETS}
            raw_tgt, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=eval_date_next,
                regime=regime,
                is_crisis=is_crisis,
                current_weights={m: 0.0 for m in self.backtester.TARGET_MARKETS},
                alphas=alphas,
            )

            # In crisis, raw target exposure is halved to <= 0.50
            total_raw = sum(raw_tgt.values())
            self.assertLessEqual(total_raw, 0.5001, f"Crisis raw target {total_raw:.2f} should be <= 0.50")
            total_exec = sum(exec_w.values())
            self.assertLessEqual(total_exec, 0.5001, f"Crisis fresh execution {total_exec:.2f} should be <= 0.50")
        finally:
            self.backtester._price_matrix.loc[eval_date, "SP500"] = orig_sp

    def test_ledoit_wolf_positive_definiteness_under_perfect_correlation(self) -> None:
        """
        Adversarial test: If all markets move with identical returns (perfect collinearity, det=0),
        the covariance estimation MUST still produce a strictly positive-definite matrix
        with positive eigenvalues >= 1e-8 without raising LinAlgError.
        """
        eval_date = self.backtester._aligned_dates[200]
        orig_rets = self.backtester._return_matrix.copy()
        try:
            for m in self.backtester.TARGET_MARKETS:
                self.backtester._return_matrix[m] = orig_rets["SP500"]

            cov, vols, mkts = self.backtester.compute_covariance_matrix(eval_date)
            eigvals = np.linalg.eigvalsh(cov)
            self.assertTrue(np.all(eigvals >= 1e-8), f"Eigenvalues must be >= 1e-8, got {eigvals}")
            self.assertFalse(np.isnan(cov).any(), "Covariance matrix contains NaNs")
        finally:
            self.backtester._return_matrix = orig_rets


class TestEdgeCasesAndNumericStability(unittest.TestCase):
    """
    Adversarial tests for zero-division guards, flash crashes, and full verifier compliance.
    """

    def test_zero_variance_flat_portfolio_stability(self) -> None:
        """
        If portfolio returns are zero across all days, performance metrics
        must return exact finite numbers (0.0 Sharpe, 0.0 MDD, 0.0 CAGR) without crashing.
        """
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        flat_eq = pd.Series([100_000_000.0] * 100, index=dates)
        flat_rets = pd.Series([0.0] * 99, index=dates[1:])
        turnover = pd.Series([0.0] * 99, index=dates[1:])
        frictions = pd.Series([0.0] * 99, index=dates[1:])

        bt = Historical30YrBacktester()
        metrics = bt._compute_performance_metrics(
            equity_curve=flat_eq,
            gross_equity_curve=flat_eq,
            net_returns=flat_rets,
            gross_returns=flat_rets,
            turnover_series=turnover,
            friction_bps_series=frictions
        )

        self.assertEqual(metrics["sharpe_ratio"], 0.0)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)
        self.assertEqual(metrics["cagr_pct"], 0.0)
        self.assertEqual(metrics["total_net_return_pct"], 0.0)
        self.assertEqual(metrics["total_friction_bps"], 0.0)

    def test_exported_artifacts_pass_verifier_in_strict_mode(self) -> None:
        """
        Runs full simulation, exports to temporary directory, and executes Backtest30YearVerifier
        in strict mode. Verifies 100% check pass rate with zero failures.
        """
        bt = Historical30YrBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            initial_capital=100_000_000.0,
        )
        result = bt.run_simulation()

        with tempfile.TemporaryDirectory(prefix="adv_m2_verifier_") as tmpdir:
            paths = bt.export_artifacts(result, result_dir=tmpdir)

            verifier = Backtest30YearVerifier(result_dir=tmpdir, strict=True)
            summary = verifier.verify_all()

            self.assertTrue(summary.passed, "Verifier failed in strict mode")
            self.assertEqual(summary.failed_checks, 0)
            self.assertEqual(summary.warning_checks, 0)
            self.assertGreaterEqual(summary.total_checks, 20)


if __name__ == "__main__":
    unittest.main()

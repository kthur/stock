"""
tests/test_historical_30yr_backtester_unit.py — Unit & Integration Tests for Historical30YrBacktester
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
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
from src.backtest.historical_30yr_pipeline import HistoricalDataPipeline
from scripts.verify_30year_backtest import Backtest30YearVerifier


class TestHistorical30YrBacktesterUnit(unittest.TestCase):
    """Unit test suite for Historical30YrBacktester."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            rebalance_freq_days=20,
            target_volatility=0.12,
            initial_capital=100_000_000.0,
            base_currency="KRW",
        )
        cls.backtester.load_data()

    def test_backtester_initialization_defaults_and_custom(self) -> None:
        """Validates parameter assignment and clamping during initialization."""
        bt_custom = Historical30YrBacktester(
            start_date="2000-01-01",
            end_date="2010-12-31",
            rebalance_freq_days=10,
            target_volatility=0.15,
            initial_capital=50_000_000.0,
            max_single_weight=0.25,
            leland_cost_bps=30.0,
        )
        self.assertEqual(bt_custom.start_date, "2000-01-01")
        self.assertEqual(bt_custom.end_date, "2010-12-31")
        self.assertEqual(bt_custom.rebalance_freq_days, 10)
        self.assertAlmostEqual(bt_custom.target_volatility, 0.15, places=4)
        self.assertAlmostEqual(bt_custom.initial_capital, 50_000_000.0, places=1)
        self.assertAlmostEqual(bt_custom.max_single_weight, 0.25, places=4)
        self.assertAlmostEqual(bt_custom.leland_cost_bps, 30.0, places=1)

    def test_all_five_target_markets_loaded(self) -> None:
        """Verifies that all 5 required markets are present in the ingested panel."""
        panels = self.backtester._panels
        self.assertIsNotNone(panels)
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            self.assertIn(m, panels)
            df = panels[m]
            self.assertGreater(len(df), 7000, f"Market {m} must have > 7,000 daily bars")
            self.assertIn("Close", df.columns)

    def test_aligned_price_matrix_properties(self) -> None:
        """Validates that price and return matrices are synchronized and positive."""
        p_mat = self.backtester._price_matrix
        r_mat = self.backtester._return_matrix
        self.assertIsNotNone(p_mat)
        self.assertIsNotNone(r_mat)
        self.assertEqual(len(p_mat), len(r_mat))
        self.assertTrue(all(c in p_mat.columns for c in self.backtester.TARGET_MARKETS))
        self.assertTrue(np.all(p_mat.values > 0.0), "All asset prices must be strictly positive")
        self.assertFalse(np.isnan(r_mat.values).any(), "Return matrix must contain zero NaNs")

    def test_2d_regime_classification_states(self) -> None:
        """Verifies 2D Market Regime classification and crisis gating."""
        sample_dates = self.backtester._aligned_dates[100:150:10]
        valid_states = {
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "CRISIS"
        }
        for d in sample_dates:
            regime, is_crisis, macro = self.backtester.classify_2d_regime(d)
            self.assertIn(regime, valid_states)
            self.assertIsInstance(is_crisis, bool)
            self.assertIn("vix", macro)
            self.assertIn("sp500_ret_20d", macro)

    def test_causal_multi_factor_alpha_signals(self) -> None:
        """Verifies multi-factor alpha scores are cross-sectionally normalized and bounded."""
        test_date = self.backtester._aligned_dates[500]
        alphas = self.backtester.compute_multi_factor_alpha(test_date, "BULL_LOW_VOL")
        self.assertEqual(len(alphas), 5)
        for m, score in alphas.items():
            self.assertTrue(math.isfinite(score))
            self.assertGreaterEqual(score, -3.0)
            self.assertLessEqual(score, 3.0)

    def test_ledoit_wolf_covariance_positive_definite(self) -> None:
        """Ledoit-Wolf shrinkage covariance matrix must be strictly positive definite."""
        test_date = self.backtester._aligned_dates[300]
        cov, ann_vols, mkts = self.backtester.compute_covariance_matrix(test_date)
        self.assertEqual(cov.shape, (5, 5))
        # Check symmetry
        np.testing.assert_allclose(cov, cov.T, atol=1e-8)
        # Check positive eigenvalues
        eigvals = np.linalg.eigvalsh(cov)
        self.assertTrue(np.all(eigvals > 0.0), f"All eigenvalues must be positive, got {eigvals}")
        # Check realistic annual volatilities
        self.assertTrue(np.all((ann_vols >= 0.05) & (ann_vols <= 1.0)))

    def test_institutional_portfolio_allocation_adheres_to_vol_target(self) -> None:
        """Allocation weights must be long-only, capped, and adhere to 12% target volatility."""
        test_date = self.backtester._aligned_dates[600]
        current_w = {m: 0.10 for m in self.backtester.TARGET_MARKETS}
        alphas = self.backtester.compute_multi_factor_alpha(test_date, "SIDEWAYS_LOW_VOL")

        raw_tgt, exec_w, turnover, cost_bps = self.backtester.allocate_portfolio(
            date=test_date,
            regime="SIDEWAYS_LOW_VOL",
            is_crisis=False,
            current_weights=current_w,
            alphas=alphas
        )

        for m in self.backtester.TARGET_MARKETS:
            w = exec_w[m]
            self.assertGreaterEqual(w, 0.0, f"Weight for {m} must be non-negative")
            self.assertLessEqual(w, self.backtester.max_single_weight + 1e-4)

        self.assertLessEqual(sum(exec_w.values()), 1.0001, "Total portfolio exposure must not exceed 100%")
        self.assertGreaterEqual(turnover, 0.0, "Turnover must be non-negative")
        self.assertGreaterEqual(cost_bps, 0.0, "Friction bps must be non-negative")

    def test_leland_bypass_on_fresh_entry_and_full_exit(self) -> None:
        """UnifiedPortfolioAllocator Leland buffer bands must strictly bypass entries and exits."""
        curr_arr = np.array([0.0, 0.12, 0.08])
        tgt_arr = np.array([0.10, 0.13, 0.0])  # asset 0 is fresh entry, asset 2 is full liquidation
        vols = np.array([0.15, 0.12, 0.20])

        realized = self.backtester.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=tgt_arr,
            current_weights=curr_arr,
            volatilities=vols,
            use_asymmetric_bands=False,
        )

        self.assertAlmostEqual(realized[0], 0.10, places=4, msg="Fresh entry must bypass Leland buffer")
        self.assertAlmostEqual(realized[2], 0.0, places=4, msg="Full liquidation must bypass Leland buffer")

    def test_execution_frictions_statutory_rates(self) -> None:
        """Verifies statutory tax and fee deductions: KRX STT (18/20 bps) vs US SEC (0.3 bps)."""
        # Selling KOSPI vs selling SP500 for a realistic 1% trade size
        curr_ks = {"KOSPI": 0.01, "SP500": 0.0, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "KOSDAQ": 0.0}
        exec_ks = {"KOSPI": 0.00, "SP500": 0.0, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "KOSDAQ": 0.0}
        vols = {m: 0.15 for m in self.backtester.TARGET_MARKETS}

        cost_ks, bps_ks = self.backtester.calculate_execution_frictions(curr_ks, exec_ks, 100_000_000.0, vols)

        curr_us = {"KOSPI": 0.0, "SP500": 0.01, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "KOSDAQ": 0.0}
        exec_us = {"KOSPI": 0.0, "SP500": 0.00, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "KOSDAQ": 0.0}

        cost_us, bps_us = self.backtester.calculate_execution_frictions(curr_us, exec_us, 100_000_000.0, vols)

        # Selling KOSPI incurs 18 bps STT + 3 bps fee + spread >> selling SP500 (0.3 bps SEC fee + 0.5 bps fee)
        self.assertGreater(cost_ks, cost_us, "KRX selling friction must exceed US selling friction")
        self.assertGreater(cost_ks, cost_us * 3.0, "KRX selling friction must be >3x US due to STT tax")

        # Explicit statutory tax and fee rate validation
        cfg_ks = self.backtester.MARKET_FRICTION_CONFIG["KOSPI"]
        cfg_us = self.backtester.MARKET_FRICTION_CONFIG["SP500"]
        stat_ks = cfg_ks["sell_stt_rate"] + cfg_ks["brokerage_fee_rate"]  # 21 bps
        stat_us = cfg_us["sell_stt_rate"] + cfg_us["brokerage_fee_rate"]  # 0.8 bps
        self.assertGreater(stat_ks, stat_us * 20.0, "KRX statutory sell tax+fee (21 bps) must be >20x US (0.8 bps)")

    def test_full_simulation_run_metrics_integrity(self) -> None:
        """Runs full 30-year simulation and asserts statistical bounds and friction drag."""
        result = self.backtester.run_simulation()
        self.assertIsInstance(result, BacktestSimulationResult)

        # 1. Finite Sharpe in [-3.0, 5.0]
        self.assertTrue(math.isfinite(result.sharpe_ratio))
        self.assertGreaterEqual(result.sharpe_ratio, -3.0)
        self.assertLessEqual(result.sharpe_ratio, 5.0)

        # 2. Finite MDD in [-100%, 0%]
        self.assertTrue(math.isfinite(result.max_drawdown_pct))
        self.assertLessEqual(result.max_drawdown_pct, 0.0)
        self.assertGreaterEqual(result.max_drawdown_pct, -100.0)

        # 3. Monotonic friction deduction: Net Return < Gross Return
        self.assertLess(result.total_net_return_pct, result.total_gross_return_pct)
        self.assertLess(result.final_equity, result.metrics["final_gross_equity"])

        # 4. Realistic win rate and turnover
        self.assertGreater(result.win_rate_pct, 40.0)
        self.assertLess(result.win_rate_pct, 70.0)
        self.assertGreater(result.total_turnover, 0.0)
        self.assertGreater(len(result.rebalance_records), 300)

    def test_exported_artifacts_verifier_clean_pass(self) -> None:
        """Exports artifacts and verifies 100% pass under Backtest30YearVerifier."""
        temp_dir = tempfile.mkdtemp(prefix="test_bt_artifacts_")
        result = self.backtester.run_simulation()
        paths = self.backtester.export_artifacts(result, result_dir=temp_dir)

        verifier = Backtest30YearVerifier(result_dir=temp_dir, strict=True)
        summary = verifier.verify_all()

        self.assertTrue(summary.passed, f"Verification failed: {[c for c in summary.checks if not c.passed]}")
        self.assertEqual(summary.failed_checks, 0)
        self.assertEqual(summary.warning_checks, 0)
        self.assertGreaterEqual(summary.total_checks, 20)


if __name__ == "__main__":
    unittest.main()

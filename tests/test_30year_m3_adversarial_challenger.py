"""
tests/test_30year_m3_adversarial_challenger.py — Milestone 3 Empirical Adversarial Stress Suite

Adversarially evaluates:
1. Performance metrics thresholds (CAGR >= 8.0%, Sharpe >= 0.30, MDD <= -50%, friction <= 10,185 bps).
2. Lookahead bias immunity & statutory filing lags (KRX >= 45d, SEC >= 40d, T->T+1 execution lag).
3. Simplex and cash buffer invariants across all 6/7 regimes.
4. Regime-Adaptive Risk Budget exposure limits in allocate_portfolio:
   - BEAR_HIGH_VOL (max 0.25)
   - BEAR_LOW_VOL (max 0.40)
   - SIDEWAYS_HIGH_VOL (max 0.70)
   - SIDEWAYS_LOW_VOL (max 0.85)
   - CRISIS (max 0.15)
   - BULL_LOW_VOL (max 1.00)
   - BULL_HIGH_VOL (max 1.00)
5. Execution vs Logging integrity: audits whether the simulation executed weights diverge from logged weights.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_backtester import (
    Historical30YrBacktester,
    REGIME_ADAPTIVE_RISK_BUDGET,
)


class TestMilestone3PerformanceAndStress(unittest.TestCase):
    """Verifies Milestone 3 performance requirements and lookahead guards."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.sim_res = cls.backtester.run_simulation()
        cls.metrics = cls.sim_res.metrics

    def test_cagr_meets_threshold(self) -> None:
        """Requirement: Net CAGR >= 8.00%."""
        cagr = float(self.metrics.get("cagr_pct", 0.0))
        self.assertGreaterEqual(
            cagr, 8.00,
            f"Net CAGR {cagr:.2f}% did not meet threshold >= 8.00%"
        )

    def test_sharpe_meets_threshold(self) -> None:
        """Requirement: Net Sharpe Ratio >= 0.30."""
        sharpe = float(self.metrics.get("sharpe_ratio", 0.0))
        self.assertGreaterEqual(
            sharpe, 0.30,
            f"Net Sharpe Ratio {sharpe:.2f} did not meet threshold >= 0.30"
        )

    def test_max_drawdown_within_bound(self) -> None:
        """Requirement: 30-Year MDD <= -50.0% (i.e. between -50.0% and 0.0%)."""
        mdd = float(self.metrics.get("max_drawdown_pct", -100.0))
        self.assertGreaterEqual(
            mdd, -50.0,
            f"Max Drawdown {mdd:.2f}% breached the -50.0% floor"
        )
        self.assertLessEqual(mdd, 0.0, f"Max Drawdown {mdd:.2f}% cannot be positive")

    def test_friction_drag_compressed_by_25_pct(self) -> None:
        """Requirement: Total friction drag <= 10,185 bps (>= 25% compression vs 13,579 baseline)."""
        fric = float(self.metrics.get("total_friction_bps", 99999.0))
        self.assertLessEqual(
            fric, 10185.0,
            f"Total friction drag {fric:.1f} bps exceeded 10,185 bps threshold"
        )

    def test_lookahead_guards_and_filing_lags(self) -> None:
        """Requirement: Execution lag >= 1 day, KRX lag >= 45d, SEC lag >= 40d."""
        import json
        summary_path = TRADING_SYSTEM_DIR / "result" / "backtest_30year_summary.json"
        self.assertTrue(summary_path.exists(), "Summary JSON must exist")
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        self.assertFalse(meta.get("lookahead_bias_detected", True))
        self.assertGreaterEqual(int(meta.get("signal_lag_days", 0)), 1)
        self.assertGreaterEqual(int(meta.get("krx_filing_lag_days", 0)), 45)
        self.assertGreaterEqual(int(meta.get("sec_filing_lag_days", 0)), 40)


class TestMilestone3RegimeExposureAndIntegrity(unittest.TestCase):
    """Adversarially tests allocate_portfolio and run_simulation exposure clamping."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()
        cls.test_date = cls.backtester._aligned_dates[600]
        cls.markets = cls.backtester.TARGET_MARKETS
        cls.zero_weights = {m: 0.0 for m in cls.markets}
        cls.bull_alphas = {m: 0.80 for m in cls.markets}

    def test_regime_adaptive_risk_budget_table_complete(self) -> None:
        """All 7 regimes must be mapped with valid numerical bounds."""
        expected = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS"
        ]
        for reg in expected:
            self.assertIn(reg, REGIME_ADAPTIVE_RISK_BUDGET)
            cfg = REGIME_ADAPTIVE_RISK_BUDGET[reg]
            self.assertLessEqual(cfg["min_exposure"], cfg["max_exposure"])
            self.assertLessEqual(cfg["max_exposure"], 1.00)

    def test_allocate_portfolio_respects_regime_max_exposure(self) -> None:
        """
        Adversarial test: In BEAR and CRISIS regimes, raw_target and executed weights
        MUST NOT exceed max_exposure from REGIME_ADAPTIVE_RISK_BUDGET.
        """
        test_cases = [
            ("BEAR_HIGH_VOL", False, 0.25),
            ("BEAR_LOW_VOL", False, 0.40),
            ("SIDEWAYS_HIGH_VOL", False, 0.70),
            ("SIDEWAYS_LOW_VOL", False, 0.85),
            ("CRISIS", True, 0.15),
        ]

        failures = []
        for regime, is_crisis, max_exp in test_cases:
            raw_tgt, executed, turnover, fric = self.backtester.allocate_portfolio(
                date=self.test_date,
                regime=regime,
                is_crisis=is_crisis,
                current_weights=self.zero_weights,
                alphas=self.bull_alphas,
            )
            tot_raw = sum(raw_tgt.values())
            tot_exec = sum(executed.values())

            if tot_raw > max_exp + 1e-4:
                failures.append(
                    f"[{regime}] raw_target exposure {tot_raw:.4f} > limit {max_exp:.2f}"
                )
            if tot_exec > max_exp + 1e-4:
                failures.append(
                    f"[{regime}] executed exposure {tot_exec:.4f} > limit {max_exp:.2f}"
                )

        self.assertEqual(
            len(failures), 0,
            f"Regime exposure breaches found in allocate_portfolio:\n" + "\n".join(failures)
        )

    def test_simulation_holdings_exposure_clamping_integrity(self) -> None:
        """
        Adversarial simulation audit:
        Inspects if actual executed portfolio holdings ever breach regime limits during run_simulation.
        We monkeypatch allocate_portfolio to track executed weights, comparing against logged weights.
        """
        executed_history = []
        orig_allocate = self.backtester.allocate_portfolio

        def tracking_allocate(date, regime, is_crisis, current_weights, alphas):
            raw_tgt, executed, turnover, fric = orig_allocate(
                date, regime, is_crisis, current_weights, alphas
            )
            executed_history.append((date, regime, is_crisis, dict(executed)))
            return raw_tgt, executed, turnover, fric

        self.backtester.allocate_portfolio = tracking_allocate
        try:
            sim_res = self.backtester.run_simulation()
        finally:
            self.backtester.allocate_portfolio = orig_allocate

        divergences = []
        for (d, reg, cr, exec_w), rec in zip(executed_history, sim_res.rebalance_records):
            tot_exec = sum(exec_w.values())
            tot_log = sum(rec["weights"].values())
            cfg = self.backtester.REGIME_ADAPTIVE_RISK_BUDGET.get(
                "CRISIS" if cr else reg,
                self.backtester.REGIME_ADAPTIVE_RISK_BUDGET["SIDEWAYS_LOW_VOL"]
            )
            max_limit = float(cfg["max_exposure"])

            if abs(tot_exec - tot_log) > 1e-3:
                divergences.append(
                    f"{d.strftime('%Y-%m-%d')} [{reg}] executed={tot_exec:.4f} vs logged={tot_log:.4f} (limit={max_limit:.2f})"
                )

        print(f"Total divergences between executed and logged weights: {len(divergences)}")
        for div in divergences[:5]:
            print(f"  Sample divergence: {div}")

        self.assertEqual(
            len(divergences), 0,
            f"Found {len(divergences)} rebalances where simulated executed weights diverged from logged weights!\n"
            + "\n".join(divergences[:10])
        )

    def test_rebalance_records_simulated_holdings_integrity(self) -> None:
        """
        Integrity Test: Audits whether the actual portfolio holdings simulated
        diverge from the logged weights recorded in rebalance_records.
        """
        sim_res = self.backtester.run_simulation()
        audit_breaches = []

        for rec in sim_res.rebalance_records:
            date_str = rec["date"]
            regime = rec["regime"]
            is_crisis = rec["is_crisis"]
            log_w = rec["weights"]
            tot_w = sum(log_w.values())

            cfg = self.backtester.REGIME_ADAPTIVE_RISK_BUDGET.get(
                "CRISIS" if is_crisis else regime,
                self.backtester.REGIME_ADAPTIVE_RISK_BUDGET["SIDEWAYS_LOW_VOL"]
            )
            max_limit = float(cfg["max_exposure"])

            if tot_w > max_limit + 1e-4:
                audit_breaches.append(
                    f"{date_str} [{regime}] sum(weights)={tot_w:.4f} > {max_limit:.2f}"
                )

        self.assertEqual(
            len(audit_breaches), 0,
            f"Found {len(audit_breaches)} rebalance records exceeding regime risk limits:\n"
            + "\n".join(audit_breaches[:10])
        )


if __name__ == "__main__":
    unittest.main()

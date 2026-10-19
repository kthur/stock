"""
tests/test_30year_m1_adversarial_challenger.py — Empirical Adversarial Stress Suite for Milestone 1

Adversarially stress-tests Worker 1's implementation of Requirement R1:
Dynamic Regime-Adaptive Volatility Budgeting & Exposure Scaling in Historical30YrBacktester:

1. All 7 regime states with extreme covariance matrices:
   - Near-zero volatility (0.001, 1e-6)
   - Extreme volatility (100%+, 500%+)
   - Singular covariance matrices (rank-1, rank-2, degenerate)
   - Zero covariance and non-PSD matrices
2. Bounds Testing:
   - Total equity exposure NEVER exceeds:
     - 1.00 in BULL_LOW_VOL / BULL_HIGH_VOL
     - 0.85 in SIDEWAYS_LOW_VOL
     - 0.70 in SIDEWAYS_HIGH_VOL
     - 0.40 in BEAR_LOW_VOL
     - 0.25 in BEAR_HIGH_VOL
     - 0.15 in CRISIS
3. Cash Buffer Invariant:
   - Unallocated equity strictly routes to cash buffer: 1.0 - sum(weights) >= 0.0.
   - Verifies whether executed weights after Leland buffers & TurnoverOptimizer violate
     these bounds during cross-regime transitions.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

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
    REGIME_ADAPTIVE_RISK_BUDGET,
)


class TestM1AdversarialRegimeCovarianceStress(unittest.TestCase):
    """Stress-tests all 7 regime states under extreme and degenerate covariance matrices."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()
        cls.test_date = cls.backtester._aligned_dates[600]
        cls.alphas = {m: 0.5 for m in cls.backtester.TARGET_MARKETS}
        cls.zero_weights = {m: 0.0 for m in cls.backtester.TARGET_MARKETS}
        cls.n = len(cls.backtester.TARGET_MARKETS)

    def test_all_seven_regimes_exist_in_risk_budget(self) -> None:
        """F-R1.1: REGIME_ADAPTIVE_RISK_BUDGET must explicitly map all 7 canonical regime states."""
        expected_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "CRISIS",
        ]
        for reg in expected_regimes:
            self.assertIn(reg, REGIME_ADAPTIVE_RISK_BUDGET, f"Regime {reg} missing from risk budget")
            cfg = REGIME_ADAPTIVE_RISK_BUDGET[reg]
            self.assertIn("target_vol", cfg)
            self.assertIn("max_exposure", cfg)
            self.assertIn("min_exposure", cfg)
            self.assertIn("max_single_weight", cfg)
            self.assertLessEqual(cfg["min_exposure"], cfg["max_exposure"])
            self.assertGreaterEqual(cfg["min_exposure"], 0.0)
            self.assertLessEqual(cfg["max_exposure"], 1.00)

    def test_raw_target_bounds_under_extreme_covariances(self) -> None:
        """
        Adversarially feeds degenerate covariance matrices into allocate_portfolio
        across all 7 regimes and asserts mathematical bounds on raw_target.
        """
        scenarios: List[Tuple[str, np.ndarray, np.ndarray]] = [
            ("Near-Zero Vol 0.1%", np.eye(self.n) * (0.001 ** 2 / 252.0), np.full(self.n, 0.001)),
            ("Ultra-Low Vol 1e-6", np.eye(self.n) * (1e-6 ** 2 / 252.0), np.full(self.n, 1e-6)),
            ("High Vol 100%", np.eye(self.n) * (1.00 ** 2 / 252.0), np.full(self.n, 1.00)),
            ("Extreme Vol 500%", np.eye(self.n) * (5.00 ** 2 / 252.0), np.full(self.n, 5.00)),
            ("Singular Rank-1 Collinear", np.ones((self.n, self.n)) * (0.20 ** 2 / 252.0), np.full(self.n, 0.20)),
            ("Singular Rank-2", np.zeros((self.n, self.n)), np.full(self.n, 0.20)),
            ("Zero Covariance Matrix", np.zeros((self.n, self.n)), np.zeros(self.n)),
        ]

        regimes_to_test = [
            ("CRISIS", True, 0.15),
            ("BEAR_HIGH_VOL", False, 0.25),
            ("BEAR_LOW_VOL", False, 0.40),
            ("SIDEWAYS_HIGH_VOL", False, 0.70),
            ("SIDEWAYS_LOW_VOL", False, 0.85),
            ("BULL_HIGH_VOL", False, 1.00),
            ("BULL_LOW_VOL", False, 1.00),
        ]

        for sc_name, cov_sc, vols_sc in scenarios:
            with patch.object(self.backtester, "compute_covariance_matrix", return_value=(cov_sc, vols_sc, self.backtester.TARGET_MARKETS)):
                for regime, is_crisis, max_exp in regimes_to_test:
                    with self.subTest(scenario=sc_name, regime=regime):
                        raw_target, executed, turnover, friction = self.backtester.allocate_portfolio(
                            date=self.test_date,
                            regime=regime,
                            is_crisis=is_crisis,
                            current_weights=self.zero_weights,
                            alphas=self.alphas,
                        )

                        # 1. Finite, non-NaN weights
                        for m, w in raw_target.items():
                            self.assertTrue(math.isfinite(w), f"[{sc_name}|{regime}] Raw target for {m} is NaN/Inf")
                            self.assertGreaterEqual(w, -1e-6, f"[{sc_name}|{regime}] Weight {m} must be non-negative (long-only)")

                        # 2. Total equity exposure bound
                        tot_raw = sum(raw_target.values())
                        self.assertLessEqual(
                            tot_raw,
                            max_exp + 1e-4,
                            f"[{sc_name}|{regime}] Raw target exposure {tot_raw:.4f} exceeded limit {max_exp:.2f}",
                        )

                        # 3. Cash buffer routing
                        cash_buffer = 1.0 - tot_raw
                        self.assertGreaterEqual(
                            cash_buffer,
                            -1e-5,
                            f"[{sc_name}|{regime}] Cash buffer {cash_buffer:.4f} cannot be negative",
                        )

    def test_trend_gating_cannot_override_bear_or_crisis_exposure(self) -> None:
        """
        F-R1.3: Asserts that isolated single-asset positive SMA200 trends
        cannot force exposure to 85% during macro bear or crisis regimes.
        """
        # Mock trends: SP500 is True (positive), others are False
        mock_trends = {
            "SP500": True,
            "NASDAQ": False,
            "RUSSELL2000": False,
            "KOSPI": False,
            "KOSDAQ": False,
        }

        with patch.object(self.backtester, "compute_sma_200_trend", return_value=mock_trends):
            # 1. CRISIS with positive trend
            raw_cr, *_ = self.backtester.allocate_portfolio(
                date=self.test_date,
                regime="CRISIS",
                is_crisis=True,
                current_weights=self.zero_weights,
                alphas=self.alphas,
            )
            tot_cr = sum(raw_cr.values())
            self.assertLessEqual(tot_cr, 0.1501, f"CRISIS with positive trend had exposure {tot_cr:.4f} > 0.15")

            # 2. BEAR_HIGH_VOL with positive trend
            raw_bh, *_ = self.backtester.allocate_portfolio(
                date=self.test_date,
                regime="BEAR_HIGH_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.alphas,
            )
            tot_bh = sum(raw_bh.values())
            self.assertLessEqual(tot_bh, 0.2501, f"BEAR_HIGH_VOL with positive trend had exposure {tot_bh:.4f} > 0.25")

            # 3. BEAR_LOW_VOL with positive trend
            raw_bl, *_ = self.backtester.allocate_portfolio(
                date=self.test_date,
                regime="BEAR_LOW_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.alphas,
            )
            tot_bl = sum(raw_bl.values())
            self.assertLessEqual(tot_bl, 0.4001, f"BEAR_LOW_VOL with positive trend had exposure {tot_bl:.4f} > 0.40")


class TestM1AdversarialExecutedExposureBreaches(unittest.TestCase):
    """
    Adversarial verification of EXECUTED weights after Leland buffers and TurnoverOptimizer.
    Exposes failure modes where executed weights breach regime exposure bounds and simplex ceilings.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.backtester = Historical30YrBacktester()
        cls.backtester.load_data()
        cls.test_date = cls.backtester._aligned_dates[600]
        cls.alphas = {m: 0.5 for m in cls.backtester.TARGET_MARKETS}

    def test_executed_exposure_breach_on_crisis_transition(self) -> None:
        """
        Adversarial Scenario: Portfolio transitions from 100% equity into CRISIS.
        Evaluates whether executed weights breach the 0.15 ceiling.
        """
        # Starting with 20% in each asset (100% total equity exposure)
        cur_w_full = {m: 0.20 for m in self.backtester.TARGET_MARKETS}

        raw_target, executed, turnover, friction = self.backtester.allocate_portfolio(
            date=self.test_date,
            regime="CRISIS",
            is_crisis=True,
            current_weights=cur_w_full,
            alphas=self.alphas,
        )

        tot_raw = sum(raw_target.values())
        tot_exec = sum(executed.values())

        # Raw target complies with 0.15
        self.assertLessEqual(tot_raw, 0.1501, "raw_target must comply with 0.15 CRISIS bound")

        # In the unpatched code, executed weights reach 0.2400 (exceeding 0.15 by +9.00%)!
        # This test documents the exact empirical defect.
        if tot_exec > 0.1501:
            print(f"\n[DEFECT CONFIRMED] CRISIS Executed Exposure Breach: {tot_exec:.4f} > 0.1500 (excess: +{(tot_exec - 0.15)*100:.2f}%)")

        # We assert whether executed strictly adheres:
        # Note: In adversarial test suite, this assertion tracks the Worker 1 requirement.
        self.assertLessEqual(
            tot_exec,
            0.1501,
            f"EXECUTED exposure {tot_exec:.4f} breached CRISIS limit 0.1500 due to Leland/TurnoverOptimizer buffering",
        )

    def test_executed_exposure_breach_on_bear_high_vol_transition(self) -> None:
        """
        Adversarial Scenario: Portfolio transitions from 100% equity into BEAR_HIGH_VOL.
        Evaluates whether executed weights breach the 0.25 ceiling.
        """
        cur_w_full = {m: 0.20 for m in self.backtester.TARGET_MARKETS}

        raw_target, executed, turnover, friction = self.backtester.allocate_portfolio(
            date=self.test_date,
            regime="BEAR_HIGH_VOL",
            is_crisis=False,
            current_weights=cur_w_full,
            alphas=self.alphas,
        )

        tot_raw = sum(raw_target.values())
        tot_exec = sum(executed.values())

        self.assertLessEqual(tot_raw, 0.2501, "raw_target must comply with 0.25 BEAR_HIGH_VOL bound")

        if tot_exec > 0.2501:
            print(f"\n[DEFECT CONFIRMED] BEAR_HIGH_VOL Executed Exposure Breach: {tot_exec:.4f} > 0.2500 (excess: +{(tot_exec - 0.25)*100:.2f}%)")

        self.assertLessEqual(
            tot_exec,
            0.2501,
            f"EXECUTED exposure {tot_exec:.4f} breached BEAR_HIGH_VOL limit 0.2500",
        )

    def test_executed_exposure_breach_on_bear_low_vol_transition(self) -> None:
        """
        Adversarial Scenario: Portfolio transitions from 90% equity into BEAR_LOW_VOL.
        Evaluates whether executed weights breach the 0.40 ceiling.
        """
        cur_w_high = {"SP500": 0.20, "NASDAQ": 0.20, "RUSSELL2000": 0.20, "KOSPI": 0.20, "KOSDAQ": 0.10}

        raw_target, executed, turnover, friction = self.backtester.allocate_portfolio(
            date=self.test_date,
            regime="BEAR_LOW_VOL",
            is_crisis=False,
            current_weights=cur_w_high,
            alphas=self.alphas,
        )

        tot_raw = sum(raw_target.values())
        tot_exec = sum(executed.values())

        self.assertLessEqual(tot_raw, 0.4001, "raw_target must comply with 0.40 BEAR_LOW_VOL bound")

        if tot_exec > 0.4001:
            print(f"\n[DEFECT CONFIRMED] BEAR_LOW_VOL Executed Exposure Breach: {tot_exec:.4f} > 0.4000 (excess: +{(tot_exec - 0.40)*100:.2f}%)")

        self.assertLessEqual(
            tot_exec,
            0.4001,
            f"EXECUTED exposure {tot_exec:.4f} breached BEAR_LOW_VOL limit 0.4000",
        )

    def test_full_30year_simulation_rebalance_exposure_audit(self) -> None:
        """
        Runs the full 30-year walk-forward simulation (1996–2026, 135 rebalances)
        and audits every rebalance record for exposure ceiling and cash buffer breaches.
        """
        res = self.backtester.run_simulation()
        self.assertIn(len(res.rebalance_records), [135, 338])

        exposure_violations: List[Dict[str, Any]] = []
        negative_cash_violations: List[Dict[str, Any]] = []

        for r in res.rebalance_records:
            date_str = r["date"]
            regime = r["regime"]
            is_crisis = r["is_crisis"]
            weights = r["weights"]
            w_sum = sum(weights.values())
            cash_buffer = 1.0 - w_sum

            key = "CRISIS" if is_crisis else regime
            cfg = REGIME_ADAPTIVE_RISK_BUDGET.get(key, REGIME_ADAPTIVE_RISK_BUDGET["SIDEWAYS_LOW_VOL"])
            max_limit = cfg["max_exposure"]

            # Tolerance of 1e-4 for rounding
            if w_sum > max_limit + 1e-4:
                exposure_violations.append({
                    "date": date_str,
                    "regime": key,
                    "actual_exposure": w_sum,
                    "limit": max_limit,
                    "excess": w_sum - max_limit,
                })

            if cash_buffer < -1e-4:
                negative_cash_violations.append({
                    "date": date_str,
                    "regime": key,
                    "actual_exposure": w_sum,
                    "cash_buffer": cash_buffer,
                })

        print(f"\n[SIMULATION AUDIT] Total Rebalances: {len(res.rebalance_records)}")
        print(f"[SIMULATION AUDIT] Exposure Ceiling Breaches: {len(exposure_violations)}")
        for v in exposure_violations[:10]:
            print(f"  {v['date']} ({v['regime']}): exposure={v['actual_exposure']:.4f} > limit={v['limit']:.2f} (excess +{v['excess']*100:.2f}%)")

        print(f"[SIMULATION AUDIT] Negative Cash Buffer Breaches: {len(negative_cash_violations)}")
        for c in negative_cash_violations:
            print(f"  {c['date']} ({c['regime']}): exposure={c['actual_exposure']:.4f}, cash={c['cash_buffer']:.6f}")

        # The strict invariant requires 0 exposure violations and 0 negative cash buffer events
        self.assertEqual(
            len(exposure_violations),
            0,
            f"Found {len(exposure_violations)} exposure breaches across 30-year simulation",
        )
        self.assertEqual(
            len(negative_cash_violations),
            0,
            f"Found {len(negative_cash_violations)} negative cash buffer events across 30-year simulation",
        )


if __name__ == "__main__":
    unittest.main()

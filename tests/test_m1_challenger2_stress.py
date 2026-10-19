"""
tests/test_m1_challenger2_stress.py — Adversarial Stress Test Suite for Milestone 1
EMPIRICAL CHALLENGER 2: Stress-testing the decoupling of has_positive_trend from bear market regimes
and verifying strict adherence to dynamic regime-adaptive volatility budgeting and exposure scaling.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import numpy as np
import pandas as pd

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_backtester import Historical30YrBacktester


class TestM1Challenger2Stress(unittest.TestCase):
    """
    Adversarial stress tests challenging Worker 1's implementation of:
    - Feature F-R1.1: REGIME_ADAPTIVE_RISK_BUDGET mapping
    - Feature F-R1.2: Dynamic volatility budget scalar & exposure clamping
    - Feature F-R1.3: Decoupled trend gating preventing single-asset SMA200
      false rallies from breaching bear/crisis market capital protection.
    """

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
        cls.sample_date = cls.backtester._aligned_dates[600]
        cls.markets = cls.backtester.TARGET_MARKETS
        cls.neutral_alphas = {m: 0.20 for m in cls.markets}
        cls.zero_weights = {m: 0.0 for m in cls.markets}

    # =========================================================================
    # 1. Adversarial Challenge: Single Market Outlier in BEAR_HIGH_VOL
    # =========================================================================

    def test_bear_high_vol_single_market_synthetic_trend_decoupling(self) -> None:
        """
        Adversarial test: In BEAR_HIGH_VOL, simulate each market individually having
        a positive SMA200 trend while the other 4 are below SMA200.
        MUST NOT allocate 85% equity (the old bug).
        MUST strictly respect BEAR_HIGH_VOL ceiling (<= 25% total, <= 20% single asset).
        """
        regime = "BEAR_HIGH_VOL"
        is_crisis = False
        budget = self.backtester.REGIME_ADAPTIVE_RISK_BUDGET[regime]
        max_exp = budget["max_exposure"]  # 0.25
        max_single = budget["max_single_weight"]  # 0.20

        for solo_market in self.markets:
            synthetic_trends = {m: (m == solo_market) for m in self.markets}
            self.assertTrue(any(synthetic_trends.values()), "has_positive_trend must be True")

            with patch.object(self.backtester, "compute_sma_200_trend", return_value=synthetic_trends):
                raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                    date=self.sample_date,
                    regime=regime,
                    is_crisis=is_crisis,
                    current_weights=self.zero_weights,
                    alphas=self.neutral_alphas,
                )

                total_raw_exp = sum(raw_target.values())
                total_exec_exp = sum(executed.values())

                # 1. Anti-Bug Assertion: MUST NOT allocate 85% equity exposure
                self.assertNotAlmostEqual(
                    total_raw_exp, 0.85, places=2,
                    msg=f"Old bug triggered! Total exposure was 85% with {solo_market} solo trend in {regime}"
                )
                self.assertLess(
                    total_raw_exp, 0.50,
                    msg=f"Total exposure {total_raw_exp:.4f} dangerously exceeds bear threshold for {solo_market}"
                )

                # 2. Strict Budget Assertion: Total equity <= 25.0%
                self.assertLessEqual(
                    total_raw_exp, max_exp + 1e-6,
                    msg=f"Total raw target {total_raw_exp:.4f} exceeded BEAR_HIGH_VOL max_exp {max_exp} for {solo_market}"
                )

                # 3. Single Asset Cap: Solo trending asset <= 20.0%
                self.assertLessEqual(
                    raw_target[solo_market], max_single + 1e-6,
                    msg=f"Solo market {solo_market} weight {raw_target[solo_market]:.4f} exceeded max_single {max_single}"
                )

                # 4. Gated Assets: Non-trending assets must receive strictly 0.0%
                for m in self.markets:
                    if m != solo_market:
                        self.assertEqual(
                            raw_target[m], 0.0,
                            msg=f"Market {m} was below SMA200 but received non-zero weight {raw_target[m]}"
                        )

                # 5. Executed weights respect bear boundaries from cash
                self.assertLessEqual(
                    total_exec_exp, max_exp + 1e-6,
                    msg=f"Total executed exposure {total_exec_exp:.4f} exceeded bear budget"
                )

    # =========================================================================
    # 2. Adversarial Challenge: Single Market Outlier in CRISIS
    # =========================================================================

    def test_crisis_single_market_synthetic_trend_decoupling(self) -> None:
        """
        Adversarial test: In CRISIS (e.g. Lehman, COVID), simulate 1 market having a
        synthetic positive SMA200 trend.
        MUST NOT allocate 85% equity (the old bug).
        MUST strictly respect CRISIS ceiling (<= 15% total equity, >= 85% cash buffer).
        """
        regime = "CRISIS"
        is_crisis = True
        budget = self.backtester.REGIME_ADAPTIVE_RISK_BUDGET["CRISIS"]
        max_exp = budget["max_exposure"]  # 0.15
        max_single = budget["max_single_weight"]  # 0.15

        for solo_market in self.markets:
            synthetic_trends = {m: (m == solo_market) for m in self.markets}

            with patch.object(self.backtester, "compute_sma_200_trend", return_value=synthetic_trends):
                raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                    date=self.sample_date,
                    regime=regime,
                    is_crisis=is_crisis,
                    current_weights=self.zero_weights,
                    alphas=self.neutral_alphas,
                )

                total_raw_exp = sum(raw_target.values())

                # Anti-Bug Assertion
                self.assertNotAlmostEqual(
                    total_raw_exp, 0.85, places=2,
                    msg=f"Old bug triggered! Total exposure was 85% during CRISIS with {solo_market} solo trend"
                )

                # Strict CRISIS cap (<= 15%)
                self.assertLessEqual(
                    total_raw_exp, max_exp + 1e-6,
                    msg=f"CRISIS exposure {total_raw_exp:.4f} exceeded 15% budget for solo {solo_market}"
                )

                # Single asset cap (<= 15%)
                self.assertLessEqual(
                    raw_target[solo_market], max_single + 1e-6,
                    msg=f"Solo asset {solo_market} weight {raw_target[solo_market]:.4f} exceeded CRISIS max single {max_single}"
                )

                # Cash buffer preservation (>= 85%)
                cash_buffer = 1.0 - total_raw_exp
                self.assertGreaterEqual(
                    cash_buffer, 0.85 - 1e-6,
                    msg=f"Cash buffer {cash_buffer:.4f} dropped below 85% during CRISIS"
                )

    # =========================================================================
    # 3. Adversarial Challenge: Single Market Outlier in BEAR_LOW_VOL
    # =========================================================================

    def test_bear_low_vol_single_market_synthetic_trend_decoupling(self) -> None:
        """
        Adversarial test: In BEAR_LOW_VOL, 1 market has positive SMA200 trend.
        MUST NOT allocate 85% equity (the old bug).
        MUST strictly respect BEAR_LOW_VOL ceiling (<= 40% total, <= 25% single asset).
        """
        regime = "BEAR_LOW_VOL"
        is_crisis = False
        budget = self.backtester.REGIME_ADAPTIVE_RISK_BUDGET[regime]
        max_exp = budget["max_exposure"]  # 0.40
        max_single = budget["max_single_weight"]  # 0.25

        for solo_market in self.markets:
            synthetic_trends = {m: (m == solo_market) for m in self.markets}

            with patch.object(self.backtester, "compute_sma_200_trend", return_value=synthetic_trends):
                raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                    date=self.sample_date,
                    regime=regime,
                    is_crisis=is_crisis,
                    current_weights=self.zero_weights,
                    alphas=self.neutral_alphas,
                )

                total_raw_exp = sum(raw_target.values())

                self.assertNotAlmostEqual(total_raw_exp, 0.85, places=2)
                self.assertLessEqual(total_raw_exp, max_exp + 1e-6)
                self.assertLessEqual(raw_target[solo_market], max_single + 1e-6)
                self.assertGreaterEqual(1.0 - total_raw_exp, 0.60 - 1e-6)

    # =========================================================================
    # 4. Multi-Market Counter-Trend Rallies in Bear & Crisis Regimes
    # =========================================================================

    def test_multi_market_trend_rallies_in_bear_and_crisis_strictly_capped(self) -> None:
        """
        Adversarial test: Multiple markets (2, 3, or all 5) experience counter-trend
        bear rallies above SMA200 during BEAR_HIGH_VOL and CRISIS regimes.
        The system must NEVER allow multi-asset trend confluence to violate the bear risk budget.
        """
        scenarios = [
            # 2 markets positive
            {"SP500": True, "NASDAQ": True, "RUSSELL2000": False, "KOSPI": False, "KOSDAQ": False},
            # 3 markets positive
            {"SP500": True, "NASDAQ": True, "RUSSELL2000": True, "KOSPI": False, "KOSDAQ": False},
            # All 5 markets positive (extreme bear divergence rally)
            {m: True for m in self.markets},
        ]

        # Test under BEAR_HIGH_VOL
        for trend_case in scenarios:
            with patch.object(self.backtester, "compute_sma_200_trend", return_value=trend_case):
                raw_target, _, _, _ = self.backtester.allocate_portfolio(
                    date=self.sample_date,
                    regime="BEAR_HIGH_VOL",
                    is_crisis=False,
                    current_weights=self.zero_weights,
                    alphas=self.neutral_alphas,
                )
                total_exp = sum(raw_target.values())
                self.assertLessEqual(
                    total_exp, 0.250001,
                    msg=f"BEAR_HIGH_VOL exposure {total_exp:.4f} exceeded 25% under trend {trend_case}"
                )
                for m, w in raw_target.items():
                    self.assertLessEqual(w, 0.200001, f"Asset {m} exceeded max_single 20% in BEAR_HIGH_VOL")

        # Test under CRISIS
        for trend_case in scenarios:
            with patch.object(self.backtester, "compute_sma_200_trend", return_value=trend_case):
                raw_target, _, _, _ = self.backtester.allocate_portfolio(
                    date=self.sample_date,
                    regime="CRISIS",
                    is_crisis=True,
                    current_weights=self.zero_weights,
                    alphas=self.neutral_alphas,
                )
                total_exp = sum(raw_target.values())
                self.assertLessEqual(
                    total_exp, 0.150001,
                    msg=f"CRISIS exposure {total_exp:.4f} exceeded 15% under trend {trend_case}"
                )
                for m, w in raw_target.items():
                    self.assertLessEqual(w, 0.150001, f"Asset {m} exceeded max_single 15% in CRISIS")

    # =========================================================================
    # 5. Confirmed Bull Regimes: Exposure Expansion to 100%
    # =========================================================================

    def test_confirmed_bull_regimes_expand_toward_100_percent(self) -> None:
        """
        Verifies that in confirmed bull regimes (BULL_LOW_VOL, BULL_HIGH_VOL) with
        positive SMA200 trends:
        - Target volatility expands to 18-22%.
        - When vol_budget_scalar >= 0.85, enable_bull_drag_elim sets vol_scalar = 1.00.
        - Equity exposure approaches or reaches 100%, eliminating cash drag.
        """
        all_bull_trends = {m: True for m in self.markets}

        # 1. BULL_LOW_VOL
        with patch.object(self.backtester, "compute_sma_200_trend", return_value=all_bull_trends):
            raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BULL_LOW_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_raw = sum(raw_target.values())

            # Exposure must expand toward 100% (at least >= min_exposure 0.90)
            self.assertGreaterEqual(
                total_raw, 0.90 - 1e-4,
                msg=f"BULL_LOW_VOL exposure {total_raw:.4f} failed to expand to min_exposure 90%"
            )
            # With typical historical covariance, vol_budget_scalar is high enough to trigger 100%
            self.assertAlmostEqual(
                total_raw, 1.00, places=2,
                msg=f"BULL_LOW_VOL exposure {total_raw:.4f} expected 1.00 (full compounding)"
            )

        # 2. BULL_HIGH_VOL
        with patch.object(self.backtester, "compute_sma_200_trend", return_value=all_bull_trends):
            raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BULL_HIGH_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_raw = sum(raw_target.values())
            self.assertGreaterEqual(
                total_raw, 0.85 - 1e-4,
                msg=f"BULL_HIGH_VOL exposure {total_raw:.4f} failed to reach min_exposure 85%"
            )
            self.assertAlmostEqual(
                total_raw, 1.00, places=2,
                msg=f"BULL_HIGH_VOL exposure {total_raw:.4f} expected 1.00 (full compounding)"
            )

    # =========================================================================
    # 6. Unconfirmed Bull Regime (All Markets Below SMA200)
    # =========================================================================

    def test_unconfirmed_bull_regime_all_markets_below_sma200(self) -> None:
        """
        Adversarial test: Bull regime signal reported by macro detector, but ALL 5
        markets are technically below their SMA200 (false bull / lag).
        The trend gating must cut raw targets to 0.0%, routing 100% to cash buffer
        without throwing division by zero or NaN errors.
        """
        all_false_trends = {m: False for m in self.markets}

        with patch.object(self.backtester, "compute_sma_200_trend", return_value=all_false_trends):
            raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BULL_LOW_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_raw = sum(raw_target.values())

            self.assertEqual(
                total_raw, 0.0,
                msg=f"Expected 0.0 total equity when all markets below SMA200, got {total_raw}"
            )
            for m in self.markets:
                self.assertEqual(raw_target[m], 0.0)
                self.assertFalse(math.isnan(raw_target[m]))

    # =========================================================================
    # 7. Adversarial Covariance Scenarios: Extreme Volatility Spikes and Collapses
    # =========================================================================

    def test_adversarial_covariance_extreme_vol_budget_clamping(self) -> None:
        """
        Adversarial test: Construct synthetic covariance matrices with extreme values.
        Case A: Realized portfolio volatility collapses to near 0 (port_vol = 0.001).
                vol_budget_scalar explodes to 60.0.
                In BEAR_HIGH_VOL and CRISIS, max_exp MUST strictly clamp exposure.
        Case B: Realized portfolio volatility explodes to 200% (port_vol = 2.00).
                vol_budget_scalar drops to 0.03.
                In BEAR_HIGH_VOL and BULL_LOW_VOL, min_exp MUST enforce proper floor.
        """
        # Case A: Near-zero covariance (high scalar)
        tiny_cov = np.eye(5) * (0.001 ** 2 / 252.0)
        tiny_vols = np.array([0.001] * 5)

        with patch.object(self.backtester, "compute_covariance_matrix", return_value=(tiny_cov, tiny_vols, self.markets)):
            # CRISIS under tiny realized vol
            raw_cr, _, _, _ = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="CRISIS",
                is_crisis=True,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_cr = sum(raw_cr.values())
            self.assertLessEqual(
                total_cr, 0.150001,
                msg=f"Exploding vol scalar breached CRISIS 15% cap: got {total_cr:.4f}"
            )

            # BEAR_HIGH_VOL under tiny realized vol
            raw_bear, _, _, _ = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BEAR_HIGH_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_bear = sum(raw_bear.values())
            self.assertLessEqual(
                total_bear, 0.250001,
                msg=f"Exploding vol scalar breached BEAR_HIGH_VOL 25% cap: got {total_bear:.4f}"
            )

        # Case B: Huge covariance (200% annual vol)
        huge_cov = np.eye(5) * (2.00 ** 2 / 252.0)
        huge_vols = np.array([2.00] * 5)

        with patch.object(self.backtester, "compute_covariance_matrix", return_value=(huge_cov, huge_vols, self.markets)):
            # BEAR_HIGH_VOL under huge realized vol
            raw_bear_h, _, _, _ = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BEAR_HIGH_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_bear_h = sum(raw_bear_h.values())
            self.assertGreaterEqual(
                total_bear_h, 0.05 - 1e-4,
                msg=f"BEAR_HIGH_VOL dropped below min_exposure 5%: got {total_bear_h:.4f}"
            )

            # BULL_LOW_VOL under huge realized vol (floored at min_exposure 90%, subject to max_single_weight 45%)
            raw_bull_h, _, _, _ = self.backtester.allocate_portfolio(
                date=self.sample_date,
                regime="BULL_LOW_VOL",
                is_crisis=False,
                current_weights=self.zero_weights,
                alphas=self.neutral_alphas,
            )
            total_bull_h = sum(raw_bull_h.values())
            # In extreme 200% vol, vol_scalar is floored at 0.90; individual asset capping at max_single_w=0.45
            # caps the highest-weighted asset, yielding ~0.893 total exposure.
            self.assertGreaterEqual(
                total_bull_h, 0.88,
                msg=f"BULL_LOW_VOL dropped below expected floor (accounting for max_single_w): got {total_bull_h:.4f}"
            )
            self.assertLessEqual(
                total_bull_h, 1.00,
                msg=f"BULL_LOW_VOL exceeded 100%: got {total_bull_h:.4f}"
            )

    # =========================================================================
    # 8. Empirical Verification on Actual 30-Year Historical Crisis Windows
    # =========================================================================

    def test_empirical_historical_crisis_windows_adherence(self) -> None:
        """
        Empirical replay across real historical crisis dates in the 30-year panel:
        - 2000 Dot-com Crash (2000-10 to 2002-10)
        - 2008 Lehman GFC (2008-09 to 2008-11)
        - 2011 US Debt Downgrade (2011-08)
        - 2020 COVID Crash (2020-03)
        Validates that on every crisis day, total equity exposure strictly obeys
        the regime's ceiling and NEVER allocates 85%.
        """
        crisis_test_dates = [
            "2000-10-16",
            "2001-03-22",
            "2002-07-24",
            "2008-09-15",
            "2008-10-10",
            "2008-11-20",
            "2011-08-08",
            "2020-03-09",
            "2020-03-16",
            "2020-03-23",
        ]

        # Convert to aligned date format
        aligned_set = set(self.backtester._aligned_dates)

        tested_count = 0
        for d_str in crisis_test_dates:
            target_ts = pd.Timestamp(d_str)
            # Find closest available aligned date
            matching = [d for d in self.backtester._aligned_dates if abs((pd.Timestamp(d) - target_ts).days) <= 3]
            if not matching:
                continue

            test_date = matching[0]
            regime, is_crisis, macro = self.backtester.classify_2d_regime(test_date)
            alphas = self.backtester.compute_multi_factor_alpha(test_date, regime)

            raw_target, executed, turnover, cost_bps = self.backtester.allocate_portfolio(
                date=test_date,
                regime=regime,
                is_crisis=is_crisis,
                current_weights=self.zero_weights,
                alphas=alphas,
            )

            total_exp = sum(raw_target.values())
            tested_count += 1

            # Assert anti-bug: NEVER 85% in bear or crisis
            if is_crisis or "BEAR" in regime:
                self.assertNotAlmostEqual(
                    total_exp, 0.85, places=2,
                    msg=f"Historical crisis date {test_date} allocated 85% exposure! (Regime={regime}, is_crisis={is_crisis})"
                )

            # Assert budget adherence
            if is_crisis:
                self.assertLessEqual(
                    total_exp, 0.150001,
                    msg=f"Historical CRISIS date {test_date} exceeded 15% budget: {total_exp:.4f}"
                )
            elif regime == "BEAR_HIGH_VOL":
                self.assertLessEqual(
                    total_exp, 0.250001,
                    msg=f"Historical BEAR_HIGH_VOL date {test_date} exceeded 25% budget: {total_exp:.4f}"
                )
            elif regime == "BEAR_LOW_VOL":
                self.assertLessEqual(
                    total_exp, 0.400001,
                    msg=f"Historical BEAR_LOW_VOL date {test_date} exceeded 40% budget: {total_exp:.4f}"
                )

        self.assertGreaterEqual(tested_count, 8, "Must test at least 8 real historical crisis dates")


if __name__ == "__main__":
    unittest.main()

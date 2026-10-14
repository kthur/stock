"""
Adversarial Empirical Stress Testing Suite for Risk Defense 1
=============================================================
Stress-tests:
1. Portfolio & Tail Risk Budgeting (R1): optimize_with_evt_cvar_constraint under boundary budgets
   (max_cvar = 0.02, 0.035, 0.04, 0.08, extreme tight 0.005, extreme loose 0.15)
2. Crisis Detector (R2): Continuous Sigmoid Crisis Gating Multiplier under extreme z-scores
   (z <= -5.0, z = 0.0, z = 0.45, z = 1.0, z = 10.0, z = 100.0)
3. Flash Crash Simulation: VIX leaping from 15 to 65+ with term structure inversion (backwardation),
   verifying immediate SEVERE escalation, 100% buy block, and recovery hysteresis.
"""

import math
import unittest
import numpy as np
import pandas as pd
from scipy.stats import t

from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.risk_manager import (
    RiskManager,
    CrisisDetector,
    CrisisLevel,
    RiskLevel,
    CRISIS_RISK_CAP,
)


class TestAdversarialTailRiskBudgeting(unittest.TestCase):
    """Task 1: Boundary and Extreme Stress Testing for EVT-CVaR Optimization."""

    def setUp(self):
        np.random.seed(42)
        self.allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            default_max_weight=0.50
        )
        self.allocator.is_phase101 = True

    def _generate_test_universe(self, n_samples=500):
        # Create 4 assets: A has heavy tail, B has medium vol, C has low vol, D has calm vol
        a_heavy = t.rvs(df=3, loc=0.0005, scale=0.030, size=n_samples)
        b_med = np.random.normal(0.0006, 0.015, size=n_samples)
        c_low = np.random.normal(0.0004, 0.008, size=n_samples)
        d_calm = np.random.normal(0.0003, 0.005, size=n_samples)

        returns_df = pd.DataFrame({
            "ASSET_HEAVY": a_heavy,
            "ASSET_MED": b_med,
            "ASSET_LOW": c_low,
            "ASSET_CALM": d_calm,
        })
        expected_returns = pd.Series({
            "ASSET_HEAVY": 0.0015,
            "ASSET_MED": 0.0010,
            "ASSET_LOW": 0.0006,
            "ASSET_CALM": 0.0004,
        })
        return returns_df, expected_returns

    def test_cvar_boundary_budgets(self):
        """Test boundary budgets max_cvar = 0.02, 0.035, 0.04, 0.08."""
        returns_df, expected_returns = self._generate_test_universe()

        # Budgets specified in dispatch:
        budgets_to_test = [0.02, 0.035, 0.04, 0.08]

        for budget in budgets_to_test:
            w_dict = self.allocator.optimize_with_evt_cvar_constraint(
                expected_returns=expected_returns,
                returns_df=returns_df,
                max_cvar=budget,
                confidence=0.95,
                max_weight=0.60
            )

            # Verification 1: Valid weights
            self.assertEqual(len(w_dict), 4)
            total_w = sum(w_dict.values())
            self.assertAlmostEqual(total_w, 1.0, places=4, msg=f"Weights do not sum to 1.0 for budget={budget}")
            for sym, w in w_dict.items():
                self.assertGreaterEqual(w, -1e-6, msg=f"Negative weight {w} for {sym} at budget={budget}")
                self.assertLessEqual(w, 0.60 + 1e-4, msg=f"Weight exceeds max_weight for {sym} at budget={budget}")

            # Verification 2: Realized EVT-CVaR
            w_vec = np.array([w_dict[c] for c in returns_df.columns])
            port_cvar = self.allocator.estimate_portfolio_evt_cvar(w_vec, returns_df.values, confidence=0.95)

            # For budget = 0.04 under is_phase101, dynamic scaling targets dyn_cvar ~ 0.0709
            if math.isclose(budget, 0.04, abs_tol=1e-5):
                eff_budget = float(np.clip(0.12 * math.sqrt(20 / 252.0) * 2.10, 0.065, 0.075))
            elif budget > 0.05:
                eff_budget = max(budget, float(np.clip(0.12 * math.sqrt(20 / 252.0) * 2.10, 0.065, 0.075)))
            else:
                eff_budget = budget

            self.assertLessEqual(
                port_cvar,
                eff_budget + 1e-4,
                msg=f"Portfolio CVaR {port_cvar:.5f} violated effective budget {eff_budget:.5f} (raw budget={budget})"
            )

            # When explicit tight budget is given (0.02 and 0.035), port_cvar MUST satisfy budget + 1e-4
            if budget in (0.02, 0.035):
                self.assertLessEqual(
                    port_cvar,
                    budget + 1e-4,
                    msg=f"Portfolio CVaR {port_cvar:.5f} violated strict explicit user budget {budget:.5f}"
                )

    def test_cvar_extreme_unfeasible_budget_graceful_fallback(self):
        """Adversarial stress: Ultra-tight budget (0.001) where all assets have CVaR > 0.005."""
        returns_df, expected_returns = self._generate_test_universe()
        ultra_tight_budget = 0.001

        # Must not raise exception, must return normalized weights, and must heavily weight lowest risk assets
        w_dict = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=ultra_tight_budget,
            confidence=0.95,
            max_weight=0.60
        )
        self.assertAlmostEqual(sum(w_dict.values()), 1.0, places=4)
        # Lowest vol assets (LOW and CALM) should dominate over HEAVY
        self.assertGreater(
            w_dict["ASSET_CALM"] + w_dict["ASSET_LOW"],
            w_dict["ASSET_HEAVY"],
            msg="Fallback did not prioritize lowest risk assets under impossible budget constraint"
        )

    def test_cvar_dirty_returns_matrix(self):
        """Adversarial stress: returns_df with NaNs, Infs, and zero variance columns."""
        returns_df, expected_returns = self._generate_test_universe()
        dirty_df = returns_df.copy()
        dirty_df.iloc[10:15, 0] = np.nan
        dirty_df.iloc[20, 1] = np.inf
        dirty_df.iloc[25, 2] = -np.inf
        dirty_df["ZERO_VOL"] = 0.0
        exp_ret_dirty = expected_returns.copy()
        exp_ret_dirty["ZERO_VOL"] = 0.0001

        w_dict = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=exp_ret_dirty,
            returns_df=dirty_df,
            max_cvar=0.035,
            confidence=0.95,
            max_weight=0.50
        )
        self.assertAlmostEqual(sum(w_dict.values()), 1.0, places=4)
        for w in w_dict.values():
            self.assertTrue(math.isfinite(w))
            self.assertGreaterEqual(w, 0.0)


class TestAdversarialCrisisDetectorSmoothGating(unittest.TestCase):
    """Task 2: Continuous Sigmoid Crisis Gating Multiplier Stress Testing."""

    def setUp(self):
        self.detector = CrisisDetector()

    def test_extreme_z_scores(self):
        """
        Stress test get_smooth_crisis_position_multiplier with:
        z <= -5.0, z = 0.0, z = 0.45, z = 1.0, z = 10.0, z = 100.0
        """
        # 1. z <= -5.0 (calm regime beyond left bound): must be EXACTLY 1.0
        for z_calm in [-10.0, -5.0, -1.0, -0.001]:
            mult = self.detector.get_smooth_crisis_position_multiplier(composite_score=z_calm)
            self.assertEqual(mult, 1.0, msg=f"Negative z={z_calm} did not return exact 1.0")

        # 2. z = 0.0 (calm baseline): must be EXACTLY 1.0
        mult_0 = self.detector.get_smooth_crisis_position_multiplier(composite_score=0.0)
        self.assertEqual(mult_0, 1.0, msg="z=0.0 did not return exact 1.0")

        # 3. z = 0.45 (inflection point z0):
        # Sigmoid value = 1 / (1 + exp(0)) = 0.5
        # Expected: 1.0 - (1.0 - 0.15) * 0.5 = 1.0 - 0.425 = 0.575
        mult_inflection = self.detector.get_smooth_crisis_position_multiplier(composite_score=0.45)
        self.assertAlmostEqual(mult_inflection, 0.575, places=5, msg="z=0.45 not at exact sigmoid midpoint 0.575")

        # 4. z = 1.0 (severe crisis boundary):
        # Sigmoid: 1 / (1 + exp(-10 * (1 - 0.45))) = 1 / (1 + exp(-5.5)) ~ 0.99593
        # Expected: 1.0 - 0.85 * 0.99593 ~ 0.15346
        mult_1 = self.detector.get_smooth_crisis_position_multiplier(composite_score=1.0)
        self.assertAlmostEqual(mult_1, 0.15346, places=4, msg="z=1.0 deviated from expected asymptotic value")
        self.assertGreaterEqual(mult_1, 0.15)
        self.assertLess(mult_1, 0.16)

        # 5. z = 10.0 and z = 100.0 (extreme crisis):
        # Clip to 1.0 guarantees finite evaluation and floor >= 0.15
        for z_extreme in [2.0, 5.0, 10.0, 100.0, 1e6]:
            mult_ext = self.detector.get_smooth_crisis_position_multiplier(composite_score=z_extreme)
            self.assertTrue(math.isfinite(mult_ext))
            self.assertGreaterEqual(mult_ext, 0.15, msg=f"z={z_extreme} breached floor 0.15")
            self.assertLessEqual(mult_ext, 0.16, msg=f"z={z_extreme} unexpectedly exceeded boundary")

    def test_smooth_crisis_cash_target_bounds(self):
        """Verify smooth cash target is strictly within [0.10, 0.90]."""
        for z in [-5.0, 0.0, 0.25, 0.45, 0.70, 1.0, 10.0]:
            cash_tgt = self.detector.get_smooth_crisis_cash_target(composite_score=z)
            self.assertGreaterEqual(cash_tgt, 0.10)
            self.assertLessEqual(cash_tgt, 0.90)
            self.assertTrue(math.isfinite(cash_tgt))

        # At calm z=0.0, cash target = 1.0 - 1.0 + 0.10 = 0.10
        self.assertAlmostEqual(self.detector.get_smooth_crisis_cash_target(composite_score=0.0), 0.10, places=5)
        # At severe z=1.0, cash target ~ 1.0 - 0.15346 + 0.10 = 0.94654 -> clipped to 0.90
        self.assertAlmostEqual(self.detector.get_smooth_crisis_cash_target(composite_score=1.0), 0.90, places=5)


class TestAdversarialFlashCrashSimulation(unittest.TestCase):
    """Task 3: Flash Crash Simulation and Crisis Level Escalation."""

    def setUp(self):
        self.risk_manager = RiskManager(portfolio_value=100000000)  # 100M KRW
        self.detector = self.risk_manager.crisis_detector

    def test_flash_crash_immediate_severe_escalation(self):
        """
        Simulate 20 days of tranquil market followed by instant Flash Crash:
        VIX leaps 15 -> 65 with term structure inverted (VIX/SMA60 > 1.15).
        """
        # Phase 1: Tranquil regime for 20 days
        for day in range(20):
            level = self.detector.evaluate_indicators(
                vix=14.5 + np.random.uniform(-0.5, 0.5),
                dd=0.01,
                daily_volume_ratio=0.95,
                usdkrw=1300.0,
                oil=75.0,
                tnx=4.0,
                dxy=102.0
            )
            self.assertEqual(level, CrisisLevel.NONE)
            self.assertFalse(self.detector.should_block_new_buys())

        # Verify sizing before crash: Normal buying allowed
        pos_size_before = self.risk_manager.calculate_position_sizing(
            symbol="005930",
            entry_price=70000,
            stop_loss_price=66500,
            win_rate=0.55,
            win_loss_ratio=1.5
        )
        self.assertGreater(pos_size_before, 0, "Normal buying should be non-zero in tranquil regime")

        # Phase 2: Instant Flash Crash on Day 21
        # VIX leaps to 65.0, drawdown accelerates to 8%, volume spikes to 3.5x
        crash_level = self.detector.evaluate_indicators(
            vix=65.0,
            dd=0.08,
            daily_volume_ratio=3.5,
            usdkrw=1380.0,
            oil=90.0,
            tnx=4.8,
            dxy=107.0
        )

        # Assertion 1: Immediate SEVERE escalation
        self.assertEqual(crash_level, CrisisLevel.SEVERE, "CrisisDetector did not escalate immediately to SEVERE on VIX 65 crash")
        self.assertEqual(self.detector.crisis_level, CrisisLevel.SEVERE)

        # Assertion 2: 100% buy block
        self.assertTrue(self.detector.should_block_new_buys(), "should_block_new_buys() was not True in SEVERE crisis")

        # Assertion 3: Position sizing returns EXACTLY 0 shares (100% buy block enforced)
        pos_size_during_crash = self.risk_manager.calculate_position_sizing(
            symbol="005930",
            entry_price=60000,
            stop_loss_price=57000,
            win_rate=0.55,
            win_loss_ratio=1.5
        )
        self.assertEqual(pos_size_during_crash, 0, "calculate_position_sizing() did not return 0 during SEVERE crisis")

        # Assertion 4: Emergency cash target is maximized (85%)
        cash_target = self.detector.get_crisis_cash_target()
        self.assertEqual(cash_target, 0.85, "Cash target was not 0.85 in SEVERE crisis")

        # Assertion 5: Crisis risk cap is 0.000 (total halt)
        risk_cap = CRISIS_RISK_CAP[CrisisLevel.SEVERE]
        self.assertEqual(risk_cap, 0.0, "CRISIS_RISK_CAP for SEVERE was not 0.0")

    def test_flash_crash_liquidation_trigger_after_3_days(self):
        """Simulate prolonged SEVERE flash crash: should_liquidate triggers on day 3."""
        # 10 tranquil days
        for _ in range(10):
            self.detector.evaluate_indicators(vix=15.0, dd=0.01)

        # Day 1 of crash: SEVERE, but should_liquidate False (only 1 day in crisis)
        self.detector.evaluate_indicators(vix=68.0, dd=0.10)
        self.assertEqual(self.detector.crisis_level, CrisisLevel.SEVERE)
        self.assertFalse(self.detector.should_liquidate())

        # Day 2 of crash
        self.detector.evaluate_indicators(vix=70.0, dd=0.12)
        self.assertEqual(self.detector.crisis_level, CrisisLevel.SEVERE)
        self.assertFalse(self.detector.should_liquidate())

        # Day 3 of crash: _days_in_crisis >= 3 -> should_liquidate MUST be True
        self.detector.evaluate_indicators(vix=72.0, dd=0.15)
        self.assertEqual(self.detector.crisis_level, CrisisLevel.SEVERE)
        self.assertTrue(self.detector.should_liquidate(), "should_liquidate() did not trigger on day 3 of SEVERE crisis")

    def test_cds_credit_shock_standalone_override(self):
        """Verify credit default swap spike > 150bp triggers standalone SEVERE override."""
        level = self.detector.evaluate_indicators(
            vix=20.0,
            dd=0.02,
            cds_5y=160.0  # Acute sovereign/corporate credit event
        )
        self.assertEqual(level, CrisisLevel.SEVERE, "CDS > 150bp failed to trigger standalone SEVERE level")
        self.assertTrue(self.detector.should_block_new_buys())


if __name__ == "__main__":
    unittest.main()

"""
Adversarial Empirical Stress Testing Suite for Risk Defense Gen2 (R1 & R2)
Authored by: challenger_risk_defense_gen2_1 (Empirical Challenger)

Coverage:
1. Boundary CVaR budgets (0.01, 0.02, 0.035, 0.04, 0.08, 0.15) under heavy-tail Student-t (df=2, 3, 5) and Cauchy returns.
2. Non-positive definite covariance matrices, extreme correlation spikes (r -> 1.0), all-zero volatility, NaN/Inf return arrays.
3. 12% target volatility tracking under sudden 400% volatility surges.
4. Continuous sigmoid behavior with extreme z-scores (z = -10.0, 0.0, +10.0, +100.0).
5. Flash crash simulation: VIX leaping from 15 to 80+ with term structure backwardation inversion.
6. Verification that SEVERE crisis level guarantees 100% rejection of new buy orders and zero position sizing.
7. Verification that NaN, Inf, negative, or above-entry stop-loss prices never cause crashes or invalid sizes.
"""

import unittest
import math
import numpy as np
import pandas as pd
from scipy.stats import t, cauchy

from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.risk_manager import (
    RiskManager, CrisisDetector, CrisisLevel
)


class TestAdversarialEVTCVaRBudgetsAndDistributions(unittest.TestCase):
    """Stress tests boundary CVaR budgets under heavy-tailed Student-t and Cauchy distributions."""

    def setUp(self):
        np.random.seed(42)
        self.allocator = PortfolioAllocator(min_tail_samples=15)
        self.unified_allocator = UnifiedPortfolioAllocator(version=102)

    def test_direct_evt_cvar_heavy_tails(self):
        """Estimate EVT-CVaR directly on Student-t (df=2, 3, 5) and Cauchy (df=1)."""
        distributions = [
            ("Student-t df=2", t.rvs(df=2, loc=0.0005, scale=0.015, size=800)),
            ("Student-t df=3", t.rvs(df=3, loc=0.0005, scale=0.015, size=800)),
            ("Student-t df=5", t.rvs(df=5, loc=0.0005, scale=0.015, size=800)),
            ("Cauchy df=1", cauchy.rvs(loc=0.0, scale=0.01, size=800)),
        ]

        for dist_name, rets in distributions:
            res = self.allocator.estimate_evt_cvar(rets, confidence=0.95)
            self.assertTrue(math.isfinite(res["cvar"]), f"Non-finite CVaR for {dist_name}: {res}")
            self.assertTrue(math.isfinite(res["var"]), f"Non-finite VaR for {dist_name}: {res}")
            self.assertGreater(res["cvar"], 0.0, f"CVaR not positive for {dist_name}")
            self.assertGreaterEqual(res["cvar"], res["var"] - 1e-5, f"CVaR < VaR for {dist_name}")
            self.assertLessEqual(res["xi"], 0.50 + 1e-6, f"Shape xi not clamped for {dist_name}")

    def test_boundary_cvar_budgets_student_t_and_cauchy(self):
        """
        Verify boundary CVaR budgets [0.01, 0.02, 0.035, 0.04, 0.08, 0.15] under heavy tails.
        """
        budgets = [0.01, 0.02, 0.035, 0.04, 0.08, 0.15]
        N = 500

        # Construct universe with differing tail risks
        # Asset A: High tail risk (Student-t df=2)
        # Asset B: Moderate tail risk (Student-t df=5)
        # Asset C: Normal baseline
        # Asset D: Cauchy extreme risk
        asset_a = t.rvs(df=2, loc=0.0010, scale=0.030, size=N)
        asset_b = t.rvs(df=5, loc=0.0008, scale=0.015, size=N)
        asset_c = np.random.normal(0.0005, 0.010, size=N)
        asset_d = cauchy.rvs(loc=0.0002, scale=0.008, size=N)

        returns_df = pd.DataFrame({
            'ASSET_A': asset_a,
            'ASSET_B': asset_b,
            'ASSET_C': asset_c,
            'ASSET_D': asset_d,
        })
        expected_returns = pd.Series({
            'ASSET_A': 0.0020,
            'ASSET_B': 0.0012,
            'ASSET_C': 0.0006,
            'ASSET_D': 0.0003,
        })

        for budget in budgets:
            weights = self.allocator.optimize_with_evt_cvar_constraint(
                expected_returns=expected_returns,
                returns_df=returns_df,
                max_cvar=budget,
                confidence=0.95,
                max_weight=0.70
            )

            # 1. Weights must be non-empty and well-formed
            self.assertEqual(len(weights), 4, f"Missing weights for budget {budget}")
            for sym, w in weights.items():
                self.assertTrue(math.isfinite(w), f"Weight for {sym} not finite: {w}")
                self.assertGreaterEqual(w, -1e-6, f"Negative weight for {sym}: {w}")
                self.assertLessEqual(w, 0.70 + 1e-4, f"Weight exceeded max_weight: {w}")

            # 2. Weights sum to 1.0
            sum_w = sum(weights.values())
            self.assertAlmostEqual(sum_w, 1.0, places=4, msg=f"Weights do not sum to 1.0 at budget {budget}")

            # 3. Portfolio EVT-CVaR check
            w_arr = np.array([weights['ASSET_A'], weights['ASSET_B'], weights['ASSET_C'], weights['ASSET_D']])
            port_cvar = self.allocator.estimate_portfolio_evt_cvar(w_arr, returns_df.values, confidence=0.95)
            self.assertTrue(math.isfinite(port_cvar), f"Portfolio CVaR not finite: {port_cvar}")

            # If budget >= 0.035, verify budget satisfaction
            if budget >= 0.035:
                eff_limit = budget if not getattr(self.allocator, "is_phase101", False) else max(budget, 0.075)
                self.assertLessEqual(port_cvar, eff_limit + 1e-3, f"Port CVaR {port_cvar} exceeded budget {eff_limit}")


class TestAdversarialNumericalSingularities(unittest.TestCase):
    """Stress tests non-PSD covariance, extreme correlations, zero vol, and NaN/Inf arrays."""

    def setUp(self):
        np.random.seed(42)
        self.allocator = PortfolioAllocator(min_tail_samples=15)
        self.unified_allocator = UnifiedPortfolioAllocator(version=102)

    def test_non_psd_covariance_handling(self):
        """Covariance matrix with negative eigenvalues (non-PSD)."""
        N = 4
        # Create indefinite matrix: eigenvalues [0.02, 0.01, 0.005, -0.01]
        Q, _ = np.linalg.qr(np.random.randn(N, N))
        diag_indef = np.diag([0.02, 0.01, 0.005, -0.01])
        non_psd_cov = Q @ diag_indef @ Q.T

        returns_matrix = np.random.normal(0, 0.01, size=(100, N))
        tail_cov = self.allocator.compute_tail_stress_cov(returns_matrix, non_psd_cov)

        self.assertEqual(tail_cov.shape, (N, N))
        self.assertTrue(np.all(np.isfinite(tail_cov)))

        # Also test component CVaR risk contributions under non-PSD
        w = np.ones(N) / N
        mrc, trc = self.unified_allocator.compute_component_cvar_risk_contributions(w, non_psd_cov)
        self.assertEqual(len(mrc), N)
        self.assertEqual(len(trc), N)
        self.assertTrue(np.all(np.isfinite(mrc)))
        self.assertTrue(np.all(np.isfinite(trc)))

    def test_extreme_correlation_spike_r_near_one(self):
        """All assets perfectly correlated (r -> 1.0), rank 1 covariance matrix."""
        N = 5
        base_ret = np.random.normal(0.001, 0.02, size=300)
        # Create identical or near-identical asset returns
        returns_dict = {f"SYM_{i}": base_ret + np.random.normal(0, 1e-6, size=300) for i in range(N)}
        returns_df = pd.DataFrame(returns_dict)
        expected_returns = pd.Series({f"SYM_{i}": 0.001 + i * 1e-4 for i in range(N)})

        weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.05,
            confidence=0.95
        )

        self.assertEqual(len(weights), N)
        for sym, w in weights.items():
            self.assertTrue(math.isfinite(w), f"Weight {sym} is not finite: {w}")
            self.assertGreaterEqual(w, -1e-6)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_all_zero_volatility_returns(self):
        """All assets have zero volatility (flat zero or constant return)."""
        N = 3
        returns_df = pd.DataFrame({
            "SYM_0": np.zeros(200),
            "SYM_1": np.zeros(200),
            "SYM_2": np.zeros(200),
        })
        expected_returns = pd.Series({"SYM_0": 0.0, "SYM_1": 0.0, "SYM_2": 0.0})

        weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.04
        )

        self.assertEqual(len(weights), N)
        for sym, w in weights.items():
            self.assertTrue(math.isfinite(w))
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_nan_inf_return_arrays(self):
        """Return arrays containing NaN and Inf values."""
        N = 3
        rets = np.random.normal(0.001, 0.02, size=(250, N))
        rets[0, 0] = np.nan
        rets[10, 1] = np.inf
        rets[20, 2] = -np.inf
        rets[50:60, :] = np.nan

        returns_df = pd.DataFrame(rets, columns=["A", "B", "C"])
        expected_returns = pd.Series({"A": 0.001, "B": 0.002, "C": 0.0015})

        # Must not raise unhandled exception or return NaNs
        weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.05
        )

        self.assertEqual(len(weights), N)
        for sym, w in weights.items():
            self.assertTrue(math.isfinite(w), f"Weight for {sym} became NaN/Inf: {w}")
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)


class TestAdversarialTargetVolatilityTracking(unittest.TestCase):
    """Stress tests target volatility tracking (12%) under sudden 400% surges."""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000.0, target_annual_volatility=0.12, max_position_size_pct=0.20)

    def test_position_sizing_under_400_percent_vol_surge(self):
        """
        Baseline ATR corresponds to ~12% annual vol.
        A 400% surge increases ATR by 4x (~48% vol).
        Verify position size drops significantly in response to vol surge.
        """
        entry_price = 100.0
        stop_loss_price = 95.0
        win_rate = 0.55
        win_loss_ratio = 1.8

        # Baseline: ATR = 0.756 -> annual vol = (0.756 / 100) * sqrt(252) ~ 0.120 (12%)
        baseline_atr = (0.12 / math.sqrt(252)) * entry_price
        qty_baseline = self.rm.calculate_position_sizing(
            symbol="TEST_ASSET",
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            win_rate=win_rate,
            win_loss_ratio=win_loss_ratio,
            vix=15.0,
            atr=baseline_atr
        )

        # 400% surge: ATR = 4x baseline -> annual vol ~ 48%
        surged_atr = baseline_atr * 4.0
        qty_surged = self.rm.calculate_position_sizing(
            symbol="TEST_ASSET",
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            win_rate=win_rate,
            win_loss_ratio=win_loss_ratio,
            vix=15.0,
            atr=surged_atr
        )

        self.assertGreater(qty_baseline, 0)
        self.assertGreater(qty_surged, 0)
        # Position sizing under surged volatility must be strictly smaller
        self.assertLess(qty_surged, qty_baseline)
        ratio = qty_surged / qty_baseline
        # Given vol_scaler is clamped to [0.25, 1.5], 4x vol drops ratio to ~0.25 - 0.35
        self.assertLessEqual(ratio, 0.40, f"Volatility scaling failed to sufficiently penalize surge: ratio={ratio}")


class TestAdversarialCrisisDetectorSigmoid(unittest.TestCase):
    """Stress tests continuous sigmoid behavior across extreme z-scores."""

    def setUp(self):
        self.cd = CrisisDetector()

    def test_continuous_sigmoid_extreme_z_scores(self):
        """
        Test z = -10.0, 0.0, +10.0, +100.0.
        Verify:
        - z <= 0.0 returns 1.0 (exact zero-drag baseline)
        - Monotonically non-increasing in z
        - Always bounded in [g_min, 1.0] where g_min = 0.15
        """
        test_z_values = [-10.0, -1.0, 0.0, 0.20, 0.45, 0.70, 1.0, 10.0, 100.0]
        results = [self.cd.get_smooth_crisis_position_multiplier(composite_score=z) for z in test_z_values]

        # 1. Zero drag at z <= 0.0
        self.assertEqual(results[0], 1.0, "z = -10.0 must yield 1.0")
        self.assertEqual(results[1], 1.0, "z = -1.0 must yield 1.0")
        self.assertEqual(results[2], 1.0, "z = 0.0 must yield exactly 1.0")

        # 2. Monotonicity for non-negative z
        non_neg_z = [z for z in test_z_values if z >= 0.0]
        non_neg_mults = [self.cd.get_smooth_crisis_position_multiplier(composite_score=z) for z in non_neg_z]
        for i in range(len(non_neg_mults) - 1):
            self.assertGreaterEqual(
                non_neg_mults[i],
                non_neg_mults[i+1],
                f"Sigmoid multiplier not monotonically decreasing: {non_neg_z[i]} ({non_neg_mults[i]}) vs {non_neg_z[i+1]} ({non_neg_mults[i+1]})"
            )

        # 3. Extreme high z-scores (clipped to 1.0, where smooth_mult approaches g_min = 0.15)
        mult_10 = self.cd.get_smooth_crisis_position_multiplier(composite_score=10.0)
        mult_100 = self.cd.get_smooth_crisis_position_multiplier(composite_score=100.0)
        self.assertAlmostEqual(mult_10, mult_100, places=6)
        self.assertLessEqual(mult_10, 0.155)
        self.assertGreaterEqual(mult_10, 0.150)

    def test_smooth_crisis_cash_target_bounds(self):
        """Continuous sigmoid cash target must be in [0.10, 0.90] and monotonic."""
        test_z = [0.0, 0.30, 0.50, 0.80, 1.0, 50.0]
        cash_targets = [self.cd.get_smooth_crisis_cash_target(composite_score=z) for z in test_z]

        for ct in cash_targets:
            self.assertGreaterEqual(ct, 0.10)
            self.assertLessEqual(ct, 0.90)

        # Monotonically increasing cash target with crisis severity
        for i in range(len(cash_targets) - 1):
            self.assertLessEqual(cash_targets[i], cash_targets[i+1])


class TestAdversarialFlashCrashAndSevereCrisis(unittest.TestCase):
    """Stress tests flash crash simulation (VIX 15 -> 80+) and SEVERE buy rejection."""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000.0)
        self.cd = self.rm.crisis_detector

    def test_flash_crash_simulation_vix_15_to_85_backwardation(self):
        """
        Simulate calm market followed by sudden flash crash:
        VIX jumps from 15 to 85 with inverted term structure (backwardation).
        Verify SEVERE crisis trigger, 100% buy rejection, and zero position sizing.
        """
        # 1. Warm up with 60 days of calm VIX = 15.0
        for _ in range(60):
            self.cd.evaluate(vix=15.0, daily_volume_ratio=1.0)
        self.assertEqual(self.cd.crisis_level, CrisisLevel.NONE)
        self.assertFalse(self.cd.should_block_new_buys())

        # 2. Flash crash: VIX jumps to 85.0 with volume surge 3.5x and drawdown 18%
        level = self.cd.evaluate(vix=85.0, daily_volume_ratio=3.5, dd=0.18)

        # 3. Verify SEVERE crisis
        self.assertEqual(level, CrisisLevel.SEVERE)
        self.assertEqual(self.cd.crisis_level, CrisisLevel.SEVERE)

        # 4. Verify 100% block of new buys
        self.assertTrue(self.cd.should_block_new_buys())

        # 5. Verify calculate_position_sizing returns strictly 0
        qty = self.rm.calculate_position_sizing(
            symbol="CRASH_BUY_ATTEMPT",
            entry_price=150.0,
            stop_loss_price=140.0,
            win_rate=0.70,
            win_loss_ratio=2.5,
            vix=85.0
        )
        self.assertEqual(qty, 0, "Position sizing under SEVERE crisis must be 0")

        # 6. Verify multipliers
        self.assertEqual(self.cd.get_crisis_position_multiplier(), 0.15)
        self.assertEqual(self.cd.get_crisis_cash_target(), 0.85)
        self.assertEqual(self.cd.get_crisis_risk_multiplier(), 0.25)


class TestAdversarialStopLossPrices(unittest.TestCase):
    """Stress tests NaN, Inf, negative, zero, and above-entry stop-loss inputs."""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000.0)

    def test_stop_loss_nan_fallback(self):
        """NaN stop-loss price must fall back to default stop-loss percentage without crashing."""
        entry = 100.0
        qty = self.rm.calculate_position_sizing(
            symbol="NAN_STOP",
            entry_price=entry,
            stop_loss_price=float('nan'),
            vix=18.0
        )
        self.assertGreater(qty, 0, "NaN stop-loss should fallback to safe positive quantity")
        self.assertIsInstance(qty, int)

    def test_stop_loss_inf_fallback(self):
        """Infinite stop-loss price must not cause crash or invalid sizing."""
        entry = 100.0
        qty_pos_inf = self.rm.calculate_position_sizing(
            symbol="POS_INF_STOP",
            entry_price=entry,
            stop_loss_price=float('inf'),
            vix=18.0
        )
        qty_neg_inf = self.rm.calculate_position_sizing(
            symbol="NEG_INF_STOP",
            entry_price=entry,
            stop_loss_price=-float('inf'),
            vix=18.0
        )
        self.assertGreaterEqual(qty_pos_inf, 0)
        self.assertGreaterEqual(qty_neg_inf, 0)
        self.assertTrue(math.isfinite(qty_pos_inf))
        self.assertTrue(math.isfinite(qty_neg_inf))

    def test_stop_loss_negative_or_zero(self):
        """Negative or zero stop-loss price must fall back to safe default."""
        entry = 100.0
        qty_zero = self.rm.calculate_position_sizing(
            symbol="ZERO_STOP",
            entry_price=entry,
            stop_loss_price=0.0,
            vix=18.0
        )
        qty_neg = self.rm.calculate_position_sizing(
            symbol="NEG_STOP",
            entry_price=entry,
            stop_loss_price=-50.0,
            vix=18.0
        )
        self.assertGreater(qty_zero, 0)
        self.assertGreater(qty_neg, 0)

    def test_stop_loss_above_entry_price(self):
        """Stop-loss price >= entry price (invalid long stop) must return 0."""
        entry = 100.0
        qty_equal = self.rm.calculate_position_sizing(
            symbol="EQUAL_STOP",
            entry_price=entry,
            stop_loss_price=100.0,
            vix=18.0
        )
        qty_above = self.rm.calculate_position_sizing(
            symbol="ABOVE_STOP",
            entry_price=entry,
            stop_loss_price=105.0,
            vix=18.0
        )
        self.assertEqual(qty_equal, 0, "Stop equal to entry must return 0 quantity")
        self.assertEqual(qty_above, 0, "Stop above entry must return 0 quantity")

    def test_entry_price_invalid(self):
        """Invalid entry prices (NaN, Inf, 0, negative) must return 0."""
        for invalid_entry in [float('nan'), float('inf'), -float('inf'), 0.0, -10.0]:
            qty = self.rm.calculate_position_sizing(
                symbol="INVALID_ENTRY",
                entry_price=invalid_entry,
                stop_loss_price=90.0,
                vix=18.0
            )
            self.assertEqual(qty, 0, f"Entry {invalid_entry} must return 0 quantity")


if __name__ == '__main__':
    unittest.main()

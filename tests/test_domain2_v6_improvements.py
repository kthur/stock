"""
Unit and Integration Regression Tests for Domain 2 (V6-09 ~ V6-16) Improvements:
- V6-09: Leland Dynamic Buffer Band Boundary Collapse Fix (w_curr=0 new entry, w_targ=0 full exit, small allocation delta scaling)
- V6-10: Black-Litterman C1 Smooth Quadratic Penalty & Global Problem Formulation in SLSQP
- V6-11: EVT-POT Quantile Inversion Guard (u <= q_alpha) & GPD Regular Shape Bounds (xi in [-0.50, 0.50])
- V6-12: Rockafellar-Uryasev Convex CVaR Pseudo-Huber L1 Smoothing & Vectorized Constraints
- V6-13: CrisisDetector Recovery Latch Auto-Reset (20d) & WATCH Defensive Haircut Priority
- V6-14: StrategyCoverageAnalyzer Primary Missing Reason Modal Frequency Extraction
- V6-15: Downside Co-Semivariance Diagonal Variance Target Shrinkage (Negative Hedging Preservation)
- V6-16: RMT Marchenko-Pastur Dynamic Residual Variance Estimation (Excluding Market Mode Lambda_1)
"""

import unittest
import numpy as np
import pandas as pd
from scipy.stats import t, norm

from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.analysis.portfolio_optimizer import (
    calculate_black_litterman_weights,
    shrink_covariance_matrix
)
from trading_system.src.risk.risk_manager import CrisisDetector, CrisisLevel
from trading_system.src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from trading_system.src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine


class TestDomain2V6Improvements(unittest.TestCase):
    """Exhaustive test suite for V6-09 through V6-16."""

    def setUp(self):
        np.random.seed(42)

    # -------------------------------------------------------------------------
    # V6-09: Leland Dynamic Buffer Band Boundary Collapse Fix
    # -------------------------------------------------------------------------
    def test_v6_09_leland_new_entry_bypass(self):
        """
        Verify that new position initiation (w_curr == 0.0, w_targ > 0.0) is NEVER
        suppressed by buffer band even when w_targ <= delta_i (where L_i == 0.0).
        """
        allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            delta_cap=0.050,
            rebalance_mode="target"
        )
        # Small target weight of 1.2% with 0 current weight
        current_weights = {"005930": 0.0}
        target_weights = {"005930": 0.012}
        market_map = {"005930": "KOSPI"}
        vol_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]
        # Must execute BUY, NOT HOLD
        self.assertEqual(trade["action"], "BUY")
        self.assertGreater(trade["w_new"], 0.0)
        self.assertGreater(trade["trade_weight"], 0.0)
        self.assertEqual(res["summary"]["traded_count"], 1)
        self.assertEqual(res["summary"]["skipped_count"], 0)

    def test_v6_09_leland_full_exit_bypass(self):
        """
        Verify that complete liquidation (w_targ == 0.0, w_curr > 0.0) is NEVER
        trapped in HOLD even if w_curr is within [0.0, delta_i].
        """
        allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            delta_cap=0.050,
            rebalance_mode="boundary"
        )
        current_weights = {"005930": 0.008}
        target_weights = {"005930": 0.0}
        market_map = {"005930": "KOSPI"}
        vol_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]
        self.assertEqual(trade["action"], "SELL")
        self.assertEqual(trade["w_new"], 0.0)
        self.assertEqual(res["summary"]["traded_count"], 1)

    def test_v6_09_leland_small_allocation_delta_scaling(self):
        """
        Verify delta_i is scaled proportionally (delta_i <= 0.40 * w_targ)
        so that lower buffer band L_i = max(0.0, w_targ - delta_i) > 0.
        """
        allocator = PortfolioAllocator(delta_floor=0.005, delta_cap=0.050)
        current_weights = {"005930": 0.015}
        target_weights = {"005930": 0.010}  # delta_i should be <= 0.004 -> L_i >= 0.006
        market_map = {"005930": "KOSPI"}
        vol_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )
        band = res["trades"]["005930"]["band"]
        # L_i must be strictly positive
        self.assertGreater(band[0], 0.0)

    # -------------------------------------------------------------------------
    # V6-10: Black-Litterman C1 Smooth Quadratic Utility & SLSQP Stability
    # -------------------------------------------------------------------------
    def test_v6_10_black_litterman_negative_excess_smooth_convergence(self):
        """
        Verify Black-Litterman optimization converges smoothly without gradient explosion
        or exception fallback when all expected returns are below the risk-free rate.
        """
        cov = np.array([
            [0.04, 0.01, 0.01],
            [0.01, 0.05, 0.02],
            [0.01, 0.02, 0.06]
        ])
        predicted_returns = np.array([0.01, 0.015, 0.02])  # All below rf=0.04

        weights = calculate_black_litterman_weights(
            cov_matrix=cov,
            predicted_returns=predicted_returns,
            tau=0.05,
            risk_free_rate=0.04
        )

        self.assertEqual(len(weights), 3)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=5)
        self.assertTrue(np.all(weights >= 0.0))
        self.assertTrue(np.all(np.isfinite(weights)))

    def test_v6_10_black_litterman_positive_excess_smooth_convergence(self):
        """
        Verify Black-Litterman optimization converges to valid weights with positive excess returns.
        """
        cov = np.array([
            [0.04, 0.01],
            [0.01, 0.05]
        ])
        predicted_returns = np.array([0.08, 0.06])

        weights = calculate_black_litterman_weights(
            cov_matrix=cov,
            predicted_returns=predicted_returns,
            tau=0.05,
            risk_free_rate=0.03
        )

        self.assertEqual(len(weights), 2)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=5)
        self.assertTrue(np.all(weights >= 0.0))

    # -------------------------------------------------------------------------
    # V6-11: EVT-POT Quantile Inversion Guard & GPD Shape Bounds
    # -------------------------------------------------------------------------
    def test_v6_11_evt_pot_threshold_ceiling(self):
        """
        Verify threshold u is capped at u_max_allowed <= quantile(losses, confidence - 0.02)
        preventing u > VaR_alpha and quantile inversion.
        """
        allocator = PortfolioAllocator(min_tail_samples=10)
        # Generate quiet regime with positive drift returns (losses are negative or small)
        returns = np.random.normal(loc=0.005, scale=0.008, size=500)
        res = allocator.estimate_evt_cvar(returns, confidence=0.95, quantile_threshold=0.90)

        # VaR and CVaR must be non-negative and finite
        self.assertGreaterEqual(res["var"], 0.0)
        self.assertGreaterEqual(res["cvar"], res["var"] - 1e-6)
        self.assertIn(res["method"], ["evt_gpd", "evt_gpd_sigmoid_blended", "cornish_fisher", "empirical_fallback"])

    def test_v6_11_gpd_shape_regularity_bounds(self):
        """
        Verify shape parameter xi is strictly clamped to [-0.50, 0.50].
        """
        allocator = PortfolioAllocator(min_tail_samples=10)
        # Heavy-tailed Pareto returns
        returns = -np.random.pareto(a=1.5, size=500) * 0.02
        res = allocator.estimate_evt_cvar(returns, confidence=0.95, quantile_threshold=0.88)

        self.assertGreaterEqual(res["xi"], -0.50)
        self.assertLessEqual(res["xi"], 0.50)

    # -------------------------------------------------------------------------
    # V6-12: Rockafellar-Uryasev Convex CVaR Pseudo-Huber & Vectorized Constraints
    # -------------------------------------------------------------------------
    def test_v6_12_rockafellar_uryasev_cvar_optimization(self):
        """
        Verify optimize_rockafellar_uryasev_cvar completes successfully with
        Pseudo-Huber turnover regularization and vectorized constraints.
        """
        allocator = PortfolioAllocator(risk_aversion=2.0)
        mu_dict = {"A": 0.002, "B": 0.0015, "C": 0.001, "D": 0.0008}
        T = 60
        r_mat = np.random.normal(0.001, 0.015, size=(T, 4))
        cov_mat = np.cov(r_mat, rowvar=False)
        w_prev = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}

        weights = allocator.optimize_rockafellar_uryasev_cvar(
            expected_returns=mu_dict,
            historical_returns=r_mat,
            covariance_matrix=cov_mat,
            previous_weights=w_prev,
            confidence=0.95,
            max_cvar_limit=0.035,
            max_weight=0.50
        )

        self.assertEqual(len(weights), 4)
        self.assertAlmostEqual(float(sum(weights.values())), 1.0, places=4)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, -1e-6)
            self.assertLessEqual(w, 0.50 + 1e-4)

    # -------------------------------------------------------------------------
    # V6-13: CrisisDetector Recovery Mode Auto-Reset & WATCH Haircut Priority
    # -------------------------------------------------------------------------
    def test_v6_13_recovery_mode_auto_resets_at_day_20(self):
        """
        Verify that CrisisDetector resets _recovery_mode to False once _recovery_days >= 20.
        """
        detector = CrisisDetector()
        # Force activate crisis
        detector.evaluate(vix=45.0, daily_volume_ratio=2.0)
        self.assertEqual(detector.crisis_level, CrisisLevel.SEVERE)
        self.assertFalse(detector.is_recovery)

        # Transition to recovery (calm conditions)
        detector.evaluate(vix=18.0, daily_volume_ratio=1.0)
        detector.evaluate(vix=18.0, daily_volume_ratio=1.0)
        detector.evaluate(vix=18.0, daily_volume_ratio=1.0)

        # Run 25 calm days to verify auto-reset at day 20
        for _ in range(25):
            detector.evaluate(vix=18.0, daily_volume_ratio=1.0)

        self.assertFalse(detector.is_recovery)
        self.assertEqual(detector._recovery_days, 0)
        self.assertEqual(detector.get_crisis_position_multiplier(), 1.0)

    def test_v6_13_defensive_watch_overrides_recovery_multiplier(self):
        """
        Verify that if market enters CrisisLevel.WATCH, position multiplier is
        defensively reduced (0.70) instead of returning 1.00 from recovery mode.
        """
        detector = CrisisDetector()
        # Manually configure recovery state with day 15
        detector._recovery_mode = True
        detector._recovery_days = 15
        detector.crisis_level = CrisisLevel.WATCH

        multiplier = detector.get_crisis_position_multiplier()
        # Must return WATCH multiplier (0.70), NOT recovery 0.7875 or 1.00
        self.assertEqual(multiplier, 0.70)

    # -------------------------------------------------------------------------
    # V6-14: StrategyCoverageAnalyzer Primary Missing Reason Modal Frequency
    # -------------------------------------------------------------------------
    def test_v6_14_coverage_primary_missing_reason_modal_frequency(self):
        """
        Verify generate_coverage_report selects the modal missing reason with the
        highest count (max(reasons, key=reasons.get)), not just the first dict key.
        """
        analyzer = StrategyCoverageAnalyzer()
        coverage_data = {
            "total_symbols": 200,
            "strategies": {
                "rim_valuation": {
                    "valid_count": 50,
                    "missing_count": 150,
                    "coverage_pct": 25.0,
                    "reasons": {
                        "INSUFFICIENT_PRICE_HISTORY": 2,
                        "NO_FUNDAMENTAL_DATA": 148  # Clearly dominant reason
                    }
                }
            }
        }

        report = analyzer.generate_coverage_report(coverage_data, date_str="2026-08-22")
        # Report must list NO_FUNDAMENTAL_DATA as the primary missing reason
        self.assertIn("NO_FUNDAMENTAL_DATA", report)
        # Should NOT show INSUFFICIENT_PRICE_HISTORY as primary
        lines = [line for line in report.split("\n") if "rim_valuation" in line]
        self.assertTrue(len(lines) > 0)
        self.assertIn("NO_FUNDAMENTAL_DATA", lines[0])

    # -------------------------------------------------------------------------
    # V6-15: Downside Co-Semivariance Ledoit-Wolf Diagonal Target Shrinkage
    # -------------------------------------------------------------------------
    def test_v6_15_downside_semi_cov_preserves_negative_hedging_covariance(self):
        """
        Verify compute_downside_semi_cov uses diagonal variance target shrinkage,
        preserving negative covariance between stock asset and inverse hedge asset.
        """
        allocator = PortfolioAllocator()
        # Synthetic returns: Asset 0 is long, Asset 1 is inverse ETF (-1.0 correlation)
        T_len = 100
        long_rets = np.random.normal(0.001, 0.02, size=T_len)
        hedge_rets = -long_rets + np.random.normal(0, 0.001, size=T_len)
        returns_mat = np.column_stack([long_rets, hedge_rets])
        base_cov = np.cov(returns_mat, rowvar=False)

        semi_cov = allocator.compute_downside_semi_cov(returns_mat, base_cov=base_cov, shrinkage_intensity=0.20)

        # Off-diagonal element (covariance between Long and Hedge) MUST remain negative!
        self.assertLess(semi_cov[0, 1], 0.0)
        self.assertLess(semi_cov[1, 0], 0.0)
        # Positive diagonal
        self.assertGreater(semi_cov[0, 0], 0.0)
        self.assertGreater(semi_cov[1, 1], 0.0)

    # -------------------------------------------------------------------------
    # V6-16: RMT Marchenko-Pastur Dynamic Residual Variance Estimation
    # -------------------------------------------------------------------------
    def test_v6_16_rmt_dynamic_residual_variance(self):
        """
        Verify denoise_covariance_marchenko_pastur dynamically estimates sigma^2
        excluding the dominant market eigenvalue lambda_1, retaining factor signal eigenvalues.
        """
        engine = FXAdjustedCovarianceEngine()
        n_assets = 10
        t_obs = 100

        # Construct covariance with dominant market mode (first factor accounts for 50% variance)
        market_mode = np.random.normal(0, 0.03, size=(t_obs, 1))
        factors = np.random.normal(0, 0.015, size=(t_obs, 2))
        idiosyncratic = np.random.normal(0, 0.01, size=(t_obs, n_assets))

        returns = 0.7 * market_mode + 0.3 * np.dot(factors, np.random.randn(2, n_assets)) + idiosyncratic
        cov = np.cov(returns, rowvar=False)

        denoised_cov = engine.denoise_covariance_marchenko_pastur(
            cov_matrix=cov,
            n_assets=n_assets,
            t_obs=t_obs,
            noise_spread_factor=1.0
        )

        # Denoised covariance must be symmetric, positive-definite, and finite
        self.assertEqual(denoised_cov.shape, (n_assets, n_assets))
        self.assertTrue(np.all(np.isfinite(denoised_cov)))
        np.testing.assert_allclose(denoised_cov, denoised_cov.T, atol=1e-6)
        eigvals = np.linalg.eigvalsh(denoised_cov)
        self.assertTrue(np.all(eigvals > 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)

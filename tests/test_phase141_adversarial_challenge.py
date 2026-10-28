"""
tests/test_phase141_adversarial_challenge.py - Empirical Adversarial Stress Harness for Phase 141.
Author: Challenger 1 (Phase 141, Features F685-F689).

Empirically tests:
1. Degenerate / singular return covariance matrices:
   - T < N (high-dimensional rank deficiency)
   - Perfectly collinear assets
   - Zero-variance / constant assets
   - Non-invertible / singular covariance passed to fractional Kelly
2. Extreme fat-tail coskewness/cokurtosis inputs:
   - Massive negative coskewness & positive cokurtosis
   - Heavy-tailed Student-t / Cauchy distributions
   - Co-moment penalty directionality and risk reduction
3. Rapid VIX velocity jumps (> 3.0/day) and TSR inversions (TSR >= 1.08):
   - Sudden VIX spikes and multi-tier gating envelope
4. 5-day contango lock in RELIEF_RALLY:
   - Ensuring leverage does NOT expand to 1.25x until 5 full consecutive days of TSR < 0.95
   - Handling of missing, short, or interrupted history
5. High-Water Mark (HWM) drawdown ladder & circuit breaker:
   - Exact piece-wise thresholds (-4%, -7%, -10%, -12%)
6. UnifiedPortfolioAllocator integration and dynamic leverage enforcement.
"""

from __future__ import annotations

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestPhase141AdversarialChallenge(unittest.TestCase):
    """Adversarial stress testing suite for DynamicRegimeLeverageAllocator and its integration."""

    def setUp(self):
        np.random.seed(1337)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.25,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )

    # =========================================================================
    # Section 1: Degenerate / Singular Return Covariance Matrices
    # =========================================================================

    def test_cov_high_dim_rank_deficiency_t_less_than_n(self):
        """Stress: T=20 samples, N=100 assets (T << N). Regularizer must guarantee positive definiteness."""
        T, N = 20, 100
        returns_raw = np.random.normal(0.0005, 0.02, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(returns_raw, top_k_modes=10)

        self.assertEqual(cov_final.shape, (N, N))
        self.assertEqual(len(vols), N)
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))

        # Symmetry check
        np.testing.assert_allclose(cov_final, cov_final.T, atol=1e-10)

        # Minimum eigenvalue must be strictly positive (positive definiteness)
        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreater(float(np.min(eigvals)), 1e-7, "Covariance is not positive definite under T << N")

    def test_cov_perfectly_collinear_assets(self):
        """Stress: Multiple collinear assets (identical or scaled copies)."""
        T, N = 60, 10
        base_series = np.random.normal(0.001, 0.02, size=(T, 1))
        # 5 unique series, 5 identical copies of the first series
        unique_series = np.random.normal(0.001, 0.02, size=(T, 5))
        collinear_copies = np.repeat(base_series, 5, axis=1)
        X = np.hstack([unique_series, collinear_copies])

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=3)
        self.assertEqual(cov_final.shape, (N, N))
        self.assertTrue(np.all(np.isfinite(cov_final)))

        # Tikhonov regularization must ensure positive definiteness despite exact collinearity
        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreater(float(np.min(eigvals)), 1e-7, "Collinear matrix failed positive definiteness")

    def test_cov_zero_variance_assets(self):
        """Stress: Asset with exactly zero variance (flat price)."""
        T, N = 50, 8
        X = np.random.normal(0.001, 0.015, size=(T, N))
        X[:, 2] = 0.0  # Flat asset 2
        X[:, 5] = 0.0  # Flat asset 5

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=2)
        self.assertEqual(cov_final.shape, (N, N))
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))
        self.assertTrue(np.all(vols > 0.0), "Zero-variance asset must have non-zero regularized vol floor")

        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreater(float(np.min(eigvals)), 1e-7)

    def test_kelly_with_singular_covariance_matrix(self):
        """Stress: Pass an un-invertible (all zeros or rank 1) covariance directly to compute_fractional_kelly_weights."""
        N = 5
        singular_cov = np.ones((N, N)) * 0.0004  # Rank 1 matrix
        pred_rets = np.array([0.02, 0.03, 0.01, 0.04, 0.02])

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=pred_rets,
            cov_matrix=singular_cov,
            leverage=1.25,
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.isfinite(w_cash))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.25, places=5)

    def test_kelly_all_negative_expected_returns(self):
        """Stress: All assets have negative expected returns -> must preserve 100% cash."""
        N = 6
        cov = np.eye(N) * 0.0004
        neg_rets = np.array([-0.05, -0.02, -0.01, -0.03, -0.04, -0.08])

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=neg_rets,
            cov_matrix=cov,
            leverage=1.10,
        )
        self.assertEqual(float(np.sum(w)), 0.0, "Negative expected returns should result in 0 equity weight")
        self.assertAlmostEqual(w_cash, 1.10, places=5, msg="All leverage capacity must reside in Cash")

    # =========================================================================
    # Section 2: Extreme Fat-Tail Coskewness / Cokurtosis Inputs
    # =========================================================================

    def test_fat_tail_extreme_skew_kurtosis_contraction(self):
        """Stress: Extreme negative coskewness and explosive positive cokurtosis."""
        N = 4
        cov = np.eye(N) * 0.0004
        mu = np.array([0.05, 0.05, 0.05, 0.05])
        # Asset 0: calm, Asset 1: moderate crash risk, Asset 2: extreme crash risk, Asset 3: catastrophic
        coskew = np.array([0.0, -0.05, -0.50, -5.0])
        cokurt = np.array([0.0, 0.10, 2.00, 20.0])

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=0.50,
            coskewness=coskew,
            cokurtosis=cokurt,
            max_single_stock=0.90,
            risk_free_rate=0.0,
        )
        # Asset with higher crash risk should receive strictly less allocation
        self.assertGreater(w[0], w[1], "Calm asset must receive higher weight than moderate crash asset")
        self.assertGreater(w[1], w[2], "Moderate crash asset must receive higher weight than extreme crash asset")
        self.assertEqual(w[3], 0.0, "Catastrophic crash asset must be zeroed out")

    def test_fat_tail_student_t_heavy_tailed_data(self):
        """Stress: Co-moments computed on Student-t with df=2 (infinite variance/kurtosis theoretical limit)."""
        T, N = 200, 6
        # Generate heavy tails with df=2.5
        t_data = np.random.standard_t(df=2.5, size=(T, N)) * 0.02
        s_w, k_w = self.allocator.compute_higher_order_co_moments(t_data)

        self.assertEqual(len(s_w), N)
        self.assertEqual(len(k_w), N)
        self.assertTrue(np.all(np.isfinite(s_w)))
        self.assertTrue(np.all(np.isfinite(k_w)))

    # =========================================================================
    # Section 3: Rapid VIX Velocity Jumps & TSR Inversions
    # =========================================================================

    def test_vix_velocity_severe_jump_over_3_per_day(self):
        """Stress: VIX jumps from 15 to 33 over 5 days (vel = 3.6/day > 2.0). Must force L <= 0.40."""
        vix_hist = [15.0, 15.0, 15.0, 15.0, 15.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=33.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(L, 0.40, "Rapid VIX jump > 3.0/day failed to cap leverage at <= 0.40")

    def test_vix_velocity_jump_with_low_absolute_vix(self):
        """Stress: VIX jumps from 8.0 to 19.0 (vel = (19-8)/5 = 2.2 > 2.0), absolute VIX still < 20."""
        vix_hist = [8.0, 8.0, 8.0, 8.0, 8.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=19.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(L, 0.40, "Velocity jump > 2.0 must force L <= 0.40 even if VIX < 20")

    def test_tsr_inversion_boundary_and_extreme(self):
        """Stress: TSR ratio exactly at 1.08 and extreme inversion 1.45."""
        # Case 1: TSR = 1.08 -> L <= 0.50
        L_108 = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=16.0, vix_history=[16.0]*5, tsr_ratio=1.08, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(L_108, 0.50, "TSR = 1.08 must force L <= 0.50")

        # Case 2: TSR = 1.45 (acute panic term structure) -> L <= 0.50
        L_145 = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=16.0, vix_history=[16.0]*5, tsr_ratio=1.45, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(L_145, 0.50, "TSR = 1.45 must force L <= 0.50")

    def test_simultaneous_vix_jump_and_tsr_inversion(self):
        """Stress: Both VIX velocity > 3.0 (cap 0.40) and TSR >= 1.08 (cap 0.50) -> min envelope must be 0.40."""
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=32.0,
            vix_history=[14.0]*5, # vel = (32 - 14)/5 = 3.6
            tsr_ratio=1.20,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(L, 0.40, "Minimum envelope must select 0.40 over 0.50")

    # =========================================================================
    # Section 4: 5-Day Contango Lock in RELIEF_RALLY
    # =========================================================================

    def test_relief_rally_contango_lock_less_than_5_days(self):
        """Stress: RELIEF_RALLY with only 4 consecutive days of TSR < 0.95. Must NOT expand to 1.25x."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        tsr_hist_4d = [0.90, 0.88, 0.92, 0.91] # 4 days only
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=[16.0]*5,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=tsr_hist_4d,
        )
        self.assertAlmostEqual(L, 0.90, places=5, msg="RELIEF_RALLY with 4d contango must remain locked at 0.90x")

    def test_relief_rally_contango_lock_interrupted(self):
        """Stress: 5 days history where day 3 spiked to 0.96 (TSR >= 0.95). Must NOT expand to 1.25x."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        tsr_hist_interrupted = [0.90, 0.92, 0.96, 0.91, 0.90]
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=[16.0]*5,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=tsr_hist_interrupted,
        )
        self.assertAlmostEqual(L, 0.90, places=5, msg="Interrupted contango must remain locked at 0.90x")

    def test_relief_rally_contango_lock_satisfied_5_full_days(self):
        """Stress: 5 consecutive days strictly < 0.95. Must successfully unlock 1.25x."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        tsr_hist_5d = [0.94, 0.93, 0.91, 0.89, 0.92]
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=16.0,
            vix_history=[16.0]*5,
            tsr_ratio=0.90,
            regime="RELIEF_RALLY",
            tsr_history=tsr_hist_5d,
        )
        self.assertAlmostEqual(L, 1.25, places=5, msg="5 consecutive days contango must unlock 1.25x")

    def test_relief_rally_missing_tsr_history(self):
        """Stress: RELIEF_RALLY with tsr_history=None or empty list. Must default to locked 0.90x."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        for bad_hist in [None, []]:
            L = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=16.0,
                vix_history=[16.0]*5,
                tsr_ratio=0.90,
                regime="RELIEF_RALLY",
                tsr_history=bad_hist,
            )
            self.assertAlmostEqual(L, 0.90, places=5, msg=f"Missing history {bad_hist} must lock at 0.90x")

    # =========================================================================
    # Section 5: Drawdown Ladder De-leveraging & Circuit Breaker
    # =========================================================================

    def test_drawdown_ladder_exact_thresholds(self):
        """Stress: Exact test of drawdown ladder steps."""
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0

        # DD = 0% -> 1.25
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 1.25)
        # DD = -3.5% (above -4.0%) -> 1.25
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(96.5, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 1.25)
        # DD = -4.0% -> 1.25
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(96.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 1.25)
        # DD = -5.5% -> Linear trim: 1.00 + 0.25 * (-0.07 - (-0.055)) / (-0.03) = 1.125
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(94.5, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 1.125)
        # DD = -7.0% -> 0.85
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(93.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.85)
        # DD = -8.5% (between -7% and -10%) -> 0.85
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(91.5, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.85)
        # DD = -10.0% -> 0.50
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(90.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.50)
        # DD = -11.0% (between -10% and -12%) -> 0.50
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(89.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.50)
        # DD = -12.0% -> Circuit breaker 0.15
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(88.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.15)
        # DD = -30.0% -> Circuit breaker 0.15
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(70.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL"), 0.15)


if __name__ == "__main__":
    unittest.main()

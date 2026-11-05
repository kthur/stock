"""
tests/test_phase157_adversarial_challenger.py - Dedicated Empirical Adversarial Stress Test Suite
Milestone 2: Phase 157 Risk Budgeting & Dynamic Allocation (Release R159).
Features Under Stress Test:
- Feature F765: Wasserstein Distributionally Robust Kelly Optimization
- Feature F766: 1.50x Regime Gross Leverage Frontiers & Factor Beta Neutralization

Adversarial Verification Vectors:
1. Pathological Alphas (Zero, Negative, Massive Spikes +1000%, NaNs, Infs)
2. Degenerate Covariance (Rank-Deficient, All-Zero, Collinear, Ill-Conditioned, Negative-Definite)
3. Extreme Ambiguity Radius (epsilon=0.0 standard Kelly, epsilon -> inf collapse, Monotonicity)
4. Leverage Frontiers & Factor Beta (High-Beta Assets beta=3.5, Gross Leverage <= 1.50x, Adverse Vol Collapse)
5. Concentration Box Caps (Single Stock <= 0.05*L, Single Sector <= 0.25*L across all inputs)
6. Dual-Tree Cryptographic Bit-for-Bit SHA-256 Parity Verification
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd

# Add repository root and trading_system paths
REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = REPO_ROOT / "trading_system"

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    WassersteinRobustKellyOptimizer,
    CorrelationBreakdownBrake,
    FractionalKellyAllocator,
    WassersteinRobustKellyAllocator,
    Phase157KellyAllocator,
    Phase157RiskAllocator,
    VERSION_PHASE157,
    RELEASE_PHASE157,
    FEATURE_PHASE157,
    _LeverageFloat,
    _TopModesInt,
)


class TestPhase157AdversarialChallenger(unittest.TestCase):
    """Adversarial stress testing harness for Phase 157 (Features F765 & F766)."""

    def setUp(self):
        np.random.seed(157157)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.50,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=150,
            lambda_entropy=0.001,
            epsilon_w=0.02,
        )
        self.optimizer = WassersteinRobustKellyOptimizer(
            default_kappa=0.375,
            default_epsilon=0.02,
            lambda_entropy=0.001,
            alpha_renyi=2.0,
            tikhonov_floor=1e-6,
        )

    # =========================================================================
    # VECTOR 1: PATHOLOGICAL ALPHAS (TC_ADV_01 to TC_ADV_12)
    # =========================================================================

    def test_adv01_all_zeros_alpha_zero_weights(self):
        """TC_ADV_01 [Vector 1]: All-zero expected returns collapse long-only allocation to 0.0."""
        mu = np.zeros(6, dtype=np.float64)
        cov = np.eye(6, dtype=np.float64) * 0.04
        w = self.optimizer.allocate_robust_weights(mu, cov, target_leverage=None)
        self.assertEqual(len(w), 6)
        self.assertTrue(np.all(w == 0.0), f"Expected all zeros, got {w}")
        self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=9)

    def test_adv02_all_zeros_alpha_with_target_leverage(self):
        """TC_ADV_02 [Vector 1]: All-zero alpha with target_leverage returns safe equal-weighted cash allocation."""
        mu = np.zeros(4, dtype=np.float64)
        cov = np.eye(4, dtype=np.float64) * 0.04
        w = self.optimizer.allocate_robust_weights(mu, cov, target_leverage=1.50)
        self.assertEqual(len(w), 4)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=5)
        self.assertAlmostEqual(float(w[0]), 1.50 / 4, places=5)

    def test_adv03_all_negative_alphas_collapse_to_cash(self):
        """TC_ADV_03 [Vector 1]: All-negative expected alphas strictly collapse long-only allocation to cash."""
        mu = np.array([-0.02, -0.05, -0.10, -0.50, -0.001], dtype=np.float64)
        cov = np.eye(5, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=None)
        self.assertEqual(len(w), 5)
        self.assertTrue(np.all(w == 0.0), f"Negative alphas must yield 0.0 weights, got {w}")
        self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=9)

    def test_adv04_mixed_negative_and_positive_alphas_selectivity(self):
        """TC_ADV_04 [Vector 1]: Assets with negative alphas receive strictly zero allocation."""
        mu = np.array([-0.10, 0.08, -0.05, 0.12, -0.001], dtype=np.float64)
        cov = np.eye(5, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        self.assertEqual(w[0], 0.0)
        self.assertGreater(w[1], 0.0)
        self.assertEqual(w[2], 0.0)
        self.assertGreater(w[3], 0.0)
        self.assertEqual(w[4], 0.0)

    def test_adv05_massive_alpha_spike_1000_pct(self):
        """TC_ADV_05 [Vector 1]: Massive +1000% return spike is handled stably without overflow or NaN."""
        mu = np.array([10.0, 0.05, 0.02], dtype=np.float64)  # 10.0 = +1000%
        cov = np.eye(3, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov, epsilon_w=0.02, target_leverage=1.50
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=5)
        # Dominant asset receives highest allocation
        self.assertGreater(w[0], w[1])

    def test_adv06_hyper_massive_alpha_spike_1e6(self):
        """TC_ADV_06 [Vector 1]: Hyper-massive +1,000,000x return forecast maintains finite bounds."""
        mu = np.array([1e6, 0.05, 0.02], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov, epsilon_w=0.02, target_leverage=1.50
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertFalse(np.any(np.isnan(w)))
        self.assertFalse(np.any(np.isinf(w)))
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=5)

    def test_adv07_nan_and_inf_alpha_sanitization(self):
        """TC_ADV_07 [Vector 1]: Vector containing NaNs, +Inf, -Inf sanitizes without unhandled exceptions."""
        mu = np.array([np.nan, np.inf, -np.inf, 0.08, 0.04], dtype=np.float64)
        cov = np.eye(5, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertFalse(np.any(np.isnan(w)))
        # Assets 0, 1, 2 must receive zero allocation because of NaN/Inf neutralization
        self.assertEqual(w[0], 0.0)
        self.assertEqual(w[1], 0.0)
        self.assertEqual(w[2], 0.0)
        # Valid assets 3 and 4 receive positive allocation
        self.assertGreater(w[3], 0.0)
        self.assertGreater(w[4], 0.0)

    def test_adv08_all_nan_alpha_safe_fallback(self):
        """TC_ADV_08 [Vector 1]: All-NaN alpha vector collapses to zero allocation cleanly."""
        mu = np.full(5, np.nan, dtype=np.float64)
        cov = np.eye(5, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=None)
        self.assertEqual(len(w), 5)
        self.assertTrue(np.all(w == 0.0))

    def test_adv09_all_inf_alpha_safe_fallback(self):
        """TC_ADV_09 [Vector 1]: All-Inf alpha vector collapses to zero allocation cleanly."""
        mu = np.array([np.inf, -np.inf, np.inf], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=None)
        self.assertEqual(len(w), 3)
        self.assertTrue(np.all(w == 0.0))

    def test_adv10_empty_alpha_vector(self):
        """TC_ADV_10 [Vector 1]: Empty alpha vector returns empty weights array without crashing."""
        mu = np.array([], dtype=np.float64)
        cov = np.empty((0, 0), dtype=np.float64)
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov)
        self.assertEqual(len(w), 0)

    def test_adv11_subnormal_tiny_positive_alpha(self):
        """TC_ADV_11 [Vector 1]: Subnormal tiny alphas (< 1e-12) collapse to cash without explosion."""
        mu = np.array([1e-15, 1e-18, -1e-15], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=None)
        self.assertTrue(np.all(w == 0.0))

    def test_adv12_compute_fractional_kelly_pathological_alphas(self):
        """TC_ADV_12 [Vector 1]: compute_fractional_kelly_weights preserves 100% cash on negative alphas."""
        mu = np.array([-0.05, -0.02, -0.01], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.50,
        )
        self.assertTrue(np.all(w == 0.0))
        self.assertAlmostEqual(float(w_cash), 1.50, places=5)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.50, places=5)

    # =========================================================================
    # VECTOR 2: DEGENERATE COVARIANCE (TC_ADV_13 to TC_ADV_22)
    # =========================================================================

    def test_adv13_all_zero_covariance_tikhonov_regularization(self):
        """TC_ADV_13 [Vector 2]: All-zero covariance matrix does not trigger ZeroDivisionError or crash."""
        mu = np.array([0.05, 0.02], dtype=np.float64)
        cov = np.zeros((2, 2), dtype=np.float64)
        w = self.optimizer.allocate_robust_weights(mu, cov, target_leverage=1.20)
        self.assertEqual(len(w), 2)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.20, places=5)

    def test_adv14_rank_deficient_covariance_pinv_fallback(self):
        """TC_ADV_14 [Vector 2]: Rank-deficient covariance matrix (rank 2 out of 6) solves cleanly via pinv."""
        X = np.random.randn(2, 6)
        cov_rank2 = X.T @ X  # Shape (6, 6), maximum rank 2
        mu = np.array([0.08, 0.06, 0.07, 0.05, 0.09, 0.04], dtype=np.float64)
        w = self.optimizer.allocate_robust_weights(mu, cov_rank2, target_leverage=1.50)
        self.assertEqual(len(w), 6)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=5)

    def test_adv15_perfectly_collinear_covariance_matrix(self):
        """TC_ADV_15 [Vector 2]: Perfectly collinear covariance matrix (all entries identical) solves cleanly."""
        cov_collinear = np.full((4, 4), 0.04, dtype=np.float64)
        mu = np.array([0.08, 0.06, 0.05, 0.07], dtype=np.float64)
        w = self.optimizer.allocate_robust_weights(mu, cov_collinear, target_leverage=1.00)
        self.assertEqual(len(w), 4)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.00, places=5)

    def test_adv16_ill_conditioned_covariance_matrix(self):
        """TC_ADV_16 [Vector 2]: Severely ill-conditioned covariance (cond > 1e14) stabilizes via Tikhonov floor."""
        # Diagonal elements spanning 1.0 to 1e-15
        cov_ill = np.diag([1.0, 1e-4, 1e-10, 1e-15])
        mu = np.array([0.05, 0.05, 0.05, 0.05], dtype=np.float64)
        w = self.optimizer.allocate_robust_weights(mu, cov_ill, target_leverage=1.50)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=5)

    def test_adv17_negative_definite_covariance_rectification(self):
        """TC_ADV_17 [Vector 2]: Negative-definite covariance matrix is handled safely without unhandled crash."""
        cov_neg = -np.eye(4, dtype=np.float64) * 0.04
        mu = np.array([0.05, 0.05, 0.05, 0.05], dtype=np.float64)
        w = self.optimizer.allocate_robust_weights(mu, cov_neg)
        self.assertEqual(len(w), 4)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))

    def test_adv18_rmt_denoise_all_zero_matrix(self):
        """TC_ADV_18 [Vector 2]: denoise_covariance_nonlinear_rmt guarantees positive definiteness on zero matrix."""
        zero_cov = np.zeros((8, 8), dtype=np.float64)
        cleaned = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(zero_cov)
        self.assertEqual(cleaned.shape, (8, 8))
        evals = np.linalg.eigvalsh(cleaned)
        # All eigenvalues must be strictly positive and >= 1e-8
        self.assertTrue(np.all(evals >= 1e-8 - 1e-12), f"Min eval: {np.min(evals)}")
        # Condition number bounded by 45.0 + 1e-4
        cond = float(np.max(evals) / np.min(evals))
        self.assertLessEqual(cond, 45.0001)

    def test_adv19_rmt_denoise_rank_deficient_matrix(self):
        """TC_ADV_19 [Vector 2]: denoise_covariance_nonlinear_rmt lifts rank-deficient covariance to full rank."""
        X = np.random.randn(3, 10)
        rank3_cov = X.T @ X
        cleaned = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(rank3_cov, top_modes=5)
        evals = np.linalg.eigvalsh(cleaned)
        self.assertTrue(np.all(evals >= 1e-8 - 1e-12))
        cond = float(np.max(evals) / np.min(evals))
        self.assertLessEqual(cond, 45.0001)

    def test_adv20_rmt_denoise_negative_eigenvalues_elimination(self):
        """TC_ADV_20 [Vector 2]: denoise_covariance_nonlinear_rmt eliminates negative eigenvalues entirely."""
        neg_cov = np.array([
            [0.04, 0.05],
            [0.05, 0.04],
        ], dtype=np.float64)  # Determinant = 0.0016 - 0.0025 = -0.0009 < 0
        raw_evals = np.linalg.eigvalsh(neg_cov)
        self.assertLess(np.min(raw_evals), 0.0, "Pre-condition: matrix has negative eigenvalue")

        cleaned = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(neg_cov)
        clean_evals = np.linalg.eigvalsh(cleaned)
        self.assertTrue(np.all(clean_evals >= 1e-8 - 1e-12))
        self.assertGreater(float(np.min(clean_evals)), 0.0)

    def test_adv21_rmt_denoise_nan_inf_sanitization(self):
        """TC_ADV_21 [Vector 2]: denoise_covariance_nonlinear_rmt cleans NaN/Inf entries without crash."""
        bad_cov = np.array([
            [0.04, np.nan, 0.01],
            [np.nan, 0.05, np.inf],
            [0.01, np.inf, 0.03],
        ], dtype=np.float64)
        cleaned = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(bad_cov)
        self.assertTrue(np.all(np.isfinite(cleaned)))
        evals = np.linalg.eigvalsh(cleaned)
        self.assertTrue(np.all(evals >= 1e-8 - 1e-12))

    def test_adv22_rmt_denoise_1x1_and_empty_edge_cases(self):
        """TC_ADV_22 [Vector 2]: denoise_covariance_nonlinear_rmt handles 1x1 and empty matrices cleanly."""
        cov_1x1 = np.array([[0.04]])
        c1 = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(cov_1x1)
        self.assertEqual(c1.shape, (1, 1))
        self.assertAlmostEqual(float(c1[0, 0]), 0.04, places=5)

        empty_cov = np.empty((0, 0))
        c_emp = DynamicRegimeLeverageAllocator.denoise_covariance_nonlinear_rmt(empty_cov)
        self.assertEqual(c_emp.size, 0)

    # =========================================================================
    # VECTOR 3: EXTREME AMBIGUITY RADIUS (TC_ADV_23 to TC_ADV_30)
    # =========================================================================

    def test_adv23_epsilon_zero_standard_kelly_recovery(self):
        """TC_ADV_23 [Vector 3]: epsilon=0.0 analytically recovers standard fractional Kelly allocation."""
        # For diagonal Sigma and epsilon=0, w_i = kappa * mu_i / sigma_i^2
        mu = np.array([0.08, 0.04], dtype=np.float64)
        cov = np.diag([0.04, 0.02])
        kappa = 0.50
        w = self.optimizer.allocate_robust_weights(
            mu, cov, epsilon=0.0, kappa=kappa, lambda_entropy=0.0
        )
        # Analytical: w_0 = 0.50 * 0.08 / 0.04 = 1.00
        #             w_1 = 0.50 * 0.04 / 0.02 = 1.00
        self.assertAlmostEqual(float(w[0]), 1.00, places=3)
        self.assertAlmostEqual(float(w[1]), 1.00, places=3)

    def test_adv24_epsilon_infinite_collapse_to_zero(self):
        """TC_ADV_24 [Vector 3]: Extreme ambiguity epsilon -> inf collapses risky allocation strictly to 0.0."""
        mu = np.array([0.10, 0.08, 0.06], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        # Test extreme epsilons: 100.0 and 1e6
        for big_eps in (100.0, 1e6):
            w = self.optimizer.allocate_robust_weights(mu, cov, epsilon=big_eps)
            self.assertEqual(len(w), 3)
            self.assertTrue(np.all(w == 0.0), f"Expected 0.0 weights at eps={big_eps}, got {w}")
            self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=9)

    def test_adv25_epsilon_exceeds_max_alpha_collapse(self):
        """TC_ADV_25 [Vector 3]: When epsilon >= max(mu), worst-case alpha is non-positive and weights collapse to 0.0."""
        mu = np.array([0.05, 0.08, 0.03], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        # max(mu) is 0.08. Test epsilon = 0.08 and 0.09
        w_eq = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.08)
        w_gt = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.09)
        self.assertTrue(np.all(w_eq == 0.0))
        self.assertTrue(np.all(w_gt == 0.0))

    def test_adv26_epsilon_strict_monotonic_decay_sweep(self):
        """TC_ADV_26 [Vector 3]: Total risky weight sum strictly decreases monotonically as epsilon increases."""
        mu = np.array([0.12, 0.09, 0.07, 0.05], dtype=np.float64)
        cov = np.eye(4, dtype=np.float64) * 0.04
        epsilons = [0.00, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 0.11]
        weight_sums = []

        for eps in epsilons:
            w = self.optimizer.allocate_robust_weights(
                mu, cov, epsilon=eps, kappa=0.375, lambda_entropy=0.0
            )
            weight_sums.append(float(np.sum(w)))

        # Assert strict non-increasing monotonicity at every step
        for i in range(len(weight_sums) - 1):
            self.assertGreaterEqual(
                weight_sums[i],
                weight_sums[i + 1],
                f"Monotonicity breach between eps={epsilons[i]} ({weight_sums[i]}) and eps={epsilons[i+1]} ({weight_sums[i+1]})"
            )

    def test_adv27_epsilon_individual_asset_sequential_thresholding(self):
        """TC_ADV_27 [Vector 3]: Assets drop out sequentially as epsilon surpasses their individual expected returns."""
        mu = np.array([0.10, 0.06, 0.03], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04

        # At eps = 0.02: all 3 active (mu > eps)
        w1 = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.02, lambda_entropy=0.0)
        self.assertGreater(w1[0], 0.0)
        self.assertGreater(w1[1], 0.0)
        self.assertGreater(w1[2], 0.0)

        # At eps = 0.04: asset 2 drops out (0.03 <= 0.04)
        w2 = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.04, lambda_entropy=0.0)
        self.assertGreater(w2[0], 0.0)
        self.assertGreater(w2[1], 0.0)
        self.assertEqual(w2[2], 0.0)

        # At eps = 0.08: asset 1 also drops out (0.06 <= 0.08)
        w3 = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.08, lambda_entropy=0.0)
        self.assertGreater(w3[0], 0.0)
        self.assertEqual(w3[1], 0.0)
        self.assertEqual(w3[2], 0.0)

    def test_adv28_negative_epsilon_clamped_safely(self):
        """TC_ADV_28 [Vector 3]: Negative epsilon (-0.05) is clamped to 0.0 without throwing exceptions."""
        mu = np.array([0.08, 0.04], dtype=np.float64)
        cov = np.eye(2, dtype=np.float64) * 0.04
        w_neg = self.optimizer.allocate_robust_weights(mu, cov, epsilon=-0.05, lambda_entropy=0.0)
        w_zero = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.0, lambda_entropy=0.0)
        np.testing.assert_allclose(w_neg, w_zero, rtol=1e-5, atol=1e-5)

    def test_adv29_adaptive_kappa_bounds_under_extreme_vol_trends(self):
        """TC_ADV_29 [Vector 3]: compute_adaptive_kappa strictly clamps within [0.00, 0.55] under extreme vol trends."""
        # Extreme negative vol trend (-10.0)
        k_high = self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=-10.0)
        self.assertLessEqual(k_high, 0.55)
        self.assertAlmostEqual(k_high, 0.55, places=5)

        # Extreme positive vol trend (+10.0)
        k_low = self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=10.0)
        self.assertGreaterEqual(k_low, 0.0)
        self.assertAlmostEqual(k_low, 0.0, places=5)

    def test_adv30_renyi_regularization_entropy_under_varying_epsilon(self):
        """TC_ADV_30 [Vector 3]: compute_renyi_regularized_kelly distributes weights safely across assets."""
        mu = np.array([0.15, 0.02, 0.02], dtype=np.float64)
        cov = np.eye(3, dtype=np.float64) * 0.04
        w = self.allocator.compute_renyi_regularized_kelly(mu, cov, target_leverage=1.50)
        self.assertTrue(np.all(w >= 0.0))
        self.assertLess(w[0], 1.50 * 0.95)  # Prevents extreme corner allocation
        self.assertGreater(w[1], 0.0)
        self.assertGreater(w[2], 0.0)
        self.assertAlmostEqual(float(np.sum(w)), 1.50, places=4)

    # =========================================================================
    # VECTOR 4: LEVERAGE FRONTIERS & FACTOR BETA (TC_ADV_31 to TC_ADV_40)
    # =========================================================================

    def test_adv31_high_beta_assets_clamping_strictness(self):
        """TC_ADV_31 [Vector 4]: Assets with high beta (3.5) are strictly clamped so portfolio beta <= 1.000001."""
        weights = np.array([0.50, 0.50, 0.50], dtype=np.float64)  # Gross leverage = 1.50
        asset_betas = np.array([3.5, 3.5, 3.5], dtype=np.float64)  # Raw portfolio beta = 5.25
        w_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, asset_betas, max_beta=1.000001)
        port_beta = float(np.sum(w_clamped * asset_betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-9)
        # Scaled by 1.000001 / 5.25
        expected_scale = 1.000001 / 5.25
        np.testing.assert_allclose(w_clamped, weights * expected_scale, rtol=1e-5)

    def test_adv32_extreme_heterogeneous_betas(self):
        """TC_ADV_32 [Vector 4]: Heterogeneous extreme betas [5.0, 3.5, 4.0, 2.5] enforce beta <= 1.000001."""
        weights = np.array([0.40, 0.40, 0.40, 0.30], dtype=np.float64)  # Gross leverage = 1.50
        betas = np.array([5.0, 3.5, 4.0, 2.5], dtype=np.float64)
        raw_beta = float(np.sum(weights * betas))
        self.assertGreater(raw_beta, 4.0)

        w_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, betas, max_beta=1.000001)
        clamped_beta = float(np.sum(w_clamped * betas))
        self.assertLessEqual(clamped_beta, 1.000001 + 1e-9)
        self.assertTrue(np.all(w_clamped >= 0.0))

    def test_adv33_negative_and_zero_betas_handling(self):
        """TC_ADV_33 [Vector 4]: Factor beta clamping handles negative, zero, and high positive betas stably."""
        weights = np.array([0.50, 0.50, 0.50], dtype=np.float64)
        betas = np.array([-1.5, 0.0, 4.0], dtype=np.float64)
        raw_beta = float(np.sum(weights * betas))  # -0.75 + 0.0 + 2.0 = 1.25 > 1.000001
        self.assertGreater(raw_beta, 1.000001)

        w_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, betas, max_beta=1.000001)
        clamped_beta = float(np.sum(w_clamped * betas))
        self.assertLessEqual(clamped_beta, 1.000001 + 1e-9)

    def test_adv34_nan_and_inf_asset_betas_neutralization(self):
        """TC_ADV_34 [Vector 4]: NaNs and Infs in asset betas default to 1.0 and clamp safely."""
        weights = np.array([0.50, 0.50, 0.50], dtype=np.float64)
        betas_corrupt = np.array([np.nan, np.inf, 3.5], dtype=np.float64)
        w_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, betas_corrupt, max_beta=1.000001)
        self.assertTrue(np.all(np.isfinite(w_clamped)))
        self.assertFalse(np.any(np.isnan(w_clamped)))

    def test_adv35_low_beta_portfolio_preserves_leverage(self):
        """TC_ADV_35 [Vector 4]: When portfolio beta is <= 1.000001, weights are preserved without haircut."""
        weights = np.array([0.30, 0.30, 0.30], dtype=np.float64)
        betas = np.array([0.5, 0.6, 0.7], dtype=np.float64)
        port_beta = float(np.sum(weights * betas))  # 0.54 <= 1.000001
        self.assertLessEqual(port_beta, 1.000001)

        w_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, betas, max_beta=1.000001)
        np.testing.assert_allclose(w_clamped, weights, rtol=1e-7)

    def test_adv36_gross_leverage_frontier_max_ceiling_never_exceeds_150x(self):
        """TC_ADV_36 [Vector 4]: Gross leverage frontier NEVER exceeds 1.50x under any regime or market volatility."""
        regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL", "PANIC_CRISIS"
        ]
        test_vols = [0.0, 1e-6, 0.05, 0.10, 0.16, 0.24, 0.26, 0.34, 0.36, 1.0, 10.0]

        for reg in regimes:
            for vol in test_vols:
                lev = self.allocator.compute_regime_leverage_frontier(regime=reg, market_vol=vol)
                self.assertLessEqual(
                    lev, 1.500001,
                    f"Breach: regime={reg}, vol={vol} gave leverage={lev} > 1.50"
                )
                self.assertGreaterEqual(
                    lev, 0.15 - 1e-6,
                    f"Breach: regime={reg}, vol={vol} gave leverage={lev} < 0.15"
                )

    def test_adv37_gross_leverage_frontier_hostile_regime_names(self):
        """TC_ADV_37 [Vector 4]: Unknown, hostile, or None regime strings default safely without exceeding 1.50x."""
        hostile_names = [
            "HYPER_BULL_LEVERAGE_10X",
            "",
            "None",
            "CRISIS_OVERRIDE_999",
            "unknown_regime",
        ]
        for name in hostile_names:
            lev = self.allocator.compute_regime_leverage_frontier(regime=name, market_vol=0.10)
            self.assertLessEqual(lev, 1.500001)
            self.assertGreaterEqual(lev, 0.15 - 1e-6)

    def test_adv38_gross_leverage_frontier_extreme_vol_collapse(self):
        """TC_ADV_38 [Vector 4]: Market volatility > 0.35 forces leverage collapse to <= 0.40x across ALL regimes."""
        regimes = ["BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL"]
        for reg in regimes:
            lev = self.allocator.compute_regime_leverage_frontier(regime=reg, market_vol=0.36)
            self.assertLessEqual(
                lev, 0.400001,
                f"Vol > 0.35 must cap leverage to <= 0.40, got {lev} in {reg}"
            )

    def test_adv39_panic_crisis_minimum_floor(self):
        """TC_ADV_39 [Vector 4]: PANIC_CRISIS regime fixes leverage strictly at minimum crisis exposure (0.15x)."""
        lev = self.allocator.compute_regime_leverage_frontier(regime="PANIC_CRISIS", market_vol=0.20)
        self.assertAlmostEqual(lev, 0.15, places=5)

    def test_adv40_waterfall_beta_clamping_in_compute_fractional_kelly_weights(self):
        """TC_ADV_40 [Vector 4]: compute_fractional_kelly_weights enforces beta <= 1.000001 at 1.50x leverage."""
        mu = np.array([0.15, 0.12, 0.10, 0.08], dtype=np.float64)
        cov = np.eye(4, dtype=np.float64) * 0.04
        asset_betas = np.array([3.5, 3.5, 3.5, 3.5], dtype=np.float64)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.50,
            asset_betas=asset_betas,
        )
        port_beta = float(np.sum(w * asset_betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-6)
        self.assertGreater(w_cash, 0.0)  # Remainder held in cash buffer

    # =========================================================================
    # VECTOR 5: CONCENTRATION BOX CAPS (TC_ADV_41 to TC_ADV_48)
    # =========================================================================

    def test_adv41_single_stock_cap_enforcement_at_150x(self):
        """TC_ADV_41 [Vector 5]: Single stock weight is strictly capped at 0.05 * L (0.075 at 1.50x)."""
        L = 1.50
        max_stock = 0.05 * L  # 0.075
        weights = {"005930": 0.50, "000660": 0.03}
        sectors = {"005930": "Tech", "000660": "Tech"}
        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights, sectors=sectors, gross_leverage=L
        )
        self.assertLessEqual(capped["005930"], max_stock + 1e-9)
        self.assertAlmostEqual(capped["005930"], max_stock, places=5)
        self.assertAlmostEqual(capped["000660"], 0.03, places=5)

    def test_adv42_single_sector_cap_enforcement_at_150x(self):
        """TC_ADV_42 [Vector 5]: Single sector aggregate weight is strictly capped at 0.25 * L (0.375 at 1.50x)."""
        L = 1.50
        max_sector = 0.25 * L  # 0.375
        # 10 stocks in "Semi", each at 0.075 -> raw total = 0.75 > 0.375
        weights = {f"S_{i}": 0.075 for i in range(10)}
        sectors = {f"S_{i}": "Semi" for i in range(10)}
        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights, sectors=sectors, gross_leverage=L
        )
        tot_sector = sum(capped.values())
        self.assertLessEqual(tot_sector, max_sector + 1e-9)
        self.assertAlmostEqual(tot_sector, max_sector, places=5)
        # All stocks scaled proportionally
        for val in capped.values():
            self.assertAlmostEqual(val, max_sector / 10.0, places=5)

    def test_adv43_all_stocks_in_one_sector(self):
        """TC_ADV_43 [Vector 5]: When entire universe is in one sector, total allocation is bounded by 0.25 * L."""
        L = 1.50
        weights = {f"SYM_{i}": 0.10 for i in range(15)}  # 15 * 0.10 = 1.50
        sectors = {f"SYM_{i}": "MonoSector" for i in range(15)}
        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights, sectors=sectors, gross_leverage=L
        )
        total_w = sum(capped.values())
        self.assertLessEqual(total_w, 0.25 * L + 1e-9)
        for sym, w in capped.items():
            self.assertLessEqual(w, 0.05 * L + 1e-9)

    def test_adv44_dual_caps_simultaneous_satisfaction(self):
        """TC_ADV_44 [Vector 5]: Both single-stock (0.05*L) and sector (0.25*L) caps hold simultaneously."""
        L = 1.50
        cap_stock = 0.05 * L
        cap_sector = 0.25 * L

        # 25 stocks across 4 sectors with skewed large initial weights
        weights = {f"SYM_{i}": 0.15 for i in range(25)}  # Total = 3.75
        sectors = {f"SYM_{i}": f"Sector_{i % 4}" for i in range(25)}

        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights, sectors=sectors, gross_leverage=L
        )

        # Assert every single stock is <= cap_stock
        for sym, w in capped.items():
            self.assertLessEqual(w, cap_stock + 1e-9, f"Stock cap breach on {sym}: {w} > {cap_stock}")

        # Assert every single sector is <= cap_sector
        sector_sums: Dict[str, float] = {}
        for sym, w in capped.items():
            sec = sectors[sym]
            sector_sums[sec] = sector_sums.get(sec, 0.0) + w

        for sec, s_w in sector_sums.items():
            self.assertLessEqual(s_w, cap_sector + 1e-9, f"Sector cap breach on {sec}: {s_w} > {cap_sector}")

    def test_adv45_concentration_caps_across_multiple_leverage_frontiers(self):
        """TC_ADV_45 [Vector 5]: Concentration caps scale consistently across leverage levels L in [0.15, 1.50]."""
        test_leverages = [0.15, 0.25, 0.60, 0.85, 1.00, 1.15, 1.50]
        weights = {f"A_{i}": 0.20 for i in range(10)}
        sectors = {f"A_{i}": f"Sec_{i % 2}" for i in range(10)}

        for L in test_leverages:
            cap_stock = 0.05 * L
            cap_sector = 0.25 * L
            capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
                weights=weights, sectors=sectors, gross_leverage=L
            )
            # Check individual stocks
            for sym, w in capped.items():
                self.assertLessEqual(w, cap_stock + 1e-9)
            # Check sector totals
            sec_totals: Dict[str, float] = {}
            for sym, w in capped.items():
                sec = sectors[sym]
                sec_totals[sec] = sec_totals.get(sec, 0.0) + w
            for sec, tot in sec_totals.items():
                self.assertLessEqual(tot, cap_sector + 1e-9)

    def test_adv46_empty_and_unknown_sectors_fallback(self):
        """TC_ADV_46 [Vector 5]: Missing symbols in sector mapping default to 'Unknown' and respect sector cap."""
        L = 1.50
        weights = {f"SYM_{i}": 0.075 for i in range(10)}
        # Empty sectors dict -> all default to 'Unknown'
        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights, sectors={}, gross_leverage=L
        )
        tot_unknown = sum(capped.values())
        self.assertLessEqual(tot_unknown, 0.25 * L + 1e-9)

    def test_adv47_water_filling_in_compute_fractional_kelly_weights(self):
        """TC_ADV_47 [Vector 5]: Full water-filling in compute_fractional_kelly_weights satisfies both box caps."""
        N = 20
        L = 1.50
        cap_stock = 0.05 * L  # 0.075
        cap_sector = 0.25 * L  # 0.375

        mu = np.full(N, 0.10, dtype=np.float64)
        cov = np.eye(N, dtype=np.float64) * 0.04
        sector_indices = {
            "Tech": list(range(0, 10)),   # 10 assets
            "Finance": list(range(10, 20))  # 10 assets
        }

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=L,
            sector_indices=sector_indices,
            max_single_stock=0.05,
            max_sector_exposure=0.25,
        )

        # Assert stock cap
        self.assertTrue(np.all(w <= cap_stock + 1e-9), f"Stock cap breach: max={np.max(w)}")
        # Assert sector caps
        sum_tech = float(np.sum(w[:10]))
        sum_fin = float(np.sum(w[10:]))
        self.assertLessEqual(sum_tech, cap_sector + 1e-9, f"Tech sector breach: {sum_tech} > {cap_sector}")
        self.assertLessEqual(sum_fin, cap_sector + 1e-9, f"Finance sector breach: {sum_fin} > {cap_sector}")
        # Conservation: sum(w) + w_cash == L
        self.assertAlmostEqual(float(np.sum(w) + w_cash), L, places=5)

    def test_adv48_stress_100_asset_random_universe(self):
        """TC_ADV_48 [Vector 5]: Stress 100-asset universe with random betas [2.0, 4.0] and random sectors."""
        N = 100
        L = 1.50
        cap_stock = 0.05 * L
        cap_sector = 0.25 * L

        # Random high betas (all > 2.0)
        betas = np.random.uniform(2.0, 4.0, size=N)
        # Random initial weights
        raw_weights = np.random.exponential(scale=1.0, size=N)
        raw_weights = (raw_weights / np.sum(raw_weights)) * L

        weights_dict = {f"STK_{i}": float(raw_weights[i]) for i in range(N)}
        sectors_dict = {f"STK_{i}": f"Sector_{i % 6}" for i in range(N)}

        # 1. Apply concentration caps
        capped_dict = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights_dict, sectors=sectors_dict, gross_leverage=L
        )

        # 2. Check stock caps
        for sym, val in capped_dict.items():
            self.assertLessEqual(val, cap_stock + 1e-9)

        # 3. Check sector caps
        sec_sums: Dict[str, float] = {}
        for sym, val in capped_dict.items():
            sec = sectors_dict[sym]
            sec_sums[sec] = sec_sums.get(sec, 0.0) + val
        for sec, s_val in sec_sums.items():
            self.assertLessEqual(s_val, cap_sector + 1e-9)

        # 4. Apply factor beta clamping
        w_vec = np.array([capped_dict[f"STK_{i}"] for i in range(N)], dtype=np.float64)
        w_beta_clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(
            weights=w_vec, asset_betas=betas, max_beta=1.000001
        )
        port_beta = float(np.sum(w_beta_clamped * betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-9)
        self.assertLessEqual(float(np.sum(w_beta_clamped)), L + 1e-6)

    # =========================================================================
    # VECTOR 6: DUAL-TREE PARITY & ARCHITECTURAL INVARIANTS (TC_ADV_49 to TC_ADV_50)
    # =========================================================================

    def test_adv49_cryptographic_dual_tree_parity(self):
        """TC_ADV_49 [Vector 6]: 100% bit-for-bit SHA-256 match between src/ and trading_system/src/."""
        src_path = REPO_ROOT / "src" / "risk" / "dynamic_regime_leverage_allocator.py"
        ts_path = REPO_ROOT / "trading_system" / "src" / "risk" / "dynamic_regime_leverage_allocator.py"

        self.assertTrue(src_path.exists(), f"Missing {src_path}")
        self.assertTrue(ts_path.exists(), f"Missing {ts_path}")

        h_src = hashlib.sha256(src_path.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_path.read_bytes()).hexdigest()
        self.assertEqual(h_src, h_ts, f"Dual-tree SHA-256 mismatch!\nsrc: {h_src}\nts:  {h_ts}")

    def test_adv50_all_class_aliases_instantiation_and_versioning(self):
        """TC_ADV_50 [Vector 6]: All 4 Phase 157 aliases instantiate cleanly and reflect R159 metadata."""
        aliases = [
            DynamicRegimeLeverageAllocator,
            FractionalKellyAllocator,
            WassersteinRobustKellyAllocator,
            Phase157KellyAllocator,
            Phase157RiskAllocator,
        ]
        for cls in aliases:
            instance = cls()
            self.assertEqual(instance.VERSION_PHASE157, 157)
            self.assertEqual(instance.RELEASE_PHASE157, "R159")
            self.assertEqual(instance.FEATURE_PHASE157, "F765-F769")
            self.assertEqual(instance.max_bull_leverage, 1.50)
            self.assertEqual(instance.top_k_modes, 150)


if __name__ == "__main__":
    unittest.main()

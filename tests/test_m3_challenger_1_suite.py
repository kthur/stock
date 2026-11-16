"""
Milestone 3 Challenger 1 Adversarial Edge-Case Test Suite
Target Modules:
  - src/ai/ensemble_scorer.py (compute_entropy_softmax_weights)
  - src/risk/unified_portfolio_allocator.py (compute_factor_risk_contributions)
Invariant:
  - synthetic_rows == 0 strictly verified as native Python int 0

This suite executes extreme, degenerate, and boundary-value stress tests to
empirically challenge the numerical stability, robustness, and mathematical invariants
of Milestone 3 implementations.
"""

import json
import math
import unittest
import numpy as np

from src.ai.ensemble_scorer import compute_entropy_softmax_weights, EnsembleScoringEngine
from src.risk.unified_portfolio_allocator import (
    compute_factor_risk_contributions,
    calculate_factor_risk_parity_weights,
    UnifiedPortfolioAllocator,
)


class TestAdversarialEntropySoftmaxWeights(unittest.TestCase):
    """
    Adversarial stress tests for continuous entropy-regularized softmax strategy weighting.
    Focuses on extreme Sharpe values, asymptotic temperature limits, high strategy counts,
    dense crowding monotonicity, and floor inversion immunity.
    """

    def setUp(self):
        np.random.seed(42)

    def test_extreme_sharpe_magnitudes(self):
        """
        Sharpe ratios with extreme magnitudes (+1000.0, -1000.0, +1e6, -1e6).
        Must be clipped safely to [-3.0, 3.0] and produce normalized weights summing to 1.0.
        """
        base = {"strat_A": 0.5, "strat_B": 0.5}
        sharpes = {"strat_A": 1000.0, "strat_B": -1000.0}

        w = compute_entropy_softmax_weights(base, sharpes, temperature=1.0)
        self.assertTrue(all(np.isfinite(list(w.values()))))
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
        self.assertGreater(w["strat_A"], w["strat_B"])

        # Astronomical Sharpe
        sharpes_mega = {"strat_A": 1e9, "strat_B": -1e9}
        w_mega = compute_entropy_softmax_weights(base, sharpes_mega, temperature=1.0)
        self.assertTrue(all(np.isfinite(list(w_mega.values()))))
        self.assertAlmostEqual(sum(w_mega.values()), 1.0, places=9)
        # Bounded within [min_weight, max_weight]
        self.assertAlmostEqual(w["strat_A"], w_mega["strat_A"], places=7)
        self.assertAlmostEqual(w["strat_B"], w_mega["strat_B"], places=7)

    def test_infinite_and_nan_sharpe_sanitization(self):
        """
        Sharpe ratios with +inf, -inf, NaN, None, and unparseable values.
        Must sanitize without throwing exceptions or generating non-finite outputs.
        """
        base = {
            "strat_posinf": 0.2,
            "strat_neginf": 0.2,
            "strat_nan": 0.2,
            "strat_none": 0.2,
            "strat_valid": 0.2,
        }
        sharpes = {
            "strat_posinf": float("inf"),
            "strat_neginf": float("-inf"),
            "strat_nan": float("nan"),
            "strat_none": None,
            "strat_valid": 1.5,
        }

        w = compute_entropy_softmax_weights(base, sharpes, temperature=1.0)
        self.assertEqual(len(w), 5)
        self.assertTrue(all(np.isfinite(list(w.values()))))
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
        # +inf clips to +3.0, valid is 1.5, nan/none becomes 0.0, -inf clips to -3.0
        self.assertGreater(w["strat_posinf"], w["strat_valid"])
        self.assertGreater(w["strat_valid"], w["strat_nan"])
        self.assertAlmostEqual(w["strat_nan"], w["strat_none"], places=9)
        self.assertGreater(w["strat_nan"], w["strat_neginf"])

    def test_mixed_extreme_outliers(self):
        """
        Universe of 10 strategies with wildly mixed extreme values across Sharpe, IC, and Crowding.
        """
        strategies = [f"s_{i}" for i in range(10)]
        base = {s: 0.10 for s in strategies}
        sharpes = {
            "s_0": 1e6, "s_1": -1e6, "s_2": float("nan"), "s_3": float("inf"),
            "s_4": float("-inf"), "s_5": 0.0, "s_6": 2.5, "s_7": -2.5,
            "s_8": 0.5, "s_9": -0.5
        }
        ics = {
            "s_0": float("inf"), "s_1": -100.0, "s_2": float("nan"), "s_3": 0.05,
            "s_4": -0.05, "s_5": 0.99, "s_6": -0.99, "s_7": None,
            "s_8": 10.0, "s_9": -10.0
        }
        crowd = {
            "s_0": 100.0, "s_1": -50.0, "s_2": float("nan"), "s_3": 1.0,
            "s_4": 0.0, "s_5": 0.5, "s_6": float("inf"), "s_7": float("-inf"),
            "s_8": None, "s_9": 0.2
        }

        w = compute_entropy_softmax_weights(base, sharpes, ic_dict=ics, crowding_dict=crowd)
        self.assertEqual(len(w), 10)
        self.assertTrue(all(np.isfinite(list(w.values()))))
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
        for val in w.values():
            self.assertTrue(val >= 0.005 - 1e-9)
            self.assertTrue(val <= 0.25 + 1e-9)

    def test_extreme_temperatures_dirac_delta(self):
        """
        Asymptotic limit: T -> 1e-6 (Dirac delta / argmax approximation).
        The highest utility strategy should receive maximal allowed weight (eff_max).
        The implementation clamps T = max(temperature, 1e-4) to guarantee numerical stability.
        """
        base = {"leader": 0.5, "laggard": 0.5}
        sharpes = {"leader": 2.0, "laggard": -1.0}

        for low_T in [1e-6, 1e-12, 0.0, -1.0]:
            w = compute_entropy_softmax_weights(base, sharpes, temperature=low_T)
            self.assertTrue(all(np.isfinite(list(w.values()))))
            self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
            # leader dominates, laggard clamped to eff_min
            self.assertGreater(w["leader"], 0.99)
            self.assertLess(w["laggard"], 0.01)

    def test_extreme_temperatures_uniform_limit(self):
        """
        Asymptotic limit: T -> 1000.0 (maximum entropy / uniform distribution).
        Utilities differences vanish: (u_i - max(u)) / T -> 0 => weights -> 1/K.
        """
        base = {"strat_A": 0.2, "strat_B": 0.3, "strat_C": 0.5}
        sharpes = {"strat_A": 3.0, "strat_B": 0.0, "strat_C": -3.0}

        for high_T in [1000.0, 50000.0]:
            w = compute_entropy_softmax_weights(base, sharpes, temperature=high_T)
            self.assertTrue(all(np.isfinite(list(w.values()))))
            self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
            # For 3 strategies, each should be very close to 1/3
            for val in w.values():
                self.assertAlmostEqual(val, 1.0 / 3.0, delta=0.01)

    def test_high_strategy_counts_100_and_500(self):
        """
        High strategy counts: K=100 and K=500.
        Verifies dynamic feasibility bounds:
        For K=100, min_weight=0.005 satisfies min_weight * K = 0.5 <= 1.0.
        For K=500, min_weight=0.005 would exceed 1.0, so eff_min is dynamically clamped to 1/K = 0.002.
        """
        # Test K = 100
        K100 = 100
        base100 = {f"s_{i}": 1.0 / K100 for i in range(K100)}
        sharpes100 = {f"s_{i}": float(np.sin(i)) * 2.5 for i in range(K100)}
        crowd100 = {f"s_{i}": float((i % 10) / 10.0) for i in range(K100)}
        w100 = compute_entropy_softmax_weights(base100, sharpes100, crowding_dict=crowd100)

        self.assertEqual(len(w100), K100)
        self.assertTrue(all(np.isfinite(list(w100.values()))))
        self.assertAlmostEqual(sum(w100.values()), 1.0, places=9)
        self.assertTrue(all(v >= 0.005 - 1e-9 for v in w100.values()))
        self.assertTrue(all(v <= 0.25 + 1e-9 for v in w100.values()))

        # Test K = 500 (with default min_weight)
        K500 = 500
        base500 = {f"s_{i}": 1.0 / K500 for i in range(K500)}
        sharpes500 = {f"s_{i}": float(np.cos(i)) * 2.0 for i in range(K500)}
        w500 = compute_entropy_softmax_weights(base500, sharpes500)
        self.assertEqual(len(w500), K500)
        self.assertTrue(all(np.isfinite(list(w500.values()))))
        self.assertAlmostEqual(sum(w500.values()), 1.0, places=9)

        # Test K = 500 with scaled min_weight
        w500_scaled = compute_entropy_softmax_weights(base500, sharpes500, min_weight=0.0005)
        self.assertEqual(len(w500_scaled), K500)
        self.assertTrue(all(np.isfinite(list(w500_scaled.values()))))
        self.assertAlmostEqual(sum(w500_scaled.values()), 1.0, places=9)
        self.assertTrue(all(v >= 0.0005 - 1e-9 for v in w500_scaled.values()))

    def test_dense_crowding_grid_200_points_monotonicity(self):
        """
        Dense crowding grid test: verify Delta w_i / Delta Crowd_i < 0 across 200 grid points.
        Evaluates crowd in [0.0, 1.0] over 201 samples (200 step intervals).
        """
        base = {"strat_test": 0.4, "strat_other1": 0.3, "strat_other2": 0.3}
        sharpes = {"strat_test": 1.0, "strat_other1": 1.0, "strat_other2": 1.0}
        crowd_grid = np.linspace(0.0, 1.0, 201)

        weights = []
        for c in crowd_grid:
            w = compute_entropy_softmax_weights(
                base,
                sharpes,
                crowding_dict={"strat_test": float(c), "strat_other1": 0.1, "strat_other2": 0.1},
                beta=0.40,
                temperature=1.0
            )
            weights.append(w["strat_test"])

        weights = np.array(weights)
        diffs = np.diff(weights)

        # Monotonicity check: where weight is above lower floor, diff must be strictly negative
        active_mask = weights[:-1] > 0.0055
        self.assertTrue(np.all(diffs[active_mask] < 0.0), "Weight failed strict monotonic decrease on 200-point crowding grid.")
        # Under no circumstance should weight increase with crowding
        self.assertFalse(np.any(diffs > 1e-12), "Weight increased with crowding penalty on 200-point grid.")

    def test_floor_inversion_immunity_100x_leader_surge(self):
        """
        Verify floor inversion immunity under a 100x leader Sharpe surge.
        Legacy defect mechanism:
          _vmin_floor = _vmax * 0.05
          Surge in leader's Sharpe inflated _vmax, raising the floor and inadvertently
          boosting decaying/crowded models by up to 10x.
        New continuous softmax guarantee:
          Surge in leader's Sharpe increases max(u), causing (u_crowded - max(u))/T
          to decrease, strictly reducing or preserving crowded strategy's allocation.
        """
        base = {
            "leader_A": 0.4,
            "crowded_B": 0.3,
            "neutral_C": 0.3,
        }
        crowd = {
            "leader_A": 0.05,
            "crowded_B": 0.95,
            "neutral_C": 0.20,
        }

        # Baseline: leader has normal Sharpe 1.0
        sharpes_base = {"leader_A": 1.0, "crowded_B": -1.0, "neutral_C": 0.5}
        w_base = compute_entropy_softmax_weights(base, sharpes_base, crowding_dict=crowd)

        # 100x Leader Sharpe surge: 1.0 -> 100.0
        sharpes_100x = {"leader_A": 100.0, "crowded_B": -1.0, "neutral_C": 0.5}
        w_surged = compute_entropy_softmax_weights(base, sharpes_100x, crowding_dict=crowd)

        # 1. Leader weight must increase or reach max cap
        self.assertGreaterEqual(w_surged["leader_A"], w_base["leader_A"])
        # 2. Crowded model B MUST NOT INCREASE in weight under leader surge (Floor Inversion Immunity)
        self.assertLessEqual(
            w_surged["crowded_B"],
            w_base["crowded_B"] + 1e-12,
            f"Floor inversion detected! Crowded model weight increased: {w_base['crowded_B']} -> {w_surged['crowded_B']}"
        )


class TestAdversarialFactorRiskContributions(unittest.TestCase):
    """
    Adversarial stress tests for factor risk decomposition and Euler identity.
    Focuses on near-zero variance portfolios, defective/singular covariance matrices,
    degenerate factor loadings, 1D/2D idiosyncratic structures, and 500-portfolio randomized stress.
    """

    def setUp(self):
        np.random.seed(42)

    def test_near_zero_variance_portfolios_zero_weights(self):
        """
        Portfolio with w = 0 (total_var = 0.0 <= 1e-12).
        Must return zeros for MFRC and PFRC, and IRR = 1.0 without ZeroDivisionError.
        """
        N, K = 10, 3
        w = np.zeros(N)
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.04
        D_idio = np.ones(N) * 0.01

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        self.assertEqual(len(mfrc), K)
        self.assertEqual(len(pfrc), K)
        np.testing.assert_allclose(mfrc, np.zeros(K))
        np.testing.assert_allclose(pfrc, np.zeros(K))
        self.assertEqual(irr, 1.0)
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)

    def test_near_zero_variance_portfolios_tiny_norm(self):
        """
        Portfolio with tiny norm ||w|| = 1e-9, such that w^T Sigma w <= 1e-15.
        Must trigger the total_var <= 1e-12 branch cleanly.
        """
        N, K = 5, 2
        w = np.full(N, 1e-9)
        B = np.ones((N, K))
        Omega_F = np.eye(K) * 1e-4
        D_idio = np.full(N, 1e-4)

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(mfrc, np.zeros(K))
        np.testing.assert_allclose(pfrc, np.zeros(K))
        self.assertEqual(irr, 1.0)

    def test_near_zero_variance_nullspace_exposure(self):
        """
        Portfolio where w is orthogonal to B (B^T w = 0) and D_idio = 0.
        Total variance is strictly zero, must return safe fallback.
        """
        N, K = 4, 1
        # B is all ones, w sums to 0
        B = np.ones((N, K))
        w = np.array([1.0, -1.0, 1.0, -1.0])  # B.T @ w = 0
        Omega_F = np.array([[0.05]])
        D_idio = np.zeros(N)

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        np.testing.assert_allclose(mfrc, np.zeros(K))
        np.testing.assert_allclose(pfrc, np.zeros(K))
        self.assertEqual(irr, 1.0)

    def test_defective_omega_negative_eigenvalues(self):
        """
        Defective factor covariance matrix with negative eigenvalues (non-PSD).
        Must be projected onto the positive semi-definite cone via eigenvalue thresholding (max(val, 0)).
        Euler identity sum(PFRC) + IRR == 1.0 must still hold.
        """
        N, K = 8, 3
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        # Construct non-PSD matrix with negative eigenvalues
        Omega_defective = np.array([
            [-5.0,  1.0,  0.5],
            [ 1.0,  2.0, -0.5],
            [ 0.5, -0.5, -3.0],
        ])
        D_idio = np.ones(N) * 0.02

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_defective, D_idio)
        self.assertTrue(all(np.isfinite(mfrc)))
        self.assertTrue(all(np.isfinite(pfrc)))
        self.assertTrue(np.isfinite(irr))
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)

    def test_singular_omega_rank_deficient_and_zero(self):
        """
        Singular factor covariance: rank-1 matrix v v^T and all-zeros matrix 0.
        """
        N, K = 10, 4
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        D_idio = np.ones(N) * 0.05

        # Rank-1 Omega
        v = np.array([1.0, 2.0, 3.0, 4.0])
        Omega_rank1 = np.outer(v, v)
        mfrc1, pfrc1, irr1 = compute_factor_risk_contributions(w, B, Omega_rank1, D_idio)
        self.assertAlmostEqual(float(np.sum(pfrc1) + irr1), 1.0, places=9)

        # All-zero Omega
        Omega_zero = np.zeros((K, K))
        mfrc0, pfrc0, irr0 = compute_factor_risk_contributions(w, B, Omega_zero, D_idio)
        np.testing.assert_allclose(mfrc0, np.zeros(K))
        np.testing.assert_allclose(pfrc0, np.zeros(K))
        self.assertAlmostEqual(irr0, 1.0, places=9)
        self.assertAlmostEqual(float(np.sum(pfrc0) + irr0), 1.0, places=9)

    def test_random_degenerate_factor_loadings(self):
        """
        Degenerate factor loadings B:
        1. B = 0 (all zeros).
        2. Columns of all zeros (unloaded factors).
        3. Collinear factor columns (redundant factors).
        """
        N, K = 12, 3
        w = np.ones(N) / N
        Omega_F = np.eye(K) * 0.04
        D_idio = np.ones(N) * 0.03

        # Case 1: B = 0
        B_zero = np.zeros((N, K))
        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B_zero, Omega_F, D_idio)
        np.testing.assert_allclose(mfrc, np.zeros(K))
        np.testing.assert_allclose(pfrc, np.zeros(K))
        self.assertAlmostEqual(irr, 1.0, places=9)
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)

        # Case 2: Unloaded factor in column 1
        B_unloaded = np.random.randn(N, K)
        B_unloaded[:, 1] = 0.0
        mfrc_u, pfrc_u, irr_u = compute_factor_risk_contributions(w, B_unloaded, Omega_F, D_idio)
        self.assertAlmostEqual(float(mfrc_u[1]), 0.0, places=9)
        self.assertAlmostEqual(float(pfrc_u[1]), 0.0, places=9)
        self.assertAlmostEqual(float(np.sum(pfrc_u) + irr_u), 1.0, places=9)

        # Case 3: Collinear factor columns (col 2 = 3.0 * col 0)
        B_collinear = np.random.randn(N, K)
        B_collinear[:, 2] = 3.0 * B_collinear[:, 0]
        mfrc_c, pfrc_c, irr_c = compute_factor_risk_contributions(w, B_collinear, Omega_F, D_idio)
        self.assertTrue(all(np.isfinite(mfrc_c)))
        self.assertTrue(all(np.isfinite(pfrc_c)))
        self.assertAlmostEqual(float(np.sum(pfrc_c) + irr_c), 1.0, places=9)

    def test_1d_vs_2d_idiosyncratic_structures(self):
        """
        Idiosyncratic risk as 1D array of shape (N,) vs 2D diagonal matrix of shape (N, N).
        Both must produce mathematically identical risk contributions.
        """
        N, K = 15, 3
        w = np.random.uniform(0.01, 0.1, size=N)
        w /= np.sum(w)
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.05
        d_vec = np.random.uniform(0.01, 0.05, size=N)
        D_mat = np.diag(d_vec)

        mfrc_1d, pfrc_1d, irr_1d = compute_factor_risk_contributions(w, B, Omega_F, d_vec)
        mfrc_2d, pfrc_2d, irr_2d = compute_factor_risk_contributions(w, B, Omega_F, D_mat)

        np.testing.assert_allclose(mfrc_1d, mfrc_2d, atol=1e-12)
        np.testing.assert_allclose(pfrc_1d, pfrc_2d, atol=1e-12)
        self.assertAlmostEqual(irr_1d, irr_2d, places=12)

    def test_negative_diagonal_idiosyncratic_clamping(self):
        """
        Negative idiosyncratic variance values (e.g. from numerical noise in sample covariance).
        Must be clamped to 0.0 without producing imaginary numbers or NaN variance.
        """
        N, K = 5, 2
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.02
        D_neg = np.array([-0.05, 0.01, -0.02, 0.03, -0.01])

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_neg)
        self.assertTrue(all(np.isfinite(mfrc)))
        self.assertTrue(all(np.isfinite(pfrc)))
        self.assertTrue(np.isfinite(irr))
        self.assertTrue(irr >= 0.0)
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)

    def test_non_finite_inputs_sanitization(self):
        """
        Weights, loadings, or variances containing NaNs, Infs, or -Infs.
        np.nan_to_num sanitization must catch them all and maintain finite output.
        """
        N, K = 6, 2
        w = np.array([0.2, float("nan"), 0.2, float("inf"), float("-inf"), 0.2])
        B = np.random.randn(N, K)
        B[0, 0] = float("nan")
        B[1, 1] = float("inf")
        Omega_F = np.array([[0.04, float("nan")], [float("nan"), 0.04]])
        D_idio = np.array([0.01, float("inf"), 0.01, float("nan"), 0.01, 0.01])

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
        self.assertTrue(all(np.isfinite(mfrc)))
        self.assertTrue(all(np.isfinite(pfrc)))
        self.assertTrue(np.isfinite(irr))
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)

    def test_euler_identity_500_randomized_portfolios(self):
        """
        Comprehensive stress test: verify Euler decomposition identity:
          sum_{k=1}^K PFRC_k + IRR == 1.000000
        across 500 randomized portfolios encompassing varying dimensions,
        singular covariance matrices, zero loadings, and extreme asset weights.
        """
        np.random.seed(1337)
        max_deviation = 0.0

        for trial in range(500):
            N = np.random.randint(2, 60)
            K = np.random.randint(1, 15)

            # Random weight types: long-only, long-short, unnormalized, concentrated
            w_type = trial % 4
            if w_type == 0:
                w = np.random.dirichlet(np.ones(N))
            elif w_type == 1:
                w = np.random.randn(N)
                w /= (np.sum(np.abs(w)) + 1e-6)
            elif w_type == 2:
                w = np.zeros(N)
                w[np.random.randint(0, N)] = 1.0
            else:
                w = np.random.uniform(-1.0, 1.0, size=N)

            # Random loadings: standard, sparse, or with zero factor
            B = np.random.randn(N, K)
            if trial % 5 == 0:
                B[:, np.random.randint(0, K)] = 0.0  # unloaded factor

            # Random factor covariance: non-PSD, singular, or well-conditioned
            if trial % 7 == 0:
                A = np.random.randn(K, max(1, K // 2))
                Omega_F = A @ A.T  # rank deficient
            elif trial % 11 == 0:
                Omega_F = np.random.randn(K, K)
                Omega_F = (Omega_F + Omega_F.T) / 2.0  # may have negative eigenvalues
            else:
                A = np.random.randn(K, K)
                Omega_F = A.T @ A + np.eye(K) * 1e-3

            # Random idiosyncratic risk
            if trial % 13 == 0:
                D_idio = np.random.uniform(-0.02, 0.05, size=N)  # negative elements
            else:
                D_idio = np.random.uniform(0.001, 0.10, size=N)

            mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, Omega_F, D_idio)

            total_risk_contribution = float(np.sum(pfrc) + irr)
            dev = abs(total_risk_contribution - 1.0)
            if dev > max_deviation:
                max_deviation = dev

            self.assertAlmostEqual(
                total_risk_contribution,
                1.0,
                places=6,
                msg=f"Trial {trial} failed Euler identity! sum(PFRC) + IRR = {total_risk_contribution:.8f}, deviation={dev:.2e}"
            )

        self.assertLess(max_deviation, 1e-6, f"Maximum Euler deviation exceeded threshold: {max_deviation:.2e}")

    def test_automatic_factor_decomposition_with_cov_matrix(self):
        """
        Automatic factor decomposition when Omega_F and D_idio are None but cov_matrix is provided.
        Verifies GLS projection Omega_F = pinv(B) cov pinv(B)^T and D = diag(cov - B Omega B^T).
        """
        N, K = 8, 2
        w = np.ones(N) / N
        B = np.random.randn(N, K)
        # Construct synthetic asset covariance
        true_omega = np.eye(K) * 0.04
        true_d = np.ones(N) * 0.02
        cov_matrix = B @ true_omega @ B.T + np.diag(true_d)

        mfrc, pfrc, irr = compute_factor_risk_contributions(
            weights=w,
            B_loadings=B,
            Omega_F=None,
            D_idio=None,
            cov_matrix=cov_matrix
        )

        self.assertTrue(all(np.isfinite(mfrc)))
        self.assertTrue(all(np.isfinite(pfrc)))
        self.assertTrue(np.isfinite(irr))
        self.assertAlmostEqual(float(np.sum(pfrc) + irr), 1.0, places=9)


class TestMilestone3SystemInvariants(unittest.TestCase):
    """
    Verifies system core invariants for Milestone 3.
    """

    def test_synthetic_rows_native_int_zero(self):
        """
        Invariant: synthetic_rows == 0 strictly verified as native Python int 0 (not bool).
        """
        status_path = "benchmarks/30year/status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        synth = status.get("synthetic_rows")
        self.assertTrue(
            isinstance(synth, int) and not isinstance(synth, bool) and synth == 0,
            f"Invariant synthetic_rows == 0 failed: value={synth}, type={type(synth)}"
        )


if __name__ == "__main__":
    unittest.main()

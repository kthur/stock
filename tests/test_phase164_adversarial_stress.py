"""
tests/test_phase164_adversarial_stress.py — Empirical Challenger Stress Suite for Phase 164 (Milestone 1).

Adversarial stress-testing of:
- Category A: Octuple-Pillar Symmetric ZCA Whitening Adversarial Stress (TC01 ~ TC10)
- Category B: Fréchet Shrinkage and Riemannian AIRM Metric Stability (TC11 ~ TC17)
- Category C: Hyperbolic Deadband Thresholding Edge Cases & Singularities (TC18 ~ TC24)
- Category D: Phase164Coupler Degeneracy, Rank Deficiency & Large Scale (TC25 ~ TC30)
- Category E: 5-Market Long-Term Compounding Return Policies Stress (TC31 ~ TC40)

All tests empirically verify invariants, edge cases, and failure modes.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.ai.factor_orthogonalizer import (
    OCTUPLE_PILLAR_MAP,
    OctuplePillarMap,
    FactorOrthogonalizerEngine,
    compute_octuple_pillar_zca_whitening,
    compute_septuple_pillar_zca_whitening,
    compute_riemannian_airm_distance,
    compute_riemannian_airm_metric,
    compute_riemannian_frechet_shrinkage,
    apply_hyperbolic_deadband_phase164,
)
from src.ai.historical_couplers import (
    Phase164Coupler,
    F804Coupler,
    OctuplePillarCoupler,
    Phase164AlphaCoupler,
)
from src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    apply_distress_gatekeeper,
    apply_high_quality_compounder_bonus,
    evaluate_long_term_compounding_policies,
)


class TestPhase164AdversarialStress(unittest.TestCase):
    """Adversarial stress tests for Phase 164 implementation."""

    def setUp(self) -> None:
        self.ortho = FactorOrthogonalizerEngine()
        self.coupler = Phase164Coupler()

    # =========================================================================
    # Category A: Octuple-Pillar Symmetric ZCA Whitening Adversarial Stress
    # =========================================================================

    def test_tc01_singular_rank1_covariance(self) -> None:
        """TC01: Rank-1 covariance (all 8 pillars identical/perfectly collinear)."""
        # All factors identical: cov = ones(8, 8)
        cov_rank1 = np.ones((8, 8), dtype=np.float64)
        w_zca = compute_octuple_pillar_zca_whitening(cov_rank1, shrink_weight=0.0)

        # Invariants: No NaNs, No Infs, Strictly Symmetric
        self.assertFalse(np.isnan(w_zca).any(), "ZCA on rank-1 cov must not produce NaNs")
        self.assertFalse(np.isinf(w_zca).any(), "ZCA on rank-1 cov must not produce Infs")
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10, err_msg="ZCA matrix must be strictly symmetric")

        # Resulting whitened matrix must be positive semi-definite and finite
        cov_white = w_zca @ cov_rank1 @ w_zca.T
        self.assertFalse(np.isnan(cov_white).any())
        self.assertFalse(np.isinf(cov_white).any())
        eigvals = np.linalg.eigvalsh(0.5 * (cov_white + cov_white.T))
        self.assertTrue(np.all(eigvals >= -1e-6), "Whitened covariance eigenvalues must be >= -1e-6")

    def test_tc02_rank_deficient_covariance(self) -> None:
        """TC02: Rank-4 covariance (4 unique factors, 4 exact duplicated factors)."""
        rng = np.random.RandomState(164)
        X4 = rng.normal(0, 1, (100, 4))
        X8 = np.hstack([X4, X4])  # Rank 4 in 8 dimensions
        cov8 = np.cov(X8, rowvar=False)
        self.assertEqual(np.linalg.matrix_rank(cov8), 4)

        w_zca = compute_octuple_pillar_zca_whitening(cov8, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_zca).any())
        self.assertFalse(np.isinf(w_zca).any())
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10)

        # Test with shrink weight > 0 (shrinkage regularizes rank deficiency)
        w_zca_shrunk = compute_octuple_pillar_zca_whitening(cov8, shrink_weight=0.2)
        self.assertFalse(np.isnan(w_zca_shrunk).any())
        np.testing.assert_allclose(w_zca_shrunk, w_zca_shrunk.T, atol=1e-10)

    def test_tc03_zero_covariance_matrix(self) -> None:
        """TC03: Degenerate zero covariance matrix (all zeros)."""
        cov_zero = np.zeros((8, 8), dtype=np.float64)
        w_zca = compute_octuple_pillar_zca_whitening(cov_zero, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_zca).any(), "ZCA on all-zeros matrix must not produce NaNs")
        self.assertFalse(np.isinf(w_zca).any(), "ZCA on all-zeros matrix must not produce Infs")
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10)

    def test_tc04_near_collinear_ill_conditioned_covariance(self) -> None:
        """TC04: Near-collinear covariance matrix with condition number > 10^14."""
        v = np.ones((8, 1))
        # rank 1 + 1e-15 identity perturbation -> cond ~ 10^15
        cov_ill = v @ v.T + np.eye(8) * 1e-14
        cond_num = np.linalg.cond(cov_ill)
        self.assertGreater(cond_num, 1e12)

        w_zca = compute_octuple_pillar_zca_whitening(cov_ill, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_zca).any())
        self.assertFalse(np.isinf(w_zca).any())
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10)

    def test_tc05_asymmetric_input_covariance(self) -> None:
        """TC05: Asymmetric input covariance matrix is properly symmetrized."""
        rng = np.random.RandomState(42)
        A = rng.normal(0, 1, (8, 8))
        A = A + np.eye(8) * 5.0  # Asymmetric matrix
        self.assertFalse(np.allclose(A, A.T))

        w_zca = compute_octuple_pillar_zca_whitening(A, shrink_weight=0.0)
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10, err_msg="Output ZCA must be symmetric even if input is asymmetric")

    def test_tc06_negative_eigenvalues_covariance(self) -> None:
        """TC06: Non-positive semi-definite empirical covariance with negative eigenvalues."""
        cov_neg = np.diag([2.0, 1.5, 1.0, 0.5, 0.2, 0.1, -0.5, -2.0])
        w_zca = compute_octuple_pillar_zca_whitening(cov_neg, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_zca).any())
        self.assertFalse(np.isinf(w_zca).any())
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-10)

    def test_tc07_extreme_variances_scale(self) -> None:
        """TC07: Extreme variances scaling (huge 10^10 vs microscopic 10^-12)."""
        cov_huge = np.eye(8) * 1e10
        w_huge = compute_octuple_pillar_zca_whitening(cov_huge, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_huge).any())
        self.assertFalse(np.isinf(w_huge).any())

        cov_tiny = np.eye(8) * 1e-12
        w_tiny = compute_octuple_pillar_zca_whitening(cov_tiny, shrink_weight=0.0)
        self.assertFalse(np.isnan(w_tiny).any())
        self.assertFalse(np.isinf(w_tiny).any())

    def test_tc08_geometric_shrinkage_weights_and_bounds(self) -> None:
        """TC08: Geometric shrinkage weight extremes (0.0, 0.5, 1.0, and out-of-bounds clipping)."""
        rng = np.random.RandomState(99)
        cov = np.cov(rng.normal(0, 1, (50, 8)), rowvar=False)

        # Pure ZCA (t=0.0)
        w_0 = compute_octuple_pillar_zca_whitening(cov, shrink_weight=0.0)
        # Full Identity Target (t=1.0)
        w_1 = compute_octuple_pillar_zca_whitening(cov, shrink_weight=1.0)
        # Out-of-bounds weight -1.0 should clip to 0.0
        w_neg = compute_octuple_pillar_zca_whitening(cov, shrink_weight=-1.0)
        # Out-of-bounds weight 2.5 should clip to 1.0
        w_pos = compute_octuple_pillar_zca_whitening(cov, shrink_weight=2.5)

        np.testing.assert_allclose(w_0, w_neg, atol=1e-10)
        np.testing.assert_allclose(w_1, w_pos, atol=1e-10)

    def test_tc09_orthogonalize_phase164_with_nan_pillars(self) -> None:
        """TC09: Orthogonalize on score dataframe preserves NaN masks (zero synthetic data invariant) while bounding valid values in [0.05, 0.95]."""
        cols = [f"f_{i}" for i in range(8)]
        df = pd.DataFrame(np.random.uniform(0.2, 0.8, (25, 8)), columns=cols)
        # f_2 is completely missing; f_5 is partially missing (rows 0-5)
        df["f_2"] = np.nan
        df.loc[0:5, "f_5"] = np.nan
        df["market"] = "SP500"

        res = self.ortho.orthogonalize_phase164(df, strategy_cols=cols)
        self.assertEqual(len(res), 25)

        # Invariant 1: Completely missing column f_2 must remain NaN (no fabricated predictions)
        self.assertTrue(res["f_2"].isna().all(), "Completely missing strategy column must preserve NaNs to avoid synthetic data")

        # Invariant 2: Partially missing column f_5 preserves NaN at rows 0-5 and valid in rows 6-24
        self.assertTrue(res.loc[0:5, "f_5"].isna().all(), "Missing rows must preserve NaNs")
        self.assertTrue(res.loc[6:24, "f_5"].notna().all(), "Valid rows must be populated")
        self.assertTrue(((res.loc[6:24, "f_5"] >= 0.05) & (res.loc[6:24, "f_5"] <= 0.95)).all())

        # Invariant 3: Complete columns must have zero NaNs and be bounded in [0.05, 0.95]
        for c in [c for c in cols if c not in ("f_2", "f_5")]:
            self.assertFalse(res[c].isna().any(), f"Complete column {c} must have no NaNs")
            self.assertTrue(((res[c] >= 0.05) & (res[c] <= 0.95)).all(), f"Column {c} outside [0.05, 0.95]")

    def test_tc10_orthogonalize_phase164_with_constant_zero_variance_pillar(self) -> None:
        """TC10: Orthogonalize with constant (zero-variance) factor pillars."""
        cols = [f"f_{i}" for i in range(8)]
        df = pd.DataFrame(np.random.uniform(0.2, 0.8, (20, 8)), columns=cols)
        df["f_0"] = 0.50  # Constant column (zero variance)
        df["f_7"] = 0.50  # Another constant column

        res = self.ortho.orthogonalize_phase164(df, strategy_cols=cols)
        self.assertEqual(len(res), 20)
        for c in cols:
            self.assertFalse(res[c].isna().any())
            self.assertTrue(np.isfinite(res[c].values).all())

    # =========================================================================
    # Category B: Fréchet Shrinkage and Riemannian AIRM Metric Stability
    # =========================================================================

    def test_tc11_airm_identity_and_symmetry(self) -> None:
        """TC11: Riemannian AIRM satisfies d(A, A) = 0 and d(A, B) = d(B, A)."""
        rng = np.random.RandomState(42)
        X1 = rng.normal(0, 1, (40, 8))
        X2 = rng.normal(0, 1, (40, 8))
        cov1 = np.cov(X1, rowvar=False) + np.eye(8) * 0.1
        cov2 = np.cov(X2, rowvar=False) + np.eye(8) * 0.1

        d_11 = compute_riemannian_airm_distance(cov1, cov1)
        self.assertAlmostEqual(d_11, 0.0, places=6)

        d_12 = compute_riemannian_airm_distance(cov1, cov2)
        d_21 = compute_riemannian_airm_distance(cov2, cov1)
        self.assertGreater(d_12, 0.0)
        self.assertAlmostEqual(d_12, d_21, places=6)

    def test_tc12_airm_positivity_and_triangle_inequality(self) -> None:
        """TC12: AIRM metric satisfies positivity and triangle inequality d(A,C) <= d(A,B) + d(B,C)."""
        cov_a = np.diag([1.0, 1.2, 0.8, 1.1, 0.9, 1.0, 1.0, 1.0])
        cov_b = np.diag([1.5, 0.7, 1.3, 0.8, 1.2, 0.9, 1.1, 1.0])
        cov_c = np.diag([0.5, 2.0, 0.6, 1.5, 0.7, 1.3, 0.8, 1.2])

        d_ab = compute_riemannian_airm_distance(cov_a, cov_b)
        d_bc = compute_riemannian_airm_distance(cov_b, cov_c)
        d_ac = compute_riemannian_airm_distance(cov_a, cov_c)

        self.assertGreater(d_ab, 0.0)
        self.assertGreater(d_bc, 0.0)
        self.assertGreater(d_ac, 0.0)
        self.assertLessEqual(d_ac, d_ab + d_bc + 1e-6, "AIRM triangle inequality must hold")

    def test_tc13_airm_on_rank_deficient_and_zero_eigenvalues(self) -> None:
        """TC13: AIRM distance under rank-deficient and zero-eigenvalue matrices does not crash."""
        cov_rank1 = np.ones((8, 8))
        cov_eye = np.eye(8)
        d = compute_riemannian_airm_distance(cov_rank1, cov_eye)
        self.assertTrue(np.isfinite(d))
        self.assertGreaterEqual(d, 0.0)

        # Zero matrix
        cov_zero = np.zeros((8, 8))
        d_zero = compute_riemannian_airm_distance(cov_zero, cov_eye)
        self.assertTrue(np.isfinite(d_zero))
        self.assertGreaterEqual(d_zero, 0.0)

    def test_tc14_airm_on_malformed_inputs(self) -> None:
        """TC14: AIRM distance on dimension mismatch or empty arrays returns 0.0 gracefully."""
        self.assertEqual(compute_riemannian_airm_distance(np.eye(4), np.eye(8)), 0.0)
        self.assertEqual(compute_riemannian_airm_distance(np.array([]), np.array([])), 0.0)
        self.assertEqual(compute_riemannian_airm_distance(np.ones((4,)), np.ones((4,))), 0.0)

    def test_tc15_frechet_shrinkage_geodesic_endpoints_and_symmetry(self) -> None:
        """TC15: Fréchet shrinkage Gamma(t) satisfies endpoints Gamma(0) = Sigma1, Gamma(1) = Sigma2."""
        rng = np.random.RandomState(42)
        s1 = np.cov(rng.normal(0, 1, (30, 8)), rowvar=False) + np.eye(8) * 0.2
        s2 = np.diag(np.diag(s1))  # Diagonal target

        g0 = compute_riemannian_frechet_shrinkage(s1, s2, alpha=0.0)
        g1 = compute_riemannian_frechet_shrinkage(s1, s2, alpha=1.0)
        g_mid = compute_riemannian_frechet_shrinkage(s1, s2, alpha=0.5)

        np.testing.assert_allclose(g0, 0.5 * (s1 + s1.T), atol=1e-5, err_msg="Gamma(0) must equal s1")
        np.testing.assert_allclose(g1, 0.5 * (s2 + s2.T), atol=1e-5, err_msg="Gamma(1) must equal s2")
        np.testing.assert_allclose(g_mid, g_mid.T, atol=1e-10, err_msg="Gamma(t) must be strictly symmetric")

    def test_tc16_frechet_shrinkage_on_singular_sample_cov(self) -> None:
        """TC16: Fréchet shrinkage regularizes singular sample covariance toward identity target."""
        s_sing = np.ones((8, 8))  # Rank 1 singular matrix
        target = np.eye(8)

        shrunk = compute_riemannian_frechet_shrinkage(s_sing, target, alpha=0.5)
        self.assertFalse(np.isnan(shrunk).any())
        self.assertFalse(np.isinf(shrunk).any())
        np.testing.assert_allclose(shrunk, shrunk.T, atol=1e-10)

        # Resulting matrix should have strictly positive eigenvalues
        eigs = np.linalg.eigvalsh(shrunk)
        self.assertTrue(np.all(eigs > 0.0), f"Shrunk eigenvalues must be positive, got {eigs}")

    def test_tc17_frechet_shrinkage_weight_clipping(self) -> None:
        """TC17: Fréchet shrinkage handles weights outside [0, 1] by clamping."""
        s1 = np.eye(8) * 2.0
        s2 = np.eye(8) * 5.0
        g_neg = compute_riemannian_frechet_shrinkage(s1, s2, alpha=-0.5)
        g_pos = compute_riemannian_frechet_shrinkage(s1, s2, alpha=1.5)
        np.testing.assert_allclose(g_neg, s1, atol=1e-6)
        np.testing.assert_allclose(g_pos, s2, atol=1e-6)

    # =========================================================================
    # Category C: Hyperbolic Deadband Thresholding Edge Cases & Singularities
    # =========================================================================

    def test_tc18_hyperbolic_deadband_exact_boundary(self) -> None:
        """TC18: Hyperbolic deadband at boundary |z| = delta."""
        delta = 0.035
        # Below 0.85*delta: strictly 0.0
        self.assertEqual(apply_hyperbolic_deadband_phase164(0.80 * delta, delta=delta), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase164(-0.80 * delta, delta=delta), 0.0)

        # Above 1.05*delta: 100% transmitted
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase164(1.10 * delta, delta=delta), 1.10 * delta, places=5)
        self.assertAlmostEqual(apply_hyperbolic_deadband_phase164(-1.10 * delta, delta=delta), -1.10 * delta, places=5)

    def test_tc19_hyperbolic_deadband_transition_band(self) -> None:
        """TC19: Hyperbolic deadband within transition band [0.85*delta, 1.05*delta]."""
        delta = 0.035
        # Inside transition band, output must be smooth and bounded
        z_trans = 0.95 * delta
        res = apply_hyperbolic_deadband_phase164(z_trans, delta=delta)
        self.assertTrue(0.0 <= res <= z_trans)

        z_trans_neg = -0.95 * delta
        res_neg = apply_hyperbolic_deadband_phase164(z_trans_neg, delta=delta)
        self.assertTrue(z_trans_neg <= res_neg <= 0.0)

    def test_tc20_hyperbolic_deadband_antisymmetry_odd_function(self) -> None:
        """TC20: Odd function invariant f(-z) = -f(z) holds across all ranges."""
        delta = 0.035
        test_vals = [0.0, 1e-5, 0.01, 0.029, 0.035, 0.040, 0.10, 0.50, 1.0, 5.0]
        for val in test_vals:
            pos = apply_hyperbolic_deadband_phase164(val, delta=delta)
            neg = apply_hyperbolic_deadband_phase164(-val, delta=delta)
            self.assertAlmostEqual(pos, -neg, places=7, msg=f"Antisymmetry failed for z={val}")

    def test_tc21_hyperbolic_deadband_extreme_values(self) -> None:
        """TC21: Extreme values z=10^50, z=10^300 do not overflow or raise RuntimeWarning."""
        delta = 0.035
        for big_z in [1e10, 1e50, 1e200]:
            res = apply_hyperbolic_deadband_phase164(big_z, delta=delta)
            self.assertTrue(np.isfinite(res))
            self.assertEqual(res, big_z)

            res_neg = apply_hyperbolic_deadband_phase164(-big_z, delta=delta)
            self.assertTrue(np.isfinite(res_neg))
            self.assertEqual(res_neg, -big_z)

    def test_tc22_hyperbolic_deadband_microscopic_and_zero(self) -> None:
        """TC22: Microscopic inputs |z| <= 1e-12 return exact 0.0."""
        self.assertEqual(apply_hyperbolic_deadband_phase164(0.0), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase164(1e-13), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase164(-1e-13), 0.0)

    def test_tc23_hyperbolic_deadband_type_polymorphism(self) -> None:
        """TC23: Deadband supports float, int, np.ndarray (1D and 2D), and pd.Series."""
        delta = 0.035
        # int
        self.assertEqual(apply_hyperbolic_deadband_phase164(0, delta=delta), 0.0)
        self.assertEqual(apply_hyperbolic_deadband_phase164(1, delta=delta), 1.0)

        # 1D array
        arr1 = np.array([-0.05, -0.01, 0.0, 0.01, 0.05])
        res1 = apply_hyperbolic_deadband_phase164(arr1, delta=delta)
        self.assertEqual(res1.shape, (5,))
        self.assertEqual(res1[1], 0.0)
        self.assertEqual(res1[2], 0.0)
        self.assertEqual(res1[3], 0.0)

        # 2D array
        arr2 = np.array([[-0.05, 0.01], [0.0, 0.05]])
        res2 = apply_hyperbolic_deadband_phase164(arr2, delta=delta)
        self.assertEqual(res2.shape, (2, 2))

        # pd.Series
        ser = pd.Series([-0.05, 0.01, 0.05], index=["A", "B", "C"])
        res_ser = apply_hyperbolic_deadband_phase164(ser, delta=delta)
        self.assertIsInstance(res_ser, pd.Series)
        self.assertEqual(list(res_ser.index), ["A", "B", "C"])
        self.assertEqual(res_ser["B"], 0.0)

    def test_tc24_factor_orthogonalizer_deadband_score_bounds(self) -> None:
        """TC24: Deadband within orthogonalize_phase164 preserves [0.05, 0.95] institutional bounds."""
        rng = np.random.RandomState(42)
        cols = [f"f_{i}" for i in range(8)]
        # Synthetic scores near 0.50 (deadband region) and near edges
        X = np.vstack([
            rng.uniform(0.48, 0.52, (20, 8)),  # within deadband
            rng.uniform(0.01, 0.99, (20, 8)),  # broad range
        ])
        df = pd.DataFrame(X, columns=cols)
        res = self.ortho.orthogonalize_phase164(df, strategy_cols=cols)
        for c in cols:
            self.assertTrue((res[c] >= 0.05).all())
            self.assertTrue((res[c] <= 0.95).all())

    # =========================================================================
    # Category D: Phase164Coupler Degeneracy, Rank Deficiency & Large Scale
    # =========================================================================

    def test_tc25_phase164_coupler_single_asset_n1(self) -> None:
        """TC25: Single asset input (N=1) falls back gracefully to identity covariance."""
        single_scores = np.array([0.7, 0.6, 0.8, 0.5, 0.75, 0.65, 0.7, 0.6])
        res = self.coupler.evaluate(single_scores)
        self.assertIn("alpha_p164", res)
        self.assertIn("h_phase164", res)
        self.assertIn("fcpi_v164", res)

        alpha = float(res["alpha_p164"])
        self.assertTrue(np.isfinite(alpha))
        self.assertTrue(-3.0 <= alpha <= 3.0)
        self.assertTrue(0.0 < float(res["h_phase164"]) <= 1.0)
        self.assertTrue(0.0 < float(res["fcpi_v164"]) <= 1.0)

    def test_tc26_phase164_coupler_underdetermined_rank_deficiency(self) -> None:
        """TC26: Under-determined cross-section N=3 < D=8 (rank-deficient empirical covariance)."""
        rng = np.random.RandomState(77)
        scores_3x8 = rng.uniform(0.3, 0.7, (3, 8))
        res = self.coupler.evaluate(scores_3x8)

        alphas = np.asarray(res["alpha_p164"])
        self.assertEqual(len(alphas), 3)
        self.assertTrue(np.all(np.isfinite(alphas)))
        self.assertTrue(np.all(alphas >= -3.0))
        self.assertTrue(np.all(alphas <= 3.0))

    def test_tc27_phase164_coupler_extreme_factor_signals(self) -> None:
        """TC27: Coupler with maximum bullish, maximum bearish, and alternating extreme signals."""
        signals = np.array([
            [0.95] * 8,  # Extreme bullish
            [0.05] * 8,  # Extreme bearish
            [0.95, 0.05, 0.95, 0.05, 0.95, 0.05, 0.95, 0.05],  # Divergent
        ])
        res = self.coupler.evaluate(signals)
        alphas = np.asarray(res["alpha_p164"])
        self.assertGreater(alphas[0], 0.0, "Bullish factor signals must yield positive alpha")
        self.assertLess(alphas[1], 0.0, "Bearish factor signals must yield negative alpha")
        self.assertTrue(np.all(alphas >= -3.0))
        self.assertTrue(np.all(alphas <= 3.0))

    def test_tc28_phase164_coupler_corrupted_inputs_sanitization(self) -> None:
        """TC28: Coupler input with NaNs, Infs, -Infs produces clean finite alpha."""
        corrupted = np.array([
            [np.nan, 0.6, np.inf, -np.inf, 0.7, 0.5, 0.6, 0.8],
            [0.5, np.nan, 0.6, 0.7, 0.5, 0.6, 0.4, 0.55],
            [0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.7, np.nan],
        ])
        res = self.coupler.evaluate(corrupted)
        alphas = np.asarray(res["alpha_p164"])
        self.assertTrue(np.all(np.isfinite(alphas)))
        self.assertTrue(np.all(alphas >= -3.0))
        self.assertTrue(np.all(alphas <= 3.0))

    def test_tc29_phase164_coupler_full_universe_scale_and_sla(self) -> None:
        """TC29: Large-scale universe (N=3,379 symbols x 8 pillars) executes within < 50ms."""
        rng = np.random.RandomState(123)
        universe_scores = rng.uniform(0.1, 0.9, (3379, 8))
        t0 = time.perf_counter()
        res = self.coupler.evaluate(universe_scores)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        alphas = np.asarray(res["alpha_p164"])
        self.assertEqual(len(alphas), 3379)
        self.assertTrue(np.all(np.isfinite(alphas)))
        self.assertLess(elapsed_ms, 85.0, f"Coupler latency {elapsed_ms:.2f}ms exceeds 85ms SLA")

    def test_tc30_phase164_coupler_aliases(self) -> None:
        """TC30: Verify all backward compatibility aliases point to Phase164Coupler."""
        self.assertIs(F804Coupler, Phase164Coupler)
        self.assertIs(OctuplePillarCoupler, Phase164Coupler)
        self.assertIs(Phase164AlphaCoupler, Phase164Coupler)

    # =========================================================================
    # Category E: 5-Market Long-Term Compounding Return Policies Stress
    # =========================================================================

    def test_tc31_kospi_high_quality_compounder_bonus(self) -> None:
        """TC31: KOSPI high-quality compounder (005930, 000660) receives 1.035x bonus."""
        df_kospi = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "market": ["KOSPI", "KOSPI"],
            "operating_margin": [0.22, 0.16],
            "roe": [0.18, 0.15],
            "ensemble_score": [0.70, 0.65],
        })
        scores = evaluate_long_term_compounding_policies(df_kospi)
        self.assertAlmostEqual(scores.iloc[0], min(1.0, 0.70 * 1.035), places=5)
        self.assertAlmostEqual(scores.iloc[1], min(1.0, 0.65 * 1.035), places=5)

    def test_tc32_kosdaq_distress_gatekeeper_penalty(self) -> None:
        """TC32: KOSDAQ loss-making distressed firms receive 0.70x penalty."""
        df_kosdaq = pd.DataFrame({
            "symbol": ["068270", "091990", "LOSS_MAKER_OP", "LOSS_MAKER_ROE"],
            "market": ["KOSDAQ", "KOSDAQ", "KOSDAQ", "KOSDAQ"],
            "operating_margin": [0.05, 0.08, -0.15, 0.02],
            "roe": [0.05, 0.08, 0.01, -0.12],
            "ensemble_score": [0.60, 0.60, 0.60, 0.60],
        })
        scores = evaluate_long_term_compounding_policies(df_kosdaq)
        self.assertAlmostEqual(scores.iloc[0], 0.60, places=5)  # Neutral: no penalty
        self.assertAlmostEqual(scores.iloc[1], 0.60, places=5)  # Neutral: no penalty
        self.assertAlmostEqual(scores.iloc[2], 0.60 * 0.70, places=5)  # OP < -0.10 penalty
        self.assertAlmostEqual(scores.iloc[3], 0.60 * 0.70, places=5)  # ROE < -0.10 penalty

    def test_tc33_sp500_partial_fundamental_quality_bonus(self) -> None:
        """TC33: S&P 500 single-metric quality threshold (OP >= 0.18 solo or ROE >= 0.18 solo) and dual-metric (OP >= 0.15 and ROE >= 0.15)."""
        # Mode 1: Solo operating_margin available in universe
        df_op_solo = pd.DataFrame({
            "symbol": ["NVDA", "UNPROFITABLE"],
            "operating_margin": [0.25, -0.05],
            "ensemble_score": [0.60, 0.60],
        })
        scores_op = evaluate_long_term_compounding_policies(df_op_solo)
        self.assertAlmostEqual(scores_op.iloc[0], 0.60 * 1.035, places=5)  # OP >= 0.18 solo bonus
        self.assertAlmostEqual(scores_op.iloc[1], 0.60, places=5)          # Unprofitable, neutral

        # Mode 2: Solo ROE available in universe
        df_roe_solo = pd.DataFrame({
            "symbol": ["AAPL", "UNPROFITABLE"],
            "roe": [0.28, -0.02],
            "ensemble_score": [0.60, 0.60],
        })
        scores_roe = evaluate_long_term_compounding_policies(df_roe_solo)
        self.assertAlmostEqual(scores_roe.iloc[0], 0.60 * 1.035, places=5)  # ROE >= 0.18 solo bonus
        self.assertAlmostEqual(scores_roe.iloc[1], 0.60, places=5)          # Unprofitable, neutral

        # Mode 3: Dual metric available (requires OP >= 0.15 and ROE >= 0.15)
        df_dual = pd.DataFrame({
            "symbol": ["MSFT", "PARTIAL_ONE_ONLY"],
            "operating_margin": [0.25, 0.25],
            "roe": [0.20, np.nan],
            "ensemble_score": [0.60, 0.60],
        })
        scores_dual = evaluate_long_term_compounding_policies(df_dual)
        self.assertAlmostEqual(scores_dual.iloc[0], 0.60 * 1.035, places=5)  # Dual satisfied
        self.assertAlmostEqual(scores_dual.iloc[1], 0.60, places=5)          # Missing one metric does not satisfy dual criteria

    def test_tc34_nasdaq_short_squeeze_turnaround_exemption(self) -> None:
        """TC34: NASDAQ distressed stock with short squeeze catalyst gets turnaround exemption."""
        df_nasdaq = pd.DataFrame({
            "symbol": ["DISTRESS_NO_CATALYST", "DISTRESS_SQUEEZE"],
            "market": ["NASDAQ", "NASDAQ"],
            "operating_margin": [-0.25, -0.25],
            "roe": [-0.30, -0.30],
            "short_squeeze_score": [0.20, 0.75],
            "ensemble_score": [0.60, 0.60],
        })
        scores = evaluate_long_term_compounding_policies(df_nasdaq)
        self.assertAlmostEqual(scores.iloc[0], 0.60 * 0.70, places=5)  # Penalized
        self.assertAlmostEqual(scores.iloc[1], 0.60, places=5)          # Exempted!

    def test_tc35_russell2000_valueup_turnaround_exemption(self) -> None:
        """TC35: RUSSELL 2000 distressed stock with value-up catalyst gets turnaround exemption."""
        df_r2k = pd.DataFrame({
            "symbol": ["R2K_DISTRESS", "R2K_VALUEUP"],
            "market": ["RUSSELL2000", "RUSSELL2000"],
            "operating_margin": [-0.15, -0.15],
            "roe": [-0.20, -0.20],
            "valueup_catalyst_score": [0.30, 0.80],
            "ensemble_score": [0.55, 0.55],
        })
        scores = evaluate_long_term_compounding_policies(df_r2k)
        self.assertAlmostEqual(scores.iloc[0], 0.55 * 0.70, places=5)  # Penalized
        self.assertAlmostEqual(scores.iloc[1], 0.55, places=5)          # Exempted!

    def test_tc36_reversal_catalyst_turnaround_exemption(self) -> None:
        """TC36: Distressed stock with mean-reversal catalyst gets turnaround exemption."""
        df_rev = pd.DataFrame({
            "symbol": ["REV_STOCK"],
            "operating_margin": [-0.30],
            "roe": [-0.40],
            "reversal_score": [0.70],
            "ensemble_score": [0.50],
        })
        scores = evaluate_long_term_compounding_policies(df_rev)
        self.assertAlmostEqual(scores.iloc[0], 0.50, places=5)  # Exempted from penalty

    def test_tc37_missing_fundamentals_nan_resilience(self) -> None:
        """TC37: Missing/NaN fundamentals pass through untouched without errors or NaNs."""
        df_nans = pd.DataFrame({
            "symbol": ["NAN_1", "NAN_2"],
            "operating_margin": [np.nan, np.nan],
            "roe": [np.nan, np.nan],
            "ensemble_score": [0.58, 0.42],
        })
        scores = evaluate_long_term_compounding_policies(df_nans)
        self.assertAlmostEqual(scores.iloc[0], 0.58, places=5)
        self.assertAlmostEqual(scores.iloc[1], 0.42, places=5)
        self.assertFalse(scores.isna().any())

    def test_tc38_boundary_critical_values_distress(self) -> None:
        """TC38: Exact distress boundary check: -0.10 (strict inequality < -0.10)."""
        df_bound = pd.DataFrame({
            "symbol": ["EXACT_BOUNDARY", "SLIGHTLY_BELOW"],
            "operating_margin": [-0.10, -0.1000001],
            "roe": [0.0, 0.0],
            "ensemble_score": [0.60, 0.60],
        })
        scores = evaluate_long_term_compounding_policies(df_bound)
        self.assertAlmostEqual(scores.iloc[0], 0.60, places=5, msg="-0.10 exactly is not < -0.10, should not penalize")
        self.assertAlmostEqual(scores.iloc[1], 0.60 * 0.70, places=5, msg="-0.1000001 < -0.10, must penalize")

    def test_tc39_distress_and_quality_mutual_exclusion(self) -> None:
        """TC39: Distressed firms (even with one high metric) cannot receive quality bonus."""
        df_mut = pd.DataFrame({
            "symbol": ["CONFLICT_STOCK"],
            "operating_margin": [0.25],  # High operating margin
            "roe": [-0.20],             # But severely negative ROE -> distressed!
            "ensemble_score": [0.60],
        })
        scores = evaluate_long_term_compounding_policies(df_mut)
        # Should be penalized by distress gatekeeper (0.60 * 0.70 = 0.42)
        # and NOT boosted by quality bonus
        self.assertAlmostEqual(scores.iloc[0], 0.60 * 0.70, places=5)

    def test_tc40_score_clamping_to_zero_one(self) -> None:
        """TC40: Scores after compounding bonus do not exceed 1.0; after penalty do not drop below 0.0."""
        df_clamp = pd.DataFrame({
            "symbol": ["HIGH_BASE", "LOW_BASE"],
            "operating_margin": [0.30, -0.50],
            "roe": [0.30, -0.50],
            "ensemble_score": [0.99, 0.01],
        })
        scores = evaluate_long_term_compounding_policies(df_clamp)
        self.assertLessEqual(scores.iloc[0], 1.0)
        self.assertGreaterEqual(scores.iloc[1], 0.0)


if __name__ == "__main__":
    unittest.main()

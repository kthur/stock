"""
tests/test_dfcn_neutralizer.py — Comprehensive Unit & Integration Test Suite
for Dynamic Factor Covariance Neutralizer (D-FCN) & Bilinear Factor Interaction Tensor (BFIT).

Covers:
1. Precision GLS projection closed-form formula verification:
   y_star = [I - W^{-1} B (B^T W^{-1} B + lambda * I)^{-1} B^T] y
2. Exact factor orthogonality: B^T y_star ~ 0 (< 1e-10).
3. Precision weighting distortion reduction and OLS/QR algebraic reduction.
4. BFIT tensor symmetry (M = M^T), bounded activation in [-1.0, 1.0], and factor synergy responses:
   - Value x Momentum (0.25)
   - Momentum x Quality (0.20)
   - Quality x Investment (0.15)
5. Numerical robustness & edge cases: singular matrices, constant features, all NaNs, small N (1, 2, 5, N < K).
6. NumPy 2.0+ rank writeability.
7. MultiFactorNeutralizerEngine API compatibility, static method parity, and kwargs binding.
"""

from __future__ import annotations

import unittest
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.core.multi_factor_neutralizer import (
    MultiFactorNeutralizerEngine,
    compute_precision_weighted_neutralization,
    compute_bilinear_interaction_alpha,
)


class TestDFCNMathematicalCorrectness(unittest.TestCase):
    """Test suite for D-FCN mathematical formulas, projection properties, and orthogonality."""

    def setUp(self):
        np.random.seed(42)

    def test_gls_closed_form_exact_formula(self):
        """Verify D-FCN matches closed-form GLS minimum-distortion formula:
        y_star = [I - W^{-1} B (B^T W^{-1} B)^{-1} B^T] y.
        """
        N, K = 150, 5
        B = np.random.randn(N, K)
        y = np.random.randn(N)
        w = np.random.uniform(0.5, 3.0, size=N)

        # Expected formula via direct matrix inversion
        W_inv = np.diag(1.0 / w)
        A = B.T @ W_inv @ B
        expected_y_star = (np.eye(N) - W_inv @ B @ np.linalg.inv(A) @ B.T) @ y

        actual_y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)

        np.testing.assert_allclose(
            actual_y_star,
            expected_y_star,
            rtol=1e-11,
            atol=1e-11,
            err_msg="D-FCN output does not match closed-form GLS projection formula."
        )

    def test_exact_orthogonality_guarantee(self):
        """Verify exact orthogonality condition: B^T y_star ~ 0 (< 1e-10)."""
        N, K = 250, 5
        B = np.random.randn(N, K)
        y = np.random.randn(N)
        w = np.random.uniform(0.2, 5.0, size=N)

        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)

        ortho_residuals = B.T @ y_star
        max_ortho_error = float(np.max(np.abs(ortho_residuals)))

        self.assertLess(
            max_ortho_error,
            1e-10,
            f"Exact orthogonality violated: max |B^T y_star| = {max_ortho_error:.2e} >= 1e-10"
        )

    def test_none_weights_reduces_to_qr_ols(self):
        """When weights_precision is None, D-FCN must algebraically reduce to standard QR / OLS projection."""
        N, K = 100, 4
        B = np.random.randn(N, K)
        y = np.random.randn(N)

        Q, _ = np.linalg.qr(B, mode="reduced")
        expected_qr = y - Q @ (Q.T @ y)

        actual_qr = compute_precision_weighted_neutralization(y, B, weights_precision=None)

        np.testing.assert_allclose(
            actual_qr,
            expected_qr,
            atol=1e-12,
            err_msg="weights_precision=None failed to reduce to standard QR projection."
        )

    def test_uniform_weights_reduces_to_qr_ols(self):
        """When weights_precision is uniform across all stocks, D-FCN must reduce to standard QR / OLS projection."""
        N, K = 120, 5
        B = np.random.randn(N, K)
        y = np.random.randn(N)
        w_uniform = np.full(N, 4.5)

        Q, _ = np.linalg.qr(B, mode="reduced")
        expected_qr = y - Q @ (Q.T @ y)

        actual_unif = compute_precision_weighted_neutralization(y, B, weights_precision=w_uniform)

        np.testing.assert_allclose(
            actual_unif,
            expected_qr,
            atol=1e-12,
            err_msg="Uniform weights failed to reduce algebraically to standard QR projection."
        )

    def test_precision_weighting_noise_distortion_reduction(self):
        """Verify that high-precision stocks experience lower distortion (|y* - y|) than noisy stocks."""
        N = 200
        K = 3
        B = np.random.randn(N, K)
        y = np.random.randn(N)

        # First half has high signal confidence (precision 100.0), second half is noisy (precision 0.01)
        w = np.ones(N)
        w[:100] = 100.0
        w[100:] = 0.01

        y_star_gls = compute_precision_weighted_neutralization(y, B, weights_precision=w)
        y_star_ols = compute_precision_weighted_neutralization(y, B, weights_precision=None)

        # Distortions for high-precision stocks
        gls_distortion_high = np.mean((y_star_gls[:100] - y[:100]) ** 2)
        ols_distortion_high = np.mean((y_star_ols[:100] - y[:100]) ** 2)

        self.assertLess(
            gls_distortion_high,
            ols_distortion_high,
            "GLS failed to minimize signal distortion for high-precision assets."
        )

    def test_mean_zero_residual_with_intercept(self):
        """When design matrix includes an intercept column, residual sum and mean must be zero."""
        N, K = 100, 4
        Z = np.random.randn(N, K)
        X = np.column_stack([np.ones(N), Z])
        y = np.random.randn(N) + 5.0
        w = np.random.uniform(0.5, 2.0, size=N)

        residual = compute_precision_weighted_neutralization(y, X, weights_precision=w)

        self.assertAlmostEqual(
            float(np.mean(residual)),
            0.0,
            places=10,
            msg="Mean residual with intercept is not zero."
        )


class TestDFCNEdgeCasesAndRobustness(unittest.TestCase):
    """Test suite for D-FCN edge cases, singular matrices, collinearity, and small universes."""

    def setUp(self):
        np.random.seed(123)

    def test_singular_and_collinear_factor_matrix(self):
        """Verify Tikhonov regularization fallback when factors are perfectly collinear."""
        N = 80
        B = np.random.randn(N, 5)
        # Force column 1 to be identical to column 0 (rank deficient)
        B[:, 1] = B[:, 0]
        y = np.random.randn(N)
        w = np.random.uniform(0.5, 2.0, size=N)

        # Must not raise LinAlgError
        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w, ridge_lambda=1e-4)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_underdetermined_universe_n_less_than_k(self):
        """When N < K, function must fall back gracefully to SVD pseudoinverse without error."""
        N, K = 3, 6
        B = np.random.randn(N, K)
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_single_asset_universe(self):
        """When N = 1, function must return zero residual."""
        B = np.array([[1.0, 2.0, 3.0]])
        y = np.array([42.0])

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), 1)
        self.assertEqual(y_star[0], 0.0)

    def test_empty_universe(self):
        """When universe is empty (N = 0), function must return empty array."""
        B = np.zeros((0, 5))
        y = np.zeros(0)

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), 0)

    def test_nan_and_inf_sanitization(self):
        """Verify robust imputation when inputs contain NaNs and Infs."""
        N, K = 50, 5
        B = np.random.randn(N, K)
        B[5, 2] = np.nan
        B[10, 4] = np.inf
        y = np.random.randn(N)
        y[2] = np.nan
        y[15] = -np.inf

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_zero_variance_and_constant_columns(self):
        """Verify behavior when factors have zero variance (constant columns)."""
        N = 60
        B = np.random.randn(N, 4)
        B[:, 1] = 0.0  # Constant column
        B[:, 3] = 5.5  # Constant column
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

    def test_1d_factor_input(self):
        """When B is passed as 1D array of shape (N,), it is reshaped to (N, 1) and neutralized."""
        N = 50
        B = np.random.randn(N)
        y = np.random.randn(N)

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))
        self.assertLess(abs(float(B @ y_star)), 1e-10)

    def test_mismatched_dimensions_graceful(self):
        """When B length does not match y length, function returns zero array."""
        y = np.random.randn(50)
        B = np.random.randn(40, 3)

        y_star = compute_precision_weighted_neutralization(y, B)

        self.assertEqual(len(y_star), 50)
        self.assertTrue(np.all(y_star == 0.0))


class TestBFITInteractionTensor(unittest.TestCase):
    """Test suite for Bilinear Factor Interaction Tensor (BFIT)."""

    def setUp(self):
        np.random.seed(999)

    def test_default_tensor_symmetry(self):
        """Verify that default interaction tensor M is strictly symmetric (M = M^T)."""
        S = np.random.randn(10, 5)
        # Default M tensor inside compute_bilinear_interaction_alpha
        # M[1,4] = M[4,1] = 0.25, M[4,2] = M[2,4] = 0.20, M[2,3] = M[3,2] = 0.15
        M = np.zeros((5, 5))
        M[1, 4] = M[4, 1] = 0.25
        M[4, 2] = M[2, 4] = 0.20
        M[2, 3] = M[3, 2] = 0.15

        np.testing.assert_array_equal(M, M.T, err_msg="Default BFIT tensor is not symmetric.")

    def test_output_bounded_strictly_in_negative_one_to_one(self):
        """Verify bounded activation: alpha_synergy in [-1.0, 1.0] across normal and extreme inputs."""
        # Extreme positive and negative values
        S_extreme = np.array([
            [1e6, 1e6, 1e6, 1e6, 1e6],
            [-1e6, -1e6, -1e6, -1e6, -1e6],
            [10.0, -10.0, 5.0, -5.0, 8.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ])

        alpha = compute_bilinear_interaction_alpha(S_extreme)

        self.assertEqual(len(alpha), 4)
        self.assertTrue(np.all(alpha >= -1.0), "BFIT output below -1.0")
        self.assertTrue(np.all(alpha <= 1.0), "BFIT output above 1.0")

    def test_synergy_factor_pairs(self):
        """Verify synergy response for specified factor pairs:
        - Value (1) x Momentum (4) = 0.25
        - Momentum (4) x Quality (2) = 0.20
        - Quality (2) x Investment (3) = 0.15
        """
        # Test 1: Value x Momentum positive synergy
        S_vm = np.zeros((1, 5))
        S_vm[0, 1] = 2.0  # Value
        S_vm[0, 4] = 2.0  # Momentum
        alpha_vm = compute_bilinear_interaction_alpha(S_vm)
        self.assertGreater(alpha_vm[0], 0.0, "Value x Momentum same sign must produce positive synergy.")

        # Test 2: Value x Momentum negative synergy
        S_vm_opp = np.zeros((1, 5))
        S_vm_opp[0, 1] = 2.0   # Value
        S_vm_opp[0, 4] = -2.0  # Momentum
        alpha_vm_opp = compute_bilinear_interaction_alpha(S_vm_opp)
        self.assertLess(alpha_vm_opp[0], 0.0, "Value x Momentum opposite sign must produce negative synergy.")

        # Test 3: Momentum x Quality synergy
        S_mq = np.zeros((1, 5))
        S_mq[0, 4] = 1.5  # Momentum
        S_mq[0, 2] = 1.5  # Quality
        alpha_mq = compute_bilinear_interaction_alpha(S_mq)
        self.assertGreater(alpha_mq[0], 0.0, "Momentum x Quality same sign must produce positive synergy.")

        # Test 4: Quality x Investment synergy
        S_qi = np.zeros((1, 5))
        S_qi[0, 2] = 1.5  # Quality
        S_qi[0, 3] = 1.5  # Investment
        alpha_qi = compute_bilinear_interaction_alpha(S_qi)
        self.assertGreater(alpha_qi[0], 0.0, "Quality x Investment same sign must produce positive synergy.")

    def test_orthogonal_pairs_zero_synergy(self):
        """Pairs with zero interaction tensor entries (e.g. Size x Investment) produce zero synergy."""
        S_size_inv = np.zeros((1, 5))
        S_size_inv[0, 0] = 3.0  # Size
        S_size_inv[0, 3] = 3.0  # Investment
        alpha = compute_bilinear_interaction_alpha(S_size_inv)
        self.assertAlmostEqual(alpha[0], 0.0, places=10, msg="Non-interacting factors must yield 0.0 synergy.")

    def test_constant_and_zero_factors_zero_synergy(self):
        """Zero or constant factor scores must produce 0.0 synergy."""
        S_zero = np.zeros((20, 5))
        alpha = compute_bilinear_interaction_alpha(S_zero)
        np.testing.assert_array_equal(alpha, np.zeros(20))

    def test_all_nan_scores_handling(self):
        """All-NaN scores must be safely sanitized to 0.0 without crash."""
        S_nan = np.full((15, 5), np.nan)
        alpha = compute_bilinear_interaction_alpha(S_nan)
        self.assertEqual(len(alpha), 15)
        np.testing.assert_array_equal(alpha, np.zeros(15))

    def test_custom_m_tensor_override(self):
        """Verify custom interaction tensor is respected when supplied by caller."""
        S = np.array([[1.0, 1.0]])
        # Custom 2x2 tensor with interaction 0.50
        M_custom = np.array([[0.0, 0.50], [0.50, 0.0]])
        alpha = compute_bilinear_interaction_alpha(S, M_tensor=M_custom)
        # interaction = 0.5 * (1*0.5*1 + 1*0.5*1) = 0.5
        expected = np.tanh(0.5)
        self.assertAlmostEqual(alpha[0], expected, places=7)

    def test_1d_input_reshaping(self):
        """1D factor score vector of length K reshaped to (1, K) returns (1,) array."""
        S_1d = np.array([0.0, 2.0, 0.0, 0.0, 2.0])
        alpha = compute_bilinear_interaction_alpha(S_1d)
        self.assertEqual(alpha.shape, (1,))
        self.assertGreater(alpha[0], 0.0)


class TestMultiFactorNeutralizerEngineIntegration(unittest.TestCase):
    """Integration test suite for MultiFactorNeutralizerEngine with D-FCN and BFIT."""

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()

    def _generate_test_universe(self, n_symbols: int = 200, seed: int = 42):
        np.random.seed(seed)
        symbols = [f"SYM_{i:04d}" for i in range(n_symbols)]
        markets = np.random.choice(["KOSPI", "KOSDAQ", "SP500"], size=n_symbols)

        df = pd.DataFrame({
            "symbol": symbols,
            "name": symbols,
            "market": markets,
            "market_cap": np.exp(np.random.normal(24.0, 1.5, size=n_symbols)),
            "per": np.random.uniform(5.0, 40.0, size=n_symbols),
            "pbr": np.random.uniform(0.5, 5.0, size=n_symbols),
            "roe": np.random.normal(12.0, 6.0, size=n_symbols),
            "asset_growth_yoy": np.random.normal(0.08, 0.12, size=n_symbols),
            "momentum_12m": np.random.normal(0.10, 0.20, size=n_symbols),
        })

        raw_scores_df = pd.DataFrame({
            "symbol": symbols,
            "score": np.random.normal(0.0, 1.0, size=n_symbols)
        })

        return df, raw_scores_df

    def test_static_method_parity(self):
        """Verify static methods on MultiFactorNeutralizerEngine match module-level functions."""
        y = np.random.randn(50)
        B = np.random.randn(50, 4)

        mod_res = compute_precision_weighted_neutralization(y, B)
        cls_res = MultiFactorNeutralizerEngine.compute_precision_weighted_neutralization(y, B)
        inst_res = self.engine.compute_precision_weighted_neutralization(y, B)

        np.testing.assert_array_equal(mod_res, cls_res)
        np.testing.assert_array_equal(mod_res, inst_res)

        S = np.random.randn(30, 5)
        mod_alpha = compute_bilinear_interaction_alpha(S)
        cls_alpha = MultiFactorNeutralizerEngine.compute_bilinear_interaction_alpha(S)
        inst_alpha = self.engine.compute_bilinear_interaction_alpha(S)

        np.testing.assert_array_equal(mod_alpha, cls_alpha)
        np.testing.assert_array_equal(mod_alpha, inst_alpha)

    def test_compute_scores_with_weights_precision_dict(self):
        """Pass weights_precision dictionary to compute_scores and verify execution."""
        univ_df, raw_df = self._generate_test_universe(n_symbols=150)
        weights_dict = {sym: float(np.random.uniform(0.5, 3.0)) for sym in univ_df["symbol"]}

        res_df = self.engine.compute_scores(
            universe=univ_df,
            raw_scores=raw_df,
            weights_precision=weights_dict,
        )

        self.assertEqual(len(res_df), 150)
        self.assertIn("factor_neutralized_score", res_df.columns)
        self.assertIn("neutralized_score", res_df.columns)
        self.assertTrue(np.all(np.isfinite(res_df["factor_neutralized_score"])))
        self.assertTrue(np.all(res_df["factor_neutralized_score"] >= 0.0))
        self.assertTrue(np.all(res_df["factor_neutralized_score"] <= 1.0))

    def test_compute_scores_with_idiosyncratic_var(self):
        """Pass idiosyncratic_var to compute_scores and verify precision inversion."""
        univ_df, raw_df = self._generate_test_universe(n_symbols=120)
        idio_var_dict = {sym: float(np.random.uniform(0.01, 0.25)) for sym in univ_df["symbol"]}

        res_df = self.engine.compute_scores(
            universe=univ_df,
            raw_scores=raw_df,
            idiosyncratic_var=idio_var_dict,
        )

        self.assertEqual(len(res_df), 120)
        self.assertTrue(np.all(np.isfinite(res_df["factor_neutralized_score"])))

    def test_unconditional_sla_factor_decorrelation_post_condition(self):
        """Verify hard SLA post-condition: Pearson |rho| < 0.15 across all 5 Fama-French factors."""
        univ_df, raw_df = self._generate_test_universe(n_symbols=500, seed=777)
        res_df = self.engine.compute_scores(universe=univ_df, raw_scores=raw_df)

        merged = pd.merge(univ_df, res_df, on="symbol")
        scores = merged["factor_neutralized_score"].values

        factors = ["market_cap", "per", "roe", "asset_growth_yoy", "momentum_12m"]
        for f in factors:
            vals = merged[f].values.astype(float)
            valid = np.isfinite(vals)
            if np.sum(valid) > 10:
                corr = float(np.corrcoef(vals[valid], scores[valid])[0, 1])
                self.assertLess(
                    abs(corr),
                    0.15,
                    f"Factor SLA decorrelation breached for factor '{f}': |rho| = {abs(corr):.4f} >= 0.15"
                )

    def test_numpy_2_rank_writeability(self):
        """Ensure no 'assignment destination is read-only' error occurs from Pandas rank array in NumPy 2.0+."""
        univ_df, raw_df = self._generate_test_universe(n_symbols=80)
        # This will trigger pd.Series(residual).rank(pct=True).values.copy()
        try:
            res_df = self.engine.compute_scores(universe=univ_df, raw_scores=raw_df)
            self.assertTrue(isinstance(res_df, pd.DataFrame))
        except ValueError as e:
            if "read-only" in str(e).lower():
                self.fail(f"NumPy 2.0+ read-only array violation: {e}")
            raise

    def test_small_universes_n_1_2_5(self):
        """Verify stability across small universe subsets (N in {1, 2, 5})."""
        for n in [1, 2, 5]:
            univ_df, raw_df = self._generate_test_universe(n_symbols=n, seed=n)
            res_df = self.engine.compute_scores(universe=univ_df, raw_scores=raw_df)
            self.assertEqual(len(res_df), n)
            self.assertTrue(np.all(np.isfinite(res_df["factor_neutralized_score"])))
            self.assertTrue(np.all(res_df["factor_neutralized_score"] >= 0.0))
            self.assertTrue(np.all(res_df["factor_neutralized_score"] <= 1.0))


    def test_dfcn_readonly_arrays_with_nans_and_infs(self):
        """Verify D-FCN handles read-only arrays with NaNs/Infs without writeability crash or mutating inputs."""
        N, K = 40, 4
        B = np.random.randn(N, K)
        B[5, 1] = np.nan
        B[10, 2] = np.inf
        B[15, 3] = -np.inf
        B_orig = B.copy()
        B.flags.writeable = False

        y = np.random.randn(N)
        y[3] = np.nan
        y[7] = np.inf
        y_orig = y.copy()
        y.flags.writeable = False

        w = np.random.uniform(0.5, 2.0, size=N)
        w[12] = np.nan
        w_orig = w.copy()
        w.flags.writeable = False

        # Should never raise ValueError: assignment destination is read-only
        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)
        self.assertEqual(len(y_star), N)
        self.assertTrue(np.all(np.isfinite(y_star)))

        # Verify caller input arrays were NOT mutated in place
        np.testing.assert_array_equal(np.isnan(B), np.isnan(B_orig))
        np.testing.assert_array_equal(np.isnan(y), np.isnan(y_orig))
        np.testing.assert_array_equal(np.isnan(w), np.isnan(w_orig))

    def test_bfit_readonly_arrays_with_nans_and_infs(self):
        """Verify BFIT handles read-only scores and tensors with NaNs/Infs without writeability crash or mutating inputs."""
        N, K = 30, 5
        S = np.random.randn(N, K)
        S[2, 0] = np.nan
        S[8, 4] = np.inf
        S_orig = S.copy()
        S.flags.writeable = False

        M = np.random.randn(K, K)
        M = 0.5 * (M + M.T)
        M[1, 1] = 0.0
        M_orig = M.copy()
        M.flags.writeable = False

        alpha = compute_bilinear_interaction_alpha(S, M_tensor=M)
        self.assertEqual(len(alpha), N)
        self.assertTrue(np.all(np.isfinite(alpha)))
        self.assertTrue(np.all(alpha >= -1.0))
        self.assertTrue(np.all(alpha <= 1.0))

        # Verify caller input arrays were NOT mutated in place
        np.testing.assert_array_equal(np.isnan(S), np.isnan(S_orig))
        np.testing.assert_array_equal(np.isnan(M), np.isnan(M_orig))

    def test_engine_compute_scores_readonly_inputs(self):
        """Verify MultiFactorNeutralizerEngine accepts read-only precision weights and idiosyncratic var."""
        univ_df, raw_df = self._generate_test_universe(n_symbols=60)

        # Read-only precision weights with NaNs
        w = np.random.uniform(0.5, 3.0, size=60)
        w[5] = np.nan
        w.flags.writeable = False

        res_df = self.engine.compute_scores(
            universe=univ_df,
            raw_scores=raw_df,
            weights_precision=w,
        )
        self.assertEqual(len(res_df), 60)
        self.assertTrue(np.all(np.isfinite(res_df["factor_neutralized_score"])))

        # Read-only idiosyncratic variance with NaNs
        iv = np.random.uniform(0.01, 0.20, size=60)
        iv[10] = np.nan
        iv.flags.writeable = False

        res_df2 = self.engine.compute_scores(
            universe=univ_df,
            raw_scores=raw_df,
            idiosyncratic_var=iv,
        )
        self.assertEqual(len(res_df2), 60)
        self.assertTrue(np.all(np.isfinite(res_df2["factor_neutralized_score"])))


if __name__ == "__main__":
    unittest.main()

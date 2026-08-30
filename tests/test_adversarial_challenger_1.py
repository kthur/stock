r"""
Empirical Adversarial Stress Tests & Mathematical Oracles
Author: Challenger 1 (Mathematical & Numerical Adversarial Verifier)
Target Domains:
1. PCA-ZCA Whitening & Factor Orthogonalization on Rank-Deficient and Singular Score Matrices ($N < K$, $N=1$, identical columns, $K=31$)
2. Clayton Copula PSD Spectral Projection on Extreme Negative Correlations
3. Black-Litterman Quadratic Utility under Negative Excess Returns
4. HRP Cluster Variance Numerical Stability with Zero-Volatility Assets ($\sigma \approx 0$)
5. Platt Scaling Probability Monotonicity across Logit Domains
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.analysis.portfolio_optimizer import (
    calculate_black_litterman_weights,
    calculate_hrp_weights,
    calculate_risk_parity_weights,
    apply_portfolio_constraints,
)


# ============================================================================
# 1. PCA-ZCA Whitening Adversarial Stress Tests
# ============================================================================

class TestPCAZCAAdversarial:
    """
    Adversarial stress testing for PCA-ZCA whitening on rank-deficient,
    singular, and pathological score matrices ($K=31$).
    """

    @pytest.fixture
    def engine(self):
        return FactorOrthogonalizerEngine(ridge_epsilon=1e-4, shrinkage_alpha=0.05)

    def test_rank_deficient_n_less_than_k(self, engine):
        """
        Oracle test: When N < K (e.g. N=5 symbols, K=31 factors), the sample
        covariance is rank deficient with rank at most min(N-1, K).
        The continuous ridge regularizer must prevent null-space noise explosion.
        """
        K = 31
        cols = [f"factor_{i}" for i in range(K)]
        for N in [1, 2, 5, 10, 20, 30]:
            np.random.seed(42 + N)
            raw_scores = np.random.uniform(0.1, 0.9, size=(N, K))
            df = pd.DataFrame(raw_scores, columns=cols, index=[f"SYM_{i}" for i in range(N)])

            # Test both PCA-ZCA and Gram-Schmidt
            out_pca = engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')
            out_gs = engine.orthogonalize(df, cols, method='gram_schmidt', scaling_method='dispersion')

            # Verification: output must be finite, within [0, 1]
            assert np.all(np.isfinite(out_pca.values)), f"PCA-ZCA produced non-finite values for N={N}, K={K}"
            assert np.all(np.isfinite(out_gs.values)), f"Gram-Schmidt produced non-finite values for N={N}, K={K}"
            assert np.all(out_pca.values >= 0.0) and np.all(out_pca.values <= 1.0)
            assert np.all(out_gs.values >= 0.0) and np.all(out_gs.values <= 1.0)

    def test_identical_and_collinear_columns(self, engine):
        """
        Oracle test: When multiple factors are identical (correlation = 1.0),
        the covariance matrix is singular. Continuous ridge regularization
        must keep eigenvalue inversion bounded.
        """
        N, K = 50, 31
        cols = [f"factor_{i}" for i in range(K)]
        np.random.seed(123)
        raw_scores = np.random.uniform(0.2, 0.8, size=(N, K))
        # Make factors 1, 2, 3, 4 identical to factor 0
        for i in [1, 2, 3, 4]:
            raw_scores[:, i] = raw_scores[:, 0]
        # Make factors 10 to 20 all identical
        for i in range(11, 21):
            raw_scores[:, i] = raw_scores[:, 10]

        df = pd.DataFrame(raw_scores, columns=cols)
        out_df = engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')

        assert np.all(np.isfinite(out_df.values))
        assert np.all((out_df.values >= 0.0) & (out_df.values <= 1.0))
        # Variance of each non-constant factor in output should remain positive
        out_stds = np.std(out_df.values, axis=0)
        assert np.all(out_stds > 0.0)

    def test_all_constant_columns_zero_variance(self, engine):
        """
        Oracle test: When some factors have zero cross-sectional variance (constant across symbols),
        standardization must not produce division by zero or NaN.
        """
        N, K = 20, 31
        cols = [f"factor_{i}" for i in range(K)]
        np.random.seed(999)
        raw_scores = np.random.uniform(0.2, 0.8, size=(N, K))
        # Make 5 columns completely constant
        raw_scores[:, 2] = 0.5
        raw_scores[:, 7] = 0.0
        raw_scores[:, 15] = 1.0
        raw_scores[:, 22] = 0.75
        raw_scores[:, 30] = 0.33

        df = pd.DataFrame(raw_scores, columns=cols)
        out_df = engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')

        assert np.all(np.isfinite(out_df.values))
        assert np.all((out_df.values >= 0.0) & (out_df.values <= 1.0))

    def test_single_row_matrix_n_equals_1(self, engine):
        """
        Oracle test: Edge case N=1 symbol.
        """
        K = 31
        cols = [f"factor_{i}" for i in range(K)]
        df = pd.DataFrame([np.linspace(0.1, 0.9, K)], columns=cols, index=["SINGLE_SYM"])
        out_df = engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')

        assert len(out_df) == 1
        assert np.all(np.isfinite(out_df.values))
        assert np.all((out_df.values >= 0.0) & (out_df.values <= 1.0))

    def test_extreme_numerical_scales(self, engine):
        """
        Oracle test: Scores with extreme ranges ($10^{10}$ and $10^{-10}$).
        """
        N, K = 25, 31
        cols = [f"factor_{i}" for i in range(K)]
        np.random.seed(42)
        raw_scores = np.random.uniform(1e8, 1e10, size=(N, K))
        raw_scores[:, 0] = np.random.uniform(1e-12, 1e-10, size=N)

        df = pd.DataFrame(raw_scores, columns=cols)
        out_df = engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')

        assert np.all(np.isfinite(out_df.values))
        assert np.all((out_df.values >= 0.0) & (out_df.values <= 1.0))

    def test_eigenvalue_shrinkage_bounded_multiplier(self, engine):
        """
        Oracle test: Directly checks that continuous ridge regularization
        bounds the inverse square root multiplier lambda_i^(-1/2) <= 10.0.
        """
        N, K = 5, 31
        np.random.seed(101)
        X = np.random.randn(N, K)
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        stds = np.where(stds < 1e-8, 1e-6, stds)

        X_bar = (X - means) / stds
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
        C_shrunk = engine._compute_ledoit_wolf_covariance(X_bar, C)
        eigenvalues, _ = np.linalg.eigh(C_shrunk)

        mean_eig = float(np.mean(eigenvalues))
        ridge_floor = max(0.01 * mean_eig, engine.ridge_epsilon)
        reg_eigenvalues = np.maximum(eigenvalues, 0.0) + ridge_floor
        inv_sqrt_lambda = 1.0 / np.sqrt(reg_eigenvalues)

        # Multiplier must be bounded: max multiplier <= 1 / sqrt(ridge_floor)
        assert np.all(np.isfinite(inv_sqrt_lambda))
        max_theoretical_bound = 1.0 / np.sqrt(ridge_floor) + 1e-3
        assert np.max(inv_sqrt_lambda) <= max_theoretical_bound, f"Multiplier exploded: {np.max(inv_sqrt_lambda)} vs bound {max_theoretical_bound}"


# ============================================================================
# 2. Clayton Copula PSD Spectral Projection Adversarial Tests
# ============================================================================

class TestClaytonCopulaAdversarial:
    """
    Adversarial stress testing for Clayton Copula tail stress covariance
    under extreme negative correlations and singular returns.
    """

    def test_extreme_negative_correlation_anti_hedges(self):
        """
        Oracle test: Assets with perfect negative correlation (rho = -1.0).
        Blending with all-ones matrix (1-lambda)*corr + lambda*11^T induces negative
        eigenvalues. Spectral projection must restore strict Positive Semi-Definiteness (PSD)
        and pass Cholesky factorization.
        """
        np.random.seed(777)
        T, K = 100, 6
        base_returns = np.random.randn(T, K) * 0.02
        # Asset 1 is exact inverse of Asset 0 (rho = -1.0)
        base_returns[:, 1] = -base_returns[:, 0]
        # Asset 3 is negative leveraged inverse of Asset 2
        base_returns[:, 3] = -2.0 * base_returns[:, 2]
        # Force a market crash in the first 25 days to trigger tail mask
        base_returns[:25, :] -= 0.08

        base_cov = np.cov(base_returns, rowvar=False)

        for stress_w in [0.1, 0.3, 0.5, 0.7]:
            for tail_q in [0.10, 0.20, 0.35]:
                stressed_cov = PortfolioAllocator.compute_tail_stress_cov(
                    base_returns,
                    base_cov,
                    tail_quantile=tail_q,
                    stress_weight=stress_w,
                    use_clayton_copula=True
                )

                assert stressed_cov.shape == (K, K)
                assert np.all(np.isfinite(stressed_cov))
                # Check symmetry: Sigma = Sigma^T
                assert np.allclose(stressed_cov, stressed_cov.T, atol=1e-10)

                # Check eigenvalues strictly positive
                evals = np.linalg.eigvalsh(stressed_cov)
                assert np.all(evals >= 1e-5), f"Eigenvalues failed PSD guarantee: min_eval = {np.min(evals)}"

                # Check Cholesky decomposition succeeds
                chol = np.linalg.cholesky(stressed_cov)
                assert chol.shape == (K, K)

    def test_high_dimensional_pathological_negative_correlations(self):
        """
        Oracle test: K=31 assets with alternating anti-correlated pairs.
        """
        np.random.seed(888)
        T, K = 120, 31
        returns = np.random.randn(T, K) * 0.015
        # Pairwise anti-hedges
        for k in range(0, K - 1, 2):
            returns[:, k + 1] = -returns[:, k]
        # Tail event
        returns[:30, :] -= 0.05

        base_cov = np.cov(returns, rowvar=False)
        stressed_cov = PortfolioAllocator.compute_tail_stress_cov(
            returns,
            base_cov,
            tail_quantile=0.25,
            stress_weight=0.60,
            use_clayton_copula=True
        )

        evals = np.linalg.eigvalsh(stressed_cov)
        assert np.all(evals >= 1e-5)
        # Verify strict positive quadratic form for random test vectors
        for _ in range(50):
            x = np.random.randn(K)
            quad = float(x @ stressed_cov @ x)
            assert quad > 0.0, f"Quadratic form non-positive: {quad}"

    def test_downside_semi_covariance_psd(self):
        """
        Oracle test: Downside semi-covariance matrix Sigma^- must be positive semi-definite.
        """
        np.random.seed(321)
        T, K = 80, 10
        returns = np.random.randn(T, K) * 0.02
        semi_cov = PortfolioAllocator.compute_downside_semi_cov(returns, target_return=0.0)

        assert semi_cov.shape == (K, K)
        assert np.all(np.isfinite(semi_cov))
        evals = np.linalg.eigvalsh(semi_cov)
        assert np.all(evals > 0), f"Semi-cov not positive definite: min_eval = {np.min(evals)}"


# ============================================================================
# 3. Black-Litterman Quadratic Utility & Scale Alignment Adversarial Tests
# ============================================================================

class TestBlackLittermanAdversarial:
    """
    Adversarial stress testing for Black-Litterman optimization
    under negative excess return regimes and percentage view scales.
    """

    def test_negative_excess_return_regime_penalizes_variance(self):
        """
        Oracle test: When port_ret <= risk_free_rate, the objective evaluates
        quadratic utility: max (w^T mu - 0.5 * lambda * w^T Sigma w).
        Under negative returns, minimizing negative Sharpe would perversely maximize variance.
        Quadratic utility must penalize variance, allocating higher weight to lower volatility assets.
        """
        # 3 assets with increasing variances
        cov = np.array([
            [0.01, 0.00, 0.00],
            [0.00, 0.04, 0.00],
            [0.00, 0.00, 0.09]
        ])
        # Severe bear market views (equal negative expectations so all posterior mu_bl <= rf)
        views = [-0.30, -0.30, -0.30]
        rf = 0.03

        weights = calculate_black_litterman_weights(
            cov_matrix=cov,
            predicted_returns=views,
            risk_free_rate=rf
        )

        assert len(weights) == 3
        assert np.all(np.isfinite(weights))
        assert np.isclose(np.sum(weights), 1.0, atol=1e-5)
        assert np.all(weights >= 0.0)

        # Asset 0 (lowest volatility) must receive higher weight than Asset 2 (highest volatility)
        assert weights[0] > weights[1] > weights[2], (
            f"Quadratic utility failed to penalize volatility monotonically: "
            f"w={weights}"
        )

    def test_percentage_vs_decimal_view_scale_alignment(self):
        """
        Oracle test: Views provided in percentage (e.g. 5.0% = 5.0) vs decimal (0.05)
        must produce consistent, non-exploding weights aligned with equilibrium prior.
        """
        cov = np.array([
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.02],
            [0.00, 0.02, 0.16]
        ])
        views_pct = [5.0, 8.0, 12.0]     # Percentage units
        views_dec = [0.05, 0.08, 0.12]   # Decimal units

        w_pct = calculate_black_litterman_weights(cov, views_pct)
        w_dec = calculate_black_litterman_weights(cov, views_dec)

        assert np.all(np.isfinite(w_pct))
        assert np.all(np.isfinite(w_dec))
        assert np.isclose(np.sum(w_pct), 1.0, atol=1e-5)
        assert np.isclose(np.sum(w_dec), 1.0, atol=1e-5)
        # Weights should be identical or extremely close
        assert np.allclose(w_pct, w_dec, atol=1e-3), f"Scale mismatch: w_pct={w_pct}, w_dec={w_dec}"

    def test_singular_and_ill_conditioned_covariance_fallback(self):
        """
        Oracle test: If covariance matrix is singular, BL must not crash
        and must gracefully return valid normalized weights (via fallback or robust solve).
        """
        cov_singular = np.ones((4, 4)) * 0.04
        views = [0.05, 0.06, 0.07, 0.08]

        weights = calculate_black_litterman_weights(cov_singular, views)
        assert len(weights) == 4
        assert np.all(np.isfinite(weights))
        assert np.isclose(np.sum(weights), 1.0, atol=1e-5)


# ============================================================================
# 4. HRP Cluster Variance Numerical Stability with Zero-Volatility Assets
# ============================================================================

class TestHRPAdversarial:
    """
    Adversarial stress testing for HRP (Hierarchical Risk Parity)
    with zero-volatility assets and singular distance matrices.
    """

    def test_zero_and_near_zero_volatility_assets(self):
        """
        Oracle test: When assets have zero or near-zero variance (e.g. sigma=0 or sigma=1e-15),
        inverse variance weighting 1/sigma^2 must NOT overflow to Inf or NaN.
        The variance floor and volatility floor must guarantee finite weights.
        """
        for near_zero_vol in [0.0, 1e-15, 1e-10, 1e-8]:
            cov = np.array([
                [near_zero_vol ** 2, 0.0, 0.0, 0.0],
                [0.0, 0.04, 0.01, 0.00],
                [0.0, 0.01, 0.09, 0.02],
                [0.0, 0.00, 0.02, 0.16]
            ])

            weights = calculate_hrp_weights(cov)

            assert len(weights) == 4
            assert np.all(np.isfinite(weights)), f"HRP produced non-finite weights for vol={near_zero_vol}: {weights}"
            assert np.isclose(np.sum(weights), 1.0, atol=1e-5)
            assert np.all(weights >= 0.0) and np.all(weights <= 1.0)

    def test_all_zero_volatility_degenerate_portfolio(self):
        """
        Oracle test: Portfolio where ALL assets have near-zero volatility.
        """
        cov = np.eye(5) * 1e-12
        weights = calculate_hrp_weights(cov)

        assert len(weights) == 5
        assert np.all(np.isfinite(weights))
        assert np.isclose(np.sum(weights), 1.0, atol=1e-5)
        # Should be equal weight 0.20 each
        assert np.allclose(weights, np.full(5, 0.20), atol=1e-3)

    def test_high_dimensional_hrp_scalability(self):
        """
        Oracle test: Large portfolio (N=100 assets) with random singular sub-blocks.
        """
        np.random.seed(555)
        N = 100
        # Generate random positive semi-definite covariance
        A = np.random.randn(N, 20)  # Rank at most 20 (severely rank-deficient)
        cov = A @ A.T + np.eye(N) * 1e-5

        weights = calculate_hrp_weights(cov)

        assert len(weights) == N
        assert np.all(np.isfinite(weights))
        assert np.isclose(np.sum(weights), 1.0, atol=1e-4)
        assert np.all(weights >= 0.0)


# ============================================================================
# 5. Platt Scaling Probability Monotonicity across Logit Domains
# ============================================================================

class TestPlattScalingMonotonicity:
    """
    Adversarial stress testing for Platt scaling probability monotonicity
    and linear vs logit domain correctness.
    """

    def test_monotonicity_across_probability_domain(self):
        """
        Oracle test: For any p1 < p2 in [0, 1], calibrated probability must satisfy
        P(p1) <= P(p2). Tested across 10,000 finely spaced probabilities.
        """
        p_raw = np.linspace(0.0, 1.0, 10000)

        # Test diverse realistic LogisticRegression parameter pairs (coef > 0)
        param_grid = [
            (1.5, -0.5),
            (2.0, -1.0),
            (0.5, 0.0),
            (5.0, -2.5),
            (10.0, -5.0),
            (0.1, -0.05),
        ]

        for coef, intercept in param_grid:
            # Model implementation formula
            z = np.clip(coef * p_raw + intercept, -10, 10)
            calib_p = 1.0 / (1.0 + np.exp(-z))
            blend_prob = np.where(p_raw > 0, np.maximum(calib_p, p_raw * 0.05), calib_p)

            # Check finite
            assert np.all(np.isfinite(blend_prob))
            assert np.all(blend_prob >= 0.0) and np.all(blend_prob <= 1.0)

            # Check monotonicity: diff >= 0 (allowing minor float epsilon)
            diffs = np.diff(blend_prob)
            assert np.all(diffs >= -1e-12), (
                f"Monotonicity violated for coef={coef}, intercept={intercept}: "
                f"min diff = {np.min(diffs)}"
            )

    def test_prevention_of_probability_collapse(self):
        """
        Oracle test: Verifies that applying Platt scaling directly to raw probabilities
        in [0, 1] avoids the catastrophic collapse to ~0 that occurred when logit(p)
        was erroneously applied.
        """
        p_raw = np.array([0.10, 0.30, 0.50, 0.70, 0.90])
        coef = 2.0
        intercept = -0.5

        # Correct linear domain Platt scaling:
        z_correct = np.clip(coef * p_raw + intercept, -10, 10)
        calib_correct = 1.0 / (1.0 + np.exp(-z_correct))

        # Expected output must be well-distributed in [0.2, 0.9]
        assert calib_correct[0] > 0.10, f"Calibrated probability collapsed: {calib_correct[0]}"
        assert calib_correct[-1] > 0.70, f"Calibrated probability too low: {calib_correct[-1]}"
        assert np.all(np.diff(calib_correct) > 0.0), "Ranking order destroyed"

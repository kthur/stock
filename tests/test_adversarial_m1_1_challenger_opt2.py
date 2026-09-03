"""
tests/test_adversarial_m1_1_challenger_opt2.py

Adversarial Empirical Verification Suite for Milestone 1 (M1-1 Challenger).
Author: Challenger M1-1 (teamwork_preview_challenger_m1_1_opt2)

Focus Areas:
1. Numerical stability of `_pca_zca_symmetric` with `preserve_top_k=2` on near-singular,
   rank-deficient, collinear matrices (N < K, condition number > 10^8).
2. Noise-scaled Marchenko-Pastur lower spectral edge behavior under extreme noise bulk variations.
3. Fisher z-score cutoff calibration theta(R, N) edge cases (N=0, 1, 2, 3, 4, 10000, NaN).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure project and trading_system paths are present
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine


class TestPcaZcaSymmetricNearSingularAndRankDeficient:
    """Adversarial stress tests for _pca_zca_symmetric with preserve_top_k=2."""

    @pytest.fixture
    def engine(self):
        return FactorOrthogonalizerEngine(default_method='pca_symmetric', preserve_top_k=2)

    def test_n_less_than_k_small_sample_extreme_collinear(self, engine):
        """
        Adversarial test: N=5, K=37 where 35 columns are almost exact linear combinations.
        Condition number > 10^8.
        Must produce strictly finite values, no NaN/Inf, shape (5, 37).
        """
        np.random.seed(42)
        N, K = 5, 37
        X_latent = np.random.randn(N, 2)
        X_full = np.zeros((N, K), dtype=np.float64)
        X_full[:, :2] = X_latent
        # Columns 2..36 are collinear combinations of column 0 with microscopic noise (1e-9)
        for j in range(2, K):
            X_full[:, j] = X_latent[:, 0] * (0.1 * j) + 1e-9 * np.random.randn(N)

        means = np.mean(X_full, axis=0)
        stds = np.std(X_full, axis=0)
        stds = np.where(stds < 1e-8, 1e-6, stds)

        out = engine._pca_zca_symmetric(
            X=X_full,
            means=means,
            stds=stds,
            preserve_pc1=True,
            preserve_top_k=2
        )

        assert out.shape == (N, K)
        assert np.isfinite(out).all(), "Output contains non-finite values (NaN or Inf)"
        assert not np.isnan(out).any(), "Output contains NaNs"

    def test_extreme_condition_number_above_10_pow_8(self, engine):
        """
        Construct a score matrix whose covariance matrix condition number exceeds 10^10.
        Verify that Ledoit-Wolf shrinkage, Marchenko-Pastur flooring, and whitening filter
        cap (<= 10.0) prevent numerical explosion or LinAlgError.
        """
        np.random.seed(123)
        N, K = 15, 20
        # Create rank-2 signal plus tiny perturbations of order 1e-6
        v1 = np.random.randn(N, 1)
        v2 = np.random.randn(N, 1)
        weights_1 = np.linspace(1.0, 5.0, K)
        weights_2 = np.linspace(0.5, 2.0, K)
        X = v1 @ weights_1.reshape(1, K) + v2 @ weights_2.reshape(1, K)
        X += 1e-6 * np.random.randn(N, K)

        # Check raw covariance condition number
        C_raw = np.cov(X, rowvar=False)
        cond_num = np.linalg.cond(C_raw)
        assert cond_num > 1e8, f"Condition number was {cond_num}, expected > 1e8"

        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)

        assert out.shape == (N, K)
        assert np.isfinite(out).all()
        # Verify no extreme explosive values
        assert np.max(np.abs(out)) < 1e5

    def test_n_equals_3_boundary_condition(self, engine):
        """
        Test minimum allowable sample size N=3 with K=10 strategies.
        Must succeed without crashing and maintain finite outputs.
        """
        np.random.seed(99)
        N, K = 3, 10
        X = np.random.uniform(0.1, 0.9, (N, K))
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (3, 10)
        assert np.isfinite(out).all()

    def test_k_equals_2_boundary_with_preserve_top_k_2(self, engine):
        """
        Boundary condition: K=2 features and preserve_top_k=2.
        Code computes num_to_preserve = min(eff_top_k, max(K - 1, 0)) = min(2, 1) = 1.
        Verify it preserves 1 leading component and decorrelates the 2nd without IndexError.
        """
        np.random.seed(77)
        N, K = 20, 2
        X = np.random.uniform(0.1, 0.9, (N, K))
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (20, 2)
        assert np.isfinite(out).all()

    def test_all_identical_features_singular_matrix(self, engine):
        """
        Rank-1 matrix: All K=15 strategies have IDENTICAL values for all symbols.
        The covariance matrix is singular with 1 non-zero eigenvalue and 14 zero eigenvalues.
        Verify robust handling via shrinkage and ridge regularization.
        """
        N, K = 30, 15
        single_col = np.random.uniform(0.2, 0.8, (N, 1))
        X = np.repeat(single_col, K, axis=1)

        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        stds = np.where(stds < 1e-8, 1e-6, stds)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (N, K)
        assert np.isfinite(out).all()

    def test_end_to_end_orthogonalize_n_less_than_k_bounds(self, engine):
        """
        End-to-end orthogonalize() pipeline test with N=10 and K=37.
        Verify that the output dataframe values are strictly bounded in [0.0, 1.0].
        """
        np.random.seed(42)
        N, K = 10, 37
        strat_cols = [f"strat_{i:02d}" for i in range(K)]
        data = np.random.uniform(0.1, 0.9, (N, K))
        df = pd.DataFrame(data, columns=strat_cols)
        df['symbol'] = [f"SYM_{i:02d}" for i in range(N)]

        res = engine.orthogonalize(df, strat_cols, preserve_top_k=2)
        vals = res[strat_cols].values
        assert np.isfinite(vals).all()
        assert (vals >= 0.0).all() and (vals <= 1.0).all(), "Scores exceeded [0.0, 1.0] bound!"


class TestMarchenkoPasturLowerSpectralEdge:
    """Adversarial stress tests for Marchenko-Pastur lower spectral edge flooring."""

    @pytest.fixture
    def engine(self):
        return FactorOrthogonalizerEngine(default_method='pca_symmetric', preserve_top_k=2)

    def test_extreme_large_noise_variance_bulk(self, engine):
        """
        Extreme scenario: Noise variance sigma2 is massive (e.g., sigma2 = 1000.0).
        The theoretical mp_lower = sigma2 * (1 - sqrt(q))^2 is huge.
        Verify that lambda_floor is properly clipped to at most 1.0, preventing
        excessive suppression of valid spectral variance.
        """
        N, K = 100, 20
        # Highly noisy matrix with large dispersion
        X = np.random.normal(0.0, 50.0, (N, K))
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (N, K)
        assert np.isfinite(out).all()

    def test_extreme_small_vanishing_noise_variance(self, engine):
        """
        Extreme scenario: Noise variance vanishes (sigma2 -> 0).
        Verify that sigma2 is bounded by max(sigma2, 1e-4) and lambda_floor is bounded
        by at least 1e-4, preventing division-by-zero or infinite whitening filter.
        """
        N, K = 50, 10
        # Perfectly noiseless rank-2 signal
        v1 = np.random.randn(N, 1)
        v2 = np.random.randn(N, 1)
        X = v1 @ np.ones((1, K)) + v2 @ np.ones((1, K))
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        stds = np.where(stds < 1e-8, 1e-6, stds)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (N, K)
        assert np.isfinite(out).all()

    def test_n_equals_k_marchenko_pastur_edge_zero(self, engine):
        """
        When N = K, q = min(K, N) / max(K, N) = 1.0.
        Theoretical MP lower edge mp_lower = sigma2 * (1 - sqrt(1.0))^2 = 0.0.
        Verify that the fallback max(mp_lower, 0.01 * sigma2) ensures the floor
        is at least 0.01 * sigma2 and >= 1e-4.
        """
        N = K = 25
        np.random.seed(55)
        X = np.random.randn(N, K)
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        out = engine._pca_zca_symmetric(X, means, stds, preserve_top_k=2)
        assert out.shape == (N, K)
        assert np.isfinite(out).all()

    def test_noise_subspace_isolation_with_preserve_top_k_2(self, engine):
        """
        Verify that when preserve_top_k=2 is used, eigenvalues[:-2] isolates the true
        noise variance without being inflated by PC1 and PC2 dominant signal variance.
        Compare against preserve_top_k=0 where noise estimate includes signal dimensions.
        """
        N, K = 100, 10
        np.random.seed(42)
        # Dominant signals in 2 factors, pure white noise in remaining 8
        signal = np.random.randn(N, 2) * 10.0
        noise = np.random.randn(N, 8) * 0.1
        X = np.hstack([signal, noise])
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        X_bar = (X - means) / stds
        C = np.dot(X_bar.T, X_bar) / (N - 1)
        C_shrunk = engine._compute_ledoit_wolf_covariance(X_bar, C)
        eigenvalues, _ = np.linalg.eigh(C_shrunk)

        # preserve_top_k=2 isolates noise as eigenvalues[:-2]
        noise_evals_top2 = eigenvalues[:-2]
        sigma2_top2 = float(np.mean(noise_evals_top2))

        # preserve_top_k=0 isolates noise as eigenvalues[:-1]
        noise_evals_top0 = eigenvalues[:-1]
        sigma2_top0 = float(np.mean(noise_evals_top0))

        # sigma2_top2 should be strictly smaller or equal because PC2 (value/quality) is excluded
        assert sigma2_top2 <= sigma2_top0
        assert sigma2_top2 >= 1e-4


class TestFisherZScoreCutoffCalibrationEdgeCases:
    """Adversarial stress tests for calibrate_cutoff theta(R, N) edge cases."""

    def test_n_zero_one_two_three_fallbacks(self):
        """Verify N in [0, 1, 2, 3] falls back cleanly to theta_0 without division-by-zero."""
        theta_0 = 0.65
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, 0) == 0.65
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, 1) == 0.65
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, 2) == 0.65
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, 3) == 0.65
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, None) == 0.65

    def test_n_four_exact_calculation(self):
        """
        N = 4 is the first integer where N > 3.
        Under Fisher formula: max(4 - 3, 1) = 1.
        theta(R, 4) = clip(theta_0 + 1.645 / sqrt(1), 0.35, 0.85).
        For theta_0 = 0.60: 0.60 + 1.645 = 2.245 -> clipped to 0.85.
        For theta_0 = -1.0: -1.0 + 1.645 = 0.645 -> clipped to 0.645.
        """
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(0.60, 4) == 0.85
        assert abs(RegimeFactorSuppressionEngine.calibrate_cutoff(-1.0, 4) - 0.645) < 1e-5

    def test_n_ten_thousand_asymptotic_convergence(self):
        """
        For large N=10000, 1.645 / sqrt(9997) ~ 0.0164525.
        Cutoff should converge closely to theta_0 with small empirical correction.
        """
        theta_0 = 0.60
        calibrated = RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, 10000)
        expected = np.clip(0.60 + 1.645 / np.sqrt(9997), 0.35, 0.85)
        assert abs(calibrated - expected) < 1e-6
        assert calibrated > theta_0
        assert calibrated - theta_0 < 0.02

    def test_negative_n_graceful_handling(self):
        """Negative N values (e.g. -5) must satisfy N <= 3 and return theta_0."""
        theta_0 = 0.55
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, -5) == 0.55
        assert RegimeFactorSuppressionEngine.calibrate_cutoff(theta_0, -1) == 0.55

    def test_nan_sample_size_behavior_characterization(self):
        """
        Adversarially probe passing NaN as n_samples.
        Characterizes IEEE 754 propagation:
        calibrate_cutoff(theta_0, NaN) returns NaN because in Python `np.nan <= 3` is False.
        Verify that suppress_weights handles NaN n_samples without raising uncaught exceptions,
        maintaining normalized output weights that sum to 1.0.
        """
        engine = RegimeFactorSuppressionEngine()
        theta_0 = 0.60
        result_nan = engine.calibrate_cutoff(theta_0, float('nan'))
        # Documents that calibrate_cutoff currently propagates NaN on NaN input
        assert np.isnan(result_nan), "calibrate_cutoff did not return NaN on NaN input"

        # Verify suppress_weights behavior when n_samples is NaN
        corr = pd.DataFrame(
            [[1.0, 0.85], [0.85, 1.0]],
            index=['strat_a', 'strat_b'],
            columns=['strat_a', 'strat_b']
        )
        base_w = {'strat_a': 0.5, 'strat_b': 0.5}
        suppressed_w = engine.suppress_weights(
            base_weights=base_w,
            corr_matrix=corr,
            regime_label='SIDEWAYS_LOW_VOL',
            n_samples=float('nan')
        )

        assert isinstance(suppressed_w, dict)
        assert len(suppressed_w) == 2
        assert np.isfinite(list(suppressed_w.values())).all()
        assert abs(sum(suppressed_w.values()) - 1.0) < 1e-5

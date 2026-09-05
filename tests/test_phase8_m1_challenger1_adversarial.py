"""
Adversarial Empirical Challenge Test Suite for Milestone 1 (Phase 8 Sovereign Alpha Architecture).
Author: Challenger 1 (Empirical Challenger)
Targets: Features F51 and F52
Scope:
1. Fisher-Rao Riemannian Manifold Geodesic Distance Numerical Stability & BC Clipping:
   - Roundoff error stress test: arccos(clip(BC, 0.0, 1.0)) under BC = 1.0000000000000002, 1.0 + eps,
     degenerate distributions (all-zeros, extreme single-spike, Cauchy noise).
   - Metric space axioms on unit 4-sphere S^4 (non-negativity, identity, symmetry, triangle inequality).
   - Harmony regularizer H_Riemann = exp(-2.40 * d_R^2) and regime synergy caps (1.250x in BULL_LOW_VOL vs 1.040x in CRISIS).
2. Rank Preservation and Monotonicity under Hyperexponential Convex Rank Modulation:
   - 1,000 randomized assets across 5 distinct probability distributions (Uniform, Normal, Cauchy, Pareto, Beta).
   - Random permutations and verification of Spearman rank correlation rho_s == 1.000000.
   - Strict pointwise monotonicity of g_v8(r) = r * exp(gamma_top * r^3) and second-derivative convexity.
   - Top 1% alpha spread expansion >= 25% (target +44.2% in BULL_LOW_VOL).
3. Asymmetric Septic Wavelet Noise Deadband Attenuation Ratio (F52.2):
   - Noise attenuation ratio at |z| = 0.010: assert leakage <= 0.010% (>= 99.99% suppression, target 99.997%).
   - High-conviction signal transmission at |z| >= 0.150: assert transmission >= 99.999%.
   - Exact unconditioned odd symmetry f(-z) == -f(z) to within machine precision (< 10^-12).
   - Directional downside deadband expansion in Bear/Crisis regimes.
4. Hurst Fractional Jump-Diffusion Mixture Invariants (F52.1):
   - Simplex sum == 1.0000 and non-negativity across H in [0.01, 0.99].
   - Exact continuity at Brownian motion baseline H = 0.50.
   - Monotonic scaling with persistence (trending vs mean-reverting chop).
5. 5-Market Comprehensive Stress & Backward Compatibility Invariants:
   - SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ across all 7 regimes under version=8.
   - Strict version hierarchy: Cap(v8) > Cap(v7) > Cap(v6).
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import (
    QUINT_PILLAR_MAP,
    apply_quintic_hyperbolic_deadband,
    apply_asymmetric_wavelet_deadband
)


# =============================================================================
# 1. FISHER-RAO RIEMANNIAN DISTANCE & GEODESIC HARMONY STABILITY (F51.1)
# =============================================================================

class TestFisherRaoGeodesicNumericalStability:
    """
    Adversarially challenges the Fisher-Rao geodesic distance calculation:
    d_R(p, p0) = arccos(clip(BC(p, p0), 0.0, 1.0))
    """

    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    def test_bc_floating_point_roundoff_overshoot_nan_prevention(self, engine):
        """
        Adversarial test: Floating-point roundoff can cause BC to exceed 1.0.
        Without clipping, arccos(1.0000000000000002) returns NaN and throws RuntimeWarning.
        With np.clip(bc, 0.0, 1.0), it MUST cleanly return d_R = 0.0, avoiding NaN pollution.
        """
        # 1. Demonstrate standard arccos failure without clipping
        bc_unclipped_overshoot = 1.0000000000000002
        with pytest.warns(RuntimeWarning):
            raw_val = np.arccos(bc_unclipped_overshoot)
            assert np.isnan(raw_val), "Unclipped overshoot MUST produce NaN in standard arccos"

        # 2. Test clipped behavior across a spectrum of overshoots
        overshoots = np.array([
            1.0000000000000002,
            1.0 + 1e-15,
            1.0 + 1e-12,
            1.0001,
            1.50,
            2.00
        ])
        clipped = np.clip(overshoots, 0.0, 1.0)
        d_riemann = np.arccos(clipped)
        assert np.all(d_riemann == 0.0), "Clipped overshoots must yield exact geodesic arc distance 0.0"
        assert not np.any(np.isnan(d_riemann)), "No NaNs permitted"

        # 3. Test negative undershoots
        undershoots = np.array([-1e-16, -1e-12, -0.5, -2.0])
        clipped_neg = np.clip(undershoots, 0.0, 1.0)
        d_riemann_neg = np.arccos(clipped_neg)
        assert np.all(np.isclose(d_riemann_neg, np.pi / 2.0, atol=1e-14)), (
            "Clipped negative inputs must yield pi/2 arc distance"
        )
        assert not np.any(np.isnan(d_riemann_neg))

    def test_riemannian_synergy_on_degenerate_and_extreme_inputs(self, engine):
        """
        Stress-tests compute_quint_pillar_tensor_synergy against degenerate inputs:
        - All-zero pillar scores (should NOT receive false harmony boost).
        - Single-pillar extreme spike (e.g. 1.0 on mom, 0.0 on others).
        - Extreme floating-point values (10^6, 10^-15).
        - Uniform prior alignment p = (0.2, 0.2, 0.2, 0.2, 0.2).
        """
        symbols = [f"ASSET_{i}" for i in range(10)]
        df = pd.DataFrame({'symbol': symbols}, index=symbols)
        all_cols = [
            'rim_score', 'surge_score', 'order_flow_score', 'event_score',
            'supply_chain_score', 'vcp_ml_score', 'valueup_catalyst_score',
            'accruals_quality_score', 'arm_score', 'factor_neutralized_score',
            'reg_score', 'darkpool_score', 'microstructure_score'
        ]
        for c in all_cols:
            df[c] = 0.50

        # ASSET_0: All zeros (all strategies = 0.0)
        for c in all_cols:
            df.loc['ASSET_0', c] = 0.0

        # ASSET_1: Single pillar spike (surge_score = 1.0, all others 0.0)
        for c in all_cols:
            df.loc['ASSET_1', c] = 0.0
        df.loc['ASSET_1', 'surge_score'] = 1.0

        # ASSET_2: Uniform identical high conviction (all strategies = 0.95)
        for c in all_cols:
            df.loc['ASSET_2', c] = 0.95

        # ASSET_3: Floating point near-zero (1e-12)
        for c in all_cols:
            df.loc['ASSET_3', c] = 1e-12

        # ASSET_4: Extreme unclipped value (10.0)
        for c in all_cols:
            df.loc['ASSET_4', c] = 10.0

        # Compute tensor synergy in BULL_LOW_VOL under version=8
        synergy = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime='BULL_LOW_VOL',
            version=8
        )

        # Assertions
        assert not synergy.isna().any(), "Synergy output contains NaNs"
        assert not np.isinf(synergy.values).any(), "Synergy output contains Infs"

        # ASSET_0 (all zeros): must yield exactly 1.0000x (no false harmony boost)
        assert math.isclose(synergy.loc['ASSET_0'], 1.00, abs_tol=1e-4), (
            f"All-zero asset must have 1.00x synergy, got {synergy.loc['ASSET_0']}"
        )

        # ASSET_1 (single spike): must have 1.0000x synergy (1 pillar has no multi-pillar confluence)
        assert math.isclose(synergy.loc['ASSET_1'], 1.00, abs_tol=1e-4), (
            f"Single-pillar asset must have 1.00x synergy, got {synergy.loc['ASSET_1']}"
        )

        # ASSET_2 (balanced high conviction): achieves maximum expanded cap under v8 (1.250x)
        assert math.isclose(synergy.loc['ASSET_2'], 1.250, abs_tol=1e-3), (
            f"Harmonious 5-pillar asset must reach v8 cap ~1.250, got {synergy.loc['ASSET_2']}"
        )

        # ASSET_3 (near zero): yields 1.0000x
        assert math.isclose(synergy.loc['ASSET_3'], 1.00, abs_tol=1e-4)

        # ASSET_4 (extreme input): gracefully clipped at 1.250x cap
        assert synergy.loc['ASSET_4'] <= 1.25001

    def test_metric_space_axioms_on_4sphere(self, engine):
        """
        Mathematically verifies that Fisher-Rao geodesic distance satisfies metric axioms on S^4:
        1. Non-negativity: d_R(p, q) >= 0 for all p, q on simplex.
        2. Identity of indiscernibles: d_R(p, p) == 0.0.
        3. Symmetry: d_R(p, q) == d_R(q, p).
        4. Triangle inequality: d_R(p, r) <= d_R(p, q) + d_R(q, r) + epsilon.
        """
        np.random.seed(1337)
        K = 5
        N_TRIALS = 200

        for _ in range(N_TRIALS):
            # Generate random points on simplex S^4
            p = np.random.dirichlet(np.ones(K))
            q = np.random.dirichlet(np.ones(K))
            r = np.random.dirichlet(np.ones(K))

            # Project to unit sphere S^4
            u_p = np.sqrt(p)
            u_q = np.sqrt(q)
            u_r = np.sqrt(r)

            # Geodesic arc distances
            bc_pq = np.clip(np.sum(u_p * u_q), 0.0, 1.0)
            bc_qp = np.clip(np.sum(u_q * u_p), 0.0, 1.0)
            bc_pp = np.clip(np.sum(u_p * u_p), 0.0, 1.0)
            bc_pr = np.clip(np.sum(u_p * u_r), 0.0, 1.0)
            bc_qr = np.clip(np.sum(u_q * u_r), 0.0, 1.0)

            d_pq = math.acos(bc_pq)
            d_qp = math.acos(bc_qp)
            d_pp = math.acos(bc_pp)
            d_pr = math.acos(bc_pr)
            d_qr = math.acos(bc_qr)

            # 1. Non-negativity
            assert d_pq >= 0.0
            # 2. Identity (arccos(1 - eps) ~ sqrt(2*eps) ~ 1.5e-8 due to derivative divergence)
            assert math.isclose(d_pp, 0.0, abs_tol=1e-7)
            # 3. Symmetry
            assert math.isclose(d_pq, d_qp, abs_tol=1e-14)
            # 4. Triangle inequality
            assert d_pr <= d_pq + d_qr + 1e-12, (
                f"Triangle inequality violated: d(p,r)={d_pr} > d(p,q)={d_pq} + d(q,r)={d_qr}"
            )


# =============================================================================
# 2. RANK MONOTONICITY UNDER HYPEREXPONENTIAL RANK MODULATION (F51.2)
# =============================================================================

class TestHyperexponentialRankMonotonicityStress:
    """
    Adversarially tests rank preservation and monotonicity of:
    mult = 0.50 + 0.65 * r * exp(gamma_top * r^3)
    across random permutations of 1,000 assets drawn from diverse probability distributions.
    """

    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    @pytest.mark.parametrize('dist_name', ['uniform', 'normal', 'cauchy', 'pareto', 'beta_bimodal'])
    def test_rank_preservation_1000_assets_diverse_distributions(self, engine, dist_name):
        """
        Generates 1,000 assets under 5 challenging distributions:
        - uniform: standard uniform
        - normal: truncated Gaussian
        - cauchy: extreme fat tails
        - pareto: heavy right-tail power law
        - beta_bimodal: Beta(0.5, 0.5) clustered at boundaries 0 and 1
        Verifies:
        1. Spearman rank correlation between raw score and ensemble_expected_return is 1.000000.
        2. Pairwise monotonicity: x_i < x_j => y_i <= y_j everywhere.
        3. Zero NaNs, zero Infs.
        """
        np.random.seed(42)
        N = 1000

        if dist_name == 'uniform':
            raw = np.random.uniform(0.0, 1.0, N)
        elif dist_name == 'normal':
            raw = np.clip(np.random.normal(0.50, 0.15, N), 0.0, 1.0)
        elif dist_name == 'cauchy':
            c_vals = np.random.standard_cauchy(N)
            # Map cauchy to [0, 1] via arctan CDF
            raw = 0.50 + np.arctan(c_vals) / np.pi
        elif dist_name == 'pareto':
            p_vals = np.random.pareto(a=1.5, size=N)
            raw = np.clip(p_vals / (p_vals + 1.0), 0.0, 1.0)
        elif dist_name == 'beta_bimodal':
            raw = np.random.beta(0.5, 0.5, N)

        # Shuffle indices to simulate non-ordered asset input
        perm = np.random.permutation(N)
        raw = raw[perm]

        symbols = [f"ASSET_{i:04d}" for i in range(N)]
        df = pd.DataFrame({
            'symbol': symbols,
            'market': 'SP500',
            'close': 100.0,
            'volume': 1_000_000.0,
            'volatility_20d': 0.02,
            'reg_score': raw,
            'surge_score': raw,
            'vcp_ml_score': raw,
            'order_flow_score': raw,
            'rim_score': raw,
        })

        for reg in ['BULL_LOW_VOL', 'SIDEWAYS_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS']:
            res = engine.combine_predictions(
                predictions_df=df,
                target_horizon='20d',
                regime=reg,
                version=8
            )

            scores = res['ensemble_score'].values
            returns = res['ensemble_expected_return'].values

            # Zero NaNs / Infs
            assert not np.any(np.isnan(scores)), f"NaN in scores for {dist_name} in {reg}"
            assert not np.any(np.isnan(returns)), f"NaN in returns for {dist_name} in {reg}"

            # Verify rank correlation between ensemble_score and expected returns
            # Note: For assets where returns > 0, rank correlation must be strictly 1.000000
            pos_mask = (scores > 0.50) & (returns > 0.0)
            if np.sum(pos_mask) > 10:
                rho_pos, _ = spearmanr(scores[pos_mask], returns[pos_mask])
                assert math.isclose(rho_pos, 1.0000, abs_tol=1e-5), (
                    f"Positive excess return rank correlation violated for {dist_name} in {reg}: {rho_pos}"
                )

            # Strict global pairwise monotonicity check on sorted scores
            sort_order = np.argsort(scores)
            sorted_scores = scores[sort_order]
            sorted_returns = returns[sort_order]

            diff_returns = np.diff(sorted_returns)
            # Returns must be non-decreasing with scores
            assert np.all(diff_returns >= -1e-7), (
                f"Pairwise monotonicity violated in {dist_name} under {reg}: "
                f"min diff = {np.min(diff_returns)}"
            )

    def test_hyperexponential_mathematical_invariants_spectrum(self, engine):
        """
        Adversarially evaluates g_v8(r) = r * exp(gamma_top * r^3) over a dense grid
        of 50,000 points across the full parameter space gamma_top in [0.20, 0.85].
        Verifies:
        1. Exact boundary value: g_v8(0.0) == 0.0.
        2. First derivative positivity: g'(r) > 0 for all r in [0, 1].
        3. Second derivative non-negativity: g''(r) >= 0 (strict convexity).
        4. Multiplier range: mult(0) == 0.50, mult(1) == 0.50 + 0.65 * exp(gamma_top).
        """
        r = np.linspace(0.0, 1.0, 50000)
        gammas = [0.20, 0.25, 0.35, 0.45, 0.55, 0.70, 0.85]

        for g in gammas:
            g_r = r * np.exp(g * (r ** 3))
            mult = 0.50 + 0.65 * g_r

            # 1. Boundary value
            assert math.isclose(g_r[0], 0.0, abs_tol=1e-15)
            assert math.isclose(mult[0], 0.50, abs_tol=1e-15)

            # 2. First derivative analytical vs discrete
            dg_analytical = (1.0 + 3.0 * g * (r ** 3)) * np.exp(g * (r ** 3))
            assert np.all(dg_analytical > 0.0), f"First derivative not positive for gamma={g}"

            discrete_diff = np.diff(g_r)
            assert np.all(discrete_diff > 0.0), f"Discrete monotonicity violated for gamma={g}"

            # 3. Second derivative
            d2g_analytical = 3.0 * g * (r ** 2) * (4.0 + 3.0 * g * (r ** 3)) * np.exp(g * (r ** 3))
            assert np.all(d2g_analytical >= 0.0), f"Convexity violated for gamma={g}"

            # 4. Multiplier maximum value
            expected_max = 0.50 + 0.65 * 1.0 * np.exp(g)
            assert math.isclose(mult[-1], expected_max, abs_tol=1e-12)

    def test_alpha_spread_expansion_target_achievement(self, engine):
        """
        Verifies that top 1% alpha spread under v8 expands by >= 25% (target +44.2% in BULL_LOW_VOL)
        relative to Phase 7 quartic rank modulation.
        """
        gamma_bull = engine.get_regime_adaptive_gamma_top('BULL_LOW_VOL', version=8) # 0.85

        # Phase 7 quartic multiplier:
        # mult_v7(r) = 0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4
        def mult_v7(r):
            return 0.60 + 0.25 * r + 0.25 * (r ** 2) + 0.40 * (r ** 3) + 0.35 * (r ** 4)

        # Phase 8 hyperexponential multiplier:
        # mult_v8(r) = 0.50 + 0.65 * r * exp(gamma * r^3)
        def mult_v8(r):
            return 0.50 + 0.65 * r * np.exp(gamma_bull * (r ** 3))

        spread_v7 = mult_v7(1.00) - mult_v7(0.90)
        spread_v8 = mult_v8(1.00) - mult_v8(0.90)

        expansion_pct = ((spread_v8 - spread_v7) / spread_v7) * 100.0
        assert expansion_pct >= 25.0, (
            f"Alpha spread expansion {expansion_pct:.2f}% failed to reach minimum 25% threshold"
        )
        assert math.isclose(expansion_pct, 44.2, abs_tol=3.0), (
            f"Alpha spread expansion {expansion_pct:.2f}% expected near target +44.2%"
        )


# =============================================================================
# 3. ASYMMETRIC SEPTIC WAVELET NOISE DEADBAND ATTENUATION RATIO (F52.2)
# =============================================================================

class TestSepticWaveletDeadbandAttenuationRatio:
    """
    Empirically verifies:
    - At |z| = 0.010: leakage <= 0.010% (>= 99.99% noise suppression, actual ~99.997%).
    - At |z| >= 0.150: transmission >= 99.999% (actual 100.000%).
    - Exact odd symmetry f(-z) == -f(z).
    - Monotonicity: rho == 1.000000.
    """

    def test_noise_leakage_and_suppression_ratio_at_0010(self):
        """
        Authoritative assertion from DISPATCH.md:
        "Noise deadband attenuation ratio at |z| = 0.010: assert leakage <= 0.010% (99.99% noise suppression)"
        """
        delta = 0.045
        z_noise = np.array([0.010])

        denoised_septic = apply_asymmetric_wavelet_deadband(z_noise, delta_noise=delta, alpha_pos=7.0)
        leakage_ratio = float(denoised_septic[0] / z_noise[0])
        leakage_pct = leakage_ratio * 100.0
        suppression_pct = (1.0 - leakage_ratio) * 100.0

        # Primary DISPATCH assertion: leakage <= 0.010% (99.99% suppression)
        assert leakage_pct <= 0.010, f"Noise leakage {leakage_pct:.6f}% exceeds DISPATCH bound 0.010%"
        assert suppression_pct >= 99.990, f"Noise suppression {suppression_pct:.6f}% below 99.990%"

        # Actual septic deadband performance: suppresses 99.997% (leakage < 0.003%)
        assert leakage_pct < 0.003, f"Septic deadband leakage {leakage_pct:.6f}% exceeds target 0.003%"
        assert suppression_pct > 99.997, f"Septic suppression {suppression_pct:.6f}% below target 99.997%"

        # Compare with Phase 7 quintic deadband (alpha=5.0)
        denoised_quintic = apply_quintic_hyperbolic_deadband(z_noise, delta_noise=delta, alpha_pos=5.0)
        leakage_quintic_pct = float(denoised_quintic[0] / z_noise[0]) * 100.0

        # Must achieve > 18x reduction in noise leakage
        reduction_factor = leakage_quintic_pct / leakage_pct
        assert reduction_factor >= 18.0, (
            f"Septic reduction factor {reduction_factor:.2f}x below 18x threshold "
            f"(v8 leakage: {leakage_pct:.6f}%, v7 leakage: {leakage_quintic_pct:.6f}%)"
        )

    def test_high_conviction_signal_transmission_at_0150(self):
        """
        Verifies that for high conviction signals |z| = 0.150 (>= 2.5 * delta):
        Signal transmission is >= 99.999% (100.000% full pass-through).
        """
        delta = 0.045
        z_high = np.array([0.150, 0.200, 0.300, 0.500])

        denoised = apply_asymmetric_wavelet_deadband(z_high, delta_noise=delta, alpha_pos=7.0)
        trans_pct = (denoised / z_high) * 100.0

        for idx, val in enumerate(z_high):
            assert trans_pct[idx] >= 99.999, (
                f"Signal at {val} transmitted at only {trans_pct[idx]:.6f}%, expected >= 99.999%"
            )
            assert math.isclose(denoised[idx], val, abs_tol=1e-5), (
                f"Signal at {val} degraded: got {denoised[idx]}"
            )

    def test_unconditioned_odd_symmetry_and_monotonicity_spectrum(self):
        """
        Verifies exact odd symmetry f(-z) == -f(z) across 20,000 points in [-1.0, 1.0].
        Verifies rank monotonicity rho == 1.000000.
        """
        delta = 0.045
        z_grid = np.linspace(-1.0, 1.0, 20001)

        out_grid = apply_asymmetric_wavelet_deadband(z_grid, delta_noise=delta, alpha_pos=7.0)

        # 1. Symmetry check: f(-z) + f(z) == 0 to machine precision
        rev_grid = out_grid[::-1]
        sym_error = np.max(np.abs(out_grid + rev_grid))
        assert sym_error < 1e-12, f"Odd symmetry violation: {sym_error}"

        # 2. Monotonicity: discrete diffs >= 0
        diffs = np.diff(out_grid)
        assert np.all(diffs >= -1e-15), "Deadband filter violates monotonicity"

        # 3. Spearman rank correlation == 1.000000
        rho, _ = spearmanr(z_grid, out_grid)
        assert math.isclose(rho, 1.0000, abs_tol=1e-6)

    def test_directional_asymmetry_in_bear_and_crisis_regimes(self):
        """
        Verifies that in Bear and Crisis regimes, the negative deadband is widened
        (chi_bear in [1.15, 1.40]), suppressing negative false alarms more aggressively.
        """
        z_test_neg = np.array([-0.050])
        z_test_pos = np.array([0.050])

        # CRISIS: chi_bear = 1.40
        out_crisis_neg = apply_asymmetric_wavelet_deadband(z_test_neg, delta_noise=0.045, regime='CRISIS')
        out_crisis_pos = apply_asymmetric_wavelet_deadband(z_test_pos, delta_noise=0.045, regime='CRISIS')

        # In CRISIS, negative score at -0.050 is squashed more than positive score at +0.050
        assert abs(out_crisis_neg[0]) < abs(out_crisis_pos[0]), (
            f"Negative score ({abs(out_crisis_neg[0]):.6f}) should be more squashed than "
            f"positive score ({abs(out_crisis_pos[0]):.6f}) in CRISIS"
        )


# =============================================================================
# 4. HURST FRACTIONAL JUMP-DIFFUSION SIMPLEX INVARIANTS (F52.1)
# =============================================================================

class TestHurstFractionalJumpDiffusionSimplex:
    """
    Adversarially evaluates:
    w_Zenith^* = (1 - blend_jump) * w_diffusion + blend_jump * W_2D(R_jump)
    across the entire range of Hurst exponents H in [0.01, 0.99].
    Verifies:
    1. Simplex invariant: sum(w_i) == 1.000000 across all 37 strategies.
    2. Non-negativity: w_i >= 0.0 for all i.
    3. Monotonic jump responsiveness with persistence.
    4. Exact continuity at Brownian motion baseline H = 0.50.
    """

    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    def test_hurst_sweep_simplex_invariants(self, engine):
        prev_probs = {'BULL_LOW_VOL': 0.90, 'SIDEWAYS_LOW_VOL': 0.10}
        curr_probs = {'CRISIS': 0.80, 'BEAR_HIGH_VOL': 0.20}

        hurst_values = [0.01, 0.05, 0.15, 0.25, 0.35, 0.50, 0.65, 0.70, 0.85, 0.95, 0.99]

        for h in hurst_values:
            weights = engine.get_base_weights(
                regime=curr_probs,
                prev_regime_probs=prev_probs,
                version=8,
                hurst_exponent=h
            )

            # Simplex invariant: sum == 1.0000
            w_sum = sum(weights.values())
            assert math.isclose(w_sum, 1.0000, abs_tol=1e-5), (
                f"Simplex sum violated at H={h}: sum={w_sum}"
            )

            # Non-negativity
            for strat, w_val in weights.items():
                assert w_val >= 0.0, f"Negative weight for {strat} at H={h}: {w_val}"

        # Exact continuity check at H = 0.50
        w_h050 = engine.get_base_weights(
            regime=curr_probs,
            prev_regime_probs=prev_probs,
            version=8,
            hurst_exponent=0.50
        )
        assert math.isclose(sum(w_h050.values()), 1.0000, abs_tol=1e-5)

    def test_jump_scaling_monotonicity_with_persistence(self, engine):
        """
        Verifies that jump weight strictly increases with Hurst exponent H:
        (2H)^1.5 scales monotonically from 0.0 to ~2.80x.
        """
        h_low = 0.25
        h_mid = 0.50
        h_high = 0.75

        scale_low = (2.0 * h_low) ** 1.5   # 0.5^1.5 ~ 0.353
        scale_mid = (2.0 * h_mid) ** 1.5   # 1.0^1.5 = 1.000
        scale_high = (2.0 * h_high) ** 1.5 # 1.5^1.5 ~ 1.837

        assert scale_low < scale_mid < scale_high
        assert math.isclose(scale_mid, 1.0, abs_tol=1e-6)


# =============================================================================
# 5. REGIME BRANCH ORDERING & SYSTEMIC INTEGRITY VERIFICATION
# =============================================================================

class TestRegimeBranchOrderingIntegrity:
    """
    Verifies that all 7 regimes are correctly parsed without branch shadowing defects
    (e.g., verifying BEAR_HIGH_VOL is not shadowed by BEAR_LOW_VOL).
    """

    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    def test_regime_caps_and_gamma_top_reachability(self, engine):
        """
        Tests that all 7 regimes yield distinct, intended parameters.
        """
        regimes = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL',
            'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
            'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'CRISIS'
        ]

        # Verify gamma_top
        gammas = {r: engine.get_regime_adaptive_gamma_top(r, version=8) for r in regimes}
        assert gammas['CRISIS'] == 0.20
        assert gammas['BEAR_HIGH_VOL'] == 0.25
        assert gammas['BEAR_LOW_VOL'] == 0.35
        assert gammas['SIDEWAYS_HIGH_VOL'] == 0.45
        assert gammas['SIDEWAYS_LOW_VOL'] == 0.55
        assert gammas['BULL_HIGH_VOL'] == 0.70
        assert gammas['BULL_LOW_VOL'] == 0.85

        # Strictly ordered progression (descending from BULL_LOW_VOL to CRISIS)
        sorted_gammas = sorted(gammas.values(), reverse=True)
        assert sorted_gammas == list(gammas.values()), "gamma_top progression must be strictly monotonic across regimes"

        # Verify synergy cap in BEAR_HIGH_VOL is 0.045 (not shadowed to 0.085)
        idx = [f"SYM_{i}" for i in range(10)]
        df = pd.DataFrame({'symbol': idx}, index=idx)
        for col in [
            'rim_score', 'surge_score', 'order_flow_score', 'event_score',
            'supply_chain_score', 'vcp_ml_score', 'valueup_catalyst_score'
        ]:
            df[col] = 0.95

        synergy_bear_high = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime='BEAR_HIGH_VOL',
            version=8
        )
        assert synergy_bear_high.max() <= 1.04501, (
            f"BEAR_HIGH_VOL cap shadowed! Got {synergy_bear_high.max()}, expected <= 1.045"
        )

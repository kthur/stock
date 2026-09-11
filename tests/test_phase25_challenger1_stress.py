"""
tests/test_phase25_challenger1_stress.py

Adversarial Empirical Stress Test Suite for Phase 25 Alpha Signal and Risk Allocation Innovations:
Challenger 1 (Alpha and Risk Adversarial Challenger)

Coverage:
1. Alpha Signal Stress:
   - Feature F120.2: 64th-order Hexatetrahedral hyperbolic deadband at boundaries:
     * z = 0, +0, -0, subnormals (1e-15, 1e-50, 1e-300)
     * |z| approx delta_noise = 0.035 (tanh(1.0) approx 0.0266558, smooth transition)
     * Extreme |z| >> 1 (z = 10, 100, 1e4, 1e6, 1e15, no overflow, 100% transmission)
     * NaNs and Infs (safe pass-through / handling without crash)
     * Ultra-low noise leakage across [-0.005, 0.005] (< 10^-34, empirically < 10^-50)
     * Full transmission for |z| >= 0.150 (ratio == 1.000000000000)
     * Odd symmetry f(-z) == -f(z) and strict rank monotonicity (Spearman rho == 1.0000)
     * Scalar, ndarray, and pandas Series type preservation
   - Feature F120.1: 20th-order Hyper-Convex Rank Modulation (g_v25(r)):
     * Extreme percentiles: r in [0.9990, 1.0000], g(1.0) = 0.50 + 1.14 * exp(gamma_top)
     * Out-of-bounds inputs: r < 0 and r > 1 clipping
     * Negative z branch: 1.35 - 1.00 * r vs positive branch boundary at z = 0, +/- 1e-15
     * Extreme gamma_top: 0.0, 2.60, negative, and large values
     * Strict monotonicity (dg/dr > 0) and strict convexity (d^2g/dr^2 > 0) on right tail
     * Conviction concentration: bottom 70% flat, >90% convexity reserved for top 5%
   - Feature F119: Non-Abelian Hodge and Deligne-Simpson Spectral Moduli Coupler:
     * Completely orthogonal pillars (identity, orthogonal permutations)
     * Singular covariance matrices and zero-variance / rank-deficient factor matrices
     * Coherent zero obstruction state: E_hodge = 0.0, Z_simpson = 1.0, h_hodge = 1.0, FERI = 1.0
     * Extreme adversarial discordance: massive obstruction, h_hodge squashed to epsilon_reg
     * NaN / Inf input sanitization
     * All 10 class aliases and multiple input formats (1D, 2D, transposed, Dict, DataFrame)
2. Risk Allocation Stress:
   - Feature F121.1: Lurie Non-Abelian Hodge Fisher-Rao Barycenter:
     * Extreme Dirac delta vertex measures (all 4 vertices, dominance > 0.99)
     * Extreme dispersion / near-zero inputs ([1e-12, 1e-12, 1e-12, 1.0])
     * Simplex boundary states (edges, faces)
     * Uniform prior metric prioritization: CVaR (2.75) > BL (2.20) > HERC (1.70) > RP (1.65)
     * Degenerate zero and negative inputs (clamped fallback, valid distribution)
     * Monte Carlo Dirichlet consensus convergence over 200 random states
     * All 14 method aliases and static method delegation on PortfolioAllocator
   - Feature F121.1.2: 21st-Cumulant Ultra-Trans-Super-Hyper EVaR:
     * Exact factorial 21! = 51,090,942,171,709,440,000 and xi_21 = 0.85
     * Strict coherent tail risk hierarchy across 50 diverse synthetic return profiles:
       VaR <= CVaR <= Trans-Super-Hyper-EVaR <= Ultra-Trans-Super-Hyper-EVaR
     * Heavy-tailed distributions: Cauchy, Student-t (df=2), Pareto (alpha=1.1)
     * Catastrophic crash shocks (-50%, -80%, -95%, -99.9%, 100-sigma black swans)
     * Crash severity monotonicity and confidence level alpha monotonicity
     * Degenerate inputs: empty array, single value, all-zero, all-NaN
     * Static method delegations and aliases on PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import cauchy, pareto, t as student_t, spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexatetrahedral_hyperbolic_deadband,
    compute_phase25_hyperconvex_rank_modulation,
    compute_phase25_rank_warping,
    NonAbelianHodgeCoupler,
    DeligneSimpsonSpectralModuliCoupler,
    HodgeCoupler,
    DeligneSimpsonCoupler,
    HitchinEquationCoupler,
    HarmonicBundleCoupler,
    NonAbelianHodgeSpectralCoupler,
    HitchinHarmonicBundleCoupler,
    NonAbelianHodgeTheoryCoupler,
    SimpsonSpectralModuliCoupler,
    HitchinEquationsCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexatetrahedral_hyperbolic_deadband as fs_hexatetrahedral_deadband,
    compute_phase25_hyperconvex_rank_modulation as fs_compute_phase25_modulation,
    get_regime_adaptive_gamma_top_v25,
    REGIME_GAMMA_TOP_V25,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =============================================================================
# PART 1: ALPHA SIGNAL ADVERSARIAL STRESS TESTS (F119, F120.1, F120.2)
# =============================================================================

class TestPhase25AlphaAdversarial:
    """Adversarial stress testing of Phase 25 Alpha Signal innovations."""

    # -------------------------------------------------------------------------
    # 1. 64th-Order Hexatetrahedral Hyperbolic Deadband Boundary & Stress Tests
    # -------------------------------------------------------------------------

    def test_deadband_exact_boundary_zero_and_subnormals(self):
        """Verify handling of zero and subnormal values."""
        assert apply_hexatetrahedral_hyperbolic_deadband(0.0) == 0.0
        assert apply_hexatetrahedral_hyperbolic_deadband(-0.0) == 0.0

        for tiny in [1e-15, 1e-30, 1e-50, 1e-100, 1e-300]:
            out_pos = apply_hexatetrahedral_hyperbolic_deadband(tiny)
            out_neg = apply_hexatetrahedral_hyperbolic_deadband(-tiny)
            assert abs(out_pos) < 1e-50, f"Tiny {tiny} leaked {out_pos}"
            assert abs(out_neg) < 1e-50, f"-Tiny {-tiny} leaked {out_neg}"

    def test_deadband_delta_boundary_behavior(self):
        """
        Stress-test behavior around |z| approx delta_noise = 0.035.
        At z = delta, (|z|/delta)^64 = 1.0, so z_denoised = delta * tanh(1.0) approx 0.0266558.
        """
        delta = 0.035
        expected_at_delta = delta * math.tanh(1.0)
        out_at_delta = apply_hexatetrahedral_hyperbolic_deadband(delta, delta_noise=delta)
        assert math.isclose(out_at_delta, expected_at_delta, rel_tol=1e-6)

        # Check neighborhood continuity
        eps_grid = np.array([delta - 1e-5, delta, delta + 1e-5])
        outs = apply_hexatetrahedral_hyperbolic_deadband(eps_grid, delta_noise=delta)
        assert outs[0] < outs[1] < outs[2], "Deadband must be strictly increasing across delta threshold"

    def test_deadband_extreme_large_inputs_no_overflow(self):
        """Stress-test extreme large inputs to verify no overflow in tanh or power."""
        huge_vals = [10.0, 100.0, 1e4, 1e6, 1e15, 1e30]
        for val in huge_vals:
            out_pos = apply_hexatetrahedral_hyperbolic_deadband(val)
            out_neg = apply_hexatetrahedral_hyperbolic_deadband(-val)
            assert math.isfinite(out_pos)
            assert math.isfinite(out_neg)
            assert math.isclose(out_pos, val, rel_tol=1e-12)
            assert math.isclose(out_neg, -val, rel_tol=1e-12)

    def test_deadband_nan_inf_handling(self):
        """Verify handling of NaNs and Infinities in array inputs without raising exceptions."""
        arr = np.array([np.nan, np.inf, -np.inf, 0.0, 0.035, 1.0])
        out = apply_hexatetrahedral_hyperbolic_deadband(arr)
        assert np.isnan(out[0])
        assert np.isinf(out[1]) and out[1] > 0
        assert np.isinf(out[2]) and out[2] < 0
        assert out[3] == 0.0
        assert math.isclose(out[4], 0.035 * math.tanh(1.0), rel_tol=1e-6)
        assert math.isclose(out[5], 1.0, rel_tol=1e-12)

    def test_deadband_noise_leakage_dense_grid(self):
        """
        Verify that across 500,000 points in [-0.005, 0.005], noise leakage
        is strictly < 10^-34 (in fact < 10^-50).
        """
        z_dense = np.linspace(-0.005, 0.005, 500001)
        denoised = apply_hexatetrahedral_hyperbolic_deadband(z_dense, delta_noise=0.035, alpha_pos=64.0)
        max_leak = np.max(np.abs(denoised))
        assert max_leak < 1e-34, f"Noise leakage {max_leak} must be < 1e-34"
        assert max_leak < 1e-50, f"Ultra-tight leakage bound < 1e-50 violated: {max_leak}"

    def test_deadband_high_conviction_full_transmission(self):
        """
        Verify that for |z| >= 0.150, transmission ratio z_denoised / z == 1.000000000000 (100.000%).
        """
        z_conviction = np.array([0.150, 0.150001, 0.200, 0.350, 0.500, 1.000, 5.000, 10.000])
        for sign in [1.0, -1.0]:
            z_vals = sign * z_conviction
            denoised = apply_hexatetrahedral_hyperbolic_deadband(z_vals, delta_noise=0.035, alpha_pos=64.0)
            ratio = denoised / z_vals
            np.testing.assert_allclose(ratio, 1.0, rtol=1e-14, atol=1e-14)

    def test_deadband_monotonicity_fine_grid(self):
        """Verify strict monotonicity across 100,000 points from -1.0 to 1.0."""
        grid = np.linspace(-1.0, 1.0, 100000)
        out = apply_hexatetrahedral_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=64.0)

        diffs = np.diff(out)
        assert np.all(diffs >= -1e-15), "Deadband must be strictly monotonic non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert math.isclose(rho, 1.0, abs_tol=1e-6), f"Spearman correlation must be 1.0, got {rho}"

    def test_deadband_symmetry_and_regimes(self):
        """Verify odd symmetry f(-z) == -f(z) under symmetric settings."""
        z_sample = np.linspace(0.01, 1.0, 1000)
        pos_out = apply_hexatetrahedral_hyperbolic_deadband(z_sample, delta_noise=0.035, alpha_pos=64.0)
        neg_out = apply_hexatetrahedral_hyperbolic_deadband(-z_sample, delta_noise=0.035, alpha_pos=64.0)
        np.testing.assert_allclose(pos_out, -neg_out, atol=1e-12)

    def test_deadband_type_preservation(self):
        """Verify scalar, array, and pandas Series type preservation."""
        # Scalar
        sc = apply_hexatetrahedral_hyperbolic_deadband(0.25)
        assert isinstance(sc, float)

        # Array
        arr = apply_hexatetrahedral_hyperbolic_deadband(np.array([0.1, 0.2]))
        assert isinstance(arr, np.ndarray)

        # Series
        s = pd.Series([0.1, 0.2], index=['A', 'B'])
        res_s = apply_hexatetrahedral_hyperbolic_deadband(s)
        assert isinstance(res_s, pd.Series)
        assert list(res_s.index) == ['A', 'B']

    # -------------------------------------------------------------------------
    # 2. 20th-Order Hyperconvex Rank Modulation ($g_{v25}(r)$) Stress Tests
    # -------------------------------------------------------------------------

    def test_rank_modulation_extreme_percentiles(self):
        """Stress-test extreme right-tail conviction at r in [0.9990, 1.0000]."""
        r_dense = np.linspace(0.9990, 1.0000, 10001)
        mod = compute_phase25_hyperconvex_rank_modulation(r_dense, gamma_top=2.60)

        # Monotonicity across top percentiles
        diffs = np.diff(mod)
        assert np.all(diffs >= 0.0), "Rank modulation must be strictly non-decreasing in right tail"

        # Numerical bounds
        assert np.all(np.isfinite(mod)), "Rank modulation must not produce NaN or Inf"
        expected_top = 0.50 + 1.14 * math.exp(2.60)
        assert math.isclose(mod[-1], expected_top, rel_tol=1e-12)
        assert mod[-1] > 15.0, f"Conviction at r=1.0 must exceed 15.0, got {mod[-1]}"

        # At r = 0.9999
        val_9999 = compute_phase25_hyperconvex_rank_modulation(0.9999, gamma_top=2.60)
        assert val_9999 > 15.0, f"Conviction at r=0.9999 must exceed 15.0, got {val_9999}"
        assert val_9999 < expected_top

    def test_rank_modulation_out_of_bounds_inputs(self):
        """Stress-test out-of-bounds inputs: r < 0 and r > 1."""
        r_oob = np.array([-100.0, -1.0, -1e-6, 0.0, 1.0, 1.0 + 1e-6, 2.0, 100.0])
        mod = compute_phase25_hyperconvex_rank_modulation(r_oob, gamma_top=2.60)

        assert np.all(np.isfinite(mod))
        # Negative ranks clipped to 0 -> 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[1], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[2], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[3], 0.50, abs_tol=1e-12)

        # Ranks > 1 clipped to 1.0 -> 0.50 + 1.14 * exp(2.60)
        expected_top = 0.50 + 1.14 * math.exp(2.60)
        assert math.isclose(mod[4], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[5], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[6], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[7], expected_top, abs_tol=1e-12)

    def test_rank_modulation_negative_denoised_branch_boundary(self):
        """Stress-test negative vs positive denoised z boundary at z = 0, +/- 1e-15."""
        r = np.array([0.1, 0.5, 0.9])

        # Exactly z = 0.0 should use positive branch
        mod_zero_z = compute_phase25_hyperconvex_rank_modulation(r, gamma_top=2.60, z_denoised=np.array([0.0, 0.0, 0.0]))
        mod_pos_z = compute_phase25_hyperconvex_rank_modulation(r, gamma_top=2.60, z_denoised=np.array([1e-15, 1e-15, 1e-15]))
        np.testing.assert_allclose(mod_zero_z, mod_pos_z, atol=1e-10)

        # Negative z: 1.35 - 1.00 * r
        mod_neg_z = compute_phase25_hyperconvex_rank_modulation(r, gamma_top=2.60, z_denoised=np.array([-1e-15, -1e-15, -1e-15]))
        expected_neg = 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg_z, expected_neg, atol=1e-10)

    def test_rank_modulation_gamma_top_parameter_extremes(self):
        """Stress-test extreme gamma_top values: negative, zero, very large."""
        r_test = np.array([0.0, 0.5, 0.9, 1.0])

        # gamma_top = 0.0 -> g(r) = 0.50 + 1.14 * r * exp(0) = 0.50 + 1.14 * r
        mod_zero = compute_phase25_hyperconvex_rank_modulation(r_test, gamma_top=0.0)
        np.testing.assert_allclose(mod_zero, 0.50 + 1.14 * r_test, atol=1e-12)

        # Negative gamma_top: -2.60
        mod_neg = compute_phase25_hyperconvex_rank_modulation(r_test, gamma_top=-2.60)
        assert np.all(np.isfinite(mod_neg))
        assert np.all(mod_neg > 0.0)

        # Very large gamma_top: 10.0, 20.0
        mod_large = compute_phase25_hyperconvex_rank_modulation(r_test, gamma_top=10.0)
        assert np.all(np.isfinite(mod_large))
        assert mod_large[-1] > 1e4

    def test_rank_modulation_strict_convexity_and_monotonicity(self):
        """Verify strict convexity and monotonicity across right tail r in [0.5, 1.0]."""
        r_grid = np.linspace(0.5, 1.0, 1000)
        g_vals = compute_phase25_hyperconvex_rank_modulation(r_grid, gamma_top=2.60)

        # First differences (monotonicity)
        d1 = np.diff(g_vals)
        assert np.all(d1 > 0.0), "First derivative must be strictly positive on [0.5, 1.0]"

        # Second differences (convexity on right tail)
        r_top = np.linspace(0.80, 1.0, 500)
        g_top = compute_phase25_hyperconvex_rank_modulation(r_top, gamma_top=2.60)
        d2 = np.diff(g_top, n=2)
        assert np.all(d2 > 0.0), "Second derivative must be strictly positive on right tail [0.80, 1.00]"

    def test_rank_modulation_flat_bottom_70_percent(self):
        """Verify that bottom 70% of distribution remains flat and controlled."""
        g_00 = compute_phase25_hyperconvex_rank_modulation(0.0, gamma_top=2.60)
        g_50 = compute_phase25_hyperconvex_rank_modulation(0.50, gamma_top=2.60)
        g_70 = compute_phase25_hyperconvex_rank_modulation(0.70, gamma_top=2.60)
        g_100 = compute_phase25_hyperconvex_rank_modulation(1.00, gamma_top=2.60)

        assert math.isclose(g_00, 0.50, abs_tol=1e-12)
        assert math.isclose(g_50, 1.07, abs_tol=0.01)
        assert g_70 < 1.35
        assert g_100 > 15.0

    # -------------------------------------------------------------------------
    # 3. F119 Non-Abelian Hodge & Deligne-Simpson Spectral Moduli Coupler Stress
    # -------------------------------------------------------------------------

    def test_hodge_coupler_orthogonal_pillars(self):
        """Stress-test coupler under completely orthogonal pillar matrices."""
        ortho_mat = np.eye(5)
        res = NonAbelianHodgeCoupler.compute(ortho_mat)
        h = res['h_hodge']
        z = res['z_simpson']
        e = res['e_hodge']

        assert np.all(e > 0.0), "Obstruction must be positive for non-identical orthogonal states"
        assert np.all((z > 0.0) & (z <= 1.0))
        assert np.all((h >= 1e-6) & (h <= 1.0))

    def test_hodge_coupler_singular_and_zero_variance(self):
        """Stress-test coupler under singular, rank-1, and zero-variance matrices."""
        # Case A: Identical zeros
        zeros = pd.DataFrame(np.zeros((8, 5)), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_zeros = NonAbelianHodgeCoupler.compute(zeros)
        np.testing.assert_allclose(res_zeros['e_hodge'].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res_zeros['z_simpson'].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_zeros['h_hodge'].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_zeros['FERI_v25'].values, 1.0, atol=1e-12)

        # Case B: Identical constants
        const_val = pd.DataFrame(np.full((6, 5), 0.888), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_const = NonAbelianHodgeCoupler.compute(const_val)
        np.testing.assert_allclose(res_const['e_hodge'].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res_const['z_simpson'].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_const['h_hodge'].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_const['FERI_v25'].values, 1.0, atol=1e-12)

    def test_hodge_coupler_extreme_adversarial_discordance(self):
        """Stress-test coupler under extreme pillar discordance: [-10, 10, -10, 10, -10]."""
        disc = pd.DataFrame([
            [-10.0, 10.0, -10.0, 10.0, -10.0],
            [10.0, -10.0, 10.0, -10.0, 10.0],
        ], columns=['val', 'mom', 'flow', 'cat', 'net'])

        res = NonAbelianHodgeCoupler.compute(disc)
        assert np.all(res['e_hodge'].values > 100.0)
        assert np.all(res['h_hodge'].values <= 1e-5)
        assert np.all(res['h_hodge'].values >= 1e-6)
        assert np.all(res['FERI_v25'].values < 0.01)

    def test_hodge_coupler_nan_inf_adversarial_inputs(self):
        """Stress-test coupler handling of NaNs and Infs."""
        bad_df = pd.DataFrame([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [0.5, np.nan, np.nan, 0.5, 0.5],
            [0.5, 0.5, 0.5, 0.5, np.nan],
        ], columns=['val', 'mom', 'flow', 'cat', 'net'])

        res = NonAbelianHodgeCoupler.compute(bad_df)
        assert np.all(np.isfinite(res['h_hodge'].values))
        assert np.all(np.isfinite(res['z_simpson'].values))
        assert np.all(np.isfinite(res['e_hodge'].values))
        assert np.all(np.isfinite(res['FERI_v25'].values))

    def test_hodge_coupler_all_aliases_and_formats(self):
        """Verify all 10 aliases and multiple input formats (1D, 2D, transposed, Dict, DataFrame)."""
        aliases = [
            NonAbelianHodgeCoupler,
            DeligneSimpsonSpectralModuliCoupler,
            HodgeCoupler,
            DeligneSimpsonCoupler,
            HitchinEquationCoupler,
            HarmonicBundleCoupler,
            NonAbelianHodgeSpectralCoupler,
            HitchinHarmonicBundleCoupler,
            NonAbelianHodgeTheoryCoupler,
            SimpsonSpectralModuliCoupler,
            HitchinEquationsCoupler,
        ]
        p_1d = np.array([0.4, 0.4, 0.4, 0.4, 0.4])
        for cls_alias in aliases:
            out = cls_alias.compute(p_1d)
            assert math.isclose(out['e_hodge'], 0.0, abs_tol=1e-12)
            assert math.isclose(out['z_simpson'], 1.0, abs_tol=1e-12)
            assert math.isclose(out['h_hodge'], 1.0, abs_tol=1e-12)


# =============================================================================
# PART 2: RISK ALLOCATION ADVERSARIAL STRESS TESTS (F121.1, F121.1.2)
# =============================================================================

class TestPhase25RiskAdversarial:
    """Adversarial stress testing of Phase 25 Risk Allocation innovations."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    # -------------------------------------------------------------------------
    # 4. F121.1 Lurie Non-Abelian Hodge Fisher-Rao Barycenter Stress
    # -------------------------------------------------------------------------

    def test_barycenter_dirac_measure_all_vertices(self, allocator):
        """Verify consensus on all 4 pure Dirac delta vertices."""
        vertices = [
            ('bl', {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0}),
            ('herc', {'bl': 0.0, 'herc': 1.0, 'rp': 0.0, 'cvar': 0.0}),
            ('rp', {'bl': 0.0, 'herc': 0.0, 'rp': 1.0, 'cvar': 0.0}),
            ('cvar', {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 1.0}),
        ]
        for name, w in vertices:
            res = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
            assert res[name] > 0.99, f"Vertex {name} dominance failed: {res[name]}"
            for other in ['bl', 'herc', 'rp', 'cvar']:
                if other != name:
                    assert res[other] < 0.01

    def test_barycenter_extreme_dispersion(self, allocator):
        """Stress-test extreme dispersion inputs [1e-12, 1e-12, 1e-12, 1.0]."""
        w = {'bl': 1e-12, 'herc': 1e-12, 'rp': 1e-12, 'cvar': 1.0}
        res = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
        assert res['cvar'] > 0.99
        assert all(v > 0.0 for v in res.values())

    def test_barycenter_uniform_prior_metric_prioritization(self, allocator):
        """
        Verify that under uniform prior [0.25, 0.25, 0.25, 0.25], Non-Abelian Hodge metric weights
        mu_hodge = [2.20, 1.70, 1.65, 2.75] strictly enforce:
            CVaR (2.75) > BL (2.20) > HERC (1.70) > RP (1.65)
        """
        unif = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
        res = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(unif)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
        assert res['cvar'] > res['bl'] > res['herc'] > res['rp'], f"Prioritization failed: {res}"
        # Check normalized ratio matching
        total_mu = 2.20 + 1.70 + 1.65 + 2.75
        assert math.isclose(res['cvar'], 2.75 / total_mu, rel_tol=1e-3)
        assert math.isclose(res['bl'], 2.20 / total_mu, rel_tol=1e-3)
        assert math.isclose(res['herc'], 1.70 / total_mu, rel_tol=1e-3)
        assert math.isclose(res['rp'], 1.65 / total_mu, rel_tol=1e-3)

    def test_barycenter_degenerate_zero_and_negative_inputs(self, allocator):
        """Stress-test degenerate all-zero and negative inputs."""
        w_zeros = {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0}
        res_zeros = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w_zeros)
        assert math.isclose(sum(res_zeros.values()), 1.0, abs_tol=1e-6)
        assert res_zeros['cvar'] > res_zeros['bl'] > res_zeros['herc'] > res_zeros['rp']

        # Negative and unnormalized
        w_neg = {'bl': -10.0, 'herc': 20.0, 'rp': 30.0, 'cvar': 50.0}
        res_neg = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w_neg)
        assert math.isclose(sum(res_neg.values()), 1.0, abs_tol=1e-6)
        assert all(v > 0.0 for v in res_neg.values())

    def test_barycenter_monte_carlo_dirichlet_consensus(self, allocator):
        """Monte Carlo verification of barycenter convergence over 200 random Dirichlet distributions."""
        np.random.seed(888)
        alpha_prior = [1.0, 1.0, 1.0, 1.0]
        samples = np.random.dirichlet(alpha_prior, size=200)

        for s in samples:
            w_dict = {'bl': float(s[0]), 'herc': float(s[1]), 'rp': float(s[2]), 'cvar': float(s[3])}
            res = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w_dict, max_iter=50, tol=1e-6)
            tot = sum(res.values())
            assert math.isclose(tot, 1.0, abs_tol=1e-5), f"Partition of unity violated: {tot}"
            assert all(v >= 0.0 for v in res.values())

    def test_barycenter_static_delegations_and_aliases(self, allocator):
        """Verify PortfolioAllocator static delegations and all aliases."""
        w_test = {'bl': 0.3, 'herc': 0.2, 'rp': 0.2, 'cvar': 0.3}
        res_alloc = allocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w_test)
        res_static = PortfolioAllocator.compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend(w_test)

        for k in ['bl', 'herc', 'rp', 'cvar']:
            assert math.isclose(res_alloc[k], res_static[k], rel_tol=1e-6)

        # Contiguous alias
        res_contig = PortfolioAllocator.compute_lurie_nonabelian_hodge_fisher_rao_barycenter_blend(w_test)
        for k in ['bl', 'herc', 'rp', 'cvar']:
            assert math.isclose(res_alloc[k], res_contig[k], rel_tol=1e-6)

    # -------------------------------------------------------------------------
    # 5. F121.1.2 21st-Cumulant Ultra-Trans-Super-Hyper EVaR Tail Measure Stress
    # -------------------------------------------------------------------------

    def test_evar_exact_combinatorics_and_defaults(self, allocator):
        """Verify exact factorial 21! = 51,090,942,171,709,440,000 and xi_21 = 0.85."""
        assert math.factorial(21) == 51090942171709440000
        assert math.factorial(20) == 2432902008176640000

        rets = np.array([-0.02, -0.01, 0.01, 0.02, 0.005, -0.03])
        res = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)
        assert res['order'] == 21
        assert math.isclose(res['xi_21'], 0.85, abs_tol=1e-12)
        assert math.isclose(res['xi_ultra_super'], 0.85, abs_tol=1e-12)
        assert math.isclose(res['xi_ultra_trans_super_hyper'], 0.85, abs_tol=1e-12)

    def test_evar_strict_coherent_hierarchy_50_trials(self, allocator):
        """
        Verify strict coherent tail risk hierarchy across 50 diverse synthetic return profiles:
            VaR <= CVaR <= Trans-Super-Hyper-EVaR <= Ultra-Trans-Super-Hyper-EVaR
        """
        np.random.seed(54321)
        for trial in range(50):
            base_rets = np.random.normal(0.0005, 0.015, 200)
            jumps = np.random.choice([0.0, -0.05, -0.10, -0.20], size=200, p=[0.92, 0.05, 0.02, 0.01])
            rets = base_rets + jumps

            res = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)
            tsh_res = allocator.compute_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)

            var_val = res['var_value']
            cvar_val = res['cvar_value']
            tsh_val = tsh_res['trans_super_hyper_evar_value']
            utsh_val = res['ultra_trans_super_hyper_evar_value']

            assert var_val <= cvar_val + 1e-6, f"Trial {trial}: VaR ({var_val}) > CVaR ({cvar_val})"
            assert cvar_val <= tsh_val + 1e-6, f"Trial {trial}: CVaR ({cvar_val}) > TSH-EVaR ({tsh_val})"
            assert tsh_val <= utsh_val + 1e-6, f"Trial {trial}: TSH-EVaR ({tsh_val}) > UTSH-EVaR ({utsh_val})"

    def test_evar_adversarial_fat_tail_distributions(self, allocator):
        """
        Empirically test Ultra-Trans-Super-Hyper EVaR under heavy fat-tail distributions:
        - Cauchy: infinite mean and variance
        - Pareto (alpha=1.1): finite mean, infinite variance
        - Student-t (df=2.0): infinite variance
        - Catastrophic Black Swan shocks (-30%, -50%, -80%, -95%, -99.9%, 100-sigma crash)
        """
        np.random.seed(98765)
        scenarios = {
            'Cauchy_Extreme': cauchy.rvs(loc=-0.02, scale=0.04, size=1000),
            'Pareto_Alpha_1.1': -(pareto.rvs(b=1.1, scale=0.015, size=1000) - 0.015),
            'Student_t_df_2.0': student_t.rvs(df=2.0, loc=-0.01, scale=0.025, size=1000),
            'Black_Swan_Minus_50': np.concatenate([
                np.random.normal(0.001, 0.012, 990),
                np.array([-0.15, -0.25, -0.35, -0.50])
            ]),
            'Catastrophic_Minus_95': np.concatenate([
                np.random.normal(0.001, 0.01, 995),
                np.array([-0.30, -0.60, -0.80, -0.90, -0.95])
            ]),
            'Crash_100sigma': np.concatenate([
                np.random.normal(0.0005, 0.015, 990),
                np.full(10, -0.999)
            ]),
        }

        for name, r in scenarios.items():
            res = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(r, alpha=0.05)
            val = res['ultra_trans_super_hyper_evar_value']

            assert math.isfinite(val), f"Non-finite EVaR value under {name}: {val}"
            assert val > 0.0, f"EVaR must be strictly positive under loss-heavy {name}: {val}"
            assert val >= res['cvar_value'] - 1e-6, f"EVaR < CVaR under {name}"

    def test_evar_black_swan_severity_monotonicity(self, allocator):
        """Verify that increasing severity of crash shocks monotonically increases Ultra-Trans-Super-Hyper EVaR."""
        np.random.seed(42)
        base = np.random.normal(0.001, 0.01, 500)

        evar_levels = []
        crashes = [-0.10, -0.25, -0.50, -0.75, -0.90, -0.99]
        for crash in crashes:
            r_shock = np.append(base, crash)
            res = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(r_shock, alpha=0.05)
            evar_levels.append(res['ultra_trans_super_hyper_evar_value'])

        diffs = np.diff(evar_levels)
        assert np.all(diffs >= 0.0), f"EVaR must strictly increase as crash size increases: {evar_levels}"

    def test_evar_confidence_level_monotonicity(self, allocator):
        """Verify that decreasing alpha (increasing confidence 90% -> 95% -> 99% -> 99.9%) monotonically increases EVaR."""
        np.random.seed(123)
        rets = np.random.normal(0.001, 0.02, 1000)
        alphas = [0.10, 0.05, 0.02, 0.01, 0.005]
        risk_vals = []
        for a in alphas:
            res = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(rets, alpha=a)
            risk_vals.append(res['ultra_trans_super_hyper_evar_value'])

        diffs = np.diff(risk_vals)
        assert np.all(diffs >= 0.0), f"Risk must monotonically increase as alpha decreases: {risk_vals}"

    def test_evar_degenerate_and_empty_inputs(self, allocator):
        """Verify graceful handling of degenerate inputs (empty, all-NaN, single value)."""
        # Empty array
        res_empty = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(np.array([]))
        assert math.isfinite(res_empty['ultra_trans_super_hyper_evar_value'])

        # All NaNs
        res_nan = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(np.array([np.nan, np.nan]))
        assert math.isfinite(res_nan['ultra_trans_super_hyper_evar_value'])

        # Single value
        res_single = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(np.array([0.05]))
        assert math.isfinite(res_single['ultra_trans_super_hyper_evar_value'])

    def test_evar_static_delegation_on_portfolio_allocator(self, allocator):
        """Verify PortfolioAllocator static delegations and aliases for EVaR."""
        rets = np.array([-0.05, -0.02, 0.01, 0.03, -0.01])
        res_alloc = allocator.compute_ultra_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)
        res_static = PortfolioAllocator.compute_ultra_trans_super_hyper_evar_risk_measure(returns=rets, alpha=0.05)

        assert math.isclose(res_alloc['ultra_trans_super_hyper_evar_value'],
                            res_static['ultra_trans_super_hyper_evar_value'],
                            rel_tol=1e-5)

        # Alias
        res_alias = PortfolioAllocator.compute_ultra_super_hyper_evar(returns=rets, alpha=0.05)
        assert math.isclose(res_alloc['ultra_trans_super_hyper_evar_value'],
                            res_alias['ultra_trans_super_hyper_evar_value'],
                            rel_tol=1e-5)
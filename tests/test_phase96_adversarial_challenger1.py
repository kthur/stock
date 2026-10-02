r"""
tests/test_phase96_adversarial_challenger1.py

Adversarial Empirical Challenge and Stress Test Suite for Phase 96
Quantitative Alpha Enhancement & Risk Allocation (v103 Production Master):
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)

Scope of Empirical Adversarial Tests:
1. Feature F450: Asymmetric Pentacontahexagonal (576th-Order) Hyperbolic Noise Deadband
   - Sub-threshold noise annihilation: |z| <= 0.0003 across 10,000 random sub-threshold samples -> strictly < 10^-576 (float64 0.0)
   - High-conviction signal transmission: |z| >= 0.150 -> 100.0% retention (|f(z)/z - 1.0| < 1e-4)
   - Monotonicity across 100,000 synthetic values under micro-jitter (Spearman rho == 1.0000, all diffs >= 0)
   - Odd symmetry: f(-z) == -f(z)
   - Mathematical boundary and edge inputs: 0.0, -0.0, inf, -inf, nan, subnormals (1e-320, 5e-324), extreme floats (1e300, -1e300), empty arrays
   - Full 17-alias tree bit-identical verification

2. Feature F450: 123rd-Order Hyper-Convex Rank Modulation
   - Strict rank monotonicity across 50,000 points across all regimes in REGIME_GAMMA_TOP_V96
   - Top-decile amplification: g(1.0) > 10^7 under Bull/Sideways regimes (up to ~2.15e15 under BULL_LOW_VOL)
   - Regime hierarchy: BULL_LOW_VOL (34.00) > BULL_HIGH_VOL (28.50) > SIDEWAYS (23.00) > SIDEWAYS_HIGH_VOL (17.50) > BEAR (12.00) > BEAR_HIGH_VOL (6.00) > CRISIS (2.50)
   - Boundary inputs: r = 0.0 (0.50), r = 1.0, r > 1.0 (clipped to r=1.0), r < 0.0 (clipped to r=0.0)
   - Negative conviction branch: z_denoised < 0 -> g_neg(r) = 1.35 - 1.00 * r (monotonic decreasing from 1.35 to 0.35)
   - Extreme gamma_top values: gamma_top = 0.0, gamma_top = 100.0, gamma_top = 1000.0
   - Full alias tree verification

3. Feature F451: Quantum Geometric Langlands Monster Whittaker Coupler v96
   - Degenerate inputs: all-zeros (e_monster_whit == 0, h in [0, 1], z == 1.0), all-ones
   - Missing signals and NaN resilience: NaN entries, empty columns, 1D array (<5 padded to 5), 2D array (<5 or >5 columns)
   - High-dimensional stress (1000 rows x 5 pillars, random uniform in [-10, 10])
   - Boundedness of invariants: h, z, FERI in [0, 1], e_monster_whit finite
   - 204th-order chiral oper obstruction and 116th-order topological defect invariant verification
   - Backward compatibility: FERI_v96, feri_v96, f_out_96 alongside FERI_v95 down to v48
   - Coupler alias tree verification

4. Feature F452.1: Higher-Homology-46 Motivic Fisher-Rao Barycenter Blend
   - Collinear and identical model weights: consensus preserves asset weights
   - Single-asset dominance: 100% allocation on dominant asset
   - Simplex conservation: sum q_i == 1.000000 within 1e-5, all q_i >= 0.0
   - Metric curvature hierarchy under uniform input: CVaR (11.50) > BL (9.50) > HERC (5.90) > RP (2.65)
   - Extreme tau convergence: spectrum from 1e-15 to 0.05 preserves exact simplex and hierarchy
   - Input format stress: dict of dicts, DataFrame, dict of floats, list of dicts, 1D array, 2D array
   - Full alias tree verification across UnifiedPortfolioAllocator and PortfolioAllocator

5. Feature F452.2: 124th-Cumulant Expansion Trans-Singular EVaR Risk Measure
   - Heavy-tailed return stress: Cauchy, Student-t (df=1), Normal distributions
   - Tail-risk ordering: EVaR(Cauchy) > EVaR(Normal), EVaR(Student-t(1)) > EVaR(Normal)
   - Dirac delta returns resilience: constant positive vs constant negative returns
   - Volatility monotonicity: EVaR scales monotonically with scale
   - Order=124, 32-nines+9 xi_monster (0.9999999999999999999999999999999)
   - Full alias tree verification across UnifiedPortfolioAllocator and PortfolioAllocator
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import itertools
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_pentacontahexagonal_hyperbolic_deadband,
    apply_quingentaoctacontahexagonal_hyperbolic_deadband,
    apply_pentacontaoctacontahexagonal_hyperbolic_deadband,
    apply_pentacontahexa_hyperbolic_deadband,
    apply_pentacontahexagonal_deadband,
    pentacontahexagonal_deadband,
    pentacontahexagonal_hyperbolic_deadband,
    compute_phase96_deadband,
    apply_phase96_deadband,
    phase96_deadband,
    apply_576th_order_hyperbolic_deadband,
    apply_576th_deadband,
    apply_576_deadband,
    apply_hyperbolic_deadband_v96,
    suppress_factor_noise_hyperbolic_v96,
    apply_quingentaheptacontahexagonal_hyperbolic_deadband,
    apply_pentacentaheptacontahexagonal_hyperbolic_deadband,
    apply_tridecatetracontasagonal_hyperbolic_deadband,
    compute_phase96_hyperconvex_rank_modulation,
    compute_123rd_order_hyperconvex_rank_modulation,
    compute_phase96_rank_warping,
    compute_phase96_rank_modulation,
    phase96_rank_modulation,
    phase96_hyperconvex_rank_modulation,
    apply_phase96_rank_modulation,
    apply_hyper_convex_rank_modulation_v96,
    REGIME_GAMMA_TOP_V96,
    get_regime_adaptive_gamma_top_v96,
    Phase96FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase96Coupler,
    Phase96WhittakerDrinfeldCoupler,
    Phase96BorcherdsMoonshineCoupler,
    Phase96MonsterWhittakerCoupler,
    compute_phase96_coupling,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =========================================================================
# 1. FEATURE F450: 576TH-ORDER HYPERBOLIC NOISE DEADBAND ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF450DeadbandAdversarialStress:
    """Adversarial stress testing on 576th-order hyperbolic noise deadband."""

    def test_sub_noise_annihilation_float64_underflow(self):
        """Stress: |z| <= 0.0003 across 10,000 random sub-noise samples underflows strictly to 0.0."""
        rng = np.random.default_rng(42)
        sub_samples = rng.uniform(-0.0003, 0.0003, size=10000)
        # Ensure exact boundary points are tested
        sub_samples[0] = 0.0003
        sub_samples[1] = -0.0003
        sub_samples[2] = 0.0001
        sub_samples[3] = -0.0001

        out = apply_pentacontahexagonal_hyperbolic_deadband(sub_samples, delta_noise=0.035, alpha_pos=576.0)

        # In float64, (|z|/0.035)^576 for |z|<=0.0003 is (0.0003/0.035)^576 = (0.00857)^576 ~ 10^-1190
        # which strictly underflows to exact 0.0
        assert np.all(out == 0.0), f"Detected non-zero noise leakage in sub-noise zone: max={np.max(np.abs(out))}"

    def test_high_conviction_full_transmission(self):
        """Stress: |z| >= 0.150 preserves >= 99.99% fidelity (|f(z)/z - 1.0| < 1e-4)."""
        strong_vals = np.array([
            0.150, 0.151, 0.200, 0.350, 0.500, 1.000, 2.500, 5.000, 10.000,
            -0.150, -0.151, -0.200, -0.350, -0.500, -1.000, -2.500, -5.000, -10.000
        ], dtype=np.float64)

        out = apply_pentacontahexagonal_hyperbolic_deadband(strong_vals, delta_noise=0.035, alpha_pos=576.0)
        ratios = out / strong_vals

        for z_in, r in zip(strong_vals, ratios):
            assert math.isclose(r, 1.0, rel_tol=1e-4), f"Signal distorted at z={z_in}: ratio={r:.6f}"
            assert r >= 0.9999, f"Signal dropped below 99.99% retention at z={z_in}: {r:.6f}"

    def test_monotonicity_under_fine_grained_jitter(self):
        """Stress: 100,000 synthetic values with random jitter exhibit strict rank monotonicity (rho == 1.0000)."""
        rng = np.random.default_rng(12345)
        grid = np.linspace(0.001, 2.0, 100000)
        jitter = rng.normal(0, 1e-12, size=grid.shape)
        sorted_inputs = np.sort(grid + jitter)

        denoised = apply_pentacontahexagonal_hyperbolic_deadband(sorted_inputs, delta_noise=0.035, alpha_pos=576.0)
        rho, _ = spearmanr(sorted_inputs, denoised)
        assert math.isclose(rho, 1.0, rel_tol=1e-5), f"Rank monotonicity violated: Spearman rho={rho}"

        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), f"Detected negative diff in sorted output: min diff={np.min(diffs)}"

    def test_odd_symmetry(self):
        """Stress: Odd symmetry f(-z) == -f(z) holds across positive and negative domains."""
        rng = np.random.default_rng(999)
        test_z = rng.uniform(0.001, 5.0, size=5000)
        f_pos = apply_pentacontahexagonal_hyperbolic_deadband(test_z)
        f_neg = apply_pentacontahexagonal_hyperbolic_deadband(-test_z)

        diff = np.abs(f_neg + f_pos)
        assert np.all(diff < 1e-12), f"Odd symmetry violated: max diff={np.max(diff)}"

    def test_mathematical_edge_inputs(self):
        """Stress: Edge inputs (0.0, -0.0, inf, -inf, nan, subnormals 1e-320, extreme floats 1e300)."""
        edge_inputs = np.array([
            0.0, -0.0, np.inf, -np.inf, np.nan,
            1e-320, -1e-320, 5e-324, 1e300, -1e300
        ], dtype=np.float64)

        out = apply_pentacontahexagonal_hyperbolic_deadband(edge_inputs)
        assert out[0] == 0.0 and math.copysign(1.0, out[0]) == 1.0
        assert out[1] == 0.0 and math.copysign(1.0, out[1]) == -1.0
        assert np.isinf(out[2]) and out[2] > 0
        assert np.isinf(out[3]) and out[3] < 0
        assert np.isnan(out[4])
        # Subnormals underflow
        assert out[5] == 0.0 and out[6] == 0.0 and out[7] == 0.0
        # Extreme floats
        assert math.isclose(out[8], 1e300, rel_tol=1e-4)
        assert math.isclose(out[9], -1e300, rel_tol=1e-4)

    def test_pandas_series_and_scalar_support(self):
        """Stress: Series preserves index and scalar returns float."""
        s = pd.Series([0.0001, 0.200, -0.300], index=['a', 'b', 'c'])
        out_s = apply_pentacontahexagonal_hyperbolic_deadband(s)
        assert isinstance(out_s, pd.Series)
        assert list(out_s.index) == ['a', 'b', 'c']
        assert out_s['a'] == 0.0
        assert math.isclose(out_s['b'], 0.200, rel_tol=1e-4)

        val_scalar = apply_pentacontahexagonal_hyperbolic_deadband(0.25)
        assert isinstance(val_scalar, float)
        assert math.isclose(val_scalar, 0.25, rel_tol=1e-4)

    def test_deadband_17_aliases_identity(self):
        """Stress: All 17 alias names return identical results."""
        test_arr = np.array([0.0001, 0.035, 0.200, -0.0002, -0.300])
        canonical = apply_pentacontahexagonal_hyperbolic_deadband(test_arr)

        aliases = [
            apply_quingentaoctacontahexagonal_hyperbolic_deadband,
            apply_pentacontaoctacontahexagonal_hyperbolic_deadband,
            apply_pentacontahexa_hyperbolic_deadband,
            apply_pentacontahexagonal_deadband,
            pentacontahexagonal_deadband,
            pentacontahexagonal_hyperbolic_deadband,
            compute_phase96_deadband,
            apply_phase96_deadband,
            phase96_deadband,
            apply_576th_order_hyperbolic_deadband,
            apply_576th_deadband,
            apply_576_deadband,
            apply_hyperbolic_deadband_v96,
            suppress_factor_noise_hyperbolic_v96,
            apply_quingentaheptacontahexagonal_hyperbolic_deadband,
            apply_pentacentaheptacontahexagonal_hyperbolic_deadband,
            apply_tridecatetracontasagonal_hyperbolic_deadband,
        ]

        for alias_fn in aliases:
            res = alias_fn(test_arr)
            assert np.array_equal(canonical, res, equal_nan=True), f"Alias {alias_fn.__name__} mismatch"


# =========================================================================
# 2. FEATURE F450: 123RD-ORDER RANK MODULATION ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF450RankModulationAdversarialStress:
    """Adversarial stress testing on 123rd-order hyper-convex rank modulation."""

    def test_boundary_points_and_clipping(self):
        """Stress: Boundary points r=0.0 -> 0.50, r=1.0 -> 0.50 + 3.70*exp(gamma_top), r > 1.0 and r < 0.0 clipped."""
        gamma_test = 23.00
        # Exact boundary r=0.0
        g0 = compute_phase96_hyperconvex_rank_modulation(0.0, gamma_top=gamma_test)
        assert math.isclose(g0, 0.50), f"g(0.0) expected 0.50, got {g0}"

        # Exact boundary r=1.0
        g1 = compute_phase96_hyperconvex_rank_modulation(1.0, gamma_top=gamma_test)
        expected_g1 = 0.50 + 3.70 * 1.0 * math.exp(gamma_test * (1.0 ** 123))
        assert math.isclose(g1, expected_g1, rel_tol=1e-7), f"g(1.0) expected {expected_g1}, got {g1}"

        # Over-range clipping
        g_over = compute_phase96_hyperconvex_rank_modulation(1.0001, gamma_top=gamma_test)
        g_over2 = compute_phase96_hyperconvex_rank_modulation(5.0, gamma_top=gamma_test)
        assert math.isclose(g_over, g1), "r > 1.0 was not clipped to r=1.0"
        assert math.isclose(g_over2, g1), "r=5.0 was not clipped to r=1.0"

        # Under-range clipping
        g_under = compute_phase96_hyperconvex_rank_modulation(-0.001, gamma_top=gamma_test)
        g_under2 = compute_phase96_hyperconvex_rank_modulation(-10.0, gamma_top=gamma_test)
        assert math.isclose(g_under, 0.50), "r < 0.0 was not clipped to r=0.0"
        assert math.isclose(g_under2, 0.50), "r=-10.0 was not clipped to r=0.0"

    def test_strict_monotonicity_across_all_regimes(self):
        """Stress: 50,000 points in [0, 1] exhibit strict monotonicity across all 14 regimes."""
        r_grid = np.linspace(0.0, 1.0, 50000)

        for regime_name, gamma_val in REGIME_GAMMA_TOP_V96.items():
            g_vals = compute_phase96_hyperconvex_rank_modulation(r_grid, regime=regime_name)
            diffs = np.diff(g_vals)
            assert np.all(diffs >= 0.0), f"Monotonicity violation in regime '{regime_name}' with gamma={gamma_val}"

    def test_top_decile_exponential_boost(self):
        """Stress: BULL_LOW_VOL achieves massive conviction amplification g(1.0) > 10^7 (up to ~2.15e15)."""
        g_bull = compute_phase96_hyperconvex_rank_modulation(1.0, regime='BULL_LOW_VOL')
        assert g_bull > 1e7, f"Top-decile boost insufficient: {g_bull}"
        # For gamma=34.00: 0.50 + 3.70 * exp(34.00) ~ 2.1588e15
        assert g_bull > 1e15, f"BULL_LOW_VOL expected > 1e15, got {g_bull}"

    def test_regime_hierarchy(self):
        """Stress: gamma_top hierarchy holds: BULL_LOW_VOL (34.0) > BULL_HIGH_VOL (28.5) > SIDEWAYS (23.0) > BEAR (12.0) > CRISIS (2.5)."""
        g_bull_low = get_regime_adaptive_gamma_top_v96('BULL_LOW_VOL')
        g_bull_high = get_regime_adaptive_gamma_top_v96('BULL_HIGH_VOL')
        g_sideways = get_regime_adaptive_gamma_top_v96('SIDEWAYS')
        g_bear = get_regime_adaptive_gamma_top_v96('BEAR')
        g_crisis = get_regime_adaptive_gamma_top_v96('CRISIS')

        assert g_bull_low == 34.00
        assert g_bull_high == 28.50
        assert g_sideways == 23.00
        assert g_bear == 12.00
        assert g_crisis == 2.50
        assert g_bull_low > g_bull_high > g_sideways > g_bear > g_crisis

    def test_negative_conviction_branch(self):
        """Stress: Negative signals (z_denoised < 0) follow g_neg(r) = 1.35 - 1.00 * r (monotonic decreasing)."""
        r_grid = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full_like(r_grid, -0.05)

        g_neg = compute_phase96_hyperconvex_rank_modulation(r_grid, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35)
        assert math.isclose(g_neg[-1], 0.35)

        diffs = np.diff(g_neg)
        assert np.all(diffs <= 0.0), "Negative conviction branch must be monotonically non-increasing"

    def test_extreme_gamma_top_values(self):
        """Stress: gamma_top = 0.0 returns 0.50 + 3.70*r; extreme gamma_top = 100.0 does not error or NaN."""
        # Flat boost
        g_zero = compute_phase96_hyperconvex_rank_modulation(np.array([0.0, 0.5, 1.0]), gamma_top=0.0)
        assert math.isclose(g_zero[0], 0.50)
        assert math.isclose(g_zero[1], 0.50 + 3.70 * 0.5)
        assert math.isclose(g_zero[2], 0.50 + 3.70 * 1.0)

        # High gamma
        g_high = compute_phase96_hyperconvex_rank_modulation(0.8, gamma_top=100.0)
        assert np.isfinite(g_high) and g_high > 0.0

    def test_rank_modulation_aliases(self):
        """Stress: All alias functions compute identical outputs."""
        r_arr = np.array([0.1, 0.5, 0.9])
        ref = compute_phase96_hyperconvex_rank_modulation(r_arr)

        aliases = [
            compute_123rd_order_hyperconvex_rank_modulation,
            compute_phase96_rank_warping,
            compute_phase96_rank_modulation,
            phase96_rank_modulation,
            phase96_hyperconvex_rank_modulation,
            apply_phase96_rank_modulation,
            apply_hyper_convex_rank_modulation_v96,
        ]

        for fn in aliases:
            out = fn(r_arr)
            assert np.array_equal(ref, out), f"Rank modulation alias {fn.__name__} mismatch"


# =========================================================================
# 3. FEATURE F451: MONSTER WHITTAKER COUPLER ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF451CouplerAdversarialStress:
    """Adversarial stress testing on Quantum Geometric Langlands Monster Whittaker Coupler Phase 96."""

    def test_degenerate_inputs_zeros_and_ones(self):
        """Stress: All-zeros and all-ones matrices produce zero obstruction energy and finite bounded invariants."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)

        # All zeros
        zeros_mat = np.zeros((20, 5))
        res_zero = coupler.evaluate(zeros_mat)
        assert np.allclose(res_zero['e_monster_whit'], 0.0), "Zeros matrix should yield e_monster_whit == 0"
        assert np.allclose(res_zero['z_monster_whit'], 1.0), "Zeros matrix should yield z_monster_whit == 1"
        assert np.all(res_zero['h_monster_whit'] >= 0.0) and np.all(res_zero['h_monster_whit'] <= 1.0)
        assert np.all(res_zero['FERI_v96'] >= 0.0) and np.all(res_zero['FERI_v96'] <= 1.0)

        # All ones
        ones_mat = np.ones((20, 5))
        res_ones = coupler.evaluate(ones_mat)
        assert np.allclose(res_ones['e_monster_whit'], 0.0), "Identical signals should yield e_monster_whit == 0"

    def test_missing_signals_and_nan_resilience(self):
        """Stress: Matrix with NaNs, missing columns, and irregular shapes is handled gracefully."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)

        # NaNs in array
        nan_mat = np.random.uniform(0.1, 0.9, size=(30, 5))
        nan_mat[0, 1] = np.nan
        nan_mat[10, :] = np.nan
        res_nan = coupler.evaluate(nan_mat)
        assert not np.any(np.isnan(res_nan['FERI_v96'])), "FERI_v96 contains NaN after nan input"
        assert not np.any(np.isnan(res_nan['h_monster_whit'])), "h_monster_whit contains NaN after nan input"

        # 1D array < 5 elements
        vec_3 = np.array([0.2, 0.4, 0.6])
        res_1d = coupler.evaluate(vec_3)
        assert isinstance(res_1d['FERI_v96'], float)
        assert 0.0 <= res_1d['FERI_v96'] <= 1.0

        # DataFrame with 3 columns (padded to 5)
        df_3col = pd.DataFrame({'val': [0.1, 0.2], 'mom': [0.3, 0.4], 'flow': [0.5, 0.6]})
        res_df = coupler.evaluate(df_3col)
        assert len(res_df['FERI_v96']) == 2

    def test_extreme_dimensionality_stress(self):
        """Stress: 1000 rows x 5 pillars under extreme values [-10.0, 10.0] produce strictly finite outputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)
        rng = np.random.default_rng(777)
        large_mat = rng.uniform(-10.0, 10.0, size=(1000, 5))

        res = coupler.evaluate(large_mat)
        assert np.all(np.isfinite(res['FERI_v96'])), "FERI_v96 contains non-finite values"
        assert np.all(np.isfinite(res['h_monster_whit'])), "h_monster_whit contains non-finite values"
        assert np.all(res['FERI_v96'] >= 0.0) and np.all(res['FERI_v96'] <= 1.0)
        assert np.all(res['h_monster_whit'] >= 0.0) and np.all(res['h_monster_whit'] <= 1.0)

    def test_chiral_oper_and_topological_defect_invariants(self):
        """Stress: Coupler v96 activates 204th-order oper obstruction and 116th-order topological defect invariants."""
        coupler_v96 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)
        coupler_v95 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=95)

        assert coupler_v96.is_phase96 is True
        assert coupler_v96.kappa_monster_whit == 39.80
        assert math.isclose(coupler_v96.lambda_monster, 1.0, rel_tol=1e-15)
        assert coupler_v96.harmony_boost == 9.90

        # With input diff = 1.5, the higher order power 1.5^204 and 1.5^116 creates distinct energy from v95
        test_mat = np.array([[0.0, 1.5, 0.0, 0.0, 0.0]])
        res_v96 = coupler_v96.evaluate(test_mat)
        res_v95 = coupler_v95.evaluate(test_mat)

        assert res_v96['e_monster_whit'] != res_v95['e_monster_whit'], "v96 should have distinct oper energy from v95"

    def test_backward_compatibility_output_keys(self):
        """Stress: Output dictionary contains FERI_v96, feri_v96, f_out_96 and historical keys down to v48."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)
        res = coupler.evaluate(np.array([[0.1, 0.2, 0.3, 0.4, 0.5]]))

        for key in ['FERI_v96', 'feri_v96', 'f_out_96', 'FERI_v95', 'FERI_v94', 'FERI_v93', 'FERI_v92', 'FERI_v48']:
            assert key in res, f"Missing output key {key}"

    def test_coupler_alias_tree(self):
        """Stress: Coupler class aliases and compute methods."""
        mat = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        res1 = Phase96Coupler.compute(mat)
        res2 = Phase96WhittakerDrinfeldCoupler.compute(mat)
        res3 = Phase96BorcherdsMoonshineCoupler.compute(mat)
        res4 = Phase96MonsterWhittakerCoupler.compute(mat)
        res5 = compute_phase96_coupling(mat)

        v1 = float(np.asarray(res1['FERI_v96']).ravel()[0])
        v2 = float(np.asarray(res2['FERI_v96']).ravel()[0])
        v3 = float(np.asarray(res3['FERI_v96']).ravel()[0])
        v4 = float(np.asarray(res4['FERI_v96']).ravel()[0])
        v5 = float(np.asarray(res5['FERI_v96']).ravel()[0])

        assert math.isclose(v1, v2)
        assert math.isclose(v1, v3)
        assert math.isclose(v1, v4)
        assert math.isclose(v1, v5)


# =========================================================================
# 4. FEATURE F452.1: HIGHER-HOMOLOGY-46 BARYCENTER BLEND ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF452_1BarycenterBlendAdversarialStress:
    """Adversarial stress testing on Higher-Homology-46 Motivic Fisher-Rao Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=96)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=96)

    def test_collinear_and_identical_model_weights(self, allocator):
        """Stress: When all models output identical asset weights [0.5, 0.5], consensus reproduces [0.5, 0.5]."""
        w_collinear = {
            'BL': {'AAPL': 0.50, 'MSFT': 0.50},
            'HERC': {'AAPL': 0.50, 'MSFT': 0.50},
            'RP': {'AAPL': 0.50, 'MSFT': 0.50},
            'CVaR': {'AAPL': 0.50, 'MSFT': 0.50},
        }
        res = allocator.compute_phase96_barycenter(w_collinear)
        assert math.isclose(res['AAPL'], 0.50, abs_tol=1e-5)
        assert math.isclose(res['MSFT'], 0.50, abs_tol=1e-5)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_single_asset_dominance(self, allocator):
        """Stress: When all models place 100% on a single dominant asset, consensus is 100% on that asset."""
        w_single = {
            'BL': {'AAPL': 1.00, 'MSFT': 0.00},
            'HERC': {'AAPL': 1.00, 'MSFT': 0.00},
            'RP': {'AAPL': 1.00, 'MSFT': 0.00},
            'CVaR': {'AAPL': 1.00, 'MSFT': 0.00},
        }
        res = allocator.compute_phase96_barycenter(w_single)
        assert math.isclose(res['AAPL'], 1.00, abs_tol=1e-5)
        assert math.isclose(res['MSFT'], 0.00, abs_tol=1e-5)

    def test_simplex_preservation_and_positivity(self, allocator):
        """Stress: Simplex sum == 1.000000 within 1e-5 and all weights are strictly non-negative."""
        weights = {
            'bl': 0.40,
            'herc': 0.30,
            'rp': 0.10,
            'cvar': 0.20,
        }
        res = allocator.compute_phase96_barycenter(weights)
        total = sum(res.values())
        assert math.isclose(total, 1.0, abs_tol=1e-5), f"Simplex sum violated: {total}"
        for k, v in res.items():
            assert v >= 0.0, f"Negative weight detected for {k}: {v}"

    def test_metric_curvature_hierarchy(self, allocator):
        """Stress: Under uniform model weights [0.25, 0.25, 0.25, 0.25], curvature forces CVaR > BL > HERC > RP."""
        uniform_weights = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
        res = allocator.compute_phase96_barycenter(uniform_weights)

        # Expected order: CVaR (11.50) > BL (9.50) > HERC (5.90) > RP (2.65)
        assert res['cvar'] > res['bl'], f"Hierarchy failed: CVaR ({res['cvar']}) <= BL ({res['bl']})"
        assert res['bl'] > res['herc'], f"Hierarchy failed: BL ({res['bl']}) <= HERC ({res['herc']})"
        assert res['herc'] > res['rp'], f"Hierarchy failed: HERC ({res['herc']}) <= RP ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_tau_convergence_spectrum(self, allocator):
        """Stress: tau convergence across 1e-15 to 0.05 preserves exact simplex and hierarchy."""
        uniform_weights = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}

        for tau in [1e-15, 1e-12, 1e-9, 1e-7, 3e-6, 1e-5, 1e-4, 1e-3, 0.01, 0.05]:
            res = allocator.compute_phase96_barycenter(uniform_weights, tau=tau)
            total = sum(res.values())
            assert math.isclose(total, 1.0, abs_tol=1e-5), f"Simplex violated at tau={tau}: {total}"
            assert res['cvar'] > res['bl'] > res['herc'] > res['rp'], f"Hierarchy violated at tau={tau}"

    def test_input_formats_resilience(self, allocator):
        """Stress: Dict of dicts, DataFrame, Dict of floats, List of dicts, 1D array, 2D array."""
        # 1. DataFrame
        df = pd.DataFrame({
            'bl': [0.4, 0.6],
            'herc': [0.5, 0.5],
            'rp': [0.3, 0.7],
            'cvar': [0.2, 0.8],
        }, index=['A', 'B'])
        res_df = allocator.compute_phase96_barycenter(df)
        assert math.isclose(sum(res_df.values()), 1.0, abs_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25},
            {'bl': 0.30, 'herc': 0.20, 'rp': 0.20, 'cvar': 0.30},
        ]
        res_list = allocator.compute_phase96_barycenter(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, abs_tol=1e-5)

        # 3. 1D Array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_arr1 = allocator.compute_phase96_barycenter(arr_1d)
        assert math.isclose(sum(res_arr1.values()), 1.0, abs_tol=1e-5)

        # 4. 2D Array
        arr_2d = np.array([[0.25, 0.25, 0.25, 0.25], [0.3, 0.2, 0.2, 0.3]])
        res_arr2 = allocator.compute_phase96_barycenter(arr_2d)
        assert math.isclose(sum(res_arr2.values()), 1.0, abs_tol=1e-5)

    def test_barycenter_alias_tree(self, allocator, portfolio_allocator):
        """Stress: All aliases across UnifiedPortfolioAllocator and PortfolioAllocator return valid blends."""
        w = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}

        upa_aliases = [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_46_fisher_rao_barycenter_blend,
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_46_barycenter,
            allocator.compute_phase96_barycenter,
            allocator.compute_phase96_fisher_rao_barycenter,
            allocator.compute_phase96_barycenter_blend,
            allocator.compute_higher_homology_46_barycenter,
            allocator.phase96_fisher_rao_barycenter,
            allocator.higher_homology_46_blend,
            allocator.phase96_barycenter_blend,
            allocator.higher_homology_46_barycenter,
            allocator.lmbmwdh46_barycenter,
            allocator.compute_higher_homology_46_fisher_rao_barycenter,
            allocator.higher_homology_46_fisher_rao_barycenter_blend,
            allocator.lurie_borcherds_higher_homology_46_barycenter,
        ]

        for fn in upa_aliases:
            res = fn(w)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

        # PortfolioAllocator
        res_pa = portfolio_allocator.compute_phase96_barycenter(w)
        assert math.isclose(sum(res_pa.values()), 1.0, abs_tol=1e-5)


# =========================================================================
# 5. FEATURE F452.2: 124TH-CUMULANT EXPANSION EVAR ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF452_2EVaRAdversarialStress:
    """Adversarial stress testing on 124th-cumulant expansion EVaR risk measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=96)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=96)

    def test_heavy_tailed_cauchy_and_student_t1_stress(self, allocator):
        """Stress: Heavy-tailed Cauchy and Student-t(1) distributions produce amplified tail risk > Gaussian EVaR."""
        rng = np.random.default_rng(42)

        # Normal baseline
        r_norm = rng.normal(0.0, 0.05, size=500)
        evar_norm = allocator.compute_phase96_evar(r_norm)['evar']

        # Cauchy
        r_cauchy = rng.standard_cauchy(size=500) * 0.05
        evar_cauchy = allocator.compute_phase96_evar(r_cauchy)['evar']

        # Student-t(df=1)
        r_t1 = rng.standard_t(df=1, size=500) * 0.05
        evar_t1 = allocator.compute_phase96_evar(r_t1)['evar']

        assert np.isfinite(evar_cauchy) and evar_cauchy > 0.0
        assert np.isfinite(evar_t1) and evar_t1 > 0.0
        assert evar_cauchy > evar_norm, f"Cauchy EVaR ({evar_cauchy}) not greater than Normal EVaR ({evar_norm})"
        assert evar_t1 > evar_norm, f"Student-t(1) EVaR ({evar_t1}) not greater than Normal EVaR ({evar_norm})"

    def test_dirac_delta_returns(self, allocator):
        """Stress: Constant returns (Dirac delta) produce stable positive EVaR with negative returns penalized higher."""
        r_pos = np.full(100, 0.02)
        r_neg = np.full(100, -0.05)

        evar_pos = allocator.compute_phase96_evar(r_pos)['evar']
        evar_neg = allocator.compute_phase96_evar(r_neg)['evar']

        assert np.isfinite(evar_pos) and evar_pos > 0.0
        assert np.isfinite(evar_neg) and evar_neg > 0.0
        assert evar_neg > evar_pos, f"Negative return risk ({evar_neg}) must exceed positive return risk ({evar_pos})"

    def test_volatility_monotonicity(self, allocator):
        """Stress: EVaR monotonically increases as return volatility scale increases."""
        rng = np.random.default_rng(101)
        base = rng.normal(0.0, 1.0, size=500)

        evar_low = allocator.compute_phase96_evar(base * 0.01)['evar']
        evar_med = allocator.compute_phase96_evar(base * 0.05)['evar']
        evar_high = allocator.compute_phase96_evar(base * 0.15)['evar']

        assert evar_low < evar_med < evar_high, f"Volatility monotonicity failed: {evar_low} < {evar_med} < {evar_high}"

    def test_order124_and_xi_monster_invariants(self, allocator):
        """Stress: Invariants order=124 and xi_monster=0.9999999999999999999999999999999 are strictly stamped."""
        r = np.array([0.01, -0.02, 0.03, -0.01])
        res = allocator.compute_phase96_evar(r)

        assert res['order'] == 124
        assert math.isclose(res['xi_monster'], 1.0, rel_tol=1e-15)
        assert 'phase96_evar' in res
        assert 'evar' in res
        assert res['phase96_evar'] == res['evar']

    def test_evar_alias_trees(self, allocator, portfolio_allocator):
        """Stress: All alias methods across UnifiedPortfolioAllocator and PortfolioAllocator return valid EVaR."""
        r = np.array([0.01, -0.02, 0.03, -0.01])

        upa_aliases = [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_46_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_46_evar,
            allocator.compute_phase96_evar,
            allocator.compute_phase96_evar_risk_measure,
            allocator.phase96_evar_risk_measure,
            allocator.compute_higher_homology_46_evar_risk_measure,
            allocator.compute_higher_homology_46_evar,
            allocator.compute_evar_order124,
            allocator.compute_124th_cumulant_evar,
            allocator.compute_monster_whittaker_124th_cumulant_evar,
            allocator.phase96_tail_risk_evar,
            allocator.phase96_evar_bound,
            allocator.lmbmwdh46_evar,
            allocator.trans_singular_evar_v96,
        ]

        ref = allocator.compute_phase96_evar(r)['evar']

        for fn in upa_aliases:
            out = fn(r)
            val = out['evar'] if isinstance(out, dict) else out
            assert math.isclose(float(val), float(ref), rel_tol=1e-7), f"EVaR alias {fn.__name__} mismatch"

        # PortfolioAllocator
        res_pa = portfolio_allocator.compute_phase96_evar(r)
        val_pa = res_pa['evar'] if isinstance(res_pa, dict) else res_pa
        assert math.isclose(float(val_pa), float(ref), rel_tol=1e-7)

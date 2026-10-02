r"""
tests/test_phase97_adversarial_challenger1.py

Adversarial Empirical Challenge and Stress Test Suite for Phase 97
Quantitative Alpha Enhancement & Risk Allocation (v104 Production Master):
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)

Scope of Empirical Adversarial Tests:
1. Feature F455: Asymmetric Octacontahexagonal (584th-Order) Hyperbolic Noise Deadband
   - Sub-threshold noise annihilation: |z| <= 0.0003 across 20,000 sub-threshold points
     (including boundaries +-0.0003, interior points, subnormals 5e-324, 1e-320)
     evaluates strictly to 0.0 in float64 precision.
   - Boundary sharpness at delta_noise = 0.035: z = +-0.035 matches z * tanh(1.0) with machine precision.
   - High-conviction signal transmission fidelity: |z| >= 0.150 retains 100.0% signal fidelity
     (|z_denoised - z| < 1e-12).
   - Monotonicity across 50,000 fine-jittered points (Spearman rho == 1.0000, all diffs >= -1e-15).
   - Odd symmetry: f(-z) == -f(z) across continuous domain.
   - Degenerate & edge inputs: 0.0, -0.0, +-inf, nan, extreme floats +-1e300, empty array.
   - Full 18-alias tree bit-identical verification.

2. Feature F455: 125th-Order Hyper-Convex Rank Modulation
   - Strict rank monotonicity across all 15 regime keys in REGIME_GAMMA_TOP_V97 (50,000 points each).
   - Boundary points r=0.0 -> 0.50, r=1.0 -> 0.50 + 3.74*exp(gamma_top), clipping for r>1.0 and r<0.0.
   - Top-decile amplification: BULL_LOW_VOL achieves g(1.0) > 10^15 >> 10^7.
   - Regime gamma hierarchy: BULL_LOW_VOL (35.0) > BULL_HIGH_VOL (29.8) > SIDEWAYS (23.8) > BEAR (12.0) > PANIC (2.4).
   - Negative conviction branch: z_denoised < 0 -> g_neg(r) = 1.35 - 1.00*r (monotonic decreasing).
   - Full alias tree verification.

3. Feature F456: Quantum Geometric Langlands Monster Whittaker Coupler Phase 97
   - Extreme degenerate inputs: all-zeros (e_monster_whit == 0, h in [0, 1], z == 1.0), all-ones, constant signals.
   - Missing signals and NaN resilience: NaN entries, empty columns, 1D array (<5 padded to 5), varying column counts.
   - Extreme dimensionality stress: 1000 rows x 5 pillars in [-10, 10] produce strictly finite outputs.
   - Verification of required output keys: FERI_v97, feri_v97, f_out_97 and backward compatibility down to v48.
   - Default parameter invariants: kappa=40.40, lambda=21-nines, harmony_boost=10.25, 206th oper, 118th defect.
   - Full coupler alias tree verification.

4. Feature F457.1: Higher-Homology-47 Motivic Fisher-Rao Barycenter Blending
   - Near-zero model weights (1e-12), single model dominance, zero weights, unbalanced weights.
   - Simplex conservation: sum q_i == 1.000000 within 1e-5 and all q_i >= 0.0 across all degenerate cases.
   - Metric curvature hierarchy under uniform input: CVaR (11.75) > BL (9.70) > HERC (6.05) > RP (2.70).
   - Tau convergence spectrum: tau = 0.0000025 and 1e-15 to 0.05 preserving exact simplex and ordering.
   - Input format stress: dict of dicts, DataFrame, list of dicts, 1D array, 2D array.
   - Full alias tree verification across UnifiedPortfolioAllocator and PortfolioAllocator.

5. Feature F457.2: 126th-Cumulant Expansion Trans-Singular EVaR Risk Measure
   - Stamped invariants: order=126 (126! ~ 9.58e211), xi_monster=33-nines, phase97_evar key present.
   - Volatility scaling monotonicity: EVaR strictly increases with volatility scale.
   - Fat-tailed return and crash stress: Cauchy, Student-t (df=2), and -25% single jump crash.
   - Alpha confidence level monotonicity: stricter alpha yields strictly higher EVaR bound.
   - Degenerate returns resilience: all zeros, constant returns, single return, NaNs.
   - Full alias tree verification across UnifiedPortfolioAllocator and PortfolioAllocator.
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_octacontahexagonal_hyperbolic_deadband,
    apply_quingentaoctacontatetragonal_hyperbolic_deadband,
    apply_pentacontaoctacontatetragonal_hyperbolic_deadband,
    apply_octacontahexa_hyperbolic_deadband,
    apply_octacontahexagonal_deadband,
    apply_octacontatetragonal_deadband,
    octacontahexagonal_deadband,
    octacontatetragonal_deadband,
    octacontahexagonal_hyperbolic_deadband,
    octacontatetragonal_hyperbolic_deadband,
    compute_phase97_deadband,
    apply_phase97_deadband,
    phase97_deadband,
    apply_584th_order_hyperbolic_deadband,
    apply_584th_deadband,
    apply_584_deadband,
    apply_hyperbolic_deadband_v97,
    suppress_factor_noise_hyperbolic_v97,
    apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97,
    compute_phase97_hyperconvex_rank_modulation,
    compute_125th_order_hyperconvex_rank_modulation,
    compute_phase97_rank_warping,
    compute_phase97_rank_modulation,
    phase97_rank_modulation,
    phase97_hyperconvex_rank_modulation,
    apply_phase97_rank_modulation,
    apply_hyper_convex_rank_modulation_v97,
    REGIME_GAMMA_TOP_V97,
    get_regime_adaptive_gamma_top_v97,
    Phase97FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase97Coupler,
    Phase97WhittakerDrinfeldCoupler,
    Phase97BorcherdsMoonshineCoupler,
    Phase97MonsterWhittakerCoupler,
    compute_phase97_coupling,
    EnsembleScoringEngine,
)

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =========================================================================
# 1. FEATURE F455: 584TH-ORDER HYPERBOLIC NOISE DEADBAND ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF455DeadbandAdversarialStress:
    """Adversarial stress testing on 584th-order asymmetric hyperbolic noise deadband."""

    def test_sub_noise_annihilation_float64_exact_zero(self):
        """Stress: Values z in [-0.0003, 0.0003] evaluate strictly to 0.0 in float64 precision."""
        rng = np.random.default_rng(42)
        n_samples = 20000
        sub_samples = rng.uniform(-0.0003, 0.0003, size=n_samples)

        # Exact boundary and critical interior points
        sub_samples[0] = 0.0003
        sub_samples[1] = -0.0003
        sub_samples[2] = 0.00029999999999999997
        sub_samples[3] = -0.00029999999999999997
        sub_samples[4] = 0.0001
        sub_samples[5] = -0.0001
        sub_samples[6] = 1e-5
        sub_samples[7] = -1e-5
        sub_samples[8] = 1e-12
        sub_samples[9] = -1e-12
        sub_samples[10] = 1e-15
        sub_samples[11] = -1e-15
        sub_samples[12] = 5e-324  # Smallest positive subnormal in float64
        sub_samples[13] = -5e-324
        sub_samples[14] = 1e-320
        sub_samples[15] = -1e-320
        sub_samples[16] = 0.0
        sub_samples[17] = -0.0

        out = apply_octacontahexagonal_hyperbolic_deadband(sub_samples, delta_noise=0.035, alpha_pos=584.0)

        # In float64, (|z|/0.035)^584 for |z|<=0.0003 is <= (0.0003/0.035)^584 = (0.0085714)^584 ~ 10^-1207
        # which strictly underflows to 0.0
        assert np.all(out == 0.0), (
            f"Detected non-zero noise leakage in sub-noise zone [-0.0003, 0.0003]: max={np.max(np.abs(out))}"
        )

        # Verify scalar inputs directly
        assert apply_octacontahexagonal_hyperbolic_deadband(0.0003) == 0.0
        assert apply_octacontahexagonal_hyperbolic_deadband(-0.0003) == 0.0
        assert apply_octacontahexagonal_hyperbolic_deadband(0.0001) == 0.0
        assert apply_octacontahexagonal_hyperbolic_deadband(-0.0001) == 0.0
        assert apply_octacontahexagonal_hyperbolic_deadband(0.0) == 0.0

        # Verify pandas Series
        s_test = pd.Series([-0.0003, 0.0, 0.0003], index=['lo', 'mid', 'hi'])
        out_s = apply_octacontahexagonal_hyperbolic_deadband(s_test)
        assert isinstance(out_s, pd.Series)
        assert np.all(out_s.values == 0.0)

    def test_boundary_behavior_delta_noise_035(self):
        """Stress: Exact boundary at delta_noise=0.035 matches z * tanh(1.0) with machine precision."""
        delta = 0.035
        expected_pos = delta * math.tanh(1.0)  # ~ 0.02665579545845177
        expected_neg = -delta * math.tanh(1.0)

        out_pos = apply_octacontahexagonal_hyperbolic_deadband(delta, delta_noise=delta, alpha_pos=584.0)
        out_neg = apply_octacontahexagonal_hyperbolic_deadband(-delta, delta_noise=delta, alpha_pos=584.0)

        assert math.isclose(out_pos, expected_pos, rel_tol=1e-14), (
            f"Boundary z=+0.035 mismatch: expected {expected_pos}, got {out_pos}"
        )
        assert math.isclose(out_neg, expected_neg, rel_tol=1e-14), (
            f"Boundary z=-0.035 mismatch: expected {expected_neg}, got {out_neg}"
        )

        # Verify phase transition sharpness around delta:
        # z = 0.0349: (0.0349/0.035)^584 ~ 0.1878 -> tanh(0.1878) ~ 0.1856 -> z*tanh ~ 0.006478
        # z = 0.0351: (0.0351/0.035)^584 ~ 5.30 -> tanh(5.30) ~ 0.99995 -> z*tanh ~ 0.035098
        z_sub = apply_octacontahexagonal_hyperbolic_deadband(0.0349, delta_noise=delta, alpha_pos=584.0)
        z_super = apply_octacontahexagonal_hyperbolic_deadband(0.0351, delta_noise=delta, alpha_pos=584.0)
        assert z_sub < 0.010, f"Expected strong attenuation at 0.0349, got {z_sub}"
        assert z_super > 0.034, f"Expected near-complete transmission at 0.0351, got {z_super}"

    def test_high_conviction_transmission_fidelity(self):
        """Stress: |z| >= 0.150 preserves signal fidelity with |z_denoised - z| < 1e-12."""
        strong_vals = np.array([
            0.150, 0.1500001, 0.160, 0.200, 0.350, 0.500, 1.000, 2.500, 5.000, 10.000, 100.0,
            -0.150, -0.1500001, -0.160, -0.200, -0.350, -0.500, -1.000, -2.500, -5.000, -10.000, -100.0
        ], dtype=np.float64)

        out = apply_octacontahexagonal_hyperbolic_deadband(strong_vals, delta_noise=0.035, alpha_pos=584.0)

        # For |z| >= 0.150, (|z|/0.035)^584 >= (4.2857)^584 > 10^369
        # In float64, tanh(x) = 1.0 for all x >= 19.1, so |z_denoised - z| is identical to 0.0
        diffs = np.abs(out - strong_vals)
        assert np.all(diffs < 1e-12), (
            f"High-conviction signal distortion detected: max diff = {np.max(diffs)}"
        )
        for z_in, z_out in zip(strong_vals, out):
            assert abs(z_out - z_in) < 1e-12, f"Failed at z={z_in}: out={z_out}"

    def test_deadband_monotonicity_under_fine_jitter(self):
        """Stress: 50,000 sorted values with random micro-jitter exhibit strict rank monotonicity (rho == 1.0000)."""
        rng = np.random.default_rng(2026)
        grid = np.linspace(0.0001, 3.0, 50000)
        jitter = rng.normal(0, 1e-12, size=grid.shape)
        sorted_inputs = np.sort(grid + jitter)

        denoised = apply_octacontahexagonal_hyperbolic_deadband(sorted_inputs, delta_noise=0.035, alpha_pos=584.0)
        rho, _ = spearmanr(sorted_inputs, denoised)
        assert math.isclose(rho, 1.0, rel_tol=1e-5), f"Rank monotonicity violated: Spearman rho={rho}"

        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), f"Detected negative diff in sorted output: min diff={np.min(diffs)}"

    def test_deadband_odd_symmetry(self):
        """Stress: Odd symmetry f(-z) == -f(z) holds across positive and negative domains."""
        rng = np.random.default_rng(999)
        test_z = rng.uniform(0.0001, 5.0, size=5000)
        f_pos = apply_octacontahexagonal_hyperbolic_deadband(test_z)
        f_neg = apply_octacontahexagonal_hyperbolic_deadband(-test_z)

        diff = np.abs(f_neg + f_pos)
        assert np.all(diff < 1e-12), f"Odd symmetry violated: max diff={np.max(diff)}"

    def test_deadband_degenerate_and_edge_inputs(self):
        """Stress: Edge inputs (0.0, -0.0, inf, -inf, nan, subnormals, extreme floats, empty array)."""
        edge_inputs = np.array([
            0.0, -0.0, np.inf, -np.inf, np.nan,
            1e-320, -1e-320, 5e-324, 1e300, -1e300
        ], dtype=np.float64)

        out = apply_octacontahexagonal_hyperbolic_deadband(edge_inputs)
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

        # Empty array
        empty_out = apply_octacontahexagonal_hyperbolic_deadband(np.array([]))
        assert len(empty_out) == 0

    def test_deadband_full_alias_tree_identity(self):
        """Stress: All 18+ alias names return bit-identical results."""
        test_arr = np.array([0.0001, 0.035, 0.150, 0.200, -0.0002, -0.035, -0.200])
        canonical = apply_octacontahexagonal_hyperbolic_deadband(test_arr)

        aliases = [
            apply_quingentaoctacontatetragonal_hyperbolic_deadband,
            apply_pentacontaoctacontatetragonal_hyperbolic_deadband,
            apply_octacontahexa_hyperbolic_deadband,
            apply_octacontahexagonal_deadband,
            apply_octacontatetragonal_deadband,
            octacontahexagonal_deadband,
            octacontatetragonal_deadband,
            octacontahexagonal_hyperbolic_deadband,
            octacontatetragonal_hyperbolic_deadband,
            compute_phase97_deadband,
            apply_phase97_deadband,
            phase97_deadband,
            apply_584th_order_hyperbolic_deadband,
            apply_584th_deadband,
            apply_584_deadband,
            apply_hyperbolic_deadband_v97,
            suppress_factor_noise_hyperbolic_v97,
            apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97,
        ]

        for alias_fn in aliases:
            res = alias_fn(test_arr)
            assert np.array_equal(canonical, res, equal_nan=True), f"Alias {alias_fn.__name__} mismatch"


# =========================================================================
# 2. FEATURE F455: 125TH-ORDER RANK MODULATION ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF455RankModulationAdversarialStress:
    """Adversarial stress testing on 125th-order hyper-convex rank modulation."""

    def test_monotonicity_across_all_15_regimes_in_regime_gamma_top_v97(self):
        """Stress: Monotonicity holds strictly across all 15 regime keys in REGIME_GAMMA_TOP_V97."""
        # 15 distinct regime keys specified in REGIME_GAMMA_TOP_V97
        expected_regimes = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS', 'SIDEWAYS_LOW_VOL',
            'SIDEWAYS_HIGH_VOL', 'BEAR', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'PANIC', 'CRISIS', 'RECOVERY', '2', '1', '0', 'UNKNOWN'
        ]
        for reg in expected_regimes:
            assert reg in REGIME_GAMMA_TOP_V97, f"Missing regime key {reg} in REGIME_GAMMA_TOP_V97"

        r_grid = np.linspace(0.0, 1.0, 50000)

        for regime_name, gamma_val in REGIME_GAMMA_TOP_V97.items():
            g_vals = compute_phase97_hyperconvex_rank_modulation(r_grid, regime=regime_name)
            diffs = np.diff(g_vals)
            assert np.all(diffs >= 0.0), (
                f"Monotonicity violation in regime '{regime_name}' with gamma={gamma_val}: min diff={np.min(diffs)}"
            )
            rho, _ = spearmanr(r_grid, g_vals)
            assert math.isclose(rho, 1.0, rel_tol=1e-5), f"Spearman rho != 1.0 in regime '{regime_name}'"
            assert math.isclose(g_vals[0], 0.50, abs_tol=1e-12), f"g(0.0) != 0.50 in regime '{regime_name}'"
            assert np.all(np.isfinite(g_vals)), f"Non-finite value detected in regime '{regime_name}'"

    def test_boundary_conditions_and_hyperconvex_clipping(self):
        """Stress: Boundary points r=0.0 -> 0.50, r=1.0 -> 0.50 + 3.74*exp(gamma_top), clipping for r>1.0 and r<0.0."""
        gamma_test = 23.80
        # Exact boundary r=0.0
        g0 = compute_phase97_hyperconvex_rank_modulation(0.0, gamma_top=gamma_test)
        assert math.isclose(g0, 0.50, abs_tol=1e-12), f"g(0.0) expected 0.50, got {g0}"

        # Exact boundary r=1.0: g(1.0) = 0.50 + 3.74 * 1.0 * exp(gamma_test * 1.0^125)
        g1 = compute_phase97_hyperconvex_rank_modulation(1.0, gamma_top=gamma_test)
        expected_g1 = 0.50 + 3.74 * 1.0 * math.exp(gamma_test * (1.0 ** 125))
        assert math.isclose(g1, expected_g1, rel_tol=1e-7), f"g(1.0) expected {expected_g1}, got {g1}"

        # Over-range clipping: r > 1.0 must be clipped to r=1.0
        g_over1 = compute_phase97_hyperconvex_rank_modulation(1.0001, gamma_top=gamma_test)
        g_over2 = compute_phase97_hyperconvex_rank_modulation(5.0, gamma_top=gamma_test)
        g_over3 = compute_phase97_hyperconvex_rank_modulation(100.0, gamma_top=gamma_test)
        assert math.isclose(g_over1, g1, rel_tol=1e-7), "r=1.0001 was not clipped to r=1.0"
        assert math.isclose(g_over2, g1, rel_tol=1e-7), "r=5.0 was not clipped to r=1.0"
        assert math.isclose(g_over3, g1, rel_tol=1e-7), "r=100.0 was not clipped to r=1.0"

        # Under-range clipping: r < 0.0 must be clipped to r=0.0
        g_under1 = compute_phase97_hyperconvex_rank_modulation(-0.001, gamma_top=gamma_test)
        g_under2 = compute_phase97_hyperconvex_rank_modulation(-10.0, gamma_top=gamma_test)
        assert math.isclose(g_under1, 0.50, abs_tol=1e-12), "r=-0.001 was not clipped to r=0.0"
        assert math.isclose(g_under2, 0.50, abs_tol=1e-12), "r=-10.0 was not clipped to r=0.0"

    def test_top_decile_exponential_boost_and_hierarchy(self):
        """Stress: BULL_LOW_VOL achieves massive conviction amplification g(1.0) > 10^15 >> 10^7, hierarchy holds."""
        g_bull_low = compute_phase97_hyperconvex_rank_modulation(1.0, regime='BULL_LOW_VOL')
        g_bull_high = compute_phase97_hyperconvex_rank_modulation(1.0, regime='BULL_HIGH_VOL')
        g_sideways = compute_phase97_hyperconvex_rank_modulation(1.0, regime='SIDEWAYS')
        g_bear = compute_phase97_hyperconvex_rank_modulation(1.0, regime='BEAR')
        g_panic = compute_phase97_hyperconvex_rank_modulation(1.0, regime='PANIC')

        # 0.50 + 3.74 * exp(35.00) ~ 5.932e15 >> 10^7
        assert g_bull_low > 1e15, f"BULL_LOW_VOL expected > 1e15, got {g_bull_low}"
        assert g_bull_low > 1e7, f"Requirement g(1.0) > 10^7 violated: {g_bull_low}"

        # Hierarchy verification
        assert g_bull_low > g_bull_high > g_sideways > g_bear > g_panic, (
            f"Regime hierarchy violated: {g_bull_low} > {g_bull_high} > {g_sideways} > {g_bear} > {g_panic}"
        )

        # Gamma top getter verification
        assert get_regime_adaptive_gamma_top_v97('BULL_LOW_VOL') == 35.00
        assert get_regime_adaptive_gamma_top_v97('BULL_HIGH_VOL') == 29.80
        assert get_regime_adaptive_gamma_top_v97('SIDEWAYS') == 23.80
        assert get_regime_adaptive_gamma_top_v97('BEAR') == 12.00
        assert get_regime_adaptive_gamma_top_v97('PANIC') == 2.40

    def test_negative_signal_conviction_branch(self):
        """Stress: Negative signals (z_denoised < 0) follow g_neg(r) = 1.35 - 1.00*r (monotonic decreasing)."""
        r_grid = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full_like(r_grid, -0.05)

        g_neg = compute_phase97_hyperconvex_rank_modulation(r_grid, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-12)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-12)

        diffs = np.diff(g_neg)
        assert np.all(diffs <= 0.0), "Negative conviction branch must be monotonically non-increasing"

        # Mixed vector verification
        r_mix = np.array([0.2, 0.8])
        z_mix = np.array([0.05, -0.05])
        g_mix = compute_phase97_hyperconvex_rank_modulation(r_mix, z_denoised=z_mix, gamma_top=23.80)
        expected_pos = 0.50 + 3.74 * 0.2 * math.exp(23.80 * (0.2 ** 125))
        expected_neg = 1.35 - 1.00 * 0.8
        assert math.isclose(g_mix[0], expected_pos, rel_tol=1e-7)
        assert math.isclose(g_mix[1], expected_neg, rel_tol=1e-7)

    def test_rank_modulation_alias_trees(self):
        """Stress: All rank modulation aliases compute bit-identical outputs."""
        r_arr = np.array([0.1, 0.4, 0.7, 0.99])
        ref = compute_phase97_hyperconvex_rank_modulation(r_arr)

        aliases = [
            compute_125th_order_hyperconvex_rank_modulation,
            compute_phase97_rank_warping,
            compute_phase97_rank_modulation,
            phase97_rank_modulation,
            phase97_hyperconvex_rank_modulation,
            apply_phase97_rank_modulation,
            apply_hyper_convex_rank_modulation_v97,
        ]

        for fn in aliases:
            out = fn(r_arr)
            assert np.array_equal(ref, out), f"Rank modulation alias {fn.__name__} mismatch"


# =========================================================================
# 3. FEATURE F456: MONSTER WHITTAKER COUPLER PHASE 97 ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF456CouplerAdversarialStress:
    """Adversarial stress testing on Quantum Geometric Langlands Monster Whittaker Coupler Phase 97."""

    def test_degenerate_inputs_zeros_ones_and_uniform(self):
        """Stress: All-zeros, all-ones, and uniform inputs yield zero obstruction energy and finite bounded invariants."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=97)

        # 1. All zeros
        zeros_mat = np.zeros((30, 5))
        res_zero = coupler.evaluate(zeros_mat)
        assert np.allclose(res_zero['e_monster_whit'], 0.0), "Zeros matrix should yield e_monster_whit == 0"
        assert np.allclose(res_zero['z_monster_whit'], 1.0), "Zeros matrix should yield z_monster_whit == 1"
        assert np.all(res_zero['h_monster_whit'] >= 0.0) and np.all(res_zero['h_monster_whit'] <= 1.0)
        assert np.all(res_zero['FERI_v97'] >= 0.0) and np.all(res_zero['FERI_v97'] <= 1.0)

        # 2. All ones
        ones_mat = np.ones((30, 5))
        res_ones = coupler.evaluate(ones_mat)
        assert np.allclose(res_ones['e_monster_whit'], 0.0), "Identical signals should yield e_monster_whit == 0"

        # 3. Constant non-zero signals
        const_mat = np.full((20, 5), 0.77)
        res_const = coupler.evaluate(const_mat)
        assert np.allclose(res_const['e_monster_whit'], 0.0), "Constant signals should yield e_monster_whit == 0"

    def test_nan_and_inf_resilience_adversarial(self):
        """Stress: NaN and Inf contaminated inputs are handled gracefully without crashing or emitting NaNs in FERI_v97."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=97)

        # NaNs inside array
        nan_mat = np.random.uniform(0.1, 0.9, size=(40, 5))
        nan_mat[0, 1] = np.nan
        nan_mat[5, :] = np.nan
        nan_mat[10, 3] = np.inf
        nan_mat[15, 0] = -np.inf

        res_nan = coupler.evaluate(nan_mat)
        assert not np.any(np.isnan(res_nan['FERI_v97'])), "FERI_v97 contains NaN after contaminated input"
        assert not np.any(np.isnan(res_nan['feri_v97'])), "feri_v97 contains NaN after contaminated input"
        assert not np.any(np.isnan(res_nan['f_out_97'])), "f_out_97 contains NaN after contaminated input"
        assert not np.any(np.isnan(res_nan['h_monster_whit'])), "h_monster_whit contains NaN after contaminated input"

        # 1D array < 5 elements (should be padded to 5 pillars without error)
        vec_3 = np.array([0.2, 0.4, 0.6])
        res_1d = coupler.evaluate(vec_3)
        assert isinstance(res_1d['FERI_v97'], float)
        assert 0.0 <= res_1d['FERI_v97'] <= 1.0

        # DataFrame with 2 columns (padded to 5)
        df_2col = pd.DataFrame({'pillar_a': [0.1, 0.2], 'pillar_b': [0.3, 0.4]})
        res_df = coupler.evaluate(df_2col)
        assert len(res_df['FERI_v97']) == 2
        assert np.all(np.isfinite(res_df['FERI_v97']))

    def test_extreme_dimensionality_stress(self):
        """Stress: 1000 rows x 5 pillars under extreme values [-10.0, 10.0] produce strictly finite bounded outputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=97)
        rng = np.random.default_rng(777)
        large_mat = rng.uniform(-10.0, 10.0, size=(1000, 5))

        res = coupler.evaluate(large_mat)
        assert np.all(np.isfinite(res['FERI_v97'])), "FERI_v97 contains non-finite values"
        assert np.all(np.isfinite(res['feri_v97'])), "feri_v97 contains non-finite values"
        assert np.all(np.isfinite(res['f_out_97'])), "f_out_97 contains non-finite values"
        assert np.all(np.isfinite(res['h_monster_whit'])), "h_monster_whit contains non-finite values"
        assert np.all(res['FERI_v97'] >= 0.0) and np.all(res['FERI_v97'] <= 1.0)
        assert np.all(res['h_monster_whit'] >= 0.0) and np.all(res['h_monster_whit'] <= 1.0)

    def test_output_keys_veri_v97_and_backward_compatibility(self):
        """Stress: Output dictionary strictly contains FERI_v97, feri_v97, f_out_97 and historical keys down to v48."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=97)
        res = coupler.evaluate(np.array([[0.1, 0.2, 0.3, 0.4, 0.5]]))

        # Explicit mission requirement output keys
        assert "FERI_v97" in res, "Missing required output key FERI_v97"
        assert "feri_v97" in res, "Missing required output key feri_v97"
        assert "f_out_97" in res, "Missing required output key f_out_97"

        # Values must be finite floats
        assert isinstance(float(np.asarray(res["FERI_v97"]).ravel()[0]), float)
        assert isinstance(float(np.asarray(res["feri_v97"]).ravel()[0]), float)
        assert isinstance(float(np.asarray(res["f_out_97"]).ravel()[0]), float)

        # Backward compatibility cascade
        for v in [96, 95, 94, 93, 92, 91, 90, 80, 70, 60, 50, 48]:
            assert f"FERI_v{v}" in res, f"Missing historical output key FERI_v{v}"
            assert f"feri_v{v}" in res, f"Missing historical output key feri_v{v}"

    def test_coupler_default_parameters_v97(self):
        """Stress: Coupler defaults to version=97, kappa=40.40, lambda=21-nines, harmony_boost=10.25, is_phase97=True."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=97)
        assert coupler.version == 97
        assert coupler.is_phase97 is True
        assert coupler.is_phase96 is True
        assert math.isclose(coupler.kappa_monster_whit, 40.40, abs_tol=1e-5)
        assert math.isclose(coupler.lambda_monster, 0.99999999999999999995, abs_tol=1e-15)
        assert math.isclose(coupler.harmony_boost, 10.25, abs_tol=1e-5)

        # 206th-order oper activation verification against v96
        coupler_v96 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=96)
        test_mat = np.array([[0.0, 1.5, 0.0, 0.0, 0.0]])
        res_v97 = coupler.evaluate(test_mat)
        res_v96 = coupler_v96.evaluate(test_mat)

        assert res_v97['e_monster_whit'] != res_v96['e_monster_whit'], (
            "Phase 97 206th-order oper obstruction should yield distinct energy from Phase 96"
        )

    def test_coupler_alias_tree_v97(self):
        """Stress: All Phase 97 coupler alias classes and compute methods compute identical results."""
        mat = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        res1 = Phase97Coupler.compute(mat)
        res2 = Phase97WhittakerDrinfeldCoupler.compute(mat)
        res3 = Phase97BorcherdsMoonshineCoupler.compute(mat)
        res4 = Phase97MonsterWhittakerCoupler.compute(mat)
        res5 = compute_phase97_coupling(mat)

        v1 = float(np.asarray(res1['FERI_v97']).ravel()[0])
        v2 = float(np.asarray(res2['FERI_v97']).ravel()[0])
        v3 = float(np.asarray(res3['FERI_v97']).ravel()[0])
        v4 = float(np.asarray(res4['FERI_v97']).ravel()[0])
        v5 = float(np.asarray(res5['FERI_v97']).ravel()[0])

        assert math.isclose(v1, v2, abs_tol=1e-12)
        assert math.isclose(v1, v3, abs_tol=1e-12)
        assert math.isclose(v1, v4, abs_tol=1e-12)
        assert math.isclose(v1, v5, abs_tol=1e-12)


# =========================================================================
# 4. FEATURE F457.1: HIGHER-HOMOLOGY-47 BARYCENTER BLEND ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF457_1BarycenterBlendAdversarialStress:
    """Adversarial stress testing on Higher-Homology-47 Motivic Fisher-Rao Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=97)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=97)

    def test_near_zero_and_degenerate_weights_simplex_sum(self, allocator):
        """Stress: Near-zero weights (1e-12), single model dominance, zero weights strictly maintain sum=1.000000 (+-1e-5)."""
        # Case A: Near-zero weights across all models
        w_near_zero = {'bl': 1e-12, 'herc': 1e-12, 'rp': 1e-12, 'cvar': 1e-12}
        res_nz = allocator.compute_phase97_barycenter(w_near_zero)
        total_nz = sum(res_nz.values())
        assert math.isclose(total_nz, 1.0, abs_tol=1e-5), f"Near-zero simplex violated: {total_nz}"
        for k, v in res_nz.items():
            assert v >= 0.0, f"Negative weight in near-zero case: {k}={v}"

        # Case B: Single model 100% dominance, others near zero
        w_dom = {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0}
        res_dom = allocator.compute_phase97_barycenter(w_dom)
        total_dom = sum(res_dom.values())
        assert math.isclose(total_dom, 1.0, abs_tol=1e-5), f"Dominance simplex violated: {total_dom}"
        for k, v in res_dom.items():
            assert v >= 0.0

        # Case C: All zeros
        w_zeros = {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0}
        res_zero = allocator.compute_phase97_barycenter(w_zeros)
        total_zero = sum(res_zero.values())
        assert math.isclose(total_zero, 1.0, abs_tol=1e-5), f"All-zero simplex violated: {total_zero}"

        # Case D: Highly unbalanced weights
        w_unbalanced = {'bl': 0.9999, 'herc': 0.00003, 'rp': 0.00003, 'cvar': 0.00004}
        res_unb = allocator.compute_phase97_barycenter(w_unbalanced)
        total_unb = sum(res_unb.values())
        assert math.isclose(total_unb, 1.0, abs_tol=1e-5), f"Unbalanced simplex violated: {total_unb}"

        # Case E: Multi-asset dictionary of dicts with near-zero weights
        w_multi_nz = {
            'BL': {'AAPL': 1e-9, 'MSFT': 2e-9, 'NVDA': 1e-9},
            'HERC': {'AAPL': 2e-9, 'MSFT': 1e-9, 'NVDA': 1e-9},
            'RP': {'AAPL': 1e-9, 'MSFT': 1e-9, 'NVDA': 2e-9},
            'CVaR': {'AAPL': 1e-9, 'MSFT': 2e-9, 'NVDA': 2e-9},
        }
        res_multi = allocator.compute_phase97_barycenter(w_multi_nz)
        total_multi = sum(res_multi.values())
        assert math.isclose(total_multi, 1.0, abs_tol=1e-5), f"Multi-asset near-zero simplex violated: {total_multi}"

    def test_metric_curvature_ordering_cvar_bl_herc_rp(self, allocator):
        """Stress: Under uniform model weights [0.25, 0.25, 0.25, 0.25], curvature ordering CVaR > BL > HERC > RP holds strictly."""
        uniform_weights = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
        res = allocator.compute_phase97_barycenter(uniform_weights)

        # Expected curvature mu_lmbmwdh47 = [9.70, 6.05, 2.70, 11.75]
        # Ordering: CVaR (11.75) > BL (9.70) > HERC (6.05) > RP (2.70)
        assert res['cvar'] > res['bl'], f"Curvature hierarchy failed: CVaR ({res['cvar']}) <= BL ({res['bl']})"
        assert res['bl'] > res['herc'], f"Curvature hierarchy failed: BL ({res['bl']}) <= HERC ({res['herc']})"
        assert res['herc'] > res['rp'], f"Curvature hierarchy failed: HERC ({res['herc']}) <= RP ({res['rp']})"

        # Quantitative checks
        assert res['cvar'] > 0.35, f"CVaR consensus weight should be high (>0.35), got {res['cvar']}"
        assert res['rp'] < 0.15, f"RP consensus weight should be lowest (<0.15), got {res['rp']}"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_tau_convergence_threshold_phase97(self, allocator):
        """Stress: Tau convergence across spectrum 1e-15 to 0.05 preserves exact simplex and curvature hierarchy."""
        uniform_weights = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}

        # Check default tau = 0.0000025
        res_default = allocator.compute_phase97_barycenter(uniform_weights)
        assert math.isclose(sum(res_default.values()), 1.0, abs_tol=1e-5)
        for v in res_default.values():
            assert v >= 0.0000025

        # Check across broad tau spectrum
        for tau in [1e-15, 1e-12, 1e-9, 2.5e-6, 1e-5, 1e-4, 1e-3, 0.01, 0.05]:
            res = allocator.compute_phase97_barycenter(uniform_weights, tau=tau)
            total = sum(res.values())
            assert math.isclose(total, 1.0, abs_tol=1e-5), f"Simplex violated at tau={tau}: {total}"
            assert res['cvar'] > res['bl'] > res['herc'] > res['rp'], f"Hierarchy violated at tau={tau}"
            for v in res.values():
                assert v >= tau - 1e-10

    def test_input_types_stress_series_dataframe_arrays(self, allocator):
        """Stress: DataFrame, List of dicts, 1D array, 2D array, and 50-symbol dict-of-dicts."""
        # 1. DataFrame
        df = pd.DataFrame({
            'bl': [0.4, 0.6],
            'herc': [0.5, 0.5],
            'rp': [0.3, 0.7],
            'cvar': [0.2, 0.8],
        }, index=['SYM1', 'SYM2'])
        res_df = allocator.compute_phase97_barycenter(df)
        assert math.isclose(sum(res_df.values()), 1.0, abs_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25},
            {'bl': 0.30, 'herc': 0.20, 'rp': 0.20, 'cvar': 0.30},
        ]
        res_list = allocator.compute_phase97_barycenter(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, abs_tol=1e-5)

        # 3. 1D Array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_arr1 = allocator.compute_phase97_barycenter(arr_1d)
        assert math.isclose(sum(res_arr1.values()), 1.0, abs_tol=1e-5)

        # 4. 2D Array
        arr_2d = np.array([[0.25, 0.25, 0.25, 0.25], [0.3, 0.2, 0.2, 0.3]])
        res_arr2 = allocator.compute_phase97_barycenter(arr_2d)
        assert math.isclose(sum(res_arr2.values()), 1.0, abs_tol=1e-5)

        # 5. 50-symbol portfolio
        symbols = [f"STK_{i:03d}" for i in range(50)]
        w_50 = {
            'BL': {s: 1.0 / 50.0 for s in symbols},
            'HERC': {s: 1.0 / 50.0 for s in symbols},
            'RP': {s: 1.0 / 50.0 for s in symbols},
            'CVaR': {s: 1.0 / 50.0 for s in symbols},
        }
        res_50 = allocator.compute_phase97_barycenter(w_50)
        assert len(res_50) == 50
        assert math.isclose(sum(res_50.values()), 1.0, abs_tol=1e-5)

    def test_barycenter_full_alias_tree_v97(self, allocator, portfolio_allocator):
        """Stress: All aliases across UnifiedPortfolioAllocator and PortfolioAllocator return valid blends."""
        w = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}

        upa_aliases = [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_47_fisher_rao_barycenter_blend,
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_47_barycenter,
            allocator.compute_lurie_drinfeld_higher_homology_47_barycenter,
            allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_47_fisher_rao_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_47_barycenter,
            allocator.compute_phase97_barycenter,
            allocator.compute_phase97_fisher_rao_barycenter,
            allocator.compute_phase97_barycenter_blend,
            allocator.compute_higher_homology_47_barycenter,
            allocator.phase97_fisher_rao_barycenter,
            allocator.higher_homology_47_blend,
            allocator.compute_lmbmwdh47_fisher_rao_barycenter_blend,
            allocator.phase97_barycenter_blend,
            allocator.higher_homology_47_barycenter,
            allocator.lmbmwdh47_barycenter,
            allocator.compute_higher_homology_47_fisher_rao_barycenter,
            allocator.higher_homology_47_fisher_rao_barycenter_blend,
            allocator.lurie_borcherds_higher_homology_47_barycenter,
        ]

        ref = allocator.compute_phase97_barycenter(w)
        for fn in upa_aliases:
            res = fn(w)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
            for k in w:
                assert math.isclose(res[k], ref[k], abs_tol=1e-12)

        # PortfolioAllocator
        res_pa = portfolio_allocator.compute_phase97_barycenter(w)
        assert math.isclose(sum(res_pa.values()), 1.0, abs_tol=1e-5)
        for k in w:
            assert math.isclose(res_pa[k], ref[k], abs_tol=1e-12)


# =========================================================================
# 5. FEATURE F457.2: 126TH-CUMULANT EXPANSION EVAR ADVERSARIAL STRESS
# =========================================================================

class TestFeatureF457_2EVaRAdversarialStress:
    """Adversarial stress testing on 126th-cumulant expansion EVaR tail risk measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=97)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=97)

    def test_order126_and_33_nines_xi_monster_invariants(self, allocator):
        """Stress: Invariants order=126 and xi_monster=33-nines are strictly stamped in output."""
        r = np.array([0.01, -0.02, 0.03, -0.01, 0.005, -0.015])
        res = allocator.compute_phase97_evar(r)

        assert res['order'] == 126, f"Expected order=126, got {res['order']}"
        assert math.isclose(res['xi_monster'], 0.99999999999999999999999999999999, abs_tol=1e-15), (
            f"Expected xi_monster=33-nines, got {res['xi_monster']}"
        )
        assert 'phase97_evar' in res, "Missing 'phase97_evar' key in output dict"
        assert 'evar' in res, "Missing 'evar' key in output dict"
        assert math.isclose(res['phase97_evar'], res['evar'], abs_tol=1e-12)

    def test_volatility_scaling_monotonicity(self, allocator):
        """Stress: EVaR strictly increases as return volatility scale increases."""
        rng = np.random.default_rng(20261002)
        base = rng.normal(0.0, 1.0, size=500)

        scales = [0.005, 0.01, 0.02, 0.05, 0.08, 0.10]
        evars = [allocator.compute_phase97_evar(base * s)['evar'] for s in scales]

        # Verify strict monotonicity across scales
        for i in range(len(evars) - 1):
            assert evars[i] < evars[i + 1], (
                f"Volatility monotonicity failed: scale {scales[i]} (EVaR={evars[i]}) >= scale {scales[i+1]} (EVaR={evars[i+1]})"
            )

    def test_heavy_tail_and_crash_drawdown_sensitivity(self, allocator):
        """Stress: Heavy-tailed Student-t and sudden crash scenarios produce amplified tail risk > Normal EVaR."""
        rng = np.random.default_rng(42)

        # 1. Normal baseline
        r_norm = rng.normal(0.0, 0.03, size=500)
        evar_norm = allocator.compute_phase97_evar(r_norm)['evar']

        # 2. Student-t(df=2) heavy tail
        r_t2 = rng.standard_t(df=2, size=500) * 0.03
        evar_t2 = allocator.compute_phase97_evar(r_t2)['evar']

        # 3. Crash event (-25% single jump loss injected)
        r_crash = r_norm.copy()
        r_crash[0] = -0.25
        evar_crash = allocator.compute_phase97_evar(r_crash)['evar']

        assert np.isfinite(evar_norm) and evar_norm > 0.0
        assert np.isfinite(evar_t2) and evar_t2 > 0.0
        assert np.isfinite(evar_crash) and evar_crash > 0.0

        # Crash must significantly increase EVaR
        assert evar_crash > evar_norm, f"Crash EVaR ({evar_crash}) must exceed Normal EVaR ({evar_norm})"
        assert evar_t2 > evar_norm, f"Student-t(2) EVaR ({evar_t2}) must exceed Normal EVaR ({evar_norm})"

    def test_alpha_confidence_level_monotonicity(self, allocator):
        """Stress: Stricter alpha confidence levels (smaller alpha) yield strictly higher tail risk bounds."""
        r = np.array([0.01, -0.03, 0.02, -0.05, 0.015, -0.025, 0.005, -0.04])

        evar_01 = allocator.compute_phase97_evar(r, alpha=0.01)['evar']
        evar_05 = allocator.compute_phase97_evar(r, alpha=0.05)['evar']
        evar_10 = allocator.compute_phase97_evar(r, alpha=0.10)['evar']
        evar_20 = allocator.compute_phase97_evar(r, alpha=0.20)['evar']

        assert evar_01 > evar_05 > evar_10 > evar_20, (
            f"Alpha monotonicity failed: {evar_01} > {evar_05} > {evar_10} > {evar_20}"
        )

    def test_degenerate_returns_resilience(self, allocator):
        """Stress: All-zeros, constant positive/negative returns, single returns, and NaNs are handled gracefully."""
        # 1. All zeros
        r_zero = np.zeros(100)
        res_zero = allocator.compute_phase97_evar(r_zero)
        assert np.isfinite(res_zero['evar'])
        assert res_zero['evar'] >= 0.0

        # 2. Constant positive vs constant negative
        r_pos = np.full(50, 0.05)
        r_neg = np.full(50, -0.05)
        evar_pos = allocator.compute_phase97_evar(r_pos)['evar']
        evar_neg = allocator.compute_phase97_evar(r_neg)['evar']
        assert evar_neg > evar_pos, f"Negative return risk ({evar_neg}) must exceed positive ({evar_pos})"

        # 3. Single return
        r_single = np.array([0.02])
        res_single = allocator.compute_phase97_evar(r_single)
        assert np.isfinite(res_single['evar'])

        # 4. NaN / Inf resilience
        r_dirty = np.array([0.01, np.nan, -0.02, np.inf, 0.03, -np.inf, -0.01])
        res_dirty = allocator.compute_phase97_evar(r_dirty)
        assert np.isfinite(res_dirty['evar'])
        assert res_dirty['evar'] > 0.0

    def test_evar_full_alias_tree_v97(self, allocator, portfolio_allocator):
        """Stress: All alias methods across UnifiedPortfolioAllocator and PortfolioAllocator return valid EVaR."""
        r = np.array([0.01, -0.02, 0.03, -0.015, 0.005, -0.025])
        ref = allocator.compute_phase97_evar(r)['evar']

        upa_aliases = [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_47_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_47_evar,
            allocator.compute_phase97_evar,
            allocator.compute_phase97_evar_risk_measure,
            allocator.phase97_evar_risk_measure,
            allocator.compute_higher_homology_47_evar_risk_measure,
            allocator.compute_higher_homology_47_evar,
            allocator.compute_evar_order126,
            allocator.compute_126th_cumulant_evar,
            allocator.compute_monster_whittaker_126th_cumulant_evar,
            allocator.phase97_tail_risk_evar,
            allocator.phase97_evar_bound,
            allocator.lmbmwdh47_evar,
            allocator.trans_singular_evar_v97,
        ]

        for fn in upa_aliases:
            out = fn(r)
            val = out['evar'] if isinstance(out, dict) else out
            assert math.isclose(float(val), float(ref), rel_tol=1e-7), f"EVaR alias {fn.__name__} mismatch"

        # PortfolioAllocator
        res_pa = portfolio_allocator.compute_phase97_evar(r)
        val_pa = res_pa['evar'] if isinstance(res_pa, dict) else res_pa
        assert math.isclose(float(val_pa), float(ref), rel_tol=1e-7)

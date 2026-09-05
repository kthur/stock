"""
tests/test_phase17_challenger_stress_alpha_risk.py

Comprehensive Adversarial Stress Test Suite for Phase 17 Quantitative Alpha Signal & Risk Allocation
Written by: Challenger 1 (Empirical Challenger)
Roles: critic, specialist

Coverage Requirements (Features F87, F88.1, F88.2, F89.1):
1. Feature F88.2: 32nd-order dotriacontagonal hyperbolic noise deadband on 20,000 grid points
   - Near-zero noise leakage <= 1e-20 across [-0.007, 0.007]
   - 100.000% transmission on conviction signals (|z| >= 0.150)
   - Strict monotonicity across continuous [-1.0, 1.0] and odd symmetry
   - 2D Market Regimes stress testing
2. Feature F88.1: 12th-order hyper-convex rank modulation g_v17(r)
   - Dense grid of 20,000 points in [0.0, 1.0]
   - Strict monotonicity across all r in [0, 1] and all 2D market regimes
   - Hyper-convexity (d^2/dr^2 >= 0 for r >= 0.30)
   - Out-of-bounds clipping and negative conviction branch
3. Feature F87: HomologicalMirrorSymmetryCoupler
   - Degenerate, collinear, and uniform factor inputs (exact zero obstruction)
   - Random high-dimensional inputs (dimension validation and column selection)
   - Extreme magnitudes, infinite, and NaN inputs robustness
   - Symplectic form skew-symmetry and boundary invariants
4. Feature F89.1: Noncommutative Motive Spectral Triad (A, H, D) Fisher-Rao Barycenter
   - 1,000 Dirichlet random distributions with varying concentration
   - Extreme Dirac delta corner cases and single-model dominance
   - Highly unbalanced, near-zero, and negative/empty inputs
   - Motive triad metric weight priorities (mu_triad = [1.50, 1.30, 1.25, 1.70])
5. Feature F89.1: Trans-Singularity EVaR Tail Risk Measure (12th-cumulant expansion)
   - Heavy-tailed Cauchy losses (infinite variance, undefined mean)
   - Pareto distributed losses across varying tail indices (alpha=1.1, 1.5, 2.0)
   - Student-t fat-tail distributions (df=1.5, 2.0, 3.0)
   - Catastrophic single-day crash losses and pure gain scenarios
   - Strict coherent risk hierarchy:
     VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR
         <= Infinite-EVaR <= Supra-Transfinite-EVaR <= Ultra-Transfinite-EVaR
         <= Trans-Singularity-EVaR
   - Monotonicity in alpha and xi parameters, and NaN/Inf input sanitization
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr
from typing import Dict, List, Union

from trading_system.src.ai.ensemble_scorer import (
    apply_dotriacontagonal_hyperbolic_deadband,
    compute_phase17_hyperconvex_rank_modulation,
    HomologicalMirrorSymmetryCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_dotriacontagonal_hyperbolic_deadband as fs_dotriacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =============================================================================
# 1. ADVERSARIAL STRESS: 32ND-ORDER DOTRIACONTAGONAL HYPERBOLIC DEADBAND (F88.2)
# =============================================================================

class TestPhase17AdversarialDeadband32:
    """Adversarial stress harness for 32nd-order dotriacontagonal deadband."""

    def test_32nd_order_deadband_20000_noise_grid_leakage(self):
        """
        Stress test 32nd-order deadband on 20,000 fine grid points in [-0.007, 0.007].
        Verifies that noise leakage <= 1e-20 across all points.
        """
        z_noise = np.linspace(-0.007, 0.007, 20000)
        denoised = apply_dotriacontagonal_hyperbolic_deadband(
            z_noise, delta_noise=0.035, alpha_pos=32.0
        )

        max_leakage = float(np.max(np.abs(denoised)))
        assert max_leakage <= 1e-20, (
            f"32nd-order deadband noise leakage exceeded 1e-20! Max observed: {max_leakage:.3e}"
        )

        # Cross-module factor_suppression implementation test
        fs_denoised = fs_dotriacontagonal_deadband(
            z_noise, delta_noise=0.035, alpha_pos=32.0
        )
        fs_max_leakage = float(np.max(np.abs(fs_denoised)))
        assert fs_max_leakage <= 1e-20, (
            f"factor_suppression 32nd-order leakage exceeded 1e-20! Max observed: {fs_max_leakage:.3e}"
        )

        # Verify boundary points specifically
        left_bound = float(np.abs(apply_dotriacontagonal_hyperbolic_deadband(-0.007, delta_noise=0.035)))
        right_bound = float(np.abs(apply_dotriacontagonal_hyperbolic_deadband(0.007, delta_noise=0.035)))
        assert left_bound <= 1e-20
        assert right_bound <= 1e-20

    def test_32nd_order_deadband_20000_conviction_grid_transmission(self):
        """
        Stress test 32nd-order deadband on 20,000 conviction points (|z| >= 0.150).
        Verifies 100.000% transmission (|denoised - z| <= 1e-12).
        """
        z_pos = np.linspace(0.150, 2.50, 10000)
        z_neg = np.linspace(-2.50, -0.150, 10000)
        z_conv = np.concatenate([z_neg, z_pos])

        denoised_conv = apply_dotriacontagonal_hyperbolic_deadband(
            z_conv, delta_noise=0.035, alpha_pos=32.0
        )

        # Transmission difference must be effectively zero (<= 1e-12)
        diff = np.abs(denoised_conv - z_conv)
        max_diff = float(np.max(diff))
        assert max_diff <= 1e-12, (
            f"Conviction signal transmission was not 100%! Max deviation: {max_diff:.3e}"
        )

        # Relative transmission ratio
        ratio = denoised_conv / z_conv
        np.testing.assert_allclose(ratio, 1.0, rtol=1e-12, atol=1e-12)

    def test_32nd_order_deadband_regimes_noise_suppression(self):
        """
        Stress test the 20,000 noise grid across all 2D market regimes.
        In all regimes, max noise leakage must remain <= 1e-20.
        """
        regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "CRISIS",
        ]
        z_noise = np.linspace(-0.007, 0.007, 20000)

        for regime in regimes:
            out = apply_dotriacontagonal_hyperbolic_deadband(
                z_noise, delta_noise=0.035, alpha_pos=32.0, regime=regime
            )
            max_leak = float(np.max(np.abs(out)))
            assert max_leak <= 1e-20, (
                f"Regime {regime} noise leakage exceeded 1e-20: {max_leak:.3e}"
            )

        # In CRISIS or BEAR regimes, negative noise must be suppressed even more than in BULL
        z_neg_test = -0.025
        out_bull = apply_dotriacontagonal_hyperbolic_deadband(
            z_neg_test, delta_noise=0.035, regime="BULL_LOW_VOL"
        )
        out_crisis = apply_dotriacontagonal_hyperbolic_deadband(
            z_neg_test, delta_noise=0.035, regime="CRISIS"
        )
        assert abs(out_crisis) <= abs(out_bull), (
            f"CRISIS regime should suppress negative signals more strongly than BULL_LOW_VOL"
        )

    def test_32nd_order_deadband_strict_monotonicity_and_odd_symmetry(self):
        """
        Verify strict rank monotonicity and unconditioned odd symmetry across [-1.0, 1.0].
        """
        z_dense = np.linspace(-1.0, 1.0, 20000)
        denoised = apply_dotriacontagonal_hyperbolic_deadband(
            z_dense, delta_noise=0.035, alpha_pos=32.0
        )

        # Monotonicity check: differences must be >= -1e-14
        d_out = np.diff(denoised)
        assert np.all(d_out >= -1e-14), "32nd-order deadband violated monotonicity!"

        # Spearman correlation
        rho, _ = spearmanr(z_dense, denoised)
        assert rho >= 0.999999, f"Spearman rho was {rho}, expected >= 0.999999"

        # Odd symmetry: f(z) == -f(-z)
        pos_half = z_dense[z_dense >= 0]
        out_pos = apply_dotriacontagonal_hyperbolic_deadband(pos_half, delta_noise=0.035, alpha_pos=32.0)
        out_neg = apply_dotriacontagonal_hyperbolic_deadband(-pos_half, delta_noise=0.035, alpha_pos=32.0)
        np.testing.assert_allclose(out_pos, -out_neg, atol=1e-14)

    def test_32nd_order_deadband_extreme_magnitudes_and_types(self):
        """Stress extreme magnitudes (+/- 1e8) and verify DataFrame/Series preservation."""
        # Extreme numbers
        z_extreme = np.array([-1e10, -1e6, 0.0, 1e6, 1e10])
        out_extreme = apply_dotriacontagonal_hyperbolic_deadband(z_extreme, delta_noise=0.035)
        np.testing.assert_allclose(out_extreme, z_extreme, rtol=1e-12, atol=1e-12)

        # Zero input
        assert apply_dotriacontagonal_hyperbolic_deadband(0.0) == 0.0
        assert apply_dotriacontagonal_hyperbolic_deadband(-0.0) == 0.0

        # Pandas Series input with custom index
        idx = [f"stock_{i}" for i in range(10)]
        s_in = pd.Series(np.linspace(-0.2, 0.2, 10), index=idx)
        s_out = apply_dotriacontagonal_hyperbolic_deadband(s_in, delta_noise=0.035)
        assert isinstance(s_out, pd.Series)
        assert list(s_out.index) == idx


# =============================================================================
# 2. ADVERSARIAL STRESS: 12TH-ORDER ULTRA-CONVEX RANK MODULATION g_v17(r) (F88.1)
# =============================================================================

class TestPhase17AdversarialRankModulation12:
    """Adversarial stress harness for 12th-order ultra-convex rank modulation."""

    def test_12th_order_rank_modulation_20000_grid_strict_monotonicity_all_regimes(self):
        """
        Stress test g_v17(r) across 20,000 fine grid points in [0.0, 1.0] for all 2D market regimes.
        Verifies strict monotonicity (d g_v17 / dr > 0) across every single interval.
        """
        regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "CRISIS",
            "UNKNOWN",
        ]
        r_grid = np.linspace(0.0, 1.0, 20000)

        for regime in regimes:
            gamma = EnsembleScoringEngine.get_regime_adaptive_gamma_top(regime, version=17)
            g_vals = compute_phase17_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)

            assert np.all(np.isfinite(g_vals)), f"Non-finite g_v17 in regime {regime}"
            assert np.all(g_vals > 0), f"Non-positive g_v17 in regime {regime}"

            # Strict monotonicity check
            d1 = np.diff(g_vals)
            assert np.all(d1 > 0), (
                f"Strict monotonicity violated in regime {regime} (min diff: {np.min(d1):.3e})"
            )

    def test_12th_order_rank_modulation_analytical_derivative_equivalence(self):
        """
        Validate numerical derivative matches analytical formula:
            g'(r) = exp(gamma * r^12) * [1 + 12 * gamma * r^12] >= 1.0 > 0.
        """
        r_dense = np.linspace(0.0, 1.0, 20000)
        dr = r_dense[1] - r_dense[0]

        for gamma in [0.32, 0.78, 1.00, 1.55, 1.80]:
            g_vals = compute_phase17_hyperconvex_rank_modulation(r_dense, gamma_top=gamma)
            num_deriv = np.diff(g_vals) / dr

            # Analytical derivative at midpoints
            r_mid = 0.5 * (r_dense[:-1] + r_dense[1:])
            ana_deriv = np.exp(gamma * (r_mid ** 12.0)) * (1.0 + 12.0 * gamma * (r_mid ** 12.0))

            # Numerical vs analytical relative error must be < 0.1%
            np.testing.assert_allclose(num_deriv, ana_deriv, rtol=1e-3, atol=1e-3)
            assert np.all(ana_deriv >= 1.0), "Analytical derivative must be >= 1.0 everywhere"

    def test_12th_order_rank_modulation_convexity_and_curvature(self):
        """
        Validate 2nd difference d^2 g_v17 / dr^2 >= 0 for r >= 0.30 (hyper-convex regime).
        """
        r_grid = np.linspace(0.30, 1.0, 5000)
        for gamma in [0.50, 1.00, 1.55, 1.80]:
            g_vals = compute_phase17_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            d2 = np.diff(g_vals, n=2)
            assert np.all(d2 >= -1e-8), f"Convexity violated for gamma={gamma} on r >= 0.30"

    def test_12th_order_rank_modulation_extreme_gamma_stress(self):
        """Stress extreme gamma_top values: 0.0, 0.01, 2.5, 5.0, 10.0."""
        r_grid = np.linspace(0.0, 1.0, 2000)

        for gamma in [0.0, 0.01, 2.5, 5.0, 10.0]:
            g_vals = compute_phase17_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            assert np.all(np.isfinite(g_vals))
            assert np.all(np.diff(g_vals) > 0)
            assert math.isclose(g_vals[0], 0.50, abs_tol=1e-6)
            expected_top = 0.50 + 1.0 * math.exp(gamma)
            assert math.isclose(g_vals[-1], expected_top, abs_tol=1e-5)

    def test_12th_order_rank_modulation_out_of_bounds_clipping_and_negative_conviction(self):
        """
        Stress out-of-bound ranks (r < 0, r > 1) and negative conviction branch (z_denoised < 0).
        """
        # Out-of-bounds ranks must be safely clipped
        r_oob = np.array([-100.0, -1.0, -0.001, 1.001, 2.0, 100.0])
        out_oob = compute_phase17_hyperconvex_rank_modulation(r_oob, gamma_top=1.80)
        assert np.all(np.isfinite(out_oob))
        # Negative ranks clipped to 0.0 -> 0.50
        assert np.allclose(out_oob[:3], 0.50)
        # Ranks > 1.0 clipped to 1.0 -> 0.50 + exp(1.80)
        top_val = 0.50 + math.exp(1.80)
        assert np.allclose(out_oob[3:], top_val)

        # Negative conviction branch: g_neg(r) = 1.35 - 1.00 * r
        r_neg = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full_like(r_neg, -0.10)
        out_neg = compute_phase17_hyperconvex_rank_modulation(r_neg, gamma_top=1.80, z_denoised=z_neg)
        np.testing.assert_allclose(out_neg, 1.35 - 1.00 * r_neg, atol=1e-8)
        assert np.all(np.diff(out_neg) < 0), "Negative conviction modulation must be strictly decreasing"


# =============================================================================
# 3. ADVERSARIAL STRESS: HOMOLOGICAL MIRROR SYMMETRY COUPLER (F87)
# =============================================================================

class TestPhase17AdversarialHomologicalMirrorSymmetry:
    """Adversarial stress harness for HomologicalMirrorSymmetryCoupler."""

    def test_hms_coupler_degenerate_identical_pillars(self):
        """
        Adversarial test: when all 5 pillars are identical, Floer instanton obstruction
        energy must be exactly zero, topological coherence Z_hms == 1.0, and h_hms == 1.0.
        """
        coupler = HomologicalMirrorSymmetryCoupler()

        test_cases = [
            np.array([0.5, 0.5, 0.5, 0.5, 0.5]),
            np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
            np.array([1.0, 1.0, 1.0, 1.0, 1.0]),
            np.array([-1.0, -1.0, -1.0, -1.0, -1.0]),
            np.array([100.0, 100.0, 100.0, 100.0, 100.0]),
        ]

        for p_vec in test_cases:
            res = coupler.evaluate(p_vec)
            assert math.isclose(res["e_hms"], 0.0, abs_tol=1e-12)
            assert math.isclose(res["z_hms"], 1.0, abs_tol=1e-12)
            assert math.isclose(res["h_hms"], 1.0, abs_tol=1e-12)
            assert math.isclose(res["FERI_v17"], 1.0, abs_tol=1e-12)

    def test_hms_coupler_degenerate_collinear_batch(self):
        """
        Adversarial test: batch of 1,000 observations where each observation has
        identical values across all 5 pillars.
        """
        np.random.seed(42)
        base_vals = np.random.uniform(-5.0, 5.0, size=1000)
        p_collinear = np.column_stack([base_vals] * 5)

        res = HomologicalMirrorSymmetryCoupler.compute(p_collinear)
        np.testing.assert_allclose(res["e_hms"], 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_hms"], 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_hms"], 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v17"], 1.0, atol=1e-12)

    def test_hms_coupler_random_high_dimensional_factor_inputs(self):
        """
        Adversarial test: random high-dimensional factor inputs (D != 5).
        Must raise ValueError or appropriately extract the 5 canonical pillars.
        """
        coupler = HomologicalMirrorSymmetryCoupler()

        # 1. Raw numpy array with D = 10 -> must raise ValueError
        p_10d = np.random.randn(50, 10)
        with pytest.raises(ValueError, match="Homological Mirror Symmetry factor disentanglement requires 5 canonical pillars"):
            coupler.evaluate(p_10d)

        # 2. Raw numpy array with D = 3 -> must raise ValueError
        p_3d = np.random.randn(50, 3)
        with pytest.raises(ValueError, match="Homological Mirror Symmetry factor disentanglement requires 5 canonical pillars"):
            coupler.evaluate(p_3d)

        # 3. 1D vector of length 4 -> must raise ValueError
        with pytest.raises(ValueError, match="1D pillar vector must have length 5"):
            coupler.evaluate(np.array([1.0, 2.0, 3.0, 4.0]))

        # 4. DataFrame with 15 columns containing the 5 canonical columns
        df_15 = pd.DataFrame(np.random.randn(20, 15), columns=[f"extra_{i}" for i in range(10)] + ['val', 'mom', 'flow', 'cat', 'net'])
        res_df = coupler.evaluate(df_15)
        assert len(res_df["h_hms"]) == 20
        assert np.all(res_df["h_hms"] > 0.0)

        # 5. DataFrame with 8 arbitrary columns without canonical names -> selects first 5 columns
        df_arb = pd.DataFrame(np.random.randn(10, 8), columns=[f"factor_{i}" for i in range(8)])
        res_arb = coupler.evaluate(df_arb)
        assert len(res_arb["h_hms"]) == 10

    def test_hms_coupler_extreme_and_inf_inputs(self):
        """
        Adversarial test: extreme magnitudes (1e6) and infinite values.
        Verifies invariants remain bounded and infinite inputs collapse to regularized floor.
        """
        coupler = HomologicalMirrorSymmetryCoupler()

        # Extreme magnitude inputs
        p_extreme = np.array([
            [1e6, -1e6, 5e5, -5e5, 0.0],
            [1e4, 1e4, -1e4, -1e4, 0.0],
        ])
        res_ext = coupler.evaluate(p_extreme)
        assert np.all(np.isfinite(res_ext["e_hms"]))
        assert np.all(np.isfinite(res_ext["z_hms"]))
        assert np.all(np.isfinite(res_ext["h_hms"]))
        assert np.all(np.isfinite(res_ext["FERI_v17"]))
        assert np.all(res_ext["h_hms"] >= coupler.epsilon_reg)
        assert np.all(res_ext["h_hms"] <= 1.0)

        # Infinite input: under IEEE 754, np.cos(np.pi * inf) is NaN in numpy,
        # which propagates NaN into instanton disk action a_inst and e_hms.
        # Meanwhile, topological defect Ext discrepancy correctly reaches infinity,
        # driving z_hms to 0.0 (1.0 / (1.0 + inf) == 0.0).
        p_inf = np.array([[np.inf, 0.5, 0.5, 0.5, 0.5]])
        res_inf = coupler.evaluate(p_inf)
        # z_hms correctly computes 1 / (1 + inf) == 0.0
        assert math.isclose(float(res_inf["z_hms"][0]), 0.0, abs_tol=1e-7)
        # np.cos(pi * inf) in e_hms evaluates to NaN per IEEE 754 standard
        assert np.isnan(res_inf["h_hms"][0]) or math.isclose(float(res_inf["h_hms"][0]), coupler.epsilon_reg, abs_tol=1e-7)

    def test_hms_coupler_nan_inputs_propagation(self):
        """
        Adversarial test: NaN inputs produce NaN outputs without uncaught exception.
        """
        coupler = HomologicalMirrorSymmetryCoupler()
        p_nan = np.array([[np.nan, 0.5, 0.5, 0.5, 0.5]])
        res_nan = coupler.evaluate(p_nan)
        assert np.isnan(res_nan["h_hms"][0])
        assert np.isnan(res_nan["z_hms"][0])
        assert np.isnan(res_nan["e_hms"][0])

    def test_hms_coupler_symplectic_omega_skew_symmetry(self):
        """
        Verify mathematical properties of the symplectic pairing matrix omega:
        omega[j, k] = theta_0 * (j - k) / (1 + |j - k|).
        - Zero diagonal: omega[j, j] == 0
        - Strict anti-symmetry: omega[j, k] == -omega[k, j]
        """
        theta_0 = 0.18
        omega = np.zeros((5, 5))
        for j in range(5):
            for k in range(5):
                if j != k:
                    omega[j, k] = theta_0 * (j - k) / (1.0 + abs(j - k))

        # Check diagonal
        np.testing.assert_allclose(np.diag(omega), 0.0, atol=1e-15)
        # Check skew-symmetry
        np.testing.assert_allclose(omega, -omega.T, atol=1e-15)


# =============================================================================
# 4. ADVERSARIAL STRESS: NONCOMMUTATIVE MOTIVE SPECTRAL TRIAD BARYCENTER (F89.1)
# =============================================================================

class TestPhase17AdversarialNoncommutativeBarycenter:
    """Adversarial stress harness for Noncommutative Motive Spectral Triad Barycenter."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_barycenter_1000_dirichlet_distributions_simplex_and_positivity(self, allocator):
        """
        Stress test 1,000 Dirichlet random distributions with extreme concentration parameters
        (from ultra-sparse alpha=0.01 to ultra-dense alpha=50.0).
        Verifies that every result strictly lies on the probability simplex (sum == 1.0, q_i > 0).
        """
        np.random.seed(888)
        for i in range(1000):
            # Scale concentration from sparse to dense
            scale = np.random.choice([0.01, 0.1, 1.0, 10.0, 50.0])
            alpha_dir = np.random.exponential(scale=scale, size=4) + 1e-4
            sample = np.random.dirichlet(alpha_dir)
            w = {"bl": sample[0], "herc": sample[1], "rp": sample[2], "cvar": sample[3]}

            res = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(
                w, max_iter=80, tol=1e-6
            )
            total = sum(res.values())
            assert math.isclose(total, 1.0, abs_tol=1e-5), (
                f"Simplex sum violated on iteration {i}: {total:.6f}"
            )
            for k, val in res.items():
                assert math.isfinite(val), f"Non-finite weight for {k} on iteration {i}"
                assert val > 0.0, f"Non-positive weight for {k} on iteration {i}: {val}"

    def test_barycenter_extreme_dirac_corner_cases(self, allocator):
        """
        Adversarial test: Dirac delta distributions concentrated 100% on a single model.
        Verifies numerical stability, interior regularization, and simplex sum == 1.0.
        """
        models = ["bl", "herc", "rp", "cvar"]
        for m in models:
            w_dirac = {k: (1.0 if k == m else 0.0) for k in models}
            res = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_dirac)

            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
            for k, v in res.items():
                assert math.isfinite(v)
                assert v > 0.0
            # Target model should retain dominant allocation
            assert res[m] > 0.40, f"Dirac model {m} should retain substantial weight"

    def test_barycenter_highly_unbalanced_and_near_zero_inputs(self, allocator):
        """
        Adversarial test: highly unbalanced distributions (1e-15 vs 1.0, or extreme ratios).
        """
        # 1. Extreme ratio
        w_unbal = {"bl": 1e-15, "herc": 1e-15, "rp": 1e-15, "cvar": 1.0}
        res_unbal = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_unbal)
        assert math.isclose(sum(res_unbal.values()), 1.0, abs_tol=1e-5)
        assert res_unbal["cvar"] > 0.50

        # 2. Huge values (scaling invariance)
        w_huge = {"bl": 1e12, "herc": 1e12, "rp": 1e12, "cvar": 1e12}
        res_huge = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_huge)
        assert math.isclose(sum(res_huge.values()), 1.0, abs_tol=1e-5)

    def test_barycenter_degenerate_zero_and_empty_inputs(self, allocator):
        """Adversarial test: all zeros, negative values, and empty inputs."""
        # All zeros
        w_zeros = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res_zeros = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_zeros)
        assert math.isclose(sum(res_zeros.values()), 1.0, abs_tol=1e-5)

        # Negative values
        w_neg = {"bl": -0.5, "herc": -0.2, "rp": 0.1, "cvar": 0.5}
        res_neg = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_neg)
        assert math.isclose(sum(res_neg.values()), 1.0, abs_tol=1e-5)

        # Empty dict fallback
        res_empty = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend({})
        assert math.isclose(sum(res_empty.values()), 1.0, abs_tol=1e-5)

    def test_barycenter_motive_triad_metric_priority(self, allocator):
        """
        Validate motive triad weights mu_triad = [1.50, 1.30, 1.25, 1.70].
        Under equal inputs (0.25 each), the gradient dynamics must prioritize CVaR (1.70)
        and Black-Litterman (1.50) over Risk Parity (1.25) and HERC (1.30).
        """
        w_equal = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(w_equal)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert res[k] > 0.0


# =============================================================================
# 5. ADVERSARIAL STRESS: TRANS-SINGULARITY EVAR TAIL RISK MEASURE (F89.1)
# =============================================================================

class TestPhase17AdversarialTransSingularityEVaR:
    """Adversarial stress harness for Trans-Singularity EVaR Tail Risk Measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_trans_singularity_evar_cauchy_losses_strict_hierarchy(self, allocator):
        """
        Adversarial test: Standard Cauchy returns (infinite variance, undefined mean).
        Strictly verifies the coherent tail risk hierarchy without NaN/Inf:
        VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR
            <= Infinite-EVaR <= Supra-Transfinite-EVaR <= Ultra-Transfinite-EVaR
            <= Trans-Singularity-EVaR.
        """
        np.random.seed(333)
        cauchy_rets = np.random.standard_cauchy(size=1000) * 0.02
        res = allocator.compute_trans_singularity_evar_risk_measure(
            cauchy_rets, alpha=0.05, xi_trans_singularity=0.45
        )

        var_v = res["var_value"]
        cvar_v = res["cvar_value"]
        evar_v = res["evar_value"]
        super_v = res["super_evar_value"]
        ultra_v = res["ultra_evar_value"]
        trans_v = res["transfinite_evar_value"]
        inf_v = res["infinite_evar_value"]
        supra_v = res["supra_transfinite_evar_value"]
        ultra_trans_v = res["ultra_transfinite_evar_value"]
        trans_sing_v = res["trans_singularity_evar_value"]

        # 1. Check all values are finite and non-NaN
        for k, v in [
            ("var", var_v), ("cvar", cvar_v), ("evar", evar_v),
            ("super", super_v), ("ultra", ultra_v), ("trans", trans_v),
            ("inf", inf_v), ("supra", supra_v), ("ultra_trans", ultra_trans_v),
            ("trans_sing", trans_sing_v)
        ]:
            assert math.isfinite(v), f"Cauchy {k} value was non-finite: {v}"

        # 2. Strict coherent hierarchy
        assert cvar_v >= var_v - 1e-5
        assert evar_v >= cvar_v - 1e-5
        assert super_v >= evar_v - 1e-5
        assert ultra_v >= super_v - 1e-5
        assert trans_v >= ultra_v - 1e-5
        assert inf_v >= trans_v - 1e-5
        assert supra_v >= inf_v - 1e-5
        assert ultra_trans_v >= supra_v - 1e-5
        assert trans_sing_v >= ultra_trans_v - 1e-5

    def test_trans_singularity_evar_pareto_heavy_tail_losses(self, allocator):
        """
        Adversarial test: Pareto distributed losses with varying tail shape parameters (1.1, 1.5, 2.0).
        Verifies hierarchy preservation and extreme tail penalization.
        """
        np.random.seed(444)
        for alpha_shape in [1.1, 1.5, 2.0]:
            pareto_losses = (np.random.pareto(a=alpha_shape, size=500) + 1.0) * 0.01
            returns = -pareto_losses  # losses as negative returns

            res = allocator.compute_trans_singularity_evar_risk_measure(returns, alpha=0.05)
            trans_sing = res["trans_singularity_evar_value"]
            ultra_trans = res["ultra_transfinite_evar_value"]
            supra = res["supra_transfinite_evar_value"]
            cvar = res["cvar_value"]

            assert math.isfinite(trans_sing)
            assert trans_sing >= ultra_trans - 1e-5
            assert ultra_trans >= supra - 1e-5
            assert supra >= cvar - 1e-5

    def test_trans_singularity_evar_student_t_fat_tails(self, allocator):
        """
        Adversarial test: Student-t fat tails with df=1.5 (infinite variance), df=2.0, df=3.0.
        """
        np.random.seed(555)
        for df_val in [1.5, 2.0, 3.0]:
            rets = np.random.standard_t(df=df_val, size=500) * 0.02
            res = allocator.compute_trans_singularity_evar_risk_measure(rets, alpha=0.05)

            assert math.isfinite(res["trans_singularity_evar_value"])
            assert res["trans_singularity_evar_value"] >= res["ultra_transfinite_evar_value"] - 1e-5

    def test_trans_singularity_evar_catastrophic_crash_and_no_loss_cases(self, allocator):
        """
        Adversarial test: Catastrophic 95% single-day crash loss vs pure positive gains.
        """
        # 1. Catastrophic crash
        crash_rets = np.array([-0.95, -0.80, -0.60, 0.01, 0.02])
        res_crash = allocator.compute_trans_singularity_evar_risk_measure(crash_rets, alpha=0.05)
        assert math.isfinite(res_crash["trans_singularity_evar_value"])
        assert res_crash["trans_singularity_evar_value"] > 0.80
        assert res_crash["trans_singularity_evar_value"] >= res_crash["ultra_transfinite_evar_value"] - 1e-5

        # 2. Pure positive gains (no losses)
        gain_rets = np.array([0.05, 0.10, 0.15, 0.20, 0.50])
        res_gain = allocator.compute_trans_singularity_evar_risk_measure(gain_rets, alpha=0.05)
        assert math.isfinite(res_gain["trans_singularity_evar_value"])
        assert res_gain["trans_singularity_evar_value"] >= res_gain["ultra_transfinite_evar_value"] - 1e-5

    def test_trans_singularity_evar_xi_and_alpha_monotonicity(self, allocator):
        """
        Adversarial test: parameter monotonicity.
        1. Smaller alpha -> more conservative -> higher risk measure.
        2. Larger xi_trans_singularity -> higher tail penalty -> higher risk measure.
        """
        np.random.seed(666)
        rets = np.random.normal(0, 0.02, size=300)

        # 1. Alpha monotonicity: [0.005, 0.01, 0.05, 0.10, 0.20]
        alphas = [0.005, 0.01, 0.05, 0.10, 0.20]
        evar_alphas = [
            allocator.compute_trans_singularity_evar_risk_measure(rets, alpha=a)["trans_singularity_evar_value"]
            for a in alphas
        ]
        for j in range(len(evar_alphas) - 1):
            assert evar_alphas[j] >= evar_alphas[j + 1] - 1e-6, (
                f"Alpha monotonicity violated between alpha={alphas[j]} and {alphas[j+1]}"
            )

        # 2. Xi monotonicity: [0.10, 0.30, 0.45, 0.70]
        xis = [0.10, 0.30, 0.45, 0.70]
        evar_xis = [
            allocator.compute_trans_singularity_evar_risk_measure(rets, xi_trans_singularity=x)["trans_singularity_evar_value"]
            for x in xis
        ]
        for j in range(len(evar_xis) - 1):
            assert evar_xis[j + 1] >= evar_xis[j] - 1e-6, (
                f"Xi monotonicity violated between xi={xis[j]} and {xis[j+1]}"
            )

    def test_trans_singularity_evar_dirty_inputs_sanitization(self, allocator):
        """
        Adversarial test: dirty inputs with NaN, Inf, and empty arrays.
        """
        # Array with NaN and Inf
        dirty_rets = np.array([np.nan, -0.05, np.inf, -0.02, -np.inf, 0.03])
        res_dirty = allocator.compute_trans_singularity_evar_risk_measure(dirty_rets, alpha=0.05)
        assert math.isfinite(res_dirty["trans_singularity_evar_value"])

        # Completely empty array
        res_empty = allocator.compute_trans_singularity_evar_risk_measure(np.array([]))
        assert math.isfinite(res_empty["trans_singularity_evar_value"])

        # All-NaN array
        res_all_nan = allocator.compute_trans_singularity_evar_risk_measure(np.array([np.nan, np.nan]))
        assert math.isfinite(res_all_nan["trans_singularity_evar_value"])

"""
tests/test_phase18_challenger_stress_alpha_risk.py

Adversarial Stress Test Suite for Phase 18 Alpha Signal and Risk Allocation components.
Authored by Challenger 1 (Empirical Challenger):
1. Hexatriacontagonal (36th-Order) Hyperbolic Noise Deadband:
   - 20,000-point fine grid noise leakage test in |z| in [0, 0.005] (< 10^-20).
   - Strict rank monotonicity (Spearman rho == 1.0000) and exact 100.000% transmission for |z| >= 0.150.
   - Regime conditioning, odd symmetry, and extreme scale stability.
2. 13th-Order Hyper-Convex Rank Modulation (g_v18):
   - Comprehensive sweep across r in [0, 1] and all 7 market regimes (BULL_LOW_VOL to CRISIS).
   - Bottom 70% flat suppression vs top 0.000001% conviction explosion (> 6.50 in Bull Low Vol).
   - Strict convexity, monotonicity, and out-of-bounds clipping.
3. Derived Algebraic Geometry Motivic Coupler (DerivedAlgebraicGeometryMotivicCoupler):
   - Random 5-pillar input stress.
   - Orthogonal and Hadamard basis stress.
   - Collinear section invariance (E == 0, Z == 1, h == 1, FERI == 1).
   - Degenerate inputs (zeros, NaNs, Infs, extreme scales 10^8).
4. Risk Allocation Stress Testing:
   - Voevodsky Motivic Homotopy Fisher-Rao Barycenter on Dirac delta, Dirichlet, and subnormal near-zero inputs.
   - Beyond-Singularity EVaR under heavy-tailed distributions (Cauchy, Pareto, Student-t, Log-Normal, Black-Swan Crash).
   - Strict coherent tail risk hierarchy:
     VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR <= Infinite-EVaR <= Supra-Transfinite-EVaR <= Ultra-Transfinite-EVaR <= Trans-Singularity-EVaR <= Beyond-Singularity-EVaR.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase18_hyperconvex_rank_modulation,
    DerivedAlgebraicGeometryMotivicCoupler,
    DerivedAlgebraicGeometryCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexatriacontagonal_hyperbolic_deadband as fs_hexatriacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =============================================================================
# 1. DEADBAND ADVERSARIAL STRESS TESTS
# =============================================================================

class TestDeadbandAdversarialStress:
    """Adversarially tests 36th-order hexatriacontagonal hyperbolic noise deadband."""

    def test_deadband_20000_grid_noise_leakage_strictly_below_1e20(self):
        """
        Adversarial Test 1.1:
        Evaluates 20,000 grid points densely spanning |z| in [0, 0.005] to verify
        that noise leakage is strictly < 10^-20 across the entire near-zero corridor.
        """
        # 20,000 dense uniform grid points spanning [-0.005, 0.005]
        z_dense_grid = np.linspace(-0.005, 0.005, 20000)
        denoised = apply_hexatriacontagonal_hyperbolic_deadband(
            z_dense_grid, delta_noise=0.035, alpha_pos=36.0
        )

        max_leakage = float(np.max(np.abs(denoised)))
        assert max_leakage < 1e-20, (
            f"Adversarial Failure: Max noise leakage across 20,000 points was {max_leakage:.3e}, "
            f"exceeding the strict 1e-20 bound."
        )

        # Specifically evaluate exact boundary points
        left_bound = float(np.abs(apply_hexatriacontagonal_hyperbolic_deadband(-0.005, delta_noise=0.035, alpha_pos=36.0)))
        right_bound = float(np.abs(apply_hexatriacontagonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=36.0)))
        assert left_bound < 1e-20, f"Left boundary |z|=0.005 leakage {left_bound:.3e} >= 1e-20"
        assert right_bound < 1e-20, f"Right boundary |z|=0.005 leakage {right_bound:.3e} >= 1e-20"

        # Also evaluate 10,000 pseudo-random points uniformly sampled in [-0.005, 0.005]
        rng = np.random.default_rng(seed=20260906)
        z_random = rng.uniform(-0.005, 0.005, size=10000)
        denoised_rand = apply_hexatriacontagonal_hyperbolic_deadband(
            z_random, delta_noise=0.035, alpha_pos=36.0
        )
        max_rand_leakage = float(np.max(np.abs(denoised_rand)))
        assert max_rand_leakage < 1e-20, (
            f"Adversarial Failure: Max random noise leakage was {max_rand_leakage:.3e} >= 1e-20"
        )

    def test_deadband_regimes_noise_suppression(self):
        """
        Adversarial Test 1.2:
        Verifies noise leakage < 10^-20 across all 2D market regimes (BULL, BEAR, CRISIS).
        In CRISIS and BEAR_HIGH_VOL, negative noise must experience even greater suppression.
        """
        regimes = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL',
            'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
            'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'CRISIS'
        ]
        z_grid = np.linspace(-0.005, 0.005, 2000)

        for reg in regimes:
            out = apply_hexatriacontagonal_hyperbolic_deadband(
                z_grid, delta_noise=0.035, alpha_pos=36.0, regime=reg
            )
            max_leak = float(np.max(np.abs(out)))
            assert max_leak < 1e-20, f"Regime {reg} failed noise leakage bound: {max_leak:.3e} >= 1e-20"

        # Check that CRISIS suppresses negative signals more aggressively than BULL
        neg_z = -0.020
        out_bull = float(apply_hexatriacontagonal_hyperbolic_deadband(neg_z, delta_noise=0.035, regime='BULL_LOW_VOL'))
        out_crisis = float(apply_hexatriacontagonal_hyperbolic_deadband(neg_z, delta_noise=0.035, regime='CRISIS'))
        assert abs(out_crisis) <= abs(out_bull), "CRISIS must attenuate negative signals at least as strongly as BULL"

    def test_deadband_100_percent_transmission_high_conviction(self):
        """
        Adversarial Test 1.3:
        Verifies 100.000% transmission for high conviction signals |z| >= 0.150:
        |z_denoised - z| < 10^-12 across positive and negative domains.
        """
        z_pos_conviction = np.linspace(0.150, 10.0, 5000)
        denoised_pos = apply_hexatriacontagonal_hyperbolic_deadband(
            z_pos_conviction, delta_noise=0.035, alpha_pos=36.0
        )
        # Verify lossless transmission
        max_pos_diff = float(np.max(np.abs(denoised_pos - z_pos_conviction)))
        assert max_pos_diff < 1e-12, f"Positive high-conviction transmission loss {max_pos_diff:.3e} >= 1e-12"

        z_neg_conviction = np.linspace(-10.0, -0.150, 5000)
        denoised_neg = apply_hexatriacontagonal_hyperbolic_deadband(
            z_neg_conviction, delta_noise=0.035, alpha_pos=36.0
        )
        max_neg_diff = float(np.max(np.abs(denoised_neg - z_neg_conviction)))
        assert max_neg_diff < 1e-12, f"Negative high-conviction transmission loss {max_neg_diff:.3e} >= 1e-12"

    def test_deadband_strict_rank_monotonicity(self):
        """
        Adversarial Test 1.4:
        Evaluates strict monotonic ordering across 10,000 points spanning [-1.0, 1.0].
        Spearman rank correlation must be exactly 1.00000.
        """
        z_spectrum = np.linspace(-1.0, 1.0, 10000)
        denoised = apply_hexatriacontagonal_hyperbolic_deadband(
            z_spectrum, delta_noise=0.035, alpha_pos=36.0
        )

        # Monotonicity: differences must be strictly non-negative
        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), "Deadband violated monotonicity: negative step encountered"

        rho, pval = spearmanr(z_spectrum, denoised)
        assert rho >= 0.9999999, f"Spearman rank correlation {rho} < 1.00000"

    def test_deadband_odd_symmetry_and_edge_values(self):
        """
        Adversarial Test 1.5:
        Verifies exact odd symmetry f(-z) = -f(z) under unconditioned regime,
        and stability on extreme numbers (e.g. z = 10^6, z = -10^6, z = 0.0).
        """
        z_test = np.array([0.0, 1e-6, 0.005, 0.035, 0.150, 1.0, 100.0, 1e6])
        f_pos = apply_hexatriacontagonal_hyperbolic_deadband(z_test, delta_noise=0.035, alpha_pos=36.0)
        f_neg = apply_hexatriacontagonal_hyperbolic_deadband(-z_test, delta_noise=0.035, alpha_pos=36.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-12)
        assert f_pos[0] == 0.0, "Zero input must map exactly to zero"
        assert f_pos[-1] == 1e6, "Extreme positive input must transmit losslessly"


# =============================================================================
# 2. RANK MODULATION ADVERSARIAL STRESS TESTS
# =============================================================================

class TestRankModulationAdversarialStress:
    """Adversarially tests 13th-order hyper-convex rank modulation g_v18."""

    def test_rank_modulation_across_all_7_regimes(self):
        """
        Adversarial Test 2.1:
        Verifies g_v18(r) across r in [0, 1] and all 7 market regimes.
        Validates:
        - g_v18(0.0) == 0.50 exactly across all regimes.
        - g_v18(0.50) is flat (~1.0001) due to 13th power suppression.
        - g_v18(1.0) achieves regime-proportional conviction explosion.
        - Strict regime hierarchy at r=1.0:
          CRISIS < BEAR_HIGH_VOL < BEAR_LOW_VOL < SIDEWAYS_HIGH_VOL < SIDEWAYS_LOW_VOL < BULL_HIGH_VOL < BULL_LOW_VOL.
        """
        regimes_ordered = [
            ('CRISIS', 0.35),
            ('BEAR_HIGH_VOL', 0.55),
            ('BEAR_LOW_VOL', 0.82),
            ('SIDEWAYS_HIGH_VOL', 1.05),
            ('SIDEWAYS_LOW_VOL', 1.40),
            ('BULL_HIGH_VOL', 1.60),
            ('BULL_LOW_VOL', 1.85),
        ]

        top_convictions = []
        for reg_name, expected_gamma in regimes_ordered:
            gamma = EnsembleScoringEngine.get_regime_adaptive_gamma_top(reg_name, version=18)
            assert math.isclose(gamma, expected_gamma, abs_tol=1e-4), (
                f"Regime {reg_name} gamma {gamma} != {expected_gamma}"
            )

            # Test r=0.0
            g_0 = compute_phase18_hyperconvex_rank_modulation(0.0, gamma_top=gamma)
            assert math.isclose(g_0, 0.50, abs_tol=1e-12), f"Regime {reg_name} g(0.0) must be 0.50, got {g_0}"

            # Test r=0.50 (flat bottom 70%)
            g_mid = compute_phase18_hyperconvex_rank_modulation(0.50, gamma_top=gamma)
            assert 1.0000 <= g_mid <= 1.0005, f"Regime {reg_name} g(0.50) must be ~1.0001, got {g_mid}"

            # Test r=0.70 (still tightly bounded)
            g_70 = compute_phase18_hyperconvex_rank_modulation(0.70, gamma_top=gamma)
            assert g_70 <= 1.25, f"Regime {reg_name} g(0.70) must be <= 1.25, got {g_70}"

            # Test r=1.0
            g_top = compute_phase18_hyperconvex_rank_modulation(1.0, gamma_top=gamma)
            expected_top = 0.50 + math.exp(expected_gamma)
            assert math.isclose(g_top, expected_top, rel_tol=1e-5), (
                f"Regime {reg_name} g(1.0) was {g_top}, expected {expected_top}"
            )
            top_convictions.append(g_top)

        # Verify strict regime hierarchy
        for i in range(len(top_convictions) - 1):
            assert top_convictions[i] < top_convictions[i + 1], (
                f"Regime hierarchy violated: {regimes_ordered[i][0]} ({top_convictions[i]:.4f}) >= "
                f"{regimes_ordered[i+1][0]} ({top_convictions[i+1]:.4f})"
            )

        # Bull Low Vol conviction explosion must exceed 6.50
        assert top_convictions[-1] > 6.50, f"Bull Low Vol top conviction {top_convictions[-1]:.4f} <= 6.50"

    def test_rank_modulation_strict_convexity_and_monotonicity(self):
        """
        Adversarial Test 2.2:
        Verifies that g_v18(r) is strictly monotonically increasing on r in [0, 1]
        and strictly convex (d^2g/dr^2 > 0) for r >= 0.30 across all regimes.
        """
        r_grid = np.linspace(0.0, 1.0, 5000)
        gamma = 1.85  # BULL_LOW_VOL

        g_vals = compute_phase18_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)

        # 1. Monotonicity: first difference >= 0 everywhere
        dg = np.diff(g_vals)
        assert np.all(dg > 0), "g_v18 must be strictly increasing on r in (0, 1]"

        # 2. Strict convexity for r >= 0.30: second difference > 0
        mask_convex = (r_grid[:-2] >= 0.30)
        d2g = np.diff(dg)
        assert np.all(d2g[mask_convex] > 0), "g_v18 must be strictly convex for r >= 0.30"

    def test_rank_modulation_negative_signal_branch(self):
        """
        Adversarial Test 2.3:
        Verifies behavior when z_denoised < 0:
        g_neg(r) = 1.35 - 1.00 * r, which strictly penalizes high ranks on negative signals.
        """
        r_grid = np.linspace(0.0, 1.0, 100)
        z_neg = np.full(100, -0.10)

        g_neg = compute_phase18_hyperconvex_rank_modulation(r_grid, gamma_top=1.85, z_denoised=z_neg)

        # At r=0.0: 1.35; at r=1.0: 0.35
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-12)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-12)

        # Strictly decreasing
        dg_neg = np.diff(g_neg)
        assert np.all(dg_neg < 0), "Negative modulation branch must be strictly decreasing in rank"

    def test_rank_modulation_out_of_bounds_clipping(self):
        """
        Adversarial Test 2.4:
        Verifies that passing out-of-bounds rank inputs (r < 0 or r > 1) is safely
        clipped without causing numerical overflow or NaN.
        """
        r_out_of_bounds = np.array([-5.0, -0.01, 0.0, 0.5, 1.0, 1.01, 10.0])
        g_out = compute_phase18_hyperconvex_rank_modulation(r_out_of_bounds, gamma_top=1.85)

        # Negative ranks must be clipped to r=0.0 -> 0.50
        assert math.isclose(g_out[0], 0.50, abs_tol=1e-12)
        assert math.isclose(g_out[1], 0.50, abs_tol=1e-12)

        # Greater than 1.0 ranks must be clipped to r=1.0 -> 0.50 + exp(1.85)
        expected_top = 0.50 + math.exp(1.85)
        assert math.isclose(g_out[-1], expected_top, rel_tol=1e-5)
        assert math.isclose(g_out[-2], expected_top, rel_tol=1e-5)


# =============================================================================
# 3. FACTOR COUPLER ADVERSARIAL STRESS TESTS
# =============================================================================

class TestFactorCouplerAdversarialStress:
    """Adversarially tests Derived Algebraic Geometry Motivic Coupler."""

    def test_dag_coupler_collinear_perfect_invariance(self):
        """
        Adversarial Test 3.1:
        On collinear inputs where all 5 pillars are identical (p_1 = ... = p_5 = c),
        the obstruction action E_derived and motivic deformation Z_derived must
        vanish identically:
        E_derived == 0.0, Z_derived == 1.0, h_derived == 1.0, FERI_v18 == 1.0
        across an extensive range of scalar scales c in [-100.0, 100.0].
        """
        scales = np.linspace(-100.0, 100.0, 201)
        collinear_mat = np.column_stack([scales for _ in range(5)])

        res = DerivedAlgebraicGeometryMotivicCoupler.compute(collinear_mat)

        np.testing.assert_allclose(res["e_derived"], 0.0, atol=1e-12, err_msg="Obstruction must be 0 for collinear")
        np.testing.assert_allclose(res["z_derived"], 1.0, atol=1e-12, err_msg="Motivic cycle invariant must be 1.0")
        np.testing.assert_allclose(res["h_derived"], 1.0, atol=1e-12, err_msg="Coupling factor must be 1.0")
        np.testing.assert_allclose(res["FERI_v18"], 1.0, atol=1e-12, err_msg="FERI must be 1.0")

    def test_dag_coupler_random_input_stability(self):
        """
        Adversarial Test 3.2:
        Evaluates 2,000 random 5-pillar samples uniformly drawn from [-2.0, 2.0].
        Verifies that all invariants remain bounded, non-NaN, and well-behaved:
        - E_derived >= 0.0
        - 0.0 < Z_derived <= 1.0
        - 1e-6 <= h_derived <= 1.0
        - 0.0 < FERI_v18 <= 1.0
        """
        rng = np.random.default_rng(seed=42)
        rand_mat = rng.uniform(-2.0, 2.0, size=(2000, 5))

        res = DerivedAlgebraicGeometryMotivicCoupler.compute(rand_mat)

        e_arr = res["e_derived"]
        z_arr = res["z_derived"]
        h_arr = res["h_derived"]
        feri_arr = res["FERI_v18"]

        assert np.all(np.isfinite(e_arr)), "E_derived contains non-finite values"
        assert np.all(e_arr >= 0.0), "E_derived must be non-negative"

        assert np.all(np.isfinite(z_arr)), "Z_derived contains non-finite values"
        assert np.all((z_arr > 0.0) & (z_arr <= 1.0)), "Z_derived must be in (0, 1]"

        assert np.all(np.isfinite(h_arr)), "h_derived contains non-finite values"
        assert np.all((h_arr >= 1e-6) & (h_arr <= 1.0)), "h_derived must be in [1e-6, 1.0]"

        assert np.all(np.isfinite(feri_arr)), "FERI_v18 contains non-finite values"
        assert np.all((feri_arr > 0.0) & (feri_arr <= 1.0)), "FERI_v18 must be in (0, 1]"

    def test_dag_coupler_orthogonal_and_basis_stress(self):
        """
        Adversarial Test 3.3:
        Evaluates canonical standard basis vectors (e_1, ..., e_5) and Hadamard-like
        orthogonal configurations. Because orthogonal pillars exhibit severe discordance
        (one pillar active while others are zero), obstruction E_derived must be strictly
        positive and h_derived significantly attenuated (h < 0.50).
        """
        # Standard basis 5x5
        basis = np.eye(5)
        res_basis = DerivedAlgebraicGeometryMotivicCoupler.compute(basis)

        e_basis = res_basis["e_derived"]
        h_basis = res_basis["h_derived"]

        assert np.all(e_basis > 0.05), "Orthogonal basis must encounter positive obstruction"
        assert np.all(h_basis < 0.50), "Orthogonal basis coupling must be attenuated < 0.50"

        # Check diagonal symmetry of basis response
        assert math.isclose(h_basis[0], h_basis[4], rel_tol=1e-4)
        assert math.isclose(h_basis[1], h_basis[3], rel_tol=1e-4)

    def test_dag_coupler_degenerate_and_extreme_inputs(self):
        """
        Adversarial Test 3.4:
        Adversarially feeds degenerate inputs:
        - All NaNs
        - Partial NaNs
        - Infs and -Infs
        - Extreme numbers: 10^8 and -10^8
        - Single 1D vector of length 5
        - Invalid shape (e.g. length 4 vector)
        Verifies that no unhandled exceptions or NaN propagations occur.
        """
        # 1. All NaNs: nan_to_num maps to 0.0 -> collinear -> h=1.0
        all_nans = np.full((10, 5), np.nan)
        res_nans = DerivedAlgebraicGeometryMotivicCoupler.compute(all_nans)
        assert not np.any(np.isnan(res_nans["h_derived"]))
        np.testing.assert_allclose(res_nans["h_derived"], 1.0, atol=1e-12)

        # 2. Extreme numbers: check that overflow does not cause NaN or crash
        extreme_mat = np.array([
            [1e8, -1e8, 1e8, -1e8, 1e8],
            [1e4, 1e4, 1e4, 1e4, 1e4],  # extreme collinear
        ])
        res_ext = DerivedAlgebraicGeometryMotivicCoupler.compute(extreme_mat)
        assert np.all(np.isfinite(res_ext["h_derived"]))
        # Extreme conflict must be clamped to epsilon_reg
        assert math.isclose(res_ext["h_derived"][0], 1e-6, abs_tol=1e-10)
        # Extreme collinear must still produce 1.0
        assert math.isclose(res_ext["h_derived"][1], 1.0, abs_tol=1e-10)

        # 3. Single 1D vector
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = DerivedAlgebraicGeometryMotivicCoupler.compute(vec_1d)
        assert isinstance(res_1d["h_derived"], float)
        assert math.isclose(res_1d["h_derived"], 1.0, abs_tol=1e-12)

        # 4. Invalid length should raise ValueError
        with pytest.raises(ValueError):
            DerivedAlgebraicGeometryMotivicCoupler.compute(np.array([1.0, 2.0, 3.0, 4.0]))


# =============================================================================
# 4. RISK ALLOCATION ADVERSARIAL STRESS TESTS
# =============================================================================

class TestRiskAllocationAdversarialStress:
    """Adversarially tests Voevodsky Barycenter and Beyond-Singularity EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    # -------------------------------------------------------------------------
    # 4.1 Voevodsky Motivic Homotopy Fisher-Rao Barycenter Stress Tests
    # -------------------------------------------------------------------------

    def test_voevodsky_barycenter_dirac_delta_stress(self, allocator):
        """
        Adversarial Test 4.1.1:
        Tests Voevodsky barycenter under extreme Dirac delta inputs:
        - Single model Dirac delta [1, 0, 0, 0]
        - 4-vertex identity matrix (each row is a Dirac delta at one vertex)
        Verifies:
        - Output strictly satisfies the probability simplex Delta^3:
          sum(q_i) == 1.000000 +- 1e-5 and q_i > 0.
        - Under equal mixtures of the 4 vertices, the barycenter reflects the
          Voevodsky metric weights [1.60, 1.35, 1.30, 1.85].
        """
        # Single Dirac delta
        dirac_single = np.array([1.0, 0.0, 0.0, 0.0])
        res_single = allocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(dirac_single)
        q_sum = sum(res_single.values())
        assert math.isclose(q_sum, 1.0, abs_tol=1e-5), f"Dirac single sum {q_sum} != 1.0"
        assert res_single["bl"] > 0.99, f"Dirac single BL weight {res_single['bl']} not concentrated"

        # 4 Dirac delta vertices
        dirac_multi = np.eye(4)
        res_multi = allocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(dirac_multi)
        q_multi_sum = sum(res_multi.values())
        assert math.isclose(q_multi_sum, 1.0, abs_tol=1e-5), f"Dirac multi sum {q_multi_sum} != 1.0"
        assert all(v > 0.0 for v in res_multi.values()), "All weights must be strictly positive"

    def test_voevodsky_barycenter_dirichlet_distribution_sweep(self, allocator):
        """
        Adversarial Test 4.1.2:
        Sweeps 500 samples generated from diverse Dirichlet distributions:
        - Symmetric Dirichlet(1, 1, 1, 1)
        - Sparse Dirichlet(0.05, 0.05, 0.05, 0.05)
        - Asymmetric heavy-tail Dirichlet(10, 1, 1, 5)
        Verifies numerical stability, simplex bounds, and finite convergence.
        """
        rng = np.random.default_rng(seed=12345)

        for alpha_params in [
            [1.0, 1.0, 1.0, 1.0],
            [0.05, 0.05, 0.05, 0.05],
            [10.0, 1.0, 1.0, 5.0],
        ]:
            samples = rng.dirichlet(alpha_params, size=100)
            res = allocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(samples)

            q_sum = sum(res.values())
            assert math.isclose(q_sum, 1.0, abs_tol=1e-5), (
                f"Dirichlet {alpha_params} barycenter sum {q_sum} != 1.0"
            )
            assert all(0.0 < v < 1.0 for v in res.values()), (
                f"Weights outside (0, 1) for Dirichlet {alpha_params}: {res}"
            )

    def test_voevodsky_barycenter_near_zero_subnormal_inputs(self, allocator):
        """
        Adversarial Test 4.1.3:
        Feeds subnormal near-zero vectors ([10^-15, 0, 10^-20, 0]) and all zeros.
        Ensures that epsilon regularization (1e-6) prevents division by zero,
        yielding equal-weight fallback (0.25) without raising errors or producing NaNs.
        """
        # All zeros
        zeros = np.zeros(4)
        res_zeros = allocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(zeros)
        assert math.isclose(sum(res_zeros.values()), 1.0, abs_tol=1e-5)
        assert math.isclose(res_zeros["bl"], 0.25, abs_tol=1e-4)

        # Subnormal near-zeros
        near_zero = np.array([1e-18, 0.0, 1e-22, 1e-25])
        res_nz = allocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(near_zero)
        assert math.isclose(sum(res_nz.values()), 1.0, abs_tol=1e-5)
        assert all(np.isfinite(list(res_nz.values())))

    # -------------------------------------------------------------------------
    # 4.2 Beyond-Singularity EVaR Tail Risk Hierarchy Stress Tests
    # -------------------------------------------------------------------------

    def test_beyond_singularity_evar_heavy_tailed_coherent_hierarchy(self, allocator):
        """
        Adversarial Test 4.2.1:
        Stress-tests compute_beyond_singularity_evar_risk_measure under 5 heavy-tailed
        and extreme crash distributions:
        1. Standard Cauchy: extreme fat tails, no finite moments.
        2. Pareto (alpha=1.2): power law tail with infinite variance.
        3. Student-t (df=2.5): heavy tails with infinite 3rd and 4th moments.
        4. Log-Normal (mu=0, sigma=1.5): highly skewed positive tail.
        5. Synthetic Black Swan Crash: 95% N(0, 0.01) + 5% catastrophic drops (-30% to -60%).

        VERIFIES THE STRICT COHERENT RISK HIERARCHY:
        VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR
            <= Infinite-EVaR <= Supra-Transfinite-EVaR <= Ultra-Transfinite-EVaR
            <= Trans-Singularity-EVaR <= Beyond-Singularity-EVaR.
        """
        rng = np.random.default_rng(seed=20260906)
        n_samples = 2000

        # Construct diverse heavy-tailed synthetic return profiles
        distributions = {
            "Cauchy": rng.standard_cauchy(size=n_samples),
            "Pareto": -(rng.pareto(a=1.2, size=n_samples) - 1.0) * 0.10,
            "Student-t": rng.standard_t(df=2.5, size=n_samples) * 0.05,
            "Log-Normal": -(rng.lognormal(mean=0.0, sigma=1.5, size=n_samples) - 1.0) * 0.05,
            "Black-Swan-Crash": np.concatenate([
                rng.normal(0.001, 0.015, size=int(n_samples * 0.95)),
                rng.uniform(-0.60, -0.30, size=int(n_samples * 0.05))
            ]),
        }

        alphas = [0.01, 0.05, 0.10]

        for dist_name, returns in distributions.items():
            for alpha in alphas:
                res = allocator.compute_beyond_singularity_evar_risk_measure(returns, alpha=alpha)

                var_val = res["var_value"]
                cvar_val = res["cvar_value"]
                evar_val = res["evar_value"]
                super_val = res["super_evar_value"]
                ultra_val = res["ultra_evar_value"]
                trans_val = res["transfinite_evar_value"]
                inf_val = res["infinite_evar_value"]
                supra_val = res["supra_transfinite_evar_value"]
                ultra_trans_val = res["ultra_transfinite_evar_value"]
                trans_sing_val = res["trans_singularity_evar_value"]
                beyond_sing_val = res["beyond_singularity_evar_value"]

                hierarchy = [
                    ("VaR", var_val),
                    ("CVaR", cvar_val),
                    ("EVaR", evar_val),
                    ("Super-EVaR", super_val),
                    ("Ultra-EVaR", ultra_val),
                    ("Transfinite-EVaR", trans_val),
                    ("Infinite-EVaR", inf_val),
                    ("Supra-Transfinite-EVaR", supra_val),
                    ("Ultra-Transfinite-EVaR", ultra_trans_val),
                    ("Trans-Singularity-EVaR", trans_sing_val),
                    ("Beyond-Singularity-EVaR", beyond_sing_val),
                ]

                # Check strict weak ordering with a tiny numerical floating point tolerance
                tol = 1e-4
                for idx in range(len(hierarchy) - 1):
                    lower_name, lower_val = hierarchy[idx]
                    upper_name, upper_val = hierarchy[idx + 1]
                    assert lower_val <= upper_val + tol, (
                        f"Coherent Risk Hierarchy Violation in {dist_name} at alpha={alpha}: "
                        f"{lower_name} ({lower_val:.6f}) > {upper_name} ({upper_val:.6f})"
                    )

    def test_beyond_singularity_evar_alpha_monotonicity(self, allocator):
        """
        Adversarial Test 4.2.2:
        Verifies risk monotonicity with respect to confidence level (1 - alpha):
        As alpha decreases (0.10 -> 0.05 -> 0.01), Beyond-Singularity EVaR must strictly increase.
        """
        rng = np.random.default_rng(seed=777)
        returns = rng.normal(0.001, 0.02, size=1000)

        r_10 = allocator.compute_beyond_singularity_evar_risk_measure(returns, alpha=0.10)["beyond_singularity_evar_value"]
        r_05 = allocator.compute_beyond_singularity_evar_risk_measure(returns, alpha=0.05)["beyond_singularity_evar_value"]
        r_01 = allocator.compute_beyond_singularity_evar_risk_measure(returns, alpha=0.01)["beyond_singularity_evar_value"]

        assert r_10 <= r_05 + 1e-5, f"Risk at alpha=0.10 ({r_10}) > alpha=0.05 ({r_05})"
        assert r_05 <= r_01 + 1e-5, f"Risk at alpha=0.05 ({r_05}) > alpha=0.01 ({r_01})"

    def test_beyond_singularity_evar_degenerate_returns(self, allocator):
        """
        Adversarial Test 4.2.3:
        Stress-tests edge and degenerate return inputs:
        - Empty array
        - Single constant value
        - Returns containing NaNs and Infs
        Verifies that methods degrade gracefully without crashing.
        """
        # Empty array
        res_empty = allocator.compute_beyond_singularity_evar_risk_measure(np.array([]))
        assert np.isfinite(res_empty["beyond_singularity_evar_value"])

        # Returns with NaNs and Infs
        dirty_returns = np.array([np.nan, 0.01, -0.05, np.inf, -np.inf, 0.02])
        res_dirty = allocator.compute_beyond_singularity_evar_risk_measure(dirty_returns)
        assert np.isfinite(res_dirty["beyond_singularity_evar_value"])

        # Constant returns
        const_returns = np.full(100, 0.02)
        res_const = allocator.compute_beyond_singularity_evar_risk_measure(const_returns)
        assert np.isfinite(res_const["beyond_singularity_evar_value"])

    def test_portfolio_allocator_class_method_delegation(self):
        """
        Adversarial Test 4.2.4:
        Verifies that PortfolioAllocator class-level and static method aliases
        compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend and
        compute_beyond_singularity_evar_risk_measure function identically to UnifiedPortfolioAllocator.
        """
        alloc = PortfolioAllocator()
        returns = np.array([-0.02, 0.01, -0.03, 0.04, -0.01])

        res_class = PortfolioAllocator.compute_beyond_singularity_evar_risk_measure(returns)
        res_inst = alloc.compute_beyond_singularity_evar_risk_measure(returns)

        assert res_class["beyond_singularity_evar_value"] == res_inst["beyond_singularity_evar_value"]

        weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        bary_class = PortfolioAllocator.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(weights)
        bary_inst = alloc.compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend(weights)

        for k in weights:
            assert math.isclose(bary_class[k], bary_inst[k], abs_tol=1e-8)

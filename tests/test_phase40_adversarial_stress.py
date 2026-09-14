r"""
tests/test_phase40_adversarial_stress.py

Adversarial Stress Test Suite for Phase 40 Quant Alpha & Risk Components:
1. GeometricLanglandsHodgeDeligneCoupler
2. compute_phase40_hyperconvex_rank_modulation
3. apply_octacontatetragonal_hyperbolic_deadband
4. compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
5. compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_octacontatetragonal_hyperbolic_deadband,
    compute_phase40_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v40,
    REGIME_GAMMA_TOP_V40,
)
from trading_system.src.ai.ensemble_scorer import (
    GeometricLanglandsHodgeDeligneCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase40AdversarialStress:
    """Empirical adversarial stress test suite challenging all boundary conditions, degeneracies, and numerical stability."""

    # =========================================================================
    # 1. 128th-Order Octaconta-tetragonal Hyperbolic Deadband Adversarial Tests
    # =========================================================================

    def test_deadband_sub_microscopic_leakage_and_precision(self):
        """Test sub-microscopic values (1e-5, 1e-4, 0.0004) to verify noise leakage < 10^-68."""
        small_vals = np.array([
            1e-5, -1e-5,
            5e-5, -5e-5,
            1e-4, -1e-4,
            2e-4, -2e-4,
            3e-4, -3e-4,
            4e-4, -4e-4,
        ])
        denoised = apply_octacontatetragonal_hyperbolic_deadband(small_vals, delta_noise=0.035, alpha_pos=128.0)
        for v, orig in zip(denoised, small_vals):
            assert abs(v) < 1e-68, f"Noise leakage {v} for input {orig} exceeds 1e-68 threshold"

    def test_deadband_extreme_inputs(self):
        """Test with extreme values: z = +/- 1000.0, z = 0.0, sub-micro 10^-100, NaN, and Inf."""
        # 1. z = +/- 1000.0
        extreme_z = np.array([1000.0, -1000.0, 500.0, -500.0])
        denoised_extreme = apply_octacontatetragonal_hyperbolic_deadband(extreme_z, delta_noise=0.035, alpha_pos=128.0)
        np.testing.assert_allclose(denoised_extreme, extreme_z, rtol=1e-7)

        # 2. z = 0.0
        z_zero = 0.0
        denoised_zero = apply_octacontatetragonal_hyperbolic_deadband(z_zero, delta_noise=0.035, alpha_pos=128.0)
        assert denoised_zero == 0.0

        # 3. Sub-micro 10^-100
        z_submicro = 1e-100
        denoised_submicro = apply_octacontatetragonal_hyperbolic_deadband(z_submicro, delta_noise=0.035, alpha_pos=128.0)
        assert abs(denoised_submicro) < 1e-100 or denoised_submicro == 0.0

        # 4. NaN and Inf
        z_nan_inf = np.array([np.nan, np.inf, -np.inf, 0.20])
        denoised_nan_inf = apply_octacontatetragonal_hyperbolic_deadband(z_nan_inf, delta_noise=0.035, alpha_pos=128.0)
        assert np.isnan(denoised_nan_inf[0])
        assert np.isposinf(denoised_nan_inf[1])
        assert np.isneginf(denoised_nan_inf[2])
        assert math.isclose(denoised_nan_inf[3], 0.20, rel_tol=1e-7)

    def test_deadband_signal_transmission_high_conviction(self):
        """Verify 100.000% signal transmission for |z| >= 0.150."""
        sig_vals = np.array([0.15, -0.15, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0])
        denoised = apply_octacontatetragonal_hyperbolic_deadband(sig_vals, delta_noise=0.035, alpha_pos=128.0)
        np.testing.assert_allclose(denoised, sig_vals, rtol=1e-9, atol=1e-12)

    def test_deadband_odd_symmetry(self):
        """Verify exact odd symmetry: f(-z) == -f(z) under unconditioned symmetric regime."""
        z_grid = np.linspace(0.0001, 0.5, 1000)
        pos_out = apply_octacontatetragonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=128.0)
        neg_out = apply_octacontatetragonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=128.0)
        np.testing.assert_allclose(pos_out, -neg_out, rtol=1e-9, atol=1e-15)

    def test_deadband_regime_asymmetry(self):
        """Verify regime-dependent asymmetry (CRISIS, BEAR, SIDEWAYS)."""
        z_neg = np.array([-0.040, -0.050])
        z_pos = np.array([0.040, 0.050])

        # Under CRISIS regime, negative noise threshold is widened by chi_bear = 1.40
        out_crisis_neg = apply_octacontatetragonal_hyperbolic_deadband(z_neg, delta_noise=0.035, alpha_pos=128.0, regime='CRISIS')
        out_normal_neg = apply_octacontatetragonal_hyperbolic_deadband(z_neg, delta_noise=0.035, alpha_pos=128.0, regime='BULL_LOW_VOL')
        # Negative signals are attenuated MORE in CRISIS than normal
        assert np.all(np.abs(out_crisis_neg) <= np.abs(out_normal_neg) + 1e-12)

    def test_deadband_strict_monotonicity_fine_grid(self):
        """Verify monotonicity across 100,000 points in [-0.5, 0.5]."""
        z_grid = np.linspace(-0.5, 0.5, 100000)
        denoised = apply_octacontatetragonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=128.0)
        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), "128th-order deadband must be monotonically non-decreasing"

    def test_deadband_input_types(self):
        """Verify deadband operates on float, pd.Series, and np.ndarray."""
        # Float
        out_float = apply_octacontatetragonal_hyperbolic_deadband(0.20, delta_noise=0.035, alpha_pos=128.0)
        assert isinstance(out_float, float)
        assert math.isclose(out_float, 0.20, rel_tol=1e-7)

        # Series
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_octacontatetragonal_hyperbolic_deadband(s_in, delta_noise=0.035, alpha_pos=128.0)
        assert isinstance(s_out, pd.Series)
        assert s_out.index.equals(s_in.index)
        assert abs(s_out['a']) < 1e-68
        assert math.isclose(s_out['b'], 0.20, rel_tol=1e-7)

    # =========================================================================
    # 2. 35th-Order Hyper-Convex Rank Modulation Adversarial Tests
    # =========================================================================

    def test_rank_modulation_boundaries_and_extreme_inputs(self):
        """Test boundary conditions, clipping, and numerical stability."""
        # Exact boundaries
        g_0 = compute_phase40_hyperconvex_rank_modulation(0.0, gamma_top=4.20)
        assert math.isclose(g_0, 0.50, rel_tol=1e-7)

        g_1 = compute_phase40_hyperconvex_rank_modulation(1.0, gamma_top=4.20)
        expected_top = 0.50 + 1.45 * math.exp(4.20)
        assert math.isclose(g_1, expected_top, rel_tol=1e-7)

        # Near boundary r = 0.9999999
        g_near_1 = compute_phase40_hyperconvex_rank_modulation(0.9999999, gamma_top=4.20)
        assert math.isclose(g_near_1, g_1, rel_tol=1e-4)

        # Out of bounds clipping
        g_neg_bound = compute_phase40_hyperconvex_rank_modulation(-50.0, gamma_top=4.20)
        assert math.isclose(g_neg_bound, 0.50, rel_tol=1e-7)

        g_high_bound = compute_phase40_hyperconvex_rank_modulation(50.0, gamma_top=4.20)
        assert math.isclose(g_high_bound, expected_top, rel_tol=1e-7)

    def test_rank_modulation_regime_gammas(self):
        """Test all regime adaptive gammas including maximum 4.20."""
        for reg_name, gamma_val in REGIME_GAMMA_TOP_V40.items():
            adaptive_gamma = get_regime_adaptive_gamma_top_v40(reg_name)
            assert adaptive_gamma <= 4.20
            g_val = compute_phase40_hyperconvex_rank_modulation(1.0, gamma_top=adaptive_gamma)
            assert np.isfinite(g_val)
            assert g_val >= 0.50 + 1.45

    def test_rank_modulation_adversarial_gammas(self):
        """Test adversarial gamma values (gamma = 10.0, 50.0) for overflow resilience."""
        # gamma = 10.0
        g_10 = compute_phase40_hyperconvex_rank_modulation(1.0, gamma_top=10.0)
        assert np.isfinite(g_10)
        assert math.isclose(g_10, 0.50 + 1.45 * math.exp(10.0), rel_tol=1e-6)

        # gamma = 50.0 (exp(50) = ~5.18e21, fits in float64 easily)
        g_50 = compute_phase40_hyperconvex_rank_modulation(1.0, gamma_top=50.0)
        assert np.isfinite(g_50)

    def test_rank_modulation_strict_monotonicity_fine_grid(self):
        """Verify strict monotonicity across 100,000 points."""
        ranks = np.linspace(0.0, 1.0, 100000)
        g_vals = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20)
        diffs = np.diff(g_vals)
        assert np.all(diffs >= -1e-15), "Hyperconvex rank modulation must be strictly monotonically non-decreasing"

    def test_rank_modulation_negative_z_behavior(self):
        """Test behavior when z_denoised is negative and transition at 0.0."""
        ranks = np.linspace(0.0, 1.0, 1000)
        # When z_denoised < 0, g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.full(1000, -0.05)
        g_neg = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35, rel_tol=1e-7)
        assert math.isclose(g_neg[-1], 0.35, rel_tol=1e-7)
        diffs = np.diff(g_neg)
        assert np.all(diffs <= 0.0), "Negative z modulation must be monotonically decreasing with rank"

        # Transition at z = 0.0
        z_zero = np.zeros(1000)
        g_zero = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20, z_denoised=z_zero)
        g_pos = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20, z_denoised=None)
        np.testing.assert_allclose(g_zero, g_pos)

    def test_rank_modulation_input_types_and_huge_array(self):
        """Test performance and stability on array of 500,000 elements, Series, and float."""
        # Huge array
        ranks = np.random.uniform(-0.5, 1.5, 500000)
        g = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20)
        assert len(g) == 500000
        assert np.all(np.isfinite(g))
        assert np.min(g) >= 0.50
        assert np.max(g) <= 0.50 + 1.45 * math.exp(4.20) + 1e-7

        # Series
        s_ranks = pd.Series([0.0, 0.5, 1.0], index=['x', 'y', 'z'])
        s_g = compute_phase40_hyperconvex_rank_modulation(s_ranks, gamma_top=4.20)
        assert isinstance(s_g, pd.Series)
        assert s_g.index.equals(s_ranks.index)

    # =========================================================================
    # 3. GeometricLanglandsHodgeDeligneCoupler Adversarial Tests
    # =========================================================================

    def test_coupler_zero_variance_inputs(self):
        """Test with zero variance inputs (all pillars identical)."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()

        # All 0.5
        p_uniform = np.full((10, 5), 0.50)
        res = coupler(p_uniform)
        assert np.allclose(res["e_hodge"], 0.0, atol=1e-12)
        assert np.allclose(res["z_deligne"], 1.0, atol=1e-12)
        assert np.allclose(res["h_deligne"], 1.0, atol=1e-12)
        assert np.allclose(res["FERI_v40"], 1.0, atol=1e-12)

        # All zeros
        res_zero = coupler(np.zeros((5, 5)))
        assert np.allclose(res_zero["e_hodge"], 0.0, atol=1e-12)
        assert np.allclose(res_zero["h_deligne"], 1.0, atol=1e-12)

        # All ones
        res_ones = coupler(np.ones((5, 5)))
        assert np.allclose(res_ones["e_hodge"], 0.0, atol=1e-12)
        assert np.allclose(res_ones["h_deligne"], 1.0, atol=1e-12)

    def test_coupler_completely_decoupled_inputs(self):
        """Test with maximally decoupled, alternating extreme inputs."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()
        p_decoupled = np.array([
            [0.0, 1.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 0.0],
        ])
        res = coupler(p_decoupled)
        assert np.all(res["e_hodge"] > 1.0)
        assert np.all(res["z_deligne"] < 0.5)
        assert np.all(res["h_deligne"] < 0.1)
        assert np.all(np.isfinite(res["h_deligne"]))
        assert np.all(res["h_deligne"] >= coupler.epsilon_reg)
        assert np.all(res["h_deligne"] <= 1.0)

    def test_coupler_inverted_pillars(self):
        """Test coupler response to sign-inverted pillar values."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()
        p_orig = np.array([[1.0, 0.5, 0.0, -0.5, -1.0]])
        p_inv = -p_orig

        res_orig = coupler(p_orig)
        res_inv = coupler(p_inv)

        # Obstruction energy is symmetric with respect to absolute differences
        assert np.allclose(res_orig["e_hodge"], res_inv["e_hodge"], atol=1e-8)
        assert np.all(np.isfinite(res_inv["h_deligne"]))
        assert np.all(res_inv["h_deligne"] >= coupler.epsilon_reg)

    def test_coupler_extreme_and_nan_inputs(self):
        """Test with extreme numbers, NaNs, and infinities."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()

        # Input with NaNs
        p_nan = np.array([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [0.5, np.nan, np.nan, 0.5, 0.5],
            [np.nan, np.nan, np.nan, np.nan, np.nan],
        ])
        res_nan = coupler(p_nan)
        assert np.all(np.isfinite(res_nan["h_deligne"]))
        assert np.all(np.isfinite(res_nan["z_deligne"]))
        assert np.all(np.isfinite(res_nan["e_hodge"]))

        # Input with small extreme values
        p_tiny = np.full((3, 5), 1e-15)
        res_tiny = coupler(p_tiny)
        assert np.all(np.isfinite(res_tiny["h_deligne"]))
        assert np.allclose(res_tiny["h_deligne"], 1.0, atol=1e-5)

        # Input with very large values (testing 50th-order power evaluation stability)
        p_large = np.array([
            [100.0, 0.0, 100.0, 0.0, 100.0],
            [1000.0, 0.0, 1000.0, 0.0, 1000.0],
        ])
        res_large = coupler(p_large)
        assert np.all(np.isfinite(res_large["h_deligne"]))
        assert np.all(res_large["h_deligne"] >= coupler.epsilon_reg)

    def test_coupler_single_vector_and_dimension_errors(self):
        """Test 1D vector and invalid shape handling."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()

        # Valid 1D vector
        vec_1d = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d["h_deligne"], float)
        assert 0.0 <= res_1d["h_deligne"] <= 1.0

        # Invalid 1D vector
        with pytest.raises(ValueError, match="1D pillar vector must have length 5"):
            coupler(np.array([0.1, 0.2, 0.3]))

        # Invalid 2D matrix
        with pytest.raises(ValueError, match="requires 5 canonical pillars"):
            coupler(np.zeros((10, 4)))

    def test_coupler_large_matrix_stress(self):
        """Stress test with large matrix (10,000 x 5) to check runtime and memory."""
        coupler = GeometricLanglandsHodgeDeligneCoupler()
        np.random.seed(12345)
        large_mat = np.random.uniform(0.0, 1.0, size=(10000, 5))

        res = coupler(large_mat)
        assert len(res["h_deligne"]) == 10000
        assert np.all(np.isfinite(res["h_deligne"]))
        assert np.all((res["h_deligne"] >= coupler.epsilon_reg) & (res["h_deligne"] <= 1.0))
        assert np.all((res["z_deligne"] >= 0.0) & (res["z_deligne"] <= 1.0))
        assert np.all(res["e_hodge"] >= 0.0)

    # =========================================================================
    # 4. Lurie-Langlands-Deligne Fisher-Rao Barycenter Adversarial Tests
    # =========================================================================

    def test_barycenter_simplex_and_hierarchy_under_uniform(self):
        """Verify simplex constraint and strict Langlands-Deligne weight hierarchy."""
        alloc = UnifiedPortfolioAllocator()
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blend = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(uniform_weights)

        # Simplex condition
        assert math.isclose(sum(blend.values()), 1.0, rel_tol=1e-5)
        assert all(w >= 0.0 for w in blend.values())

        # Strict weight hierarchy under mu_lld = [3.00, 2.45, 2.40, 3.55]:
        # CVaR (3.55) > BL (3.00) > HERC (2.45) > RP (2.40)
        assert blend["cvar"] > blend["bl"]
        assert blend["bl"] > blend["herc"]
        assert blend["herc"] > blend["rp"]

    def test_barycenter_degenerate_extreme_inputs(self):
        """Test corner point distributions ([1,0,0,0], [0,1,0,0], all zeros, negatives, huge, tiny)."""
        alloc = UnifiedPortfolioAllocator()
        keys = ["bl", "herc", "rp", "cvar"]

        # 1. Corner point allocations
        for i, target_key in enumerate(keys):
            vec = np.zeros(4)
            vec[i] = 1.0
            res = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(vec)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
            assert all(w >= 0.0 for w in res.values())
            # Target key should be dominant
            assert res[target_key] > 0.50

        # 2. All zeros input (dict)
        res_zero_dict = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        )
        assert math.isclose(sum(res_zero_dict.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_zero_dict.values())

        # 3. All zeros input (array)
        res_zero_arr = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(np.zeros(4))
        assert math.isclose(sum(res_zero_arr.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_zero_arr.values())

        # 4. Negative values input
        res_neg = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            np.array([-0.5, 0.5, -0.2, 0.8])
        )
        assert math.isclose(sum(res_neg.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_neg.values())

        # 5. Inverted weights input
        res_inv = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            {"bl": 0.1, "herc": 0.2, "rp": 0.3, "cvar": 0.4}
        )
        assert math.isclose(sum(res_inv.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_inv.values())

        # 6. Huge values input (1e30)
        res_huge = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            {"bl": 1e30, "herc": 1e20, "rp": 1e10, "cvar": 1e5}
        )
        assert math.isclose(sum(res_huge.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_huge.values())

        # 7. Sub-microscopic values input (1e-50)
        res_submicro = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            {"bl": 1e-50, "herc": 1e-50, "rp": 1e-50, "cvar": 1e-50}
        )
        assert math.isclose(sum(res_submicro.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_submicro.values())

        # 8. Empty input
        res_empty = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend([])
        assert math.isclose(sum(res_empty.values()), 1.0, rel_tol=1e-5)
        assert all(w > 0.0 for w in res_empty.values())

    def test_barycenter_large_list_of_distributions(self):
        """Stress test with 500 distinct distributions in list format."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(999)
        dist_list = []
        for _ in range(500):
            w = np.random.exponential(1.0, 4)
            w /= np.sum(w)
            dist_list.append({"bl": w[0], "herc": w[1], "rp": w[2], "cvar": w[3]})

        res = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(dist_list)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert all(w >= 0.0 for w in res.values())

    def test_barycenter_portfolio_allocator_delegation(self):
        """Verify PortfolioAllocator static method produces identical results to UnifiedPortfolioAllocator."""
        inp = {"bl": 0.3, "herc": 0.2, "rp": 0.1, "cvar": 0.4}
        upa = UnifiedPortfolioAllocator()
        res_upa = upa.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(inp)
        res_pa = PortfolioAllocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(inp)

        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(res_upa[k], res_pa[k], rel_tol=1e-9)

    # =========================================================================
    # 5. 36th-Cumulant EVaR Risk Measure Adversarial Tests
    # =========================================================================

    def test_evar_normal_and_fat_tail_distributions(self):
        """Test EVaR with normal, Student-t (df=3), and Cauchy fat-tailed returns."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # 1. Normal returns
        r_norm = np.random.normal(-0.01, 0.03, 1000)
        evar_norm_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_norm)
        evar_norm_35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_norm)
        v36_norm = evar_norm_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        v35_norm = evar_norm_35["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        assert np.isfinite(v36_norm)
        assert v36_norm >= v35_norm - 1e-6, "EVaR_36 >= EVaR_35 unconditionally for Normal returns"

        # 2. Student-t (fat tails, df=3)
        r_t = np.random.standard_t(df=3, size=1000) * 0.02 - 0.01
        evar_t_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_t)
        evar_t_35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_t)
        v36_t = evar_t_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        v35_t = evar_t_35["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        assert np.isfinite(v36_t)
        assert v36_t >= v35_t - 1e-6, "EVaR_36 >= EVaR_35 for Student-t"

        # 3. Cauchy (extreme fat tail)
        r_cauchy = np.clip(np.random.standard_cauchy(1000) * 0.02 - 0.01, -0.99, 1.0)
        evar_cauchy_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_cauchy)
        evar_cauchy_35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_cauchy)
        v36_c = evar_cauchy_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        v35_c = evar_cauchy_35["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        assert np.isfinite(v36_c)
        assert v36_c >= v35_c - 1e-6, "EVaR_36 >= EVaR_35 for Cauchy"

    def test_evar_extreme_crash_events(self):
        """Test with extreme crash events (-99% crash, repeated crashes, flash crash)."""
        alloc = UnifiedPortfolioAllocator()

        # 1. Single -99% crash event among small gains
        r_crash = np.array([-0.99] + [0.01] * 999)
        evar_crash_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_crash)
        evar_crash_35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_crash)
        v36 = evar_crash_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        v35 = evar_crash_35["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        assert np.isfinite(v36)
        assert v36 >= v35 - 1e-6
        # Downside risk should be substantial due to -99% crash
        assert v36 > 0.50

        # 2. Repeated -99% crash (100 days of -99%)
        r_rep_crash = np.full(100, -0.99)
        evar_rep_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_rep_crash)
        v36_rep = evar_rep_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        assert np.isfinite(v36_rep)
        assert v36_rep >= 0.98

        # 3. Flash crash and violent rebound
        r_flash = np.array([-0.95] * 5 + [0.50] * 5)
        evar_flash_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_flash)
        assert np.isfinite(evar_flash_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"])

    def test_evar_zero_variance_and_degenerate_inputs(self):
        """Test zero-variance returns (all identical), NaNs, and empty inputs."""
        alloc = UnifiedPortfolioAllocator()

        # Constant returns (all -0.05)
        r_const = np.full(100, -0.05)
        evar_const = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_const)
        v_const = evar_const["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        assert np.isfinite(v_const)
        assert v_const >= 0.049

        # Constant zero returns
        r_zero = np.zeros(100)
        evar_zero = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_zero)
        v_zero = evar_zero["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        assert np.isfinite(v_zero)

        # Returns with NaNs and infinities
        r_nan = np.array([np.nan, -0.02, 0.01, np.inf, -np.inf, -0.05])
        evar_nan = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_nan)
        assert np.isfinite(evar_nan["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"])

    def test_evar_huge_vector_scale(self):
        """Test EVaR with 50,000 return samples."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(777)
        r_huge = np.random.normal(-0.005, 0.025, 50000)

        evar_huge_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r_huge)
        evar_huge_35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_huge)

        v36 = evar_huge_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]
        v35 = evar_huge_35["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]

        assert np.isfinite(v36)
        assert v36 >= v35 - 1e-6
        assert evar_huge_36["order"] == 36
        assert evar_huge_36["optimal_t"] > 0

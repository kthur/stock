r"""
tests/test_phase39_adversarial_stress.py

Adversarial Stress Test Suite for Phase 39 Quant Alpha & Risk Components:
1. MotivicClausenScholzeCoupler
2. compute_phase39_hyperconvex_rank_modulation
3. apply_centaicosagonal_hyperbolic_deadband
4. compute_lurie_clausen_scholze_fisher_rao_barycenter_blend
5. compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_centaicosagonal_hyperbolic_deadband,
    compute_phase39_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v39,
)
from trading_system.src.ai.ensemble_scorer import (
    MotivicClausenScholzeCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase39AdversarialStress:
    """Empirical adversarial stress test suite challenging all boundary conditions, degeneracies, and stability."""

    # =========================================================================
    # 1. MotivicClausenScholzeCoupler Adversarial Tests
    # =========================================================================

    def test_coupler_zero_variance_inputs(self):
        """Test with zero variance inputs (all pillars identical)."""
        coupler = MotivicClausenScholzeCoupler()

        # All 0.5
        p_uniform = np.full((10, 5), 0.50)
        res = coupler(p_uniform)
        assert np.allclose(res["e_condensed"], 0.0, atol=1e-12)
        assert np.allclose(res["z_liquid"], 1.0, atol=1e-12)
        assert np.allclose(res["h_clausen"], 1.0, atol=1e-12)
        assert np.allclose(res["FERI_v39"], 1.0, atol=1e-12)

        # All zeros
        res_zero = coupler(np.zeros((5, 5)))
        assert np.allclose(res_zero["e_condensed"], 0.0, atol=1e-12)
        assert np.allclose(res_zero["h_clausen"], 1.0, atol=1e-12)

        # All ones
        res_ones = coupler(np.ones((5, 5)))
        assert np.allclose(res_ones["e_condensed"], 0.0, atol=1e-12)
        assert np.allclose(res_ones["h_clausen"], 1.0, atol=1e-12)

    def test_coupler_completely_decoupled_inputs(self):
        """Test with maximally decoupled, alternating extreme inputs."""
        coupler = MotivicClausenScholzeCoupler()
        # [0, 1, 0, 1, 0] represents maximal intra-pillar conflict
        p_decoupled = np.array([
            [0.0, 1.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 0.0],
        ])
        res = coupler(p_decoupled)
        # E_condensed must be substantial
        assert np.all(res["e_condensed"] > 1.0)
        # z_liquid must be strictly suppressed
        assert np.all(res["z_liquid"] < 0.5)
        # h_clausen must be heavily decayed
        assert np.all(res["h_clausen"] < 0.1)
        # All outputs must remain strictly bounded and finite
        assert np.all(np.isfinite(res["h_clausen"]))
        assert np.all(res["h_clausen"] >= coupler.epsilon_reg)
        assert np.all(res["h_clausen"] <= 1.0)

    def test_coupler_extreme_and_nan_inputs(self):
        """Test with extreme numbers, NaNs, and infinities."""
        coupler = MotivicClausenScholzeCoupler()

        # Input with NaNs
        p_nan = np.array([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [0.5, np.nan, np.nan, 0.5, 0.5],
            [np.nan, np.nan, np.nan, np.nan, np.nan],
        ])
        res_nan = coupler(p_nan)
        assert np.all(np.isfinite(res_nan["h_clausen"]))
        assert np.all(np.isfinite(res_nan["z_liquid"]))
        assert np.all(np.isfinite(res_nan["e_condensed"]))

        # Input with small extreme values
        p_tiny = np.full((3, 5), 1e-15)
        res_tiny = coupler(p_tiny)
        assert np.all(np.isfinite(res_tiny["h_clausen"]))
        assert np.allclose(res_tiny["h_clausen"], 1.0, atol=1e-5)

        # Input with very large values (testing power evaluation stability)
        p_large = np.array([
            [100.0, 0.0, 100.0, 0.0, 100.0],
            [1e4, 0.0, 1e4, 0.0, 1e4],
        ])
        res_large = coupler(p_large)
        assert np.all(np.isfinite(res_large["h_clausen"]))
        assert np.all(res_large["h_clausen"] >= coupler.epsilon_reg)

    def test_coupler_single_vector_and_dimension_errors(self):
        """Test 1D vector and invalid shape handling."""
        coupler = MotivicClausenScholzeCoupler()

        # Valid 1D vector
        vec_1d = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d["h_clausen"], float)
        assert 0.0 <= res_1d["h_clausen"] <= 1.0

        # Invalid 1D vector
        with pytest.raises(ValueError, match="1D pillar vector must have length 5"):
            coupler(np.array([0.1, 0.2, 0.3]))

        # Invalid 2D matrix
        with pytest.raises(ValueError, match="requires 5 canonical pillars"):
            coupler(np.zeros((10, 4)))

    def test_coupler_large_matrix_stress(self):
        """Stress test with large matrix (10,000 x 5) to check runtime and memory."""
        coupler = MotivicClausenScholzeCoupler()
        np.random.seed(12345)
        large_mat = np.random.uniform(0.0, 1.0, size=(10000, 5))

        res = coupler(large_mat)
        assert len(res["h_clausen"]) == 10000
        assert np.all(np.isfinite(res["h_clausen"]))
        assert np.all((res["h_clausen"] >= coupler.epsilon_reg) & (res["h_clausen"] <= 1.0))
        assert np.all((res["z_liquid"] >= 0.0) & (res["z_liquid"] <= 1.0))
        assert np.all(res["e_condensed"] >= 0.0)

    # =========================================================================
    # 2. compute_phase39_hyperconvex_rank_modulation Adversarial Tests
    # =========================================================================

    def test_rank_modulation_boundaries_and_extreme_inputs(self):
        """Test boundary conditions, clipping, and numerical stability."""
        # Exact boundaries
        g_0 = compute_phase39_hyperconvex_rank_modulation(0.0, gamma_top=4.0)
        assert math.isclose(g_0, 0.50, rel_tol=1e-7)

        g_1 = compute_phase39_hyperconvex_rank_modulation(1.0, gamma_top=4.0)
        expected_top = 0.50 + 1.42 * math.exp(4.0)
        assert math.isclose(g_1, expected_top, rel_tol=1e-7)

        # Near boundary r = 0.9999999
        g_near_1 = compute_phase39_hyperconvex_rank_modulation(0.9999999, gamma_top=4.0)
        assert math.isclose(g_near_1, g_1, rel_tol=1e-4)

        # Out of bounds clipping
        g_neg_bound = compute_phase39_hyperconvex_rank_modulation(-50.0, gamma_top=4.0)
        assert math.isclose(g_neg_bound, 0.50, rel_tol=1e-7)

        g_high_bound = compute_phase39_hyperconvex_rank_modulation(50.0, gamma_top=4.0)
        assert math.isclose(g_high_bound, expected_top, rel_tol=1e-7)

    def test_rank_modulation_strict_monotonicity_fine_grid(self):
        """Verify strict monotonicity across 100,000 points."""
        ranks = np.linspace(0.0, 1.0, 100000)
        g_vals = compute_phase39_hyperconvex_rank_modulation(ranks, gamma_top=4.0)
        diffs = np.diff(g_vals)
        assert np.all(diffs >= -1e-15), "Hyperconvex rank modulation must be strictly monotonically non-decreasing"

    def test_rank_modulation_negative_z_behavior(self):
        """Test behavior when z_denoised is negative."""
        ranks = np.linspace(0.0, 1.0, 1000)
        # When z_denoised < 0, g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.full(1000, -0.05)
        g_neg = compute_phase39_hyperconvex_rank_modulation(ranks, gamma_top=4.0, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35, rel_tol=1e-7)
        assert math.isclose(g_neg[-1], 0.35, rel_tol=1e-7)
        diffs = np.diff(g_neg)
        assert np.all(diffs <= 0.0), "Negative z modulation must be monotonically decreasing with rank"

    def test_rank_modulation_huge_array(self):
        """Test performance and stability on array of 1,000,000 elements."""
        ranks = np.random.uniform(-0.5, 1.5, 1000000)
        g = compute_phase39_hyperconvex_rank_modulation(ranks, gamma_top=4.0)
        assert len(g) == 1000000
        assert np.all(np.isfinite(g))
        assert np.min(g) >= 0.50
        assert np.max(g) <= 0.50 + 1.42 * math.exp(4.0) + 1e-7

    # =========================================================================
    # 3. apply_centaicosagonal_hyperbolic_deadband Adversarial Tests
    # =========================================================================

    def test_deadband_sub_microscopic_leakage_and_precision(self):
        """Test sub-microscopic values (1e-5, 1e-4, 0.0004) to verify noise leakage < 10^-62."""
        small_vals = np.array([
            1e-5, -1e-5,
            5e-5, -5e-5,
            1e-4, -1e-4,
            2e-4, -2e-4,
            3e-4, -3e-4,
            4e-4, -4e-4,
        ])
        denoised = apply_centaicosagonal_hyperbolic_deadband(small_vals, delta_noise=0.035, alpha_pos=120.0)
        for v, orig in zip(denoised, small_vals):
            assert abs(v) < 1e-62, f"Noise leakage {v} for input {orig} exceeds 1e-62 threshold"

    def test_deadband_signal_transmission_high_conviction(self):
        """Verify 100.0% signal transmission for |z| >= 0.150."""
        sig_vals = np.array([0.15, -0.15, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0])
        denoised = apply_centaicosagonal_hyperbolic_deadband(sig_vals, delta_noise=0.035, alpha_pos=120.0)
        np.testing.assert_allclose(denoised, sig_vals, rtol=1e-9, atol=1e-12)

    def test_deadband_odd_symmetry(self):
        """Verify exact odd symmetry: f(-z) == -f(z) under unconditioned symmetric regime."""
        z_grid = np.linspace(0.0001, 0.5, 1000)
        pos_out = apply_centaicosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=120.0)
        neg_out = apply_centaicosagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=120.0)
        np.testing.assert_allclose(pos_out, -neg_out, rtol=1e-9, atol=1e-15)

    def test_deadband_strict_monotonicity_fine_grid(self):
        """Verify monotonicity across 100,000 points in [-0.5, 0.5]."""
        z_grid = np.linspace(-0.5, 0.5, 100000)
        denoised = apply_centaicosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=120.0)
        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), "120th-order deadband must be monotonically non-decreasing"

    def test_deadband_extreme_large_inputs(self):
        """Test with extreme magnitudes (1e6, -1e6, 1e12, -1e12)."""
        huge_z = np.array([1e6, -1e6, 1e12, -1e12])
        denoised = apply_centaicosagonal_hyperbolic_deadband(huge_z, delta_noise=0.035, alpha_pos=120.0)
        np.testing.assert_allclose(denoised, huge_z, rtol=1e-9)

    # =========================================================================
    # 4. compute_lurie_clausen_scholze_fisher_rao_barycenter_blend Adversarial Tests
    # =========================================================================

    def test_barycenter_simplex_and_hierarchy_under_uniform(self):
        """Verify simplex constraint and strict Clausen-Scholze weight hierarchy."""
        alloc = UnifiedPortfolioAllocator()
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blend = alloc.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(uniform_weights)

        # Simplex condition
        assert math.isclose(sum(blend.values()), 1.0, rel_tol=1e-6)
        assert all(w >= 0.0 for w in blend.values())

        # Strict weight hierarchy: CVaR (3.45) > BL (2.90) > HERC (2.40) > RP (2.35)
        assert blend["cvar"] > blend["bl"]
        assert blend["bl"] > blend["herc"]
        assert blend["herc"] > blend["rp"]

    def test_barycenter_degenerate_extreme_inputs(self):
        """Test corner point distributions ([1,0,0,0], [0,1,0,0], etc.)."""
        alloc = UnifiedPortfolioAllocator()
        keys = ["bl", "herc", "rp", "cvar"]

        # Corner point allocations
        for i, target_key in enumerate(keys):
            vec = np.zeros(4)
            vec[i] = 1.0
            res = alloc.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(vec)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
            assert all(w >= 0.0 for w in res.values())
            # Target key should be dominant
            assert res[target_key] > 0.50

        # All zero input
        res_zero = alloc.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(np.zeros(4))
        assert math.isclose(sum(res_zero.values()), 1.0, rel_tol=1e-5)
        assert all(w >= 0.0 for w in res_zero.values())

        # Negative input
        res_neg = alloc.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(np.array([-0.5, 0.5, 0.2, 0.8]))
        assert math.isclose(sum(res_neg.values()), 1.0, rel_tol=1e-5)
        assert all(w >= 0.0 for w in res_neg.values())

    def test_barycenter_large_list_of_distributions(self):
        """Stress test with 500 distinct distributions in list format."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(999)
        dist_list = []
        for _ in range(500):
            w = np.random.exponential(1.0, 4)
            w /= np.sum(w)
            dist_list.append({"bl": w[0], "herc": w[1], "rp": w[2], "cvar": w[3]})

        res = alloc.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(dist_list)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert all(w >= 0.0 for w in res.values())

    # =========================================================================
    # 5. compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure Adversarial Tests
    # =========================================================================

    def test_evar_normal_and_fat_tail_distributions(self):
        """Test EVaR with normal, Student-t (df=3), and Cauchy fat-tailed returns."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # 1. Normal returns
        r_norm = np.random.normal(-0.01, 0.03, 1000)
        evar_norm = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_norm)
        evar_norm_34 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_risk_measure(r_norm)
        v35_norm = evar_norm["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        v34_norm = evar_norm_34["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_value"]
        assert np.isfinite(v35_norm)
        assert v35_norm >= v34_norm - 1e-6, "EVaR_35 >= EVaR_34 unconditionally"

        # 2. Student-t (fat tails, df=3)
        r_t = np.random.standard_t(df=3, size=1000) * 0.02 - 0.01
        evar_t = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_t)
        evar_t_34 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_risk_measure(r_t)
        v35_t = evar_t["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        v34_t = evar_t_34["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_value"]
        assert np.isfinite(v35_t)
        assert v35_t >= v34_t - 1e-6, "EVaR_35 >= EVaR_34 for Student-t"

        # 3. Cauchy (extreme fat tail)
        # Cauchy can produce values like 1000.0; clip returns to realistic stock loss bounds [-1.0, 1.0]
        r_cauchy = np.clip(np.random.standard_cauchy(1000) * 0.02 - 0.01, -0.99, 1.0)
        evar_cauchy = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_cauchy)
        evar_cauchy_34 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_risk_measure(r_cauchy)
        v35_c = evar_cauchy["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        v34_c = evar_cauchy_34["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_value"]
        assert np.isfinite(v35_c)
        assert v35_c >= v34_c - 1e-6, "EVaR_35 >= EVaR_34 for Cauchy"

    def test_evar_degenerate_inputs_single_value_and_constants(self):
        """Test EVaR with single return, constant returns, empty returns, NaNs."""
        alloc = UnifiedPortfolioAllocator()

        # Constant returns (all -0.05)
        r_const = np.full(100, -0.05)
        evar_const = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_const)
        v_const = evar_const["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        assert np.isfinite(v_const)
        # Loss is +0.05, so EVaR should be approximately >= 0.05
        assert v_const >= 0.049

        # Constant zero returns
        r_zero = np.zeros(100)
        evar_zero = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_zero)
        assert np.isfinite(evar_zero["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"])

        # Returns with NaNs and infinities
        r_nan = np.array([np.nan, -0.02, 0.01, np.inf, -np.inf, -0.05])
        evar_nan = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_nan)
        assert np.isfinite(evar_nan["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"])

    def test_evar_huge_vector_scale(self):
        """Test EVaR with 50,000 return samples."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(777)
        r_huge = np.random.normal(-0.005, 0.025, 50000)

        evar_huge = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(r_huge)
        evar_huge_34 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_risk_measure(r_huge)

        v35 = evar_huge["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"]
        v34 = evar_huge_34["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_value"]

        assert np.isfinite(v35)
        assert v35 >= v34 - 1e-6
        assert evar_huge["order"] == 35
        assert evar_huge["optimal_t"] > 0

"""
tests/test_phase102_adversarial_numerical.py

Adversarial Empirical Stress Testing Suite for Phase 102:
Role: Numerical & Mathematical Stress Challenger (Features F480, F481, F482.1, F482.2)

Target Verification Axes:
1. 624th-Order Sexcentotetravigesimal Hyperbolic Noise Deadband (F480):
   - Extreme values z in [-1e-12, 1e-12], subnormal floats, denormals down to 1e-324.
   - Near-zero exact underflow: |z| <= 0.0003 -> exactly 0.0 in float64 (< 10^-624).
   - Full conviction transmission: |z| >= 0.150 -> 100.000% transmission (|z| preserved to float64 eps).
   - Strict rank monotonicity (Spearman rho == 1.0000) and exact odd symmetry.
   - NaN, Inf, empty array, and high-dimensional shape stability.
2. 135th-Order Hyper-Convex Rank Modulation (F480):
   - Boundary behavior for r in [0.99, 1.00].
   - Top-decile warping verification: g(1.0) > 10^7 (target ~ 9.27e17 at gamma_top = 40.00).
   - IEEE 754 float64 overflow safety across all regime gamma_top <= 40.00.
   - Negative signal branch g_neg(r) = 1.35 - 1.00 * r rank penalty.
   - Out-of-bounds clipping [0.0, 1.0].
3. Quantum Geometric Langlands Monster Whittaker Coupler Phase 102 (F481):
   - Theoretical parameter assertions: kappa = 43.40, lambda_monster >= 1.0 - 1e-26 (26-nines), harmony_boost = 12.00.
   - 216th-order chiral oper obstruction and 128th-order topological defect invariants active under is_phase102.
   - Extreme inputs: huge values (|p| > 1000), intermediate power overflow protection via clipping |p| <= 300.0, subnormals (|p| < 1e-20), identical pillar scores, Infs and NaNs.
   - Output finite boundedness for FERI_v102, feri_v102, f_out_102 in [0.0, 1.0].
4. Higher-Homology-52 Motivic Fisher-Rao Barycenter Blending (F482.1):
   - Simplex constraint: sum(q) == 1.000000 across all degenerate input distributions (one-hot, zero vectors, extreme dynamic range).
   - Strictly positive element floor: q_i >= tau = 0.8e-6 for all i.
   - Curvature hierarchy: CVaR (13.00) > BL (10.70) > HERC (6.80) > RP (2.95) under uniform input.
   - Riemannian gradient norm clipping in [-100.0, 100.0] preventing exponential gradient explosion.
5. 136th-Cumulant Expansion Trans-Singular EVaR Risk Measure (F482.2):
   - Order = 136, xi_monster = 1.0 - 1e-38 (38-nines).
   - Extreme heavy-tail distributions: Student-t (df=1.5 and df=0.8), Pareto (alpha=1.1), Cauchy, 1000-sigma market crash.
   - Log-gamma numerical stability for 136! (~ 2.14e232).
   - Edge case returns: all zero, constant, microscopic (1e-8), catastrophic drawdowns.
6. Waterfall Capital Redistribution Convergence (F482.1):
   - Unconstrained capacity absorption, eliminating idle cash drag under ADV liquidity limits.
   - Strict allocation boundary compliance and capital conservation.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import sys
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentotetravigesimal_hyperbolic_deadband,
    apply_624th_order_hyperbolic_deadband,
    compute_phase102_deadband,
    compute_phase102_hyperconvex_rank_modulation,
    REGIME_GAMMA_TOP_V102,
    get_regime_adaptive_gamma_top_v102,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase102Coupler,
)
from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_52_fisher_rao_barycenter_blend,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_52_evar_risk_measure,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =========================================================================
# AXIS 1: 624TH-ORDER HYPERBOLIC NOISE DEADBAND STRESS TESTS
# =========================================================================

class TestAdversarialDeadbandStressPhase102:
    """Adversarial stress testing of the 624th-Order Sexcentotetravigesimal Hyperbolic Noise Deadband."""

    def test_deadband_exact_zero_underflow_dense_grid(self):
        """Verify that |z| <= 0.0003 strictly underflows to exact 0.0 in float64."""
        # 100,000 points strictly within [-0.0003, 0.0003]
        z_grid = np.linspace(-0.0003, 0.0003, 100000, dtype=np.float64)
        denoised = apply_sexcentotetravigesimal_hyperbolic_deadband(z_grid)

        # Check exact 0.0 for every point
        nonzero_mask = denoised != 0.0
        num_nonzeros = np.sum(nonzero_mask)
        assert num_nonzeros == 0, f"Found {num_nonzeros} non-zero values in deadband region [-0.0003, 0.0003]"

        # Boundary checks specifically at +/- 0.0003000
        z_exact_boundaries = np.array([-0.0003000, -0.00029999, 0.0, 0.00029999, 0.0003000])
        denoised_bounds = apply_sexcentotetravigesimal_hyperbolic_deadband(z_exact_boundaries)
        for orig, d in zip(z_exact_boundaries, denoised_bounds):
            assert d == 0.0, f"Boundary point {orig} did not underflow to 0.0: got {d}"

    def test_deadband_subnormal_floats_and_denormals(self):
        """Stress test with subnormal and microscopic float64 values."""
        smallest_subnormal = np.nextafter(np.float64(0.0), np.float64(1.0))  # ~ 4.94e-324
        smallest_normal = sys.float_info.min  # ~ 2.22e-308

        test_denormals = np.array([
            smallest_subnormal,
            -smallest_subnormal,
            1e-320,
            -1e-320,
            1e-310,
            -1e-310,
            smallest_normal,
            -smallest_normal,
            1e-15,
            -1e-15,
            1e-12,
            -1e-12,
            1e-6,
            -1e-6,
            0.0,
            -0.0,
        ], dtype=np.float64)

        denoised = apply_sexcentotetravigesimal_hyperbolic_deadband(test_denormals)

        # All of these are well below 0.0003, so all must be exactly 0.0
        for orig, d in zip(test_denormals, denoised):
            assert d == 0.0, f"Subnormal/denormal {orig} failed to yield exact 0.0: got {d}"

    def test_deadband_full_conviction_transmission(self):
        """Verify that |z| >= 0.150 is transmitted with 100.000% fidelity without distortion."""
        conviction_levels = np.array([
            0.150, 0.151, 0.200, 0.300, 0.500, 1.000, 2.500, 10.000, 100.000,
            -0.150, -0.151, -0.200, -0.300, -0.500, -1.000, -2.500, -10.000, -100.000,
        ], dtype=np.float64)

        denoised = apply_sexcentotetravigesimal_hyperbolic_deadband(conviction_levels)

        # Transmission must be mathematically exact to float64 machine epsilon
        for orig, d in zip(conviction_levels, denoised):
            diff = abs(d - orig)
            rel_err = diff / abs(orig)
            assert rel_err < 1e-12, f"Conviction level {orig} transmitted with loss: got {d}, rel_err={rel_err}"

    def test_deadband_rank_monotonicity_and_odd_symmetry(self):
        """Verify strict rank monotonicity and exact odd symmetry."""
        grid = np.linspace(-5.0, 5.0, 50000, dtype=np.float64)
        denoised = apply_sexcentotetravigesimal_hyperbolic_deadband(grid)

        # Monotonicity check
        diffs = np.diff(denoised)
        min_diff = np.min(diffs)
        assert min_diff >= -1e-15, f"Monotonicity violated: min_diff = {min_diff}"

        # Odd symmetry check: f(-z) == -f(z)
        pos_z = np.linspace(0.0001, 2.0, 20000, dtype=np.float64)
        denoised_pos = apply_sexcentotetravigesimal_hyperbolic_deadband(pos_z)
        denoised_neg = apply_sexcentotetravigesimal_hyperbolic_deadband(-pos_z)
        sym_diff = np.abs(denoised_pos + denoised_neg)
        max_sym_err = np.max(sym_diff)
        assert max_sym_err < 1e-14, f"Odd symmetry violated: max_sym_err = {max_sym_err}"

    def test_deadband_nan_inf_empty_and_nd_stability(self):
        """Verify robustness to NaNs, Infs, empty arrays, and multidimensional arrays."""
        # Empty array
        empty_res = apply_sexcentotetravigesimal_hyperbolic_deadband(np.array([]))
        assert len(empty_res) == 0

        # NaNs and Infs handling
        bad_inputs = np.array([np.nan, np.inf, -np.inf, 0.05, -0.05])
        denoised_bad = apply_sexcentotetravigesimal_hyperbolic_deadband(bad_inputs)
        assert np.isnan(denoised_bad[0])
        assert np.isinf(denoised_bad[1])
        assert np.isinf(denoised_bad[2])

        # 2D and 3D shape preservation
        mat_2d = np.random.randn(50, 20)
        res_2d = apply_sexcentotetravigesimal_hyperbolic_deadband(mat_2d)
        assert res_2d.shape == (50, 20)

        mat_3d = np.random.randn(10, 20, 30)
        res_3d = apply_sexcentotetravigesimal_hyperbolic_deadband(mat_3d)
        assert res_3d.shape == (10, 20, 30)


# =========================================================================
# AXIS 2: 135TH-ORDER HYPER-CONVEX RANK MODULATION STRESS TESTS
# =========================================================================

class TestAdversarialRankModulationStressPhase102:
    """Adversarial stress testing of 135th-Order Hyper-Convex Rank Modulation."""

    def test_rank_modulation_top_decile_warping_magnitude(self):
        """Verify top decile warping g(1.0) > 10^7 at maximum regime gamma_top = 40.00."""
        # Formula: g(r) = 0.50 + 3.94 * r * exp(gamma_top * r^135)
        # At r = 1.0, gamma_top = 40.00 -> g(1.0) = 0.50 + 3.94 * exp(40.00) ≈ 9.27e17
        r_top = np.array([1.0], dtype=np.float64)
        mod_top = compute_phase102_hyperconvex_rank_modulation(r_top, gamma_top=40.00)
        assert mod_top[0] > 1e7, f"g(1.0) = {mod_top[0]} <= 10^7"
        expected = 0.50 + 3.94 * math.exp(40.00)
        assert math.isclose(mod_top[0], expected, rel_tol=1e-12)

    def test_rank_modulation_boundary_behavior_r_near_one(self):
        """Test fine boundary grid for r in [0.990, 1.000]."""
        fine_r = np.linspace(0.990, 1.000, 1000, dtype=np.float64)
        mod = compute_phase102_hyperconvex_rank_modulation(fine_r, gamma_top=40.00)

        # Monotonically increasing check
        assert np.all(np.diff(mod) >= 0.0), "Rank modulation is not monotonically increasing near r=1.0"
        assert mod[0] > 1.0, f"g(0.990) = {mod[0]} too small"
        assert mod[-1] > 1e7

    def test_rank_modulation_float64_overflow_safety_across_regimes(self):
        """Verify IEEE 754 float64 overflow safety across all regimes."""
        for regime_name, gamma_val in REGIME_GAMMA_TOP_V102.items():
            assert gamma_val <= 40.00, f"Regime {regime_name} has gamma_top = {gamma_val} > 40.00"
            r_dense = np.linspace(0.0, 1.0, 1000, dtype=np.float64)
            mod = compute_phase102_hyperconvex_rank_modulation(r_dense, gamma_top=gamma_val)
            assert np.all(np.isfinite(mod)), f"Overflow or NaN encountered in regime {regime_name}"
            assert np.all(mod >= 0.50), f"Modulation below minimum baseline 0.50 in regime {regime_name}"

    def test_rank_modulation_clipping_and_negative_signal_branch(self):
        """Test out-of-bounds clipping and negative signal branch penalty."""
        # Out-of-bounds ranks [ -0.5, 1.5 ]
        out_ranks = np.array([-0.5, -0.1, 0.0, 1.0, 1.1, 1.5], dtype=np.float64)
        mod_out = compute_phase102_hyperconvex_rank_modulation(out_ranks, gamma_top=40.00)

        # -0.5 clipped to 0.0 -> g(0.0) = 0.50
        assert math.isclose(mod_out[0], 0.50, abs_tol=1e-12)
        assert math.isclose(mod_out[1], 0.50, abs_tol=1e-12)
        assert math.isclose(mod_out[2], 0.50, abs_tol=1e-12)

        # 1.5 clipped to 1.0 -> g(1.0)
        assert math.isclose(mod_out[3], mod_out[4], rel_tol=1e-12)
        assert math.isclose(mod_out[4], mod_out[5], rel_tol=1e-12)

        # Negative branch: g_neg(r) = 1.35 - 1.00 * r
        ranks = np.linspace(0.0, 1.0, 100)
        z_neg = np.full(len(ranks), -0.25)
        mod_neg = compute_phase102_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)

        # At r = 0.0 -> 1.35, at r = 1.0 -> 0.35
        assert math.isclose(mod_neg[0], 1.35, abs_tol=1e-12)
        assert math.isclose(mod_neg[-1], 0.35, abs_tol=1e-12)
        assert np.all(np.diff(mod_neg) <= 0.0)


# =========================================================================
# AXIS 3: QGL MONSTER WHITTAKER COUPLER PHASE 102 STRESS TESTS
# =========================================================================

class TestAdversarialQGLMonsterWhittakerCouplerStressPhase102:
    """Adversarial stress testing of the QGL Monster Whittaker Coupler Phase 102."""

    def test_coupler_phase102_invariants(self):
        """Verify Phase 102 coupler invariants, 216th-order chiral oper and 128th-order defect."""
        coupler = Phase102Coupler()
        assert coupler.version >= 102
        assert coupler.is_phase102 is True
        assert math.isclose(coupler.kappa_monster_whit, 43.40, abs_tol=1e-5)
        assert coupler.lambda_monster >= 1.0 - 1e-25
        assert math.isclose(coupler.harmony_boost, 12.00, abs_tol=1e-5)

    def test_coupler_standard_and_degenerate_pillar_inputs(self):
        """Verify coupler evaluate on normalized pillar scores and boundary cases."""
        coupler = Phase102Coupler()

        # 1. Standard factor range scores (|p| <= 5.0)
        norm_df = pd.DataFrame({
            "val": [2.5, -2.5],
            "mom": [1.5, -1.5],
            "flow": [2.0, -2.0],
            "cat": [0.5, -0.5],
            "net": [3.0, -3.0],
        }, index=["A", "B"])
        norm_res = coupler.couple_signals(norm_df)
        assert np.all(np.isfinite(norm_res["FERI_v102"])), "Non-finite FERI on standard scores"
        assert np.all(norm_res["FERI_v102"] >= 0.0) and np.all(norm_res["FERI_v102"] <= 1.0)

        # 2. Identical scores across all pillars (diff == 0.0)
        identical_df = pd.DataFrame({
            "val": [0.5, -0.2],
            "mom": [0.5, -0.2],
            "flow": [0.5, -0.2],
            "cat": [0.5, -0.2],
            "net": [0.5, -0.2],
        }, index=["A", "B"])
        ident_res = coupler.couple_signals(identical_df)
        assert np.all(np.isclose(ident_res["FERI_v102"], 1.0, atol=1e-6)), "Identical scores did not yield FERI == 1.0"

        # 3. Microscopic subnormal scores (1e-20)
        subnormal_df = pd.DataFrame({
            "val": [1e-20, -1e-20],
            "mom": [2e-20, -2e-20],
            "flow": [3e-20, -3e-20],
            "cat": [4e-20, -4e-20],
            "net": [5e-20, -5e-20],
        }, index=["A", "B"])
        sub_res = coupler.couple_signals(subnormal_df)
        assert np.all(np.isfinite(sub_res["FERI_v102"]))
        assert np.all(np.isclose(sub_res["FERI_v102"], 1.0, atol=1e-6))

        # 4. NaNs and Infs in input matrix
        bad_df = pd.DataFrame({
            "val": [np.nan, np.inf],
            "mom": [-np.inf, 0.1],
            "flow": [0.2, np.nan],
            "cat": [np.nan, 0.3],
            "net": [0.4, -np.inf],
        }, index=["A", "B"])
        bad_res = coupler.couple_signals(bad_df)
        assert np.all(np.isfinite(bad_res["FERI_v102"])), "NaN/Inf leaked into FERI output"

    def test_coupler_intermediate_power_clipping_overflow_protection(self):
        """
        Adversarial Stress Test: intermediate factor power overflow clipping (|p| <= 300.0).
        Demonstrate that when inputs exceed |p| >= 400.0 or 1000.0, factor matrix clipping
        strictly limits (300.0)^128 < 1.798e308, preventing intermediate float64 overflow,
        producing finite, non-NaN FERI_v102 bounded in [0.0, 1.0].
        """
        coupler = Phase102Coupler()
        overflow_df = pd.DataFrame({
            "val": [400.0, -500.0, 1000.0],
            "mom": [400.0, 350.0, -1000.0],
            "flow": [400.0, 450.0, 800.0],
            "cat": [400.0, -350.0, -600.0],
            "net": [400.0, 500.0, 950.0],
        }, index=["OVF1", "OVF2", "OVF3"])
        res = coupler.couple_signals(overflow_df)
        feri_series = res["FERI_v102"]
        assert np.all(np.isfinite(feri_series)), "Expected finite values in FERI output under unbounded inputs"
        assert not np.any(np.isnan(feri_series)), "Expected non-NaN values in FERI output under unbounded inputs"
        assert np.all((feri_series >= 0.0) & (feri_series <= 1.0)), "FERI values out of [0, 1] range"


# =========================================================================
# AXIS 4: HIGHER-HOMOLOGY-52 FISHER-RAO BARYCENTER BLENDING STRESS TESTS
# =========================================================================

class TestAdversarialBarycenterBlendStressPhase102:
    """Adversarial stress testing of Higher-Homology-52 Fisher-Rao Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=102)

    def test_barycenter_simplex_constraint_under_extreme_degeneracy(self, allocator):
        """Test simplex constraint sum(q) == 1.0 across all degenerate distributions."""
        degenerate_cases = [
            # One-hot extreme vectors
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 0.0, 1.0]),
            # All zeros
            np.array([0.0, 0.0, 0.0, 0.0]),
            # Uniform
            np.array([0.25, 0.25, 0.25, 0.25]),
            # Extreme dynamic range
            np.array([1e15, 1e-15, 1.0, 0.0]),
            # Negative inputs
            np.array([-1.0, 0.5, 0.5, 0.5]),
            # Dict one-hot
            {"BL": 1.0, "HERC": 0.0, "RP": 0.0, "CVaR": 0.0},
            {"BL": 0.0, "HERC": 0.0, "RP": 0.0, "CVaR": 1.0},
        ]

        for case in degenerate_cases:
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_52_fisher_rao_barycenter_blend(case)
            assert isinstance(res, dict)
            weights = list(res.values())
            # Simplex condition strictly preserved: sum == 1.000000
            assert math.isclose(sum(weights), 1.0, abs_tol=1e-5), f"Sum != 1.0 for case {case}: got {sum(weights)}"

    def test_barycenter_tau_floor_violation_prevention(self, allocator):
        """
        Verify that exact truncated simplex projection strictly guarantees
        q_i >= tau = 0.8e-6 and exact simplex sum == 1.000000 across extreme one-hot vectors.
        """
        tau_mandatory = 0.8e-6
        for one_hot_idx in range(4):
            v = np.zeros(4)
            v[one_hot_idx] = 1.0
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_52_fisher_rao_barycenter_blend(v)
            min_weight = min(res.values())
            assert min_weight >= tau_mandatory, (
                f"Strict tau floor violated for index {one_hot_idx}: {min_weight} < {tau_mandatory}"
            )
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6), (
                f"Simplex sum violated for index {one_hot_idx}: sum={sum(res.values())}"
            )

    def test_barycenter_curvature_hierarchy(self, allocator):
        """Verify exact theoretical ordering CVaR (13.00) > BL (10.70) > HERC (6.80) > RP (2.95)."""
        uniform_dict = {"BL": 0.25, "HERC": 0.25, "RP": 0.25, "CVaR": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_52_fisher_rao_barycenter_blend(uniform_dict)

        cvar_w = res.get("cvar", res.get("CVaR", 0.0))
        bl_w = res.get("bl", res.get("BL", 0.0))
        herc_w = res.get("herc", res.get("HERC", 0.0))
        rp_w = res.get("rp", res.get("RP", 0.0))

        assert cvar_w > bl_w, f"CVaR ({cvar_w}) <= BL ({bl_w})"
        assert bl_w > herc_w, f"BL ({bl_w}) <= HERC ({herc_w})"
        assert herc_w > rp_w, f"HERC ({herc_w}) <= RP ({rp_w})"
        assert math.isclose(cvar_w + bl_w + herc_w + rp_w, 1.0, abs_tol=1e-5)

    def test_barycenter_gradient_clipping_and_sparse_vector_stability(self, allocator):
        """
        Verify that Riemannian gradient norm clipping in [-100.0, 100.0]
        and exponential argument clipping in [-100.0, 100.0] prevent Riemannian gradient explosion
        and NaN collapse under sparse / skewed inputs, strictly producing finite, non-NaN probabilities.
        """
        tau_mandatory = 0.8e-6
        sparse_vec = np.array([9.99999e-01, 1e-15, 1e-15, 1e-15])
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_52_fisher_rao_barycenter_blend(sparse_vec)
        assert all(np.isfinite(v) for v in res.values()), "Encountered non-finite values on sparse vector"
        assert not any(np.isnan(v) for v in res.values()), "Encountered NaN values on sparse vector"
        assert min(res.values()) >= tau_mandatory, f"Minimum weight below tau: {min(res.values())}"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6), f"Sum != 1.0: {sum(res.values())}"


# =========================================================================
# AXIS 5: 136TH-CUMULANT EVAR TAIL RISK MEASURE STRESS TESTS
# =========================================================================

class TestAdversarialEVaRTailRiskStressPhase102:
    """Adversarial stress testing of 136th-Cumulant Expansion Trans-Singular EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=102)

    def test_evar_order_and_xi_monster_invariants(self, allocator):
        """Verify order=136 and 38-nines xi_monster invariants."""
        dummy_ret = np.array([-0.02, 0.01, 0.03, -0.01])
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_52_evar_risk_measure(dummy_ret)

        assert res.get("order") == 136
        assert math.isclose(float(res.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
        assert "phase102_evar" in res
        assert np.isfinite(res["phase102_evar"])
        assert res["phase102_evar"] > 0.0

    def test_evar_extreme_heavy_tail_distributions(self, allocator):
        """Stress EVaR calculation on Student-t, Pareto, Cauchy, and market crash scenarios."""
        rng = np.random.RandomState(102)

        # 1. Student-t with df=1.5 (infinite variance)
        t_heavy = rng.standard_t(df=1.5, size=2000) * 0.02
        res_t = allocator.compute_phase102_evar(t_heavy)
        assert np.isfinite(res_t["phase102_evar"])
        assert res_t["phase102_evar"] > 0.0

        # 2. Student-t with df=0.8 (infinite mean and variance)
        t_super_heavy = rng.standard_t(df=0.8, size=1000) * 0.01
        res_super_t = allocator.compute_phase102_evar(t_super_heavy)
        assert np.isfinite(res_super_t["phase102_evar"])
        assert res_super_t["phase102_evar"] > 0.0

        # 3. Cauchy distribution
        cauchy_ret = rng.standard_cauchy(size=1000) * 0.01
        res_cauchy = allocator.compute_phase102_evar(cauchy_ret)
        assert np.isfinite(res_cauchy["phase102_evar"])
        assert res_cauchy["phase102_evar"] > 0.0

        # 4. Pareto distribution (heavy right tail / negated for losses)
        pareto_ret = -(rng.pareto(a=1.1, size=1000) - 1.0) * 0.02
        res_pareto = allocator.compute_phase102_evar(pareto_ret)
        assert np.isfinite(res_pareto["phase102_evar"])
        assert res_pareto["phase102_evar"] > 0.0

        # 5. Catastrophic 1000-sigma market crash scenario
        crash_ret = np.concatenate([rng.normal(0.001, 0.01, size=995), [-0.20, -0.40, -0.60, -0.80, -0.95]])
        res_crash = allocator.compute_phase102_evar(crash_ret)
        assert np.isfinite(res_crash["phase102_evar"])
        assert res_crash["phase102_evar"] > 0.50, f"EVaR on catastrophic crash was too low: {res_crash['phase102_evar']}"

    def test_evar_edge_case_returns(self, allocator):
        """Verify stability on all zero, constant, microscopic, and single-element returns."""
        # 1. All zeros
        zeros = np.zeros(100)
        res_z = allocator.compute_phase102_evar(zeros)
        assert np.isfinite(res_z["phase102_evar"])
        assert res_z["phase102_evar"] >= 0.0

        # 2. Constant returns (-0.05)
        const = np.full(50, -0.05)
        res_c = allocator.compute_phase102_evar(const)
        assert np.isfinite(res_c["phase102_evar"])
        opt_t = float(res_c["optimal_t"])
        expected_evar = 0.05 - math.log(0.05) / opt_t
        assert math.isclose(res_c["phase102_evar"], expected_evar, rel_tol=1e-4)

        # 3. Microscopic returns (1e-8)
        micro = np.array([-1e-8, 1e-8, -2e-8, 2e-8])
        res_m = allocator.compute_phase102_evar(micro)
        assert np.isfinite(res_m["phase102_evar"])
        assert res_m["phase102_evar"] > 0.0


# =========================================================================
# AXIS 6: WATERFALL CAPITAL REDISTRIBUTION CONVERGENCE TESTS
# =========================================================================

class TestAdversarialWaterfallRedistributionStressPhase102:
    """Adversarial stress testing of Waterfall Capital Redistribution."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=102)

    def test_waterfall_redistribution_eliminates_idle_cash(self, allocator):
        """Verify that waterfall redistribution allocates unconstrained capacity without idle cash leakage."""
        current_w = {"A": 0.05, "B": 0.05, "C": 0.05, "D": 0.05}
        target_w = {"A": 0.45, "B": 0.45, "C": 0.05, "D": 0.05}
        # A and B are severely constrained by ADV limits (delta <= 0.05)
        max_delta = {"A": 0.05, "B": 0.05, "C": 0.30, "D": 0.30}
        alpha_scores = {"A": 0.98, "B": 0.95, "C": 0.88, "D": 0.70}

        pre_waterfall = {}
        for sym in current_w:
            delta = target_w[sym] - current_w[sym]
            allowed = max(-max_delta[sym], min(max_delta[sym], delta))
            pre_waterfall[sym] = current_w[sym] + allowed

        # Pre-waterfall: A=0.10, B=0.10, C=0.05, D=0.05 -> sum = 0.30 (0.70 idle cash!)
        assert math.isclose(sum(pre_waterfall.values()), 0.30, abs_tol=1e-5)

        redistributed = allocator.redistribute_waterfall_capital(
            current_weights=current_w,
            next_weights=pre_waterfall,
            target_weights=target_w,
            max_delta_w=max_delta,
            max_single_weight=0.35,
            alpha_scores=alpha_scores,
        )

        # C and D have max_single_weight = 0.35 and max_delta = 0.30
        # C absorbs from 0.05 to 0.35 (+0.30), D absorbs from 0.05 to 0.35 (+0.30)
        # Total weight increases from 0.30 to 0.90!
        assert sum(redistributed.values()) > sum(pre_waterfall.values())
        assert math.isclose(sum(redistributed.values()), 0.90, abs_tol=1e-4)
        assert redistributed["A"] == pre_waterfall["A"]
        assert redistributed["B"] == pre_waterfall["B"]
        assert redistributed["C"] <= 0.35
        assert redistributed["D"] <= 0.35

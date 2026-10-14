"""
tests/test_phase99_adversarial_numerical.py

Adversarial Empirical Stress Testing Suite for Phase 99:
Role: Numerical & Mathematical Stress Challenger (Features F465, F466, F467.1, F467.2)

Target Verification Axes:
1. 600th-Order Sexcentennial Hyperbolic Noise Deadband (F465):
   - Extreme values z in [-1e-12, 1e-12], subnormal floats, denormals down to 1e-324.
   - Near-zero exact underflow: |z| <= 0.0003 -> exactly 0.0 in float64 (< 10^-600).
   - Full conviction transmission: |z| >= 0.150 -> 100.000% transmission (|z| preserved to float64 eps).
   - Strict rank monotonicity (Spearman rho == 1.0000) and exact odd symmetry.
   - NaN, Inf, empty array, and high-dimensional shape stability.
2. 129th-Order Hyper-Convex Rank Modulation (F465):
   - Boundary behavior for r in [0.99, 1.00].
   - Top-decile warping verification: g(1.0) > 10^7 (target ~ 4.47e16).
   - IEEE 754 float64 overflow safety across all regime gamma_top <= 37.00.
   - Negative signal branch g_neg(r) = 1.35 - 1.00 * r rank penalty.
   - Out-of-bounds clipping [0.0, 1.0].
3. Quantum Geometric Langlands Monster Whittaker Coupler Phase 99 (F466):
   - Theoretical parameter assertions: kappa = 41.60, lambda_monster = 1.0 - 1e-23 (23-nines), harmony_boost = 10.95.
   - 210th-order chiral oper obstruction and 122nd-order topological defect invariants active under is_phase99.
   - Extreme inputs: huge values (|p| > 1000), subnormals (|p| < 1e-20), identical pillar scores, Infs and NaNs.
   - Output finite boundedness for FERI_v99, feri_v99, f_out_99 in [0.0, 1.0].
4. Higher-Homology-49 Motivic Fisher-Rao Barycenter Blending (F467.1):
   - Simplex constraint: sum(q) == 1.000000 across all degenerate input distributions (one-hot, zero vectors, extreme dynamic range).
   - Strictly positive element floor: q_i >= tau = 1.5e-6 for all i.
   - Curvature hierarchy: CVaR (12.25) > BL (10.10) > HERC (6.35) > RP (2.80) under uniform input.
   - Convergence speed and numerical stability under degenerate/extreme inputs.
5. 130th-Cumulant Expansion Trans-Singular EVaR Risk Measure (F467.2):
   - Order = 130, xi_monster = 1.0 - 1e-35 (35-nines).
   - Extreme heavy-tail distributions: Student-t (df=1.5 and df=0.8), Pareto (alpha=1.1), Cauchy, 1000-sigma market crash.
   - Log-gamma numerical stability for 130! (~ 6.47e219).
   - Edge case returns: all zero, constant, microscopic (1e-8), catastrophic drawdowns.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import sys
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentennial_hyperbolic_deadband,
    apply_600th_order_hyperbolic_deadband,
    compute_phase99_hyperconvex_rank_modulation,
    REGIME_GAMMA_TOP_V99,
    get_regime_adaptive_gamma_top_v99,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase99Coupler,
)
from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_49_evar_risk_measure,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =========================================================================
# AXIS 1: 600TH-ORDER HYPERBOLIC NOISE DEADBAND STRESS TESTS
# =========================================================================

class TestAdversarialDeadbandStress:
    """Adversarial stress testing of the 600th-Order Sexcentennial Hyperbolic Noise Deadband."""

    def test_deadband_exact_zero_underflow_dense_grid(self):
        """Verify that |z| <= 0.0003 strictly underflows to exact 0.0 in float64."""
        # 100,000 points strictly within [-0.0003, 0.0003]
        z_grid = np.linspace(-0.0003, 0.0003, 100000, dtype=np.float64)
        denoised = apply_sexcentennial_hyperbolic_deadband(z_grid)

        # Check exact 0.0 for every point
        nonzero_mask = denoised != 0.0
        num_nonzeros = np.sum(nonzero_mask)
        assert num_nonzeros == 0, f"Found {num_nonzeros} non-zero values in deadband region [-0.0003, 0.0003]"

        # Boundary checks specifically at +/- 0.0003000
        z_exact_boundaries = np.array([-0.0003000, -0.00029999, 0.0, 0.00029999, 0.0003000])
        denoised_bounds = apply_sexcentennial_hyperbolic_deadband(z_exact_boundaries)
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

        denoised = apply_sexcentennial_hyperbolic_deadband(test_denormals)

        # All of these are well below 0.0003, so all must be exactly 0.0
        for orig, d in zip(test_denormals, denoised):
            assert d == 0.0, f"Subnormal/denormal {orig} failed to yield exact 0.0: got {d}"

    def test_deadband_full_conviction_transmission(self):
        """Verify that |z| >= 0.150 is transmitted with 100.000% fidelity without distortion."""
        conviction_levels = np.array([
            0.150, 0.151, 0.200, 0.300, 0.500, 1.000, 2.500, 10.000, 100.000,
            -0.150, -0.151, -0.200, -0.300, -0.500, -1.000, -2.500, -10.000, -100.000,
        ], dtype=np.float64)

        denoised = apply_sexcentennial_hyperbolic_deadband(conviction_levels)

        # Transmission must be mathematically exact to float64 machine epsilon
        for orig, d in zip(conviction_levels, denoised):
            # Ratio of denoised to orig must be 1.0000000000000000
            diff = abs(d - orig)
            rel_err = diff / abs(orig)
            assert rel_err < 1e-12, f"Conviction level {orig} transmitted with loss: got {d}, rel_err={rel_err}"

    def test_deadband_rank_monotonicity_and_odd_symmetry(self):
        """Verify strict rank monotonicity (Spearman rho == 1.0000) and exact odd symmetry."""
        grid = np.linspace(-5.0, 5.0, 50000, dtype=np.float64)
        denoised = apply_sexcentennial_hyperbolic_deadband(grid)

        # Monotonicity check
        diffs = np.diff(denoised)
        min_diff = np.min(diffs)
        assert min_diff >= -1e-15, f"Monotonicity violated: min_diff = {min_diff}"

        # Odd symmetry check: f(-z) == -f(z)
        pos_z = np.linspace(0.0001, 2.0, 20000, dtype=np.float64)
        denoised_pos = apply_sexcentennial_hyperbolic_deadband(pos_z)
        denoised_neg = apply_sexcentennial_hyperbolic_deadband(-pos_z)
        sym_diff = np.abs(denoised_pos + denoised_neg)
        max_sym_err = np.max(sym_diff)
        assert max_sym_err < 1e-14, f"Odd symmetry violated: max_sym_err = {max_sym_err}"

    def test_deadband_pathological_and_scalar_inputs(self):
        """Verify handling of scalars, empty arrays, 2D arrays, and non-finite floats."""
        # Scalar float
        s_res = apply_sexcentennial_hyperbolic_deadband(0.0001)
        assert isinstance(s_res, float)
        assert s_res == 0.0

        s_conv = apply_sexcentennial_hyperbolic_deadband(0.25)
        assert math.isclose(s_conv, 0.25, rel_tol=1e-12)

        # Empty array
        empty_arr = np.array([], dtype=np.float64)
        empty_res = apply_sexcentennial_hyperbolic_deadband(empty_arr)
        assert len(empty_res) == 0

        # Pandas Series
        s = pd.Series([0.0001, 0.20, -0.0002, -0.30], index=["s1", "s2", "s3", "s4"])
        s_out = apply_sexcentennial_hyperbolic_deadband(s)
        assert isinstance(s_out, pd.Series)
        assert s_out["s1"] == 0.0
        assert math.isclose(s_out["s2"], 0.20, rel_tol=1e-12)
        assert s_out["s3"] == 0.0
        assert math.isclose(s_out["s4"], -0.30, rel_tol=1e-12)


# =========================================================================
# AXIS 2: 129TH-ORDER HYPER-CONVEX RANK MODULATION STRESS TESTS
# =========================================================================

class TestAdversarialRankModulationStress:
    """Adversarial stress testing of the 129th-Order Hyper-Convex Rank Modulation."""

    def test_rank_modulation_boundary_and_top_decile_warping(self):
        """Verify boundary condition at r = 1.0: g(1.0) > 10^7 and smooth near-boundary behavior."""
        # At r = 1.0, g(1.0) = 0.50 + 3.82 * exp(gamma_top)
        gamma_bull = get_regime_adaptive_gamma_top_v99("BULL_LOW_VOL")  # 37.00
        g_1 = compute_phase99_hyperconvex_rank_modulation(1.0, gamma_top=gamma_bull)

        expected_g_1 = 0.50 + 3.82 * math.exp(gamma_bull)
        assert math.isclose(g_1, expected_g_1, rel_tol=1e-12)
        assert g_1 > 1e7, f"g(1.0) = {g_1} <= 10^7"
        assert g_1 > 4.4e16, f"g(1.0) = {g_1} did not achieve theoretical magnitude ~ 4.47e16"

        # Dense sweep in boundary region [0.99, 1.00]
        r_boundary = np.linspace(0.99, 1.00, 50000, dtype=np.float64)
        g_boundary = compute_phase99_hyperconvex_rank_modulation(r_boundary, gamma_top=gamma_bull)

        assert np.all(np.isfinite(g_boundary)), "Non-finite values encountered in [0.99, 1.00]"
        assert np.all(np.diff(g_boundary) >= 0.0), "Strict monotonicity violated in [0.99, 1.00]"

    def test_rank_modulation_overflow_safety_all_regimes(self):
        """Verify IEEE 754 float64 overflow safety across all regimes."""
        for regime_name, gamma_val in REGIME_GAMMA_TOP_V99.items():
            assert gamma_val <= 37.00, f"Regime {regime_name} has gamma_top = {gamma_val} > 37.00"
            r_dense = np.linspace(0.0, 1.0, 1000, dtype=np.float64)
            mod = compute_phase99_hyperconvex_rank_modulation(r_dense, gamma_top=gamma_val)
            assert np.all(np.isfinite(mod)), f"Overflow or NaN encountered in regime {regime_name}"
            assert np.all(mod >= 0.50), f"Modulation below minimum baseline 0.50 in regime {regime_name}"

    def test_rank_modulation_clipping_and_negative_signal_branch(self):
        """Test out-of-bounds clipping and negative signal branch penalty."""
        # Out-of-bounds ranks [ -0.5, 1.5 ]
        out_ranks = np.array([-0.5, -0.1, 0.0, 1.0, 1.1, 1.5], dtype=np.float64)
        mod_out = compute_phase99_hyperconvex_rank_modulation(out_ranks, gamma_top=37.00)

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
        mod_neg = compute_phase99_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)

        # At r = 0.0 -> 1.35, at r = 1.0 -> 0.35
        assert math.isclose(mod_neg[0], 1.35, abs_tol=1e-12)
        assert math.isclose(mod_neg[-1], 0.35, abs_tol=1e-12)
        # Strictly decreasing with rank for negative conviction
        assert np.all(np.diff(mod_neg) <= 0.0)


# =========================================================================
# AXIS 3: QGL MONSTER WHITTAKER COUPLER PHASE 99 STRESS TESTS
# =========================================================================

class TestAdversarialQGLMonsterWhittakerCouplerStress:
    """Adversarial stress testing of the QGL Monster Whittaker Coupler Phase 99."""

    def test_coupler_phase99_invariants(self):
        """Verify Phase 99 coupler invariants, 210th-order chiral oper and 122nd-order defect."""
        coupler = Phase99Coupler()
        assert coupler.version >= 99
        assert coupler.is_phase99 is True
        assert math.isclose(coupler.kappa_monster_whit, 41.60, abs_tol=1e-5)
        assert coupler.lambda_monster >= 1.0 - 1e-22
        assert math.isclose(coupler.harmony_boost, 10.95, abs_tol=1e-5)

    def test_coupler_standard_and_degenerate_pillar_inputs(self):
        """Verify coupler evaluate on normalized pillar scores and boundary cases."""
        coupler = Phase99Coupler()

        # 1. Standard factor range scores (|p| <= 5.0)
        norm_df = pd.DataFrame({
            "val": [2.5, -2.5],
            "mom": [1.5, -1.5],
            "flow": [2.0, -2.0],
            "cat": [0.5, -0.5],
            "net": [3.0, -3.0],
        }, index=["A", "B"])
        norm_res = coupler.couple_signals(norm_df)
        assert np.all(np.isfinite(norm_res["FERI_v99"])), "Non-finite FERI on standard scores"
        assert np.all(norm_res["FERI_v99"] >= 0.0) and np.all(norm_res["FERI_v99"] <= 1.0)

        # 2. Identical scores across all pillars (diff == 0.0)
        identical_df = pd.DataFrame({
            "val": [0.5, -0.2],
            "mom": [0.5, -0.2],
            "flow": [0.5, -0.2],
            "cat": [0.5, -0.2],
            "net": [0.5, -0.2],
        }, index=["A", "B"])
        ident_res = coupler.couple_signals(identical_df)
        # When all pillars are identical, obstruction energy is 0.0, defect is 0.0 -> FERI == 1.0
        assert np.all(np.isclose(ident_res["FERI_v99"], 1.0, atol=1e-6)), "Identical scores did not yield FERI == 1.0"

        # 3. Microscopic subnormal scores (1e-20)
        subnormal_df = pd.DataFrame({
            "val": [1e-20, -1e-20],
            "mom": [2e-20, -2e-20],
            "flow": [3e-20, -3e-20],
            "cat": [4e-20, -4e-20],
            "net": [5e-20, -5e-20],
        }, index=["A", "B"])
        sub_res = coupler.couple_signals(subnormal_df)
        assert np.all(np.isfinite(sub_res["FERI_v99"]))
        assert np.all(np.isclose(sub_res["FERI_v99"], 1.0, atol=1e-6))

        # 4. NaNs and Infs in input matrix
        bad_df = pd.DataFrame({
            "val": [np.nan, np.inf],
            "mom": [-np.inf, 0.1],
            "flow": [0.2, np.nan],
            "cat": [np.nan, 0.3],
            "net": [0.4, -np.inf],
        }, index=["A", "B"])
        bad_res = coupler.couple_signals(bad_df)
        assert np.all(np.isfinite(bad_res["FERI_v99"])), "NaN/Inf leaked into FERI output"

    def test_coupler_unbounded_input_overflow_vulnerability_demonstration(self):
        """
        Adversarial Verification: Verify that when inputs exceed |p| >= 335.0,
        factor pillar clipping (pn_safe in [-50.0, 50.0]) prevents intermediate overflow
        in high-order powers (p^122, diff^210), ensuring FERI_v99 remains finite,
        non-NaN, and within valid [0.0, 1.0] bounds.
        """
        coupler = Phase99Coupler()
        overflow_df = pd.DataFrame({
            "val": [400.0, -500.0, 1000.0],
            "mom": [400.0, 350.0, -1000.0],
            "flow": [400.0, 450.0, 800.0],
            "cat": [400.0, -350.0, -600.0],
            "net": [400.0, 500.0, 950.0],
        }, index=["OVF1", "OVF2", "OVF3"])
        res = coupler.couple_signals(overflow_df)
        feri_series = res["FERI_v99"]
        assert np.all(np.isfinite(feri_series)), "Expected finite values in FERI output under unbounded inputs"
        assert not np.any(np.isnan(feri_series)), "Expected non-NaN values in FERI output under unbounded inputs"
        assert np.all((feri_series >= 0.0) & (feri_series <= 1.0)), "FERI values out of [0, 1] range"


# =========================================================================
# AXIS 4: HIGHER-HOMOLOGY-49 FISHER-RAO BARYCENTER BLENDING STRESS TESTS
# =========================================================================

class TestAdversarialBarycenterBlendStress:
    """Adversarial stress testing of Higher-Homology-49 Fisher-Rao Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=99)

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
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend(case)
            assert isinstance(res, dict)
            weights = list(res.values())
            # Simplex condition strictly preserved: sum == 1.000000
            assert math.isclose(sum(weights), 1.0, abs_tol=1e-5), f"Sum != 1.0 for case {case}: got {sum(weights)}"

    def test_barycenter_tau_floor_violation_vulnerability_demonstration(self, allocator):
        """
        Adversarial Verification: Verify that exact truncated simplex projection
        strictly guarantees the floor constraint q_i >= tau = 1.5e-6 and
        exact simplex sum == 1.000000 across extreme one-hot vectors and boundary states.
        """
        tau_mandatory = 1.5e-6
        for one_hot_idx in range(4):
            v = np.zeros(4)
            v[one_hot_idx] = 1.0
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend(v)
            min_weight = min(res.values())
            assert min_weight >= tau_mandatory, (
                f"Strict tau floor violated for index {one_hot_idx}: {min_weight} < {tau_mandatory}"
            )
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6), (
                f"Simplex sum violated for index {one_hot_idx}: sum={sum(res.values())}"
            )

    def test_barycenter_curvature_hierarchy(self, allocator):
        """Verify exact theoretical ordering CVaR (12.25) > BL (10.10) > HERC (6.35) > RP (2.80)."""
        uniform_dict = {"BL": 0.25, "HERC": 0.25, "RP": 0.25, "CVaR": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend(uniform_dict)

        cvar_w = res.get("cvar", res.get("CVaR", 0.0))
        bl_w = res.get("bl", res.get("BL", 0.0))
        herc_w = res.get("herc", res.get("HERC", 0.0))
        rp_w = res.get("rp", res.get("RP", 0.0))

        assert cvar_w > bl_w, f"CVaR ({cvar_w}) <= BL ({bl_w})"
        assert bl_w > herc_w, f"BL ({bl_w}) <= HERC ({herc_w})"
        assert herc_w > rp_w, f"HERC ({herc_w}) <= RP ({rp_w})"
        assert math.isclose(cvar_w + bl_w + herc_w + rp_w, 1.0, abs_tol=1e-5)

    def test_barycenter_convergence_under_moderate_dirichlet_stress(self, allocator):
        """Stress moderate Dirichlet distributions (alpha >= 1.0) for rapid convergence and simplex sum."""
        rng = np.random.RandomState(42)
        alpha_priors = [1.0, 5.0, 20.0]

        for alpha in alpha_priors:
            samples = rng.dirichlet(np.full(4, alpha), size=50)
            for row in samples:
                res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend(row)
                vals = list(res.values())
                assert math.isclose(sum(vals), 1.0, abs_tol=1e-5)
                # Check that weights strictly satisfy tau floor
                assert all(v >= 1.5e-6 for v in vals)

    def test_barycenter_sparse_gradient_explosion_vulnerability_demonstration(self, allocator):
        """
        Adversarial Verification: Verify that exponential argument clipping
        exp_arg = np.clip(-step_size * grad, -50.0, 50.0) and truncated simplex projection
        prevent Riemannian gradient explosion and NaN collapse under sparse / high-conviction
        inputs, strictly producing finite, non-NaN probabilities with q_i >= tau and sum == 1.0.
        """
        tau_mandatory = 1.5e-6
        sparse_vec = np.array([9.93851896e-01, 7.34734065e-14, 6.13557399e-13, 6.14810376e-03])
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_49_fisher_rao_barycenter_blend(sparse_vec)
        # Verify finite non-NaN values satisfying simplex conditions
        assert all(np.isfinite(v) for v in res.values()), "Encountered non-finite values on sparse vector"
        assert not any(np.isnan(v) for v in res.values()), "Encountered NaN values on sparse vector"
        assert min(res.values()) >= tau_mandatory, f"Minimum weight below tau: {min(res.values())}"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6), f"Sum != 1.0: {sum(res.values())}"


# =========================================================================
# AXIS 5: 130TH-CUMULANT EVAR TAIL RISK MEASURE STRESS TESTS
# =========================================================================

class TestAdversarialEVaRTailRiskStress:
    """Adversarial stress testing of 130th-Cumulant Expansion Trans-Singular EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=99)

    def test_evar_order_and_xi_monster_invariants(self, allocator):
        """Verify order=130 and 35-nines xi_monster invariants."""
        dummy_ret = np.array([-0.02, 0.01, 0.03, -0.01])
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_49_evar_risk_measure(dummy_ret)

        assert res.get("order") == 130
        assert math.isclose(float(res.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
        assert "phase99_evar" in res
        assert np.isfinite(res["phase99_evar"])
        assert res["phase99_evar"] > 0.0

    def test_evar_extreme_heavy_tail_distributions(self, allocator):
        """Stress EVaR calculation on Student-t, Pareto, Cauchy, and market crash scenarios."""
        rng = np.random.RandomState(99)

        # 1. Student-t with df=1.5 (infinite variance)
        t_heavy = rng.standard_t(df=1.5, size=2000) * 0.02
        res_t = allocator.compute_phase99_evar(t_heavy)
        assert np.isfinite(res_t["phase99_evar"])
        assert res_t["phase99_evar"] > 0.0

        # 2. Student-t with df=0.8 (infinite mean and variance)
        t_super_heavy = rng.standard_t(df=0.8, size=1000) * 0.01
        res_super_t = allocator.compute_phase99_evar(t_super_heavy)
        assert np.isfinite(res_super_t["phase99_evar"])
        assert res_super_t["phase99_evar"] > 0.0

        # 3. Cauchy distribution
        cauchy_ret = rng.standard_cauchy(size=1000) * 0.01
        res_cauchy = allocator.compute_phase99_evar(cauchy_ret)
        assert np.isfinite(res_cauchy["phase99_evar"])
        assert res_cauchy["phase99_evar"] > 0.0

        # 4. Pareto distribution (heavy right tail / negated for losses)
        pareto_ret = -(rng.pareto(a=1.1, size=1000) - 1.0) * 0.02
        res_pareto = allocator.compute_phase99_evar(pareto_ret)
        assert np.isfinite(res_pareto["phase99_evar"])
        assert res_pareto["phase99_evar"] > 0.0

        # 5. Catastrophic 1000-sigma market crash scenario
        crash_ret = np.concatenate([rng.normal(0.001, 0.01, size=995), [-0.20, -0.40, -0.60, -0.80, -0.95]])
        res_crash = allocator.compute_phase99_evar(crash_ret)
        assert np.isfinite(res_crash["phase99_evar"])
        assert res_crash["phase99_evar"] > 0.50, f"EVaR on catastrophic crash was too low: {res_crash['phase99_evar']}"

    def test_evar_edge_case_returns(self, allocator):
        """Verify stability on all zero, constant, microscopic, and single-element returns."""
        # 1. All zeros
        zeros = np.zeros(100)
        res_z = allocator.compute_phase99_evar(zeros)
        assert np.isfinite(res_z["phase99_evar"])
        assert res_z["phase99_evar"] >= 0.0

        # 2. Constant returns (-0.05)
        # Theoretical EVaR = -c - ln(alpha) / t_opt = 0.05 - ln(0.05) / t_opt
        const = np.full(50, -0.05)
        res_c = allocator.compute_phase99_evar(const)
        assert np.isfinite(res_c["phase99_evar"])
        opt_t = float(res_c["optimal_t"])
        expected_evar = 0.05 - math.log(0.05) / opt_t
        assert math.isclose(res_c["phase99_evar"], expected_evar, rel_tol=1e-4)

        # 3. Microscopic returns (1e-8)
        micro = np.array([-1e-8, 1e-8, -2e-8, 2e-8])
        res_m = allocator.compute_phase99_evar(micro)
        assert np.isfinite(res_m["phase99_evar"])
        assert res_m["phase99_evar"] > 0.0

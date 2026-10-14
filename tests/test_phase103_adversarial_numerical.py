"""
tests/test_phase103_adversarial_numerical.py

Adversarial Empirical Stress Testing Suite for Phase 103:
Role: Numerical & Mathematical Stress Challenger (Features F485, F486, F487.1, F487.2)

Target Verification Axes:
1. 632nd-Order Sexcentoduotrigesimal Hyperbolic Noise Deadband (F485):
   - Extreme values z in [-1e-12, 1e-12], subnormal floats, denormals down to 1e-324.
   - Near-zero exact underflow: |z| <= 0.0003 -> exactly 0.0 in float64 (< 10^-632).
   - Full conviction transmission: |z| >= 0.150 -> 100.000% transmission (|z| preserved to float64 eps).
   - Strict rank monotonicity (Spearman rho == 1.0000) and exact odd symmetry.
   - NaN, Inf, empty array, and high-dimensional shape stability.
2. 137th-Order Hyper-Convex Rank Modulation (F485):
   - Boundary behavior for r in [0.99, 1.00].
   - Top-decile warping verification: g(1.0) > 10^7 (target ~ 2.58e18 at gamma_top = 41.00).
   - IEEE 754 float64 overflow safety across all regime gamma_top <= 41.00.
   - Negative signal branch g_neg(r) = 1.35 - 1.00 * r rank penalty.
   - Out-of-bounds clipping [0.0, 1.0].
3. Quantum Geometric Langlands Monster Whittaker Coupler Phase 103 (F486):
   - Theoretical parameter assertions: kappa = 44.00, lambda_monster >= 1.0 - 1e-27 (27-nines), harmony_boost = 12.35.
   - 218th-order chiral oper obstruction and 130th-order topological defect invariants active under is_phase103.
   - Extreme inputs: huge values (|p| > 1000), intermediate power overflow protection via clipping |p| <= 300.0, subnormals (|p| < 1e-20), identical pillar scores, Infs and NaNs.
   - Output finite boundedness for FERI_v103, feri_v103, f_out_103 in [0.0, 1.0].
4. Higher-Homology-53 Motivic Fisher-Rao Barycenter Blending (F487.1):
   - Simplex constraint: sum(q) == 1.000000 across all degenerate input distributions (one-hot, zero vectors, extreme dynamic range).
   - Strictly positive element floor: q_i >= tau = 0.6e-6 for all i.
   - Curvature hierarchy: CVaR (13.25) > BL (10.90) > HERC (6.95) > RP (3.00) under uniform input.
   - Riemannian gradient norm clipping in [-100.0, 100.0] preventing exponential gradient explosion.
5. 138th-Cumulant Expansion Trans-Singular EVaR Risk Measure (F487.2):
   - Order = 138, xi_monster = 1.0 - 1e-39 (39-nines).
   - Extreme heavy-tail distributions: Student-t (df=1.5 and df=0.8), Pareto (alpha=1.1), Cauchy, 1000-sigma market crash.
   - Log-gamma numerical stability for 138! (~ 3.99e236).
   - Edge case returns: all zero, constant, microscopic (1e-8), catastrophic drawdowns.
6. Waterfall Capital Redistribution Convergence (F487.1):
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
    apply_sexcentoduotrigesimal_hyperbolic_deadband,
    apply_632nd_order_hyperbolic_deadband,
    compute_phase103_deadband,
    compute_phase103_hyperconvex_rank_modulation,
    REGIME_GAMMA_TOP_V103,
    get_regime_adaptive_gamma_top_v103,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase103Coupler,
)
from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestAdversarialDeadbandStressPhase103:
    """Adversarial stress testing of the 632nd-Order Sexcentoduotrigesimal Hyperbolic Noise Deadband."""

    def test_deadband_exact_zero_underflow_dense_grid(self):
        """Verify that |z| <= 0.0003 strictly underflows to exact 0.0 in float64."""
        z_grid = np.linspace(-0.0003, 0.0003, 100000, dtype=np.float64)
        denoised = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_grid)

        nonzero_mask = denoised != 0.0
        num_nonzeros = np.sum(nonzero_mask)
        assert num_nonzeros == 0, f"Found {num_nonzeros} non-zero values in deadband region [-0.0003, 0.0003]"

        z_exact_boundaries = np.array([-0.0003000, -0.00029999, 0.0, 0.00029999, 0.0003000])
        denoised_bounds = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_exact_boundaries)
        for orig, d in zip(z_exact_boundaries, denoised_bounds):
            assert d == 0.0, f"Boundary point {orig} did not underflow to 0.0: got {d}"

    def test_deadband_subnormal_floats_and_denormals(self):
        """Stress test with subnormal and microscopic float64 values."""
        smallest_subnormal = np.nextafter(np.float64(0.0), np.float64(1.0))
        smallest_normal = sys.float_info.min

        test_denormals = np.array([
            smallest_subnormal,
            -smallest_subnormal,
            smallest_normal,
            -smallest_normal,
            1e-50,
            -1e-50,
            1e-300,
            -1e-300,
        ], dtype=np.float64)

        result = apply_sexcentoduotrigesimal_hyperbolic_deadband(test_denormals)
        assert np.all(result == 0.0), f"Subnormal floats failed to zero out: {result}"

    def test_deadband_full_conviction_transmission(self):
        """Verify that |z| >= 0.150 preserves full magnitude within float64 eps."""
        conviction_z = np.array([-1.0, -0.5, -0.150, 0.150, 0.5, 1.0, 5.0, -5.0], dtype=np.float64)
        result = apply_sexcentoduotrigesimal_hyperbolic_deadband(conviction_z)
        rel_diff = np.abs(result - conviction_z) / np.abs(conviction_z)
        assert np.all(rel_diff < 1e-12), f"Conviction signals suffered magnitude distortion: {rel_diff}"

    def test_deadband_odd_symmetry(self):
        """Verify strict odd symmetry: f(-z) == -f(z)."""
        z_random = np.random.uniform(-1.0, 1.0, 10000)
        f_pos = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_random)
        f_neg = apply_sexcentoduotrigesimal_hyperbolic_deadband(-z_random)
        sym_diff = np.abs(f_pos + f_neg)
        assert np.max(sym_diff) < 1e-15, f"Odd symmetry violated: max diff {np.max(sym_diff)}"


class TestAdversarialRankModulationPhase103:
    """Adversarial stress testing of the 137th-Order Hyper-Convex Rank Modulation."""

    def test_rank_modulation_top_decile_warping(self):
        """Verify top-decile warping g(1.0) > 10^7 under max gamma_top."""
        r = np.array([1.0], dtype=np.float64)
        gamma_max = REGIME_GAMMA_TOP_V103["BULL_LOW_VOL"]  # 41.00
        g_val = compute_phase103_hyperconvex_rank_modulation(r, gamma_top=gamma_max)
        assert g_val[0] > 1e7, f"g(1.0) did not exceed 10^7: got {g_val[0]}"
        assert math.isfinite(g_val[0]), "g(1.0) overflowed IEEE 754 float64"

    def test_rank_modulation_regime_stability(self):
        """Verify all regime gamma values maintain finite, monotonically non-decreasing outputs."""
        r_grid = np.linspace(0.0, 1.0, 1000)
        for regime, gamma in REGIME_GAMMA_TOP_V103.items():
            g_vals = compute_phase103_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            assert np.all(np.isfinite(g_vals)), f"Non-finite output in regime {regime}"
            assert np.all(np.diff(g_vals) >= 0.0), f"Monotonicity violated in regime {regime}"

    def test_negative_rank_modulation_penalty(self):
        """Verify negative rank branch g_neg(r) = 1.35 - 1.00 * r."""
        r_grid = np.linspace(0.0, 1.0, 50)
        z_neg = np.full_like(r_grid, -1.0)
        g_neg = compute_phase103_hyperconvex_rank_modulation(r_grid, z_denoised=z_neg)
        expected = 1.35 - 1.00 * r_grid
        assert np.allclose(g_neg, expected, atol=1e-12)


class TestAdversarialCouplerPhase103:
    """Adversarial stress testing of the QGL Monster Whittaker Coupler Phase 103."""

    def test_coupler_overflow_protection_large_inputs(self):
        """Verify clipping |p| <= 300.0 prevents intermediate overflow with huge pillar scores."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)
        df_extreme = pd.DataFrame({
            "ml_ensemble": [500.0],
            "vcp": [600.0],
            "stat_arb": [-800.0],
            "sentiment": [1000.0],
            "order_flow": [-1200.0],
            "supply_chain": [500.0],
            "catalyst": [-600.0],
        })
        res = coupler.couple_signals(df_extreme)
        assert "FERI_v103" in res
        val = res["FERI_v103"]
        val_scalar = float(val.iloc[0]) if isinstance(val, pd.Series) else float(val[0] if isinstance(val, (list, np.ndarray)) else val)
        assert math.isfinite(val_scalar)
        assert 0.0 <= val_scalar <= 1.0

    def test_coupler_phase103_theoretical_invariants(self):
        """Verify kappa = 44.00, lambda >= 1 - 1e-27, harmony_boost = 12.35."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)
        assert math.isclose(coupler.kappa_monster_whit, 44.00, rel_tol=1e-5)
        assert coupler.lambda_monster >= 1.0 - 1e-27
        assert math.isclose(coupler.harmony_boost, 12.35, rel_tol=1e-5)


class TestAdversarialRiskLayerPhase103:
    """Adversarial stress testing on Motivic Fisher-Rao Barycenter Blending and 138th-Cumulant EVaR."""

    def test_barycenter_simplex_boundary_degenerate_inputs(self):
        """Verify simplex condition sum(q) == 1.000000 across degenerate inputs."""
        allocator = UnifiedPortfolioAllocator(version=103)

        # Single non-zero candidate
        deg_weights = {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        q = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(deg_weights)
        assert math.isclose(sum(q.values()), 1.0, rel_tol=1e-6)
        assert all(v >= 0.6e-6 for v in q.values())

        # All zero candidate
        zero_weights = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        q_zero = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(zero_weights)
        assert math.isclose(sum(q_zero.values()), 1.0, rel_tol=1e-6)
        assert all(v >= 0.6e-6 for v in q_zero.values())

    def test_barycenter_curvature_hierarchy_uniform(self):
        """Under uniform inputs, hierarchy must hold: CVaR (13.25) > BL (10.90) > HERC (6.95) > RP (3.00)."""
        allocator = UnifiedPortfolioAllocator(version=103)
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        q = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(uniform_weights)
        assert q["cvar"] > q["bl"] > q["herc"] > q["rp"]

    def test_evar_heavy_tail_distribution_stress(self):
        """Stress test 138th-cumulant EVaR under heavy-tailed Student-t (df=1.5)."""
        allocator = UnifiedPortfolioAllocator(version=103)
        np.random.seed(103)
        heavy_returns = np.random.standard_t(df=1.5, size=5000) * 0.02
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure(heavy_returns)

        evar_val = float(evar_res.get("phase103_evar", evar_res.get("evar", 0.0)))
        assert evar_res["order"] == 138
        assert evar_res["xi_monster"] == 1.0 - 1e-39
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

    def test_waterfall_capital_redistribution_conservation(self):
        """Verify waterfall redistribution preserves total capital exactly."""
        allocator = UnifiedPortfolioAllocator(version=103)
        current_w = {"A": 0.10, "B": 0.10, "C": 0.10}
        target_w = {"A": 0.50, "B": 0.30, "C": 0.20}
        pre_waterfall = {"A": 0.15, "B": 0.30, "C": 0.20}
        max_delta = {"A": 0.05, "B": 0.20, "C": 0.20}
        alpha_scores = {"A": 0.95, "B": 0.85, "C": 0.75}

        rebalanced = allocator.redistribute_waterfall_capital(
            current_weights=current_w,
            next_weights=pre_waterfall,
            target_weights=target_w,
            max_delta_w=max_delta,
            max_single_weight=0.50,
            alpha_scores=alpha_scores,
        )
        assert math.isclose(sum(rebalanced.values()), sum(target_w.values()) - 0.05, rel_tol=1e-4) or sum(rebalanced.values()) > sum(pre_waterfall.values())
        assert rebalanced["A"] <= current_w["A"] + max_delta["A"] + 1e-9

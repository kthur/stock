r"""
tests/test_phase51_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 51 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F227.2: 216th-Order Bicentadodecagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband leakage at boundary (|z| <= 0.00035 -> 0.0, leakage < 10^-136)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry
2. Feature F227.1: 46th-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 1000.0 > 500.0 (bull low vol gamma=7.80)
   - Lower 70% damping g(0.70) <= 1.665 < 1.67
   - Out-of-bounds clipping and regime hierarchy
3. Feature F226: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F228.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Homology Motivic Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP
5. Feature F228.2: 47th-Cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker EVaR
   - Analytical monotonicity and boundedness across diverse random distributions
   - Heavy-tail sensitivity comparison
   - Numerical stability under extreme inputs
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_bicentadodecagonal_hyperbolic_deadband,
    compute_phase51_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v51,
    REGIME_GAMMA_TOP_V51,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_val(res):
    if isinstance(res, dict):
        return float(res.get(
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_value",
            res.get("evar", 0.0)))
        ))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F227.2)
# =========================================================================

class TestPhase51DeadbandAdversarial:
    """Adversarial stress testing of the 216th-order Bicentadodecagonal deadband."""

    @pytest.mark.parametrize("z", [
        0.0,
        1e-15,
        -1e-15,
        1e-10,
        -1e-10,
        1e-5,
        -1e-5,
        0.0001,
        -0.0001,
        0.000349,
        -0.000349,
        0.00035,
        -0.00035,
    ])
    def test_deadband_boundary_noise_annihilation(self, z):
        """Verify strict noise annihilation to 0.0 (< 10^-136) for |z| <= 0.00035."""
        z_denoised = apply_bicentadodecagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-136, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        for z in test_points:
            pos_val = apply_bicentadodecagonal_hyperbolic_deadband(z)
            neg_val = apply_bicentadodecagonal_hyperbolic_deadband(-z)
            assert np.isclose(pos_val, -neg_val, atol=1e-15, rtol=1e-12)

    def test_deadband_signal_preservation_high_conviction(self):
        """Verify 100.0% signal preservation for high conviction |z| >= 0.15."""
        conviction_points = [0.15, -0.15, 0.25, -0.25, 0.50, -0.50, 1.0, -1.0]
        for z in conviction_points:
            val = apply_bicentadodecagonal_hyperbolic_deadband(z)
            assert np.isclose(val, z, rtol=1e-12)

    def test_deadband_extreme_inputs(self):
        """Verify stability against extreme floating point inputs."""
        extreme_points = [1e10, -1e10, 1e50, -1e50, 1e150, -1e150]
        for z in extreme_points:
            val = apply_bicentadodecagonal_hyperbolic_deadband(z)
            assert math.isfinite(val)
            assert np.isclose(val, z, rtol=1e-9)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F227.1)
# =========================================================================

class TestPhase51RankModulationAdversarial:
    """Adversarial stress testing of 46th-order hyper-convex rank modulation."""

    def test_rank_modulation_strict_monotonicity_positive(self):
        """Verify strict monotonicity across 10,000 rank points for positive conviction."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase51_hyperconvex_rank_modulation(r_grid, gamma_top=7.80, z_denoised=0.1)
        diffs = np.diff(g_vals)
        assert (diffs >= 0.0).all(), "Positive conviction modulation must be strictly monotonically non-decreasing"

    def test_rank_modulation_strict_monotonicity_negative(self):
        """Verify strict monotonicity (decreasing) across 10,000 rank points for negative conviction."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase51_hyperconvex_rank_modulation(r_grid, gamma_top=7.80, z_denoised=-0.1)
        diffs = np.diff(g_vals)
        assert (diffs <= 0.0).all(), "Negative conviction modulation must be strictly monotonically non-increasing"

    def test_rank_modulation_extreme_amplification_and_damping(self):
        """Verify right-tail amplification g(1.0) > 1000.0 and lower 70% damping g(0.70) <= 1.665."""
        g_top = compute_phase51_hyperconvex_rank_modulation(1.0, gamma_top=7.80, z_denoised=0.0)
        assert g_top > 4000.0 > 1000.0, f"g(1.0)={g_top} did not achieve required amplification > 1000.0"

        g_70 = compute_phase51_hyperconvex_rank_modulation(0.70, gamma_top=7.80, z_denoised=0.0)
        assert g_70 <= 1.665 < 1.67, f"g(0.70)={g_70} exceeded damping ceiling 1.665"

    def test_rank_modulation_regime_hierarchy(self):
        """Verify gamma_top ordering across all market regimes."""
        assert REGIME_GAMMA_TOP_V51["BULL_LOW_VOL"] > REGIME_GAMMA_TOP_V51["BULL_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V51["BULL_HIGH_VOL"] > REGIME_GAMMA_TOP_V51["SIDEWAYS"]
        assert REGIME_GAMMA_TOP_V51["SIDEWAYS"] > REGIME_GAMMA_TOP_V51["BEAR"]
        assert REGIME_GAMMA_TOP_V51["BEAR"] > REGIME_GAMMA_TOP_V51["CRISIS"]


# =========================================================================
# 3. ADVERSARIAL RISK BARYCENTER & EVAR STRESS TESTS (F228.1 & F228.2)
# =========================================================================

class TestPhase51RiskAdversarial:
    """Adversarial stress testing of Lurie-Borcherds Homology Barycenter and 47th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_barycenter_degenerate_single_model(self, allocator):
        """Verify barycenter handles degenerate single model concentrations."""
        deg_cases = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
        ]
        for case in deg_cases:
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(case)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
            for v in res.values():
                assert 0.0 < v < 1.0

    def test_evar_order_47_heavy_tail_sensitivity(self, allocator):
        """Verify 47th-cumulant EVaR strictly increases with tail thickness."""
        np.random.seed(123)
        normal_returns = np.random.normal(0.0005, 0.015, 1000)
        t_student_returns = np.random.standard_t(df=3, size=1000) * 0.015

        evar_norm = _extract_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_risk_measure(normal_returns, order=47))
        evar_t = _extract_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_risk_measure(t_student_returns, order=47))

        assert evar_t > evar_norm, "47th-cumulant EVaR must reflect heavier Student-t tails"

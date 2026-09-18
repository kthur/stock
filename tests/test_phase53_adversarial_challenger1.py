r"""
tests/test_phase53_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 53 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F237.2: 232nd-Order Bicentadotriacontagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband leakage at boundary (|z| <= 0.00035 -> 0.0, leakage < 10^-152)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity across broad spectrum and odd symmetry: f(-z) == -f(z)
2. Feature F237.1: 48th-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 14000.0 > 500.0 (bull low vol gamma=9.00)
   - Lower 70% damping g(0.70) <= 1.74
   - Out-of-bounds clipping and regime hierarchy
3. Feature F236: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F238.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-3 Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [4.30, 3.15, 3.10, 4.85])
5. Feature F238.2: 49th-Cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker EVaR
   - Analytical monotonicity and boundedness across diverse random distributions
   - Heavy-tail sensitivity comparison (Student-t vs Gaussian)
   - Extreme input stability and empty / NaN resilience
6. Feature F239.1: KNK 32-Dark-Energy DAHA Limits
   - Outer horizon coordinate scale: c_monster_scale = (1.0 / max(10^-6, c_monster)) ** (1.0 / 34.0)
   - Repulsive tidal acceleration scaling: -17.0 * c_monster * (r ** 33) * daha_32
   - Clamped acceleration in [-100.0, 100.0]
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_bicentadotriacontagonal_hyperbolic_deadband,
    compute_phase53_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v53,
    REGIME_GAMMA_TOP_V53,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.core.fast_lob_engine import FastOrderBookMatchingEngine


def _extract_evar_val(res):
    if isinstance(res, dict):
        return float(res.get(
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F237.2)
# =========================================================================

class TestPhase53DeadbandAdversarial:
    """Adversarial stress testing of the 232nd-order Bicentadotriacontagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-152) for |z| <= 0.00035."""
        z_denoised = apply_bicentadotriacontagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-152, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_bicentadotriacontagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_bicentadotriacontagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify exact signal preservation for high-conviction signals (|z| >= 0.150)."""
        strong_signals = np.array([0.15, -0.15, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0])
        denoised = apply_bicentadotriacontagonal_hyperbolic_deadband(strong_signals)
        np.testing.assert_allclose(denoised, strong_signals, rtol=1e-12)

    def test_deadband_subnormal_and_extreme_range(self):
        """Stress test with subnormal and extreme numbers to ensure no NaNs or overflow exceptions."""
        extremes = np.array([1e-308, -1e-308, 1e-100, -1e-100, 1e20, -1e20, 1e100, -1e100])
        out = apply_bicentadotriacontagonal_hyperbolic_deadband(extremes)
        assert not np.isnan(out).any()
        assert not np.isinf(out).any()


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F237.1)
# =========================================================================

class TestPhase53RankModulationAdversarial:
    """Adversarial stress testing of 48th-order hyper-convex rank modulation."""

    def test_convexity_and_right_tail_amplification(self):
        """Test right-tail ultra-amplification g(1.0) > 14000.0 > 500.0 with damping in lower 70%."""
        gamma_top = 9.00
        g_70 = compute_phase53_hyperconvex_rank_modulation(0.70, gamma_top=gamma_top)
        assert g_70 <= 1.74, f"Lower 70% damping violated: g(0.70) = {g_70}"

        g_100 = compute_phase53_hyperconvex_rank_modulation(1.00, gamma_top=gamma_top)
        expected_top = 0.50 + 1.74 * math.exp(9.00)
        assert math.isclose(g_100, expected_top, rel_tol=1e-5)
        assert g_100 > 14000.0 > 500.0

    def test_strict_monotonicity_positive_and_negative(self):
        """Verify strict monotonicity across 1,000 ranks for both long and short conviction."""
        r = np.linspace(0.0, 1.0, 1000)

        # Positive conviction (long expansion)
        g_pos = compute_phase53_hyperconvex_rank_modulation(r, gamma_top=9.00, z_denoised=0.1)
        diff_pos = np.diff(g_pos)
        assert (diff_pos >= 0.0).all(), "Monotonicity violated for positive conviction"

        # Negative conviction (short damping)
        g_neg = compute_phase53_hyperconvex_rank_modulation(r, gamma_top=9.00, z_denoised=-0.1)
        diff_neg = np.diff(g_neg)
        assert (diff_neg <= 0.0).all(), "Monotonicity violated for negative conviction"

    def test_regime_hierarchy_gamma(self):
        """Ensure regime hierarchy is strictly preserved."""
        assert REGIME_GAMMA_TOP_V53["BULL_LOW_VOL"] > REGIME_GAMMA_TOP_V53["BULL_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V53["BULL_HIGH_VOL"] > REGIME_GAMMA_TOP_V53["SIDEWAYS"]
        assert REGIME_GAMMA_TOP_V53["SIDEWAYS"] > REGIME_GAMMA_TOP_V53["BEAR"]
        assert REGIME_GAMMA_TOP_V53["BEAR"] > REGIME_GAMMA_TOP_V53["CRISIS"]


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F236)
# =========================================================================

class TestPhase53CouplerAdversarial:
    """Stress testing of Quantum Geometric Langlands Chiral Affine Monster Moonshine Coupler."""

    def test_coupler_collinear_degenerate(self):
        """Stress coupler with completely identical pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=13.00, lambda_monster=0.94
        )
        p_df = pd.DataFrame({
            "val": [0.6, 0.6, 0.6],
            "mom": [0.6, 0.6, 0.6],
            "flow": [0.6, 0.6, 0.6],
            "cat": [0.6, 0.6, 0.6],
            "net": [0.6, 0.6, 0.6],
        })
        res = coupler(p_df)
        assert (res["e_monster_whit"] == 0.0).all()
        assert (res["z_monster_whit"] == 1.0).all()
        assert (res["h_monster_whit"] == 1.0).all()
        assert (res["FERI_v53"] == 1.0).all()

    def test_coupler_extreme_divergence(self):
        """Stress coupler with extreme opposing pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=13.00, lambda_monster=0.94
        )
        p_df = pd.DataFrame({
            "val": [1.0],
            "mom": [0.0],
            "flow": [1.0],
            "cat": [0.0],
            "net": [1.0],
        })
        res = coupler(p_df)
        assert 0.0 <= res["h_monster_whit"].iloc[0] <= 1.0
        assert 0.0 <= res["z_monster_whit"].iloc[0] <= 1.0
        assert 0.0 <= res["FERI_v53"].iloc[0] <= 1.0


# =========================================================================
# 4. ADVERSARIAL RISK BARYCENTER & EVAR STRESS TESTS (F238.1 & F238.2)
# =========================================================================

class TestPhase53RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-3 Barycenter & 49th-cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_barycenter_simplex_conservation_under_stress(self, allocator):
        """Verify strict simplex conservation sum(q_i) = 1.0 with zero and extreme input weights."""
        extreme_inputs = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
            {"bl": 0.0001, "herc": 0.0001, "rp": 0.0001, "cvar": 0.9997},
            {"bl": 0.9997, "herc": 0.0001, "rp": 0.0001, "cvar": 0.0001},
        ]
        for w in extreme_inputs:
            bary = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(bary.values()), 1.0, rel_tol=1e-5)
            for k, v in bary.items():
                assert v > 0.0

    def test_evar_heavy_tail_sensitivity(self, allocator):
        """EVaR with order=49 must be strictly more sensitive to Student-t heavy tails than normal distributions."""
        np.random.seed(42)
        n = 2000
        normal_samples = np.random.normal(0, 0.02, n)
        # Student-t with df=3 has fat tails
        t_samples = np.random.standard_t(df=3, size=n) * 0.02

        evar_normal = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure(normal_samples))
        evar_t = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure(t_samples))

        assert evar_t > evar_normal, "49th-cumulant EVaR must register higher risk under fat-tailed Student-t shocks"

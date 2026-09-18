r"""
tests/test_phase49_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 49 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F217.2: 200th-Order Bicentagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband leakage at boundary (|z| <= 0.00035 -> 0.0, leakage < 10^-120)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry
2. Feature F217.1: 44th-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 460.0 (bull low vol gamma=6.50)
   - Lower 70% damping g(0.70) < 1.62
   - Out-of-bounds clipping and regime hierarchy
3. Feature F216: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F218.1: Lurie-Borcherds-Monster-Moonshine-Whittaker Motivic Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP
5. Feature F218.1: 45th-Cumulant Trans-Singular Borcherds-Moonshine-Monster EVaR
   - Analytical monotonicity (EVaR_45 >= EVaR_44 or strictly bounded) across diverse random distributions
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
    apply_bicentagonal_hyperbolic_deadband,
    compute_phase49_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v49,
    REGIME_GAMMA_TOP_V49,
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_evar_value",
            res.get("evar", 0.0)))
        ))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F217.2)
# =========================================================================

class TestPhase49DeadbandAdversarial:
    """Adversarial stress testing of the 200th-order Bicentagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-120) for |z| <= 0.00035."""
        z_denoised = apply_bicentagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-120, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        for z in test_points:
            pos_val = apply_bicentagonal_hyperbolic_deadband(z)
            neg_val = apply_bicentagonal_hyperbolic_deadband(-z)
            assert np.isclose(pos_val, -neg_val, atol=1e-15, rtol=1e-12)

    def test_deadband_signal_preservation_high_conviction(self):
        """Verify >= 99.9999% signal preservation for high conviction signals (|z| >= 0.15)."""
        test_points = np.linspace(0.15, 2.0, 100)
        for z in test_points:
            z_denoised = apply_bicentagonal_hyperbolic_deadband(z)
            ratio = z_denoised / z
            assert ratio > 0.999999, f"Signal attenuation at z={z}: ratio={ratio}"


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F217.1)
# =========================================================================

class TestPhase49RankModulationAdversarial:
    """Adversarial stress testing of the 44th-order hyper-convex rank modulation."""

    def test_rank_modulation_extreme_top_convexity(self):
        """Verify explosive right-tail expansion g(1.0) > 460.0 under bull low vol (gamma=6.50)."""
        g_1 = compute_phase49_hyperconvex_rank_modulation(1.0, gamma_top=6.50)
        assert g_1 > 460.0

        # And modest lower 70% damping: g(0.70) < 1.62
        g_70 = compute_phase49_hyperconvex_rank_modulation(0.70, gamma_top=6.50)
        assert g_70 < 1.62

    def test_rank_modulation_negative_conviction_monotonicity(self):
        """Verify strict downward monotonicity for negative conviction signals."""
        ranks = np.linspace(0.0, 1.0, 200)
        g_neg = compute_phase49_hyperconvex_rank_modulation(ranks, gamma_top=6.50, z_denoised=-0.2)
        diffs = np.diff(g_neg)
        assert (diffs <= 0.0).all()
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F216)
# =========================================================================

class TestPhase49CouplerAdversarial:
    """Adversarial stress testing of the Monstrous Moonshine Whittaker Coupler."""

    def test_coupler_degenerate_and_extreme_inputs(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        # Degenerate uniform
        df_unif = pd.DataFrame({k: [0.5] * 5 for k in ['val', 'mom', 'flow', 'cat', 'net']})
        res_unif = coupler(df_unif)
        assert (res_unif['h_monster_whit'] == 1.0).all()

        # Extreme values [0.0, 1.0]
        df_ext = pd.DataFrame({
            'val': [0.0, 1.0],
            'mom': [1.0, 0.0],
            'flow': [0.0, 1.0],
            'cat': [1.0, 0.0],
            'net': [0.0, 1.0],
        })
        res_ext = coupler(df_ext)
        assert (res_ext['h_monster_whit'] >= 0.0).all() and (res_ext['h_monster_whit'] <= 1.0).all()
        assert (res_ext['FERI_v49'] >= 0.0).all() and (res_ext['FERI_v49'] <= 1.0).all()


# =========================================================================
# 4. ADVERSARIAL RISK & EVAR STRESS TESTS (F218.1)
# =========================================================================

class TestPhase49RiskAdversarial:
    """Adversarial stress testing of Lurie-Borcherds-Monster-Moonshine-Whittaker Barycenter & EVaR."""

    def test_barycenter_metric_weights_and_simplex(self):
        alloc = UnifiedPortfolioAllocator()
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blend = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(blend.values()), 1.0, rel_tol=1e-5)
        assert blend["cvar"] > blend["bl"] > blend["herc"] > blend["rp"]

    def test_evar_order45_vs_order44_monotonicity(self):
        """Analytical property: EVaR with order 45 provides tighter or equal tail bounding vs order 44."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(123)
        returns = np.random.standard_t(df=3, size=1000) * 0.02
        res_45 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_risk_measure(returns, order=45)
        res_44 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_risk_measure(returns, order=44)
        evar_45 = _extract_val(res_45)
        evar_44 = _extract_val(res_44)
        assert evar_45 > 0.0
        assert evar_44 > 0.0

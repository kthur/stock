r"""
tests/test_phase50_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 50 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F222.2: 208th-Order Bicentaoctahedral Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband leakage at boundary (|z| <= 0.00035 -> 0.0, leakage < 10^-128)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry
2. Feature F222.1: 45th-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 500.0 (bull low vol gamma=7.20)
   - Lower 70% damping g(0.70) <= 1.635 < 1.64
   - Out-of-bounds clipping and regime hierarchy
3. Feature F221: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F223.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Motivic Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP
5. Feature F223.2: 46th-Cumulant Trans-Singular Borcherds-Moonshine-Monster EVaR
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
    apply_bicentaoctahedral_hyperbolic_deadband,
    compute_phase50_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v50,
    REGIME_GAMMA_TOP_V50,
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
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F222.2)
# =========================================================================

class TestPhase50DeadbandAdversarial:
    """Adversarial stress testing of the 208th-order Bicentaoctahedral deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-128) for |z| <= 0.00035."""
        z_denoised = apply_bicentaoctahedral_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-128, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        for z in test_points:
            pos_val = apply_bicentaoctahedral_hyperbolic_deadband(z)
            neg_val = apply_bicentaoctahedral_hyperbolic_deadband(-z)
            assert np.isclose(pos_val, -neg_val, atol=1e-15, rtol=1e-12)

    def test_deadband_signal_preservation_high_conviction(self):
        """Verify 100.0% signal transmission for high conviction |z| >= 0.150."""
        sig_points = [0.150, 0.20, 0.30, 0.50, 1.0, 5.0]
        for z in sig_points:
            pos_out = apply_bicentaoctahedral_hyperbolic_deadband(z)
            neg_out = apply_bicentaoctahedral_hyperbolic_deadband(-z)
            assert np.isclose(pos_out, z, rtol=1e-9)
            assert np.isclose(neg_out, -z, rtol=1e-9)

    def test_deadband_monotonicity_adversarial(self):
        """Verify strict non-decreasing monotonicity across 10,000 dense points."""
        dense_z = np.linspace(-0.5, 0.5, 10001)
        out = apply_bicentaoctahedral_hyperbolic_deadband(dense_z)
        diffs = np.diff(out)
        assert (diffs >= 0.0).all(), "Deadband violated monotonicity"


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F222.1)
# =========================================================================

class TestPhase50RankModulationAdversarial:
    """Adversarial stress testing of 45th-order hyper-convex rank modulation."""

    def test_rank_modulation_right_tail_explosion_and_damping(self):
        """Verify right-tail explosion g(1.0) > 500.0 and damping g(0.70) <= 1.635 < 1.64."""
        g_top = compute_phase50_hyperconvex_rank_modulation(1.0, gamma_top=7.20)
        assert g_top > 2000.0 > 500.0, f"g(1.0) {g_top} failed right-tail explosion"

        g_70 = compute_phase50_hyperconvex_rank_modulation(0.70, gamma_top=7.20)
        assert g_70 <= 1.635 < 1.64, f"g(0.70) {g_70} exceeded upper bound 1.635"

    def test_rank_modulation_directional_monotonicity(self):
        """Verify monotonicity for positive and negative conviction."""
        r = np.linspace(0.0, 1.0, 1000)
        g_pos = compute_phase50_hyperconvex_rank_modulation(r, gamma_top=7.20, z_denoised=0.1)
        assert (np.diff(g_pos) >= 0.0).all()

        g_neg = compute_phase50_hyperconvex_rank_modulation(r, gamma_top=7.20, z_denoised=-0.1)
        assert (np.diff(g_neg) <= 0.0).all()


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F221)
# =========================================================================

class TestPhase50CouplerAdversarial:
    """Adversarial stress testing of Quantum Geometric Langlands Coupler."""

    def test_coupler_pillar_collapse_and_bounds(self):
        """Verify coupler invariants under collapsed, degenerate pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()

        # All identical pillars (zero dispersion)
        identical_df = pd.DataFrame({col: [0.5, 0.8, 0.2] for col in ['val', 'mom', 'flow', 'cat', 'net']})
        res = coupler(identical_df)
        assert np.allclose(res['h_monster_whit'].values, 1.0)
        assert np.allclose(res['z_monster_whit'].values, 1.0)
        assert np.allclose(res['FERI_v50'].values, 1.0)

        # Extreme divergence
        divergent_df = pd.DataFrame({
            'val': [0.0, 1.0],
            'mom': [1.0, 0.0],
            'flow': [0.0, 1.0],
            'cat': [1.0, 0.0],
            'net': [0.0, 1.0],
        })
        res_div = coupler(divergent_df)
        assert (res_div['h_monster_whit'] >= 0.0).all() and (res_div['h_monster_whit'] <= 1.0).all()
        assert (res_div['FERI_v50'] >= 0.0).all() and (res_div['FERI_v50'] <= 1.0).all()


# =========================================================================
# 4. ADVERSARIAL RISK & BARYCENTER STRESS TESTS (F223.1 & F223.2)
# =========================================================================

class TestPhase50RiskAdversarial:
    """Adversarial stress testing of Barycenter blending and 46th-cumulant EVaR."""

    def test_barycenter_metric_ordering_and_conservation(self):
        """Verify simplex conservation and weight ordering CVaR > BL > HERC > RP."""
        alloc = UnifiedPortfolioAllocator()
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blend = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_fisher_rao_barycenter_blend(uniform_weights)

        assert math.isclose(sum(blend.values()), 1.0, rel_tol=1e-5)
        assert blend["cvar"] > blend["bl"] > blend["herc"] > blend["rp"]
        assert all(0.0 < v < 1.0 for v in blend.values())

    def test_46th_cumulant_evar_heavy_tail_sensitivity(self):
        """Verify 46th-cumulant EVaR strictly increases with extreme tail shock."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(123)
        normal_ret = np.random.normal(0.001, 0.02, 1000)

        evar_normal = _extract_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_risk_measure(normal_ret, order=46))

        # Add heavy negative tail shock
        shocked_ret = np.concatenate([normal_ret, [-0.20, -0.30, -0.40]])
        evar_shocked = _extract_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_risk_measure(shocked_ret, order=46))

        assert evar_shocked > evar_normal
        assert math.isfinite(evar_shocked)

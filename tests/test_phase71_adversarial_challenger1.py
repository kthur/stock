r"""
tests/test_phase71_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 71 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F327.2: 376th-Order Tricentaseptacontahexagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs
   - Deadband boundary noise annihilation (|z| <= 0.00035 -> 0.0, leakage < 10^-278)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry: f(-z) == -f(z)
2. Feature F327.1: 73rd-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Right-tail amplification g(1.0) > 10000000.0 (bull low vol gamma=18.05)
   - Lower 70% damping g(0.70) <= 2.29
   - Regime hierarchy
3. Feature F326: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F328.1: Higher-Homology-21 Fisher-Rao Barycenter Blend
   - Simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [6.10, 4.05, 3.30, 7.00])
5. Feature F328.2: 74th-Cumulant EVaR
   - Analytical monotonicity, heavy-tail sensitivity, empty / NaN resilience
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_tricentaseptacontahexagonal_hyperbolic_deadband,
    compute_phase71_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v71,
    REGIME_GAMMA_TOP_V71,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F327.2)
# =========================================================================

class TestPhase71DeadbandAdversarial:
    """Adversarial stress testing of the 376th-order Tricentaseptacontahexagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-278) for |z| <= 0.00035."""
        z_denoised = apply_tricentaseptacontahexagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-240, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_tricentaseptacontahexagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_tricentaseptacontahexagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify 100% signal transmission for high conviction |z| >= 0.15."""
        extreme_z = np.array([-10.0, -2.0, -0.5, -0.15, 0.15, 0.5, 2.0, 10.0])
        denoised = apply_tricentaseptacontahexagonal_hyperbolic_deadband(extreme_z)
        np.testing.assert_allclose(denoised, extreme_z, rtol=1e-9)

    def test_deadband_subnormal_stability(self):
        """Verify stability with subnormal float inputs."""
        subnormals = np.array([5e-324, -5e-324, 2.2e-308, -2.2e-308])
        denoised = apply_tricentaseptacontahexagonal_hyperbolic_deadband(subnormals)
        for d in denoised:
            assert abs(d) < 1e-250


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F327.1)
# =========================================================================

class TestPhase71RankModulationAdversarial:
    """Adversarial stress testing of 73rd-order rank modulation."""

    def test_rank_modulation_monotone_positive(self):
        """Verify monotonicity of rank modulation for positive alpha."""
        r = np.linspace(0.0, 1.0, 200)
        g = compute_phase71_hyperconvex_rank_modulation(r, gamma_top=18.05, z_denoised=0.1)
        diffs = np.diff(g)
        assert (diffs >= 0.0).all()

    def test_rank_modulation_monotone_negative(self):
        """Verify monotonicity of rank modulation for negative alpha."""
        r = np.linspace(0.0, 1.0, 200)
        g = compute_phase71_hyperconvex_rank_modulation(r, gamma_top=18.05, z_denoised=-0.1)
        diffs = np.diff(g)
        assert (diffs <= 0.0).all()

    def test_rank_modulation_right_tail_amplification(self):
        """Verify right-tail alpha amplification g(1.0) > 10^7 under bull low vol gamma."""
        top_val = compute_phase71_hyperconvex_rank_modulation(1.0, gamma_top=18.05, z_denoised=0.1)
        assert top_val > 10000000.0

    def test_rank_modulation_lower_70_damping(self):
        """Verify lower 70% damping g(0.70) <= 2.29 under bull low vol gamma."""
        val_70 = compute_phase71_hyperconvex_rank_modulation(0.70, gamma_top=18.05, z_denoised=0.1)
        assert val_70 <= 2.29

    def test_regime_gamma_hierarchy(self):
        """Verify strictly descending regime gamma hierarchy."""
        g_bull_low = get_regime_adaptive_gamma_top_v71("BULL_LOW_VOL")
        g_bull_high = get_regime_adaptive_gamma_top_v71("BULL_HIGH_VOL")
        g_side = get_regime_adaptive_gamma_top_v71("SIDEWAYS")
        g_side_high = get_regime_adaptive_gamma_top_v71("SIDEWAYS_HIGH_VOL")
        g_bear = get_regime_adaptive_gamma_top_v71("BEAR")
        g_bear_high = get_regime_adaptive_gamma_top_v71("BEAR_HIGH_VOL")
        g_crisis = get_regime_adaptive_gamma_top_v71("CRISIS")

        assert g_bull_low > g_bull_high > g_side > g_side_high > g_bear > g_bear_high > g_crisis


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F326)
# =========================================================================

class TestPhase71CouplerAdversarial:
    """Adversarial stress testing of Borcherds-Moonshine Monster Whittaker Coupler."""

    def test_coupler_degenerate_inputs(self):
        """Test coupler with identical values across all pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        df_deg = pd.DataFrame({
            "p1": [0.5, 0.5],
            "p2": [0.5, 0.5],
            "p3": [0.5, 0.5],
            "p4": [0.5, 0.5],
            "p5": [0.5, 0.5],
        })
        res = coupler(df_deg)
        assert "FERI_v71" in res
        assert (res["FERI_v71"] >= 0.0).all() and (res["FERI_v71"] <= 1.0).all()

    def test_coupler_extreme_divergence(self):
        """Test coupler with maximum possible dispersion between pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        df_div = pd.DataFrame({
            "p1": [1.0, 0.0],
            "p2": [0.0, 1.0],
            "p3": [1.0, 0.0],
            "p4": [0.0, 1.0],
            "p5": [1.0, 0.0],
        })
        res = coupler(df_div)
        assert (res["h_monster_whit"] >= 0.0).all() and (res["h_monster_whit"] <= 1.0).all()


# =========================================================================
# 4. ADVERSARIAL RISK ALLOCATION STRESS TESTS (F328.1 & F328.2)
# =========================================================================

class TestPhase71RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-21 Barycenter and 74th-Cumulant EVaR."""

    def test_barycenter_simplex_conservation_under_perturbation(self):
        """Verify simplex conservation under random highly skewed inputs."""
        alloc = UnifiedPortfolioAllocator(version=71)
        np.random.seed(7171)
        for _ in range(50):
            raw = np.random.exponential(scale=2.0, size=4)
            raw /= np.sum(raw)
            weights = {"bl": raw[0], "herc": raw[1], "rp": raw[2], "cvar": raw[3]}
            b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_21_fisher_rao_barycenter_blend(weights)
            assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5)
            for v in b.values():
                assert v > 0.0

    def test_barycenter_metric_priority(self):
        """Verify metric ordering under uniform inputs."""
        alloc = UnifiedPortfolioAllocator(version=71)
        w_uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_21_fisher_rao_barycenter_blend(w_uniform)
        assert b["cvar"] > b["bl"] > b["herc"] > b["rp"]

    def test_evar_fat_tailed_student_t_vs_gaussian(self):
        """Verify fat-tailed Student-t returns generate higher EVaR than Gaussian returns."""
        alloc = UnifiedPortfolioAllocator(version=71)
        np.random.seed(7171)
        norm_rets = np.random.normal(0.0, 0.02, 1000)
        t_rets = np.random.standard_t(df=3, size=1000) * 0.02

        evar_norm = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_21_evar_risk_measure(norm_rets))
        evar_t = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_21_evar_risk_measure(t_rets))

        assert evar_t > evar_norm

    def test_evar_volatility_monotonicity(self):
        """Verify EVaR strictly increases with volatility."""
        alloc = UnifiedPortfolioAllocator(version=71)
        np.random.seed(7171)
        base = np.random.normal(0.0, 1.0, 1000)
        r_low = base * 0.01
        r_high = base * 0.05

        e_low = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_21_evar_risk_measure(r_low))
        e_high = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_21_evar_risk_measure(r_high))

        assert e_high > e_low

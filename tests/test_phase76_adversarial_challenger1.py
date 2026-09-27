r"""
tests/test_phase76_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 76 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F351: 416th-Order Tetracosihexadecagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs
   - Deadband boundary noise annihilation (|z| <= 0.00035 -> 0.0, leakage < 10^-308)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry: f(-z) == -f(z)
2. Feature F351: 83rd-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Right-tail amplification g(1.0) > 10000000.0 (bull low vol gamma=19.80)
   - Lower 70% damping g(0.70) <= 2.50
   - Regime hierarchy
3. Feature F352: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
   - Output gating for FERI_v76 and f_out_76
4. Feature F353.1: Higher-Homology-26 Fisher-Rao Barycenter Blend
   - Simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [6.60, 4.30, 3.05, 7.75])
5. Feature F353.2: 84th-Cumulant EVaR
   - Analytical monotonicity, heavy-tail sensitivity, empty / NaN resilience
   - Order=84 and xi_monster=0.99999999999999998 verification
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_tetracosihexadecagonal_hyperbolic_deadband,
    compute_phase76_deadband,
    apply_phase76_deadband,
    phase76_deadband,
    compute_phase76_hyperconvex_rank_modulation,
    compute_phase76_rank_warping,
    compute_phase76_rank_modulation,
    phase76_rank_modulation,
    get_regime_adaptive_gamma_top_v76,
    REGIME_GAMMA_TOP_V76,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase76Coupler,
    Phase76WhittakerDrinfeldCoupler,
    Phase76BorcherdsMoonshineCoupler,
    Phase76MonsterWhittakerCoupler,
    compute_phase76_coupling,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F351)
# =========================================================================

class TestPhase76DeadbandAdversarial:
    """Adversarial stress testing of the 416th-order Tetracosihexadecagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-308) for |z| <= 0.00035."""
        z_denoised = apply_tetracosihexadecagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-250, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_aliases_and_wrapper(self):
        """Verify deadband aliases produce identical results."""
        z_test = 0.0002
        ref = apply_tetracosihexadecagonal_hyperbolic_deadband(z_test)
        assert compute_phase76_deadband(z_test) == ref
        assert apply_phase76_deadband(z_test) == ref
        assert phase76_deadband(z_test) == ref

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_tetracosihexadecagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_tetracosihexadecagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify 100% signal transmission for high conviction |z| >= 0.15."""
        extreme_z = np.array([-10.0, -2.0, -0.5, -0.15, 0.15, 0.5, 2.0, 10.0])
        denoised = apply_tetracosihexadecagonal_hyperbolic_deadband(extreme_z)
        np.testing.assert_allclose(denoised, extreme_z, rtol=1e-9)

    def test_deadband_subnormal_stability(self):
        """Verify stability with subnormal float inputs."""
        subnormals = np.array([5e-324, -5e-324, 2.2e-308, -2.2e-308])
        denoised = apply_tetracosihexadecagonal_hyperbolic_deadband(subnormals)
        for d in denoised:
            assert abs(d) < 1e-250 or d == 0.0

    def test_deadband_exact_boundary_0035(self):
        """Verify smooth C^inf transition at exact boundary |z| = 0.035."""
        z_bound = 0.035
        f_pos = apply_tetracosihexadecagonal_hyperbolic_deadband(z_bound)
        f_neg = apply_tetracosihexadecagonal_hyperbolic_deadband(-z_bound)
        expected_val = 0.035 * math.tanh(1.0)
        assert math.isclose(f_pos, expected_val, rel_tol=1e-7)
        assert math.isclose(f_neg, -expected_val, rel_tol=1e-7)
        assert 0.0 < f_pos < z_bound

    def test_deadband_nan_inf_handling(self):
        """Verify clean handling of NaN and Inf without crashing."""
        arr = np.array([np.nan, np.inf, -np.inf, 0.035, 0.0])
        res = apply_tetracosihexadecagonal_hyperbolic_deadband(arr)
        assert np.isnan(res[0])
        assert np.isposinf(res[1])
        assert np.isneginf(res[2])
        assert math.isclose(res[3], 0.035 * math.tanh(1.0), rel_tol=1e-7)
        assert res[4] == 0.0

    def test_deadband_extreme_noise_stress(self):
        """Verify 100,000 extreme noise samples in [-0.00035, 0.00035] annihilated to 0.0."""
        np.random.seed(42)
        noise = np.random.uniform(-0.00035, 0.00035, size=100000)
        res = apply_tetracosihexadecagonal_hyperbolic_deadband(noise)
        assert np.all(res == 0.0)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F351)
# =========================================================================

class TestPhase76RankModulationAdversarial:
    """Adversarial stress testing of 83rd-order rank modulation."""

    def test_rank_modulation_monotone_positive(self):
        """Verify monotonicity of rank modulation for positive alpha."""
        r = np.linspace(0.0, 1.0, 200)
        g = compute_phase76_hyperconvex_rank_modulation(r, gamma_top=19.80, z_denoised=0.1)
        diffs = np.diff(g)
        assert (diffs >= 0.0).all()

    def test_rank_modulation_monotone_negative(self):
        """Verify monotonicity of rank modulation for negative alpha."""
        r = np.linspace(0.0, 1.0, 200)
        g = compute_phase76_hyperconvex_rank_modulation(r, gamma_top=19.80, z_denoised=-0.1)
        diffs = np.diff(g)
        assert (diffs <= 0.0).all()

    def test_rank_modulation_right_tail_amplification(self):
        """Verify right-tail alpha amplification g(1.0) > 10^7 under bull low vol gamma."""
        top_val = compute_phase76_hyperconvex_rank_modulation(1.0, gamma_top=19.80, z_denoised=0.1)
        assert top_val > 10000000.0

    def test_rank_modulation_lower_70_damping(self):
        """Verify lower 70% damping g(0.70) <= 2.50 under bull low vol gamma."""
        val_70 = compute_phase76_hyperconvex_rank_modulation(0.70, gamma_top=19.80, z_denoised=0.1)
        assert val_70 <= 2.50

    def test_rank_modulation_aliases(self):
        """Verify rank modulation aliases return matching values."""
        r = 0.85
        ref = compute_phase76_hyperconvex_rank_modulation(r, gamma_top=16.10)
        assert compute_phase76_rank_warping(r, gamma_top=16.10) == ref
        assert compute_phase76_rank_modulation(r, gamma_top=16.10) == ref
        assert phase76_rank_modulation(r, gamma_top=16.10) == ref

    def test_regime_gamma_hierarchy(self):
        """Verify strictly descending regime gamma hierarchy for Phase 76."""
        g_bull_low = get_regime_adaptive_gamma_top_v76("BULL_LOW_VOL")
        g_bull_high = get_regime_adaptive_gamma_top_v76("BULL_HIGH_VOL")
        g_side = get_regime_adaptive_gamma_top_v76("SIDEWAYS")
        g_side_high = get_regime_adaptive_gamma_top_v76("SIDEWAYS_HIGH_VOL")
        g_bear = get_regime_adaptive_gamma_top_v76("BEAR")
        g_bear_high = get_regime_adaptive_gamma_top_v76("BEAR_HIGH_VOL")
        g_crisis = get_regime_adaptive_gamma_top_v76("CRISIS")

        assert g_bull_low == 19.80
        assert g_bull_high == 16.10
        assert g_side == 12.35
        assert g_side_high == 8.20
        assert g_bear == 4.30
        assert g_bear_high == 3.50
        assert g_crisis == 2.30
        assert g_bull_low > g_bull_high > g_side > g_side_high > g_bear > g_bear_high > g_crisis

    def test_rank_modulation_negative_ranks(self):
        """Verify negative ranks (< 0) are safely clipped to boundary conviction."""
        neg_ranks = np.array([-10.0, -2.5, -1.0, -0.5, -1e-6])
        res_neg_pos_z = compute_phase76_hyperconvex_rank_modulation(neg_ranks, gamma_top=19.80, z_denoised=0.1)
        res_neg_neg_z = compute_phase76_hyperconvex_rank_modulation(neg_ranks, gamma_top=19.80, z_denoised=-0.1)
        assert np.all(res_neg_pos_z == 0.50)
        assert np.all(res_neg_neg_z == 1.35)

    def test_rank_modulation_ranks_greater_than_one(self):
        """Verify ranks > 1.0 are safely clipped to peak conviction g(1.0)."""
        large_ranks = np.array([1.00001, 1.05, 1.5, 2.0, 10.0, 100.0])
        res = compute_phase76_hyperconvex_rank_modulation(large_ranks, gamma_top=19.80, z_denoised=0.1)
        val_1 = compute_phase76_hyperconvex_rank_modulation(1.0, gamma_top=19.80, z_denoised=0.1)
        assert np.all(res == val_1)
        assert val_1 > 1e7

    def test_rank_modulation_10000_point_monotonicity(self):
        """Verify monotonicity across 10,000 sorted random points."""
        np.random.seed(42)
        r = np.sort(np.random.uniform(-0.5, 1.5, size=10000))
        g = compute_phase76_hyperconvex_rank_modulation(r, gamma_top=19.80, z_denoised=0.1)
        diffs = np.diff(g)
        assert np.all(diffs >= -1e-12)



# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F352)
# =========================================================================

class TestPhase76CouplerAdversarial:
    """Adversarial stress testing of Borcherds-Moonshine Monster Whittaker Coupler for Phase 76."""

    def test_coupler_parameters_and_defaults(self):
        """Verify default Phase 76 coupler parameters."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.kappa_monster_whit == 26.90
        assert coupler.lambda_monster == 0.999999998
        assert coupler.version == 76

    def test_coupler_degenerate_inputs(self):
        """Test coupler with identical values across all pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=76)
        df_deg = pd.DataFrame({
            "p1": [0.5, 0.5],
            "p2": [0.5, 0.5],
            "p3": [0.5, 0.5],
            "p4": [0.5, 0.5],
            "p5": [0.5, 0.5],
        })
        res = coupler(df_deg)
        assert "FERI_v76" in res
        assert "f_out_76" in res
        assert (res["FERI_v76"] >= 0.0).all() and (res["FERI_v76"] <= 1.0).all()
        assert (res["f_out_76"] >= 0.0).all() and (res["f_out_76"] <= 1.0).all()

    def test_coupler_extreme_divergence(self):
        """Test coupler with maximum possible dispersion between pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=76)
        df_div = pd.DataFrame({
            "p1": [1.0, 0.0],
            "p2": [0.0, 1.0],
            "p3": [1.0, 0.0],
            "p4": [0.0, 1.0],
            "p5": [1.0, 0.0],
        })
        res = coupler(df_div)
        assert (res["h_monster_whit"] >= 0.0).all() and (res["h_monster_whit"] <= 1.0).all()
        assert (res["z_monster_whit"] >= 0.0).all() and (res["z_monster_whit"] <= 1.0).all()
        assert (res["FERI_v76"] >= 0.0).all() and (res["FERI_v76"] <= 1.0).all()

    def test_coupler_aliases(self):
        """Verify alias classes for Phase 76 coupler."""
        assert Phase76Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase76WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase76BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase76MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler


# =========================================================================
# 4. ADVERSARIAL RISK ALLOCATION STRESS TESTS (F353.1 & F353.2)
# =========================================================================

class TestPhase76RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-26 Barycenter and 84th-Cumulant EVaR."""

    def test_barycenter_simplex_conservation_under_perturbation(self):
        """Verify simplex conservation under random highly skewed inputs."""
        alloc = UnifiedPortfolioAllocator(version=76)
        np.random.seed(7676)
        for _ in range(50):
            raw = np.random.exponential(scale=2.0, size=4)
            raw /= np.sum(raw)
            weights = {"bl": raw[0], "herc": raw[1], "rp": raw[2], "cvar": raw[3]}
            b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(weights)
            assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5)
            for v in b.values():
                assert v > 0.0

    def test_barycenter_metric_priority(self):
        """Verify metric ordering under uniform inputs: CVaR > BL > HERC > RP (mu=[6.60, 4.30, 3.05, 7.75])."""
        alloc = UnifiedPortfolioAllocator(version=76)
        w_uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(w_uniform)
        assert b["cvar"] > b["bl"] > b["herc"] > b["rp"]

    def test_evar_fat_tailed_student_t_vs_gaussian(self):
        """Verify fat-tailed Student-t returns generate higher EVaR than Gaussian returns."""
        alloc = UnifiedPortfolioAllocator(version=76)
        np.random.seed(7676)
        norm_rets = np.random.normal(0.0, 0.02, 1000)
        t_rets = np.random.standard_t(df=3, size=1000) * 0.02

        evar_norm = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(norm_rets))
        evar_t = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(t_rets))

        assert evar_t > evar_norm

    def test_evar_volatility_monotonicity(self):
        """Verify EVaR strictly increases with volatility."""
        alloc = UnifiedPortfolioAllocator(version=76)
        np.random.seed(7676)
        base = np.random.normal(0.0, 1.0, 1000)
        r_low = base * 0.01
        r_high = base * 0.05

        e_low = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(r_low))
        e_high = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(r_high))

        assert e_high > e_low

    def test_evar_parameters_and_resilience(self):
        """Verify EVaR returns order=84 and xi_monster=0.99999999999999998, and handles empty inputs."""
        alloc = UnifiedPortfolioAllocator(version=76)
        res = alloc.compute_phase76_evar(np.random.normal(0, 0.01, 100))
        assert res["order"] == 84
        assert res["xi_monster"] == 0.99999999999999998

        empty_res = alloc.compute_phase76_evar([])
        assert _extract_evar_val(empty_res) == 0.0

    def test_barycenter_degenerate_dirichlet_weights(self):
        """Verify Higher-Homology-26 Barycenter with 50 degenerate Dirichlet distributions."""
        alloc = UnifiedPortfolioAllocator(version=76)
        np.random.seed(42)
        for _ in range(50):
            d = np.random.dirichlet([0.005, 0.005, 0.005, 0.005])
            w = {"bl": d[0], "herc": d[1], "rp": d[2], "cvar": d[3]}
            b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5)
            for v in b.values():
                assert v > 0.0 and math.isfinite(v)

    def test_barycenter_near_zero_initial_weights(self):
        """Verify Higher-Homology-26 Barycenter with near-zero (1e-25) initial weights."""
        alloc = UnifiedPortfolioAllocator(version=76)
        near_zero = {"bl": 1e-25, "herc": 1e-25, "rp": 1e-25, "cvar": 1e-25}
        b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(near_zero)
        assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5)
        assert b["cvar"] > b["bl"] > b["herc"] > b["rp"]

    def test_evar_heavy_tailed_pareto(self):
        """Verify 84th-cumulant EVaR with heavy-tailed Pareto distributions."""
        alloc = UnifiedPortfolioAllocator(version=76)
        np.random.seed(42)
        pareto_heavy = -np.random.pareto(a=1.5, size=50000) * 0.01
        pareto_light = -np.random.pareto(a=3.0, size=50000) * 0.01
        e_heavy = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(pareto_heavy))
        e_light = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(pareto_light))
        assert math.isfinite(e_heavy) and e_heavy > 0.0
        assert math.isfinite(e_light) and e_light > 0.0
        assert e_heavy > e_light

    def test_evar_zero_variance_returns(self):
        """Verify 84th-cumulant EVaR with zero variance returns."""
        alloc = UnifiedPortfolioAllocator(version=76)
        zero_rets = np.zeros(1000)
        e_zero = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(zero_rets))
        assert math.isfinite(e_zero) and e_zero >= 0.0

    def test_evar_large_n_stability(self):
        """Verify 84th-cumulant EVaR on large N=100,000."""
        alloc = UnifiedPortfolioAllocator(version=76)
        rets_large = np.random.normal(-0.001, 0.02, size=100000)
        res = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(rets_large)
        e_val = _extract_evar_val(res)
        assert math.isfinite(e_val) and e_val > 0.0
        assert res["order"] == 84


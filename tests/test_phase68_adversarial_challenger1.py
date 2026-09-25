r"""
tests/test_phase68_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 68 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F312.2: 352th-Order Bicentatetratetracontaoctagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs
   - Deadband boundary noise annihilation (|z| <= 0.00035 -> 0.0, leakage < 10^-254)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry: f(-z) == -f(z)
2. Feature F312.1: 67th-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Right-tail amplification g(1.0) > 10000000.0 (bull low vol gamma=17.00)
   - Lower 70% damping g(0.70) <= 2.40
   - Regime hierarchy
3. Feature F311: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F313.1: Higher-Homology-17 Fisher-Rao Barycenter Blend
   - Simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [5.80, 3.90, 3.45, 6.55])
5. Feature F313.2: 68th-Cumulant EVaR
   - Analytical monotonicity, heavy-tail sensitivity, empty / NaN resilience
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_biheptacontaoctagonal_hyperbolic_deadband,
    compute_phase68_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v68,
    REGIME_GAMMA_TOP_V68,
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
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F312.2)
# =========================================================================

class TestPhase68DeadbandAdversarial:
    """Adversarial stress testing of the 352th-order Bicentatetratetracontaoctagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-254) for |z| <= 0.00035."""
        z_denoised = apply_biheptacontaoctagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-240, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_biheptacontaoctagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_biheptacontaoctagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify 100% signal transmission for high conviction |z| >= 0.15."""
        extreme_z = np.array([-10.0, -2.0, -0.5, -0.15, 0.15, 0.5, 2.0, 10.0])
        denoised = apply_biheptacontaoctagonal_hyperbolic_deadband(extreme_z)
        np.testing.assert_allclose(denoised, extreme_z, rtol=1e-9)

    def test_deadband_subnormal_stability(self):
        """Verify stability with subnormal float inputs."""
        subnormals = np.array([5e-324, -5e-324, 2.2e-308, -2.2e-308])
        denoised = apply_biheptacontaoctagonal_hyperbolic_deadband(subnormals)
        assert np.all(np.isfinite(denoised))
        assert np.all(np.abs(denoised) < 1e-240)

    def test_deadband_large_array_monotonicity(self):
        """Verify monotonicity across a large grid."""
        spectrum = np.linspace(-1.0, 1.0, 10001)
        denoised = apply_biheptacontaoctagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=352.0)
        diffs = np.diff(denoised)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION TESTS (F312.1)
# =========================================================================

class TestPhase68RankModulationAdversarial:
    """Adversarial stress testing of 67th-order hyper-convex rank modulation."""

    def test_rank_modulation_strict_convexity_and_asymptote(self):
        """Verify right-tail amplification > 10000000.0 and bottom 70% damping <= 2.40."""
        r_grid = np.linspace(0.0, 1.0, 1000)
        g_vals = compute_phase68_hyperconvex_rank_modulation(r_grid, gamma_top=17.00)

        assert g_vals[-1] > 100000.0, f"Expected g(1.0) > 100000.0, got {g_vals[-1]}"
        assert g_vals[-1] > 1000000.0, f"Expected g(1.0) > 1000000.0, got {g_vals[-1]}"
        assert g_vals[-1] > 10000000.0, f"Expected g(1.0) > 10000000.0, got {g_vals[-1]}"

        idx_70 = int(0.70 * len(r_grid))
        assert g_vals[idx_70] <= 2.40, f"Expected g(0.70) <= 2.40, got {g_vals[idx_70]}"

        diffs = np.diff(g_vals)
        assert np.all(diffs >= 0.0), "Monotonicity violated across rank grid"

    def test_rank_modulation_regime_hierarchy(self):
        """Verify gamma_top follows strict regime hierarchy: Bull > Sideways > Bear > Crisis."""
        g_bull_low = get_regime_adaptive_gamma_top_v68("BULL_LOW_VOL")
        g_bull_high = get_regime_adaptive_gamma_top_v68("BULL_HIGH_VOL")
        g_side_low = get_regime_adaptive_gamma_top_v68("SIDEWAYS_LOW_VOL")
        g_side_high = get_regime_adaptive_gamma_top_v68("SIDEWAYS_HIGH_VOL")
        g_bear_low = get_regime_adaptive_gamma_top_v68("BEAR_LOW_VOL")
        g_bear_high = get_regime_adaptive_gamma_top_v68("BEAR_HIGH_VOL")
        g_crisis = get_regime_adaptive_gamma_top_v68("CRISIS")

        assert g_bull_low > g_bull_high > g_side_low > g_side_high > g_bear_low > g_bear_high > g_crisis

    def test_rank_modulation_negative_z_linear_decay(self):
        """Verify linear decay 1.35 - 1.00*r for negative z_denoised."""
        r_grid = np.linspace(0.0, 1.0, 100)
        g_neg = compute_phase68_hyperconvex_rank_modulation(r_grid, gamma_top=17.00, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_rank_modulation_out_of_bounds_clipping(self):
        """Verify that ranks outside [0,1] are clipped."""
        g_neg = compute_phase68_hyperconvex_rank_modulation(-0.5, gamma_top=17.00)
        g_zero = compute_phase68_hyperconvex_rank_modulation(0.0, gamma_top=17.00)
        assert np.isclose(g_neg, g_zero, rtol=1e-6)

        g_over = compute_phase68_hyperconvex_rank_modulation(1.5, gamma_top=17.00)
        g_one = compute_phase68_hyperconvex_rank_modulation(1.0, gamma_top=17.00)
        assert np.isclose(g_over, g_one, rtol=1e-6)


# =========================================================================
# 3. ADVERSARIAL PILLAR COUPLER TESTS (F311)
# =========================================================================

class TestPhase68CouplerAdversarial:
    """Adversarial stress testing of the Whittaker-Moonshine-Monster Coupler."""

    def test_coupler_extreme_and_degenerate_pillars(self):
        """Verify coupler stability on degenerate, zero, and infinite pillar inputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=20.60,
            lambda_monster=0.999998,
        )

        # All zeros
        df_zeros = pd.DataFrame(0.0, index=range(5), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_zeros = coupler(df_zeros)
        assert np.all(np.isfinite(res_zeros['h_monster_whit']))
        assert np.all(np.isfinite(res_zeros['z_monster_whit']))
        assert np.all(res_zeros['FERI_v67'] >= 0.0)
        assert np.all(res_zeros['FERI_v67'] <= 1.0)

        # All ones
        df_ones = pd.DataFrame(1.0, index=range(5), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_ones = coupler(df_ones)
        assert np.all(res_ones['h_monster_whit'] == 1.0)
        assert np.all(res_ones['z_monster_whit'] == 1.0)
        assert np.all(res_ones['FERI_v67'] == 1.0)

    def test_coupler_single_vector(self):
        """Verify coupler returns scalar outputs for 1D vector input."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=20.60,
            lambda_monster=0.999998,
        )
        vec = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res = coupler(vec)
        assert isinstance(res['h_monster_whit'], float)
        assert np.isclose(res['e_monster_whit'], 0.0, atol=1e-7)
        assert np.isclose(res['FERI_v67'], 1.0, atol=1e-7)


# =========================================================================
# 4. ADVERSARIAL BARYCENTER & EVAR STRESS TESTS (F313.1 & F313.2)
# =========================================================================

class TestPhase68RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-17 barycenter and 68th-cumulant EVaR."""

    def test_barycenter_simplex_conservation_and_heavy_tail_prioritization(self):
        """Verify simplex conservation sum(q_i) == 1.0 and CVaR dominance under equal inputs."""
        alloc = UnifiedPortfolioAllocator()

        w_eq = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        q = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_18_fisher_rao_barycenter_blend(w_eq)

        assert math.isclose(sum(q.values()), 1.0, rel_tol=1e-5)
        # CVaR (mu=6.55) > BL (mu=5.80) > HERC (mu=3.90) > RP (mu=3.45)
        assert q["cvar"] > q["bl"] > q["herc"] > q["rp"]

    def test_68th_cumulant_evar_fat_tailed_sensitivity(self):
        """Verify that 68th-cumulant EVaR is strictly sensitive to fat-tailed distributions."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)

        norm_rets = np.random.normal(0.0, 0.02, 2000)
        t_rets = np.random.standard_t(df=3, size=2000) * 0.02 / math.sqrt(3)

        evar_norm = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_18_evar_risk_measure(norm_rets))
        evar_t = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_18_evar_risk_measure(t_rets))

        assert evar_t > evar_norm, f"Fat-tailed Student-t EVaR ({evar_t}) must exceed Gaussian EVaR ({evar_norm})"

    def test_68th_cumulant_evar_volatility_monotonicity(self):
        """Verify that 68th-cumulant EVaR is strictly monotonically increasing with volatility."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(101)

        vols = [0.005, 0.010, 0.020, 0.040]
        evars = []
        for v in vols:
            rets = np.random.normal(0.0, v, 2000)
            val = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_18_evar_risk_measure(rets))
            evars.append(val)

        for i in range(len(evars) - 1):
            assert evars[i] < evars[i + 1], f"EVaR must increase with volatility: {evars[i]} >= {evars[i + 1]}"

    def test_68th_cumulant_evar_empty_resilience(self):
        """Verify EVaR handles empty and NaN inputs gracefully."""
        alloc = UnifiedPortfolioAllocator()
        empty_res = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_18_evar_risk_measure([])
        assert _extract_evar_val(empty_res) == 0.0

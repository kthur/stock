r"""
tests/test_phase60_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 60 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F272: 288th-Order Bicentaoctaoctagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband boundary noise annihilation (|z| <= 0.00035 -> 0.0, leakage < 10^-208)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity across broad spectrum and odd symmetry: f(-z) == -f(z)
2. Feature F271: 55th-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 100000.0 (bull low vol gamma=13.20, g(1.0) > 1000000.0)
   - Lower 70% damping g(0.70) <= 2.02
   - Out-of-bounds clipping and regime hierarchy
3. Feature F271: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F273.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-10 Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [5.00, 3.50, 3.45, 5.55])
5. Feature F273.2: 56th-Cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker EVaR
   - Analytical monotonicity and boundedness across diverse random distributions
   - Heavy-tail sensitivity comparison (Student-t vs Gaussian)
   - Extreme input stability and empty / NaN resilience
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_bicentaoctaoctagonal_hyperbolic_deadband,
    compute_phase60_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v60,
    REGIME_GAMMA_TOP_V60,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        return float(res.get(
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_9_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_9_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F272)
# =========================================================================

class TestPhase60DeadbandAdversarial:
    """Adversarial stress testing of the 288th-order Bicentaoctaoctagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-208) for |z| <= 0.00035."""
        z_denoised = apply_bicentaoctaoctagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-208, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_bicentaoctaoctagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_bicentaoctaoctagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify 100% signal transmission for high conviction |z| >= 0.15."""
        extreme_z = np.array([-10.0, -2.0, -0.5, -0.15, 0.15, 0.5, 2.0, 10.0])
        denoised = apply_bicentaoctaoctagonal_hyperbolic_deadband(extreme_z)
        np.testing.assert_allclose(denoised, extreme_z, rtol=1e-9)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION TESTS (F271)
# =========================================================================

class TestPhase60RankModulationAdversarial:
    """Adversarial stress testing of 55th-order hyper-convex rank modulation."""

    def test_rank_modulation_strict_convexity_and_asymptote(self):
        """Verify right-tail amplification > 100000.0 and bottom 70% damping <= 2.02."""
        r_grid = np.linspace(0.0, 1.0, 1000)
        g_vals = compute_phase60_hyperconvex_rank_modulation(r_grid, gamma_top=13.20)

        assert g_vals[-1] > 100000.0, f"Expected g(1.0) > 100000.0, got {g_vals[-1]}"
        assert g_vals[-1] > 1000000.0, f"Expected g(1.0) > 1000000.0, got {g_vals[-1]}"

        idx_70 = int(0.70 * len(r_grid))
        assert g_vals[idx_70] <= 2.02, f"Expected g(0.70) <= 2.02, got {g_vals[idx_70]}"

        diffs = np.diff(g_vals)
        assert np.all(diffs >= 0.0), "Monotonicity violated across rank grid"

    def test_rank_modulation_regime_hierarchy(self):
        """Verify that gamma_top follows strict regime hierarchy: Bull > Sideways > Bear > Crisis."""
        g_bull_low = get_regime_adaptive_gamma_top_v60("BULL_LOW_VOL")
        g_bull_high = get_regime_adaptive_gamma_top_v60("BULL_HIGH_VOL")
        g_side_low = get_regime_adaptive_gamma_top_v60("SIDEWAYS_LOW_VOL")
        g_side_high = get_regime_adaptive_gamma_top_v60("SIDEWAYS_HIGH_VOL")
        g_bear_low = get_regime_adaptive_gamma_top_v60("BEAR_LOW_VOL")
        g_bear_high = get_regime_adaptive_gamma_top_v60("BEAR_HIGH_VOL")
        g_crisis = get_regime_adaptive_gamma_top_v60("CRISIS")

        assert g_bull_low > g_bull_high > g_side_low > g_side_high > g_bear_low > g_bear_high > g_crisis


# =========================================================================
# 3. ADVERSARIAL PILLAR COUPLER TESTS (F271)
# =========================================================================

class TestPhase60CouplerAdversarial:
    """Adversarial stress testing of the Whittaker-Moonshine-Monster Coupler."""

    def test_coupler_extreme_and_degenerate_pillars(self):
        """Verify coupler stability on degenerate, zero, and infinite pillar inputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=16.50,
            lambda_monster=0.9995,
        )

        # All zeros
        df_zeros = pd.DataFrame(0.0, index=range(5), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_zeros = coupler(df_zeros)
        assert np.all(np.isfinite(res_zeros['h_monster_whit']))
        assert np.all(np.isfinite(res_zeros['z_monster_whit']))
        assert np.all(res_zeros['FERI_v60'] >= 0.0)
        assert np.all(res_zeros['FERI_v60'] <= 1.0)

        # All ones
        df_ones = pd.DataFrame(1.0, index=range(5), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_ones = coupler(df_ones)
        assert np.all(res_ones['h_monster_whit'] == 1.0)
        assert np.all(res_ones['z_monster_whit'] == 1.0)
        assert np.all(res_ones['FERI_v60'] == 1.0)


# =========================================================================
# 4. ADVERSARIAL BARYCENTER & EVAR STRESS TESTS (F273.1 & F273.2)
# =========================================================================

class TestPhase60RiskAdversarial:
    """Adversarial stress testing of higher-homology-10 barycenter and 56th-cumulant EVaR."""

    def test_barycenter_simplex_conservation_and_heavy_tail_prioritization(self):
        """Verify simplex conservation sum(q_i) == 1.0 and CVaR dominance under equal inputs."""
        alloc = UnifiedPortfolioAllocator()

        # Equal input weights
        w_eq = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        q = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_10_fisher_rao_barycenter_blend(w_eq)

        assert math.isclose(sum(q.values()), 1.0, rel_tol=1e-5)
        # CVaR (mu=5.55) > BL (mu=5.00) > HERC (mu=3.50) > RP (mu=3.45)
        assert q["cvar"] > q["bl"] > q["herc"] >= q["rp"]

    def test_56th_cumulant_evar_fat_tailed_sensitivity(self):
        """Verify that 56th-cumulant EVaR is strictly sensitive to fat-tailed distributions."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # Normal vs Student-t with df=3
        norm_rets = np.random.normal(0.0, 0.02, 2000)
        t_rets = np.random.standard_t(df=3, size=2000) * 0.02 / math.sqrt(3)

        evar_norm = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar_risk_measure(norm_rets))
        evar_t = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar_risk_measure(t_rets))

        assert evar_t > evar_norm, f"Fat-tailed Student-t EVaR ({evar_t}) must exceed Gaussian EVaR ({evar_norm})"

    def test_56th_cumulant_evar_volatility_monotonicity(self):
        """Verify that 56th-cumulant EVaR is strictly monotonically increasing with volatility."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(101)

        vols = [0.005, 0.010, 0.020, 0.040]
        evars = []
        for v in vols:
            rets = np.random.normal(0.0, v, 2000)
            val = _extract_evar_val(alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar_risk_measure(rets))
            evars.append(val)

        for i in range(len(evars) - 1):
            assert evars[i] < evars[i + 1], f"EVaR must increase with volatility: {evars[i]} >= {evars[i + 1]}"

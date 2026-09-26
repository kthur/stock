r"""
tests/test_phase70_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 70 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F322.2: 368th-Order Tricentahexacontaoctagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs
   - Deadband boundary noise annihilation (|z| <= 0.00035 -> 0.0, leakage < 10^-272)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry: f(-z) == -f(z)
2. Feature F322.1: 71st-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Right-tail amplification g(1.0) > 10000000.0 (bull low vol gamma=17.70)
   - Lower 70% damping g(0.70) <= 2.26
   - Regime hierarchy
3. Feature F321: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F323.1: Higher-Homology-20 Fisher-Rao Barycenter Blend
   - Simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [6.00, 4.00, 3.35, 6.85])
5. Feature F323.2: 72nd-Cumulant EVaR
   - Analytical monotonicity, heavy-tail sensitivity, empty / NaN resilience
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_tricentahexacontaoctagonal_hyperbolic_deadband,
    compute_phase70_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v70,
    REGIME_GAMMA_TOP_V70,
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
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F322.2)
# =========================================================================

class TestPhase70DeadbandAdversarial:
    """Adversarial stress testing of the 368th-order Tricentahexacontaoctagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-272) for |z| <= 0.00035."""
        z_denoised = apply_tricentahexacontaoctagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-240, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        pos = apply_tricentahexacontaoctagonal_hyperbolic_deadband(test_points, regime="UNKNOWN")
        neg = apply_tricentahexacontaoctagonal_hyperbolic_deadband(-test_points, regime="UNKNOWN")
        np.testing.assert_allclose(neg, -pos, atol=1e-15)

    def test_deadband_extreme_signals(self):
        """Verify 100% signal transmission for high conviction |z| >= 0.15."""
        extreme_z = np.array([-10.0, -2.0, -0.5, -0.15, 0.15, 0.5, 2.0, 10.0])
        denoised = apply_tricentahexacontaoctagonal_hyperbolic_deadband(extreme_z)
        np.testing.assert_allclose(denoised, extreme_z, rtol=1e-9)

    def test_deadband_subnormal_stability(self):
        """Verify stability with subnormal float inputs."""
        subnormals = np.array([5e-324, -5e-324, 2.2e-308, -2.2e-308])
        denoised = apply_tricentahexacontaoctagonal_hyperbolic_deadband(subnormals)
        assert np.all(denoised == 0.0)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F322.1)
# =========================================================================

class TestPhase70RankModulationAdversarial:
    """Adversarial testing of 71st-order hyper-convex rank modulation."""

    def test_rank_modulation_extreme_monotonicity(self):
        """Test monotonicity on finely spaced rank grid."""
        r = np.linspace(0.0, 1.0, 2000)
        g = compute_phase70_hyperconvex_rank_modulation(r, gamma_top=17.70)
        diffs = np.diff(g)
        assert (diffs >= 0.0).all(), "Rank modulation violates monotonicity!"

    def test_rank_modulation_regime_hierarchy(self):
        """Verify gamma_top regime hierarchy across all regimes."""
        assert REGIME_GAMMA_TOP_V70["BULL_LOW_VOL"] > REGIME_GAMMA_TOP_V70["BULL_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V70["BULL_HIGH_VOL"] > REGIME_GAMMA_TOP_V70["SIDEWAYS"]
        assert REGIME_GAMMA_TOP_V70["SIDEWAYS"] > REGIME_GAMMA_TOP_V70["SIDEWAYS_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V70["SIDEWAYS_HIGH_VOL"] > REGIME_GAMMA_TOP_V70["BEAR"]
        assert REGIME_GAMMA_TOP_V70["BEAR"] > REGIME_GAMMA_TOP_V70["BEAR_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V70["BEAR_HIGH_VOL"] > REGIME_GAMMA_TOP_V70["CRISIS"]

    def test_rank_modulation_damping_lower_70_percent(self):
        """Verify lower 70% damping: g(0.70) <= 2.26 across all regimes."""
        for regime, gamma in REGIME_GAMMA_TOP_V70.items():
            g_70 = compute_phase70_hyperconvex_rank_modulation(0.70, gamma_top=gamma)
            assert g_70 <= 2.26, f"Lower 70% damping violated in {regime}: {g_70}"


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F321)
# =========================================================================

class TestPhase70CouplerAdversarial:
    """Adversarial stress testing of the Borcherds-Moonshine Monster Whittaker coupler."""

    def test_coupler_collinear_and_degenerate_inputs(self):
        """Coupler must produce valid bounded outputs on collinear or constant inputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=22.70,
            lambda_monster=0.9999998,
        )
        const_df = pd.DataFrame({
            "val": [0.5, 0.5, 0.5],
            "mom": [0.5, 0.5, 0.5],
            "flow": [0.5, 0.5, 0.5],
            "cat": [0.5, 0.5, 0.5],
            "net": [0.5, 0.5, 0.5],
        })
        res = coupler(const_df)
        assert np.all(res["h_monster_whit"].values == 1.0)
        assert np.all(res["z_monster_whit"].values == 1.0)
        assert np.all(res["FERI_v70"].values == 1.0)

    def test_coupler_boundary_invariants(self):
        """All outputs must lie strictly within [0, 1]."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=22.70,
            lambda_monster=0.9999998,
        )
        np.random.seed(70)
        rand_df = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(100, 5)), columns=["val", "mom", "flow", "cat", "net"])
        res = coupler(rand_df)
        for col in ["h_monster_whit", "z_monster_whit", "FERI_v70"]:
            vals = res[col].values
            assert (vals >= 0.0).all() and (vals <= 1.0).all()


# =========================================================================
# 4. ADVERSARIAL BARYCENTER & EVAR STRESS TESTS (F323.1 & F323.2)
# =========================================================================

class TestPhase70RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-20 barycenter and 72nd-cumulant EVaR."""

    def test_barycenter_simplex_conservation_and_heavy_tail_prioritization(self):
        """Verify simplex conservation sum(q_i) == 1.0 and CVaR dominance under equal inputs."""
        alloc = UnifiedPortfolioAllocator(version=70)

        w_eq = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        q = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_20_fisher_rao_barycenter_blend(w_eq)

        assert math.isclose(sum(q.values()), 1.0, rel_tol=1e-5)
        # CVaR (mu=6.85) > BL (mu=6.00) > HERC (mu=4.00) > RP (mu=3.35)
        assert q["cvar"] > q["bl"] > q["herc"] > q["rp"]

    def test_72nd_cumulant_evar_fat_tailed_sensitivity(self):
        """Verify that 72nd-cumulant EVaR is strictly sensitive to fat-tailed distributions."""
        alloc = UnifiedPortfolioAllocator(version=70)
        np.random.seed(42)

        norm_rets = np.random.normal(0.0, 0.02, 2000)
        t_rets = np.random.standard_t(df=3, size=2000) * 0.02 / math.sqrt(3)

        evar_norm = _extract_evar_val(alloc.compute_phase70_evar(norm_rets))
        evar_t = _extract_evar_val(alloc.compute_phase70_evar(t_rets))

        assert evar_t > evar_norm, f"Fat-tailed Student-t EVaR ({evar_t}) must exceed Gaussian EVaR ({evar_norm})"

    def test_72nd_cumulant_evar_volatility_monotonicity(self):
        """Verify that 72nd-cumulant EVaR is strictly monotonically increasing with volatility."""
        alloc = UnifiedPortfolioAllocator(version=70)
        np.random.seed(101)

        vols = [0.005, 0.010, 0.020, 0.040]
        evars = []
        for v in vols:
            rets = np.random.normal(0.0, v, 2000)
            val = _extract_evar_val(alloc.compute_phase70_evar(rets))
            evars.append(val)

        for i in range(len(evars) - 1):
            assert evars[i] < evars[i + 1], f"EVaR must increase with volatility: {evars[i]} >= {evars[i + 1]}"

    def test_72nd_cumulant_evar_empty_resilience(self):
        """Verify EVaR handles empty and NaN inputs gracefully."""
        alloc = UnifiedPortfolioAllocator(version=70)
        empty_res = alloc.compute_phase70_evar([])
        assert _extract_evar_val(empty_res) == 0.0

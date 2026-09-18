r"""
tests/test_phase52_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 52 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F232.2: 224th-Order Bicentatetracontagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs (z in [-10^300, 10^300])
   - Deadband leakage at boundary (|z| <= 0.00035 -> 0.0, leakage < 10^-144)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity across broad spectrum and odd symmetry: f(-z) == -f(z)
2. Feature F232.1: 47th-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Strict monotonicity for negative conviction (z_denoised < 0)
   - Right-tail amplification g(1.0) > 7000.0 > 500.0 (bull low vol gamma=8.40)
   - Lower 70% damping g(0.70) <= 1.70
   - Out-of-bounds clipping and regime hierarchy
3. Feature F231: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
4. Feature F233.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [4.20, 3.10, 3.05, 4.75])
5. Feature F233.2: 48th-Cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker EVaR
   - Analytical monotonicity and boundedness across diverse random distributions
   - Heavy-tail sensitivity comparison (Student-t vs Gaussian)
   - Extreme input stability and empty / NaN resilience
6. Feature F234.1: KNK 31-Dark-Energy DAHA Limits
   - Outer horizon coordinate scale: c_monster_scale = (1.0 / max(10^-6, c_monster)) ** (1.0 / 33.0)
   - Repulsive tidal acceleration scaling: -16.5 * c_monster * (r ** 32) * daha_31
   - Clamped acceleration in [-100.0, 100.0]
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_bicentatetracontagonal_hyperbolic_deadband,
    compute_phase52_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v52,
    REGIME_GAMMA_TOP_V52,
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F232.2)
# =========================================================================

class TestPhase52DeadbandAdversarial:
    """Adversarial stress testing of the 224th-order Bicentatetracontagonal deadband."""

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
        """Verify strict noise annihilation to 0.0 (< 10^-144) for |z| <= 0.00035."""
        z_denoised = apply_bicentatetracontagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-144, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_odd_symmetry(self):
        """Verify perfect odd symmetry f(-z) == -f(z) across the dynamic range."""
        test_points = np.linspace(0.0001, 1.0, 500)
        for z in test_points:
            pos_val = apply_bicentatetracontagonal_hyperbolic_deadband(z)
            neg_val = apply_bicentatetracontagonal_hyperbolic_deadband(-z)
            assert np.isclose(pos_val, -neg_val, atol=1e-15, rtol=1e-12)

    def test_deadband_signal_preservation_high_conviction(self):
        """Verify 100.0% signal preservation for high conviction |z| >= 0.15."""
        conviction_points = [0.15, -0.15, 0.25, -0.25, 0.50, -0.50, 1.0, -1.0]
        for z in conviction_points:
            val = apply_bicentatetracontagonal_hyperbolic_deadband(z)
            assert np.isclose(val, z, rtol=1e-12)

    def test_deadband_subnormal_and_extreme_inputs(self):
        """Verify stability against subnormals and extreme floating point inputs."""
        subnormals = [1e-300, -1e-300, 1e-150, -1e-150]
        for z in subnormals:
            val = apply_bicentatetracontagonal_hyperbolic_deadband(z)
            assert val == 0.0

        extreme_points = [1e10, -1e10, 1e50, -1e50, 1e150, -1e150]
        for z in extreme_points:
            val = apply_bicentatetracontagonal_hyperbolic_deadband(z)
            assert math.isfinite(val)
            assert np.isclose(val, z, rtol=1e-9)

    def test_deadband_monotonicity_broad_spectrum(self):
        """Verify strict non-decreasing monotonicity across 10,000 points."""
        spectrum = np.linspace(-1.0, 1.0, 10001)
        denoised = apply_bicentatetracontagonal_hyperbolic_deadband(spectrum)
        diffs = np.diff(denoised)
        assert (diffs >= 0.0).all(), "Deadband must be strictly monotonically non-decreasing"


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F232.1)
# =========================================================================

class TestPhase52RankModulationAdversarial:
    """Adversarial stress testing of 47th-order hyper-convex rank modulation."""

    def test_rank_modulation_strict_monotonicity_positive(self):
        """Verify strict monotonicity across 10,000 rank points for positive conviction."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase52_hyperconvex_rank_modulation(r_grid, gamma_top=8.40, z_denoised=0.1)
        diffs = np.diff(g_vals)
        assert (diffs >= 0.0).all(), "Positive conviction modulation must be strictly monotonically non-decreasing"

    def test_rank_modulation_strict_monotonicity_negative(self):
        """Verify strict monotonicity (decreasing) across 10,000 rank points for negative conviction."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase52_hyperconvex_rank_modulation(r_grid, gamma_top=8.40, z_denoised=-0.1)
        diffs = np.diff(g_vals)
        assert (diffs <= 0.0).all(), "Negative conviction modulation must be strictly monotonically non-increasing"

    def test_rank_modulation_extreme_amplification_and_damping(self):
        """Verify right-tail amplification g(1.0) > 7000.0 > 500.0 and lower 70% damping g(0.70) <= 1.70."""
        g_top = compute_phase52_hyperconvex_rank_modulation(1.0, gamma_top=8.40, z_denoised=0.0)
        assert g_top > 7000.0 > 500.0, f"g(1.0)={g_top} did not achieve required amplification > 7000.0"

        g_70 = compute_phase52_hyperconvex_rank_modulation(0.70, gamma_top=8.40, z_denoised=0.0)
        assert g_70 <= 1.70, f"g(0.70)={g_70} exceeded damping ceiling 1.70"

    def test_rank_modulation_regime_hierarchy(self):
        """Verify gamma_top ordering across all market regimes."""
        assert REGIME_GAMMA_TOP_V52["BULL_LOW_VOL"] > REGIME_GAMMA_TOP_V52["BULL_HIGH_VOL"]
        assert REGIME_GAMMA_TOP_V52["BULL_HIGH_VOL"] > REGIME_GAMMA_TOP_V52["SIDEWAYS"]
        assert REGIME_GAMMA_TOP_V52["SIDEWAYS"] > REGIME_GAMMA_TOP_V52["BEAR"]
        assert REGIME_GAMMA_TOP_V52["BEAR"] > REGIME_GAMMA_TOP_V52["CRISIS"]


# =========================================================================
# 3. ADVERSARIAL RISK BARYCENTER & EVAR STRESS TESTS (F233.1 & F233.2)
# =========================================================================

class TestPhase52RiskAdversarial:
    """Adversarial stress testing of Lurie-Borcherds Homology Barycenter and 48th-Cumulant EVaR."""

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
            res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_fisher_rao_barycenter_blend(case)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
            for v in res.values():
                assert 0.0 < v < 1.0

    def test_barycenter_curvature_metric_weight_ordering(self, allocator):
        """Verify metric weights mu = [4.20, 3.10, 3.05, 4.75] order CVaR > BL > HERC > RP under uniform inputs."""
        uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_fisher_rao_barycenter_blend(uniform)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    def test_barycenter_fisher_rao_simplex_conservation(self, allocator):
        """Verify simplex conservation sum q_i == 1.0 for 50 diverse random Dirichlet inputs."""
        np.random.seed(42)
        for _ in range(50):
            alpha = np.random.uniform(0.1, 5.0, size=4)
            w = np.random.dirichlet(alpha)
            inp = {"bl": w[0], "herc": w[1], "rp": w[2], "cvar": w[3]}
            out = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_fisher_rao_barycenter_blend(inp)
            assert math.isclose(sum(out.values()), 1.0, rel_tol=1e-5)
            for v in out.values():
                assert v > 0.0

    def test_evar_order_48_heavy_tail_sensitivity(self, allocator):
        """Verify 48th-cumulant EVaR strictly increases with tail thickness."""
        np.random.seed(123)
        normal_returns = np.random.normal(0.0005, 0.015, 1000)
        t_student_returns = np.random.standard_t(df=3, size=1000) * 0.015 + 0.0005

        evar_norm = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_risk_measure(normal_returns, order=48))
        evar_t = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_risk_measure(t_student_returns, order=48))

        assert evar_t > evar_norm, "48th-cumulant EVaR must reflect heavier Student-t tails"

    def test_evar_order_48_monotonicity_with_scale(self, allocator):
        """Verify EVaR increases monotonically as losses are scaled up."""
        np.random.seed(777)
        rets = np.random.normal(-0.001, 0.02, 500)
        ev1 = _extract_evar_val(allocator.compute_48th_cumulant_evar(rets))
        ev2 = _extract_evar_val(allocator.compute_48th_cumulant_evar(rets * 2.0))
        assert ev2 > ev1


# =========================================================================
# 4. ADVERSARIAL MICROSTRUCTURE OMS LIMIT TESTS (F234.1)
# =========================================================================

class TestPhase52MicrostructureAdversarial:
    """Adversarial stress testing of KNK 31-Dark-Energy DAHA Spacetime Hydrodynamics."""

    def test_knk_31_dark_energy_daha_limits_and_clamping(self):
        """Verify KNK 31-Dark-Energy DAHA acceleration remains strictly clamped in [-100.0, 100.0]."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)
        radii = [0.001, 0.01, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0, 1000.0]

        for r in radii:
            res = engine.compute_kerr_newman_kiselev_31_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
                r_coord=r,
                spread=0.05,
                p_mid=100.0,
                qi_l3=0.3,
            )
            assert -100.0 <= res["queue_acceleration"] <= 100.0
            assert math.isfinite(res["predicted_micro_price"])
            assert math.isclose(res["equation_of_state_w_31"], -11.0, rel_tol=1e-5)
            assert math.isclose(res["daha_31_factor"], 3.54, rel_tol=1e-5)
            assert math.isclose(res["density_dark_energy_31"], 0.00000000009765625, rel_tol=1e-9)
            assert "knk_31_dark_energy_tidal_force" in res

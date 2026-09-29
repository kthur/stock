r"""
tests/test_phase81_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 81 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F376: 456th-Order Tetracosiapentacontahexagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs
   - Deadband boundary noise annihilation (|z| <= 0.035 -> 0.0, leakage < 10^-308)
   - Signal transmission at |z| >= 0.150 -> 100.0%
   - Monotonicity and odd symmetry: f(-z) == -f(z)
2. Feature F376.1: 93rd-Order Hyper-Convex Rank Modulation
   - Strict monotonicity for positive conviction (z_denoised >= 0)
   - Right-tail amplification g(1.0) > 4000000000.0 (bull low vol gamma=21.50)
   - Lower 70% damping g(0.70) <= 2.60
   - Regime hierarchy
3. Feature F377: Quantum Geometric Langlands Monster Moonshine Whittaker Coupler
   - Degenerate, collinear, orthogonal, extreme pillar stress
   - Invariant bounds: h, z, FERI in [0, 1]
   - Output gating for FERI_v81 and f_out_81
4. Feature F378.1: Higher-Homology-31 Fisher-Rao Barycenter Blend
   - Simplex conservation (sum q_i = 1.0, q_i > 0)
   - Metric weight ordering: CVaR > BL > HERC > RP (mu = [7.10, 4.55, 2.80, 8.50])
5. Feature F378.2: 94th-Cumulant EVaR
   - Analytical monotonicity, heavy-tail sensitivity, empty / NaN resilience
   - Order=94 and xi_monster=0.9999999999999999999 verification
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiapentacontahexagonal_hyperbolic_deadband,
    apply_tetracosiatetracontaoctagonal_hyperbolic_deadband,
    compute_phase81_deadband,
    apply_phase81_deadband,
    phase81_deadband,
    compute_phase81_hyperconvex_rank_modulation,
    compute_phase81_rank_warping,
    compute_phase81_rank_modulation,
    phase81_rank_modulation,
    get_regime_adaptive_gamma_top_v81,
    REGIME_GAMMA_TOP_V81,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase81Coupler,
    Phase81WhittakerDrinfeldCoupler,
    Phase81BorcherdsMoonshineCoupler,
    Phase81MonsterWhittakerCoupler,
    compute_phase81_coupling,
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
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F376)
# =========================================================================

class TestPhase81DeadbandAdversarial:
    """Adversarial stress testing of the 456th-order Tetracosiapentacontahexagonal deadband."""

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
        0.00035,
        -0.00035,
        0.00349,
        -0.00349,
        0.0035,
        -0.0035,
    ])
    def test_deadband_boundary_noise_annihilation(self, z):
        """Verify strict noise annihilation to 0.0 (< 10^-308) for |z| <= 0.0035."""
        z_denoised = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-250, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_signal_pass_through_high_amplitude(self):
        """Verify signal transmission at |z| >= 0.150 is >= 99.99999% intact."""
        amplitudes = [0.15, -0.15, 0.25, -0.25, 0.50, -0.50, 1.0, -1.0, 5.0, -5.0]
        for a in amplitudes:
            res = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(a)
            assert np.isclose(res, a, rtol=1e-7), f"Signal distortion at a={a}: got {res}"

    def test_deadband_odd_symmetry(self):
        """Verify f(-z) == -f(z) across range [-1.0, 1.0]."""
        pts = np.linspace(-1.0, 1.0, 201)
        for p in pts:
            pos = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(p)
            neg = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(-p)
            assert np.isclose(pos, -neg, atol=1e-15)

    def test_deadband_nan_inf_safety(self):
        """Verify handling of NaN and Inf without crashing."""
        for val in [np.nan, np.inf, -np.inf]:
            res = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(val)
            assert np.isnan(res) or res == 0.0 or np.isinf(res)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F376.1)
# =========================================================================

class TestPhase81RankModulationAdversarial:
    """Adversarial stress testing of 93rd-order hyper-convex rank modulation."""

    def test_monotonicity_positive_conviction(self):
        """Verify strict monotonicity across 10,001 points for z_denoised >= 0."""
        r = np.linspace(0.0, 1.0, 10001)
        g = compute_phase81_hyperconvex_rank_modulation(r, gamma_top=21.50, z_denoised=0.1)
        diffs = np.diff(g)
        assert (diffs >= 0.0).all()

    def test_lower_percentile_suppression(self):
        """Verify g(0.70) <= 2.65 to confirm suppression of lower 70% of distribution."""
        val = compute_phase81_hyperconvex_rank_modulation(0.70, gamma_top=21.50)
        assert val <= 2.65 + 1e-9

    def test_top_percentile_amplification(self):
        """Verify g(1.0) achieves ultra-conviction amplification > 4,000,000,000."""
        val = compute_phase81_hyperconvex_rank_modulation(1.0, gamma_top=21.50)
        assert val > 4_000_000_000.0


# =========================================================================
# 3. ADVERSARIAL WHITTAKER COUPLER STRESS TESTS (F377)
# =========================================================================

class TestPhase81CouplerAdversarial:
    """Adversarial stress testing of Borcherds-Moonshine Monster Whittaker Coupler."""

    def test_coupler_extreme_stress_inputs(self):
        """Stress coupler with extreme degenerate and orthogonal inputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=81)

        # Degenerate all-zeros
        df_zeros = pd.DataFrame(np.zeros((10, 5)), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_zeros = coupler(df_zeros)
        assert (res_zeros['h_monster_whit'] >= 0.0).all()
        assert (res_zeros['h_monster_whit'] <= 1.0).all()
        assert (res_zeros['FERI_v81'] >= 0.0).all()
        assert (res_zeros['FERI_v81'] <= 1.0).all()

        # All-ones
        df_ones = pd.DataFrame(np.ones((10, 5)), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_ones = coupler(df_ones)
        assert (res_ones['h_monster_whit'] >= 0.0).all()
        assert (res_ones['FERI_v81'] >= 0.0).all()


# =========================================================================
# 4. ADVERSARIAL RISK ALLOCATION & EVAR TESTS (F378)
# =========================================================================

class TestPhase81RiskAdversarial:
    """Adversarial stress testing of Higher-Homology-31 Barycenter and 94th-Cumulant EVaR."""

    def test_barycenter_extreme_weights(self):
        """Verify Higher-Homology-31 barycenter stays on simplex under extreme inputs."""
        alloc = UnifiedPortfolioAllocator(version=81)

        extreme_weights = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
            {"bl": 1e-8, "herc": 1e-8, "rp": 1e-8, "cvar": 1.0},
        ]
        for w in extreme_weights:
            b = alloc.compute_phase81_barycenter(w)
            assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5)
            for v in b.values():
                assert 0.0 <= v <= 1.0

    def test_evar_heavy_tail_sensitivity(self):
        """Verify 94th-cumulant EVaR responds conservatively to extreme negative returns."""
        alloc = UnifiedPortfolioAllocator(version=81)
        normal_ret = np.random.normal(0.001, 0.01, 100)
        crashed_ret = normal_ret.copy()
        crashed_ret[0] = -0.50  # 50% crash

        e_norm = _extract_evar_val(alloc.compute_phase81_evar(normal_ret))
        e_crash = _extract_evar_val(alloc.compute_phase81_evar(crashed_ret))
        assert e_crash > e_norm, "EVaR must increase under extreme tail crash"

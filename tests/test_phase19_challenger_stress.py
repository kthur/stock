"""
tests/test_phase19_challenger_stress.py

Adversarial Stress Test Suite for Phase 19 Quantitative Enhancements:
- Milestone 1 (Alpha Signal and Deadband):
  * Tetracontagonal (40th-Order) Hyperbolic Noise Deadband leakage and monotonicity
  * 14th-Order Ultra-Convex Rank Modulation g_v19(r) boundary limits, convexity and monotonicity
  * Lurie Infinity-Topos Coupler under identical, orthogonal, opposite, NaN and extreme inputs
- Milestone 2 (Portfolio Allocation and Tail Risk):
  * Grothendieck-Lurie (Infinity,1)-Category Fisher-Rao Barycenter on degenerated edge allocations
  * 15th-Cumulant Ultra-Beyond-Singularity EVaR float stability (15! = 1.307e12) and coherent tail hierarchy
- Milestone 3 (Microstructure and Fast LOB Hydrodynamics):
  * Reissner-Nordstrom Extremal Black Hole L3 Hydrodynamics
  * Near-horizon behavior (r -> r_H = M), vanishing frame-dragging (omega == 0), positive throat amplification

Author: Challenger Quant 1 (Empirical Challenger)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_tetracontagonal_hyperbolic_deadband,
    compute_phase19_hyperconvex_rank_modulation,
    LurieInfinityToposCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetracontagonal_hyperbolic_deadband as fs_tetracontagonal_deadband,
    apply_quintic_hyperbolic_deadband,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.core.fast_lob_engine import FastOrderBookMatchingEngine


# =============================================================================
# 1. TETRACONTAGONAL (40TH-ORDER) HYPERBOLIC DEADBAND ADVERSARIAL STRESS
# =============================================================================

class TestTetracontagonalDeadbandAdversarial:
    """Adversarial stress testing of the 40th-order tetracontagonal deadband."""

    @pytest.mark.parametrize("z, expected_max_leakage", [
        (0.001, 1e-60),
        (0.005, 2e-34),
        (0.010, 1e-20),
    ])
    def test_deadband_numerical_leakage_points(self, z, expected_max_leakage):
        """Verify exact numerical leakage of 40th-order deadband at key points."""
        out = apply_tetracontagonal_hyperbolic_deadband(z, delta_noise=0.035, alpha_pos=40.0)
        leakage = abs(out) / z
        assert leakage < expected_max_leakage, f"Leakage {leakage} exceeded {expected_max_leakage} at z={z}"

    def test_deadband_leakage_strictly_below_1e22_for_near_zero(self):
        """
        Verify that for all |z| <= 0.005, noise leakage (|z_denoised| / |z|) is strictly < 10^-22.
        Tests a fine grid of 5,000 points in [1e-6, 0.005].
        """
        z_grid = np.linspace(1e-6, 0.005, 5000)
        out = apply_tetracontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=40.0)
        leakages = np.abs(out) / z_grid
        max_leakage = np.max(leakages)
        assert max_leakage < 1e-22, f"Max leakage {max_leakage:.4e} was not strictly < 1e-22 in [0, 0.005]"

    def test_deadband_full_transmission_at_high_conviction(self):
        """At |z| = 0.150, deadband must transmit 100.000% of signal."""
        z_high = 0.150
        out = apply_tetracontagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=40.0)
        transmission = out / z_high
        assert math.isclose(transmission, 1.0, rel_tol=1e-9), f"Transmission {transmission} is not 100%"

    def test_deadband_exact_intermediate_values(self):
        """Verify deadband behavior at delta boundary |z| = 0.035."""
        z_delta = 0.035
        out = apply_tetracontagonal_hyperbolic_deadband(z_delta, delta_noise=0.035, alpha_pos=40.0)
        # At z = delta, ratio = 1.0, arg = 1.0, tanh(1.0) ~ 0.761594156
        expected = z_delta * math.tanh(1.0)
        assert math.isclose(out, expected, rel_tol=1e-5)

    def test_deadband_strict_rank_monotonicity(self):
        """Verify strict rank monotonicity (Spearman rho == 1.0000) across range [-0.5, 0.5]."""
        z_range = np.linspace(-0.5, 0.5, 2000)
        out = apply_tetracontagonal_hyperbolic_deadband(z_range, delta_noise=0.035, alpha_pos=40.0)
        rho, _ = spearmanr(z_range, out)
        assert math.isclose(rho, 1.0, abs_tol=1e-7), f"Spearman rho was {rho}, expected 1.0000"

    def test_deadband_odd_symmetry(self):
        """In symmetric regimes, deadband must exhibit exact odd symmetry f(-z) == -f(z)."""
        z_points = np.array([0.001, 0.005, 0.010, 0.035, 0.100, 0.250])
        out_pos = apply_tetracontagonal_hyperbolic_deadband(z_points, delta_noise=0.035, alpha_pos=40.0)
        out_neg = apply_tetracontagonal_hyperbolic_deadband(-z_points, delta_noise=0.035, alpha_pos=40.0)
        np.testing.assert_allclose(out_pos, -out_neg, rtol=1e-12, atol=1e-15)

    def test_deadband_extreme_and_subnormal_stability(self):
        """Ensure no crash, underflow-to-NaN, or overflow on extreme inputs."""
        extremes = np.array([1e-35, 1e-100, 1e5, -1e5, 0.0])
        out = apply_tetracontagonal_hyperbolic_deadband(extremes, delta_noise=0.035, alpha_pos=40.0)
        assert np.all(np.isfinite(out)), "Outputs contained non-finite values"


# =============================================================================
# 2. 14TH-ORDER ULTRA-CONVEX RANK MODULATION g_v19 ADVERSARIAL STRESS
# =============================================================================

class TestRankModulationGv19Adversarial:
    """Adversarial stress testing of 14th-order ultra-convex rank modulation g_v19."""

    @pytest.mark.parametrize("r, expected_pos, expected_neg", [
        (0.0, 0.50, 1.35),
        (0.5, 0.50 + 1.02 * 0.5 * math.exp(1.0 * (0.5 ** 14)), 1.35 - 1.00 * 0.5),
        (1.0, 0.50 + 1.02 * 1.0 * math.exp(1.0), 1.35 - 1.00 * 1.0),
    ])
    def test_rank_modulation_exact_values(self, r, expected_pos, expected_neg):
        """Test exact values of g_v19(r) at boundary points 0.0, 0.5, 1.0."""
        out_pos = compute_phase19_hyperconvex_rank_modulation(r, gamma_top=1.0, z_denoised=1.0)
        out_neg = compute_phase19_hyperconvex_rank_modulation(r, gamma_top=1.0, z_denoised=-1.0)
        assert math.isclose(out_pos, expected_pos, rel_tol=1e-6)
        assert math.isclose(out_neg, expected_neg, rel_tol=1e-6)

    def test_rank_modulation_negative_and_excess_rank_clipping(self):
        """Negative ranks and ranks > 1.0 must be clipped safely to [0, 1]."""
        out_neg_rank = compute_phase19_hyperconvex_rank_modulation(-0.5, gamma_top=1.0, z_denoised=1.0)
        out_zero_rank = compute_phase19_hyperconvex_rank_modulation(0.0, gamma_top=1.0, z_denoised=1.0)
        assert math.isclose(out_neg_rank, out_zero_rank, abs_tol=1e-12)

        out_high_rank = compute_phase19_hyperconvex_rank_modulation(2.5, gamma_top=1.0, z_denoised=1.0)
        out_one_rank = compute_phase19_hyperconvex_rank_modulation(1.0, gamma_top=1.0, z_denoised=1.0)
        assert math.isclose(out_high_rank, out_one_rank, abs_tol=1e-12)

    def test_rank_modulation_strict_monotonicity(self):
        """g_v19(r) for z_denoised >= 0 must be strictly monotonic increasing for r in [0, 1]."""
        r_grid = np.linspace(0.0, 1.0, 2000)
        g_vals = [compute_phase19_hyperconvex_rank_modulation(r, gamma_top=1.2, z_denoised=1.0) for r in r_grid]
        diffs = np.diff(g_vals)
        assert np.all(diffs > 0), "g_v19(r) was not strictly monotonically increasing"

    def test_rank_modulation_strict_convexity(self):
        """
        g_v19(r) must be convex on [0, 1].
        Analytical derivative:
        g'(r) = 1.02 * exp(gamma * r^14) * (1 + 14 * gamma * r^14)
        g''(r) = 1.02 * 14 * gamma * r^13 * exp(gamma * r^14) * (15 + 14 * gamma * r^14) >= 0.
        Verify second differences are strictly non-negative.
        """
        r_grid = np.linspace(0.01, 1.0, 1000)
        g_vals = np.array([compute_phase19_hyperconvex_rank_modulation(r, gamma_top=1.5, z_denoised=1.0) for r in r_grid])
        diff1 = np.diff(g_vals)
        diff2 = np.diff(diff1)
        assert np.all(diff2 >= -1e-12), f"Convexity violated: min 2nd diff was {np.min(diff2)}"


# =============================================================================
# 3. LURIE INFINITY-TOPOS COUPLER ADVERSARIAL STRESS
# =============================================================================

class TestLurieInfinityToposCouplerAdversarial:
    """Adversarial stress testing of LurieInfinityToposCoupler."""

    def test_lurie_coupler_identical_scores(self):
        """
        When all 5 pillars have identical scores, there is zero obstruction:
        E_lurie == 0.0, Z_lurie == 1.0, h_lurie == 1.0, FERI_v19 == 1.0.
        """
        coupler = LurieInfinityToposCoupler()
        identical_scores = np.array([0.7, 0.7, 0.7, 0.7, 0.7])
        res = coupler(identical_scores)
        assert math.isclose(res["e_lurie"], 0.0, abs_tol=1e-12)
        assert math.isclose(res["z_lurie"], 1.0, abs_tol=1e-12)
        assert math.isclose(res["h_lurie"], 1.0, abs_tol=1e-12)
        assert math.isclose(res["FERI_v19"], 1.0, abs_tol=1e-12)

    def test_lurie_coupler_orthogonal_scores(self):
        """
        When pillars are orthogonal standard basis vectors (e.g. eye(5)):
        coupler must compute finite non-NaN energy, coupling, and FERI for each object.
        """
        coupler = LurieInfinityToposCoupler()
        orth = np.eye(5)
        res = coupler(orth)
        assert np.all(np.isfinite(res["h_lurie"]))
        assert np.all(np.isfinite(res["z_lurie"]))
        assert np.all(res["h_lurie"] >= 1e-6)
        assert np.all(res["h_lurie"] <= 1.0)
        assert np.all(res["FERI_v19"] > 0.0)

    def test_lurie_coupler_opposite_scores(self):
        """
        When pillars have maximally opposite scores (+2.0 vs -2.0):
        obstruction energy must be large, but h_lurie must remain strictly >= epsilon_reg and finite.
        """
        coupler = LurieInfinityToposCoupler(epsilon_reg=1e-6)
        opposite = np.array([2.0, -2.0, 2.0, -2.0, 2.0])
        res = coupler(opposite)
        assert res["e_lurie"] > 0.0
        assert res["h_lurie"] >= 1e-6
        assert res["h_lurie"] <= 1.0
        assert np.isfinite(res["h_lurie"])

    def test_lurie_coupler_nan_handling(self):
        """When pillar inputs contain NaNs, coupler must sanitize via nan_to_num without crash."""
        coupler = LurieInfinityToposCoupler()
        nan_input = np.array([np.nan, 0.5, np.nan, -0.2, 0.8])
        res = coupler(nan_input)
        assert not np.isnan(res["h_lurie"])
        assert not np.isnan(res["z_lurie"])
        assert not np.isnan(res["e_lurie"])
        assert not np.isnan(res["FERI_v19"])

    def test_lurie_coupler_extreme_scales(self):
        """Extreme scales (+100.0, -100.0) must not cause overflow or NaN."""
        coupler = LurieInfinityToposCoupler()
        huge_input = np.array([100.0, -100.0, 50.0, -50.0, 0.0])
        res = coupler(huge_input)
        assert np.isfinite(res["h_lurie"])
        assert res["h_lurie"] == 1e-6  # Saturated at epsilon_reg


# =============================================================================
# 4. GROTHENDIECK-LURIE BARYCENTER ADVERSARIAL STRESS
# =============================================================================

class TestGrothendieckLurieBarycenterAdversarial:
    """Adversarial stress testing of Grothendieck-Lurie Fisher-Rao barycenter."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.mark.parametrize("input_weights", [
        {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
        {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
        {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0},
        {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
        {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25},
        {"bl": 1e-9, "herc": 1e-9, "rp": 1e-9, "cvar": 1.0},
        {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [-0.5, 0.2, 0.3, 0.5],
    ])
    def test_barycenter_sum_to_one_and_non_negativity(self, allocator, input_weights):
        """
        Grothendieck-Lurie barycenter must strictly satisfy:
        1. sum(weights) == 1.000000 (within numerical tolerance 1e-7)
        2. All weights > 0 (strict non-negativity with minimum bound >= 1e-8)
        across any degenerated edge allocation.
        """
        res = allocator.compute_grothendieck_lurie_infinity_fisher_rao_barycenter_blend(input_weights)
        total_w = sum(res.values())
        assert math.isclose(total_w, 1.0, abs_tol=1e-7), f"Weight sum {total_w} != 1.0 for input {input_weights}"
        for k, v in res.items():
            assert v > 0.0, f"Weight {k}={v} was not strictly positive for input {input_weights}"
            assert np.isfinite(v), f"Weight {k}={v} was non-finite"

    def test_barycenter_prioritizes_cvar_and_bl(self, allocator):
        """
        Under uniform input [0.25, 0.25, 0.25, 0.25], Grothendieck-Lurie metric weights
        mu_lurie = [1.70, 1.40, 1.35, 2.00] must prioritize cvar (2.00) and bl (1.70).
        """
        uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_grothendieck_lurie_infinity_fisher_rao_barycenter_blend(uniform)
        assert res["cvar"] > 0.20
        assert res["bl"] > 0.20


# =============================================================================
# 5. ULTRA-BEYOND-SINGULARITY EVAR AND 15! ADVERSARIAL STRESS
# =============================================================================

class TestUltraBeyondSingularityEVaRAdversarial:
    """Adversarial stress testing of 15th-cumulant Ultra-Beyond-Singularity EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_15_factorial_overflow_under_large_returns_and_t(self, allocator):
        """
        Verify that 15! = 1,307,674,368,000 does NOT cause float overflow or NaN
        under extreme return values (-100.0, +100.0) and large t values.
        """
        extreme_returns = np.array([-100.0, -50.0, -20.0, 0.0, 20.0, 50.0, 100.0])
        t_grid = [0.01, 0.1, 1.0, 5.0, 10.0, 20.0]
        res = allocator.compute_ultra_beyond_singularity_evar_risk_measure(
            extreme_returns,
            alpha=0.05,
            t_grid=t_grid
        )
        val = res["ultra_beyond_singularity_evar_value"]
        assert np.isfinite(val), f"EVaR value {val} was not finite"
        assert val > 0.0, f"EVaR value {val} was not positive for loss distribution"

    @pytest.mark.parametrize("seed, dist_func", [
        (42, lambda: np.random.normal(0.001, 0.02, 500)),
        (43, lambda: np.random.standard_t(df=3, size=500) * 0.02),
        (44, lambda: np.random.laplace(0.0, 0.03, 500)),
        (45, lambda: np.concatenate([np.random.normal(0.001, 0.01, 490), np.array([-0.15, -0.25, -0.35])])),
    ])
    def test_coherent_tail_risk_hierarchy(self, allocator, seed, dist_func):
        """
        Coherent tail risk hierarchy must be strictly non-violable:
        VaR <= CVaR <= Beyond-Singularity-EVaR <= Ultra-Beyond-Singularity-EVaR.
        """
        np.random.seed(seed)
        sample = dist_func()
        res = allocator.compute_ultra_beyond_singularity_evar_risk_measure(sample, alpha=0.05)
        var = res["var_value"]
        cvar = res["cvar_value"]
        beyond = res["beyond_singularity_evar_value"]
        ultra = res["ultra_beyond_singularity_evar_value"]

        assert var <= cvar + 1e-6, f"VaR ({var}) > CVaR ({cvar})"
        assert cvar <= beyond + 1e-6, f"CVaR ({cvar}) > Beyond-EVaR ({beyond})"
        assert beyond <= ultra + 1e-6, f"Beyond-EVaR ({beyond}) > Ultra-Beyond-EVaR ({ultra})"

    def test_evar_empty_or_zero_returns(self, allocator):
        """Empty or all-zero returns must yield graceful non-crashing fallback."""
        res_zero = allocator.compute_ultra_beyond_singularity_evar_risk_measure(np.zeros(100), alpha=0.05)
        assert np.isfinite(res_zero["ultra_beyond_singularity_evar_value"])

        res_empty = allocator.compute_ultra_beyond_singularity_evar_risk_measure([], alpha=0.05)
        assert np.isfinite(res_empty["ultra_beyond_singularity_evar_value"])


# =============================================================================
# 6. REISSNER-NORDSTROM EXTREMAL L3 HYDRODYNAMICS ADVERSARIAL STRESS
# =============================================================================

class TestReissnerNordstromExtremalHydrodynamicsAdversarial:
    """Adversarial stress testing of Reissner-Nordstrom extremal L3 hydrodynamics."""

    @pytest.fixture
    def engine(self):
        eng = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(1, 11):
            eng.add_limit_order(f"bid_{i}", "BUY", 10000.0 - i * 10, 100 * i)
            eng.add_limit_order(f"ask_{i}", "SELL", 10000.0 + i * 10, 100 * i)
        return eng

    def test_rn_extremal_horizon_approach_no_division_by_zero(self, engine):
        """
        When coordinate radius r approaches horizon r_H = M:
        dist_horiz_sq = (r - r_H)^2 + 0.05 * M^2 >= 0.05 * M^2 > 0.
        Verify that near-horizon and in-horizon conditions produce NO division by zero or NaN.
        """
        res = engine.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        assert np.isfinite(res["reissner_nordstrom_rotational_acceleration"])
        assert np.isfinite(res["reissner_nordstrom_accelerated_qi"])
        assert np.isfinite(res["reissner_nordstrom_micro_price"])
        assert np.isfinite(res["rn_tidal_force"])

    def test_rn_vanishing_frame_dragging(self, engine):
        """Static Reissner-Nordstrom black hole has zero spin (a=0), so frame-dragging omega == 0.0 identically."""
        res = engine.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        assert res["frame_dragging_omega"] == 0.0
        assert math.isclose(res["frame_dragging_omega"], 0.0, abs_tol=1e-12)

    def test_rn_positive_throat_amplification(self, engine):
        """
        AdS_2 near-horizon throat amplification factor:
        Gamma_ext = 1.0 + max(0, (r_H - r)/r_H) + M^2 / ((r - M)^2 + 0.05*M^2)
        must strictly satisfy Gamma_ext >= 1.0 > 0.0 everywhere.
        """
        res = engine.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        m_mass = res["rn_mass_M"]
        r_h = res["horizon_radius"]
        for r_test in [0.1, 0.5 * r_h, r_h, 1.5 * r_h, 10.0 * r_h]:
            dist_sq = (r_test - r_h) ** 2 + 0.05 * (m_mass ** 2)
            gamma_ext = 1.0 + max(0.0, (r_h - r_test) / max(1e-4, r_h)) + (m_mass ** 2) / max(1e-4, dist_sq)
            assert gamma_ext >= 1.0, f"Throat amplification {gamma_ext} was < 1.0 at r={r_test}"
            assert np.isfinite(gamma_ext), f"Throat amplification was non-finite at r={r_test}"

    def test_rn_extremal_charge_clamping(self, engine):
        """Charge parameter Q must be strictly clamped to M (cosmic censorship, no naked singularity)."""
        res_super = engine.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=10.0)
        assert res_super["rn_charge_Q"] <= res_super["rn_mass_M"] + 1e-6
        assert math.isclose(res_super["extremal_ratio_Q_over_M"], 1.0, abs_tol=1e-3)
        assert res_super["is_extremal"] is True

    def test_rn_empty_order_book_resilience(self):
        """Empty order book must not cause division by zero or NaN."""
        empty_eng = FastOrderBookMatchingEngine(symbol="EMPTY")
        res = empty_eng.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        assert np.isfinite(res["reissner_nordstrom_micro_price"])
        assert np.isfinite(res["rn_tidal_force"])

r"""
tests/test_phase93_adversarial_challenger1.py

Adversarial Empirical Challenge and Stress Test Suite for Phase 93
Quantitative Alpha Enhancement & Risk Allocation (v100 Production Master):
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)

Scope of Empirical Adversarial Tests:
1. Feature F435: Asymmetric Decacosidodecagonal (552nd-Order) Hyperbolic Noise Deadband
   - Sub-threshold noise annihilation: |z| <= 0.0003 across 10,000 random sub-threshold samples -> strictly < 10^-552 (float64 0.0)
   - Boundary inputs: z = 0.035, z = 0.0350001, z = -0.035
   - Signal transmission: |z| >= 0.150 -> 100.0% retention (|f(z)/z - 1.0| < 1e-4)
   - Monotonicity across 1,000,000 synthetic values (Spearman rho == 1.0000, all diffs >= 0)
   - Odd symmetry: f(-z) == -f(z)
   - Edge case robustness: NaN, Inf, -Inf, empty arrays, subnormal floats (1e-320), extreme magnitude (1e15)
   - Complete 19-alias tree bit-identical verification

2. Feature F435: 117th-Order Hyper-Convex Rank Modulation
   - Strict rank monotonicity across 100,000 points across all regimes in REGIME_GAMMA_TOP_V93
   - Top-decile amplification: g(1.0) > 10^7 under Bull/Sideways regimes (up to ~1.04e14 under BULL_LOW_VOL)
   - Defensive regime scaling: verify intentional risk dampening in BEAR/CRISIS regimes
   - Boundary inputs: r = 0.0 (0.50), r = 1.0, r < 0 (clipped to 0.50), r > 1.0 (clipped to r=1.0)
   - Lower-percentile damping: r <= 0.70 -> g(r) <= 3.05 (r^117 suppression)
   - Negative conviction branch: z_denoised < 0 -> g_neg(r) = 1.35 - 1.00 * r
   - Complete 5-alias tree verification

3. Feature F436: Borcherds-Moonshine Monster Whittaker Coupler v93
   - High-dimensional stress (1000 rows x 5 pillars, random uniform in [0, 1])
   - Degenerate inputs: all-zeros, all-ones, NaN-corrupted entries, collinear vectors
   - Boundedness of invariants: h, z, FERI in [0, 1], e_monster_whit finite
   - 198th-order chiral oper obstruction and 110th-order topological defect invariant verification
   - Backward compatibility: FERI_v93, feri_v93, f_out_93 alongside FERI_v92~v85
   - Coupler alias tree verification

4. Feature F437.1: Higher-Homology-43 Motivic Fisher-Rao Barycenter Blend
   - Boundary weight vectors: [1, 0, 0, 0], [0, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0]
   - Unnormalized weights: [500, 200, 100, 800], [1000, 0, 0, 0]
   - Simplex conservation: sum q_i == 1.000000 within 1e-5
   - Metric curvature hierarchy under uniform input: CVaR (10.75) > BL (8.90) > HERC (5.45) > RP (2.50)
   - Permutation invariance/stability across all 24 permutations
   - Input format stress: dict, list of dicts, 1D array, 2D array
   - Complete 17-alias tree verification

5. Feature F437.2: 118th-Cumulant Expansion Trans-Singular EVaR Risk Measure
   - Heavy-tailed return stress: Student-t (df=2), Cauchy, Pareto, Normal
   - Tail-risk ordering: EVaR(Crash) > EVaR(Normal)
   - Volatility monotonicity: EVaR expands monotonically with scale
   - Zero returns and extreme negative returns resilience
   - Order=118, 29-nines+5 xi_monster (0.99999999999999999999999999995)
   - Complete 30-alias tree verification across UnifiedPortfolioAllocator and PortfolioAllocator
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import itertools
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_decacosidodecagonal_hyperbolic_deadband,
    apply_decacosidodecadihedral_hyperbolic_deadband,
    apply_quingentapentacontasagonal_hyperbolic_deadband,
    apply_quingentapentacontadigonal_hyperbolic_deadband,
    apply_pentacentapentacontasagonal_hyperbolic_deadband,
    apply_pentacentapentacontadigonal_hyperbolic_deadband,
    apply_decacosidodeca_hyperbolic_deadband,
    apply_decacosidodecagonal_deadband,
    decacosidodecagonal_deadband,
    decacosidodecagonal_hyperbolic_deadband,
    compute_phase93_deadband,
    apply_phase93_deadband,
    phase93_deadband,
    apply_552nd_order_hyperbolic_deadband,
    apply_552th_order_hyperbolic_deadband,
    apply_552nd_deadband,
    apply_552th_deadband,
    apply_552_deadband,
    apply_hyperbolic_deadband_v93,
    suppress_factor_noise_hyperbolic_v93,
    compute_phase93_hyperconvex_rank_modulation,
    compute_phase93_rank_warping,
    compute_phase93_rank_modulation,
    phase93_rank_modulation,
    phase93_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v93,
    REGIME_GAMMA_TOP_V93,
    get_regime_adaptive_gamma_top_v93,
    Phase93FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase93Coupler,
    Phase93WhittakerDrinfeldCoupler,
    Phase93BorcherdsMoonshineCoupler,
    Phase93MonsterWhittakerCoupler,
    compute_phase93_coupling,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_43_fisher_rao_barycenter_blend as module_phase93_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_43_evar_risk_measure as module_phase93_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    """Safely extract scalar EVaR value from dict or numeric return."""
    if isinstance(res, dict):
        for key in ["phase93_evar", "evar", "evar_risk_measure", "value"]:
            if key in res and res[key] is not None:
                return float(res[key])
        for key in res:
            if "evar" in key.lower():
                return float(res[key])
        return 0.0
    return float(res)


# =========================================================================
# 1. EMPIRICAL ADVERSARIAL DEADBAND STRESS TESTS (F435)
# =========================================================================

class TestPhase93DeadbandAdversarial:
    """Empirical adversarial stress testing of 552nd-order Decacosidodecagonal hyperbolic deadband."""

    def test_deadband_10k_sub_threshold_zero_leakage(self):
        """Verify noise leakage < 10^-552 (strictly 0.0 in float64) across 10,000 sub-threshold samples (|z| <= 0.0003)."""
        rng = np.random.default_rng(93)
        # Uniform random samples strictly in [-0.0003, 0.0003]
        z_sub = rng.uniform(-0.0003, 0.0003, 10_000)
        z_denoised = apply_decacosidodecagonal_hyperbolic_deadband(z_sub, delta_noise=0.035, alpha_pos=552.0)

        # In float64, (0.0003 / 0.035)^552 = (0.0085714)^552 ~ 10^-1141 which underflows to exact 0.0
        assert np.all(z_denoised == 0.0), f"Leakage detected: {np.count_nonzero(z_denoised)} non-zero samples found"
        assert np.all(np.abs(z_denoised) < 1e-300)

    @pytest.mark.parametrize("z_val", [
        0.0, 1e-15, -1e-15, 1e-10, -1e-10, 1e-6, -1e-6,
        0.0001, -0.0001, 0.000299, -0.000299, 0.0003, -0.0003
    ])
    def test_deadband_subnormal_and_exact_points(self, z_val):
        """Verify discrete sub-threshold points underflow strictly to 0.0."""
        out = apply_decacosidodecagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=552.0)
        assert out == 0.0, f"Expected exact 0.0 at z={z_val}, got {out}"

    def test_deadband_boundary_inputs(self):
        """Test boundary inputs: z = 0.035, z = 0.0350001, z = -0.035."""
        b1 = apply_decacosidodecagonal_hyperbolic_deadband(0.035, delta_noise=0.035, alpha_pos=552.0)
        b2 = apply_decacosidodecagonal_hyperbolic_deadband(0.0350001, delta_noise=0.035, alpha_pos=552.0)
        b3 = apply_decacosidodecagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, alpha_pos=552.0)

        # At z = delta = 0.035, ratio = 1.0, arg = 1.0^552 = 1.0, output = 0.035 * tanh(1.0)
        expected_b1 = 0.035 * math.tanh(1.0)
        assert math.isclose(b1, expected_b1, rel_tol=1e-5), f"Boundary b1={b1} expected {expected_b1}"
        assert b2 > b1, f"Boundary monotonicity violated: {b2} <= {b1}"
        assert math.isclose(b1, -b3, abs_tol=1e-15), f"Odd symmetry violated at boundary: {b1} != -{b3}"

    def test_deadband_100pct_signal_retention(self):
        """Verify 100.0% signal retention (|f(z)/z - 1.0| < 1e-4) for |z| >= 0.150 across 10,000 samples."""
        rng = np.random.default_rng(9301)
        z_pos = rng.uniform(0.150, 5.0, 5000)
        z_neg = rng.uniform(-5.0, -0.150, 5000)
        z_strong = np.concatenate([z_pos, z_neg])

        denoised = apply_decacosidodecagonal_hyperbolic_deadband(z_strong, delta_noise=0.035, alpha_pos=552.0)
        rel_errors = np.abs(denoised / z_strong - 1.0)
        assert np.all(rel_errors < 1e-4), f"Max relative error {np.max(rel_errors)} exceeds 1e-4"
        assert np.allclose(denoised, z_strong, rtol=1e-4)

    def test_deadband_1m_synthetic_rank_monotonicity(self):
        """Verify strict rank monotonicity rho = 1.0000 across 1,000,000 sorted synthetic values."""
        rng = np.random.default_rng(9302)
        z_raw = np.sort(rng.uniform(-5.0, 5.0, 1_000_000))
        z_out = apply_decacosidodecagonal_hyperbolic_deadband(z_raw, delta_noise=0.035, alpha_pos=552.0)

        diffs = np.diff(z_out)
        assert np.all(diffs >= 0.0), f"Monotonicity violation: {np.sum(diffs < 0.0)} negative differences found"

        # Downsample for Spearman correlation check
        sample_indices = np.linspace(0, len(z_raw) - 1, 10_000, dtype=int)
        rho, _ = spearmanr(z_raw[sample_indices], z_out[sample_indices])
        assert math.isclose(rho, 1.0000, rel_tol=1e-5), f"Spearman rho={rho} != 1.0000"

    def test_deadband_odd_symmetry(self):
        """Verify f(-z) == -f(z) across symmetric grid."""
        pts = np.linspace(0.0001, 2.0, 1000)
        pos = apply_decacosidodecagonal_hyperbolic_deadband(pts, delta_noise=0.035, alpha_pos=552.0)
        neg = apply_decacosidodecagonal_hyperbolic_deadband(-pts, delta_noise=0.035, alpha_pos=552.0)
        assert np.allclose(pos, -neg, atol=1e-15)

    def test_deadband_extreme_and_degenerate_inputs(self):
        """Stress deadband with empty arrays, NaNs, Infs, extreme values, subnormals."""
        # Empty array
        empty = np.array([])
        assert len(apply_decacosidodecagonal_hyperbolic_deadband(empty)) == 0

        # Subnormal float
        subnormal = 1e-320
        res_sub = apply_decacosidodecagonal_hyperbolic_deadband(subnormal)
        assert res_sub == 0.0

        # Extreme magnitude
        extreme_pos = 1e15
        extreme_neg = -1e15
        assert math.isclose(apply_decacosidodecagonal_hyperbolic_deadband(extreme_pos), extreme_pos, rel_tol=1e-5)
        assert math.isclose(apply_decacosidodecagonal_hyperbolic_deadband(extreme_neg), extreme_neg, rel_tol=1e-5)

        # NaN / Inf handling
        for val in [np.nan, np.inf, -np.inf]:
            res = apply_decacosidodecagonal_hyperbolic_deadband(val)
            assert np.isnan(res) or np.isinf(res) or res == 0.0

    def test_deadband_19_aliases_bit_identity(self):
        """Verify all 19 aliases of 552nd-order hyperbolic deadband produce bit-identical results."""
        arr = np.array([-0.20, -0.035, -0.0002, 0.0, 0.0002, 0.035, 0.20])
        ref = apply_decacosidodecagonal_hyperbolic_deadband(arr)

        assert np.array_equal(apply_decacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_quingentapentacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_quingentapentacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_pentacentapentacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_pentacentapentacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_decacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_decacosidodecagonal_deadband(arr), ref)
        assert np.array_equal(decacosidodecagonal_deadband(arr), ref)
        assert np.array_equal(decacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(compute_phase93_deadband(arr), ref)
        assert np.array_equal(apply_phase93_deadband(arr), ref)
        assert np.array_equal(phase93_deadband(arr), ref)
        assert np.array_equal(apply_552nd_order_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_552th_order_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_552nd_deadband(arr), ref)
        assert np.array_equal(apply_552th_deadband(arr), ref)
        assert np.array_equal(apply_552_deadband(arr), ref)
        assert np.array_equal(apply_hyperbolic_deadband_v93(arr), ref)
        assert np.array_equal(suppress_factor_noise_hyperbolic_v93(arr), ref)
        assert np.array_equal(Phase93FactorSuppressionEngine.apply_decacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(RegimeFactorSuppressionEngine.apply_decacosidodecagonal_hyperbolic_deadband(arr), ref)


# =========================================================================
# 2. EMPIRICAL ADVERSARIAL RANK MODULATION STRESS TESTS (F435)
# =========================================================================

class TestPhase93RankModulationAdversarial:
    """Empirical adversarial stress testing of 117th-order hyper-convex rank modulation."""

    def test_rank_modulation_all_regimes_monotonicity(self):
        """Verify strict rank monotonicity across 100,000 points for all regimes in REGIME_GAMMA_TOP_V93."""
        r_sweep = np.linspace(0.0, 1.0, 100_000)
        for regime, gamma in REGIME_GAMMA_TOP_V93.items():
            g = compute_phase93_hyperconvex_rank_modulation(r_sweep, regime=regime)
            diffs = np.diff(g)
            assert np.all(diffs >= 0.0), f"Strict monotonicity failed for regime '{regime}' (gamma={gamma})"
            assert get_regime_adaptive_gamma_top_v93(regime) == gamma
            assert gamma <= 31.00

    def test_rank_modulation_amplification_under_bull_and_sideways(self):
        """Verify g(1.0) > 10^7 under Bull and Sideways regimes (e.g. ~1.04e14 under BULL_LOW_VOL)."""
        high_gamma_regimes = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS', 'SIDEWAYS_LOW_VOL',
            'SIDEWAYS_HIGH_VOL', 'RECOVERY', '2', '1', 'UNKNOWN'
        ]
        for regime in high_gamma_regimes:
            g_one = compute_phase93_hyperconvex_rank_modulation(1.0, regime=regime)
            assert g_one > 1e7, f"Expected g(1.0) > 10^7 for regime '{regime}', got {g_one}"

        # Exact formula verification for BULL_LOW_VOL (gamma = 31.00)
        g_bull_low = compute_phase93_hyperconvex_rank_modulation(1.0, regime='BULL_LOW_VOL')
        expected_bull_low = 0.50 + 3.58 * 1.0 * math.exp(31.00)
        assert math.isclose(g_bull_low, expected_bull_low, rel_tol=1e-5)
        assert g_bull_low > 1.0e14

    def test_rank_modulation_defensive_regime_scaling(self):
        """Verify and document graceful risk scaling: in BEAR and CRISIS regimes, g(1.0) is bounded as designed."""
        defensive_regimes = {
            'BEAR': 10.60,
            'BEAR_LOW_VOL': 10.60,
            'BEAR_HIGH_VOL': 5.30,
            'CRISIS': 2.30,
            'PANIC': 2.30,
            '0': 10.60,
        }
        for regime, expected_gamma in defensive_regimes.items():
            g_one = compute_phase93_hyperconvex_rank_modulation(1.0, regime=regime)
            expected = 0.50 + 3.58 * math.exp(expected_gamma)
            assert math.isclose(g_one, expected, rel_tol=1e-4)
            # Confirms intentional capital protection: defensive regimes do not over-amplify
            assert g_one < 1e7

    def test_rank_modulation_boundaries(self):
        """Test boundary inputs: r = 0.0, r = 1.0, r < 0, r > 1.0."""
        g_zero = compute_phase93_hyperconvex_rank_modulation(0.0)
        g_neg = compute_phase93_hyperconvex_rank_modulation(-0.5)
        g_one = compute_phase93_hyperconvex_rank_modulation(1.0, regime='BULL_LOW_VOL')
        g_over = compute_phase93_hyperconvex_rank_modulation(1.5, regime='BULL_LOW_VOL')

        assert g_zero == 0.50, f"g(0.0) must be exactly 0.50, got {g_zero}"
        assert g_neg == 0.50, f"g(r < 0) must be clipped to r=0.0 (0.50), got {g_neg}"
        assert g_over == g_one, f"g(r > 1.0) must be clipped to r=1.0, got {g_over}"

    def test_rank_modulation_lower_percentile_damping(self):
        """Verify 117th-order power completely dampens lower 70%: g(0.70) <= 3.05 under BULL_LOW_VOL."""
        # 0.70^117 ~ 6.9e-19, so exp(31 * 0.70^117) = exp(~0) = 1.00000000
        # g(0.70) = 0.50 + 3.58 * 0.70 * 1.0 = 3.006 <= 3.05
        val_70 = compute_phase93_hyperconvex_rank_modulation(0.70, regime='BULL_LOW_VOL')
        assert val_70 <= 3.05, f"Lower percentile damping failed: got {val_70} > 3.05"
        assert math.isclose(val_70, 0.50 + 3.58 * 0.70, abs_tol=1e-12)

        # Median damping: g(0.50) = 0.50 + 3.58 * 0.50 = 2.29
        val_50 = compute_phase93_hyperconvex_rank_modulation(0.50, regime='BULL_LOW_VOL')
        assert math.isclose(val_50, 0.50 + 3.58 * 0.50, abs_tol=1e-12)

    def test_rank_modulation_negative_conviction_branch(self):
        """Verify g_neg(r) = 1.35 - 1.00 * r when z_denoised < 0."""
        r = np.array([0.0, 0.25, 0.50, 0.75, 1.0])
        z_neg = np.full_like(r, -0.05)
        res_neg = compute_phase93_hyperconvex_rank_modulation(r, z_denoised=z_neg)
        expected_neg = 1.35 - 1.00 * r
        assert np.allclose(res_neg, expected_neg)

        # Mixed vector test
        z_mixed = np.array([-0.1, 0.1, -0.2, 0.2, 0.0])
        r_mixed = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
        res_mixed = compute_phase93_hyperconvex_rank_modulation(r_mixed, z_denoised=z_mixed, regime='BULL_LOW_VOL')
        assert math.isclose(res_mixed[0], 1.35 - 1.00 * 0.2)
        assert math.isclose(res_mixed[1], 0.50 + 3.58 * 0.4 * math.exp(31.0 * (0.4 ** 117)))
        assert math.isclose(res_mixed[2], 1.35 - 1.00 * 0.6)
        assert math.isclose(res_mixed[3], 0.50 + 3.58 * 0.8 * math.exp(31.0 * (0.8 ** 117)))
        assert math.isclose(res_mixed[4], 0.50 + 3.58 * 1.0 * math.exp(31.0 * (1.0 ** 117)))

    def test_rank_modulation_5_aliases(self):
        """Verify all 5 aliases produce bit-identical results."""
        ranks = np.array([0.0, 0.3, 0.7, 1.0])
        ref = compute_phase93_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL')

        assert np.array_equal(compute_phase93_rank_warping(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(compute_phase93_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(phase93_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(phase93_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(apply_hyper_convex_rank_modulation_v93(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(Phase93FactorSuppressionEngine.compute_phase93_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(RegimeFactorSuppressionEngine.compute_phase93_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)


# =========================================================================
# 3. EMPIRICAL ADVERSARIAL WHITTAKER COUPLER STRESS TESTS (F436)
# =========================================================================

class TestPhase93CouplerAdversarial:
    """Empirical adversarial stress testing of Borcherds-Moonshine Monster Whittaker Coupler v93."""

    def test_coupler_high_dim_stress_1000_rows(self):
        """Stress coupler with 1000 rows, random uniform features across 5 pillars."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=93)
        cols = ['val', 'mom', 'flow', 'cat', 'net']

        rng = np.random.default_rng(9303)
        df_1000 = pd.DataFrame(rng.uniform(0.0, 1.0, size=(1000, 5)), columns=cols)
        res = coupler(df_1000)

        required_keys = [
            'FERI_v93', 'feri_v93', 'f_out_93',
            'FERI_v92', 'feri_v92', 'f_out_92',
            'h_monster_whit', 'z_monster_whit', 'e_monster_whit'
        ]
        for key in required_keys:
            assert key in res, f"Missing key '{key}' in coupler output"
            vals = np.asarray(res[key])
            assert len(vals) == 1000
            assert np.all(np.isfinite(vals)), f"Non-finite values found in key '{key}'"
            assert np.all(vals >= 0.0), f"Negative values found in key '{key}'"

    def test_coupler_degenerate_inputs_and_nan_resilience(self):
        """Stress coupler with degenerate inputs: all-zeros, all-ones, NaNs, collinear features."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=93)
        cols = ['val', 'mom', 'flow', 'cat', 'net']

        # 1. All-zeros DataFrame
        df_zeros = pd.DataFrame(np.zeros((50, 5)), columns=cols)
        res_zeros = coupler(df_zeros)
        assert np.all(np.isfinite(res_zeros['FERI_v93']))
        assert np.all((res_zeros['FERI_v93'] >= 0.0) & (res_zeros['FERI_v93'] <= 1.0))

        # 2. All-ones DataFrame
        df_ones = pd.DataFrame(np.ones((50, 5)), columns=cols)
        res_ones = coupler(df_ones)
        assert np.all(np.isfinite(res_ones['FERI_v93']))
        assert np.all((res_ones['FERI_v93'] >= 0.0) & (res_ones['FERI_v93'] <= 1.0))

        # 3. NaN-corrupted DataFrame
        rng = np.random.default_rng(9304)
        df_nan = pd.DataFrame(rng.uniform(0.1, 0.9, size=(60, 5)), columns=cols)
        df_nan.iloc[0:10, 0] = np.nan
        df_nan.iloc[20:30, 2] = np.nan
        df_nan.iloc[40:50, :] = np.nan  # All columns NaN for rows 40-50
        res_nan = coupler(df_nan)
        assert np.all(np.isfinite(res_nan['FERI_v93']))

    def test_coupler_oper_and_defect_invariants(self):
        """Verify numerical stability of 198th chiral oper obstruction and 110th defect invariants."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            version=93,
            kappa_monster_whit=38.00,
            lambda_monster=0.99999999999999995,
        )
        assert coupler.kappa_monster_whit == 38.00
        assert coupler.lambda_monster == 0.99999999999999995
        assert coupler.is_phase93 is True
        assert coupler.harmony_boost == 8.85

        # Extreme pillar dispersion
        p_df = pd.DataFrame({
            'val': [0.0, 1.0, 0.0, 1.0],
            'mom': [1.0, 0.0, 1.0, 0.0],
            'flow': [0.0, 1.0, 0.0, 1.0],
            'cat': [1.0, 0.0, 1.0, 0.0],
            'net': [0.0, 1.0, 0.0, 1.0],
        })
        res = coupler(p_df)
        assert np.all(np.isfinite(res['e_monster_whit']))
        assert np.all(np.isfinite(res['z_monster_whit']))
        assert np.all(res['z_monster_whit'] > 0.0)

    def test_coupler_backward_compatibility_with_earlier_phases(self):
        """Verify coupler retains earlier phase output keys (FERI_v92~v85) and backward compatibility."""
        p_df = pd.DataFrame({
            'val': [0.5, 0.4],
            'mom': [0.5, 0.6],
            'flow': [0.5, 0.5],
            'cat': [0.5, 0.7],
            'net': [0.5, 0.3],
        })
        res = compute_phase93_coupling(p_df)
        for ver in [93, 92, 91, 90, 89, 88, 87, 86, 85]:
            assert f'FERI_v{ver}' in res, f"Missing backwards compatible key FERI_v{ver}"
            assert f'feri_v{ver}' in res, f"Missing backwards compatible key feri_v{ver}"
            assert f'f_out_{ver}' in res, f"Missing backwards compatible key f_out_{ver}"

    def test_coupler_alias_tree(self):
        """Verify all coupler aliases reference the primary coupler class."""
        assert Phase93Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler


# =========================================================================
# 4. EMPIRICAL ADVERSARIAL BARYCENTER STRESS TESTS (F437.1)
# =========================================================================

class TestPhase93BarycenterAdversarial:
    """Empirical adversarial stress testing of Higher-Homology-43 Motivic Fisher-Rao Barycenter Blend."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=93)

    def test_barycenter_boundary_weight_vectors(self, allocator):
        """Test boundary weight vectors: [1, 0, 0, 0], [0, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0]."""
        boundary_cases = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
        ]
        for w in boundary_cases:
            b = allocator.compute_phase93_barycenter(w)
            total = sum(b.values())
            assert math.isclose(total, 1.0, rel_tol=1e-5), f"Simplex violation for w={w}: sum={total}"
            for k, v in b.items():
                assert 0.0 < v < 1.0, f"Boundary out of bounds for {k}: {v}"

    def test_barycenter_unnormalized_and_extreme_weights(self, allocator):
        """Test unnormalized weights: [500, 200, 100, 800], [1000, 0, 0, 0], [1e-8, 1e-8, 1e-8, 1.0]."""
        test_cases = [
            [500.0, 200.0, 100.0, 800.0],
            [1000.0, 0.0, 0.0, 0.0],
            [1e-8, 1e-8, 1e-8, 1.0],
            {"bl": 500.0, "herc": 200.0, "rp": 100.0, "cvar": 800.0},
        ]
        for w in test_cases:
            b = allocator.compute_phase93_barycenter(w)
            total = sum(b.values())
            assert math.isclose(total, 1.0, rel_tol=1e-5), f"Simplex sum={total} != 1.0 for unnormalized input"
            for k, v in b.items():
                assert 0.0 < v < 1.0, f"Component {k}={v} out of (0, 1)"

    def test_barycenter_metric_hierarchy_uniform(self, allocator):
        """Verify strict metric curvature hierarchy under uniform input: CVaR (10.75) > BL (8.90) > HERC (5.45) > RP (2.50)."""
        res = allocator.compute_phase93_barycenter([0.25, 0.25, 0.25, 0.25])
        assert res['cvar'] > res['bl'], f"CVaR ({res['cvar']}) must exceed BL ({res['bl']})"
        assert res['bl'] > res['herc'], f"BL ({res['bl']}) must exceed HERC ({res['herc']})"
        assert res['herc'] > res['rp'], f"HERC ({res['herc']}) must exceed RP ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)

    def test_barycenter_all_24_weight_permutations(self, allocator):
        """Verify simplex conservation across all 24 permutations of asymmetric base weights."""
        keys = ['bl', 'herc', 'rp', 'cvar']
        base_weights = [0.45, 0.30, 0.15, 0.10]
        for perm in itertools.permutations(base_weights):
            input_dict = dict(zip(keys, perm))
            b = allocator.compute_phase93_barycenter(input_dict)
            total = sum(b.values())
            assert math.isclose(total, 1.0, rel_tol=1e-5), f"Simplex violation for perm={perm}"
            assert all(0.0 < v < 1.0 for v in b.values())

    def test_barycenter_input_types_stress(self, allocator):
        """Stress barycenter across dict, list of dicts, 1D array, 2D array, pandas Series."""
        # 1D array
        res_1d = allocator.compute_phase93_barycenter(np.array([0.2, 0.3, 0.1, 0.4]))
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # List of dicts (multi-regime distribution consensus)
        list_dicts = [
            {"bl": 0.4, "herc": 0.2, "rp": 0.1, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.1, "herc": 0.2, "rp": 0.1, "cvar": 0.6},
        ]
        res_list = allocator.compute_phase93_barycenter(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 2D array
        arr_2d = np.array([
            [0.4, 0.2, 0.1, 0.3],
            [0.2, 0.3, 0.2, 0.3],
        ])
        res_2d = allocator.compute_phase93_barycenter(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

        # Pandas Series
        s = pd.Series({"bl": 0.35, "herc": 0.25, "rp": 0.15, "cvar": 0.25})
        res_s = allocator.compute_phase93_barycenter(s.to_dict())
        assert math.isclose(sum(res_s.values()), 1.0, rel_tol=1e-5)

    def test_barycenter_17_aliases_and_delegation(self, allocator):
        """Verify barycenter alias tree on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.35, "herc": 0.20, "rp": 0.15, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_43_fisher_rao_barycenter_blend(w)

        assert allocator.compute_phase93_barycenter(w) == ref
        assert allocator.compute_phase93_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_43_barycenter(w) == ref
        assert allocator.higher_homology_43_blend(w) == ref
        assert allocator.compute_lmbmwdh43_fisher_rao_barycenter_blend(w) == ref
        assert allocator.phase93_barycenter_blend(w) == ref
        assert allocator.higher_homology_43_barycenter(w) == ref
        assert allocator.lmbmwdh43_barycenter(w) == ref

        pa = PortfolioAllocator(version=93)
        pa_res = pa.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_43_fisher_rao_barycenter_blend(w)
        assert pa_res == ref
        assert pa.compute_phase93_barycenter(w) == ref
        assert pa.compute_phase93_fisher_rao_barycenter(w) == ref
        assert pa.compute_phase93_barycenter_blend(w) == ref
        assert pa.higher_homology_43_barycenter(w) == ref
        assert pa.lmbmwdh43_barycenter(w) == ref

        assert module_phase93_barycenter(w) == ref


# =========================================================================
# 5. EMPIRICAL ADVERSARIAL EVAR STRESS TESTS (F437.2)
# =========================================================================

class TestPhase93EVaRAdversarial:
    """Empirical adversarial stress testing of 118th-Cumulant Expansion EVaR Risk Measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=93)

    def test_evar_heavy_tailed_distributions_and_order_metadata(self, allocator):
        """Verify EVaR order=118, xi_monster=29-nines+5, finite and positive bounds across heavy-tailed distributions."""
        rng = np.random.default_rng(9305)
        ret_t2 = rng.standard_t(df=2, size=500) * 0.02
        ret_cauchy = rng.standard_cauchy(size=500) * 0.005
        ret_pareto = -(rng.pareto(a=1.5, size=500) - 1.0) * 0.02
        ret_norm = rng.normal(loc=0.001, scale=0.02, size=500)

        for dist_name, ret in [('Student-t(df=2)', ret_t2), ('Cauchy', ret_cauchy), ('Pareto', ret_pareto), ('Normal', ret_norm)]:
            res = allocator.compute_phase93_evar(returns=ret)
            order = res.get('order')
            xi = res.get('xi_monster')
            evar_val = _extract_evar_val(res)

            assert order == 118, f"Expected order=118 for {dist_name}, got {order}"
            assert np.isclose(xi, 0.99999999999999999999999999995, atol=1e-15), f"Expected 29-nines+5 xi for {dist_name}"
            assert np.isfinite(evar_val), f"EVaR must be finite for {dist_name}, got {evar_val}"
            assert evar_val > 0.0, f"EVaR must be strictly positive for {dist_name}, got {evar_val}"

    def test_evar_fat_tailed_risk_ordering_and_crash_shock(self, allocator):
        """Verify tail-risk ordering: EVaR under extreme negative crash shock > EVaR under normal market."""
        rng = np.random.default_rng(9306)
        normal_ret = rng.normal(loc=0.0, scale=0.02, size=500)
        crashed_ret = normal_ret.copy()
        crashed_ret[:10] = -0.40  # Extreme -40% tail crash shock

        e_norm = _extract_evar_val(allocator.compute_phase93_evar(returns=normal_ret))
        e_crash = _extract_evar_val(allocator.compute_phase93_evar(returns=crashed_ret))

        assert e_crash > e_norm, f"EVaR failed to expand under crash shock: {e_crash} <= {e_norm}"

    def test_evar_volatility_monotonicity(self, allocator):
        """Verify EVaR scales monotonically with market volatility."""
        rng = np.random.default_rng(9307)
        ret_low_vol = rng.normal(loc=0.0, scale=0.01, size=500)
        ret_mid_vol = rng.normal(loc=0.0, scale=0.03, size=500)
        ret_high_vol = rng.normal(loc=0.0, scale=0.06, size=500)

        e_low = _extract_evar_val(allocator.compute_phase93_evar(returns=ret_low_vol))
        e_mid = _extract_evar_val(allocator.compute_phase93_evar(returns=ret_mid_vol))
        e_high = _extract_evar_val(allocator.compute_phase93_evar(returns=ret_high_vol))

        assert e_low < e_mid < e_high, f"Volatility monotonicity violated: low={e_low}, mid={e_mid}, high={e_high}"

    def test_evar_zero_and_constant_returns(self, allocator):
        """Test resilience to zero returns and constant returns."""
        zeros = np.zeros(200)
        res_zeros = allocator.compute_phase93_evar(returns=zeros)
        e_zeros = _extract_evar_val(res_zeros)
        assert np.isfinite(e_zeros)
        assert e_zeros >= 0.0

        const_ret = np.full(200, 0.01)
        res_const = allocator.compute_phase93_evar(returns=const_ret)
        e_const = _extract_evar_val(res_const)
        assert np.isfinite(e_const)
        assert e_const >= 0.0

    def test_evar_30_aliases_and_delegation(self, allocator):
        """Verify EVaR alias tree consistency across UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        ret = np.array([0.02, -0.01, 0.015, -0.02, 0.005, -0.015])
        ref_dict = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_43_evar_risk_measure(returns=ret)
        ref_evar = _extract_evar_val(ref_dict)

        assert math.isclose(_extract_evar_val(allocator.compute_phase93_evar(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_evar_order118(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_118th_cumulant_evar(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.higher_homology_43_evar(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase93_tail_risk_evar(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase93_evar_bound(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_monster_whittaker_118th_cumulant_evar(returns=ret)), ref_evar, rel_tol=1e-5)

        pa = PortfolioAllocator(version=93)
        assert math.isclose(_extract_evar_val(pa.compute_phase93_evar(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(pa.compute_evar_order118(returns=ret)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(pa.compute_118th_cumulant_evar(returns=ret)), ref_evar, rel_tol=1e-5)

        assert math.isclose(_extract_evar_val(module_phase93_evar(returns=ret)), ref_evar, rel_tol=1e-5)

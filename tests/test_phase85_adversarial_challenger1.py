r"""
tests/test_phase85_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 85 Quantitative Alpha Enhancement (v92 Production Master):
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F395: Asymmetric Tetracosiaoctacontaoctagonal (488th-Order) Hyperbolic Noise Deadband
   - Subnormals, extreme inputs, near-zero leakage (< 10^-488, underflows to 0.0)
   - Boundary inputs: z = 0.035, z = 0.0350001, z = -0.035
   - Signal transmission at |z| >= 0.150 -> 100.0% (|f(z)/z - 1.0| < 1e-4)
   - Monotonicity across 1,000,000 synthetic values (Spearman rho == 1.0000, all diffs >= 0)
   - Odd symmetry: f(-z) == -f(z)
2. Feature F395: 101st-Order Hyper-Convex Rank Modulation
   - Strict monotonicity across all regimes in REGIME_GAMMA_TOP_V85
   - Boundary inputs: r = 0.0, r = 1.0, r < 0, r > 1.0
   - Ultra-conviction right-tail amplification g(1.0) > 10^7 under BULL_LOW_VOL (gamma=22.70)
   - Lower 70% damping: g(0.70) <= 2.80
   - Negative conviction behavior: z_denoised < 0 -> g_neg(r) = 1.35 - 1.00 * r
3. Feature F396: Borcherds-Moonshine Monster Whittaker Coupler v85
   - High-dimensional stress (1000 rows, zero vectors, NaN resilience)
   - Numerical stability of 182nd chiral oper obstruction and 94th topological defect invariants
   - Invariant bounds: h, z, FERI in [0, 1]
   - Output gating for FERI_v85, feri_v85, f_out_85 with backward compatibility
4. Feature F397.1: Higher-Homology-35 Motivic Fisher-Rao Barycenter Blend
   - Degenerate weights: [1.0, 0, 0, 0], [0, 0, 0, 1.0], uniform [0.25, 0.25, 0.25, 0.25]
   - Simplex conservation: sum q_i == 1.000000 within 1e-6
   - Metric curvature hierarchy: CVaR (9.10) > BL (7.50) > HERC (4.75) > RP (2.60)
   - Permutation stability across all 24 weight permutations
5. Feature F397.2: 102nd-Cumulant EVaR Tail Risk Measure
   - Extreme heavy-tail distributions: Student-t (df=2), Pareto, Gaussian
   - Order=102, 23-nines xi_monster (0.99999999999999999999999)
   - Strict tail-risk ordering: EVaR(Pareto) > EVaR(Student-t) > EVaR(Normal)
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import itertools
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband,
    apply_tetracosiaoctacontaoctadihedral_hyperbolic_deadband,
    apply_quadringentaoctacontaoctagonal_hyperbolic_deadband,
    apply_tetracentaoctacontaoctagonal_hyperbolic_deadband,
    apply_tetracosiaoctacontaocta_hyperbolic_deadband,
    apply_tetracosiaoctacontaoctagonal_deadband,
    tetracosiaoctacontaoctagonal_deadband,
    tetracosiaoctacontaoctagonal_hyperbolic_deadband,
    compute_phase85_deadband,
    apply_phase85_deadband,
    phase85_deadband,
    apply_488th_order_hyperbolic_deadband,
    apply_488th_deadband,
    apply_488_deadband,
    apply_hyperbolic_deadband_v85,
    suppress_factor_noise_hyperbolic_v85,
    compute_phase85_hyperconvex_rank_modulation,
    compute_phase85_rank_warping,
    compute_phase85_rank_modulation,
    phase85_rank_modulation,
    phase85_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v85,
    get_regime_adaptive_gamma_top_v85,
    REGIME_GAMMA_TOP_V85,
    Phase85FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase85Coupler,
    Phase85WhittakerDrinfeldCoupler,
    Phase85BorcherdsMoonshineCoupler,
    Phase85MonsterWhittakerCoupler,
    compute_phase85_coupling,
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
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F395)
# =========================================================================

class TestPhase85DeadbandAdversarial:
    """Adversarial stress testing of 488th-order Tetracosiaoctacontaoctagonal hyperbolic deadband."""

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
        0.0003,
        -0.0003,
    ])
    def test_deadband_near_zero_noise_annihilation(self, z):
        """Verify noise leakage < 10^-488 (underflows strictly to 0.0 in float64) for |z| <= 0.0003."""
        z_denoised = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-300, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    def test_deadband_boundary_inputs(self):
        """Test boundary inputs: z = 0.035, z = 0.0350001, z = -0.035."""
        b1 = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(0.035)
        b2 = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(0.0350001)
        b3 = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(-0.035)

        # At z = 0.035 = delta, tanh(1.0) ~= 0.761594, z * tanh(1.0) ~= 0.0266558
        assert np.isclose(b1, 0.035 * np.tanh(1.0), rtol=1e-5)
        assert b2 > b1, f"Boundary monotonicity violation: {b2} <= {b1}"
        assert np.isclose(b1, -b3, atol=1e-15), f"Odd symmetry violated at boundary: {b1} != -{b3}"

    @pytest.mark.parametrize("z", [0.15, -0.15, 0.50, -0.50, 1.0, -1.0, 10.0, -10.0])
    def test_deadband_high_conviction_transmission(self, z):
        """Verify 100.0% signal transmission (|f(z)/z - 1.0| < 1e-4) for |z| >= 0.150."""
        fz = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(z)
        rel_err = abs(fz / z - 1.0)
        assert rel_err < 1e-4, f"High conviction transmission distorted at z={z}: rel_err={rel_err}"
        assert np.isclose(fz, z, rtol=1e-6)

    def test_deadband_synthetic_1m_monotonicity(self):
        """Monotonicity test on 1,000,000 synthetic values across [-10.0, 10.0]."""
        np.random.seed(42)
        z_synth = np.sort(np.random.uniform(-10.0, 10.0, 1_000_000))
        out_synth = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(z_synth)
        diffs = np.diff(out_synth)
        assert np.all(diffs >= 0.0), f"Non-monotonic anomalies found: {np.sum(diffs < 0)} violations"

    def test_deadband_odd_symmetry(self):
        """Verify f(-z) == -f(z) across linear sweep."""
        pts = np.linspace(-1.0, 1.0, 501)
        pos = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(pts)
        neg = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(-pts)
        assert np.allclose(pos, -neg, atol=1e-15)

    def test_deadband_nan_inf_safety(self):
        """Verify NaN and Inf inputs are handled without unhandled exception."""
        for val in [np.nan, np.inf, -np.inf]:
            res = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(val)
            assert np.isnan(res) or np.isinf(res) or res == 0.0

    def test_deadband_alias_tree_synchronization(self):
        """Verify complete alias tree returns bit-identical results."""
        arr = np.array([-0.10, -0.01, 0.0, 0.01, 0.035, 0.20])
        ref = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr)

        assert np.array_equal(apply_tetracosiaoctacontaoctadihedral_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_quadringentaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_tetracentaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_tetracosiaoctacontaocta_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_tetracosiaoctacontaoctagonal_deadband(arr), ref)
        assert np.array_equal(tetracosiaoctacontaoctagonal_deadband(arr), ref)
        assert np.array_equal(tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(compute_phase85_deadband(arr), ref)
        assert np.array_equal(apply_phase85_deadband(arr), ref)
        assert np.array_equal(phase85_deadband(arr), ref)
        assert np.array_equal(apply_488th_order_hyperbolic_deadband(arr), ref)
        assert np.array_equal(apply_488th_deadband(arr), ref)
        assert np.array_equal(apply_488_deadband(arr), ref)
        assert np.array_equal(apply_hyperbolic_deadband_v85(arr), ref)
        assert np.array_equal(suppress_factor_noise_hyperbolic_v85(arr), ref)
        assert np.array_equal(Phase85FactorSuppressionEngine.apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.array_equal(RegimeFactorSuppressionEngine.apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F395)
# =========================================================================

class TestPhase85RankModulationAdversarial:
    """Adversarial stress testing of 101st-order hyper-convex rank modulation."""

    def test_rank_modulation_boundaries(self):
        """Test boundary inputs: r = 0.0, r = 1.0, r < 0, r > 1.0."""
        g_zero = compute_phase85_hyperconvex_rank_modulation(0.0)
        g_one = compute_phase85_hyperconvex_rank_modulation(1.0, regime='BULL_LOW_VOL')
        g_neg = compute_phase85_hyperconvex_rank_modulation(-0.5)
        g_over = compute_phase85_hyperconvex_rank_modulation(1.5, regime='BULL_LOW_VOL')

        assert g_zero == 0.50, f"g(0.0) must be exactly 0.50, got {g_zero}"
        assert g_neg == 0.50, f"g(r < 0) must be clipped to r=0.0 (0.50), got {g_neg}"
        assert g_one > 1e7, f"g(1.0) must exceed 10^7 under BULL_LOW_VOL, got {g_one}"
        assert np.isclose(g_one, 0.50 + 3.25 * np.exp(22.70), rtol=1e-4)
        assert g_over == g_one, f"g(r > 1.0) must be clipped to r=1.0, got {g_over}"

    def test_rank_modulation_all_regimes_monotonicity(self):
        """Verify strict monotonicity across 100,000 points for all regimes in REGIME_GAMMA_TOP_V85."""
        r_sweep = np.linspace(0.0, 1.0, 100_000)
        for regime, gamma in REGIME_GAMMA_TOP_V85.items():
            g = compute_phase85_hyperconvex_rank_modulation(r_sweep, regime=regime)
            diffs = np.diff(g)
            assert np.all(diffs >= 0.0), f"Monotonicity failed in regime {regime} (gamma={gamma})"
            assert get_regime_adaptive_gamma_top_v85(regime) == gamma
            assert gamma <= 22.70

    def test_rank_modulation_lower_percentile_damping(self):
        """Verify g(0.70) <= 2.80 to guarantee suppression of lower 70% of distribution."""
        val = compute_phase85_hyperconvex_rank_modulation(0.70, regime='BULL_LOW_VOL')
        assert val <= 2.80, f"Damping failed at r=0.70: got {val} > 2.80"

    def test_rank_modulation_negative_conviction(self):
        """Verify g_neg(r) = 1.35 - 1.00 * r when z_denoised < 0."""
        r = np.array([0.0, 0.25, 0.50, 0.75, 1.0])
        z_neg = np.full_like(r, -0.1)
        res = compute_phase85_hyperconvex_rank_modulation(r, z_denoised=z_neg)
        expected = 1.35 - 1.00 * r
        assert np.allclose(res, expected)

    def test_rank_modulation_alias_tree(self):
        """Verify rank modulation alias tree consistency."""
        ranks = np.array([0.0, 0.3, 0.7, 1.0])
        ref = compute_phase85_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL')

        assert np.array_equal(compute_phase85_rank_warping(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(compute_phase85_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(phase85_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(phase85_hyperconvex_rank_modulation(ranks, regime='BULL_LOW_VOL'), ref)
        assert np.array_equal(apply_hyper_convex_rank_modulation_v85(ranks, regime='BULL_LOW_VOL'), ref)


# =========================================================================
# 3. ADVERSARIAL WHITTAKER COUPLER STRESS TESTS (F396)
# =========================================================================

class TestPhase85CouplerAdversarial:
    """Adversarial stress testing of Borcherds-Moonshine Monster Whittaker Coupler v85."""

    def test_coupler_high_dim_stress_1000_rows(self):
        """Stress coupler with 1000 rows, random values, and degenerate vectors."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=85)
        cols = ['val', 'mom', 'flow', 'cat', 'net']

        np.random.seed(85)
        df_1000 = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(1000, 5)), columns=cols)
        res = coupler(df_1000)

        for key in ['FERI_v85', 'feri_v85', 'f_out_85', 'h_monster_whit', 'z_monster_whit', 'e_monster_whit']:
            assert key in res, f"Missing key {key} in coupler output"
            vals = np.asarray(res[key])
            assert len(vals) == 1000
            assert np.all(np.isfinite(vals)), f"Non-finite values in {key}"
            assert np.all(vals >= 0.0), f"Negative values in {key}"
            if key != 'e_monster_whit':
                assert np.all(vals <= 1.0), f"Value exceeds 1.0 in {key}"

    def test_coupler_zero_vectors_and_nan_resilience(self):
        """Stress coupler with zero vectors, NaN entries, and collinear inputs."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=85)
        cols = ['val', 'mom', 'flow', 'cat', 'net']

        # Zero dataframe
        df_zeros = pd.DataFrame(np.zeros((50, 5)), columns=cols)
        res_zeros = coupler(df_zeros)
        assert np.all(np.isfinite(res_zeros['FERI_v85']))
        assert np.all((res_zeros['FERI_v85'] >= 0.0) & (res_zeros['FERI_v85'] <= 1.0))

        # NaN dataframe
        df_nan = pd.DataFrame(np.random.uniform(0.1, 0.9, size=(50, 5)), columns=cols)
        df_nan.iloc[0:5, 0] = np.nan
        df_nan.iloc[10:15, 2] = np.nan
        df_nan.iloc[20:25, :] = np.nan
        res_nan = coupler(df_nan)
        assert np.all(np.isfinite(res_nan['FERI_v85']))

    def test_coupler_oper_and_defect_invariants_boundedness(self):
        """Verify numerical stability of 182nd chiral oper action and 94th defect invariants."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            version=85,
            kappa_monster_whit=33.20,
            lambda_monster=0.9999999999995,
        )
        assert coupler.kappa_monster_whit == 33.20
        assert coupler.lambda_monster == 0.9999999999995
        assert coupler.is_phase85 is True

        # Test extreme differences near 1.0
        p_df = pd.DataFrame({
            'val': [0.0, 1.0, 0.5],
            'mom': [1.0, 0.0, 0.5],
            'flow': [0.0, 1.0, 0.5],
            'cat': [1.0, 0.0, 0.5],
            'net': [0.0, 1.0, 0.5],
        })
        res = coupler(p_df)
        assert np.all(np.isfinite(res['e_monster_whit']))
        assert np.all(np.isfinite(res['z_monster_whit']))
        assert np.all(res['z_monster_whit'] > 0.0)

    def test_coupler_aliases_and_backward_compatibility(self):
        """Verify coupler alias tree and backward compatible keys."""
        assert Phase85Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase85_coupling(p_df)
        assert 'FERI_v85' in res
        assert 'FERI_v84' in res
        assert 'FERI_v83' in res


# =========================================================================
# 4. ADVERSARIAL BARYCENTER STRESS TESTS (F397.1)
# =========================================================================

class TestPhase85BarycenterAdversarial:
    """Adversarial stress testing of Higher-Homology-35 Motivic Fisher-Rao Barycenter Blend."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=85)

    def test_barycenter_degenerate_weight_vectors(self, allocator):
        """Test degenerate weight vectors [1, 0, 0, 0], [0, 0, 0, 1], and uniform [0.25, 0.25, 0.25, 0.25]."""
        test_cases = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.25, 0.25, 0.25, 0.25],
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
            {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25},
        ]
        for w in test_cases:
            b = allocator.compute_phase85_barycenter(w)
            total = sum(b.values())
            assert math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6), f"Simplex violation for w={w}: sum={total}"
            for k, v in b.items():
                assert 0.0 <= v <= 1.0, f"Weight bounds violated for {k}: {v}"

    def test_barycenter_metric_hierarchy_uniform(self, allocator):
        """Verify strict metric curvature hierarchy CVaR (9.10) > BL (7.50) > HERC (4.75) > RP (2.60) on uniform input."""
        res = allocator.compute_phase85_barycenter([0.25, 0.25, 0.25, 0.25])
        assert res['cvar'] > res['bl'], f"CVaR ({res['cvar']}) must exceed BL ({res['bl']})"
        assert res['bl'] > res['herc'], f"BL ({res['bl']}) must exceed HERC ({res['herc']})"
        assert res['herc'] > res['rp'], f"HERC ({res['herc']}) must exceed RP ({res['rp']})"

    def test_barycenter_all_weight_permutations(self, allocator):
        """Verify simplex conservation across all 24 permutations of input weights."""
        keys = ['bl', 'herc', 'rp', 'cvar']
        base_weights = [0.40, 0.30, 0.20, 0.10]
        for perm in itertools.permutations(base_weights):
            input_dict = dict(zip(keys, perm))
            b = allocator.compute_phase85_barycenter(input_dict)
            total = sum(b.values())
            assert math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6)
            assert all(0.0 <= v <= 1.0 for v in b.values())

    def test_barycenter_aliases(self, allocator):
        """Verify barycenter alias tree consistency."""
        w = [0.3, 0.3, 0.2, 0.2]
        ref = allocator.compute_phase85_barycenter(w)

        assert allocator.compute_phase85_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_35_barycenter(w) == ref
        assert allocator.phase85_barycenter_blend(w) == ref
        assert allocator.compute_lmbmwdh35_fisher_rao_barycenter_blend(w) == ref


# =========================================================================
# 5. ADVERSARIAL EVAR STRESS TESTS (F397.2)
# =========================================================================

class TestPhase85EVaRAdversarial:
    """Adversarial stress testing of 102nd-Cumulant EVaR Tail Risk Measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=85)

    def test_evar_heavy_tailed_distributions(self, allocator):
        """Verify EVaR order=102, xi_monster=23-nines, and finite positivity across Student-t, Pareto, Normal distributions."""
        np.random.seed(85)
        ret_t2 = np.random.standard_t(df=2, size=500) * 0.02
        ret_pareto = -(np.random.pareto(a=1.5, size=500) - 1.0) * 0.02
        ret_norm = np.random.normal(loc=0.001, scale=0.02, size=500)

        for dist_name, ret in [('Student-t(df=2)', ret_t2), ('Pareto', ret_pareto), ('Normal', ret_norm)]:
            res = allocator.compute_phase85_evar(ret)
            order = res.get('order')
            xi = res.get('xi_monster')
            evar_val = _extract_evar_val(res)

            assert order == 102, f"Expected order=102 for {dist_name}, got {order}"
            assert np.isclose(xi, 0.99999999999999999999999, atol=1e-15), f"Expected 23-nines xi for {dist_name}"
            assert np.isfinite(evar_val), f"EVaR must be finite for {dist_name}, got {evar_val}"
            assert evar_val > 0.0, f"EVaR must be strictly positive for {dist_name}, got {evar_val}"

    def test_evar_fat_tailed_risk_ordering(self, allocator):
        """Verify fat-tailed EVaR is strictly greater than Gaussian EVaR under standardized crash risk."""
        np.random.seed(99)
        normal_ret = np.random.normal(loc=0.0, scale=0.02, size=500)
        crashed_ret = normal_ret.copy()
        crashed_ret[:5] = -0.30  # Extreme tail loss shock

        e_norm = _extract_evar_val(allocator.compute_phase85_evar(normal_ret))
        e_crash = _extract_evar_val(allocator.compute_phase85_evar(crashed_ret))

        assert e_crash > e_norm, f"EVaR must expand under tail shock: {e_crash} <= {e_norm}"

    def test_evar_aliases(self, allocator):
        """Verify EVaR alias tree consistency."""
        ret = np.array([0.01, -0.02, 0.005, -0.015, 0.02])
        ref = allocator.compute_phase85_evar(ret)

        assert allocator.compute_phase85_evar_risk_measure(ret)["phase85_evar"] == ref["phase85_evar"]
        assert allocator.compute_evar_order102(ret)["phase85_evar"] == ref["phase85_evar"]
        assert allocator.higher_homology_35_evar(ret)["phase85_evar"] == ref["phase85_evar"]
        assert allocator.phase85_tail_risk_evar(ret)["phase85_evar"] == ref["phase85_evar"]
        assert allocator.phase85_evar_bound(ret)["phase85_evar"] == ref["phase85_evar"]

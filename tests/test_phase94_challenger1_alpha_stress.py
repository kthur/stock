"""
tests/test_phase94_challenger1_alpha_stress.py

Adversarial Stress Testing & Empirical Verification Harness for Phase 94 Alpha & Coupler.
Author: Challenger 1 (teamwork_preview_challenger)
Target Features:
- F440: Asymmetric Hendecacosidodecagonal 560th-Order Hyperbolic Noise Deadband
- F440: 119th-Order Hyper-Convex Rank Modulation
- F441: Quantum Geometric Langlands Monster Whittaker Coupler Phase 94
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_hendecacosidodecagonal_hyperbolic_deadband,
    apply_560th_order_hyperbolic_deadband,
    apply_560_deadband,
    compute_phase94_deadband,
    apply_phase94_deadband,
    phase94_deadband,
    apply_hyperbolic_deadband_v94,
    suppress_factor_noise_hyperbolic_v94,
    compute_phase94_hyperconvex_rank_modulation,
    compute_phase94_rank_warping,
    compute_phase94_rank_modulation,
    phase94_rank_modulation,
    phase94_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v94,
    REGIME_GAMMA_TOP_V94,
    get_regime_adaptive_gamma_top_v94,
    Phase94FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase94Coupler,
    Phase94WhittakerDrinfeldCoupler,
    Phase94BorcherdsMoonshineCoupler,
    Phase94MonsterWhittakerCoupler,
    compute_phase94_coupling,
)


class TestDeadbandAdversarialExtremes:
    """Adversarial stress harness for 560th-order hyperbolic noise deadband (F440)."""

    def test_sub_noise_leakage_underflow(self):
        """Stress: Verify sub-noise |z| in [10^-10, 0.0003] produces zero noise leakage (< 10^-560)."""
        sub_noise_grid = np.array([
            1e-10, 5e-10, 1e-8, 1e-6, 5e-5, 1e-4, 2e-4, 2.9e-4, 3.0e-4,
            -1e-10, -5e-10, -1e-8, -1e-6, -5e-5, -1e-4, -2e-4, -2.9e-4, -3.0e-4
        ], dtype=np.float64)

        denoised = apply_hendecacosidodecagonal_hyperbolic_deadband(sub_noise_grid, delta_noise=0.035, alpha_pos=560.0)

        # In float64, anything < 10^-560 strictly underflows to 0.0 (or absolute < 1e-300)
        for z_in, z_out in zip(sub_noise_grid, denoised):
            assert abs(z_out) < 1e-300 or z_out == 0.0, f"Noise leakage detected for z={z_in}: {z_out}"

    def test_high_conviction_transmission_guarantee(self):
        """Stress: Verify high conviction signals |z| in [0.150, 10.0] transmit >= 99.99%."""
        strong_signals = np.array([
            0.150, 0.175, 0.200, 0.350, 0.500, 1.000, 2.500, 5.000, 10.000,
            -0.150, -0.175, -0.200, -0.350, -0.500, -1.000, -2.500, -5.000, -10.000
        ], dtype=np.float64)

        denoised = apply_hendecacosidodecagonal_hyperbolic_deadband(strong_signals, delta_noise=0.035, alpha_pos=560.0)
        transmission = denoised / strong_signals

        for z_in, trans in zip(strong_signals, transmission):
            assert trans >= 0.9999, f"Transmission dropped below 99.99% for z={z_in}: {trans:.6f}"
            assert math.isclose(trans, 1.0, rel_tol=1e-4), f"Signal distorted: z_in={z_in}, trans={trans}"

    def test_rank_monotonicity_under_jitter(self):
        """Stress: Verify strict rank monotonicity (rho == 1.0000) under microscopic float64 jitter."""
        np.random.seed(42)
        grid = np.linspace(0.005, 1.5, 500)
        jitter = np.random.normal(0, 1e-12, size=grid.shape)
        perturbed = np.sort(grid + jitter)

        denoised = apply_hendecacosidodecagonal_hyperbolic_deadband(perturbed, delta_noise=0.035, alpha_pos=560.0)
        rho, _ = spearmanr(perturbed, denoised)
        assert math.isclose(rho, 1.0, rel_tol=1e-5), f"Rank monotonicity violated: Spearman rho={rho}"

    def test_mathematical_boundary_and_edge_values(self):
        """Stress: Verify stability at 0.0, -0.0, +-inf, NaN, and subnormal floats."""
        edge_inputs = np.array([0.0, -0.0, np.inf, -np.inf, np.nan, 1e-320, -1e-320, 5e-324], dtype=np.float64)
        out = apply_hendecacosidodecagonal_hyperbolic_deadband(edge_inputs)

        assert out[0] == 0.0
        assert math.copysign(1.0, out[0]) == 1.0
        assert out[1] == 0.0
        assert math.copysign(1.0, out[1]) == -1.0
        assert np.isinf(out[2]) and out[2] > 0
        assert np.isinf(out[3]) and out[3] < 0
        assert np.isnan(out[4])
        assert out[5] == 0.0  # Subnormal smoothly underflows to 0
        assert out[6] == 0.0
        assert out[7] == 0.0

    def test_regime_asymmetric_deadband(self):
        """Stress: Verify regime bear multiplier (chi_bear) widens negative deadband under stress."""
        z = np.array([-0.040, 0.040])
        # Under normal regime, delta_neg = delta_pos = 0.035, so -0.040 passes through
        out_normal = apply_hendecacosidodecagonal_hyperbolic_deadband(z, delta_noise=0.035, regime="BULL_LOW_VOL")
        # Under CRISIS regime, chi_bear = 1.40 -> delta_neg = 0.049 > 0.040, suppressing negative noise
        out_crisis = apply_hendecacosidodecagonal_hyperbolic_deadband(z, delta_noise=0.035, regime="CRISIS")

        assert abs(out_normal[0]) > abs(out_crisis[0]), "Crisis regime failed to suppress negative noise"
        assert math.isclose(out_normal[1], out_crisis[1], rel_tol=1e-5), "Positive signal altered by bear regime"

    def test_deadband_polymorphic_types_and_aliases(self):
        """Stress: Verify scalar, Series, and array inputs produce identical results across aliases."""
        scalar_val = 0.25
        res_scalar = apply_hendecacosidodecagonal_hyperbolic_deadband(scalar_val)
        assert isinstance(res_scalar, float)
        assert math.isclose(res_scalar, 0.25, rel_tol=1e-4)

        s = pd.Series([0.0001, 0.30], index=['low', 'high'])
        res_s = apply_hendecacosidodecagonal_hyperbolic_deadband(s)
        assert isinstance(res_s, pd.Series)
        assert res_s['low'] == 0.0
        assert math.isclose(res_s['high'], 0.30, rel_tol=1e-4)

        arr = np.array([0.0001, 0.25, -0.0001, -0.25])
        ref = apply_hendecacosidodecagonal_hyperbolic_deadband(arr)
        assert np.allclose(apply_560th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_560_deadband(arr), ref)
        assert np.allclose(compute_phase94_deadband(arr), ref)
        assert np.allclose(apply_phase94_deadband(arr), ref)
        assert np.allclose(phase94_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v94(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v94(arr), ref)
        assert np.allclose(Phase94FactorSuppressionEngine.apply_hendecacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_hendecacosidodecagonal_hyperbolic_deadband(arr), ref)


class TestRankModulationAdversarialExtremes:
    """Adversarial stress harness for 119th-order hyper-convex rank modulation (F440)."""

    def test_all_15_regimes_explosion_and_finite_ceiling(self):
        """Stress: Verify explosive convex separation at r=1.0 without float64 overflow across all regimes."""
        ranks = np.array([0.0, 0.5, 0.8, 0.9, 0.95, 0.99, 1.0], dtype=np.float64)

        for reg, gamma in REGIME_GAMMA_TOP_V94.items():
            mod = compute_phase94_hyperconvex_rank_modulation(ranks, regime=reg)
            assert np.all(np.isfinite(mod)), f"Non-finite output in regime {reg}"
            assert np.all(np.diff(mod) > 0), f"Monotonicity violated in regime {reg}"
            # Check boundaries
            assert math.isclose(mod[0], 0.50, rel_tol=1e-5), f"Base weight mismatch at r=0 in {reg}"
            assert mod[-1] > 30.0, f"Insufficient boost at r=1 in {reg}"
            # Even at max gamma=32.0, exp(32) ~ 7.896e13, mod[-1] ~ 2.858e14 < 1e308
            assert mod[-1] < 1e20, f"Unexpectedly large weight in {reg}: {mod[-1]}"

    def test_top_decile_hyperconvex_sensitivity(self):
        """Stress: Verify convexity order 119 isolates top-1% decile while keeping median flat."""
        ranks = np.array([0.0, 0.25, 0.50, 0.75, 0.90, 0.99, 1.0])
        mod = compute_phase94_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")

        # Flat linear-like region for r <= 0.75 (0.50 + 3.62 * r)
        assert math.isclose(mod[2], 0.50 + 3.62 * 0.50, rel_tol=1e-4)  # r^119 = 0.5^119 ~ 1.5e-36 -> exp ~ 1
        assert math.isclose(mod[3], 0.50 + 3.62 * 0.75, rel_tol=1e-4)  # 0.75^119 ~ 1.4e-15 -> exp ~ 1

        # Super-exponential explosive surge between 0.99 and 1.00
        surge_ratio = mod[-1] / mod[-2]
        assert surge_ratio > 10.0, f"Convexity failed to create top-1% separation: {surge_ratio}"

    def test_negative_signal_branch_inversion(self):
        """Stress: Verify negative signals z < 0 strictly follow g_neg(r) = 1.35 - 1.00 * r."""
        z_neg = np.array([-0.01, -0.15, -0.50, -2.00])
        ranks = np.array([0.0, 0.35, 0.70, 1.0])
        mod = compute_phase94_hyperconvex_rank_modulation(ranks, z_denoised=z_neg, regime="BULL_LOW_VOL")

        expected = 1.35 - 1.00 * ranks
        assert np.allclose(mod, expected), f"Negative branch failed: got {mod}, expected {expected}"
        assert np.all(np.diff(mod) < 0), "Negative branch should be monotonically decreasing with rank"

    def test_adversarial_out_of_bounds_inputs(self):
        """Stress: Verify extreme inputs (r < 0, r > 1) are cleanly clipped to [0, 1]."""
        extreme_r = np.array([-100.0, -1.0, 0.0, 1.0, 2.0, 50.0])
        mod = compute_phase94_hyperconvex_rank_modulation(extreme_r, regime="BULL_LOW_VOL")

        assert math.isclose(mod[0], 0.50, rel_tol=1e-5)  # -100 clipped to 0
        assert math.isclose(mod[1], 0.50, rel_tol=1e-5)  # -1 clipped to 0
        assert math.isclose(mod[2], 0.50, rel_tol=1e-5)  # 0
        assert math.isclose(mod[3], mod[4], rel_tol=1e-5)  # 2 clipped to 1
        assert math.isclose(mod[3], mod[5], rel_tol=1e-5)  # 50 clipped to 1

    def test_rank_modulation_aliases(self):
        """Stress: Verify all Phase 94 rank modulation aliases produce identical results."""
        ranks = np.array([0.15, 0.85])
        ref = compute_phase94_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase94_rank_warping(ranks), ref)
        assert np.allclose(compute_phase94_rank_modulation(ranks), ref)
        assert np.allclose(phase94_rank_modulation(ranks), ref)
        assert np.allclose(phase94_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v94(ranks), ref)
        assert np.allclose(Phase94FactorSuppressionEngine.compute_phase94_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase94_hyperconvex_rank_modulation(ranks), ref)


class TestMonsterWhittakerCouplerAdversarialExtremes:
    """Adversarial stress harness for Monster Whittaker Coupler (F441)."""

    def setup_method(self):
        self.coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()

    def test_coupler_phase94_hyperparameters(self):
        """Verify Phase 94 exact hyperparameters: kappa=38.60, lambda=18-nines, harmony_boost=9.20."""
        assert self.coupler.version == 94
        assert self.coupler.is_phase94 is True
        assert self.coupler.kappa_monster_whit == 38.60
        assert self.coupler.lambda_monster == 0.99999999999999999
        assert self.coupler.harmony_boost == 9.20

    def test_zero_variance_identical_pillars(self):
        """Stress: When all pillars are identical, topological defect and energy must be zero, FERI = 1.0."""
        df_zero = pd.DataFrame({
            'val': [0.5, 0.2, 0.9],
            'mom': [0.5, 0.2, 0.9],
            'flow': [0.5, 0.2, 0.9],
            'cat': [0.5, 0.2, 0.9],
            'net': [0.5, 0.2, 0.9],
        })
        res = self.coupler(df_zero)

        assert np.allclose(res['e_monster_whit'], 0.0)
        assert np.allclose(res['z_monster_whit'], 1.0)
        assert np.allclose(res['FERI_v94'], 1.0)

    def test_extreme_variance_inputs(self):
        """Stress: High variance inputs across realistic quant bounds (up to +-30 standard deviations)."""
        df_extreme = pd.DataFrame({
            'val': [25.0, -25.0, 10.0],
            'mom': [-25.0, 25.0, -10.0],
            'flow': [10.0, -10.0, 5.0],
            'cat': [-10.0, 10.0, -5.0],
            'net': [20.0, -20.0, 0.0],
        })
        res = self.coupler(df_extreme)

        assert np.all(np.isfinite(res['FERI_v94']))
        # Massive obstruction energy causes FERI to collapse to zero
        assert np.all(res['FERI_v94'] < 1e-10)

    def test_single_symbol_and_dict_inputs(self):
        """Stress: Single 1D vector of length 5 and Dict of pillars."""
        p_1d = np.array([0.8, 0.6, 0.4, 0.9, 0.5])
        res_1d = self.coupler(p_1d)
        assert isinstance(res_1d['FERI_v94'], (float, np.floating))
        assert np.isfinite(res_1d['FERI_v94'])

        p_dict = {
            'val': [0.6, 0.7],
            'mom': [0.5, 0.8],
            'flow': [0.4, 0.6],
            'cat': [0.9, 0.5],
            'net': [0.3, 0.4],
        }
        res_dict = self.coupler(p_dict)
        assert len(res_dict['FERI_v94']) == 2
        assert np.all(np.isfinite(res_dict['FERI_v94']))

    def test_nan_resilience_in_pillars(self):
        """Stress: NaN in pillar DataFrame gracefully replaced with zero without raising errors."""
        df_nan = pd.DataFrame({
            'val': [np.nan, 0.5],
            'mom': [0.5, np.nan],
            'flow': [np.nan, 0.5],
            'cat': [0.5, np.nan],
            'net': [0.5, 0.5],
        })
        res = self.coupler(df_nan)
        assert np.all(np.isfinite(res['FERI_v94']))

    def test_dimension_validation(self):
        """Stress: Coupler must reject inputs with pillar count != 5."""
        invalid_mat = np.ones((10, 4))
        with pytest.raises(ValueError, match="5 canonical pillars"):
            self.coupler(invalid_mat)

    def test_backward_compatibility_and_cascade(self):
        """Stress: Verify instantiation with earlier versions maintains historical parameter regimes."""
        c93 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=93)
        assert c93.kappa_monster_whit == 38.00
        assert c93.harmony_boost == 8.85
        assert c93.is_phase94 is False
        assert c93.is_phase93 is True

        c85 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=85)
        assert c85.kappa_monster_whit == 33.20
        assert c85.harmony_boost == 6.55

    def test_comprehensive_output_key_contracts(self):
        """Stress: Verify all expected output keys are present and correctly typed."""
        df = pd.DataFrame({
            'val': [0.5], 'mom': [0.55], 'flow': [0.45], 'cat': [0.6], 'net': [0.4]
        })
        res = self.coupler(df)

        expected_keys = [
            'FERI_v94', 'feri_v94', 'f_out_94',
            'FERI_v93', 'feri_v93', 'f_out_93',
            'FERI_v92', 'feri_v92', 'f_out_92',
            'FERI_v91', 'feri_v91', 'f_out_91',
            'FERI_v90', 'feri_v90', 'f_out_90',
            'FERI_v89', 'feri_v89', 'f_out_89',
            'FERI_v88', 'feri_v88', 'f_out_88',
            'FERI_v66', 'FERI_v55', 'FERI_v48',
            'h_monster_whit', 'z_monster_whit', 'e_monster_whit', 'h_decay'
        ]
        for key in expected_keys:
            assert key in res, f"Expected key {key} missing from Coupler output"

    def test_coupler_alias_tree(self):
        """Stress: Verify full alias tree and functional entrypoint."""
        assert Phase94Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        df = pd.DataFrame({
            'val': [0.5], 'mom': [0.5], 'flow': [0.5], 'cat': [0.5], 'net': [0.5]
        })
        res = compute_phase94_coupling(df)
        assert 'FERI_v94' in res

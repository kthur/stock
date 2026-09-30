"""
tests/test_phase88_alpha.py

Unit test suite for Phase 88 Quantitative Alpha Enhancement (Features F410, F411):
- Feature F410: Asymmetric Pentacosidodecagonal (512th-Order) Hyperbolic Deadband
  (alpha_pos = 512.0, delta_noise = 0.035, noise suppression < 10^-512 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F410: 107th-Order Hyperconvex Rank Modulation
  (g_v88(r) = 0.50 + 3.38 * r * exp(gamma_top * r^107) with REGIME_GAMMA_TOP_V88,
   gamma_top <= 24.80, strictly monotonic non-decreasing, g(1.0) > 10^7).
- Feature F411: Borcherds-Moonshine Monster Whittaker Coupler v88
  (defaults to version=88, kappa_monster_whit=35.00, lambda_monster=0.99999999999999,
   is_phase88=True, harmony_boost=7.10, output keys FERI_v88, feri_v88, f_out_88, FERI_v87, feri_v87, f_out_87).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import pytest
import math
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_pentacosidodecagonal_hyperbolic_deadband,
    apply_pentacosidodecadihedral_hyperbolic_deadband,
    apply_quingentadodecagonal_hyperbolic_deadband,
    apply_pentacentadodecagonal_hyperbolic_deadband,
    apply_pentacosidodeca_hyperbolic_deadband,
    apply_pentacosidodecagonal_deadband,
    pentacosidodecagonal_deadband,
    pentacosidodecagonal_hyperbolic_deadband,
    compute_phase88_deadband,
    apply_phase88_deadband,
    phase88_deadband,
    apply_512th_order_hyperbolic_deadband,
    apply_512th_deadband,
    apply_512_deadband,
    apply_hyperbolic_deadband_v88,
    suppress_factor_noise_hyperbolic_v88,
    compute_phase88_hyperconvex_rank_modulation,
    compute_phase88_rank_warping,
    compute_phase88_rank_modulation,
    phase88_rank_modulation,
    phase88_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v88,
    REGIME_GAMMA_TOP_V88,
    get_regime_adaptive_gamma_top_v88,
    Phase88FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase88Coupler,
    Phase88WhittakerDrinfeldCoupler,
    Phase88BorcherdsMoonshineCoupler,
    Phase88MonsterWhittakerCoupler,
    compute_phase88_coupling,
    Phase87Coupler,
    Phase86Coupler,
    Phase85Coupler,
    EnsembleScoringEngine,
)


class TestPhase88AlphaEnhancements:
    def test_feature_f411_coupler_properties_v88(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=35.00,
            lambda_monster=0.99999999999999,
            version=88,
        )
        assert coupler.kappa_monster_whit == 35.00
        assert coupler.lambda_monster == 0.99999999999999
        assert coupler.version == 88
        assert coupler.is_phase88 is True
        assert coupler.harmony_boost == 7.10

        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_monster_whit' in res
        assert 'z_monster_whit' in res
        assert 'e_monster_whit' in res
        assert 'FERI_v88' in res
        assert 'feri_v88' in res
        assert 'f_out_88' in res
        assert 'FERI_v87' in res
        assert 'feri_v87' in res
        assert 'f_out_87' in res

        feri_88 = res['FERI_v88']
        assert len(feri_88) == len(p_df)
        assert np.all(np.isfinite(feri_88))

    def test_feature_f411_coupler_aliases(self):
        assert Phase88Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase88WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase88BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase88MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase87Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase88_coupling(p_df)
        assert 'FERI_v88' in res

    def test_feature_f410_deadband_suppression(self):
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-512 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_pentacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=512.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_pentacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=512.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_pentacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=512.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f410_deadband_aliases(self):
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_pentacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_pentacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentadodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentadodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacosidodecagonal_deadband(arr), ref)
        assert np.allclose(pentacosidodecagonal_deadband(arr), ref)
        assert np.allclose(pentacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase88_deadband(arr), ref)
        assert np.allclose(apply_phase88_deadband(arr), ref)
        assert np.allclose(phase88_deadband(arr), ref)
        assert np.allclose(apply_512th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_512th_deadband(arr), ref)
        assert np.allclose(apply_512_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v88(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v88(arr), ref)
        assert np.allclose(Phase88FactorSuppressionEngine.apply_pentacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_pentacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f410_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase88_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

    def test_feature_f410_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V88.items():
            g = get_regime_adaptive_gamma_top_v88(regime)
            assert g == gamma
            assert g <= 24.80

    def test_feature_f410_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase88_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase88_rank_warping(ranks), ref)
        assert np.allclose(compute_phase88_rank_modulation(ranks), ref)
        assert np.allclose(phase88_rank_modulation(ranks), ref)
        assert np.allclose(phase88_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v88(ranks), ref)
        assert np.allclose(Phase88FactorSuppressionEngine.compute_phase88_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase88_hyperconvex_rank_modulation(ranks), ref)

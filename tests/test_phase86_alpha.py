"""
tests/test_phase86_alpha.py

Unit test suite for Phase 86 Quantitative Alpha Enhancement (Features F400, F401):
- Feature F400: Asymmetric Tetracosianonacontahexagonal (496th-Order) Hyperbolic Deadband
  (alpha_pos = 496.0, delta_noise = 0.035, noise suppression < 10^-496 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F400: 103rd-Order Hyperconvex Rank Modulation
  (g_v86(r) = 0.50 + 3.30 * r * exp(gamma_top * r^103) with REGIME_GAMMA_TOP_V86,
   strictly monotonic non-decreasing, g(1.0) > 10^7).
- Feature F401: Borcherds-Moonshine Monster Whittaker Coupler v86
  (defaults to version=86, kappa=33.90, lambda=0.9999999999999, 184th-order chiral oper obstruction,
   96th-order defect invariant, harmony boost 6.65 when h > 0.65, output keys FERI_v86, feri_v86, f_out_86).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import pytest
import math
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_tetracosianonacontahexagonal_hyperbolic_deadband,
    apply_tetracosianonacontahexadihedral_hyperbolic_deadband,
    apply_quadringentanonahexagonal_hyperbolic_deadband,
    apply_tetracentanonahexagonal_hyperbolic_deadband,
    apply_tetracosianonacontahexa_hyperbolic_deadband,
    apply_tetracosianonacontahexagonal_deadband,
    tetracosianonacontahexagonal_deadband,
    tetracosianonacontahexagonal_hyperbolic_deadband,
    compute_phase86_deadband,
    apply_phase86_deadband,
    phase86_deadband,
    apply_496th_order_hyperbolic_deadband,
    apply_496th_deadband,
    apply_496_deadband,
    apply_hyperbolic_deadband_v86,
    suppress_factor_noise_hyperbolic_v86,
    compute_phase86_hyperconvex_rank_modulation,
    compute_phase86_rank_warping,
    compute_phase86_rank_modulation,
    phase86_rank_modulation,
    phase86_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v86,
    REGIME_GAMMA_TOP_V86,
    get_regime_adaptive_gamma_top_v86,
    Phase86FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase86Coupler,
    Phase86WhittakerDrinfeldCoupler,
    Phase86BorcherdsMoonshineCoupler,
    Phase86MonsterWhittakerCoupler,
    compute_phase86_coupling,
    Phase85Coupler,
    Phase84Coupler,
    Phase83Coupler,
    EnsembleScoringEngine,
)


class TestPhase86AlphaEnhancements:
    def test_feature_f401_coupler_properties_v86(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=33.90,
            lambda_monster=0.9999999999999,
            version=86,
        )
        assert coupler.kappa_monster_whit == 33.90
        assert coupler.lambda_monster == 0.9999999999999
        assert coupler.version == 86
        assert coupler.is_phase86 is True
        assert coupler.harmony_boost == 6.65

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
        assert 'FERI_v86' in res
        assert 'feri_v86' in res
        assert 'f_out_86' in res
        assert 'FERI_v85' in res
        assert 'feri_v85' in res
        assert 'f_out_85' in res

        feri_86 = res['FERI_v86']
        assert len(feri_86) == len(p_df)
        assert np.all(np.isfinite(feri_86))

    def test_feature_f401_coupler_aliases(self):
        assert Phase86Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase86_coupling(p_df)
        assert 'FERI_v86' in res

    def test_feature_f400_deadband_suppression(self):
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-496
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_tetracosianonacontahexagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_tetracosianonacontahexagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_tetracosianonacontahexagonal_hyperbolic_deadband(grid, delta_noise=0.035)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f400_deadband_aliases(self):
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_tetracosianonacontahexagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_tetracosianonacontahexadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quadringentanonahexagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracentanonahexagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosianonacontahexa_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosianonacontahexagonal_deadband(arr), ref)
        assert np.allclose(tetracosianonacontahexagonal_deadband(arr), ref)
        assert np.allclose(tetracosianonacontahexagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase86_deadband(arr), ref)
        assert np.allclose(apply_phase86_deadband(arr), ref)
        assert np.allclose(phase86_deadband(arr), ref)
        assert np.allclose(apply_496th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_496th_deadband(arr), ref)
        assert np.allclose(apply_496_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v86(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v86(arr), ref)
        assert np.allclose(Phase86FactorSuppressionEngine.apply_tetracosianonacontahexagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_tetracosianonacontahexagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f400_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase86_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

    def test_feature_f400_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V86.items():
            g = get_regime_adaptive_gamma_top_v86(regime)
            assert g == gamma
            assert g <= 23.00

    def test_feature_f400_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase86_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase86_rank_warping(ranks), ref)
        assert np.allclose(compute_phase86_rank_modulation(ranks), ref)
        assert np.allclose(phase86_rank_modulation(ranks), ref)
        assert np.allclose(phase86_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v86(ranks), ref)
        assert np.allclose(Phase86FactorSuppressionEngine.compute_phase86_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase86_hyperconvex_rank_modulation(ranks), ref)

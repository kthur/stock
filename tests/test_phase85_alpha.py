"""
tests/test_phase85_alpha.py

Unit test suite for Phase 85 Quantitative Alpha Enhancement (Features F395, F396):
- Feature F395: Asymmetric Tetracosiaoctacontaoctagonal (488th-Order) Hyperbolic Deadband
  (alpha_pos = 488.0, delta_noise = 0.035, noise suppression < 10^-488 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F395: 101st-Order Hyperconvex Rank Modulation
  (g_v85(r) = 0.50 + 3.25 * r * exp(gamma_top * r^101) with REGIME_GAMMA_TOP_V85,
   strictly monotonic non-decreasing, g(1.0) > 10^7).
- Feature F396: Borcherds-Moonshine Monster Whittaker Coupler v85
  (defaults to version=85, kappa=33.20, lambda=0.9999999999995, 182nd-order chiral oper obstruction,
   94th-order defect invariant, harmony boost 6.55 when h > 0.65, output keys FERI_v85, feri_v85, f_out_85).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import pytest
import math
import numpy as np
import pandas as pd

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
    REGIME_GAMMA_TOP_V85,
    get_regime_adaptive_gamma_top_v85,
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
    Phase84Coupler,
    Phase83Coupler,
    EnsembleScoringEngine,
)


class TestPhase85AlphaEnhancements:
    def test_feature_f396_coupler_properties_v85(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=33.20,
            lambda_monster=0.9999999999995,
            version=85,
        )
        assert coupler.kappa_monster_whit == 33.20
        assert coupler.lambda_monster == 0.9999999999995
        assert coupler.version == 85
        assert coupler.is_phase85 is True
        assert coupler.harmony_boost == 6.55

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
        assert 'FERI_v85' in res
        assert 'feri_v85' in res
        assert 'f_out_85' in res
        assert 'FERI_v84' in res
        assert 'feri_v84' in res
        assert 'f_out_84' in res

        feri_85 = res['FERI_v85']
        assert len(feri_85) == len(p_df)
        assert np.all(np.isfinite(feri_85))

    def test_feature_f396_coupler_aliases(self):
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

    def test_feature_f395_deadband_suppression(self):
        sub_noise = np.array([0.0001, 0.0002, 0.0003])
        denoised = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        strong_sig = np.array([0.150, 0.20, 0.50])
        denoised_strong = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

    def test_feature_f395_deadband_aliases(self):
        arr = np.array([0.0002, 0.18])
        ref = apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_tetracosiaoctacontaoctadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quadringentaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracentaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaoctacontaocta_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaoctacontaoctagonal_deadband(arr), ref)
        assert np.allclose(tetracosiaoctacontaoctagonal_deadband(arr), ref)
        assert np.allclose(tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase85_deadband(arr), ref)
        assert np.allclose(apply_phase85_deadband(arr), ref)
        assert np.allclose(phase85_deadband(arr), ref)
        assert np.allclose(apply_488th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_488th_deadband(arr), ref)
        assert np.allclose(apply_488_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v85(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v85(arr), ref)
        assert np.allclose(Phase85FactorSuppressionEngine.apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_tetracosiaoctacontaoctagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f395_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase85_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

    def test_feature_f395_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V85.items():
            g = get_regime_adaptive_gamma_top_v85(regime)
            assert g == gamma
            assert g <= 22.70

    def test_feature_f395_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase85_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase85_rank_warping(ranks), ref)
        assert np.allclose(compute_phase85_rank_modulation(ranks), ref)
        assert np.allclose(phase85_rank_modulation(ranks), ref)
        assert np.allclose(phase85_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v85(ranks), ref)
        assert np.allclose(Phase85FactorSuppressionEngine.compute_phase85_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase85_hyperconvex_rank_modulation(ranks), ref)

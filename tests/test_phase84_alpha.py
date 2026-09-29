import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiaoctacontagonal_hyperbolic_deadband,
    apply_tetracosiaoctacontadihedral_hyperbolic_deadband,
    apply_quadringentaoctacontagonal_hyperbolic_deadband,
    apply_tetracentaoctacontagonal_hyperbolic_deadband,
    apply_tetracosiaoctaconta_hyperbolic_deadband,
    apply_tetracosiaoctacontagonal_deadband,
    tetracosiaoctacontagonal_deadband,
    tetracosiaoctacontagonal_hyperbolic_deadband,
    compute_phase84_deadband,
    apply_phase84_deadband,
    phase84_deadband,
    apply_480th_order_hyperbolic_deadband,
    apply_480th_deadband,
    apply_480_deadband,
    apply_hyperbolic_deadband_v84,
    suppress_factor_noise_hyperbolic_v84,
    compute_phase84_hyperconvex_rank_modulation,
    compute_phase84_rank_warping,
    compute_phase84_rank_modulation,
    phase84_rank_modulation,
    phase84_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v84,
    REGIME_GAMMA_TOP_V84,
    get_regime_adaptive_gamma_top_v84,
    Phase84FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase84Coupler,
    Phase84WhittakerDrinfeldCoupler,
    Phase84BorcherdsMoonshineCoupler,
    Phase84MonsterWhittakerCoupler,
    compute_phase84_coupling,
    Phase83Coupler,
    Phase82Coupler,
    Phase81Coupler,
    EnsembleScoringEngine,
)


class TestPhase84AlphaEnhancements:
    def test_feature_f391_coupler_properties_v84(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=32.50,
            lambda_monster=0.999999999999,
            version=84,
        )
        assert coupler.kappa_monster_whit == 32.50
        assert coupler.lambda_monster == 0.999999999999
        assert coupler.version == 84
        assert coupler.is_phase84 is True

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
        assert 'FERI_v84' in res
        assert 'feri_v84' in res
        assert 'f_out_84' in res
        assert 'FERI_v83' in res
        assert 'feri_v83' in res
        assert 'f_out_83' in res

        feri_84 = res['FERI_v84']
        assert len(feri_84) == len(p_df)
        assert np.all(np.isfinite(feri_84))

    def test_feature_f391_coupler_aliases(self):
        assert Phase84Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase84WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase84BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase84MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase84_coupling(p_df)
        assert 'FERI_v84' in res

    def test_feature_f390_deadband_suppression(self):
        sub_noise = np.array([0.005, 0.010, 0.020])
        denoised = apply_tetracosiaoctacontagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035)
        for val in denoised:
            assert abs(val) < 1e-10

        strong_sig = np.array([0.10, 0.20, 0.50])
        denoised_strong = apply_tetracosiaoctacontagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

    def test_feature_f390_deadband_aliases(self):
        arr = np.array([0.01, 0.15])
        ref = apply_tetracosiaoctacontagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_tetracosiaoctacontadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quadringentaoctacontagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracentaoctacontagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaoctaconta_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaoctacontagonal_deadband(arr), ref)
        assert np.allclose(tetracosiaoctacontagonal_deadband(arr), ref)
        assert np.allclose(tetracosiaoctacontagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase84_deadband(arr), ref)
        assert np.allclose(apply_phase84_deadband(arr), ref)
        assert np.allclose(phase84_deadband(arr), ref)
        assert np.allclose(apply_480th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_480th_deadband(arr), ref)
        assert np.allclose(apply_480_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v84(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v84(arr), ref)
        assert np.allclose(Phase84FactorSuppressionEngine.apply_tetracosiaoctacontagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_tetracosiaoctacontagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f390_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase84_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e9

    def test_feature_f390_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V84.items():
            g = get_regime_adaptive_gamma_top_v84(regime)
            assert g == gamma
            assert g <= 22.40

    def test_feature_f390_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase84_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase84_rank_warping(ranks), ref)
        assert np.allclose(compute_phase84_rank_modulation(ranks), ref)
        assert np.allclose(phase84_rank_modulation(ranks), ref)
        assert np.allclose(phase84_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v84(ranks), ref)
        assert np.allclose(Phase84FactorSuppressionEngine.compute_phase84_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase84_hyperconvex_rank_modulation(ranks), ref)

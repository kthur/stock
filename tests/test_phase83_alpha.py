import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiaheptacontadual_hyperbolic_deadband,
    apply_tetracosiaheptacontadihedral_hyperbolic_deadband,
    apply_quadringentaheptacontadual_hyperbolic_deadband,
    apply_tetracentapentacontadual_hyperbolic_deadband,
    apply_tetracosiaheptaconta_hyperbolic_deadband,
    apply_tetracosiaheptacontadual_deadband,
    tetracosiaheptacontadual_deadband,
    tetracosiaheptacontadual_hyperbolic_deadband,
    compute_phase83_deadband,
    apply_phase83_deadband,
    phase83_deadband,
    apply_472nd_order_hyperbolic_deadband,
    apply_472nd_deadband,
    apply_472_deadband,
    apply_hyperbolic_deadband_v83,
    suppress_factor_noise_hyperbolic_v83,
    compute_phase83_hyperconvex_rank_modulation,
    compute_phase83_rank_warping,
    compute_phase83_rank_modulation,
    phase83_rank_modulation,
    phase83_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v83,
    REGIME_GAMMA_TOP_V83,
    get_regime_adaptive_gamma_top_v83,
    Phase83FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase83Coupler,
    Phase83WhittakerDrinfeldCoupler,
    Phase83BorcherdsMoonshineCoupler,
    Phase83MonsterWhittakerCoupler,
    compute_phase83_coupling,
    Phase82Coupler,
    Phase81Coupler,
    Phase80Coupler,
    EnsembleScoringEngine,
)


class TestPhase83AlphaEnhancements:
    def test_feature_f387_coupler_properties_v83(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=31.80,
            lambda_monster=0.999999999998,
            version=83,
        )
        assert coupler.kappa_monster_whit == 31.80
        assert coupler.lambda_monster == 0.999999999998
        assert coupler.version == 83
        assert coupler.is_phase83 is True

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
        assert 'FERI_v83' in res
        assert 'feri_v83' in res
        assert 'f_out_83' in res
        assert 'FERI_v82' in res
        assert 'feri_v82' in res
        assert 'f_out_82' in res

        feri_83 = res['FERI_v83']
        assert len(feri_83) == len(p_df)
        assert np.all(np.isfinite(feri_83))

    def test_feature_f387_coupler_aliases(self):
        assert Phase83Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase83WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase83BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase83MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase83_coupling(p_df)
        assert 'FERI_v83' in res

    def test_feature_f386_deadband_suppression(self):
        # Noise below threshold delta=0.035 should be aggressively suppressed by 472nd order
        sub_noise = np.array([0.005, 0.010, 0.020])
        denoised = apply_tetracosiaheptacontadual_hyperbolic_deadband(sub_noise, delta_noise=0.035)
        for val in denoised:
            assert abs(val) < 1e-10

        # Signal well above threshold should be preserved
        strong_sig = np.array([0.10, 0.20, 0.50])
        denoised_strong = apply_tetracosiaheptacontadual_hyperbolic_deadband(strong_sig, delta_noise=0.035)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

    def test_feature_f386_deadband_aliases(self):
        arr = np.array([0.01, 0.15])
        ref = apply_tetracosiaheptacontadual_hyperbolic_deadband(arr)

        assert np.allclose(apply_tetracosiaheptacontadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quadringentaheptacontadual_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracentapentacontadual_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaheptaconta_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_tetracosiaheptacontadual_deadband(arr), ref)
        assert np.allclose(tetracosiaheptacontadual_deadband(arr), ref)
        assert np.allclose(tetracosiaheptacontadual_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase83_deadband(arr), ref)
        assert np.allclose(apply_phase83_deadband(arr), ref)
        assert np.allclose(phase83_deadband(arr), ref)
        assert np.allclose(apply_472nd_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_472nd_deadband(arr), ref)
        assert np.allclose(apply_472_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v83(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v83(arr), ref)
        assert np.allclose(Phase83FactorSuppressionEngine.apply_tetracosiaheptacontadual_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_tetracosiaheptacontadual_hyperbolic_deadband(arr), ref)

    def test_feature_f386_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase83_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        # Monotonically increasing
        assert np.all(np.diff(mod) > 0)
        # Top rank should receive massive convexity boost from r^97
        assert mod[-1] > 1e9

    def test_feature_f386_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V83.items():
            g = get_regime_adaptive_gamma_top_v83(regime)
            assert g == gamma
            assert g <= 22.10

    def test_feature_f386_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase83_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase83_rank_warping(ranks), ref)
        assert np.allclose(compute_phase83_rank_modulation(ranks), ref)
        assert np.allclose(phase83_rank_modulation(ranks), ref)
        assert np.allclose(phase83_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v83(ranks), ref)
        assert np.allclose(Phase83FactorSuppressionEngine.compute_phase83_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase83_hyperconvex_rank_modulation(ranks), ref)

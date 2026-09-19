import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_bicentaoctacontagonal_hyperbolic_deadband,
    compute_phase59_hyperconvex_rank_modulation,
    compute_phase59_rank_warping,
    REGIME_GAMMA_TOP_V59,
    get_regime_adaptive_gamma_top_v59,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerCoupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerFactorCoupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterCoupler,
    GeometricLanglandsBorcherdsMoonshineMonsterWhittakerCoupler,
    GeometricLanglandsBorcherdsMoonshineMonsterCoupler,
    BorcherdsMoonshineMonsterWhittakerSheafHomologyCoupler,
    BorcherdsMoonshineMonsterWhittakerChiralOperCoupler,
    BorcherdsMoonshineMonsterWhittakerHomologyCoupler,
    BorcherdsMoonshineMonsterWhittakerCoupler,
    BorcherdsMoonshineMonsterCoupler,
    BorcherdsMonsterWhittakerSheafMoonshineHomologyCoupler,
    BorcherdsMonsterWhittakerMoonshineCoupler,
    BorcherdsMoonshineMonsterTensorCoupler,
    WhittakerBorcherdsMoonshineMonsterSheafCoupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterSuperalgebraCoupler,
    Phase59Coupler,
    Phase58Coupler,
    Phase57Coupler,
    Phase56Coupler,
    Phase55Coupler,
    Phase54Coupler,
    Phase53Coupler,
    Phase52Coupler,
    Phase51Coupler,
    Phase50Coupler,
    Phase49Coupler,
    Phase48Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology9Coupler,
    DrinfeldHigherHomology9Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology8Coupler,
    DrinfeldHigherHomology8Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology7Coupler,
    DrinfeldHigherHomology7Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology6Coupler,
    DrinfeldHigherHomology6Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology5Coupler,
    DrinfeldHigherHomology5Coupler,
    EnsembleScoringEngine,
)


class TestPhase59AlphaEnhancements:
    def test_feature_f266_quantum_geometric_langlands_borcherds_moonshine_monster_whittaker_coupler_properties(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=16.00,
            lambda_monster=0.999,
        )
        assert coupler.kappa_monster_whit == 16.00
        assert coupler.lambda_monster == 0.999

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
        assert 'FERI_v59' in res
        assert 'feri_v59' in res
        assert 'FERI_v58' in res
        assert 'feri_v58' in res
        assert 'FERI_v57' in res
        assert 'feri_v57' in res
        assert 'FERI_v56' in res
        assert 'FERI_v55' in res
        assert 'FERI_v54' in res
        assert 'FERI_v53' in res
        assert 'FERI_v52' in res
        assert 'FERI_v51' in res
        assert 'FERI_v50' in res
        assert 'FERI_v49' in res
        assert 'FERI_v48' in res
        assert 'Z_monster_whit' in res
        assert 'E_monster_whit' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v59']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Dispersion and obstruction ordering
        assert res['e_monster_whit'].iloc[0] < res['e_monster_whit'].iloc[1] < res['e_monster_whit'].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_monster_whit'], float)
        assert np.isclose(res_1d['e_monster_whit'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['FERI_v59'], 1.0, atol=1e-7)

    def test_feature_f266_quantum_geometric_langlands_aliases_and_exports(self):
        assert Phase59Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase58Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase57Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase56Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology9Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert DrinfeldHigherHomology9Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology8Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert DrinfeldHigherHomology8Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        res_class = EnsembleScoringEngine.compute_quantum_geometric_langlands_borcherds_moonshine_monster_whittaker_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_monster_whit' in res_class
        assert 'FERI_v59' in res_class

    def test_feature_f266_54th_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase59_hyperconvex_rank_modulation(ranks, gamma_top=12.60)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.98 * exp(12.60)
        expected_top = 0.50 + 1.98 * math.exp(12.60)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 100000.0
        assert g_mod[-1] > 570000.0

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '54th-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest (<= 1.95) while r=1.0 explodes
        g_70 = compute_phase59_hyperconvex_rank_modulation(0.70, gamma_top=12.60)
        assert g_70 <= 1.95

        # With negative z_denoised
        g_neg = compute_phase59_hyperconvex_rank_modulation(ranks, gamma_top=12.60, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f266_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v59('BULL_LOW_VOL') == 12.60
        assert get_regime_adaptive_gamma_top_v59('BULL_HIGH_VOL') == 10.08
        assert get_regime_adaptive_gamma_top_v59('SIDEWAYS') == 7.56
        assert get_regime_adaptive_gamma_top_v59('SIDEWAYS_LOW_VOL') == 7.56
        assert get_regime_adaptive_gamma_top_v59('SIDEWAYS_HIGH_VOL') == 5.04
        assert get_regime_adaptive_gamma_top_v59('BEAR') == 2.52
        assert get_regime_adaptive_gamma_top_v59('BEAR_LOW_VOL') == 2.52
        assert get_regime_adaptive_gamma_top_v59('BEAR_HIGH_VOL') == 1.89
        assert get_regime_adaptive_gamma_top_v59('PANIC') == 1.26
        assert get_regime_adaptive_gamma_top_v59('CRISIS') == 1.26
        assert get_regime_adaptive_gamma_top_v59('RECOVERY') == 10.08
        assert get_regime_adaptive_gamma_top_v59('UNKNOWN') == 12.60

    def test_feature_f267_280th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035])
        denoised = apply_bicentaoctacontagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=280.0)

        for val in denoised:
            assert abs(val) < 1e-200, f'Noise leakage {val} not suppressed below 10^-200'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_bicentaoctacontagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=280.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_bicentaoctacontagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=280.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

        # Odd symmetry
        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_bicentaoctacontagonal_hyperbolic_deadband(-z), -apply_bicentaoctacontagonal_hyperbolic_deadband(z))

    def test_feature_f267_factor_suppression_delegation(self):
        scalar_res = apply_bicentaoctacontagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-200

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_bicentaoctacontagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-200
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_59(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        res_v59 = engine.apply_smooth_noise_deadband(z_noise, version=59)
        assert abs(res_v59[0]) < 1e-200

    def test_combine_predictions_version_59_confluence_and_harmony(self):
        engine = EnsembleScoringEngine()
        n = 10
        mock_scores = {
            'symbol': [f'SYM_{i}' for i in range(n)],
            'regression': pd.Series(np.linspace(0.1, 0.9, n)),
            'surge': pd.Series(np.linspace(0.2, 0.8, n)),
            'vcp': pd.Series(np.linspace(0.3, 0.7, n)),
            'vcp_ml': pd.Series(np.linspace(0.4, 0.6, n)),
            'lstm': pd.Series(np.linspace(0.2, 0.8, n)),
            'stat_arb': pd.Series(np.linspace(0.1, 0.5, n)),
            'sector_rotation': pd.Series(np.linspace(0.2, 0.7, n)),
            'factor_neutralized': pd.Series(np.linspace(0.3, 0.8, n)),
            'order_flow': pd.Series(np.linspace(0.4, 0.9, n)),
            'event_driven': pd.Series(np.linspace(0.2, 0.6, n)),
        }
        df_scores = pd.DataFrame(mock_scores)

        comb_v58 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=58)
        comb_v59 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=59)

        assert isinstance(comb_v59, pd.DataFrame)
        assert not comb_v59.empty
        assert 'ensemble_score' in comb_v59.columns
        assert len(comb_v59) == n
        assert np.all(np.isfinite(comb_v59['ensemble_score'].values))
        assert np.all(comb_v59['ensemble_score'].values >= 0.0)
        assert np.all(comb_v59['ensemble_score'].values <= 1.0)

        top_v58 = comb_v58.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v59 = comb_v59.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v59 >= top_v58 - 1e-6, f'Top conviction in v59 ({top_v59}) should be >= v58 ({top_v58})'

    def test_strict_backward_compatibility_v58_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v59 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=59)
        out_v58 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=58)
        out_v57 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=57)
        out_v56 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=56)
        out_v55 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=55)
        out_v54 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=54)
        out_v53 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=53)
        out_v52 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=52)
        out_v51 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=51)
        out_v50 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=50)
        out_v49 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=49)
        out_v48 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=48)
        out_v47 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=47)
        out_v46 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=46)
        out_v45 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=45)
        out_v44 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=44)

        assert abs(out_v59[0]) < 1e-200
        assert abs(out_v58[0]) < 1e-192
        assert abs(out_v57[0]) < 1e-184
        assert abs(out_v56[0]) < 1e-176
        assert abs(out_v55[0]) < 1e-168
        assert abs(out_v54[0]) < 1e-160
        assert abs(out_v53[0]) < 1e-152
        assert abs(out_v52[0]) < 1e-144
        assert abs(out_v51[0]) < 1e-136
        assert abs(out_v50[0]) < 1e-128
        assert abs(out_v49[0]) < 1e-120
        assert abs(out_v48[0]) < 1e-114
        assert abs(out_v47[0]) < 1e-108
        assert abs(out_v46[0]) < 1e-102
        assert abs(out_v45[0]) < 1e-96
        assert abs(out_v44[0]) < 1e-90

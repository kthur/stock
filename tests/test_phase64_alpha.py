import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_bicentatriacontaoctagonal_hyperbolic_deadband,
    compute_phase64_hyperconvex_rank_modulation,
    compute_phase64_rank_warping,
    REGIME_GAMMA_TOP_V64,
    get_regime_adaptive_gamma_top_v64,
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
    Phase64Coupler,
    Phase63Coupler,
    Phase62Coupler,
    Phase61Coupler,
    Phase60Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology14Coupler,
    DrinfeldHigherHomology14Coupler,
    HigherHomology14Coupler,
    QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology13Coupler,
    DrinfeldHigherHomology13Coupler,
    HigherHomology13Coupler,
    EnsembleScoringEngine,
)


class TestPhase64AlphaEnhancements:
    def test_feature_f291_quantum_geometric_langlands_borcherds_moonshine_monster_whittaker_coupler_properties(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=18.50,
            lambda_monster=0.99998,
        )
        assert coupler.kappa_monster_whit == 18.50
        assert coupler.lambda_monster == 0.99998

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
        assert 'FERI_v64' in res
        assert 'feri_v64' in res
        assert 'FERI_v63' in res
        assert 'feri_v63' in res
        assert 'FERI_v62' in res
        assert 'feri_v62' in res
        assert 'FERI_v61' in res
        assert 'feri_v61' in res
        assert 'FERI_v60' in res
        assert 'Z_monster_whit' in res
        assert 'E_monster_whit' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v64']

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
        assert np.isclose(res_1d['FERI_v64'], 1.0, atol=1e-7)

    def test_feature_f291_quantum_geometric_langlands_aliases_and_exports(self):
        assert Phase64Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase63Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase62Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase61Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology14Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert DrinfeldHigherHomology14Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert HigherHomology14Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology13Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        res_class = EnsembleScoringEngine.compute_quantum_geometric_langlands_borcherds_moonshine_monster_whittaker_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_monster_whit' in res_class
        assert 'FERI_v64' in res_class

    def test_feature_f292_1_59th_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase64_hyperconvex_rank_modulation(ranks, gamma_top=15.60)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 2.20 * exp(15.60)
        expected_top = 0.50 + 2.20 * math.exp(15.60)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 1000000.0
        assert g_mod[-1] > 10000000.0

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '59th-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest (<= 2.20) while r=1.0 explodes
        g_70 = compute_phase64_hyperconvex_rank_modulation(0.70, gamma_top=15.60)
        assert g_70 <= 2.20

        # With negative z_denoised
        g_neg = compute_phase64_hyperconvex_rank_modulation(ranks, gamma_top=15.60, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f292_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v64('BULL_LOW_VOL') == 15.60
        assert get_regime_adaptive_gamma_top_v64('BULL_HIGH_VOL') == 12.50
        assert get_regime_adaptive_gamma_top_v64('SIDEWAYS') == 9.40
        assert get_regime_adaptive_gamma_top_v64('SIDEWAYS_LOW_VOL') == 9.40
        assert get_regime_adaptive_gamma_top_v64('SIDEWAYS_HIGH_VOL') == 6.25
        assert get_regime_adaptive_gamma_top_v64('BEAR') == 3.10
        assert get_regime_adaptive_gamma_top_v64('BEAR_LOW_VOL') == 3.10
        assert get_regime_adaptive_gamma_top_v64('BEAR_HIGH_VOL') == 2.35
        assert get_regime_adaptive_gamma_top_v64('PANIC') == 1.55
        assert get_regime_adaptive_gamma_top_v64('CRISIS') == 1.55
        assert get_regime_adaptive_gamma_top_v64('RECOVERY') == 12.50
        assert get_regime_adaptive_gamma_top_v64('UNKNOWN') == 15.60
        assert get_regime_adaptive_gamma_top_v64('2') == 15.60
        assert get_regime_adaptive_gamma_top_v64('1') == 9.40
        assert get_regime_adaptive_gamma_top_v64('0') == 3.10

    def test_feature_f292_2_320th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035])
        denoised = apply_bicentatriacontaoctagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=320.0)

        for val in denoised:
            assert abs(val) < 1e-238, f'Noise leakage {val} not suppressed below 10^-238'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_bicentatriacontaoctagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=320.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_bicentatriacontaoctagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=320.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

        # Odd symmetry
        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_bicentatriacontaoctagonal_hyperbolic_deadband(-z), -apply_bicentatriacontaoctagonal_hyperbolic_deadband(z))

    def test_feature_f292_2_factor_suppression_delegation(self):
        scalar_res = apply_bicentatriacontaoctagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-238

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_bicentatriacontaoctagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-238
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_64(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        res_v64 = engine.apply_smooth_noise_deadband(z_noise, version=64)
        assert abs(res_v64[0]) < 1e-238

    def test_combine_predictions_version_64_confluence_and_harmony(self):
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

        comb_v63 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=63)
        comb_v64 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=64)

        assert isinstance(comb_v64, pd.DataFrame)
        assert not comb_v64.empty
        assert 'ensemble_score' in comb_v64.columns
        assert len(comb_v64) == n
        assert np.all(np.isfinite(comb_v64['ensemble_score'].values))
        assert np.all(comb_v64['ensemble_score'].values >= 0.0)
        assert np.all(comb_v64['ensemble_score'].values <= 1.0)

        top_v63 = comb_v63.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v64 = comb_v64.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v64 >= top_v63 - 1e-6, f'Top conviction in v64 ({top_v64}) should be >= v63 ({top_v63})'

    def test_strict_backward_compatibility_v63_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v64 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=64)
        out_v63 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=63)
        out_v62 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=62)
        out_v61 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=61)
        out_v60 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=60)
        out_v59 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=59)

        assert abs(out_v64[0]) < 1e-238
        assert abs(out_v63[0]) < 1e-232
        assert abs(out_v62[0]) < 1e-224
        assert abs(out_v61[0]) < 1e-216
        assert abs(out_v60[0]) < 1e-208
        assert abs(out_v59[0]) < 1e-200

import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tricentaseptacontahexagonal_hyperbolic_deadband,
    compute_phase71_hyperconvex_rank_modulation,
    compute_phase71_rank_warping,
    REGIME_GAMMA_TOP_V71,
    get_regime_adaptive_gamma_top_v71,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase71Coupler,
    Phase70Coupler,
    Phase69Coupler,
    Phase68Coupler,
    EnsembleScoringEngine,
)


class TestPhase71AlphaEnhancements:
    def test_feature_f326_coupler_properties_v71(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=23.40,
            lambda_monster=0.9999999,
        )
        assert coupler.kappa_monster_whit == 23.40
        assert coupler.lambda_monster == 0.9999999

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
        assert 'FERI_v71' in res
        assert 'feri_v71' in res
        assert 'FERI_v70' in res
        assert 'feri_v70' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v71']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        assert res['e_monster_whit'].iloc[0] < res['e_monster_whit'].iloc[1] < res['e_monster_whit'].iloc[2]
        assert h.iloc[0] > h.iloc[1] >= h.iloc[2]

        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_monster_whit'], float)
        assert np.isclose(res_1d['e_monster_whit'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['FERI_v71'], 1.0, atol=1e-7)

    def test_feature_f326_coupler_aliases_v71(self):
        assert Phase71Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase70Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase69Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase68Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

    def test_feature_f327_1_73rd_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase71_hyperconvex_rank_modulation(ranks, gamma_top=18.05)

        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        expected_top = 0.50 + 2.55 * math.exp(18.05)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 10000000.0

        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '73rd-order rank modulation must be strictly monotonically increasing'

        g_71 = compute_phase71_hyperconvex_rank_modulation(0.70, gamma_top=18.05)
        assert g_71 <= 2.29

        g_neg = compute_phase71_hyperconvex_rank_modulation(ranks, gamma_top=18.05, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f327_1_regime_adaptive_gamma_top_v71(self):
        assert get_regime_adaptive_gamma_top_v71('BULL_LOW_VOL') == 18.05
        assert get_regime_adaptive_gamma_top_v71('BULL_HIGH_VOL') == 14.60
        assert get_regime_adaptive_gamma_top_v71('SIDEWAYS') == 11.10
        assert get_regime_adaptive_gamma_top_v71('SIDEWAYS_LOW_VOL') == 11.10
        assert get_regime_adaptive_gamma_top_v71('SIDEWAYS_HIGH_VOL') == 7.30
        assert get_regime_adaptive_gamma_top_v71('BEAR') == 3.80
        assert get_regime_adaptive_gamma_top_v71('BEAR_LOW_VOL') == 3.80
        assert get_regime_adaptive_gamma_top_v71('BEAR_HIGH_VOL') == 3.00
        assert get_regime_adaptive_gamma_top_v71('PANIC') == 1.90
        assert get_regime_adaptive_gamma_top_v71('CRISIS') == 1.90
        assert get_regime_adaptive_gamma_top_v71('RECOVERY') == 14.60
        assert get_regime_adaptive_gamma_top_v71('UNKNOWN') == 18.05
        assert get_regime_adaptive_gamma_top_v71('2') == 18.05
        assert get_regime_adaptive_gamma_top_v71('1') == 11.10
        assert get_regime_adaptive_gamma_top_v71('0') == 3.80

    def test_feature_f327_2_376th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035])
        denoised = apply_tricentaseptacontahexagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=376.0)

        for val in denoised:
            assert abs(val) < 1e-250, f'Noise leakage {val} not suppressed below 10^-250'

        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_tricentaseptacontahexagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=376.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_tricentaseptacontahexagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=376.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'

        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_tricentaseptacontahexagonal_hyperbolic_deadband(-z), -apply_tricentaseptacontahexagonal_hyperbolic_deadband(z))

    def test_feature_f327_2_deadband_scalar_and_series(self):
        scalar_res = apply_tricentaseptacontahexagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-250

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_tricentaseptacontahexagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-250
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_71(self):
        z_noise = np.array([0.0002])
        res_v71 = EnsembleScoringEngine.apply_smooth_noise_deadband(z_noise, version=71)
        assert abs(res_v71[0]) < 1e-250

    def test_combine_predictions_version_71_confluence(self):
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

        comb_v70 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=70)
        comb_v71 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=71)

        assert isinstance(comb_v71, pd.DataFrame)
        assert not comb_v71.empty
        assert 'ensemble_score' in comb_v71.columns
        assert len(comb_v71) == n
        assert np.all(np.isfinite(comb_v71['ensemble_score'].values))
        assert np.all(comb_v71['ensemble_score'].values >= 0.0)
        assert np.all(comb_v71['ensemble_score'].values <= 1.0)

        top_v70 = comb_v70.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v71 = comb_v71.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v71 >= top_v70 - 1e-6

    def test_strict_backward_compatibility_v70_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v71 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=71)
        out_v70 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=70)
        out_v69 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=69)
        out_v68 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=68)
        out_v67 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=67)

        assert abs(out_v71[0]) < 1e-250
        assert abs(out_v70[0]) < 1e-250
        assert abs(out_v69[0]) < 1e-250
        assert abs(out_v68[0]) < 1e-250
        assert abs(out_v67[0]) < 1e-250

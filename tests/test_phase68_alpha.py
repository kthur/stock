import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_biheptacontaoctagonal_hyperbolic_deadband,
    compute_phase68_hyperconvex_rank_modulation,
    compute_phase68_rank_warping,
    REGIME_GAMMA_TOP_V68,
    get_regime_adaptive_gamma_top_v68,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase68Coupler,
    Phase66Coupler,
    Phase64Coupler,
    Phase63Coupler,
    EnsembleScoringEngine,
)


class TestPhase68AlphaEnhancements:
    def test_feature_f306_coupler_properties_v67(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=21.30,
            lambda_monster=0.999999,
        )
        assert coupler.kappa_monster_whit == 21.30
        assert coupler.lambda_monster == 0.999999

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
        assert 'FERI_v67' in res
        assert 'feri_v67' in res
        assert 'FERI_v66' in res
        assert 'feri_v66' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v67']

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
        assert np.isclose(res_1d['FERI_v67'], 1.0, atol=1e-7)

    def test_feature_f306_coupler_aliases_v67(self):
        assert Phase68Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase66Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase64Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase63Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

    def test_feature_f307_1_67th_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase68_hyperconvex_rank_modulation(ranks, gamma_top=17.00)

        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        expected_top = 0.50 + 2.40 * math.exp(17.00)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 10000000.0

        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '65th-order rank modulation must be strictly monotonically increasing'

        g_70 = compute_phase68_hyperconvex_rank_modulation(0.70, gamma_top=17.00)
        assert g_70 <= 2.40

        g_neg = compute_phase68_hyperconvex_rank_modulation(ranks, gamma_top=17.00, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f307_1_regime_adaptive_gamma_top_v67(self):
        assert get_regime_adaptive_gamma_top_v68('BULL_LOW_VOL') == 17.00
        assert get_regime_adaptive_gamma_top_v68('BULL_HIGH_VOL') == 13.70
        assert get_regime_adaptive_gamma_top_v68('SIDEWAYS') == 10.35
        assert get_regime_adaptive_gamma_top_v68('SIDEWAYS_LOW_VOL') == 10.35
        assert get_regime_adaptive_gamma_top_v68('SIDEWAYS_HIGH_VOL') == 6.85
        assert get_regime_adaptive_gamma_top_v68('BEAR') == 3.50
        assert get_regime_adaptive_gamma_top_v68('BEAR_LOW_VOL') == 3.50
        assert get_regime_adaptive_gamma_top_v68('BEAR_HIGH_VOL') == 2.70
        assert get_regime_adaptive_gamma_top_v68('PANIC') == 1.75
        assert get_regime_adaptive_gamma_top_v68('CRISIS') == 1.75
        assert get_regime_adaptive_gamma_top_v68('RECOVERY') == 13.70
        assert get_regime_adaptive_gamma_top_v68('UNKNOWN') == 17.00
        assert get_regime_adaptive_gamma_top_v68('2') == 17.00
        assert get_regime_adaptive_gamma_top_v68('1') == 10.35
        assert get_regime_adaptive_gamma_top_v68('0') == 3.50

    def test_feature_f307_2_352th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035])
        denoised = apply_biheptacontaoctagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=352.0)

        for val in denoised:
            assert abs(val) < 1e-250, f'Noise leakage {val} not suppressed below 10^-250'

        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_biheptacontaoctagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=352.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_biheptacontaoctagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=352.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'

        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_biheptacontaoctagonal_hyperbolic_deadband(-z), -apply_biheptacontaoctagonal_hyperbolic_deadband(z))

    def test_feature_f307_2_deadband_scalar_and_series(self):
        scalar_res = apply_biheptacontaoctagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-250

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_biheptacontaoctagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-250
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_67(self):
        z_noise = np.array([0.0002])
        res_v67 = EnsembleScoringEngine.apply_smooth_noise_deadband(z_noise, version=68)
        assert abs(res_v67[0]) < 1e-250

    def test_combine_predictions_version_67_confluence(self):
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

        comb_v66 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=66)
        comb_v67 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=68)

        assert isinstance(comb_v67, pd.DataFrame)
        assert not comb_v67.empty
        assert 'ensemble_score' in comb_v67.columns
        assert len(comb_v67) == n
        assert np.all(np.isfinite(comb_v67['ensemble_score'].values))
        assert np.all(comb_v67['ensemble_score'].values >= 0.0)
        assert np.all(comb_v67['ensemble_score'].values <= 1.0)

        top_v66 = comb_v66.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v67 = comb_v67.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v67 >= top_v66 - 1e-6

    def test_strict_backward_compatibility_v66_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v67 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=68)
        out_v66 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=66)
        out_v65 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=65)
        out_v64 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=64)
        out_v63 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=63)
        out_v62 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=62)

        assert abs(out_v67[0]) < 1e-250
        assert abs(out_v66[0]) < 1e-240
        assert abs(out_v65[0]) < 1e-240
        assert abs(out_v64[0]) < 1e-238
        assert abs(out_v63[0]) < 1e-232
        assert abs(out_v62[0]) < 1e-224

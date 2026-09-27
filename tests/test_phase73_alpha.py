import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tricentanonacontaditagonal_hyperbolic_deadband,
    compute_phase73_deadband,
    apply_phase73_deadband,
    phase73_deadband,
    compute_phase73_hyperconvex_rank_modulation,
    compute_phase73_rank_warping,
    compute_phase73_rank_modulation,
    phase73_rank_modulation,
    REGIME_GAMMA_TOP_V73,
    get_regime_adaptive_gamma_top_v73,
    Phase73FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase73Coupler,
    Phase73WhittakerDrinfeldCoupler,
    Phase73BorcherdsMoonshineCoupler,
    Phase73MonsterWhittakerCoupler,
    compute_phase73_coupling,
    Phase72Coupler,
    Phase71Coupler,
    Phase70Coupler,
    Phase69Coupler,
    Phase68Coupler,
    EnsembleScoringEngine,
)


class TestPhase73AlphaEnhancements:
    def test_feature_f337_coupler_properties_v73(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=24.80,
            lambda_monster=0.99999998,
            version=73,
        )
        assert coupler.kappa_monster_whit == 24.80
        assert coupler.lambda_monster == 0.99999998
        assert coupler.version == 73

        # Test default instantiation
        default_coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert default_coupler.kappa_monster_whit == 24.80
        assert default_coupler.lambda_monster == 0.99999998
        assert default_coupler.version == 73

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
        assert 'FERI_v73' in res
        assert 'feri_v73' in res
        assert 'f_out_73' in res
        assert 'FERI_v72' in res
        assert 'feri_v72' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v73']
        f_out = res['f_out_73']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()
        assert (f_out >= 0.0).all() and (f_out <= 1.0).all()

        assert res['e_monster_whit'].iloc[0] < res['e_monster_whit'].iloc[1] < res['e_monster_whit'].iloc[2]
        assert h.iloc[0] > h.iloc[1] >= h.iloc[2]

        # 1D vector forward evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_monster_whit'], float)
        assert np.isclose(res_1d['e_monster_whit'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_monster_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['FERI_v73'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['f_out_73'], 1.0, atol=1e-7)

    def test_feature_f337_coupler_aliases_v73(self):
        assert Phase73Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase73WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase73BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase73MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert compute_phase73_coupling == QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.compute

        assert Phase72Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase71Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase70Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase69Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

    def test_feature_f336_77th_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase73_hyperconvex_rank_modulation(ranks, gamma_top=18.75)

        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        expected_top = 0.50 + 2.65 * math.exp(18.75)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 10000000.0

        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '77th-order rank modulation must be strictly monotonically non-decreasing'

        g_73 = compute_phase73_hyperconvex_rank_modulation(0.70, gamma_top=18.75)
        assert g_73 <= 2.36, f'At r=0.70, g(0.70) must be <= 2.36, got {g_73}'

        g_neg = compute_phase73_hyperconvex_rank_modulation(ranks, gamma_top=18.75, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f336_regime_adaptive_gamma_top_v73(self):
        assert get_regime_adaptive_gamma_top_v73('BULL_LOW_VOL') == 18.75
        assert get_regime_adaptive_gamma_top_v73('BULL_HIGH_VOL') == 15.20
        assert get_regime_adaptive_gamma_top_v73('SIDEWAYS') == 11.60
        assert get_regime_adaptive_gamma_top_v73('SIDEWAYS_LOW_VOL') == 11.60
        assert get_regime_adaptive_gamma_top_v73('SIDEWAYS_HIGH_VOL') == 7.60
        assert get_regime_adaptive_gamma_top_v73('BEAR') == 4.00
        assert get_regime_adaptive_gamma_top_v73('BEAR_LOW_VOL') == 4.00
        assert get_regime_adaptive_gamma_top_v73('BEAR_HIGH_VOL') == 3.20
        assert get_regime_adaptive_gamma_top_v73('PANIC') == 2.00
        assert get_regime_adaptive_gamma_top_v73('CRISIS') == 2.00
        assert get_regime_adaptive_gamma_top_v73('RECOVERY') == 15.20
        assert get_regime_adaptive_gamma_top_v73('UNKNOWN') == 18.75
        assert get_regime_adaptive_gamma_top_v73('2') == 18.75
        assert get_regime_adaptive_gamma_top_v73('1') == 11.60
        assert get_regime_adaptive_gamma_top_v73('0') == 4.00

        # Verify hierarchy
        assert (
            REGIME_GAMMA_TOP_V73['BULL_LOW_VOL']
            > REGIME_GAMMA_TOP_V73['BULL_HIGH_VOL']
            > REGIME_GAMMA_TOP_V73['SIDEWAYS']
            > REGIME_GAMMA_TOP_V73['SIDEWAYS_HIGH_VOL']
            > REGIME_GAMMA_TOP_V73['BEAR']
            > REGIME_GAMMA_TOP_V73['BEAR_HIGH_VOL']
            > REGIME_GAMMA_TOP_V73['CRISIS']
        )

    def test_feature_f336_392nd_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035])
        denoised = apply_tricentanonacontaditagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=392.0)

        for val in denoised:
            assert abs(val) < 1e-290 or val == 0.0, f'Noise leakage {val} not suppressed below 10^-290'

        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_tricentanonacontaditagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=392.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_tricentanonacontaditagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=392.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'

        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_tricentanonacontaditagonal_hyperbolic_deadband(-z), -apply_tricentanonacontaditagonal_hyperbolic_deadband(z))

    def test_feature_f336_deadband_scalar_and_series(self):
        scalar_res = apply_tricentanonacontaditagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-290 or scalar_res == 0.0

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_tricentanonacontaditagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-290 or s_out['a'] == 0.0
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_73(self):
        z_noise = np.array([0.0002])
        res_v73 = EnsembleScoringEngine.apply_smooth_noise_deadband(z_noise, version=73)
        assert abs(res_v73[0]) < 1e-290 or res_v73[0] == 0.0

    def test_combine_predictions_version_73_confluence(self):
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

        comb_v72 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=72)
        comb_v73 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=73)

        assert isinstance(comb_v73, pd.DataFrame)
        assert not comb_v73.empty
        assert 'ensemble_score' in comb_v73.columns
        assert len(comb_v73) == n
        assert np.all(np.isfinite(comb_v73['ensemble_score'].values))
        assert np.all(comb_v73['ensemble_score'].values >= 0.0)
        assert np.all(comb_v73['ensemble_score'].values <= 1.0)

        top_v72 = comb_v72.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v73 = comb_v73.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v73 >= top_v72 - 1e-6

    def test_strict_backward_compatibility_v72_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v73 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=73)
        out_v72 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=72)
        out_v71 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=71)
        out_v70 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=70)
        out_v69 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=69)
        out_v68 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=68)

        assert abs(out_v73[0]) < 1e-250
        assert abs(out_v72[0]) < 1e-250
        assert abs(out_v71[0]) < 1e-250
        assert abs(out_v70[0]) < 1e-250
        assert abs(out_v69[0]) < 1e-250
        assert abs(out_v68[0]) < 1e-250

    def test_feature_f336_alias_trees_v73(self):
        # Deadband aliases
        assert compute_phase73_deadband is apply_tricentanonacontaditagonal_hyperbolic_deadband
        assert apply_phase73_deadband is apply_tricentanonacontaditagonal_hyperbolic_deadband
        assert phase73_deadband is apply_tricentanonacontaditagonal_hyperbolic_deadband

        # Rank modulation aliases
        assert compute_phase73_rank_warping is compute_phase73_hyperconvex_rank_modulation
        assert compute_phase73_rank_modulation is compute_phase73_hyperconvex_rank_modulation
        assert phase73_rank_modulation is compute_phase73_hyperconvex_rank_modulation

        # Engine staticmethod functional equivalence
        assert callable(RegimeFactorSuppressionEngine.apply_tricentanonacontaditagonal_hyperbolic_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase73_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase73_hyperconvex_rank_modulation)
        assert callable(RegimeFactorSuppressionEngine.phase73_rank_modulation)

        val_deadband = RegimeFactorSuppressionEngine.apply_tricentanonacontaditagonal_hyperbolic_deadband(0.0001)
        assert abs(val_deadband) < 1e-290 or val_deadband == 0.0

        val_mod = RegimeFactorSuppressionEngine.compute_phase73_hyperconvex_rank_modulation(0.70, gamma_top=18.75)
        assert np.isclose(val_mod, compute_phase73_hyperconvex_rank_modulation(0.70, gamma_top=18.75))

        # Engine class alias
        assert Phase73FactorSuppressionEngine is RegimeFactorSuppressionEngine

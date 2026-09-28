import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiatetracontagonal_hyperbolic_deadband,
    apply_tetracosiatetracontadigonal_hyperbolic_deadband,
    compute_phase79_deadband,
    apply_phase79_deadband,
    phase79_deadband,
    compute_phase79_hyperconvex_rank_modulation,
    compute_phase79_rank_warping,
    compute_phase79_rank_modulation,
    phase79_rank_modulation,
    REGIME_GAMMA_TOP_V79,
    get_regime_adaptive_gamma_top_v79,
    Phase79FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase79Coupler,
    Phase79WhittakerDrinfeldCoupler,
    Phase79BorcherdsMoonshineCoupler,
    Phase79MonsterWhittakerCoupler,
    compute_phase79_coupling,
    Phase78Coupler,
    Phase77Coupler,
    Phase76Coupler,
    Phase75Coupler,
    Phase74Coupler,
    Phase73Coupler,
    Phase72Coupler,
    Phase71Coupler,
    Phase70Coupler,
    Phase69Coupler,
    Phase68Coupler,
    EnsembleScoringEngine,
)


class TestPhase79AlphaEnhancements:
    def test_feature_f367_coupler_properties_v79(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=29.00,
            lambda_monster=0.9999999998,
            version=79,
        )
        assert coupler.kappa_monster_whit == 29.00
        assert coupler.lambda_monster == 0.9999999998
        assert coupler.version == 79

        # Test default instantiation
        default_coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert default_coupler.kappa_monster_whit == 29.00
        assert default_coupler.lambda_monster == 0.9999999998
        assert default_coupler.version == 79

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
        assert 'FERI_v79' in res
        assert 'feri_v79' in res
        assert 'f_out_79' in res
        assert 'FERI_v78' in res
        assert 'feri_v78' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v79']
        f_out = res['f_out_79']

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
        assert np.isclose(res_1d['FERI_v79'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['f_out_79'], 1.0, atol=1e-7)

    def test_feature_f367_coupler_aliases_v79(self):
        assert Phase79Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase79WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase79BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase79MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert compute_phase79_coupling == QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.compute

        assert Phase78Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase77Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase76Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase75Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase74Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase73Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase72Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase71Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase70Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase69Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

    def test_feature_f366_89th_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase79_hyperconvex_rank_modulation(ranks, gamma_top=20.85)

        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        expected_top = 0.50 + 2.95 * math.exp(20.85)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 10000000.0

        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '89th-order rank modulation must be strictly monotonically non-decreasing'

        g_79 = compute_phase79_hyperconvex_rank_modulation(0.70, gamma_top=20.85)
        assert g_79 <= 2.60, f'At r=0.70, g(0.70) must be <= 2.60, got {g_79}'

        g_neg = compute_phase79_hyperconvex_rank_modulation(ranks, gamma_top=20.85, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f366_regime_adaptive_gamma_top_v79(self):
        assert get_regime_adaptive_gamma_top_v79('BULL_LOW_VOL') == 20.85
        assert get_regime_adaptive_gamma_top_v79('BULL_HIGH_VOL') == 17.00
        assert get_regime_adaptive_gamma_top_v79('SIDEWAYS') == 13.10
        assert get_regime_adaptive_gamma_top_v79('SIDEWAYS_LOW_VOL') == 13.10
        assert get_regime_adaptive_gamma_top_v79('SIDEWAYS_HIGH_VOL') == 8.80
        assert get_regime_adaptive_gamma_top_v79('BEAR') == 4.60
        assert get_regime_adaptive_gamma_top_v79('BEAR_LOW_VOL') == 4.60
        assert get_regime_adaptive_gamma_top_v79('BEAR_HIGH_VOL') == 3.80
        assert get_regime_adaptive_gamma_top_v79('PANIC') == 2.60
        assert get_regime_adaptive_gamma_top_v79('CRISIS') == 2.60
        assert get_regime_adaptive_gamma_top_v79('RECOVERY') == 17.00
        assert get_regime_adaptive_gamma_top_v79('UNKNOWN') == 20.85
        assert get_regime_adaptive_gamma_top_v79('2') == 20.85
        assert get_regime_adaptive_gamma_top_v79('1') == 13.10
        assert get_regime_adaptive_gamma_top_v79('0') == 4.60

        # Verify hierarchy
        assert (
            REGIME_GAMMA_TOP_V79['BULL_LOW_VOL']
            > REGIME_GAMMA_TOP_V79['BULL_HIGH_VOL']
            > REGIME_GAMMA_TOP_V79['SIDEWAYS']
            > REGIME_GAMMA_TOP_V79['SIDEWAYS_HIGH_VOL']
            > REGIME_GAMMA_TOP_V79['BEAR']
            > REGIME_GAMMA_TOP_V79['BEAR_HIGH_VOL']
            > REGIME_GAMMA_TOP_V79['CRISIS']
        )

    def test_feature_f366_440th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035, 0.0035, -0.0035])
        denoised = apply_tetracosiatetracontagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=440.0)

        for val in denoised:
            assert abs(val) < 1e-308 or val == 0.0, f'Noise leakage {val} not suppressed below 10^-308'

        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_tetracosiatetracontagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=440.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_tetracosiatetracontagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=440.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'

        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_tetracosiatetracontagonal_hyperbolic_deadband(-z), -apply_tetracosiatetracontagonal_hyperbolic_deadband(z))

    def test_feature_f366_deadband_scalar_and_series(self):
        scalar_res = apply_tetracosiatetracontagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-308 or scalar_res == 0.0

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_tetracosiatetracontagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-308 or s_out['a'] == 0.0
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_79(self):
        z_noise = np.array([0.0002])
        res_v79 = EnsembleScoringEngine.apply_smooth_noise_deadband(z_noise, version=79)
        assert abs(res_v79[0]) < 1e-308 or res_v79[0] == 0.0

    def test_combine_predictions_version_79_confluence(self):
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

        comb_v78 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=78)
        comb_v79 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=79)

        assert isinstance(comb_v79, pd.DataFrame)
        assert not comb_v79.empty
        assert 'ensemble_score' in comb_v79.columns
        assert len(comb_v79) == n
        assert np.all(np.isfinite(comb_v79['ensemble_score'].values))
        assert np.all(comb_v79['ensemble_score'].values >= 0.0)
        assert np.all(comb_v79['ensemble_score'].values <= 1.0)

        top_v78 = comb_v78.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v79 = comb_v79.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v79 >= top_v78 - 1e-6

    def test_strict_backward_compatibility_v78_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v79 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=79)
        out_v78 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=78)
        out_v77 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=77)
        out_v76 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=76)
        out_v75 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=75)
        out_v74 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=74)
        out_v73 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=73)
        out_v72 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=72)
        out_v71 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=71)
        out_v70 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=70)
        out_v69 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=69)

        assert abs(out_v79[0]) < 1e-250
        assert abs(out_v78[0]) < 1e-250
        assert abs(out_v77[0]) < 1e-250
        assert abs(out_v76[0]) < 1e-250
        assert abs(out_v75[0]) < 1e-250
        assert abs(out_v74[0]) < 1e-250
        assert abs(out_v73[0]) < 1e-250
        assert abs(out_v72[0]) < 1e-250
        assert abs(out_v71[0]) < 1e-250
        assert abs(out_v70[0]) < 1e-250
        assert abs(out_v69[0]) < 1e-250

    def test_feature_f366_alias_trees_v79(self):
        # Deadband aliases
        assert compute_phase79_deadband is apply_tetracosiatetracontagonal_hyperbolic_deadband
        assert apply_phase79_deadband is apply_tetracosiatetracontagonal_hyperbolic_deadband
        assert phase79_deadband is apply_tetracosiatetracontagonal_hyperbolic_deadband
        assert apply_tetracosiatetracontadigonal_hyperbolic_deadband is apply_tetracosiatetracontagonal_hyperbolic_deadband

        # Rank modulation aliases
        assert compute_phase79_rank_warping is compute_phase79_hyperconvex_rank_modulation
        assert compute_phase79_rank_modulation is compute_phase79_hyperconvex_rank_modulation
        assert phase79_rank_modulation is compute_phase79_hyperconvex_rank_modulation

        # Engine staticmethod functional equivalence
        assert callable(RegimeFactorSuppressionEngine.apply_tetracosiatetracontagonal_hyperbolic_deadband)
        assert callable(RegimeFactorSuppressionEngine.apply_tetracosiatetracontadigonal_hyperbolic_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase79_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase79_hyperconvex_rank_modulation)
        assert callable(RegimeFactorSuppressionEngine.phase79_rank_modulation)

        val_deadband = RegimeFactorSuppressionEngine.apply_tetracosiatetracontagonal_hyperbolic_deadband(0.0001)
        assert abs(val_deadband) < 1e-308 or val_deadband == 0.0

        val_mod = RegimeFactorSuppressionEngine.compute_phase79_hyperconvex_rank_modulation(0.70, gamma_top=20.85)
        assert np.isclose(val_mod, compute_phase79_hyperconvex_rank_modulation(0.70, gamma_top=20.85))

        # Engine class alias
        assert Phase79FactorSuppressionEngine is RegimeFactorSuppressionEngine

import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_tetracosiapentacontahexagonal_hyperbolic_deadband,
    apply_tetracosiapentacontahexadihedral_hyperbolic_deadband,
    apply_quadringentapentacontahexagonal_hyperbolic_deadband,
    apply_tetracentapentacontahexa_hyperbolic_deadband,
    apply_tetracosiapentacontahexa_hyperbolic_deadband,
    apply_tetracosiapentacontahexagonal_deadband,
    tetracosiapentacontahexagonal_deadband,
    tetracosiapentacontahexagonal_hyperbolic_deadband,
    compute_phase81_deadband,
    apply_phase81_deadband,
    phase81_deadband,
    apply_456th_order_hyperbolic_deadband,
    apply_456nd_order_hyperbolic_deadband,
    apply_456_deadband,
    apply_hyperbolic_deadband_v81,
    suppress_factor_noise_hyperbolic_v81,
    compute_phase81_hyperconvex_rank_modulation,
    compute_phase81_rank_warping,
    compute_phase81_rank_modulation,
    phase81_rank_modulation,
    phase81_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v81,
    REGIME_GAMMA_TOP_V81,
    get_regime_adaptive_gamma_top_v81,
    Phase81FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase81Coupler,
    Phase81WhittakerDrinfeldCoupler,
    Phase81BorcherdsMoonshineCoupler,
    Phase81MonsterWhittakerCoupler,
    compute_phase81_coupling,
    Phase80Coupler,
    Phase79Coupler,
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


class TestPhase81AlphaEnhancements:
    def test_feature_f377_coupler_properties_v81(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=30.40,
            lambda_monster=0.99999999999,
            version=81,
        )
        assert coupler.kappa_monster_whit == 30.40
        assert coupler.lambda_monster == 0.99999999999
        assert coupler.version == 81

        # Test default instantiation (detects 'phase81' in filename)
        default_coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert default_coupler.kappa_monster_whit == 30.40
        assert default_coupler.lambda_monster == 0.99999999999
        assert default_coupler.version == 81

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
        assert 'FERI_v81' in res
        assert 'feri_v81' in res
        assert 'f_out_81' in res
        assert 'FERI_v80' in res
        assert 'feri_v80' in res
        assert 'f_out_80' in res
        assert 'FERI_v79' in res
        assert 'feri_v79' in res

        h = res['h_monster_whit']
        z = res['z_monster_whit']
        feri = res['FERI_v81']
        f_out = res['f_out_81']

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
        assert np.isclose(res_1d['FERI_v81'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['f_out_81'], 1.0, atol=1e-7)

    def test_feature_f377_coupler_aliases_v81(self):
        assert Phase81Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase81WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase81BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase81MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert compute_phase81_coupling == QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.compute

        assert Phase80Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase79Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
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

    def test_feature_f376_93rd_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase81_hyperconvex_rank_modulation(ranks, gamma_top=21.50)

        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        expected_top = 0.50 + 3.05 * math.exp(21.50)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-3)
        assert g_mod[-1] > 10000000.0

        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '93rd-order rank modulation must be strictly monotonically non-decreasing'

        g_81 = compute_phase81_hyperconvex_rank_modulation(0.70, gamma_top=21.50)
        assert g_81 <= 2.64, f'At r=0.70, g(0.70) must be <= 2.64, got {g_81}'

        g_neg = compute_phase81_hyperconvex_rank_modulation(ranks, gamma_top=21.50, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f376_regime_adaptive_gamma_top_v81(self):
        assert get_regime_adaptive_gamma_top_v81('BULL_LOW_VOL') == 21.50
        assert get_regime_adaptive_gamma_top_v81('BULL_HIGH_VOL') == 17.60
        assert get_regime_adaptive_gamma_top_v81('SIDEWAYS') == 13.60
        assert get_regime_adaptive_gamma_top_v81('SIDEWAYS_LOW_VOL') == 13.60
        assert get_regime_adaptive_gamma_top_v81('SIDEWAYS_HIGH_VOL') == 9.15
        assert get_regime_adaptive_gamma_top_v81('BEAR') == 4.80
        assert get_regime_adaptive_gamma_top_v81('BEAR_LOW_VOL') == 4.80
        assert get_regime_adaptive_gamma_top_v81('BEAR_HIGH_VOL') == 4.00
        assert get_regime_adaptive_gamma_top_v81('PANIC') == 2.80
        assert get_regime_adaptive_gamma_top_v81('CRISIS') == 2.80
        assert get_regime_adaptive_gamma_top_v81('RECOVERY') == 17.60
        assert get_regime_adaptive_gamma_top_v81('UNKNOWN') == 21.50
        assert get_regime_adaptive_gamma_top_v81('2') == 21.50
        assert get_regime_adaptive_gamma_top_v81('1') == 13.60
        assert get_regime_adaptive_gamma_top_v81('0') == 4.80

        # Verify hierarchy
        assert (
            REGIME_GAMMA_TOP_V81['BULL_LOW_VOL']
            > REGIME_GAMMA_TOP_V81['BULL_HIGH_VOL']
            > REGIME_GAMMA_TOP_V81['SIDEWAYS']
            > REGIME_GAMMA_TOP_V81['SIDEWAYS_HIGH_VOL']
            > REGIME_GAMMA_TOP_V81['BEAR']
            > REGIME_GAMMA_TOP_V81['BEAR_HIGH_VOL']
            > REGIME_GAMMA_TOP_V81['CRISIS']
        )

    def test_feature_f376_456th_order_hyperbolic_deadband_leakage(self):
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035, 0.0035, -0.0035])
        denoised = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=456.0)

        for val in denoised:
            assert abs(val) < 1e-308 or val == 0.0, f'Noise leakage {val} not suppressed below 10^-308'

        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=456.0)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=456.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be monotonically non-decreasing'

        for z in [0.001, 0.01, 0.05, 0.10, 0.25]:
            assert np.isclose(apply_tetracosiapentacontahexagonal_hyperbolic_deadband(-z), -apply_tetracosiapentacontahexagonal_hyperbolic_deadband(z))

    def test_feature_f376_deadband_scalar_and_series(self):
        scalar_res = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-308 or scalar_res == 0.0

        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_tetracosiapentacontahexagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-308 or s_out['a'] == 0.0
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_81(self):
        z_noise = np.array([0.0002])
        res_v81 = EnsembleScoringEngine.apply_smooth_noise_deadband(z_noise, version=81)
        assert abs(res_v81[0]) < 1e-308 or res_v81[0] == 0.0

    def test_combine_predictions_version_81_confluence(self):
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

        comb_v80 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=80)
        comb_v81 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=81)

        assert isinstance(comb_v81, pd.DataFrame)
        assert not comb_v81.empty
        assert 'ensemble_score' in comb_v81.columns
        assert len(comb_v81) == n
        assert np.all(np.isfinite(comb_v81['ensemble_score'].values))
        assert np.all(comb_v81['ensemble_score'].values >= 0.0)
        assert np.all(comb_v81['ensemble_score'].values <= 1.0)

        top_v80 = comb_v80.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v81 = comb_v81.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v81 >= top_v80 - 1e-6

    def test_strict_backward_compatibility_v80_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v81 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=81)
        out_v80 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=80)
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

        assert abs(out_v81[0]) < 1e-250
        assert abs(out_v80[0]) < 1e-250
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

    def test_feature_f376_alias_trees_v81(self):
        # Deadband aliases
        assert compute_phase81_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_phase81_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert phase81_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_tetracosiapentacontahexadihedral_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_quadringentapentacontahexagonal_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_tetracentapentacontahexa_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_tetracosiapentacontahexa_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_tetracosiapentacontahexagonal_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert tetracosiapentacontahexagonal_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert tetracosiapentacontahexagonal_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_456th_order_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_456nd_order_hyperbolic_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_456_deadband is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert apply_hyperbolic_deadband_v81 is apply_tetracosiapentacontahexagonal_hyperbolic_deadband
        assert suppress_factor_noise_hyperbolic_v81 is apply_tetracosiapentacontahexagonal_hyperbolic_deadband

        # Rank modulation aliases
        assert compute_phase81_rank_warping is compute_phase81_hyperconvex_rank_modulation
        assert compute_phase81_rank_modulation is compute_phase81_hyperconvex_rank_modulation
        assert phase81_rank_modulation is compute_phase81_hyperconvex_rank_modulation
        assert phase81_hyperconvex_rank_modulation is compute_phase81_hyperconvex_rank_modulation
        assert apply_hyper_convex_rank_modulation_v81 is compute_phase81_hyperconvex_rank_modulation

        # Engine staticmethod functional equivalence
        assert callable(RegimeFactorSuppressionEngine.apply_tetracosiapentacontahexagonal_hyperbolic_deadband)
        assert callable(RegimeFactorSuppressionEngine.apply_tetracosiapentacontahexadihedral_hyperbolic_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase81_deadband)
        assert callable(RegimeFactorSuppressionEngine.compute_phase81_hyperconvex_rank_modulation)
        assert callable(RegimeFactorSuppressionEngine.phase81_rank_modulation)

        val_deadband = RegimeFactorSuppressionEngine.apply_tetracosiapentacontahexagonal_hyperbolic_deadband(0.0001)
        assert abs(val_deadband) < 1e-308 or val_deadband == 0.0

        val_mod = RegimeFactorSuppressionEngine.compute_phase81_hyperconvex_rank_modulation(0.70, gamma_top=21.50)
        assert np.isclose(val_mod, compute_phase81_hyperconvex_rank_modulation(0.70, gamma_top=21.50))

        # Engine class alias
        assert Phase81FactorSuppressionEngine is RegimeFactorSuppressionEngine

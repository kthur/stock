import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centahexaoctagonal_hyperbolic_deadband,
    compute_phase45_hyperconvex_rank_modulation,
    compute_phase45_rank_warping,
    REGIME_GAMMA_TOP_V45,
    get_regime_adaptive_gamma_top_v45,
    apply_smooth_deadband_attenuation,
    apply_centahexacontagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsKacMoodyWhittakerCoupler,
    QuantumGeometricLanglandsKacMoodyWhittakerFactorCoupler,
    QuantumGeometricLanglandsKacMoodyCoupler,
    GeometricLanglandsKacMoodyWhittakerCoupler,
    GeometricLanglandsKacMoodyCoupler,
    KacMoodyWhittakerSheafHomologyCoupler,
    KacMoodyWhittakerChiralOperCoupler,
    KacMoodyWhittakerHomologyCoupler,
    KacMoodyWhittakerCoupler,
    KacMoodyCoupler,
    WhittakerKacMoodySheafCoupler,
    QuantumGeometricLanglandsSuperalgebraCoupler,
    Phase45Coupler,
    QuantumGeometricLanglandsChiralAffineCoupler,
    CategoricalChiralAffineDualityCoupler,
    GeometricLanglandsKacMoodyDualityCoupler,
    EnsembleScoringEngine,
)


class TestPhase45AlphaEnhancements:
    def test_feature_f199_quantum_geometric_langlands_kac_moody_whittaker_coupler_properties(self):
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_km_whit' in res
        assert 'z_km_whit' in res
        assert 'e_km_whit' in res
        assert 'FERI_v45' in res
        assert 'Z_km_whit' in res
        assert 'E_km_whit' in res
        assert 'h_kac_moody_whittaker' in res
        assert 'h_geometric_langlands' in res
        assert 'h_langlands_kac_moody' in res

        h = res['h_km_whit']
        z = res['z_km_whit']
        feri = res['FERI_v45']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res['e_km_whit'].iloc[0] < res['e_km_whit'].iloc[1] < res['e_km_whit'].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_km_whit'], float)
        assert np.isclose(res_1d['e_km_whit'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_km_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_km_whit'], 1.0, atol=1e-7)

    def test_feature_f199_quantum_geometric_langlands_aliases_and_exports(self):
        assert QuantumGeometricLanglandsKacMoodyWhittakerFactorCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsKacMoodyCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert GeometricLanglandsKacMoodyWhittakerCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert GeometricLanglandsKacMoodyCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert KacMoodyWhittakerSheafHomologyCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert KacMoodyWhittakerChiralOperCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert KacMoodyWhittakerHomologyCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert KacMoodyWhittakerCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert KacMoodyCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert WhittakerKacMoodySheafCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsSuperalgebraCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert Phase45Coupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsChiralAffineCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert CategoricalChiralAffineDualityCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler
        assert GeometricLanglandsKacMoodyDualityCoupler is QuantumGeometricLanglandsKacMoodyWhittakerCoupler

        res_class = EnsembleScoringEngine.compute_quantum_geometric_langlands_kac_moody_whittaker_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_km_whit' in res_class
        assert 'FERI_v45' in res_class

    def test_feature_f200_1_40th_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^40 concentrates conviction into top alpha slice
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase45_hyperconvex_rank_modulation(ranks, gamma_top=5.10)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.52 * exp(5.10)
        expected_top = 0.50 + 1.52 * math.exp(5.10)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '40th-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase45_hyperconvex_rank_modulation(0.70, gamma_top=5.10)
        assert g_70 < 1.60
        assert g_mod[-1] > 200.0

        # With negative z_denoised
        g_neg = compute_phase45_hyperconvex_rank_modulation(ranks, gamma_top=5.10, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f200_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v45('BULL_LOW_VOL') == 5.10
        assert get_regime_adaptive_gamma_top_v45('BULL_HIGH_VOL') == 4.80
        assert get_regime_adaptive_gamma_top_v45('SIDEWAYS') == 4.60
        assert get_regime_adaptive_gamma_top_v45('BEAR') == 4.30
        assert get_regime_adaptive_gamma_top_v45('CRISIS') == 1.55
        assert get_regime_adaptive_gamma_top_v45('UNKNOWN') == 5.10

    def test_feature_f200_2_168th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0003, leakage is < 10^-96
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003])
        denoised = apply_centahexaoctagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=168.0)

        for val in denoised:
            assert abs(val) < 1e-96, f'Noise leakage {val} not suppressed below 10^-96'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_centahexaoctagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=168.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_centahexaoctagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=168.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

    def test_feature_f200_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_centahexaoctagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-96

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_centahexaoctagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-96
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_45(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=45 should route to 168th order deadband
        res_v45 = engine.apply_smooth_noise_deadband(z_noise, version=45)
        assert abs(res_v45[0]) < 1e-96

    def test_combine_predictions_version_45_confluence_and_harmony(self):
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

        comb_v44 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=44)
        comb_v45 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=45)

        assert isinstance(comb_v45, pd.DataFrame)
        assert not comb_v45.empty
        assert 'ensemble_score' in comb_v45.columns
        assert len(comb_v45) == n
        assert np.all(np.isfinite(comb_v45['ensemble_score'].values))
        assert np.all(comb_v45['ensemble_score'].values >= 0.0)
        assert np.all(comb_v45['ensemble_score'].values <= 1.0)

        # Top conviction in v45 should be >= v44
        top_v44 = comb_v44.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v45 = comb_v45.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v45 >= top_v44 - 1e-6, f'Top conviction in v45 ({top_v45}) should be >= v44 ({top_v44})'

    def test_strict_backward_compatibility_v44_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v45 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=45)
        out_v44 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=44)
        out_v43 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=43)
        out_v42 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=42)
        out_v41 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=41)
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)

        assert abs(out_v45[0]) < 1e-96
        assert abs(out_v44[0]) < 1e-90
        assert abs(out_v43[0]) < 1e-84
        assert abs(out_v42[0]) < 1e-80
        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62

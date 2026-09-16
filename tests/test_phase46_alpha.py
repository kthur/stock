import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centaheptacontahexagonal_hyperbolic_deadband,
    compute_phase46_hyperconvex_rank_modulation,
    compute_phase46_rank_warping,
    REGIME_GAMMA_TOP_V46,
    get_regime_adaptive_gamma_top_v46,
    apply_smooth_deadband_attenuation,
    apply_centahexaoctagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler,
    QuantumGeometricLanglandsBorcherdsKacMoodyWhittakerCoupler,
    QuantumGeometricLanglandsBorcherdsKacMoodyWhittakerFactorCoupler,
    QuantumGeometricLanglandsBorcherdsCoupler,
    GeometricLanglandsBorcherdsKacMoodyWhittakerCoupler,
    GeometricLanglandsBorcherdsKacMoodyCoupler,
    BorcherdsKacMoodyWhittakerSheafHomologyCoupler,
    BorcherdsKacMoodyWhittakerChiralOperCoupler,
    BorcherdsKacMoodyWhittakerHomologyCoupler,
    BorcherdsKacMoodyWhittakerCoupler,
    BorcherdsKacMoodyCoupler,
    BorcherdsWhittakerSheafHomologyCoupler,
    BorcherdsWhittakerCoupler,
    BorcherdsCoupler,
    WhittakerBorcherdsKacMoodySheafCoupler,
    QuantumGeometricLanglandsBorcherdsSuperalgebraCoupler,
    Phase46Coupler,
    QuantumGeometricLanglandsBorcherdsChiralAffineCoupler,
    CategoricalBorcherdsChiralAffineDualityCoupler,
    GeometricLanglandsBorcherdsKacMoodyDualityCoupler,
    EnsembleScoringEngine,
)


class TestPhase46AlphaEnhancements:
    def test_feature_f203_quantum_geometric_langlands_borcherds_kac_moody_whittaker_coupler_properties(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_borch_whit' in res
        assert 'z_borch_whit' in res
        assert 'e_borch_whit' in res
        assert 'FERI_v46' in res
        assert 'Z_borch_whit' in res
        assert 'E_borch_whit' in res
        assert 'h_borcherds_kac_moody_whittaker' in res
        assert 'h_borcherds_kac_moody' in res
        assert 'h_geometric_langlands' in res
        assert 'h_langlands_borcherds' in res

        h = res['h_borch_whit']
        z = res['z_borch_whit']
        feri = res['FERI_v46']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res['e_borch_whit'].iloc[0] < res['e_borch_whit'].iloc[1] < res['e_borch_whit'].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_borch_whit'], float)
        assert np.isclose(res_1d['e_borch_whit'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_borch_whit'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_borch_whit'], 1.0, atol=1e-7)

    def test_feature_f203_quantum_geometric_langlands_aliases_and_exports(self):
        assert QuantumGeometricLanglandsBorcherdsKacMoodyWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsKacMoodyWhittakerFactorCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert GeometricLanglandsBorcherdsKacMoodyWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert GeometricLanglandsBorcherdsKacMoodyCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsKacMoodyWhittakerSheafHomologyCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsKacMoodyWhittakerChiralOperCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsKacMoodyWhittakerHomologyCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsKacMoodyWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsKacMoodyCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsWhittakerSheafHomologyCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert BorcherdsCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert WhittakerBorcherdsKacMoodySheafCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsSuperalgebraCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert Phase46Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert QuantumGeometricLanglandsBorcherdsChiralAffineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert CategoricalBorcherdsChiralAffineDualityCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
        assert GeometricLanglandsBorcherdsKacMoodyDualityCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler

        res_class = EnsembleScoringEngine.compute_quantum_geometric_langlands_borcherds_kac_moody_whittaker_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_borch_whit' in res_class
        assert 'FERI_v46' in res_class

    def test_feature_f204_1_41st_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^41 concentrates conviction into top alpha slice
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase46_hyperconvex_rank_modulation(ranks, gamma_top=5.30)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.52 * exp(5.30)
        expected_top = 0.50 + 1.52 * math.exp(5.30)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '41st-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase46_hyperconvex_rank_modulation(0.70, gamma_top=5.30)
        assert g_70 < 1.60
        assert g_mod[-1] > 300.0

        # With negative z_denoised
        g_neg = compute_phase46_hyperconvex_rank_modulation(ranks, gamma_top=5.30, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f204_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v46('BULL_LOW_VOL') == 5.30
        assert get_regime_adaptive_gamma_top_v46('BULL_HIGH_VOL') == 5.00
        assert get_regime_adaptive_gamma_top_v46('SIDEWAYS') == 4.80
        assert get_regime_adaptive_gamma_top_v46('BEAR') == 4.50
        assert get_regime_adaptive_gamma_top_v46('CRISIS') == 1.65
        assert get_regime_adaptive_gamma_top_v46('UNKNOWN') == 5.30

    def test_feature_f204_2_176th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0003, leakage is < 10^-102
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003])
        denoised = apply_centaheptacontahexagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=176.0)

        for val in denoised:
            assert abs(val) < 1e-102, f'Noise leakage {val} not suppressed below 10^-102'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_centaheptacontahexagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=176.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_centaheptacontahexagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=176.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

    def test_feature_f204_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_centaheptacontahexagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-102

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_centaheptacontahexagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-102
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_46(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=46 should route to 176th order deadband
        res_v46 = engine.apply_smooth_noise_deadband(z_noise, version=46)
        assert abs(res_v46[0]) < 1e-102

    def test_combine_predictions_version_46_confluence_and_harmony(self):
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

        comb_v45 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=45)
        comb_v46 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=46)

        assert isinstance(comb_v46, pd.DataFrame)
        assert not comb_v46.empty
        assert 'ensemble_score' in comb_v46.columns
        assert len(comb_v46) == n
        assert np.all(np.isfinite(comb_v46['ensemble_score'].values))
        assert np.all(comb_v46['ensemble_score'].values >= 0.0)
        assert np.all(comb_v46['ensemble_score'].values <= 1.0)

        # Top conviction in v46 should be >= v45
        top_v45 = comb_v45.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v46 = comb_v46.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v46 >= top_v45 - 1e-6, f'Top conviction in v46 ({top_v46}) should be >= v45 ({top_v45})'

    def test_strict_backward_compatibility_v45_and_prior(self):
        z = np.array([0.0003, 0.05, 0.15])
        out_v46 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=46)
        out_v45 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=45)
        out_v44 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=44)
        out_v43 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=43)
        out_v42 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=42)
        out_v41 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=41)
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)

        assert abs(out_v46[0]) < 1e-102
        assert abs(out_v45[0]) < 1e-96
        assert abs(out_v44[0]) < 1e-90
        assert abs(out_v43[0]) < 1e-84
        assert abs(out_v42[0]) < 1e-80
        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62

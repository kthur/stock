import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centatetracontatetragonal_hyperbolic_deadband,
    compute_phase42_hyperconvex_rank_modulation,
    compute_phase42_rank_warping,
    REGIME_GAMMA_TOP_V42,
    get_regime_adaptive_gamma_top_v42,
    apply_smooth_deadband_attenuation,
    apply_centatriacontaoctagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    BeilinsonDrinfeldChiralKacMoodyCoupler,
    BeilinsonDrinfeldChiralKacMoodyFactorCoupler,
    BeilinsonDrinfeldCoupler,
    ChiralKacMoodyCoupler,
    QuantumAffineCoupler,
    KacMoodyVertexAlgebraCoupler,
    BeilinsonDrinfeldChiralCoupler,
    Phase42Coupler,
    BeilinsonKacMoodyCoupler,
    EnsembleScoringEngine,
)


class TestPhase42AlphaEnhancements:
    def test_feature_f187_beilinson_drinfeld_chiral_kac_moody_coupler_properties(self):
        coupler = BeilinsonDrinfeldChiralKacMoodyCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_chiral' in res
        assert 'z_kac_moody' in res
        assert 'e_chiral' in res
        assert 'FERI_v42' in res
        assert 'Z_kac_moody' in res
        assert 'E_chiral' in res
        assert 'h_beilinson' in res
        assert 'h_drinfeld' in res
        assert 'h_kac_moody' in res

        h = res['h_chiral']
        z = res['z_kac_moody']
        feri = res['FERI_v42']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res['e_chiral'].iloc[0] < res['e_chiral'].iloc[1] < res['e_chiral'].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_chiral'], float)
        assert np.isclose(res_1d['e_chiral'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_kac_moody'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_chiral'], 1.0, atol=1e-7)

    def test_feature_f187_beilinson_drinfeld_aliases_and_exports(self):
        assert BeilinsonDrinfeldChiralKacMoodyFactorCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert BeilinsonDrinfeldCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert ChiralKacMoodyCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert QuantumAffineCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert KacMoodyVertexAlgebraCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert BeilinsonDrinfeldChiralCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert Phase42Coupler is BeilinsonDrinfeldChiralKacMoodyCoupler
        assert BeilinsonKacMoodyCoupler is BeilinsonDrinfeldChiralKacMoodyCoupler

        res_class = EnsembleScoringEngine.compute_beilinson_drinfeld_chiral_kac_moody_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_chiral' in res_class
        assert 'FERI_v42' in res_class

    def test_feature_f188_1_37th_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^37 concentrates conviction into top 0.0000000000000000000000000001%
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase42_hyperconvex_rank_modulation(ranks, gamma_top=4.60)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.50 * exp(4.60)
        expected_top = 0.50 + 1.50 * math.exp(4.60)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '37th-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase42_hyperconvex_rank_modulation(0.70, gamma_top=4.60)
        assert g_70 < 1.56
        assert g_mod[-1] > 140.0

        # With negative z_denoised
        g_neg = compute_phase42_hyperconvex_rank_modulation(ranks, gamma_top=4.60, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f188_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v42('BULL_LOW_VOL') == 4.60
        assert get_regime_adaptive_gamma_top_v42('BULL_HIGH_VOL') == 4.30
        assert get_regime_adaptive_gamma_top_v42('SIDEWAYS') == 4.10
        assert get_regime_adaptive_gamma_top_v42('BEAR') == 3.80
        assert get_regime_adaptive_gamma_top_v42('CRISIS') == 1.30
        assert get_regime_adaptive_gamma_top_v42('UNKNOWN') == 4.60

    def test_feature_f188_2_144th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0004, leakage is < 10^-80
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0004, -0.0004])
        denoised = apply_centatetracontatetragonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=144.0)

        for val in denoised:
            assert abs(val) < 1e-80, f'Noise leakage {val} not suppressed below 10^-80'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_centatetracontatetragonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=144.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_centatetracontatetragonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=144.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

    def test_feature_f188_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_centatetracontatetragonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-80

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_centatetracontatetragonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-80
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_42(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=42 should route to 144th order deadband
        res_v42 = engine.apply_smooth_noise_deadband(z_noise, version=42)
        assert abs(res_v42[0]) < 1e-80

    def test_combine_predictions_version_42_confluence_and_harmony(self):
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

        comb_v41 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=41)
        comb_v42 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=42)

        assert isinstance(comb_v42, pd.DataFrame)
        assert not comb_v42.empty
        assert 'ensemble_score' in comb_v42.columns
        assert len(comb_v42) == n
        assert np.all(np.isfinite(comb_v42['ensemble_score'].values))
        assert np.all(comb_v42['ensemble_score'].values >= 0.0)
        assert np.all(comb_v42['ensemble_score'].values <= 1.0)

        # Top conviction in v42 should be >= v41
        top_v41 = comb_v41.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v42 = comb_v42.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v42 >= top_v41 - 1e-6, f'Top conviction in v42 ({top_v42}) should be >= v41 ({top_v41})'

    def test_strict_backward_compatibility_v41_and_prior(self):
        z = np.array([0.0004, 0.05, 0.15])
        out_v42 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=42)
        out_v41 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=41)
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)
        out_v38 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=38)

        assert abs(out_v42[0]) < 1e-80
        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62
        assert abs(out_v38[0]) < 1e-60

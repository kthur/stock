import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centapentacontaduogonal_hyperbolic_deadband,
    compute_phase43_hyperconvex_rank_modulation,
    compute_phase43_rank_warping,
    REGIME_GAMMA_TOP_V43,
    get_regime_adaptive_gamma_top_v43,
    apply_smooth_deadband_attenuation,
    apply_centatetracontatetragonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumLanglandsAffineWAlgebraCoupler,
    QuantumLanglandsAffineWAlgebraFactorCoupler,
    QuantumLanglandsWAlgebraCoupler,
    AffineWAlgebraChiralOperCoupler,
    AffineWAlgebraCoupler,
    QuantumLanglandsCoupler,
    WAlgebraChiralOperCoupler,
    WAlgebraCoupler,
    Phase43Coupler,
    QuantumLanglandsDualityCoupler,
    ChiralOperHomologyCoupler,
    EnsembleScoringEngine,
)


class TestPhase43AlphaEnhancements:
    def test_feature_f191_quantum_langlands_affine_w_algebra_coupler_properties(self):
        coupler = QuantumLanglandsAffineWAlgebraCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_w_algebra' in res
        assert 'z_quant_langlands' in res
        assert 'e_w_algebra' in res
        assert 'FERI_v43' in res
        assert 'Z_quant_langlands' in res
        assert 'E_w_algebra' in res
        assert 'h_quant_langlands' in res
        assert 'h_w_alg' in res
        assert 'h_langlands' in res

        h = res['h_w_algebra']
        z = res['z_quant_langlands']
        feri = res['FERI_v43']

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res['e_w_algebra'].iloc[0] < res['e_w_algebra'].iloc[1] < res['e_w_algebra'].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d['h_w_algebra'], float)
        assert np.isclose(res_1d['e_w_algebra'], 0.0, atol=1e-7)
        assert np.isclose(res_1d['z_quant_langlands'], 1.0, atol=1e-7)
        assert np.isclose(res_1d['h_w_algebra'], 1.0, atol=1e-7)

    def test_feature_f191_quantum_langlands_aliases_and_exports(self):
        assert QuantumLanglandsAffineWAlgebraFactorCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert QuantumLanglandsWAlgebraCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert AffineWAlgebraChiralOperCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert AffineWAlgebraCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert QuantumLanglandsCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert WAlgebraChiralOperCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert WAlgebraCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert Phase43Coupler is QuantumLanglandsAffineWAlgebraCoupler
        assert QuantumLanglandsDualityCoupler is QuantumLanglandsAffineWAlgebraCoupler
        assert ChiralOperHomologyCoupler is QuantumLanglandsAffineWAlgebraCoupler

        res_class = EnsembleScoringEngine.compute_quantum_langlands_affine_w_algebra_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert 'h_w_algebra' in res_class
        assert 'FERI_v43' in res_class

    def test_feature_f192_1_38th_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^38 concentrates conviction into top 0.000000000000000000000000000001%
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase43_hyperconvex_rank_modulation(ranks, gamma_top=4.70)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.52 * exp(4.70)
        expected_top = 0.50 + 1.52 * math.exp(4.70)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), '38th-order rank modulation must be strictly monotonically increasing'

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase43_hyperconvex_rank_modulation(0.70, gamma_top=4.70)
        assert g_70 < 1.57
        assert g_mod[-1] > 160.0

        # With negative z_denoised
        g_neg = compute_phase43_hyperconvex_rank_modulation(ranks, gamma_top=4.70, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f192_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v43('BULL_LOW_VOL') == 4.70
        assert get_regime_adaptive_gamma_top_v43('BULL_HIGH_VOL') == 4.40
        assert get_regime_adaptive_gamma_top_v43('SIDEWAYS') == 4.20
        assert get_regime_adaptive_gamma_top_v43('BEAR') == 3.90
        assert get_regime_adaptive_gamma_top_v43('CRISIS') == 1.35
        assert get_regime_adaptive_gamma_top_v43('UNKNOWN') == 4.70

    def test_feature_f192_2_152th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0004, leakage is < 10^-84
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0004, -0.0004])
        denoised = apply_centapentacontaduogonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=152.0)

        for val in denoised:
            assert abs(val) < 1e-84, f'Noise leakage {val} not suppressed below 10^-84'

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_centapentacontaduogonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=152.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_centapentacontaduogonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=152.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), 'Deadband must be strictly monotonically non-decreasing'

    def test_feature_f192_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_centapentacontaduogonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-84

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_centapentacontaduogonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-84
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_43(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=43 should route to 152th order deadband
        res_v43 = engine.apply_smooth_noise_deadband(z_noise, version=43)
        assert abs(res_v43[0]) < 1e-84

    def test_combine_predictions_version_43_confluence_and_harmony(self):
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

        comb_v42 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=42)
        comb_v43 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=43)

        assert isinstance(comb_v43, pd.DataFrame)
        assert not comb_v43.empty
        assert 'ensemble_score' in comb_v43.columns
        assert len(comb_v43) == n
        assert np.all(np.isfinite(comb_v43['ensemble_score'].values))
        assert np.all(comb_v43['ensemble_score'].values >= 0.0)
        assert np.all(comb_v43['ensemble_score'].values <= 1.0)

        # Top conviction in v43 should be >= v42
        top_v42 = comb_v42.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        top_v43 = comb_v43.sort_values('ensemble_score', ascending=False).iloc[0]['ensemble_score']
        assert top_v43 >= top_v42 - 1e-6, f'Top conviction in v43 ({top_v43}) should be >= v42 ({top_v42})'

    def test_strict_backward_compatibility_v42_and_prior(self):
        z = np.array([0.0004, 0.05, 0.15])
        out_v43 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=43)
        out_v42 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=42)
        out_v41 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=41)
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)

        assert abs(out_v43[0]) < 1e-84
        assert abs(out_v42[0]) < 1e-80
        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62

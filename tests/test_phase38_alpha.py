import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_hexadecadodecagonal_hyperbolic_deadband,
    compute_phase38_hyperconvex_rank_modulation,
    compute_phase38_rank_warping,
    REGIME_GAMMA_TOP_V38,
    get_regime_adaptive_gamma_top_v38,
    apply_smooth_deadband_attenuation,
    apply_centadodecagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    MotivicLanglandsScholzeCoupler,
    MotivicScholzeCoupler,
    LanglandsScholzeCoupler,
    ScholzeLanglandsCoupler,
    FarguesFontaineCoupler,
    MotivicFarguesFontaineCoupler,
    ScholzeVStackCoupler,
    EnsembleScoringEngine,
)


class TestPhase38AlphaEnhancements:
    """
    Test suite for Phase 38 Quantitative Alpha Signal Enhancements:
    - Feature F171: Motivic Fargues-Fontaine Curve & Scholze v-Stack Local Langlands Coupler
    - Feature F172.1: 33rd-Order Hyper-Convex Rank Modulation (g_v38)
    - Feature F172.2: 116th-Order Hexadecadodecagonal Hyperbolic Noise Deadband
    """

    def test_feature_f171_motivic_scholze_coupler_properties(self):
        coupler = MotivicLanglandsScholzeCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert "h_scholze" in res
        assert "z_langlands" in res
        assert "e_scholze" in res
        assert "FERI_v38" in res

        h = res["h_scholze"]
        z = res["z_langlands"]
        feri = res["FERI_v38"]

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res["e_scholze"].iloc[0] < res["e_scholze"].iloc[1] < res["e_scholze"].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d["h_scholze"], float)
        assert np.isclose(res_1d["e_scholze"], 0.0, atol=1e-7)
        assert np.isclose(res_1d["z_langlands"], 1.0, atol=1e-7)
        assert np.isclose(res_1d["h_scholze"], 1.0, atol=1e-7)

    def test_feature_f171_scholze_aliases_and_exports(self):
        assert MotivicScholzeCoupler is MotivicLanglandsScholzeCoupler
        assert LanglandsScholzeCoupler is MotivicLanglandsScholzeCoupler
        assert ScholzeLanglandsCoupler is MotivicLanglandsScholzeCoupler
        assert FarguesFontaineCoupler is MotivicLanglandsScholzeCoupler
        assert MotivicFarguesFontaineCoupler is MotivicLanglandsScholzeCoupler
        assert ScholzeVStackCoupler is MotivicLanglandsScholzeCoupler

        res_class = EnsembleScoringEngine.compute_motivic_langlands_scholze_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert "h_scholze" in res_class
        assert "FERI_v38" in res_class

    def test_feature_f172_1_33rd_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^33 concentrates conviction into top 0.000000000000000000000001%
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase38_hyperconvex_rank_modulation(ranks, gamma_top=3.90)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.40 * exp(3.90)
        expected_top = 0.50 + 1.40 * math.exp(3.90)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), "33rd-order rank modulation must be strictly monotonically increasing"

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase38_hyperconvex_rank_modulation(0.70, gamma_top=3.90)
        # 0.70^33 is ~ 8.7e-6, exp(3.90 * 8.7e-6) ~ 1.000034, so g(0.70) ~ 0.50 + 1.40*0.70 = 1.48
        assert g_70 < 1.55
        assert g_mod[-1] > 60.0

        # With negative z_denoised
        g_neg = compute_phase38_hyperconvex_rank_modulation(ranks, gamma_top=3.90, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f172_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v38('BULL_LOW_VOL') == 3.90
        assert get_regime_adaptive_gamma_top_v38('BULL_HIGH_VOL') == 3.60
        assert get_regime_adaptive_gamma_top_v38('SIDEWAYS') == 3.40
        assert get_regime_adaptive_gamma_top_v38('BEAR') == 3.10
        assert get_regime_adaptive_gamma_top_v38('CRISIS') == 0.95
        assert get_regime_adaptive_gamma_top_v38('UNKNOWN') == 3.90

    def test_feature_f172_2_116th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0004, leakage is < 10^-60
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0004, -0.0004])
        denoised = apply_hexadecadodecagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=116.0)

        for val in denoised:
            assert abs(val) < 1e-60, f"Noise leakage {val} not suppressed below 10^-60"

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_hexadecadodecagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=116.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_hexadecadodecagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=116.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), "Deadband must be strictly monotonically non-decreasing"

    def test_feature_f172_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_hexadecadodecagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-60

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_hexadecadodecagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-60
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_38(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=38 should route to 116th order deadband
        res_v38 = engine.apply_smooth_noise_deadband(z_noise, version=38)
        assert abs(res_v38[0]) < 1e-60

    def test_combine_predictions_version_38_confluence_and_harmony(self):
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

        comb_v37 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=37)
        comb_v38 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=38)

        assert isinstance(comb_v38, pd.DataFrame)
        assert not comb_v38.empty
        assert "ensemble_score" in comb_v38.columns
        assert len(comb_v38) == n
        assert np.all(np.isfinite(comb_v38["ensemble_score"].values))
        assert np.all(comb_v38["ensemble_score"].values >= 0.0)
        assert np.all(comb_v38["ensemble_score"].values <= 1.0)

        # Top conviction in v38 should be >= v37
        top_v37 = comb_v37.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v38 = comb_v38.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v38 >= top_v37 - 1e-6, f"Top conviction in v38 ({top_v38}) should be >= v37 ({top_v37})"

    def test_strict_backward_compatibility_v37_and_v36(self):
        z = np.array([0.0004, 0.05, 0.15])
        out_v37 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=37)
        out_v36 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=36)
        out_v35 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=35)

        assert abs(out_v37[0]) < 1e-60
        assert abs(out_v36[0]) < 1e-55
        assert abs(out_v35[0]) < 1e-50

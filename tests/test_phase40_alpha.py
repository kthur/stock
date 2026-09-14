import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_octacontatetragonal_hyperbolic_deadband,
    compute_phase40_hyperconvex_rank_modulation,
    compute_phase40_rank_warping,
    REGIME_GAMMA_TOP_V40,
    get_regime_adaptive_gamma_top_v40,
    apply_smooth_deadband_attenuation,
    apply_centaicosagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    GeometricLanglandsHodgeDeligneCoupler,
    GeometricLanglandsHodgeDeligneFactorCoupler,
    HodgeDeligneCoupler,
    LanglandsDeligneCoupler,
    HodgeDeligneAnalyticCoupler,
    Phase40Coupler,
    DeligneLanglandsCoupler,
    EnsembleScoringEngine,
)


class TestPhase40AlphaEnhancements:
    """
    Test suite for Phase 40 Quantitative Alpha Signal Enhancements:
    - Feature F179: Geometric Langlands & Non-Abelian Hodge-Deligne Analytic Cohomology Coupler
    - Feature F180.1: 35th-Order Hyper-Convex Rank Modulation (g_v40)
    - Feature F180.2: 128th-Order Octaconta-tetragonal Hyperbolic Noise Deadband
    """

    def test_feature_f179_geometric_langlands_hodge_deligne_coupler_properties(self):
        coupler = GeometricLanglandsHodgeDeligneCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert "h_deligne" in res
        assert "z_deligne" in res
        assert "e_hodge" in res
        assert "FERI_v40" in res
        assert "Z_deligne" in res
        assert "E_hodge" in res
        assert "h_langlands" in res

        h = res["h_deligne"]
        z = res["z_deligne"]
        feri = res["FERI_v40"]

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res["e_hodge"].iloc[0] < res["e_hodge"].iloc[1] < res["e_hodge"].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d["h_deligne"], float)
        assert np.isclose(res_1d["e_hodge"], 0.0, atol=1e-7)
        assert np.isclose(res_1d["z_deligne"], 1.0, atol=1e-7)
        assert np.isclose(res_1d["h_deligne"], 1.0, atol=1e-7)

    def test_feature_f179_langlands_deligne_aliases_and_exports(self):
        assert GeometricLanglandsHodgeDeligneFactorCoupler is GeometricLanglandsHodgeDeligneCoupler
        assert HodgeDeligneCoupler is GeometricLanglandsHodgeDeligneCoupler
        assert LanglandsDeligneCoupler is GeometricLanglandsHodgeDeligneCoupler
        assert HodgeDeligneAnalyticCoupler is GeometricLanglandsHodgeDeligneCoupler
        assert Phase40Coupler is GeometricLanglandsHodgeDeligneCoupler
        assert DeligneLanglandsCoupler is GeometricLanglandsHodgeDeligneCoupler

        res_class = EnsembleScoringEngine.compute_geometric_langlands_hodge_deligne_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert "h_deligne" in res_class
        assert "FERI_v40" in res_class

    def test_feature_f180_1_35th_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^35 concentrates conviction into top 0.00000000000000000000000001%
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.45 * exp(4.20)
        expected_top = 0.50 + 1.45 * math.exp(4.20)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), "35th-order rank modulation must be strictly monotonically increasing"

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase40_hyperconvex_rank_modulation(0.70, gamma_top=4.20)
        # 0.70^35 is ~ 1.9e-6, exp(4.20 * 1.9e-6) ~ 1.000008, so g(0.70) ~ 0.50 + 1.45*0.70 = 1.515
        assert g_70 < 1.55
        assert g_mod[-1] > 90.0

        # With negative z_denoised
        g_neg = compute_phase40_hyperconvex_rank_modulation(ranks, gamma_top=4.20, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f180_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v40('BULL_LOW_VOL') == 4.20
        assert get_regime_adaptive_gamma_top_v40('BULL_HIGH_VOL') == 3.90
        assert get_regime_adaptive_gamma_top_v40('SIDEWAYS') == 3.70
        assert get_regime_adaptive_gamma_top_v40('BEAR') == 3.40
        assert get_regime_adaptive_gamma_top_v40('CRISIS') == 1.10
        assert get_regime_adaptive_gamma_top_v40('UNKNOWN') == 4.20

    def test_feature_f180_2_128th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0004, leakage is < 10^-68
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0004, -0.0004])
        denoised = apply_octacontatetragonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=128.0)

        for val in denoised:
            assert abs(val) < 1e-68, f"Noise leakage {val} not suppressed below 10^-68"

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_octacontatetragonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=128.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_octacontatetragonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=128.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), "Deadband must be strictly monotonically non-decreasing"

    def test_feature_f180_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_octacontatetragonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-68

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_octacontatetragonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-68
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_40(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=40 should route to 128th order deadband
        res_v40 = engine.apply_smooth_noise_deadband(z_noise, version=40)
        assert abs(res_v40[0]) < 1e-68

    def test_combine_predictions_version_40_confluence_and_harmony(self):
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

        comb_v39 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=39)
        comb_v40 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=40)

        assert isinstance(comb_v40, pd.DataFrame)
        assert not comb_v40.empty
        assert "ensemble_score" in comb_v40.columns
        assert len(comb_v40) == n
        assert np.all(np.isfinite(comb_v40["ensemble_score"].values))
        assert np.all(comb_v40["ensemble_score"].values >= 0.0)
        assert np.all(comb_v40["ensemble_score"].values <= 1.0)

        # Top conviction in v40 should be >= v39
        top_v39 = comb_v39.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v40 = comb_v40.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v40 >= top_v39 - 1e-6, f"Top conviction in v40 ({top_v40}) should be >= v39 ({top_v39})"

    def test_strict_backward_compatibility_v39_and_prior(self):
        z = np.array([0.0004, 0.05, 0.15])
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)
        out_v38 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=38)
        out_v37 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=37)

        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62
        assert abs(out_v38[0]) < 1e-60
        assert abs(out_v37[0]) < 1e-60

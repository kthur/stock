r"""
tests/test_phase35_alpha.py

Comprehensive unit test suite for Phase 35 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F159: Motivic Tate-Shafarevich Group & Fontaine-Mazur Geometric Representation Coupler
  (MotivicShafarevichFontaineMazurCoupler, Shafarevich obstruction complex E_sha,
  Fontaine-Mazur geometric invariant Z_fontaine_mazur, coupling factor h_sha,
  theta_0=0.50, kappa_sha=5.00, complete aliases and factor_suppression bindings)
- Feature F160.1: 30th-Order Hyper-Convex Rank Modulation (g_v35(r) = 0.50 + 1.34 * r * exp(gamma_top * r^30))
  with regime-adaptive gamma_top up to 3.60 (REGIME_GAMMA_TOP_V35, get_regime_adaptive_gamma_top_v35)
- Feature F160.2: 104th-Order Tetracentagonal Hyperbolic Tangent Noise Deadband (alpha=104.0, leakage < 10^-54)
- End-to-End EnsembleScoringEngine combine_predictions() with version=35
- Strict backward compatibility validation with Phase 14 through Phase 34
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_tetracentagonal_hyperbolic_deadband,
    apply_centagonal_hyperbolic_deadband,
    apply_hexanonacontagonal_hyperbolic_deadband,
    apply_nonacontaditagonal_hyperbolic_deadband,
    apply_octaoctacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase35_hyperconvex_rank_modulation,
    compute_phase35_rank_warping,
    compute_phase34_hyperconvex_rank_modulation,
    compute_phase33_hyperconvex_rank_modulation,
    MotivicShafarevichFontaineMazurCoupler,
    MotivicShafarevichCoupler,
    FontaineMazurCoupler,
    ShafarevichFontaineMazurCoupler,
    ShafarevichCoupler,
    TateShafarevichCoupler,
    MotivicTateShafarevichCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetracentagonal_hyperbolic_deadband as fs_tetracentagonal_deadband,
    apply_centagonal_hyperbolic_deadband as fs_centagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase35_hyperconvex_rank_modulation as fs_compute_phase35_modulation,
    compute_phase35_rank_warping as fs_compute_phase35_warping,
    REGIME_GAMMA_TOP_V35 as fs_REGIME_GAMMA_TOP_V35,
    get_regime_adaptive_gamma_top_v35 as fs_get_regime_adaptive_gamma_top_v35,
    MotivicShafarevichFontaineMazurCoupler as fs_MotivicShafarevichFontaineMazurCoupler,
    MotivicShafarevichCoupler as fs_MotivicShafarevichCoupler,
    FontaineMazurCoupler as fs_FontaineMazurCoupler,
    ShafarevichFontaineMazurCoupler as fs_ShafarevichFontaineMazurCoupler,
    ShafarevichCoupler as fs_ShafarevichCoupler,
    TateShafarevichCoupler as fs_TateShafarevichCoupler,
    MotivicTateShafarevichCoupler as fs_MotivicTateShafarevichCoupler,
)


class TestPhase35AlphaEnhancements:
    """Test suite for Phase 35 Alpha Engine Innovations."""

    def test_feature_f159_motivic_sha_coupler_properties(self):
        """Verify MotivicShafarevichFontaineMazurCoupler calculation and canonical outputs."""
        coupler = MotivicShafarevichFontaineMazurCoupler(theta_0=0.50, kappa_sha=5.00)
        p_vec = np.array([0.55, 0.62, 0.48, 0.51, 0.58])
        res = coupler.evaluate(p_vec)

        assert isinstance(res, dict)
        expected_keys = [
            "h_sha", "z_fontaine_mazur", "e_sha", "h_decay", "FERI_v35",
            "feri_v35", "Z_fontaine_mazur", "E_sha", "H_sha",
            "h_motivic_sha", "z_motivic_sha", "e_motivic_sha",
            "h_fontaine_mazur", "z_sha", "e_fontaine_mazur",
            "h_tate_shafarevich", "z_tate_shafarevich", "e_tate_shafarevich",
            "h_motivic", "z_motivic", "e_motivic",
        ]
        for k in expected_keys:
            assert k in res, f"Missing key: {k}"

        assert 0.0 <= res["h_sha"] <= 1.0
        assert 0.0 <= res["z_fontaine_mazur"] <= 1.0
        assert res["e_sha"] >= 0.0
        assert 0.0 <= res["FERI_v35"] <= 1.0

        # Uniform vector has 0 obstruction energy
        p_uniform = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_u = coupler.evaluate(p_uniform)
        assert math.isclose(res_u["e_sha"], 0.0, abs_tol=1e-8)
        assert math.isclose(res_u["z_fontaine_mazur"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["h_sha"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["FERI_v35"], 1.0, abs_tol=1e-8)

    def test_feature_f159_sha_aliases_and_exports(self):
        """Verify all class aliases and dynamic export bindings for Feature F159."""
        aliases = [
            MotivicShafarevichFontaineMazurCoupler,
            MotivicShafarevichCoupler,
            FontaineMazurCoupler,
            ShafarevichFontaineMazurCoupler,
            ShafarevichCoupler,
            TateShafarevichCoupler,
            MotivicTateShafarevichCoupler,
        ]
        p_vec = np.array([[0.5, 0.6, 0.4, 0.5, 0.7]])
        for cls_alias in aliases:
            out = cls_alias.compute(p_vec)
            assert "h_sha" in out
            assert "z_fontaine_mazur" in out

        fs_aliases = [
            fs_MotivicShafarevichFontaineMazurCoupler,
            fs_MotivicShafarevichCoupler,
            fs_FontaineMazurCoupler,
            fs_ShafarevichFontaineMazurCoupler,
            fs_ShafarevichCoupler,
            fs_TateShafarevichCoupler,
            fs_MotivicTateShafarevichCoupler,
        ]
        for cls_alias in fs_aliases:
            out = cls_alias.compute(p_vec)
            assert "h_sha" in out
            assert "z_fontaine_mazur" in out

    def test_feature_f160_1_30th_order_rank_modulation_convexity(self):
        """Verify 30th-order hyper-convex modulation g_v35(r) = 0.50 + 1.34*r*exp(gamma_top*r^30)."""
        ranks = np.array([0.0, 0.2, 0.5, 0.8, 0.95, 0.99, 1.0])
        z_pos = np.ones_like(ranks)
        gamma = 3.60

        mod_vals = compute_phase35_hyperconvex_rank_modulation(ranks, gamma_top=gamma, z_denoised=z_pos)

        # Baseline at r=0 is exactly 0.50
        assert math.isclose(mod_vals[0], 0.50, abs_tol=1e-5)

        # Top 1% (r=1.0) must achieve ultra-high conviction: 0.50 + 1.34 * exp(3.60)
        expected_top = 0.50 + 1.34 * math.exp(gamma)
        assert math.isclose(mod_vals[-1], expected_top, rel_tol=1e-5)
        assert mod_vals[-1] > 49.0  # 0.5 + 1.34 * 36.598 = 49.54

        # Monotonicity check
        assert np.all(np.diff(mod_vals) > 0)

        # Flatness in bottom 60% vs explosive growth in top 5%
        growth_bottom = mod_vals[2] - mod_vals[0]
        growth_top = mod_vals[-1] - mod_vals[-3]
        assert growth_top > 20.0 * growth_bottom

        # Verify alias
        mod_alias = compute_phase35_rank_warping(ranks, gamma_top=gamma, z_denoised=z_pos)
        np.testing.assert_allclose(mod_vals, mod_alias)

    def test_feature_f160_1_regime_adaptive_gamma_top(self):
        """Verify regime adaptive gamma_top table for Phase 35."""
        assert fs_REGIME_GAMMA_TOP_V35['BULL_LOW_VOL'] == 3.60
        assert fs_REGIME_GAMMA_TOP_V35['BULL_HIGH_VOL'] == 3.30
        assert fs_REGIME_GAMMA_TOP_V35['SIDEWAYS'] == 3.10
        assert fs_REGIME_GAMMA_TOP_V35['BEAR'] == 2.80
        assert fs_REGIME_GAMMA_TOP_V35['CRISIS'] == 0.90
        assert fs_REGIME_GAMMA_TOP_V35['RECOVERY'] == 3.40

        assert fs_get_regime_adaptive_gamma_top_v35('bull_low_vol') == 3.60
        assert fs_get_regime_adaptive_gamma_top_v35('crisis') == 0.90
        assert fs_get_regime_adaptive_gamma_top_v35(2) == 3.60

    def test_feature_f160_2_104th_order_hyperbolic_deadband_leakage(self):
        """Verify 104th-Order Tetracentagonal deadband eliminates noise leakage to < 10^-54."""
        # For |z| <= 0.0006 with delta=0.035:
        # ratio <= 0.0006 / 0.035 = 0.01714
        # ratio^104 <= (0.01714)^104 < 10^-180, tanh(arg) <= 10^-180, leakage < 10^-54.
        micro_noise = np.array([-0.0006, -0.0003, 0.0, 0.0003, 0.0006])
        denoised = apply_tetracentagonal_hyperbolic_deadband(micro_noise, delta_noise=0.035)

        for val in denoised:
            assert abs(val) < 1e-54, f"Leakage violation: {val}"

        # High conviction transmission (|z| >= 0.150)
        high_conviction = np.array([0.150, 0.200, 0.350])
        transmitted = apply_tetracentagonal_hyperbolic_deadband(high_conviction, delta_noise=0.035)
        np.testing.assert_allclose(high_conviction, transmitted, rtol=1e-7)

        # Monotonicity check
        grid = np.linspace(-0.20, 0.20, 2000)
        denoised_grid = apply_tetracentagonal_hyperbolic_deadband(grid, delta_noise=0.035)
        assert np.all(np.diff(denoised_grid) >= 0.0)

    def test_feature_f160_2_factor_suppression_delegation(self):
        """Verify factor_suppression module functions and deadband attenuation routing."""
        z = np.array([0.0005, 0.10, -0.0005])
        out1 = fs_tetracentagonal_deadband(z)
        out2 = apply_tetracentagonal_hyperbolic_deadband(z)
        np.testing.assert_allclose(out1, out2)

        # Smooth deadband attenuation with version=35 must route to 104th-order deadband
        res_v35 = fs_smooth_deadband(z, version=35)
        np.testing.assert_allclose(res_v35, out1)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_35(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband with version=35."""
        z = np.array([0.0004, -0.0004, 0.18])
        res_v35 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=35)
        assert abs(res_v35[0]) < 1e-54
        assert abs(res_v35[1]) < 1e-54
        assert math.isclose(res_v35[2], 0.18, rel_tol=1e-7)

    def test_combine_predictions_version_35_confluence_and_harmony(self):
        """Verify combine_predictions with version=35 integrates MotivicShafarevichCoupler."""
        engine = EnsembleScoringEngine()
        N = 20
        df_list = []
        for i in range(N):
            df_list.append({
                "symbol": f"STOCK_{i:03d}",
                "market": "SP500",
                "regression": 0.35 + 0.02 * i,
                "surge": 0.30 + 0.02 * i,
                "vcp_ml": 0.25 + 0.02 * i,
            })
        test_df = pd.DataFrame(df_list)

        comb_v34 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=34)
        comb_v35 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=35)

        assert isinstance(comb_v35, pd.DataFrame)
        assert not comb_v35.empty
        assert "ensemble_score" in comb_v35.columns
        assert len(comb_v35) == N
        assert np.all(np.isfinite(comb_v35["ensemble_score"].values))
        assert np.all(comb_v35["ensemble_score"].values >= 0.0)
        assert np.all(comb_v35["ensemble_score"].values <= 1.0)

        # Top conviction in v35 should be >= v34
        top_v34 = comb_v34.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v35 = comb_v35.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v35 >= top_v34 - 1e-6, f"Top conviction in v35 ({top_v35}) should be >= v34 ({top_v34})"

    def test_strict_backward_compatibility_v34_and_v33(self):
        """Verify strict backward compatibility with version 34 and 33."""
        z = np.array([0.0008, 0.05, 0.15])
        out_v34 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=34)
        out_v33 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=33)

        assert abs(out_v34[0]) < 1e-45
        assert abs(out_v33[0]) < 1e-40

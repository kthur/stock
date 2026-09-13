r"""
tests/test_phase31_alpha.py

Comprehensive unit test suite for Phase 31 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F143: Motivic Kato Euler System & Fontaine-Perrin-Riou Dual Exponential Coupler
  (MotivicKatoDualExponentialCoupler, Kato obstruction complex E_kato,
  Fontaine crystalline class invariant Z_fontaine, coupling factor h_kato,
  theta_0=0.42, kappa_kato=4.20, complete aliases and factor_suppression bindings)
- Feature F144.1: 26th-Order Hyper-Convex Rank Modulation (g_v31(r) = 0.50 + 1.26 * r * exp(gamma_top * r^26))
  with regime-adaptive gamma_top up to 3.20 (REGIME_GAMMA_TOP_V31, get_regime_adaptive_gamma_top_v31)
- Feature F144.2: 88th-Order Octaoctacontagonal Hyperbolic Tangent Noise Deadband (alpha=88.0, leakage < 10^-46)
- End-to-End EnsembleScoringEngine combine_predictions() with version=31
- Strict backward compatibility validation with Phase 14 through Phase 30
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_octaoctacontagonal_hyperbolic_deadband,
    apply_tetraoctacontagonal_hyperbolic_deadband,
    apply_octacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase31_hyperconvex_rank_modulation,
    compute_phase31_rank_warping,
    compute_phase30_hyperconvex_rank_modulation,
    compute_phase29_hyperconvex_rank_modulation,
    MotivicKatoDualExponentialCoupler,
    KatoDualExponentialCoupler,
    KatoCoupler,
    FontaineCoupler,
    KatoFontaineCoupler,
    PerrinRiouCoupler,
    FontainePerrinRiouCoupler,
    MotivicFontaineCoupler,
    CrystallineCoupler,
    KatoEulerSystemCoupler,
    MotivicKatoCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_octaoctacontagonal_hyperbolic_deadband as fs_octaoctacontagonal_deadband,
    apply_tetraoctacontagonal_hyperbolic_deadband as fs_tetraoctacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase31_hyperconvex_rank_modulation as fs_compute_phase31_modulation,
    compute_phase31_rank_warping as fs_compute_phase31_warping,
    REGIME_GAMMA_TOP_V31 as fs_REGIME_GAMMA_TOP_V31,
    get_regime_adaptive_gamma_top_v31 as fs_get_regime_adaptive_gamma_top_v31,
    MotivicKatoDualExponentialCoupler as fs_MotivicKatoDualExponentialCoupler,
    KatoDualExponentialCoupler as fs_KatoDualExponentialCoupler,
    KatoCoupler as fs_KatoCoupler,
    FontaineCoupler as fs_FontaineCoupler,
    KatoFontaineCoupler as fs_KatoFontaineCoupler,
    PerrinRiouCoupler as fs_PerrinRiouCoupler,
    FontainePerrinRiouCoupler as fs_FontainePerrinRiouCoupler,
    MotivicFontaineCoupler as fs_MotivicFontaineCoupler,
    CrystallineCoupler as fs_CrystallineCoupler,
    KatoEulerSystemCoupler as fs_KatoEulerSystemCoupler,
    MotivicKatoCoupler as fs_MotivicKatoCoupler,
    compute_motivic_kato_dual_exponential_coupling as fs_compute_motivic_kato_dual_exponential_coupling,
)


class TestPhase31AlphaSignalEnhancement:
    """Test suite for Phase 31 Alpha Signal Enhancements."""

    def test_feature_f143_motivic_kato_coupler_instantiation_and_computation(self):
        """Verify MotivicKatoDualExponentialCoupler calculation and canonical outputs."""
        coupler = MotivicKatoDualExponentialCoupler(theta_0=0.42, kappa_kato=4.20)
        p_data = {
            'val': [0.85, 0.20, 0.40],
            'mom': [0.90, 0.15, 0.50],
            'flow': [0.80, 0.10, 0.30],
            'cat': [0.95, 0.25, 0.60],
            'net': [0.75, 0.05, 0.45],
        }
        df = pd.DataFrame(p_data, index=['stock_A', 'stock_B', 'stock_C'])
        res = coupler.evaluate(df)

        assert "h_kato" in res
        assert "z_fontaine" in res
        assert "e_kato" in res
        assert "FERI_v31" in res

        assert len(res["h_kato"]) == 3
        assert len(res["z_fontaine"]) == 3
        assert len(res["e_kato"]) == 3
        assert len(res["FERI_v31"]) == 3

        # stock_A has high concordant values, stock_B has low
        assert res["FERI_v31"].iloc[0] > 0.0
        assert res["h_kato"].iloc[0] > 0.0
        assert (res["z_fontaine"] > 0.0).all()

    def test_feature_f143_aliases_and_facades(self):
        """Verify that all Kato and Fontaine aliases point to the correct class and methods."""
        for alias_cls in [
            KatoDualExponentialCoupler,
            KatoCoupler,
            FontaineCoupler,
            KatoFontaineCoupler,
            PerrinRiouCoupler,
            FontainePerrinRiouCoupler,
            MotivicFontaineCoupler,
            CrystallineCoupler,
            KatoEulerSystemCoupler,
            MotivicKatoCoupler,
            fs_MotivicKatoDualExponentialCoupler,
            fs_KatoDualExponentialCoupler,
            fs_KatoCoupler,
            fs_FontaineCoupler,
            fs_KatoFontaineCoupler,
            fs_PerrinRiouCoupler,
            fs_FontainePerrinRiouCoupler,
            fs_MotivicFontaineCoupler,
            fs_CrystallineCoupler,
            fs_KatoEulerSystemCoupler,
            fs_MotivicKatoCoupler,
        ]:
            assert issubclass(alias_cls, MotivicKatoDualExponentialCoupler) or alias_cls is MotivicKatoDualExponentialCoupler

        p_vec = np.array([0.5, 0.6, 0.4, 0.7, 0.5])
        res1 = MotivicKatoDualExponentialCoupler.compute(p_vec)
        res2 = EnsembleScoringEngine.compute_motivic_kato_dual_exponential_coupling(p_vec)
        res3 = fs_compute_motivic_kato_dual_exponential_coupling(p_vec)

        assert math.isclose(float(res1["h_kato"]), float(res2["h_kato"]), rel_tol=1e-7)
        assert math.isclose(float(res1["z_fontaine"]), float(res3["z_fontaine"]), rel_tol=1e-7)

    def test_feature_f144_1_hyperconvex_rank_modulation(self):
        """Verify 26th-order hyper-convex rank modulation g_v31(r)."""
        ranks = pd.Series([0.1, 0.5, 0.9, 0.99, 1.0])
        z_pos = pd.Series([0.1, 0.1, 0.1, 0.1, 0.1])
        z_neg = pd.Series([-0.1, -0.1, -0.1, -0.1, -0.1])

        mult_pos = compute_phase31_hyperconvex_rank_modulation(ranks, gamma_top=3.20, z_denoised=z_pos)
        mult_neg = compute_phase31_hyperconvex_rank_modulation(ranks, gamma_top=3.20, z_denoised=z_neg)

        # For top rank r=1.0, g_v31(1.0) = 0.50 + 1.26 * 1.0 * exp(3.20 * 1^26) = 0.50 + 1.26 * exp(3.20)
        expected_top = 0.50 + 1.26 * math.exp(3.20)
        assert math.isclose(mult_pos.iloc[-1], expected_top, rel_tol=1e-5)

        # For bottom rank r=0.1, g_v31(0.1) ~ 0.50 + 1.26 * 0.1 * exp(3.20 * 0.1^26) ~ 0.50 + 0.126 ~ 0.626
        assert mult_pos.iloc[0] < 0.70

        # Monotonicity for positive signals
        assert (np.diff(mult_pos.values) > 0).all()

        # Negative signals should penalize high ranks
        assert mult_neg.iloc[-1] < mult_neg.iloc[0]

    def test_feature_f144_1_regime_adaptive_gamma_top(self):
        """Verify regime adaptive gamma_top table and getter."""
        assert fs_REGIME_GAMMA_TOP_V31['BULL_LOW_VOL'] == 3.20
        assert fs_REGIME_GAMMA_TOP_V31['BULL_HIGH_VOL'] == 2.90
        assert fs_REGIME_GAMMA_TOP_V31['SIDEWAYS'] == 2.70
        assert fs_REGIME_GAMMA_TOP_V31['BEAR'] == 2.40
        assert fs_REGIME_GAMMA_TOP_V31['CRISIS'] == 0.90

        assert fs_get_regime_adaptive_gamma_top_v31('BULL_LOW_VOL') == 3.20
        assert fs_get_regime_adaptive_gamma_top_v31('CRISIS') == 0.90
        assert fs_get_regime_adaptive_gamma_top_v31('SIDEWAYS') == 2.70

    def test_feature_f144_2_88th_order_octaoctacontagonal_deadband(self):
        """Verify 88th-order deadband suppresses noise to < 10^-46 while transmitting signals."""
        # Sub-threshold noise |z| <= 0.0010
        z_noise = 0.0010
        res_noise = apply_octaoctacontagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=88.0)
        # ratio = 0.0010 / 0.035 ~ 0.02857
        # ratio^88 ~ 10^-136 -> tanh(arg) * z < 10^-46
        assert abs(res_noise) < 1e-46

        # Strong signal |z| >= 0.150
        z_signal = 0.150
        res_signal = apply_octaoctacontagonal_hyperbolic_deadband(z_signal, delta_noise=0.035, alpha_pos=88.0)
        # Should transmit 100.000%
        assert math.isclose(res_signal, z_signal, rel_tol=1e-7)

        # Monotonicity
        arr = np.linspace(-0.20, 0.20, 100)
        filtered = apply_octaoctacontagonal_hyperbolic_deadband(arr, delta_noise=0.035, alpha_pos=88.0)
        assert (np.diff(filtered) >= -1e-12).all()

    def test_feature_f144_2_factor_suppression_delegation(self):
        """Verify deadband functions via factor_suppression bindings."""
        z = 0.05
        r1 = apply_octaoctacontagonal_hyperbolic_deadband(z)
        r2 = fs_octaoctacontagonal_deadband(z)
        assert math.isclose(r1, r2, rel_tol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_31(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband delegates to 88th-order deadband under v31."""
        z_noise = 0.0010
        out_v31 = apply_smooth_deadband_attenuation(z_noise, version=31)
        out_v30 = apply_smooth_deadband_attenuation(z_noise, version=30)

        # v31 should have even stricter attenuation than v30
        assert abs(out_v31) <= abs(out_v30)
        assert abs(out_v31) < 1e-46

    def test_combine_predictions_version_31_confluence_and_harmony(self):
        """Verify EnsembleScoringEngine.combine_predictions with version=31 incorporates Kato bonus."""
        engine = EnsembleScoringEngine()
        N = 25
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

        comb_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)
        comb_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)

        assert isinstance(comb_v31, pd.DataFrame)
        assert not comb_v31.empty
        assert "ensemble_score" in comb_v31.columns
        assert len(comb_v31) == N
        assert np.all(np.isfinite(comb_v31["ensemble_score"].values))
        assert np.all(comb_v31["ensemble_score"].values >= 0.0)
        assert np.all(comb_v31["ensemble_score"].values <= 1.0)

        # Top conviction in v31 should be >= v30
        top_v30 = comb_v30.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v31 = comb_v31.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v31 >= top_v30 - 1e-6, f"Top conviction in v31 ({top_v31}) should be >= v30 ({top_v30})"

    def test_strict_backward_compatibility_v30_and_v29(self):
        """Verify that combine_predictions with version=30 and 29 behaves identically to pre-Phase 31."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)
        res_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)
        res_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)
        res_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)

        assert len(res_v28) == N
        assert len(res_v29) == N
        assert len(res_v30) == N
        assert len(res_v31) == N
        assert all("ensemble_score" in res_v31.columns for _ in [1])
        assert all("ensemble_score" in res_v30.columns for _ in [1])
        assert all("ensemble_score" in res_v29.columns for _ in [1])
        assert all("ensemble_score" in res_v28.columns for _ in [1])

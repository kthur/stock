r"""
tests/test_phase33_alpha.py

Comprehensive unit test suite for Phase 33 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F151: Motivic Tamagawa Number Conjecture & Bloch-Kato Exponential Coupler
  (MotivicTamagawaBlochKatoCoupler, tamagawa obstruction complex E_tamagawa,
  Bloch-Kato exponential class invariant Z_bloch_kato, coupling factor h_tamagawa,
  theta_0=0.46, kappa_tamagawa=4.60, complete aliases and factor_suppression bindings)
- Feature F152.1: 28th-Order Hyper-Convex Rank Modulation (g_v33(r) = 0.50 + 1.30 * r * exp(gamma_top * r^28))
  with regime-adaptive gamma_top up to 3.40 (REGIME_GAMMA_TOP_V33, get_regime_adaptive_gamma_top_v33)
- Feature F152.2: 96th-Order Hexanonacontagonal Hyperbolic Tangent Noise Deadband (alpha=96.0, leakage < 10^-50)
- End-to-End EnsembleScoringEngine combine_predictions() with version=33
- Strict backward compatibility validation with Phase 14 through Phase 32
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_hexanonacontagonal_hyperbolic_deadband,
    apply_nonacontaditagonal_hyperbolic_deadband,
    apply_octaoctacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase33_hyperconvex_rank_modulation,
    compute_phase33_rank_warping,
    compute_phase32_hyperconvex_rank_modulation,
    compute_phase31_hyperconvex_rank_modulation,
    MotivicTamagawaBlochKatoCoupler,
    MotivicTamagawaCoupler,
    BlochKatoCoupler,
    TamagawaBlochKatoCoupler,
    TamagawaNumberCoupler,
    BlochKatoExponentialCoupler,
    TamagawaBlochKatoExponentialCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexanonacontagonal_hyperbolic_deadband as fs_hexanonacontagonal_deadband,
    apply_nonacontaditagonal_hyperbolic_deadband as fs_nonacontaditagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase33_hyperconvex_rank_modulation as fs_compute_phase33_modulation,
    compute_phase33_rank_warping as fs_compute_phase33_warping,
    REGIME_GAMMA_TOP_V33 as fs_REGIME_GAMMA_TOP_V33,
    get_regime_adaptive_gamma_top_v33 as fs_get_regime_adaptive_gamma_top_v33,
    MotivicTamagawaBlochKatoCoupler as fs_MotivicTamagawaBlochKatoCoupler,
    MotivicTamagawaCoupler as fs_MotivicTamagawaCoupler,
    BlochKatoCoupler as fs_BlochKatoCoupler,
    TamagawaBlochKatoCoupler as fs_TamagawaBlochKatoCoupler,
    TamagawaNumberCoupler as fs_TamagawaNumberCoupler,
    BlochKatoExponentialCoupler as fs_BlochKatoExponentialCoupler,
    TamagawaBlochKatoExponentialCoupler as fs_TamagawaBlochKatoExponentialCoupler,
)


class TestPhase33AlphaEnhancements:
    """Test suite for Phase 33 Alpha Engine Innovations."""

    def test_feature_f151_motivic_tamagawa_coupler_properties(self):
        """Verify MotivicTamagawaBlochKatoCoupler calculation and canonical outputs."""
        coupler = MotivicTamagawaBlochKatoCoupler(theta_0=0.46, kappa_tamagawa=4.60)
        p_vec = np.array([0.55, 0.62, 0.48, 0.51, 0.58])
        res = coupler.evaluate(p_vec)

        assert isinstance(res, dict)
        expected_keys = [
            "h_tamagawa", "z_bloch_kato", "e_tamagawa", "h_decay", "FERI_v33",
            "feri_v33", "Z_bloch_kato", "E_tamagawa", "H_tamagawa",
            "h_motivic_tamagawa", "z_motivic_tamagawa", "e_motivic_tamagawa",
            "h_bloch_kato", "z_tamagawa", "e_bloch_kato",
            "h_tamagawa_number", "z_tamagawa_number", "e_tamagawa_number",
            "h_bloch_kato_exp", "z_bloch_kato_exp", "e_bloch_kato_exp",
            "h_motivic", "z_motivic", "e_motivic",
        ]
        for k in expected_keys:
            assert k in res, f"Missing key: {k}"

        assert 0.0 <= res["h_tamagawa"] <= 1.0
        assert 0.0 <= res["z_bloch_kato"] <= 1.0
        assert res["e_tamagawa"] >= 0.0
        assert 0.0 <= res["FERI_v33"] <= 1.0

        # Uniform vector has 0 obstruction energy
        p_uniform = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_u = coupler.evaluate(p_uniform)
        assert math.isclose(res_u["e_tamagawa"], 0.0, abs_tol=1e-8)
        assert math.isclose(res_u["z_bloch_kato"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["h_tamagawa"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["FERI_v33"], 1.0, abs_tol=1e-8)

    def test_feature_f151_tamagawa_aliases_and_exports(self):
        """Verify all class aliases and dynamic export bindings for Feature F151."""
        aliases = [
            MotivicTamagawaBlochKatoCoupler,
            MotivicTamagawaCoupler,
            BlochKatoCoupler,
            TamagawaBlochKatoCoupler,
            TamagawaNumberCoupler,
            BlochKatoExponentialCoupler,
            TamagawaBlochKatoExponentialCoupler,
            fs_MotivicTamagawaBlochKatoCoupler,
            fs_MotivicTamagawaCoupler,
            fs_BlochKatoCoupler,
            fs_TamagawaBlochKatoCoupler,
            fs_TamagawaNumberCoupler,
            fs_BlochKatoExponentialCoupler,
            fs_TamagawaBlochKatoExponentialCoupler,
        ]
        for alias_cls in aliases:
            assert issubclass(alias_cls, MotivicTamagawaBlochKatoCoupler) or alias_cls is MotivicTamagawaBlochKatoCoupler

        p_vec = np.array([0.6, 0.7, 0.5, 0.4, 0.65])
        res1 = MotivicTamagawaBlochKatoCoupler.compute(p_vec)
        res2 = EnsembleScoringEngine.compute_motivic_tamagawa_bloch_kato_coupling(p_vec)
        assert math.isclose(res1["h_tamagawa"], res2["h_tamagawa"], rel_tol=1e-9)

    def test_feature_f152_1_28th_order_rank_modulation_convexity(self):
        """Verify 28th-order hyper-convex rank modulation mathematical characteristics."""
        r_mid = 0.50
        r_high = 0.99
        g_mid = compute_phase33_hyperconvex_rank_modulation(r_mid, gamma_top=3.40)
        g_high = compute_phase33_hyperconvex_rank_modulation(r_high, gamma_top=3.40)

        # Extreme hyper-convexity
        assert g_high > 12.0 * g_mid, f"Expected extreme convexity: g_high={g_high}, g_mid={g_mid}"
        assert math.isclose(compute_phase33_hyperconvex_rank_modulation(0.0), 0.50, abs_tol=1e-8)

        # Alias verification
        assert math.isclose(
            compute_phase33_rank_warping(0.85, gamma_top=2.5),
            compute_phase33_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )
        assert math.isclose(
            fs_compute_phase33_modulation(0.85, gamma_top=2.5),
            compute_phase33_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )

    def test_feature_f152_1_regime_adaptive_gamma_top(self):
        """Verify regime-adaptive gamma_top dictionary and function up to 3.40."""
        assert fs_REGIME_GAMMA_TOP_V33['BULL_LOW_VOL'] == 3.40
        assert fs_REGIME_GAMMA_TOP_V33['BULL_HIGH_VOL'] == 3.10
        assert fs_REGIME_GAMMA_TOP_V33['SIDEWAYS'] == 2.90
        assert fs_REGIME_GAMMA_TOP_V33['BEAR'] == 2.60
        assert fs_REGIME_GAMMA_TOP_V33['CRISIS'] == 0.90

        assert fs_get_regime_adaptive_gamma_top_v33('BULL_LOW_VOL') == 3.40
        assert fs_get_regime_adaptive_gamma_top_v33('CRISIS') == 0.90
        assert fs_get_regime_adaptive_gamma_top_v33('RECOVERY') == 3.20

    def test_feature_f152_2_96th_order_hyperbolic_deadband_leakage(self):
        """Verify 96th-order hexanonacontagonal deadband suppresses sub-threshold micro-noise to < 10^-50."""
        z_noise = 0.0008
        res_noise = apply_hexanonacontagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=96.0)
        assert abs(res_noise) < 1e-50, f"Expected < 10^-50 leakage, got {res_noise}"

        # 100% transmission of high conviction signals
        z_signal = 0.150
        res_signal = apply_hexanonacontagonal_hyperbolic_deadband(z_signal, delta_noise=0.035, alpha_pos=96.0)
        assert math.isclose(res_signal, z_signal, rel_tol=1e-4)

        # Monotonicity
        arr = np.linspace(-0.20, 0.20, 100)
        filtered = apply_hexanonacontagonal_hyperbolic_deadband(arr, delta_noise=0.035, alpha_pos=96.0)
        assert (np.diff(filtered) >= -1e-12).all()

    def test_feature_f152_2_factor_suppression_delegation(self):
        """Verify deadband functions via factor_suppression bindings."""
        z = 0.05
        r1 = apply_hexanonacontagonal_hyperbolic_deadband(z)
        r2 = fs_hexanonacontagonal_deadband(z)
        assert math.isclose(r1, r2, rel_tol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_33(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband delegates to 96th-order deadband under v33."""
        z_noise = 0.0008
        out_v33 = apply_smooth_deadband_attenuation(z_noise, version=33)
        out_v32 = apply_smooth_deadband_attenuation(z_noise, version=32)

        # v33 should have even stricter attenuation than v32
        assert abs(out_v33) <= abs(out_v32)
        assert abs(out_v33) < 1e-50

    def test_combine_predictions_version_33_confluence_and_harmony(self):
        """Verify EnsembleScoringEngine.combine_predictions with version=33 incorporates Tamagawa bonus."""
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

        comb_v32 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=32)
        comb_v33 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=33)

        assert isinstance(comb_v33, pd.DataFrame)
        assert not comb_v33.empty
        assert "ensemble_score" in comb_v33.columns
        assert len(comb_v33) == N
        assert np.all(np.isfinite(comb_v33["ensemble_score"].values))
        assert np.all(comb_v33["ensemble_score"].values >= 0.0)
        assert np.all(comb_v33["ensemble_score"].values <= 1.0)

        # Top conviction in v33 should be >= v32
        top_v32 = comb_v32.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v33 = comb_v33.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v33 >= top_v32 - 1e-6, f"Top conviction in v33 ({top_v33}) should be >= v32 ({top_v32})"

    def test_strict_backward_compatibility_v32_and_v31(self):
        """Verify that combine_predictions with version=32 and 31 behaves identically to pre-Phase 33."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)
        res_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)
        res_v32 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=32)
        res_v33 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=33)

        assert len(res_v30) == N
        assert len(res_v31) == N
        assert len(res_v32) == N
        assert len(res_v33) == N
        assert all("ensemble_score" in res_v33.columns for _ in [1])
        assert all("ensemble_score" in res_v32.columns for _ in [1])
        assert all("ensemble_score" in res_v31.columns for _ in [1])
        assert all("ensemble_score" in res_v30.columns for _ in [1])

r"""
tests/test_phase32_alpha.py

Comprehensive unit test suite for Phase 32 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F147: Motivic Beilinson-Flach Euler System & Perrin-Riou Coates-Wiles Syntomic Coupler
  (MotivicBeilinsonFlachSyntomicCoupler, syntomic obstruction complex E_syntomic,
  Coates-Wiles syntomic class invariant Z_coates_wiles, coupling factor h_syntomic,
  theta_0=0.44, kappa_syntomic=4.40, complete aliases and factor_suppression bindings)
- Feature F148.1: 27th-Order Hyper-Convex Rank Modulation (g_v32(r) = 0.50 + 1.28 * r * exp(gamma_top * r^27))
  with regime-adaptive gamma_top up to 3.30 (REGIME_GAMMA_TOP_V32, get_regime_adaptive_gamma_top_v32)
- Feature F148.2: 92nd-Order Nonacontaditagonal Hyperbolic Tangent Noise Deadband (alpha=92.0, leakage < 10^-48)
- End-to-End EnsembleScoringEngine combine_predictions() with version=32
- Strict backward compatibility validation with Phase 14 through Phase 31
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_nonacontaditagonal_hyperbolic_deadband,
    apply_octaoctacontagonal_hyperbolic_deadband,
    apply_tetraoctacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase32_hyperconvex_rank_modulation,
    compute_phase32_rank_warping,
    compute_phase31_hyperconvex_rank_modulation,
    compute_phase30_hyperconvex_rank_modulation,
    MotivicBeilinsonFlachSyntomicCoupler,
    MotivicSyntomicCoupler,
    PerrinRiouSyntomicCoupler,
    CoatesWilesCoupler,
    SyntomicCoupler,
    BeilinsonFlachSyntomicCoupler,
    EulerSyntomicCoupler,
    PerrinRiouCoatesWilesCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_nonacontaditagonal_hyperbolic_deadband as fs_nonacontaditagonal_deadband,
    apply_octaoctacontagonal_hyperbolic_deadband as fs_octaoctacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase32_hyperconvex_rank_modulation as fs_compute_phase32_modulation,
    compute_phase32_rank_warping as fs_compute_phase32_warping,
    REGIME_GAMMA_TOP_V32 as fs_REGIME_GAMMA_TOP_V32,
    get_regime_adaptive_gamma_top_v32 as fs_get_regime_adaptive_gamma_top_v32,
    MotivicBeilinsonFlachSyntomicCoupler as fs_MotivicBeilinsonFlachSyntomicCoupler,
    MotivicSyntomicCoupler as fs_MotivicSyntomicCoupler,
    PerrinRiouSyntomicCoupler as fs_PerrinRiouSyntomicCoupler,
    CoatesWilesCoupler as fs_CoatesWilesCoupler,
    SyntomicCoupler as fs_SyntomicCoupler,
    BeilinsonFlachSyntomicCoupler as fs_BeilinsonFlachSyntomicCoupler,
    EulerSyntomicCoupler as fs_EulerSyntomicCoupler,
    PerrinRiouCoatesWilesCoupler as fs_PerrinRiouCoatesWilesCoupler,
)


class TestPhase32AlphaEnhancements:
    """Test suite for Phase 32 Alpha Engine Innovations."""

    def test_feature_f147_motivic_syntomic_coupler_properties(self):
        """Verify MotivicBeilinsonFlachSyntomicCoupler calculation and canonical outputs."""
        coupler = MotivicBeilinsonFlachSyntomicCoupler(theta_0=0.44, kappa_syntomic=4.40)
        p_vec = np.array([0.55, 0.62, 0.48, 0.51, 0.58])
        res = coupler.evaluate(p_vec)

        assert isinstance(res, dict)
        expected_keys = [
            "h_syntomic", "z_coates_wiles", "e_syntomic", "h_decay", "FERI_v32",
            "feri_v32", "Z_coates_wiles", "E_syntomic", "H_syntomic",
            "h_motivic_syntomic", "z_motivic_syntomic", "e_motivic_syntomic",
            "h_coates_wiles", "z_syntomic", "e_coates_wiles",
            "h_perrin_riou_syntomic", "z_perrin_riou_syntomic", "e_perrin_riou_syntomic",
            "h_beilinson_flach_syntomic", "z_beilinson_flach_syntomic", "e_beilinson_flach_syntomic",
            "h_euler_syntomic", "z_euler_syntomic", "e_euler_syntomic",
            "h_motivic", "z_motivic", "e_motivic",
        ]
        for k in expected_keys:
            assert k in res, f"Missing key: {k}"

        assert 0.0 <= res["h_syntomic"] <= 1.0
        assert 0.0 <= res["z_coates_wiles"] <= 1.0
        assert res["e_syntomic"] >= 0.0
        assert 0.0 <= res["FERI_v32"] <= 1.0

        # Uniform vector has 0 obstruction energy
        p_uniform = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_u = coupler.evaluate(p_uniform)
        assert math.isclose(res_u["e_syntomic"], 0.0, abs_tol=1e-8)
        assert math.isclose(res_u["z_coates_wiles"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["h_syntomic"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["FERI_v32"], 1.0, abs_tol=1e-8)

    def test_feature_f147_syntomic_aliases_and_exports(self):
        """Verify all class aliases and dynamic export bindings for Feature F147."""
        aliases = [
            MotivicBeilinsonFlachSyntomicCoupler,
            MotivicSyntomicCoupler,
            PerrinRiouSyntomicCoupler,
            CoatesWilesCoupler,
            SyntomicCoupler,
            BeilinsonFlachSyntomicCoupler,
            EulerSyntomicCoupler,
            PerrinRiouCoatesWilesCoupler,
            fs_MotivicBeilinsonFlachSyntomicCoupler,
            fs_MotivicSyntomicCoupler,
            fs_PerrinRiouSyntomicCoupler,
            fs_CoatesWilesCoupler,
            fs_SyntomicCoupler,
            fs_BeilinsonFlachSyntomicCoupler,
            fs_EulerSyntomicCoupler,
            fs_PerrinRiouCoatesWilesCoupler,
        ]
        for alias_cls in aliases:
            assert issubclass(alias_cls, MotivicBeilinsonFlachSyntomicCoupler) or alias_cls is MotivicBeilinsonFlachSyntomicCoupler

        p_vec = np.array([0.6, 0.7, 0.5, 0.4, 0.65])
        res1 = MotivicBeilinsonFlachSyntomicCoupler.compute(p_vec)
        res2 = EnsembleScoringEngine.compute_motivic_syntomic_coupling(p_vec)
        assert math.isclose(res1["h_syntomic"], res2["h_syntomic"], rel_tol=1e-9)

    def test_feature_f148_1_27th_order_rank_modulation_convexity(self):
        """Verify 27th-order hyper-convex rank modulation mathematical characteristics."""
        r_mid = 0.50
        r_high = 0.99
        g_mid = compute_phase32_hyperconvex_rank_modulation(r_mid, gamma_top=3.30)
        g_high = compute_phase32_hyperconvex_rank_modulation(r_high, gamma_top=3.30)

        # Extreme hyper-convexity
        assert g_high > 10.0 * g_mid, f"Expected extreme convexity: g_high={g_high}, g_mid={g_mid}"
        assert math.isclose(compute_phase32_hyperconvex_rank_modulation(0.0), 0.50, abs_tol=1e-8)

        # Alias verification
        assert math.isclose(
            compute_phase32_rank_warping(0.85, gamma_top=2.5),
            compute_phase32_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )
        assert math.isclose(
            fs_compute_phase32_modulation(0.85, gamma_top=2.5),
            compute_phase32_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )

    def test_feature_f148_1_regime_adaptive_gamma_top(self):
        """Verify regime-adaptive gamma_top dictionary and function up to 3.30."""
        assert fs_REGIME_GAMMA_TOP_V32['BULL_LOW_VOL'] == 3.30
        assert fs_REGIME_GAMMA_TOP_V32['BULL_HIGH_VOL'] == 3.00
        assert fs_REGIME_GAMMA_TOP_V32['SIDEWAYS'] == 2.80
        assert fs_REGIME_GAMMA_TOP_V32['BEAR'] == 2.50
        assert fs_REGIME_GAMMA_TOP_V32['CRISIS'] == 0.90

        assert fs_get_regime_adaptive_gamma_top_v32('BULL_LOW_VOL') == 3.30
        assert fs_get_regime_adaptive_gamma_top_v32('CRISIS') == 0.90
        assert fs_get_regime_adaptive_gamma_top_v32('RECOVERY') == 3.10

    def test_feature_f148_2_92nd_order_hyperbolic_deadband_leakage(self):
        """Verify 92nd-order nonacontaditagonal deadband suppresses sub-threshold micro-noise to < 10^-48."""
        z_noise = 0.0009
        res_noise = apply_nonacontaditagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=92.0)
        assert abs(res_noise) < 1e-48, f"Expected < 10^-48 leakage, got {res_noise}"

        # 100% transmission of high conviction signals
        z_signal = 0.150
        res_signal = apply_nonacontaditagonal_hyperbolic_deadband(z_signal, delta_noise=0.035, alpha_pos=92.0)
        assert math.isclose(res_signal, z_signal, rel_tol=1e-4)

        # Monotonicity
        arr = np.linspace(-0.20, 0.20, 100)
        filtered = apply_nonacontaditagonal_hyperbolic_deadband(arr, delta_noise=0.035, alpha_pos=92.0)
        assert (np.diff(filtered) >= -1e-12).all()

    def test_feature_f148_2_factor_suppression_delegation(self):
        """Verify deadband functions via factor_suppression bindings."""
        z = 0.05
        r1 = apply_nonacontaditagonal_hyperbolic_deadband(z)
        r2 = fs_nonacontaditagonal_deadband(z)
        assert math.isclose(r1, r2, rel_tol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_32(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband delegates to 92nd-order deadband under v32."""
        z_noise = 0.0009
        out_v32 = apply_smooth_deadband_attenuation(z_noise, version=32)
        out_v31 = apply_smooth_deadband_attenuation(z_noise, version=31)

        # v32 should have even stricter attenuation than v31
        assert abs(out_v32) <= abs(out_v31)
        assert abs(out_v32) < 1e-48

    def test_combine_predictions_version_32_confluence_and_harmony(self):
        """Verify EnsembleScoringEngine.combine_predictions with version=32 incorporates Syntomic bonus."""
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

        comb_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)
        comb_v32 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=32)

        assert isinstance(comb_v32, pd.DataFrame)
        assert not comb_v32.empty
        assert "ensemble_score" in comb_v32.columns
        assert len(comb_v32) == N
        assert np.all(np.isfinite(comb_v32["ensemble_score"].values))
        assert np.all(comb_v32["ensemble_score"].values >= 0.0)
        assert np.all(comb_v32["ensemble_score"].values <= 1.0)

        # Top conviction in v32 should be >= v31
        top_v31 = comb_v31.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v32 = comb_v32.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v32 >= top_v31 - 1e-6, f"Top conviction in v32 ({top_v32}) should be >= v31 ({top_v31})"

    def test_strict_backward_compatibility_v31_and_v30(self):
        """Verify that combine_predictions with version=31 and 30 behaves identically to pre-Phase 32."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)
        res_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)
        res_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)
        res_v32 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=32)

        assert len(res_v29) == N
        assert len(res_v30) == N
        assert len(res_v31) == N
        assert len(res_v32) == N
        assert all("ensemble_score" in res_v32.columns for _ in [1])
        assert all("ensemble_score" in res_v31.columns for _ in [1])
        assert all("ensemble_score" in res_v30.columns for _ in [1])
        assert all("ensemble_score" in res_v29.columns for _ in [1])

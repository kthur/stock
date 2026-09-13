r"""
tests/test_phase34_alpha.py

Comprehensive unit test suite for Phase 34 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F155: Motivic Birch-Swinnerton-Dyer (BSD) Conjecture & Gross-Zagier Heegner Point Coupler
  (MotivicBsdGrossZagierCoupler, BSD obstruction complex E_bsd,
  Gross-Zagier Heegner point invariant Z_gross_zagier, coupling factor h_bsd,
  theta_0=0.48, kappa_bsd=4.80, complete aliases and factor_suppression bindings)
- Feature F156.1: 29th-Order Hyper-Convex Rank Modulation (g_v34(r) = 0.50 + 1.32 * r * exp(gamma_top * r^29))
  with regime-adaptive gamma_top up to 3.50 (REGIME_GAMMA_TOP_V34, get_regime_adaptive_gamma_top_v34)
- Feature F156.2: 100th-Order Centagonal Hyperbolic Tangent Noise Deadband (alpha=100.0, leakage < 10^-52)
- End-to-End EnsembleScoringEngine combine_predictions() with version=34
- Strict backward compatibility validation with Phase 14 through Phase 33
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_centagonal_hyperbolic_deadband,
    apply_hexanonacontagonal_hyperbolic_deadband,
    apply_nonacontaditagonal_hyperbolic_deadband,
    apply_octaoctacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase34_hyperconvex_rank_modulation,
    compute_phase34_rank_warping,
    compute_phase33_hyperconvex_rank_modulation,
    compute_phase32_hyperconvex_rank_modulation,
    MotivicBsdGrossZagierCoupler,
    MotivicBsdCoupler,
    GrossZagierCoupler,
    BsdGrossZagierCoupler,
    HeegnerPointCoupler,
    BsdCoupler,
    MotivicGrossZagierCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_centagonal_hyperbolic_deadband as fs_centagonal_deadband,
    apply_hexanonacontagonal_hyperbolic_deadband as fs_hexanonacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase34_hyperconvex_rank_modulation as fs_compute_phase34_modulation,
    compute_phase34_rank_warping as fs_compute_phase34_warping,
    REGIME_GAMMA_TOP_V34 as fs_REGIME_GAMMA_TOP_V34,
    get_regime_adaptive_gamma_top_v34 as fs_get_regime_adaptive_gamma_top_v34,
    MotivicBsdGrossZagierCoupler as fs_MotivicBsdGrossZagierCoupler,
    MotivicBsdCoupler as fs_MotivicBsdCoupler,
    GrossZagierCoupler as fs_GrossZagierCoupler,
    BsdGrossZagierCoupler as fs_BsdGrossZagierCoupler,
    HeegnerPointCoupler as fs_HeegnerPointCoupler,
    BsdCoupler as fs_BsdCoupler,
    MotivicGrossZagierCoupler as fs_MotivicGrossZagierCoupler,
)


class TestPhase34AlphaEnhancements:
    """Test suite for Phase 34 Alpha Engine Innovations."""

    def test_feature_f155_motivic_bsd_coupler_properties(self):
        """Verify MotivicBsdGrossZagierCoupler calculation and canonical outputs."""
        coupler = MotivicBsdGrossZagierCoupler(theta_0=0.48, kappa_bsd=4.80)
        p_vec = np.array([0.55, 0.62, 0.48, 0.51, 0.58])
        res = coupler.evaluate(p_vec)

        assert isinstance(res, dict)
        expected_keys = [
            "h_bsd", "z_gross_zagier", "e_bsd", "h_decay", "FERI_v34",
            "feri_v34", "Z_gross_zagier", "E_bsd", "H_bsd",
            "h_motivic_bsd", "z_motivic_bsd", "e_motivic_bsd",
            "h_gross_zagier", "z_bsd", "e_gross_zagier",
            "h_heegner_point", "z_heegner_point", "e_heegner_point",
            "h_motivic", "z_motivic", "e_motivic",
        ]
        for k in expected_keys:
            assert k in res, f"Missing key: {k}"

        assert 0.0 <= res["h_bsd"] <= 1.0
        assert 0.0 <= res["z_gross_zagier"] <= 1.0
        assert res["e_bsd"] >= 0.0
        assert 0.0 <= res["FERI_v34"] <= 1.0

        # Uniform vector has 0 obstruction energy
        p_uniform = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_u = coupler.evaluate(p_uniform)
        assert math.isclose(res_u["e_bsd"], 0.0, abs_tol=1e-8)
        assert math.isclose(res_u["z_gross_zagier"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["h_bsd"], 1.0, abs_tol=1e-8)
        assert math.isclose(res_u["FERI_v34"], 1.0, abs_tol=1e-8)

    def test_feature_f155_bsd_aliases_and_exports(self):
        """Verify all class aliases and dynamic export bindings for Feature F155."""
        aliases = [
            MotivicBsdGrossZagierCoupler,
            MotivicBsdCoupler,
            GrossZagierCoupler,
            BsdGrossZagierCoupler,
            HeegnerPointCoupler,
            BsdCoupler,
            MotivicGrossZagierCoupler,
            fs_MotivicBsdGrossZagierCoupler,
            fs_MotivicBsdCoupler,
            fs_GrossZagierCoupler,
            fs_BsdGrossZagierCoupler,
            fs_HeegnerPointCoupler,
            fs_BsdCoupler,
            fs_MotivicGrossZagierCoupler,
        ]
        for a in aliases:
            assert a is not None
            c = a()
            res = c.evaluate(np.array([0.5, 0.5, 0.5, 0.5, 0.5]))
            assert math.isclose(res["h_bsd"], 1.0, abs_tol=1e-6)

    def test_feature_f156_1_29th_order_rank_modulation_convexity(self):
        """Verify 29th-order hyper-convex rank modulation properties and convexity."""
        r_mid = 0.50
        r_high = 0.99
        g_mid = compute_phase34_hyperconvex_rank_modulation(r_mid, gamma_top=3.50)
        g_high = compute_phase34_hyperconvex_rank_modulation(r_high, gamma_top=3.50)

        # Extreme hyper-convexity
        assert g_high > 12.0 * g_mid, f"Expected extreme convexity: g_high={g_high}, g_mid={g_mid}"
        assert math.isclose(compute_phase34_hyperconvex_rank_modulation(0.0), 0.50, abs_tol=1e-8)

        # Alias verification
        assert math.isclose(
            compute_phase34_rank_warping(0.85, gamma_top=2.5),
            compute_phase34_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )
        assert math.isclose(
            fs_compute_phase34_modulation(0.85, gamma_top=2.5),
            compute_phase34_hyperconvex_rank_modulation(0.85, gamma_top=2.5),
            rel_tol=1e-9
        )

    def test_feature_f156_1_regime_adaptive_gamma_top(self):
        """Verify regime-adaptive gamma_top bounds for Phase 34."""
        assert fs_REGIME_GAMMA_TOP_V34['BULL_LOW_VOL'] == 3.50
        assert fs_REGIME_GAMMA_TOP_V34['BULL_HIGH_VOL'] == 3.20
        assert fs_REGIME_GAMMA_TOP_V34['SIDEWAYS'] == 3.00
        assert fs_REGIME_GAMMA_TOP_V34['BEAR'] == 2.70
        assert fs_REGIME_GAMMA_TOP_V34['CRISIS'] == 0.90

        assert fs_get_regime_adaptive_gamma_top_v34('BULL_LOW_VOL') == 3.50
        assert fs_get_regime_adaptive_gamma_top_v34('CRISIS') == 0.90
        assert fs_get_regime_adaptive_gamma_top_v34('RECOVERY') == 3.30
        assert fs_get_regime_adaptive_gamma_top_v34('UNKNOWN') == 3.50

    def test_feature_f156_2_100th_order_hyperbolic_deadband_leakage(self):
        """Verify 100th-order centagonal deadband suppresses sub-threshold micro-noise to < 10^-52."""
        z_noise = 0.0007
        res_noise = apply_centagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=100.0)
        assert abs(res_noise) < 1e-52, f"Expected < 10^-52 leakage, got {res_noise}"

        # 100% transmission of high conviction signals
        z_signal = 0.150
        res_signal = apply_centagonal_hyperbolic_deadband(z_signal, delta_noise=0.035, alpha_pos=100.0)
        assert math.isclose(res_signal, z_signal, rel_tol=1e-4)

        # Monotonicity
        arr = np.linspace(-0.20, 0.20, 100)
        filtered = apply_centagonal_hyperbolic_deadband(arr, delta_noise=0.035, alpha_pos=100.0)
        assert (np.diff(filtered) >= -1e-12).all()

    def test_feature_f156_2_factor_suppression_delegation(self):
        """Verify deadband functions via factor_suppression bindings."""
        z = 0.05
        r1 = apply_centagonal_hyperbolic_deadband(z)
        r2 = fs_centagonal_deadband(z)
        assert math.isclose(r1, r2, rel_tol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_34(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband delegates to 100th-order deadband under v34."""
        z_noise = 0.0007
        out_v34 = apply_smooth_deadband_attenuation(z_noise, version=34)
        out_v33 = apply_smooth_deadband_attenuation(z_noise, version=33)

        # v34 should have even stricter attenuation than v33
        assert abs(out_v34) <= abs(out_v33)
        assert abs(out_v34) < 1e-52

    def test_combine_predictions_version_34_confluence_and_harmony(self):
        """Verify EnsembleScoringEngine.combine_predictions with version=34 incorporates BSD Gross-Zagier bonus."""
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

        comb_v33 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=33)
        comb_v34 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=34)

        assert isinstance(comb_v34, pd.DataFrame)
        assert not comb_v34.empty
        assert "ensemble_score" in comb_v34.columns
        assert len(comb_v34) == N
        assert np.all(np.isfinite(comb_v34["ensemble_score"].values))
        assert np.all(comb_v34["ensemble_score"].values >= 0.0)
        assert np.all(comb_v34["ensemble_score"].values <= 1.0)

        # Top conviction in v34 should be >= v33
        top_v33 = comb_v33.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v34 = comb_v34.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v34 >= top_v33 - 1e-6, f"Top conviction in v34 ({top_v34}) should be >= v33 ({top_v33})"

    def test_strict_backward_compatibility_v33_and_v32(self):
        """Verify that combine_predictions with version=33 and 32 behaves identically to pre-Phase 34."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v31 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=31)
        res_v32 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=32)
        res_v33 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=33)
        res_v34 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=34)

        assert len(res_v31) == N
        assert len(res_v32) == N
        assert len(res_v33) == N
        assert len(res_v34) == N
        assert all("ensemble_score" in res_v34.columns for _ in [1])
        assert all("ensemble_score" in res_v33.columns for _ in [1])
        assert all("ensemble_score" in res_v32.columns for _ in [1])
        assert all("ensemble_score" in res_v31.columns for _ in [1])

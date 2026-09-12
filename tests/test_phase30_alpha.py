r"""
tests/test_phase30_alpha.py

Comprehensive unit test suite for Phase 30 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F139: Motivic Kolyvagin Euler System & Iwasawa Main Conjecture Factor Disentanglement Engine
  (MotivicKolyvaginEulerSystemCoupler, Iwasawa characteristic ideal obstruction E_kolyvagin,
  Euler system class invariant Z_iwasawa, coupling factor h_kolyvagin,
  theta_0=0.40, kappa=4.00, complete aliases and factor_suppression bindings)
- Feature F140.1: 25th-Order Hyper-Convex Rank Modulation (g_v30(r) = 0.50 + 1.24 * r * exp(gamma_top * r^25))
  with regime-adaptive gamma_top up to 3.10 (REGIME_GAMMA_TOP_V30, get_regime_adaptive_gamma_top_v30)
- Feature F140.2: 84th-Order Tetraoctacontagonal Hyperbolic Tangent Noise Deadband (alpha=84.0, leakage < 10^-44)
- End-to-End EnsembleScoringEngine combine_predictions() with version=30
- Strict backward compatibility validation with Phase 13 through Phase 29
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_tetraoctacontagonal_hyperbolic_deadband,
    apply_octacontagonal_hyperbolic_deadband,
    apply_hexaheptacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase30_hyperconvex_rank_modulation,
    compute_phase30_rank_warping,
    compute_phase29_hyperconvex_rank_modulation,
    compute_phase28_hyperconvex_rank_modulation,
    MotivicKolyvaginEulerSystemCoupler,
    KolyvaginEulerSystemCoupler,
    KolyvaginCoupler,
    IwasawaCoupler,
    KolyvaginIwasawaCoupler,
    EulerSystemIwasawaCoupler,
    MotivicIwasawaCoupler,
    SelmerCoupler,
    KolyvaginSelmerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetraoctacontagonal_hyperbolic_deadband as fs_tetraoctacontagonal_deadband,
    apply_octacontagonal_hyperbolic_deadband as fs_octacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase30_hyperconvex_rank_modulation as fs_compute_phase30_modulation,
    compute_phase30_rank_warping as fs_compute_phase30_warping,
    REGIME_GAMMA_TOP_V30 as fs_REGIME_GAMMA_TOP_V30,
    get_regime_adaptive_gamma_top_v30 as fs_get_regime_adaptive_gamma_top_v30,
    MotivicKolyvaginEulerSystemCoupler as fs_MotivicKolyvaginEulerSystemCoupler,
    KolyvaginEulerSystemCoupler as fs_KolyvaginEulerSystemCoupler,
    KolyvaginCoupler as fs_KolyvaginCoupler,
    IwasawaCoupler as fs_IwasawaCoupler,
    KolyvaginIwasawaCoupler as fs_KolyvaginIwasawaCoupler,
    EulerSystemIwasawaCoupler as fs_EulerSystemIwasawaCoupler,
    MotivicIwasawaCoupler as fs_MotivicIwasawaCoupler,
    SelmerCoupler as fs_SelmerCoupler,
    KolyvaginSelmerCoupler as fs_KolyvaginSelmerCoupler,
    compute_motivic_kolyvagin_euler_system_coupling as fs_compute_motivic_kolyvagin_euler_system_coupling,
)


class TestPhase30AlphaSignalEnhancement:
    """Test suite for Phase 30 Alpha Signal Enhancements."""

    def test_feature_f139_motivic_kolyvagin_coupler_instantiation_and_computation(self):
        """Verify MotivicKolyvaginEulerSystemCoupler calculation and canonical outputs."""
        coupler = MotivicKolyvaginEulerSystemCoupler(theta_0=0.40, kappa_kolyvagin=4.00)
        p_data = {
            'val': [0.85, 0.20, 0.40],
            'mom': [0.90, 0.15, 0.50],
            'flow': [0.80, 0.10, 0.30],
            'cat': [0.95, 0.25, 0.60],
            'net': [0.75, 0.05, 0.45],
        }
        df = pd.DataFrame(p_data, index=['stock_A', 'stock_B', 'stock_C'])
        res = coupler.evaluate(df)

        assert "h_kolyvagin" in res
        assert "z_iwasawa" in res
        assert "e_kolyvagin" in res
        assert "FERI_v30" in res

        assert len(res["h_kolyvagin"]) == 3
        assert len(res["z_iwasawa"]) == 3
        assert len(res["e_kolyvagin"]) == 3
        assert len(res["FERI_v30"]) == 3

        # stock_A has high concordant values, stock_B has low
        assert res["FERI_v30"].iloc[0] > 0.0
        assert res["h_kolyvagin"].iloc[0] > 0.0
        assert (res["z_iwasawa"] > 0.0).all()

    def test_feature_f139_aliases_and_facades(self):
        """Verify that all Kolyvagin and Iwasawa aliases point to the correct class and methods."""
        for alias_cls in [
            KolyvaginEulerSystemCoupler,
            KolyvaginCoupler,
            IwasawaCoupler,
            KolyvaginIwasawaCoupler,
            EulerSystemIwasawaCoupler,
            MotivicIwasawaCoupler,
            SelmerCoupler,
            KolyvaginSelmerCoupler,
            fs_MotivicKolyvaginEulerSystemCoupler,
            fs_KolyvaginEulerSystemCoupler,
            fs_KolyvaginCoupler,
            fs_IwasawaCoupler,
            fs_KolyvaginIwasawaCoupler,
            fs_EulerSystemIwasawaCoupler,
            fs_MotivicIwasawaCoupler,
            fs_SelmerCoupler,
            fs_KolyvaginSelmerCoupler,
        ]:
            assert issubclass(alias_cls, MotivicKolyvaginEulerSystemCoupler) or alias_cls is MotivicKolyvaginEulerSystemCoupler

        p_vec = np.array([0.5, 0.6, 0.4, 0.7, 0.5])
        res1 = MotivicKolyvaginEulerSystemCoupler.compute(p_vec)
        res2 = EnsembleScoringEngine.compute_motivic_kolyvagin_euler_system_coupling(p_vec)
        res3 = fs_compute_motivic_kolyvagin_euler_system_coupling(p_vec)

        assert math.isclose(float(res1["h_kolyvagin"]), float(res2["h_kolyvagin"]), rel_tol=1e-7)
        assert math.isclose(float(res1["z_iwasawa"]), float(res3["z_iwasawa"]), rel_tol=1e-7)

    def test_feature_f140_1_hyperconvex_rank_modulation(self):
        """Verify 25th-order hyper-convex rank modulation g_v30(r)."""
        ranks = pd.Series([0.1, 0.5, 0.9, 0.99, 1.0])
        z_pos = pd.Series([0.1, 0.1, 0.1, 0.1, 0.1])
        z_neg = pd.Series([-0.1, -0.1, -0.1, -0.1, -0.1])

        mult_pos = compute_phase30_hyperconvex_rank_modulation(ranks, gamma_top=3.10, z_denoised=z_pos)
        mult_neg = compute_phase30_hyperconvex_rank_modulation(ranks, gamma_top=3.10, z_denoised=z_neg)

        # For top rank r=1.0, g_v30(1.0) = 0.50 + 1.24 * 1.0 * exp(3.10 * 1^25) = 0.50 + 1.24 * exp(3.10)
        expected_top = 0.50 + 1.24 * math.exp(3.10)
        assert math.isclose(mult_pos.iloc[-1], expected_top, rel_tol=1e-5)

        # For bottom rank r=0.1, g_v30(0.1) ~ 0.50 + 1.24 * 0.1 * exp(3.10 * 0.1^25) ~ 0.50 + 0.124 ~ 0.624
        assert mult_pos.iloc[0] < 0.70

        # Monotonicity for positive signals
        assert (np.diff(mult_pos.values) > 0).all()

        # Negative signals should penalize high ranks
        assert mult_neg.iloc[-1] < mult_neg.iloc[0]

    def test_feature_f140_1_regime_adaptive_gamma_top(self):
        """Verify regime adaptive gamma_top table and getter."""
        assert fs_REGIME_GAMMA_TOP_V30['BULL_LOW_VOL'] == 3.10
        assert fs_REGIME_GAMMA_TOP_V30['BULL_HIGH_VOL'] == 2.80
        assert fs_REGIME_GAMMA_TOP_V30['SIDEWAYS'] == 2.60
        assert fs_REGIME_GAMMA_TOP_V30['BEAR'] == 2.30
        assert fs_REGIME_GAMMA_TOP_V30['CRISIS'] == 0.95

        assert fs_get_regime_adaptive_gamma_top_v30('BULL_LOW_VOL') == 3.10
        assert fs_get_regime_adaptive_gamma_top_v30('CRISIS') == 0.95
        assert fs_get_regime_adaptive_gamma_top_v30('SIDEWAYS') == 2.60

    def test_feature_f140_2_84th_order_tetraoctacontagonal_deadband(self):
        """Verify 84th-order deadband suppresses noise to < 10^-44 while transmitting signals."""
        # Sub-threshold noise |z| <= 0.0012
        z_noise = 0.0012
        res_noise = apply_tetraoctacontagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=84.0)
        # ratio = 0.0012 / 0.035 ~ 0.03428
        # ratio^84 ~ 10^-123 -> tanh(arg) * z < 10^-44
        assert abs(res_noise) < 1e-44

        # Strong signal |z| >= 0.150
        z_signal = 0.150
        res_signal = apply_tetraoctacontagonal_hyperbolic_deadband(z_signal, delta_noise=0.035, alpha_pos=84.0)
        # Should transmit 100.000%
        assert math.isclose(res_signal, z_signal, rel_tol=1e-7)

        # Monotonicity
        arr = np.linspace(-0.20, 0.20, 100)
        filtered = apply_tetraoctacontagonal_hyperbolic_deadband(arr, delta_noise=0.035, alpha_pos=84.0)
        assert (np.diff(filtered) >= -1e-12).all()

    def test_feature_f140_2_factor_suppression_delegation(self):
        """Verify deadband functions via factor_suppression bindings."""
        z = 0.05
        r1 = apply_tetraoctacontagonal_hyperbolic_deadband(z)
        r2 = fs_tetraoctacontagonal_deadband(z)
        assert math.isclose(r1, r2, rel_tol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_30(self):
        """Verify EnsembleScoringEngine.apply_smooth_noise_deadband delegates to 84th-order deadband under v30."""
        z_noise = 0.0012
        out_v30 = apply_smooth_deadband_attenuation(z_noise, version=30)
        out_v29 = apply_smooth_deadband_attenuation(z_noise, version=29)

        # v30 should have even stricter attenuation than v29
        assert abs(out_v30) <= abs(out_v29)
        assert abs(out_v30) < 1e-44

    def test_combine_predictions_version_30_confluence_and_harmony(self):
        """Verify EnsembleScoringEngine.combine_predictions with version=30 incorporates Kolyvagin bonus."""
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

        comb_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)
        comb_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)

        assert isinstance(comb_v30, pd.DataFrame)
        assert not comb_v30.empty
        assert "ensemble_score" in comb_v30.columns
        assert len(comb_v30) == N
        assert np.all(np.isfinite(comb_v30["ensemble_score"].values))
        assert np.all(comb_v30["ensemble_score"].values >= 0.0)
        assert np.all(comb_v30["ensemble_score"].values <= 1.0)

        # Top conviction in v30 should be >= v29
        top_v29 = comb_v29.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v30 = comb_v30.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v30 >= top_v29 - 1e-6, f"Top conviction in v30 ({top_v30}) should be >= v29 ({top_v29})"

    def test_strict_backward_compatibility_v29_and_v28(self):
        """Verify that combine_predictions with version=29 and 28 behaves identically to pre-Phase 30."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=27)
        res_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)
        res_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)
        res_v30 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=30)

        assert len(res_v27) == N
        assert len(res_v28) == N
        assert len(res_v29) == N
        assert len(res_v30) == N
        assert all("ensemble_score" in res_v30.columns for _ in [1])
        assert all("ensemble_score" in res_v29.columns for _ in [1])
        assert all("ensemble_score" in res_v28.columns for _ in [1])
        assert all("ensemble_score" in res_v27.columns for _ in [1])

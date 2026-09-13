import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centadodecagonal_hyperbolic_deadband,
    compute_phase37_hyperconvex_rank_modulation,
    compute_phase37_rank_warping,
    REGIME_GAMMA_TOP_V37,
    get_regime_adaptive_gamma_top_v37,
    apply_smooth_deadband_attenuation,
    apply_octacentagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    MotivicWilesTaylorKisinCoupler,
    MotivicWilesCoupler,
    TaylorKisinCoupler,
    WilesTaylorKisinCoupler,
    MotivicTaylorKisinCoupler,
    WilesModularityCoupler,
    KisinDeformationCoupler,
    EnsembleScoringEngine,
)


class TestPhase37AlphaEnhancements:
    """
    Test suite for Phase 37 Quantitative Alpha Signal Enhancements:
    - Feature F167: Motivic Wiles Modularity & Taylor-Kisin Patching Factor Coupler
    - Feature F168.1: 32nd-Order Hyper-Convex Rank Modulation (g_v37)
    - Feature F168.2: 112th-Order Centadodecagonal Hyperbolic Noise Deadband
    """

    def test_feature_f167_motivic_wiles_coupler_properties(self):
        coupler = MotivicWilesTaylorKisinCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.45, 0.80, 0.10],
            'mom': [0.55, 0.85, 0.20],
            'flow': [0.50, 0.75, 0.15],
            'cat': [0.60, 0.90, 0.05],
            'net': [0.40, 0.70, 0.30],
        }, index=['s1', 's2', 's3'])

        res = coupler.evaluate(p_df)
        assert "h_wiles" in res
        assert "z_kisin" in res
        assert "e_wiles" in res
        assert "FERI_v37" in res
        assert "feri_v37" in res

        h_wiles = res["h_wiles"]
        z_kisin = res["z_kisin"]
        e_wiles = res["e_wiles"]
        feri = res["FERI_v37"]

        assert isinstance(h_wiles, pd.Series)
        assert len(h_wiles) == 3
        assert np.all(h_wiles >= 1e-6)
        assert np.all(h_wiles <= 1.0)
        assert np.all(z_kisin >= 0.0)
        assert np.all(z_kisin <= 1.0)
        assert np.all(e_wiles >= 0.0)
        assert np.all(feri > 0.0)

        # 1D single stock array test
        p_vec = np.array([0.5, 0.6, 0.55, 0.7, 0.45])
        res_1d = coupler(p_vec)
        assert isinstance(res_1d["h_wiles"], float)
        assert 0.0 < res_1d["h_wiles"] <= 1.0
        assert isinstance(res_1d["z_kisin"], float)

    def test_feature_f167_wiles_aliases_and_exports(self):
        assert MotivicWilesTaylorKisinCoupler is MotivicWilesCoupler
        assert MotivicWilesTaylorKisinCoupler is TaylorKisinCoupler
        assert MotivicWilesTaylorKisinCoupler is WilesTaylorKisinCoupler
        assert MotivicWilesTaylorKisinCoupler is MotivicTaylorKisinCoupler
        assert MotivicWilesTaylorKisinCoupler is WilesModularityCoupler
        assert MotivicWilesTaylorKisinCoupler is KisinDeformationCoupler

        assert hasattr(EnsembleScoringEngine, "MotivicWilesTaylorKisinCoupler")
        assert hasattr(EnsembleScoringEngine, "compute_motivic_wiles_taylor_kisin_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_wiles_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_kisin_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_wiles_taylor_kisin_coupling")

    def test_feature_f168_1_32nd_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        # For positive alpha names
        g_v37 = compute_phase37_hyperconvex_rank_modulation(ranks, gamma_top=3.80, z_denoised=1.0)
        assert isinstance(g_v37, np.ndarray)
        assert len(g_v37) == 100

        # Strict monotonicity for r in [0, 1]
        assert np.all(np.diff(g_v37) >= 0.0)

        # Extreme convexity at right-tail
        # g_v37(0.0) should be 0.50
        assert np.isclose(g_v37[0], 0.50, atol=1e-5)
        # Near r=1.0, g_v37 should be massively boosted
        top_val = compute_phase37_hyperconvex_rank_modulation(1.0, gamma_top=3.80, z_denoised=1.0)
        expected_top = 0.50 + 1.38 * np.exp(3.80)
        assert math.isclose(top_val, expected_top, rel_tol=1e-3)

        # At r=0.50, exponent 0.5^32 is negligible (< 1e-9), so g_v37(0.5) ~ 0.50 + 1.38*0.50 = 1.19
        mid_val = compute_phase37_hyperconvex_rank_modulation(0.50, gamma_top=3.80, z_denoised=1.0)
        assert np.isclose(mid_val, 0.50 + 1.38 * 0.50, atol=1e-4)

        # Scalar and Series inputs
        s_ranks = pd.Series([0.1, 0.9, 1.0], index=['a', 'b', 'c'])
        s_res = compute_phase37_rank_warping(s_ranks, gamma_top=3.0, z_denoised=0.5)
        assert isinstance(s_res, pd.Series)
        assert s_res['c'] > s_res['b'] > s_res['a']

    def test_feature_f168_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v37('BULL_LOW_VOL') == 3.80
        assert get_regime_adaptive_gamma_top_v37('BULL_HIGH_VOL') == 3.50
        assert get_regime_adaptive_gamma_top_v37('SIDEWAYS') == 3.30
        assert get_regime_adaptive_gamma_top_v37('BEAR') == 3.00
        assert get_regime_adaptive_gamma_top_v37('CRISIS') == 0.90
        assert get_regime_adaptive_gamma_top_v37(2) == 3.80
        assert get_regime_adaptive_gamma_top_v37(0) == 3.00

    def test_feature_f168_2_112th_order_hyperbolic_deadband_leakage(self):
        # 112th-order deadband: z * tanh((|z| / 0.035)^112)
        # Near-zero noise: |z| <= 0.0004
        noise_samples = np.array([-0.0004, -0.0002, 0.0, 0.0002, 0.0004], dtype=np.float64)
        denoised = apply_centadodecagonal_hyperbolic_deadband(noise_samples, delta_noise=0.035)

        # (|z|/0.035)^112 for |z| = 0.0004 is (0.0004/0.035)^112 = (0.0114)^112 < 10^-215
        # Denoised output must be virtually zero (< 1e-58)
        assert np.all(np.abs(denoised) < 1e-58)

        # High-conviction signal (|z| >= 0.150) transmission
        signals = np.array([0.150, 0.250, 0.500], dtype=np.float64)
        denoised_sig = apply_centadodecagonal_hyperbolic_deadband(signals, delta_noise=0.035)
        assert np.allclose(denoised_sig, signals, atol=1e-12)

        # Strict monotonicity check across grid
        z_grid = np.linspace(-0.5, 0.5, 500)
        denoised_grid = apply_centadodecagonal_hyperbolic_deadband(z_grid, delta_noise=0.035)
        diffs = np.diff(denoised_grid)
        assert np.all(diffs >= -1e-15)

    def test_feature_f168_2_factor_suppression_delegation(self):
        z = np.array([-0.0002, 0.0002, 0.20])
        res = apply_smooth_deadband_attenuation(z, version=37)
        assert np.abs(res[0]) < 1e-58
        assert np.abs(res[1]) < 1e-58
        assert np.isclose(res[2], 0.20, atol=1e-6)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_37(self):
        z = np.array([-0.0003, 0.0003, 0.25])
        res = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=37)
        assert np.abs(res[0]) < 1e-58
        assert np.abs(res[1]) < 1e-58
        assert np.isclose(res[2], 0.25, atol=1e-6)

    def test_combine_predictions_version_37_confluence_and_harmony(self):
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

        comb_v36 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=36)
        comb_v37 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=37)

        assert isinstance(comb_v37, pd.DataFrame)
        assert not comb_v37.empty
        assert "ensemble_score" in comb_v37.columns
        assert len(comb_v37) == N
        assert np.all(np.isfinite(comb_v37["ensemble_score"].values))
        assert np.all(comb_v37["ensemble_score"].values >= 0.0)
        assert np.all(comb_v37["ensemble_score"].values <= 1.0)

        # Top conviction in v37 should be >= v36
        top_v36 = comb_v36.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v37 = comb_v37.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v37 >= top_v36 - 1e-6, f"Top conviction in v37 ({top_v37}) should be >= v36 ({top_v36})"

    def test_strict_backward_compatibility_v36_and_v35(self):
        z = np.array([0.0006, 0.05, 0.15])
        out_v36 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=36)
        out_v35 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=35)

        assert abs(out_v36[0]) < 1e-55
        assert abs(out_v35[0]) < 1e-50

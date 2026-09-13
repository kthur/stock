import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_octacentagonal_hyperbolic_deadband,
    compute_phase36_hyperconvex_rank_modulation,
    compute_phase36_rank_warping,
    REGIME_GAMMA_TOP_V36,
    get_regime_adaptive_gamma_top_v36,
    apply_smooth_deadband_attenuation,
    apply_tetracentagonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    MotivicSerreMazurCoupler,
    MotivicSerreEisensteinCoupler,
    SerreModularCoupler,
    MazurEisensteinCoupler,
    MotivicSerreCoupler,
    MazurEisensteinIdealCoupler,
    SerreMazurCoupler,
    EnsembleScoringEngine,
)


class TestPhase36AlphaEnhancements:
    """
    Test suite for Phase 36 Quantitative Alpha Signal Enhancements:
    - Feature F163: Motivic Serre Modular Form & Mazur Eisenstein Ideal Factor Coupler
    - Feature F164.1: 31st-Order Hyper-Convex Rank Modulation (g_v36)
    - Feature F164.2: 108th-Order Octacentagonal Hyperbolic Noise Deadband
    """

    def test_feature_f163_motivic_serre_coupler_properties(self):
        coupler = MotivicSerreMazurCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.45, 0.80, 0.10],
            'mom': [0.55, 0.85, 0.20],
            'flow': [0.50, 0.75, 0.15],
            'cat': [0.60, 0.90, 0.05],
            'net': [0.40, 0.70, 0.30],
        }, index=['s1', 's2', 's3'])

        res = coupler.evaluate(p_df)
        assert "h_serre" in res
        assert "z_mazur" in res
        assert "e_serre" in res
        assert "FERI_v36" in res
        assert "feri_v36" in res

        h_serre = res["h_serre"]
        z_mazur = res["z_mazur"]
        e_serre = res["e_serre"]
        feri = res["FERI_v36"]

        assert isinstance(h_serre, pd.Series)
        assert len(h_serre) == 3
        assert np.all(h_serre >= 1e-6)
        assert np.all(h_serre <= 1.0)
        assert np.all(z_mazur >= 0.0)
        assert np.all(z_mazur <= 1.0)
        assert np.all(e_serre >= 0.0)
        assert np.all(feri > 0.0)

        # 1D single stock array test
        p_vec = np.array([0.5, 0.6, 0.55, 0.7, 0.45])
        res_1d = coupler(p_vec)
        assert isinstance(res_1d["h_serre"], float)
        assert 0.0 < res_1d["h_serre"] <= 1.0
        assert isinstance(res_1d["z_mazur"], float)

    def test_feature_f163_serre_aliases_and_exports(self):
        assert MotivicSerreMazurCoupler is MotivicSerreEisensteinCoupler
        assert MotivicSerreMazurCoupler is SerreModularCoupler
        assert MotivicSerreMazurCoupler is MazurEisensteinCoupler
        assert MotivicSerreMazurCoupler is MotivicSerreCoupler
        assert MotivicSerreMazurCoupler is MazurEisensteinIdealCoupler
        assert MotivicSerreMazurCoupler is SerreMazurCoupler

        assert hasattr(EnsembleScoringEngine, "MotivicSerreMazurCoupler")
        assert hasattr(EnsembleScoringEngine, "compute_motivic_serre_mazur_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_serre_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_mazur_coupling")
        assert hasattr(EnsembleScoringEngine, "compute_serre_mazur_coupling")

    def test_feature_f164_1_31st_order_rank_modulation_convexity(self):
        ranks = np.linspace(0.0, 1.0, 100)
        # For positive alpha names
        g_v36 = compute_phase36_hyperconvex_rank_modulation(ranks, gamma_top=3.70, z_denoised=1.0)
        assert isinstance(g_v36, np.ndarray)
        assert len(g_v36) == 100

        # Strict monotonicity for r in [0, 1]
        assert np.all(np.diff(g_v36) >= 0.0)

        # Extreme convexity at right-tail
        # g_v36(0.0) should be 0.50
        assert np.isclose(g_v36[0], 0.50, atol=1e-5)
        # Near r=1.0, g_v36 should be massively boosted
        top_val = compute_phase36_hyperconvex_rank_modulation(1.0, gamma_top=3.70, z_denoised=1.0)
        expected_top = 0.50 + 1.36 * np.exp(3.70)
        assert math.isclose(top_val, expected_top, rel_tol=1e-3)

        # At r=0.50, exponent 0.5^31 is negligible (< 1e-9), so g_v36(0.5) ~ 0.50 + 1.36*0.50 = 1.18
        mid_val = compute_phase36_hyperconvex_rank_modulation(0.50, gamma_top=3.70, z_denoised=1.0)
        assert np.isclose(mid_val, 0.50 + 1.36 * 0.50, atol=1e-4)

        # Scalar and Series inputs
        s_ranks = pd.Series([0.1, 0.9, 1.0], index=['a', 'b', 'c'])
        s_res = compute_phase36_rank_warping(s_ranks, gamma_top=3.0, z_denoised=0.5)
        assert isinstance(s_res, pd.Series)
        assert s_res['c'] > s_res['b'] > s_res['a']

    def test_feature_f164_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v36('BULL_LOW_VOL') == 3.70
        assert get_regime_adaptive_gamma_top_v36('BULL_HIGH_VOL') == 3.40
        assert get_regime_adaptive_gamma_top_v36('SIDEWAYS') == 3.20
        assert get_regime_adaptive_gamma_top_v36('BEAR') == 2.90
        assert get_regime_adaptive_gamma_top_v36('CRISIS') == 0.95
        assert get_regime_adaptive_gamma_top_v36(2) == 3.70
        assert get_regime_adaptive_gamma_top_v36(0) == 2.90

    def test_feature_f164_2_108th_order_hyperbolic_deadband_leakage(self):
        # 108th-order deadband: z * tanh((|z| / 0.035)^108)
        # Near-zero noise: |z| <= 0.0006
        noise_samples = np.array([-0.0006, -0.0003, 0.0, 0.0003, 0.0006], dtype=np.float64)
        denoised = apply_octacentagonal_hyperbolic_deadband(noise_samples, delta_noise=0.035)

        # (|z|/0.035)^108 for |z| = 0.0006 is (0.0006/0.035)^108 = (0.01714)^108 < 10^-190
        # Denoised output must be virtually zero (< 1e-56)
        assert np.all(np.abs(denoised) < 1e-56)

        # High-conviction signal (|z| >= 0.150) transmission
        signals = np.array([0.150, 0.250, 0.500], dtype=np.float64)
        denoised_sig = apply_octacentagonal_hyperbolic_deadband(signals, delta_noise=0.035)
        assert np.allclose(denoised_sig, signals, atol=1e-12)

        # Strict monotonicity check across grid
        z_grid = np.linspace(-0.5, 0.5, 500)
        denoised_grid = apply_octacentagonal_hyperbolic_deadband(z_grid, delta_noise=0.035)
        diffs = np.diff(denoised_grid)
        assert np.all(diffs >= -1e-15)

    def test_feature_f164_2_factor_suppression_delegation(self):
        z = np.array([-0.0002, 0.0002, 0.20])
        res = apply_smooth_deadband_attenuation(z, version=36)
        assert np.abs(res[0]) < 1e-56
        assert np.abs(res[1]) < 1e-56
        assert np.isclose(res[2], 0.20, atol=1e-6)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_36(self):
        z = np.array([-0.0003, 0.0003, 0.25])
        res = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=36)
        assert np.abs(res[0]) < 1e-56
        assert np.abs(res[1]) < 1e-56
        assert np.isclose(res[2], 0.25, atol=1e-6)

    def test_combine_predictions_version_36_confluence_and_harmony(self):
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

        comb_v35 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=35)
        comb_v36 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=36)

        assert isinstance(comb_v36, pd.DataFrame)
        assert not comb_v36.empty
        assert "ensemble_score" in comb_v36.columns
        assert len(comb_v36) == N
        assert np.all(np.isfinite(comb_v36["ensemble_score"].values))
        assert np.all(comb_v36["ensemble_score"].values >= 0.0)
        assert np.all(comb_v36["ensemble_score"].values <= 1.0)

        # Top conviction in v36 should be >= v35
        top_v35 = comb_v35.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v36 = comb_v36.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v36 >= top_v35 - 1e-6, f"Top conviction in v36 ({top_v36}) should be >= v35 ({top_v35})"

    def test_strict_backward_compatibility_v35_and_v34(self):
        z = np.array([0.0006, 0.05, 0.15])
        out_v35 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=35)
        out_v34 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=34)

        assert abs(out_v35[0]) < 1e-50
        assert abs(out_v34[0]) < 1e-45

"""
test_phase12_signal_enhancement.py — Unit tests for Phase 12 Genesis Signal Enhancement (F67, F68.1, F68.2)
"""

import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    YangMillsGaugeFieldCoupler,
    apply_tetradecagonal_hyperbolic_deadband,
    compute_phase12_hyperconvex_rank_modulation,
)


class TestPhase12SignalEnhancement:
    """Test suite verifying mathematical invariants of Phase 12 Genesis Signal Enhancement components."""

    # =========================================================================
    # F68.2: 14TH-ORDER (TETRADECAGONAL) HYPERBOLIC NOISE DEADBAND TESTS
    # =========================================================================

    def test_tetradecagonal_hyperbolic_deadband_noise_leakage(self):
        """Feature F68.2: Verify tetradecagonal (alpha=14.0) deadband attenuates >99.999999% noise for |z| <= 0.010."""
        small_z = np.array([-0.010, -0.0075, -0.005, -0.002, 0.0, 0.002, 0.005, 0.0075, 0.010])
        denoised = apply_tetradecagonal_hyperbolic_deadband(small_z, delta_noise=0.045, alpha_pos=14.0)

        # Max noise leakage must be strictly below 1e-8 (theoretically ~7.67e-12)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-8, f"Expected noise leakage < 1e-8, got {max_leakage}"
        assert max_leakage < 1e-10, f"Expected sub-threshold leakage < 1e-10, got {max_leakage}"

        # Attenuation percentage must exceed 99.999999%
        non_zero_mask = small_z != 0.0
        attenuation = 1.0 - (np.abs(denoised[non_zero_mask]) / np.abs(small_z[non_zero_mask]))
        assert np.all(attenuation > 0.99999999), f"Expected attenuation > 99.999999%, got {attenuation}"

    def test_tetradecagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Feature F68.2: Verify high conviction pass-through (|z| >= 0.150) and strict monotonicity."""
        large_z = np.array([-0.35, -0.25, -0.20, -0.15, 0.15, 0.20, 0.25, 0.35])
        denoised_large = apply_tetradecagonal_hyperbolic_deadband(large_z, delta_noise=0.045, alpha_pos=14.0)
        retention = np.abs(denoised_large) / np.abs(large_z)
        assert np.all(retention > 0.999999), f"Expected high conviction retention > 99.9999%, got {retention}"
        # For |z| >= 0.15, tanh is 1.0 to float64 precision
        assert np.allclose(denoised_large, large_z, atol=1e-12)

        # Monotonicity test across fine grid [-0.35, 0.35]
        grid = np.linspace(-0.35, 0.35, 201)
        denoised_grid = apply_tetradecagonal_hyperbolic_deadband(grid, delta_noise=0.045, alpha_pos=14.0)
        diffs = np.diff(denoised_grid)
        assert np.all(diffs >= -1e-12), "Tetradecagonal deadband must be strictly monotonically non-decreasing"

        # Scalar and pandas Series support
        s_val = apply_tetradecagonal_hyperbolic_deadband(0.005, delta_noise=0.045)
        assert isinstance(s_val, (float, np.floating))
        assert abs(s_val) < 1e-8

        ser = pd.Series([0.005, 0.20], index=["A", "B"])
        ser_denoised = apply_tetradecagonal_hyperbolic_deadband(ser, delta_noise=0.045)
        assert isinstance(ser_denoised, pd.Series)
        assert ser_denoised["A"] < 1e-8
        assert np.isclose(ser_denoised["B"], 0.20, atol=1e-12)

    def test_tetradecagonal_deadband_regime_asymmetry(self):
        """Feature F68.2: Verify regime-adaptive asymmetry in bear/crisis regimes."""
        z_neg = np.array([-0.05])
        z_pos = np.array([0.05])

        # Under CRISIS regime, chi_bear = 1.40, making negative threshold wider (more suppression)
        denoised_crisis_neg = apply_tetradecagonal_hyperbolic_deadband(z_neg, delta_noise=0.045, regime="CRISIS")
        denoised_crisis_pos = apply_tetradecagonal_hyperbolic_deadband(z_pos, delta_noise=0.045, regime="CRISIS")

        # In crisis, negative score should be squashed more aggressively than positive
        assert np.abs(denoised_crisis_neg) < np.abs(denoised_crisis_pos)

    # =========================================================================
    # F67: NON-ABELIAN SO(5) YANG-MILLS GAUGE FIELD THEORY COUPLER TESTS
    # =========================================================================

    def test_yang_mills_gauge_connections_skew_symmetry(self):
        """Feature F67: Verify skew-symmetry of connections A_1, A_2 and Lie bracket in so(5)."""
        np.random.seed(42)
        N = 25
        pillars = np.random.uniform(0.2, 0.8, size=(N, 5))

        res = YangMillsGaugeFieldCoupler.compute(pillars, g=0.85, v0=1.0, lambda_higgs=1.20, kappa=1.50)

        A1 = res["connection_1"]
        A2 = res["connection_2"]
        bracket = res["lie_bracket"]
        F12 = res["curvature_tensor"]

        # 1. A_1 must be skew-symmetric: A_1^T = -A_1
        A1_T = np.transpose(A1, (0, 2, 1))
        assert np.allclose(A1, -A1_T, atol=1e-12), "Connection A_1 must be strictly skew-symmetric in so(5)"

        # 2. A_2 must be skew-symmetric: A_2^T = -A_2
        A2_T = np.transpose(A2, (0, 2, 1))
        assert np.allclose(A2, -A2_T, atol=1e-12), "Connection A_2 must be strictly skew-symmetric in so(5)"

        # 3. Lie bracket [A_1, A_2] = A_1 A_2 - A_2 A_1 must be skew-symmetric in so(5)
        bracket_T = np.transpose(bracket, (0, 2, 1))
        assert np.allclose(bracket, -bracket_T, atol=1e-12), "Lie bracket [A_1, A_2] must be strictly skew-symmetric"

        # 4. Curvature tensor F_12 must be skew-symmetric: F_12^T = -F_12
        F12_T = np.transpose(F12, (0, 2, 1))
        assert np.allclose(F12, -F12_T, atol=1e-12), "Curvature tensor F_12 must be strictly skew-symmetric"

    def test_yang_mills_action_and_higgs_potential_properties(self):
        """Feature F67: Verify non-negativity of S_YM, T_cov, V_Higgs, and minimum of V_Higgs at ||p|| = v0."""
        np.random.seed(123)
        N = 30
        pillars = np.random.uniform(0.1, 0.9, size=(N, 5))

        res = YangMillsGaugeFieldCoupler.compute(pillars, g=0.85, v0=1.0, lambda_higgs=1.20, kappa=1.50)

        S_ym = res["ym_action"]
        T_cov = res["cov_kinetic"]
        V_higgs = res["higgs_potential"]
        S_action = res["action_functional"]
        h_gauge = res["h_gauge"]
        fcpi = res["fcpi"]

        # All action densities must be non-negative
        assert np.all(S_ym >= 0.0), "Yang-Mills action density must be non-negative"
        assert np.all(T_cov >= 0.0), "Covariant kinetic energy must be non-negative"
        assert np.all(V_higgs >= 0.0), "Higgs potential must be non-negative"
        assert np.all(S_action >= 0.0), "Stochastic action functional must be non-negative"

        # Action sum invariant
        assert np.allclose(S_action, S_ym + T_cov + V_higgs, atol=1e-12)

        # Gauge regularizer must be strictly bounded in (0, 1]
        assert np.all(h_gauge > 0.0) and np.all(h_gauge <= 1.0), "h_gauge must be bounded in (0, 1]"
        # FCPI must be strictly bounded in (0, 1]
        assert np.all(fcpi > 0.0) and np.all(fcpi <= 1.0), "FCPI must be bounded in (0, 1]"

        # Higgs potential minimum: when ||p|| = 1.0, V_Higgs must be exactly 0.0
        unit_p = np.array([1.0 / np.sqrt(5.0)] * 5)
        res_unit = YangMillsGaugeFieldCoupler.compute(unit_p, v0=1.0, lambda_higgs=1.20)
        assert np.isclose(res_unit["higgs_potential"], 0.0, atol=1e-12), "Higgs potential must vanish at ||p|| = v0 = 1.0"

    def test_local_factor_collapse_sensitivity(self):
        """Feature F67: Verify that single-pillar collapse triggers high action and lower FCPI."""
        # Scenario A: Healthy diversified pillars on the unit sphere
        balanced_p = np.full((10, 5), 1.0 / np.sqrt(5.0))
        res_balanced = YangMillsGaugeFieldCoupler.compute(balanced_p, v0=1.0, kappa=1.50)

        # Scenario B: Local Factor Collapse — 1 pillar dominates weakly while 4 pillars collapse to 0.01
        collapsed_p = np.zeros((10, 5))
        collapsed_p[:, 0] = 0.15
        collapsed_p[:, 1:] = 0.01
        res_collapsed = YangMillsGaugeFieldCoupler.compute(collapsed_p, v0=1.0, kappa=1.50)

        # In factor collapse, Higgs potential heavily penalizes ||p|| far from 1.0
        assert np.mean(res_collapsed["action_functional"]) > np.mean(res_balanced["action_functional"])
        assert np.mean(res_collapsed["fcpi"]) < np.mean(res_balanced["fcpi"])
        assert np.mean(res_collapsed["h_gauge"]) < np.mean(res_balanced["h_gauge"])

    def test_yang_mills_coupler_input_formats(self):
        """Feature F67: Verify coupler handles DataFrame, Dict, 1D array, and 2D array seamlessly."""
        df = pd.DataFrame({
            "val": [0.4, 0.5],
            "mom": [0.6, 0.7],
            "flow": [0.5, 0.5],
            "cat": [0.3, 0.4],
            "net": [0.5, 0.6],
        }, index=["STOCK_A", "STOCK_B"])

        res_df = EnsembleScoringEngine.compute_non_abelian_gauge_curvature(df)
        assert isinstance(res_df["h_gauge"], pd.Series)
        assert list(res_df["h_gauge"].index) == ["STOCK_A", "STOCK_B"]
        assert np.all(res_df["h_gauge"].values > 0.0)

        # 1D single-asset array
        vec_1d = np.array([0.5, 0.4, 0.6, 0.5, 0.5])
        res_1d = EnsembleScoringEngine.compute_non_abelian_gauge_curvature(vec_1d)
        assert isinstance(res_1d["h_gauge"], (float, np.floating))
        assert 0.0 < res_1d["h_gauge"] <= 1.0

    # =========================================================================
    # F68.1: 7TH-ORDER HYPERCONVEX RANK MODULATION TESTS
    # =========================================================================

    def test_7th_order_rank_modulation_percentiles(self):
        """Feature F68.1: Verify g_v12(r) values at key percentiles for gamma_top = 1.35."""
        gamma = 1.35

        # r = 0.0 -> 0.5000
        g_0 = compute_phase12_hyperconvex_rank_modulation(0.0, gamma_top=gamma)
        assert np.isclose(g_0, 0.5000, atol=1e-4)

        # r = 0.50 -> ~0.8790
        g_50 = compute_phase12_hyperconvex_rank_modulation(0.50, gamma_top=gamma)
        expected_50 = 0.50 + 0.75 * 0.50 * np.exp(gamma * (0.50 ** 7))
        assert np.isclose(g_50, expected_50, atol=1e-4)
        assert np.isclose(g_50, 0.8790, atol=2e-3)

        # r = 0.90 (top decile) -> ~1.7874
        g_90 = compute_phase12_hyperconvex_rank_modulation(0.90, gamma_top=gamma)
        expected_90 = 0.50 + 0.75 * 0.90 * np.exp(gamma * (0.90 ** 7))
        assert np.isclose(g_90, expected_90, atol=1e-4)

        # r = 0.999 (top 0.10%) -> ~3.3630
        g_999 = compute_phase12_hyperconvex_rank_modulation(0.999, gamma_top=gamma)
        expected_999 = 0.50 + 0.75 * 0.999 * np.exp(gamma * (0.999 ** 7))
        assert np.isclose(g_999, expected_999, atol=1e-4)
        assert g_999 > 3.30, f"Expected top 0.10% alpha multiplier > 3.30, got {g_999}"

        # r = 1.000 (peak) -> ~3.3931
        g_100 = compute_phase12_hyperconvex_rank_modulation(1.00, gamma_top=gamma)
        expected_100 = 0.50 + 0.75 * 1.00 * np.exp(gamma)
        assert np.isclose(g_100, expected_100, atol=1e-4)
        assert np.isclose(g_100, 3.3931, atol=2e-3)

    def test_7th_order_rank_modulation_strict_convexity(self):
        """Feature F68.1: Verify strict convexity (positive second finite difference) on r in (0, 1]."""
        r_grid = np.linspace(0.10, 1.0, 100)
        g_vals = compute_phase12_hyperconvex_rank_modulation(r_grid, gamma_top=1.35)

        # First differences (derivative) must be strictly positive (monotonicity)
        d1 = np.diff(g_vals)
        assert np.all(d1 > 0.0), "First derivative of g_v12(r) must be strictly positive"

        # Second differences (convexity) must be positive on r > 0.1
        d2 = np.diff(d1)
        assert np.all(d2 >= -1e-8), "Second derivative of g_v12(r) must be non-negative (convex)"

    def test_regime_adaptive_gamma_top_version12(self):
        """Feature F68.1: Verify regime-adaptive gamma_top calibration under version=12."""
        engine = EnsembleScoringEngine()
        gamma_bull_low = engine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=12)
        gamma_bull_high = engine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=12)
        gamma_side_low = engine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=12)
        gamma_side_high = engine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=12)
        gamma_bear_low = engine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=12)
        gamma_bear_high = engine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=12)
        gamma_crisis = engine.get_regime_adaptive_gamma_top("CRISIS", version=12)
        gamma_def = engine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=12)

        assert gamma_bull_low == 1.35, f"Expected 1.35 for BULL_LOW_VOL v12, got {gamma_bull_low}"
        assert gamma_bull_high == 1.15, f"Expected 1.15 for BULL_HIGH_VOL v12, got {gamma_bull_high}"
        assert gamma_side_low == 0.95, f"Expected 0.95 for SIDEWAYS_LOW_VOL v12, got {gamma_side_low}"
        assert gamma_side_high == 0.70, f"Expected 0.70 for SIDEWAYS_HIGH_VOL v12, got {gamma_side_high}"
        assert gamma_bear_low == 0.55, f"Expected 0.55 for BEAR_LOW_VOL v12, got {gamma_bear_low}"
        assert gamma_bear_high == 0.35, f"Expected 0.35 for BEAR_HIGH_VOL v12, got {gamma_bear_high}"
        assert gamma_crisis == 0.20, f"Expected 0.20 for CRISIS v12, got {gamma_crisis}"
        assert gamma_def == 1.00, f"Expected 1.00 default for v12, got {gamma_def}"

        # Strict monotonicity across risk regimes
        assert (
            gamma_bull_low > gamma_bull_high > gamma_side_low > gamma_side_high
            > gamma_bear_low > gamma_bear_high > gamma_crisis
        ), "gamma_top must be strictly monotonic across descending risk regimes"

    # =========================================================================
    # FULL ENSEMBLE SCORING PIPELINE INTEGRATION TESTS (PHASE 12)
    # =========================================================================

    def test_yang_mills_quint_pillar_tensor_synergy_version12(self):
        """Feature F67: Verify quint-pillar tensor synergy incorporates Yang-Mills gauge regularizer under v12."""
        np.random.seed(42)
        idx = [f"SYM_{i:02d}" for i in range(25)]
        scores_df = pd.DataFrame(np.random.uniform(0.40, 0.90, size=(25, 37)), index=idx)

        synergy_v11 = EnsembleScoringEngine.compute_quint_pillar_tensor_synergy(scores_df, regime="BULL_LOW_VOL", version=11)
        synergy_v12 = EnsembleScoringEngine.compute_quint_pillar_tensor_synergy(scores_df, regime="BULL_LOW_VOL", version=12)

        assert len(synergy_v12) == 25
        assert np.all(np.isfinite(synergy_v12.values))
        assert np.all(synergy_v12.values >= 1.0), "Synergy multiplier must be >= 1.0"
        # In BULL_LOW_VOL v12, reg_cap is expanded to 0.300 (max multiplier <= 1.300)
        assert np.all(synergy_v12.values <= 1.3001), "Synergy multiplier must respect reg_cap <= 0.300"

    def test_combine_predictions_version12_full_pipeline(self):
        """Feature F67/F68.1/F68.2: Verify combine_predictions executes Phase 12 enhancements without error."""
        engine = EnsembleScoringEngine()
        N = 30
        df_list = []
        for i in range(N):
            df_list.append({
                "symbol": f"STOCK_{i:03d}",
                "market": "SP500",
                "regression": 0.35 + 0.02 * i,
                "surge": 0.30 + 0.02 * i,
                "vcp_ml": 0.25 + 0.02 * i,
                "mq_factor": 0.40 + 0.018 * i,
                "factor_neutralized": 0.35 + 0.02 * i,
                "sentiment": 0.50 + 0.01 * i,
                "supply_chain": 0.45 + 0.015 * i,
            })
        test_df = pd.DataFrame(df_list)

        comb_v11 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=11)
        comb_v12 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=12)

        assert "ensemble_score" in comb_v12.columns
        assert len(comb_v12) == N
        assert np.all(np.isfinite(comb_v12["ensemble_score"].values))
        assert np.all(comb_v12["ensemble_score"].values >= 0.0)
        assert np.all(comb_v12["ensemble_score"].values <= 1.0)

        # Top asset in v12 should exhibit stronger convex concentration than v11
        top_v11 = comb_v11.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v12 = comb_v12.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v12 >= top_v11 - 1e-4, f"v12 top score ({top_v12}) should be >= v11 top score ({top_v11})"

    def test_backward_compatibility_v10_v11(self):
        """Ensure versions 10 and 11 execute without regression."""
        engine = EnsembleScoringEngine()
        N = 10
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "SP500",
            "regression": 0.55,
            "surge": 0.60
        } for i in range(N)])

        res_v10 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=10)
        res_v11 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=11)
        res_v12 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=12)

        assert len(res_v10) == N
        assert len(res_v11) == N
        assert len(res_v12) == N

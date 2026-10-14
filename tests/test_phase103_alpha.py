"""
tests/test_phase103_alpha.py

Unit test suite for Phase 103 Quantitative Alpha Enhancement (Features F485, F486):
- Feature F485: Sexcentoduotrigesimal (632nd-Order) Hyperbolic Deadband
  (alpha_pos = 632.0, delta_noise = 0.035, noise suppression for |z| <= 0.0003 exact float64 0.0,
   full transmission for |z| >= 0.150, rank monotonicity non-decreasing).
- Feature F485: 137th-Order Hyper-Convex Rank Modulation
  (g_v103(r) = 0.50 + 3.98 * r * exp(gamma_top * r^137) with REGIME_GAMMA_TOP_V103,
   gamma_top <= 41.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F486: Quantum Geometric Langlands Monster Whittaker Coupler Phase 103
  (version=103, kappa_monster_whit=44.00, lambda_monster >= 1.0 - 1e-27 [27-nines],
   is_phase103=True, harmony_boost=12.35,
   218th-order chiral oper defect, 130th-order topological defect invariant,
   intermediate factor clipping |p| <= 300.0 preventing float64 overflow,
   output keys FERI_v103, feri_v103, f_out_103, FERI_v102, feri_v102, f_out_102, etc.).
- Feature F485.3: Multi-Horizon Monotonicity Regularization & PAVA Projection
  (isotonic_pava and regularize_multi_horizon_monotonicity enforcing p_1d <= p_3d <= p_5d <= p_20d,
   preserving naturally monotonic inputs bit-exact, integrated into OnDevicePredictionModel._predict_surge).
- Feature F485.3: Cross-Sectional Relative Rank Feature Generator
  (compute_cross_sectional_relative_rank_features with group-wise percentile ranking bounded in [0.05, 0.95],
   NaN preservation, and neutral 0.50 fallback for singletons).
- Full alias trees for deadband, rank modulation, gamma regimes, and coupler across modules.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentoduotrigesimal_hyperbolic_deadband,
    apply_sexcentoduotrigesimal_deadband,
    apply_hexacosiatriacontadigonal_hyperbolic_deadband,
    apply_hexacosiatriacontadigonal_deadband,
    sexcentoduotrigesimal_deadband,
    sexcentoduotrigesimal_hyperbolic_deadband,
    hexacosiatriacontadigonal_deadband,
    hexacosiatriacontadigonal_hyperbolic_deadband,
    compute_phase103_deadband,
    apply_phase103_deadband,
    phase103_deadband,
    apply_632nd_order_hyperbolic_deadband,
    apply_632nd_deadband,
    apply_632_deadband,
    apply_hyperbolic_deadband_v103,
    suppress_factor_noise_hyperbolic_v103,
    apply_sexcentoduotrigesimal_hyperbolic_deadband_v103,
    apply_sexcentoduotrigesihedral_hyperbolic_deadband,
    apply_sexcentoduotrigesimal_dihedral_hyperbolic_deadband,
    apply_sexcentoduotrigesimal_suppression,
    compute_phase103_hyperconvex_rank_modulation,
    compute_137th_order_hyperconvex_rank_modulation,
    compute_phase103_rank_warping,
    compute_phase103_rank_modulation,
    phase103_rank_modulation,
    phase103_hyperconvex_rank_modulation,
    apply_phase103_rank_modulation,
    apply_hyper_convex_rank_modulation_v103,
    apply_137th_order_hyper_convex_rank_modulation,
    REGIME_GAMMA_TOP_V103,
    get_regime_adaptive_gamma_top_v103,
    get_regime_adaptive_gamma_top_phase103,
    get_gamma_top_v103,
    regime_adaptive_gamma_top_v103,
    get_phase103_gamma_top,
    phase103_gamma_top,
    get_gamma_top_phase103,
    adaptive_gamma_top_v103,
    Phase103FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)

from trading_system.src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase103Coupler,
    Phase103WhittakerDrinfeldCoupler,
    Phase103BorcherdsMoonshineCoupler,
    Phase103MonsterWhittakerCoupler,
    compute_phase103_coupling,
    compute_quantum_geometric_langlands_monster_whittaker_coupler_phase103,
    FERI_v103,
    feri_v103,
    f_out_103,
)

from trading_system.src.ai.prediction_model import (
    OnDevicePredictionModel,
    isotonic_pava,
    regularize_multi_horizon_monotonicity,
    compute_cross_sectional_relative_rank_features,
)


class TestPhase103AlphaEnhancements:
    """Test suite for Phase 103 Alpha Signal Processing, Langlands Monster Coupler, and Prediction Regularizers."""

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F485: 632nd-Order Deadband Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f485_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to exact float64 0.0
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_sexcentoduotrigesimal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert val == 0.0, f"Expected exact 0.0 for micro noise, got {val}"

        # Scalar test
        assert apply_sexcentoduotrigesimal_hyperbolic_deadband(0.0002) == 0.0
        assert apply_sexcentoduotrigesimal_hyperbolic_deadband(-0.0002) == 0.0

        # Conviction signal |z| >= 0.150 preserved with full transmission (>99.999%)
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_sexcentoduotrigesimal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Negative conviction signals preserve negative sign
        neg_conv = np.array([-0.150, -0.300, -0.500])
        denoised_neg = apply_sexcentoduotrigesimal_hyperbolic_deadband(neg_conv)
        for orig, d in zip(neg_conv, denoised_neg):
            assert d < 0.0
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test: strictly monotonic non-decreasing
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_sexcentoduotrigesimal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f485_deadband_aliases(self):
        aliases = [
            apply_sexcentoduotrigesimal_hyperbolic_deadband,
            apply_sexcentoduotrigesimal_deadband,
            apply_hexacosiatriacontadigonal_hyperbolic_deadband,
            apply_hexacosiatriacontadigonal_deadband,
            sexcentoduotrigesimal_deadband,
            sexcentoduotrigesimal_hyperbolic_deadband,
            hexacosiatriacontadigonal_deadband,
            hexacosiatriacontadigonal_hyperbolic_deadband,
            compute_phase103_deadband,
            apply_phase103_deadband,
            phase103_deadband,
            apply_632nd_order_hyperbolic_deadband,
            apply_632nd_deadband,
            apply_632_deadband,
            apply_hyperbolic_deadband_v103,
            suppress_factor_noise_hyperbolic_v103,
            apply_sexcentoduotrigesimal_hyperbolic_deadband_v103,
            apply_sexcentoduotrigesihedral_hyperbolic_deadband,
            apply_sexcentoduotrigesimal_dihedral_hyperbolic_deadband,
            apply_sexcentoduotrigesimal_suppression,
        ]
        assert len(aliases) == 20
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase103FactorSuppressionEngine is not None
        assert Phase103FactorSuppressionEngine is RegimeFactorSuppressionEngine

    def test_feature_f485_ensemble_engine_deadband_dispatch(self):
        # Verify deadband dispatch for version=103 in EnsembleScoringEngine
        res_deadband = EnsembleScoringEngine.apply_smooth_noise_deadband(0.0001, version=103)
        assert res_deadband == 0.0

        # High conviction transmission
        res_conv = EnsembleScoringEngine.apply_smooth_noise_deadband(0.25, version=103)
        assert math.isclose(res_conv, 0.25, rel_tol=1e-3)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F485: 137th-Order Rank Modulation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f485_rank_modulation(self):
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase103_hyperconvex_rank_modulation(ranks, gamma_top=41.00)
        assert len(modulated) == len(ranks)
        # Monotonicity test
        assert np.all(np.diff(modulated) >= -1e-12)
        # Top-decile exponential boost: g(1.0) must exceed 1e7
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase103_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank
        assert math.isclose(mod_neg[0], 1.35, abs_tol=1e-5)   # r = 0.0
        assert math.isclose(mod_neg[-1], 0.35, abs_tol=1e-5)  # r = 1.0

    def test_feature_f485_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V103
        assert REGIME_GAMMA_TOP_V103["BULL_LOW_VOL"] == 41.00
        assert REGIME_GAMMA_TOP_V103["BULL_HIGH_VOL"] == 35.40
        assert REGIME_GAMMA_TOP_V103["SIDEWAYS"] == 27.90
        assert REGIME_GAMMA_TOP_V103["SIDEWAYS_LOW_VOL"] == 27.90
        assert REGIME_GAMMA_TOP_V103["SIDEWAYS_HIGH_VOL"] == 21.20
        assert REGIME_GAMMA_TOP_V103["BEAR"] == 14.80
        assert REGIME_GAMMA_TOP_V103["BEAR_LOW_VOL"] == 14.80
        assert REGIME_GAMMA_TOP_V103["BEAR_HIGH_VOL"] == 8.20
        assert REGIME_GAMMA_TOP_V103["CRISIS"] == 2.35
        assert REGIME_GAMMA_TOP_V103["PANIC"] == 2.35
        assert REGIME_GAMMA_TOP_V103["RECOVERY"] == 35.40

        gamma_bull = get_regime_adaptive_gamma_top_v103("BULL_LOW_VOL")
        assert gamma_bull == 41.00
        gamma_crisis = get_regime_adaptive_gamma_top_v103("CRISIS")
        assert gamma_crisis == 2.35

    def test_feature_f485_rank_modulation_aliases(self):
        aliases = [
            compute_phase103_hyperconvex_rank_modulation,
            compute_137th_order_hyperconvex_rank_modulation,
            compute_phase103_rank_warping,
            compute_phase103_rank_modulation,
            phase103_rank_modulation,
            phase103_hyperconvex_rank_modulation,
            apply_phase103_rank_modulation,
            apply_hyper_convex_rank_modulation_v103,
            apply_137th_order_hyper_convex_rank_modulation,
        ]
        assert len(aliases) == 9
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=27.90)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=27.90)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        gamma_aliases = [
            get_regime_adaptive_gamma_top_v103,
            get_regime_adaptive_gamma_top_phase103,
            get_gamma_top_v103,
            regime_adaptive_gamma_top_v103,
            get_phase103_gamma_top,
            phase103_gamma_top,
            get_gamma_top_phase103,
            adaptive_gamma_top_v103,
        ]
        assert len(gamma_aliases) == 8
        base_g = gamma_aliases[0]("BULL_LOW_VOL")
        for g_fn in gamma_aliases[1:]:
            assert g_fn("BULL_LOW_VOL") == base_g

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F486: Quantum Geometric Langlands Monster Whittaker Coupler
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f486_coupler_properties_v103(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version >= 103
        assert getattr(coupler, "is_phase103", False) is True
        assert getattr(coupler, "is_phase102", False) is True
        assert getattr(coupler, "is_phase101", False) is True
        assert getattr(coupler, "is_phase100", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 44.00, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.999999999999999999999999999  # 27-nines
        assert math.isclose(coupler.harmony_boost, 12.35, abs_tol=1e-5)

        # Forward coupling test
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v103" in res or "feri_v103" in res or "f_out_103" in res
        assert "FERI_v102" in res or "feri_v102" in res or "f_out_102" in res

    def test_feature_f486_coupler_aliases(self):
        assert Phase103Coupler is not None
        assert Phase103WhittakerDrinfeldCoupler is not None
        assert Phase103BorcherdsMoonshineCoupler is not None
        assert Phase103MonsterWhittakerCoupler is not None
        coupler = Phase103Coupler()
        assert coupler.version >= 103
        assert coupler.is_phase103 is True

        df = pd.DataFrame({
            "p1": [0.10, 0.20],
            "p2": [0.12, 0.18],
            "p3": [0.11, 0.22],
            "p4": [0.09, 0.19]
        })
        res1 = compute_phase103_coupling(df)
        res2 = compute_quantum_geometric_langlands_monster_whittaker_coupler_phase103(df)
        assert isinstance(res1, dict)
        assert isinstance(res2, dict)
        assert "FERI_v103" in res1
        assert "FERI_v103" in res2

    def test_feature_f486_factor_clipping_overflow_protection(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        # Extreme factor magnitudes that would normally overflow p^130 or (diff)^218
        df_extreme = pd.DataFrame({
            "p1": [500.0, -500.0],
            "p2": [400.0, -400.0],
            "p3": [350.0, -350.0],
            "p4": [300.0, -300.0],
            "p5": [0.0, 0.0]
        })
        res = coupler.couple_signals(df_extreme)
        assert isinstance(res, dict)
        f_val = res.get("FERI_v103", res.get("f_out_103"))
        assert f_val is not None
        if isinstance(f_val, pd.Series):
            assert np.all(np.isfinite(f_val.values))
        else:
            assert np.all(np.isfinite(f_val))

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F485.3: Multi-Horizon Monotonicity Regularization Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f485_3_isotonic_pava_properties(self):
        # 1. Already non-decreasing array remains bit-exact identical
        mono_arr = np.array([0.05, 0.12, 0.18, 0.35], dtype=np.float64)
        pava_res = isotonic_pava(mono_arr)
        np.testing.assert_allclose(mono_arr, pava_res, atol=1e-12)

        # 2. Inverted array projected to non-decreasing sequence
        inverted_arr = np.array([0.30, 0.20, 0.25, 0.15], dtype=np.float64)
        reg_res = isotonic_pava(inverted_arr)
        assert np.all(np.diff(reg_res) >= -1e-12)
        # Check boundary bounds
        assert reg_res[0] >= 0.15 - 1e-12
        assert reg_res[-1] <= 0.30 + 1e-12

        # 3. Single element and empty arrays
        np.testing.assert_allclose(isotonic_pava(np.array([0.42])), np.array([0.42]))
        assert len(isotonic_pava(np.array([]))) == 0

    def test_feature_f485_3_regularize_multi_horizon_monotonicity(self):
        df = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "surge_1d": [0.35, 0.05, 0.40],
            "surge_3d": [0.20, 0.10, 0.25],
            "surge_5d": [0.25, 0.15, 0.30],
            "surge_20d": [0.15, 0.30, 0.20],
        })

        out_df = regularize_multi_horizon_monotonicity(df, horizons=[1, 3, 5, 20])

        for idx in range(len(out_df)):
            p_1d = out_df.loc[idx, "surge_1d"]
            p_3d = out_df.loc[idx, "surge_3d"]
            p_5d = out_df.loc[idx, "surge_5d"]
            p_20d = out_df.loc[idx, "surge_20d"]

            assert p_1d <= p_3d + 1e-9
            assert p_3d <= p_5d + 1e-9
            assert p_5d <= p_20d + 1e-9
            assert 0.0 <= p_1d <= 1.0
            assert 0.0 <= p_20d <= 1.0

        # Empty and missing columns tests
        empty_df = pd.DataFrame()
        assert regularize_multi_horizon_monotonicity(empty_df).empty
        df_no_cols = pd.DataFrame({"other": [1, 2, 3]})
        assert "surge_1d" not in regularize_multi_horizon_monotonicity(df_no_cols).columns

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F485.3: Cross-Sectional Relative Rank Features Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f485_3_cross_sectional_relative_rank(self):
        df = pd.DataFrame({
            "symbol": ["A", "B", "C", "D", "E"],
            "market": ["SP500", "SP500", "SP500", "KOSPI", "KOSPI"],
            "ret_5d": [0.01, 0.05, 0.10, -0.02, 0.08],
            "vcp_score": [10.0, np.nan, 30.0, 50.0, 60.0],
        })

        rank_df = compute_cross_sectional_relative_rank_features(
            df,
            feature_cols=["ret_5d", "vcp_score"],
            group_cols=["market"],
            clip_range=(0.05, 0.95),
        )

        assert "ret_5d_rel_rank" in rank_df.columns
        assert "vcp_score_rel_rank" in rank_df.columns

        # NaN preservation check
        assert pd.isna(rank_df.loc[1, "vcp_score_rel_rank"])
        assert not pd.isna(rank_df.loc[0, "vcp_score_rel_rank"])

        # Range bounds [0.05, 0.95]
        for col in ["ret_5d_rel_rank", "vcp_score_rel_rank"]:
            valid = rank_df[col].dropna()
            assert (valid >= 0.05).all()
            assert (valid <= 0.95).all()

        # Group-wise ordering check for SP500 ret_5d (symbols A < B < C)
        sp500_ranks = rank_df[rank_df["market"] == "SP500"]["ret_5d_rel_rank"].values
        assert sp500_ranks[0] < sp500_ranks[1] < sp500_ranks[2]

    def test_feature_f485_3_singleton_group_neutral_fallback(self):
        # Singleton group (N=1) must fall back to neutral 0.50
        df_singleton = pd.DataFrame({
            "symbol": ["ONLY_ONE"],
            "market": ["RUSSELL2000"],
            "ret_20d": [0.15],
        })

        rank_df = compute_cross_sectional_relative_rank_features(
            df_singleton,
            feature_cols=["ret_20d"],
            group_cols=["market"],
        )

        assert math.isclose(rank_df.loc[0, "ret_20d_rel_rank"], 0.50, abs_tol=1e-5)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F486: Combine Predictions Phase 103 Integration
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f486_combine_predictions_v103_integration(self):
        engine = EnsembleScoringEngine()
        reg_df = pd.DataFrame({
            "symbol": [f"SYM_{i}" for i in range(10)],
            "predicted_return": [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, -1.0, -2.0, 0.5, 2.5],
            "market": ["SP500"] * 10
        })
        res_df = engine.combine_predictions(reg_df=reg_df, version=103)
        assert not res_df.empty
        assert "ensemble_expected_return" in res_df.columns
        assert len(res_df) == 10

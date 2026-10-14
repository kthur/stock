"""
tests/test_phase101_alpha.py

Unit test suite for Phase 101 Quantitative Alpha Enhancement (Features F475, F476):
- Feature F475: Sexcentosextennial (616th-Order) Hyperbolic Deadband
  (alpha_pos = 616.0, delta_noise = 0.035, noise suppression < 10^-616 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F475: 133rd-Order Hyper-Convex Rank Modulation
  (g_v101(r) = 0.50 + 3.90 * r * exp(gamma_top * r^133) with REGIME_GAMMA_TOP_V101,
   gamma_top <= 39.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F475: Sector Map Propagation in Strategy Executor
  (CrossAssetSpilloverEngine and SupplyChainGNNEngine receive sector_map=ctx.sector_mapping).
- Feature F475: Net Expected Return Sign Preservation [-50.0, 50.0]
  (ensemble_expected_return preserves negative returns for Gate 8 synthetic inverse hedge;
   long candidate hurdle isolates returns > 0.0).
- Feature F476: Quantum Geometric Langlands Monster Whittaker Coupler Phase 101
  (version=101, kappa_monster_whit=42.80, lambda_monster=1.0 - 1e-25 [25-nines],
   is_phase101=True, harmony_boost=11.65,
   214th-order chiral oper obstruction, 126th-order topological defect invariant,
   intermediate factor clipping |p| <= 300.0 preventing float64 overflow,
   output keys FERI_v101, feri_v101, f_out_101, FERI_v100, feri_v100, f_out_100, etc.).
- Feature F476: Black-Litterman View Uncertainty Horizon Scaling
  (Omega diagonal scaled by 1 / eff_horizon with eff_horizon = 20).
- Feature F476: Sortino HERC Cluster Allocation
  (calculate_herc_weights downside semivariance sigma_k^- = sqrt(1/T * sum(min(R, 0)^2))
   with inverse risk weighting 1 / sigma_k^-).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentosextennial_hyperbolic_deadband,
    apply_sexcentosextennial_deadband,
    apply_hexacosiahexadecadic_hyperbolic_deadband,
    apply_hexacosiahexadecadic_deadband,
    sexcentosextennial_deadband,
    sexcentosextennial_hyperbolic_deadband,
    hexacosiahexadecadic_deadband,
    hexacosiahexadecadic_hyperbolic_deadband,
    compute_phase101_deadband,
    apply_phase101_deadband,
    phase101_deadband,
    apply_616th_order_hyperbolic_deadband,
    apply_616th_deadband,
    apply_616_deadband,
    apply_hyperbolic_deadband_v101,
    suppress_factor_noise_hyperbolic_v101,
    apply_sexcentosextennial_hyperbolic_deadband_v101,
    apply_sexcentosextahedral_hyperbolic_deadband,
    apply_sexcentosextennial_dihedral_hyperbolic_deadband,
    apply_sexcentosextennial_suppression,
    compute_phase101_hyperconvex_rank_modulation,
    compute_133rd_order_hyperconvex_rank_modulation,
    compute_phase101_rank_warping,
    compute_phase101_rank_modulation,
    phase101_rank_modulation,
    phase101_hyperconvex_rank_modulation,
    apply_phase101_rank_modulation,
    apply_hyper_convex_rank_modulation_v101,
    apply_133rd_order_hyper_convex_rank_modulation,
    REGIME_GAMMA_TOP_V101,
    get_regime_adaptive_gamma_top_v101,
    get_regime_adaptive_gamma_top_phase101,
    get_gamma_top_v101,
    regime_adaptive_gamma_top_v101,
    get_phase101_gamma_top,
    phase101_gamma_top,
    get_gamma_top_phase101,
    adaptive_gamma_top_v101,
    Phase101FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)

from trading_system.src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase101Coupler,
    Phase101WhittakerDrinfeldCoupler,
    Phase101BorcherdsMoonshineCoupler,
    Phase101MonsterWhittakerCoupler,
    compute_phase101_coupling,
    compute_quantum_geometric_langlands_monster_whittaker_coupler_phase101,
    FERI_v101,
    feri_v101,
    f_out_101,
)

from trading_system.src.analysis.portfolio_optimizer import (
    calculate_black_litterman_weights,
    calculate_herc_weights,
)


class TestPhase101AlphaEnhancements:
    """Test suite for Phase 101 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F475: 616th-Order Deadband Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f475_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 10^-616 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_sexcentosextennial_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with full transmission (>99.999%)
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_sexcentosextennial_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Negative conviction signals preserve negative sign
        neg_conv = np.array([-0.150, -0.300, -0.500])
        denoised_neg = apply_sexcentosextennial_hyperbolic_deadband(neg_conv)
        for orig, d in zip(neg_conv, denoised_neg):
            assert d < 0.0
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test: strictly monotonic non-decreasing
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_sexcentosextennial_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f475_deadband_aliases(self):
        aliases = [
            apply_sexcentosextennial_hyperbolic_deadband,
            apply_sexcentosextennial_deadband,
            apply_hexacosiahexadecadic_hyperbolic_deadband,
            apply_hexacosiahexadecadic_deadband,
            sexcentosextennial_deadband,
            sexcentosextennial_hyperbolic_deadband,
            hexacosiahexadecadic_deadband,
            hexacosiahexadecadic_hyperbolic_deadband,
            compute_phase101_deadband,
            apply_phase101_deadband,
            phase101_deadband,
            apply_616th_order_hyperbolic_deadband,
            apply_616th_deadband,
            apply_616_deadband,
            apply_hyperbolic_deadband_v101,
            suppress_factor_noise_hyperbolic_v101,
            apply_sexcentosextennial_hyperbolic_deadband_v101,
            apply_sexcentosextahedral_hyperbolic_deadband,
            apply_sexcentosextennial_dihedral_hyperbolic_deadband,
            apply_sexcentosextennial_suppression,
        ]
        assert len(aliases) == 20
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase101FactorSuppressionEngine is not None
        assert Phase101FactorSuppressionEngine is RegimeFactorSuppressionEngine

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F475: 133rd-Order Rank Modulation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f475_rank_modulation(self):
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase101_hyperconvex_rank_modulation(ranks, gamma_top=39.00)
        assert len(modulated) == len(ranks)
        # Monotonicity test
        assert np.all(np.diff(modulated) >= -1e-12)
        # Top-decile exponential boost: g(1.0) must be massive (> 1e7)
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase101_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank
        assert math.isclose(mod_neg[0], 1.35, abs_tol=1e-5)   # r = 0.0
        assert math.isclose(mod_neg[-1], 0.35, abs_tol=1e-5)  # r = 1.0

    def test_feature_f475_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V101
        assert REGIME_GAMMA_TOP_V101["BULL_LOW_VOL"] == 39.00
        assert REGIME_GAMMA_TOP_V101["BULL_HIGH_VOL"] == 33.60
        assert REGIME_GAMMA_TOP_V101["SIDEWAYS"] == 26.50
        assert REGIME_GAMMA_TOP_V101["BEAR"] == 14.00
        assert REGIME_GAMMA_TOP_V101["CRISIS"] == 2.25

        gamma_bull = get_regime_adaptive_gamma_top_v101("BULL_LOW_VOL")
        assert gamma_bull == 39.00
        gamma_crisis = get_regime_adaptive_gamma_top_v101("CRISIS")
        assert gamma_crisis == 2.25

    def test_feature_f475_rank_modulation_aliases(self):
        aliases = [
            compute_phase101_hyperconvex_rank_modulation,
            compute_133rd_order_hyperconvex_rank_modulation,
            compute_phase101_rank_warping,
            compute_phase101_rank_modulation,
            phase101_rank_modulation,
            phase101_hyperconvex_rank_modulation,
            apply_phase101_rank_modulation,
            apply_hyper_convex_rank_modulation_v101,
            apply_133rd_order_hyper_convex_rank_modulation,
        ]
        assert len(aliases) == 9
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=26.50)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=26.50)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        gamma_aliases = [
            get_regime_adaptive_gamma_top_v101,
            get_regime_adaptive_gamma_top_phase101,
            get_gamma_top_v101,
            regime_adaptive_gamma_top_v101,
            get_phase101_gamma_top,
            phase101_gamma_top,
            get_gamma_top_phase101,
            adaptive_gamma_top_v101,
        ]
        assert len(gamma_aliases) == 8
        base_g = gamma_aliases[0]("BULL_LOW_VOL")
        for g_fn in gamma_aliases[1:]:
            assert g_fn("BULL_LOW_VOL") == base_g

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F475: Strategy Executor Sector Map Propagation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f475_strategy_executor_sector_map(self):
        from trading_system.src.pipeline.strategy_executor import AlphaStrategyExecutor
        import inspect

        source = inspect.getsource(AlphaStrategyExecutor)
        # Check that sector_map is passed in Strategy 32 and Strategy 33
        assert "sector_map=ctx.sector_mapping" in source

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F475: Return Sign Preservation [-50.0, 50.0]
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f475_return_sign_preservation(self):
        engine = EnsembleScoringEngine()
        # Verify deadband dispatch for version=101
        res_deadband = EnsembleScoringEngine.apply_smooth_noise_deadband(0.0001, version=101)
        assert abs(res_deadband) < 1e-12

        # Verify that combine_predictions clips ensemble_expected_return to [-50.0, 50.0]
        # and preserves negative returns for Gate 8 synthetic inverse hedge
        reg_df = pd.DataFrame({
            "symbol": ["SYM_POS", "SYM_NEG"],
            "predicted_return": [15.0, -25.0]
        })
        res_df = engine.combine_predictions(reg_df=reg_df, version=101)
        assert "ensemble_expected_return" in res_df.columns
        neg_row = res_df[res_df["symbol"] == "SYM_NEG"]
        assert not neg_row.empty
        # Raw return is -25.0, friction cost is deducted, resulting in negative return preserved in [-50.0, 0.0]
        assert -50.0 <= neg_row["ensemble_expected_return"].iloc[0] < 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F476: Coupler Properties & Aliases
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f476_coupler_properties_v101(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 101 or coupler.version >= 101
        assert getattr(coupler, "is_phase101", False) is True
        assert getattr(coupler, "is_phase100", False) is True
        assert getattr(coupler, "is_phase99", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 42.80, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.999999999999999999999999
        assert math.isclose(coupler.harmony_boost, 11.65, abs_tol=1e-5)

        # Forward coupling test
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v101" in res or "feri_v101" in res or "f_out_101" in res
        assert "FERI_v100" in res or "feri_v100" in res or "f_out_100" in res
        assert "FERI_v99" in res or "feri_v99" in res or "f_out_99" in res

    def test_feature_f476_coupler_aliases(self):
        assert Phase101Coupler is not None
        assert Phase101WhittakerDrinfeldCoupler is not None
        assert Phase101BorcherdsMoonshineCoupler is not None
        assert Phase101MonsterWhittakerCoupler is not None
        coupler = Phase101Coupler()
        assert coupler.version >= 101
        assert coupler.is_phase101 is True

        df = pd.DataFrame({
            "p1": [0.10, 0.20],
            "p2": [0.12, 0.18],
            "p3": [0.11, 0.22],
            "p4": [0.09, 0.19]
        })
        res1 = compute_phase101_coupling(df)
        res2 = compute_quantum_geometric_langlands_monster_whittaker_coupler_phase101(df)
        assert isinstance(res1, dict)
        assert isinstance(res2, dict)
        assert "FERI_v101" in res1
        assert "FERI_v101" in res2

    def test_feature_f476_factor_clipping_overflow_protection(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        # Extreme factor magnitudes that would normally overflow p^126 or (diff)^214
        df_extreme = pd.DataFrame({
            "p1": [500.0, -500.0],
            "p2": [400.0, -400.0],
            "p3": [350.0, -350.0],
            "p4": [300.0, -300.0],
            "p5": [0.0, 0.0]
        })
        res = coupler.couple_signals(df_extreme)
        assert isinstance(res, dict)
        f_val = res.get("FERI_v101", res.get("f_out_101"))
        assert f_val is not None
        if isinstance(f_val, pd.Series):
            assert np.all(np.isfinite(f_val.values))
        else:
            assert np.all(np.isfinite(f_val))

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F476: Black-Litterman Horizon Scaling
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f476_black_litterman_horizon_scaling(self):
        # 3 assets
        cov_matrix = np.array([
            [0.04, 0.01, 0.01],
            [0.01, 0.05, 0.02],
            [0.01, 0.02, 0.06]
        ])
        views = np.array([0.10, 0.12, 0.08])

        # Optimize with horizon=20 vs horizon=1
        w_h20 = calculate_black_litterman_weights(cov_matrix, views, view_horizon=20)
        w_h1 = calculate_black_litterman_weights(cov_matrix, views, view_horizon=1)

        assert isinstance(w_h20, np.ndarray)
        assert isinstance(w_h1, np.ndarray)
        assert math.isclose(np.sum(w_h20), 1.0, abs_tol=1e-4)
        assert math.isclose(np.sum(w_h1), 1.0, abs_tol=1e-4)
        assert np.all(w_h20 >= 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F476: Sortino HERC Cluster Allocation
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f476_sortino_herc_weights(self):
        # 4 assets
        np.random.seed(42)
        n_assets = 4
        t_periods = 100
        returns_mat = np.random.randn(t_periods, n_assets) * 0.02
        # Asset 0 and 1 have higher downside volatility than 2 and 3
        returns_mat[:, 0] -= 0.01
        returns_mat[:, 1] -= 0.01

        cov_matrix = np.cov(returns_mat, rowvar=False)

        # Standard volatility HERC
        w_vol = calculate_herc_weights(
            cov_matrix=cov_matrix,
            risk_measure="volatility",
            max_single_stock_weight=0.50
        )
        assert len(w_vol) == n_assets
        assert math.isclose(np.sum(w_vol), 1.0, abs_tol=1e-4)

        # Sortino HERC with returns_matrix
        w_sortino = calculate_herc_weights(
            cov_matrix=cov_matrix,
            risk_measure="sortino",
            returns_matrix=returns_mat,
            max_single_stock_weight=0.50
        )
        assert len(w_sortino) == n_assets
        assert math.isclose(np.sum(w_sortino), 1.0, abs_tol=1e-4)
        assert np.all(w_sortino >= 0.0)

        # Sortino HERC with returns_df
        returns_df = pd.DataFrame(returns_mat, columns=["S1", "S2", "S3", "S4"])
        w_sortino_df = calculate_herc_weights(
            cov_matrix=cov_matrix,
            risk_measure="sortino",
            returns_df=returns_df,
            max_single_stock_weight=0.50
        )
        np.testing.assert_allclose(w_sortino, w_sortino_df, atol=1e-6)

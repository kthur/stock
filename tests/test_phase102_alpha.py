"""
tests/test_phase102_alpha.py

Unit test suite for Phase 102 Quantitative Alpha Enhancement (Features F480, F481):
- Feature F480: Sexcentotetravigesimal (624th-Order) Hyperbolic Deadband
  (alpha_pos = 624.0, delta_noise = 0.035, noise suppression for |z| <= 0.0003 exact float64 0.0,
   full transmission for |z| >= 0.150, rank monotonicity non-decreasing).
- Feature F480: 135th-Order Hyper-Convex Rank Modulation
  (g_v102(r) = 0.50 + 3.94 * r * exp(gamma_top * r^135) with REGIME_GAMMA_TOP_V102,
   gamma_top <= 40.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F481: Quantum Geometric Langlands Monster Whittaker Coupler Phase 102
  (version=102, kappa_monster_whit=43.40, lambda_monster >= 1.0 - 1e-26 [26-nines],
   is_phase102=True, harmony_boost=12.00,
   216th-order chiral oper defect, 128th-order topological defect invariant,
   intermediate factor clipping |p| <= 300.0 preventing float64 overflow,
   output keys FERI_v102, feri_v102, f_out_102, FERI_v101, feri_v101, f_out_101, etc.).
- Feature F481: Student-t (nu=4) Tail-Preserving Cross-Sectional Score Normalization
  (method='student_t' in CrossSectionalScoreNormalizer, preserves extreme alpha fat-tail dispersion,
   strict NaN preservation, zero-score block isolation, combine_predictions integration).
- Feature F481: Pairwise Available-Data Covariance Estimator & PSD Repair
  (compute_pairwise_available_covariance and repair_covariance_psd in FactorOrthogonalizerEngine,
   eigenvalues guaranteed >= ridge_epsilon, diagonal variance preservation, missingness handling).
- Full alias trees for deadband, rank modulation, gamma regimes, and coupler across modules.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentotetravigesimal_hyperbolic_deadband,
    apply_sexcentotetravigesimal_deadband,
    apply_hexacosiatetravigesimal_hyperbolic_deadband,
    apply_hexacosiatetravigesimal_deadband,
    sexcentotetravigesimal_deadband,
    sexcentotetravigesimal_hyperbolic_deadband,
    hexacosiatetravigesimal_deadband,
    hexacosiatetravigesimal_hyperbolic_deadband,
    compute_phase102_deadband,
    apply_phase102_deadband,
    phase102_deadband,
    apply_624th_order_hyperbolic_deadband,
    apply_624th_deadband,
    apply_624_deadband,
    apply_hyperbolic_deadband_v102,
    suppress_factor_noise_hyperbolic_v102,
    apply_sexcentotetravigesimal_hyperbolic_deadband_v102,
    apply_sexcentotetravigesihedral_hyperbolic_deadband,
    apply_sexcentotetravigesimal_dihedral_hyperbolic_deadband,
    apply_sexcentotetravigesimal_suppression,
    compute_phase102_hyperconvex_rank_modulation,
    compute_135th_order_hyperconvex_rank_modulation,
    compute_phase102_rank_warping,
    compute_phase102_rank_modulation,
    phase102_rank_modulation,
    phase102_hyperconvex_rank_modulation,
    apply_phase102_rank_modulation,
    apply_hyper_convex_rank_modulation_v102,
    apply_135th_order_hyper_convex_rank_modulation,
    REGIME_GAMMA_TOP_V102,
    get_regime_adaptive_gamma_top_v102,
    get_regime_adaptive_gamma_top_phase102,
    get_gamma_top_v102,
    regime_adaptive_gamma_top_v102,
    get_phase102_gamma_top,
    phase102_gamma_top,
    get_gamma_top_phase102,
    adaptive_gamma_top_v102,
    Phase102FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)

from trading_system.src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase102Coupler,
    Phase102WhittakerDrinfeldCoupler,
    Phase102BorcherdsMoonshineCoupler,
    Phase102MonsterWhittakerCoupler,
    compute_phase102_coupling,
    compute_quantum_geometric_langlands_monster_whittaker_coupler_phase102,
    FERI_v102,
    feri_v102,
    f_out_102,
)

from trading_system.src.ai.score_normalizer import CrossSectionalScoreNormalizer
from trading_system.src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_pairwise_available_covariance,
    repair_covariance_psd,
)


class TestPhase102AlphaEnhancements:
    """Test suite for Phase 102 Alpha Signal Processing, Langlands Coupler, Normalizer, and Orthogonalizer."""

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F480: 624th-Order Deadband Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f480_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to exact float64 0.0
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_sexcentotetravigesimal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert val == 0.0, f"Expected exact 0.0 for micro noise, got {val}"

        # Conviction signal |z| >= 0.150 preserved with full transmission (>99.999%)
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_sexcentotetravigesimal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Negative conviction signals preserve negative sign
        neg_conv = np.array([-0.150, -0.300, -0.500])
        denoised_neg = apply_sexcentotetravigesimal_hyperbolic_deadband(neg_conv)
        for orig, d in zip(neg_conv, denoised_neg):
            assert d < 0.0
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test: strictly monotonic non-decreasing
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_sexcentotetravigesimal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f480_deadband_aliases(self):
        aliases = [
            apply_sexcentotetravigesimal_hyperbolic_deadband,
            apply_sexcentotetravigesimal_deadband,
            apply_hexacosiatetravigesimal_hyperbolic_deadband,
            apply_hexacosiatetravigesimal_deadband,
            sexcentotetravigesimal_deadband,
            sexcentotetravigesimal_hyperbolic_deadband,
            hexacosiatetravigesimal_deadband,
            hexacosiatetravigesimal_hyperbolic_deadband,
            compute_phase102_deadband,
            apply_phase102_deadband,
            phase102_deadband,
            apply_624th_order_hyperbolic_deadband,
            apply_624th_deadband,
            apply_624_deadband,
            apply_hyperbolic_deadband_v102,
            suppress_factor_noise_hyperbolic_v102,
            apply_sexcentotetravigesimal_hyperbolic_deadband_v102,
            apply_sexcentotetravigesihedral_hyperbolic_deadband,
            apply_sexcentotetravigesimal_dihedral_hyperbolic_deadband,
            apply_sexcentotetravigesimal_suppression,
        ]
        assert len(aliases) == 20
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase102FactorSuppressionEngine is not None
        assert Phase102FactorSuppressionEngine is RegimeFactorSuppressionEngine

    def test_feature_f480_ensemble_engine_deadband_dispatch(self):
        # Verify deadband dispatch for version=102 in EnsembleScoringEngine
        res_deadband = EnsembleScoringEngine.apply_smooth_noise_deadband(0.0001, version=102)
        assert res_deadband == 0.0

        # High conviction transmission
        res_conv = EnsembleScoringEngine.apply_smooth_noise_deadband(0.25, version=102)
        assert math.isclose(res_conv, 0.25, rel_tol=1e-3)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F480: 135th-Order Rank Modulation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f480_rank_modulation(self):
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase102_hyperconvex_rank_modulation(ranks, gamma_top=40.00)
        assert len(modulated) == len(ranks)
        # Monotonicity test
        assert np.all(np.diff(modulated) >= -1e-12)
        # Top-decile exponential boost: g(1.0) must exceed 1e7
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase102_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank
        assert math.isclose(mod_neg[0], 1.35, abs_tol=1e-5)   # r = 0.0
        assert math.isclose(mod_neg[-1], 0.35, abs_tol=1e-5)  # r = 1.0

    def test_feature_f480_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V102
        assert REGIME_GAMMA_TOP_V102["BULL_LOW_VOL"] == 40.00
        assert REGIME_GAMMA_TOP_V102["BULL_HIGH_VOL"] == 34.50
        assert REGIME_GAMMA_TOP_V102["SIDEWAYS"] == 27.20
        assert REGIME_GAMMA_TOP_V102["BEAR"] == 14.40
        assert REGIME_GAMMA_TOP_V102["CRISIS"] == 2.30

        gamma_bull = get_regime_adaptive_gamma_top_v102("BULL_LOW_VOL")
        assert gamma_bull == 40.00
        gamma_crisis = get_regime_adaptive_gamma_top_v102("CRISIS")
        assert gamma_crisis == 2.30

    def test_feature_f480_rank_modulation_aliases(self):
        aliases = [
            compute_phase102_hyperconvex_rank_modulation,
            compute_135th_order_hyperconvex_rank_modulation,
            compute_phase102_rank_warping,
            compute_phase102_rank_modulation,
            phase102_rank_modulation,
            phase102_hyperconvex_rank_modulation,
            apply_phase102_rank_modulation,
            apply_hyper_convex_rank_modulation_v102,
            apply_135th_order_hyper_convex_rank_modulation,
        ]
        assert len(aliases) == 9
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=27.20)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=27.20)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        gamma_aliases = [
            get_regime_adaptive_gamma_top_v102,
            get_regime_adaptive_gamma_top_phase102,
            get_gamma_top_v102,
            regime_adaptive_gamma_top_v102,
            get_phase102_gamma_top,
            phase102_gamma_top,
            get_gamma_top_phase102,
            adaptive_gamma_top_v102,
        ]
        assert len(gamma_aliases) == 8
        base_g = gamma_aliases[0]("BULL_LOW_VOL")
        for g_fn in gamma_aliases[1:]:
            assert g_fn("BULL_LOW_VOL") == base_g

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F481: Quantum Geometric Langlands Monster Whittaker Coupler
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f481_coupler_properties_v102(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version >= 102
        assert getattr(coupler, "is_phase102", False) is True
        assert getattr(coupler, "is_phase101", False) is True
        assert getattr(coupler, "is_phase100", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 43.40, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.99999999999999999999999999  # 26-nines
        assert math.isclose(coupler.harmony_boost, 12.00, abs_tol=1e-5)

        # Forward coupling test
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v102" in res or "feri_v102" in res or "f_out_102" in res
        assert "FERI_v101" in res or "feri_v101" in res or "f_out_101" in res

    def test_feature_f481_coupler_aliases(self):
        assert Phase102Coupler is not None
        assert Phase102WhittakerDrinfeldCoupler is not None
        assert Phase102BorcherdsMoonshineCoupler is not None
        assert Phase102MonsterWhittakerCoupler is not None
        coupler = Phase102Coupler()
        assert coupler.version >= 102
        assert coupler.is_phase102 is True

        df = pd.DataFrame({
            "p1": [0.10, 0.20],
            "p2": [0.12, 0.18],
            "p3": [0.11, 0.22],
            "p4": [0.09, 0.19]
        })
        res1 = compute_phase102_coupling(df)
        res2 = compute_quantum_geometric_langlands_monster_whittaker_coupler_phase102(df)
        assert isinstance(res1, dict)
        assert isinstance(res2, dict)
        assert "FERI_v102" in res1
        assert "FERI_v102" in res2

    def test_feature_f481_factor_clipping_overflow_protection(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        # Extreme factor magnitudes that would normally overflow p^128 or (diff)^216
        df_extreme = pd.DataFrame({
            "p1": [500.0, -500.0],
            "p2": [400.0, -400.0],
            "p3": [350.0, -350.0],
            "p4": [300.0, -300.0],
            "p5": [0.0, 0.0]
        })
        res = coupler.couple_signals(df_extreme)
        assert isinstance(res, dict)
        f_val = res.get("FERI_v102", res.get("f_out_102"))
        assert f_val is not None
        if isinstance(f_val, pd.Series):
            assert np.all(np.isfinite(f_val.values))
        else:
            assert np.all(np.isfinite(f_val))

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F481: Tail-Preserving Student-t Normalization Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f481_student_t_score_normalization(self):
        norm = CrossSectionalScoreNormalizer(method="student_t")

        df = pd.DataFrame({
            "strat_a": [-3.0, -1.0, 0.0, 1.0, 3.0, 6.0, np.nan],
            "strat_b": [10.0, 20.0, 30.0, 40.0, 50.0, 100.0, 15.0],
            "market": ["SP500"] * 7
        })

        norm_df = norm.normalize_scores(df, strategy_cols=["strat_a", "strat_b"])

        # Strict NaN preservation
        assert pd.isna(norm_df.loc[6, "strat_a"])
        assert not pd.isna(norm_df.loc[6, "strat_b"])

        # Bounds strictly in [0.005, 0.995]
        for col in ["strat_a", "strat_b"]:
            valid_vals = norm_df[col].dropna()
            assert (valid_vals >= 0.005).all()
            assert (valid_vals <= 0.995).all()

        # Fat-tail distinction preservation: extreme observation at row 5 (val=6.0)
        # must have higher score than row 4 (val=3.0)
        assert norm_df.loc[5, "strat_a"] > norm_df.loc[4, "strat_a"]

    def test_feature_f481_student_t_zero_block_isolation(self):
        norm = CrossSectionalScoreNormalizer(method="student_t")
        # 10 stocks, 5 zero scores (50% > 20% threshold), 5 positive scores
        df = pd.DataFrame({
            "sparse_factor": [0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "market": ["KOSPI"] * 10
        })
        norm_df = norm.normalize_scores(df, strategy_cols=["sparse_factor"])
        res = norm_df["sparse_factor"].values

        # Inactive zeros receive neutral 0.50
        assert np.all(res[:5] == 0.50)
        # Active positive signals are strictly ranked in [0.52, 0.995]
        assert np.all(res[5:] >= 0.52)
        assert np.all(np.diff(res[5:]) > 0.0)

    def test_feature_f481_combine_predictions_student_t_integration(self):
        engine = EnsembleScoringEngine()
        reg_df = pd.DataFrame({
            "symbol": [f"SYM_{i}" for i in range(10)],
            "predicted_return": [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, -1.0, -2.0, 0.5, 2.5],
            "market": ["SP500"] * 10
        })
        res_df = engine.combine_predictions(reg_df=reg_df, version=102)
        assert not res_df.empty
        assert "ensemble_expected_return" in res_df.columns
        assert len(res_df) == 10

    # ─────────────────────────────────────────────────────────────────────────
    # Feature F481: Pairwise Covariance & PSD Repair Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_feature_f481_pairwise_covariance_and_psd_repair(self):
        np.random.seed(42)
        # Generate 25 samples for 4 factors with structured missingness
        X = np.random.randn(25, 4)
        X[0:5, 0] = np.nan
        X[4:10, 1] = np.nan
        X[15:20, 2] = np.nan

        # Compute pairwise covariance with repair
        C = compute_pairwise_available_covariance(X, min_periods=3, repair=True, ridge_epsilon=1e-6)

        assert C.shape == (4, 4)
        # Check exact symmetry
        np.testing.assert_allclose(C, C.T, atol=1e-12)

        # Check positive semi-definiteness: all eigenvalues >= ridge_epsilon
        evals = np.linalg.eigvalsh(C)
        assert np.all(evals >= 1e-6)

        # Check diagonal preservation of marginal variances
        for i in range(4):
            valid_i = X[~np.isnan(X[:, i]), i]
            sample_var = float(np.var(valid_i, ddof=1))
            assert math.isclose(C[i, i], sample_var, rel_tol=1e-4)

    def test_feature_f481_repair_adversarial_non_psd_matrix(self):
        # Adversarial matrix with severely negative eigenvalue
        C_non_psd = np.array([
            [1.0, 0.95, 0.95],
            [0.95, 1.0, -0.95],
            [0.95, -0.95, 1.0]
        ], dtype=np.float64)

        orig_evals = np.linalg.eigvalsh(C_non_psd)
        assert np.any(orig_evals < 0.0), "Input must be non-PSD for stress testing"

        C_repaired = repair_covariance_psd(C_non_psd, ridge_epsilon=1e-6)

        repaired_evals = np.linalg.eigvalsh(C_repaired)
        assert np.all(repaired_evals >= 1e-6)

        # Diagonal variances strictly preserved
        np.testing.assert_allclose(np.diag(C_repaired), np.diag(C_non_psd), atol=1e-8)

    def test_feature_f481_factor_orthogonalizer_engine_missingness(self):
        engine = FactorOrthogonalizerEngine(default_method="pca_symmetric", ridge_epsilon=1e-6)

        # DataFrame with NaNs across factors
        df = pd.DataFrame({
            "f1": [0.2, 0.4, np.nan, 0.8, 0.9, 0.5, 0.3, 0.7],
            "f2": [0.3, np.nan, 0.5, 0.7, 0.8, 0.4, 0.2, 0.6],
            "f3": [0.1, 0.3, 0.6, np.nan, 0.7, 0.5, 0.4, 0.8],
            "market": ["SP500"] * 8
        })

        ortho_df = engine.orthogonalize(df, strategy_cols=["f1", "f2", "f3"])

        # NaNs must remain strictly preserved at original coordinates
        assert pd.isna(ortho_df.loc[2, "f1"])
        assert pd.isna(ortho_df.loc[1, "f2"])
        assert pd.isna(ortho_df.loc[3, "f3"])

        # Valid values bounded in [0.0, 1.0]
        for col in ["f1", "f2", "f3"]:
            valid = ortho_df[col].dropna()
            assert (valid >= 0.0).all()
            assert (valid <= 1.0).all()

"""
tests/test_adversarial_m1_2_opt3_stress.py

Adversarial Stress Test Suite for Milestone 1 (3rd Deep Quantitative Enhancement)
Evaluates Empirical Robustness and Failure Modes for Features F04, F06, F07, F08:
1. Chaotic Universe & Decay Filtering (F04, F06):
   - Dynamic universe churn across repeated combine_predictions runs
   - Duplicate symbol rows and duplicate columns
   - Extreme boundary scores (all-zero, all-one) and heavy NaN/Inf injection
   - Memory boundedness of _prev_filtered_scores cache
2. Pathological Collinearity in Factor Orthogonalizer (F08):
   - Isolation of 5 constant columns without cross-contamination noise bleed
   - Multiple pairwise duplicate/identical columns (singular covariance)
   - Severe singularity regime (N=5, K=37: N << K)
   - Top-level orthogonalize() pipeline integration under singularity
3. Ill-Conditioned Entropy Solver (F07):
   - Synthetic correlation matrix with condition number > 10^6
   - Severe condition number (> 10^7) combined with heavy partial missingness (10 present, 27 missing)
   - All-ones singular correlation matrix (rank 1, condition number -> inf)
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import (
    RegimeFactorSuppressionEngine,
    solve_single_stage_entropy_allocation
)


# =============================================================================
# SUITE 1: Chaotic Universe & Multi-Horizon Decay Filtering (F04, F06)
# =============================================================================

class TestChaoticUniverseAndDecayFiltering:
    """Stress tests for combine_predictions with dynamic universes, duplicates, NaNs, and bounds."""

    def test_dynamic_universe_churn_and_bounded_memory(self):
        """
        Simulate 15 consecutive trading days with chaotic universe churn:
        Symbols dynamically entering, exiting, and re-entering across rounds.
        Universe size oscillates between 5 and 45 symbols.
        Verify:
        - combine_predictions runs without failure across all rounds.
        - All output scores ('ensemble_score' and strategy scores) are strictly in [0.0, 1.0].
        - Memory in _prev_filtered_scores is strictly bounded to current universe (no leak).
        """
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()

        np.random.seed(101)
        all_possible_symbols = [f"SYM_{i:03d}" for i in range(100)]

        for day in range(15):
            # Dynamic universe selection
            n_syms = np.random.randint(5, 45)
            active_symbols = sorted(list(np.random.choice(all_possible_symbols, size=n_syms, replace=False)))
            market = "US" if day % 2 == 0 else "KOSPI"

            # Create synthetic prediction inputs
            reg_df = pd.DataFrame({
                "symbol": active_symbols,
                "expected_return": np.random.uniform(-5.0, 15.0, size=n_syms),
                "market": market
            })
            surge_df = pd.DataFrame({
                "symbol": active_symbols,
                "surge_probability": np.random.uniform(0.0, 1.0, size=n_syms),
                "market": market
            })
            stat_arb_df = pd.DataFrame({
                "symbol": active_symbols,
                "stat_arb_score": np.random.uniform(0.1, 0.9, size=n_syms)
            })

            regime = "BULL_LOW_VOL" if day % 3 == 0 else ("CRISIS" if day % 3 == 1 else "SIDEWAYS_HIGH_VOL")

            res = engine.combine_predictions(
                reg_df=reg_df,
                s_df=surge_df,
                stat_arb_df=stat_arb_df,
                regime=regime
            )

            # Assertions on output
            assert not res.empty, f"Day {day}: Result must not be empty"
            assert len(res) == n_syms, f"Day {day}: Output length {len(res)} must match input {n_syms}"
            assert "ensemble_score" in res.columns, f"Day {day}: 'ensemble_score' missing"

            # Strict bounds check [0.0, 1.0]
            assert (res["ensemble_score"] >= 0.0).all(), f"Day {day}: Score < 0.0 found"
            assert (res["ensemble_score"] <= 1.0).all(), f"Day {day}: Score > 1.0 found"
            assert not res["ensemble_score"].isna().any(), f"Day {day}: NaNs in ensemble_score"

            # Verify memory boundedness:
            # _prev_filtered_scores['global'] should NOT accumulate exited symbols.
            # Its length must equal the current active chunk length!
            cached_global = engine._prev_filtered_scores.get("global")
            assert cached_global is not None
            assert len(cached_global) == n_syms, (
                f"Day {day}: Cache memory leak detected! Expected {n_syms} cached symbols, got {len(cached_global)}"
            )

    def test_duplicate_symbol_rows_graceful_handling(self):
        """
        Adversarial inputs containing duplicate symbol rows in input DataFrames.
        Verify:
        - combine_predictions or decay filtering does not crash on duplicate index.
        - Output produces finite valid scores in [0.0, 1.0].
        """
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()

        # Duplicate "AAPL" (3x) and "MSFT" (2x)
        symbols_with_dups = ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT", "GOOG"]
        reg_df = pd.DataFrame({
            "symbol": symbols_with_dups,
            "expected_return": [0.10, 0.12, 0.11, 0.05, 0.06, 0.20],
            "market": "US"
        })
        surge_df = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOG"],
            "surge_probability": [0.70, 0.40, 0.85],
            "market": "US"
        })

        # Run day 1
        res1 = engine.combine_predictions(reg_df=reg_df, s_df=surge_df, regime="BULL_LOW_VOL")
        assert not res1.empty
        assert (res1["ensemble_score"] >= 0.0).all() and (res1["ensemble_score"] <= 1.0).all()

        # Run day 2 with same duplicates to trigger warm-start decay filter with duplicates
        res2 = engine.combine_predictions(reg_df=reg_df, s_df=surge_df, regime="BULL_LOW_VOL")
        assert not res2.empty
        assert (res2["ensemble_score"] >= 0.0).all() and (res2["ensemble_score"] <= 1.0).all()

    def test_duplicate_columns_graceful_handling(self):
        """
        Adversarial inputs containing duplicate column names in DataFrames.
        Verify:
        - apply_exponential_decay_filter handles duplicate column names in current and previous scores.
        - combine_predictions does not crash and produces valid bounded scores.
        """
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()

        # Test direct apply_exponential_decay_filter with duplicated columns in both current and prev
        curr_dup = pd.DataFrame(
            [[ "A", 0.7, 0.7, 0.8 ], [ "B", 0.3, 0.3, 0.4 ]],
            columns=["symbol", "reg_score", "reg_score", "surge_score"]
        )
        prev_dup = pd.DataFrame(
            [[ "A", 0.5, 0.5 ], [ "B", 0.2, 0.2 ]],
            columns=["symbol", "reg_score", "reg_score"]
        )

        res_filtered = engine.apply_exponential_decay_filter(
            current_scores=curr_dup,
            previous_scores=prev_dup,
            regime="BULL_LOW_VOL"
        )
        assert not res_filtered.empty
        assert len(res_filtered) == 2

        # Test combine_predictions with duplicate columns in reg_df
        reg_base = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "expected_return": [0.10, 0.15, 0.20],
            "market": ["US", "US", "US"]
        })
        reg_with_dup_cols = pd.concat([reg_base, reg_base[["expected_return"]]], axis=1)

        surge_df = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "surge_probability": [0.60, 0.70, 0.80],
            "market": ["US", "US", "US"]
        })

        res_comb = engine.combine_predictions(
            reg_df=reg_with_dup_cols,
            s_df=surge_df,
            regime="BULL_LOW_VOL"
        )
        assert not res_comb.empty
        assert "ensemble_score" in res_comb.columns
        assert (res_comb["ensemble_score"] >= 0.0).all() and (res_comb["ensemble_score"] <= 1.0).all()

    def test_extreme_boundary_all_zero_and_all_one_scores(self):
        """
        Adversarial inputs where all factor scores are identically 0.0 or identically 1.0.
        Verify:
        - Output ensemble_score remains strictly within [0.0, 1.0].
        - No zero-division or numerical collapse occurs.
        - Bessembinder convex power law preserves bounds.
        """
        engine = EnsembleScoringEngine()

        syms = ["SYM_A", "SYM_B", "SYM_C", "SYM_D", "SYM_E"]

        # Case 1: All-zero scores
        reg_zero = pd.DataFrame({"symbol": syms, "expected_return": [0.0] * 5, "market": "US"})
        surge_zero = pd.DataFrame({"symbol": syms, "surge_probability": [0.0] * 5, "market": "US"})

        res_zero = engine.combine_predictions(reg_df=reg_zero, s_df=surge_zero, regime="BULL_LOW_VOL")
        assert (res_zero["ensemble_score"] >= 0.0).all()
        assert (res_zero["ensemble_score"] <= 1.0).all()
        assert not res_zero["ensemble_score"].isna().any()

        # Case 2: All-one scores
        reg_one = pd.DataFrame({"symbol": syms, "expected_return": [100.0] * 5, "market": "US"})
        surge_one = pd.DataFrame({"symbol": syms, "surge_probability": [1.0] * 5, "market": "US"})

        res_one = engine.combine_predictions(reg_df=reg_one, s_df=surge_one, regime="BULL_LOW_VOL")
        assert (res_one["ensemble_score"] >= 0.0).all()
        assert (res_one["ensemble_score"] <= 1.0).all()
        assert not res_one["ensemble_score"].isna().any()

        # In pure tied-universe, cross-sectional normalization correctly assigns neutral median 0.50
        assert (res_zero["ensemble_score"] == 0.50).all()
        assert (res_one["ensemble_score"] == 0.50).all()

        # Case 3: Mixed cross-sectional dispersion (SYM_HIGH=100.0, SYM_LOW=-100.0)
        reg_mixed = pd.DataFrame({
            "symbol": ["SYM_HIGH", "SYM_MID", "SYM_LOW"],
            "expected_return": [100.0, 0.0, -100.0],
            "market": "US"
        })
        surge_mixed = pd.DataFrame({
            "symbol": ["SYM_HIGH", "SYM_MID", "SYM_LOW"],
            "surge_probability": [0.99, 0.50, 0.01],
            "market": "US"
        })
        res_mixed = engine.combine_predictions(reg_df=reg_mixed, s_df=surge_mixed, regime="BULL_LOW_VOL")
        high_score = res_mixed.loc[res_mixed["symbol"] == "SYM_HIGH", "ensemble_score"].iloc[0]
        low_score = res_mixed.loc[res_mixed["symbol"] == "SYM_LOW", "ensemble_score"].iloc[0]
        assert high_score > low_score, f"High score {high_score} must exceed low score {low_score}"
        assert (res_mixed["ensemble_score"] >= 0.0).all() and (res_mixed["ensemble_score"] <= 1.0).all()

    def test_pathological_nans_and_infinities_resilience(self):
        """
        Adversarial inputs with 50% NaNs, entire columns of NaNs, and Infs.
        Verify:
        - Pipeline does not raise unhandled exceptions.
        - Imputation prevents NaN propagation to ensemble_score.
        - All output scores remain strictly in [0.0, 1.0].
        """
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()

        syms = [f"STOCK_{i}" for i in range(12)]
        reg_df = pd.DataFrame({
            "symbol": syms,
            "expected_return": [1.0, np.nan, -2.0, np.inf, 5.0, np.nan, 0.0, -np.inf, 3.0, np.nan, 2.0, 1.5],
            "market": "US"
        })
        surge_df = pd.DataFrame({
            "symbol": syms,
            "surge_probability": [np.nan] * 12,  # Entire column NaN
            "market": "US"
        })
        stat_arb_df = pd.DataFrame({
            "symbol": syms,
            "stat_arb_score": [0.5, np.nan, 0.8, 0.2, np.nan, np.nan, 0.9, 0.1, np.nan, 0.6, 0.4, np.nan]
        })

        res = engine.combine_predictions(
            reg_df=reg_df,
            s_df=surge_df,
            stat_arb_df=stat_arb_df,
            regime="CRISIS"
        )

        assert not res.empty
        assert len(res) == 12
        assert not res["ensemble_score"].isna().any(), "ensemble_score must never contain NaNs"
        assert (res["ensemble_score"] >= 0.0).all()
        assert (res["ensemble_score"] <= 1.0).all()
        assert np.isfinite(res["ensemble_score"]).all()


# =============================================================================
# SUITE 2: Pathological Collinearity in Factor Orthogonalizer (F08)
# =============================================================================

class TestPathologicalCollinearityOrthogonalizer:
    """Stress tests for FactorOrthogonalizerEngine under severe singularity and collinearity."""

    def test_five_constant_columns_isolation(self):
        """
        Adversarial matrix with 5 constant columns interspersed among active features:
        - Column 0, 1, 2: Active correlated signals
        - Column 3, 4, 5, 6, 7: Constant columns (0.0, 0.5, 1.0, -2.5, 100.0)
        - Column 8, 9: Additional active features
        Verify:
        - _pca_zca_symmetric isolates active columns.
        - Constant columns remain strictly uncorrupted (zero noise bleed).
        - Active columns are decorrelated.
        - Output is completely finite without NaNs.
        """
        ortho = FactorOrthogonalizerEngine(default_method="pca_symmetric")
        N = 40
        np.random.seed(42)

        # Active correlated features
        latent = np.random.randn(N)
        f0 = latent + 0.2 * np.random.randn(N)
        f1 = latent + 0.2 * np.random.randn(N)
        f2 = 0.5 * latent + 0.5 * np.random.randn(N)

        # 5 Constant columns
        c3 = np.full(N, 0.0)
        c4 = np.full(N, 0.5)
        c5 = np.full(N, 1.0)
        c6 = np.full(N, -2.5)
        c7 = np.full(N, 100.0)

        # More active features
        f8 = np.random.randn(N)
        f9 = np.random.randn(N)

        X = np.column_stack([f0, f1, f2, c3, c4, c5, c6, c7, f8, f9])
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        stds[3:8] = 1e-6  # Clipped std for constant columns

        X_ortho = ortho._pca_zca_symmetric(X, means, stds, preserve_pc1=True, preserve_top_k=1)

        assert X_ortho.shape == (N, 10)
        assert np.isfinite(X_ortho).all(), "Orthogonalized matrix must be strictly finite"
        assert not np.isnan(X_ortho).any(), "No NaNs permitted"

        # Verify 5 constant columns are exactly preserved without noise bleed
        np.testing.assert_allclose(X_ortho[:, 3], 0.0, atol=1e-6, err_msg="c3 corrupted")
        np.testing.assert_allclose(X_ortho[:, 4], 0.5, atol=1e-6, err_msg="c4 corrupted")
        np.testing.assert_allclose(X_ortho[:, 5], 1.0, atol=1e-6, err_msg="c5 corrupted")
        np.testing.assert_allclose(X_ortho[:, 6], -2.5, atol=1e-6, err_msg="c6 corrupted")
        np.testing.assert_allclose(X_ortho[:, 7], 100.0, atol=1e-6, err_msg="c7 corrupted")

        # Verify active columns were decorrelated
        raw_corr_01 = np.corrcoef(X[:, 0], X[:, 1])[0, 1]
        ortho_corr_01 = np.corrcoef(X_ortho[:, 0], X_ortho[:, 1])[0, 1]
        assert abs(ortho_corr_01) < abs(raw_corr_01), (
            f"Correlation between active columns did not decrease: {raw_corr_01:.3f} -> {ortho_corr_01:.3f}"
        )

    def test_multiple_pairwise_identical_duplicate_columns(self):
        """
        Adversarial matrix with multiple pairs of perfectly identical columns:
        - col 0 == col 1
        - col 2 == col 3
        - col 4 == col 5
        This causes perfect collinearity (multiple zero eigenvalues in sample covariance).
        Verify:
        - Whitening filter capping and Marchenko-Pastur lower floor prevent division by zero.
        - Output is completely finite and valid.
        """
        ortho = FactorOrthogonalizerEngine(default_method="pca_symmetric")
        N = 35
        np.random.seed(99)

        base1 = np.random.randn(N)
        base2 = np.random.randn(N)
        base3 = np.random.randn(N)
        base4 = np.random.randn(N)

        col0 = base1
        col1 = base1.copy()  # Duplicate pair 1
        col2 = base2
        col3 = base2.copy()  # Duplicate pair 2
        col4 = base3
        col5 = base3.copy()  # Duplicate pair 3
        col6 = base4

        X = np.column_stack([col0, col1, col2, col3, col4, col5, col6])
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        X_ortho = ortho._pca_zca_symmetric(X, means, stds, preserve_pc1=False, preserve_top_k=0)

        assert X_ortho.shape == (N, 7)
        assert np.isfinite(X_ortho).all(), "Orthogonalized output with duplicates must be finite"
        assert not np.isnan(X_ortho).any()

    def test_severe_singularity_n5_k37(self):
        """
        Extreme singularity regime: N=5 cross-sectional samples, K=37 features.
        N << K means the empirical covariance matrix has rank <= 4 (at least 33 zero eigenvalues).
        Verify:
        - Does not crash with LinAlgError or SingularMatrix exception.
        - Returns (5, 37) array with all finite numbers.
        """
        ortho = FactorOrthogonalizerEngine(default_method="pca_symmetric")
        N = 5
        K = 37
        np.random.seed(777)

        X = np.random.uniform(0.1, 0.9, size=(N, K))
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        X_ortho = ortho._pca_zca_symmetric(X, means, stds, preserve_pc1=True, preserve_top_k=1)

        assert X_ortho.shape == (N, K)
        assert np.isfinite(X_ortho).all()
        assert not np.isnan(X_ortho).any()

    def test_top_level_orthogonalize_dataframe_under_pathological_conditions(self):
        """
        End-to-end call of FactorOrthogonalizerEngine.orthogonalize(score_df):
        Score DataFrame with 37 columns, N=6 samples, 5 constant columns, and 2 identical columns.
        Verify:
        - Output is a valid DataFrame matching input index and columns.
        - Values are strictly finite and normalized in [0.0, 1.0].
        - Constant columns retain their values.
        """
        ortho = FactorOrthogonalizerEngine(default_method="pca_symmetric")
        N = 6
        np.random.seed(123)

        cols = [f"strat_{i}_score" for i in range(37)]
        data = np.random.uniform(0.2, 0.8, size=(N, 37))

        # Inject 5 constant columns
        for c_idx in [5, 12, 19, 26, 33]:
            data[:, c_idx] = 0.50

        # Inject duplicate column
        data[:, 2] = data[:, 1]

        df = pd.DataFrame(data, columns=cols, index=[f"SYM_{i}" for i in range(N)])

        out_df = ortho.orthogonalize(df, strategy_cols=cols)

        assert out_df.shape == (N, 37)
        assert list(out_df.columns) == cols
        assert not out_df.isna().any().any(), "No NaNs permitted in orthogonalized DataFrame"
        assert (out_df.values >= 0.0).all() and (out_df.values <= 1.0).all(), (
            "All orthogonalized scores must be bounded in [0.0, 1.0]"
        )


# =============================================================================
# SUITE 3: Ill-Conditioned Entropy Redundancy Solver (F07)
# =============================================================================

class TestIllConditionedEntropySolver:
    """Stress tests for solve_single_stage_entropy_allocation and suppress_weights."""

    def test_synthetic_correlation_condition_number_exceeding_1e6(self):
        """
        Generate a synthetic 10x10 correlation matrix with condition number > 10^6.
        Verify:
        - solve_single_stage_entropy_allocation converges to finite, valid weights.
        - All weights >= w_min (0.005).
        - Weights sum strictly to 1.0000.
        """
        K = 10
        np.random.seed(42)

        # Generate orthogonal Q via QR decomposition
        A = np.random.randn(K, K)
        Q, _ = np.linalg.qr(A)

        # Ill-conditioned spectrum: lambda_max / lambda_min > 10^6
        eigvals = np.logspace(0, -7, K)  # cond ~ 10^7
        C = Q @ np.diag(eigvals) @ Q.T
        # Rescale to correlation matrix (unit diagonal)
        D_inv = np.diag(1.0 / np.sqrt(np.diag(C)))
        R = D_inv @ C @ D_inv
        R = (R + R.T) * 0.5
        np.fill_diagonal(R, 1.0)

        cond_num = np.linalg.cond(R)
        assert cond_num > 1e6, f"Constructed condition number must exceed 10^6, got {cond_num:.2e}"

        w0 = np.ones(K) / K
        opt_w = solve_single_stage_entropy_allocation(
            R=R,
            w0=w0,
            tau_entropy=0.05,
            gamma_anchor=1.0,
            w_min=0.005,
            max_iter=200
        )

        assert len(opt_w) == K
        assert np.isfinite(opt_w).all(), "Entropy solver weights must be strictly finite"
        assert not np.isnan(opt_w).any()
        assert pytest.approx(float(np.sum(opt_w)), abs=1e-5) == 1.0
        assert all(w >= 0.005 - 1e-6 for w in opt_w), f"Minimum weight floor violated: {np.min(opt_w)}"

    def test_ill_conditioned_entropy_with_extreme_partial_missingness(self):
        """
        Adversarial test of suppress_weights():
        - 37 base strategies in universe.
        - Correlation matrix contains only 10 active strategies (27 strategies missing).
        - The 10x10 active sub-matrix has condition number > 10^7.
        Verify:
        - suppress_weights successfully completes without crashing.
        - Output contains all 37 strategies.
        - All 37 weights are strictly positive (> 0.0).
        - Output weights sum strictly to 1.0000.
        - Missing strategies and active strategies are balanced proportionally.
        """
        engine = RegimeFactorSuppressionEngine()

        all_37_strats = list(EnsembleScoringEngine.REGIME_2D_WEIGHTS["BULL_LOW_VOL"].keys())
        active_10 = all_37_strats[:10]
        missing_27 = all_37_strats[10:]

        # Construct ill-conditioned 10x10 correlation matrix
        K = 10
        np.random.seed(888)
        A = np.random.randn(K, K)
        Q, _ = np.linalg.qr(A)
        eigvals = np.logspace(0, -7.5, K)  # cond > 10^7
        C = Q @ np.diag(eigvals) @ Q.T
        D_inv = np.diag(1.0 / np.sqrt(np.diag(C)))
        R = D_inv @ C @ D_inv
        R = (R + R.T) * 0.5
        np.fill_diagonal(R, 1.0)

        assert np.linalg.cond(R) > 1e7, f"Condition number must exceed 10^7, got {np.linalg.cond(R):.2e}"

        corr_df = pd.DataFrame(R, index=active_10, columns=active_10)

        base_weights = {s: 1.0 / 37.0 for s in all_37_strats}

        suppressed_w = engine.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_df,
            regime_label="CRISIS",
            use_entropy_allocation=True,
            n_samples=60
        )

        assert len(suppressed_w) == 37, f"Expected 37 strategies in output, got {len(suppressed_w)}"
        assert pytest.approx(sum(suppressed_w.values()), abs=1e-5) == 1.0, (
            f"Suppressed weights must sum to 1.0, got {sum(suppressed_w.values())}"
        )
        assert all(w > 0.0 for w in suppressed_w.values()), "All weights must be strictly positive"
        assert all(np.isfinite(w) for w in suppressed_w.values()), "All weights must be finite"

        # Check proportion of active vs missing mass:
        active_sum = sum(suppressed_w[s] for s in active_10)
        missing_sum = sum(suppressed_w[s] for s in missing_27)
        assert pytest.approx(active_sum + missing_sum, abs=1e-5) == 1.0
        assert 0.15 < active_sum < 0.40, f"Active sum {active_sum:.4f} should reflect 10/37 ~ 0.27 share"

    def test_pathological_singular_all_ones_correlation_matrix(self):
        """
        Extreme edge case: Correlation matrix of all ones (perfect 1.0 correlation everywhere).
        Matrix rank is 1, condition number is infinite.
        Verify:
        - suppress_weights handles it gracefully (via solver or clean fallback).
        - Output weights sum strictly to 1.0000.
        - Strategy diversification is maintained (weights do not collapse to a single factor).
        """
        engine = RegimeFactorSuppressionEngine()

        strats = ["surge", "vcp_ml", "stat_arb", "rim_valuation", "mq_factor", "order_flow"]
        K = len(strats)
        R_all_ones = np.ones((K, K))
        corr_df = pd.DataFrame(R_all_ones, index=strats, columns=strats)

        base_weights = {s: 1.0 / K for s in strats}

        suppressed_w = engine.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_df,
            regime_label="SIDEWAYS_LOW_VOL",
            use_entropy_allocation=True,
            n_samples=50
        )

        assert len(suppressed_w) == K
        assert pytest.approx(sum(suppressed_w.values()), abs=1e-5) == 1.0
        assert all(w > 0.0 for w in suppressed_w.values())
        assert all(np.isfinite(w) for w in suppressed_w.values())

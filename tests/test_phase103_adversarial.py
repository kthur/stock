"""
tests/test_phase103_adversarial.py

Adversarial Stress Test Suite for Phase 103 Milestone 1 Alpha Features (F485, F486):
- 632nd-Order Deadband:
    * Zero noise leakage at z in {0.0, 0.0001, 0.0003, -0.0001, -0.0003} and denormals
    * Strict threshold boundary behaviour around z = 0.0003 and sharp transition near z = 0.035
    * Monotonicity, odd symmetry, float32/float64/Series/scalar compatibility
- 137th-Order Rank Modulation:
    * Monotonicity on [0.0, 1.0] across fine grid (10,000 points)
    * Top-decile exponential boost g(1.0) > 10^7 for BULL_LOW_VOL
    * Negative penalty g_neg(r) = 1.35 - 1.00*r for negative signals
    * Out-of-bounds handling (negative ranks r < 0, oversized ranks r > 1.0, extreme values)
- Multi-Horizon Monotonicity Regularizer:
    * Monte Carlo randomized inverted probability distributions (1,000 trials)
    * Extreme inversions ([0.9, 0.5, 0.3, 0.1], [1.0, 0.0, 0.0, 0.0], alternating, etc.)
    * PAVA mathematical invariants (L2 projection, mean conservation, bounds preservation)
    * Empty DF, missing columns, NaNs, infs
- Cross-Sectional Ranking:
    * Singleton groups (N=1 fallback to 0.50)
    * All-NaN groups (NaN preservation, zero crash)
    * Identical value groups (tie handling, bounds compliance)
    * Multi-group combinations (market x sector)
- Coupler F486 Stress:
    * Extreme inputs (+/- 1000.0), uniform inputs, zero-variance inputs
    * Output keys validation and finite boundedness
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentoduotrigesimal_hyperbolic_deadband,
    compute_phase103_hyperconvex_rank_modulation,
    REGIME_GAMMA_TOP_V103,
    get_regime_adaptive_gamma_top_v103,
)
from trading_system.src.ai.prediction_model import (
    isotonic_pava,
    regularize_multi_horizon_monotonicity,
    compute_cross_sectional_relative_rank_features,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    compute_phase103_coupling,
    FERI_v103,
    feri_v103,
    f_out_103,
)


class TestPhase103AdversarialAlpha:
    """Adversarial challenger test harness for Milestone 1 Alpha features."""

    # =========================================================================
    # 1. 632nd-Order Deadband Adversarial Tests
    # =========================================================================
    @pytest.mark.parametrize("z_val", [0.0, 0.0001, 0.0003, -0.0001, -0.0003, 1e-15, -1e-15, 1e-300, -1e-300])
    def test_deadband_zero_noise_leakage_scalars(self, z_val):
        """Verify absolute zero leakage (exact float64 0.0) for |z| <= 0.0003."""
        out = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_val)
        assert out == 0.0, f"Leakage observed for scalar {z_val}: got {out}"

    def test_deadband_zero_noise_leakage_vector(self):
        """Vectorized zero noise leakage test across dense sub-0.0003 grid."""
        z_grid = np.linspace(-0.0003, 0.0003, 601)
        out = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_grid)
        assert np.all(out == 0.0), f"Non-zero elements found in deadband zone: {out[out != 0.0]}"

    def test_deadband_sharp_transition_at_delta(self):
        """
        Verify the ultra-sharp transition profile near delta = 0.035:
        At z = 0.030: transmission should be effectively zero (< 1e-35).
        At z = 0.035: transmission is ~76.16% (tanh(1.0) = 0.761594).
        At z = 0.040: transmission should be > 99.9999%.
        At z >= 0.050: transmission is 100.000%.
        """
        z_sub = 0.030
        out_sub = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_sub)
        # (0.030 / 0.035)^632 ≈ 1.1e-42
        assert abs(out_sub) < 1e-35, f"Expected near zero at 0.030, got {out_sub}"

        z_delta = 0.035
        out_delta = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_delta)
        expected_ratio = math.tanh(1.0**632)
        assert math.isclose(out_delta / z_delta, expected_ratio, rel_tol=1e-5), (
            f"Expected ratio {expected_ratio} at delta, got {out_delta / z_delta}"
        )

        z_sup = 0.040
        out_sup = apply_sexcentoduotrigesimal_hyperbolic_deadband(z_sup)
        # (0.040 / 0.035)^632 >> 1, tanh -> 1.0
        assert math.isclose(out_sup, z_sup, rel_tol=1e-12), (
            f"Expected full transmission at 0.040, got {out_sup} vs {z_sup}"
        )

        # Transition steepness: derivative / difference between 0.034 and 0.036
        t_34 = apply_sexcentoduotrigesimal_hyperbolic_deadband(0.034)
        t_36 = apply_sexcentoduotrigesimal_hyperbolic_deadband(0.036)
        transmission_rate_34 = t_34 / 0.034
        transmission_rate_36 = t_36 / 0.036
        assert transmission_rate_34 < 0.10, f"Rate at 0.034 too high: {transmission_rate_34}"
        assert transmission_rate_36 > 0.99, f"Rate at 0.036 too low: {transmission_rate_36}"

    def test_deadband_odd_symmetry(self):
        """f(-z) == -f(z) for arbitrary z."""
        test_points = np.array([-0.5, -0.1, -0.035, -0.01, -0.0003, 0.0, 0.0003, 0.01, 0.035, 0.1, 0.5])
        pos_points = np.abs(test_points)
        f_pos = apply_sexcentoduotrigesimal_hyperbolic_deadband(pos_points)
        f_neg = apply_sexcentoduotrigesimal_hyperbolic_deadband(-pos_points)
        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-15)

    def test_deadband_monotonicity_fine_grid(self):
        """Strict non-decreasing monotonicity across 50,000 points spanning [-1.0, 1.0]."""
        fine_grid = np.linspace(-1.0, 1.0, 50000)
        filtered = apply_sexcentoduotrigesimal_hyperbolic_deadband(fine_grid)
        diffs = np.diff(filtered)
        assert np.all(diffs >= -1e-14), f"Monotonicity violation found: min diff = {diffs.min()}"

    def test_deadband_pandas_series_preservation(self):
        """Preserves index, structure, and handles series with NaNs gracefully."""
        s = pd.Series([0.0001, -0.0002, 0.05, -0.10, 0.0003, 0.0], index=["a", "b", "c", "d", "e", "f"], name="factor")
        out = apply_sexcentoduotrigesimal_hyperbolic_deadband(s)
        assert isinstance(out, pd.Series)
        assert list(out.index) == list(s.index)
        assert out["a"] == 0.0
        assert out["b"] == 0.0
        assert out["e"] == 0.0
        assert out["f"] == 0.0
        assert out["c"] > 0.049
        assert out["d"] < -0.099

    # =========================================================================
    # 2. 137th-Order Rank Modulation Adversarial Tests
    # =========================================================================
    def test_rank_modulation_strict_monotonicity_10000_grid(self):
        """Verify strict monotonicity on [0.0, 1.0] across 10,000 uniformly spaced points."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase103_hyperconvex_rank_modulation(r_grid, gamma_top=41.00)
        diffs = np.diff(g_vals)
        assert np.all(diffs >= -1e-12), f"Monotonicity violated on [0.0, 1.0]: min diff {diffs.min()}"
        assert g_vals[0] == 0.50, f"g(0.0) should be 0.50, got {g_vals[0]}"

    def test_rank_modulation_top_decile_exponential_boost(self):
        """Verify g(1.0) > 10^7 for BULL_LOW_VOL and compare with other regimes."""
        # BULL_LOW_VOL
        gamma_bull = get_regime_adaptive_gamma_top_v103("BULL_LOW_VOL")
        assert gamma_bull == 41.00
        g_bull_1 = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=gamma_bull)
        assert g_bull_1 > 1e7, f"g(1.0) must exceed 10^7: got {g_bull_1}"
        # Theoretical exact: 0.50 + 3.98 * 1.0 * exp(41.0) ≈ 2.54e18
        expected_bull = 0.50 + 3.98 * math.exp(41.00)
        assert math.isclose(g_bull_1, expected_bull, rel_tol=1e-7)

        # BULL_HIGH_VOL (35.40): exp(35.40) ≈ 2.36e15 > 1e7
        gamma_high = get_regime_adaptive_gamma_top_v103("BULL_HIGH_VOL")
        g_high_1 = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=gamma_high)
        assert g_high_1 > 1e7

        # Regime ordering check: g(1.0) under BULL > SIDEWAYS > BEAR > CRISIS
        g_side_1 = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=get_regime_adaptive_gamma_top_v103("SIDEWAYS"))
        g_bear_1 = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=get_regime_adaptive_gamma_top_v103("BEAR"))
        g_crisis_1 = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=get_regime_adaptive_gamma_top_v103("CRISIS"))
        assert g_bull_1 > g_high_1 > g_side_1 > g_bear_1 > g_crisis_1

    def test_rank_modulation_negative_penalty_branch(self):
        """
        Verify negative signal penalty:
        g_neg(r) = 1.35 - 1.00 * r
        Higher rank r leads to severe penalty (g_neg drops from 1.35 to 0.35).
        """
        ranks = np.linspace(0.0, 1.0, 101)
        z_neg = np.full_like(ranks, -0.05)
        g_neg = compute_phase103_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)

        # Strict decreasing monotonicity
        diffs = np.diff(g_neg)
        assert np.all(diffs <= 1e-12), f"Negative penalty must be non-increasing, got diffs {diffs}"
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-6)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-6)

        # Transition at z = 0.0: positive vs negative branch
        g_at_zero = compute_phase103_hyperconvex_rank_modulation(1.0, z_denoised=0.0)
        assert g_at_zero > 1e7  # z >= 0 follows pos_mult
        g_below_zero = compute_phase103_hyperconvex_rank_modulation(1.0, z_denoised=-1e-9)
        assert math.isclose(g_below_zero, 0.35, abs_tol=1e-6)

    def test_rank_modulation_out_of_bounds_handling(self):
        """
        Verify robust clipping to [0.0, 1.0] prevents numerical overflow or NaN.
        r = -10.0 should evaluate identical to r = 0.0 (0.50).
        r = 10.0 should evaluate identical to r = 1.0 (clamped, avoiding exp(41 * 10^137) overflow!).
        """
        g_under = compute_phase103_hyperconvex_rank_modulation(-5.0, gamma_top=41.00)
        assert math.isclose(g_under, 0.50, abs_tol=1e-9)

        # Oversized rank that would trigger float overflow if unclipped:
        g_over = compute_phase103_hyperconvex_rank_modulation(1.5, gamma_top=41.00)
        g_one = compute_phase103_hyperconvex_rank_modulation(1.0, gamma_top=41.00)
        assert math.isclose(g_over, g_one, rel_tol=1e-9)

        # Vector with out-of-bound inputs
        r_oob = np.array([-100.0, -1.0, -0.001, 0.0, 0.5, 1.0, 1.001, 2.0, 50.0])
        g_oob = compute_phase103_hyperconvex_rank_modulation(r_oob, gamma_top=41.00)
        assert np.all(np.isfinite(g_oob))
        assert g_oob[0] == 0.50
        assert g_oob[1] == 0.50
        assert math.isclose(g_oob[-1], g_one, rel_tol=1e-9)

    # =========================================================================
    # 3. Multi-Horizon Monotonicity Regularizer Adversarial Tests
    # =========================================================================
    def test_multi_horizon_monte_carlo_random_inversions(self):
        """
        Monte Carlo stress testing: 1,000 randomized 4-horizon vectors.
        Ensure for 100% of samples, regularized probabilities satisfy:
        p_1d <= p_3d <= p_5d <= p_20d within tolerance.
        """
        np.random.seed(42)
        n_samples = 1000
        rand_probs = np.random.uniform(0.0, 1.0, size=(n_samples, 4))
        df = pd.DataFrame(rand_probs, columns=["surge_1d", "surge_3d", "surge_5d", "surge_20d"])

        # Test both isotonic and cumulative_max modes
        for mode in ["isotonic", "cumulative_max"]:
            reg_df = regularize_multi_horizon_monotonicity(df, mode=mode)
            vals = reg_df[["surge_1d", "surge_3d", "surge_5d", "surge_20d"]].values

            # Verify monotonicity condition: diff across columns >= 0
            diffs = np.diff(vals, axis=1)
            violations = np.sum(diffs < -1e-12)
            assert violations == 0, f"Mode {mode}: Found {violations} monotonicity violations!"

            # Verify probability bounds [0.0, 1.0]
            assert np.all(vals >= 0.0)
            assert np.all(vals <= 1.0)

    def test_multi_horizon_severe_inversions(self):
        """Test specific severe inversion edge cases."""
        severe_cases = [
            [0.9, 0.5, 0.3, 0.1],          # strictly decreasing
            [1.0, 0.0, 0.0, 0.0],          # maximum spike at 1d
            [0.0, 0.0, 0.0, 1.0],          # naturally monotonic
            [0.8, 0.1, 0.9, 0.2],          # zig-zag
            [0.5, 0.5, 0.5, 0.5],          # constant
            [0.0, 0.0, 0.0, 0.0],          # all zero
            [1.0, 1.0, 1.0, 1.0],          # all one
        ]
        df = pd.DataFrame(severe_cases, columns=["surge_1d", "surge_3d", "surge_5d", "surge_20d"])
        reg_df = regularize_multi_horizon_monotonicity(df, mode="isotonic")
        vals = reg_df.values

        for i, row in enumerate(vals):
            assert row[0] <= row[1] + 1e-12, f"Case {i}: 1d ({row[0]}) > 3d ({row[1]})"
            assert row[1] <= row[2] + 1e-12, f"Case {i}: 3d ({row[1]}) > 5d ({row[2]})"
            assert row[2] <= row[3] + 1e-12, f"Case {i}: 5d ({row[2]}) > 20d ({row[3]})"

        # Check that naturally monotonic [0.0, 0.0, 0.0, 1.0] remains unchanged
        np.testing.assert_allclose(vals[2], severe_cases[2], atol=1e-12)
        # Check that constant [0.5, 0.5, 0.5, 0.5] remains unchanged
        np.testing.assert_allclose(vals[4], severe_cases[4], atol=1e-12)

    def test_isotonic_pava_mathematical_properties(self):
        """
        Verify PAVA algorithm mathematical properties:
        1. Projection onto the isotonic cone: sum(y) == sum(x) (mass conservation).
        2. Bounds: min(y) <= min(x) <= max(x) <= max(y).
        3. Monotonicity: x_i <= x_{i+1}.
        """
        np.random.seed(123)
        for _ in range(100):
            y = np.random.randn(8)
            x = isotonic_pava(y)
            # 1. Mass conservation
            assert math.isclose(np.sum(y), np.sum(x), abs_tol=1e-10)
            # 2. Bounds
            assert x.min() >= y.min() - 1e-12
            assert x.max() <= y.max() + 1e-12
            # 3. Monotonicity
            assert np.all(np.diff(x) >= -1e-12)

    def test_multi_horizon_edge_structures(self):
        """Test with empty df, missing horizons, and rows containing NaN."""
        # Empty
        assert regularize_multi_horizon_monotonicity(pd.DataFrame()).empty

        # Missing horizon columns
        df_incomplete = pd.DataFrame({"surge_1d": [0.5], "surge_3d": [0.2]})  # Only 2 columns
        out = regularize_multi_horizon_monotonicity(df_incomplete)
        assert out.loc[0, "surge_1d"] <= out.loc[0, "surge_3d"] + 1e-12

        # Rows with NaN: row with NaN should be skipped without exception
        df_nan = pd.DataFrame({
            "surge_1d": [0.8, np.nan, 0.9],
            "surge_3d": [0.6, 0.2, 0.5],
            "surge_5d": [0.4, 0.3, 0.3],
            "surge_20d": [0.2, 0.4, 0.1],
        })
        out_nan = regularize_multi_horizon_monotonicity(df_nan)
        # Row 0: regularized
        assert out_nan.loc[0, "surge_1d"] <= out_nan.loc[0, "surge_20d"] + 1e-12
        # Row 1: NaN row unchanged
        assert pd.isna(out_nan.loc[1, "surge_1d"])
        # Row 2: regularized
        assert out_nan.loc[2, "surge_1d"] <= out_nan.loc[2, "surge_20d"] + 1e-12

    # =========================================================================
    # 4. Cross-Sectional Ranking Adversarial Tests
    # =========================================================================
    def test_cross_sectional_singleton_groups(self):
        """
        Verify singleton groups (groups with count < 2) fall back to neutral 0.50.
        """
        df_singletons = pd.DataFrame({
            "symbol": ["S1", "S2", "S3"],
            "market": ["M1", "M2", "M3"],  # Each has size 1
            "factor_a": [100.0, -50.0, 0.0],
        })
        out = compute_cross_sectional_relative_rank_features(
            df_singletons,
            feature_cols=["factor_a"],
            group_cols=["market"]
        )
        assert "factor_a_rel_rank" in out.columns
        for val in out["factor_a_rel_rank"]:
            assert math.isclose(val, 0.50, abs_tol=1e-5), f"Singleton should be 0.50, got {val}"

    def test_cross_sectional_all_nan_group(self):
        """
        Verify groups where all values are NaN preserve NaNs without crashing or division by zero.
        """
        df_all_nan = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "market": ["SP500", "SP500", "SP500"],
            "factor_nan": [np.nan, np.nan, np.nan],
        })
        out = compute_cross_sectional_relative_rank_features(
            df_all_nan,
            feature_cols=["factor_nan"],
            group_cols=["market"]
        )
        assert out["factor_nan_rel_rank"].isna().all()

    def test_cross_sectional_identical_value_groups(self):
        """
        Verify groups where all values are identical (zero variance ties).
        Ties are assigned average rank (1.0 for pct=True), scaled into clip_range [0.05, 0.95].
        """
        df_ties = pd.DataFrame({
            "symbol": ["A", "B", "C", "D"],
            "market": ["KOSPI", "KOSPI", "KOSPI", "KOSPI"],
            "flat_val": [42.0, 42.0, 42.0, 42.0],
        })
        out = compute_cross_sectional_relative_rank_features(
            df_ties,
            feature_cols=["flat_val"],
            group_cols=["market"],
            clip_range=(0.05, 0.95)
        )
        ranks = out["flat_val_rel_rank"].values
        # All ranks must be identical and finite
        assert len(set(ranks)) == 1
        assert 0.05 <= ranks[0] <= 0.95

    def test_cross_sectional_mixed_multi_group(self):
        """
        Verify multi-group ranking (market x sector) with mixture of singletons, NaNs, and ties.
        """
        df_complex = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "XOM", "CVX", "SOLO", "GHOST"],
            "market": ["US", "US", "US", "US", "KR", "KR"],
            "sector": ["TECH", "TECH", "ENERGY", "ENERGY", "TECH", "ENERGY"],
            "val": [10.0, 20.0, 5.0, 5.0, 99.0, np.nan]
        })
        out = compute_cross_sectional_relative_rank_features(
            df_complex,
            feature_cols=["val"],
            group_cols=["market", "sector"],
            clip_range=(0.05, 0.95)
        )
        ranks = out.set_index("symbol")["val_rel_rank"]

        # US TECH: AAPL < MSFT
        assert ranks["AAPL"] < ranks["MSFT"]
        # US ENERGY: XOM == CVX (ties)
        assert ranks["XOM"] == ranks["CVX"]
        # KR TECH: SOLO is singleton -> 0.50
        assert math.isclose(ranks["SOLO"], 0.50, abs_tol=1e-5)
        # KR ENERGY: GHOST is NaN -> NaN
        assert pd.isna(ranks["GHOST"])

    # =========================================================================
    # 5. Coupler F486 Adversarial Stress Tests
    # =========================================================================
    def test_coupler_extreme_and_zero_inputs(self):
        """
        Feed extreme inputs (+1000, -1000), uniform inputs, and zero inputs to Coupler v103.
        Verify no Inf/NaN and proper emission of FERI_v103.
        """
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.is_phase103 is True
        assert coupler.kappa_monster_whit == 44.00

        # Extreme values dataframe
        df_extreme = pd.DataFrame({
            "p1": [1000.0, -1000.0, 0.0, 50.0],
            "p2": [-1000.0, 1000.0, 0.0, 50.0],
            "p3": [500.0, -500.0, 0.0, 50.0],
            "p4": [-500.0, 500.0, 0.0, 50.0],
            "p5": [0.0, 0.0, 0.0, 50.0],
        }, index=["ext_pos", "ext_neg", "zeros", "uniform"])

        res = coupler.couple_signals(df_extreme)
        assert isinstance(res, dict)
        for key in ["FERI_v103", "feri_v103", "f_out_103"]:
            assert key in res, f"Expected output key '{key}' missing from coupler response"

        f_vals = res["FERI_v103"]
        if isinstance(f_vals, pd.Series):
            assert np.all(np.isfinite(f_vals.values)), f"Non-finite FERI_v103 found: {f_vals}"
            assert np.all(f_vals.values >= 0.0)
            assert np.all(f_vals.values <= 1.0)
        else:
            assert np.all(np.isfinite(f_vals))
            assert np.all(f_vals >= 0.0)
            assert np.all(f_vals <= 1.0)

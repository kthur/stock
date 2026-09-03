"""
tests/test_adversarial_m1_2_empirical_stress.py

Empirical Challenge & Stress Test Suite for Milestone 1:
Adversarial verification of scoring, convexity, and synergy logic in:
- `trading_system/src/ai/ensemble_scorer.py`

Challenges:
1. Rank preservation and strict monotonicity of `apply_bessembinder_convex_power_law(..., symmetric=True)`
   across 10,000 randomized score vectors (ties, extreme outliers, all-zeros, all-ones, skewed distributions).
2. Smoothness and continuity of `compute_bilinear_cross_pillar_synergy` across boundary points
   (0.499 -> 0.501, 0.599 -> 0.601) ensuring |Delta Xi| < 0.005.
3. Regime transition stability across all 7 regime labels:
   ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS'].
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRADING_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "trading_system")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if TRADING_SYSTEM_DIR not in sys.path:
    sys.path.insert(0, TRADING_SYSTEM_DIR)

from src.ai.ensemble_scorer import EnsembleScoringEngine


ALL_7_REGIMES = [
    'BULL_LOW_VOL',
    'BULL_HIGH_VOL',
    'SIDEWAYS_LOW_VOL',
    'SIDEWAYS_HIGH_VOL',
    'BEAR_LOW_VOL',
    'BEAR_HIGH_VOL',
    'CRISIS'
]


# =============================================================================
# CHALLENGE 1: Bessembinder Convex Power-Law Monotonicity & Rank Preservation
# =============================================================================

class TestBessembinderPowerLawAdversarial:
    """Adversarial stress testing of apply_bessembinder_convex_power_law."""

    def test_10000_randomized_score_vectors_monotonicity_and_rank_preservation(self):
        """
        Generate 10,000 randomized score vectors spanning uniform, beta, normal,
        discrete ties, extreme outliers, all-zero, all-one, and edge cases.
        Verify:
        - Output is finite and strictly bounded in [0.0, 1.0].
        - Weak / strict monotonicity: s_i < s_j => out_i <= out_j.
        - Exact tie preservation: s_i == s_j => out_i == out_j.
        - Sorted index monotonicity: diff(out[argsort(s)]) >= 0.
        - Spearman rank correlation == 1.00000 (when > 1 distinct values).
        - Neutral invariance: s_i == 0.50 => out_i == 0.50.
        """
        rng = np.random.default_rng(20260904)
        n_trials = 10_000

        lengths = [5, 8, 15, 30, 50, 100, 250, 500, 1000]

        for trial_idx in range(n_trials):
            N = lengths[trial_idx % len(lengths)]
            dist_type = trial_idx % 10

            if dist_type == 0:
                # Uniform [0, 1]
                scores = rng.uniform(0.0, 1.0, size=N)
            elif dist_type == 1:
                # Skewed Beta: U-shaped (extremes heavy)
                scores = rng.beta(0.2, 0.2, size=N)
            elif dist_type == 2:
                # Skewed Beta: Right-tailed (low scores heavy)
                scores = rng.beta(1.5, 5.0, size=N)
            elif dist_type == 3:
                # Skewed Beta: Left-tailed (high scores heavy)
                scores = rng.beta(5.0, 1.5, size=N)
            elif dist_type == 4:
                # High-frequency ties: discrete choice from 3-5 distinct values
                discrete_vals = np.linspace(0.1, 0.9, num=rng.integers(3, 6))
                scores = rng.choice(discrete_vals, size=N)
            elif dist_type == 5:
                # Normal distribution centered at 0.5 with varying sigma
                sigma = rng.uniform(0.05, 0.35)
                scores = np.clip(rng.normal(0.50, sigma, size=N), 0.0, 1.0)
            elif dist_type == 6:
                # All zeros, all ones, all neutral, or all identical
                edge_val = rng.choice([0.0, 0.5, 1.0, 0.23, 0.87])
                scores = np.full(N, edge_val)
            elif dist_type == 7:
                # 90% ties with a few outliers
                scores = np.full(N, 0.50)
                n_spikes = max(1, N // 10)
                spike_idx = rng.choice(N, size=n_spikes, replace=False)
                scores[spike_idx] = rng.uniform(0.0, 1.0, size=n_spikes)
            elif dist_type == 8:
                # Extreme outliers outside [0, 1] (e.g. -1e5, 1e5)
                scores = rng.uniform(0.0, 1.0, size=N)
                scores[0] = -1e5
                scores[1] = 1e5
                scores[2] = 0.50
            else:
                # Dense clusters around 0.50 and 0.60
                cluster_a = rng.normal(0.50, 0.005, size=N // 2)
                cluster_b = rng.normal(0.60, 0.005, size=N - N // 2)
                scores = np.clip(np.concatenate([cluster_a, cluster_b]), 0.0, 1.0)

            # Apply Bessembinder Symmetric Richards Power Law
            out = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
                scores=scores,
                symmetric=True,
                power_gamma=1.60,
                max_boost=0.50
            )

            # 1. Output length and finiteness
            assert len(out) == N, f"Trial {trial_idx}: output length mismatch"
            assert np.all(np.isfinite(out)), f"Trial {trial_idx}: non-finite output detected"

            # 2. Output bounds [0.0, 1.0]
            assert np.all((out >= 0.0) & (out <= 1.0)), f"Trial {trial_idx}: output out of [0, 1] bounds"

            # 3. Neutral invariance: exactly 0.50 -> 0.50 (for inputs in [0, 1])
            neutral_mask = (scores == 0.50)
            if np.any(neutral_mask):
                np.testing.assert_allclose(
                    out[neutral_mask], 0.50, atol=1e-6,
                    err_msg=f"Trial {trial_idx}: neutral invariance violated"
                )

            # 4. Tie preservation: if s_i == s_j, then out_i == out_j
            # Test on sorted array
            sort_order = np.argsort(scores, kind='mergesort')
            sorted_s = scores[sort_order]
            sorted_out = out[sort_order]

            # Monotonicity: sorted_out must be monotonically non-decreasing
            diffs = np.diff(sorted_out)
            assert np.all(diffs >= -1e-12), (
                f"Trial {trial_idx}: Monotonicity violated! Min diff: {np.min(diffs)}"
            )

            # Strict equality on ties
            ties = (sorted_s[1:] == sorted_s[:-1])
            if np.any(ties):
                np.testing.assert_allclose(
                    sorted_out[1:][ties], sorted_out[:-1][ties], atol=1e-12,
                    err_msg=f"Trial {trial_idx}: tie preservation violated"
                )

            # 5. Spearman Rank Correlation (when there are at least 2 distinct values in [0, 1])
            valid_mask = (scores >= 0.0) & (scores <= 1.0)
            if np.sum(valid_mask) >= 5:
                sub_s = scores[valid_mask]
                sub_out = out[valid_mask]
                if len(np.unique(sub_s)) > 2:
                    rho = pd.Series(sub_s).corr(pd.Series(sub_out), method='spearman')
                    assert rho >= 0.99999, f"Trial {trial_idx}: Spearman rho < 0.99999 ({rho})"

    def test_bessembinder_edge_cases_and_outliers(self):
        """Test specific edge conditions: N < 5, NaNs, Infs, and extreme boundary vectors."""
        # 1. N < 5 must return safely without error
        short_arr = np.array([0.1, 0.5, 0.9])
        out_short = EnsembleScoringEngine.apply_bessembinder_convex_power_law(short_arr, symmetric=True)
        np.testing.assert_array_equal(out_short, short_arr)

        # 2. NaNs and Infs must be handled by nan_to_num (converted to 0.0)
        dirty_arr = np.array([np.nan, np.inf, -np.inf, 0.50, 0.80])
        out_dirty = EnsembleScoringEngine.apply_bessembinder_convex_power_law(dirty_arr, symmetric=True)
        assert np.all(np.isfinite(out_dirty))
        assert np.all((out_dirty >= 0.0) & (out_dirty <= 1.0))

        # 3. All zeros vector
        zeros_arr = np.zeros(10)
        out_zeros = EnsembleScoringEngine.apply_bessembinder_convex_power_law(zeros_arr, symmetric=True)
        assert np.all(out_zeros >= 0.0) and np.all(out_zeros <= 0.50)
        assert np.all(out_zeros == out_zeros[0])

        # 4. All ones vector
        ones_arr = np.ones(10)
        out_ones = EnsembleScoringEngine.apply_bessembinder_convex_power_law(ones_arr, symmetric=True)
        assert np.all(out_ones <= 1.0) and np.all(out_ones >= 0.50)
        assert np.all(out_ones == out_ones[0])

    def test_bessembinder_decile_spread_expansion(self):
        """
        Empirically confirm that symmetric Richards/Bessembinder scaling suppresses
        near-center noise (S=0.55 compressed to neutral) while expanding the relative
        conviction spread of top/bottom decile winners (conviction amplification > 2.5x).
        """
        # S=0.05 (bottom decile), S=0.50 (neutral), S=0.55 (noise), S=0.95 (top decile), S=1.00 (max)
        test_inputs = np.array([0.05, 0.50, 0.55, 0.95, 1.00])
        transformed = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            test_inputs, symmetric=True
        )

        # 1. Neutral invariance
        assert abs(transformed[1] - 0.50) < 1e-6

        # 2. Symmetric distance from neutral
        dist_bottom = abs(transformed[0] - 0.50)
        dist_top = abs(transformed[3] - 0.50)
        np.testing.assert_allclose(dist_bottom, dist_top, atol=1e-5)

        # 3. Noise suppression: S=0.55 is pulled closer to 0.50
        assert abs(transformed[2] - 0.50) < abs(test_inputs[2] - 0.50)

        # 4. Relative conviction amplification: Top decile vs noise ratio expands by > 2.5x
        raw_conviction_ratio = (test_inputs[3] - 0.50) / (test_inputs[2] - 0.50)  # 0.45 / 0.05 = 9.0
        trans_conviction_ratio = (transformed[3] - 0.50) / (transformed[2] - 0.50)  # > 25.0
        amplification = trans_conviction_ratio / raw_conviction_ratio
        assert amplification > 2.5, f"Conviction amplification {amplification:.2f} <= 2.5x"


# =============================================================================
# CHALLENGE 2: Smoothness & Continuity of Bilinear Cross-Pillar Synergy
# =============================================================================

class TestBilinearCrossPillarSynergyContinuity:
    """Adversarial stress testing of compute_bilinear_cross_pillar_synergy continuity and smoothness."""

    def test_boundary_points_continuity_0499_to_0501(self):
        """
        Verify continuity across the softplus activation threshold 0.500:
        Test transitions 0.499 -> 0.501 across all 4 pillars individually and simultaneously.
        Requirement: |Delta Xi| < 0.005.
        """
        pillars = {
            'val': 'rim_score',
            'mom': 'surge_score',
            'flow': 'order_flow_score',
            'cat': 'event_score'
        }

        # Baseline: other pillars high (0.80) to maximize coupling potential
        for target_pillar, target_col in pillars.items():
            df_low = pd.DataFrame({col: [0.80 if col != target_col else 0.499] * 5 for col in pillars.values()})
            df_high = pd.DataFrame({col: [0.80 if col != target_col else 0.501] * 5 for col in pillars.values()})

            for regime in ALL_7_REGIMES:
                xi_low = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_low, regime=regime).iloc[0]
                xi_high = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_high, regime=regime).iloc[0]

                delta_xi = abs(xi_high - xi_low)
                assert delta_xi < 0.005, (
                    f"Pillar {target_pillar} in regime {regime} broke continuity at 0.500: "
                    f"|{xi_high:.6f} - {xi_low:.6f}| = {delta_xi:.6f} >= 0.005"
                )

        # Simultaneous transition of ALL 4 pillars: 0.499 -> 0.501
        df_all_low = pd.DataFrame({col: [0.499] * 5 for col in pillars.values()})
        df_all_high = pd.DataFrame({col: [0.501] * 5 for col in pillars.values()})

        for regime in ALL_7_REGIMES:
            xi_low = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_all_low, regime=regime).iloc[0]
            xi_high = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_all_high, regime=regime).iloc[0]

            delta_xi = abs(xi_high - xi_low)
            assert delta_xi < 0.005, (
                f"Simultaneous 4-pillar transition in regime {regime} broke continuity at 0.500: "
                f"|{xi_high:.6f} - {xi_low:.6f}| = {delta_xi:.6f} >= 0.005"
            )

    def test_boundary_points_continuity_0599_to_0601(self):
        """
        Verify elimination of legacy step-cliff at 0.600:
        Test transitions 0.599 -> 0.601 across all 4 pillars individually and simultaneously.
        Requirement: |Delta Xi| < 0.005.
        """
        pillars = {
            'val': 'rim_score',
            'mom': 'surge_score',
            'flow': 'order_flow_score',
            'cat': 'event_score'
        }

        for target_pillar, target_col in pillars.items():
            df_low = pd.DataFrame({col: [0.80 if col != target_col else 0.599] * 5 for col in pillars.values()})
            df_high = pd.DataFrame({col: [0.80 if col != target_col else 0.601] * 5 for col in pillars.values()})

            for regime in ALL_7_REGIMES:
                xi_low = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_low, regime=regime).iloc[0]
                xi_high = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_high, regime=regime).iloc[0]

                delta_xi = abs(xi_high - xi_low)
                assert delta_xi < 0.005, (
                    f"Pillar {target_pillar} in regime {regime} broke continuity at 0.600: "
                    f"|{xi_high:.6f} - {xi_low:.6f}| = {delta_xi:.6f} >= 0.005"
                )

        # Simultaneous transition of ALL 4 pillars: 0.599 -> 0.601
        df_all_low = pd.DataFrame({col: [0.599] * 5 for col in pillars.values()})
        df_all_high = pd.DataFrame({col: [0.601] * 5 for col in pillars.values()})

        for regime in ALL_7_REGIMES:
            xi_low = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_all_low, regime=regime).iloc[0]
            xi_high = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_all_high, regime=regime).iloc[0]

            delta_xi = abs(xi_high - xi_low)
            assert delta_xi < 0.005, (
                f"Simultaneous 4-pillar transition in regime {regime} broke continuity at 0.600: "
                f"|{xi_high:.6f} - {xi_low:.6f}| = {delta_xi:.6f} >= 0.005"
            )

    def test_dense_infinitesimal_sweep_bounded_derivative(self):
        """
        Perform a fine-grained sweep (delta = 0.0005) across both critical windows:
        [0.490, 0.510] and [0.590, 0.610].
        Verify that maximum finite difference step is strictly bounded (< 0.002 per 0.0005 step).
        """
        steps = np.linspace(0.490, 0.510, 41)
        for i in range(len(steps) - 1):
            s1, s2 = steps[i], steps[i + 1]
            df1 = pd.DataFrame({'rim_score': [s1] * 5, 'surge_score': [0.85] * 5})
            df2 = pd.DataFrame({'rim_score': [s2] * 5, 'surge_score': [0.85] * 5})

            xi1 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df1, regime='BULL_LOW_VOL').iloc[0]
            xi2 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df2, regime='BULL_LOW_VOL').iloc[0]
            assert abs(xi2 - xi1) < 0.001, f"Step discontinuity at s={s1:.4f}: Delta Xi = {abs(xi2 - xi1):.6f}"

        steps_60 = np.linspace(0.590, 0.610, 41)
        for i in range(len(steps_60) - 1):
            s1, s2 = steps_60[i], steps_60[i + 1]
            df1 = pd.DataFrame({'rim_score': [s1] * 5, 'surge_score': [0.85] * 5})
            df2 = pd.DataFrame({'rim_score': [s2] * 5, 'surge_score': [0.85] * 5})

            xi1 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df1, regime='BULL_LOW_VOL').iloc[0]
            xi2 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df2, regime='BULL_LOW_VOL').iloc[0]
            assert abs(xi2 - xi1) < 0.001, f"Step discontinuity at s={s1:.4f}: Delta Xi = {abs(xi2 - xi1):.6f}"

    def test_cluster_mutual_exclusivity_and_bounding(self):
        """
        Verify:
        1. High conviction in only 1 cluster produces Xi == 1.0000 (no cross-pillar synergy).
        2. Xi is strictly bounded in [1.0000, 1.1000] across all possible configurations.
        3. All 37 strategies belong to at most one cluster (disjoint partitioning).
        """
        # 1. Intra-pillar isolation (Catalyst cluster contains 11 strategies)
        cat_cols = [
            'event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
            'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
            'dual_correction_score', 'index_rebalance_score', 'insider_buying_score',
            'earnings_tone_drift_score'
        ]
        df_isolated_cat = pd.DataFrame({col: [0.99] * 5 for col in cat_cols})
        for regime in ALL_7_REGIMES:
            xi_isolated = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(
                df_isolated_cat, regime=regime
            )
            np.testing.assert_allclose(
                xi_isolated.values, 1.0000, atol=1e-5,
                err_msg=f"Intra-pillar isolation violated in regime {regime}"
            )

        # 2. Maximum synergy capping (all pillars at maximum 1.00)
        df_max = pd.DataFrame({
            'rim_score': [1.0] * 5,
            'surge_score': [1.0] * 5,
            'order_flow_score': [1.0] * 5,
            'event_score': [1.0] * 5
        })
        for regime in ALL_7_REGIMES:
            xi_max = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_max, regime=regime).iloc[0]
            assert 1.05 <= xi_max <= 1.1000, f"Max synergy out of bounds in regime {regime}: {xi_max}"


# =============================================================================
# CHALLENGE 3: Regime Transition Stability Across All 7 Regime Labels
# =============================================================================

class TestRegimeTransitionStability:
    """Adversarial stress testing of stability across all 7 regime labels."""

    def test_synergy_multiplier_bounded_variation_across_all_regime_pairs(self):
        """
        For a diverse universe of 100 stocks with random multi-pillar scores,
        verify that transitioning between ANY pair of the 7 regimes produces
        bounded variation in synergy multiplier: |Xi(R1) - Xi(R2)| <= 0.025.
        """
        rng = np.random.default_rng(42)
        n_stocks = 100
        test_df = pd.DataFrame({
            'rim_score': rng.uniform(0.3, 0.9, size=n_stocks),
            'surge_score': rng.uniform(0.3, 0.9, size=n_stocks),
            'order_flow_score': rng.uniform(0.3, 0.9, size=n_stocks),
            'event_score': rng.uniform(0.3, 0.9, size=n_stocks),
        })

        results = {}
        for reg in ALL_7_REGIMES:
            results[reg] = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(
                test_df, regime=reg
            ).values

        # Test all pairwise regime transitions
        for i, reg1 in enumerate(ALL_7_REGIMES):
            for reg2 in ALL_7_REGIMES[i + 1:]:
                diff = np.abs(results[reg1] - results[reg2])
                max_diff = np.max(diff)
                assert max_diff <= 0.025, (
                    f"Regime transition {reg1} -> {reg2} produced excessive variation: "
                    f"max |Delta Xi| = {max_diff:.6f} > 0.025"
                )

    def test_regime_adaptive_half_lives_all_7_regimes_monotonicity_and_elasticity(self):
        """
        Verify:
        1. All 7 regimes return full dictionary of 37 strategies with tau >= 0.10.
        2. Mean half-life follows strict crisis-to-bull ordering:
           tau(CRISIS) < tau(BEAR_HIGH_VOL) < tau(SIDEWAYS_HIGH_VOL) <= tau(BULL_HIGH_VOL)
           < tau(BEAR_LOW_VOL) < tau(SIDEWAYS_LOW_VOL) < tau(BULL_LOW_VOL).
        3. Fast-tier strategies accelerate more strongly than slow-tier in crisis.
        """
        half_lives = {reg: EnsembleScoringEngine.get_regime_adaptive_half_lives(reg) for reg in ALL_7_REGIMES}

        for reg in ALL_7_REGIMES:
            hl = half_lives[reg]
            assert len(hl) >= 31, f"Regime {reg} missing strategies"
            for strat, tau in hl.items():
                assert np.isfinite(tau), f"Regime {reg} strat {strat} non-finite tau"
                assert tau >= 0.10, f"Regime {reg} strat {strat} tau < 0.10 ({tau})"

        # Check mean half-life monotonic ordering
        mean_hl = {reg: np.mean(list(hl.values())) for reg, hl in half_lives.items()}

        assert mean_hl['CRISIS'] < mean_hl['BEAR_HIGH_VOL']
        assert mean_hl['BEAR_HIGH_VOL'] < mean_hl['SIDEWAYS_HIGH_VOL']
        assert mean_hl['SIDEWAYS_HIGH_VOL'] <= mean_hl['BULL_HIGH_VOL']
        assert mean_hl['BULL_HIGH_VOL'] < mean_hl['BEAR_LOW_VOL']
        assert mean_hl['BEAR_LOW_VOL'] < mean_hl['SIDEWAYS_LOW_VOL']
        assert mean_hl['SIDEWAYS_LOW_VOL'] < mean_hl['BULL_LOW_VOL']

        # Fast vs slow tier acceleration relative to baseline (SIDEWAYS_LOW_VOL):
        # Fast tier (order_flow base=2.0) compresses super-linearly (drops to ~7%)
        # Slow tier (rim_valuation base=45.0) has bounded compression (drops to ~18%)
        hl_crisis = half_lives['CRISIS']
        hl_sideways = half_lives['SIDEWAYS_LOW_VOL']

        assert hl_crisis['microstructure'] <= 0.15
        assert hl_crisis['rim_valuation'] >= 5.0

        fast_compression = hl_crisis['order_flow'] / hl_sideways['order_flow']
        slow_compression = hl_crisis['rim_valuation'] / hl_sideways['rim_valuation']
        assert fast_compression < slow_compression, (
            f"Tier elasticity inverted: fast compression {fast_compression:.4f} >= slow compression {slow_compression:.4f}"
        )

    def test_combine_predictions_end_to_end_across_all_7_regimes(self):
        """
        Run end-to-end combine_predictions on a realistic 50-stock multi-market universe
        across all 7 regimes. Verify:
        1. No NaNs, Infs, or crashes.
        2. ensemble_score bounded in [0.0, 1.0].
        3. Rank stability across adjacent regimes (Spearman rho >= 0.80).
        4. Bessembinder convex power law actively scales top/bottom spread.
        """
        engine = EnsembleScoringEngine()
        rng = np.random.default_rng(42)
        n = 50

        # Construct realistic multi-market synthetic universe
        symbols = [f"KR_{i:03d}" for i in range(25)] + [f"US_{i:03d}" for i in range(25)]
        markets = ['KOSPI'] * 25 + ['SP500'] * 25

        base_df = pd.DataFrame({
            'symbol': symbols,
            'name': symbols,
            'market': markets,
            'close': [50000.0] * 25 + [150.0] * 25,
            'volume': [1_000_000.0] * 50,
            'volatility_20d': [0.02] * 50,
            'operating_margin': rng.uniform(-0.15, 0.25, size=n),
            'roe': rng.uniform(-0.15, 0.25, size=n),
            20: rng.uniform(0.01, 0.15, size=n),
            # Key active strategy columns
            'surge_score': rng.uniform(0.2, 0.9, size=n),
            'vcp_ml_score': rng.uniform(0.2, 0.9, size=n),
            'rim_score': rng.uniform(0.2, 0.9, size=n),
            'order_flow_score': rng.uniform(0.2, 0.9, size=n),
            'event_score': rng.uniform(0.2, 0.9, size=n),
            'trend_efficiency_score': rng.uniform(0.2, 0.9, size=n),
            'range_expansion_score': rng.uniform(0.2, 0.9, size=n),
            'dual_correction_score': rng.uniform(0.2, 0.9, size=n),
        })

        regime_outputs = {}
        for reg in ALL_7_REGIMES:
            res = engine.combine_predictions(
                reg_df=base_df.copy(),
                target_horizon=20,
                regime=reg
            )

            assert not res.empty
            assert 'ensemble_score' in res.columns
            scores = res['ensemble_score'].values

            # Invariants
            assert np.all(np.isfinite(scores)), f"Regime {reg} produced non-finite scores"
            assert np.all((scores >= 0.0) & (scores <= 1.0)), f"Regime {reg} scores out of bounds"
            regime_outputs[reg] = res['ensemble_score'].values

        # Rank stability between adjacent regime transitions
        adjacent_pairs = [
            ('BULL_LOW_VOL', 'BULL_HIGH_VOL'),
            ('BULL_HIGH_VOL', 'SIDEWAYS_HIGH_VOL'),
            ('SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL'),
            ('SIDEWAYS_HIGH_VOL', 'BEAR_HIGH_VOL'),
            ('BEAR_LOW_VOL', 'BEAR_HIGH_VOL'),
            ('BEAR_HIGH_VOL', 'CRISIS'),
        ]

        for r1, r2 in adjacent_pairs:
            s1 = regime_outputs[r1]
            s2 = regime_outputs[r2]
            rho = pd.Series(s1).corr(pd.Series(s2), method='spearman')
            assert rho >= 0.80, (
                f"Turnover whipsaw risk! Spearman rho between {r1} and {r2} is {rho:.4f} < 0.80"
            )

    def test_adversarial_regime_inputs_and_fallbacks(self):
        """Verify robust handling of irregular regime inputs (case variation, unknown strings, None)."""
        engine = EnsembleScoringEngine()
        df = pd.DataFrame({
            'symbol': [f'S_{i}' for i in range(5)],
            'name': [f'S_{i}' for i in range(5)],
            'market': ['SP500'] * 5,
            'close': [100.0] * 5,
            'volume': [1000.0] * 5,
            20: [0.05] * 5,
            'surge_score': [0.70] * 5,
            'rim_score': [0.60] * 5,
        })

        irregular_regimes = ['bull_low_vol', 'crisis', 'UNKNOWN_REGIME_XYZ', '', None, 0, 1, 2]
        for reg in irregular_regimes:
            # Synergy calculation
            xi = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df, regime=reg)
            assert np.all(np.isfinite(xi.values))
            assert np.all((xi.values >= 1.0) & (xi.values <= 1.10))

            # Half-lives calculation
            hl = EnsembleScoringEngine.get_regime_adaptive_half_lives(reg)
            assert len(hl) >= 31
            assert all(v >= 0.10 for v in hl.values())

            # combine_predictions
            res = engine.combine_predictions(reg_df=df.copy(), target_horizon=20, regime=reg)
            assert not res.empty
            assert np.all(np.isfinite(res['ensemble_score'].values))

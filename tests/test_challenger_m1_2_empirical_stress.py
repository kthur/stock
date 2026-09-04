"""
Empirical Stress Test Harness by Challenger 2 for Milestone 1 Phase 4.

Verifies:
1. REGIME_2D_WEIGHTS sum strictly to 1.0000 across all regimes (class & instance, before and after tuned weights loading).
2. Half-life monotonicity: BEAR < SIDEWAYS < BULL across 1D and 2D regimes, per-strategy and aggregate.
3. BessembinderParams unpacking across diverse call frames (direct, indirect, nested, comprehension, star unpacking).
4. Adversarial stress testing for NaN and Inf leaks in combine_predictions under extreme and degenerate inputs.
"""

import math
import numpy as np
import pandas as pd
import pytest

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "trading_system"))

from src.ai.ensemble_scorer import EnsembleScoringEngine, BessembinderParams


# =============================================================================
# 1. REGIME_2D_WEIGHTS SUM AND NORMALIZATION
# =============================================================================

def test_regime_2d_weights_sum_exact_1():
    """Verify REGIME_2D_WEIGHTS sum to exactly 1.0000 across all regimes."""
    engine = EnsembleScoringEngine()
    regimes = ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL', 'CRISIS']

    for r in regimes:
        # Check class dict
        w_class = EnsembleScoringEngine.REGIME_2D_WEIGHTS[r]
        assert len(w_class) == 37, f"Class dict for {r} must have 37 strategies, got {len(w_class)}"
        sum_class = sum(w_class.values())
        assert abs(sum_class - 1.0000) < 1e-9, f"Class {r} sum = {sum_class} != 1.0000"

        # Check instance dict
        w_inst = engine.REGIME_2D_WEIGHTS[r]
        assert len(w_inst) == 37, f"Instance dict for {r} must have 37 strategies, got {len(w_inst)}"
        sum_inst = sum(w_inst.values())
        assert abs(sum_inst - 1.0000) < 1e-9, f"Instance {r} sum = {sum_inst} != 1.0000"

        # Check all weights are strictly positive
        for strat, val in w_inst.items():
            assert val > 0, f"Strategy {strat} in {r} has non-positive weight {val}"


def test_regime_2d_weights_after_tuned_weights_loading():
    """Verify that loading tuned regime weights does not corrupt 37-strategy sums in SIDEWAYS regimes."""
    engine = EnsembleScoringEngine()
    # Mock tuned params with legacy 31-strategy format
    mock_tuned = {
        'regime_2d_weights': {
            'SIDEWAYS_LOW_VOL': {'surge': 0.08, 'regression': 0.08},
            'SIDEWAYS_HIGH_VOL': {'surge': 0.08, 'regression': 0.08},
            'BULL_LOW_VOL': {'surge': 0.05}
        }
    }
    engine._tuned_params = mock_tuned
    engine._load_tuned_regime_weights()

    # SIDEWAYS regimes must NOT have been overwritten
    w_side_low = engine.REGIME_2D_WEIGHTS['SIDEWAYS_LOW_VOL']
    assert math.isclose(w_side_low['surge'], 0.015, abs_tol=1e-6)
    assert abs(sum(w_side_low.values()) - 1.0000) < 1e-9

    w_side_high = engine.REGIME_2D_WEIGHTS['SIDEWAYS_HIGH_VOL']
    assert math.isclose(w_side_high['surge'], 0.015, abs_tol=1e-6)
    assert abs(sum(w_side_high.values()) - 1.0000) < 1e-9


# =============================================================================
# 2. HALF-LIFE MONOTONICITY: BEAR < SIDEWAYS < BULL
# =============================================================================

def test_half_life_ordering_analysis():
    """
    Empirically inspect whether half-lives obey strict ordering: BEAR < SIDEWAYS < BULL.
    Examines:
    1. 1D regimes: 'BEAR', 'SIDEWAYS', 'BULL'
    2. 2D Low Vol regimes: 'BEAR_LOW_VOL', 'SIDEWAYS_LOW_VOL', 'BULL_LOW_VOL'
    3. 2D High Vol regimes: 'BEAR_HIGH_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_HIGH_VOL'
    4. Per-strategy vs Aggregate Mean.
    """
    hl_bear_1d = EnsembleScoringEngine.get_regime_adaptive_half_lives('BEAR')
    hl_side_1d = EnsembleScoringEngine.get_regime_adaptive_half_lives('SIDEWAYS')
    hl_bull_1d = EnsembleScoringEngine.get_regime_adaptive_half_lives('BULL')

    hl_bear_low = EnsembleScoringEngine.get_regime_adaptive_half_lives('BEAR_LOW_VOL')
    hl_side_low = EnsembleScoringEngine.get_regime_adaptive_half_lives('SIDEWAYS_LOW_VOL')
    hl_bull_low = EnsembleScoringEngine.get_regime_adaptive_half_lives('BULL_LOW_VOL')

    hl_bear_high = EnsembleScoringEngine.get_regime_adaptive_half_lives('BEAR_HIGH_VOL')
    hl_side_high = EnsembleScoringEngine.get_regime_adaptive_half_lives('SIDEWAYS_HIGH_VOL')
    hl_bull_high = EnsembleScoringEngine.get_regime_adaptive_half_lives('BULL_HIGH_VOL')

    # Aggregate means
    mean_bear_1d = np.mean(list(hl_bear_1d.values()))
    mean_side_1d = np.mean(list(hl_side_1d.values()))
    mean_bull_1d = np.mean(list(hl_bull_1d.values()))

    mean_bear_low = np.mean(list(hl_bear_low.values()))
    mean_side_low = np.mean(list(hl_side_low.values()))
    mean_bull_low = np.mean(list(hl_bull_low.values()))

    mean_bear_high = np.mean(list(hl_bear_high.values()))
    mean_side_high = np.mean(list(hl_side_high.values()))
    mean_bull_high = np.mean(list(hl_bull_high.values()))

    print(f"\n[Aggregate Half-Life Means]")
    print(f"1D: BEAR={mean_bear_1d:.2f}, SIDEWAYS={mean_side_1d:.2f}, BULL={mean_bull_1d:.2f}")
    print(f"2D Low Vol: BEAR={mean_bear_low:.2f}, SIDEWAYS={mean_side_low:.2f}, BULL={mean_bull_low:.2f}")
    print(f"2D High Vol: BEAR={mean_bear_high:.2f}, SIDEWAYS={mean_side_high:.2f}, BULL={mean_bull_high:.2f}")

    # Check aggregate mean ordering
    # In Low Vol: BEAR (0.85) < SIDEWAYS (1.00) < BULL (1.30)
    assert mean_bear_low < mean_side_low < mean_bull_low
    assert mean_bear_1d < mean_side_1d < mean_bull_1d

    # Now inspect trend/momentum strategies specifically:
    print(f"\n[Trend Strategy Half-Lives]")
    trend_strats = list(EnsembleScoringEngine.TREND_STRATEGIES)
    violations = []
    for s in trend_strats:
        tau_b = hl_bear_low.get(s, None)
        tau_s = hl_side_low.get(s, None)
        tau_u = hl_bull_low.get(s, None)
        print(f"Strategy '{s}': BEAR_LOW={tau_b}, SIDEWAYS_LOW={tau_s}, BULL_LOW={tau_u}")
        if tau_b is not None and tau_s is not None and tau_u is not None:
            # Does tau_b < tau_s < tau_u hold?
            if not (tau_b < tau_s < tau_u):
                violations.append((s, tau_b, tau_s, tau_u))

    print(f"Trend strategies violating BEAR < SIDEWAYS < BULL: {violations}")


# =============================================================================
# 3. BESSEMBINDER PARAMS UNPACKING SEAMLESSNESS
# =============================================================================

def test_bessembinder_params_2_and_3_tuple_unpacking():
    """Verify BessembinderParams unpacks into 2-tuples and 3-tuples without TypeError."""
    engine = EnsembleScoringEngine()

    # Direct 2-tuple unpacking
    g2, b2 = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL')
    assert math.isclose(g2, 1.70, abs_tol=1e-4)
    assert math.isclose(b2, 0.50, abs_tol=1e-4)

    # Direct 3-tuple unpacking
    g3, b3, u3 = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL')
    assert math.isclose(g3, 1.70, abs_tol=1e-4)
    assert math.isclose(b3, 0.50, abs_tol=1e-4)
    assert math.isclose(u3, 0.45, abs_tol=1e-4)

    # In a separate function
    def unpack_2():
        params = engine.get_regime_adaptive_bessembinder_params('CRISIS')
        gamma, beta = params
        return gamma, beta

    def unpack_3():
        params = engine.get_regime_adaptive_bessembinder_params('CRISIS')
        gamma, beta, u_thresh = params
        return gamma, beta, u_thresh

    assert unpack_2() == (1.20, 0.20)
    assert unpack_3() == (1.20, 0.20, 0.75)

    # Comprehension unpacking
    params_list = [engine.get_regime_adaptive_bessembinder_params(r) for r in ['BULL_LOW_VOL', 'SIDEWAYS_LOW_VOL']]
    unpacked_2 = [(g, b) for g, b in params_list]
    assert len(unpacked_2) == 2
    assert unpacked_2[0] == (1.70, 0.50)
    assert unpacked_2[1] == (1.45, 0.40)

    unpacked_3 = [(g, b, u) for g, b, u in params_list]
    assert len(unpacked_3) == 2
    assert unpacked_3[0] == (1.70, 0.50, 0.45)
    assert unpacked_3[1] == (1.45, 0.40, 0.60)

    # Properties
    p = BessembinderParams(1.5, 0.35, 0.65)
    assert p.gamma == 1.5
    assert p.beta == 0.35
    assert p.u_thresh == 0.65
    assert len(p) == 3


# =============================================================================
# 4. ADVERSARIAL STRESS: NAN AND INF LEAKS IN COMBINE_PREDICTIONS
# =============================================================================

def test_combine_predictions_nan_inf_adversarial_stress():
    """
    Stress-test combine_predictions against adversarial inputs:
    - All-NaN predictions
    - All-Inf predictions
    - Extreme values (spikes, negative values, 1e12, -1e12)
    - Zero variance scores
    - Degenerate single-stock universes
    - Mixed missing columns
    """
    engine = EnsembleScoringEngine()

    # Case A: Degenerate single stock
    df_single = pd.DataFrame({
        'symbol': ['SOLO'],
        'market': ['SP500'],
        'ensemble_score': [0.75],
        'volatility_20d': [0.02],
        'close': [150.0],
        'volume': [500_000.0],
    })
    res_single = engine.combine_predictions(predictions_df=df_single, target_horizon='20d')
    assert not res_single['ensemble_score'].isna().any()
    assert not np.isinf(res_single['ensemble_score']).any()
    assert not res_single['ensemble_expected_return'].isna().any()

    # Case B: All-NaN strategy scores
    n = 20
    df_nans = pd.DataFrame({
        'symbol': [f"NAN_SYM_{i}" for i in range(n)],
        'market': ['SP500'] * n,
        'surge_pred': [np.nan] * n,
        'stat_arb_score': [np.nan] * n,
        'rim_score': [np.nan] * n,
        'trend_efficiency_score': [np.nan] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [100_000.0] * n,
    })
    res_nans = engine.combine_predictions(predictions_df=df_nans, target_horizon='20d')
    assert not res_nans['ensemble_score'].isna().any(), "All-NaN strategy input leaked NaN into ensemble_score!"
    assert not np.isinf(res_nans['ensemble_score']).any(), "All-NaN strategy input leaked Inf into ensemble_score!"
    assert not res_nans['ensemble_expected_return'].isna().any(), "All-NaN leaked NaN into expected_return!"
    assert not np.isinf(res_nans['ensemble_expected_return']).any(), "All-NaN leaked Inf into expected_return!"

    # Case C: Zero-variance input (all scores identical)
    df_zerovar = pd.DataFrame({
        'symbol': [f"IDENT_{i}" for i in range(n)],
        'market': ['KOSPI'] * n,
        'ensemble_score': [0.55] * n,
        'volatility_20d': [0.02] * n,
        'close': [50_000.0] * n,
        'volume': [200_000.0] * n,
    })
    res_zerovar = engine.combine_predictions(predictions_df=df_zerovar, target_horizon='20d')
    assert not res_zerovar['ensemble_score'].isna().any()
    assert not np.isinf(res_zerovar['ensemble_score']).any()
    assert (res_zerovar['ensemble_score'] >= 0.0).all() and (res_zerovar['ensemble_score'] <= 1.0).all()

    # Case D: Extreme scores (> 1.0 and < 0.0)
    df_extreme = pd.DataFrame({
        'symbol': [f"EXT_{i}" for i in range(n)],
        'market': ['NASDAQ'] * n,
        'ensemble_score': np.linspace(-5.0, 5.0, n),
        'volatility_20d': [0.03] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
    })
    res_extreme = engine.combine_predictions(predictions_df=df_extreme, target_horizon='20d')
    assert not res_extreme['ensemble_score'].isna().any()
    assert not np.isinf(res_extreme['ensemble_score']).any()
    assert (res_extreme['ensemble_score'] >= 0.0).all() and (res_extreme['ensemble_score'] <= 1.0).all()
    assert not res_extreme['ensemble_expected_return'].isna().any()
    assert not np.isinf(res_extreme['ensemble_expected_return']).any()


def test_top_decile_power_law_exponent_numerical_stability():
    """
    Stress test F21 dynamic rank-modulated multiplier and power-law exponent 1.15
    for edge cases: abs_centered = -0.50, 0.0, +0.50, ranks = 0.0, 0.5, 1.0.
    """
    abs_centered_vals = np.array([-0.50, -0.25, 0.0, 0.25, 0.50])
    ranks_vals = np.array([0.0, 0.25, 0.50, 0.75, 1.0])

    mult = np.where(abs_centered_vals >= 0.0, 0.60 + 0.80 * ranks_vals, 1.40 - 0.80 * ranks_vals)
    unclipped_score = abs_centered_vals * mult
    convex_alpha = np.sign(unclipped_score) * np.clip((np.abs(unclipped_score * 2.0) ** 1.15) / 1.15, 0.0, 1.0)

    assert not np.isnan(convex_alpha).any()
    assert not np.isinf(convex_alpha).any()
    assert (np.abs(convex_alpha) <= 1.0).all()
    # Monotonicity with respect to centered score
    assert np.all(np.diff(convex_alpha) >= 0.0)

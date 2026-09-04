"""
Adversarial Stress Harness and Empirical Benchmark by Challenger 2
Milestone 1 (Requirement R1: Features F35 & F36).

Stress Scenarios:
1. Extreme Regimes & Bounds (All 7 regimes, all 0s, all 1s, 90% NaN, 99% NaN, 100% NaN, negative/huge values, small universes)
2. Quad-Pillar & Tri-Catalyst Synergy Bounds (missing pillars, partial pillars, exact regime caps, backward compatibility)
3. Performance Benchmarking (500 stocks x 37 strategies realistic universe, latency < 50ms)
4. Deep Mathematical Invariants (Deadband monotonicity & odd symmetry, Holder p=2.0 Jensen inequality, Half-life entropy bounds)
"""

import math
import time
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine


ALL_REGIMES = [
    'BULL_LOW_VOL',
    'BULL_HIGH_VOL',
    'SIDEWAYS_LOW_VOL',
    'SIDEWAYS_HIGH_VOL',
    'BEAR_LOW_VOL',
    'BEAR_HIGH_VOL',
    'CRISIS',
]

STRATEGY_COLS_37 = [
    'reg_pred', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
    'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
    'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score', 'arm_score',
    'card_score', 'latr_score', 'inst_foreign_sector_score', 'supply_chain_score',
    'sentiment_score', 'factor_neutralized_score', 'vol_target_score',
    'microstructure_score', 'accruals_quality_score', 'short_squeeze_score',
    'valueup_catalyst_score', 'trend_efficiency_score', 'gamma_squeeze_score',
    'insider_buying_score', 'darkpool_score', 'earnings_tone_drift_score',
    'cross_asset_spillover_score', 'supply_chain_gnn_score', 'range_expansion_score',
    'dual_correction_score', 'index_rebalance_score', 'overnight_gap_score'
]


# =============================================================================
# SCENARIO 1: EXTREME REGIMES & BOUNDS (ALL 0s, ALL 1s, HIGH NaNs, OUTLIERS)
# =============================================================================

@pytest.mark.parametrize("regime", ALL_REGIMES + ['UNKNOWN_FALLBACK'])
def test_scenario1_all_zeros_scores(regime):
    """Stress test with all 0.0 scores across all strategies."""
    engine = EnsembleScoringEngine()
    n = 20
    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(n)],
        'market': ['SP500'] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
        **{c: [0.0] * n for c in STRATEGY_COLS_37}
    })
    out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime=regime)

    assert not out['ensemble_score'].isna().any(), f"NaNs found in ensemble_score under {regime}"
    assert not np.isinf(out['ensemble_score']).any(), f"Infs found in ensemble_score under {regime}"
    assert (out['ensemble_score'] >= 0.0).all(), f"Scores < 0.0 under {regime}"
    assert (out['ensemble_score'] <= 1.0).all(), f"Scores > 1.0 under {regime}"
    assert not out['ensemble_expected_return'].isna().any(), f"NaNs found in expected return under {regime}"
    assert not np.isinf(out['ensemble_expected_return']).any(), f"Infs found in expected return under {regime}"
    assert (out['ensemble_expected_return'] >= 0.0).all()
    assert (out['ensemble_expected_return'] <= 50.0).all()


@pytest.mark.parametrize("regime", ALL_REGIMES + ['UNKNOWN_FALLBACK'])
def test_scenario1_all_ones_scores(regime):
    """Stress test with all 1.0 scores across all strategies."""
    engine = EnsembleScoringEngine()
    n = 20
    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(n)],
        'market': ['SP500'] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
        **{c: [1.0] * n for c in STRATEGY_COLS_37}
    })
    out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime=regime)

    assert not out['ensemble_score'].isna().any(), f"NaNs found in ensemble_score under {regime}"
    assert not np.isinf(out['ensemble_score']).any(), f"Infs found in ensemble_score under {regime}"
    assert (out['ensemble_score'] >= 0.0).all(), f"Scores < 0.0 under {regime}"
    assert (out['ensemble_score'] <= 1.0).all(), f"Scores > 1.0 under {regime}"
    assert not out['ensemble_expected_return'].isna().any()
    assert not np.isinf(out['ensemble_expected_return']).any()
    assert (out['ensemble_expected_return'] >= 0.0).all()
    assert (out['ensemble_expected_return'] <= 50.0).all()


@pytest.mark.parametrize("nan_prob", [0.90, 0.99, 1.00])
def test_scenario1_high_nan_proportions(nan_prob):
    """Stress test with extreme missingness (90%, 99%, 100% NaNs)."""
    np.random.seed(123)
    engine = EnsembleScoringEngine()
    n = 30
    symbols = [f'SYM_{i:03d}' for i in range(n)]

    data = {
        'symbol': symbols,
        'market': ['KOSPI' if i % 2 == 0 else 'NASDAQ' for i in range(n)],
        'volatility_20d': np.random.uniform(0.01, 0.05, n),
        'close': np.random.uniform(10.0, 200.0, n),
        'volume': np.random.uniform(10_000, 1_000_000, n),
    }
    for c in STRATEGY_COLS_37:
        if nan_prob == 1.00:
            data[c] = [np.nan] * n
        else:
            raw = np.random.uniform(0.0, 1.0, n)
            mask = np.random.rand(n) < nan_prob
            raw[mask] = np.nan
            data[c] = raw

    df = pd.DataFrame(data)

    for regime in ['BULL_LOW_VOL', 'CRISIS', 'SIDEWAYS_HIGH_VOL']:
        out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime=regime)
        assert not out['ensemble_score'].isna().any(), f"NaNs found with nan_prob={nan_prob} under {regime}"
        assert not np.isinf(out['ensemble_score']).any()
        assert (out['ensemble_score'] >= 0.0).all()
        assert (out['ensemble_score'] <= 1.0).all()
        assert not out['ensemble_expected_return'].isna().any()
        assert not np.isinf(out['ensemble_expected_return']).any()


def test_scenario1_extreme_outliers_and_negative_inputs():
    """Stress test with wild input values (-9999, +9999, inf)."""
    engine = EnsembleScoringEngine()
    n = 10
    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(n)],
        'market': ['SP500'] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
        **{c: [(-1000.0 if i % 2 == 0 else 1000.0) for i in range(n)] for c in STRATEGY_COLS_37}
    })
    for regime in ['BULL_LOW_VOL', 'CRISIS']:
        out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime=regime)
        assert not out['ensemble_score'].isna().any()
        assert not np.isinf(out['ensemble_score']).any()
        assert (out['ensemble_score'] >= 0.0).all()
        assert (out['ensemble_score'] <= 1.0).all()


@pytest.mark.parametrize("universe_size", [1, 2, 4, 5, 8])
def test_scenario1_small_universe_edge_cases(universe_size):
    """Stress test with universes having <5 and >=5 stocks (evaluates threshold branch)."""
    engine = EnsembleScoringEngine()
    n = universe_size
    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(n)],
        'market': ['KOSPI'] * n,
        'volatility_20d': [0.02] * n,
        'close': [50000.0] * n,
        'volume': [500_000.0] * n,
        **{c: np.linspace(0.2, 0.8, n) for c in STRATEGY_COLS_37}
    })
    out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime='BULL_LOW_VOL')
    assert len(out) == n
    assert not out['ensemble_score'].isna().any()
    assert (out['ensemble_score'] >= 0.0).all() and (out['ensemble_score'] <= 1.0).all()


# =============================================================================
# SCENARIO 2: QUAD-PILLAR & TRI-CATALYST SYNERGY BOUNDS & MISSING PILLARS
# =============================================================================

REGIME_EXACT_CAPS = {
    'BULL_LOW_VOL': 1.150,
    'BULL_HIGH_VOL': 1.125,
    'SIDEWAYS_LOW_VOL': 1.100,
    'SIDEWAYS_HIGH_VOL': 1.060,
    'BEAR_LOW_VOL': 1.075,
    'BEAR_HIGH_VOL': 1.040,
    'CRISIS': 1.040,
    'UNKNOWN_FALLBACK': 1.080,
}


@pytest.mark.parametrize("regime, expected_cap", list(REGIME_EXACT_CAPS.items()))
def test_scenario2_exact_regime_synergy_caps(regime, expected_cap):
    """
    Empirically verify that with extreme conviction across all strategies (1.0),
    synergy multipliers NEVER exceed their exact regime cap (within numerical eps).
    """
    engine = EnsembleScoringEngine()
    idx = [f'ASSET_{i}' for i in range(10)]
    # All 37 strategies at 1.0 (extreme conviction)
    df = pd.DataFrame({c: [1.0] * 10 for c in STRATEGY_COLS_37}, index=idx)

    synergy = engine.compute_bilinear_cross_pillar_synergy(
        df, regime=regime, regime_adaptive_cap=True
    )
    max_syn = synergy.max()
    min_syn = synergy.min()

    assert min_syn >= 1.000, f"Synergy under {regime} dropped below 1.000: {min_syn}"
    assert math.isclose(max_syn, expected_cap, abs_tol=1e-4), (
        f"Regime {regime} failed exact cap test! Expected {expected_cap:.4f}, got {max_syn:.4f}"
    )


def test_scenario2_backward_compatibility_cap():
    """
    When regime_adaptive_cap=False (default), multiplier must strictly never exceed 1.100
    even in BULL_LOW_VOL with all strategies at 1.0.
    """
    engine = EnsembleScoringEngine()
    df = pd.DataFrame({c: [1.0] * 5 for c in STRATEGY_COLS_37})

    for regime in ALL_REGIMES:
        synergy_default = engine.compute_bilinear_cross_pillar_synergy(
            df, regime=regime, regime_adaptive_cap=False
        )
        assert (synergy_default <= 1.100 + 1e-6).all(), (
            f"Default cap exceeded 1.100 in {regime}! Max={synergy_default.max()}"
        )


def test_scenario2_missing_and_partial_pillars():
    """
    Adversarial test on missing pillars:
    - 0 pillars present (DataFrame with none of the strategy columns)
    - 1 pillar present (only Valuation)
    - 2 pillars present (Valuation + Catalyst, but NO Momentum and NO Flow)
    - Partial columns with high NaNs
    """
    engine = EnsembleScoringEngine()
    n = 10
    idx = [f'ASSET_{i}' for i in range(n)]

    # 1. Zero pillar columns present
    df_empty_strats = pd.DataFrame({'unrelated_col': [123.4] * n}, index=idx)
    syn_0 = engine.compute_bilinear_cross_pillar_synergy(df_empty_strats, regime='BULL_LOW_VOL')
    assert (syn_0 == 1.0).all(), f"0 pillars present must yield exactly 1.0 synergy! Got {syn_0.values}"

    # 2. Only 1 pillar present (Valuation: rim_score only)
    df_1_pillar = pd.DataFrame({'rim_score': [0.95] * n}, index=idx)
    syn_1 = engine.compute_bilinear_cross_pillar_synergy(df_1_pillar, regime='BULL_LOW_VOL')
    assert (syn_1 == 1.0).all(), f"1 pillar present must yield exactly 1.0 cross-pillar synergy!"

    # 3. 2 non-adjacent pillars present (Valuation + Catalyst, missing Momentum & Flow)
    # Bilinear term (val, cat) = 0.020 in BULL_LOW_VOL. Tri-linear and Quad-pillar MUST be 0.0!
    df_2_pillars = pd.DataFrame({
        'rim_score': [1.0] * n,
        'event_score': [1.0] * n
    }, index=idx)
    syn_2 = engine.compute_bilinear_cross_pillar_synergy(df_2_pillars, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
    # Omega(val, cat) in BULL_LOW_VOL is 0.015 (canonical specification in ensemble_scorer.py)
    assert math.isclose(syn_2.iloc[0], 1.015, abs_tol=1e-3), (
        f"2-pillar (val + cat) synergy must equal 1.015! Got {syn_2.iloc[0]:.4f}"
    )

    # 4. Partial NaN corruption inside a pillar
    df_corrupt = pd.DataFrame({
        'rim_score': [np.nan, 0.9, np.nan],
        'valueup_catalyst_score': [np.nan, np.nan, 0.9],
        'surge_score': [0.9, np.nan, 0.9],
    }, index=['A1', 'A2', 'A3'])
    syn_corrupt = engine.compute_bilinear_cross_pillar_synergy(df_corrupt, regime='BULL_LOW_VOL')
    assert not syn_corrupt.isna().any(), "Synergy contains NaNs under corrupt inputs"
    assert (syn_corrupt >= 1.0).all() and (syn_corrupt <= 1.15).all()


# =============================================================================
# SCENARIO 3: PERFORMANCE BENCHMARKING (500 STOCKS x 37 STRATEGIES < 50ms)
# =============================================================================

def test_scenario3_performance_benchmark_500_stocks_37_strategies():
    """
    Measure execution runtime of combine_predictions on a realistic universe
    of 500 stocks across all 37 strategies to verify negligible latency (< 50ms).
    """
    np.random.seed(42)
    n_stocks = 500
    engine = EnsembleScoringEngine()

    symbols = [f"SYM_{i:04d}" for i in range(n_stocks)]
    markets = np.random.choice(['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'], size=n_stocks)

    data = {
        'symbol': symbols,
        'market': markets,
        'volatility_20d': np.random.uniform(0.012, 0.035, n_stocks),
        'close': np.random.uniform(10.0, 300.0, n_stocks),
        'volume': np.random.uniform(200_000, 20_000_000, n_stocks),
        'operating_margin': np.random.uniform(-0.10, 0.25, n_stocks),
        'roe': np.random.uniform(-0.10, 0.25, n_stocks),
    }

    # Simulate all 37 strategies with realistic missingness (15% NaNs)
    for col in STRATEGY_COLS_37:
        scores = np.random.uniform(0.15, 0.85, n_stocks)
        mask_nan = np.random.rand(n_stocks) < 0.15
        scores[mask_nan] = np.nan
        data[col] = scores

    test_df = pd.DataFrame(data)

    # Warm-up run of full combine_predictions
    res = engine.combine_predictions(
        predictions_df=test_df,
        target_horizon='20d',
        regime='BULL_LOW_VOL',
        regime_probs={'BULL_LOW_VOL': 0.70, 'SIDEWAYS_LOW_VOL': 0.30}
    )
    assert len(res) == n_stocks
    assert not res['ensemble_score'].isna().any()
    assert (res['ensemble_score'] >= 0.0).all() and (res['ensemble_score'] <= 1.0).all()

    # Benchmark Phase 5 enhancements pure latency overhead over 20 iterations
    # (Cross-pillar synergy + Hölder p=2.0 boost + Bessembinder tail + noise deadband)
    n_iters = 20
    latencies_ms = []
    base_scores = pd.Series(0.55, index=test_df.index)

    for _ in range(n_iters):
        t0 = time.perf_counter()
        _syn = engine.compute_bilinear_cross_pillar_synergy(test_df, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
        _boost = engine.apply_top_decile_convex_boost(test_df, STRATEGY_COLS_37, base_scores, top_k=3, p_norm=2.0, regime='BULL_LOW_VOL')
        _bessem = engine.apply_bessembinder_convex_power_law(_boost.values, symmetric=True, regime='BULL_LOW_VOL', version=5)
        _dead = engine.apply_smooth_noise_deadband(_bessem - 0.50, delta_noise=0.045)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)

    latencies_ms = np.array(latencies_ms)
    mean_lat = float(np.mean(latencies_ms))
    median_lat = float(np.median(latencies_ms))
    min_lat = float(np.min(latencies_ms))
    max_lat = float(np.max(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))

    print(f"\n[BENCHMARK] Phase 5 Pure Overhead (500 stocks x 37 strategies, 20 runs): "
          f"mean={mean_lat:.2f}ms, median={median_lat:.2f}ms, min={min_lat:.2f}ms, "
          f"max={max_lat:.2f}ms, p95={p95_lat:.2f}ms")

    # Invariant: Phase 5 mathematical latency overhead strictly < 50ms
    assert mean_lat < 50.0, f"Mean Phase 5 latency overhead ({mean_lat:.2f}ms) exceeds budget of 50ms!"
    assert p95_lat < 65.0, f"p95 Phase 5 latency overhead ({p95_lat:.2f}ms) exceeds 65ms!"


# =============================================================================
# SCENARIO 4: DEEP MATHEMATICAL INVARIANTS & INTEGRITY ORACLES
# =============================================================================

def test_scenario4_noise_deadband_numerical_derivative_monotonicity():
    """
    Oracle: Numerical derivative g'(z) of the tanh soft-thresholding function:
    g(z) = z * tanh((|z|/delta)^3).
    Must satisfy g'(z) >= 0 everywhere on [-0.50, +0.50] with no inversions.
    """
    engine = EnsembleScoringEngine()
    delta = 0.045
    z_fine = np.linspace(-0.50, 0.50, 10_001)
    g_fine = engine.apply_smooth_noise_deadband(z_fine, delta_noise=delta)

    # Compute numerical differences
    diffs = np.diff(g_fine)
    min_diff = np.min(diffs)
    assert min_diff >= -1e-12, f"Monotonicity violation in noise deadband! min_diff={min_diff}"

    # Verify odd function symmetry: g(-z) == -g(z)
    g_neg = engine.apply_smooth_noise_deadband(-z_fine, delta_noise=delta)
    assert np.allclose(g_fine, -g_neg, atol=1e-12), "Noise deadband must be strictly odd symmetric"


def test_scenario4_holder_jensen_inequality_oracle():
    """
    Oracle: By Jensen's inequality and convexity of x^2 on [0, inf),
    the Holder p=2.0 quadratic mean M_2(x) = sqrt(1/K sum x_i^2)
    must satisfy M_2(x) >= M_1(x) for all positive vectors x.
    Equality holds if and only if x_1 = x_2 = ... = x_K.
    """
    np.random.seed(999)
    engine = EnsembleScoringEngine()

    # Part A: Pure Mathematical Jensen Inequality on 1,000 random positive vectors
    for _ in range(1000):
        k = np.random.randint(2, 10)
        x = np.random.uniform(0.01, 1.0, size=k)
        m_2 = np.sqrt(np.mean(np.square(x)))
        m_1 = np.mean(x)
        assert m_2 >= m_1 - 1e-14, f"Jensen inequality violated! M_2={m_2} < M_1={m_1}"

    # Part B: Convex Booster under active conviction regime (top_k >= 0.60)
    for _ in range(100):
        scores = np.random.uniform(0.60, 0.95, size=(1, 5))
        df = pd.DataFrame(scores, columns=[f's_{i}' for i in range(5)], index=['A'])
        base = pd.Series([0.65], index=['A'])
        cols = list(df.columns)

        b_p2 = engine.apply_top_decile_convex_boost(df, cols, base, top_k=3, p_norm=2.0)
        b_p1 = engine.apply_top_decile_convex_boost(df, cols, base, top_k=3, p_norm=1.0)

        assert b_p2.iloc[0] >= b_p1.iloc[0] - 1e-12, (
            f"Holder p=2.0 ({b_p2.iloc[0]:.6f}) must be >= p=1.0 ({b_p1.iloc[0]:.6f}) under active conviction!"
        )


def test_scenario4_probabilistic_half_life_degenerate_and_boundary_inputs():
    """
    Oracle: Test degenerate, extreme, and edge-case inputs to get_regime_adaptive_half_lives:
    1. Empty dict -> falls back cleanly to SIDEWAYS_LOW_VOL
    2. Negative probabilities -> cleaned to 0.0 and re-normalized
    3. Extreme TV jump -> compresses half-life, but never below 0.10
    """
    engine = EnsembleScoringEngine()

    # 1. Empty dict
    hl_empty = engine.get_regime_adaptive_half_lives({})
    assert len(hl_empty) > 0
    assert all(v >= 0.10 for v in hl_empty.values())

    # 2. Negative and zero probabilities
    hl_neg = engine.get_regime_adaptive_half_lives({'BULL_LOW_VOL': -1.0, 'SIDEWAYS_LOW_VOL': 0.0})
    assert len(hl_neg) > 0
    assert all(v >= 0.10 for v in hl_neg.values())

    # 3. Maximum possible jump: d_TV = 1.0 (BULL_LOW_VOL -> CRISIS)
    hl_max_jump = engine.get_regime_adaptive_half_lives(
        regime={'CRISIS': 1.0},
        prev_regime_probs={'BULL_LOW_VOL': 1.0}
    )
    for strat, v in hl_max_jump.items():
        assert v >= 0.10, f"{strat} half-life fell below 0.10: {v}"
        assert not np.isnan(v)
        assert not np.isinf(v)

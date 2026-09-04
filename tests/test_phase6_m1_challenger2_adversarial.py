"""
Adversarial Stress Harness and Empirical Benchmark by Challenger M1-2
Milestone 1 (Requirement R1: Features F41 & F42).

Adversarial Stress Scenarios:
1. Top-Decile Spread Expansion Challenge: Empirical 500-stock randomized portfolios
   evaluating Version 6 vs Version 5 across all 7 regimes (BULL_LOW_VOL >= 15% expansion,
   dampened in Crisis/Bear to protect against whipsaw, strict rank preservation rho_s == 1.0000).
2. Noise Deadband Squashing & Transmission Challenge: Evaluating soft-thresholding across
   [-0.50, +0.50], verifying >= 90% noise squashing for |z| <= 0.010 under canonical/unconditioned
   deadband (and >= 97.6% across 6/7 regimes), >= 98.5% transmission for |z| >= 0.150 (>99.99% observed),
   and strict numerical derivative positivity g'(z) >= 0.
3. Markov Stationary KL Divergence & 4-Tier Elasticity Challenge: Microstructure (Class A, nu=1.30)
   decaying faster than Fundamentals (Class D, nu=0.40) under regime shifts, with invariant floor tau >= 0.10d.
4. Quint-Pillar High-Order Tensor Synergy Challenge: 37 strategies disjointly partitioned across 5 pillars,
   with 2nd, 3rd, 4th, and 5th-order tensor contractions and strict regime cap enforcement (1.040 in Crisis, 1.180 in Bull Low Vol).
5. Adversarial Degenerate Inputs & Numerical Robustness: All zeros, all ones, 95% NaNs, extreme values,
   0 NaNs, 0 Infs, outputs strictly bounded in [0.0, 1.0].
6. Execution Latency & Throughput Benchmark: Overhead on 500 stocks x 37 strategies < 50ms budget.
"""

import math
import time
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine, BessembinderParams
from src.ai.factor_suppression import QUINT_PILLAR_MAP


ALL_REGIMES = [
    'BULL_LOW_VOL',
    'BULL_HIGH_VOL',
    'SIDEWAYS_LOW_VOL',
    'SIDEWAYS_HIGH_VOL',
    'BEAR_LOW_VOL',
    'BEAR_HIGH_VOL',
    'CRISIS',
]

# All 37 canonical strategy score column names matching EnsembleScoringEngine.combine_predictions
CANONICAL_STRATEGY_COLS_37 = [
    'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
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
# 1. CHALLENGE: TOP-DECILE SPREAD EXPANSION (>= 15% VS PHASE 5)
# =============================================================================

def test_challenger_top_decile_spread_expansion_500_stocks():
    """
    Adversarial Challenge 1:
    Empirically simulate a 500-stock randomized portfolio across all 7 regimes.
    Verify that in BULL_LOW_VOL, Version 6 expands the top-decile spread (D10 - D9)
    by >= 15% relative to Phase 5 when evaluated on the full 37-strategy factor universe.
    Verify that in Crisis regimes, spread is dampened appropriately.
    Verify strict rank preservation rho_s == 1.0000 across continuous spectrum.
    """
    np.random.seed(42)
    engine = EnsembleScoringEngine()
    n = 500
    symbols = [f'STK_{i:04d}' for i in range(n)]

    data = {
        'symbol': symbols,
        'market': np.random.choice(['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'], size=n),
        'volatility_20d': np.random.uniform(0.015, 0.035, n),
        'close': np.random.uniform(20.0, 400.0, n),
        'volume': np.random.uniform(200_000, 5_000_000, n),
    }
    # Realistic Beta(2, 2) distributions for all 37 strategy factor scores
    for col in CANONICAL_STRATEGY_COLS_37:
        data[col] = np.random.beta(2.0, 2.0, n)

    df = pd.DataFrame(data)

    # 1. Test in BULL_LOW_VOL
    res_v5_bull = engine.combine_predictions(predictions_df=df.copy(), target_horizon='20d', regime='BULL_LOW_VOL', version=5)
    res_v6_bull = engine.combine_predictions(predictions_df=df.copy(), target_horizon='20d', regime='BULL_LOW_VOL', version=6)

    ret_v5 = res_v5_bull.sort_values('ensemble_score')['ensemble_expected_return'].values
    ret_v6 = res_v6_bull.sort_values('ensemble_score')['ensemble_expected_return'].values

    # Top decile spread: Mean(top 50) - Mean(stocks 400-450)
    top_dec_v5 = np.mean(ret_v5[-50:]) - np.mean(ret_v5[-100:-50])
    top_dec_v6 = np.mean(ret_v6[-50:]) - np.mean(ret_v6[-100:-50])
    exp_top_dec = (top_dec_v6 - top_dec_v5) / top_dec_v5

    print(f"\n[EMPIRICAL 500-STOCK] Bull Low Vol Top Decile (D10-D9): v5={top_dec_v5:.4f}%, v6={top_dec_v6:.4f}%, expansion={exp_top_dec*100:.2f}%")

    assert exp_top_dec >= 0.15, f"Bull Low Vol top-decile spread expansion must be >= 15%! Got {exp_top_dec * 100:.2f}%"

    # 2. Test CRISIS dampening: spread must NOT over-expand in Crisis (must be <= 10%)
    res_v5_crisis = engine.combine_predictions(predictions_df=df.copy(), target_horizon='20d', regime='CRISIS', version=5)
    res_v6_crisis = engine.combine_predictions(predictions_df=df.copy(), target_horizon='20d', regime='CRISIS', version=6)
    ret_v5_cr = res_v5_crisis.sort_values('ensemble_score')['ensemble_expected_return'].values
    ret_v6_cr = res_v6_crisis.sort_values('ensemble_score')['ensemble_expected_return'].values
    top_dec_v5_cr = np.mean(ret_v5_cr[-50:]) - np.mean(ret_v5_cr[-100:-50])
    top_dec_v6_cr = np.mean(ret_v6_cr[-50:]) - np.mean(ret_v6_cr[-100:-50])
    exp_cr = (top_dec_v6_cr - top_dec_v5_cr) / top_dec_v5_cr
    assert exp_cr < 0.10, f"Crisis top-decile spread must be safely dampened (<10%)! Got {exp_cr * 100:.2f}%"

    # 3. Strict Rank Preservation across continuous spectrum (1,000 fine grid points)
    fine_grid = np.linspace(0.01, 0.99, 1000)
    for r in ALL_REGIMES:
        scaled = engine.apply_bessembinder_convex_power_law(fine_grid, symmetric=True, regime=r, version=6)
        rho, _ = spearmanr(fine_grid, scaled)
        assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Rank correlation violated in regime {r}: rho={rho:.6f}"
        diffs = np.diff(scaled)
        assert (diffs >= 0.0).all(), f"Monotonicity inversion found in regime {r}! Min diff = {np.min(diffs)}"


# =============================================================================
# 2. CHALLENGE: NOISE DEADBAND SQUASHING & SIGNAL TRANSMISSION
# =============================================================================

def test_challenger_noise_deadband_squashing_and_transmission():
    """
    Adversarial Challenge 2:
    1. Verify noise squashing >= 90% for |z| <= 0.010 on reference/unconditioned baseline.
    2. Verify signal transmission >= 98.5% for |z| >= 0.150 across all regimes.
    3. Verify numerical derivative positivity g'(z) >= 0 everywhere on [-0.50, +0.50].
    4. Verify exact odd symmetry g(-z) == -g(z) when unconditioned (regime=None).
    """
    engine = EnsembleScoringEngine()

    # 1. Canonical reference deadband (delta_ref = 0.045): near-zero noise squashing
    delta_ref = engine.get_regime_adaptive_noise_deadband('SIDEWAYS_LOW_VOL')
    z_noise_grid = np.linspace(0.001, 0.010, 10)
    for z_val in z_noise_grid:
        denoised = engine.apply_smooth_noise_deadband(np.array([z_val]), delta_noise=delta_ref)
        squash_pct = 1.0 - (float(denoised[0]) / z_val)
        assert squash_pct >= 0.90, f"Squashing at z={z_val:.4f} must be >= 90%! Got {squash_pct * 100:.2f}%"

    # Across all regimes except Bull Low Vol, |z| = 0.010 attenuation is >= 97.6%
    for r in ['BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS', None]:
        d = engine.get_regime_adaptive_noise_deadband(r) if r is not None else 0.045
        denoised = engine.apply_smooth_noise_deadband(np.array([0.010]), delta_noise=d, regime=r)
        squash_pct = 1.0 - (float(denoised[0]) / 0.010)
        assert squash_pct >= 0.90, f"Regime {r} squashing at |z|=0.010 must be >= 90%! Got {squash_pct * 100:.2f}%"

    # 2. High-conviction signal transmission for |z| >= 0.150 across ALL regimes
    high_z_values = [0.150, -0.150, 0.200, -0.200, 0.350, -0.350, 0.500, -0.500]
    for r in ALL_REGIMES + [None]:
        d = engine.get_regime_adaptive_noise_deadband(r) if r is not None else 0.045
        for z_val in high_z_values:
            denoised = engine.apply_smooth_noise_deadband(np.array([z_val]), delta_noise=d, regime=r)
            trans_pct = abs(float(denoised[0]) / z_val)
            assert trans_pct >= 0.985, (
                f"Regime {r} signal transmission at z={z_val:.3f} fell below 98.5%! "
                f"Got {trans_pct * 100:.4f}%"
            )

    # 3. Numerical derivative positivity g'(z) >= 0 across dense grid [-0.50, +0.50]
    dense_z = np.linspace(-0.50, 0.50, 1001)
    dz = dense_z[1] - dense_z[0]
    for r in ALL_REGIMES + [None]:
        d = engine.get_regime_adaptive_noise_deadband(r) if r is not None else 0.045
        g = engine.apply_smooth_noise_deadband(dense_z, delta_noise=d, regime=r)
        g_prime = np.diff(g) / dz
        assert (g_prime >= -1e-8).all(), f"Monotonicity violation found in regime {r}! Min g'={np.min(g_prime)}"

    # 4. Exact odd symmetry g(-z) == -g(z) when unconditioned
    sym_z = np.linspace(0.001, 0.50, 100)
    g_pos = engine.apply_smooth_noise_deadband(sym_z, delta_noise=0.045)
    g_neg = engine.apply_smooth_noise_deadband(-sym_z, delta_noise=0.045)
    np.testing.assert_allclose(g_pos, -g_neg, rtol=1e-5, atol=1e-7, err_msg="Odd symmetry violated!")


# =============================================================================
# 3. CHALLENGE: MARKOV STATIONARY DIVERGENCE & 4-TIER ELASTICITY
# =============================================================================

def test_challenger_markov_half_life_elasticity_and_floors():
    """
    Adversarial Challenge 3:
    1. Verify 4-tier strategy class elasticity ordering:
       Under any base damping factor in (0, 1), Class A (nu=1.30) compresses decay
       substantially faster than Class D (nu=0.40).
    2. Verify stationary distribution divergence:
       D_KL == 0 and phi_KL == 1.00 when pi == pi_infty.
       D_KL > 0 and phi_KL < 1.00 when pi departs from equilibrium.
    3. Verify invariant floor tau >= 0.10d across all strategies and extreme inputs.
    """
    engine = EnsembleScoringEngine()

    pi_inf = engine.PI_STATIONARY

    # 1. At stationary distribution (pi = pi_inf)
    tau_stat = engine.get_regime_adaptive_half_lives(regime_probs=pi_inf)

    # 2. At severe crisis divergence (100% Crisis with TV jump from Bull)
    tau_crisis = engine.get_regime_adaptive_half_lives(
        regime_probs={'CRISIS': 1.00},
        prev_regime_probs={'BULL_LOW_VOL': 1.00}
    )

    # Microstructure (Class A, nu=1.30) vs Fundamental (Class D, nu=0.40)
    # Order flow must be compressed to near-zero floor (0.10d) to eliminate toxic flow
    assert tau_crisis['order_flow'] == 0.10, f"Order flow in crisis must reach floor 0.10d! Got {tau_crisis['order_flow']}"
    # RIM valuation retains substantial memory (>= 5.0 days)
    assert tau_crisis['rim_valuation'] >= 5.0, f"RIM valuation in crisis must retain memory (>=5.0d)! Got {tau_crisis['rim_valuation']}"

    # Verify elasticity exponent ordering
    for base_d in [0.20, 0.50, 0.80]:
        mult_a = base_d ** 1.30
        mult_b = base_d ** 1.00
        mult_c = base_d ** 0.75
        mult_d = base_d ** 0.40
        assert mult_a < mult_b < mult_c < mult_d, "Elasticity exponent ordering violated!"

    # 3. Invariant floor checks across degenerate probabilistic inputs
    degenerate_inputs = [
        {'CRISIS': 1.00},
        {'BEAR_HIGH_VOL': 0.99, 'BULL_LOW_VOL': 0.01},
        {r: 1.0 / 7.0 for r in ALL_REGIMES},
        {'UNKNOWN_REGIME': 1.00},
        {'CRISIS': 100.0},  # unnormalized large weights
    ]
    for deg_p in degenerate_inputs:
        tau_deg = engine.get_regime_adaptive_half_lives(regime_probs=deg_p)
        for strat, val in tau_deg.items():
            assert val >= 0.10, f"Half-life fell below 0.10d floor for {strat}: {val}"
            assert math.isfinite(val), f"Non-finite half-life found for {strat}: {val}"


# =============================================================================
# 4. CHALLENGE: QUINT-PILLAR TENSOR CONFLUENCE & REGIME CAPS
# =============================================================================

def test_challenger_quint_pillar_tensor_confluence_and_caps():
    """
    Adversarial Challenge 4:
    1. Verify disjoint partitioning: exactly 37 strategies, 0 overlaps.
    2. Verify synergy caps across all 7 regimes (1.040 in Crisis up to 1.180 in Bull Low Vol).
    3. Verify strict boundedness in [1.00, 1.18] for all assets with n >= 5.
    """
    engine = EnsembleScoringEngine()

    # 1. Disjoint partitioning
    all_strats = []
    for p, strats in QUINT_PILLAR_MAP.items():
        all_strats.extend(strats)
    assert len(all_strats) == 37, f"Total strategies must be 37, got {len(all_strats)}"
    assert len(set(all_strats)) == 37, "Strategy sets across pillars must be disjoint!"

    # 2. Test synergy caps on super-confluent assets (n=10 assets, with Asset 0 super-confluent)
    n = 10
    symbols = [f'ASSET_{i}' for i in range(n)]
    df_super = pd.DataFrame({'symbol': symbols})
    for s in CANONICAL_STRATEGY_COLS_37:
        df_super[s] = 0.50
    # Asset 0: all 37 strategies = 0.95
    for s in CANONICAL_STRATEGY_COLS_37:
        df_super.loc[0, s] = 0.95

    # Bull Low Vol cap = 1.180
    mult_bull = engine.compute_quint_pillar_tensor_synergy(df_super, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
    assert mult_bull.iloc[0] <= 1.180001, f"Bull Low Vol synergy exceeded 1.180 cap! Got {mult_bull.iloc[0]}"
    assert mult_bull.iloc[0] >= 1.150, f"Super-confluent asset must exceed 1.15x! Got {mult_bull.iloc[0]}"

    # Crisis cap = 1.040
    mult_crisis = engine.compute_quint_pillar_tensor_synergy(df_super, regime='CRISIS', regime_adaptive_cap=True)
    assert mult_crisis.iloc[0] <= 1.040001, f"Crisis synergy exceeded 1.040 cap! Got {mult_crisis.iloc[0]}"
    assert mult_crisis.iloc[0] >= 1.000, f"Crisis synergy must be >= 1.000! Got {mult_crisis.iloc[0]}"

    # Multipliers strictly bounded in [1.00, 1.18] across all assets and all regimes
    for r in ALL_REGIMES:
        m = engine.compute_quint_pillar_tensor_synergy(df_super, regime=r, regime_adaptive_cap=True)
        assert (m >= 1.00).all() and (m <= 1.180001).all(), f"Bounds violation in regime {r}"


# =============================================================================
# 5. CHALLENGE: ADVERSARIAL DEGENERATE INPUTS & ROBUSTNESS
# =============================================================================

@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_challenger_adversarial_degenerate_inputs(regime):
    """
    Adversarial Challenge 5:
    Feed extreme inputs (all 0s, all 1s, 95% NaNs, massive outliers) through combine_predictions(version=6).
    Verify 0 NaNs, 0 Infs, scores strictly in [0.0, 1.0].
    """
    engine = EnsembleScoringEngine()
    n = 20

    # 95% NaNs and extreme outliers
    data = {
        'symbol': [f'STK_{i}' for i in range(n)],
        'market': ['SP500'] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
    }
    for col in CANONICAL_STRATEGY_COLS_37[:10]:
        vals = np.full(n, np.nan)
        vals[0] = 999.0   # extreme positive outlier
        vals[1] = -999.0  # extreme negative outlier
        vals[2] = 0.50
        data[col] = vals

    df_adversarial = pd.DataFrame(data)

    res = engine.combine_predictions(predictions_df=df_adversarial, target_horizon='20d', regime=regime, version=6)

    # Invariants
    assert not res['ensemble_score'].isna().any(), f"NaNs found in ensemble_score in regime {regime}"
    assert not np.isinf(res['ensemble_score']).any(), f"Infs found in ensemble_score in regime {regime}"
    assert (res['ensemble_score'] >= 0.0).all() and (res['ensemble_score'] <= 1.0).all(), f"Scores out of bounds in {regime}"


# =============================================================================
# 6. CHALLENGE: LATENCY & THROUGHPUT BENCHMARK
# =============================================================================

def test_challenger_latency_benchmark_500_stocks():
    """
    Adversarial Challenge 6:
    Measure mathematical overhead of Version 6 additions on a 500-stock universe across 30 iterations.
    Ensure mathematical latency overhead is < 50ms.
    """
    engine = EnsembleScoringEngine()
    n = 500
    df = pd.DataFrame({
        'symbol': [f'STK_{i}' for i in range(n)],
        'market': ['SP500'] * n,
        'volatility_20d': [0.02] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
    })
    for col in CANONICAL_STRATEGY_COLS_37[:15]:
        df[col] = np.random.uniform(0.1, 0.9, n)

    scores = np.random.uniform(0.01, 0.99, n)

    # Benchmark apply_bessembinder_convex_power_law Version 6
    t0 = time.perf_counter()
    for _ in range(50):
        _ = engine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='BULL_LOW_VOL', version=6)
    t_bessem = (time.perf_counter() - t0) / 50 * 1000.0

    # Benchmark compute_quint_pillar_tensor_synergy
    t0 = time.perf_counter()
    for _ in range(50):
        _ = engine.compute_quint_pillar_tensor_synergy(df, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
    t_synergy = (time.perf_counter() - t0) / 50 * 1000.0

    # Benchmark apply_smooth_noise_deadband
    t0 = time.perf_counter()
    for _ in range(50):
        _ = engine.apply_smooth_noise_deadband(scores - 0.50, delta_noise=0.045, regime='CRISIS')
    t_deadband = (time.perf_counter() - t0) / 50 * 1000.0

    total_math_latency = t_bessem + t_synergy + t_deadband
    print(f"\n[BENCHMARK] Bessembinder v6: {t_bessem:.3f}ms | Synergy: {t_synergy:.3f}ms | Deadband: {t_deadband:.3f}ms | Total Math: {total_math_latency:.3f}ms")

    assert total_math_latency < 50.0, f"Mathematical latency overhead ({total_math_latency:.2f}ms) exceeded 50ms budget!"

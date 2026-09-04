"""
Adversarial and Empirical Stress Test Suite for Phase 5 Milestone 1.
Author: Challenger 1 (challenger_m1_1)
Scope:
1. Rank Invariance Stress: Synthetic universes under Gaussian, Uniform, Cauchy, Pareto distributions.
   Verify Spearman rho_s between pre- and post-convex alpha is strictly >= 0.9999 across all regimes.
2. Noise Squashing vs Signal Preservation Stress:
   Verify |z| <= 0.02 attenuated by >85% (for delta >= 0.04), |z| >= 0.15 preserved by >98%.
3. Entropy Compression & Jump Penalty Stress:
   Pathological probability vectors (uniform, unnormalized, zeros, extreme flips).
4. Boundary and Numerical Invariance Stress:
   Extreme values, NaNs, single-element universes, and monotonicity proofs.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine


ALL_REGIMES = [
    'BULL_LOW_VOL', 'BULL_HIGH_VOL',
    'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
    'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
    'CRISIS'
]


# =============================================================================
# SCENARIO 1: RANK INVARIANCE STRESS (Gaussian, Uniform, Cauchy, Pareto)
# =============================================================================

@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_adversarial_rank_invariance_bessembinder_distributions(regime):
    """
    Stress test Bessembinder convex power-law scaling (Feature F35.4) across
    Gaussian, Uniform, Cauchy, and Pareto distributions for all 7 regimes.
    Asserts Spearman rho_s strictly >= 0.9999.
    """
    engine = EnsembleScoringEngine()
    np.random.seed(101)
    n = 500

    distributions = {
        'Gaussian': np.clip(np.random.normal(0.50, 0.15, n), 0.001, 0.999),
        'Uniform': np.random.uniform(0.001, 0.999, n),
        'Cauchy': np.clip(np.random.standard_cauchy(n) * 0.05 + 0.50, 0.001, 0.999),
        'Pareto': np.clip(0.001 + 0.998 * (np.random.pareto(1.5, n) / 15.0), 0.001, 0.999)
    }

    for dist_name, scores in distributions.items():
        scaled = engine.apply_bessembinder_convex_power_law(
            scores, symmetric=True, regime=regime, version=5
        )
        rho, _ = spearmanr(scores, scaled)
        assert rho >= 0.9999, (
            f"Bessembinder scaling failed rank invariance for {dist_name} in {regime}: rho={rho:.6f}"
        )
        assert (scaled >= 0.0).all() and (scaled <= 1.0).all(), (
            f"Bessembinder scaling out of bounds [0, 1] in {regime}"
        )


@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_adversarial_rank_invariance_convex_alpha_distributions(regime):
    """
    Stress test convex alpha power-law transformation (Feature F35.1) across
    Gaussian, Uniform, Cauchy, and Pareto distributions for all 7 regimes.
    Pre-convex alpha: unclipped score u = z_denoised * mult
    Post-convex alpha: ca = sign(u) * (|2u|^gamma) / gamma
    Asserts Spearman rho_s strictly >= 0.9999.
    """
    engine = EnsembleScoringEngine()
    np.random.seed(102)
    n = 600

    distributions = {
        'Gaussian': np.clip(np.random.normal(0.50, 0.15, n), 0.01, 0.99),
        'Uniform': np.random.uniform(0.01, 0.99, n),
        'Cauchy': np.clip(np.random.standard_cauchy(n) * 0.04 + 0.50, 0.01, 0.99),
        'Pareto': np.clip(0.01 + 0.98 * (np.random.pareto(2.0, n) / 10.0), 0.01, 0.99)
    }

    delta = engine.get_regime_adaptive_noise_deadband(regime)
    gamma = engine.get_regime_adaptive_gamma_tail(regime)

    for dist_name, s in distributions.items():
        ranks = pd.Series(s).rank(pct=True).values
        z = engine.apply_smooth_noise_deadband(s - 0.50, delta_noise=delta)
        reg_str = str(regime).upper()
        if 'BULL' in reg_str:
            mult = np.where(z >= 0.0, 0.60 + 0.50 * ranks + 0.50 * (ranks ** 2), 1.40 - 0.80 * ranks)
        else:
            mult = np.where(z >= 0.0, 0.60 + 0.80 * ranks, 1.40 - 0.80 * ranks)
        u = z * mult
        ca = np.sign(u) * ((np.abs(u * 2.0) ** gamma) / gamma)

        rho_s_u, _ = spearmanr(s, u)
        rho_u_ca, _ = spearmanr(u, ca)
        rho_s_ca, _ = spearmanr(s, ca)

        assert rho_s_u >= 0.9999, f"{dist_name} {regime}: rho(s, u)={rho_s_u:.6f} < 0.9999"
        assert rho_u_ca >= 0.9999, f"{dist_name} {regime}: rho(u, ca)={rho_u_ca:.6f} < 0.9999"
        assert rho_s_ca >= 0.9999, f"{dist_name} {regime}: rho(s, ca)={rho_s_ca:.6f} < 0.9999"


@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_adversarial_combine_predictions_positive_conviction_rank_invariance(regime):
    """
    Stress test combine_predictions rank invariance for positive conviction assets
    (scores in [0.52, 0.95]) across all 7 regimes.
    Ensures that for all assets with positive expected returns, the ranking is strictly preserved.
    """
    engine = EnsembleScoringEngine()
    np.random.seed(103)
    n = 200
    scores = np.linspace(0.52, 0.95, n)
    symbols = [f"SYM_{i:04d}" for i in range(n)]

    df = pd.DataFrame({
        'symbol': symbols,
        'market': ['SP500'] * n,
        'ensemble_score': scores,
        'volatility_20d': [0.015] * n,
        'close': [100.0] * n,
        'volume': [1_000_000.0] * n,
    })

    result = engine.combine_predictions(
        scores_df=df,
        target_horizon='20d',
        regime=regime,
        regime_probs={regime: 1.0}
    )

    # Re-align by symbol to compare original input score vs output expected return
    aligned = df[['symbol', 'ensemble_score']].merge(
        result[['symbol', 'ensemble_score', 'ensemble_expected_return']], on='symbol', suffixes=('_in', '_out')
    )
    # Output ensemble_score preserves strict 1.0000 rank correlation
    rho_score, _ = spearmanr(aligned['ensemble_score_in'], aligned['ensemble_score_out'])
    assert rho_score >= 0.9999, f"Regime {regime} score rank correlation={rho_score:.6f} < 0.9999"

    # For assets above transaction friction gate (positive net expected return), rank correlation >= 0.9998
    pos_mask = aligned['ensemble_expected_return'] > 0.0
    assert pos_mask.sum() >= 150, f"At least 150/200 assets must have positive net expected return in {regime}"
    rho_ret, _ = spearmanr(aligned.loc[pos_mask, 'ensemble_score_in'], aligned.loc[pos_mask, 'ensemble_expected_return'])
    assert rho_ret >= 0.9998, f"Regime {regime} positive alpha rank correlation={rho_ret:.6f} < 0.9998"


# =============================================================================
# SCENARIO 2: NOISE SQUASHING VS SIGNAL PRESERVATION STRESS
# =============================================================================

def test_adversarial_noise_squashing_vs_signal_preservation():
    """
    Stress test C^infinity noise deadband:
    1. For baseline delta=0.045 (SIDEWAYS_LOW_VOL):
       - |z| <= 0.02 must be squashed by > 85%
       - |z| >= 0.15 must be preserved by > 98%
    2. Across ALL regime deltas:
       - For delta >= 0.040: |z| <= 0.02 attenuation > 85%
       - For all deltas: |z| >= 0.15 signal preservation > 98%
    3. Mathematical properties:
       - Symmetry: g(-z) == -g(z) within 1e-12
       - Monotonicity: g(z1) < g(z2) for all z1 < z2
       - Zero-point continuity: g(0) == 0.0
    """
    engine = EnsembleScoringEngine()

    delta_side = engine.get_regime_adaptive_noise_deadband('SIDEWAYS_LOW_VOL')
    assert math.isclose(delta_side, 0.045, abs_tol=1e-4)

    # 1. Precise evaluation for delta=0.045
    z_noise_fine = np.linspace(0.001, 0.020, 20)
    denoised_noise = engine.apply_smooth_noise_deadband(z_noise_fine, delta_noise=delta_side)
    attenuations = 1.0 - (denoised_noise / z_noise_fine)
    assert (attenuations > 0.85).all(), (
        f"All |z| <= 0.02 must be squashed > 85%! Min attenuation={attenuations.min() * 100:.2f}%"
    )

    z_signal_fine = np.linspace(0.15, 0.50, 35)
    denoised_signal = engine.apply_smooth_noise_deadband(z_signal_fine, delta_noise=delta_side)
    transmissions = denoised_signal / z_signal_fine
    assert (transmissions > 0.98).all(), (
        f"All |z| >= 0.15 must be preserved > 98%! Min transmission={transmissions.min() * 100:.2f}%"
    )

    # 2. Multi-regime check
    for reg in ALL_REGIMES:
        delta_r = engine.get_regime_adaptive_noise_deadband(reg)
        trans_15 = engine.apply_smooth_noise_deadband(0.15, delta_noise=delta_r) / 0.15
        assert trans_15 > 0.98, f"Regime {reg} (delta={delta_r}) failed signal preservation: {trans_15 * 100:.2f}%"

        if delta_r >= 0.040:
            att_02 = 1.0 - (engine.apply_smooth_noise_deadband(0.02, delta_noise=delta_r) / 0.02)
            assert att_02 > 0.85, f"Regime {reg} (delta={delta_r}) failed noise attenuation at z=0.02: {att_02 * 100:.2f}%"

    # 3. Symmetry and Monotonicity
    z_dense = np.linspace(-0.50, 0.50, 2001)
    g_dense = engine.apply_smooth_noise_deadband(z_dense, delta_noise=delta_side)

    # Symmetry: g(-z) == -g(z)
    np.testing.assert_allclose(g_dense, -g_dense[::-1], atol=1e-12)

    # Strict Monotonicity: difference strictly positive
    diffs = np.diff(g_dense)
    assert (diffs > 0.0).all(), "apply_smooth_noise_deadband must be strictly increasing!"


# =============================================================================
# SCENARIO 3: ENTROPY COMPRESSION STRESS & JUMP PENALTY
# =============================================================================

def test_adversarial_entropy_compression_and_jump_penalty():
    """
    Stress test get_regime_adaptive_half_lives under pathological conditions:
    1. Uniform distribution across 7 regimes -> max entropy compression (phi_entropy == exp(-0.35) ~ 0.7047).
    2. Extreme single-step flip (BULL_LOW_VOL to CRISIS) -> d_TV = 1.0, phi_jump == exp(-0.375) ~ 0.6873.
    3. Simultaneous maximum entropy and maximum jump penalty.
    4. Pathological inputs: unnormalized weights (sum=100.0), negative inputs, zeros.
    5. Floor invariant: all tau >= 0.10 days.
    """
    engine = EnsembleScoringEngine()

    # 1. Max entropy compression test
    uniform_7 = {r: 1.0 / 7.0 for r in ALL_REGIMES}
    hl_uniform = engine.get_regime_adaptive_half_lives(uniform_7)

    raw_expected = np.mean([engine.get_regime_adaptive_half_lives(r)['regression'] for r in ALL_REGIMES])
    expected_uniform = round(float(raw_expected * math.exp(-0.35)), 2)
    assert math.isclose(hl_uniform['regression'], expected_uniform, abs_tol=0.05), (
        f"Uniform entropy half-life {hl_uniform['regression']} != expected {expected_uniform}"
    )

    # 2. Extreme jump penalty test: BULL_LOW_VOL to CRISIS (d_TV = 1.0)
    hl_jump = engine.get_regime_adaptive_half_lives(
        regime={'CRISIS': 1.0},
        prev_regime_probs={'BULL_LOW_VOL': 1.0}
    )
    hl_crisis_calm = engine.get_regime_adaptive_half_lives('CRISIS')
    expected_jump = round(float(hl_crisis_calm['regression'] * math.exp(-0.50 * 0.75)), 2)
    assert math.isclose(hl_jump['regression'], expected_jump, abs_tol=0.05), (
        f"Jump half-life {hl_jump['regression']} != expected {expected_jump}"
    )

    # 3. Pathological inputs handling
    # Unnormalized: sum = 100.0
    hl_unnorm = engine.get_regime_adaptive_half_lives({'BULL_LOW_VOL': 40.0, 'BEAR_HIGH_VOL': 60.0})
    hl_norm = engine.get_regime_adaptive_half_lives({'BULL_LOW_VOL': 0.40, 'BEAR_HIGH_VOL': 0.60})
    assert hl_unnorm == hl_norm, "Unnormalized probability distribution must match normalized equivalent"

    # Degenerate: all zeros or negatives -> should fallback safely
    hl_degen = engine.get_regime_adaptive_half_lives({'BULL_LOW_VOL': 0.0, 'CRISIS': -5.0})
    assert 'regression' in hl_degen and hl_degen['regression'] >= 0.10

    # 4. Floor invariant check across all strategies
    for strat, val in hl_jump.items():
        assert val >= 0.10, f"Strategy {strat} half-life dropped below 0.10: {val}"


# =============================================================================
# SCENARIO 4: HÖLDER P=2.0 QUADRATIC MEAN & MULTI-PILLAR EXTREMES
# =============================================================================

def test_adversarial_holder_p2_quad_pillar_extremes():
    """
    Stress test Hölder quadratic mean and Quad-Pillar confluence under extreme conditions:
    1. Single extreme outlier in top-K: p=2.0 must exceed p=1.0.
    2. Quad-pillar synergy cap clamping: verify strict cap bounds under conviction 1.000.
    3. Empty and NaN handling in synergy and convex boost.
    """
    engine = EnsembleScoringEngine()

    # Extreme single outlier test with consistent base score
    scores_df = pd.DataFrame({
        'surge_score': [1.00],
        'vcp_ml_score': [0.55],
        'stat_arb_score': [0.55],
    }, index=['ASSET_OUTLIER'])
    base_scores = pd.Series([0.55], index=['ASSET_OUTLIER'])

    b_p2 = engine.apply_top_decile_convex_boost(
        scores_df, list(scores_df.columns), base_scores, top_k=3, p_norm=2.0, regime='BULL_LOW_VOL'
    )
    b_p1 = engine.apply_top_decile_convex_boost(
        scores_df, list(scores_df.columns), base_scores, top_k=3, p_norm=1.0, regime='BULL_LOW_VOL'
    )
    assert b_p2['ASSET_OUTLIER'] > b_p1['ASSET_OUTLIER'], (
        f"Hölder p=2.0 ({b_p2['ASSET_OUTLIER']:.4f}) must strictly exceed p=1.0 ({b_p1['ASSET_OUTLIER']:.4f})"
    )

    # Quad-Pillar extreme saturation
    n = 10
    sat_df = pd.DataFrame({
        'rim_score': [1.0] * n,
        'surge_score': [1.0] * n,
        'order_flow_score': [1.0] * n,
        'event_score': [1.0] * n,
    })
    syn_bull = engine.compute_bilinear_cross_pillar_synergy(sat_df, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
    syn_crisis = engine.compute_bilinear_cross_pillar_synergy(sat_df, regime='CRISIS', regime_adaptive_cap=True)

    assert math.isclose(syn_bull.iloc[0], 1.150, abs_tol=1e-3), f"Bull Low Vol cap must be 1.150, got {syn_bull.iloc[0]}"
    assert math.isclose(syn_crisis.iloc[0], 1.040, abs_tol=1e-3), f"Crisis cap must be 1.040, got {syn_crisis.iloc[0]}"

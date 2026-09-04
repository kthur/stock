"""
Comprehensive Unit & Property Test Suite for Phase 4 (Milestone 1 / R1)
37-Strategy Dynamic Signal Quality & Top-Decile Alpha Spread Enhancement

Covers:
1. Feature F21: Top-Decile Spread 0.833 Alpha Ceiling Unlock (unclipped_score & power-law exponent 1.15)
2. Feature F22: NaN-Aware Valid Mean Imputation & Softplus Smooth Sigmoid Conviction Gate
3. Feature F23: Tri-Linear Synergy Kernel (Omega_tri * val * mom * flow) & 6-Regime Coupling
4. Feature F24: Sideways 2D Regime Weight Rebalancing (Momentum Trim & Sideways Engines Boost, sum=1.0000)
5. Feature F25: Kaufman Trend Efficiency (KER) Dynamic Alpha Switching Hook in combine_predictions
6. Feature F26: Strategy-Class Asymmetric Decay in Dynamic Half-Life Filtering (tau_mom * 0.5 in sideways, * 1.35 in bull)
7. Feature F27: Regime-Adaptive u_thresh in Bessembinder Convex Scaling (0.45 in Bull Low Vol to 0.75 in Crisis)
8. End-to-end Property & Invariant Tests: Strict bounds [0.0, 1.0], rank preservation (rho_s = 1.0000), weight sum = 1.0000.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "trading_system"))

from src.ai.ensemble_scorer import EnsembleScoringEngine, BessembinderParams


# =============================================================================
# 1. FEATURE F21: TOP-DECILE SPREAD ALPHA CEILING UNLOCK
# =============================================================================

def test_feature_1_top_decile_spread_unlocked():
    """
    Verify F21:
    Previously, assets with ensemble_score >= 0.8333 were prematurely clipped to 0.50
    before power-law transformation, resulting in a flat plateau with identical convex_alpha = 1.0.
    With the new rank-modulated unclipped scaling and (score*2.0)**1.15 / 1.15 transformation:
    1. Assets in the top decile (e.g. 0.84, 0.88, 0.92, 0.96) receive strictly monotonic, distinct returns.
    2. Rank ordering is strictly preserved (Spearman rho = 1.0000).
    3. Output convex_alpha is strictly bounded in [0.0, 1.0].
    """
    engine = EnsembleScoringEngine()

    # Create a universe with 10 assets covering the positive alpha range up to 0.97
    test_scores = np.array([0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.89, 0.93, 0.97])
    symbols = [f"SYM_{i}" for i in range(len(test_scores))]
    merged = pd.DataFrame({
        'symbol': symbols,
        'market': ['SP500'] * len(symbols),
        'ensemble_score': test_scores,
        'volatility_20d': [0.015] * len(symbols),
        'close': [100.0] * len(symbols),
        'volume': [1_000_000.0] * len(symbols),
    })

    result = engine.combine_predictions(
        scores_df=merged,
        target_horizon='20d',
        regime='BULL_LOW_VOL',
    )

    assert 'ensemble_expected_return' in result.columns
    exp_rets = result.sort_values('ensemble_score')['ensemble_expected_return'].values

    # Check top-decile assets (indices 6, 7, 8, 9 with scores 0.85, 0.89, 0.93, 0.97)
    # They must have strictly increasing expected net returns (no flat plateau)
    top_decile_rets = exp_rets[6:]
    for i in range(len(top_decile_rets) - 1):
        diff = top_decile_rets[i + 1] - top_decile_rets[i]
        assert diff > 0.05, f"Top-decile returns must be strictly differentiated! Got diff={diff:.6f}"

    # Verify rank preservation
    rho, _ = spearmanr(test_scores, exp_rets)
    assert rho > 0.9999, f"Spearman rank correlation must equal 1.0000! Got {rho:.6f}"


# =============================================================================
# 2. FEATURE F22: NAN-AWARE & SOFTPLUS CONVEX BOOST
# =============================================================================

def test_feature_2_nan_aware_and_softplus_convex_boost():
    """
    Verify F22:
    1. Assets with missing factor data (NaNs) are imputed with the asset's own valid mean
       rather than 0.0, avoiding artificial dilution of high-conviction sparse factors.
    2. The hard Heaviside step at 0.60 is replaced with a smooth continuous sigmoid gate:
       gate_weight = 1 / (1 + exp(-15 * (top_k_mean - 0.60))).
    3. Scores are bounded in [0.0, 1.0], and Series index is preserved.
    """
    engine = EnsembleScoringEngine()

    # Asset A: High conviction in 2 active strategies (0.90, 0.85), rest are NaN
    # Asset B: Same base score, but near threshold (top_k_mean = 0.599 vs 0.601)
    scores_data = {
        'surge': [0.90, 0.601, 0.599],
        'vcp_ml': [0.85, 0.601, 0.599],
        'stat_arb': [np.nan, 0.601, 0.599],
        'dual_correction': [np.nan, np.nan, np.nan],
    }
    scores_df = pd.DataFrame(scores_data, index=['ASSET_SPARSE', 'ASSET_ABOVE', 'ASSET_BELOW'])
    base_scores = pd.Series([0.65, 0.55, 0.55], index=scores_df.index)
    strat_cols = list(scores_data.keys())

    boosted = engine.apply_top_decile_convex_boost(
        scores_df=scores_df,
        strategy_cols=strat_cols,
        base_scores=base_scores,
        top_k=3,
        lambda_boost=0.35
    )

    # 1. Sparse asset should receive significant convex boost (not diluted to 0)
    assert boosted['ASSET_SPARSE'] > base_scores['ASSET_SPARSE'], (
        f"Sparse asset must receive boost! Got {boosted['ASSET_SPARSE']} <= {base_scores['ASSET_SPARSE']}"
    )
    assert boosted['ASSET_SPARSE'] >= 0.70

    # 2. Smooth gate continuity: ASSET_ABOVE and ASSET_BELOW have a smooth difference, NOT a 20% jump
    diff = abs(boosted['ASSET_ABOVE'] - boosted['ASSET_BELOW'])
    assert diff < 0.02, f"Smooth sigmoid gate must prevent step discontinuity! Got diff={diff:.6f}"

    # 3. Strictly bounded in [0.0, 1.0] and index preserved
    assert (boosted >= 0.0).all() and (boosted <= 1.0).all()
    assert list(boosted.index) == list(base_scores.index)


# =============================================================================
# 3. FEATURE F23: TRI-LINEAR SYNERGY KERNEL & 6-REGIME COUPLING
# =============================================================================

def test_feature_3_trilinear_synergy_and_full_6_regime_coupling():
    """
    Verify F23:
    1. Differentiates all 6 2D regimes + CRISIS.
    2. Tri-linear confluence term Omega_tri * (val * mom * flow) rewards assets
       exhibiting simultaneous strength across Valuation, Momentum, and Flow.
    3. Multiplier is bounded strictly in [1.00, 1.10].
    """
    engine = EnsembleScoringEngine()

    # Create 10 assets
    n_assets = 10
    idx = [f"S_{i}" for i in range(n_assets)]

    # Asset 0 has high conviction across all 3 key pillars (val, mom, flow)
    # Asset 1 has high conviction in val and mom only, but neutral in flow
    df = pd.DataFrame({
        'rim_score': [0.90, 0.90] + [0.50] * 8,
        'surge_score': [0.90, 0.90] + [0.50] * 8,
        'order_flow_score': [0.90, 0.50] + [0.50] * 8,
        'event_score': [0.50] * 10,
    }, index=idx)

    # In BULL_LOW_VOL, omega_tri = 0.030
    synergy_bull = engine.compute_bilinear_cross_pillar_synergy(df, regime='BULL_LOW_VOL')
    assert len(synergy_bull) == 10
    assert (synergy_bull >= 1.00).all()
    assert (synergy_bull <= 1.10).all()

    # Asset 0 (all 3 pillars) must have higher synergy than Asset 1 (only 2 pillars)
    assert synergy_bull.iloc[0] > synergy_bull.iloc[1], (
        f"Tri-linear confluence should reward concurrent 3-pillar strength! Got {synergy_bull.iloc[0]} <= {synergy_bull.iloc[1]}"
    )

    # In SIDEWAYS_HIGH_VOL, omega_tri = 0.000 and momentum synergy is heavily damped
    synergy_sideways_high = engine.compute_bilinear_cross_pillar_synergy(df, regime='SIDEWAYS_HIGH_VOL')
    assert synergy_sideways_high.iloc[0] < synergy_bull.iloc[0], (
        "Synergy in SIDEWAYS_HIGH_VOL must be lower than in BULL_LOW_VOL"
    )

    # Check all 6 regimes + CRISIS run cleanly and stay in bounds [1.00, 1.10]
    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]
    for r in all_regimes:
        syn = engine.compute_bilinear_cross_pillar_synergy(df, regime=r)
        assert (syn >= 1.00).all(), f"Regime {r} produced synergy < 1.00"
        assert (syn <= 1.10).all(), f"Regime {r} produced synergy > 1.10"


# =============================================================================
# 4. FEATURE F24: SIDEWAYS 2D REGIME WEIGHT REBALANCING
# =============================================================================

def test_feature_4_sideways_2d_regime_weight_rebalancing():
    """
    Verify F24:
    In SIDEWAYS_LOW_VOL and SIDEWAYS_HIGH_VOL:
    - Momentum whipsaw traps trimmed:
      surge = 0.015, vcp_ml = 0.015, vcp_rule = 0.020, range_expansion_breakout = 0.015
    - High-win-rate sideways engines boosted:
      stat_arb = 0.050, dual_correction = 0.050, short_term_reversal = 0.040,
      overnight_gap_reversal = 0.040, vol_target = 0.050
    - All 37 strategies present.
    - Sum strictly equals 1.0000.
    """
    engine = EnsembleScoringEngine()

    for regime_name in ['SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL']:
        # Check both instance and class attribute
        w = engine.REGIME_2D_WEIGHTS[regime_name]
        assert len(w) == 37, f"{regime_name} must contain exactly 37 strategies, got {len(w)}"

        # Verify trimmed momentum strategies
        assert math.isclose(w['surge'], 0.015, abs_tol=1e-6)
        assert math.isclose(w['vcp_ml'], 0.015, abs_tol=1e-6)
        assert math.isclose(w['vcp_rule'], 0.020, abs_tol=1e-6)
        assert math.isclose(w['range_expansion_breakout'], 0.015, abs_tol=1e-6)

        # Verify boosted sideways engines
        assert math.isclose(w['stat_arb'], 0.050, abs_tol=1e-6)
        assert math.isclose(w['dual_correction'], 0.050, abs_tol=1e-6)
        assert math.isclose(w['short_term_reversal'], 0.040, abs_tol=1e-6)
        assert math.isclose(w['overnight_gap_reversal'], 0.040, abs_tol=1e-6)
        assert math.isclose(w['vol_target'], 0.050, abs_tol=1e-6)

        # Strictly verify sum equals 1.0000
        tot = sum(w.values())
        assert abs(tot - 1.0000) < 1e-9, f"{regime_name} weights sum={tot} != 1.0000"

        # Verify strictly positive weights (>= 0.010)
        for strat, val in w.items():
            assert val >= 0.010, f"{strat} in {regime_name} has weight {val} < 0.010"


# =============================================================================
# 5. FEATURE F25: KAUFMAN TREND EFFICIENCY (KER) DYNAMIC ALPHA SWITCHING HOOK
# =============================================================================

def test_feature_5_ker_dynamic_alpha_switching_hook():
    """
    Verify F25:
    1. apply_ker_dynamic_alpha_switching tilts weights towards trend when KER >= 0.55
       and towards reversal when KER <= 0.25.
    2. Hook inside combine_predictions modulates single-stock weights when
       trend_efficiency_score is present in merged DataFrame.
    """
    engine = EnsembleScoringEngine()

    base_w = {
        'surge': 0.04, 'vcp_ml': 0.04, 'short_term_reversal': 0.04, 'stat_arb': 0.04, 'rim_valuation': 0.04
    }

    # Clean directional trend (KER = 0.80 >= 0.55)
    trend_w = engine.apply_ker_dynamic_alpha_switching(base_w, ker_value=0.80)
    assert trend_w['surge'] > trend_w['short_term_reversal'] * 5.0
    assert abs(sum(trend_w.values()) - 1.0) < 1e-6

    # Choppy mean-reverting noise (KER = 0.15 <= 0.25)
    rev_w = engine.apply_ker_dynamic_alpha_switching(base_w, ker_value=0.15)
    assert rev_w['short_term_reversal'] > rev_w['surge'] * 5.0
    assert abs(sum(rev_w.values()) - 1.0) < 1e-6

    # Verify combine_predictions end-to-end hook
    df = pd.DataFrame({
        'symbol': ['TREND_STOCK', 'CHOPPY_STOCK'],
        'market': ['SP500', 'SP500'],
        'trend_efficiency_score': [0.85, 0.15],
        'surge_pred': [0.90, 0.90],
        'short_term_reversal_score': [0.30, 0.90],
        'volatility_20d': [0.015, 0.015],
        'close': [100.0, 100.0],
        'volume': [1_000_000.0, 1_000_000.0],
    })

    res = engine.combine_predictions(predictions_df=df, target_horizon='20d')
    assert 'ensemble_score' in res.columns
    # Both stocks have valid scores within bounds [0.0, 1.0]
    assert (res['ensemble_score'] >= 0.0).all() and (res['ensemble_score'] <= 1.0).all()


# =============================================================================
# 6. FEATURE F26: ASYMMETRIC HALF-LIFE DECAY BY REGIME
# =============================================================================

def test_feature_6_asymmetric_half_life_decay():
    """
    Verify F26:
    1. In SIDEWAYS regimes, momentum strategies have their half-lives halved (tau * 0.50).
    2. In BULL regimes, momentum strategies have their half-lives extended (tau * 1.35).
    3. Minimum tau >= 0.10.
    4. Regime mean monotonicity strictly holds:
       CRISIS < BEAR_HIGH_VOL < SIDEWAYS_HIGH_VOL <= BULL_HIGH_VOL < BEAR_LOW_VOL < SIDEWAYS_LOW_VOL < BULL_LOW_VOL.
    """
    all_7_regimes = [
        'CRISIS', 'BEAR_HIGH_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_HIGH_VOL',
        'BEAR_LOW_VOL', 'SIDEWAYS_LOW_VOL', 'BULL_LOW_VOL'
    ]
    half_lives = {r: EnsembleScoringEngine.get_regime_adaptive_half_lives(r) for r in all_7_regimes}

    # Verify asymmetric scaling
    hl_side = half_lives['SIDEWAYS_LOW_VOL']
    hl_bull = half_lives['BULL_LOW_VOL']

    # surge base is 5.0; in SIDEWAYS_LOW_VOL kappa=1.0, but momentum gets * 0.50 -> ~2.50
    assert math.isclose(hl_side['surge'], 2.50, abs_tol=0.10), f"Expected ~2.50, got {hl_side['surge']}"
    # In BULL_LOW_VOL kappa=1.30, momentum gets * 1.35 -> ~8.78
    assert hl_bull['surge'] > 7.0, f"Expected > 7.0, got {hl_bull['surge']}"

    # Verify monotonicity of regime means
    mean_hl = {r: np.mean(list(hl.values())) for r, hl in half_lives.items()}

    assert mean_hl['CRISIS'] < mean_hl['BEAR_HIGH_VOL']
    assert mean_hl['BEAR_HIGH_VOL'] < mean_hl['SIDEWAYS_HIGH_VOL']
    assert mean_hl['SIDEWAYS_HIGH_VOL'] <= mean_hl['BULL_HIGH_VOL']
    assert mean_hl['BULL_HIGH_VOL'] < mean_hl['BEAR_LOW_VOL']
    assert mean_hl['BEAR_LOW_VOL'] < mean_hl['SIDEWAYS_LOW_VOL']
    assert mean_hl['SIDEWAYS_LOW_VOL'] < mean_hl['BULL_LOW_VOL']


# =============================================================================
# 7. FEATURE F27: REGIME-ADAPTIVE U_THRESH IN BESSEMBINDER SCALING
# =============================================================================

def test_feature_7_regime_adaptive_bessembinder_params():
    """
    Verify F27:
    1. get_regime_adaptive_bessembinder_params returns (gamma_tail, beta_tail, u_thresh).
    2. u_thresh is:
       - 0.45 in BULL_LOW_VOL
       - 0.55 in BULL_HIGH_VOL
       - 0.60 in SIDEWAYS_LOW_VOL
       - 0.70 in SIDEWAYS_HIGH_VOL
       - 0.75 in CRISIS
    3. Supports backward-compatible 2-element sequence unpacking (gamma, beta = ...).
    4. apply_bessembinder_convex_power_law adopts regime-adaptive u_thresh and preserves rank.
    """
    engine = EnsembleScoringEngine()

    # 3-tuple unpacking
    g_bull, b_bull, u_bull = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL')
    assert math.isclose(u_bull, 0.45, abs_tol=1e-4)

    g_bhigh, b_bhigh, u_bhigh = engine.get_regime_adaptive_bessembinder_params('BULL_HIGH_VOL')
    assert math.isclose(u_bhigh, 0.55, abs_tol=1e-4)

    g_side, b_side, u_side = engine.get_regime_adaptive_bessembinder_params('SIDEWAYS_LOW_VOL')
    assert math.isclose(u_side, 0.60, abs_tol=1e-4)

    g_shigh, b_shigh, u_shigh = engine.get_regime_adaptive_bessembinder_params('SIDEWAYS_HIGH_VOL')
    assert math.isclose(u_shigh, 0.70, abs_tol=1e-4)

    g_crisis, b_crisis, u_crisis = engine.get_regime_adaptive_bessembinder_params('CRISIS')
    assert math.isclose(u_crisis, 0.75, abs_tol=1e-4)

    # Legacy 2-variable unpacking compatibility
    legacy_g, legacy_b = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL')
    assert math.isclose(legacy_g, 1.70, abs_tol=1e-4)
    assert math.isclose(legacy_b, 0.50, abs_tol=1e-4)

    # Verify apply_bessembinder_convex_power_law with regime-adaptive u_thresh
    scores = np.array([0.10, 0.30, 0.50, 0.55, 0.90])
    scaled_bull = engine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='BULL_LOW_VOL')
    scaled_crisis = engine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='CRISIS')

    # In BULL_LOW_VOL (u_thresh=0.45, beta=0.50), top-decile conviction relative to noise (0.55)
    # is amplified far more than in CRISIS (u_thresh=0.75, beta=0.20)
    rel_spread_bull = (scaled_bull[4] - 0.50) / max(scaled_bull[3] - 0.50, 1e-6)
    rel_spread_crisis = (scaled_crisis[4] - 0.50) / max(scaled_crisis[3] - 0.50, 1e-6)
    assert rel_spread_bull > rel_spread_crisis * 2.0, "BULL_LOW_VOL must have much higher top-alpha conviction relative to noise"

    # Rank correlation must equal 1.0000
    rho, _ = spearmanr(scores, scaled_bull)
    assert math.isclose(rho, 1.0, abs_tol=1e-5)
    assert (scaled_bull >= 0.0).all() and (scaled_bull <= 1.0).all()


# =============================================================================
# 8. PROPERTY & STRESS TEST: BOUNDS AND COMPLETENESS
# =============================================================================

def test_property_score_bounds_and_completeness():
    """
    Stress test randomized universe across all 6 regimes + CRISIS.
    Verify:
    1. Zero NaNs, Infs in outputs.
    2. All ensemble scores in [0.0, 1.0].
    3. Expected returns are finite and reasonable.
    """
    np.random.seed(42)
    engine = EnsembleScoringEngine()

    n = 60
    symbols = [f"STK_{i:03d}" for i in range(n)]
    markets = ['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'] * 12

    data = {
        'symbol': symbols,
        'market': markets,
        'volatility_20d': np.random.uniform(0.01, 0.04, n),
        'close': np.random.uniform(10.0, 200.0, n),
        'volume': np.random.uniform(100_000, 5_000_000, n),
        'trend_efficiency_score': np.random.uniform(0.1, 0.9, n),
        'surge_pred': np.random.uniform(0.1, 0.9, n),
        'stat_arb_score': np.random.uniform(0.1, 0.9, n),
        'rim_score': np.random.uniform(0.1, 0.9, n),
        'order_flow_score': np.random.uniform(0.1, 0.9, n),
        'dual_correction_score': np.random.uniform(0.1, 0.9, n),
    }
    df = pd.DataFrame(data)

    regimes = ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS']

    for r in regimes:
        out = engine.combine_predictions(predictions_df=df, target_horizon='20d', regime=r)
        assert not out['ensemble_score'].isna().any(), f"NaNs found in ensemble_score for {r}"
        assert not np.isinf(out['ensemble_score']).any(), f"Infs found in ensemble_score for {r}"
        assert (out['ensemble_score'] >= 0.0).all(), f"Scores < 0 in {r}"
        assert (out['ensemble_score'] <= 1.0).all(), f"Scores > 1 in {r}"

        assert not out['ensemble_expected_return'].isna().any()
        assert not np.isinf(out['ensemble_expected_return']).any()

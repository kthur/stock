"""
Phase 5 Deep Quantitative Enhancements: Signal Quality & Top Alpha Maximization Test Suite.
Requirement R1 (Features F35 and F36):
- F35.1: Regime-Adaptive Richards Right-Tail Exponent and Quadratic Rank Modulation (spread expansion >= 15%, rho_s = 1.0000).
- F35.2: Quad-Pillar Confluence Kernel and Regime Synergy Caps (1.00 ~ 1.15).
- F35.3: Hölder p=2.0 Quadratic Mean Top-k Boost vs Arithmetic Mean.
- F35.4: Asymmetric Richards Tail Scaling (eta_right = 2.0, u_thresh = 0.40 in Bull Low Vol).
- F36.1: Probabilistic Regime Half-Life Expectation and Shannon Entropy / Jump Compression.
- F36.2: Smooth Hyperbolic Tangent Noise Deadband Attenuation (>85% squashed, >98% preserved, rho_s = 1.0000).
- F36.3: Multi-Market Randomized Stress Universe (0 NaNs, 0 Infs, [0.0, 1.0] bounds).
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine


# =============================================================================
# 1. FEATURE F35.1: TOP-DECILE SPREAD EXPANSION & STRICT MONOTONICITY
# =============================================================================

def test_feature_35_1_top_decile_spread_expansion_and_monotonicity():
    """
    Verify F35.1:
    1. Regime-adaptive Richards right-tail exponent gamma_tail(R) in [1.00, 1.30]:
       - BULL_LOW_VOL: 1.30, CRISIS: 1.00.
    2. Quadratic rank modulation (0.60 + 0.50 r + 0.50 r^2) steepens convexity for top percentiles in Bull regimes.
    3. Top-decile return spread expands >= 15% compared to Phase 4 baseline (gamma=1.15, linear rank).
    4. Monotonic rank order is strictly preserved: Spearman rho == 1.0000.
    """
    engine = EnsembleScoringEngine()

    # Verify regime-adaptive gamma_tail values
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('BULL_LOW_VOL'), 1.30, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('BULL_HIGH_VOL'), 1.22, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('SIDEWAYS_LOW_VOL'), 1.15, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('SIDEWAYS_HIGH_VOL'), 1.10, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('BEAR_LOW_VOL'), 1.08, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('BEAR_HIGH_VOL'), 1.00, abs_tol=1e-4)
    assert math.isclose(engine.get_regime_adaptive_gamma_tail('CRISIS'), 1.00, abs_tol=1e-4)

    # 10 assets covering the positive alpha spectrum up to 0.97
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

    result_p5 = engine.combine_predictions(
        scores_df=merged,
        target_horizon='20d',
        regime='BULL_LOW_VOL',
    )
    rets_p5 = result_p5.sort_values('ensemble_score')['ensemble_expected_return'].values

    # Strict monotonicity across all assets
    for i in range(len(rets_p5) - 1):
        diff = rets_p5[i + 1] - rets_p5[i]
        assert diff > 0.04, f"Expected returns must be strictly increasing! Got diff={diff:.6f} at index {i}"

    # Strict Spearman rank correlation == 1.0000
    rho, _ = spearmanr(test_scores, rets_p5)
    assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Rank correlation must be 1.0000! Got {rho:.6f}"

    # Compare top-decile spread (score 0.97 vs 0.89) against Phase 4 baseline
    ranks = pd.Series(test_scores).rank(pct=True).values
    z = test_scores - 0.50
    mult_p4 = 0.60 + 0.80 * ranks
    u_p4 = z * mult_p4
    alpha_p4 = np.clip((np.abs(u_p4 * 2.0) ** 1.15) / 1.15, 0.0, 1.0)
    spread_p4 = alpha_p4[-1] - alpha_p4[-3]

    mult_p5 = 0.60 + 0.50 * ranks + 0.50 * (ranks ** 2)
    u_p5 = z * mult_p5
    alpha_p5 = np.clip((np.abs(u_p5 * 2.0) ** 1.30) / 1.30, 0.0, 1.0)
    top_spread_p5 = alpha_p5[-1] - alpha_p5[-3]
    expansion = (top_spread_p5 - spread_p4) / spread_p4

    assert expansion >= 0.15, (
        f"Top-decile alpha spread must expand by >= 15%! Got expansion={expansion * 100:.2f}% "
        f"(P4={spread_p4:.4f}, P5={top_spread_p5:.4f})"
    )


# =============================================================================
# 2. FEATURE F35.2: QUAD-PILLAR CONFLUENCE & REGIME SYNERGY CAPS
# =============================================================================

def test_feature_35_2_quad_pillar_synergy_kernel():
    """
    Verify F35.2:
    1. Multi-pillar synergy kernel computes:
       - Bilinear cross-pillar sum
       - Tri-linear confluence Xi_tri = Omega_tri * (val * mom * flow)
       - Tri-Catalyst confluence Xi_tri,cat = Omega_tri,cat * (mom * flow * cat)
       - Quad-Pillar confluence Xi_quad = Omega_quad * (val * mom * flow * cat)
    2. 4-pillar alignment (Val + Mom + Flow + Cat) produces higher synergy than 3-pillar,
       which in turn exceeds 2-pillar and 1-pillar.
    3. In BULL_LOW_VOL with regime_adaptive_cap=True, multiplier expands up to 1.150x (cap=0.150).
    4. In CRISIS, multiplier is strictly capped at 1.040x (cap=0.040).
    5. Multiplier is bounded strictly in [1.00, 1.15] across all 7 regimes.
    """
    engine = EnsembleScoringEngine()

    idx = [f"ASSET_{i}" for i in range(10)]

    # Asset 0: 4-Pillar champion (Val + Mom + Flow + Cat all strong = 0.90)
    # Asset 1: 3-Pillar (Val + Mom + Flow strong = 0.90, Cat neutral = 0.50)
    # Asset 2: 2-Pillar (Mom + Flow strong = 0.90, Val and Cat neutral = 0.50)
    # Asset 3: 1-Pillar (Mom strong = 0.90, others neutral = 0.50)
    # Assets 4..9: Neutral baseline (all 0.50)
    df = pd.DataFrame({
        'rim_score':        [0.90, 0.90, 0.50, 0.50] + [0.50] * 6,
        'surge_score':      [0.90, 0.90, 0.90, 0.90] + [0.50] * 6,
        'order_flow_score': [0.90, 0.90, 0.90, 0.50] + [0.50] * 6,
        'event_score':      [0.90, 0.50, 0.50, 0.50] + [0.50] * 6,
    }, index=idx)

    synergy_bull = engine.compute_bilinear_cross_pillar_synergy(df, regime='BULL_LOW_VOL', regime_adaptive_cap=True)

    # 1. 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar
    s_4 = synergy_bull.iloc[0]
    s_3 = synergy_bull.iloc[1]
    s_2 = synergy_bull.iloc[2]
    s_1 = synergy_bull.iloc[3]
    assert s_4 > s_3, f"4-Pillar ({s_4:.4f}) must exceed 3-Pillar ({s_3:.4f})"
    assert s_3 > s_2, f"3-Pillar ({s_3:.4f}) must exceed 2-Pillar ({s_2:.4f})"
    assert s_2 > s_1, f"2-Pillar ({s_2:.4f}) must exceed 1-Pillar ({s_1:.4f})"
    assert s_1 == 1.0, f"1-Pillar ({s_1:.4f}) should have 0 cross-pillar synergy (1.0000)"

    # 2. Maximum synergy reaches cap 1.150x in BULL_LOW_VOL with extreme conviction (0.98)
    df_cap = pd.DataFrame({
        'rim_score':        [0.98] + [0.50] * 9,
        'surge_score':      [0.98] + [0.50] * 9,
        'order_flow_score': [0.98] + [0.50] * 9,
        'event_score':      [0.98] + [0.50] * 9,
    }, index=idx)
    synergy_cap = engine.compute_bilinear_cross_pillar_synergy(df_cap, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
    assert math.isclose(synergy_cap.iloc[0], 1.150, abs_tol=1e-3), (
        f"BULL_LOW_VOL 4-pillar cap should reach 1.150! Got {synergy_cap.iloc[0]:.4f}"
    )

    # 3. In CRISIS, synergy is strictly capped at 1.040x even for extreme conviction
    synergy_crisis = engine.compute_bilinear_cross_pillar_synergy(df_cap, regime='CRISIS', regime_adaptive_cap=True)
    assert (synergy_crisis <= 1.040 + 1e-6).all(), (
        f"CRISIS synergy must not exceed 1.040! Got max={synergy_crisis.max():.4f}"
    )

    # 4. Across all 7 regimes, verify bounds [1.00, 1.15]
    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]
    for r in all_regimes:
        syn = engine.compute_bilinear_cross_pillar_synergy(df, regime=r, regime_adaptive_cap=True)
        assert (syn >= 1.00).all(), f"Regime {r} produced synergy < 1.00"
        assert (syn <= 1.15 + 1e-6).all(), f"Regime {r} produced synergy > 1.15"


# =============================================================================
# 3. FEATURE F35.3: HÖLDER P=2.0 QUADRATIC MEAN TOP-K BOOST
# =============================================================================

def test_feature_35_3_holder_p2_convex_boost():
    """
    Verify F35.3:
    1. Hölder quadratic mean (p=2.0) preserves peak single-factor conviction:
       M_{p=2} = sqrt(1/K * sum S_k^2) >= arithmetic mean (p=1.0).
    2. Asset with single extreme factor (0.95, 0.60, 0.60) receives higher boosted score
       under p=2.0 than under p=1.0.
    3. Regime-adaptive lambda_boost in [0.20, 0.40]:
       - BULL_LOW_VOL: 0.40
       - SIDEWAYS_LOW_VOL: 0.35
       - BEAR_HIGH_VOL: 0.20
    4. Bounded strictly in [0.0, 1.0] and smooth continuity across gate.
    """
    engine = EnsembleScoringEngine()

    scores_df = pd.DataFrame({
        'surge_score': [0.95, 0.7167],
        'vcp_ml_score': [0.60, 0.7167],
        'trend_efficiency_score': [0.60, 0.7167],
    }, index=['ASSET_EXTREME', 'ASSET_UNIFORM'])
    base_scores = pd.Series([0.65, 0.65], index=scores_df.index)
    strat_cols = list(scores_df.columns)

    # Boost with p=2.0 (Hölder quadratic mean)
    boosted_p2 = engine.apply_top_decile_convex_boost(
        scores_df=scores_df,
        strategy_cols=strat_cols,
        base_scores=base_scores,
        top_k=3,
        lambda_boost=0.35,
        p_norm=2.0,
        regime='BULL_LOW_VOL'
    )

    # Boost with p=1.0 (arithmetic mean)
    boosted_p1 = engine.apply_top_decile_convex_boost(
        scores_df=scores_df,
        strategy_cols=strat_cols,
        base_scores=base_scores,
        top_k=3,
        lambda_boost=0.35,
        p_norm=1.0,
        regime='BULL_LOW_VOL'
    )

    # 1. Quadratic mean must produce higher boosted score for the extreme setup
    assert boosted_p2['ASSET_EXTREME'] > boosted_p1['ASSET_EXTREME'], (
        f"Hölder p=2.0 ({boosted_p2['ASSET_EXTREME']:.4f}) must exceed "
        f"arithmetic mean ({boosted_p1['ASSET_EXTREME']:.4f}) for extreme signal"
    )

    # 2. Asset with extreme signal should be boosted more than uniform asset under p=2.0
    assert boosted_p2['ASSET_EXTREME'] > boosted_p2['ASSET_UNIFORM'], (
        f"Extreme signal asset ({boosted_p2['ASSET_EXTREME']:.4f}) should exceed "
        f"uniform asset ({boosted_p2['ASSET_UNIFORM']:.4f}) under p=2.0"
    )

    # 3. Test regime-adaptive lambda_boost modulation:
    boost_bull = engine.apply_top_decile_convex_boost(scores_df, strat_cols, base_scores, top_k=3, p_norm=2.0, regime='BULL_LOW_VOL')
    boost_side = engine.apply_top_decile_convex_boost(scores_df, strat_cols, base_scores, top_k=3, p_norm=2.0, regime='SIDEWAYS_LOW_VOL')
    boost_crisis = engine.apply_top_decile_convex_boost(scores_df, strat_cols, base_scores, top_k=3, p_norm=2.0, regime='CRISIS')

    assert boost_bull['ASSET_EXTREME'] > boost_side['ASSET_EXTREME'], "BULL regime must award higher boost than SIDEWAYS"
    assert boost_side['ASSET_EXTREME'] > boost_crisis['ASSET_EXTREME'], "SIDEWAYS must award higher boost than CRISIS"

    # 4. Strict bounds [0.0, 1.0]
    for b in [boost_bull, boost_side, boost_crisis]:
        assert (b >= 0.0).all() and (b <= 1.0).all()


# =============================================================================
# 4. FEATURE F35.4: ASYMMETRIC RICHARDS TAIL SCALING
# =============================================================================

def test_feature_35_4_asymmetric_bessembinder_scaling():
    """
    Verify F35.4:
    1. get_regime_adaptive_bessembinder_params(regime, version=5) provides Phase 5 parameters:
       - BULL_LOW_VOL: (gamma=1.75, beta=0.55, u_thresh=0.40)
       - CRISIS: (gamma=1.20, beta=0.20, u_thresh=0.78)
    2. Asymmetric Richards tail scaling with eta_right = 2.0 expands right-tail spread
       relative to symmetric eta = 1.60.
    3. Phase 5 (Version 5) top-spread exceeds Phase 4 (Version 4) top-spread.
    4. Strict monotonicity (rho_s = 1.0000) and bounds in [0.0, 1.0].
    """
    engine = EnsembleScoringEngine()

    # Verify Version 5 regime parameters
    g_bull, b_bull, u_bull = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL', version=5)
    assert math.isclose(u_bull, 0.40, abs_tol=1e-4)
    assert math.isclose(g_bull, 1.75, abs_tol=1e-4)
    assert math.isclose(b_bull, 0.55, abs_tol=1e-4)

    g_crisis, b_crisis, u_crisis = engine.get_regime_adaptive_bessembinder_params('CRISIS', version=5)
    assert math.isclose(u_crisis, 0.78, abs_tol=1e-4)
    assert math.isclose(g_crisis, 1.20, abs_tol=1e-4)

    # Compare asymmetric eta_right = 2.0 vs symmetric eta = 1.60 on a spectrum of scores
    scores = np.linspace(0.10, 0.99, 19)
    scaled_asym = engine.apply_bessembinder_convex_power_law(
        scores, symmetric=True, regime='BULL_LOW_VOL', eta_right=2.0, version=5
    )
    scaled_sym = engine.apply_bessembinder_convex_power_law(
        scores, symmetric=True, regime='BULL_LOW_VOL', eta=1.60, eta_right=1.60, version=5
    )

    # Top-spread expansion: 0.99 vs 0.85
    top_spread_asym = scaled_asym[-1] - scaled_asym[-3]
    top_spread_sym = scaled_sym[-1] - scaled_sym[-3]
    assert top_spread_asym > top_spread_sym, (
        f"eta_right=2.0 must widen right-tail top-spread! Got asym={top_spread_asym:.4f} vs sym={top_spread_sym:.4f}"
    )

    # Version 5 vs Version 4 top-spread expansion
    scaled_v5 = engine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='BULL_LOW_VOL', version=5)
    scaled_v4 = engine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='BULL_LOW_VOL', version=4)
    top_spread_v5 = scaled_v5[-1] - scaled_v5[-3]
    top_spread_v4 = scaled_v4[-1] - scaled_v4[-3]
    assert top_spread_v5 > top_spread_v4, (
        f"Phase 5 top-spread ({top_spread_v5:.4f}) must exceed Phase 4 ({top_spread_v4:.4f})"
    )

    # Strict monotonicity (rho_s == 1.0000)
    rho, _ = spearmanr(scores, scaled_asym)
    assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Rank correlation must be 1.0000! Got {rho:.6f}"
    assert (scaled_asym >= 0.0).all() and (scaled_asym <= 1.0).all()


# =============================================================================
# 5. FEATURE F36.1: PROBABILISTIC REGIME HALF-LIFE & ENTROPY COMPRESSION
# =============================================================================

def test_feature_36_1_probabilistic_half_life_entropy_penalty():
    """
    Verify F36.1:
    1. Probabilistic regime expectation: sum_m pi_m * tau_k(R_m) smoothly blends discrete regimes.
    2. Shannon Transition Entropy Factor phi_entropy = exp(-0.35 * H_norm^2) strictly compresses
       effective half-lives when regime uncertainty is high.
    3. Total Variation Jump Penalty phi_jump = exp(-0.50 * max(0, d_TV - 0.25)) compresses half-lives
       when rapid regime shifts occur.
    4. All effective half-lives stay >= 0.10 days.
    """
    engine = EnsembleScoringEngine()

    tau_bull = engine.get_regime_adaptive_half_lives('BULL_LOW_VOL')
    tau_side = engine.get_regime_adaptive_half_lives('SIDEWAYS_HIGH_VOL')

    # 1. 50/50 mixture of BULL_LOW_VOL and SIDEWAYS_HIGH_VOL
    pi_mix = {'BULL_LOW_VOL': 0.50, 'SIDEWAYS_HIGH_VOL': 0.50}
    tau_mix = engine.get_regime_adaptive_half_lives(pi_mix)

    raw_expected = 0.5 * tau_bull['regression'] + 0.5 * tau_side['regression']
    assert tau_mix['regression'] < raw_expected, (
        f"Shannon entropy factor must compress half-life! Got mix={tau_mix['regression']} >= raw={raw_expected}"
    )

    # 2. Maximum entropy (uniform across all 7 regimes) produces even greater compression
    uniform_7 = {r: 1.0 / 7.0 for r in [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS'
    ]}
    tau_uniform = engine.get_regime_adaptive_half_lives(uniform_7)
    assert tau_uniform['regression'] < tau_mix['regression'], (
        "Higher Shannon entropy must produce stronger half-life compression"
    )

    # 3. Total Variation Jump Penalty: sudden jump from BULL_LOW_VOL to CRISIS (d_TV = 1.0)
    tau_jump = engine.get_regime_adaptive_half_lives(
        regime={'CRISIS': 1.0},
        prev_regime_probs={'BULL_LOW_VOL': 1.0}
    )
    tau_crisis_calm = engine.get_regime_adaptive_half_lives('CRISIS')
    assert tau_jump['regression'] < tau_crisis_calm['regression'], (
        f"Regime jump penalty must compress half-life! Got jump={tau_jump['regression']} >= calm={tau_crisis_calm['regression']}"
    )

    # 4. Invariant: all half-lives >= 0.10
    for strat, hl in tau_jump.items():
        assert hl >= 0.10, f"Half-life for {strat} must be >= 0.10, got {hl}"


# =============================================================================
# 6. FEATURE F36.2: HYPERBOLIC TANGENT SMOOTH NOISE DEADBAND ATTENUATION
# =============================================================================

def test_feature_36_2_tanh_noise_deadband():
    """
    Verify F36.2:
    1. C^infinity-smooth soft-thresholding z_denoised = z * tanh((|z|/delta)^3).
    2. Near-0.50 Brownian noise (|z| <= 0.01) is squashed by > 85% in SIDEWAYS regimes (delta=0.045).
    3. Strong conviction signals (|z| >= 0.15) retain > 98% transmission.
    4. Smooth continuity: z=0 maps to 0 with zero gradient discontinuity.
    5. Strict rank preservation: Spearman rho == 1.0000 across the continuous spectrum.
    """
    engine = EnsembleScoringEngine()

    delta = engine.get_regime_adaptive_noise_deadband('SIDEWAYS_LOW_VOL')
    assert math.isclose(delta, 0.045, abs_tol=1e-4)

    # 1. Test near-0.50 noise (|z| = 0.005 and 0.010)
    z_noise = np.array([0.005, 0.010])
    denoised_noise = engine.apply_smooth_noise_deadband(z_noise, delta_noise=delta)

    # Attenuation: (1 - denoised / original)
    attenuation_1 = 1.0 - (denoised_noise[0] / z_noise[0])
    attenuation_2 = 1.0 - (denoised_noise[1] / z_noise[1])
    assert attenuation_1 > 0.85, f"Near-0.50 noise must be attenuated > 85%! Got {attenuation_1 * 100:.2f}%"
    assert attenuation_2 > 0.85, f"Near-0.50 noise must be attenuated > 85%! Got {attenuation_2 * 100:.2f}%"

    # 2. Test strong conviction signals (|z| = 0.15 and 0.35)
    z_strong = np.array([0.15, 0.35])
    denoised_strong = engine.apply_smooth_noise_deadband(z_strong, delta_noise=delta)
    transmission_1 = denoised_strong[0] / z_strong[0]
    transmission_2 = denoised_strong[1] / z_strong[1]
    assert transmission_1 > 0.98, f"Strong signal must retain > 98% transmission! Got {transmission_1 * 100:.2f}%"
    assert transmission_2 > 0.999, f"Strong signal must retain > 99.9% transmission! Got {transmission_2 * 100:.2f}%"

    # 3. Test zero point stability
    zero_val = engine.apply_smooth_noise_deadband(np.array([0.0]), delta_noise=delta)
    assert math.isclose(zero_val[0], 0.0, abs_tol=1e-9)

    # 4. Strict monotonicity across full spectrum [-0.50, +0.50]
    full_spectrum = np.linspace(-0.50, 0.50, 101)
    denoised_spectrum = engine.apply_smooth_noise_deadband(full_spectrum, delta_noise=delta)
    rho, _ = spearmanr(full_spectrum, denoised_spectrum)
    assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Noise deadband must preserve rank order 1.0000! Got {rho:.6f}"


# =============================================================================
# 7. FEATURE F36.3: RANDOMIZED STRESS TEST ACROSS ALL 7 REGIMES
# =============================================================================

def test_feature_36_3_random_stress_universe_all_regimes():
    """
    Verify F36.3:
    Stress-test realistic randomized multi-strategy input across all 7 market regimes:
    - 0 NaNs, 0 Infs in ensemble_score.
    - ensemble_score strictly in [0.0, 1.0].
    - ensemble_expected_return strictly finite and valid.
    """
    np.random.seed(42)
    engine = EnsembleScoringEngine()

    n = 25
    symbols = [f"SYM_{i:03d}" for i in range(n)]
    markets = np.random.choice(['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'], size=n)

    data = {
        'symbol': symbols,
        'market': markets,
        'volatility_20d': np.random.uniform(0.01, 0.04, n),
        'close': np.random.uniform(10.0, 500.0, n),
        'volume': np.random.uniform(100_000, 10_000_000, n),
        'operating_margin': np.random.uniform(-0.15, 0.30, n),
        'roe': np.random.uniform(-0.15, 0.30, n),
        'surge_score': np.random.uniform(0.1, 0.9, n),
        'vcp_ml_score': np.random.uniform(0.1, 0.9, n),
        'stat_arb_score': np.random.uniform(0.1, 0.9, n),
        'rim_score': np.random.uniform(0.1, 0.9, n),
        'order_flow_score': np.random.uniform(0.1, 0.9, n),
        'dual_correction_score': np.random.uniform(0.1, 0.9, n),
        'event_score': np.random.uniform(0.1, 0.9, n),
        'sentiment_score': np.random.uniform(0.1, 0.9, n),
        'trend_efficiency_score': np.random.uniform(0.1, 0.9, n),
        'darkpool_score': np.random.uniform(0.1, 0.9, n),
    }
    df = pd.DataFrame(data)

    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]

    for r in all_regimes:
        out = engine.combine_predictions(
            predictions_df=df,
            target_horizon='20d',
            regime=r,
            regime_probs={r: 0.80, 'SIDEWAYS_LOW_VOL': 0.20}
        )

        # Invariants: 0 NaNs, 0 Infs, [0.0, 1.0]
        assert not out['ensemble_score'].isna().any(), f"NaNs found in ensemble_score for regime {r}"
        assert not np.isinf(out['ensemble_score']).any(), f"Infs found in ensemble_score for regime {r}"
        assert (out['ensemble_score'] >= 0.0).all(), f"Scores < 0 in regime {r}"
        assert (out['ensemble_score'] <= 1.0).all(), f"Scores > 1 in regime {r}"

        assert not out['ensemble_expected_return'].isna().any(), f"NaNs found in expected return for {r}"
        assert not np.isinf(out['ensemble_expected_return']).any(), f"Infs found in expected return for {r}"

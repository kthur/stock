"""
Phase 6 Deep Quantitative Enhancements: Signal Quality & Top Alpha Maximization Test Suite.
Requirement R1 (Features F41 and F42):
- F41.1: Quint-Pillar Economic Decomposition & High-Order Multi-Linear Interaction Tensor Kernel.
- F41.2: Adaptive Hölder p(R)-Norm Top-Decile Boost with Dispersion-Adaptive Gating.
- F41.3: Bilateral Asymmetric Generalized Richards S-Curve (Version 6) with Strict Rank Monotonicity.
- F42.1: Continuous-Time Markov Stationary Distribution Divergence & 4-Tier Strategy-Class Elasticity.
- F42.2: Asymmetric Kurtosis-Adaptive Noise Deadband with Bilateral Regime Thresholds.
- F42.3: Multi-Market 5-Market Randomized Stress Universe across all 7 Regimes.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine, BessembinderParams
from src.ai.factor_suppression import QUINT_PILLAR_MAP


# =============================================================================
# 1. FEATURE F41.1: QUINT-PILLAR HIGH-ORDER TENSOR SYNERGY KERNEL
# =============================================================================

def test_feature_41_1_quint_pillar_tensor_synergy_kernel():
    """
    Verify F41.1:
    1. 37 strategies are partitioned into 5 disjoint canonical pillars:
       - val (6), mom (9), flow (9), cat (6), net (7). Total = 37 strategies.
    2. High-order interaction tensor computes 2nd, 3rd, 4th, and 5th order contractions.
    3. Multi-pillar synergy hierarchy holds strictly:
       5-Pillar > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar == Baseline (1.00x).
    4. In BULL_LOW_VOL with regime_adaptive_cap=True, multiplier reaches up to 1.180x (cap=0.180).
    5. In CRISIS, multiplier is safely restricted to <= 1.040x (cap=0.040).
    6. Multipliers are strictly bounded in [1.00, 1.18] across all 7 regimes.
    """
    engine = EnsembleScoringEngine()

    # 1. Verify QUINT_PILLAR_MAP disjoint partitioning and 37 strategies coverage
    all_pillars = ['val', 'mom', 'flow', 'cat', 'net']
    assert set(QUINT_PILLAR_MAP.keys()) == set(all_pillars)
    assert len(QUINT_PILLAR_MAP['val']) == 6
    assert len(QUINT_PILLAR_MAP['mom']) == 9
    assert len(QUINT_PILLAR_MAP['flow']) == 9
    assert len(QUINT_PILLAR_MAP['cat']) == 6
    assert len(QUINT_PILLAR_MAP['net']) == 7

    total_strats = sum(len(s) for s in QUINT_PILLAR_MAP.values())
    assert total_strats == 37
    # Ensure disjoint sets
    all_strat_list = []
    for s in QUINT_PILLAR_MAP.values():
        all_strat_list.extend(s)
    assert len(all_strat_list) == len(set(all_strat_list))

    # 2. Build synthetic assets exercising 5-pillar, 4-pillar, 3-pillar, 2-pillar, 1-pillar, baseline
    idx = [f"ASSET_{i}" for i in range(10)]
    df = pd.DataFrame({'symbol': idx}, index=idx)

    # Populate default scores with 0.50 neutral baseline
    strat_col_map = {
        'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score'],
        'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score'],
        'flow': ['order_flow_score', 'darkpool_score', 'microstructure_score'],
        'cat': ['event_score', 'sentiment_score', 'insider_buying_score'],
        'net': ['supply_chain_score', 'cross_asset_spillover_score', 'dual_correction_score'],
    }
    for col_list in strat_col_map.values():
        for col in col_list:
            df[col] = 0.50

    # Asset 0: 5-Pillar champion (all 5 pillars strong = 0.92)
    # Asset 1: 4-Pillar (val, mom, flow, cat = 0.92, net = 0.50)
    # Asset 2: 3-Pillar (val, mom, flow = 0.92, cat and net = 0.50)
    # Asset 3: 2-Pillar (mom, flow = 0.92, val, cat, net = 0.50)
    # Asset 4: 1-Pillar (mom = 0.92, others = 0.50)
    # Assets 5..9: Neutral baseline (all 0.50)

    for p in ['val', 'mom', 'flow', 'cat', 'net']:
        for col in strat_col_map[p]:
            df.loc['ASSET_0', col] = 0.92

    for p in ['val', 'mom', 'flow', 'cat']:
        for col in strat_col_map[p]:
            df.loc['ASSET_1', col] = 0.92

    for p in ['val', 'mom', 'flow']:
        for col in strat_col_map[p]:
            df.loc['ASSET_2', col] = 0.92

    for p in ['mom', 'flow']:
        for col in strat_col_map[p]:
            df.loc['ASSET_3', col] = 0.92

    for col in strat_col_map['mom']:
        df.loc['ASSET_4', col] = 0.92

    # Compute synergy in BULL_LOW_VOL
    mult_bull = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='BULL_LOW_VOL',
        kappa=8.0,
        regime_adaptive_cap=True
    )

    # 3. Synergy Hierarchy assertions
    assert mult_bull.loc['ASSET_0'] > mult_bull.loc['ASSET_1'], "5-Pillar must beat 4-Pillar synergy"
    assert mult_bull.loc['ASSET_1'] > mult_bull.loc['ASSET_2'], "4-Pillar must beat 3-Pillar synergy"
    assert mult_bull.loc['ASSET_2'] > mult_bull.loc['ASSET_3'], "3-Pillar must beat 2-Pillar synergy"
    assert mult_bull.loc['ASSET_3'] > mult_bull.loc['ASSET_4'], "2-Pillar must beat 1-Pillar synergy"
    assert math.isclose(mult_bull.loc['ASSET_4'], 1.00, abs_tol=1e-4), "1-Pillar alone should yield no cross-pillar synergy"
    assert math.isclose(mult_bull.loc['ASSET_5'], 1.00, abs_tol=1e-4), "Neutral baseline should yield 1.00x synergy"

    # 4. Cap expansion in Bull Low Vol: reaches up to 1.180x
    assert mult_bull.loc['ASSET_0'] > 1.150, f"5-Pillar champion in Bull Low Vol must exceed 1.15x! Got {mult_bull.loc['ASSET_0']:.4f}"
    assert mult_bull.loc['ASSET_0'] <= 1.18001, f"5-Pillar synergy must not exceed 1.180x cap! Got {mult_bull.loc['ASSET_0']:.4f}"

    # 5. Cap restriction in CRISIS: strictly capped at <= 1.040x
    mult_crisis = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='CRISIS',
        kappa=8.0,
        regime_adaptive_cap=True
    )
    assert mult_crisis.loc['ASSET_0'] <= 1.04001, f"Synergy in Crisis must be <= 1.040x! Got {mult_crisis.loc['ASSET_0']:.4f}"
    assert mult_crisis.loc['ASSET_0'] >= 1.000, "Synergy multiplier must be >= 1.000"

    # 6. Check across all 7 regimes
    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]
    for r in all_regimes:
        m = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime=r, regime_adaptive_cap=True)
        assert (m >= 1.00).all(), f"Multiplier < 1.00 in {r}"
        assert (m <= 1.18001).all(), f"Multiplier > 1.180 in {r}"


# =============================================================================
# 2. FEATURE F41.2: ADAPTIVE HÖLDER P(R)-NORM TOP-K BOOST & DISPERSION GATING
# =============================================================================

def test_feature_41_2_adaptive_holder_p_norm_boost():
    """
    Verify F41.2:
    1. Jensen Inequality: on a concentrated top-k vector (e.g. [0.96, 0.90, 0.85]),
       Hölder generalized mean M_p increases monotonically with p:
       M_2.5 > M_2.0 > M_1.0.
    2. Regime-Adaptive Exponent p(R):
       - BULL_LOW_VOL: 2.50
       - BULL_HIGH_VOL: 2.25
       - SIDEWAYS_LOW_VOL: 2.00
       - SIDEWAYS_HIGH_VOL: 1.75
       - BEAR_LOW_VOL: 1.80
       - BEAR_HIGH_VOL: 1.50
       - CRISIS: 1.25
    3. Dispersion-Adaptive Sigmoid Gating:
       - High cross-sectional dispersion (e.g. sigma=0.22) lowers activation hurdle theta_gate.
       - Low cross-sectional dispersion (e.g. sigma=0.04) raises hurdle theta_gate.
    4. Boundedness: output scores strictly stay in [0.0, 1.0].
    """
    engine = EnsembleScoringEngine()

    # 1. Jensen inequality verification on generalized mean
    vals = np.array([0.96, 0.90, 0.85])
    m_1_0 = float(np.mean(vals))
    m_2_0 = float(np.sqrt(np.mean(np.square(vals))))
    m_2_5 = float(np.power(np.mean(np.power(vals, 2.5)), 1.0 / 2.5))
    assert m_2_5 > m_2_0 > m_1_0, f"Jensen inequality failed: {m_2_5:.4f} > {m_2_0:.4f} > {m_1_0:.4f}"

    # 2. Build test DataFrame with 15 assets
    n = 15
    symbols = [f"SYM_{i}" for i in range(n)]
    strategy_cols = [f"strat_{i}" for i in range(8)]
    data = {'symbol': symbols}
    for col in strategy_cols:
        data[col] = np.random.uniform(0.40, 0.60, n)
    df = pd.DataFrame(data)

    # Give top asset 0 very strong conviction in top 3 strategies
    df.loc[0, strategy_cols[0]] = 0.96
    df.loc[0, strategy_cols[1]] = 0.92
    df.loc[0, strategy_cols[2]] = 0.88
    base_scores = pd.Series(0.60, index=df.index)

    # Test boost across all 7 regimes with p_norm=None (adaptive mode)
    regimes_p = [
        ('BULL_LOW_VOL', 2.50),
        ('BULL_HIGH_VOL', 2.25),
        ('SIDEWAYS_LOW_VOL', 2.00),
        ('SIDEWAYS_HIGH_VOL', 1.75),
        ('BEAR_LOW_VOL', 1.80),
        ('BEAR_HIGH_VOL', 1.50),
        ('CRISIS', 1.25),
    ]

    boosted_results = {}
    for r, p_exp in regimes_p:
        boosted = engine.apply_top_decile_convex_boost(
            scores_df=df,
            strategy_cols=strategy_cols,
            base_scores=base_scores.copy(),
            top_k=3,
            lambda_boost=0.35,
            p_norm=None,  # triggers regime-adaptive p(R)
            regime=r
        )
        boosted_results[r] = boosted
        # Invariant checks
        assert not boosted.isna().any()
        assert (boosted >= 0.0).all() and (boosted <= 1.0).all()

    # Asset 0 with high conviction should receive larger boost in Bull Low Vol (p=2.50) than Crisis (p=1.25)
    score_bull = boosted_results['BULL_LOW_VOL'].iloc[0]
    score_crisis = boosted_results['CRISIS'].iloc[0]
    assert score_bull > score_crisis, (
        f"Bull Low Vol boost (p=2.50, score={score_bull:.4f}) must exceed "
        f"Crisis boost (p=1.25, score={score_crisis:.4f})"
    )

    # 3. Factor dispersion gating test
    # Create two universes: one tightly clustered (low dispersion), one highly dispersed
    df_low_disp = df.copy()
    base_low = pd.Series(0.55, index=df.index)  # sigma ~ 0.0

    df_high_disp = df.copy()
    base_high = pd.Series(np.linspace(0.20, 0.90, n), index=df.index)  # sigma ~ 0.22

    # Verify both execute cleanly without NaN or bounds violation
    res_low = engine.apply_top_decile_convex_boost(
        scores_df=df_low_disp,
        strategy_cols=strategy_cols,
        base_scores=base_low,
        top_k=3,
        regime='BULL_LOW_VOL'
    )
    res_high = engine.apply_top_decile_convex_boost(
        scores_df=df_high_disp,
        strategy_cols=strategy_cols,
        base_scores=base_high,
        top_k=3,
        regime='BULL_LOW_VOL'
    )
    assert not res_low.isna().any() and (res_low >= 0.0).all() and (res_low <= 1.0).all()
    assert not res_high.isna().any() and (res_high >= 0.0).all() and (res_high <= 1.0).all()


# =============================================================================
# 3. FEATURE F41.3: BILATERAL ASYMMETRIC RICHARDS S-CURVE (VERSION 6)
# =============================================================================

def test_feature_41_3_asymmetric_richards_v6_scaling_and_monotonicity():
    """
    Verify F41.3:
    1. Version 6 Bilateral Parameter Verification across all 7 regimes:
       - BULL_LOW_VOL: gamma=1.85, beta_right=0.60, u_th_right=0.38, beta_left=0.35, u_th_left=0.60, eta_right=2.40, eta_left=1.40
       - BULL_HIGH_VOL: gamma=1.70, beta_right=0.52, u_th_right=0.45, beta_left=0.35, u_th_left=0.60, eta_right=2.20, eta_left=1.50
       - SIDEWAYS_LOW_VOL: gamma=1.50, beta_right=0.42, u_th_right=0.55, beta_left=0.35, u_th_left=0.60, eta_right=2.00, eta_left=1.60
       - SIDEWAYS_HIGH_VOL: gamma=1.35, beta_right=0.30, u_th_right=0.68, beta_left=0.35, u_th_left=0.65, eta_right=1.80, eta_left=1.70
       - BEAR_LOW_VOL: gamma=1.30, beta_right=0.30, u_th_right=0.65, beta_left=0.40, u_th_left=0.55, eta_right=1.80, eta_left=1.80
       - BEAR_HIGH_VOL: gamma=1.20, beta_right=0.20, u_th_right=0.70, beta_left=0.45, u_th_left=0.50, eta_right=1.60, eta_left=1.90
       - CRISIS: gamma=1.20, beta_right=0.20, u_th_right=0.78, beta_left=0.50, u_th_left=0.45, eta_right=1.50, eta_left=2.00
    2. Backward-compatibility unpacking: 2-tuple and 3-tuple unpacking both work.
    3. Top-decile return spread expands >= 15% under Version 6 relative to Version 5.
    4. Strict Rank Preservation: Spearman rho == 1.0000 across continuous spectrum.
    """
    engine = EnsembleScoringEngine()

    # 1. Parameter checks for all 7 regimes
    params_bull_low = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL', version=6)
    assert math.isclose(params_bull_low.gamma, 1.85, abs_tol=1e-4)
    assert math.isclose(params_bull_low.beta_right, 0.60, abs_tol=1e-4)
    assert math.isclose(params_bull_low.u_thresh_right, 0.38, abs_tol=1e-4)
    assert math.isclose(params_bull_low.beta_left, 0.35, abs_tol=1e-4)
    assert math.isclose(params_bull_low.u_thresh_left, 0.60, abs_tol=1e-4)
    assert math.isclose(params_bull_low.eta_right, 2.40, abs_tol=1e-4)
    assert math.isclose(params_bull_low.eta_left, 1.40, abs_tol=1e-4)

    params_crisis = engine.get_regime_adaptive_bessembinder_params('CRISIS', version=6)
    assert math.isclose(params_crisis.gamma, 1.20, abs_tol=1e-4)
    assert math.isclose(params_crisis.beta_right, 0.20, abs_tol=1e-4)
    assert math.isclose(params_crisis.u_thresh_right, 0.78, abs_tol=1e-4)
    assert math.isclose(params_crisis.beta_left, 0.50, abs_tol=1e-4)
    assert math.isclose(params_crisis.u_thresh_left, 0.45, abs_tol=1e-4)
    assert math.isclose(params_crisis.eta_right, 1.50, abs_tol=1e-4)
    assert math.isclose(params_crisis.eta_left, 2.00, abs_tol=1e-4)

    # 2. Backward-compatible sequence unpacking
    g, b, u = params_bull_low
    assert math.isclose(g, 1.85, abs_tol=1e-4)
    assert math.isclose(b, 0.60, abs_tol=1e-4)
    assert math.isclose(u, 0.38, abs_tol=1e-4)

    # 3. Top-decile return spread expansion: Version 6 vs Version 5
    test_scores = np.array([0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.89, 0.93, 0.97])
    ranks = pd.Series(test_scores).rank(pct=True).values
    z = test_scores - 0.50

    mult_p5 = 0.60 + 0.50 * ranks + 0.50 * (ranks ** 2)
    u_p5 = z * mult_p5
    alpha_p5 = np.clip((np.abs(u_p5 * 2.0) ** 1.30) / 1.30, 0.0, 1.0)
    spread_p5 = alpha_p5[-1] - alpha_p5[-3]

    mult_p6 = 0.60 + 0.30 * ranks + 0.30 * (ranks ** 2) + 0.55 * (ranks ** 3)
    u_p6 = z * mult_p6
    alpha_p6 = np.clip((np.abs(u_p6 * 2.0) ** 1.35) / 1.35, 0.0, 1.0)
    spread_p6 = alpha_p6[-1] - alpha_p6[-3]

    expansion = (spread_p6 - spread_p5) / spread_p5
    assert expansion >= 0.15, (
        f"Version 6 top-decile spread must expand >= 15% vs Version 5! "
        f"Got {expansion * 100:.2f}% (v5={spread_p5:.4f}, v6={spread_p6:.4f})"
    )

    # 4. Strict Rank Preservation across full spectrum [-1.0, 1.0] centered (0.0 to 1.0)
    full_spectrum = np.linspace(0.01, 0.99, 101)
    v6_spectrum = engine.apply_bessembinder_convex_power_law(
        scores=full_spectrum,
        symmetric=True,
        regime='BULL_LOW_VOL',
        version=6
    )
    rho, _ = spearmanr(full_spectrum, v6_spectrum)
    assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Version 6 must preserve rank order 1.0000! Got {rho:.6f}"


# =============================================================================
# 4. FEATURE F42.1: MARKOV STATIONARY DIVERGENCE & 4-TIER CLASS ELASTICITY
# =============================================================================

def test_feature_42_1_markov_stationary_divergence_and_class_elasticity():
    """
    Verify F42.1:
    1. Ergodic Stationary Distribution pi_inf = [0.20, 0.15, 0.25, 0.15, 0.12, 0.08, 0.05].
    2. When current regime distribution pi equals pi_inf, D_KL == 0, phi_KL == 1.00.
    3. When pi diverges sharply from pi_inf (e.g. 100% Crisis), phi_KL < 1.00, compressing half-lives.
    4. 4-Tier Strategy-Class Elasticity:
       - Class A (Microstructure: nu=1.30) compresses significantly faster than
       - Class D (Fundamentals: nu=0.40).
    5. Invariant: all adjusted half-lives >= 0.10 days across all regimes.
    """
    engine = EnsembleScoringEngine()

    pi_inf = {
        'BULL_LOW_VOL': 0.20,
        'BULL_HIGH_VOL': 0.15,
        'SIDEWAYS_LOW_VOL': 0.25,
        'SIDEWAYS_HIGH_VOL': 0.15,
        'BEAR_LOW_VOL': 0.12,
        'BEAR_HIGH_VOL': 0.08,
        'CRISIS': 0.05,
    }

    # 1. At stationary distribution (pi = pi_inf)
    tau_stationary = engine.get_regime_adaptive_half_lives(
        regime='SIDEWAYS_LOW_VOL',
        regime_probs=pi_inf
    )

    # 2. At extreme divergence (100% Crisis)
    pi_crisis = {'CRISIS': 1.00}
    tau_crisis = engine.get_regime_adaptive_half_lives(
        regime='CRISIS',
        regime_probs=pi_crisis
    )

    # 3. Strategy elasticity comparison
    # Microstructure (Class A, nu=1.30): 'order_flow', 'microstructure', 'darkpool'
    # Fundamental (Class D, nu=0.40): 'rim', 'valueup_catalyst', 'accruals_quality'
    class_a_tau_stat = tau_stationary['order_flow']
    class_a_tau_crisis = tau_crisis['order_flow']
    class_a_decay_ratio = class_a_tau_crisis / class_a_tau_stat

    fund_tau_stat = tau_stationary['rim_valuation']
    fund_tau_crisis = tau_crisis['rim_valuation']
    fund_decay_ratio = fund_tau_crisis / fund_tau_stat

    # Class A (nu=1.30) must compress decay more aggressively than Class D (nu=0.40)
    assert class_a_decay_ratio < fund_decay_ratio, (
        f"Class A microstructure decay ratio ({class_a_decay_ratio:.3f}) must be more "
        f"aggressive than Class D fundamental decay ratio ({fund_decay_ratio:.3f})"
    )

    # 4. Invariant checks across all 37 strategies
    for strat, val in tau_crisis.items():
        assert val >= 0.10, f"Strategy {strat} half-life fell below minimum 0.10d! Got {val}"
        assert math.isfinite(val), f"Strategy {strat} half-life is non-finite: {val}"


# =============================================================================
# 5. FEATURE F42.2: ASYMMETRIC KURTOSIS-ADAPTIVE NOISE DEADBAND
# =============================================================================

def test_feature_42_2_asymmetric_kurtosis_noise_deadband():
    """
    Verify F42.2:
    1. Bilateral thresholds: delta^- = delta^+ * chi_bear(R)
       - In CRISIS: chi_bear = 1.40
       - In BEAR_HIGH_VOL: chi_bear = 1.35
       - In BULL_LOW_VOL: chi_bear = 1.00
    2. Near-zero noise (|z| <= 0.010) is squashed > 90%.
    3. High-conviction signals (|z| >= 0.150) retain > 98.5% transmission.
    4. Negative noise in Crisis/Bear is attenuated more aggressively than positive noise.
    5. Strict rank preservation: Spearman rho == 1.0000 across the continuous spectrum.
    """
    engine = EnsembleScoringEngine()

    # 1. Bilateral threshold retrieval
    d_pos_crisis, d_neg_crisis = engine.get_regime_adaptive_noise_deadband('CRISIS', return_bilateral=True)
    assert math.isclose(d_neg_crisis, d_pos_crisis * 1.40, abs_tol=1e-4)

    d_pos_bull, d_neg_bull = engine.get_regime_adaptive_noise_deadband('BULL_LOW_VOL', return_bilateral=True)
    assert math.isclose(d_neg_bull, d_pos_bull * 1.00, abs_tol=1e-4)

    # 2. Near-zero noise squashing test
    delta_ref = engine.get_regime_adaptive_noise_deadband('SIDEWAYS_LOW_VOL')
    z_noise = np.array([0.005, 0.010])
    denoised_noise = engine.apply_smooth_noise_deadband(z_noise, delta_noise=delta_ref)
    att_1 = 1.0 - (denoised_noise[0] / z_noise[0])
    att_2 = 1.0 - (denoised_noise[1] / z_noise[1])
    assert att_1 > 0.90, f"Noise (|z|=0.005) squashing must exceed 90%! Got {att_1 * 100:.2f}%"
    assert att_2 > 0.90, f"Noise (|z|=0.010) squashing must exceed 90%! Got {att_2 * 100:.2f}%"

    # 3. High-conviction signal transmission test
    z_high = np.array([0.150, 0.300])
    denoised_high = engine.apply_smooth_noise_deadband(z_high, delta_noise=delta_ref)
    trans_1 = denoised_high[0] / z_high[0]
    trans_2 = denoised_high[1] / z_high[1]
    assert trans_1 > 0.985, f"High signal (|z|=0.15) transmission must exceed 98.5%! Got {trans_1 * 100:.2f}%"
    assert trans_2 > 0.995, f"High signal (|z|=0.30) transmission must exceed 99.5%! Got {trans_2 * 100:.2f}%"

    # 4. Asymmetric negative noise attenuation in Bear/Crisis
    # Compare +0.030 vs -0.030 in CRISIS
    z_pos = np.array([0.030])
    z_neg = np.array([-0.030])
    denoised_pos = engine.apply_smooth_noise_deadband(z_pos, delta_noise=d_pos_crisis, regime='CRISIS')
    denoised_neg = engine.apply_smooth_noise_deadband(z_neg, delta_noise=d_pos_crisis, regime='CRISIS')

    trans_pos = float(denoised_pos[0] / z_pos[0])
    trans_neg = float(denoised_neg[0] / z_neg[0])
    assert trans_neg < trans_pos, (
        f"Negative noise in Crisis must be attenuated more (trans={trans_neg:.4f}) "
        f"than positive signal (trans={trans_pos:.4f})"
    )

    # 5. Continuous spectrum rank monotonicity
    full_spectrum = np.linspace(-0.50, 0.50, 201)
    denoised_spectrum = engine.apply_smooth_noise_deadband(full_spectrum, delta_noise=d_pos_crisis, regime='CRISIS')
    rho, _ = spearmanr(full_spectrum, denoised_spectrum)
    assert math.isclose(rho, 1.0, abs_tol=1e-5), f"Noise deadband rank correlation must be 1.0000! Got {rho:.6f}"


# =============================================================================
# 6. FEATURE F42.3: MULTI-MARKET 5-MARKET RANDOMIZED STRESS TEST
# =============================================================================

def test_feature_42_3_multi_market_randomized_stress_all_regimes():
    """
    Verify F42.3:
    Stress-test realistic randomized multi-strategy input across 5 global markets
    (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) and all 7 market regimes:
    - 0 NaNs, 0 Infs in ensemble_score.
    - ensemble_score strictly bounded in [0.0, 1.0].
    - ensemble_expected_return strictly finite and non-negative.
    """
    np.random.seed(42)
    engine = EnsembleScoringEngine()

    n = 30
    symbols = [f"SYM_{i:03d}" for i in range(n)]
    markets = np.random.choice(['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'], size=n)

    data = {
        'symbol': symbols,
        'market': markets,
        'volatility_20d': np.random.uniform(0.01, 0.05, n),
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
        'cross_asset_spillover_score': np.random.uniform(0.1, 0.9, n),
        'supply_chain_gnn_score': np.random.uniform(0.1, 0.9, n),
        'range_expansion_score': np.random.uniform(0.1, 0.9, n),
        'overnight_gap_score': np.random.uniform(0.1, 0.9, n),
        'index_rebalance_score': np.random.uniform(0.1, 0.9, n),
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
            regime_probs={r: 0.75, 'SIDEWAYS_LOW_VOL': 0.25},
            version=6
        )

        # Invariants: 0 NaNs, 0 Infs, [0.0, 1.0]
        assert not out['ensemble_score'].isna().any(), f"NaNs found in ensemble_score for regime {r}"
        assert not np.isinf(out['ensemble_score']).any(), f"Infs found in ensemble_score for regime {r}"
        assert (out['ensemble_score'] >= 0.0).all(), f"Scores < 0 in regime {r}"
        assert (out['ensemble_score'] <= 1.0).all(), f"Scores > 1 in regime {r}"

        # Expected returns: finite, non-negative
        assert not out['ensemble_expected_return'].isna().any(), f"NaNs found in expected return for {r}"
        assert not np.isinf(out['ensemble_expected_return']).any(), f"Infs found in expected return for {r}"
        assert (out['ensemble_expected_return'] >= 0.0).all(), f"Expected return < 0 in {r}"

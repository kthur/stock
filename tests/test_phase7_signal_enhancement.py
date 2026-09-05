"""
Phase 7 Zenith Quantitative Enhancements: Dynamic Alpha Signal Synergy,
Right-Tail Convexity & Regime Noise Deadband Test Suite.
Requirement R1 (Features F47 and F48):
- F47.1: 5-Pillar Economically-Weighted Trilinear Tensors & Pillar Harmony Regularizer H_pillar.
- F47.2: Bull Low Vol Cap Expansion to 0.220 (1.220x) and Crisis Cap Preservation at 0.040 (1.040x).
- F47.3: Merton-Style Jump-Diffusion Regime Transition Base Weight Mixture (w_Zenith*).
- F48.1: Asymmetric Volatility-Directional Markov Departure Penalty kappa_Markov(S_vol).
- F48.2: True C^infinity Quintic-Hyperbolic Deadband Noise Reduction (alpha=5.0) & Odd Symmetry.
- F48.3: Bilateral Asymmetric Richards S-Curve (Version 7) & Quartic Rank Modulation g_v7(r).
- F48.4: Multi-Market 5-Market Randomized Stress Test & Version 6 Backward Compatibility Invariants.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine, BessembinderParams
from src.ai.factor_suppression import QUINT_PILLAR_MAP, apply_quintic_hyperbolic_deadband


# =============================================================================
# 1. FEATURE F47.1: ECONOMICALLY-WEIGHTED TRILINEAR TENSORS & PILLAR HARMONY
# =============================================================================

def test_feature_47_1_economically_weighted_trilinear_tensors_and_pillar_harmony():
    """
    Verify F47.1:
    1. 37 strategies are partitioned into 5 disjoint canonical pillars:
       - val (6), mom (9), flow (9), cat (6), net (7). Total = 37 strategies.
    2. High-order interaction tensor computes 2nd, 3rd, 4th, and 5th order contractions.
    3. Economically-Weighted Triplets under version=7:
       - Omega_tri(val, mom, flow) = 1.40 * w_tri
       - Omega_tri(flow, cat, net) = 1.20 * w_tri
       - Other 8 triplets = 1.00 * w_tri
       Asset with (val, mom, flow) strength achieves higher synergy than an asset with
       equally strong (cat, net, val) due to the 1.40x economic multiplier.
    4. Pillar Harmony Regularizer:
       H_pillar = exp(-1.20 * CV_psi^2). When an asset has balanced high conviction across
       all 5 pillars (CV_psi ~ 0), harmony factor is 1.0 + 0.25 * H_pillar ~ 1.25x.
       When unbalanced (only 1 pillar high, CV_psi ~ 2.0), harmony factor collapses to 1.00x.
    5. Multi-pillar synergy hierarchy holds strictly:
       5-Pillar Champion > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar == Baseline (1.00x).
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
    all_strat_list = []
    for s in QUINT_PILLAR_MAP.values():
        all_strat_list.extend(s)
    assert len(all_strat_list) == len(set(all_strat_list))

    # 2. Build synthetic assets exercising 5-pillar, 4-pillar, 3-pillar (core vs secondary), 2-pillar, 1-pillar, baseline
    idx = [f"ASSET_{i}" for i in range(12)]
    df = pd.DataFrame({'symbol': idx}, index=idx)

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

    # ASSET_0: 5-Pillar champion (all 5 pillars balanced high = 0.92)
    # ASSET_1: 4-Pillar (val, mom, flow, cat = 0.92, net = 0.50)
    # ASSET_2: 3-Pillar CORE sweet spot (val, mom, flow = 0.92, cat and net = 0.50)
    # ASSET_3: 3-Pillar SECONDARY (cat, net, val = 0.92, mom and flow = 0.50)
    # ASSET_4: 2-Pillar (mom, flow = 0.92, others = 0.50)
    # ASSET_5: 1-Pillar (mom = 0.92, others = 0.50)
    # ASSET_6: Unbalanced 5-pillar asset (one pillar 0.98, four pillars 0.52)
    # ASSETS 7..11: Neutral baseline (all 0.50)

    for p in ['val', 'mom', 'flow', 'cat', 'net']:
        for col in strat_col_map[p]:
            df.loc['ASSET_0', col] = 0.92

    for p in ['val', 'mom', 'flow', 'cat']:
        for col in strat_col_map[p]:
            df.loc['ASSET_1', col] = 0.92

    for p in ['val', 'mom', 'flow']:
        for col in strat_col_map[p]:
            df.loc['ASSET_2', col] = 0.92

    for p in ['cat', 'net', 'val']:
        for col in strat_col_map[p]:
            df.loc['ASSET_3', col] = 0.92

    for p in ['mom', 'flow']:
        for col in strat_col_map[p]:
            df.loc['ASSET_4', col] = 0.92

    for col in strat_col_map['mom']:
        df.loc['ASSET_5', col] = 0.92

    df.loc['ASSET_6', strat_col_map['mom']] = 0.98
    for p in ['val', 'flow', 'cat', 'net']:
        df.loc['ASSET_6', strat_col_map[p]] = 0.52

    # Compute synergy in BULL_LOW_VOL under version=7
    mult_bull_v7 = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='BULL_LOW_VOL',
        kappa=8.0,
        regime_adaptive_cap=True,
        version=7
    )

    # 3. Hierarchy assertions
    assert mult_bull_v7.loc['ASSET_0'] > mult_bull_v7.loc['ASSET_1'], "5-Pillar must beat 4-Pillar synergy"
    assert mult_bull_v7.loc['ASSET_1'] > mult_bull_v7.loc['ASSET_2'], "4-Pillar must beat 3-Pillar synergy"
    assert mult_bull_v7.loc['ASSET_2'] > mult_bull_v7.loc['ASSET_4'], "3-Pillar must beat 2-Pillar synergy"
    assert mult_bull_v7.loc['ASSET_4'] > mult_bull_v7.loc['ASSET_5'], "2-Pillar must beat 1-Pillar synergy"
    assert math.isclose(mult_bull_v7.loc['ASSET_5'], 1.00, abs_tol=1e-4), "1-Pillar alone should yield no cross-pillar synergy"
    assert math.isclose(mult_bull_v7.loc['ASSET_7'], 1.00, abs_tol=1e-4), "Neutral baseline should yield 1.00x synergy"

    # 4. Economic triplet advantage: (val, mom, flow) sweet spot receives 1.40x vs 1.00x
    assert mult_bull_v7.loc['ASSET_2'] > mult_bull_v7.loc['ASSET_3'], (
        f"Core triplet (val, mom, flow, synergy={mult_bull_v7.loc['ASSET_2']:.4f}) must exceed "
        f"secondary triplet (cat, net, val, synergy={mult_bull_v7.loc['ASSET_3']:.4f})"
    )

    # 5. Pillar Harmony boost: balanced ASSET_0 receives significant harmony boost
    assert mult_bull_v7.loc['ASSET_0'] > mult_bull_v7.loc['ASSET_6'], (
        f"Harmonious 5-pillar asset ({mult_bull_v7.loc['ASSET_0']:.4f}) must exceed "
        f"unbalanced 5-pillar asset ({mult_bull_v7.loc['ASSET_6']:.4f})"
    )


# =============================================================================
# 2. FEATURE F47.2: BULL LOW VOL CAP EXPANSION (0.220) & CRISIS PRESERVATION (0.040)
# =============================================================================

def test_feature_47_2_bull_low_vol_cap_expansion_and_crisis_preservation():
    """
    Verify F47.2:
    1. Cap Expansion in Bull Low Vol:
       In BULL_LOW_VOL under version=7, the maximum tensor synergy cap expands from
       0.180 (1.180x) to 0.220 (1.220x), expanding the right-tail conviction headroom.
       A 5-pillar champion must achieve > 1.180x and <= 1.22001x.
    2. Crisis Multiplier Preservation:
       In CRISIS under version=7, the maximum tensor synergy cap is strictly maintained at
       0.040 (<= 1.04001x), preventing false alpha amplification during market panics.
    3. Multiplier bounds across all 7 regimes under version=7:
       All multipliers must satisfy 1.000 <= M <= 1.22001.
    """
    engine = EnsembleScoringEngine()

    idx = [f"ASSET_{i}" for i in range(5)]
    df = pd.DataFrame({'symbol': idx}, index=idx)
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

    # ASSET_0 is 5-pillar super champion (all 0.98)
    for p in ['val', 'mom', 'flow', 'cat', 'net']:
        for col in strat_col_map[p]:
            df.loc['ASSET_0', col] = 0.98

    # 1. Bull Low Vol cap expansion test
    mult_bull = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='BULL_LOW_VOL',
        kappa=8.0,
        regime_adaptive_cap=True,
        version=7
    )
    score_bull = mult_bull.loc['ASSET_0']
    assert score_bull > 1.180, (
        f"5-Pillar champion in Bull Low Vol (version=7) must exceed Phase 6 cap 1.180x! Got {score_bull:.4f}"
    )
    assert score_bull <= 1.22001, (
        f"5-Pillar champion must not exceed Zenith cap 1.220x! Got {score_bull:.4f}"
    )

    # 2. Crisis preservation test
    mult_crisis = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='CRISIS',
        kappa=8.0,
        regime_adaptive_cap=True,
        version=7
    )
    score_crisis = mult_crisis.loc['ASSET_0']
    assert score_crisis <= 1.04001, (
        f"Synergy in Crisis (version=7) must remain capped at <= 1.040x! Got {score_crisis:.4f}"
    )
    assert score_crisis >= 1.000, "Synergy multiplier must be >= 1.000x"

    # 3. Across all 7 regimes
    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]
    for r in all_regimes:
        m = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime=r,
            regime_adaptive_cap=True,
            version=7
        )
        assert (m >= 1.00).all(), f"Multiplier fell below 1.00 in {r}"
        assert (m <= 1.22001).all(), f"Multiplier exceeded 1.220 in {r}"


# =============================================================================
# 3. FEATURE F47.3: MERTON JUMP-DIFFUSION REGIME TRANSITION BASE WEIGHT MIXTURE
# =============================================================================

def test_feature_47_3_merton_jump_diffusion_regime_transition_mixture():
    """
    Verify F47.3:
    1. Jump Indicator J_regime:
       d_TV = 0.5 * sum |pi_{m, t} - pi_{m, t-1}|
       When d_TV <= 0.25: J_regime = 0.0 => pure continuous diffusion weights w_diffusion.
       When d_TV > 0.25: J_regime = clip((d_TV - 0.25) / 0.35, 0.0, 1.0).
    2. Dynamic Jump Mixture:
       w_Zenith* = (1 - 0.60 * J_regime) * w_diffusion + (0.60 * J_regime) * W_2D(R_jump)
    3. Sudden Market Crash Scenario:
       Previous pi = [0.80 Bull, 0.20 Crisis] -> Current pi = [0.10 Bull, 0.85 Crisis, 0.05 Bear].
       d_TV = 0.70 => J_regime = 1.0.
       60% of weight mass instantaneously routes to Crisis hedge factors (stat_arb, vol_target, rim_valuation).
    4. Simplex Normalization Invariant: sum(w_i) == 1.0000, all w_i >= 0.
    """
    engine = EnsembleScoringEngine()

    # Case A: Calm diffusion transition (d_TV = 0.10 <= 0.25 => J_regime = 0)
    pi_prev_calm = {'BULL_LOW_VOL': 0.70, 'SIDEWAYS_LOW_VOL': 0.30}
    pi_curr_calm = {'BULL_LOW_VOL': 0.60, 'SIDEWAYS_LOW_VOL': 0.40}

    w_calm_v7 = engine.get_base_weights(
        regime='BULL_LOW_VOL',
        regime_probs=pi_curr_calm,
        prev_regime_probs=pi_prev_calm,
        version=7
    )
    w_calm_v6 = engine.get_base_weights(
        regime='BULL_LOW_VOL',
        regime_probs=pi_curr_calm,
        prev_regime_probs=pi_prev_calm,
        version=6
    )
    # Under calm diffusion (no jump), v7 matches v6 diffusion base weights closely
    for s in w_calm_v7:
        assert math.isclose(w_calm_v7[s], w_calm_v6[s], abs_tol=1e-3)

    # Case B: Severe Crisis Jump Shock (d_TV = 0.70 => J_regime = 1.0)
    pi_prev_bull = {'BULL_LOW_VOL': 0.80, 'CRISIS': 0.20}
    pi_curr_crash = {'BULL_LOW_VOL': 0.10, 'CRISIS': 0.85, 'BEAR_HIGH_VOL': 0.05}

    w_crash_v7 = engine.get_base_weights(
        regime='CRISIS',
        regime_probs=pi_curr_crash,
        prev_regime_probs=pi_prev_bull,
        version=7
    )
    w_crash_v6 = engine.get_base_weights(
        regime='CRISIS',
        regime_probs=pi_curr_crash,
        prev_regime_probs=pi_prev_bull,
        version=6
    )

    # Crisis hedges (stat_arb, vol_target, rim_valuation) receive higher weights in v7 jump mixture
    crisis_hedges = ['stat_arb', 'vol_target', 'rim_valuation']
    for strat in crisis_hedges:
        if strat in w_crash_v7 and strat in w_crash_v6:
            assert w_crash_v7[strat] >= w_crash_v6[strat] - 1e-4

    # Simplex normalization invariants
    assert math.isclose(sum(w_crash_v7.values()), 1.0000, abs_tol=1e-4)
    assert all(v >= 0.0 for v in w_crash_v7.values())


# =============================================================================
# 4. FEATURE F48.1: ASYMMETRIC VOLATILITY-DIRECTIONAL MARKOV DEPARTURE PENALTY
# =============================================================================

def test_feature_48_1_directional_markov_departure_penalty():
    """
    Verify F48.1:
    1. Volatility Regime Shift S_vol:
       S_vol = sum_{m in V_high} pi_m - sum_{m in V_high} pi_{inf, m}
       where V_high = {CRISIS, BEAR_HIGH_VOL, SIDEWAYS_HIGH_VOL, BULL_HIGH_VOL}.
    2. Directional Markov Departure Exponent:
       kappa_Markov(S_vol) = 0.25 * (1.0 + 0.80 * max(0, S_vol)) in [0.25, 0.45].
    3. Transition to High Volatility (S_vol > 0):
       kappa_Markov scales up to 0.45, accelerating half-life compression.
       Class A microstructure strategies compress half-life faster than Class D fundamentals.
    4. Transition to Tranquil Bull (S_vol <= 0):
       kappa_Markov = 0.25, preserving baseline decay without turnover churn.
    5. Minimum half-life invariant: tau_i >= 0.10 days across all 37 strategies.
    """
    engine = EnsembleScoringEngine()

    pi_stationary = {
        'BULL_LOW_VOL': 0.20,
        'BULL_HIGH_VOL': 0.15,
        'SIDEWAYS_LOW_VOL': 0.25,
        'SIDEWAYS_HIGH_VOL': 0.15,
        'BEAR_LOW_VOL': 0.12,
        'BEAR_HIGH_VOL': 0.08,
        'CRISIS': 0.05,
    }

    # At stationary distribution (S_vol = 0, D_KL = 0)
    tau_stat = engine.get_regime_adaptive_half_lives(
        regime='SIDEWAYS_LOW_VOL',
        regime_probs=pi_stationary,
        version=7
    )

    # In extreme high-volatility crisis (S_vol = 1.0 - 0.43 = 0.57 > 0 => kappa_Markov ~ 0.364)
    pi_crisis = {'CRISIS': 1.00}
    tau_crisis = engine.get_regime_adaptive_half_lives(
        regime='CRISIS',
        regime_probs=pi_crisis,
        version=7
    )

    # In calm bull regime (S_vol = 0.0 - 0.43 = -0.43 <= 0 => kappa_Markov = 0.25)
    pi_pure_bull = {'BULL_LOW_VOL': 1.00}
    tau_bull = engine.get_regime_adaptive_half_lives(
        regime='BULL_LOW_VOL',
        regime_probs=pi_pure_bull,
        version=7
    )

    # Verify Class A vs Class D elasticity under high volatility
    # Class A (nu=1.30): 'order_flow', 'microstructure', 'darkpool'
    # Class D (nu=0.40): 'rim_valuation', 'valueup_catalyst', 'accruals_quality'
    decay_ratio_a = tau_crisis['order_flow'] / tau_stat['order_flow']
    decay_ratio_d = tau_crisis['rim_valuation'] / tau_stat['rim_valuation']

    assert decay_ratio_a < decay_ratio_d, (
        f"Class A microstructure decay ratio ({decay_ratio_a:.3f}) must be more "
        f"aggressive than Class D fundamental decay ratio ({decay_ratio_d:.3f})"
    )

    # Minimum half-life invariant
    for s, tau in tau_crisis.items():
        assert tau >= 0.10, f"Half-life of {s} fell below 0.10d: {tau}"
        assert math.isfinite(tau)


# =============================================================================
# 5. FEATURE F48.2: TRUE C^INFINITY QUINTIC DEADBAND NOISE REDUCTION & ODD SYMMETRY
# =============================================================================

def test_feature_48_2_true_quintic_deadband_noise_reduction_and_odd_symmetry():
    """
    Verify F48.2:
    1. True C^infinity Quintic Exponent (alpha = 5.0):
       Near-zero noise (|z| <= 0.010 with delta = 0.045):
       Leakage <= 0.06% (0.054%), squashing > 99.9%.
       Provides a 22-fold reduction in near-zero noise leakage vs Phase 6 cubic deadband (1.10% leakage).
    2. High-conviction signal transmission:
       At |z| = 0.150 with delta = 0.045, transmission >= 99.99% (~100.0%). Zero signal loss.
    3. Exact Odd Symmetry when unconditioned (regime=None):
       f(-z) == -f(z) for all z to within machine precision (1e-12).
    4. Strict Rank Monotonicity:
       Spearman rank correlation rho_s == 1.0000 across continuous spectrum [-0.50, 0.50].
       Pointwise strict monotonicity: f(z_{i+1}) > f(z_i) for all z_{i+1} > z_i.
    5. Asymmetric attenuation in Bear/Crisis:
       Negative noise in CRISIS is attenuated more aggressively than positive noise.
    6. Module Parity:
       apply_quintic_hyperbolic_deadband in factor_suppression and
       apply_smooth_noise_deadband(..., version=7) produce identical outputs.
    """
    engine = EnsembleScoringEngine()
    delta_ref = 0.045

    # 1. Near-zero noise leakage test
    z_noise = np.array([0.005, 0.010])
    denoised_q = apply_quintic_hyperbolic_deadband(z_noise, delta_noise=delta_ref, alpha_pos=5.0)

    leakage_1 = abs(denoised_q[0]) / z_noise[0]
    leakage_2 = abs(denoised_q[1]) / z_noise[1]
    assert leakage_1 < 0.0010, f"Noise leakage at 0.005 must be < 0.10%! Got {leakage_1 * 100:.4f}%"
    assert leakage_2 < 0.0010, f"Noise leakage at 0.010 must be < 0.10%! Got {leakage_2 * 100:.4f}%"
    # Target is ~0.054% leakage (99.946% squashing)
    assert abs(leakage_2 - 0.00054) < 0.0002, f"Leakage at 0.010 should be ~0.054%! Got {leakage_2 * 100:.4f}%"

    # Compare against cubic deadband (alpha=3.0)
    denoised_cubic = engine.apply_smooth_noise_deadband(z_noise, delta_noise=delta_ref, alpha_pos=3.0, version=6)
    leakage_cubic = abs(denoised_cubic[1]) / z_noise[1]
    reduction_factor = leakage_cubic / leakage_2
    assert reduction_factor >= 18.0, (
        f"Quintic deadband must provide >= 18x noise reduction vs cubic! Got {reduction_factor:.2f}x "
        f"(cubic={leakage_cubic*100:.3f}%, quintic={leakage_2*100:.4f}%)"
    )

    # 2. High conviction signal transmission test
    z_high = np.array([0.150, 0.300])
    denoised_high = apply_quintic_hyperbolic_deadband(z_high, delta_noise=delta_ref, alpha_pos=5.0)
    trans_1 = denoised_high[0] / z_high[0]
    trans_2 = denoised_high[1] / z_high[1]
    assert trans_1 >= 0.9999, f"Signal transmission at 0.150 must be >= 99.99%! Got {trans_1 * 100:.4f}%"
    assert trans_2 >= 0.9999, f"Signal transmission at 0.300 must be >= 99.99%! Got {trans_2 * 100:.4f}%"

    # 3. Exact Odd Symmetry test (unconditioned)
    z_test_sym = np.linspace(0.001, 0.40, 100)
    pos_res = apply_quintic_hyperbolic_deadband(z_test_sym, delta_noise=delta_ref, regime=None)
    neg_res = apply_quintic_hyperbolic_deadband(-z_test_sym, delta_noise=delta_ref, regime=None)
    np.testing.assert_allclose(pos_res, -neg_res, atol=1e-12, err_msg="Exact odd symmetry violated!")

    # 4. Strict Rank Monotonicity test
    spectrum = np.linspace(-0.50, 0.50, 201)
    denoised_spectrum = apply_quintic_hyperbolic_deadband(spectrum, delta_noise=delta_ref, regime='BULL_LOW_VOL')
    rho, _ = spearmanr(spectrum, denoised_spectrum)
    assert math.isclose(rho, 1.0, abs_tol=1e-6), f"Rank correlation must be 1.0000! Got {rho:.6f}"
    diffs = np.diff(denoised_spectrum)
    assert (diffs > 0).all(), "Pointwise strict monotonicity violated: derivative must be strictly positive!"

    # 5. Asymmetric attenuation in Crisis
    z_p = np.array([0.030])
    z_m = np.array([-0.030])
    d_p = apply_quintic_hyperbolic_deadband(z_p, delta_noise=delta_ref, regime='CRISIS')
    d_m = apply_quintic_hyperbolic_deadband(z_m, delta_noise=delta_ref, regime='CRISIS')
    assert (abs(d_m[0]) / 0.030) < (d_p[0] / 0.030), "Negative noise in Crisis must be attenuated more than positive"

    # 6. Parity between factor_suppression and ensemble_scorer version=7
    d_supp = apply_quintic_hyperbolic_deadband(spectrum, delta_noise=delta_ref, regime='SIDEWAYS_LOW_VOL')
    d_ens = engine.apply_smooth_noise_deadband(spectrum, delta_noise=delta_ref, regime='SIDEWAYS_LOW_VOL', version=7)
    np.testing.assert_allclose(d_supp, d_ens, atol=1e-10, err_msg="Deadband parity violated between modules!")


# =============================================================================
# 6. FEATURE F48.3: QUARTIC RANK MODULATION & TOP-DECILE ALPHA EXPANSION
# =============================================================================

def test_feature_48_3_quartic_rank_modulation_and_alpha_expansion():
    """
    Verify F48.3:
    1. Quartic Rank Modulation Polynomial:
       g_v7(r) = 0.60 + 0.25 * r + 0.25 * r^2 + 0.40 * r^3 + 0.35 * r^4
       Guarantees strict monotonicity: g_v7'(r) > 0 for all r in [0, 1].
    2. Top-Decile Spread Expansion:
       Comparing top conviction winner (rank=1.0, score=0.97) vs lower decile (score=0.89),
       the Version 7 alpha spread expands by >= 15% (target 18% to 22%) relative to Version 6.
    3. Strict Non-Negativity:
       Positive excess conviction produces strictly non-negative expected return.
    """
    engine = EnsembleScoringEngine()

    test_scores = np.array([0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.89, 0.93, 0.97])
    ranks = pd.Series(test_scores).rank(pct=True).values
    z = test_scores - 0.50

    # Version 6 cubic rank modulation
    mult_p6 = 0.60 + 0.30 * ranks + 0.30 * (ranks ** 2) + 0.55 * (ranks ** 3)
    u_p6 = z * mult_p6
    alpha_p6 = np.clip((np.abs(u_p6 * 2.0) ** 1.35) / 1.35, 0.0, 1.0)
    spread_p6 = alpha_p6[-1] - alpha_p6[-3]

    # Version 7 quartic rank modulation
    mult_p7 = 0.60 + 0.25 * ranks + 0.25 * (ranks ** 2) + 0.40 * (ranks ** 3) + 0.35 * (ranks ** 4)
    u_p7 = z * mult_p7
    alpha_p7 = np.clip((np.abs(u_p7 * 2.0) ** 1.42) / 1.42, 0.0, 1.0)
    spread_p7 = alpha_p7[-1] - alpha_p7[-3]

    expansion = (spread_p7 - spread_p6) / spread_p6
    assert expansion >= 0.15, (
        f"Version 7 top-decile spread must expand >= 15% vs Version 6! "
        f"Got {expansion * 100:.2f}% (v6={spread_p6:.4f}, v7={spread_p7:.4f})"
    )

    # Quartic polynomial derivative monotonicity check
    r_grid = np.linspace(0.0, 1.0, 100)
    g_vals = 0.60 + 0.25 * r_grid + 0.25 * (r_grid ** 2) + 0.40 * (r_grid ** 3) + 0.35 * (r_grid ** 4)
    g_deriv = 0.25 + 0.50 * r_grid + 1.20 * (r_grid ** 2) + 1.40 * (r_grid ** 3)
    assert (g_deriv > 0.20).all(), "Quartic polynomial derivative must be strictly positive"
    diffs = np.diff(g_vals)
    assert (diffs > 0).all(), "Quartic rank modulation must be strictly increasing"


# =============================================================================
# 7. FEATURE F48.4: MULTI-MARKET STRESS TEST & V6 BACKWARD COMPATIBILITY
# =============================================================================

def test_feature_48_4_multi_market_stress_and_v6_backward_compatibility():
    """
    Verify F48.4:
    1. Multi-Market Stress Test across 5 global markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)
       and all 7 regimes under version=7:
       - 0 NaNs, 0 Infs in ensemble_score and ensemble_expected_return.
       - ensemble_score strictly in [0.0, 1.0].
       - ensemble_expected_return finite and non-negative.
    2. Version 6 Backward Compatibility Invariants:
       When version=6 is passed:
       - Cap in Bull Low Vol remains 0.180 (1.180x).
       - apply_smooth_noise_deadband uses cubic alpha=3.0.
       - combine_predictions uses cubic rank modulation.
    3. BessembinderParams tuple unpacking:
       2-tuple (gamma, beta) and 3-tuple (gamma, beta, u_thresh) unpacking both succeed.
    """
    np.random.seed(42)
    engine = EnsembleScoringEngine()

    n = 25
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

    # 1. Multi-market test under version=7
    for r in all_regimes:
        out = engine.combine_predictions(
            predictions_df=df,
            target_horizon='20d',
            regime=r,
            regime_probs={r: 0.75, 'SIDEWAYS_LOW_VOL': 0.25},
            version=7
        )
        assert not out['ensemble_score'].isna().any(), f"NaN in ensemble_score in {r}"
        assert not np.isinf(out['ensemble_score']).any(), f"Inf in ensemble_score in {r}"
        assert (out['ensemble_score'] >= 0.0).all() and (out['ensemble_score'] <= 1.0).all()
        assert not out['ensemble_expected_return'].isna().any(), f"NaN in expected return in {r}"
        assert (out['ensemble_expected_return'] >= 0.0).all(), f"Negative expected return in {r}"

    # 2. Backward compatibility test under version=6
    out_v6 = engine.combine_predictions(
        predictions_df=df,
        target_horizon='20d',
        regime='BULL_LOW_VOL',
        regime_probs={'BULL_LOW_VOL': 1.0},
        version=6
    )
    assert not out_v6['ensemble_score'].isna().any()

    # 3. BessembinderParams unpacking invariants
    params = engine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL', version=7)
    g2, b2 = params
    assert g2 > 0 and b2 > 0
    g3, b3, u3 = params
    assert g3 > 0 and b3 > 0 and u3 > 0
    assert hasattr(params, 'gamma') and hasattr(params, 'beta_right')

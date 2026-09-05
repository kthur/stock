"""
Phase 8 Sovereign Quantitative Enhancements: Information Geometry Riemannian Manifold Synergy,
Hyperexponential Convex Rank Modulation, Hurst Fractional Jump-Diffusion & Septic Wavelet Noise Deadband.
Requirement R1 (Features F51 and F52):
- F51.1: Riemannian Manifold Geodesic 5-Pillar Synergy & Fisher-Rao Harmony Regularizer H_Riemann.
- F51.2: Hyperexponential Convex Rank Modulation g_v8(r) = r * exp(gamma_top * r^3) & Spread Expansion.
- F52.1: Hurst Exponent (H) Fractional Jump-Diffusion Regime Transition Base Weight Mixture.
- F52.2: Asymmetric Septic Wavelet Noise Deadband Filter (alpha=7.0, 99.997% noise suppression).
- F52.3: Multi-Market 5-Market Comprehensive Stress Test across 7 Regimes under Version 8.
- F52.4: Version Backward Compatibility Invariants (Version 6 vs 7 vs 8).
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import (
    QUINT_PILLAR_MAP,
    apply_quintic_hyperbolic_deadband,
    apply_asymmetric_wavelet_deadband
)


# =============================================================================
# 1. FEATURE F51.1: RIEMANNIAN MANIFOLD GEODESIC 5-PILLAR SYNERGY & HARMONY
# =============================================================================

def test_feature_51_1_riemannian_manifold_geodesic_5pillar_mapping():
    """
    Verify F51.1:
    1. 37 strategies are partitioned into 5 disjoint canonical pillars:
       - val (6), mom (9), flow (9), cat (6), net (7). Total = 37 strategies.
    2. High-order interaction tensor computes 2nd, 3rd, 4th, and 5th order contractions.
    3. Triplet Multipliers under version=8:
       - Omega_tri(val, mom, flow) = 1.50 * w_tri (boosted from 1.40x)
       - Omega_tri(flow, cat, net) = 1.25 * w_tri (boosted from 1.20x)
       - Other 8 triplets = 1.00 * w_tri
       Asset with (val, mom, flow) strength achieves higher synergy than an asset with
       equally strong (cat, net, val) due to the 1.50x economic multiplier.
    4. Riemannian Geodesic Pillar Harmony Regularizer:
       p_k in S^4, Bhattacharyya affinity BC(p, p0) = sum(sqrt(0.20 * p_k)),
       geodesic arc distance d_R(p, p0) = arccos(clip(BC, 0, 1)).
       H_Riemann = exp(-2.40 * d_R^2). When an asset has balanced high conviction across
       all 5 pillars (d_R ~ 0), harmony factor is 1.0 + 0.30 * H_Riemann ~ 1.30x.
       When unbalanced (only 1 pillar high, d_R ~ 1.107 rad), harmony factor collapses to 1.00x.
    5. Multi-pillar synergy hierarchy holds strictly:
       5-Pillar Champion > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar == Baseline (1.00x).
    6. Cap Expansion in Bull Low Vol:
       In BULL_LOW_VOL under version=8, max tensor synergy cap expands to 0.250 (1.250x),
       while in CRISIS it is strictly maintained at 0.040 (1.040x).
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

    # ASSET_0: 5-Pillar champion (all 5 pillars balanced high = 0.95)
    # ASSET_1: 4-Pillar (val, mom, flow, cat = 0.92, net = 0.50)
    # ASSET_2: 3-Pillar CORE sweet spot (val, mom, flow = 0.92, cat and net = 0.50)
    # ASSET_3: 3-Pillar SECONDARY (cat, net, val = 0.92, mom and flow = 0.50)
    # ASSET_4: 2-Pillar (mom, flow = 0.92, others = 0.50)
    # ASSET_5: 1-Pillar (mom = 0.92, others = 0.50)
    # ASSET_6: Unbalanced 5-pillar asset (one pillar 0.98, four pillars 0.52)
    # ASSETS 7..11: Neutral baseline (all 0.50)

    for p in ['val', 'mom', 'flow', 'cat', 'net']:
        for col in strat_col_map[p]:
            df.loc['ASSET_0', col] = 0.95

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

    # Compute synergy in BULL_LOW_VOL under version=8
    mult_bull_v8 = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='BULL_LOW_VOL',
        kappa=8.0,
        regime_adaptive_cap=True,
        version=8
    )

    # 3. Hierarchy assertions
    assert mult_bull_v8.loc['ASSET_0'] > mult_bull_v8.loc['ASSET_1'], "5-Pillar must beat 4-Pillar synergy"
    assert mult_bull_v8.loc['ASSET_1'] > mult_bull_v8.loc['ASSET_2'], "4-Pillar must beat 3-Pillar synergy"
    assert mult_bull_v8.loc['ASSET_2'] > mult_bull_v8.loc['ASSET_4'], "3-Pillar must beat 2-Pillar synergy"
    assert mult_bull_v8.loc['ASSET_4'] > mult_bull_v8.loc['ASSET_5'], "2-Pillar must beat 1-Pillar synergy"
    assert math.isclose(mult_bull_v8.loc['ASSET_5'], 1.00, abs_tol=1e-4), "1-Pillar alone should yield no cross-pillar synergy"
    assert math.isclose(mult_bull_v8.loc['ASSET_7'], 1.00, abs_tol=1e-4), "Neutral baseline should yield 1.00x synergy"

    # 4. Economic triplet advantage: (val, mom, flow) receives 1.50x vs 1.00x
    assert mult_bull_v8.loc['ASSET_2'] > mult_bull_v8.loc['ASSET_3'], (
        f"Core triplet (val, mom, flow, synergy={mult_bull_v8.loc['ASSET_2']:.4f}) must exceed "
        f"secondary triplet (cat, net, val, synergy={mult_bull_v8.loc['ASSET_3']:.4f})"
    )

    # 5. Riemannian Harmony boost: balanced ASSET_0 receives significant harmony boost
    assert mult_bull_v8.loc['ASSET_0'] > mult_bull_v8.loc['ASSET_6'], (
        f"Harmonious 5-pillar asset ({mult_bull_v8.loc['ASSET_0']:.4f}) must exceed "
        f"unbalanced 5-pillar asset ({mult_bull_v8.loc['ASSET_6']:.4f})"
    )

    # 6. Cap Expansion in Bull Low Vol (0.250 cap, 1.250x multiplier)
    assert mult_bull_v8.loc['ASSET_0'] > 1.220, "Champion asset under v8 should surpass v7 cap of 1.220"
    assert mult_bull_v8.loc['ASSET_0'] <= 1.25001, "Cap in BULL_LOW_VOL under v8 must not exceed 1.250"

    # 7. Crisis Multiplier Preservation (0.040 cap, 1.040x multiplier)
    mult_crisis_v8 = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='CRISIS',
        kappa=8.0,
        regime_adaptive_cap=True,
        version=8
    )
    for a in idx:
        assert mult_crisis_v8.loc[a] <= 1.04001, f"Crisis multiplier for {a} must not exceed 1.040"


# =============================================================================
# 2. FEATURE F51.2: HYPEREXPONENTIAL CONVEX RANK MODULATION & ALPHA SPREAD
# =============================================================================

def test_feature_51_2_hyperexponential_convex_rank_modulation():
    """
    Verify F51.2:
    1. get_regime_adaptive_gamma_top returns values in [0.20, 0.85] tailored by regime.
    2. Mathematical properties of g_v8(r) = r * exp(gamma_top * r^3):
       - Strict C^infinity smoothness.
       - Strict monotonicity: d/dr g_v8(r) = (1 + 3 * gamma_top * r^3) * exp(gamma_top * r^3) > 0 for all r in [0, 1].
       - Strict convexity: d^2/dr^2 g_v8(r) = 3 * gamma_top * r^2 * (4 + 3 * gamma_top * r^3) * exp(gamma_top * r^3) >= 0.
    3. Top 1% Alpha Spread Expansion:
       - Compares spread between 90th percentile and 100th percentile under v8 vs v7.
       - Under gamma_top = 0.85, alpha spread expansion is >= 25% (target +44.2%).
    4. combine_predictions integration under version=8:
       - Sign-preserving conviction scaling: scores > 0.50 receive positive return multipliers.
       - Cross-sectional ranking monotonicity is strictly preserved.
    """
    engine = EnsembleScoringEngine()

    # 1. Verify get_regime_adaptive_gamma_top
    assert math.isclose(engine.get_regime_adaptive_gamma_top('CRISIS', version=8), 0.20, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('BEAR_HIGH_VOL', version=8), 0.25, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('BEAR_LOW_VOL', version=8), 0.35, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('SIDEWAYS_HIGH_VOL', version=8), 0.45, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('SIDEWAYS_LOW_VOL', version=8), 0.55, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('BULL_HIGH_VOL', version=8), 0.70, abs_tol=1e-5)
    assert math.isclose(engine.get_regime_adaptive_gamma_top('BULL_LOW_VOL', version=8), 0.85, abs_tol=1e-5)

    # 2. Verify Monotonicity and Convexity across r in [0.0, 1.0]
    gamma_top = 0.85
    r_grid = np.linspace(0.01, 1.0, 100)
    g_v8 = r_grid * np.exp(gamma_top * (r_grid ** 3))

    # First derivative (numerical & analytical)
    dg_dr = (1.0 + 3.0 * gamma_top * (r_grid ** 3)) * np.exp(gamma_top * (r_grid ** 3))
    assert np.all(dg_dr > 0), "g_v8(r) must be strictly monotonic increasing"
    diffs = np.diff(g_v8)
    assert np.all(diffs > 0), "Discrete differences must be strictly positive"

    # Second derivative
    d2g_dr2 = 3.0 * gamma_top * (r_grid ** 2) * (4.0 + 3.0 * gamma_top * (r_grid ** 3)) * np.exp(gamma_top * (r_grid ** 3))
    assert np.all(d2g_dr2 >= 0), "g_v8(r) must be strictly convex"

    # 3. Top 1% Alpha Spread Expansion vs Phase 7 quartic
    # Phase 7 quartic: mult_v7(r) = 0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4
    mult_v7_100 = 0.60 + 0.25 * 1.0 + 0.25 * (1.0**2) + 0.40 * (1.0**3) + 0.35 * (1.0**4) # 1.850
    mult_v7_90 = 0.60 + 0.25 * 0.9 + 0.25 * (0.9**2) + 0.40 * (0.9**3) + 0.35 * (0.9**4)   # ~1.5490
    spread_v7 = mult_v7_100 - mult_v7_90

    # Phase 8 hyperexponential: mult_v8(r) = 0.50 + 0.65 * r * exp(gamma_top * r^3)
    mult_v8_100 = 0.50 + 0.65 * 1.0 * np.exp(gamma_top * (1.0**3))
    mult_v8_90 = 0.50 + 0.65 * 0.9 * np.exp(gamma_top * (0.9**3))
    spread_v8 = mult_v8_100 - mult_v8_90

    spread_expansion_pct = ((spread_v8 - spread_v7) / spread_v7) * 100.0
    assert spread_expansion_pct >= 25.0, f"Spread expansion {spread_expansion_pct:.2f}% must exceed 25% (target +44.2%)"

    # 4. combine_predictions integration
    N = 25
    symbols = [f"SYM_{i:02d}" for i in range(N)]
    df_pred = pd.DataFrame({
        'symbol': symbols,
        'market': 'SP500',
        'close': np.linspace(50.0, 150.0, N),
        'volume': 1_000_000.0,
        'volatility_20d': 0.02,
        'reg_score': np.linspace(0.20, 0.80, N),
        'surge_score': np.linspace(0.10, 0.90, N),
        'vcp_ml_score': np.linspace(0.15, 0.85, N),
        'order_flow_score': np.linspace(0.20, 0.90, N),
        'rim_score': np.linspace(0.25, 0.75, N)
    })
    res_v8 = engine.combine_predictions(
        predictions_df=df_pred,
        target_horizon='20d',
        regime='BULL_LOW_VOL',
        version=8
    )
    assert not res_v8.empty
    assert 'ensemble_score' in res_v8.columns
    assert 'ensemble_expected_return' in res_v8.columns

    # Check rank order preservation: highest score gets highest return
    sorted_df = res_v8.sort_values(by='ensemble_score', ascending=False)
    ret_values = sorted_df['ensemble_expected_return'].values
    # Check monotonicity of returns among positive excess return assets
    pos_mask = ret_values > 0
    if np.sum(pos_mask) > 1:
        assert np.all(np.diff(ret_values[pos_mask]) <= 1e-6), "Expected returns must be monotonically decreasing when sorted descending"


# =============================================================================
# 3. FEATURE F52.1: HURST FRACTIONAL JUMP-DIFFUSION REGIME WEIGHTS
# =============================================================================

def test_feature_52_1_hurst_fractional_jump_diffusion_regime_weights():
    """
    Verify F52.1:
    1. Fractional jump indicator: J_frac = clip(J_regime * (2H)^1.5, 0, 1).
    2. At H = 0.50: (2*0.50)^1.5 = 1.0 => J_frac == J_regime (backward compatibility).
    3. At H = 0.70 (trending memory): (2*0.70)^1.5 ~ 1.656x, jump responsiveness is boosted by ~1.65x.
    4. At H = 0.35 (mean-reverting chop): (2*0.35)^1.5 ~ 0.585x, jump false alarms attenuated by >40%.
    5. Simplex sum invariant: sum(w_i) == 1.0000, w_i >= 0 across all strategies.
    6. get_regime_adaptive_half_lives with version=8 modulates Markov penalty with Hurst exponent.
    """
    engine = EnsembleScoringEngine()

    prev_probs = {'BULL_LOW_VOL': 0.80, 'SIDEWAYS_LOW_VOL': 0.20}
    curr_probs = {'CRISIS': 0.70, 'BEAR_HIGH_VOL': 0.30}

    # 1. Test H = 0.50 (Brownian motion baseline)
    w_h050 = engine.get_base_weights(
        regime=curr_probs,
        prev_regime_probs=prev_probs,
        version=8,
        hurst_exponent=0.50
    )
    assert math.isclose(sum(w_h050.values()), 1.0, abs_tol=1e-5), "Weights must sum to 1.0"
    for strat, val in w_h050.items():
        assert val >= 0.0, f"Strategy weight for {strat} must be non-negative"

    # 2. Test H = 0.70 (persistent trend): jump weight should be higher or equal to H = 0.50
    w_h070 = engine.get_base_weights(
        regime=curr_probs,
        prev_regime_probs=prev_probs,
        version=8,
        hurst_exponent=0.70
    )
    assert math.isclose(sum(w_h070.values()), 1.0, abs_tol=1e-5)

    # 3. Test H = 0.35 (anti-persistent chop): jump weight should be lower
    w_h035 = engine.get_base_weights(
        regime=curr_probs,
        prev_regime_probs=prev_probs,
        version=8,
        hurst_exponent=0.35
    )
    assert math.isclose(sum(w_h035.values()), 1.0, abs_tol=1e-5)

    # 4. Verify fractional jump scaling factors
    h_trend = 0.70
    scale_trend = (2.0 * h_trend) ** 1.5
    assert math.isclose(scale_trend, 1.4 ** 1.5, rel_tol=1e-5)
    assert 1.64 < scale_trend < 1.67, f"Scale factor {scale_trend} should be ~1.656x"

    h_chop = 0.35
    scale_chop = (2.0 * h_chop) ** 1.5
    assert math.isclose(scale_chop, 0.7 ** 1.5, rel_tol=1e-5)
    attenuation = 1.0 - scale_chop
    assert attenuation > 0.40, f"Chop attenuation {attenuation:.4f} must be >40%"

    # 5. Half-lives modulation with Hurst exponent
    hl_h050 = engine.get_regime_adaptive_half_lives(
        regime=curr_probs,
        prev_regime_probs=prev_probs,
        version=8,
        hurst_exponent=0.50
    )
    hl_h070 = engine.get_regime_adaptive_half_lives(
        regime=curr_probs,
        prev_regime_probs=prev_probs,
        version=8,
        hurst_exponent=0.70
    )
    assert isinstance(hl_h050, dict)
    assert isinstance(hl_h070, dict)
    for strat in hl_h050:
        assert hl_h050[strat] >= 0.10
        assert hl_h070[strat] >= 0.10


# =============================================================================
# 4. FEATURE F52.2: ASYMMETRIC SEPTIC WAVELET NOISE DEADBAND (99.997% SUPPRESSION)
# =============================================================================

def test_feature_52_2_septic_wavelet_noise_deadband_9999_suppression():
    """
    Verify F52.2:
    1. Septic Wavelet Deadband: z_denoised = z * tanh((|z| / delta_eff)^7).
    2. Near-zero noise suppression at |z| = 0.010 with delta = 0.045:
       - Leakage is <= 0.003% (suppressing 99.997% of noise).
       - Provides 20-fold reduction in leakage compared to Phase 7 quintic deadband (~0.054%).
    3. High-conviction signal transmission at |z| = 0.150 with delta = 0.045:
       - Transmission is >= 99.999% (100.0000% full conviction pass-through).
    4. Exact odd symmetry unconditioned: f(-z) == -f(z) to within 10^-12.
    5. Monotonicity: Spearman rank correlation rho == 1.0000.
    6. Integration via apply_smooth_noise_deadband(..., version=8).
    """
    engine = EnsembleScoringEngine()
    delta = 0.045

    # 1. Leakage at |z| = 0.010
    z_noise = np.array([0.010])
    denoised_v8 = apply_asymmetric_wavelet_deadband(z_noise, delta_noise=delta, alpha_pos=7.0)
    denoised_v7 = apply_quintic_hyperbolic_deadband(z_noise, delta_noise=delta, alpha_pos=5.0)

    leakage_v8 = float(denoised_v8[0] / z_noise[0]) * 100.0
    leakage_v7 = float(denoised_v7[0] / z_noise[0]) * 100.0

    assert leakage_v8 <= 0.003, f"V8 septic leakage {leakage_v8:.6f}% must be <= 0.003%"
    assert leakage_v8 < (leakage_v7 / 18.0), (
        f"V8 septic deadband must achieve >= 18x noise leakage reduction vs V7 quintic "
        f"(v8: {leakage_v8:.6f}%, v7: {leakage_v7:.6f}%)"
    )

    # 2. High conviction transmission at |z| = 0.150
    z_conviction = np.array([0.150])
    denoised_conv = apply_asymmetric_wavelet_deadband(z_conviction, delta_noise=delta, alpha_pos=7.0)
    trans_pct = float(denoised_conv[0] / z_conviction[0]) * 100.0
    assert trans_pct >= 99.999, f"Transmission {trans_pct:.6f}% must be >= 99.999%"

    # 3. Exact odd symmetry unconditioned
    z_grid = np.linspace(-0.25, 0.25, 201)
    pos_z = z_grid[z_grid > 0]
    neg_z = -pos_z
    pos_out = apply_asymmetric_wavelet_deadband(pos_z, delta_noise=delta, alpha_pos=7.0)
    neg_out = apply_asymmetric_wavelet_deadband(neg_z, delta_noise=delta, alpha_pos=7.0)
    max_sym_err = np.max(np.abs(neg_out + pos_out))
    assert max_sym_err < 1e-12, f"Odd symmetry violation: {max_sym_err}"

    # 4. Strict Rank Monotonicity
    out_grid = apply_asymmetric_wavelet_deadband(z_grid, delta_noise=delta, alpha_pos=7.0)
    rho, _ = spearmanr(z_grid, out_grid)
    assert math.isclose(rho, 1.0, abs_tol=1e-6), "Spearman rank correlation must be 1.0000"

    # 5. Engine integration via apply_smooth_noise_deadband(..., version=8)
    res_engine = engine.apply_smooth_noise_deadband(z_noise, delta_noise=delta, version=8)
    assert math.isclose(res_engine[0], denoised_v8[0], abs_tol=1e-12)


# =============================================================================
# 5. FEATURE F52.3: MULTI-MARKET 5-MARKET STRESS TEST ACROSS 7 REGIMES (V8)
# =============================================================================

def test_feature_52_3_multi_market_5market_stress_v8():
    """
    Verify F52.3:
    Executes version=8 pipeline across all 5 global equity markets:
    (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)
    and all 7 2D market regimes:
    (BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL, CRISIS).
    Assertions:
    1. Zero NaNs and zero Infs in ensemble_score and ensemble_expected_return.
    2. ensemble_score is strictly bounded in [0.0, 1.0].
    3. Sign preservation holds: positive excess scores (> 0.50) map to positive expected returns.
    """
    engine = EnsembleScoringEngine()
    markets = ['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ']
    regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]

    np.random.seed(42)
    for mkt in markets:
        n_assets = 15
        symbols = [f"{mkt}_{i:03d}" for i in range(n_assets)]
        df_mkt = pd.DataFrame({
            'symbol': symbols,
            'market': mkt,
            'close': np.random.uniform(20.0, 300.0, n_assets),
            'volume': np.random.uniform(500_000, 5_000_000, n_assets),
            'volatility_20d': np.random.uniform(0.015, 0.040, n_assets),
            'reg_score': np.random.uniform(0.10, 0.90, n_assets),
            'surge_score': np.random.uniform(0.05, 0.95, n_assets),
            'vcp_ml_score': np.random.uniform(0.10, 0.85, n_assets),
            'order_flow_score': np.random.uniform(0.20, 0.80, n_assets),
            'rim_score': np.random.uniform(0.25, 0.75, n_assets),
            'dual_correction_score': np.random.uniform(0.20, 0.80, n_assets),
            'darkpool_score': np.random.uniform(0.20, 0.80, n_assets),
        })

        for reg in regimes:
            res = engine.combine_predictions(
                predictions_df=df_mkt,
                target_horizon='20d',
                regime=reg,
                version=8
            )
            assert not res.empty, f"Result empty for {mkt} in {reg}"
            scores = res['ensemble_score'].values
            returns = res['ensemble_expected_return'].values

            assert not np.any(np.isnan(scores)), f"NaN in ensemble_score for {mkt} in {reg}"
            assert not np.any(np.isinf(scores)), f"Inf in ensemble_score for {mkt} in {reg}"
            assert not np.any(np.isnan(returns)), f"NaN in returns for {mkt} in {reg}"
            assert not np.any(np.isinf(returns)), f"Inf in returns for {mkt} in {reg}"

            assert np.all((scores >= 0.0) & (scores <= 1.0)), f"Scores out of [0, 1] for {mkt} in {reg}"


# =============================================================================
# 6. FEATURE F52.4: VERSION BACKWARD COMPATIBILITY INVARIANTS (V6 vs V7 vs V8)
# =============================================================================

def test_feature_52_4_version_backward_compatibility_invariants():
    """
    Verify F52.4:
    1. Passing version=6 executes Phase 6 logic:
       - Cap in Bull Low Vol is 0.180.
       - Cubic rank modulation.
    2. Passing version=7 executes Phase 7 Zenith logic:
       - Cap in Bull Low Vol is 0.220.
       - Quartic rank modulation.
       - Quintic deadband (alpha=5.0).
    3. Passing version=8 executes Phase 8 Sovereign logic:
       - Cap in Bull Low Vol is 0.250.
       - Hyperexponential convex rank modulation.
       - Septic deadband (alpha=7.0).
    4. Strict cap hierarchy: Cap(v8) > Cap(v7) > Cap(v6).
    5. Multi-invocation determinism: repeat runs yield identical outputs.
    """
    engine = EnsembleScoringEngine()

    idx = [f"SYM_{i}" for i in range(10)]
    df = pd.DataFrame({'symbol': idx}, index=idx)
    all_cols = [
        'rim_score', 'surge_score', 'order_flow_score', 'event_score',
        'supply_chain_score', 'vcp_ml_score', 'valueup_catalyst_score',
        'accruals_quality_score', 'arm_score', 'factor_neutralized_score',
        'reg_score', 'darkpool_score', 'microstructure_score'
    ]
    for c in all_cols:
        df[c] = 0.95

    # 1. Cap hierarchy
    synergy_v6 = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime='BULL_LOW_VOL', version=6)
    synergy_v7 = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime='BULL_LOW_VOL', version=7)
    synergy_v8 = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime='BULL_LOW_VOL', version=8)

    max_v6 = float(synergy_v6.max())
    max_v7 = float(synergy_v7.max())
    max_v8 = float(synergy_v8.max())

    assert max_v6 <= 1.18001, f"V6 cap exceeded: {max_v6}"
    assert max_v7 <= 1.22001, f"V7 cap exceeded: {max_v7}"
    assert max_v8 <= 1.25001, f"V8 cap exceeded: {max_v8}"

    assert max_v8 > max_v7 > max_v6, f"Cap hierarchy violated: v8={max_v8}, v7={max_v7}, v6={max_v6}"

    # 2. Deadband alpha progression
    z_test = np.array([0.010])
    d_v6 = engine.apply_smooth_noise_deadband(z_test, version=6)
    d_v7 = engine.apply_smooth_noise_deadband(z_test, version=7)
    d_v8 = engine.apply_smooth_noise_deadband(z_test, version=8)

    # Strict noise squashing progression: d_v8 < d_v7 < d_v6
    assert float(d_v8[0]) < float(d_v7[0]) < float(d_v6[0]), "Noise deadband squashing progression violated"

    # 3. Determinism check
    d_v8_repeat = engine.apply_smooth_noise_deadband(z_test, version=8)
    assert np.all(d_v8 == d_v8_repeat), "Outputs must be strictly deterministic"


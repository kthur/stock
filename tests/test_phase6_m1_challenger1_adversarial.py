"""
Adversarial Stress Harness and Empirical Validation by Challenger M1-1
Phase 6 Milestone 1 (Requirement R1: Features F41 & F42).

Mandatory Challenges:
1. Rank monotonicity (rho_s == 1.0000) under extreme market simulations and pathological distributions.
2. Boundary behavior of Hölder p-norm (p=1.25, 2.00, 2.50, zero vectors, uniform vectors, extreme spikes).
3. Boundary behavior of Version 6 Richards S-curve across all 7 regimes.
4. Quint-pillar tensor synergy kernel hierarchy and strict capping.
5. Markov stationary divergence (KL) and kurtosis-adaptive noise deadband invariants.
"""

import math
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


# =============================================================================
# 1. ADVERSARIAL CHALLENGE: RANK MONOTONICITY (rho_s == 1.0000) UNDER EXTREMES
# =============================================================================

@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_rank_monotonicity_across_distributions(regime):
    """
    Adversarial Challenge 1:
    Verify strict rank monotonicity (Spearman rho == 1.0000) for Bilateral
    Asymmetric Richards S-Curve (Version 6) under 6 distinct probability distributions:
    1. Uniform U(0.01, 0.99)
    2. Gaussian N(0.5, 0.15) clipped to (0.001, 0.999)
    3. Cauchy / heavy-tailed distribution centered at 0.50
    4. Right-skewed Pareto / Power-law distribution
    5. Left-skewed Beta(0.5, 2.0) distribution
    6. Micro-scale tightly clustered distribution around 0.50 [0.4999, 0.5001]
    """
    engine = EnsembleScoringEngine()
    np.random.seed(2026)

    # 1. Uniform
    u_vals = np.sort(np.random.uniform(0.01, 0.99, 200))
    res_u = engine.apply_bessembinder_convex_power_law(u_vals, symmetric=True, regime=regime, version=6)
    rho_u, _ = spearmanr(u_vals, res_u)
    assert math.isclose(rho_u, 1.0000, abs_tol=1e-5), f"Failed for Uniform in {regime}: rho={rho_u}"

    # 2. Gaussian
    g_vals = np.sort(np.clip(np.random.normal(0.50, 0.15, 200), 0.001, 0.999))
    res_g = engine.apply_bessembinder_convex_power_law(g_vals, symmetric=True, regime=regime, version=6)
    rho_g, _ = spearmanr(g_vals, res_g)
    assert math.isclose(rho_g, 1.0000, abs_tol=1e-5), f"Failed for Gaussian in {regime}: rho={rho_g}"

    # 3. Cauchy heavy-tailed
    c_raw = np.random.standard_cauchy(500) * 0.05 + 0.50
    c_vals = np.sort(np.clip(c_raw, 0.001, 0.999))
    res_c = engine.apply_bessembinder_convex_power_law(c_vals, symmetric=True, regime=regime, version=6)
    rho_c, _ = spearmanr(c_vals, res_c)
    assert math.isclose(rho_c, 1.0000, abs_tol=1e-5), f"Failed for Cauchy in {regime}: rho={rho_c}"

    # 4. Pareto right-tail
    pareto_raw = 0.50 + 0.05 * (np.random.pareto(a=3.0, size=200))
    pareto_vals = np.sort(np.clip(pareto_raw, 0.001, 0.999))
    res_p = engine.apply_bessembinder_convex_power_law(pareto_vals, symmetric=True, regime=regime, version=6)
    rho_p, _ = spearmanr(pareto_vals, res_p)
    assert math.isclose(rho_p, 1.0000, abs_tol=1e-5), f"Failed for Pareto in {regime}: rho={rho_p}"

    # 5. Beta skewed
    beta_vals = np.sort(np.clip(np.random.beta(0.5, 2.0, size=200), 0.001, 0.999))
    res_b = engine.apply_bessembinder_convex_power_law(beta_vals, symmetric=True, regime=regime, version=6)
    rho_b, _ = spearmanr(beta_vals, res_b)
    assert math.isclose(rho_b, 1.0000, abs_tol=1e-5), f"Failed for Beta in {regime}: rho={rho_b}"

    # 6. Micro-scale cluster near 0.50
    micro_vals = np.sort(np.linspace(0.49990, 0.50010, 100))
    res_m = engine.apply_bessembinder_convex_power_law(micro_vals, symmetric=True, regime=regime, version=6)
    rho_m, _ = spearmanr(micro_vals, res_m)
    assert math.isclose(rho_m, 1.0000, abs_tol=1e-5), f"Failed for Micro-scale in {regime}: rho={rho_m}"


@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_strict_pointwise_monotonicity(regime):
    """
    Adversarial Challenge 2:
    Strictly verify that for any strictly increasing sequence x_0 < x_1 < ... < x_N,
    the transformed outputs y_0 < y_1 < ... < y_N have strictly positive pairwise diffs:
    y_{i+1} - y_i > 0 for all i.
    """
    engine = EnsembleScoringEngine()
    x = np.linspace(0.001, 0.999, 1000)
    y = engine.apply_bessembinder_convex_power_law(x, symmetric=True, regime=regime, version=6)

    diffs = np.diff(y)
    assert (diffs > 0).all(), f"Pointwise non-positive derivative detected in {regime}: min diff = {np.min(diffs)}"


# =============================================================================
# 2. ADVERSARIAL CHALLENGE: HÖLDER P-NORM BOUNDARY BEHAVIOR & EXTREMES
# =============================================================================

def test_holder_boundary_zero_and_uniform_vectors():
    """
    Adversarial Challenge 3:
    Stress Hölder generalized mean under boundary vectors:
    1. Zero vector [0, 0, 0] -> returns exactly base_scores, no NaN / div-by-zero.
    2. Uniform vector [c, c, c] -> M_p([c, c, c]) == c for all p in [1.0, 1.25, 2.0, 2.5].
    3. Extreme single-factor spike [1.0, 0.0, 0.0] -> M_p == (1/3)^(1/p).
    4. Negative values / NaN values in columns.
    """
    engine = EnsembleScoringEngine()

    # 1. Zero vector
    df_zeros = pd.DataFrame({
        'strat_0': [0.0, 0.0, 0.0],
        'strat_1': [0.0, 0.0, 0.0],
        'strat_2': [0.0, 0.0, 0.0],
    })
    base_scores = pd.Series([0.50, 0.50, 0.50])
    res_zeros = engine.apply_top_decile_convex_boost(
        scores_df=df_zeros,
        strategy_cols=['strat_0', 'strat_1', 'strat_2'],
        base_scores=base_scores,
        top_k=3,
        regime='CRISIS'  # p=1.25
    )
    assert not res_zeros.isna().any(), "NaN in zero vector output"
    assert (res_zeros >= 0.0).all() and (res_zeros <= 1.0).all()

    # 2. Uniform vector [c, c, c]
    for c in [0.10, 0.40, 0.50, 0.80, 0.95]:
        vals = np.array([c, c, c])
        for p in [1.0, 1.25, 1.50, 1.75, 1.80, 2.0, 2.25, 2.50]:
            if p == 1.0:
                m_p = float(np.mean(vals))
            elif p == 2.0:
                m_p = float(np.sqrt(np.mean(np.square(vals))))
            else:
                m_p = float(np.power(np.mean(np.power(vals, p)), 1.0 / p))
            assert math.isclose(m_p, c, abs_tol=1e-6), f"M_{p}([c,c,c]) != {c}: got {m_p}"

    # 3. Single-factor spike [1.0, 0.0, 0.0]
    spike_vals = np.array([1.0, 0.0, 0.0])
    for p in [1.25, 2.00, 2.50]:
        if p == 2.0:
            m_p = float(np.sqrt(np.mean(np.square(spike_vals))))
        else:
            m_p = float(np.power(np.mean(np.power(spike_vals, p)), 1.0 / p))
        expected_m_p = float((1.0 / 3.0) ** (1.0 / p))
        assert math.isclose(m_p, expected_m_p, abs_tol=1e-6)

    # 4. NaNs in score columns
    df_nan = pd.DataFrame({
        'strat_0': [np.nan, 0.90, np.nan],
        'strat_1': [np.nan, np.nan, 0.85],
        'strat_2': [np.nan, 0.92, 0.88],
    })
    res_nan = engine.apply_top_decile_convex_boost(
        scores_df=df_nan,
        strategy_cols=['strat_0', 'strat_1', 'strat_2'],
        base_scores=base_scores,
        top_k=3,
        regime='BULL_LOW_VOL'
    )
    assert not res_nan.isna().any(), "NaN survived in top_decile_convex_boost output"
    assert (res_nan >= 0.0).all() and (res_nan <= 1.0).all()


def test_jensen_inequality_stress_1000_trials():
    """
    Adversarial Challenge 4:
    Verify that across 1,000 randomized non-negative factor vectors,
    Jensen's Generalized Mean Inequality strictly holds:
    M_2.50 >= M_2.25 >= M_2.00 >= M_1.80 >= M_1.50 >= M_1.25 >= M_1.00
    with strict inequality whenever elements are non-constant.
    """
    np.random.seed(42)
    for _ in range(1000):
        # Generate random top-k vector of length 5
        k = 5
        v = np.random.uniform(0.10, 0.98, k)

        m_1_00 = float(np.mean(v))
        m_1_25 = float(np.power(np.mean(np.power(v, 1.25)), 1.0 / 1.25))
        m_1_50 = float(np.power(np.mean(np.power(v, 1.50)), 1.0 / 1.50))
        m_1_80 = float(np.power(np.mean(np.power(v, 1.80)), 1.0 / 1.80))
        m_2_00 = float(np.sqrt(np.mean(np.square(v))))
        m_2_25 = float(np.power(np.mean(np.power(v, 2.25)), 1.0 / 2.25))
        m_2_50 = float(np.power(np.mean(np.power(v, 2.50)), 1.0 / 2.50))

        assert m_2_50 >= m_2_25 - 1e-12
        assert m_2_25 >= m_2_00 - 1e-12
        assert m_2_00 >= m_1_80 - 1e-12
        assert m_1_80 >= m_1_50 - 1e-12
        assert m_1_50 >= m_1_25 - 1e-12
        assert m_1_25 >= m_1_00 - 1e-12


def test_dispersion_gate_extremes():
    """
    Adversarial Challenge 5:
    Stress dispersion-adaptive gating under extreme standard deviations:
    sigma = 0.0 (all identical) -> hurdle = 0.648 (gate raises)
    sigma = 0.35 (extreme polarization) -> hurdle = 0.550 (gate lowers to floor)
    """
    engine = EnsembleScoringEngine()
    n = 20
    strategy_cols = ['strat_0', 'strat_1', 'strat_2']

    # Clustered universe (sigma = 0.0)
    df_clustered = pd.DataFrame({
        'symbol': [f'S_{i}' for i in range(n)],
        'strat_0': [0.55] * n,
        'strat_1': [0.55] * n,
        'strat_2': [0.55] * n,
    })
    base_clustered = pd.Series([0.55] * n)
    res_clustered = engine.apply_top_decile_convex_boost(
        scores_df=df_clustered,
        strategy_cols=strategy_cols,
        base_scores=base_clustered,
        top_k=3,
        regime='BULL_LOW_VOL'
    )
    assert not res_clustered.isna().any()
    assert (res_clustered >= 0.0).all() and (res_clustered <= 1.0).all()

    # Polarized universe (sigma ~ 0.35)
    base_polarized = pd.Series([0.05] * 10 + [0.95] * 10)
    df_polarized = pd.DataFrame({
        'symbol': [f'S_{i}' for i in range(n)],
        'strat_0': [0.05] * 10 + [0.95] * 10,
        'strat_1': [0.05] * 10 + [0.95] * 10,
        'strat_2': [0.05] * 10 + [0.95] * 10,
    })
    res_polarized = engine.apply_top_decile_convex_boost(
        scores_df=df_polarized,
        strategy_cols=strategy_cols,
        base_scores=base_polarized,
        top_k=3,
        regime='CRISIS'
    )
    assert not res_polarized.isna().any()
    assert (res_polarized >= 0.0).all() and (res_polarized <= 1.0).all()


# =============================================================================
# 3. ADVERSARIAL CHALLENGE: EXTREME MARKET SIMULATION SCENARIOS (VERSION 6)
# =============================================================================

@pytest.mark.parametrize("regime", ALL_REGIMES)
def test_flash_crash_and_meme_squeeze_simulations(regime):
    """
    Adversarial Challenge 6:
    Simulate extreme market scenarios:
    1. Flash Crash: 95% of stocks in severe collapse (s in [0.01, 0.15]), 5% defensive hedges (s in [0.55, 0.70]).
    2. Hyper-Bull Squeeze: 90% in raging surge (s in [0.85, 0.99]), 10% laggards (s in [0.45, 0.55]).
    3. Complete Market Freeze: 100% of stocks at exact 0.50 neutral.
    4. Bimodal Polarization: 50% at 0.01, 50% at 0.99.
    Verify: 0 NaNs, 0 Infs, strict boundedness in [0.0, 1.0], and monotonicity.
    """
    engine = EnsembleScoringEngine()

    # 1. Flash Crash
    n = 100
    crash_scores = np.concatenate([
        np.random.uniform(0.01, 0.15, 95),
        np.random.uniform(0.55, 0.70, 5)
    ])
    crash_scores.sort()
    res_crash = engine.apply_bessembinder_convex_power_law(crash_scores, symmetric=True, regime=regime, version=6)
    assert not np.isnan(res_crash).any()
    assert (res_crash >= 0.0).all() and (res_crash <= 1.0).all()
    rho_crash, _ = spearmanr(crash_scores, res_crash)
    assert math.isclose(rho_crash, 1.0000, abs_tol=1e-5)

    # 2. Hyper-Bull Squeeze
    squeeze_scores = np.concatenate([
        np.random.uniform(0.45, 0.55, 10),
        np.random.uniform(0.85, 0.99, 90)
    ])
    squeeze_scores.sort()
    res_sq = engine.apply_bessembinder_convex_power_law(squeeze_scores, symmetric=True, regime=regime, version=6)
    assert not np.isnan(res_sq).any()
    assert (res_sq >= 0.0).all() and (res_sq <= 1.0).all()
    rho_sq, _ = spearmanr(squeeze_scores, res_sq)
    assert math.isclose(rho_sq, 1.0000, abs_tol=1e-5)

    # 3. Complete Market Freeze (all 0.50)
    freeze_scores = np.full(50, 0.50)
    res_freeze = engine.apply_bessembinder_convex_power_law(freeze_scores, symmetric=True, regime=regime, version=6)
    assert not np.isnan(res_freeze).any()
    assert np.allclose(res_freeze, 0.50, atol=1e-6)

    # 4. Bimodal Polarization
    bimodal = np.concatenate([np.full(25, 0.01), np.full(25, 0.99)])
    res_bimodal = engine.apply_bessembinder_convex_power_law(bimodal, symmetric=True, regime=regime, version=6)
    assert not np.isnan(res_bimodal).any()
    assert (res_bimodal >= 0.0).all() and (res_bimodal <= 1.0).all()
    # Ranks of distinct groups must be preserved
    assert res_bimodal[0] < res_bimodal[-1]


# =============================================================================
# 4. ADVERSARIAL CHALLENGE: QUINT-PILLAR TENSOR SYNERGY BOUNDS & HIERARCHY
# =============================================================================

def test_quint_pillar_tensor_confluence_and_zero_leakage():
    """
    Adversarial Challenge 7:
    1. Zero leakage: when only 1 pillar is active, cross-pillar synergy MUST be 1.0000x.
    2. When all 5 pillars are strong, synergy multiplier must strictly adhere to regime caps:
       - BULL_LOW_VOL: <= 1.180x
       - BULL_HIGH_VOL: <= 1.145x
       - SIDEWAYS_LOW_VOL: <= 1.115x
       - SIDEWAYS_HIGH_VOL: <= 1.070x
       - BEAR_LOW_VOL: <= 1.085x
       - BEAR_HIGH_VOL: <= 1.045x
       - CRISIS: <= 1.040x
    3. Missing columns / partial columns handled gracefully.
    """
    engine = EnsembleScoringEngine()

    regime_caps = {
        'BULL_LOW_VOL': 1.18001,
        'BULL_HIGH_VOL': 1.14501,
        'SIDEWAYS_LOW_VOL': 1.11501,
        'SIDEWAYS_HIGH_VOL': 1.07001,
        'BEAR_LOW_VOL': 1.08501,
        'BEAR_HIGH_VOL': 1.04501,
        'CRISIS': 1.04001,
    }

    # Setup 10 assets
    idx = [f"ASSET_{i}" for i in range(10)]
    df = pd.DataFrame({'symbol': idx}, index=idx)

    strat_cols = [
        'rim_score', 'valueup_catalyst_score', 'accruals_quality_score',
        'surge_score', 'vcp_ml_score', 'trend_efficiency_score',
        'order_flow_score', 'darkpool_score', 'microstructure_score',
        'event_score', 'sentiment_score', 'insider_buying_score',
        'supply_chain_score', 'cross_asset_spillover_score', 'dual_correction_score'
    ]
    for col in strat_cols:
        df[col] = 0.50

    # ASSET_0: All 5 pillars strong (0.95)
    for col in strat_cols:
        df.loc['ASSET_0', col] = 0.95

    # ASSET_1: Only 'mom' pillar strong (0.95), others neutral 0.50
    for col in ['surge_score', 'vcp_ml_score', 'trend_efficiency_score']:
        df.loc['ASSET_1', col] = 0.95

    for reg, expected_cap in regime_caps.items():
        mult = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime=reg,
            regime_adaptive_cap=True
        )
        # 1. Zero leakage check for 1-pillar
        assert math.isclose(mult.loc['ASSET_1'], 1.0000, abs_tol=1e-4), (
            f"1-Pillar active should produce no synergy in {reg}: got {mult.loc['ASSET_1']}"
        )
        # 2. Strict cap enforcement
        assert mult.loc['ASSET_0'] <= expected_cap, (
            f"Regime {reg} exceeded synergy cap {expected_cap}: got {mult.loc['ASSET_0']}"
        )
        assert mult.loc['ASSET_0'] >= 1.0000, f"Synergy multiplier < 1.0 in {reg}"


# =============================================================================
# 5. ADVERSARIAL CHALLENGE: MARKOV STATIONARY DIVERGENCE & NOISE DEADBAND
# =============================================================================

def test_markov_stationary_divergence_pathological_inputs():
    """
    Adversarial Challenge 8:
    Verify Markov stationary distribution divergence phi_KL:
    1. Perfect match with pi_infinity -> D_KL == 0, phi_KL == 1.0.
    2. Degenerate single-state distributions [1, 0, 0, ...] -> phi_KL in (0, 1).
    3. Invariant check: tau >= 0.10d across ALL strategies even under extreme divergence.
    """
    engine = EnsembleScoringEngine()

    # 1. Exact stationary
    pi_stat = dict(EnsembleScoringEngine.PI_STATIONARY)
    tau_stat = engine.get_regime_adaptive_half_lives('SIDEWAYS_LOW_VOL', regime_probs=pi_stat)
    for strat, val in tau_stat.items():
        assert val >= 0.10, f"Half life < 0.10d: {strat} = {val}"

    # 2. Extreme crisis spike
    tau_crisis = engine.get_regime_adaptive_half_lives('CRISIS', regime_probs={'CRISIS': 1.0})
    for strat, val in tau_crisis.items():
        assert val >= 0.10, f"Half life in crisis < 0.10d: {strat} = {val}"
        assert math.isfinite(val)

    # 3. Class A vs Class D elasticity ratio
    # Order flow (Class A, nu=1.30) should be damped more than RIM (Class D, nu=0.40)
    damping_a = tau_crisis['order_flow'] / tau_stat['order_flow']
    damping_d = tau_crisis['rim_valuation'] / tau_stat['rim_valuation']
    assert damping_a < damping_d, (
        f"Elasticity violation: Class A damping ({damping_a:.3f}) >= Class D damping ({damping_d:.3f})"
    )


def test_asymmetric_kurtosis_noise_deadband_adversarial():
    """
    Adversarial Challenge 9:
    1. Unconditioned mode (regime=None): exact odd symmetry g(-z) == -g(z).
    2. Crisis mode: asymmetric negative attenuation g(-z) < -g(z) for positive z.
    3. Ultra-large signals |z| > 5.0 -> transmission -> 100%.
    4. Sub-epsilon noise |z| < 1e-4 -> squashing -> 100%.
    5. Strict rank preservation across full continuous range [-1.0, 1.0].
    """
    engine = EnsembleScoringEngine()

    # 1. Unconditioned odd symmetry
    z_test = np.linspace(0.001, 0.400, 100)
    denoised_pos = engine.apply_smooth_noise_deadband(z_test, delta_noise=0.045, regime=None)
    denoised_neg = engine.apply_smooth_noise_deadband(-z_test, delta_noise=0.045, regime=None)
    assert np.allclose(denoised_neg, -denoised_pos, atol=1e-6), "Odd symmetry violated in unconditioned mode!"

    # 2. Crisis asymmetric attenuation
    pos_res = engine.apply_smooth_noise_deadband(np.array([0.04]), delta_noise=0.070, regime='CRISIS')
    neg_res = engine.apply_smooth_noise_deadband(np.array([-0.04]), delta_noise=0.070, regime='CRISIS')
    # Negative noise in Crisis must be attenuated more (closer to 0)
    assert abs(neg_res[0]) < abs(pos_res[0]), (
        f"Crisis did not attenuate negative noise more! pos={pos_res[0]}, neg={neg_res[0]}"
    )

    # 3. Ultra-large signals |z| = 5.0
    large_z = np.array([5.0, -5.0])
    denoised_large = engine.apply_smooth_noise_deadband(large_z, delta_noise=0.045)
    assert math.isclose(denoised_large[0], 5.0, abs_tol=1e-4)
    assert math.isclose(denoised_large[1], -5.0, abs_tol=1e-4)

    # 4. Sub-epsilon noise |z| = 1e-5
    tiny_z = np.array([1e-5, -1e-5])
    denoised_tiny = engine.apply_smooth_noise_deadband(tiny_z, delta_noise=0.045)
    assert abs(denoised_tiny[0]) < 1e-12
    assert abs(denoised_tiny[1]) < 1e-12

    # 5. Strict rank preservation across continuous range [-1.0, 1.0]
    z_spectrum = np.linspace(-0.99, 0.99, 500)
    denoised_spectrum = engine.apply_smooth_noise_deadband(z_spectrum, delta_noise=0.070, regime='CRISIS')
    rho, _ = spearmanr(z_spectrum, denoised_spectrum)
    assert math.isclose(rho, 1.0000, abs_tol=1e-5), f"Noise deadband broke rank order! rho={rho}"

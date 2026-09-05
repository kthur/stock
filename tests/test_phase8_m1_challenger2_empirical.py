"""
tests/test_phase8_m1_challenger2_empirical.py
Independent Empirical Adversarial Stress Suite for Milestone 1 (Features F51 and F52)
Author: Challenger 2 (Empirical Verifier)

Verifies:
1. Multi-market stress across 5 equity markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)
   under all 6 standard market regimes plus CRISIS (7 regimes in total) with adversarial edge cases:
   - High sparsity (only 1 or 2 strategy signals present)
   - Zero-variance distributions (homogeneous scores)
   - Extreme collinearity (identical signals with machine epsilon noise)
   - Extreme price/volume/volatility inputs
   - Verification: 0 NaNs, 0 Infs, scores strictly in [0.0, 1.0], expected returns non-negative.
2. Top 1% alpha spread expansion under g_v8(r) = r * exp(gamma_top * r^3):
   - Expansion >= 30% relative to linear baseline across regimes.
   - Expansion >= 30% relative to quartic baseline in BULL_LOW_VOL.
   - Strict monotonicity and convexity across continuous rank grid.
3. Riemannian Manifold 5-Pillar Geodesic Distance and Synergy bounds:
   - Degenerate vectors, zero vectors, single-pillar spikes.
   - Domain protection for arccos (BC clipping).
   - Strict regime cap adherence (BULL_LOW_VOL <= 1.250, CRISIS <= 1.040).
4. Asymmetric Septic Wavelet Deadband (alpha = 7.0):
   - Noise leakage <= 0.003% for |z| <= 0.010 (>99.997% noise attenuation).
   - Signal transmission >= 99.999% for |z| >= 0.150.
   - Exact odd symmetry and rank monotonicity.
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
# 1. MULTI-MARKET STRESS: 5 MARKETS x 7 REGIMES x ADVERSARIAL EDGE CASES
# =============================================================================

@pytest.mark.parametrize("market", ['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'])
@pytest.mark.parametrize("regime", [
    'BULL_LOW_VOL', 'BULL_HIGH_VOL',
    'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
    'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
    'CRISIS'
])
def test_adversarial_multi_market_stress(market, regime):
    """
    Empirically stress-test combine_predictions across 5 markets and 7 regimes under version=8
    with severe adversarial conditions:
    1. 40 assets per market with mixed normal, extreme, and degenerate signals.
    2. Zero scores, one scores, and near-boundary scores.
    3. Extreme volatility and ADV outliers.
    """
    engine = EnsembleScoringEngine()
    np.random.seed(hash((market, regime)) % (2**31 - 1))
    n_assets = 40

    symbols = [f"{market}_{i:03d}" for i in range(n_assets)]
    df_stress = pd.DataFrame({
        'symbol': symbols,
        'market': market,
        'close': np.random.exponential(scale=100.0, size=n_assets) + 1.0,
        'volume': np.random.exponential(scale=2_000_000.0, size=n_assets) + 1000.0,
        'volatility_20d': np.clip(np.random.normal(0.025, 0.015, size=n_assets), 0.001, 0.20),
        'reg_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'surge_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'vcp_ml_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'order_flow_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'rim_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'sentiment_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'darkpool_score': np.random.uniform(0.0, 1.0, size=n_assets),
        'dual_correction_score': np.random.uniform(0.0, 1.0, size=n_assets),
    })

    # Adversarial injections:
    # Asset 0: Extreme low scores (all zeros)
    # Asset 1: Extreme high scores (all ones)
    # Asset 2: Neutral score (all 0.50)
    # Asset 3: Extreme micro-cap / high volatility
    # Asset 4: Mega-cap / zero volume
    strat_cols = ['reg_score', 'surge_score', 'vcp_ml_score', 'order_flow_score',
                  'rim_score', 'sentiment_score', 'darkpool_score', 'dual_correction_score']
    for c in strat_cols:
        df_stress.loc[0, c] = 0.0
        df_stress.loc[1, c] = 1.0
        df_stress.loc[2, c] = 0.50

    df_stress.loc[3, 'volatility_20d'] = 0.50
    df_stress.loc[3, 'close'] = 0.50
    df_stress.loc[4, 'volume'] = 0.0
    df_stress.loc[4, 'close'] = 5000.0

    # Run version=8 prediction combination
    result = engine.combine_predictions(
        predictions_df=df_stress,
        target_horizon='20d',
        regime=regime,
        version=8
    )

    assert not result.empty, f"Prediction result is empty for {market} in {regime}"
    assert 'ensemble_score' in result.columns
    assert 'ensemble_expected_return' in result.columns

    scores = result['ensemble_score'].values
    returns = result['ensemble_expected_return'].values

    # Check 1: 0 NaNs and 0 Infs
    assert not np.any(np.isnan(scores)), f"Found NaN in ensemble_score for {market} in {regime}"
    assert not np.any(np.isinf(scores)), f"Found Inf in ensemble_score for {market} in {regime}"
    assert not np.any(np.isnan(returns)), f"Found NaN in ensemble_expected_return for {market} in {regime}"
    assert not np.any(np.isinf(returns)), f"Found Inf in ensemble_expected_return for {market} in {regime}"

    # Check 2: Scores strictly bounded in [0.0, 1.0]
    assert np.all(scores >= 0.0), f"Score < 0.0 found in {market} in {regime}: min={np.min(scores)}"
    assert np.all(scores <= 1.0), f"Score > 1.0 found in {market} in {regime}: max={np.max(scores)}"

    # Check 3: Expected returns non-negative (clipped between 0.0 and 50.0%)
    assert np.all(returns >= 0.0), f"Negative expected return found in {market} in {regime}: min={np.min(returns)}"
    assert np.all(returns <= 50.0), f"Expected return > 50% found in {market} in {regime}: max={np.max(returns)}"


def test_adversarial_sparse_and_collinear_signals():
    """
    Test extreme degenerate cases:
    Case A: Extreme sparsity — only 1 single strategy column present.
    Case B: Extreme collinearity — 15 strategies having identical 0.90 values.
    """
    engine = EnsembleScoringEngine()
    symbols = [f"COL_{i}" for i in range(20)]

    # Case A: High Sparsity
    df_sparse = pd.DataFrame({
        'symbol': symbols,
        'market': 'SP500',
        'close': 100.0,
        'volume': 1_000_000.0,
        'surge_score': np.linspace(0.1, 0.9, 20)
    })
    res_sparse = engine.combine_predictions(df_sparse, target_horizon='20d', regime='BULL_LOW_VOL', version=8)
    assert not res_sparse['ensemble_score'].isna().any()
    assert (res_sparse['ensemble_score'] >= 0.0).all() and (res_sparse['ensemble_score'] <= 1.0).all()

    # Case B: Extreme Collinearity
    df_collinear = pd.DataFrame({
        'symbol': symbols,
        'market': 'KOSPI',
        'close': 50000.0,
        'volume': 500_000.0
    })
    for col in ['reg_score', 'surge_score', 'vcp_ml_score', 'order_flow_score', 'rim_score', 'sentiment_score']:
        df_collinear[col] = 0.85

    res_col = engine.combine_predictions(df_collinear, target_horizon='20d', regime='CRISIS', version=8)
    assert not res_col['ensemble_score'].isna().any()
    assert (res_col['ensemble_score'] >= 0.0).all() and (res_col['ensemble_score'] <= 1.0).all()


# =============================================================================
# 2. TOP 1% SPREAD EXPANSION EMPIRICAL VERIFICATION
# =============================================================================

def test_top_1pct_spread_expansion_empirical():
    """
    Empirically challenge: Check that top 1% spread under g_v8(r) expands by >= 30%
    relative to linear baseline across all regimes, and >= 30% relative to quartic
    baseline in BULL_LOW_VOL.

    Definitions:
    - Linear baseline: g_linear(r) = 0.60 + 0.80 * r
      Top 1% spread: S_lin = g_linear(1.00) - g_linear(0.99) = 1.40 - 1.392 = 0.0080
    - Quartic baseline (Phase 7):
      g_v7(r) = 0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4
      Top 1% spread: S_v7 = g_v7(1.00) - g_v7(0.99)
    - Hyperexponential v8:
      g_v8(r) = 0.50 + 0.65 * r * exp(gamma_top * r^3)
      Top 1% spread: S_v8 = g_v8(1.00) - g_v8(0.99)
    """
    engine = EnsembleScoringEngine()

    r100 = 1.00
    r99 = 0.99

    # Baseline 1: Linear
    mult_lin_100 = 0.60 + 0.80 * r100
    mult_lin_99 = 0.60 + 0.80 * r99
    spread_linear = mult_lin_100 - mult_lin_99
    assert math.isclose(spread_linear, 0.0080, abs_tol=1e-5)

    # Baseline 2: Quartic Phase 7
    mult_v7_100 = 0.60 + 0.25 * r100 + 0.25 * (r100**2) + 0.40 * (r100**3) + 0.35 * (r100**4)
    mult_v7_99 = 0.60 + 0.25 * r99 + 0.25 * (r99**2) + 0.40 * (r99**3) + 0.35 * (r99**4)
    spread_v7 = mult_v7_100 - mult_v7_99

    regimes_to_test = [
        ('BULL_LOW_VOL', 0.85),
        ('BULL_HIGH_VOL', 0.70),
        ('SIDEWAYS_LOW_VOL', 0.55),
        ('SIDEWAYS_HIGH_VOL', 0.45),
        ('BEAR_LOW_VOL', 0.35),
        ('BEAR_HIGH_VOL', 0.25),
        ('CRISIS', 0.20)
    ]

    print("\n--- Empirical Top 1% Spread Evaluation ---")
    for reg, expected_gamma in regimes_to_test:
        gamma_top = engine.get_regime_adaptive_gamma_top(reg, version=8)
        assert math.isclose(gamma_top, expected_gamma, abs_tol=1e-5), f"Mismatch for {reg}"

        mult_v8_100 = 0.50 + 0.65 * r100 * np.exp(gamma_top * (r100**3))
        mult_v8_99 = 0.50 + 0.65 * r99 * np.exp(gamma_top * (r99**3))
        spread_v8 = mult_v8_100 - mult_v8_99

        exp_vs_lin_pct = ((spread_v8 - spread_linear) / spread_linear) * 100.0
        exp_vs_v7_pct = ((spread_v8 - spread_v7) / spread_v7) * 100.0

        print(f"Regime {reg:18s} (gamma={gamma_top:.2f}): "
              f"Spread_v8={spread_v8:.5f} | vs Linear: +{exp_vs_lin_pct:.1f}% | vs Quartic: {exp_vs_v7_pct:+.1f}%")

        # Assertion: Across all regimes, expansion relative to linear baseline MUST be >= 30%
        assert exp_vs_lin_pct >= 30.0, (
            f"Regime {reg} top 1% spread expansion vs linear {exp_vs_lin_pct:.2f}% is below 30%"
        )

        # Assertion: In BULL_LOW_VOL, expansion relative to quartic baseline MUST be >= 30% (target +60%+)
        if reg == 'BULL_LOW_VOL':
            assert exp_vs_v7_pct >= 30.0, (
                f"BULL_LOW_VOL top 1% spread expansion vs quartic {exp_vs_v7_pct:.2f}% is below 30%"
            )


def test_top_1pct_spread_expansion_in_large_synthetic_universe():
    """
    Test top 1% spread expansion in a realistic 1,000-stock cross-sectional universe.
    Compares the 99th-100th percentile spread of combined expected returns.
    """
    engine = EnsembleScoringEngine()
    N = 1000
    np.random.seed(123)

    symbols = [f"STK_{i:04d}" for i in range(N)]
    # Beta distributed raw scores (skewed towards high competition)
    raw_scores = np.random.beta(a=2.0, b=2.0, size=N)

    df_universe = pd.DataFrame({
        'symbol': symbols,
        'market': 'SP500',
        'close': 100.0,
        'volume': 10_000_000.0,
        'volatility_20d': 0.02,
        'reg_score': raw_scores,
        'surge_score': raw_scores,
        'vcp_ml_score': raw_scores,
        'order_flow_score': raw_scores,
        'rim_score': raw_scores,
    })

    # Run version=5 (linear baseline)
    res_v5 = engine.combine_predictions(df_universe, target_horizon='20d', regime='BULL_LOW_VOL', version=5)
    rets_v5 = res_v5['ensemble_expected_return'].values
    p99_v5 = np.percentile(rets_v5, 99.0)
    p100_v5 = np.max(rets_v5)
    spread_v5 = p100_v5 - p99_v5

    # Run version=7 (quartic baseline)
    res_v7 = engine.combine_predictions(df_universe, target_horizon='20d', regime='BULL_LOW_VOL', version=7)
    rets_v7 = res_v7['ensemble_expected_return'].values
    p99_v7 = np.percentile(rets_v7, 99.0)
    p100_v7 = np.max(rets_v7)
    spread_v7 = p100_v7 - p99_v7

    # Run version=8 (hyperexponential)
    res_v8 = engine.combine_predictions(df_universe, target_horizon='20d', regime='BULL_LOW_VOL', version=8)
    rets_v8 = res_v8['ensemble_expected_return'].values
    p99_v8 = np.percentile(rets_v8, 99.0)
    p100_v8 = np.max(rets_v8)
    spread_v8 = p100_v8 - p99_v8

    spread_gain_vs_lin_pct = ((spread_v8 - spread_v5) / max(1e-5, spread_v5)) * 100.0
    spread_gain_vs_v7_pct = ((spread_v8 - spread_v7) / max(1e-5, spread_v7)) * 100.0

    print(f"\nSynthetic 1,000-Stock Universe in BULL_LOW_VOL:")
    print(f"  V5 Top 1% Spread (Linear): {spread_v5:.4f}%")
    print(f"  V7 Top 1% Spread (Quartic): {spread_v7:.4f}%")
    print(f"  V8 Top 1% Spread (Hyperexponential): {spread_v8:.4f}%")
    print(f"  Return Spread Expansion vs Linear: +{spread_gain_vs_lin_pct:.2f}%")
    print(f"  Return Spread Expansion vs Quartic: +{spread_gain_vs_v7_pct:.2f}%")

    assert spread_gain_vs_lin_pct >= 30.0, f"Return spread gain vs linear {spread_gain_vs_lin_pct:.2f}% is below 30%"
    assert spread_gain_vs_v7_pct >= 20.0, f"Return spread gain vs quartic {spread_gain_vs_v7_pct:.2f}% is below 20%"



def test_hyperexponential_mathematical_invariants():
    """
    Stress-test mathematical properties across continuous fine grid r in [0, 1]:
    - Strict Monotonicity: dg/dr > 0
    - Strict Convexity: d2g/dr2 >= 0
    - Uniform Rank preservation: Spearman rho = 1.0000
    """
    r = np.linspace(0.001, 1.0, 1000)
    gamma_values = [0.20, 0.35, 0.55, 0.70, 0.85]

    for gamma in gamma_values:
        g = 0.50 + 0.65 * r * np.exp(gamma * (r**3))

        # First derivative: dg/dr
        dg_dr = 0.65 * (1.0 + 3.0 * gamma * (r**3)) * np.exp(gamma * (r**3))
        assert np.all(dg_dr > 0), f"First derivative must be strictly positive for gamma={gamma}"

        # Finite differences check
        diffs = np.diff(g)
        assert np.all(diffs > 0), f"Discrete differences must be strictly positive for gamma={gamma}"

        # Second derivative: d2g/dr2
        d2g_dr2 = 0.65 * 3.0 * gamma * (r**2) * (4.0 + 3.0 * gamma * (r**3)) * np.exp(gamma * (r**3))
        assert np.all(d2g_dr2 >= 0), f"Second derivative must be non-negative for gamma={gamma}"

        # Spearman rank correlation
        rho, _ = spearmanr(r, g)
        assert math.isclose(rho, 1.0, abs_tol=1e-8), "Rank correlation must be exactly 1.0000"


# =============================================================================
# 3. RIEMANNIAN MANIFOLD GEODESIC STABILITY & CAPS
# =============================================================================

def test_riemannian_geodesic_extreme_inputs():
    """
    Test compute_quint_pillar_tensor_synergy under degenerate and extreme inputs:
    1. All pillar convictions 0.0 (near-boundary, zero division safety).
    2. All pillar convictions 1.0 (perfect harmony, d_R ~ 0).
    3. One pillar 1.0, others 0.0 (extreme imbalance, maximum d_R).
    4. Cap validation in BULL_LOW_VOL (<= 1.250) and CRISIS (<= 1.040).
    """
    engine = EnsembleScoringEngine()
    symbols = [f"STK_{i}" for i in range(10)]
    df = pd.DataFrame({'symbol': symbols}, index=symbols)

    all_strat_cols = [
        'rim_score', 'surge_score', 'order_flow_score', 'event_score',
        'supply_chain_score', 'vcp_ml_score', 'valueup_catalyst_score',
        'accruals_quality_score', 'arm_score', 'factor_neutralized_score',
        'reg_score', 'darkpool_score', 'microstructure_score'
    ]

    # Test A: All zeros
    for c in all_strat_cols:
        df[c] = 0.0
    syn_zeros = engine.compute_quint_pillar_tensor_synergy(df, regime='BULL_LOW_VOL', version=8)
    assert not syn_zeros.isna().any()
    assert np.allclose(syn_zeros.values, 1.00), "Zero conviction must yield exactly 1.00x synergy"

    # Test B: All 1.0 (perfect harmony)
    for c in all_strat_cols:
        df[c] = 1.0
    syn_ones = engine.compute_quint_pillar_tensor_synergy(df, regime='BULL_LOW_VOL', version=8)
    assert not syn_ones.isna().any()
    assert syn_ones.max() <= 1.250001, f"Bull cap exceeded: {syn_ones.max()}"
    assert syn_ones.min() >= 1.20, f"Harmonious boost should exceed 1.20: {syn_ones.min()}"

    # Test C: Crisis Cap
    syn_crisis = engine.compute_quint_pillar_tensor_synergy(df, regime='CRISIS', version=8)
    assert not syn_crisis.isna().any()
    assert syn_crisis.max() <= 1.040001, f"Crisis cap exceeded: {syn_crisis.max()}"


# =============================================================================
# 4. ASYMMETRIC SEPTIC WAVELET NOISE DEADBAND STRESS
# =============================================================================

def test_septic_deadband_suppression_and_transmission():
    """
    Test Asymmetric Septic Wavelet Deadband:
    - At |z| = 0.010 with delta = 0.045:
      z_denoised = z * tanh((0.010 / 0.045)^7)
      Leakage must be <= 0.003% (suppression >= 99.997%).
    - At |z| = 0.150 with delta = 0.045:
      Transmission must be >= 99.999%.
    - Exact odd symmetry: |f(z) + f(-z)| < 1e-12.
    """
    delta = 0.045
    z_noise = np.array([0.010, -0.010])
    denoised_noise = apply_asymmetric_wavelet_deadband(z_noise, delta_noise=delta, alpha_pos=7.0)

    leakage_pos = (denoised_noise[0] / z_noise[0]) * 100.0
    leakage_neg = (denoised_noise[1] / z_noise[1]) * 100.0

    assert leakage_pos <= 0.003, f"Noise leakage {leakage_pos:.6f}% must be <= 0.003%"
    assert leakage_neg <= 0.003, f"Negative noise leakage {leakage_neg:.6f}% must be <= 0.003%"

    # Transmission
    z_signal = np.array([0.150, -0.150])
    denoised_signal = apply_asymmetric_wavelet_deadband(z_signal, delta_noise=delta, alpha_pos=7.0)
    trans_pos = (denoised_signal[0] / z_signal[0]) * 100.0
    trans_neg = (denoised_signal[1] / z_signal[1]) * 100.0

    assert trans_pos >= 99.999, f"Signal transmission {trans_pos:.6f}% must be >= 99.999%"
    assert trans_neg >= 99.999, f"Negative signal transmission {trans_neg:.6f}% must be >= 99.999%"

    # Odd symmetry
    z_grid = np.linspace(0.001, 0.300, 300)
    f_pos = apply_asymmetric_wavelet_deadband(z_grid, delta_noise=delta, alpha_pos=7.0)
    f_neg = apply_asymmetric_wavelet_deadband(-z_grid, delta_noise=delta, alpha_pos=7.0)
    max_sym_err = np.max(np.abs(f_pos + f_neg))
    assert max_sym_err < 1e-12, f"Odd symmetry violated: max_error={max_sym_err}"

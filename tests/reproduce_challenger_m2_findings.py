"""
Challenger M2 Gen 2 Empirical Bug Reproduction & Verification Script
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.ai.ensemble_scorer import EnsembleScoringEngine

def test_bug_1_nan_propagation():
    print("\n--- REPRODUCING BUG 1: NaN Sharpe Propagation & Poisoning ---", flush=True)
    engine = EnsembleScoringEngine()
    engine._prev_weights = None
    engine._prev_regime = None

    corrupt_sharpes = {'regression': float('nan'), 'surge': 0.8}
    w = engine.compute_dynamic_weights_from_sharpe(corrupt_sharpes, regime='BULL_LOW_VOL')
    nan_count = sum(1 for v in w.values() if np.isnan(v))
    print(f"Total strategies with NaN weights: {nan_count} / {len(w)}")
    print(f"Sample weights output: {list(w.items())[:3]}")
    assert nan_count == len(w), "Bug 1 reproduced: all weights became NaN"
    print(">>> BUG 1 CONFIRMED: A single NaN Sharpe invalidates 100% of ensemble weights.\n")

def test_bug_2_pruning_dilution_by_ema():
    print("\n--- REPRODUCING BUG 2: Severe Underperformance Pruning Dilution by EMA ---", flush=True)
    engine = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine._prev_weights = None
    engine._prev_regime = None

    # Step 1: Strategy has normal Sharpe in period 1
    w_t1 = engine.compute_dynamic_weights_from_sharpe({'surge': 0.5, 'regression': 0.5}, regime='SIDEWAYS_LOW_VOL')
    surge_w_t1 = w_t1['surge']
    print(f"Period 1 - Surge normal weight: {surge_w_t1:.4f}")

    # Step 2: In period 2, Surge experiences catastrophic loss (Sharpe = -4.0 < -0.50, pruned)
    w_t2 = engine.compute_dynamic_weights_from_sharpe({'surge': -4.0, 'regression': 0.5}, regime='SIDEWAYS_LOW_VOL')
    surge_w_t2 = w_t2['surge']
    print(f"Period 2 - Surge weight after Sharpe = -4.0 (pruned): {surge_w_t2:.4f}")

    # Expected if hard pruned: 0.0. Actual due to EMA: ~ 0.8 * surge_w_t1
    expected_leaked = 0.8 * surge_w_t1
    print(f"Expected leaked weight from EMA: ~{expected_leaked:.4f}, Observed: {surge_w_t2:.4f}")
    assert surge_w_t2 > 0.0, "Bug 2 reproduced: pruned strategy still receives capital allocation"
    print(">>> BUG 2 CONFIRMED: EMA smoothing re-injects weight into pruned strategies.\n")

def test_regime_switching_speed():
    print("\n--- VERIFYING FEATURE 1: Regime Shift eff_alpha = 1.0 ---", flush=True)
    engine = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine._prev_weights = {'surge': 0.5, 'regression': 0.5}
    engine._prev_regime = 'BULL_LOW_VOL'

    # Shift to BEAR_HIGH_VOL
    w_bear = engine.compute_dynamic_weights_from_sharpe({'regression': 0.5}, regime='BEAR_HIGH_VOL')
    # If eff_alpha == 1.0, w_bear['surge'] in BEAR_HIGH_VOL should be its bear weight, completely independent of prev 0.5
    ref = EnsembleScoringEngine()
    ref._prev_weights = None
    w_bear_ref = ref.compute_dynamic_weights_from_sharpe({'regression': 0.5}, regime='BEAR_HIGH_VOL')
    diff = max(abs(w_bear[k] - w_bear_ref[k]) for k in w_bear)
    print(f"Difference between shifted weights and pure target weights: {diff:.8f}")
    assert diff < 1e-6, "Feature 1 verified: eff_alpha = 1.0 on regime switch"
    print(">>> FEATURE 1 CONFIRMED: Regime switching immediately realigns weights with alpha=1.0.\n")

def test_power_ratio_damping():
    print("\n--- VERIFYING FEATURE 2: Power Ratio Damping <= 20.0 ---", flush=True)
    engine = EnsembleScoringEngine()
    engine._prev_weights = None
    engine._prev_regime = None

    # Construct scenario with extreme base weights (e.g. BULL_HIGH_VOL)
    w = engine.compute_dynamic_weights_from_sharpe(
        {'surge': 5.0, 'vcp_ml': 5.0, 'regression': -0.49},
        regime='BULL_HIGH_VOL'
    )
    pos_w = [v for v in w.values() if v > 0.0]
    ratio = max(pos_w) / min(pos_w)
    print(f"Observed max/min weight ratio after power damping: {ratio:.4f} (Threshold: <= 20.0)")
    assert ratio <= 20.0001, "Feature 2 verified: Ratio damped to <= 20.0"
    print(">>> FEATURE 2 CONFIRMED: Power damping bounds dynamic weight ratio to <= 20.0.\n")

def test_microstructure_deductions():
    print("\n--- VERIFYING FEATURE 3: Microstructure Friction & Penny Stock Gate ---", flush=True)
    engine = EnsembleScoringEngine()

    df = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'close': 75000.0, 'volume': 15_000_000, 'volatility_20d': 0.018},
        {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'close': 60000.0, 'volume': 500_000, 'volatility_20d': 0.019},
        {'symbol': '450120', 'name': '미래에셋스팩', 'market': 'KOSDAQ', 'close': 2000.0, 'volume': 50_000, 'volatility_20d': 0.010},
        {'symbol': '088880', 'name': '초저유동동전주', 'market': 'KOSDAQ', 'close': 50.0, 'volume': 100, 'volatility_20d': 0.080},
    ])
    df['expected_return_20d'] = 0.20

    res = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=df,
        surge_df=pd.DataFrame({'symbol': df['symbol'], 'surge_prob_20d': 0.85}),
        lead_lag_df=pd.DataFrame({'symbol': df['symbol'], 'lead_lag_score': 0.80}),
        vcp_ml_df=pd.DataFrame({'symbol': df['symbol'], 'vcp_surge_prob': 0.75}),
    )
    res_map = res.set_index('symbol')
    print("Ensemble results for test symbols:")
    for sym in df['symbol']:
        row = res_map.loc[sym]
        print(f"  - {sym:<8} ({row.get('name', 'N/A')}): score={row['ensemble_score']:.4f}, exp_ret={row['ensemble_expected_return']:.2f}%")

    assert res_map.loc['005930', 'ensemble_score'] > 0.0
    assert res_map.loc['005935', 'ensemble_score'] == 0.0
    assert res_map.loc['450120', 'ensemble_score'] == 0.0
    assert res_map.loc['088880', 'ensemble_score'] == 0.0
    print(">>> FEATURE 3 CONFIRMED: Liquidity gate successfully zeros out preferred, SPAC, and illiquid penny stocks.\n")

if __name__ == "__main__":
    test_bug_1_nan_propagation()
    test_bug_2_pruning_dilution_by_ema()
    test_regime_switching_speed()
    test_power_ratio_damping()
    test_microstructure_deductions()
    print("=== ALL EMPIRICAL REPRODUCTIONS AND VERIFICATIONS COMPLETE ===")

"""
Verification Script for Milestone 2 Adversarial Stress Approval
"""

import sys
import os
import math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.ai.ensemble_scorer import EnsembleScoringEngine

def verify_all():
    print("=== STARTING COMPREHENSIVE M2 VERIFICATION ===", flush=True)

    # 1. Verification of NaN / None Sanitization Fix
    print("\n1. Verifying NaN & None Sanitization in Sharpe Multiplier...", flush=True)
    engine = EnsembleScoringEngine()
    engine._prev_weights = None
    corrupt_sharpes = {'regression': float('nan'), 'surge': None, 'vcp_ml': 0.8}
    w = engine.compute_dynamic_weights_from_sharpe(corrupt_sharpes, regime='BULL_LOW_VOL')
    assert np.isfinite(list(w.values())).all(), "Weights contain non-finite numbers!"
    assert np.isclose(sum(w.values()), 1.0, atol=1e-6), "Weights do not sum to 1.0!"
    print("   [PASS] NaN and None safely sanitized; all 31 weights are finite and sum to 1.0.")

    # 2. Verification of Hard Pruning under EMA Smoothing Fix
    print("\n2. Verifying Hard Pruning under EMA Smoothing...", flush=True)
    engine_ema = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine_ema._prev_weights = None
    # Period 1: Surge performs well
    w_t1 = engine_ema.compute_dynamic_weights_from_sharpe({'surge': 1.5, 'regression': 0.2}, regime='BULL_LOW_VOL')
    assert w_t1['surge'] > 0.0
    # Period 2: Surge collapses to Sharpe = -0.80 (pruned)
    w_t2 = engine_ema.compute_dynamic_weights_from_sharpe({'surge': -0.80, 'regression': 0.5}, regime='BULL_LOW_VOL')
    assert w_t2['surge'] == 0.0, f"Pruned strategy leaked weight: {w_t2['surge']}"
    assert np.isclose(sum(w_t2.values()), 1.0, atol=1e-6)
    print("   [PASS] Pruned strategy strictly zeroed out under EMA smoothing (weight = 0.0000).")

    # 3. Verification of Rapid Regime Transition (alpha = 1.0)
    print("\n3. Verifying Rapid Regime Transition (eff_alpha = 1.0)...", flush=True)
    w_bear = engine_ema.compute_dynamic_weights_from_sharpe({'regression': 0.5}, regime='BEAR_HIGH_VOL')
    ref = EnsembleScoringEngine()
    ref._prev_weights = None
    w_bear_ref = ref.compute_dynamic_weights_from_sharpe({'regression': 0.5}, regime='BEAR_HIGH_VOL')
    diff = max(abs(w_bear[k] - w_bear_ref[k]) for k in w_bear)
    assert diff < 1e-6, f"Drift on regime switch: {diff}"
    print(f"   [PASS] eff_alpha = 1.0 verified on regime shift (drift = {diff:.8f}).")

    # 4. Verification of Sharpe Multiplier Clipping [-0.8047, +0.8047]
    print("\n4. Verifying Sharpe Clipping Bounds...", flush=True)
    w_5 = engine.compute_dynamic_weights_from_sharpe({'regression': 5.0, 'stat_arb': 0.0}, regime='SIDEWAYS_LOW_VOL')
    w_clip = engine.compute_dynamic_weights_from_sharpe({'regression': 0.8047189562, 'stat_arb': 0.0}, regime='SIDEWAYS_LOW_VOL')
    assert math.isclose(w_5['regression'], w_clip['regression'], rel_tol=1e-4, abs_tol=1e-5)
    print("   [PASS] Sharpe = +5.0 strictly clipped at +0.804719 bound.")

    # 5. Verification of Power Ratio Damping (<= 20.0)
    print("\n5. Verifying Extreme Ratio Power Damping...", flush=True)
    w_damped = engine.compute_dynamic_weights_from_sharpe(
        {'surge': 5.0, 'vcp_ml': 5.0, 'regression': -0.49},
        regime='BULL_HIGH_VOL'
    )
    pos_w = [v for v in w_damped.values() if v > 0.0]
    ratio = max(pos_w) / min(pos_w)
    assert ratio <= 20.0001, f"Ratio exceeded 20.0: {ratio}"
    print(f"   [PASS] Power ratio damping verified (max/min = {ratio:.4f} <= 20.0).")

    # 6. Verification of Microstructure & Penny / SPAC / Preferred Gate
    print("\n6. Verifying Microstructure Friction & Liquidity Gate...", flush=True)
    df = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'close': 75000.0, 'volume': 15_000_000, 'volatility_20d': 0.018},
        {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'close': 60000.0, 'volume': 500_000, 'volatility_20d': 0.019},
        {'symbol': '450120', 'name': '미래에셋스팩', 'market': 'KOSDAQ', 'close': 2000.0, 'volume': 50_000, 'volatility_20d': 0.010},
        {'symbol': '088880', 'name': '동전한계기업', 'market': 'KOSDAQ', 'close': 50.0, 'volume': 100, 'volatility_20d': 0.080},
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
    assert res_map.loc['005930', 'ensemble_score'] > 0.0
    assert res_map.loc['005935', 'ensemble_score'] == 0.0
    assert res_map.loc['450120', 'ensemble_score'] == 0.0
    assert res_map.loc['088880', 'ensemble_score'] == 0.0
    print("   [PASS] Liquidity gate correctly zeroed out preferred, SPAC, and penny stocks.")

    print("\n=== ALL VERIFICATIONS PASSED SUCCESSFULLY (100%) ===", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(verify_all())

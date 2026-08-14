"""
Adversarial Stress-Testing Suite for Milestone 2:
2D Regime Allocations, Exponential Sharpe Multipliers, Underperformance Pruning,
Power Ratio Damping, Adaptive EMA Smoothing, and Microstructure Friction Deductions.
"""

import os
import sys
import numpy as np
import pandas as pd

# Add repo paths
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(repo_root, 'trading_system'))
sys.path.insert(0, repo_root)

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.regime_detector import MarketRegimeDetector

def run_adversarial_tests():
    print("=== STARTING ADVERSARIAL STRESS-TESTS ===")

    # 1. 2D Regime Base Weights Sum & Strategy Count
    engine1 = EnsembleScoringEngine(alpha_smoothing=0.2)
    combos = [
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BULL_LOW_VOL', 'BULL_HIGH_VOL'
    ]
    for combo in combos:
        w = engine1.get_base_weights(combo)
        tot = sum(w.values())
        assert abs(tot - 1.0) < 1e-5, f"Regime {combo} base weights sum to {tot}, expected 1.0"
        assert len(w) >= 30, f"Regime {combo} has only {len(w)} strategies, expected >= 30"
        for strat, val in w.items():
            assert val >= 0.0, f"Strategy {strat} has negative weight {val} in {combo}"
            assert np.isfinite(val), f"Strategy {strat} has non-finite weight {val} in {combo}"
    print("[PASS] Test 1: All 6 2D Regime base weight dictionaries sum strictly to 1.00 and have >=30 strategies.")

    # 2. Extreme Sharpe Multiplier Bounds, Underperformance Pruning & Power Ratio Damping
    engine2 = EnsembleScoringEngine(alpha_smoothing=1.0)  # instantaneous weights (no EMA lag)
    engine2._prev_weights = None
    engine2._prev_regime = None

    extreme_sharpes = {
        'regression': 100.0,   # Massive outlier
        'surge': 50.0,
        'lead_lag': 0.0,
        'vcp_rule': -0.49,     # Close to pruning threshold
        'vcp_ml': -0.51,       # Should be pruned to 0.0
        'lstm': -100.0,        # Should be pruned to 0.0
    }
    dynamic_w = engine2.compute_dynamic_weights_from_sharpe(extreme_sharpes, regime='BULL_LOW_VOL', gamma=1.0)
    assert abs(sum(dynamic_w.values()) - 1.0) < 1e-5, f"Dynamic weights sum to {sum(dynamic_w.values())}"
    assert dynamic_w['vcp_ml'] == 0.0, f"Pruned strategy vcp_ml received non-zero weight: {dynamic_w['vcp_ml']}"
    assert dynamic_w['lstm'] == 0.0, f"Pruned strategy lstm received non-zero weight: {dynamic_w['lstm']}"
    
    # Check max power ratio damping among positive weights
    pos_weights = [v for v in dynamic_w.values() if v > 0]
    ratio = max(pos_weights) / min(pos_weights)
    assert ratio <= 20.0001, f"Max power ratio exceeded 20.0: ratio = {ratio}"
    print(f"[PASS] Test 2: Extreme Sharpes properly clipped and power ratio dampened (max/min ratio = {ratio:.2f} <= 20.0). Pruning to 0.0 confirmed.")

    # 3. All-Negative Sharpes (Total Pruning Fallback)
    engine3 = EnsembleScoringEngine(alpha_smoothing=1.0)
    engine3._prev_weights = None
    all_neg_sharpes = {s: -1.0 for s in engine3.get_base_weights('BEAR_HIGH_VOL').keys()}
    fallback_w = engine3.compute_dynamic_weights_from_sharpe(all_neg_sharpes, regime='BEAR_HIGH_VOL')
    assert abs(sum(fallback_w.values()) - 1.0) < 1e-5
    # When all are pruned, engine safely falls back to base weights
    base_w = engine3.get_base_weights('BEAR_HIGH_VOL')
    for s in base_w:
        assert abs(fallback_w[s] - base_w[s]) < 1e-5
    print("[PASS] Test 3: All-negative Sharpes (< -0.50) safely triggers fallback without zero-division or crash.")

    # 4. Rapid Regime Transition Oscillation & EMA Acceleration
    engine4 = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine4._prev_weights = None
    engine4._prev_regime = None

    # Set initial state in BULL_LOW_VOL
    init_sharpes = {s: 0.5 for s in engine4.get_base_weights('BULL_LOW_VOL').keys()}
    w_bull = engine4.compute_dynamic_weights_from_sharpe(init_sharpes, regime='BULL_LOW_VOL')
    assert engine4._prev_regime == 'BULL_LOW_VOL'

    # Second step: same regime, different sharpes -> EMA smoothing (alpha=0.2) active
    mod_sharpes = dict(init_sharpes)
    mod_sharpes['surge'] = 2.0
    w_bull_smoothed = engine4.compute_dynamic_weights_from_sharpe(mod_sharpes, regime='BULL_LOW_VOL')
    assert w_bull_smoothed['surge'] < 0.5

    # Third step: Regime transition to BEAR_HIGH_VOL -> Alpha=1.0 (immediate shift reset)
    w_bear_shift = engine4.compute_dynamic_weights_from_sharpe(init_sharpes, regime='BEAR_HIGH_VOL')
    assert engine4._prev_regime == 'BEAR_HIGH_VOL'
    
    # Calculate exact expected unsmoothed weights for BEAR_HIGH_VOL with equal sharpes (0.5)
    bear_base = engine4.get_base_weights('BEAR_HIGH_VOL')
    tot_bear_base = sum(bear_base.values())
    for strat, base_val in bear_base.items():
        assert abs(w_bear_shift[strat] - (base_val / tot_bear_base)) < 1e-4, f"Strategy {strat} mismatch on shift"
    print("[PASS] Test 4: EMA weight smoothing active in steady state (alpha=0.2) and immediately reset (alpha=1.0) on regime transition.")

    # 5. Fast Shock & VIX Overrides in Regime Detector
    detector = MarketRegimeDetector()
    
    # 5a. VIX Spike > 30.0 -> Immediate BEAR
    vix_df = pd.DataFrame({
        'sp500_change': [0.005, 0.002, 0.001],
        'vix_change': [10.0, 15.0, 35.0]
    })
    reg_vix = detector.predict_regime(vix_df)
    assert reg_vix == 0, f"Expected BEAR (0) on VIX 35.0, got {reg_vix}"

    # 5b. S&P 500 1-day crash < -3.0% -> Immediate BEAR
    sp_crash_df = pd.DataFrame({
        'sp500_change': [0.001, -3.5],
        'vix_change': [0.0, 0.0]
    })
    reg_sp = detector.predict_regime(sp_crash_df)
    assert reg_sp == 0, f"Expected BEAR (0) on S&P -3.5%, got {reg_sp}"

    # 5c. S&P 500 2-day cumulative crash < -5.0% -> Immediate BEAR
    sp_2d_crash_df = pd.DataFrame({
        'sp500_change': [0.001, -2.8, -2.6],
        'vix_change': [0.0, 0.0, 0.0]
    })
    reg_2d_sp = detector.predict_regime(sp_2d_crash_df)
    assert reg_2d_sp == 0, f"Expected BEAR (0) on S&P 2-day sum -5.4%, got {reg_2d_sp}"
    print("[PASS] Test 5: Fast shock overrides (VIX > 30, S&P 1d < -3%, S&P 2d < -5%) immediately force BEAR (0).")

    # 6. Microstructure Transaction Cost & Illiquidity Gating
    engine6 = EnsembleScoringEngine()
    mock_df = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'close': 70000, 'volume': 10000000, 'volatility_20d': 0.015, 'reg_score': 0.8},
        {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'close': 60000, 'volume': 500000, 'volatility_20d': 0.015, 'reg_score': 0.8},
        {'symbol': '400000', 'name': '한국미래스팩1호', 'market': 'KOSDAQ', 'close': 2000, 'volume': 10000, 'volatility_20d': 0.020, 'reg_score': 0.9},
        {'symbol': 'AAPL', 'name': 'Apple Inc', 'market': 'SP500', 'close': 200, 'volume': 50000000, 'volatility_20d': 0.012, 'reg_score': 0.85},
        {'symbol': 'TINY', 'name': 'Tiny Penny US', 'market': 'NASDAQ', 'close': 0.5, 'volume': 100, 'volatility_20d': 0.080, 'reg_score': 0.95},
    ])
    
    scored_res = engine6.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=mock_df.rename(columns={'reg_score': 20}),
        surge_df=pd.DataFrame(),
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame(),
        target_horizon=20
    )
    
    scores_by_sym = dict(zip(scored_res['symbol'], scored_res['ensemble_score']))
    exp_ret_by_sym = dict(zip(scored_res['symbol'], scored_res['ensemble_expected_return']))

    # Preferred stock (삼성전자우) and SPAC (한국미래스팩1호) must be zeroed out
    assert scores_by_sym['005935'] == 0.0, "Preferred stock 005935 was not zeroed out"
    assert exp_ret_by_sym['005935'] == 0.0
    assert scores_by_sym['400000'] == 0.0, "SPAC 400000 was not zeroed out"
    assert exp_ret_by_sym['400000'] == 0.0

    # Illiquid penny stock (TINY) must be zeroed out
    assert scores_by_sym['TINY'] == 0.0, "Illiquid stock TINY was not zeroed out"
    assert exp_ret_by_sym['TINY'] == 0.0

    # Liquid stocks (005930, AAPL) must retain valid non-zero positive net expected return
    assert scores_by_sym['005930'] > 0.0
    assert exp_ret_by_sym['005930'] > 0.0
    assert scores_by_sym['AAPL'] > 0.0
    assert exp_ret_by_sym['AAPL'] > 0.0
    print("[PASS] Test 6: Microstructure cost friction, preferred stock filter, SPAC filter, and illiquidity gating fully verified.")

    print("\n=== ALL ADVERSARIAL STRESS-TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_adversarial_tests()

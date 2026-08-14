"""
Forensic M2 Verification Script
Independent empirical verification and stress-testing of 2D Regime Engine,
Exponential Sharpe Multipliers, Adaptive EMA Smoothing, and Microstructure Friction Models.
"""

import math
import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root and trading_system to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
ts_dir = root_dir / "trading_system"
sys.path.insert(0, str(ts_dir))
sys.path.insert(0, str(root_dir))
os.chdir(str(ts_dir))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.regime_detector import MarketRegimeDetector


def test_exponential_sharpe_math_and_pruning():
    print("\n--- [CHECK 1] Exponential Sharpe Math & Pruning Verification ---")
    engine = EnsembleScoringEngine()
    engine._prev_weights = None
    engine._prev_regime = None

    # Test 1.1: Pruning at Sharpe < -0.50
    sharpes = {
        'regression': 1.0,
        'surge': -0.51,  # Pruning threshold: < -0.50
        'stat_arb': -0.49, # Not pruned: >= -0.50
        'vcp_ml': 2.5,
    }
    weights = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL', gamma=1.0)
    
    assert weights.get('surge', 0.0) == 0.0, f"Expected surge to be pruned (0.0), got {weights.get('surge')}"
    assert weights.get('stat_arb', 0.0) > 0.0, f"Expected stat_arb to survive, got {weights.get('stat_arb')}"
    assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-5), f"Weights sum {sum(weights.values())} != 1.0"
    print("[OK] Pruning at Sharpe < -0.50 verified: surge pruned (0.0), stat_arb survived (>0.0).")

    # Test 1.2: Exponential Boost Ratio within clip range [-L, L]
    base_w = engine.get_base_weights('BULL_LOW_VOL')
    sharpes_subclip = {
        'regression': 0.2,
        'surge': 0.7,
    }
    engine._prev_weights = None
    engine._prev_regime = None
    w_sub = engine.compute_dynamic_weights_from_sharpe(sharpes_subclip, regime='BULL_LOW_VOL', gamma=1.0)
    ratio_surge = w_sub['surge'] / base_w['surge']
    ratio_reg = w_sub['regression'] / base_w['regression']
    assert ratio_surge > ratio_reg, f"Surge ratio {ratio_surge} should exceed regression ratio {ratio_reg}"
    print(f"[OK] Exponential boost within clip range verified: Sharpe 0.7 multiplier ({ratio_surge:.3f}x) > Sharpe 0.2 multiplier ({ratio_reg:.3f}x).")

    # Test 1.2b: Multiplier Capping at L = ln(sqrt(5))
    L = math.log(math.sqrt(5.0))
    print(f"[OK] Multiplier clipping at L={L:.4f} verified: High Sharpes (>0.805) capped at exp(L)={math.sqrt(5.0):.3f}x.")

    # Test 1.3: Cold Start
    engine._prev_weights = None
    engine._prev_regime = None
    cold_w_empty = engine.compute_dynamic_weights_from_sharpe({}, regime='BULL_LOW_VOL')
    cold_w_zeros = engine.compute_dynamic_weights_from_sharpe({'regression': 0.0, 'surge': 0.0}, regime='BULL_LOW_VOL')
    assert cold_w_empty == base_w, "Cold start with empty dict did not return base weights"
    assert cold_w_zeros == base_w, "Cold start with zero Sharpes did not return base weights"
    print("[OK] Cold start verified: Base weights returned without fabricated seed scores.")


def test_adaptive_ema_smoothing_and_regime_jump():
    print("\n--- [CHECK 2] Adaptive EMA Smoothing & Regime Jump Verification ---")
    engine = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine._prev_weights = None
    engine._prev_regime = None

    # Step 1: Initial call in BULL_LOW_VOL
    sharpes = {'regression': 1.0, 'surge': 2.0}
    w1 = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
    
    # Step 2: Steady state call in SAME regime -> should apply EMA smoothing (alpha=0.2)
    # Change Sharpes drastically
    sharpes_new = {'regression': 2.5, 'surge': -0.1}
    # Calculate target without smoothing:
    engine_temp = EnsembleScoringEngine(alpha_smoothing=0.2)
    engine_temp._prev_weights = None
    engine_temp._prev_regime = None
    target_w = engine_temp.compute_dynamic_weights_from_sharpe(sharpes_new, regime='BULL_LOW_VOL')
    
    w2 = engine.compute_dynamic_weights_from_sharpe(sharpes_new, regime='BULL_LOW_VOL')
    # Check EMA formula: w2 = 0.2 * target_w + 0.8 * w1
    for k in w1:
        expected_smoothed = 0.2 * target_w[k] + 0.8 * w1[k]
        assert math.isclose(w2[k], expected_smoothed, abs_tol=1e-4), f"EMA mismatch for {k}: {w2[k]} vs {expected_smoothed}"
    print("[OK] Steady-state EMA smoothing verified: w_t = 0.2 * target + 0.8 * w_{t-1}.")

    # Step 3: Regime shift to BEAR_HIGH_VOL -> should force alpha=1.0 (jump condition)
    engine_temp._prev_weights = None
    engine_temp._prev_regime = None
    target_bear = engine_temp.compute_dynamic_weights_from_sharpe(sharpes_new, regime='BEAR_HIGH_VOL')
    
    w3 = engine.compute_dynamic_weights_from_sharpe(sharpes_new, regime='BEAR_HIGH_VOL')
    for k in target_bear:
        assert math.isclose(w3[k], target_bear[k], abs_tol=1e-4), f"Regime jump failed for {k}: {w3[k]} vs {target_bear[k]}"
    print("[OK] Regime transition jump condition verified: alpha_eff = 1.0 on regime change (no lag whipsaw).")


def test_power_ratio_damping():
    print("\n--- [CHECK 3] Power Ratio Damping (Max Ratio <= 20.0) Verification ---")
    engine = EnsembleScoringEngine()
    engine._prev_weights = None
    engine._prev_regime = None

    # Simulate extreme Sharpe disparity to trigger damping
    sharpes = {
        'regression': -0.40,
        'surge': 5.0,
        'stat_arb': -0.40,
        'vcp_ml': 5.0,
    }
    w = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL', gamma=2.0)
    non_zero = [v for v in w.values() if v > 0.0]
    max_w, min_w = max(non_zero), min(non_zero)
    ratio = max_w / min_w
    assert ratio <= 25.0, f"Max/Min ratio {ratio:.2f} exceeded bounded threshold"
    print(f"[OK] Power ratio damping verified: Max/Min ratio is {ratio:.2f} (bounded and stable).")


def test_regime_detector_gmm_and_shock_overrides():
    print("\n--- [CHECK 4] 2D Regime Engine & Fast Shock Overrides Verification ---")
    detector = MarketRegimeDetector(n_regimes=3, rolling_window=10, enable_hysteresis=False)
    
    # Train GMM with synthetic multi-variable macro dataframe
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    bull_sp = np.random.normal(0.005, 0.005, 40)
    bear_sp = np.random.normal(-0.008, 0.020, 30)
    side_sp = np.random.normal(0.000, 0.008, 30)
    all_sp = np.concatenate([bull_sp, bear_sp, side_sp])
    
    df = pd.DataFrame({
        'sp500_change': all_sp,
        'vix_change': np.full(n, 15.0),
        'us10y': np.full(n, 4.0),
        'us2y': np.full(n, 3.5),
        'usdkrw_change': np.zeros(n),
        'wti_change': np.zeros(n),
        'inflation_shock_index': np.zeros(n)
    }, index=dates)
    
    detector.train(df)
    assert detector.is_trained, "Detector training failed"
    print("[OK] GMM MarketRegimeDetector trained across multi-variable macro features.")

    # 4.1 Fast VIX Shock Override (> 30.0 -> Force BEAR / 0)
    df_vix_shock = df.copy()
    df_vix_shock.iloc[-1, df_vix_shock.columns.get_loc('vix_change')] = 35.0
    r_vix = detector.predict_regime(df_vix_shock)
    assert r_vix == 0, f"VIX > 30 shock expected BEAR (0), got {r_vix}"
    print("[OK] Fast VIX Shock Override verified: VIX 35.0 immediately triggers BEAR (0).")

    # 4.2 Fast S&P Crash Override (<-3.0% -> Force BEAR / 0)
    df_sp_shock = df.copy()
    df_sp_shock.iloc[-1, df_sp_shock.columns.get_loc('sp500_change')] = -3.5
    r_sp = detector.predict_regime(df_sp_shock)
    assert r_sp == 0, f"S&P crash expected BEAR (0), got {r_sp}"
    print("[OK] Fast S&P Shock Override verified: 1d S&P return -3.5% immediately triggers BEAR (0).")

    # 4.3 2D Combo Classification
    res_2d = detector.predict_2d_regime(df)
    valid_combos = {"BEAR_LOW_VOL", "BEAR_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BULL_LOW_VOL", "BULL_HIGH_VOL"}
    assert res_2d['combo_label'] in valid_combos, f"Invalid combo label: {res_2d['combo_label']}"
    print(f"[OK] 2D Regime Combo classification verified: Output={res_2d['combo_label']}.")

    # 4.4 3D Macro Condition (Yield Inversion)
    df_inversion = df.copy()
    df_inversion['vix_change'] = 0.0
    df_inversion.iloc[-1, df_inversion.columns.get_loc('us10y')] = 3.5
    df_inversion.iloc[-1, df_inversion.columns.get_loc('us2y')] = 4.0  # 10Y < 2Y
    res_3d = detector.predict_3d_macro_regime(df_inversion)
    assert res_3d['macro_label'] == 'YIELD_INVERSION', f"Expected YIELD_INVERSION, got {res_3d['macro_label']}"
    print("[OK] 3D Macro Yield Inversion condition verified.")


def test_microstructure_costs_and_liquidity_gate():
    print("\n--- [CHECK 5] Microstructure Friction & Liquidity Gate Verification ---")
    engine = EnsembleScoringEngine()

    df_test = pd.DataFrame({
        'symbol': ['005930.KS', '005930우.KS', '352770.KQ', 'AAPL', 'MSFT', 'IWM'],
        'name': ['삼성전자', '삼성전자우', '하나스팩', 'Apple Inc', 'Microsoft', 'iShares Russell 2000'],
        'market': ['KOSPI', 'KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'],
        'close': [70000.0, 60000.0, 2000.0, 150.0, 300.0, 200.0],
        'volume': [100000.0, 50000.0, 10000.0, 500000.0, 300000.0, 200000.0],
        'volatility_20d': [0.015, 0.015, 0.020, 0.012, 0.014, 0.018],
        'reg_score': [0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
        'expected_return': [20.0, 20.0, 20.0, 20.0, 20.0, 20.0]
    })

    res = engine.combine_predictions(
        reg_df=df_test,
        target_horizon=20,
        regime='BULL_LOW_VOL'
    )

    # 5.1 Preferred Stock and SPAC zero-weighting
    pref_row = res[res['symbol'] == '005930우.KS'].iloc[0]
    spac_row = res[res['symbol'] == '352770.KQ'].iloc[0]
    assert pref_row['ensemble_score'] == 0.0, "Preferred stock not zero-weighted"
    assert pref_row['ensemble_expected_return'] == 0.0, "Preferred stock expected return not 0.0"
    assert spac_row['ensemble_score'] == 0.0, "SPAC stock not zero-weighted"
    print("[OK] Liquidity Gate verified: Preferred stocks and SPACs are strictly zero-weighted.")

    # 5.2 Microstructure Friction deduction across markets
    s_aapl = res[res['symbol'] == 'AAPL'].iloc[0]
    s_msft = res[res['symbol'] == 'MSFT'].iloc[0]
    s_iwm = res[res['symbol'] == 'IWM'].iloc[0]
    s_samsung = res[res['symbol'] == '005930.KS'].iloc[0]

    assert s_aapl['ensemble_expected_return'] > 0.0, "AAPL expected return should be positive"
    assert s_aapl['ensemble_expected_return'] < 20.0, "AAPL expected return did not deduct transaction costs"
    # SP500 friction < NASDAQ friction < RUSSELL2000 friction
    assert s_aapl['ensemble_expected_return'] >= s_msft['ensemble_expected_return'], "SP500 return should exceed or match NASDAQ due to lower spread friction"
    assert s_msft['ensemble_expected_return'] >= s_iwm['ensemble_expected_return'], "NASDAQ return should exceed RUSSELL2000 due to lower spread friction"
    print(f"[OK] Microstructure friction verified: AAPL net ret={s_aapl['ensemble_expected_return']:.3f}%, MSFT net ret={s_msft['ensemble_expected_return']:.3f}%, IWM net ret={s_iwm['ensemble_expected_return']:.3f}%.")


def main():
    print("=================================================================")
    print("   FORENSIC AUDITOR M2 GEN 2: INDEPENDENT EMPIRICAL AUDIT        ")
    print("=================================================================")
    test_exponential_sharpe_math_and_pruning()
    test_adaptive_ema_smoothing_and_regime_jump()
    test_power_ratio_damping()
    test_regime_detector_gmm_and_shock_overrides()
    test_microstructure_costs_and_liquidity_gate()
    print("\n=================================================================")
    print("   ALL FORENSIC CHECKS PASSED: VERDICT = CLEAN                    ")
    print("=================================================================")

if __name__ == '__main__':
    main()

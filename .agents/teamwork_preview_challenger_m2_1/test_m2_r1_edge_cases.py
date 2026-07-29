import os
import sys
import numpy as np
import pandas as pd

# Add Project Root to sys.path
PROJECT_ROOT = r"d:\Finance\code\stock"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine

def run_tests():
    print("==================================================")
    print(" EMPIRICAL TEST SUITE: M2 R1 EnsembleScoringEngine ")
    print("==================================================")

    engine = EnsembleScoringEngine()

    # ----------------------------------------------------
    # Test 1 & 2: Valid 0.0 vs NaN Score Handling & Denominator Exclusion
    # ----------------------------------------------------
    print("\n--- Test 1 & 2: Valid 0.0 Score vs NaN Score & Denominator Exclusion ---")
    reg_df = pd.DataFrame({
        'symbol': ['SYM_ZERO', 'SYM_NAN', 'SYM_NORMAL'],
        20: [0.0, np.nan, 0.10]
    })
    # Map 20d expected return to reg_score: 0.0 -> 0.0, NaN -> NaN, 0.10 -> 0.40

    surge_df = pd.DataFrame({
        'symbol': ['SYM_ZERO', 'SYM_NAN', 'SYM_NORMAL'],
        'surge_20d': [0.80, 0.80, 0.80]
    })

    res = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=surge_df,
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame(),
        target_horizon=20
    )

    sym_zero_score = res.loc[res['symbol'] == 'SYM_ZERO', 'ensemble_score'].values[0]
    sym_nan_score = res.loc[res['symbol'] == 'SYM_NAN', 'ensemble_score'].values[0]
    sym_normal_score = res.loc[res['symbol'] == 'SYM_NORMAL', 'ensemble_score'].values[0]

    base_w = engine.get_base_weights('BULL_LOW_VOL')
    w_reg = base_w['regression']
    w_surge = base_w['surge']

    expected_zero = (0.0 * w_reg + 0.80 * w_surge) / (w_reg + w_surge)
    expected_nan = (0.80 * w_surge) / (w_surge)

    print(f"BULL_LOW_VOL Base Weights: reg={w_reg:.4f}, surge={w_surge:.4f}")
    print(f"SYM_ZERO (reg=0.0, surge=0.80) score: {sym_zero_score:.6f} (Expected: {expected_zero:.6f})")
    print(f"SYM_NAN  (reg=NaN, surge=0.80) score: {sym_nan_score:.6f} (Expected: {expected_nan:.6f})")
    print(f"SYM_NORMAL (reg=0.4, surge=0.80) score: {sym_normal_score:.6f}")

    t1_pass = np.isclose(sym_zero_score, expected_zero, atol=1e-5)
    t2_pass = np.isclose(sym_nan_score, expected_nan, atol=1e-5)
    print(f"Test 1 (0.0 receives weight in denominator): {'PASS' if t1_pass else 'FAIL'}")
    print(f"Test 2 (NaN excluded from denominator): {'PASS' if t2_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 3: Infinities (+inf, -inf)
    # ----------------------------------------------------
    print("\n--- Test 3: Infinities (+inf, -inf) ---")
    reg_inf_df = pd.DataFrame({
        'symbol': ['SYM_POS_INF', 'SYM_NEG_INF'],
        20: [np.inf, -np.inf]
    })
    surge_inf_df = pd.DataFrame({
        'symbol': ['SYM_POS_INF', 'SYM_NEG_INF'],
        'surge_20d': [0.50, 0.50]
    })

    res_inf = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_inf_df,
        surge_df=surge_inf_df,
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame(),
        target_horizon=20
    )

    pos_inf_score = res_inf.loc[res_inf['symbol'] == 'SYM_POS_INF', 'ensemble_score'].values[0]
    neg_inf_score = res_inf.loc[res_inf['symbol'] == 'SYM_NEG_INF', 'ensemble_score'].values[0]

    print(f"SYM_POS_INF ensemble_score: {pos_inf_score}")
    print(f"SYM_NEG_INF ensemble_score: {neg_inf_score}")

    t3_pass = (pos_inf_score == 0.50) and (neg_inf_score == 0.50) and np.isfinite(pos_inf_score) and np.isfinite(neg_inf_score)
    print(f"Test 3 (Infinities masked out cleanly): {'PASS' if t3_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 4: All-NaN Strategies
    # ----------------------------------------------------
    print("\n--- Test 4: All-NaN Strategies ---")
    reg_all_nan = pd.DataFrame({'symbol': ['SYM_ALL_NAN'], 20: [np.nan]})
    surge_all_nan = pd.DataFrame({'symbol': ['SYM_ALL_NAN'], 'surge_20d': [np.nan]})

    res_all_nan = engine.calculate_ensemble_score(
        regime='SIDEWAYS_LOW_VOL',
        regression_df=reg_all_nan,
        surge_df=surge_all_nan,
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame()
    )

    all_nan_score = res_all_nan.loc[res_all_nan['symbol'] == 'SYM_ALL_NAN', 'ensemble_score'].values[0]
    print(f"SYM_ALL_NAN ensemble_score: {all_nan_score}")

    t4_pass = (all_nan_score == 0.0) and not np.isnan(all_nan_score)
    print(f"Test 4 (All-NaN strategies produce 0.0 score safely): {'PASS' if t4_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 5: Extreme VIX (>50)
    # ----------------------------------------------------
    print("\n--- Test 5: Extreme VIX (>50) ---")
    weights_vix_55 = engine.get_base_weights('BEAR_HIGH_VOL', vix_val=55.0)
    print("Weights with VIX=55.0:")
    for k, v in weights_vix_55.items():
        print(f"  {k:<20}: {v:.4f}")

    sum_vix_w = sum(weights_vix_55.values())
    surge_vix_w = weights_vix_55['surge']
    vcp_ml_vix_w = weights_vix_55['vcp_ml']
    stat_arb_vix_w = weights_vix_55['stat_arb']

    t5_pass = np.isclose(sum_vix_w, 1.0) and surge_vix_w == 0.0 and vcp_ml_vix_w == 0.0 and stat_arb_vix_w > 0.15
    print(f"Test 5 (Extreme VIX > 50 overrides applied & normalized): {'PASS' if t5_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 6: Negative Yield Spread / Macro Modifier
    # ----------------------------------------------------
    print("\n--- Test 6: Negative Yield Spread (HIGH_YIELD_BEAR Macro Modifier) ---")
    weights_macro = engine.get_base_weights('BEAR_LOW_VOL', macro_label='HIGH_YIELD_BEAR')
    print("Weights with HIGH_YIELD_BEAR:")
    for k, v in weights_macro.items():
        print(f"  {k:<20}: {v:.4f}")

    sum_macro_w = sum(weights_macro.values())
    t6_pass = np.isclose(sum_macro_w, 1.0) and weights_macro['regression'] > 0.20
    print(f"Test 6 (Macro override applied & normalized): {'PASS' if t6_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 7: Zero-Volume Symbols & Liquidity Gate
    # ----------------------------------------------------
    print("\n--- Test 7: Zero-Volume Symbols & Liquidity Gate ---")
    reg_vol = pd.DataFrame({
        'symbol': ['SYM_NORMAL_VOL', 'SYM_ZERO_VOL'],
        'name': ['Normal Corp', 'Zero Corp'],
        'volume': [10000.0, 0.0],
        20: [0.15, 0.15]
    })
    surge_vol = pd.DataFrame({
        'symbol': ['SYM_NORMAL_VOL', 'SYM_ZERO_VOL'],
        'surge_20d': [0.80, 0.80]
    })

    res_vol = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_vol,
        surge_df=surge_vol,
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame()
    )

    norm_vol_score = res_vol.loc[res_vol['symbol'] == 'SYM_NORMAL_VOL', 'ensemble_score'].values[0]
    zero_vol_score = res_vol.loc[res_vol['symbol'] == 'SYM_ZERO_VOL', 'ensemble_score'].values[0]

    print(f"SYM_NORMAL_VOL (volume=10000) ensemble_score: {norm_vol_score:.6f}")
    print(f"SYM_ZERO_VOL   (volume=0)     ensemble_score: {zero_vol_score:.6f}")

    t7_pass = (norm_vol_score > 0.0) and (zero_vol_score == 0.0)
    print(f"Test 7 (Zero-volume symbols zero-weighted): {'PASS' if t7_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Test 8: Raw Scores Retain True NaNs vs Formatted Output 0.0
    # ----------------------------------------------------
    print("\n--- Test 8: Raw Scores Retain True NaNs ---")
    reg_raw = pd.DataFrame({'symbol': ['SYM_TEST'], 20: [0.20]})
    # surge_df is empty, so surge_score is missing (NaN in raw_scores)

    res_raw = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_raw,
        surge_df=pd.DataFrame(),
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame()
    )

    raw_scores_df = res_raw.attrs['raw_scores']
    
    formatted_surge = res_raw.loc[res_raw['symbol'] == 'SYM_TEST', 'surge_score'].values[0]
    raw_surge = raw_scores_df.loc[raw_scores_df['symbol'] == 'SYM_TEST', 'surge_score'].values[0]

    print(f"Formatted Output surge_score: {formatted_surge}")
    print(f"Raw Scores surge_score: {raw_surge}")

    t8_pass = (formatted_surge == 0.0) and pd.isna(raw_surge)
    print(f"Test 8 (Raw scores retain true NaN while formatted output has 0.0): {'PASS' if t8_pass else 'FAIL'}")

    # ----------------------------------------------------
    # Final Verdict Summary
    # ----------------------------------------------------
    all_tests = [t1_pass, t2_pass, t3_pass, t4_pass, t5_pass, t6_pass, t7_pass, t8_pass]
    overall_pass = all(all_tests)

    print("\n==================================================")
    print(f" FINAL EMPIRICAL VERDICT: {'PASS' if overall_pass else 'FAIL'}")
    print("==================================================")

    return overall_pass

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

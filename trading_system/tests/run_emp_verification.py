"""
Empirical Data Extractor for Handoff Report
Runs test suite and prints exact quantitative tables for handoff.md.
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from trading_system.src.execution.slippage_feedback import SlippageFeedbackEngine, SlippageMetrics
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine

def main():
    print("=== EMPIRICAL VERIFICATION DATA REPORT ===")
    
    # 1. Monotonicity Verification
    print("\n--- 1. Monotonicity & Net Expected Return Impact ---")
    scorer = EnsembleScoringEngine()
    df_candidates = pd.DataFrame([
        {'symbol': '005930.KS', 'name': 'Samsung', 'market': 'KOSPI', 'close': 70000.0, 'volume': 1000000.0, 'reg_pred': 0.15, 'volatility_20d': 0.02},
        {'symbol': '035720.KQ', 'name': 'Kakao', 'market': 'KOSDAQ', 'close': 50000.0, 'volume': 200000.0, 'reg_pred': 0.12, 'volatility_20d': 0.035},
        {'symbol': 'AAPL', 'name': 'Apple', 'market': 'SP500', 'close': 180.0, 'volume': 5000000.0, 'reg_pred': 0.10, 'volatility_20d': 0.015}
    ])

    factors = [0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 2.50, 3.00]
    results = []

    for f in factors:
        scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=f))
        scored = scorer.combine_predictions(reg_df=df_candidates.copy())
        
        row_dict = {'factor': f}
        for _, row in scored.iterrows():
            sym = row['symbol']
            # Recompute total_cost_pct for reporting
            # ensemble_expected_return = raw_exp_ret - cost_series * 100
            # raw_exp_ret is reg_pred * 100
            raw_exp_ret = df_candidates.loc[df_candidates['symbol'] == sym, 'reg_pred'].values[0] * 100.0
            net_ret = row['ensemble_expected_return']
            cost_pct = (raw_exp_ret - net_ret) / 100.0
            row_dict[f"{sym}_cost_pct"] = cost_pct
            row_dict[f"{sym}_net_ret"] = net_ret
        results.append(row_dict)

    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))

    # 2. Asset Score Demotion
    print("\n--- 2. High-Slippage Asset Score Demotion ---")
    df_demotion = pd.DataFrame([
        {'symbol': 'HIGH_COST_STOCK', 'name': 'HighCost', 'market': 'KOSDAQ', 'close': 10000.0, 'volume': 60000.0, 'reg_pred': 0.15, 'volatility_20d': 0.05},
        {'symbol': 'LOW_COST_STOCK', 'name': 'LowCost', 'market': 'KOSPI', 'close': 100000.0, 'volume': 2000000.0, 'reg_pred': 0.14, 'volatility_20d': 0.01},
        {'symbol': 'HARD_ILLIQUID_STOCK', 'name': 'HardIlliquid', 'market': 'KOSDAQ', 'close': 5000.0, 'volume': 10000.0, 'reg_pred': 0.20, 'volatility_20d': 0.05}
    ])

    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=1.0))
    scored_1x = scorer.combine_predictions(reg_df=df_demotion.copy())
    
    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=3.0))
    scored_3x = scorer.combine_predictions(reg_df=df_demotion.copy())

    print("1.0x Scaling:")
    print(scored_1x[['symbol', 'ensemble_expected_return', 'ensemble_score']])
    print("3.0x Scaling:")
    print(scored_3x[['symbol', 'ensemble_expected_return', 'ensemble_score']])

    # 3. Clamping Verification
    print("\n--- 3. Clamping Bounds Verification ---")
    inputs = [-99.0, -5.0, 0.0, 0.49, 0.50, 1.00, 2.00, 3.00, 3.01, 100.0]
    clamping_res = []
    for inp in inputs:
        scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=inp))
        actual = scorer.cost_scaling_factor
        clamping_res.append({'input': inp, 'clamped': actual, 'valid': 0.50 <= actual <= 3.00})
    
    clamp_df = pd.DataFrame(clamping_res)
    print(clamp_df.to_string(index=False))

if __name__ == '__main__':
    main()

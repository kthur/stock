import sys
import os
import pandas as pd
import numpy as np

# Ensure project root and trading_system are in sys.path
PROJECT_ROOT = r"d:\Finance\code\stock"
TRADING_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "trading_system")
if TRADING_SYSTEM_DIR not in sys.path:
    sys.path.insert(0, TRADING_SYSTEM_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import TradingConfig
from src.ai.ensemble_scorer import EnsembleScoringEngine

def run_tests():
    print("==================================================")
    print("EMPIRICAL TEST: EnsembleScoringEngine M2-2 Verification")
    print("==================================================")
    
    config = TradingConfig()
    scorer = EnsembleScoringEngine(config=config)
    
    # Define test symbols across 4 markets
    test_symbols_data = [
        # SP500 normal
        {"symbol": "AAPL", "market": "SP500", "name": "Apple Inc.", "volume": 1000000.0, "score": 0.50},
        {"symbol": "SPAC_US", "market": "SP500", "name": "ACME SPAC Corp", "volume": 500000.0, "score": 0.50},
        
        # KOSPI normal & preferred
        {"symbol": "005930", "market": "KOSPI", "name": "삼성전자", "volume": 10000000.0, "score": 0.50},
        {"symbol": "005935", "market": "KOSPI", "name": "삼성전자우", "volume": 500000.0, "score": 0.50},
        {"symbol": "005387", "market": "KOSPI", "name": "현대차2우B", "volume": 300000.0, "score": 0.50},
        {"symbol": "005930.KS", "market": "KOSPI", "name": "삼성전자(KS)", "volume": 10000000.0, "score": 0.50},
        
        # KOSDAQ normal & SPAC
        {"symbol": "035720", "market": "KOSDAQ", "name": "카카오", "volume": 2000000.0, "score": 0.50},
        {"symbol": "475150", "market": "KOSDAQ", "name": "하나금융31호스팩", "volume": 100000.0, "score": 0.50},
        {"symbol": "035720.KQ", "market": "KOSDAQ", "name": "카카오(KQ)", "volume": 2000000.0, "score": 0.50},
        
        # KONEX normal
        {"symbol": "217620", "market": "KONEX", "name": "지노믹트리", "volume": 50000.0, "score": 0.50},
        {"symbol": "217620.KN", "market": "KONEX", "name": "지노믹트리(KN)", "volume": 50000.0, "score": 0.50},
        
        # Zero volume
        {"symbol": "000001", "market": "KOSPI", "name": "거래량제로종목", "volume": 0.0, "score": 0.50},
    ]
    
    input_df = pd.DataFrame(test_symbols_data)
    
    print("\n--- Input DataFrame provided to calculate_ensemble_score ---")
    print(input_df[['symbol', 'market', 'name', 'volume', 'score']])
    
    # We pass regression_df with column 20 as score
    reg_df = input_df[['symbol', 'market', 'name', 'volume']].copy()
    # expected return 25% -> score = 25/25 = 1.0, or 0.125 -> score = 0.5
    # In ensemble_scorer: reg_score = reg_pred / 0.25. So for reg_score = 0.5, reg_pred = 0.125
    reg_df[20] = 0.125
    
    surge_df = pd.DataFrame(columns=['symbol'])
    lead_lag_df = pd.DataFrame(columns=['symbol'])
    vcp_ml_df = pd.DataFrame(columns=['symbol'])
    
    result_df = scorer.calculate_ensemble_score(
        regime="BULL_LOW_VOL",
        regression_df=reg_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_ml_df=vcp_ml_df,
        target_horizon=20
    )
    
    print("\n--- Output DataFrame from calculate_ensemble_score ---")
    print(result_df)
    
    # Inspect columns present in result_df
    print("\nColumns in result_df:", result_df.columns.tolist())
    
    # Check expected returns and transaction cost deduction per market
    # raw_exp_ret for ensemble_score=0.5 with mult=0.2 is: 0.5 * 0.2 * 100 = 10.0 (%)
    # Required deductions:
    # SP500: 0.10% fee + 0.50% slippage = 0.60% -> net return = 10.0 - 0.60 = 9.40%
    # KOSPI: 0.35% fee + 0.50% slippage = 0.85% -> net return = 10.0 - 0.85 = 9.15%
    # KOSDAQ: 0.50% fee + 0.50% slippage = 1.00% -> net return = 10.0 - 1.00 = 9.00%
    # KONEX: 0.80% fee + 0.50% slippage = 1.30% -> net return = 10.0 - 1.30 = 8.70%
    
    print("\n--- DETAILED SYMBOL ANALYSIS ---")
    for _, row in result_df.iterrows():
        sym = row['symbol']
        score = row['ensemble_score']
        exp_ret = row['ensemble_expected_return']
        print(f"Symbol: {sym:<12} | Score: {score:.4f} | Net Exp Return: {exp_ret:.4f}%")
        
    print("\n--- TEST RATIONALE SUMMARY ---")
    rationale = scorer.get_regime_reasoning_summary("BULL_LOW_VOL")
    print(rationale)

if __name__ == "__main__":
    run_tests()

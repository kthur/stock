import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "trading_system"))

import pandas as pd
import numpy as np
from src.ai.ensemble_scorer import EnsembleScoringEngine

def test_metadata_retention_and_filtering():
    """
    Empirical Test for Worker 2's metadata retention fix in EnsembleScoringEngine:
    1. Verify preferred stocks ('삼성전자우', '00593K') and SPACs ('하나금융25호스팩') receive ensemble_score == 0.0
    2. Verify KOSDAQ, KONEX, KOSPI, and SP500 receive correct transaction cost deductions:
       - KOSDAQ: 0.50% fee + 0.50% slippage = 1.00%
       - KONEX:  0.80% fee + 0.50% slippage = 1.30%
       - KOSPI:  0.35% fee + 0.50% slippage = 0.85%
       - SP500:  0.10% fee + 0.50% slippage = 0.60%
    """
    engine = EnsembleScoringEngine()
    
    # 1. Create test DataFrame
    test_data = pd.DataFrame({
        'symbol': ['005935', '00593K', '207700', '035720', '217880', '005930', 'AAPL'],
        'name': ['삼성전자우', '삼성전자1우B', '하나금융25호스팩', '카카오', '메디키나폰드', '삼성전자', 'Apple Inc.'],
        'market': ['KOSPI', 'KOSPI', 'KOSDAQ', 'KOSDAQ', 'KONEX', 'KOSPI', 'SP500'],
        'volume': [100000, 100000, 100000, 100000, 100000, 100000, 100000],
        20: [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10]
    })
    
    empty_df = pd.DataFrame(columns=['symbol'])
    
    # Run ensemble score calculation
    result_df = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=test_data,
        surge_df=empty_df,
        lead_lag_df=empty_df,
        vcp_ml_df=empty_df,
        target_horizon=20
    )
    
    print("\n--- Test Results DataFrame ---")
    print(result_df[['symbol', 'name', 'market', 'ensemble_score', 'ensemble_expected_return']])
    
    # Assertions
    results = {}
    for idx, row in result_df.iterrows():
        results[row['symbol']] = row
        
    # Check Preferred stocks & SPACs -> ensemble_score == 0.0
    pref1 = results['005935']  # 삼성전자우
    pref2 = results['00593K']  # 삼성전자1우B
    spac = results['207700']   # 하나금융25호스팩
    
    assert pref1['ensemble_score'] == 0.0, f"Expected 0.0 for 삼성전자우, got {pref1['ensemble_score']}"
    assert pref2['ensemble_score'] == 0.0, f"Expected 0.0 for 삼성전자1우B, got {pref2['ensemble_score']}"
    assert spac['ensemble_score'] == 0.0, f"Expected 0.0 for SPAC, got {spac['ensemble_score']}"
    print("PASS: Preferred stocks and SPAC receive ensemble_score == 0.0")
    
    # Raw expected return calculation: score * 0.20 * 100 = 0.40 * 20.0 = 8.00%
    # Expected return after deduction = 8.00 - cost%
    
    # KOSDAQ: 035720 (카카오)
    kosdaq = results['035720']
    expected_kosdaq_ret = 8.00 - 1.00  # 7.00%
    assert abs(kosdaq['ensemble_expected_return'] - expected_kosdaq_ret) < 1e-4, \
        f"KOSDAQ expected return mismatch: expected {expected_kosdaq_ret}, got {kosdaq['ensemble_expected_return']}"
    print("PASS: KOSDAQ transaction cost deduction (1.00%) correctly applied.")
    
    # KONEX: 217880 (메디키나폰드)
    konex = results['217880']
    expected_konex_ret = 8.00 - 1.30  # 6.70%
    assert abs(konex['ensemble_expected_return'] - expected_konex_ret) < 1e-4, \
        f"KONEX expected return mismatch: expected {expected_konex_ret}, got {konex['ensemble_expected_return']}"
    print("PASS: KONEX transaction cost deduction (1.30%) correctly applied.")
    
    # KOSPI: 005930 (삼성전자)
    kospi = results['005930']
    expected_kospi_ret = 8.00 - 0.85  # 7.15%
    assert abs(kospi['ensemble_expected_return'] - expected_kospi_ret) < 1e-4, \
        f"KOSPI expected return mismatch: expected {expected_kospi_ret}, got {kospi['ensemble_expected_return']}"
    print("PASS: KOSPI transaction cost deduction (0.85%) correctly applied.")
    
    # SP500: AAPL (Apple Inc.)
    sp500 = results['AAPL']
    expected_sp500_ret = 8.00 - 0.60  # 7.40%
    assert abs(sp500['ensemble_expected_return'] - expected_sp500_ret) < 1e-4, \
        f"SP500 expected return mismatch: expected {expected_sp500_ret}, got {sp500['ensemble_expected_return']}"
    print("PASS: SP500 transaction cost deduction (0.60%) correctly applied.")
    
    print("\nALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_metadata_retention_and_filtering()

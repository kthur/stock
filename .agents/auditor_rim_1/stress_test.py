import sys
import os
import math
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('trading_system'))

from src.core.rim_valuation import RIMValuationEngine, is_preferred_share
from src.data_layer.indicator_storage import MarketIndicatorStorage
from generate_report import parse_rim, build_html, EnsembleData, EnsembleMarket, EnsembleRow
from merge_predictions import merge_generic_strategy_files

def run_stress_tests():
    print("=== STARTING ADVERSARIAL STRESS TESTS ===")
    engine = RIMValuationEngine(default_required_return=0.08)

    # 1. Extreme NaN, Inf, and Malformed inputs
    print("\n[Test 1] Extreme NaN/Inf/Malformed types:")
    malformed_df = pd.DataFrame([
        {'symbol': 'INF_01', 'market': 'NASDAQ', 'Close': float('inf'), 'bps': float('inf'), 'roe': float('inf')},
        {'symbol': 'NEG_01', 'market': 'SP500', 'Close': -100.0, 'bps': -50.0, 'roe': -0.20},
        {'symbol': 'STR_01', 'market': 'KOSDAQ', 'Close': "invalid_price", 'bps': "invalid_bps", 'roe': "bad_roe"},
        {'symbol': 'ZERO_01', 'market': 'RUSSELL2000', 'Close': 0.0, 'bps': 0.0, 'roe': 0.0},
        {'symbol': 'MISS_01', 'market': 'KOSPI'},
    ])
    res1 = engine.compute_rim_scores(malformed_df)
    assert len(res1) == 5, f"Expected 5 rows, got {len(res1)}"
    # All scores should be NaN or properly handled without crashing
    for i, row in res1.iterrows():
        assert np.isnan(row['rim_score']) or (0.0 <= row['rim_score'] <= 1.0), f"Row {i} invalid rim_score: {row['rim_score']}"
    print(" -> PASS: Malformed inputs handled cleanly with no exceptions.")

    # 2. Fake BPS elimination stress test
    print("\n[Test 2] Fake BPS Elimination & Zero Phantom Discounts:")
    cyclical_df = pd.DataFrame([
        {'symbol': 'CYCLIC_NO_BV', 'market': 'KOSPI', 'Close': 5000.0, 'eps': 2000.0, 'roe': 0.12}, # P/E = 2.5
        {'symbol': 'GENUINE_BV', 'market': 'KOSPI', 'Close': 5000.0, 'eps': 2000.0, 'bps': 6000.0, 'roe': 0.12},
    ])
    res2 = engine.compute_rim_scores(cyclical_df).set_index('symbol')
    assert np.isnan(res2.loc['CYCLIC_NO_BV', 'bps']), "CYCLIC_NO_BV should have NaN BPS"
    assert np.isnan(res2.loc['CYCLIC_NO_BV', 'intrinsic_value']), "CYCLIC_NO_BV should have NaN intrinsic value"
    assert np.isnan(res2.loc['CYCLIC_NO_BV', 'discount_ratio']), "CYCLIC_NO_BV should have NaN discount ratio"
    assert np.isnan(res2.loc['CYCLIC_NO_BV', 'rim_score']), "CYCLIC_NO_BV should have NaN rim score"
    assert res2.loc['GENUINE_BV', 'bps'] == 6000.0, "GENUINE_BV should preserve valid BPS"
    assert not np.isnan(res2.loc['GENUINE_BV', 'rim_score']), "GENUINE_BV should have valid score"
    print(" -> PASS: Fake BPS strictly eliminated, no phantom discounts created.")

    # 3. Holding company detection & SOTP discount precision
    print("\n[Test 3] Holding company detection and mathematical SOTP discount:")
    hc_df = pd.DataFrame([
        {
            'symbol': '000001', 'name': '한진칼홀딩스', 'market': 'KOSPI', 'Close': 10000.0,
            'bps': 20000.0, 'roe': 0.15, 'total_debt': 100000.0, 'cash_equivalents': 20000.0,
            'shares_outstanding': 10.0, # net debt per share = 8000.0
        },
        {
            'symbol': '000002', 'name': '일반기업', 'market': 'KOSPI', 'Close': 10000.0,
            'bps': 20000.0, 'roe': 0.15, 'total_debt': 100000.0, 'cash_equivalents': 20000.0,
            'shares_outstanding': 10.0,
        }
    ])
    res3 = engine.compute_rim_scores(hc_df).set_index('symbol')
    assert res3.loc['000001', 'holding_co_flag'] == True, "한진칼홀딩스 should be flagged as holding company"
    assert res3.loc['000002', 'holding_co_flag'] == False, "일반기업 should not be flagged as holding company"
    # Net debt = 8000, BPS adj = 20000 - 8000 = 12000
    assert abs(res3.loc['000001', 'bps_adjusted'] - 12000.0) < 1e-5
    # Holding company intrinsic value must be strictly less than non-holding company
    assert res3.loc['000001', 'intrinsic_value'] < res3.loc['000002', 'intrinsic_value']
    print(f" -> PASS: Holding co IV = {res3.loc['000001', 'intrinsic_value']:.2f} < Regular IV = {res3.loc['000002', 'intrinsic_value']:.2f}")

    # 4. 5 Markets Coverage Verification
    print("\n[Test 4] 5 Markets Coverage & Output Consistency:")
    markets = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']
    market_rows = []
    for m in markets:
        market_rows.append({
            'symbol': f'SYM_{m}',
            'market': m,
            'Close': 100.0,
            'bps': 120.0,
            'roe': 0.10,
            'operating_income': 10.0,
            'net_income': 10.0
        })
    df_5m = pd.DataFrame(market_rows)
    res_5m = engine.compute_rim_scores(df_5m)
    assert len(res_5m) == 5
    assert set(res_5m['market'].tolist()) == set(markets)
    assert res_5m['rim_score'].notna().all()
    print(" -> PASS: All 5 markets computed valid RIM scores.")

    # 5. Report parser resilience across 8, 9, 12 columns
    print("\n[Test 5] Report Parser 12/9/8 column compatibility:")
    txt_12 = """=== Strategy 9: RIM ===
Date: 2026-08-22
1    005930    삼성전자    KOSPI    70000.00    93750.00    +33.9%    15.0%    15.0%    100%    [ADJ]    95.0%
"""
    txt_9 = """=== Strategy 9: RIM ===
Date: 2026-08-22
1    005930    삼성전자    KOSPI    70000.00    93750.00    +33.9%    100%    95.0%
"""
    txt_8 = """=== Strategy 9: RIM ===
Date: 2026-08-22
1    005930    삼성전자    KOSPI    70000.00    93750.00    +33.9%    95.0%
"""
    _, r12 = parse_rim(txt_12)
    _, r9 = parse_rim(txt_9)
    _, r8 = parse_rim(txt_8)
    assert len(r12) == 1 and r12[0].filter_tags == "[ADJ]" and r12[0].score == "95.0%"
    assert len(r9) == 1 and r9[0].eq == "100%" and r9[0].score == "95.0%"
    assert len(r8) == 1 and r8[0].score == "95.0%"
    print(" -> PASS: parse_rim handles 12-col, 9-col, and 8-col formats seamlessly.")

    # 6. Preferred Share Recognition
    print("\n[Test 6] Preferred Share pattern checks:")
    assert is_preferred_share("005935") == True
    assert is_preferred_share("000025") == True
    assert is_preferred_share("00680K") == True
    assert is_preferred_share("33626L") == True
    assert is_preferred_share("005930") == False
    assert is_preferred_share("AAPL") == False
    print(" -> PASS: Preferred share regex verified accurately.")

    print("\n=== ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_stress_tests()

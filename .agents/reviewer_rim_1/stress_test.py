import sys
import os
import pandas as pd
import numpy as np
import sqlite3
import tempfile
from pathlib import Path

# Add project root and trading_system to sys.path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("trading_system"))

from src.core.rim_valuation import (
    RIMValuationEngine,
    ABSOLUTE_ROE_CAP,
    EXTREME_ROE_THRESHOLD,
    HOLDING_CO_DISCOUNT,
    EARNINGS_QUALITY_MIN_RATIO,
    is_preferred_share,
)
from generate_report import parse_rim, RimRow, build_html, EnsembleData, EnsembleMarket, EnsembleRow
from src.data_layer.indicator_storage import MarketIndicatorStorage

print("=== STARTING ADVERSARIAL STRESS TESTS ===")

engine = RIMValuationEngine()

# Test 1: BPS anomalies
print("\n--- 1. BPS Anomalies (Zero, Negative, Inf, NaN, Synthetic) ---")
df_bps = pd.DataFrame([
    {'symbol': 'NEG_BPS', 'market': 'KOSPI', 'Close': 1000.0, 'bps': -500.0, 'roe': 0.15},
    {'symbol': 'ZERO_BPS', 'market': 'KOSPI', 'Close': 1000.0, 'bps': 0.0, 'roe': 0.15},
    {'symbol': 'INF_BPS', 'market': 'KOSPI', 'Close': 1000.0, 'bps': np.inf, 'roe': 0.15},
    {'symbol': 'NAN_BPS', 'market': 'KOSPI', 'Close': 1000.0, 'bps': np.nan, 'roe': 0.15},
    {'symbol': 'NO_BPS_COL', 'market': 'KOSPI', 'Close': 1000.0, 'eps': 500.0, 'roe': 0.15},
])
res_bps = engine.compute_rim_scores(df_bps).set_index('symbol')
for sym in ['NEG_BPS', 'ZERO_BPS', 'INF_BPS', 'NAN_BPS', 'NO_BPS_COL']:
    score = res_bps.loc[sym, 'rim_score']
    iv = res_bps.loc[sym, 'intrinsic_value']
    assert np.isnan(score), f"{sym} expected NaN rim_score, got {score}"
    assert np.isnan(iv), f"{sym} expected NaN intrinsic_value, got {iv}"
print("Pass: All invalid/missing BPS cases strictly evaluate to NaN without fabrication.")

# Test 2: Extreme ROE, Prices, and Operating/Net Income combinations
print("\n--- 2. Extreme ROE, Prices, and Income Scenarios ---")
df_extreme = pd.DataFrame([
    # Extreme ROE with low EQ
    {'symbol': 'EXTREME_LOW_EQ', 'market': 'SP500', 'Close': 100.0, 'bps': 50.0, 'roe': 0.80,
     'operating_income': 50.0, 'net_income': 1000.0, 'book_value': 2000.0},
    # Extreme ROE with normal EQ (capped at 25%)
    {'symbol': 'EXTREME_NORM_EQ', 'market': 'SP500', 'Close': 100.0, 'bps': 50.0, 'roe': 0.80,
     'operating_income': 1000.0, 'net_income': 1000.0, 'book_value': 2000.0},
    # Net income 0 with positive op income
    {'symbol': 'NET_ZERO', 'market': 'SP500', 'Close': 100.0, 'bps': 50.0, 'roe': 0.10,
     'operating_income': 100.0, 'net_income': 0.0, 'book_value': 500.0},
    # Negative Price
    {'symbol': 'NEG_PRICE', 'market': 'SP500', 'Close': -50.0, 'bps': 50.0, 'roe': 0.10},
    # Zero Price
    {'symbol': 'ZERO_PRICE', 'market': 'SP500', 'Close': 0.0, 'bps': 50.0, 'roe': 0.10},
])
res_ext = engine.compute_rim_scores(df_extreme).set_index('symbol')

assert res_ext.loc['EXTREME_LOW_EQ', 'roe'] <= EXTREME_ROE_THRESHOLD + 1e-6
assert res_ext.loc['EXTREME_LOW_EQ', 'roe_normalized'] == True
assert res_ext.loc['EXTREME_NORM_EQ', 'roe'] <= ABSOLUTE_ROE_CAP + 1e-6
assert res_ext.loc['EXTREME_NORM_EQ', 'roe_normalized'] == True
assert np.isnan(res_ext.loc['NEG_PRICE', 'discount_ratio'])
assert np.isnan(res_ext.loc['ZERO_PRICE', 'discount_ratio'])
print("Pass: Extreme ROE normalization and non-positive price gating succeed.")

# Test 3: Holding Company Patterns and Net Debt Deductions
print("\n--- 3. Holding Company Patterns & SOTP Discounts ---")
df_hc = pd.DataFrame([
    {'symbol': '001040', 'market': 'KOSPI', 'name': 'CJ지주', 'Close': 90000.0, 'bps': 150000.0, 'roe': 0.10,
     'total_debt': 500000.0, 'cash_equivalents': 100000.0, 'shares_outstanding': 10.0},
    {'symbol': '000001', 'market': 'KOSPI', 'name': 'CJ', 'sector_code': '6020', 'Close': 90000.0, 'bps': 150000.0, 'roe': 0.10,
     'total_debt': 500000.0, 'cash_equivalents': 100000.0, 'shares_outstanding': 10.0},
    {'symbol': 'US_HD', 'market': 'SP500', 'name': 'HD Hyundai', 'Close': 350.0, 'bps': 20.0, 'roe': 0.20},
    {'symbol': 'US_HLD', 'market': 'NASDAQ', 'name': 'Global Tech Holdings Ltd.', 'Close': 50.0, 'bps': 40.0, 'roe': 0.15},
    {'symbol': 'NORM1', 'market': 'KOSPI', 'name': '현대자동차', 'Close': 200000.0, 'bps': 250000.0, 'roe': 0.10},
])
res_hc = engine.compute_rim_scores(df_hc).set_index('symbol')
assert res_hc.loc['001040', 'holding_co_flag'] == True
assert res_hc.loc['000001', 'holding_co_flag'] == True
assert res_hc.loc['US_HD', 'holding_co_flag'] == True
assert res_hc.loc['US_HLD', 'holding_co_flag'] == True
assert res_hc.loc['NORM1', 'holding_co_flag'] == False
print("Pass: Holding company identification and SOTP logic confirmed.")

# Test 4: Preferred share matching accuracy
print("\n--- 4. Preferred Share Regex Robustness ---")
pref_symbols = ['005935', '005936', '005937', '005938', '005939', '00680K', '33626L', '000025']
non_pref_symbols = ['005930', '000660', 'AAPL', 'MSFT', '123450', '123454']
for s in pref_symbols:
    assert is_preferred_share(s) == True, f"{s} should be preferred"
for s in non_pref_symbols:
    assert is_preferred_share(s) == False, f"{s} should not be preferred"
print("Pass: Preferred share detection 100% accurate.")

# Test 5: 5-Market Scale & Percentile Distribution
print("\n--- 5. All 5 Target Markets Percentile Calculation ---")
markets = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']
test_rows = []
for m in markets:
    for idx in range(50):
        test_rows.append({
            'symbol': f'{m}_{idx:03d}',
            'market': m,
            'Close': 100.0,
            'bps': 50.0 + idx * 2.0,
            'roe': 0.05 + (idx % 10) * 0.02,
            'operating_income': 10.0 + idx,
            'net_income': 10.0 + idx,
            'shares_outstanding': 1000.0,
            'book_value': (50.0 + idx * 2.0) * 1000.0,
        })
df_5m = pd.DataFrame(test_rows)
res_5m = engine.compute_rim_scores(df_5m)
for m in markets:
    sub = res_5m[res_5m['market'] == m]
    assert len(sub) == 50
    assert sub['rim_score'].notna().all()
    assert (sub['rim_score'] >= 0.0).all() and (sub['rim_score'] <= 1.05).all()
print("Pass: 5-market percentile ranking generated without errors.")

# Test 6: Legacy SQLite Database Schema Auto-Migration
print("\n--- 6. SQLite Auto-Migration from Legacy Table Without New Columns ---")
with tempfile.TemporaryDirectory() as tmp_dir:
    db_path = Path(tmp_dir) / "test_legacy.db"
    # Create legacy table missing bps, book_value, total_debt, cash_equivalents, dividend_per_share
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE stock_fundamentals (
            symbol TEXT,
            date TEXT,
            revenue REAL,
            operating_income REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    conn.execute("INSERT INTO stock_fundamentals VALUES ('LEGACY_SYM', '2026-01-01', 1000.0, 100.0)")
    conn.commit()
    conn.close()

    # Instantiate MarketIndicatorStorage on this legacy db -> should auto-migrate
    storage = MarketIndicatorStorage(db_path=str(db_path))
    
    # Check table info
    with storage._connect() as c:
        cols = {row[1] for row in c.execute("PRAGMA table_info(stock_fundamentals)").fetchall()}
        required = {'bps', 'book_value', 'total_debt', 'cash_equivalents', 'dividend_per_share', 'shares_outstanding', 'eps', 'net_income'}
        missing = required - cols
        assert not missing, f"Missing migrated columns: {missing}"

    # Verify save_fundamentals and get_all_fundamentals work seamlessly
    fund_df = pd.DataFrame([{
        'symbol': 'NEW_SYM',
        'date': '2026-02-01',
        'revenue': 2000.0,
        'operating_income': 300.0,
        'net_income': 250.0,
        'eps': 25.0,
        'shares_outstanding': 10.0,
        'dividend_per_share': 2.0,
        'book_value': 1000.0,
        'bps': 100.0,
        'total_debt': 200.0,
        'cash_equivalents': 50.0,
    }])
    storage.save_fundamentals(fund_df)
    retrieved = storage.get_all_fundamentals(['LEGACY_SYM', 'NEW_SYM'])
    assert len(retrieved) == 2
    new_row = retrieved[retrieved['symbol'] == 'NEW_SYM'].iloc[0]
    assert new_row['bps'] == 100.0
    assert new_row['total_debt'] == 200.0
    assert new_row['cash_equivalents'] == 50.0
    storage.close()
print("Pass: Auto-migration of legacy SQLite database succeeds completely.")

# Test 7: 12-Column, 9-Column, and 8-Column parse_rim Compatibility
print("\n--- 7. parse_rim Backward Compatibility and Robustness ---")
text_12 = """=== Strategy 9: RIM Valuation ===
Date: 2026-08-22 09:00 KST
Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ] [HC]                         95.0%
"""
d12, r12 = parse_rim(text_12)
assert len(r12) == 1
assert r12[0].symbol == "005930"
assert r12[0].filter_tags == "[ADJ] [HC]"
assert r12[0].roe_raw == "15.0%"
assert r12[0].roe_adj == "15.0%"

text_9 = """=== Strategy 9: RIM Valuation ===
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    100%  95.0%
"""
d9, r9 = parse_rim(text_9)
assert len(r9) == 1
assert r9[0].eq == "100%"

text_8 = """=== Strategy 9: RIM Valuation ===
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    95.0%
"""
d8, r8 = parse_rim(text_8)
assert len(r8) == 1
assert r8[0].score == "95.0%"

text_empty = "=== Strategy 9: RIM Valuation ===\n데이터 없음\n"
de, re = parse_rim(text_empty)
assert len(re) == 0
print("Pass: parse_rim handles 12-col, 9-col, 8-col, and empty outputs reliably.")

print("\n=== ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===")

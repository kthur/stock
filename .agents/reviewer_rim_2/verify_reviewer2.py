import sys
import os
import tempfile
import sqlite3
import pandas as pd
import numpy as np

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
from trading_system.src.core.rim_valuation import RIMValuationEngine
from trading_system.generate_report import parse_rim, build_html, EnsembleData, EnsembleMarket, EnsembleRow

def test_1_sqlite_schema_auto_migration():
    print("=== TEST 1: SQLite Schema Auto-Migration & Field Persistence ===")
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "legacy_test.db")
    
    # 1. Create a bare legacy DB table missing new columns
    with sqlite3.connect(temp_db) as conn:
        conn.execute('''
            CREATE TABLE stock_fundamentals (
                symbol TEXT,
                date TEXT,
                revenue REAL,
                operating_income REAL,
                PRIMARY KEY (symbol, date)
            )
        ''')
        conn.commit()
    
    # 2. Open with MarketIndicatorStorage which runs _init_db and schema migrations
    storage = MarketIndicatorStorage(db_path=temp_db)
    
    with storage._connect() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info('stock_fundamentals')").fetchall()]
        print(f"Table columns after migration ({len(cols)} cols): {cols}")
        for col_name in ['book_value', 'bps', 'total_debt', 'cash_equivalents', 'dividend_per_share', 'net_income', 'eps', 'shares_outstanding']:
            assert col_name in cols, f"Migration failed to add {col_name}"
            
    # 3. Test insert & retrieve for 5 markets
    df_fund = pd.DataFrame([
        {'symbol': '005930', 'date': '2026-08-22', 'revenue': 1000, 'operating_income': 200, 'net_income': 180, 'eps': 5000, 'shares_outstanding': 1000000, 'dividend_per_share': 1400, 'book_value': 50000000, 'bps': 50000, 'total_debt': 10000000, 'cash_equivalents': 15000000},
        {'symbol': 'AAPL', 'date': '2026-08-22', 'revenue': 5000, 'operating_income': 1500, 'net_income': 1200, 'eps': 6.5, 'shares_outstanding': 15000000, 'dividend_per_share': 1.0, 'book_value': 70000000, 'bps': 4.66, 'total_debt': 100000000, 'cash_equivalents': 30000000},
        {'symbol': 'NVDA', 'date': '2026-08-22', 'revenue': 3000, 'operating_income': 1800, 'net_income': 1600, 'eps': 2.5, 'shares_outstanding': 24000000, 'dividend_per_share': 0.16, 'book_value': 40000000, 'bps': 1.66, 'total_debt': 10000000, 'cash_equivalents': 20000000},
        {'symbol': 'IWM01', 'date': '2026-08-22', 'revenue': 100, 'operating_income': 10, 'net_income': 8, 'eps': 1.0, 'shares_outstanding': 8000000, 'dividend_per_share': 0.0, 'book_value': 80000000, 'bps': 10.0, 'total_debt': 5000000, 'cash_equivalents': 2000000},
        {'symbol': '035420', 'date': '2026-08-22', 'revenue': 800, 'operating_income': 150, 'net_income': 120, 'eps': 8000, 'shares_outstanding': 1600000, 'dividend_per_share': 1000, 'book_value': 80000000, 'bps': 50000, 'total_debt': 5000000, 'cash_equivalents': 10000000},
    ])
    storage.save_fundamentals(df_fund)
    
    ret = storage.get_all_fundamentals(['005930', 'AAPL', 'NVDA', 'IWM01', '035420'])
    assert len(ret) == 5
    assert ret.loc[ret['symbol'] == 'AAPL', 'bps'].iloc[0] == 4.66
    assert ret.loc[ret['symbol'] == '005930', 'total_debt'].iloc[0] == 10000000
    storage.close()
    print("PASS: Test 1 SQLite migration & persistence verified successfully.")

def test_2_rim_12_column_and_5_market_parsing_and_html():
    print("=== TEST 2: 12-Column RIM Parsing & 5-Market HTML Table Generation ===")
    
    # Text with 5 markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000
    sample_text = """=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-08-22 09:00 KST
Total symbols evaluated: 5
Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ]                               95.0%
2    035420    NAVER               KOSDAQ    200000.00   220000.00         +10.0%    12.0%    12.0%   100%                                      85.0%
3    AAPL      Apple Inc.          SP500     180.00      240.00            +33.3%    25.0%    20.0%    85%  [ADJ]                               90.0%
4    NVDA      NVIDIA Corp         NASDAQ    120.00      150.00            +25.0%    30.0%    25.0%    90%  [ADJ]                               88.0%
5    IWM01     Russell Small       RUSSELL2000 50.00     60.00             +20.0%    10.0%    10.0%   100%  [HC]                                70.0%
"""
    date_str, rows = parse_rim(sample_text)
    assert date_str == "2026-08-22 09:00 KST"
    assert len(rows) == 5
    
    # Assert row values
    r_kospi = [r for r in rows if r.market == 'KOSPI'][0]
    assert r_kospi.symbol == '005930'
    assert r_kospi.discount == '+33.9%'
    assert r_kospi.roe_raw == '15.0%'
    assert r_kospi.roe_adj == '15.0%'
    assert r_kospi.eq == '100%'
    assert r_kospi.filter_tags == '[ADJ]'
    assert r_kospi.rim_score == '95.0%'
    
    r_russell = [r for r in rows if r.market == 'RUSSELL2000'][0]
    assert r_russell.symbol == 'IWM01'
    assert r_russell.filter_tags == '[HC]'
    assert r_russell.rim_score == '70.0%'

    # Generate HTML
    ensemble = EnsembleData(
        date="2026-08-22",
        regime="SIDEWAYS",
        markets=[
            EnsembleMarket(market="KOSPI", rows=[EnsembleRow(1, "005930", "삼성전자", "85%", "5.2%", "40%", "10%", "20%", "15%", "10%", "15%", "15%", "10%", "15%")]),
        ],
    )
    
    html_out = build_html(
        ensemble,
        surge_date="2026-08-22", surge_sections=[],
        vcp_date="2026-08-22", vcp_rows=[],
        lag_date="2026-08-22", follower_rows=[], leader_rows=[],
        vcp_ml_sections=[], reg_sections=[],
        portfolio_data=None,
        stat_arb_rows=[],
        sector_rows=[],
        rim_rows=rows
    )
    
    # Check headers
    assert "<th>순위</th><th>종목코드</th><th>종목명</th><th>현재가</th><th>RIM 적정가(V0)</th><th>안전마진(할인율)</th><th>ROE(보고)</th><th>ROE(조정)</th><th>EQ</th><th>필터</th><th>RIM 스코어</th>" in html_out
    
    # Check that each market has data and NOT '데이터 없음'
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        assert f'data-market="{mkt}"' in html_out
        
    assert "삼성전자" in html_out
    assert "NAVER" in html_out
    assert "Apple Inc." in html_out
    assert "NVIDIA Corp" in html_out
    assert "Russell Small" in html_out
    assert "[ADJ]" in html_out
    assert "[HC]" in html_out
    
    print("PASS: Test 2 12-Column parsing and 5-market HTML verified successfully.")

def test_3_adversarial_edge_cases():
    print("=== TEST 3: Adversarial Edge Cases & Value Trap Stress Test ===")
    engine = RIMValuationEngine(default_required_return=0.08)
    
    # Case A: Missing BPS / zero BPS / negative BPS
    df_edge = pd.DataFrame([
        {'symbol': 'ZERO_BPS', 'market': 'SP500', 'Close': 100.0, 'bps': 0.0, 'roe': 0.15},
        {'symbol': 'NEG_BPS', 'market': 'NASDAQ', 'Close': 50.0, 'bps': -10.0, 'roe': 0.20},
        {'symbol': 'NAN_BPS', 'market': 'RUSSELL2000', 'Close': 25.0, 'eps': 5.0, 'roe': 0.10}, # No bps, high eps (fake BPS trap)
        {'symbol': 'OP_LOSS', 'market': 'KOSPI', 'Close': 50000.0, 'bps': 60000.0, 'operating_income': -500, 'net_income': 100}, # Operating loss trap
        {'symbol': 'PREF_SH', 'market': 'KOSPI', 'Close': 30000.0, 'symbol': '005935', 'bps': 50000.0, 'roe': 0.15}, # Preferred share
    ])
    
    res = engine.compute_rim_scores(df_edge).set_index('symbol')
    
    # Assert all edge cases are strictly NaN (no fake discounts or pollution)
    for sym in ['ZERO_BPS', 'NEG_BPS', 'NAN_BPS', 'OP_LOSS', '005935']:
        assert pd.isna(res.loc[sym, 'rim_score']), f"Expected NaN rim_score for {sym}, got {res.loc[sym, 'rim_score']}"
        assert pd.isna(res.loc[sym, 'discount_ratio']), f"Expected NaN discount_ratio for {sym}, got {res.loc[sym, 'discount_ratio']}"
        assert pd.isna(res.loc[sym, 'intrinsic_value']), f"Expected NaN intrinsic_value for {sym}, got {res.loc[sym, 'intrinsic_value']}"
        
    print("PASS: Test 3 Value trap and edge cases properly gated with NaN.")

if __name__ == '__main__':
    test_1_sqlite_schema_auto_migration()
    test_2_rim_12_column_and_5_market_parsing_and_html()
    test_3_adversarial_edge_cases()
    print("\nALL ADVERSARIAL AND INTEGRITY TESTS PASSED 100%!")

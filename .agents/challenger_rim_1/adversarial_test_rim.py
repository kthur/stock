"""
adversarial_test_rim.py
Comprehensive Empirical Adversarial Stress Test Suite for Strategy #9 RIM Valuation.
"""
import sys
import os
import numpy as np
import pandas as pd
import pytest

# Ensure repo root and trading_system are on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
trading_system_dir = os.path.join(repo_root, "trading_system")
if trading_system_dir not in sys.path:
    sys.path.insert(0, trading_system_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.core.rim_valuation import (
    RIMValuationEngine,
    ABSOLUTE_ROE_CAP,
    EXTREME_ROE_THRESHOLD,
    EXTREME_EQ_THRESHOLD,
    HOLDING_CO_DISCOUNT,
    EARNINGS_QUALITY_MIN_RATIO,
    is_preferred_share,
    _is_holding_company
)
from generate_report import parse_rim, build_html, EnsembleData, EnsembleMarket, EnsembleRow

def run_all_adversarial_tests():
    print("======================================================================")
    print("STARTING RIM VALUATION EMPIRICAL ADVERSARIAL STRESS TEST SUITE")
    print("======================================================================")

    engine = RIMValuationEngine(default_required_return=0.08, decay_rate=0.10, retention_ratio=0.6)

    # --------------------------------------------------------------------------
    # TEST 1: Empty, Single-Row, All-NaN, and Extreme Invalids
    # --------------------------------------------------------------------------
    print("\n[Test 1] Testing Empty, Single-Row, and All-NaN DataFrames...")
    
    # 1.1 None and empty
    res_none = engine.compute_rim_scores(None)
    assert isinstance(res_none, pd.DataFrame) and res_none.empty, "Failed on None input"
    
    res_empty = engine.compute_rim_scores(pd.DataFrame())
    assert isinstance(res_empty, pd.DataFrame) and res_empty.empty, "Failed on empty DataFrame"

    # 1.2 All-NaN DataFrame
    df_all_nan = pd.DataFrame([{
        'symbol': np.nan, 'market': np.nan, 'Close': np.nan, 'bps': np.nan,
        'roe': np.nan, 'operating_income': np.nan, 'net_income': np.nan,
        'book_value': np.nan, 'shares_outstanding': np.nan, 'total_debt': np.nan,
        'cash_equivalents': np.nan
    }])
    res_nan = engine.compute_rim_scores(df_all_nan)
    assert len(res_nan) == 1
    assert np.isnan(res_nan.iloc[0]['rim_score'])
    assert np.isnan(res_nan.iloc[0]['intrinsic_value'])
    print("  -> Passed empty and all-NaN tests.")

    # 1.3 Infinite values in all columns
    df_inf = pd.DataFrame([{
        'symbol': 'INF_SYM', 'market': 'SP500', 'Close': np.inf, 'bps': np.inf,
        'roe': np.inf, 'operating_income': np.inf, 'net_income': -np.inf,
        'book_value': -np.inf, 'shares_outstanding': np.inf, 'total_debt': np.inf,
        'cash_equivalents': -np.inf
    }])
    res_inf = engine.compute_rim_scores(df_inf)
    assert len(res_inf) == 1
    assert np.isnan(res_inf.iloc[0]['rim_score'])
    assert np.isnan(res_inf.iloc[0]['intrinsic_value'])
    print("  -> Passed infinite values test.")

    # 1.4 Missing all optional columns
    df_minimal = pd.DataFrame([{'Close': 50.0}])
    res_minimal = engine.compute_rim_scores(df_minimal)
    assert len(res_minimal) == 1
    assert res_minimal.iloc[0]['symbol'] == 'SYM_0'
    assert res_minimal.iloc[0]['market'] == 'KOSPI'
    assert np.isnan(res_minimal.iloc[0]['rim_score'])
    print("  -> Passed minimal columns test.")

    # --------------------------------------------------------------------------
    # TEST 2: Missing Column Permutations (shares_outstanding, book_value, Close, etc.)
    # --------------------------------------------------------------------------
    print("\n[Test 2] Testing Missing Column Permutations...")
    
    # 2.1 Missing shares_outstanding when book_value is present
    df_no_shares = pd.DataFrame([
        {'symbol': 'US_NO_SHARES', 'market': 'NASDAQ', 'Close': 100.0, 'book_value': 1_000_000_000.0, 'roe': 0.15}
    ])
    res_no_shares = engine.compute_rim_scores(df_no_shares)
    assert np.isnan(res_no_shares.iloc[0]['bps']), "BPS should be NaN without shares_outstanding"
    assert np.isnan(res_no_shares.iloc[0]['rim_score']), "rim_score should be NaN without valid BPS"

    # 2.2 Missing book_value when shares_outstanding is present
    df_no_bv = pd.DataFrame([
        {'symbol': 'US_NO_BV', 'market': 'RUSSELL2000', 'Close': 20.0, 'shares_outstanding': 10_000_000.0, 'roe': 0.10}
    ])
    res_no_bv = engine.compute_rim_scores(df_no_bv)
    assert np.isnan(res_no_bv.iloc[0]['bps'])
    assert np.isnan(res_no_bv.iloc[0]['rim_score'])

    # 2.3 Zero shares outstanding / zero book value
    df_zero = pd.DataFrame([
        {'symbol': 'ZERO_SHARES', 'market': 'SP500', 'Close': 10.0, 'book_value': 100.0, 'shares_outstanding': 0.0},
        {'symbol': 'ZERO_BV', 'market': 'SP500', 'Close': 10.0, 'book_value': 0.0, 'shares_outstanding': 100.0},
        {'symbol': 'NEG_BV', 'market': 'SP500', 'Close': 10.0, 'book_value': -500.0, 'shares_outstanding': 100.0},
        {'symbol': 'NEG_BPS', 'market': 'SP500', 'Close': 10.0, 'bps': -50.0}
    ])
    res_zero = engine.compute_rim_scores(df_zero)
    for idx, row in res_zero.iterrows():
        assert np.isnan(row['bps']), f"Row {row['symbol']} should have NaN BPS"
        assert np.isnan(row['rim_score']), f"Row {row['symbol']} should have NaN rim_score"
    print("  -> Passed missing column permutations and zero/negative book value tests.")

    # --------------------------------------------------------------------------
    # TEST 3: Cyclical / Deep-Value Low-P/E Fake BPS Gating
    # --------------------------------------------------------------------------
    print("\n[Test 3] Testing Cyclical Deep-Value Stocks Without BPS (Fake BPS Fabrication Check)...")
    
    # Stocks with high EPS / low P/E, but no book value / BPS
    df_cyclical = pd.DataFrame([
        {'symbol': 'CYCLIC_1', 'market': 'KOSPI', 'Close': 10000.0, 'eps': 4000.0, 'roe': 0.25, 'operating_income': 4000.0, 'net_income': 4000.0},
        {'symbol': 'CYCLIC_2', 'market': 'KOSDAQ', 'Close': 5000.0, 'eps': 2500.0, 'roe': 0.30, 'operating_income': 2500.0, 'net_income': 2500.0},
        {'symbol': 'VALID_VAL', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 15000.0, 'roe': 0.12, 'operating_income': 1800.0, 'net_income': 1800.0}
    ])
    res_cyclical = engine.compute_rim_scores(df_cyclical).set_index('symbol')
    
    # CYCLIC_1 and CYCLIC_2 must have NaN BPS, NaN intrinsic_value, NaN discount_ratio, NaN rim_score
    assert np.isnan(res_cyclical.loc['CYCLIC_1', 'bps']), "CYCLIC_1 fabricated BPS!"
    assert np.isnan(res_cyclical.loc['CYCLIC_1', 'intrinsic_value']), "CYCLIC_1 fabricated intrinsic value!"
    assert np.isnan(res_cyclical.loc['CYCLIC_1', 'discount_ratio']), "CYCLIC_1 fabricated discount ratio!"
    assert np.isnan(res_cyclical.loc['CYCLIC_1', 'rim_score']), "CYCLIC_1 fabricated rim_score!"
    
    assert np.isnan(res_cyclical.loc['CYCLIC_2', 'bps']), "CYCLIC_2 fabricated BPS!"
    assert np.isnan(res_cyclical.loc['CYCLIC_2', 'rim_score']), "CYCLIC_2 fabricated rim_score!"

    # VALID_VAL should be valid and have positive margin of safety
    assert res_cyclical.loc['VALID_VAL', 'bps'] == 15000.0
    assert res_cyclical.loc['VALID_VAL', 'intrinsic_value'] > 15000.0
    assert res_cyclical.loc['VALID_VAL', 'discount_ratio'] > 0.50
    assert not np.isnan(res_cyclical.loc['VALID_VAL', 'rim_score'])
    print("  -> Confirmed: NO fake BPS is fabricated for cyclical low-P/E stocks; discount and score are strictly NaN.")

    # --------------------------------------------------------------------------
    # TEST 4: Earnings Quality (EQ) & Nonrecurring Income Spikes & Operating Loss
    # --------------------------------------------------------------------------
    print("\n[Test 4] Testing Earnings Quality, Nonrecurring Spikes, and Operating Losses...")

    df_eq = pd.DataFrame([
        # Case A: Operating loss + positive net income (one-off gain like land disposal)
        {
            'symbol': 'DISPOSAL_GAIN', 'market': 'KOSPI', 'Close': 20000.0, 'bps': 25000.0, 'roe': 0.35,
            'operating_income': -500.0, 'net_income': 8750.0, 'book_value': 25000.0
        },
        # Case B: Operating loss + net loss
        {
            'symbol': 'CHRONIC_LOSS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 12000.0, 'roe': -0.10,
            'operating_income': -1200.0, 'net_income': -1200.0, 'book_value': 12000.0
        },
        # Case C: Low EQ (operating income is 20% of net income)
        {
            'symbol': 'LOW_EQ', 'market': 'KOSPI', 'Close': 30000.0, 'bps': 30000.0, 'roe': 0.15,
            'operating_income': 900.0, 'net_income': 4500.0, 'book_value': 30000.0
        },
        # Case D: Extreme ROE Spike (> 20%) with low EQ (< 0.4) -> Normalized via operating income / book_value
        {
            'symbol': 'EXTREME_SPIKE', 'market': 'KOSPI', 'Close': 5000.0, 'bps': 5000.0, 'roe': 0.50,
            'operating_income': 250.0, 'net_income': 2500.0, 'book_value': 5000.0
        },
        # Case E: High ROE (> 25%) with perfect EQ (1.0) -> Capped at ABSOLUTE_ROE_CAP (25%)
        {
            'symbol': 'STAR_GROWTH', 'market': 'KOSPI', 'Close': 50000.0, 'bps': 30000.0, 'roe': 0.45,
            'operating_income': 13500.0, 'net_income': 13500.0, 'book_value': 30000.0
        }
    ])
    res_eq = engine.compute_rim_scores(df_eq).set_index('symbol')

    # Verify DISPOSAL_GAIN: EQ=0, filter=LOW_EARNINGS_QUALITY, score=NaN
    assert res_eq.loc['DISPOSAL_GAIN', 'earnings_quality'] == 0.0
    assert res_eq.loc['DISPOSAL_GAIN', 'rim_filter_reason'] == 'LOW_EARNINGS_QUALITY'
    assert np.isnan(res_eq.loc['DISPOSAL_GAIN', 'rim_score'])
    assert np.isnan(res_eq.loc['DISPOSAL_GAIN', 'intrinsic_value'])

    # Verify CHRONIC_LOSS: filter=OPERATING_LOSS, score=NaN
    assert res_eq.loc['CHRONIC_LOSS', 'rim_filter_reason'] == 'OPERATING_LOSS'
    assert np.isnan(res_eq.loc['CHRONIC_LOSS', 'rim_score'])

    # Verify LOW_EQ: EQ=0.20 (< 0.5), filter=QUALITY_ADJUSTED, ROE decayed from 0.15 to 0.03
    assert abs(res_eq.loc['LOW_EQ', 'earnings_quality'] - 0.20) < 1e-6
    assert 'QUALITY_ADJUSTED' in res_eq.loc['LOW_EQ', 'rim_filter_reason']
    assert abs(res_eq.loc['LOW_EQ', 'roe'] - 0.03) < 1e-6

    # Verify EXTREME_SPIKE: ROE was 50%, normalized to op_income / book_value = 250/5000 = 0.05 (5%)
    assert res_eq.loc['EXTREME_SPIKE', 'roe_normalized'] == True
    assert 'ROE_NORMALIZED' in res_eq.loc['EXTREME_SPIKE', 'rim_filter_reason']
    assert abs(res_eq.loc['EXTREME_SPIKE', 'roe'] - 0.05) < 1e-6

    # Verify STAR_GROWTH: ROE was 45%, capped to 25%
    assert res_eq.loc['STAR_GROWTH', 'roe_normalized'] == True
    assert abs(res_eq.loc['STAR_GROWTH', 'roe'] - ABSOLUTE_ROE_CAP) < 1e-6

    print("  -> Passed all Earnings Quality, nonrecurring spike, and operating loss tests.")

    # --------------------------------------------------------------------------
    # TEST 5: Holding Company Detection & SOTP Discount Calculations
    # --------------------------------------------------------------------------
    print("\n[Test 5] Testing Holding Company Identification & SOTP Discount Calculations...")

    # Test names and sector codes
    assert _is_holding_company("SK스퀘어지주", None) is True
    assert _is_holding_company("카카오홀딩스", None) is True
    assert _is_holding_company("Berkshire Hathaway Holdings", None) is True
    assert _is_holding_company("HD현대", "6020") is True  # Identified via sector code 6020
    assert _is_holding_company("HD Holdings", None) is True
    assert _is_holding_company("삼성물산", "6020") is True
    assert _is_holding_company("미국금융지주", "20202020") is True
    assert _is_holding_company("현대자동차", "Automobiles") is False

    df_hc = pd.DataFrame([
        # Holding company with large net debt (total_debt 50B, cash 10B -> net debt 40B, 10M shares -> 4,000 KRW/sh)
        {
            'symbol': 'HOLDING_A', 'market': 'KOSPI', 'name': 'ABC홀딩스', 'Close': 8000.0,
            'bps': 10000.0, 'roe': 0.12, 'shares_outstanding': 10_000_000.0,
            'total_debt': 50_000_000_000.0, 'cash_equivalents': 10_000_000_000.0,
            'book_value': 100_000_000_000.0, 'operating_income': 12_000_000_000.0, 'net_income': 12_000_000_000.0
        },
        # Non-holding operating company with identical fundamentals
        {
            'symbol': 'OP_CO_A', 'market': 'KOSPI', 'name': 'ABC제조', 'Close': 8000.0,
            'bps': 10000.0, 'roe': 0.12, 'shares_outstanding': 10_000_000.0,
            'total_debt': 50_000_000_000.0, 'cash_equivalents': 10_000_000_000.0,
            'book_value': 100_000_000_000.0, 'operating_income': 12_000_000_000.0, 'net_income': 12_000_000_000.0
        },
        # Holding company with net cash (cash > debt)
        {
            'symbol': 'HOLDING_CASH', 'market': 'KOSPI', 'name': '현금부자지주', 'Close': 8000.0,
            'bps': 10000.0, 'roe': 0.12, 'shares_outstanding': 10_000_000.0,
            'total_debt': 10_000_000_000.0, 'cash_equivalents': 30_000_000_000.0,
            'book_value': 100_000_000_000.0, 'operating_income': 12_000_000_000.0, 'net_income': 12_000_000_000.0
        },
        # Holding company with massive debt (> 80% BPS) -> BPS floor of 30% BPS
        {
            'symbol': 'HOLDING_DEBT_FLOOR', 'market': 'KOSPI', 'name': '과다부채홀딩스', 'Close': 2000.0,
            'bps': 10000.0, 'roe': 0.10, 'shares_outstanding': 10_000_000.0,
            'total_debt': 90_000_000_000.0, 'cash_equivalents': 0.0,
            'book_value': 100_000_000_000.0, 'operating_income': 10_000_000_000.0, 'net_income': 10_000_000_000.0
        }
    ])
    res_hc = engine.compute_rim_scores(df_hc).set_index('symbol')

    # Check HOLDING_A:
    assert res_hc.loc['HOLDING_A', 'holding_co_flag'] == True
    assert res_hc.loc['OP_CO_A', 'holding_co_flag'] == False
    
    # Net debt per share = (50B - 10B) / 10M = 4000 KRW
    # bps_adjusted = max(10000 - 4000, 3000) = 6000 KRW
    assert abs(res_hc.loc['HOLDING_A', 'bps_adjusted'] - 6000.0) < 1.0
    assert abs(res_hc.loc['OP_CO_A', 'bps_adjusted'] - 10000.0) < 1.0

    # Intrinsic value of holding company must be substantially lower than operating company
    iv_hc = res_hc.loc['HOLDING_A', 'intrinsic_value']
    iv_op = res_hc.loc['OP_CO_A', 'intrinsic_value']
    assert iv_hc < iv_op * 0.70, f"Holding company discount insufficiently applied: HC={iv_hc}, OP={iv_op}"

    # Check HOLDING_CASH: net debt is clipped to 0 (no bonus BPS)
    assert abs(res_hc.loc['HOLDING_CASH', 'net_debt_per_share'] - 0.0) < 1e-6
    assert abs(res_hc.loc['HOLDING_CASH', 'bps_adjusted'] - 10000.0) < 1.0

    # Check HOLDING_DEBT_FLOOR: debt is 9,000 KRW/sh -> 10000 - 9000 = 1000, but floor is 30% (3,000 KRW)
    assert abs(res_hc.loc['HOLDING_DEBT_FLOOR', 'bps_adjusted'] - 3000.0) < 1.0

    print("  -> Passed all Holding Company SOTP and Net Debt adjustment tests.")

    # --------------------------------------------------------------------------
    # TEST 6: Preferred Shares & Multi-Market Ranking
    # --------------------------------------------------------------------------
    print("\n[Test 6] Testing Preferred Shares and 5-Market Percentile Scoring...")

    df_multi = pd.DataFrame([
        # KOSPI
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 55000.0, 'roe': 0.14},
        {'symbol': '005935', 'market': 'KOSPI', 'Close': 60000.0, 'bps': 55000.0, 'roe': 0.14}, # Preferred
        {'symbol': '000660', 'market': 'KOSPI', 'Close': 130000.0, 'bps': 90000.0, 'roe': 0.10},
        # KOSDAQ
        {'symbol': '035420', 'market': 'KOSDAQ', 'Close': 200000.0, 'bps': 180000.0, 'roe': 0.15},
        {'symbol': '035720', 'market': 'KOSDAQ', 'Close': 50000.0, 'bps': 30000.0, 'roe': 0.06},
        # SP500
        {'symbol': 'AAPL', 'market': 'SP500', 'Close': 180.0, 'bps': 50.0, 'roe': 0.25},
        {'symbol': 'MSFT', 'market': 'SP500', 'Close': 400.0, 'bps': 120.0, 'roe': 0.22},
        # NASDAQ
        {'symbol': 'NVDA', 'market': 'NASDAQ', 'Close': 120.0, 'bps': 25.0, 'roe': 0.25},
        {'symbol': 'AMD', 'market': 'NASDAQ', 'Close': 150.0, 'bps': 35.0, 'roe': 0.12},
        # RUSSELL2000
        {'symbol': 'RUT_A', 'market': 'RUSSELL2000', 'Close': 20.0, 'bps': 25.0, 'roe': 0.11},
        {'symbol': 'RUT_B', 'market': 'RUSSELL2000', 'Close': 30.0, 'bps': 15.0, 'roe': 0.05},
    ])
    res_multi = engine.compute_rim_scores(df_multi).set_index('symbol')

    # Check preferred share 005935
    assert res_multi.loc['005935', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert np.isnan(res_multi.loc['005935', 'rim_score'])
    assert np.isnan(res_multi.loc['005935', 'intrinsic_value'])

    # Check all 5 markets have non-empty valid scores
    for mkt in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
        mkt_rows = res_multi[res_multi['market'] == mkt]
        valid_scores = mkt_rows['rim_score'].dropna()
        assert len(valid_scores) > 0, f"No valid RIM scores for market {mkt}"
        assert (valid_scores >= 0.0).all() and (valid_scores <= 1.0).all()

    print("  -> Passed preferred share exclusion and 5-market scoring tests.")

    # --------------------------------------------------------------------------
    # TEST 7: Countercyclical ERP & Stress Conditions
    # --------------------------------------------------------------------------
    print("\n[Test 7] Testing Dynamic Countercyclical Required Return (ERP)...")

    # Calm market
    r_calm_us = engine.derive_required_return('SP500', us10y_yield=4.0, vix_val=15.0, credit_spread=3.0)
    r_calm_kr = engine.derive_required_return('KOSPI', us10y_yield=4.0, vix_val=15.0, credit_spread=3.0)
    assert abs(r_calm_us - (0.04 + 0.05)) < 1e-6
    assert abs(r_calm_kr - (0.04 + 0.06)) < 1e-6

    # Crisis market: VIX = 45, Credit Spread = 7.0%, 10Y Yield = 5.0%
    r_crisis = engine.derive_required_return('KOSPI', us10y_yield=5.0, vix_val=45.0, credit_spread=7.0)
    # base_rf = 0.05, base_erp = 0.06, vix_expansion = min((45-20)*0.0025, 0.04) = 0.04, spread_expansion = min((7-4)*0.01, 0.03) = 0.03
    # dynamic_erp = 0.06 + 0.04 + 0.03 = 0.13
    # dynamic_re = 0.05 + 0.13 = 0.18 (clipped at 0.18)
    assert abs(r_crisis - 0.18) < 1e-6

    # NaN / Inf inputs
    r_nan = engine.derive_required_return('KOSPI', us10y_yield=np.nan, vix_val=np.inf, credit_spread=-np.inf)
    assert 0.06 <= r_nan <= 0.18

    print("  -> Passed countercyclical dynamic ERP tests.")

    # --------------------------------------------------------------------------
    # TEST 8: Text Output & 12-Column HTML Parser Integration
    # --------------------------------------------------------------------------
    print("\n[Test 8] Testing Text Reporting and 12-Column HTML Parser...")

    sample_12col_txt = """=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-08-22 09:00 KST
Total symbols evaluated: 3
Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ]                               95.0%
2    016880    웅진홀딩스          KOSPI     2000.00     2500.00           +25.0%    40.0%    25.0%    40%  [ADJ] [HC]                          80.0%
3    CYCLIC    사이클기업          KOSPI     10000.00    nan                 nan%     N/A      N/A    N/A                                       nan%
"""
    date_str, rows = parse_rim(sample_12col_txt)
    assert len(rows) == 3
    assert rows[0].symbol == "005930"
    assert rows[0].filter_tags == "[ADJ]"
    assert rows[1].symbol == "016880"
    assert rows[1].filter_tags == "[ADJ] [HC]"
    assert rows[2].symbol == "CYCLIC"
    assert rows[2].intrinsic_value == "nan"

    print("  -> Passed 12-column parser and reporting integration test.")

    print("\n======================================================================")
    print("ALL EMPIRICAL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    run_all_adversarial_tests()

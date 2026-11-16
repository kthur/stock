#!/usr/bin/env python3
"""
scripts/verify_market_data_integrity.py

Automated diagnostic verification script for macro indicators, 5-market OHLCV,
order flow/fundamentals, database integrity, rate limiting, and zero synthetic data invariance.
"""

import sys
import os
import json
import sqlite3
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

# Add repository root to path
sys.path.insert(0, os.path.abspath('.'))

from src.data_layer.global_market import GlobalMarketClient, GLOBAL_INDICES, MACRO_COMMODITIES, FX_PAIRS
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.data_validator import DataValidator
from src.persistence.database import StockPriceDB
from src.config import TradingConfig
from src.utils.rate_limiter import get_global_rate_limiter

KST = timezone(timedelta(hours=9))

def run_diagnostics() -> bool:
    print("=" * 80)
    print("      5-MARKET & MACRO DATA COLLECTION INTEGRITY DIAGNOSTIC SUITE      ")
    print("=" * 80)
    all_passed = True
    diagnostic_results = []

    # ─────────────────────────────────────────────────────────────────────────────
    # 1. Macro Indicators Collection & Freshness Check (R1)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 1/6] Verifying Macro Indicators Collection & Storage...")
    storage = MarketIndicatorStorage()
    db_path = storage.db_path
    print(f"  Connected Storage DB: {db_path}")

    required_macro = {
        '^VIX': 'VIX Volatility Index',
        '^TNX': 'US 10Y Treasury Yield',
        'USDKRW=X': 'USD/KRW FX Rate',
        'CL=F': 'WTI Crude Oil Futures',
        'GLD': 'Gold ETF (GLD)',
        'GC=F': 'Gold Futures (GC=F)',
        'DX-Y.NYB': 'US Dollar Index (DXY)',
        '^SOX': 'PHLX Semiconductor Index',
        '^GSPC': 'S&P 500 Index',
        '^IXIC': 'NASDAQ Composite Index',
        '^KS11': 'KOSPI Index',
        '^KQ11': 'KOSDAQ Index',
    }

    latest_indicators = storage.get_latest_global_indicators()
    macro_table = []
    macro_failures = []

    for sym, desc in required_macro.items():
        val = latest_indicators.get(sym)
        bounds = storage.INDICATOR_VALUE_BOUNDS.get(sym, storage._INDICATOR_DEFAULT_BOUNDS)
        ok = (val is not None) and (bounds[0] <= val <= bounds[1])
        status = "PASS" if ok else "FAIL"
        if not ok:
            macro_failures.append(sym)
        macro_table.append((sym, desc, f"{val:.4f}" if val is not None else "MISSING", f"[{bounds[0]}, {bounds[1]}]", status))

    print(f"  {'Symbol':<12} {'Description':<28} {'Latest Price':<14} {'Plausible Bounds':<18} {'Status'}")
    print("  " + "-" * 76)
    for r in macro_table:
        print(f"  {r[0]:<12} {r[1]:<28} {r[2]:<14} {r[3]:<18} {r[4]}")

    if not macro_failures:
        print(f"  ==> Macro Indicators Verification: ALL {len(required_macro)} PASSED")
        diagnostic_results.append(("Macro Indicators", True, f"{len(required_macro)}/12 indicators verified in bounds"))
    else:
        print(f"  ==> Macro Indicators Verification: FAILED for {macro_failures}")
        diagnostic_results.append(("Macro Indicators", False, f"Failed: {macro_failures}"))
        all_passed = False

    # ─────────────────────────────────────────────────────────────────────────────
    # 2. Database Integrity Check: global_indicators (R1, R3)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 2/6] Checking market_indicators.db Integrity...")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM global_indicators WHERE price IS NULL")
        null_prices = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM global_indicators WHERE price <= 0")
        le_zero_prices = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT symbol), MAX(date) FROM global_indicators")
        total_gi, uniq_gi_syms, max_gi_date = cur.fetchone()

    gi_ok = (null_prices == 0) and (le_zero_prices == 0) and (total_gi > 0)
    print(f"  Total records: {total_gi:,} | Unique Symbols: {uniq_gi_syms} | Latest Date: {max_gi_date}")
    print(f"  NULL Price count: {null_prices} | Price <= 0 count: {le_zero_prices} -> {'PASS' if gi_ok else 'FAIL'}")
    diagnostic_results.append(("Indicator DB Integrity", gi_ok, f"{total_gi} rows, 0 nulls, 0 non-positive"))
    if not gi_ok:
        all_passed = False

    # ─────────────────────────────────────────────────────────────────────────────
    # 3. 5 Major Markets & Stock Universe Verification (R2)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 3/6] Verifying 5 Major Markets & Universe Coverage...")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT market, COUNT(*) FROM stock_universe GROUP BY market")
        univ_breakdown = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM post_market_rankings")
        rankings_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM post_market_rankings WHERE composite_score IS NULL OR rank IS NULL")
        bad_rankings = cur.fetchone()[0]

    expected_markets = ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500', 'NASDAQ', 'RUSSELL2000']
    missing_markets = [m for m in expected_markets if m not in univ_breakdown]
    
    print("  Stock Universe Breakdown by Market:")
    for m, cnt in univ_breakdown.items():
        print(f"    - {m:<15}: {cnt:,} symbols")
    print(f"  Post-Market Rankings Evaluated Symbols: {rankings_count:,} (Bad/Null rows: {bad_rankings})")

    univ_ok = (len(missing_markets) == 0) and (rankings_count == 3379) and (bad_rankings == 0)
    diagnostic_results.append(("Universe & 5 Markets", univ_ok, f"Markets: {len(univ_breakdown)}, Rankings: {rankings_count} (target 3379)"))
    if not univ_ok:
        all_passed = False
        print(f"  ==> Universe Verification FAILED: missing {missing_markets} or rankings != 3379")
    else:
        print(f"  ==> Universe & 5-Market Rankings Verification: PASSED (3,379 symbols verified)")

    # ─────────────────────────────────────────────────────────────────────────────
    # 4. Stock Prices DB & Strict OHLC Integrity (R2, R3)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 4/6] Checking stock_prices.db & Fundamentals Integrity...")
    price_db = StockPriceDB()
    price_db_path = str(price_db.db_path)
    print(f"  Connected Price DB: {price_db_path}")

    with sqlite3.connect(price_db_path) as pconn:
        pcur = pconn.cursor()
        pcur.execute("SELECT COUNT(*), COUNT(DISTINCT symbol), MIN(date), MAX(date) FROM stock_prices")
        tot_prices, uniq_price_syms, min_pdate, max_pdate = pcur.fetchone()
        
        # Strict check on corrupted equity prices:
        # Open, High, Low, Close must be positive, non-null, and satisfy High >= Low, High >= Open/Close, Low <= Open/Close
        pcur.execute("""
            SELECT COUNT(*) FROM stock_prices 
            WHERE (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 
                   OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
                   OR high < open OR high < close OR low > open OR low > close OR high < low) 
            AND symbol NOT IN ('CL=F', '^IRX', '^TNX', '^FVX', '2YY=X')
            AND symbol NOT LIKE '^%' AND symbol NOT LIKE '%=F' AND symbol NOT LIKE '%=X'
        """)
        bad_equity_prices = pcur.fetchone()[0]

        # Verify authentic crisis negative pricing is preserved for CL=F on 2020-04-20
        pcur.execute("""
            SELECT COUNT(*) FROM stock_prices 
            WHERE symbol = 'CL=F' AND date = '2020-04-20' AND close < 0
        """)
        cl_negative_preserved = (pcur.fetchone()[0] == 1)

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT symbol), MIN(date), MAX(date) FROM stock_fundamentals")
        tot_fund, uniq_fund_syms, min_fdate, max_fdate = cur.fetchone()

    price_ok = (bad_equity_prices == 0) and (tot_prices > 10_000_000) and cl_negative_preserved
    fund_ok = (uniq_fund_syms >= 3200) and (tot_fund > 10_000)

    print(f"  Stock Prices Records: {tot_prices:,} across {uniq_price_syms:,} symbols ({min_pdate} ~ {max_pdate})")
    print(f"  Strict Corrupted Equity Price Rows: {bad_equity_prices} -> {'PASS' if bad_equity_prices == 0 else 'FAIL'}")
    print(f"  Crisis Negative Commodity Preserved: {cl_negative_preserved} -> {'PASS' if cl_negative_preserved else 'FAIL'}")
    print(f"  Fundamental Records: {tot_fund:,} across {uniq_fund_syms:,} symbols ({min_fdate} ~ {max_fdate}) -> {'PASS' if fund_ok else 'FAIL'}")

    diagnostic_results.append(("Price DB Strict OHLC", price_ok, f"{tot_prices:,} rows, 0 corrupted equity rows, CL=F preserved"))
    diagnostic_results.append(("Fundamental DB Coverage", fund_ok, f"{uniq_fund_syms:,} symbols covered (>= 3,200)"))
    if not (price_ok and fund_ok):
        all_passed = False

    # ─────────────────────────────────────────────────────────────────────────────
    # 5. Rate Limiting & Resilience Architecture Verification (R3)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 5/6] Verifying Rate Limiting & Resilience Architecture...")
    rate_limiter_ok = False
    try:
        limiter = get_global_rate_limiter()
        # Verify rate limiter can execute without exception
        limiter.wait()
        rate_limiter_ok = True
        print("  Token-Bucket Global Rate Limiter: Active and functional -> PASS")
    except Exception as e:
        print(f"  Token-Bucket Global Rate Limiter check failed: {e} -> FAIL")

    # Verify DataValidator preserves physical negative commodity data while cleaning equities
    import pandas as pd
    import tempfile
    val_cl_df = pd.DataFrame({
        'Open': [17.73, -14.0], 'High': [17.85, 13.86],
        'Low': [-40.32, -16.74], 'Close': [-37.63, 10.01], 'Volume': [247947, 2288230]
    }, index=pd.date_range('2020-04-20', periods=2))
    cleaned_cl = DataValidator.validate_and_clean_price_series(val_cl_df, symbol='CL=F')
    validator_cl_ok = (
        cleaned_cl['Close'].iloc[0] == -37.63
        and cleaned_cl['Low'].iloc[0] == -40.32
        and cleaned_cl['High'].iloc[0] >= cleaned_cl['Open'].iloc[0]
        and cleaned_cl['Low'].iloc[0] <= cleaned_cl['Open'].iloc[0]
    )

    val_eq_df = pd.DataFrame({
        'Open': [0.0, 100.0, 102.0, 101.0, 103.0],
        'High': [0.0, 105.0, 104.0, 103.0, 106.0],
        'Low': [0.0, 99.0, 100.0, 98.0, 101.0],
        'Close': [100.0, 102.0, 101.0, 103.0, 105.0],
        'Volume': [0, 1000, 1100, 900, 1200]
    }, index=pd.date_range('2026-01-01', periods=5))
    cleaned_eq = DataValidator.validate_and_clean_price_series(val_eq_df, symbol='005930')
    validator_eq_ok = (
        (cleaned_eq[['Open', 'High', 'Low', 'Close']] > 0).all().all()
        and (cleaned_eq['High'] >= cleaned_eq['Open']).all()
        and (cleaned_eq['High'] >= cleaned_eq['Close']).all()
        and (cleaned_eq['Low'] <= cleaned_eq['Open']).all()
        and (cleaned_eq['Low'] <= cleaned_eq['Close']).all()
        and (cleaned_eq['High'] >= cleaned_eq['Low']).all()
    )

    # Verify DB batch upsert roundtrip resilience for both commodities and equities
    db_roundtrip_ok = False
    try:
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            tmp_db_path = tmp_db.name
        test_db = StockPriceDB(tmp_db_path)
        cl_count = test_db.update_prices_batch({'CL=F': val_cl_df})
        eq_count = test_db.update_prices_batch({'005930': val_eq_df})
        ret_cl = test_db.get_prices('CL=F')
        ret_eq = test_db.get_prices('005930')
        test_db.close()
        try:
            os.remove(tmp_db_path)
        except Exception:
            pass

        db_roundtrip_ok = (
            cl_count == 2 and eq_count == 5
            and ret_cl['Close'].iloc[0] == -37.63
            and (ret_eq[['Open', 'High', 'Low', 'Close']] > 0).all().all()
            and (ret_eq['High'] >= ret_eq['Low']).all()
        )
    except Exception as e:
        print(f"  DB roundtrip verification error: {e}")

    # Verify OnDevicePredictionModel indicator merge isolates auxiliary NaN columns
    indicator_isolation_ok = False
    try:
        import numpy as np
        from src.ai.prediction_model import OnDevicePredictionModel
        pred_model = OnDevicePredictionModel()
        dummy_stock = pd.DataFrame({'Close': [100.0, 101.0, 102.0]}, index=pd.date_range('2026-01-01', periods=3))
        dummy_ind = pd.DataFrame({'vix_change': [0.1, 0.2, 0.3], 'vix_raw': [np.nan, 20.0, np.nan]}, index=pd.date_range('2026-01-01', periods=3))
        merged_ind = pred_model._merge_indicator_history(dummy_stock, dummy_ind)
        indicator_isolation_ok = ('vix_raw' not in merged_ind.columns) and ('vix_change' in merged_ind.columns)
    except Exception as e:
        print(f"  Indicator merge isolation check error: {e}")

    validator_ok = validator_cl_ok and validator_eq_ok and db_roundtrip_ok and indicator_isolation_ok
    print(f"  DataValidator & DB Roundtrip Resilience (CL=F negative kept, equity rectified, auxiliary NaNs isolated): {validator_ok} -> {'PASS' if validator_ok else 'FAIL'}")

    resilience_ok = rate_limiter_ok and validator_ok
    diagnostic_results.append(("Resilience Architecture", resilience_ok, "Rate limiter active, asset-aware price validation & DB roundtrip verified"))
    if not resilience_ok:
        all_passed = False

    # ─────────────────────────────────────────────────────────────────────────────
    # 6. Invariant Verification: synthetic_rows == 0 (R4)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n[DIAGNOSTIC 6/6] Verifying Strict Invariant: synthetic_rows == 0...")
    status_path = 'benchmarks/30year/status.json'
    summary_path = 'benchmarks/30year/stock_universe_summary.json'

    status_ok = False
    summary_ok = False

    if os.path.exists(status_path):
        with open(status_path, encoding='utf-8') as f:
            st = json.load(f)
        sr = st.get('synthetic_rows')
        if sr == 0 and type(sr) is int:
            status_ok = True
            print(f"  [PASS] {status_path}: synthetic_rows == 0 (type: {type(sr).__name__})")
        else:
            print(f"  [FAIL] {status_path}: synthetic_rows = {sr} (type: {type(sr).__name__})")

    if os.path.exists(summary_path):
        with open(summary_path, encoding='utf-8') as f:
            sm = json.load(f)
        sr = sm.get('metadata', {}).get('synthetic_rows')
        if sr == 0 and type(sr) is int:
            summary_ok = True
            print(f"  [PASS] {summary_path}: metadata.synthetic_rows == 0 (type: {type(sr).__name__})")
        else:
            print(f"  [FAIL] {summary_path}: metadata.synthetic_rows = {sr} (type: {type(sr).__name__})")

    invariant_ok = status_ok and summary_ok
    diagnostic_results.append(("Synthetic Rows Invariant", invariant_ok, "synthetic_rows == 0 (pure Python int 0) across benchmarks"))
    if not invariant_ok:
        all_passed = False

    # ─────────────────────────────────────────────────────────────────────────────
    # Final Diagnostic Summary Table
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("                    FINAL DIAGNOSTIC VERIFICATION SUMMARY                     ")
    print("=" * 80)
    for name, ok, details in diagnostic_results:
        mark = "[PASS]" if ok else "[FAIL]"
        print(f"  {mark:<8} {name:<26} : {details}")
    print("=" * 80)
    print(f"OVERALL DIAGNOSTIC RESULT: {'ALL VERIFICATIONS PASSED (SUCCESS)' if all_passed else 'SOME CHECKS FAILED'}")
    print("=" * 80 + "\n")

    return all_passed

if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)

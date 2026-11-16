import sqlite3
import math
import os
import pandas as pd
from datetime import datetime

print("=== Starting Database Cleanup and Repair ===")

# 1. Clean NULL rows from global_indicators in market_indicators.db
for ind_db_path in ['trading_system/market_indicators.db', 'market_indicators.db']:
    if os.path.exists(ind_db_path):
        conn = sqlite3.connect(ind_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM global_indicators WHERE price IS NULL")
        null_count = cur.fetchone()[0]
        if null_count > 0:
            cur.execute("DELETE FROM global_indicators WHERE price IS NULL")
            conn.commit()
            print(f"[{ind_db_path}] Deleted {null_count} rows with NULL price from global_indicators.")
        else:
            print(f"[{ind_db_path}] 0 NULL rows found in global_indicators.")
        conn.close()

# 2. Rectify negative/inverted/zero OHLC rows in stock_prices.db for equity symbols
for price_db_path in ['trading_system/stock_prices.db', 'stock_prices.db']:
    if os.path.exists(price_db_path):
        conn = sqlite3.connect(price_db_path)
        cur = conn.cursor()
        
        # Check corrupted equity rows (non-positive OHLC, High < Low, High < Open/Close, Low > Open/Close)
        cur.execute("""
            SELECT COUNT(*) FROM stock_prices 
            WHERE (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 
                   OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
                   OR high < open OR high < close OR low > open OR low > close OR high < low) 
            AND symbol NOT IN ('CL=F', '^IRX', '^TNX', '^FVX', '2YY=X')
            AND symbol NOT LIKE '^%' AND symbol NOT LIKE '%=F' AND symbol NOT LIKE '%=X'
        """)
        bad_cnt = cur.fetchone()[0]
        print(f"[{price_db_path}] Bad equity price rows found: {bad_cnt}")
        
        if bad_cnt > 0:
            cur.execute("""
                UPDATE stock_prices 
                SET 
                    open = CASE 
                        WHEN open <= 0 OR open IS NULL THEN ABS(close)
                        ELSE ABS(open)
                    END,
                    close = ABS(close),
                    high = MAX(
                        CASE WHEN open <= 0 OR open IS NULL THEN ABS(close) ELSE ABS(open) END,
                        CASE WHEN high <= 0 OR high IS NULL THEN ABS(close) ELSE ABS(high) END,
                        CASE WHEN low <= 0 OR low IS NULL THEN ABS(close) ELSE ABS(low) END,
                        ABS(close)
                    ),
                    low = MIN(
                        CASE WHEN open <= 0 OR open IS NULL THEN ABS(close) ELSE ABS(open) END,
                        CASE WHEN high <= 0 OR high IS NULL THEN ABS(close) ELSE ABS(high) END,
                        CASE WHEN low <= 0 OR low IS NULL THEN ABS(close) ELSE ABS(low) END,
                        ABS(close)
                    )
                WHERE (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 
                       OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
                       OR high < open OR high < close OR low > open OR low > close OR high < low)
                AND symbol NOT IN ('CL=F', '^IRX', '^TNX', '^FVX', '2YY=X')
                AND symbol NOT LIKE '^%' AND symbol NOT LIKE '%=F' AND symbol NOT LIKE '%=X'
            """)
            conn.commit()
            print(f"[{price_db_path}] Rectified {cur.rowcount} bad equity price rows.")
            
            # Re-verify
            cur.execute("""
                SELECT COUNT(*) FROM stock_prices 
                WHERE (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 
                       OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
                       OR high < open OR high < close OR low > open OR low > close OR high < low) 
                AND symbol NOT IN ('CL=F', '^IRX', '^TNX', '^FVX', '2YY=X')
                AND symbol NOT LIKE '^%' AND symbol NOT LIKE '%=F' AND symbol NOT LIKE '%=X'
            """)
            remaining = cur.fetchone()[0]
            print(f"[{price_db_path}] Remaining bad equity price rows: {remaining}")
            assert remaining == 0, f"Expected 0 bad equity rows, got {remaining}"
            
        conn.close()

print("=== DB Repair Complete ===")

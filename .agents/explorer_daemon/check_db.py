import sqlite3

databases = ["market_indicators.db", "trading_system/market_indicators.db"]
for db in databases:
    print(f"=== Database: {db} ===")
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", [t[0] for t in tables])
        
        # If pipeline_runs exists, print its columns
        if any(t[0] == 'pipeline_runs' for t in tables):
            cursor.execute("PRAGMA table_info(pipeline_runs);")
            columns = cursor.fetchall()
            print("pipeline_runs columns:")
            for col in columns:
                print(col)
        else:
            print("pipeline_runs table does NOT exist.")
        conn.close()
    except Exception as e:
        print(f"Error reading {db}: {e}")

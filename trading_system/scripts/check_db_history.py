import sqlite3
from pathlib import Path

db_path = Path("trading_system/market_indicators.db")
if not db_path.exists():
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(str(db_path))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables in DB:", tables)
    if "pipeline_run_history" in tables:
        count = conn.execute("SELECT count(*) FROM pipeline_run_history").fetchone()[0]
        print(f"pipeline_run_history row count: {count}")
        rows = conn.execute("SELECT * FROM pipeline_run_history ORDER BY start_time DESC LIMIT 10").fetchall()
        for r in rows:
            print("Run row:", r)
    else:
        print("pipeline_run_history table DOES NOT EXIST!")

    if "ensemble_prediction_history" in tables:
        ens_count = conn.execute("SELECT count(*) FROM ensemble_prediction_history").fetchone()[0]
        print(f"ensemble_prediction_history row count: {ens_count}")
    else:
        print("ensemble_prediction_history table DOES NOT EXIST!")

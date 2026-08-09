"""
migrate_to_postgres.py — SQLite to PostgreSQL Migration Utility

Migrates historical stock prices, market indicators, fundamental data,
and trade logs from local SQLite database files to a target PostgreSQL instance.

Usage:
  python trading_system/scripts/migrate_to_postgres.py
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.persistence.unified_db import UnifiedDBEngine, PostgresConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MigrateToPostgres")


def migrate_table(sqlite_db_path: Path, table_name: str, pg_engine: UnifiedDBEngine):
    if not sqlite_db_path.exists():
        logger.warning(f"SQLite DB file {sqlite_db_path} does not exist. Skipping table '{table_name}'.")
        return

    logger.info(f"Starting migration for table '{table_name}' from {sqlite_db_path.name}...")
    sq_conn = sqlite3.connect(sqlite_db_path)
    sq_cur = sq_conn.cursor()

    try:
        sq_cur.execute(f"SELECT * FROM {table_name}")
        rows = sq_cur.fetchall()
        if not rows:
            logger.info(f"Table '{table_name}' is empty.")
            return

        col_names = [description[0] for description in sq_cur.description]
        placeholders = ", ".join(["%s"] * len(col_names))
        cols_str = ", ".join(col_names)

        pg_conn = pg_engine.get_connection()
        pg_cur = pg_conn.cursor()

        insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"

        batch_size = 1000
        total_inserted = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            pg_cur.executemany(insert_sql, batch)
            pg_conn.commit()
            total_inserted += len(batch)

        logger.info(f"Successfully migrated {total_inserted} rows into PostgreSQL table '{table_name}'.")
        pg_engine.release_connection(pg_conn)
    except Exception as e:
        logger.error(f"Failed to migrate table '{table_name}': {e}")
    finally:
        sq_conn.close()


def main():
    os.environ["DB_ENGINE"] = "postgresql"
    pg_config = PostgresConfig()
    logger.info(f"Initializing target PostgreSQL database: {pg_config.host}:{pg_config.port}/{pg_config.database}...")

    engine = UnifiedDBEngine()
    if engine.engine_type != "postgresql":
        logger.error("PostgreSQL driver/connection pool not available. Ensure psycopg2 is installed and DB settings are valid.")
        sys.exit(1)

    # 1. Create PostgreSQL Schema
    engine.create_postgres_schema()

    # 2. Migrate stock_prices
    stock_db_path = _PROJECT_ROOT / "stock_prices.db"
    migrate_table(stock_db_path, "stock_prices", engine)

    # 3. Migrate market_indicators & fundamentals
    indicators_db_path = _PROJECT_ROOT / "market_indicators.db"
    migrate_table(indicators_db_path, "global_indicators", engine)
    migrate_table(indicators_db_path, "stock_fundamentals", engine)

    # 4. Migrate trade logs
    trade_db_path = _PROJECT_ROOT / "trade_logs.db"
    migrate_table(trade_db_path, "orders", engine)
    migrate_table(trade_db_path, "executions", engine)

    logger.info("PostgreSQL migration process completed successfully!")


if __name__ == "__main__":
    main()

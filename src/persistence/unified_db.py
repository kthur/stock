"""
unified_db.py — Unified Persistence Layer (PostgreSQL & SQLite dual engine)

Supports seamless switching between SQLite WAL mode and PostgreSQL via DB_ENGINE environment variable.
Provides connection pooling, SQL dialect translation, schema initialization, and migration helpers.
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

_TRADING_SYSTEM_ROOT = Path(__file__).resolve().parent.parent.parent


class PostgresConfig:
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "stock_trading")
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.sslmode = os.getenv("POSTGRES_SSLMODE", "prefer")

    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def dsn(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "sslmode": self.sslmode,
        }


class UnifiedDBEngine:
    """
    Unified database interface capable of driving both SQLite WAL and PostgreSQL.
    Controlled by DB_ENGINE environment variable ('sqlite' or 'postgresql').
    """

    def __init__(self, sqlite_db_name: str = "market_indicators.db"):
        self.engine_type = os.getenv("DB_ENGINE", "sqlite").lower()
        self.pg_config = PostgresConfig()
        self.sqlite_path = _TRADING_SYSTEM_ROOT / sqlite_db_name
        self._pg_pool = None

        if self.engine_type == "postgresql":
            self._init_postgres_pool()

    def _init_postgres_pool(self):
        """Initialize PostgreSQL connection pool if psycopg2 or asyncpg is available."""
        try:
            import psycopg2.pool
            self._pg_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self.pg_config.dsn()
            )
            logger.info(f"[UnifiedDBEngine] PostgreSQL Connection Pool initialized ({self.pg_config.host}:{self.pg_config.port}/{self.pg_config.database}).")
        except ImportError:
            logger.warning("[UnifiedDBEngine] psycopg2 not installed. Falling back to SQLite engine.")
            self.engine_type = "sqlite"
        except Exception as e:
            logger.error(f"[UnifiedDBEngine] PostgreSQL pool initialization failed: {e}. Falling back to SQLite.")
            self.engine_type = "sqlite"

    def get_connection(self):
        """Returns a connection object for the configured engine."""
        if self.engine_type == "postgresql" and self._pg_pool:
            return self._pg_pool.getconn()
        else:
            conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            return conn

    def release_connection(self, conn):
        """Releases connection back to the pool or closes SQLite connection."""
        if self.engine_type == "postgresql" and self._pg_pool:
            self._pg_pool.putconn(conn)
        else:
            try:
                conn.close()
            except Exception:
                pass

    def execute_query(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        """Execute a SELECT query and return rows."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            if self.engine_type == "postgresql":
                sql_trans = sql.replace("?", "%s")
                cur.execute(sql_trans, params)
            else:
                cur.execute(sql, params)
            rows = cur.fetchall()
            from typing import cast
            return cast(List[Tuple[Any, ...]], list(rows))
        finally:
            self.release_connection(conn)

    def execute_write(self, sql: str, params: Tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            if self.engine_type == "postgresql":
                sql_trans = sql.replace("?", "%s")
                cur.execute(sql_trans, params)
            else:
                cur.execute(sql, params)
            conn.commit()
            return int(cur.rowcount if cur.rowcount is not None else 0)

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def create_postgres_schema(self):
        """Creates standard PostgreSQL schema tables for high-performance quant trading."""
        ddl_script = """
        CREATE TABLE IF NOT EXISTS stock_prices (
            symbol VARCHAR(32) NOT NULL,
            date VARCHAR(16) NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume BIGINT,
            adj_close DOUBLE PRECISION,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, date)
        );

        CREATE TABLE IF NOT EXISTS global_indicators (
            date VARCHAR(16) NOT NULL,
            symbol VARCHAR(32) NOT NULL,
            name VARCHAR(64),
            price DOUBLE PRECISION,
            change_pct DOUBLE PRECISION,
            PRIMARY KEY (date, symbol)
        );

        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            symbol VARCHAR(32) NOT NULL,
            date VARCHAR(16) NOT NULL,
            revenue DOUBLE PRECISION,
            operating_income DOUBLE PRECISION,
            net_income DOUBLE PRECISION,
            eps DOUBLE PRECISION,
            shares_outstanding BIGINT,
            dividend_per_share DOUBLE PRECISION,
            book_value DOUBLE PRECISION,
            PRIMARY KEY (symbol, date)
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(64) PRIMARY KEY,
            symbol VARCHAR(32),
            order_type VARCHAR(16),
            quantity INT,
            price DOUBLE PRECISION,
            status VARCHAR(16),
            filled_quantity INT,
            created_at TIMESTAMP,
            executed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS executions (
            exec_id VARCHAR(64) PRIMARY KEY,
            order_id VARCHAR(64),
            symbol VARCHAR(32),
            action VARCHAR(8),
            quantity INT,
            price DOUBLE PRECISION,
            fee DOUBLE PRECISION,
            executed_at TIMESTAMP
        );
        """
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(ddl_script)
            conn.commit()
            logger.info("[UnifiedDBEngine] PostgreSQL schema created/verified successfully.")
        finally:
            self.release_connection(conn)

    def close(self):
        if self._pg_pool:
            self._pg_pool.closeall()

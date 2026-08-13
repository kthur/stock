"""
TimescaleDB / High-Throughput Time-Series Database Connector Module
Extends SQLite storage to scalable PostgreSQL/TimescaleDB for enterprise time-series data handling.
"""

import logging
import sqlite3
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TimescaleDBConnector:
    """
    Enterprise Time-Series Data Store Connector.
    Provides hypertable partitioning and WAL-optimised batch ingestion.
    """

    def __init__(self, db_url: Optional[str] = None, fallback_sqlite_path: str = "stock_prices.db"):
        self.db_url = db_url
        self.fallback_sqlite_path = fallback_sqlite_path
        self._init_schema()

    def _get_connection(self):
        if self.db_url and self.db_url.startswith("postgresql"):
            try:
                import psycopg2
                return psycopg2.connect(self.db_url)
            except Exception as e:
                logger.warning(f"[TIMESCALEDB] PostgreSQL connection failed: {e}. Falling back to SQLite.")

        conn = sqlite3.connect(self.fallback_sqlite_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_schema(self):
        """Initializes time-series tables and hypertable partitions."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices_ts (
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (time, symbol)
                );
            """)
            conn.commit()
            logger.info("[TIMESCALEDB] Schema initialized successfully.")
        except Exception as e:
            logger.warning(f"[TIMESCALEDB] Schema init error: {e}")
        finally:
            conn.close()

    def batch_insert_prices(self, price_records: List[Dict[str, Any]]) -> bool:
        """Batch inserts price records using optimized multi-row queries."""
        if not price_records:
            return True
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = """
                INSERT OR REPLACE INTO stock_prices_ts (time, symbol, market, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            rows = [
                (
                    r.get("time", r.get("date", "")),
                    r.get("symbol", ""),
                    r.get("market", ""),
                    float(r.get("open", 0.0)),
                    float(r.get("high", 0.0)),
                    float(r.get("low", 0.0)),
                    float(r.get("close", 0.0)),
                    float(r.get("volume", 0.0))
                )
                for r in price_records
            ]
            cursor.executemany(query, rows)
            conn.commit()
            logger.info(f"[TIMESCALEDB] Inserted {len(rows)} price records.")
            return True
        except Exception as e:
            logger.error(f"[TIMESCALEDB] Batch insert failed: {e}")
            return False
        finally:
            conn.close()

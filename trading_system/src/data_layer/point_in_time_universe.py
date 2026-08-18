"""
Point-in-Time Universe & Delisting Archive Module (Phase 2 Institutional Enhancement)
Eliminates survivorship bias by tracking historical index constituents, entry/exit dates,
and realistic delisting terminal liquidation values.
"""

import logging
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PointInTimeUniverseManager:
    """
    Manages historical index constituents and delisted assets to ensure
    survivorship-bias-free backtesting and training data preparation.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).resolve().parent.parent.parent / "market_indicators.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_db(self):
        """Initializes tables for point-in-time constituents and delisting events."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historical_constituents (
                        market TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        name TEXT,
                        start_date TEXT NOT NULL,
                        end_date TEXT,
                        is_active INTEGER DEFAULT 1,
                        PRIMARY KEY(market, symbol, start_date)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS delisting_events (
                        symbol TEXT PRIMARY KEY,
                        market TEXT NOT NULL,
                        delisting_date TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        recovery_rate REAL DEFAULT 0.0,
                        last_price REAL,
                        notes TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize Point-in-Time DB schema: {e}")

    def record_constituent_membership(
        self,
        market: str,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        name: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        """Records a symbol's membership period in a market/index."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO historical_constituents
                    (market, symbol, name, start_date, end_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (market.upper(), symbol, name, start_date, end_date, 1 if is_active else 0))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to record constituent membership: {e}")
            return False

    def record_delisting_event(
        self,
        symbol: str,
        market: str,
        delisting_date: str,
        reason: str = "BANKRUPTCY",
        recovery_rate: float = 0.0,
        last_price: Optional[float] = None,
        notes: str = ""
    ) -> bool:
        """
        Records a delisting event with reason and terminal liquidation recovery rate.
        Reasons: 'BANKRUPTCY' (recovery ~0.0), 'ACQUISITION' (recovery ~1.0+premium), 'REGULATORY' (haircut)
        """
        try:
            safe_rec = float(np.clip(recovery_rate, 0.0, 2.0))
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO delisting_events
                    (symbol, market, delisting_date, reason, recovery_rate, last_price, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (symbol, market.upper(), delisting_date, reason.upper(), safe_rec, last_price, notes))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to record delisting event: {e}")
            return False

    def get_active_universe_at(
        self,
        as_of_date: str,
        market: Optional[str] = None,
        fallback_symbols: Optional[List[str]] = None
    ) -> List[str]:
        """
        Retrieves active constituents as of a specific date in history.
        If no historical records exist for that market, returns fallback_symbols.
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                if market:
                    cursor.execute("""
                        SELECT symbol FROM historical_constituents
                        WHERE market = ? AND start_date <= ? AND (end_date IS NULL OR end_date >= ?)
                    """, (market.upper(), as_of_date, as_of_date))
                else:
                    cursor.execute("""
                        SELECT symbol FROM historical_constituents
                        WHERE start_date <= ? AND (end_date IS NULL OR end_date >= ?)
                    """, (as_of_date, as_of_date))
                rows = cursor.fetchall()
                if rows:
                    return [r[0] for r in rows]
        except Exception as e:
            logger.debug(f"Point-in-Time universe query failed: {e}")

        return fallback_symbols or []

    def get_delisting_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves delisting details and terminal recovery rate for a given symbol."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT delisting_date, reason, recovery_rate, last_price, notes
                    FROM delisting_events WHERE symbol = ?
                """, (symbol,))
                row = cursor.fetchone()
                if row:
                    return {
                        'delisting_date': row[0],
                        'reason': row[1],
                        'recovery_rate': float(row[2]),
                        'last_price': float(row[3]) if row[3] is not None else None,
                        'notes': row[4]
                    }
        except Exception as e:
            logger.debug(f"Failed to fetch delisting info for {symbol}: {e}")
        return None

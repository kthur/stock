"""Realtime monitor state store - 장중 모니터링 상태 SQLite 영속화.

고점/저점 추적, 손절·익절 발동 이력, 시그널 보정 이력을 날짜별로 저장하여
15분 간격 실행 사이에도 상태가 유지되고 중복 알림을 방지한다.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SymbolIntradayState:
    symbol: str
    date: str
    open_price: float = 0.0
    peak_price: float = 0.0
    low_price: float = 0.0
    stop_triggered: bool = False
    take_profit_triggered: bool = False
    stop_reasons: str = ""
    signal_downgraded: bool = False
    last_alert_ts: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class RealtimeStateStore:
    """SQLite 기반 장중 상태 저장소 (realtime_state.db)."""

    def __init__(self, db_path: str = "realtime_state.db"):
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbol_state (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open_price REAL DEFAULT 0,
                    peak_price REAL DEFAULT 0,
                    low_price REAL DEFAULT 0,
                    stop_triggered INTEGER DEFAULT 0,
                    take_profit_triggered INTEGER DEFAULT 0,
                    stop_reasons TEXT DEFAULT '',
                    signal_downgraded INTEGER DEFAULT 0,
                    last_alert_ts TEXT DEFAULT '',
                    updated_at TEXT DEFAULT '',
                    PRIMARY KEY (symbol, date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    detail TEXT DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_monitor_events_date
                ON monitor_events (date, event_type)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def get_state(self, symbol: str, date: str) -> SymbolIntradayState:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM symbol_state WHERE symbol=? AND date=?",
                (symbol, date),
            ).fetchone()
            if row is None:
                return SymbolIntradayState(symbol=symbol, date=date)
            cols = [c[1] for c in conn.execute("PRAGMA table_info(symbol_state)").fetchall()]
            return SymbolIntradayState(
                symbol=row[cols.index("symbol")],
                date=row[cols.index("date")],
                open_price=row[cols.index("open_price")] or 0.0,
                peak_price=row[cols.index("peak_price")] or 0.0,
                low_price=row[cols.index("low_price")] or 0.0,
                stop_triggered=bool(row[cols.index("stop_triggered")]),
                take_profit_triggered=bool(row[cols.index("take_profit_triggered")]),
                stop_reasons=row[cols.index("stop_reasons")] or "",
                signal_downgraded=bool(row[cols.index("signal_downgraded")]),
                last_alert_ts=row[cols.index("last_alert_ts")] or "",
                updated_at=row[cols.index("updated_at")] or "",
            )
        finally:
            conn.close()

    def update_state(self, state: SymbolIntradayState) -> None:
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO symbol_state (
                    symbol, date, open_price, peak_price, low_price,
                    stop_triggered, take_profit_triggered, stop_reasons,
                    signal_downgraded, last_alert_ts, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.symbol, state.date, state.open_price, state.peak_price, state.low_price,
                    int(state.stop_triggered), int(state.take_profit_triggered),
                    state.stop_reasons, int(state.signal_downgraded),
                    state.last_alert_ts, state.updated_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def log_event(self, date: str, symbol: str, event_type: str, message: str, detail: str = "") -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO monitor_events (date, ts, symbol, event_type, message, detail) VALUES (?, ?, ?, ?, ?, ?)",
                    (date, datetime.now().isoformat(timespec="seconds"), symbol, event_type, message, detail[:2000]),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"[STATE] event log failed: {e}")

    def get_events(self, date: str, event_type: Optional[str] = None, limit: int = 50) -> List[dict]:
        conn = self._connect()
        try:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM monitor_events WHERE date=? AND event_type=? ORDER BY id DESC LIMIT ?",
                    (date, event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM monitor_events WHERE date=? ORDER BY id DESC LIMIT ?",
                    (date, limit),
                ).fetchall()
            cols = [c[1] for c in conn.execute("PRAGMA table_info(monitor_events)").fetchall()]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    def reset_day(self, date: str) -> None:
        """새 거래일 시작 시 이전 날짜 상태 정리 (옵션)."""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM symbol_state WHERE date <> ?", (date,))
            conn.commit()
        finally:
            conn.close()

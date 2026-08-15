"""Persistence Layer - 데이터 저장소 (aiosqlite 비동기 마이그레이션)"""

import asyncio
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import aiosqlite
import pandas as pd

logger = logging.getLogger(__name__)

# Absolute path constant — resolves to trading_system/ directory regardless of CWD
_TRADING_SYSTEM_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_STOCK_PRICES_DB = _TRADING_SYSTEM_ROOT / "stock_prices.db"



class _DBConnection:
    """재사용 가능한 aiosqlite 연결 관리자 (Lock 기반 트랜잭션 보호)"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def get(self) -> aiosqlite.Connection:
        async with self._lock:
            if self._conn is None:
                self._conn = await aiosqlite.connect(self.db_path)
                await self._conn.execute("PRAGMA journal_mode=WAL")
                await self._conn.execute("PRAGMA synchronous=NORMAL")
                await self._conn.execute("PRAGMA cache_size=-32000")
                await self._conn.execute("PRAGMA temp_store=MEMORY")
                await self._conn.execute("PRAGMA busy_timeout=30000")
                await self._conn.execute("PRAGMA foreign_keys=ON")
            else:
                try:
                    await self._conn.execute("SELECT 1")
                except Exception:
                    try:
                        await self._conn.close()
                    except Exception:
                        pass
                    self._conn = await aiosqlite.connect(self.db_path)
                    await self._conn.execute("PRAGMA journal_mode=WAL")
                    await self._conn.execute("PRAGMA synchronous=NORMAL")
                    await self._conn.execute("PRAGMA cache_size=-32000")
                    await self._conn.execute("PRAGMA temp_store=MEMORY")
                    await self._conn.execute("PRAGMA busy_timeout=30000")
                    await self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

    async def execute_write(self, sql: str, params: tuple = ()):
        """Locks connection during write and commit to ensure transaction isolation."""
        async with self._lock:
            if self._conn is None:
                self._conn = await aiosqlite.connect(self.db_path)
                await self._conn.execute("PRAGMA journal_mode=WAL")
                await self._conn.execute("PRAGMA synchronous=NORMAL")
                await self._conn.execute("PRAGMA cache_size=-32000")
                await self._conn.execute("PRAGMA temp_store=MEMORY")
                await self._conn.execute("PRAGMA busy_timeout=30000")
            await self._conn.execute(sql, params)
            await self._conn.commit()

    async def close(self):
        async with self._lock:
            if self._conn:
                await self._conn.close()
                self._conn = None


class TradeLogger:
    """주문 및 체결 로그 저장 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
        self._conn_mgr = _DBConnection(self.db_path)

    async def _get_conn(self):
        conn = await self._conn_mgr.get()
        conn.row_factory = sqlite3.Row
        return conn

    async def _init_database(self):
        """데이터베이스 초기화 (비동기 지연 초기화)"""
        if self._db_initialized:
            return
        async with self._init_lock:
            if self._db_initialized:
                return
            conn = await self._get_conn()
            cursor = await conn.cursor()

            # 주문 테이블
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    order_type TEXT,
                    quantity INTEGER,
                    price REAL,
                    status TEXT,
                    filled_quantity INTEGER,
                    created_at TIMESTAMP,
                    executed_at TIMESTAMP
                )
            """)

            # 체결 기록 테이블
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    symbol TEXT,
                    quantity INTEGER,
                    price REAL,
                    executed_at TIMESTAMP,
                    FOREIGN KEY(order_id) REFERENCES orders(order_id)
                )
            """)

            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id);")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_sym_date ON orders(symbol, created_at DESC);")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")

            await conn.commit()
            self._db_initialized = True
            self.logger.info(f"Database initialized at {self.db_path}")

    async def log_order(self, order: Any) -> None:
        """주문 로그"""
        await self._init_database()
        sql = """
            INSERT OR REPLACE INTO orders
            (order_id, symbol, order_type, quantity, price, status, filled_quantity, created_at, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            order.order_id,
            order.symbol,
            order.order_type.value,
            order.quantity,
            order.price,
            order.status.value,
            order.filled_quantity,
            order.created_at.isoformat(),
            order.executed_at.isoformat() if order.executed_at else None,
        )
        await self._conn_mgr.execute_write(sql, params)
        self.logger.debug(f"Order logged: {order.order_id}")

    async def log_execution(self, order_id: str, symbol: str, quantity: int, price: float):
        """체결 기록"""
        await self._init_database()
        now_str = datetime.now().isoformat()
        sql_order = """
            INSERT OR IGNORE INTO orders
            (order_id, symbol, order_type, quantity, price, status, created_at)
            VALUES (?, ?, 'LIMIT', ?, ?, 'FILLED', ?)
        """
        await self._conn_mgr.execute_write(sql_order, (order_id, symbol, quantity, price, now_str))

        sql = """
            INSERT INTO executions
            (order_id, symbol, quantity, price, executed_at)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (order_id, symbol, quantity, price, now_str)
        await self._conn_mgr.execute_write(sql, params)
        self.logger.info(f"Execution logged: {symbol} x{quantity} @ {price}")

    async def get_trade_history(self, symbol: str | None = None, limit: int = 100) -> List[Dict]:
        """거래 이력 조회"""
        await self._init_database()
        conn = await self._get_conn()
        async with conn.execute(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC LIMIT ?"
            if symbol
            else "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (symbol, limit) if symbol else (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        await self._conn_mgr.close()


class AssetHistoryDB:
    """자산 이력 저장 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "asset_history.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
        self._conn_mgr = _DBConnection(self.db_path)

    async def _get_conn(self):
        conn = await self._conn_mgr.get()
        conn.row_factory = sqlite3.Row
        return conn

    async def _init_database(self):
        """데이터베이스 초기화 (비동기 지연 초기화)"""
        if self._db_initialized:
            return
        async with self._init_lock:
            if self._db_initialized:
                return
            conn = await self._get_conn()
            cursor = await conn.cursor()

            # 자산 스냅샷 테이블
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS asset_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL,
                    total_value REAL,
                    holdings TEXT,
                    timestamp TIMESTAMP
                )
            """)

            await conn.commit()
            self._db_initialized = True
            self.logger.info(f"Asset history DB initialized at {self.db_path}")

    async def save_snapshot(self, cash: float, total_value: float, holdings: Dict[str, int]):
        """자산 스냅샷 저장"""
        await self._init_database()
        holdings_json = json.dumps(holdings)
        sql = """
            INSERT INTO asset_snapshots (cash, total_value, holdings, timestamp)
            VALUES (?, ?, ?, ?)
        """
        params = (cash, total_value, holdings_json, datetime.now().isoformat())
        await self._conn_mgr.execute_write(sql, params)
        self.logger.info(f"Asset snapshot saved: cash={cash}, total={total_value}")

    async def get_history(self, limit: int = 100) -> List[Dict]:
        """자산 이력 조회"""
        await self._init_database()
        conn = await self._get_conn()
        async with conn.execute("SELECT * FROM asset_snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                record = dict(row)
                record["holdings"] = json.loads(record["holdings"])
                result.append(record)
            return result

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        await self._conn_mgr.close()


class AIPredictionDB:
    """AI 투자 예측 기록 및 자체 평가 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "ai_predictions.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
        self._conn_mgr = _DBConnection(self.db_path)

    async def _get_conn(self):
        conn = await self._conn_mgr.get()
        conn.row_factory = sqlite3.Row
        return conn

    async def _init_database(self):
        if self._db_initialized:
            return
        async with self._init_lock:
            if self._db_initialized:
                return
            conn = await self._get_conn()
            cursor = await conn.cursor()

            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    recommendation TEXT,
                    sentiment TEXT,
                    confidence REAL,
                    target_price REAL,
                    current_price REAL,
                    reasoning TEXT,
                    timestamp TIMESTAMP,
                    evaluated INTEGER DEFAULT 0,
                    accuracy_score REAL DEFAULT NULL
                )
            """)
            await conn.commit()
            self._db_initialized = True
            self.logger.info(f"AI Prediction DB initialized at {self.db_path}")

    async def log_prediction(self, opinion: Any, current_price: float) -> None:
        await self._init_database()
        sql = """
            INSERT INTO predictions
            (symbol, recommendation, sentiment, confidence, target_price, current_price, reasoning, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            opinion.symbol,
            opinion.recommendation,
            opinion.sentiment.value if hasattr(opinion.sentiment, "value") else str(opinion.sentiment),
            opinion.confidence,
            opinion.target_price,
            current_price,
            opinion.reasoning,
            opinion.timestamp.isoformat() if opinion.timestamp else datetime.now().isoformat(),
        )
        await self._conn_mgr.execute_write(sql, params)
        self.logger.debug(f"AI prediction logged for {opinion.symbol}")

    async def evaluate_pending_predictions(self, get_current_price_func: Callable[[str], float]) -> None:
        """저장된 예측 중 오래된(예: 7일 이상) 항목을 실제 가격과 비교하여 정확도 평가"""
        await self._init_database()
        try:
            threshold_date = (datetime.now() - timedelta(days=7)).isoformat()

            conn = await self._get_conn()
            async with conn.execute(
                "SELECT * FROM predictions WHERE evaluated = 0 AND timestamp < ?", (threshold_date,)
            ) as cursor:
                rows = await cursor.fetchall()

            for row in rows:
                symbol = row["symbol"]
                rec = row["recommendation"]
                orig_price = row["current_price"]

                try:
                    latest_price = await asyncio.to_thread(get_current_price_func, symbol)
                    if not latest_price:
                        continue

                    price_diff_pct = (latest_price - orig_price) / orig_price

                    score = 0.5
                    if rec == "BUY":
                        if price_diff_pct > 0.05:
                            score = 1.0
                        elif price_diff_pct > 0:
                            score = 0.8
                        elif price_diff_pct < -0.05:
                            score = 0.0
                        else:
                            score = 0.3
                    elif rec == "SELL":
                        if price_diff_pct < -0.05:
                            score = 1.0
                        elif price_diff_pct < 0:
                            score = 0.8
                        elif price_diff_pct > 0.05:
                            score = 0.0
                        else:
                            score = 0.3
                    else:
                        if abs(price_diff_pct) < 0.05:
                            score = 1.0
                        else:
                            score = 0.0

                    await conn.execute(
                        "UPDATE predictions SET evaluated = 1, accuracy_score = ? WHERE id = ?", (score, row["id"])
                    )
                    self.logger.info(f"Evaluated AI prediction for {symbol} (Rec: {rec}, Score: {score})")

                except Exception as e:
                    self.logger.warning(f"Failed to evaluate prediction for {symbol}: {e}")

            await conn.commit()
        except Exception as e:
            self.logger.error(f"Error evaluating AI predictions: {e}")

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        await self._conn_mgr.close()


def normalize_symbol(symbol: str) -> str:
    """Standardize ticker symbol canonical keys.

    KRX numeric codes (len <= 6) -> 6-digit zero padded (e.g., '5930' -> '005930').
    US tickers and non-numeric codes are returned stripped without modification (e.g. 'BRK.B').
    """
    s = str(symbol).strip()
    if s.isdigit() and len(s) <= 6:
        return s.zfill(6)
    return s


class StockPriceDB:
    """주가 데이터 SQLite 캐시 (OHLCV + 거래량) — 외부 API 재호출 방지

    Thread-safe: WAL 모드 + connection 재사용 + mutex lock.
    """

    def __init__(self, db_path: str = str(_DEFAULT_STOCK_PRICES_DB)):
        self.db_path = Path(db_path)
        self.logger = logger
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_db()

    def health_check(self) -> bool:
        """Runs PRAGMA quick_check to verify SQLite database integrity."""
        try:
            conn = self._get_conn()
            res = conn.execute("PRAGMA quick_check").fetchone()
            if res and res[0] == "ok":
                self.logger.info("StockPriceDB health check passed (PRAGMA quick_check = ok)")
                return True
            self.logger.critical(f"StockPriceDB health check FAILED: {res}")
            return False
        except Exception as e:
            self.logger.critical(f"StockPriceDB health check exception: {e}")
            return False

    def close(self):
        """현재 스레드의 sqlite3 커넥션 명시적 닫기"""

        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), timeout=30.0, check_same_thread=False
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn.execute("PRAGMA cache_size=-500000")  # 500MB page cache
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA mmap_size=2000000000") # 2GB memory mapped I/O
        return cast(sqlite3.Connection, self._local.conn)

    def _init_db(self):
        with self._write_lock:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")

                conn.execute("PRAGMA cache_size=-500000")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=2000000000")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_prices (
                        symbol TEXT NOT NULL,
                        date TEXT NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume INTEGER,
                        updated_at TEXT DEFAULT (datetime('now')),
                        PRIMARY KEY (symbol, date)
                    )
                """)
                conn.execute("DROP INDEX IF EXISTS idx_stock_prices_symbol_date")
                conn.execute("DROP INDEX IF EXISTS idx_stock_prices_sym_date")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices (date)")
                conn.commit()
            finally:
                conn.close()
        self.logger.info(f"StockPriceDB initialized at {self.db_path}")

    def update_prices(self, symbol: str, df: pd.DataFrame, bypass_validation: bool = False) -> int:
        """OHLCV DataFrame을 DB에 batch upsert. 반환: 저장된 행 수 (Retry Lock 포함)"""
        if df is None or df.empty:
            return 0

        symbol = normalize_symbol(symbol)

        if not bypass_validation:
            from src.data_layer.data_validator import DataValidator
            if not DataValidator.validate_price_data(symbol, df):
                self.logger.warning(f"[StockPriceDB] Price data validation failed for {symbol}. Upsert aborted.")
                return 0

        cols = {str(c).lower(): c for c in df.columns}
        has_open = "open" in cols
        has_high = "high" in cols
        has_low = "low" in cols
        has_close = "close" in cols
        has_vol = "volume" in cols

        import math
        records = []
        for idx, row in df.iterrows():
            d_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            try:
                op = float(row[cols["open"]]) if has_open else 0.0
                hi = float(row[cols["high"]]) if has_high else 0.0
                lo = float(row[cols["low"]]) if has_low else 0.0
                cl = float(row[cols["close"]]) if has_close else 0.0
                vol_f = float(row[cols["volume"]]) if has_vol else 0.0
                vol = int(vol_f) if math.isfinite(vol_f) and vol_f >= 0 else 0

                if not (math.isfinite(op) and math.isfinite(hi) and math.isfinite(lo) and math.isfinite(cl)):
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            records.append((symbol, d_str, op, hi, lo, cl, vol))
        if not records:
            return 0

        def _do_update():
            with self._write_lock:
                conn = self._get_conn()
                conn.executemany("""
                    INSERT OR REPLACE INTO stock_prices
                    (symbol, date, open, high, low, close, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, records)
                conn.commit()

        try:
            from src.data_layer.hybrid_storage import execute_sqlite_with_retry
            execute_sqlite_with_retry(_do_update)
        except (ImportError, ModuleNotFoundError):
            _do_update()

        count = len(records)
        self.logger.info(f"Upserted {count} price rows for {symbol}")
        return count

    def get_prices(self, symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """DB에서 주가 데이터 조회 (시계열 정렬된 DataFrame, 컬럼명 대문자)"""
        symbol = normalize_symbol(symbol)
        conn = self._get_conn()
        query = "SELECT date, open, high, low, close, volume FROM stock_prices WHERE symbol = ?"
        params: list = [symbol]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            end_param = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
            params.append(end_param)
        query += " ORDER BY date ASC"
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])
        if not df.empty:
            df.set_index("date", inplace=True)
            df.columns = [col.capitalize() for col in df.columns]
        else:
            df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            df.index = pd.DatetimeIndex([], name='date')
        return df

    def get_latest_date(self, symbol: str) -> Optional[str]:
        """해당 종목의 DB 내 최신 날짜 반환"""
        symbol = normalize_symbol(symbol)
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT MAX(date) FROM stock_prices WHERE symbol = ?", (symbol,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def _get_earliest_date(self, symbol: str) -> Optional[str]:
        """해당 종목의 DB 내 최초 날짜 반환"""
        symbol = normalize_symbol(symbol)
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT MIN(date) FROM stock_prices WHERE symbol = ?", (symbol,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def needs_update(self, symbol: str, max_age_days: int = 1,
                     start_date: Optional[str] = None) -> bool:
        """DB 데이터가 max_age_days 이상 지났거나, start_date보다 앞 데이터가 부족하면 True"""
        symbol = normalize_symbol(symbol)
        if max_age_days < 0:
            return False
        latest = self.get_latest_date(symbol)
        if latest is None:
            return True
        latest_dt = datetime.strptime(latest[:10], "%Y-%m-%d")
        if (datetime.now() - latest_dt).days >= max_age_days:
            return True
        if start_date is not None:
            earliest = self._get_earliest_date(symbol)
            if earliest is None:
                return True
            earliest_dt = datetime.strptime(earliest[:10], "%Y-%m-%d")
            start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
            if (earliest_dt - start_dt).days > 7:
                return True
        return False

    def get_all_symbols(self) -> List[str]:
        """DB에 저장된 모든 심볼 목록"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol")
        rows = cursor.fetchall()
        return [r[0] for r in rows]

    def count_rows(self, symbol: Optional[str] = None) -> int:
        """저장된 행 수 (선택적 symbol 필터)"""
        conn = self._get_conn()
        if symbol:
            symbol = normalize_symbol(symbol)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM stock_prices WHERE symbol = ?", (symbol,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM stock_prices")
        row = cursor.fetchone()
        return row[0] if row else 0

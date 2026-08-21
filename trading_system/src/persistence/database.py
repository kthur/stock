"""Persistence Layer - 데이터 저장소 (aiosqlite 비동기 마이그레이션)"""

import asyncio
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast

import aiosqlite
import numpy as np
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


class AsyncDBBase:
    """Base class for aiosqlite asynchronous database repositories."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
        self._conn_mgr = _DBConnection(self.db_path)

    async def _get_conn(self) -> aiosqlite.Connection:
        conn = await self._conn_mgr.get()
        conn.row_factory = sqlite3.Row
        return conn

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        await self._conn_mgr.close()


class TradeLogger(AsyncDBBase):
    """주문 및 체결 로그 저장 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "trade_logs.db"):
        super().__init__(db_path)

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
                    filled_quantity INTEGER DEFAULT 0,
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


class AssetHistoryDB(AsyncDBBase):
    """자산 이력 저장 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "asset_history.db"):
        super().__init__(db_path)

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


class AIPredictionDB(AsyncDBBase):
    """AI 투자 예측 기록 및 자체 평가 (aiosqlite 기반 비동기 구현)"""

    def __init__(self, db_path: str = "ai_predictions.db"):
        super().__init__(db_path)

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


class DataValidator:
    """
    Domain-level data validator for cleaning and enforcing invariants on market series.
    Separates data validation and sanitization domain logic from persistence mechanisms.
    """
    @staticmethod
    def validate_and_clean_price_series(df: pd.DataFrame, max_daily_jump: float = 0.65) -> pd.DataFrame:
        """
        Validates price series for unadjusted split anomalies or erroneous data feeds.
        Interpolates transient spikes/drops > max_daily_jump (65%) across all OHLC columns
        and enforces strict OHLC boundary invariants (Low <= Open, Close <= High).
        """
        if df.empty or len(df) < 5 or 'Close' not in df.columns:
            return df

        df_clean = df.copy()
        close = df_clean['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        pct_chg = close.pct_change().abs()
        anomalies = pct_chg > max_daily_jump
        transient_spikes = pd.Series(False, index=df_clean.index)
        if anomalies.any():
            # Check for transient single-day spike/drop that reverts immediately
            next_pct_chg = close.pct_change(-1).abs()
            transient_spikes = anomalies & (next_pct_chg > (max_daily_jump * 0.8))
            if transient_spikes.any():
                logger.warning(f"Detected {transient_spikes.sum()} transient price anomalies. Interpolating clean OHLC values.")
                for col in ['Close', 'Open', 'High', 'Low']:
                    if col in df_clean.columns:
                        df_clean.loc[transient_spikes, col] = np.nan
                        df_clean[col] = df_clean[col].interpolate(method='linear').ffill().bfill()
                        
            # Update close series after potential transient spike interpolation
            close = df_clean['Close']
            
        # Detect stock splits (permanent drops > 25% that don't revert) with crash guard & volume confirmation
        split_candidates = (close.pct_change() < -0.25) & (~transient_spikes)
        if split_candidates.any():
            split_dates = split_candidates[split_candidates].index
            for date in split_dates:
                # Get index of the date
                idx = df_clean.index.get_loc(date)
                if isinstance(idx, slice):
                    idx = idx.start
                elif isinstance(idx, np.ndarray):
                    idx = np.where(idx)[0][0]
                    
                if idx > 0:
                    prev_close = df_clean['Close'].iloc[idx-1]
                    curr_close = df_clean['Close'].iloc[idx]
                    if prev_close > 0:
                        ratio = curr_close / prev_close
                        # Standard split ratio check (e.g. 1:2, 1:3, 1:4, 1:5, 1:10, 2:3, 3:4)
                        is_standard_split_ratio = any(abs(ratio - r) / r < 0.08 for r in [0.5, 0.3333, 0.25, 0.2, 0.1, 0.05, 0.6667, 0.75])
                        
                        # Volume expansion confirmation (>1.25x volume expansion or zero-volume recovery)
                        has_vol_confirmation = True
                        if 'Volume' in df_clean.columns and len(df_clean['Volume']) > idx:
                            vol_prev = float(df_clean['Volume'].iloc[idx-1])
                            vol_curr = float(df_clean['Volume'].iloc[idx])
                            if vol_prev > 0 and vol_curr > 0:
                                has_vol_confirmation = (vol_curr / vol_prev) >= 1.25
                        
                        if is_standard_split_ratio and has_vol_confirmation:
                            logger.warning(f"Detected stock split around {date} with ratio {ratio:.4f}. Adjusting historical data.")
                            for col in ['Open', 'High', 'Low', 'Close']:
                                if col in df_clean.columns:
                                    df_clean.iloc[:idx, df_clean.columns.get_loc(col)] *= ratio
                            if 'Volume' in df_clean.columns:
                                df_clean.iloc[:idx, df_clean.columns.get_loc('Volume')] /= ratio

        # Enforce OHLC consistency invariants
        if 'High' in df_clean.columns and 'Low' in df_clean.columns and 'Close' in df_clean.columns:
            open_series = df_clean['Open'] if 'Open' in df_clean.columns else df_clean['Close']
            df_clean['High'] = np.fmax(df_clean['High'], np.fmax(open_series, df_clean['Close']))
            df_clean['Low'] = np.fmin(df_clean['Low'], np.fmin(open_series, df_clean['Close']))
            df_clean['Low'] = df_clean['Low'].clip(lower=1e-4)

        return df_clean


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
            self._local.conn.execute("PRAGMA cache_size=-32000")  # 32MB page cache per thread
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA mmap_size=268435456") # 256MB memory mapped I/O
        return cast(sqlite3.Connection, self._local.conn)

    def _init_db(self):
        with self._write_lock:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")

                conn.execute("PRAGMA cache_size=-32000")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=268435456")
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

        # Pre-resolve column indices for ultra-fast itertuples extraction
        col_list = list(df.columns)
        lower_cols = [str(c).lower() for c in col_list]
        open_pos = lower_cols.index("open") if "open" in lower_cols else None
        high_pos = lower_cols.index("high") if "high" in lower_cols else None
        low_pos = lower_cols.index("low") if "low" in lower_cols else None
        close_pos = lower_cols.index("close") if "close" in lower_cols else None
        vol_pos = lower_cols.index("volume") if "volume" in lower_cols else None

        import math
        records = []
        for row in df.itertuples(index=True):
            idx = row[0]
            d_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            try:
                op = float(row[open_pos + 1]) if open_pos is not None else 0.0
                hi = float(row[high_pos + 1]) if high_pos is not None else 0.0
                lo = float(row[low_pos + 1]) if low_pos is not None else 0.0
                cl = float(row[close_pos + 1]) if close_pos is not None else 0.0
                vol_f = float(row[vol_pos + 1]) if vol_pos is not None else 0.0
                vol = int(vol_f) if math.isfinite(vol_f) and vol_f >= 0 else 0

                if not (math.isfinite(op) and math.isfinite(hi) and math.isfinite(lo) and math.isfinite(cl)):
                    continue
                if cl <= 0.0 or op <= 0.0 or hi <= 0.0 or lo <= 0.0:
                    continue
                # Enforce logical OHLC consistency (fix minor data feed rounding errors or skip corrupt rows)
                if hi < lo or op > hi or op < lo or cl > hi or cl < lo:
                    hi = max(hi, op, cl, lo)
                    lo = min(lo, op, cl, hi)
                    if hi <= 0.0 or lo <= 0.0 or hi < lo:
                        continue
            except (ValueError, TypeError, IndexError):
                continue
            records.append((symbol, d_str, op, hi, lo, cl, vol))
        if not records:
            return 0

        def _do_update():
            with self._write_lock:
                conn = self._get_conn()
                try:
                    conn.executemany("""
                        INSERT OR REPLACE INTO stock_prices
                        (symbol, date, open, high, low, close, volume, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, records)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        try:
            from src.data_layer.hybrid_storage import execute_sqlite_with_retry
            execute_sqlite_with_retry(_do_update)
        except (ImportError, ModuleNotFoundError):
            _do_update()

        count = len(records)
        self.logger.info(f"Upserted {count} price rows for {symbol}")
        return count

    @staticmethod
    def validate_and_clean_price_series(df: pd.DataFrame, max_daily_jump: float = 0.65) -> pd.DataFrame:
        """Delegate to DataValidator for backwards compatibility and clean SRP separation."""
        return DataValidator.validate_and_clean_price_series(df, max_daily_jump=max_daily_jump)

    def get_prices(self, symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """DB에서 주가 데이터 조회 (시계열 정렬된 DataFrame, 컬럼명 대문자, 이상치 자동 보정)"""
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
            df = self.validate_and_clean_price_series(df)
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

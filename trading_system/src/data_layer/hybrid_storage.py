"""
d:\\Finance\\code\\stock\\trading_system\\src\\data_layer\\hybrid_storage.py
Hybrid Parquet/SQLite High-Concurrency Storage Engine.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import logging
import random
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Absolute base dir for stock project
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def execute_sqlite_with_retry(
    fn: Callable[[], Any],
    max_retries: int = 10,
    base_delay: float = 0.05,
    max_delay: float = 0.5,
) -> Any:
    """
    Executes a database write callable with exponential backoff and random jitter,
    retrying transient sqlite3.OperationalError ("database is locked") to eliminate lock failures.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() or "busy" in str(e).lower():
                if attempt == max_retries - 1:
                    logger.error(f"SQLite write lock exhausted after {max_retries} retries: {e}")
                    raise e
                sleep_time = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.02)
                time.sleep(sleep_time)
            else:
                raise e


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes reset_index() column names so DatetimeIndex and date-like columns
    are consistently mapped to 'date', avoiding NaT parsing errors.
    """
    if df is None or df.empty:
        return df
    df_copy = df.copy()

    if isinstance(df_copy.index, pd.DatetimeIndex) or (df_copy.index.name and str(df_copy.index.name).lower() in ["date", "datetime", "index"]):
        df_copy = df_copy.reset_index()

    for col in list(df_copy.columns):
        col_str = str(col)
        if col_str.lower() in ["date", "datetime", "index"] and col_str != "date":
            df_copy = df_copy.rename(columns={col: "date"})
            break

    if "date" in df_copy.columns:
        df_copy["date"] = pd.to_datetime(df_copy["date"], errors="coerce")

    return df_copy


class ParquetWALBuffer:
    """
    Lock-free staging buffer for multi-asset price and indicator streaming.
    Workers write price updates into staging Parquet files (.wal_staging/<symbol>_<uuid>.parquet),
    completely bypassing SQLite database locks during multi-threaded downloads.
    """

    def __init__(self, staging_dir: Optional[Union[str, Path]] = None, master_dir: Optional[Union[str, Path]] = None):
        self.staging_dir = Path(staging_dir) if staging_dir else _PROJECT_ROOT / "data" / "wal_staging"
        self.master_dir = Path(master_dir) if master_dir else _PROJECT_ROOT / "data" / "store"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write_symbol_wal(self, symbol: str, df: pd.DataFrame) -> Path:
        """
        Writes a staging Parquet file for a symbol without acquiring database write locks.
        Returns path to created staging file.
        """
        if df.empty:
            return Path()
        clean_sym = symbol.replace("/", "_").replace("\\", "_")
        file_id = f"{clean_sym}_{uuid.uuid4().hex[:8]}.parquet"
        staging_path = self.staging_dir / file_id

        # Preserve index as date if DatetimeIndex
        df_copy = _normalize_date_column(df)
        df_copy.to_parquet(staging_path, compression="snappy", index=False)
        return staging_path

    def get_symbol_staging_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Reads and concatenates all un-flushed staging WAL files for a specific symbol."""
        clean_sym = symbol.replace("/", "_").replace("\\", "_")
        pattern = f"{clean_sym}_*.parquet"
        files = list(self.staging_dir.glob(pattern))
        if not files:
            return None

        dfs = []
        for f in files:
            try:
                raw_df = pd.read_parquet(f)
                dfs.append(_normalize_date_column(raw_df))
            except Exception as e:
                logger.warning(f"Error reading WAL file {f}: {e}")

        if not dfs:
            return None
        combined = pd.concat(dfs, ignore_index=True)

        if "date" in combined.columns:
            combined = combined.dropna(subset=["date"])
            combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")
            combined.set_index("date", inplace=True)
        return combined

    def flush_staging_to_master(self, db_callback: Optional[Callable[[str, pd.DataFrame], None]] = None) -> int:
        """
        Consolidates staging Parquet WAL files by symbol into master Parquet dataset
        and optionally calls db_callback (e.g. StockPriceDB.update_prices) in a batch transaction.
        Returns total number of staging files flushed.
        """
        files = list(self.staging_dir.glob("*.parquet"))
        if not files:
            return 0

        # Group staging files by symbol prefix
        symbol_files: Dict[str, List[Path]] = defaultdict(list)
        for f in files:
            sym_part = f.name.rsplit("_", 1)[0]
            symbol_files[sym_part].append(f)

        flushed_count = 0
        for sym_part, f_list in symbol_files.items():
            try:
                dfs = [_normalize_date_column(pd.read_parquet(fp)) for fp in f_list]
                combined = pd.concat(dfs, ignore_index=True)

                if "date" in combined.columns:
                    combined = combined.dropna(subset=["date"])
                    combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")
                    combined.set_index("date", inplace=True)

                # Save master parquet
                master_sym_path = self.master_dir / f"{sym_part}.parquet"
                if master_sym_path.exists():
                    existing = pd.read_parquet(master_sym_path)
                    if not existing.empty:
                        existing_norm = _normalize_date_column(existing)
                        combined_reset = _normalize_date_column(combined)
                        merged = pd.concat([existing_norm, combined_reset], ignore_index=True)
                        if "date" in merged.columns:
                            merged = merged.dropna(subset=["date"])
                            merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date")
                            merged.set_index("date", inplace=True)
                        combined = merged

                out_df = _normalize_date_column(combined)
                out_df.to_parquet(master_sym_path, compression="snappy", index=False)

                # Call optional SQLite callback in consolidated batch
                if db_callback:
                    db_callback(sym_part, combined)

                # Unlink staging files
                for fp in f_list:
                    try:
                        fp.unlink()
                    except Exception:
                        pass
                flushed_count += len(f_list)

            except Exception as e:
                logger.error(f"Error flushing WAL staging for {sym_part}: {e}")

        return flushed_count


class HybridDataEngine:
    """
    High-Concurrency Hybrid Parquet / SQLite Engine.
    Routes streaming asset updates through Parquet WAL buffers and thread-safe SQLite retry transactions.
    """

    def __init__(self, db_path: Optional[str] = None, staging_dir: Optional[str] = None):
        self.wal_buffer = ParquetWALBuffer(staging_dir=staging_dir)
        self.db_path = db_path or str(_PROJECT_ROOT / "stock_prices.db")

    def write_prices_async(self, symbol: str, df: pd.DataFrame) -> Path:
        """Thread-safe lock-free write to staging buffer."""
        return self.wal_buffer.write_symbol_wal(symbol, df)

    def flush_to_sqlite(self, db_instance) -> int:
        """Flushes staging WAL buffer directly to StockPriceDB using single-writer batch transaction."""
        def callback(sym: str, df: pd.DataFrame):
            db_instance.update_prices(sym, df)

        return self.wal_buffer.flush_staging_to_master(db_callback=callback)

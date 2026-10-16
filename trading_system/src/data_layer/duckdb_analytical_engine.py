"""
src/data_layer/duckdb_analytical_engine.py
DuckDB In-Process High-Frequency Analytical Engine & Parquet Lakehouse Query Provider (Feature F536).

Key Capabilities:
1. Ultra-fast in-process OLAP SQL query engine using DuckDB with zero-copy Arrow & Polars memory exchange.
2. Point-in-time AS OF joins for trade and quote streaming data, ensuring absolute zero lookahead bias.
3. Multi-market parallel OLAP aggregations (cross-sectional quintiles, sector rankings, median liquidity).
4. Hive-partitioned Parquet Lakehouse persistence & querying with predicate pushdown and projection pushdown.
5. Thread-safe connection management with support for in-memory and persistent catalog modes.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import pandas as pd

try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    _DUCKDB_AVAILABLE = False

try:
    import polars as pl
    _POLARS_AVAILABLE = True
except ImportError:
    pl = None
    _POLARS_AVAILABLE = False

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _ARROW_AVAILABLE = True
except ImportError:
    pa = None
    pq = None
    _ARROW_AVAILABLE = False

logger = logging.getLogger(__name__)


class DuckDBAnalyticalEngine:
    """
    In-process vectorized SQL OLAP engine for high-frequency market data querying,
    point-in-time AS OF joins, and Parquet Lakehouse access.
    """

    def __init__(self, db_path: str = ":memory:", threads: Optional[int] = None):
        self.db_path = db_path
        self.threads = threads or os.cpu_count() or 4
        self._lock = threading.Lock()
        
        if not _DUCKDB_AVAILABLE:
            logger.warning("DuckDBAnalyticalEngine: duckdb package not available.")
            self.conn = None
            return

        self.conn = duckdb.connect(database=self.db_path, read_only=False)
        self.conn.execute(f"PRAGMA threads={self.threads};")
        self.conn.execute("PRAGMA enable_progress_bar=false;")
        self.conn.execute("PRAGMA preserve_insertion_order=false;")

    @property
    def is_available(self) -> bool:
        return _DUCKDB_AVAILABLE and self.conn is not None

    def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        return_format: str = "polars",
    ) -> Union[pl.DataFrame, pd.DataFrame, pa.Table, List[tuple]]:
        """
        Executes a vectorized OLAP SQL query and returns result in requested format:
        'polars' (default), 'pandas', 'arrow', or 'tuples'.
        """
        if not self.is_available:
            raise RuntimeError("DuckDB connection is not available.")

        with self._lock:
            if params:
                rel = self.conn.execute(query, params)
            else:
                rel = self.conn.execute(query)

            fmt = return_format.lower()
            if fmt == "polars":
                if _POLARS_AVAILABLE and hasattr(rel, "pl"):
                    return rel.pl()
                elif hasattr(rel, "arrow"):
                    arrow_res = rel.arrow()
                    tbl = arrow_res.read_all() if hasattr(arrow_res, "read_all") else arrow_res
                    return pl.from_arrow(tbl) if _POLARS_AVAILABLE else tbl
                return rel.df()
            elif fmt == "pandas":
                return rel.df()
            elif fmt == "arrow":
                arrow_res = rel.arrow()
                return arrow_res.read_all() if hasattr(arrow_res, "read_all") else arrow_res
            else:
                return rel.fetchall()

    def register_dataframe(self, view_name: str, df: Union[pd.DataFrame, pl.DataFrame, pa.Table]) -> None:
        """Registers an in-memory DataFrame or Arrow Table as a virtual SQL view."""
        if not self.is_available:
            raise RuntimeError("DuckDB connection is not available.")

        with self._lock:
            if isinstance(df, pd.DataFrame):
                self.conn.register(view_name, df)
            elif _POLARS_AVAILABLE and isinstance(df, pl.DataFrame):
                self.conn.register(view_name, df.to_arrow())
            elif _ARROW_AVAILABLE and isinstance(df, pa.Table):
                self.conn.register(view_name, df)
            else:
                raise TypeError(f"Unsupported DataFrame type: {type(df)}")

    def unregister_view(self, view_name: str) -> None:
        """Unregisters an in-memory virtual view."""
        if not self.is_available:
            return
        with self._lock:
            try:
                self.conn.unregister(view_name)
            except Exception:
                pass

    def execute_pit_asof_join(
        self,
        trades_df: Union[pd.DataFrame, pl.DataFrame],
        quotes_df: Union[pd.DataFrame, pl.DataFrame],
        trade_time_col: str = "timestamp",
        quote_time_col: str = "timestamp",
        symbol_col: str = "symbol",
        tolerance_interval: Optional[str] = "INTERVAL 1 MINUTE",
        return_format: str = "polars",
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """
        Executes an exact Point-In-Time AS-OF Join between trades and quotes,
        strictly preventing any lookahead bias (trade_time >= quote_time).
        """
        self.register_dataframe("_t_trades", trades_df)
        self.register_dataframe("_t_quotes", quotes_df)

        tolerance_filter = ""
        if tolerance_interval:
            tolerance_filter = f"AND t.{trade_time_col} - q.{quote_time_col} <= {tolerance_interval}"

        sql = f"""
        SELECT 
            t.*,
            q.* EXCLUDE ({symbol_col})
        FROM _t_trades t
        ASOF JOIN _t_quotes q
            ON t.{symbol_col} = q.{symbol_col}
            AND t.{trade_time_col} >= q.{quote_time_col}
            {tolerance_filter}
        ORDER BY t.{trade_time_col}
        """
        try:
            res = self.execute_query(sql, return_format=return_format)
            return res
        finally:
            self.unregister_view("_t_trades")
            self.unregister_view("_t_quotes")

    def compute_cross_sectional_summary(
        self,
        df: Union[pd.DataFrame, pl.DataFrame],
        market_col: str = "market",
        price_col: str = "close",
        volume_col: str = "volume",
        return_format: str = "polars",
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """Calculates multi-market summary statistics (count, median price, total volume) via SQL."""
        self.register_dataframe("_t_cs_data", df)
        sql = f"""
        SELECT 
            {market_col},
            COUNT(*) as symbol_count,
            AVG({price_col}) as avg_price,
            MEDIAN({price_col}) as median_price,
            SUM({volume_col}) as total_volume,
            AVG({volume_col}) as avg_volume
        FROM _t_cs_data
        GROUP BY {market_col}
        ORDER BY symbol_count DESC
        """
        try:
            return self.execute_query(sql, return_format=return_format)
        finally:
            self.unregister_view("_t_cs_data")

    def query_top_n_ranked(
        self,
        df: Union[pd.DataFrame, pl.DataFrame],
        partition_col: str = "market",
        order_col: str = "score",
        top_n: int = 10,
        ascending: bool = False,
        return_format: str = "polars",
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """Extracts top N assets per market/sector partition using SQL window functions."""
        self.register_dataframe("_t_ranked", df)
        sort_dir = "ASC" if ascending else "DESC"
        sql = f"""
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY {partition_col} ORDER BY {order_col} {sort_dir}) as __rank__
            FROM _t_ranked
            WHERE {order_col} IS NOT NULL
        )
        SELECT * EXCLUDE (__rank__)
        FROM ranked
        WHERE __rank__ <= {top_n}
        ORDER BY {partition_col}, __rank__
        """
        try:
            return self.execute_query(sql, return_format=return_format)
        finally:
            self.unregister_view("_t_ranked")

    def save_to_parquet_lakehouse(
        self,
        df: Union[pd.DataFrame, pl.DataFrame],
        lakehouse_dir: Union[str, Path],
        table_name: str,
        partition_cols: Optional[List[str]] = None,
    ) -> Path:
        """
        Persists a dataset into a Hive-partitioned Snappy Parquet Lakehouse structure.
        """
        lakehouse_dir_path = Path(lakehouse_dir)
        lakehouse_dir_path.mkdir(parents=True, exist_ok=True)

        self.register_dataframe("_t_lake_in", df)
        if partition_cols:
            dest_target = lakehouse_dir_path / table_name
            dest_target.mkdir(parents=True, exist_ok=True)
            part_str = ", ".join(f"'{c}'" for c in partition_cols)
            partition_clause = f", PARTITION_BY ({part_str})"
        else:
            dest_target = lakehouse_dir_path / f"{table_name}.parquet"
            partition_clause = ""

        dest_glob = str(dest_target).replace("\\", "/")
        sql = f"""
        COPY _t_lake_in TO '{dest_glob}' (FORMAT PARQUET, COMPRESSION SNAPPY {partition_clause}, OVERWRITE_OR_IGNORE 1)
        """
        try:
            with self._lock:
                self.conn.execute(sql)
            logger.info(f"DuckDBAnalyticalEngine: Saved lakehouse table {table_name} to {dest_target}")
            return dest_target
        finally:
            self.unregister_view("_t_lake_in")

    def query_parquet_lakehouse(
        self,
        parquet_glob_or_path: Union[str, Path],
        where_clause: Optional[str] = None,
        columns: Optional[List[str]] = None,
        return_format: str = "polars",
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """
        Directly queries Parquet Lakehouse files with predicate and projection pushdown.
        """
        path_str = str(parquet_glob_or_path).replace("\\", "/")
        col_str = ", ".join(columns) if columns else "*"
        where_str = f"WHERE {where_clause}" if where_clause else ""

        sql = f"""
        SELECT {col_str}
        FROM read_parquet('{path_str}')
        {where_str}
        """
        return self.execute_query(sql, return_format=return_format)

    def close(self) -> None:
        """Closes the DuckDB connection."""
        with self._lock:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None

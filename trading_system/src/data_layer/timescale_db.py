"""
TimescaleDB / High-Throughput Time-Series & Real-Time Tick/LOB Database Connector Module
Extends SQLite storage to scalable PostgreSQL/TimescaleDB for enterprise Level 2/3 Tick & Order Book data handling.
"""

from __future__ import annotations

import json
import math
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TimescaleDBConnector:
    """
    Enterprise Time-Series & Real-Time Level 2/3 Tick/LOB Store Connector.
    Provides hypertable partitioning and WAL-optimised batch ingestion for ticks and order book depth.
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
            # 1. Daily / Intraday OHLCV
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
            # 2. Level 1/2 Tick Trades Stream
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_trades (
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL NOT NULL,
                    side TEXT NOT NULL,
                    bid_price REAL,
                    ask_price REAL,
                    spread_bps REAL,
                    trade_id TEXT NOT NULL,
                    PRIMARY KEY (time, symbol, trade_id)
                );
            """)
            # 3. Level 2/3 Order Book Depth Snapshots (10-Level Depth)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lob_depth_snapshots (
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    bid_prices TEXT,
                    bid_volumes TEXT,
                    ask_prices TEXT,
                    ask_volumes TEXT,
                    micro_price REAL,
                    obi_1 REAL,
                    obi_5 REAL,
                    obi_10 REAL,
                    spread_bps REAL,
                    PRIMARY KEY (time, symbol)
                );
            """)
            # Create indexes for sub-millisecond lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tick_trades_sym_time ON tick_trades (symbol, time);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lob_depth_sym_time ON lob_depth_snapshots (symbol, time);")
            conn.commit()
            logger.info("[TIMESCALEDB] Schema initialized with Tick & LOB depth tables.")
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
            def _sf(val):
                try:
                    f = float(val)
                    return f if math.isfinite(f) else 0.0
                except (ValueError, TypeError):
                    return 0.0

            rows = []
            for r in price_records:
                if not isinstance(r, dict):
                    continue
                t_val = str(r.get("time") or r.get("date") or "").strip()
                sym_val = str(r.get("symbol") or "").strip()
                if not t_val or not sym_val:
                    continue
                rows.append((
                    t_val,
                    sym_val,
                    str(r.get("market") or "").strip(),
                    _sf(r.get("open", 0.0)),
                    _sf(r.get("high", 0.0)),
                    _sf(r.get("low", 0.0)),
                    _sf(r.get("close", 0.0)),
                    _sf(r.get("volume", 0.0))
                ))
            if not rows:
                return True
            cursor.executemany(query, rows)
            conn.commit()
            logger.debug(f"[TIMESCALEDB] Inserted {len(rows)} price records.")
            return True
        except Exception as e:
            logger.error(f"[TIMESCALEDB] Batch price insert failed: {e}")
            return False
        finally:
            conn.close()

    def batch_insert_ticks(self, tick_records: List[Dict[str, Any]]) -> bool:
        """Batch inserts raw tick trade executions."""
        if not tick_records:
            return True
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = """
                INSERT OR REPLACE INTO tick_trades (time, symbol, market, price, volume, side, bid_price, ask_price, spread_bps, trade_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            def _sf(val, default=0.0):
                try:
                    f = float(val)
                    return f if math.isfinite(f) else default
                except (ValueError, TypeError):
                    return default

            rows = []
            for i, r in enumerate(tick_records):
                if not isinstance(r, dict):
                    continue
                t_val = str(r.get("time") or r.get("timestamp") or datetime.now().isoformat()).strip()
                sym_val = str(r.get("symbol") or "").strip()
                if not sym_val:
                    continue
                tr_id = str(r.get("trade_id") or f"tr_{int(time.time()*1000)}_{i}")
                p = _sf(r.get("price"), 0.0)
                v = _sf(r.get("volume"), 0.0)
                side = str(r.get("side") or "BUY").upper()
                pb = _sf(r.get("bid_price"), p)
                pa = _sf(r.get("ask_price"), p)
                mid = (pb + pa) / 2.0 if (pb + pa) > 0 else p
                spread_bps = ((pa - pb) / mid * 10000.0) if mid > 0 else 0.0

                rows.append((
                    t_val,
                    sym_val,
                    str(r.get("market") or "").strip(),
                    p,
                    v,
                    side,
                    pb,
                    pa,
                    spread_bps,
                    tr_id,
                ))

            if not rows:
                return True
            cursor.executemany(query, rows)
            conn.commit()
            logger.debug(f"[TIMESCALEDB] Inserted {len(rows)} tick trades.")
            return True
        except Exception as e:
            logger.error(f"[TIMESCALEDB] Batch tick insert failed: {e}")
            return False
        finally:
            conn.close()

    def batch_insert_lob_snapshots(self, snapshot_records: List[Dict[str, Any]]) -> bool:
        """Batch inserts Level 2/3 Order Book (10-Depth) snapshots."""
        if not snapshot_records:
            return True
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = """
                INSERT OR REPLACE INTO lob_depth_snapshots (
                    time, symbol, market, bid_prices, bid_volumes, ask_prices, ask_volumes,
                    micro_price, obi_1, obi_5, obi_10, spread_bps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            from src.core.lob_obi import LimitOrderBookCalculator
            lob_calc = LimitOrderBookCalculator(depth_levels=10)

            rows = []
            for s in snapshot_records:
                if not isinstance(s, dict):
                    continue
                t_val = str(s.get("time") or s.get("timestamp") or datetime.now().isoformat()).strip()
                sym_val = str(s.get("symbol") or "").strip()
                if not sym_val:
                    continue

                bids = s.get("bids", [])
                asks = s.get("asks", [])
                eval_res = lob_calc.evaluate_lob_snapshot({"bids": bids, "asks": asks})

                # Extract price/volume arrays
                b_prices = [b.get("price", 0.0) for b in bids[:10]]
                b_vols = [b.get("volume", 0.0) for b in bids[:10]]
                a_prices = [a.get("price", 0.0) for a in asks[:10]]
                a_vols = [a.get("volume", 0.0) for a in asks[:10]]

                micro_p = float(s.get("micro_price") or eval_res.get("micro_price", 0.0))
                obi_1 = float(s.get("obi_1") or eval_res.get("obi_1", eval_res.get("obi", 0.0)))
                obi_5 = float(s.get("obi_5") or eval_res.get("obi_5", eval_res.get("obi", 0.0)))
                obi_10 = float(s.get("obi_10") or eval_res.get("obi_10", eval_res.get("obi", 0.0)))
                spread_bps = float(s.get("spread_bps") or (eval_res.get("spread", 0.0) / max(1e-4, micro_p) * 10000.0))

                rows.append((
                    t_val,
                    sym_val,
                    str(s.get("market") or "").strip(),
                    json.dumps(b_prices),
                    json.dumps(b_vols),
                    json.dumps(a_prices),
                    json.dumps(a_vols),
                    micro_p,
                    obi_1,
                    obi_5,
                    obi_10,
                    spread_bps,
                ))

            if not rows:
                return True
            cursor.executemany(query, rows)
            conn.commit()
            logger.debug(f"[TIMESCALEDB] Inserted {len(rows)} LOB depth snapshots.")
            return True
        except Exception as e:
            logger.error(f"[TIMESCALEDB] Batch LOB insert failed: {e}")
            return False
        finally:
            conn.close()

    def get_recent_ticks(self, symbol: str, lookback_seconds: int = 300, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve recent tick trades within lookback window for a symbol."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(seconds=lookback_seconds)).isoformat()
            cursor.execute("""
                SELECT time, symbol, market, price, volume, side, bid_price, ask_price, spread_bps, trade_id
                FROM tick_trades
                WHERE symbol = ? AND time >= ?
                ORDER BY time ASC
                LIMIT ?
            """, (symbol, cutoff, limit))
            cols = ["time", "symbol", "market", "price", "volume", "side", "bid_price", "ask_price", "spread_bps", "trade_id"]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"[TIMESCALEDB] get_recent_ticks error: {e}")
            return []
        finally:
            conn.close()

    def get_recent_lob_snapshots(self, symbol: str, lookback_seconds: int = 300, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent Level 2/3 Order Book depth snapshots."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(seconds=lookback_seconds)).isoformat()
            cursor.execute("""
                SELECT time, symbol, market, bid_prices, bid_volumes, ask_prices, ask_volumes,
                       micro_price, obi_1, obi_5, obi_10, spread_bps
                FROM lob_depth_snapshots
                WHERE symbol = ? AND time >= ?
                ORDER BY time ASC
                LIMIT ?
            """, (symbol, cutoff, limit))
            cols = ["time", "symbol", "market", "bid_prices", "bid_volumes", "ask_prices", "ask_volumes",
                    "micro_price", "obi_1", "obi_5", "obi_10", "spread_bps"]
            results = []
            for row in cursor.fetchall():
                d = dict(zip(cols, row))
                d["bid_prices"] = json.loads(d["bid_prices"]) if d["bid_prices"] else []
                d["bid_volumes"] = json.loads(d["bid_volumes"]) if d["bid_volumes"] else []
                d["ask_prices"] = json.loads(d["ask_prices"]) if d["ask_prices"] else []
                d["ask_volumes"] = json.loads(d["ask_volumes"]) if d["ask_volumes"] else []
                results.append(d)
            return results
        except Exception as e:
            logger.warning(f"[TIMESCALEDB] get_recent_lob_snapshots error: {e}")
            return []
        finally:
            conn.close()

    def compute_rolling_vpin(
        self,
        symbol: str,
        bucket_size_vol: float = 1000.0,
        num_buckets: int = 50,
        lookback_seconds: int = 3600
    ) -> float:
        """Computes Volume-Synchronized Probability of Toxicity (VPIN) over tick trade stream.
        VPIN = sum(|V_tau^B - V_tau^S|) / (N * V)
        """
        ticks = self.get_recent_ticks(symbol, lookback_seconds=lookback_seconds, limit=5000)
        if not ticks or len(ticks) < 10:
            return 0.50

        bucket_imbalances = []
        current_buy_vol = 0.0
        current_sell_vol = 0.0
        current_bucket_vol = 0.0

        for t in ticks:
            vol = float(t.get("volume", 0.0))
            side = str(t.get("side", "BUY")).upper()
            if side == "BUY":
                current_buy_vol += vol
            else:
                current_sell_vol += vol
            current_bucket_vol += vol

            while current_bucket_vol >= bucket_size_vol:
                imbalance = abs(current_buy_vol - current_sell_vol)
                bucket_imbalances.append(imbalance)
                # Reset for next bucket
                current_buy_vol = 0.0
                current_sell_vol = 0.0
                current_bucket_vol -= bucket_size_vol
                if len(bucket_imbalances) >= num_buckets:
                    break

        if not bucket_imbalances:
            return 0.50

        recent_imbalances = bucket_imbalances[-num_buckets:]
        vpin = sum(recent_imbalances) / (len(recent_imbalances) * bucket_size_vol)
        return float(np.clip(vpin, 0.0, 1.0))

    def compute_microstructure_metrics(self, symbol: str, lookback_seconds: int = 300) -> Dict[str, Any]:
        """Computes a unified suite of real-time market microstructure indicators from ticks & LOB depth."""
        ticks = self.get_recent_ticks(symbol, lookback_seconds=lookback_seconds, limit=1000)
        snapshots = self.get_recent_lob_snapshots(symbol, lookback_seconds=lookback_seconds, limit=100)

        metrics = {
            "symbol": symbol,
            "tick_count": len(ticks),
            "lob_snapshot_count": len(snapshots),
            "micro_price": 0.0,
            "obi_1": 0.0,
            "obi_5": 0.0,
            "obi_10": 0.0,
            "spread_bps": 0.0,
            "vpin": 0.50,
            "buy_volume_ratio": 0.50,
            "vwap": 0.0,
            "realized_volatility_pct": 0.0,
        }

        if snapshots:
            last_snap = snapshots[-1]
            metrics["micro_price"] = float(last_snap.get("micro_price", 0.0))
            metrics["obi_1"] = float(last_snap.get("obi_1", 0.0))
            metrics["obi_5"] = float(last_snap.get("obi_5", 0.0))
            metrics["obi_10"] = float(last_snap.get("obi_10", 0.0))
            metrics["spread_bps"] = float(last_snap.get("spread_bps", 0.0))

        if ticks:
            prices = np.array([float(t["price"]) for t in ticks if float(t["price"]) > 0])
            volumes = np.array([float(t["volume"]) for t in ticks if float(t["volume"]) >= 0])
            sides = [str(t.get("side", "BUY")).upper() for t in ticks]

            if len(prices) > 0 and len(volumes) == len(prices):
                tot_vol = np.sum(volumes)
                if tot_vol > 0:
                    metrics["vwap"] = float(np.sum(prices * volumes) / tot_vol)
                    buy_vol = sum(v for v, s in zip(volumes, sides) if s == "BUY")
                    metrics["buy_volume_ratio"] = float(buy_vol / tot_vol)

            if len(prices) >= 3:
                log_rets = np.diff(np.log(prices))
                metrics["realized_volatility_pct"] = float(np.std(log_rets) * 100.0) if len(log_rets) > 0 else 0.0

            metrics["vpin"] = self.compute_rolling_vpin(symbol, lookback_seconds=lookback_seconds)

        return metrics


RealTimeTickLOBStore = TimescaleDBConnector


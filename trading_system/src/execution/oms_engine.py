"""
Execution & OMS Module:
- Order Plan Generation from Top Ensemble Predictions & Risk Parity Weights
- Slippage Tracking & Tracking Error Logging to SQLite DB (trade_logs.db)
"""

import re
import sqlite3
import datetime
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-^]*$")

# Conservative sanity bounds for order planning. Plans outside these are dropped:
# sub-KRW-100 / sub-USD-1 prices indicate missing or corrupted price data.
_MIN_PRICE_BOUND = 1.0
_MAX_PRICE_BOUND = 100_000_000.0


class ExecutionOMSEngine:
    """
    Order Management & Execution Engine for Stock Trading System.
    Generates actionable trade execution plans and monitors slippage and tracking error.
    """
    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_db(self):
        """Initializes trade_logs.db schema for order execution & tracking error monitoring."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_plans (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    market TEXT,
                    action TEXT NOT NULL,
                    target_weight REAL NOT NULL,
                    target_amount REAL NOT NULL,
                    target_price REAL NOT NULL,
                    quantity INTEGER,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # Migration: legacy DBs created before the quantity column
            try:
                cols = [r[1] for r in cursor.execute("PRAGMA table_info(order_plans)").fetchall()]
                if cols and "quantity" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN quantity INTEGER")
            except Exception:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    executed_price REAL NOT NULL,
                    slippage_bps REAL NOT NULL,
                    executed_volume INTEGER NOT NULL,
                    executed_at TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES order_plans(order_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _validate_symbol(self, sym: Any) -> str:
        """Returns a clean symbol string or empty string if the symbol is invalid."""
        if sym is None or not isinstance(sym, str):
            return ""
        clean_sym: str = sym.strip()
        if len(clean_sym) > 20 or len(clean_sym) < 1:
            return ""
        if "{" in clean_sym or ":" in clean_sym or "'" in clean_sym or '"' in clean_sym or " " in clean_sym:
            return ""
        if not _SYMBOL_RE.match(clean_sym):
            return ""
        return clean_sym

    def generate_order_plan(
        self,
        top_predictions: List[Dict[str, Any]],
        portfolio_weights: Dict[str, float],
        total_capital: float = 100000000.0,  # 100,000,000 KRW default
        crisis_level: str = "NORMAL",
    ) -> List[Dict[str, Any]]:
        """
        Generates actionable order execution plans based on predictions and Risk Parity weights.

        Safety gates (never disable these):
        - `crisis_level == "SEVERE"` blocks ALL order plan generation.
        - Kill switch (KILL_SWITCH file / KILL_SWITCH env / engage()) blocks ALL order plan generation.
        - Symbols failing `_validate_symbol` are skipped (protects against dict-string
          symbol corruption from upstream strategy outputs).
        - Plans without an explicit, in-bounds `close_price`/`target_price` are skipped
          (the old behavior of defaulting to price 1.0 is removed - it would generate
          meaningless orders if a broker ever consumes these rows).
        """
        order_plans: List[Dict[str, Any]] = []
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        from src.execution.kill_switch import is_kill_switch_active
        if is_kill_switch_active():
            logger.critical("[OMS ENGINE] KILL SWITCH ACTIVE - skipping ALL order plan generation.")
            return order_plans

        if str(crisis_level).upper() == "SEVERE":
            logger.warning("[OMS ENGINE] SEVERE crisis level - skipping ALL order plan generation.")
            return order_plans

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            for pred in top_predictions:
                if not isinstance(pred, dict):
                    continue

                sym = self._validate_symbol(pred.get("symbol"))
                if not sym:
                    continue

                weight = portfolio_weights.get(sym, 0.0)
                try:
                    weight = float(weight)
                except Exception:
                    continue
                if not (0.0 < weight <= 1.0):
                    continue

                target_amount = total_capital * weight
                if not (0.0 < target_amount <= total_capital):
                    continue

                close_price = pred.get("close_price")
                plan_price = pred.get("target_price")
                if close_price is None or close_price == "":
                    close_price = plan_price
                if close_price is None or close_price == "":
                    continue
                try:
                    target_price = float(close_price)
                except Exception:
                    continue
                if not (_MIN_PRICE_BOUND <= target_price <= _MAX_PRICE_BOUND):
                    continue

                order_id = f"ORD_{sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                action = "BUY"
                name = pred.get("name", "")
                market = pred.get("market", "")

                lot = 10 if market in ("KOSPI", "KOSDAQ", "KRX") else 1
                quantity = int(target_amount // target_price)
                if lot > 1:
                    quantity = (quantity // lot) * lot
                if quantity <= 0:
                    continue

                plan_entry = {
                    "order_id": order_id,
                    "symbol": sym,
                    "name": name,
                    "market": market,
                    "action": action,
                    "target_weight": round(weight, 4),
                    "target_amount": round(target_amount, 2),
                    "target_price": round(target_price, 2),
                    "quantity": quantity,
                    "status": "PENDING",
                    "created_at": now_str
                }
                order_plans.append(plan_entry)

                cursor.execute("""
                    INSERT OR REPLACE INTO order_plans
                    (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), quantity, "PENDING", now_str))

            conn.commit()
        finally:
            conn.close()
        return order_plans

    def record_execution(
        self,
        order_id: str,
        symbol: str,
        target_price: float,
        executed_price: float,
        executed_volume: int
    ) -> Dict[str, Any]:
        """
        Records trade execution and calculates real-time slippage in basis points (bps).
        """
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if target_price <= 0:
            slippage_bps = 0.0
        else:
            # Slippage in basis points (1 bps = 0.01%)
            slippage_bps = ((executed_price - target_price) / target_price) * 10000.0

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO execution_logs
                (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, symbol, target_price, executed_price, round(slippage_bps, 2), executed_volume, now_str))

            cursor.execute("""
                UPDATE order_plans SET status = 'EXECUTED' WHERE order_id = ?
            """, (order_id,))

            conn.commit()
        finally:
            conn.close()

        return {
            "order_id": order_id,
            "symbol": symbol,
            "slippage_bps": round(slippage_bps, 2),
            "executed_price": executed_price,
            "executed_volume": executed_volume,
            "executed_at": now_str
        }


# Module level alias for backward compatibility
OMSEngine = ExecutionOMSEngine

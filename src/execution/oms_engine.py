"""
Execution & OMS Module:
- Order Plan Generation from Top Ensemble Predictions & Risk Parity Weights
- Slippage Tracking & Tracking Error Logging to SQLite DB (trade_logs.db)
"""

import os
import sqlite3
import datetime
from typing import Dict, List, Any, Optional

class ExecutionOMSEngine:
    """
    Order Management & Execution Engine for Stock Trading System.
    Generates actionable trade execution plans and monitors slippage and tracking error.
    """
    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes trade_logs.db schema for order execution & tracking error monitoring."""
        conn = sqlite3.connect(self.db_path)
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
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
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
                FOREIGN KEY (order_id) REFERENCES order_plans (order_id)
            )
        """)
        conn.commit()
        conn.close()

    def generate_order_plan(
        self,
        top_predictions: List[Dict[str, Any]],
        portfolio_weights: Dict[str, float],
        total_capital: float = 100000000.0  # 100,000,000 KRW default
    ) -> List[Dict[str, Any]]:
        """
        Generates actionable order execution plans based on predictions and Risk Parity weights.
        """
        order_plans = []
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for pred in top_predictions:
            sym = pred.get("symbol")
            if not sym:
                continue
            
            weight = portfolio_weights.get(sym, 0.0)
            if weight <= 0.0:
                continue

            target_amount = total_capital * weight
            target_price = float(pred.get("close_price", pred.get("target_price", 1.0)))
            if target_price <= 0:
                target_price = 1.0

            order_id = f"ORD_{sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
            action = "BUY"
            name = pred.get("name", "")
            market = pred.get("market", "")

            plan_entry = {
                "order_id": order_id,
                "symbol": sym,
                "name": name,
                "market": market,
                "action": action,
                "target_weight": round(weight, 4),
                "target_amount": round(target_amount, 2),
                "target_price": round(target_price, 2),
                "status": "PENDING",
                "created_at": now_str
            }
            order_plans.append(plan_entry)

            cursor.execute("""
                INSERT OR REPLACE INTO order_plans 
                (order_id, symbol, name, market, action, target_weight, target_amount, target_price, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), "PENDING", now_str))

        conn.commit()
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

        conn = sqlite3.connect(self.db_path)
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
        conn.close()

        return {
            "order_id": order_id,
            "symbol": symbol,
            "slippage_bps": round(slippage_bps, 2),
            "executed_price": executed_price,
            "executed_volume": executed_volume,
            "executed_at": now_str
        }

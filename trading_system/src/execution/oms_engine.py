"""
Execution & OMS Module:
- Order Plan Generation from Top Ensemble Predictions & Risk Parity Weights
- Slippage Tracking & Tracking Error Logging to SQLite DB (trade_logs.db)
"""

import re
import math
import sqlite3
import datetime
import logging
import numpy as np
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
        self.db_path = str(db_path) if db_path is not None else "trade_logs.db"
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
                    execution_strategy TEXT DEFAULT 'DIRECT',
                    slice_count INTEGER DEFAULT 1,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # Migration: legacy DBs created before the quantity/execution columns
            try:
                cols = [r[1] for r in cursor.execute("PRAGMA table_info(order_plans)").fetchall()]
                if cols and "quantity" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN quantity INTEGER")
                if cols and "execution_strategy" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN execution_strategy TEXT DEFAULT 'DIRECT'")
                if cols and "slice_count" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN slice_count INTEGER DEFAULT 1")
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

        if total_capital is None or total_capital == 100000000.0:
            try:
                from src.config import TradingConfig
                cfg_inst = TradingConfig()
                cfg_cap = getattr(cfg_inst, "portfolio_capital_krw", None)
                if cfg_cap and math.isfinite(float(cfg_cap)) and float(cfg_cap) > 0:
                    total_capital = float(cfg_cap)
            except Exception:
                pass

        try:
            tot_cap = float(total_capital) if (total_capital is not None and math.isfinite(float(total_capital))) else 100000000.0
        except (ValueError, TypeError):
            tot_cap = 100000000.0
        tot_cap = max(0.0, tot_cap)

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            for pred in top_predictions:
                if not isinstance(pred, dict):
                    continue

                sym = self._validate_symbol(pred.get("symbol"))
                if not sym:
                    continue

                weight_raw = portfolio_weights.get(sym, 0.0)
                try:
                    weight = float(weight_raw) if (weight_raw is not None and math.isfinite(float(weight_raw))) else 0.0
                except (ValueError, TypeError):
                    continue
                if not (0.0 < weight <= 1.0):
                    continue

                target_amount = tot_cap * weight
                if not (0.0 < target_amount <= tot_cap):
                    continue

                close_price = pred.get("close_price")
                plan_price = pred.get("target_price")
                if close_price is None or close_price == "":
                    close_price = plan_price
                if close_price is None or close_price == "":
                    continue
                try:
                    f_price = float(close_price)
                    target_price = f_price if math.isfinite(f_price) else 0.0
                except (ValueError, TypeError):
                    continue
                if not (_MIN_PRICE_BOUND <= target_price <= _MAX_PRICE_BOUND):
                    continue

                order_id = f"ORD_{sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                raw_action = str(pred.get("action", "BUY") or "BUY").upper()
                name = str(pred.get("name", "") or "")
                market = str(pred.get("market", "") or "")
                is_krx = str(market).upper() in ["KOSPI", "KOSDAQ"] or sym.isdigit() or sym.endswith((".KS", ".KQ"))

                # Gate 7.1: KRX Long-Only Synthetic Short / Cash Overlay Filter
                if is_krx and raw_action in ["SELL_SHORT", "SHORT"]:
                    action = "CASH_OVERLAY"
                    status = "HEDGE_FLAG"
                else:
                    action = "BUY"
                    status = "PENDING"

                # Gate 7.2: KRX Upper Limit Lock (±30% Price Limit Gate)
                change_pct = pred.get("change_pct") or pred.get("daily_return")
                try:
                    if change_pct is not None and float(change_pct) >= 0.295 and action == "BUY":
                        logger.warning(f"[OMS GATE 7] {sym} locked at upper limit (+{float(change_pct):.2%}), skipping buy.")
                        continue
                except (ValueError, TypeError):
                    pass

                # Gate 7.3: KRX STT / Transaction Cost Net Alpha Hurdle Check
                if is_krx and action == "BUY" and ("expected_return" in pred or "ensemble_expected_return" in pred):
                    try:
                        from src.risk.portfolio_allocator import PortfolioAllocator
                        allocator = PortfolioAllocator()
                        adv_val = float(pred.get("adv", pred.get("trading_value", 1_000_000_000.0)) or 1_000_000_000.0)
                        vol_val = float(pred.get("volatility_20d", 0.02) or 0.02)
                        friction_cost = allocator.estimate_transaction_cost_rate(
                            symbol=sym,
                            market=market or "KOSPI",
                            target_weight=weight,
                            portfolio_value=tot_cap,
                            volatility_20d=vol_val,
                            adv=adv_val,
                            is_sell=False
                        )
                        raw_exp_ret = float(pred.get("expected_return", pred.get("ensemble_expected_return", 0.0)) or 0.0)
                        exp_ret_frac = raw_exp_ret / 100.0
                        safety_margin = 0.0010  # 0.10% safety margin
                        if exp_ret_frac < (friction_cost + safety_margin):
                            logger.info(f"[OMS GATE 7] {sym} net alpha {exp_ret_frac:.4%} < hurdle ({friction_cost:.4%}), skipping.")
                            continue
                    except Exception as _fe:
                        logger.debug(f"[OMS GATE 7] Hurdle check exception for {sym}: {_fe}")

                raw_quantity = int(target_amount // target_price)
                if is_krx:
                    quantity = (raw_quantity // 10) * 10 if raw_quantity >= 10 else raw_quantity
                else:
                    quantity = raw_quantity
                if quantity <= 0 and status != "HEDGE_FLAG":
                    continue

                # Institutional Execution Strategy Routing (ADV Participation Slicing)
                adv_val = float(pred.get("adv", pred.get("trading_value", 1_000_000_000.0)) or 1_000_000_000.0)
                part_ratio = target_amount / max(adv_val, 1.0)
                if part_ratio > 0.03:
                    exec_strategy = "VWAP"
                    slice_count = min(10, max(3, int(np.ceil(part_ratio / 0.01))))
                elif part_ratio > 0.01:
                    exec_strategy = "TWAP"
                    slice_count = min(5, max(2, int(np.ceil(part_ratio / 0.005))))
                else:
                    exec_strategy = "DIRECT"
                    slice_count = 1

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
                    "execution_strategy": exec_strategy,
                    "slice_count": slice_count,
                    "status": status,
                    "created_at": now_str
                }
                order_plans.append(plan_entry)

                cursor.execute("""
                    INSERT OR REPLACE INTO order_plans
                    (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), quantity, exec_strategy, slice_count, status, now_str))

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
        try:
            pt = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 0.0
            pe = float(executed_price) if (executed_price is not None and math.isfinite(float(executed_price))) else 0.0
        except (ValueError, TypeError):
            pt, pe = 0.0, 0.0

        if pt <= 0:
            slippage_bps = 0.0
        else:
            # Slippage in basis points (1 bps = 0.01%)
            raw_slip = ((pe - pt) / pt) * 10000.0
            slippage_bps = raw_slip if math.isfinite(raw_slip) else 0.0

        q_vol = max(0, int(executed_volume)) if executed_volume is not None else 0

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO execution_logs
                (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, symbol, pt, pe, round(slippage_bps, 2), q_vol, now_str))

            # Calculate total executed volume so far for this order
            cursor.execute("""
                SELECT COALESCE(SUM(executed_volume), 0) FROM execution_logs WHERE order_id = ?
            """, (order_id,))
            total_executed = cursor.execute("SELECT COALESCE(SUM(executed_volume), 0) FROM execution_logs WHERE order_id = ?", (order_id,)).fetchone()[0]

            # Fetch target quantity from order_plans
            row = cursor.execute("SELECT quantity FROM order_plans WHERE order_id = ?", (order_id,)).fetchone()
            target_qty = row[0] if row and row[0] is not None else 0

            if target_qty > 0 and total_executed < target_qty:
                new_status = 'PARTIALLY_FILLED'
            else:
                new_status = 'EXECUTED'

            cursor.execute("""
                UPDATE order_plans SET status = ? WHERE order_id = ?
            """, (new_status, order_id))

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

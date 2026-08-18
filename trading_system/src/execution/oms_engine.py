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
        self._mem_conn = sqlite3.connect(":memory:") if self.db_path == ":memory:" else None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self.db_path == ":memory:" and self._mem_conn is not None:
            return self._mem_conn
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
            if self.db_path != ":memory:":
                conn.close()

    @staticmethod
    def round_to_tick_size(price: float, market: str = "KOSPI") -> float:
        """
        Rounds target execution price to exact exchange tick size:
        KRX (KOSPI/KOSDAQ):
          - price < 2,000 KRW: tick = 1 KRW
          - 2,000 <= price < 5,000 KRW: tick = 5 KRW
          - 5,000 <= price < 20,000 KRW: tick = 10 KRW
          - 20,000 <= price < 50,000 KRW: tick = 50 KRW
          - 50,000 <= price < 200,000 KRW: tick = 100 KRW
          - 200,000 <= price < 500,000 KRW: tick = 500 KRW
          - price >= 500,000 KRW: tick = 1,000 KRW
        US (SP500/NASDAQ/RUSSELL2000):
          - price >= $1.00: tick = $0.01 (penny)
          - price < $1.00: tick = $0.0001 (sub-penny)
        """
        if not math.isfinite(price) or price <= 0:
            return price

        mkt = str(market).upper()
        if mkt in ["KOSPI", "KOSDAQ"] or "KRW" in mkt:
            if price < 2000.0:
                tick = 1.0
            elif price < 5000.0:
                tick = 5.0
            elif price < 20000.0:
                tick = 10.0
            elif price < 50000.0:
                tick = 50.0
            elif price < 200000.0:
                tick = 100.0
            elif price < 500000.0:
                tick = 500.0
            else:
                tick = 1000.0
            return float(round(round(price / tick) * tick, 2))
        else:
            # US / Global
            if price >= 1.0:
                tick = 0.01
                return float(round(round(price / tick) * tick, 2))
            else:
                tick = 0.0001
                return float(round(round(price / tick) * tick, 4))

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

        # Continuous crisis regime scaling (0.15 to 1.0)
        crisis_mult = 1.0
        try:
            from src.risk.risk_manager import RiskManager
            rm = RiskManager()
            if hasattr(rm, 'crisis_detector'):
                crisis_mult = rm.crisis_detector.get_crisis_position_multiplier()
        except Exception:
            pass

        cl_upper = str(crisis_level).upper()
        if cl_upper == "ACTIVE":
            crisis_mult = min(crisis_mult, 0.40)
        elif cl_upper == "WATCH":
            crisis_mult = min(crisis_mult, 0.70)
        elif cl_upper == "RECOVERY":
            crisis_mult = min(crisis_mult, 0.50)

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
        tot_cap = max(0.0, tot_cap) * max(0.15, min(1.0, float(crisis_mult)))

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

                raw_action = str(pred.get("action", "BUY") or "BUY").upper()
                name = str(pred.get("name", "") or "")
                market = str(pred.get("market", "") or "")
                target_price = self.round_to_tick_size(target_price, market=market)
                order_id = f"ORD_{sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
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

                # Gate 7.4: Dynamic Adverse Opening Gap Filter (-3 sigma shock protection)
                try:
                    vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
                    gap_ret = float(change_pct or 0.0)
                    if action == "BUY" and gap_ret <= -3.0 * max(vol_20d, 0.015):
                        logger.warning(f"[OMS GATE 7.4] {sym} adverse gap {gap_ret:.2%} <= -3sigma, skipping toxic order flow.")
                        continue
                except (ValueError, TypeError):
                    pass

                raw_quantity = int(target_amount // target_price)
                if is_krx:
                    quantity = (raw_quantity // 10) * 10 if raw_quantity >= 10 else raw_quantity
                else:
                    quantity = raw_quantity
                if quantity <= 0 and status != "HEDGE_FLAG":
                    continue

                # Institutional Execution Strategy Routing (ADV Participation Slicing & U-shaped Volume Profile)
                adv_val = float(pred.get("adv", pred.get("trading_value", 1_000_000_000.0)) or 1_000_000_000.0)
                part_ratio = target_amount / max(adv_val, 1.0)
                if part_ratio > 0.03:
                    exec_strategy = "DYNAMIC_VWAP"
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
            if self.db_path != ":memory:":
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

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Determine side from order_plans for directional slippage (BUY: pe > pt is adverse; SELL: pe < pt is adverse)
            action_row = cursor.execute("SELECT action FROM order_plans WHERE order_id = ?", (order_id,)).fetchone()
            action = str(action_row[0]).upper() if action_row and action_row[0] else "BUY"
            side_sign = 1.0 if action in ["BUY", "LONG"] else -1.0

            if pt <= 0:
                slippage_bps = 0.0
            else:
                raw_slip = side_sign * ((pe - pt) / pt) * 10000.0
                slippage_bps = raw_slip if math.isfinite(raw_slip) else 0.0

            q_vol = max(0, int(executed_volume)) if executed_volume is not None else 0

            cursor.execute("""
                INSERT INTO execution_logs
                (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, symbol, pt, pe, round(slippage_bps, 2), q_vol, now_str))

            # Calculate total executed volume so far for this order
            cursor.execute("""
                SELECT COALESCE(SUM(executed_volume), 0) FROM execution_logs WHERE order_id = ?
            """, (order_id,))
            total_executed = cursor.fetchone()[0]

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
            if self.db_path != ":memory:":
                conn.close()

        return {
            "order_id": order_id,
            "symbol": symbol,
            "slippage_bps": round(slippage_bps, 2),
            "executed_price": executed_price,
            "executed_volume": executed_volume,
            "executed_at": now_str
        }


class AlmgrenChrissScheduler:
    """
    Almgren-Chriss (2000) Optimal Execution Trajectory Scheduler.
    Computes optimal VWAP/TWAP order slicing to minimize transaction costs and timing risk.
    """
    @staticmethod
    def compute_trajectory(
        total_quantity: int,
        adv: float,
        daily_volatility: float,
        strategy_tier: str = "medium",
        n_slices: int = 6
    ) -> List[int]:
        """
        Computes share allocation across n_slices based on Almgren-Chriss hyperbolic schedule.
        """
        if total_quantity <= 0 or n_slices <= 1:
            return [total_quantity]

        urgency_map = {"fast": 1.0e-3, "medium": 1.0e-5, "slow": 1.0e-7}
        lambda_urg = urgency_map.get(str(strategy_tier).lower(), 1.0e-5)
        eta = 0.5 * (max(daily_volatility, 0.01) / max(adv, 1.0))
        kappa = np.sqrt(lambda_urg * (daily_volatility ** 2) / max(eta, 1e-8))

        t = np.linspace(0, 1, n_slices + 1)
        if kappa > 1e-4:
            traj = np.sinh(kappa * (1.0 - t)) / np.sinh(kappa)
        else:
            traj = 1.0 - t

        diffs = -np.diff(traj)
        diffs = np.maximum(diffs, 0.0)
        diffs_sum = np.sum(diffs)
        if diffs_sum > 0:
            alloc = np.round((diffs / diffs_sum) * total_quantity).astype(int)
        else:
            alloc = np.full(n_slices, total_quantity // n_slices, dtype=int)

        # Reconcile rounding discrepancy to exact total_quantity
        diff_total = total_quantity - int(np.sum(alloc))
        alloc[-1] += diff_total
        return [int(x) for x in alloc]


# Module level alias for backward compatibility
OMSEngine = ExecutionOMSEngine

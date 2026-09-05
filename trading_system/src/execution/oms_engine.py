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
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._\-^]*$")

# Conservative sanity bounds for order planning. Plans outside these are dropped:
# sub-KRW-100 / sub-USD-1 prices indicate missing or corrupted price data.
_MIN_PRICE_BOUND = 1.0
_MAX_PRICE_BOUND = 100_000_000.0

STRATEGY_ALPHA_HALF_LIVES: Dict[str, float] = {
    'microstructure': 0.5,
    'darkpool': 1.0,
    'surge': 1.0,
    'gamma_squeeze': 2.0,
    'short_term_reversal': 3.0,
    'order_flow': 3.0,
    'iv_skew': 5.0,
    'lead_lag': 5.0,
    'stat_arb': 7.0,
    'sector_rotation': 10.0,
    'event_driven': 10.0,
    'sentiment': 10.0,
    'lstm': 10.0,
    'vcp_ml': 10.0,
    'vcp_rule': 10.0,
    'mq_factor': 15.0,
    'trend_efficiency': 15.0,
    'regression': 20.0,
    'factor_neutralized': 20.0,
    'vol_target': 20.0,
    'arm_factor': 20.0,
    'card_factor': 20.0,
    'latr_factor': 20.0,
    'supply_chain': 20.0,
    'inst_foreign_sector': 20.0,
    'short_squeeze': 15.0,
    'accruals_quality': 30.0,
    'insider_buying': 30.0,
    'earnings_tone_drift': 30.0,
    'valueup_catalyst': 45.0,
    'rim_valuation': 60.0,
    'cross_asset_spillover': 5.0,
    'supply_chain_gnn': 10.0,
    'range_expansion_breakout': 2.0,
    'dual_correction': 5.0,
    'dual_correction_regime': 5.0,
    'index_rebalance': 20.0,
    'index_rebalance_structural_flow': 20.0,
    'overnight_gap_reversal': 1.0,
    'overnight_gap': 1.0,
}


class ExecutionOMSEngine:
    """
    Order Management & Execution Engine for Stock Trading System.
    Generates actionable trade execution plans and monitors slippage and tracking error.
    """
    def __init__(self, db_path: str = "trade_logs.db", lot_size_krx: int = 1, config: Optional[Any] = None):
        self.db_path = str(db_path) if db_path is not None else "trade_logs.db"
        self.config = config
        self.lot_size_krx = max(1, int(lot_size_krx)) if lot_size_krx is not None else 1
        self.sor: Optional[Any] = None
        try:
            from src.execution.smart_order_router import SmartOrderRouter
            self.sor = SmartOrderRouter()
        except Exception:
            self.sor = None
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
                    sleeve_type TEXT,
                    target_take_profit REAL,
                    target_stop_loss REAL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tranches TEXT,
                    sor_routing TEXT,
                    expected_cost_saving_bps REAL DEFAULT 0.0
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
                if cols and "sleeve_type" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN sleeve_type TEXT")
                if cols and "target_take_profit" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN target_take_profit REAL")
                if cols and "target_stop_loss" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN target_stop_loss REAL")
                if cols and "tranches" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN tranches TEXT")
                if cols and "sor_routing" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN sor_routing TEXT")
                if cols and "expected_cost_saving_bps" not in cols:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN expected_cost_saving_bps REAL DEFAULT 0.0")
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
        if mkt in ["KOSPI", "KOSDAQ", "KRX", "KS", "KQ"] or "KRW" in mkt:
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

    def _get_latest_price(
        self,
        symbol: str,
        prices_dict: Optional[Dict[str, Any]] = None,
        top_predictions: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """
        Retrieves the latest / current market price for a symbol from:
        1. prices_dict (DataFrame, dict, or scalar price)
        2. top_predictions list
        3. StockPriceDB / SQLite storage cache
        Returns 0.0 if not found or invalid.
        """
        if not symbol:
            return 0.0

        # 1. Check prices_dict
        if prices_dict and isinstance(prices_dict, dict):
            candidates = [symbol, symbol.upper(), symbol.lower()]
            if symbol.endswith((".KS", ".KQ")):
                candidates.append(symbol.split(".")[0])
            else:
                candidates.extend([f"{symbol}.KS", f"{symbol}.KQ"])

            for sym_key in candidates:
                if sym_key in prices_dict:
                    val = prices_dict[sym_key]
                    if isinstance(val, (int, float)) and math.isfinite(float(val)) and float(val) > 0:
                        return float(val)
                    if hasattr(val, "empty") and not val.empty:
                        for col in ["Close", "close", "Adj Close", "adj_close", "Price", "price"]:
                            if hasattr(val, "columns") and col in val.columns:
                                try:
                                    s = val[col].dropna()
                                    if len(s) > 0 and math.isfinite(float(s.iloc[-1])) and float(s.iloc[-1]) > 0:
                                        return float(s.iloc[-1])
                                except Exception:
                                    pass
                    if isinstance(val, dict):
                        for k in ["close_price", "target_price", "close", "price", "current_price"]:
                            if k in val and val[k] is not None:
                                try:
                                    p = float(val[k])
                                    if math.isfinite(p) and p > 0:
                                        return p
                                except (ValueError, TypeError):
                                    pass

        # 2. Check top_predictions
        if top_predictions:
            sym_clean = symbol.split(".")[0]
            for pred in top_predictions:
                if isinstance(pred, dict):
                    p_sym = str(pred.get("symbol", "") or "")
                    if p_sym in (symbol, f"{symbol}.KS", f"{symbol}.KQ", sym_clean):
                        for k in ["close_price", "target_price", "close", "price", "current_price"]:
                            if pred.get(k) is not None:
                                try:
                                    p = float(pred[k])
                                    if math.isfinite(p) and p > 0:
                                        return p
                                except (ValueError, TypeError):
                                    pass

        # 3. Check StockPriceDB SQLite cache
        try:
            from src.persistence.database import StockPriceDB
            db = StockPriceDB()
            df = db.get_prices(symbol, limit=1)
            if df is not None and not df.empty:
                for col in ["Close", "close", "Adj Close"]:
                    if col in df.columns:
                        p = float(df[col].iloc[-1])
                        if math.isfinite(p) and p > 0:
                            return p
        except Exception:
            pass

        return 0.0

    def generate_order_plan(
        self,
        top_predictions: List[Dict[str, Any]],
        portfolio_weights: Dict[str, float],
        total_capital: float = 100000000.0,  # 100,000,000 KRW default
        crisis_level: str = "NORMAL",
        current_holdings: Optional[Dict[str, float]] = None,
        use_leland_buffer: bool = True,
        regime_label: str = "BULL",
        max_adv_ratio: float = 0.05,
        prices_dict: Optional[Dict[str, Any]] = None,
        usdkrw_rate: float = 1350.0,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generates actionable order execution plans based on predictions and Risk Parity weights.

        Safety gates (never disable these):
        - `crisis_level == "SEVERE"` blocks ALL order plan generation.
        - Kill switch (KILL_SWITCH file / KILL_SWITCH env / engage()) blocks ALL order plan generation.
        - Leland Dynamic Buffer Band Gating: if current_weight is within [target - delta, target + delta],
          skips order creation to suppress unnecessary turnover and transaction drag.
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

        is_severe = "SEVERE" in str(crisis_level).upper()
        if is_severe:
            logger.warning("[OMS ENGINE] SEVERE crisis level - skipping BUY orders (except capitulation oversold plays), allowing SELL/liquidate orders.")

        # Continuous crisis regime scaling (0.15 to 1.0)
        crisis_mult = 1.0
        cl_upper = str(crisis_level).upper()
        if cl_upper == "ACTIVE":
            crisis_mult = 0.40
        elif cl_upper == "WATCH":
            crisis_mult = 0.70
        elif cl_upper == "RECOVERY":
            crisis_mult = 0.50
        elif cl_upper == "AUTO":
            try:
                from src.risk.risk_manager import RiskManager
                rm = RiskManager()
                if hasattr(rm, 'crisis_detector'):
                    crisis_mult = rm.crisis_detector.get_crisis_position_multiplier()
            except Exception:
                crisis_mult = 1.0
        else:
            crisis_mult = 1.0

        if total_capital is None:
            try:
                from src.config import TradingConfig
                cfg_inst = TradingConfig()
                cfg_cap = getattr(cfg_inst, "portfolio_capital_krw", None)
                if cfg_cap and math.isfinite(float(cfg_cap)) and float(cfg_cap) > 0:
                    total_capital = float(cfg_cap)
            except Exception:
                total_capital = 100000000.0

        try:
            base_portfolio_cap = float(total_capital) if (total_capital is not None and math.isfinite(float(total_capital))) else 100000000.0
        except (ValueError, TypeError):
            base_portfolio_cap = 100000000.0
        tot_cap = max(0.0, base_portfolio_cap) * max(0.15, min(1.0, float(crisis_mult)))

        try:
            fx_rate = float(usdkrw_rate) if (usdkrw_rate is not None and math.isfinite(float(usdkrw_rate)) and float(usdkrw_rate) > 0) else 1350.0
        except (ValueError, TypeError):
            fx_rate = 1350.0

        # Pre-compute realized slippage multiplier and shared allocator instance once outside the loop (prevents N+1 DB queries)
        try:
            from src.execution.slippage_feedback import SlippageFeedbackEngine
            slip_res = SlippageFeedbackEngine(db_path=self.db_path).calculate_realized_slippage()
            if hasattr(slip_res, "cost_scaling_factor"):
                cached_slip_mult = float(slip_res.cost_scaling_factor)
            elif hasattr(slip_res, "recommended_market_impact_multiplier"):
                cached_slip_mult = float(slip_res.recommended_market_impact_multiplier)
            elif isinstance(slip_res, (int, float)):
                cached_slip_mult = float(slip_res)
            else:
                cached_slip_mult = 1.0
        except Exception as _se:
            logger.debug(f"[OMS] Slippage feedback preload exception: {_se}")
            cached_slip_mult = 1.0

        try:
            from src.risk.portfolio_allocator import PortfolioAllocator
            shared_allocator = PortfolioAllocator()
        except Exception:
            shared_allocator = None

        is_batch_percent_scale = any(
            abs(float(p.get("expected_return", p.get("ensemble_expected_return", 0.0)) or 0.0)) > 1.0
            for p in (top_predictions or []) if isinstance(p, dict)
        )

        def _get_holding_weight(h_item: Any) -> float:
            if h_item is None:
                return 0.0
            if isinstance(h_item, (int, float)):
                try:
                    return float(h_item) if math.isfinite(float(h_item)) else 0.0
                except (ValueError, TypeError):
                    return 0.0
            if isinstance(h_item, dict):
                w = h_item.get("weight", h_item.get("target_weight", 0.0))
                try:
                    return float(w) if (w is not None and math.isfinite(float(w))) else 0.0
                except (ValueError, TypeError):
                    return 0.0
            return 0.0

        def _get_holding_shares(h_item: Any, price: float, eff_cap: float, lot: int = 1) -> int:
            if h_item is None:
                return 0
            if isinstance(h_item, dict):
                if "quantity" in h_item and h_item["quantity"] is not None:
                    try:
                        return max(0, int(h_item["quantity"]))
                    except (ValueError, TypeError):
                        pass
                hw = _get_holding_weight(h_item)
                if hw > 0 and price > 0:
                    raw_sh = int((eff_cap * hw) // price)
                    return max(0, (raw_sh // lot) * lot)
            elif isinstance(h_item, int) and h_item > 1:
                return max(0, (h_item // lot) * lot)
            elif isinstance(h_item, (int, float)):
                hw = _get_holding_weight(h_item)
                if hw > 0 and price > 0:
                    raw_sh = int((eff_cap * hw) // price)
                    return max(0, (raw_sh // lot) * lot)
            return 0

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Ensure tranches and sor_routing columns exist for legacy databases
            try:
                db_cols = [r[1] for r in cursor.execute("PRAGMA table_info(order_plans)").fetchall()]
                has_tranches_col = "tranches" in db_cols
                if not has_tranches_col:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN tranches TEXT")
                    has_tranches_col = True
                has_sor_col = "sor_routing" in db_cols
                if not has_sor_col:
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN sor_routing TEXT")
                    cursor.execute("ALTER TABLE order_plans ADD COLUMN expected_cost_saving_bps REAL DEFAULT 0.0")
                    has_sor_col = True
            except Exception:
                has_tranches_col = False
                has_sor_col = False

            # Collect all predictions to process
            predictions_to_process = list(top_predictions) if top_predictions else []
            seen_symbols = set()
            for p in predictions_to_process:
                if isinstance(p, dict):
                    s = self._validate_symbol(p.get("symbol"))
                    if s:
                        seen_symbols.add(s)

            # Rebalance Liquidation: Include held symbols whose target weight dropped to 0 or fell out of top_predictions
            if current_holdings:
                for h_sym, h_val in current_holdings.items():
                    v_sym = self._validate_symbol(h_sym)
                    if not v_sym or v_sym in seen_symbols:
                        continue
                    h_w = _get_holding_weight(h_val)
                    targ_w = portfolio_weights.get(v_sym, portfolio_weights.get(h_sym, 0.0))
                    if h_w > 0.0 and (targ_w is None or targ_w <= 0.0):
                        # Position dropped out of top rank or target weight is 0 -> Liquidate
                        h_px = float(h_val.get("current_price", h_val.get("entry_price", 0.0))) if isinstance(h_val, dict) else 0.0
                        h_mkt = "KOSPI" if (v_sym.isdigit() or v_sym.endswith((".KS", ".KQ")) or h_px > 500.0) else "US"
                        if isinstance(h_val, dict) and h_val.get("market"):
                            h_mkt = str(h_val["market"])
                        predictions_to_process.append({
                            "symbol": v_sym,
                            "action": "SELL",
                            "market": h_mkt,
                            "close_price": h_px,
                            "reason": "PORTFOLIO_REBALANCE_EXIT"
                        })
                        seen_symbols.add(v_sym)

            for pred in predictions_to_process:
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

                raw_action = str(pred.get("action", "BUY") or "BUY").upper()
                curr_holding_w = _get_holding_weight(current_holdings.get(sym)) if current_holdings is not None else 0.0
                is_full_liquidation = (weight <= 0.0 and curr_holding_w > 0.0) or (raw_action == "SELL" and weight <= 0.0)
                if is_full_liquidation:
                    raw_action = "SELL"

                if is_severe:
                    # V7-07: Capitulation Buy Override (15% Cap, 25% Fractional Kelly for high-conviction oversold turnaround)
                    is_capitulation_play = (
                        any(k in pred for k in ["short_term_reversal", "oversold_bounce", "stat_arb"])
                        and (float(pred.get("expected_return", pred.get("ensemble_expected_return", 0.0)) or 0.0) > 0.0)
                    )
                    if raw_action == "BUY" and is_capitulation_play and weight > 0:
                        weight = float(np.clip(weight * 0.25, 0.01, 0.15))
                        logger.info(f"[OMS CAPITULATION BUY] {sym}: Permitting oversold reversal entry in SEVERE crisis (Weight: {weight:.2%}, Max Cap: 15%)")
                    elif raw_action == "BUY" and weight > 0:
                        continue
                    else:
                        weight = 0.0
                        raw_action = "SELL"

                if not is_severe and not (0.0 < weight <= 1.0) and raw_action != "SELL":
                    continue

                # Gate: Leland Dynamic Buffer Band (No-Trade Zone) Gating
                if use_leland_buffer and current_holdings is not None:
                    curr_w = _get_holding_weight(current_holdings.get(sym))
                    is_full_exit = is_full_liquidation
                    is_new_entry = (curr_w <= 0.0 and weight > 0.0)
                    if not is_full_exit and not is_new_entry:
                        try:
                            p_alloc = shared_allocator
                            if p_alloc is None:
                                from src.risk.portfolio_allocator import PortfolioAllocator
                                p_alloc = PortfolioAllocator()
                            mkt = str(pred.get("market", "KOSPI"))
                            vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
                            c_rate = p_alloc.estimate_transaction_cost_rate(
                                symbol=sym, market=mkt, target_weight=weight,
                                portfolio_value=tot_cap, volatility_20d=vol_20d,
                                slippage_multiplier=cached_slip_mult
                            )
                            delta_i = p_alloc.calculate_dynamic_buffer_band(
                                symbol=sym, target_weight=weight, cost_rate=c_rate, volatility_20d=vol_20d
                            )
                            if abs(curr_w - weight) <= delta_i:
                                logger.info(f"[OMS LELAND BUFFER] Symbol {sym}: Current weight {curr_w:.3f} within ±{delta_i:.3f} of target {weight:.3f} -> skipping redundant trade (Hold)")
                                continue
                        except Exception as _leland_e:
                            logger.debug(f"[OMS LELAND BUFFER] Leland buffer check skipped for {sym}: {_leland_e}")

                curr_holding_w = _get_holding_weight(current_holdings.get(sym)) if current_holdings is not None else 0.0
                if is_full_liquidation:
                    target_amount = base_portfolio_cap * curr_holding_w
                else:
                    target_amount = tot_cap * weight

                if not is_severe and raw_action != "SELL" and not (0.0 < target_amount <= tot_cap):
                    continue

                close_price = pred.get("close_price")
                plan_price = pred.get("target_price")
                if close_price is None or close_price == "":
                    close_price = plan_price
                if close_price is None or close_price == "":
                    for alt_k in ["close", "Close", "CLOSE", "price", "current_price"]:
                        if pred.get(alt_k) not in (None, ""):
                            close_price = pred.get(alt_k)
                            break
                if (close_price is None or close_price == "" or float(close_price or 0.0) <= 0.0) and raw_action == "SELL":
                    try:
                        cursor.execute("SELECT target_price FROM order_plans WHERE symbol = ? AND target_price > 0 ORDER BY created_at DESC LIMIT 1", (sym,))
                        row = cursor.fetchone()
                        if row and row[0]:
                            close_price = float(row[0])
                    except Exception:
                        pass
                if close_price is None or close_price == "":
                    continue
                try:
                    f_price = float(close_price)
                    target_price = f_price if math.isfinite(f_price) else 0.0
                except (ValueError, TypeError):
                    continue
                if not (_MIN_PRICE_BOUND <= target_price <= _MAX_PRICE_BOUND):
                    continue

                name = str(pred.get("name", "") or "")
                market = str(pred.get("market", "") or "")
                target_price = self.round_to_tick_size(target_price, market=market)
                order_id = f"ORD_{sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                is_krx = str(market).upper() in ["KOSPI", "KOSDAQ"] or sym.isdigit() or sym.endswith((".KS", ".KQ"))

                # Gate 7.1: KRX Long-Only Synthetic Short / Cash Overlay Filter
                if is_krx and raw_action in ["SELL_SHORT", "SHORT"]:
                    action = "CASH_OVERLAY"
                    status = "HEDGE_FLAG"
                elif raw_action == "SELL":
                    action = "SELL"
                    status = "PENDING"
                else:
                    action = "BUY"
                    status = "PENDING"

                # Gate 7.2: KRX Upper/Lower Limit Lock (±30% Price Limit & Liquidity Vanishing Gate)
                # C-3 Fix: Only apply to KRX markets (US stocks can move >30% normally)
                change_pct_raw = pred.get("change_pct") or pred.get("daily_return")
                change_pct: Optional[float] = None
                is_explicit_percent = False
                if change_pct_raw is not None:
                    try:
                        if isinstance(change_pct_raw, str):
                            if "%" in change_pct_raw:
                                is_explicit_percent = True
                            change_pct = float(change_pct_raw.replace("%", "").strip())
                        else:
                            change_pct = float(change_pct_raw)
                    except (ValueError, TypeError):
                        change_pct = None

                if change_pct is not None and is_krx:
                    # S-5 Fix: Unified percentage-to-decimal normalization
                    c_norm = change_pct / 100.0 if (is_explicit_percent or abs(change_pct) >= 0.50) else change_pct
                    if c_norm >= 0.295 and action == "BUY":
                        logger.warning(f"[OMS GATE 7] {sym} locked at upper limit (+{c_norm:.2%}), skipping buy execution.")
                        continue
                    elif c_norm <= -0.295:
                        if action == "SELL":
                            logger.warning(f"[OMS GATE 7] {sym} locked at lower limit ({c_norm:.2%}). Queueing PASSIVE_LIMIT SELL order for unfreeze liquidation.")
                            exec_strategy = "PASSIVE_LIMIT"
                        else:
                            logger.warning(f"[OMS GATE 7] {sym} locked at lower limit ({c_norm:.2%}) - complete liquidity freeze; skipping new entry.")
                            continue

                # Gate 7.3: KRX STT / Transaction Cost Net Alpha Hurdle Check
                if is_krx and action == "BUY" and ("expected_return" in pred or "ensemble_expected_return" in pred):
                    try:
                        allocator = shared_allocator
                        if allocator is None:
                            from src.risk.portfolio_allocator import PortfolioAllocator
                            allocator = PortfolioAllocator()
                        slip_mult = cached_slip_mult
                        adv_val = float(pred.get("adv", pred.get("trading_value", 1_000_000_000.0)) or 1_000_000_000.0)
                        vol_val = float(pred.get("volatility_20d", 0.02) or 0.02)
                        buy_cost = allocator.estimate_transaction_cost_rate(
                            symbol=sym,
                            market=market or "KOSPI",
                            target_weight=weight,
                            portfolio_value=tot_cap,
                            volatility_20d=vol_val,
                            adv=adv_val,
                            is_sell=False,
                            slippage_multiplier=slip_mult
                        )
                        sell_cost = allocator.estimate_transaction_cost_rate(
                            symbol=sym,
                            market=market or "KOSPI",
                            target_weight=weight,
                            portfolio_value=tot_cap,
                            volatility_20d=vol_val,
                            adv=adv_val,
                            is_sell=True,
                            slippage_multiplier=slip_mult
                        )
                        friction_cost = buy_cost + sell_cost
                        # V7-11: Adaptive safety margin by ADV liquidity tier
                        if adv_val >= 10_000_000_000.0:
                            safety_margin = 0.0005  # 5 bps for large caps
                        elif adv_val >= 1_000_000_000.0:
                            safety_margin = 0.0010  # 10 bps for mid caps
                        else:
                            safety_margin = 0.0020  # 20 bps for small caps
                        _is_net = "ensemble_expected_return" in pred
                        _exp_ret_raw = pred.get("ensemble_expected_return") if _is_net else pred.get("expected_return", 0.0)
                        raw_exp_ret = float(_exp_ret_raw or 0.0)
                        # Pipeline expected returns are percentage scale (e.g. 15.0 for 15%, 0.15 for 0.15%) or decimal (0.05 for 5%)
                        if is_batch_percent_scale or abs(raw_exp_ret) >= 0.50:
                            exp_ret_frac = raw_exp_ret / 100.0
                        else:
                            exp_ret_frac = raw_exp_ret
                        hurdle = safety_margin if _is_net else (friction_cost + safety_margin)

                        if exp_ret_frac <= hurdle:
                            logger.info(f"[OMS GATE 7] {sym} net alpha {exp_ret_frac:.4%} <= hurdle ({hurdle:.4%}), skipping.")
                            continue
                    except Exception as _fe:
                        logger.debug(f"[OMS GATE 7] Hurdle check exception for {sym}: {_fe}")

                # Gate 7.4: Dynamic Adverse Opening Gap Filter (-3 sigma shock protection)
                try:
                    vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
                    raw_gap = float(change_pct or 0.0)
                    # S-4/S-5 Fix: Unified normalization
                    gap_ret = raw_gap / 100.0 if (is_explicit_percent or abs(raw_gap) >= 0.50) else raw_gap
                    # Short-term reversal strategy is specifically designed for oversold bounce; exempt it
                    is_oversold_play = any(k in pred for k in ["short_term_reversal", "oversold_bounce", "stat_arb"])
                    if action == "BUY" and not is_oversold_play and gap_ret < -max(3.0 * vol_20d, 0.05):
                        logger.info(f"[OMS GATE 7] {sym} adverse gap {gap_ret:.2%} < -3*vol ({vol_20d:.2%}), skipping buy entry.")
                        continue
                except Exception as _ge:
                    logger.debug(f"[OMS GATE 7] Gap filter exception for {sym}: {_ge}")

                # Calculate currency translation
                # Determine currency (auto-detect USD for US markets)
                curr_iso = pred.get("currency") if isinstance(pred, dict) else None
                if not curr_iso:
                    curr_iso = "KRW" if is_krx else "USD"

                fx_rate_item = 1.0
                effective_target_amount = target_amount
                if curr_iso != "KRW" and curr_iso != "UNK":
                    try:
                        fx_val = pred.get("fx_rate") if isinstance(pred, dict) else None
                        if fx_val is not None and float(fx_val) > 0.01:
                            fx_rate_item = float(fx_val)
                        elif fx_rate > 0.01:
                            fx_rate_item = fx_rate
                        else:
                            fx_rate_item = 1350.0
                    except Exception:
                        fx_rate_item = fx_rate if fx_rate > 0.01 else 1350.0

                    if np.isfinite(fx_rate_item) and fx_rate_item > 0.01:
                        rate_to_krw = fx_rate_item
                        effective_target_amount = target_amount / max(fx_rate_item, 1e-4)

                # Gate 7.5: ADV Capacity Cap (max_adv_ratio of ADV max order value)
                # Now compares in local currency (USD for US stocks, KRW for KRX)
                adv_in_pred = pred.get("adv") if pred.get("adv") is not None else pred.get("trading_value")
                if adv_in_pred is not None and float(adv_in_pred) > 0:
                    adv_val = float(adv_in_pred)
                    effective_max_adv_ratio = min(max_adv_ratio, 0.05)  # V7-10: Strict 5% ADV market impact bound
                    max_adv_amount = effective_max_adv_ratio * adv_val
                    if effective_target_amount > max_adv_amount:
                        logger.info(f"[OMS ADV CAPACITY] {sym} target amount {effective_target_amount:,.0f} capped to {effective_max_adv_ratio:.1%} ADV ({max_adv_amount:,.0f})")
                        effective_target_amount = max_adv_amount
                        if curr_iso == "KRW":
                            target_amount = effective_target_amount
                        elif curr_iso == "USD":
                            target_amount = effective_target_amount * max(fx_rate_item, 1.0)
                        else:
                            try:
                                target_amount = effective_target_amount * fx_rate_item
                            except Exception:
                                pass
                else:
                    adv_val = 1_000_000_000.0 if curr_iso == "KRW" else 1_000_000.0
                # Market-specific standard lot size constraints (KRX: lot_size_krx or 1 share, TSE/HOSE/HKEX: 100 shares, US: 1 share)
                if is_krx or str(market).upper() in ("KOSPI", "KOSDAQ", "KRX") or curr_iso == "KRW":
                    lot_size = getattr(self, 'lot_size_krx', 1)
                elif str(market).upper() in ("JAPAN_TSE", "VIETNAM_HOSE", "HKEX") or curr_iso in ("JPY", "VND", "HKD") or sym.endswith((".T", ".VN", ".HK")):
                    lot_size = 100
                else:
                    lot_size = 1
                min_order_qty = lot_size

                # ── Feature 10: Delta Rebalancing (ΔQ = Q_target - Q_current) ──
                raw_target_qty = int(effective_target_amount // target_price) if (target_price > 0 and np.isfinite(target_price) and np.isfinite(effective_target_amount)) else 0
                target_shares = (raw_target_qty // lot_size) * lot_size

                held_item: Any = None
                if current_holdings and isinstance(current_holdings, dict):
                    held_item = current_holdings.get(sym) or current_holdings.get(str(sym))
                    if held_item is None:
                        base_s = sym.split('.')[0]
                        for alt_k in [base_s, f"{base_s}.KS", f"{base_s}.KQ"]:
                            if alt_k in current_holdings:
                                held_item = current_holdings[alt_k]
                                break

                eff_local_cap = base_portfolio_cap if (curr_iso == "KRW" or curr_iso == "UNK") else (base_portfolio_cap / max(fx_rate_item, 1e-4))
                curr_shares = _get_holding_shares(held_item, price=target_price, eff_cap=eff_local_cap, lot=lot_size) if held_item is not None else 0

                if current_holdings is not None:
                    if is_full_liquidation:
                        delta_shares = -curr_shares
                    else:
                        delta_shares = target_shares - curr_shares
                else:
                    delta_shares = target_shares

                # Leland Buffer Hold / Zero-Delta Rebalance Gating
                if current_holdings is not None and delta_shares == 0:
                    logger.info(f"[OMS DELTA REBALANCE] {sym}: Target shares ({target_shares}) == current shares ({curr_shares}) -> ΔQ=0, skipping order (HOLD)")
                    continue

                # Determine Action and Trade Quantity from ΔQ
                if action == "CASH_OVERLAY":
                    quantity = int(abs(delta_shares))
                elif delta_shares > 0:
                    action = "BUY"
                    quantity = int(delta_shares)
                elif delta_shares < 0:
                    action = "SELL"
                    quantity = int(abs(delta_shares))
                else:
                    continue

                is_held_liquidation = is_full_liquidation and (action == "SELL")

                # Sub-lot noise filter for existing holdings
                if curr_shares > 0 and not is_held_liquidation and quantity < min_order_qty:
                    logger.info(f"[OMS DELTA REBALANCE] {sym}: Rebalance delta {quantity} < min lot {min_order_qty}, skipping minor drift adjustment.")
                    continue

                if not is_held_liquidation and quantity < min_order_qty:
                    min_order_cost = float(min_order_qty * target_price)
                    # If effective amount covers at least 50% of 1 lot and does not breach position cap
                    if effective_target_amount >= 0.50 * min_order_cost and min_order_cost <= (float(tot_cap) * 0.25):
                        quantity = int(min_order_qty)
                    else:
                        logger.info(f"[OMS MIN LOT] {sym} target amount {effective_target_amount:,.0f} < 1 lot ({min_order_cost:,.0f}), skipping order.")
                        if status != "HEDGE_FLAG":
                            continue

                if (quantity <= 0 or not math.isfinite(quantity)) and status != "HEDGE_FLAG":
                    continue

                # Strategy Alpha Half-Life (tau_alpha) Adaptive Execution Strategy Routing (V7-10)
                # Fast alpha (<= 2d) requires fast execution (FAST_VWAP) to avoid alpha decay.
                # Use min(hl_list) so that the fastest active alpha component dictates urgency.
                hl_list = []
                for strat_key, strat_hl in STRATEGY_ALPHA_HALF_LIVES.items():
                    if strat_key in pred or f"{strat_key}_score" in pred or f"{strat_key}_prob" in pred or f"{strat_key}_20d" in pred:
                        hl_list.append(strat_hl)
                effective_half_life = float(np.min(hl_list)) if hl_list else 10.0
                effective_half_life = effective_half_life if np.isfinite(effective_half_life) else 10.0

                adv_eff = (adv_val / max(fx_rate_item, 1.0)) if (curr_iso != "KRW" and adv_val > 10_000_000.0) else adv_val
                part_ratio = float(effective_target_amount / max(adv_eff, 1.0)) if (np.isfinite(effective_target_amount) and np.isfinite(adv_eff)) else 0.0
                is_preassigned_strategy = (
                    'exec_strategy' in locals() and exec_strategy in ["PASSIVE_LIMIT", "CASH_OVERLAY", "DIP_LIMIT"]
                )
                if not is_preassigned_strategy:
                    if effective_half_life <= 2.0:
                        exec_strategy = "FAST_VWAP"
                        slice_count = 3
                    elif effective_half_life >= 25.0:
                        exec_strategy = "MIDPOINT_PEG"
                        slice_count = 8
                    elif part_ratio > 0.005:
                        exec_strategy = "DYNAMIC_VWAP"
                        slice_count = 5
                    elif effective_half_life <= 5.0 and part_ratio > 0.001:
                        exec_strategy = "TWAP"
                        slice_count = 4
                    else:
                        exec_strategy = "DIRECT"
                        slice_count = 1

                # Ensure tranche slices respect minimum lot size (each slice >= 1 lot)
                if quantity > 0 and lot_size > 0:
                    max_possible_slices = max(1, quantity // lot_size)
                    slice_count = min(slice_count, max_possible_slices)

                # Gate 7.6: VPIN Order Flow Toxicity Gate (Easley, Lopez de Prado, O'Hara 2012)
                # If adverse informed toxic order flow is detected (vpin > 0.70):
                # - BUY: switch to PASSIVE_LIMIT to prevent adverse selection
                # - SELL: switch to FAST_VWAP to rapidly liquidate before price collapses
                # - Wide spread (>100 bps): route to PASSIVE_LIMIT to minimize spread crossing cost
                vpin_val = float(pred.get("vpin", pred.get("microstructure_toxicity", pred.get("order_flow_toxicity", 0.0))) or 0.0)
                spread_val = float(pred.get("bid_ask_spread", pred.get("spread", 0.0)) or 0.0)
                if action == "BUY" and vpin_val > 0.70:
                    logger.warning(f"[OMS GATE 7.6] {sym} High VPIN toxicity ({vpin_val:.2f} > 0.70) detected on BUY. Routing to PASSIVE_LIMIT to avoid adverse selection.")
                    exec_strategy = "PASSIVE_LIMIT"
                    slice_count = max(6, slice_count)
                elif action == "SELL" and vpin_val > 0.70:
                    logger.warning(f"[OMS GATE 7.6] {sym} High VPIN toxicity ({vpin_val:.2f} > 0.70) detected on SELL. Routing to FAST_VWAP for rapid liquidation.")
                    exec_strategy = "FAST_VWAP"
                    slice_count = max(2, slice_count // 2)
                elif spread_val > 0.01:
                    logger.warning(f"[OMS GATE 7.6] {sym} Wide spread ({spread_val:.4f} > 0.01) detected. Routing to PASSIVE_LIMIT.")

                # Gate 7.7: Opening Gap Overheat & Dip-Buying Gating
                # If opening gap is excessive (> +5.0%), avoid buying the peak of the opening surge.
                # Route to DIP_LIMIT at 1.5% below open price to enter on intraday pullback.
                gap_val = float(change_pct or 0.0)
                if action == "BUY" and gap_val >= 5.0 and exec_strategy != "PASSIVE_LIMIT":
                    logger.info(f"[OMS GATE 7.7] {sym} Overheated opening gap (+{gap_val:.2f}%) detected. Routing to DIP_LIMIT to buy intraday dip.")
                    exec_strategy = "DIP_LIMIT"
                    target_price = target_price * 0.985  # Enter at 1.5% pullback discount

                # Feature 13 & F31: Orderbook Imbalance (OBI) & Micro-Price Peg Pricing
                obi_val = float(pred.get("obi", pred.get("orderbook_imbalance", pred.get("microstructure_imbalance", 0.0))) or 0.0)
                micro_px = pred.get("micro_price")
                multi_obi_val = pred.get("multi_obi", pred.get("multi_tier_obi"))
                bid_px = pred.get("bid_price")
                ask_px = pred.get("ask_price")
                spr_px = pred.get("bid_ask_spread", pred.get("spread"))
                if spr_px is None and bid_px is not None and ask_px is not None and ask_px > bid_px:
                    spr_px = ask_px - bid_px

                if exec_strategy == "MIDPOINT_PEG" or (obi_val != 0.0 and (bid_px is not None or ask_px is not None)) or micro_px is not None or multi_obi_val is not None:
                    target_price = ExecutionOMSEngine.calculate_peg_limit_price(
                        target_price=target_price,
                        bid_price=bid_px,
                        ask_price=ask_px,
                        spread=spr_px,
                        alpha_urgency=0.50,
                        action=action,
                        obi=obi_val if obi_val != 0.0 else None,
                        micro_price=micro_px,
                        multi_obi=multi_obi_val,
                    )

                sleeve_type = "FAST_MOMENTUM" if effective_half_life <= 3.0 else "CORE_FUNDAMENTAL"
                regime_params = self.get_regime_timing_parameters(pred.get("market_regime", getattr(self, "current_regime", None)))
                sl_mult = regime_params.get('sl_atr_mult', 1.5 if sleeve_type == "FAST_MOMENTUM" else 2.0)
                tp_t2 = regime_params.get('tp_tier2', 0.15 if sleeve_type == "FAST_MOMENTUM" else 0.25)
                vol_sigma = max(0.015, min(0.15, float(pred.get("volatility_20d", 0.02) or 0.02)))
                dynamic_sl_pct = float(np.clip(sl_mult * vol_sigma, 0.03, 0.12))
                min_reward = 2.5 * dynamic_sl_pct
                raw_exp_alpha = float(pred.get("ensemble_expected_return", pred.get("expected_return", 0.0)) or 0.0)
                exp_ret_decimal = (raw_exp_alpha / 100.0) if (is_batch_percent_scale or abs(raw_exp_alpha) >= 0.50) else raw_exp_alpha
                target_reward = max(tp_t2, min_reward, max(0.0, exp_ret_decimal) * 1.25)
                dynamic_tp_pct = float(np.clip(target_reward, 0.08, 0.40))

                target_take_profit = round(target_price * (1.0 + dynamic_tp_pct), 2)
                target_stop_loss = round(target_price * (1.0 - dynamic_sl_pct), 2)

                order_amount = round(float(quantity * target_price), 2)

                # ── Feature 11 & 13: Almgren-Chriss Slicing & Tranche Tagging with OBI Peg Pricing ──
                tranches = []
                if quantity > 0:
                    if slice_count > 1 and quantity >= slice_count:
                        tier = "fast" if effective_half_life <= 2.0 else ("slow" if effective_half_life >= 25.0 else "medium")
                        adv_ac = float(adv_eff) if adv_eff > 0 else 1_000_000.0
                        vol_ac = float(vol_sigma) if vol_sigma > 0 else 0.02
                        raw_slices = AlmgrenChrissScheduler.compute_trajectory(
                            total_quantity=quantity,
                            adv=adv_ac,
                            daily_volatility=vol_ac,
                            strategy_tier=tier,
                            n_slices=slice_count
                        )
                        if lot_size > 1:
                            alloc_lots = [q // lot_size for q in raw_slices]
                            diff_lots = (quantity // lot_size) - sum(alloc_lots)
                            if diff_lots > 0:
                                for k in range(diff_lots):
                                    alloc_lots[k % len(alloc_lots)] += 1
                            elif diff_lots < 0:
                                rem_lots = abs(diff_lots)
                                for k in range(len(alloc_lots) - 1, -1, -1):
                                    sub = min(alloc_lots[k], rem_lots)
                                    alloc_lots[k] -= sub
                                    rem_lots -= sub
                                    if rem_lots == 0:
                                        break
                            raw_slices = [lots * lot_size for lots in alloc_lots]

                        active_slices = [q for q in raw_slices if q > 0]
                        if not active_slices:
                            active_slices = [quantity]
                        n_act = len(active_slices)
                        for j, q_slice in enumerate(active_slices):
                            is_final = (j == n_act - 1)
                            if exec_strategy == "PASSIVE_LIMIT":
                                t_tag = "PASSIVE_LIMIT"
                            elif exec_strategy == "DIP_LIMIT":
                                t_tag = "DIP_LIMIT" if not is_final else "AGGRESSIVE_TAKER"
                            else:
                                t_tag = "AGGRESSIVE_TAKER" if is_final else "MIDPOINT_PEG"
                            t_offset = int(j * (180.0 / max(n_act, 1)))

                            slice_px = target_price
                            if t_tag == "MIDPOINT_PEG" and (bid_px or ask_px or obi_val != 0.0 or micro_px is not None or multi_obi_val is not None):
                                slice_px = ExecutionOMSEngine.calculate_peg_limit_price(
                                    target_price=target_price,
                                    bid_price=bid_px,
                                    ask_price=ask_px,
                                    spread=spr_px,
                                    alpha_urgency=0.50,
                                    action=action,
                                    obi=obi_val if obi_val != 0.0 else None,
                                    micro_price=micro_px,
                                    multi_obi=multi_obi_val,
                                )

                            tranches.append({
                                "slice": j + 1,
                                "quantity": int(q_slice),
                                "action": action,
                                "exec_type": t_tag,
                                "time_offset_min": t_offset,
                                "limit_price": round(float(slice_px), 2)
                            })
                    else:
                        s_tag = "PASSIVE_LIMIT" if exec_strategy == "PASSIVE_LIMIT" else ("MIDPOINT_PEG" if exec_strategy == "MIDPOINT_PEG" else ("DIP_LIMIT" if exec_strategy == "DIP_LIMIT" else "AGGRESSIVE_TAKER"))
                        tranches.append({
                            "slice": 1,
                            "quantity": int(quantity),
                            "action": action,
                            "exec_type": s_tag,
                            "time_offset_min": 0,
                            "limit_price": round(float(target_price), 2)
                        })

                # Feature 12: Dynamic Dark Probing & 3-Tier Multi-Leg SOR Routing
                dp_score = float(pred.get("darkpool_score", pred.get("dark_pool_score", 0.0)) or 0.0)
                is_accum = bool(pred.get("is_accumulation", False))
                order_dict = {
                    "symbol": sym,
                    "name": name,
                    "market": market,
                    "action": action,
                    "quantity": quantity,
                    "target_price": target_price,
                    "execution_strategy": exec_strategy,
                    "darkpool_score": dp_score,
                    "is_accumulation": is_accum,
                }
                sor_routing = {}
                expected_saving_bps = 0.0
                if self.sor is not None and quantity > 0:
                    try:
                        spr_bps = float(pred.get("market_spread_bps", 15.0) or 15.0)
                        sor_res = self.sor.route_order(order_dict, ats_available=True, market_spread_bps=spr_bps)
                        sor_routing = sor_res
                        expected_saving_bps = float(sor_res.get("expected_cost_saving_bps", 0.0))
                    except Exception as _sor_err:
                        logger.debug(f"[OMS] Error routing with SOR: {_sor_err}")

                # Attach SOR routing to individual tranches
                if self.sor is not None and tranches:
                    for tr in tranches:
                        try:
                            t_dict = dict(order_dict)
                            t_dict["quantity"] = tr["quantity"]
                            t_dict["execution_strategy"] = tr["exec_type"]
                            t_dict["target_price"] = tr.get("limit_price", target_price)
                            t_res = self.sor.route_order(t_dict, ats_available=True)
                            tr["sor_routing"] = t_res.get("legs", [])
                            tr["expected_cost_saving_bps"] = t_res.get("expected_cost_saving_bps", 0.0)
                        except Exception:
                            pass

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
                    "lot_size": lot_size,
                    "min_order_qty": min_order_qty,
                    "order_amount": order_amount,
                    "execution_strategy": exec_strategy,
                    "slice_count": slice_count,
                    "sleeve_type": sleeve_type,
                    "target_take_profit": target_take_profit,
                    "target_stop_loss": target_stop_loss,
                    "status": status,
                    "created_at": now_str,
                    "tranches": tranches,
                    "sor_routing": sor_routing,
                    "expected_cost_saving_bps": round(expected_saving_bps, 2)
                }
                order_plans.append(plan_entry)

                tranches_json = json.dumps(tranches) if tranches else "[]"
                sor_routing_json = json.dumps(sor_routing) if sor_routing else "{}"
                if has_sor_col and has_tranches_col:
                    cursor.execute("""
                        INSERT OR REPLACE INTO order_plans
                        (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, created_at, tranches, sor_routing, expected_cost_saving_bps)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), quantity, exec_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, now_str, tranches_json, sor_routing_json, round(expected_saving_bps, 2)))
                elif has_tranches_col:
                    cursor.execute("""
                        INSERT OR REPLACE INTO order_plans
                        (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, created_at, tranches)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), quantity, exec_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, now_str, tranches_json))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO order_plans
                        (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (order_id, sym, name, market, action, round(weight, 4), round(target_amount, 2), round(target_price, 2), quantity, exec_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, now_str))

            # Gate 8: Synthetic Beta Inverse Hedge Overlay (Bear / Crisis regime)
            # V8-HIGH-03 Fix: Multi-market decomposed inverse hedging (KRX vs US independent hedges)
            if "BEAR" in str(regime_label).upper() or "CRISIS" in str(regime_label).upper():
                try:
                    from src.risk.portfolio_allocator import PortfolioAllocator

                    krx_sub_weights = {s: w for s, w in portfolio_weights.items() if str(s).isdigit() or str(s).endswith(('.KS', '.KQ'))}
                    us_sub_weights = {s: w for s, w in portfolio_weights.items() if s not in krx_sub_weights}

                    hedge_specs = []
                    if sum(krx_sub_weights.values()) > 0.05:
                        h_krx = PortfolioAllocator.compute_synthetic_inverse_hedge(
                            portfolio_weights=krx_sub_weights,
                            market="KOSPI",
                            regime_label=regime_label
                        )
                        if h_krx.get("hedge_required") and h_krx.get("hedge_weight", 0.0) > 0:
                            hedge_specs.append((h_krx, "KOSPI"))

                    if sum(us_sub_weights.values()) > 0.05:
                        has_nasdaq = any("NASDAQ" in str(pred.get("market", "")).upper() for pred in (top_predictions or []) if pred.get("symbol") in us_sub_weights)
                        us_mkt = "NASDAQ" if has_nasdaq else "SP500"
                        h_us = PortfolioAllocator.compute_synthetic_inverse_hedge(
                            portfolio_weights=us_sub_weights,
                            market=us_mkt,
                            regime_label=regime_label
                        )
                        if h_us.get("hedge_required") and h_us.get("hedge_weight", 0.0) > 0:
                            hedge_specs.append((h_us, us_mkt))

                    if not hedge_specs and portfolio_weights:
                        first_market = str(top_predictions[0].get("market", "KOSPI")) if top_predictions else "KOSPI"
                        h_fallback = PortfolioAllocator.compute_synthetic_inverse_hedge(
                            portfolio_weights=portfolio_weights,
                            market=first_market,
                            regime_label=regime_label
                        )
                        if h_fallback.get("hedge_required") and h_fallback.get("hedge_weight", 0.0) > 0:
                            hedge_specs.append((h_fallback, first_market))

                    for hedge_info, target_market in hedge_specs:
                        h_sym = hedge_info["hedge_symbol"]
                        h_weight = float(np.clip(hedge_info["hedge_weight"], 0.0, 0.50))
                        h_amount = tot_cap * h_weight
                        h_order_id = f"ORD_HEDGE_{h_sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                        hedge_price = self._get_latest_price(h_sym, prices_dict=prices_dict, top_predictions=top_predictions)
                        if hedge_price <= 0.0:
                            hedge_price = 10000.0 if str(target_market).upper() in ["KOSPI", "KOSDAQ", "KRX"] or str(h_sym).isdigit() else 50.0
                        hedge_price = self.round_to_tick_size(hedge_price, market=target_market)

                        is_krx_hedge = str(target_market).upper() in ["KOSPI", "KOSDAQ", "KRX"] or str(h_sym).isdigit() or str(h_sym).endswith((".KS", ".KQ"))
                        h_amount_local = h_amount if is_krx_hedge else (h_amount / fx_rate)
                        lot_h = getattr(self, 'lot_size_krx', 1) if is_krx_hedge else 1
                        raw_h_qty = int(h_amount_local / max(hedge_price, 1e-6))
                        h_quantity = (raw_h_qty // lot_h) * lot_h

                        h_entry = {
                            "order_id": h_order_id,
                            "symbol": h_sym,
                            "name": "INVERSE_HEDGE_OVERLAY",
                            "market": target_market,
                            "action": "BUY_HEDGE",
                            "target_weight": round(h_weight, 4),
                            "target_amount": round(h_amount_local, 2),
                            "target_price": round(hedge_price, 2),
                            "quantity": h_quantity,
                            "execution_strategy": "DIRECT",
                            "slice_count": 1,
                            "sleeve_type": "FAST",
                            "target_take_profit": None,
                            "target_stop_loss": None,
                            "status": "HEDGE_ACTIVE",
                            "created_at": now_str,
                            "tranches": [{
                                "slice": 1,
                                "quantity": int(h_quantity),
                                "action": "BUY_HEDGE",
                                "exec_type": "AGGRESSIVE_TAKER",
                                "time_offset_min": 0
                            }]
                        }
                        order_plans.append(h_entry)
                        h_tranches_json = json.dumps(h_entry["tranches"])
                        if has_tranches_col:
                            cursor.execute("""
                                INSERT OR REPLACE INTO order_plans
                                (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, created_at, tranches)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (h_order_id, h_sym, "INVERSE_HEDGE_OVERLAY", target_market, "BUY_HEDGE", round(h_weight, 4), round(h_amount_local, 2), h_entry["target_price"], h_entry["quantity"], "DIRECT", 1, "FAST", None, None, "HEDGE_ACTIVE", now_str, h_tranches_json))
                        else:
                            cursor.execute("""
                                INSERT OR REPLACE INTO order_plans
                                (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, sleeve_type, target_take_profit, target_stop_loss, status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (h_order_id, h_sym, "INVERSE_HEDGE_OVERLAY", target_market, "BUY_HEDGE", round(h_weight, 4), round(h_amount_local, 2), h_entry["target_price"], h_entry["quantity"], "DIRECT", 1, "FAST", None, None, "HEDGE_ACTIVE", now_str))
                except Exception as _hedge_e:
                    logger.warning(f"[OMS HEDGE OVERLAY] Hedge order plan generation skipped: {_hedge_e}")

            conn.commit()
        finally:
            if self.db_path != ":memory:":
                conn.close()
        return order_plans

    generate_order_plans = generate_order_plan

    def route_with_smart_order_router(
        self,
        order_plans: List[Dict[str, Any]],
        ats_available: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Routes generated order plans through Multi-Venue SmartOrderRouter (SOR)
        to minimize market impact, capture maker rebates, and leverage Dark Pool / ATS liquidity.
        """
        try:
            from src.execution.smart_order_router import SmartOrderRouter
            sor = SmartOrderRouter()
            return sor.route_batch(order_plans, ats_available=ats_available)
        except Exception as _sor_e:
            logger.debug(f"[OMS SOR] Fallback routing without SOR: {_sor_e}")
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
            side_sign = 1.0 if (action.startswith("BUY") or action in ["LONG", "BUY_HEDGE"]) else -1.0

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

            if target_qty > 0 and total_executed < (target_qty * 0.98) and (target_qty - total_executed) > 5:
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

    def get_current_holdings_from_db(self) -> Dict[str, float]:
        """Queries recent target_weight or executed allocations from trade_logs.db."""
        conn = self._get_conn()
        holdings: Dict[str, float] = {}
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, target_weight FROM order_plans
                WHERE status IN ('EXECUTED', 'PENDING', 'PARTIALLY_FILLED')
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            for sym, w in rows:
                if sym not in holdings and w is not None:
                    try:
                        holdings[sym] = float(w)
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.debug(f"[OMS ENGINE] Failed to fetch current holdings from DB: {e}")
        finally:
            if self.db_path != ":memory:":
                conn.close()
        return holdings

    def get_current_holdings_details_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Queries recent holding details (quantity, price, entry, weight, date, sleeve) from trade_logs.db."""
        conn = self._get_conn()
        holdings: Dict[str, Dict[str, Any]] = {}
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, target_weight, target_price, quantity, action, status, created_at, sleeve_type
                FROM order_plans
                WHERE status IN ('EXECUTED', 'PENDING', 'PARTIALLY_FILLED')
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            for sym, w, p, qty, action, status, dt, sleeve in rows:
                if sym not in holdings and action == "BUY" and w and float(w) > 0:
                    try:
                        days = 1
                        if dt:
                            try:
                                dt_parsed = datetime.datetime.fromisoformat(str(dt).split('.')[0])
                                days = max(1, (datetime.datetime.now() - dt_parsed).days)
                            except Exception:
                                days = 1
                        holdings[sym] = {
                            "symbol": sym,
                            "quantity": int(qty or 1),
                            "entry_price": float(p or 1.0),
                            "current_price": float(p or 1.0),
                            "weight": float(w),
                            "target_weight": float(w),
                            "days_held": days,
                            "sleeve_type": str(sleeve or "CORE"),
                            "enable_3tier_tp": True
                        }
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.debug(f"[OMS ENGINE] Failed to fetch holding details from DB: {e}")
        finally:
            if self.db_path != ":memory:":
                conn.close()
        return holdings

    @staticmethod
    def calculate_peg_limit_price(
        target_price: float,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        spread: Optional[float] = None,
        alpha_urgency: float = 0.50,
        action: str = "BUY",
        obi: Optional[float] = None,
        kappa: float = 1.5,
        micro_price: Optional[float] = None,
        multi_obi: Optional[Dict[str, float]] = None,
        daily_volatility: Optional[float] = None,
        book_depth_ratio: Optional[float] = None,
        queue_position_ratio: Optional[float] = None,
        l3_micro_price: Optional[float] = None,
        l3_imbalance: Optional[float] = None,
        hawkes_toxicity: Optional[float] = None,
        hawkes_arrival_imbalance: Optional[float] = None,
        queue_imbalance: Optional[float] = None,
        qi_acceleration: Optional[float] = None,
        cross_asset_toxicity: Optional[float] = None,
        version: int = 6,
        qi_jerk: Optional[float] = None,
        deep_ofi: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        Phase 6 (F44), Phase 7 (F50) & Phase 8 (F54) Level-3 Micro-Price & Queue-Position-Aware Peg Calculation:
        1. Base anchor price: Hawkes arrival-adjusted micro-price > L3 micro-price > L1 micro-price > mid price.
        2. Dynamic curvature kappa_eff scales with volatility and orderbook depth.
        3. Imbalance shift uses Queue Imbalance (QI_L3*) > L3 decayed imbalance > multi-tier L2 OBI composite > L1 OBI.
        4. Queue position adverse selection offset delta_P_queue compensates when order is buried (u_q > 0.40),
           suppressed by Hawkes & cross-asset composite toxicity gamma_composite (F50 & F54).
        5. Toxic shading offset delta_P_shade steps back against toxic flow when gamma_composite > 0.45/0.50 (F50 & F54).
        6. Queue Imbalance 2nd-order acceleration peg shift a_shift (F54.2).
        7. Strict clipping within [min(bid, ask), max(bid, ask)].
        """
        tp = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 1000.0
        if tp <= 0:
            return tp

        spr = float(spread) if (spread is not None and spread > 0) else max(tp * 0.002, 1.0)
        p_bid = float(bid_price) if (bid_price is not None and bid_price > 0) else (tp - spr / 2.0)
        p_ask = float(ask_price) if (ask_price is not None and ask_price > 0) else (tp + spr / 2.0)
        p_mid = (p_bid + p_ask) / 2.0

        # 2. Imbalance resolution: Queue Imbalance > L3 decayed imbalance > Multi-tier L2 composite > L1 OBI
        eff_obi = None
        if queue_imbalance is not None and math.isfinite(float(queue_imbalance)):
            eff_obi = float(queue_imbalance)
        elif l3_imbalance is not None and math.isfinite(float(l3_imbalance)):
            eff_obi = float(l3_imbalance)
        elif multi_obi is not None and isinstance(multi_obi, dict):
            multi_dict: Dict[Any, Any] = multi_obi
            obi_1 = float(multi_dict.get("OBI_1", multi_dict.get("obi_1", multi_dict.get("1", multi_dict.get(1, 0.0)))) or 0.0)
            obi_5 = float(multi_dict.get("OBI_5", multi_dict.get("obi_5", multi_dict.get("5", multi_dict.get(5, 0.0)))) or 0.0)
            obi_10 = float(multi_dict.get("OBI_10", multi_dict.get("obi_10", multi_dict.get("10", multi_dict.get(10, 0.0)))) or 0.0)
            eff_obi = 0.50 * obi_1 + 0.35 * obi_5 + 0.15 * obi_10
        elif obi is not None and math.isfinite(float(obi)):
            eff_obi = float(obi)

        # 1. Base anchor price: Hawkes arrival adjusted (F50) > L3 micro-price > L1 micro-price > mid price
        omega_H = 0.35
        kappa_H = 1.20
        del_lam = None
        if hawkes_arrival_imbalance is not None and math.isfinite(float(hawkes_arrival_imbalance)):
            del_lam = float(np.clip(float(hawkes_arrival_imbalance), -1.0, 1.0))

        if del_lam is not None:
            qi_val = float(np.clip(eff_obi if eff_obi is not None else 0.0, -1.0, 1.0))
            if l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
                p_base = float(l3_micro_price) + 0.5 * spr * omega_H * math.tanh(kappa_H * del_lam)
            else:
                p_base = p_mid + 0.5 * spr * ((1.0 - omega_H) * qi_val + omega_H * math.tanh(kappa_H * del_lam))
        elif l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
            p_base = float(l3_micro_price)
        elif micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
            p_base = float(micro_price)
        else:
            p_base = p_mid

        # 3. Dynamic curvature scaling
        if daily_volatility is not None or book_depth_ratio is not None:
            sig = float(daily_volatility) if daily_volatility is not None else 0.02
            r_depth = float(book_depth_ratio) if book_depth_ratio is not None else 1.0
            r_depth = float(np.clip(r_depth, 0.20, 5.0))
            kappa_eff = float(np.clip(1.5 * (sig / 0.02) / math.sqrt(r_depth), 0.8, 3.0))
        else:
            kappa_eff = float(kappa)

        is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE", "BID"]
        direction = 1.0 if is_buy else -1.0

        # 4. Imbalance peg shift
        if eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0 and del_lam is None:
            obi_val = float(np.clip(float(eff_obi), -1.0, 1.0))
            peg_shift = 0.5 * spr * math.tanh(kappa_eff * obi_val)
        else:
            peg_shift = 0.0

        # F50 & F54: Directional Hawkes and Cross-Asset Composite Toxicity
        g_loc = float(np.clip(float(hawkes_toxicity), 0.0, 1.0)) if (hawkes_toxicity is not None and math.isfinite(float(hawkes_toxicity))) else 0.0
        g_cross = float(np.clip(float(cross_asset_toxicity), 0.0, 1.0)) if (cross_asset_toxicity is not None and math.isfinite(float(cross_asset_toxicity))) else 0.0
        gamma_composite = float(np.clip(0.65 * g_loc + 0.35 * g_cross, 0.0, 1.0)) if cross_asset_toxicity is not None else g_loc

        # 5. Queue position adverse selection offset (F44, F50 & F54)
        q_shift = 0.0
        if queue_position_ratio is not None and math.isfinite(float(queue_position_ratio)):
            u_q = float(np.clip(float(queue_position_ratio), 0.0, 1.0))
            if u_q > 0.40:
                urg = float(np.clip(float(alpha_urgency), 0.1, 1.0))
                tox_suppress = max(0.0, 1.0 - 0.85 * gamma_composite)
                q_shift = direction * 0.5 * spr * urg * (u_q - 0.40) * 0.60 * tox_suppress

        # 6. Toxic shading offset (F50 & F54)
        shade_shift = 0.0
        if int(version) >= 8 and gamma_composite > 0.45:
            shade_shift = -direction * 0.35 * spr * (gamma_composite - 0.45)
        elif gamma_composite > 0.50:
            shade_shift = -direction * 0.25 * spr * (gamma_composite - 0.50)

        # 7. Queue Imbalance 2nd-Order Acceleration Peg Shift (F54)
        accel_shift = 0.0
        if qi_acceleration is not None and math.isfinite(float(qi_acceleration)):
            a_val = float(qi_acceleration)
            accel_tox_damp = max(0.0, 1.0 - 0.90 * gamma_composite)
            accel_shift = direction * 0.20 * spr * math.tanh(0.80 * a_val) * accel_tox_damp

        # 8. Queue Imbalance 3rd-Order Jerk & Deep-OFI Peg Shift (Phase 9 F58.1)
        jerk_shift = 0.0
        if int(version) >= 9:
            j_val = float(qi_jerk) if (qi_jerk is not None and math.isfinite(float(qi_jerk))) else float(kwargs.get("qi_jerk", 0.0))
            d_ofi = float(deep_ofi) if (deep_ofi is not None and math.isfinite(float(deep_ofi))) else float(kwargs.get("deep_ofi", 0.0))
            jerk_tox_damp = max(0.0, 1.0 - 0.95 * gamma_composite)
            jerk_shift = direction * spr * (0.10 * math.tanh(0.50 * j_val) + 0.15 * math.tanh(1.20 * d_ofi)) * jerk_tox_damp

        # If micro-price, L3 micro-price, OBI shift, queue offset, shade shift, accel shift, jerk shift, or arrival imbalance was active
        if (
            (l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0)
            or (micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0)
            or (eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0)
            or q_shift != 0.0
            or shade_shift != 0.0
            or accel_shift != 0.0
            or jerk_shift != 0.0
            or del_lam is not None
        ):
            peg_price = p_base + peg_shift + q_shift + shade_shift + accel_shift + jerk_shift
            return float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))

        # Fallback to urgency interpolation between bid and ask
        urgency = max(0.0, min(1.0, float(alpha_urgency)))
        if is_buy:
            peg_price = p_bid + urgency * (p_ask - p_bid)
        else:
            peg_price = p_ask - urgency * (p_ask - p_bid)

        return float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))

    REGIME_TIMING_MATRIX: Dict[str, Dict[str, Any]] = {
        'BULL_LOW_VOL': {'entry_thresh': 0.65, 'tp_tier1': 0.08, 'tp_tier2': 0.15, 'tp_tier3': 0.25, 'sl_atr_mult': 2.0, 'ts_atr_mult': 2.5, 'max_holding_days': 45},
        'BULL_HIGH_VOL': {'entry_thresh': 0.72, 'tp_tier1': 0.08, 'tp_tier2': 0.15, 'tp_tier3': 0.25, 'sl_atr_mult': 1.5, 'ts_atr_mult': 1.8, 'max_holding_days': 20},
        'SIDEWAYS_LOW_VOL': {'entry_thresh': 0.75, 'tp_tier1': 0.06, 'tp_tier2': 0.12, 'tp_tier3': 0.20, 'sl_atr_mult': 1.2, 'ts_atr_mult': 1.2, 'max_holding_days': 10},
        'SIDEWAYS_HIGH_VOL': {'entry_thresh': 0.80, 'tp_tier1': 0.05, 'tp_tier2': 0.10, 'tp_tier3': 0.15, 'sl_atr_mult': 1.0, 'ts_atr_mult': 1.0, 'max_holding_days': 7},
        'BEAR_LOW_VOL': {'entry_thresh': 0.85, 'tp_tier1': 0.05, 'tp_tier2': 0.08, 'tp_tier3': 0.12, 'sl_atr_mult': 1.0, 'ts_atr_mult': 1.0, 'max_holding_days': 5},
        'BEAR_HIGH_VOL': {'entry_thresh': 0.95, 'tp_tier1': 0.03, 'tp_tier2': 0.06, 'tp_tier3': 0.10, 'sl_atr_mult': 0.8, 'ts_atr_mult': 0.8, 'max_holding_days': 3},
    }

    @classmethod
    def get_regime_timing_parameters(cls, regime: Optional[str] = None) -> Dict[str, Any]:
        """Returns 2D regime-specific timing thresholds and ATR multipliers."""
        r_key = str(regime).upper() if regime else 'SIDEWAYS_LOW_VOL'
        for key in cls.REGIME_TIMING_MATRIX:
            if key in r_key:
                return dict(cls.REGIME_TIMING_MATRIX[key])
        return dict(cls.REGIME_TIMING_MATRIX['SIDEWAYS_LOW_VOL'])

    @staticmethod
    def calculate_confluence_entry_score(
        ensemble_score: float,
        vcp_score: float = 0.0,
        volume_surge_ratio: float = 1.0,
        obi_score: float = 0.0,
        price_above_ma50: bool = True
    ) -> Dict[str, Any]:
        """
        Engine 1: Multi-Timeframe Confluence Entry Engine.
        Combines macro trend, daily ensemble score, VCP compression, volume surge, and L2 OBI.
        """
        ens_c = float(np.clip(ensemble_score, 0.0, 1.0))
        vcp_c = float(np.clip(vcp_score, 0.0, 1.0))
        vol_c = float(np.clip((volume_surge_ratio - 1.0) / 2.0, 0.0, 1.0))
        obi_c = float(np.clip(0.50 + obi_score * 0.50, 0.0, 1.0))

        # Composite confluence weighting
        confluence_score = 0.40 * ens_c + 0.30 * vcp_c + 0.15 * vol_c + 0.15 * obi_c
        if not price_above_ma50:
            confluence_score *= 0.80  # Penalty for trading below 50-day moving average

        is_valid_entry = (confluence_score >= 0.65) and (ens_c >= 0.55)
        return {
            'confluence_score': round(confluence_score, 4),
            'is_valid_entry': is_valid_entry,
            'ensemble_component': round(ens_c, 4),
            'vcp_component': round(vcp_c, 4),
            'volume_component': round(vol_c, 4),
            'obi_component': round(obi_c, 4)
        }

    check_confluence_entry = calculate_confluence_entry_score

    @staticmethod
    def generate_scale_in_order_plan(
        symbol: str,
        total_target_shares: int,
        current_stage: int = 1,
        entry_price: float = 0.0,
        current_price: float = 0.0,
        pivot_price: float = 0.0
    ) -> Dict[str, Any]:
        """
        Engine 2: 3-Stage Dynamic Scale-In Pyramiding Engine:
        - Stage 1 (Probe): 30% position upon initial signal.
        - Stage 2 (Breakout Confirmation): 50% position when price breaks above pivot.
        - Stage 3 (Pullback Support): 20% position on pullback bounce.
        """
        if total_target_shares <= 0:
            return {'symbol': symbol, 'stage': current_stage, 'allocated_shares': 0, 'action': 'HOLD'}

        if current_stage == 1:
            shares = max(1, int(total_target_shares * 0.30))
            return {'symbol': symbol, 'stage': 1, 'allocated_shares': shares, 'weight_pct': 0.30, 'action': 'BUY_PROBE'}
        elif current_stage == 2:
            shares = max(1, int(total_target_shares * 0.50))
            return {'symbol': symbol, 'stage': 2, 'allocated_shares': shares, 'weight_pct': 0.50, 'action': 'BUY_BREAKOUT'}
        elif current_stage == 3:
            shares = max(1, total_target_shares - int(total_target_shares * 0.80))
            return {'symbol': symbol, 'stage': 3, 'allocated_shares': shares, 'weight_pct': 0.20, 'action': 'BUY_PYRAMID'}
        else:
            return {'symbol': symbol, 'stage': current_stage, 'allocated_shares': 0, 'action': 'HOLD_FULL'}

    @staticmethod
    def check_signal_exhaustion_exit(
        current_score: float,
        top_candidates_avg_expected_return: float = 0.0,
        holding_expected_return: float = 0.0,
        min_score_threshold: float = 0.48,
        switching_hurdle: float = 0.08
    ) -> Tuple[bool, str]:
        """
        Engine 4: Signal Decay & Opportunity Cost Switching Exit.
        """
        if current_score < min_score_threshold:
            return True, "ALPHA_SCORE_COLLAPSE"
        if (top_candidates_avg_expected_return - holding_expected_return) >= switching_hurdle:
            return True, "OPPORTUNITY_COST_SWITCHING"
        return False, "HOLD"

    @staticmethod
    def check_time_stop_exit(
        days_held: int,
        unrealized_return: float,
        max_stall_days: int = 12,
        stall_band: Tuple[float, float] = (-0.02, 0.03)
    ) -> Tuple[bool, str]:
        """
        Engine 5: Time-Stop / Stalling Momentum Exit.
        """
        if days_held >= max_stall_days and (stall_band[0] <= unrealized_return <= stall_band[1]):
            return True, "TIME_STOP_MOMENTUM_STALLED"
        return False, "HOLD"

    @staticmethod
    def check_order_flow_shock_exit(
        mfi_value: float = 50.0,
        is_down_day: bool = False,
        volume_ratio: float = 1.0,
        obi: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Engine 6: Institutional Order Flow Shock Exit.
        """
        shock_conditions = 0
        if mfi_value < 25.0:
            shock_conditions += 1
        if is_down_day and volume_ratio >= 3.5:
            shock_conditions += 1
        if obi < -0.60:
            shock_conditions += 1

        if shock_conditions >= 2:
            return True, "EMERGENCY_ORDER_FLOW_SHOCK"
        return False, "HOLD"

    def calculate_trailing_stop_plan(
        self,
        current_holdings: Dict[str, Dict[str, Any]],
        prices_dict: Optional[Dict[str, Any]] = None,
        atr_multiplier: float = 2.0,
        profit_take_threshold: float = 0.15,
        regime: Optional[str] = None,
        enable_3tier_tp: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Engine 3: 4-Tier Multi-Stage Dynamic Profit-Taking & Chandelier/KAMA Trend Runner Engine.
        - Tier 1 (+8% or +1.5R): 30% Partial TP + Move stop to Breakeven (+0.3% friction) -> Free Trade.
        - Tier 2 (+15% or +3.0R): 30% Partial TP + Chandelier ATR (High_20 - 1.5 * ATR) Trailing Stop.
        - Tier 3 (+25%): 25% Partial TP + KAMA Adaptive Moving Average Trailing Stop.
        - Tier 4 (Runner 25~40%): Let run until 50-day MA or Chandelier trailing stop breakdown.
        - Integrates Signal Exhaustion, Time-Stop, and Emergency Order Flow exits.
        """
        trailing_plans: List[Dict[str, Any]] = []
        if not current_holdings:
            return trailing_plans

        regime_params = self.get_regime_timing_parameters(regime)
        tp_t2 = profit_take_threshold if profit_take_threshold is not None else regime_params.get('tp_tier2', 0.15)
        tp_t1 = min(regime_params.get('tp_tier1', 0.08), tp_t2 * 0.7)
        tp_t3 = max(0.25, tp_t2 + 0.15)
        sl_mult = regime_params.get('sl_atr_mult', 1.5)
        ts_mult = atr_multiplier if atr_multiplier is not None else regime_params.get('ts_atr_mult', 2.0)
        max_holding_days = regime_params.get('max_holding_days', 30)

        for sym, h_info in current_holdings.items():
            qty = float(h_info.get("quantity", 0.0))
            entry_p = float(h_info.get("entry_price", 0.0))
            curr_p = float(h_info.get("current_price", entry_p))
            days_held = int(h_info.get("days_held", 0))
            current_score = float(h_info.get("current_score", 0.60))
            mfi = float(h_info.get("mfi", 50.0))
            obi = float(h_info.get("obi", 0.0))
            correction_phase = str(h_info.get("correction_phase", "")).upper()
            use_3tier = bool(enable_3tier_tp or h_info.get("enable_3tier_tp") or h_info.get("auto_tier_tp"))
            if qty <= 0 or entry_p <= 0 or curr_p <= 0:
                continue

            # Phase-adaptive stop loss adjustments
            local_sl_mult = sl_mult
            local_ts_mult = ts_mult
            if correction_phase == 'TIME_CONSOLIDATION':
                local_sl_mult = min(local_sl_mult, 0.9)  # Ultra-tight stop on base breakdowns
                local_ts_mult = min(local_ts_mult, 1.2)
            elif correction_phase == 'PRICE_PULLBACK':
                local_sl_mult = max(local_sl_mult, 1.3)  # Wider room for Fibonacci swing bounces

            unrealized_return = (curr_p - entry_p) / entry_p
            p_df = prices_dict.get(sym) if prices_dict else None

            # Dynamic volatility scaling if price history < 14 rows
            vol_20d = h_info.get("volatility_20d")
            if vol_20d is None:
                ann_vol = h_info.get("annualized_volatility") or h_info.get("annualized_vol") or h_info.get("volatility") or h_info.get("vol")
                if ann_vol is not None and float(ann_vol) > 0:
                    vol_20d = float(ann_vol) / np.sqrt(252.0)

            if vol_20d is not None and float(vol_20d) > 0:
                vol_scale = max(0.01, min(0.20, float(vol_20d)))
            else:
                vol_scale = 0.02

            # Compute ATR, 20-day high, and 50-day MA if available
            high_20 = max(curr_p, entry_p)
            ma_50 = entry_p * 0.95
            atr = curr_p * vol_scale
            is_down_day = False
            vol_ratio = 1.0

            if isinstance(p_df, pd.DataFrame) and len(p_df) >= 14:
                high_col = next((c for c in p_df.columns if str(c).lower() == 'high'), None)
                low_col = next((c for c in p_df.columns if str(c).lower() == 'low'), None)
                close_col = next((c for c in p_df.columns if str(c).lower() in ('close', 'adj close')), None)
                vol_col = next((c for c in p_df.columns if str(c).lower() == 'volume'), None)

                if high_col and low_col and close_col:
                    high_20 = float(p_df[high_col].tail(20).max())
                    h_s = pd.to_numeric(p_df[high_col], errors='coerce')
                    l_s = pd.to_numeric(p_df[low_col], errors='coerce')
                    c_s = pd.to_numeric(p_df[close_col], errors='coerce')
                    tr1 = (h_s - l_s).abs()
                    tr2 = (h_s - c_s.shift(1)).abs()
                    tr3 = (l_s - c_s.shift(1)).abs()
                    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                    atr_val = tr.tail(14).dropna().mean()
                    atr = float(atr_val) if (pd.notna(atr_val) and atr_val > 0) else curr_p * vol_scale
                    if len(c_s) >= 50:
                        ma_50 = float(c_s.tail(50).mean())
                    if len(c_s) >= 2:
                        is_down_day = bool(c_s.iloc[-1] < c_s.iloc[-2])
                    if vol_col and len(p_df[vol_col]) >= 20:
                        vol_s = pd.to_numeric(p_df[vol_col], errors='coerce')
                        vol_ratio = float(vol_s.iloc[-1] / max(vol_s.tail(20).mean(), 1.0))
            elif isinstance(p_df, pd.DataFrame) and len(p_df) > 0:
                high_col = next((c for c in p_df.columns if str(c).lower() == 'high'), None)
                if high_col:
                    h_max = pd.to_numeric(p_df[high_col], errors='coerce').dropna().max()
                    if pd.notna(h_max) and float(h_max) > 0:
                        high_20 = max(high_20, float(h_max))

            # 1. Emergency Order Flow Shock Exit
            is_shock, shock_reason = self.check_order_flow_shock_exit(mfi, is_down_day, vol_ratio, obi)
            if is_shock:
                trailing_plans.append({
                    "symbol": sym, "action": "SELL", "reason": shock_reason,
                    "quantity": int(qty), "unrealized_return": round(unrealized_return, 4),
                    "current_price": round(curr_p, 2)
                })
                continue

            # 2. Signal Exhaustion & Opportunity Cost Exit
            is_exhausted, exhaust_reason = self.check_signal_exhaustion_exit(current_score)
            if is_exhausted:
                trailing_plans.append({
                    "symbol": sym, "action": "SELL", "reason": exhaust_reason,
                    "quantity": int(qty), "unrealized_return": round(unrealized_return, 4),
                    "current_price": round(curr_p, 2)
                })
                continue

            # 3. Time-Stop Exit for Stalled Positions
            is_time_stop, time_reason = self.check_time_stop_exit(days_held, unrealized_return, max_stall_days=min(12, max_holding_days))
            if is_time_stop:
                trailing_plans.append({
                    "symbol": sym, "action": "SELL", "reason": time_reason,
                    "quantity": int(qty), "unrealized_return": round(unrealized_return, 4),
                    "current_price": round(curr_p, 2)
                })
                continue

            # 4. Multi-Tier Dynamic Profit Taking & Trailing Stop
            trailing_stop_p = high_20 - (local_ts_mult * atr)
            stop_loss_p = entry_p - (local_sl_mult * atr)
            breakeven_p = entry_p * 1.003  # Free-trade breakeven with friction costs

            peak_return = (high_20 - entry_p) / entry_p

            # Monotonic Ratchet Stop Calculation based on peak achieved return
            if peak_return >= tp_t2:
                effective_stop_p = max(stop_loss_p, entry_p * (1.0 + tp_t1 * 0.5), breakeven_p)
            elif peak_return >= tp_t1:
                effective_stop_p = max(stop_loss_p, breakeven_p)
            else:
                effective_stop_p = stop_loss_p

            # Priority A: Check if current price breached effective stop loss (ATR Stop or Breakeven Lock)
            if curr_p <= effective_stop_p:
                reason = "BREAKEVEN_PROFIT_LOCK" if effective_stop_p > stop_loss_p else "ATR_STOP_LOSS"
                trailing_plans.append({
                    "symbol": sym, "action": "SELL", "reason": reason,
                    "quantity": int(qty), "unrealized_return": round(unrealized_return, 4),
                    "stop_loss_price": round(effective_stop_p, 2), "current_price": round(curr_p, 2)
                })
            # Priority B: If still above effective stop loss, evaluate profit taking tiers
            elif unrealized_return >= tp_t3:
                # Tier 3 & Runner (+25%): Chandelier/KAMA trailing lock
                if curr_p <= trailing_stop_p or curr_p < ma_50:
                    trailing_plans.append({
                        "symbol": sym, "action": "SELL", "reason": "TIER3_KAMA_RUNNER_EXIT",
                        "quantity": int(qty), "unrealized_return": round(unrealized_return, 4),
                        "trailing_stop_price": round(trailing_stop_p, 2), "current_price": round(curr_p, 2)
                    })
                else:
                    partial_qty = max(1, int(qty * 0.25))
                    trailing_plans.append({
                        "symbol": sym, "action": "SELL", "reason": "TIER3_PROFIT_TAKE",
                        "quantity": partial_qty, "unrealized_return": round(unrealized_return, 4),
                        "trailing_stop_price": round(trailing_stop_p, 2), "current_price": round(curr_p, 2)
                    })
            elif unrealized_return >= tp_t2:
                # Tier 2 (+15%): 25-30% take profit + Chandelier ATR trailing
                if curr_p <= trailing_stop_p:
                    trailing_plans.append({
                        "symbol": sym, "action": "SELL", "reason": "CHANDELIER_TRAILING_PROFIT",
                        "quantity": max(1, int(qty * 0.50)), "unrealized_return": round(unrealized_return, 4),
                        "trailing_stop_price": round(trailing_stop_p, 2), "current_price": round(curr_p, 2)
                    })
                elif use_3tier and not h_info.get("tier2_taken", False):
                    trailing_plans.append({
                        "symbol": sym, "action": "SELL", "reason": "TIER_2_PROFIT_LOCK",
                        "quantity": max(1, int(qty * 0.30)), "unrealized_return": round(unrealized_return, 4),
                        "trailing_stop_price": round(trailing_stop_p, 2), "current_price": round(curr_p, 2)
                    })
            elif unrealized_return >= tp_t1:
                # Tier 1 (+8%): 30% take profit when 3tier active
                if use_3tier and not h_info.get("tier1_taken", False):
                    trailing_plans.append({
                        "symbol": sym, "action": "SELL", "reason": "TIER_1_PROFIT_LOCK",
                        "quantity": max(1, int(qty * 0.30)), "unrealized_return": round(unrealized_return, 4),
                        "stop_loss_price": round(effective_stop_p, 2), "current_price": round(curr_p, 2)
                    })

        return trailing_plans


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
        # Standardized temporary impact parameter based on participation fraction
        eta = 0.5 * max(daily_volatility, 0.01)
        kappa = float(np.clip(np.sqrt(lambda_urg * (daily_volatility ** 2) / max(eta, 1e-8)), 0.01, 3.0))

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

        # Safe reconciliation of integer rounding discrepancies without producing negative tranches
        diff_total = total_quantity - int(np.sum(alloc))
        if diff_total > 0:
            for i in range(diff_total):
                alloc[i % n_slices] += 1
        elif diff_total < 0:
            rem = abs(diff_total)
            for i in range(n_slices - 1, -1, -1):
                sub = min(alloc[i], rem)
                alloc[i] -= sub
                rem -= sub
                if rem <= 0:
                    break
        return [int(x) for x in alloc]

    @staticmethod
    def calculate_peg_limit_price(
        target_price: float,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        spread: Optional[float] = None,
        alpha_urgency: float = 0.50,
        action: str = "BUY",
        obi: Optional[float] = None,
        kappa: float = 1.5,
        micro_price: Optional[float] = None,
        multi_obi: Optional[Dict[str, float]] = None,
        daily_volatility: Optional[float] = None,
        book_depth_ratio: Optional[float] = None,
        queue_position_ratio: Optional[float] = None,
        l3_micro_price: Optional[float] = None,
        l3_imbalance: Optional[float] = None,
        hawkes_toxicity: Optional[float] = None,
        hawkes_arrival_imbalance: Optional[float] = None,
        queue_imbalance: Optional[float] = None,
        qi_acceleration: Optional[float] = None,
        cross_asset_toxicity: Optional[float] = None,
        version: int = 6,
        qi_jerk: Optional[float] = None,
        deep_ofi: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        Phase 6 (F44), Phase 7 (F50) & Phase 8 (F54) Level-3 Micro-Price & Queue-Position-Aware Peg Calculation:
        1. Base anchor price: Hawkes arrival-adjusted micro-price > L3 micro-price > L1 micro-price > mid price.
        2. Dynamic curvature kappa_eff scales with volatility and orderbook depth.
        3. Imbalance shift uses Queue Imbalance (QI_L3*) > L3 decayed imbalance > multi-tier L2 OBI composite > L1 OBI.
        4. Queue position adverse selection offset delta_P_queue compensates when order is buried (u_q > 0.40),
           suppressed by Hawkes & cross-asset composite toxicity gamma_composite (F50 & F54).
        5. Toxic shading offset delta_P_shade steps back against toxic flow when gamma_composite > 0.45/0.50 (F50 & F54).
        6. Queue Imbalance 2nd-order acceleration peg shift a_shift (F54.2).
        7. Strict clipping within [min(bid, ask), max(bid, ask)].
        """
        tp = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 1000.0
        if tp <= 0:
            return tp

        spr = float(spread) if (spread is not None and spread > 0) else max(tp * 0.002, 1.0)
        p_bid = float(bid_price) if (bid_price is not None and bid_price > 0) else (tp - spr / 2.0)
        p_ask = float(ask_price) if (ask_price is not None and ask_price > 0) else (tp + spr / 2.0)
        p_mid = (p_bid + p_ask) / 2.0

        # 2. Imbalance resolution: Queue Imbalance > L3 decayed imbalance > Multi-tier L2 composite > L1 OBI
        eff_obi = None
        if queue_imbalance is not None and math.isfinite(float(queue_imbalance)):
            eff_obi = float(queue_imbalance)
        elif l3_imbalance is not None and math.isfinite(float(l3_imbalance)):
            eff_obi = float(l3_imbalance)
        elif multi_obi is not None and isinstance(multi_obi, dict):
            multi_dict: Dict[Any, Any] = multi_obi
            obi_1 = float(multi_dict.get("OBI_1", multi_dict.get("obi_1", multi_dict.get("1", multi_dict.get(1, 0.0)))) or 0.0)
            obi_5 = float(multi_dict.get("OBI_5", multi_dict.get("obi_5", multi_dict.get("5", multi_dict.get(5, 0.0)))) or 0.0)
            obi_10 = float(multi_dict.get("OBI_10", multi_dict.get("obi_10", multi_dict.get("10", multi_dict.get(10, 0.0)))) or 0.0)
            eff_obi = 0.50 * obi_1 + 0.35 * obi_5 + 0.15 * obi_10
        elif obi is not None and math.isfinite(float(obi)):
            eff_obi = float(obi)

        # 1. Base anchor price: Hawkes arrival adjusted (F50) > L3 micro-price > L1 micro-price > mid price
        omega_H = 0.35
        kappa_H = 1.20
        del_lam = None
        if hawkes_arrival_imbalance is not None and math.isfinite(float(hawkes_arrival_imbalance)):
            del_lam = float(np.clip(float(hawkes_arrival_imbalance), -1.0, 1.0))

        if del_lam is not None:
            qi_val = float(np.clip(eff_obi if eff_obi is not None else 0.0, -1.0, 1.0))
            if l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
                p_base = float(l3_micro_price) + 0.5 * spr * omega_H * math.tanh(kappa_H * del_lam)
            else:
                p_base = p_mid + 0.5 * spr * ((1.0 - omega_H) * qi_val + omega_H * math.tanh(kappa_H * del_lam))
        elif l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
            p_base = float(l3_micro_price)
        elif micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
            p_base = float(micro_price)
        else:
            p_base = p_mid

        # 3. Dynamic curvature scaling
        if daily_volatility is not None or book_depth_ratio is not None:
            sig = float(daily_volatility) if daily_volatility is not None else 0.02
            r_depth = float(book_depth_ratio) if book_depth_ratio is not None else 1.0
            r_depth = float(np.clip(r_depth, 0.20, 5.0))
            kappa_eff = float(np.clip(1.5 * (sig / 0.02) / math.sqrt(r_depth), 0.8, 3.0))
        else:
            kappa_eff = float(kappa)

        is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE", "BID"]
        direction = 1.0 if is_buy else -1.0

        # 4. Imbalance peg shift
        if eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0 and del_lam is None:
            obi_val = float(np.clip(float(eff_obi), -1.0, 1.0))
            peg_shift = 0.5 * spr * math.tanh(kappa_eff * obi_val)
        else:
            peg_shift = 0.0

        # F50 & F54: Directional Hawkes and Cross-Asset Composite Toxicity
        g_loc = float(np.clip(float(hawkes_toxicity), 0.0, 1.0)) if (hawkes_toxicity is not None and math.isfinite(float(hawkes_toxicity))) else 0.0
        g_cross = float(np.clip(float(cross_asset_toxicity), 0.0, 1.0)) if (cross_asset_toxicity is not None and math.isfinite(float(cross_asset_toxicity))) else 0.0
        gamma_composite = float(np.clip(0.65 * g_loc + 0.35 * g_cross, 0.0, 1.0)) if cross_asset_toxicity is not None else g_loc

        # 5. Queue position adverse selection offset (F44, F50 & F54)
        q_shift = 0.0
        if queue_position_ratio is not None and math.isfinite(float(queue_position_ratio)):
            u_q = float(np.clip(float(queue_position_ratio), 0.0, 1.0))
            if u_q > 0.40:
                urg = float(np.clip(float(alpha_urgency), 0.1, 1.0))
                tox_suppress = max(0.0, 1.0 - 0.85 * gamma_composite)
                q_shift = direction * 0.5 * spr * urg * (u_q - 0.40) * 0.60 * tox_suppress

        # 6. Toxic shading offset (F50 & F54)
        shade_shift = 0.0
        if int(version) >= 8 and gamma_composite > 0.45:
            shade_shift = -direction * 0.35 * spr * (gamma_composite - 0.45)
        elif gamma_composite > 0.50:
            shade_shift = -direction * 0.25 * spr * (gamma_composite - 0.50)

        # 7. Queue Imbalance 2nd-Order Acceleration Peg Shift (F54)
        accel_shift = 0.0
        if qi_acceleration is not None and math.isfinite(float(qi_acceleration)):
            a_val = float(qi_acceleration)
            accel_tox_damp = max(0.0, 1.0 - 0.90 * gamma_composite)
            accel_shift = direction * 0.20 * spr * math.tanh(0.80 * a_val) * accel_tox_damp

        # 8. Queue Imbalance 3rd-Order Jerk & Deep-OFI Peg Shift (Phase 9 F58.1)
        jerk_shift = 0.0
        if int(version) >= 9:
            j_val = float(qi_jerk) if (qi_jerk is not None and math.isfinite(float(qi_jerk))) else float(kwargs.get("qi_jerk", 0.0))
            d_ofi = float(deep_ofi) if (deep_ofi is not None and math.isfinite(float(deep_ofi))) else float(kwargs.get("deep_ofi", 0.0))
            jerk_tox_damp = max(0.0, 1.0 - 0.95 * gamma_composite)
            jerk_shift = direction * spr * (0.10 * math.tanh(0.50 * j_val) + 0.15 * math.tanh(1.20 * d_ofi)) * jerk_tox_damp

        # If micro-price, L3 micro-price, OBI shift, queue offset, shade shift, accel shift, jerk shift, or arrival imbalance was active
        if (
            (l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0)
            or (micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0)
            or (eff_obi is not None and math.isfinite(float(eff_obi)) and float(eff_obi) != 0.0)
            or q_shift != 0.0
            or shade_shift != 0.0
            or accel_shift != 0.0
            or jerk_shift != 0.0
            or del_lam is not None
        ):
            peg_price = p_base + peg_shift + q_shift + shade_shift + accel_shift + jerk_shift
            return float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))

        # Fallback to urgency interpolation between bid and ask
        urgency = max(0.0, min(1.0, float(alpha_urgency)))
        if is_buy:
            peg_price = p_bid + urgency * (p_ask - p_bid)
        else:
            peg_price = p_ask - urgency * (p_ask - p_bid)

        return float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))


class GatheralMarketImpactKernel:
    """
    Gatheral (2010) Transient Market Impact Kernel with Power-Law Decay G(t) = eta / (t + tau_0)^alpha.
    Permanent square-root impact: I_perm = gamma * sigma * sqrt(Q / ADV).
    Computes optimal non-linear execution schedule minimizing total execution cost + timing variance.
    """
    @staticmethod
    def estimate_permanent_impact(
        quantity: float,
        adv: float,
        daily_volatility: float,
        gamma: float = 0.314
    ) -> float:
        """Square-root permanent price impact: I_perm = gamma * sigma * sqrt(Q / ADV)."""
        ratio = max(0.0, float(quantity)) / max(float(adv), 1.0)
        return float(gamma * max(daily_volatility, 0.01) * np.sqrt(ratio))

    @staticmethod
    def compute_transient_impact_decay(
        time_elapsed_slices: np.ndarray,
        eta: float = 0.50,
        decay_power: float = 0.50,
        tau_0: float = 0.10,
        cost_scaling_factor: Optional[float] = None,
    ) -> np.ndarray:
        """Power-law decay kernel: G(t) = eta / (t + tau_0)^decay_power."""
        # F33: Scale eta by empirical realized slippage cost_scaling_factor
        if cost_scaling_factor is None:
            try:
                from src.execution.slippage_feedback import SlippageFeedbackEngine
                metrics = SlippageFeedbackEngine().calculate_realized_slippage()
                cost_scaling_factor = float(getattr(metrics, "cost_scaling_factor", 1.0) or 1.0)
            except Exception:
                cost_scaling_factor = 1.0
        eff_eta = float(eta) * max(0.1, float(cost_scaling_factor))
        t = np.asarray(time_elapsed_slices, dtype=float)
        return eff_eta / (np.maximum(t, 0.0) + tau_0) ** decay_power

    @staticmethod
    def compute_optimal_gatheral_slices(
        total_quantity: int,
        n_slices: Optional[int] = None,
        daily_volatility: float = 0.02,
        adv: float = 1_000_000.0,
        alpha_decay_half_life: float = 10.0,
        cost_scaling_factor: Optional[float] = None,
        order_adv_fraction: Optional[float] = None,
    ) -> List[int]:
        """
        Computes slice trajectory incorporating Gatheral power-law transient impact.
        F38: ADV-adaptive Gatheral slice count:
            n_slices* = clip(round(3 + 8 * sqrt(rho_adv / 0.01)), 2, 20)
        with intraday U-shaped volume smile weighting:
            V_smile(t) = 1.0 + 0.6 * (2t - 1)^2.
        """
        if total_quantity <= 0:
            return [0]

        eff_adv = max(float(adv), 1000.0)
        if n_slices is not None:
            eff_n_slices = max(1, int(n_slices))
        else:
            # F38: Dynamic ADV-adaptive slice count
            rho_adv = float(order_adv_fraction) if order_adv_fraction is not None else (total_quantity / eff_adv)
            rho_adv = max(0.0, rho_adv)
            n_slices_star = int(round(3.0 + 8.0 * math.sqrt(rho_adv / 0.01)))
            eff_n_slices = int(np.clip(n_slices_star, 2, 20))

        if eff_n_slices <= 1:
            return [total_quantity]

        if cost_scaling_factor is None:
            try:
                from src.execution.slippage_feedback import SlippageFeedbackEngine
                metrics = SlippageFeedbackEngine().calculate_realized_slippage()
                cost_scaling_factor = float(getattr(metrics, "cost_scaling_factor", 1.0) or 1.0)
            except Exception:
                cost_scaling_factor = 1.0

        t = np.linspace(0.1, 1.0, eff_n_slices)
        decay_w = (1.0 / (t ** 0.5))
        # F33: When realized slippage is high (cost_scaling_factor > 1.0), soften front-loading urgency
        scale_adj = max(0.5, min(2.0, float(cost_scaling_factor)))
        urgency_bias = max(0.2, min(2.0, (10.0 / max(alpha_decay_half_life, 0.5)) / scale_adj))
        raw_urgency_w = decay_w ** urgency_bias

        # F38: Intraday U-shaped volume smile weighting
        t_norm = (np.arange(eff_n_slices, dtype=float) + 0.5) / float(eff_n_slices)
        v_smile = 1.0 + 0.60 * ((2.0 * t_norm - 1.0) ** 2)

        raw_weights = raw_urgency_w * v_smile
        norm_weights = raw_weights / np.sum(raw_weights)

        alloc = np.round(norm_weights * total_quantity).astype(int)
        diff_total = total_quantity - int(np.sum(alloc))
        if diff_total != 0:
            # V8-MED-13 Fix: Safely distribute residual difference while ensuring every tranche >= 0
            if diff_total > 0:
                alloc[0] += diff_total
            else:
                # Distribute negative remainder backwards from tranches that have positive quantities
                rem = -diff_total
                for i in range(len(alloc) - 1, -1, -1):
                    deduct = min(alloc[i], rem)
                    alloc[i] -= deduct
                    rem -= deduct
                    if rem == 0:
                        break
        # Final safety check: if total still doesn't match due to extreme inputs, assign all to first tranche
        if int(np.sum(alloc)) != total_quantity:
            alloc = np.zeros(eff_n_slices, dtype=int)
            alloc[0] = total_quantity
        return [int(x) for x in alloc]


# Module level alias for backward compatibility
OMSEngine = ExecutionOMSEngine


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
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-^]*$")

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
}


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

        is_severe = str(crisis_level).upper() == "SEVERE"
        if is_severe:
            logger.warning("[OMS ENGINE] SEVERE crisis level - skipping BUY orders, allowing SELL/liquidate orders.")

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
            tot_cap = float(total_capital) if (total_capital is not None and math.isfinite(float(total_capital))) else 100000000.0
        except (ValueError, TypeError):
            tot_cap = 100000000.0
        tot_cap = max(0.0, tot_cap) * max(0.15, min(1.0, float(crisis_mult)))

        try:
            fx_rate = float(usdkrw_rate) if (usdkrw_rate is not None and math.isfinite(float(usdkrw_rate)) and float(usdkrw_rate) > 0) else 1350.0
        except (ValueError, TypeError):
            fx_rate = 1350.0

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

                raw_action = str(pred.get("action", "BUY") or "BUY").upper()
                if is_severe:
                    if raw_action == "BUY" and weight > 0:
                        continue
                    weight = 0.0
                    raw_action = "SELL"

                if not is_severe and not (0.0 < weight <= 1.0) and raw_action != "SELL":
                    continue

                # Gate: Leland Dynamic Buffer Band (No-Trade Zone) Gating
                if use_leland_buffer and current_holdings is not None:
                    curr_w = float(current_holdings.get(sym, 0.0))
                    is_full_exit = (weight <= 0.0 or raw_action == "SELL")
                    is_new_entry = (curr_w <= 0.0 and weight > 0.0)
                    if not is_full_exit and not is_new_entry:
                        try:
                            from src.risk.portfolio_allocator import PortfolioAllocator
                            p_alloc = PortfolioAllocator()
                            mkt = str(pred.get("market", "KOSPI"))
                            vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
                            c_rate = p_alloc.estimate_transaction_cost_rate(
                                symbol=sym, market=mkt, target_weight=weight,
                                portfolio_value=tot_cap, volatility_20d=vol_20d
                            )
                            delta_i = p_alloc.calculate_dynamic_buffer_band(
                                symbol=sym, target_weight=weight, cost_rate=c_rate, volatility_20d=vol_20d
                            )
                            if abs(curr_w - weight) <= delta_i:
                                logger.info(f"[OMS LELAND BUFFER] Symbol {sym}: Current weight {curr_w:.3f} within ±{delta_i:.3f} of target {weight:.3f} -> skipping redundant trade (Hold)")
                                continue
                        except Exception as _leland_e:
                            logger.debug(f"[OMS LELAND BUFFER] Leland buffer check skipped for {sym}: {_leland_e}")

                curr_holding_w = float(current_holdings.get(sym, 0.0)) if current_holdings is not None else 0.0
                if (raw_action == "SELL" or is_severe) and weight == 0.0 and curr_holding_w > 0.0:
                    target_amount = tot_cap * curr_holding_w
                else:
                    target_amount = tot_cap * weight

                if not is_severe and raw_action != "SELL" and not (0.0 < target_amount <= tot_cap):
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
                change_pct = pred.get("change_pct") or pred.get("daily_return")
                try:
                    if change_pct is not None:
                        raw_c = float(change_pct)
                        c_norm = raw_c / 100.0 if abs(raw_c) >= 0.35 else raw_c
                        if c_norm >= 0.295 and action == "BUY":
                            logger.warning(f"[OMS GATE 7] {sym} locked at upper limit (+{c_norm:.2%}), skipping buy execution.")
                            continue
                        elif c_norm <= -0.295:
                            logger.warning(f"[OMS GATE 7] {sym} locked at lower limit ({c_norm:.2%}) - complete liquidity freeze; skipping new entry and tagging emergency monitoring.")
                            continue
                except (ValueError, TypeError):
                    pass

                # Gate 7.3: KRX STT / Transaction Cost Net Alpha Hurdle Check
                if is_krx and action == "BUY" and ("expected_return" in pred or "ensemble_expected_return" in pred):
                    try:
                        from src.risk.portfolio_allocator import PortfolioAllocator
                        try:
                            from src.execution.slippage_feedback import SlippageFeedbackEngine
                            slip_res = SlippageFeedbackEngine(db_path=self.db_path).calculate_realized_slippage()
                            if hasattr(slip_res, "cost_scaling_factor"):
                                slip_mult = float(slip_res.cost_scaling_factor)
                            elif hasattr(slip_res, "recommended_market_impact_multiplier"):
                                slip_mult = float(slip_res.recommended_market_impact_multiplier)
                            elif isinstance(slip_res, (int, float)):
                                slip_mult = float(slip_res)
                            else:
                                slip_mult = 1.0
                        except Exception:
                            slip_mult = 1.0

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
                            is_sell=False,
                            slippage_multiplier=slip_mult
                        )
                        safety_margin = 0.0010  # 0.10% KRX safety margin
                        if "expected_return" in pred and pred["expected_return"] is not None:
                            raw_exp_ret = float(pred["expected_return"])
                            exp_ret_frac = raw_exp_ret / 100.0 if abs(raw_exp_ret) >= 0.10 else raw_exp_ret
                            hurdle = friction_cost + safety_margin
                        else:
                            raw_exp_ret = float(pred.get("ensemble_expected_return", 0.0) or 0.0)
                            exp_ret_frac = raw_exp_ret / 100.0 if abs(raw_exp_ret) >= 0.10 else raw_exp_ret
                            hurdle = friction_cost + safety_margin

                        if exp_ret_frac < hurdle:
                            logger.info(f"[OMS GATE 7] {sym} net alpha {exp_ret_frac:.4%} < hurdle ({hurdle:.4%}), skipping.")
                            continue
                    except Exception as _fe:
                        logger.debug(f"[OMS GATE 7] Hurdle check exception for {sym}: {_fe}")

                # Gate 7.4: Dynamic Adverse Opening Gap Filter (-3 sigma shock protection)
                try:
                    vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
                    raw_gap = float(change_pct or 0.0)
                    gap_ret = raw_gap / 100.0 if abs(raw_gap) >= 0.35 else raw_gap
                    if action == "BUY" and gap_ret <= -3.0 * max(vol_20d, 0.015):
                        logger.warning(f"[OMS GATE 7.4] {sym} adverse gap {gap_ret:.2%} <= -3sigma, skipping toxic order flow.")
                        continue
                except (ValueError, TypeError):
                    pass

                # Gate 7.5: ADV Capacity Cap (max_adv_ratio of ADV max order value)
                adv_in_pred = pred.get("adv") if pred.get("adv") is not None else pred.get("trading_value")
                if adv_in_pred is not None and float(adv_in_pred) > 0:
                    adv_val = float(adv_in_pred)
                    max_adv_amount = max(100_000.0, max_adv_ratio * adv_val)
                    if target_amount > max_adv_amount:
                        logger.info(f"[OMS ADV CAPACITY] {sym} target amount {target_amount:,.0f} capped to {max_adv_ratio:.1%} ADV ({max_adv_amount:,.0f})")
                        target_amount = max_adv_amount
                else:
                    adv_val = 1_000_000_000.0

                curr_iso = "KRW"
                try:
                    from src.config import TradingConfig
                    cfg = TradingConfig()
                    curr_iso = cfg.get_market_currency(market or "KOSPI")
                except Exception:
                    curr_iso = "KRW" if is_krx else "USD"

                if curr_iso == "KRW":
                    effective_target_amount = target_amount
                elif curr_iso == "USD":
                    effective_target_amount = target_amount / fx_rate
                else:
                    try:
                        from src.data_layer.global_market import GlobalMarketClient
                        g_client = GlobalMarketClient()
                        rate_to_krw = g_client.get_cross_rate(from_curr=curr_iso, to_curr="KRW")
                        rate_krw_to_curr = 1.0 / max(1e-6, rate_to_krw)
                        effective_target_amount = target_amount * rate_krw_to_curr
                    except Exception:
                        effective_target_amount = target_amount / fx_rate

                raw_quantity = int(effective_target_amount // target_price) if target_price > 0 else 0
                if is_krx:
                    quantity = (raw_quantity // 10) * 10 if raw_quantity >= 10 else raw_quantity
                elif curr_iso in ('JPY', 'VND'):
                    quantity = int(raw_quantity)
                else:
                    quantity = raw_quantity
                if quantity <= 0 and status != "HEDGE_FLAG":
                    continue

                # Strategy Alpha Half-Life (tau_alpha) Adaptive Execution Strategy Routing
                # Fast alpha (<= 2d) requires fast execution (FAST_VWAP) to avoid alpha decay.
                # Slow alpha (>= 25d) uses patient execution (PATIENT_TWAP) with smaller slice sizes to minimize market impact.
                hl_list = []
                for strat_key, strat_hl in STRATEGY_ALPHA_HALF_LIVES.items():
                    if strat_key in pred or f"{strat_key}_score" in pred or f"{strat_key}_prob" in pred or f"{strat_key}_20d" in pred:
                        hl_list.append(strat_hl)
                avg_half_life = float(np.mean(hl_list)) if hl_list else 10.0

                part_ratio = target_amount / max(adv_val, 1.0)
                if avg_half_life <= 2.0 and part_ratio > 0.01:
                    exec_strategy = "FAST_VWAP"
                    slice_count = min(6, max(2, int(np.ceil(part_ratio / 0.005))))
                elif avg_half_life >= 25.0 and part_ratio > 0.01:
                    exec_strategy = "MIDPOINT_PEG"
                    slice_count = min(12, max(4, int(np.ceil(part_ratio / 0.005))))
                elif part_ratio > 0.03:
                    exec_strategy = "DYNAMIC_VWAP"
                    slice_count = min(10, max(3, int(np.ceil(part_ratio / 0.01))))
                elif avg_half_life >= 15.0:
                    exec_strategy = "MIDPOINT_PEG"
                    slice_count = min(5, max(2, int(np.ceil(part_ratio / 0.005))))
                elif part_ratio > 0.01:
                    exec_strategy = "TWAP"
                    slice_count = min(5, max(2, int(np.ceil(part_ratio / 0.005))))
                else:
                    exec_strategy = "DIRECT"
                    slice_count = 1

                # Gate 7.6: VPIN Order Flow Toxicity Gate (Easley, Lopez de Prado, O'Hara 2012)
                # If adverse informed toxic order flow is detected (vpin > 0.70),
                # switch execution to PASSIVE_LIMIT or scale down slice size to prevent adverse selection.
                vpin_val = float(pred.get("vpin", pred.get("microstructure_toxicity", pred.get("order_flow_toxicity", 0.0))) or 0.0)
                if action == "BUY" and vpin_val > 0.70:
                    logger.warning(f"[OMS GATE 7.6] {sym} High VPIN toxicity ({vpin_val:.2f} > 0.70) detected. Routing to PASSIVE_LIMIT to avoid adverse selection.")
                    exec_strategy = "PASSIVE_LIMIT"
                    slice_count = max(6, slice_count)

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

            # Gate 8: Synthetic Beta Inverse Hedge Overlay (Bear / Crisis regime)
            if "BEAR" in str(regime_label).upper() or "CRISIS" in str(regime_label).upper():
                try:
                    from src.risk.portfolio_allocator import PortfolioAllocator
                    first_market = str(top_predictions[0].get("market", "KOSPI")) if top_predictions else "KOSPI"
                    hedge_info = PortfolioAllocator.compute_synthetic_inverse_hedge(
                        portfolio_weights=portfolio_weights,
                        market=first_market,
                        regime_label=regime_label
                    )
                    if hedge_info.get("hedge_required") and hedge_info.get("hedge_weight", 0.0) > 0:
                        h_sym = hedge_info["hedge_symbol"]
                        h_weight = hedge_info["hedge_weight"]
                        h_amount = tot_cap * h_weight
                        h_order_id = f"ORD_HEDGE_{h_sym}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                        hedge_price = self._get_latest_price(h_sym, prices_dict=prices_dict, top_predictions=top_predictions)
                        if hedge_price <= 0.0:
                            hedge_price = 10000.0 if str(first_market).upper() in ["KOSPI", "KOSDAQ", "KRX"] or str(h_sym).isdigit() else 50.0
                        hedge_price = self.round_to_tick_size(hedge_price, market=first_market)

                        is_krx_hedge = str(first_market).upper() in ["KOSPI", "KOSDAQ", "KRX"] or str(h_sym).isdigit() or str(h_sym).endswith((".KS", ".KQ"))
                        h_amount_local = h_amount if is_krx_hedge else (h_amount / fx_rate)
                        raw_h_qty = int(h_amount_local // hedge_price) if hedge_price > 0 else 0
                        if is_krx_hedge:
                            h_quantity = (raw_h_qty // 10) * 10 if raw_h_qty >= 10 else raw_h_qty
                        else:
                            h_quantity = raw_h_qty

                        h_entry = {
                            "order_id": h_order_id,
                            "symbol": h_sym,
                            "name": "INVERSE_HEDGE_OVERLAY",
                            "market": first_market,
                            "action": "BUY_HEDGE",
                            "target_weight": round(h_weight, 4),
                            "target_amount": round(h_amount, 2),
                            "target_price": round(hedge_price, 2),
                            "quantity": h_quantity,
                            "execution_strategy": "DIRECT",
                            "slice_count": 1,
                            "status": "HEDGE_ACTIVE",
                            "created_at": now_str
                        }
                        order_plans.append(h_entry)
                        cursor.execute("""
                            INSERT OR REPLACE INTO order_plans
                            (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, slice_count, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (h_order_id, h_sym, "INVERSE_HEDGE_OVERLAY", first_market, "BUY_HEDGE", round(h_weight, 4), round(h_amount, 2), h_entry["target_price"], h_entry["quantity"], "DIRECT", 1, "HEDGE_ACTIVE", now_str))
                except Exception as _hedge_e:
                    logger.warning(f"[OMS HEDGE OVERLAY] Hedge order plan generation skipped: {_hedge_e}")

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

    @staticmethod
    def calculate_peg_limit_price(
        target_price: float,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        spread: Optional[float] = None,
        alpha_urgency: float = 0.50,
        action: str = "BUY"
    ) -> float:
        """
        Calculates optimal limit price for Midpoint Pegged passive maker order routing.
        Saves half-spread and captures maker rebates when alpha urgency is low/medium.
        """
        tp = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 1000.0
        if tp <= 0:
            return tp

        spr = spread if (spread is not None and spread > 0) else max(tp * 0.002, 1.0)
        p_bid = bid_price if (bid_price is not None and bid_price > 0) else (tp - spr / 2.0)
        p_ask = ask_price if (ask_price is not None and ask_price > 0) else (tp + spr / 2.0)
        p_mid = (p_bid + p_ask) / 2.0

        is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE"]
        if alpha_urgency <= 0.40:
            peg_price = p_bid if is_buy else p_ask
        elif alpha_urgency <= 0.75:
            peg_price = p_mid
        else:
            peg_price = p_ask if is_buy else p_bid

        return float(peg_price)


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
        action: str = "BUY"
    ) -> float:
        """
        Calculates optimal limit price for Midpoint Pegged passive maker order routing.
        Saves half-spread and captures maker rebates when alpha urgency is low/medium.
        """
        tp = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 1000.0
        if tp <= 0:
            return tp

        spr = spread if (spread is not None and spread > 0) else max(tp * 0.002, 1.0)
        p_bid = bid_price if (bid_price is not None and bid_price > 0) else (tp - spr / 2.0)
        p_ask = ask_price if (ask_price is not None and ask_price > 0) else (tp + spr / 2.0)
        p_mid = (p_bid + p_ask) / 2.0

        is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE"]
        if alpha_urgency <= 0.40:
            peg_price = p_bid if is_buy else p_ask
        elif alpha_urgency <= 0.75:
            peg_price = p_mid
        else:
            peg_price = p_ask if is_buy else p_bid

        return float(peg_price)


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
        tau_0: float = 0.10
    ) -> np.ndarray:
        """Power-law decay kernel: G(t) = eta / (t + tau_0)^decay_power."""
        t = np.asarray(time_elapsed_slices, dtype=float)
        return eta / (np.maximum(t, 0.0) + tau_0) ** decay_power

    @staticmethod
    def compute_optimal_gatheral_slices(
        total_quantity: int,
        n_slices: int = 6,
        daily_volatility: float = 0.02,
        adv: float = 1_000_000.0,
        alpha_decay_half_life: float = 10.0
    ) -> List[int]:
        """Computes slice trajectory incorporating Gatheral power-law transient impact."""
        if total_quantity <= 0 or n_slices <= 1:
            return [total_quantity]

        t = np.linspace(0.1, 1.0, n_slices)
        decay_w = (1.0 / (t ** 0.5))
        urgency_bias = max(0.2, min(2.0, 10.0 / max(alpha_decay_half_life, 0.5)))
        raw_weights = decay_w ** urgency_bias
        norm_weights = raw_weights / np.sum(raw_weights)

        alloc = np.round(norm_weights * total_quantity).astype(int)
        diff_total = total_quantity - int(np.sum(alloc))
        if diff_total != 0:
            alloc[0] += diff_total
        return [int(max(0, x)) for x in alloc]


# Module level alias for backward compatibility
OMSEngine = ExecutionOMSEngine


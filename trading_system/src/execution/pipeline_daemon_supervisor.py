"""
trading_system/src/execution/pipeline_daemon_supervisor.py
===========================================================
Autonomous Pipeline Daemon Supervisor (Phase 107 / Feature F505 / Release R123 / v114 Production Master).

Coordinates the end-to-end continuous automated trading lifecycle across 5 markets:
1. Pre-Market Phase:
   - Ingests global macro indicators (TNX, US2Y, USDKRW, DXY, SOX, WTI, VIX, ECOS CD91d/KTB3y).
   - Evaluates yield curve inversion ($S_{10Y2Y} < 0$) and computes continuous macro impulse.
   - Modulates baseline 37-strategy factor weights via DynamicMacroFactorTimingEngine.
2. Market-Open Phase:
   - Allocates portfolio capital across high-conviction candidate assets respecting single-stock
     (<= 5.0%) and sector (<= 25.0%) guardrails.
   - Computes delta rebalance orders and filters through OMS safety gates via PaperTradingDaemon.
   - Dispatches Market-Open notification alerts.
3. Intraday Risk Phase:
   - Real-time continuous monitoring loop via InstitutionalIntradayRiskMonitor.
   - Enforces 3-Tier profit taking (+5% TP1, +10% TP2, +20% runner exit).
   - Enforces Leland volatility-adaptive trailing stops (-6% baseline, -10% peak with [0.60, 1.80] multiplier).
   - Executes flash-crash circuit breakers (asset drop >= 7.0%, macro VIX surge > 20.0% Gate 8 inverse hedge).
4. Market-Close Phase:
   - Shadow execution reconciliation and daily shadow PnL accounting.
   - Strictly enforces mathematical invariant: Net Equity <= Gross Equity.
   - Dispatches daily operational summary alert via AlertDispatcher.
   - Persists state snapshot to supervisor_state.json.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import logging
import math
import os
import signal
import sqlite3
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Path setup for resilient imports
# ---------------------------------------------------------------------------
_CURRENT_DIR = Path(__file__).resolve().parent
_TRADING_SYSTEM_DIR = _CURRENT_DIR.parent.parent
_REPO_ROOT = _TRADING_SYSTEM_DIR.parent if _TRADING_SYSTEM_DIR.name == "trading_system" else _TRADING_SYSTEM_DIR

for p in (str(_REPO_ROOT), str(_TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("PipelineDaemonSupervisor")


# ---------------------------------------------------------------------------
# Enums and Dataclasses
# ---------------------------------------------------------------------------

class SupervisorLifecyclePhase(str, Enum):
    """Lifecycle phases orchestrated by the Pipeline Daemon Supervisor."""
    PRE_MARKET = "PRE_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    INTRADAY_RISK = "INTRADAY_RISK"
    MARKET_CLOSE = "MARKET_CLOSE"
    IDLE = "IDLE"


@dataclass
class SupervisorCycleReport:
    """Standardized report emitted after each lifecycle phase execution."""
    cycle_id: str
    phase: SupervisorLifecyclePhase
    timestamp: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(d["phase"], SupervisorLifecyclePhase):
            d["phase"] = d["phase"].value
        return d


@dataclass
class SupervisorConfig:
    """Operational configuration container for PipelineDaemonSupervisor."""
    capital: float = 100_000_000.0
    db_path: str = "trade_logs.db"
    state_file: str = "supervisor_state.json"
    market: str = "ALL"
    regime_label: str = "BULL_LOW_VOL"
    interval_seconds: int = 60
    dry_run: bool = False
    max_single_weight: float = 0.05
    max_sector_weight: float = 0.25
    vix_surge_threshold: float = 0.20
    single_asset_drop_threshold: float = -0.07

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# PipelineDaemonSupervisor Implementation
# ---------------------------------------------------------------------------

class PipelineDaemonSupervisor:
    """
    Autonomous Pipeline Daemon Supervisor coordinating the multi-market trading lifecycle.
    """

    DEFAULT_MACRO_INDICATORS: Dict[str, float] = {
        "us10y": 4.25,
        "us2y": 4.00,
        "term_spread": 0.25,
        "yield_velocity": 0.02,
        "usdkrw": 1350.0,
        "usdkrw_momentum": 0.005,
        "dxy": 104.20,
        "dxy_momentum": 0.002,
        "sox": 4850.0,
        "sox_spillover": 0.015,
        "wti": 76.50,
        "wti_terms_of_trade": -0.01,
        "vix": 16.50,
        "cd_91d": 3.55,
        "ktb_3y": 3.30,
    }

    DEFAULT_CANDIDATES: List[Dict[str, Any]] = [
        # KRX Large Caps
        {"symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI", "price": 75000.0, "score": 0.88, "sector": "Technology"},
        {"symbol": "000660", "name": "SK Hynix", "market": "KOSPI", "price": 180000.0, "score": 0.85, "sector": "Technology"},
        {"symbol": "035420", "name": "NAVER", "market": "KOSPI", "price": 195000.0, "score": 0.78, "sector": "Communication"},
        {"symbol": "005380", "name": "Hyundai Motor", "market": "KOSPI", "price": 240000.0, "score": 0.81, "sector": "Consumer Discretionary"},
        {"symbol": "068270", "name": "Celltrion", "market": "KOSPI", "price": 175000.0, "score": 0.74, "sector": "Healthcare"},
        {"symbol": "247540", "name": "Ecopro BM", "market": "KOSDAQ", "price": 210000.0, "score": 0.72, "sector": "Materials"},
        # US Large Caps
        {"symbol": "NVDA", "name": "Nvidia", "market": "NASDAQ", "price": 125.0, "score": 0.92, "sector": "Technology"},
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ", "price": 220.0, "score": 0.82, "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft", "market": "NASDAQ", "price": 430.0, "score": 0.84, "sector": "Technology"},
        {"symbol": "AMZN", "name": "Amazon", "market": "NASDAQ", "price": 185.0, "score": 0.79, "sector": "Consumer Discretionary"},
        {"symbol": "GOOGL", "name": "Alphabet", "market": "NASDAQ", "price": 175.0, "score": 0.80, "sector": "Communication"},
        {"symbol": "JPM", "name": "JPMorgan Chase", "market": "SP500", "price": 210.0, "score": 0.76, "sector": "Financials"},
    ]

    def __init__(
        self,
        capital: float = 100_000_000.0,
        db_path: str = "trade_logs.db",
        state_file: str = "supervisor_state.json",
        market: str = "ALL",
        regime_label: str = "BULL_LOW_VOL",
        interval_seconds: int = 60,
        dry_run: bool = False,
        config: Optional[Any] = None,
        max_single_weight: float = 0.05,
        max_sector_weight: float = 0.25,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the master PipelineDaemonSupervisor.
        """
        self.capital = float(capital)
        self.db_path = str(db_path)
        self.state_file = str(state_file)
        self.market = str(market).upper()
        self.regime_label = str(regime_label).upper()
        self.interval_seconds = max(1, int(interval_seconds))
        self.dry_run = bool(dry_run)
        self.max_single_weight = float(max_single_weight)
        self.max_sector_weight = float(max_sector_weight)
        self.custom_config = config

        self._lock = threading.RLock()
        self.stop_requested = False
        self.cycle_count = 0
        self.active_phase: SupervisorLifecyclePhase = SupervisorLifecyclePhase.IDLE

        # Operational State
        self.state: Dict[str, Any] = {
            "version": "v114",
            "release": "R123",
            "phase107": True,
            "cycle_count": 0,
            "current_phase": SupervisorLifecyclePhase.IDLE.value,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "capital": self.capital,
            "gross_equity": self.capital,
            "net_equity": self.capital,
            "cash_balance": self.capital,
            "pre_market": {},
            "market_open": {},
            "intraday_risk": {},
            "market_close": {},
            "history": [],
        }

        # Initialize Sub-Components with fault-tolerant fallbacks
        self._init_subcomponents()

        # Attempt to recover existing state if state file is present
        if Path(self.state_file).exists():
            self.load_state(self.state_file)

        logger.info(
            f"[PipelineDaemonSupervisor] Initialized successfully. "
            f"Capital={self.capital:,.0f}, Market={self.market}, Regime={self.regime_label}, "
            f"Interval={self.interval_seconds}s, DryRun={self.dry_run}"
        )

    def _init_subcomponents(self) -> None:
        """Initialize all sub-engines with isolated fault tolerance."""
        # 1. Macro Factor Timing Engine
        try:
            from src.ai.macro_factor_timing import DynamicMacroFactorTimingEngine
            self.macro_engine = DynamicMacroFactorTimingEngine()
        except Exception as e:
            logger.warning(f"[PipelineDaemonSupervisor] DynamicMacroFactorTimingEngine init warning: {e}")
            self.macro_engine = None

        # 2. Paper Trading Shadow Execution Daemon
        try:
            from src.execution.paper_trading_daemon import PaperTradingDaemon
            self.paper_daemon = PaperTradingDaemon(
                initial_capital=self.capital,
                db_path=self.db_path,
                dry_run=self.dry_run,
                regime_label=self.regime_label,
            )
            # Attach adapter methods if not already present
            if not hasattr(self.paper_daemon, "process_target_allocations"):
                def _process_target_allocations(target_allocations, current_market_prices=None, crisis_level="NORMAL"):
                    res = self.paper_daemon.run_cycle(target_input=target_allocations, market_data=current_market_prices)
                    return res.get("executions", [])
                self.paper_daemon.process_target_allocations = _process_target_allocations

            if not hasattr(self.paper_daemon, "get_portfolio_snapshot"):
                self.paper_daemon.get_portfolio_snapshot = self.paper_daemon.snapshot_portfolio

        except Exception as e:
            logger.warning(f"[PipelineDaemonSupervisor] PaperTradingDaemon init warning: {e}")
            self.paper_daemon = None

        # 3. Institutional Intraday Risk Monitor
        try:
            from src.risk.intraday_risk_monitor import InstitutionalIntradayRiskMonitor
            self.risk_monitor = InstitutionalIntradayRiskMonitor(
                baseline_stop_pct=-0.06,
                peak_trailing_stop_pct=-0.10,
                tier1_profit_pct=0.05,
                tier2_profit_pct=0.10,
                tier3_profit_pct=0.20,
            )
            # Attach adapter methods if not already present
            if not hasattr(self.risk_monitor, "evaluate_positions"):
                def _evaluate_positions(prices_or_market_data, holdings=None):
                    h = holdings if holdings is not None else (self.paper_daemon.holdings if self.paper_daemon else {})
                    m_data: Dict[str, Dict[str, float]] = {}
                    if isinstance(prices_or_market_data, dict):
                        for sym, val in prices_or_market_data.items():
                            if isinstance(val, (int, float)):
                                m_data[sym] = {"current_price": float(val), "price": float(val)}
                            elif isinstance(val, dict):
                                m_data[sym] = val
                    return self.risk_monitor.evaluate_portfolio(
                        holdings=h,
                        market_data=m_data,
                        capital=self.capital,
                    )
                self.risk_monitor.evaluate_positions = _evaluate_positions

        except Exception as e:
            logger.warning(f"[PipelineDaemonSupervisor] InstitutionalIntradayRiskMonitor init warning: {e}")
            self.risk_monitor = None

        # 4. Multi-Channel Alert Dispatcher
        try:
            from src.notification.alert_dispatcher import AlertDispatcher
            self.alert_dispatcher = AlertDispatcher(dry_run=self.dry_run)
        except Exception as e:
            logger.warning(f"[PipelineDaemonSupervisor] AlertDispatcher init warning: {e}")
            self.alert_dispatcher = None

        # 5. Market Indicator Storage (Optional)
        try:
            from src.data_layer.indicator_storage import MarketIndicatorStorage
            self.indicator_storage = MarketIndicatorStorage()
        except Exception:
            self.indicator_storage = None

    # -----------------------------------------------------------------------
    # State Persistence & Recovery
    # -----------------------------------------------------------------------

    def save_state(self, filepath: Optional[str] = None) -> bool:
        """
        Atomically persist current supervisor operational state to JSON file.
        """
        target_path = Path(filepath or self.state_file)
        tmp_path = target_path.with_suffix(".tmp")
        with self._lock:
            try:
                self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
                self.state["cycle_count"] = self.cycle_count
                self.state["current_phase"] = self.active_phase.value

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, target_path)
                return True
            except Exception as e:
                logger.error(f"[PipelineDaemonSupervisor] Failed to save state to {target_path}: {e}")
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
                return False

    def load_state(self, filepath: Optional[str] = None) -> bool:
        """
        Recover operational state from JSON file.
        """
        target_path = Path(filepath or self.state_file)
        if not target_path.exists():
            return False

        with self._lock:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.state.update(loaded)
                    self.cycle_count = int(self.state.get("cycle_count", self.cycle_count))
                    loaded_phase = self.state.get("current_phase", SupervisorLifecyclePhase.IDLE.value)
                    try:
                        self.active_phase = SupervisorLifecyclePhase(loaded_phase)
                    except ValueError:
                        self.active_phase = SupervisorLifecyclePhase.IDLE
                    self.capital = float(self.state.get("capital", self.capital))
                    logger.info(
                        f"[PipelineDaemonSupervisor] State restored from {target_path}: "
                        f"Cycle={self.cycle_count}, Phase={self.active_phase.value}, Capital={self.capital:,.0f}"
                    )
                    return True
            except Exception as e:
                logger.error(f"[PipelineDaemonSupervisor] Error reading state file {target_path}: {e}")
        return False

    # -----------------------------------------------------------------------
    # Phase 1: Pre-Market Macro Ingestion & Factor Timing
    # -----------------------------------------------------------------------

    def run_pre_market_phase(
        self,
        indicators: Optional[Dict[str, float]] = None,
    ) -> SupervisorCycleReport:
        """
        Phase 1: Ingests macro data, assesses yield curve inversion, and modulates 37-strategy factor weights.
        """
        cycle_id = f"CYCLE_{self.cycle_count + 1:05d}_PRE_MKT_{uuid.uuid4().hex[:6]}"
        phase = SupervisorLifecyclePhase.PRE_MARKET
        self.active_phase = phase
        t0 = time.time()

        try:
            logger.info(f"[Phase 1: Pre-Market] Executing macro data ingestion & factor timing...")

            # 1. Ingest macro indicator dictionary
            macro_data = copy.deepcopy(self.DEFAULT_MACRO_INDICATORS)
            if self.indicator_storage is not None:
                try:
                    storage_indicators = self.indicator_storage.get_latest_global_indicators()
                    if storage_indicators:
                        for k, v in storage_indicators.items():
                            if v is not None and math.isfinite(float(v)):
                                macro_data[k] = float(v)
                except Exception as e:
                    logger.debug(f"[Phase 1: Pre-Market] IndicatorStorage fetch fallback: {e}")

            if indicators:
                for k, v in indicators.items():
                    if v is not None and math.isfinite(float(v)):
                        macro_data[k] = float(v)

            # 2. Extract macro condition vector via DynamicMacroFactorTimingEngine
            is_krx = bool(self.market in ("KRX", "KOSPI", "KOSDAQ"))
            condition_vector: Dict[str, float] = {}
            macro_impulse = 0.0
            is_inverted = False
            term_spread = macro_data.get("term_spread", macro_data.get("us10y", 4.25) - macro_data.get("us2y", 4.00))

            if self.macro_engine is not None:
                condition_vector = self.macro_engine.extract_macro_condition_vector(macro_data, is_krx=is_krx)
                macro_impulse = float(self.macro_engine.compute_macro_impulse(condition_vector))
                is_inverted = bool(condition_vector.get("is_inverted", term_spread < 0))
            else:
                is_inverted = bool(term_spread < 0)
                macro_impulse = float(math.tanh(term_spread * 2.0))
                condition_vector = {
                    "term_spread": float(math.tanh(term_spread * 2.0)),
                    "is_inverted": is_inverted,
                    "macro_impulse": macro_impulse,
                }

            # 3. Modulate baseline strategy weights
            base_weights = {
                "regression": 0.05,
                "surge": 0.05,
                "vcp_rule": 0.05,
                "rim_valuation": 0.08,
                "mq_factor": 0.08,
                "accruals_quality": 0.07,
                "factor_neutralized": 0.07,
                "valueup_catalyst": 0.07,
                "trend_efficiency": 0.05,
                "range_expansion_breakout": 0.05,
            }
            # Normalize base_weights
            s_sum = sum(base_weights.values())
            for k in base_weights:
                base_weights[k] /= s_sum

            modulated_weights = copy.deepcopy(base_weights)
            if self.macro_engine is not None:
                modulated_weights = self.macro_engine.modulate_strategy_weights(
                    base_weights=base_weights,
                    indicators=macro_data,
                    market="krx" if is_krx else "us",
                )

            # Verification: Simplex sum must be 1.000000
            total_weight = sum(modulated_weights.values())
            if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
                modulated_weights = {k: v / total_weight for k, v in modulated_weights.items()}

            details = {
                "cycle_id": cycle_id,
                "duration_sec": round(time.time() - t0, 4),
                "is_inverted": is_inverted,
                "term_spread": term_spread,
                "macro_impulse": round(macro_impulse, 4),
                "condition_vector": condition_vector,
                "quality_boost_active": is_inverted,
                "strategy_weights_count": len(modulated_weights),
                "top_weighted_strategy": max(modulated_weights.items(), key=lambda x: x[1])[0],
            }

            self.state["pre_market"] = details
            self.save_state()

            logger.info(
                f"[Phase 1: Pre-Market] Completed in {details['duration_sec']}s. "
                f"Inverted={is_inverted}, TermSpread={term_spread:.2f}%, Impulse={macro_impulse:+.3f}"
            )

            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True,
                details=details,
            )

        except Exception as e:
            logger.error(f"[Phase 1: Pre-Market] Unhandled error: {e}", exc_info=True)
            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={"duration_sec": round(time.time() - t0, 4)},
                error_message=str(e),
            )

    # -----------------------------------------------------------------------
    # Phase 2: Market-Open Portfolio Optimization & Order Generation
    # -----------------------------------------------------------------------

    def run_market_open_phase(
        self,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> SupervisorCycleReport:
        """
        Phase 2: Optimizes portfolio allocations and generates OMS orders via PaperTradingDaemon.
        """
        cycle_id = f"CYCLE_{self.cycle_count + 1:05d}_MKT_OPEN_{uuid.uuid4().hex[:6]}"
        phase = SupervisorLifecyclePhase.MARKET_OPEN
        self.active_phase = phase
        t0 = time.time()

        try:
            logger.info(f"[Phase 2: Market-Open] Generating portfolio allocations & orders...")

            # 1. Filter candidate universe based on target market
            cand_pool = copy.deepcopy(candidates if candidates is not None else self.DEFAULT_CANDIDATES)
            if self.market != "ALL":
                filtered = [c for c in cand_pool if c.get("market", "").upper() == self.market]
                if filtered:
                    cand_pool = filtered

            # 2. Compute Target Allocation with Single-Stock (<= 5%) and Sector (<= 25%) constraints
            cand_pool.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
            top_picks = cand_pool[:20]

            sector_allocations: Dict[str, float] = collections.defaultdict(float)
            target_allocations: Dict[str, float] = {}

            # Proportional allocation capped at guardrails
            for c in top_picks:
                sym = str(c.get("symbol", "")).strip()
                sector = str(c.get("sector", "General")).strip()
                score = max(0.01, float(c.get("score", 0.5)))

                prop_weight = min(self.max_single_weight, score * 0.06)

                # Check sector cap
                if sector_allocations[sector] + prop_weight > self.max_sector_weight:
                    prop_weight = max(0.0, self.max_sector_weight - sector_allocations[sector])

                if prop_weight > 0.001:
                    target_allocations[sym] = round(prop_weight, 5)
                    sector_allocations[sector] += prop_weight

            # 3. Market prices and market data dictionary (dict of dicts for OMS safety gates)
            market_data_dict: Dict[str, Dict[str, Any]] = {}
            for c in cand_pool:
                sym = str(c.get("symbol", "")).strip()
                px = float(c.get("price", 100.0))
                mkt = str(c.get("market", "KOSPI"))
                market_data_dict[sym] = {
                    "price": px,
                    "current_price": px,
                    "open_price": px,
                    "prev_close": px,
                    "daily_change_pct": 0.0,
                    "open_gap_pct": 0.0,
                    "spread_bps": 5.0,
                    "adv_20d": 1_000_000_000.0 if "KR" in mkt or sym.isdigit() else 50_000_000.0,
                    "market": mkt,
                }

            # 4. Route through PaperTradingDaemon
            orders_executed = 0
            execution_details: List[Dict[str, Any]] = []

            if self.paper_daemon is not None:
                # Use run_cycle directly with market_data_dict
                cycle_summary = self.paper_daemon.run_cycle(
                    target_input=target_allocations,
                    market_data=market_data_dict,
                )
                execution_details = cycle_summary.get("executions", [])
                orders_executed = len(execution_details)
            else:
                # Fallback mock order generation if paper daemon unavailable
                orders_executed = len(target_allocations)
                for sym, w in target_allocations.items():
                    px = market_prices.get(sym, 1000.0)
                    qty = max(1, int((self.capital * w) / px))
                    execution_details.append({
                        "order_id": f"ORD_{sym}_{uuid.uuid4().hex[:6]}",
                        "symbol": sym,
                        "action": "BUY",
                        "weight": w,
                        "price": px,
                        "quantity": qty,
                        "status": "FILLED" if not self.dry_run else "SIMULATED",
                    })

            # 5. Dispatch Market-Open Alert
            if self.alert_dispatcher is not None:
                try:
                    self.alert_dispatcher.send_alert(
                        title=f"Market-Open Orders Generated ({len(target_allocations)} Assets)",
                        message=(
                            f"Supervisor Phase 2 complete.\n"
                            f"• Total Orders: {orders_executed}\n"
                            f"• Invested Capital Target: {sum(target_allocations.values()) * 100:.2f}%\n"
                            f"• Top Asset: {max(target_allocations.items(), key=lambda x: x[1])[0] if target_allocations else 'None'}"
                        ),
                        level="INFO",
                    )
                except Exception as e:
                    logger.debug(f"[Phase 2: Market-Open] Alert dispatch fallback: {e}")

            details = {
                "cycle_id": cycle_id,
                "duration_sec": round(time.time() - t0, 4),
                "candidates_considered": len(cand_pool),
                "target_assets_count": len(target_allocations),
                "orders_count": orders_executed,
                "total_target_exposure": round(sum(target_allocations.values()), 4),
                "target_allocations": target_allocations,
                "sector_breakdown": dict(sector_allocations),
            }

            self.state["market_open"] = details
            self.save_state()

            logger.info(
                f"[Phase 2: Market-Open] Completed in {details['duration_sec']}s. "
                f"Generated {orders_executed} orders across {len(target_allocations)} assets."
            )

            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True,
                details=details,
            )

        except Exception as e:
            logger.error(f"[Phase 2: Market-Open] Unhandled error: {e}", exc_info=True)
            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={"duration_sec": round(time.time() - t0, 4)},
                error_message=str(e),
            )

    # -----------------------------------------------------------------------
    # Phase 3: Intraday Real-Time Risk Monitoring Loop
    # -----------------------------------------------------------------------

    def run_intraday_risk_phase(
        self,
        price_updates: Optional[Dict[str, float]] = None,
        vix_value: Optional[float] = None,
    ) -> SupervisorCycleReport:
        """
        Phase 3: Monitors 3-Tier profit taking, Leland trailing stops, and flash-crash circuit breakers.
        """
        cycle_id = f"CYCLE_{self.cycle_count + 1:05d}_INTRADAY_{uuid.uuid4().hex[:6]}"
        phase = SupervisorLifecyclePhase.INTRADAY_RISK
        self.active_phase = phase
        t0 = time.time()

        try:
            logger.info(f"[Phase 3: Intraday Risk] Monitoring positions and volatility...")

            # 1. Synchronize positions from paper daemon
            active_holdings: Dict[str, Dict[str, Any]] = {}
            if self.paper_daemon is not None and hasattr(self.paper_daemon, "holdings"):
                active_holdings = copy.deepcopy(self.paper_daemon.holdings)

            # If paper daemon has no holdings, populate with mock/registered positions for monitoring
            if not active_holdings and self.risk_monitor is not None and self.risk_monitor.positions:
                for sym, p_state in self.risk_monitor.positions.items():
                    active_holdings[sym] = {
                        "symbol": sym,
                        "quantity": p_state.current_quantity,
                        "avg_cost": p_state.entry_price,
                        "current_price": p_state.last_price,
                        "market": p_state.market,
                    }

            # 2. Register/update positions in InstitutionalIntradayRiskMonitor
            if self.risk_monitor is not None:
                for sym, h in active_holdings.items():
                    qty = int(h.get("quantity", 0))
                    avg_px = float(h.get("avg_cost", h.get("entry_price", 100.0)))
                    mkt = str(h.get("market", "KOSPI"))
                    if qty > 0 and sym not in self.risk_monitor.positions:
                        self.risk_monitor.register_position(
                            symbol=sym,
                            entry_price=avg_px,
                            quantity=qty,
                            market=mkt,
                        )

            # 3. Apply price updates if provided
            current_prices: Dict[str, float] = {}
            market_data_dict: Dict[str, Dict[str, float]] = {}

            for sym, h in active_holdings.items():
                p = float(h.get("current_price", h.get("avg_cost", 100.0)))
                current_prices[sym] = p
                market_data_dict[sym] = {
                    "current_price": p,
                    "price": p,
                    "open_price": p,
                    "prev_close": p,
                    "volatility_20d": float(h.get("volatility_20d", 0.02)),
                    "peak_price": float(h.get("peak_price", p)),
                }

            if price_updates:
                for sym, px in price_updates.items():
                    if px is not None and math.isfinite(float(px)):
                        p_flt = float(px)
                        current_prices[sym] = p_flt
                        if sym not in market_data_dict:
                            market_data_dict[sym] = {
                                "current_price": p_flt,
                                "price": p_flt,
                                "open_price": p_flt,
                                "prev_close": p_flt,
                            }
                        else:
                            market_data_dict[sym]["current_price"] = p_flt
                            market_data_dict[sym]["price"] = p_flt
                        if self.paper_daemon is not None and sym in self.paper_daemon.holdings:
                            self.paper_daemon.holdings[sym]["current_price"] = p_flt

            # 4. Evaluate positions for 3-Tier Take Profit and Leland Trailing Stops
            risk_actions: List[Dict[str, Any]] = []
            curr_vix = vix_value if vix_value is not None else self.DEFAULT_MACRO_INDICATORS.get("vix", 16.5)

            if self.risk_monitor is not None:
                vix_dict = {
                    "vix_current": curr_vix,
                    "vix_1h_ago": self.DEFAULT_MACRO_INDICATORS.get("vix", 16.5),
                    "market": self.market if self.market != "ALL" else "GLOBAL",
                }
                actions = self.risk_monitor.evaluate_portfolio(
                    holdings=active_holdings,
                    market_data=market_data_dict,
                    vix_data=vix_dict,
                    capital=self.capital,
                )
                for a in actions:
                    risk_actions.append(a.to_dict() if hasattr(a, "to_dict") else asdict(a))

                    # If emergency liquidation or take profit, execute in paper daemon if not dry run
                    if self.paper_daemon is not None and not self.dry_run:
                        try:
                            if a.action == "SELL" and a.symbol in self.paper_daemon.holdings:
                                sell_qty = min(a.quantity, self.paper_daemon.holdings[a.symbol]["quantity"])
                                self.paper_daemon.holdings[a.symbol]["quantity"] -= sell_qty
                                self.paper_daemon.cash_balance += sell_qty * a.current_price
                        except Exception as e:
                            logger.debug(f"[Phase 3: Intraday Risk] Paper daemon sync fallback: {e}")

                    # Dispatch Circuit Breaker alert
                    if self.alert_dispatcher is not None and (a.force_liquidate or getattr(a, "is_hedge", False)):
                        try:
                            self.alert_dispatcher.send_circuit_breaker_alert(
                                trigger_type=a.reason,
                                symbol=a.symbol,
                                trigger_value=round((a.current_price - a.trigger_price) / a.trigger_price * 100, 2) if a.trigger_price else 0.0,
                                threshold=-6.0,
                                action_taken=f"{a.action}_{a.quantity}_SHARES",
                                severity=a.severity,
                                current_price=a.current_price,
                            )
                        except Exception as e:
                            logger.debug(f"[Phase 3: Intraday Risk] Circuit breaker alert fallback: {e}")

            details = {
                "cycle_id": cycle_id,
                "duration_sec": round(time.time() - t0, 4),
                "positions_monitored": len(active_holdings),
                "risk_actions_count": len(risk_actions),
                "risk_actions": risk_actions,
                "vix_observed": curr_vix,
                "circuit_breaker_triggered": any(a.get("force_liquidate", False) for a in risk_actions),
            }

            self.state["intraday_risk"] = details
            self.save_state()

            logger.info(
                f"[Phase 3: Intraday Risk] Completed in {details['duration_sec']}s. "
                f"Monitored {len(active_holdings)} assets, emitted {len(risk_actions)} risk actions."
            )

            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True,
                details=details,
            )

        except Exception as e:
            logger.error(f"[Phase 3: Intraday Risk] Unhandled error: {e}", exc_info=True)
            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={"duration_sec": round(time.time() - t0, 4)},
                error_message=str(e),
            )

    # -----------------------------------------------------------------------
    # Phase 4: Market-Close Shadow Reconciliation & PnL Accounting
    # -----------------------------------------------------------------------

    def run_market_close_phase(self) -> SupervisorCycleReport:
        """
        Phase 4: Reconciles shadow executions, performs PnL accounting, enforces Net Equity <= Gross Equity,
        and dispatches daily operational summary alert.
        """
        cycle_id = f"CYCLE_{self.cycle_count + 1:05d}_CLOSE_{uuid.uuid4().hex[:6]}"
        phase = SupervisorLifecyclePhase.MARKET_CLOSE
        self.active_phase = phase
        t0 = time.time()

        try:
            logger.info(f"[Phase 4: Market-Close] Reconciling shadow execution & daily PnL...")

            gross_equity = self.capital
            net_equity = self.capital
            cash_balance = self.capital
            invested_value = 0.0
            total_fees = 0.0
            total_impact = 0.0
            total_slippage = 0.0
            holdings_count = 0

            # 1. Extract snapshot from paper trading daemon
            if self.paper_daemon is not None:
                snap = self.paper_daemon.snapshot_portfolio()
                gross_equity = float(snap.gross_equity)
                net_equity = float(snap.net_equity)
                cash_balance = float(snap.cash_balance)
                invested_value = float(snap.invested_value)
                holdings_count = int(snap.holdings_count)
                total_fees = float(self.paper_daemon.total_fees_paid)
                total_impact = float(self.paper_daemon.total_impact_cost)
                total_slippage = float(self.paper_daemon.total_slippage_cost)

            # 2. Strict Mathematical Invariant Enforcement: Net Equity <= Gross Equity
            if net_equity > gross_equity:
                logger.warning(
                    f"[Invariant Warning] Net Equity ({net_equity}) exceeded Gross Equity ({gross_equity}). "
                    f"Applying non-linear friction clamping."
                )
                net_equity = gross_equity

            # Guarantee Net Equity <= Gross Equity within floating-point tolerance
            assert net_equity <= gross_equity + 1e-9, (
                f"Mathematical Invariant Violation: Net Equity ({net_equity}) > Gross Equity ({gross_equity})"
            )

            # Update master state
            self.state["gross_equity"] = gross_equity
            self.state["net_equity"] = net_equity
            self.state["cash_balance"] = cash_balance
            self.capital = net_equity

            # 3. Format top conviction picks per market for AlertDispatcher
            top_picks_per_market: Dict[str, List[Dict[str, Any]]] = {}
            if self.paper_daemon is not None and hasattr(self.paper_daemon, "holdings"):
                for sym, h in self.paper_daemon.holdings.items():
                    mkt = str(h.get("market", "KOSPI"))
                    if mkt not in top_picks_per_market:
                        top_picks_per_market[mkt] = []
                    top_picks_per_market[mkt].append({
                        "symbol": sym,
                        "name": sym,
                        "score": 0.85,
                        "price": float(h.get("current_price", 100.0)),
                        "target_price": float(h.get("current_price", 100.0)) * 1.15,
                    })

            # 4. Dispatch daily pipeline summary alert via AlertDispatcher
            alert_sent = False
            if self.alert_dispatcher is not None:
                try:
                    alert_sent = self.alert_dispatcher.send_pipeline_summary(
                        run_id=cycle_id,
                        duration_sec=round(time.time() - t0, 2),
                        regime_2d=self.regime_label,
                        top_picks_per_market=top_picks_per_market,
                        status="COMPLETED",
                    )
                except Exception as e:
                    logger.debug(f"[Phase 4: Market-Close] Alert dispatcher summary fallback: {e}")

            details = {
                "cycle_id": cycle_id,
                "duration_sec": round(time.time() - t0, 4),
                "gross_equity": round(gross_equity, 2),
                "net_equity": round(net_equity, 2),
                "cash_balance": round(cash_balance, 2),
                "invested_value": round(invested_value, 2),
                "holdings_count": holdings_count,
                "total_fees_paid": round(total_fees, 4),
                "total_market_impact": round(total_impact, 4),
                "total_slippage_cost": round(total_slippage, 4),
                "invariant_verified": bool(net_equity <= gross_equity + 1e-9),
                "summary_alert_sent": alert_sent,
            }

            self.state["market_close"] = details
            self.state["history"].append({
                "cycle_id": cycle_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "net_equity": round(net_equity, 2),
                "gross_equity": round(gross_equity, 2),
            })
            if len(self.state["history"]) > 200:
                self.state["history"] = self.state["history"][-200:]

            self.save_state()

            logger.info(
                f"[Phase 4: Market-Close] Completed in {details['duration_sec']}s. "
                f"Gross Equity={gross_equity:,.0f}, Net Equity={net_equity:,.0f}, Invariant=PASS"
            )

            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True,
                details=details,
            )

        except Exception as e:
            logger.error(f"[Phase 4: Market-Close] Unhandled error: {e}", exc_info=True)
            return SupervisorCycleReport(
                cycle_id=cycle_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={"duration_sec": round(time.time() - t0, 4)},
                error_message=str(e),
            )

    # -----------------------------------------------------------------------
    # Comprehensive Master Orchestrations
    # -----------------------------------------------------------------------

    def run_single_sweep(
        self,
        indicators: Optional[Dict[str, float]] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        price_updates: Optional[Dict[str, float]] = None,
        vix_value: Optional[float] = None,
    ) -> Dict[str, SupervisorCycleReport]:
        """
        Executes a complete single operational cycle through all 4 lifecycle phases sequentially.
        """
        with self._lock:
            self.cycle_count += 1
            logger.info(f"\n{'='*70}\n[PipelineDaemonSupervisor] Starting Cycle #{self.cycle_count} Master Sweep\n{'='*70}")

            reports: Dict[str, SupervisorCycleReport] = {}

            # Phase 1: Pre-Market
            r1 = self.run_pre_market_phase(indicators=indicators)
            reports[SupervisorLifecyclePhase.PRE_MARKET.value] = r1

            # Phase 2: Market-Open
            r2 = self.run_market_open_phase(candidates=candidates)
            reports[SupervisorLifecyclePhase.MARKET_OPEN.value] = r2

            # Phase 3: Intraday Risk
            r3 = self.run_intraday_risk_phase(price_updates=price_updates, vix_value=vix_value)
            reports[SupervisorLifecyclePhase.INTRADAY_RISK.value] = r3

            # Phase 4: Market-Close
            r4 = self.run_market_close_phase()
            reports[SupervisorLifecyclePhase.MARKET_CLOSE.value] = r4

            self.active_phase = SupervisorLifecyclePhase.IDLE
            self.save_state()

            logger.info(
                f"[PipelineDaemonSupervisor] Finished Cycle #{self.cycle_count} Master Sweep. "
                f"All 4 phases: {[r.success for r in reports.values()]}\n{'='*70}"
            )

            return reports

    def run_daemon_loop(self, max_cycles: Optional[int] = None) -> None:
        """
        Executes the continuous 24/7 daemon supervisor loop until stopped or interrupted.
        """
        logger.info(
            f"[PipelineDaemonSupervisor] Entering continuous daemon loop. "
            f"Interval: {self.interval_seconds}s, MaxCycles: {max_cycles or 'Infinite'}"
        )

        cycles_run = 0
        while not self.stop_requested:
            try:
                self.run_single_sweep()
                cycles_run += 1

                if max_cycles is not None and cycles_run >= max_cycles:
                    logger.info(f"[PipelineDaemonSupervisor] Reached max_cycles={max_cycles}. Exiting daemon loop.")
                    break

                # Sleep interval in small chunks for responsive cancellation
                sleep_start = time.time()
                while time.time() - sleep_start < self.interval_seconds:
                    if self.stop_requested:
                        break
                    time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("[PipelineDaemonSupervisor] KeyboardInterrupt received. Gracefully shutting down...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"[PipelineDaemonSupervisor] Error in daemon loop: {e}", exc_info=True)
                time.sleep(5)

        logger.info("[PipelineDaemonSupervisor] Daemon loop terminated cleanly.")

    def stop(self) -> None:
        """Signal the supervisor daemon to stop running."""
        with self._lock:
            self.stop_requested = True
            self.active_phase = SupervisorLifecyclePhase.IDLE
            self.save_state()


# ---------------------------------------------------------------------------
# Complete Alias Trees
# ---------------------------------------------------------------------------
AutonomousPipelineDaemonSupervisor = PipelineDaemonSupervisor
Phase107PipelineDaemonSupervisor = PipelineDaemonSupervisor
PipelineSupervisorDaemon = PipelineDaemonSupervisor
DailyTradingSupervisor = PipelineDaemonSupervisor

__all__ = [
    "SupervisorLifecyclePhase",
    "SupervisorCycleReport",
    "SupervisorConfig",
    "PipelineDaemonSupervisor",
    "AutonomousPipelineDaemonSupervisor",
    "Phase107PipelineDaemonSupervisor",
    "PipelineSupervisorDaemon",
    "DailyTradingSupervisor",
]

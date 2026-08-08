"""TradeExecutor - 장중 실시간 매매 실행기.

기본은 DRY_RUN(모의 로그 + OMS 기록만). 키움 커넥터가 실연결(비시뮬레이션) 상태이고
REALTIME_TRADE_ENABLED=true 이면 실제 주문을 접수한다.

모든 실행은 OMS(OrderManagementSystem)에 기록되어 trade_logs / 오더 이력으로 추적된다.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    symbol: str
    action: str            # BUY | SELL | NONE
    quantity: int
    price: float
    executed: bool
    mode: str              # dry_run | live
    order_id: str = ""
    message: str = ""


class TradeExecutor:
    def __init__(
        self,
        kiwoom=None,
        oms=None,
        dry_run: bool = True,
        max_order_value_krw: float = 50_000_000.0,  # 5천만 원 상한
        lot_size_krx: int = 1,                      # KRX 호가 단위 수량 (1주)
        lot_size_us: int = 1,                       # US 호가 단위 수량 (1주)
    ):
        self.kiwoom = kiwoom
        self.oms = oms
        self.dry_run = dry_run
        self.max_order_value_krw = max_order_value_krw
        self.lot_size_krx = lot_size_krx
        self.lot_size_us = lot_size_us
        self._executed_today: Dict[str, str] = {}   # symbol -> action (중복 실행 방지)
        self._last_execution_date: str = datetime.now().strftime('%Y-%m-%d')

    @property
    def can_trade_live(self) -> bool:
        env_enabled = os.getenv("REALTIME_TRADE_ENABLED", "false").lower() == "true"
        return (env_enabled and not self.dry_run and self.kiwoom is not None
                and getattr(self.kiwoom, "is_connected", False)
                and not getattr(self.kiwoom, "simulation_mode", True))

    def _round_lot(self, qty: int, market: str = "KOSPI") -> int:
        if qty <= 0:
            return 0
        lot = self.lot_size_krx if market in ("KOSPI", "KOSDAQ", "KONEX") else self.lot_size_us
        return (qty // lot) * lot

    def _check_and_reset_daily_tracker(self) -> None:
        today_str = datetime.now().strftime('%Y-%m-%d')
        if self._last_execution_date != today_str:
            self._executed_today.clear()
            self._last_execution_date = today_str

    def execute(
        self,
        symbol: str,
        market: str,
        action: str,          # BUY | SELL
        quantity: int,
        price: float,
        reason: str = "",
        risk_manager: Any = None,
        usdkrw_rate: float = 1380.0,
    ) -> ExecResult:
        self._check_and_reset_daily_tracker()

        if price <= 0 or quantity <= 0:
            return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                              executed=False, mode="dry_run" if self.dry_run else "live",
                              message="invalid qty/price")

        # RiskManager Pre-Trade Gate check
        if risk_manager is not None:
            if getattr(risk_manager, 'emergency_stop', False):
                return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                                  executed=False, mode="dry_run" if self.dry_run else "live",
                                  message="blocked by emergency stop")
            if action == "BUY" and hasattr(risk_manager, 'get_crisis_new_buy_blocked') and risk_manager.get_crisis_new_buy_blocked():
                return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                                  executed=False, mode="dry_run" if self.dry_run else "live",
                                  message="new buys blocked by crisis detector")

        if market in ("KOSPI", "KOSDAQ", "KONEX"):
            quantity = self._round_lot(quantity, market=market)
            if quantity <= 0:
                return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                                  executed=False, mode="dry_run" if self.dry_run else "live",
                                  message="below lot size")
            fx_rate = 1.0
        else:
            quantity = self._round_lot(quantity, market=market)
            fx_rate = usdkrw_rate if usdkrw_rate > 0 else 1380.0

        order_value_krw = quantity * price * fx_rate
        if order_value_krw > self.max_order_value_krw:
            max_qty_raw = int(self.max_order_value_krw / (price * fx_rate))
            lot = self.lot_size_krx if market in ("KOSPI", "KOSDAQ", "KONEX") else self.lot_size_us
            quantity = (max_qty_raw // lot) * lot
            order_value_krw = quantity * price * fx_rate
            if quantity <= 0:
                return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                                  executed=False, mode="dry_run" if self.dry_run else "live",
                                  message="over max order value")

        # 중복 실행 방지: 동일 종목·동일 방향은 하루 1회
        if self._executed_today.get(symbol) == action:
            return ExecResult(symbol=symbol, action="NONE", quantity=0, price=price,
                              executed=False, mode="dry_run" if self.dry_run else "live",
                              message="duplicate action for symbol today")

        order_id = ""
        is_krx = market in ("KOSPI", "KOSDAQ", "KONEX")
        live = self.can_trade_live and is_krx
        mode = "live" if live else "dry_run"

        if live:
            try:
                kr_order_type = "매수" if action == "BUY" else "매도"
                order_id = self.kiwoom.place_order(symbol, quantity, price, kr_order_type)
                if not order_id:
                    return ExecResult(symbol=symbol, action=action, quantity=quantity, price=price,
                                      executed=False, mode=mode, message="kiwoom order rejected")
                logger.info(f"[EXEC] LIVE {action} {quantity} {symbol} @ {price} (order={order_id})")
            except Exception as e:
                return ExecResult(symbol=symbol, action=action, quantity=quantity, price=price,
                                  executed=False, mode=mode, message=f"kiwoom error: {e}")
        else:
            if not is_krx and self.can_trade_live:
                logger.warning(f"[EXEC] US market ({market}) live API ordering not yet supported. Simulating order.")
            logger.info(f"[EXEC] DRY-RUN {action} {quantity} {symbol} @ {price} (reason={reason})")

        self._executed_today[symbol] = action

        # OMS 기록 (항상)
        if self.oms is not None:
            try:
                from src.core.order_management import Order, OrderStatus, OrderType
                order = Order(
                    symbol=symbol,
                    order_type=OrderType.BUY if action == "BUY" else OrderType.SELL,
                    quantity=quantity,
                    price=price,
                    signal_name=f"realtime_{reason[:40]}" if reason else "realtime",
                    broker_order_id=order_id or f"DRY_{datetime.now().timestamp()}",
                )
                order.status = OrderStatus.EXECUTED if not live else OrderStatus.SUBMITTED
                order.filled_quantity = quantity if not live else 0
                order.executed_at = datetime.now() if not live else None
                self.oms.orders[order.order_id] = order
            except Exception as e:
                logger.warning(f"[EXEC] OMS record failed: {e}")

        return ExecResult(symbol=symbol, action=action, quantity=quantity, price=price,
                          executed=True, mode=mode, order_id=order_id,
                          message=f"{mode.upper()} {action} {quantity} {symbol} @ {price}")

"""
src/broker/unified_adapter.py — Unified Broker Adapter & Protocol Standardization
Milestone 1: Broker Architecture DIP & Interface Standardization
Phase 112 (Release R128 / v119 Production Master, Feature F530)

Unifies heterogeneous broker interfaces across the system:
  - BrokerProtocol: runtime-checkable typing Protocol (Daishin, Hanwha, Kiwoom, NH, Mirae, IBKR, FIX 4.4).
  - BrokerBase: ABC for order submission and account balance (RealBroker, KoreaInvestmentBroker, KiwoomBroker).
  - BaseBrokerConnector: institutional OpenAPI connector (KISBrokerConnector, LSBrokerConnector).
  - Custom / simulated brokers.

Guarantees 100% compliance with BrokerProtocol, provides bi-directional order translation
(place_order <-> submit_order), standardized balance/position formats, and connected state handling.
"""

from __future__ import annotations

import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union

from .base_connector import (
    AccountBalanceSnapshot,
    BaseBrokerConnector,
    BrokerResponse,
    ConnectedState,
    ExecutionNotice,
    MarketTradeTick,
    OrderbookDepth,
    PositionSnapshot,
)
from .protocol import BrokerProtocol

logger = logging.getLogger(__name__)

VERSION = 119
RELEASE = "R128"
FEATURE = "F530"
MODULE_NAME = "unified_adapter"


class UnifiedBrokerAdapter:
    """
    Polymorphic adapter establishing a uniform interface across:
      - BrokerProtocol (Protocol)
      - BrokerBase (ABC)
      - BaseBrokerConnector (ABC)
      - Any generic broker with duck-typing support.

    Conforms to runtime BrokerProtocol checkability (`isinstance(adapter, BrokerProtocol)` is True).
    """

    def __init__(
        self,
        target_broker: Any,
        broker_name: Optional[str] = None,
        account_number: Optional[str] = None,
        simulation_mode: Optional[bool] = None,
    ):
        if target_broker is None:
            raise ValueError("target_broker cannot be None")

        self._target = target_broker
        self._broker_name = str(broker_name or getattr(target_broker, "__class__", type(target_broker)).__name__)
        self._account_number: Optional[str] = (
            str(account_number)
            if account_number is not None
            else getattr(target_broker, "account_number", getattr(target_broker, "_account_number", None))
        )
        self._simulation_mode: bool = (
            bool(simulation_mode)
            if simulation_mode is not None
            else bool(getattr(target_broker, "simulation_mode", False))
        )
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{self._broker_name}]")

    @property
    def target(self) -> Any:
        """Return the underlying wrapped broker instance."""
        return self._target

    @property
    def broker_name(self) -> str:
        """Return human-readable identifier for this broker adapter."""
        return self._broker_name

    @property
    def is_connected(self) -> ConnectedState:
        """
        Unified connection state wrapper supporting both boolean evaluation
        (`if adapter.is_connected:`) and method invocation (`if adapter.is_connected():`).
        """
        raw_state = getattr(self._target, "is_connected", getattr(self._target, "connected", False))
        if callable(raw_state):
            try:
                state_bool = bool(raw_state())
            except Exception:
                state_bool = False
        elif isinstance(raw_state, ConnectedState):
            state_bool = bool(raw_state)
        else:
            state_bool = bool(raw_state)
        return ConnectedState(state_bool)

    @property
    def account_number(self) -> Optional[str]:
        """Query account number."""
        acc = getattr(self._target, "account_number", getattr(self._target, "_account_number", None))
        return str(acc) if acc is not None else self._account_number

    @account_number.setter
    def account_number(self, value: Optional[str]) -> None:
        """Set account number."""
        self._account_number = str(value) if value is not None else None
        if hasattr(self._target, "account_number"):
            try:
                self._target.account_number = self._account_number
            except (AttributeError, TypeError):
                pass
        if hasattr(self._target, "_account_number"):
            self._target._account_number = self._account_number

    @property
    def simulation_mode(self) -> bool:
        """Query simulation mode flag."""
        return bool(getattr(self._target, "simulation_mode", self._simulation_mode))

    @simulation_mode.setter
    def simulation_mode(self, value: bool) -> None:
        """Set simulation mode flag."""
        self._simulation_mode = bool(value)
        if hasattr(self._target, "simulation_mode"):
            try:
                self._target.simulation_mode = self._simulation_mode
            except (AttributeError, TypeError):
                pass

    def connect(self, account_number: Optional[str] = None) -> bool:
        """
        Connect to broker. Handles variable parameter signatures across
        BrokerProtocol, BrokerBase, and BaseBrokerConnector.
        """
        target_acc = account_number or self.account_number or ""
        if account_number:
            self.account_number = account_number

        if not hasattr(self._target, "connect") or not callable(self._target.connect):
            return False

        try:
            sig = inspect.signature(self._target.connect)
            params = [p for p in sig.parameters.values() if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            if len(params) == 0:
                return bool(self._target.connect())
            elif len(params) == 1 and params[0].default is inspect.Parameter.empty:
                return bool(self._target.connect(target_acc))
            else:
                return bool(self._target.connect(account_number=target_acc))
        except (TypeError, ValueError):
            try:
                return bool(self._target.connect(target_acc))
            except TypeError:
                return bool(self._target.connect())

    def disconnect(self) -> bool:
        """Disconnect session and clean up socket/stream connections."""
        if hasattr(self._target, "disconnect") and callable(self._target.disconnect):
            try:
                return bool(self._target.disconnect())
            except Exception as e:
                self.logger.warning(f"Error during disconnect on {self._broker_name}: {e}")
                return False
        # If target has a connected attribute, set it to False
        if hasattr(self._target, "connected"):
            self._target.connected = False
        return True

    def place_order(
        self,
        code: Optional[str] = None,
        quantity: int = 0,
        price: float = 0.0,
        order_type: str = "LIMIT",
        symbol: Optional[str] = None,
        qty: Optional[int] = None,
        side: Optional[Union[str, int]] = "BUY",
        **kwargs: Any,
    ) -> Any:
        """
        Unified order submission interface.
        Accepts both (code, quantity, price, order_type) and (symbol, qty, price, side, order_type).
        Delegates to target's place_order or submit_order transparently.
        """
        sym = symbol or code or kwargs.get("ticker", "")
        q = quantity if quantity else (qty if qty is not None else int(kwargs.get("amount", 0)))
        raw_side = str(side).upper() if side is not None else str(kwargs.get("action", "BUY")).upper()
        norm_side = "SELL" if raw_side in ("SELL", "ASK", "2") else "BUY"

        # Determine order_type to pass for BrokerProtocol targets
        target_order_type = order_type
        if target_order_type in ("LIMIT", "MARKET") and norm_side in ("BUY", "SELL"):
            if hasattr(self._target, "buy") and hasattr(self._target, "sell"):
                target_order_type = norm_side

        # Case 1: Target has native place_order
        if hasattr(self._target, "place_order") and callable(self._target.place_order):
            call_kwargs = dict(kwargs)
            if self._simulation_mode and "market_price" not in call_kwargs and float(price) > 0.0:
                call_kwargs["market_price"] = float(price)
            try:
                sig = inspect.signature(self._target.place_order)
                param_names = set(sig.parameters.keys())
                if "symbol" in param_names:
                    return self._target.place_order(
                        symbol=sym,
                        side=norm_side,
                        order_type=order_type,
                        price=price,
                        quantity=q,
                        **call_kwargs,
                    )
                else:
                    return self._target.place_order(str(sym), int(q), float(price), str(target_order_type))
            except TypeError:
                try:
                    return self._target.place_order(str(sym), int(q), float(price), str(target_order_type))
                except TypeError:
                    return self._target.place_order(
                        symbol=sym,
                        side=norm_side,
                        order_type=order_type,
                        price=price,
                        quantity=q,
                        **call_kwargs,
                    )

        # Case 2: Target has submit_order (BrokerBase style)
        if hasattr(self._target, "submit_order") and callable(self._target.submit_order):
            try:
                receipt = self._target.submit_order(sym, float(q), norm_side)
            except TypeError:
                receipt = self._target.submit_order(symbol=sym, qty=float(q), side=norm_side)
            if isinstance(receipt, dict):
                return BrokerResponse(receipt)
            return str(receipt)

        raise NotImplementedError(f"Underlying broker {self._broker_name} implements neither place_order nor submit_order")

    def submit_order(self, symbol: str, qty: float, side: str, **kwargs: Any) -> Dict[str, Any]:
        """
        BrokerBase contract compatibility method.
        Submits an order and guarantees a receipt dictionary with:
        order_id, symbol, qty, side, timestamp, status.
        """
        if hasattr(self._target, "submit_order") and callable(self._target.submit_order):
            try:
                res = self._target.submit_order(symbol, float(qty), side)
            except TypeError:
                res = self._target.submit_order(symbol=symbol, qty=float(qty), side=side)
            if isinstance(res, dict):
                return res
            return {
                "order_id": str(res),
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "status": "SUBMITTED",
                "timestamp": time.time(),
            }

        # Delegate to place_order
        forward_kwargs = dict(kwargs)
        price_val = float(forward_kwargs.pop("price", 0.0))
        order_type_val = str(forward_kwargs.pop("order_type", "MARKET"))
        forward_kwargs.pop("symbol", None)
        forward_kwargs.pop("code", None)
        forward_kwargs.pop("quantity", None)
        forward_kwargs.pop("qty", None)
        forward_kwargs.pop("side", None)
        if self._simulation_mode and "market_price" not in forward_kwargs and price_val > 0.0:
            forward_kwargs["market_price"] = price_val
        result = self.place_order(
            symbol=symbol,
            quantity=int(qty),
            price=price_val,
            order_type=order_type_val,
            side=side,
            **forward_kwargs,
        )

        if isinstance(result, dict):
            res = dict(result)
            res.setdefault("symbol", symbol)
            res.setdefault("qty", qty)
            res.setdefault("side", side)
            res.setdefault("status", res.get("status", "SUBMITTED"))
            res.setdefault("timestamp", time.time())
            return res

        return {
            "order_id": str(result),
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "status": "SUBMITTED",
            "timestamp": time.time(),
        }

    def cancel_order(self, order_id: str, symbol: Optional[str] = None, **kwargs: Any) -> bool:
        """Cancel an open order."""
        if hasattr(self._target, "cancel_order") and callable(self._target.cancel_order):
            try:
                sig = inspect.signature(self._target.cancel_order)
                if "symbol" in sig.parameters and symbol is not None:
                    res = self._target.cancel_order(str(order_id), symbol=symbol, **kwargs)
                else:
                    res = self._target.cancel_order(str(order_id))
            except TypeError:
                res = self._target.cancel_order(str(order_id))

            if isinstance(res, dict):
                return bool(res.get("success", res.get("status") == "CANCELLED"))
            return bool(res)
        return False

    def modify_order(
        self,
        order_id: str,
        symbol: str,
        new_price: float,
        new_quantity: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Modify an existing open order."""
        if hasattr(self._target, "modify_order") and callable(self._target.modify_order):
            return self._target.modify_order(
                order_id=order_id,
                symbol=symbol,
                new_price=new_price,
                new_quantity=new_quantity,
                **kwargs,
            )
        return {"order_id": order_id, "success": False, "error": "MODIFY_NOT_SUPPORTED"}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Query execution and open status for order ID."""
        if hasattr(self._target, "get_order_status") and callable(self._target.get_order_status):
            res = self._target.get_order_status(str(order_id))
            return res if isinstance(res, dict) else {"order_id": order_id, "status": str(res)}
        return {"order_id": order_id, "status": "UNKNOWN"}

    def get_account_info(self) -> Dict[str, Any]:
        """Return standardized account status, balance, and positions."""
        if hasattr(self._target, "get_account_info") and callable(self._target.get_account_info):
            return self._target.get_account_info()

        bal = self.get_balance()
        pos = self.get_positions()
        cash = float(bal.get("cash_balance", bal.get("cash", 0.0)))
        total = float(bal.get("total_asset_value", bal.get("total_value", cash)))
        return {
            "account_number": self.account_number or "",
            "balance": bal,
            "positions": pos,
            "cash_balance": cash,
            "total_asset_value": total,
            "purchasing_power": float(bal.get("purchasing_power", cash)),
        }

    def get_balance(self) -> Dict[str, Any]:
        """Query real-time cash balance and purchasing power."""
        if hasattr(self._target, "get_balance") and callable(self._target.get_balance):
            res = self._target.get_balance()
            if isinstance(res, (int, float)):
                return {
                    "cash_balance": float(res),
                    "purchasing_power": float(res),
                    "total_asset_value": float(res),
                }
            if isinstance(res, dict):
                cash = float(res.get("cash_balance", res.get("cash", 0.0)))
                total = float(res.get("total_asset_value", res.get("total_value", cash)))
                pp = float(res.get("purchasing_power", cash))
                res.setdefault("cash_balance", cash)
                res.setdefault("purchasing_power", pp)
                res.setdefault("total_asset_value", total)
                return res

        if hasattr(self._target, "get_account_info") and callable(self._target.get_account_info):
            info = self._target.get_account_info()
            cash = float(info.get("cash_balance", info.get("balance", info.get("cash", 0.0))))
            total = float(info.get("total_asset_value", info.get("total_value", cash)))
            return {
                "cash_balance": cash,
                "purchasing_power": float(info.get("purchasing_power", cash)),
                "total_asset_value": total,
                "unrealized_pnl": float(info.get("unrealized_pnl", 0.0)),
            }

        return {"cash_balance": 0.0, "purchasing_power": 0.0, "total_asset_value": 0.0}

    def get_positions(self) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Query currently held positions."""
        if hasattr(self._target, "get_positions") and callable(self._target.get_positions):
            return self._target.get_positions()

        if hasattr(self._target, "get_account_info") and callable(self._target.get_account_info):
            info = self._target.get_account_info()
            return info.get("positions", [])

        return []

    def get_stock_quote(self, code: str) -> Dict[str, Any]:
        """Retrieve market quote for symbol."""
        if hasattr(self._target, "get_stock_quote") and callable(self._target.get_stock_quote):
            return self._target.get_stock_quote(str(code))
        return {"symbol": str(code), "price": 0.0, "status": "NOT_SUPPORTED"}

    def get_daily_chart(self, code: str, days: int = 20) -> List[Dict[str, Any]]:
        """Retrieve historical daily price bars."""
        if hasattr(self._target, "get_daily_chart") and callable(self._target.get_daily_chart):
            try:
                return self._target.get_daily_chart(str(code), int(days))
            except TypeError:
                return self._target.get_daily_chart(str(code), count=int(days))
        return []

    def get_broker_info(self) -> Dict[str, Any]:
        """Retrieve broker gateway metadata and diagnostic status."""
        info: Dict[str, Any] = {}
        if hasattr(self._target, "get_broker_info") and callable(self._target.get_broker_info):
            try:
                res = self._target.get_broker_info()
                if isinstance(res, dict):
                    info = dict(res)
            except Exception:
                info = {}

        info.setdefault("broker_name", self._broker_name)
        info.setdefault("is_connected", bool(self.is_connected))
        info.setdefault("account_number", self.account_number)
        info.setdefault("simulation_mode", self.simulation_mode)
        info["adapter"] = "UnifiedBrokerAdapter"
        info["target_class"] = getattr(self._target, "__class__", type(self._target)).__name__
        return info

    # Pass-through for WebSocket and asynchronous streaming capabilities
    async def connect_websocket(self) -> bool:
        """Asynchronously connect WebSocket if supported."""
        if hasattr(self._target, "connect_websocket") and callable(self._target.connect_websocket):
            return await self._target.connect_websocket()
        return False

    async def subscribe_orderbook(self, symbol: str, callback: Callable[[OrderbookDepth], Any]) -> bool:
        """Subscribe to orderbook depth streaming if supported."""
        if hasattr(self._target, "subscribe_orderbook") and callable(self._target.subscribe_orderbook):
            return await self._target.subscribe_orderbook(symbol, callback)
        return False

    async def subscribe_trades(self, symbol: str, callback: Callable[[MarketTradeTick], Any]) -> bool:
        """Subscribe to trade ticks streaming if supported."""
        if hasattr(self._target, "subscribe_trades") and callable(self._target.subscribe_trades):
            return await self._target.subscribe_trades(symbol, callback)
        return False

    async def subscribe_order_events(self, callback: Callable[[ExecutionNotice], Any]) -> bool:
        """Subscribe to private account execution events if supported."""
        if hasattr(self._target, "subscribe_order_events") and callable(self._target.subscribe_order_events):
            return await self._target.subscribe_order_events(callback)
        return False

    def __getattr__(self, name: str) -> Any:
        """Forward any unhandled attribute or method lookup to the wrapped target."""
        return getattr(self._target, name)

    @classmethod
    def wrap(cls, broker: Any, broker_name: Optional[str] = None) -> "UnifiedBrokerAdapter":
        """
        Factory helper: wrap any broker instance in a UnifiedBrokerAdapter.
        If already a UnifiedBrokerAdapter, returns it directly.
        """
        if isinstance(broker, cls):
            return broker
        return cls(broker, broker_name=broker_name)


__all__ = [
    "UnifiedBrokerAdapter",
]

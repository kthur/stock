"""
src/broker/base_connector.py — Abstract Base Broker Connector & Standardized Data Models
Milestone 1: Broker Architecture DIP & Interface Standardization
Phase 112 (Release R128 / v119 Production Master, Feature F530)

Establishes the uniform institutional broker interface contract and shared broker data models:
  - Standardized broker snapshots: OrderbookLevel, OrderbookDepth, MarketTradeTick, ExecutionNotice,
    PositionSnapshot, AccountBalanceSnapshot.
  - ConnectedState supporting dual attribute / method evaluation.
  - Dict-compatible BrokerResponse.
  - TokenBucketRateLimiter for thread-safe and async-safe request throttling.
  - BaseBrokerConnector abstract base class.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import logging
import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

VERSION = 119
RELEASE = "R128"
FEATURE = "F530"
MODULE_NAME = "base_connector"


# ─────────────────────────────────────────────────────────────────────────────
# Standardized Broker Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderbookLevel:
    """Single price-quantity level in the orderbook ladder."""
    price: float
    quantity: int
    order_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrderbookDepth:
    """10-level normalized orderbook depth snapshot."""
    symbol: str
    timestamp: float
    bids: List[OrderbookLevel]      # 10 levels, descending by price
    asks: List[OrderbookLevel]      # 10 levels, ascending by price
    total_bid_qty: int
    total_ask_qty: int
    mid_price: float
    spread: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "bids": [b.to_dict() for b in self.bids],
            "asks": [a.to_dict() for a in self.asks],
            "total_bid_qty": self.total_bid_qty,
            "total_ask_qty": self.total_ask_qty,
            "mid_price": self.mid_price,
            "spread": self.spread,
        }


@dataclass
class MarketTradeTick:
    """Real-time market trade execution print."""
    symbol: str
    timestamp: float
    price: float
    quantity: int
    side: str                      # 'BUY' or 'SELL'
    accumulated_volume: int
    accumulated_amount: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionNotice:
    """Private account order fill or status execution notice."""
    order_id: str
    original_order_id: Optional[str]
    symbol: str
    side: str                      # 'BUY' or 'SELL'
    exec_price: float
    exec_quantity: int
    remaining_quantity: int
    status: str                    # 'SUBMITTED', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED'
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PositionSnapshot:
    """Normalized holding snapshot for a single symbol."""
    symbol: str
    symbol_name: str
    quantity: int
    available_quantity: int
    average_price: float
    current_price: float
    eval_amount: float
    unrealized_pnl: float
    pnl_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccountBalanceSnapshot:
    """Comprehensive cash, equity, and purchasing power snapshot."""
    account_number: str
    cash_balance: float            # 예수금
    purchasing_power: float        # 주문가능금액
    total_asset_value: float       # 총평가금액
    settled_cash: float            # D+2 예수금
    unrealized_pnl: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConnectedState:
    """
    Dual-purpose state wrapper supporting both attribute bool evaluation
    (`if connector.is_connected:`) and method call invocation (`if connector.is_connected():`).
    """
    def __init__(self, value: bool = False):
        self._value = bool(value)

    def set_state(self, value: bool) -> None:
        self._value = bool(value)

    def __bool__(self) -> bool:
        return self._value

    def __call__(self) -> bool:
        return self._value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ConnectedState):
            return self._value == other._value
        return self._value == bool(other)

    def __repr__(self) -> str:
        return str(self._value)


class BrokerResponse(dict):
    """
    Dict-compatible broker response object that also evaluates cleanly in boolean contexts
    and provides attribute access for common keys (order_id, status, success).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, bool):
            return bool(self.get("success", True)) is other
        return super().__eq__(other)


class TokenBucketRateLimiter:
    """
    Thread-safe and async-safe token bucket rate limiter for OpenAPI request throttling.
    """
    def __init__(self, rate: float = 20.0, capacity: float = 20.0):
        self.rate = float(rate)
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            if self.tokens < tokens:
                required_sleep = (tokens - self.tokens) / self.rate
                self.tokens = 0.0
                self.last_update = time.time() + required_sleep
            else:
                self.tokens -= tokens
                required_sleep = 0.0

        if required_sleep > 0:
            time.sleep(required_sleep)

    async def acquire_async(self, tokens: float = 1.0) -> None:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            if self.tokens < tokens:
                required_sleep = (tokens - self.tokens) / self.rate
                self.tokens = 0.0
                self.last_update = time.time() + required_sleep
            else:
                self.tokens -= tokens
                required_sleep = 0.0

        if required_sleep > 0:
            await asyncio.sleep(required_sleep)


# ─────────────────────────────────────────────────────────────────────────────
# Base Broker Connector Contract
# ─────────────────────────────────────────────────────────────────────────────

class BaseBrokerConnector(ABC):
    """
    Abstract base class establishing the institutional broker interface contract.
    Satisfies runtime BrokerProtocol with full backward compatibility.
    """

    def __init__(
        self,
        account_number: Optional[str] = None,
        simulation_mode: bool = False,
        max_order_value: float = 50_000_000.0,
        max_price_deviation_pct: float = 0.03,
    ):
        self._account_number = str(account_number) if account_number is not None else None
        self._connected_state = ConnectedState(False)
        self.simulation_mode = bool(simulation_mode)
        self.max_order_value = float(max_order_value)
        self.max_price_deviation_pct = float(max_price_deviation_pct)
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def account_number(self) -> Optional[str]:
        return self._account_number

    @account_number.setter
    def account_number(self, value: Optional[str]) -> None:
        self._account_number = str(value) if value is not None else None

    @property
    def is_connected(self) -> ConnectedState:
        return self._connected_state

    @abstractmethod
    def connect(self, account_number: Optional[str] = None) -> bool:
        """Establish session connection and authenticate with broker gateway."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Terminate broker session and clean up streaming sockets."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: Optional[str] = None,
        side: Optional[Union[str, int]] = None,
        order_type: str = "LIMIT",
        price: float = 0.0,
        quantity: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit a new cash order with pre-order safety guards."""
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        symbol: str,
        new_price: float,
        new_quantity: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Modify an existing open order's price and/or quantity."""
        pass

    @abstractmethod
    def cancel_order(
        self,
        order_id: str,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Cancel an open order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Query execution and open status for a specific order ID."""
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Return standardized account status, balance, and positions."""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """Query real-time cash balance and purchasing power."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Query currently held stock positions."""
        pass

    @abstractmethod
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Retrieve latest market quote for a symbol."""
        pass

    @abstractmethod
    def get_daily_chart(self, symbol: str, count: int = 100) -> List[Dict[str, Any]]:
        """Retrieve historical daily price bars for technical analysis."""
        pass

    @abstractmethod
    def get_broker_info(self) -> Dict[str, Any]:
        """Retrieve broker gateway metadata, latency, and status."""
        pass

    @abstractmethod
    async def connect_websocket(self) -> bool:
        """Establish asynchronous WebSocket feed connection."""
        pass

    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, callback: Callable[[OrderbookDepth], Any]) -> bool:
        """Subscribe to real-time 10-level orderbook depth updates."""
        pass

    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback: Callable[[MarketTradeTick], Any]) -> bool:
        """Subscribe to real-time trade tick execution prints."""
        pass

    @abstractmethod
    async def subscribe_order_events(self, callback: Callable[[ExecutionNotice], Any]) -> bool:
        """Subscribe to private account order execution notices."""
        pass

    def parse_order_notice_frame(self, raw_data: Union[str, Dict[str, Any]]) -> Optional[ExecutionNotice]:
        """Parse incoming WebSocket order execution notice frame."""
        return None

    def _validate_order_safety(
        self,
        code: str,
        quantity: int,
        price: float,
        market_price: Optional[float] = None,
    ) -> None:
        """Enforce institutional pre-order safety guards."""
        if quantity <= 0:
            raise ValueError(f"Invalid order quantity {quantity} for {code}: must be strictly positive")

        if not math.isfinite(price) or price < 0.0:
            raise ValueError(f"Invalid order price {price} for {code}: must be finite and non-negative")

        order_val = float(price) * float(quantity)
        if order_val > self.max_order_value:
            raise ValueError(
                f"Order value {order_val:,.0f} KRW exceeds maximum allowed single order value limit of {self.max_order_value:,.0f} KRW"
            )

        if price > 0.0:
            ref = market_price
            if (ref is None or ref <= 0.0) and hasattr(self, "get_stock_quote"):
                try:
                    q = self.get_stock_quote(code)
                    if isinstance(q, dict) and float(q.get("price", 0.0)) > 0:
                        ref = float(q["price"])
                except Exception:
                    ref = None

            if ref is not None and ref > 0.0:
                dev = abs(price - ref) / ref
                if dev > self.max_price_deviation_pct:
                    raise ValueError(
                        f"Order price {price:,.0f} deviates by {dev:.2%} from market price {ref:,.0f}, "
                        f"exceeding ±{self.max_price_deviation_pct:.0%} sanity bound"
                    )


__all__ = [
    "OrderbookLevel",
    "OrderbookDepth",
    "MarketTradeTick",
    "ExecutionNotice",
    "PositionSnapshot",
    "AccountBalanceSnapshot",
    "ConnectedState",
    "BrokerResponse",
    "TokenBucketRateLimiter",
    "BaseBrokerConnector",
]

"""
Broker implementations for the trading system.

Hierarchy:
    BrokerBase (ABC)
    ├── RealBroker          — generic paper-trading / mock broker
    ├── KoreaInvestmentBroker — 한국투자증권 (Korea Investment & Securities)
    └── KiwoomBroker          — 키움증권 (Kiwoom Securities)
"""

import datetime
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ─── Abstract Base ────────────────────────────────────────────────────────────


class BrokerBase(ABC):
    """
    Abstract base class for all broker implementations.

    Every concrete broker must implement:
        connect()       — establish connection / authenticate
        submit_order()  — place an order and return a receipt
        get_balance()   — return cash / asset balance summary
        get_positions() — return list of currently open positions
    """

    @property
    def is_connected(self) -> bool:
        return getattr(self, "connected", False)

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the broker.

        Returns:
            True if connection succeeded, False otherwise.
        """
        ...

    @abstractmethod
    def submit_order(self, symbol: str, qty: float, side: str) -> dict:
        """
        Submit a market order.

        Args:
            symbol: Ticker symbol (e.g. 'SAMSUNG', '005930').
            qty:    Number of shares / units to trade.
            side:   'BUY' or 'SELL'.

        Returns:
            Order receipt dict with at least:
                order_id, symbol, qty, side, timestamp, status
        """
        ...

    @abstractmethod
    def get_balance(self) -> dict:
        """
        Retrieve current account balance.

        Returns:
            dict with cash, total_value, currency keys.
        """
        ...

    @abstractmethod
    def get_positions(self) -> list:
        """
        Retrieve list of open positions.

        Returns:
            list of dicts, each with symbol, qty, avg_price.
        """
        ...


# ─── RealBroker ───────────────────────────────────────────────────────────────


class RealBroker(BrokerBase):
    """
    Generic paper-trading broker implementation.

    Simulates order execution without connecting to any real exchange.
    Useful for testing strategies without live capital.
    """

    def __init__(self):
        self.connected: bool = False
        self._balance: float = 100_000_000.0  # ₩100M initial paper balance
        self._positions: list = []
        self._order_history: list = []

    def connect(self) -> bool:
        """
        Simulate broker connection.

        Returns:
            True (always succeeds for paper trading).
        """
        self.connected = True
        logger.info("RealBroker: connected (paper trading mode)")
        return True

    def submit_order(self, symbol: str, arg2: Any, arg3: Any) -> Any:
        """
        Submit a simulated market order.
        Supports both (symbol, qty, side) and (symbol, side, qty) parameter orders.
        """
        if not self.connected:
            raise ConnectionError("Broker not connected. Call connect() first.")
        if not symbol or not isinstance(symbol, str):
            raise ValueError("symbol must be a non-empty string")

        import math
        if isinstance(arg2, str):
            side = str(arg2).upper()
            try:
                f_qty = float(arg3)
                qty = f_qty if math.isfinite(f_qty) else 0.0
            except (ValueError, TypeError):
                qty = 0.0
        else:
            try:
                f_qty = float(arg2)
                qty = f_qty if math.isfinite(f_qty) else 0.0
            except (ValueError, TypeError):
                qty = 0.0
            side = str(arg3).upper()

        if qty <= 0:
            raise ValueError("qty must be > 0")
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")

        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        logger.info("RealBroker: order submitted %s %s x%s @ market", side, symbol, qty)

        receipt = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "price": 100.0,
            "timestamp": timestamp,
            "status": "FILLED",
            "broker": "RealBroker",
        }
        self._order_history.append(receipt)
        if isinstance(arg2, str):
            return True
        return receipt

    def get_order_history(self) -> list:
        return self._order_history

    def get_balance(self) -> dict:
        """Return simulated account balance."""
        return {
            "cash": self._balance,
            "total_value": self._balance,
            "currency": "KRW",
        }

    def get_positions(self) -> list:
        """Return simulated open positions (empty for paper broker)."""
        return list(self._positions)


# ─── Korea Investment & Securities ────────────────────────────────────────────


class KoreaInvestmentBroker(BrokerBase):
    """
    Korea Investment & Securities (한국투자증권) broker skeleton.

    Real API details:
    - Base URL:       https://openapi.koreainvestment.com:9443
    - Auth:           OAuth 2.0 — POST /oauth2/tokenP with app_key + app_secret
    - Order endpoint: POST /uapi/domestic-stock/v1/trading/order-cash
    - Required headers:
        Content-Type: application/json; charset=utf-8
        authorization: Bearer <access_token>
        appkey: <app_key>
        appsecret: <app_secret>
        tr_id: VTTC0802U (buy, simulation) / VTTC0801U (sell, simulation)
                TTTC0802U (buy, real)       / TTTC0801U (sell, real)
    - Simulation host: https://openapi.koreainvestment.com:9443  (same host, tr_id differs)
    - Documentation:  https://apiportal.koreainvestment.com

    This skeleton runs in simulation mode by default (no actual HTTP calls).
    To enable real trading, set simulation=False and provide valid credentials.
    """

    BASE_URL = "https://openapi.koreainvestment.com:9443"
    TOKEN_PATH = "/oauth2/tokenP"
    ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"

    def __init__(
        self,
        app_key: str = "",
        app_secret: str = "",
        account_no: str = "",
        simulation: bool = True,
        max_order_value: float = 50_000_000.0,
        max_price_deviation_pct: float = 0.03,
    ):
        """
        Args:
            app_key:    KIS Open API application key.
            app_secret: KIS Open API application secret.
            account_no: Brokerage account number (계좌번호).
            simulation: If True, use paper-trading tr_ids (VTTC*).
            max_order_value: Single order max value cap (default 50,000,000 KRW).
            max_price_deviation_pct: Limit price sanity bound (default ±3%).
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.simulation = simulation
        self.max_order_value = max_order_value
        self.max_price_deviation_pct = max_price_deviation_pct
        self._access_token: Optional[str] = None
        self.connected: bool = False
        self.orders: dict = {}

    def connect(self) -> bool:
        """
        Obtain an OAuth access token from KIS.
        In simulation mode (default) returns True without an actual HTTP call.

        Returns:
            True on success.
        """
        # In a real implementation this would POST to TOKEN_PATH
        # and store the returned access_token.
        self.connected = True
        self._access_token = "simulated_token_KIS"
        mode = "simulation" if self.simulation else "live"
        logger.info("KoreaInvestmentBroker: connected (%s mode)", mode)
        return True

    def submit_order(
        self,
        symbol: str,
        arg2: Any,
        arg3: Any,
        price: Optional[float] = None,
        market_price: Optional[float] = None,
    ) -> dict:
        """
        Submit an order to KIS.
        Supports both (symbol, qty, side) and (symbol, side, qty) parameter orders.
        Applies safety guards: single order max value cap and limit price sanity bounds.
        """
        if not self.connected:
            self.connect()

        if not symbol or not isinstance(symbol, str):
            raise ValueError("symbol must be a non-empty string")

        if isinstance(arg2, str):
            side = arg2
            qty = arg3
        else:
            qty = arg2
            side = arg3

        if qty <= 0:
            raise ValueError("qty must be > 0")
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")

        # Safety Guard 1: Single order max value cap
        if price is not None and price > 0:
            order_val = price * qty
            if order_val > self.max_order_value:
                raise ValueError(
                    f"Order value {order_val:,.0f} KRW exceeds single order max value cap of {self.max_order_value:,.0f} KRW"
                )

        # Safety Guard 2: Limit price sanity bounds (±3%)
        if price is not None and price > 0 and market_price is not None and market_price > 0:
            dev = abs(price - market_price) / market_price
            if dev > self.max_price_deviation_pct:
                raise ValueError(
                    f"Order price {price:,.0f} deviates by {dev:.2%} from market price {market_price:,.0f}, exceeding ±{self.max_price_deviation_pct:.0%} sanity bound"
                )

        # tr_id selects simulation vs. live and buy vs. sell
        if self.simulation:
            tr_id = "VTTC0802U" if side.upper() == "BUY" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side.upper() == "BUY" else "TTTC0801U"

        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        logger.info("KoreaInvestmentBroker: %s %s x%s (tr_id=%s)", side, symbol, qty, tr_id)

        receipt = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side.upper(),
            "price": price if price is not None else 0.0,
            "timestamp": timestamp,
            "status": "ACCEPTED",
            "tr_id": tr_id,
            "broker": "KoreaInvestmentBroker",
            "simulation": self.simulation,
        }
        self.orders[order_id] = receipt
        return receipt

    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if order_id in self.orders:
            self.orders[order_id]["status"] = "CANCELLED"
            logger.info("KoreaInvestmentBroker: order %s cancelled", order_id)
            return True
        return False

    def get_order_status(self, order_id: str) -> dict:
        """주문 상태 조회"""
        res = self.orders.get(order_id, {})
        return dict(res) if isinstance(res, dict) else {}

    def get_balance(self) -> dict:
        """
        Retrieve account balance from KIS.
        (Skeleton — returns simulated data.)
        """
        return {
            "cash": 50_000_000.0,
            "total_value": 50_000_000.0,
            "currency": "KRW",
            "broker": "KoreaInvestmentBroker",
        }

    def modify_order(self, order_id: str, new_price: float, new_order_type: str = "00") -> bool:
        """
        Modify existing unexecuted order (or convert to market order).
        new_order_type: '00' = limit, '01' = market
        """
        import math
        try:
            p = float(new_price) if (new_price is not None and math.isfinite(float(new_price))) else 0.0
        except (ValueError, TypeError):
            p = 0.0
        p = max(0.0, p)

        if order_id in self.orders and self.orders[order_id]["status"] in ("ACCEPTED", "PENDING"):
            self.orders[order_id]["price"] = p
            self.orders[order_id]["order_type"] = str(new_order_type)
            self.orders[order_id]["status"] = "MODIFIED"
            logger.info("KoreaInvestmentBroker: order %s modified (price=%.2f, type=%s)", order_id, p, new_order_type)
            return True
        return False

    def process_unfilled_orders(self, max_unfilled_seconds: float = 180.0) -> int:
        """
        Scan open orders older than max_unfilled_seconds (3 mins) and automatically convert to market order.
        """
        modified_count = 0
        now = datetime.datetime.now()
        for oid, order in list(self.orders.items()):
            if order.get("status") in ("ACCEPTED", "PENDING"):
                try:
                    order_time = datetime.datetime.fromisoformat(order["timestamp"])
                    elapsed = (now - order_time).total_seconds()
                    if elapsed >= max_unfilled_seconds:
                        logger.info("Unfilled order %s elapsed %.1fs -> Auto-converting to Market Order", oid, elapsed)
                        self.modify_order(oid, new_price=0.0, new_order_type="01")
                        order["status"] = "FILLED"
                        modified_count += 1
                except Exception as e:
                    logger.warning("Error processing unfilled order %s: %s", oid, e)
        return modified_count

    def get_positions(self) -> list:
        """
        Retrieve open positions from KIS.
        (Skeleton — returns empty list.)
        """
        return []


# ─── Kiwoom Securities ────────────────────────────────────────────────────────


class KiwoomBroker(BrokerBase):
    """
    Kiwoom Securities (키움증권) broker skeleton.

    Real API details:
    - Kiwoom uses a Windows COM-based API called OpenAPI+ (HTS-based).
    - Python wrapper: PyKiwoom (pip install pykiwoom) or QAxWidget (PyQt5).
    - COM progId:     'KHOPENAPI.KHOpenAPICtrl.1'
    - Connection:     QAxWidget.dynamicCall("CommConnect()") — launches HTS login popup.
    - Market order:   SendOrder(rqname, screen_no, account_no, order_type,
                                code, qty, price, hogagb, order_no)
        order_type: 1=buy, 2=sell
        hogagb:     '03'=market order
    - Requires:       Kiwoom HTS installed and logged in on a Windows machine.
    - Restriction:    Only available on Windows; COM calls are synchronous-event-driven.

    This skeleton does NOT make actual COM calls and works on any OS.
    """

    def __init__(
        self,
        account_no: str = "",
        screen_no: str = "1000",
    ):
        """
        Args:
            account_no: Kiwoom account number (계좌번호).
            screen_no:  Virtual screen number for order grouping.
        """
        self.account_no = account_no
        self.screen_no = screen_no
        self._kiwoom = None  # Would be QAxWidget in real usage
        self.connected: bool = False

    def connect(self) -> bool:
        """
        Simulate connection to Kiwoom HTS via COM.
        Real implementation would call:
            self._kiwoom = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
            self._kiwoom.dynamicCall('CommConnect()')

        Returns:
            True (skeleton — always succeeds).
        """
        self.connected = True
        logger.info("KiwoomBroker: connected (skeleton mode — no COM calls)")
        return True

    def submit_order(self, symbol: str, arg2: Any, arg3: Any) -> dict:
        """
        Submit a market order via Kiwoom OpenAPI+.
        Supports both (symbol, qty, side) and (symbol, side, qty) parameter orders.
        """
        if not self.connected:
            self.connect()

        if not symbol or not isinstance(symbol, str):
            raise ValueError("symbol must be a non-empty string")

        if isinstance(arg2, str):
            side = arg2
            qty = arg3
        else:
            qty = arg2
            side = arg3

        if qty <= 0:
            raise ValueError("qty must be > 0")
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")

        order_type = 1 if side.upper() == "BUY" else 2
        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        logger.info("KiwoomBroker: %s %s x%s (order_type=%s)", side, symbol, qty, order_type)

        return {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side.upper(),
            "timestamp": timestamp,
            "status": "SUBMITTED",
            "order_type": order_type,
            "screen_no": self.screen_no,
            "broker": "KiwoomBroker",
        }

    def get_balance(self) -> dict:
        """
        Retrieve account balance from Kiwoom.
        Real implementation would use TR code: opw00001 (예수금상세현황요청).
        (Skeleton — returns simulated data.)
        """
        return {
            "cash": 50_000_000.0,
            "total_value": 50_000_000.0,
            "currency": "KRW",
            "broker": "KiwoomBroker",
        }

    def get_positions(self) -> list:
        """
        Retrieve open positions from Kiwoom.
        Real implementation would use TR code: opw00018 (계좌평가잔고내역요청).
        (Skeleton — returns empty list.)
        """
        return []

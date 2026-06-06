"""
Broker implementations for the trading system.

Hierarchy:
    BrokerBase (ABC)
    ├── RealBroker          — generic paper-trading / mock broker
    ├── KoreaInvestmentBroker — 한국투자증권 (Korea Investment & Securities)
    └── KiwoomBroker          — 키움증권 (Kiwoom Securities)
"""

import uuid
import datetime
import logging
from abc import ABC, abstractmethod
from typing import Optional

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

    def connect(self) -> bool:
        """
        Simulate broker connection.

        Returns:
            True (always succeeds for paper trading).
        """
        self.connected = True
        logger.info("RealBroker: connected (paper trading mode)")
        return True

    def submit_order(self, symbol: str, qty: float, side: str) -> dict:
        """
        Submit a simulated market order.

        Args:
            symbol: Ticker symbol.
            qty:    Quantity (must be > 0).
            side:   'BUY' or 'SELL'.

        Returns:
            Order receipt dict.

        Raises:
            Exception: If broker is not connected.
            ValueError: If qty <= 0 or side is invalid.
        """
        if not self.connected:
            raise Exception("Broker not connected. Call connect() first.")
        if qty <= 0:
            raise ValueError("qty must be > 0")
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")

        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        logger.info("RealBroker: order submitted %s %s x%s @ market", side, symbol, qty)

        return {
            "order_id":  order_id,
            "symbol":    symbol,
            "qty":       qty,
            "side":      side,
            "timestamp": timestamp,
            "status":    "FILLED",
            "broker":    "RealBroker",
        }

    def get_balance(self) -> dict:
        """Return simulated account balance."""
        return {
            "cash":        self._balance,
            "total_value": self._balance,
            "currency":    "KRW",
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
    ):
        """
        Args:
            app_key:    KIS Open API application key.
            app_secret: KIS Open API application secret.
            account_no: Brokerage account number (계좌번호).
            simulation: If True, use paper-trading tr_ids (VTTC*).
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.simulation = simulation
        self._access_token: Optional[str] = None
        self.connected: bool = False

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

    def submit_order(self, symbol: str, qty: float, side: str) -> dict:
        """
        Submit an order to KIS.

        Args:
            symbol: 6-digit KRX ticker code (e.g. '005930' for Samsung).
            qty:    Number of shares.
            side:   'BUY' or 'SELL'.

        Returns:
            Order receipt dict.
        """
        if not self.connected:
            self.connect()

        # tr_id selects simulation vs. live and buy vs. sell
        if self.simulation:
            tr_id = "VTTC0802U" if side.upper() == "BUY" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side.upper() == "BUY" else "TTTC0801U"

        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        logger.info(
            "KoreaInvestmentBroker: %s %s x%s (tr_id=%s)", side, symbol, qty, tr_id
        )

        return {
            "order_id":   order_id,
            "symbol":     symbol,
            "qty":        qty,
            "side":       side.upper(),
            "timestamp":  timestamp,
            "status":     "ACCEPTED",
            "tr_id":      tr_id,
            "broker":     "KoreaInvestmentBroker",
            "simulation": self.simulation,
        }

    def get_balance(self) -> dict:
        """
        Retrieve account balance from KIS.
        (Skeleton — returns simulated data.)
        """
        return {
            "cash":        50_000_000.0,
            "total_value": 50_000_000.0,
            "currency":    "KRW",
            "broker":      "KoreaInvestmentBroker",
        }

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

    def submit_order(self, symbol: str, qty: float, side: str) -> dict:
        """
        Submit a market order via Kiwoom OpenAPI+.
        Real implementation would call:
            order_type = 1 if side == 'BUY' else 2
            self._kiwoom.dynamicCall(
                'SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)',
                ['order', self.screen_no, self.account_no, order_type,
                 symbol, qty, 0, '03', '']
            )

        Args:
            symbol: 6-digit KRX ticker (e.g. '005930').
            qty:    Number of shares.
            side:   'BUY' or 'SELL'.

        Returns:
            Order receipt dict.
        """
        if not self.connected:
            self.connect()

        order_type = 1 if side.upper() == "BUY" else 2
        order_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        logger.info("KiwoomBroker: %s %s x%s (order_type=%s)", side, symbol, qty, order_type)

        return {
            "order_id":   order_id,
            "symbol":     symbol,
            "qty":        qty,
            "side":       side.upper(),
            "timestamp":  timestamp,
            "status":     "SUBMITTED",
            "order_type": order_type,
            "screen_no":  self.screen_no,
            "broker":     "KiwoomBroker",
        }

    def get_balance(self) -> dict:
        """
        Retrieve account balance from Kiwoom.
        Real implementation would use TR code: opw00001 (예수금상세현황요청).
        (Skeleton — returns simulated data.)
        """
        return {
            "cash":        50_000_000.0,
            "total_value": 50_000_000.0,
            "currency":    "KRW",
            "broker":      "KiwoomBroker",
        }

    def get_positions(self) -> list:
        """
        Retrieve open positions from Kiwoom.
        Real implementation would use TR code: opw00018 (계좌평가잔고내역요청).
        (Skeleton — returns empty list.)
        """
        return []

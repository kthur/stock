"""
tests/test_phase112_broker_connectors.py — Comprehensive Unit & Integration Test Suite
Phase 112 (Release R128 / v119 Production Master, Feature F530)

Tests:
  - TC01: Class exports, version metadata, and alias trees conformance
  - TC02: Mirrored import parity between src.broker and trading_system.src.broker
  - TC03: Dual placement bit-for-bit SHA-256 hash identity across all mirrored files
  - TC04: BrokerProtocol runtime checkability and ConnectedState dual usability
  - TC05: KIS OAuth 2.0 token caching, disk persistence, and proactive refresh
  - TC06: LS OAuth 2.0 token caching and lifecycle validation
  - TC07: KIS order placement, revision, cancellation, and status tracking in simulation mode
  - TC08: LS order placement, revision, cancellation, and status tracking in simulation mode
  - TC09: Pre-order safety guards (50M KRW cap, ±3% price sanity, invalid qty/price rejection)
  - TC10: Real-time cash balance, purchasing power, and position queries
  - TC11: Market quote and historical daily chart bar generation
  - TC12: TokenBucketRateLimiter thread-safe and async-safe token replenishment
  - TC13: KIS H0STASP0 10-level orderbook depth parsing and ladder verification
  - TC14: KIS H0STCNT0 real-time trade execution print parsing
  - TC15: LS HA_ 10-level orderbook depth parsing and ladder verification
  - TC16: LS S3_ real-time trade execution print parsing
  - TC17: Asynchronous WebSocket streaming and event callback dispatch (Orderbook, Trades, Fills)
  - TC18: Broker gateway metadata, diagnostic telemetry, and disconnect cleanup
  - TC19: KIS H0STCNI0 private order fill and execution notice parser
  - TC20: LS SC0 private order fill and execution notice parser
  - TC21: Proactive token refresh threshold (< 3600s runway)
  - TC22: TokenBucketRateLimiter non-blocking mutex release during sleep
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
import pytest

from src.broker.kis_broker_connector import (
    AccountBalanceSnapshot,
    BaseBrokerConnector,
    BrokerResponse,
    ConnectedState,
    ExecutionNotice,
    FEATURE,
    KISBrokerConnector,
    KISConnector,
    KoreaInvestmentOpenAPIConnector,
    MarketTradeTick,
    OrderbookDepth,
    OrderbookLevel,
    Phase112KISConnector,
    PositionSnapshot,
    RELEASE,
    TokenBucketRateLimiter,
    VERSION,
)
from src.broker.ls_broker_connector import (
    EBestXingConnector,
    LSBrokerConnector,
    LSOpenAPIConnector,
    LSSecuritiesConnector,
    Phase112LSConnector,
)
from trading_system.src.broker.protocol import BrokerProtocol


class TestPhase112BrokerConnectors:
    """Comprehensive test suite for Phase 112 Native OpenAPI Broker Connectors."""

    def test_tc01_class_exports_and_aliases(self):
        """TC01: Verify all class exports, version metadata, and alias trees."""
        assert VERSION == 119
        assert RELEASE == "R128"
        assert FEATURE == "F530"

        # KIS Aliases
        assert KoreaInvestmentOpenAPIConnector is KISBrokerConnector
        assert KISConnector is KISBrokerConnector
        assert Phase112KISConnector is KISBrokerConnector

        # LS Aliases
        assert LSSecuritiesConnector is LSBrokerConnector
        assert EBestXingConnector is LSBrokerConnector
        assert LSOpenAPIConnector is LSBrokerConnector
        assert Phase112LSConnector is LSBrokerConnector

        # Base inheritance
        assert issubclass(KISBrokerConnector, BaseBrokerConnector)
        assert issubclass(LSBrokerConnector, BaseBrokerConnector)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify mirrored import parity between src.broker and trading_system.src.broker."""
        import src.broker as root_broker
        import trading_system.src.broker as ts_broker

        assert root_broker.KISBrokerConnector.__name__ == ts_broker.KISBrokerConnector.__name__
        assert root_broker.LSBrokerConnector.__name__ == ts_broker.LSBrokerConnector.__name__
        assert root_broker.BaseBrokerConnector.__name__ == ts_broker.BaseBrokerConnector.__name__
        assert root_broker.OrderbookDepth.__name__ == ts_broker.OrderbookDepth.__name__

    def test_tc03_sha256_hash_identity(self):
        """TC03: Guarantee bit-for-bit SHA-256 hash synchrony between src/ and trading_system/ mirrors."""
        root = Path(__file__).resolve().parent.parent

        file_pairs = [
            ("src/broker/kis_broker_connector.py", "trading_system/src/broker/kis_broker_connector.py"),
            ("src/broker/ls_broker_connector.py", "trading_system/src/broker/ls_broker_connector.py"),
            ("src/broker/__init__.py", "trading_system/src/broker/__init__.py"),
        ]

        for p1, p2 in file_pairs:
            path1 = root / p1
            path2 = root / p2
            assert path1.exists(), f"File {path1} does not exist"
            assert path2.exists(), f"File {path2} does not exist"

            h1 = hashlib.sha256(path1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(path2.read_bytes()).hexdigest()
            assert h1 == h2, f"SHA-256 mismatch between {p1} and {p2}:\n  {h1}\n  {h2}"

    def test_tc04_broker_protocol_runtime_check(self):
        """TC04: Verify BrokerProtocol compliance and ConnectedState dual usability."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        ls = LSBrokerConnector(account_number="98765432101", simulation_mode=True)

        assert isinstance(kis, BrokerProtocol)
        assert isinstance(ls, BrokerProtocol)

        # Before connect
        assert not kis.is_connected
        assert not kis.is_connected()
        assert kis.is_connected == False

        # Connect
        assert kis.connect("12345678") is True
        assert kis.is_connected
        assert kis.is_connected()
        assert kis.is_connected == True

        # Disconnect
        assert kis.disconnect() is True
        assert not kis.is_connected
        assert not kis.is_connected()

    def test_tc05_kis_token_caching_and_proactive_refresh(self):
        """TC05: Test KIS OAuth token disk caching, expiry threshold, and proactive refresh."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".kis_test_token.json"
            connector = KISBrokerConnector(
                account_number="12345678",
                simulation_mode=False,
                app_key="MOCK_KEY",
                app_secret="MOCK_SECRET",
                token_cache_path=str(cache_file),
            )

            # 1. No cache initially
            assert not connector._load_cached_token()

            # 2. Save valid unexpired token (> 3600s remaining)
            valid_exp = time.time() + 7200.0
            connector._save_cached_token("VALID_TOKEN_ABC", valid_exp)
            assert cache_file.exists()

            # 3. Load valid cache
            assert connector._load_cached_token() is True
            assert connector.access_token == "VALID_TOKEN_ABC"
            assert connector.token_expires_at == valid_exp

            # 4. Save token with < 3600s remaining (must be rejected for proactive refresh)
            stale_exp = time.time() + 1800.0
            connector._save_cached_token("STALE_TOKEN_XYZ", stale_exp)
            connector.access_token = None
            assert connector._load_cached_token() is False

    def test_tc06_ls_token_caching_and_lifecycle(self):
        """TC06: Test LS Securities OAuth token disk caching and expiry validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".ls_test_token.json"
            connector = LSBrokerConnector(
                account_number="12345678901",
                simulation_mode=False,
                app_key="MOCK_LS_KEY",
                app_secret="MOCK_LS_SECRET",
                token_cache_path=str(cache_file),
            )

            assert not connector._load_cached_token()

            valid_exp = time.time() + 8000.0
            connector._save_cached_token("VALID_LS_TOKEN_999", valid_exp)
            assert connector._load_cached_token() is True
            assert connector.access_token == "VALID_LS_TOKEN_999"

    def test_tc07_kis_order_lifecycle_simulation(self):
        """TC07: Test KIS order placement, revision, cancellation, and status tracking in simulation mode."""
        connector = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        connector.connect()

        initial_bal = connector.get_balance()
        initial_p_power = initial_bal["purchasing_power"]

        # Place BUY order
        code = "005930"
        price = 70000.0
        qty = 10
        receipt = connector.place_order(symbol=code, side="BUY", order_type="LIMIT", price=price, quantity=qty, market_price=70000.0)

        assert receipt["success"] is True
        order_id = receipt["order_id"]
        assert order_id != ""
        assert receipt["status"] == "SUBMITTED"

        # Verify purchasing power was deducted
        post_order_bal = connector.get_balance()
        assert post_order_bal["purchasing_power"] == initial_p_power - (price * qty)

        # Check status inquiry
        status_info = connector.get_order_status(order_id)
        assert status_info["order_id"] == order_id
        assert status_info["symbol"] == code
        assert status_info["status"] == "SUBMITTED"

        # Modify order: change price to 71000 and qty to 8
        mod_receipt = connector.modify_order(order_id=order_id, symbol=code, new_price=71000.0, new_quantity=8, market_price=70000.0)
        assert mod_receipt["success"] is True
        assert mod_receipt["status"] == "MODIFIED"

        mod_status = connector.get_order_status(order_id)
        assert mod_status["status"] == "MODIFIED"
        assert mod_status["price"] == 71000.0
        assert mod_status["quantity"] == 8

        # Cancel order
        cancel_receipt = connector.cancel_order(order_id)
        assert cancel_receipt["success"] is True
        assert cancel_receipt["status"] == "CANCELLED"
        assert cancel_receipt == True  # Boolean compatibility check

        # Verify purchasing power was fully refunded
        post_cancel_bal = connector.get_balance()
        assert post_cancel_bal["purchasing_power"] == initial_p_power

        # Cancel non-existent order
        non_existent = connector.cancel_order("NON_EXISTENT_999")
        assert non_existent["status"] == "NOT_FOUND"
        assert non_existent["success"] is False

    def test_tc08_ls_order_lifecycle_simulation(self):
        """TC08: Test LS order placement, revision, cancellation in simulation mode."""
        connector = LSBrokerConnector(account_number="12345678901", simulation_mode=True)
        connector.connect()

        code = "000660"
        price = 150000.0
        qty = 5
        receipt = connector.place_order(symbol=code, side="BUY", order_type="LIMIT", price=price, quantity=qty, market_price=150000.0)

        assert receipt["success"] is True
        order_id = receipt["order_id"]
        assert receipt["status"] == "SUBMITTED"

        # Modify order
        mod_res = connector.modify_order(order_id=order_id, symbol=code, new_price=151000.0, new_quantity=4, market_price=150000.0)
        assert mod_res["success"] is True
        assert mod_res["status"] == "MODIFIED"

        # Cancel order
        canc_res = connector.cancel_order(order_id)
        assert canc_res["success"] is True
        assert canc_res["status"] == "CANCELLED"

    def test_tc09_pre_order_safety_guards(self):
        """TC09: Enforce institutional pre-order safety guards across both connectors."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        ls = LSBrokerConnector(account_number="98765432101", simulation_mode=True)

        for conn in [kis, ls]:
            code = "005930"
            mkt_price = 70000.0

            # Guard 1: Single order max value cap (> 50,000,000 KRW)
            # 1,000 shares @ 60,000 = 60,000,000 KRW > 50M cap
            with pytest.raises(ValueError, match="exceeds maximum allowed single order value limit"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=60000.0, quantity=1000, market_price=mkt_price)

            # Guard 2: Price deviation sanity (> ±3.0% from market price 70,000)
            # Price 75,000 is +7.14% (> 3%)
            with pytest.raises(ValueError, match="deviates by"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=75000.0, quantity=10, market_price=mkt_price)

            # Price 65,000 is -7.14% (> 3%)
            with pytest.raises(ValueError, match="deviates by"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=65000.0, quantity=10, market_price=mkt_price)

            # Guard 3: Invalid quantity (<= 0)
            with pytest.raises(ValueError, match="must be strictly positive"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=70000.0, quantity=0, market_price=mkt_price)

            # Guard 4: Non-finite / negative price
            with pytest.raises(ValueError, match="must be finite and non-negative"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=-100.0, quantity=10, market_price=mkt_price)

            with pytest.raises(ValueError, match="must be finite and non-negative"):
                conn.place_order(symbol=code, side="BUY", order_type="LIMIT", price=float("nan"), quantity=10, market_price=mkt_price)

    def test_tc10_balance_and_position_queries(self):
        """TC10: Test balance, purchasing power, positions, and account info snapshots."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        bal = kis.get_balance()

        assert "cash_balance" in bal
        assert "purchasing_power" in bal
        assert "total_asset_value" in bal
        assert bal["cash_balance"] == 100_000_000.0

        positions = kis.get_positions()
        assert isinstance(positions, list)

        acct_info = kis.get_account_info()
        assert acct_info["account_number"] == "12345678"
        assert "positions" in acct_info
        assert "timestamp" in acct_info

    def test_tc11_market_quote_and_daily_chart(self):
        """TC11: Test market quote and historical daily chart bar generation."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        quote = kis.get_stock_quote("005930")
        assert quote["symbol"] == "005930"
        assert quote["price"] > 0.0
        assert quote["volume"] > 0

        bars = kis.get_daily_chart("005930", count=25)
        assert len(bars) == 25
        for b in bars:
            assert "open" in b and "high" in b and "low" in b and "close" in b and "volume" in b
            assert b["high"] >= b["low"]

        ls = LSBrokerConnector(account_number="98765432101", simulation_mode=True)
        ls_quote = ls.get_stock_quote("000660")
        assert ls_quote["symbol"] == "000660"
        assert ls_quote["price"] > 0.0

        ls_bars = ls.get_daily_chart("000660", count=15)
        assert len(ls_bars) == 15

    def test_tc12_token_bucket_rate_limiter(self):
        """TC12: Verify TokenBucketRateLimiter capacity, rate throttling, and async replenishment."""
        limiter = TokenBucketRateLimiter(rate=50.0, capacity=5.0)

        # Immediate acquire within capacity
        limiter.acquire(2.0)
        assert limiter.tokens <= 3.05

        # Async acquire
        async def _test_async():
            await limiter.acquire_async(1.0)
            assert limiter.tokens >= 0.0

        asyncio.run(_test_async())

    def test_tc13_kis_websocket_10_level_orderbook_parser(self):
        """TC13: Test KIS H0STASP0 10-level orderbook parser."""
        connector = KISBrokerConnector(simulation_mode=True)

        # Construct synthetic H0STASP0 raw frame:
        # code^hour^cls^ask1..10^bid1..10^askq1..10^bidq1..10^tot_ask^tot_bid
        asks_p = [str(70000 + i * 100) for i in range(1, 11)]
        bids_p = [str(70000 - i * 100) for i in range(1, 11)]
        asks_q = [str(100 + i * 10) for i in range(10)]
        bids_q = [str(120 + i * 10) for i in range(10)]

        payload = "005930^093000^0^" + "^".join(asks_p) + "^" + "^".join(bids_p) + "^" + "^".join(asks_q) + "^" + "^".join(bids_q) + "^15000^18000"
        raw_msg = f"0|H0STASP0|001|{payload}"

        depth = connector.parse_orderbook_frame(raw_msg)
        assert depth.symbol == "005930"
        assert len(depth.asks) == 10
        assert len(depth.bids) == 10
        assert depth.asks[0].price == 70100.0
        assert depth.bids[0].price == 69900.0
        assert depth.spread == pytest.approx(200.0)
        assert depth.mid_price == pytest.approx(70000.0)
        assert depth.total_ask_qty == 15000
        assert depth.total_bid_qty == 18000

    def test_tc14_kis_websocket_trade_tick_parser(self):
        """TC14: Test KIS H0STCNT0 real-time trade tick parser."""
        connector = KISBrokerConnector(simulation_mode=True)

        # code^time^price^sign^change^rate^ask^bid^qty^cum_vol^cum_amt...^side
        payload = "005930^093015^70200^2^200^0.28^70300^70200^25^150250^10500000000^0^0^1"
        raw_msg = f"0|H0STCNT0|001|{payload}"

        tick = connector.parse_trade_frame(raw_msg)
        assert tick.symbol == "005930"
        assert tick.price == 70200.0
        assert tick.quantity == 25
        assert tick.side == "BUY"
        assert tick.accumulated_volume == 150250
        assert tick.accumulated_amount == 10500000000.0

    def test_tc15_ls_websocket_10_level_orderbook_parser(self):
        """TC15: Test LS HA_ 10-level orderbook parser."""
        connector = LSBrokerConnector(simulation_mode=True)

        body_dict = {
            "shcode": "000660",
            "totofferrem": 22000,
            "totbidrem": 25000,
        }
        for i in range(1, 11):
            body_dict[f"offerho{i}"] = 150000.0 + i * 500.0
            body_dict[f"offerrem{i}"] = 200 + i * 20
            body_dict[f"bidho{i}"] = 150000.0 - i * 500.0
            body_dict[f"bidrem{i}"] = 250 + i * 20

        raw_frame = {
            "header": {"tr_key": "000660"},
            "body": body_dict,
        }

        depth = connector.parse_orderbook_frame(raw_frame)
        assert depth.symbol == "000660"
        assert len(depth.asks) == 10
        assert len(depth.bids) == 10
        assert depth.asks[0].price == 150500.0
        assert depth.bids[0].price == 149500.0
        assert depth.spread == pytest.approx(1000.0)
        assert depth.mid_price == pytest.approx(150000.0)

    def test_tc16_ls_websocket_trade_tick_parser(self):
        """TC16: Test LS S3_ real-time trade tick parser."""
        connector = LSBrokerConnector(simulation_mode=True)

        raw_frame = {
            "header": {"tr_key": "000660"},
            "body": {
                "shcode": "000660",
                "price": 150500.0,
                "cvolume": 12,
                "volume": 850000,
                "value": 127000000000.0,
                "cgubun": "1",  # 1: SELL
            },
        }

        tick = connector.parse_trade_frame(raw_frame)
        assert tick.symbol == "000660"
        assert tick.price == 150500.0
        assert tick.quantity == 12
        assert tick.side == "SELL"
        assert tick.accumulated_volume == 850000

    def test_tc17_async_streaming_and_callbacks(self):
        """TC17: Test asynchronous WebSocket feed subscription and callback execution."""
        async def _run_test():
            kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
            await kis.connect_websocket()

            received_books: List[OrderbookDepth] = []
            received_trades: List[MarketTradeTick] = []
            received_events: List[ExecutionNotice] = []

            def on_book(depth: OrderbookDepth):
                received_books.append(depth)

            def on_trade(tick: MarketTradeTick):
                received_trades.append(tick)

            def on_event(notice: ExecutionNotice):
                received_events.append(notice)

            await kis.subscribe_orderbook("005930", on_book)
            await kis.subscribe_trades("005930", on_trade)
            await kis.subscribe_order_events(on_event)

            # Trigger an order to generate execution notice
            kis.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)

            # Allow simulation loop to emit events
            await asyncio.sleep(0.7)

            await kis.disconnect_websocket()

            assert len(received_books) >= 1, "Should have received at least 1 simulated orderbook snapshot"
            assert len(received_trades) >= 1, "Should have received at least 1 simulated trade tick"
            assert len(received_events) >= 1, "Should have received at least 1 order execution notice"
            assert received_events[0].symbol == "005930"
            assert received_events[0].status == "SUBMITTED"

        asyncio.run(_run_test())

    def test_tc18_broker_info_and_diagnostics(self):
        """TC18: Test broker gateway metadata, diagnostic telemetry, and disconnect cleanup."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        kis.connect()
        info = kis.get_broker_info()

        assert info["broker_code"] == "KIS"
        assert info["version"] == 119
        assert info["release"] == "R128"
        assert info["feature"] == "F530"
        assert info["simulation_mode"] is True
        assert info["is_connected"] is True

        ls = LSBrokerConnector(account_number="98765432101", simulation_mode=True)
        ls.connect()
        ls_info = ls.get_broker_info()

        assert ls_info["broker_code"] == "LS"
        assert ls_info["version"] == 119
        assert ls_info["release"] == "R128"
        assert ls_info["feature"] == "F530"

        # Disconnect cleanup
        assert kis.disconnect() is True
        assert ls.disconnect() is True
        assert not kis.is_connected
        assert not ls.is_connected

    def test_tc19_kis_websocket_order_notice_parser(self):
        """TC19: Test KIS H0STCNI0 private order fill and status execution notice parser."""
        connector = KISBrokerConnector(simulation_mode=True)

        # 1. Standard 10-field reviewer format (BUY Fill)
        # odno^orgn_odno^pdno^sll_buy_dvsn_cd^ord_unpr^ord_qty^ccld_unpr^ccld_qty^remn_qty^ord_stus
        payload_10 = "KIS_ORD_1001^^005930^02^70000.0^10^70000.0^10^0^FILLED"
        raw_msg_10 = f"0|H0STCNI0|001|{payload_10}"
        notice = connector.parse_order_notice_frame(raw_msg_10)

        assert notice is not None
        assert isinstance(notice, ExecutionNotice)
        assert notice.order_id == "KIS_ORD_1001"
        assert notice.original_order_id is None
        assert notice.symbol == "005930"
        assert notice.side == "BUY"
        assert notice.exec_price == 70000.0
        assert notice.exec_quantity == 10
        assert notice.remaining_quantity == 0
        assert notice.status == "FILLED"
        assert notice.timestamp > 0.0

        # 2. Standard 14-field KIS Developers format (Partial SELL)
        # [0]CUST_ID^[1]ACNT^[2]ODNO^[3]ORGN^[4]SELN^[5]RVSE^[6]PDNO^[7]ORDQ^[8]ORDP^[9]CCLDQ^[10]CCLDP^[11]DVSN^[12]TIME^[13]REMNQ
        payload_14 = "USER001^12345678-01^KIS_ORD_1002^^01^01^000660^20^150000.0^8^150500.0^01^093045^12"
        raw_msg_14 = f"0|H0STCNI0|001|{payload_14}"
        notice_partial = connector.parse_order_notice_frame(raw_msg_14)

        assert notice_partial is not None
        assert notice_partial.order_id == "KIS_ORD_1002"
        assert notice_partial.symbol == "000660"
        assert notice_partial.side == "SELL"
        assert notice_partial.exec_price == 150500.0
        assert notice_partial.exec_quantity == 8
        assert notice_partial.remaining_quantity == 12
        assert notice_partial.status == "PARTIAL"

        # 3. Compact 7-field format (Order Cancellation)
        # order_id^symbol^side^exec_price^exec_qty^exec_time^order_status
        payload_7 = "KIS_ORD_1003^035420^02^0.0^0^093100^CANCELLED"
        raw_msg_7 = f"0|H0STCNI0|001|{payload_7}"
        notice_cancel = connector.parse_order_notice_frame(raw_msg_7)

        assert notice_cancel is not None
        assert notice_cancel.order_id == "KIS_ORD_1003"
        assert notice_cancel.symbol == "035420"
        assert notice_cancel.side == "BUY"
        assert notice_cancel.exec_quantity == 0
        assert notice_cancel.status == "CANCELLED"

        # 4. Error and edge case handling
        assert connector.parse_order_notice_frame("") is None
        assert connector.parse_order_notice_frame("invalid^payload") is None

    def test_tc20_ls_websocket_order_notice_parser(self):
        """TC20: Test LS SC0 private order fill and status execution notice parser."""
        connector = LSBrokerConnector(simulation_mode=True)

        # 1. Full JSON dict frame with header and body (BUY Fill)
        raw_frame_dict = {
            "header": {"tr_cd": "SC0", "tr_key": "98765432101"},
            "body": {
                "ordno": "LS_ORD_2001",
                "orgordno": "0",
                "expcode": "000660",
                "bnstp": "2",  # 2: BUY
                "ordprc": 150000.0,
                "ordqty": 15,
                "cheprc": 150000.0,
                "cheqty": 15,
                "remqty": 0,
                "status": "FILLED",
            },
        }
        notice_dict = connector.parse_order_notice_frame(raw_frame_dict)

        assert notice_dict is not None
        assert isinstance(notice_dict, ExecutionNotice)
        assert notice_dict.order_id == "LS_ORD_2001"
        assert notice_dict.original_order_id is None
        assert notice_dict.symbol == "000660"
        assert notice_dict.side == "BUY"
        assert notice_dict.exec_price == 150000.0
        assert notice_dict.exec_quantity == 15
        assert notice_dict.remaining_quantity == 0
        assert notice_dict.status == "FILLED"

        # 2. JSON string serialization (Partial SELL)
        raw_frame_str = json.dumps({
            "ordno": "LS_ORD_2002",
            "orgordno": None,
            "expcode": "005930",
            "bnstp": "1",  # 1: SELL
            "ordprc": 70000.0,
            "ordqty": 50,
            "cheprc": 70200.0,
            "cheqty": 20,
            "remqty": 30,
            "status": "PARTIAL",
        })
        notice_str = connector.parse_order_notice_frame(raw_frame_str)

        assert notice_str is not None
        assert notice_str.order_id == "LS_ORD_2002"
        assert notice_str.symbol == "005930"
        assert notice_str.side == "SELL"
        assert notice_str.exec_price == 70200.0
        assert notice_str.exec_quantity == 20
        assert notice_str.remaining_quantity == 30
        assert notice_str.status == "PARTIAL"

        # 3. Order Submission / Receipt notice (0 fills, remqty > 0)
        raw_submit_dict = {
            "ordno": "LS_ORD_2003",
            "expcode": "035420",
            "bnstp": "2",
            "ordprc": 210000.0,
            "ordqty": 5,
            "cheprc": 0.0,
            "cheqty": 0,
            "remqty": 5,
            "status": "SUBMITTED",
        }
        notice_submit = connector.parse_order_notice_frame(raw_submit_dict)

        assert notice_submit is not None
        assert notice_submit.order_id == "LS_ORD_2003"
        assert notice_submit.exec_quantity == 0
        assert notice_submit.remaining_quantity == 5
        assert notice_submit.status == "SUBMITTED"

        # 4. Order Cancellation notice
        raw_cancel_dict = {
            "ordno": "LS_ORD_2004",
            "orgordno": "LS_ORD_2003",
            "expcode": "035420",
            "bnstp": "2",
            "cheqty": 0,
            "remqty": 0,
            "status": "CANCELLED",
        }
        notice_cancel = connector.parse_order_notice_frame(raw_cancel_dict)

        assert notice_cancel is not None
        assert notice_cancel.order_id == "LS_ORD_2004"
        assert notice_cancel.original_order_id == "LS_ORD_2003"
        assert notice_cancel.status == "CANCELLED"

        # 5. Malformed input handling
        assert connector.parse_order_notice_frame("") is None
        assert connector.parse_order_notice_frame("{bad_json") is None
        assert connector.parse_order_notice_frame({}) is None

    def test_tc21_kis_and_ls_auth_headers_proactive_refresh_threshold(self):
        """TC21: Test proactive OAuth token refresh threshold (< 3600.0s) for KIS and LS connectors."""
        # KIS test
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=False, app_key="K", app_secret="S")
        kis._access_token = "TOKEN_VALID_LONG"
        kis._token_expires_at = time.time() + 4000.0  # > 3600s, should NOT refresh

        with unittest.mock.patch.object(kis, "issue_oauth_token") as mock_kis_issue:
            headers = kis._get_auth_headers()
            assert headers["authorization"] == "Bearer TOKEN_VALID_LONG"
            assert mock_kis_issue.call_count == 0

            # Set expiration to 2500s (< 3600s threshold, previously > 1800s would not refresh)
            kis._token_expires_at = time.time() + 2500.0
            mock_kis_issue.return_value = "TOKEN_REFRESHED_KIS"
            # Simulate issue_oauth_token updating token
            def side_effect_kis():
                kis._access_token = "TOKEN_REFRESHED_KIS"
                kis._token_expires_at = time.time() + 86400.0
                return "TOKEN_REFRESHED_KIS"
            mock_kis_issue.side_effect = side_effect_kis

            headers_refreshed = kis._get_auth_headers()
            assert mock_kis_issue.call_count == 1
            assert headers_refreshed["authorization"] == "Bearer TOKEN_REFRESHED_KIS"

        # LS test
        ls = LSBrokerConnector(account_number="98765432101", simulation_mode=False, app_key="K", app_secret="S")
        ls._access_token = "TOKEN_VALID_LS"
        ls._token_expires_at = time.time() + 4000.0  # > 3600s, should NOT refresh

        with unittest.mock.patch.object(ls, "issue_oauth_token") as mock_ls_issue:
            headers = ls._get_auth_headers()
            assert headers["authorization"] == "Bearer TOKEN_VALID_LS"
            assert mock_ls_issue.call_count == 0

            # Set expiration to 2500s (< 3600s threshold)
            ls._token_expires_at = time.time() + 2500.0
            def side_effect_ls():
                ls._access_token = "TOKEN_REFRESHED_LS"
                ls._token_expires_at = time.time() + 86400.0
                return "TOKEN_REFRESHED_LS"
            mock_ls_issue.side_effect = side_effect_ls

            headers_refreshed_ls = ls._get_auth_headers()
            assert mock_ls_issue.call_count == 1
            assert headers_refreshed_ls["authorization"] == "Bearer TOKEN_REFRESHED_LS"

    def test_tc22_token_bucket_rate_limiter_lock_non_blocking_during_sleep(self):
        """TC22: Test that TokenBucketRateLimiter releases lock during sleep, eliminating contention."""
        # Limiter with rate 2.0 (takes 0.5s per token) and capacity 1.0
        limiter = TokenBucketRateLimiter(rate=2.0, capacity=1.0)
        limiter.tokens = 0.0  # Empty bucket

        lock_acquired_during_sleep = []

        def worker_acquire():
            # Will need to sleep ~0.5s
            limiter.acquire(1.0)

        t = threading.Thread(target=worker_acquire)
        t.start()

        # Give worker a moment to enter acquire and start sleeping
        time.sleep(0.05)

        # While worker is sleeping, verify that the limiter's lock is FREE and accessible
        acquired = limiter._lock.acquire(blocking=False)
        lock_acquired_during_sleep.append(acquired)
        if acquired:
            limiter._lock.release()

        t.join(timeout=2.0)

        assert lock_acquired_during_sleep == [True], (
            "Lock contention defect: TokenBucketRateLimiter held self._lock while sleeping!"
        )


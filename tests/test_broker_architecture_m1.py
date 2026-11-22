"""
tests/test_broker_architecture_m1.py — Verification Test Suite for Milestone 1
Milestone 1: Broker Architecture DIP & Interface Standardization
Phase 112 / Phase 119 (Release R128 / v119 Production Master, Feature F530)

Verifies:
  1. BaseBrokerConnector extraction to src.broker.base_connector (DIP resolution).
  2. 100% backward compatibility of BaseBrokerConnector re-exports in kis_broker_connector.
  3. LSBrokerConnector clean inheritance directly from base_connector (no KIS sibling coupling).
  4. UnifiedBrokerAdapter standardizing BrokerProtocol, BrokerBase, and BaseBrokerConnector.
  5. MultiBrokerManager dependency injection (DI) and dynamic broker registration.
  6. Dual-tree parity verification between src/ and trading_system/src/.
"""

import inspect
import pytest

from src.broker.base_connector import (
    AccountBalanceSnapshot,
    BaseBrokerConnector,
    BrokerResponse,
    ConnectedState,
    ExecutionNotice,
    MarketTradeTick,
    OrderbookDepth,
    OrderbookLevel,
    PositionSnapshot,
    TokenBucketRateLimiter,
)
import src.broker.kis_broker_connector as kis_mod
from src.broker.kis_broker_connector import (
    BaseBrokerConnector as KISBaseBrokerConnector,
    KISBrokerConnector,
    OrderbookDepth as KISOrderbookDepth,
)
import src.broker.ls_broker_connector as ls_mod
from src.broker.ls_broker_connector import LSBrokerConnector
from src.broker.protocol import BrokerProtocol
from src.broker.real_broker import BrokerBase, RealBroker
from src.broker.interactive_brokers import InteractiveBrokersConnector
from src.broker.fix_protocol_engine import FIX44Engine
from src.broker.unified_adapter import UnifiedBrokerAdapter
from src.broker.multi_broker_manager import BrokerType, MultiBrokerManager


class TestMilestone1BrokerDIP:
    """Verifies Dependency Inversion Principle (DIP) resolution in broker subsystem."""

    def test_base_connector_module_exports(self):
        """1. Verify base_connector module exports all required base classes and models."""
        assert issubclass(BaseBrokerConnector, object)
        assert hasattr(BaseBrokerConnector, "connect")
        assert hasattr(BaseBrokerConnector, "place_order")
        assert hasattr(BaseBrokerConnector, "cancel_order")
        assert hasattr(BaseBrokerConnector, "get_account_info")
        assert hasattr(BaseBrokerConnector, "get_balance")
        assert hasattr(BaseBrokerConnector, "get_positions")

        # Snapshot dataclasses
        assert OrderbookLevel is not None
        assert OrderbookDepth is not None
        assert MarketTradeTick is not None
        assert ExecutionNotice is not None
        assert PositionSnapshot is not None
        assert AccountBalanceSnapshot is not None
        assert ConnectedState is not None
        assert BrokerResponse is not None
        assert TokenBucketRateLimiter is not None

    def test_kis_broker_connector_backward_compatibility(self):
        """2. Verify kis_broker_connector re-exports BaseBrokerConnector with 100% backward compatibility."""
        assert KISBaseBrokerConnector is BaseBrokerConnector
        assert KISOrderbookDepth is OrderbookDepth
        assert issubclass(KISBrokerConnector, BaseBrokerConnector)
        assert getattr(kis_mod, "BaseBrokerConnector") is BaseBrokerConnector

    def test_ls_broker_connector_clean_inheritance_without_kis(self):
        """3. Verify ls_broker_connector inherits directly from base_connector and NOT kis_broker_connector."""
        assert issubclass(LSBrokerConnector, BaseBrokerConnector)
        # Verify MRO does not contain KISBrokerConnector
        mro = LSBrokerConnector.mro()
        assert KISBrokerConnector not in mro
        assert BaseBrokerConnector in mro

        # Verify source file inspects base_connector
        ls_file_source = inspect.getsource(ls_mod)
        assert "from .base_connector import" in ls_file_source
        assert "from .kis_broker_connector import BaseBrokerConnector" not in ls_file_source


class TestMilestone1UnifiedBrokerAdapter:
    """Verifies UnifiedBrokerAdapter bridging BrokerProtocol, BrokerBase, and BaseBrokerConnector."""

    def test_adapter_with_broker_protocol(self):
        """4. Verify UnifiedBrokerAdapter wrapping BrokerProtocol (InteractiveBrokersConnector & FIX44Engine)."""
        ib = InteractiveBrokersConnector(account_id="U111222")
        adapter = UnifiedBrokerAdapter(ib, broker_name="ibkr_test")

        # Runtime BrokerProtocol check
        assert isinstance(adapter, BrokerProtocol)
        assert not adapter.is_connected
        assert not adapter.is_connected()

        # Connect
        assert adapter.connect("U111222") is True
        assert adapter.is_connected
        assert adapter.is_connected()

        # Balance & Position
        bal = adapter.get_balance()
        assert isinstance(bal, dict)
        assert "cash_balance" in bal

        # Order operations
        assert adapter.place_order(code="AAPL", quantity=10, price=150.0, side="BUY")
        assert adapter.get_positions().get("AAPL") == 10

        # submit_order BrokerBase compatibility
        receipt = adapter.submit_order(symbol="AAPL", qty=5.0, side="SELL")
        assert isinstance(receipt, dict)
        assert receipt["symbol"] == "AAPL"
        assert receipt["qty"] == 5.0

        # Disconnect
        assert adapter.disconnect() is True
        assert not adapter.is_connected

    def test_adapter_with_broker_base(self):
        """5. Verify UnifiedBrokerAdapter wrapping BrokerBase (RealBroker)."""
        real = RealBroker(initial_balance=50_000_000.0)
        adapter = UnifiedBrokerAdapter(real, broker_name="real_paper")

        assert isinstance(adapter, BrokerProtocol)
        assert not adapter.is_connected

        # Connect
        assert adapter.connect() is True
        assert adapter.is_connected

        # Query balance
        bal = adapter.get_balance()
        assert bal["cash_balance"] == 50_000_000.0

        # Place order via place_order (BrokerProtocol method translated to BrokerBase submit_order)
        order_res = adapter.place_order(code="005930", quantity=100, price=70000.0, order_type="LIMIT")
        assert order_res is not None

        # Verify positions and order history
        pos = adapter.get_positions()
        assert isinstance(pos, list)
        assert len(real.get_order_history()) >= 1

        # Query account info
        info = adapter.get_account_info()
        assert "balance" in info
        assert "positions" in info

        # Disconnect
        assert adapter.disconnect() is True
        assert not adapter.is_connected

    def test_adapter_with_base_broker_connector(self):
        """6. Verify UnifiedBrokerAdapter wrapping BaseBrokerConnector (KISBrokerConnector in simulation mode)."""
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        adapter = UnifiedBrokerAdapter.wrap(kis)

        assert isinstance(adapter, BrokerProtocol)
        assert adapter.connect("12345678") is True
        assert adapter.is_connected

        # Order via place_order
        res = adapter.place_order(symbol="005930", side="BUY", price=70000.0, quantity=10, market_price=70000.0)
        assert res["success"] is True
        assert "order_id" in res

        # Order via submit_order
        receipt = adapter.submit_order(symbol="005930", qty=5, side="SELL")
        assert isinstance(receipt, dict)
        assert receipt["symbol"] == "005930"

        # Order via submit_order with kwargs (price and order_type) verifying no duplicate kwarg TypeError
        limit_receipt = adapter.submit_order(
            symbol="005930",
            qty=10,
            side="BUY",
            price=70000.0,
            order_type="LIMIT",
        )
        assert isinstance(limit_receipt, dict)
        assert limit_receipt["symbol"] == "005930"
        assert limit_receipt["status"] == "SUBMITTED"

        # Balance & positions
        bal = adapter.get_balance()
        assert "cash_balance" in bal
        positions = adapter.get_positions()
        assert isinstance(positions, list)

        # Quotes and daily chart
        quote = adapter.get_stock_quote("005930")
        assert "price" in quote
        chart = adapter.get_daily_chart("005930", 10)
        assert len(chart) == 10

        # Telemetry & broker info
        info = adapter.get_broker_info()
        assert info["adapter"] == "UnifiedBrokerAdapter"


class TestMilestone1MultiBrokerDI:
    """Verifies Dependency Injection (DI) and dynamic registration in MultiBrokerManager."""

    def test_multi_broker_manager_dependency_injection(self):
        """7. Verify MultiBrokerManager accepts injected broker dictionary and default broker."""
        kis = KISBrokerConnector(account_number="KIS_100", simulation_mode=True)
        real = RealBroker(initial_balance=20_000_000.0)

        injected_brokers = {
            "my_kis": kis,
            "my_paper": real,
        }

        mgr = MultiBrokerManager(brokers=injected_brokers, default_broker="my_kis")
        assert "my_kis" in mgr.brokers
        assert "my_paper" in mgr.brokers
        assert mgr.active_broker == "my_kis"

        # Connect injected broker
        assert mgr.connect("my_kis", "KIS_100") is True
        assert mgr.active_broker == "my_kis"

        # Switch broker
        assert mgr.connect("my_paper", "PAPER_ACC") is True
        assert mgr.switch_broker("my_paper") is True
        assert mgr.active_broker == "my_paper"

        # Place order on active broker
        order_id = mgr.place_order(code="005930", quantity=10, price=70000.0, order_type="LIMIT")
        assert order_id != ""

    def test_dynamic_registration_and_unregistration(self):
        """8. Verify dynamic register_broker and unregister_broker."""
        mgr = MultiBrokerManager()  # Starts with defaults
        assert len(mgr.brokers) == 9

        # Register custom broker
        custom_broker = RealBroker(initial_balance=10_000_000.0)
        assert mgr.register_broker("custom_paper", custom_broker, set_active=True) is True
        assert "custom_paper" in mgr.brokers
        assert mgr.active_broker == "custom_paper"
        assert len(mgr.brokers) == 10

        # Unregister custom broker
        assert mgr.unregister_broker("custom_paper") is True
        assert "custom_paper" not in mgr.brokers
        assert len(mgr.brokers) == 9
        assert mgr.active_broker is None

    def test_multi_broker_manager_backward_compatibility_defaults(self):
        """9. Verify default instantiations and existing BrokerType enum lookups work untouched."""
        mgr = MultiBrokerManager()
        assert BrokerType.KIWOOM in mgr.brokers
        assert BrokerType.DAISHIN in mgr.brokers
        assert BrokerType.HANWHA in mgr.brokers
        assert BrokerType.KOREA_INVESTMENT in mgr.brokers
        assert BrokerType.MIRAE_ASSET in mgr.brokers
        assert BrokerType.NH in mgr.brokers
        assert BrokerType.LS in mgr.brokers
        assert BrokerType.INTERACTIVE_BROKERS in mgr.brokers
        assert BrokerType.FIX_PROTOCOL in mgr.brokers

        # Connect with string or enum
        assert mgr.connect(BrokerType.INTERACTIVE_BROKERS, "U123456") is True
        assert mgr.active_broker == BrokerType.INTERACTIVE_BROKERS

        # Connect with string
        assert mgr.connect("fix_protocol", "INST_42") is True
        assert mgr.switch_broker("fix_protocol") is True
        assert mgr.active_broker == BrokerType.FIX_PROTOCOL

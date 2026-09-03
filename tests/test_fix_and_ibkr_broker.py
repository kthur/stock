"""Unit and Integration Tests for FIX 4.4 Protocol, Interactive Brokers, and Global Multi-Broker Routing."""

import pytest
from src.broker.fix_protocol_engine import FIXMessage, FIX44Engine, SOH
from src.broker.interactive_brokers import InteractiveBrokersConnector
from src.broker.multi_broker_manager import MultiBrokerManager, BrokerType
from src.execution.smart_order_router import SmartOrderRouter


def test_fix_message_encoding_checksum():
    """Test standard FIX 4.4 message encoding, BodyLength, and CheckSum calculation."""
    msg = FIXMessage(msg_type="D", sender_comp_id="ANTIGRAVITY", target_comp_id="CBOE")
    msg.set(11, "ORD_12345")
    msg.set(55, "AAPL")
    msg.set(54, "1") # BUY
    msg.set(38, 100) # Qty 100
    msg.set(40, "2") # Limit
    msg.set(44, "150.25")

    encoded = msg.encode(msg_seq_num=42)
    assert encoded.startswith("8=FIX.4.4\x019=")
    assert "\x0135=D\x01" in encoded
    assert "\x0149=ANTIGRAVITY\x01" in encoded
    assert "\x0156=CBOE\x01" in encoded
    assert "\x0134=42\x01" in encoded
    assert "\x0155=AAPL\x01" in encoded
    assert "\x0110=" in encoded
    assert encoded.endswith("\x01")

    # Verify CheckSum mathematically
    idx_10 = encoded.rfind("10=")
    body_to_check = encoded[:idx_10]
    expected_chk = f"{sum(body_to_check.encode('latin-1')) % 256:03d}"
    actual_chk = encoded[idx_10+3:idx_10+6]
    assert actual_chk == expected_chk


def test_fix_message_decoding():
    """Test decoding a raw FIX string back into a structured FIXMessage."""
    raw = "8=FIX.4.4\x019=65\x0135=8\x0149=EXCHANGE\x0156=ANTIGRAVITY\x0134=10\x0155=NVDA\x0139=2\x0110=123\x01"
    decoded = FIXMessage.decode(raw)
    assert decoded.msg_type == "8" # ExecutionReport
    assert decoded.sender_comp_id == "EXCHANGE"
    assert decoded.target_comp_id == "ANTIGRAVITY"
    assert decoded.get(55) == "NVDA"
    assert decoded.get(39) == "2" # Filled


def test_fix44_engine_lifecycle_and_orders():
    """Test FIX44Engine session connection, buy/sell executions, and position tracking."""
    engine = FIX44Engine(sender_comp_id="ANTIGRAVITY_DMA", target_comp_id="NASDAQ_GATEWAY")
    assert engine.is_connected is False

    assert engine.connect("ACC_9999") is True
    assert engine.is_connected is True

    init_bal = engine.get_balance()
    # Buy 50 MSFT at 300.0
    ok_buy = engine.buy("MSFT", 50, price=300.0)
    assert ok_buy is True
    assert engine.get_positions().get("MSFT") == 50
    assert engine.get_balance() == init_bal - (50 * 300.0)

    # Sell 20 MSFT at 310.0
    ok_sell = engine.sell("MSFT", 20, price=310.0)
    assert ok_sell is True
    assert engine.get_positions().get("MSFT") == 30
    assert engine.get_balance() == (init_bal - 15000.0) + (20 * 310.0)

    # Disconnect
    assert engine.disconnect() is True
    assert engine.is_connected is False


def test_interactive_brokers_connector():
    """Test InteractiveBrokersConnector for US equity executions."""
    ib = InteractiveBrokersConnector(account_id="U888888")
    assert ib.connect("U888888") is True
    assert ib.is_connected is True

    init_bal = ib.get_balance()
    # Buy 100 TSLA at 200.0
    assert ib.buy("TSLA", 100, price=200.0) is True
    assert ib.get_positions().get("TSLA") == 100
    assert ib.get_balance() == init_bal - 20000.0

    # Sell 50 TSLA at 210.0
    assert ib.sell("TSLA", 50, price=210.0) is True
    assert ib.get_positions().get("TSLA") == 50
    assert ib.get_balance() == (init_bal - 20000.0) + 10500.0

    assert ib.disconnect() is True
    assert ib.is_connected is False


def test_multi_broker_manager_integration():
    """Verify MultiBrokerManager registers IBKR and FIX Protocol."""
    mgr = MultiBrokerManager()
    assert BrokerType.INTERACTIVE_BROKERS in mgr.brokers
    assert BrokerType.FIX_PROTOCOL in mgr.brokers

    # Connect to IBKR
    assert mgr.connect(BrokerType.INTERACTIVE_BROKERS, "U123456") is True
    assert mgr.active_broker == BrokerType.INTERACTIVE_BROKERS

    # Switch to FIX Protocol
    assert mgr.connect(BrokerType.FIX_PROTOCOL, "INST_99") is True
    assert mgr.switch_broker(BrokerType.FIX_PROTOCOL) is True
    assert mgr.active_broker == BrokerType.FIX_PROTOCOL


def test_smart_order_router_global_destination():
    """Verify SmartOrderRouter dispatches KRX vs US orders to appropriate brokers and venues."""
    sor = SmartOrderRouter()

    # 1. KRX symbol (005930)
    krx_plan = {"symbol": "005930", "market": "KOSPI", "action": "BUY", "quantity": 100, "target_price": 70000.0}
    krx_res = sor.route_order(krx_plan)
    assert krx_res["destination"]["market_region"] == "KRX"
    assert krx_res["destination"]["primary_broker"] == "korea_investment"
    assert krx_res["destination"]["venue"] == "KRX_ATS_NEXTRADE"

    # 2. US symbol (AAPL)
    us_plan = {"symbol": "AAPL", "market": "NASDAQ", "action": "BUY", "quantity": 50, "target_price": 180.0}
    us_res = sor.route_order(us_plan)
    assert us_res["destination"]["market_region"] == "US"
    assert us_res["destination"]["primary_broker"] == "interactive_brokers"
    assert us_res["destination"]["dma_gateway"] == "fix_protocol"
    assert us_res["destination"]["venue"] == "US_SMART_DMA"
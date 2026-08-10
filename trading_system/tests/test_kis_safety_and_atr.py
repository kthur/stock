"""
Unit tests for Requirement 3 (R3: KIS Automated Trading Safety & ATR Trailing Stop)
- Sector Risk Cap enforcement across RiskManager, PortfolioAllocator, TradingAgent, TradingSystem
- ATR Dynamic Trailing Stop evaluation & OrderManagementSystem synchronization
- KIS Broker Execution & Safety Guards (cancel_order, get_order_status, ±3% limit price sanity, 50M KRW single order max cap)
"""

import pytest
import pandas as pd

from src.risk.risk_manager import RiskManager
from src.risk.position_sizing import PortfolioAllocator
from src.broker.korea_investment import KoreaInvestmentConnector
from src.broker.real_broker import KoreaInvestmentBroker
from src.config import TradingConfig
from trading_system.trading_system import StockTradingSystem


# ─────────────────────────────────────────────────────────────────────────────
# 1. Sector Risk Cap Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_manager_sector_risk_cap():
    """Test RiskManager sector risk cap check and max sector position value calculation."""
    rm = RiskManager(portfolio_value=100_000_000.0, max_sector_exposure_pct=0.30)

    # 20M current exposure + 5M new trade = 25M (25%) <= 30% -> True
    assert rm.check_sector_risk_cap("Technology", 20_000_000.0, 5_000_000.0, 100_000_000.0) is True

    # 25M current exposure + 10M new trade = 35M (35%) > 30% -> False
    assert rm.check_sector_risk_cap("Technology", 25_000_000.0, 10_000_000.0, 100_000_000.0) is False

    # Max allowed sector position value calculation
    # Total portfolio = 100M, max 30% = 30M. Current exposure = 18M -> Max additional = 12M
    max_additional = rm.calculate_max_sector_position_value("Technology", 18_000_000.0, 100_000_000.0)
    assert max_additional == pytest.approx(12_000_000.0)

    # Current exposure = 35M (> 30M cap) -> Max additional = 0.0
    max_over = rm.calculate_max_sector_position_value("Technology", 35_000_000.0, 100_000_000.0)
    assert max_over == 0.0


def test_portfolio_allocator_sector_risk_cap():
    """Test PortfolioAllocator enforcing 30% max sector exposure on allocated weights."""
    allocator = PortfolioAllocator(
        max_single_position=0.25,
        max_total_allocation=0.80,
        max_sector_exposure=0.30
    )

    # 3 candidates in Tech sector with high returns
    predictions_df = pd.DataFrame([
        {'symbol': 'TECH1', 20: 0.15},
        {'symbol': 'TECH2', 20: 0.12},
        {'symbol': 'TECH3', 20: 0.10},
        {'symbol': 'FIN1', 20: 0.05},
    ])

    # Dummy price data with low volatility so weights remain high
    dates = pd.date_range("2026-01-01", periods=30)
    prices_dict = {
        sym: pd.DataFrame({
            'Close': [100.0 + i * 0.1 for i in range(30)],
            'High': [101.0 + i * 0.1 for i in range(30)],
            'Low': [99.0 + i * 0.1 for i in range(30)],
            'Open': [100.0 + i * 0.1 for i in range(30)],
            'Volume': [1000.0 for _ in range(30)]
        }, index=dates)
        for sym in ['TECH1', 'TECH2', 'TECH3', 'FIN1']
    }

    sector_map = {
        'TECH1': 'Technology',
        'TECH2': 'Technology',
        'TECH3': 'Technology',
        'FIN1': 'Finance',
    }

    df_alloc = allocator.allocate(
        predictions_df,
        prices_dict,
        total_portfolio_value=100_000_000.0,
        sector_map=sector_map
    )

    assert not df_alloc.empty

    # Calculate sum of allocated weights for Technology sector
    tech_candidates = df_alloc[df_alloc['symbol'].isin(['TECH1', 'TECH2', 'TECH3'])]
    tech_weight_sum = tech_candidates['weight'].sum()

    # Total technology weight must not exceed 0.30 (30%)
    assert float(tech_weight_sum) <= 0.30 + 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# 2. ATR Dynamic Trailing Stop & Order Sync Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_manager_atr_trailing_stop_signal_and_price():
    """Test RiskManager calculation of ATR trailing stop price and trigger signal."""
    rm = RiskManager(portfolio_value=100_000_000.0)
    rm.peak_value = 100_000_000.0

    highest_price = 100000.0
    atr = 2000.0

    # Under weak_bull with risk_config StopLoss=5.0%, expected trailing stop price = 100000 - 5000 = 95000
    stop_price = rm.calculate_trailing_stop_price(highest_price, atr, regime="weak_bull", adx=20.0)
    assert stop_price in (pytest.approx(95000.0), pytest.approx(96000.0))

    # Current price = 97000 (> stop_price 96000) -> Signal False
    assert rm.check_trailing_stop_signal("005930", 97000.0, highest_price, atr, regime="weak_bull", adx=20.0) is False

    # Current price = 94000 (<= stop_price 96000) -> Signal True
    assert rm.check_trailing_stop_signal("005930", 94000.0, highest_price, atr, regime="weak_bull", adx=20.0) is True


def test_trading_system_trailing_stop_order_sync():
    """Test TradingSystem updating trailing stops and synchronizing with OrderManagementSystem."""
    config = TradingConfig(initial_cash=100_000_000.0, mock_trading=True)
    system = StockTradingSystem(config=config)

    symbol = "005930"
    entry_price = 70000.0
    qty = 100

    # Setup open position
    system.portfolio.add_position(symbol, qty, entry_price)
    pos = system.portfolio.positions[symbol]
    pos.highest_price = 70000.0

    # Create stop loss order in OrderManagementSystem
    initial_sl_price = 65000.0
    sl_order = system.order_management.create_stop_loss_order(symbol, qty, initial_sl_price)

    # Mock tech_cache to return ATR = 2000.0
    system._tech_cache.get = lambda sym, keys, default: {'atr': 2000.0}

    # New peak price = 80000.0
    # RiskManager calculated ATR stop price for highest=80000, atr=2000 (distance = 5000) -> 75000.0
    system._update_trailing_stops(symbol, 80000.0)

    # Check that highest price in position updated
    assert pos.highest_price == 80000.0

    # Check that the stop-loss order trigger_price in OrderManagementSystem was updated to >= 75000.0
    updated_order = system.order_management.get_order(sl_order.order_id)
    assert updated_order is not None
    assert updated_order.trigger_price >= 75000.0
    assert updated_order.price >= 75000.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. KIS Broker Execution & Safety Guards Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_koreainvestment_connector_order_operations_and_safety_guards():
    """Test KoreaInvestmentConnector cancel_order, get_order_status, and pre-order safety guards."""
    connector = KoreaInvestmentConnector(account_number="1234567801", use_mock=True)
    connector.simulation_mode = True

    code = "005930"
    market_price = 70000.0

    # Valid order placement
    order_id = connector.place_order(code=code, quantity=10, price=70000.0, order_type="BUY", market_price=market_price)
    assert order_id != ""

    # Test get_order_status
    status_info = connector.get_order_status(order_id)
    assert status_info.get("order_id") == order_id
    assert status_info.get("code") == code
    assert status_info.get("status") in ("0", "SUBMITTED")

    # Test cancel_order
    cancel_success = connector.cancel_order(order_id)
    assert cancel_success is True

    # Status after cancellation
    cancelled_status = connector.get_order_status(order_id)
    assert cancelled_status.get("status") == "CANCELLED"

    # Test safety guard 1: Single order max value cap (> 50,000,000 KRW)
    with pytest.raises(ValueError, match="exceeds maximum allowed single order value limit"):
        connector.place_order(code=code, quantity=1000, price=60000.0, order_type="BUY", market_price=market_price)

    # Test safety guard 2: Limit price sanity bound (> ±3% deviation from market price 70000)
    # Price 75000 is +7.14% (> 3%) -> Exception
    with pytest.raises(ValueError, match="deviates by"):
        connector.place_order(code=code, quantity=10, price=75000.0, order_type="BUY", market_price=market_price)

    # Price 65000 is -7.14% (> 3%) -> Exception
    with pytest.raises(ValueError, match="deviates by"):
        connector.place_order(code=code, quantity=10, price=65000.0, order_type="BUY", market_price=market_price)

    # Price 71500 is +2.14% (<= 3%) -> OK
    valid_id = connector.place_order(code=code, quantity=10, price=71500.0, order_type="BUY", market_price=market_price)
    assert valid_id != ""


def test_koreainvestment_broker_safety_guards_and_order_tracking():
    """Test KoreaInvestmentBroker class in real_broker.py for safety guards and status inquiry."""
    broker = KoreaInvestmentBroker(account_no="12345678", simulation=True)
    broker.connect()

    symbol = "005930"
    market_price = 70000.0

    # Valid order submission
    receipt = broker.submit_order(symbol, 10, "BUY", price=71000.0, market_price=market_price)
    order_id = receipt["order_id"]
    assert receipt["status"] == "ACCEPTED"

    # Test get_order_status
    status = broker.get_order_status(order_id)
    assert status.get("order_id") == order_id
    assert status.get("status") == "ACCEPTED"

    # Test cancel_order
    assert broker.cancel_order(order_id) is True
    assert broker.get_order_status(order_id).get("status") == "CANCELLED"

    # Test safety guard 1: Max single order value cap (> 50,000,000 KRW)
    with pytest.raises(ValueError, match="exceeds single order max value cap"):
        broker.submit_order(symbol, 1000, "BUY", price=60000.0, market_price=market_price)

    # Test safety guard 2: Limit price sanity bound (> 3% deviation)
    with pytest.raises(ValueError, match="deviates by"):
        broker.submit_order(symbol, 10, "BUY", price=75000.0, market_price=market_price)

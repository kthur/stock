import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import TradingConfig
from src.core.factory import SystemFactory
from src.utils import EventBus
from trading_system import StockTradingSystem
from src.core.order_management import OrderType

async def main():
    event_bus = EventBus()
    config = TradingConfig(initial_cash=100000.0)
    components = SystemFactory.create_default_components(config.initial_cash, event_bus)
    system = StockTradingSystem(initial_cash=100000.0, config=config, components=components)
    system.market_data_handler.fetch_historical_data = MagicMock(return_value=[])
    system.market_data_cache["VIX"] = {"price": 30.0}
    system.risk_manager.calculate_position_sizing = MagicMock(return_value=500)

    try:
        print("Submitting order...")
        await system._create_and_submit_order("AAPL", OrderType.BUY, 100.0)
        print("Submitted order successfully.")
    except Exception as e:
        print("EXCEPTION RAISED:", e)
        import traceback
        traceback.print_exc()

    print("Orders dict keys:", list(system.order_management.orders.keys()))
    print("All orders:")
    for oid, o in system.order_management.orders.items():
         print(f"  {oid}: symbol={o.symbol}, type={o.order_type}, qty={o.quantity}, price={o.price}, status={o.status}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from trading_system import StockTradingSystem


if __name__ == "__main__":
    system = StockTradingSystem(initial_cash=1000000)
    asyncio.run(system.simulate_trading_day("AAPL"))
    system.start_dashboard()

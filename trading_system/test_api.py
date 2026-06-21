import sys
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.append("d:/Finance/code/stock/trading_system")

from src.analysis.backtest import BacktestEngine
from src.data_layer.market_data_handler import MarketDataHandler

async def run():
    handler = MarketDataHandler()
    engine = BacktestEngine()
    bars = handler.fetch_historical_data("AAPL", "1y")
    result = engine.run_backtest("AAPL", bars, engine.get_strategy_func("MA"))

    dates_str = [d.strftime("%Y-%m-%d") for d in getattr(result, 'dates', [])]
    price_curve = getattr(result, 'price_curve', [])
    equity_curve = getattr(result, 'equity_curve', [])
    print(f"dates_str len: {len(dates_str)}, price_curve len: {len(price_curve)}, equity_curve len: {len(equity_curve)}")
    print("Trades count:", len(result.trades))

if __name__ == "__main__":
    asyncio.run(run())

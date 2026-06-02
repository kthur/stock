import asyncio
from trading_system import StockTradingSystem

# 1. 초기 자본금 100만 달러로 시스템 생성
system = StockTradingSystem(initial_cash=1000000)

# 2. AAPL 주식을 시뮬레이션하여 기초 데이터를 채워 넣음
asyncio.run(system.simulate_trading_day("AAPL"))

# 3. FastAPI 대시보드 서버 시작
system.start_dashboard()

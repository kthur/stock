"""주식 트레이딩 시스템 테스트"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from trading_system import StockTradingSystem


async def main():
    """메인 테스트 실행 (비동기)"""
    
    # 시스템 초기화 (100만원 초기 자본금)
    system = StockTradingSystem(initial_cash=1000000)
    
    print("\n" + "="*60)
    print("주식 트레이딩 시스템 - 데모")
    print("="*60 + "\n")
    
    # 1. AAPL 거래 시뮬레이션
    print(">>> AAPL 거래 시뮬레이션 시작\n")
    await system.simulate_trading_day(symbol="AAPL")
    
    print("\n" + "-"*60)
    
    # 2. 거래 상태 조회
    print("\n>>> 현재 거래 상태\n")
    status = system.get_trading_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-"*60)
    
    # 3. 증권사 계좌 동기화
    print("\n>>> 증권사 계좌 동기화\n")
    broker_cash = 900000
    broker_holdings = {"AAPL": 10}
    system.sync_with_broker(broker_cash, broker_holdings)
    
    print("\n" + "-"*60)
    
    # 4. 거래 이력 조회
    print("\n>>> AAPL 거래 이력\n")
    trade_history = await system.trade_logger.get_trade_history(symbol="AAPL", limit=5)
    for trade in trade_history:
        print(f"  {trade['order_id']}: {trade['order_type']} {trade['quantity']}주 @ {trade['price']}")
    
    print("\n" + "="*60)
    print("데모 완료")
    print("="*60 + "\n")
    
    # 시스템 자원 해제 (aiosqlite 백그라운드 스레드 종료)
    await system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

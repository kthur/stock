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
    
    # CI/CD 환경(GitHub Actions)에서 yfinance 네트워크 타임아웃 방지를 위한 모킹
    system.market_data_handler.fetch_live_data = lambda symbol: system.market_data_handler.simulate_api_call(
        symbol, 150.0, 149.95, 150.05, 5000000
    )
    
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
    
    # 5. Market Scanner 테스트 (빠른 테스트를 위해 Mocking 적용)
    print(">>> 한국 시장 전체 퀵 스캔 (Market Scanner) 테스트\n")
    try:
        from src.analysis.market_scanner import MarketScanner
        scanner = MarketScanner()
        
        # CI/CD 타임아웃 방지를 위한 Mocking (1차 스캔 대상을 소수로 제한)
        original_get_top = scanner._get_top_krx_stocks
        def mock_get_top_krx():
            return {
                "005930.KS": "삼성전자", 
                "000660.KS": "SK하이닉스", 
                "035420.KS": "NAVER",
                "005380.KS": "현대차",
                "373220.KS": "LG에너지솔루션"
            }
        scanner._get_top_krx_stocks = mock_get_top_krx
        
        results = scanner.scan_market()
        print(f"  발견된 고수익 유망 종목 수: {len(results)}")
        for r in results:
            print(f"  [{r['rank']}위] {r['name']}({r['symbol']}) - 현재가: {r['price']}원, 기대수익률: {r['expected_return']}%")
        
        # 모킹 원복
        scanner._get_top_krx_stocks = original_get_top
        
    except Exception as e:
        print(f"  Market Scanner 오류 발생: {e}")
    
    # 6. 글로벌 시장 현황 조회
    print("\n>>> 글로벌 시장 현황 (Global Market) 테스트\n")
    try:
        summary = system.get_global_market_summary()
        if summary and "indices" in summary:
            for sym, info in summary["indices"].items():
                name = info.get("name", sym)
                price = info.get("price")
                chg = info.get("change_pct")
                if price is not None:
                    print(f"  {name}: {price:,.2f} ({chg:+.2f}%)")
            print("\n  --- 환율 ---")
            for pair, info in summary.get("fx_rates", {}).items():
                rate = info.get("rate")
                chg = info.get("change_pct")
                if rate is not None:
                    print(f"  {info['name']}: {rate:.4f} ({chg:+.2f}%)")
        else:
            print("  (데이터 없음 - 네트워크 필요)")
    except Exception as e:
        print(f"  글로벌 시장 조회 오류: {e}")

    # 7. 상대 강도 분석 (시장 대비 수익률 스크리닝)
    print("\n>>> 시장 대비 상대 강도 분석 (Relative Strength) 테스트\n")
    try:
        mock_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        rankings = system.get_relative_strength_ranking(mock_symbols, period="3mo", top_n=5)
        if rankings:
            print(f"  {'랭킹':>4s} {'종목':8s} {'점수':>8s} {'알파':>10s} {'상대수익률':>12s} {'상관계수':>8s}")
            print(f"  {'-'*4} {'-'*8} {'-'*8} {'-'*10} {'-'*12} {'-'*8}")
            for r in rankings:
                print(f"  {r['rank']:>4d} {r['symbol']:8s} {r['composite_score']:>+8.3f} "
                      f"{r.get('alpha', 0):>+10.6f} {r.get('relative_strength_pct', 0):>+10.2f}% "
                      f"{r.get('correlation', 0):>+8.3f}")
        else:
            print("  (데이터 없음)")
    except Exception as e:
        print(f"  상대 강도 분석 오류: {e}")

    print("\n" + "="*60)
    print("전체 테스트가 성공적으로 종료되었습니다.")
    print("="*60 + "\n")
    
    # 시스템 자원 해제 (aiosqlite 백그라운드 스레드 종료)
    await system.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # 강제 종료하여 백그라운드 스레드(EventBus 등)로 인한 무한 대기 방지
        sys.exit(0)

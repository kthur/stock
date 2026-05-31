"""Advanced Features Demo - 고급 기능 데모"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from trading_system import StockTradingSystem
from src.analysis import PriceBar
from datetime import datetime, timedelta


def demo_risk_management():
    """위험 관리 데모"""
    print("\n" + "="*60)
    print("위험 관리 (Risk Management) 데모")
    print("="*60 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    
    # 포지션 사이징 계산
    max_pos = system.risk_manager.calculate_max_position_size(150.0)
    print(f"최대 포지션 크기 (150달러): {max_pos} 주")
    
    # Stop Loss / Take Profit 확인
    has_sl = system.risk_manager.check_stop_loss("AAPL", 142.5, 150.0)
    print(f"Stop Loss 발동 (142.5 @ 150): {has_sl}")
    
    has_tp = system.risk_manager.check_take_profit("AAPL", 165.0, 150.0)
    print(f"Take Profit 발동 (165 @ 150): {has_tp}")
    
    # 위험 보고서
    risk_report = system.get_risk_report()
    print(f"\n위험 보고서:")
    for key, value in risk_report.items():
        print(f"  {key}: {value}")


def demo_backtesting():
    """백테스팅 데모"""
    print("\n" + "="*60)
    print("백테스팅 (Backtesting) 데모")
    print("="*60 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    
    # 샘플 가격 바 생성
    price_bars = []
    current_date = datetime.now() - timedelta(days=100)
    current_price = 100.0
    
    for i in range(100):
        bar = PriceBar(
            timestamp=current_date + timedelta(days=i),
            open=current_price,
            high=current_price * 1.02,
            low=current_price * 0.98,
            close=current_price * (0.99 + 0.02),
            volume=1000000
        )
        price_bars.append(bar)
        current_price = bar.close
    
    # 간단한 전략
    def simple_strategy(bars):
        if len(bars) < 20:
            return "HOLD"
        
        short_ma = sum(b.close for b in bars[-20:]) / 20
        long_ma = sum(b.close for b in bars[-50:]) / 50 if len(bars) >= 50 else short_ma
        
        if short_ma > long_ma:
            return "BUY"
        elif short_ma < long_ma:
            return "SELL"
        return "HOLD"
    
    # 백테스트 실행
    result = system.run_backtest("AAPL", price_bars, simple_strategy)
    
    print("백테스트 결과:")
    for key, value in result.items():
        print(f"  {key}: {value}")


def demo_advanced_statistics():
    """고급 통계 분석 데모"""
    print("\n" + "="*60)
    print("고급 통계 분석 (Advanced Statistics) 데모")
    print("="*60 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    
    # 샘플 포트폴리오 가치 곡선
    equity_curve = [1000000]
    for i in range(100):
        daily_return = (1 + (0.001 if i % 2 == 0 else -0.0005))
        equity_curve.append(equity_curve[-1] * daily_return)
    
    # 성과 지표 계산
    metrics = system.get_performance_metrics(equity_curve)
    
    print("성과 지표:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")


def demo_error_handling():
    """에러 처리 데모"""
    print("\n" + "="*60)
    print("에러 처리 (Error Handling) 데모")
    print("="*60 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    
    # 재시도 테스트
    def failing_func():
        raise Exception("Test error")
    
    try:
        system.error_handler.retry_with_exponential_backoff(failing_func)
    except Exception as e:
        print(f"재시도 실패: {str(e)}")
    
    # 에러 요약
    error_summary = system.get_error_summary()
    
    print("\n에러 요약:")
    for key, value in error_summary.items():
        print(f"  {key}: {value}")


def demo_kiwoom_integration():
    """키움증권 API 통합 데모"""
    print("\n" + "="*60)
    print("키움증권 API 통합 (Kiwoom Integration) 데모")
    print("="*60 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    
    # 증권사 연결
    connected = system.connect_broker("1234567890")
    print(f"증권사 연결: {connected}")
    
    # 연결 상태
    status = system.get_broker_status()
    print(f"\n증권사 상태:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 주문 접수
    if connected:
        order_id = system.broker.place_order("005930", 10, 50000.0, "매수")
        print(f"\n주문 ID: {order_id}")
        
        # 주문 상태
        order_status = system.broker.get_order_status(order_id)
        print(f"주문 상태: {order_status}")


def main():
    """메인 데모 실행"""
    
    print("\n" + "="*60)
    print("주식 트레이딩 시스템 - 고급 기능 데모")
    print("="*60 + "\n")
    
    # 1. 위험 관리
    demo_risk_management()
    
    # 2. 백테스팅
    demo_backtesting()
    
    # 3. 고급 통계
    demo_advanced_statistics()
    
    # 4. 에러 처리
    demo_error_handling()
    
    # 5. 키움증권 통합
    demo_kiwoom_integration()
    
    print("\n" + "="*60)
    print("모든 데모 완료")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

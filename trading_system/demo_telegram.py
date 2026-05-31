"""텔레그램 봇 데모 - 트레이딩 시스템 모니터링 및 제어"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from trading_system import StockTradingSystem


def demo_telegram_bot():
    """텔레그램 봇 데모"""
    print("\n" + "="*70)
    print("텔레그램 봇 - 트레이딩 시스템 모니터링 및 제어")
    print("="*70 + "\n")
    
    # 시스템 초기화
    system = StockTradingSystem(initial_cash=1000000)
    
    # 봇 시작
    print("🤖 텔레그램 봇 시작...\n")
    system.start_telegram_bot()
    
    # 테스트 사용자
    test_user_id = 123456789
    
    # 1. 시작 명령어
    print("📍 [사용자 입력] /start")
    response = system.process_telegram_message(test_user_id, "/start")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 2. 상태 조회
    print("📍 [사용자 입력] /status")
    response = system.process_telegram_message(test_user_id, "/status")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 3. 포트폴리오
    print("📍 [사용자 입력] /portfolio")
    response = system.process_telegram_message(test_user_id, "/portfolio")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 4. 증권사 현황
    print("📍 [사용자 입력] /brokers")
    response = system.process_telegram_message(test_user_id, "/brokers")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 5. 위험 관리
    print("📍 [사용자 입력] /risk")
    response = system.process_telegram_message(test_user_id, "/risk")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 6. 주식 분석
    print("📍 [사용자 입력] /analyze AAPL")
    response = system.process_telegram_message(test_user_id, "/analyze AAPL")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 7. 뉴스 조회
    print("📍 [사용자 입력] /news")
    response = system.process_telegram_message(test_user_id, "/news")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 8. 매수 주문
    print("📍 [사용자 입력] /buy AAPL 10 150")
    response = system.process_telegram_message(test_user_id, "/buy AAPL 10 150")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 9. 증권사 연결
    print("📍 [사용자 입력] /connect kiwoom 1234567890")
    response = system.process_telegram_message(test_user_id, "/connect kiwoom 1234567890")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 10. 도움말
    print("📍 [사용자 입력] /help")
    response = system.process_telegram_message(test_user_id, "/help")
    print(f"🤖 [봇 응답]\n{response}\n")
    
    # 봇 통계
    print("📊 봇 통계")
    print("="*70)
    stats = system.get_telegram_bot_stats()
    print(f"✅ 봇 상태: {'실행 중' if stats['is_running'] else '중지됨'}")
    print(f"👥 등록된 사용자: {stats['subscribed_users']}명")
    print(f"📝 총 명령어 수: {stats['total_commands']}개")
    print(f"\n최근 명령어:")
    for cmd in stats['recent_commands'][-5:]:
        print(f"  • {cmd['command']} (사용자: {cmd['user_id']})")
    
    # 알림 예시
    print("\n\n📢 알림 예시")
    print("="*70 + "\n")
    
    # 주문 접수
    notification = system.send_telegram_notification(
        test_user_id,
        "order_placed",
        {'symbol': 'AAPL', 'quantity': 10, 'price': 150.0}
    )
    print(f"주문 접수 알림: {notification}\n")
    
    # 손절매
    notification = system.send_telegram_notification(
        test_user_id,
        "stop_loss",
        {'symbol': 'MSFT', 'price': 300.0}
    )
    print(f"손절매 알림: {notification}\n")
    
    # 익절매
    notification = system.send_telegram_notification(
        test_user_id,
        "take_profit",
        {'symbol': 'GOOGL', 'price': 290.0}
    )
    print(f"익절매 알림: {notification}\n")
    
    # 일일 보고서
    print("\n📊 일일 거래 보고서")
    print("="*70 + "\n")
    report = system.get_telegram_daily_report(test_user_id)
    if report:
        print(report)
    
    # 봇 중지
    print("\n🛑 텔레그램 봇 중지...\n")
    system.stop_telegram_bot()


def demo_telegram_commands():
    """텔레그램 봇 명령어 예시"""
    print("\n" + "="*70)
    print("텔레그램 봇 명령어 완전 가이드")
    print("="*70 + "\n")
    
    system = StockTradingSystem(initial_cash=1000000)
    system.start_telegram_bot()
    
    test_user_id = 987654321
    
    commands = [
        ("상태 조회", [
            "/status - 현재 거래 상태",
            "/portfolio - 포트폴리오 조회",
            "/positions - 포지션 상세",
            "/orders - 주문 현황",
            "/brokers - 증권사 상태",
            "/risk - 위험 관리"
        ]),
        ("분석 및 정보", [
            "/analyze AAPL - AAPL 주식 분석",
            "/news - 시장 뉴스"
        ]),
        ("거래", [
            "/buy AAPL 10 150 - AAPL 10주를 150달러에 매수",
            "/sell MSFT 5 320 - MSFT 5주를 320달러에 매도",
            "/cancel ORD_123456789 - 주문 취소"
        ]),
        ("증권사 관리", [
            "/connect kiwoom 1234567890 - 키움증권 연결",
            "/connect daishin 0987654321 - 대신증권 연결",
            "/connect hanwha 5555555555 - 한투증권 연결"
        ])
    ]
    
    for category, cmd_list in commands:
        print(f"📌 {category}")
        print("-" * 70)
        for cmd in cmd_list:
            print(f"  {cmd}")
        print()
    
    system.stop_telegram_bot()


def main():
    """메인 데모 실행"""
    
    # 1. 텔레그램 봇 기본 데모
    demo_telegram_bot()
    
    # 2. 명령어 가이드
    demo_telegram_commands()
    
    print("\n" + "="*70)
    print("텔레그램 봇 데모 완료")
    print("="*70)
    print("\n💡 팁:")
    print("   1. TELEGRAM_BOT_TOKEN 환경변수를 설정하면 실제 봇이 작동합니다.")
    print("   2. 봇을 시작하려면: @BotFather로 새 봇을 만들고 토큰을 받으세요.")
    print("   3. 봇을 추가하려면: 텔레그램에서 봇을 검색해 /start를 입력하세요.\n")


if __name__ == "__main__":
    main()

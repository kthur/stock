"""Phase 5 데모 - 유명인 전략, AI 통합, 다중 증권사 API"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from trading_system import StockTradingSystem


def demo_famous_investor_strategies():
    """유명 투자자 전략 데모"""
    print("\n" + "="*70)
    print("유명 투자자 전략 (Famous Investor Strategies) 데모")
    print("="*70 + "\n")

    system = StockTradingSystem(initial_cash=1000000)

    # 샘플 주식 데이터
    sample_stocks = [
        {
            'symbol': 'AAPL',
            'company_name': 'Apple Inc.',
            'price': 150.0,
            'pe_ratio': 18.5,
            'pb_ratio': 28.0,
            'roe': 85.0,
            'debt_ratio': 25.0,
            'dividend_yield': 0.5,
            'earnings_growth': 12.0,
            'revenue_growth': 8.0,
            'market_cap': 2400000000000
        },
        {
            'symbol': 'MSFT',
            'company_name': 'Microsoft Corp.',
            'price': 320.0,
            'pe_ratio': 30.0,
            'pb_ratio': 12.0,
            'roe': 40.0,
            'debt_ratio': 15.0,
            'dividend_yield': 0.8,
            'earnings_growth': 20.0,
            'revenue_growth': 18.0,
            'market_cap': 2300000000000
        },
        {
            'symbol': 'GOOGL',
            'company_name': 'Alphabet Inc.',
            'price': 280.0,
            'pe_ratio': 22.0,
            'pb_ratio': 6.0,
            'roe': 28.0,
            'debt_ratio': 5.0,
            'dividend_yield': 0.0,
            'earnings_growth': 15.0,
            'revenue_growth': 12.0,
            'market_cap': 1800000000000
        }
    ]

    # 각 주식에 대한 유명 투자자 전략 분석
    for stock in sample_stocks:
        print(f"\n[{stock['symbol']}] {stock['company_name']}")
        print("-" * 50)

        opinions = system.get_famous_investor_signals(stock)

        for investor_type, signal in opinions.items():
            print(f"  {investor_type}:")
            print(f"    추천: {signal.recommendation}")
            print(f"    신뢰도: {signal.confidence:.0%}")
            for reason in signal.reasons[:2]:
                print(f"    - {reason}")
            print()

    # 합의 의견
    print("\n" + "="*50)
    print("합의 의견 (Consensus)")
    print("="*50 + "\n")

    consensus = system.get_investor_consensus(sample_stocks[0])
    print("AAPL 합의:")
    print(f"  종합 의견: {consensus['consensus']}")
    print(f"  매수 투자자: {consensus['buy_count']}명")
    print(f"  보유 투자자: {consensus['hold_count']}명")
    print(f"  매도 투자자: {consensus['sell_count']}명")
    print(f"  평균 신뢰도: {consensus['avg_confidence']:.0%}")

    # 상위 추천주
    print("\n" + "="*50)
    print("상위 추천주 TOP 3")
    print("="*50 + "\n")

    top_recommendations = system.get_top_recommendation_stocks(sample_stocks, top_n=3)
    for i, rec in enumerate(top_recommendations, 1):
        print(f"{i}. {rec['symbol']} ({rec['company_name']})")
        print(f"   가격: ${rec['price']:,.2f}")
        print(f"   종합 의견: {rec['consensus']}")
        print(f"   신뢰도: {rec['confidence']:.0%}")
        print(f"   매수 투자자: {rec['buy_count']}명\n")


def demo_ai_investment_opinion():
    """AI 투자 의견 데모"""
    print("\n" + "="*70)
    print("AI 투자 의견 (AI Investment Opinion) 데모")
    print("="*70 + "\n")

    system = StockTradingSystem(initial_cash=1000000)

    # 샘플 주식
    stock = {
        'symbol': 'TSLA',
        'price': 245.0,
        'pe_ratio': 65.0,
        'pb_ratio': 15.0,
        'roe': 25.0,
        'debt_ratio': 8.0,
        'dividend_yield': 0.0,
        'earnings_growth': 35.0,
        'revenue_growth': 28.0,
        'industry': '자동차'
    }

    # AI 의견
    print(f"[{stock['symbol']}] 주식에 대한 AI 분석\n")

    ai_opinion = system.get_ai_investment_opinion(stock)

    print(f"추천: {ai_opinion['recommendation']}")
    print(f"감정도: {ai_opinion['sentiment']}")
    print(f"신뢰도: {ai_opinion['confidence']:.0%}")
    print(f"목표 주가: ${ai_opinion['target_price']:,.2f}" if ai_opinion['target_price'] else "목표 주가: 미정")
    print("\n분석:")
    print(f"{ai_opinion['reasoning']}")

    if ai_opinion['risks']:
        print("\n리스크 요인:")
        for risk in ai_opinion['risks']:
            print(f"  - {risk}")

    if ai_opinion['opportunities']:
        print("\n기회 요인:")
        for opp in ai_opinion['opportunities']:
            print(f"  - {opp}")


def demo_ai_and_investor_consensus():
    """AI와 투자자 의견의 합의 데모"""
    print("\n" + "="*70)
    print("AI + 투자자 합의 의견 (AI & Investor Consensus) 데모")
    print("="*70 + "\n")

    system = StockTradingSystem(initial_cash=1000000)

    stock = {
        'symbol': 'NVDA',
        'price': 420.0,
        'pe_ratio': 55.0,
        'pb_ratio': 18.0,
        'roe': 45.0,
        'debt_ratio': 12.0,
        'dividend_yield': 0.1,
        'earnings_growth': 55.0,
        'revenue_growth': 50.0,
        'market_cap': 1050000000000
    }

    print(f"[{stock['symbol']}] NVDA - AI와 투자자 의견 분석\n")

    consensus = system.get_consensus_with_ai(stock)

    print(f"최종 합의: {consensus['consensus']}")
    print(f"매수 비율: {consensus['buy_ratio']:.0%}")
    print(f"가중 신뢰도: {consensus['weighted_confidence']:.0%}\n")

    # AI 의견
    ai_op = consensus['ai_opinion']
    print("AI 의견:")
    print(f"  추천: {ai_op.recommendation}")
    print(f"  감정도: {ai_op.sentiment.value}")
    print(f"  신뢰도: {ai_op.confidence:.0%}\n")

    # 투자자 의견
    print("투자자 의견:")
    for investor_type, opinion in consensus['investor_opinions'].items():
        print(f"  {investor_type}: {opinion.recommendation} ({opinion.confidence:.0%})")


def demo_multi_broker_management():
    """다중 증권사 관리 데모"""
    print("\n" + "="*70)
    print("다중 증권사 관리 (Multi-Broker Management) 데모")
    print("="*70 + "\n")

    system = StockTradingSystem(initial_cash=1000000)

    # 1. 증권사 연결
    print("[1] 증권사 연결\n")

    print("키움증권 연결...")
    connected = system.connect_to_broker("kiwoom", "1234567890")
    print(f"결과: {'성공' if connected else '실패'}\n")

    print("대신증권 연결...")
    connected = system.connect_to_broker("daishin", "0987654321")
    print(f"결과: {'성공' if connected else '실패'}\n")

    print("한투증권 연결...")
    connected = system.connect_to_broker("hanwha", "5555555555")
    print(f"결과: {'성공' if connected else '실패'}\n")

    # 2. 증권사 상태 확인
    print("[2] 모든 증권사 상태\n")

    broker_status = system.get_all_broker_status()
    for broker_name, status in broker_status.items():
        print(f"{broker_name}:")
        print(f"  연결 상태: {'연결됨' if status['is_connected'] else '미연결'}")
        print(f"  계좌: {status['account_number']}")
        print(f"  시뮬레이션: {'활성' if status['simulation_mode'] else '비활성'}")
        print(f"  활성: {'예' if status['is_active'] else '아니오'}\n")

    # 3. 증권사 전환
    print("[3] 증권사 전환\n")

    print("활성 증권사를 대신증권으로 전환...")
    switched = system.switch_broker("daishin")
    print(f"결과: {'성공' if switched else '실패'}\n")

    # 4. 주문 접수
    print("[4] 주문 접수\n")

    print("키움증권으로 AAPL 매수 주문...")
    order_id = system.place_order_with_broker("AAPL", 10, 150.0, "매수", "kiwoom")
    print(f"주문번호: {order_id}\n")

    print("대신증권으로 MSFT 매도 주문...")
    order_id = system.place_order_with_broker("MSFT", 5, 320.0, "매도", "daishin")
    print(f"주문번호: {order_id}\n")

    # 5. 계좌 정보
    print("[5] 각 증권사 계좌 정보\n")

    kiwoom_account = system.get_broker_account_info("kiwoom")
    print("키움증권 계좌:")
    print(f"  계좌번호: {kiwoom_account.get('account_number')}")
    print(f"  잔액: ${kiwoom_account.get('balance'):,.0f}\n")

    daishin_account = system.get_broker_account_info("daishin")
    print("대신증권 계좌:")
    print(f"  계좌번호: {daishin_account.get('account_number')}")
    print(f"  잔액: ${daishin_account.get('balance'):,.0f}\n")

    hanwha_account = system.get_broker_account_info("hanwha")
    print("한투증권 계좌:")
    print(f"  계좌번호: {hanwha_account.get('account_number')}")
    print(f"  잔액: ${hanwha_account.get('balance'):,.0f}\n")


def main():
    """메인 데모 실행"""

    print("\n" + "="*70)
    print("주식 트레이딩 시스템 - Phase 5 (유명인 전략, AI, 다중 증권사)")
    print("="*70)

    # 1. 유명 투자자 전략
    demo_famous_investor_strategies()

    # 2. AI 투자 의견
    demo_ai_investment_opinion()

    # 3. AI + 투자자 합의
    demo_ai_and_investor_consensus()

    # 4. 다중 증권사 관리
    demo_multi_broker_management()

    print("\n" + "="*70)
    print("모든 Phase 5 데모 완료")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

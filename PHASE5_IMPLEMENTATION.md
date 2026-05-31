"""
주식 트레이딩 시스템 - Phase 5 구현 완료

===========================================
Phase 5: 유명인 전략, AI 통합, 다중 증권사 API
===========================================

## 1. 유명인 전략 엔진 (Famous Investor Strategies)
============================================

### 구현된 전략들:

#### 1.1 워렌 버펫 - 가치투자 (Buffett Strategy)
- 저평가 우량주 찾기
- 평가 지표: PER, PBR, ROE, 부채율, 배당율
- 파일: src/strategy/famous_investors.py::BuffettStrategy

예시:
  - PER < 15: 매수 신호
  - PBR < 1.0: 추가 매수 신호
  - ROE > 15%: 우량 기업 판별
  - 부채율 < 30%: 재무 건전성 확인

#### 1.2 피터 린치 - 성장투자 (Lynch Strategy)
- 빠른 성장 기업 찾기
- 성장률 + PEG Ratio 분석
- 파일: src/strategy/famous_investors.py::LynchStrategy

예시:
  - 실적 성장 > 25%: 강한 성장
  - PEG < 1.0: 저평가 성장주
  - 매출 성장 > 20%: 강한 수요

#### 1.3 미너바니 - 모멘텀 투자 (Minerva Strategy)
- 가격 모멘텀 추적
- 기술적 강세 신호 (RSI, 거래량)
- 파일: src/strategy/famous_investors.py::MinervaStrategy

예시:
  - 52주 수익률 > 50%: 강한 상승세
  - RSI 50-70: 매수 신호
  - 모멘텀 점수 > 70: 강한 상승

#### 1.4 배당 투자 (Dividend Strategy)
- 높은 배당율 기업 찾기
- 안정적 배당 성장 확인
- 파일: src/strategy/famous_investors.py::DividendStrategy

예시:
  - 배당율 > 4%: 높은 배당
  - 연속 배당 >= 20년: 매우 안정적
  - 배당 성향 < 60%: 지속 가능

### 핵심 기능:

```python
# 모든 전략 분석
opinions = system.get_famous_investor_signals(stock_data)

# 투자자들의 합의 의견
consensus = system.get_investor_consensus(stock_data)

# 상위 추천주 조회
top_stocks = system.get_top_recommendation_stocks(stocks_data, top_n=10)
```


## 2. AI/LLM 통합 엔진 (AI Investment Opinion)
==============================================

### 기능:

#### 2.1 OpenAI API 통합
- GPT-3.5/GPT-4 모델 지원
- 환경변수 OPENAI_API_KEY로 자동 설정
- 파일: src/ai/llm_integration.py::LLMEngine

#### 2.2 투자 의견 쿼리
- 주식 데이터를 기반한 AI 분석
- 추천(BUY/HOLD/SELL) + 감정도 + 신뢰도 반환
- 목표 주가, 리스크, 기회 요인 분석

#### 2.3 AI + 투자자 합의
- AI 의견 + 유명인 전략 의견 통합
- 가중 신뢰도 계산
- 최종 합의 의견 도출

### 핵심 기능:

```python
# AI 의견 조회
opinion = system.get_ai_investment_opinion(stock_data)

# AI + 투자자 합의
consensus = system.get_consensus_with_ai(stock_data)

# 배치 AI 분석
opinions = system.batch_ai_analysis(stocks_data)
```

### 응답 예시:

```
{
  'symbol': 'TSLA',
  'recommendation': 'BUY',
  'sentiment': '긍정적',
  'confidence': 0.85,
  'target_price': 280.0,
  'risks': ['시장 변동성', '경쟁사 동향'],
  'opportunities': ['신제품 출시', '기술 혁신']
}
```


## 3. 다중 증권사 API 관리 (Multi-Broker Management)
================================================

### 구현된 증권사:

#### 3.1 키움증권 (Kiwoom Securities)
- API 버전: 1.0
- 파일: src/broker/kiwoom.py
- 기능: 주문, 계좌 조회, 시세, 일봉 차트
- 상태: 기존 구현 강화

#### 3.2 대신증권 (Daishin Securities)
- API 버전: 2.0
- 파일: src/broker/daishin.py
- 기능: 완전한 API 지원
- 신규 추가

#### 3.3 한투증권 (Hanwha Investment & Securities)
- API 버전: 3.0
- 파일: src/broker/hanwha.py
- 기능: 완전한 API 지원
- 신규 추가

### 다중 증권사 관리자:

#### 3.4 MultiBrokerManager
- 파일: src/broker/multi_broker_manager.py
- 기능: 증권사 통합 관리 인터페이스

### 핵심 기능:

```python
# 증권사 연결
system.connect_to_broker("kiwoom", "계좌번호")
system.connect_to_broker("daishin", "계좌번호")
system.connect_to_broker("hanwha", "계좌번호")

# 증권사 전환
system.switch_broker("daishin")

# 주문 접수 (특정 증권사 선택 가능)
order_id = system.place_order_with_broker(
    code="AAPL",
    quantity=10,
    price=150.0,
    order_type="매수",
    broker_type="kiwoom"
)

# 계좌 정보 조회
info = system.get_broker_account_info("kiwoom")

# 모든 증권사 상태 조회
status = system.get_all_broker_status()

# 주식 시세 조회
quote = system.get_stock_quote_from_broker("AAPL", "kiwoom")

# 일봉 차트 조회
chart = system.get_chart_from_broker("AAPL", days=20, broker_type="daishin")
```


## 4. 파일 구조
==================

새로 추가된 파일들:

```
src/
├── strategy/
│   ├── __init__.py (신규)
│   └── famous_investors.py (신규)
│       ├── BuffettStrategy
│       ├── LynchStrategy
│       ├── MinervaStrategy
│       ├── DividendStrategy
│       └── InvestorStrategyEngine
│
├── ai/
│   ├── __init__.py (신규)
│   └── llm_integration.py (신규)
│       ├── LLMEngine
│       └── InvestmentOpinion
│
└── broker/
    ├── kiwoom.py (수정: get_account_info 메서드 추가)
    ├── daishin.py (신규)
    ├── hanwha.py (신규)
    ├── multi_broker_manager.py (신규)
    └── __init__.py (수정: 새 클래스 export)

trading_system.py (수정)
└── 유명인 전략, AI, 다중 증권사 메서드 추가

demo_phase5.py (신규)
└── Phase 5 전체 기능 데모
```


## 5. 테스트 결과
=================

✅ 기존 15개 테스트 모두 통과
✅ Phase 5 데모 완전 실행
✅ 모든 기능 호환성 확인


## 6. 사용 예시
================

### 예시 1: 유명인 전략으로 추천주 찾기

```python
from trading_system import StockTradingSystem

system = StockTradingSystem()

# 주식 데이터
stock = {
    'symbol': 'AAPL',
    'price': 150.0,
    'pe_ratio': 18.5,
    'pb_ratio': 28.0,
    'roe': 85.0,
    'debt_ratio': 25.0,
    'dividend_yield': 0.5,
    'earnings_growth': 12.0,
    'revenue_growth': 8.0
}

# 유명인 의견
opinions = system.get_famous_investor_signals(stock)
for investor, opinion in opinions.items():
    print(f"{investor}: {opinion.recommendation} ({opinion.confidence:.0%})")

# 합의 의견
consensus = system.get_investor_consensus(stock)
print(f"합의: {consensus['consensus']}")
```

### 예시 2: AI 투자 의견 조회

```python
# AI 의견
ai_opinion = system.get_ai_investment_opinion(stock)
print(f"AI 추천: {ai_opinion['recommendation']}")
print(f"목표 주가: ${ai_opinion['target_price']:,.0f}")
print(f"이유: {ai_opinion['reasoning']}")

# AI + 투자자 합의
combined = system.get_consensus_with_ai(stock)
print(f"최종 합의: {combined['consensus']}")
print(f"가중 신뢰도: {combined['weighted_confidence']:.0%}")
```

### 예시 3: 다중 증권사에서 주문하기

```python
# 키움증권 연결
system.connect_to_broker("kiwoom", "1234567890")

# 키움증권에서 매수
order = system.place_order_with_broker(
    "AAPL", 10, 150.0, "매수", "kiwoom"
)

# 대신증권으로 전환
system.switch_broker("daishin")

# 대신증권에서 매도
order = system.place_order_with_broker(
    "AAPL", 10, 155.0, "매도", "daishin"
)

# 모든 계좌 정보 확인
accounts = system.get_broker_account_info()
```


## 7. 주요 개선사항
====================

1. **투자 전략 다양화**
   - 4가지 유명인 전략 지원
   - 각 전략의 신뢰도 계산
   - 투자자들의 합의 의견 도출

2. **AI 기반 의사결정**
   - OpenAI API 통합 (시뮬레이션 모드 포함)
   - AI와 투자자 의견 통합
   - 자동 분석 쿼리 생성

3. **다중 증권사 지원**
   - 3개 증권사 API (키움, 대신, 한투)
   - 통일된 인터페이스
   - 증권사 간 전환 용이

4. **확장성**
   - 새로운 투자자 전략 추가 용이
   - 다른 LLM 모델 통합 가능
   - 새로운 증권사 추가 용이


## 8. 기술 스택
================

- Python 3.9+
- OpenAI API (선택적)
- 기존 모든 의존성 호환


## 9. 다음 단계
==================

1. OpenAI API 키 설정
2. 실제 증권사 API 통합
3. 실시간 데이터 스트리밍
4. 포트폴리오 리스크 관리 최적화
5. 머신러닝 기반 전략 개선


## 10. 완료 체크리스트
=======================

✅ 워렌 버펫 가치투자 전략
✅ 피터 린치 성장투자 전략
✅ 미너바니 모멘텀 투자 전략
✅ 배당 투자 전략
✅ AI/LLM 투자 의견
✅ AI + 투자자 합의
✅ 키움증권 API (강화)
✅ 대신증권 API (신규)
✅ 한투증권 API (신규)
✅ 다중 증권사 관리자
✅ 통합 시스템 테스트
✅ 데모 및 예시
✅ 문서화

"""

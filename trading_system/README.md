# 주식 트레이딩 시스템 (Stock Trading System)

Mermaid 다이어그램의 주식 트레이딩 아키텍처를 Python으로 구현한 시스템입니다.

## 시스템 개요

```
외부 인터페이스 → 데이터 레이어 → 전략 엔진 → 주문 관리 → 증권사 API
              ↓          ↓           ↓         ↓
           저장소 (데이터베이스)
```

## 핵심 컴포넌트

### 1. 데이터 레이어 (Data Layer)
- **MarketDataHandler**: 실시간 시세 데이터 수신 및 관리
- **NLPEngine**: 뉴스 텍스트 분석 및 감정 점수 계산

### 2. 자산 관리 (Asset Management)
- **PortfolioManager**: 실시간 포트폴리오 가치 계산
- **AccountSyncAgent**: 증권사 계좌와 자동 동기화

### 3. 전략 엔진 (Strategy Engine)
- **HybridStrategyEngine**: 기술적 분석 + 감정 분석 통합
- **OptimizationEngine**: 슬리피지/손익 기반 파라미터 자동 튜닝

### 4. 주문 관리 (Order Management System)
- **OrderManagementSystem**: 주문 생성/제출/체결/취소 관리
- 미체결 주문 모니터링

### 5. 지속성 레이어 (Persistence Layer)
- **TradeLogger**: SQLite 기반 거래 로그 저장
- **AssetHistoryDB**: 일별 자산 추이 저장

## 디렉토리 구조

```
trading_system/
├── src/
│   ├── data_layer/
│   │   ├── __init__.py
│   │   ├── market_data_handler.py
│   │   └── nlp_engine.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── asset_management.py
│   │   ├── strategy_engine.py
│   │   └── order_management.py
│   └── persistence/
│       ├── __init__.py
│       └── database.py
├── tests/
├── trading_system.py      # 메인 통합 시스템
├── test_system.py         # 테스트 실행 파일
└── README.md
```

## 설치 및 사용

### 필수 환경
- Python 3.9+
- 추가 패키지 없음 (표준 라이브러리만 사용)

### 실행

```bash
# 프로젝트 디렉토리로 이동
cd trading_system

# 테스트 실행
python test_system.py
```

## 사용 예제

```python
from trading_system import StockTradingSystem

# 시스템 초기화 (100만원 초기 자본금)
system = StockTradingSystem(initial_cash=1000000)

# 하루 거래 시뮬레이션
system.simulate_trading_day(symbol="AAPL")

# 거래 상태 조회
status = system.get_trading_status()
print(status)

# 증권사 계좌 동기화
system.sync_with_broker(broker_cash=900000, broker_holdings={"AAPL": 10})

# 거래 이력 조회
history = system.trade_logger.get_trade_history(symbol="AAPL")
```

## 데이터 흐름

### 1. 시세 및 뉴스 흐름
```
증권사 API → MarketDataHandler → 전략 엔진
네이버 뉴스 → NLPEngine → 전략 엔진
```

### 2. 자산 동기화 흐름
```
증권사 API → AccountSyncAgent → PortfolioManager → 전략 엔진
              ↓
          AssetHistoryDB (스냅샷 저장)
```

### 3. 매매 실행 흐름
```
전략 엔진 → OrderManagementSystem → 증권사 API
           ↓
        TradeLogger (로그 저장)
```

### 4. 체결 응답 및 처리
```
증권사 API → OrderManagementSystem → PortfolioManager
           ↓
        TradeLogger
```

### 5. 피드백 및 최적화
```
TradeLogger → OptimizationEngine → HybridStrategyEngine (파라미터 조정)
```

## 주요 기능

### MarketDataHandler
- 실시간 시세 수신
- 구독자 패턴을 통한 이벤트 알림
- 시세 데이터 캐싱

### NLPEngine
- 간단한 키워드 기반 감정 분석
- -1.0 ~ 1.0 범위의 감정 점수
- 뉴스 데이터 저장 및 조회

### PortfolioManager
- 포지션 추적
- 현금 관리
- 포트폴리오 가치 계산
- 자산 히스토리 기록

### HybridStrategyEngine
- 기술적 분석 (스프레드 기반)
- 감정 분석 가중치
- 매수/매도/보유 신호 생성
- 신뢰도 점수 제공

### OrderManagementSystem
- 주문 생성/제출/체결/취소
- 미체결 주문 모니터링
- 부분 체결 처리

## 로깅

모든 주요 이벤트는 로깅됩니다:
- INFO: 중요한 이벤트
- DEBUG: 상세 정보
- WARNING: 경고 사항

## 성능 지표

- 승률 (Win Rate): 수익거래 / 전체거래
- 평균 슬리피지: 예정 가격과 실제 거래 가격의 차이

## 확장 가능성

다음과 같이 확장할 수 있습니다:

1. **실제 증권사 API 연동**
   - 키움증권, 한투, 이베스트 등 API 연동

2. **고급 NLP 모델**
   - BERT, GPT 기반 감정 분석
   - 핵심 키워드 추출

3. **머신러닝**
   - 가격 예측 모델
   - 이상 탐지

4. **웹 대시보드**
   - Flask/Django 기반 실시간 모니터링
   - 성과 분석 시각화

5. **위험 관리**
   - Stop Loss 자동 설정
   - Position Sizing 최적화

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트 환영합니다!

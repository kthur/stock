# 주식 트레이딩 시스템 (Stock Trading System)

Python으로 구현된 완전한 알고리즘 트레이딩 시스템입니다.

## 시스템 개요

```
외부 인터페이스 → 데이터 레이어 → 전략 엔진 → 주문 관리 → 증권사 API
               ↓          ↓           ↓         ↓
            저장소 (데이터베이스)
```

## 핵심 컴포넌트

### 1. 데이터 레이어 (Data Layer)
- **MarketDataHandler**: 실시간 시세 데이터 수신 및 관리, 과거 데이터 조회
- **NLPEngine**: 뉴스 텍스트 분석 및 감정 점수 계산 (-1.0 ~ 1.0)
- **AlternativeDataClient**: VIX, 공포/탐욕 지수, 시장 레짐 탐지
- **DarkPoolTracker**: 다크풀 활동 및 고래 움직임 추적

### 2. 자산 관리 (Asset Management)
- **PortfolioManager**: 실시간 포트폴리오 가치 계산, 포지션/현금 관리
- **AccountSyncAgent**: 증권사 계좌와 자동 동기화
- **QuantumPortfolioOptimizer**: 평균-분산 최적화, 리스크 패리티

### 3. 전략 엔진 (Strategy Engine)
- **HybridStrategyEngine**: 기술적 분석 + 감정 분석 + ML/RL + 다크풀 + LLM 통합
- **OptimizationEngine**: 슬리피지/손익 기반 파라미터 자동 튜닝
- **InvestorStrategyEngine**: 워렌 버핏, 피터 린치, 찰리 멍거 등 유명 투자자 전략 구현

### 4. 주문 관리 (Order Management System)
- **OrderManagementSystem**: 주문 생성/제출/체결/취소, 미체결 모니터링
- **자동 손절/익절 주문**: 진입 시 Stop Loss / Take Profit 주문 자동 생성
- **실시간 발동 체결**: 시장 데이터 업데이트 시 손절/익절 주문 자동 감지 및 체결

### 5. 위험 관리 (Risk Management)
- **RiskManager**: 동적 포지션 사이징 (Kelly Criterion), VaR/CVaR, Drawdown 모니터링
- **상관관계 리스크**: 포트폴리오 내 고상관 종목 집중도 감지
- **변동성 스케일링**: VIX 기반 포지션 크기 자동 조정

### 6. 백테스팅 & 분석 (Backtesting & Analysis)
- **BacktestEngine**: 과거 데이터 기반 전략 검증, 수수료/슬리피지/시장충격 모델링
- **AdvancedStatistics**: Sharpe/Sortino/Calmar Ratio, VaR, Hurst Exponent
- **파라미터 최적화**: 그리드 서치 기반 최적 파라미터 탐색

### 7. 웹 대시보드 & 알림
- **WebDashboard**: FastAPI 기반 실시간 모니터링, WebSocket 실시간 푸시
- **TelegramBotEngine**: 거래 알림, 포트폴리오 조회, 명령어 기반 제어
- **RESTful API**: `/api/portfolio`, `/api/performance`, `/api/orders`, `/api/health`

### 8. 증권사 연동 (Multi-Broker)
- **7개 증권사 지원**: 키움, 대신, 한화, 한국투자, 미래에셋, NH, LS
- **MultiBrokerManager**: 통합 인터페이스, 동시 연결 및 전환 지원

## 디렉토리 구조

```
trading_system/
├── src/
│   ├── data_layer/          # 시장 데이터 & NLP
│   ├── core/                # 자산관리, 전략, 주문, 위험관리
│   ├── persistence/         # SQLite 데이터 저장소
│   ├── risk/                # 위험 관리
│   ├── analysis/            # 백테스트, 통계, ML
│   ├── web/                 # 웹 대시보드
│   ├── utils/               # 유틸리티 (에러핸들링, 이벤트버스)
│   ├── broker/              # 7개 증권사 연동
│   ├── strategy/            # 유명 투자자 전략
│   ├── ai/                  # LLM/ML 엔진
│   └── telegram_bot/        # 텔레그램 봇
├── tests/                   # 유닛 테스트 (15개)
├── trading_system.py        # 메인 통합 시스템
├── test_system.py           # 데모 실행 파일
├── README.md                # 이 파일
├── IMPLEMENTATION_GUIDE.md  # 구현 가이드
├── ADVANCED_FEATURES.md     # 고급 기능 상세
├── ALGORITHMS.md            # 알고리즘 상세 문서
└── requirements.txt
```

## 설치 및 사용

### 필수 환경
- Python 3.10+
- `pip install -r requirements.txt`

### 실행

```bash
cd trading_system

# 테스트 실행
python -m unittest tests.test_system -v

# 데모 실행
python test_system.py
```

### 사용 예제

```python
from trading_system import StockTradingSystem

# 시스템 초기화 (100만원 초기 자본금)
system = StockTradingSystem(initial_cash=1000000)

# 하루 거래 시뮬레이션
await system.simulate_trading_day(symbol="AAPL")

# 거래 상태 조회
status = system.get_trading_status()
print(f"현금: {status['cash']:,}")
print(f"포지션: {status['positions']}")

# 위험 리포트
risk_report = system.get_risk_report()
print(f"드로다운: {risk_report['drawdown']}")
print(f"리스크 레벨: {risk_report['risk_level']}")

# 백테스트
from src.analysis import PriceBar
price_bars = [...]  # PriceBar 객체 리스트
result = system.run_backtest("AAPL", price_bars, my_strategy)
```

## 데이터 흐름

### 1. 시세 및 뉴스 흐름
```
증권사 API → MarketDataHandler ──┐
네이버 뉴스 → NLPEngine ─────────┤  → HybridStrategyEngine → 매매 신호
AlternativeDataClient → 시장레짐 ──┘
```

### 2. 자산 동기화 흐름
```
증권사 API → AccountSyncAgent → PortfolioManager
                      │
                      └──→ AssetHistoryDB (스냅샷 저장)
```

### 3. 매매 실행 흐름 (자동 손절/익절 포함)
```
전략 엔진 → OrderManagementSystem → 진입 주문
                    ↓
            Stop Loss 주문 자동 생성
            Take Profit 주문 자동 생성
                    ↓
            증권사 API → 체결 → PortfolioManager
                    ↓
            TradeLogger (로그 저장)
```

### 4. 실시간 손절/익절 체결
```
시장 데이터 업데이트 → _on_market_data 콜백
                    → check_and_trigger_stop_orders()
                    → 발동된 주문 즉시 시장가 체결
                    → 포트폴리오 업데이트 + 텔레그램 알림
```

### 5. 피드백 및 최적화
```
TradeLogger → OptimizationEngine → HybridStrategyEngine (파라미터 조정)
```

## 주요 기능

### 자동 손절/익절 시스템
- **진입 시 자동 생성**: 매수/매도 주문 체결 시 Stop Loss / Take Profit 주문 자동 생성
- **비율 기반**: 설정된 비율(기본 5% 손절, 10% 익절) 기준 자동 계산
- **실시간 감시**: 시장 데이터 업데이트마다 발동 조건 자동 확인
- **즉시 체결**: 발동 시 시장가로 즉시 체결, 포트폴리오 즉시 반영
- **텔레그램 알림**: 발동 시 실시간 알림 전송

### 위험 관리
- **Kelly Criterion**: 승률/손익비 기반 최적 포지션 사이징
- **ATR 기반 손절/익절**: 변동성(ATR) 적응형 레벨
- **VIX 스케일링**: 고변동성 시 포지션 자동 축소 (VIX 40+ = 0.25x)
- **상관관계 리스크**: 고상관 종목 집중도 감지 → 리스크 레벨 상향
- **Drawdown 제한**: 최대 허용 드로다운 초과 시 포지션 축소

### 백테스팅
- **현실적 비용 모델**: 수수료(0.1%) + 슬리피지(0.1%) + 시장충격(0.05%)
- **다양한 전략**: MA, RSI, MACD, 볼린저밴드, 유명인 전략, ML 앙상블
- **파라미터 최적화**: 그리드 서치 + 교차검증

## 로깅

모든 주요 이벤트는 로깅됩니다:
- INFO: 시스템 초기화, 주문 체결, 손절/익절 발동
- DEBUG: 시세 업데이트, 데이터 캐싱
- WARNING: 미체결 주문, 고슬리피지, 손절 발동
- ERROR: 주문 실패, API 오류

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트 환영합니다!
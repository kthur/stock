# 주식 트레이딩 시스템 - 구현 가이드

> **상태**: Phase 1-7 통합 완료
> **테스트**: 315개 중 313개 통과, 2개 스킵 · **린트**: ruff 0 오류

본 문서는 `D:\Finance\code\stock\trading_system\docs\` 및 루트 디렉터리에 실제로 구현된 시스템의 동작 방식을 설명합니다. 문서의 모든 항목은 코드를 기준으로 검증되었으며, 향후 동작이 변경되면 본 문서도 함께 갱신해야 합니다.

## 1. 시스템 개요

이 시스템은 **이벤트 버스(EventBus) + 의존성 주입(Factory + DI) + 전략/실행 분리** 구조의 알고리즘 트레이딩 플랫폼입니다.

### 1.1 핵심 흐름

```
                ┌──────────── 외부 인터페이스 ────────────┐
                │                                           │
                │  yfinance 시세 / 네이버 뉴스 / VIX / SPX  │
                │  yfinance 공포·탐욕 / KRX 종목 스크리너   │
                └──────────┬────────────────────────────────┘
                           ▼
        ┌──────────────── 데이터 레이어 (data_layer/) ────────────────┐
        │  MarketDataHandler  · NLPEngine  · AlternativeDataClient    │
        │  GlobalMarketClient · RelativeStrengthAnalyzer              │
        └──────────────────┬───────────────────────────────────────────┘
                           │ event_bus.publish("market_data" / "news_sentiment")
                           ▼
        ┌──────────────── 전략 엔진 (core/strategy_engine.py) ──────────────┐
        │  HybridStrategyEngine (9-시그널 가중합, 동적 가중치 적응)        │
        │  ├─ 기술 + 감정 + ML + RL + DarkPool + LLM                      │
        │  ├─ GlobalMarket + CashRatio + Macro (9개 신호)                │
        │  ├─ Signal Consensus Scoring (합의도 기반 증폭)                  │
        │  ├─ Regime-based Full Weight Adjustment (ADX + BB Width)        │
        │  └─ 15-거래 윈도우 적응형 가중치 (HybridStrategyEngine)          │
        │  OptimizationEngine (슬리피지/손익 + Performance Attribution)    │
        │  InvestorStrategyEngine (Buffett/Lynch/Minerva/Dividend)        │
        └──────────────────┬──────────────────────────────────────────────┘
                           │ event_bus.publish("strategy_signal")
                           ▼
        ┌──────────────── 주문 관리 (core/order_management.py) ────────────┐
        │  OrderManagementSystem (OrderType 5종)                          │
        │  ├─ BUY / SELL                                                  │
        │  ├─ STOP_LOSS / TAKE_PROFIT (자동 생성 + 자동 체결)              │
        │  ├─ Trailing Stop (가격 상승 시 SL 상향 조정)                     │
        │  └─ Partial Take-Profit (ATR 기반 3-티어 분할 익절)             │
        └──────────────────┬──────────────────────────────────────────────┘
                           ▼
        ┌──────────────── 위험 관리 (risk/risk_manager.py) ──────────────────┐
        │  Kelly Criterion / VIX 스케일링 / ATR 손절 / VaR/CVaR             │
        │  Drawdown 모니터링 / 상관관계 리스크 / Volatility Targeting       │
        │  Risk Parity (correlation-adjusted limits)                       │
        └──────────────────┬──────────────────────────────────────────────┘
                           ▼
        ┌──────────────── 주문 사이징 파이프라인 (순서대로 적용) ────────────┐
        │  1. Kelly Criterion                                               │
        │  2. Conservative Ramp (초기 30% -> 10건 후 100% 점진 확대)        │
        │  3. Volatility Targeting (목표 연변동성 15%로 스케일)              │
        │  4. Confidence-based Sizing (신뢰도 스케일링)                     │
        │  5. Crisis Cash (위기 시 자산 보존)                               │
        │  6. Macro Score (거시 환경 기반 베팅 축소)                        │
        │  7. Earnings Guard (실적 발표 5일 전 50% 축소)                    │
        │  8. Information Ratio (IR기반 가중 조정)                          │
        │  9. Market Impact (일일 거래량 >5%면 축소)                        │
        └───────────────────────────────────────────────────────────────────┘
                           ▼
        ┌──────────────── 증권사 연동 (broker/) ──────────────────────────────┐
        │  MultiBrokerManager  →  7개 증권사 (Kiwoom/Daishin/Hanwha/       │
        │  KoreaInvestment/MiraeAsset/NH/LS), mock_trading 모드 기동        │
        └──────────────────┬───────────────────────────────────────────────┘
                           ▼
        ┌──────────────── 저장 / 알림 ───────────────────────────────────────┐
        │  TradeLogger (aiosqlite) / AssetHistoryDB / AIPredictionDB       │
        │  TelegramBotEngine (18+ 명령어) / Plotly Dash 대시보드            │
        │  Trade Journal (거래 내역 구조화 저장) / State Auto-Save         │
        └──────────────────────────────────────────────────────────────────┘
```

---

## 2. 시작하기

### 2.1 의존성 설치

```bash
cd D:\Finance\code\stock\trading_system
pip install -r requirements.txt
```

### 2.2 테스트 실행

```bash
# 전체 315개 테스트 실행
.venv\Scripts\python -m pytest tests/ -v
```

### 2.3 데모 실행

```bash
python test_system.py
```

### 2.4 데스크톱 대시보드 실행

```bash
python run_dashboard.py
# http://127.0.0.1:8050 접속
```

### 2.5 텔레그램 봇 실행

```bash
python telegram_bot_runner.py
```

---

## 3. 핵심 컴포넌트 사용법

### 3.1 시스템 부트스트랩

```python
from trading_system import StockTradingSystem
import asyncio

# 1) 기본 초기화 (1,000,000원)
system = StockTradingSystem(initial_cash=1_000_000)

# 2) 커스텀 컴포넌트 주입
from src.core.factory import SystemFactory
from src.utils import EventBus
bus = EventBus()
components = SystemFactory.create_default_components(1_000_000, bus)
components['dashboard'] = None  # 대시보드 미사용
system = StockTradingSystem(components=components, event_bus=bus)
```

### 3.2 시뮬레이션 및 모의투자 동기화

```python
# 단일 종목 하루 시뮬레이션
await system.simulate_trading_day(symbol="AAPL")

# 브로커 연동 및 잔고 동기화
system.sync_with_broker_api()
```

### 3.3 LLM 제공자별 설정 (DeepSeek 포함)

`.env` 파일에 다음과 같이 API를 연동하여 사용할 수 있습니다:

```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-chat # 또는 deepseek-reasoner (R1)
```

어댑터 파이프라인(`src/ai/llm_integration.py`)에서 해당 설정을 자동으로 읽어 API 호출을 대리하고, 결과를 구조화된 JSON 객체로 파싱합니다.

---

## 4. 포지션 사이징 파이프라인

주문 생성 시 9단계 파이프라인을 순차적으로 거치며 수량이 확정됩니다:

1. **Kelly Criterion**: 백테스트 승률과 평균 손익비를 결합한 이론적 최적 크기
2. **Conservative Ramp**: 초기 트레이딩 10건 동안은 포지션을 30%로 억제
3. **Volatility Targeting**: 목표 연변동성 15%를 넘지 않도록 변동성 비례 축소/확대
4. **Confidence**: 매매 신호 신뢰도 가중치 반영
5. **Crisis Cash**: 위기 발생 시 현금을 다량 확보하도록 강제 차단
6. **Macro Score**: 거시 위험 지표 점수가 낮을 경우 베팅 축소
7. **Earnings Guard**: 실적 발표일 전후 5일 이내 포지션 크기 50% 축소
8. **Information Ratio**: 성과 지표가 우수한 구간에서 비중 확대
9. **Market Impact**: 5% 이상의 대형 주문 시 슬리피지 방지를 위해 비례 제한

---

## 5. 자동 손절/익절 + 트레일링 스탑

- **ATR 손절/익절**: 포지션 진입 시 ATR의 2배 손절(SL), ATR의 1.5배/3배/5배로 구성된 3단계 부분 익절(TP) 주문을 자동으로 생성합니다.
- **트레일링 스탑**: 매 분봉 시세 업데이트 주기마다 고가 워터마크를 갱신하고, 기존 등록된 손절 주문의 트리거 가격을 점진적으로 상향 갱신합니다.
- **포트폴리오 손절**: 전체 계좌의 누적 드로다운이 20%를 초과하는 즉시 모든 오픈 포지션을 강제 청산하고 신규 매수를 전면 동결합니다.

---

## 6. 테스트 결과 (315개 테스트)

### 6.1 테스트 상세 요약

- **Happy Path 테스트**: 주요 엔진들(전략, 리스크, 주문)의 핵심적인 매매 시나리오 커버
- **코너 케이스/Adversarial 테스트**: 데이터 누락, Extreme Volatility, API 타임아웃 상황 검증
- **모의 투자 통합 테스트**: Mock Connector를 활용해 주문 체결 폴링 상태 및 잔고 동기화 흐름 검사 완료

```bash
# 전체 테스트 실행
.venv\Scripts\python -m pytest tests/ -v
# 결과: 313 passed, 2 skipped, 6 warnings in 240s
```

---

## 7. 디렉터리 구조

```
trading_system/
├── docs/                      # 시스템 관련 문서 보관 폴더
│   ├── ADVANCED_FEATURES.md   # 고급 기능 상세
│   ├── ALGORITHMS.md          # 알고리즘 상세
│   ├── IMPLEMENTATION_GUIDE.md# 본 문서
│   ├── ORIGINAL_REQUEST.md    # 원래 요구사항
│   ├── PHASE7_IMPLEMENTATION_PLAN.md
│   ├── PROJECT.md             # 프로젝트 개요 및 로드맵
│   ├── TEST_INFRA.md          # 테스트 인프라 정의
│   └── TEST_READY.md          # 테스트 준비 요약
├── src/                       # 소스 코드 디렉터리
│   ├── data_layer/            # 데이터 수집, HMM 레짐 및 NLP
│   ├── core/                  # 전략 엔진, 주문관리, 의존성 팩토리
│   ├── risk/                  # RiskManager (Kelly, ATR, Vol Target)
│   ├── analysis/              # ML 앙상블, TPE 최적화기, 백테스터
│   ├── broker/                # 7개 증권사 연동 프로토콜
│   ├── ai/                    # DeepSeek/OpenAI/Gemini 어댑터, RL
│   ├── persistence/           # SQLite DB 연동
│   ├── utils/                 # EventBus, 기술지표, PDF 리포트
│   ├── web/                   # Plotly Dash 대시보드
│   └── telegram_bot/          # 텔레그램 연동 봇
├── tests/                     # 테스트 스위트 (315개)
├── trading_system.py          # 메인 통합 시스템 파일
├── requirements.txt           # 의존 라이브러리 목록
└── pyproject.toml             # 빌드 및 ruff/pytest 설정
```

---

**마지막 업데이트**: 2026-06-11

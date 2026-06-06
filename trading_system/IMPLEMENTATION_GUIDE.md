# 주식 트레이딩 시스템 - 구현 가이드

> **상태**: Phase 1-5 + Phase 3 통합 완료 · **테스트**: 19/19 통과 · **린트**: ruff 0 / mypy 0 오류

본 문서는 `D:\Finance\code\stock\trading_system\` 디렉터리에 실제로 구현된 시스템의
동작 방식을 설명합니다. 문서의 모든 항목은 코드를 기준으로 검증되었으며, 향후 동작이
변경되면 본 문서도 함께 갱신해야 합니다.

## 1. 시스템 개요

이 시스템은 **이벤트 버스(EventBus) + 의존성 주입(Factory + DI) + 전략/실행 분리** 구조의
알고리즘 트레이딩 플랫폼입니다.

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
       │  DarkPoolTracker (중립값)                                    │
       └──────────────────┬───────────────────────────────────────────┘
                          │ event_bus.publish("market_data" / "news_sentiment")
                          ▼
       ┌──────────────── 전략 엔진 (core/strategy_engine.py) ─────────────┐
       │  HybridStrategyEngine (5-시그널 가중합, 동적 가중치 적응)        │
       │  ├─ 기술(RSI/MACD/MA) + 감정 + RL/ML + DarkPool + LLM          │
       │  └─ 50-거래 윈도우 적응형 가중치 (HybridStrategyEngine:296)     │
       │  OptimizationEngine (HybridStrategyEngine:353, 슬리피지/손익)   │
       │  InvestorStrategyEngine (Buffett/Lynch/Minerva/Dividend, 451줄)│
       └──────────────────┬──────────────────────────────────────────────┘
                          │ event_bus.publish("strategy_signal")
                          ▼
       ┌──────────────── 주문 관리 (core/order_management.py) ────────────┐
       │  OrderManagementSystem (OrderType 5종)                          │
       │  ├─ BUY / SELL                                                  │
       │  └─ STOP_LOSS / TAKE_PROFIT (자동 생성 + 자동 체결)              │
       └──────────────────┬──────────────────────────────────────────────┘
                          ▼
       ┌──────────────── 위험 관리 (risk/risk_manager.py) ─────────────────┐
       │  Kelly Criterion / VIX 스케일링 / 상관관계 리스크 / ATR 손절     │
       │  calculate_position_sizing  · _volatility_scalar                │
       └──────────────────┬──────────────────────────────────────────────┘
                          ▼
       ┌──────────────── 증권사 연동 (broker/) ─────────────────────────────┐
       │  MultiBrokerManager  →  7개 증권사 (Kiwoom/Daishin/Hanwha/      │
       │  KoreaInvestment/MiraeAsset/NH/LS), simulation_mode 기본        │
       └──────────────────┬──────────────────────────────────────────────┘
                          ▼
       ┌──────────────── 저장 / 알림 ──────────────────────────────────────┐
       │  TradeLogger (aiosqlite) / AssetHistoryDB / AIPredictionDB       │
       │  TelegramBotEngine (574줄, 16+ 명령어) / WebDashboard (3258줄)   │
       └──────────────────────────────────────────────────────────────────┘
```

### 1.2 패키지 구성 (47 모듈)

| 패키지 | 파일 수 | 책임 |
|--------|--------|------|
| `src/data_layer/` | 4 | 시세, 뉴스, 시장 레짐, 다크풀(중립) |
| `src/core/` | 6 | 자산관리, 전략, 주문, 통계적 차익거래, HFT(Mock), 팩토리 |
| `src/risk/` | 1 | Kelly/VaR/CVaR/드로다운/상관관계 |
| `src/analysis/` | 6 | 백테스트, 통계, ML, RL, 양자(클래식)최적화, 마켓 스캐너 |
| `src/broker/` | 11 | 7개 증권사 커넥터 + MultiBrokerManager + 프로토콜 |
| `src/strategy/` | 3 | 유명 투자자 전략 + 자산 배분 |
| `src/ai/` | 5 | LLM/OpenAI·Gemini 통합, DQN RL, 어닝 분석, 감정 |
| `src/persistence/` | 1 | aiosqlite 비동기 DB 3종 |
| `src/utils/` | 8 | EventBus, ErrorHandler, Notifier, PDF/Text 리포트 |
| `src/web/` | 1 | FastAPI 대시보드 + WebSocket |
| `src/telegram_bot/` | 2 | 텔레그램 봇 + 미니앱 |
| 루트 | 5 | `trading_system.py` 통합 + demo/test 스크립트 |

## 2. 시작하기

### 2.1 의존성 설치

```bash
cd D:\Finance\code\stock\trading_system
pip install -r requirements.txt
```

### 2.2 테스트 실행

```bash
# 핵심 15개 유닛 테스트
python -m unittest tests.test_system -v

# Phase 3 통합 테스트 4개 추가 (총 19)
python -m unittest discover -s tests -p "test_*.py"

# pytest 기반 (SB3 설치 시 1개 추가, 미설치 시 자동 스킵)
python -m pytest tests/ -v
```

### 2.3 데모 실행

```bash
python test_system.py
```

### 2.4 데스크톱 대시보드 실행

```bash
python run_dashboard.py
# http://127.0.0.1:5000 접속
```

### 2.5 텔레그램 봇 실행

```bash
# TELEGRAM_BOT_TOKEN 환경변수가 없으면 시뮬레이션 모드로 동작
python telegram_bot_runner.py
```

## 3. 핵심 컴포넌트 사용법

### 3.1 시스템 부트스트랩

```python
from trading_system import StockTradingSystem
import asyncio

# 1) 기본 초기화 (1,000,000원)
system = StockTradingSystem(initial_cash=1_000_000)

# 2) 커스텀 컴포넌트 주입 (테스트·모의용)
from src.core.factory import SystemFactory
from src.utils import EventBus
bus = EventBus()
components = SystemFactory.create_default_components(1_000_000, bus)
components['dashboard'] = None  # 대시보드 미사용
system = StockTradingSystem(components=components, event_bus=bus)
```

### 3.2 시뮬레이션 실행

```python
# 단일 종목 하루 시뮬레이션
await system.simulate_trading_day(symbol="AAPL")

# 상태 조회
status = system.get_trading_status()
# status = {
#   "cash": 850000.0,
#   "positions": {"AAPL": {"quantity": 10, "avg_price": 150.0, ...}},
#   "open_orders": 2,
#   "total_trades": 3,
#   "portfolio_value": 870000.0
# }
```

### 3.3 전략 직접 호출

```python
from src.core import HybridStrategyEngine, TradeSignal

engine = HybridStrategyEngine()
result = engine.analyze(
    symbol="005930",
    market_data={"price": 71000, "bid": 70950, "ask": 71050, "volume": 1_200_000},
    news_sentiment=0.6,
    price_bars=None,  # None이면 sentiment+price+volume만 사용
)
# result.signal  : TradeSignal.BUY / SELL / HOLD
# result.confidence : 0.0 ~ 1.0
# result.signals  : dict (component별 점수)
```

### 3.4 주문 + 자동 손절

```python
from src.core import OrderType

# 내부 호출 (자동 SL/TP 포함): _create_and_submit_order()
# 진입가 70,000원 → 손절 66,500원(-5%) / 익절 77,000원(+10%) 자동 생성
await system._create_and_submit_order("005930", OrderType.BUY, 70_000)
```

### 3.5 백테스트

```python
from src.analysis import BacktestEngine
from datetime import datetime, timedelta

engine = BacktestEngine(initial_capital=1_000_000, fee_pct=0.001,
                        slippage_pct=0.001, market_impact_pct=0.0005)

bars = system.market_data_handler.fetch_historical_data("005930", period="1y")
# bars: List[PriceBar] (open/high/low/close/volume/datetime)

def strategy_func(bars):
    if len(bars) < 2:
        return "HOLD"
    return "BUY" if bars[-1].close > bars[-2].close else "HOLD"

result = engine.run_backtest("005930", bars, strategy_func)
# result: BacktestResult (total_return, sharpe, max_drawdown, trades, ...)
```

### 3.6 리밸런싱

```python
target = {"005930": 0.4, "000660": 0.3, "035420": 0.3}
current = {"005930": 50, "000660": 30, "035420": 20}
prices = {"005930": 70000, "000660": 130000, "035420": 200000}

plan = system.portfolio.compute_rebalance_plan(target, current, prices)
# plan: {symbol: (action, quantity_diff, est_cash_diff), ...}
cash_needed = system.portfolio.estimate_rebalance_cash_needed(plan, prices)
```

## 4. 자동 손절/익절 시스템 (Stop Loss / Take Profit)

> 이 기능은 본 PR에서 새로 구현되었습니다.

### 4.1 라이프사이클

```
진입 주문 체결 → _create_and_submit_order() → 자동 SL+TP 주문 생성
                                          ↓
시장 데이터 도착 → _on_market_data() → check_and_trigger_stop_orders()
                                          ↓
                              발동 조건 충족 → SUBMITTED
                                          ↓
                              _execute_stop_order() → 시장가 체결
                                          ↓
                              포트폴리오 reduce_position() + 텔레그램 알림
```

### 4.2 핵심 구현 위치

| 동작 | 파일:라인 | 설명 |
|------|----------|------|
| 주문 타입 정의 | `order_management.py:19-20` | `OrderType.STOP_LOSS`, `OrderType.TAKE_PROFIT` |
| 트리거 필드 | `order_management.py:46` | `Order.trigger_price` |
| 손절 주문 생성 | `order_management.py:176-189` | `create_stop_loss_order()` |
| 익절 주문 생성 | `order_management.py:191-204` | `create_take_profit_order()` |
| 발동 검사 | `order_management.py:206-234` | `check_and_trigger_stop_orders()` |
| 목록 조회 | `order_management.py:236-241` | `get_stop_orders()` |
| 일괄 취소 | `order_management.py:243-255` | `cancel_stop_orders()` |
| 진입 시 자동 생성 | `trading_system.py:255-275` | `_create_and_submit_order()` (매수/매도 분기) |
| 시장가 체결 처리 | `trading_system.py:142-178` | `_execute_stop_order()` |

### 4.3 매수/매도별 트리거 방향

| 포지션 | 손절 트리거 | 익절 트리거 |
|--------|------------|------------|
| BUY | `current_price ≤ entry × (1 - stop_loss_pct)` | `current_price ≥ entry × (1 + take_profit_pct)` |
| SELL (숏) | `current_price ≥ entry × (1 + stop_loss_pct)` | `current_price ≤ entry × (1 - take_profit_pct)` |

기본 비율: `RiskManager.default_stop_loss_pct = 0.05`, `default_take_profit_pct = 0.10`.
변동성 기반 적응형 손절은 `RiskManager.calculate_atr_based_stop()` (line 75)에서 별도 제공되며
향후 `_create_and_submit_order`에 통합될 예정입니다.

## 5. 데이터 흐름 상세

### 5.1 시세 → 신호
```
yfinance API
  └─ MarketDataHandler._fetch_yf_with_retry()  ← tenacity 재시도 + CircuitBreaker
       └─ publish_market_data()
            └─ event_bus "market_data"
                 ├─ HybridStrategyEngine._on_market_data()
                 └─ _on_market_data()  ← 시스템 캐시 갱신 + SL/TP 발동 검사
```

### 5.2 뉴스 → 감정
```
NLPEngine.process_news(title, content, symbol)
  └─ analyze_sentiment(text)  ← 한글/영문 키워드 사전
       └─ publish "news_sentiment"
            └─ HybridStrategyEngine 캐시 + 시스템 캐시
```

### 5.3 신호 → 주문 (자동 SL/TP)
```
HybridStrategyEngine.analyze() → StrategyResult
  └─ publish "strategy_signal"
       └─ _on_strategy_signal()
            └─ _create_and_submit_order(symbol, BUY/SELL, price)
                 ├─ position sizing (Kelly) ← RiskManager
                 ├─ create_order(진입)
                 ├─ create_stop_loss_order(트리거 가격)
                 ├─ create_take_profit_order(익절 가격)
                 └─ submit_order × 3
```

### 5.4 증권사 연동
```
MultiBrokerManager.place_order() → 활성 커넥터.place_order()
  └─ 시뮬레이션 모드: 즉시 체결 시뮬레이션
  └─ 실전 모드: 증권사 API 호출 (현재는 시뮬레이션만 지원)
```

### 5.5 자산 동기화
```
AccountSyncAgent.sync_with_broker(broker_cash, broker_holdings)
  └─ PortfolioManager (현금·포지션 보정)
       └─ AssetHistoryDB.save_snapshot()  ← 자산 이력
```

## 6. 시스템 파라미터

### 6.1 위험 관리 (`RiskManager`)
| 파라미터 | 기본값 | 위치 |
|---------|--------|------|
| `default_stop_loss_pct` | 0.05 | `risk_manager.py:39` |
| `default_take_profit_pct` | 0.10 | `risk_manager.py:39` |
| `max_loss_per_trade_pct` | 0.02 | `risk_manager.py:39` |
| `max_portfolio_loss_pct` | 0.10 | `risk_manager.py:39` |
| `max_position_size_pct` | 0.20 | `risk_manager.py:39` |
| `atr_multiplier_stop` | 2.0 | `risk_manager.py:75` |
| `atr_multiplier_target` | 4.0 | `risk_manager.py:79` |

### 6.2 전략 엔진 (`HybridStrategyEngine`)
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `weights` | `{technical: 0.25, sentiment: 0.20, ml: 0.20, rl: 0.20, darkpool: 0.05, llm: 0.10}` | 신호 가중치 |
| `adapt_window` | 50 | 가중치 적응 윈도우 |
| `rsi_period` | 14 | RSI 계산 기간 |
| `macd_fast/slow/signal` | 12/26/9 | MACD 파라미터 |

### 6.3 백테스트 (`BacktestEngine`)
| 파라미터 | 기본값 | 위치 |
|---------|--------|------|
| `fee_pct` | 0.001 | `backtest.py` |
| `slippage_pct` | 0.001 | `backtest.py` |
| `market_impact_pct` | 0.0005 | `backtest.py` |

## 7. 테스트 결과

### 7.1 유닛 테스트 (19/19 PASS)

| 영역 | 테스트 | 상태 |
|------|--------|------|
| MarketDataHandler | 2 | ✅ |
| NLPEngine | 3 | ✅ |
| PortfolioManager | 4 | ✅ |
| AccountSyncAgent | 1 | ✅ |
| OrderManagementSystem | 4 | ✅ |
| HybridStrategyEngine | 1 | ✅ |
| Phase3 Integration | 4 | ✅ |
| SB3 RL (선택) | 1 | ⏭ SB3 미설치 시 스킵 |

### 7.2 정적 분석
- **ruff**: 0 errors
- **mypy --strict**: `Success: no issues found in 50 source files`
- **bandit**: 0 high-severity issues (의도된 `urlopen`은 `# nosec`)

### 7.3 CI 단계
1. `ruff check` — PEP 8 + 버그 탐지
2. `mypy` — 타입 검사
3. `pytest` / `unittest` — 유닛 테스트
4. `bandit -r src -ll` — 보안 정적 분석
5. `pip-audit` — 의존성 CVE 스캔

## 8. 디렉터리 구조

```
trading_system/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_layer/        (4)
│   ├── core/              (6) — 전략, 주문, 자산, 팩토리, HFT, 통계차익
│   ├── risk/              (1)
│   ├── analysis/          (6) — 백테스트, 통계, ML, RL, 양자(클래식), 스캐너
│   ├── broker/            (11) — 7 증권사 + 매니저 + 프로토콜
│   ├── strategy/          (3) — 유명투자자 + 자산배분
│   ├── ai/                (5) — LLM, DQN, 어닝, 감정
│   ├── persistence/       (1) — aiosqlite
│   ├── utils/             (8) — EventBus, ErrorHandler, 리포트, 알림
│   ├── web/               (1) — FastAPI 대시보드
│   └── telegram_bot/      (2)
├── tests/
│   ├── test_system.py             (15)
│   └── phase3/
│       ├── test_allocation.py     (1)
│       ├── test_broker_reporting.py (3)
│       ├── test_m1_ai_pipeline.py (3)
│       └── e2e/test_e2e.py
├── trading_system.py              (메인 통합, 771줄)
├── test_system.py                 (데모)
├── demo_*.py                      (고급 데모)
├── run_dashboard.py               (대시보드 실행)
├── telegram_bot_runner.py
├── README.md
├── IMPLEMENTATION_GUIDE.md        (본 문서)
├── ADVANCED_FEATURES.md
├── ALGORITHMS.md
├── requirements.txt
└── pyproject.toml
```

## 9. 알려진 제약

- `broker/*.py` 7종 모두 **시뮬레이션 모드만** 구현. 실전 API 연동은 `connect()` 내부의
  `simulation_mode = True`를 끄고 PyQt5/pywin32로 OCX 호출 필요.
- `quantum_optimizer.py`는 **클래식 Mean-Variance / Risk-Parity**이며, 명칭은
  `QuantumPortfolioOptimizer`이지만 실제 양자 어닐링은 사용하지 않음 (코드 동작은
  docstring과 일치).
- `darkpool_tracker.py`는 **중립값(0.0) 반환** — 다크풀 데이터 소스 부재로 의도적으로
  신호를 주지 않음. `HybridStrategyEngine` 가중치에서 5%만 차지하므로 영향 미미.
- `hft_engine.py`는 `time.perf_counter_ns`만 측정하는 **Mock**. 실전 HFT는 Cython/C++
  래퍼가 필요.
- `rl_trading.py`는 Phase 3 테스트 호환용 얇은 래퍼. 실전 RL 학습은 `rl_trader.py`
  (`DQNAgent`, `TradingEnvironment`)을 직접 사용.

## 10. 향후 작업 후보

1. `RiskManager.calculate_atr_based_stop()` 을 `_create_and_submit_order()`에 통합
2. `dashboard.py` 단일 파일 (3258줄) → `routes/`, `services/`, `tasks/` 분리
3. 증권사 OCX 어댑터 추상화 + 시뮬레이션 fallback 명확화
4. SB3 PPO 학습 파이프라인 (현재 in-house DQN만 동작)
5. 실시간 시세 WebSocket 어댑터 (현재는 yfinance polling)

---

**마지막 업데이트**: 2026-06-06
**검증 상태**: ruff ✓ mypy ✓ 19/19 tests pass

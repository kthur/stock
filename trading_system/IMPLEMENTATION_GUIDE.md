# 주식 트레이딩 시스템 - 구현 가이드

> **상태**: Phase 1-5 + 30개 개선 항목 통합 완료
> **테스트**: 105/105 통과 · **린트**: ruff 0 오류

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
       │  GlobalMarketClient · RelativeStrengthAnalyzer              │
       └──────────────────┬───────────────────────────────────────────┘
                          │ event_bus.publish("market_data" / "news_sentiment")
                          ▼
       ┌──────────────── 전략 엔진 (core/strategy_engine.py) ──────────────┐
       │  HybridStrategyEngine (8-시그널 가중합, 동적 가중치 적응)        │
       │  ├─ 기술 + 감정 + ML + RL + DarkPool + LLM                      │
       │  ├─ GlobalMarket + CashRatio (8개 신호)                          │
       │  ├─ Signal Consensus Scoring (합의도 기반 증폭)                  │
       │  ├─ Regime-based Full Weight Adjustment (ADX + BB Width)        │
       │  └─ 50-거래 윈도우 적응형 가중치 (HybridStrategyEngine)          │
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
       │  2. Volatility Targeting (목표 연변동성 15%로 스케일)              │
       │  3. Confidence-based Sizing (신뢰도 0.5→0.75x, 1.0→1.0x)         │
       │  4. Cash Ratio Adjustment (현금 과다/부족 반영)                   │
       │  5. Multi-timeframe Confirmation (주봉 약세 시 50% 축소)         │
       │  6. VIX Risk-Off (VIX≥25 → 현금 70% 강제)                       │
       │  7. Market Impact (일일 거래량 >5%면 축소)                        │
       │  8. Correlation Regime (고상관 시 25% 축소)                      │
       │  9. Risk Parity 집중도 체크 (상관기반 한도)                       │
       │  10. Earnings Gapper Protection (실적 5일 전 50% 축소)            │
       │  11. Max Concurrent Positions (최대 10종목)                       │
       │  12. Available Cash Check + Min Trade Unit                       │
       └───────────────────────────────────────────────────────────────────┘
                          ▼
       ┌──────────────── 증권사 연동 (broker/) ──────────────────────────────┐
       │  MultiBrokerManager  →  7개 증권사 (Kiwoom/Daishin/Hanwha/       │
       │  KoreaInvestment/MiraeAsset/NH/LS), simulation_mode 기본         │
       └──────────────────┬───────────────────────────────────────────────┘
                          ▼
       ┌──────────────── 저장 / 알림 ───────────────────────────────────────┐
       │  TradeLogger (aiosqlite) / AssetHistoryDB / AIPredictionDB       │
       │  TelegramBotEngine (18+ 명령어) / Plotly Dash 대시보드            │
       │  Trade Journal (거래 내역 구조화 저장) / State Auto-Save         │
       └──────────────────────────────────────────────────────────────────┘
```

### 1.2 패키지 구성 (48 모듈)

| 패키지 | 파일 수 | 책임 |
|--------|--------|------|
| `src/data_layer/` | 4 | 시세, 뉴스, 시장 레짐, 글로벌 마켓 |
| `src/core/` | 8 | 자산관리, 전략, 주문, 통계차익, HFT(Mock), 팩토리, DistributedOrderManager, Risk Parity |
| `src/risk/` | 1 | Kelly/VaR/CVaR/Drawdown/상관관계/ATR/Volatility Targeting |
| `src/analysis/` | 7 | 백테스트, 통계, ML, RL, 양자(클래식)최적화, 스캐너, Relative Strength |
| `src/broker/` | 11 | 7개 증권사 커넥터 + MultiBrokerManager + 프로토콜 |
| `src/strategy/` | 3 | 유명 투자자 전략 + 자산 배분 |
| `src/ai/` | 5 | LLM/OpenAI·Gemini 통합, DQN RL, 어닝 분석, 감정 |
| `src/persistence/` | 1 | aiosqlite 비동기 DB 3종 |
| `src/utils/` | 8 | EventBus, ErrorHandler, Notifier, PDF/Text 리포트 |
| `src/web/` | 1 | Plotly Dash 대시보드 |
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
# 전체 테스트 (105개)
python -m pytest tests/test_system.py tests/test_risk_manager.py tests/test_telegram_bot.py -v

# 핵심 유닛 테스트
python -m pytest tests/test_system.py -v
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

# 2) 커스텀 컴포넌트 주입
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
# {
#   "cash": 850000.0,
#   "positions": {"AAPL": {"quantity": 10, ...}},
#   "open_orders": 2,
#   "total_trades": 3,
# }
```

### 3.3 포트폴리오 분석 조회

```python
# 위험조정 성과지표
analytics = system.get_portfolio_analytics()
# {
#   "sharpe_ratio": 1.234,
#   "sortino_ratio": 1.876,
#   "calmar_ratio": 2.345,
#   "daily_volatility": 0.008,
#   "avg_daily_return": 0.001,
# }

# 거래 저널
journal = system.get_trade_journal(limit=10)
# [{"event": "order_submitted", "symbol": "AAPL", ...}, ...]

# 위험 리포트
risk = system.get_risk_report()
```

### 3.4 전략 직접 호출

```python
from src.core import HybridStrategyEngine, TradeSignal

engine = HybridStrategyEngine()
result = engine.analyze(
    symbol="005930",
    market_data={"price": 71000, "bid": 70950, "ask": 71050, "volume": 1_200_000},
    news_sentiment=0.6,
    price_bars=None,
    cash_ratio=0.35,  # 8번째 신호: 현금 비중
)
# result.signal  : TradeSignal.BUY / SELL / HOLD
# result.confidence : 0.0 ~ 1.0
```

### 3.5 주문 + 자동 손절/익절 (ATR + Trailing + Partial TP)

```python
from src.core import OrderType

# 내부 호출 (자동 SL/TP + 트레일링 스탑 + 부분 익절 포함)
# 진입가 70,000원
# → SL: ATR 2.0x (변동성 적응)
# → TP: 1.5x/3.0x/5.0x ATR 3-티어 분할 익절 (33/33/34%)
# → 가격 상승 시 트레일링 스탑으로 SL 자동 상향
await system._create_and_submit_order("005930", OrderType.BUY, 70_000, confidence=0.8)
```

### 3.6 백테스트

```python
from src.analysis import BacktestEngine
from datetime import datetime, timedelta

engine = BacktestEngine(initial_capital=1_000_000, fee_pct=0.001,
                        slippage_pct=0.001, market_impact_pct=0.0005)

bars = system.market_data_handler.fetch_historical_data("005930", period="1y")

def strategy_func(bars):
    if len(bars) < 2:
        return "HOLD"
    return "BUY" if bars[-1].close > bars[-2].close else "HOLD"

result = engine.run_backtest("005930", bars, strategy_func)
```

### 3.7 리밸런싱

```python
target = {"005930": 0.4, "000660": 0.3, "035420": 0.3}
prices = {"005930": 70000, "000660": 130000, "035420": 200000}

plan = system.portfolio.compute_rebalance_plan(target, prices)
cash_needed = system.portfolio.estimate_rebalance_cash_needed(plan, prices)

# 자동 리밸런싱 실행 (주기 스케줄러 내장: 168시간마다)
await system.rebalance_portfolio()
```

## 4. 포지션 사이징 파이프라인 (Order Sizing Pipeline)

> 주문 생성 시 12단계 검증을 순차적으로 통과합니다.

```
1. Kelly Criterion           → 이론적 최적 수량
2. Volatility Targeting      → 목표 연변동성 15% 기준 스케일 [0.25x, 2.0x]
3. Confidence-based Sizing   → 신뢰도에 따라 선형 스케일 [0.75x, 1.0x]
4. Cash Ratio Adjustment     → 현금 과다/부족 반영 [0.5x, 1.5x]
5. Multi-timeframe Confirm   → 주봉 EMA20<EMA50 이면 50% 축소
6. Earnings Gapper Protection→ 실적 5일 전이면 50% 축소
7. VIX Risk-Off              → VIX≥25면 현금 70% 강제 유지
8. Market Impact             → 일일 거래량 대비 5% 초과 시 축소
9. Correlation Regime        → 포트폴리오 평균 상관계수>0.8 시 25% 축소
10. Risk Parity 집중도 체크  → 상관관계 기반 포지션 한도 적용
11. Max Concurrent Positions → 최대 10종목 초과 시 차단
12. Cash + Min Trade Unit    → 가용 현금 확인 + 최소 거래 단위 보장
```

**구현 위치**: `trading_system.py:_create_and_submit_order()` (전체 파이프라인)

## 5. 자동 손절/익절 + 트레일링 스탑

### 5.1 라이프사이클

```
진입 주문 체결 → _create_and_submit_order()
  ├─ ATR 기반 SL/TP 가격 계산 (또는 고정 비율 폴백)
  ├─ SL 주문 생성 (1개)
  ├─ TP 주문 3-티어 생성 (ATR 1.5x / 3.0x / 5.0x)
  └─ 모두 SUBMITTED
       
시장 데이터 도착 → _on_market_data()
  ├─ check_and_trigger_stop_orders() → 발동 조건 충족 시 체결
  ├─ _update_trailing_stops() → 가격 상승 시 SL trigger_price 상향
  ├─ _check_portfolio_stop_loss() → 전체 DD 20% 초과 시 전량 청산
  └─ _check_rebalance_schedule() + _auto_save_state()
```

### 5.2 트레일링 스탑

- `trail_pct = 0.05` (5%): 가격 상승 시 SL을 따라 올림
- `_on_market_data()`에서 매 틱마다 `_update_trailing_stops()` 호출
- 기존 SL 주문의 `trigger_price`를 직접 갱신 (취소/재생성 불필요)
- `Position.highest_price` 워터마크 갱신

### 5.3 포트폴리오 레벨 손절

- `max_portfolio_drawdown_pct = 0.20` (20%)
- 초과 시 모든 포지션 즉시 시장가 청산 + 신규 주문 차단
- `_portfolio_liquidated = True`로 중복 청산 방지

## 6. 데이터 흐름 상세

### 6.1 시세 → 신호

```
yfinance API
  └─ MarketDataHandler._fetch_yf_with_retry()  ← tenacity 재시도 + CircuitBreaker
       └─ publish_market_data()
            └─ event_bus "market_data"
                 ├─ _on_market_data()  ← 캐시 + SL/TP + 트레일링 + 상태저장
                 └─ strategy_engine (시세 캐시)
```

### 6.2 뉴스 → 감정

```
NLPEngine.process_news(title, content, symbol)
  └─ analyze_sentiment(text)  ← 한글/영문 키워드 사전
       └─ publish "news_sentiment"
            └─ strategy_engine 캐시 + 시스템 캐시
```

### 6.3 신호 → 주문 (전체 파이프라인)

```
HybridStrategyEngine.analyze() → StrategyResult (confidence 포함)
  └─ publish "strategy_signal"
       └─ _on_strategy_signal()
            └─ _create_and_submit_order(symbol, type, price, confidence)
                 ├─ Staleness Guard → Max Positions Guard
                 ├─ Limit Order Pricing (bid/ask spread capture)
                 ├─ Regime Filter (EMA200)
                 ├─ ATR Stop 계산
                 ├─ Kelly Position Sizing
                 ├─ [12단계 사이징 파이프라인]
                 ├─ Single Order 또는 Distributed Order 분기
                 ├─ SL + 3-Tier TP 생성
                 └─ Trade Journal 기록
```

## 7. 시스템 파라미터

### 7.1 위험 관리 (`RiskManager`)

| 파라미터 | 기본값 | 위치 |
|---------|--------|------|
| `default_stop_loss_pct` | 0.05 | `risk_manager.py` |
| `default_take_profit_pct` | 0.10 | `risk_manager.py` |
| `max_loss_per_trade_pct` | 0.02 | `risk_manager.py` |
| `max_portfolio_loss_pct` | 0.10 | `risk_manager.py` |
| `max_position_size_pct` | 0.20 | `risk_manager.py` |
| `atr_multiplier_stop` | 2.0 | `risk_manager.py` |
| `atr_multiplier_target` | 4.0 | `risk_manager.py` |
| `target_annual_volatility` | 0.15 | `risk_manager.py` |

### 7.2 전략 엔진 (`HybridStrategyEngine`)

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `sentiment_weight` | 0.30 | 감성 분석 |
| `technical_weight` | 0.20 | RSI/MACD/MA |
| `ml_weight` | 0.20 | ML 예측 |
| `rl_weight` | 0.10 | RL 휴리스틱 |
| `darkpool_weight` | 0.10 | 다크풀 (중립) |
| `llm_weight` | 0.10 | LLM 의견 |
| `global_market_weight` | 0.10 | 글로벌 지수 (7번째) |
| `cash_ratio_weight` | 0.08 | 현금 비중 (8번째) |
| `adapt_window` | 50 | 가중치 적응 윈도우 |

### 7.3 트레이딩 시스템 (`StockTradingSystem`)

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `min_trade_value_pct` | 0.001 | 최소 거래 = PV의 0.1% |
| `distributed_threshold_pct` | 0.005 | 분산 주문 = PV의 0.5% |
| `trail_pct` | 0.05 | 트레일링 스탑 5% |
| `correlation_limit_pct` | 0.40 | 상관쌍 최대 40% |
| `target_annual_volatility` | 0.15 | 목표 연변동성 15% |
| `max_portfolio_drawdown_pct` | 0.20 | 포트폴리오 청산 DD |
| `max_concurrent_positions` | 10 | 최대 동시 보유 종목 |
| `max_data_age_seconds` | 300 | 허용 시세 지연 시간 |
| `rebalance_interval_hours` | 168 | 리밸런싱 주기 (7일) |
| `state_save_interval_seconds` | 3600 | 상태 자동 저장 주기 |

## 8. 테스트 결과

### 8.1 유닛 테스트 (105/105 PASS)

| 영역 | 테스트 파일 | 테스트 수 |
|------|------------|----------|
| MarketDataHandler | `test_system.py` | 2 |
| NLPEngine | `test_system.py` | 3 |
| PortfolioManager | `test_system.py` | 4 |
| AccountSyncAgent | `test_system.py` | 1 |
| OrderManagementSystem | `test_system.py` | 4 |
| StrategyEngine (10 tests) | `test_system.py` | 12 |
| GlobalMarketClient | `test_system.py` | 4 |
| RelativeStrengthAnalyzer | `test_system.py` | 6 |
| DistributedOrderManager | `test_system.py` | 7 |
| PreTradeConcentrationCheck | `test_system.py` | 4 |
| PortfolioBasedSizing | `test_system.py` | 7 |
| RiskManager (33 tests) | `test_risk_manager.py` | 33 |
| TelegramBot (17 tests) | `test_telegram_bot.py` | 17 |
| **Total** | **3 files** | **105** |

### 8.2 정적 분석

- **ruff**: 0 errors (src/ 전체)

### 8.3 테스트 명령

```bash
# 전체 테스트
python -m pytest tests/test_system.py tests/test_risk_manager.py tests/test_telegram_bot.py -v

# 특정 영역만
python -m pytest tests/test_system.py::TestStrategyEngine -v
python -m pytest tests/test_risk_manager.py -v
python -m pytest tests/test_telegram_bot.py -v

# 린트
python -m ruff check src/

# 타입 검사
python -m mypy src/ --strict
```

## 9. 디렉터리 구조

```
trading_system/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_layer/            (4) — 시세, 뉴스, 시장 레짐, 글로벌 마켓
│   ├── core/                  (8) — 전략, 주문, 자산, 팩토리, HFT, 통계차익,
│   │                               distributed_order, PortfolioManager
│   ├── risk/                  (1) — RiskManager (Kelly, ATR, VaR, Vol Target)
│   ├── analysis/              (7) — 백테스트, 통계, ML, RL, 양자(클래식),
│   │                               스캐너, RelativeStrength
│   ├── broker/                (11) — 7 증권사 + 매니저 + 프로토콜
│   ├── strategy/              (3) — 유명투자자 + 자산배분
│   ├── ai/                    (5) — LLM, DQN, 어닝, 감정
│   ├── persistence/           (1) — aiosqlite
│   ├── utils/                 (8) — EventBus, ErrorHandler, 리포트, 알림
│   ├── web/                   (1) — Plotly Dash 대시보드
│   └── telegram_bot/          (2) — 텔레그램 봇 + 미니앱
├── tests/
│   ├── test_system.py         (55)
│   ├── test_risk_manager.py   (33)
│   ├── test_telegram_bot.py   (17)
│   ├── test_macro.py          (dash 미설치 시 스킵)
│   ├── test_portfolio_risk.py (dash 미설치 시 스킵)
│   └── phase3/                (기존, SB3 조건부)
├── trading_system.py          (메인 통합, ~1470줄)
├── IMPLEMENTATION_GUIDE.md    (본 문서)
├── ADVANCED_FEATURES.md
├── ALGORITHMS.md
├── requirements.txt
└── pyproject.toml
```

## 10. 신규 기능: 동작 확인 방법

### 10.1 현금 비중 신호 (Cash Ratio Signal)

```python
# analyze()에 cash_ratio 파라미터 전달
result = engine.analyze("AAPL", market_data, 0.0, cash_ratio=0.9)
# confidence > 0.5 (현금 많음 → 매수 유도)

result = engine.analyze("AAPL", market_data, 0.0, cash_ratio=0.05)
# confidence < 0.5 (현금 부족 → 매수 억제)
```

### 10.2 트레일링 스탑

시세 업데이트마다 SL이 상향 조정되는지 로그 확인:
```
Trailing stop updated: AAPL 145.00 -> 147.25 (trail=5.0%, price=155.00)
```

### 10.3 포트폴리오 분석

```python
analytics = system.get_portfolio_analytics()
# {"sharpe_ratio": 1.5, "sortino_ratio": 2.1, ...}
```

### 10.4 거래 저널

```python
journal = system.get_trade_journal()
# [{"event": "order_submitted", "symbol": "AAPL", "confidence": 0.85, ...}]
```

### 10.5 성과 속성 (Performance Attribution)

```python
attribution = system.optimization_engine.get_signal_performance_attribution()
# {"technical": {"total_pnl": 1250.0, "trade_count": 15, "win_rate": 0.6}, ...}
```

### 10.6 리밸런싱 스케줄러

로그에서 168시간마다 자동 실행 확인:
```
Scheduled rebalance triggered (interval=168h)
```

### 10.7 상태 자동 저장

`state_snapshot.json` 파일이 1시간마다 갱신되는지 확인.

## 11. 알려진 제약

- `broker/*.py` 7종 모두 **시뮬레이션 모드만** 구현. 실전 API 연동은 `connect()` 내부의 `simulation_mode = True`를 끄고 PyQt5/pywin32로 OCX 호출 필요.
- `quantum_optimizer.py`는 **클래식 Mean-Variance / Risk-Parity**이며, 명칭은 `QuantumPortfolioOptimizer`이지만 실제 양자 어닐링은 사용하지 않음.
- `darkpool_tracker.py`는 **중립값(0.0) 반환** — 데이터 소스 부재로 의도적으로 신호를 주지 않음.
- `hft_engine.py`는 `time.perf_counter_ns`만 측정하는 **Mock**.
- `rl_trading.py`는 테스트 호환용 얇은 래퍼. 실전 RL 학습은 `rl_trader.py` (`DQNAgent`, `TradingEnvironment`)을 직접 사용.
- `tests/phase3/test_m1_ai_pipeline.py`는 SB3 미설치 시 `pytest.importorskip`에서 블로킹 (pre-existing).
- `tests/phase3/e2e/test_e2e.py`는 `trading_system.phase3` 참조 문제로 `@pytest.mark.skip` (pre-existing).

---

**마지막 업데이트**: 2026-06-08
**검증 상태**: ruff ✓ 105/105 tests pass

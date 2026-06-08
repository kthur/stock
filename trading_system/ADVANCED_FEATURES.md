# 고급 기능 설명서 - ADVANCED FEATURES

본 문서는 `D:\Finance\code\stock\trading_system\`이 실제로 구현하고 있는 **30+ 고급 기능**을
기능별로 설명합니다. 각 섹션은 **기능 설명, 구현 위치, 정책(또는 수식), 사용 방법** 순서로 구성됩니다.

---

## 1. 신호 시스템

### 1.1 신호 합의 점수 (Signal Consensus Scoring, v4.0)

**목적**: 8개 신호의 방향성 일치도를 측정하여 신뢰도를 증폭 또는 감쇠합니다.

**파일**: `trading_system.py:_on_strategy_signal()` (라인 690)

| 신호 일치도 | 효과 | 계산 |
|------------|------|------|
| 7~8개 일치 | confidence × 1.40 | 강한 합의 = 강한 진입 |
| 5~6개 일치 | confidence × 1.15 | 약한 합의 = 약한 증폭 |
| 3~4개 일치 | confidence × 0.85 | 분열 = 신뢰도 하락 |
| 1~2개 일치 | confidence × 0.60 | 소수 의견 = 대폭 감쇠 |

`sell_consensus`와 `buy_consensus`를 각각 계산하여 매수/매도 각각에 반영합니다.

### 1.2 레짐 기반 가중치 전체 조정 (Regime-based Full Weight, v4.1)

**파일**: `trading_system.py:_adjust_weights_for_regime()`

추세가 강할 때(ADX ≥ 25) ML/기술적 가중치 증폭, 추세 약할 때 감성/LLM 가중치 증폭:

| 조건 | ADX | BB Width | ML 가중치 승수 | Sentiment 가중치 승수 |
|------|-----|----------|---------------|----------------------|
| 강한 추세 | ≥ 25 | — | ×1.5 | ×0.7 |
| 약한 추세 | < 25 | — | ×0.7 | ×1.3 |
| 고변동성 | — | 높음 (25% 기준) | ×0.8 | ×0.8 |
| 저변동성 | — | 낮음 | ×1.2 | ×1.2 |

### 1.3 50-거래 적응형 가중치 (Adaptive Weights)

**파일**: `core/strategy_engine.py:HybridStrategyEngine._update_weights()`

최근 50개 신호의 정확도를 기반으로 각 신호 가중치를 동적으로 조정합니다:
- 정확도가 높은 신호의 가중치를 증가시키고 낮은 신호를 감소시킵니다.
- 변화율은 `LEARNING_RATE = 0.1`로 제한하여 급격한 변동을 방지합니다.

---

## 2. 주문 및 실행

### 2.1 다중 증권사 분산 주문 (Distributed Order, v1.0)

**파일**: `core/distributed_order.py:DistributedOrderManager`

단일 대량 주문을 7개 증권사로 분할하여 시장 임팩트를 완화:
- `min_order_size = 1,000,000`원 이상이면 자동 분할
- Kiwoom 20% / Daishin 15% / Hanwha 15% / K.Invest 20% / Mirae 15% / NH 15%
- 각 broker에 개별 `PlaceOrderJob` 전송

### 2.2 지정가 주문 (Limit Order Entry, v2.0)

**파일**: `trading_system.py:_create_and_submit_order()` (라인 490)

시장가 대신 호가 스프레드 내 지정가로 주문하여 체결 품질 개선:
```python
price = bid + (ask - bid) * 0.3  # 스프레드의 30% 지점
```
단, 긴급 청산(손절/포지션청산)은 시장가 유지.

### 2.3 트레일링 스탑 (Trailing Stop, v4.0)

**파일**: `trading_system.py:_update_trailing_stops()` (라인 580)

**파라미터**: `trail_pct = 0.05` (고정 5%)

모든 오픈 포지션을 순회하며:
1. 현재가가 `Position.highest_price`보다 높으면 워터마크 갱신
2. 새 워터마크 기준으로 `trigger_price = highest_price × (1 - trail_pct)` 계산
3. 기존 STOP_LOSS 주문의 `trigger_price` 필드를 직접 갱신 (재생성 불필요)

### 2.4 부분 익절 (Partial Take-Profit, v4.2)

**파일**: `trading_system.py:_create_and_submit_order()`(라인 498)

ATR 기반 3-티어 분할 익절로 단일 TP 대비 성능 개선:

| 티어 | ATR 배수 | 할당 비율 |
|------|---------|----------|
| 1차 | 1.5× ATR | 33% |
| 2차 | 3.0× ATR | 33% |
| 3차 | 5.0× ATR | 34% |

각 티어가 체결될 때마다 나머지 티어의 수량을 자동 조정합니다.

---

## 3. 위험 관리

### 3.1 켈리 공식 (Kelly Criterion)

**파일**: `risk/risk_manager.py:RiskManager.kelly_criterion()`

```python
f* = (p * win_ratio - loss_ratio) / (win_ratio * loss_ratio / avg_win)
```
- `p`는 백테스트 기반 승률, `win_ratio`는 평균 수익률/손실률
- 실제 적용 시 **1/2 Kelly** 사용 (25%로 캡: `min(f*, 0.25)`)
- `position_size = kelly_fraction * portfolio_value`

### 3.2 변동성 타겟팅 (Volatility Targeting, v4.0)

**파일**: `risk/risk_manager.py:RiskManager.compute_volatility_targeting()`

목표 연변동성 15%를 유지하도록 포지션 크기를 동적 조정:
```python
scale = target_annual_vol / (current_vol + 1e-10)
clipped_scale = clamp(scale, 0.25, 2.0)  # [0.25x, 2.0x] 범위 제한
adjusted_size = base_size * clipped_scale
```
- ATR(14) 기반 일변동성 → 연변동성 환산: `vol * sqrt(252)`
- 저변동성 시장에서는 최대 2배까지 레버리지 가능
- 고변동성 시장에서는 최소 25%로 축소

### 3.3 VaR / CVaR (Value at Risk)

**파일**: `risk/risk_manager.py:RiskManager.var()`, `.cvar()`

```python
VaR(95%) = -percentile(daily_returns, 5) * sqrt(holding_days)
CVaR(95%) = -mean of worst 5% returns * sqrt(holding_days)
```
- 최소 252개 일일 수익률 필요
- VaR 초과 시 전체 포지션의 50% 강제 청산

### 3.4 시장 임팩트 모델 (Market Impact, v4.0)

**파일**: `trading_system.py:_compute_market_impact()`

```python
impact = order_value / (avg_daily_volume * close_price)
if impact > 0.05:  # 일일 거래량의 5% 초과
    reduction = 0.05 / impact
    sized_quantity = int(sized_quantity * reduction)
```

### 3.5 상관관계 레짐 (Correlation Regime, v4.0)

**파일**: `trading_system.py:_compute_portfolio_correlation()` (라인 780)

포지션 간 평균 상관계수를 계산하고 고상관 상태 감지:
```python
corr_matrix = prices.pct_change().corr()
avg_corr = (corr_matrix.sum().sum() - n) / (n * (n - 1))
if avg_corr > 0.80:
    sized_quantity *= 0.75  # 25% 축소
```

### 3.6 포트폴리오 레벨 손절 (Portfolio Stop Loss, v4.1)

**파일**: `trading_system.py:_check_portfolio_stop_loss()`

`max_portfolio_drawdown_pct = 0.20` (20%) 초과 시:
1. 모든 오픈 포지션 즉시 시장가 청산
2. 모든 오픈 STOP_LOSS/TAKE_PROFIT 주문 취소
3. `_portfolio_liquidated = True` 플래그로 중복 청산 방지
4. 시스템 콜드 스타트 후에도 플래그 유지 (재진입 방지)

---

## 4. 성과 및 모니터링

### 4.1 성과 속성 분석 (Performance Attribution, v4.0)

**파일**: `core/strategy_engine.py:OptimizationEngine.get_signal_performance_attribution()`

각 신호의 개별 성과를 추적:
```python
{
  "technical": {"total_pnl": 1250.0, "trade_count": 15, "win_rate": 0.6,
                "avg_pnl": 83.33, "max_drawdown": -300.0},
  "sentiment": {"total_pnl": -200.0, "trade_count": 8, "win_rate": 0.375,
                "avg_pnl": -25.0, "max_drawdown": -150.0},
  ...
}
```
- 신호별로 실제 체결된 거래와 매핑하여 PnL 누적
- 각 사이클 시작 시 초기화되므로 장기 실행 시 과거 데이터 유실

### 4.2 거래 저널 (Trade Journal, v4.0)

**파일**: `trading_system.py:_log_trade_event()` (라인 160)

모든 트레이딩 이벤트를 메모리 큐에 저장:
```python
journal_entry = {
    "event": "order_submitted",
    "symbol": "AAPL",
    "timestamp": datetime.now().isoformat(),
    "details": {"order_type": "BUY", "price": 150.0, "quantity": 10, "confidence": 0.85}
}
```
- `get_trade_journal(limit=50)`로 최근 N개 조회
- 이벤트 타입: `order_submitted`, `stop_triggered`, `trailing_stop_updated`, `stop_placed`, `tp_triggered`, `position_closed`, `portfolio_liquidated`, `order_rejected`, `rebalance_completed`, `state_saved`

### 4.3 포트폴리오 분석 (Portfolio Analytics, v4.0)

**파일**: `trading_system.py:PortfolioAnalytics`

```python
analytics = {
    "sharpe_ratio": 1.5,         # (avg_return - rf) / std_return
    "sortino_ratio": 2.1,        # (avg_return - rf) / downside_std
    "calmar_ratio": 2.3,         # CAGR / max_drawdown
    "daily_volatility": 0.008,   # std(daily_returns)
    "avg_daily_return": 0.001,   # mean(daily_returns)
    "max_drawdown": -0.05,       # 최대 낙폭
    "total_return": 0.03,        # 누적 수익률
    "positive_days_ratio": 0.55, # 상승일 비율
    "avg_win": 0.02,             # 평균 수익일 수익률
    "avg_loss": -0.015,          # 평균 손실일 손실률
}
```
- 최소 2개 일일 수익률 필요 (부족 시 None 반환)
- 무위험 수익률: 0.02 (고정)

### 4.4 상태 자동 저장 (State Auto-Save, v4.1)

**파일**: `trading_system.py:_auto_save_state()` (라인 830)

`state_save_interval_seconds = 3600` (1시간)마다:
```python
state = {
    "cash": self.cash,
    "positions": {...},
    "portfolio_value": self.portfolio.get_total_value(),
    "pending_amount": ...,
    "timestamp": ...,
}
# state_snapshot.json에 저장 (직렬화 보장)
```
- 시작 시 `state_snapshot.json` 존재하면 자동 복원
- 텔레그램 `/state` 명령어로 조회 가능

---

## 5. 데이터 및 외부 연동

### 5.1 어닝 분석 (Earnings Analyzer, v4.2)

**파일**: `ai/earnings_analyzer.py:EarningsAnalyzer`

실적 발표 텍스트를 분석하여 매수/매도/중립 신호 생성:
- 카테고리: 매출 / EPS / 가이던스 / 현금흐름 / 부채
- 각 카테고리별 감정 점수 집계
- 실적일 기준 ±5일은 포지션 크기 50% 자동 축소 (Earnings Gapper Protection)

### 5.2 리밸런싱 스케줄러 (v4.1)

**파일**: `trading_system.py:_check_rebalance_schedule()`

`rebalance_interval_hours = 168` (7일)마다 자동 리밸런싱:
- `_last_rebalance_time` 기준 경과 시간 확인
- `rebalance_portfolio()` 호출
- 로그 기록: `Scheduled rebalance triggered (interval=168h)`

### 5.3 감정 분석 (NLP Engine)

**파일**: `data_layer/nlp_engine.py:NLPEngine`

한글/영문 키워드 기반 감정 점수:
- 긍정 키워드: 상승/돌파/호실적/수주/신고가/특허/협력 (+0.1~+0.3)
- 부정 키워드: 하락/악재/적자/하향/조정/소송/감산 (-0.1~-0.3)
- 최종 점수: `clamp(pos_count / total - neg_count / total, -1.0, 1.0)`

### 5.4 텔레그램 봇 (Telegram Bot, 18+ 명령어)

**파일**: `telegram_bot/telegram_bot_engine.py:TelegramBotEngine`

| 명령어 | 기능 | 응답 형식 |
|--------|------|----------|
| `/start` | 봇 시작 및 환영 메시지 | 텍스트 |
| `/help` | 명령어 목록 | 텍스트 |
| `/status` | 시스템 상태 조회 | 텍스트 |
| `/balance` | 계좌 잔고 조회 | 텍스트 |
| `/positions` | 포지션 현황 | 텍스트 |
| `/performance` | 성과 요약 | 텍스트 |
| `/risk` | 위험 지표 | 텍스트 |
| `/trade [symbol] [type]` | 주문 실행 | 텍스트 |
| `/cancel [order_id]` | 주문 취소 | 텍스트 |
| `/orders` | 미체결 주문 | 텍스트 |
| `/state` | 시스템 상태 스냅샷 | 텍스트 |
| `/journal [symbol]` | 거래 저널 | 텍스트 |
| `/attribution` | 신호 성과 속성 | 텍스트 |
| `/settings` | 설정 조회 | 텍스트 |
| `/price [symbol]` | 실시간 시세 | 텍스트 |
| `/news [symbol]` | 관련 뉴스 | 텍스트 |
| `/analyze [symbol]` | 종목 분석 | 텍스트 |
| `/signal [symbol]` | 신호 상세 | 텍스트 |

`TELEGRAM_BOT_TOKEN` 환경변수 미설정 시 시뮬레이션 모드로 동작.

### 5.5 대시보드 (Plotly Dash, v4.2)

**파일**: `web/dashboard.py`

`python run_dashboard.py` → http://127.0.0.1:5000
- 포트폴리오 가치 추이
- 일일 수익률 분포
- 리스크 메트릭 요약
- 현재 포지션

---

## 6. 아키텍처 패턴

### 6.1 이벤트 버스 (EventBus)

**파일**: `utils/event_bus.py`

| 이벤트 | 발행자 | 구독자 |
|--------|--------|--------|
| `market_data` | MarketDataHandler | order_management, risk_manager, strategy_engine |
| `news_sentiment` | NLPEngine | strategy_engine |
| `strategy_signal` | strategy_engine | order_management |
| `order_executed` | order_management | portfolio, risk_manager |
| `position_closed` | order_management | portfolio |
| `error` | 모든 컴포넌트 | error_handler |
| `system_state` | trading_system | telegram_bot, dashboard |

`emit()`은 **fire-and-forget**으로, 구독자 예외를 발행자에게 전파하지 않음.

### 6.2 Circuit Breaker

**파일**: `data_layer/market_data.py:MarketDataHandler._fetch_yf_with_retry()`

yfinance 호출 실패 시 지수 백오프 재시도 (tenacity) + 5연속 실패 시 Circuit Breaker:
- OPEN 상태: 즉시 실패 반환 (추가 호출 차단)
- `CIRCUIT_RESET_TIMEOUT = 300`초 후 HALF_OPEN
- HALF_OPEN에서 1회 성공 시 CLOSED, 실패 시 OPEN 유지

### 6.3 Broker Protocol 인터페이스

**파일**: `broker/protocol.py`

7개 증권사가 구현해야 하는 인터페이스:
```python
class BrokerProtocol(ABC):
    async def connect(self) -> bool
    async def get_account_info(self) -> AccountInfo
    async def get_positions(self) -> List[Position]
    async def place_order(self, order: Order) -> OrderResult
    async def cancel_order(self, order_id: str) -> bool
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def get_real_time_price(self, symbol: str) -> PriceInfo
    async def disconnect(self) -> None
```

### 6.4 의존성 주입 (Factory)

**파일**: `core/factory.py:SystemFactory.create_default_components()`

시스템 부트스트랩을 단일 진입점으로 통일:
```python
components = {
    "market_data": MarketDataHandler(...),
    "nlp_engine": NLPEngine(),
    "strategy_engine": HybridStrategyEngine(...),
    "order_management": OrderManagementSystem(...),
    "portfolio": PortfolioManager(...),
    "risk_manager": RiskManager(...),
    "optimization_engine": OptimizationEngine(...),
    "broker_manager": MultiBrokerManager(...),
    "telegram_bot": TelegramBotEngine(...),
    "dashboard": ...,
}
```

---

## 7. 성과 최적화

### 7.1 슬리피지 + 수수료 + 시장임팩트

**파일**: `analysis/backtest_engine.py:BacktestEngine`

```python
slippage_pct = 0.001     # 0.1% 슬리피지
fee_pct = 0.001          # 0.1% 수수료
market_impact_pct = 0.0005  # 0.05% 시장임팩트

# 실행 가격 = 신호 가격 × (1 ± total_cost)
total_cost = slippage_pct + fee_pct + market_impact_pct
exec_price = price * (1 + total_cost) if buy else price * (1 - total_cost)
```

### 7.2 리스크 패리티 (Risk Parity)

**파일**: `trading_system.py:_compute_concentration_check()`, `core/risk_parity.py`

상관관계를 고려한 포지션 한도:
```python
for pair in position_pairs:
    if corr_matrix.loc[sym1, sym2] > 0.70:
        combined_pct = w1 + w2
        if combined_pct > correlation_limit_pct:
            # 초과분만큼 모든 포지션 비례 축소
```

---

## 8. LLM 통합

**파일**: `ai/openai_adapter.py`, `ai/gemini_adapter.py`

OpenAI / Gemini API를 통한 시장 의견 조회:
- `LLMProvider` 추상 클래스 기준 `analyze_market()`, `get_trading_signal()` 구현
- `LLMClientConfig`로 프롬프트/모델/온도 설정
- `LLMResponse`로 결과 수신 (signal + rationale + confidence)
- OpenAI는 `gpt-4` (또는 `gpt-4o-mini`), Gemini는 `gemini-pro` (또는 `gemini-2.0-flash`) 기본
- API 키 미설정 시 중립 신호(0.5) 반환

---

## 9. ML / RL 통합

**파일**: `analysis/ml_predictor.py`, `analysis/rl_trader.py`, `ai/rl_trading.py`

- **ML 예측기**: LSTM 기반 다음날 종가 방향 예측 (TensorFlow/Keras). 과거 60일 시퀀스 입력.
- **RL 에이전트**: DQN (Deep Q-Network). `TradingEnvironment`와 상호작용하며 정책 학습.
  - 상태: 가격, 보유량, 현금, MACD, RSI
  - 행동: 매수(+1) / 홀드(0) / 매도(-1)
  - 보상: 포트폴리오 가치 변화율
- `rl_trading.py`는 얇은 래퍼로 외부 `TradingEnvironment`에 의존 (테스트 호환용)

---

**마지막 업데이트**: 2026-06-08

# 고급 기능 설명서 - ADVANCED FEATURES

본 문서는 `D:\Finance\code\stock\trading_system\docs\`가 실제로 구현하고 있는 **30+ 고급 기능**을 기능별로 설명합니다. 각 섹션은 **기능 설명, 구현 위치, 정책(또는 수식), 사용 방법** 순서로 구성됩니다.

---

## 1. 신호 시스템

### 1.1 신호 합의 점수 (Signal Consensus Scoring, v4.0)

**목적**: 8개 신호의 방향성 일치도를 측정하여 신뢰도를 증폭 또는 감쇠합니다.

**파일**: `trading_system.py:_on_strategy_signal()`

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

### 1.3 적응형 가중치 (Adaptive Weights)

**파일**: `core/strategy_engine.py:HybridStrategyEngine._adapt_weights()`

최근 15개 신호의 정확도를 기반으로 각 신호 가중치를 동적으로 조정합니다:
- 정확도가 높은 신호의 가중치를 증가시키고 낮은 신호를 감소시킵니다.
- 변화율은 `weight_adaptation_rate = 0.05`로 제한하여 급격한 변동을 방지합니다.

---

## 2. 주문 및 실행

### 2.1 다중 증권사 분산 주문 (Distributed Order, v1.0)

**파일**: `core/distributed_order.py:DistributedOrderManager`

단일 대량 주문을 7개 증권사로 분할하여 시장 임팩트를 완화:
- `min_order_size = 1,000,000`원 이상이면 자동 분할
- Kiwoom 20% / Daishin 15% / Hanwha 15% / K.Invest 20% / Mirae 15% / NH 15%
- 각 broker에 개별 `PlaceOrderJob` 전송

### 2.2 지정가 주문 (Limit Order Entry, v2.0)

**파일**: `trading_system.py:_create_and_submit_order()`

시장가 대신 호가 스프레드 내 지정가로 주문하여 체결 품질 개선:
```python
price = bid + (ask - bid) * 0.3  # 스프레드의 30% 지점
```
단, 긴급 청산(손절/포지션청산)은 시장가 유지.

### 2.3 트레일링 스탑 (Trailing Stop, v4.0)

**파일**: `trading_system.py:_update_trailing_stops()`

**파라미터**: `trail_pct = 0.04` (상태에 따라 가변 적용)

모든 오픈 포지션을 순회하며:
1. 현재가가 `Position.highest_price`보다 높으면 워터마크 갱신
2. 새 워터마크 기준으로 `trigger_price = highest_price × (1 - trail_pct)` 계산
3. 기존 STOP_LOSS 주문의 `trigger_price` 필드를 직접 갱신 (재생성 불필요)

### 2.4 부분 익절 (Partial Take-Profit, v4.2)

**파일**: `trading_system.py:_create_and_submit_order()`

ATR 기반 3-티어 분할 익절로 단일 TP 대비 성능 개선:

| 티어 | ATR 배수 | 할당 비율 |
|------|---------|----------|
| 1차 | 1.5× ATR | 33% |
| 2차 | 3.0× ATR | 33% |
| 3차 | 5.0× ATR | 34% |

각 티어가 체결될 때마다 나머지 티어의 수량을 자동 조정합니다.

### 2.5 모의 투자 체결 감시 (Mock Trading Order Monitor)

**파일**: `trading_system.py:_monitor_broker_orders()`

- `mock_trading` 설정 활성화 시 실제 브로커 커넥터로 주문 전송
- 발급받은 `broker_order_id`를 기반으로 백그라운드 태스크에서 체결 상태(FILLED / EXECUTED / CANCELLED)를 3초마다 폴링
- 실시간으로 체결이 확인되면 로컬 포트폴리오 자산을 즉시 동기화

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

**파일**: `trading_system.py:_compute_portfolio_correlation()`

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
- 신호별로 실제 체결된 거래와 매핑하여 PnL 누적
- 각 사이클 시작 시 초기화되므로 장기 실행 시 과거 데이터 유실

### 4.2 거래 저널 (Trade Journal, v4.0)

**파일**: `trading_system.py:_log_trade_event()`

모든 트레이딩 이벤트를 메모리 큐에 저장:
- `get_trade_journal(limit=50)`로 최근 N개 조회
- 이벤트 타입: `order_submitted`, `stop_triggered`, `trailing_stop_updated`, `stop_placed`, `tp_triggered`, `position_closed`, `portfolio_liquidated`, `order_rejected`, `rebalance_completed`, `state_saved`

### 4.3 포트폴리오 분석 (Portfolio Analytics, v4.0)

**파일**: `trading_system.py:PortfolioAnalytics`

- 샤프 지수(Sharpe Ratio), 소르티노 지수(Sortino Ratio), 칼마 지수(Calmar Ratio) 실시간 계산
- 일일 변동성 및 최대 낙폭(MDD) 집계

### 4.4 상태 자동 저장 (State Auto-Save, v4.1)

**파일**: `trading_system.py:_auto_save_state()`

`state_save_interval_seconds = 3600` (1시간)마다:
- `state_snapshot.json`에 자산, 보유 종목, 주문 스냅샷 저장
- 시작 시 복원 루프 내장

---

## 5. 데이터 및 외부 연동

### 5.1 어닝 분석 (Earnings Analyzer, v4.2)

**파일**: `ai/earnings_analyzer.py:EarningsAnalyzer`

- 실적 발표 텍스트 및 가이던스를 분석하여 감정 점수 추출
- 실적일 기준 ±5일은 포지션 크기 50% 자동 축소 (Earnings Gapper Protection)

### 5.2 리밸런싱 스케줄러 (v4.1)

**파일**: `trading_system.py:_check_rebalance_schedule()`

`rebalance_interval_hours = 168` (7일)마다 자동 리밸런싱을 트리거하여 포트폴리오 비중을 재조정합니다.

### 5.3 감정 분석 (NLP Engine)

**파일**: `data_layer/nlp_engine.py:NLPEngine`

한글 및 영문 키워드 사전을 활용하여 뉴스 센티먼트(-1.0 ~ 1.0)를 산출합니다.

### 5.4 텔레그램 봇 (Telegram Bot, 18+ 명령어)

**파일**: `telegram_bot/telegram_bot_engine.py:TelegramBotEngine`

- `/status`, `/balance`, `/positions`, `/performance`, `/risk`, `/trade`, `/state` 등 지원
- `TELEGRAM_BOT_TOKEN` 미설정 시 시뮬레이션 모드로 안전 기동

### 5.5 대시보드 (Plotly Dash, v4.2)

**파일**: `web/dashboard.py`

포트폴리오 추이, 일일 수익률 분포, 종목 비중 파이차트 등을 실시간 렌더링.

---

## 6. 아키텍처 패턴

### 6.1 이벤트 버스 (EventBus)

**파일**: `utils/event_bus.py`

`market_data`, `news_sentiment`, `strategy_signal`, `order_status` 등 5가지 주요 이벤트를 비동기로 중개합니다.

### 6.2 Circuit Breaker

**파일**: `data_layer/market_data.py:MarketDataHandler._fetch_yf_with_retry()`

yfinance 호출 실패 시 지수 백오프 재시도 및 5회 연속 실패 시 Circuit Breaker 차단.

### 6.3 의존성 주입 (Factory)

**파일**: `core/factory.py:SystemFactory.create_default_components()`

모든 의존성을 팩토리 클래스 단일 진입점에서 통일하여 주입합니다.

---

## 7. 최적화 및 적응형 최적화기 (Adaptive Parameter Optimizer)

### 7.1 슬리피지 + 수수료 + 시장임팩트

**파일**: `analysis/backtest_engine.py:BacktestEngine`

```python
exec_price = price * (1 + total_cost)  # 매수 시
```

### 7.2 적응형 파라미터 최적화기

**파일**: `analysis/adaptive_optimizer.py:AdaptiveParameterOptimizer`

- **TPE (Tree-structured Parzen Estimator) 샘플러**를 이용해 베이지안 최적화 실행
- 시장 환경 변화에 따라 임계값 및 가중치를 자동으로 탐색하고 `data/adaptive_params.json`에 캐싱
- Sharpe 비율 감소, MDD 초과 또는 VIX 급등 시 스케줄러(`OptimizationScheduler`)가 최적화를 동적으로 자동 트리거

---

## 8. LLM 통합

**파일**: `ai/llm_integration.py` (과거 `openai_adapter.py` 및 `gemini_adapter.py`를 통합)

**지원 제공자 및 모델**:
- **OpenAI**: `gpt-4o-mini`, `gpt-4` 등
- **Google Gemini**: `gemini-1.5-flash`, `gemini-2.0-flash` 등
- **DeepSeek**: `deepseek-chat` (V3), `deepseek-reasoner` (R1) 지원 (OpenAI 호환 엔드포인트 `https://api.deepseek.com` 연동)

---

## 9. ML 앙상블 (Machine Learning Ensemble)

**파일**: `analysis/ml_engine.py`

- **Random Forest + XGBoost 50:50 Ensemble**: 두 모델의 예측 클래스 확률값을 소프트 보팅(Soft Voting)하여 가중 평균으로 최종 ML 점수(`ml_score`) 도출
- **24개 입력 피처**: 일별 수익률, SMA 이격도, RSI, MACD, 볼린저밴드 이격도, ATR, 거래량 변동률, 갭 비율, 일중 변동폭, ROC, 전고점/전저점 돌파 여부, 52주 고점 대비 거리 등
- **HMM Market Regime**: `hmmlearn` 라이브러리를 활용해 3상태 Hidden Markov Model을 학습하고, 탐지된 레짐(`hmm_regime`)을 ML 피처로 피드백
- **자동 학습**: 20번의 거래마다 자동으로 앙상블 모델 학습 수행
- **DQN RL Agent**: `src/ai/rl_trader.py`를 활용해 가치 평가 및 최적 액션을 탐색

---

**마지막 업데이트**: 2026-06-11

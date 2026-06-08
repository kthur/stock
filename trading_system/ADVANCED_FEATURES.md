# 고급 기능 가이드 (Advanced Features)

> 본 문서는 `IMPLEMENTATION_GUIDE.md`에서 다루지 않은 알고리즘/분석/AI/UX 기능을
> 코드 레퍼런스(`파일:라인`)와 함께 정리합니다.

---

## 1. 위험 관리 (Risk Management) — `src/risk/risk_manager.py`

### 1.1 Kelly Criterion 포지션 사이징

```python
# risk_manager.py:139-156
def calculate_kelly_fraction(self, win_rate, win_loss_ratio, half_kelly=True):
    """켈리 기준: f* = (p*b - q) / b, half-Kelly 기본 적용"""
```

- **입력**: 최근 50건의 `win_rate` (`OptimizationEngine.last_win_rate`),
  `win_loss_ratio` (`last_profit_factor`).
- **출력**: 0~1 사이 비율, `calculate_position_sizing()`에서 현금 한도와 결합해
  최종 수량 산출.

### 1.2 ATR 기반 손절/익절

```python
# risk_manager.py:75-81
def calculate_atr_based_stop(self, entry_price, atr):   # entry - 2*ATR
def calculate_atr_based_target(self, entry_price, atr): # entry + 4*ATR
```

- ATR(14) 데이터는 `MarketDataHandler.fetch_historical_data()` 결과(`PriceBar`)에서
  표준 ATR 공식을 사용해 직접 계산해야 함. 현재 `_create_and_submit_order()`에서
  ATR을 사용한 동적 손절/익절이 적용됨 (trading_system.py:246-276).

### 1.3 VIX 스케일링

```python
# risk_manager.py:83-94
def _volatility_scalar(self, vix=20.0):
    """VIX 구간별 포지션 스케일
    VIX 40+  → 0.25x
    VIX 30-40 → 0.5x
    VIX 20-30 → 1.0x (기준)
    VIX 15-20 → 1.1x
    VIX 12-15 → 1.25x
    """
```

- `AlternativeDataClient.fetch_vix()` (alt_data.py:18)가 `^VIX`를 yfinance에서
  조회해 캐싱.

### 1.4 상관관계 리스크

```python
# risk_manager.py:259-280
def update_correlation(symbol_a, symbol_b, correlation)  # 상관계수 기록
def _calculate_correlation_risk(symbols)                  # 평균 |corr| 산출
def calculate_risk_level(positions)                       # LOW/MEDIUM/HIGH/CRITICAL
```

- 두 종목의 상관계수가 0.7 이상이면 동일 섹터 집중으로 보고 리스크 레벨을 한 단계
  상향 조정.

### 1.5 VaR / CVaR

```python
# risk_manager.py:299-325
def calculate_var(returns, confidence=0.95)   # Historical VaR
def calculate_cvar(returns, confidence=0.95)  # Expected Shortfall
```

- 손실 분포의 5% 분위수 / 5% 이하 평균 손실.

### 1.6 Drawdown 모니터링

```python
# risk_manager.py:217-235
def update_portfolio_value(new_value)
def calculate_drawdown() -> float   # (peak - current) / peak
```

- `max_portfolio_loss_pct` (10%) 초과 시 `RiskLevel.HIGH` 이상.

### 1.7 리스크 리포트

```python
report = system.get_risk_report()
# {
#   "drawdown": 0.04,
#   "risk_level": RiskLevel.LOW,
#   "alerts": [...],
#   "var_95": -0.025,
#   "cvar_95": -0.038,
#   "correlation_risk": 0.32,
#   "volatility_scalar": 1.0
# }
```

---

## 2. 자동 손절/익절 (Stop Loss / Take Profit)

> 본 PR 신규 구현 — `IMPLEMENTATION_GUIDE.md` §4 참고

### 2.1 핵심 API

| 메서드 | 위치 | 역할 |
|--------|------|------|
| `OrderManagementSystem.create_stop_loss_order()` | `order_management.py:176` | 손절 주문 생성 |
| `OrderManagementSystem.create_take_profit_order()` | `order_management.py:191` | 익절 주문 생성 |
| `OrderManagementSystem.check_and_trigger_stop_orders()` | `order_management.py:206` | 가격 도달 시 발동 |
| `OrderManagementSystem.get_stop_orders()` | `order_management.py:236` | 활성 SL/TP 목록 |
| `OrderManagementSystem.cancel_stop_orders()` | `order_management.py:243` | 일괄 취소 |
| `trading_system._on_market_data()` | `trading_system.py:124` | 시세 콜백 + SL/TP 검사 |
| `trading_system._execute_stop_order()` | `trading_system.py:142` | 발동 시 시장가 체결 |

### 2.2 데이터 모델

```python
@dataclass
class Order:
    order_id: str
    symbol: str
    order_type: OrderType  # BUY / SELL / STOP_LOSS / TAKE_PROFIT
    quantity: int
    price: float
    trigger_price: float | None = None  # SL/TP 발동 가격
    parent_order_id: str | None = None  # 진입 주문 ID
    status: OrderStatus
```

### 2.3 실행 시퀀스

```
1. _on_strategy_signal() → _create_and_submit_order()
2. 진입가 P 기준
   SL_trigger = P × (1 - stop_loss_pct)
   TP_trigger = P × (1 + take_profit_pct)
3. SL/TP 두 주문 PENDING 상태로 저장
4. 시장 데이터 도착 → _on_market_data()
5. check_and_trigger_stop_orders(symbol, current_price)
   - 현재가가 SL_trigger 이하 → SL 발동 (BUY 포지션)
   - 현재가가 TP_trigger 이상 → TP 발동
6. _execute_stop_order()
   - order_management.execute_order() → 시장가 체결
   - portfolio.reduce_position()
   - 텔레그램 알림
```

### 2.4 숏 포지션 반전

`order_type == SELL`인 경우 SL/TP 방향 반전:
- 손절 = 위 (가격 상승 시)
- 익절 = 아래 (가격 하락 시)

코드는 `trading_system.py:264-272` 참고.

---

## 3. 전략 엔진 (Hybrid Strategy Engine) — `src/core/strategy_engine.py`

### 3.1 7-시그널 가중합

```python
# strategy_engine.py:32-87
class HybridStrategyEngine:
    def __init__(self):
        self.weights = {
            "technical": 0.25,  # RSI / MACD / MA
            "sentiment": 0.20,  # NLPEngine 결과
            "ml": 0.20,         # MLEngine 예측
            "rl": 0.20,         # RLEngine 적응형 임계값
            "darkpool": 0.05,   # DarkPoolTracker (현재 중립)
            "llm": 0.10,        # LLMEngine InvestmentOpinion
            "global_market": 0.10,  # 글로벌 지수/환율
        }
```

### 3.2 기술 지표

- **RSI(14)**: `strategy_engine.py:_compute_rsi()` — Wilder smoothing
- **MACD(12, 26, 9)**: EMA 차이, 시그널 = EMA(MACD, 9)
- **이동평균**: 5/20 크로스

### 3.3 동적 가중치 적응

```python
# strategy_engine.py:296-351
def record_signal_outcome(signal_name, was_correct)  # 신호별 정답 기록
def _adapt_weights()                                  # 50-거래 윈도우로 가중치 재계산
```

- 정답률 낮은 신호는 가중치를 줄이고, 높은 신호는 늘림.
- L2 정규화로 가중치 합 1 유지.
- `weight_map`에 `"global_market": "global_market_weight"` 포함.

### 3.4 OptimizationEngine

```python
# strategy_engine.py:353-419
class OptimizationEngine:
    def record_trade_result(signal, entry, exit, slippage)
    def get_win_rate() -> float
    def get_avg_slippage() -> float
    def optimize_parameters() -> Dict
```

- 최근 100건 거래의 승률/평균 슬리피지를 계산해 `HybridStrategyEngine` 가중치 적응
  트리거.

### 3.5 유서 깊은 투자자 전략

```python
# strategy/famous_investors.py (451줄)
BuffettStrategy.analyze(stock_data)      # 가치투자: P/E, ROE, 부채비율
LynchStrategy.analyze(stock_data)        # 성장주: PEG, earnings growth
MinervaStrategy.analyze(stock_data)      # 알파: 다중 팩터 종합
DividendStrategy.analyze(stock_data)     # 배당: yield, payout ratio
```

- `InvestorStrategyEngine.analyze_all_strategies(stock_data)` → 모든 전략 일괄 실행.
- `get_consensus_recommendation()` → 다수결 + 가중 신뢰도 합산.

---

## 4. 포트폴리오 최적화 (Quantum/Mean-Variance Optimizer)

> `src/analysis/quantum_optimizer.py`는 명칭은 "Quantum"이지만 구현은
> **고전 Markowitz Mean-Variance + Risk-Parity**입니다 (numpy 선형대수).

### 4.1 Mean-Variance Optimization

```python
# quantum_optimizer.py:14-63
def optimize_allocation(symbols, current_weights, expected_returns, cov_matrix):
    """Markowitz 1952.
    weights = Σ^-1 (λμ + γ1) / sum
    조건: weights >= 0, sum(weights) = 1
    """
```

- 공분산 행렬이 특이행렬에 가까우면 ridge regularization(`eye × 0.001`).

### 4.2 Risk-Parity

```python
# quantum_optimizer.py:65-90
def risk_parity_allocation(symbols, cov_matrix):
    """w_i ∝ 1/σ_i  (각 종목의 위험 기여도를 균등하게)"""
```

### 4.3 공분산 계산

```python
# quantum_optimizer.py:92-99
def compute_covariance(historical_returns: Dict[symbol, List[float]]) -> np.ndarray
```

- 길이가 다른 시리즈는 자동으로 최소 길이에 맞춰 절단.

### 4.4 자산 배분 전략 (`src/strategy/asset_allocation.py`)

```python
# asset_allocation.py:54-178
AssetAllocator(strategy="equal_weight" | "risk_parity" | "momentum")
.equal_weight(tickers)              # 동일 가중
._risk_parity(price_data)           # 1/σ 가중 (자산별 편차/변동성)
._momentum(price_data)              # 과거 대비 수익 모멘텀 순위 배분
```

- **상세 알고리즘**:
  1. **데이터 전처리**: 다변량 시계열 가격 데이터(`Dict[str, List[float]]`) 수집 후 결측치(`NaN`/`Inf`) 필터링, 최소 2종목 이상 확보.
  2. **위험 평가 (Risk-Parity 기준)**: 각 종목의 수익률 시계열의 표준편차($\sigma_i$) 계산. 역변동성($1 / \sigma_i$)을 할당 비중의 기초값으로 설정하여 고위험 자산의 비중을 낮춤.
  3. **모멘텀 평가 (Momentum 기준)**: 최근 N일(보통 20일)의 수익률 $R_i = (P_{today} - P_{N}) / P_{N}$ 을 계산 후 상위 랭킹 순으로 가중치 차등 부여.
  4. **정규화(Normalization)**: $w_i = \frac{\text{raw\_weight}_i}{\sum \text{raw\_weight}_j}$ 연산을 통해 부동소수점 오차 누적을 방지하며 합계가 1.0(100%)이 되도록 강제. (마지막 자산에 잔차 반영)

---

## 5. RL/ML/AI 스택

### 5.1 휴리스틱 RL 분석 엔진 (`src/analysis/rl_engine.py`)

> 명칭은 "RL"이지만 실제 구현은 **적응형 임계값 휴리스틱**입니다.

```python
# analysis/rl_engine.py:41-110
def get_action(state_features) -> {action, confidence}
def record_outcome(action, pnl_pct)  # 학습 데이터 누적
def _adapt_thresholds()              # win_rate 기반 VIX/RSI 임계값 조정
```

- 신경망 대신 과거 트레이딩 승률 및 수익/손실(Win/Loss) 기록을 피드백 루프로 삼아, VIX나 RSI 같은 정적 지표의 매수/매도 임계값을 동적으로 적응시키는 룰 기반 엔진(`RLEngine`)입니다.

### 5.2 DQN 모델 (`src/ai/rl_trader.py`)

```python
# PyTorch 기반 DQN, 외부 SB3 의존성 없음
TradingEnvironment(prices)           # 상태: [price_norm, position, pnl]
DQNAgent(state_dim, action_dim)      # Q-Network + ReplayBuffer + ε-greedy
agent.train(env, episodes=5)
```

- **상세 알고리즘**:
  1. **State(상태)**: 직전 가격 변화율(Price Norm), 현재 보유 포지션 여부, 현재 누적 수익률(PnL).
  2. **Action(행동)**: 0(Buy), 1(Hold), 2(Sell)의 3가지 이산 행동 공간.
  3. **Reward(보상)**:
     - 수익 청산 시: 양의 보상 (수익률 비례)
     - 손실 청산 시: 음의 보상 (손실률 비례)
     - 장기 보유 시: 기회비용 반영 위한 미세 페널티
  4. **Q-Learning 업데이트**: 타겟 네트워크와 메인 네트워크 분리. 벨만 방정식 $Q(s,a) = r + \gamma \max_{a'} Q(s', a')$을 바탕으로 손실함수(MSE)를 구성해 PyTorch 옵티마이저로 역전파.

### 5.3 PPO 기반 트레이딩 (`src/ai/rl_trading.py`)

```python
# rl_trading.py (SB3 PPO 통합 래퍼)
DummyTradingEnv(data)                # Gymnasium 5-튜플 step API
train_rl_model(data)                 # SB3 PPO 사용, 없으면 in-house DQN fallback
```

- 시스템의 일차적인(Primary) RL 모델로, `gymnasium` 커스텀 환경 위에서 `stable-baselines3`의 PPO 알고리즘을 훈련합니다.

### 5.4 LLM 통합 (`src/ai/llm_integration.py`, 430줄)

```python
# OpenAI / Google Gemini 지원
LLMEngine(api_key=None, model=None, provider=None)
.query_investment_opinion(stock_data)  # → InvestmentOpinion (sentiment, target_price, confidence)
.batch_query_stocks(stocks_data)       # 병렬 호출
._simulate_response(stock_data)        # API 키 없을 때 결정적 모의 응답
```

- `query_investment_opinion()`이 `HybridStrategyEngine`의 `llm` 컴포넌트로 주입됨.

### 5.5 어닝 분석 (`src/ai/llm_earnings_agent.py`)

```python
# 키워드 매칭 (Mock LLM)
LLMEarningsAgent(llm_engine).analyze_earnings_call(symbol, transcript)
→ {sentiment_score, is_earnings_beat, guidance, key_driver}
```

- 실제 LLM 호출은 `llm_engine`에 위임하도록 확장 가능.

### 5.6 감성 분석 (Sentiment Analysis)

- **자체 사전 엔진 (`src/ai/sentiment.py`)**: `SentimentAnalyzer` 클래스가 텍스트를 토큰화합니다.
  1. 텍스트 내 부정어(Negation, 예: "not", "rarely")를 탐지해 반경(window) 내 단어들의 극성을 역전시킵니다.
  2. 강조어(Intensifier, 예: "very", "extremely")를 탐지해 가중치를 곱합니다.
  3. `POSITIVE_WORDS`와 `NEGATIVE_WORDS` 출현 빈도를 점수화하여 최종 $x$ 산출.
  4. $score = \tanh(x)$ 정규화를 통해 -1.0 ~ 1.0 범위의 긍정/부정 스코어 도출.
- **LLM 의견 통합 (`src/ai/llm_integration.py` / `src/ai/llm_earnings_agent.py`)**: LLM 프롬프트를 통해 비정형 텍스트(실적 발표 등)의 맥락을 이해하고 추가 구조화된 딕셔너리로 변환해 점수를 보완합니다.
- **아키텍처 제약사항**: 도출된 감성 점수는 전적으로 분석 파이프라인에서만 사용되며, `src/core/strategy_engine.py`(`HybridStrategyEngine`)를 거쳐 가중 통합됩니다. 증권사 체결 모듈(`real_broker.py` 등)은 최종 `TradeSignal` 에만 반응합니다.

### 5.7 HMM 및 ML 엔진 (`src/analysis/ml_engine.py`)

```python
# scikit-learn / XGBoost / LightGBM / HMM / Optuna (선택 의존성)
MLEngine()
.fit(features, targets)         # 분류/회귀 모델 학습
.predict(features)              # 확률/값 예측
```
- **HMM(은닉 마르코프 모델)**: `GaussianHMM(n_components=3)`을 이용해 시장을 강세장/약세장/횡보장이라는 숨겨진 3개의 상태(Hidden States)로 추정.
- **Optuna**: `TimeSeriesSplit`을 사용해 교차 검증을 수행하고, Tree-structured Parzen Estimator(TPE) 알고리즘으로 하이퍼파라미터 최적화.

---

## 6. 백테스트 & 통계

### 6.1 BacktestEngine (`src/analysis/backtest.py`, 1322줄)

```python
BacktestEngine(initial_capital, fee_pct=0.001, slippage_pct=0.001, market_impact_pct=0.0005)
.run_backtest(symbol, price_bars, strategy_func) → BacktestResult
.optimize_parameters(symbol, price_bars, param_grid) → 그리드 서치
```

**비용 모델** (모든 체결에 3중 적용):
1. `fee_pct`: 증권사 수수료 (0.1%)
2. `slippage_pct`: 시장가 주문의 가격 미끄러짐 (0.1%)
3. `market_impact_pct`: 대량 주문의 시장 충격 (0.05%)

### 6.2 AdvancedStatistics (`src/analysis/statistics.py`, 261줄)

```python
AdvancedStatistics()
.calculate_sharpe_ratio(returns, rf=0.02)   # 연환산
.calculate_sortino_ratio(returns, rf=0.02)  # 하방 위험만
.calculate_calmar_ratio(returns)            # CAGR / MDD
.calculate_hurst_exponent(prices)           # 추세 강도 (0.5 미만 = 평균회귀)
.calculate_var(returns, c=0.95)             # Historical VaR
.max_drawdown(equity_curve)                 # MDD
.volatility(returns)                        # 연환산 변동성
```

### 6.3 통계적 차익거래 (`src/core/stat_arb.py`)

```python
StatisticalArbitrageEngine()
.find_cointegrated_pairs(prices_dict: {symbol: List[float]}) → List[Pair]
# 방법: (1) correlation > 0.5 필터 → (2) OLS 회귀로 β 산출 →
#       (3) 잔차 시계열 z-score 계산 → (4) 평균회귀 후보 탐지
```

---

## 7. 텔레그램 봇 (`src/telegram_bot/bot_engine.py`, 574줄) (18종)

### 7.1 명령어 (18종)

| 명령 | 메서드 | 동작 |
|------|--------|------|
| `/start` | `_cmd_start` | 환영 메시지 + 도움말 |
| `/help` | `_cmd_help` | 사용 가능한 명령 안내 |
| `/status` | `_cmd_status` | 시스템 ON/OFF, 현금, 포지션 수 |
| `/portfolio` | `_cmd_portfolio` | 종목별 수량/평단/평가 |
| `/positions` | `_cmd_positions` | 보유 종목 간단 목록 |
| `/orders` | `_cmd_orders` | 미체결 + 최근 체결 |
| `/news` | `_cmd_news` | 최신 뉴스 헤드라인 |
| `/analyze` | `_cmd_analyze` | 특정 종목 전략 신호 |
| `/buy` | `_cmd_buy` | 매수 (인자: 종목 수량 가격) |
| `/sell` | `_cmd_sell` | 매도 (인자: 종목 수량 가격) |
| `/cancel` | `_cmd_cancel` | 주문 취소 (인자: 주문ID) |
| `/brokers` | `_cmd_brokers` | 등록된 7 증권사 상태 |
| `/connect` | `_cmd_connect` | 증권사 연결 (인자: 키 계좌) |
| `/risk` | `_cmd_risk` | VaR/드로다운/리스크 레벨 |
| `/strategy` | `_cmd_strategy` | 활성 전략 + 가중치 |
| `/performance` | `_cmd_performance` | 승률/손익/드로다운/리스크 |
| `/global` | `_cmd_global` | 글로벌 지수 + 환율 현황 |
| `/screen` | `_cmd_screen` | 상대 강도 스크리닝 (min_corr 필터 지원) |

### 7.2 시뮬레이션 모드

- `TELEGRAM_BOT_TOKEN` 환경변수가 없으면 `simulation_mode = True`.
- `process_message(user_id, message)`를 직접 호출해 로컬에서 명령 테스트 가능.

### 7.3 알림

```python
notification_text = bot.get_notification(event_type, data)
# event_type: "stop_loss" | "take_profit" | "order_filled" | "news_alert"
```

---

## 8. Plotly Dash 대시보드 (`src/web/dashboard.py`, 177줄)

Plotly Dash single-page app (177 lines). Routes: `/` (main dashboard), `/api/*` (minimal REST for live data).

### 8.2 WebSocket 메시지

- `ping` → `pong` (JSON)
- `subscribe` → `portfolio` / `orders` / `market` 채널 구독
- `broadcast_portfolio_update()` → 전체 클라이언트에 푸시

### 8.3 미니앱

- PWA 지원 (Service Worker + Manifest)
- 모바일 친화적 UI (HTML 인라인 임베디드)

---

## 9. 시장 데이터 & 대체 데이터

### 9.1 MarketDataHandler (`src/data_layer/market_data_handler.py`, 279줄)

- **RateLimiter**: 초당 호출 횟수 제한
- **CircuitBreaker**: 연속 실패 시 호출 차단 (5회 / 60초)
- **tenacity 재시도**: yfinance 호출 시 지수 백오프
- `simulate_api_call()`: 시뮬레이션 데이터 생성
- `fetch_live_data()`: yfinance 단일 시세
- `fetch_historical_data(period)`: `1mo` / `1y` / `10y` 등

### 9.2 AlternativeDataClient (`src/data_layer/alt_data.py`, 107줄)

```python
.fetch_vix()                  # ^VIX (yfinance)
.fetch_fear_and_greed_proxy() # SPX 20일 모멘텀 기반 자체 계산
._fetch_spx_trend()           # ^GSPC 50/200 MA 비교
._detect_volatility_regime()  # VIX → "low"/"normal"/"elevated"/"high"/"extreme"
.get_market_regime()          # {vix, spx_trend, vol_regime, regime_score}
```

`regime_score`는 -1(극단 공포) ~ +1(극단 탐욕)이며, `HybridStrategyEngine`이
가중치 동적 적응에 사용.

### 9.3 DarkPoolTracker (`src/data_layer/darkpool_tracker.py`)

- 현재는 **중립값 반환** (데이터 소스 부재로 의도적 no-signal).
- `OnChainTracker.fetch_whale_movement()`도 중립값.

### 9.4 MarketScanner (`src/analysis/market_scanner.py`)

```python
MarketScanner()
._get_top_krx_stocks()    # KRX 시총 상위 30종목 (FinanceDataReader)
.scan_market()            # → {symbol, name, price, change_pct, volume}
```

---

## 10. 멀티 브로커 (`src/broker/`)

### 10.1 지원 증권사 (7종)

| Enum | 클래스 | 비고 |
|------|--------|------|
| `BrokerType.KIWOOM` | `KiwoomConnector` | 메인 (factory 기본값) |
| `BrokerType.DAISHIN` | `DaishinConnector` | |
| `BrokerType.HANWHA` | `HanwhaConnector` | |
| `BrokerType.KOREA_INVESTMENT` | `KoreaInvestmentConnector` | |
| `BrokerType.MIRAE_ASSET` | `MiraeAssetConnector` | |
| `BrokerType.NH` | `NHConnector` | |
| `BrokerType.LS` | `LSConnector` | |

모두 `BrokerProtocol`을 구현하며, 기본은 `simulation_mode = True`로 즉시 체결
시뮬레이션.

### 10.2 MultiBrokerManager

```python
manager = MultiBrokerManager()
manager.connect(BrokerType.KIWOOM, "1234567890")
manager.switch_broker(BrokerType.MIRAE_ASSET)
manager.place_order("005930", 10, 70_000, "매수")
manager.get_all_broker_status()  # 7사 일괄 조회
```

### 10.3 새 증권사 추가 (5줄)

```python
# src/broker/my_broker.py
from .protocol import BrokerProtocol
class MyBrokerConnector(BrokerProtocol):
    def connect(self, account): return True  # simulation
    def place_order(self, code, qty, price, type): return f"sim-{code}"
    def cancel_order(self, order_id): return True
    def get_account_info(self): return {"cash": 0, "positions": {}}
    def is_connected(self): return False
```

`multi_broker_manager.py:42-50`의 `_init_brokers()`에 한 줄 추가하면 끝.

---

## 11. 영속성 (Persistence) — `src/persistence/database.py`

### 11.1 aiosqlite 비동기 DB

| 클래스 | DB 파일 | 테이블 |
|--------|---------|--------|
| `TradeLogger` | `trade_logs.db` | orders, executions |
| `AssetHistoryDB` | `asset_history.db` | snapshots |
| `AIPredictionDB` | `ai_predictions.db` | ai_predictions |

### 11.2 스키마 예시 (orders)

```sql
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT,
    order_type TEXT,    -- BUY/SELL/STOP_LOSS/TAKE_PROFIT
    quantity INTEGER,
    price REAL,
    trigger_price REAL,
    parent_order_id TEXT,
    status TEXT,        -- PENDING/SUBMITTED/FILLED/CANCELLED
    created_at TIMESTAMP,
    filled_at TIMESTAMP
);
```

---

## 12. 리포트 (`src/utils/`)

### 12.1 콘솔 리포트

```python
# utils/report_generator.py:13
ReportGenerator.generate_text_report(data) → str
# 예: "=== 트레이딩 시스템 리포트 ===\n일자: ...\n수익률: +5.2%\n..."
```

### 12.2 PDF 리포트

```python
ReportGenerator.generate_backtest_report(data, output_path="backtest.pdf")
# ReportLab Platypus 기반, 한글 미지원(영문 only)
```

### 12.3 스타일드 PDF (별도)

```python
# utils/pdf_report.py (320줄, 풀 기능)
generate_styled_pdf(trade_data, output_path)
# 색상, 표, 차트 포함. 다양한 리포트 타입 지원.
```

---

## 13. 에러 처리 (`src/utils/error_handler.py`)

```python
ErrorHandler(max_retries=3, retry_delay=1.0)
.retry_with_exponential_backoff(func, *args)        # 지수 백오프
.handle_transaction(transaction_func, rollback_func) # 2PC
.circuit_breaker(func, failure_threshold=5)          # 회로 차단기
.timeout(func, timeout_seconds=10)                   # 타임아웃
.validate_data(data, validator)                      # 데이터 검증
.register_error_callback(callback)                   # 알림 콜백
.get_error_summary()                                 # {by_severity, total, recent}
```

- `ErrorSeverity`: `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`.

---

## 14. 이벤트 버스 (`src/utils/event_bus.py`)

```python
bus = EventBus()
bus.subscribe("market_data", callback_a)  # 다중 구독자
bus.subscribe("market_data", callback_b)
bus.publish("market_data", market_data)  # 모든 구독자 순차 호출
```

**발행 이벤트**:
- `market_data` — 시세 도착
- `news_sentiment` — 뉴스 분석 완료
- `strategy_signal` — 매매 신호
- `account_sync` — 계좌 동기화 완료
- `order_status` — 주문 상태 변경

---

## 15. CI/CD 파이프라인 (`.github/workflows/test.yml`)

```yaml
1. checkout
2. setup-python 3.11
3. pip install -r requirements.txt
4. ruff check src tests      # 린트
5. mypy --strict src         # 타입 검사
6. pytest                    # 테스트
7. bandit -r src -ll         # 보안 정적 분석
8. pip-audit -r requirements.txt  # 의존성 CVE
```

---

## 16. 분산 매수/매도 (Distributed Orders)

- `DistributedOrderManager` in `src/core/distributed_order.py`
- 설명: 대량 주문을 N개 트렌치로 분할 (매수: 하락가 DCA, 매도: 상승가 이익실현)
- 각 트렌치별 개별 SL/TP 자동 생성
- 포트폴리오 대비 비율 기반 활성화 threshold

---

## 17. 알려진 한계 (요약)

- `quantum_optimizer.py`는 명칭만 양자, 구현은 고전 Markowitz
- `darkpool_tracker.py`는 중립값 반환 (의도적 no-signal)
- `hft_engine.py`는 Cython/C++ Mock
- `rl_trading.py`는 SB3 호환 래퍼; 실전 학습은 `rl_trader.py` (DQN) 사용
- **증권사 연동**: 현재 `RealBroker` 클래스와 `kiwoom_server.py`, `korea_investment.py`를 통해 실제 API 연동 뼈대 및 연결(`connect()`, `submit_order()`)이 구축되어 테스트를 통과했습니다. 다만, 모의투자 환경을 넘어선 실계좌 체결 테스트는 사용자 로컬 환경의 인증서 및 추가 인가 작업이 필요합니다.

자세한 제약은 `IMPLEMENTATION_GUIDE.md §9` 참고.

---

**마지막 업데이트**: 2026-06-08
**검증 상태**: 코드와 1:1 매핑 확인됨

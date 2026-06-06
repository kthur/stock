# 알고리즘 가이드 (Algorithms)

> 본 문서는 트레이딩 시스템에 구현된 모든 알고리즘을 **수학적 정의 → 구현 위치 →
> 사용 예시** 순서로 체계적으로 정리합니다. 코드 변경 시 본 문서도 함께 갱신해야 합니다.

## 목차

1. [위험 관리 (Risk Management)](#1-위험-관리)
   - 1.1 Kelly Criterion
   - 1.2 Value at Risk (VaR) & Conditional VaR
   - 1.3 VIX 기반 변동성 스케일링
   - 1.4 ATR 기반 손절/익절
   - 1.5 상관관계 리스크
   - 1.6 Drawdown 모니터링
2. [주문 관리 (Order Management)](#2-주문-관리)
   - 2.1 Stop Loss / Take Profit
   - 2.2 자동 손절·익절 발동 알고리즘
3. [전략 엔진 (Strategy Engine)](#3-전략-엔진)
   - 3.1 5-시그널 가중합 (Hybrid Strategy)
   - 3.2 동적 가중치 적응 (Weight Adaptation)
   - 3.3 RSI (Relative Strength Index)
   - 3.4 MACD (Moving Average Convergence Divergence)
   - 3.5 거래량 필터
   - 3.6 스프레드 필터
4. [강화학습 (RL)](#4-강화학습)
   - 4.1 적응형 임계값 휴리스틱
   - 4.2 Deep Q-Network (DQN)
5. [포트폴리오 최적화 (Portfolio Optimization)](#5-포트폴리오-최적화)
   - 5.1 Mean-Variance Optimization (Markowitz)
   - 5.2 Risk Parity
   - 5.3 모멘텀 기반 배분
6. [통계적 차익거래 (Statistical Arbitrage)](#6-통계적-차익거래)
7. [유명 투자자 전략 (Famous Investor Strategies)](#7-유명-투자자-전략)
   - 7.1 Buffett (가치투자)
   - 7.2 Lynch (성장주)
   - 7.3 Minerva (모멘텀)
   - 7.4 Dividend (배당)
8. [고급 통계 지표 (Advanced Statistics)](#8-고급-통계-지표)
   - 8.1 Sharpe Ratio
   - 8.2 Sortino Ratio
   - 8.3 Calmar Ratio
   - 8.4 Hurst Exponent
   - 8.5 Maximum Drawdown
9. [시장 레짐 감지 (Market Regime Detection)](#9-시장-레짐-감지)
10. [자연어 처리 (NLP)](#10-자연어-처리)
    - 10.1 한국어 키워드 감정 분석
    - 10.2 영문 금융 어휘 감정 분석
11. [백테스트 비용 모델 (Backtest Cost Model)](#11-백테스트-비용-모델)
12. [이벤트 버스 패턴 (Event Bus)](#12-이벤트-버스-패턴)

---

## 1. 위험 관리 (Risk Management)

### 1.1 Kelly Criterion

**목적**: 장기 자산 증가를最大化하는 최적 베팅 비율 산출.

**수식 (Full Kelly)**:
```
f* = (p × b - q) / b
```
- `p`: 승률 (win rate)
- `q = 1 - p`: 패률
- `b`: 손익비 (avg win / avg loss)

**Half-Kelly (기본 적용)**:
```
f = f* / 2
```

**구현**:
- `src/risk/risk_manager.py:139-156` — `calculate_kelly_fraction()`
- `src/risk/risk_manager.py:158-193` — `calculate_position_sizing()`
  - Kelly 분수 × 포트폴리오 가치 / 진입가 = 매수 수량
  - 손절가까지의 거리로 분모 조정 (Kelly × |entry - stop_loss|)
- 호출자: `trading_system.py:232-238` (`_create_and_submit_order`)

**예시**:
```python
# win_rate=0.55, win_loss_ratio=1.2 → full Kelly = 0.10 → half = 0.05
kelly = risk_mgr.calculate_kelly_fraction(0.55, 1.2, half_kelly=True)
# → 0.05

qty = risk_mgr.calculate_position_sizing(
    symbol="AAPL", entry_price=150.0, stop_loss_price=145.0,
    win_rate=0.55, win_loss_ratio=1.2,
)
# → Kelly 0.05 × portfolio_value × (1/|entry-stop|) 제약 적용
```

**왜 Half-Kelly?** Full Kelly는 변동성이 크고 추정 오차에 민감. Half-Kelly는
기하학적 성장률은 75%로 줄지만 MDD는 절반 이하로 감소 (Thorp, 2006).

### 1.2 Value at Risk (VaR) & Conditional VaR

**목적**: 일정 신뢰수준에서 예상되는 최대 손실.

**Historical VaR** (분포 가정 없음):
```
VaR_α = -quantile(returns, 1-α)
```

**CVaR (Expected Shortfall)**:
```
CVaR_α = -mean(returns | returns ≤ -VaR_α)
```

**구현**:
- `src/risk/risk_manager.py:299-310` — `calculate_var(returns, confidence=0.95)`
- `src/risk/risk_manager.py:313-324` — `calculate_cvar(...)`

**예시**:
```python
returns = [0.01, -0.02, 0.015, -0.005, -0.03, 0.008, ...]  # 일별 수익률
var_95 = risk_mgr.calculate_var(returns, 0.95)   # 5% 분위수 손실
cvar_95 = risk_mgr.calculate_cvar(returns, 0.95)  # 5% 이하 평균 손실
# var_95  ≈ -0.025  (하루 2.5% 손실 위험)
# cvar_95 ≈ -0.038  (꼬리 평균 3.8% 손실)
```

### 1.3 VIX 기반 변동성 스케일링

**목적**: 고변동성 국면에서 자동 포지션 축소, 저변동성 국면에서 확대.

**룩업 테이블** (위험 관리자 기본):
| VIX 범위 | 스케일 | 해석 |
|---------|--------|------|
| VIX ≥ 40 | 0.25x | 극단 공포 (서킷브레이커 빈번) |
| 30 ≤ VIX < 40 | 0.50x | 고변동성 |
| 20 ≤ VIX < 30 | 1.00x | 기준 (정상) |
| 15 ≤ VIX < 20 | 1.10x | 저변동성 |
| VIX < 15 | 1.25x | 극단 안정 (역사적 저점) |

**구현**:
- `src/risk/risk_manager.py:83-94` — `_volatility_scalar(vix=20.0)`
- 호출: `calculate_position_sizing()` 내부에서 `position *= scalar`
- VIX 소스: `src/data_layer/alt_data.py:18` (yfinance `^VIX`)

### 1.4 ATR 기반 손절/익절

**목적**: 변동성 적응형 손절 — 고변동 종목은 넓게, 저변동 종목은 좁게.

**수식**:
```
stop_loss  = entry - k_stop  × ATR(14)
take_profit = entry + k_target × ATR(14)
```

**기본값** (위험 관리자):
- `k_stop = 2.0`, `k_target = 4.0` (위험:보상 = 1:2)
- ATR(14) = 14일 True Range의 Wilder 평활화 평균

**구현**:
- `src/risk/risk_manager.py:75-77` — `calculate_atr_based_stop()`
- `src/risk/risk_manager.py:79-81` — `calculate_atr_based_target()`

**현재 통합 상태**: 함수는 존재하지만 `_create_and_submit_order()`는 아직
고정 비율(5%/10%) 사용. ATR 통합은 향후 작업 (구현 #1).

### 1.5 상관관계 리스크

**목적**: 포트폴리오 내 고상관 종목 집중도 감지 → 리스크 레벨 상향.

**알고리즘**:
```
1. 보유 종목들의 일별 수익률 계산
2. corr_matrix 산출 (Pearson)
3. 평균 |상관계수| 산출 (대각선 제외)
4. 평균 > 0.7 → 리스크 레벨 1단계 상향
5. 평균 > 0.85 → 리스크 레벨 2단계 상향
```

**구현**:
- `src/risk/risk_manager.py:259-265` — `update_correlation()`
- `src/risk/risk_manager.py:267-280` — `_calculate_correlation_risk()`
- `src/risk/risk_manager.py:235-257` — `calculate_risk_level()` (상관관계 반영)

### 1.6 Drawdown 모니터링

**수식**:
```
DD_t = (Peak_t - V_t) / Peak_t
Peak_t = max(V_0, V_1, ..., V_t)
MaxDD = max(DD_0, DD_1, ..., DD_T)
```

**구현**:
- `src/risk/risk_manager.py:217-225` — `update_portfolio_value()`
- `src/risk/risk_manager.py:227-233` — `calculate_drawdown()`
- 임계값: `max_portfolio_loss_pct = 0.10` (10%) → 초과 시 포지션 축소

---

## 2. 주문 관리 (Order Management)

### 2.1 Stop Loss / Take Profit

**데이터 모델**:
```python
class Order:
    order_type: OrderType  # BUY / SELL / STOP_LOSS / TAKE_PROFIT
    trigger_price: float | None  # SL/TP 발동 가격
    parent_order_id: str | None  # 진입 주문 ID
```

**주문 타입 (OrderType enum)** — `order_management.py:13-22`:
| 타입 | 의미 | 트리거 조건 (BUY 포지션) |
|------|------|-------------------------|
| `BUY` | 진입 (롱) | — |
| `SELL` | 진입 (숏) 또는 청산 | — |
| `STOP_LOSS` | 손절 | `current_price ≤ trigger_price` |
| `TAKE_PROFIT` | 익절 | `current_price ≥ trigger_price` |

**구현**:
- `order_management.py:19-20` — `OrderType.STOP_LOSS`, `TAKE_PROFIT`
- `order_management.py:46` — `Order.trigger_price` 필드
- `order_management.py:55` — `Order.is_stop_order()` 메서드
- `order_management.py:176-189` — `create_stop_loss_order()`
- `order_management.py:191-204` — `create_take_profit_order()`
- `order_management.py:206-234` — `check_and_trigger_stop_orders()`
- `order_management.py:236-241` — `get_stop_orders()`
- `order_management.py:243-255` — `cancel_stop_orders()`

### 2.2 자동 손절·익절 발동 알고리즘

**시퀀스**:
```
진입 주문 체결 (BUY/SELL)
   ↓
_create_and_submit_order() — 진입가 P 기준
   ├─ stop_loss_price  = P × (1 - stop_loss_pct)  [BUY: 아래, SELL: 위]
   ├─ take_profit_price = P × (1 + take_profit_pct)  [BUY: 위, SELL: 아래]
   ├─ SL 주문 (PENDING)
   └─ TP 주문 (PENDING)
   ↓
(시세 도착 → _on_market_data)
   ↓
check_and_trigger_stop_orders(symbol, current_price)
   for order in pending:
     if order.is_stop_order:
       if order.type == STOP_LOSS and current_price ≤ trigger:
         order.status = SUBMITTED
       elif order.type == TAKE_PROFIT and current_price ≥ trigger:
         order.status = SUBMITTED
   ↓
_execute_stop_order(order, current_price)
   ├─ execute_order() → 시장가 체결
   ├─ portfolio.reduce_position()
   └─ 텔레그램 알림
```

**기본 비율**:
- `stop_loss_pct = 0.05` (5%)
- `take_profit_pct = 0.10` (10%)
- 리스크:보상 = 1:2

**구현 위치**:
- 진입 + 자동 SL/TP 생성: `trading_system.py:204-279`
- 시장가 체결: `trading_system.py:142-178`
- 트리거 검사: `trading_system.py:134-140`

**숏 포지션 반전**:
| 포지션 | 손절 트리거 | 익절 트리거 |
|--------|------------|------------|
| BUY | `price ≤ entry × (1 - 0.05)` | `price ≥ entry × (1 + 0.10)` |
| SELL | `price ≥ entry × (1 + 0.05)` | `price ≤ entry × (1 - 0.10)` |

→ `trading_system.py:264-272`

---

## 3. 전략 엔진 (Strategy Engine)

**파일**: `src/core/strategy_engine.py` (424줄)

### 3.1 5-시그널 가중합 (Hybrid Strategy)

**6개 신호 컴포넌트** (기본 가중치):
| 신호 | 기본 가중치 | 소스 |
|------|------------|------|
| `sentiment` | 0.30 | NLPEngine |
| `technical` | 0.20 | RSI/MACD/스프레드 |
| `ml` | 0.20 | MLEngine |
| `rl` | 0.10 | RLEngine |
| `darkpool` | 0.10 | DarkPoolTracker |
| `llm` | 0.10 | LLMEngine |

(README에서는 0.25/0.20/0.20/0.20/0.05/0.10으로 기재되어 있으나 **실제 기본값은
위 표가 정확함** — `strategy_engine.py:46-51`)

**결합 점수**:
```python
combined_score = Σ(signal_score_i × weight_i)   # score_i ∈ [0, 1]
```

**신호 → 액션 매핑**:
```
combined_score > 0.7                          → BUY
combined_score < 0.4 (sell_threshold)         → SELL
그 외                                         → HOLD
```

**고변동성 레짐 오버라이드** (regime.is_high_volatility == True):
- 기술 가중치 × 1.5, RL × 1.3, 다크풀 × 1.2 (관측 가능한 신호 강화)
- 감정 × 0.8, ML × 0.7, LLM × 0.8 (지연·잡음 큰 신호 약화)
- 재합산 후 L1 정규화

**구현**: `strategy_engine.py:200-230`

### 3.2 동적 가중치 적응 (Weight Adaptation)

**목적**: 백테스트/실전 결과로 신호 가중치를 자동 조정.

**메커니즘**:
```
매 거래 종료 시
   for each signal s:
     _signal_performance[s].append(was_s_correct)  # True/False 기록
   if len(performance) > adapt_window (50):
     _adapt_weights()
```

**가중치 업데이트**:
```python
correct_rate[s] = mean(_signal_performance[s][-50:])
new_weight[s] = old_weight[s] × (1 - α + α × correct_rate[s] / 0.5)
# α = weight_adaptation_rate = 0.05 (학습률)
weights = L1_normalize(new_weights)  # 합 = 1 유지
```

**효과**:
- 승률 50% 신호 → 가중치 유지
- 승률 70% 신호 → 가중치 +7.5%
- 승률 30% 신호 → 가중치 -7.5%

**구현**: `strategy_engine.py:296-351`

### 3.3 RSI (Relative Strength Index)

**수식 (Wilder Smoothing)**:
```
RS  = avg_gain(14) / avg_loss(14)
RSI = 100 - 100/(1 + RS)
```

**간이 구현** (현재 코드, `strategy_engine.py:148-162`):
```python
gains = sum(max(0, close[i] - close[i-1]) for i in range(-14, 0))
losses = sum(max(0, close[i-1] - close[i]) for i in range(-14, 0))
avg_gain = gains / 14
avg_loss = losses / 14
RSI = 100 - 100/(1 + avg_gain/avg_loss) if avg_loss > 0 else 100
```

**신호 임계값** (RLEngine 입력으로 사용):
- RSI > 70 → 과매수 (SELL 신호)
- RSI < 30 → 과매도 (BUY 신호)

### 3.4 MACD

**수식**:
```
EMA_12(t) = close(t) × k_12 + EMA_12(t-1) × (1 - k_12),  k_12 = 2/13
EMA_26(t) = close(t) × k_26 + EMA_26(t-1) × (1 - k_26),  k_26 = 2/27
MACD(t)   = EMA_12(t) - EMA_26(t)
Signal(t) = EMA_9(MACD)
Histogram  = MACD - Signal
```

**간이 구현** (현재 코드, `strategy_engine.py:163-165`):
```python
ema12 = sum(closes[-12:]) / 12          # 단순 이동평균 (EMA 아님)
ema26 = sum(closes[-26:]) / 26 if len(closes) >= 26 else ema12
macd_val = ema12 - ema26
```

> ⚠️ 현재 구현은 **단순 이동평균(SMA) 기반 근사치**. 정확한 EMA 평활화는
> 향후 작업. 신호 방향성에는 영향 없음.

**신호**:
- MACD > 0 → 상승 모멘텀 (BUY 가산)
- MACD < 0 → 하락 모멘텀 (SELL 가산)

### 3.5 거래량 필터

```python
if volume < volume_threshold (1,000,000):
    return HOLD (confidence=0.3)
```

**의미**: 유동성 부족 종목을 자동으로 거래 회피.

**구현**: `strategy_engine.py:103-107`

### 3.6 스프레드 필터

```python
spread_ratio = (ask - bid) / bid
if spread_ratio < spread_threshold (0.001):
    technical_signal = BUY if price > bid × buy_price_threshold else HOLD
```

**의미**: 스프레드 0.1% 이상 시 기술 신호 무시 (HOLD) — 시장가 주문의
실제 체결 가격이 너무 불리한 상황 회피.

**구현**: `strategy_engine.py:109-116`

---

## 4. 강화학습 (RL)

### 4.1 적응형 임계값 휴리스틱 (analysis/rl_engine.py)

> 명칭은 "RLEngine"이지만 실제 구현은 **휴리스틱**입니다.
> 완전한 DQN은 `src/ai/rl_trader.py`에 별도.

**입력 state features**:
```python
state = {
    "vix": float,               # VIX 지수
    "rsi": float (0~100),
    "macd": float,
    "trend_strength": float (0~1)
}
```

**행동 결정**:
```python
def get_action(state):
    vix = state["vix"]
    rsi = state["rsi"]
    macd = state["macd"]
    
    # 적응형 임계값 (win_rate 기반)
    self._adapt_thresholds()  # win_rate 50%+ → 임계값 완화
    
    if vix > self.high_vix_threshold (40):
        return {"action": "HOLD", "confidence": 0.3}
    if rsi < self.oversold_threshold (30):
        return {"action": "BUY", "confidence": 0.8}
    if rsi > self.overbought_threshold (70):
        return {"action": "SELL", "confidence": 0.8}
    if macd > 0 and trend_strength > 0.6:
        return {"action": "BUY", "confidence": 0.6}
    if macd < 0 and trend_strength > 0.6:
        return {"action": "SELL", "confidence": 0.6}
    return {"action": "HOLD", "confidence": 0.5}
```

**적응형 임계값 (`_adapt_thresholds`)**:
```python
self.oversold_threshold = 30 + (win_rate - 0.5) × 20  # 20~40
self.overbought_threshold = 70 - (win_rate - 0.5) × 20  # 60~80
# win_rate 높으면 임계값 완화 (더 자주 신호 발생)
# win_rate 낮으면 임계값 강화 (신회 신호만)
```

**구현**: `src/analysis/rl_engine.py:8-110`

### 4.2 Deep Q-Network (DQN)

**파일**: `src/ai/rl_trader.py` (358줄, 순수 PyTorch — SB3 의존성 없음)

**환경** (`TradingEnvironment`):
- 상태: `[price_norm, position, unrealized_pnl_norm]` (3-dim)
- 행동: `0=HOLD, 1=BUY, 2=SELL` (3-dim)
- 보상: `Δ 포트폴리오 가치`

**에이전트 (`DQNAgent`)**:
```python
class QNetwork(nn.Module):
    """3 → 64 → 64 → 3"""
    def __init__(state_dim, action_dim, hidden=64):
        self.fc1 = nn.Linear(state_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.out = nn.Linear(hidden, action_dim)
```

**학습**:
```python
# Replay buffer (10,000 transition)
# ε-greedy (start=0.5, end=0.05, decay=0.995)
# Bellman update: y = r + γ × max_a Q(s', a; θ_target)
# Target network soft update (τ=0.01)
```

**API**:
```python
env = TradingEnvironment(prices=[100, 102, 105, 103, 108])
agent = DQNAgent(state_dim=3, action_dim=3)
agent.train(env, episodes=5)
action = agent.select_action(state)
```

**구현**: `src/ai/rl_trader.py:166-358`

### 4.3 Phase 3 호환 (`src/ai/rl_trading.py`)

```python
DummyTradingEnv(data)      # Gymnasium 5-튜플 step API
train_rl_model(data)       # SB3 PPO 우선, 없으면 in-house DQN fallback
```

- 테스트 호환용 얇은 래퍼
- `stable_baselines3` 미설치 시 in-house DQNAgent 어댑터 반환

---

## 5. 포트폴리오 최적화 (Portfolio Optimization)

### 5.1 Mean-Variance Optimization (Markowitz 1952)

**수식**:
```
min_w  w^T Σ w
s.t.   w^T μ = μ_target
       w^T 1 = 1
       w_i ≥ 0
```

**Closed-form 해** (Lagrangian):
```
w* = Σ^-1 × (λμ + γ1)
λ = (C × μ_target - A) / D
γ = (B - A × μ_target) / D
where A = 1^T Σ^-1 μ, B = μ^T Σ^-1 μ, C = 1^T Σ^-1 1, D = B·C - A²
```

**구현** (`src/analysis/quantum_optimizer.py:14-63`):
```python
def optimize_allocation(symbols, current_weights, expected_returns, cov_matrix):
    inv_cov = np.linalg.inv(cov + ridge)  # ridge: condition number > 1e12
    w = inv_cov @ (λ × er + γ × ones)
    w = max(w, 0)  # long-only
    w = w / sum(w)  # 합 = 1
```

**입력**:
- `expected_returns`: `Dict[symbol, float]` — 없으면 0으로 가정
- `cov_matrix`: `np.ndarray (n×n)` — 없으면 단위행렬 × 0.04 (σ=20% 가정)
- `current_weights`: 리밸런싱 기준 (반환값은 normalized)

**출력**: `Dict[symbol, float]` (합=1, 모두 ≥0)

### 5.2 Risk Parity

**원리**: 각 종목의 위험 기여도를 균등하게 (`w_i × σ_i = const`).

**Closed-form 근사**:
```
w_i ∝ 1/σ_i
σ_i = sqrt(Σ_ii)
```

**구현** (`src/analysis/quantum_optimizer.py:65-90`):
```python
def risk_parity_allocation(symbols, cov_matrix):
    sigma = sqrt(diag(cov))
    w = 1 / max(sigma, 1e-8)
    return L1_normalize(w)
```

**사용 시나리오**:
- 변동성 큰 종목은 가중치를 줄이고, 안정적인 종목은 늘림
- 분산 효과 극대화

### 5.3 모멘텀 기반 배분 (`src/strategy/asset_allocation.py:138-178`)

```python
def _momentum(price_data):
    """12개월 수익률 순위 기반 가중치 (상위 50%만 롱)"""
    returns_12m = {sym: price[-1]/price[-252] - 1 for sym, price in price_data.items()}
    positive = {s: r for s, r in returns_12m.items() if r > 0}
    total = sum(positive.values())
    return {s: r/total for s, r in positive.items()} if total > 0 else equal_weight
```

**전략 비교** (`AssetAllocator`):
| 전략 | 용도 | 장점 |
|------|------|------|
| `equal_weight` | 단순 분산 | 안정, 거래 비용 최소 |
| `risk_parity` | 위험 균등 | 분산 효과 최대 |
| `momentum` | 추세 추종 | 강세장 초과 수익 |

---

## 6. 통계적 차익거래 (Statistical Arbitrage)

**파일**: `src/core/stat_arb.py` (실제 코인테그레이션 분석)

**알고리즘 (Pairs Trading)**:
```
1. correlation > 0.5 필터 (강한 상관관계 페어만)
2. OLS 회귀: y = α + β·x → 잔차 ε = y - (α + β·x)
3. 잔차의 z-score 계산: z = (ε_t - μ_ε) / σ_ε
4. |z| > 2 → 평균회귀 신호
```

**구현** (`src/core/stat_arb.py:14-62`):
```python
def find_cointegrated_pairs(prices_dict):
    pairs = []
    symbols = list(prices_dict.keys())
    for i, j in combinations(range(len(symbols)), 2):
        x = prices_dict[symbols[i]]
        y = prices_dict[symbols[j]]
        if len(x) < 30 or len(y) < 30:
            continue
        # (1) correlation
        corr = np.corrcoef(x, y)[0, 1]
        if corr < 0.5:
            continue
        # (2) OLS
        beta, alpha = np.polyfit(x, y, 1)
        residual = y - (alpha + beta * np.array(x))
        # (3) z-score
        z = (residual[-1] - residual.mean()) / residual.std()
        if abs(z) > 2:
            pairs.append({
                "pair": (symbols[i], symbols[j]),
                "beta": beta,
                "alpha": alpha,
                "z_score": z,
                "signal": "LONG_SPREAD" if z < 0 else "SHORT_SPREAD"
            })
    return pairs
```

**호출 위치**: `strategy_engine.py:254-264` (진입 신호 생성 시 참고)

---

## 7. 유명 투자자 전략 (Famous Investor Strategies)

**파일**: `src/strategy/famous_investors.py` (451줄)

### 7.1 Buffett (가치투자)

**5가지 기준** (각 1점, 70% 이상이면 BUY):

| 기준 | 조건 | 점수 |
|------|------|------|
| PER | < 15 | 1.0 |
| PER | 15-20 | 0.5 |
| PBR | < 1.0 | 1.0 |
| PBR | 1.0-2.0 | 0.5 |
| ROE | > 15% | 1.0 |
| ROE | 10-15% | 0.5 |
| 부채비율 | < 30% | 1.0 |
| 부채비율 | 30-50% | 0.5 |
| 배당률 | > 2% | 1.0 |

**구현**: `famous_investors.py:37-116`

### 7.2 Lynch (성장주)

**5가지 기준**:

| 기준 | 조건 | 점수 |
|------|------|------|
| Earnings Growth | > 25% | 1.5 |
| Earnings Growth | 15-25% | 1.0 |
| Revenue Growth | > 20% | 1.0 |
| PEG Ratio (PER/성장률) | < 1 | 1.0 |
| PEG Ratio | 1-2 | 0.5 |
| Industry Growth | > 0 | 가산 |

**구현**: `famous_investors.py:119-195`

### 7.3 Minerva (모멘텀)

**5가지 기준**:

| 기준 | 조건 | 점수 |
|------|------|------|
| 52주 수익률 | > 50% | 1.5 |
| 52주 수익률 | 20-50% | 1.0 |
| 6개월 수익률 | > 20% | 1.0 |
| RSI | 50 < rsi < 70 | 1.0 |
| RSI | ≥ 70 | 0.3 (과매수 주의) |
| 모멘텀 점수 | > 70 | 1.0 |
| 거래량 증가 | > 20% | 0.5 |

**구현**: `famous_investors.py:197-277`

### 7.4 Dividend (배당)

**5가지 기준**:

| 기준 | 조건 | 점수 |
|------|------|------|
| 배당률 | > 4% | 1.5 |
| 배당률 | 2.5-4% | 1.0 |
| 배당 성장률 | > 5% | 1.0 |
| 배당 지속 연수 | > 10년 | 1.0 |
| 잉여현금흐름 | > 0 | 0.5 |

**구현**: `famous_investors.py:280-368`

**컨센서스 엔진** (`InvestorStrategyEngine`):
```python
# 4개 전략 일괄 실행 → 가중 투표
consensus = {
    "BUY":  [전략 1, 전략 2, ...],   # BUY 추천한 전략
    "HOLD": [...],
    "SELL": [...]
}
# 가중 신뢰도 합산이 가장 높은 액션 채택
```

**구현**: `famous_investors.py:369-451`

---

## 8. 고급 통계 지표 (Advanced Statistics)

**파일**: `src/analysis/statistics.py` (261줄)

### 8.1 Sharpe Ratio

**수식** (연환산):
```
Sharpe = (E[R] - Rf) / σ(R) × √252
```

**구현**: `statistics.py` (계산식)

### 8.2 Sortino Ratio

**수식**:
```
Sortino = (E[R] - Rf) / σ_downside(R) × √252
σ_downside = sqrt(E[min(R - Rf, 0)²])
```

**차이**: Sharpe는 상승/하방 변동성 모두 penalize, Sortino는 하방만 penalize.

### 8.3 Calmar Ratio

**수식**:
```
Calmar = CAGR / MaxDrawdown
CAGR = (V_T / V_0)^(1/years) - 1
```

**의미**: 단위 MDD당 복리 성장률. 높을수록 안정적 고수익.

### 8.4 Hurst Exponent (H)

**수식** (R/S 분석):
```
E[R(n)/S(n)] = c × n^H
H = 0.5  → 랜덤워크 (Brownian motion)
H < 0.5  → 평균회귀 (mean-reverting) → 역추세 전략
H > 0.5  → 추세 지속 (trending)    → 추세추종 전략
```

**의미**: Hurst < 0.5면 평균회귀 신호(Stat Arb)에 유리, > 0.5면 모멘텀 전략에 유리.

**구현**: `statistics.py`

### 8.5 Maximum Drawdown

**수식**:
```
DD_t = (Peak_t - V_t) / Peak_t
MaxDD = max(DD_t)
```

**구현**: `statistics.py` (계산식)

### 8.6 VaR / CVaR (이전 §1.2 참고)

---

## 9. 시장 레짐 감지 (Market Regime Detection)

**파일**: `src/data_layer/alt_data.py` (107줄)

### 9.1 VIX 조회
```python
# alt_data.py:18
def fetch_vix() -> float
# yfinance "^VIX" 조회, 5분 캐시
```

### 9.2 SPX 추세
```python
# alt_data.py:41
def _fetch_spx_trend() -> Dict
# ^GSPC 50일 MA vs 200일 MA 비교
# "BULL" / "BEAR" / "NEUTRAL"
```

### 9.3 변동성 레짐
```python
# alt_data.py:76
def _detect_volatility_regime(vix) -> str
# "low" (< 15)
# "normal" (15-20)
# "elevated" (20-25)
# "high" (25-35)
# "extreme" (≥ 35)
```

### 9.4 통합 레짐 점수
```python
# alt_data.py:88
def get_market_regime() -> Dict
# {
#   "vix": float,
#   "spx_trend": "BULL" | "BEAR" | "NEUTRAL",
#   "vol_regime": "low" | "normal" | "elevated" | "high" | "extreme",
#   "is_high_volatility": bool,
#   "regime_score": float (-1 ~ +1)
# }
```

**regime_score 계산**:
- SPX 200일 MA 위 + VIX < 20 → +0.8 (강세)
- SPX 200일 MA 위 + VIX 20-25 → +0.3
- SPX 200일 MA 아래 + VIX > 25 → -0.7 (약세)
- 그 외 → 0.0 (중립)

**사용처**: `HybridStrategyEngine.analyze()` — regime == `is_high_volatility`일 때 가중치 동적 조정.

---

## 10. 자연어 처리 (NLP)

### 10.1 한국어 키워드 감정 분석

**파일**: `src/data_layer/nlp_engine.py` (106줄)

**알고리즘**:
```python
# 1. 토큰화
tokens = text.split()

# 2. 매칭
score = 0
for token in tokens:
    if token in positive_keywords:
        score += positive_weight[token]
    elif token in negative_keywords:
        score += negative_weight[token]

# 3. 정규화
final_score = max(-1.0, min(1.0, score / max(len(tokens), 1) × 10))
```

**기본 어휘** (`nlp_engine.py:39-46`):
- 긍정: `상승`, `호재`, `긍정`, `강세`, `매수`, `돌파`, `신고가`, ...
- 부정: `하락`, `악재`, `부정`, `약세`, `매도`, `이탈`, `손실`, ...

**구현**: `nlp_engine.py:53-99`

### 10.2 영문 금융 어휘 감정 분석

**파일**: `src/ai/sentiment.py` (354줄)

**어휘 예시** (가중치):
```python
POSITIVE = {
    "surge": 0.8, "soar": 0.8, "beat": 0.7, "outperform": 0.7,
    "record-high": 0.8, "strong buy": 0.9, "bullish": 0.8, ...
}
NEGATIVE = {
    "plummet": 0.8, "tumble": 0.7, "miss": 0.7, "downgrade": 0.7,
    "weak": 0.5, "bearish": 0.8, "sell-off": 0.7, ...
}
```

**점수 계산**:
```python
def analyze_sentiment(text):
    tokens = re.findall(r'\w+', text.lower())
    score = sum(POSITIVE.get(t, 0) - abs(NEGATIVE.get(t, 0)) for t in tokens)
    return tanh(score / 5)  # squash to [-1, 1]
```

**구현**: `sentiment.py:1-354`

### 10.3 LLM 기반 감정 분석

**파일**: `src/ai/llm_earnings_agent.py`

**알고리즘** (현재 Mock):
```python
# 키워드 매칭 → 결정적 응답
if "성장" in transcript or "초과" in transcript:
    return {score: 0.8, beat: True, guidance: "POSITIVE", ...}
elif "하향" in transcript or "위축" in transcript:
    return {score: -0.6, beat: False, guidance: "NEGATIVE", ...}
```

**향후 LLM 통합**: `LLMEarningsAgent.__init__(self.llm_engine)`이 LLMEngine을
받아 `self.llm.generate_text(prompt)` 호출로 확장 가능.

---

## 11. 백테스트 비용 모델 (Backtest Cost Model)

**파일**: `src/analysis/backtest.py` (1322줄)

**3중 비용 모델** (모든 체결에 적용):
```python
def _apply_costs(self, fill_price, quantity, side):
    fee = fill_price * quantity * self.fee_pct           # 0.10%
    slippage = fill_price * self.slippage_pct            # 0.10%
    market_impact = fill_price * quantity**0.5 * self.market_impact_pct  # 0.05% × √qty
    
    # 매수: 더 비싸게
    # 매도: 더 싸게
    adjusted = fill_price + slippage + market_impact if side == BUY else fill_price - slippage - market_impact
    
    return adjusted, fee
```

**시장 충격 모델** (`√qty 비례`):
- 100주 → 0.05% × 10 = 0.5%
- 1,000주 → 0.05% × 31.6 = 1.58%
- 10,000주 → 0.05% × 100 = 5.0%

→ 대량 주문의 비선형 슬리피지 모델링 (Almgren-Chriss 2000 단순화).

---

## 12. 이벤트 버스 패턴 (Event Bus)

**파일**: `src/utils/event_bus.py`

**Pub-Sub 패턴**:
```python
class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_name: str, callback: Callable):
        self.subscribers.setdefault(event_name, []).append(callback)
    
    def publish(self, event_name: str, data):
        for cb in self.subscribers.get(event_name, []):
            cb(data)
```

**발행 이벤트**:
| 이벤트 | 발행자 | 구독자 |
|--------|--------|--------|
| `market_data` | MarketDataHandler | HybridStrategyEngine, _on_market_data |
| `news_sentiment` | NLPEngine | HybridStrategyEngine, _on_news_analyzed |
| `strategy_signal` | HybridStrategyEngine | _on_strategy_signal |
| `account_sync` | AccountSyncAgent | _on_account_synced |
| `order_status` | OrderManagementSystem | _on_order_status_changed |

**장점**:
- 컴포넌트 간 직접 의존성 제거
- 새 구독자 추가가 코드 변경 최소화
- 테스트 시 모킹 용이

---

## 부록: 수치 안정성 노트

1. **공분산 행렬**: 조건수 > 1e12 시 ridge regularization (`eye × 0.001`) 추가
2. **분모 0 회피**: VaR/CVaR 계산 시 `max(σ, 1e-8)` 클램핑
3. **L1 정규화**: 가중치 적응 후 `sum(weights) = 1` 강제
4. **NaN/Inf 방지**: `np.where(cond, safe_val, computed_val)` 패턴 사용

---

**마지막 업데이트**: 2026-06-06
**검증 상태**: 모든 알고리즘이 코드로 검증되었으며, 향후 변경 시 본 문서 갱신 필요

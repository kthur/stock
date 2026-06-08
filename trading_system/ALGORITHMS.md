# 알고리즘 정의서 - ALGORITHMS

본 문서는 `D:\Finance\code\stock\trading_system\`에서 실제로 사용되는 모든
트레이딩 알고리즘을 수학적 정의와 함께 정리합니다.

---

## 1. 기술적 신호

### 1.1 RSI (Relative Strength Index)

**파일**: `core/strategy_engine.py:HybridStrategyEngine._compute_technical()`

```
RSI = 100 - (100 / (1 + RS))
RS = avg_gain(14) / avg_loss(14)
```

- **RSI < 30**: 과매도 → 매수 신호 (signal = +1)
- **RSI > 70**: 과매수 → 매도 신호 (signal = -1)
- **else**: 중립 (signal = 0)

### 1.2 MACD (Moving Average Convergence Divergence)

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

- **Histogram > 0**: 매수 신호 (+0.5)
- **Histogram < 0**: 매도 신호 (-0.5)

### 1.3 이동평균선 (MA)

```
SMA(20) = Σ(P_i) / 20   (short)
SMA(50) = Σ(P_i) / 50   (long)
```

- **SMA(20) > SMA(50)**: 상승 추세 → 매수 신호 (+0.3)
- **SMA(20) < SMA(50)**: 하락 추세 → 매도 신호 (-0.3)

### 1.4 기술 종합 점수

```python
tech_score = rsi_signal(0.4) + macd_signal(0.35) + ma_signal(0.25)
```

최종 신호: `BUY` (tech_score > 0.3), `SELL` (tech_score < -0.3), `HOLD` (그 외)

---

## 2. 감성 신호 (Sentiment Signal)

**파일**: `data_layer/nlp_engine.py:NLPEngine.analyze_sentiment()`

### 2.1 키워드 기반 점수

```
pos_words = {상승, 돌파, 호실적, 수주, 신고가, 특허, 협력, ...}  # +0.1 ~ +0.3
neg_words = {하락, 악재, 적자, 하향, 조정, 소송, 감산, ...}     # -0.1 ~ -0.3
```

```
score = clamp(pos_count / total_words - neg_count / total_words, -1.0, 1.0)
```

### 2.2 신호 변환

- `score > 0.2`: BUY (confidence = score)
- `score < -0.2`: SELL (confidence = |score|)
- `|score| ≤ 0.2`: HOLD

### 2.3 에포크 기반 평활 (Epoch-based Smoothing)

- `sentiment_history`에 최대 5개 저장
- 5개 누적 시 분산이 0.3 이상이면 현재 점수에 0.5 가중치 적용 (신뢰도 하락 보정)

---

## 3. ML 예측 신호 (ML Prediction)

**파일**: `analysis/ml_predictor.py:MLPredictor`

### 3.1 전처리

```
features = [close, volume, RSI, MACD, BB_upper, BB_lower, OBV, ATR]
X(t) = features[t-59:t+1]   # 과거 60일 시퀀스
X_scaled = (X - μ) / σ      # Z-score 정규화
```

### 3.2 모델 (LSTM)

```
Input(60, 8) → LSTM(50, return_sequences) → Dropout(0.2) →
LSTM(50) → Dropout(0.2) → Dense(1, sigmoid)
```

### 3.3 신호

```
raw_prediction ∈ [0, 1]  # 1 = 상승 예측
```

- `raw_prediction > 0.55`: BUY (confidence = 2 × (pred - 0.55))
- `raw_prediction < 0.45`: SELL (confidence = 2 × (0.45 - pred))
- `else`: HOLD

---

## 4. RL 신호 (Reinforcement Learning)

**파일**: `analysis/rl_trader.py`

### 4.1 환경

```
State:  (prices[t], position[t], cash[t], MACD[t], RSI[t])
Action: {BUY(+1), HOLD(0), SELL(-1)}
Reward: Δ(portfolio_value) / portfolio_value[t-1]
```

### 4.2 DQN

```
Q(s, a) ← Q(s, a) + α × [reward + γ × max(Q(s', a')) - Q(s, a)]
```

- `α = 0.001` (learning rate)
- `γ = 0.95` (discount factor)
- `ε-greedy` exploration: `ε = 0.1`

### 4.3 신호

- Q-value(action=BUY)가 Q-value(action=SELL)보다 큰 정도를 sigmoid로 confidence 변환

---

## 5. 다크풀 신호 (DarkPool Signal)

**파일**: `data_layer/darkpool_tracker.py:DarkPoolTracker`

### 5.1 현재 구현

데이터 소스 부재로 항상 **중립값 0.0** 반환:
```python
# 의도적 상수 반환 — 실제 데이터 피드 연동 시 구현 필요
```

### 5.2 설계 의도

```
DP_Ratio = DarkPool_Volume / Total_Volume
DP_Ratio_Z = (DP_Ratio - μ) / σ   # 20일 Z-score
```

- `DP_Ratio_Z > 2.0`: 기관 이탈 → 매도 신호
- `DP_Ratio_Z < -2.0`: 기관 축적 → 매수 신호

---

## 6. LLM 신호 (Large Language Model)

**파일**: `ai/openai_adapter.py`, `ai/gemini_adapter.py`

### 6.1 프롬프트 구조

```
System: 당신은 주식 트레이딩 전문가입니다.
User: 종목 {symbol}, 현재가 {price}, RSI {rsi}, MACD {macd}, 뉴스 감정 {sentiment}...
```

### 6.2 응답 파싱

```python
raw_confidence = parse(response_text)  # 0.0 ~ 1.0
```

- `raw_confidence > 0.6`: BUY (closer to 0/1은 스케일 조정)
- `raw_confidence < 0.4`: SELL
- `else`: HOLD

### 6.3 폴백

API 키 미설정 시 **`LLMResponse(signal=Signal.HOLD, confidence=0.5)`** 반환.

---

## 7. 글로벌 마켓 신호 (Global Market Signal)

**파일**: `data_layer/global_market_client.py:GlobalMarketClient`

### 7.1 지표 수집

```
VIX / S&P 500 (^VIX, ^GSPC) — yfinance
Fear & Greed Index — yfinance (^FNGD)
```

### 7.2 신호 변환

```
risk_off = VIX > 30  → confidence = 0.0 (BUY 금지)
normal   = VIX < 20  → confidence = 0.6
fng_adj  = fear_greed / 100 → [0, 1]
```

### 7.3 종합

```
global_confidence = 0.5 × (1 - vix/100) + 0.5 × fng_adj
```

---

## 8. 현금 비중 신호 (Cash Ratio Signal)

**파일**: `core/strategy_engine.py:HybridStrategyEngine.analyze()` (8번째 신호)

### 8.1 정의

```python
cash_ratio = available_cash / portfolio_value  # [0, 1]
```

### 8.2 신호 변환

```
signal_direction = +1 (BUY)   if cash_ratio > 0.50  # 현금 과다 → 매수 유도
signal_direction = -1 (SELL)  if cash_ratio < 0.15  # 현금 부족 → 매도 유도
signal_direction = 0 (HOLD)   otherwise
```

### 8.3 신뢰도

```python
if cash_ratio > 0.50:
    confidence = (cash_ratio - 0.50) * 2.0  # 0.0 ~ 1.0
elif cash_ratio < 0.15:
    confidence = (0.15 - cash_ratio) * 2.0  # 0.0 ~ 1.0
else:
    confidence = 0.0  # HOLD
```

---

## 9. 시장 레짐 감지 (Market Regime Detection)

**파일**: `data_layer/market_regime.py:MarketRegimeDetector`

### 9.1 변동성 레짐

```
ATR(14) = EMA(14) of TR
daily_vol = ATR / close
annual_vol = daily_vol × √252
```

- `annual_vol > 0.30`: HIGH_VOL
- `annual_vol > 0.15`: MID_VOL
- `else`: LOW_VOL

### 9.2 추세 레짐 (ADX 기반, v4.1)

```
+DM = high[t] - high[t-1]  (if > low[t-1] - low[t], else 0)
-DM = low[t-1] - low[t]    (if > high[t] - high[t-1], else 0)
TR = max(high-low, |high-close[t-1]|, |low-close[t-1]|)

+DI(14) = 100 × EMA(+DM, 14) / EMA(TR, 14)
-DI(14) = 100 × EMA(-DM, 14) / EMA(TR, 14)
DX = 100 × |+DI - -DI| / (+DI + -DI)
ADX(14) = EMA(DX, 14)
```

- `ADX ≥ 25`: 강한 추세 (TRENDING)
- `ADX < 25`: 약한 추세 (RANGING)

### 9.3 BB Width (볼린저 밴드 폭, v4.1)

```
BB_Width = (BB_upper - BB_lower) / SMA(20)
BB_Width_Z = (BB_Width - μ(20)) / σ(20)
```

- `BB_Width_Z > 1.5`: 고변동성 (HIGH_BETA)
- `BB_Width_Z < -1.5`: 저변동성 (LOW_BETA)

### 9.4 레짐별 가중치 조정

| 추세 | 변동성 | ML 가중치 | Sentiment 가중치 |
|------|--------|----------|-----------------|
| TRENDING | — | ×1.5 | ×0.7 |
| RANGING | — | ×0.7 | ×1.3 |
| — | HIGH_BETA | ×0.8 | ×0.8 |
| — | LOW_BETA | ×1.2 | ×1.2 |

---

## 10. 주문 사이징 (Order Sizing Pipeline)

**파일**: `trading_system.py:_create_and_submit_order()`

### 10.1 Kelly Criterion

```
f* = (p × W - L) / (W × L / W_avg)
  p     = win_rate
  W     = avg_win / capital
  L     = avg_loss / capital
  W_avg = avg_win (ratio)

final_f = min(f* × 0.5, 0.25)  # Half Kelly, max 25%
```

### 10.2 Volatility Targeting (v4.0)

```
σ_daily  = ATR(14) / close_price
σ_annual = σ_daily × √252

scale = target_annual_vol / (σ_annual + ε)
scale = clamp(scale, 0.25, 2.0)

adjusted_size = base_kelly_size × scale
```

`target_annual_vol = 0.15` (15%), `ε = 1e-10`

### 10.3 Multi-timeframe Confirmation

```
weekly_ema20 = EMA(20) of weekly_close
weekly_ema50 = EMA(50) of weekly_close

if weekly_ema20 < weekly_ema50:
    size *= 0.50  # 주봉 약세 → 50% 축소
```

### 10.4 VIX Risk-Off

```
if VIX ≥ 25:
    max_cash_exposure = portfolio_value × 0.30  # 현금 70% 강제 유지
```

### 10.5 상관관계 레짐 (Correlation Regime, v4.0)

```
return_matrix = prices.pct_change()
corr_matrix  = return_matrix.corr()

# 포트폴리오 평균 상관계수
avg_corr = Σ(corr[i][j]) / (n × (n-1)), i≠j

if avg_corr > 0.80:
    size *= 0.75  # 25% 축소
```

### 10.6 시장 임팩트 (Market Impact, v4.0)

```
impact = order_value / (avg_daily_volume × close_price)
if impact > 0.05:
    size *= 0.05 / impact  # 비례 축소
```

### 10.7 리스크 패리티 집중도 체크

```
for each pair (i, j):
    if corr_matrix[i][j] > 0.70:
        combined = weight[i] + weight[j]
        if combined > correlation_limit_pct (0.40):
            # 초과분 비례 축소
```

### 10.8 Earnings Gapper Protection (v4.2)

```
days_to_earnings = earnings_date - today
if days_to_earnings ≤ 5:
    size *= 0.50
```

---

## 11. 자동 손절/익절 (Auto SL/TP + Trailing + Partial)

**파일**: `trading_system.py:_create_and_submit_order()`, `_update_trailing_stops()`

### 11.1 ATR 기반 손절/익절가

```
ATR_stop = entry_price - ATR(14) × atr_multiplier_stop (2.0x)
ATR_tp   = entry_price + ATR(14) × atr_multiplier_target (4.0x)
```

폴백: `stop_price = entry × 0.95`, `tp_price = entry × 1.10`

### 11.2 트레일링 스탑 (v4.0)

```
각 Position에 대해:
  new_highest = max(current_price, highest_price)
  
  if new_highest > highest_price:
      highest_price = new_highest
      new_trigger = new_highest × (1 - trail_pct)
      # 기존 SL 주문의 trigger_price 갱신 (5% 하방)
```

`trail_pct = 0.05`

### 11.3 부분 익절 3-티어 (v4.2)

| 티어 | 가격 | 할당 |
|------|------|------|
| **TP1** | `entry + ATR × 1.5` | 33% |
| **TP2** | `entry + ATR × 3.0` | 33% |
| **TP3** | `entry + ATR × 5.0` | 34% |

ATR 계산 불가 시 고정 비율 폴백: 1.5× / 3.0× / 5.0× ATR 대신 상대 비율 유지.

### 11.4 포트폴리오 레벨 손절 (v4.1)

```
current_DD = (peak_value - current_value) / peak_value

if current_DD > max_portfolio_drawdown_pct (0.20):
    liquidate_all_positions()    # 시장가 전량 청산
    cancel_all_stop_orders()     # 모든 미체결 주문 취소
    _portfolio_liquidated = True # 중복 청산 방지
```

---

## 12. 신호 합의 점수 (Signal Consensus Scoring)

**파일**: `trading_system.py:_on_strategy_signal()`

### 12.1 정의

```python
buy_consensus  = sum(1 for s in signals if s == "BUY")
sell_consensus = sum(1 for s in signals if s == "SELL")
n_signals = len(all_signals)  # 8
```

### 12.2 합의 증폭 계수

```
일치도       buy/sell_consensus / n_signals         confidence 승수
100%                 1.0                                1.40
75~87.5%          0.75~0.875                            1.15
37.5~62.5%        0.375~0.625                           0.85
12.5~25%          0.125~0.25                            0.60
0%                   0.0                                0.40
```

### 12.3 적용

```
adjusted_confidence = original_confidence × consensus_multiplier
adjusted_confidence = clamp(adjusted_confidence, 0.0, 1.0)
```

---

## 13. 백테스트 (Backtest Engine)

**파일**: `analysis/backtest_engine.py:BacktestEngine`

### 13.1 슬리피지 + 수수료

```
cost = slippage_pct (0.001) + fee_pct (0.001) + market_impact_pct (0.0005)

exec_price_buy  = price × (1 + cost)
exec_price_sell = price × (1 - cost)
```

### 13.2 PnL 계산

```
trade_pnl = Σ(q_sell × p_sell × (1 - cost)) - Σ(q_buy × p_buy × (1 + cost))
```

---

## 14. 최적화 (Optimization Engine)

**파일**: `core/strategy_engine.py:OptimizationEngine`

### 14.1 슬리피지/수수료 최적화

```
net_pnl = gross_pnl - slippage_cost - fee_cost
```

### 14.2 성과 속성 (Performance Attribution, v4.0)

```python
# 각 신호별
attribution[symbol]["total_pnl"] += trade_pnl
attribution[symbol]["trade_count"] += 1
win_rate = wins / total

# 요약
total_pnl = Σ attribution[symbol]["total_pnl"]
```

---

## 15. 리밸런싱 (Auto-Rebalancing)

**파일**: `trading_system.py:rebalance_portfolio()`

### 15.1 목표 비중

현재 전략 엔진의 신호 강도를 목표 비중으로 변환:
```python
signal_strength → target_weight = softmax(all_signal_confidences)
```

### 15.2 리밸런싱 실행

```python
plan = portfolio.compute_rebalance_plan(target_weights, current_prices)
# plan: [(symbol, current_qty, target_qty, action), ...]

cash_needed = portfolio.estimate_rebalance_cash_needed(plan, prices)
```

### 15.3 스케줄링 (v4.1)

```python
# 168시간마다 자동 실행
if hours_since_last_rebalance >= rebalance_interval_hours (168):
    await self.rebalance_portfolio()
```

---

## 16. Cash Ratio Adjustment (Sizing 내)

**파일**: `trading_system.py:_create_and_submit_order()`

### 16.1 정의

```python
cash_ratio = self.cash / portfolio_value
```

### 16.2 조정 계수

```
if cash_ratio > 0.50:
    sizing_multiplier = 1.0 + (cash_ratio - 0.50)  # max 1.5×
elif cash_ratio < 0.15:
    sizing_multiplier = 0.5  # 50% 축소
else:
    sizing_multiplier = 1.0
```

목적: 현금이 너무 많으면 공격적으로, 너무 적으면 보수적으로 진입.

---

## 부록: 신호별 가중치 기본값

| 순서 | 신호 | 기본 가중치 | 소스 파일 |
|------|------|------------|----------|
| 1 | Sentiment | 0.30 | `strategy_engine.py` |
| 2 | Technical | 0.20 | `strategy_engine.py` |
| 3 | ML | 0.20 | `ml_predictor.py` |
| 4 | RL | 0.10 | `rl_trader.py` |
| 5 | DarkPool | 0.10 | `darkpool_tracker.py` |
| 6 | LLM | 0.10 | `openai_adapter.py` / `gemini_adapter.py` |
| 7 | Global Market | 0.10 | `global_market_client.py` |
| 8 | Cash Ratio | 0.08 | `strategy_engine.py` |

**합계**: 1.18 (내부 정규화로 1.0 스케일)

---

**마지막 업데이트**: 2026-06-08

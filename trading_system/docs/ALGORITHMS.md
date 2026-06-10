# 알고리즘 정의서 - ALGORITHMS

본 문서는 `D:\Finance\code\stock\trading_system\docs\`에서 실제로 사용되는 모든 트레이딩 알고리즘을 수학적 정의와 함께 정리합니다.

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

---

## 3. ML 예측 신호 (ML Prediction Ensemble)

**파일**: `analysis/ml_engine.py:MLEngine`

### 3.1 24개 입력 피처 (Features)

모델 학습 및 예측에 사용되는 24개 주요 정형 데이터 피처는 다음과 같습니다:

1. `ret_1`: 1일 수익률
2. `ret_5`: 5일 누적 수익률
3. `ret_20`: 20일 누적 수익률
4. `sma_10_dist`: 10일 단순이동평균 대비 이격도
5. `sma_50_dist`: 50일 단순이동평균 대비 이격도
6. `rsi_14`: 14일 RSI 지표
7. `rsi_5`: 5일 단기 RSI 지표
8. `volatility_10`: 10일 일별 수익률 표준편차
9. `macd`: MACD 값
10. `macd_signal`: MACD 시그널 라인
11. `bb_upper_dist`: 볼린저 밴드 상단 이격도
12. `bb_lower_dist`: 볼린저 밴드 하단 이격도
13. `atr_14`: 정규화된 14일 ATR (Average True Range)
14. `volume_change`: 1일 거래량 변화율
15. `log_volume_ratio`: 평균 거래량 대비 로그 볼륨 비율
16. `gap_pct`: 갭 상승/하락 비율
17. `intraday_range`: 일중 변동률 (고가 - 저가 대비 비율)
18. `bb_width`: 볼린저 밴드 너비
19. `macd_hist_norm`: 종가 대비 정규화된 MACD 히스토그램
20. `roc_10`: 10일 Rate of Change
21. `roc_20`: 20일 Rate of Change
22. `higher_high`: 고가 상승 여부
23. `higher_low`: 저가 상승 여부
24. `distance_from_52w_high`: 52주 신고가 대비 이격도

HMM이 활성화된 경우 `hmm_regime`이 25번째 피처로 자동 추가됩니다. 입력 행렬은 `StandardScaler`를 이용해 Z-score 정규화됩니다.

### 3.2 앙상블 아키텍처 및 Soft Voting

- **Random Forest Classifier**: 트리의 최대 깊이 및 개수 탐색
- **XGBoost Classifier**: 극도의 비선형 학습 및 정규화 규제 처리
- 두 분류기의 클래스 1(상승) 예측 확률값을 산술 평균(50:50 soft voting)하여 최종 ML 점수를 구합니다:

```
ml_score = 0.5 × P_RF(상승) + 0.5 × P_XGB(상승)
```

- `ml_score > 0.55`: BUY 신호 (confidence = 2 × (ml_score - 0.55))
- `ml_score < 0.45`: SELL 신호 (confidence = 2 × (0.45 - ml_score))
- `else`: HOLD 신호

---

## 4. RL 신호 (Reinforcement Learning)

**파일**: `analysis/rl_trader.py`

### 4.1 환경 정의

```
State:  (prices[t], position[t], cash[t], MACD[t], RSI[t])
Action: {BUY(+1), HOLD(0), SELL(-1)}
Reward: Δ(portfolio_value) / portfolio_value[t-1]
```

### 4.2 DQN 아키텍처

```
Q(s, a) ← Q(s, a) + α × [reward + γ × max(Q(s', a')) - Q(s, a)]
```

- `α = 0.001` (learning rate)
- `γ = 0.95` (discount factor)
- `ε-greedy` 탐색 파라미터 적용

---

## 5. HMM 시장 레짐 감지 (Hidden Markov Model)

**파일**: `analysis/ml_engine.py` (hmmlearn GaussianHMM)

과거 1일 수익률(`ret_1`)과 10일 변동성(`volatility_10`) 데이터를 관측치(Observation)로 사용하여 시장 상태를 3개의 은닉 상태(Hidden States)로 추정합니다:

```
Observation X_t = [ret_1_t, volatility_10_t]
P(X_t | S_t = i) ~ N(μ_i, Σ_i)   (Gaussian Emission)
Transition Probability Matrix: A_ij = P(S_(t+1) = j | S_t = i)
```

- 학습된 HMM 모델을 기반으로 현재 시점의 가장 높은 사후 확률을 갖는 상태 번호(`hmm_regime` = 0, 1, 2)를 실시간 예측하여 ML 피처로 피드백합니다.

---

## 6. Optuna 하이퍼파라미터 최적화

**파일**: `analysis/ml_engine.py:MLEngine.optimize_hyperparameters()`

- 목적 함수(Objective Function): Time Series Cross Validation (3 splits)을 이용해 예측된 소프트 보팅 확률과 정답 값 간의 **Log Loss (교차 엔트로피 손실)**를 최소화합니다.
- 탐색 범위:
  - `n_estimators`: [50, 300] (50 간격)
  - `max_depth`: [3, 10]
  - `learning_rate`: [0.01, 0.3] (Log Scale)

---

## 7. LLM 신호 (Large Language Model)

**파일**: `ai/llm_integration.py`

### 7.1 프롬프트 구조

```
System: 당신은 전문적인 양적/기본적 주식 트레이더입니다.
User: 종목 {symbol}, 현재가 {price}, 재무 지표 및 기술적 보조 지표 제공...
```

### 7.2 응답 파싱 및 폴백

JSON 형식의 응답에서 `recommendation` 및 `confidence`를 추출합니다. API 오류 또는 키 누락 시 `HOLD` 및 confidence 0.5로 안전 폴백합니다. DeepSeek 어댑터는 R1의 추론 토큰도 투명하게 전송합니다.

---

## 8. 주문 사이징 파이프라인 (Order Sizing Pipeline)

**파일**: `trading_system.py:_create_and_submit_order()`

### 8.1 Kelly Criterion

```
f* = (p × W - L) / (W × L / W_avg)
  p     = win_rate
  W     = avg_win / capital
  L     = avg_loss / capital
  W_avg = avg_win (ratio)

final_f = min(f* × 0.5, 0.25)  # Half Kelly, max 25%
```

### 8.2 Volatility Targeting

```
σ_daily  = ATR(14) / close_price
σ_annual = σ_daily × √252

scale = target_annual_vol (0.15) / (σ_annual + 1e-10)
scale = clamp(scale, 0.25, 2.0)

adjusted_size = base_kelly_size × scale
```

---

## 9. 자동 손절/익절 (Auto SL/TP + Trailing + Partial)

### 9.1 ATR 기반 손절/익절가

```
ATR_stop = entry_price - ATR(14) × atr_multiplier_stop
ATR_tp   = entry_price + ATR(14) × atr_multiplier_target
```

### 9.2 트레일링 스탑 (v4.0)

- 포지션 고점 워터마크가 갱신되면 손절 주문의 트리거 가격을 비례해서 상향 조정합니다:
```
trigger_price = highest_price × (1 - trail_pct)
```

### 9.3 부분 익절 3-티어

- **TP1**: `entry + ATR × 1.5` (수량의 33%)
- **TP2**: `entry + ATR × 3.0` (수량의 33%)
- **TP3**: `entry + ATR × 5.0` (수량의 34%)

---

## 부록: 신호별 가중치 기본값

| 순서 | 신호 | 기본 가중치 | 소스 파일 |
|------|------|------------|----------|
| 1 | Sentiment | 0.20 | `strategy_engine.py` |
| 2 | Technical | 0.30 | `strategy_engine.py` |
| 3 | ML Ensemble | 0.30 | `ml_engine.py` |
| 4 | RL | 0.10 | `rl_trader.py` |
| 5 | DarkPool | 0.00 | `darkpool_tracker.py` |
| 6 | LLM | 0.10 | `llm_integration.py` |
| 7 | Global Market | 0.00 | `global_market_client.py` |
| 8 | Cash Ratio | 0.08 | `strategy_engine.py` |
| 9 | Macro | 0.08 | `strategy_engine.py` |

**합계**: 1.16 (전전략 가중치 정규화 과정을 거쳐 최종 1.0 스케일로 적용됨)

---

**마지막 업데이트**: 2026-06-11

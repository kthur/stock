# 전략 06: 엄격한 인과 시계열 LSTM (Strict Causal LSTM)

## 1. 전략 개요 (Overview)
- **전략 ID**: `lstm` (`lstm_score`)
- **전략 범주**: Deep Learning / Strict Causal Recurrent Neural Network
- **목적**: 과거 시점의 롤링 정규화만을 적용하여 미래 정보 유출(Look-ahead)을 원천 차단한 순수 인과적(Causal) 딥러닝 수익률 시계열 모델.
- **핵심 특징**:
  - **시점 분리 롤링 정규화 (Point-in-Time Rolling Normalization)**: 전체 시계열의 평균/표준편차가 아닌, 과거 $W=60$일 윈도우 내 통계치만으로 인풋 스케일링.
  - **Causal LSTM Architecture**: 양방향(Bi-directional)을 배제하고 순방향 단방향 2-Layer LSTM + Dropout + Dense 헤드로 구성.
  - **다중 시계열 입력**: 종목별 가격/거래량 시계열과 글로벌 매크로 지표 결합.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 인과적 입력 정규화 (Causal Z-Score)
시점 $t$에서의 피처 벡터 $\mathbf{x}_t$에 대해, 과거 $W$일 윈도우 $[t-W, t]$의 통계치만을 사용:
$$\mu_t = \frac{1}{W} \sum_{k=0}^{W-1} \mathbf{x}_{t-k}, \quad \sigma_t = \sqrt{\frac{1}{W} \sum_{k=0}^{W-1} (\mathbf{x}_{t-k} - \mu_t)^2 + \epsilon}$$
$$\tilde{\mathbf{x}}_t = \frac{\mathbf{x}_t - \mu_t}{\sigma_t}$$

### 2.2 LSTM 순전파 (Forward Recurrence)
$$\mathbf{h}_t = \text{LSTM}(\tilde{\mathbf{x}}_t, \mathbf{h}_{t-1})$$
$$\hat{y}_t = \mathbf{w}^\top \mathbf{h}_t + b$$
출력값은 20일 전방 기대수익률 또는 상승 확률을 표현.

### 2.3 스코어 정규화
$$S_{\text{lstm}, i} = \text{Sigmoid}\left( \frac{\hat{y}_i - \bar{y}}{\sigma_y} \right) \in [0.0, 1.0]$$

---

## 3. 입력 텐서 구성 (Input Tensor Shape)

- **입력 형상**: `(Batch_Size, Sequence_Length=60, Num_Features=15)`
- **주요 피처**:
  - `Close_return`, `Volume_ratio`, `High_Low_Range`, `RSI_14`, `MACD_hist`, `Dist_SMA20`
  - `VIX_change`, `USDKRW_change`, `US10Y_yield`

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[종목별 60일 OHLCV 윈도우] --> B[과거 통계치 기반 Z-Score 정규화]
    B --> C[PyTorch Causal LSTM 모델 추론]
    C --> D[20일 전방 방향성 예측치 산출]
    D --> E[Sigmoid 정규화]
    E --> F[lstm_predictions.txt 저장]
```

1. **시퀀스 빌더**: 종목별 최근 60개 봉 데이터를 인과적으로 변환.
2. **모델 추론**: 사전 훈련된 PyTorch LSTM 모델 가중치를 로드하여 일괄 배치 추론.
3. **앙상블 통합**: 스코어 데이터프레임으로 변환 후 앙상블 엔진에 제공.

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BULL_LOW_VOL** | 0.05 | 시계열 모멘텀 지속성 학습 활용 |
| **BULL_HIGH_VOL** | 0.04 | 고변동성 국면 비선형 패턴 해석 |
| **SIDEWAYS_LOW_VOL** | 0.04 | 주기적 파동 및 박스권 학습 포착 |
| **BEAR_LOW_VOL** | 0.03 | 하락 추세 시계열 감쇄 반영 |
| **BEAR_HIGH_VOL** | 0.02 | 위기 상황 노이즈 방지를 위한 비중 축소 |

- **관련 소스 파일**: [`src/ai/prediction_model.py`](file:///d:/Finance/code/stock/trading_system/src/ai/prediction_model.py), [`src/ai/ml_strategy_adapters.py`](file:///d:/Finance/code/stock/trading_system/src/ai/ml_strategy_adapters.py)

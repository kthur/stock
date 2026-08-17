# 전략 27: 카우프만 효율성 비율 및 허스트 지수 (Kaufman Trend Efficiency)

## 1. 전략 개요 (Overview)
- **전략 ID**: `trend_efficiency` (`trend_efficiency_score`)
- **전략 범주**: Technical Quantitative Trend Filter / KER & Hurst Exponent
- **목적**: 페리 카우프만(Perry Kaufman)의 효율성 비율(Kaufman Efficiency Ratio, KER)과 허스트 지수(Hurst Exponent, $H$)를 측정하여, 지그재그 노이즈가 적고 방향성 있는 순수한 추세(Pure Trend)를 형성하는 고순도 추세주를 선별.
- **핵심 특징**:
  - **다기간 KER 결합**: 5일, 10일, 20일 효율성 비율을 결합하여 단기/중기 추세 순도 측정.
  - **허스트 지수 ($H > 0.5$)**: 장기 기억성(Long Memory) 및 추세 지속성 검증 ($H > 0.6$ 강력 추세, $H \approx 0.5$ 랜덤워크, $H < 0.4$ 평균회귀).
  - **노이즈 횡보장 손실 방지**: KER이 낮은 휩소(Whipsaw) 구간 종목 사전 배제.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 카우프만 효율성 비율 (Kaufman Efficiency Ratio, KER)
기간 $N$일 동안의 순 가격 변동폭(Direction)과 일별 절대 변동폭 합(Volatility):
$$\text{Direction}_N = |P_t - P_{t-N}|$$
$$\text{Volatility}_N = \sum_{k=0}^{N-1} |P_{t-k} - P_{t-k-1}|$$
$$\text{KER}_N = \frac{\text{Direction}_N}{\text{Volatility}_N} \in [0.0, 1.0]$$
($\text{KER} = 1.0 \implies$ 단 한 번의 흔들림 없는 완벽한 직선 추세, $\text{KER} \to 0 \implies$ 극심한 노이즈 횡보)

### 2.2 허스트 지수 (Hurst Exponent, $H$)
재조정 범위 분석(Rescaled Range Analysis, $R/S$):
$$(R/S)_n \approx c \cdot n^H$$

### 2.3 복합 추세 효율성 점수
$$\text{TrendEffRaw}_i = 0.40 \cdot \text{KER}_{10, i} + 0.30 \cdot \text{KER}_{20, i} + 0.30 \cdot \max(0.0, H_i - 0.5) \times 2.0$$
$$S_{\text{trend}, i} = \text{clip}(\text{TrendEffRaw}_i, 0.0, 1.0)$$

---

## 3. 입력 데이터 및 처리 방식 (Data Pipeline)

1. **최근 120일 일봉 종가 데이터**: 5d/10d/20d KER 및 $R/S$ 분산 통계 산출.
2. **추세 방향 일치성 검증**: $\text{sign}(P_t - P_{t-20}) > 0$인 상승 추세 종목에만 고득점 부여.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[OHLCV 시계열 수집] --> B[5d / 10d / 20d KER 추세 순도 계산]
    B --> C[R/S 허스트 지수 H 추정]
    C --> D[노이즈 횡보주 필터링 및 추세 순도 점수화]
    D --> E[앙상블 팩터 결합]
```

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BULL_LOW_VOL** | 0.06 | 순도 높은 우상향 추세 추종 최적 (주력 레짐) |
| **BULL_HIGH_VOL** | 0.05 | 강력한 모멘텀 형성주 선별 |
| **SIDEWAYS_LOW_VOL** | 0.03 | 추세 부재 횡보장 감점 필터로 기능 |
| **BEAR_LOW_VOL** | 0.02 | 하락 추세 종목 역선별 배제 |
| **BEAR_HIGH_VOL** | 0.01 | 고변동성 노이즈 장세 비중 축소 |

- **관련 소스 파일**: [`src/core/trend_efficiency.py`](file:///d:/Finance/code/stock/trading_system/src/core/trend_efficiency.py)

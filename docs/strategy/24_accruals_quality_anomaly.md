# 전략 24: 발생액 품질 이상현상 (Accruals Quality Anomaly)

## 1. 전략 개요 (Overview)
- **전략 ID**: `accruals_quality` (`accruals_quality_score`)
- **전략 범주**: Accounting Quality / Sloan Accrual Anomaly
- **목적**: 슬론(Richard Sloan, 1996)의 발생액 이상현상(Accrual Anomaly)을 계량화하여, 회계적 당기순이익 대비 실제 영업현금흐름(Operating Cash Flow, OCF)의 비율이 높아 이익의 질(Quality of Earnings)이 우수한 기업을 선별하고 분식/장부상 이익 기업을 감점.
- **핵심 특징**:
  - **총발생액(Total Accruals) 비율 측정**: $\text{발생액} = \text{당기순이익} - \text{영업활동현금흐름}$.
  - **자산 대비 발생액 비율 (Accruals / Total Assets)**: 자산 규모 표준화.
  - **현금흐름 건전성 검증**: 영업현금흐름 > 순이익 구조를 가진 고품질 재무 기업 우대.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 대차대조표/현금흐름표 기준 발생액 (Balance Sheet & Cash Flow Accruals)
총자산 $A_t$, 당기순이익 $\text{NI}_t$, 영업활동 현금흐름 $\text{CFO}_t$:
$$\text{Accruals}_t = \frac{\text{NI}_t - \text{CFO}_t}{A_{\text{avg}, t}}$$
여기서 $A_{\text{avg}, t} = \frac{A_t + A_{t-1}}{2}$.

### 2.2 이익의 질 점수 (Quality of Earnings Score)
발생액이 낮을수록(즉, 현금 유입이 순이익보다 많을수록) 회계적 품질이 우수함:
$$\text{AccrualRank}_i = 1.0 - \text{PercentileRank}(\text{Accruals}_i)$$

### 2.3 복합 품질 스코어 정규화
$$S_{\text{accrual}, i} = \text{clip}(\text{AccrualRank}_i, 0.0, 1.0)$$

---

## 3. 입력 데이터 및 처리 방식 (Data Pipeline)

1. **분기/연간 재무제표 (60일 공시 시차 엄격 적용)**:
   - 당기순이익, 영업활동으로인한현금흐름, 기초/기말 총자산.
2. **이상치 처리**: 금융업 등 특수 업종은 별도 현금흐름 지표로 조정.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[재무제표 순이익 및 영업현금흐름 수집] --> B[총자산 대비 발생액 비율 산출]
    B --> C[시장 횡단면 백분위 순위 역산]
    C --> D[회계적 품질 스코어 매핑]
    D --> E[앙상블 엔진 팩터 결합]
```

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BEAR_LOW_VOL** | 0.04 | 약세장에서 현금흐름 건전 기업의 강력한 하방 방어 |
| **SIDEWAYS_LOW_VOL** | 0.04 | 실질 현금창출 능력 우량주 부각 |
| **BEAR_HIGH_VOL** | 0.03 | 유동성 위기 시 부실 회계 기업 회피 |
| **BULL_LOW_VOL** | 0.03 | 펀더멘탈 우량주 안정적 지속 |
| **BULL_HIGH_VOL** | 0.02 | 테마 장세 대비 보조 역할 |

- **관련 소스 파일**: [`src/core/accruals_quality.py`](file:///d:/Finance/code/stock/trading_system/src/core/accruals_quality.py)

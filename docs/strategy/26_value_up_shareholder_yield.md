# 전략 26: 밸류업 프로그램 및 주주환원율 (Value-Up & Shareholder Yield)

## 1. 전략 개요 (Overview)
- **전략 ID**: `valueup_catalyst` (`valueup_catalyst_score`)
- **전략 범주**: Policy & Fundamental / Corporate Value-Up & Shareholder Yield
- **목적**: 저PBR(PBR < 1.0) 탈피를 위한 기업 밸류업 프로그램 수혜주, 순현금 비중(Net Cash / Market Cap), 총주주환원율(배당수익률 + 자사주 매입/소각 수익률)이 높은 저평가 주주친화 기업을 선별.
- **핵심 특징**:
  - **총주주환원수익률 (Total Shareholder Yield)**: $\text{배당금} + \text{자사주 취득/소각 금액} / \text{시가총액}$.
  - **순현금 안전마진 (Net Cash Safety Margin)**: 현금성자산 - 총차입금이 시총 대비 큰 자산주 우대.
  - **코리아 디스카운트 해소 수혜**: PBR 1.0 이하이면서 ROE가 개선되는 턴어라운드 종목 가산점.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 총주주환원율 (Total Shareholder Yield, TSY)
$$\text{TSY}_i = \frac{\text{Dividend}_i + \text{Buyback}_i + \text{Retirement}_i}{\text{MarketCap}_i}$$

### 2.2 순현금 비율 및 저PBR 촉매 점수
$$\text{NetCashRatio}_i = \frac{\text{Cash \& Equiv}_i - \text{Total Debt}_i}{\text{MarketCap}_i}$$
$$\text{PBR\_Factor}_i = \max\left(0.0, 1.0 - \text{PBR}_i\right) \times \mathbb{I}(\text{ROE}_i \ge 0.05)$$

### 2.3 복합 밸류업 점수
$$\text{ValueUpRaw}_i = 0.40 \cdot \text{Z}(\text{TSY}_i) + 0.35 \cdot \text{Z}(\text{NetCashRatio}_i) + 0.25 \cdot \text{PBR\_Factor}_i$$
$$S_{\text{valueup}, i} = \text{clip}\left( \frac{\text{ValueUpRaw}_i - \mu_{\text{mkt}}}{3 \sigma_{\text{mkt}}} \cdot 0.5 + 0.5, 0.0, 1.0 \right)$$

---

## 3. 입력 데이터 및 처리 방식 (Data Pipeline)

1. **배당 및 자사주 공시**: 배당결정, 자사주 취득/소각 결정 공시(DART/SEC).
2. **재무제표**: 현금및현금성자산, 단기금융상품, 총차입금, BPS.
3. **60일 공시 시차 적용**: 정보 누수 방지.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[재무제표 및 배당/자사주 공시] --> B[총주주환원율 TSY 및 순현금 산출]
    B --> C[저PBR 및 ROE 개선 검증]
    C --> D[밸류업 수혜 종합 점수화]
    D --> E[앙상블 팩터 결합]
```

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **SIDEWAYS_LOW_VOL** | 0.05 | 횡보장에서 고배당 및 주주환원 가치주 선호 최고 (주력 레짐) |
| **BEAR_LOW_VOL** | 0.04 | 하락장 속 높은 배당수익률로 하방 지지력 발휘 |
| **BULL_LOW_VOL** | 0.04 | 밸류업 정책 모멘텀 동반 랠리 |
| **BEAR_HIGH_VOL** | 0.03 | 순현금 풍부 기업의 안정성 부각 |
| **BULL_HIGH_VOL** | 0.02 | 고성장 성장주 장세 대비 보조 역할 |

- **관련 소스 파일**: [`src/core/valueup_catalyst.py`](file:///d:/Finance/code/stock/trading_system/src/core/valueup_catalyst.py)

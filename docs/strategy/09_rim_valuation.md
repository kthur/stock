# 전략 09: 잔여이익 가치평가 모델 (RIM Valuation)

## 1. 전략 개요 (Overview)
- **전략 ID**: `rim` (`rim_score`)
- **전략 범주**: Fundamental Valuation / Accounting Alpha
- **목적**: 사경인 회계사의 잔여이익모델(Residual Income Model, RIM)을 계량화하여 기업의 자기자본비용(Cost of Equity, $r_e$)을 초과하는 초과이익의 영구가치를 정밀 평가하고 안전마진(Margin of Safety)이 높은 저평가 우량주를 발굴.
- **핵심 특징**:
  - **Terminal Value 보정**: 영구 잔여이익 감소율(감소계수 $\omega \in [0.8, 1.0]$)을 반영하여 장기 지속성 반영.
  - **자본비용($r_e$) 동적 산출**: 국고채 10년물 금리 + 주식시장 위험 프리미엄(ERP) 기반 산출.
  - **60일 공시 시차 적용**: 재무제표 룩어헤드 방지.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 자기자본비용 산출 (Cost of Equity, $r_e$)
$$r_e = R_f + \beta \cdot \text{ERP}$$
(기본값: 한국 시장 $R_f = \text{KTB10Y}$, $\text{ERP} = 5.5\%$, $r_e \approx 8.0\% \sim 10.0\%$)

### 2.2 기업 내재가치 ($V_{\text{RIM}}$)
지배주주 순자산(BPS), 지속 예상 $\text{ROE}$에 대해:
$$\text{RI} = \text{BPS} \cdot (\text{ROE} - r_e)$$
$$\text{초과이익 영구가치} = \begin{cases} \frac{\text{RI} \cdot \omega}{1 + r_e - \omega}, & \text{if } \omega < 1.0 \\ \frac{\text{RI}}{r_e}, & \text{if } \omega = 1.0 \end{cases}$$
$$V_{\text{RIM}} = \text{BPS} + \text{초과이익 영구가치}$$

### 2.3 상승 여력(Upside) 및 스코어 매핑
$$\text{Upside}_i = \frac{V_{\text{RIM}, i} - P_i}{P_i}$$
$$S_{\text{rim}, i} = \text{clip}\left( 0.5 + \frac{\text{Upside}_i}{2.0}, 0.0, 1.0 \right)$$
(상승여력 $+100\% \implies S = 1.0$, 적정가 $0\% \implies S = 0.5$, 하락여력 $-100\% \implies S = 0.0$)

---

## 3. 입력 데이터 및 펀더멘탈 처리 (Input Fundamentals)

1. **지배주주자기자본 (Book Value of Equity)**
2. **최근 3개년 ROE 가중평균**: $\text{ROE}_{\text{est}} = \frac{3 \text{ROE}_{t} + 2 \text{ROE}_{t-1} + \text{ROE}_{t-2}}{6}$
3. **발행주식수 및 현재가**
4. **금리 지표**: 국채 10년물 금리 (`us10y` 또는 `ktb10y`)

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[재무제표 BPS / ROE 60d Lag] --> B[국고채 금리 연동 자본비용 r_e 산출]
    B --> C[초과이익 RI 및 잔여이익 영구가치 합산]
    C --> D[목표주가 V_RIM 및 괴리율 계산]
    D --> E[rim_predictions.txt 저장]
```

1. **재무 수집**: `earnings_data.py`를 통해 최근 공시된 BPS, 당기순이익, ROE 추출.
2. **가치 평가**: `RIMValuationEngine`이 종목별 적정주가 및 안전마진 계산.
3. **리포트 출력**: `rim_predictions.txt`에 적정가, 현재가, 상승여력(%) 명시.

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BEAR_LOW_VOL** | 0.06 | 하락장에서 펀더멘탈 가치 안전마진이 주효 (주력 레짐) |
| **BEAR_HIGH_VOL** | 0.05 | 투매 시 본질가치 대비 극저평가주 담기 |
| **SIDEWAYS_LOW_VOL** | 0.05 | 박스권에서 실적주/가치주 재평가 기회 |
| **BULL_LOW_VOL** | 0.03 | 강세장에서는 모멘텀 대비 보조 지표로 기능 |
| **BULL_HIGH_VOL** | 0.02 | 유동성 과열장에서는 가치 지표 비중 축소 |

- **관련 소스 파일**: [`src/core/rim_valuation.py`](file:///d:/Finance/code/stock/trading_system/src/core/rim_valuation.py)

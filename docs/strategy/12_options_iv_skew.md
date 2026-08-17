# 전략 12: 옵션 내재변동성 스큐 및 풋/콜 비율 (Options IV Skew)

## 1. 전략 개요 (Overview)
- **전략 ID**: `iv_skew` (`iv_skew_score`)
- **전략 범주**: Derivatives Sentiment / Contrarian Volatility Skew
- **목적**: 개별 종목 및 지수 옵션의 풋(Put) 및 콜(Call) 내재변동성(Implied Volatility, IV)의 왜도(Skew)와 풋/콜 비율(Put-Call Ratio)을 분석하여, 극단적 공포(Extreme Fear) 국면에서의 역발상 반등 매수 점수를 산출.
- **핵심 특징**:
  - **IV Skew 측정**: OTM(외가격) 풋 옵션 IV vs OTM 콜 옵션 IV의 스프레드 측정.
  - **역발상 매수(Contrarian Buy)**: 풋 IV가 역사적 극단에 도달하여 하방 패닉이 정점에 달했을 때 반등 신호 포착.
  - **한국/미국 시장 맞춤형 지표**: 미국은 CBOE/yfinance 옵션 체인, 한국은 VKOSPI 및 지수 풋콜 비율 연동.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 25-Delta IV Skew
행사가 $\Delta = -0.25$ 풋 내재변동성 $\sigma_{\text{put}, 25\Delta}$와 $\Delta = +0.25$ 콜 내재변동성 $\sigma_{\text{call}, 25\Delta}$:
$$\text{Skew}_{25\Delta} = \sigma_{\text{put}, 25\Delta} - \sigma_{\text{call}, 25\Delta}$$

### 2.2 풋/콜 거래량 및 미결제약정 비율 (Put-Call Ratio, PCR)
$$\text{PCR} = \frac{\text{Volume}_{\text{Put}}}{\text{Volume}_{\text{Call}}}$$

### 2.3 역발상 공포 점수화 (Fear Contrarian Score)
$$\text{FearZ} = \frac{\text{Skew}_t - \mu_{\text{skew}, 60\text{d}}}{\sigma_{\text{skew}, 60\text{d}}}$$
$$\text{Score}_{\text{iv}} = \begin{cases} 0.5 + 0.25 \cdot \text{FearZ}, & \text{if } \text{FearZ} \ge 1.5 \text{ (극단적 공포 = 강력한 반등 기회)} \\ 0.5 - 0.15 \cdot \text{FearZ}, & \text{if } \text{FearZ} \le -1.5 \text{ (극단적 탐욕 = 고점 경계)} \\ 0.50, & \text{otherwise} \end{cases}$$
최종 스코어 $S_{\text{iv}} \in [0.0, 1.0]$.

---

## 3. 입력 데이터 및 처리 방식 (Data Pipeline)

1. **yfinance 옵션 체인 (미국 주요 대형주)**: 행사가별 내재변동성 및 미결제약정 추출.
2. **글로벌 거시 지표**: VIX, VKOSPI 지수 및 CBOE Put/Call Total Ratio.
3. **폴백 계산**: 옵션 미상장 중소형주의 경우 최근 20일 실현 하방 변동성(Downside Realized Volatility)과 단기 낙폭을 통해 대용치(Proxy) 산출.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[옵션 체인 및 IV 데이터 수집] --> B[25-Delta Skew 및 PCR 계산]
    B --> C[60일 롤링 Z-Score 및 분위수 분석]
    C --> D[역발상 공포/탐욕 전환 시그널 매핑]
    D --> E[iv_skew_predictions.txt 저장]
```

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BEAR_HIGH_VOL** | 0.05 | 극단적 패닉 및 변동성 피크 시 역발상 매수 최적화 (주력 레짐) |
| **BEAR_LOW_VOL** | 0.04 | 서서히 진행되는 하락장의 공포 정점 포착 |
| **SIDEWAYS_LOW_VOL** | 0.03 | 중립적 수준 유지 |
| **BULL_HIGH_VOL** | 0.03 | 과열 경계 신호 반영 |
| **BULL_LOW_VOL** | 0.02 | 안정적 상승장에서는 옵션 왜곡 미미 |

- **관련 소스 파일**: [`src/core/iv_skew.py`](file:///d:/Finance/code/stock/trading_system/src/core/iv_skew.py)

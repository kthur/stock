# 전략 08: 섹터 로테이션 상대 모멘텀 (Sector Rotation Relative Momentum)

## 1. 전략 개요 (Overview)
- **전략 ID**: `sector` (`sector_score`)
- **전략 범주**: Factor / Macro Relative Momentum & Flow
- **목적**: KRX/GICS 업종별 1개월(20일) 및 3개월(60일) 상대 모멘텀과 수급 집중도를 측정하여, 주도 섹터에 속한 우량 종목에 가산점을 부여.
- **핵심 특징**:
  - **다기간 상대 모멘텀 (Multi-Horizon Relative Strength)**: 섹터 지수 vs 시장 벤치마크 지수의 상대강도(RS) 산출.
  - **모멘텀 가속도 (Momentum Acceleration)**: 1개월 단기 모멘텀이 3개월 중기 모멘텀을 상회하는 골든크로스 섹터 포착.
  - **업종 주도주 가중치 부여**: 주도 섹터 내 시총 상위 및 베타 상위 종목에 알파 배분.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 섹터 상대 강도 지수 (Sector Relative Strength)
섹터 $S$의 $T$일 수익률 $R_{S, T}$과 벤치마크 지수(예: KOSPI, SP500) 수익률 $R_{M, T}$:
$$\text{RS}_{S, T} = \frac{1 + R_{S, T}}{1 + R_{M, T}} - 1$$

### 2.2 복합 섹터 모멘텀 스코어 (Composite Sector Score)
$$\text{Score}_S = 0.5 \cdot \text{RS}_{S, 20\text{d}} + 0.3 \cdot \text{RS}_{S, 60\text{d}} + 0.2 \cdot (\text{RS}_{S, 20\text{d}} - \text{RS}_{S, 60\text{d}})$$
가장 최근 20일 상대수익률과 가속도 항$(\text{RS}_{20\text{d}} - \text{RS}_{60\text{d}})$을 결합.

### 2.3 종목별 섹터 스코어 매핑
종목 $i$가 속한 섹터 $S(i)$의 시장 내 순위 백분위수:
$$S_{\text{sector}, i} = \text{PercentileRank}(\text{Score}_{S(i)}) \in [0.0, 1.0]$$

---

## 3. 입력 데이터 및 섹터 매핑 (Universe & Sector Data)

1. **한국 시장 (KRX)**:
   - 반도체, IT하드웨어, 바이오/헬스케어, 2차전지, 자동차, 방산/우주, 원전/전력, 금융/지주 등 18개 주요 업종.
2. **미국 시장 (GICS)**:
   - XLK (Tech), XLV (Health), XLE (Energy), XLF (Financials), XLY (Consumer Disc), XLI (Industrials) 등 11대 SPDR 섹터.
3. **수급 데이터**: 섹터별 외국인/기관 순매수 누적액 결합.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[업종 분류 및 지수 가격 데이터] --> B[1M / 3M 상대강도 RS 계산]
    B --> C[모멘텀 가속도 및 랭킹 산출]
    C --> D[종목별 섹터 점수 전파]
    D --> E[sector_predictions.txt 저장]
```

1. **섹터 수익률 집계**: `SectorRotationEngine`이 개별 종목 데이터를 바탕으로 섹터 평균 수익률 산출.
2. **상대강도 평가**: 시장 벤치마크 대비 초과수익 섹터 랭킹화.
3. **결과 출력**: `sector_predictions.txt`에 섹터별 점수 및 상위 소속 종목 출력.

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BULL_LOW_VOL** | 0.05 | 주도 업종 지속성(Trend Persistence) 극대화 |
| **BULL_HIGH_VOL** | 0.04 | 섹터 간 빠른 순환매 추종 |
| **SIDEWAYS_LOW_VOL** | 0.05 | 테마/업종별 차별화 장세 공략 |
| **BEAR_LOW_VOL** | 0.03 | 경기방어주 및 고배당 섹터 압축 |
| **BEAR_HIGH_VOL** | 0.02 | 전 섹터 동반 하락 시 영향력 제한 |

- **관련 소스 파일**: [`src/core/sector_rotation.py`](file:///d:/Finance/code/stock/trading_system/src/core/sector_rotation.py)

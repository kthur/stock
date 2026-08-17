# 전략 31: 다크풀 블록딜 및 HFT 호가 모멘텀 (Darkpool & HFT Flow)

## 1. 전략 개요 (Overview)
- **전략 ID**: `darkpool` (`darkpool_score`)
- **전략 범주**: Alternative Flow / Dark Pool Block Trades & Micro-Spread Momentum
- **목적**: 공개 시장(Lit Markets)에 노출되지 않는 다크풀(Dark Pools, 장외대량체결/대체거래소)에서의 대형 블록 거래(Block Trades)와 고빈도 매매(HFT) 마이크로 스프레드 압력을 추적하여 은밀한 기관 매집 흐름을 포착.
- **핵심 특징**:
  - **다크풀 거래량 비중 (Dark Pool Activity Index, DPI)**: 전체 거래량 대비 비공개 ATS/장외 체결 비율 측정.
  - **블록 거래 방향성 (Net Block Trade Value)**: 대형 체결의 평균체결가(VWAP) 대비 상단 체결 비중 분석.
  - **한국/미국 시장 다크풀 정합**: 미국 FINRA OTC Off-Exchange 거래 데이터 및 한국 장개시전/시간외 대량매매(블록딜) 데이터 연동.

---

## 2. 수학적 모델 및 수식 (Mathematical Formulation)

### 2.1 다크풀 활동 지수 (Dark Pool Activity Index, DPI)
비공개 다크풀 거래량 $V_{\text{dark}}$, 전체 시장 거래량 $V_{\text{total}}$:
$$\text{DPI}_i = \frac{V_{\text{dark}, i}}{V_{\text{total}, i}}$$

### 2.2 순 블록 매수 금액 (Net Block Trade Direction)
단일 체결 규모 상위 5% 거래 중 VWAP 이상에서 체결된 금액 $B_{\text{up}}$과 이하에서 체결된 금액 $B_{\text{down}}$:
$$\text{NetBlock}_i = \frac{B_{\text{up}, i} - B_{\text{down}, i}}{\text{MarketCap}_i}$$

### 2.3 다크풀 복합 점수
$$\text{DarkRaw}_i = 0.5 \cdot \text{Z}(\text{DPI}_i) + 0.5 \cdot \text{Z}(\text{NetBlock}_i)$$
$$S_{\text{darkpool}, i} = \text{clip}\left( \frac{\text{DarkRaw}_i - \mu_{\text{mkt}}}{3 \sigma_{\text{mkt}}} \cdot 0.5 + 0.5, 0.0, 1.0 \right)$$

---

## 3. 입력 데이터 및 처리 방식 (Data Pipeline)

1. **미국 FINRA TRF / OTC Transparency**: 일별 Off-Exchange Short & Total Volume.
2. **한국 KRX 시간외 대량매매(블록딜) 통계**: 블록딜 거래량, 할인/할증률.
3. **틱 체결 데이터**: 대형 체결(1억원 이상 / 10만 달러 이상) 필터링.

---

## 4. 전체 동작 파이프라인 (Execution Workflow)

```mermaid
flowchart LR
    A[장외/다크풀 체결 및 대량매매 데이터] --> B[DPI 다크풀 비중 산출]
    B --> C[VWAP 대비 대량 매수 체결 방향성 판정]
    C --> D[기관 은밀 매집 점수화]
    D --> E[앙상블 팩터 결합]
```

---

## 5. 2D 레짐별 기본 가중치

| 레짐 | 가중치 | 동작 특성 |
|---|---|---|
| **BULL_LOW_VOL** | 0.05 | 메이저 기관의 장기 포지션 구축 추종 (주력 레짐) |
| **BULL_HIGH_VOL** | 0.04 | 고변동성 국면 대규모 블록 거래 포착 |
| **SIDEWAYS_LOW_VOL** | 0.04 | 횡보장 속 은밀한 장외 매집 선별 |
| **BEAR_LOW_VOL** | 0.03 | 하락장 내 기관 저가 블록 매수 지지 포착 |
| **BEAR_HIGH_VOL** | 0.02 | 유동성 위기 국면 비중 축소 |

- **관련 소스 파일**: [`src/core/hft_engine.py`](file:///d:/Finance/code/stock/trading_system/src/core/hft_engine.py)

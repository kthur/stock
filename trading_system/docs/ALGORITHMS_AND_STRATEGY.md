# 🧠 핵심 알고리즘 및 전략 명세서

> **Version**: 4.1 — 2026-07-30 기준 17대 전략 다변화 앙상블 및 리스크 제어 시스템 반영  
> **Source**: `src/ai/prediction_model.py`, `src/ai/ensemble_scorer.py`, `src/core/*.py`, `src/risk/risk_manager.py`

---

## 목차

1. [전략 1: XGBoost 회귀 (수익률 예측)](#1-전략-1-xgboost-회귀-수익률-예측)
2. [전략 2: Surge 분류기 (급등 확률)](#2-전략-2-surge-분류기-급등-확률)
3. [전략 3: Lead-Lag 분석 (1일 Lag Shift 보정)](#3-전략-3-lead-lag-분석)
4. [전략 4: VCP 규칙 기반 패턴](#4-전략-4-vcp-규칙-기반-패턴)
5. [전략 5: VCP ML 분류기](#5-전략-5-vcp-ml-분류기)
6. [전략 6: Strict Causal LSTM](#6-전략-6-strict-causal-lstm)
7. [전략 7: Stat-Arb Log 공적분 차익거래](#7-전략-7-stat-arb-log-공적분-차익거래)
8. [전략 8: Sector Rotation 상대모멘텀](#8-전략-8-sector-rotation-상대모멘텀)
9. [전략 9: RIM Valuation (Terminal Value 중복 할인 보정)](#9-전략-9-rim-valuation)
10. [전략 10: Event-Driven 공시 촉매](#10-전략-10-event-driven-공시-촉매)
11. [전략 11: Momentum Quality (MQ)](#11-전략-11-momentum-quality-mq)
12. [전략 12: Options IV Skew](#12-전략-12-options-iv-skew)
13. [전략 13: Order Flow Imbalance (MFI)](#13-전략-13-order-flow-imbalance-mfi)
14. [전략 14: Short-Term Reversal](#14-전략-14-short-term-reversal)
15. [전략 15: Analyst Revision Momentum (ARM)](#15-전략-15-analyst-revision-momentum-arm)
16. [전략 16: Cross-Asset Regime Divergence (CARD)](#16-전략-16-cross-asset-regime-divergence-card)
17. [전략 17: Liquidity-Adjusted Tail Risk (LATR - 부호 보정)](#17-전략-17-liquidity-adjusted-tail-risk-latr)
18. [17대 전략 2D 레짐 앙상블 & 실전 미시구조 거래비용 모델](#18-17대-전략-2d-레짐-앙상블--실전-미시구조-거래비용-모델)
19. [자율 매매 에이전트 & RiskManager 위기 제어 규칙](#19-자율-매매-에이전트--riskmanager-위기-제어-규칙)

---

## 1. 전략 1: XGBoost 회귀 (수익률 예측)

**파일**: `src/ai/prediction_model.py` — `OnDevicePredictionModel`

### 1.1 개요

시장별(SP500/KOSPI/KOSDAQ/KONEX) XGBoost + LightGBM + CatBoost **앙상블 회귀** 모델을 학습하여, 각 종목의 **8개 시간 horizon별 예상 수익률**을 예측합니다.

### 1.2 예측 Horizon

| Horizon | 설명 |
|---------|------|
| 1일 | 단기 스캘핑 |
| 5일 | 단기 스윙 |
| 10일 | 중단기 |
| 20일 | 1개월 |
| 30일 | 중기 |
| 60일 | 분기 |
| 120일 | 반기 |
| 200일 | 장기 |

### 1.3 앙상블 구조

세 모델(XGBoost, LightGBM, CatBoost)의 예측값을 **동적 가중 평균**으로 합산합니다:

$$\hat{y} = w_{\text{xgb}} \cdot \hat{y}_{\text{xgb}} + w_{\text{lgb}} \cdot \hat{y}_{\text{lgb}} + w_{\text{cat}} \cdot \hat{y}_{\text{cat}}$$

- 가중치는 검증 세트 R² 점수 기반으로 시장·horizon별 자동 계산
- 기본 가중치: XGBoost 0.4, LightGBM 0.3, CatBoost 0.3

### 1.4 XGBoost 하이퍼파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `n_estimators` | 500 | 부스팅 라운드 |
| `max_depth` | 5 | 트리 깊이 |
| `learning_rate` | 0.05 | 학습률 |
| `subsample` | 0.8 | 행 샘플링 비율 |
| `colsample_bytree` | 0.8 | 열 샘플링 비율 |
| `reg_lambda` | 1.0 | L2 정규화 |
| `early_stopping_rounds` | 50 | 조기 종료 |

### 1.5 타겟 변수

$$\text{target}_{h} = \frac{\text{Close}_{t+h}}{\text{Close}_{t}} - 1$$

극단값 클리핑: $[-0.5\sqrt{h},\ +0.5\sqrt{h}]$

### 1.6 Train/Validation 분리

시계열 특성을 반영한 **날짜 기준 분리** (80% 학습 / 20% 검증):

```
cutoff = dates.quantile(0.80)
train_idx = dates <= cutoff
val_idx = dates > cutoff
```

---

## 2. 전략 2: Surge 분류기 (급등 확률)

**파일**: `src/ai/prediction_model.py` — `train_surge()` / `predict_surge()`

### 2.1 개요

각 종목이 특정 기간 내 **20% 이상 급등**할 확률을 예측하는 **이진 분류** 모델입니다.

### 2.2 Surge Horizon 및 레이블

| Horizon | 레이블 조건 |
|---------|------------|
| 1일 | 1일 수익률 ≥ 20% → 1 |
| 3일 | 3일 수익률 ≥ 20% → 1 |
| 5일 | 5일 수익률 ≥ 20% → 1 |
| 20일 | 20일 수익률 ≥ 20% → 1 |

### 2.3 클래스 불균형 처리

급등은 매우 드문 이벤트이므로, `scale_pos_weight`를 자동 계산하여 양성 클래스에 가중치를 부여합니다:

$$\text{scale\_pos\_weight} = \min\left(\frac{N_{\text{neg}}}{N_{\text{pos}}},\ 500\right)$$

### 2.4 Surge XGBClassifier 하이퍼파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `max_depth` | 4 | (회귀보다 1단계 낮음) |
| `min_child_weight` | 10 | 리프 최소 샘플 |
| `max_delta_step` | 5 | 로짓 업데이트 제한 (불균형 안정화) |
| `scale_pos_weight` | 자동 계산 (≤ 500) | 클래스 불균형 보정 |

### 2.5 최적 임계치 탐색

예측 확률 → 이진 결정 변환 시, 검증 세트에서 F1 점수를 최대화하는 임계치를 그리드 탐색합니다:

```
thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
```

### 2.6 출력

시장별·horizon별 **TOP20** 급등 확률 종목을 `surge_predictions.txt`에 출력합니다.

---

## 3. 전략 3: Lead-Lag 분석

**파일**: `src/ai/prediction_model.py` — `train_lead_lag()` / `predict_lead_lag()`

### 3.1 개요

시가총액 상위 50개 종목(leader)의 최근 움직임과 다른 종목(follower)의 과거 수익률 간 **시차 상관관계(lag-1 correlation)**를 분석하여, leader의 움직임을 뒤따를 가능성이 높은 종목을 발굴합니다.

### 3.2 알고리즘

1. **Leader 선정**: 시가총액 상위 50개 종목
2. **상관 행렬 계산**: 각 leader의 수익률과 모든 종목의 1일 뒤 수익률 간 Pearson 상관 계수
3. **Follower 점수**: 상관계수 × leader 최근 수익률

$$\text{score}_{\text{follower}} = \sum_{i \in \text{leaders}} \rho_i \times r_i^{\text{recent}}$$

4. **필터**: leader 최근 수익률이 1% 이하인 경우 제외

### 3.3 출력

Leader별 상위 20개 follower 종목을 `lead_lag_predictions.txt`에 출력합니다.

---

## 4. 전략 4: VCP 규칙 기반 패턴

**파일**: `src/ai/vcp_detector.py` — `VCPDetector`

### 4.1 개요

**Volatility Contraction Pattern (VCP)**은 Mark Minervini의 트레이딩 전략으로, 변동성이 점진적으로 수축하고 거래량이 감소하면서 주가가 고점 근처에 위치하는 패턴을 감지합니다.

### 4.2 감지 조건

| 조건 | 설명 | 점수 |
|------|------|------|
| 변동성 수축 감소 | 5d > 10d > 20d > 40d > 60d 범위 단조감소 | 25점 |
| 거래량 감소 | 20일 평균 거래량 < 60일 평균 × 0.85 | 15점 |
| 50일 이평 근접 | 현재가와 MA50 거리 5% 이내 | 15점 |
| 200일 이평 상방 | 현재가 > MA200 | 15점 |
| 고점 근접 | 52주 고점의 85% 이상 | 15점 |
| 지지선 확인 | 최근 저점이 상승 추세 | 15점 |
| 패턴 지속 | 2개 이상 수축 사이클 확인 | 20점 |

### 4.3 VCP Score

$$\text{VCP Score} = \min\left(\sum w_i \times \text{condition}_i,\ 100\right)$$

### 4.4 출력

VCP Score ≥ 50 이상인 종목을 `vcp_patterns.txt`에 출력합니다.

---

## 5. 전략 5: VCP ML 분류기

**파일**: `src/ai/vcp_ml_predictor.py` — `VCPSurgePredictor`

### 5.1 개요

VCP 패턴 관련 11개 피처를 사용하여, **4개 시장 × 4개 horizon = 16개** XGBClassifier로 VCP 패턴 이후 급등 확률을 예측합니다.

### 5.2 VCP ML 피처 (11개)

| 피처 | 수식 | 설명 |
|------|------|------|
| `range_5v20` | range(5d) / range(20d) | 단기/중기 변동성 비율 |
| `range_10v20` | range(10d) / range(20d) | 10일/20일 변동성 비율 |
| `range_20v40` | range(20d) / range(40d) | 중기 변동성 수축도 |
| `range_40v60` | range(40d) / range(60d) | 장기 변동성 수축도 |
| `vol_20v60` | vol_avg(20d) / vol_avg(60d) | 거래량 수축 비율 |
| `dist_ma50` | (close - MA50) / MA50 | 50일 이평선 거리 |
| `dist_ma200` | (close - MA200) / MA200 | 200일 이평선 거리 |
| `range_pos_10d` | 최근 10일 양봉 비율 | 단기 추세 강도 |
| `range_pos_20d` | 최근 20일 양봉 비율 | 중기 추세 강도 |
| `atr_14d_norm` | ATR(14) / close | 정규화된 변동성 |
| `monotonic` | 범위 단조감소 여부 (0/1) | VCP 패턴 적합성 |

### 5.3 학습 구조

```
4 시장 (SP500, KOSPI, KOSDAQ, KONEX)
  × 4 horizon (1, 3, 5, 20일)
  = 16개 독립 XGBClassifier
```

각 모델은 해당 시장의 종목 데이터만으로 학습합니다.

### 5.4 출력

시장별 VCP 기반 급등 확률 **TOP10** 종목을 `vcp_ml_predictions.txt`에 출력합니다.

---

## 6. 피처 명세

### 6.1 기본 피처 (FEATURES)

| 카테고리 | 피처 | 설명 |
|----------|------|------|
| **수익률** | `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d` | 기간별 수익률 |
| **이동평균** | `dist_sma_20` | SMA(20) 대비 거리 |
| **변동성** | `vol_20d` | 20일 변동성 |
| **시장 정규화** | `norm_market_cap`, `norm_floating_value`, `norm_volume` | 일별 시장 대비 정규화 |
| **펀더멘탈** | `operating_margin`, `revenue_to_market_cap`, `dividend_yield`, `net_profit_margin`, `eps_yield`, `eps_growth_1y` | 재무 지표 |
| **기술적 지표** | `rsi_14`, `rsi_5`, `macd`, `macd_signal`, `macd_hist_norm` | RSI, MACD |
| **볼린저** | `bb_upper_dist`, `bb_lower_dist`, `bb_width` | 볼린저 밴드 |
| **추가 기술적** | `atr_14`, `roc_10`, `roc_20`, `adx_14` | ATR, ROC, ADX |
| **추세** | `higher_high`, `higher_low`, `distance_from_52w_high`, `ema_crossover` | 추세 지표 |
| **스토캐스틱** | `stoch_k`, `stoch_d`, `stoch_rsi_k`, `stoch_rsi_d` | 스토캐스틱 |
| **일목균형표** | `tenkan_sen`, `kijun_sen` | 일목균형표 |
| **거래량** | `volume_ratio` | 거래량 비율 |
| **VCP** | `range_5v20` ~ `vcp_score` (12개) | VCP 관련 피처 |
| **래그** | `ret_1d_lag1`, `ret_5d_lag1` | 지연 수익률 |

### 6.2 글로벌 피처 (GLOBAL_FEATURES — 8개)

| 피처 | 소스 | 설명 |
|------|------|------|
| `vix_change` | ^VIX | 공포지수 변화율 |
| `us10y` | ^TNX | 미국 10년 국채 수익률 |
| `usdkrw_change` | USD/KRW | 원·달러 환율 변화율 |
| `sp500_change` | ^GSPC | S&P500 지수 변화율 |
| `dxy_change` | DX-Y.NYB | 달러 인덱스 변화율 |
| `wti_change` | CL=F | WTI 원유 변화율 |
| `kospi_change` | ^KS11 | KOSPI 변화율 |
| `kosdaq_change` | ^KQ11 | KOSDAQ 변화율 |

---

## 7. 모델 학습 및 저장

### 7.1 학습 프로세스

1. 시장별 종목 데이터 수집 (ThreadPoolExecutor)
2. 피처 엔지니어링 + 글로벌 지표 병합
3. 시장별 정규화 (일별 시장 총합 대비 비율)
4. 날짜 기준 Train/Val 분리 (80/20)
5. XGBoost + LightGBM + CatBoost 각각 학습
6. 앙상블 가중치 계산 (Val R² 기반)
7. 모델 파일 저장

### 7.2 저장 형식

```
trading_system/models/
├── xgb_regression_{market}_{horizon}d.json     # XGBoost 회귀
├── lgb_regression_{market}_{horizon}d.txt      # LightGBM 회귀
├── cat_regression_{market}_{horizon}d.cbm      # CatBoost 회귀
├── xgb_surge_{market}_{horizon}d.json          # XGBoost Surge
├── lgb_surge_{market}_{horizon}d.txt           # LightGBM Surge
├── cat_surge_{market}_{horizon}d.cbm           # CatBoost Surge
├── vcp_xgb_{market}_{horizon}d.json            # VCP ML
├── ensemble_weights.json                       # 앙상블 가중치
└── tuned_params.json                           # 튜닝된 하이퍼파라미터
```

### 7.3 XGBoost 2.1.4 호환성 Workaround

XGBoost 2.1.4에서 `model.save_model()` 호출 시 `_get_type()` → `TypeError` 버그가 있어,
**Booster 직접 저장** 방식을 사용합니다:

```python
# 저장
model.get_booster().save_model(str(model_path))

# 로드
booster = xgb.Booster()
booster.load_model(str(model_path))
wrapper = xgb.XGBRegressor()
wrapper._Booster = booster
wrapper._estimator_type = 'regressor'
```

---

## 8. 자율 매매 에이전트 & 퀀트 고도화 규칙

**파일**: `src/ai/trading_agent.py` — `TradingAgent`

자율 매매 에이전트는 생성된 투자 시그널을 바탕으로 계좌 자산을 보호하고 리스크를 제한하기 위해 5가지 운영 규칙과 4가지 핵심 퀀트 고도화 알고리즘을 수행합니다.

### 8.1 5대 운영 규칙 (Operational Rules)

1. **위험 관리 (Rule 1)**
   - 단일 거래에 대한 최대 손실 금액이 총 자본금의 2%를 초과할 수 없도록 제한합니다.
   - 켈리 공식 또는 수동 비중으로 계산된 주문 수량이 리스크 한도를 초과할 경우, 리스크 캡 내로 들어오도록 수량을 자동으로 동적 축소(Downsizing)합니다.

2. **시장 상황 및 감성 필터 (Rule 2)**
   - 뉴스 감성 수집기(`NewsSentimentFetcher`)를 통해 조회된 최근 1시간 뉴스 감성 점수 평균이 **-0.2 이하**인 경우 매수를 차단합니다.
   - 공포지수(VIX)가 **30.0 이상**으로 급등하여 시장 불확실성이 극에 달할 경우 신규 매수를 차단합니다.

3. **통계적 우위 검증 (Rule 3)**
   - `TradeJournal`에 기록된 최근 90일 동안의 매도 거래 횟수가 **5회 이상**일 경우, 승률이 **55% 이상**이고 수학적 기대값(Mathematical Edge)이 양수 (\(> 0\))인 경우에만 신규 시그널을 통과시킵니다.
   - 데이터 수(거래 횟수)가 5회 미만일 때는 기본 백테스트 우위 사전 확률(Priors)을 사용해 검증합니다.

4. **의사결정 보고 (Rule 4)**
   - 매수, 매도, 청산 결정을 내리기 전, 거래 방향, 수량, 진입 단가, 손절가, 익절가 및 결정의 구체적인 통계적/정량적 판단 근거를 요약하여 보고서 형식으로 Telegram 알림 시스템을 통해 전송합니다.

5. **비상 대응 프로토콜 (Rule 5)**
   - 시장 지수(KOSPI, S&P500 등)의 일중 등락율이 **5.0% 이상**으로 급변하는 서킷 브레이커 수준의 사태 발생 시, 모든 대기(Pending) 주문을 즉시 취소하고 보유 중인 모든 주식 포지션을 시장가로 전량 즉시 청산하여 현금화합니다.

### 8.2 4대 퀀트 고도화 알고리즘 (Quant Enhancements)

#### Q1. ATR 동적 트레일링 스탑 (Trailing Stop)
기존의 고정 -5% 손절선을 대체하여, 최근 14일간의 변동성 평균인 ATR(Average True Range)을 활용합니다.
- **최고가 추적**: 진입 이후 기록된 최고가(\(\text{HighestPrice}\))를 지속적으로 모니터링합니다.
- **동적 손절선**: \(\text{HighestPrice} - 2.5 \times \text{ATR}_{14}\)로 설정되며, 최고가가 갱신될 때마다 동적으로 함께 올라갑니다. 가격이 이 선 아래로 떨어지면 즉각 매도 청산합니다.
- 고정 익절선(진입가 +15%)은 병행 운영하여 확정 이익을 조기 실현합니다.

#### Q2. Pearson 상관관계 기반 포트폴리오 다각화 (Diversification)
상승 섹터에 대한 과집중(Overweight) 리스크를 최소화하기 위해 신규 진입 종목과 기존 포트폴리오 보유 종목들 간의 동조화를 검사합니다.
- **수익률 계산**: 진입 후보 종목과 기존 보유 종목들의 최근 60영업일 일간 수익률 시계열을 가져옵니다.
- **상관계수 산출**: Pearson 상관계수(\(\rho\))를 행렬 형태로 구합니다.
- **동적 액션**:
  - \(\rho \ge 0.85\): 동조화가 극도로 심한 종목으로 판정하여 진입을 완전히 보류합니다 (`BLOCK`).
  - \(0.70 \le \rho < 0.85\): 동조화가 의심되는 종목으로 판정하여 투자 비중(수량)을 절반으로 감축하여 진입합니다 (`HALVE`).
  - \(\rho < 0.70\): 상관관계가 낮으므로 다각화에 적합한 것으로 판정하여 정상 수량으로 진입합니다 (`OK`).

#### Q3. 위기 단계별 동적 리스크 캡 (Crisis Dynamic Cap)
VIX 지수를 기준으로 계산된 시장 위기 점수(Crisis Score) 및 위기 레벨(Crisis Level)에 따라 단일 거래에 허용하는 리스크 캡(자본금 대비 비율)을 차등 적용합니다:
- **NONE** (평온): 리스크 한도 **2.0%**
- **WATCH** (주의): 리스크 한도 **1.5%**
- **ACTIVE** (위기): 리스크 한도 **1.0%**
- **SEVERE** (심각): 신규 매수 수량을 0으로 제한 (**진입 전면 차단**)

#### Q4. 실효 매매비용 및 슬리피지 내재화 (Net PnL Internalization)
실제 트레이딩 환경에서의 수수료, 세금 및 시장 충격(슬리피지)을 매수/매도 실효 단가에 반영하여 정밀한 Net PnL을 산출합니다:
- **매수 실효가**: \(\text{Price}_{\text{buy\_net}} = \text{Price} \times (1 + \text{Fee}_{\text{buy\_pct}} + \text{Slippage}_{\text{pct}}) = \text{Price} \times 1.00215\) (수수료 0.015%, 슬리피지 0.2% 가정)
- **매도 실효가**: \(\text{Price}_{\text{sell\_net}} = \text{Price} \times (1 - \text{Fee}_{\text{sell\_pct}} - \text{Tax}_{\text{pct}} - \text{Slippage}_{\text{pct}}) = \text{Price} \times 0.99545\) (수수료/거래세 0.255%, 슬리피지 0.2% 가정)
- **Net PnL**: \(( \text{Price}_{\text{sell\_net}} - \text{Price}_{\text{buy\_net}} ) \times \text{Quantity}\)

# 🧠 핵심 알고리즘 및 전략 명세서

> **Version**: 3.0 — 2026-06-21 기준 실제 코드 반영  
> **Source**: `src/ai/prediction_model.py`, `src/ai/vcp_detector.py`, `src/ai/vcp_ml_predictor.py`

---

## 목차

1. [전략 1: XGBoost 회귀 (수익률 예측)](#1-전략-1-xgboost-회귀-수익률-예측)
2. [전략 2: Surge 분류기 (급등 확률)](#2-전략-2-surge-분류기-급등-확률)
3. [전략 3: Lead-Lag 분석](#3-전략-3-lead-lag-분석)
4. [전략 4: VCP 규칙 기반 패턴](#4-전략-4-vcp-규칙-기반-패턴)
5. [전략 5: VCP ML 분류기](#5-전략-5-vcp-ml-분류기)
6. [피처 명세](#6-피처-명세)
7. [모델 학습 및 저장](#7-모델-학습-및-저장)

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

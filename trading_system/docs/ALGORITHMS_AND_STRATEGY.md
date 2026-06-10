# 🧠 주식 자동매매 전략 및 핵심 알고리즘 설명서 (Algorithms & Strategy)

본 문서는 플랫폼의 핵심 수익 창출부인 머신러닝 앙상블 모델, HMM 레짐 기반 스타일 로테이션 전략, Optuna 적응형 파라미터 최적화기 및 리스크 관리 알고리즘의 세부 수학적/공학적 스펙을 명세합니다.

---

## 1. Random Forest + XGBoost 머신러닝 앙상블

플랫폼의 핵심 예측 모듈(`src/analysis/ml_engine.py`)은 전통적인 정형 데이터 강자인 **Random Forest(RF)** 모델과 그래디언트 부스팅 최강자인 **XGBoost(XGB)** 모델을 혼합한 **소프트 보팅(Soft Voting / 가중 평균) 앙상블**을 채택하고 있습니다.

### 1.1 입력 피처 엔지니어링 (24개 피처)
데이터 편향을 줄이고 예측 성능을 극대화하기 위해 다음 24개의 다차원 피처를 생성 및 활용합니다:
- **이동평균 크로스오버**: `MA_5_20_ratio`, `MA_20_60_ratio`
- **모멘텀 및 강도 지표**: `RSI_14`, `MACD`, `MACD_signal`, `MACD_hist`, `ROC_10` (Rate of Change)
- **변동성 및 시장 폭**: `Bollinger_width`, `ATR_14_ratio`
- **거래량 지표**: `OBV_ratio` (On-Balance Volume), `Volume_MA_ratio`
- **기타 통계치**: 가격 Z-score 정규화 결과 등 24종 기술적 지표.

### 1.2 소프트 보팅 합산 공식
두 모델이 각각 독립적으로 도출한 매수 확률 예측값을 50:50의 비율로 가중 평균하여 최종 `ml_score`를 산출합니다.

$$\text{ml\_score} = 0.5 \times P_{\text{RandomForest}}(\text{Class}=1) + 0.5 \times P_{\text{XGBoost}}(\text{Class}=1)$$

최종 산출되는 `ml_score`는 **`0.0` ~ `1.0`** 사이의 실수 범위로 한정되며, 설정된 임계치(예: `0.65`)를 상회할 시 매수 강도 강화 신호로 활용됩니다.

### 1.3 하이퍼파라미터 최튜닝 (Optuna & TimeSeriesSplit)
- 데이터 누수(Data Leakage)를 원천 차단하기 위해 일반 K-Fold 대신 시계열의 순차적 정렬을 보장하는 `TimeSeriesSplit` 교차 검증을 사용합니다.
- **Optuna** 프레임워크를 연동하여 XGBoost의 `max_depth`, `learning_rate`, `n_estimators` 및 Random Forest의 `min_samples_split` 등을 자동으로 탐색해 Log Loss를 최소화하고 승률을 최적화합니다.

---

## 2. HMM 시장 레짐 감지 & 유명 자산가 스타일 로테이션

시장 환경의 변화에 유연하게 대처하기 위해, 플랫폼은 시장 지수를 감시하여 현재 국면을 감지하고 그에 가장 유효한 포트폴리오 전략을 채택하는 **스타일 로테이션(Style Rotation)** 구조(`src/analysis/style_rotator.py`)를 제공합니다.

### 2.1 GaussianHMM 기반 시장 국면 감지
보정된 지수 종가의 일일 수익률과 일방 변동성을 2차원 관측 데이터로 삼아, 은닉 마르코프 모형(**Gaussian Hidden Markov Model**)을 통해 시장 국면을 3단계로 실시간 분류합니다:
1. **Regime 0 (안정 상승장)**: 높은 평균 수익률, 낮은 변동성.
2. **Regime 1 (횡보/조정장)**: 제로에 수렴하는 수익률, 중간 변동성.
3. **Regime 2 (패닉 하락장)**: 음의 평균 수익률, 극도로 높은 변동성.

### 2.2 국면별 투자가 전략 매핑 (`src/strategy/famous_investors.py`)

시장 국면(Regime)에 맞춰 다음 4대 시그니처 전략 중 최적의 비중 배분을 제안합니다:

| 시장 국면 (Regime) | 추천 포트폴리오 스타일 | 전략 상세 및 조건식 스펙 |
| :--- | :--- | :--- |
| **안정 상승장 (Regime 0)** | **Peter Lynch (성장주/GARP)** | - PER 대비 이익성장률 비율(PEG)이 `1.0` 미만인 종목 필터링.<br>- 신저점 돌파 및 중소형 모멘텀 가중. |
| **횡보/조정장 (Regime 1)** | **Warren Buffett (가치 투자)** | - ROE가 15% 이상이고, PBR이 `1.5` 이하인 안정적 해자 종목.<br>- 부채 비율이 낮고 잉여현금흐름(FCF)이 풍부한 기업 발굴. |
| **패닉 하락장 (Regime 2)** | **Ray Dalio (올웨더/자산배분)** | - 단일 종목 위험 극단 통제.<br>- 변동성 역수 가중치(Risk Parity) 및 ATR 기반 안전 배분 비율 확대. |
| **강한 추세장** | **Trend Following (추세 추종)** | - 20일, 50일, 200일 지수이동평균선(EMA) 정배열 돌파 기법.<br>- 윌리엄스 %R 또는 ADX를 활용한 추세 강도 추적. |

---

## 3. 적응형 파라미터 최적화기 (Adaptive Optimizer)

시간에 따라 변하는 시장의 미시구조(Microstructure)에 대응하기 위해, `AdaptiveParameterOptimizer`(`src/analysis/adaptive_optimizer.py`)는 매 주기 백테스트 성과 지표를 백그라운드 분석하여 매매 규칙 파라미터를 실시간 조정합니다.

### 3.1 동적 피드백 제어 흐름
1. 최근 $N$일간의 실시간 체결 로그와 모의 백테스트 결과를 취합합니다.
2. **평가 함수(Objective Function)**로 샤프 비율(Sharpe Ratio)의 극대화와 최대 낙폭(MDD)의 최소화를 혼합한 효용 함수 $U$를 정의합니다:

$$U = w_1 \times \text{SharpeRatio} - w_2 \times \text{MDD}$$

3. Optuna 탐색을 통하여 익절선 비율(take_profit_pct), 손절선 비율(stop_loss_pct), ML 예측 임계치(ml_threshold)의 최적 점을 탐색해 설정값(`.env` 및 내부 설정 메모리)에 동적 업데이트합니다.

---

## 4. 리스크 매니저 통제 정책 (Risk Manager Limits)

매매 체결부 최전방에 위치하는 `RiskManager`(`src/risk/risk_manager.py`)는 사전에 정해진 규칙에 입각하여 과도한 위험 노출을 완전히 제어합니다.

- **Stop-loss (손절 한도)**: 진입가 대비 설정된 범위(기본값: `-3%`)를 이탈 시 시장가 청산 신호 자동 발행.
- **Take-profit (익절 한도)**: 진입가 대비 설정된 목표치(기본값: `+10%`) 도달 시 자동 익절 매도 처리.
- **종목별 최대 비중(Max Weight Limit)**: 아무리 훌륭한 매수 신호가 발생해도, 해당 종목이 전체 포트폴리오 평가 자산의 특정 한도(기본값: `20%`)를 초과하여 적재되지 못하도록 주문 수량을 자동으로 하향 조정.
- **포트폴리오 서킷 브레이커**: 당일 손실이 총 자산 대비 `-5%`를 초과할 시 시스템의 당일 매수 주문 송신 기능을 차단하고 전체 강제 청산 대기 상태로 전환.

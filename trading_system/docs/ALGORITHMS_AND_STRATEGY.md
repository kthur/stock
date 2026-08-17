# 🧠 31대 다변화 전략 및 퀀트 알고리즘 완전 명세서

> **Version**: 5.0  
> **Last Updated**: 2026-08-17 (KST)  
> **Source Modules**: `trading_system/src/core/*.py`, `src/ai/`, `src/risk/`, `src/execution/`  
> **Target Universe**: 한국(KOSPI, KOSDAQ) 및 미국(S&P 500, NASDAQ, RUSSELL 2000) 5대 시장

---

## 📑 목차

1. [31대 다변화 전략 종합 일람](#1-31대-다변화-전략-종합-일람)
2. [머신러닝 & 시계열 딥러닝 엔진 (전략 1~6)](#2-머신러닝--시계열-딥러닝-엔진-전략-16)
3. [차익거래 & 펀더멘탈 가치평가 엔진 (전략 7~10)](#3-차익거래--펀더멘탈-가치평가-엔진-전략-710)
4. [모멘텀 & 퀀트 팩터 엔진 (전략 11~18)](#4-모멘텀--퀀트-팩터-엔진-전략-1118)
5. [공급망, 감성 & 대체 데이터 엔진 (전략 19~23)](#5-공급망-감성--대체-데이터-엔진-전략-1923)
6. [회계 품질 & 특수 촉매 엔진 (전략 24~31)](#6-회계-품질--특수-촉매-엔진-전략-2431)
7. [통계적 직교화 및 팩터 억제 (Statistical Hygiene)](#7-통계적-직교화-및-팩터-억제-statistical-hygiene)
8. [2D 시장 레짐 & 동적 앙상블 가중치](#8-2d-시장-레짐--동적-앙상블-가중치)
9. [포트폴리오 최적화 & EVT-CVaR 꼬리위험 예산](#9-포트폴리오-최적화--evt-cvar-꼬리위험-예산)
10. [실전 미시구조 거래비용 및 슬리피지 피드백](#10-실전-미시구조-거래비용-및-슬리피지-피드백)
11. [Execution OMS 6대 주문 안전 게이트](#11-execution-oms-6대-주문-안전-게이트)

---

## 1. 31대 다변화 전략 종합 일람

| # | 전략명 | 분류 | 핵심 수식 / 메커니즘 | 주요 입력 데이터 | 출력 파일 |
|---|--------|------|----------------------|------------------|-----------|
| **1** | **XGBoost 회귀** | ML 회귀 | 8개 horizon GBDT 앙상블 $\hat{r}_h \in [-1, 1]$ | OHLCV, 23개 기술/재무 피처 | `pipeline_result.txt` |
| **2** | **Surge 분류기** | ML 분류 | $P(\text{Return} \ge 20\%)$ (Class weight $\le 20$) | 4개 horizon, 변동성/모멘텀 | `surge_predictions.txt` |
| **3** | **Lead-Lag 분석** | 시차 상관 | 2-Tier 리더-팔로워 상관행렬 (+1d US 시차) | 지수/ETF/대형주 일별 수익률 | `lead_lag_predictions.txt` |
| **4** | **VCP 패턴 (규칙)** | 기술적 패턴 | Minervini 4단계 변동성 수축 & 거래량 급감 | 일봉 고저가, 20d 거래량 MA | `vcp_patterns.txt` |
| **5** | **VCP ML 분류기** | ML 분류 | 12개 패턴 벡터 피처 기반 XGBClassifier | 수축률, 단조성, ATR 정규화 | `vcp_ml_predictions.txt` |
| **6** | **Strict Causal LSTM** | 딥러닝 시계열 | 롤링 z-score 정규화 기반 룩어헤드 방지 LSTM | 60일 윈도우 순차 OHLCV | `lstm_predictions.txt` |
| **7** | **Stat-Arb Cointegration**| 통계적 차익 | Engle-Granger Log 주가 잔차 $Z < -2.0$ | 페어별 일간 종가 시계열 | `stat_arb_predictions.txt` |
| **8** | **Sector Rotation** | 상대 모멘텀 | 1M/3M 업종 상대강도 + 기관/외인 수급 가속도 | KRX/GICS 섹터 지수, 순매수 | `sector_predictions.txt` |
| **9** | **RIM Valuation** | 잔여이익 모델 | $V_0 = B_0 + \sum \frac{(\text{ROE}-k_e)B_{t-1}}{(1+k_e)^t}$ 적정가 | BPS, ROE, 요구수익률($k_e$) | `rim_predictions.txt` |
| **10** | **Event-Driven** | 이벤트 촉매 | DART 공시, 서프라이즈($>15\%$), $3\times$ 거래량 | OpenDART 공시, 컨센서스 | `event_driven_predictions.txt` |
| **11** | **Momentum Quality** | 팩터 모멘텀 | $(R_{12M} - R_{1M}) \times (\text{OP Margin} \times \text{ROE})$ | 12M-1M 수익률, 재무제표 | `mq_factor_predictions.txt` |
| **12** | **Options IV Skew** | 옵션 미시구조 | $\text{IV}_{\text{put}} - \text{IV}_{\text{call}}$ 공포 역발상 매수 | yfinance 옵션 체인 IV | `iv_skew_predictions.txt` |
| **13** | **Order Flow Imbalance** | 수급 흐름 | 외인/기관 순매수 가속도 (MFI 차분) | 거래소 투자자별 순매수 | `order_flow_predictions.txt` |
| **14** | **Short-Term Reversal** | 평균 회귀 | 3~5일 연속 하락 과매도 ($RSI < 30, z < -2$) | 일봉 종가, 볼린저 밴드 | `short_term_reversal_predictions.txt` |
| **15** | **Analyst Revision** | 컨센서스 수정 | $\Delta \text{EPS}_{\text{consensus}} / \text{EPS}_{\text{prior}}$ 상향 속도 | FnGuide / Refinitiv 컨센서스 | `arm_factor_predictions.txt` |
| **16** | **Cross-Asset Divergence**| 매크로 괴리 | 주식 vs 환율/유가/금리 매크로 이탈 괴리율 | USD/KRW, WTI, US10Y | `card_factor_predictions.txt` |
| **17** | **Liquidity Tail Risk** | 유동성/꼬리위험| $DD_{52w} + \text{VolumeSurge} - \text{CVaR}_{95\%}$ | 52주 고점 낙폭, EVT tail | `latr_factor_predictions.txt` |
| **18** | **Inst & Foreign Sector**| 수급 주도주 | 기관/외인 60일 누적 순매수 & 주도주 상관성 | 투자자별 누적 순매수 대금 | `inst_foreign_sector_predictions.txt` |
| **19** | **Supply Chain Momentum**| 가치사슬 전이 | 전방 대표기업 수익률 $\to$ 협력사 시차 온기 | 서플라이 체인 관계도, 수익률 | `supply_chain_predictions.txt` |
| **20** | **NLP Sentiment Catalyst**| FinBERT 감성 | DART/SEC 공시 및 뉴스 FinBERT 감성 점수 | 공시 요약, 뉴스 헤드라인 | `sentiment_predictions.txt` |
| **21** | **Style Neutralizer** | 팩터 중립화 | Fama-French 5-Factor 잔차화 ($\|\rho\| < 0.15$) | 시총, PBR, OP, 자산성장률 | `factor_neutralized_predictions.txt` |
| **22** | **Dynamic Vol Target** | 리스크 파리티 | 실산출 변동성 vs 목표 변동성(12%) 비중 스코어 | 20일/60일 실현 변동성 | `vol_target_predictions.txt` |
| **23** | **Microstructure Imbalance**| 호가창/동시호가 | 호가 잔량 불균형(OFI) & 동시호가 오버나이트 갭 | 5단계 호가잔량, 시초가 갭 | `microstructure_predictions.txt` |
| **24** | **Accruals Quality** | 회계 이상치 | $(\text{NetIncome} - \text{OCF}) / \text{TotalAssets}$ | 현금흐름표, 당기순이익 | 앙상블 결합 |
| **25** | **Short Squeeze** | 숏스퀴즈 | Short Interest + Days-to-Cover + 5D 모멘텀 | 공매도 잔고, 대차잔고 | 앙상블 결합 |
| **26** | **Value-Up Catalyst** | 주주환원 | PBR < 1.0 + 순현금/시총 + 총주주환원율 | 배당성향, 자사주 소각 | 앙상블 결합 |
| **27** | **Kaufman Trend Eff** | 추세 효율성 | 5D/10D/20D KER + Hurst Exponent ($H > 0.5$) | 일봉 방향성 변위 / 총이동거리 | 앙상블 결합 |
| **28** | **Gamma Squeeze** | 감마 스퀴즈 | 옵션 미결제약정(OI) 및 콜옵션 델타 가속도 | 풋콜 OI, 델타/감마 익스포저 | 앙상블 결합 |
| **29** | **Insider Buying** | 내부자 매수 | 대주주/임원 장내 매수 공시 및 지분 변동률 | DART/SEC 내부자 지분 공시 | 앙상블 결합 |
| **30** | **Earnings Tone Drift** | 어닝콜 톤 분석 | 실적발표 콘퍼런스콜 텍스트 긍/부정 어조 변화 | 어닝콜 스크립트 텍스트 | 앙상블 결합 |
| **31** | **High-Frequency Exec** | HFT 마이크로 | 다크풀 블록체결 & 틱 스프레드 마이크로구조 | 다크풀 거래량, 틱 스프레드 | 앙상블 결합 |

---

## 2. 머신러닝 & 시계열 딥러닝 엔진 (전략 1~6)

### 2.1 전략 1: XGBoost Multi-Horizon Regression (`prediction_model.py`)
- **목적**: 8개 시간 horizon ($1\text{d}, 3\text{d}, 5\text{d}, 10\text{d}, 20\text{d}, 60\text{d}, 120\text{d}, 200\text{d}$)에 대한 기대수익률 $\hat{r}_h$ 동시 예측.
- **모델 앙상블**: XGBoost(0.40) + LightGBM(0.30) + CatBoost(0.30) 블렌딩.
- **타겟 스케일링**:
  $$M_h = \begin{cases} 0.15 & (h \le 5\text{d}) \\ 0.25 & (h \le 20\text{d}) \\ 0.40 & (h \le 60\text{d}) \\ 0.80 & (h \le 200\text{d}) \end{cases}, \quad S_{\text{reg}} = \operatorname{clip}\left(\frac{\hat{r}_h}{M_h}, 0.0, 1.0\right)$$
- **피처 엔지니어링**: 기술적 지표(EMA, RSI, MACD, BB, ATR) + 거시경제(VIX, TNX, USDKRW, Oil) + 펀더멘탈(PER, PBR, ROE, 영업이익률 등 23개 피처).

### 2.2 전략 2: Surge Classifier (`prediction_model.py`)
- **목적**: $h \in \{1\text{d}, 3\text{d}, 5\text{d}, 20\text{d}\}$ 기간 내 $+20\%$ 이상 급등 확률 예측.
- **불균형 가중치 캡**:
  $$\text{scale\_pos\_weight} = \min\left(\frac{N_{\text{neg}}}{N_{\text{pos}}}, 20.0\right)$$
- 극단적인 가중치 폭주를 방지하여 정밀도(Precision)를 유지.

### 2.3 전략 3: Cross-Border Lead-Lag Matrix (`cross_border_lead_lag.py`)
- **2-Tier 구조**: Tier 1 (업종 대표 ETF 및 글로벌 대형주), Tier 2 (개별 추종주).
- **시차 보정**: 미국 시장 지표/ETF는 한국 시장 대비 **+1일 Lag Shift**를 적용하여 시차 룩어헤드 방지.
- **스코어링**: 상관계수 $\rho_{ij}$와 리더의 5일 가속도를 결합하여 후행 점수 산출.

### 2.4 전략 4 & 5: Mark Minervini VCP Rule & ML (`vcp_detector.py`, `vcp_ml_predictor.py`)
- **규칙 탐지기**: 3~4회 연속 변동성 수축 (예: $20\% \to 10\% \to 5\% \to 2\%$), 거래량 20일 MA 대비 $50\%$ 미만 건조화(Dry-up), 피봇 저항선 근접($<2\%$).
- **VCP ML**: 12개 패턴 벡터 피처(`range_5v20`, `vol_20v60`, `monotonic_decay`, `pivot_proximity`)를 학습한 XGBClassifier.

### 2.5 전략 6: Strict Causal LSTM (`lstm_predictor.py`)
- **아키텍처**: 2-layer LSTM + Dropout(0.2) + Linear Output Head.
- **인과적 정규화 (Causal Normalization)**: 전체 시계열 평균 대신 각 시점 $t$ 이전의 60일 롤링 윈도우 $\mu_{t-60:t}, \sigma_{t-60:t}$만을 사용하여 Z-score 정규화. 미래 데이터 누출(Data Leakage) 완전 차단.

---

## 3. 차익거래 & 펀더멘탈 가치평가 엔진 (전략 7~10)

### 3.1 전략 7: Stat-Arb Log Cointegration (`stat_arb.py`)
- **Engle-Granger 2단계 회귀**: raw price $P$ 대신 Log 가격 $\ln P$를 사용하여 스케일 불변성 확보:
  $$\ln P_{A, t} = \alpha + \beta \ln P_{B, t} + \epsilon_t$$
- **ADF 공적분 검정**: 잔차 $\epsilon_t$에 대해 ADF 검정 통과($p < 0.05$) 및 반감기(Half-Life) $\tau \in [3, 30]$일 필터링.
- **신호**: 잔차 Z-score $Z_t = \frac{\epsilon_t - \mu_\epsilon}{\sigma_\epsilon} < -2.0$ 시 매수 진입.

### 3.2 전략 8: Sector Rotation Relative Momentum (`sector_rotation.py`)
- 11개 KRX/GICS 섹터 지수의 1M/3M 상대수익률 및 기관/외인 순매수 가속도를 합성하여 주도 업종 스코어링.

### 3.3 전략 9: RIM Valuation Model (`rim_valuation.py`)
- **잔여이익 가치평가**:
  $$V_0 = B_0 + \sum_{t=1}^5 \frac{(\text{ROE}_t - k_e) B_{t-1}}{(1 + k_e)^t} + \frac{(\text{ROE}_5 - k_e) B_4 \cdot \omega}{(1 + k_e - \omega)(1 + k_e)^5}$$
- **보정 사항**: 자기자본비용 $k_e$ 할인 시 Terminal Value 중복 할인 오류 제거, 음수 영업이익/순이익 기업 필터링.

### 3.4 전략 10: Event-Driven Catalyst Engine (`event_driven.py`)
- OpenDART 실시간 공시(유상증자, 무상증자, 전환사채, 주주총회, 자사주 취득/소각) 파싱.
- 컨센서스 대비 어닝 서프라이즈 $>15\%$, 일일 거래량 $3\times$ 서지 결합 촉매 스코어링.

---

## 4. 모멘텀 & 퀀트 팩터 엔진 (전략 11~18)

- **전략 11 (MQ Factor)**: $12\text{M}-1\text{M}$ 장기 모멘텀에서 1M 단기 반전 노이즈를 차감하고 영업이익률 $\times$ ROE 퀄리티 결합.
- **전략 12 (Options IV Skew)**: 풋/콜 IV 괴리율($\text{IV}_{\text{put}} - \text{IV}_{\text{call}}$) 및 Put/Call Volume Ratio 극단값 역발상(Contrarian) 매수.
- **전략 13 (Order Flow Imbalance)**: 외인/기관 순매수 대금 가속도 및 자금유입강도(MFI) 지표 결합.
- **전략 14 (Short-Term Reversal)**: 3~5일 연속 음봉 과매도($RSI_{14} < 30$, 볼린저 하단 이탈 $z < -2.0$) 기술적 반등 스코어링.
- **전략 15 (Analyst Revision)**: 애널리스트 컨센서스 EPS 및 목표주가 1M/3M 상향 조정 속도.
- **전략 16 (Cross-Asset Divergence)**: 주식 지수와 환율(USD/KRW), 국제유가(WTI), 미국 10년물 금리(US10Y) 크로스에셋 괴리율 스코어링.
- **전략 17 (Liquidity-Adjusted Tail Risk)**: 52주 고점 대비 낙폭($DD_{52w}$) + 거래량 서지 지수에서 EVT $\text{CVaR}_{95\%}$ 하방 꼬리위험 페널티 차감.
- **전략 18 (Inst & Foreign Sector)**: 외인/투신 60일 누적 순매수 강도 및 업종 주도주 상관성 점수.

---

## 5. 공급망, 감성 & 대체 데이터 엔진 (전략 19~23)

- **전략 19 (Supply Chain Momentum)**: 전방 완성품 대기업(예: 삼성전자, 현대차, 애플) 1D/3D 급등 시 1~3일 시차를 두고 부품/장비 공급망 협력사로 온기가 전이되는 모멘텀 파급 스코어링.
- **전략 20 (NLP Sentiment Catalyst)**: DART/SEC 공시 요약문 및 뉴스 텍스트를 FinBERT 모델로 감성 분류하여 긍정/부정 스코어 산출.
- **전략 21 (Multi-Factor Style Neutralizer)**: Fama-French 5-Factor(Market, SMB, HML, RMW, CMA)에 대한 회귀 잔차를 추출하여 순수 종목 고유 알파($\|\rho\| < 0.15$) 산출.
- **전략 22 (Dynamic Volatility Targeting)**: 실현 변동성과 포트폴리오 목표 변동성(연 12%)을 비교하여 리스크 파리티 비중 스코어링.
- **전략 23 (Microstructure Imbalance)**: 호가창 매수/매도 잔량 불균형(Order Book Imbalance) 및 장 마감 동시호가 수급 오버나이트 갭 점수.

---

## 6. 회계 품질 & 특수 촉매 엔진 (전략 24~31)

- **전략 24 (Accruals Quality Anomaly)**: 순이익과 영업활동현금흐름(OCF) 간의 발생액 괴리율 $\frac{\text{Net Income} - \text{OCF}}{\text{Total Assets}}$ 회계적 투명성 점수.
- **전략 25 (Short Interest & Squeeze)**: 공매도 잔고 비율, Days-to-Cover, 5일 상승 모멘텀을 결합한 숏스퀴즈 발생 확률.
- **전략 26 (Value-Up & Shareholder Yield)**: 저PBR(<1.0) + 순현금/시총 비율 + 총주주환원율(배당수익률 + 자사주 소각률).
- **전략 27 (Kaufman Trend Efficiency)**: Kaufman Efficiency Ratio (KER) 및 Hurst Exponent ($H > 0.5$) 기반 고순도 추세 필터.
- **전략 28 (Gamma Squeeze)**: 옵션 미결제약정(OI) 집중 구간 및 콜옵션 델타 가속도 기반 델타/감마 헤지 스퀴즈.
- **전략 29 (Insider Buying)**: 임원 및 주요주주 내부자 장내 매수 공시 수치화.
- **전략 30 (Earnings Tone Drift)**: 콘퍼런스콜 어닝콜 질의응답 텍스트 톤 변화 감성 퀀트.
- **전략 31 (High-Frequency Darkpool & Microspread)**: 다크풀 대량 블록딜 체결 및 틱 스프레드 마이크로구조 모멘텀.

---

## 7. 통계적 직교화 및 팩터 억제 (Statistical Hygiene)

### 7.1 PCA-ZCA 대칭 화이트닝 & Gram-Schmidt 직교화
- **PCA-ZCA 대칭 화이트닝**:
  $$C = V \Lambda V^T, \quad C^{-1/2} = V \Lambda^{-1/2} V^T, \quad X_{\text{decorr}} = \bar{X} \cdot C^{-1/2}$$
  - 순서 편향 없이 모든 팩터 간 상관관계를 $0.0$으로 정규 직교화.
- **순차 Gram-Schmidt**: 레짐 가중치 순으로 정렬 후 선행 요인에 대한 사영(Projection) 성분 제거.

### 7.2 결측 적응형 동적 재정규화 (Missingness-Aware Renormalization)
- 특정 종목에 데이터(옵션, 재무 등)가 결측된 경우, 유효한 전략 집합 $V_i$에 대해 가중치를 재스케일링:
  $$S_{\text{linear}, i} = \frac{\sum_{k \in V_i} w_k \cdot s_{k, i}}{\sum_{k \in V_i} w_k}$$
- 커버리지 비율 $\frac{|V_i|}{K} < 0.40$ 미달 시 신뢰도 페널티 부과.

---

## 8. 2D 시장 레짐 & 동적 앙상블 가중치

### 8.1 6대 2D 레짐 매트릭스
20일 벤치마크 추세($\pm 1\%$)와 20일 실현 변동성(15% / 25%)을 결합:
1. `BULL_LOW_VOL`: 모멘텀, VCP ML, Surge 가중치 극대화
2. `BULL_HIGH_VOL`: Gamma Squeeze, Vol Target 가중치 강화
3. `SIDEWAYS_LOW_VOL`: Stat-Arb, RIM Valuation, Value-Up 가중치 강화
4. `SIDEWAYS_HIGH_VOL`: Short-Term Reversal, Stat-Arb 가중치 강화
5. `BEAR_LOW_VOL`: Accruals Quality, RIM Valuation 방어 팩터 강화
6. `BEAR_HIGH_VOL`: Short Squeeze, 현금 비중 극대화 & 리스크 게이팅

---

## 9. 포트폴리오 최적화 & EVT-CVaR 꼬리위험 예산

### 9.1 Hierarchical Risk Parity (HRP) & Ledoit-Wolf 축소
- 자산 간 상관거리 $d_{ij} = \sqrt{\frac{1 - \rho_{ij}}{2}}$ 기반 계층적 군집 트리(Tree) 생성.
- Ledoit-Wolf 수축 공분산 행렬 $\Sigma_{\text{shrunk}} = (1 - \delta)\Sigma + \delta \nu I$ ($\delta = 0.15$)을 적용하여 역행렬 불안정성 제거.

### 9.2 EVT-CVaR 3단계 계층 예산
- Peaks-Over-Threshold (POT) 기반 Generalized Pareto Distribution (GPD) 적합 $\to$ Cornish-Fisher $\to$ Empirical 3단계 폴백으로 95% CVaR 산출 및 포트폴리오 꼬리위험 통제.

### 9.3 Leland 동적 No-Trade 버퍼 밴드
- 불필요한 잦은 매매를 방지하기 위해 종목별 마찰비용과 변동성을 반영한 버퍼 밴드 $\delta_i \in [0.5\%, 5.0\%]$ 적용:
  $$w_{i, \text{current}} \in [w_{i, \text{target}} - \delta_i, \; w_{i, \text{target}} + \delta_i] \implies \text{HOLD}$$

---

## 10. 실전 미시구조 거래비용 및 슬리피지 피드백

### 10.1 시장별 거래비용 모델
- **KOSPI**: 증권거래세 0.15% + 브로커 수수료 0.03% + 동적 스프레드 $S_i$ + Kyle 시장 충격
- **KOSDAQ**: 증권거래세 0.18% + 브로커 수수료 0.03% + 동적 스프레드 $S_i$ + Kyle 시장 충격
- **S&P 500 / NASDAQ**: SEC Fee 0.003% + 브로커 수수료 0.005% + 동적 스프레드 + 시장 충격

### 10.2 슬리피지 피드백 루프
- `trade_logs.db`에 저장된 실체결 가격과 주문 시점 호가를 비교하여 비용 승수 $k_{\text{cost}}$ 및 시장충격 지수 $\alpha$를 자동 업데이트.

---

## 11. Execution OMS 6대 주문 안전 게이트

1. **Gate 1 (거시 위기 게이트)**: `CrisisLevel.SEVERE` 판정 시 신규 매수 주문 100% 차단.
2. **Gate 2 (하드웨어 킬 스위치)**: `KILL_SWITCH` 파일 또는 환경변수 감지 시 모든 신규 주문 즉시 차단.
3. **Gate 3 (심볼 정규식 검증)**: 유효하지 않은 문자열(JSON dict 문자열, 공백 등) 차단.
4. **Gate 4 (가격 유효 경계)**: $1.0 \le P \le 100,000,000$ 범위 외 주문 거부.
5. **Gate 5 (단위 라운딩)**: 한국 시장 10주 단위 (소수점 주문 불가) 자동 라운딩.
6. **Gate 6 (포지션 집중도 상한)**: 단일 종목 최대 비중 10% (집중 허용 시 20%), 단일 섹터 최대 25% 하드 캡.

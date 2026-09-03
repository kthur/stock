# 🧠 37대 다변화 전략 및 퀀트 알고리즘 완전 명세서

> **Version**: 9.0 (Institutional Production Standard)  
> **Last Updated**: 2026-09-03 (KST)  
> **Source Modules**: `trading_system/src/core/*.py`, `src/ai/`, `src/risk/`, `src/execution/`, `src/broker/`  
> **Target Universe**: 한국(KOSPI, KOSDAQ) 및 미국(S&P 500, NASDAQ, RUSSELL 2000) 5대 시장

---

## 📑 목차

1. [37대 다변화 전략 종합 일람](#1-37대-다변화-전략-종합-일람)
2. [머신러닝 & 시계열 딥러닝 엔진 (전략 1~6)](#2-머신러닝--시계열-딥러닝-엔진-전략-16)
3. [차익거래 & 펀더멘탈 가치평가 엔진 (전략 7~10)](#3-차익거래--펀더멘탈-가치평가-엔진-전략-710)
4. [모멘텀 & 퀀트 팩터 엔진 (전략 11~18)](#4-모멘텀--퀀트-팩터-엔진-전략-1118)
5. [공급망, 감성 & 대체 데이터 엔진 (전략 19~23)](#5-공급망-감성--대체-데이터-엔진-전략-1923)
6. [회계 품질 & 특수 촉매 엔진 (전략 24~31)](#6-회계-품질--특수-촉매-엔진-전략-2431)
7. [거시 파급, 네트워크 & 구조적 수급 엔진 (전략 32~37)](#7-거시-파급-네트워크--구조적-수급-엔진-전략-3237)
8. [횡단면 점수 정규화 및 통계적 위생 (Cross-Sectional Hygiene)](#8-횡단면-점수-정규화-및-통계적-위생-cross-sectional-hygiene)
9. [2D 시장 레짐 & 동적 앙상블 가중치](#9-2d-시장-레짐--동적-앙상블-가중치)
10. [기관급 포트폴리오 최적화 & EVT-CVaR 꼬리위험 예산](#10-기관급-포트폴리오-최적화--evt-cvar-꼬리위험-예산)
11. [실전 미시구조 거래비용 및 슬리피지 피드백](#11-실전-미시구조-거래비용-및-슬리피지-피드백)
12. [Execution OMS 8대 주문 안전 게이트 & Almgren-Chriss](#12-execution-oms-8대-주문-안전-게이트--almgren-chriss)
13. [기관급 초저지연 실행 엔진 및 고도화 퀀트 알고리즘](#13-기관급-초저지연-실행-엔진-및-고도화-퀀트-알고리즘)

---

## 1. 37대 다변화 전략 종합 일람

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
| **24** | **Accruals Quality** | 회계 이상치 | $(\text{NetIncome} - \text{OCF}) / \text{TotalAssets}$ | 현금흐름표, 당기순이익 | `accruals_quality_predictions.txt` |
| **25** | **Short Squeeze** | 숏스퀴즈 | Short Interest + Days-to-Cover + 5D 모멘텀 | 공매도 잔고, 대차잔고 | `short_squeeze_predictions.txt` |
| **26** | **Value-Up Catalyst** | 주주환원 | PBR < 1.0 + 순현금/시총 + 총주주환원율 | 배당성향, 자사주 소각 | `valueup_catalyst_predictions.txt` |
| **27** | **Kaufman Trend Eff** | 추세 효율성 | 5D/10D/20D KER + Hurst Exponent ($H > 0.5$) | 일봉 방향성 변위 / 총이동거리 | `trend_efficiency_predictions.txt` |
| **28** | **Gamma Squeeze** | 감마 스퀴즈 | 옵션 미결제약정(OI) 및 콜옵션 델타 가속도 | 풋콜 OI, 델타/감마 익스포저 | `gamma_squeeze_predictions.txt` |
| **29** | **Insider Buying** | 내부자 매수 | 대주주/임원 장내 매수 공시 및 지분 변동률 | DART/SEC 내부자 지분 공시 | `insider_buying_predictions.txt` |
| **30** | **Earnings Tone Drift** | 어닝콜 톤 분석 | 실적발표 콘퍼런스콜 텍스트 긍/부정 어조 변화 | 어닝콜 스크립트 텍스트 | `earnings_tone_drift_predictions.txt` |
| **31** | **Darkpool & HFT Flow** | HFT 마이크로 | 다크풀 블록체결 & 틱 스프레드 마이크로구조 | 다크풀 거래량, 틱 스프레드 | `darkpool_predictions.txt` |
| **32** | **Cross-Asset Spillover**| 매크로 임펄스 | $\text{MacroImpulse}_s = \sum \beta_{s,k} \Delta M_k$ 미가격 파급 | 글로벌 거시 8대 지표 (SOX/FX 등) | `cross_asset_spillover_predictions.txt` |
| **33** | **Supply Chain GNN** | 관계형 그래프 | 2-Hop GNN 메시지 패싱 + 채찍효과 비선형 증폭 | 글로벌 밸류체인 지식그래프 | `supply_chain_gnn_predictions.txt` |
| **34** | **Range Expansion Breakout**| 변동성 돌파 | NR7/BB 압축 후 REF $\ge 1.5$ + RVOL $\ge 1.8$ + CLV $\ge 0.65$ | OHLCV, 14d ATR, 20d SMA Vol | `range_expansion_predictions.txt` |
| **35** | **Dual Correction** | 기술적 눌림목 | 피보나치(38.2%/50%/61.8%) + AVWAP + VDI 거래량 고갈 | 150d OHLCV, 앵커드 VWAP | `dual_correction_predictions.txt` |
| **36** | **Index Rebalance** | 구조적 패시브 | 40조 패시브 ETF 정기변경 15~30일 선반영 ($N_{\text{DTC}}$) | 시가총액 순위, 유동비율, ADV | `index_rebalance_predictions.txt` |
| **37** | **Overnight Gap Reversal**| 갭 평균회귀 | ATR 정규화 갭 $\frac{\text{Open}_t - \text{Close}_{t-1}}{\text{ATR}_{14}}$ 통계적 갭필 | 장시작 시가, 전일 종가, 14d ATR | `overnight_gap_predictions.txt` |

---

## 2. 머신러닝 & 시계열 딥러닝 엔진 (전략 1~6)

- **전략 1 (XGBoost 회귀)**: 8개 horizon(1d, 3d, 5d, 10d, 20d, 60d, 120d, 200d)별 예상수익률 회귀 추정.
- **전략 2 (Surge 분류기)**: 불균형 데이터셋 가중치(scale_pos_weight $\le 20.0$)를 적용하여 20% 이상 급등 확률 예측.
- **전략 3 (Lead-Lag 2-Tier)**: 리더 종목과 후행 종목 간의 1일 시차 상관성 분석. 미국 지수 ETF에 대해 +1일 Lag Shift 적용.
- **전략 4 (VCP 패턴 규칙)**: 마크 미너비니 변동성 수축 패턴(4차례 수축, 거래량 50% 이하 건조) 규칙 기반 탐지.
- **전략 5 (VCP ML 분류기)**: 수축률, 단조성, 거래량 수축 속도 벡터를 XGBClassifier에 학습시켜 급등 확률 산출.
- **전략 6 (Strict Causal LSTM)**: 시점별 롤링 정규화를 통해 미래 참조를 원천 차단한 시계열 딥러닝 예측.

---

## 3. 차익거래 & 펀더멘탈 가치평가 엔진 (전략 7~10)

- **전략 7 (Stat-Arb Cointegration)**: 주가 시계열에 로그 변환을 적용한 후 Engle-Granger 공적분 검정 통과($p < 0.05$) 페어만 선별하여 잔차 Z-score 기반 롱/숏 차익거래 신호 산출.
- **전략 8 (Sector Rotation)**: 1M/3M 업종 상대강도와 기관/외인 수급 가속도를 결합한 순환매 점수 산출.
- **전략 9 (RIM Valuation)**: 자기자본비용($k_e = R_f + \beta \times \text{ERP}$)과 잔여이익 모델을 활용한 정밀 본질가치 산출.
- **전략 10 (Event-Driven Catalyst)**: 실적 서프라이즈(>15%), DART 자사주 취득/소각, 3배 거래량 폭증 촉매 수치화.

---

## 4. 모멘텀 & 퀀트 팩터 엔진 (전략 11~18)

- **전략 11 (Momentum Quality, MQ)**: 12M-1M 장기 모멘텀에서 1M 단기 반전 노이즈를 제거하고 영업이익률 및 ROE 펀더멘탈 퀄리티 결합.
- **전략 12 (Options IV Skew)**: yfinance 풋/콜 IV Skew 및 Put/Call Ratio 역발상 공포 국면 매수 스코어링.
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

## 7. 거시 파급, 네트워크 & 구조적 수급 엔진 (전략 32~37)

### 7.1 전략 32: 크로스에셋 거시 파급 모멘텀 (Cross-Asset Spillover Momentum)
- **알고리즘 및 수식**:
  1. 8대 글로벌 거시 변수 $M \in \{\text{SOX}, \text{USDKRW}, \text{WTI}, \text{TNX}, \text{VIX}, \text{Gold}, \text{DXY}, \text{SP500}\}$에 대한 기간 가중 수익률 산출:
     $$\Delta M_k = 0.50 \cdot r_{k, 1d} + 0.35 \cdot r_{k, 3d} + 0.15 \cdot r_{k, 5d}$$
  2. 업종별 탄력도 계수 $\beta_{s,k}$를 적용하여 섹터 기대 임팩트 산출:
     $$\text{MacroImpulse}_s = \sum_{k=1}^{8} \beta_{s,k} \cdot \Delta M_k$$
  3. 개별 종목 누적 수익률과의 괴리율을 측정하여 미가격 시차 알파 선취:
     $$\text{RawScore}_i = \text{MacroImpulse}_{s(i)} + 0.6 \cdot (\text{MacroImpulse}_{s(i)} - R_{i})$$

### 7.2 전략 33: 공급망 GNN & 불위그 증폭 (Supply Chain GNN)
- **알고리즘 및 수식**:
  1. 2-Hop 관계형 그래프 메시지 패싱 집계:
     $$h_v^{(1)} = \frac{\sum_{u \in \mathcal{N}_1(v)} w_{uv} r_u}{\sum_{u \in \mathcal{N}_1(v)} w_{uv}}, \quad h_v^{(2)} = \frac{\sum_{k \in \mathcal{N}_2(v)} w_{kv}^{(2)} h_k^{(1)}}{\sum_{k \in \mathcal{N}_2(v)} w_{kv}^{(2)}}$$
  2. 전방 거래량 서지 기반 비선형 채찍효과 증폭 계수:
     $$\text{Amp}_v = 1.0 + 0.25 \cdot \max_{u \in \mathcal{N}(v)} \max(0, \text{VolSurge}_u - 1.0)$$
  3. 합성 GNN 모멘텀 점수:
     $$\text{GNNRaw}_v = (0.70 \cdot h_v^{(1)} + 0.30 \cdot h_v^{(2)}) \cdot \text{Amp}_v$$

### 7.3 전략 34: 레인지 확장 돌파 (Range Expansion Breakout)
- **알고리즘 및 수식**:
  1. 변동성 압축 전조 식별: 직전봉 NR7(7일 최저 변동폭) 및 볼린저 밴드폭 스퀴즈 $C_i$.
  2. 레인지 확장 계수: $\text{REF}_t = \frac{\text{High}_t - \text{Low}_t}{\text{ATR}_{14, t-1}} \ge 1.5$.
  3. 상대 거래량 서지: $\text{RVOL}_t = \frac{\text{Volume}_t}{\text{SMA}_{20}(\text{Volume})_{t-1}} \ge 1.8$.
  4. 종가 위치 품질: $\text{CLV}_t = \frac{\text{Close}_t - \text{Low}_t}{\text{High}_t - \text{Low}_t} \ge 0.65$.
  5. 복합 돌파 스코어:
     $$\text{RawBreakout}_i = 0.35 \cdot E_i + 0.30 \cdot V_i + 0.20 \cdot \text{CLV}_t + 0.15 \cdot C_i$$

### 7.4 전략 35: 듀얼 코렉션 (Dual Correction)
- **알고리즘 및 수식**:
  1. 가격 조정 지수($S_{\text{price}}$): 120일 스윙 하이/로우 피보나치 황금비율 지지선(38.2%/50.0%/61.8%) 및 앵커드 VWAP 근접도 지수 감쇠 계산:
     $$\text{Score}_{\text{fib}} = \exp\left(-0.5 \cdot \left(\min_k \frac{|P_t - \text{Level}_k|}{\text{ATR}_{14}}\right)^2\right)$$
  2. 기간 조정 지수($S_{\text{time}}$): 5일 거래량이 50일 평균 대비 급감하는 거래량 고갈 지수(VDI)와 15~45일 횡보 박스권 기간 검증.
  3. 합성 눌림목 반등 점수: $\text{RawDual}_i = 0.55 \cdot S_{\text{price}} + 0.45 \cdot S_{\text{time}}$.

### 7.5 전략 36: 인덱스 리밸런싱 패시브 수급 (Index Rebalance Structural Flow)
- **알고리즘 및 수식**:
  1. 4대 정기변경(3/6/9/12월 선물옵션, 2/5/8/11월 MSCI) D-45 ~ D-5 윈도우 감지.
  2. 패시브 ETF AUM(약 40조 원) 추종 필요 거래일수(Days-to-Cover):
     $$N_{\text{DTC}, i} = \frac{A_{\text{tracking}} \cdot \Delta w_i}{\text{ADV}_{20, i}}$$
  3. 시간 감쇠 및 편입 확률 가중치 결합:
     $$\text{RawRebal}_i = P_{\text{inclusion}, i} \cdot \log(1.0 + N_{\text{DTC}, i}) \cdot W(D_{\text{rem}})$$

### 7.6 전략 37: 오버나이트 갭 반전 (Overnight Gap Reversal)
- **알고리즘 및 수식**:
  1. 일일 변동성(ATR) 단위 오버나이트 갭 정규화:
     $$\text{GapRatio}_t = \frac{\text{Open}_t - \text{Close}_{t-1}}{\text{ATR}_{14, t-1}}$$
  2. 비대칭 갭 페이드 및 갭 채우기(Gap Fill) 확률 스코어링:
     - 과도한 하락 갭($\text{GapRatio} < -0.5$): 공포 매도 소진 후 평균회귀 반등 고득점 부여.
     - 과도한 상승 갭($\text{GapRatio} > +0.5$): 피로감에 따른 소진성 갭 페이드 감점 부여.

---

## 8. 횡단면 점수 정규화 및 통계적 위생 (Cross-Sectional Hygiene)

### 8.1 `CrossSectionalScoreNormalizer`
- 37개 전략의 상이한 출력 점수 분포로 인한 앙상블 왜곡을 방지하기 위해 시장별 횡단면 정규화 적용:
  $$S_{\text{norm}, i, k} = \frac{\operatorname{Rank}(s_{i, k}) - 0.5}{N_{\text{valid}}}$$
- 또는 Winsorized Gaussian CDF 변환:
  $$Z_{i, k} = \operatorname{clip}\left(\frac{s_{i, k} - \mu_k}{\sigma_k}, -3.0, 3.0\right), \quad S_{\text{norm}, i, k} = \Phi(Z_{i, k})$$

### 8.2 결측 전략 동적 제로 가중치 재정규화 (Dynamic Zero-Weighting)
- 특정 종목 $i$에 대해 결측된 전략 $k \notin \text{Active}_i$의 가중치를 0으로 처리하고, 활성 전략 집합에 대해 가중치를 재분배:
  $$\tilde{w}_{i, k} = \begin{cases} \frac{w_k}{\sum_{m \in \text{Active}_i} w_m} & \text{if } k \in \text{Active}_i \\ 0.0 & \text{otherwise} \end{cases}$$
- 인위적인 0.50 기본값 대체를 완전 배제하여 예측 왜곡을 제거.

### 8.3 PCA-ZCA 대칭 화이트닝 & Gram-Schmidt 직교화
- **PCA-ZCA 대칭 화이트닝**:
  $$C = V \Lambda V^T, \quad C^{-1/2} = V \Lambda^{-1/2} V^T, \quad X_{\text{decorr}} = \bar{X} \cdot C^{-1/2}$$
  - 순서 편향 없이 모든 팩터 간 상관관계를 $0.0$으로 정규 직교화.

---

## 9. 2D 시장 레짐 & 동적 앙상블 가중치

### 9.1 6대 2D 레짐 매트릭스 (가중치 합 = 1.0000)
20일 벤치마크 추세($\pm 1\%$)와 20일 실현 변동성(15% / 25%)을 결합:
1. `BULL_LOW_VOL`: 모멘텀, VCP ML, Surge, Range Expansion, Index Rebalance 주력
2. `BULL_HIGH_VOL`: Gamma Squeeze, Short Squeeze, Vol Target, Range Expansion 주력
3. `SIDEWAYS_LOW_VOL`: Stat-Arb, RIM Valuation, Value-Up, Dual Correction, Index Rebalance 주력
4. `SIDEWAYS_HIGH_VOL`: Short-Term Reversal, Overnight Gap Reversal, Dual Correction, Stat-Arb 주력
5. `BEAR_LOW_VOL`: Accruals Quality, RIM Valuation, Cross-Asset Spillover 방어 팩터 주력
6. `BEAR_HIGH_VOL`: Overnight Gap Reversal, LATR, Vol Target, 현금 비중 극대화 & OMS Gate 8 인버스 ETF 헤지

---

## 10. 기관급 포트폴리오 최적화 & EVT-CVaR 꼬리위험 예산

### 10.1 UnifiedPortfolioAllocator 4대 최적화 블렌딩
- **Black-Litterman (BL)**: 시장 균형 포트폴리오에 37대 알파 신호를 합성.
- **Hierarchical Equal Risk Contribution (HERC)**: 머신러닝 클러스터 트리 기반 다계층 위험 배분.
- **Risk Parity (RP)**: 개별 자산의 위험 기여도 균등 배분.
- **EVT-CVaR Tail Risk Optimizer**: Extreme Value Theory POT-GPD 기반 95% CVaR 최소화.

### 10.2 3/2승 비선형 시장충격 페널티 목적함수
Gatheral & Almgren-Chriss 프레임워크에 따른 자산 운용 규모별 시장충격 최적화:
$$\min_w \; -\mu^T w + \frac{\lambda}{2} w^T \Sigma w + \gamma_{\text{impact}} \sum_{i} \left(\frac{|w_i - w_{i, 0}| \cdot \text{PortfolioValue}}{\text{ADV}_i}\right)^{1.5}$$

### 10.3 Leland 동적 No-Trade 버퍼 밴드
- 불필요한 잦은 매매를 방지하기 위해 종목별 마찰비용과 변동성을 반영한 버퍼 밴드 $\delta_i \in [0.5\%, 5.0\%]$ 적용:
  $$w_{i, \text{current}} \in [w_{i, \text{target}} - \delta_i, \; w_{i, \text{target}} + \delta_i] \implies \text{HOLD}$$
- 단, 신규 진입($w_{\text{curr}}=0$) 및 전량 청산($w_{\text{targ}}=0$) 시에는 버퍼 억제 없이 즉시 바이패스 실행.

---

## 11. 실전 미시구조 거래비용 및 슬리피지 피드백

### 11.1 시장별 거래비용 모델
- **KOSPI**: 증권거래세 0.15% + 브로커 수수료 0.03% + 동적 스프레드 $S_i$ + Kyle 시장 충격
- **KOSDAQ**: 증권거래세 0.15% (2026 세제 개편 동기화 완료, 3 bps 알파 마찰 제거) + 브로커 수수료 0.03% + 동적 스프레드 $S_i$ + Kyle 시장 충격
- **S&P 500 / NASDAQ**: SEC Fee 0.003% + 브로커 수수료 0.005% + 동적 스프레드 + 시장 충격

### 11.2 슬리피지 피드백 루프
- `trade_logs.db`에 저장된 실체결 가격과 주문 시점 호가를 비교하여 비용 승수 $k_{\text{cost}}$ 및 시장충격 지수 $\alpha$를 자동 업데이트.

---

## 12. Execution OMS 8대 주문 안전 게이트 & Almgren-Chriss

### 12.1 8대 안전 게이트 체계
1. **Gate 1 (거시 위기 게이트)**: `CrisisLevel.SEVERE` 판정 시 신규 매수 주문 100% 차단.
2. **Gate 2 (하드웨어 킬 스위치)**: `KILL_SWITCH` 파일 또는 환경변수 감지 시 모든 신규 주문 즉시 차단.
3. **Gate 3 (심볼 정규식 검증)**: 유효하지 않은 문자열(JSON dict 문자열, 공백 등) 차단.
4. **Gate 4 (가격 유효 경계 & 틱 그리드)**: $1.0 \le P \le 100,000,000$ 범위 외 주문 거부 및 KRX/US 호가단위 자동 정렬.
5. **Gate 5 (단위 라운딩)**: 한국 시장 10주 단위 (소수점 주문 불가) 자동 라운딩, 미국 1주 단위.
6. **Gate 6 (포지션 집중도 상한)**: 단일 종목 최대 비중 10% (집중 허용 시 20%), 단일 섹터 최대 35% 하드 캡.
7. **Gate 7 (고급 미시구조 실행 서브게이트)**:
   - **7.1 (KRX Long-Only Synthetic Short / Cash Overlay)**: 공매도 불가 계좌 합성 숏/현금 비중 자동 조정.
   - **7.2 (KRX Upper/Lower Limit Lock)**: $\pm 30\%$ 상하한가 락 및 호가 유동성 증발 감지.
   - **7.3 (STT / Friction Net Alpha Hurdle)**: 세금 및 마찰비용 차감 후 순알파($\text{Net Alpha} > 0$) 검증.
   - **7.4 (Dynamic Adverse Opening Gap Filter)**: $-3\sigma$ 극단적 시초가 충격 회피.
   - **7.5 (ADV Capacity Cap)**: 일평균 거래대금의 10% 초과 주문 차단.
   - **7.6 (VPIN Toxicity Gate)**: 주문 흐름 독성 $VPIN > 0.70$ 감지 시 PASSIVE_LIMIT/FAST_VWAP 전환.
   - **7.7 (Opening Gap Overheat & Dip-Buying)**: 과열 갭업 시 DIP_LIMIT 장중 눌림목 주문 전환.
8. **Gate 8 (합성 인버스 헤지 오버레이)**: 약세장(Bear) 또는 위기 국면 판정 시 시장 베타에 비례하여 인버스 ETF(KODEX 인버스, KODEX 200선물인버스2X, PSQ, SQQQ)를 자동 매수하여 포트폴리오를 방어.

### 12.2 Almgren-Chriss 최적 집행 스케줄러
- 거래량과 변동성을 고려하여 시장 충격과 타이밍 위험을 최소화하는 비선형 트랜치 분할 스케줄링 적용.

---

## 13. 기관급 초저지연 실행 엔진 및 고도화 퀀트 알고리즘

### 13.1 Fast LOB 제로카피 링버퍼 & Hawkes 프로세스 (`fast_lob_engine.py`)
- **제로카피 고정 크기 링버퍼**: GC 오버헤드를 배제한 메모리 순환 구조로 마이크로초 단위 Level 3 호가 접수 및 틱 매칭 수행.
- **Hawkes 자기여기(Self-Exciting) 점 과정 오더 도착 강도 모델**:
  $$\lambda(t) = \mu + \sum_{t_i < t} \alpha e^{-\beta (t - t_i)}$$
  - 연속 주문 폭주 및 유동성 증발 시점을 포착하여 슬리피지 방어.

### 13.2 강화학습 기반 동적 주문 슬라이싱 에이전트 (`rl_execution_agent.py`)
- **상태 공간 $S$**: 남은 수량 비율, 남은 실행 시간 비율, 스프레드, 단기 체결 강도, 오더북 불균형(OBI).
- **행동 공간 $A$**: 주문 슬라이스 비율 (트랜치 크기) 및 가격 지정 오프셋 (Midpoint Peg, Passive, Aggressive).
- **보상 함수 $R_t$**:
  $$R_t = -(\text{ExecutedPrice} - \text{ArrivalPrice}) \cdot q_t - \gamma \cdot \operatorname{Var}(\text{ExecutionRisk})$$
  - 시장충격과 기회비용을 실시간 학습하여 동적으로 최적 집행.

### 13.3 글로벌 스마트 오더 라우터 (SOR) & FIX 4.4 DMA (`smart_order_router.py`, `fix_protocol_engine.py`)
- **다중 거래소 자동 라우팅**: 국내 KOSPI/KOSDAQ(`.KS`, `.KQ` 접미사 자동 파싱) 및 미국(US), 일본(JP), 홍콩(HK), 유럽(EU), 캐나다(CA) 거래소 자동 분기.
- **기관 직결 FIX 4.4 클라이언트**: 표준 태그(`35=D`, `54=Side`, `38=OrderQty`, `44=Price` 등) 기반 DMA 주문 전송 및 하트비트 세션 관리.
- **Interactive Brokers (IBKR) 연동**: TWS/Gateway 소켓 통신을 통한 전 세계 주식 복합 주문 지원.

### 13.4 30일 롤링 RankIC 동적 알파 가중치 & 패닉 역발상
- **30일 롤링 RankIC**: 각 전략 $k$의 실제 실현수익률 순위 상관계수 $\operatorname{RankIC}_k(30\text{d})$에 비례하여 앙상블 가중치 동적 스케일링:
  $$w_k^{\text{dynamic}} \propto w_k^{\text{base}} \times \max\left(0.2, \; 1.0 + \gamma_{\text{IC}} \cdot \operatorname{RankIC}_k\right)$$
- **패닉 역발상 알파 (Contrarian Reversal)**: VIX 폭등 및 급락장 발생 시 단기 과매도 평균회귀 팩터의 가중치를 일시 증폭하여 반등 알파 선취.

### 13.5 EWMA 공분산 행렬 & 연속 비례 Leland 버퍼 밴드
- **EWMA 공분산 행렬 (RiskMetrics 표준)**:
  $$\Sigma_t = \lambda \Sigma_{t-1} + (1 - \lambda) r_t r_t^T, \quad \lambda = 0.94$$
- **연속 비례 Leland 버퍼 밴드**:
  $$\delta_i = \operatorname{clip}\left(c \cdot \frac{\text{Cost}_i}{\sigma_i}, \; 0.005, \; 0.05\right)$$
  - 종목별 마찰비용과 변동성에 정확히 비례하는 동적 불감대를 형성하여 턴오버 및 거래비용 최소화.


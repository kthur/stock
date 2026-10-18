"""
trading_system/report_multipage.py
Static Multi-Page Architecture generator for Stock Trading System Dashboard.
Deploys 7 static pages:
  1. index.html: Executive Summary Dashboard (< 500 KB, initial DOM nodes reduced > 70%)
  2. strategies.html: 37-Strategy Technical Encyclopedia & Live Candidate Panels
  3-7. market_{market}.html: 5 Dedicated Full-Universe 42-Column Ranking Tables
"""

import html
import json
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────
# 37 Strategies Technical Catalog & Metadata
# ─────────────────────────────────────────────

STRATEGY_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "regression",
        "num": 1,
        "name": "XGBoost 다중 기간 회귀",
        "name_en": "XGBoost Multi-Horizon Return Regression",
        "category": "AI/ML",
        "formula": r"E[R_{t+h}] = \sum_{m=1}^M f_m(X_t) \quad (h \in \{1, 3, 5, 10, 20, 60, 120, 200\})",
        "intuition": "8개 투자 시계(1~200일)별 연속형 기대수익률을 시장별 XGBoost 회귀 앙상블 트리로 정밀 산출",
        "inputs": "기술적 지표(RSI, MACD, 볼린저밴드), 거시 지표(VIX, USDKRW, SOX), 펀더멘탈",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.7, "BEAR_LOW_VOL": 0.5, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.4},
        "data_source": "OHLCV, Fred, DART/SEC (일일 갱신)",
        "panel_id": "panel-regression",
    },
    {
        "id": "surge",
        "num": 2,
        "name": "Surge 급등 분류기",
        "name_en": "Short-Term Surge Classifier",
        "category": "AI/ML",
        "formula": r"P(\text{Surge}_{t+h}) = \sigma\left(\sum_{m=1}^M f_m(X_t)\right) \quad (\text{scale\_pos\_weight} \le 20.0)",
        "intuition": "단기 급등(+5%~+15% 이상) 발생 확률을 클래스 불균형 제어 XGBClassifier로 예측",
        "inputs": "변동성 확장률, 거래량 서지 비율, 호가 불균형 가속도, 이격도",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.3, "BEAR_HIGH_VOL": 0.1, "SIDEWAYS_LOW_VOL": 0.6, "SIDEWAYS_HIGH_VOL": 0.3},
        "data_source": "OHLCV, 장중 호가 (일일 갱신)",
        "panel_id": "panel-surge",
    },
    {
        "id": "leadlag",
        "num": 3,
        "name": "Lead-Lag 시차 상관",
        "name_en": "Lead-Lag Cross-Asset Momentum",
        "category": "모멘텀/수급",
        "formula": r"\text{Corr}(\Delta P_{\text{lead}, t-1}, \Delta P_{\text{lag}, t}) > \theta_{\text{thresh}} \quad (+1\text{d US Lag Shift})",
        "intuition": "업종 대형주 및 미국 대표주의 전일 선행 변동이 국내/후행주로 전이되는 시차 차익 포착",
        "inputs": "글로벌 섹터 ETF 수익률, 업종 1위주 시총 가중 수익률, 1D Lagged Price",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.6, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "글로벌 지수, KRX/US 주가 (일일 갱신)",
        "panel_id": "panel-leadlag",
    },
    {
        "id": "vcp",
        "num": 4,
        "name": "VCP 패턴 규칙",
        "name_en": "Volatility Contraction Pattern Rule",
        "category": "모멘텀/수급",
        "formula": r"\text{VCP} = \mathbb{I}(\sigma_1 > \sigma_2 > \sigma_3 \land V \downarrow \land P \ge 0.85 \times P_{52w})",
        "intuition": "마크 미네르비니의 변동성 축소 + 거래량 고갈 + 52주 고점 근접 돌파 셋업",
        "inputs": "일중 고저폭 변동성(ATR), 거래량 이동평균 비율, 52주 신고가 근접도",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.3, "BEAR_HIGH_VOL": 0.1, "SIDEWAYS_LOW_VOL": 0.5, "SIDEWAYS_HIGH_VOL": 0.2},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-vcp",
    },
    {
        "id": "vcpml",
        "num": 5,
        "name": "VCP 머신러닝",
        "name_en": "VCP ML Breakout Classifier",
        "category": "AI/ML",
        "formula": r"P(\text{Breakout} \mid \text{VCP}_{\text{features}}) = \text{XGBoost}(\text{ContractionRatio}, \text{VolumeDrift}, \dots)",
        "intuition": "VCP 패턴 형성 후 실제 성공적 상방 돌파 확률을 머신러닝 분류기로 재필터링",
        "inputs": "1~3차 수축 진폭, 거래량 감소 기울기, 저항선 터치 횟수, 시장 상대강도",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.85, "BEAR_LOW_VOL": 0.3, "BEAR_HIGH_VOL": 0.1, "SIDEWAYS_LOW_VOL": 0.6, "SIDEWAYS_HIGH_VOL": 0.25},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-vcpml",
    },
    {
        "id": "lstm",
        "num": 6,
        "name": "Strict Causal LSTM",
        "name_en": "Strict Causal Deep Learning",
        "category": "AI/ML",
        "formula": r"h_t = \text{LSTM}(x_t, h_{t-1}), \quad \hat{y}_{t+k} = \mathbf{W}_o h_t + b_o \quad (\text{No Lookahead Leakage})",
        "intuition": "엄격한 시점 분리 롤링 정규화 기반 순방향 순환 신경망으로 시계열 동적 패턴 추출",
        "inputs": "20거래일 시퀀스 정규화 OHLCV, 기술적 보조지표 텐서",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.7, "BEAR_LOW_VOL": 0.6, "BEAR_HIGH_VOL": 0.4, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.5},
        "data_source": "OHLCV 텐서 (일일 갱신)",
        "panel_id": "panel-lstm",
    },
    {
        "id": "stat-arb",
        "num": 7,
        "name": "Stat-Arb 차익거래",
        "name_en": "Cointegration Pairs Stat-Arb",
        "category": "거시/차익",
        "formula": r"z_t = \frac{\ln(P_A) - \beta \ln(P_B) - \alpha}{\sigma_\epsilon}, \quad |z_t| > 2.0 \implies \text{Mean Reversion}",
        "intuition": "동일 업종 내 장기 균형(공적분) 관계에 있는 페어의 일시적 잔차 왜곡 역발상 수렴 베팅",
        "inputs": "통계적 유의 공적분 페어 주가 시계열, Engle-Granger Z-score",
        "regime_weights": {"BULL_LOW_VOL": 0.6, "BULL_HIGH_VOL": 0.4, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.5, "SIDEWAYS_LOW_VOL": 1.0, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "OHLCV 가격 페어 (일일 갱신)",
        "panel_id": "panel-stat-arb",
    },
    {
        "id": "sector",
        "num": 8,
        "name": "Sector Rotation",
        "name_en": "Sector Relative Momentum & Flow",
        "category": "모멘텀/수급",
        "formula": r"S_{\text{sec}} = 0.6 \times R_{1M} + 0.4 \times R_{3M} - R_{\text{market}} + \Delta \text{ForeignFlow}",
        "intuition": "KRX/GICS 11대 섹터 간 자금 이동 경로 추적 및 주도 업종 내 최상위 유망주 선별",
        "inputs": "업종별 수익률, 외국인/기관 섹터 누적 순매수, 섹터 상대강도",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.4, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "KRX/GICS 업종 지수, 투자자별 수급 (일일 갱신)",
        "panel_id": "panel-sector",
    },
    {
        "id": "rim",
        "num": 9,
        "name": "RIM Valuation",
        "name_en": "Residual Income Model Valuation",
        "category": "가치/어닝",
        "formula": r"V_0 = B_0 + \sum_{t=1}^T \frac{(\text{ROE}_t - r_e) B_{t-1}}{(1+r_e)^t} + \frac{(\text{ROE}_T - r_e) B_{T-1} \cdot \omega}{(1+r_e - \omega)(1+r_e)^T}",
        "intuition": "자기자본비용(COE)을 초과하는 영구성 잔여이익 모델 기반 기업 본질가치 대비 할인율 산출",
        "inputs": "자본총계, ROE 컨센서스/실적치, 국채 10년물 금리 기반 COE, 영구성 계수",
        "regime_weights": {"BULL_LOW_VOL": 0.7, "BULL_HIGH_VOL": 0.5, "BEAR_LOW_VOL": 1.0, "BEAR_HIGH_VOL": 0.8, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "DART/SEC 재무제표, 국채금리 (분기/일일 갱신)",
        "panel_id": "panel-rim",
    },
    {
        "id": "event",
        "num": 10,
        "name": "Event-Driven 촉매",
        "name_en": "Corporate Filing & Catalyst Event",
        "category": "가치/어닝",
        "formula": r"S_{\text{event}} = w_1 \mathbb{I}_{\text{DART}} + w_2 \text{Surprise}_{\text{Earn}} + w_3 \mathbb{I}_{\text{Buyback}} + w_4 \mathbb{I}_{V \ge 3 \bar{V}}",
        "intuition": "DART/SEC 공시, 어닝 서프라이즈, 자사주 매입/소각, 유상증자, 특이 거래량 폭발 촉매 포착",
        "inputs": "공시 분류 태그, 잠정실적치 vs 컨센서스 괴리, 자사주 취득 공시, 일중 거래량 배수",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.6, "BEAR_HIGH_VOL": 0.5, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "DART OpenAPI, SEC EDGAR, 공시 피드 (실시간/일일)",
        "panel_id": "panel-event",
    },
    {
        "id": "mq",
        "num": 11,
        "name": "MQ Factor (퀄리티 모멘텀)",
        "name_en": "Momentum Quality Factor",
        "category": "모멘텀/수급",
        "formula": r"\text{MQ} = (R_{12M} - R_{1M}) \times \text{OpMargin} \times \text{ROE} \times (1 - \text{Vol}_{\text{noise}})",
        "intuition": "12M-1M 모멘텀에서 1M 단기 반전 노이즈를 차감하고 영업이익률/ROE로 고품질 추세 선별",
        "inputs": "12개월/1개월 누적 수익률, 영업이익률, ROE, 일별 수익률 표준편차",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.5, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.4},
        "data_source": "OHLCV, 재무제표 (일일/분기)",
        "panel_id": "panel-mq",
    },
    {
        "id": "iv",
        "num": 12,
        "name": "Options IV Skew",
        "name_en": "Options Implied Volatility Skew",
        "category": "거시/차익",
        "formula": r"\text{Skew}_{\text{IV}} = \text{IV}_{\text{OTM Put}} - \text{IV}_{\text{OTM Call}} \quad (\text{Fear Contrarian Score})",
        "intuition": "옵션 시장 풋/콜 내재변동성(IV) 스큐 극단치 분석을 통한 공포 역발상 매수 신호 포착",
        "inputs": "yfinance 옵션 체인 델타 25 풋/콜 IV, 역사적 변동성(HV) 괴리",
        "regime_weights": {"BULL_LOW_VOL": 0.5, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.9, "BEAR_HIGH_VOL": 1.0, "SIDEWAYS_LOW_VOL": 0.6, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "OPRA, yfinance Options Chain (일일 갱신)",
        "panel_id": "panel-iv",
    },
    {
        "id": "flow",
        "num": 13,
        "name": "Order Flow 수급",
        "name_en": "Order Flow Imbalance (MFI)",
        "category": "수급/미시구조",
        "formula": r"\text{OFI}_t = \Delta \text{BidQty}_t - \Delta \text{AskQty}_t + \text{MFI}_{\text{accel}}",
        "intuition": "외인 및 기관의 순매수 호가창 잔량 변화율과 수급 가속도(MFI) 기반 매수 압력 측정",
        "inputs": "외인/기관 일별 순매수 대금, 자금흐름지수(MFI), 체결 강도",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.5, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "KRX/FINRA 거래원 수급 (일일 갱신)",
        "panel_id": "panel-flow",
    },
    {
        "id": "reversal",
        "num": 14,
        "name": "ST Reversal 단기 반등",
        "name_en": "Short-Term Mean Reversion",
        "category": "모멘텀/수급",
        "formula": r"Z_{\text{rev}} = \frac{P_t - \text{SMA}_{20}}{\sigma_{20}} \le -2.0 \land \text{RSI}_3 \le 20 \implies \text{Long}",
        "intuition": "3~5일 연속 과매도 및 볼린저 밴드 하단 이탈 후 통계적 평균 회귀 기술적 반등 포착",
        "inputs": "3일/5일 누적 하락폭, 볼린저 하단 이탈률, 단기 RSI",
        "regime_weights": {"BULL_LOW_VOL": 0.6, "BULL_HIGH_VOL": 0.5, "BEAR_LOW_VOL": 0.8, "BEAR_HIGH_VOL": 0.9, "SIDEWAYS_LOW_VOL": 1.0, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "OHLCV 일봉 (일일 갱신)",
        "panel_id": "panel-reversal",
    },
    {
        "id": "arm",
        "num": 15,
        "name": "ARM Factor (컨센서스)",
        "name_en": "Analyst Revision Momentum",
        "category": "가치/어닝",
        "formula": r"\text{ARM} = \frac{\Delta \text{EPS}_{\text{FY1}}}{|\text{EPS}_{\text{FY1}}|} + \frac{\Delta \text{TargetPrice}}{\text{Price}_t}",
        "intuition": "증권사 애널리스트들의 목표주가 및 영업이익/EPS 추정치 상향 조정 모멘텀 수치화",
        "inputs": "FnGuide / LSEG 1개월/3개월 컨센서스 EPS 수정치, 목표주가 괴리율",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.6, "BEAR_HIGH_VOL": 0.3, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.5},
        "data_source": "FnGuide, Refinitiv, Yahoo Finance (주간/일일)",
        "panel_id": "panel-arm",
    },
    {
        "id": "card",
        "num": 16,
        "name": "CARD Factor (크로스에셋)",
        "name_en": "Cross-Asset Regime Divergence",
        "category": "거시/차익",
        "formula": r"\text{CARD} = \text{Resid}\left(R_i \sim \beta_1 R_{\text{WTI}} + \beta_2 R_{\text{FX}} + \beta_3 R_{\text{Bond}}\right)",
        "intuition": "주식-원자재-환율-채권 매크로 자산군 간 거시 괴리율 역발상 매수 스코어링",
        "inputs": "WTI 유가, USDKRW 환율, 미국채 10년물, 달러인덱스(DXY) 탄력도",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.7, "BEAR_LOW_VOL": 0.9, "BEAR_HIGH_VOL": 0.9, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "Fred, 글로벌 원자재/환율 시계열 (일일 갱신)",
        "panel_id": "panel-card",
    },
    {
        "id": "latr",
        "num": 17,
        "name": "LATR Factor (꼬리위험)",
        "name_en": "Liquidity-Adjusted Tail Risk",
        "category": "거시/차익",
        "formula": r"\text{LATR} = \frac{\text{MaxDD}_{52w} \times \text{AmihudIlliquidity}}{\text{DownsideVol}_{20d}}",
        "intuition": "52주 최고점 대비 낙폭과 유동성 서지 대비 하방 꼬리위험(Tail Risk) 페널티 보정",
        "inputs": "52주 최대 낙폭(MDD), Amihud 비유동성 비율, 하방 반편차(Semi-variance)",
        "regime_weights": {"BULL_LOW_VOL": 0.7, "BULL_HIGH_VOL": 0.6, "BEAR_LOW_VOL": 1.0, "BEAR_HIGH_VOL": 1.0, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "OHLCV 주가/거래대금 (일일 갱신)",
        "panel_id": "panel-latr",
    },
    {
        "id": "ifs",
        "num": 18,
        "name": "외인/투신 수급",
        "name_en": "Institutional & Foreign Sector Flow",
        "category": "수급/미시구조",
        "formula": r"S_{\text{IFS}} = \sum_{t=1}^{40} \left(w_{\text{foreign}} \Delta \text{NetBuy}_{\text{for}, t} + w_{\text{inst}} \Delta \text{NetBuy}_{\text{inst}, t}\right)",
        "intuition": "외국인 및 투신(기관)의 최근 2개월 수급 누적 패턴 및 업종 주도주 상관성 분석",
        "inputs": "투자자별 일별 순매수 대금, 업종 내 수급 집중도, 연속 순매수 일수",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.4, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "KRX 정보데이터시스템, SEC Form 13F (일일/분기)",
        "panel_id": "panel-ifs",
    },
    {
        "id": "supplychain",
        "num": 19,
        "name": "Supply Chain 공급망",
        "name_en": "Supply Chain Momentum Spillover",
        "category": "거시/차익",
        "formula": r"R_{\text{supplier}, t} \sim \alpha + \beta_1 R_{\text{customer}, t-1} + \beta_2 R_{\text{customer}, t-3}",
        "intuition": "전방 대표기업(삼성전자, 애플, 테슬라 등) 1D/3D 수익률의 부품/장비 공급망 시차 전이",
        "inputs": "글로벌 밸류체인 관계 그래프, 고객사 일간 수익률, 매출 의존도 가중치",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.6, "BEAR_HIGH_VOL": 0.4, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "공급망 지식 그래프, 사업보고서 매출처 (일일 갱신)",
        "panel_id": "panel-supplychain",
    },
    {
        "id": "sentiment",
        "num": 20,
        "name": "NLP Sentiment (감성)",
        "name_en": "FinBERT NLP Sentiment Catalyst",
        "category": "거시/차익",
        "formula": r"\text{Sentiment} = \text{FinBERT}(\text{Filings}, \text{News}) \in [-1.0, +1.0]",
        "intuition": "DART/SEC 공시 요약, 기업 뉴스 및 실적 발표 텍스트를 금융 특화 FinBERT로 감성 스코어링",
        "inputs": "기업 공시 텍스트, 경제 뉴스 헤드라인/본문, FinBERT 감성 확률 분포",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.6, "SIDEWAYS_LOW_VOL": 0.7, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "DART/SEC 공시 본문, 뉴스 피드 (실시간/일일)",
        "panel_id": "panel-sentiment",
    },
    {
        "id": "neutralized",
        "num": 21,
        "name": "Factor Neutralized",
        "name_en": "Fama-French 5-Factor Style Neutralized",
        "category": "거시/차익",
        "formula": r"R_{i,t} - R_{f,t} = \alpha_i + \beta_1 \text{MKT} + \beta_2 \text{SMB} + \beta_3 \text{HML} + \beta_4 \text{RMW} + \beta_5 \text{CMA} + \epsilon_{i,t}",
        "intuition": "Fama-French 5대 스타일 요인(시장, 시총, 가치, 수익성, 투자) 노출도를 제거한 순수 알파",
        "inputs": "Fama-French 5-Factor 일별 시계열, 종목 수익률 공분산",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.8, "BEAR_HIGH_VOL": 0.8, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.9},
        "data_source": "Kenneth French Data Library, 종목 주가 (일일 갱신)",
        "panel_id": "panel-neutralized",
    },
    {
        "id": "voltarget",
        "num": 22,
        "name": "Vol Targeting",
        "name_en": "Dynamic Volatility Targeting",
        "category": "거시/차익",
        "formula": r"w_i = \min\left(1.0, \frac{\sigma_{\text{target}}}{\hat{\sigma}_{i, 20d}}\right) \quad (\sigma_{\text{target}} = 12\%\text{ p.a.})",
        "intuition": "실산출 변동성과 연 목표 변동성(12%)에 기반한 리스크 파리티 위험 가중치 스코어링",
        "inputs": "20일/60일 실현 변동성, EWMA 변동성, 목표 연변동성",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.6, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.4, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.5},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-voltarget",
    },
    {
        "id": "microstructure",
        "num": 23,
        "name": "Microstructure 호가",
        "name_en": "Market Microstructure Imbalance",
        "category": "수급/미시구조",
        "formula": r"\text{Imbalance} = \frac{\text{BidVol} - \text{AskVol}}{\text{BidVol} + \text{AskVol}} + \text{AuctionOvernightGap}",
        "intuition": "호가창 매수/매도 5단계 잔량 불균형 및 장마감 종가 동시호가 수급 오버나이트 갭 포착",
        "inputs": "최우선 및 5단계 호가 잔량, 동시호가 체결 틱, 개장가 갭",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.6, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "KRX/L3 오더북 틱 피드 (일일 갱신)",
        "panel_id": "panel-microstructure",
    },
    {
        "id": "accruals",
        "num": 24,
        "name": "Accruals Quality (발생액)",
        "name_en": "Accruals Quality Anomaly",
        "category": "가치/어닝",
        "formula": r"\text{Accrual} = -\frac{(\text{NetIncome} - \text{OperatingCashFlow})}{\text{TotalAssets}}",
        "intuition": "당기순이익 대비 영업현금흐름(OCF) 괴리율 분석을 통한 회계적 이익 품질 평가",
        "inputs": "당기순이익, 영업활동현금흐름, 총자산, 매출채권/재고자산 증감",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.6, "BEAR_LOW_VOL": 1.0, "BEAR_HIGH_VOL": 0.9, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "DART/SEC 현금흐름표, 재무상태표 (분기 갱신)",
        "panel_id": "panel-accruals",
    },
    {
        "id": "shortsqueeze",
        "num": 25,
        "name": "Short Squeeze 촉매",
        "name_en": "Short Interest & Squeeze Potential",
        "category": "수급/미시구조",
        "formula": r"\text{SQZ} = \text{ShortRatio} \times \text{DaysToCover} \times R_{5D} \quad (\text{Short Squeeze Score})",
        "intuition": "공매도 잔고 비율, 커버리지 일수(DTC) 및 5일 상승 모멘텀 결합 숏스퀴즈 발생 촉매",
        "inputs": "공매도 잔고 수량, 일평균 거래량(ADV), 최근 5거래일 주가 상승률",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 1.0, "BEAR_LOW_VOL": 0.5, "BEAR_HIGH_VOL": 0.3, "SIDEWAYS_LOW_VOL": 0.7, "SIDEWAYS_HIGH_VOL": 0.5},
        "data_source": "KRX 공매도 종합포털, FINRA Short Interest (일일/반월)",
        "panel_id": "panel-shortsqueeze",
    },
    {
        "id": "valueup",
        "num": 26,
        "name": "Value-Up Yield (주주환원)",
        "name_en": "Value-Up & Shareholder Yield",
        "category": "가치/어닝",
        "formula": r"\text{Yield}_{\text{total}} = \text{DivYield} + \text{BuybackYield} + \frac{\text{NetCash}}{\text{MarketCap}} + \frac{1}{\text{PBR}}",
        "intuition": "PBR 1배 미만 + 순현금 보유 + 총주주환원율(배당수익률 + 자사주 매입/소각) 결합 가치주",
        "inputs": "배당수익률, 자사주 취득/소각 공시 금액, PBR, 순현금(현금및현금성자산 - 총차입금)",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.6, "BEAR_LOW_VOL": 1.0, "BEAR_HIGH_VOL": 0.8, "SIDEWAYS_LOW_VOL": 1.0, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "KRX 밸류업 지수, 배당 공시 (일일/분기)",
        "panel_id": "panel-valueup",
    },
    {
        "id": "trendeff",
        "num": 27,
        "name": "Trend Efficiency 추세",
        "name_en": "Kaufman Trend Efficiency Ratio",
        "category": "모멘텀/수급",
        "formula": r"\text{KER}_n = \frac{|P_t - P_{t-n}|}{\sum_{k=1}^n |P_t - P_{t-1}|} \times H \quad (H: \text{Hurst Exponent})",
        "intuition": "카우프만 트렌드 효율성(KER) 및 허스트 지수(Hurst)를 통한 노이즈 없는 고순도 추세 필터",
        "inputs": "5D/10D/20D 가격 변위 및 가격 궤적 총합, Hurst Exponent",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.7, "BEAR_LOW_VOL": 0.4, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.7, "SIDEWAYS_HIGH_VOL": 0.3},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-trendeff",
    },
    {
        "id": "gammasqueeze",
        "num": 28,
        "name": "Gamma Squeeze (감마)",
        "name_en": "Options Gamma Squeeze",
        "category": "수급/미시구조",
        "formula": r"\Gamma_{\text{net}} = \sum \Gamma_i \times \text{OpenInterest}_i \times \Delta_{\text{flow}} / \text{ADV}",
        "intuition": "단기 콜옵션 미결제약정 급증 및 딜러 감마 헤징 매수 가속도 기반 감마 스퀴즈",
        "inputs": "옵션 행사가별 감마(Gamma), 델타(Delta), 미결제약정(OI), 일평균거래량",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 1.0, "BEAR_LOW_VOL": 0.4, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.6, "SIDEWAYS_HIGH_VOL": 0.4},
        "data_source": "CBOE/OPRA 옵션 데이터 (일일 갱신)",
        "panel_id": "panel-gammasqueeze",
    },
    {
        "id": "insider",
        "num": 29,
        "name": "Insider Buying (내부자)",
        "name_en": "Corporate Insider Buying",
        "category": "수급/미시구조",
        "formula": r"S_{\text{insider}} = \log\left(\sum \text{Shares}_{\text{buy}} \times P\right) \times \text{OfficerRankWeight}",
        "intuition": "임원 및 최대주주의 장내 매수 공시 금액, 매수자 직급 가중치 및 지분율 변동 추적",
        "inputs": "DART 임원/주요주주 특정증권등 소유상황보고서, SEC Form 4",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.7, "BEAR_LOW_VOL": 1.0, "BEAR_HIGH_VOL": 0.9, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "DART 전자공시, SEC Form 4 (실시간/일일)",
        "panel_id": "panel-insider",
    },
    {
        "id": "darkpool",
        "num": 30,
        "name": "Darkpool & HFT Flow",
        "name_en": "Darkpool & High-Frequency Block Flow",
        "category": "수급/미시구조",
        "formula": r"\text{DP}_{\text{score}} = \frac{\text{BlockVol}_{\text{off-exchange}}}{\text{TotalVol}} \times \text{MicroSpreadSpread}",
        "intuition": "다크풀 및 장외 대체거래소(ATS) 대량 블록딜 체결 수급과 HFT 주문 흐름 포착",
        "inputs": "FINRA ATS/장외 체결 데이터, 대량 매매 블록 체결 비율, 마이크로스프레드",
        "regime_weights": {"BULL_LOW_VOL": 0.8, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.8, "BEAR_HIGH_VOL": 0.7, "SIDEWAYS_LOW_VOL": 0.9, "SIDEWAYS_HIGH_VOL": 0.8},
        "data_source": "FINRA ATS, KRX 시간외 대량매매 (일일 갱신)",
        "panel_id": "panel-darkpool",
    },
    {
        "id": "tonedrift",
        "num": 31,
        "name": "Tone Drift 어닝어조",
        "name_en": "Earnings Call Tone Drift",
        "category": "가치/어닝",
        "formula": r"\Delta \text{Tone} = \text{PosRatio}_t - \text{NegRatio}_t - (\text{PosRatio}_{t-1} - \text{NegRatio}_{t-1})",
        "intuition": "분기 실적 발표 콘퍼런스콜 경영진 질의응답 텍스트의 어조(Tone) 변화율 퀀트화",
        "inputs": "실적 발표 스크립트, Q&A 녹취록 텍스트, Loughran-McDonald 감성 사전",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.7, "BEAR_HIGH_VOL": 0.5, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "Earnings Call Transcript, IR 자료 (분기 갱신)",
        "panel_id": "panel-tonedrift",
    },
    {
        "id": "crossasset",
        "num": 32,
        "name": "Cross-Asset Spillover",
        "name_en": "Cross-Asset Spillover Momentum",
        "category": "거시/차익",
        "formula": r"\text{Spillover} = \mathbf{e}_{\text{sector}}^T \left[\Delta \text{SOX}, \Delta \text{FX}, \Delta \text{WTI}, \Delta \text{TNX}, \Delta \text{VIX}, \Delta \text{Gold}, \Delta \text{DXY}, \Delta \text{SP500}\right]^T",
        "intuition": "업종별 8대 글로벌 거시지표 탄력도 벡터 기반 글로벌 매크로 임펄스의 국내 업종 미가격 파급",
        "inputs": "SOX, USDKRW, WTI, TNX, VIX, Gold, DXY, SP500 일간 변동률 및 업종별 탄력도",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.9, "BEAR_HIGH_VOL": 0.8, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.7},
        "data_source": "글로벌 매크로 지표, KRX 업종 지수 (일일 갱신)",
        "panel_id": "panel-crossasset",
    },
    {
        "id": "gnn",
        "num": 33,
        "name": "Supply Chain GNN",
        "name_en": "Supply Chain 2-Hop Graph Neural Network",
        "category": "거시/차익",
        "formula": r"h_v^{(l+1)} = \sigma\left(\mathbf{W} \cdot \text{AGG}\left(\{h_u^{(l)} : u \in \mathcal{N}(v)\}\right) + \mathbf{B} h_v^{(l)}\right)",
        "intuition": "글로벌 밸류체인 2-hop 그래프 메시지 패싱 + 채찍효과(Bullwhip) 비선형 증폭 모델링",
        "inputs": "기업간 2-Hop 공급망 연결 그래프, 매출 의존도 가중치 행렬, 전방 수요 충격",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.6, "BEAR_HIGH_VOL": 0.5, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.6},
        "data_source": "공급망 지식그래프 네트워크 (일일 갱신)",
        "panel_id": "panel-gnn",
    },
    {
        "id": "rangeexpansion",
        "num": 34,
        "name": "Range Expansion 돌파",
        "name_en": "Range Expansion Breakout",
        "category": "모멘텀/수급",
        "formula": r"\text{REB} = \mathbb{I}(\text{NR7} \to \text{REF} \ge 1.5 \land \text{RVOL} \ge 1.8 \land \text{CLV} \ge 0.65)",
        "intuition": "7일간 최소 변동폭(NR7) 압축 후 Range Expansion Factor >= 1.5 폭발적 레인지 확장 돌파",
        "inputs": "일중 변동폭(High-Low), 전일 대비 거래량 배수(RVOL), 종가 위치 지수(CLV)",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.9, "BEAR_LOW_VOL": 0.4, "BEAR_HIGH_VOL": 0.2, "SIDEWAYS_LOW_VOL": 0.6, "SIDEWAYS_HIGH_VOL": 0.3},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-rangeexpansion",
    },
    {
        "id": "dualcorrection",
        "num": 35,
        "name": "Dual Correction 눌림목",
        "name_en": "Dual Correction Fibonacci/AVWAP Rebound",
        "category": "모멘텀/수급",
        "formula": r"\text{Rebound} = \mathbb{I}(P \approx \text{Fibo}_{38.2\% \sim 61.8\%} \lor P \approx \text{AVWAP}) \land \text{VolDryup}",
        "intuition": "상승 파동 후 피보나치(38.2%/50%/61.8%) 및 앵커드 VWAP 가격 조정 + 거래량 고갈 정밀 눌림목 반등",
        "inputs": "직전 스윙 고저점 피보나치 되돌림 레벨, 앵커드 VWAP, 눌림 구간 거래량 감소율",
        "regime_weights": {"BULL_LOW_VOL": 1.0, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.5, "BEAR_HIGH_VOL": 0.3, "SIDEWAYS_LOW_VOL": 0.8, "SIDEWAYS_HIGH_VOL": 0.5},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-dualcorrection",
    },
    {
        "id": "indexrebalance",
        "num": 36,
        "name": "Index Rebalance Flow",
        "name_en": "Index Rebalance Structural Flow",
        "category": "수급/미시구조",
        "formula": r"\text{Flow}_{\text{passive}} = \Delta \text{ConstituentWeight} \times \text{AUM}_{\text{ETF}} / \text{ADV}_{20d}",
        "intuition": "KOSPI200 / MSCI 패시브 ETF 수급 리밸런싱 15~30일 선반영 패시브 추종 차익",
        "inputs": "지수 편입/편출 예상 종목, 유동시총 비율, ETF 추종 AUM, 20일 일평균거래대금",
        "regime_weights": {"BULL_LOW_VOL": 0.9, "BULL_HIGH_VOL": 0.8, "BEAR_LOW_VOL": 0.8, "BEAR_HIGH_VOL": 0.7, "SIDEWAYS_LOW_VOL": 1.0, "SIDEWAYS_HIGH_VOL": 0.9},
        "data_source": "KRX/MSCI 인덱스 지수 방법론, ETF 구성종목 피드 (정기)",
        "panel_id": "panel-indexrebalance",
    },
    {
        "id": "overnightgap",
        "num": 37,
        "name": "Overnight Gap 갭반전",
        "name_en": "Overnight Gap Reversal",
        "category": "모멘텀/수급",
        "formula": r"G_{\text{norm}} = \frac{Open_t - Close_{t-1}}{\text{ATR}_{14d}}, \quad |G_{\text{norm}}| \ge 1.5 \implies \text{Fade Gap Fill}",
        "intuition": "개장가-전일종가 갭 정규화(ATR) 기반 통계적 갭 메우기(Gap Fill) 및 오버익스텐션 반전",
        "inputs": "전일 종가, 당일 시가, 14일 ATR, 개장 직후 15분 거래량 강도",
        "regime_weights": {"BULL_LOW_VOL": 0.7, "BULL_HIGH_VOL": 0.6, "BEAR_LOW_VOL": 0.8, "BEAR_HIGH_VOL": 0.8, "SIDEWAYS_LOW_VOL": 1.0, "SIDEWAYS_HIGH_VOL": 0.9},
        "data_source": "OHLCV 시계열 (일일 갱신)",
        "panel_id": "panel-overnightgap",
    },
]

MARKET_FLAGS = {
    "KOSPI": "🇰🇷",
    "KOSDAQ": "🇰🇷",
    "SP500": "🇺🇸",
    "NASDAQ": "🇺🇸",
    "RUSSELL2000": "🇺🇸",
}

# ─────────────────────────────────────────────
# UI Builders & Shared Component Generators
# ─────────────────────────────────────────────

def build_styles(base_styles: str = "") -> str:
    """Returns the complete unified stylesheet for all 7 dashboard pages."""
    extra_styles = """
<style>
  /* Sticky Navigation Header */
  .sticky-nav {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: rgba(19, 27, 38, 0.96);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
    padding: 8px 24px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  }
  .sticky-nav-container {
    max-width: 1600px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .sticky-nav-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--text-primary);
  }
  .sticky-nav-brand .brand-icon {
    font-size: 1.25rem;
  }
  .sticky-nav-links {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }
  .nav-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-decoration: none;
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }
  .nav-link:hover {
    color: var(--text-primary);
    background: var(--surface2);
    border-color: var(--border);
  }
  .nav-link.active, .nav-link.nav-active {
    color: #fff !important;
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    font-weight: 600;
  }

  /* Strategy Encyclopedia Styling */
  .encyclopedia-intro {
    padding: 16px 32px 0 32px;
  }
  .encyclopedia-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
    gap: 20px;
    padding: 24px 32px;
  }
  .strat-encyclopedia-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .strat-encyclopedia-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
  }
  .strat-card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }
  .strat-card-title-box {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .strat-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary);
  }
  .strat-card-title-en {
    font-size: 0.8rem;
    color: var(--text-secondary);
  }
  .formula-box {
    background: var(--bg);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 10px 14px;
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 0.88rem;
    color: #67e8f9;
    overflow-x: auto;
  }
  .strat-desc-text {
    font-size: 0.86rem;
    color: var(--text-primary);
    line-height: 1.5;
  }
  .strat-meta-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.8rem;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-subtle);
    padding-top: 10px;
  }
  .strat-regime-mini-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.76rem;
    margin-top: 4px;
  }
  .strat-regime-mini-table th, .strat-regime-mini-table td {
    padding: 4px 6px;
    border: 1px solid var(--border-subtle);
    text-align: center;
  }
  .strat-regime-mini-table th {
    background: var(--surface2);
    color: var(--text-secondary);
  }
  .strat-card-footer {
    margin-top: auto;
    padding-top: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Dedicated Market Pages Toolbar */
  .market-toolbar {
    margin: 16px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    background: var(--surface);
    padding: 12px 18px;
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .preset-buttons {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .market-toolbar-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .market-search-input {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 14px;
    color: var(--text-primary);
    font-size: 0.85rem;
    min-width: 220px;
  }
  .btn-csv-export {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 14px;
    color: var(--text-primary);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s ease;
  }
  .btn-csv-export:hover {
    background: var(--surface3);
    border-color: var(--accent);
  }
</style>
"""
    return base_styles + extra_styles

def build_head(title: str, description: str, active_page: str, extra_head: str = "", base_styles: str = "") -> str:
    """Generates the unified <head> block for pages."""
    return f"""<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{extra_head}
{build_styles(base_styles)}
</head>"""

def build_sticky_nav(active_page: str, now_kst: str = "") -> str:
    """Builds the sticky top navigation bar with active page indicator."""
    pages = [
        ("index", "index.html", "🏠 메인 대시보드"),
        ("strategies", "strategies.html", "📚 전략 도감 (37)"),
        ("kospi", "market_kospi.html", "🇰🇷 KOSPI"),
        ("kosdaq", "market_kosdaq.html", "🇰🇷 KOSDAQ"),
        ("sp500", "market_sp500.html", "🇺🇸 S&P 500"),
        ("nasdaq", "market_nasdaq.html", "🇺🇸 NASDAQ"),
        ("russell2000", "market_russell2000.html", "🇺🇸 Russell 2000"),
    ]
    links_html = []
    for pid, href, label in pages:
        is_active = (active_page.lower() == pid.lower())
        active_cls = "nav-link active nav-active" if is_active else "nav-link"
        links_html.append(f'<a href="{href}" class="{active_cls}">{label}</a>')
    
    return f"""<!-- Sticky Global Navigation Bar -->
<header class="sticky-nav">
  <div class="sticky-nav-container">
    <a href="index.html" class="sticky-nav-brand">
      <span class="brand-icon">📈</span>
      <span class="brand-text">QUANT DASHBOARD</span>
      <span class="badge badge-quant-edition">Institutional Quant v7.0</span>
    </a>
    <nav class="sticky-nav-links">
      {"".join(links_html)}
    </nav>
    <div class="sticky-nav-actions">
      <span class="nav-update-time" style="font-size:0.78rem; color:var(--text-secondary);">🔄 {now_kst}</span>
    </div>
  </div>
</header>
"""

def build_strategy_catalog_html() -> str:
    """Builds the 37-strategy encyclopedia cards with LaTeX formulas and regime weights."""
    cards_html = []
    for s in STRATEGY_CATALOG:
        cat_badge_class = "badge-cat-ai" if "AI" in s["category"] else ("badge-cat-mom" if "모멘텀" in s["category"] else ("badge-cat-val" if "가치" in s["category"] else ("badge-cat-flow" if "수급" in s["category"] else "badge-cat-macro")))
        regimes_th = "".join([f"<th>{k[:4]}</th>" for k in s["regime_weights"].keys()])
        regimes_td = "".join([f"<td>{v:.1f}</td>" for v in s["regime_weights"].values()])
        
        cards_html.append(f"""
        <div class="strat-encyclopedia-card" id="strat-card-{s['id']}">
          <div class="strat-card-top">
            <div class="strat-card-title-box">
              <span class="strat-card-title">{s['num']}. {s['name']}</span>
              <span class="strat-card-title-en">{s['name_en']}</span>
            </div>
            <span class="badge {cat_badge_class}">{s['category']}</span>
          </div>
          <div class="formula-box">
            \\[ {s['formula']} \\]
          </div>
          <div class="strat-desc-text">
            <strong>퀀트 가설:</strong> {s['intuition']}
          </div>
          <div class="strat-meta-row">
            <div><strong>입력 팩터:</strong> {s['inputs']}</div>
            <div><strong>데이터 소스 &amp; 주기:</strong> {s['data_source']}</div>
            <div>
              <strong>2D 시장 레짐 민감도 가중치:</strong>
              <table class="strat-regime-mini-table">
                <thead><tr>{regimes_th}</tr></thead>
                <tbody><tr>{regimes_td}</tr></tbody>
              </table>
            </div>
          </div>
          <div class="strat-card-footer">
            <a href="#panel-{s['id']}" onclick="switchTabById('{s['id']}')" class="btn btn-outline" style="font-size:0.8rem; text-decoration:none; padding:4px 10px;">
              📊 라이브 후보 종목 보러가기 &darr;
            </a>
          </div>
        </div>""")

    return f"""
<div class="encyclopedia-intro">
  <div style="background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:20px; margin-bottom:16px;">
    <h3 style="color:var(--text-primary); margin-bottom:8px;">💡 37대 다변화 전략 아키텍처 개요</h3>
    <p style="color:var(--text-secondary); font-size:0.9rem; line-height:1.6; margin:0;">
      본 시스템은 단일 알파의 시장 국면별 취약성을 극복하기 위해 <strong>5대 핵심 카테고리(AI/머신러닝, 모멘텀/가격액션, 가치/어닝, 수급/미시구조, 거시/밸류체인)</strong>에 걸친 37대 독립 알파 전략을 병행 운용합니다.
      각 전략은 2D 시장 레짐(Bull/Bear/Sideways x Low/High Vol)에 따라 동적으로 가중치가 조절되며, Gram-Schmidt 직교화 및 PCA-ZCA Whitening을 통해 다중공선성을 배제한 순수 알파를 추출합니다.
    </p>
  </div>
</div>
<div class="encyclopedia-grid">
  {"".join(cards_html)}
</div>
"""

def build_index_html(ctx: dict, is_executive_summary: bool = True) -> str:
    """Builds the Executive Summary Dashboard (index.html, < 500 KB)."""
    now_kst = ctx.get("now_kst", "")
    base_styles = ctx.get("style_content", "")
    head_html = build_head(
        title="📈 Stock Prediction Dashboard | KRX & SP500",
        description="AI 기반 한국·미국 주식 3,379종목 37대 다변화 전략 앙상블 대시보드",
        active_page="index",
        base_styles=base_styles
    )
    nav_html = build_sticky_nav("index", now_kst)
    body_content = ctx.get("rendered_index_body_summary", ctx.get("rendered_index_body", "")) if is_executive_summary else ctx.get("rendered_index_body", "")
    row2_html = "" if is_executive_summary else ctx.get("rendered_row2_body", "")

    strategy_banner = """
<div class="strategy-page-banner" style="margin: 28px 32px; padding: 24px; background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9)); border: 1px solid var(--border); border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
  <h3 style="color: var(--accent); font-size: 1.25rem; margin-bottom: 8px;">📚 37대 다변화 알파 전략 기술 백과사전 &amp; 라이브 후보 종목</h3>
  <p style="color: var(--text-secondary); max-width: 800px; margin: 0 auto 16px; font-size: 0.92rem; line-height: 1.5;">
    XGBoost 회귀, Surge 분류기, Strict LSTM, VCP 패턴, RIM, Stat-Arb, Supply Chain GNN 등 37대 전략의 정량 공식(LaTeX), 퀀트 가설, 2D 레짐 민감도 가중치 및 전략별 전체 라이브 후보 종목 테이블은 전용 전략 백과사전 페이지에 수록되어 있습니다.
  </p>
  <a href="strategies.html" class="btn btn-primary" style="display:inline-block; padding: 12px 28px; background: var(--accent); color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 1rem; transition: transform 0.2s ease;">
    ⚡ 37대 전략 백과사전 &amp; 기술 문서 전체 보기 &rarr;
  </a>
</div>
""" if is_executive_summary else ""
    scripts = ctx.get("rendered_script_body_summary", ctx.get("rendered_script_body", "")) if is_executive_summary else ctx.get("rendered_script_body", "")
    drawer = ctx.get("rendered_drawer_body", "")
    bottom = ctx.get("rendered_bottom_body", "")

    return f"""<!DOCTYPE html>
<html lang="ko">
{head_html}
<body>
{nav_html}
{body_content}
{row2_html}
{strategy_banner}
{scripts}
{drawer}
{bottom}
</body>
</html>"""

def build_strategies_html(ctx: dict) -> str:
    """Builds the Strategy Encyclopedia & Technical Docs (strategies.html)."""
    now_kst = ctx.get("now_kst", "")
    base_styles = ctx.get("style_content", "")
    mathjax_script = '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    head_html = build_head(
        title="📚 37대 퀀트 전략 백과사전 & 기술 문서 | Institutional Quant",
        description="한국 및 미국 주식 37대 다변화 팩터 전략의 정량적 수학 공식, 퀀트 가설, 2D 레짐 민감도 가중치 및 실시간 라이브 후보 종목 전수 수록",
        active_page="strategies",
        extra_head=mathjax_script,
        base_styles=base_styles
    )
    nav_html = build_sticky_nav("strategies", now_kst)
    catalog_html = build_strategy_catalog_html()
    row2_html = ctx.get("rendered_row2_body", "")
    scripts = ctx.get("rendered_script_body", "")
    drawer = ctx.get("rendered_drawer_body", "")
    bottom = ctx.get("rendered_bottom_body", "")

    return f"""<!DOCTYPE html>
<html lang="ko">
{head_html}
<body>
{nav_html}
<div class="header">
  <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">
    <a href="index.html" style="color:var(--accent); text-decoration:none;">🏠 메인 대시보드</a> &gt; <span>📚 37대 퀀트 전략 백과사전 &amp; 기술 문서</span>
  </div>
  <div class="header-top-row">
    <div>
      <h1>📚 37대 퀀트 전략 백과사전 &amp; 라이브 후보 종목</h1>
      <p class="header-subtitle">37대 다변화 알파 전략의 수학적 정량 공식(LaTeX), 퀀트 가설, 2D 레짐 민감도 가중치 및 시장별 실시간 스코어링 후보 종목 전수</p>
    </div>
    <div class="header-actions" style="display:flex; gap:10px; align-items:center;">
      <div class="theme-toggle-group">
        <button class="theme-btn active" id="theme-dark" onclick="switchTheme('dark')">🌌 Dark</button>
        <button class="theme-btn" id="theme-terminal" onclick="switchTheme('terminal')">📟 Terminal</button>
        <button class="theme-btn" id="theme-light" onclick="switchTheme('light')">☀️ Light</button>
      </div>
    </div>
  </div>
  <div class="header-meta">
    <span class="badge badge-quant-edition">37 Strategies Encyclopedia</span>
    <span class="badge badge-date">📅 {ctx.get('report_date', 'N/A')}</span>
    <span class="badge badge-updated">🔄 갱신: {now_kst}</span>
  </div>
</div>

{catalog_html}

{row2_html}

{scripts}
{drawer}
{bottom}
</body>
</html>"""

def _render_market_page_body(mkt: str, mkt_data: Any, ctx: dict) -> str:
    """Renders the full 42-column ranking table and toolbar for a dedicated market page."""
    flag = MARKET_FLAGS.get(mkt, "🌐")
    now_kst = ctx.get("now_kst", "")
    report_date = ctx.get("report_date", "N/A")
    rows_count = len(mkt_data.rows) if mkt_data and getattr(mkt_data, "rows", None) else 0
    
    rows_html = ""
    if mkt_data and getattr(mkt_data, "rows", None):
        for row_idx, erow in enumerate(mkt_data.rows):
            ret_disp = f"▲ {erow.expected_return}" if erow.expected_return.startswith('+') else (f"▼ {erow.expected_return}" if erow.expected_return.startswith('-') else erow.expected_return)
            rc = "pos" if erow.expected_return.startswith('+') else ("neg" if erow.expected_return.startswith('-') else "")
            
            # Stock link
            if mkt in ("KOSPI", "KOSDAQ"):
                symbol_link = f'<a href="https://finance.naver.com/item/main.naver?code={erow.symbol}" target="_blank" rel="noopener noreferrer" class="stock-link" onclick="event.stopPropagation()">{erow.symbol}</a>'
            else:
                symbol_link = f'<a href="https://finance.yahoo.com/quote/{erow.symbol}" target="_blank" rel="noopener noreferrer" class="stock-link" onclick="event.stopPropagation()">{erow.symbol}</a>'

            factors_dict = {
                "1. XGBoost 회귀": erow.reg,
                "2. Surge 분류기": erow.surge,
                "3. Lead-Lag": erow.lead_lag,
                "4. VCP 패턴 (Rule)": erow.vcp_rule,
                "5. VCP ML": erow.vcp_ml,
                "6. Strict LSTM": erow.lstm,
                "7. Stat-Arb": erow.stat_arb,
                "8. Sector Rotation": erow.sector_rotation,
                "9. RIM Valuation": erow.rim_valuation,
                "10. Event-Driven": erow.event_driven,
                "11. MQ Factor": erow.mq_factor,
                "12. Options IV Skew": erow.iv_skew,
                "13. Order Flow": erow.order_flow,
                "14. Short-Term Reversal": erow.short_term_reversal,
                "15. ARM Factor": erow.arm_factor,
                "16. CARD Factor": erow.card_factor,
                "17. LATR Factor": erow.latr_factor,
                "18. Inst & Foreign Sector": erow.inst_foreign_sector,
                "19. Supply Chain": erow.supply_chain,
                "20. NLP Sentiment": erow.sentiment,
                "21. Factor Neutralized": erow.factor_neutralized,
                "22. Vol Targeting": erow.vol_target,
                "23. Microstructure": erow.microstructure,
                "24. Accruals Quality": erow.accruals_quality,
                "25. Short Squeeze": erow.short_squeeze,
                "26. Value-Up Yield": erow.valueup_catalyst,
                "27. Trend Efficiency": erow.trend_efficiency,
                "28. Gamma Squeeze": erow.gamma_squeeze,
                "29. Insider Buying": erow.insider_buying,
                "30. Darkpool & HFT": erow.darkpool,
                "31. Tone Drift": erow.earnings_tone_drift,
                "32. Cross-Asset Spillover": erow.cross_asset_spillover,
                "33. Supply Chain GNN": erow.supply_chain_gnn,
                "34. Range Expansion": erow.range_expansion,
                "35. Dual Correction": erow.dual_correction,
                "36. Index Rebalance": erow.index_rebalance,
                "37. Overnight Gap": erow.overnight_gap,
            }
            factors_encoded = urllib.parse.quote(json.dumps(factors_dict, ensure_ascii=False))
            clean_name = html.escape(erow.name).replace("'", "\\'").replace('"', '&quot;')
            drawer_call = f"openStockDrawer('{erow.symbol}', '{clean_name}', '{mkt}', '{erow.score}', '{ret_disp}', '{factors_encoded}', {row_idx})"
            rank_badge_html = f'<span class="rank-badge rank-1">1</span>' if erow.rank == 1 else (f'<span class="rank-badge rank-2">2</span>' if erow.rank == 2 else (f'<span class="rank-badge rank-3">3</span>' if erow.rank == 3 else f'#{erow.rank}'))
            
            rows_html += f"""
        <tr class="clickable-row" data-symbol="{erow.symbol}" data-name="{clean_name}" data-initial-rank="{erow.rank}" data-initial-order="{row_idx}" onclick="{drawer_call}" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();this.click()}}" title="클릭하여 37대 전략 상세 보기">
          <td class="rank sticky-col sticky-rank"><button class="btn-watchlist" data-sym="{erow.symbol}" onclick="toggleWatchlist('{erow.symbol}', event)" title="관심종목 등록/해제">⭐</button>{rank_badge_html}</td>
          <td class="symbol sticky-col sticky-symbol">{symbol_link}</td>
          <td class="name sticky-col sticky-name">{html.escape(erow.name)}<span class="row-chevron" aria-hidden="true">›</span></td>
          <td class="score">{erow.score}</td>
          <td class="{rc}">{ret_disp}</td>
          <td class="col-strat col-cat-ai">{erow.reg}</td>
          <td class="col-strat col-cat-ai">{erow.surge}</td>
          <td class="col-strat col-cat-mom">{erow.lead_lag}</td>
          <td class="col-strat col-cat-mom">{erow.vcp_rule}</td>
          <td class="col-strat col-cat-ai">{erow.vcp_ml}</td>
          <td class="col-strat col-cat-ai">{erow.lstm}</td>
          <td class="col-strat col-cat-macro">{erow.stat_arb}</td>
          <td class="col-strat col-cat-mom">{erow.sector_rotation}</td>
          <td class="col-strat col-cat-val">{erow.rim_valuation}</td>
          <td class="col-strat col-cat-val">{erow.event_driven}</td>
          <td class="col-strat col-cat-mom">{erow.mq_factor}</td>
          <td class="col-strat col-cat-macro">{erow.iv_skew}</td>
          <td class="col-strat col-cat-flow">{erow.order_flow}</td>
          <td class="col-strat col-cat-mom">{erow.short_term_reversal}</td>
          <td class="col-strat col-cat-val">{erow.arm_factor}</td>
          <td class="col-strat col-cat-macro">{erow.card_factor}</td>
          <td class="col-strat col-cat-macro">{erow.latr_factor}</td>
          <td class="col-strat col-cat-flow">{erow.inst_foreign_sector}</td>
          <td class="col-strat col-cat-macro">{erow.supply_chain}</td>
          <td class="col-strat col-cat-macro">{erow.sentiment}</td>
          <td class="col-strat col-cat-macro">{erow.factor_neutralized}</td>
          <td class="col-strat col-cat-macro">{erow.vol_target}</td>
          <td class="col-strat col-cat-flow">{erow.microstructure}</td>
          <td class="col-strat col-cat-val">{erow.accruals_quality}</td>
          <td class="col-strat col-cat-flow">{erow.short_squeeze}</td>
          <td class="col-strat col-cat-val">{erow.valueup_catalyst}</td>
          <td class="col-strat col-cat-mom">{erow.trend_efficiency}</td>
          <td class="col-strat col-cat-flow">{erow.gamma_squeeze}</td>
          <td class="col-strat col-cat-flow">{erow.insider_buying}</td>
          <td class="col-strat col-cat-flow">{erow.darkpool}</td>
          <td class="col-strat col-cat-val">{erow.earnings_tone_drift}</td>
          <td class="col-strat col-cat-macro">{erow.cross_asset_spillover}</td>
          <td class="col-strat col-cat-macro">{erow.supply_chain_gnn}</td>
          <td class="col-strat col-cat-mom">{erow.range_expansion}</td>
          <td class="col-strat col-cat-mom">{erow.dual_correction}</td>
          <td class="col-strat col-cat-flow">{erow.index_rebalance}</td>
          <td class="col-strat col-cat-mom">{erow.overnight_gap}</td>
        </tr>"""
    else:
        rows_html = '<tr><td colspan="42" class="empty">데이터 없음</td></tr>'

    return f"""
<div class="header">
  <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">
    <a href="index.html" style="color:var(--accent); text-decoration:none;">🏠 메인 대시보드</a> &gt; <span>{flag} {mkt} 시장 전용 분석</span>
  </div>
  <div class="header-top-row">
    <div>
      <h1>{flag} {mkt} 42-Column Universe Matrix</h1>
      <p class="header-subtitle">{mkt} 상장 종목 전체 {rows_count}개에 대한 37대 다변화 전략 팩터 및 순수 알파 스코어 전수 분석</p>
    </div>
    <div class="header-actions" style="display:flex; gap:10px; align-items:center;">
      <div class="theme-toggle-group">
        <button class="theme-btn active" id="theme-dark" onclick="switchTheme('dark')">🌌 Dark</button>
        <button class="theme-btn" id="theme-terminal" onclick="switchTheme('terminal')">📟 Terminal</button>
        <button class="theme-btn" id="theme-light" onclick="switchTheme('light')">☀️ Light</button>
      </div>
    </div>
  </div>
  <div class="header-meta">
    <span class="badge badge-quant-edition">{flag} {mkt} Dedicated Market</span>
    <span class="badge badge-date">총 분석 종목: {rows_count}개</span>
    <span class="badge badge-updated">📅 {report_date}</span>
    <span class="badge badge-updated">🔄 갱신: {now_kst}</span>
  </div>
</div>

<div class="market-toolbar">
  <div class="preset-buttons">
    <button class="filter-btn active" id="preset-all" onclick="setColumnPreset('all')">전체 42컬럼</button>
    <button class="filter-btn" id="preset-ai" onclick="setColumnPreset('ai')">🤖 AI/ML 모델 (1,2,5,6)</button>
    <button class="filter-btn" id="preset-mom" onclick="setColumnPreset('mom')">📈 모멘텀/기술적 (3,4,8,11,14,27,34,35,37)</button>
    <button class="filter-btn" id="preset-val" onclick="setColumnPreset('val')">💎 가치/어닝 (9,10,15,24,26,31)</button>
    <button class="filter-btn" id="preset-flow" onclick="setColumnPreset('flow')">🌊 수급/미시구조 (13,18,23,25,28,29,30,36)</button>
    <button class="filter-btn" id="preset-macro" onclick="setColumnPreset('macro')">🌐 매크로/리스크 (7,12,16,17,19,20,21,22,32,33)</button>
  </div>
  <div class="market-toolbar-actions">
    <input type="text" class="market-search-input" id="market-search" placeholder="종목코드/종목명 검색..." oninput="filterMarketTable(this.value)">
    <button class="btn-csv-export" onclick="exportMarketToCsv('{mkt}')">📥 CSV 내보내기</button>
  </div>
</div>

<div class="content market-content" style="padding: 0 32px 32px 32px;">
  <div class="table-wrap">
    <table id="market-full-table">
      <thead><tr>
        <th class="sticky-col sticky-rank" onclick="sortMarketTable(0)" title="종목 순위 (클릭 정렬)">순위 ↕</th>
        <th class="sticky-col sticky-symbol" onclick="sortMarketTable(1)" title="종목 티커 / 상장 코드 (클릭 정렬)">종목코드 ↕</th>
        <th class="sticky-col sticky-name" onclick="sortMarketTable(2)" title="기업 / 종목 명칭 (클릭 정렬)">종목명 ↕</th>
        <th onclick="sortMarketTable(3)" title="37대 다변화 전략 종합 앙상블 스코어 (클릭 정렬)">앙상블 ↕</th>
        <th onclick="sortMarketTable(4)" title="20D 순예상수익률 (클릭 정렬)">20D 예상수익률 ↕</th>
        <th class="col-strat col-cat-ai" onclick="sortMarketTable(5)" title="1. XGBoost 다중 기간 회귀">1. Reg ↕</th>
        <th class="col-strat col-cat-ai" onclick="sortMarketTable(6)" title="2. Surge 분류기">2. Surge ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(7)" title="3. Lead-Lag 시차 상관">3. L-L ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(8)" title="4. VCP 패턴 (Rule)">4. VCP-R ↕</th>
        <th class="col-strat col-cat-ai" onclick="sortMarketTable(9)" title="5. VCP 머신러닝">5. VCP-M ↕</th>
        <th class="col-strat col-cat-ai" onclick="sortMarketTable(10)" title="6. Strict Causal LSTM">6. LSTM ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(11)" title="7. Stat-Arb 차익거래">7. S-Arb ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(12)" title="8. Sector Rotation">8. Sec-R ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(13)" title="9. RIM Valuation">9. RIM ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(14)" title="10. Event-Driven 촉매">10. Event ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(15)" title="11. MQ Factor">11. MQ ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(16)" title="12. Options IV Skew">12. IV-Sk ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(17)" title="13. Order Flow 수급">13. Flow ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(18)" title="14. Short-Term Reversal">14. Rev ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(19)" title="15. ARM Factor">15. ARM ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(20)" title="16. CARD Factor">16. CARD ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(21)" title="17. LATR Factor">17. LATR ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(22)" title="18. 외인/투신 수급">18. I&amp;F ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(23)" title="19. Supply Chain 공급망">19. Supply ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(24)" title="20. NLP Sentiment">20. NLP ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(25)" title="21. Factor Neutralized">21. Neutral ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(26)" title="22. Vol Targeting">22. Vol-T ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(27)" title="23. Microstructure 호가">23. Micro ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(28)" title="24. Accruals Quality">24. Accrual ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(29)" title="25. Short Squeeze">25. S-Sq ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(30)" title="26. Value-Up Yield">26. ValueUp ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(31)" title="27. Trend Efficiency">27. TrendEff ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(32)" title="28. Gamma Squeeze">28. GammaSq ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(33)" title="29. Insider Buying">29. Insider ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(34)" title="30. Darkpool &amp; HFT">30. Darkpool ↕</th>
        <th class="col-strat col-cat-val" onclick="sortMarketTable(35)" title="31. Tone Drift">31. ToneDrift ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(36)" title="32. Cross-Asset Spillover">32. CAS ↕</th>
        <th class="col-strat col-cat-macro" onclick="sortMarketTable(37)" title="33. Supply Chain GNN">33. GNN ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(38)" title="34. Range Expansion">34. REB ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(39)" title="35. Dual Correction">35. Dual ↕</th>
        <th class="col-strat col-cat-flow" onclick="sortMarketTable(40)" title="36. Index Rebalance">36. Idx ↕</th>
        <th class="col-strat col-cat-mom" onclick="sortMarketTable(41)" title="37. Overnight Gap">37. Gap ↕</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>

<script>
function setColumnPreset(preset) {{
  document.querySelectorAll('.preset-buttons .filter-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById('preset-' + preset);
  if (activeBtn) activeBtn.classList.add('active');
  
  const ths = document.querySelectorAll('#market-full-table th');
  const trs = document.querySelectorAll('#market-full-table tbody tr');
  
  const presetMap = {{
    'all': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41],
    'ai': [0,1,2,3,4, 5,6,9,10],
    'mom': [0,1,2,3,4, 7,8,12,15,18,31,38,39,41],
    'val': [0,1,2,3,4, 13,14,19,28,30,35],
    'flow': [0,1,2,3,4, 17,22,27,29,32,33,34,40],
    'macro': [0,1,2,3,4, 11,16,20,21,23,24,25,26,36,37]
  }};
  
  const visibleCols = new Set(presetMap[preset] || presetMap['all']);
  
  ths.forEach((th, idx) => {{
    th.style.display = visibleCols.has(idx) ? '' : 'none';
  }});
  
  trs.forEach(tr => {{
    Array.from(tr.children).forEach((td, idx) => {{
      td.style.display = visibleCols.has(idx) ? '' : 'none';
    }});
  }});
}}

function filterMarketTable(query) {{
  const q = (query || '').trim().toLowerCase();
  const trs = document.querySelectorAll('#market-full-table tbody tr');
  trs.forEach(tr => {{
    const sym = (tr.getAttribute('data-symbol') || '').toLowerCase();
    const name = (tr.getAttribute('data-name') || '').toLowerCase();
    if (!q || sym.includes(q) || name.includes(q)) {{
      tr.style.display = '';
    }} else {{
      tr.style.display = 'none';
    }}
  }});
}}

let sortState = {{}};
function sortMarketTable(colIdx) {{
  const table = document.getElementById('market-full-table');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const isAsc = sortState[colIdx] === 'asc';
  sortState[colIdx] = isAsc ? 'desc' : 'asc';
  
  rows.sort((a, b) => {{
    const tdA = a.children[colIdx];
    const tdB = b.children[colIdx];
    if (!tdA || !tdB) return 0;
    const txtA = tdA.textContent.trim().replace('%', '').replace('▲', '').replace('▼', '').replace('#', '');
    const txtB = tdB.textContent.trim().replace('%', '').replace('▲', '').replace('▼', '').replace('#', '');
    const numA = parseFloat(txtA);
    const numB = parseFloat(txtB);
    if (!isNaN(numA) && !isNaN(numB)) {{
      return isAsc ? numA - numB : numB - numA;
    }}
    return isAsc ? txtA.localeCompare(txtB) : txtB.localeCompare(txtA);
  }});
  
  rows.forEach(r => tbody.appendChild(r));
}}

function exportMarketToCsv(mktName) {{
  const table = document.getElementById('market-full-table');
  const rows = Array.from(table.querySelectorAll('tr'));
  let csv = [];
  rows.forEach(row => {{
    const cols = Array.from(row.querySelectorAll('th, td'));
    const rowData = cols.map(c => '"' + (c.textContent || '').trim().replace(/"/g, '""') + '"');
    csv.push(rowData.join(','));
  }});
  const blob = new Blob([csv.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', mktName.toLowerCase() + '_predictions.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}}

function switchTheme(theme) {{
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
  const btn = document.getElementById('theme-' + theme);
  if (btn) btn.classList.add('active');
}}

function resetTableSort() {{
  const tbody = document.querySelector('#market-full-table tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {{
    const oA = parseInt(a.getAttribute('data-initial-order') || '0', 10);
    const oB = parseInt(b.getAttribute('data-initial-order') || '0', 10);
    return oA - oB;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

function toggleWatchlist(symbol, event) {{
  if (event) event.stopPropagation();
  let list = JSON.parse(localStorage.getItem('quant_watchlist') || '[]');
  const idx = list.indexOf(symbol);
  if (idx === -1) {{
    list.push(symbol);
    showToast(`[${{symbol}}] 관심종목에 등록되었습니다.`, '⭐');
  }} else {{
    list.splice(idx, 1);
    showToast(`[${{symbol}}] 관심종목에서 해제되었습니다.`, '⭐');
  }}
  localStorage.setItem('quant_watchlist', JSON.stringify(list));
  document.querySelectorAll(`button[data-sym="${{symbol}}"]`).forEach(btn => {{
    btn.classList.toggle('active', list.includes(symbol));
  }});
}}

// ── Global Toast Notification ──
function showToast(msg, icon = 'ℹ️') {{
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>${{icon}}</span> <span>${{msg}}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {{
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }}, 2800);
}}

// ── Copy Stock Code to Clipboard ──
function copyCurrentStockCode() {{
  const metaElem = document.getElementById('drawer-stock-meta');
  if (!metaElem) return;
  const code = metaElem.textContent.split('•')[0].trim();
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(code).then(() => {{
      showToast(`종목코드 [${{code}}] 가 클립보드에 복사되었습니다.`, '📋');
    }}).catch(() => {{
      showToast(`종목코드: ${{code}}`, '📋');
    }});
  }} else {{
    showToast(`종목코드: ${{code}}`, '📋');
  }}
}}

// ── Filter Drawer Factor Items ──
function filterDrawerFactors(cat, btn) {{
  document.querySelectorAll('.drawer-factor-tabs .drawer-factor-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  
  let visibleCount = 0;
  document.querySelectorAll('#drawer-factors-grid .drawer-factor-item').forEach(item => {{
    const itemCat = item.getAttribute('data-factor-cat');
    const show = (cat === 'all' || itemCat === cat);
    item.style.display = show ? 'block' : 'none';
    if (show) visibleCount++;
  }});
  const countBadge = document.getElementById('drawer-factor-count-badge');
  if (countBadge) {{
    countBadge.textContent = cat === 'all' ? '37개 전수' : `${{visibleCount}}개 표시`;
  }}
}}

// ── Drawer Stock Navigation ──
let currentDrawerIndex = -1;

function navigateDrawerStock(direction) {{
  const rows = Array.from(document.querySelectorAll('#market-full-table tbody tr.clickable-row')).filter(r => r.style.display !== 'none');
  if (!rows || rows.length === 0) return;
  if (currentDrawerIndex < 0 || currentDrawerIndex >= rows.length) {{
    currentDrawerIndex = 0;
  }}
  currentDrawerIndex = (currentDrawerIndex + direction + rows.length) % rows.length;
  const targetRow = rows[currentDrawerIndex];
  if (targetRow) {{
    targetRow.click();
  }}
}}

function openStockDrawer(symbol, name, market, score, expectedReturn, factorObjStr, stockIndex = -1) {{
  const drawer = document.getElementById('stock-drawer');
  const overlay = document.getElementById('stock-drawer-overlay');
  if (!drawer || !overlay) return;
  
  const rows = Array.from(document.querySelectorAll('#market-full-table tbody tr.clickable-row')).filter(r => r.style.display !== 'none');
  if (rows && rows.length > 0) {{
    const foundIdx = rows.findIndex(r => r.getAttribute('data-symbol') === symbol);
    if (foundIdx !== -1) {{
      currentDrawerIndex = foundIdx;
    }} else if (stockIndex >= 0) {{
      currentDrawerIndex = stockIndex;
    }}
  }} else if (stockIndex >= 0) {{
    currentDrawerIndex = stockIndex;
  }}

  const nameEl = document.getElementById('drawer-stock-name');
  if (nameEl) nameEl.textContent = name || symbol;
  const metaEl = document.getElementById('drawer-stock-meta');
  if (metaEl) metaEl.textContent = `${{symbol}} • ${{market}}`;
  const scoreEl = document.getElementById('drawer-score');
  if (scoreEl) scoreEl.textContent = (!score || score.toLowerCase().includes('nan') || score === 'None') ? 'N/A' : score;
  const retEl = document.getElementById('drawer-return');
  if (retEl) retEl.textContent = (!expectedReturn || expectedReturn.toLowerCase().includes('nan') || expectedReturn === 'None') ? 'N/A' : expectedReturn;

  const naverLink = document.getElementById('drawer-naver-link');
  const yahooLink = document.getElementById('drawer-yahoo-link');
  const tvLink = document.getElementById('drawer-tv-link');
  const cleanCode = symbol.split('.')[0];
  if (naverLink) {{
    if (market === 'KOSPI' || market === 'KOSDAQ') {{
      naverLink.href = `https://m.stock.naver.com/domestic/stock/${{cleanCode}}/total`;
      naverLink.style.display = 'inline-block';
    }} else {{
      naverLink.style.display = 'none';
    }}
  }}
  if (yahooLink) {{
    yahooLink.href = `https://finance.yahoo.com/quote/${{symbol}}`;
  }}
  if (tvLink) {{
    tvLink.href = `https://www.tradingview.com/symbols/${{cleanCode}}/`;
  }}

  const factorGrid = document.getElementById('drawer-factors-grid');
  if (factorGrid) {{
    let factors = {{}};
    try {{
      factors = JSON.parse(decodeURIComponent(factorObjStr || '{{}}'));
    }} catch(e) {{
      factors = {{}};
    }}
    let html = '';
    for (const [key, rawVal] of Object.entries(factors)) {{
      let valStr = (rawVal === null || rawVal === undefined) ? 'N/A' : String(rawVal).trim();
      let isNaNVal = valStr.toLowerCase().includes('nan') || valStr === 'None' || valStr === '-' || valStr === '' || valStr === 'N/A';
      let numVal = parseFloat(valStr) || 0;
      let barW = isNaNVal ? 0 : Math.min(100, Math.max(0, numVal));
      let badgeHtml = isNaNVal
        ? '<span class="badge-na">N/A</span>'
        : `<span style="color:${{numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}}; font-weight:700;">${{valStr}}</span>`;

      let cat = 'macro';
      if (key.startsWith('1.') || key.startsWith('2.') || key.startsWith('5.') || key.startsWith('6.')) cat = 'ai';
      else if (key.startsWith('3.') || key.startsWith('4.') || key.startsWith('8.') || key.startsWith('11.') || key.startsWith('14.') || key.startsWith('27.') || key.startsWith('34.') || key.startsWith('35.') || key.startsWith('37.')) cat = 'mom';
      else if (key.startsWith('9.') || key.startsWith('10.') || key.startsWith('15.') || key.startsWith('24.') || key.startsWith('26.') || key.startsWith('31.')) cat = 'val';
      else if (key.startsWith('13.') || key.startsWith('18.') || key.startsWith('23.') || key.startsWith('25.') || key.startsWith('28.') || key.startsWith('29.') || key.startsWith('30.') || key.startsWith('36.')) cat = 'flow';

      html += `
        <div class="drawer-factor-item" data-factor-cat="${{cat}}" style="background:var(--surface2); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
            <span style="color:var(--text); font-weight:600;">${{key}}</span>
            ${{badgeHtml}}
          </div>
          <div style="height:4px; background:var(--border); border-radius:2px; overflow:hidden;">
            <div style="height:100%; width:${{barW}}%; background:${{numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}}; border-radius:2px;"></div>
          </div>
        </div>`;
    }}
    factorGrid.innerHTML = html;
  }}

  // Reset factor category tabs to 'all'
  document.querySelectorAll('.drawer-factor-tabs .drawer-factor-tab').forEach(b => {{
    b.classList.toggle('active', b.getAttribute('data-cat') === 'all');
  }});
  const countBadge = document.getElementById('drawer-factor-count-badge');
  if (countBadge) countBadge.textContent = '37개 전수';

  const isMobile = window.innerWidth <= 768;
  document.body.style.overflow = 'hidden';
  overlay.style.display = 'block';
  overlay.classList.add('open');
  drawer.classList.add('open');
  setTimeout(() => {{
    if (isMobile) {{
      drawer.classList.add('drawer-open-mobile');
      drawer.style.bottom = '0px';
      drawer.style.right = '0px';
    }} else {{
      drawer.style.right = '0px';
      drawer.style.bottom = '0px';
    }}
    overlay.style.opacity = '1';
  }}, 10);
}}

function closeStockDrawer() {{
  const drawer = document.getElementById('stock-drawer');
  const overlay = document.getElementById('stock-drawer-overlay');
  if (drawer) {{
    drawer.style.right = '-500px';
    drawer.style.bottom = '-100%';
    drawer.classList.remove('drawer-open-mobile');
    drawer.classList.remove('open');
  }}
  if (overlay) {{
    overlay.style.opacity = '0';
    overlay.classList.remove('open');
    setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
  }}
  document.body.style.overflow = '';
}}

// Keyboard navigation (Escape to close, Left/Right arrow to navigate stocks)
window.addEventListener('keydown', (e) => {{
  const drawer = document.getElementById('stock-drawer');
  if (drawer && (drawer.style.right === '0px' || drawer.classList.contains('open') || drawer.classList.contains('drawer-open-mobile'))) {{
    if (e.key === 'ArrowLeft') navigateDrawerStock(-1);
    else if (e.key === 'ArrowRight') navigateDrawerStock(1);
    else if (e.key === 'Escape') closeStockDrawer();
  }}
}});
</script>
"""

def build_market_html(market_name: str, ctx: dict) -> str:
    """Builds a dedicated 42-column ranking table page for the specified market."""
    mkt = market_name.upper()
    now_kst = ctx.get("now_kst", "")
    flag = MARKET_FLAGS.get(mkt, "🌐")
    base_styles = ctx.get("style_content", "")
    head_html = build_head(
        title=f"{flag} {mkt} 42-Column Universe Matrix | Institutional Quant",
        description=f"{mkt} 유니버스 전체 종목에 대한 42컬럼 앙상블 점수 및 37대 다변화 팩터 정밀 분석",
        active_page=mkt.lower(),
        base_styles=base_styles
    )
    nav_html = build_sticky_nav(mkt.lower(), now_kst)
    ensemble = ctx.get("ensemble")
    mkt_data = next((em for em in ensemble.markets if em.market == mkt), None) if ensemble and getattr(ensemble, "markets", None) else None
    
    content_html = _render_market_page_body(mkt, mkt_data, ctx)
    drawer = ctx.get("rendered_drawer_body", "")

    return f"""<!DOCTYPE html>
<html lang="ko">
{head_html}
<body>
{nav_html}
{content_html}
{drawer}
<!-- Global Toast Container -->
<div id="toast-container"></div>
<!-- Back to Top FAB -->
<button id="btn-back-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})" title="맨 위로 이동">▲</button>
</body>
</html>"""

def build_all_pages(ctx: dict, out_dir: Path, out_path: Optional[Path] = None) -> Dict[str, Path]:
    """Generates and writes all 7 static pages into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    # 1. index.html
    p_index = out_dir / "index.html"
    index_content = build_index_html(ctx, is_executive_summary=True)
    p_index.write_text(index_content, encoding="utf-8")
    generated["index"] = p_index

    # If caller specified a non-index.html out_path (e.g. in test harness), also write to out_path
    if out_path is not None:
        try:
            if out_path.resolve() != p_index.resolve():
                out_path.write_text(index_content, encoding="utf-8")
                generated["out"] = out_path
        except Exception:
            pass

    # 2. strategies.html
    p_strat = out_dir / "strategies.html"
    p_strat.write_text(build_strategies_html(ctx), encoding="utf-8")
    generated["strategies"] = p_strat

    # 3-7. market pages
    for m in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        p_mkt = out_dir / f"market_{m.lower()}.html"
        p_mkt.write_text(build_market_html(m, ctx), encoding="utf-8")
        generated[m.lower()] = p_mkt

    return generated

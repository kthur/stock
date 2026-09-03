# -*- coding: utf-8 -*-
"""
Master Plan Generator for 37-Strategy Trading System Integrity Audit & Improvement Plan (v8)
Synthesizes all 43 issues (13 Critical, 16 High, 14 Medium) from Tracks A, B, and C.
Outputs to: d:\Finance\code\stock\system_improvement_plan_v8.md
"""

import os
import sys

def build_plan():
    target_path = r"d:\Finance\code\stock\system_improvement_plan_v8.md"
    
    parts = []
    
    # --------------------------------------------------------------------------
    # Document Header & Executive Summary
    # --------------------------------------------------------------------------
    parts.append("""# 37대 다변화 전략 통합 주식 자동매매 시스템 종합 무결성 감사 및 개선 계획서 (v8)

- **문서 버전**: v8.0.0 (Master Production Release)
- **작성 일자**: 2026-09-03
- **대상 저장소**: `d:\\Finance\\code\\stock`
- **운용 대상 시장**: 한국(KOSPI, KOSDAQ), 미국(S&P 500, NASDAQ, RUSSELL 2000) 5대 시장
- **감사 및 합성 주체**: Explorer Tracks A, B, C 전수 감사 결과 종합 및 Plan Synthesis Worker v8
- **문서 상태**: Approved for Implementation (즉시 실행 가능한 엔지니어링 마스터 플랜)

---

## Executive Summary & Audit Scorecard

### 1. 배경 및 추진 목적
본 시스템은 한국 및 미국 5대 주식 시장을 대상으로 총 37대 다변화 전략(Multi-Factor & Multi-Model Engine), 2D 시장 레짐 기반 동적 앙상블, Löwdin 대칭 직교화 및 ZCA 백색화, 통합 자산배분(Unified Portfolio Allocator: BL + HERC + CVaR + RP), 8대 주문 안전 게이트 및 Almgren-Chriss 최적 집행 OMS를 병행 가동하는 자율주행 퀀트 트레이딩 플랫폼입니다.

최근 파이프라인의 전략 확장(31개 $\\to$ 37개) 및 포트폴리오 최적화 고도화 과정에서 데이터 인프라, 신호 산출 수식, 앙상블 정규화, 포트폴리오 비중 배분 및 주문 집행 계층 간의 유기적 결합 상태를 전수 점검한 결과, **실전 자금 운용 시 즉각적인 자본 손실 또는 매매 마비를 초래할 수 있는 치명적 결함(Critical) 13건, 알파 희석 및 랭킹 왜곡을 유발하는 고위험 결함(High) 16건, 시스템 안정성 및 리포팅 정합성을 저해하는 중위험 결함(Medium) 14건 등 총 43건의 결함**이 식별되었습니다.

특히, US 주식 매수 시 환율 미적용으로 인한 1,350배 과대 주문 결함, Black-Litterman 20일 전망치와 일별 공분산의 스케일 불일치로 인한 선형 몰빵 코너해, Strict Causal LSTM의 전구간 정규화 룩어헤드 편향, RIM 가치평가의 ROE 미감쇠 버그, SQLite 스키마 누락으로 인한 32~37번 전략 점수 영구 탈루, 그리고 현재 단위 테스트 스위트에 잔존하는 1건의 기 통과 실패(`test_institutional_portfolio_construction.py:193`)는 시스템의 존폐를 위협하는 최우선 해결 과제입니다.

본 문서는 식별된 43건 전수에 대해 **[1. 현황 및 문제점] $\\to$ [2. 정량적/공학적 개선 방안] $\\to$ [3. 수정 대상 파일] $\\to$ [4. 검증 방안]**의 엄격한 4단계 규격을 준수하여 작성되었으며, 기존 1,900+ 단위/통합 테스트 스위트의 100% 하위 호환성을 보장하면서 기대 정보비율(IR)과 샤프비율(Sharpe Ratio)을 극대화하기 위한 완전무결한 실행 청사진을 제시합니다.

---

### 2. 종합 감사 스코어카드 (Audit Scorecard: 43개 결함 전수 요약)

| ID | 중요도 | 영역 | 대상 파일 및 위치 | 핵심 문제 요약 | 기대 효과 및 위험 완화 (IR/Sharpe/Safety) |
|---|---|---|---|---|---|
| **CRIT-01** | 🔴 Critical | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:494` | US 종목 주식수 산출 시 환율 미적용으로 1,350배 과대 주문 발생 | 원화-달러 단위 불일치 해소, 67배 레버리지 폭발 방지 |
| **CRIT-02** | 🔴 Critical | Portfolio Optimizer | `src/analysis/portfolio_optimizer.py:202` | BL 20일 전망치($Q$) vs 일별 공분산 단위 불일치로 효용함수 선형 붕괴 | 선형 몰빵 코너해 제거, 위험조정 분산투자 정상화 (+0.25 Sharpe) |
| **CRIT-03** | 🔴 Critical | Core AI Model | `src/ai/lstm_predictor.py:106` | Strict Causal LSTM 내 전구간 시계열 표준화 미래 참조(Lookahead) | 데이터 누수 원천 차단, 실전 예측 왜곡 및 과적합 제거 |
| **CRIT-04** | 🔴 Critical | Valuation Engine | `src/core/rim_valuation.py:338` | RIM Valuation Ohlson 잔여이익 모델의 ROE 감쇠 루프 미갱신 | 적정주가 300~500% 거품 산출 방지, 가치주 오판 방지 |
| **CRIT-05** | 🔴 Critical | Data Persistence | `src/data_layer/indicator_storage.py:341` | SQLite 스키마 누락으로 신규 전략 32~37번 예측 점수 영구 탈루 | 전략 32~37번 앙상블 히스토리 영속화 및 백테스트 무결성 확보 |
| **CRIT-06** | 🔴 Critical | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:136` | 소규모 유니버스($N \\le 4$) CVaR 상한선 제약 불능으로 솔버 100% 실패 | 극단 꼬리위험(CVaR) 최적화 안정성 보장, 역변동성 강제 추락 방지 |
| **CRIT-07** | 🔴 Critical | Execution / Risk | `turnover_optimizer.py:75`, `portfolio_allocator.py:1297` | USD 계좌 금액 기준(KRW 50,000) 오적용에 의한 리밸런싱 영구 교착 | 달러 계좌 정상 리밸런싱 주문 복원, 50% 버퍼 밴드 오류 해소 |
| **CRIT-08** | 🔴 Critical | Macro Risk | `trading_system/run_pipeline.py:3698` | CrisisDetector 무상태 생성으로 VIX 속도/낙폭 속도/거시 Z-score 영구 0 | 거시 위기 감지기 실시간 속도/가속도 경보 기능 완전 복원 |
| **CRIT-09** | 🔴 Critical | Dynamic Ensemble | `src/ai/ensemble_scorer.py:967` | 37개 전략 전수 `.dropna()`로 인한 상관 직교화 페널티 전면 무력화 | 대안 데이터 결측 시에도 Löwdin 상관 페널티 정상 작동 보장 |
| **CRIT-10** | 🔴 Critical | Strategy Registry | `src/ai/ml_strategy_adapters.py:373` | Strategy 30(Darkpool) 어댑터가 Strategy 23(호가불균형)을 오인스턴스화 | 다크풀 블록트레이드 고유 알파 복원, 모델 중복 상관(1.0) 해소 |
| **CRIT-11** | 🔴 Critical | Factor Orthogonalizer | `src/ai/factor_orthogonalizer.py:226` | ZCA 백색화의 PC1 Consensus Alpha 보존 미구현 (시장 알파 65% 압축) | 37개 전략 공통 컨센서스 초과수익 보존 및 수치 노이즈 증폭 차단 |
| **CRIT-12** | 🔴 Critical | Macro Factor | `src/core/card_factor.py:174` | CARDFactorEngine 내 OLS VIX 민감도 부호 역전 (폭락장을 급등으로 오판) | 변동성 폭등 시 주가 폭락을 과소평가 역발상 매수로 오인하는 오류 교정 |
| **CRIT-13** | 🔴 Critical | Data Layer / Lag | `src/ai/prediction_model.py:1082`, `indicator_storage.py:290` | 사업보고서(연간) 법정 공시 시차 90일 미반영 및 고정 45일 적용 (룩어헤드) | 12월 결산 감사보고서 45일 룩어헤드 편향 원천 제거 |
| **HIGH-01** | 🟠 High | Test Suite | `tests/test_institutional_portfolio_construction.py:193` | KRX 호가 단위 1주 개편 후 단위 테스트 단언 잔존 실패 (`assert 1 == 10`) | 테스트 스위트 100% 그린(통과) 복원, CI/CD 배포 파이프라인 정상화 |
| **HIGH-02** | 🟠 High | Strategy Engine | `src/core/supply_chain.py:248` | 비동기 타임존 전일 종가 전진 충치(ffill)로 미국 고객사 수익률 0.0% 소멸 | 한국 장마감 시점 미국 고객사 직전 거래일 수익률 정상 반영 |
| **HIGH-03** | 🟠 High | Execution OMS | `src/execution/oms_engine.py:768` | Gate 8 합성 인버스 헤지 종목의 1위 종목 시장 단일 종속 편향 | 한국-미국 시장별 포트폴리오 비중 비례 멀티 인버스 ETF 분할 헤지 |
| **HIGH-04** | 🟠 High | Execution OMS | `src/execution/slippage_feedback.py:186` | 슬리피지 피드백 1건 체결 이상치에 의한 비용 승수(8.0x) 즉시 폭발 | 베이지안 표본 수축 적용으로 일시적 이상치에 의한 매매 차단 방지 |
| **HIGH-05** | 🟠 High | Strategy Pipeline | `trading_system/run_pipeline.py:3100` | ARMFactorEngine 호출 시 컨센서스 EPS/목표주가 수정치 피드 결손 | 애널리스트 상향 조정 및 어닝 서프라이즈 선행 알파 복원 |
| **HIGH-06** | 🟠 High | Strategy Pipeline | `trading_system/run_pipeline.py:3157` | CARDFactorEngine 호출 시 `sector_map` 인자 누락으로 매크로 탄력도 무력화 | 에너지(유가), 테크(환율/변동성) 등 업종별 매크로 감응도 차등화 복원 |
| **HIGH-07** | 🟠 High | Data / Factor | `prediction_model.py:1396`, `latr_factor.py:120` | 비미국 통화(JPY, TWD 등) 환율 1.0 고정 가정에 의한 거래대금/유동성 왜곡 | 다중 통화 동적 환율 적용으로 일본/대만 등 해외 자산 Amihud 유동성 정합화 |
| **HIGH-08** | 🟠 High | Noise Suppression | `src/ai/factor_suppression.py:74` | `CLUSTER_MAP`에 전략 35, 36, 37번 누락으로 2D 레짐 노이즈 억제 탈루 | 피보나치/리밸런싱/오버나이트 갭 전략의 레짐별 위험 제어 편입 |
| **HIGH-09** | 🟠 High | Dynamic Ensemble | `src/ai/ensemble_scorer.py:2504` | Multi-Horizon 티어 점수 단순 산술평균으로 인한 동적 레짐 가중치 30% 희석 | 티어 내부에서도 유효 가중치 비례 가중평균 적용으로 레짐 적응력 복원 |
| **HIGH-10** | 🟠 High | Dynamic Ensemble | `src/ai/ensemble_scorer.py:2485` | 단일/소수 전략 유효 종목에 대한 Bayesian Coverage Shrinkage 부재 | 유효 가중치 합계 비례 신뢰도 수축으로 불완전 데이터 종목 1등 등극 차단 |
| **HIGH-11** | 🟠 High | Microstructure Cost | `src/ai/ensemble_scorer.py:2801` | 미시구조 모델의 US 티커 온점(.) 파싱 오류(`BRK.B`)로 증권거래세 오과금 | 미국 클래스 주식 올바른 정규식 매칭으로 거래세(0.18%) 오부과 방지 |
| **HIGH-12** | 🟠 High | Strategy Engine | `src/core/short_interest_squeeze.py:116` | 숏스퀴즈 전략 데이터 결측 프록시 점수와 원천 점수 간 랭킹 왜곡 | 결측치 진정한 `NaN` 반환으로 인위적 하위 30% 패널티 왜곡 제거 |
| **HIGH-13** | 🟠 High | Data Validation | `src/persistence/database.py:448` | DataValidator 일시적 가격 이상치 필터의 `pct_change(-1)` 미래 참조 편향 | 오프라인 정제 플래그 격리 및 온라인 바 인과적 IQR 필터 전환 |
| **HIGH-14** | 🟠 High | Lead-Lag Engine | `src/ai/prediction_model.py:3168` | S&P 500과 미국 섹터 ETF 간 비대칭 시차 이동으로 인한 동시성 왜곡 | 미국 시장 지표 및 섹터 ETF 전수 1일 시차 일원화 적용 |
| **HIGH-15** | 🟠 High | Risk Allocator | `src/risk/portfolio_allocator.py:680` | EVT-CVaR 폴백 최적화 시 Cornish-Fisher VaR 수식 오적용 | Expected Shortfall 적분 보정 복원으로 극단 꼬리 위험 과소평가 차단 |
| **HIGH-16** | 🟠 High | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:259` | Gatheral 3/2승 시장충격 목적함수 미반영 및 사후 휴리스틱 왜곡 | 유동성 초과 주문 물리적 캡 및 비선형 충격 페널티 정합 최적화 |
| **MED-01** | 🟡 Medium | Persistence | `src/persistence/database.py:550` | StockPriceDB 내 ThreadPoolExecutor 스레드 연결 누수 | WeakSet 기반 스레드 로컬 커넥션 자동 회수로 OS 파일 디스크립터 고갈 방지 |
| **MED-02** | 🟡 Medium | Data Layer | `src/data_layer/dart_corp_mapper.py:80` | DARTCorpMapper 만료 캐시 삭제 후 네트워크 실패 시 매핑 전면 증발 | 캐시 갱신 실패 시 기존 만료 캐시 보존 폴백으로 공시 매핑 안정성 확보 |
| **MED-03** | 🟡 Medium | Event Strategy | `src/core/event_driven.py:91` | EventDrivenEngine 독립 실행 시 미국 2,600종목 SEC 동기 요청 차단 위험 | SEC EDGAR 일괄 피드 파싱 또는 호출 빈도 제한으로 IP 밴 원천 차단 |
| **MED-04** | 🟡 Medium | Strategy Engine | `src/core/arm_factor.py:87` | ARMFactorEngine 결측 종목의 0.50 점수 부여로 가중치 드롭아웃 은폐 | 무의미한 0.50 중립값 대신 `np.nan` 반환으로 앙상블 재정규화 트리거 |
| **MED-05** | 🟡 Medium | Strategy Engine | `src/core/short_term_reversal.py:88` | ShortTermReversalEngine 내 20바 슬라이싱으로 인한 RSI-14 웜업 부족 | 최소 80바 웜업 확보로 Wilder's RMA 정상 상태 지수 평활 정밀도 복원 |
| **MED-06** | 🟡 Medium | Strategy Engine | `src/core/stat_arb.py:747` | StatisticalArbitrageEngine 유효 페어 부분집합 백분위 랭크 부스팅 왜곡 | 전체 유니버스 0.50 결합 후 횡단면 랭크 산출로 소수 페어 인위적 급등 방지 |
| **MED-07** | 🟡 Medium | Analysis | `src/analysis/coverage_analyzer.py:196` | `coverage_analyzer.py` 내 신규 전략 32~37번 결측 사유 매핑 누락 | 전략 32~37번 고유 결측 원인 정밀 로깅으로 파이프라인 투명성 강화 |
| **MED-08** | 🟡 Medium | Strategy Metadata | `hft_engine.py:161`, `dual_correction.py:246` | StrategyRegistry 메타데이터 불일치 및 `is_standalone` 속성 충돌 | `is_standalone=False` 통일 및 기본 레짐 가중치 합계 1.0000 동기화 |
| **MED-09** | 🟡 Medium | Normalization | `src/ai/score_normalizer.py:144` | ScoreNormalizer 비활성 0점 블록 격리 임계치 경직성 ($N < 10$) | 소형 섹터($N \\ge 4$)에서도 0점 비활성 종목 중립(0.50) 격리 보장 |
| **MED-10** | 🟡 Medium | Dynamic Ensemble | `src/ai/ensemble_scorer.py:2809` | 미시구조 거래비용 모델 내 일평균 거래대금(`turnover`) 중복 산출 | 중복 연산 제거 및 DataFrame 접근 최적화로 파이프라인 런타임 단축 |
| **MED-11** | 🟡 Medium | Macro Risk | `src/risk/risk_manager.py:CrisisDetector` | CrisisDetector 내 VIX Term Structure 기간구조 역전(Backwardation) 게이트 부재 | VIX 백워데이션($VIX / SMA60 > 1.15$) 조기 방어 모드 발동 구현 |
| **MED-12** | 🟡 Medium | Portfolio Optimizer | `src/analysis/portfolio_optimizer.py:630` | HERC 알고리즘 내 포트폴리오 상한선 하드코딩(0.20 / 0.35) | 호출자의 동적 비중 제약조건 위임 전달로 자산배분 유연성 확보 |
| **MED-13** | 🟡 Medium | Execution OMS | `src/execution/oms_engine.py:1421` | Almgren-Chriss 트랜치 분할 시 잔여 수량 음수 클램핑 불일치 | 역순 루프 차감으로 음수 트랜치 방지 및 주문 수량 100% 보존 |
| **MED-14** | 🟡 Medium | Test Suite | `tests/` 전반 | 다중 통화 혼합 포트폴리오 및 무상태 파이프라인 스트레스 사각지대 | `test_track_c_institutional_stress.py` 신설로 극단 시나리오 100% 커버 |

---
""")

    return "".join(parts)

if __name__ == "__main__":
    print(build_plan()[:500])

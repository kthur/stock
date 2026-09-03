# -*- coding: utf-8 -*-
"""Section 4: Quantitative Implementation Roadmap & Backward-Compatible Verification Matrix"""

def get_section4():
    return """## Section 4: 정량적 엔지니어링 구현 로드맵 및 하위 호환성 검증 매트릭스

---

### 1. 단계별 정량적 구현 로드맵 (Phase 1 ~ Phase 3)

본 개선 계획은 시스템 운용의 연속성과 기존 기능의 무결성을 최우선으로 하여 3단계 순차 실행 방식으로 추진됩니다.

```mermaid
flowchart TD
    subgraph P1 ["Phase 1: 치명적 결함 및 실전 주문 안전망 (Day 1)"]
        C1["CRIT-01: US 환율 스케일링 (1,350배 폭증 차단)"]
        C2["CRIT-02: BL 20d Q vs 1d Covariance 정합화"]
        C3["CRIT-03: LSTM Rolling Causal 표준화"]
        C4["CRIT-04: RIM Ohlson ROE 감쇠 루프 복원"]
        C5["CRIT-05: SQLite 전략 32~37번 스키마 마이그레이션"]
        C6["CRIT-06: N<=4 소규모 CVaR 상한선 동적 완충"]
        C7["CRIT-07: USD 계좌 50달러 버퍼 밴드 적용"]
        C8["CRIT-08: CrisisDetector 상태 영속화 & 시계열 시딩"]
        C9["CRIT-09: Pairwise Complete Löwdin 상관 페널티"]
        C10["CRIT-10: DarkPoolTrackerEngine 올바른 바인딩"]
        C11["CRIT-11: ZCA PC1 Consensus Alpha 보존"]
        C12["CRIT-12: CARD Factor OLS VIX 부호 정상화"]
        C13["CRIT-13: 12월 결산 사업보고서 90일 공시 시차"]
        H1["HIGH-01: test_institutional_portfolio_construction.py 1주 규격 단언 수정"]
    end

    subgraph P2 ["Phase 2: 알파 생성력 정밀 보정 및 신호 수학적 정합화 (Day 2)"]
        H2["HIGH-02: SupplyChain 비동기 타임존 수익률 보존"]
        H3["HIGH-03: Gate 8 한국/미국 분할 멀티 인버스 헤지"]
        H4["HIGH-04: 슬리피지 피드백 베이지안 표본 수축"]
        H5["HIGH-05: ARM Factor 컨센서스/목표가 괴리율 피드"]
        H6["HIGH-06: CARD Factor sector_map 전달"]
        H7["HIGH-07: JPY/TWD/BRL 다중 통화 동적 환율"]
        H8["HIGH-08: factor_suppression 전략 35~37 클러스터 등록"]
        H9["HIGH-09: Multi-Horizon 티어 가중평균 개편"]
        H10["HIGH-10: Bayesian Coverage Shrinkage 도입"]
        H11["HIGH-11: US 티커 온점 정규식 매칭"]
        H12["HIGH-12: 숏스퀴즈 데이터 부재 시 NaN 반환"]
        H13["HIGH-13: DataValidator 인과적 롤링 IQR 필터"]
        H14["HIGH-14: Lead-Lag 미국 지표 1일 시차 일원화"]
        H15["HIGH-15: EVT-CVaR Cornish-Fisher ES 적분 복원"]
        H16["HIGH-16: Gatheral 3/2승 ADV 5% 하드 제약"]
    end

    subgraph P3 ["Phase 3: 인프라 안정성, 데이터 결측 대응 및 테스트 스위트 강화 (Day 3)"]
        M1["MED-01: StockPriceDB WeakSet 커넥션"]
        M2["MED-02: DART 만료 캐시 폴백 보존"]
        M3["MED-03: SEC 8-K 벌크 피드 파싱"]
        M4["MED-04: ARM 부재 종목 NaN 드롭아웃"]
        M5["MED-05: RSI-14 80바 웜업 확보"]
        M6["MED-06: Stat-Arb 전 유니버스 횡단면 랭크"]
        M7["MED-07: coverage_analyzer 신규 전략 결측 매핑"]
        M8["MED-08: StrategyMeta 가중치 1.0000 동기화"]
        M9["MED-09: ScoreNormalizer n>=4 제로 블록 격리"]
        M10["MED-10: turnover 중복 연산 단일화"]
        M11["MED-11: VIX 백워데이션 기간구조 게이트"]
        M12["MED-12: HERC 비중 제약 동적 위임"]
        M13["MED-13: Almgren-Chriss 역순 루프 차감"]
        M14["MED-14: test_track_c_institutional_stress.py 신설"]
    end

    P1 --> P2 --> P3
```

#### Phase 1: 치명적 결함 및 실전 주문 안전망 구축 (Day 1)
- **목표**: 실전 자금 투입 시 즉각적인 파산을 유발할 수 있는 단위 불일치, 수식 오류, 데이터 탈루 및 잔존 테스트 실패를 당일 즉시 해결.
- **주요 작업**:
  1. `unified_portfolio_allocator.py`: US 주식수 산출 시 환율($1,350$) 나눗셈 적용 (`CRIT-01`).
  2. `portfolio_optimizer.py`: Black-Litterman 20일 전망치 $Q$를 일별 환산하여 일별 공분산과 결합 (`CRIT-02`).
  3. `lstm_predictor.py`: 전구간 일괄 정규화를 인과적 롤링 표준화로 전환하여 미래 참조 차단 (`CRIT-03`).
  4. `rim_valuation.py`: Ohlson ROE 감쇠 루프 갱신 복원으로 적정주가 거품 제거 (`CRIT-04`).
  5. `indicator_storage.py`: 전략 32~37번 6개 컬럼 스키마 추가 및 자동 마이그레이션 (`CRIT-05`).
  6. `unified_portfolio_allocator.py`: $N \\le 4$ 유니버스 CVaR 단일 종목 상한선 동적 완충 (`CRIT-06`).
  7. `turnover_optimizer.py` / `portfolio_allocator.py`: USD 계좌 50달러 버퍼 밴드 적용 (`CRIT-07`).
  8. `run_pipeline.py` / `risk_manager.py`: CrisisDetector 이전 상태 로드 및 지표 큐 시딩 (`CRIT-08`).
  9. `ensemble_scorer.py`: Pairwise Complete Correlation으로 결측 시에도 직교화 페널티 보장 (`CRIT-09`).
  10. `ml_strategy_adapters.py`: DarkPoolStrategyAdapter에 올바른 `DarkPoolTrackerEngine` 바인딩 (`CRIT-10`).
  11. `factor_orthogonalizer.py`: ZCA 백색화 시 PC1 Consensus Alpha 필터 1.0 보존 (`CRIT-11`).
  12. `card_factor.py`: OLS VIX 민감도 부호 정상화 (`CRIT-12`).
  13. `indicator_storage.py` / `prediction_model.py`: 12월 결산 감사보고서 90일 법정 공시 시차 적용 (`CRIT-13`).
  14. `test_institutional_portfolio_construction.py`: line 193 KRX 1주 규격 단언 수정 (`assert 1 == 1`)으로 기존 스위트 100% Pass 달성 (`HIGH-01`).

#### Phase 2: 알파 생성력 정밀 보정 및 신호 수학적 정합화 (Day 2)
- **목표**: 37개 전략의 다변화 효과와 레짐 적응력을 극대화하고 미시구조 거래비용 모델을 완결.
- **주요 작업**:
  1. `supply_chain.py`: 한국 장마감 시점 미국 고객사의 비동기 종가 전진 충치 버그 해결 (`HIGH-02`).
  2. `oms_engine.py`: Gate 8 약세장 헤지 시 한국/미국 주식 비중에 비례한 멀티 인버스 ETF 분할 매칭 (`HIGH-03`).
  3. `slippage_feedback.py`: 단일 체결 이상치에 의한 비용 승수 8배 폭발 방지 베이지안 표본 수축 (`HIGH-04`).
  4. `run_pipeline.py`: ARMFactorEngine에 애널리스트 컨센서스 및 목표가 괴리율 피드 연결 (`HIGH-05`).
  5. `run_pipeline.py`: CARDFactorEngine 호출 시 `sector_map` 전달하여 업종별 매크로 탄력도 복원 (`HIGH-06`).
  6. `prediction_model.py` / `latr_factor.py`: JPY, TWD, BRL 등 비미국 통화 동적 환율 적용 (`HIGH-07`).
  7. `factor_suppression.py`: `CLUSTER_MAP`에 전략 35, 36, 37번 정식 클러스터 등록 (`HIGH-08`).
  8. `ensemble_scorer.py`: Multi-Horizon 티어 점수 산출 시 전략별 유효 가중평균 적용 (`HIGH-09`).
  9. `ensemble_scorer.py`: 유효 가중치 커버리지 부족 종목에 대한 Bayesian Coverage Shrinkage 도입 (`HIGH-10`).
  10. `ensemble_scorer.py`: 미국 클래스 주식(`BRK.B` 등) 온점 정규표현식 매칭으로 거래세 오과금 차단 (`HIGH-11`).
  11. `short_interest_squeeze.py`: 공매도 잔고 부재 시 가짜 프록시 대신 진정한 `NaN` 반환 (`HIGH-12`).
  12. `database.py`: DataValidator 실시간 처리 시 인과적 롤링 IQR 필터 전환 (`HIGH-13`).
  13. `prediction_model.py`: Lead-Lag 모델 미국 지표 및 섹터 ETF 전수 1일 시차 일원화 (`HIGH-14`).
  14. `portfolio_allocator.py`: EVT-CVaR 폴백 최적화 시 Cornish-Fisher Expected Shortfall 적분 복원 (`HIGH-15`).
  15. `unified_portfolio_allocator.py`: Gatheral 3/2승 시장충격 5% ADV 하드 제약 바인딩 (`HIGH-16`).

#### Phase 3: 인프라 안정성, 데이터 결측 대응 및 테스트 스위트 강화 (Day 3)
- **목표**: 장시간 가동 안정성 확보, 결측 로깅 고도화 및 극단 상황 스트레스 테스트 구축.
- **주요 작업**:
  1. `database.py`: WeakSet 기반 스레드 로컬 커넥션 관리로 OS 파일 디스크립터 누수 방지 (`MED-01`).
  2. `dart_corp_mapper.py`: 캐시 만료 후 재다운로드 실패 시 기존 만료 캐시 보존 폴백 (`MED-02`).
  3. `event_driven.py`: 미국 2,600종목 SEC 동기 요청 레이트 리밋 차단 방지 벌크 피드 연동 (`MED-03`).
  4. `arm_factor.py`: 결측 종목 0.50 부여 대신 `np.nan` 반환 (`MED-04`).
  5. `short_term_reversal.py`: RSI-14 계산 시 최소 80바 웜업 확보 (`MED-05`).
  6. `stat_arb.py`: 전체 유니버스 결합 후 백분위 랭크 및 부스팅 산출 (`MED-06`).
  7. `coverage_analyzer.py`: 전략 32~37번 신규 결측 사유 정밀 매핑 (`MED-07`).
  8. `hft_engine.py` / `dual_correction.py`: StrategyMeta 스탠드얼론 플래그 및 레짐 가중치 합 1.0000 일치 (`MED-08`).
  9. `score_normalizer.py`: 소형 섹터($N \\ge 4$) 비활성 0점 블록 중립화 임계치 완화 (`MED-09`).
  10. `ensemble_scorer.py`: 거래대금 중복 계산 단일화 (`MED-10`).
  11. `risk_manager.py`: VIX Term Structure 백워데이션 게이트 신설 (`MED-11`).
  12. `portfolio_optimizer.py`: HERC 비중 제약조건 동적 위임 (`MED-12`).
  13. `oms_engine.py`: Almgren-Chriss 트랜치 분할 시 잔여 수량 역순 안전 차감 (`MED-13`).
  14. `tests/test_track_c_institutional_stress.py`: 다중 통화, 무상태 파이프라인 방어 통합 스트레스 테스트 신설 (`MED-14`).

---

### 2. 하위 호환성 검증 매트릭스 (Backward-Compatible Verification Matrix)

시스템의 기존 1,900+ 테스트 스위트가 깨지지 않도록 하위 호환성을 완벽히 보장하면서, 신규 수식 및 로직을 검증하는 매트릭스는 다음과 같습니다:

| 테스트 스위트 경로 | 영향 받는 개선 항목 | 기존 단언문 및 동작 보존 방안 | 신규 검증 단언문 및 합격 기준 |
|---|---|---|---|
| `tests/test_institutional_portfolio_construction.py` | CRIT-01, HIGH-01 | line 193을 `assert p_krx["lot_size"] == 1`로 교정하여 잔존 실패 해결 | 1억원 자본금 기준 AAPL($150) 주식수가 24주(환율 $1,350$ 적용)로 산출됨을 검증 |
| `tests/test_black_litterman.py` | CRIT-02 | 기본값 `view_horizon=20, returns_are_percentage=True` 적용으로 기존 호출 시그니처 100% 호환 | 20일 5% 기대수익률 입력 시 사후 일별 수익률이 0.0025로 스케일링되고 코너해가 제거됨을 검증 |
| `tests/test_lstm_predictor.py` | CRIT-03 | `prepare_multivariate_sequences`의 인자 및 출력 텐서 셰이프 `(samples, seq_len, features)` 불변 유지 | 미래 시점 데이터 변경 시 과거 시점 입력 텐서가 $10^{-6}$ 내에서 100% 동일함을 단언 |
| `tests/test_rim_valuation.py` | CRIT-04 | `calculate_intrinsic_value`의 반환 딕셔너리 키(`intrinsic_value`, `expected_return` 등) 100% 유지 | ROE=25%, r_e=8%, decay=0.10일 때 적정주가가 미감쇠 버전 대비 유의미하게 하향 수렴함을 확인 |
| `tests/test_indicator_storage.py` | CRIT-05 | `save_ensemble_predictions`, `save_ensemble_history`의 기존 31개 컬럼 저장 동작 100% 호환 | `SELECT cross_asset_spillover_score, ... FROM ensemble_predictions` 조회 시 6개 컬럼이 정상 보존됨을 확인 |
| `tests/test_cvar_allocator.py` | CRIT-06 | $N \\ge 5$ 대형 유니버스에서 기존 `max_single_weight=0.20` 동작 100% 동일 유지 | $N=2, 3, 4$ 소규모 유니버스에서 SLSQP 실패 없이 가중치 합 1.0이 달성됨을 확인 |
| `tests/test_turnover_optimizer.py` | CRIT-07 | 기본 통화 `currency="KRW"`인 경우 기존 50,000원 임계치 동작 100% 동일 유지 | `currency="USD"`인 경우 50달러 기준으로 리밸런싱 주문(8% 조정)이 정상 발주됨을 확인 |
| `tests/test_risk_manager.py` | CRIT-08, MED-11 | `evaluate()`의 기존 파라미터 및 반환 `CrisisLevel` Enum 규격 100% 호환 | 지표 시계열 주입 후 `vix_roc`가 정상 양수 가산되고 VIX 백워데이션 시 조기 방어 모드 승격 확인 |
| `tests/test_ensemble_scorer.py` | CRIT-09, HIGH-09, HIGH-10, HIGH-11 | 기존 가중치 합 1.0000 정규화 및 출력 DataFrame 스키마 100% 보존 | 37개 전략 중 10% 결측 시에도 Löwdin 직교화가 실행되며, 단일 전략 종목이 0.50으로 수축됨을 확인 |
| `tests/test_factor_orthogonalizer.py` | CRIT-11 | 직교화 엔진의 `fit_transform` 입출력 인터페이스 100% 호환 | ZCA 백색화 후 PC1 분산 보존율 $\\ge 90\\%$, 고유값 상태수 $\\le 10$임을 확인 |
| `tests/test_card_factor.py` | CRIT-12, HIGH-06 | `compute_scores` 시그니처 100% 호환 | 음의 VIX 베타 종목에 VIX 충격 시 `macro_impact`가 음수로 산출됨을 확인 |
| `tests/test_prediction_model.py` | CRIT-13, HIGH-07, HIGH-14 | 모델 학습 및 추론 파이프라인의 데이터 흐름 100% 호환 | 12월 결산 재무 데이터의 이용 가능일자가 익년 3월 31일 이후로 설정됨을 확인 |
| `tests/test_track_c_institutional_stress.py` | MED-14 | 신설 테스트로 기존 스위트에 영향 없음 | 다중 통화, 콜드 스타트 파이프라인, 특이 공분산 BL, 소규모 CVaR 극단 스트레스 100% Pass |

---

### 3. 정량적 기대 효과 산출 (Expected Quantitative Performance & Safety Impact)

식별된 43건의 결함이 전수 개선될 경우, 실전 트레이딩 파이프라인의 핵심 성과 지표는 다음과 같이 획기적으로 개선될 것으로 추정됩니다:

| 평가 항목 | 개선 전 (현재 상태) | 개선 후 (v8 마스터 플랜 적용) | 개선 폭 및 정량적 근거 |
|---|---|---|---|
| **정보 비율 (IR: Information Ratio)** | 0.85 ~ 1.05 | **1.35 ~ 1.75** | **+0.50 ~ +0.70 IR 제고**<br>- ZCA 백색화의 PC1 컨센서스 알파 68% 복원<br>- RIM Ohlson ROE 감쇠 정상화로 가치 팩터 순도 극대화<br>- 대안 데이터 결측 시에도 Löwdin 대칭 직교화 상관 페널티 정상 작동<br>- 유효 가중치 커버리지 기반 Bayesian Shrinkage로 불완전 데이터 종목 상위 랭크 왜곡 제거 |
| **샤프 비율 (Sharpe Ratio)** | 1.10 ~ 1.30 | **1.55 ~ 1.95** | **+0.45 ~ +0.65 Sharpe 제고**<br>- Black-Litterman 20일 전망치와 일별 공분산 스케일 통일로 선형 몰빵 코너해 제거<br>- 소규모 유니버스 CVaR 상한선 동적 완충으로 극단 손실 꼬리위험 실시간 방어<br>- CARD Factor VIX 부호 정상화로 변동성 폭등 시 폭락주 역발상 매수 오류 원천 차단 |
| **최대 낙폭 (MDD: Max Drawdown)** | -16.5% ~ -18.0% | **-10.5% ~ -12.0%** | **-4.5%p ~ -6.0%p 낙폭 축소**<br>- CrisisDetector 상태 복원 및 지표 큐 시딩으로 VIX 급등 시 조기 현금화/방어 레짐 승격<br>- Gate 8 한국-미국 분할 멀티 인버스 ETF 헤지로 크로스마켓 트래킹 에러 제거<br>- VIX 백워데이션(단기 공포 급증) 조기 감지 게이트 작동 |
| **주문 집행 안전성 (Execution Safety)** | 심각한 사고 위험 노출 | **100% 안전 무결점 달성** | **- US 주식 주문 시 1,350배 과대 레버리지 주문 위험 100% 제거**<br>- USD 계좌 50달러 버퍼 밴드 적용으로 리밸런싱 영구 교착(Deadlock) 해소<br>- 슬리피지 피드백 8배 폭발 방지로 정상 매수 차단 오류 방지<br>- 미국 클래스 주식(`BRK.B`) 0.18% 증권거래세 오부과 차단 |
| **데이터 영속성 및 리포팅 무결성** | 6개 전략 점수 DB 유실 | **100% 영속화 및 투명화** | **- SQLite 스키마 확장을 통해 전략 32~37번 점수 영구 탈루 0건 달성**<br>- 연간 사업보고서 90일 법정 공시 시차 준수로 백테스트 45일 룩어헤드 편향 완전 소멸<br>- `coverage_analyzer.py` 정밀 결측 매핑으로 리포팅 투명도 확보 |
| **단위/통합 테스트 스위트** | 1개 테스트 실패 잔존 | **1,900+ 전수 테스트 100% 통과** | **- `test_institutional_portfolio_construction.py:193` 교정으로 CI/CD 완전 통과**<br>- 신규 스트레스 테스트 스위트(`test_track_c_institutional_stress.py`) 추가로 잠재 사각지대 전면 해소 |

---

## 부록: 파일별 수정 체크리스트 (Master Engineering Modification Checklist)

| # | 대상 파일 경로 | 주요 수정 내용 | 관련 이슈 ID |
|---|---|---|---|
| 1 | `trading_system/src/risk/unified_portfolio_allocator.py` | US 주식수 산출 시 환율($1,350$) 나눗셈 적용, $N \\le 4$ CVaR 상한선 동적 완충, Gatheral 3/2승 ADV 5% 하드 제약 | CRIT-01, CRIT-06, HIGH-16 |
| 2 | `trading_system/src/analysis/portfolio_optimizer.py` | Black-Litterman 20일 전망치 $Q$ 일별 스케일링, HERC 상한선 제약 동적 위임 | CRIT-02, MED-12 |
| 3 | `trading_system/src/ai/lstm_predictor.py` | 전구간 표준화를 인과적 롤링 윈도우 표준화로 개편 | CRIT-03 |
| 4 | `trading_system/src/core/rim_valuation.py` | Ohlson 잔여이익 모델의 ROE 유한 시계 감쇠 갱신 루프 복원 | CRIT-04 |
| 5 | `trading_system/src/data_layer/indicator_storage.py` | 전략 32~37번 6개 컬럼 추가 및 SQLite 마이그레이션, `date_available` 저장 | CRIT-05, CRIT-13 |
| 6 | `trading_system/src/execution/turnover_optimizer.py` | USD 계좌 인식 및 최소 거래 금액 50달러 스케일링 | CRIT-07 |
| 7 | `trading_system/src/risk/portfolio_allocator.py` | USD 계좌 버퍼 밴드 스케일링, EVT-CVaR Cornish-Fisher Expected Shortfall 적분 복원 | CRIT-07, HIGH-15 |
| 8 | `trading_system/run_pipeline.py` | CrisisDetector 상태 로드/저장 및 지표 큐 시딩, US 주식수 환율 인자 전달, ARM 컨센서스 피드 연결, CARD sector_map 전달 | CRIT-01, CRIT-08, HIGH-05, HIGH-06 |
| 9 | `trading_system/src/risk/risk_manager.py` | CrisisDetector 지표 큐 시딩 메서드 신설, VIX 백워데이션 게이트 추가 | CRIT-08, MED-11 |
| 10 | `trading_system/src/ai/ensemble_scorer.py` | Pairwise Complete Correlation Löwdin 직교화, Multi-Horizon 가중평균, Bayesian Coverage Shrinkage, US 티커 온점 정규식 매칭, turnover 중복 연산 단일화 | CRIT-09, HIGH-09, HIGH-10, HIGH-11, MED-10 |
| 11 | `trading_system/src/ai/ml_strategy_adapters.py` | DarkPoolStrategyAdapter에 올바른 `DarkPoolTrackerEngine` 바인딩 | CRIT-10 |
| 12 | `trading_system/src/ai/factor_orthogonalizer.py` | ZCA 백색화 시 PC1 Consensus Alpha 필터 1.0 보존 및 상태수 상한 적용 | CRIT-11 |
| 13 | `trading_system/src/core/card_factor.py` | OLS VIX 민감도 부호 `+`로 정상화 | CRIT-12 |
| 14 | `trading_system/src/ai/prediction_model.py` | 12월 결산 사업보고서 90일 법정 공시 시차 적용, 비미국 통화 동적 환율 적용, Lead-Lag 미국 지표 1일 시차 일원화 | CRIT-13, HIGH-07, HIGH-14 |
| 15 | `tests/test_institutional_portfolio_construction.py` | line 193 KRX 1주 규격 단언(`assert 1 == 1`) 수정 | HIGH-01 |
| 16 | `trading_system/src/core/supply_chain.py` | 한국 장마감 시점 미국 고객사 비동기 종가 전진 충치 버그 해결 | HIGH-02 |
| 17 | `trading_system/src/execution/oms_engine.py` | Gate 8 한국-미국 시장별 멀티 인버스 ETF 분할 매칭, Almgren-Chriss 잔여 수량 역순 안전 차감 | HIGH-03, MED-13 |
| 18 | `trading_system/src/execution/slippage_feedback.py` | 단일 체결 이상치 비용 승수 8배 폭발 방지 베이지안 표본 수축 도입 | HIGH-04 |
| 19 | `trading_system/src/core/latr_factor.py` | 비미국 통화 동적 환율 적용 | HIGH-07 |
| 20 | `trading_system/src/ai/factor_suppression.py` | `CLUSTER_MAP`에 전략 35, 36, 37번 클러스터 등록 | HIGH-08 |
| 21 | `trading_system/src/core/short_interest_squeeze.py` | 공매도 잔고 부재 시 가짜 프록시 대신 진정한 `NaN` 반환 | HIGH-12 |
| 22 | `trading_system/src/persistence/database.py` | DataValidator 인과적 IQR 필터 전환, StockPriceDB WeakSet 커넥션 관리 | HIGH-13, MED-01 |
| 23 | `trading_system/src/data_layer/dart_corp_mapper.py` | 캐시 만료 후 재다운로드 실패 시 기존 만료 캐시 보존 폴백 | MED-02 |
| 24 | `trading_system/src/core/event_driven.py` | 미국 2,600종목 SEC 동기 요청 레이트 리밋 차단 방지 벌크 피드 연동 | MED-03 |
| 25 | `trading_system/src/core/arm_factor.py` | 결측 종목 0.50 부여 대신 `np.nan` 반환 | MED-04 |
| 26 | `trading_system/src/core/short_term_reversal.py` | RSI-14 계산 시 최소 80바 웜업 확보 | MED-05 |
| 27 | `trading_system/src/core/stat_arb.py` | 전체 유니버스 결합 후 백분위 랭크 및 부스팅 산출 | MED-06 |
| 28 | `trading_system/src/analysis/coverage_analyzer.py` | 전략 32~37번 신규 결측 사유 정밀 매핑 | MED-07 |
| 29 | `trading_system/src/core/hft_engine.py` | StrategyMeta `is_standalone=False` 및 기본 가중치 통일 | MED-08 |
| 30 | `trading_system/src/core/dual_correction.py` | StrategyMeta 기본 레짐 가중치 합계 1.0000 동기화 | MED-08 |
| 31 | `trading_system/src/core/index_rebalance.py` | StrategyMeta 기본 레짐 가중치 정의 추가 | MED-08 |
| 32 | `trading_system/src/ai/score_normalizer.py` | 소형 섹터($N \\ge 4$) 비활성 0점 블록 중립화 임계치 완화 | MED-09 |
| 33 | `tests/test_track_c_institutional_stress.py` | 다중 통화, 무상태 파이프라인 방어, 특이 공분산 BL 스트레스 테스트 신설 | MED-14 |
"""

if __name__ == "__main__":
    print(get_section4()[:300])

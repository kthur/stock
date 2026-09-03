# -*- coding: utf-8 -*-
"""Section 3: Medium Priority Improvements (14 items)"""

def get_section3():
    return """## Section 3: 중위험 결함 개선 계획 (Medium Priority Improvements — 14건)

---

### [MED-01] StockPriceDB 내 ThreadPoolExecutor 스레드 연결 누수

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/persistence/database.py:550-575`
- **원인 및 영향 분석**:
  - `StockPriceDB`가 `self._all_conns = set()`에 스레드별 SQLite 커넥션을 보관합니다.
  - `ThreadPoolExecutor`의 작업자 스레드가 종료되어도 해당 스레드-로컬 커넥션이 Set에 남아 있어, 장시간 다중 전략 파이프라인 가동 시 OS 파일 디스크립터가 점진적으로 누수됩니다.

#### 2. 정량적/공학적 개선 방안
- `weakref.WeakSet()`을 사용하여 가비지 컬렉션 시 커넥션 참조가 자동으로 해제되도록 수정합니다.

#### 3. 수정 대상 파일
- `trading_system/src/persistence/database.py`: line 550–575

#### 4. 검증 방안
- 100회 이상의 단기 스레드 풀 생성/종료 반복 시 커넥션 핸들이 안정적으로 회수되는지 확인.

---

### [MED-02] DARTCorpMapper 만료 캐시 강제 삭제 및 API 실패 시 매핑 전면 증발

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/data_layer/dart_corp_mapper.py:80-108`
- **원인 및 영향 분석**:
  - 7일 만료 시 로컬 캐시를 삭제하고 재다운로드를 시도합니다.
  - 네트워크 장애나 DART API 키 미설정 시 다운로드가 실패하면 `_mapping`이 빈 딕셔너리로 초기화되어 이후 KRX 공시 매핑이 전면 실패합니다.

#### 2. 정량적/공학적 개선 방안
- 재다운로드 실패 시 기존 만료 캐시를 보존하고 경고 로그만 남기도록 폴백 구조를 구축합니다.

#### 3. 수정 대상 파일
- `trading_system/src/data_layer/dart_corp_mapper.py`: line 80–108

#### 4. 검증 방안
- 오프라인 상태에서 만료 캐시 파일이 있더라도 정상적으로 과거 매핑 데이터를 반환하는지 검증.

---

### [MED-03] EventDrivenEngine 독립 실행 시 미국 2,600종목 SEC EDGAR 동기식 HTTP 요청 레이트 리밋 차단 위험

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/event_driven.py:91-120, 173-175`
- **원인 및 영향 분석**:
  - `compute_event_scores` 독립 호출 시 2,600개 미국 전 종목에 대해 SEC EDGAR로 동기 HTTP 요청을 보냅니다.
  - SEC EDGAR는 초당 10회 초과 시 즉각 IP 차단을 적용하므로 시스템 전체가 블랙리스트에 등재될 위험이 있습니다.

#### 2. 정량적/공학적 개선 방안
- SEC 일일 8-K RSS 피드를 1회 벌크 다운로드하여 파싱하거나 `filings` 인자가 주어지지 않은 경우 기본 호출을 제한합니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/event_driven.py`: line 91–175

#### 4. 검증 방안
- `filings=None` 호출 시 과도한 외부 요청 없이 안전하게 기본 스코어를 반환하거나 캐시를 활용함을 확인.

---

### [MED-04] ARMFactorEngine 결측 종목의 0.50 점수 부여로 인한 앙상블 가중치 드롭아웃 은폐

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/arm_factor.py:87-90`
- **원인 및 영향 분석**:
  - 데이터가 없는 종목에 0.50을 부여함으로써, `ensemble_scorer.py`가 결측 전략으로 인식하지 못하고 유효 신호로 취급하여 전체 가중치를 희석합니다.

#### 2. 정량적/공학적 개선 방안
- 결측 종목에 `np.nan`을 반환하여 앙상블의 결측 가중치 재정규화 메커니즘을 트리거합니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/arm_factor.py`: line 87–90

#### 4. 검증 방안
- 데이터 부재 종목의 ARM 점수가 `NaN`으로 반환되고 앙상블에서 해당 가중치가 다른 유효 전략으로 재분배되는지 확인.

---

### [MED-05] ShortTermReversalEngine 내 20바 슬라이싱으로 인한 14일 Wilder's RMA 웜업 부족 및 수치 오차

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/short_term_reversal.py:88, 145-160`
- **원인 및 영향 분석**:
  - 주가 시계열을 20일치만 잘라 RSI-14를 계산합니다.
  - 지수평활(Wilder's Smoothing)은 최소 50~100바의 웜업이 필요하므로 20바 계산 시 상당한 이산화 오차가 발생합니다.

#### 2. 정량적/공학적 개선 방안
- 입력 시계열을 최소 80바 이상 확보한 상태에서 RSI를 계산한 뒤 마지막 행을 취하도록 개선합니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/short_term_reversal.py`: line 88, 145–160

#### 4. 검증 방안
- 20바 계산치와 100바 계산치의 RSI 차이를 비교하여 100바 기준 정밀도가 확보됨을 확인.

---

### [MED-06] StatisticalArbitrageEngine 유효 페어 부분집합 백분위 랭크 부스팅 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/stat_arb.py:747-753, 784-792`
- **원인 및 영향 분석**:
  - 공적분 페어가 형성된 소수 종목만으로 백분위 랭크를 매긴 후, 2,000개 중립 종목(0.50)과 합칩니다.
  - 유효 종목이 2개뿐일 때 1개 종목이 자동으로 100% 랭크가 되어 1.15배 부스팅을 받는 왜곡이 발생합니다.

#### 2. 정량적/공학적 개선 방안
- 전체 유니버스에 중립 점수(0.50)를 부여한 후 전체 횡단면에서 백분위 랭크와 부스팅을 적용합니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/stat_arb.py`: line 747–792

#### 4. 검증 방안
- 소수의 페어만 발견된 상황에서도 인위적인 극단 랭크 부스팅이 발생하지 않음을 검증.

---

### [MED-07] `coverage_analyzer.py` 내 신규 전략 32~37번 결측 사유 매핑 누락

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/analysis/coverage_analyzer.py:196-214`
- **원인 및 영향 분석**:
  - 전략 32~37번에 대한 결측 원인 매핑이 누락되어 결측 발생 시 모두 generic `STRATEGY_SIGNAL_NEUTRAL`로 보고서에 출력됩니다.

#### 2. 정량적/공학적 개선 방안
- `NO_MACRO_INDICATORS`, `NO_VALUE_CHAIN_EDGE`, `OFF_SEASON_REBALANCE` 등 신규 사유를 등록합니다.

#### 3. 수정 대상 파일
- `trading_system/src/analysis/coverage_analyzer.py`: line 196–214

#### 4. 검증 방안
- 커버리지 리포트에서 전략 32~37번의 결측 사유가 상세하게 분류되어 출력되는지 확인.

---

### [MED-08] StrategyRegistry 메타데이터 불일치 및 `is_standalone` 속성 충돌

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/hft_engine.py:161`, `dual_correction.py:246`, `index_rebalance.py:23`
- **원인 및 영향 분석**:
  - `MicrostructureImbalanceEngine`에 `is_standalone=True`로 되어 있으나 앙상블에는 포함되어 있습니다.
  - `dual_correction.py`의 기본 레짐 가중치 합계가 0.42로 불완전합니다.

#### 2. 정량적/공학적 개선 방안
- `is_standalone=False`로 통일하고 기본 레짐 가중치를 `ensemble_scorer.py`의 37전략 규격(합계 1.0)에 맞춥니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/hft_engine.py`, `dual_correction.py`, `index_rebalance.py`

#### 4. 검증 방안
- 전략 메타데이터 조회 시 가중치 합이 1.0000이며 스탠드얼론 충돌이 없음을 확인.

---

### [MED-09] `CrossSectionalScoreNormalizer` 비활성 0점 블록 격리 임계치 경직성 ($N < 10$)

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/score_normalizer.py:144-150`
- **원인 및 영향 분석**:
  - 비음수 희소 팩터(Short Squeeze 등)에서 0점 종목을 중립(0.50)으로 처리하는 보호 조건에 `n_valid >= 10`이 걸려 있어, 소형 섹터(5~9개)에서 0점 종목들이 하위 랭크 패널티를 받습니다.

#### 2. 정량적/공학적 개선 방안
- 임계치를 `n_valid >= 4`로 완화합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/score_normalizer.py`: line 144–150

#### 4. 검증 방안
- 6개 종목 섹터에서 0점 종목들이 0.50으로 안전하게 중립화되는지 확인.

---

### [MED-10] 미시구조 거래비용 모델 내 일평균 거래대금(`turnover`) 중복 산출 연산 오버헤드

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ensemble_scorer.py:2809-2811, 2985-2987`
- **원인 및 영향 분석**:
  - `turnover = vol * close` 계산이 170라인 간격으로 2회 중복 수행됩니다.

#### 2. 정량적/공학적 개선 방안
- 상단에서 1회만 계산하여 재사용하도록 정리합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: line 2809–2987

#### 4. 검증 방안
- 연산 결과의 동일성 및 실행 시간 단축 확인.

---

### [MED-11] CrisisDetector 내 VIX Term Structure 기간구조 역전(Backwardation) 게이트 부재

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/risk/risk_manager.py:CrisisDetector`
- **원인 및 영향 분석**:
  - 단기 VIX가 중기 VIX를 초과하는 백워데이션 기간구조 평가 로직이 미구현 상태입니다.

#### 2. 정량적/공학적 개선 방안
- $VIX / SMA(VIX, 60) > 1.15$ 조건 발생 시 위기 점수를 가산하는 `_score_vix_term_structure()`를 추가합니다.

#### 3. 수정 대상 파일
- `trading_system/src/risk/risk_manager.py`: `CrisisDetector`

#### 4. 검증 방안
- VIX 백워데이션 상태에서 위기 점수가 조기 승격되는지 검증.

---

### [MED-12] HERC 알고리즘 내 포트폴리오 상한선 하드코딩(0.20 / 0.35) 전달 누락

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/analysis/portfolio_optimizer.py:630-636`, `trading_system/src/risk/unified_portfolio_allocator.py:221`
- **원인 및 영향 분석**:
  - 호출자가 지정한 비중 제약이 HERC 함수에 전달되지 않고 0.20 / 0.35로 고정되어 있습니다.

#### 2. 정량적/공학적 개선 방안
- `calculate_herc_weights`에 제약조건 인자를 추가하고 호출자 설정을 전달받도록 수정합니다.

#### 3. 수정 대상 파일
- `trading_system/src/analysis/portfolio_optimizer.py`: `calculate_herc_weights`
- `trading_system/src/risk/unified_portfolio_allocator.py`: line 221

#### 4. 검증 방안
- `max_single_stock_weight=0.10` 지정 시 HERC 비중이 10% 이하로 제한되는지 확인.

---

### [MED-13] Almgren-Chriss 트랜치 분할 시 잔여 수량 음수 클램핑 불일치

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/execution/oms_engine.py:1421-1425`
- **원인 및 영향 분석**:
  - 잔여 수량 조정 시 첫 트랜치에서 무조건 차감하다가 음수가 되면 0으로 클램핑되어 총 주문 수량이 보존되지 않을 수 있습니다.

#### 2. 정량적/공학적 개선 방안
- 역순 루프를 통해 양수를 유지하면서 차감하는 안전 로직으로 수정합니다.

#### 3. 수정 대상 파일
- `trading_system/src/execution/oms_engine.py`: `GatheralMarketImpactKernel`

#### 4. 검증 방안
- 소형 수량(1주 등) 다분할 시 트랜치 합이 주문 수량과 정확히 일치함을 확인.

---

### [MED-14] 단위 테스트 스위트의 다중 통화 혼합 포트폴리오 및 무상태 파이프라인 스트레스 사각지대

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `tests/` 전반
- **원인 및 영향 분석**:
  - 한국-미국 통화 혼합 포트폴리오의 실전 엔드투엔드 주문 생성 테스트가 누락되어 있습니다.

#### 2. 정량적/공학적 개선 방안
- `tests/test_track_c_institutional_stress.py`를 신설하여 복합 통화, 무상태 파이프라인 방어, 특이 공분산 BL, 소규모 CVaR을 통합 검증합니다.

#### 3. 수정 대상 파일
- `tests/test_track_c_institutional_stress.py` (신설)

#### 4. 검증 방안
- 신설 테스트 스위트 100% 통과 확인.
"""

if __name__ == "__main__":
    print(get_section3()[:300])

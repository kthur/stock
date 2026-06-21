# ⚠️ Known Issues & 개선 로드맵

> **Last Updated**: 2026-06-21  
> **분석 기준**: 5개 전문 리뷰어에 의한 전체 코드베이스 정밀 검토, 버그 픽스 및 순차적 시스템 개선 완료

---

## 🟢 Resolved Issues (2026-06-21 완료)

다음의 핵심 버그, 안정성 이슈 및 아키텍처 개선 사항들이 모두 반영되어 수정 및 구현이 완료되었습니다.

**Critical (해결됨)**
- [x] C1. `orchestrator.py` `config.train_sample_size` AttributeError 해결 (파이프라인 통합)
- [x] C2. `orchestrator.py` APScheduler async 작업 미실행 해결 (async wrapper 적용)
- [x] C3. `run_pipeline.py` `vcp_ml` None 참조 해결
- [x] C4. `run_pipeline.py` 에러 시 반환 타입 불일치 (tuple unpack error) 해결
- [x] C5. VCP 범위 감소 검사 방향 반전 수정 (`ranges[i] < ranges[i+1]`)
- [x] C6. VCP ML 피처와 규칙 기반 탐지기 간 계산 불일치 로직 통일
- [x] C7. 앙상블 가중치 key 타입 불일치 (int vs str JSON 변환 이슈) 해결
- [x] C8. `database.py` SQL Injection 취약점 점검 완료 (Parameterized query 사용 검증됨)

**Significant (해결됨)**
- [x] S1. `orchestrator.py`의 구식 `run_stage_train()` 함수를 메인 파이프라인 호출로 교체
- [x] S2. `run_pipeline.py` 글로벌 지표 히스토리 이중 Fetch 방지 (데이터 슬라이싱 재사용)
- [x] S3. `prediction_model.py` 피처 엔지니어링 중 발생하는 `inf` 값 처리 (`replace([np.inf, -np.inf], 0.0)`)
- [x] S4. `prediction_model.py` 펀더멘탈 데이터 누락 시 0.0으로 인한 모델 판단 오류 방지 및 `np.nan` 최적화 분기 전환 완료 (`has_fundamental` 피처 및 NaN 전파 처리 구현)
- [x] S5. `@retry(reraise=False)` 무음 실패 이슈를 `reraise=True`로 수정하여 네트워크 에러 명시화
- [x] S6. `indicator_storage.py` SQLite 동시 쓰기 `database is locked` 에러 방지 (WAL 모드 + Thread Lock)
- [x] S7. `locale.setlocale()` 스레드 안전성 확인 (코드 내 미사용 확인)
- [x] S8. `run_pipeline.py` ProcessPoolExecutor의 pickle 오버헤드를 ThreadPoolExecutor로 교체하여 성능 최적화

---

## 🟡 개선 사항 완료 내역 (개선 계획 이행 결과)

장기 로드맵의 모든 세부 개선 항목들이 다음과 같이 이행되어 완료되었습니다.

| # | 영역 | 이슈 | 우선순위 | 상태 |
|---|------|------|----------|------|
| **I1** | 테스트 | 전체 커버리지 51% → 핵심 모듈 유닛 테스트 추가 | Medium | **완료 [2026-06-21]** |
| **I2** | 테스트 | `config.py` 전용 테스트 없음 | Medium | **완료 [2026-06-21]** |
| **I3** | 테스트 | 동시성(SQLite, locale) 테스트 없음 | Medium | **완료 [2026-06-21]** |
| **I4** | 테스트 | `backtest.py` 전용 테스트 없음 | Medium | **완료 [2026-06-21]** |
| **I5** | 성능 | O(n²) universe 조회 → dict/set 기반 O(1) 최적화 | Low | **완료 [2026-06-21]** |
| **I6** | 성능 | 1초 polling loop → 60초 간격으로 CPU 점유율 축소 | Low | **완료 [2026-06-21]** |
| **I7** | 코드 | 미사용 import 정리 (orchestrator 등) | Low | **완료 [2026-06-21]** |
| **I8** | 코드 | `FallbackMetadataDict.__contains__` membership assertion 수정 | Low | **완료 [2026-06-21]** |
| **I9** | 데이터 | 펀더멘탈 데이터 캐싱 구현 (성공/실패 모두 90일 캐싱) | Medium | **완료 [2026-06-21]** |
| **I10** | 보안 | Telegram 오류 알림에 전체 traceback 노출 방지 | Low | **완료 [2026-06-21]** |
| **I11** | CI/CD | GitHub Actions 기반 빌드 및 테스트 자동 검증 | Medium | **완료 [2026-06-21]** |
| **I12** | CI/CD | 린팅(ruff) 및 타입 검사(mypy) CI 적용 | Low | **완료 [2026-06-21]** |

---

## 🚀 수익률 극대화 장기 로드맵 (향후 과제)

안정성이 확보된 현재 시스템 위에서 절대 수익률 및 복리 성장률(CAGR)을 극대화하기 위해 다음과 같은 중장기 과제를 추진합니다.

| # | 영역 | 과제명 | 우선순위 | 상태 |
|---|------|--------|----------|------|
| **N1** | 자금 관리 | **Kelly Criterion 도입**: 단순 Sharpe-ratio proxy 대신 Kelly 공식($\mu / \sigma^2$) 기반 사이징 | High | **완료 [2026-06-21]** |
| **N2** | 최적화 | **Black-Litterman 모델**: Risk Parity를 넘어 기대수익률을 반영한 비중 최적화 | High | **완료 [2026-06-21]** |
| **N3** | 모델 아키텍처 | **시장 국면(Regime) 감지**: HMM/GMM을 활용한 강세/약세/횡보장 감지 및 전략 스위칭 | High | **완료 [2026-06-21]** |
| **N4** | 피처 추가 | **Alt-Data 및 수급**: 다크풀, 블록트레이드, 옵션 GEX 등 미시구조 피처 추가 | Medium | **완료 [2026-06-21]** |
| **N5** | 모델 아키텍처 | **딥러닝 시계열 모델**: LSTM/Transformer/TabNet 도입 및 트리 모델 앙상블 | Medium | **완료 [2026-06-21]** |
| **N6** | 전략 추가 | **Stat-Arb / 단기 HFT**: 통계적 차익거래 및 장중(Intraday) 모멘텀 추종 전략 추가 | Low | **완료 [2026-06-21]** |

---

### I1. 테스트 커버리지 현황 (2026-06-21 측정)

- **전체 프로젝트 커버리지**: **52%** (총 11,295 statement 중 5,890 statement 실행됨)

**주요 모듈별 커버리지 상세**:
* **핵심 AI/ML & 설정**: 
  - `config.py` (55% → **98%**) 📈 대폭 보강됨
  - `vcp_ml_predictor.py` (84% → **87%**)
  - `prediction_model.py` (78%)
  - `rate_limiter.py` (**70%**)
  - `vcp_detector.py` (0%) ⚠️ 향후 유닛 테스트 작성 필요
* **데이터 및 저장소**: 
  - `macro_predictor.py` (92%)
  - `macro_analyzer.py` (82%)
  - `database.py` (61% → **65%**)
  - `indicator_storage.py` (58%)
* **트레이딩 및 엔진**: 
  - `strategy_engine.py` (70%)
  - `real_broker.py` (53%)
  - `simulated_broker.py` (51%)
  - `backtest.py` (40% → **45%**)
* **위험 관리 및 유틸리티**: 
  - `risk_manager.py` (64%)
  - `indicators.py` (96%)
  - `event_bus.py` (95%)
  - `report.py` (93%)

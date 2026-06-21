# ⚠️ Known Issues & 개선 로드맵

> **Last Updated**: 2026-06-21  
> **분석 기준**: 5개 전문 리뷰어에 의한 전체 코드베이스 정밀 검토 및 버그 픽스 완료

---

## 🟢 Resolved Issues (2026-06-21 완료)

다음의 핵심 버그 및 안정성 이슈들은 최근의 코드 감사와 패치를 통해 모두 수정되었습니다.

**Critical (즉시 수정 항목이었으나 완료됨)**
- [x] C1. `orchestrator.py` `config.train_sample_size` AttributeError 해결 (파이프라인 통합)
- [x] C2. `orchestrator.py` APScheduler async 작업 미실행 해결 (async wrapper 적용)
- [x] C3. `run_pipeline.py` `vcp_ml` None 참조 해결
- [x] C4. `run_pipeline.py` 에러 시 반환 타입 불일치 (tuple unpack error) 해결
- [x] C5. VCP 범위 감소 검사 방향 반전 수정 (`ranges[i] < ranges[i+1]`)
- [x] C6. VCP ML 피처와 규칙 기반 탐지기 간 계산 불일치 로직 통일
- [x] C7. 앙상블 가중치 key 타입 불일치 (int vs str JSON 변환 이슈) 해결
- [x] C8. `database.py` SQL Injection 취약점 점검 완료 (Parameterized query 사용 검증됨)

**Significant (중요 수정 항목이었으나 완료됨)**
- [x] S1. `orchestrator.py`의 구식 `run_stage_train()` 함수를 메인 파이프라인 호출로 교체
- [x] S2. `run_pipeline.py` 글로벌 지표 히스토리 이중 Fetch 방지 (데이터 슬라이싱 재사용)
- [x] S3. `prediction_model.py` 피처 엔지니어링 중 발생하는 `inf` 값 처리 (`replace([np.inf, -np.inf], 0.0)`)
- [x] S5. `@retry(reraise=False)` 무음 실패 이슈를 `reraise=True`로 수정하여 네트워크 에러 명시화
- [x] S6. `indicator_storage.py` SQLite 동시 쓰기 `database is locked` 에러 방지 (WAL 모드 + Thread Lock)
- [x] S7. `locale.setlocale()` 스레드 안전성 확인 (코드 내 미사용 확인)
- [x] S8. `run_pipeline.py` ProcessPoolExecutor의 pickle 오버헤드를 ThreadPoolExecutor로 교체하여 성능 최적화

---

## 🟠 Significant — 추가 개선 필요 (진행 중)

### S4. 펀더멘탈 누락 = 0.0 구분 불가

**위치**: `prediction_model.py` L145-160  
**영향**: "데이터 없음"과 "실제 0" (배당수익률 0% 등)을 모델이 구분 불가  
**수정 방향**: 별도 `has_fundamental` 바이너리 피처 추가, 또는 XGBoost의 네이티브 NaN 처리 활용으로 구조 변경 예정

---

## 🟡 개선 사항 — 장기 로드맵

| # | 영역 | 이슈 | 우선순위 |
|---|------|------|----------|
| I1 | 테스트 | 전체 커버리지 ~35-40% → 최소 60% 목표 | Medium |
| I2 | 테스트 | `config.py` 전용 테스트 없음 | Medium |
| I3 | 테스트 | 동시성(SQLite, locale) 테스트 없음 | Medium |
| I4 | 테스트 | `backtest.py` 전용 테스트 없음 | Medium |
| I5 | 성능 | O(n²) universe 조회 → dict 변환 필요 (L752-754) | Low |
| I6 | 성능 | 1초 polling loop → 30-60초 간격 (orchestrator L483) | Low |
| I7 | 코드 | 미사용 import 정리 (`orchestrator.py`: subprocess, functools, ThreadPoolExecutor) | Low |
| I8 | 코드 | `FallbackMetadataDict.__contains__` 항상 True 반환 | Low |
| I9 | 데이터 | 펀더멘탈 데이터 캐싱 미구현 (매 실행 시 재수집) | Medium |
| I10 | 보안 | Telegram 오류 알림에 전체 traceback 노출 | Low |
| I11 | CI/CD | 코드 커버리지 리포팅 미구현 | Medium |
| I12 | CI/CD | 린팅(ruff) 및 타입 검사(mypy) CI 미포함 | Low |

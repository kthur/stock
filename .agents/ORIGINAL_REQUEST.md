# Original User Request

## 2026-08-31T14:48:42Z

GitHub Actions 워크플로우(Data Seed, Training, Pipeline) 전 구간의 데이터 페치 및 모델 학습 무결성을 검증하고, 모든 전략의 처리 및 GitHub Pages 대시보드 표시 순서를 표준화하며, 관련 지표들을 단일 카드로 통합하는 대시보드 UX 카드 정밀 개편을 수행합니다.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. GitHub Actions Data Seeding & Model Training End-to-End Pipeline Integrity
- GitHub Actions 워크플로우(`.github/workflows/pipeline.yml`, `preseed.yml`, `training.yml`)에서 5대 시장(KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) 유니버스, 주가 시계열, 글로벌 거시 지표, 재무제표 데이터가 온전히 페치되고 캐시/시딩되는지 전수 검증.
- 회귀(Regression), Surge 분류기, VCP ML, LSTM 등 핵심 모델의 학습 및 추론 파이프라인이 결측치나 에러 없이 정상 구동되도록 보장.

### R2. 31대 전략 처리 및 GitHub Pages 대시보드 표준 순서 일원화
- 파이프라인 엔진(`run_pipeline.py`) 및 리포트 생성기(`generate_report.py`, `src/pipeline/reporter.py`)에서 31대 전략의 계산, 정규화, 앙상블, 출력 파일 저장 및 대시보드 렌더링 순서를 단일 표준 순서(Canonical Strategy Sequence)로 일관되게 고정.
- 출력 텍스트 파일(`pipeline_result.txt`, `surge_predictions.txt`, `vcp_ml_predictions.txt`, `ensemble_predictions.txt` 등)과 `gh-pages/index.html` 상의 전략 탭/섹션 순서가 1:1로 정확히 일치하도록 보장.

### R3. GitHub Pages 대시보드 카드 통합 및 UX 고도화 (Same-Card Metric Consolidation)
- `generate_report.py`의 HTML 대시보드 레이아웃을 개편하여, 상호 연관된 분산 지표들을 하나의 통합 카드(Single Unified Card)로 그룹화:
  1. **시장 환경 & 리스크 게이트 카드**: 2D 시장 레짐(6-Regime) + 거시 위기 감지(Crisis Detector) + VIX 기간구조/속도 게이트 통합.
  2. **전략 커버리지 & 결측 진단 카드**: 31대 전략 커버리지율 + 결측 사유 분포(Missingness Reasons) + 종목 진단 요약 통합.
  3. **포트폴리오 최적화 & 실행 OMS 카드**: HRP/Black-Litterman 자산배분 + EVT-CVaR 꼬리위험 + 실시간 슬리피지/마찰비용 피드백 통합.
- 카드 내 정보 밀도와 가독성을 높이고, 모바일/데스크톱 반응형 뷰에서 직관적인 데이터 시각화(배지, 프로그레스 바, 툴팁, 콤팩트 테이블) 제공.

## Acceptance Criteria

### Pipeline & GHA Verification
- [ ] GHA 워크플로우 및 파이프라인 로컬 시뮬레이션에서 5대 시장 데이터 페치 및 모델 학습이 에러 없이 완주.
- [ ] `verify_gha_artifacts.py` 및 파이프라인 산출물 검증 스크립트 실행 시 31대 전략 산출물 및 `index.html`이 100% Non-Zero 유효 데이터로 생성.

### Strategy Sequence Consistency
- [ ] 파이프라인 로깅, 텍스트 리포트, 대시보드 HTML의 전략 탭/테이블 목록이 동일한 표준 번호 및 순서(1~31번)로 일관되게 렌더링.

### Dashboard UX Consolidation
- [ ] `gh-pages/index.html`에서 연관 지표들이 단일 통합 카드로 정리되어 시각적 파편화가 해소되고 로딩 및 탭 전환이 매끄럽게 동작.
- [ ] `pytest tests/` 전수 실행 시 기존 테스트 스위트 100% 통과 유지.

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

## 2026-09-03T00:46:54Z

This is a focused review and improvement plan; keep it small and focused.
한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 37대 다변화 전략을 병행 운영하는 통합 주식 자동매매 시스템의 전 파이프라인(데이터 수집/캐시, 모델 학습/추론, 앙상블/정규화, 포트폴리오 최적화, OMS 주문 집행) 동작을 전수 점검하고, 잠재적 결함 및 수익률 개선 기회를 도출하여 구체적이고 실행 가능한 수정 계획안을 작성합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 전체 파이프라인 엔드투엔드 무결성 및 동작 감사
- `trading_system/run_pipeline.py`를 중심으로 데이터 레이어(SQLite WAL 캐시, 펀더멘탈/Filing Lag, 지표 수집), 37대 전략 엔진(`src/core/`, `src/ai/`), 횡단면 정규화(`score_normalizer.py`), 동적 앙상블 가중치(`ensemble_scorer.py`), 포트폴리오 최적화(`unified_portfolio_allocator.py`, `portfolio_optimizer.py`), 실행 OMS 8대 게이트(`oms_engine.py`)의 전 과정 데이터 흐름 및 로직 무결성을 점검합니다.
- 각 구성 요소 간 데이터 전달 시 발생할 수 있는 스케일 불일치, 결측치(NaN) 전파, 룩어헤드 편향, 또는 예외 누락 요소를 분석합니다.

### R2. 병목 구간, 결측(Missingness) 및 리스크 분석
- 37대 전략별 데이터 커버리지 및 최빈 결측 사유(`coverage_analyzer.py`), 레짐 전환 시 가중치 스무딩 안정성, 비선형 시장충격 및 거래비용 모델(STT, SEC fee, 스프레드, Gatheral 3/2승 충격)의 보정 적정성을 검토합니다.
- 시스템의 안정성을 뒷받침하는 단위/통합 테스트(1,900+ tests)의 사각지대나 취약한 가정을 식별합니다.

### R3. 실전 수익률 극대화 및 시스템 완결성 제고를 위한 단계별 수정 계획안 작성
- 분석 결과를 바탕으로 즉시 해결해야 할 버그, 로직 개선점, 성능 최적화 요소를 명확한 우선순위(Critical / High / Medium)로 분류합니다.
- 각 개선 항목별로 정량적 배경 근거, 변경 대상 파일 및 함수, 구체적인 수정 방법, 회귀 방지를 위한 검증 계획(테스트 케이스 설계 포함)을 명시한 종합 실행 계획안 문서를 작성합니다.

## Acceptance Criteria

### 코드 및 아키텍처 감사 품질
- [ ] 37대 전략 및 핵심 파이프라인 컴포넌트(데이터/앙상블/배분/OMS) 전반에 대해 구체적인 파일 경로와 코드 라인 번호를 인용한 문제점 및 개선점 도출 완료
- [ ] 정규화(Winsorized Z-Score), 직교화(ZCA Whitening), 앙상블(동적 가중치), 포트폴리오 최적화(BL+HERC+CVaR+RP), OMS(8대 게이트 및 슬리피지 피드백)의 유기적 결합 상태 검증 완료

### 수정 계획안의 완결성 및 실행성
- [ ] 작성된 계획안이 모든 제안 항목에 대해 [현황 및 문제점] -> [정량적/공학적 개선 방안] -> [수정 대상 파일] -> [검증 방안]의 4단계 구조를 갖출 것
- [ ] 기존 1,900+ 단위/통합 테스트의 하위 호환성을 완벽히 유지하면서 파이프라인 신뢰도 및 기대 수익률(IR/Sharpe)을 제고할 수 있는 현실적인 로드맵 제시
- [ ] 결과 계획안이 산출물 문서(`system_improvement_plan_v8.md` 등)로 완전하게 생성되어 검토 및 즉시 실행 가능할 것

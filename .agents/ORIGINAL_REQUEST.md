# Original User Request

## 2026-06-12T23:59:05Z

An automated pipeline orchestrator and scheduler daemon that triggers the daily data ingestion, periodic model retraining, post-market stock scoring, and sends operational status alerts via a Telegram bot.

Working directory: d:/Finance/code/stock
Integrity mode: demo

## Requirements

### R1. Central Orchestrator & CLI Trigger
Implement a central orchestrator component with a single command-line interface (CLI) entry point (e.g., `run.py` or similar) that can trigger individual pipeline stages manually or manage the background execution of the automated daemon. Supported CLI arguments must include:
- `start`: Start the scheduler daemon in the background.
- `stop`: Stop the running scheduler daemon.
- `status`: Display the current execution status (running/stopped, last run times, next scheduled runs).
- `run-now <stage>`: Force execution of a specific stage (ingest, train, score, dashboard) immediately.

### R2. Daemon Scheduler
Implement a background daemon scheduler (using `APScheduler` or a time-loop check) that coordinates:
- Daily Data Ingestion & Database Sync (prices + fundamentals).
- Daily Post-Market scoring & rankings calculation (post-market hour).
- Periodic XGBoost model retraining (e.g., weekly).
The daemon should handle concurrency safely, prevent overlapping runs of the same task, and log all scheduled actions.

### R3. Status Alerts & Telegram Integration
Integrate the system's Telegram bot wrapper to send automated notification alerts on:
- Successful pipeline stage executions (with summary stats like number of stocks scored, training time).
- Execution failures or exceptions raised in any pipeline stages (including stack trace summaries).
**Graceful Fallback**: If Telegram API credentials are not configured, the system must log warnings and output the status messages to local file logs and stdout without crashing or halting the pipeline.

### R4. Verification & Logging
Log all orchestrator and daemon actions into a dedicated rolling log file `orchestrator.log`. Maintain a SQLite metadata table `pipeline_runs` tracking each execution's stage, start time, end time, status (success/failure), and error message if any.

## Acceptance Criteria

### Execution & Control
- [ ] Running the CLI `start` command correctly boots the scheduler daemon.
- [ ] Running the CLI `status` command displays the correct operational status and task schedules.
- [ ] Running the CLI `stop` command safely terminates the background daemon.
- [ ] Individual stages can be triggered manually using `run-now`.

### Pipeline Orchestration & Integrity
- [ ] The scheduler daemon triggers daily ingest, train, and score tasks without memory leaks or overlapping conflicts.
- [ ] The database table `pipeline_runs` is correctly updated after each stage run with accurate timing and status.

### Alerting & Fallback
- [ ] Telegram alert notifications are successfully queued/sent on stage completions and errors.
- [ ] The pipeline runs and logs warnings normally when Telegram API keys are missing (no crashes).

### Verification
- [ ] A comprehensive test suite verifies daemon start/stop, manual execution, database logging, and fallback behaviors, with all tests passing successfully.

---
## Verification Plan

### Automated Tests
- Create a new test suite `tests/test_orchestrator.py` verifying:
  - CLI parser arguments (`start`, `stop`, `status`, `run-now`).
  - Correct execution tracking database records in `pipeline_runs`.
  - Daemon scheduler startup, task triggering, and shutdown.
  - Safe gracefully-handled fallback logs when Telegram keys are missing.
- Run the tests using:
  ```powershell
  python -m pytest trading_system/tests/test_orchestrator.py
  ```
  ```powershell
  python -m pytest
  ```

## Follow-up — 2026-06-13T04:46:05Z

Audit, supplement, and improve the stock trading system's risk management and portfolio construction modules from the perspective of an expert quantitative trader to enhance capital protection, optimize position sizing, and control drawdowns. Generate a comparative backtest report showing performance metrics before and after the improvements.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: development

## Requirements

### R1. Risk Management & Position Sizing Upgrades
- Audit and enhance `src/risk/risk_manager.py` and asset allocation mechanisms in `src/strategy/asset_allocation.py` or `src/core/strategy_engine.py`.
- Implement a robust dynamic position sizing mechanism (such as Risk Parity or Volatility Sizing using ATR/historical volatility) that adjusts target trade sizes based on asset-specific risk.
- Implement adaptive stop-loss and take-profit logic (such as ATR-based trailing stops or dynamic thresholds) instead of fixed static percentages.

### R2. Comparative Backtesting Framework
- Set up a comparative backtesting runner to evaluate the system's performance on S&P 500 and KRX stock universes under the baseline (original) vs. enhanced (improved) configurations.
- Track key quantitative metrics: Cumulative Return, Annualized Return, Sharpe Ratio, Maximum Drawdown (MDD), and Win Rate.

### R3. Expert Markdown Verification Report
- Generate a comprehensive markdown report named `expert_review_report.md` in the `reports/` folder.
- The report must include a detailed audit of existing risk rules, mathematical formulas for the new sizing and stop models, and a side-by-side comparative table of the backtest metrics (before vs. after).

## Acceptance Criteria

### Execution & Integration
- [ ] Running the backtest comparison script successfully executes both baseline and enhanced configurations without errors.
- [ ] Dynamic position sizing and adaptive trailing stop calculations are covered by new unit tests in `tests/test_risk_enhancements.py`.
- [ ] The full test suite runs and passes successfully.

### Quality & Performance
- [ ] The `reports/expert_review_report.md` file is successfully generated with detailed mathematical formulations and side-by-side comparative tables.
- [ ] The enhanced configuration demonstrates improved risk-adjusted metrics (lower MDD or higher Sharpe Ratio) on backtested historical samples.

## Follow-up — 2026-06-19T13:37:45Z

이 프로젝트는 통합 주식 자동매매 및 예측 시스템의 run_pipeline.py 실행 시 발생하는 런타임 오류 및 데이터 누수 관련 버그 5종을 수정하는 작업입니다.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. 예측 데이터 누수 해결 (P0)
- indicator_storage.py의 save_predictions 함수가 horizon 120, 200 데이터를 누락 없이 저장하도록 저장 루프의 horizon 목록을 [1, 5, 10, 20, 30, 60, 120, 200]으로 변경해야 합니다.

### R2. merge_fundamentals 안정성 보장 (P1)
- prediction_model.py의 merge_fundamentals 함수에서 date_fund 컬럼 drop 시 KeyError가 나지 않도록 errors='ignore' 옵션을 추가해야 합니다.

### R3. run_pipeline.py의 VCP universe 맵 구성 수정 (P1)
- run_pipeline.py에서 universe.get() 대신 universe['symbol'] 등 컬럼에 직접 접근하여 안전하고 일관된 방식으로 VCP universe 맵을 구성해야 합니다.

### R4. pandas Deprecation Warning 해결 (P2)
- prediction_model.py에서 pandas 2.1+의 deprecated 매개변수인 fill_method=None를 제거하여 pct_change() 호출들을 수정해야 합니다.

### R5. StockPriceDB Thread-safety 보장 (P2)
- database.py of StockPriceDB._get_conn에서 커넥션 초기화 시 다중 스레드 환경에서 race condition이 발생하여 커넥션 누수가 생기지 않도록 thread-safe하게 락 안에서 초기화하도록 수정해야 합니다.

## Acceptance Criteria

### 기능 작동 검증
- .venv\Scripts\python -m pytest tests/ -v 명령어를 통한 모든 단위 테스트가 에러 없이 성공해야 합니다.
- run_pipeline.py가 에러 없이 정상적으로 추론 및 파이프라인 단계를 완료해야 합니다.
- DB 저장 후 120일, 200일 예측 값이 누락 없이 올바르게 캐시 및 저장되어야 합니다.

## Follow-up — 2026-06-20T05:23:20Z

이 프로젝트는 현재 구현된 주식 자동매매 시스템의 모델 예측 정확도(XGBoost 회귀, Surge 분류기, VCP ML 등)를 향상시키기 위해 피처 엔지니어링, 하이퍼파라미터 튜닝, 모델 구조 변경(LightGBM, CatBoost 도입 등)을 코드에 직접 반영하고 검증하여 실전 포지션에 적용할 수 있도록 개선하는 것을 목표로 합니다.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: demo

## Requirements

### R1. Feature Engineering & Alternative Models
- 새로운 피처(기술적 지표, 거시경제 지표 등)를 도입하여 특징 공간(Feature Space)을 확장합니다.
- XGBoost 단일 모델 외에 LightGBM, CatBoost 등의 대안 그래디언트 부스팅 모델을 도입하여 성능을 비교하고, 앙상블(Ensemble) 또는 최적의 단일 모델을 설정합니다. 기존 XGBoost 학습 및 예측 파이프라인의 호환성을 해치지 않아야 합니다.

### R2. Automated Hyperparameter Tuning
- Optuna 등을 활용한 자동화된 하이퍼파라미터 튜닝(Hyperparameter Optimization) 스크립트를 구현하여 최적의 파라미터를 탐색하고 저장하는 자동 튜닝 파이프라인을 추가합니다.

### R3. API & Data Integration Stability
- 외부 금융 데이터 API나 지표를 연동할 경우, 과도한 API 호출 제한이나 요금 발생을 예방하도록 비동기 호출 제어 및 적절한 재시도(Retry with rate-limiting) 장치를 갖추어야 합니다.

## Acceptance Criteria

### Model Performance & Code Verification
- [ ] 최소 1개 이상의 새로운 모델(LightGBM/CatBoost) 혹은 신규 피처 조합이 파이프라인에 통합되어 있어야 합니다.
- [ ] Optuna 등을 통한 자동 하이퍼파라미터 튜닝 스크립트가 작성되어 있고 정상적으로 구동되어야 합니다.
- [ ] 과거 검증용 데이터셋(Historical Validation Set)을 기준으로 새롭게 학습된 앙상블/개선 모델이 기존 기준 모델(Baseline)보다 평가지표(회귀의 경우 MSE 감소, 분류의 경우 AUC 향상) 측면에서 유의미한 성능 향상을 증명해야 합니다.
- [ ] 기존 및 추가된 전체 테스트 케이스(`pytest tests/`)가 모두 성공적으로 통과되어야 합니다.

## Follow-up — 2026-07-11T00:24:44+09:00

한국·미국 주식 자동매매 예측 시스템(3,379개 종목, 5개 전략) 전체 코드베이스를 전문가 관점에서 정밀 검토하고, 개선 가능한 영역을 우선순위별로 정리한 종합 보고서를 작성한다. 보고서는 경영진 요약과 기술 상세를 모두 포함한다.

Working directory: d:/Finance/code/stock
Integrity mode: development

---

## Requirements

### R1. 5개 핵심 영역 심층 분석

아래 5개 영역 각각을 실제 코드를 읽어 파악하고 개선 기회를 도출한다:

| 영역 | 검토 대상 파일 | 주요 관심사 |
|------|--------------|------------|
| ① ML 모델 품질 | `src/ai/prediction_model.py`, `src/ai/vcp_detector.py`, `src/ai/vcp_ml_predictor.py` | feature 설계, 데이터 누수 여부, 앙상블 전략, 학습 데이터 품질 |
| ② 파이프라인 성능 | `trading_system/run_pipeline.py`, `src/data_layer/` | 병목 지점, 중복 계산, ThreadPoolExecutor 활용도, 캐시 효율 |
| ③ CI/CD & 인프라 | `.github/workflows/pipeline.yml`, `.github/workflows/training.yml` | GitHub Actions 안정성, 캐시 전략, 에러 복구 메커니즘 |
| ④ 코드 품질 | 전체 `src/` + `trading_system/` | 중복 코드, 타입 힌팅, 테스트 커버리지, 복잡도 |
| ⑤ 운영·모니터링 | `trading_system/generate_report.py`, pipeline 출력 | Telegram 알림, 장애 감지, GitHub Pages 대시보드 UX |

### R2. 우선순위 분류 및 액션 아이템

발견된 모든 문제/개선 기회에 대해:
- **P0(즉시)**: 데이터 누수·버그·장애 위험 → 즉시 수정 필요
- **P1(단기)**: 정확도·성능·안정성 개선 → 1~2주 내
- **P2(중기)**: 코드 품질·테스트·모니터링 → 1~2달 내
- **P3(장기)**: 아키텍처 개선·확장성 → 로드맵 수준

각 항목에 **예상 효과**와 **구현 난이도**(Easy/Medium/Hard) 반드시 포함.

### R3. 주요 발견사항 Before/After 코드 예시

가장 임팩트 큰 개선점 **상위 5개**에 대해:
- 현재 코드 snippet (파일명·라인 포함)
- 개선 후 코드 또는 설계 변경안
- 기대 효과 정량화 (예: "학습 시간 30% 단축", "추론 정확도 +2%p")

### R4. 보고서 구조

`reports/improvement_report.md`에 다음 구조로 저장:

```
1. 경영진 요약 (Executive Summary) — 1페이지 분량
   - 시스템 현황 평가 (5점 척도)
   - 최우선 개선 3가지
   - 예상 ROI

2. 영역별 상세 분석 (5개 섹션)
   - 현재 상태 평가
   - 발견된 문제/개선 기회 (코드 인용)
   - 개선 권고사항

3. 종합 우선순위 표
   | 항목 | 영역 | 우선순위 | 난이도 | 예상 효과 |
   
4. Before/After 상위 5개 (코드 예시 포함)

5. 실행 로드맵 (주차별)
```

---

## Acceptance Criteria

### 분석 완성도
- [ ] 5개 영역 각각에 최소 3개 이상의 구체적 개선점 (총 15개 이상)
- [ ] 모든 개선점에 근거 코드(파일명·라인) 인용
- [ ] P0~P3 우선순위 + 예상 효과 + 난이도 누락 없음

### Before/After 예시
- [ ] 상위 5개에 대해 실제 코드 기반 Before/After 제시
- [ ] 추상적 설명이 아닌 실제 코드 snippet

### Pipeline Orchestration & Integrity
- [ ] The scheduler daemon triggers daily ingest, train, and score tasks without memory leaks or overlapping conflicts.
- [ ] The database table `pipeline_runs` is correctly updated after each stage run with accurate timing and status.

### Alerting & Fallback
- [ ] Telegram alert notifications are successfully queued/sent on stage completions and errors.
- [ ] The pipeline runs and logs warnings normally when Telegram API keys are missing (no crashes).

### Verification
- [ ] A comprehensive test suite verifies daemon start/stop, manual execution, database logging, and fallback behaviors, with all tests passing successfully.

---
## Verification Plan

### Automated Tests
- Create a new test suite `tests/test_orchestrator.py` verifying:
  - CLI parser arguments (`start`, `stop`, `status`, `run-now`).
  - Correct execution tracking database records in `pipeline_runs`.
  - Daemon scheduler startup, task triggering, and shutdown.
  - Safe gracefully-handled fallback logs when Telegram keys are missing.
- Run the tests using:
  ```powershell
  python -m pytest trading_system/tests/test_orchestrator.py
  ```
  ```powershell
  python -m pytest
  ```

## Follow-up — 2026-06-13T04:46:05Z

Audit, supplement, and improve the stock trading system's risk management and portfolio construction modules from the perspective of an expert quantitative trader to enhance capital protection, optimize position sizing, and control drawdowns. Generate a comparative backtest report showing performance metrics before and after the improvements.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: development

## Requirements

### R1. Risk Management & Position Sizing Upgrades
- Audit and enhance `src/risk/risk_manager.py` and asset allocation mechanisms in `src/strategy/asset_allocation.py` or `src/core/strategy_engine.py`.
- Implement a robust dynamic position sizing mechanism (such as Risk Parity or Volatility Sizing using ATR/historical volatility) that adjusts target trade sizes based on asset-specific risk.
- Implement adaptive stop-loss and take-profit logic (such as ATR-based trailing stops or dynamic thresholds) instead of fixed static percentages.

### R2. Comparative Backtesting Framework
- Set up a comparative backtesting runner to evaluate the system's performance on S&P 500 and KRX stock universes under the baseline (original) vs. enhanced (improved) configurations.
- Track key quantitative metrics: Cumulative Return, Annualized Return, Sharpe Ratio, Maximum Drawdown (MDD), and Win Rate.

### R3. Expert Markdown Verification Report
- Generate a comprehensive markdown report named `expert_review_report.md` in the `reports/` folder.
- The report must include a detailed audit of existing risk rules, mathematical formulas for the new sizing and stop models, and a side-by-side comparative table of the backtest metrics (before vs. after).

## Acceptance Criteria

### Execution & Integration
- [ ] Running the backtest comparison script successfully executes both baseline and enhanced configurations without errors.
- [ ] Dynamic position sizing and adaptive trailing stop calculations are covered by new unit tests in `tests/test_risk_enhancements.py`.
- [ ] The full test suite runs and passes successfully.

### Quality & Performance
- [ ] The `reports/expert_review_report.md` file is successfully generated with detailed mathematical formulations and side-by-side comparative tables.
- [ ] The enhanced configuration demonstrates improved risk-adjusted metrics (lower MDD or higher Sharpe Ratio) on backtested historical samples.

## Follow-up — 2026-06-19T13:37:45Z

이 프로젝트는 통합 주식 자동매매 및 예측 시스템의 run_pipeline.py 실행 시 발생하는 런타임 오류 및 데이터 누수 관련 버그 5종을 수정하는 작업입니다.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. 예측 데이터 누수 해결 (P0)
- indicator_storage.py의 save_predictions 함수가 horizon 120, 200 데이터를 누락 없이 저장하도록 저장 루프의 horizon 목록을 [1, 5, 10, 20, 30, 60, 120, 200]으로 변경해야 합니다.

### R2. merge_fundamentals 안정성 보장 (P1)
- prediction_model.py의 merge_fundamentals 함수에서 date_fund 컬럼 drop 시 KeyError가 나지 않도록 errors='ignore' 옵션을 추가해야 합니다.

### R3. run_pipeline.py의 VCP universe 맵 구성 수정 (P1)
- run_pipeline.py에서 universe.get() 대신 universe['symbol'] 등 컬럼에 직접 접근하여 안전하고 일관된 방식으로 VCP universe 맵을 구성해야 합니다.

### R4. pandas Deprecation Warning 해결 (P2)
- prediction_model.py에서 pandas 2.1+의 deprecated 매개변수인 fill_method=None를 제거하여 pct_change() 호출들을 수정해야 합니다.

### R5. StockPriceDB Thread-safety 보장 (P2)
- database.py of StockPriceDB._get_conn에서 커넥션 초기화 시 다중 스레드 환경에서 race condition이 발생하여 커넥션 누수가 생기지 않도록 thread-safe하게 락 안에서 초기화하도록 수정해야 합니다.

## Acceptance Criteria

### 기능 작동 검증
- .venv\Scripts\python -m pytest tests/ -v 명령어를 통한 모든 단위 테스트가 에러 없이 성공해야 합니다.
- run_pipeline.py가 에러 없이 정상적으로 추론 및 파이프라인 단계를 완료해야 합니다.
- DB 저장 후 120일, 200일 예측 값이 누락 없이 올바르게 캐시 및 저장되어야 합니다.

## Follow-up — 2026-06-20T05:23:20Z

이 프로젝트는 현재 구현된 주식 자동매매 시스템의 모델 예측 정확도(XGBoost 회귀, Surge 분류기, VCP ML 등)를 향상시키기 위해 피처 엔지니어링, 하이퍼파라미터 튜닝, 모델 구조 변경(LightGBM, CatBoost 도입 등)을 코드에 직접 반영하고 검증하여 실전 포지션에 적용할 수 있도록 개선하는 것을 목표로 합니다.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: demo

## Requirements

### R1. Feature Engineering & Alternative Models
- 새로운 피처(기술적 지표, 거시경제 지표 등)를 도입하여 특징 공간(Feature Space)을 확장합니다.
- XGBoost 단일 모델 외에 LightGBM, CatBoost 등의 대안 그래디언트 부스팅 모델을 도입하여 성능을 비교하고, 앙상블(Ensemble) 또는 최적의 단일 모델을 설정합니다. 기존 XGBoost 학습 및 예측 파이프라인의 호환성을 해치지 않아야 합니다.

### R2. Automated Hyperparameter Tuning
- Optuna 등을 활용한 자동화된 하이퍼파라미터 튜닝(Hyperparameter Optimization) 스크립트를 구현하여 최적의 파라미터를 탐색하고 저장하는 자동 튜닝 파이프라인을 추가합니다.

### R3. API & Data Integration Stability
- 외부 금융 데이터 API나 지표를 연동할 경우, 과도한 API 호출 제한이나 요금 발생을 예방하도록 비동기 호출 제어 및 적절한 재시도(Retry with rate-limiting) 장치를 갖추어야 합니다.

## Acceptance Criteria

### Model Performance & Code Verification
- [ ] 최소 1개 이상의 새로운 모델(LightGBM/CatBoost) 혹은 신규 피처 조합이 파이프라인에 통합되어 있어야 합니다.
- [ ] Optuna 등을 통한 자동 하이퍼파라미터 튜닝 스크립트가 작성되어 있고 정상적으로 구동되어야 합니다.
- [ ] 과거 검증용 데이터셋(Historical Validation Set)을 기준으로 새롭게 학습된 앙상블/개선 모델이 기존 기준 모델(Baseline)보다 평가지표(회귀의 경우 MSE 감소, 분류의 경우 AUC 향상) 측면에서 유의미한 성능 향상을 증명해야 합니다.
- [ ] 기존 및 추가된 전체 테스트 케이스(`pytest tests/`)가 모두 성공적으로 통과되어야 합니다.

## Follow-up — 2026-07-11T00:24:44+09:00

한국·미국 주식 자동매매 예측 시스템(3,379개 종목, 5개 전략) 전체 코드베이스를 전문가 관점에서 정밀 검토하고, 개선 가능한 영역을 우선순위별로 정리한 종합 보고서를 작성한다. 보고서는 경영진 요약과 기술 상세를 모두 포함한다.

Working directory: d:/Finance/code/stock
Integrity mode: development

---

## Requirements

### R1. 5개 핵심 영역 심층 분석

아래 5개 영역 각각을 실제 코드를 읽어 파악하고 개선 기회를 도출한다:

| 영역 | 검토 대상 파일 | 주요 관심사 |
|------|--------------|------------|
| ① ML 모델 품질 | `src/ai/prediction_model.py`, `src/ai/vcp_detector.py`, `src/ai/vcp_ml_predictor.py` | feature 설계, 데이터 누수 여부, 앙상블 전략, 학습 데이터 품질 |
| ② 파이프라인 성능 | `trading_system/run_pipeline.py`, `src/data_layer/` | 병목 지점, 중복 계산, ThreadPoolExecutor 활용도, 캐시 효율 |
| ③ CI/CD & 인프라 | `.github/workflows/pipeline.yml`, `.github/workflows/training.yml` | GitHub Actions 안정성, 캐시 전략, 에러 복구 메커니즘 |
| ④ 코드 품질 | 전체 `src/` + `trading_system/` | 중복 코드, 타입 힌팅, 테스트 커버리지, 복잡도 |
| ⑤ 운영·모니터링 | `trading_system/generate_report.py`, pipeline 출력 | Telegram 알림, 장애 감지, GitHub Pages 대시보드 UX |

### R2. 우선순위 분류 및 액션 아이템

발견된 모든 문제/개선 기회에 대해:
- **P0(즉시)**: 데이터 누수·버그·장애 위험 → 즉시 수정 필요
- **P1(단기)**: 정확도·성능·안정성 개선 → 1~2주 내
- **P2(중기)**: 코드 품질·테스트·모니터링 → 1~2달 내
- **P3(장기)**: 아키텍처 개선·확장성 → 로드맵 수준

각 항목에 **예상 효과**와 **구현 난이도**(Easy/Medium/Hard) 반드시 포함.

### R3. 주요 발견사항 Before/After 코드 예시

가장 임팩트 큰 개선점 **상위 5개**에 대해:
- 현재 코드 snippet (파일명·라인 포함)
- 개선 후 코드 또는 설계 변경안
- 기대 효과 정량화 (예: "학습 시간 30% 단축", "추론 정확도 +2%p")

### R4. 보고서 구조

`reports/improvement_report.md`에 다음 구조로 저장:

```
1. 경영진 요약 (Executive Summary) — 1페이지 분량
   - 시스템 현황 평가 (5점 척도)
   - 최우선 개선 3가지
   - 예상 ROI

2. 영역별 상세 분석 (5개 섹션)
   - 현재 상태 평가
   - 발견된 문제/개선 기회 (코드 인용)
   - 개선 권고사항

3. 종합 우선순위 표
   | 항목 | 영역 | 우선순위 | 난이도 | 예상 효과 |
   
4. Before/After 상위 5개 (코드 예시 포함)

5. 실행 로드맵 (주차별)
```

---

## Acceptance Criteria

### 분석 완성도
- [ ] 5개 영역 각각에 최소 3개 이상의 구체적 개선점 (총 15개 이상)
- [ ] 모든 개선점에 근거 코드(파일명·라인) 인용
- [ ] P0~P3 우선순위 + 예상 효과 + 난이도 누락 없음

### Before/After 예시
- [ ] 상위 5개에 대해 실제 코드 기반 Before/After 제시
- [ ] 추상적 설명이 아닌 실제 코드 snippet

### 보고서 형식
- [ ] 경영진 요약(Executive Summary) 포함
- [ ] 종합 우선순위 표 (전체 발견사항 한눈에)
- [ ] 실행 로드맵 포함
- [ ] `reports/improvement_report.md` 파일로 저장
- [ ] 총 길이: 최소 4,000자 이상, 한국어 작성

## Follow-up — 2026-07-12T15:18:46Z

# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval
> Goal: Diagnose and fix all 4 strategy output quality bugs in the stock prediction pipeline

각 전략별 예측 출력에 심각한 품질 문제가 있습니다. Surge 분류기는 거의 모든 KRX 종목에서 0.0%를 출력하고, Lead-Lag는 KRX 마켓 예측이 아예 없으며, VCP ML 출력은 완전히 비어 있습니다. 이 버그들을 진단·수정하여 각 전략이 시장별 20개 이상의 유효한 데이터를 출력하도록 만드는 것이 목표입니다.

Working directory: D:\Finance\code\stock

---

## 확인된 주요 버그

### Bug 1: Surge 분류기 — 0.0% 확률 출력
**파일**: `trading_system/src/ai/prediction_model.py`

`_predict_surge()` (L1936)에서 surge_models, surge_lgb_models, surge_cat_models 가운데 하나라도 로드된 모델이 없으면 해당 시장/horizon 조합 전체를 0.0으로 기록합니다. INFERENCE_TARGET이 특정 마켓으로 한정되거나 GitHub Actions of 병렬 분산 학습에서 모델 파일이 다른 job에서 저장되었을 경우, load_surge_models()가 모델을 못 찾아 모든 예측이 0이 됩니다.

### Bug 2: Lead-Lag — KRX 마켓 예측 없음
**파일**: `trading_system/src/ai/prediction_model.py`

compute_lead_lag() (L2074)의 리더 선정 기준이 전체 학습 데이터 중 market_cap 상위 50개입니다. 결과적으로 리더가 대부분 SP500 대형주여서 predict_lead_lag()에서 KRX 종목의 lead_lag_score가 실질적으로 0에 가깝습니다. 현재 lead_lag_predictions.txt에서 SP500 Top20만 존재하고 KOSPI/KOSDAQ/KONEX는 완전히 비어 있습니다.

### Bug 3: VCP ML — 완전히 빈 출력
**파일**: `trading_system/src/ai/vcp_ml_predictor.py`

predict() (L487): if not self.models: return pd.DataFrame(). 즉 학습 후 저장된 vcp_surge_*.json 모델 파일이 없거나 load_models()가 실패하면 바로 빈 결과 반환. GHA에서 분산 학습 후 merge 단계에서 vcp_ml 인스턴스가 모델을 찾지 못하는 것으로 추정됩니다.

### Bug 4: Ensemble — Surge/Lead-Lag/VCP 모두 0% (KRX)
Bug 1~3의 결과로 ensemble_predictions.txt의 KRX 종목들은 Reg만 비영값이고 Surge=0%, L-L=0%, VCP=0%. SP500만 정상값 출력.

---

## Requirements

### R1. Surge 분류기 모델 로드 문제 진단 및 수정
GHA 분산 파이프라인 환경에서 surge 모델이 정상적으로 저장·로드되는지 확인하십시오. 모델이 없을 경우 명시적 경고와 함께 가능한 fallback을 적용하십시오. 최종적으로 각 시장(KOSPI, KOSDAQ, KONEX, SP500) x horizon(1/3/5/20d) 조합에서 유효한 Surge 확률 값(> 0%)이 나오는 종목이 20개 이상이어야 합니다.

### R2. Lead-Lag KRX 마켓 예측 복원
compute_lead_lag()에서 시장별(KOSPI/KOSDAQ/SP500)로 각각 상위 N개씩 리더를 선정하여 KRX 종목들도 충분히 follower로 탐지되도록 수정하십시오. predict_lead_lag()도 수정하여 KOSPI, KOSDAQ, KONEX Top 20 결과가 lead_lag_predictions.txt에 포함되어야 합니다.

### R3. VCP ML 모델 저장/로드 경로 문제 수정
GHA 분산 환경에서 vcp_surge_*.json 모델이 정상적으로 저장되고 merge/deploy 단계에서 로드되는지 확인하십시오. vcp_ml_predictions.txt에 각 시장별 Top 10 이상의 유효한 VCP ML 예측이 포함되어야 합니다.

### R4. 출력 파일 보증 — 빈 데이터 방지
각 전략 출력 파일에 데이터가 없는 경우에도 "데이터 없음" 메시지를 명시적으로 기록하여 파일이 헤더만 있거나 비어있는 상태를 방지하십시오.

---

## Acceptance Criteria

### 전략별 출력 품질
- [ ] surge_predictions.txt: KOSPI/KOSDAQ/KONEX/SP500 각 시장 x 4 horizons(1/3/5/20d) 조합에서 최소 20개 종목이 > 0.0% 확률을 가져야 함
- [ ] lead_lag_predictions.txt: KOSPI Top 20, KOSDAQ Top 20, KONEX Top 20, SP500 Top 20 섹션이 모두 존재하며 비어있지 않아야 함
- [ ] vcp_ml_predictions.txt: KOSPI/KOSDAQ/KONEX/SP500 각 시장 x 4 horizons에서 Top 10 이상 유효 예측 포함
- [ ] ensemble_predictions.txt: 모든 4개 마켓에서 Surge%, L-L%, VCP% 값이 0이 아닌 종목이 최소 5개 이상

### 코드 품질
- [ ] 수정 후 ruff check 및 mypy --ignore-missing-imports 오류 없음
- [ ] 기존 pytest 테스트 통과: .venv\Scripts\pytest tests\ -v --tb=short

### 검증 스크립트
```python
import re
for fname in ['trading_system/result/surge_predictions.txt',
              'trading_system/result/lead_lag_predictions.txt',
              'trading_system/result/vcp_ml_predictions.txt']:
    content = open(fname, encoding='utf-8').read()
    nonzero = len(re.findall(r': [1-9]\d*\.\d+%', content))
    print(f'{fname}: {nonzero} non-zero entries')
```

## Key Files

| 파일 | 역할 |
|------|------|
| trading_system/run_pipeline.py | 파이프라인 오케스트레이터 |
| trading_system/src/ai/prediction_model.py | Surge 분류기, Lead-Lag 학습/예측 |
| trading_system/src/ai/vcp_ml_predictor.py | VCP ML 학습/예측/저장/로드 |
| trading_system/src/ai/ensemble_scorer.py | 앙상블 점수 계산 |
| .github/workflows/pipeline.yml | GHA 파이프라인 설정 |
| trading_system/merge_predictions.py | 분산 결과 병합 |

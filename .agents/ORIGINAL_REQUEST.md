# Original User Request

## 2026-07-21T18:27:38Z

Fix all root causes where `run_pipeline.py` execution results in empty ("데이터 없음"), `0.0%`, or `NaN` outputs across all 5 strategies (Regression, Surge, Lead-Lag, VCP pattern, VCP ML) and ensure robust data fetching, training, inference, and reporting.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. Comprehensive Strategy & Pipeline Audit
Audit and fix all root causes resulting in empty ("데이터 없음"), `0.0%`, or `NaN` predictions across all 5 strategies (Regression, Surge, Lead-Lag, VCP pattern, VCP ML) in `run_pipeline.py`, `prediction_model.py`, `vcp_detector.py`, `vcp_ml_predictor.py`, and related modules.

### R2. Data Ingestion & Cache Fallback Resiliency
Ensure historical price fetching, indicator history, and corporate fundamentals loading (including DB cache fallbacks and network retry logic) operate resiliently in all environments without producing empty DataFrames.

### R3. Reporting & Dashboard Assembly Integrity
Ensure `generate_report.py` and output text file formatters properly parse, format, and render valid, populated prediction tables without showing missing data blocks.

## Acceptance Criteria

### Verification & Robustness
- [ ] `run_pipeline.py` runs cleanly without verification warnings of "All expected returns in pipeline_result.txt are 0.0".
- [ ] Output files (`pipeline_result.txt`, `surge_predictions.txt`, `lead_lag_predictions.txt`, `vcp_patterns.txt`, `vcp_ml_predictions.txt`) contain valid non-zero predictions for active markets.
- [ ] `generate_report.py` produces `index.html` with zero empty table warnings (`데이터 없음`) for valid active market sections.
- [ ] Unit & integration tests pass cleanly (`python -m pytest trading_system/tests/`).

## 2026-07-25T01:16:15Z

통합 주식 자동매매 및 예측 시스템(KRX & SP500, 3,379개 종목)의 AI 예측 정밀도, 대시보드 시각화 UX, 및 KIS 실전 자동매매 리스크 관리를 종합적으로 고도화하는 전체 시스템 자율 개선 프로젝트입니다.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. AI 모델 예측 정밀도 & 하이퍼파라미터 오토튜닝 자동화
- 5개 전략(회귀, Surge, Lead-Lag, VCP, VCP ML)의 하이퍼파라미터를 Optuna 기반으로 자동 튜닝하고, 2D 레짐 및 롤링 백테스트 샤프지수에 기반한 동적 앙상블 가중치를 최적화하여 예측 정확도 극대화.

### R2. GitHub Pages 대시보드 시각화 & HRP 자산배분 UX 고도화
- gh-pages/index.html 리포트에 HRP(Hierarchical Risk Parity) 자산 배분 비중 그래프, 레짐별 성과 트렌드 및 종목별 네이버 금융/해외주식 모바일 하이퍼링크 뷰어 기능 고도화.

### R3. KIS 자동매매 주문 안전성 & ATR 트레일링 스탑 강화
- KIS 실전/모의 계좌 주문 실행 시 ATR(Average True Range) 기반 동적 트레일링 스탑과 포트폴리오 노출 한도 제어를 연동하여 자동매매 안정성 보장.

## Acceptance Criteria

### Verification & Automated Testing
- [ ] python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages 수행 시 모든 전략 및 대시보드가 ✅ PASSED 일 것.
- [ ] pytest trading_system/tests/ -v 수트 내의 모든 단위/통합 테스트(HRP, Triple Barrier, 2D 레짐 등)가 100% 통과할 것.
- [ ] 파이프라인 구동 시 NaN/Null 발생률 0% 및 빌드 에러 0건 달성.

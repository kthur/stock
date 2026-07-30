# Original User Request

## Initial Request — 2026-07-30T00:52:09+09:00

You are the Project Orchestrator for the Stock Trading System quantitative review.

Working directory: d:\Finance\code\stock\.agents\orchestrator
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md

Please create your workspace directory at `d:\Finance\code\stock\.agents\orchestrator`, create your `BRIEFING.md` and `plan.md`, and orchestrate subagent specialists (or perform analysis) to conduct a full-system financial expert & quantitative multi-agent review of the Stock Trading System (3,379 symbols, 17 multi-factor/multi-model strategies, 2D regime ensemble, risk/transaction cost models, and memory-optimized pipeline).

Specific Audit Requirements:
1. R1. Quant & Financial Engineering Validation of 17 Strategies in `src/ai/` and `src/core/` (Stat-Arb Cointegration, RIM Valuation, Options IV Skew, Strict Causal LSTM, Order Flow Imbalance, LATR, CARD, ARM, Surge, VCP, VCP ML, Lead-Lag, Regression, Sector Rotation, Event-Driven, MQ Factor, Short-Term Reversal).
2. R2. Ensemble Engine & 2D Regime Optimization Audit in `src/ai/ensemble_scorer.py` and `src/ai/optuna_tuner.py`.
3. R3. Data Pipeline, Missingness & Lookahead Bias Audit in `run_pipeline.py`, `src/analysis/coverage_analyzer.py`, `src/data_layer/earnings_data.py`, and `src/persistence/database.py`.
4. R4. Microstructure, Slippage & Risk Management Audit in `src/ai/ensemble_scorer.py` and `src/config.py`.
5. R5. Technical Architecture & Pipeline Performance Audit across Python memory downcasting, concurrency, DB writes, and race conditions for 3,379 symbols.

Deliverables required:
- Update `progress.md` continuously as milestones progress.
- Produce a comprehensive final audit report containing:
  - Comprehensive analysis covering all 17 strategies, 2D ensemble engine, data pipeline integrity, risk management, and system architecture.
  - Detailed vulnerability matrix identifying specific risks (lookahead bias, edge cases, execution bottlenecks, risk controls).
  - Prioritized, actionable improvement recommendations with clear impact scores.
- When all audit milestones are completed, report victory / project completion back to Sentinel.

## Follow-up — 2026-07-30T01:37:41+09:00

17대 다변화 전략 주식 자동매매 및 예측 시스템(3,379개 종목 대상)의 성능 최적화, 거래비용 정밀 모델링, 결측 처리 고도화 및 백테스트/앙상블 알고리즘 개선 작업을 수행합니다.

Working directory: D:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 데이터 결측 전략의 Dynamic Re-weighting 스코어링 개선
- Options IV Skew, DART 공시, ARM 등 일부 종목/시장에서 데이터가 결측되는 전략에 대해, 데이터가 유효한 전략들의 가중치 합이 1.0(100%)이 되도록 동적으로 가중치를 Rescale하는 Dynamic Re-weighting 알고리즘 구현 및 검증 (`src/ai/ensemble_scorer.py`).

### R2. 정밀 Order Book Market Impact 거래비용 모델링
- 종목별 유동성(거래대금, 시가총액, 변동성) 및 주문 규모 가설 기반의 Order Book Market Impact(시장 충격 비용 및 호가 갭) 산정 공식을 적용하여, 미시구조 거래비용 산정 알고리즘 강화 (`src/config.py`, `src/ai/ensemble_scorer.py`).

### R3. 전략 간 다중공선성(Multicollinearity) 억제 및 레짐 기반 동적 앙상블 최적화
- 17대 전략 간 신호 상관관계를 모니터링하고, 특정 장세(2D 레짐: 횡보장/추세장/고변동성)에 맞춰 중복 요인 노이즈를 제어하며 예측 수익률을 최적화하도록 Optuna 및 Regime Scorer 연동 강화.

## Acceptance Criteria

### 알고리즘 검증 및 테스트
- [ ] 데이터 결측 발생 시에도 Ensemble Score 가중치 합이 정상 동적 스케일링(Re-scale)되는지 기존 및 신규 unit test로 확인
- [ ] 정밀 Order Book Impact 모델 도입 후 거래비용 산정 기능의 정상 동작 검증 (pyTest 통과)
- [ ] 전체 파이프라인 및 백테스트 실행 시 에러 없이 17대 전략 앙상블 리포트(`ensemble_predictions.txt`) 정상 생성


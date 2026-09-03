# Execution Plan: 37-Strategy Trading System Integrity Audit & Improvement Plan (v8)

## 1. Objective & Scope
Perform an end-to-end audit of the 37-strategy multi-factor trading system across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000). Identify latent bugs, numerical instability, scale mismatches, lookahead bias, missingness handling, portfolio optimization friction, OMS execution gates, and test blindspots across 1,900+ tests. Deliver `system_improvement_plan_v8.md` structured with:
`[현황 및 문제점]` -> `[정량적/공학적 개선 방안]` -> `[수정 대상 파일 및 라인]` -> `[검증 방안]`.

## 2. Milestone Decomposition
- **Milestone 1: Multi-Track Deep Technical Audit (Exploration)**
  - Track A (Explorer 1): Data Layer & Strategies 1-19
    - Files: `trading_system/run_pipeline.py`, `src/data_layer/`, `src/persistence/`, `src/ai/prediction_model.py`, `src/ai/vcp_*.py`, `src/core/` (strategies 1-19: RIM, Event, MQ, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, Inst/Foreign, Supply Chain).
    - Focus: SQLite WAL locking, dynamic filing lag (KRX 45d / US 40d), point-in-time correctness, feature scaling, NaN propagation, lookahead bias, divide-by-zero risks.
  - Track B (Explorer 2): Strategies 20-37 & Dynamic Ensemble Scoring
    - Files: `src/core/` (strategies 20-37: FinBERT Sentiment, Factor Neutralized, Vol Target, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Darkpool, Tone Drift, Cross-Asset Spillover, Supply Chain GNN, Range Expansion Breakout, Dual Correction, Index Rebalance, Overnight Gap Reversal), `src/ai/score_normalizer.py`, `src/ai/factor_orthogonalizer.py`, `src/ai/factor_suppression.py`, `src/ai/ensemble_scorer.py`, `src/analysis/coverage_analyzer.py`.
    - Focus: 2D regime matrix weight normalization, missing strategy zero-weighting, percentile rank vs winsorized Gaussian CDF stability, ZCA whitening condition numbers, micro-cost deduction, multi-market scale compatibility.
  - Track C (Explorer 3): Risk Management, Portfolio Optimization, OMS Execution & Test Blindspots
    - Files: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/risk/risk_manager.py`, `src/analysis/portfolio_optimizer.py`, `src/execution/order_manager.py`, `src/execution/almgren_chriss.py`, `src/execution/slippage_feedback.py`, `src/execution/turnover_optimizer.py`, `tests/`.
    - Focus: BL+HERC+CVaR ensemble, Ledoit-Wolf shrinkage, Gatheral 3/2 power market impact, Leland no-trade bands, OMS 8 safety gates, slippage feedback parameter drift, test suite edge-case gaps across 1,900+ tests.

- **Milestone 2: Synthesis & Improvement Plan Drafting**
  - Worker compiles the 3 audit reports into `system_improvement_plan_v8.md`.
  - Structure per requirement:
    - Executive Summary & Audit Scorecard
    - Critical Priority Improvements (Immediate action required)
    - High Priority Improvements (Alpha & Execution enhancement)
    - Medium Priority Improvements (Architecture & Test hardening)
    - 4-Stage Structure for each item: [현황 및 문제점] -> [정량적/공학적 개선 방안] -> [수정 대상 파일] -> [검증 방안]
    - Quantitative roadmap preserving 100% backward compatibility of existing 1,900+ tests.

- **Milestone 3: Independent Review & Verification**
  - Reviewer 1: Technical correctness, mathematical rigor (BL, HERC, ZCA, Ledoit-Wolf, Gatheral 3/2, Leland), and file/line citation precision.
  - Reviewer 2: Test compatibility, regression avoidance, and operational safety (OMS gates, execution risks).

- **Milestone 4: Finalization & Delivery**
  - Final polish of `system_improvement_plan_v8.md`.
  - Notification to parent agent via `send_message`.

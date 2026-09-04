# Phase 4 Plan: Quantitative Trading System Enhancement

## Objective
Execute Phase 4 quantitative trading system enhancement across:
1. R1: 37-Strategy Dynamic Signal Quality & Top-Decile Alpha Spread Enhancement.
2. R2: 4-Model Portfolio Allocation & SOR/OBI Execution Friction Optimization.
3. R3: Benchmark Comparison Report Generation & Quantification across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
4. Full Test Suite Verification: 2,295+ tests 100% passing.

## Milestones & Work Breakdown
- **Survey Phase**:
  - Dispatch Explorers to investigate current Phase 3 benchmark reports (`reports/quant_benchmark_comparison_phase3.md`, `reports/quant_benchmark_comparison.md`), current implementations in `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`, `src/risk/unified_portfolio_allocator.py`, `src/execution/smart_order_router.py`, `src/core/fast_lob_engine.py`, and test status.
- **Milestone 1: Dynamic Signal Quality & Top-Decile Alpha Spread**:
  - Worker implementation: Enhance non-linear interactions, cross-sectional ranking preservation, regime-adaptive weighting, half-life delay filtering.
  - Review & Gate: Reviewer + Challenger.
- **Milestone 2: Portfolio Allocation & SOR/Execution Friction Optimization**:
  - Worker implementation: 4-model dynamic portfolio allocation fine-tuning, SOR darkpool/HFT order book imbalance (OBI) pegging execution refinement.
  - Review & Gate: Reviewer + Challenger.
- **Milestone 3: Benchmark Quantification & Report Generation**:
  - Generate Phase 4 comparison tables across 5 markets and update reports.
- **Milestone 4: Full Test Suite Verification & Audit**:
  - Run full pytest test suite across `tests/` verifying all 2,295+ tests pass with zero regressions.
  - Run Forensic Auditor to confirm clean implementation without dummy code or cheating.
- **Handoff & Sentinel Notification**:
  - Compile final handoff and report to sentinel via send_message.

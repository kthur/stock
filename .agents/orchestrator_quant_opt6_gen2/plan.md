# Execution Plan — Phase 6 Deep Quantitative Enhancements (Generation 2)

## Context & Objectives
As the Generation 2 Project Orchestrator, drive Phase 6 through completion:
1. Milestone 1 (M1): Evaluate Gate as PASS (Remediation confirmed by reviewer_m1_3).
2. Milestone 2 (M2): Implement and verify F43 (4-Model portfolio allocation & tail risk budgeting in `unified_portfolio_allocator.py`) and F44 (Level-3 micro-price pegging, Bivariate Hawkes toxicity, and darkpool anti-gaming in `fast_lob_engine.py`, `smart_order_router.py`, `oms_engine.py`).
3. Milestone 3 (M3): Implement `benchmark_phase6_quant_performance.py` and synchronize 5-market comparative benchmark reports.
4. Milestone 4 (M4): Full repository test suite execution (2,442+ tests) with zero defects and zero regressions.
5. Final synthesis, comprehensive handoff report, and completion report to Sentinel.

## Step-by-Step Milestones

### Step 1: Initialize Orchestrator Gen 2 Workspace [DONE]
- Create `DISPATCH.md`, `PROJECT.md`, `GATE_STATUS.md`, `plan.md`, `progress.md`, `BRIEFING.md`.
- Register background heartbeat cron.

### Step 2: Milestone 1 Gate Sign-off [DONE]
- Confirm Worker M1-2 branch order remediation in `trading_system/src/ai/ensemble_scorer.py`.
- Confirm Reviewer M1-3 APPROVE verdict and 48/48 test pass.
- Record Milestone 1 as PASS.

### Step 3: Milestone 2 Implementation (F43 & F44)
- **Worker Dispatch**:
  - Implement F43 in `trading_system/src/risk/unified_portfolio_allocator.py`:
    - `compute_downside_semi_volatility`
    - `compute_component_cvar_risk_contributions`
    - `compute_information_theoretic_blend_weights`
    - Softmax reliability blending
    - Downside Sortino conviction tilting
    - Euler Component CVaR risk budget cap
    - Quadratic Shannon entropy volatility scaling
    - Asymmetric Downside Leland buffer bands
  - Implement F44 in:
    - `trading_system/src/core/fast_lob_engine.py`: `estimate_queue_position`, L3 multi-tier depth decay micro-price, `BivariateHawkesIntensity`.
    - `trading_system/src/execution/smart_order_router.py`: Directional Hawkes toxicity modulation, dynamic anti-gaming `min_quantity`, logistic hazard dark fill probability, KRX Nextrade & US SMART DMA venue tags.
    - `trading_system/src/execution/oms_engine.py`: L3 micro-price & queue position aware peg pricing in `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
  - Author comprehensive test suite `tests/test_phase6_portfolio_execution.py` (covering all F43 & F44 properties and unit cases).
  - Execute test suites and verify 100% pass with 0 regressions.
- **Review & Verification**:
  - Dispatch Reviewers (Math, Code, Robustness).
  - Dispatch Challengers (Adversarial stress testing).
  - Dispatch Forensic Auditor (Zero hardcoding, zero facade, genuine logic verification).
  - Evaluate Milestone 2 Gate.

### Step 4: Milestone 3 (Quantitative Benchmark Performance Engine F45)
- Dispatch Worker to create `trading_system/scripts/benchmark_phase6_quant_performance.py`:
  - Run 15 institutional metrics across 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
  - Calculate F41-F44 quantitative attribution deltas vs Phase 5 baseline.
  - Generate and synchronize:
    - `reports/quant_benchmark_comparison_phase6.md`
    - `trading_system/result/quant_benchmark_comparison_phase6.md`
    - `reports/quant_benchmark_comparison.md`
- Verification & Forensic Integrity Audit.
- Evaluate Milestone 3 Gate.

### Step 5: Milestone 4 (Full Repository Regression Verification F46)
- Dispatch Worker / Test Runner to execute full test suite (`.venv\Scripts\pytest.exe tests/ -v`).
- Confirm zero regressions across 2,442+ tests.
- Evaluate Milestone 4 Gate.

### Step 6: Final Synthesis & Sentinel Report
- Author authoritative `handoff.md` in `.agents/orchestrator_quant_opt6_gen2/`.
- Send final completion message to Sentinel.

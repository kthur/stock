# Project Plan: Post-Market Stock Scoring, Ranking, and Backtest Dashboard

## Resuming Project State (2026-06-12)
The project is being resumed by a new Project Orchestrator instance. 
- **Milestone 1 (PyTorch & Config Fixes)** is verified and complete (audit verdict: CLEAN).
- **Milestone 2 (Post-Market Stock Scoring Backend)** has implementation files and tests in place, but needs verification and auditing to confirm if it is fully complete and compliant.
- **Milestone 3 (Dashboard Integration)** needs to be implemented.
- **Milestone 4 (E2E Testing Track)** needs to be designed and implemented.
- **Milestone 5 (E2E Verification & Audit)** needs to be run.

---

## Detailed Milestone Plans

### Milestone 1: PyTorch DLL & Config Fixes
- **Status**: DONE (Clean Audit)
- **Objective**: Resolve PyTorch WinError 1114 DLL load crash and the failing KIS mock config tests.
- **Verification**: Run `tests/phase6/unit/test_mock_trading.py` and confirm all pass.

### Milestone 2: Post-Market Stock Scoring Backend (R1)
- **Status**: IN_PROGRESS (Verification needed)
- **Objective**: Implement daily post-market scoring script using technical, AI, and sentiment scores, and store in SQLite table `post_market_rankings`.
- **Verification**: Run `tests/test_post_market_scoring.py` and run a trial execution of `scripts/post_market_scoring.py`.
- **Steps**:
  1. Spawn Explorer to verify if the scoring script and tests run successfully.
  2. If tests pass, spawn a Forensic Auditor to audit Milestone 2.
  3. If Audit is CLEAN, mark Milestone 2 as DONE. If not, spawn Worker to fix issues.

### Milestone 3: Web Dashboard UI Integration (R2 & R3)
- **Status**: PLANNED
- **Objective**: Add "Post-Market Rankings" tab (R2) and "Strategy Performance Analysis" section (R3).
- **Verification**: Web dashboard should render sortable DataTable of top 100 stocks and Strategy Performance section (yield, Sharpe, win rate, MDD, and Plotly equity curve).
- **Steps**:
  1. Spawn Explorer to analyze the dashboard codebase (`src/web/dashboard.py` and `run_dashboard.py`) and formulate implementation strategy.
  2. Spawn Worker to implement:
     - "Post-Market Rankings" tab showing rank, symbol, name, and scores.
     - "Strategy Performance Analysis" section running backtest and showing metrics + equity curve chart.
     - Ensure existing dashboard tabs and tests are not broken.
  3. Spawn Reviewer to inspect design and code.
  4. Spawn Challenger to perform stress testing on the callbacks.
  5. Spawn Forensic Auditor to verify compliance.

### Milestone 4: E2E Testing Track
- **Status**: PLANNED
- **Objective**: Create a comprehensive, requirement-driven, opaque-box E2E test suite in 4 tiers: Feature Coverage, Boundary/Edge Cases, Cross-Feature, and Real-World Workloads.
- **Verification**: Output `TEST_READY.md` summarizing the test cases.
- **Steps**:
  1. Spawn Explorer to design E2E test cases based on requirements.
  2. Spawn Worker to implement the test suite in `tests/` and verify they run successfully.

### Milestone 5: E2E Verification & Adversarial Hardening
- **Status**: PLANNED
- **Objective**: Run E2E tests, perform Challenger stress testing (Tier 5 adversarial hardening), and run final Forensic Audit.
- **Verification**: 100% test pass on final test suite, no gaps reported, and CLEAN audit verdict.
- **Steps**:
  1. Run the E2E test suite against the dashboard and scoring backend.
  2. Spawn Challenger to audit code coverage, find untested paths, and generate adversarial inputs.
  3. Spawn Worker to fix any bugs exposed by Challenger.
  4. Spawn Forensic Auditor for final project audit.

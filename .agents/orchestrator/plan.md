# Project Plan: Stock Trading System Deep Audit & Enhancement

## Objectives
1. Perform deep financial engineering audit of the Stock Trading System (18 strategies, 2D regime engine, HRP/Black-Litterman portfolio optimization, microstructure costs).
2. Perform software architecture and UI/UX responsiveness evaluation (Pipeline & GHA workflows, mobile 375/414px & desktop 1920px responsiveness, macro badges).
3. Produce `SYSTEM_IMPROVEMENT_REPORT.md` featuring quantitative equations, architecture diagrams, and concrete actionable code improvements.
4. Execute automated verification: 100% pass on pytest test suite (`.venv\Scripts\python.exe -m pytest tests/ -v`) and GHA artifact verifier across all 14 strategy panels on `gh-pages/index.html`.
5. Pass Forensic Audit gate with CLEAN verdict.

## Phased Plan

### Milestone 1: Deep Codebase & System Survey
- **Step 1.1**: Dispatch Explorer 1 (`teamwork_preview_explorer`) to audit Financial Engineering: 18 strategies (`src/ai/ensemble_scorer.py`, `src/ai/prediction_model.py`, `src/core/`), Portfolio Optimization (`src/strategy/`), Microstructure & Friction Costs (`src/config.py`).
- **Step 1.2**: Dispatch Explorer 2 (`teamwork_preview_explorer`) to audit Software Architecture & GHA Pipeline: `run_pipeline.py`, SQLite WAL concurrency (`src/persistence/database.py`, `src/data_layer/indicator_storage.py`), `.github/workflows/`, artifact aggregation resilience.
- **Step 1.3**: Dispatch Explorer 3 (`teamwork_preview_explorer`) to audit Dashboard UI/UX & GHA Artifacts: `gh-pages/index.html` (Mobile 375/414px & Desktop 1920px responsiveness, sticky headers, live macro badges) and `verify_gha_artifacts.py` / GHA verifier skill integration.

### Milestone 2: System Improvement Report Generation (`SYSTEM_IMPROVEMENT_REPORT.md`)
- **Step 2.1**: Aggregate M1 findings into unified technical requirements and blueprint.
- **Step 2.2**: Dispatch Worker 1 (`teamwork_preview_worker`) to draft `SYSTEM_IMPROVEMENT_REPORT.md` at `d:\Finance\code\stock\SYSTEM_IMPROVEMENT_REPORT.md` containing:
  - Section 1: 18-Strategy Multi-Factor Model Audit (return calibration, signal independence, isotonic calibration, coverage analysis)
  - Section 2: Portfolio Optimization Audit (HRP & Black-Litterman, covariance shrinkage, risk parity, sector caps, max position limits)
  - Section 3: Microstructure & Friction Costs (STT 0.18%, bid-ask spread models, Spiess-Kyung market impact equations for small-caps)
  - Section 4: Pipeline & GHA Workflow Resilience (automation order, weekend training vs daily split market inference, SQLite WAL concurrency, artifact aggregation)
  - Section 5: Dashboard UI/UX Responsiveness (Mobile 375/414px & Desktop 1920px layout evaluation, sticky headers, macro indicator badges)
  - Section 6: Actionable Code Improvements & Architecture Diagrams (Mermaid diagrams, formulas, code snippets)

### Milestone 3: Automated Test Suite & Artifact Verification
- **Step 3.1**: Dispatch Worker 2 (`teamwork_preview_worker`) to run the pytest suite (`.venv\Scripts\python.exe -m pytest tests/ -v`) and verify 100% pass rate.
- **Step 3.2**: Dispatch Worker 3 (`teamwork_preview_worker`) armed with GHA Artifact Verifier skill (`gha-artifact-verifier`) to execute verification across all 14 strategy panels on `gh-pages/index.html`.
- **Step 3.3**: Dispatch 2 Reviewers (`teamwork_preview_reviewer`) to independently review `SYSTEM_IMPROVEMENT_REPORT.md`, test outputs, and GHA artifact verification results.
- **Step 3.4**: Dispatch 2 Challengers (`teamwork_preview_challenger`) to adversarially challenge financial model accuracy, equations, pipeline edge cases, and UI responsiveness.
- **Step 3.5**: Dispatch Forensic Auditor (`teamwork_preview_auditor`) for integrity verification (zero hardcoding, zero fake tests, clean audit).

### Milestone 4: Final Synthesis & Handover
- **Step 4.1**: Check Gate Status: Pytest 100% pass, GHA artifact verifier 100% pass across all 14 strategy panels, Reviewers APPROVE, Auditor CLEAN.
- **Step 4.2**: Update `progress.md`, `PROJECT.md`, `BRIEFING.md`.
- **Step 4.3**: Report final completion to parent/Sentinel.

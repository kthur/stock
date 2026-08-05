# Project: Stock Trading System Deep Audit & Enhancement

## Architecture
- **Core Engine**: 18-Strategy Multi-Factor Model (`src/ai/ensemble_scorer.py`, `src/ai/prediction_model.py`, `src/core/`)
- **Portfolio Optimization**: Risk Parity, HRP & Black-Litterman (`src/strategy/`, `src/ai/ensemble_scorer.py`)
- **Microstructure & Costs**: STT (0.18%), bid-ask spreads, Spiess-Kyung market impact model (`src/config.py`, `src/ai/ensemble_scorer.py`)
- **Pipeline & Storage**: `run_pipeline.py`, SQLite WAL concurrency (`src/persistence/database.py`, `src/data_layer/indicator_storage.py`), GHA workflows (`.github/workflows/`)
- **Dashboard UI/UX**: `gh-pages/index.html` responsive layout (Mobile 375/414px & Desktop 1920px), sticky column headers, macro indicator badges (VIX, TNX, USDKRW, WTI, Gold)
- **Artifact Verification**: `verify_gha_artifacts.py` / GHA artifact verifier skill across 14 strategy panels

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 18-Strategy Multi-Factor Model Audit | Expected return calibration, signal independence, isotonic calibration, coverage analysis | M1, M2 | R1.1 |
| 2 | Portfolio Optimization Audit | HRP & Black-Litterman, covariance shrinkage, risk parity stability, sector caps, max position sizing | M1, M2 | R1.2 |
| 3 | Microstructure Friction Costs Audit | STT 0.18%, bid-ask spread models, Spiess-Kyung market impact for small-caps | M1, M2 | R1.3 |
| 4 | Pipeline & GHA Workflow Resilience | Automation order, weekend training vs daily split market inference, SQLite WAL concurrency, artifact aggregation | M1, M2 | R2.1 |
| 5 | Dashboard UI/UX Responsiveness | Mobile (375/414px) and Desktop (1920px) layout, sticky column headers, live macro indicator badges | M1, M2 | R2.2 |
| 6 | System Improvement Report Generation | Comprehensive `SYSTEM_IMPROVEMENT_REPORT.md` with quantitative equations, diagrams, and concrete actionable code improvements | M2 | R1, R2 |
| 7 | Pytest Test Suite Verification | Ensure 100% pass rate across core test suite (`.venv\Scripts\python.exe -m pytest tests/ -v`) | M3 | R3.1 |
| 8 | GHA Artifact Verifier Execution | Run artifact verifier across all 14 strategy panels on `gh-pages/index.html` ensuring non-zero data rendering | M3 | R3.2 |
| 9 | Forensic Audit & Verification Gate | Independent forensic audit for zero cheating/hardcoding and 100% authentic implementation | M3, M4 | Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Deep Codebase & System Survey | Map 18 strategies, portfolio optimization, microstructure costs, pipeline/GHA, UI/UX, and test suite | None | DONE |
| M2 | System Improvement Report Draft | Generate `SYSTEM_IMPROVEMENT_REPORT.md` with equations, architecture diagrams, and improvements | M1 | DONE |
| M3 | Test Suite & Artifact Verification | Run full pytest suite, execute GHA artifact verifier on gh-pages/index.html, review, challenge, and forensic audit | M2 | DONE |
| M4 | Final Synthesis & Handover | Validate all gate criteria, synthesize results, update briefings, and report completion | M3 | DONE |

## Code Layout
- `SYSTEM_IMPROVEMENT_REPORT.md` (root directory `d:\Finance\code\stock\SYSTEM_IMPROVEMENT_REPORT.md`)
- `.agents/orchestrator/` (metadata, plan, briefing, progress, handoff)
- `.agents/teamwork_preview_explorer_m1_1/` (Financial Engineering Audit report)
- `.agents/teamwork_preview_explorer_m1_2/` (Architecture & Pipeline Audit report)
- `.agents/teamwork_preview_explorer_m1_3/` (Dashboard UI/UX & Verifier Audit report)
- `.agents/worker_m2_1/` (Worker drafting SYSTEM_IMPROVEMENT_REPORT.md)
- `.agents/worker_m3_1/` (Worker executing Pytest suite & GHA Verifier)
- `.agents/worker_m3_remediation/` (Worker executing remediations & code enhancements)
- `.agents/reviewer_*` (review handoffs)
- `.agents/challenger_*` (adversarial stress testing handoffs)
- `.agents/auditor_*` (forensic audit report)

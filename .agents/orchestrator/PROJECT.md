# Project: Stock Trading System Comprehensive Codebase Audit

## Architecture
- `trading_system/run_pipeline.py`: Pipeline entry point and orchestration.
- `src/`: Deep logic directories containing AI predictions, technical indicators, database, and earnings fetching.
- `.github/workflows/`: CI/CD workflow configuration files.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Audit Initialization & Setup | Initialize metadata tracking files and timers. | None | DONE |
| 2 | Exploration & Codebase Inspection | Inspect `src/`, `trading_system/`, and `.github/workflows/` to identify 15+ improvement points. | M1 | DONE |
| 3 | Report Implementation | Generate `reports/improvement_report.md` in Korean (>= 4,000 chars) with executive summary, priority table, before/after snippets for top 5, and weekly roadmap. | M2 | DONE |
| 4 | Review and Quality Gate | Spawn Reviewer to verify report quality, correctness, and length. | M3 | DONE |
| 5 | Verification & Completion | Report completion of the task. | M4 | DONE |

## Interface Contracts
### reports/improvement_report.md
- **Language**: Korean.
- **Length**: >= 4,000 characters.
- **Contents**:
  - Executive Summary (Rating out of 5, top 3 priorities, expected ROI)
  - Master Priority Table (P0, P1, P2, P3 with Expected Impact, Implementation Difficulty)
  - At least 3 improvement points for each of the 5 areas: ML model quality, pipeline performance, CI/CD & infrastructure, code quality, operations/monitoring (total 15+ points).
  - Exact file path and line number range for each point.
  - Before/After code snippets for top 5 highest impact improvements with quantified expected gains.
  - Weekly execution roadmap.

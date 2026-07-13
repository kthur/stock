# Project Plan: Stock Trading and Prediction System Audit

## Mission
Perform a comprehensive professional audit of the entire stock trading and prediction system codebase at `d:/Finance/code/stock` and generate a detailed report at `reports/improvement_report.md` in Korean (at least 4,000 characters).

---

## Detailed Milestone Plans

### Milestone 1: Audit Initialization & Setup
- **Objective**: Initialize tracking files (`plan.md`, `progress.md`, `context.md`, `BRIEFING.md`) and launch the heartbeat cron.
- **Verification**: Ensure all status files are updated and the heartbeat timer is running.

### Milestone 2: Exploration & Codebase Inspection
- **Objective**: Inspect the code in `src/`, `trading_system/`, and `.github/workflows/`. Identify at least 3 concrete improvement points for each of the 5 areas (ML model quality, pipeline performance, CI/CD & infrastructure, code quality, operations/monitoring) with exact file names and line ranges.
- **Verification**: Spawn `teamwork_preview_explorer` to inspect code and generate a detailed audit analysis artifact.

### Milestone 3: Report Implementation
- **Objective**: Write the audit report `reports/improvement_report.md` in Korean.
- **Verification**: The report must contain:
  1. Executive Summary (Rating out of 5, top 3 priorities, expected ROI)
  2. 15+ concrete improvement points (3+ per area) with file names and line ranges.
  3. Master priority table (P0, P1, P2, P3, expected impact, difficulty).
  4. Before/After code snippets for top 5 highest impact improvements with quantified expected gains.
  5. Weekly execution roadmap.
  6. Must be written in Korean, saved at `reports/improvement_report.md`, and >= 4,000 characters long.
- **Action**: Spawn `teamwork_preview_worker` to write this report.

### Milestone 4: Review and Quality Gate
- **Objective**: Review the generated report for correctness, length (>= 4,000 characters), language (Korean), and coverage of all required sections.
- **Verification**: Spawn `teamwork_preview_reviewer` to check the document against instructions.

### Milestone 5: Verification & Completion
- **Objective**: Finalize and declare completion to the user and parent agent.
- **Verification**: Ensure `reports/improvement_report.md` is correctly saved and verified.

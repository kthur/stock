# Orchestration Plan — Quantitative Review of Stock Trading System

## Executive Summary
Audit of the 17-strategy quantitative stock trading system across 3,379 symbols (KOSPI/KOSDAQ/KONEX/SP500).

## Execution Milestones
1. **Phase 1: Environment & Codebase Mapping (Step 0)**
   - Setup project workspace, BRIEFING.md, PROJECT.md, plan.md, progress.md.
   - Start heartbeat timer.

2. **Phase 2: Milestone Execution via Specialized Explorers (Steps 1-5)**
   - **M1 (R1)**: Dispatch `teamwork_preview_explorer` (Worker-Quant-1) to audit all 17 strategies for mathematical soundness, theoretical validity, signal formulation, edge cases.
   - **M2 (R2)**: Dispatch `teamwork_preview_explorer` (Worker-Quant-2) to audit the 2D regime scoring matrix, Optuna hyperparameter optimization objective, search space, and decision rationales.
   - **M3 (R3)**: Dispatch `teamwork_preview_explorer` (Worker-Data-1) to audit data pipeline integrity, earnings announcement timing, lookahead bias in indicators/scaling, coverage analyzer missingness reporting.
   - **M4 (R4)**: Dispatch `teamwork_preview_explorer` (Worker-Risk-1) to audit market microstructure modeling, slippage, transaction costs (taxes, exchange fees, bid-ask spreads), liquidity filters, position limits, and tail risk controls.
   - **M5 (R5)**: Dispatch `teamwork_preview_explorer` (Worker-Perf-1) to audit Python memory downcasting, multithreading bottlenecks, SQLite database locks/concurrency, and execution scalability for 3,379 symbols.

3. **Phase 3: Synthesis & Final Deliverable (Step 6)**
   - Aggregate subagent findings into `d:\Finance\code\stock\.agents\orchestrator\audit_report.md`.
   - Formulate Vulnerability Matrix (Risk Severity, Exploitability/Impact, Module).
   - Formulate Actionable Recommendations with priority ratings.
   - Report Victory / Completion back to parent/user.

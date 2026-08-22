## 2026-08-22T06:06:04Z

<USER_REQUEST>
You are the Project Orchestrator for the stock trading system engineering task.
Your working directory is d:\Finance\code\stock\.agents\orchestrator_1\.
Project root is d:\Finance\code\stock.

Please read the authoritative request in d:\Finance\code\stock\ORIGINAL_REQUEST.md and AGENTS.md.

Mission:
Orchestrate the comprehensive resolution of all requirements R1, R2, R3, R4:
- R1: 31-Strategy Score Scale Normalization & Ensemble Distortion Resolution (Percentile Rank / Winsorized Z-Score normalization engine, dynamic zero-weighting of missing strategy signals and automatic re-normalization).
- R2: Data Pipeline Refinement (Dynamic market filing lag: KRX 45d, US 40d with real-time filing override; Market/sector/market-cap Stratified Sampling in prepare_training_data; Total elimination of fake BENCHMARK pairs in Stat-Arb).
- R3: System Stability, Timeout & Exception Handling (Remove global socket.setdefaulttimeout(5), implement adaptive timeouts and exponential backoff for yfinance/FRED/ECOS; Defend against NaN propagation in FallbackMetadataDict; VIX term structure & change-rate buffering in crisis detection).
- R4: Full Test Suite & Integrity Verification (Ensure 100% PASS on all 1,124+ tests in tests/ via .venv/Scripts/python.exe -m pytest tests/ -v without any regressions or lookahead bias).

Working instructions:
1. Initialize your working directory (d:\Finance\code\stock\.agents\orchestrator_1\) with plan.md, progress.md, and context.md.
2. Formulate a structured milestone plan, decomposing work across specialized worker subagents (e.g. explorer, implementers, reviewers).
3. Supervise implementation, enforce test-driven verification, and execute full pytest suite.
4. When all tasks and acceptance criteria are completely satisfied and verified, write handoff.md in your working directory and message the sentinel with your victory claim.
</USER_REQUEST>

# Orchestration Plan — System Readiness Audit

## Plan Overview

Execute a rigorous 4-Milestone Audit & Hardening cycle for the 18-Strategy Multi-Factor Automated Stock Trading System:

### Milestone 1: Financial Engineering & Quantitative Risk Audit (R1)
- **Explorer Phase**: Dispatch 3 Explorers in parallel to inspect all 18 strategies, 2D regime matrix, Isotonic Regression calibration, Gram-Schmidt orthogonalization, HRP portfolio allocation, filing lag (60d), lookahead/survivorship bias, microstructure transaction costs (STT, SEC, spread, market impact), empirical risk metrics (CVaR, EVT-VaR, Max Drawdown, Sharpe), and backtest assumptions.
- **Worker Phase**: Dispatch Worker to fix any identified quantitative issues, bias leaks, or backtest calculation discrepancies.
- **Reviewer & Challenger Phase**: Dispatch 2 Reviewers and 2 Challengers to verify quantitative soundness, HRP constraint enforcement, and cost model accuracy.
- **Auditor Phase**: Dispatch Forensic Auditor (`teamwork_preview_auditor`) for integrity verification.

### Milestone 2: Software Architecture & Pipeline Robustness Audit (R2)
- **Explorer Phase**: Dispatch 3 Explorers to audit `run_pipeline.py`, `.github/workflows/pipeline.yml`, `.github/workflows/training.yml`, SQLite WAL concurrency locks, failure isolation, exception safety, graceful degradation, and float32 memory/performance optimizations across all 3,379 symbols.
- **Worker Phase**: Dispatch Worker to resolve any pipeline bottlenecks, thread lock risks, missing data exceptions, or GHA workflow flakiness.
- **Reviewer & Challenger Phase**: Dispatch 2 Reviewers and 2 Challengers to run test suites, verify memory downcasting, and stress test concurrent DB locks.
- **Auditor Phase**: Dispatch Forensic Auditor for integrity verification.

### Milestone 3: GitHub Pages Dashboard & Data Integrity Audit (R3)
- **Explorer Phase**: Dispatch Explorers to audit `gh-pages/index.html` and `generate_report.py` for responsive UI/UX (mobile & desktop), macro indicator display (VIX, TNX, USDKRW, WTI, Gold, etc.), strategy coverage metrics, top 20 ensemble recommendations, HRP asset allocation percentages, and decision rationales.
- **Worker Phase**: Dispatch Worker to fix any layout clipping, mobile view overflow, or zero-data rendering issues.
- **Reviewer & Challenger Phase**: Inspect HTML layout, mobile responsiveness, and non-zero data rendering.
- **Auditor Phase**: Dispatch Forensic Auditor for integrity verification.

### Milestone 4: Final End-to-End System Validation & Verification
- **Worker Phase**: Execute end-to-end pipeline run (`run_pipeline.py`) across all markets and generate fresh report files and predictions.
- **Challenger Phase**: Run E2E verification test suite across all 18 strategy prediction outputs and dashboard UI.
- **Auditor Phase**: Final Forensic Audit for 100% compliance with acceptance criteria.
- **Synthesis & Completion**: Produce final report for human user.

## Iteration Loop Discipline per Milestone
- 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate Verdict.
- Binary veto on Forensic Audit failure.

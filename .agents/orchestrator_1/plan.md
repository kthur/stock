# Orchestrator Milestone Plan — Stock Trading System R1-R4

## Objectives
Deliver complete, production-grade solutions for R1, R2, R3, and R4 with zero integrity violations and 100% test pass on all 1,124+ tests.

## Milestones Overview

### Milestone 0: Comprehensive System Survey & Architecture Blueprint
- Map existing codebases, contracts, files, and dependencies for R1, R2, R3, R4.
- Spawn 3 parallel Explorers:
  - `explorer_survey_1`: R1 (Score scale normalization, Percentile Rank / Winsorized Z-Score engine, missing strategy zero-weighting & re-normalization in `ensemble_scorer.py`, `factor_suppression.py`, `factor_orthogonalizer.py`).
  - `explorer_survey_2`: R2 (Filing Lag 45d/40d dynamic window in `earnings_data.py` & `prediction_model.py`, stratified sampling in `prepare_training_data`, total removal of fake BENCHMARK pairs in `stat_arb.py`).
  - `explorer_survey_3`: R3 & R4 (Global `socket.setdefaulttimeout(5)` removal across codebase, individual adaptive timeout & exponential backoff for external APIs, NaN defense in `FallbackMetadataDict`, VIX term structure & change-rate buffering in `risk_manager.py`, and baseline test suite status).
- Synthesize into `PROJECT.md`.

### Milestone 1: 31-Strategy Score Normalization & Missing Weight Re-normalization (R1)
- Implement Cross-Sectional Percentile Rank / Winsorized Z-score normalization.
- Implement dynamic zero-weighting of missing strategy signals and automatic re-normalization.
- Verification: Worker tests, Reviewers, Challengers, Forensic Auditor.

### Milestone 2: Data Pipeline Refinement (R2)
- Dynamic filing lag: KRX 45d, US 40d with real-time filing date override.
- Stratified sampling by market-cap quantile and market/sector in `prepare_training_data`.
- Complete elimination of fake BENCHMARK pairs in `stat_arb.py` (return empty/statistically valid pairs only).
- Verification: Worker tests, Reviewers, Challengers, Forensic Auditor.

### Milestone 3: Stability, Timeout & Exception Handling (R3)
- Remove global `socket.setdefaulttimeout(5)` and implement adaptive timeouts / backoff for yfinance, FRED, ECOS.
- Defend against NaN propagation in `FallbackMetadataDict`.
- Implement VIX term structure and rate-of-change buffering in `risk_manager.py`.
- Verification: Worker tests, Reviewers, Challengers, Forensic Auditor.

### Milestone 4: Full Test Suite & Integrity Verification (R4)
- Execute full pytest suite (`.venv/Scripts/python.exe -m pytest tests/ -v`).
- Fix any remaining regressions or broken unit/integration tests across all 1,124+ tests.
- Verify zero lookahead bias, zero test mocking/cheating, 100% PASS on all tests.
- Final gate verification with full Auditor and Reviewers.

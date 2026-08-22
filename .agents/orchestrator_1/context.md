# Context — Stock Trading System R1-R4

## System Context
- System: Integrated Stock Auto-Trading & Forecasting System (`kthur/stock`).
- 5 Target Markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
- 31 Multi-Factor & Multi-Model Strategies with 2D Market Regime Dynamic Weighted Ensemble.
- Python Environment: `.venv/Scripts/python.exe` (Windows).

## Requirements Summary
- R1: 31-Strategy Score Scale Normalization (Percentile Rank / Winsorized Z-Score) & Missing Strategy Zero-Weighting with Re-normalization.
- R2: Data Pipeline Refinement (Dynamic Filing Lag: KRX 45d, US 40d with real-time filing override; Market/sector/market-cap Stratified Sampling in `prepare_training_data`; Total removal of fake BENCHMARK pairs in Stat-Arb).
- R3: Stability, Timeout & Exception Handling (Remove global `socket.setdefaulttimeout(5)`, adaptive timeouts & exponential backoff for APIs; Defend against NaN propagation in `FallbackMetadataDict`; VIX term structure & change-rate buffering in crisis detection).
- R4: Full Test Suite Passing (100% pass on 1,124+ tests in `tests/`) and zero lookahead bias verification.

## Core Rules & Constraints
- Orchestrator is DISPATCH-ONLY. No direct code editing or test execution.
- Forensic Auditor verdict is a hard binary veto.
- No dummy/mock cheating. All implementations must be authentic.

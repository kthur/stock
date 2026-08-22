## 2026-08-22T06:06:47Z

TASK: Comprehensive Survey & Technical Investigation of Requirements R3 & R4:
1. Global `socket.setdefaulttimeout(5)` Removal:
   - Find all occurrences of `socket.setdefaulttimeout(5)` or global socket timeout modifications in `src/`, `trading_system/`, etc.
   - Design localized adaptive timeouts and exponential backoff retry for `yfinance`, `FRED`, `ECOS`, and other external data sources.
2. `FallbackMetadataDict` NaN Defense:
   - Locate `FallbackMetadataDict` and investigate metadata lookups for invalid/delisted/unmatched tickers.
   - Design defensive filtering against NaN propagation downstream into models and calculations.
3. VIX Term Structure & Change-Rate Buffering in Crisis Detection:
   - Investigate `src/risk/risk_manager.py`, `CrisisDetector`, and VIX override gating logic.
   - Design VIX term structure (e.g. spot vs 3M/futures or historical slope) and change-rate buffering so market recovery momentum is not unnecessarily suppressed.
4. R4 Baseline Test Suite Inspection:
   - Inspect existing test suite in `tests/` (1,124+ tests). Note existing tests for R1, R2, R3 components. Check how `.venv/Scripts/python.exe -m pytest tests/ -v` behaves and identify potential edge case test gaps.
5. Identify all affected source files, exact functions, data models, and test files in `tests/`.
6. Produce a detailed investigation report at `d:\Finance\code\stock\.agents\explorer_survey_3\survey_r3_r4.md` and your `handoff.md`.
Communicate your completion via send_message to your parent.

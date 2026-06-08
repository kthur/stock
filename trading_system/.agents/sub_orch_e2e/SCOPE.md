# Scope: E2E Testing Track

## Architecture
- **tests/phase4/e2e/test_e2e.py**: Contains Tier 1 to Tier 4 E2E tests for Phase 4 requirements.
- **TEST_INFRA.md**: Contains test design specs and configuration details.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Design Test Cases | Outline Tier 1-4 test cases covering R1-R5, define the test framework, and write `TEST_INFRA.md`. | None | DONE |
| 2 | Implement Test Suite | Implement the minimum required test cases (Tier 1: 25, Tier 2: 25, Tier 3: 5, Tier 4: 5) in `tests/phase4/e2e/test_e2e.py`. | M1 | DONE |
| 3 | Publish TEST_READY | Verify tests execute and fail (or pass with stub) and write `TEST_READY.md`. | M2 | DONE |

## Interface Contracts
- Tests must be run via `pytest tests/phase4/e2e/` (or standard command).
- The test harness should mock yfinance and external network requests to avoid rate limits/timeouts.

# Master Execution Plan: Dashboard Strategy Data & UI Integrity

## Objective
Diagnose and resolve data rendering, parsing, synchronization, and interactive UI issues on the GitHub Pages dashboard (`index.html`) across all 31+ multi-factor strategies and 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ). Ensure zero console errors, full table population (no empty tables / "데이터 없음"), and 100% test pass.

## Phases
1. **Phase 0: Survey & Codebase Investigation (Parallel 3 Explorers)**
   - Explorer 1: Deep dive into `generate_report.py`, HTML templates, table rendering, strategy result file parser mappings.
   - Explorer 2: Deep dive into pipeline output files (`trading_system/result/`, `trading_system/`, `merge_predictions.py`, `run_pipeline.py`) and schema synchronization for RIM, Sentiment, Tone Drift, Accruals Quality, Value-Up, Insider Buying, etc.
   - Explorer 3: Deep dive into frontend JS/CSS (`gh-pages/`, interactive filtering, market tabs, modals, score sorting, console error checks) and existing test coverage in `tests/`.

2. **Phase 1: Project & Test Specification (`PROJECT.md` & `TEST_INFRA.md`)**
   - Synthesize Survey reports into exhaustive Feature Inventory, architecture boundaries, and test suites.

3. **Phase 2: Milestone 1 — Strategy Data Parser & Schema Synchronization**
   - 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Auditor -> Gate.
   - Resolve parser breakage, filename mismatches, column name discrepancies, and dynamic filing lag / missing data handling.

4. **Phase 3: Milestone 2 — Multi-Market Table Rendering & Decision Rationale**
   - 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Auditor -> Gate.
   - Ensure all 31+ strategy tables and ensemble rankings are populated across all 5 markets with KST formatting and UTF-8 encoding.

5. **Phase 4: Milestone 3 — Interactive UI, Market Tabs & Error-Free Frontend**
   - 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Auditor -> Gate.
   - Fix JS event listeners, dropdown handlers, dynamic sorting, modals, and responsive layout.

6. **Phase 5: Milestone 4 — 100% E2E Verification & Test Suite Pass**
   - Pass all Tier 1-4 tests and `pytest tests/` suites without regressions.

7. **Phase 6: Milestone 5 — Adversarial Coverage Hardening (Tier 5)**
   - 2 Challengers -> 1 Worker -> 2 Reviewers -> Gate.

8. **Phase 7: Final Delivery & Sentinel Handoff**

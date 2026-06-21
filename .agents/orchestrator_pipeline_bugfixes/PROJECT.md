# Project: Pipeline Bug Fixes (R1-R5)

## Architecture
This project targets five runtime and correctness bugs in the Stock Trading System pipeline.

### Target Files and Modules:
1. `src/data_layer/indicator_storage.py`
   - Purpose: Market data and prediction results database interface.
   - Target bug: R1 - horizon list is missing 120 and 200 days, causing data leaks/omissions.
2. `src/ai/prediction_model.py`
   - Purpose: Machine learning model wrappers and feature merge logic.
   - Target bugs:
     - R2 - `merge_fundamentals` drops `date_fund` which raises KeyError if it's missing. Add `errors='ignore'`.
     - R4 - remove `fill_method=None` from `pct_change()` calls to resolve pandas 2.1+ deprecation warnings.
3. `trading_system/run_pipeline.py`
   - Purpose: Orchestrator that coordinates the pipeline runs.
   - Target bug: R3 - retrieve VCP universe using direct column access (e.g. `universe['symbol']`) rather than `.get()`.
4. `src/persistence/database.py`
   - Purpose: DB connection layer.
   - Target bug: R5 - `StockPriceDB._get_conn` must initialize thread-safely inside a lock to prevent race conditions and connection leaks.

## Code Layout
- `trading_system/run_pipeline.py`
- `src/ai/prediction_model.py`
- `src/data_layer/indicator_storage.py`
- `src/persistence/database.py`
- `tests/` (Unit tests location)

## Milestones
| # | Name | Scope | Dependencies | Status | Conversation ID |
|---|------|-------|-------------|--------|-----------------|
| 1 | Exploration | Gather context and inspect the codebase files | None | DONE | dd49a76c-dcf9-4bcb-8852-06098aa99805, 4f4ade75-270e-4210-9ea6-3e2346a83940, 1d6d592c-f807-4a51-b9e3-d62355a2a7d6 |
| 2 | Implementation | Implement fixes for R1, R2, R3, R4, R5 | M1 | IN_PROGRESS | 1a1ccb2c-eae9-4d0f-bb89-fb0de30deaa0 |
| 3 | Review & Verification | Run reviews, checks, challenges, and audit | M2 | PLANNED | TBD |

## Interface Contracts
No new public interfaces are introduced. All functions must preserve their original signatures and only fix internal implementations.

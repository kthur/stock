# Explorer M1 Iteration 2 Dispatch: Challenger Findings Remediation Design

## Objective
Analyze and design exact patches for the 8 findings identified by Challengers M1-1, M1-2, and Reviewer M1-2:
1. `trading_system/src/ai/prediction_model.py`: In `FallbackMetadataDict`, ensure `'book_value'` is included in benchmark metadata dictionaries (`AAPL`, `MSFT`, `005930`, etc.) to prevent `KeyError: 'book_value'`.
2. `trading_system/src/analysis/statistics.py`:
   - Line 232: Guard annual return exponentiation using `total_ret_clamped = max(1e-6, 1.0 + total_return)` to eliminate complex numbers.
   - Line 249: Return `999.0` (or `0.0`) for `profit_factor` when `gross_loss == 0` instead of `float('inf')` for JSON compliance.
   - Guard against zero division in performance summary when equity is non-positive.
3. `trading_system/src/risk/intraday_stop_loss.py`:
   - Replace `np.inf` and `-np.inf` with `np.nan` before `.dropna()` in price arrays.
4. `trading_system/src/risk/risk_manager.py`:
   - In `CrisisDetector.evaluate()`, add single-factor VIX fast shock override (VIX >= 30.0 forces at least `CrisisLevel.WATCH` / composite >= 0.30; VIX >= 40.0 forces at least `CrisisLevel.ACTIVE` / composite >= 0.60).
5. `trading_system/run_pipeline.py`:
   - Confirm table headers and row formatting strings include Strategy 18 `IFS` (`inst_foreign_sector_score`).
6. `tests/test_m1_master_suite.py`:
   - Fix import `from tests.test_correlation_suppression import ...` so `pytest tests/` runs with 0 collection errors.
7. `trading_system/src/risk/portfolio_optimizer.py`:
   - Align default `default_max_weight=0.15` and `default_max_sector_weight=0.30`.

## Inputs
- `d:\Finance\code\stock\.agents\teamwork_preview_challenger_m1_1\handoff.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_challenger_m1_2\handoff.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m1_2\handoff.md`
- `d:\Finance\code\stock\PROJECT.md`

## Deliverables
- Detailed patch specifications in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_iter2\analysis.md`.
- Handoff report in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_iter2\handoff.md`.

# Worker M1 Dispatch: 31-Strategy Alpha Precision & Pure Alpha Factor Neutralization

## Objective
Implement the complete enhancements for Milestone 1:
1. `trading_system/src/core/multi_factor_neutralizer.py`:
   - Support `prices_dict` as DataFrame / `universe` flexible argument binding.
   - Fallback raw alpha generation from price momentum (12M-1M momentum skipping 1M reversal / 20d return) when `raw_scores` is omitted, while cleanly deactivating with NaNs when neither prices nor fundamentals/scores are present (satisfying `test_bug_a3`).
   - Cross-sectional per-market median imputation for missing fundamentals (Size, Value, Profitability, Investment, Momentum), ensuring 100% symbol retention.
   - Thin QR decomposition $X_m = Q_m R_m$ and orthogonal projection $\epsilon_m = y_m - Q_m (Q_m^T y_m)$.
   - Hard SLA post-condition gate: check $\max_k |\rho(f_k, \epsilon)| < 0.15$; apply secondary Gram-Schmidt deflation if needed.
   - Output both `'factor_neutralized_score'` and alias `'neutralized_score'` columns plus 5 style factor exposures.
2. `trading_system/run_pipeline.py`:
   - Pass keyword arguments to `fn_engine.compute_scores(prices_dict=infer_data_dict, universe=universe, raw_scores=res_df, fundamentals_dict=infer_fund_cache)`.
   - Ensure safe writing of predictions using `'factor_neutralized_score'` and `'neutralized_score'`.
3. `tests/test_factor_neutralized_sla.py`:
   - Implement the comprehensive 6-tier test suite specified by Explorer M1-3.
4. Run tests and verify 100% pass:
   - Run `tests/test_factor_neutralized_sla.py`
   - Run `tests/test_critical_bugs.py`
   - Run `tests/test_factor_orthogonalization.py`
   - Run full test suite regression to ensure 0 broken tests.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## References
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\analysis.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\analysis.md`
- `d:\Finance\code\stock\PROJECT.md`
- `d:\Finance\code\stock\TEST_INFRA.md`
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md`

## Deliverables
- Implemented and verified code files.
- Test execution output documented in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1\handoff.md`.

## 2026-08-14T09:40:13Z
**Context**: Milestone 1 Implementation Status Check
**Content**: Checking in on implementation progress for multi_factor_neutralizer.py, run_pipeline.py, and test_factor_neutralized_sla.py.
**Action**: Please continue execution, run the test suites, and write your handoff report when complete.


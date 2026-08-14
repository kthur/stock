# Worker M1 Replacement (Gen 2) Dispatch: 31-Strategy Alpha Precision & Pure Alpha Factor Neutralization

## Objective
Implement and verify the complete enhancements for Milestone 1:

1. `trading_system/src/core/multi_factor_neutralizer.py`:
   - Inspect `prices_dict`: if `isinstance(prices_dict, pd.DataFrame)`, bind `universe = prices_dict`.
   - If `raw_scores` is missing/empty, generate fallback raw alpha from price momentum (`prices_dict` 12M-1M return skipping 1M reversal / 20d return, or `universe` momentum columns). If no prices or fundamental/score columns are provided (e.g. 2-row blank test dataframe in `test_bug_a3`), cleanly deactivate by returning NaNs as required by existing tests.
   - Market-grouped Fama-French 5-Factor matrix construction with intra-market median imputation for missing fundamentals (`market_cap`, `per`, `pbr`, `roe`, `asset_growth`), ensuring 100% symbol retention across all 3,379 symbols.
   - Thin QR decomposition $X_m = Q_m R_m$ and orthogonal projection $\epsilon_m = y_m - Q_m (Q_m^T y_m)$.
   - Hard SLA post-condition gate: check $\max_k |\rho(f_k, \epsilon)| < 0.15$; apply secondary Modified Gram-Schmidt deflation if needed.
   - Output both `'factor_neutralized_score'` and alias `'neutralized_score'` columns plus 5 style factor exposures (`smb_exposure`, `hml_exposure`, `rmw_exposure`, `cma_exposure`, `umd_exposure`).

2. `trading_system/run_pipeline.py`:
   - Pass keyword arguments to `fn_engine.compute_scores(prices_dict=infer_data_dict, universe=universe, raw_scores=res_df, fundamentals_dict=infer_fund_cache)`.
   - Ensure safe writing of predictions using `'factor_neutralized_score'` and `'neutralized_score'`.

3. `tests/test_factor_neutralized_sla.py`:
   - Implement the comprehensive 6-tier test suite specified by Explorer M1-3.

4. Run tests and verify 100% pass:
   - Run `tests/test_factor_neutralized_sla.py`
   - Run `tests/test_critical_bugs.py`
   - Run `tests/test_factor_orthogonalization.py`
   - Run full regression tests across `tests/` and `trading_system/tests/`

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
- Test execution output documented in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_gen2\handoff.md`.

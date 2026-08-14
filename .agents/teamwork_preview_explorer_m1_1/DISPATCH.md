## 2026-08-14T09:26:44Z
# Explorer M1-1 Dispatch: Factor Neutralizer Engine Implementation Design

## Objective
Analyze the exact implementation changes required in `trading_system/src/core/multi_factor_neutralizer.py` to fix:
1. Positional argument handling for `compute_scores(prices_dict, **kwargs)` when `prices_dict` is a DataFrame.
2. Generating default raw scores from 12M-1M momentum / 3M returns if `raw_scores` is missing.
3. Market-grouped Fama-French 5-Factor matrix construction with median imputation for missing fundamentals (`market_cap`, `per`, `pbr`, `roe`, `asset_growth`).
4. QR decomposition $X_m = Q_m R_m$ and orthogonal projection $\epsilon_m = (I - Q_m Q_m^T) y_m$ to mathematically eliminate factor exposure.
5. Providing both `'factor_neutralized_score'` and alias `'neutralized_score'` columns.
6. A hard post-condition check: if $\max_k |\rho(f_k, \epsilon)| \ge 0.15$, apply secondary Gram-Schmidt deflation.

## Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md`
- `d:\Finance\code\stock\PROJECT.md`
- `trading_system/src/core/multi_factor_neutralizer.py`
- `tests/test_factor_orthogonalization.py`

## Deliverables
- Detailed design and line-by-line patch specifications in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md`.
- Handoff report in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\handoff.md`.


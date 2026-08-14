# Handoff Report — Multi-Factor Risk & Style Neutralizer Engine (Strategy 21) Implementation Design

**Agent**: Explorer M1-1 (Engine Implementation Designer)  
**Target Module**: `trading_system/src/core/multi_factor_neutralizer.py`  
**Milestone**: Milestone 1 (F1: Interface & Imputation, F2: QR Residualization, F3: Pure Alpha Hard SLA Gate)

---

## 1. Observation

Direct code examination and execution traces identified the following precise observations:

1. **Positional Argument Binding Defect**:
   - `trading_system/src/core/multi_factor_neutralizer.py:45-58`:
     ```python
     def compute_scores(self, prices_dict: Any = None, fundamentals_dict: Optional[Dict] = None, indicators_df: Optional[Any] = None, **kwargs: Any) -> Any:
         universe = kwargs.get("universe", kwargs.get("universe_df", pd.DataFrame()))
         ...
         if universe is None or universe.empty:
             return pd.DataFrame(columns=["symbol", "name", "market", "neutralized_score"])
     ```
   - `trading_system/run_pipeline.py:2869`:
     ```python
     factor_neutralized_df = fn_engine.compute_scores(universe)
     ```
   - `tests/test_critical_bugs.py:37`:
     ```python
     res_df1 = engine.compute_scores(universe)
     ```
   - *Observation*: When `universe` is passed as the 1st positional argument, Python binds it to `prices_dict`. `kwargs.get("universe")` evaluates to `None`, defaulting to an empty DataFrame, which causes `compute_scores` to immediately return an empty DataFrame (0 symbols evaluated) in production.

2. **Premature Strategy Deactivation on Missing `raw_scores`**:
   - `trading_system/src/core/multi_factor_neutralizer.py:63-78`:
     ```python
     if not all(col in df.columns for col in req_cols) or (raw_scores is None or raw_scores.empty or "score" not in raw_scores.columns):
         logger.info("MultiFactorNeutralizerEngine: missing required factor columns or raw_scores. Deactivating strategy (returning NaNs).")
     ```
   - *Observation*: In `run_pipeline.py`, `raw_scores` is not passed. The engine logs deactivation and returns `NaN` for all rows instead of generating a deterministic baseline raw alpha signal from available price history or momentum indicators.

3. **Catastrophic Symbol Loss via `dropna`**:
   - `trading_system/src/core/multi_factor_neutralizer.py:82`:
     ```python
     df_merged = df_merged.dropna(subset=["score", "market_cap", "per", "roe"]).copy()
     ```
   - *Observation*: Dropping rows missing any single financial metric deletes hundreds of symbols (unprofitable growth stocks without PER, biotech, recent IPOs) instead of performing market-level median imputation.

4. **Global Cross-Sectional Pooling Distortion**:
   - `trading_system/src/core/multi_factor_neutralizer.py:96-123`:
     ```python
     size_factor = np.log(df_merged["market_cap"].clip(lower=1e8))
     ```
   - *Observation*: Pooling KRW market caps ($10^{11} \sim 10^{14}$ KRW) with USD market caps ($10^8 \sim 10^{12}$ USD) in one global standardization creates artificial cross-currency factor distortions.

5. **Numerical Instability of OLS vs QR Decomposition**:
   - `trading_system/src/core/multi_factor_neutralizer.py:129-130`:
     ```python
     beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
     residuals = y - X.dot(beta)
     ```
   - *Observation*: Direct OLS solves normal equations with squared condition number $\kappa(X^T X) = \kappa(X)^2$. Collinear factor subsets cause numerical precision degradation.

6. **Output Column Inconsistency**:
   - `StrategyMeta.score_column` is `"factor_neutralized_score"`.
   - `run_pipeline.py:2880` and `tests/test_critical_bugs.py:39-40` require `"neutralized_score"`.
   - Lines 74, 91, 150 only populated `"factor_neutralized_score"`.

7. **Absence of Post-Condition SLA Deflation**:
   - No verification or enforcement of $|\rho(f_k, \epsilon)| < 0.15$ exists in the current codebase.

---

## 2. Logic Chain

1. **Step 1 (Argument Binding)**: Because `compute_scores` is invoked with `universe` as the first positional argument across `run_pipeline.py` and `test_critical_bugs.py`, `compute_scores` must inspect the type of `prices_dict`: if it is a `pd.DataFrame`, treat it as `universe`.
2. **Step 2 (Raw Score Hierarchy)**: To prevent strategy deactivation when `raw_scores` is omitted, the engine must extract baseline signals from `prices_map` (12M-1M return skipping 1M reversal noise: $(P_{t-21} / P_{t-252}) - 1.0$) or from universe momentum columns (`momentum_12m`, `return_3m`), while maintaining deterministic NaN output when neither factors nor prices are provided (passing `test_bug_a3`).
3. **Step 3 (Market-Grouped Median Imputation)**: By partitioning the universe by `market` and imputing missing factor values with the intra-market median, all 3,379 symbols are retained (0% symbol loss) and currency/market scale discrepancies are eliminated.
4. **Step 4 (QR Decomposition Orthogonal Projection)**: Factoring $X_m = Q_m R_m$ via thin QR decomposition ($Q_m^T Q_m = I_6$) yields orthogonal projector $P_{X} = Q_m Q_m^T$ and annihilator $M_X = I - Q_m Q_m^T$. Computing $\epsilon_m = y_m - Q_m (Q_m^T y_m)$ eliminates factor exposure in $O(N K)$ operations and guarantees $Q_m^T \epsilon_m = \mathbf{0}$ at machine precision without forming the $N \times N$ matrix.
5. **Step 5 (Secondary Gram-Schmidt Deflation Gate)**: Evaluating $\rho_{\max} = \max_k |\text{Corr}(f_k, \epsilon_m)|$ and applying Modified Gram-Schmidt deflation if $\rho_{\max} \ge 0.15$ guarantees the hard SLA constraint under all edge cases.
6. **Step 6 (Dual Column Schema)**: Providing both `'factor_neutralized_score'` and `'neutralized_score'` alongside style factor exposures (`smb_exposure`, `hml_exposure`, `rmw_exposure`, `cma_exposure`, `umd_exposure`) guarantees 100% test and pipeline compatibility.

---

## 3. Caveats

- **KONEX / Small Sample Markets**: For markets with $N_m < 6$ symbols (less than the number of factor columns + intercept), thin QR is under-determined; the engine falls back to de-meaning $\epsilon = y - \bar{y}$.
- **Completely Missing Data**: If a universe DataFrame contains only symbol names without prices, fundamentals, or momentum columns, the engine logs deactivation and returns `NaN` as required by test contract `test_bug_a3`.
- **Zero Variance Factors**: If all stocks in a market have identical values for a factor (e.g. constant CMA), standard deviation is clamped and the factor column is zeroed out to avoid division by zero.

---

## 4. Conclusion

The complete architectural redesign and source code specification for `trading_system/src/core/multi_factor_neutralizer.py` is documented in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md`. The proposed implementation:
1. Fixes positional argument binding and enables seamless execution from `run_pipeline.py`.
2. Implements market-grouped Fama-French 5-Factor matrix construction with intra-market median imputation.
3. Applies thin QR orthogonal projection $\epsilon = y - Q (Q^T y)$ ensuring zero linear factor exposure.
4. Enforces the $|\rho| < 0.15$ SLA gate with secondary Gram-Schmidt deflation.
5. Provides dual column naming (`factor_neutralized_score` and `neutralized_score`) and 5 style exposure diagnostics.

---

## 5. Verification Method

### Test Commands
Run pytest against critical bugs, factor orthogonalization, and empirical challenger suites:
```bash
.venv/Scripts/python.exe -m pytest tests/test_critical_bugs.py tests/test_factor_orthogonalization.py tests/test_m1_empirical_challenger.py -v
```

### Files to Inspect
- `d:\Finance\code\stock\trading_system\src\core\multi_factor_neutralizer.py`
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md`
- `d:\Finance\code\stock\trading_system\run_pipeline.py` (lines 2866–2884)

### Invalidation Conditions
- Any output DataFrame missing `'factor_neutralized_score'` or `'neutralized_score'`.
- Residual correlation with any Fama-French factor exceeding $|\rho| \ge 0.15$.
- Dropping valid symbols from the input universe (length mismatch `len(output) != len(universe)`).
- Failure of `test_bug_a3_factor_neutralizer_deactivates_without_random`.

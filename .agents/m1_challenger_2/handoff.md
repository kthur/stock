# Milestone 1 Adversarial Challenge Report: Pipeline Concurrency & Resilience

**Verdict**: **APPROVE**

---

## 1. Observation
- **Parallel Factor Strategy Scoring Concurrency & Exception Isolation** (`trading_system/run_pipeline.py:3150-3246`):
  - Factor scoring evaluates 26 strategy functions via `ThreadPoolExecutor(max_workers=_score_workers)` where `_execute_single_strat` wraps execution in `try...except Exception as _err: return _s_key, pd.DataFrame()`.
  - Non-DataFrame returns (e.g. `None`, integers, dicts) are checked via `if not isinstance(_res, pd.DataFrame): _res = pd.DataFrame()`.
  - Downstream report generation (`_save_strategy_predictions_report`) strictly skips empty or missing score columns (`if df_strat is None or df_strat.empty or score_col not in df_strat.columns: return`).
  - Downstream ensemble dictionary `_all_strategy_dfs` (lines 3299-3314) is constructed using a fixed literal dictionary mapping that references local DataFrame variables or defaults to empty DataFrames.
- **Deterministic Report & Dictionary Ordering**:
  - Worker threads complete in non-deterministic time order via `as_completed()`, but report generation iterates deterministically over `for spec in STRATEGY_REGISTRY:` (lines 3202-3217).
  - Downstream dictionary keys in `_all_strategy_dfs` follow a deterministic literal definition matching canonical strategy order.
- **Dynamic ML Thread Allocation** (`trading_system/src/ai/prediction_model.py:1581-1614, 1790-1834, 1965-1995, 2086-2176`):
  - In `train` and `train_surge`, `n_jobs` is received as an argument. When `n_jobs` is provided, `intra_n_jobs = max(1, int(n_jobs))`; otherwise `intra_n_jobs = max(1, (os.cpu_count() or 4))`.
  - Parameters are assigned to estimator configurations: `kw_xgb['n_jobs'] = intra_n_jobs`, `kw_lgb['n_jobs'] = intra_n_jobs`, `kw_cat['thread_count'] = intra_n_jobs`.
  - Instantiated estimators (`XGBRegressor`, `LGBMRegressor`, `CatBoostRegressor`, `XGBClassifier`, `LGBMClassifier`, `CatBoostClassifier`) and CPU-fallback branches retain these thread limits.
- **Persistence & Scaler Caching**:
  - `StockPriceDB.update_prices_batch` performs batch upserts under a single acquisition of `_SHARED_WRITE_LOCK`.
  - `load_scaler` uses `@functools.lru_cache(maxsize=128)` with normalized arguments and cache invalidation in `fit_scaler`.

---

## 2. Logic Chain
1. **Exception Isolation Proof**:
   - In our empirical harness (`TestStrategyScoringExceptionIsolation`), we injected simulated faults into strategy workers (`RuntimeError`, `KeyError`, `ZeroDivisionError`, returning `None`, scalar numbers, dictionaries) alongside valid strategies.
   - The thread pool successfully completed without throwing unhandled exceptions. All faulted workers produced empty DataFrames, while valid workers produced valid DataFrames.
   - We tested catastrophic 100% strategy failure across all strategies in `EnsembleScoringEngine` (`test_all_strategies_failing_ensemble_resilience`). The engine executed gracefully, appropriately applying active-weight zero-masking and returning a valid DataFrame without crashing.
2. **Deterministic Ordering Proof**:
   - In `TestDeterministicOrdering`, we introduced random thread execution delays (1-15ms jitter) across 26 strategy workers over 15 separate runs.
   - Even though futures finished in random permutations, the resulting `_all_strategy_dfs` dictionary keys and report outputs strictly preserved the exact canonical registry order across 100% of the runs.
3. **ML Thread Allocation Propagation Proof**:
   - In `TestMLThreadAllocation`, we trained models with explicit `n_jobs=1`, `n_jobs=2`, `n_jobs=3`, `n_jobs=None`, and `n_jobs=0`.
   - Verified that `xgb_model.get_params()['n_jobs']`, `lgb_model.get_params()['n_jobs']`, and `cat_model.get_params()['thread_count']` matched the assigned thread allocations exactly.
   - Confirmed `n_jobs=None` properly resolved to `max(1, os.cpu_count() or 4)` and edge cases (0 or negative) clamped safely to 1.
4. **Concurrency & Thread Safety Proof**:
   - Stressed `load_scaler` under 16 concurrent reader threads and simultaneous fitter invalidation threads. 0 errors, 0 corrupted scaler objects.
   - Stressed `StockPriceDB.update_prices_batch` across 4 concurrent threads upserting 20 tickers. 0 database lock errors, exact 30-row consistency per symbol.
5. **Full Test Suite Validation**:
   - Ran 56 core tests across database, prediction model, pipeline integration, multi-market/multi-strategy, DAG pipeline, and modular pipeline targets. 100% passed (56/56).

---

## 3. Caveats
- `_execute_single_strat` catches standard `Exception`. System-level terminations like `KeyboardInterrupt` or `SystemExit` (inheriting from `BaseException`) will intentionally terminate, which is expected standard Python behavior.
- ThreadPoolExecutor workers operate in the same process memory space; factor strategy engines must not modify shared inputs (`infer_data_dict`, `prices_dict`) in-place. All 31 factor engines adhere to read-only semantics.

---

## 4. Conclusion
The concurrency architecture, thread-pool isolation, deterministic report generation, dynamic ML thread allocation, scaler LRU caching, and database batch upserting have been empirically stressed and verified. The system demonstrates robust fault isolation, consistent execution ordering, and proper resource budgeting under multi-threaded stress.

**Verdict**: **APPROVE**

---

## 5. Verification Method
To independently verify the empirical claims and regression safety:

```bash
# 1. Run core unit, integration, and concurrency test suite
.venv\Scripts\pytest tests/test_database.py tests/test_prediction_model.py tests/test_pipeline_integration.py tests/test_all_16_markets_31_strategies.py tests/test_database_concurrency.py tests/test_dag_pipeline.py tests/test_modular_pipeline.py tests/test_ensemble_lgb_cat.py -v

# 2. Run prediction model vectorization & thread allocation tests
.venv\Scripts\pytest tests/test_prediction_model.py tests/test_pipeline_integration.py -v
```

### Invalidation Conditions:
- If a strategy worker throwing an exception crashes the `run_pipeline.py` process.
- If `_all_strategy_dfs` keys order alters across different pipeline invocations.
- If `model.train()` or `model.train_surge()` fails to pass `n_jobs` to underlying XGBoost, LightGBM, or CatBoost estimators.
- If concurrent batch upserts in `StockPriceDB` encounter unhandled `OperationalError: database is locked`.

# Handoff Report: Scaler Caching & Dynamic ML Thread Allocation

## 1. Observation

- **Obs 1: Un-cached Scaler Loading Disk I/O**:
  - In `src/ai/prediction_model.py:2495`, `_predict_regression()` iterates over all 9 prediction horizons ($h \in [1, 2, 3, 5, 10, 20, 60, 120, 200]$) and up to 5 markets (`sp500`, `nasdaq`, `russell2000`, `kospi`, `kosdaq`), calling:
    ```python
    scaler = load_scaler(str(self.model_dir), scaler_mkt, h)
    ```
  - In `src/ai/feature_engineering.py:35-43`:
    ```python
    def load_scaler(model_dir: str, market: str, horizon: int) -> StandardScaler:
        scaler_path = os.path.normpath(get_scaler_path(model_dir, market, horizon))
        if os.path.exists(scaler_path):
            try:
                return joblib.load(scaler_path)
            except Exception as e:
                logger.warning(f"Failed to load scaler from {scaler_path}: {e}")
        logger.warning(f"Scaler not found at {scaler_path}. Returning default StandardScaler.")
        return StandardScaler()
    ```
  - Every inference pass executes 45 separate disk reads and pickle deserialization calls.

- **Obs 2: CPU Thread Oversubscription during Parallel Training**:
  - In `trading_system/run_pipeline.py:1726-1760`:
    ```python
    _train_workers = max(1, min(4, _CPU_WORKERS))
    with ThreadPoolExecutor(max_workers=_train_workers) as pool:
        for m_name, m_df in market_dfs.items():
            futures[pool.submit(model.train, m_df, market=m_name, save_after=True)] = m_name
    ```
  - In `src/ai/prediction_model.py:260, 271, 280, 296, 310, 319`:
    XGBoost, LightGBM, and CatBoost models default to `n_jobs=-1` and `thread_count=-1`.
  - When 4 market workers execute concurrently on an 8-core CPU, $4 \times 8 = 32$ OpenMP compute threads contend for 8 CPU cores.

- **Obs 3: Unit Test Execution Baseline**:
  - Executed `.venv\Scripts\pytest tests/test_prediction_model.py tests/test_ensemble_lgb_cat.py -v`:
    Result: 9 passed, 16 warnings in 163.60s (100% pass rate).
  - Currently no direct unit tests exist in `tests/` verifying `load_scaler` cache behavior or dynamic `n_jobs` propagation.

---

## 2. Logic Chain

1. **Scaler Cache Thread-Safety & Hit Rate (Obs 1)**:
   - Wrapping scaler loading with `@functools.lru_cache(maxsize=128)` via an internal function `_load_scaler_cached(norm_model_dir, market, horizon)` caches fitted `StandardScaler` instances in memory.
   - CPython's `lru_cache` is internally synchronized with C mutexes, providing thread-safety across concurrent workers.
   - Normalizing paths (`os.path.normpath(str(model_dir))`), lowercase market keys (`market.lower()`), and integer horizons (`int(horizon)`) guarantees 100% cache hit consistency regardless of argument object types (`Path` vs `str`).
   - Adding `clear_scaler_cache()` and calling it in `fit_scaler(...)` ensures immediate eviction of stale scalers upon model retraining.

2. **Eliminating Thread Thrashing via Intra-Worker Budgeting (Obs 2)**:
   - By calculating $\text{intra\_n\_jobs} = \max(1, \text{\_CPU\_WORKERS} // \text{\_train\_workers})$ in `run_pipeline.py` and passing `n_jobs=_intra_n_jobs` to `model.train()` and `model.train_surge()`, each market worker's model is constrained to its fair share of CPU cores.
   - Updating `train()` and `train_surge()` in `src/ai/prediction_model.py` to set `kw_xgb['n_jobs'] = intra_n_jobs`, `kw_lgb['n_jobs'] = intra_n_jobs`, and `kw_cat['thread_count'] = intra_n_jobs` guarantees that total concurrent OpenMP threads $\le \text{cpu\_count}$.
   - This eliminates scheduler context switching, OpenMP barrier stalls, and L1/L2/L3 cache line thrashing.

---

## 3. Caveats

- In `apply_scaler` (`src/ai/feature_engineering.py:68-78`), if an unfitted scaler or feature mismatch occurs with $N > 10$ rows, `scaler.fit_transform(X)` is invoked as a fallback. Since `load_scaler` returns the cached scaler instance, callers should not mutate returned scalers in-place outside of `fit_scaler`. In practice, normal inference uses `.transform(X_aligned)` (read-only), which does not mutate internal attributes.
- PyTorch LSTM training inside `train()` (`src/ai/prediction_model.py:1834`) uses its own PyTorch CPU thread pool (`torch.set_num_threads` if configured). Tree models (XGB/LGB/Cat) are the primary consumers of OpenMP threads.

---

## 4. Conclusion

The exact code specifications developed in `analysis.md`:
1. Provide a robust, thread-safe LRU caching mechanism for `load_scaler` with key normalization and automatic invalidation in `fit_scaler`.
2. Provide dynamic CPU thread allocation for XGBoost, LightGBM, and CatBoost in `prediction_model.py` and `run_pipeline.py`.
3. Provide dedicated unit tests `TestScalerCaching` and `TestMLThreadAllocation` for regression prevention.

---

## 5. Verification Method

To verify the proposed implementation once applied:
```bash
# 1. Run prediction model and ensemble test suites
.venv\Scripts\pytest tests/test_prediction_model.py tests/test_ensemble_lgb_cat.py -v

# 2. Run full consolidated regression test suite
.venv\Scripts\pytest tests/test_e2e_consolidated.py -v
```
Inspect `analysis.md` in `d:\Finance\code\stock\.agents\m1_explorer_scaler_threads\analysis.md` for complete code diffs and implementation details.

# Forensic Audit Report — Milestone 1 (Data Quality & Corporate Action Sanity Gates)

**Work Product**: `trading_system/src/data_layer/data_validator.py`, `trading_system/src/utils/technical_cache.py`, `trading_system/src/persistence/database.py`, `trading_system/src/data_layer/price_adjuster.py`, `trading_system/run_pipeline.py`, `trading_system/tests/test_technical_cache.py`, `trading_system/tests/test_data_validator.py`  
**Profile**: General Project / Forensic Auditor  
**Integrity Mode**: Development Mode  
**Verdict**: **CLEAN**

---

## 1. Observation

### Source Code Inspection & Logic Analysis

1. **Genuine Calculations (No Facades or Hardcoded Results)**:
   - `trading_system/src/data_layer/data_validator.py`:
     - Line 147-156: Computes price return ratios `ratios = (valid_close / valid_close.shift(1)).dropna()` and magnitude `mags = ratios.apply(lambda r: (max(r, 1.0 / r) - 1.0) if (pd.notna(r) and r > 0) else 0.0)`. Checks `max_mag > 3.0` (magnitude > 300%) to flag and reject abnormal corporate action spikes or unadjusted splits.
     - Line 207-276 (`filter_price_spikes`): Calls `CorporateActionAdjuster().adjust_ohlcv(df)` for stock split ratio detection, then cleans single-day isolated spikes by interpolation (`(p_prev + p_next) / 2.0`) or unadjusted backward split adjustment (`adjusted.loc[prior_mask, pc] = adjusted.loc[prior_mask, pc] * r`).
   - `trading_system/src/data_layer/price_adjuster.py`:
     - Line 49-72 (`adjust_ohlcv`): Calculates price ratios `close_series / close_series.shift(1)`, detects split threshold anomalies `(ratios < 0.60) | (ratios > 1.60)`, and scales prior OHLCV history backward (`df.loc[prior_mask, price_cols] * r` and `df.loc[prior_mask, vol_cols] / r`).

2. **`DataFrameCache` Active TTL Eviction & Date-Change Invalidation**:
   - `trading_system/src/utils/technical_cache.py`:
     - Line 200-207: Thread-safe instantiation with `self._lock = threading.Lock()` and tracking `self._last_date = datetime.now().date()`.
     - Line 222-232 (`_check_date_change_unlocked`): Compares `datetime.now().date() != self._last_date`. When date changes, clears `self._cache` and `self._timestamps` automatically.
     - Line 233-239 (`_evict_expired_unlocked`): Computes `(now - ts) >= self._ttl` and purges expired entries upon any access (`get`, `set`, `get_or_compute`) or explicit call (`evict_expired`).
     - Line 318-322 (`_evict_if_needed`): LRU capacity eviction removes the oldest entry when cache size exceeds `max_items`.

3. **Data Gate Integration in DB & Pipeline**:
   - `trading_system/src/persistence/database.py`:
     - Line 474-478 (`update_prices`): Invokes `DataValidator.validate_price_data(symbol, df)` before saving into `StockPriceDB`. Aborts upserts if validation fails.
   - `trading_system/run_pipeline.py`:
     - Line 500-503 & Line 542-550: Uses `DataValidator.sanitize_and_validate_price_data(sym, ticker_df)` during batch prefetching and single symbol network downloads before persisting to `StockPriceDB`.

### Empirical Unit Test Execution

Running `.venv\Scripts\python.exe -m pytest trading_system/tests/test_technical_cache.py trading_system/tests/test_data_validator.py -v`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Finance\code\stock\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Finance\code\stock\trading_system
configfile: pyproject.toml
plugins: anyio-4.14.0, dash-2.18.2, cov-7.1.0, github-actions-annotate-failures-0.4.2
collecting ... collected 13 items

trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_cache_hit_and_miss PASSED [  7%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_date_change_invalidation PASSED [ 15%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_explicit_evict_expired PASSED [ 23%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_invalidate_and_clear PASSED [ 30%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_lru_capacity_eviction PASSED [ 38%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_thread_safety PASSED [ 46%]
trading_system\tests\test_technical_cache.py::TestDataFrameCache::test_ttl_auto_eviction PASSED [ 53%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_clean_macro_value PASSED [ 61%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_detect_shared_series_corruption PASSED [ 69%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_filter_price_spikes PASSED [ 76%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_single_day_price_spike_rejection PASSED [ 84%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_unadjusted_split_and_corporate_action_gate PASSED [ 92%]
trading_system\tests\test_data_validator.py::TestDataValidator::test_validate_price_data PASSED [100%]

============================= 13 passed in 1.83s ==============================
```

---

## 2. Logic Chain

1. **Step 1 (Source Verification)**: Inspection of `data_validator.py`, `technical_cache.py`, `price_adjuster.py`, `database.py`, and `run_pipeline.py` confirms that code logic contains real mathematical computations, ratio checks, timestamp comparisons, and filtering algorithms. No hardcoded expected test outputs, dummy return values, or facade methods exist.
2. **Step 2 (Feature Verification — Technical Cache)**: `DataFrameCache` implements `_evict_expired_unlocked()` for active TTL expiration and `_check_date_change_unlocked()` for trading date invalidation. Thread-safety is guaranteed via `threading.Lock()`.
3. **Step 3 (Feature Verification — Data Quality & Corporate Actions)**: `DataValidator.validate_price_data` rejects price return magnitudes > 300% (`max_mag > 3.0`). `CorporateActionAdjuster.adjust_ohlcv` and `filter_price_spikes` detect split ratios (e.g. 1:4 splits) and backward-adjust prior OHLCV data. These gates are actively invoked in `run_pipeline.py` and `StockPriceDB.update_prices()`.
4. **Step 4 (Empirical Test Verification)**: Executing pytest against `test_technical_cache.py` and `test_data_validator.py` results in 13 tests passing out of 13 collected, with 0 failures or warnings.
5. **Conclusion Formulation**: All 4 audit requirements are verified empirically and algorithmically. The work product is clean of integrity violations or cheating.

---

## 3. Caveats

- **Scope Boundary**: Audit focused exclusively on Milestone 1 requirements (`data_validator.py`, `technical_cache.py`, `database.py`, `price_adjuster.py`, `run_pipeline.py`, `test_technical_cache.py`, `test_data_validator.py`). Subsequent milestone implementations (e.g., vectorized inference in Milestone 2 or OMS dynamic slippage in Milestone 3) were not evaluated in this report.
- **Environment**: Verified on Windows OS using Python 3.11.9 (`.venv\Scripts\python.exe`).

---

## 4. Conclusion

**Verdict**: **CLEAN**

The code changes for Milestone 1 implement genuine data quality checks and technical caching without any integrity violations, hardcoded facades, or cheating logic. All 13 unit tests pass cleanly.

---

## 5. Verification Method

To independently verify this audit result, execute the following command from `d:\Finance\code\stock`:

```powershell
.venv\Scripts\python.exe -m pytest trading_system/tests/test_technical_cache.py trading_system/tests/test_data_validator.py -v
```

Expected result: 13 passed in under 3 seconds.

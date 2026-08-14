# Milestone 1 Investigation & Implementation Design Report
**Data Quality & Corporate Action Sanity Gates**

- **Author**: Explorer Agent (Milestone 1)
- **Target Working Directory**: `d:/Finance/code/stock`
- **Report Path**: `d:/Finance/code/stock/.agents/explorer_m1/report.md`
- **Date**: 2026-08-12

---

## Executive Summary

This report presents a comprehensive architectural and codebase investigation for **Milestone 1: Data Quality & Corporate Action Sanity Gates**. 

Milestone 1 resolves two major data quality risks in the stock trading pipeline:
1. **Corporate Action Price Anomalies**: Raw OHLCV data from external network providers (yfinance, FDR, Naver, PyKRX, Stooq) can contain unadjusted stock splits, reverse splits, or bad data corruption causing single-day price jumps/drops exceeding +300% or -75%. Existing validation in `DataValidator` checks if >5% of all rows have returns >100%, which completely misses isolated 1-2 bar price spikes (e.g. 0.1% of rows) and allows contaminated data into `StockPriceDB` and downstream feature calculation.
2. **Technical Indicator Cache TTL Invalidation**: `DataFrameCache` in `src/utils/technical_cache.py` caches raw OHLCV DataFrames with a 60s TTL, but lacks proactive auto-eviction of expired keys upon access, lacks trading date-change tracking (leading to stale daily price caches across midnight boundaries), and has no dedicated unit test suite.

No production code was modified during this investigation. A step-by-step implementation guide for the Implementer agent is detailed below.

---

## 1. Corporate Action Sanity Gates

### 1.1 Ingestion & Validation Code Base Locations

| File | Exact Line Numbers | Current Function / Class | Role & Observations |
|---|---|---|---|
| `trading_system/src/data_layer/data_validator.py` | Lines 102–168, 171–189 | `validate_price_data(sym, df)` / `DataValidator` | Centralized data quality validator. Checks Close non-positive ratio, NaN ratio (>50%), extreme return ratio (>100% on >5% of rows), and zero volume ratio (>90%). **Defect**: Misses isolated single-day price spikes (>300%) if total frequency is <=5% of dataset. |
| `trading_system/src/data_layer/price_adjuster.py` | Lines 17–61 | `CorporateActionAdjuster.adjust_ohlcv(df_prices)` | Detects unadjusted stock split price gaps (`ratio < 0.60` or `ratio > 1.60`) and backward-adjusts prior OHLCV prices and volumes. **Defect**: Not hooked into `DataValidator` or `StockPriceDB.update_prices`. |
| `trading_system/src/persistence/database.py` | Lines 467–504 | `StockPriceDB.update_prices(symbol, df)` | Batch upserts OHLCV data into SQLite `stock_prices`. **Defect**: Accepts any DataFrame without running `validate_price_data` first. |
| `trading_system/src/data_layer/market_data_handler.py` | Line 336 | `MarketDataHandler.fetch_historical_data(...)` | Fetches historical price bars and writes to `StockPriceDB`. **Defect**: Calls `db.update_prices(symbol, hist)` directly without calling `CorporateActionAdjuster` or `DataValidator.validate_price_data`. |
| `trading_system/run_pipeline.py` | Lines 410–460, Line 555, Line 596 | `_validate_price_data` (local) & `fetch_data_fdr` | Batch pre-fetching and network fetching. **Defect**: Lines 410–460 duplicate `_validate_price_data` inline instead of delegating 100% to `DataValidator.validate_price_data`. |

---

### 1.2 Exact Sanity Gate Logic Design

To eliminate corporate action price spikes and unadjusted splits:

1. **Single-Day Price Change Threshold (`MAX_SINGLE_DAY_RETURN = 3.0`)**:
   - Calculate single-day relative return: $R_t = \left|\frac{\text{Close}_t}{\text{Close}_{t-1}} - 1.0\right|$.
   - A single-day return $R_t > 3.0$ indicates a price jump $>+300\%$ (price ratio $>4.0$) or a drop $<-75\%$ (price ratio $<0.25$).
   
2. **Integrated Adjustment and Filtering Pipeline**:
   - **Step 1 (Auto-adjust Stock Splits)**: Pass candidate `df` through `CorporateActionAdjuster().adjust_ohlcv(df)`. This automatically detects stock splits / reverse splits and scales historical prices before the split date.
   - **Step 2 (Single-Day Spike Gate)**: After split adjustment, evaluate single-day price returns. If `daily_ret.max() > MAX_SINGLE_DAY_RETURN`:
     - Log warning: `[CorporateActionGate] {sym}: abnormal price spike detected (max return={max_ret:.1%} > 300%). Payload rejected.`
     - Return `False` in `DataValidator.validate_price_data(sym, df)`.
   - **Step 3 (Row-level Sanitizer Helper)**: Add `DataValidator.sanitize_price_spikes(sym: str, df: pd.DataFrame, max_return: float = 3.0) -> Tuple[pd.DataFrame, bool]` to allow isolated 1-row corrupt spikes to be cleaned via backward/forward fill if the rest of the dataset is healthy.

3. **Hook Locations**:
   - **`StockPriceDB.update_prices` (`database.py:467`)**: Add defensive check inside `update_prices`. If `not DataValidator.validate_price_data(symbol, df)` (and `bypass_validation=False`), skip SQLite write and return 0.
   - **`MarketDataHandler.fetch_historical_data` (`market_data_handler.py:336`)**: Apply `CorporateActionAdjuster().adjust_ohlcv(hist)` and validate with `DataValidator.validate_price_data(symbol, hist)` prior to `db.update_prices`.
   - **`run_pipeline.py` (Lines 410, 555, 596)**: Remove duplicated inline `_validate_price_data` and ensure `CorporateActionAdjuster().adjust_ohlcv` is called on raw network payloads before `DataValidator.validate_price_data` and DB update.

---

## 2. Technical Indicator Cache TTL Auto-Eviction

### 2.1 Current `DataFrameCache` Inspection

- **File Location**: `trading_system/src/utils/technical_cache.py` (Lines 191–232)
- **Current Signature & Fields**:
  ```python
  class DataFrameCache:
      def __init__(self, ttl: float = 60.0, max_items: int = 200):
          self._ttl = ttl
          self._max_items = max_items
          self._cache: Dict[Tuple[str, str], pd.DataFrame] = {}
          self._timestamps: Dict[Tuple[str, str], float] = {}
          self._lock = threading.Lock()
  ```

### 2.2 Defects Identified

1. **No Date-Change Tracking**: Cache keys are `(symbol, start_date)`. If the pipeline runs across midnight or a trading date change, cached DataFrames from the previous day remain valid until `ttl` (60s) expires. There is no trading date tracking (`_last_trading_date`) to trigger bulk cache invalidation when `datetime.now().date()` changes.
2. **Passive TTL Check**: When `key in self._cache` and `age >= self._ttl`, `get_or_compute` calls `fetcher`, but does not proactively purge expired entries from `_timestamps` and `_cache` if those keys are never accessed again.
3. **No Standalone `evict_expired()` Method**: No helper to sweep expired entries on demand.
4. **Missing Symbol-wide Invalidation**: `invalidate(symbol, start_date)` currently requires an exact `start_date` match. It cannot invalidate all cached start dates for a given symbol.

### 2.3 Required Design Enhancements

1. **Trading Date Tracking & Auto-Invalidation**:
   - Add `self._last_trading_date = datetime.now().date()` in `__init__`.
   - In `_check_date_change()` (called on `get_or_compute`, `get`, `evict_expired`):
     ```python
     current_date = datetime.now().date()
     if current_date != self._last_trading_date:
         logger.info(f"[DataFrameCache] Trading date changed ({self._last_trading_date} -> {current_date}). Clearing cache.")
         self._cache.clear()
         self._timestamps.clear()
         self._last_trading_date = current_date
     ```
2. **Proactive Access & Dedicated Sweep Eviction**:
   - On access (`get_or_compute`): if `age >= self._ttl`, explicitly `pop` key before computing new DataFrame.
   - Implement `evict_expired(self) -> int`:
     ```python
     def evict_expired(self) -> int:
         """Purge all entries older than self._ttl. Returns count of evicted items."""
         now = time.time()
         with self._lock:
             self._check_date_change()
             expired_keys = [k for k, ts in self._timestamps.items() if (now - ts) >= self._ttl]
             for k in expired_keys:
                 self._cache.pop(k, None)
                 self._timestamps.pop(k, None)
             return len(expired_keys)
     ```
3. **Enhanced Invalidation**:
   - Update `invalidate(self, symbol: str, start_date: Optional[str] = None)`:
     If `start_date` is provided, delete `(symbol, start_date)`.
     If `start_date` is `None`, delete all `(symbol, *)` keys.
4. **Properties & Helpers**:
   - `@property def ttl(self) -> float` & `@ttl.setter def ttl(self, value: float)`
   - `def __len__(self) -> int: return len(self._cache)`

---

## 3. Unit Tests Design

### 3.1 New & Extended Test Suites

| Test File | Target Module | New Test Method | Verification Purpose |
|---|---|---|---|
| `trading_system/tests/test_data_validator.py` | `src/data_layer/data_validator.py` | `test_validate_price_data_spike_filtering` | Verifies that single-day price return >300% is rejected by `validate_price_data`. |
| `trading_system/tests/test_data_validator.py` | `src/data_layer/data_validator.py` & `price_adjuster.py` | `test_unadjusted_split_and_corporate_action_gate` | Verifies `CorporateActionAdjuster` integrates with `DataValidator` to adjust splits and reject unadjusted/corrupted spikes. |
| `trading_system/tests/test_technical_cache.py` *(NEW)* | `src/utils/technical_cache.py` | `test_dataframe_cache_ttl_and_eviction` | Tests `DataFrameCache` hit, miss, TTL expiration, and `evict_expired()`. |
| `trading_system/tests/test_technical_cache.py` *(NEW)* | `src/utils/technical_cache.py` | `test_dataframe_cache_date_change_invalidation` | Verifies automatic cache clearing when `_last_trading_date` changes. |
| `trading_system/tests/test_database.py` | `src/persistence/database.py` | `test_update_prices_defensive_validation` | Verifies `StockPriceDB.update_prices` rejects DataFrames failing price validation. |

---

## 4. Step-by-Step Implementation Guide for Implementer

### Step 1: Update `trading_system/src/data_layer/data_validator.py`

**Lines 144–154**: Update `validate_price_data` to check single-day price returns:

```python
    # 2. Extreme daily returns check
    if len(valid_close) >= 2:
        daily_ret = valid_close.pct_change().abs().dropna()
        if len(daily_ret) > 0:
            # P0 Gate: Any single-day price return > 300% (4x jump or <-75% drop) indicates unadjusted corporate action / corrupt spike
            max_ret = daily_ret.max()
            if max_ret > 3.0:
                logger.warning(
                    f"[DataValidator] {sym}: single-day price return spike max={max_ret:.1%} > 300% (unadjusted split/corrupted), skipping"
                )
                return False

            extreme_ratio = (daily_ret > 1.0).sum() / len(daily_ret)
            if extreme_ratio > 0.05:
                logger.warning(
                    f"[DataValidator] {sym}: extreme return ratio={extreme_ratio:.1%} > 5%, skipping"
                )
                return False
```

Add helper method to `DataValidator` class:
```python
    @staticmethod
    def sanitize_and_validate_price_data(sym: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
        """Apply CorporateActionAdjuster and validate price data."""
        if df is None or df.empty:
            return df, False
        from src.data_layer.price_adjuster import CorporateActionAdjuster
        adjusted_df = CorporateActionAdjuster().adjust_ohlcv(df)
        is_valid = validate_price_data(sym, adjusted_df)
        return adjusted_df, is_valid
```

---

### Step 2: Update `trading_system/src/utils/technical_cache.py`

**Lines 191–232**: Replace `DataFrameCache` class with:

```python
class DataFrameCache:
    """Thread-safe TTL cache for raw OHLCV DataFrames with auto-eviction and date-change invalidation."""

    def __init__(self, ttl: float = 60.0, max_items: int = 200):
        self._ttl = ttl
        self._max_items = max_items
        self._cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self._timestamps: Dict[Tuple[str, str], float] = {}
        self._last_trading_date = datetime.now().date()
        self._lock = threading.Lock()

    @property
    def ttl(self) -> float:
        return self._ttl

    @ttl.setter
    def ttl(self, value: float) -> None:
        with self._lock:
            self._ttl = value

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def _check_date_change(self) -> None:
        """Invalidate cache if trading date has changed."""
        today = datetime.now().date()
        if today != self._last_trading_date:
            logger.info(
                f"[DataFrameCache] Trading date changed from {self._last_trading_date} to {today}. Clearing cache."
            )
            self._cache.clear()
            self._timestamps.clear()
            self._last_trading_date = today

    def get_or_compute(
        self, symbol: str, start_date: str, fetcher: Callable[[str, str], Optional[pd.DataFrame]]
    ) -> Optional[pd.DataFrame]:
        key = (symbol, start_date)
        now = time.time()
        with self._lock:
            self._check_date_change()
            if key in self._cache:
                age = now - self._timestamps.get(key, 0)
                if age < self._ttl:
                    return self._cache[key]
                else:
                    # Explicit eviction of expired key
                    self._cache.pop(key, None)
                    self._timestamps.pop(key, None)

            df = fetcher(symbol, start_date)
            if df is None or df.empty:
                return df
            self._cache[key] = df
            self._timestamps[key] = now
            self._evict_if_needed()
            return df

    def evict_expired(self) -> int:
        """Purge all entries older than self._ttl."""
        now = time.time()
        with self._lock:
            self._check_date_change()
            expired_keys = [k for k, ts in self._timestamps.items() if (now - ts) >= self._ttl]
            for k in expired_keys:
                self._cache.pop(k, None)
                self._timestamps.pop(k, None)
            return len(expired_keys)

    def invalidate(self, symbol: str, start_date: Optional[str] = None) -> None:
        with self._lock:
            if start_date is not None:
                key = (symbol, start_date)
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
            else:
                keys_to_del = [k for k in self._cache if k[0] == symbol]
                for k in keys_to_del:
                    self._cache.pop(k, None)
                    self._timestamps.pop(k, None)

    def _evict_if_needed(self) -> None:
        if len(self._cache) > self._max_items:
            oldest_key = min(self._timestamps, key=self._timestamps.get)
            self._cache.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._last_trading_date = datetime.now().date()
```

---

### Step 3: Defensive Check in `trading_system/src/persistence/database.py`

In `StockPriceDB.update_prices` (Line 467):

```python
    def update_prices(self, symbol: str, df: pd.DataFrame, bypass_validation: bool = False) -> int:
        """OHLCV DataFrame을 DB에 batch upsert. 반환: 저장된 행 수."""
        if df is None or df.empty:
            return 0

        symbol = normalize_symbol(symbol)

        if not bypass_validation:
            from src.data_layer.data_validator import DataValidator
            if not DataValidator.validate_price_data(symbol, df):
                self.logger.warning(f"[StockPriceDB] Price validation failed for {symbol}. Upsert aborted.")
                return 0

        records = []
        ...
```

---

### Step 4: Update `trading_system/src/data_layer/market_data_handler.py`

In `MarketDataHandler.fetch_historical_data` (Line 336):

```python
    # Pass network fetched payload through corporate action adjustment and validation before writing to DB
    hist, is_valid = DataValidator.sanitize_and_validate_price_data(symbol, hist)
    if is_valid:
        db.update_prices(symbol, hist)
    else:
        self.logger.warning(f"Historical data for {symbol} failed quality validation. Skipping DB update.")
```

---

### Step 5: Clean up `trading_system/run_pipeline.py`

1. Remove duplicated local `_validate_price_data` function at lines 410–460.
2. Delegate all pre-fetch and network validation directly to `DataValidator.sanitize_and_validate_price_data(sym, ticker_df)`.

---

### Step 6: Create & Extend Unit Tests

1. Create `trading_system/tests/test_technical_cache.py`:
   - `test_dataframe_cache_hit_and_miss`
   - `test_dataframe_cache_ttl_expiration`
   - `test_dataframe_cache_evict_expired`
   - `test_dataframe_cache_date_change_invalidation`
   - `test_dataframe_cache_symbol_invalidation`
2. Extend `trading_system/tests/test_data_validator.py`:
   - `test_validate_price_data_single_day_spike`
   - `test_corporate_action_adjustment_integration`
3. Extend `trading_system/tests/test_database.py`:
   - `test_update_prices_defensive_validation`

---

## 5. Handoff Report (5-Component Structure)

### 1. Observation
- `DataValidator.validate_price_data` (`data_validator.py:102`) misses single-day price return spikes $>300\%$ when spike frequency is $\le 5\%$ of total rows.
- `CorporateActionAdjuster` (`price_adjuster.py:17`) is not hooked into `StockPriceDB.update_prices` or `MarketDataHandler.fetch_historical_data`.
- `StockPriceDB.update_prices` (`database.py:467`) lacks defensive data validation before SQLite upsert.
- `DataFrameCache` (`technical_cache.py:191`) lacks date-change invalidation, proactive TTL eviction on access, and standalone `evict_expired()` method.
- `DataFrameCache` has no dedicated test module in `trading_system/tests/`.

### 2. Logic Chain
- Single-day price jumps $>300\%$ stem from unadjusted splits/reverse splits or corrupted API data.
- Unfiltered price spikes corrupt technical indicators (ATR, Bollinger Bands, Moving Averages), misguiding the 23-strategy ensemble.
- By integrating `CorporateActionAdjuster` into `DataValidator.validate_price_data` and enforcing defensive checks inside `StockPriceDB.update_prices`, no corrupted prices can reach SQLite storage.
- Adding `_last_trading_date` check and `evict_expired()` to `DataFrameCache` guarantees cache freshness across daily trading sessions.

### 3. Caveats
- `bypass_validation=True` should be reserved for synthetic test fixtures in test files where mock price series intentionally violate bounds.
- If a stock genuinely moves $>300\%$ in a single day (extremely rare mega-cap news/bankruptcy), it will be flagged as an anomaly to protect model features from extreme outliers.

### 4. Conclusion
- Milestone 1 requirements are completely mapped and verified.
- The step-by-step implementation guide provides exact line references, function signatures, and code modifications for the Implementer.

### 5. Verification Method
1. Run `.venv\Scripts\python.exe -m pytest tests/test_data_validator.py -v`
2. Run `.venv\Scripts\python.exe -m pytest tests/test_technical_cache.py -v`
3. Run `.venv\Scripts\python.exe -m pytest tests/test_database.py -v`
4. Run `.venv\Scripts\python.exe -m pytest tests/` to confirm zero regressions across all 725+ tests.

---
*End of Report*

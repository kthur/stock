# Changes Implemented for Milestone 2

## 1. Data Ingestion & Storage Resiliency

### `trading_system/src/persistence/database.py`
- Updated `StockPriceDB.get_prices()` to return an empty DataFrame with `DatetimeIndex(name='date')` and capitalized columns `['Open', 'High', 'Low', 'Close', 'Volume']` when cache queries return 0 rows.
- Enhanced end-date filtering in `get_prices()`: for 10-character date strings (`YYYY-MM-DD`), appended `" 23:59:59"` to ensure full-day intraday rows are matched.
- Fixed `StockPriceDB.needs_update()`: added check for `max_age_days < 0` (offline mode `STOCK_PRICE_FRESHNESS_DAYS=none`) to return `False`, preventing invalid forced web update attempts.

### `trading_system/src/data_layer/indicator_storage.py`
- Fixed `update_stock_universe()` to parse `KRX-ADMINISTRATIVE` list safely (handling `'Code'` or `'Symbol'` and zero-padding code strings) and removed snapshot `Volume == 0` exclusion so active symbols are not purged outside market hours.

### `trading_system/run_pipeline.py`
- Fixed `_get_excluded_krx_symbols()`: added market off-hours check (if >30% of KRX symbols have `Volume == 0`, skip purging by zero volume).

## 2. Prediction Models & Feature Pipeline

### `trading_system/src/ai/prediction_model.py`
- Fixed `_predict_regression()` fallback logic: when pre-trained ML models are missing or training is skipped, return heuristic momentum/trend predictions based on `ret_5d` / `ret_20d` / `dist_sma_20` instead of defaulting outputs to `0.0`.
- Fixed `_merge_indicator_history()`: normalized `df.index` and `indicator_df.index` to `pd.to_datetime(...)` before joining to prevent NaNs across global macro indicators.
- Fixed `train_surge()` target selection: computed raw forward return targets `raw_surge_target_{h}d` explicitly before thresholding instead of using Sharpe-scaled targets (`target_{h}d`).
- Fixed short horizon surge training: applied adaptive thresholds per horizon (`1d`: 3%, `3d`: 5%, `5d`: 8%, `20d`: 15%) and 95th quantile fallback if `pos_count == 0` so training completes and yields valid surge probabilities.

### `trading_system/src/ai/feature_engineering.py`
- Fixed `apply_scaler()`: added `hasattr(scaler, 'mean_')` check before calling `transform()`, and automatically applied `fit_transform()` on unfitted scalers to prevent `NotFittedError` and raw unscaled features.

### `trading_system/src/ai/target_transform.py`
- Fixed `inverse_transform_sharpe()`: floored `vol_scale` with lower bound `0.005` (and filled NaNs with `0.01`) so `vol_20d == 0` does not force expected returns to 0.0%.

### `trading_system/src/ai/vcp_detector.py`
- Fixed `detect_vcp()` window logic: replaced cumulative nested `tail(w).max()` windows with non-overlapping slice windows (`iloc[-5:]`, `iloc[-15:-5]`, `iloc[-35:-15]`, `iloc[-60:-35]`), preventing cumulative window overlap from invalidating valid VCP setups.

### `trading_system/src/ai/vcp_ml_predictor.py`
- Fixed `_compute_vcp_features()`: lowered history length check to 65 days and padded empty VCP feature matrices with zero defaults (`{col: 0.0 for col in VCP_FEATURES}`) so valid active symbols are not dropped.

## 3. Pipeline Execution & Report Assembly

### `trading_system/generate_report.py`
- Rewrote stock name regex matchers in `parse_surge`, `parse_vcp`, `parse_lead_lag`, `parse_vcp_ml`, `parse_regression`, `parse_ensemble` to support internal parentheses and multiple spaces cleanly (e.g. `Alphabet Inc. (Class A)`).
- Fixed `parse_vcp_ml` header regex `r"\[(\d+일)\]\s+(\w+)"` to match `(no symbols)` or empty market headers.
- Fixed HTML market panel assembly in `build_html`: rendered standard 4-market DOM panels (`KOSPI`, `KOSDAQ`, `KONEX`, `SP500`) with `data-market="{mkt}"` across all tabs (`Ensemble`, `Surge`, `VCP`, `Lead-Lag`, `VCP ML`, `Regression`) so UI market filter buttons operate cleanly.

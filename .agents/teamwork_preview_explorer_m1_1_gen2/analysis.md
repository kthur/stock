# Detailed Analysis of Prediction Model Implementation

This report analyzes the seven issues identified in `trading_system/src/ai/prediction_model.py` and proposes concrete, robust fix strategies for each.

---

## Issue 1: Lookahead Leakage
### Observation
In `merge_fundamentals` (lines 193-253), fundamental data is merged into `df_prices` and then forward-filled:
```python
251:                 df[col] = df[col].ffill().fillna(meta[col])
```
If `df_prices` is sorted in descending chronological order (newest first), `ffill()` propagates data from the first rows (newest/future dates) to subsequent rows (older/past dates), causing lookahead leakage.

### Recommendation
Explicitly sort `df_prices` in ascending chronological order at the very beginning of `merge_fundamentals`.
```python
        # Ensure prices are sorted in ascending chronological order to prevent lookahead leakage in ffill()
        date_col = None
        for col in ['Date', 'date']:
            if col in df_prices.columns:
                date_col = col
                break
        
        if date_col is not None:
            df_sorted = df_prices.sort_values(by=date_col, ascending=True)
        elif df_prices.index.name in ['Date', 'date'] or isinstance(df_prices.index, pd.DatetimeIndex):
            df_sorted = df_prices.sort_index(ascending=True)
        else:
            df_sorted = df_prices.sort_index(ascending=True)
            
        df = df_sorted.copy()
```

---

## Issue 2: Row Duplication
### Observation
In `merge_fundamentals`, when merging the daily prices DataFrame `df` with the fundamentals DataFrame `df_fun`:
```python
232:                     df = pd.merge(df, df_fun, left_on='date_align', right_on='date', how='left')
```
If `df_fun` contains multiple entries for the same date (e.g. corrected updates), a `left` join duplicates the price rows for that date.

### Recommendation
Deduplicate `df_fun` by date/symbol (keeping the last entry) before performing the merge or join.
```python
            if df_fun is not None and not df_fun.empty:
                df_fun = df_fun.copy()
                df_fun['date'] = pd.to_datetime(df_fun['date'])
                
                # Drop duplicates by date/symbol, keeping the last record
                dup_cols = ['date']
                if 'symbol' in df_fun.columns:
                    dup_cols.append('symbol')
                df_fun = df_fun.sort_values(by=dup_cols).drop_duplicates(subset=dup_cols, keep='last')
```

---

## Issue 3: Duplicate Symbol Column
### Observation
If both `df` and `df_fun` contain a `'symbol'` column, merging them without key specification or column dropping causes pandas to generate duplicate columns `symbol_x` and `symbol_y`.

### Recommendation
Drop the `'symbol'` column from `df_fun` before merging, since `merge_fundamentals` operates on a single symbol context and already has the symbol parameter.
```python
                if 'symbol' in df_fun.columns:
                    df_fun = df_fun.drop(columns=['symbol'])
```

Combined code for Issues 2 & 3:
```python
            if df_fun is not None and not df_fun.empty:
                df_fun = df_fun.copy()
                df_fun['date'] = pd.to_datetime(df_fun['date'])
                
                # Drop symbol column from df_fun to avoid symbol_x and symbol_y columns
                if 'symbol' in df_fun.columns:
                    df_fun = df_fun.drop(columns=['symbol'])
                
                # Deduplicate fundamentals by date, keeping the last entry per date
                df_fun = df_fun.sort_values(by='date').drop_duplicates(subset=['date'], keep='last')
```

---

## Issue 4: KeyError on Partial Features
### Observation
In `predict_current` (lines 354-364):
```python
354:         if 'ret_1d' not in df_current.columns:
355:             norm_dict = self.apply_market_normalization({'TEMP': df_current})
356:             df_current = norm_dict['TEMP']
357:             df_current = self._create_features(df_current)
```
If `'ret_1d'` is present in `df_current.columns` but other features (e.g. `operating_margin` or `vol_20d`) are missing, the code skips the `_create_features` call. This leads to a `KeyError` when slicing `X = latest[features]`.

### Recommendation
Check if *all* 12 required features are present in the columns. If any feature is missing, compute or regenerate them.
```python
        # Check if all 12 required features are computed
        features = [
            'ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d',
            'norm_market_cap', 'norm_floating_value', 'norm_volume',
            'operating_margin', 'revenue_to_market_cap', 'dividend_yield'
        ]
        
        if not all(col in df_current.columns for col in features):
            norm_dict = self.apply_market_normalization({'TEMP': df_current})
            df_current = norm_dict['TEMP']
            df_current = self._create_features(df_current)
            if df_current.empty:
                return {h: 0.0 for h in self.horizons}
```

---

## Issue 5: Missing Columns
### Observation
In `apply_market_normalization` (line 116), market-cap and volume normalizations are calculated:
```python
143:             df_copy['market_cap'] = df_copy['Close'] * shares_out
```
If the input DataFrame is missing the `Close` or `Volume` columns, this operation will raise a `KeyError`.

### Recommendation
Check for the presence of `Close` and `Volume` columns at the start of `apply_market_normalization`'s processing loop. Log a warning and raise a clear `ValueError` if they are missing.
```python
            if 'Close' not in df_copy.columns or 'Volume' not in df_copy.columns:
                msg = f"Input DataFrame for symbol '{sym}' is missing required 'Close' or 'Volume' columns."
                logger.warning(msg)
                raise ValueError(msg)
```

---

## Issue 6: Constant/Halted Prices dropna
### Observation
In `_create_features` (lines 278-293), technical indicator returns and volatilities are calculated:
```python
279:         df['ret_1d'] = df['Close'].pct_change(1)
...
290:         df['vol_20d'] = df['ret_1d'].rolling(20).std()
291: 
292:         # Drop NaN
293:         df.dropna(inplace=True)
```
If the stock is halted or has constant price, the return/volatility columns may contain NaNs. When `df.dropna()` is called, these rows (which may include the latest row) are dropped entirely.

### Recommendation
Fill NaNs in the return and volatility columns with `0.0` before running `dropna()`.
```python
        # Fill NaNs in return and volatility columns with 0.0 before dropping NaNs
        fill_cols = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'vol_20d']
        for col in fill_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0.0)
                
        # Drop NaN (drops remaining NaNs, e.g. from moving average warmup)
        df.dropna(inplace=True)
```

---

## Issue 7: Stale Prediction Warning
### Observation
If the latest row of the DataFrame is dropped during feature calculation (e.g. due to other invalid features), the model will predict on a stale day without notifying the system.

### Recommendation
In `predict_current`, compare the latest date of the input DataFrame before and after feature calculation. Log a warning if the latest date changed or was dropped.
```python
        # Store the latest date from the input DataFrame
        latest_date_before = df_current.index[-1] if not df_current.empty else None
        
        # Check if all 12 required features are computed
        ...
        
        # Check if the latest row was dropped during feature calculation
        if latest_date_before is not None:
            latest_ts_before = pd.to_datetime(latest_date_before)
            latest_ts_after = pd.to_datetime(df_current.index[-1]) if not df_current.empty else None
            
            if latest_ts_after is None or latest_ts_after != latest_ts_before:
                logger.warning(
                    f"Latest row with timestamp {latest_date_before} was dropped during feature calculation. "
                    f"Predicting on a stale day ({df_current.index[-1] if not df_current.empty else 'N/A'})."
                )
```

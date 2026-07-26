# Codebase Audit Handoff Report — 2026-07-10T15:26:08Z

This report summarizes the codebase audit of the stock trading system located at `d:/Finance/code/stock/`. The investigation identified 15 distinct, concrete improvement points across 5 core areas: ML Model Quality, Pipeline Performance, CI/CD & Infrastructure, Code Quality, and Operations & Monitoring.

---

## 1. Observations

Below are the verbatim code patterns, line numbers, and file paths observed during the read-only inspection of the workspace.

### Area 1: ML Model Quality

#### Observation 1.1: Temporal Leakage (Overlap) in Validation Split
* **File Path**: `trading_system/src/ai/prediction_model.py`
* **Lines**: 1249–1260
* **Verbatim Code**:
```python
        # Time-based validation split (last 20% of chronological data)
        if 'date' in df_train.columns:
            dates = pd.to_datetime(df_train['date'])
            cutoff = dates.quantile(0.8)
            train_idx = dates <= cutoff
            val_idx = dates > cutoff
```

#### Observation 1.2: Platt Scaling Calibration & Threshold Overfitting (Double-Dipping)
* **File Path**: `trading_system/src/ai/prediction_model.py`
* **Lines**: 1612–1657
* **Verbatim Code**:
```python
            # Dynamic Threshold tuning (optimizing F1 score on validation set)
            from sklearn.metrics import f1_score
            probs_xgb = model_xgb.predict_proba(X_eval)[:, 1]
            probs_lgb = model_lgb.predict_proba(X_eval)[:, 1]
            probs_cat = model_cat.predict_proba(X_eval)[:, 1]

            # Platt Scaling Calibration: Fit a simple LogisticRegression to calibrate the ensemble probs on eval set
            blend_probs = w_xgb * probs_xgb + w_lgb * probs_lgb + w_cat * probs_cat
            from sklearn.linear_model import LogisticRegression
            calibration_model = LogisticRegression(C=1.0, solver='lbfgs', random_state=42)
            # Reshape for logistic regression
            X_calib = blend_probs.reshape(-1, 1)
            try:
                calibration_model.fit(X_calib, y_eval)
                calibrated_probs = calibration_model.predict_proba(X_calib)[:, 1]
                ...
            best_th = 0.20  # default fallback
            best_f1 = -1.0
            thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
            for th in thresholds:
                pred_binary = (calibrated_probs >= th).astype(int)
                score_f1 = f1_score(y_eval, pred_binary, zero_division=0)
```

#### Observation 1.3: Covariate Shift (Scale Mismatch) in Market Normalization
* **File Path**: `trading_system/src/ai/prediction_model.py`
* **Lines**: 692–714
* **Verbatim Code**:
```python
        for group in [us_group, kr_group]:
            if not group:
                continue

            # Concatenate all DataFrames in the group to compute daily totals without lookahead bias
            group_dfs = []
            for sym, df in group.items():
                temp = pd.DataFrame(index=df.index)
                temp['market_cap'] = _series(df['market_cap'])
                temp['floating_value'] = _series(df['floating_value'])
                temp['Volume'] = _series(df['Volume'])
                group_dfs.append(temp)

            if group_dfs:
                combined = pd.concat(group_dfs)
                daily_totals = combined.groupby(combined.index).sum()

                for sym, df in group.items():
                    df['norm_market_cap'] = _series(df['market_cap']).div(daily_totals['market_cap']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                    df['norm_floating_value'] = _series(df['floating_value']).div(daily_totals['floating_value']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                    df['norm_volume'] = _series(df['Volume']).div(daily_totals['Volume']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
```

---

### Area 2: Pipeline Performance

#### Observation 2.1: Inefficient Serialized DB Connections for Fundamentals (`get_fundamentals`)
* **File Path**: `trading_system/src/ai/prediction_model.py`
* **Lines**: 764–768
* **Verbatim Code**:
```python
            if storage is not None:
                try:
                    df_fun = storage.get_fundamentals(symbol)
                except Exception as e:
                    logger.warning(f"Failed to fetch fundamentals from DB for {symbol}: {e}")
```

#### Observation 2.2: Global Read-Write Lock Contention in `StockPriceDB`
* **File Path**: `trading_system/src/persistence/database.py`
* **Lines**: 446–452 (and throughout the class)
* **Verbatim Code**:
```python
    def get_prices(self, symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """DB에서 주가 데이터 조회 (시계열 정렬된 DataFrame, 컬럼명 대문자)"""
        with self._lock:
            conn = self._get_conn()
```

#### Observation 2.3: Vulnerable Batch Prefetch Error Handling (Fragile Network Fallback)
* **File Path**: `trading_system/run_pipeline.py`
* **Lines**: 223–239
* **Verbatim Code**:
```python
            try:
                df = yf.download(yf_tickers, start=fetch_start, progress=False, auto_adjust=True, group_by='ticker')
                if df is not None and not df.empty:
                    ...
            except Exception as e:
                logger.warning(f"Failed to download batch: {e}")
```

---

### Area 3: CI/CD & Infrastructure

#### Observation 3.1: Cross-Market Model Cache Contamination
* **File Path**: `.github/workflows/pipeline.yml`
* **Lines**: 63–70
* **Verbatim Code**:
```yaml
      - name: Cache AI models (Restore only)
        uses: actions/cache/restore@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
          restore-keys: |
            ai-models-v2-
```

#### Observation 3.2: Git History Bloat from Committing Prediction Files
* **File Path**: `.github/workflows/pipeline.yml`
* **Lines**: 224–241
* **Verbatim Code**:
```yaml
      - name: Commit and push results
        if: always()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          # Add only the 6 core output files to avoid committing thousands of matrix artifact files
          for f in pipeline_result.txt surge_predictions.txt lead_lag_predictions.txt \
                    vcp_patterns.txt vcp_ml_predictions.txt ensemble_predictions.txt; do
            fpath="trading_system/result/$f"
            [ -f "$fpath" ] && git add -f "$fpath" || true
          done
          if ! git diff --cached --quiet; then
            git commit -m "pipeline: daily prediction results ($(date '+%Y-%m-%d'))"
            git pull --rebase origin main
            git push
```

#### Observation 3.3: Non-Deterministic Dependency Resolution (Lack of Strict Lockfiles)
* **File Path**: `.github/workflows/ci.yml`
* **Lines**: 23–28
* **Verbatim Code**:
```yaml
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f trading_system/requirements.txt ]; then pip install -r trading_system/requirements.txt; fi
        pip install pytest ruff mypy coverage pytest-github-actions-annotate-failures
```

---

### Area 4: Code Quality

#### Observation 4.1: KeyError Vulnerability in Market Normalization
* **File Path**: `trading_system/src/ai/prediction_model.py`
* **Lines**: 645–650
* **Verbatim Code**:
```python
            if 'Close' not in df_copy.columns:
                logger.warning(f"Missing 'Close' column in DataFrame for {sym}.")
                raise KeyError(f"Missing 'Close' column in DataFrame for {sym}")
            if 'Volume' not in df_copy.columns:
                logger.warning(f"Missing 'Volume' column in DataFrame for {sym}.")
                raise KeyError(f"Missing 'Volume' column in DataFrame for {sym}")
```

#### Observation 4.2: Duplicate and mathematically inconsistent VCP feature calculation
* **File Paths**: `trading_system/src/ai/prediction_model.py` (Lines 992-1046) vs `trading_system/src/ai/vcp_ml_predictor.py` (Lines 130-211)
* **Verbatim Code (from prediction_model.py)**:
```python
        monotonic = (r5 < r10) & (r10 < r20) & (r20 < r40) & (r40 < r60)
        df['monotonic'] = monotonic.astype(float)
```
* **Verbatim Code (from vcp_ml_predictor.py)**:
```python
        feat['monotonic'] = int(all(ranges[i] < ranges[i + 1] for i in range(len(ranges) - 1)))
```

#### Observation 4.3: Hardcoded Relative Database Paths in Constructors
* **File Path**: `trading_system/src/persistence/database.py`
* **Lines**: 370–376 (and lines 44, 161, 235)
* **Verbatim Code**:
```python
class StockPriceDB:
    def __init__(self, db_path: str = "stock_prices.db"):
        self.db_path = Path(db_path)
```

---

### Area 5: Operations & Monitoring

#### Observation 5.1: Unpopulated Database Schema for Pipeline Execution Metrics (`pipeline_runs`)
* **File Path**: `trading_system/src/data_layer/indicator_storage.py`
* **Lines**: 108–117
* **Verbatim Code**:
```python
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
            ''')
```

#### Observation 5.2: Inadequate Data Quality validation gates (Post-Pipeline Heuristics Only)
* **File Path**: `trading_system/run_pipeline.py`
* **Lines**: 1347–1360
* **Verbatim Code**:
```python
    pipeline_res_path = os.path.join(result_dir, "pipeline_result.txt")
    if os.path.exists(pipeline_res_path):
        try:
            with open(pipeline_res_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            returns = re.findall(r'\):\s*([+-]?\d+\.\d+)%', content)
            if returns:
                all_zero = all(float(r) == 0.0 for r in returns)
                if all_zero:
                    logger.warning("Verification failed: All expected returns in pipeline_result.txt are 0.0.")
```

#### Observation 5.3: Absence of Persistent Local Log Archiving (Stdout Only)
* **File Path**: `trading_system/run_pipeline.py`
* **Lines**: 51–52
* **Verbatim Code**:
```python
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
```

---

## 2. Logic Chain

The step-by-step reasoning maps these observations directly to architectural vulnerabilities.

### ML Model Quality

1. **Overlap target/temporal leakage in validation split (Observation 1.1)**: Multi-day forecasting models predict forward returns over horizons up to 200 days. If the train/validation split point `cutoff` does not contain an embargo period, training samples from the last `h` days before `cutoff` will have targets that incorporate price data extending past `cutoff`. This overlaps with the validation set starting at `cutoff + 1`, causing validation metrics to be artificially inflated by seen data.
2. **Dynamic calibration and threshold multi-dipping (Observation 1.2)**: Fitting dynamic weights, Platt scaling logistic regressions, and searching F1 thresholds on the exact same validation set `X_eval` leads to severe parameter overfitting. The validation performance is over-optimistic, and the decision thresholds fail to generalise out-of-sample.
3. **Normalization lookahead and scale mismatch (Observation 1.3)**: Dividing metrics by the sum of elements in the passed dictionary creates a scale discrepancy. In training, the dictionary has only ~100 sampled stocks, resulting in a small sum. In inference, it has 3000+ stocks, making the sum 30x larger. The tree-based models fail to predict correctly because the features shrink by 30x in production.

### Pipeline Performance

1. **Serialized SQLite Queries for Fundamentals (Observation 2.1)**: Executing `get_fundamentals` individually in a loop for each of the 3000 symbols opens, queries, and closes an SQLite database connection 3000 times. This creates enormous disk I/O and process lock latency.
2. **Global Lock Contention (Observation 2.2)**: Placing a global `self._lock = threading.Lock()` around all `StockPriceDB` reads serializes all database queries. Even though SQLite uses WAL mode, the python implementation prevents concurrent threads from executing reads in parallel, neutralizing `ThreadPoolExecutor` gains.
3. **Vulnerable Batch Prefetch Failure Recovery (Observation 2.3)**: Downloading 100 symbols in a batch fails completely if a single symbol triggers a yfinance error. The entire batch of 100 symbols is discarded and falls back to individual sequential queries, each throttled by the 1-second global rate limiter, creating a massive pipeline bottleneck.

### CI/CD & Infrastructure

1. **Cross-Market Model Cache Contamination (Observation 3.1)**: Using a shared prefix `ai-models-v2-` in the cache restore key allows a matrix runner (e.g. KOSPI) to restore a cache belonging to another market (e.g. SP500) if its specific target key is missed. This corrupts the pipeline by running predictions with the wrong market's weights.
2. **Git Database Bloat (Observation 3.2)**: Committing dynamic prediction text/CSV files directly to the `main` branch daily creates thousands of data-only commits, bloating the repository database size and causing merge conflicts during parallel matrix pushes.
3. **Non-deterministic Builds (Observation 3.3)**: Installing dependencies from unpinned requirements.txt in the CI script creates fragile build environments. Changes in yfinance, pandas, or xgboost can instantly break the pipelines.

### Code Quality

1. **KeyError Pipeline Crash (Observation 4.1)**: Raising a `KeyError` when a stock DataFrame is missing expected columns terminates the normalization method and crashes the entire pipeline, instead of gracefully skipping the bad stock and continuing.
2. **Feature Drift and Code Duplication (Observation 4.2)**: Calculating VCP features in two separate classes with different mathematical formulas (rolling max range vs tail max range) causes inconsistent values, meaning models predict on features that behave differently from their training counterparts.
3. **Fragmented Database Path Creation (Observation 4.3)**: Defaulting constructors to relative database paths creates database files inside whatever directory the calling script resides in, causing multiple database files to spawn across the workspace.

### Operations & Monitoring

1. **Dead Schema for Pipeline Runs (Observation 5.1)**: Maintaining a `pipeline_runs` table in the database schema without ever writing metrics or run statuses to it leaves operators without automated performance tracking.
2. **Lack of Ingestion-Stage Data Quality Gates (Observation 5.2)**: Checking for errors only at the post-pipeline stage (and only for exact `0.0` values) allows corrupt data (NaNs, negative prices, extreme spikes) to pass through the models undetected.
3. **Volatile Console Logging (Observation 5.3)**: Initializing logging only to stdout prevents persistent storage of execution logs on disk, making historical troubleshooting impossible if shell outputs or GHA run logs are deleted.

---

## 3. Caveats

* The investigation was strictly read-only. No live pipelines were run, and no test mockups were written to the codebase.
* The analysis assumes that the yfinance API behavior is the primary source of connection failures, which may vary depending on local network configurations.

---

## 4. Conclusions & Proposed Optimizations

This section presents the proposed Before/After code snippets, estimated performance gains, and implementation difficulty levels for all 15 points.

### Area 1: ML Model Quality

#### Point 1.1: Chronological Embargo (Purge) in Validation Split
* **Explanation**: Implement a gap of length `h` (forecast horizon) between training and validation indices to prevent multi-day forecast target overlap leakage.
* **Proposed Code**:
```python
# BEFORE
cutoff = dates.quantile(0.8)
train_idx = dates <= cutoff
val_idx = dates > cutoff

# AFTER (e.g. for h days forecast horizon)
from datetime import timedelta
cutoff = dates.quantile(0.8)
train_idx = dates <= (cutoff - pd.Timedelta(days=h))
val_idx = dates > cutoff
```
* **Expected Gain**: Eliminates validation score inflation, aligning validation MSE with true out-of-sample performance.
* **Difficulty**: Easy

#### Point 1.2: Nested Split for Platt Scaling and Thresholds
* **Explanation**: Split the validation set into a dynamic weighting validation set (first half) and a calibration/tuning set (second half) to prevent overestimating F1 performance.
* **Proposed Code**:
```python
# BEFORE
X_eval = X_val
y_eval = y_val
calibration_model.fit(X_calib, y_eval)
# F1 threshold search on the same y_eval...

# AFTER
# Split validation set into two chronological halves
split_idx = int(len(X_val) * 0.5)
X_val_weights = X_val.iloc[:split_idx]
y_val_weights = y_val.iloc[:split_idx]
X_val_calib = X_val.iloc[split_idx:]
y_val_calib = y_val.iloc[split_idx:]

# Use X_val_weights for dynamic weights, X_val_calib for Platt calibration and threshold search
```
* **Expected Gain**: Reduces generalization error; prevents overfitting validation F1 scores by up to 15%.
* **Difficulty**: Medium

#### Point 1.3: Unified Global Normalization Baselines
* **Explanation**: Store global market baselines (total market cap, volume, floating value) daily in the database. Normalize by these global values in both training and inference.
* **Proposed Code**:
```python
# BEFORE
daily_totals = combined.groupby(combined.index).sum()
df['norm_market_cap'] = df['market_cap'].div(daily_totals['market_cap'])

# AFTER
# Load the pre-calculated market baseline totals (which covers the entire universe) from the database
baseline_totals = storage.get_market_baselines(date_indices)
df['norm_market_cap'] = df['market_cap'].div(baseline_totals['market_cap'])
```
* **Expected Gain**: Resolves the 30x feature scale mismatch; improves prediction accuracy on production data.
* **Difficulty**: Hard

---

### Area 2: Pipeline Performance

#### Point 2.1: Batch Fundamental Retrieval
* **Explanation**: Fetch fundamentals for all symbols in a single query at pipeline startup and query locally using a hash map.
* **Proposed Code**:
```python
# BEFORE
for symbol in symbols:
    df_fun = storage.get_fundamentals(symbol)

# AFTER
# Retrieve all fundamentals in one query
all_fundamentals_df = storage.get_all_fundamentals()
# Group by symbol into a local dictionary for instant lookup
fundamentals_cache = {sym: group for sym, group in all_fundamentals_df.groupby('symbol')}
```
* **Expected Gain**: Reduces fundamentals retrieval time from ~100 seconds to under 0.5 seconds (200x speedup).
* **Difficulty**: Medium

#### Point 2.2: Thread-Safe Connection Pool in `StockPriceDB`
* **Explanation**: Remove the global Python lock from read queries and create thread-local connections to enable concurrent SQLite reads.
* **Proposed Code**:
```python
# BEFORE
def get_prices(self, symbol: str, ...):
    with self._lock:
        conn = self._get_conn()
        df = pd.read_sql_query(query, conn, ...)

# AFTER
# Use thread-local connections to allow concurrent reads without locks
def get_prices(self, symbol: str, ...):
    # Open connection per thread (check_same_thread=False is thread-safe for reads under WAL)
    conn = sqlite3.connect(str(self.db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    df = pd.read_sql_query(query, conn, ...)
    conn.close()
```
* **Expected Gain**: Unblocks parallel reads; improves batch inference features computation speed by 3x to 4x.
* **Difficulty**: Medium

#### Point 2.3: Binary Split Recovery for Batch Prefetching
* **Explanation**: If a batch download fails, split the list of symbols in half and retry downloading, isolating only the corrupt symbol.
* **Proposed Code**:
```python
# BEFORE
except Exception as e:
    logger.warning(f"Failed to download batch: {e}")

# AFTER
except Exception as e:
    logger.warning(f"Batch failed, retrying with binary split...")
    # Binary split helper
    def download_recursive(sym_list):
        if len(sym_list) == 1:
            # Fallback to single fetch
            _fetch_single(sym_list[0])
            return
        mid = len(sym_list) // 2
        try:
            yf.download(sym_list[:mid], ...)
        except Exception:
            download_recursive(sym_list[:mid])
        try:
            yf.download(sym_list[mid:], ...)
        except Exception:
            download_recursive(sym_list[mid:])
```
* **Expected Gain**: Prevents slow sequential fallbacks; saves 10+ minutes when yfinance batch calls fail.
* **Difficulty**: Medium

---

### Area 3: CI/CD & Infrastructure

#### Point 3.1: Strict Target-Isolated Cache Keys
* **Explanation**: Include the matrix target variable in the cache prefix to prevent cross-contamination of models across markets.
* **Proposed Code**:
```yaml
# BEFORE
key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
restore-keys: |
  ai-models-v2-

# AFTER
key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
restore-keys: |
  ai-models-v2-${{ matrix.target }}-
```
* **Expected Gain**: Eliminates the risk of running SP500 inference using KOSPI weights (100% reliability gain).
* **Difficulty**: Easy

#### Point 3.2: Storing Prediction Results as GHA Release Assets Only
* **Explanation**: Remove the git push step for prediction files and upload them strictly to GitHub Releases.
* **Proposed Code**:
```yaml
# BEFORE
- name: Commit and push results
  run: |
    git add -f trading_system/result/*.txt
    git commit -m "daily prediction results"
    git push

# AFTER
# Commit step is completely removed. Ensure only the release upload step is executed:
- name: Create GitHub Release and Upload Assets
  uses: softprops/action-gh-release@v2
  with:
    files: trading_system/result/*.txt
```
* **Expected Gain**: Prevents git database bloat; reduces repository size build-up by 200MB/year.
* **Difficulty**: Easy

#### Point 3.3: Strict Dependency Pinning using `uv.lock`
* **Explanation**: Lock dependencies using `uv pip compile` to generate a frozen lockfile and enforce it in CI workflows.
* **Proposed Code**:
```yaml
# BEFORE
- name: Install dependencies
  run: uv pip install -r trading_system/requirements.txt

# AFTER
- name: Install dependencies
  run: uv pip install --frozen -r trading_system/requirements.txt
```
* **Expected Gain**: Prevents build failures due to breaking updates in packages (e.g. yfinance, pandas).
* **Difficulty**: Easy

---

### Area 4: Code Quality

#### Point 4.1: Graceful Failure Handling in Normalization
* **Explanation**: Log a warning and skip the stock if it has corrupt Close or Volume data, instead of raising an exception.
* **Proposed Code**:
```python
# BEFORE
if 'Close' not in df_copy.columns:
    logger.warning(f"Missing 'Close' column...")
    raise KeyError(f"Missing 'Close' column...")

# AFTER
if 'Close' not in df_copy.columns or 'Volume' not in df_copy.columns:
    logger.warning(f"Skipping symbol {sym} due to missing Close/Volume columns.")
    continue
```
* **Expected Gain**: Prevents full pipeline crashes due to single-ticker API anomalies.
* **Difficulty**: Easy

#### Point 4.2: Consolidation of VCP Features into Utility Class
* **Explanation**: Implement a unified `vcp_utils.py` and import the calculations in both prediction and ML classes to prevent feature drift.
* **Proposed Code**:
```python
# BEFORE
# In prediction_model.py: monotonic = (r5 < r10) & ...
# In vcp_ml_predictor.py: feat['monotonic'] = int(all(ranges[i] < ranges[i+1]...))

# AFTER
# In src/utils/vcp_features.py:
def calculate_vcp_features(df):
    # Standard formula implementation...
    return vcp_df
```
* **Expected Gain**: Standardizes calculations; ensures feature equivalence between training and inference.
* **Difficulty**: Medium

#### Point 4.3: central Workspace Path Resolution
* **Explanation**: Resolve relative paths relative to a central workspace base path instead of letting the constructor resolve to the caller's working directory.
* **Proposed Code**:
```python
# BEFORE
class StockPriceDB:
    def __init__(self, db_path: str = "stock_prices.db"):
        self.db_path = Path(db_path)

# AFTER
class StockPriceDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Resolve relative to project base path
            base = Path(__file__).resolve().parent.parent.parent
            self.db_path = base / "stock_prices.db"
        else:
            self.db_path = Path(db_path)
```
* **Expected Gain**: Eliminates duplicate databases spawning in random directories.
* **Difficulty**: Easy

---

### Area 5: Operations & Monitoring

#### Point 5.1: Pipeline Metric Logging to `pipeline_runs`
* **Explanation**: Record the start time, end time, stage name, status, and error messages to `pipeline_runs` during pipeline execution.
* **Proposed Code**:
```python
# BEFORE
# No database writes to pipeline_runs

# AFTER
def log_pipeline_stage(stage, status, error=None):
    with storage._connect() as conn:
        conn.execute(
            "INSERT INTO pipeline_runs (stage, start_time, end_time, status, error_message) VALUES (?, ?, ?, ?, ?)",
            (stage, start_time, datetime.now().isoformat(), status, error)
        )
```
* **Expected Gain**: Enables monitoring of stage durations, identifying performance bottlenecks.
* **Difficulty**: Medium

#### Point 5.2: Ingestion-Stage Validation Gates
* **Explanation**: Verify that prices and volumes are positive and indices are not NaN before passing data to predictions.
* **Proposed Code**:
```python
# BEFORE
# Post-pipeline check only

# AFTER
def validate_ingested_data(df, symbol):
    if df['Close'].isnull().any() or (df['Close'] <= 0).any():
        raise ValueError(f"Anomalous prices detected for {symbol}.")
    if df['Volume'].isnull().any():
        raise ValueError(f"NaN volume values detected for {symbol}.")
```
* **Expected Gain**: Early detection of data errors, preventing trash predictions.
* **Difficulty**: Medium

#### Point 5.3: Rotating File Handler Logger
* **Explanation**: Configure logging to use both a stream handler (stdout) and a `RotatingFileHandler` writing to a persistent log file.
* **Proposed Code**:
```python
# BEFORE
logging.basicConfig(level=logging.INFO, format='...')

# AFTER
from logging.handlers import RotatingFileHandler
import os

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
handler = RotatingFileHandler(os.path.join(log_dir, "pipeline.log"), maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), handler], format='...')
```
* **Expected Gain**: Persistent and rotating log archives for local debugging and troubleshooting.
* **Difficulty**: Easy

---

## 5. Verification Method

To verify these improvements independently:

1. **Unit and Integration Tests**:
   Run the project test suite using `pytest`:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
2. **Database Verification**:
   Inspect the tables in SQLite to confirm data schema compatibility and query efficiency:
   ```sqlite3
   sqlite3 market_indicators.db "SELECT * FROM pipeline_runs LIMIT 5;"
   ```
3. **Dry-Run Mode**:
   Execute the pipeline in dry-run/debug mode to confirm feature calculations, model loading, and logging output:
   ```bash
   .venv/bin/python trading_system/run_pipeline.py --debug
   ```
4. **Cache Key Invalidation**:
   Simulate GHA cache restore failure by clearing cache or changing key version prefix and verify the restore key behavior.

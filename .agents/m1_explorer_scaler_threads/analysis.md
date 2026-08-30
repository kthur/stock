# Technical Analysis & Implementation Specification: Scaler Caching & Dynamic ML Thread Allocation

## Executive Summary

This investigation provides the complete technical analysis, architectural design, exact code specifications, and test verification suite for two critical Milestone 1 performance enhancements:
1. **Thread-Safe In-Memory Scaler Caching (`src/ai/feature_engineering.py`)**: Eliminates 45+ redundant `.joblib` disk read operations per inference cycle by integrating an `@functools.lru_cache(maxsize=128)` layer with automatic cache invalidation and argument normalization.
2. **Dynamic ML Intra-Thread Allocation (`src/ai/prediction_model.py` & `run_pipeline.py`)**: Eliminates CPU thread oversubscription and thrashing during multi-market parallel training by dynamically calculating $\text{intra\_n\_jobs} = \max(1, \text{cpu\_count} // \text{\_train\_workers})$ and setting `n_jobs` (XGBoost/LightGBM) and `thread_count` (CatBoost).

---

## 1. Scope 1: Scaler Caching Architecture (`src/ai/feature_engineering.py`)

### 1.1 Problem Analysis & Bottleneck Identification

During each end-to-end inference pass across 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`):
- `OnDevicePredictionModel._predict_regression` (`src/ai/prediction_model.py:2495`) iterates over all 9 prediction horizons ($h \in [1, 2, 3, 5, 10, 20, 60, 120, 200]$) and each market partition.
- In `src/ai/feature_engineering.py:35-43`, `load_scaler(model_dir, market, horizon)` executes `joblib.load(scaler_path)` directly against the filesystem on every invocation.
- For 5 markets and 9 horizons, this produces $5 \times 9 = 45$ un-cached disk read and pickle deserialization cycles per inference batch.
- When 16 to 32 I/O worker threads or batch inference processes execute concurrently, un-cached disk reads cause storage I/O queue buildup and CPU overhead.

### 1.2 Architectural Design

To solve this with zero regressions and absolute thread safety:
1. **LRU Caching Core**: Implement `@functools.lru_cache(maxsize=128)` on an internal normalized function `_load_scaler_cached(norm_model_dir: str, market: str, horizon: int) -> StandardScaler`.
2. **Argument Normalization**: `load_scaler` normalizes input types and path variations:
   - `norm_model_dir = os.path.normpath(str(model_dir)) if model_dir else ""`
   - `norm_market = str(market).lower()`
   - `norm_horizon = int(horizon)`
   This guarantees identical cache keys regardless of whether callers pass `Path("models")` vs `str("models")`, `"SP500"` vs `"sp500"`, or integer/float horizon values.
3. **Thread Safety**: CPython's `functools.lru_cache` wrapper uses internal C-level mutex locks around dictionary lookups and doubly-linked list updates, providing guaranteed thread-safety across concurrent reader/worker threads.
4. **Cache Invalidation Lifecycle**:
   - Provide `clear_scaler_cache() -> None` calling `_load_scaler_cached.cache_clear()`.
   - Hook `clear_scaler_cache()` into `fit_scaler(...)` within a `finally:` block so that whenever a model retrains and dumps a new scaler, stale in-memory objects are immediately evicted.
5. **Cache Telemetry**: Expose `get_scaler_cache_info()` returning `_load_scaler_cached.cache_info()` (`hits`, `misses`, `maxsize`, `currsize`) for testing and pipeline profiling.

### 1.3 Exact Proposed Implementation (`src/ai/feature_engineering.py`)

```python
import functools
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

# Canonical list of VCP feature column names produced by compute_vcp_features()
VCP_FEATURES = [
    'range_5v20', 'range_10v20', 'range_20v40', 'range_40v60',
    'vol_20v60', 'dist_ma50', 'dist_ma200',
    'range_pos_10d', 'range_pos_20d', 'atr_14d_norm', 'monotonic', 'vcp_score',
]

def get_scaler_path(model_dir: str, market: str, horizon: int) -> str:
    """Construct canonical scaler file path for a given market and horizon."""
    return os.path.join(model_dir, f"scaler_{market}_{horizon}d.joblib")

def fit_scaler(df: pd.DataFrame, features: list, model_dir: str, market: str, horizon: int) -> StandardScaler:
    """Fit a StandardScaler on training features, persist to disk, and invalidate cache."""
    scaler = StandardScaler()
    # Fill remaining NaNs with 0 before scaling to ensure safety
    X = df[features].replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(lower=-1e9, upper=1e9)
    scaler.fit(X)

    os.makedirs(model_dir, exist_ok=True)
    scaler_path = os.path.normpath(get_scaler_path(model_dir, market, horizon))
    try:
        joblib.dump(scaler, scaler_path)
        logger.info(f"Saved feature scaler for {market} {horizon}d to {scaler_path}")
    except Exception as e:
        logger.warning(f"Failed to save scaler to {scaler_path}: {e}")
    finally:
        # Invalidate in-memory scaler cache so newly trained scaler is immediately loaded
        clear_scaler_cache()
    return scaler

@functools.lru_cache(maxsize=128)
def _load_scaler_cached(norm_model_dir: str, market: str, horizon: int) -> StandardScaler:
    """Internal thread-safe LRU-cached loader for StandardScaler artifacts."""
    scaler_path = os.path.normpath(get_scaler_path(norm_model_dir, market, horizon))
    if os.path.exists(scaler_path):
        try:
            return joblib.load(scaler_path)
        except Exception as e:
            logger.warning(f"Failed to load scaler from {scaler_path}: {e}")
    logger.warning(f"Scaler not found at {scaler_path}. Returning default StandardScaler.")
    return StandardScaler()

def load_scaler(model_dir: str, market: str, horizon: int) -> StandardScaler:
    """Public thread-safe LRU-cached loader for StandardScaler artifacts with normalized keys."""
    norm_dir = os.path.normpath(str(model_dir)) if model_dir else ""
    return _load_scaler_cached(norm_dir, str(market).lower(), int(horizon))

def clear_scaler_cache() -> None:
    """Clear in-memory LRU cache for loaded scalers."""
    _load_scaler_cached.cache_clear()

def get_scaler_cache_info():
    """Return cache statistics (hits, misses, maxsize, currsize) for monitoring."""
    return _load_scaler_cached.cache_info()

def apply_scaler(df: pd.DataFrame, features: list, scaler: StandardScaler) -> pd.DataFrame:
    if df.empty:
        return df
    df_copy = df.copy()
    for col in features:
        if col not in df_copy.columns:
            df_copy[col] = 0.0
    X = df_copy[features].copy()
    for c in features:
        if c in X.columns:
            X[c] = pd.to_numeric(X[c], errors='coerce')
    X = X.replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(lower=-1e9, upper=1e9)
    if hasattr(scaler, 'mean_') and scaler.mean_ is not None:
        try:
            # R8-1 Fix: Reindex to scaler.feature_names_in_ if available to avoid feature mismatch exceptions
            if hasattr(scaler, 'feature_names_in_') and scaler.feature_names_in_ is not None:
                X_aligned = X.reindex(columns=scaler.feature_names_in_, fill_value=0.0)
                scaled_values = scaler.transform(X_aligned)
            else:
                scaled_values = scaler.transform(X)
            df_copy[features] = scaled_values
        except Exception as e:
            # Avoid calling fit_transform on single-row inference (which zeroes out all features)
            if len(X) > 10:
                logger.warning(f"Failed to apply scaling: {e}. Fitting on current batch data.")
                scaled_values = scaler.fit_transform(X)
                df_copy[features] = scaled_values
            else:
                logger.warning(f"Failed to apply scaling: {e}. Preserving raw features for single-row inference.")
    else:
        try:
            if len(X) > 10:
                scaled_values = scaler.fit_transform(X)
                df_copy[features] = scaled_values
        except Exception as e:
            logger.warning(f"Failed to fit_transform scaler: {e}. Using raw features.")
    df_copy[features] = df_copy[features].replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(lower=-1e9, upper=1e9)
    return df_copy
```

---

## 2. Scope 2: Dynamic ML Thread Allocation (`src/ai/prediction_model.py` & `run_pipeline.py`)

### 2.1 Problem Analysis & Mathematical Formulation

In `run_pipeline.py:1726-1760`:
```python
_train_workers = max(1, min(4, _CPU_WORKERS))
with ThreadPoolExecutor(max_workers=_train_workers) as pool:
    for m_name, m_df in market_dfs.items():
        futures[pool.submit(model.train, m_df, market=m_name, save_after=True)] = m_name
```
In `src/ai/prediction_model.py:260, 271, 280, 296, 310, 319`:
All model initialization dictionaries configured default threading parameters to `-1`:
- `self._xgb_kwargs['n_jobs'] = -1`
- `self._lgb_kwargs['n_jobs'] = -1`
- `self._cat_kwargs['thread_count'] = -1`
- `self._surge_xgb_kwargs['n_jobs'] = -1`
- `self._surge_lgb_kwargs['n_jobs'] = -1`
- `self._surge_cat_kwargs['thread_count'] = -1`

#### Mathematical Oversubscription Analysis
Let $C = \text{os.cpu\_count() or 4}$ (available CPU cores) and $W = \text{\_train\_workers} = \max(1, \min(4, C))$ (concurrent market training workers).
When each worker runs an ML algorithm configured with $n\_jobs = -1$, each algorithm spawns $C$ OpenMP worker threads:
$$\text{Total Active Threads} = W \times C$$
- On an 8-core host: $W=4, C=8 \implies 4 \times 8 = 32\text{ active threads}$.
- On a 16-core host: $W=4, C=16 \implies 4 \times 16 = 64\text{ active threads}$.

#### Performance Impact of Thread Thrashing
1. **Scheduler Preemption**: 32–64 compute threads continuously compete for 8–16 CPU cores, causing heavy context switching overhead in the OS kernel.
2. **CPU Cache Line Invalidation**: High cache thrashing in L1/L2/L3 caches as cores alternate between disjoint memory regions across 4 independent model trees.
3. **OpenMP Lock Contention**: OpenMP runtime spin-locks and barrier synchronizations experience prolonged wait times.

#### Optimized Partitioning Solution
Set the intra-model thread budget per worker to:
$$\text{intra\_n\_jobs} = \max\left(1, \left\lfloor \frac{C}{W} \right\rfloor\right)$$
Under this formula:
$$\text{Total Concurrent Threads} = W \times \text{intra\_n\_jobs} \le C$$
- On an 8-core host: $W=4, \text{intra\_n\_jobs}=2 \implies 4 \times 2 = 8\text{ threads} = C$.
- On a 16-core host: $W=4, \text{intra\_n\_jobs}=4 \implies 4 \times 4 = 16\text{ threads} = C$.
Each training worker receives dedicated CPU cores without thrashing.

### 2.2 Exact Proposed Implementation

#### 2.2.1 Changes to `trading_system/run_pipeline.py`

In `run_pipeline.py`, around lines 1725–1760:

```python
        # S8 fix: ThreadPoolExecutor avoids pickle serialization overhead of ProcessPool.
        # Limit worker count to min(4, _CPU_WORKERS) to prevent XGBoost thread oversubscription.
        # Dynamically compute intra_n_jobs per worker to eliminate OpenMP thread thrashing.
        _train_workers = max(1, min(4, _CPU_WORKERS))
        _intra_n_jobs = max(1, _CPU_WORKERS // _train_workers)
        logger.info(f"ML Parallel Training: {_train_workers} market workers with intra_n_jobs={_intra_n_jobs} per model")

        with storage.pipeline_stage("train_regression"):
            _train_failures = []
            with ThreadPoolExecutor(max_workers=_train_workers) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        logger.info(f"Training {m_name.upper()} regression model ({len(m_df)} rows, intra_n_jobs={_intra_n_jobs})...")
                        futures[pool.submit(model.train, m_df, market=m_name, save_after=True, n_jobs=_intra_n_jobs)] = m_name
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"Regression training failed for {futures[fut]}: {e}")
                        _train_failures.append(f"{futures[fut]}: {e}")
            if _train_failures:
                _notify_telegram(f"⚠️ 회귀 모델 학습 실패 ({len(_train_failures)}/{len(market_dfs)}): " + " | ".join(_train_failures[:5]))
        model.load_models()

        with storage.pipeline_stage("train_surge"):
            _surge_failures = []
            with ThreadPoolExecutor(max_workers=_train_workers) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        futures[pool.submit(model.train_surge, m_df, market=m_name, save_after=True, n_jobs=_intra_n_jobs)] = m_name
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"Surge training failed for {futures[fut]}: {e}")
                        _surge_failures.append(f"{futures[fut]}: {e}")
            if _surge_failures:
                _notify_telegram(f"⚠️ Surge 모델 학습 실패 ({len(_surge_failures)}/{len(market_dfs)}): " + " | ".join(_surge_failures[:5]))
        model.load_surge_models()
```

#### 2.2.2 Changes to `src/ai/prediction_model.py`

In `OnDevicePredictionModel.train`:
```python
    def train(self, df_train: pd.DataFrame, market: str = "sp500", save_after: bool = True, n_jobs: Optional[int] = None, **kwargs):
        """Train XGBoost, LightGBM, and CatBoost regressors for each horizon.

        Validation strategy: 5-fold Walk-Forward (TimeSeriesSplit with 20-day gap).
        Each fold's MSE is averaged to derive stable ensemble weights.
        The final model is retrained on the full dataset to maximise data usage.
        """
        try:
            from src.ai.lstm_predictor import LSTMPredictor
            _has_lstm = True
        except Exception:
            _has_lstm = False
        from sklearn.metrics import mean_squared_error, mean_absolute_error

        if df_train.empty:
            logger.warning(f"Empty training data for {market}.")
            return

        df_train = df_train.reset_index(drop=True)
        features = self.ALL_FEATURES

        # Determine intra-model parallelism:
        if n_jobs is not None:
            intra_n_jobs = max(1, int(n_jobs))
        else:
            intra_n_jobs = max(1, (os.cpu_count() or 4))

        kw_xgb = dict(self._xgb_kwargs)
        kw_lgb = dict(self._lgb_kwargs)
        kw_cat = dict(self._cat_kwargs)

        kw_xgb['n_jobs'] = intra_n_jobs
        kw_lgb['n_jobs'] = intra_n_jobs
        kw_cat['thread_count'] = intra_n_jobs
```

In `OnDevicePredictionModel.train_surge`:
```python
    def train_surge(self, df_train: pd.DataFrame, market: str = "sp500", save_after: bool = True, n_jobs: Optional[int] = None, **kwargs):
        """Train XGBoost, LightGBM, and CatBoost classifiers for surge detection.

        Validation strategy: 5-fold Walk-Forward (TimeSeriesSplit with 20-day gap).
        AUC is averaged across folds to derive stable ensemble weights.
        The final model is retrained on the full dataset.
        """
        if df_train.empty:
            logger.warning(f"Empty training data for surge {market}.")
            return

        df_train = df_train.reset_index(drop=True)
        features = self.ALL_FEATURES
        missing = [f for f in features if f not in df_train.columns]
        if missing:
            logger.error(f"Missing features {missing} for surge {market}, skipping")
            return

        # Determine intra-model parallelism:
        if n_jobs is not None:
            intra_n_jobs = max(1, int(n_jobs))
        else:
            intra_n_jobs = max(1, (os.cpu_count() or 4))

        kw_xgb = dict(self._surge_xgb_kwargs)
        kw_lgb = dict(self._surge_lgb_kwargs)
        kw_cat = dict(self._surge_cat_kwargs)

        kw_xgb['n_jobs'] = intra_n_jobs
        kw_lgb['n_jobs'] = intra_n_jobs
        kw_cat['thread_count'] = intra_n_jobs
```

#### 2.2.3 Supplemental Hardening: `src/ai/vcp_ml_predictor.py`

In `VCPSurgePredictor.train` (`src/ai/vcp_ml_predictor.py:558`), where 5 markets are trained concurrently in `ThreadPoolExecutor(max_workers=len(MARKETS))`:
```python
        # Compute balanced intra_n_jobs for VCP ML market workers
        _vcp_market_workers = len(MARKETS)
        _vcp_intra_n_jobs = max(1, _CPU_WORKERS // _vcp_market_workers)
        
        # Apply to local kwargs inside _train_vcp_market:
        kw_xgb['n_jobs'] = _vcp_intra_n_jobs
        kw_lgb['n_jobs'] = _vcp_intra_n_jobs
        kw_cat['thread_count'] = _vcp_intra_n_jobs
```

---

## 3. Test Suite Verification & New Unit Tests

### 3.1 Existing Test Audit

Existing tests in `tests/test_prediction_model.py` and `tests/test_ensemble_lgb_cat.py` were fully executed and verified:

| Test Case | Scope | Execution Result |
|---|---|---|
| `test_accruals_quality_vectorized_scoring` | Vectorized Accruals Quality Engine | **PASSED** |
| `test_lead_lag_vectorized_returns` | Vectorized Lead-Lag Shift Matrix | **PASSED** |
| `test_lstm_batch_prediction_vectorization` | 3D Array Vectorized PyTorch Inference | **PASSED** |
| `test_short_term_reversal_vectorized_scoring` | 2D Reversal Matrix Scoring | **PASSED** |
| `test_trend_efficiency_vectorized_scoring` | Vectorized Kaufman KER & Hurst Exponent | **PASSED** |
| `test_ensemble_fallback_logic` | LightGBM / CatBoost Fallbacks | **PASSED** |
| `test_feature_engineering` | EMA crossover, Stochastic, Volume ratio | **PASSED** |
| `test_training_saving_loading_prediction` | Regression & Surge Model Persistence | **PASSED** |
| `test_vcp_ml_training_prediction` | VCP ML Multi-Market Training & Scoring | **PASSED** |

### 3.2 Proposed New Unit Tests for `tests/test_prediction_model.py`

Add the following unit test classes to `tests/test_prediction_model.py` to verify scaler caching, cache eviction, and dynamic thread allocation:

```python
from src.ai.feature_engineering import fit_scaler, load_scaler, clear_scaler_cache, get_scaler_cache_info
from sklearn.preprocessing import StandardScaler
from concurrent.futures import ThreadPoolExecutor


class TestScalerCaching(unittest.TestCase):
    """Verifies thread-safe LRU caching, cache hit/miss counting, and eviction for load_scaler."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.model_dir = self.tmp_dir.name
        clear_scaler_cache()

    def tearDown(self):
        clear_scaler_cache()
        self.tmp_dir.cleanup()

    def test_scaler_cache_hits_and_misses(self):
        # Create and fit a dummy scaler
        df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [10.0, 20.0, 30.0]})
        scaler = fit_scaler(df, ["f1", "f2"], self.model_dir, "sp500", 5)

        info0 = get_scaler_cache_info()
        self.assertEqual(info0.currsize, 0)

        # First load: cache MISS
        s1 = load_scaler(self.model_dir, "sp500", 5)
        info1 = get_scaler_cache_info()
        self.assertEqual(info1.misses, 1)
        self.assertEqual(info1.hits, 0)
        self.assertEqual(info1.currsize, 1)

        # Second load with same args: cache HIT
        s2 = load_scaler(self.model_dir, "sp500", 5)
        info2 = get_scaler_cache_info()
        self.assertEqual(info2.hits, 1)
        self.assertIs(s1, s2)

        # Third load with case-insensitive market & Path object: cache HIT
        s3 = load_scaler(Path(self.model_dir), "SP500", 5)
        info3 = get_scaler_cache_info()
        self.assertEqual(info3.hits, 2)
        self.assertIs(s1, s3)

    def test_scaler_cache_invalidation_on_fit(self):
        df1 = pd.DataFrame({"f1": [1.0, 2.0], "f2": [10.0, 20.0]})
        fit_scaler(df1, ["f1", "f2"], self.model_dir, "nasdaq", 10)
        s_old = load_scaler(self.model_dir, "nasdaq", 10)

        # Refit scaler with new data
        df2 = pd.DataFrame({"f1": [100.0, 200.0], "f2": [1000.0, 2000.0]})
        fit_scaler(df2, ["f1", "f2"], self.model_dir, "nasdaq", 10)

        # After fit, cache should be invalidated
        info = get_scaler_cache_info()
        self.assertEqual(info.currsize, 0)

        s_new = load_scaler(self.model_dir, "nasdaq", 10)
        self.assertIsNot(s_old, s_new)
        self.assertAlmostEqual(s_new.mean_[0], 150.0)

    def test_concurrent_load_scaler_thread_safety(self):
        df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [4.0, 5.0, 6.0]})
        fit_scaler(df, ["f1", "f2"], self.model_dir, "kospi", 20)

        scalers = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(load_scaler, self.model_dir, "kospi", 20) for _ in range(50)]
            for fut in futures:
                scalers.append(fut.result())

        self.assertEqual(len(scalers), 50)
        first = scalers[0]
        for s in scalers:
            self.assertIs(s, first)


class TestMLThreadAllocation(unittest.TestCase):
    """Verifies that dynamic n_jobs thread allocation correctly propagates to ML estimators."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.model_dir = self.tmp_dir.name
        self.model = OnDevicePredictionModel(model_dir=self.model_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_train_thread_allocation_propagation(self):
        dates = pd.date_range("2026-01-01", periods=100)
        df_train = pd.DataFrame({
            "Open": np.linspace(100, 150, 100),
            "High": np.linspace(101, 152, 100),
            "Low": np.linspace(99, 149, 100),
            "Close": np.linspace(100, 150, 100),
            "Volume": np.full(100, 1000.0),
            "target_5d": np.random.randn(100) * 0.05,
        }, index=dates)

        # Train with explicit n_jobs=2
        self.model.train(df_train, market="sp500", save_after=False, n_jobs=2)

        xgb_model = self.model.models["sp500"][5]
        lgb_model = self.model.lgb_models["sp500"][5]
        cat_model = self.model.cat_models["sp500"][5]

        self.assertEqual(xgb_model.get_params().get("n_jobs"), 2)
        self.assertEqual(lgb_model.get_params().get("n_jobs"), 2)
        self.assertEqual(cat_model.get_params().get("thread_count"), 2)
```

---

## 4. Verification Commands

To independently execute and verify the test suites:

```bash
# Run prediction model vectorization and ensemble tests
.venv\Scripts\pytest tests/test_prediction_model.py tests/test_ensemble_lgb_cat.py -v

# Run full consolidated test suite
.venv\Scripts\pytest tests/test_e2e_consolidated.py -v
```

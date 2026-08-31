# Comprehensive Investigation Report: Milestone 1 (R1: Model Training & Inference Pipelines Integrity)

## Executive Summary
This report provides a detailed forensic analysis of the machine learning training and inference pipelines in the quantitative stock trading system. We investigated the four core model families across 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`):
1. **Multi-Horizon XGBoost Regression** (Tri-Ensemble: XGBoost + LightGBM + CatBoost + LSTM)
2. **Surge Classifier** (XGBoost + LightGBM + CatBoost with capped scale_pos_weight)
3. **VCP ML Surge Classifier** (`VCPSurgePredictor` with windowed contraction feature engineering)
4. **Strict Causal LSTM Predictor** (PyTorch LayerNorm + 2-layer LSTM with rolling causal momentum fallback)

All four model architectures feature robust dual-mode operation:
- **`SKIP_TRAINING=False` (Training Mode)**: Full on-device training with purged temporal CV (`DateAwareTimeSeriesSplit`), class imbalance mitigations, atomic file serialization, SHA-256 binary checksums, and feature schema fingerprinting in `trading_system/models/`.
- **`SKIP_TRAINING=True` (Inference Mode)**: Fast model loading via `ModelCacheManager` with memory caching, schema validation, calibrated blend scoring (Platt/Isotonic), and mathematical heuristic fallbacks when disk models are absent.

---

## 1. Model Training & Inference Architecture per Family

| Model Family | Target & Horizons | Training Implementation (`SKIP_TRAINING=False`) | Inference & Loading (`SKIP_TRAINING=True`) | Fallback Heuristic Mechanism | Artifact File Format & Path |
|---|---|---|---|---|---|
| **1. Regression (Tri-Ensemble)** | 8 horizons: 1d, 5d, 10d, 20d, 30d, 60d, 120d, 200d forward return | `OnDevicePredictionModel.train()` fits XGBoost, LightGBM, and CatBoost per market using `DateAwareTimeSeriesSplit`. Fits Isotonic calibrators on out-of-sample holdout. | `OnDevicePredictionModel.load_models()` restores models from disk. `_predict_market_batch()` blends XGB, LGB, CatBoost using market ensemble weights. | Cross-market fallback (KRX fallback for KOSPI/KOSDAQ, SP500 fallback for global). If no models, rolling momentum + volatility heuristic expected return. | `trading_system/models/xgb_model_{mkt}_{h}d.json`, `lgb_model_{mkt}_{h}d.txt`, `cat_model_{mkt}_{h}d.bin`, `calibrators.pkl` |
| **2. Surge Classifier** | 4 horizons: 1d, 3d, 5d, 20d (Binary return >= 20%) | `OnDevicePredictionModel.train_surge()` fits XGBClassifier, LGBMClassifier, CatBoostClassifier per market. Implements `scale_pos_weight <= 20.0` cap. | `OnDevicePredictionModel.load_surge_models()` restores models. `_predict_surge()` blends predictions and applies Platt scaling logit transformations. | RSI(14) oversold bounce + breakout ratio + 5-day volume spike heuristic probability bounded to 0.05~0.45 base rates. | `trading_system/models/xgb_surge_model_{mkt}_{h}d.json`, `lgb_surge_model_{mkt}_{h}d.txt`, `cat_surge_model_{mkt}_{h}d.bin` |
| **3. VCP ML Predictor** | 4 horizons: 1d, 3d, 5d, 20d (Binary surge on VCP contraction) | `VCPSurgePredictor.train()` computes sliding-window VCP features (`_windowed_vcp_features`) combining 11 VCP metrics + base features. Dynamic 95th percentile thresholding for sparse positive labels. | `VCPSurgePredictor.load_models()` restores XGB, LGB, CatBoost models. `predict()` blends models with Platt scaling or Isotonic mapping. | `_compute_vcp_features` heuristic score: $P = \text{clip}(\text{vcp\_score}/100 \times 0.40 + 0.05, 0.05, 0.45)$ based on historical volatility contraction. | `trading_system/models/vcp_surge_{market}_{h}d.json`, `lgb_vcp_surge_{market}_{h}d.txt`, `cat_vcp_surge_{market}_{h}d.bin` |
| **4. Strict Causal LSTM** | 20d horizon forward return | PyTorch `LSTMPredictor` (LayerNorm + 2-layer LSTM + Linear head) trained with Adam, `ReduceLROnPlateau`, `CosineAnnealingLR`, and gradient clipping (`max_grad_norm=1.0`). | `LSTMPredictor.load_model()` loads PyTorch checkpoint (`model_state_dict`). `predict_lstm()` prepares 20-day returns sequences and runs batch forward pass. | Rolling causal momentum with exponential decay weights ($\exp(\text{linspace}(-2, 0, 20))$) normalized by 20-day rolling return volatility (Sharpe-like ratio). Cross-sectional percentile ranked into $[0.05, 0.95]$. | `trading_system/models/lstm_model_{market}_20d.pt` |

---

## 2. Deep Dive: Training vs. Inference Control Flow

### A. Pipeline Orchestration (`trading_system/run_pipeline.py`)
- **Model Check & Cache Verification (Lines 1483–1531)**:
  - If `cfg.skip_training` is True, `ModelCacheManager` verifies cache health across required markets (`sp500`, `nasdaq`, `russell2000`, `kospi`, `kosdaq`).
  - Calls `model.load_models()`, `model.load_surge_models()`, `model.load_lead_lag()`, and `vcp_ml.load_models()`.
  - Determines `should_skip`:
    - If `PRESEED_MODE=true` or `SKIP_TRAINING=True` (env var), `should_skip` is forced to `True`.
    - If models are present on disk (`regression_loaded or surge_loaded or vcp_loaded`), `should_skip = True`.
    - If models are missing and no override is present, it logs a warning and falls back to `should_skip = False`.
- **Parallel Training Phase (Lines 1534–1852)**:
  - When `should_skip = False`:
    1. Stratified sampling (`_stratified_sample`) across markets and sectors.
    2. Background asynchronous fundamental fetching (`_bg_fundamentals`).
    3. `vcp_ml.train()` executed first to optimize memory utilization before large regression matrices.
    4. Parallel regression training via `ThreadPoolExecutor` with worker count `_train_workers = max(1, min(4, CPU_WORKERS))` and intra-model thread budgeting (`intra_n_jobs = max(1, CPU_WORKERS // _train_workers)`) preventing OpenMP thread oversubscription.
    5. Surge classifier training per market.
    6. Lead-Lag correlation matrix computation (`model.compute_lead_lag()`).
    7. Isotonic regression calibration fitting on out-of-sample chronological holdout.
- **Inference Phase (Lines 1853–4250)**:
  - Fast batch feature extraction and multi-model prediction.
  - Regression (`predict_all`), Surge (`_predict_surge`), VCP ML (`vcp_ml.predict`), LSTM (`predict_lstm`), and rule-based strategies.
  - Standalone strategy prediction output writing to `trading_system/result/`:
    - `pipeline_result.txt` (Regression)
    - `surge_predictions.txt` (Surge Classifier)
    - `vcp_ml_predictions.txt` (VCP ML)
    - `lstm_predictions.txt` (Strict Causal LSTM)
    - `vcp_patterns.txt`, `lead_lag_predictions.txt`, `stat_arb_predictions.txt`, etc.

---

## 3. Model Artifact Storage & Integrity Mechanisms (`trading_system/src/ai/model_cache.py`)

1. **Atomic File Replacement**:
   - When saving models, data is written to a process-unique temporary file (`f"{stem}.tmp_{pid}_{timestamp}{suffix}"`) before invoking `os.replace()`.
   - Prevents partial or corrupted model files on disk if the process terminates abruptly.
2. **Binary Integrity Checksums (SHA-256)**:
   - For every saved model, a JSON metadata sidecar (`{model_path}_meta.json`) is created containing the SHA-256 hex digest and file size in bytes.
   - On load, `load_model_safe()` verifies the SHA-256 digest to immediately catch file truncation or byte-level corruption.
3. **Feature Schema Fingerprinting**:
   - Hashes sorted feature column names into a 16-character SHA-256 fingerprint (`feature_fingerprint`).
   - Detects feature column drift between model training and pipeline inference.
4. **Thread-Safe In-Memory Cache with Mutex**:
   - `ModelCacheManager` maintains an in-memory cache protected by an `RLock` mutex with LRU eviction when capacity (`max_memory_items=256`) is reached.

---

## 4. GitHub Actions Workflows Audit & Alignment

### A. `.github/workflows/training.yml` (Weekend Training Pipeline)
- **Schedule**: Saturday 11:30 UTC (`cron: '30 11 * * 6'`).
- **Matrix**: 5 core markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`).
- **Environment**: `SKIP_TRAINING: 'False'`, `SKIP_INFERENCE: 'True'`.
- **Cache Saving**:
  - `key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}`
  - Path: `trading_system/models`
- **Integrity Status**: Fully verified. Caches all trained `.json`, `.txt`, `.bin`, and `.pt` model files and calibrators.

### B. `.github/workflows/pipeline.yml` (Daily Inference Pipeline)
- **Schedule**: Monday–Friday 11:30 UTC (`cron: '30 11 * * 1-5'`).
- **Matrix**: 5 core markets.
- **Environment**: `SKIP_TRAINING: 'True'`, `SKIP_INFERENCE: 'False'`.
- **Cache Restoring**:
  - `key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}`
  - `restore-keys: ai-models-${{ matrix.target }}-`
- **Step Summary & Output Tracking**:
  - Step Summary (line 193) requires `lstm_predictions.txt` to be in the inspection loop (F02).
  - Split artifact copy (line 241) properly includes `lstm_predictions`.

---

## 5. Test Suite Verification
- Ran full test suite on `tests/test_prediction_model.py` and `tests/test_vcp_ml_fallback.py`:
  - `test_accruals_quality_vectorized_scoring`: PASSED
  - `test_lead_lag_vectorized_returns`: PASSED
  - `test_lstm_batch_prediction_vectorization`: PASSED
  - `test_short_term_reversal_vectorized_scoring`: PASSED
  - `test_trend_efficiency_vectorized_scoring`: PASSED
  - `test_concurrent_load_scaler_thread_safety`: PASSED
  - `test_scaler_cache_hits_and_misses`: PASSED
  - `test_scaler_cache_invalidation_on_fit`: PASSED
  - `test_train_surge_thread_allocation_propagation`: PASSED
  - `test_train_thread_allocation_propagation`: PASSED
  - Total: **10 passed in 95.47s (100% success rate)**.

---

## 6. Recommendations for Implementation (Worker Tasks)
1. **Workflow Alignment (F02)**: Ensure `lstm_predictions.txt` is included in `pipeline.yml` line 193 Step Summary loop and release upload files list.
2. **Canonical Strategy Order (M2 / F03)**: Ensure all 4 model outputs appear in canonical order: 1: `regression`, 2: `surge`, 3: `lead_lag`, 4: `vcp_rule`, 5: `vcp_ml`, 6: `lstm`.
3. **Artifact Verification Expansion (F04 / F05)**: Ensure `verify_gha_artifacts.py` and `run_pipeline.py` output verification scripts check all 31 strategy `.txt` files with strict non-zero assertions.

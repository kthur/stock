# Handoff Report: Milestone 1 (R1: Model Training & Inference Pipelines Integrity)

## 1. Observation
- **Model Training Architecture**: In `trading_system/run_pipeline.py` (lines 1483–1852), `src/ai/prediction_model.py` (lines 1740–1950), and `src/ai/vcp_ml_predictor.py` (lines 259–593), four distinct model families are trained per market (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`):
  1. XGBoost/LGBM/CatBoost multi-horizon regression (`xgb_model_{mkt}_{h}d.json`, `lgb_model_{mkt}_{h}d.txt`, `cat_model_{mkt}_{h}d.bin`).
  2. Multi-horizon Surge classifier with `scale_pos_weight <= 20.0` (`xgb_surge_model_{mkt}_{h}d.json`, `lgb_surge_model_{mkt}_{h}d.txt`, `cat_surge_model_{mkt}_{h}d.bin`).
  3. VCP ML surge classifier with 11 contraction features and sliding-window generation (`vcp_surge_{market}_{h}d.json`, `lgb_vcp_surge_{market}_{h}d.txt`, `cat_vcp_surge_{market}_{h}d.bin`).
  4. PyTorch Strict Causal LSTM (`LSTMPredictor`) with LayerNorm and 2-layer sequence architecture (`lstm_model_{market}_20d.pt`).
- **Inference & Model Cache Loading**: In `trading_system/run_pipeline.py` (lines 1488–1531), when `SKIP_TRAINING` is True, models are loaded via `ModelCacheManager` and `load_models()`. If missing on disk, fallback heuristics are engaged:
  - Regression: cross-market model fallback (KRX for KOSPI/KOSDAQ, SP500 for global) or exponential momentum & volatility scaling.
  - Surge: RSI(14) oversold bounce + breakout ratio + volume spike heuristic probability.
  - VCP ML: VCP feature contraction score & range contraction ratio fallback ($0.05 \sim 0.45$).
  - LSTM: Exponentially weighted causal momentum divided by 20-day volatility (Sharpe-like ratio) cross-sectionally percentile-ranked into $[0.05, 0.95]$.
- **Model Artifact Storage**: In `src/ai/model_cache.py`, models are saved atomically using `.tmp` -> `os.replace` with SHA-256 digests and feature schema fingerprints in `{model}_meta.json`.
- **Workflow Cache Alignment**: `.github/workflows/training.yml` saves to `ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}` and `.github/workflows/pipeline.yml` restores using `ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}` with fallback `ai-models-${{ matrix.target }}-`.

## 2. Logic Chain
1. In `run_pipeline.py`, the training pipeline is conditionally triggered based on `cfg.skip_training` and whether models are detected on disk.
2. During training (`SKIP_TRAINING=False`), memory-safe multi-threading (`intra_n_jobs` thread allocation per worker) prevents CPU thrashing across all 5 markets.
3. During inference (`SKIP_TRAINING=True`), models are safely loaded with SHA-256 verification and feature schema compatibility checks, preventing silent model corruption or column mismatch crashes.
4. If a model file is missing or uncalibrated in a clean environment, all four models gracefully degrade to deterministic mathematical heuristics, guaranteeing non-zero predictions without crashing the pipeline.
5. All generated predictions are saved to standalone files (`pipeline_result.txt`, `surge_predictions.txt`, `vcp_ml_predictions.txt`, `lstm_predictions.txt`) and unified into `ensemble_predictions.txt`.

## 3. Caveats
- Deep learning PyTorch models require CPU inference mode (`FORCE_CPU=1`) in standard GitHub Actions ubuntu-latest runners where CUDA GPUs are unavailable. The codebase handles this automatically.
- High memory usage during massive universe historical windowing in VCP ML is mitigated by executing `vcp_ml.train()` prior to XGBoost regression and calling `gc.collect()`.

## 4. Conclusion
The model training and inference pipelines for Regression, Surge, VCP ML, and Strict Causal LSTM are verified to be robust, memory-safe, and resilient against data sparsity and missing artifacts. The GHA cache keys between `training.yml` and `pipeline.yml` match correctly. Recommendations for the Worker have been prepared and documented in `report.md`.

## 5. Verification Method
- Execute the test suite for prediction models:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/test_prediction_model.py -v
  .venv\Scripts\python.exe -m pytest tests/test_lstm_predictor.py -v
  .venv\Scripts\python.exe -m pytest tests/test_vcp_ml_fallback.py -v
  ```
- Inspect output files:
  - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\report.md`
  - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\handoff.md`

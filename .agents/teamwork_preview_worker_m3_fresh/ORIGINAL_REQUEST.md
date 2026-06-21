## 2026-06-20T14:41:37+09:00
1. Open and review `trading_system/src/ai/prediction_model.py`, `trading_system/src/ai/vcp_ml_predictor.py`, `trading_system/run_pipeline.py`, and `trading_system/src/data_layer/earnings_data.py`.
2. Implement R2: Automated Hyperparameter Tuning via Optuna
   - Create a hyperparameter tuning script/stage `trading_system/scripts/tune_models.py` (or integrate it directly in prediction_model.py or as a CLI flag).
   - The tuning script should load a sample of the training dataset, split it chronologically (80% train, 20% validation).
   - Use Optuna to search for optimal hyperparameters for XGBoost, LightGBM, and CatBoost models.
   - Save the best parameters to `trading_system/models/tuned_params.json`.
   - Update `OnDevicePredictionModel` and `VCPSurgePredictor` to check if `tuned_params.json` exists in `models/` directory, and if so, load and use those parameters when initializing and fitting models.
3. Implement R3: API & Data Integration Stability
   - Implement robust retry logic with exponential backoff using tenacity for the following data-fetching network functions:
     - `fetch_data_fdr` in `run_pipeline.py` (calls `fdr.DataReader` and `yf.download`)
     - `fetch_indicator_history` in `run_pipeline.py` (calls `yf.download` inside a thread pool)
     - `fetch_fundamentals` in `earnings_data.py` (calls `yf.Ticker` and properties)
   - Ensure the retry logic catches rate limits, timeouts, and network exceptions, waits exponentially, and resumes gracefully.
   - Ensure that a thread-safe lock or shared global rate limiter is strictly applied during concurrent network requests to prevent triggering rate limits.
4. Add unit tests under `tests/` verifying:
   - Optuna tuning runs, updates `tuned_params.json`, and those parameters are loaded by `OnDevicePredictionModel`.
   - API rate limiting/retry wrappers catch exceptions and retry correctly under simulated failures.
5. Run the entire test suite via `.venv/bin/pytest tests/ -v` and make sure everything is green.
6. Write a detailed handoff report in `handoff.md` and send a message when done.

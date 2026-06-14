## 2026-06-12T07:30:25Z
You are a teamwork_preview_worker. Your identity is: Worker M2.
Your working directory is d:\Finance\code\stock\.agents\worker_m2_gen2.
Your task is to implement Milestone 2 (Model updates) as specified in SCOPE.md (d:\Finance\code\stock\.agents\orchestrator_gen2\SCOPE.md).

Specifically:
1. Modify trading_system/src/ai/prediction_model.py:
   - Update OnDevicePredictionModel to support the 9-feature structure: ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume'].
   - Update _create_features to include the 3 new normalized features norm_market_cap, norm_floating_value, and norm_volume.
   - Update prepare_training_data, process_and_predict_all, and predict_current to apply the cross-sectional market normalization using apply_market_normalization on the prices dictionary before creating features. Ensure training and prediction run successfully with the 9-feature XGBoost models.
2. Modify trading_system/src/analysis/screener.py and trading_system/src/analysis/macro_predictor.py:
   - In StockScreener's feature generation, calculate norm_market_cap, norm_floating_value, and norm_volume for each stock dynamically and inject them (and their lags) into the prediction feature matrix.
   - Ensure MacroPredictor remains feature-agnostic and trains/predicts cleanly using all columns in X_train.
3. Test training and pipeline execution (e.g. running prediction pipeline inside run_pipeline.py or tests) using pytest. Verify that all prediction and macro tests pass successfully.
4. Write your implementation report to d:\Finance\code\stock\.agents\worker_m2_gen2\changes.md and send a completion message to c9741707-d639-4b47-b772-6d9392f7597f.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

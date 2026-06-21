## 2026-06-20T14:29:36Z

Your identity is: teamwork_preview_worker (ID will be generated)
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\
Your task is:
1. Open and inspect `trading_system/requirements.txt`. Add `catboost` and `optuna` if they are not present.
2. Run `.venv/bin/pip install -r trading_system/requirements.txt` to install the new packages.
3. Review `trading_system/src/ai/prediction_model.py` and `trading_system/src/ai/vcp_ml_predictor.py`.
4. Integrate LightGBM (`lightgbm.LGBMRegressor` / `lightgbm.LGBMClassifier`) and CatBoost (`catboost.CatBoostRegressor` / `catboost.CatBoostClassifier`) into `OnDevicePredictionModel` and `VCPSurgePredictor` alongside the existing XGBoost models.
   - For training: in `train`, `train_surge`, and `VCPSurgePredictor.train`, train the LightGBM and CatBoost models alongside XGBoost. Save validation metrics for all three.
   - For prediction: combine predictions from all three models (e.g. simple average or weighted average like 0.4 * XGBoost + 0.3 * LightGBM + 0.3 * CatBoost). Make sure the prediction logic handles cases where LightGBM/CatBoost are not loaded (e.g. fallback to XGBoost).
   - For saving and loading: save LightGBM/CatBoost models in `models/` directory using appropriate methods (`booster_.save_model()` or `save_model()`), and load them in `load_models()`.
5. Implement feature engineering improvements:
   - Introduce new technical/macro features (e.g. simple/exponential moving average crossovers, stochastic oscillator %K/%D, or additional normalized volume indicators).
   - Ensure the new features are calculated in both training and inference steps and added to `ALL_FEATURES` or `VCP_FEATURES`.
6. Add unit tests in `tests/` or edit existing tests to verify that:
   - LightGBM and CatBoost are successfully trained, saved, loaded, and predict.
   - Feature engineering generates correct features.
7. Run the test suite via `.venv/bin/pytest tests/ -v` (or standard command) and verify everything passes.
8. Document all changes and test results in `handoff.md` and send a message when done.

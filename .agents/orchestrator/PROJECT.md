# Project: Stock Trading System ML Improvements

## Architecture
- `trading_system/run_pipeline.py`: Pipeline entry point.
- `trading_system/src/ai/prediction_model.py`: Regressor and Classifier models.
- `trading_system/src/ai/vcp_ml_predictor.py`: VCP ML predictor model.
- `trading_system/src/data_layer/earnings_data.py`: Fundamental fetching logic (rate limit, retries).
- `trading_system/src/config.py`: System configuration.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Baseline Verification | Explore structure and run existing tests. | None | DONE |
| 2 | Feature & Alt Models (R1) | New features, LightGBM/CatBoost ensemble. | M1 | DONE |
| 3 | Optuna & API Stability (R2/R3) | Optuna tuning, rate-limiting & retries. | M2 | DONE |
| 4 | E2E & Forensic Audit | Verification and audit of full features. | M3 | PLANNED |

## Interface Contracts
### R1. Alternative Models & Feature Engineering
- The new models must be drop-in replacements or ensembles that preserve the signature of `OnDevicePredictionModel` and VCP predictors.
- The pipeline output files (`pipeline_result.txt`, `surge_predictions.txt`, `vcp_ml_predictions.txt`) must maintain their original layout.
- The technical / macroeconomic features must be added to the training/inference steps.

### R2. Optuna tuning
- Must have a CLI parameter or a separate entry point to trigger tuning.
- Save best parameters to configured model paths.

### R3. API & Data Integration Stability
- Rate limit wrapper/decorator or retry decorator with backoff on data extraction endpoints (e.g. FinanceDataReader, yfinance, or other APIs).

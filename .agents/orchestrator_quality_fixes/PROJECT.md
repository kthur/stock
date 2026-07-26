# Project: Quality Fixes in Stock Prediction Pipeline

## Architecture
The system is a stock automatic trading and prediction system that operates 5 strategies for 3,379 stock symbols across 4 markets (SP500, KOSPI, KOSDAQ, KONEX).
- **run_pipeline.py**: Unified pipeline orchestrating data ingestion, feature generation, model training, inference, and database caching.
- **prediction_model.py**: Contains the `OnDevicePredictionModel` which defines the features, trains XGBoost regression models, LightGBM/CatBoost surge classifiers, and computes Lead-Lag correlation matrices.
- **vcp_ml_predictor.py**: Implements the VCP ML predictions, saving/loading the `vcp_surge_*.json` models.
- **ensemble_scorer.py**: Aggregates predicted scores from regression, surge, lead-lag, and VCP ML.
- **merge_predictions.py**: Merges prediction files under GHA distributed pipeline.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Diagnosis | Analyze model paths, GHA workflow, leader selection, and prediction outputs (c92d0250-1ae5-49d1-8100-d0cdc74e8b41, 02e771ac-d659-4c77-b7c3-0b76bfec5603, 14bf208a-334e-411f-bac0-0e3c2e99ab3f) | None | DONE |
| 2 | Implementation | Apply fixes to model loading, lead-lag selection, VCP ML paths, and empty outputs (ca5308e4-0dc1-48f9-a36c-b4bc1d31be1c) | M1 | DONE |
| 3 | Verification | Validate predictions output, run existing test suite, run challengers and auditor | M2 | BLOCKED: API Quota |

## Code Layout
- `trading_system/run_pipeline.py`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/vcp_ml_predictor.py`
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/merge_predictions.py`
- `trading_system/result/`
- `tests/`

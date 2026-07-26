# Task for Worker 1

## Objective
Implement the 4 quality bug fixes and empty prediction file placeholders in the codebase as described in `d:\Finance\code\stock\.agents\orchestrator_quality_fixes\synthesis.md` and the analysis reports.

## Detailed Instructions
1. **Fix Cache Key in training.yml**:
   Align the key in `.github/workflows/training.yml` (Line 66) to match the layout of `.github/workflows/pipeline.yml`:
   `ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`.
2. **Fix Model Fallback Load Checks in prediction_model.py**:
   In `trading_system/src/ai/prediction_model.py`, update the loops in `load_models()` and `load_surge_models()` that check model existence: change target markets to `['sp500', 'kospi', 'kosdaq', 'konex']` instead of `['sp500', 'krx']`.
3. **Fix Lead-Lag KRX Predictions in prediction_model.py and run_pipeline.py**:
   Modify `compute_lead_lag()` to group/select leaders per market (SP500, KOSPI, KOSDAQ, KONEX) to ensure representation from KRX.
   Update the call to `compute_lead_lag()` in `trading_system/run_pipeline.py` to pass the `symbol_market` dictionary as `symbol_to_market`.
4. **Fix VCP ML Model Dir Alignment**:
   In `trading_system/run_pipeline.py`, pass `model_dir=str(model.model_dir)` when instantiating `VCPSurgePredictor` to ensure it looks in the correct folder under GHA.
5. **Output File Placeholders**:
   In `trading_system/run_pipeline.py`, update file saving logic for `surge_predictions.txt`, `lead_lag_predictions.txt`, `vcp_patterns.txt`, and `vcp_ml_predictions.txt` so they always write headers, writing a descriptive placeholder text (e.g. "No surge candidates detected.") when empty, to prevent missing prediction files.

## Verification Requirements
- Execute existing pytest test suite: `.venv/bin/pytest tests/ -v --tb=short` or similar command using `.venv/bin/python -m pytest`.
- Verify the build succeeds.
- Document all run commands and test results in `handoff.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

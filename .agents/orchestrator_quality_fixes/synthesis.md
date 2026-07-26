# Synthesis of Diagnosis - Quality Fixes in Stock Prediction Pipeline

## Consensus
All analyzed reports (Explorer 1 and Explorer 3) agree on the root causes and fix strategies for the 4 quality bugs:

### Bug 1: Surge Classifier 0.0% & Bug 3: VCP ML Predictions Empty
- **Root Cause**: 
  1. GHA cache key mismatch between `training.yml` (`ai-models-v2-${date}-${target}`) and `pipeline.yml` (`ai-models-v2-${target}-${date}`). Restoring fails, leaving the models directory empty.
  2. Fallback check logic in `prediction_model.py` checks for `'krx'` instead of individual market segments `'kospi'`, `'kosdaq'`, `'konex'`. Because individual models are named with the specific market (e.g. `xgb_surge_model_kospi_1d.json`), the check for `xgb_surge_model_krx_1d.json` fails even if models are somehow present.
  3. In `vcp_ml_predictor.py`, `VCPSurgePredictor` defaults to an empty predictor because no models are found, and the model directory isn't explicitly configured.
- **Fix Strategy**:
  1. Fix `.github/workflows/training.yml` to use `ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`.
  2. Update fallback check in `prediction_model.py`'s `load_models` and `load_surge_models` to check for `['sp500', 'kospi', 'kosdaq', 'konex']`.
  3. Explicitly pass the resolved model directory to `VCPSurgePredictor(model_dir=str(model.model_dir))` in `run_pipeline.py`.

### Bug 2: Lead-Lag KRX Predictions Missing
- **Root Cause**:
  1. `compute_lead_lag` selects the top 50 leaders globally based on average market cap. 
  2. Scale difference and normalization mismatch exclude KOSDAQ/KONEX from the top 50 list.
  3. Followers in missing markets never get scored because none of their leaders are in the leader list.
- **Fix Strategy**:
  1. Segment leader selection per market (e.g., SP500, KOSPI, KOSDAQ, KONEX).
  2. Select top N (e.g. 20 from SP500, 20 from KOSPI, 20 from KOSDAQ, 5 from KONEX) to form the top leaders.
  3. In `run_pipeline.py`, pass `symbol_market` map to `compute_lead_lag(..., symbol_to_market=symbol_market)`.

### Bug 4: Ensemble 0% for KRX
- **Root Cause**: Downstream consequence of Bug 1-3.
- **Fix Strategy**: Resolving Bug 1-3 will automatically populate inputs, resolving this.

### Requirement 5: Output File Placeholders
- **Root Cause**: GHA pipeline expects prediction files to be created even when empty. Skipping creation causes errors in GHA steps.
- **Fix Strategy**: Always write the output files with headers, writing a descriptive placeholder (e.g. "No candidates detected.") when empty.

## Resolved Conflicts
No conflicts identified. Explorer 1 and Explorer 3 reached identical diagnostic conclusions and very similar proposed fixes.

## Gaps
None. The proposed fixes cover all target issues.

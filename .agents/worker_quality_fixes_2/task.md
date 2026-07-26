# Task for Worker 2

## Objective
Verify the quality fixes implemented in the codebase and run tests.

## Background
`worker_1` has already modified the files:
- `.github/workflows/training.yml`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/vcp_ml_predictor.py`
- `trading_system/run_pipeline.py`
- `trading_system/merge_predictions.py`

However, `worker_1` became unresponsive. You need to verify their implementation, run tests, and execute a pipeline run to check if predictions are correctly generated.

## Detailed Tasks
1. **Review implementation**:
   Inspect the changes in the modified files. Ensure that the GHA cache key, fallback checks, lead-lag selection, VCP ML paths, and empty prediction placeholders have been properly implemented.
2. **Run Pytest**:
   Run the test suite to verify code correctness: `.venv\Scripts\pytest tests\ -v --tb=short` (or `.venv/bin/pytest` depending on the environment). If any specific tests are hanging, identify which ones they are and analyze why.
3. **Execute Prediction Pipeline (Dry-run/Mock)**:
   Run `run_pipeline.py` or trigger inference to generate predictions.
   Verify that the prediction files are generated in `trading_system/result/`.
4. **Check Predictions Output**:
   Verify the acceptance criteria:
   - `surge_predictions.txt`: at least 20 stocks with surge probability > 0.0% for KOSPI, KOSDAQ, KONEX, and SP500 for each horizon.
   - `lead_lag_predictions.txt`: KOSPI Top 20, KOSDAQ Top 20, KONEX Top 20, SP500 Top 20 sections are present and populated.
   - `vcp_ml_predictions.txt`: KOSPI, KOSDAQ, KONEX, SP500 each x 4 horizons has top 10+ predictions.
   - `ensemble_predictions.txt`: all 4 markets have at least 5 stocks with non-zero Surge%, L-L%, VCP% values.
5. **Run the check script**:
   ```python
   import re
   for fname in ['trading_system/result/surge_predictions.txt',
                 'trading_system/result/lead_lag_predictions.txt',
                 'trading_system/result/vcp_ml_predictions.txt']:
       content = open(fname, encoding='utf-8').read()
       nonzero = len(re.findall(r': [1-9]\d*\.\d+%', content))
       print(f'{fname}: {nonzero} non-zero entries')
   ```
6. **Report results**:
   Write a detailed handoff report in your working directory (`.agents/worker_quality_fixes_2/handoff.md`) with test run commands and outputs.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

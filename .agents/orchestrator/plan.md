# Project Plan: Feature Engineering, Alternative Models, Optuna Tuning, and API Stability

## Resuming Project State (2026-06-20)
The user has requested the implementation of feature engineering, alternative models (LightGBM, CatBoost), Optuna tuning, and API/data integration stability.

---

## Detailed Milestone Plans

### Milestone 1: Baseline Verification
- **Objective**: Explore the codebase, review existing pipeline execution, and verify baseline test suite.
- **Verification**: Run `pytest tests/` and run the pipeline (`run_pipeline.py` or similar) in demo mode if possible, documenting performance metrics.
- **Steps**:
  1. Spawn Explorer (`teamwork_preview_explorer`) to search files, list active tests, run the baseline tests and record results.
  2. Document existing metrics for XGBoost.

### Milestone 2: Feature Engineering & Alternative Models (R1)
- **Objective**: Integrate new features (technical indicators, macro) and alternative models (LightGBM, CatBoost) without breaking XGBoost compatibility.
- **Verification**: Confirm models train and predict successfully. Compare performance (MSE decrease, AUC increase) against the baseline.
- **Steps**:
  1. Explorer analyzes features and model structures in `src/ai/prediction_model.py` and `src/ai/vcp_ml_predictor.py`.
  2. Worker (`teamwork_preview_worker`) implements new features and integrates LightGBM & CatBoost models.
  3. Reviewer (`teamwork_preview_reviewer`) reviews codebase for code quality and compatibility.
  4. Challenger (`teamwork_preview_challenger`) runs performance comparisons.
  5. Forensic Auditor (`teamwork_preview_auditor`) audits the implementations.

### Milestone 3: Optuna Tuning & API Stability (R2 & R3)
- **Objective**: Add Optuna tuning for hyperparameters and stability controls (rate limit, retries) for data APIs.
- **Verification**: Verify hyperparameter optimization runs and saves outputs; verify retry logic handles failed API requests.
- **Steps**:
  1. Explorer plans Optuna search space and rate-limiting strategy.
  2. Worker implements Optuna script and configures retry wrappers for data fetching.
  3. Reviewer inspects code for stability and exception handling.
  4. Challenger tests rate limiting under simulated failures.
  5. Forensic Auditor verifies no cheating or bypasses.

### Milestone 4: Final E2E Verification & Forensic Audit
- **Objective**: Ensure entire codebase compiles, all tests pass, and integrity is fully verified.
- **Verification**: 100% test pass on `pytest tests/` and CLEAN audit.
- **Steps**:
  1. Run entire test suite.
  2. Run Forensic Auditor for final project audit.

# Plan - Quality Fixes in Stock Prediction Pipeline

## Objectives
Fix all 4 strategy output quality bugs in the stock prediction pipeline so that:
1. `surge_predictions.txt` contains at least 20 stocks with surge probability > 0.0% for all markets (KOSPI, KOSDAQ, KONEX, SP500) and all 4 horizons (1/3/5/20d).
2. `lead_lag_predictions.txt` includes Top 20 results for KOSPI, KOSDAQ, KONEX, and SP500.
3. `vcp_ml_predictions.txt` contains Top 10+ predictions for each market and horizon.
4. `ensemble_predictions.txt` contains at least 5 stocks with non-zero Surge%, L-L%, and VCP% for all 4 markets.
5. Ensure all code passes ruff, mypy, and existing tests.
6. Prevent empty output files by writing a "데이터 없음" or "No data" placeholder when empty.

## Milestones

### Milestone 1: Diagnosis
- **Tasks**:
  - Spawn Explorers to analyze the source code and logs for Bugs 1, 2, 3, and 4.
  - Understand why models fail to load in GHA / distributed environments.
  - Determine how to select leaders per market for Lead-Lag.
  - Identify where VCP ML models are saved/loaded and how paths differ in GHA.
- **Verification**: Explorers submit detailed findings and proposed fix strategies.

### Milestone 2: Implementation
- **Tasks**:
  - Spawn Worker to implement the fixes proposed by Explorers.
  - Run local pipeline and tests to make sure there are no syntax/logical errors.
- **Verification**: Worker provides a report showing the changes, and verifies that the pipeline runs successfully.

### Milestone 3: Review & Empirical Verification
- **Tasks**:
  - Spawn 2 Reviewers to inspect code changes for correctness, robustness, and typing (ruff and mypy).
  - Spawn 2 Challengers to run the validation scripts and verify predictions contain expected non-zero counts.
- **Verification**: Reviewers approve the changes; Challengers confirm non-zero output criteria are met.

### Milestone 4: Forensic Audit
- **Tasks**:
  - Spawn Forensic Auditor to verify no hardcoding or cheating was done.
- **Verification**: Auditor issues a CLEAN verdict.

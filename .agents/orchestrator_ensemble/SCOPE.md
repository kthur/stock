# Scope: ML Ensemble

## Architecture
- `src/analysis/ml_engine.py`: Uses `RandomForestClassifier` and `XGBClassifier` and aggregates their predictions using soft voting (weighted average) to return `ml_score`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Verify ML Ensemble | Run ML Ensemble tests and verify soft voting. | None | DONE |
| 2 | Forensic Audit | Run Forensic Auditor to confirm clean execution. | M1 | DONE |

# Task for Explorer 1

## Objective
Diagnose and analyze the 4 strategy output quality bugs in the stock prediction pipeline:
1. Bug 1: Surge classifier outputting 0.0% probability (model load paths in GHA/distributed pipeline).
2. Bug 2: Lead-Lag predictions missing for KRX markets (leader selection logic in `prediction_model.py`).
3. Bug 3: VCP ML predictions empty (model path logic in GHA/distributed environment).
4. Bug 4: Ensemble outputting 0% for KRX (consequence of Bug 1-3).
5. Output file placeholder when empty (Bug 4/R4).

## Scope
- Read-only analysis. Do NOT modify any code.
- Analyze the codebase, configuration, and logs.
- Draft specific, concrete code modification proposals for each bug.

## Key Files to Examine
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/vcp_ml_predictor.py`
- `trading_system/run_pipeline.py`
- `trading_system/merge_predictions.py`
- `.github/workflows/pipeline.yml`

## Output
Write a structured report `analysis.md` in your working directory `.agents/explorer_quality_fixes_1/`.
Include:
- Findings and root cause for each bug.
- Step-by-step logic chain and evidence.
- Proposed code changes (Before/After snippets).

# Dispatch: Explorer M0 Track 2 (R4 ML Predictors & Alpha Returns Maximization)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track2

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Objective
Investigate all failing test cases and discrepancies related to Requirement R4:
- R4: Machine Learning Predictors and Returns Maximization Logic Recovery
  - `TransformerPredictor`: forward tensor shape mismatch, sequence dimensions, training-inference pipeline, model saving and loading integrity.
  - `Sprint3` Multivariate LSTM time-series inference.
  - `v7` alpha hurdle rate (P90 hurdle rate) and unscaled trading transaction costs numerical errors.

Relevant tests to investigate:
- `tests/test_transformer_predictor.py`
- `tests/test_sprint3_alpha_refactor.py`
- `tests/test_v7_returns_maximization.py`
(Run pytest using `trading_system\.venv\Scripts\python.exe -m pytest tests -k "test_transformer_predictor or test_sprint3_alpha_refactor or test_v7_returns_maximization"`)

Relevant implementation source files:
- `src/ai/transformer_predictor.py` (or related transformer module under `src/ai/`)
- `src/ai/prediction_model.py`
- `src/ai/` / `src/strategy/` / `src/portfolio/` returns maximization scripts

## Instructions
1. Run targeted pytest commands using `trading_system\.venv\Scripts\python.exe` to reproduce and identify every failing test in Track 2.
2. Read the source code and error stack traces to understand the tensor shapes, math errors, or logic bugs.
3. Formulate a concrete, step-by-step fix strategy with exact file paths, line numbers, and proposed code modifications.
4. Output your full report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track2\handoff.md`.

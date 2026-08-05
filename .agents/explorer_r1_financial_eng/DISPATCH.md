# DISPATCH for Explorer R1 — Financial Engineering & Model Optimization

Target Scope: R1. Financial Engineering & Model Optimization
1. Verify PCA Symmetric ZCA factor orthogonalization and correlation suppression under all 6 market regimes to prevent multi-collinearity.
2. Ensure Isotonic Regression calibrators and rolling Sharpe weights seamlessly adapt without signal degradation.

Original Request File: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
Master Project File: `d:\Finance\code\stock\.agents\orchestrator_eval_opt\PROJECT.md`
Working Directory: `d:\Finance\code\stock\.agents\explorer_r1_financial_eng`

Your Role: `teamwork_preview_explorer`
Tasks:
- Read `ORIGINAL_REQUEST.md` and `PROJECT.md`.
- Thoroughly inspect relevant code in `src/ai/ensemble_scorer.py`, `src/ai/prediction_model.py`, `src/ai/optuna_tuner.py`, and test files in `tests/`.
- Verify how PCA ZCA matrix calculation handles matrix condition numbers, regime changes, eigenvalue clamping, covariance shrinkage, and correlation suppression.
- Inspect Isotonic Regression calibrators (`IsotonicCalibrator` / `IsotonicRegression`) and rolling Sharpe weighting implementation, handling of edge cases, missing signals, or zero variance.
- Formulate concrete, actionable recommendations and a step-by-step fix/improvement strategy.
- Produce `handoff.md` in `d:\Finance\code\stock\.agents\explorer_r1_financial_eng` detailing findings, logic chain, evidence, caveats, and recommendations.

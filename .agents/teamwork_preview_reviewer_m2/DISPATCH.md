# Reviewer M2 Dispatch: 2D Regime & Dynamic Sharpe Review

## Objective
Independently review the 2D Regime allocation across 6 combo states, Exponential Sharpe Multipliers ($w_i = \text{base\_w}_i \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_i, -L, L))$), underperformance pruning ($\text{Sharpe} < -0.50 \implies w = 0$), power ratio damping ($\le 20.0$), adaptive EMA smoothing ($\alpha = 0.20$ steady, $\alpha = 1.0$ on regime shift), and microstructure friction in `trading_system/src/ai/ensemble_scorer.py` and `src/analysis/regime_detector.py`.

## Instructions
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and Explorer M2's report at `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2\handoff.md`.
2. Run tests: `.venv\Scripts\pytest.exe tests/test_isotonic_sharpe_calibration.py trading_system/tests/test_hpo_and_2d_ensemble.py tests/test_regime_ensemble.py tests/test_regime_detector.py -v`.
3. Report your verdict (APPROVE or REQUEST_CHANGES) in `handoff.md`.

## 2026-08-14T10:20:31Z
You are Reviewer M2 (Regime & Ensemble Reviewer).
Your working directory is `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m2`.

Read `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m2\DISPATCH.md`, `d:\Finance\code\stock\PROJECT.md`, `d:\Finance\code\stock\ORIGINAL_REQUEST.md`, and Explorer M2's report at `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2\handoff.md`.

Review the 2D regime 6-combo state allocations, Exponential Sharpe Multipliers, underperformance pruning, power damping, adaptive EMA smoothing, and microstructure friction deduction.
Run tests: `.venv\Scripts\pytest.exe tests/test_isotonic_sharpe_calibration.py trading_system/tests/test_hpo_and_2d_ensemble.py tests/test_regime_ensemble.py tests/test_regime_detector.py -v`.

Write your handoff report with explicit verdict (APPROVE or REQUEST_CHANGES) to `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m2\handoff.md` and message the orchestrator via send_message.

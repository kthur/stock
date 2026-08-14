# Worker M2 Dispatch: Dynamic Sharpe Pruning & NaN Resilience Fixes

## Objective
Apply the 2 refinements identified by Challenger M2 Gen 2 in `trading_system/src/ai/ensemble_scorer.py`:
1. In `compute_dynamic_weights_from_sharpe()` (around lines 795–830):
   - When iterating `rolling_sharpes`, sanitize values: `val = rolling_sharpes.get(strategy, 0.0)`; if `val is None or np.isnan(val)` or `not np.isfinite(val)`, treat as `0.0`.
2. Ensure underperformance pruning is not diluted by EMA smoothing:
   - Keep track of pruned strategies (`pruned_strategies = {s for s, sh in clean_sharpes.items() if sh < -0.50}`).
   - After applying EMA smoothing:
     ```python
     for s in pruned_strategies:
         smoothed[s] = 0.0
     # Re-normalize smoothed weights
     total_w = sum(smoothed.values())
     if total_w > 0:
         smoothed = {k: v / total_w for k, v in smoothed.items()}
     ```
3. Run test suites to verify 100% pass:
   - `pytest tests/test_isotonic_sharpe_calibration.py trading_system/tests/test_hpo_and_2d_ensemble.py -v`
   - `pytest trading_system/tests/test_regime_detector.py trading_system/tests/test_regime_ensemble.py -v`
   - Run Challenger M2 stress test script to confirm 0 failures.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
- Verified code changes in `trading_system/src/ai/ensemble_scorer.py`.
- Handoff report in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md`.

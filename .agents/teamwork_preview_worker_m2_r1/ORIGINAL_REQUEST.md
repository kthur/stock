## 2026-07-25T01:20:58Z
You are Worker 2 (`teamwork_preview_worker`) working in `.agents/teamwork_preview_worker_m2_r1/`.
Your objective is to complete Requirement 1 (R1: Optuna HPO for 5 Strategies & 2D Regime + Rolling Sharpe Dynamic Ensemble Weighting).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Create workspace directory `.agents/teamwork_preview_worker_m2_r1/` if it doesn't exist.
2. Create `trading_system/src/ai/optuna_tuner.py` (`OptunaStrategyTuner`) implementing Optuna hyperparameter optimization across all 5 strategies:
   - Strategy 1: Regression (XGBoost / LightGBM / CatBoost)
   - Strategy 2: Surge Classifier
   - Strategy 3: Lead-Lag Matrix (leaders count, lag window, corr cutoff)
   - Strategy 4: VCP Rule Detector (contraction thresholds, volume ratio, near high, score weights)
   - Strategy 5: VCP ML Predictor (market classifiers, scale_pos_weight, window step)
   - Use `TimeSeriesSplit(n_splits=3)` validation.
   - Save/load parameters to `trading_system/models/tuned_params.json` and ensure model modules load these parameters.
3. Update `trading_system/src/ai/ensemble_scorer.py`:
   - Add `REGIME_2D_WEIGHTS` covering 6 regime combo states (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`).
   - Integrate Strategy 4 (`vcp_rule` / `vcp_patterns_df`) into `REGIME_WEIGHTS`, `REGIME_2D_WEIGHTS`, and `calculate_ensemble_score()` so all 5 strategies contribute to the ensemble score.
   - Update `compute_dynamic_weights_from_sharpe()` to apply exponential Sharpe scaling w_i proportional to w_i_base * exp(gamma * S_i).
4. Update `trading_system/src/analysis/regime_detector.py`:
   - Ensure `predict_2d_regime()` outputs standard string 2D combo states.
5. Update `trading_system/run_pipeline.py` and `trading_system/merge_predictions.py`:
   - Integrate 2D regime prediction, rolling Sharpe calculation, 5-strategy score aggregation, and formatting in `ensemble_predictions.txt`.
6. Add unit tests in `trading_system/tests/test_hpo_and_2d_ensemble.py` and run `.venv/bin/python -m pytest trading_system/tests/ -v`. Fix any failures until all tests pass 100%.
7. Write `.agents/teamwork_preview_worker_m2_r1/changes.md` and `handoff.md`, and send a message to parent (Recipient: "parent") when completed.

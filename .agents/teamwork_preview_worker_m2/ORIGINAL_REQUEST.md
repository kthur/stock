## 2026-07-25T01:20:29Z
You are Worker 1 (`teamwork_preview_worker`) working in `.agents/teamwork_preview_worker_m2/`.
Your objective is to implement Requirement 1 (R1: AI Model Precision & Auto-tuning with 2D Regime + Rolling Sharpe Dynamic Ensemble Weighting).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Create your workspace `.agents/teamwork_preview_worker_m2/` if it doesn't exist.
2. Create/update `src/ai/optuna_tuner.py` (`OptunaStrategyTuner`) supporting Optuna hyperparameter optimization across all 5 strategies:
   - Strategy 1: Regression (XGBoost / LightGBM / CatBoost)
   - Strategy 2: Surge Classifier (1d, 3d, 5d, 20d horizons)
   - Strategy 3: Lead-Lag Matrix (leader count, lag window, correlation threshold)
   - Strategy 4: VCP Pattern Detector (rule thresholds, contraction ratio, near-high cutoff, score weights)
   - Strategy 5: VCP ML Predictor (market classifiers, window step size, scale_pos_weight)
   - Use `TimeSeriesSplit(n_splits=3)` validation to prevent look-ahead bias.
   - Output/save tuned hyperparameters to `models/tuned_params.json` and ensure model modules (`prediction_model.py`, `vcp_detector.py`, `vcp_ml_predictor.py`) dynamically load tuned parameters.
3. 2D Market Regime Matrix & 5-Strategy Dynamic Ensemble Weighting:
   - Update `src/analysis/regime_detector.py` to ensure `predict_2d_regime()` outputs 6 combo states (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`).
   - Update `src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`) to define `REGIME_2D_WEIGHTS` for all 5 strategies (including Strategy 4 VCP Rule Detector).
   - Implement rolling Sharpe ratio calculation for all 5 strategies and wire dynamic exponential Sharpe weight adjustment: w_i_dynamic proportional to w_i_base * exp(gamma * S_i).
   - Update `trading_system/run_pipeline.py` and `trading_system/merge_predictions.py` to integrate 2D regime prediction, rolling Sharpe calculation, 5-strategy score aggregation, and formatting.
4. Run unit and integration tests using `.venv/bin/python -m pytest trading_system/tests/ -v`. Fix any issues to ensure 100% test pass.
5. Create comprehensive tests in `trading_system/tests/test_hpo_and_2d_ensemble.py` to verify HPO tuning, 2D regime matrix prediction, and dynamic Sharpe ensemble weighting.
6. Record your work in `.agents/teamwork_preview_worker_m2/changes.md` and `handoff.md`, then send a message to parent (Recipient: "parent") with summary and file paths.

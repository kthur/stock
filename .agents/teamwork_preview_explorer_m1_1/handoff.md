# Handoff Report: Requirement 1 (R1) Audit & Technical Design

**Agent**: Explorer 1 (`teamwork_preview_explorer`)  
**Working Directory**: `.agents/teamwork_preview_explorer_m1_1/`  
**Date**: 2026-07-25  

---

## 1. Observation

Direct observations from codebase inspection across `d:\Finance\code\stock`:

1. **Optuna Environment**:
   - Running `.venv\Scripts\python.exe -c "import optuna; print(optuna.__version__)"` confirmed Optuna `4.9.0` is installed.
   - `trading_system/requirements.txt` includes `optuna>=3.0`.
2. **Existing Hyperparameter Tuning Capabilities**:
   - `trading_system/scripts/tune_models.py` performs Optuna searches for XGBoost, LightGBM, and CatBoost regressors (Strategy 1) and surge classifiers (Strategy 2), outputting `models/tuned_params.json`.
   - `OnDevicePredictionModel` (`src/ai/prediction_model.py:240-257`) and `VCPSurgePredictor` (`src/ai/vcp_ml_predictor.py:93-104`) load `tuned_params.json` on initialization.
   - **Absence of HPO for Strategy 3, 4, 5**:
     * Strategy 3 (`train_lead_lag` in `prediction_model.py:650`): Leader count (50), lag days (1), and threshold (0.0) are hardcoded.
     * Strategy 4 (`detect_vcp` in `src/ai/vcp_detector.py:37-97`): Contraction windows (`[-5:]`, `[-15:-5]`, `[-35:-15]`, `[-60:-35]`), volume declining ratio (`0.85`), near-high ratio (`0.6`), score weights `(25, 15, 15, 15, 15, 15)`, and score cutoff (`50`) are hardcoded.
     * Strategy 5 (`vcp_ml_predictor.py`): Reuses `surge_*` kwargs from `tuned_params.json`, but lacks dedicated VCP ML feature/window step search space.
3. **Regime Identification**:
   - `MarketRegimeDetector` (`src/analysis/regime_detector.py`) uses a 3-component Gaussian Mixture Model (GMM) on rolling return/volatility of S&P 500.
   - `predict_regime()` (`regime_detector.py:99`) returns 1D integer regime code (`0`=BEAR, `1`=SIDEWAYS, `2`=BULL).
   - `predict_2d_regime()` (`regime_detector.py:157`) computes 2D direction $\times$ volatility (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`).
   - `run_pipeline.py:1181-1183` invokes `predict_regime_label()` (1D) and passes 1D regime code to `EnsembleScoringEngine`.
4. **Ensemble Strategy Weighting**:
   - `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py:15`) defines `REGIME_WEIGHTS` for 1D regimes (0, 1, 2) covering **4 strategies**: `regression`, `surge`, `lead_lag`, `vcp_ml`.
   - Strategy 4 (`vcp_rule` / `detect_vcp`) is **completely missing** from `REGIME_WEIGHTS` and `calculate_ensemble_score()` (`ensemble_scorer.py:62`).
   - `compute_dynamic_weights_from_sharpe()` (`ensemble_scorer.py:39`) is implemented but not called in `run_pipeline.py:1475`.

---

## 2. Logic Chain

1. **Observation**: HPO exists for Strategies 1 & 2 via `tune_models.py`, but Strategies 3 (Lead-Lag), 4 (VCP Rule), and 5 (VCP ML) lack Optuna tuning interfaces.
   - **Reasoning**: To fulfill Requirement R1 ("Optuna HPO for 5 strategies"), a unified tuner module (`src/ai/optuna_tuner.py`) must be built to define search spaces, `TimeSeriesSplit` cross-validation objectives, and JSON parameter persistence for all 5 strategies.
2. **Observation**: `MarketRegimeDetector.predict_2d_regime()` returns 6 combo states (3 direction $\times$ 2 volatility), but `EnsembleScoringEngine` only defines weights for 3 1D direction states.
   - **Reasoning**: To implement "2D regime detection (market state matrix)", `EnsembleScoringEngine.REGIME_2D_WEIGHTS` must be expanded to cover all 6 combo states (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`).
3. **Observation**: `EnsembleScoringEngine` currently merges only 4 strategy DataFrames, omitting Strategy 4 (VCP Pattern Detector).
   - **Reasoning**: R1 requires ensemble weighting across all 5 strategies. `vcp_detector.py` output scores must be merged into `calculate_ensemble_score()` alongside the other 4 strategies.
4. **Observation**: `compute_dynamic_weights_from_sharpe()` exists in `ensemble_scorer.py` but is unlinked in `run_pipeline.py`.
   - **Reasoning**: To complete "rolling Sharpe dynamic ensemble weighting", `run_pipeline.py` must track or calculate rolling strategy Sharpe ratios over out-of-sample historical backtest windows and feed them to `EnsembleScoringEngine`.

---

## 3. Caveats

- **Historical Price Data Requirement for HPO**: Optuna HPO for Lead-Lag, VCP Rule, and VCP ML requires sufficient historical price/indicator data (at least 200 trading days). When DB is empty during offline testing, mock dataset fallback logic (`create_mock_tuning_data`) must be maintained.
- **Computation Time of Full HPO**: Running Optuna studies across 5 strategies $\times$ 4 markets $\times$ 3 TimeSeriesSplit folds could take several minutes. `n_trials` should be configurable (e.g. 5 for fast tests/pipelines, 50 for deep offline HPO).
- **Alternative Models (LightGBM/CatBoost)**: GPU vs CPU execution parameters (`device_type`, `thread_count`) must be safely handled depending on PyTorch CUDA detection (`_HAS_CUDA`).

---

## 4. Conclusion

The trading system codebase is well-structured and ready for Requirement 1 implementation:
- Optuna HPO infrastructure is verified and active for XGBoost/LightGBM/CatBoost regressors and classifiers.
- The remaining work for R1 involves:
  1. Creating a unified `OptunaStrategyTuner` in `src/ai/optuna_tuner.py` for all 5 strategies using `TimeSeriesSplit`.
  2. Extending `EnsembleScoringEngine` to support a 2D Regime Weight Matrix (6 states) $\times$ 5 strategies (including VCP Pattern Detector).
  3. Linking rolling strategy Sharpe calculations in `run_pipeline.py` for dynamic softmax weight adaptation.

Detailed design details, search spaces, equations, and file modification maps are documented in `.agents/teamwork_preview_explorer_m1_1/analysis.md`.

---

## 5. Verification Method

To independently verify the findings in this report:

1. **Verify Optuna Package**:
   ```bash
   .venv/bin/python -c "import optuna; print(optuna.__version__)"
   ```
2. **Verify Existing HPO Tests**:
   ```bash
   .venv/bin/python -m pytest trading_system/tests/test_tuning_and_retry.py -v
   ```
3. **Verify Existing Regime & Ensemble Tests**:
   ```bash
   .venv/bin/python -m pytest trading_system/tests/test_regime_ensemble.py -v
   ```
4. **Inspect Key Source Files**:
   - `trading_system/src/ai/prediction_model.py` (lines 146-285: `tuned_params.json` loading)
   - `trading_system/src/ai/vcp_detector.py` (lines 37-97: hardcoded VCP parameters)
   - `trading_system/src/ai/vcp_ml_predictor.py` (lines 56-106: VCP ML kwargs)
   - `trading_system/src/ai/ensemble_scorer.py` (lines 15-60: 4-strategy 1D `REGIME_WEIGHTS` and Sharpe formula)
   - `trading_system/src/analysis/regime_detector.py` (lines 157-180: `predict_2d_regime`)

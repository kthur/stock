# Codebase Audit & Technical Design Report: Requirement 1 (R1)
**Optuna HPO for 5 Strategies & 2D Regime Rolling Sharpe Dynamic Ensemble Weighting**

**Author**: Explorer 1 (`teamwork_preview_explorer`)  
**Workspace**: `.agents/teamwork_preview_explorer_m1_1/`  
**Date**: 2026-07-25  

---

## 1. Executive Summary

This codebase audit investigates the current state of hyperparameter tuning, market regime detection, and multi-strategy ensemble weighting across the trading system (`d:\Finance\code\stock`). 

Requirement 1 (R1) requires:
1. **Optuna Hyperparameter Optimization (HPO)** across all 5 active trading strategies:
   - Strategy 1: XGBoost/LightGBM/CatBoost Regression
   - Strategy 2: Surge Classifier (20%+ return target)
   - Strategy 3: Index & Sector Lead-Lag Matrix
   - Strategy 4: VCP (Volatility Contraction Pattern) Detector (Rule-based)
   - Strategy 5: VCP ML Predictor (Market-specific XGB/LGB/Cat classifiers)
2. **2D Market Regime Detection Matrix** (Direction $\times$ Volatility = 6 states) combined with **Rolling Sharpe Ratio Dynamic Ensemble Weighting**.

### Summary of Audit Findings
- **Optuna Status**: `optuna` (v4.9.0) is installed. Standalone scripts `trading_system/scripts/tune_models.py` and `trading_system/scripts/tune_hyperparams.py` tune regressors and surge classifiers (Strategies 1 & 2) and output `models/tuned_params.json`. However, **Strategies 3 (Lead-Lag), 4 (VCP Rule), and 5 (VCP ML)** lack dedicated Optuna search spaces or parameter integration.
- **Regime Detection Status**: `MarketRegimeDetector` (`src/analysis/regime_detector.py`) uses GMM on S&P 500 rolling returns and volatility. A 2D helper `predict_2d_regime()` exists returning 6 combo states (e.g., `BULL_LOW_VOL`, `BEAR_HIGH_VOL`), but `run_pipeline.py` currently only utilizes 1D regime integers (0=BEAR, 1=SIDEWAYS, 2=BULL).
- **Ensemble Weighting Status**: `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`) defines 1D `REGIME_WEIGHTS` covering only **4 strategies** (`regression`, `surge`, `lead_lag`, `vcp_ml`). **Strategy 4 (VCP Rule Detector)** is completely excluded from ensemble scoring. Furthermore, `compute_dynamic_weights_from_sharpe()` is defined in `ensemble_scorer.py`, but rolling Sharpe calculation is not wired in `run_pipeline.py`.

---

## 2. Codebase Strategy Mapping (The 5 Strategies)

| Strategy | File Location | Key Class / Function | Inputs | Current Parameters & Hardcoded Values |
|---|---|---|---|---|
| **Strategy 1: Regression** | `src/ai/prediction_model.py` | `OnDevicePredictionModel.models` | 23 ALL_FEATURES + Global Indicators | `n_estimators=500`, `max_depth=5`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`, `reg_lambda=1.0`. Loaded from `tuned_params.json['xgb'/'lgb'/'cat']`. |
| **Strategy 2: Surge Classifier** | `src/ai/prediction_model.py` | `OnDevicePredictionModel.surge_models` | 23 ALL_FEATURES + Global Indicators | Target $\ge 20\%$ return in 1, 3, 5, 20d. `max_depth=4`, `min_child_weight=10`, `max_delta_step=5`. Loaded from `tuned_params.json['surge_*']`. |
| **Strategy 3: Lead-Lag Matrix** | `src/ai/prediction_model.py` | `OnDevicePredictionModel.train_lead_lag()` | TOP 50 Market Cap Leaders daily returns | Leader count = 50 (hardcoded), lag = 1 (hardcoded), correlation threshold > 0.0 (hardcoded). |
| **Strategy 4: VCP Pattern Detector** | `src/ai/vcp_detector.py` | `detect_vcp()` | Raw OHLCV DataFrame | Windows `[-5:]`, `[-15:-5]`, `[-35:-15]`, `[-60:-35]`. Contraction multiplier `1.05`, volume decline `< 0.85*vol_60d`, near high `> 0.6`, score weights `(25, 15, 15, 15, 15, 15)`, tightness thresholds `<4` (+20), `<7` (+12), `<10` (+6). **All hardcoded**. |
| **Strategy 5: VCP ML Predictor** | `src/ai/vcp_ml_predictor.py` | `VCPSurgePredictor` | 11 VCP Features + ALL_FEATURES | 4 markets (KOSPI, KOSDAQ, KONEX, SP500). Uses `tuned_params.json` for base kwargs, but lacks dedicated VCP ML feature/window step Optuna study. |

---

## 3. Assessment of Hyperparameter Tuning (Optuna)

### Installed Infrastructure
- **Environment**: Optuna version `4.9.0` is verified and installed in `.venv`.
- **Existing Scripts**:
  1. `trading_system/scripts/tune_models.py`: Chronological split (80% train, 20% validation). Optimizes XGBoost, LightGBM, CatBoost regressors (MSE minimization) and classifiers (AUC maximization). Saves results to `models/tuned_params.json`.
  2. `trading_system/scripts/tune_hyperparams.py`: `TimeSeriesSplit(3)` cross-validation script for XGBoost regressor and surge classifier.
  3. `src/analysis/ml_engine.py`: Contains `MLEngine.tune_hyperparameters()` for individual stock model tuning.

### Identified HPO Gaps
1. **Missing Strategy 3 (Lead-Lag) HPO**: No script or method tunes the number of market leaders (10–100), lag window (1–5 days), rolling correlation window (20–120 days), or minimum correlation threshold (0.1–0.5).
2. **Missing Strategy 4 (VCP Pattern Detector) HPO**: `vcp_detector.py` uses fixed heuristics. Optuna should tune window step sizes, volume contraction ratio, near-high threshold, and score weights to maximize out-of-sample breakout return Sharpe ratio.
3. **Missing Strategy 5 (VCP ML) Dedicated HPO**: VCP ML uses 11 VCP-specific features and windowed sliding historical samples (`_windowed_vcp_features`). Its window step size (default 20), positive class weighting (`scale_pos_weight`), and feature selection lack Optuna tuning.
4. **Validation Methodology**: `tune_models.py` uses a simple static 80/20 chronological split, whereas financial time-series require `TimeSeriesSplit` with purged validation margins to avoid look-ahead bias and autocorrelation leakage.
5. **Pipeline Integration**: HPO runs only manually via `tune_models.py`. There is no automated module to trigger HPO periodically or load structured configuration.

---

## 4. Assessment of Regime Identification & Ensemble Weighting

### 1D vs 2D Regime Detection
- `MarketRegimeDetector` (`src/analysis/regime_detector.py`) uses a 3-component Gaussian Mixture Model (GMM) trained on 20-day rolling mean return and rolling volatility of S&P 500.
- `predict_regime()` returns 1D integer codes: `0` (BEAR), `1` (SIDEWAYS), `2` (BULL).
- `predict_2d_regime()` produces a 2D matrix ($3 \times 2 = 6$ states):
  - Direction: `BEAR`, `SIDEWAYS`, `BULL`
  - Volatility: `LOW_VOL`, `HIGH_VOL`
  - States: `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`.
- **Gap**: `run_pipeline.py` currently only invokes `predict_regime()` (1D) and passes 1D integer codes to `EnsembleScoringEngine`.

### Ensemble Strategy Weighting & Rolling Sharpe
- `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`) defines `REGIME_WEIGHTS` for 1D regimes:
  - `BEAR`: Regression (70%), Lead-Lag (20%), VCP ML (10%), Surge (0%)
  - `SIDEWAYS`: Regression (35%), Lead-Lag (35%), Surge (15%), VCP ML (15%)
  - `BULL`: Surge (40%), VCP ML (40%), Regression (15%), Lead-Lag (5%)
- **Gap 1 (Excluded Strategy)**: **Strategy 4 (VCP Rule Pattern Detector)** is completely missing from `REGIME_WEIGHTS` and `calculate_ensemble_score()`.
- **Gap 2 (2D Weights Missing)**: No `REGIME_2D_WEIGHTS` table exists for the 6 2D matrix states (e.g. low-vol bull vs high-vol bull requires different weight allocations).
- **Gap 3 (Unlinked Rolling Sharpe)**: `compute_dynamic_weights_from_sharpe(rolling_sharpes, regime)` is implemented in `ensemble_scorer.py`, but `run_pipeline.py` does not compute strategy rolling Sharpes during out-of-sample execution nor pass them to `calculate_ensemble_score()`.

---

## 5. Technical Design & Architecture Plan for R1

### Component A: Unified Optuna HPO Framework (`src/ai/optuna_tuner.py`)
Create a consolidated HPO module `OptunaStrategyTuner` supporting all 5 strategies using `TimeSeriesSplit(n_splits=3)`:

```
                  ┌──────────────────────────────────────────┐
                  │       OptunaStrategyTuner (n_trials=20)  │
                  └────────────────────┬─────────────────────┘
                                       │
      ┌──────────────┬─────────────────┼─────────────────┬──────────────┐
      ▼              ▼                 ▼                 ▼              ▼
 Strategy 1     Strategy 2        Strategy 3        Strategy 4     Strategy 5
 Regression       Surge            Lead-Lag         VCP Rule        VCP ML
(MSE Target)   (AUC Target)      (Sharpe Target)  (Sharpe Target) (AUC Target)
      │              │                 │                 │              │
      └──────────────┴─────────────────┼─────────────────┴──────────────┘
                                       ▼
                       `models/tuned_params.json` &
                      `config/strategy_params.json`
```

#### Optuna Search Spaces & Objective Metrics:

1. **Strategy 1 (Regression)**:
   - Parameters: `n_estimators` [50–300], `max_depth` [3–8], `learning_rate` [0.01–0.15], `subsample` [0.6–1.0], `colsample_bytree` [0.6–1.0], `reg_lambda` [0.1–10.0], `reg_alpha` [0.0–5.0].
   - Objective: Minimize Validation RMSE across TimeSeriesSplit.

2. **Strategy 2 (Surge Classifier)**:
   - Parameters: `n_estimators` [50–300], `max_depth` [3–8], `learning_rate` [0.01–0.15], `subsample` [0.6–1.0], `colsample_bytree` [0.6–1.0], `min_child_weight` [1–20], `scale_pos_weight` [1–50].
   - Objective: Maximize Validation ROC-AUC across TimeSeriesSplit.

3. **Strategy 3 (Lead-Lag Matrix)**:
   - Parameters: `n_leaders` [10–100], `corr_threshold` [0.10–0.50], `lag_days` [1–5], `decay_factor` [0.80–1.00].
   - Objective: Maximize out-of-sample forward 5d/20d follower return correlation / Sharpe.

4. **Strategy 4 (VCP Pattern Detector Rule)**:
   - Parameters: `vol_declining_ratio` [0.70–0.95], `near_high_threshold` [0.40–0.80], `tightness_cutoff` [3.0–8.0], `score_threshold` [40.0–70.0], weights `w_decreasing`, `w_vol`, `w_ma50`, `w_ma200`, `w_near_high`.
   - Objective: Maximize out-of-sample 20d breakout return Sharpe ratio.

5. **Strategy 5 (VCP ML Predictor)**:
   - Parameters: `n_estimators` [50–300], `max_depth` [3–8], `learning_rate` [0.01–0.15], `subsample` [0.6–1.0], `colsample_bytree` [0.6–1.0], `min_child_samples` [5–30], `scale_pos_weight` [1–50], `vcp_step_size` [10–30].
   - Objective: Maximize Validation ROC-AUC across TimeSeriesSplit.

---

### Component B: 2D Market Regime Matrix & 5-Strategy Dynamic Ensemble Weighting

#### 1. 2D Regime Matrix Configuration (6 Combo States $\times$ 5 Strategies)

Update `EnsembleScoringEngine` in `src/ai/ensemble_scorer.py`:

```python
REGIME_2D_WEIGHTS = {
    # BEAR Regimes (Defensive capital protection)
    'BEAR_LOW_VOL': {
        'regression': 0.55, 'surge': 0.00, 'lead_lag': 0.25, 'vcp_rule': 0.10, 'vcp_ml': 0.10
    },
    'BEAR_HIGH_VOL': {
        'regression': 0.65, 'surge': 0.00, 'lead_lag': 0.25, 'vcp_rule': 0.05, 'vcp_ml': 0.05
    },
    # SIDEWAYS Regimes (Sector rotation & pattern setups)
    'SIDEWAYS_LOW_VOL': {
        'regression': 0.25, 'surge': 0.10, 'lead_lag': 0.35, 'vcp_rule': 0.15, 'vcp_ml': 0.15
    },
    'SIDEWAYS_HIGH_VOL': {
        'regression': 0.40, 'surge': 0.10, 'lead_lag': 0.30, 'vcp_rule': 0.10, 'vcp_ml': 0.10
    },
    # BULL Regimes (Aggressive breakout momentum)
    'BULL_LOW_VOL': {
        'regression': 0.10, 'surge': 0.35, 'lead_lag': 0.05, 'vcp_rule': 0.20, 'vcp_ml': 0.30
    },
    'BULL_HIGH_VOL': {
        'regression': 0.20, 'surge': 0.30, 'lead_lag': 0.10, 'vcp_rule': 0.15, 'vcp_ml': 0.25
    },
}
```

#### 2. Rolling Sharpe Dynamic Weight Adjustment Formula

Given base weights $w_i^{\text{base}}$ for a 2D regime state and rolling out-of-sample Sharpe ratios $S_i$ over a 20d/60d window for each strategy $i \in \{1 \dots 5\}$:

$$w_i^{\text{dynamic}} = \frac{w_i^{\text{base}} \cdot \exp(\gamma \cdot S_i)}{\sum_{j=1}^{5} w_j^{\text{base}} \cdot \exp(\gamma \cdot S_j)}$$

Where $\gamma = 0.5$ (scaling factor preventing extreme single-strategy domination).

#### 3. 5-Strategy Unified Score Calculation

$$\text{Ensemble Score} = w_{\text{reg}} S_{\text{reg}} + w_{\text{surge}} S_{\text{surge}} + w_{\text{ll}} S_{\text{ll}} + w_{\text{vcp\_rule}} S_{\text{vcp\_rule}} + w_{\text{vcp\_ml}} S_{\text{vcp\_ml}}$$

Where each strategy score $S_i \in [0, 1]$ is normalized (rank or min-max normalization).

---

### Component C: Pipeline Integration Flow (`run_pipeline.py`)

1. **Step 7 (Training)**: Invoke `OptunaStrategyTuner.run_full_hpo()` to generate `models/tuned_params.json` before fitting models.
2. **Step 10 (Regime Detection)**: Call `regime_detector.predict_2d_regime(indicator_infer)` to obtain 2D combo label (e.g. `BULL_LOW_VOL`).
3. **Step 11 (Ensemble Scoring)**: Pass all 5 strategy outputs (`res_df`, `surge_df`, `lead_lag_df`, `vcp_patterns_df`, `vcp_ml_df`), 2D regime combo label, and rolling strategy Sharpe ratios into `scorer.calculate_ensemble_score()`.
4. **Step 12 (Report & Persistence)**: Write updated 5-strategy weights and 2D regime info to `ensemble_predictions.txt` and SQLite DB.

---

## 6. Implementation Roadmap & File Impact Summary

| Task | Target File | Description of Action |
|---|---|---|
| **Optuna Tuner** | `src/ai/optuna_tuner.py` *(New)* | Implement `OptunaStrategyTuner` with `TimeSeriesSplit(3)` for 5 strategies. |
| **Strategy HPO Hooks** | `src/ai/prediction_model.py`, `src/ai/vcp_detector.py`, `src/ai/vcp_ml_predictor.py` | Expose tuneable parameter setters and load tuned JSON configs. |
| **2D Regime Expansion** | `src/analysis/regime_detector.py` | Standardize 2D matrix classification API (`predict_2d_regime()`). |
| **5-Strategy 2D Ensemble** | `src/ai/ensemble_scorer.py` | Add `REGIME_2D_WEIGHTS` (6 states $\times$ 5 strategies), integrate Strategy 4 (`vcp_rule`), and wire rolling Sharpe formula. |
| **Pipeline Integration** | `trading_system/run_pipeline.py` | Wire 2D regime prediction, rolling Sharpe calculation, 5-strategy scoring, and output generation. |
| **Unit & Integration Tests** | `trading_system/tests/test_hpo_and_2d_ensemble.py` *(New)* | Verify 5-strategy Optuna execution, 2D regime mapping, and Sharpe weight adjustment. |

---
*Report completed by Explorer 1 (`teamwork_preview_explorer`). Ready for implementation handoff.*

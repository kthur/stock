# Forensic Audit Report: Risk Management, 2D Regime Ensemble, Optuna HPO & Portfolio Allocation

**Target System**: Stock Trading System (3,379 symbols: SP500, KOSPI, KOSDAQ, KONEX)  
**Agent**: Explorer M1-3 (Risk Management & Portfolio Construction Specialist)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m1_3`  
**Date**: 2026-07-30  

---

## 1. Executive Summary

This forensic audit evaluates the Risk Management architecture (`src/risk/risk_manager.py`), 2D Regime Ensemble Engine (`src/ai/ensemble_scorer.py`), Optuna Hyperparameter Optimization (`src/ai/optuna_tuner.py`), and Portfolio Allocation pipeline (`src/risk/position_sizing.py`, `src/risk/portfolio_optimizer.py`, `run_pipeline.py`).

### Key Audit Discoveries:
1. **Pipeline Disconnection of RiskManager**: `RiskManager` state is re-instantiated fresh inside `run_pipeline.py` at line 2395 without portfolio equity or active position memory. Peak portfolio value resets to $1,000,000 every run, rendering drawdown calculation permanently 0.0%. This cripples 25% of the `CrisisDetector` composite score, disables ATR/trailing stop-loss controls, and bypasses macro crisis liquidation rules.
2. **2D Regime Table Mismatches & Sorting Discrepancy**:
   - `REGIME_2D_WEIGHTS` contains unnormalized tables (`BEAR_LOW_VOL` sums to 0.98, `SIDEWAYS_HIGH_VOL` to 0.96, `BULL_LOW_VOL` to 0.99).
   - Calling `get_regime_reasoning_summary()` triggers side-effect EMA state mutation on `self._prev_weights`.
   - `run_pipeline.py` writes recommendation output files sorted by un-cost-adjusted `ensemble_score`, while `PortfolioAllocator` allocates capital based on net expected return (`ensemble_expected_return`), creating a contradiction between published picks and actual capital deployment.
3. **Optuna HPO Gaming & Selection Bias**:
   - **VCP Rule HPO Gaming**: 4 out of 6 suggested parameters (`decreasing_weight`, `volume_weight`, `vol_declining_threshold`, `min_vcp_score`) are never used in objective evaluation; Optuna overfits `c_ratio` and `near_high` to isolate lucky outlier stocks in 30-stock samples.
   - **Lead-Lag Selection Bias**: The objective function averages correlations $\ge \text{corr\_threshold}$, causing Optuna to artificially maximize `corr_threshold` to 0.60 to filter out lower correlations rather than improving predictive accuracy.
   - **Single-Model HPO**: Optuna tunes only XGBoost, then blindly copies hyperparameters (`n_estimators`, `max_depth`, `learning_rate`) to LightGBM and CatBoost, which use incompatible tree architectures.
4. **Synthetic White Noise Input in Risk Parity Optimization**:
   - In `ensemble_scorer.py` (lines 1133-1140), `optimize_risk_parity()` is fed **`np.random.normal` white noise** as a dummy returns matrix. Real asset covariance structures are destroyed, reducing Risk Parity to noisy equal weighting.

---

## 2. Component 1: Observation

### 2.1 Risk Management & Pipeline Integration (`src/risk/risk_manager.py` & `run_pipeline.py`)

* **Observation 1.1 — Re-instantiation of `RiskManager` without state persistence**
  * **Location**: `trading_system/run_pipeline.py`: lines 2392–2412; `trading_system/src/risk/risk_manager.py`: lines 271–310.
  * **Code Verification**:
    ```python
    # run_pipeline.py line 2395:
    from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
    risk_mgr = RiskManager()
    crisis_detector = CrisisDetector(risk_mgr)
    ```
    ```python
    # risk_manager.py line 271-287:
    def __init__(self, portfolio_value: float = 1000000, ...):
        self.portfolio_value = portfolio_value
        self.peak_value = portfolio_value
    ```
    Every pipeline execution instantiates a new `RiskManager()` with default `portfolio_value = 1000000` and `peak_value = 1000000`. No historical equity curve or live trade state is loaded from `StockPriceDB` or `trade_logs.db`.

* **Observation 1.2 — Drawdown Calculation Permanently 0.0% & Crippled Crisis Detection**
  * **Location**: `trading_system/src/risk/risk_manager.py`: lines 68–86, 131–138, 781–786.
  * **Code Verification**:
    ```python
    # risk_manager.py line 781-786:
    def calculate_drawdown(self) -> float:
        if self.peak_value == 0:
            return 0
        drawdown = (self.peak_value - self.portfolio_value) / self.peak_value
        return drawdown
    ```
    Because `self.peak_value` equals `self.portfolio_value` upon every fresh initialization, `calculate_drawdown()` evaluates to `0.0`. In `CrisisDetector.evaluate()`:
    ```python
    dd = self.rm.calculate_drawdown() # Always 0.0
    self._dd_history.append(dd)       # Appends 0.0
    ...
    composite = vix_score * 0.25 + dd_score * 0.25 + volume_score * 0.15 + trend_score * 0.10 + macro_score * 0.25
    ```
    `dd_score` is permanently `0.0`, neutralizing 25% of the composite crisis weight.

* **Observation 1.3 — Uncalled Crisis Liquidation & Buy-Block Gating**
  * **Location**: `trading_system/src/risk/risk_manager.py`: lines 247–252, 759–775; `trading_system/run_pipeline.py`: lines 2392–2412.
  * **Code Verification**:
    `RiskManager.check_crisis_liquidation()` (returns `["*ALL*"]`) and `RiskManager.get_crisis_new_buy_blocked()` (blocks new buys during SEVERE crisis) are NEVER called in `run_pipeline.py` or `oms_engine.py`. During macro crashes, `run_pipeline.py` continues generating new buy order plans.

* **Observation 1.4 — Disconnection of Adaptive ATR & Trailing Stop Loss**
  * **Location**: `trading_system/src/risk/risk_manager.py`: lines 337–435; `trading_system/src/risk/position_sizing.py`: lines 177–340.
  * **Code Verification**:
    `calculate_atr_based_stop()`, `calculate_atr_based_target()`, and `check_trailing_stop_signal()` exist in `risk_manager.py`, but are not called in `PortfolioAllocator.allocate()`. `PortfolioAllocator` sizes positions using only 20-day close-to-close standard deviation without factoring in ATR channel width or trailing stop distances.

---

### 2.2 2D Regime Ensemble Engine (`src/ai/ensemble_scorer.py` & `run_pipeline.py`)

* **Observation 2.1 — Unnormalized Weights in `REGIME_2D_WEIGHTS` Table**
  * **Location**: `trading_system/src/ai/ensemble_scorer.py`: lines 98–213.
  * **Code Verification**:
    Sum of weights across 17 strategies per 2D regime combo:
    * `BEAR_LOW_VOL`: $0.17+0.02+0.02+0.02+0.02+0.03+0.10+0.05+0.12+0.04+0.08+0.04+0.03+0.05+0.06+0.08+0.07 = \mathbf{0.98}$
    * `SIDEWAYS_HIGH_VOL`: $0.08+0.03+0.05+0.03+0.06+0.05+0.12+0.07+0.08+0.06+0.07+0.03+0.04+0.04+0.05+0.08+0.06 = \mathbf{0.96}$
    * `BULL_LOW_VOL`: $0.04+0.12+0.03+0.03+0.10+0.08+0.03+0.08+0.05+0.08+0.08+0.02+0.04+0.02+0.08+0.05+0.06 = \mathbf{0.99}$

* **Observation 2.2 — Side-Effects in `get_regime_reasoning_summary()`**
  * **Location**: `trading_system/src/ai/ensemble_scorer.py`: lines 475–497, 535–540.
  * **Code Verification**:
    ```python
    # Line 535:
    dyn_weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime)
    ```
    Inside `compute_dynamic_weights_from_sharpe()`:
    ```python
    if self._prev_weights is not None:
        ...
        smoothed[k] = self.alpha_smoothing * target_w + (1 - self.alpha_smoothing) * prev_w
    self._prev_weights = dict(dynamic_weights) # State mutation!
    ```
    Generating reasoning text mutates `self._prev_weights` and persists `prev_weights.json` to disk, triggering extra EMA smoothing steps whenever summary text is retrieved.

* **Observation 2.3 — Report Sorting Mismatch (Un-Cost-Adjusted Score)**
  * **Location**: `trading_system/run_pipeline.py`: lines 2532–2588 vs `trading_system/src/ai/ensemble_scorer.py`: line 1119.
  * **Code Verification**:
    In `ensemble_scorer.py` line 1119, `merged` is sorted by `ensemble_expected_return` (net after transaction tax, spread, and market impact).
    However, in `run_pipeline.py` line 2532:
    ```python
    m_df = ensemble_df_merged[ensemble_df_merged['market'] == market].sort_values(by='ensemble_score', ascending=False)
    ```
    `ensemble_predictions.txt` ranks and outputs stock picks sorted by raw `ensemble_score` (un-cost-adjusted). A high-friction asset (e.g. KONEX with 1.3% transaction cost) can rank as the #1 pick in reports while receiving 0 capital allocation in `PortfolioAllocator`.

* **Observation 2.4 — Impaired Raw Score Preservation in `self.raw_scores`**
  * **Location**: `trading_system/src/ai/ensemble_scorer.py`: lines 917–977.
  * **Code Verification**:
    Line 960 sets `self.raw_scores = merged.copy()`. However, before line 960:
    1. Lines 917–922 apply Isotonic/Platt calibration to `merged[col]`.
    2. Lines 931–934 apply zero-filling for missing strategies during weight sum.
    Therefore, `self.raw_scores` stores calibrated/modified values rather than raw un-calibrated NaN values required by `StrategyCoverageAnalyzer`.

---

### 2.3 Optuna Hyperparameter Optimization (`src/ai/optuna_tuner.py`)

* **Observation 3.1 — Objective Function Gaming & Unused Parameters in VCP Rule HPO**
  * **Location**: `trading_system/src/ai/optuna_tuner.py`: lines 313–338.
  * **Code Verification**:
    ```python
    def vcp_rule_objective(trial):
        c_ratio = trial.suggest_float('contraction_ratio', 0.80, 1.20)
        near_high = trial.suggest_float('near_high_cutoff', 0.50, 0.85)
        trial.suggest_float('vol_declining_threshold', 0.70, 0.95) # Unused!
        trial.suggest_float('min_vcp_score', 30.0, 70.0)             # Unused!
        trial.suggest_float('decreasing_weight', 15.0, 35.0)       # Unused!
        trial.suggest_float('volume_weight', 10.0, 25.0)           # Unused!
    ```
    4 out of 6 suggested parameters are never referenced in computing `decreasing`, `near_pivot`, or `fwd_ret`. Optuna evaluates `np.mean(forward_returns)` over a 30-stock sample, allowing Optuna to set restrictive thresholds that isolate a single lucky outlier stock (+15% gain), gaming the objective function.

* **Observation 3.2 — Selection Bias in Lead-Lag Correlation Tuning**
  * **Location**: `trading_system/src/ai/optuna_tuner.py`: lines 277–284.
  * **Code Verification**:
    ```python
    r = df_ret.iloc[:, i].shift(lag_window).corr(df_ret.iloc[:, j])
    if not np.isnan(r) and abs(r) >= corr_cutoff:
        corrs.append(abs(r))
    return float(np.mean(corrs)) if corrs else 0.0
    ```
    The objective function calculates `np.mean(corrs)` only for pairs satisfying `abs(r) >= corr_cutoff`. Higher `corr_cutoff` values filter out lower correlation pairs, mathematically raising the average. Optuna inevitably drives `corr_threshold` to the upper bound (0.60) due to threshold selection bias.

* **Observation 3.3 — Absence of Temporal CV in Strategy 3 & 4 Tuning**
  * **Location**: `trading_system/src/ai/optuna_tuner.py`: lines 243–285, 313–338.
  * **Code Verification**:
    While Strategies 1, 2, and 5 use `TimeSeriesSplit(n_splits=3)`, Strategies 3 and 4 evaluate parameters on static historical slices (`df.iloc[-10:-5]`), introducing lookahead bias and in-sample overfitting.

* **Observation 3.4 — Single-Model HPO & Pseudo-Copying to LightGBM/CatBoost**
  * **Location**: `trading_system/src/ai/optuna_tuner.py`: lines 110–123, 196–206.
  * **Code Verification**:
    Optuna optimizes only XGBoost parameters (`study_xgb`). The resulting parameters are blindly copied to LightGBM (`best_lgb`) and CatBoost (`best_cat`). Because LightGBM (leaf-wise) and CatBoost (symmetric trees) use distinct tree-building algorithms, copying XGBoost hyperparameters yields sub-optimal models for non-XGBoost frameworks.

---

### 2.4 Portfolio Construction & Asset Allocation (`src/ai/ensemble_scorer.py` & `src/risk/position_sizing.py`)

* **Observation 4.1 — Synthetic White Noise Input in Risk Parity Optimization**
  * **Location**: `trading_system/src/ai/ensemble_scorer.py`: lines 1133–1140.
  * **Code Verification**:
    ```python
    top_syms = top_candidates['symbol'].tolist()
    mock_returns = pd.DataFrame(
        np.random.normal(0.001, 0.02, (30, len(top_syms))),
        columns=top_syms
    )
    raw_weights = optimizer.optimize_risk_parity(mock_returns)
    ```
    `ensemble_scorer.py` feeds synthetic white noise (`np.random.normal`) into `PortfolioOptimizer.optimize_risk_parity()`. Real asset covariance matrix structures are discarded, collapsing Risk Parity into arbitrary equal weighting (~5% per asset) with random noise fluctuations.

* **Observation 4.2 — Arbitrary Multiplication of HRP Weights by Market Budgets**
  * **Location**: `trading_system/src/risk/position_sizing.py`: lines 251–267.
  * **Code Verification**:
    When `use_hrp=True`, `PortfolioAllocator` calculates HRP weights via hierarchical clustering, but then multiplies HRP weights by static `market_budget` factors (line 263: `hrp_w * df_candidates['market_budget'] * self.max_total_allocation`). Multiplying HRP cluster weights by pre-set market budgets violates the tree-bisection optimality of Hierarchical Risk Parity.

* **Observation 4.3 — Single-Pass Sector Exposure Constraint**
  * **Location**: `trading_system/src/risk/portfolio_optimizer.py`: lines 160–169.
  * **Code Verification**:
    `apply_factor_and_sector_constraints()` scales down sector weights that exceed 35% and renormalizes all remaining weights in a single pass. Global normalization can push previously compliant sectors over the 35% limit, requiring an iterative clipping loop.

---

## 3. Component 2: Logic Chain

```
[Observation 1.1: RiskManager instantiated fresh each pipeline run]
   │
   ▼
[Observation 1.2: peak_value == portfolio_value → calculate_drawdown() = 0.0]
   │
   ▼
[Observation 1.2: CrisisDetector dd_score = 0.0 → 25% of composite crisis score neutralized]
   │
   ▼
[Observation 1.3: Crisis liquidation and buy-blocking rules never executed in pipeline]
   │
   ▼
[Conclusion 1: Risk Management is disconnected from execution; crisis gating fails to block trades]

[Observation 2.1: REGIME_2D_WEIGHTS tables sum to 0.98, 0.96, 0.99]
   │
   ▼
[Observation 2.2: get_regime_reasoning_summary() mutates self._prev_weights EMA state]
   │
   ▼
[Observation 2.3: Text report sorts picks by ensemble_score while Allocator uses ensemble_expected_return]
   │
   ▼
[Conclusion 2: 2D Regime Engine exhibits state mutation side-effects and reporting-allocation contradictions]

[Observation 3.1: VCP Rule HPO has 4 unused parameters & overfits 30-stock samples]
   │
   ▼
[Observation 3.2: Lead-Lag HPO averages corrs >= threshold → Optuna drives threshold to 0.60 max]
   │
   ▼
[Observation 3.4: LightGBM and CatBoost copy XGBoost hyperparameters without tuning]
   │
   ▼
[Conclusion 3: HPO objectives exhibit selection bias and gaming; non-XGBoost models are unoptimized]

[Observation 4.1: ensemble_scorer.py feeds np.random.normal white noise to Risk Parity]
   │
   ▼
[Observation 4.2: PortfolioAllocator multiplies HRP weights by static market budgets]
   │
   ▼
[Conclusion 4: Portfolio optimization relies on dummy noise inputs; HRP tree optimality is broken]
```

---

## 4. Component 3: Caveats

1. **Live Broker Account Synchronization**: This audit evaluated pipeline execution and simulation logs (`run_pipeline.py`, `oms_engine.py`). Real-time execution dynamics via Kiwoom/Daishin APIs were checked via static code inspection.
2. **Optuna Execution Time Constraints**: Full HPO tuning across 3,379 symbols for 100+ trials requires significant compute time; audit observations were verified against the HPO objective functions in `optuna_tuner.py`.

---

## 5. Component 4: Conclusion & Audit Summary Matrix

| # | Finding Description | Target File & Lines | Root Cause | Severity | Portfolio Impact |
|---|-------------------|-------------------|------------|----------|------------------|
| **1.1** | `RiskManager` State Disconnection | `run_pipeline.py`:2395, `risk_manager.py`:271 | Re-instantiated fresh without persistent equity state | **HIGH** | Peak drawdown tracking fails; risk levels evaluated as 0% drawdown. |
| **1.2** | Crippled Crisis Detector Sensitivity | `risk_manager.py`:68-86, 131 | `dd_score` is permanently 0.0 | **HIGH** | 25% of composite crisis detector weight is neutralized; fails early crisis detection. |
| **1.3** | Omission of Crisis Gating Execution | `risk_manager.py`:247, `run_pipeline.py`:2392 | `check_crisis_liquidation()` & `get_crisis_new_buy_blocked()` uncalled | **HIGH** | Capital deployed into new positions during severe macro market crashes. |
| **1.4** | ATR Stop Loss Non-Integration | `risk_manager.py`:337, `position_sizing.py`:177 | `PortfolioAllocator` ignores ATR stops & trailing stops | **MEDIUM** | Position sizing ignores downside tail risk distances and ATR channel width. |
| **2.1** | Unnormalized `REGIME_2D_WEIGHTS` | `ensemble_scorer.py`:98-213 | Weight tables sum to 0.96–0.99 | **LOW** | Relative strategy weight proportions slightly distorted prior to normalization. |
| **2.2** | VIX > 40 Hard-Zeroing Distortion | `ensemble_scorer.py`:388-405 | Hard-zeroing `surge`/`vcp_ml` boosts non-defensive factors | **MEDIUM** | Unintended weight boost to momentum factors during market panics. |
| **2.3** | Summary Text EMA State Mutation | `ensemble_scorer.py`:535, 475 | `get_regime_reasoning_summary()` mutates `_prev_weights` | **MEDIUM** | Generating report text advances EMA smoothing step prematurely. |
| **2.4** | Report vs Allocation Sorting Conflict | `run_pipeline.py`:2532 vs `ensemble_scorer.py`:1119 | Text report sorts by raw score; Allocator uses net return | **HIGH** | High-friction illiquid stocks appear as #1 picks in reports but get 0 capital allocation. |
| **2.5** | Raw Score Preservation Corruption | `ensemble_scorer.py`:960 | `self.raw_scores` saved after calibration & zero-filling | **LOW** | `StrategyCoverageAnalyzer` receives filled values instead of true NaNs. |
| **3.1** | VCP Rule HPO Objective Gaming | `optuna_tuner.py`:313-338 | 4 suggested params unused; forward return overfitted on 30 stocks | **HIGH** | Optuna selects extreme thresholds that isolate single lucky outlier stocks. |
| **3.2** | Lead-Lag HPO Selection Bias | `optuna_tuner.py`:277-284 | Objective averages correlations $\ge \text{threshold}$ | **HIGH** | Optuna artificially drives threshold to 0.60 max to filter lower values. |
| **3.3** | Absence of Temporal CV in HPO | `optuna_tuner.py`:243, 313 | Static historical slice used for Strategy 3 & 4 HPO | **MEDIUM** | In-sample overfitting and lookahead bias in parameter selection. |
| **3.4** | Single-Model (XGBoost Only) HPO | `optuna_tuner.py`:110, 196 | LightGBM & CatBoost copy XGBoost hyperparameters | **MEDIUM** | Sub-optimal hyperparameters for LightGBM and CatBoost models. |
| **4.1** | Random White Noise Risk Parity Input | `ensemble_scorer.py`:1133-1140 | `np.random.normal` fed into `optimize_risk_parity()` | **HIGH** | Destroys asset covariance matrix; collapses Risk Parity into noisy equal weighting. |
| **4.2** | HRP Weight Budget Multiplication | `position_sizing.py`:251-267 | HRP cluster weights multiplied by ad-hoc market budgets | **MEDIUM** | Breaks tree-bisection mathematical optimality of Hierarchical Risk Parity. |
| **4.3** | Single-Pass Sector Constraint | `portfolio_optimizer.py`:160-169 | Single-pass sector capping and global normalization | **LOW** | Global normalization can push secondary sectors over the 35% cap. |

---

## 6. Component 5: Verification Method

### 6.1 Verification Commands
To independently verify these findings, run pytest on the audit test suite:
```bash
.venv/bin/pytest tests/test_hpo_and_2d_ensemble.py -v
.venv/bin/pytest tests/test_phase3_regime_and_rebalancing.py -v
.venv/bin/pytest tests/test_kis_safety_and_atr.py -v
```

### 6.2 Inspection Points
1. **RiskManager State & Drawdown**: Inspect `trading_system/run_pipeline.py` line 2395 to verify `RiskManager()` is instantiated without passing historical peak equity or loading DB state.
2. **Random Noise Risk Parity**: Inspect `trading_system/src/ai/ensemble_scorer.py` lines 1133–1140 to verify `np.random.normal` is used as the returns matrix input for Risk Parity.
3. **Unused Optuna Parameters**: Inspect `trading_system/src/ai/optuna_tuner.py` lines 313–338 to verify `decreasing_weight`, `volume_weight`, `vol_declining_threshold`, `min_vcp_score` are suggested but never evaluated in `vcp_rule_objective`.
4. **Lead-Lag Selection Bias**: Inspect `trading_system/src/ai/optuna_tuner.py` lines 277–284 to verify `abs(r) >= corr_cutoff` filters lower correlations before taking `np.mean(corrs)`.
5. **State Mutation in Summary**: Inspect `trading_system/src/ai/ensemble_scorer.py` lines 535 and 475 to verify `get_regime_reasoning_summary()` mutates `self._prev_weights`.

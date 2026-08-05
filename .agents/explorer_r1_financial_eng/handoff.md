# Handoff Report — R1 Financial Engineering & Model Optimization Investigation

**Date**: 2026-08-05  
**Author**: Explorer R1 (`teamwork_preview_explorer`)  
**Scope**: R1 Financial Engineering & Model Optimization — PCA Symmetric ZCA Factor Orthogonalization, Correlation Suppression across 6 Market Regimes, Isotonic Regression Calibration, and Rolling Sharpe Ratio Weight Adaptation.

---

## 1. Observation

### Codebase Scope & Structure Examined
The investigation analyzed the financial engineering and model optimization components in `trading_system/src/ai/` and configuration in `trading_system/src/config.py`:
- `trading_system/src/ai/factor_orthogonalizer.py` — `FactorOrthogonalizerEngine` (Gram-Schmidt & PCA ZCA Symmetric Decorrelation Engine).
- `trading_system/src/ai/factor_suppression.py` — `RegimeFactorSuppressionEngine` (2D Regime-based factor noise suppression & cluster penalties).
- `trading_system/src/ai/ensemble_scorer.py` — `EnsembleScoringEngine` (18-Strategy dynamic weighted ensemble, 2D regime matrix, Isotonic Regression calibration, rolling Sharpe ratio weighting, microstructure cost modeling).
- `trading_system/src/ai/optuna_tuner.py` — `OptunaStrategyTuner` (Hyperparameter optimization for regression, surge, lead-lag, VCP, and regime ensemble weights).
- `trading_system/src/config.py` — `TradingConfig` (Centralized configuration parameters).
- Test suite files in `tests/`: `test_factor_orthogonalization.py`, `test_factor_ortho_empirical_stress.py`, `test_correlation_suppression.py`, `test_hpo_and_2d_ensemble.py`.

---

### Key Technical Findings by Component

#### Component A: PCA Symmetric ZCA Factor Orthogonalization & Correlation Suppression
1. **Mathematical Implementation**:
   In `trading_system/src/ai/factor_orthogonalizer.py` (lines 107–135):
   ```python
   # Standardize matrix to zero mean, unit variance
   X_bar = (X - means) / stds
   # Correlation matrix C (K, K)
   C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
   # Eigen-decomposition
   eigenvalues, eigenvectors = np.linalg.eigh(C)
   # Ridge regularization
   eigenvalues = np.maximum(eigenvalues, self.ridge_epsilon) # ridge_epsilon = 1e-6
   # ZCA operator: C^(-1/2) = V * diag(lambda^(-1/2)) * V^T
   inv_sqrt_lambda = np.diag(1.0 / np.sqrt(eigenvalues))
   C_inv_sqrt = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))
   # Decorrelation & rescaling
   X_decorr = np.dot(X_bar, C_inv_sqrt)
   X_ortho = means + X_decorr * stds
   ```
2. **Correlation Suppression SLA Verification**:
   - `test_factor_orthogonalization.py` verifies that for 17 strategy scores with input correlation $> 0.80$, PCA ZCA decorrelation successfully reduces pairwise off-diagonal correlation below $0.30$ (`test_cross_strategy_correlation_reduction`).
   - Latency for 3,379 symbols $\times$ 17 strategies is $< 50\text{ ms}$ (`test_benchmark_orthogonalization_latency`).
3. **Regime Sensitivity & Matrix Condition Numbers**:
   - In extreme volatility / crisis environments (e.g. `CRISIS` or `BEAR_HIGH_VOL`), multi-factor scores become highly collinear ($\rho \to 1.0$).
   - Current eigenvalue regularization relies on fixed `ridge_epsilon = 1e-6`. In highly singular matrices ($N < K$ or near-duplicate outputs), $1/\sqrt{10^{-6}} = 1000.0$ can amplify numerical noise before clipping. Adding Ledoit-Wolf / shrinkage regularization ($\hat{C} = (1 - \delta) C + \delta I$) would further stabilize matrix inversion under extreme market stress.
4. **Regime Map Coverage**:
   - `REGIME_2D_WEIGHTS` in `ensemble_scorer.py` explicitly covers all 6 2D market regime states:
     - `BULL_LOW_VOL`
     - `BULL_HIGH_VOL`
     - `SIDEWAYS_LOW_VOL`
     - `SIDEWAYS_HIGH_VOL`
     - `BEAR_LOW_VOL`
     - `BEAR_HIGH_VOL`
   - `RegimeFactorSuppressionEngine` in `factor_suppression.py` maps theta/lambda parameters for these 6 regimes and 1D fallbacks (`0`, `1`, `2`, `SIDEWAYS`, `BULL`, `BEAR`).
   - When explicit string aliases like `'CRISIS'` or `'HIGH_VOL'` are passed, `factor_suppression.py` falls back to default `theta=0.65, lambda=1.0`. Adding explicit parameter mappings for `'CRISIS'` ensures optimal dampening under emergency market states.

---

#### Component B: Isotonic Regression Calibrators
1. **Implementation Analysis**:
   In `trading_system/src/ai/ensemble_scorer.py` (lines 334–389):
   - Hybrid Calibration Strategy:
     - $N < 20$: Skip calibration (insufficient data).
     - $20 \le N < 50$: Fit Platt Scaling (`LogisticRegression(C=1.0, max_iter=100)`).
     - $N \ge 50$: Fit `IsotonicRegression(out_of_bounds="clip", increasing=True)`.
   ```python
   if n_samples >= 50:
       cal = IsotonicRegression(out_of_bounds="clip", increasing=True)
       cal.fit(s[mask], y[mask])
       self._calibrators[strategy] = ('isotonic', cal)
   ```
2. **Monotonicity & Bound Preservation**:
   - Setting `increasing=True` guarantees monotonic non-decreasing calibration curves, preventing rank inversion (higher raw score $\to$ higher calibrated score).
   - Setting `out_of_bounds="clip"` prevents uncalibrated score extrapolation outside $[0.0, 1.0]$.
3. **Identified Risk / Edge Cases**:
   - **Target Label Zero-Variance**: In `fit_calibrators`, `true_labels` are binary outcomes ($1$ if gain $> 20\%$, $0$ otherwise). In severe bear markets or short windows, `true_labels` may be all $0$s. `IsotonicRegression` fitted on single-class data outputs a constant $0.0$, which flattens the strategy score to zero across all stocks.
   - **Test Suite Gap**: Currently, there are NO dedicated unit tests in `tests/` explicitly verifying `fit_calibrators` and `calibrate_scores` behavior, zero-variance target handling, or monotonicity preservation.

---

#### Component C: Rolling Sharpe Ratio Weight Adaptation
1. **Formula & Execution**:
   In `trading_system/src/ai/ensemble_scorer.py` (lines 393–417, 486–565):
   - Rolling Sharpe calculation:
     $$\text{Sharpe}_i = \frac{\bar{R}_i - r_f/252}{\sigma(R_i) + 1e-6} \times \sqrt{252}$$
   - Dynamic weight adjustment:
     $$w_i^{\text{dynamic}} = \frac{w_i^{\text{base}} \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_i, -3.0, 3.0))}{\sum_j w_j^{\text{base}} \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_j, -3.0, 3.0))}$$
2. **Cold-Start Handling**:
   - When all strategy realized returns are $0.0$, `compute_dynamic_weights_from_sharpe` injects regime-differentiated seed Sharpe ratios (e.g., boosting momentum in `BULL` and mean-reversion in `BEAR/SIDEWAYS`), preventing cold-start degeneracy.
3. **EMA Smoothing & Regime Shift State Lag**:
   - Dynamic weights are smoothed using Exponential Moving Average:
     $$w_i^{\text{smoothed}} = \alpha \cdot w_i^{\text{target}} + (1 - \alpha) \cdot w_i^{\text{prev}} \quad (\alpha = 0.2)$$
   - State persistence is saved to `models/prev_weights.json`.
   - **Transition Lag Observation**: With $\alpha = 0.2$, when a market regime abruptly transitions (e.g. `BULL_LOW_VOL` $\to$ `BEAR_HIGH_VOL`), 80% of the previous regime's weights are retained in iteration 1. It takes $\sim 10-12$ update steps for the new regime's defensive weights to reach $> 90\%$ effect.
   - **Recommendation**: Accelerate EMA smoothing ($\alpha = 1.0$) upon detecting a major 2D regime state change to immediately apply defensive / regime-aligned weights.

---

## 2. Logic Chain

1. **Premise 1 (Orthogonalization & Stability)**: PCA ZCA Symmetric Decorrelation efficiently reduces strategy correlation from $>0.80$ to $<0.30$. Under extreme market regimes (`CRISIS` / `BEAR_HIGH_VOL`), cross-factor correlations approach $1.0$, rendering the sample covariance matrix near-singular.
   - *Deduction*: Adding shrinkage regularization ($\hat{C} = (1-\delta)C + \delta I$) guarantees eigenvalue stability ($\lambda_{\min} \ge 1e-4$) without affecting orthogonalization efficacy.

2. **Premise 2 (Regime Mapping Completeness)**: `REGIME_2D_WEIGHTS` defines 6 2D regime states (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`).
   - *Deduction*: Adding explicit parameter entries for `'CRISIS'` and `'HIGH_VOL'` in `RegimeFactorSuppressionEngine` ensures high-risk factor dampening is active during extreme macro shocks.

3. **Premise 3 (Calibrator Robustness & Testing)**: `IsotonicRegression` guarantees monotonic probability mapping for $N \ge 50$. If target labels $y$ have single-class zero variance, raw fitting flattens output scores to constant 0.0.
   - *Deduction*: Checking `len(np.unique(y)) >= 2` prior to fitting protects signal integrity. Adding dedicated unit tests in `tests/test_isotonic_sharpe_calibration.py` fills the test coverage gap.

4. **Premise 4 (Rolling Sharpe Transition Responsiveness)**: Exponential Sharpe weighting ($\exp(\gamma \cdot \text{Sharpe})$) dynamically rewards performing strategies. EMA smoothing ($\alpha=0.2$) prevents high-frequency whipsaws.
   - *Deduction*: Resetting or accelerating $\alpha = 1.0$ when the 2D regime label changes eliminates weight adaptation lag during regime shifts.

---

## 3. Caveats

1. **Read-Only Scope**: This report is produced under read-only investigation rules. Code modifications in `src/` and `tests/` should be implemented by a designated worker agent or in the subsequent milestone phase.
2. **Historical Return Dependency**: Rolling Sharpe weights and Isotonic calibrators depend on available historical realized strategy return series. Cold-start seed fallbacks ensure safe degradation when historical returns are absent.
3. **Environment Persistence**: `models/prev_weights.json` and `models/tuned_params.json` are dynamically created at runtime if absent. System default fallback dictionaries in `EnsembleScoringEngine` ensure full functionality even without pre-existing JSON files.

---

## 4. Conclusion & Actionable Recommendations

### Summary Conclusion
The R1 Financial Engineering & Model Optimization architecture is mathematically robust, computationally fast ($<50\text{ ms}$ latency), and properly integrated with 2D regime detection and 18-strategy ensembling.

### Recommended Step-by-Step Improvements (for Implementer/Worker)

1. **Enhancement 1: Ledoit-Wolf Covariance Shrinkage in ZCA Orthogonalizer** (`trading_system/src/ai/factor_orthogonalizer.py`):
   - Apply shrinkage $\hat{C} = (1 - \alpha) C + \alpha I$ with $\alpha = 0.01$ or adaptive shrinkage to guarantee $\kappa(C) \le 1000$ across all 6 market regimes.

2. **Enhancement 2: Add CRISIS & Alias Mapping in Factor Suppression** (`trading_system/src/ai/factor_suppression.py`):
   - Add explicit entries for `'CRISIS'` ($\theta=0.50, \lambda=2.0$) and `'HIGH_VOL'` in `DEFAULT_REGIME_PARAMS` and `HIGH_RISK_CLUSTERS_PER_REGIME`.

3. **Enhancement 3: Class-Balance Guard in Isotonic Fitting** (`trading_system/src/ai/ensemble_scorer.py`):
   - In `fit_calibrators`, check `if len(np.unique(y[mask])) < 2: logger.warning(...); continue` to prevent single-class zero-variance score flattening.

4. **Enhancement 4: Regime Shift EMA Acceleration** (`trading_system/src/ai/ensemble_scorer.py`):
   - In `compute_dynamic_weights_from_sharpe`, detect if `self._prev_regime != regime`. If changed, set $\alpha = 1.0$ for instantaneous regime weight adaptation, then resume $\alpha = 0.2$.

5. **Enhancement 5: Add Unit Tests for Isotonic Calibration & Rolling Sharpe** (`tests/test_isotonic_sharpe_calibration.py`):
   - Add comprehensive tests covering:
     - Isotonic vs Platt calibration fitting & prediction.
     - Zero-variance target label handling.
     - Rolling Sharpe calculation with positive, negative, and zero return variances.
     - Cold-start seed application across all 6 market regime states.
     - EMA weight smoothing regime shift transition responsiveness.

---

## 5. Verification Method

To independently verify R1 Financial Engineering & Model Optimization logic and tests:

```bash
# 1. Run all factor orthogonalization, correlation suppression, and HPO unit tests:
.venv\Scripts\python.exe -m pytest tests/test_factor_orthogonalization.py tests/test_factor_ortho_empirical_stress.py tests/test_correlation_suppression.py tests/test_hpo_and_2d_ensemble.py -v
```

**Verified Test Execution Result**:
- Executed: 34 test cases across `test_factor_orthogonalization.py`, `test_factor_ortho_empirical_stress.py`, `test_correlation_suppression.py`, `test_hpo_and_2d_ensemble.py`.
- Outcome: **34 passed in 56.67s** (100% clean pass, exit code 0).


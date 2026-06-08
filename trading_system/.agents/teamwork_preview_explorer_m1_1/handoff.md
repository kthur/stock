# Handoff Report — Phase 5 / Benchmark Optimization Investigation

## 1. Observation
We have inspected the workspace directories and files to map out the current structure and prepare the optimization design:
* **Asset Allocation & Portfolio Management**:
  * `src/strategy/asset_allocation.py` contains:
    * `class AssetAllocator` (line 54) supporting strategies `"equal_weight"`, `"risk_parity"` (inverse volatility), and `"momentum"`.
    * A normalize helper `_normalize(self, weights)` (line 123) which scales the weights.
  * `src/core/asset_management.py` contains the `PortfolioManager` class (line 38) tracking cash and positions.
* **Risk & Position Sizing**:
  * `src/risk/risk_manager.py` contains `calculate_position_sizing` (line 158) with a VIX volatility scalar scaling factor `_volatility_scalar(vix)` (line 83).
  * `src/data_layer/alt_data.py` contains the method `fetch_vix(self)` (line 18) using yfinance.
* **Machine Learning & Feature Screener**:
  * `src/analysis/macro_predictor.py` contains `MacroPredictor` (line 24) wrapping `RandomForestRegressor`.
  * `src/analysis/screener.py` contains `screen_global_outperformers()` (line 133) which trains `MacroPredictor` on `MACRO_SYMBOLS_lag_N` and `stock_lag_N` returns.
* **Dash Web Dashboard**:
  * `src/web/dashboard.py` layout has tabs (line 19) including `global-macro-tab` (line 44) containing tables `us-outperformers-table` and `kr-outperformers-table`.

---

## 2. Logic Chain
From these observations, we conclude how to integrate the requested Phase 5 enhancements:
1. **R1: Risk Parity Weight Optimization**: The current `risk_parity` method in `AssetAllocator` is a simplistic inverse-volatility heuristic. True Equal Risk Contribution (ERC) should be solved by formulating a convex optimization problem:
   $$\min_x \frac{1}{2} x^T \Sigma x - \sum \ln(x_i)$$
   We should implement this in a new file `src/analysis/portfolio_optimizer.py` using `scipy.optimize.minimize` (L-BFGS-B method) and then normalize $w = x / \sum x$. This guarantees that weights sum exactly to 1.0.
2. **R2: VIX-Linked Dynamic Asset Allocation**: VIX data is fetched by `AltDataClient.fetch_vix()`. We can add `check_risk_off_signal(vix_value)` inside `src/risk/risk_manager.py` to return `vix_value >= 25`. In `calculate_position_sizing`, if the risk-off switch is active, we clamp position-level exposure to 30% of total portfolio value.
3. **R3: ML Predictor Upgrade**: The `MacroPredictor` can be upgraded to LightGBM (`LGBMRegressor`) or XGBoost (`XGBRegressor`) from its current `RandomForestRegressor`. Since the tests check performance on small datasets (size $\ge 5$), we must configure LightGBM's `min_child_samples=2` (from the default of 20) to prevent failures, and implement a fallback to `xgboost`/`RandomForest` if needed. Supply/demand feature engineering (foreign/institutional net purchase volume lags) can be simulated deterministically in `screener.py` and included in the predictor features.
4. **R4: Dash Dashboard Components**: The Dash UI can be enhanced by adding `portfolio-weights-pie` and a gauge `vix-exposure-indicator` under the 'Global Macro' tab in `src/web/dashboard.py`, using callbacks linked to the new portfolio optimizer and the VIX value.

---

## 3. Caveats
* **Data Scarcity for Small Datasets**: LightGBM can fail or result in constant predictions when trained with very few samples (e.g. 5 samples, as verified in `test_macro_stress.py`). The parameter `min_child_samples=2` has been chosen to prevent such errors, but training models on 5 samples is not recommended for production.
* **Simulation of Purchase Volumes**: Because yfinance does not distribute institutional/foreign buy-sell volume breakdowns, these features must be simulated realistically (using stock returns/volume correlation) rather than downloaded.
* **Network Mode**: We are in `CODE_ONLY` network mode, meaning we cannot access live external endpoints during investigation/testing. Offline fallbacks for market data are utilized.

---

## 4. Conclusion
The codebase is fully mapped out. Integrating the 4 requirements (R1-R4) requires:
1. Writing `src/analysis/portfolio_optimizer.py` with the SLSQP/L-BFGS-B ERC solver.
2. Modifying `src/risk/risk_manager.py` to add `check_risk_off_signal` and clamping in `calculate_position_sizing`.
3. Upgrading `src/analysis/macro_predictor.py` to LightGBM/XGBoost, and updating feature building in `src/analysis/screener.py`.
4. Enhancing layouts and callbacks in `src/web/dashboard.py`.

---

## 5. Verification Method
1. Run all unit and stress tests to verify existing logic:
   `pytest tests/test_macro.py tests/test_macro_stress.py tests/test_screener_dash_challenger.py`
2. Inspect the new file `src/analysis/portfolio_optimizer.py` and verify weights sum to 1.0.
3. Check the dashboard server starts up without layout errors:
   `python run_dashboard.py` (or similar web script).

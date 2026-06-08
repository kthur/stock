# Handoff Report — Phase 5 Benchmark Optimization Exploration

## 1. Observation
* **R1: Portfolio Risk Parity**:
  - `src/strategy/asset_allocation.py` contains the `AssetAllocator` class.
  - The `_risk_parity` method (lines 119-134) implements simple inverse-volatility weighting:
    ```python
    inv_vols[ticker] = 1.0 / vol if vol > 1e-12 else ZERO_VOL_PROXY
    ```
    This is not true Equal Risk Contribution (ERC), which must account for cross-correlations (covariance) between assets.
  - `src/analysis/quantum_optimizer.py` contains a similar inverse-volatility method `risk_parity_allocation` (lines 65-90).
* **R2: VIX-Linked Dynamic Asset Allocation**:
  - `src/risk/risk_manager.py` contains `_volatility_scalar(vix)` (lines 83-94) which scales single-trade sizing but does not clamp the total portfolio equity/cash exposure.
  - `AlternativeDataClient.fetch_vix` in `src/data_layer/alt_data.py` (lines 18-27) retrieves the VIX close price from yfinance.
  - In `src/analysis/macro_analyzer.py` (lines 195-198), US symbols (including VIX) are shifted forward by 1 day to align trading days and avoid look-ahead bias:
    ```python
    combined[sym] = combined[sym].shift(1)
    ```
* **R3: ML Model Upgrade & Net Purchase Volumes**:
  - `MacroPredictor` in `src/analysis/macro_predictor.py` uses `RandomForestRegressor` (line 13, 29).
  - Ticker feature construction in `StockScreener.screen_global_outperformers` in `src/analysis/screener.py` (lines 259-326) uses lagged macro returns and lagged stock returns, but contains no net purchase volumes or supply/demand indicators.
* **R4: Dash Dashboard**:
  - `src/web/dashboard.py` contains the Dash layout and callbacks.
  - The `Global Macro` tab (lines 44-103) contains a heatmap (`macro-correlation-heatmap`) and two data tables for expected outperformers, but lacks any pie or gauge charts.
* **Dependencies**:
  - `requirements.txt` includes `scipy>=1.7.0` (line 5), `numpy>=1.21.0,<2.0.0` (line 4), `lightgbm` and `xgboost` are verified as available.

## 2. Logic Chain
1. Since the current `_risk_parity` in `AssetAllocator` does not minimize risk contributions using covariance, we must create `src/analysis/portfolio_optimizer.py` containing a numerical ERC optimizer using `scipy.optimize.minimize`.
2. Integrating this ERC solver into `AssetAllocator` requires aligning the return histories of the assets to compute a covariance matrix, which can then be passed to the ERC solver.
3. Because VIX index >= 25 represents high risk, we can create a `check_risk_off_signal(vix_val)` method in `RiskManager` and apply a portfolio-level math clamp inside the trade submission logic to keep cash exposure >= 70% and equity exposure <= 30%.
4. To upgrade `MacroPredictor` while keeping interface compatibility, we can swap `RandomForestRegressor` with `LGBMRegressor` or `XGBRegressor`, using a low `min_child_samples` to avoid errors on small training datasets.
5. Since yfinance does not directly provide institutional and foreign net purchase volumes, we can implement a return-correlated simulator in the data layer and shift these volumes as lag features into the training data pools of the screener.
6. The Dash layout can be upgraded by inserting `dcc.Graph` elements with IDs `portfolio-weights-pie` and `vix-exposure-gauge` and writing appropriate Plotly callbacks to populate them.

## 3. Caveats
* **Network Restrictions**: As we operate in `CODE_ONLY` network mode, yfinance might fall back to simulated prices during live backtests or dashboard runs. The simulated fallbacks must accurately represent the return profiles.
* **LightGBM Sample Constraint**: LightGBM's default leaf growth parameters could fail if trained on small datasets. Ensuring `min_child_samples` is set to a low value (e.g. 2) is a critical safeguard.
* **Timezone Shifts**: The 1-day shift applied to US indices in `macro_analyzer` must be maintained when constructing lag features to prevent look-ahead bias.

## 4. Conclusion
Phase 5 benchmark optimization requires transitioning:
1. Volatility allocation from inverse-variance to true numerical ERC risk parity.
2. Sizing logic to incorporate a VIX-triggered 30/70 equity/cash exposure clamp.
3. Prediction engine from RandomForest to LightGBM/XGBoost with foreign/institutional net purchase features.
4. UI dashboard to include a Plotly pie chart and VIX exposure gauge.

All proposed blueprints have been detailed and documented in `d:\Finance\code\stock\trading_system\.agents\teamwork_preview_explorer_m1_2\analysis.md`.

## 5. Verification Method
After implementation, the following verifications can be run:
* **Unit Tests**:
  ```powershell
  python -m unittest tests/test_macro.py tests/test_macro_stress.py
  ```
* **Dashboard Server**:
  ```powershell
  python run_dashboard.py
  ```
  *(Verify that the Dash server initializes, binds to port 5000, and renders the pie and gauge charts in the Global Macro tab).*

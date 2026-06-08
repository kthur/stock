# Handoff Report: Phase 5 / Benchmark Optimization Investigation

## 1. Observation
- **R1: Portfolio Risk Parity**:
  - The existing `AssetAllocator` class in `src/strategy/asset_allocation.py` has a method `_risk_parity` that implements a simplified inverse-volatility weighting (lines 119-134):
    ```python
    def _risk_parity(self, price_data: Dict[str, List[float]]) -> Dict[str, float]:
        # Inverse-volatility weighting.
        # Weight_i = (1 / vol_i) / sum(1 / vol_j)
    ```
    This does not account for asset covariances/correlations. A true Equal Risk Contribution (ERC) optimizer that takes a covariance matrix and equalizes risk contribution does not exist.
  - NumPy and SciPy are both fully installed and importable in the workspace (verified via CLI task `python -c "import scipy"`).
- **R2: VIX-Linked Dynamic Asset Allocation**:
  - `src/risk/risk_manager.py` contains `calculate_position_sizing` (lines 158-193) which scales size using a volatility scalar `_volatility_scalar(vix)` (lines 83-94) but lacks an explicit risk-off flag/logic or a hard 30% equity / 70% cash cap.
  - VIX fetching is supported via `AlternativeDataClient().fetch_vix()` in `src/data_layer/alt_data.py`.
- **R3: Machine Learning Model Upgrade**:
  - `src/analysis/macro_predictor.py` uses `RandomForestRegressor` from `sklearn.ensemble` (line 13).
  - Both `lightgbm` and `xgboost` are fully installed and importable in the workspace (verified via CLI tasks).
  - No features or references for foreign/institutional net purchase volumes exist in the current feature generation logic in `src/analysis/screener.py` or the data layer files.
- **R4: Dash Dashboard Components**:
  - `src/web/dashboard.py` implements the Dash dashboard layout and callbacks.
  - The `'global-macro-tab'` tab layout (lines 44-104) has dropdowns, tables, and a heatmap, but contains no Plotly Pie Chart (`portfolio-weights-pie`) or exposure gauge/bar chart for VIX dynamic exposure.

---

## 2. Logic Chain
1. **R1**: Because true Equal Risk Contribution requires minimizing the sum of squared differences of risk contributions across assets, and since the asset returns are correlated, we must use a covariance matrix $\Sigma$. By implementing a convex formulation $\min_y \frac{1}{2} y^T \Sigma y - \sum \ln(y_i)$ using `scipy.optimize.minimize(method='L-BFGS-B')`, we can solve for $y$ and obtain the optimal weights $w = y / \sum y$. This guarantees that risk contributions are exactly equalized and weights sum to 1.0.
2. **R2**: By implementing `check_risk_off_signal(vix_value)` in `RiskManager`, we can return a boolean indicator if VIX >= 25. Under this condition, in `calculate_position_sizing`, we clamp the maximum value of the position to `0.30 * portfolio_value`. To enforce the 70% cash floor at the portfolio-level, we intercept buying orders in `trading_system.py` and restrict the quantity such that the cash remaining in the portfolio post-trade is at least 70% of the total portfolio value ($C_{\text{post}} \ge 0.70 \times PV$).
3. **R3**: By replacing `RandomForestRegressor` with `lightgbm.LGBMRegressor` (with a safe fallback to RF if LightGBM is not present), we upgrade the ML engine to a modern GBDT regressor. To include the supply/demand feature, we simulate foreign and institutional net purchase volumes using a seed based on the stock's ticker hash. By adding these simulated volumes and their lags (lag 1 to 5) to both training and prediction features in `src/analysis/screener.py`, we keep the inputs perfectly aligned and ensure zero feature mismatches.
4. **R4**: Adding `dcc.Graph(id='portfolio-weights-pie')` and `dcc.Graph(id='vix-exposure-gauge')` in the layout, and hooking them to Dash callbacks that compute covariance matrices and fetch VIX dynamically, will provide the user with real-time portfolio optimization and exposure boundaries under risk-off conditions.

---

## 3. Caveats
- **Offline Mode/Network Constraints**: In this network-isolated environment, yfinance and real-time VIX fetches may fail. Thus, robust simulated fallback data generators (like `generate_simulated_macro_data`) are assumed and must be mocked or bypassed inside the unit tests.
- **Mocking Volumes**: Since real foreign and institutional flow data is not available on yfinance, it must be simulated using a deterministic seed (e.g. `42 + hash(ticker) % 1000`) to remain consistent between training and testing.

---

## 4. Conclusion
The exploration phase is complete. The exact files to modify and create are identified. The proposed code implementations for R1, R2, R3, and R4 have been fully detailed in `analysis.md` and are ready for implementation.

---

## 5. Verification Method
- **Verify R1**: Use `pytest` on a new unit test `tests/test_portfolio_risk.py` that mocks a covariance matrix and asserts that the computed weights sum to 1.0 and that high-volatility assets receive a lower weight.
- **Verify R2**: Run the trading system simulation with VIX set to 30.0 and verify that order sizes are clamped such that cash remains >= 70% of the portfolio value.
- **Verify R3**: Execute `pytest tests/test_macro.py` and check that the MSE metric is saved to `data/macro_model_metrics.json`.
- **Verify R4**: Run `python run_dashboard.py` and inspect the layout elements (`portfolio-weights-pie` and `vix-exposure-gauge`) to ensure Dash loads without layout or callback exceptions.

---

## 6. Remaining Work (Handoff to Implementer)
- Implement `src/analysis/portfolio_optimizer.py`.
- Modify `src/risk/risk_manager.py` to add `check_risk_off_signal` and integrate it into `calculate_position_sizing`.
- Modify `trading_system.py`'s `_create_and_submit_order` to clamp orders based on VIX risk-off status.
- Upgrade `src/analysis/macro_predictor.py` to LightGBM.
- Add simulated net purchase volume features to `src/analysis/screener.py` for training and prediction.
- Update `src/web/dashboard.py` layout and callbacks to add the pie and exposure gauge charts.
- Write unit/integration tests to verify R1, R2, R3, and R4.

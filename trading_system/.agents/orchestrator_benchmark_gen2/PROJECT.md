# Project: Phase 5 / Benchmark Optimization

## Architecture
- **src/analysis/portfolio_optimizer.py**: Implement `calculate_risk_parity_weights(cov_matrix)` and other risk parity helpers. Ensure equal risk contribution and weights summing to 1.0.
- **src/risk/risk_manager.py**: Implement VIX check `check_risk_off_signal()` and integrate it into position sizing to cap equity exposure at 30% and safety assets (cash) at 70% when VIX >= 25.
- **src/analysis/macro_predictor.py**: Upgrade RandomForest to LightGBM or XGBoost, incorporating N-day foreign and institutional net purchase volumes.
- **src/web/dashboard.py**: Add Pie Chart (`portfolio-weights-pie`) and exposure gauge/bar chart in the 'Global Macro' tab.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Planning | Analyze existing codebase and design integration points for R1, R2, R3, R4. | None | DONE (Explorer Conv IDs: d4b9f50c-ff43-4fbc-8682-5c9d036ad87e, 63c5f8dc-3251-42bc-84f9-692d9eddacf7, f942737e-b51f-4387-a2be-7c40b010a4b4) |
| 2 | Risk Parity & VIX Switch (R1 & R2) | Implement risk parity weights, equal risk contribution, VIX-based Risk-off limit. | M1 | IN_PROGRESS |
| 3 | ML Upgrade & Supply/Demand (R3) | Upgrade RF to LightGBM/XGBoost, add foreign/institutional volume features. | M1 | PLANNED |
| 4 | Dash Visualization (R4) | Add plotly charts to Global Macro tab of dashboard. | M2, M3 | PLANNED |
| 5 | E2E Testing & Audit | Verify all requirements pass E2E tests and forensic audit. | M2, M3, M4 | PLANNED |

## Interface Contracts
### R1. Portfolio Risk Parity
- `calculate_risk_parity_weights(cov_matrix: np.ndarray or pd.DataFrame) -> np.ndarray`: Returns asset weights summing to 1.0, where higher volatility has lower weight and risk contributions are equalized.
### R2. VIX-Linked Switch
- `check_risk_off_signal(vix_value: float = None) -> bool`: Returns True if VIX exceeds threshold (e.g. >= 25), leading to 30% equity / 70% cash allocation limit.
### R3. ML Model Upgrade
- `MacroPredictor` updated to use LightGBM/XGBoost.
- Features include N-day foreign and institutional net purchase volumes.
### R4. Dash Visualization
- `portfolio-weights-pie`: Plotly Pie chart for risk parity weights.
- Exposure gauge/bar chart for VIX dynamic exposure.

## Code Layout
- `src/analysis/portfolio_optimizer.py`: Risk parity weights calculation.
- `src/analysis/macro_predictor.py`: LightGBM/XGBoost model training.
- `src/web/dashboard.py`: Dashboard layout and callback.
- `tests/test_portfolio_risk.py` / `tests/test_vix_risk_off.py` etc.: Unit/integration tests.

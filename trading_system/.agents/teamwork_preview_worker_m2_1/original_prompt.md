## 2026-06-08T07:29:16Z
You are the Milestone 2 Worker. Your working directory is d:\Finance\code\stock\trading_system\.agents\teamwork_preview_worker_m2_1\.
Your parent is the Project Orchestrator at conversation ID 03461a63-fdbb-4548-bf38-718f18bdb6e4.
Your mission is to implement R1 (Portfolio Risk Parity Weight Optimization) and R2 (VIX-Linked Dynamic Asset Allocation Switch).

Here are the detailed requirements and instructions:

1. R1: Portfolio Risk Parity Weight Optimization
   - Create a new file `src/analysis/portfolio_optimizer.py`.
   - Implement `calculate_risk_parity_weights(cov_matrix: np.ndarray) -> np.ndarray` using scipy's optimizer (e.g. log-barrier formulation with L-BFGS-B or direct variance minimization with SLSQP). Refer to the mathematical blueprints in `d:\Finance\code\stock\trading_system\.agents\teamwork_preview_explorer_m1_2\analysis.md`.
   - Ensure the calculated weights sum exactly to 1.0 and each weight is between 0.0 and 1.0.
   - In case of optimizer failure, implement a robust fallback to inverse-volatility weighting, and if that fails, equal weighting.
   - Include the MANDATORY INTEGRITY WARNING in `src/analysis/portfolio_optimizer.py`.
   - Update `_risk_parity(self, price_data: Dict[str, List[float]])` in `src/strategy/asset_allocation.py` to:
     a. Compute period simple returns for each ticker using `_compute_returns`.
     b. Align returns series to their minimum shared historical length. If length is < 2, fallback to equal weighting.
     c. Compute the sample covariance matrix using numpy.cov.
     d. Call `calculate_risk_parity_weights` to get the weights.
     e. Return normalized weights using the existing `_normalize` helper.

2. R2: VIX-Linked Dynamic Asset Allocation (Risk-Off Switch)
   - In `src/risk/risk_manager.py`, implement `check_risk_off_signal(self, vix_value: float = None) -> bool` which returns True if VIX index >= 25.0. If `vix_value` is not provided, fetch it using `AlternativeDataClient().fetch_vix()` (with safety try-except block, importing `AlternativeDataClient` from `src.data_layer.alt_data`, and falling back to 20.0 on error).
   - In `trading_system.py`, inside the `_create_and_submit_order` method:
     a. Fetch/determine VIX. You can use the VIX cached in `market_data_cache` or call `self.risk_manager.check_risk_off_signal(...)`.
     b. Under risk-off conditions (VIX >= 25.0), enforce that the total cost of any new BUY order does not cause the post-trade cash in the portfolio to drop below 70% of the total portfolio value ($PV$).
     c. Specifically: $PV = C + V_E$ where $C$ is the current cash and $V_E$ is the total equity exposure (value of all open positions based on current cached prices).
     d. Post-trade cash must satisfy $C' \ge 0.70 \times PV$. Since $C' = C - Price \times Quantity$, we must clamp the quantity of any buy order such that:
        $Price \times Quantity \le C - 0.70 \times PV$.
        Clamp the quantity to $\max(0, \lfloor \frac{C - 0.70 \times PV}{Price} \rfloor)$.
     e. Log a warning or info when this VIX-linked risk-off clamping is applied.

3. Mandatory Integrity Warning (include verbatim in all modified/created files):
   # ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
   # DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

4. Testing & Verification:
   - Create a new test file `tests/test_portfolio_risk.py` containing:
     - Tests for R1: Mock a covariance matrix where one asset is high variance and another is low variance. Assert that the low-variance asset receives a higher weight, and the sum of weights is exactly 1.0.
     - Tests for R2: Assert that `check_risk_off_signal` correctly returns True for VIX >= 25 and False otherwise.
     - Tests for R2: Test the buy order clamping logic in a simulated environment to verify that under VIX >= 25, the order is clamped such that post-trade cash is >= 70% of portfolio value.
   - Run the unit tests: `pytest tests/test_portfolio_risk.py tests/test_macro.py tests/test_macro_stress.py` (propose the command to run, and document the output).
   - Verify that all tests pass.

5. Deliverables:
   - Save your detailed implementation details in `d:\Finance\code\stock\trading_system\.agents\teamwork_preview_worker_m2_1\changes.md`.
   - Write a self-contained team handoff report in `d:\Finance\code\stock\trading_system\.agents\teamwork_preview_worker_m2_1\handoff.md` summarizing what you implemented, the exact commands used to run tests, and the test execution outputs.
   - When finished, send a message to the Project Orchestrator with the paths to the changes and handoff reports.

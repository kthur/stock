## 2026-07-31T10:11:17Z

You are explorer_m3_1, the Technical Architecture Explorer for Milestone 3 (R3: CPCV & Historical Stress Testing Engine).

Your working directory is `d:\Finance\code\stock\.agents\explorer_m3_1`. Please create your working directory first if it does not exist.

Your mission:
Investigate the codebase and design the technical specifications and implementation plan for Milestone 3 (R3: CPCV & Historical Stress Testing Engine).

Scope & Specifications:
1. Module location: `src/ai/cpcv_stress_tester.py` (and `trading_system/src/ai/cpcv_stress_tester.py` if mirrored/symlinked).
2. Combinatorial Purged Cross-Validation (CPCV):
   - Implement `CPCVStressTester` class.
   - `generate_purged_folds(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)`: generates combinatorial splits $C(N, k)$ (e.g. 15 folds for 6 choose 2).
   - Purging logic: remove training samples whose time index overlaps with test set evaluation windows.
   - Embargoing logic: remove training samples in the embargo window following any test set interval to prevent autoregressive / serial correlation leak.
   - Calculate Probability of Backtest Overfitting (PBO) using logit / rank distribution across combinatorial backtest paths.
3. Historical Stress Testing Engine:
   - `run_historical_stress_test(strategy_returns: pd.Series | pd.DataFrame, scenario: str)`
   - Support historical crisis scenarios:
     - `'2008_CRISIS'`: 2008 Global Financial Crisis shock vectors (volatility jump + severe drawdown).
     - `'2020_COVID'`: March 2020 Liquidity shock / market panic.
     - `'2022_FED_HIKE'`: 2022 Fed Rate Hike / Stagflation / Tech Sell-off scenario.
   - Calculate stress metrics: Max Drawdown (MDD), 95%/99% Value at Risk (VaR), Conditional VaR / Expected Shortfall (CVaR), and Stress Recovery Time.
   - Output structured dataclass / dict: `StressTestReport(scenario, mdd, var_95, cvar_95, stress_sharpe, pass_flag)`.
4. Integration & Testing Plan:
   - Design integration points with `run_pipeline.py` or AI model validation pipelines.
   - Design comprehensive test suite for `tests/test_cpcv_stress_tester.py` and `trading_system/tests/test_cpcv_stress_tester.py`.

Please inspect `src/ai/`, `src/risk/`, `trading_system/run_pipeline.py`, and existing tests in `tests/`.
Write your full findings and technical design report to `d:\Finance\code\stock\.agents\explorer_m3_1\handoff.md` and `progress.md`.
Notify orchestrator when done via `send_message`.

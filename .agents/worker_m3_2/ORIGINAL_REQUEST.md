## 2026-07-31T10:50:38Z
You are worker_m3_2, the Replacement Implementation Worker for Milestone 3 (R3: CPCV & Historical Stress Testing Engine).

Your working directory is `d:\Finance\code\stock\.agents\worker_m3_2`. Please create your working directory first if it does not exist.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mission:
Implement Milestone 3 (R3: CPCV & Historical Stress Testing Engine) following the technical design in `d:\Finance\code\stock\.agents\explorer_m3_1\handoff.md`.

Requirements & Specifications:
1. Read `d:\Finance\code\stock\.agents\explorer_m3_1\handoff.md` carefully.
2. Implement `CPCVStressTester`, `StressTestReport`, and `run_historical_stress_test` in `trading_system/src/ai/cpcv_stress_tester.py`.
3. Create forwarder in `src/ai/cpcv_stress_tester.py` importing all symbols from `trading_system.src.ai.cpcv_stress_tester`.
4. Feature Details:
   - `generate_purged_folds(X, y=None)`: Combinatorial train/test fold splits $C(N, k)$ (e.g. 15 folds for $N=6, k=2$). Pre-test purging window (default 5 bars) and post-test embargo window (default 10 bars) to eliminate leakage.
   - `compute_pbo(strategy_matrix)`: Compute Probability of Backtest Overfitting (PBO) across combinatorial folds using Marcos Lopez de Prado's logit rank methodology. Clip rank percentile to $[1e-5, 1-1e-5]$.
   - `run_historical_stress_test(strategy_returns, scenario='2008_CRISIS'|'2020_COVID'|'2022_FED_HIKE')`: Apply historical shock vectors, calculate MDD, 95%/99% VaR, 95%/99% CVaR, Stress Recovery Time, Stress Sharpe ratio, and `pass_flag`.
5. Integration:
   - In `trading_system/src/risk/risk_manager.py`: add method or hook to adjust max position sizes if stress test `pass_flag` is False.
   - In `trading_system/run_pipeline.py`: add step to calculate stress test report / PBO metrics for strategy predictions in Step 11 and format output under `[MILESTONE 3: CPCV & HISTORICAL STRESS TEST REPORT]` in `strategy_data_coverage_report.txt`.
6. Unit Tests:
   - Write comprehensive tests in `tests/test_cpcv_stress_tester.py` and `trading_system/tests/test_cpcv_stress_tester.py`.
   - Run tests with `.venv/bin/pytest tests/test_cpcv_stress_tester.py -v` and `.venv/bin/pytest trading_system/tests/test_cpcv_stress_tester.py -v`.
   - Run full regression test suite `.venv/bin/pytest tests/ -v` to ensure zero regressions.

Write your report to `d:\Finance\code\stock\.agents\worker_m3_2\handoff.md` and notify orchestrator when done via `send_message`.

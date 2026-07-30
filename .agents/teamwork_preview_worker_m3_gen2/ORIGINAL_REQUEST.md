## 2026-07-30T15:34:41Z
You are Worker M3 (Gen 2) executing Milestone 3 (Risk Management & Portfolio Optimization Enhancement) for the Stock Trading System.
Working Directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_gen2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Objectives:
1. Implement EVT-CVaR Loss Budget Constraints in src/risk/portfolio_allocator.py (and src/risk/portfolio_optimizer.py):
   - Read Explorer M3-1 handoff report at d:\Finance\code\stock\.agents\explorer_m3_1_gen2\handoff.md for exact mathematical equations and SLSQP constraint formulation.
   - Implement Peaks-Over-Threshold (POT) GPD fitting via scipy.stats.genpareto (or MLE estimation).
   - Implement non-linear loss budget constraint EVT_CVaR(w) <= max_cvar_limit.
   - Implement 3-tier fallback hierarchy: EVT-GPD -> Cornish-Fisher -> Empirical/Gaussian CVaR when sample size N_u < 15 or fitting non-convergent.

2. Implement Dynamic Band-based Rebalancing in src/risk/portfolio_allocator.py (and src/risk/portfolio_optimizer.py):
   - Read Explorer M3-2 handoff report at d:\Finance\code\stock\.agents\explorer_m3_2_gen2\handoff.md.
   - Implement Leland cubic-root buffer band calculation delta_i for each asset based on STT tax (KOSPI 0.15%, KOSDAQ 0.18%, SP500 0.003%), spread, market impact, and volatility.
   - Implement rebalancing decision rule: return HOLD with 0 trade when current weight is within buffer band [w_target - delta_i, w_target + delta_i]; trigger rebalance trade when drift breaches buffer bands.

3. Implement Stat-Arb Candidate Pair Batching Optimization in src/core/stat_arb.py:
   - In find_cointegrated_pairs(), batch candidate pair evaluation in 100,000 pair slices to reduce peak memory under 400 MB and keep scan latency under 10 seconds.

4. Implement Unit Tests & Run Verification:
   - Read Explorer M3-3 handoff report at d:\Finance\code\stock\.agents\explorer_m3_3_gen2\handoff.md for test code templates.
   - Add/update unit tests in tests/test_portfolio_allocator.py (and tests/test_risk_enhancements.py).
   - Execute the test suite using .venv\Scripts\python.exe -m pytest tests/ -v. Ensure all unit tests pass cleanly.

5. Report Results:
   - Document all implemented code changes, test execution logs, and benchmark results in d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_gen2\handoff.md. Send completion message to parent upon finishing.
